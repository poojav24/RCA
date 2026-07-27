class TriggerService:

    def __init__(self, zabbix):
        self.zabbix = zabbix

    def get_trigger(self, parsed_alert):

        print("\nFinding Trigger...")

        # Original Problem ID itself is the Event ID
        event = self.zabbix.get_event(
            parsed_alert.original_problem_id
        )

        if event is None:
            print("Event not found.")
            return None

        print("Event Found")
        print("Trigger ID :", event.objectid)

        trigger = self.zabbix.get_trigger(
            event.objectid
        )

        if trigger is None:
            print("Trigger not found.")
            return None

        print("Trigger Found")

        return trigger