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

    def test_simulator_weather_is_dynamically_right_aligned(self):
        simulator = (ROOT / "simulator" / "index.html").read_text(encoding="utf-8")
        self.assertIn("const rightEdge = 1020;", simulator)
        self.assertIn("const temperatureWidth = context.measureText(temperatureText).width;", simulator)
        self.assertIn("const temperatureX = rightEdge - temperatureWidth;", simulator)
        self.assertIn("const iconX = Math.max(0, temperatureX - gap - iconWidth);", simulator)
        self.assertNotIn("context.fillText(temperatureText, 904, 94);", simulator)
        self.assertNotIn("context.fillRect(864 + x * 4", simulator)

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
        self.assertIn("return when + ' ' + String(event.title || event.location || 'Event');", simulator)
        self.assertNotIn("String(event.title || event.location || 'Event')).slice(0, 32)", simulator)


if __name__ == "__main__":
    unittest.main()
