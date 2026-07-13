import time
import json
from datetime import datetime


from config import *

import connectors.zabbix
from connectors.zabbix import ZabbixClient
from connectors.servicenow_client import ServiceNowClient

from services.alert_service import AlertService
from services.alert_parser import AlertParser
from services.correlation_service import CorrelationService
from services.trigger_service import TriggerService
from services.playbook_service import PlaybookService
from services.metric_service import MetricService
from services.metric_validator import MetricValidator
# from llm.grok_client import GrokClient
# from playbooks.registry import PlaybookRegistry
from llm.grok_client import GrokClient
from config import GROK_API_KEY
from connectors.loki_client import LokiConnector
from services.log_fetcher import LogFetcher
from processor.log_processor import LogProcessor
from llm.log_summarizer import LogSummarizer
from services.evidence_builder import EvidenceBuilder
from services.rca_service import RCAService
from exceptions.loki_exceptions import LokiHostNotFoundException

# grok = GrokClient(GROK_API_KEY)


print("Using:", connectors.zabbix.__file__)

POLL_INTERVAL = 60


def main():

    print("=" * 70)
    print("Near Zero Command Center - RCA Agent Started")
    print("=" * 70)

    # ----------------------------------------------------
    # Clients
    # ----------------------------------------------------

    zabbix = ZabbixClient(
        ZABBIX_URL,
        USERNAME,
        PASSWORD
    )

    zabbix.login()

    print("Has get_metrics :", hasattr(zabbix, "get_metrics"))

    snow = ServiceNowClient(
        SNOW_BASE_URL,
        SNOW_USERNAME,
        SNOW_PASSWORD
    )

    # ----------------------------------------------------
    # Services
    # ----------------------------------------------------
    alert_service = AlertService(zabbix)
    parser = AlertParser()
    correlation_service = CorrelationService(snow)
    trigger_service = TriggerService(zabbix)

    # LLM Components
    grok_client = GrokClient(GROK_API_KEY)

    evidence_builder = EvidenceBuilder()

    rca_service = RCAService(grok_client)
    
    playbook_service = PlaybookService(
        zabbix,
        grok_client,
    )

    metric_service = MetricService(zabbix) 
        # Highest processed alert id
    last_alert_id = 0

    loki = LokiConnector(LOKI_URL)

    log_fetcher = LogFetcher(loki)

    log_processor = LogProcessor()

    log_summarizer = LogSummarizer(grok_client)

    while True:

        try:

            print()
            print("=" * 70)
            print(
                f"Polling Alerts : {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"
            )
            print("=" * 70)

            alerts = alert_service.get_new_alerts()

            if not alerts:
                print("No alerts returned.")
                time.sleep(POLL_INTERVAL)
                continue

            # Process oldest -> newest
            alerts = sorted(
                alerts,
                key=lambda x: int(x.alertid)
            )

            for alert in alerts:

                # Skip already processed alerts
                if int(alert.alertid) <= last_alert_id:
                    continue

                last_alert_id = int(alert.alertid)

                print()
                print("=" * 70)
                print(f"Processing Alert : {alert.alertid}")
                print("=" * 70)

                # --------------------------------------------------
                # Parse Alert
                # --------------------------------------------------

                parsed = parser.parse(alert)
                
                parsed.problem
                parsed.host
                parsed.original_problem_id
                # --------------------------------------------------
                # Correlate ServiceNow
                # --------------------------------------------------

                incident = correlation_service.correlate(parsed)

                # --------------------------------------------------
                # Trigger
                # --------------------------------------------------

                trigger = trigger_service.get_trigger(parsed)

                if trigger is None:
                    continue

                # --------------------------------------------------
                # Playbook
                # --------------------------------------------------

                playbook = playbook_service.get_playbook(trigger)

                if playbook is None:
                    print("No playbook found.")
                    continue

                # If Generic playbook doesn't contain metrics
                if "metrics" not in playbook:
                    print("Playbook has no metrics defined.")
                    continue

                # --------------------------------------------------
                # Collect Metrics
                # --------------------------------------------------

                incident = metric_service.collect(
                    incident,
                    trigger,
                    playbook
                )

                # --------------------------------------------------
                # Loki Log Collection (Optional)
                # --------------------------------------------------

                log_summary = None
                logs_available = False

                try:

                    logs = log_fetcher.fetch_logs(
                        host=parsed.host,
                        event_time=parsed.started_time
                    )

                    print()
                    print("=" * 70)
                    print(f"Fetched {len(logs)} logs from Loki")
                    print("=" * 70)

                    processed_logs = log_processor.process(logs)

                    log_summary = log_summarizer.summarize(processed_logs)

                    logs_available = True

                except LokiHostNotFoundException as ex:

                    print()
                    print("=" * 70)
                    print("LOKI FALLBACK")
                    print("=" * 70)
                    print(ex)
                    print("Continuing RCA using Metrics + ServiceNow only.")

                except Exception as ex:

                    print()
                    print("=" * 70)
                    print("LOKI ERROR")
                    print("=" * 70)
                    print(ex)
                    print("Continuing RCA using Metrics + ServiceNow only.")

                # --------------------------------------------------
                # ServiceNow Details
                # --------------------------------------------------

                print()
                print("=" * 70)
                print("SERVICENOW INCIDENT")
                print("=" * 70)

                if incident.snow:

                    snow_inc = incident.snow

                    print("Incident Number   :", snow_inc.get("number"))
                    print("Short Description :", snow_inc.get("short_description"))
                    print("Priority          :", snow_inc.get("priority"))
                    print("Severity          :", snow_inc.get("severity"))
                    print("State             :", snow_inc.get("state"))
                    print("Assignment Group  :", snow_inc.get("assignment_group"))
                    print("Assigned To       :", snow_inc.get("assigned_to"))
                    print("Opened By         :", snow_inc.get("opened_by"))
                    print("Opened At         :", snow_inc.get("opened_at"))
                    print("Category          :", snow_inc.get("category"))
                    print("Subcategory       :", snow_inc.get("subcategory"))

                else:

                    print("No matching ServiceNow incident found.")

                # --------------------------------------------------
                # Metrics
                # --------------------------------------------------

                print()
                print("=" * 70)
                print("COLLECTED METRICS")
                print("=" * 70)

                if incident.metrics:

                    for metric in incident.metrics:
                        print(metric)

                else:

                    print("No metrics collected.")

                # --------------------------------------------------
                # Build Evidence
                # --------------------------------------------------

                print()
                print("=" * 70)
                print("BUILDING EVIDENCE")
                print("=" * 70)

                evidence = evidence_builder.build(
                    parsed_alert=parsed,
                    incident=incident,
                    trigger=trigger,
                    playbook=playbook,
                    log_summary=log_summary,
                    logs_available=logs_available
                )

                print(evidence_builder.to_json(evidence))

                # --------------------------------------------------
                # RCA
                # --------------------------------------------------

                print()
                print("=" * 70)
                print("RUNNING RCA")
                print("=" * 70)

                rca = rca_service.analyze(evidence)

                print(json.dumps(
                    rca,
                    indent=4
                ))

            print()
            print(f"Waiting {POLL_INTERVAL} seconds...")
            print()

            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            print("\nStopping RCA Agent...")
            break

        except Exception as e:
            print("\nUnexpected Error:")
            print(e)
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()