"""Palette switches must converge on the newest theme, even when sends race."""
from __future__ import annotations

from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PalettePush(unittest.TestCase):
    def test_single_flight_harness(self) -> None:
        result = subprocess.run(
            ['lua', str(ROOT / 'tests/palette_push.lua')],
            cwd=ROOT, capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn('PASS', result.stdout)

    def test_apply_palette_repairs_before_the_text_dedup(self) -> None:
        source = (ROOT / 'vitreus.luau').read_text()
        start = source.index('function iris_fx.apply_palette(pal)')
        block = source[start:source.index('-- What Hyprland is told', start)]
        self.assertIn('local same_text = text_out == iris_last_text', block,
                      'the dedup must be an explicit, inspectable condition')
        self.assertLess(block.index('iris_fx.set_facts(pal)'),
                        block.index('if same_text then'),
                        'facts must be refreshed even when the palette text did not change')
        self.assertLess(block.index('iris_fx.push_pal(pal)'),
                        block.index('if same_text then'),
                        'a same-theme reselect must still repair the widgets')
        self.assertIn('if same_text then iris_fx.apply_hypr(); return end', block,
                      'a same-theme reselect must also repair the Hyprland borders')

    def test_palette_uses_the_serialized_pusher(self) -> None:
        source = (ROOT / 'vitreus.luau').read_text()
        self.assertIn('local palette_push = require("logic/palette_push")', source)
        start = source.index('function iris_fx.push_pal(pal)')
        block = source[start:source.index('-- The room the bar', start)]
        self.assertIn('palette_push(scene, args)', block,
                      'each scene must go through the single-flight pusher')
        self.assertNotIn('run("pleamar"', block,
                         'the unsynchronised direct fan-out must be gone')


if __name__ == '__main__':
    unittest.main()
