import json
# from config import RCA_MODEL

class LogSummarizer:

    def __init__(self, grok_client):

        self.grok = grok_client

    def summarize(self, logs):

        if not logs:
            return None

        text = "\n".join(

            log["message"]

            for log in logs

        )

        prompt = f"""
You are a Linux and Windows log analysis expert.

Summarize these logs.

Return JSON only.

{{
    "summary":"",
    "key_errors":[]
}}

Logs

{text}
"""

        response = self.grok.generate(prompt)

        try:
            return json.loads(response)

        except Exception:

            return {

                "summary": response,

                "key_errors": []

            }