"""Load the dock's real settings consumer in an isolated, windowless fixture."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / 'conf_backups/cachyos_hyprland_ml4w'
SOURCE_HOME = Path(os.environ.get('ML4W_TEST_HOME', str(PROFILE / 'dotfiles')))
DOCK_SOURCE = Path(os.environ.get('DOCK_TEST_SOURCE', str(PROFILE / 'local/.local/share/ml4w-dock/DockApp')))


class DockConfigTests(unittest.TestCase):
    def test_real_dock_settings_loads_enabled_compact_preferences(self) -> None:
        with tempfile.TemporaryDirectory(prefix='dock-settings-', dir='/tmp/opencode') as directory:
            root = Path(directory)
            module = root / 'DockApp'
            module.mkdir()
            shutil.copy2(DOCK_SOURCE / 'DockSettings.qml', module / 'DockSettings.qml')
            (module / 'qmldir').write_text('module qs.DockApp\nsingleton DockSettings 1.0 DockSettings.qml\n')
            shutil.copy2(Path(__file__).with_name('dock_settings.qml'), root / 'shell.qml')
            home = root / 'home'
            config = home / '.config/ml4w-dock/config.json'
            config.parent.mkdir(parents=True)
            shutil.copy2(SOURCE_HOME / '.config/ml4w-dock/config.json', config)
            runtime = root / 'runtime'
            runtime.mkdir(mode=0o700)
            result = subprocess.run(['qs', '-p', str(root)], env={
                **os.environ, 'HOME': str(home), 'XDG_CONFIG_HOME': str(home / '.config'),
                'XDG_DATA_HOME': str(home / '.local/share'), 'XDG_CACHE_HOME': str(home / '.cache'),
                'XDG_RUNTIME_DIR': str(runtime), 'QT_QPA_PLATFORM': 'offscreen',
                'DBUS_SESSION_BUS_ADDRESS': 'unix:path=/nonexistent-dock-fixture-bus',
            }, capture_output=True, text=True, timeout=15)
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            self.assertIn('PASS: enabled compact dock preferences', output)
            self.assertNotIn('FAIL:', output)


if __name__ == '__main__':
    unittest.main()
