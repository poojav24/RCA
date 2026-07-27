import requests
from datetime import datetime


class LokiConnector:
    """
    Connector for Grafana Loki.
    Responsible only for communicating with the Loki API.
    """

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def _to_nanoseconds(self, dt: datetime) -> int:
        return int(dt.timestamp() * 1_000_000_000)

    def health(self):
        """Check whether Loki is reachable."""
        response = self.session.get(
            f"{self.base_url}/ready",
            timeout=30
        )
        response.raise_for_status()
        return response.text

    def get_labels(self):
        response = self.session.get(
            f"{self.base_url}/loki/api/v1/labels",
            timeout=30
        )
        response.raise_for_status()
        return response.json()["data"]

    def get_label_values(self, label: str):
        response = self.session.get(
            f"{self.base_url}/loki/api/v1/label/{label}/values",
            timeout=30
        )
        response.raise_for_status()
        return response.json()["data"]

    def query_range(
        self,
        query: str,
        start: datetime,
        end: datetime,
        limit: int = 500,
        direction: str = "forward"
    ):
        params = {
            "query": query,
            "start": self._to_nanoseconds(start),
            "end": self._to_nanoseconds(end),
            "limit": limit,
            "direction": direction
        }

        response = self.session.get(
            f"{self.base_url}/loki/api/v1/query_range",
            params=params,
            timeout=60
        )

        response.raise_for_status()

        return response.json()

    def flatten_response(self, response_json):
        """
        Converts Loki response into a simple list of logs.
        """

        logs = []

        results = response_json.get("data", {}).get("result", [])

        for stream in results:

            labels = stream.get("stream", {})

            for timestamp, message in stream.get("values", []):

                logs.append(
                    {
                        "timestamp": timestamp,
                        "message": message,
                        "labels": labels
                    }
                )

        return logs