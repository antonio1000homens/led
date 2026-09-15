from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DeploymentStaticTests(unittest.TestCase):
    def test_production_deploy_enables_and_verifies_todoist(self):
        workflow = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
        self.assertIn('LED_CALENDAR_SOURCE: "todoist"', workflow)
        self.assertIn('hosting_bucket=$(output HostingBucketName)', workflow)
        self.assertIn("Verify Todoist screen is live", workflow)
        self.assertIn("calendar.get('source') != 'todoist'", workflow)
        self.assertIn("calendar.get('stale')", workflow)

    def test_static_deploy_uploads_current_simulator_html(self):
        deploy_static = (ROOT / "scripts" / "deploy-static.sh").read_text(encoding="utf-8")
        self.assertIn('simulator/index.html', deploy_static)
        self.assertIn('s3://${BUCKET}/index.html', deploy_static)
        self.assertIn("--paths '/index.html' '/api/screens'", deploy_static)

    def test_simulator_weather_group_cycles_with_clock_in_header(self):
        simulator = (ROOT / "simulator" / "index.html").read_text(encoding="utf-8")
        self.assertIn("function temperatureText(weather)", simulator)
        self.assertIn("function weatherGroupLayout(weather, offset = 0)", simulator)
        self.assertIn("function drawWeatherGroup(weather, offset = 0)", simulator)
        self.assertIn("function headerItemState(phase, weather)", simulator)
        self.assertIn("if (header.item === 'weather') drawWeatherGroup(screen.weather, header.offset);", simulator)
        self.assertNotIn("drawWeatherIcon(screen.weather);", simulator)
        self.assertNotIn("iconX: 992", simulator)

    def test_simulator_hides_all_day_time_and_renders_due_countdown(self):
        simulator = (ROOT / "simulator" / "index.html").read_text(encoding="utf-8")
        self.assertIn("event.all_day || rawTimeText.toUpperCase() === 'ALL'", simulator)
        self.assertIn("function calendarDueText(event, now = new Date())", simulator)
        self.assertIn("return 'DUE TODAY';", simulator)
        self.assertIn("return `DUE IN ${dayDelta}d`;", simulator)
        self.assertIn("drawCalendarDue(events, wallClock", simulator)
        self.assertIn("timeZone: 'Europe/London'", simulator)

    def test_simulator_does_not_pretruncate_agenda_rows(self):
        simulator = (ROOT / "simulator" / "index.html").read_text(encoding="utf-8")
        self.assertIn("return parts.when + ' ' + parts.title;", simulator)
        self.assertNotIn("String(event.title || event.location || 'Event')).slice(0, 32)", simulator)

    def test_simulator_keeps_agenda_date_time_fixed_while_title_scrolls(self):
        simulator = (ROOT / "simulator" / "index.html").read_text(encoding="utf-8")
        self.assertIn("function agendaTitleX(title, phase, startX)", simulator)
        self.assertIn("const titleStart = context.measureText(parts.when + ' ').width;", simulator)
        self.assertIn("context.rect(titleStart, 32, 1024 - titleStart, 96);", simulator)
        self.assertIn("context.fillText(parts.title, agendaTitleX(parts.title, phase, titleStart), y);", simulator)
        self.assertIn("context.fillText(parts.when, 0, y);", simulator)

    def test_simulator_rail_uses_spare_line_and_runtime_marquee_settings(self):
        simulator = (ROOT / "simulator" / "index.html").read_text(encoding="utf-8")
        self.assertIn("const RAIL_MARQUEE_DELAY_SECONDS = 1.2;", simulator)
        self.assertIn("const RAIL_MARQUEE_SPEED = 120;", simulator)
        self.assertIn("const RAIL_MARQUEE_GAP = 112;", simulator)
        self.assertIn("return { services: services.slice(0, 3) };", simulator)
        self.assertIn("const upcomingServices = railServices.slice(1, 3);", simulator)
        self.assertIn("drawRailService(upcoming, 64 + index * 30", simulator)
        self.assertNotIn("context.fillText('UPCOMING', 0, 64);", simulator)
        self.assertIn("stationMarqueeSpeed(screen)", simulator)
        self.assertIn("function stationMarqueeGap()", simulator)
        self.assertIn("return RAIL_MARQUEE_GAP;", simulator)
        self.assertIn("function stationSeparator(service)", simulator)
        self.assertIn("service.station_spacing_px", simulator)

    def test_simulator_right_aligns_rail_and_queue_state_to_display_edge(self):
        simulator = (ROOT / "simulator" / "index.html").read_text(encoding="utf-8")
        self.assertIn("function drawRailService(service, y, xOffset, rightEdge, color)", simulator)
        self.assertIn("rightEdge - context.measureText(state).width", simulator)
        self.assertIn("function drawQueueRide(ride, y, rightEdge)", simulator)
        self.assertIn("drawQueueRide(ride, 34 + slot * 30 - yOffset, 1024);", simulator)

    def test_physical_renderer_uses_both_departure_rows_and_clips_agenda_title(self):
        display = (ROOT / "display.py").read_text(encoding="utf-8")
        self.assertIn("upcoming = services[1:3]", display)
        self.assertIn("y = 17 + index * 8", display)
        self.assertIn("self._rail_service(group, service, color, x, y, DISPLAY_WIDTH)", display)
        self.assertNotIn('self._label(group, "UPCOMING", 0xFFAA00, 0, 17)', display)
        self.assertIn('self._mask(group, 0, y - 3, AGENDA_TITLE_X, AGENDA_ROW_HEIGHT)', display)
        self.assertIn('self._label(group, when, 0xFFFFFF, 0, y)', display)

    def test_admin_bootstraps_access_before_fetching_api(self):
        admin = (ROOT / "simulator" / "admin.html").read_text(encoding="utf-8")
        self.assertIn('<link rel="icon" href="data:,">', admin)
        self.assertIn("window.location.replace(`${API}/session`);", admin)
        self.assertIn("window.history.replaceState(null,'','/admin');", admin)
        self.assertIn('<details class="feed-advanced"><summary>Advanced</summary>', admin)


if __name__ == "__main__":
    unittest.main()
