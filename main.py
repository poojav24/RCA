"""
Near Zero Command Center — RCA Agent (live poll loop).

Uses the same LiveRuntime as server.py so HTTP APIs and the agent
share one Zabbix / ServiceNow / Loki / knowledge path.
"""

from services.live_runtime import POLL_INTERVAL, get_runtime


def main():
    print("=" * 70)
    print("Near Zero Command Center - RCA Agent Started (Live)")
    print("=" * 70)

    # start_poller=False — this process owns the blocking poll loop
    runtime = get_runtime(start_poller=False)

    print(f"Polling Zabbix every {POLL_INTERVAL} seconds")
    print("Status:", runtime.build_system_status())

    while True:
        try:
            runtime.poll_once()
        except KeyboardInterrupt:
            print("\nStopping RCA Agent...")
            break
        except Exception as exc:  # noqa: BLE001
            print("\nUnexpected Error:", exc)

        runtime.stop_event.wait(POLL_INTERVAL)


if __name__ == "__main__":
    main()
