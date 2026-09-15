"""Layout refinements shared by the hardware and fixture displays.

This module keeps the existing display backends intact while tightening the
column layout for Todoist due labels and rail service statuses.
"""

import display as base

from formatting import (
    AGENDA_TITLE_X,
    agenda_title_marquee_x,
    calendar_row_parts,
    row_slide_phase,
)
from layout_formatting import todoist_due_label

# The inherited fixture renderer calls the function imported by display.py.
# Point it at the refined day-only formatter so hardware and fixture match.
base.todoist_due_label = todoist_due_label


class MatrixDisplay(base.MatrixDisplay):
    """Matrix display with per-row Todoist due labels and aligned rail status."""

    def show(self, screen, clock_time="--:--", clock_date="", phase=2):
        self._clock_date = clock_date
        return super().show(screen, clock_time, clock_date=clock_date, phase=phase)

    def _rail(self, group, screen, phase):
        self._rail_status_right = base._header_content_right(screen)
        try:
            return super()._rail(group, screen, phase)
        finally:
            self._rail_status_right = None

    def _rail_service(self, group, service, color, x_offset, y, right_edge):
        aligned_right = getattr(self, "_rail_status_right", None)
        if aligned_right is not None:
            right_edge = aligned_right
        return super()._rail_service(group, service, color, x_offset, y, right_edge)

    def _calendar(self, group, screen, phase):
        events, visible, start, progress = base._agenda_state(screen, phase)
        if not events:
            self._label(group, "No upcoming events", 0xFFFFFF, 0, base.AGENDA_FIRST_Y)
        else:
            row_count = min(len(events) - start, visible * 2 if progress > 0 else visible)
            y_offset = int(progress * visible * base.AGENDA_ROW_HEIGHT)
            for slot in range(max(0, row_count)):
                event_index = start + slot
                if event_index >= len(events):
                    break
                event = events[event_index]
                when, title = calendar_row_parts(event)
                y = base.AGENDA_FIRST_Y + slot * base.AGENDA_ROW_HEIGHT - y_offset
                due = todoist_due_label(event, getattr(self, "_clock_date", "")) if screen.get("source") == "todoist" else ""
                if due:
                    due_x = base._right_aligned_x(due, base.DISPLAY_WIDTH)
                    title_width = max(0, due_x - base.HEADER_GAP - AGENDA_TITLE_X)
                    self._label(
                        group,
                        base._fit_text_pixels(title, title_width),
                        0xFFFFFF,
                        AGENDA_TITLE_X,
                        y,
                    )
                else:
                    self._label(group, title, 0xFFFFFF, agenda_title_marquee_x(title, phase), y)
                self._mask(group, 0, y - 3, AGENDA_TITLE_X, base.AGENDA_ROW_HEIGHT)
                self._label(group, when, 0xFFFFFF, 0, y)
                if due:
                    due_progress = row_slide_phase(phase, slot)
                    due_offset = int((1.0 - due_progress) * base.DISPLAY_WIDTH)
                    self._label(group, due, 0xFFFFFF, due_x + due_offset, y)
        self._header_mask(group)
        self._label(group, base._clip(screen.get("title") or "UPCOMING", 30), 0xFFAA00, 0, 3)


class FixtureDisplay(base.FixtureDisplay):
    """Fixture display with the same fixed rail-status column as hardware."""

    def _draw_screen(self, screen, phase, clock_date=""):
        self._rail_status_right = (
            base._header_content_right(screen) if screen.get("kind") == "rail_combined" else None
        )
        try:
            return super()._draw_screen(screen, phase, clock_date)
        finally:
            self._rail_status_right = None

    def _rail_service(self, service, color, x_offset, y, right_edge):
        aligned_right = getattr(self, "_rail_status_right", None)
        if aligned_right is not None:
            right_edge = aligned_right
        return super()._rail_service(service, color, x_offset, y, right_edge)


def create(settings):
    return MatrixDisplay() if settings.DISPLAY_BACKEND == "matrix" else FixtureDisplay()
