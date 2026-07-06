from datetime import datetime


SEVERITY_MAP = {
    "0": "Not Classified",
    "1": "Information",
    "2": "Warning",
    "3": "Average",
    "4": "High",
    "5": "Disaster"
}


class Problem:

    def __init__(
        self,
        eventid,
        name,
        host,
        severity,
        clock,
        objectid=None
    ):

        self.eventid = eventid
        self.name = name
        self.host = host

        self.severity = SEVERITY_MAP.get(str(severity), "Unknown")

        if clock and str(clock).isdigit():
            self.clock = datetime.fromtimestamp(int(clock))
        else:
            self.clock = None

        self.objectid = objectid

    @property
    def formatted_time(self):
        if self.clock:
            return self.clock.strftime("%d-%m-%Y %H:%M:%S")
        return "N/A"

    def __str__(self):

        return f"""
==============================
Problem
==============================
Event ID : {self.eventid}
Host     : {self.host}
Problem  : {self.name}
Severity : {self.severity}
Time     : {self.formatted_time}
Trigger  : {self.objectid}
"""