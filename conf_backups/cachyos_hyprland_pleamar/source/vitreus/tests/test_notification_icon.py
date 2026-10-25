"""Notification toasts must prefer a resolvable app icon over an image name."""
from __future__ import annotations

from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]


class NotificationIcon(unittest.TestCase):
    def block(self) -> str:
        source = (ROOT / 'vitreus.luau').read_text()
        start = source.index('local function icon_ok(name)')
        return source[start:source.index('    fact.nt_body_on', start)]

    def test_file_uris_are_unwrapped_before_use(self) -> None:
        block = self.block()
        self.assertIn('image:sub(1, 7) == "file://"', block,
                      'an image sent as a file:// URI must be treated as a path')

    def test_absolute_image_paths_win(self) -> None:
        block = self.block()
        self.assertIn('if image:sub(1, 1) == "/" then return image end', block,
                      'a real picture file is the most specific icon source')

    def test_a_bare_image_name_is_not_trusted_as_an_icon(self) -> None:
        block = self.block()
        self.assertIn('local function icon_ok(name)', block,
                      'an icon name must be checked before it is drawn')
        self.assertIn('known_icons[name] == true', block,
                      'the theme name set is the authority for bare icon names')
        self.assertNotIn('\n    return image', block,
                         'a bare image name has no guaranteed theme icon; it must not produce a blank slot')
        self.assertIn('return ""', block,
                      'an unknown name must fall back to the drawn bell')

    def test_logic_loads_the_theme_names_once(self) -> None:
        source = (ROOT / 'vitreus.luau').read_text()
        self.assertIn('run("vitreus-icon-names"', source,
                      'the shell must ask the icon helper for the current theme names')
        self.assertIn('known_icons = set', source)
        scene = (ROOT / 'vitreus.plm').read_text()
        self.assertIn('"vitreus-icon-names"', scene,
                      'the icon helper must be in the scene run permissions')

    def test_theme_helper_lists_real_and_rejects_missing_names(self) -> None:
        helper = ROOT / 'bin/vitreus-icon-names'
        self.assertTrue(helper.is_file(), 'the icon-name helper must exist')
        result = subprocess.run([str(helper)], capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        names = set(result.stdout.splitlines())
        self.assertIn('firefox', names)
        self.assertIn('proton-vpn-logo', names)
        self.assertNotIn('not-a-real-image', names)

    def test_empty_icon_still_falls_back_to_the_bell(self) -> None:
        block = self.block()
        self.assertIn('fact.nt_icon_on = icon ~= ""', block,
                      'an empty icon must leave the drawn bell visible')


if __name__ == '__main__':
    unittest.main()
