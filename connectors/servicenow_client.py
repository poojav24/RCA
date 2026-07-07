import requests
from datetime import datetime, timedelta


class ServiceNowClient:

    def __init__(self, base_url, username, password):

        self.base_url = base_url
        self.username = username
        self.password = password

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

    def correlate_incident(
        self,
        host,
        problem,
        started_time
    ):

        # Convert string to datetime if needed
        if isinstance(started_time, str):

            try:
                started_time = datetime.strptime(
                    started_time,
                    "%Y-%m-%d %H:%M:%S"
                )
            except:
                pass

        # Optional time window (currently not used in query)
        if isinstance(started_time, datetime):
            start = started_time - timedelta(minutes=2)
            end = started_time + timedelta(minutes=2)

        query = (
            f"descriptionLIKE{host}"
            f"^short_descriptionLIKE{problem}"
        )

        params = {

        "sysparm_query": query,

        "sysparm_limit": 5,

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

        return self._get(
            "/api/now/table/incident",
            params
        )