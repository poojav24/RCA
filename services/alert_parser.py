from datetime import datetime

from models.parsed_alert import ParsedAlert


class AlertParser:

    def parse(self, alert):

        host = ""
        problem = ""
        severity = ""
        operational_data = ""
        started_time = None
        problem_id = ""

        # ------------------------------------------------------
        # Detect Event Type
        # ------------------------------------------------------

        event_type = "PROBLEM"

        subject = alert.subject.lower()
        message = alert.message.lower()

        if (
            "resolved" in subject or
            "recovered" in subject or
            "recovery" in subject or
            "resolved" in message or
            "recovered" in message or
            "problem has been resolved" in message
        ):
            event_type = "RESOLVED"

        # ------------------------------------------------------
        # Parse Alert Message
        # ------------------------------------------------------

        lines = alert.message.splitlines()

        for line in lines:

            line = line.strip()

            if line.startswith("Problem started at"):

                time_text = line.replace(
                    "Problem started at",
                    ""
                ).strip()

                started_time = datetime.strptime(
                    time_text,
                    "%H:%M:%S on %Y.%m.%d"
                )

            elif line.startswith("Problem name:"):

                problem = line.replace(
                    "Problem name:",
                    ""
                ).strip()

            elif line.startswith("Host:"):

                host = line.replace(
                    "Host:",
                    ""
                ).strip()

            elif line.startswith("Severity:"):

                severity = line.replace(
                    "Severity:",
                    ""
                ).strip()

            elif line.startswith("Operational data:"):

                operational_data = line.replace(
                    "Operational data:",
                    ""
                ).strip()

            elif line.startswith("Original problem ID:"):

                problem_id = line.replace(
                    "Original problem ID:",
                    ""
                ).strip()

        return ParsedAlert(

            alertid=alert.alertid,

            eventid=alert.eventid,

            host=host,

            problem=problem,

            severity=severity,

            operational_data=operational_data,

            started_time=started_time,

            original_problem_id=problem_id,

            event_type=event_type

        )