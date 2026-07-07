class Event:

    def __init__(
        self,
        eventid,
        objectid,
        object,
        clock
    ):

        self.eventid = eventid
        self.objectid = objectid      # Trigger ID
        self.object = object
        self.clock = clock

    def __str__(self):

        return f"""
==============================
EVENT
==============================
Event ID   : {self.eventid}
Trigger ID : {self.objectid}
Object     : {self.object}
Clock      : {self.clock}
"""