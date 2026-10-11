"""One-shot Wi-Fi-off window for the isolated physical train test."""


class WifiIsolationWindow:
    """Briefly disable Wi-Fi, then let CircuitPython restore its connection."""

    def __init__(self, start_at, duration_seconds):
        self.start_at = float(start_at)
        self.end_at = self.start_at + max(1.0, float(duration_seconds))
        self.state = "waiting"
        self.radio = None

    def update(self, now, radio=None):
        now = float(now)
        if self.state == "waiting" and now >= self.start_at:
            if radio is None:
                import wifi

                radio = wifi.radio
            self.radio = radio
            self.radio.enabled = False
            self.state = "offline"
            print("STEAM TRAIN TEST Wi-Fi isolation started")
            return

        if self.state == "offline" and now >= self.end_at:
            self.radio.enabled = True
            self.state = "reconnecting"
            print("STEAM TRAIN TEST Wi-Fi restored")

        if self.state == "reconnecting" and self.radio.connected:
            self.state = "done"
            print("STEAM TRAIN TEST Wi-Fi reconnected")
