from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DeploymentStaticTests(unittest.TestCase):
    def test_cloud_slicer_deploy_uses_dedicated_oidc_role_and_ssm(self):
        template = (ROOT / "infrastructure" / "bootstrap.yaml").read_text(encoding="utf-8")
        workflow = (ROOT / ".github" / "workflows" / "slicer-worker.yml").read_text(encoding="utf-8")
        deploy = (ROOT / "scripts" / "slicer" / "deploy-cloud-slicer-worker.sh").read_text(encoding="utf-8")
        self.assertIn("RoleName: led-github-cloud-slicer-deploy-role", template)
        self.assertIn("parameter/led/cloud-slicer/*", template)
        self.assertIn("role/led-github-cloud-slicer-deploy-role", workflow)
        self.assertNotIn("GitHubActionsLedDeployRole", workflow)
        for name in ("github-codespaces-token", "mcp-client-token", "origin-bearer-token", "cloudflare-api-token"):
            self.assertIn(name, deploy)
        self.assertIn("wrangler secret put", deploy)

    def test_simulator_preview_uses_full_available_width(self):
        simulator = (ROOT / "simulator" / "index.html").read_text(encoding="utf-8")
        self.assertIn("main { width: 100%; padding: 28px; }", simulator)
        self.assertIn("canvas { display: block; width: 100%;", simulator)

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

    def test_todoist_due_labels_are_day_only_and_row_level(self):
        simulator = (ROOT / "simulator" / "index.html").read_text(encoding="utf-8")
        display = (ROOT / "hardware" / "matrixportal" / "firmware" / "display.py").read_text(encoding="utf-8")
        self.assertIn("function todoistDueLabel(event, now = new Date())", simulator)
        self.assertIn("return 'TODAY';", simulator)
        self.assertIn("screen.source === 'todoist'", simulator)
        self.assertIn("todoist_due_label(events[event_index], clock_date)", display)
        self.assertIn('screen.get("source") == "todoist"', display)

    def test_simulator_does_not_pretruncate_agenda_rows(self):
        simulator = (ROOT / "simulator" / "index.html").read_text(encoding="utf-8")
        self.assertIn("return parts.when + ' ' + parts.title;", simulator)
        self.assertNotIn("String(event.title || event.location || 'Event')).slice(0, 32)", simulator)

    def test_simulator_keeps_agenda_date_time_fixed_while_title_scrolls(self):
        simulator = (ROOT / "simulator" / "index.html").read_text(encoding="utf-8")
        self.assertIn("function agendaTitleX(title, phase, startX)", simulator)
        self.assertIn("const titleStart = measureLedText(parts.when + ' ').width;", simulator)
        self.assertIn("context.rect(titleStart, 32, 1024 - titleStart, 96);", simulator)
        self.assertIn("drawLedText(parts.title, agendaTitleX(parts.title, titlePhase, titleStart), y);", simulator)
        self.assertIn("drawLedText(parts.when, 0, y);", simulator)

    def test_simulator_rail_uses_spare_line_and_runtime_marquee_settings(self):
        simulator = (ROOT / "simulator" / "index.html").read_text(encoding="utf-8")
        self.assertIn("const RAIL_MARQUEE_DELAY_SECONDS = 1.2;", simulator)
        self.assertIn("const RAIL_MARQUEE_SPEED = 120;", simulator)
        self.assertIn("const RAIL_MARQUEE_GAP = 112;", simulator)
        self.assertIn("return { services: services.slice(0, 1 + count) };", simulator)
        self.assertIn("function railRows(services, phase)", simulator)
        self.assertIn("RAIL_ROW_Y[rowIndex]", simulator)
        self.assertIn("drawRailService(row.service, y, 0, headerRight", simulator)
        self.assertNotIn("context.fillText('UPCOMING', 0, 64);", simulator)
        self.assertIn("stationMarqueeSpeed(screen)", simulator)
        self.assertIn("function stationMarqueeGap()", simulator)
        self.assertIn("return RAIL_MARQUEE_GAP;", simulator)
        self.assertIn("function stationSeparator(service)", simulator)
        self.assertIn("service.station_spacing_px", simulator)

    def test_simulator_right_aligns_rail_and_queue_state_to_display_edge(self):
        simulator = (ROOT / "simulator" / "index.html").read_text(encoding="utf-8")
        self.assertIn("function drawRailService(service, y, xOffset, rightEdge, color, ordinal = 1)", simulator)
        self.assertIn("rightEdge - measureLedText(state).width", simulator)
        self.assertIn("function drawQueueRide(ride, y, rightEdge)", simulator)
        self.assertIn("const QUEUE_ROW_HEIGHT = CONTENT_ROW_HEIGHT;", simulator)
        self.assertIn("drawQueueRide(ride, CONTENT_FIRST_Y + slot * QUEUE_ROW_HEIGHT - yOffset, 1024);", simulator)

    def test_simulator_hardware_preview_matches_matrix_constraints(self):
        simulator = (ROOT / "simulator" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="hardware-preview"', simulator)
        self.assertIn("let hardwarePreview = true;", simulator)
        self.assertIn("const MATRIX_REFRESH_FPS = 7;", simulator)
        self.assertIn("logicalCanvas.width = 256;", simulator)
        self.assertIn("logicalCanvas.height = 32;", simulator)
        self.assertIn("const FONT_5X7 =", simulator)
        self.assertIn("function drawLedText(value, x, y)", simulator)
        self.assertIn("function quantizeRgb(red, green, blue)", simulator)
        self.assertIn("[64, 128, 192].forEach", simulator)
        self.assertIn("const TODOIST_MARQUEE_SPEED = 7 * FONT_PIXEL_SCALE;", simulator)
        self.assertIn("const TODOIST_MARQUEE_PAUSE_SECONDS = 1.5;", simulator)
        self.assertIn("const CLOCK_X = 226 * FONT_PIXEL_SCALE;", simulator)
        self.assertIn("const STALE_X = 190 * FONT_PIXEL_SCALE;", simulator)
        self.assertIn("const RAIL_ROW_Y = [4, 12, 20, 28].map(value => value * FONT_PIXEL_SCALE);", simulator)
        self.assertIn("const CONTENT_FIRST_Y = 8 * FONT_PIXEL_SCALE;", simulator)
        self.assertIn("const AGENDA_FIRST_Y = 11 * FONT_PIXEL_SCALE;", simulator)
        self.assertIn("const UPCOMING_FIRST_Y = 17 * FONT_PIXEL_SCALE;", simulator)
        self.assertIn("presentPreview();", simulator)
        self.assertNotIn("context.font = '24px monospace';", simulator)

    def test_physical_renderer_uses_both_departure_rows_and_clips_agenda_title(self):
        display = (ROOT / "hardware" / "matrixportal" / "firmware" / "display.py").read_text(encoding="utf-8")
        self.assertIn("RAIL_ROW_Y", display)
        self.assertIn("rail_rows(services, phase)", display)
        self.assertIn('self._label(group, "DEPARTURES", 0xFFAA00, 0, y)', display)
        self.assertIn('self._mask(group, 0, y - 3, AGENDA_TITLE_X, AGENDA_ROW_HEIGHT)', display)
        self.assertIn('self._label(group, when, 0xFFFFFF, 0, y)', display)

    def test_no_services_page_suppresses_normal_departure_chrome(self):
        simulator = (ROOT / "simulator" / "index.html").read_text(encoding="utf-8")
        display = (ROOT / "hardware" / "matrixportal" / "firmware" / "display.py").read_text(encoding="utf-8")
        admin = (ROOT / "simulator" / "admin.html").read_text(encoding="utf-8")
        self.assertIn("if (screen.empty_state) {", simulator)
        self.assertIn("suppressHeader = true;", simulator)
        self.assertIn('empty_state = screen.get("empty_state")', display)
        self.assertIn("No services duration", admin)

    def test_admin_bootstraps_access_before_fetching_api(self):
        admin = (ROOT / "simulator" / "admin.html").read_text(encoding="utf-8")
        self.assertIn('<link rel="icon" href="data:,">', admin)
        self.assertIn("window.location.replace(`${API}/session`);", admin)
        self.assertIn("window.history.replaceState(null,'','/admin');", admin)
        self.assertIn('<details class="feed-advanced"><summary>Advanced</summary>', admin)


if __name__ == "__main__":
    unittest.main()
