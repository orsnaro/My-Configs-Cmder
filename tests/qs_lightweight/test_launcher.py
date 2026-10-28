"""Walker routing through existing helpers; no real clipboard or daemons."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(os.environ.get('ML4W_TEST_HOME', str(ROOT / 'conf_backups/cachyos_hyprland_ml4w/dotfiles')))


class LauncherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix='walker-route-', dir='/tmp/opencode')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        for directory in ('.config/ml4w/settings', '.config/waybar', '.config/swaync', '.config/hypr/conf', '.config/walker', 'bin'):
            (self.home / directory).mkdir(parents=True)
        self.audit = self.home / 'audit'
        self.env = {**os.environ, 'HOME': str(self.home), 'PATH': str(self.home / 'bin') + ':/usr/bin:/bin', 'AUDIT': str(self.audit)}
        for name in ('walker', 'rofi', 'cliphist', 'wl-copy', 'swaync-client'):
            path = self.home / 'bin' / name
            path.write_text('#!/bin/sh\nprintf "%s %s\\n" "${0##*/}" "$*" >> "$AUDIT"\n')
            path.chmod(0o755)
        wrapper = self.home / '.config/walker/launch.sh'
        wrapper.write_text('#!/bin/sh\nexec walker "$@"\n')
        wrapper.chmod(0o755)
        waybar = self.home / '.config/waybar/launch.sh'
        waybar.write_text('#!/bin/sh\nprintf "fake-waybar\\n" >> "$AUDIT"\n')
        waybar.chmod(0o755)

    def source(self, relative: str) -> Path:
        path = SOURCE / relative
        self.assertTrue(path.is_file(), f'Missing saved configuration: {relative}')
        return path

    def test_shared_launcher_selects_walker(self) -> None:
        self.assertEqual(self.source('.config/ml4w/settings/launcher').read_text().strip(), 'walker')

    def test_real_clipboard_helper_routes_to_walker_without_reading_history(self) -> None:
        shutil.copy2(self.source('.config/ml4w/settings/launcher'), self.home / '.config/ml4w/settings/launcher')
        result = subprocess.run(['bash', str(self.source('.config/ml4w/scripts/ml4w-cliphist'))], env=self.env,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.audit.read_text() if self.audit.exists() else ''
        self.assertEqual(calls, 'walker -m clipboard -N -H\n')
        self.assertNotIn('rofi', calls)
        self.assertNotIn('cliphist', calls)

    def test_theme_presets_never_reset_launcher_to_rofi(self) -> None:
        for name in ('glass', 'modern', 'transparent'):
            with self.subTest(theme=name):
                (self.home / '.config/ml4w/settings/launcher').write_text('walker\n')
                result = subprocess.run(['bash', str(self.source(f'.config/ml4w/themes/{name}/theme.sh'))],
                                        env=self.env, capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, '', 'Theme commands must stay inside the fixture')
                self.assertEqual((self.home / '.config/ml4w/settings/launcher').read_text().strip(), 'walker')


if __name__ == '__main__':
    unittest.main()
