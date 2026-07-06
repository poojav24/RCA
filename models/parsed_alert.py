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

        original_problem_id

    ):

        self.alertid = alertid
        self.eventid = eventid

        self.host = host
        self.problem = problem
        self.severity = severity
        self.operational_data = operational_data

        # KEEP DATETIME OBJECT
        self.started_time = started_time

        self.original_problem_id = original_problem_id

    def __str__(self):

        return f"""

==================================================

Host              : {self.host}

Problem           : {self.problem}

Severity          : {self.severity}

Operational Data  : {self.operational_data}

Started           : {self.started_time}

Problem ID        : {self.original_problem_id}

==================================================
"""