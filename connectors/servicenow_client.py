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
    # Generic PATCH
    # ==========================================================

    def _patch(self, endpoint, payload):

        url = self.base_url + endpoint

        response = requests.patch(
            url,
            auth=(self.username, self.password),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            json=payload
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

        if isinstance(started_time, str):

            try:

                started_time = datetime.strptime(
                    started_time,
                    "%Y-%m-%d %H:%M:%S"
                )

            except Exception:
                pass

        # ------------------------------------------------------
        # Search using Original Problem ID
        # ------------------------------------------------------

        query = (
            f"descriptionLIKEOriginal problem ID: {original_problem_id}"
        )

        params = {

            "sysparm_query": query,

            "sysparm_limit": 1,

            "sysparm_display_value": "true",

            "sysparm_fields": ",".join([

                "sys_id",
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

        if result:
            return result

        # ------------------------------------------------------
        # Fallback Search
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

    # ==========================================================
    # Update Incident with AI RCA
    # ==========================================================

    def update_resolution(

        self,

        incident_number,

        rca

    ):

        query = f"number={incident_number}"

        result = self._get(

            "/api/now/table/incident",

            {

                "sysparm_query": query,

                "sysparm_limit": 1,

                "sysparm_display_value": "true"

            }

        )

        if not result:

            print("Incident not found.")

            return

        sys_id = result[0]["sys_id"]

        # -------------------------------------------------
        # Build AI RCA Report
        # -------------------------------------------------

        reasoning = "\n".join(

            f"• {item}"

            for item in rca.get("reasoning", [])

        )

        remediation = "\n".join(

            f"• {item}"

            for item in rca.get("recommended_resolution", [])

        )

        diagnostics = "\n".join(

            f"• {item}"

            for item in rca.get("next_diagnostics", [])

        )

        notes = f"""
==========================
AI RCA ANALYSIS
==========================

Root Cause
----------
{rca.get("root_cause", "")}

Confidence
----------
{rca.get("confidence", "")}

Impact
------
{rca.get("impact", "")}

Reasoning
---------
{reasoning}

AI Recommended Remediation
--------------------------
{remediation}

Next Diagnostics
----------------
{diagnostics}

Generated Automatically by RCA Agent
"""

        body = {

            "u_root_cause": notes,

            "caller_id": "6816f79cc0a8016401c5a33be04be441",

            "state": "6"      # Resolved

        }

        updated = self._patch(

            f"/api/now/table/incident/{sys_id}",

            body

        )

        print()

        print("=" * 70)
        print("SERVICENOW UPDATE STATUS")
        print("=" * 70)

        print("Incident Number :", incident_number)

        print("Root Cause      : Updated")

        # Verify returned state
        state = str(updated.get("state", ""))

        if state in ("6", "Resolved"):

            print("Incident State  : Resolved ✓")
            print("Status          : Incident successfully moved to Resolved state.")

        else:

            print("Incident State  :", updated.get("state"))
            print("Status          : Root Cause updated but incident was NOT moved to Resolved state.")