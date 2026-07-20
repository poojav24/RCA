import time
from datetime import datetime

from config import *
from config import GROK_API_KEY

import connectors.zabbix
from connectors.zabbix import ZabbixClient
from connectors.servicenow_client import ServiceNowClient
from connectors.loki_client import LokiConnector

from services.alert_service import AlertService
from services.alert_parser import AlertParser
from services.correlation_service import CorrelationService
from services.trigger_service import TriggerService
from services.playbook_service import PlaybookService
from services.metric_service import MetricService
from services.problem_pipeline import ProblemPipeline
from services.evidence_builder import EvidenceBuilder
from services.rca_service import RCAService
from services.log_fetcher import LogFetcher
from services.resolution_pipeline import ResolutionPipeline

from processor.log_processor import LogProcessor

from llm.grok_client import GrokClient
from llm.log_summarizer import LogSummarizer

from repositories.rca_repository import RCARepository
from repositories.dedup_repository import DedupRepository

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

    loki = LokiConnector(LOKI_URL)

    # ----------------------------------------------------
    # Services
    # ----------------------------------------------------

    alert_service = AlertService(zabbix)

    parser = AlertParser()

    correlation_service = CorrelationService(snow)

    trigger_service = TriggerService(zabbix)

    grok_client = GrokClient(GROK_API_KEY)

    playbook_service = PlaybookService(
        zabbix,
        grok_client
    )

    metric_service = MetricService(zabbix)

    evidence_builder = EvidenceBuilder()

    rca_service = RCAService(grok_client)

    rca_repository = RCARepository()

    log_fetcher = LogFetcher(loki)

    log_processor = LogProcessor()

    log_summarizer = LogSummarizer(grok_client)

    dedup_repository = DedupRepository()
    repository = RCARepository()

# dedup_repository = DedupRepository()

    # ----------------------------------------------------
    # Problem Pipeline
    # ----------------------------------------------------

    problem_pipeline = ProblemPipeline(
        correlation_service,
        trigger_service,
        playbook_service,
        metric_service,
        log_fetcher,
        log_processor,
        log_summarizer,
        evidence_builder,
        rca_service,
        repository,
        dedup_repository
    )

    resolution_pipeline = ResolutionPipeline(
        correlation_service,
        repository,
        snow,
        dedup_repository
    )

    # ----------------------------------------------------
    # Highest processed alert
    # ----------------------------------------------------

    last_alert_id = 0

    # ----------------------------------------------------
    # Poll Loop
    # ----------------------------------------------------

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

            # Oldest -> Newest

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

                parsed = parser.parse(alert)

                # --------------------------------------------------
                # Later
                #
                # if parsed.event_type == "PROBLEM":
                #     problem_pipeline.run(parsed)
                #
                # elif parsed.event_type == "RESOLVED":
                #     resolution_pipeline.run(parsed)
                # --------------------------------------------------

                if parsed.event_type == "PROBLEM":

                    problem_pipeline.run(parsed)

                elif parsed.event_type == "RESOLVED":

                    resolution_pipeline.run(parsed)

                else:

                    print("Unknown Event Type")

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