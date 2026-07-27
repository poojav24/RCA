import json
import os
import re
from pathlib import Path

CACHE_DIR = Path(__file__).resolve().parent
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _filename(alert_name: str):
    name = alert_name.lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    return str(CACHE_DIR / f"{name}.json")


def exists(alert_name):
    return os.path.exists(_filename(alert_name))


def load(alert_name):
    with open(_filename(alert_name), "r", encoding="utf-8") as f:
        return json.load(f)


def save(alert_name, playbook):
    with open(_filename(alert_name), "w", encoding="utf-8") as f:
        json.dump(playbook, f, indent=4)
