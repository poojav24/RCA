from playbooks.registry import PLAYBOOKS


class PlaybookService:

    def get_playbook(self, trigger):

        if not trigger.items:
            print("No trigger items found.")
            return None

        item = trigger.items[0]

        key = item["key"]

        item_key = key.split("[")[0]

        print("\nDetected Item Key :", item_key)

        if item_key in PLAYBOOKS:

            print("Playbook Found")

            return PLAYBOOKS[item_key]

        print("Unknown Item Key")

        return {
            "name": "Generic",
            "collector": "generic",
            "item_key": item_key
        }