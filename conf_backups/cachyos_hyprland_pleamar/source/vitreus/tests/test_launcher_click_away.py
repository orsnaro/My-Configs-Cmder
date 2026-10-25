"""The launcher's own surface must catch clicks outside its panel."""
from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


def surface_block(source: str, name: str) -> str:
    start = source.index(f"surface {name} {{")
    depth = 0
    for i in range(start, len(source)):
        if source[i] == '{':
            depth += 1
        elif source[i] == '}':
            depth -= 1
            if depth == 0:
                return source[start:i + 1]
    raise AssertionError(f"unterminated surface {name}")


class LauncherClickAway(unittest.TestCase):
    def test_launcher_surface_has_a_click_away_outside_its_panel(self) -> None:
        source = (ROOT / 'vitreus.plm').read_text()
        block = surface_block(source, 'launcher')

        away = re.search(
            r'zone box launch_away_z\s*\{[^}]*'
            r'at:\s*screen\.width / 2[^}]*'
            r'size:\s*screen\.width, screen\.height[^}]*'
            r'active:\s*panel == launch',
            block,
        )
        self.assertIsNotNone(away, 'the launcher needs a full-screen click-away zone')
        self.assertIn('on press launch_away_z { panel = none }', block)
        self.assertIn('on press right launch_away_z { panel = none }', block)

        panel = re.search(
            r'zone box launch_panel_z\s*\{[^}]*'
            r'at:\s*pcx, bar\.y \+ dl\.hh / 2[^}]*'
            r'size:\s*dl\.w, dl\.hh',
            block,
        )
        self.assertIsNotNone(panel, 'clicks inside the launcher panel must not hit the click-away')

        # The panel blocker must be above the full-screen zone but below the
        # launcher's own controls, which are declared after it.
        away_at = block.index('zone box launch_away_z')
        panel_at = block.index('zone box launch_panel_z')
        first_control = block.index('zone box launch_x')
        self.assertLess(away_at, panel_at)
        self.assertLess(panel_at, first_control)

if __name__ == '__main__':
    unittest.main()
