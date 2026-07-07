import time
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

print("Using:", connectors.zabbix.__file__)

POLL_INTERVAL = 60


def main():

    print("=" * 70)
    print("Near Zero Command Center - RCA Agent Started")
    print("=" * 70)

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

    alert_service = AlertService(zabbix)
    parser = AlertParser()
    correlation_service = CorrelationService(snow)
    trigger_service = TriggerService(zabbix)
    playbook_service = PlaybookService()
    metric_service = MetricService(zabbix)

    processed_alerts = set()

    while True:

        try:

            print("=" * 70)
            print(
                f"Polling Alerts : {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}"
            )
            print("=" * 70)

            alerts = alert_service.get_new_alerts()

            for alert in alerts:

                if alert.alertid in processed_alerts:
                    continue

                processed_alerts.add(alert.alertid)

                parsed = parser.parse(alert)

                incident = correlation_service.correlate(parsed)

                trigger = trigger_service.get_trigger(parsed)

                if trigger is None:
                    continue

                playbook = playbook_service.get_playbook(trigger)

                if playbook is None:
                    continue

                incident = metric_service.collect(
                    incident,
                    trigger,
                    playbook
                )
                print()

                print("=" * 70)
                print("SERVICENOW INCIDENT")
                print("=" * 70)

                if incident.snow:

                    snow = incident.snow

                    print("Incident Number   :", snow.get("number"))
                    print("Short Description :", snow.get("short_description"))
                    print("Priority          :", snow.get("priority"))
                    print("Severity          :", snow.get("severity"))
                    print("State             :", snow.get("state"))
                    print("Assignment Group  :", snow.get("assignment_group"))
                    print("Assigned To       :", snow.get("assigned_to"))
                    print("Opened By         :", snow.get("opened_by"))
                    print("Opened At         :", snow.get("opened_at"))
                    print("Category          :", snow.get("category"))
                    print("Subcategory       :", snow.get("subcategory"))

                else:

                    print("No matching ServiceNow incident found.")

                print("\nCollected Metrics\n")

                for metric in incident.metrics:
                    print(metric)

            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            break

        except Exception as e:
            print(e)
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()