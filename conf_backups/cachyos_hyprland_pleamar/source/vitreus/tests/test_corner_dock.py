"""The official release's docks remain functional after merging local customizations."""
from __future__ import annotations

from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CornerDock(unittest.TestCase):
    def test_saved_dock_behavior(self) -> None:
        result = subprocess.run(['lua5.4', 'tests/corner_dock.lua'], cwd=ROOT,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('capacity: PASS', result.stdout)

    def test_the_launcher_and_both_movable_docks_are_connected(self) -> None:
        scene = (ROOT / 'vitreus.plm').read_text()
        self.assertIn('include "pages/corner_dock.plm"', scene)
        self.assertIn('include "pages/addon_dock.plm"', scene)
        rows = re.findall(r'for r in lres \{ LRow\([^\n]+', scene)
        self.assertTrue(rows)
        for row in rows:
            self.assertIn('ctx: launch_ctx', row)
        logic = (ROOT / 'vitreus.luau').read_text()
        self.assertIn('require("logic/dock")()', logic)
        self.assertIn('cdk_toggle(r.app)', logic)
        self.assertIn('cdk_corner = if(cdk_drag', (ROOT / 'pages/corner_dock.plm').read_text())
        self.assertIn('1 - adk.pick', (ROOT / 'pages/addon_dock.plm').read_text())


if __name__ == '__main__':
    unittest.main()
