"""Safe, structured provider failures shared by feed adapters and publisher."""


class ProviderFailure(RuntimeError):
    """Provider failure with bounded diagnostic labels and no message data."""

    def __init__(self, stage, source=None, status_code=None):
        super().__init__("provider operation failed")
        self.stage = stage
        self.source = source
        self.status_code = status_code
