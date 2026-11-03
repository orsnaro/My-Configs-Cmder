"""Execute backup/restore scripts against small isolated fixture homes."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[2]/'conf_backups/cachyos_hyprland_ml4w'


class RofiBackupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix='rofi-backup-', dir='/tmp/opencode')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root/'home with spaces'
        self.home.mkdir()
        self.backup = self.root/'backup with spaces'
        self.backup.mkdir()
        (self.backup/'dotfiles/.config/ml4w').mkdir(parents=True)
        for name in ('BACKUP.sh', 'RESTORE.sh'):
            shutil.copy2(SOURCE/name, self.backup/name)
        self.env = {**os.environ, 'HOME': str(self.home)}

    def write(self, root: Path, name: str, content: str) -> Path:
        path = root/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def payload(self) -> None:
        self.write(self.backup, 'dotfiles/.config/rofi/trial/base.rasi', 'fixture theme\n')
        self.write(self.backup, 'local/.local/bin/rofi-trial', '#!/bin/bash\nexit 99\n')
        self.write(self.backup, 'local/.local/lib/rofi-trial/smart.cpp', '// fixture\n')
        self.write(self.backup, 'local/.local/lib/rofi-trial/build-smart.sh',
                   '#!/bin/bash\ntouch "$HOME/plugin-built"\n')

    def restore(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(['bash', str(self.backup/'RESTORE.sh'), *args],
                              env=self.env, input='n\n', text=True, capture_output=True, timeout=10)

    def test_restore_copies_helpers_and_rebuilds_plugin_without_launching_ui(self) -> None:
        self.payload()
        result = self.restore()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.home/'.local/lib/rofi-trial/smart.cpp').is_file())
        self.assertTrue((self.home/'plugin-built').is_file())

    def test_restore_dry_run_never_builds_or_writes_launcher(self) -> None:
        self.payload()
        result = self.restore('--dry-run')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.home/'plugin-built').exists())
        self.assertFalse((self.home/'.local').exists())

    def test_restore_reports_plugin_build_failure(self) -> None:
        self.payload()
        self.write(self.backup, 'local/.local/lib/rofi-trial/build-smart.sh', '#!/bin/bash\nexit 19\n')
        self.assertNotEqual(self.restore().returncode, 0)

    def test_restore_preserves_nonexecutable_modes_and_newer_config_trees(self) -> None:
        self.payload()
        source = self.write(self.backup, 'local/.local/bin/fixture-data', 'not executable\n')
        source.chmod(0o640)
        self.write(self.backup, 'dotfiles/.config/matugen/fixture', 'keep main config\n')
        result = self.restore()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.home/'.local/bin/fixture-data').stat().st_mode & 0o777, 0o640)
        self.assertEqual((self.home/'.config/matugen/fixture').read_text(), 'keep main config\n')

    def test_backup_retains_main_private_file_exclusions(self) -> None:
        for name in ('hypr', 'kitty', 'quickshell', 'waybar', 'rofi', 'swaync', 'ml4w/scripts', 'ml4w/settings'):
            self.write(self.home, f'.config/{name}/fixture', 'public\n')
        self.write(self.home, '.config/rofi/credentials.json', 'fixture private content\n')
        self.write(self.home, '.config/rofi/.env', 'fixture private environment\n')
        result = subprocess.run(['bash', str(self.backup/'BACKUP.sh')], env=self.env,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.backup/'dotfiles/.config/rofi/credentials.json').exists())
        self.assertFalse((self.backup/'dotfiles/.config/rofi/.env').exists())

    def test_backup_includes_launcher_sources_and_listener_but_not_binary_plugin(self) -> None:
        for name in ('hypr', 'kitty', 'quickshell', 'waybar', 'rofi', 'swaync',
                     'ml4w/scripts', 'ml4w/settings'):
            self.write(self.home, f'.config/{name}/fixture', 'fixture\n')
        self.write(self.home, '.local/bin/rofi-trial', '#!/bin/bash\nexit 0\n')
        self.write(self.home, '.local/lib/rofi-trial/smart.cpp', '// fixture\n')
        self.write(self.home, '.local/lib/rofi-trial/smart.so', 'ABI-specific binary\n')
        self.write(self.home, '.local/lib/rofi-trial/dismiss-guard', 'native helper binary\n')
        self.write(self.home, '.config/ml4w/listeners/gtk-theme-switcher.sh', '#!/bin/bash\nexit 0\n')
        self.write(self.home, '.config/ml4w/themes/glass/theme.sh', '#!/bin/bash\nexit 0\n')
        result = subprocess.run(['bash', str(self.backup/'BACKUP.sh')], env=self.env,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.backup/'local/.local/bin/rofi-trial').is_file())
        self.assertTrue((self.backup/'local/.local/lib/rofi-trial/smart.cpp').is_file())
        self.assertFalse((self.backup/'local/.local/lib/rofi-trial/smart.so').exists())
        self.assertFalse((self.backup/'local/.local/lib/rofi-trial/dismiss-guard').exists())
        self.assertTrue((self.backup/'dotfiles/.config/ml4w/listeners/gtk-theme-switcher.sh').is_file())
        self.assertTrue((self.backup/'dotfiles/.config/ml4w/themes/glass/theme.sh').is_file())


if __name__ == '__main__':
    unittest.main()
