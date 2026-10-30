"""Pure runtime mode state for the MatrixPortal application."""


DIAGNOSTIC_COLORS = (
    ("RED", 0x400000),
    ("GREEN", 0x004000),
    ("BLUE", 0x000040),
    ("WHITE", 0x202020),
    ("BLACK", 0x000000),
)


def collect_gc_with_state(gc_module, enabled_after=False):
    """Collect once, then restore the requested collector state on every path."""
    collect = getattr(gc_module, "collect", None)
    if collect is None:
        return None
    enable = getattr(gc_module, "enable", None)
    disable = getattr(gc_module, "disable", None)
    if enable is not None:
        enable()
    try:
        return collect()
    finally:
        transition = enable if enabled_after else disable
        if transition is not None:
            transition()


def enter_rail_gc_window(gc_module, allow_during_build=False, collect_at_entry=True):
    """Configure GC before rail display, optionally avoiding a prebuilt handoff pause."""
    if allow_during_build:
        enable = getattr(gc_module, "enable", None)
        if enable is not None:
            enable()
        return False
    if collect_at_entry:
        collect_gc_with_state(gc_module, enabled_after=False)
        return True
    disable = getattr(gc_module, "disable", None)
    if disable is not None:
        disable()
    return False


FOOTBALL_GC_SETTLE_GRACE_SECONDS = 0.5


def football_gc_safe_to_collect(screen, phase, animation_active=False):
    """Allow a one-shot collection only after a fully rendered football entry.

    A settled match is motionless; countdown text changes at most once per
    second. The caller must separately gate once per rotation/prompt event.
    Avoid collections while the outgoing scene is being pushed, during goal
    flashes, or on an interrupted/non-football screen.
    """
    if (not isinstance(screen, dict)
            or screen.get("kind") != "football_score"
            or animation_active):
        return False
    try:
        return float(phase) >= 3.2 + FOOTBALL_GC_SETTLE_GRACE_SECONDS
    except (ValueError, TypeError):
        return False


def christmas_gc_action(screen_kind, suspended, overlay_active=False):
    """Return enter/exit only at Christmas screen boundaries, never mid-scene."""
    active = screen_kind in ("christmas_tracker_intro", "christmas_tracker") and not overlay_active
    if active and not suspended:
        return "enter"
    if suspended and not active:
        return "exit"
    return None


def prepare_christmas_scene_gc(gc_module):
    """Collect after off-screen scene construction while the board can still work."""
    return collect_gc_with_state(gc_module, enabled_after=True)


def enter_christmas_gc_window(gc_module):
    """Keep automatic collection enabled while the animated scene is active."""
    enable = getattr(gc_module, "enable", None)
    if enable is not None:
        enable()


def leave_christmas_gc_window(gc_module):
    """Collect deferred garbage after the scene and restore automatic GC."""
    return collect_gc_with_state(gc_module, enabled_after=True)


class RuntimeMode:
    """Track normal/diagnostic mode without depending on CircuitPython APIs."""

    def __init__(self):
        self.mode = "normal"
        self.diagnostic_index = 0

    def handle(self, event, rotation=None, now=None):
        """Handle one debounced button event.

        Return ``True`` when the displayed mode/diagnostic colour changed.
        Long UP toggles diagnostics; long DOWN advances the normal rotation.
        """
        if event == "up_long":
            self.mode = "diagnostic" if self.mode == "normal" else "normal"
            return True
        if event == "down" and self.mode == "diagnostic":
            self.diagnostic_index = (self.diagnostic_index + 1) % len(DIAGNOSTIC_COLORS)
            return True
        if event == "down_long" and self.mode == "normal" and rotation is not None:
            rotation.next(now)
        return False

    def diagnostic(self):
        return DIAGNOSTIC_COLORS[self.diagnostic_index]
