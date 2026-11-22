"""Palette aliases and native GTK parsing, with no live theme changes."""
from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
STYLE = Path(os.environ.get('WALKER_TEST_STYLE', str(ROOT / 'conf_backups/cachyos_hyprland_ml4w/dotfiles/.config/walker/themes/ml4w/style.css')))
ALIASES = {'window_bg_color': 'surface', 'accent_bg_color': 'primary',
           'theme_fg_color': 'on_surface', 'error_bg_color': 'error', 'error_fg_color': 'on_error'}


class PaletteTests(unittest.TestCase):
    def test_every_walker_alias_uses_the_generated_palette(self) -> None:
        self.assertTrue(STYLE.is_file(), 'Saved Walker stylesheet is missing')
        aliases = dict(re.findall(r'@define-color\s+(\w+)\s+([^;]+);', STYLE.read_text()))
        self.assertEqual(aliases, {name: '@' + role for name, role in ALIASES.items()})

    def test_existing_walker_layout_and_palette_import_are_retained(self) -> None:
        self.assertTrue(STYLE.is_file(), 'Saved Walker stylesheet is missing')
        text = STYLE.read_text()
        for declaration in ('@import "../../colors.css";', 'background: alpha(@surface, 0.9);',
                            'padding: 20px;', 'border-radius: 20px;', 'color: @theme_fg_color;'):
            self.assertTrue(declaration in text, f'Existing Walker layout/import changed: {declaration}')

    def test_native_gtk_accepts_aliases_with_two_generated_palettes(self) -> None:
        self.assertTrue(STYLE.is_file(), 'Saved Walker stylesheet is missing')
        with tempfile.TemporaryDirectory(prefix='walker-palette-', dir='/tmp/opencode') as name:
            root = Path(name)
            style = root / 'themes/ml4w/style.css'
            style.parent.mkdir(parents=True)
            shutil.copy2(STYLE, style)
            for color in ('#102030', '#e0d0c0'):
                roles = set(ALIASES.values()) | {'on_primary'}
                (root / 'colors.css').write_text('\n'.join(f'@define-color {role} {color};' for role in roles))
                script = '''import sys, gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk
errors = []
css = Gtk.CssProvider()
css.connect("parsing-error", lambda provider, section, error: errors.append(str(error)))
css.load_from_path(sys.argv[1])
if errors:
    raise SystemExit("\\n".join(errors))
'''
                result = subprocess.run(['python3', '-c', script, str(style)], capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
