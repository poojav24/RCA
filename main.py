import time
from datetime import datetime

from config import *

from connectors.zabbix import ZabbixClient
from connectors.servicenow_client import ServiceNowClient

from services.alert_service import AlertService
from services.alert_parser import AlertParser
from services.correlation_service import CorrelationService
from services.metric_service import MetricService

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

    metric_service = MetricService(zabbix)

    processed_alerts = set()

    # ----------------------------------------------------
    # Polling
    # ----------------------------------------------------

    while True:

        try:

            print("\n")
            print("=" * 70)
            print(
                f"Polling Alerts : {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"
            )
            print("=" * 70)

            alerts = alert_service.get_new_alerts()

            if not alerts:

                print("No new ServiceNow alerts found.")

            else:

                for alert in alerts:

                    if alert.alertid in processed_alerts:
                        continue

                    processed_alerts.add(alert.alertid)

                    print("\n")
                    print("=" * 70)
                    print("NEW SERVICENOW ALERT")
                    print("=" * 70)

                    # -----------------------------
                    # Parse Alert
                    # -----------------------------

                    parsed = parser.parse(alert)

                    # -----------------------------
                    # Correlate ServiceNow
                    # -----------------------------

                    incident = correlation_service.correlate(parsed)

                    # -----------------------------
                    # Collect Metrics
                    # -----------------------------

                    incident = metric_service.enrich(incident)

                    # -----------------------------
                    # Display Incident
                    # -----------------------------

                    print(incident)

                    print("\nImportant Metrics")
                    print("-" * 70)

                    if incident.metrics:

                        for metric in incident.metrics:

                            print(f"{metric.name}")

                            print(f"Key   : {metric.key}")

                            print(f"Value : {metric.lastvalue} {metric.units}")

                            print("-" * 40)

                    else:

                        print("No important metrics found.")

                    # =====================================
                    # NEXT STAGES
                    # =====================================

                    # incident = history_service.enrich(incident)

                    # incident = kb_service.enrich(incident)

                    # report = rca_service.generate(incident)

            print(f"\nWaiting {POLL_INTERVAL} seconds...\n")

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