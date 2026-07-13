class MetricService:

    def __init__(self, zabbix):

        self.zabbix = zabbix

    def collect(self, incident, trigger, playbook):

        print("\nCollecting Metrics...")

        host = incident.alert.host

        hosts = self.zabbix.get_hosts()

        hostid = None

        for h in hosts:

            if h.host == host or h.name == host:
                hostid = h.hostid
                break

        if hostid is None:

            print("Host not found.")

            return incident

        all_metrics = self.zabbix.get_metrics(hostid)

        collected = []

        trigger_key = ""

        if trigger.items:
            trigger_key = trigger.items[0]["key"]

        for metric_info in playbook["metrics"]:

            required_key = metric_info["key"]

            # Exact match for the triggered service metric
            if required_key == "service.info":

                for metric in all_metrics:

                    if metric.key == trigger_key:

                        collected.append(metric)
                        break

            else:

                for metric in all_metrics:

                    if (
                        metric.key == required_key
                        or
                        metric.key.startswith(required_key)
                    ):

                        collected.append(metric)
                        break

        incident.metrics = collected

        return incident