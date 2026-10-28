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
    def run_fixture(self, name: str, files: tuple[str, ...], extra_env: dict[str, str] | None = None) -> None:
        with tempfile.TemporaryDirectory(prefix='qs-lightweight-', dir='/tmp/opencode') as directory:
            root = Path(directory)
            (root / 'StatusbarApp').mkdir()
            for filename in files:
                destination = root / 'StatusbarApp' / filename
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(SOURCE / 'StatusbarApp' / filename, destination)
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
            result = subprocess.run(['qs', '-p', str(root)], env={**os.environ, 'HOME': str(home), 'QT_QPA_PLATFORM': 'offscreen', **(extra_env or {})}, capture_output=True, text=True, timeout=15)
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

    def test_focused_title_reacts_elides_and_never_overlaps_center(self) -> None:
        component = SOURCE / 'StatusbarApp/FocusedTitleModule.qml'
        self.assertTrue(component.is_file(), 'Focused title component is missing')
        self.run_fixture('focused_title.qml', ('FocusedTitleModule.qml',))
        source = component.read_text()
        self.assertNotIn('Timer {', source)
        self.assertNotIn('Process {', source)

    def test_title_is_registered_after_workspaces_only_on_main_bar(self) -> None:
        app = SOURCE / 'StatusbarApp'
        source = (app / 'StatusbarWindow.qml').read_text()
        self.assertTrue('"title":' in source, 'Main bar must register title')
        self.assertTrue('titleAvailableWidth' in source, 'Title needs a bounded layout budget')
        for name in ('StatusbarWindow.qml', 'config.json'):
            self.assertRegex((app / name).read_text(), r'"workspaces"\s*,\s*"title"')
        self.assertNotIn('FocusedTitleModule', (app / 'SlimBarWindow.qml').read_text())

    def test_existing_memory_and_panel_state_qml_fixtures(self) -> None:
        for fixture in ('memory_format.qml', 'system_panel_state.qml'):
            with self.subTest(fixture=fixture):
                self.run_fixture('legacy_harness.qml',
                                 (f'tests/{fixture}', 'SystemMetricFormat.js', 'SystemPanelState.qml'),
                                 {'QS_LEGACY_FIXTURE': fixture})


if __name__ == '__main__':
    unittest.main()
