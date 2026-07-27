class MetricValidator:

    def __init__(self, zabbix):
        self.zabbix = zabbix

    def validate(self, hostid, metrics):

        print("\n" + "=" * 60)
        print("VALIDATING METRICS")
        print("=" * 60)

        valid_metrics = []

        for metric in metrics:

            # LLM may return either a string or a dict
            if isinstance(metric, dict):
                key = metric.get("key")
            else:
                key = metric

            if not key:
                continue

            print(f"Checking : {key}")

            try:

                item = self.zabbix.get_item_by_key(
                    hostid,
                    key
                )

                if item:

                    print("   ✓ Available")

                    valid_metrics.append(key)

                else:

                    print("   ✗ Not Available")

            except Exception as e:

                print(f"   Error : {e}")

        print("-" * 60)
        print(f"Valid Metrics : {len(valid_metrics)}")
        print("-" * 60)

        return valid_metrics