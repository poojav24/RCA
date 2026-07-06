class Event:

    def __init__(

        self,

        eventid,

        objectid,

        object,

        clock

    ):

        self.eventid = eventid

        self.objectid = objectid

        self.object = object

        self.clock = clock

    def __str__(self):

        return f"""
Event ID : {self.eventid}

Trigger ID : {self.objectid}

Object Type : {self.object}

Clock : {self.clock}
"""