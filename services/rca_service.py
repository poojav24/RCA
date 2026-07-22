import json
import time
import traceback


class RCAService:

    def __init__(self, grok_client):
        self.grok = grok_client

    def _field_size_rows(self, evidence):

        rows = []

        for key, value in evidence.items():

            serialized_value = json.dumps(
                value,
                indent=4,
                default=str
            )

            rows.append(
                (
                    key,
                    len(serialized_value),
                    len(serialized_value.encode("utf-8"))
                )
            )

        rows.sort(
            key=lambda item: item[1],
            reverse=True
        )

        return rows

    def analyze(self, evidence):

        analysis_started = time.perf_counter()

        serialization_started = time.perf_counter()

        evidence_json = json.dumps(
            evidence,
            indent=4,
            default=str
        )

        serialization_elapsed = time.perf_counter() - serialization_started

        prompt_started = time.perf_counter()

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

{evidence_json}
"""

        prompt_elapsed = time.perf_counter() - prompt_started

        prompt_chars = len(prompt)
        prompt_bytes = len(prompt.encode("utf-8"))
        prompt_tokens = max(1, round(prompt_chars / 4))

        print("\n[RCA DEBUG] Prompt construction", flush=True)
        print(
            f"[RCA DEBUG] JSON serialization: {serialization_elapsed * 1000:.2f} ms",
            flush=True
        )
        print(
            f"[RCA DEBUG] Prompt assembly: {prompt_elapsed * 1000:.2f} ms",
            flush=True
        )
        print(
            f"[RCA DEBUG] Prompt size in characters: {prompt_chars}",
            flush=True
        )
        print(
            f"[RCA DEBUG] Prompt size in bytes: {prompt_bytes}",
            flush=True
        )
        print(
            f"[RCA DEBUG] Approximate token count: {prompt_tokens}",
            flush=True
        )
        print("[RCA DEBUG] Prompt field contributions:", flush=True)

        for key, char_count, byte_count in self._field_size_rows(evidence):
            print(
                f"[RCA DEBUG]   {key}: {char_count} chars / {byte_count} bytes",
                flush=True
            )

        request_started = time.perf_counter()

        print("[RCA DEBUG] Grok API request started.", flush=True)

        response = self.grok.generate(
            prompt,
            model="openai/gpt-oss-120b"
        )

        api_latency = time.perf_counter() - request_started

        response_chars = len(response) if response else 0
        response_bytes = len(response.encode("utf-8")) if response else 0

        print(
            f"[RCA DEBUG] Grok API latency: {api_latency * 1000:.2f} ms",
            flush=True
        )
        print(
            f"[RCA DEBUG] Response size: {response_chars} chars / {response_bytes} bytes",
            flush=True
        )

        parsing_started = time.perf_counter()

        try:

            parsed_response = json.loads(response)

        except Exception:

            print("[RCA DEBUG] Grok response parsing failed.", flush=True)
            print(
                f"[RCA DEBUG] Grok response parsing: {(time.perf_counter() - parsing_started) * 1000:.2f} ms",
                flush=True
            )
            traceback.print_exc()
            raise

        parsing_elapsed = time.perf_counter() - parsing_started

        print(
            f"[RCA DEBUG] Grok response parsing: {parsing_elapsed * 1000:.2f} ms",
            flush=True
        )
        print(
            f"[RCA DEBUG] RCA analysis total: {(time.perf_counter() - analysis_started) * 1000:.2f} ms",
            flush=True
        )

        return parsed_response
