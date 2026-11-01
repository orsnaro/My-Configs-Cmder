"""Portable regressions for the backed-up themes and source-built plugin."""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

PAYLOAD = Path(__file__).resolve().parents[2]/'conf_backups/cachyos_hyprland_ml4w'


class RofiSearchTests(unittest.TestCase):
    def filter(self, theme: str, query: str, rows: str) -> list[str]:
        result = subprocess.run(['rofi', '-config', str(PAYLOAD/f'dotfiles/.config/rofi/trial/{theme}.rasi'),
                                 '-dmenu', '-i', '-filter', query, '-dump'], input=rows,
                                capture_output=True, text=True, timeout=5, check=True)
        self.assertEqual(result.stderr, '')
        return result.stdout.splitlines()

    def test_emoji_heart_does_not_include_scattered_letter_matches(self) -> None:
        self.assertEqual(self.filter('emoji', 'heart',
                                    'red heart (heart, red)\ncheck mark button (check, mark, button)\n'
                                    'face with tears of joy (face, tears, joy)\n'), ['red heart (heart, red)'])

    def test_non_emoji_menus_keep_fuzzy_abbreviations(self) -> None:
        for theme in ('base', 'clipboard'):
            with self.subTest(theme=theme):
                self.assertEqual(self.filter(theme, 'frfx', 'Firefox\nTerminal\n'), ['Firefox'])

    def test_backed_up_source_builds_plugin_against_installed_libraries(self) -> None:
        with tempfile.TemporaryDirectory(prefix='smart-build-', dir='/tmp/opencode') as directory:
            root = Path(directory)/'helpers with spaces'
            shutil.copytree(PAYLOAD/'local/.local/lib/rofi-trial', root)
            result = subprocess.run(['bash', str(root/'build-smart.sh')],
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertGreater((root/'smart.so').stat().st_size, 0)


if __name__ == '__main__':
    unittest.main()
