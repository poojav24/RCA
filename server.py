"""
NZCC HTTP server — serves the existing UI and LIVE APIs.

UI files are unchanged. API responses are built from:
  - continuous Zabbix polling (same pipeline as main.py)
  - on-demand Zabbix metrics / open problems
  - live ServiceNow incidents
  - live Loki logs
  - SQLite knowledge + RCA history + vector search
"""

from __future__ import annotations

import json
import os
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent


def get_runtime():
    from services.live_runtime import get_runtime as _get

    return _get(start_poller=True)


class NZCCHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        path = url.path
        query = parse_qs(url.query)

        if path == "/":
            self.serve_file("index.html", "text/html; charset=utf-8")
            return

        if path.startswith("/api/"):
            self.handle_api(path[len("/api/") :], query)
            return

        self.serve_file(path.lstrip("/"), None)

    def handle_api(self, path, query):
        runtime = get_runtime()
        try:
            if path == "dashboard":
                payload = runtime.build_dashboard()
            elif path == "alerts":
                payload = runtime.build_alerts()
            elif path.startswith("alert-details/"):
                payload = runtime.build_alert_detail(path.split("/")[-1])
            elif path.startswith("rca/"):
                payload = runtime.build_rca(path.split("/")[-1])
            elif path == "metrics":
                payload = runtime.build_metrics(query.get("host", [None])[0])
            elif path == "logs":
                payload = runtime.build_logs(query.get("host", [None])[0])
            elif path == "knowledge":
                payload = runtime.build_knowledge()
            elif path == "search":
                payload = runtime.build_search(query.get("query", [""])[0])
            elif path == "servicenow":
                payload = runtime.build_servicenow()
            elif path == "analytics":
                payload = runtime.build_analytics()
            elif path == "system-status":
                payload = runtime.build_system_status()
            else:
                self.send_json({"error": "Not found"}, status=404)
                return
            self.send_json(payload)
        except Exception as exc:  # noqa: BLE001
            self.send_json({"error": str(exc)}, status=500)

    def serve_file(self, filename, content_type):
        if filename in {"", "index.html"}:
            filename = "index.html"
        if filename.startswith("/"):
            filename = filename[1:]
        file_path = ROOT / filename
        if not file_path.exists() or file_path.is_dir():
            self.send_response(404)
            self.end_headers()
            return
        data = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type or self.guess_type(file_path))
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def guess_type(self, path):
        if path.suffix == ".css":
            return "text/css; charset=utf-8"
        if path.suffix == ".js":
            return "application/javascript; charset=utf-8"
        return "application/octet-stream"

    def send_json(self, payload, status=200):
        body = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


def get_available_port(default_port=8001):
    candidate_ports = [
        int(os.environ.get("NZCC_PORT", default_port)),
        8001,
        8002,
        8003,
        8080,
        8081,
    ]
    for port in candidate_ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("0.0.0.0", port))
                return port
            except OSError:
                continue
    raise RuntimeError("No available port found for NZCC server")


if __name__ == "__main__":
    # Kick off live connectors in background, then accept HTTP immediately
    runtime = get_runtime()
    port = get_available_port()
    server = ThreadingHTTPServer(("0.0.0.0", port), NZCCHandler)
    print(f"NZCC live server listening on http://127.0.0.1:{port}")
    print("Live Zabbix/ServiceNow/Loki connectors initializing in background…")
    print(f"Initial status: {runtime.status}")
    server.serve_forever()
