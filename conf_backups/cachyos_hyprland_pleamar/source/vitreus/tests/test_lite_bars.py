"""Geometry and policy contracts for the two flat side strips, without a display."""
from __future__ import annotations

from pathlib import Path
import math
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
LITE = ROOT / 'pages/lite_bars.plm'
SCENE = ROOT / 'vitreus.plm'
KEYWORDS: frozenset[str] = frozenset({'and', 'or', 'not'})


class Lite:
    """Evaluate the numeric subset used by the shared strip's declarative layout."""

    def __init__(self, width: float, count: int = 9) -> None:
        source = LITE.read_text()
        self.expressions = dict(re.findall(r'^\s*let ([\w.]+) = ([^\n]+)', source, re.M))
        self.values: dict[str, float] = {
            'sw': width, 'trial_workspaces.count': count,
            'ws.active': 1, 'w.id': 0, 'w.slot': 0, 'w.occupied': 1,
        }

    def value(self, name: str) -> float:
        if name in self.values:
            return self.values[name]
        if name not in self.expressions:
            raise AssertionError(f'missing lite geometry anchor: {name}')
        expression = self.expressions[name].split('//', 1)[0].strip().replace('if(', 'choose(')
        functions = {'min': min, 'max': max, 'floor': math.floor, 'mix': lambda a, b, t: a + (b - a) * t,
                     'choose': lambda c, a, b: a if c else b, 'clamp': lambda v, a, b: max(a, min(b, v))}

        def replace(match: re.Match[str]) -> str:
            token = match.group()
            return token if token in functions or token in KEYWORDS else repr(self.value(token))

        numeric = re.sub(r'[A-Za-z_][\w.]*', replace, expression)
        return float(eval(numeric, {'__builtins__': {}}, functions))


class LiteBarTests(unittest.TestCase):
    def test_workspace_has_the_native_hover_and_selection_scale_response(self) -> None:
        for active, hover, want in ((0, 0, 1), (1, 0, 1.10), (0, 1, 1.25), (1, 1, 1.25)):
            with self.subTest(active=active, hover=hover):
                g = Lite(1366)
                g.values.update(ls_active=active, ls_hover=hover)
                self.assertAlmostEqual(g.value('ls_scale'), want)

    def test_empty_workspace_dot_grows_with_selection(self) -> None:
        for active, hover, want in ((0, 0, 3.0), (1, 0, 4.2), (0, 1, 4.05), (1, 1, 4.2)):
            with self.subTest(active=active, hover=hover):
                g = Lite(1366)
                g.values.update(ls_active=active, ls_hover=hover)
                self.assertAlmostEqual(g.value('ls_dot'), want)

    def test_typography_matches_the_native_main_bar(self) -> None:
        source = LITE.read_text()
        for token, size in (('clock_hm', 19), ('"volume_up"', 18), ('w.icon', 17)):
            with self.subTest(text=token):
                match = re.search(r'text ' + re.escape(token) + r' \{([^\n]+)', source)
                self.assertIsNotNone(match, 'native workspace glyph/label must remain present')
                assert match is not None
                found = re.search(r'size:\s*([\d.]+)', match.group(1))
                assert found is not None
                self.assertEqual(float(found.group(1)), size)
        self.assertNotIn('text "{w.id}"', source, 'side workspaces no longer carry number labels')

    def test_only_the_right_strip_shrinks_workspace_glyphs(self) -> None:
        source = LITE.read_text()
        glyph = re.search(r'text w\.icon \{[^\n]*size:\s*([\d.]+)', source)
        assert glyph is not None
        for side, want in ((0, 14.5), (1, 17)):
            with self.subTest(side=side):
                g = Lite(1440 if side == 0 else 1366)
                g.values['side'] = side
                self.assertAlmostEqual(float(glyph.group(1)) * g.value('ls.icon_scale'), want)
        self.assertRegex(
            source,
            r'group \{\s*pivot: tile_x, 18\s*scale: ls\.icon_scale\s*text w\.icon',
            'only the glyph is scaled, not the background or touch zone')
        self.assertIn('ls.tile, w.slot < ls.fit, side, pick: go)', source)
        for surface, side in (('lite_dp1', 0), ('lite_hdmi', 1)):
            self.assertIn(f'LiteStrip({surface}.width, {side})', source)

    def test_background_uses_the_shared_material_component(self) -> None:
        source = LITE.read_text()
        self.assertIn('LiteMaterial(ls.w, ls.h)', source)
        self.assertIn('let lmat.corner = 10 * (1 - 0.73 * sq)', source)

    def test_shared_material_is_moved_into_the_centred_pill(self) -> None:
        source = LITE.read_text()
        moved = re.search(r'group \{\n\s*move: ls\.left, 0\n\s*LiteMaterial\(ls\.w, ls\.h\)\n\s*\}', source)
        self.assertIsNotNone(moved, 'the one shared material must ride ls.left and be given ls.w')

    def test_ram_readout_fits_between_clock_and_audio(self) -> None:
        # Moving RAM into the clock/audio slot must fail this, not just rename a let.
        for width in (640, 1366, 1440):
            with self.subTest(width=width):
                g = Lite(width)
                left = g.value('ls.ram_r') - g.value('ls.ram_w')
                self.assertGreater(left, g.value('ls.clock') + g.value('ls.clock_half'))
                self.assertLess(g.value('ls.ram_r'), g.value('ls.vol_icon') - 12)
                self.assertEqual(g.value('ls.ram_w'), 100)

    def test_only_right_monitor_bar_is_six_pixels_down_with_clearance(self) -> None:
        source = LITE.read_text()
        for name, want_y, want_reserved in (('lite_dp1', 16, 52), ('lite_hdmi', 10, 46)):
            with self.subTest(surface=name):
                block = re.search(r'surface ' + name + r' \{(.*?)\n    \}', source, re.S)
                assert block is not None
                margin = re.search(r'margin: ([\d, ]+)', block.group(1))
                reserve = re.search(r'reserve: (\d+)', block.group(1))
                assert margin is not None and reserve is not None
                margins = [int(v.strip()) for v in margin.group(1).split(',')]
                margins += [0] * (4 - len(margins))
                self.assertEqual(margins, [want_y, 0, 0, 0])
                self.assertEqual(int(reserve.group(1)) + margins[0], want_reserved)

    def test_ram_disappears_instead_of_covering_the_clock_on_a_narrow_strip(self) -> None:
        source = LITE.read_text()
        node = re.search(r'text trial_ram \{([^\n]+)', source)
        assert node is not None
        visibility = re.search(r'show: ([\w.]+)', node.group(1))
        cases = ((0, 9, False), (200, 0, False), (200, 9, False), (200, 64, False), (300, 9, False),
                 (640, 0, True), (640, 9, True), (640, 64, True), (1366, 0, True), (1366, 9, True),
                 (1366, 64, True), (1440, 9, True))
        for width, count, want in cases:
            with self.subTest(width=width, count=count):
                shown = True if visibility is None else bool(Lite(width, count).value(visibility.group(1)))
                self.assertEqual(shown, want)

    def test_geometry_keeps_workspaces_before_the_clock(self) -> None:
        for width in (200, 640, 1366, 1440, 1920):
            for count in (0, 9, 64):
                with self.subTest(width=width, count=count):
                    g = Lite(width, count)
                    drawn = min(count, g.value('ls.fit'))
                    if drawn:
                        last_right = g.value('ls.first') + (drawn - 1) * g.value('ls.step') + g.value('ls.tile') / 2
                        self.assertLessEqual(last_right, g.value('ls.ws_r'))
                        self.assertLess(last_right, g.value('ls.clock') - g.value('ls.clock_half'))

    def test_geometry_keeps_audio_after_the_clock(self) -> None:
        for width in (640, 1366, 1440):
            with self.subTest(width=width):
                g = Lite(width)
                clock_right = g.value('ls.clock') + g.value('ls.clock_half')
                self.assertGreater(g.value('ls.vol_icon'), clock_right)
                self.assertGreaterEqual(g.value('ls.vol_value'), g.value('ls.vol_icon'))
                self.assertLessEqual(g.value('ls.vol_value'), width)

    def test_boundary_widths_never_fit_a_negative_number_of_workspaces(self) -> None:
        for width in (0, 40, 100, 200):
            with self.subTest(width=width):
                self.assertGreaterEqual(Lite(width, 64).value('ls.fit'), 0)

    def test_full_volume_label_stays_inside_the_strip_and_clear_of_icon(self) -> None:
        # A full-volume label needs space for all four characters, not just its origin.
        source = LITE.read_text()
        match = re.search(r'text "\{audio\.volume[^\n]+?%" \{([^\n]+)', source)
        assert match is not None
        right_anchored = re.search(r'anchor:\s*right center', match.group(1)) is not None
        for width in (1366, 1440):
            with self.subTest(width=width):
                g = Lite(width)
                right = g.value('ls.vol_value') + (0 if right_anchored else 36)
                left = right - 36
                self.assertLessEqual(right, width - g.value('ls.pad'))
                self.assertGreaterEqual(left, g.value('ls.vol_icon') + 12)

    def test_sixty_four_workspaces_are_clipped_to_what_fits(self) -> None:
        for width in (1366, 1440):
            with self.subTest(width=width):
                g = Lite(width, 64)
                self.assertLess(g.value('ls.fit'), 64, 'the surplus must be clipped before the clock')
                self.assertGreater(g.value('ls.fit'), 8)

    def test_clock_is_centred_in_a_thirty_six_pixel_strip(self) -> None:
        for width in (1366, 1440):
            with self.subTest(width=width):
                g = Lite(width)
                self.assertAlmostEqual(g.value('ls.clock'), width / 2)
                self.assertAlmostEqual(g.value('ls.h'), 36)
                self.assertAlmostEqual(g.value('ls.mid'), 18)

    def test_the_pill_is_centred_and_never_wider_than_its_monitor(self) -> None:
        for width in (0, 200, 640, 1366, 1440):
            for count in (0, 1, 9, 64):
                with self.subTest(width=width, count=count):
                    g = Lite(width, count)
                    self.assertGreaterEqual(g.value('ls.w'), 0)
                    self.assertLessEqual(g.value('ls.w'), max(0, width - 32))
                    self.assertAlmostEqual(g.value('ls.left'), (width - g.value('ls.w')) / 2)

    def test_nine_workspaces_need_a_five_hundred_and_forty_pixel_pill(self) -> None:
        for width in (640, 1366, 1440):
            with self.subTest(width=width):
                self.assertAlmostEqual(Lite(width, 9).value('ls.w'), 540)

    def test_workspaces_and_audio_stay_inside_the_centred_pill(self) -> None:
        for width in (0, 200, 640, 1366, 1440):
            for count in (0, 1, 9, 64):
                with self.subTest(width=width, count=count):
                    g = Lite(width, count)
                    left, w = g.value('ls.left'), g.value('ls.w')
                    drawn = min(count, g.value('ls.fit'))
                    self.assertGreaterEqual(g.value('ls.fit'), 0)
                    if drawn:
                        first, step, tile = g.value('ls.first'), g.value('ls.step'), g.value('ls.tile')
                        self.assertGreaterEqual(first - tile / 2, left)
                        self.assertLessEqual(first + (drawn - 1) * step + tile / 2, left + w)
                    if g.value('ls.audio_on'):
                        zone_left = g.value('ls.vol_icon') - 12
                        self.assertGreater(zone_left, g.value('ls.clock') + g.value('ls.clock_half'))
                        self.assertGreaterEqual(zone_left, left)
                        self.assertLessEqual(zone_left + 64, left + w)

    def test_audio_is_hidden_when_the_pill_cannot_hold_it(self) -> None:
        for width in (0, 200, 640, 1366, 1440):
            for count in (0, 1, 9, 64):
                with self.subTest(width=width, count=count):
                    g = Lite(width, count)
                    self.assertAlmostEqual(g.value('ls.audio_on'), float(g.value('ls.w') >= 236))
        for width, want in ((0, False), (200, False), (640, True), (1366, True), (1440, True)):
            with self.subTest(width=width):
                self.assertEqual(bool(Lite(width, 9).value('ls.audio_on')), want)

    def test_workspace_tile_hitbox_and_centres_fit_the_thirty_six_pixel_strip(self) -> None:
        source = LITE.read_text()
        head = re.search(r'component LiteWorkspace\([^\n]*\) \{\n\s*size: ([\d.]+), ([\d.]+)', source)
        assert head is not None
        self.assertEqual([float(head.group(1)), float(head.group(2))], [24, 36])
        g = Lite(1366)
        self.assertEqual(g.value('ls.tile'), 18)
        for prefix, want in ((r'box \{', 18), (r'ellipse \{', 18),
                             (r'text w\.icon \{', 18)):
            with self.subTest(shape=prefix):
                node = re.search(prefix + r' at: tile_x, ([\d.]+);', source)
                assert node is not None
                self.assertEqual(float(node.group(1)), want)
                self.assertEqual(float(node.group(1)), g.value('ls.h') / 2)
        zone = re.search(r'zone box touch \{ at: tile_x, ([\d.]+); size: ([\d.]+), ([\d.]+)', source)
        assert zone is not None
        self.assertEqual([float(zone.group(1)), float(zone.group(2)), float(zone.group(3))], [18, 24, 36])

    def test_the_two_named_surfaces_use_their_own_width(self) -> None:
        source = LITE.read_text()
        for name, screen, side in (('lite_dp1', 'DP-1', 0), ('lite_hdmi', 'HDMI-A-2', 1)):
            with self.subTest(surface=name):
                match = re.search(r'surface ' + name + r' \{(.*?)\n    \}', source, re.S)
                self.assertIsNotNone(match, f'missing named surface {name}')
                assert match is not None
                block = match.group(1)
                self.assertIn('size: full, 36', block)
                self.assertIn('anchor: top', block)
                self.assertIn('keyboard: none', block)
                self.assertIn('reserve: 36', block)
                self.assertIn(f'screens: "{screen}"', block)
                self.assertIn(f'LiteStrip({name}.width, {side})', block)

    def test_surfaces_default_closed_and_open_only_when_main_is_away(self) -> None:
        source = LITE.read_text()
        self.assertIn('fact bar_lite_dp1 = false', source)
        self.assertIn('fact bar_lite_hdmi = false', source)
        self.assertIn('open: bar_lite_dp1', source)
        self.assertIn('open: bar_lite_hdmi', source)

    def test_strip_reuses_existing_facts_and_events(self) -> None:
        source = LITE.read_text()
        self.assertIn('for w in trial_workspaces', source)
        self.assertIn('emit pick(w.id)', source)
        self.assertIn('pick: go', source)
        self.assertIn('ws.active', source)
        self.assertIn('text clock_hm', source)
        self.assertIn('audio.volume', source)
        self.assertIn('text trial_ram', source)
        self.assertIn('emit trial_volume_wheel(wheel)', source)
        self.assertIn('emit trial_volume_toggle', source)

    def test_strip_adds_no_services_jobs_or_full_screen_input(self) -> None:
        source = LITE.read_text()
        for forbidden in ('service ', 'every(', 'spawn(', 'run(', 'shader:'):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)
        for zone in re.finditer(r'zone box \w+ \{[^\n]+', source):
            size = re.search(r'size: ([^,]+),', zone.group(0))
            self.assertIsNotNone(size)
            assert size is not None
            self.assertNotIn(size.group(1).strip(), ('sw', 'screen.width'))

    def test_main_scene_includes_the_new_part(self) -> None:
        self.assertTrue('include "pages/lite_bars.plm"' in SCENE.read_text(),
                        'the main scene must include the new part exactly once')

    def test_controller_publishes_the_lite_flags_from_the_active_monitor_set(self) -> None:
        import subprocess
        result = subprocess.run(['lua5.4', 'tests/bar_monitors.lua'], cwd=ROOT,
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('managed-migration and lite-flag contracts: PASS', result.stdout)


if __name__ == '__main__':
    unittest.main()
