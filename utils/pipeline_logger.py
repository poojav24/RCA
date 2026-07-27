class PipelineLogger:

    @staticmethod
    def header(title):

        print()
        print("=" * 60)
        print(title)
        print("=" * 60)

    @staticmethod
    def key_value(key, value):

        print(f"{key:<18}: {value}")

    @staticmethod
    def success(message):

        print(f"✓ {message}")

    @staticmethod
    def warning(message):

        print(f"⚠ {message}")

    @staticmethod
    def info(message):

        print(f"• {message}")