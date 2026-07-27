from models.incident import Incident


class CorrelationService:

    def __init__(self, snow):

        self.snow = snow

    def correlate(self, parsed_alert):

        incident = Incident(parsed_alert)

        matches = self.snow.correlate_incident(

            original_problem_id=parsed_alert.original_problem_id,
            host=parsed_alert.host,
            problem=parsed_alert.problem,
            started_time=parsed_alert.started_time
        )
        if matches:

            incident.snow = matches[0]
            print("✓ Matching ServiceNow Incident Found")

        else:

            print("✗ No Matching ServiceNow Incident")

        return incident