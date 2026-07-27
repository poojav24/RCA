class KnowledgeService:

    REUSE_SIMILARITY = 0.88
    STORE_SIMILARITY = 0.98

    def __init__(self, knowledge_repository):
        self.repository = knowledge_repository

    # ======================================================
    # Search Similar Historical Incidents
    # ======================================================

    def search(self, parsed_alert):

        results = self.repository.search(
            host=parsed_alert.host,
            problem=parsed_alert.problem
        )

        if not results:
            return None

        return results

    # ======================================================
    # Build Historical Context for LLM
    # ======================================================

    def build_context(self, similar_cases):

        if not similar_cases:
            return ""

        context = []

        for i, case in enumerate(similar_cases[:2], start=1):

            context.append(f"""
    Historical Incident {i}

    Problem:
    {case.get("problem")}

    Technology:
    {case.get("technology")}

    Root Cause:
    {case.get("root_cause")}

    Resolution:
    {"; ".join(case.get("recommended_resolution", []))}
    """)

        return "\n".join(context)
        # ======================================================
    # Decide Whether RCA Can Be Reused
    # ======================================================

    REUSE_SIMILARITY = 0.95
    ASSIST_SIMILARITY = 0.85


    def find_reusable_rca(
        self,
        similar_cases,
        technology,
        trigger_id,
        host
    ):

        if not similar_cases:
            return None

        for case in similar_cases:

            # Skip different technologies
            if case.get("technology") != technology:
                continue

            # Skip different trigger
            if str(case.get("trigger_id")) != str(trigger_id):
                continue

            similarity = float(
                case.get("similarity", 0)
            )

            if similarity >= ASSIST_SIMILARITY:

                return case

        return None

    # ======================================================
    # Decide Whether to Store in FAISS
    # ======================================================

    def should_store_new_incident(self, similar_cases):

        if not similar_cases:
            return True

        best = similar_cases[0]

        similarity = float(best.get("similarity", 0))

        return similarity < self.STORE_SIMILARITY