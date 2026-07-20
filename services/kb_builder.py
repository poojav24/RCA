import json


class KnowledgeBaseBuilder:

    def __init__(
        self,
        snow_client,
        evidence_builder,
        rca_service,
        repository
    ):
        self.snow = snow_client
        self.evidence_builder = evidence_builder
        self.rca_service = rca_service
        self.repository = repository

    def build(self):

        print("=" * 70)
        print("Building Knowledge Base")
        print("=" * 70)

        incidents = self.snow.get_zabbix_incidents()

        print(f"Found {len(incidents)} Zabbix incidents")

        processed = 0
        skipped = 0

        for incident in incidents:

            problem_id = incident.get("original_problem_id")

            if not problem_id:
                continue

            # Skip if RCA already exists
            if self.repository.get(problem_id):

                print(f"✓ {problem_id} already processed")

                skipped += 1
                continue

            print(f"Processing {problem_id}")

            # Build evidence directly from the incident
            evidence = {

                "host": incident.get("host"),

                "problem": incident.get("problem"),

                "severity": incident.get("severity"),

                "description": incident.get("description"),

                "work_notes": incident.get("work_notes"),

                "close_notes": incident.get("close_notes")

            }

            try:

                rca = self.rca_service.analyze(evidence)

                # Create a lightweight parsed alert object
                class Parsed:
                    pass

                parsed = Parsed()
                parsed.host = incident.get("host")
                parsed.problem = incident.get("problem")

                class Wrapper:
                    pass

                wrapper = Wrapper()
                wrapper.snow = {
                    "number": incident.get("number")
                }

                self.repository.save(

                    problem_id=problem_id,

                    incident=wrapper,

                    parsed_alert=parsed,

                    rca=rca

                )

                processed += 1

                print("✓ Stored")

            except Exception as ex:

                print("Failed :", ex)

        print()
        print("=" * 70)
        print("Knowledge Base Completed")
        print("=" * 70)

        print("Processed :", processed)
        print("Skipped   :", skipped)