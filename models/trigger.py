class Trigger:

    def __init__(
        self,
        triggerid,
        description,
        priority,
        status,
        expression,
        items=None
    ):

        self.triggerid = triggerid
        self.description = description
        self.priority = priority
        self.status = status
        self.expression = expression
        self.items = items or []

    def __str__(self):

        text = "\n"
        text += "=" * 70 + "\n"
        text += "TRIGGER\n"
        text += "=" * 70 + "\n"

        text += f"Trigger ID : {self.triggerid}\n"
        text += f"Description: {self.description}\n"
        text += f"Priority   : {self.priority}\n"
        text += f"Status     : {self.status}\n"
        text += f"Expression : {self.expression}\n"

        text += "\nTrigger Items\n"
        text += "-" * 40 + "\n"

        if self.items:

            for item in self.items:

                text += f"{item['name']}\n"
                text += f"Key : {item['key']}\n\n"

        else:

            text += "No Items\n"

        return text