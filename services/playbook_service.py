from playbooks.metric_cache import exists, load, save


class PlaybookService:

    def __init__(
        self,
        zabbix,
        grok
    ):
        self.zabbix = zabbix
        self.grok = grok

    def get_playbook(self, trigger):

        if not trigger.items:
            print("Trigger has no items.")
            return None

        item_key = trigger.items[0]["key"]
        hostid = trigger.items[0]["hostid"]
        alert_name = trigger.description

        print("\n" + "=" * 60)
        print("PLAYBOOK SERVICE")
        print("=" * 60)
        print(f"Alert    : {alert_name}")
        print(f"Item Key : {item_key}")

        # --------------------------------------------------
        # Step 1 - Check Metric Cache
        # --------------------------------------------------

        if exists(alert_name):

            print("✅ Metric Cache Found")

            return load(alert_name)

        print("⚠ Metric Cache Not Found")

        # --------------------------------------------------
        # Step 2 - Fetch Available Metrics
        # --------------------------------------------------

        print("Fetching available metrics from Zabbix...")

        available_metrics = self.zabbix.get_available_metric_keys(hostid)

        print(f"Available Metrics : {len(available_metrics)}")

        # --------------------------------------------------
        # Step 3 - Ask LLM
        # --------------------------------------------------

        playbook = self.grok.generate_playbook(
            alert_name,
            item_key,
            available_metrics
        )

        # --------------------------------------------------
        # Step 4 - Save Metric Cache
        # --------------------------------------------------

        save(
            alert_name,
            playbook
        )

        print("✅ Metric Cache Saved")

        return playbook