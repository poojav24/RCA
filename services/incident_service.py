from models.incident import Incident


class IncidentService:

    def __init__(self, zabbix):

        self.zabbix = zabbix

    def build_incidents(self):

        incidents = []

        problems = self.zabbix.get_problems()

        for problem in problems:

            incident = Incident(problem)

            incidents.append(incident)

        return incidents