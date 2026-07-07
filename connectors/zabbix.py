import requests

from models.host import Host
from models.problem import Problem
from models.trigger import Trigger
from models.metric import Metric
from models.events import Event


class ZabbixClient:

    def __init__(self, url, username, password):

        self.url = url
        self.username = username
        self.password = password
        self.auth = None

    # ==========================================================
    # Login
    # ==========================================================

    def login(self):

        payload = {

            "jsonrpc": "2.0",

            "method": "user.login",

            "params": {

                "username": self.username,

                "password": self.password

            },

            "id": 1

        }

        response = requests.post(

            self.url,

            json=payload

        )

        response.raise_for_status()

        result = response.json()

        if "result" in result:

            self.auth = result["result"]

            print("Login Successful")

        else:

            raise Exception(result)

    # ==========================================================
    # Generic Request
    # ==========================================================

    def _request(self, method, params, request_id):

        payload = {

            "jsonrpc": "2.0",

            "method": method,

            "params": params,

            "auth": self.auth,

            "id": request_id

        }

        response = requests.post(

            self.url,

            json=payload

        )

        response.raise_for_status()

        result = response.json()

        if "error" in result:

            raise Exception(result["error"])

        return result["result"]

    # ==========================================================
    # Hosts
    # ==========================================================

    def get_hosts(self):

        data = self._request(

            "host.get",

            {

                "output": [

                    "hostid",

                    "host",

                    "name",

                    "status",

                    "description"

                ]

            },

            2

        )

        hosts = []

        for h in data:

            hosts.append(

                Host(

                    h["hostid"],

                    h["host"],

                    h["name"],

                    h["status"],

                    h.get("description")

                )

            )

        return hosts

    # ==========================================================
    # Problems
    # ==========================================================

    def get_problems(self):

        data = self._request(

            "problem.get",

            {

                "output": "extend"

            },

            3

        )

        problems = []

        for p in data:

            problems.append(

                Problem(

                    p["eventid"],

                    p["name"],

                    p["severity"],

                    p["clock"],

                    p["objectid"]

                )

            )

        return problems

    # ==========================================================
    # Trigger
    # ==========================================================

    def get_trigger(self, triggerid):

        data = self._request(

            "trigger.get",

            {

                "triggerids": triggerid,

                "output": [

                    "triggerid",

                    "description",

                    "priority",

                    "status",

                    "expression"

                ],

                "selectItems": [

                    "itemid",

                    "name",

                    "key_"

                ]

            },

            8

        )

        if not data:

            return None

        t = data[0]

        items = []

        for item in t.get("items", []):

            items.append(

                {

                    "itemid": item["itemid"],

                    "name": item["name"],

                    "key": item["key_"]

                }

            )

        return Trigger(

            t["triggerid"],

            t["description"],

            t["priority"],

            t["status"],

            t["expression"],

            items

        )

    # ==========================================================
    # Metrics
    # ==========================================================

    def get_metrics(self, hostid):

        data = self._request(
            "item.get",
            {
                "hostids": hostid,
                "output": [
                    "itemid",
                    "name",
                    "key_",
                    "lastvalue",
                    "units",
                    "value_type"
                ]
            },
            5
        )
        metrics = []

        for item in data:
            metrics.append(
                Metric(
                    item["itemid"],
                    item["name"],
                    item["key_"],
                    item["value_type"],
                    item.get("units", ""),
                    item.get("lastvalue", "")
                )
            )
        return metrics

    # ==========================================================
    # Important Metrics
    # ==========================================================

    def get_rca_metrics(self, hostid):
        metrics = self.get_metrics(hostid)
        keywords = [
            "cpu",
            "memory",
            "mem",
            "disk",
            "filesystem",
            "swap",
            "network",
            "net",
            "service",
            "process",
            "load"
        ]
        important = []
        for metric in metrics:
            text = (
                metric.name +
                " " +
                metric.key
            ).lower()
            if any(word in text for word in keywords):
                important.append(metric)
        return important

    # ==========================================================
    # Alerts
    # ==========================================================

    def get_alerts(self, limit=20):
        data = self._request(
            "alert.get",
            {
                "output": "extend",
                "sortfield": "clock",
                "sortorder": "DESC",
                "limit": limit
            },
            6
        )
        return data

    # ==========================================================
    # Event
    # ==========================================================

    def get_event(self, eventid):

        data = self._request(

            "event.get",

            {

                "eventids": eventid,

                "output": "extend"

            },

            7

        )

        if not data:

            return None

        e = data[0]

        return Event(

            e["eventid"],

            e["objectid"],

            e["object"],

            e["clock"]

        )