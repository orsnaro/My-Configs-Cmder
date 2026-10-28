"""Geometry contracts evaluated from the scene's own trial anchors, without a display."""
from __future__ import annotations

from pathlib import Path
import math
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class Geometry:
    """Evaluate the numeric subset used by the bar's declarative layout."""

    def __init__(self, tray_count: int, tm: float = 0) -> None:
        scene = (ROOT / 'vitreus.plm').read_text()
        geometry = ROOT / 'pages/trial_geometry.plm'
        if geometry.exists():
            scene += '\n' + geometry.read_text()
        title = ROOT / 'pages/bar_title.plm'
        if title.exists():
            scene += '\n' + title.read_text()
        scene += '\n' + (ROOT / 'pages/bar_icons.plm').read_text()
        self.expressions = dict(re.findall(r'^\s*let ([\w.]+) = ([^\n]+)', scene, re.M))
        self.values: dict[str, float] = {
            'screen.width': 2560, 'tn': tray_count, 'tm': tm, 'th.t': 0, 'lf.w': 0,
            'lm': 0, 'cu': 1.35, 'ob.y': 0, 'trial_workspaces.count': 9,
            'wrn': 0, 'tasks.count': 0, 'tb_title_w.width': 0,
            'bar_zs': 1, 'sg': 0, 'nt_size': 1,
            'tb_update_icon_w.width': 18, 'tb_update_count_w.width': 13,
            'tb_alert_icon_w.width': 18, 'tb_alert_count_w.width': 13,
        }
        self.values['ob.x'] = self.value('tb.ws') + 10 * self.value('u')

    def value(self, name: str) -> float:
        if name in self.values:
            return self.values[name]
        if name not in self.expressions:
            raise AssertionError(f'missing scene geometry anchor: {name}')
        expression = self.expressions[name].split('//', 1)[0].strip().replace('if(', 'choose(')
        functions = {'min': min, 'max': max, 'floor': math.floor, 'mix': lambda a, b, t: a + (b - a) * t,
                     'clamp': lambda v, a, b: max(a, min(b, v)),
                     'choose': lambda c, a, b: a if c else b, 'and': None, 'or': None, 'not': None}

        def replace(match: re.Match[str]) -> str:
            token = match.group()
            return token if token in functions else repr(self.value(token))

        numeric = re.sub(r'[A-Za-z_][\w.]*', replace, expression)
        if re.search(r'[^\d\s.+*/(),\-A-Za-z=<>]', numeric):
            raise AssertionError(f'unsupported numeric geometry: {expression}')
        result = float(eval(numeric, {'__builtins__': {}}, functions))
        self.values[name] = result
        return result


class TrialLayoutTests(unittest.TestCase):
    def text_style(self, source: str, name: str) -> str:
        match = re.search(r'text ' + re.escape(name) + r'\s*\{([^\n]+)', source)
        self.assertIsNotNone(match, f'missing preview text: {name}')
        assert match is not None
        return match.group(1)

    def trial_workspace(self) -> str:
        source = (ROOT / 'pages/bar_icons.plm').read_text()
        start = source.index('component TrialWorkspace(')
        return source[start:source.index('\n    group {', start)]

    def tile_scale(self, active: float, hover: float) -> float:
        g = Geometry(3)
        g.values.update({'tile_active': active, 'tile_hover': hover})
        return g.value('tile_scale')

    def dot_radius(self, active: float, hover: float) -> float:
        g = Geometry(3)
        g.values.update({'tile_active': active, 'tile_hover': hover})
        return g.value('dot_radius')

    def test_hardware_pairs_have_balanced_padding_and_tighter_slot_gaps(self) -> None:
        source = (ROOT / 'pages/trial_status.plm').read_text()
        g = Geometry(3)
        for left, width, first, second in [
            ('tb.metrics', 'tb.load_w', 'trial_cpu', 'trial_gpu'),
            ('tb.memory', 'tb.memory_w', 'trial_ram', 'trial_vram'),
        ]:
            with self.subTest(pair=(first, second)):
                bounds: list[tuple[float, float]] = []
                for name in (first, second):
                    style = self.text_style(source, name)
                    self.assertIn('anchor: center;', style, 'readings must be centered in stable slots')
                    self.assertIn('align: center;', style)
                    at = re.search(r'at: ([\w.]+),', style)
                    slot = re.search(r'width: ([\w.]+);', style)
                    assert at is not None and slot is not None
                    x, w = g.value(at.group(1)), g.value(slot.group(1))
                    bounds.append((x - w / 2, x + w / 2))
                self.assertAlmostEqual(bounds[0][0] - g.value(left), 14)
                self.assertAlmostEqual(g.value(left) + g.value(width) - bounds[1][1], 14)
                self.assertAlmostEqual(bounds[1][0] - bounds[0][1], 8)

    def test_hardware_highlights_have_an_even_twelve_pixel_gap(self) -> None:
        g = Geometry(3)
        self.assertAlmostEqual(g.value('tb.memory') - (g.value('tb.metrics') + g.value('tb.load_w')), 12)

    def test_hardware_slots_leave_room_for_full_load_and_gib_readings(self) -> None:
        g = Geometry(3)
        # Measured from the bundled Space Grotesk at 13px/600; allow 2px headroom.
        for slot, measured_width in [('tb.load_cell_w', 60.91),
                                     ('tb.mem_cell_w', 84.93), ('tb.vmem_cell_w', 92.68)]:
            with self.subTest(slot=slot):
                self.assertGreaterEqual(g.value(slot), measured_width + 2)

    def test_readings_stay_close_without_crowding_full_load_and_capacity(self) -> None:
        g = Geometry(3)
        #  Measured at 13px/600 from the bundled Space Grotesk (the slot-headroom test's numbers):
        #  the pairs read tight, but even two full-width readings keep a pixel-clear gap.
        for first, second, widths in [
            ('tb.cpu', 'tb.gpu', (60.91, 60.91)),
            ('tb.mem', 'tb.vmem', (84.93, 92.68)),
        ]:
            with self.subTest(pair=(first, second)):
                gap = g.value(second) - g.value(first) - sum(widths) / 2
                self.assertGreaterEqual(gap, 8)
                self.assertLessEqual(gap, 22)

    def test_trial_symbols_use_preview_font_size_and_weight(self) -> None:
        source = (ROOT / 'pages/trial_status.plm').read_text()
        for name in ['system_update', 'volume_up', 'volume_off', 'mic',
                     'mic_off', 'bedtime', 'notifications', 'power_settings_new']:
            with self.subTest(name=name):
                style = self.text_style(source, f'"{name}"')
                self.assertRegex(style, r'size: 18;')
                self.assertRegex(style, r'weight: 400;')
                self.assertIn('family: "Material Symbols Outlined"', style)
        style = self.text_style((ROOT / 'pages/bar_icons.plm').read_text(), '"tune"')
        self.assertIn('size: 18;', style)
        self.assertIn('weight: 400;', style)

    def test_horizontal_bar_drops_the_search_and_overview_icons(self) -> None:
        #  The launcher and the overview still have their key binds; only their buttons leave the bar.
        icons = (ROOT / 'pages/bar_icons.plm').read_text()
        self.assertNotIn('text "search"', icons)
        self.assertEqual(icons.count('* bs.ws * lm'), 3,
                         'the overview glyph shows only in the left strip')
        glass = (ROOT / 'pages/bar_glass.plm').read_text()
        self.assertIn('active: bs.ws > 0.5 and lm > 0.5', glass)
        self.assertRegex(glass, r'zone box sr_hit \{[^\n]*active: bs\.sr > 0\.5 and lm > 0\.5')

    def test_pomodoro_icon_has_left_the_bar(self) -> None:
        #  The bar shows no timer icon and no zone: the pomo tool is started from its own side now.
        status = (ROOT / 'pages/trial_status.plm').read_text()
        geometry = (ROOT / 'pages/trial_geometry.plm').read_text()
        self.assertNotIn('"timer"', status)
        self.assertNotIn('trial_pomo_hit', status)
        self.assertNotIn('tb.pomo', geometry)

    def test_weather_and_clock_have_the_preview_typography(self) -> None:
        source = (ROOT / 'pages/trial_status.plm').read_text()
        icon = self.text_style(source, 'trial_weather_icon')
        self.assertIn('size: 14;', icon)
        self.assertIn('weight: 400;', icon)
        weather = self.text_style(source, 'trial_weather')
        self.assertIn('size: 11.5;', weather)
        self.assertIn('measure: tb_temp_w;', weather)
        clock = self.text_style(source, 'clock_hm')
        self.assertIn('size: 21;', clock)
        self.assertIn('weight: 600;', clock)
        self.assertIn('measure: tb_time_w;', clock)
        self.assertNotIn('bar_ap', source)
        for name in ['bar_date', 'trial_date_dm']:
            style = self.text_style(source, name)
            self.assertIn('size: 8.5;', style)
            self.assertIn('weight: 500;', style)
            self.assertIn('family: "Space Grotesk"', style)

    def test_clock_slot_is_dead_center(self) -> None:
        g = Geometry(3)
        self.assertAlmostEqual(g.value('tb.clock'), g.value('cx'))

    def test_measured_weather_clock_and_two_line_date_fit_their_slot(self) -> None:
        for temp_width in (22, 38, 70):
            for time_width in (35, 55):
                g = Geometry(3)
                g.values.update({'tb_temp_w.width': temp_width, 'tb_time_w.width': time_width,
                                 'tb_day_w.width': 20, 'tb_date_w.width': 29})
                c = g.value('tb.clock')
                self.assertAlmostEqual(g.value('tb.temp') - (g.value('tb.weather_icon') + 7), 4)
                self.assertAlmostEqual((g.value('tb.weather_icon') - 7 + g.value('tb.temp') + temp_width) / 2, c)
                self.assertAlmostEqual(g.value('tb.date') - 29 / 2 - (g.value('tb.time') + time_width), 7)
                self.assertLess(g.value('tb.weekday_y'), g.value('tb.date_y'))
                self.assertGreaterEqual(g.value('tb.time'), c - g.value('tb.clock_w') / 2)
                self.assertLessEqual(g.value('tb.date') + 29 / 2, c + g.value('tb.clock_w') / 2)
                self.assertLessEqual(g.value('tb.date_y') + 4.25, g.value('bar.y') + g.value('bar.h') / 2)

    def test_known_tray_symbols_keep_native_unknown_image_fallback(self) -> None:
        scene = (ROOT / 'vitreus.plm').read_text()
        self.assertIsNotNone(re.search(r'model bartrays[^\n]+symbol: text', scene), 'tray model must carry preview symbol')
        block = scene[scene.index('    component BarTray('):scene.index('    component BarPriv(')]
        style = self.text_style(block, 't.symbol')
        self.assertIn('size: 18;', style)
        self.assertIn('weight: 400;', style)
        self.assertIn('family: "Material Symbols Outlined"', style)
        self.assertIn('image t.icon', block)
        self.assertIn('show: not t.symbol_on or lm >= 0.5', block)
        self.assertRegex(block, r'on press touch \{[^}]*emit click\(t.index\)')
        self.assertRegex(block, r'on press right touch \{[^}]*emit menu\(t.index\)')

    def test_hardware_clears_the_workspace_row_including_hover(self) -> None:
        for count in (6, 7, 9, 10, 12):
            with self.subTest(count=count):
                g = Geometry(3)
                g.values['trial_workspaces.count'] = count
                hovered_right = g.value('ws.row_r') + g.value('ws.box') * (self.tile_scale(0, 1) - 1) / 2
                divider_left = g.value('tb.metrics') - 9.5 * g.value('u')
                self.assertGreaterEqual(divider_left - hovered_right, 1)

    def test_workspace_boxes_leave_three_pixels_around_the_app_icon(self) -> None:
        for orientation in (0, 1):
            with self.subTest(orientation=orientation):
                g = Geometry(3)
                g.values.update({'lm': orientation, 'cu': 1.35})
                self.assertAlmostEqual(g.value('ws.box'), 29.7)
                self.assertGreaterEqual((g.value('ws.box') - 20) / 2, 3)
                self.assertAlmostEqual(g.value('ws.icon_cross'), g.value('ws.cross'))
                adjacent_gap_on_hover = g.value('ws.step') - g.value('ws.box') * (
                    self.tile_scale(0, 1) + self.tile_scale(1, 0)) / 2
                self.assertGreaterEqual(adjacent_gap_on_hover, 2)

    def test_workspace_number_labels_are_removed_from_both_bars(self) -> None:
        for path in ('pages/bar_icons.plm', 'pages/lite_bars.plm'):
            with self.subTest(path=path):
                self.assertNotIn('text "{w.id}"', (ROOT / path).read_text())

    def test_workspace_marks_carry_a_static_glyph(self) -> None:
        source = (ROOT / 'pages/bar_icons.plm').read_text()
        glyph = self.text_style(source, 'w.static_icon')
        self.assertIn('at: tile_x, tile_y', glyph)
        self.assertIn('size: 20;', glyph)
        self.assertIn('weight: 400;', glyph)
        self.assertIn('color: if(uwu and tile_active > 0.5, deep, onmint);', glyph)
        self.assertIn('opacity: bs.ws * min(100%, if(w.occupied, 100%, 38%) + 62% * tile_active + 15% * touch.hover); show: primary or w.occupied', glyph)
        self.assertIn('family: "Material Symbols Outlined"', glyph)

    def test_main_workspace_glyphs_are_static_but_side_strips_stay_dynamic(self) -> None:
        source = (ROOT / 'pages/bar_icons.plm').read_text()
        self.assertIn('text w.static_icon', source)
        self.assertNotIn('text w.icon', source)
        model = (ROOT / 'vitreus.plm').read_text()
        self.assertIn('model trial_workspaces max 64 { id: number; slot: number; icon: text; static_icon: text; occupied: bool }', model)
        logic = (ROOT / 'logic/trial_status.luau').read_text()
        table = logic[logic.index('local ws_static_icons ='):logic.index('local function ws_static_icon')]
        self.assertEqual(
            re.findall(r'"([^"]+)"', table),
            ['home', 'folder', 'language', 'edit_note', 'forum',
             'mail', 'terminal', 'dashboard', 'sports_esports'])
        self.assertIn('static_icon = ws_static_icon(id)', logic)
        self.assertIn('static_icon = ws_static_icon(active)', logic)
        lite = (ROOT / 'pages/lite_bars.plm').read_text()
        self.assertIn('text w.icon', lite, 'the side strips must keep the dynamic glyph')

    def test_workspace_scales_and_dot_radii_follow_active_and_hover(self) -> None:
        for active, hover, scale, radius in [
            (0, 0, 1, 3.5),
            (1, 0, 1.03, 4.9),
            (0, 1, 1.065, 4.725),
            (1, 1, 1.065, 4.9),
        ]:
            with self.subTest(active=active, hover=hover):
                self.assertAlmostEqual(self.tile_scale(active, hover), scale)
                self.assertAlmostEqual(self.dot_radius(active, hover), radius)

    def test_workspace_switch_animates_like_the_hover(self) -> None:
        block = self.trial_workspace()
        #  The tile that becomes active rides the same spring a hovered one does.
        self.assertIn('prop tile_active = 0 ~pop', block)
        self.assertIn('prop tile_hover = 0 ~pop', block)

    def test_primary_workspaces_keep_a_faded_mark_and_only_empty_secondary_workspaces_use_a_dot(self) -> None:
        block = self.trial_workspace()
        body = re.search(r'\n        body \{(.*?)\n        \}', block, re.S)
        self.assertIsNotNone(body, 'missing workspace body')
        assert body is not None
        self.assertIn('if(w.occupied, 85%, 30%)', body.group(1))
        self.assertIn('show: primary or w.occupied', body.group(1))
        self.assertIn(
            'opacity: bs.ws * min(100%, if(w.occupied, 100%, 38%) + 62% * tile_active + 15% * touch.hover); '
            'show: primary or w.occupied',
            self.text_style(block, 'w.static_icon'))
        dot = re.search(r'ellipse \{([^\n]+)', block)
        self.assertIsNotNone(dot, 'empty secondary workspaces need their dot')
        assert dot is not None
        self.assertIn('at: tile_x, tile_y', dot.group(1))
        self.assertIn('radius: dot_radius', dot.group(1))
        self.assertIn('color: mix(ink, mint, tile_active)', dot.group(1))
        self.assertIn('opacity: (0.65 + 0.35 * tile_active) * bs.ws', dot.group(1))
        self.assertIn('show: not primary and not w.occupied', dot.group(1))

    def test_workspace_active_growth_keeps_two_pixels_and_the_glyph_in_the_bar(self) -> None:
        g = Geometry(3)
        tile, step = g.value('ws.box'), g.value('ws.step')
        #  A hovered 29.7 box must not reach the active neighbour's half.
        self.assertGreaterEqual(step - tile * (self.tile_scale(0, 1) + self.tile_scale(1, 0)) / 2, 2)
        half_tile = tile * self.tile_scale(1, 1) / 2
        top = g.value('bar.y') - g.value('bar.h') / 2
        bottom = g.value('bar.y') + g.value('bar.h') / 2
        self.assertGreaterEqual(g.value('ws.icon_cross') - half_tile, top)
        self.assertLessEqual(g.value('ws.icon_cross') + half_tile, bottom)

    def test_workspace_full_slot_touch_zone_is_unchanged(self) -> None:
        block = self.trial_workspace()
        zone = re.search(r'zone box touch \{([^\n]+)', block)
        self.assertIsNotNone(zone, 'missing full-slot touch zone')
        assert zone is not None
        self.assertIn('at: mix(tile_along, lf.x, lm), mix(bar.y, tile_along, lm)', zone.group(1))
        self.assertIn('size: mix(ws.step, 40 * u, lm), mix(bar.h, ws.step, lm)', zone.group(1))
        self.assertIn('cursor: pointer', zone.group(1))
        self.assertIn('active: bs.ws > 0.5', zone.group(1))
        self.assertIn('on press touch { emit pick(w.id) }', block)

    def test_workspace_buttons_beyond_five_use_the_same_model_and_action(self) -> None:
        scene = (ROOT / 'vitreus.plm').read_text()
        self.assertRegex(scene, r'model trial_workspaces max 64\s*\{')
        icons = (ROOT / 'pages/bar_icons.plm').read_text()
        self.assertIn('for w in trial_workspaces { TrialWorkspace(w, pick: go) }', icons)
        self.assertIn('on press touch { emit pick(w.id) }', icons)
        self.assertNotIn('body ws_plus_icon', icons)
        self.assertNotIn('text "{ws.active}"', icons)
        glass = (ROOT / 'pages/bar_glass.plm').read_text()
        self.assertNotIn('zone box ws.hit.', glass, 'legacy zones must not intercept dynamic buttons')
        self.assertNotIn('zone box ws_plus', glass)

    def test_workspace_expansion_keeps_metrics_before_the_title(self) -> None:
        for count in (6, 9, 12):
            with self.subTest(count=count):
                g = Geometry(3)
                g.values['trial_workspaces.count'] = count
                self.assertAlmostEqual(g.value('tb.ws_row_r'), g.value('ws.row_r'))
                self.assertLess(g.value('tb.ws_row_r'), g.value('tb.metrics'))
                self.assertLess(g.value('tb.hw_r'), g.value('tb.ptitle_l'))
                self.assertLess(g.value('tb.ptitle_l'), g.value('tb.ptitle_r'))
                self.assertLess(g.value('tb.ptitle_r'), g.value('tb.clock_l'))

    def test_primary_workspaces_are_derived_from_the_id_and_auto_hide_is_gone(self) -> None:
        logic = (ROOT / 'logic/trial_status.luau').read_text()
        self.assertNotIn('ws_auto_hide', logic)
        icons = (ROOT / 'pages/bar_icons.plm').read_text()
        self.assertIn('let primary = w.id <= 7', icons)

    def test_workspace_app_glyphs_come_from_the_compositor_without_polling(self) -> None:
        source = (ROOT / 'logic/trial_status.luau').read_text()
        self.assertIn('socket2.sock', source, 'the glyphs follow the compositor socket')
        self.assertIn('["brave-browser"] = "language"', source)
        self.assertIn('kitty = "terminal"', source)
        self.assertIn('["md.obsidian.obsidian"] = "edit_note"', source)
        self.assertIn('run("hyprctl", { "clients" }', source)
        self.assertIn('sys.watch("workspaces"', source)
        self.assertIn('text["ws_app" .. n]', source)
        tracker = source.split('--  The workspace app glyphs')[1]
        for event in ('openwindow', 'closewindow', 'movewindow', 'activewindow'):
            with self.subTest(event=event):
                self.assertIn(f'"{event}"', tracker, 'the four window events drive the glyphs')
        self.assertNotIn('every(', tracker, 'the glyphs are event-driven, never polled')

    def test_inline_hardware_and_icon_counts_share_one_baseline(self) -> None:
        source = (ROOT / 'pages/trial_status.plm').read_text()
        names = ['trial_cpu', 'trial_gpu', 'trial_ram', 'trial_vram',
                 'trial_updates', '"volume_up"', '"{audio.volume * 100, 0}%"',
                 '"notifications"', '"{nt_hist.count}"']
        geometry = Geometry(3)
        for name in names:
            with self.subTest(name=name):
                match = re.search(r'text ' + re.escape(name) + r'\s*\{\s*at:\s*([^;]+)', source)
                self.assertIsNotNone(match, f'missing rendered inline widget {name}')
                assert match is not None
                y = match.group(1).split(',', 1)[1].strip()
                self.assertAlmostEqual(geometry.value(y), geometry.value('bar.y'))

    def test_weather_above_clock_fits_unchanged_bar_height(self) -> None:
        geometry = Geometry(3)
        self.assertLess(geometry.value('tb.weather_y'), geometry.value('tb.clock_y'))
        middle, half = geometry.value('bar.y'), geometry.value('bar.h') / 2
        self.assertGreaterEqual(geometry.value('tb.weather_y') - 7, middle - half)
        self.assertLessEqual(geometry.value('tb.clock_y') + 12, middle + half)
        self.assertEqual(geometry.value('bar.h'), 54)

    def zone_half(self, source: str, zone: str, g: Geometry) -> float:
        """Half the pressed width a trial zone declares, read from the scene itself."""
        match = re.search(r'zone box ' + zone + r' \{([^\n]+)', source)
        self.assertIsNotNone(match, f'missing zone: {zone}')
        assert match is not None
        size = re.search(r'size: ([^,]+),', match.group(1))
        self.assertIsNotNone(size, f'missing zone size: {zone}')
        assert size is not None
        token = size.group(1).strip()
        if token in g.expressions or token in g.values:
            return g.value(token) / 2
        literal = re.fullmatch(r'([\d.]+) \* u', token)
        self.assertIsNotNone(literal, f'unsupported zone size: {token}')
        assert literal is not None
        return float(literal.group(1)) * g.value('u') / 2

    def native_controls_half(self, g: Geometry) -> float:
        """The native sliders' horizontal press width from bar_glass, not a copied number."""
        glass = (ROOT / 'pages/bar_glass.plm').read_text()
        match = re.search(r'zone box ctl_hit \{[^\n]*size: mix\(([\d.]+) \* (b?u), [\d.]+ \* b?u, lm\)', glass)
        self.assertIsNotNone(match, 'native controls zone must state its horizontal width')
        assert match is not None
        return float(match.group(1)) * g.value(match.group(2)) / 2

    def native_arm(self, scene: str, name: str) -> str:
        """The horizontal (lm < 0.5) branch of a native bar anchor, read from the scene."""
        match = re.search(r'let ' + re.escape(name) + r' = if\(lm < 0\.5, ([\w.]+),', scene)
        self.assertIsNotNone(match, f'{name} must keep its horizontal branch first')
        assert match is not None
        return match.group(1)

    def test_sections_do_not_overlap_with_empty_or_populated_tray(self) -> None:
        source = (ROOT / 'pages/trial_status.plm').read_text()
        scene = (ROOT / 'vitreus.plm').read_text()
        for tray_count in range(13):
            with self.subTest(tray_count=tray_count):
                g = Geometry(tray_count)
                #  Left of the clock: the hardware, then the title stretch, up to the clock.
                clock_l = g.value('tb.clock') - g.value('tb.clock_w') / 2
                clock_r = g.value('tb.clock') + g.value('tb.clock_w') / 2
                self.assertLess(g.value('tb.hw_r'), g.value('tb.ptitle_l'))
                self.assertLess(g.value('tb.ptitle_l'), g.value('tb.ptitle_r'))
                self.assertLess(g.value('tb.ptitle_r'), clock_l)
                #  Right cluster, left to right: the bell beside the clock, the windows and
                #  native tray, night, the volume/media/mic audio pill, the updates pill between
                #  the mic and the language layout, the native settings sliders and power at the
                #  right edge.
                night_half = self.zone_half(source, 'trial_night_hit', g)
                power_half = self.zone_half(source, 'trial_power_hit', g)
                volume_half = self.zone_half(source, 'trial_volume_hit', g)
                mic_half = self.zone_half(source, 'trial_mic_hit', g)
                keyboard_half = self.zone_half(source, 'trial_keyboard_hit', g)
                ctl = g.value(self.native_arm(scene, 'ctl.x'))
                ctl_half = self.native_controls_half(g)
                self.assertLess(clock_r, g.value('tb.alert_l'))
                self.assertLess(g.value('tb.alert_l') + g.value('tb.alert_pill_w'), g.value('tb.tray_l'))
                self.assertLess(g.value('tb.tray_r'), g.value('tb.night') - night_half)
                self.assertLessEqual(g.value('tb.night') + night_half,
                                     g.value('tb.volume') - volume_half + 1e-6)
                self.assertLessEqual(g.value('tb.volume') + volume_half, g.value('tb.media_l') + 1e-6)
                self.assertLessEqual(g.value('tb.media_r'),
                                     g.value('tb.mic_hit') - mic_half + 1e-6)
                self.assertLess(g.value('tb.mic_hit') + mic_half, g.value('tb.update_l'))
                self.assertLessEqual(g.value('tb.update_l') + g.value('tb.update_pill_w'),
                                     g.value('tb.keyboard') - keyboard_half + 1e-6)
                self.assertLessEqual(g.value('tb.keyboard') + keyboard_half, ctl - ctl_half + 1e-6)
                self.assertLessEqual(ctl + ctl_half, g.value('tb.power') - power_half + 1e-6)
                self.assertLessEqual(g.value('tb.power') + power_half, g.value('bar.r') + 1e-6)
                #  The player's buttons stay inside the audio pill, between the speaker readout
                #  and the microphone glyph.
                self.assertLessEqual(g.value('tb.audio_l'), g.value('tb.media_l'))
                self.assertLess(g.value('tb.media_l'), g.value('tb.media_ctl'))
                self.assertLess(g.value('tb.media_ctl'), g.value('tb.media_r'))
                self.assertLessEqual(g.value('tb.media_r'), g.value('tb.audio_r'))
                #  Inside the audio highlight the number hugs the speaker, and the media run
                #  clears the mic glyph.
                self.assertLessEqual(g.value('tb.volume') - (g.value('tb.volume_icon') + 7), 7)

    def test_notification_pill_sits_close_to_the_clock(self) -> None:
        source = (ROOT / 'pages/trial_status.plm').read_text()
        #  Visually unchanged: the same plate recipe and the same press action as before.
        self.assertIn(
            'box { from: tb.alert_l, tb.row - 14 * u; size: tb.alert_pill_w, 28 * u; '
            'corner: 7 * u; color: mint; opacity: 4% }', source)
        self.assertIn('on press trial_alert_hit { pending = none; panel_scr = screen.index; '
                      'panel = controls; emit trial_alerts_open }', source)
        for tray_count in range(13):
            with self.subTest(tray_count=tray_count):
                g = Geometry(tray_count)
                clock_r = g.value('tb.clock') + g.value('tb.clock_w') / 2
                #  The bell sits 2u past the reserved clock width: close enough to read as part
                #  of the centre, clear of the clock's own hit area.
                self.assertAlmostEqual(g.value('tb.alert_l') - clock_r, 2 * g.value('u'))
                self.assertLess(g.value('tb.alert_l') + g.value('tb.alert_pill_w'),
                                g.value('tb.tray_l'))

    def test_tray_apps_keep_bookend_separators_and_native_anchors(self) -> None:
        status = (ROOT / 'pages/trial_status.plm').read_text()
        scene = (ROOT / 'vitreus.plm').read_text()
        #  No divider is left at the old audio edge; only the hardware divider and the pair of
        #  slim tray bookends remain in the trial section.
        self.assertNotIn('tb.audio_l - 10 * u', status)
        bookends = re.findall(r'box \{ at: ([^,]+), tb\.row; size: u, 20 \* u; '
                              r'color: mint; opacity: 20%', status)
        self.assertEqual(bookends, ['tb.metrics - 9 * u', 'tb.tray_sep_l', 'tb.tray_sep_r'])
        for anchor in ('tb.tray_sep_l', 'tb.tray_sep_r'):
            with self.subTest(anchor=anchor):
                #  An empty or hidden tray must not leave orphan dividers.
                self.assertIn(f'box {{ at: {anchor}, tb.row; size: u, 20 * u; '
                              'color: mint; opacity: 20%; show: tn > 0.02 }', status)
        g = Geometry(3)
        self.assertAlmostEqual(g.value('tb.tray_l') - g.value('tb.tray_sep_l'), 8 * g.value('u'))
        self.assertAlmostEqual(g.value('tb.tray_sep_r') - g.value('tb.tray_r'), 8 * g.value('u'))
        self.assertAlmostEqual(g.value('tb.tray_l'), g.value('tb.tray') - g.value('fw.tray') / 2)
        self.assertAlmostEqual(g.value('tb.tray_r'), g.value('tb.tray') + g.value('fw.tray') / 2)
        #  The native tray and sliders still consume the trial anchors they are given.
        self.assertEqual(self.native_arm(scene, 'tr.x'), 'tb.tray')
        self.assertEqual(self.native_arm(scene, 'ctl.x'), 'tb.controls')
        tray = g.value(self.native_arm(scene, 'tr.x'))
        self.assertLess(g.value('tb.tray_l'), tray)
        self.assertLess(tray, g.value('tb.tray_r'))
        self.assertAlmostEqual(Geometry(0).value('fw.tray'), 0)

    def test_running_window_strip_sits_beside_the_tray(self) -> None:
        for tray_count in (0, 1, 3, 5, 8):
            for windows in range(13):
                with self.subTest(tray=tray_count, windows=windows):
                    g = Geometry(tray_count)
                    g.values['wrn'] = windows
                    u = g.value('u')
                    n = min(windows, 12)
                    win_w = g.value('tb.win_w')
                    gap = g.value('tb.win_gap')
                    step = g.value('tb.win_step')
                    self.assertAlmostEqual(g.value('tb.win_n'), n)
                    self.assertLessEqual(step, 24 * u + 1e-6)
                    self.assertGreaterEqual(step, 18 * u - 1e-6)
                    if n:
                        self.assertAlmostEqual(win_w, (n - 1) * step + 18 * u)
                    else:
                        self.assertAlmostEqual(win_w, 0)
                    self.assertAlmostEqual(gap, 12 * u * min(1, n))
                    win_l, win_r = g.value('tb.win_l'), g.value('tb.win_r')
                    tray_l = g.value('tb.tray_l')
                    self.assertAlmostEqual(win_r, tray_l - gap)
                    self.assertAlmostEqual(win_l + win_w, win_r)
                    self.assertAlmostEqual(g.value('tb.win'), (win_l + win_r) / 2)
                    #  The update pill sits between the mic and language layout and does not move;
                    #  windows grow left of the tray into the free centre space, tightening their
                    #  gap when the right cluster is crowded.
                    base = Geometry(tray_count)
                    self.assertAlmostEqual(g.value('tb.update_l'), base.value('tb.update_l'))
                    self.assertAlmostEqual(g.value('tb.mic'), base.value('tb.mic'))
                    self.assertLessEqual(g.value('tb.alert_l') + g.value('tb.alert_pill_w') + 12 * u,
                                         win_l + 1e-6)
                    self.assertAlmostEqual(g.value('tb.clock'), base.value('tb.clock'))
                    if windows:
                        self.assertLess(win_l, win_r)
                        self.assertLess(win_r, g.value('tb.tray_sep_l'))
                        self.assertLess(win_l, g.value('tb.tray_l'))
                    else:
                        self.assertAlmostEqual(win_w, 0)
                        self.assertAlmostEqual(gap, 0)
                        self.assertAlmostEqual(win_l, tray_l)
                        self.assertAlmostEqual(win_r, tray_l)

    def test_running_window_strip_renders_beside_the_tray_and_focuses_windows(self) -> None:
        icons = (ROOT / 'pages/bar_icons.plm').read_text()
        scene = (ROOT / 'vitreus.plm').read_text()
        self.assertIn('for t in tasks { WinIcon(t, focus: task_focus, kill: task_close) { show: t.index < 12 } }', icons)
        self.assertIn('show: lm < 0.5 and wn > 0', icons)
        self.assertIn('follow wrn = min(tasks.count, 12)', scene)
        self.assertIn('let wn = min(tasks.count, 12)', scene)
        self.assertIn('tb.win', icons)
        block = scene[scene.index('    component WinIcon('):]
        block = block[:block.index('\n    }')]
        self.assertIn('image t.icon', block)
        self.assertIn('show: t.active', block)
        self.assertIn('mint', block)
        self.assertIn('on press touch { emit focus(t.index) }', block)
        self.assertIn('on press middle touch { emit kill(t.index) }', block)

    def test_window_strip_follows_hyprland_events_without_a_timer(self) -> None:
        logic = (ROOT / 'vitreus.luau').read_text()
        self.assertIn('local function watch_tasks(line)', logic)
        tracker = logic[logic.index('local function watch_tasks(line)'):]
        tracker = tracker[:tracker.index('\nend')]
        for event in ('openwindow', 'closewindow', 'activewindow',
                      'windowtitle', 'movewindow', 'workspace'):
            with self.subTest(event=event):
                self.assertIn(f'"{event}"', tracker)
        self.assertNotIn('every(', tracker)
        self.assertIn('watch_tasks(line)', logic)
        self.assertRegex(logic, r'watch_urgent\(\)\s*\n\s*refresh_tasks\(\)')

    def test_notification_toast_is_compact(self) -> None:
        scene = (ROOT / 'vitreus.plm').read_text()
        drawer = (ROOT / 'pages/osd_drawer.plm').read_text()
        g = Geometry(3)
        self.assertLessEqual(g.value('osd_w_note'), 240)
        #  The plate and its press zone take the shared width let (the volume's 316 for vol/shot).
        self.assertIn('size: osd_w * u, osd_h * u', drawer)
        #  A 30-unit tile, with the app's art mounted at the same size (no stretch).
        self.assertIn('size: 30 * u, 30 * u', drawer)
        self.assertIn('floor(30 * u + 0.5)', drawer)
        for name, size in [('nt_app', '11.5'), ('nt_title', '15'), ('nt_body', '12.5')]:
            with self.subTest(text=name):
                self.assertIn(f'size: {size};', self.text_style(drawer, name))
        self.assertIn('width: 144 * u;', self.text_style(drawer, 'nt_title'))
        self.assertIn('width: 144 * u;', self.text_style(drawer, 'nt_body'))
        act = scene[scene.index('    component NtAct('):]
        act = act[:act.index('\n    }')]
        self.assertIn('floor(62 * u + 0.5), floor(22 * u + 0.5)', act)
        self.assertRegex(scene, r'let nt_h = max\(58,')
        self.assertRegex(scene, r'let nt_th = max\(19,')

    def test_notification_plate_slides_between_kinds(self) -> None:
        scene = (ROOT / 'vitreus.plm').read_text()
        self.assertRegex(scene, r'prop os_note = 0')
        self.assertRegex(scene, r'follow os_note = if\(osd_kind == note, 1, 0\)')
        for name in ['os.px', 'do.rt', 'do.iw']:
            with self.subTest(let=name):
                match = re.search(r'let ' + re.escape(name) + r' = ([^\n]+)', scene)
                self.assertIsNotNone(match, f'missing let: {name}')
                assert match is not None
                self.assertIn('os_note', match.group(1))

    def test_notification_buttons_stay_inside_the_compact_plate(self) -> None:
        scene = (ROOT / 'vitreus.plm').read_text()
        drawer = (ROOT / 'pages/osd_drawer.plm').read_text()
        #  Two buttons and their gap fit the compact plate; a third wraps to a second line.
        self.assertRegex(drawer, r'row nt_row \{[^}]*\bwrap: 2\b')
        match = re.search(r'let nt_h = ([^\n]+)', scene)
        self.assertIsNotNone(match)
        assert match is not None
        self.assertIn('if(nt_acts.count > 2, 58,', match.group(1))
        act = scene[scene.index('    component NtAct('):]
        act = act[:act.index('\n    }')]
        self.assertIn('width: 58 * u;', act)

    def test_count_controls_share_one_pill_recipe(self) -> None:
        source = (ROOT / 'pages/trial_status.plm').read_text()
        for anchor, width in [('tb.update_l', 'tb.update_pill_w'), ('tb.alert_l', 'tb.alert_pill_w')]:
            with self.subTest(pill=anchor):
                self.assertIn(
                    f'box {{ from: {anchor}, tb.row - 14 * u; size: {width}, 28 * u; '
                    'corner: 7 * u; color: mint; opacity: 4% }', source)
        for zone, center, width in [('trial_updates_hit', 'tb.update_pill', 'tb.update_pill_w'),
                                    ('trial_alert_hit', 'tb.alert_pill', 'tb.alert_pill_w')]:
            with self.subTest(zone=zone):
                match = re.search(r'zone box ' + zone + r' \{([^\n]+)', source)
                self.assertIsNotNone(match, f'missing zone: {zone}')
                assert match is not None
                self.assertIn(f'at: {center}, tb.row;', match.group(1))
                self.assertIn(f'size: {width},', match.group(1))

    def test_count_numbers_are_unified_and_tight(self) -> None:
        source = (ROOT / 'pages/trial_status.plm').read_text()
        for name in ['trial_updates', '"{nt_hist.count}"', '"{audio.volume * 100, 0}%"']:
            with self.subTest(text=name):
                style = self.text_style(source, name)
                self.assertIn('size: 11.5;', style)
                self.assertIn('mint', style)
        g = Geometry(3)
        #  The natural-width number hugs its icon without a left-heavy unused digit slot.
        for icon, count in [('tb.update_icon', 'tb.update_count'),
                             ('tb.alert_icon', 'tb.alert_count')]:
            with self.subTest(pair=(icon, count)):
                self.assertAlmostEqual(g.value(count) - g.value(icon), 9 + 2 * g.value('u'))
        self.assertAlmostEqual(g.value('tb.alert_pill_w'), g.value('tb.update_pill_w'))
        self.assertAlmostEqual(g.value('tb.alert_pill_w'), 38 * g.value('u'))
        self.assertLess(g.value('tb.mic'), g.value('tb.update_l'))
        self.assertLess(g.value('tb.update_l') + g.value('tb.update_pill_w'),
                        g.value('tb.keyboard') - 17 * g.value('u'))

    def test_audio_pair_holds_the_player_between_them(self) -> None:
        source = (ROOT / 'pages/trial_status.plm').read_text()
        g = Geometry(3)
        u = g.value('u')
        #  The speaker readout, the 51u player run, then the microphone glyph: the player sits
        #  inside the audio pill, its centre in the gap between the two.
        self.assertAlmostEqual(g.value('tb.media_l') - g.value('tb.volume'), 31 * u)
        self.assertAlmostEqual(g.value('tb.media_r') - g.value('tb.media_l'), 51 * u)
        self.assertAlmostEqual(g.value('tb.mic') - g.value('tb.media_r'), 26 * u)
        midpoint = (g.value('tb.volume') + g.value('tb.mic')) / 2
        self.assertLess(abs(g.value('tb.media_ctl') - midpoint), 3 * u)
        #  The volume (40u) and mic (42u) press zones stay clear of the player's run.
        self.assertGreaterEqual(g.value('tb.media_l'),
                                g.value('tb.volume') + 20 * u)
        self.assertLessEqual(g.value('tb.media_r'),
                             g.value('tb.mic_hit') - 21 * u)
        #  The number hugs the speaker glyph; the pill keeps its ~15px pad left of the glyph.
        self.assertLessEqual(g.value('tb.volume') - (g.value('tb.volume_icon') + 7), 7)
        self.assertAlmostEqual((g.value('tb.volume_icon') - 7) - g.value('tb.audio_l'),
                               16 * u - 7)
        zone = re.search(r'zone box trial_volume_hit \{([^\n]+)', source)
        self.assertIsNotNone(zone)
        assert zone is not None
        self.assertIn('size: 40 * u,', zone.group(1))

    def test_microphone_gain_readout_mirrors_the_speaker_percentage(self) -> None:
        scene = (ROOT / 'vitreus.plm').read_text()
        self.assertRegex(scene, r'service audio \{[^}]*\binput: number\b')
        source = (ROOT / 'pages/trial_status.plm').read_text()
        gain = self.text_style(source, '"{audio.input * 100, 0}%"')
        self.assertIn('at: tb.mic_value', gain)
        self.assertIn('anchor: left center;', gain)
        self.assertIn('size: 11.5;', gain)
        self.assertIn('color: if(audio.input_muted, alert, mint);', gain)
        g = Geometry(3)
        self.assertAlmostEqual(g.value('tb.mic_value') + g.value('tb.mic_readout_w'),
                               g.value('tb.update_l') - g.value('tb.update_gap'))
        self.assertGreaterEqual(g.value('tb.mic_readout_w'), 28.3)
        mic_zone = re.search(r'zone box trial_mic_hit \{([^\n]+)', source)
        self.assertIsNotNone(mic_zone)
        assert mic_zone is not None
        self.assertIn('at: tb.mic_hit,', mic_zone.group(1))
        self.assertIn('size: 42 * u,', mic_zone.group(1))

    def test_volume_icon_wheel_steps_the_level(self) -> None:
        status = (ROOT / 'pages/trial_status.plm').read_text()
        scene = (ROOT / 'vitreus.plm').read_text()
        logic = (ROOT / 'vitreus.luau').read_text()
        #  The wheel over the bar's audio cluster steps the level five percent a notch.
        self.assertIn('on scroll trial_volume_hit { emit trial_volume_wheel(wheel) }', status)
        self.assertIn('event trial_volume_wheel ->', scene,
                      'the scene must declare the wheel event the bar emits')
        handler = logic[logic.index('on("trial_volume_wheel"'):]
        handler = handler[:handler.index('end)')]
        self.assertIn('0.05', handler, 'a notch steps five percent')
        self.assertIn('math.max(0, math.min(1,', handler, 'the level stays within 0..1')
        self.assertIn('sys.call("audio.volume", vol_now)', handler)

    def test_microphone_icon_wheel_steps_the_gain(self) -> None:
        status = (ROOT / 'pages/trial_status.plm').read_text()
        scene = (ROOT / 'vitreus.plm').read_text()
        logic = (ROOT / 'vitreus.luau').read_text()
        self.assertIn('on scroll trial_mic_hit { emit trial_mic_wheel(wheel) }', status)
        self.assertIn('event trial_mic_wheel ->', scene,
                      'the scene must declare the mic wheel event the bar emits')
        self.assertIn('mic_now = a.input or 0', logic,
                      'the handler must step from the gain the service reports')
        handler = logic[logic.index('on("trial_mic_wheel"'):]
        handler = handler[:handler.index('end)')]
        self.assertIn('0.05', handler, 'a notch steps five percent')
        self.assertIn('math.max(0, math.min(1,', handler, 'the gain stays within 0..1')
        self.assertIn('sys.call("audio.input", mic_now)', handler)

    def test_ctrl_w_closes_every_esc_closable_surface(self) -> None:
        scene = (ROOT / 'vitreus.plm').read_text()
        escape = re.findall(r'^\s*on key Escape (while .+?) \{', scene, re.MULTILINE)
        ctrl = re.findall(r'^\s*on key Ctrl\+w (while .+?) \{', scene, re.MULTILINE)
        self.assertEqual(ctrl, escape,
                         'every Escape close rule needs the same Ctrl+W rule')
        wallpaper = (ROOT / 'pages/wallpaper.plm').read_text()
        self.assertIn('on key Ctrl+w while wpd_open { wpd_open = false }', wallpaper)

    def test_note_toast_is_a_hundred_and_ten_pixels_higher_than_ten_percent(self) -> None:
        for height in (480, 500, 768, 900, 1440):
            for osd_h in (58, 160, 320):
                with self.subTest(height=height, osd_h=osd_h):
                    g = Geometry(3)
                    g.values.update({'screen.height': height, 'osd_h': osd_h,
                                     'vol': 0, 'note': 1, 'shot': 2,
                                     'osd_kind': 1, 'lm': 0, 'bt': 0})
                    expected = max(0, height * 0.10 - 110)
                    self.assertAlmostEqual(g.value('os.cy') - g.value('os.cy_base'), expected)
                    for kind, lm, bt in [(0, 0, 0), (2, 0, 0), (1, 1, 0), (1, 0, 1)]:
                        with self.subTest(kind=kind, lm=lm, bt=bt):
                            z = Geometry(3)
                            z.values.update({'screen.height': height, 'osd_h': osd_h,
                                             'vol': 0, 'note': 1, 'shot': 2,
                                             'osd_kind': kind, 'lm': lm, 'bt': bt})
                            self.assertAlmostEqual(z.value('os.cy') - z.value('os.cy_base'), 0)

    def test_note_toast_geometry_anchors_move_together(self) -> None:
        for height, osd_h in [(768, 58), (900, 160), (1440, 320)]:
            with self.subTest(height=height, osd_h=osd_h):
                g = Geometry(3)
                g.values.update({'screen.height': height, 'osd_h': osd_h,
                                 'vol': 0, 'note': 1, 'shot': 2,
                                 'osd_kind': 1, 'lm': 0, 'bt': 0})
                u = g.value('u')
                #  The renamed base holds the drawer's original top placement, unchanged.
                baseline = g.value('yo') + g.value('th.t') + 24 * u + g.value('os.hd') / 2
                self.assertAlmostEqual(g.value('os.cy_base'), baseline)
                #  Content, its clip and the hit zone all hang from `os.ck` (the plate's middle `do.ey`).
                self.assertAlmostEqual(g.value('do.ey'), g.value('os.cy'))
                self.assertAlmostEqual(g.value('os.ck') + (8 + osd_h / 2) * u, g.value('os.cy'))
                #  The lift is notice-only: where it is active the toast's top edge clears the bar's bottom;
                #  a short screen keeps the drawer's original top placement, unchanged.
                plate_top = g.value('os.cy') - osd_h * u / 2
                baseline_top = g.value('os.cy_base') - osd_h * u / 2
                drop = max(0, height * 0.10 - 110)
                if drop > 0:
                    self.assertAlmostEqual(plate_top, baseline_top + drop)
                    self.assertGreaterEqual(plate_top, g.value('bar.y') + g.value('bar.h') / 2)
                else:
                    self.assertAlmostEqual(plate_top, baseline_top)


    def test_compact_title_footprint_stays_on_the_system_info_side(self) -> None:
        scene = (ROOT / 'vitreus.plm').read_text()
        self.assertIn('text win_title30 = ""', scene)
        self.assertEqual(scene.count('text win_title30 {'), 2,
                          'vertical title rendering must keep its compact fallbacks')
        self.assertIn('measure tb_title_w', scene)
        geometry = (ROOT / 'pages/trial_geometry.plm').read_text()
        self.assertIn('let tb.metrics = max(tb.ws + 188 * u, tb.ws_row_r + 14 * u)', geometry)
        self.assertIn('let tb.ptitle_l = tb.hw_r + 14 * u', geometry)
        self.assertIn('let tb.ptitle_max = max(48 * u, tb.clock_l - 12 * u - tb.ptitle_l)', geometry)
        self.assertIn('let tb.ptitle_w = max(48 * u, min(tb.ptitle_max, tb_title_w.width + 12 * u))', geometry)
        self.assertIn('let tb.ptitle_r = tb.ptitle_l + tb.ptitle_w', geometry)
        self.assertIn('let tb.media_r = tb.mic - 26 * u', geometry)
        self.assertIn('let tb.media_l = tb.media_r - tb.media_w', geometry)
        self.assertIn('let tb.media_ctl = (tb.media_l + tb.media_r) / 2', geometry)
        self.assertIn('let tb.volume = tb.media_l - 31 * u', geometry)
        self.assertIn('let win.x = if(lm < 0.5, tb.ptitle_l,', scene)
        self.assertIn('let win.w = mix(if(lm < 0.5, max(1, tb.ptitle_r - tb.ptitle_l),', scene)
        self.assertRegex(scene, r'let win\.w = [^\n]*sg\.tw, sg\)',
                         'the new Notches layout retains its own title stretch')
        self.assertIn('let win.xs = mix(if(lm < 0.5, win.x + 6 * u,', scene)
        self.assertRegex(scene, r'let win\.xs = [^\n]*sg\.tl \+ 6 \* bu, sg\)')
        self.assertIn('let mcx = if(lm < 0.5, tb.media_ctl,', (ROOT / 'pages/bar_glass.plm').read_text())
        glass = (ROOT / 'pages/bar_glass.plm').read_text()
        self.assertIn('measure: tb_title_w', glass)
        self.assertIn('size: 12; weight: 500; width: max(0, win.hw - 12 * u - mctl);', scene)

        g = Geometry(3, tm=1)                       # the bar along the top, with its frame
        u = g.value('u')
        g.values['tb_title_w.width'] = 168          # a typical shortened title
        self.assertAlmostEqual(g.value('tb.ptitle_w'), 168 + 12 * u)
        self.assertAlmostEqual(g.value('tb.metrics'),
                               max(g.value('tb.ws') + 188 * u,
                                   g.value('tb.ws_row_r') + 14 * u))
        self.assertAlmostEqual(g.value('tb.ptitle_l'), g.value('tb.hw_r') + 14 * u)
        self.assertLess(g.value('tb.ws_row_r'), g.value('tb.metrics'))
        self.assertLess(g.value('tb.hw_r'), g.value('tb.ptitle_l'))
        self.assertLess(g.value('tb.ptitle_l'), g.value('tb.ptitle_r'))
        self.assertLess(g.value('tb.ptitle_r'), g.value('tb.clock_l'))
        #  The player's buttons sit inside the audio pill, between the speaker and the mic.
        self.assertLess(g.value('tb.volume'), g.value('tb.media_l'))
        self.assertLess(g.value('tb.media_l'), g.value('tb.media_ctl'))
        self.assertLess(g.value('tb.media_ctl'), g.value('tb.media_r'))
        self.assertLess(g.value('tb.media_r'), g.value('tb.mic'))
        self.assertLessEqual(g.value('tb.audio_l'), g.value('tb.media_l'))
        self.assertLessEqual(g.value('tb.media_r'), g.value('tb.audio_r'))

        capped = Geometry(3, tm=1)                  # a title the run cannot hold: it clamps
        capped.values['tb_title_w.width'] = 1000
        self.assertAlmostEqual(capped.value('tb.ptitle_w'), capped.value('tb.ptitle_max'))
        self.assertAlmostEqual(capped.value('tb.ptitle_r'), capped.value('tb.clock_l') - 12 * u)


if __name__ == '__main__':
    unittest.main()
