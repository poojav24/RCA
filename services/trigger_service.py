class TriggerService:

    def __init__(self, zabbix):

        self.zabbix = zabbix

    def get_trigger(self, parsed_alert):

        event = self.zabbix.get_event(

            parsed_alert.original_problem_id

        )

        if event is None:

            return None

        triggers = self.zabbix.get_triggers()

        for trigger in triggers:

            if trigger.triggerid == event.objectid:

                return trigger

        return None