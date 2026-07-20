import json


class EvidenceBuilder:

    def build(
        self,
        parsed_alert,
        incident,
        trigger,
        playbook,
        log_summary,
        logs_available
    ):

        evidence = {

            "incident": {

                "host": parsed_alert.host,
                "problem": parsed_alert.problem,
                "severity": parsed_alert.severity,
                "started_time": str(parsed_alert.started_time),
                "original_problem_id": parsed_alert.original_problem_id

            },

            "servicenow": incident.snow,

            "trigger": {
                "triggerid": getattr(trigger, "triggerid", None),
                "description": getattr(trigger, "description", None)
            },

            "playbook": playbook,

            "metrics": [

                {
                    "name": m.name,
                    "key": m.key,
                    "value": m.lastvalue,
                    "units": m.units
                }

                for m in incident.metrics

            ],

            "logs": {

                "available": logs_available,
                "summary": log_summary

            }

        }

        return evidence

    def to_json(self, evidence):

        return json.dumps(
            evidence,
            indent=4,
            default=str
        )