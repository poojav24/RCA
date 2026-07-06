class MetricService:

    def __init__(self, zabbix):

        self.zabbix = zabbix

    def enrich(self, incident):

        host = incident.alert.host

        hosts = self.zabbix.get_hosts()

        hostid = None

        for h in hosts:

            if h.host == host or h.name == host:

                hostid = h.hostid
                break

        if hostid is None:

            print("Host not found in Zabbix.")

            return incident

        metrics = self.zabbix.get_rca_metrics(hostid)

        incident.metrics = metrics

        return incident