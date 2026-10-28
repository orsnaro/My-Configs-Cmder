"""File-manager launch routes must select Dolphin without consulting another app."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from textwrap import dedent
import unittest

import gi

gi.require_version('GioUnix', '2.0')
from gi.repository import GioUnix


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / 'bin/vitreus-files'
ML4W = Path.home() / '.config/ml4w/settings/filemanager'


class FileManagerDefaults(unittest.TestCase):
    def launch(self, script: Path, *arguments: str) -> list[str]:
        with TemporaryDirectory(dir='/tmp/opencode') as directory:
            temporary = Path(directory)
            log = temporary / 'launch.log'
            for command in ('dolphin', 'nautilus', 'dbus-send', 'xdg-open'):
                executable = temporary / command
                executable.write_text(
                    '#!/bin/sh\nprintf "%s\\n" "${0##*/}" "$@" > "$CALL_LOG"\n'
                )
                executable.chmod(0o755)
            environment = {
                **os.environ,
                'HOME': '/home/example user',
                'PATH': str(temporary),
                'CALL_LOG': str(log),
            }
            subprocess.run(
                ['/bin/sh', str(script), *arguments], env=environment,
                check=True, capture_output=True, text=True, timeout=5,
            )
            return log.read_text().splitlines()

    def test_files_shortcut_opens_home_in_dolphin(self) -> None:
        self.assertEqual(
            self.launch(HELPER),
            ['dolphin', '--new-window', '/home/example user'],
        )

    def test_files_shortcut_preserves_a_requested_folder_with_spaces(self) -> None:
        self.assertEqual(
            self.launch(HELPER, '/tmp/folder with spaces'),
            ['dolphin', '--new-window', '/tmp/folder with spaces'],
        )

    def test_ml4w_file_manager_route_selects_dolphin(self) -> None:
        self.assertEqual(self.launch(ML4W), ['dolphin', '--new-window'])

    def test_files_launcher_entry_resolves_to_dolphin(self) -> None:
        entry = GioUnix.DesktopAppInfo.new('org.kde.dolphin.desktop')
        self.assertIsNotNone(entry)
        self.assertEqual(entry.get_name(), 'Files (Dolphin)')
        self.assertEqual(entry.get_executable(), 'dolphin')
        self.assertTrue(entry.should_show())

    def test_nautilus_keeps_its_own_launcher_name_and_command(self) -> None:
        entry = GioUnix.DesktopAppInfo.new('org.gnome.Nautilus.desktop')
        self.assertIsNotNone(entry)
        self.assertEqual(entry.get_name(), 'Nautilus')
        self.assertEqual(entry.get_executable(), 'nautilus')
        self.assertTrue(entry.should_show())

    def test_live_launcher_normalizes_only_the_two_file_managers(self) -> None:
        script = dedent(r'''
            local file = assert(io.open(arg[1], 'r'))
            local source = file:read('*a'); file:close()
            local block = source:match('(    local function normalize_file_managers%(list%)\n.-\n    end)\n')
            assert(block, 'missing launcher file-manager normalization')
            local normalize = assert(load(block .. '\nreturn normalize_file_managers'))()
            local original = { id = 'org.kde.dolphin', name = 'Dolphin', exec = 'dolphin --new-window', icon = 'dolphin-icon' }
            local other = { id = 'example.files', name = 'Files', exec = 'other-files' }
            local rows = normalize({
                original,
                { id = 'org.kde.dolphin.desktop', name = 'Files (Dolphin)', exec = 'duplicate-dolphin' },
                { id = 'org.gnome.Nautilus', name = 'Files', exec = 'nautilus --new-window' },
                { id = 'org.gnome.Nautilus.desktop', name = 'Nautilus', exec = 'duplicate-nautilus' },
                other,
            })
            assert(#rows == 3, 'only duplicate file-manager IDs should be removed')
            assert(rows[1].name == 'Files (Dolphin)' and rows[1].exec == 'dolphin --new-window')
            assert(rows[1].id == original.id and rows[1].icon == original.icon)
            assert(rows[2].name == 'Nautilus' and rows[2].exec == 'nautilus --new-window')
            assert(rows[3] == other, 'unrelated apps must be left untouched')
            assert(original.name == 'Dolphin', 'shared app records must not be mutated')
            assert(#normalize(nil) == 0 and #normalize({}) == 0)
        ''')
        result = subprocess.run(
            ['lua', '-', str(ROOT / 'vitreus.luau')], input=script,
            capture_output=True, text=True, timeout=5,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
