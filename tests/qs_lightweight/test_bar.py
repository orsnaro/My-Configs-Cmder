"""Exercise real bar components offscreen with isolated cache/process inputs."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
BACKUP = ROOT / 'conf_backups/cachyos_hyprland_ml4w/dotfiles/.config/quickshell'
SOURCE = Path(os.environ.get('QS_TEST_SOURCE', str(BACKUP)))
FIXTURES = Path(__file__).resolve().parent


class BarTests(unittest.TestCase):
    def run_fixture(self, name: str, files: tuple[str, ...]) -> None:
        with tempfile.TemporaryDirectory(prefix='qs-lightweight-', dir='/tmp/opencode') as directory:
            root = Path(directory)
            (root / 'StatusbarApp').mkdir()
            for filename in files:
                shutil.copy2(SOURCE / 'StatusbarApp' / filename, root / 'StatusbarApp' / filename)
            theme = root / 'CustomTheme'
            theme.mkdir()
            (theme / 'qmldir').write_text('module qs.CustomTheme\nsingleton Theme 1.0 Theme.qml\n')
            (theme / 'Theme.qml').write_text('pragma Singleton\nimport QtQuick\nQtObject { property color primary: "#aabbcc"; property color background: "#112233"; property string fontFamily: "sans-serif" }\n')
            shutil.copy2(FIXTURES / name, root / 'shell.qml')
            home = root / 'home'
            (home / '.cache').mkdir(parents=True)
            (home / '.cache/sysinfo.json').write_text('{}\n')
            binary = home / '.local/bin/hypr-sysinfo'
            binary.parent.mkdir(parents=True)
            binary.write_text('#!/bin/sh\nexit 0\n')
            binary.chmod(0o755)
            result = subprocess.run(['qs', '-p', str(root)], env={**os.environ, 'HOME': str(home), 'QT_QPA_PLATFORM': 'offscreen'}, capture_output=True, text=True, timeout=15)
            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, output)
            self.assertIn('PASS:', output)
            self.assertNotIn('FAIL:', output)

    def test_gpu_vram_use_existing_sample_and_handle_unavailable_values(self) -> None:
        self.run_fixture('metrics.qml', ('CpuModule.qml', 'SystemMetricFormat.js'))

    def test_gpu_adds_no_collector_or_timer(self) -> None:
        source = (SOURCE / 'StatusbarApp/CpuModule.qml').read_text()
        self.assertEqual(source.count('Process {'), 1)
        self.assertEqual(source.count('Timer {'), 3)
        self.assertIn('interval: 3000', source)


if __name__ == '__main__':
    unittest.main()
