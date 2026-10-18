"""Today date animation continuity, cached scene geometry and preview parity."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import types
import unittest
from unittest import mock

sys.modules.setdefault('board', types.SimpleNamespace(GP0=0))
import display as led_display


class Bitmap:
    def __init__(self, width, height, colors):
        self.width, self.height = width, height
        self.cells = {}
        self.writes = 0

    def __getitem__(self, point):
        return self.cells.get(point, 0)

    def __setitem__(self, point, value):
        x, y = point
        assert 0 <= x < self.width and 0 <= y < self.height
        self.cells[point] = value
        self.writes += 1


class Palette(list):
    def __init__(self, count):
        super().__init__([0] * count)
        self.writes = 0

    def make_transparent(self, index):
        self.transparent = index

    def __setitem__(self, index, value):
        self.writes += 1
        super().__setitem__(index, value)


class TileGrid:
    def __init__(self, bitmap, pixel_shader, x=0, y=0):
        self.bitmap, self.pixel_shader = bitmap, pixel_shader
        self.x, self.y = x, y


class Font:
    ascent = 7

    def load_glyphs(self, codepoints):
        pass

    def get_glyph(self, codepoint):
        bitmap = Bitmap(5, 7, 2)
        if codepoint != ord(' '):
            for y in range(7):
                for x in range(5):
                    bitmap[x, y] = int(x in (0, 4) or y in (0, 6) or (x + y) % 3 == 0)
        return types.SimpleNamespace(bitmap=bitmap, width=5, height=7, dx=0, dy=0, shift_x=6)


class TodayDateAnimationTests(unittest.TestCase):
    def setUp(self):
        self.displayio = mock.patch.dict(sys.modules, {'displayio': types.SimpleNamespace(
            Bitmap=Bitmap, Palette=Palette, TileGrid=TileGrid, Group=list,
        )})
        self.displayio.start()
        self.addCleanup(self.displayio.stop)
        self.display = led_display.MatrixDisplay.__new__(led_display.MatrixDisplay)
        self.display.font = Font()
        self.display.display = types.SimpleNamespace(root_group=None, auto_refresh=False)
        self.display.presentation_mode = 'immediate'
        self.display._rail_auto_refresh_override = False
        self.display._record_animation_update = mock.Mock()
        self.display._refresh = mock.Mock()
        self.display._present = lambda group: setattr(self.display.display, 'root_group', group)

    def color(self, phase, width, x):
        position = led_display._today_date_sweep_position(phase, width)
        return led_display._today_date_blend_color(
            led_display._today_date_column_state(position, width, x))

    def test_constant_speed_including_cycle_boundaries(self):
        width = led_display._today_date_width(16)
        for phase in (0, 1, 3.9, 4, 4.9, 5, 9.9, 10):
            with self.subTest(phase=phase):
                before = led_display._today_date_sweep_position(phase, width)
                after = led_display._today_date_sweep_position(phase + .125, width)
                self.assertAlmostEqual(after - before, width / 40)
        self.assertEqual(led_display._today_date_sweep_position(None, width), 0)
        self.assertEqual(led_display._today_date_sweep_position(-3, width), 0)

    def test_blend_spans_pixel_columns_and_letter_boundaries(self):
        width = led_display._today_date_width(16)
        phase = 5 * 24 / width
        self.assertEqual(self.color(phase, width, 0), led_display.TODAY_DATE_COLORS[0])
        self.assertEqual(self.color(phase, width, 24), 0xffffff)
        # Adjacent columns either side of an 11px letter boundary differ.
        self.assertNotEqual(self.color(phase, width, 10), self.color(phase, width, 11))
        self.assertNotIn(self.color(phase, width, 12), (0xffffff, led_display.TODAY_DATE_COLORS[0]))

    def test_wrap_has_no_jump_and_new_sweep_overlaps_previous_tail(self):
        width = 188
        for boundary in (5, 10, 15, 20, 25, 30):
            with self.subTest(boundary=boundary):
                self.assertEqual(self.color(boundary - .00001, width, 0),
                                 self.color(boundary, width, 0))
                self.assertNotEqual(self.color(boundary, width, width - 1),
                                    self.color(boundary, width, 0))
                self.assertNotEqual(self.color(boundary + .25, width, 0),
                                    self.color(boundary, width, 0))

    def test_ordered_dither_is_fixed_and_uses_only_panel_colors(self):
        color = 0x808080
        tile = [led_display._today_date_pixel_color(color, x, y)
                for y in range(4) for x in range(4)]
        self.assertEqual(tile.count(0xffffff), 8)
        self.assertEqual(tile.count(0), 8)
        for y in range(4):
            for x in range(4):
                self.assertEqual(tile[y * 4 + x],
                                 led_display._today_date_pixel_color(color, x + 4, y + 4))
        self.assertEqual(led_display._today_date_pixel_color(0xffffff, 3, 3), 0xffffff)

    def test_cached_bitmap_preserves_existing_letter_geometry_for_every_weekday(self):
        for day in range(19, 26):
            text = led_display._today_compact_date_label('2026-10-' + str(day))
            group = []
            self.display._today_date_bitmap(group, text, 22)
            tile = group[0]
            old_mask = set()
            for index, character in enumerate(text):
                previous = []
                self.display._scaled_label(previous, character, 0xffffff,
                                           22 + index * 11, 10, scale=2)
                old_tile = previous[0]
                old_mask.update((old_tile.x + x, old_tile.y + y)
                                for (x, y), value in old_tile.bitmap.cells.items() if value)
            new_mask = {(tile.x + x, tile.y + y)
                        for (x, y), value in tile.bitmap.cells.items() if value}
            self.assertEqual(new_mask, old_mask, text)
            self.assertEqual(len(group), 1)

    def test_animation_reuses_bitmap_and_palette_and_updates_only_changed_columns(self):
        group = []
        self.display._today_date_bitmap(group, 'WEDNESDAY 21 OCT', 22)
        tile = group[0]
        initial_writes = tile.bitmap.writes
        states = self.display._today_date_column_states
        self.display._update_today_date_colors(0)
        for tick in range(1, 241):
            before = tuple(tile.pixel_shader)
            palette_writes = tile.pixel_shader.writes
            changed = self.display._update_today_date_colors(tick / 8)
            self.assertEqual(changed, before != tuple(tile.pixel_shader))
            self.assertTrue(changed, 'visible colour movement on every tick')
            self.assertLessEqual(tile.pixel_shader.writes - palette_writes, (24 + 6) * 4)
            self.assertFalse(self.display._update_today_date_colors(tick / 8))
        self.assertEqual(tile.bitmap.writes, initial_writes)
        self.assertIs(self.display._today_date_palette, tile.pixel_shader)
        self.assertIs(self.display._today_date_column_states, states)

    def test_today_scene_survives_animation_and_rebuilds_on_clock_or_date_change(self):
        screen = {'kind': 'today', 'weather': {'temperature_c': 12, 'icon': 'cloudy'}}
        self.display.show(screen, clock_time='12:34', clock_date='2026-10-21', phase=4)
        first = self.display.display.root_group
        icon = first[1]
        self.assertEqual((icon.bitmap.width, icon.bitmap.height), (22, 22))
        self.display.show(screen, clock_time='12:34', clock_date='2026-10-21', phase=4.125)
        self.assertIs(self.display.display.root_group, first)
        self.display._refresh.assert_called_with(animation_class='today_date')
        for time, date in (('12:35', '2026-10-21'), ('00:00', '2026-10-22')):
            self.display.show(screen, clock_time=time, clock_date=date, phase=6)
            scene = self.display.display.root_group
            self.assertIsNot(scene, first)
            width = len(self.display._today_date_column_states)
            self.assertEqual(scene[0].x, led_display._today_date_position(
                led_display._today_compact_date_label(date), time))
            self.assertEqual(scene[0].y, 10)
            for x in range(width):
                self.assertEqual(scene[0].pixel_shader[1 + x * 4],
                                 led_display._today_date_pixel_color(self.color(6, width, x), x, 0))
            first = scene

    def test_cadence_is_eight_capped_by_configured_cadence(self):
        for cap, expected in ((7, 7), (8, 8), (12, 8)):
            with mock.patch.object(led_display, 'MATRIX_REFRESH_FPS', cap):
                self.assertEqual(self.display.animation_cadence({'kind': 'today'}, 7), expected)

    def test_fixture_uses_same_per_pixel_dithering(self):
        captured = {}
        fixture = led_display.FixtureDisplay.__new__(led_display.FixtureDisplay)
        fixture._pixel = lambda x, y, color: None
        original_text = fixture._text
        def date_text(text, x, y, color, scale=1):
            if callable(color):
                fixture._pixel = lambda x, y, color: captured.__setitem__((x, y), color)
                original_text(text, x, y, color, scale)
                fixture._pixel = lambda x, y, color: None
        fixture._text = date_text
        fixture._draw_screen({'kind': 'today'}, 3, '2026-10-21', '12:34')
        text = led_display._today_compact_date_label('2026-10-21')
        left = led_display._today_date_position(text, '12:34')
        width = led_display._today_date_width(len(text))
        self.assertTrue(captured)
        for (x, y), color in captured.items():
            expected = led_display._today_date_pixel_color(self.color(3, width, x - left), x - left, y - 10)
            self.assertEqual(color, led_display._rgb_tuple(expected))

    @unittest.skipUnless(shutil.which('node'), 'Node is needed for simulator parity')
    def test_simulator_matches_firmware_colors_through_multiple_cycles(self):
        html = (Path(__file__).resolve().parents[1] / 'simulator/index.html').read_text()
        constants = '\n'.join(line for line in html.splitlines() if line.strip().startswith('const TODAY_DATE_'))
        functions = html[html.index('    function todayDateWidth('):html.index('    function drawTodayDate(')]
        samples = [(phase, 188, x, y) for phase in (0, .125, 4, 4.875, 5, 5.125, 10, 25.25)
                   for x in range(0, 188, 7) for y in range(4)]
        script = (constants + functions + '\nconsole.log(JSON.stringify(' + json.dumps(samples) +
                  '.map(([p,w,x,y]) => todayDatePixelColor(todayDateColumnColor(p,w,x),x,y))));')
        result = subprocess.run(['node', '-e', script], check=True, capture_output=True, text=True)
        expected = [led_display._today_date_pixel_color(self.color(p, w, x), x, y)
                    for p, w, x, y in samples]
        self.assertEqual(json.loads(result.stdout), expected)


if __name__ == '__main__':
    unittest.main()
