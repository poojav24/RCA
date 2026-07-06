from models.alert import Alert


class AlertService:

    def __init__(self, zabbix):

        self.zabbix = zabbix

    def get_new_alerts(self):

        alerts = []

        data = self.zabbix.get_alerts()

        for row in data:

            alert = Alert(

                alertid=row["alertid"],

                eventid=row["eventid"],

                clock=row["clock"],

                subject=row["subject"],

                message=row["message"],

                status=row["status"],

                sendto=row["sendto"],

                actionid=row["actionid"]

            )

            alerts.append(alert)

        return alerts