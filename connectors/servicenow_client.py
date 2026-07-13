import requests
from datetime import datetime


class ServiceNowClient:

    def __init__(self, base_url, username, password):

        self.base_url = base_url
        self.username = username
        self.password = password

    # ==========================================================
    # Generic GET
    # ==========================================================

    def _get(self, endpoint, params=None):

        url = self.base_url + endpoint

        response = requests.get(
            url,
            auth=(self.username, self.password),
            headers={
                "Accept": "application/json"
            },
            params=params
        )

        response.raise_for_status()

        return response.json()["result"]

    # ==========================================================
    # Correlate Incident
    # ==========================================================

    def correlate_incident(
        self,
        original_problem_id,
        host,
        problem,
        started_time
    ):

        # Convert string to datetime if required
        if isinstance(started_time, str):

            try:
                started_time = datetime.strptime(
                    started_time,
                    "%Y-%m-%d %H:%M:%S"
                )
            except Exception:
                pass

        # ------------------------------------------------------
        # First search using Original Problem ID
        # ------------------------------------------------------

        query = (
            f"descriptionLIKEOriginal problem ID: {original_problem_id}"
        )

        params = {

            "sysparm_query": query,

            "sysparm_limit": 1,

            "sysparm_display_value": "true",

            "sysparm_fields": ",".join([

                "number",
                "short_description",
                "priority",
                "severity",
                "state",
                "assignment_group",
                "assigned_to",
                "opened_by",
                "opened_at",
                "category",
                "subcategory"

            ])

        }

        result = self._get(
            "/api/now/table/incident",
            params
        )

        # ------------------------------------------------------
        # Found exact incident
        # ------------------------------------------------------

        if result:
            return result

        # ------------------------------------------------------
        # Fallback using Host + Problem
        # ------------------------------------------------------

        query = (
            f"descriptionLIKE{host}"
            f"^short_descriptionLIKE{problem}"
        )

        params["sysparm_query"] = query

        return self._get(
            "/api/now/table/incident",
            params
        )