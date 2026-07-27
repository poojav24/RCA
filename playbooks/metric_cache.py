import json
import os
import re

CACHE_DIR = "playbooks/metric_cache"

os.makedirs(CACHE_DIR, exist_ok=True)


def _filename(alert_name: str):

    name = alert_name.lower()

    name = re.sub(r'[^a-z0-9]+', '_', name)

    return os.path.join(
        CACHE_DIR,
        f"{name}.json"
    )


def exists(alert_name):

    return os.path.exists(
        _filename(alert_name)
    )


def load(alert_name):

    with open(
        _filename(alert_name),
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


def save(alert_name, playbook):

    with open(
        _filename(alert_name),
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            playbook,
            f,
            indent=4
        )