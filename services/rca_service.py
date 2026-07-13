import json


class RCAService:

    def __init__(self, grok_client):
        self.grok = grok_client

    def analyze(self, evidence):

        prompt = f"""
You are a Senior Site Reliability Engineer.

Analyze the following evidence and determine the most probable root cause.

Return ONLY valid JSON.

{{
    "root_cause": "",
    "confidence": 0.95,
    "impact": "",
    "reasoning": [
        ""
    ],
    "recommended_resolution": [
        ""
    ],
    "next_diagnostics": [
        ""
    ]
}}

Evidence

{json.dumps(evidence, indent=4, default=str)}
"""

        response = self.grok.generate(
            prompt,
            model="openai/gpt-oss-120b"
        )

        return json.loads(response)