"""On-demand launcher routing and explicit legacy recovery; no real clipboard."""
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
        launcher = self.home / '.local/bin/rofi-trial'
        launcher.parent.mkdir(parents=True)
        launcher.write_text('#!/bin/sh\nprintf "rofi-launcher %s\\n" "$*" >> "$AUDIT"\n')
        launcher.chmod(0o755)
        sherlock = self.home / '.local/bin/sherlock-launch'
        sherlock.write_text('#!/bin/sh\nprintf "sherlock-launcher %s\\n" "$*" >> "$AUDIT"\n')
        sherlock.chmod(0o755)
        waybar = self.home / '.config/waybar/launch.sh'
        waybar.write_text('#!/bin/sh\nprintf "fake-waybar\\n" >> "$AUDIT"\n')
        waybar.chmod(0o755)

    def source(self, relative: str) -> Path:
        path = SOURCE / relative
        self.assertTrue(path.is_file(), f'Missing saved configuration: {relative}')
        return path

    def test_shared_launcher_routes_apps_to_resident_sherlock(self) -> None:
        shutil.copy2(self.source('.config/ml4w/settings/launcher'), self.home / '.config/ml4w/settings/launcher')
        result = subprocess.run(['bash', str(self.source('.config/hypr/scripts/launcher.sh'))],
                                env=self.env, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.audit.read_text(), 'sherlock-launcher apps\n')

    def test_real_clipboard_helper_routes_to_walker_without_reading_history(self) -> None:
        (self.home / '.config/ml4w/settings/launcher').write_text('walker\n')
        result = subprocess.run(['bash', str(self.source('.config/ml4w/scripts/ml4w-cliphist'))], env=self.env,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.audit.read_text() if self.audit.exists() else ''
        self.assertEqual(calls, 'walker -m clipboard -N -H\n')
        self.assertNotIn('rofi', calls)
        self.assertNotIn('cliphist', calls)

    def test_clipboard_button_uses_preview_and_toggle_wrapper(self) -> None:
        shutil.copy2(self.source('.config/ml4w/settings/launcher'), self.home / '.config/ml4w/settings/launcher')
        result = subprocess.run(['bash', str(self.source('.config/ml4w/scripts/ml4w-cliphist'))],
                                env=self.env, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.audit.read_text(), 'rofi-launcher clipboard\n')

    def test_theme_presets_preserve_rofi_and_explicit_legacy_selection(self) -> None:
        for name in ('glass', 'modern', 'transparent', 'glass-walker', 'modern-walker'):
            for launcher in ('rofi', 'walker'):
                with self.subTest(theme=name, launcher=launcher):
                    (self.home / '.config/ml4w/settings/launcher').write_text(launcher+'\n')
                    result = subprocess.run(['bash', str(self.source(f'.config/ml4w/themes/{name}/theme.sh'))],
                                            env=self.env, capture_output=True, text=True, timeout=10)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stderr, '', 'Theme commands must stay inside the fixture')
                    self.assertEqual((self.home / '.config/ml4w/settings/launcher').read_text().strip(), launcher)

    def test_saved_gtk_listener_restarts_only_explicit_walker_for_both_theme_modes(self) -> None:
        gtk = self.home/'.config/gtk-3.0'
        gtk.mkdir()
        cache = self.home/'.cache/ml4w/hyprland-dotfiles'
        cache.mkdir(parents=True)
        (cache/'current_wallpaper').write_text('/synthetic/wallpaper.png\n')
        hook = self.home/'.config/hypr/scripts/gtk.sh'
        hook.parent.mkdir(parents=True)
        hook.write_text('#!/bin/sh\nexit 0\n')
        hook.chmod(0o755)
        (self.home/'.config/waybar/launch.sh').write_text('#!/bin/sh\nexit 0\n')
        for name in ('matugen', 'qs', 'pkill', 'walker'):
            command = self.home/'bin'/name
            command.write_text('#!/bin/sh\nprintf "%s %s\\n" "${0##*/}" "$*" >> "$AUDIT"\n')
            command.chmod(0o755)
        watcher = self.home/'bin/inotifywait'
        watcher.write_text('#!/bin/sh\nprintf "%s CLOSE_WRITE settings.ini\\n" "$HOME/.config/gtk-3.0/"\n')
        watcher.chmod(0o755)
        for preference in ('0', '1'):
            for launcher in ('rofi', 'walker'):
                with self.subTest(preference=preference, launcher=launcher):
                    (gtk/'settings.ini').write_text(f'gtk-application-prefer-dark-theme={preference}\n')
                    (self.home/'.config/ml4w/settings/launcher').write_text(launcher+'\n')
                    self.audit.unlink(missing_ok=True)
                    # Keep the event loop in this shell so wait joins its Walker child.
                    result = subprocess.run(['bash', '-O', 'lastpipe', '-c', 'source "$1"; wait', 'fixture',
                                             str(self.source('.config/ml4w/listeners/gtk-theme-switcher.sh'))],
                                            env=self.env, capture_output=True, text=True, timeout=10)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stderr, '')
                    calls = self.audit.read_text()
                    self.assertEqual('walker --gapplication-service' in calls, launcher == 'walker')
                    self.assertEqual('pkill -x walker' in calls, launcher == 'walker')


if __name__ == '__main__':
    unittest.main()
