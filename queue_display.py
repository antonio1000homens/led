"""Display adapter for combined Queue-Times park cycling and splash transitions.

The existing display backend remains responsible for drawing ordinary screens.
This adapter selects the active park, translates configurable queue timing into
the legacy queue renderer's phase model, and owns the optional full-page splash.
"""

from queue_cycle import (
    QUEUE_ROW_HEIGHT,
    QUEUE_VISIBLE_ROWS,
    queue_cycle_state,
    queue_scroll_state,
)

DISPLAY_WIDTH = 256
DISPLAY_HEIGHT = 32
FONT_WIDTH = 5
LEGACY_QUEUE_HOLD_SECONDS = 1.0
LEGACY_QUEUE_SLIDE_SECONDS = 0.3
LEGACY_QUEUE_STEP_SECONDS = LEGACY_QUEUE_HOLD_SECONDS + LEGACY_QUEUE_SLIDE_SECONDS
SPLASH_TARGET_X = 12
SPLASH_BASELINE_Y = 17
SPLASH_TOP_Y = -6


def _parks(screen):
    parks = screen.get("parks")
    if isinstance(parks, list) and parks:
        return [park for park in parks if isinstance(park, dict)]
    # Backward compatibility for pre-combined Queue-Times payloads.
    return [{
        "id": screen.get("id") or "queue-times",
        "title": screen.get("title") or "QUEUE TIMES",
        "source": screen.get("source") or "queue_times",
        "stale": bool(screen.get("stale")),
        "rides": screen.get("rides") or [],
    }]


def _legacy_phase(start, progress):
    start = max(0, int(start or 0))
    progress = max(0.0, min(1.0, float(progress or 0.0)))
    if progress <= 0:
        return start * LEGACY_QUEUE_STEP_SECONDS
    return (
        start * LEGACY_QUEUE_STEP_SECONDS
        + LEGACY_QUEUE_HOLD_SECONDS
        + progress * LEGACY_QUEUE_SLIDE_SECONDS
    )


def queue_render_state(screen, phase):
    """Return the active park and render phase for the existing queue drawer."""
    parks = _parks(screen)
    counts = [len(park.get("rides") or []) for park in parks]
    park_index, data_phase, mode, transition_progress = queue_cycle_state(
        phase,
        counts,
        screen.get("queue_scroll_pause_seconds"),
        screen.get("queue_scroll_speed"),
        bool(screen.get("splash_enabled")),
    )
    park = parks[min(park_index, len(parks) - 1)]
    rides = park.get("rides") or []
    start, progress = queue_scroll_state(
        data_phase,
        len(rides),
        screen.get("queue_scroll_pause_seconds"),
        screen.get("queue_scroll_speed"),
        visible_rows=QUEUE_VISIBLE_ROWS,
        row_height=QUEUE_ROW_HEIGHT,
    )
    rendered = dict(screen)
    rendered.pop("parks", None)
    rendered["id"] = park.get("id") or park.get("feed_id") or screen.get("id")
    rendered["title"] = park.get("title") or "QUEUE TIMES"
    rendered["source"] = park.get("source") or screen.get("source") or "queue_times"
    rendered["stale"] = bool(park.get("stale")) or bool(screen.get("stale"))
    rendered["rides"] = rides
    rendered["active_park_index"] = park_index
    rendered["active_park_count"] = len(parks)
    rendered["active_park_mode"] = mode
    return rendered, _legacy_phase(start, progress), mode, transition_progress


def _flash_visible(progress):
    # Three quick pulses across the transition period, ending visible.
    return int(max(0.0, min(0.999, float(progress or 0.0))) * 6) % 2 == 0


def _title_width(title):
    return len(str(title or "")) * FONT_WIDTH


class QueueAwareDisplay:
    def __init__(self, base):
        self.base = base

    def _matrix_splash(self, screen, clock_time, mode, progress):
        import displayio

        title = str(screen.get("title") or "QUEUE TIMES")
        if mode == "splash_up":
            # Draw real data first, then cover/reveal it from top to bottom as the
            # splash title exits upward.
            self.base.show(screen, clock_time, phase=0)
            group = self.base.display.root_group
            y = int(SPLASH_BASELINE_Y + (SPLASH_TOP_Y - SPLASH_BASELINE_Y) * progress)
            cover_height = max(0, min(DISPLAY_HEIGHT, y + 5))
            if cover_height:
                self.base._mask(group, 0, 0, DISPLAY_WIDTH, cover_height)
            self.base._label(group, title, 0xFFAA00, SPLASH_TARGET_X, y)
            self.base._present(group)
            return

        group = displayio.Group()
        if mode == "splash_in":
            x = int(-_title_width(title) + (SPLASH_TARGET_X + _title_width(title)) * progress)
            self.base._label(group, title, 0xFFAA00, x, SPLASH_BASELINE_Y)
        elif _flash_visible(progress):
            self.base._label(group, title, 0xFFFFFF, SPLASH_TARGET_X, SPLASH_BASELINE_Y)
        self.base._present(group)

    def _fixture_splash(self, screen, clock_time, mode, progress):
        title = str(screen.get("title") or "QUEUE TIMES")
        if self.base.pixels is None:
            print("\n[{}] {}".format(clock_time, title))
            return
        if mode == "splash_up":
            self.base.show(screen, clock_time, phase=0)
            y = int(SPLASH_BASELINE_Y + (SPLASH_TOP_Y - SPLASH_BASELINE_Y) * progress)
            cover_height = max(0, min(DISPLAY_HEIGHT, y + 5))
            self.base._clear_rows(0, cover_height)
            self.base._text(title, SPLASH_TARGET_X, y, (255, 100, 0))
            self.base.pixels.show()
            return
        self.base.pixels.fill((0, 0, 0))
        if mode == "splash_in":
            x = int(-_title_width(title) + (SPLASH_TARGET_X + _title_width(title)) * progress)
            self.base._text(title, x, SPLASH_BASELINE_Y, (255, 100, 0))
        elif _flash_visible(progress):
            self.base._text(title, SPLASH_TARGET_X, SPLASH_BASELINE_Y, (255, 255, 255))
        self.base.pixels.show()

    def show(self, screen, clock_time="--:--", clock_date="", phase=2):
        if screen.get("kind") != "theme_park_queues" or not screen.get("parks"):
            return self.base.show(screen, clock_time, clock_date=clock_date, phase=phase)

        rendered, render_phase, mode, progress = queue_render_state(screen, phase)
        if mode == "data":
            return self.base.show(rendered, clock_time, clock_date=clock_date, phase=render_phase)
        if mode == "flash":
            flashed = dict(rendered)
            if not _flash_visible(progress):
                flashed["title"] = " "
            return self.base.show(flashed, clock_time, clock_date=clock_date, phase=0)

        # Full-page splash intentionally suppresses clock/weather/stale overlays
        # until the data is revealed.
        if hasattr(self.base, "display") and hasattr(self.base, "_label"):
            return self._matrix_splash(rendered, clock_time, mode, progress)
        if hasattr(self.base, "pixels") and hasattr(self.base, "_text"):
            return self._fixture_splash(rendered, clock_time, mode, progress)
        return self.base.show(rendered, clock_time, clock_date=clock_date, phase=render_phase)

    def show_diagnostic(self, color):
        return self.base.show_diagnostic(color)


def create(settings):
    from display import create as create_base

    return QueueAwareDisplay(create_base(settings))
