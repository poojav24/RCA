from datetime import timedelta
from exceptions.loki_exceptions import LokiHostNotFoundException


class LogFetcher:

    def __init__(self, loki_connector):
        self.loki = loki_connector

    def fetch_logs(
        self,
        host,
        event_time,
        before_minutes=10,
        after_minutes=10,
        limit=500
    ):

        # Check whether the host exists in Loki
        hosts = self.loki.get_label_values("host")

        if host not in hosts:
            raise LokiHostNotFoundException(
                f"{host} is not configured in Loki."
            )

        start = event_time - timedelta(minutes=before_minutes)
        end = event_time + timedelta(minutes=after_minutes)

        query = f'{{host="{host}"}}'

        response = self.loki.query_range(
            query=query,
            start=start,
            end=end,
            limit=limit
        )

        return self.loki.flatten_response(response)