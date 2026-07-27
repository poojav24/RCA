from datetime import datetime


class ParsedAlert:

    def __init__(

        self,

        alertid,

        eventid,

        host,

        problem,

        severity,

        operational_data,

        started_time,

        original_problem_id,

        event_type

    ):

        self.alertid = alertid
        self.eventid = eventid

        self.host = host
        self.problem = problem
        self.severity = severity
        self.operational_data = operational_data

        self.started_time = started_time

        self.original_problem_id = original_problem_id

        self.event_type = event_type

    def __str__(self):

        return f"""

==================================================

Event Type        : {self.event_type}

Host              : {self.host}

Problem           : {self.problem}

Severity          : {self.severity}

Operational Data  : {self.operational_data}

Started           : {self.started_time}

Problem ID        : {self.original_problem_id}

==================================================
"""