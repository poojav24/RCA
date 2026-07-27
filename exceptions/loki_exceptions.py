class LokiHostNotFoundException(Exception):
    """Raised when the requested host is not configured in Loki."""
    pass