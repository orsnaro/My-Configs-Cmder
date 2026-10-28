"""Execute Display VRR behavior without changing any live output settings."""
from __future__ import annotations

from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DisplayVrrTests(unittest.TestCase):
    def test_switch_click_target_covers_its_drawn_track_at_settings_scales(self) -> None:
        page = (ROOT / 'pages/display.plm').read_text()
        scene = (ROOT / 'vitreus.plm').read_text()
        switch = re.search(r'SettingsSwitch\(([^,]+), dtop \+ 67 \* pu, disp_vrr_pill', page)
        zone = re.search(r'zone box disp_vrr_hit \{ at: ([^,]+), [^;]+; size: ([^,]+),', page)
        label = next(line for line in page.splitlines() if 'text "VRR"' in line)
        label_x = re.search(r'pivot: floor\(([^,]+) \+ 0.5\),', label)
        component = scene[scene.index('component SettingsSwitch('):]
        width = re.search(r'let sw = ([^\n]+)', component)
        assert switch and zone and label_x and width
        for height in (768, 900, 1440):
            rs = max(0.55, min(1, height / 1350))
            values = {'spx': 0, 'pu': 1.6875 * rs, 'cu': 1.5525}
            for selected in (0, 1):
                with self.subTest(height=height, selected=selected):
                    values['k'] = selected
                    def number(expression: str) -> float:
                        return float(eval(expression, {'__builtins__': {}}, values))
                    right = number(switch.group(1))
                    left = right - number(width.group(1))
                    hit_x, hit_w = number(zone.group(1)), number(zone.group(2))
                    self.assertLessEqual(hit_x - hit_w / 2, left)
                    self.assertGreaterEqual(hit_x + hit_w / 2, right)
                    self.assertLess(number(label_x.group(1)), left)

    def test_vrr_drafts_apply_persistence_and_safety(self) -> None:
        for case in ('selected_monitor', 'apply_and_revert', 'keep_and_profiles',
                     'old_profile_and_rejection', 'timeout_and_backend'):
            with self.subTest(case=case):
                result = subprocess.run(
                    ['lua5.4', 'tests/display_vrr.lua', case], cwd=ROOT,
                    text=True, capture_output=True, timeout=10,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
