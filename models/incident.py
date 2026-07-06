class Incident:

    def __init__(self, parsed_alert):

        self.alert = parsed_alert

        self.snow = None

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

        if self.snow:

            text += "\n"

            text += "ServiceNow\n"

            text += "-" * 40 + "\n"

            text += f"Number    : {self.snow.get('number')}\n"

            text += f"Priority  : {self.snow.get('priority')}\n"

            text += f"State     : {self.snow.get('state')}\n"

        return text