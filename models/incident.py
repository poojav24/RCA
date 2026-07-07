class Incident:

    def __init__(self, parsed_alert):

        self.alert = parsed_alert

        self.snow = None

        self.trigger = None

        self.playbook = None

        self.metrics = []

        self.history = []

        self.kb_articles = []

        self.rca = None

    def __str__(self):

        text = "\n"

        text += "=" * 70 + "\n"
        text += "INCIDENT SUMMARY\n"
        text += "=" * 70 + "\n\n"

        text += f"Host      : {self.alert.host}\n"
        text += f"Problem   : {self.alert.problem}\n"
        text += f"Severity  : {self.alert.severity}\n"
        text += f"Started   : {self.alert.started_time}\n"

        if self.trigger:

            text += "\nTrigger\n"
            text += "-" * 30 + "\n"
            text += self.trigger.description + "\n"

        if self.playbook:

            text += "\nPlaybook\n"
            text += "-" * 30 + "\n"
            text += self.playbook["name"] + "\n"

        if self.snow:

            text += "\nServiceNow\n"
            text += "-" * 30 + "\n"
            text += f"Incident : {self.snow.get('number')}\n"

        return text