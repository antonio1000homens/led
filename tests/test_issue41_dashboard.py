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

    def test_display_python_remains_syntactically_valid(self):
        ast.parse(self.display_source)

    def test_departures_keep_two_upcoming_services_without_label_row(self):
        self.assertIn('upcoming = services[1:3]', self.display_source)
        self.assertNotIn('self._label(group, "UPCOMING", 0xFFAA00, 0, 17)', self.display_source)
        self.assertIn('const upcomingServices = railServices.slice(1, 3);', self.simulator_source)
        self.assertNotIn("context.fillText('UPCOMING', 0, 64)", self.simulator_source)

    def test_temperature_replaces_clock_in_shared_header_slot(self):
        self.assertIn('def _header_item_state(phase, weather):', self.display_source)
        self.assertIn('return "temperature", int((1.0 - progress) * HEADER_SLOT_WIDTH)', self.display_source)
        self.assertIn('self._mask(group, CLOCK_X, 0, HEADER_SLOT_WIDTH, 8)', self.display_source)
        self.assertIn('function headerItemState(phase, weather)', self.simulator_source)
        self.assertIn("if (header.item === 'temperature') drawTemperature(screen.weather, header.offset);", self.simulator_source)
        self.assertIn('else drawClock(clock, header.offset);', self.simulator_source)

    def test_station_marquee_is_slower_and_more_compact(self):
        self.assertRegex(self.display_source, r'CALLING_SCROLL_SPEED\s*=\s*36\.0')
        self.assertRegex(self.display_source, r'CALLING_SCROLL_GAP\s*=\s*36')
        self.assertRegex(self.simulator_source, r'const RAIL_MARQUEE_SPEED\s*=\s*144;')
        self.assertRegex(self.simulator_source, r'const RAIL_MARQUEE_GAP\s*=\s*144;')

    def test_platforms_use_a_stable_column_in_hardware_and_simulator(self):
        self.assertRegex(self.display_source, r'RAIL_PLATFORM_X\s*=\s*132')
        self.assertIn('platform_x = RAIL_PLATFORM_X', self.display_source)
        self.assertRegex(self.simulator_source, r'const RAIL_PLATFORM_X\s*=\s*528;')
        self.assertIn('let platformX = RAIL_PLATFORM_X;', self.simulator_source)

    def test_temperature_is_not_duplicated_in_bottom_weather_renderer(self):
        matrix_weather = re.search(r'def _weather\(self, group, weather\):(.*?)\n    def show\(', self.display_source, re.S)
        self.assertIsNotNone(matrix_weather)
        self.assertNotIn('_weather_text(', matrix_weather.group(1))
        self.assertIn('function drawWeatherIcon(weather)', self.simulator_source)
        weather_icon_body = self.simulator_source.split('function drawWeatherIcon(weather)', 1)[1].split('function fitLeftText', 1)[0]
        self.assertNotIn('temperatureText(', weather_icon_body)


if __name__ == "__main__":
    unittest.main()
