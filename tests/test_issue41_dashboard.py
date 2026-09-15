import ast
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class Issue41DashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.display_source = (ROOT / "display.py").read_text()
        cls.simulator_source = (ROOT / "simulator" / "index.html").read_text()
        cls.admin_source = (ROOT / "simulator" / "admin.html").read_text()
        cls.runtime_source = (ROOT / "runtime_config.py").read_text()
        cls.publisher_source = (ROOT / "publisher.py").read_text()

    def test_python_sources_remain_syntactically_valid(self):
        ast.parse(self.display_source)
        ast.parse(self.runtime_source)
        ast.parse(self.publisher_source)

    def test_departures_keep_two_upcoming_services_without_label_row(self):
        self.assertIn('upcoming = services[1:3]', self.display_source)
        self.assertNotIn('self._label(group, "UPCOMING", 0xFFAA00, 0, 17)', self.display_source)
        self.assertIn('const upcomingServices = railServices.slice(1, 3);', self.simulator_source)
        self.assertNotIn("context.fillText('UPCOMING', 0, 64)", self.simulator_source)

    def test_weather_icon_and_temperature_replace_clock_as_one_header_group(self):
        self.assertIn('def _header_item_state(phase, weather):', self.display_source)
        self.assertIn('return "weather", int((1.0 - progress) * HEADER_SLOT_WIDTH)', self.display_source)
        self.assertIn('def _header_weather(self, group, weather, offset=0):', self.display_source)
        self.assertIn('text, icon_x, text_x = _weather_group_layout(weather, offset)', self.display_source)
        self.assertIn('x=icon_x, y=0', self.display_source)
        self.assertIn('if item == "weather":', self.display_source)
        self.assertNotIn('WEATHER_Y =', self.display_source)

        self.assertIn('function headerItemState(phase, weather)', self.simulator_source)
        self.assertIn("return { item: 'weather', offset: (1 - progress) * HEADER_SLOT_WIDTH };", self.simulator_source)
        self.assertIn('function drawWeatherGroup(weather, offset = 0)', self.simulator_source)
        self.assertIn("if (header.item === 'weather') drawWeatherGroup(screen.weather, header.offset);", self.simulator_source)
        self.assertNotIn('drawWeatherIcon(screen.weather);', self.simulator_source)

    def test_station_marquee_defaults_are_slower_and_denser(self):
        self.assertRegex(self.display_source, r'CALLING_SCROLL_SPEED\s*=\s*30\.0')
        self.assertRegex(self.display_source, r'CALLING_SCROLL_GAP\s*=\s*28')
        self.assertRegex(self.simulator_source, r'const RAIL_MARQUEE_SPEED\s*=\s*120;')
        self.assertRegex(self.simulator_source, r'const RAIL_MARQUEE_GAP\s*=\s*112;')
        self.assertIn('scroll_speed, scroll_gap = _station_scroll_settings(screen)', self.display_source)
        self.assertIn('stationMarqueeSpeed(screen)', self.simulator_source)
        self.assertIn('stationMarqueeGap(screen)', self.simulator_source)

    def test_admin_departures_has_collapsed_advanced_controls(self):
        self.assertIn('advanced_fields', self.runtime_source)
        self.assertIn('<details class="feed-advanced"><summary>Advanced</summary>', self.admin_source)
        self.assertNotIn('<details class="feed-advanced" open>', self.admin_source)
        self.assertIn("station_scroll_speed:['Station scroll speed','pixels per second']", self.admin_source)
        self.assertIn("station_list_spacing:['Station list spacing','pixels between repeated station lists']", self.admin_source)

    def test_marquee_settings_are_published_to_renderer_payload(self):
        self.assertIn('"station_scroll_speed": departures_config["station_scroll_speed"]', self.publisher_source)
        self.assertIn('"station_list_spacing": departures_config["station_list_spacing"]', self.publisher_source)
        self.assertIn('screen.get("station_scroll_speed")', self.display_source)
        self.assertIn('screen.get("station_list_spacing")', self.display_source)
        self.assertIn('screen.station_scroll_speed', self.simulator_source)
        self.assertIn('screen.station_list_spacing', self.simulator_source)

    def test_platforms_use_a_stable_column_in_hardware_and_simulator(self):
        self.assertRegex(self.display_source, r'RAIL_PLATFORM_X\s*=\s*132')
        self.assertIn('platform_x = RAIL_PLATFORM_X', self.display_source)
        self.assertRegex(self.simulator_source, r'const RAIL_PLATFORM_X\s*=\s*528;')
        self.assertIn('let platformX = RAIL_PLATFORM_X;', self.simulator_source)


if __name__ == "__main__":
    unittest.main()
