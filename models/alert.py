from datetime import datetime


class Alert:

    def __init__(
        self,
        alertid,
        eventid,
        clock,
        subject,
        message,
        status,
        sendto,
        actionid
    ):

        self.alertid = alertid
        self.eventid = eventid
        self.actionid = actionid
        self.sendto = sendto
        self.status = status
        self.subject = subject
        self.message = message
        self.clock = datetime.fromtimestamp(int(clock))

    def __str__(self):

        return f"""
==================================================

Alert ID   : {self.alertid}

Event ID   : {self.eventid}

Time       : {self.clock.strftime('%d-%m-%Y %H:%M:%S')}

Subject    : {self.subject}

Status     : {self.status}

Send To    : {self.sendto}

==================================================
"""