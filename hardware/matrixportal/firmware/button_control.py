"""Non-blocking debounced button helpers for the MatrixPortal S3."""


class DebouncedButton:
    """Emit ``pressed`` once after a raw input stays changed long enough."""

    def __init__(self, read, debounce_seconds=0.05, active_low=True):
        self.read = read
        self.debounce_seconds = float(debounce_seconds)
        self.active_low = bool(active_low)
        raw = bool(read())
        self._raw_pressed = (not raw) if self.active_low else raw
        self._stable_pressed = self._raw_pressed
        self._changed_at = None

    def poll(self, now):
        raw = bool(self.read())
        pressed = (not raw) if self.active_low else raw
        if pressed != self._raw_pressed:
            self._raw_pressed = pressed
            self._changed_at = now
            return False
        if self._changed_at is None or pressed == self._stable_pressed:
            return False
        if now - self._changed_at < self.debounce_seconds:
            return False
        self._stable_pressed = pressed
        return pressed


class MatrixButtons:
    """Configure the MatrixPortal UP and DOWN buttons without host imports."""

    def __init__(self):
        import board
        import digitalio

        self._up_io = digitalio.DigitalInOut(board.BUTTON_UP)
        self._down_io = digitalio.DigitalInOut(board.BUTTON_DOWN)
        self._up_io.switch_to_input(pull=digitalio.Pull.UP)
        self._down_io.switch_to_input(pull=digitalio.Pull.UP)
        self._up = DebouncedButton(lambda: self._up_io.value)
        self._down = DebouncedButton(lambda: self._down_io.value)

    def poll(self, now):
        events = []
        if self._up.poll(now):
            events.append("up")
        if self._down.poll(now):
            events.append("down")
        return events
