"""
Live NZCC runtime — shared by server.py and main.py.

- Continuous Zabbix alert polling (same pipeline as main.py)
- On-demand live fetches from Zabbix / ServiceNow / Loki
- Knowledge + RCA still persisted to SQLite for history
- UI API shapes stay unchanged (no frontend edits)
"""

from __future__ import annotations

import json
import os
import threading
import time
import traceback
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from config import (
    GROK_API_KEY,
    LOKI_URL,
    PASSWORD,
    SNOW_BASE_URL,
    SNOW_PASSWORD,
    SNOW_USERNAME,
    USERNAME,
    ZABBIX_URL,
)

from connectors.loki_client import LokiConnector
from connectors.servicenow_client import ServiceNowClient
from connectors.zabbix import ZabbixClient
from llm.grok_client import GrokClient
from llm.log_summarizer import LogSummarizer
from processor.log_processor import LogProcessor
from repositories.knowledge_repository import KnowledgeRepository
from repositories.rca_repository import RCARepository
from services.alert_parser import AlertParser
from services.alert_service import AlertService
from services.correlation_service import CorrelationService
from services.evidence_builder import EvidenceBuilder
from services.log_fetcher import LogFetcher
from services.metric_service import MetricService
from services.playbook_service import PlaybookService
from services.problem_pipeline import ProblemPipeline
from services.rca_service import RCAService
from services.resolution_pipeline import ResolutionPipeline
from services.trigger_service import TriggerService

ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = ROOT / ".nzcc_poll_state.json"
POLL_INTERVAL = int(os.environ.get("NZCC_POLL_INTERVAL", "60"))

SEVERITY_MAP = {
    "0": "Information",
    "1": "Information",
    "2": "Warning",
    "3": "Average",
    "4": "High",
    "5": "Critical",
    "not classified": "Information",
    "information": "Information",
    "warning": "Warning",
    "average": "Average",
    "high": "High",
    "disaster": "Critical",
    "critical": "Critical",
}


def _as_confidence(value) -> float:
    try:
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip()
        if not text:
            return 0.0
        # percentage string
        if text.endswith("%"):
            return float(text[:-1]) / 100.0
        return float(text)
    except Exception:
        return 0.0


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_severity(value) -> str:
    if value is None:
        return "Information"
    key = str(value).strip().lower()
    if key in SEVERITY_MAP:
        return SEVERITY_MAP[key]
    # already a friendly label
    for label in ("Critical", "High", "Average", "Warning", "Information"):
        if label.lower() == key:
            return label
    return str(value)


def _safe_json(value):
    if isinstance(value, (dict, list)):
        return value
    if value is None:
        return None
    try:
        return json.loads(value)
    except Exception:
        return value


class LiveRuntime:
    """Thread-safe live backend used by HTTP APIs + poll loop."""

    def __init__(self):
        self.lock = threading.RLock()
        self.started = False
        self.poll_thread = None
        self.stop_event = threading.Event()
        self._start_poller = True
        self._ready = False

        self.connected = False
        self.status = "Starting"
        self.last_poll_at = None
        self.last_error = None
        self.last_alert_id = self._load_last_alert_id()
        self.poll_count = 0

        self.zabbix = None
        self.snow = None
        self.loki = None
        self.alert_service = None
        self.parser = None
        self.problem_pipeline = None
        self.resolution_pipeline = None
        # Local repos available immediately for UI while live connectors boot
        self.knowledge_repository = KnowledgeRepository()
        self.rca_repository = RCARepository()
        self.semantic_search = None
        self.log_fetcher = None

        self.live_alerts = []
        self.live_hosts = []

        # Seed from DB so first API calls work even before Zabbix connects
        try:
            seeded = []
            for row in self.knowledge_repository.get_all():
                pid = str(row.get("problem_id") or row.get("id") or "")
                if not pid:
                    continue
                seeded.append(
                    {
                        "problemId": pid,
                        "severity": _normalize_severity(row.get("severity")),
                        "host": row.get("host") or "unknown",
                        "problem": row.get("problem") or "Unknown problem",
                        "technology": row.get("technology") or "Unknown",
                        "trigger": str(row.get("trigger_id") or "—"),
                        "incidentNumber": row.get("incident_number") or "—",
                        "status": "Resolved",
                        "createdAt": row.get("created_at"),
                        "eventId": pid,
                        "source": "knowledge",
                    }
                )
            self.live_alerts = seeded
        except Exception:
            pass

    # --------------------------------------------------
    # Bootstrap
    # --------------------------------------------------

    def start(self, start_poller: bool = True) -> None:
        with self.lock:
            if self.started:
                return
            self.started = True
            # Heavy connector init off the HTTP accept path
            init_thread = threading.Thread(
                target=self._safe_init,
                name="nzcc-runtime-init",
                daemon=True,
            )
            init_thread.start()
            self._start_poller = start_poller

    def _safe_init(self) -> None:
        try:
            self._init_clients()
            if getattr(self, "_start_poller", True):
                self.poll_thread = threading.Thread(
                    target=self._poll_loop,
                    name="nzcc-zabbix-poller",
                    daemon=True,
                )
                self.poll_thread.start()
            self.status = "Operational" if self.connected else (self.status or "Degraded")
        except Exception as exc:  # noqa: BLE001
            self.status = "Init failed"
            self.last_error = str(exc)
            print(f"[LiveRuntime] Init failed: {exc}")
            traceback.print_exc()

    def _init_clients(self) -> None:
        print("[LiveRuntime] Connecting to Zabbix / ServiceNow / Loki…")
        self.zabbix = ZabbixClient(ZABBIX_URL, USERNAME, PASSWORD)
        try:
            self.zabbix.login()
            self.connected = True
            self.status = "Operational"
            print("[LiveRuntime] Zabbix login OK")
        except Exception as exc:  # noqa: BLE001
            self.connected = False
            self.status = "Zabbix unreachable"
            self.last_error = str(exc)
            print(f"[LiveRuntime] Zabbix login failed: {exc}")

        self.snow = ServiceNowClient(SNOW_BASE_URL, SNOW_USERNAME, SNOW_PASSWORD)
        self.loki = LokiConnector(LOKI_URL)

        self.alert_service = AlertService(self.zabbix) if self.zabbix else None
        self.parser = AlertParser()
        self.correlation_service = CorrelationService(self.snow)
        self.trigger_service = TriggerService(self.zabbix) if self.connected else None

        grok_client = GrokClient(GROK_API_KEY)
        playbook_service = PlaybookService(self.zabbix, grok_client) if self.connected else None
        metric_service = MetricService(self.zabbix) if self.connected else None
        evidence_builder = EvidenceBuilder()
        rca_service = RCAService(grok_client)
        # repos already created in __init__
        self.log_fetcher = LogFetcher(self.loki)
        log_processor = LogProcessor()
        log_summarizer = LogSummarizer(grok_client)

        from services.knowledge_service import KnowledgeService

        knowledge_service = KnowledgeService(self.knowledge_repository)

        # Vector DB is optional — never block API startup
        try:
            from services.semantic_search_service import SemanticSearchService

            self.semantic_search = SemanticSearchService(self.knowledge_repository)
        except Exception as exc:  # noqa: BLE001
            print(f"[LiveRuntime] Vector DB init deferred: {exc}")
            self.semantic_search = None

        if self.connected and self.zabbix:
            self.problem_pipeline = ProblemPipeline(
                self.correlation_service,
                self.trigger_service,
                playbook_service,
                metric_service,
                self.log_fetcher,
                log_processor,
                log_summarizer,
                evidence_builder,
                rca_service,
                self.rca_repository,
                self.knowledge_repository,
                knowledge_service,
                self.semantic_search,
                None,
            )
            self.resolution_pipeline = ResolutionPipeline(
                self.correlation_service,
                self.rca_repository,
                self.snow,
                None,
            )

        try:
            if self.connected:
                self.refresh_live_problems()
        except Exception as exc:  # noqa: BLE001
            print(f"[LiveRuntime] Initial problem refresh failed: {exc}")

        self._ready = True
        print("[LiveRuntime] Ready")

    # --------------------------------------------------
    # Poll state
    # --------------------------------------------------

    def _load_last_alert_id(self) -> int:
        try:
            if STATE_FILE.exists():
                data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                return int(data.get("last_alert_id") or 0)
        except Exception:
            pass
        return 0

    def _save_last_alert_id(self) -> None:
        try:
            STATE_FILE.write_text(
                json.dumps({"last_alert_id": self.last_alert_id, "updated_at": _utc_now_iso()}),
                encoding="utf-8",
            )
        except Exception:
            pass

    # --------------------------------------------------
    # Continuous Zabbix poll (main.py logic)
    # --------------------------------------------------

    def _poll_loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                self.poll_once()
            except Exception as exc:  # noqa: BLE001
                self.last_error = str(exc)
                print(f"[LiveRuntime] Poll error: {exc}")
                traceback.print_exc()
            self.stop_event.wait(POLL_INTERVAL)

    def poll_once(self) -> None:
        """One poll cycle — refresh open problems + process new Zabbix alerts."""
        if not self.zabbix or not self.connected:
            # try reconnect
            try:
                if self.zabbix:
                    self.zabbix.login()
                    self.connected = True
                    self.status = "Operational"
            except Exception as exc:  # noqa: BLE001
                self.connected = False
                self.status = "Zabbix unreachable"
                self.last_error = str(exc)
                self.last_poll_at = _utc_now_iso()
                return

        print()
        print("=" * 70)
        print(f"[LiveRuntime] Polling Zabbix : {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}")
        print("=" * 70)

        # Always refresh open problems for /api/alerts dashboard freshness
        self.refresh_live_problems()

        if not self.alert_service or not self.problem_pipeline:
            self.last_poll_at = _utc_now_iso()
            return

        alerts = self.alert_service.get_new_alerts() or []
        alerts = sorted(alerts, key=lambda x: int(x.alertid))

        for alert in alerts:
            if int(alert.alertid) <= self.last_alert_id:
                continue
            self.last_alert_id = int(alert.alertid)
            self._save_last_alert_id()

            print(f"[LiveRuntime] Processing alert {alert.alertid}")
            parsed = self.parser.parse(alert)

            try:
                if parsed.event_type == "PROBLEM":
                    self.problem_pipeline.run(parsed)
                elif parsed.event_type == "RESOLVED":
                    self.resolution_pipeline.run(parsed)
            except Exception as exc:  # noqa: BLE001
                print(f"[LiveRuntime] Pipeline failed for {alert.alertid}: {exc}")
                traceback.print_exc()

        self.poll_count += 1
        self.last_poll_at = _utc_now_iso()
        self.status = "Operational" if self.connected else self.status

    # --------------------------------------------------
    # Live Zabbix problem snapshot (UI alerts)
    # --------------------------------------------------

    def refresh_live_problems(self) -> list:
        if not self.zabbix or not self.connected:
            return list(self.live_alerts)

        raw = self.zabbix.get_open_problems_raw(limit=100)
        kb_by_problem = {}
        try:
            for row in self.knowledge_repository.get_all():
                pid = str(row.get("problem_id") or "")
                if pid:
                    kb_by_problem[pid] = row
        except Exception:
            pass

        alerts = []
        for p in raw:
            event_id = str(p.get("eventid") or "")
            hosts = p.get("hosts") or []
            host = hosts[0].get("host") if hosts else (p.get("host") or "unknown")
            severity = _normalize_severity(p.get("severity"))
            clock = p.get("clock")
            created = None
            if clock:
                try:
                    created = datetime.fromtimestamp(int(clock), tz=timezone.utc).isoformat()
                except Exception:
                    created = str(clock)

            kb = kb_by_problem.get(event_id) or {}
            incident = kb.get("incident_number") or "—"
            technology = kb.get("technology") or self._guess_technology(p.get("name") or "", host)
            trigger_id = str(p.get("objectid") or kb.get("trigger_id") or "—")

            alerts.append(
                {
                    "problemId": event_id,
                    "severity": severity,
                    "host": host,
                    "problem": p.get("name") or "Unknown problem",
                    "technology": technology,
                    "trigger": trigger_id,
                    "incidentNumber": incident if incident else "—",
                    "status": "Open",
                    "createdAt": created or kb.get("created_at") or _utc_now_iso(),
                    "eventId": event_id,
                    "source": "zabbix",
                }
            )

        # Also surface recently resolved / investigated items from KB that may not be open
        open_ids = {a["problemId"] for a in alerts}
        try:
            for row in self.knowledge_repository.get_all():
                pid = str(row.get("problem_id") or row.get("id") or "")
                if not pid or pid in open_ids:
                    continue
                alerts.append(
                    {
                        "problemId": pid,
                        "severity": _normalize_severity(row.get("severity")),
                        "host": row.get("host") or "unknown",
                        "problem": row.get("problem") or "Unknown problem",
                        "technology": row.get("technology") or "Unknown",
                        "trigger": str(row.get("trigger_id") or "—"),
                        "incidentNumber": row.get("incident_number") or "—",
                        "status": "Resolved",
                        "createdAt": row.get("created_at"),
                        "eventId": pid,
                        "source": "knowledge",
                    }
                )
        except Exception:
            pass

        with self.lock:
            self.live_alerts = alerts
            try:
                self.live_hosts = [
                    {"hostid": h.hostid, "host": h.host, "name": h.name}
                    for h in (self.zabbix.get_hosts() or [])
                ]
            except Exception:
                pass

        return alerts

    def _guess_technology(self, problem: str, host: str) -> str:
        text = f"{problem} {host}".lower()
        if "redis" in text:
            return "Redis"
        if "windows" in text or "mssql" in text:
            return "Windows"
        if "network" in text or "interface" in text:
            return "Network"
        if "linux" in text or "cpu" in text or "memory" in text:
            return "Linux"
        return "Infrastructure"

    # --------------------------------------------------
    # API builders (UI contract)
    # --------------------------------------------------

    def build_dashboard(self) -> dict:
        alerts = self.refresh_live_problems() if self.connected else list(self.live_alerts)
        knowledge = []
        try:
            knowledge = self.knowledge_repository.get_all() if self.knowledge_repository else []
        except Exception:
            knowledge = []

        today = datetime.now(timezone.utc).date()
        today_alerts = 0
        for a in alerts:
            dt = self._parse_dt(a.get("createdAt"))
            if dt and dt.date() == today:
                today_alerts += 1
        if today_alerts == 0:
            today_alerts = len([a for a in alerts if a.get("status") == "Open"])

        open_incidents = len([a for a in alerts if a.get("status") == "Open"])
        resolved = len([a for a in alerts if a.get("status") == "Resolved"])
        critical = len([a for a in alerts if (a.get("severity") or "").lower() == "critical"])

        hosts = {a.get("host") for a in alerts if a.get("host")}
        techs = {a.get("technology") for a in alerts if a.get("technology")}
        if knowledge:
            hosts |= {k.get("host") for k in knowledge if k.get("host")}
            techs |= {k.get("technology") for k in knowledge if k.get("technology")}

        # Real hourly trend from live alert timestamps
        buckets = defaultdict(int)
        for a in alerts:
            dt = self._parse_dt(a.get("createdAt"))
            if not dt:
                continue
            buckets[dt.strftime("%H")] += 1
        if buckets:
            trend = [{"label": h, "value": buckets[h]} for h in sorted(buckets.keys())][-7:]
        else:
            # still real: zeros for last windows rather than fake rising numbers
            now = datetime.now(timezone.utc)
            trend = [
                {"label": f"{(now - timedelta(hours=i)).strftime('%H')}", "value": 0}
                for i in range(6, -1, -1)
            ]

        sev_counts = Counter(_normalize_severity(a.get("severity")) for a in alerts)
        severity_distribution = [
            {"label": label, "count": sev_counts.get(label, 0)}
            for label in ("Critical", "High", "Average", "Information")
        ]

        tech_counts = Counter(a.get("technology") or "Unknown" for a in alerts)
        technology_distribution = [
            {"label": label, "count": count}
            for label, count in tech_counts.most_common(6)
        ]

        avg_rca = self._avg_rca_minutes()

        return {
            "todayAlerts": today_alerts,
            "criticalAlerts": critical,
            "openIncidents": open_incidents,
            "resolvedIncidents": resolved,
            "avgRcaTime": avg_rca,
            "knowledgeSize": len(knowledge),
            "historicalReuse": round(min(100, (len(knowledge) / max(1, open_incidents + resolved)) * 100)),
            "connectedHosts": len(hosts) or len(self.live_hosts),
            "connectedTechnologies": len(techs),
            "systemHealth": 100 if self.connected else 0,
            "backendStatus": self.status,
            "alertTrend": trend,
            "severityDistribution": severity_distribution,
            "technologyDistribution": technology_distribution,
            "knowledgeGrowth": f"+{len(knowledge)} indexed",
        }

    def build_alerts(self) -> dict:
        alerts = self.refresh_live_problems() if self.connected else list(self.live_alerts)
        # Strip internal fields for UI
        clean = []
        for a in alerts:
            clean.append(
                {
                    "problemId": a["problemId"],
                    "severity": a.get("severity") or "Information",
                    "host": a.get("host") or "unknown",
                    "problem": a.get("problem") or "Unknown problem",
                    "technology": a.get("technology") or "Unknown",
                    "trigger": a.get("trigger") or "—",
                    "incidentNumber": a.get("incidentNumber") or "—",
                    "status": a.get("status") or "Open",
                    "createdAt": a.get("createdAt"),
                }
            )
        return {"alerts": clean}

    def _find_knowledge(self, problem_id: str):
        if not self.knowledge_repository:
            return None
        # Prefer Zabbix problem_id
        for row in self.knowledge_repository.get_all():
            if str(row.get("problem_id") or "") == str(problem_id):
                return row
            if str(row.get("id") or "") == str(problem_id):
                return row
        return None

    def build_alert_detail(self, problem_id: str) -> dict:
        alerts = {a["problemId"]: a for a in (self.live_alerts or self.refresh_live_problems())}
        alert = alerts.get(str(problem_id))
        kb = self._find_knowledge(problem_id)

        if not alert and kb:
            alert = {
                "problemId": str(kb.get("problem_id") or kb.get("id")),
                "severity": _normalize_severity(kb.get("severity")),
                "host": kb.get("host") or "unknown",
                "problem": kb.get("problem") or "Unknown problem",
                "technology": kb.get("technology") or "Unknown",
                "trigger": str(kb.get("trigger_id") or "—"),
                "incidentNumber": kb.get("incident_number") or "—",
                "status": "Resolved",
                "createdAt": kb.get("created_at"),
            }

        if not alert:
            return {"alert": None, "metrics": [], "historicalIncidents": []}

        host = alert.get("host")
        metrics = self.fetch_live_metrics(host)
        if not metrics and kb:
            metrics = self._metrics_from_kb(kb)

        historical = self._historical_similar(alert.get("problem") or "", host or "")

        return {
            "alert": {
                "problemId": alert["problemId"],
                "severity": alert.get("severity") or "Information",
                "host": host or "unknown",
                "problem": alert.get("problem") or "Unknown problem",
                "technology": alert.get("technology") or "Unknown",
                "trigger": alert.get("trigger") or "—",
                "incidentNumber": alert.get("incidentNumber") or "—",
                "status": alert.get("status") or "Open",
                "createdAt": alert.get("createdAt"),
            },
            "metrics": metrics,
            "historicalIncidents": historical,
        }

    def build_rca(self, problem_id: str) -> dict:
        # RCA repository keyed by Zabbix original_problem_id
        row = None
        if self.rca_repository:
            try:
                row = self.rca_repository.get(problem_id)
            except Exception:
                row = None

        if row:
            return {
                "problemId": problem_id,
                "rootCause": row.get("root_cause") or "Root cause is being generated from live evidence.",
                "confidence": _as_confidence(row.get("confidence")),
                "impact": row.get("impact") or "-",
                "reasoning": _safe_json(row.get("reasoning")) or [],
                "recommendedResolution": _safe_json(row.get("recommended_resolution"))
                or _safe_json(row.get("resolution"))
                or [],
                "nextDiagnostics": _safe_json(row.get("next_diagnostics"))
                or _safe_json(row.get("diagnostics"))
                or [],
            }

        kb = self._find_knowledge(problem_id)
        if kb:
            return {
                "problemId": problem_id,
                "rootCause": kb.get("root_cause") or "Root cause is being generated from live evidence.",
                "confidence": _as_confidence(kb.get("confidence")),
                "impact": kb.get("impact") or "-",
                "reasoning": _safe_json(kb.get("reasoning")) or [],
                "recommendedResolution": _safe_json(kb.get("remediation")) or _safe_json(kb.get("recommended_resolution")) or [],
                "nextDiagnostics": _safe_json(kb.get("diagnostics")) or _safe_json(kb.get("next_diagnostics")) or [],
            }

        return {
            "problemId": problem_id,
            "rootCause": "Root cause is being generated from live evidence.",
            "confidence": 0.0,
            "impact": "-",
            "reasoning": [],
            "recommendedResolution": [],
            "nextDiagnostics": [],
        }

    def fetch_live_metrics(self, host: str | None) -> list:
        if not host or not self.zabbix or not self.connected:
            return []
        try:
            host_obj = self.zabbix.get_host_by_name(host)
            if not host_obj:
                return []
            metrics = self.zabbix.get_rca_metrics(host_obj["hostid"]) or []
            out = []
            for m in metrics[:40]:
                out.append(
                    {
                        "host": host,
                        "technology": self._guess_technology(getattr(m, "name", ""), host),
                        "name": getattr(m, "name", None) or getattr(m, "key", "Metric"),
                        "value": getattr(m, "lastvalue", None) or getattr(m, "value", 0),
                        "unit": getattr(m, "units", None) or "—",
                    }
                )
            return out
        except Exception as exc:  # noqa: BLE001
            print(f"[LiveRuntime] Live metrics failed for {host}: {exc}")
            return []

    def build_metrics(self, host: str | None = None) -> dict:
        # Prefer live Zabbix
        if host:
            live = self.fetch_live_metrics(host)
            if live:
                return {"metrics": live}

        # All hosts currently in live alerts
        metrics = []
        hosts = []
        if host:
            hosts = [host]
        else:
            hosts = sorted({a.get("host") for a in self.live_alerts if a.get("host")})[:8]
            if not hosts and self.live_hosts:
                hosts = [h["host"] for h in self.live_hosts[:5]]

        for h in hosts:
            metrics.extend(self.fetch_live_metrics(h))

        if metrics:
            return {"metrics": metrics}

        # Fallback: stored investigation metrics
        if self.knowledge_repository:
            for row in self.knowledge_repository.get_all():
                if host and row.get("host") != host:
                    continue
                metrics.extend(self._metrics_from_kb(row))
        return {"metrics": metrics}

    def _metrics_from_kb(self, row) -> list:
        parsed = _safe_json(row.get("metrics")) or []
        out = []
        if isinstance(parsed, list):
            for item in parsed:
                if not isinstance(item, dict):
                    continue
                out.append(
                    {
                        "host": row.get("host"),
                        "technology": row.get("technology"),
                        "name": item.get("name") or "Metric",
                        "value": item.get("value") or 0,
                        "unit": item.get("unit") or "—",
                    }
                )
        return out

    def fetch_live_logs(self, host: str | None) -> list:
        if not host or not self.log_fetcher:
            return []
        try:
            # Fast readiness check with short timeout
            import requests

            ready = requests.get(f"{LOKI_URL.rstrip('/')}/ready", timeout=3)
            if ready.status_code >= 400:
                return []
        except Exception:
            return []

        try:
            end = datetime.now(timezone.utc)
            entries = self.log_fetcher.fetch_logs(host, end, before_minutes=30, after_minutes=1, limit=100)
            out = []
            for entry in entries[:80]:
                if isinstance(entry, dict):
                    ts = entry.get("timestamp") or entry.get("ts") or _utc_now_iso()
                    # Loki ns timestamps
                    if isinstance(ts, str) and ts.isdigit():
                        try:
                            ts = datetime.fromtimestamp(int(ts) / 1_000_000_000, tz=timezone.utc).isoformat()
                        except Exception:
                            pass
                    out.append(
                        {
                            "host": host,
                            "timestamp": ts,
                            "message": entry.get("line") or entry.get("message") or str(entry),
                        }
                    )
                else:
                    out.append({"host": host, "timestamp": _utc_now_iso(), "message": str(entry)})
            return out
        except Exception as exc:  # noqa: BLE001
            print(f"[LiveRuntime] Live Loki fetch failed for {host}: {exc}")
            return []

    def build_logs(self, host: str | None = None) -> dict:
        if host:
            live = self.fetch_live_logs(host)
            if live:
                return {"logs": live}
        else:
            logs = []
            hosts = sorted({a.get("host") for a in self.live_alerts if a.get("host")})[:5]
            for h in hosts:
                logs.extend(self.fetch_live_logs(h))
            if logs:
                return {"logs": logs}

        # Fallback to stored summaries
        logs = []
        if self.knowledge_repository:
            for row in self.knowledge_repository.get_all():
                if host and row.get("host") != host:
                    continue
                raw = row.get("log_summary") or ""
                if not raw:
                    continue
                parsed = _safe_json(raw)
                if isinstance(parsed, list):
                    for item in parsed:
                        logs.append(
                            {
                                "host": row.get("host"),
                                "timestamp": row.get("created_at"),
                                "message": item if isinstance(item, str) else json.dumps(item),
                            }
                        )
                else:
                    logs.append(
                        {
                            "host": row.get("host"),
                            "timestamp": row.get("created_at"),
                            "message": str(raw),
                        }
                    )
        if not logs:
            return {
                "logs": [
                    {
                        "host": host or "unknown",
                        "timestamp": None,
                        "message": "Logs are currently unavailable for this host.",
                    }
                ]
            }
        return {"logs": logs}

    def build_knowledge(self) -> dict:
        knowledge = []
        if not self.knowledge_repository:
            return {"knowledge": knowledge}
        for row in self.knowledge_repository.get_all():
            knowledge.append(
                {
                    "host": row.get("host"),
                    "problem": row.get("problem"),
                    "technology": row.get("technology"),
                    "severity": _normalize_severity(row.get("severity")),
                    "rootCause": row.get("root_cause"),
                    "confidence": _as_confidence(row.get("confidence")),
                    "occurrences": int(row.get("occurrences") or 1) if str(row.get("occurrences") or "1").isdigit() else 1,
                    "lastSeen": row.get("created_at"),
                }
            )
        return {"knowledge": knowledge}

    def build_search(self, query: str) -> dict:
        query = (query or "").strip()
        results = []
        if not query:
            return {"results": results}

        # Prefer vector DB semantic search when available
        if self.semantic_search:
            try:
                hits = self.semantic_search.search_text(query, top_k=8)
                for hit in hits or []:
                    row = hit if isinstance(hit, dict) else {}
                    results.append(
                        {
                            "problem": row.get("problem") or query,
                            "rootCause": row.get("root_cause") or row.get("rootCause") or "",
                            "technology": row.get("technology") or "",
                            "confidence": row.get("score") or row.get("similarity") or row.get("confidence") or 0.0,
                        }
                    )
                if results:
                    return {"results": results}
            except Exception as exc:  # noqa: BLE001
                print(f"[LiveRuntime] Vector search failed, falling back: {exc}")

        if self.knowledge_repository:
            for row in self.knowledge_repository.get_all():
                blob = " ".join(
                    str(x or "")
                    for x in (
                        row.get("problem"),
                        row.get("root_cause"),
                        row.get("technology"),
                        row.get("host"),
                    )
                ).lower()
                if query.lower() in blob:
                    results.append(
                        {
                            "problem": row.get("problem"),
                            "rootCause": row.get("root_cause"),
                            "technology": row.get("technology"),
                            "confidence": row.get("confidence") or 0.0,
                        }
                    )
        return {"results": results}

    def build_servicenow(self) -> dict:
        incidents = []
        # Live ServiceNow table query
        try:
            if self.snow:
                rows = self.snow.list_incidents(limit=50) or []
                for row in rows:
                    ag = row.get("assignment_group")
                    if isinstance(ag, dict):
                        ag = ag.get("display_value") or ag.get("value") or "—"
                    incidents.append(
                        {
                            "incidentNumber": row.get("number") or "—",
                            "problem": row.get("short_description") or "—",
                            "status": row.get("state") or "—",
                            "priority": row.get("priority") or "—",
                            "assignmentGroup": ag or "—",
                        }
                    )
        except Exception as exc:  # noqa: BLE001
            print(f"[LiveRuntime] ServiceNow live list failed: {exc}")

        if incidents:
            return {"incidents": incidents}

        # Fallback: correlated numbers from knowledge + live refresh of each
        if self.knowledge_repository:
            for row in self.knowledge_repository.get_all():
                number = row.get("incident_number")
                if not number:
                    continue
                detail = None
                try:
                    detail = self.snow.get_incident_by_number(number) if self.snow else None
                except Exception:
                    detail = None
                if detail:
                    ag = detail.get("assignment_group")
                    if isinstance(ag, dict):
                        ag = ag.get("display_value") or ag.get("value")
                    incidents.append(
                        {
                            "incidentNumber": detail.get("number") or number,
                            "problem": detail.get("short_description") or row.get("problem"),
                            "status": detail.get("state") or "—",
                            "priority": detail.get("priority") or "—",
                            "assignmentGroup": ag or "—",
                        }
                    )
                else:
                    incidents.append(
                        {
                            "incidentNumber": number,
                            "problem": row.get("problem"),
                            "status": "Linked",
                            "priority": row.get("severity") or "—",
                            "assignmentGroup": "—",
                        }
                    )
        return {"incidents": incidents}

    def build_analytics(self) -> dict:
        knowledge = self.build_knowledge()["knowledge"]
        alerts = self.live_alerts or []
        techs = [item.get("technology") for item in knowledge if item.get("technology")]
        tech_counts = Counter(techs)
        causes = [item.get("rootCause") for item in knowledge if item.get("rootCause")]
        triggers = Counter(a.get("trigger") for a in alerts if a.get("trigger") and a.get("trigger") != "—")

        return {
            "avgRcaTime": self._avg_rca_minutes(),
            "avgResolutionTime": self._avg_rca_minutes(),
            "knowledgeGrowth": f"+{len(knowledge)} indexed",
            "mostCommonTechnologies": ", ".join(t for t, _ in tech_counts.most_common(4)) or "—",
            "topRootCauses": causes[:5],
            "topTriggers": [t for t, _ in triggers.most_common(5)],
        }

    def build_system_status(self) -> dict:
        status = self.status
        if not self.connected:
            status = "Zabbix unreachable" if "zabbix" in (self.last_error or "").lower() or "resolve" in (self.last_error or "").lower() else (self.status or "Degraded")
        return {
            "connected": bool(self.connected),
            "status": status,
            "backend": "Live Zabbix + ServiceNow + Loki + SQLite knowledge",
            "pollingIntervalSec": POLL_INTERVAL,
            "lastUpdated": self.last_poll_at or _utc_now_iso(),
        }

    def _historical_similar(self, problem: str, host: str) -> list:
        out = []
        if self.semantic_search and problem:
            try:
                hits = self.semantic_search.search_text(f"{host} {problem}", top_k=5) or []
                for hit in hits:
                    if not isinstance(hit, dict):
                        continue
                    sim = hit.get("similarity") or hit.get("score") or 0
                    try:
                        sim_f = float(sim)
                    except Exception:
                        sim_f = 0
                    out.append(
                        {
                            "problem": hit.get("problem"),
                            "technology": hit.get("technology"),
                            "rootCause": hit.get("root_cause") or hit.get("rootCause"),
                            "similarity": int(round(sim_f * 100)) if sim_f <= 1 else int(sim_f),
                            "lastSeen": hit.get("created_at") or hit.get("lastSeen"),
                            "occurrences": hit.get("occurrences") or 1,
                        }
                    )
                if out:
                    return out
            except Exception:
                pass

        if self.knowledge_repository:
            for row in self.knowledge_repository.get_all()[:5]:
                out.append(
                    {
                        "problem": row.get("problem"),
                        "technology": row.get("technology"),
                        "rootCause": row.get("root_cause"),
                        "similarity": 70,
                        "lastSeen": row.get("created_at"),
                        "occurrences": 1,
                    }
                )
        return out

    def _avg_rca_minutes(self) -> str:
        try:
            rows = []
            if self.rca_repository:
                # rca_repository may not have list_all — use knowledge timestamps
                pass
            knowledge = self.knowledge_repository.get_all() if self.knowledge_repository else []
            stamps = [self._parse_dt(k.get("created_at")) for k in knowledge]
            stamps = [s for s in stamps if s]
            stamps.sort()
            if len(stamps) >= 2:
                spans = [(b - a).total_seconds() for a, b in zip(stamps, stamps[1:])]
                avg = sum(spans) / len(spans)
                return f"{max(1, int(avg / 60))}m"
        except Exception:
            pass
        return "—"

    @staticmethod
    def _parse_dt(value):
        if not value:
            return None
        try:
            if isinstance(value, (int, float)):
                return datetime.fromtimestamp(value, tz=timezone.utc)
            text = str(value)
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            dt = datetime.fromisoformat(text)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return None


_RUNTIME: LiveRuntime | None = None
_RUNTIME_LOCK = threading.Lock()


def get_runtime(start_poller: bool = True) -> LiveRuntime:
    global _RUNTIME
    with _RUNTIME_LOCK:
        if _RUNTIME is None:
            _RUNTIME = LiveRuntime()
            _RUNTIME.start(start_poller=start_poller)
        return _RUNTIME
