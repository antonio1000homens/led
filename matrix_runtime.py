"""Pure runtime mode state for the MatrixPortal application."""


DIAGNOSTIC_COLORS = (
    ("RED", 0x400000),
    ("GREEN", 0x004000),
    ("BLUE", 0x000040),
    ("WHITE", 0x202020),
    ("BLACK", 0x000000),
)


class RuntimeMode:
    """Track normal/diagnostic mode without depending on CircuitPython APIs."""

    def __init__(self):
        self.mode = "normal"
        self.diagnostic_index = 0

    def handle(self, event, rotation=None, now=None):
        """Handle one debounced button event.

        Return ``True`` when the displayed mode/diagnostic colour changed.
        ``rotation`` is only used for DOWN in normal mode.
        """
        if event == "up":
            self.mode = "diagnostic" if self.mode == "normal" else "normal"
            return True
        if event != "down":
            return False
        if self.mode == "diagnostic":
            self.diagnostic_index = (self.diagnostic_index + 1) % len(DIAGNOSTIC_COLORS)
            return True
        if rotation is not None:
            rotation.next(now)
        return False

    def diagnostic(self):
        return DIAGNOSTIC_COLORS[self.diagnostic_index]
