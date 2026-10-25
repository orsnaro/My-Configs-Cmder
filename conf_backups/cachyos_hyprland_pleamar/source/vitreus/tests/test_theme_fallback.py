"""Glass must not inherit the previous named palette when Iris is unavailable."""
from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class GlassFallback(unittest.TestCase):
    def setUp(self) -> None:
        self.source = (ROOT / 'vitreus.luau').read_text()

    def test_glass_fallback_exists(self) -> None:
        self.assertIn('function iris_fx.apply_glass_fallback()', self.source)
        self.assertIn('local GLASS_FALLBACK = {', self.source)
        self.assertIn('iris-last.json', self.source)
        self.assertIn('iris-card.json', self.source)

    def test_iris_failure_applies_the_fallback(self) -> None:
        start = self.source.index('local function run_iris(path, card_only)')
        block = self.source[start:self.source.index('-- ── Video wallpapers', start)]
        self.assertIn('run("which", { "iris" }', block,
                      'a missing iris command must be detected before run')
        self.assertIn('iris_fx.apply_glass_fallback()', block,
                      'a failed Iris read must not leave the old named palette')
        self.assertIn('files.write", "iris-last.json", pal', block,
                      'the last good wallpaper palette must be cached for Glass fallback')

    def test_entering_glass_without_a_known_wallpaper_does_not_wait(self) -> None:
        start = self.source.index('on("theme_pick", function(k)')
        block = self.source[start:self.source.index('on("iris_int_set"', start)]
        self.assertIn('if not iris_last_wp then iris_fx.apply_glass_fallback() end', block,
                      'Glass must paint a fallback before the first wallpaper check')
        self.assertIn('iris_cfg.look, iris_cfg.preset, iris_cfg.enabled = nil, nil, true', block)

    def test_iris_toggle_on_restores_a_glass_palette(self) -> None:
        start = self.source.index('on("iris_toggle", function()')
        block = self.source[start:self.source.index('on("theme_pick"', start)]
        self.assertIn('if not iris_last_wp then iris_fx.apply_glass_fallback() end', block,
                      'Iris on/off/on must not reset Glass to mono or a named palette')


if __name__ == '__main__':
    unittest.main()
