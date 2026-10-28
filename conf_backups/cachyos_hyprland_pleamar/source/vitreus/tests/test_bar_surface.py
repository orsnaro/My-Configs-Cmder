"""The launcher keeps its own overlay surface, and the bar never grabs the keyboard."""
from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCENE = ROOT / 'vitreus.plm'


class BarSurface(unittest.TestCase):
    def surface_line(self) -> str:
        source = SCENE.read_text()
        match = re.search(r'^    surface \{([^\n]*)\}', source, re.M)
        self.assertIsNotNone(match, 'the scene has no main surface')
        return match.group(1)

    def launcher_surface(self) -> str:
        source = SCENE.read_text()
        match = re.search(r'^    surface launcher \{(.*?)^    \}', source, re.M | re.S)
        self.assertIsNotNone(match, 'the launcher has no named overlay surface')
        return match.group(1)

    def test_launcher_is_a_full_screen_overlay(self) -> None:
        block = self.launcher_surface()
        self.assertIn('level: overlay', block)
        self.assertIn('screens: "DP-2"', block)
        self.assertIn('open: panel == launch or dl > 0.01', block)
        self.assertIn('opacity: fl * pown', block)
        self.assertNotRegex(
            block,
            r'keyboard:\s*\w+',
            'the launcher must not ask for the keyboard: the bar surface owns that policy')

    def test_the_main_surface_asks_for_keyboard_only_while_a_panel_needs_it(self) -> None:
        line = self.surface_line()
        self.assertIn('level: top', line)
        self.assertNotIn('level: overlay', line)
        self.assertIn('keyboard: on_demand while', line,
                      'each-monitor copies must not all take exclusive keyboard focus')
        self.assertIn('panel != none', line)
        self.assertIn('pk_open', line)
        self.assertNotIn('keyboard: none', line)

    def test_only_one_conditional_keyboard_is_declared(self) -> None:
        source = SCENE.read_text()
        self.assertEqual(
            len(re.findall(r'keyboard:\s*\w+\s+while\b', source)), 1,
            'Pleamar 0.4.18 keeps one scene-wide condition: a later surface\'s condition '
            'overwrites the main one, so the launcher must not declare its own')


if __name__ == '__main__':
    unittest.main()
