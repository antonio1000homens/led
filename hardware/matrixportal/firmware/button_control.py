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

    @property
    def pressed(self):
        return self._stable_pressed

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


class ButtonGesture:
    """Classify a debounced button as a short or long press."""

    def __init__(self, read, debounce_seconds=0.05, long_press_seconds=0.8):
        self.button = DebouncedButton(read, debounce_seconds=debounce_seconds)
        self.long_press_seconds = float(long_press_seconds)
        self._pressed_at = None
        self._long_emitted = False

    def poll(self, now):
        just_pressed = self.button.poll(now)
        if just_pressed:
            self._pressed_at = now
            self._long_emitted = False

        if self._pressed_at is not None and self.button.pressed:
            if not self._long_emitted and now - self._pressed_at >= self.long_press_seconds:
                self._long_emitted = True
                return "long"
            return None

        if self._pressed_at is not None and not self.button.pressed:
            event = None if self._long_emitted else "short"
            self._pressed_at = None
            self._long_emitted = False
            return event
        return None


class MatrixButtons:
    """Configure the MatrixPortal UP and DOWN buttons without host imports."""

    def __init__(self):
        import board
        import digitalio

        self._up_io = digitalio.DigitalInOut(board.BUTTON_UP)
        self._down_io = digitalio.DigitalInOut(board.BUTTON_DOWN)
        self._up_io.switch_to_input(pull=digitalio.Pull.UP)
        self._down_io.switch_to_input(pull=digitalio.Pull.UP)
        self._up = ButtonGesture(lambda: self._up_io.value)
        self._down = ButtonGesture(lambda: self._down_io.value)

    def poll(self, now):
        events = []
        up = self._up.poll(now)
        down = self._down.poll(now)
        if up:
            events.append("up_long" if up == "long" else "up")
        if down:
            events.append("down_long" if down == "long" else "down")
        return events
