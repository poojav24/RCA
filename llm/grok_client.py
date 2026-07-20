import json
from openai import OpenAI
# from config import RCA_MODEL

class GrokClient:

    def __init__(self, api_key: str):

        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1"
        )

    def generate_playbook(
        self,
        alert_name,
        item_key,
        available_metrics
    ):

        metrics_text = "\n".join(available_metrics)

        prompt = f"""
You are a Senior Infrastructure Monitoring and Root Cause Analysis Engineer with expertise in:

- Zabbix Monitoring
- Windows Server
- Linux
- VMware
- Docker
- Kubernetes
- Nginx
- Apache
- IIS
- Redis
- MySQL
- PostgreSQL
- Oracle Database
- Network Infrastructure

Your responsibility is to determine the STANDARD set of monitoring metrics that should be collected for Root Cause Analysis (RCA) of the given alert.

A Zabbix alert has been triggered.

Alert:
{alert_name}

Triggered Item:
{item_key}

The following metrics are currently available on the affected host.

Available Zabbix Metrics:

{metrics_text}

Instructions:

1. Carefully analyze the alert and the triggered item.
2. Identify the affected technology.
3. Select the STANDARD RCA metrics that an experienced infrastructure engineer would collect for this type of issue.
4. Select metrics ONLY from the Available Zabbix Metrics list.
5. Never invent metric names.
6. Include service-specific metrics whenever applicable.
7. Include operating system metrics whenever relevant.
8. Ignore unrelated metrics.
9. Return every useful metric required for a complete RCA.
10. Explain why each metric is useful.
11. Assign priority (Critical, High, Medium).
12. Return ONLY valid JSON.

Return exactly in the following format:

{{
    "technology": "windows_service",
    "collector": "windows_service",
    "confidence": 0.96,
    "metrics": [
        {{
            "key": "service.info[\\"AppXSvc\\",state]",
            "reason": "Checks whether the AppXSvc service is currently running.",
            "priority": "Critical"
        }}
    ]
}}
"""

        response = self.client.chat.completions.create(
            model="openai/gpt-oss-20b",
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        content = response.choices[0].message.content.strip()

        if content.startswith("```"):
            content = (
                content
                .replace("```json", "")
                .replace("```", "")
                .strip()
            )

        try:
            return json.loads(content)

        except Exception:

            print("\nLLM RESPONSE\n")
            print(content)

            raise

    # =====================================================
    # Generic LLM Method
    # Used by LogSummarizer and future RCA Engine
    # =====================================================

    def generate(
        self,
        prompt: str,
        model="openai/gpt-oss-120b"
    ):

        response = self.client.chat.completions.create(
            model=model,
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        return response.choices[0].message.content.strip()