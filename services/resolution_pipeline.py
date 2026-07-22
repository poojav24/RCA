from services.correlation_service import CorrelationService


class ResolutionPipeline:

    def __init__(
        self,
        correlation_service,
        repository,
        snow,
        dedup_repository
    ):

        self.correlation_service = correlation_service
        self.repository = repository
        self.snow = snow
        self.dedup_repository = dedup_repository

    # ==========================================================
    # Resolution Pipeline
    # ==========================================================

    def run(self, parsed):

        print()
        print("=" * 70)
        print("RESOLUTION PIPELINE")
        print("=" * 70)

        incident = self.correlation_service.correlate(parsed)

        print()
        print("=" * 70)
        print("SERVICENOW INCIDENT")
        print("=" * 70)

        if incident.snow:

            snow = incident.snow

            print("Incident Number   :", snow.get("number"))
            print("Short Description :", snow.get("short_description"))
            print("Priority          :", snow.get("priority"))
            print("Severity          :", snow.get("severity"))
            print("State             :", snow.get("state"))
            print("Assignment Group  :", snow.get("assignment_group"))
            print("Assigned To       :", snow.get("assigned_to"))
            print("Opened By         :", snow.get("opened_by"))
            print("Opened At         :", snow.get("opened_at"))
            print("Category          :", snow.get("category"))
            print("Subcategory       :", snow.get("subcategory"))

        else:

            print("No matching ServiceNow Incident Found.")
            return

        # ==========================================================
        # Load Stored RCA
        # ==========================================================

        print("\nLoading RCA...")

        rca = self.repository.get(parsed.original_problem_id)

        if rca:

            print("✓ RCA found using Problem ID")

        else:

            print("Problem ID not found.")

            print("Trying Host + Problem...")

            rca = self.repository.get_by_host_problem(
                parsed.host,
                parsed.problem
            )

            if rca:
                print("✓ RCA found using Host + Problem")

        if rca is None:

            print("=" * 70)
            print("No RCA available.")
            print("Skipping ServiceNow update.")
            print("=" * 70)

            return

        self.snow.update_resolution(

            incident_number=incident.snow["number"],

            rca=rca

        )
        print("✓ Incident updated successfully.")

        # ==========================================================
        # Mark Duplicate Record as Resolved
        # ==========================================================

        if self.dedup_repository:
            self.dedup_repository.resolve(
                parsed.host,
                parsed.problem
            )