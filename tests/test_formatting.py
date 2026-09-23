import unittest

from formatting import (
    AGENDA_TITLE_X,
    agenda_marquee_x,
    agenda_scroll_state,
    agenda_title_marquee_x,
    calendar_due_text,
    todoist_due_label,
    calendar_row,
    calendar_row_parts,
    calendar_row_text,
    calling_marquee_x,
    calling_text,
    todoist_effective_duration,
    todoist_page_timing,
    RAIL_ROW_Y,
    rail_phase,
    rail_rows,
    departure_scroll_state,
    ordinal_label,
    format_row,
    header,
    queue_scroll_state,
    rail_row_parts,
    row_slide_phase,
)


class FormattingTests(unittest.TestCase):
    def test_row_is_fixed_width(self):
        self.assertEqual(len(format_row({"time": "12:04", "destination": "Waterloo", "platform": "1", "status": "On time"})), 32)

    def test_long_destination_uses_available_row_space(self):
        row = format_row({"time": "12:04", "destination": "London Waterloo", "platform": "1", "status": "On time"})
        self.assertIn("London Waterloo", row)
        self.assertIn("P1", row)

    def test_on_time_status_is_at_right_edge_of_formatted_row(self):
        row = format_row({"time": "12:04", "destination": "Waterloo", "platform": "1", "status": "On time"})
        self.assertTrue(row.endswith("On time"))

    def test_rail_row_parts_keep_status_independent_for_right_alignment(self):
        left, status = rail_row_parts({"time": "12:04", "destination": "Waterloo", "platform": "1", "status": "On time"})
        self.assertEqual(status, "On time")
        self.assertEqual(left, "12:04 Waterloo P1")

    def test_cancelled_status_is_visible(self):
        self.assertIn("CANCELLED", format_row({"time": "12:04", "destination": "Waterloo", "platform": "1", "cancelled": True}))

    def test_stale_header(self):
        self.assertIn("STALE", header("NEM", stale=True))

    def test_header_is_new_departures(self):
        self.assertEqual(header("NEM"), "NEW DEPARTURES")

    def test_rows_slide_in_one_at_a_time(self):
        self.assertEqual(row_slide_phase(0, 0), 0)
        self.assertEqual(row_slide_phase(0, 1), 0)
        self.assertGreater(row_slide_phase(1.1, 0), row_slide_phase(1.1, 1))
        self.assertEqual(row_slide_phase(4, 2), 1)

    def test_departures_scroll_one_upcoming_train_at_a_time_after_pause(self):
        self.assertEqual(departure_scroll_state(0, 4, 2), (0, 0.0, 0.0))
        self.assertEqual(departure_scroll_state(2, 4, 2), (0, 0.0, 0.0))
        start, progress, reset = departure_scroll_state(2.2, 4, 2)
        self.assertEqual(start, 0)
        self.assertAlmostEqual(progress, 0.5)
        self.assertEqual(reset, 0.0)
        self.assertEqual(departure_scroll_state(2.4, 4, 2), (1, 0.0, 0.0))
        self.assertEqual(departure_scroll_state(6.8, 4, 2), (2, 0.0, 0.0))
        self.assertIsNone(departure_scroll_state(7.2, 4, 2)[2])
        self.assertEqual(departure_scroll_state(7.6, 4, 2)[2], 0.0)
        self.assertAlmostEqual(departure_scroll_state(8.0, 4, 2)[2], 0.5)
        self.assertEqual(departure_scroll_state(8.4, 4, 2), (0, 0.0, 0.0))

    def test_departure_ordinals_use_correct_suffixes(self):
        self.assertEqual([ordinal_label(value) for value in (1, 2, 3, 4, 11, 12, 13, 21)], ["1st", "2nd", "3rd", "4th", "11th", "12th", "13th", "21st"])

    def test_calling_marquee_enters_from_right_immediately(self):
        text = "CALLING AT: " + "x" * 50
        self.assertEqual(calling_marquee_x(text, 0), 256)
        self.assertEqual(calling_marquee_x(text, 1), 208)
        self.assertEqual(calling_marquee_x(text, 2), 160)
        self.assertIsNone(calling_marquee_x(text, 11.3))
        self.assertEqual(calling_marquee_x(text, 14.25), 256)
        short = "CALLING AT: x"
        self.assertEqual(calling_marquee_x(short, 0), 256)
        self.assertGreater(calling_marquee_x(short, 1), 72)

    def test_queue_scroll_holds_then_slides_up(self):
        self.assertEqual(queue_scroll_state(0.9, 6), (0, 0.0))
        start, progress = queue_scroll_state(1.15, 6)
        self.assertEqual(start, 0)
        self.assertAlmostEqual(progress, 0.5)
        self.assertEqual(queue_scroll_state(1.3, 6), (1, 0.0))

    def test_queue_scroll_stops_on_last_three_rides(self):
        self.assertEqual(queue_scroll_state(99, 7), (4, 0.0))
        self.assertEqual(queue_scroll_state(99, 3), (0, 0.0))

    def test_calendar_row_starts_with_date_and_time(self):
        row = calendar_row({"date_text": "14/09", "time_text": "18:30", "title": "Scout meeting"})
        self.assertEqual(len(row), 42)
        self.assertTrue(row.startswith("14/09 18:30 Scout meeting"))

    def test_calendar_row_uses_full_board_width(self):
        row = calendar_row({"date_text": "14/09", "time_text": "18:30", "title": "Scout meeting with a deliberately long title"})
        self.assertEqual(len(row), 42)
        self.assertTrue(row[32:].strip())

    def test_calendar_row_text_retains_marquee_overflow(self):
        text = calendar_row_text({"date_text": "14/09", "time_text": "18:30", "title": "Scout meeting with a deliberately long title for scrolling"})
        self.assertGreater(len(text), 42)
        self.assertTrue(text.endswith("for scrolling"))

    def test_calendar_parts_keep_date_time_fixed_and_title_separate(self):
        when, title = calendar_row_parts({"date_text": "14/09", "time_text": "18:30", "title": "Scout meeting"})
        self.assertEqual(when, "14/09 18:30")
        self.assertEqual(title, "Scout meeting")

    def test_agenda_title_marquee_never_changes_fixed_prefix_origin(self):
        title = "x" * 40
        self.assertEqual(agenda_title_marquee_x(title, 0), AGENDA_TITLE_X)
        self.assertEqual(agenda_title_marquee_x(title, 1), AGENDA_TITLE_X - 30)
        self.assertEqual(agenda_title_marquee_x(title, 2), AGENDA_TITLE_X - 50)
        self.assertEqual(agenda_title_marquee_x(title, 3.25), AGENDA_TITLE_X - 9)

    def test_agenda_marquee_keeps_42_characters_static(self):
        self.assertEqual(agenda_marquee_x("x" * 42, 99), 0)

    def test_agenda_marquee_scrolls_pauses_and_resets(self):
        text = "x" * 52
        self.assertEqual(agenda_marquee_x(text, 0), 0)
        self.assertEqual(agenda_marquee_x(text, 1), -30)
        self.assertEqual(agenda_marquee_x(text, 2), -50)
        self.assertEqual(agenda_marquee_x(text, 3), -2)
        self.assertEqual(agenda_marquee_x(text, 3.25), -9)

    def test_calendar_row_hides_all_day_time(self):
        row = calendar_row({"start": "2026-09-14", "all_day": True, "date_text": "14/09", "time_text": "ALL", "title": "Inset day"})
        self.assertTrue(row.startswith("14/09       Inset day"))
        self.assertNotIn("ALL", row)

    def test_calendar_row_hides_legacy_all_day_marker(self):
        row = calendar_row({"start": "2026-09-14", "date_text": "14/09", "time_text": "ALL", "title": "Inset day"})
        self.assertNotIn("ALL", row)

    def test_calendar_due_text_same_day_hours_and_minutes(self):
        event = {"start": "2026-09-13T15:45:00+01:00", "time_text": "15:45", "all_day": False}
        self.assertEqual(calendar_due_text(event, "2026-09-13", "13:30"), "DUE IN 2h 15m")

    def test_calendar_due_text_same_day_minutes(self):
        event = {"start": "2026-09-13T14:00:00+01:00", "time_text": "14:00", "all_day": False}
        self.assertEqual(calendar_due_text(event, "2026-09-13", "13:30"), "DUE IN 30m")

    def test_calendar_due_text_due_now(self):
        event = {"start": "2026-09-13T13:30:00+01:00", "time_text": "13:30", "all_day": False}
        self.assertEqual(calendar_due_text(event, "2026-09-13", "13:30"), "DUE NOW")

    def test_calendar_due_text_all_day_today(self):
        event = {"start": "2026-09-13", "all_day": True}
        self.assertEqual(calendar_due_text(event, "2026-09-13", "13:30"), "DUE TODAY")

    def test_calendar_due_text_future_day_uses_calendar_days(self):
        event = {"start": "2026-09-15T09:00:00+01:00", "time_text": "09:00", "all_day": False}
        self.assertEqual(calendar_due_text(event, "2026-09-13", "23:59"), "DUE IN 2d")

    def test_todoist_due_label_ignores_time(self):
        event = {"start": "2026-09-13T23:59:00+01:00"}
        self.assertEqual(todoist_due_label(event, "2026-09-13"), "TODAY")
        self.assertEqual(todoist_due_label({"start": "2026-09-14"}, "2026-09-13"), "DUE 1 DAY")
        self.assertEqual(todoist_due_label({"start": "2026-09-15T01:00:00+01:00"}, "2026-09-13"), "DUE 2 DAYS")

    def test_todoist_due_label_marks_past_date_overdue(self):
        self.assertEqual(todoist_due_label({"start": "2026-09-12"}, "2026-09-13"), "OVERDUE")

    def test_todoist_timing_adds_scroll_before_readable_dwell(self):
        short = [{"start": "2026-09-13", "all_day": True, "title": "Short"}]
        long = [{"start": "2026-09-13", "all_day": True, "title": "x" * 80}]
        self.assertEqual(todoist_page_timing(short, page_seconds=5, current_date="2026-09-13"), 5)
        self.assertGreater(todoist_page_timing(long, page_seconds=5, current_date="2026-09-13"), 5)

    def test_todoist_timing_gives_each_page_its_own_dwell(self):
        events = [{"start": "2026-09-13", "all_day": True, "title": "Short"} for _ in range(6)]
        self.assertEqual(todoist_page_timing(events, page_seconds=5, current_date="2026-09-13"), 21.2)

    def test_todoist_effective_duration_never_shortens_configured_duration(self):
        events = [{"start": "2026-09-13", "all_day": True, "title": "Short"}]
        self.assertEqual(todoist_effective_duration(30, events, page_seconds=5, current_date="2026-09-13"), 30)

    def test_rail_uses_shared_four_row_grid_and_safe_missing_services(self):
        self.assertEqual(RAIL_ROW_Y, (4, 12, 20, 28))
        self.assertEqual(sorted(RAIL_ROW_Y), list(RAIL_ROW_Y))
        self.assertGreaterEqual(RAIL_ROW_Y[0], 4)
        self.assertEqual(RAIL_ROW_Y[-1], 28)
        for count in range(4):
            rows = rail_rows([{"time": "12:00"}] * count, 0)
            self.assertEqual(len(rows), 4)
            self.assertIsNotNone(rows[0])

    def test_rail_summary_and_calling_rows_match_issue_72_contract(self):
        services = [{"time": "12:{:02d}".format(index), "destination": "Waterloo"} for index in range(4)]
        summary_rows = rail_rows(services, 0)
        self.assertEqual([kind for kind, _ in summary_rows], ["header", "service", "service", "service"])
        self.assertIs(summary_rows[1][1], services[0])
        self.assertIs(summary_rows[2][1], services[1])
        self.assertIs(summary_rows[3][1], services[2])
        calling_rows = rail_rows(services, 8)
        self.assertEqual([kind for kind, _ in calling_rows], ["service", "calling", "service", "calling"])
        self.assertIs(calling_rows[0][1], services[0])
        self.assertIs(calling_rows[1][1], services[0])
        self.assertIs(calling_rows[2][1], services[1])
        self.assertIs(calling_rows[3][1], services[1])
        self.assertEqual(rail_phase(0), "summary")
        self.assertEqual(rail_phase(8), "calling")
        self.assertEqual(rail_phase(19.9), "calling")
        self.assertEqual(rail_phase(20), "summary")

    def test_agenda_page_holds_then_slides_to_second_three(self):
        self.assertEqual(agenda_scroll_state(4.9, 6, 5), (0, 0.0))
        start, progress = agenda_scroll_state(5.2, 6, 5)
        self.assertEqual(start, 0)
        self.assertAlmostEqual(progress, 0.5)
        self.assertEqual(agenda_scroll_state(5.5, 6, 5), (3, 0.0))

    def test_agenda_does_not_page_three_or_fewer_events(self):
        self.assertEqual(agenda_scroll_state(99, 3, 5), (0, 0.0))

    def test_calling_text_includes_station_times(self):
        text = calling_text({"destination": "Waterloo", "stops": [{"station": "Wimbledon", "time": "12:19", "status": "On time"}]})
        self.assertEqual(text, "CALLING AT: Wimbledon 12:19")

    def test_calling_text_uses_configured_spacing_between_individual_stations(self):
        service = {
            "station_spacing_px": 12,
            "stops": [
                {"station": "Wimbledon", "time": "12:19", "status": "On time"},
                {"station": "Clapham Junction", "time": "12:27", "status": "On time"},
            ],
        }
        self.assertEqual(
            calling_text(service),
            "CALLING AT: Wimbledon 12:19  Clapham Junction 12:27",
        )
        service["station_spacing_px"] = 30
        self.assertEqual(
            calling_text(service),
            "CALLING AT: Wimbledon 12:19      Clapham Junction 12:27",
        )


if __name__ == "__main__":
    unittest.main()
