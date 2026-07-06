class Trigger:

    def __init__(
        self,
        triggerid,
        description,
        priority,
        status,
        expression
    ):

        self.triggerid = triggerid
        self.description = description
        self.priority = priority
        self.status = status
        self.expression = expression

    def __str__(self):

        return (
            f"""
Trigger ID : {self.triggerid}
Description: {self.description}
Priority   : {self.priority}
Status     : {self.status}
Expression : {self.expression}
"""
        )