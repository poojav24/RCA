import os

# Live integration endpoints — override with environment variables in real deployments.
ZABBIX_URL = os.environ.get("ZABBIX_URL", "http://zabbix.mfgitis.tcs/api_jsonrpc.php")
USERNAME = os.environ.get("ZABBIX_USERNAME", "Admin")
PASSWORD = os.environ.get("ZABBIX_PASSWORD", "zabbix")

SNOW_INSTANCE = os.environ.get("SNOW_INSTANCE", "dev187880")
SNOW_USERNAME = os.environ.get("SNOW_USERNAME", "admin")
SNOW_PASSWORD = os.environ.get("SNOW_PASSWORD", "wEA$up08pX=S")
SNOW_BASE_URL = os.environ.get(
    "SNOW_BASE_URL",
    f"https://{SNOW_INSTANCE}.service-now.com",
)

GROK_API_KEY = os.environ.get(
    "GROK_API_KEY",
    "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",
)

LOKI_URL = os.environ.get("LOKI_URL", "http://172.19.0.9:3100")
