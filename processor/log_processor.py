from collections import OrderedDict


class LogProcessor:

    def process(self, logs):

        if not logs:
            return []

        logs = self.remove_duplicates(logs)

        logs = self.sort_by_timestamp(logs)

        logs = self.remove_empty(logs)

        logs = self.keep_important(logs)

        return logs

    def remove_duplicates(self, logs):

        unique = OrderedDict()

        for log in logs:

            message = log["message"]

            if message not in unique:
                unique[message] = log

        return list(unique.values())

    def sort_by_timestamp(self, logs):

        return sorted(
            logs,
            key=lambda x: int(x["timestamp"])
        )

    def remove_empty(self, logs):

        return [
            log
            for log in logs
            if log["message"].strip()
        ]

    def keep_important(self, logs):

        important = []

        keywords = [

            "error",
            "failed",
            "critical",
            "panic",
            "fatal",
            "warning",
            "timeout",
            "denied",
            "exception"

        ]

        for log in logs:

            message = log["message"].lower()

            if any(word in message for word in keywords):
                important.append(log)

        if important:
            return important

        return logs[:50]