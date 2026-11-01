"""Real native sessions: only this launcher's verified process may be closed."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest

SOURCE = Path(__file__).resolve().parents[2]/'conf_backups/cachyos_hyprland_ml4w/local/.local/lib/rofi-trial'


class SessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(prefix='rofi-session-build-', dir='/tmp/opencode')
        cls.build = Path(cls.temporary.name)
        shutil.copytree(SOURCE, cls.build/'helpers')
        subprocess.run(['bash', str(cls.build/'helpers/build-dismiss.sh')], check=True,
                       capture_output=True, text=True, timeout=30)
        cls.guard = cls.build/'helpers/dismiss-guard'
        fixture = cls.build/'fixture.c'
        fixture.write_text('#include <stdio.h>\n#include <unistd.h>\nint main(void) { while (1) pause(); }\n')
        subprocess.run(['cc', '-Wall', '-Wextra', '-Werror', str(fixture), '-o', str(cls.build/'rofi')],
                       check=True, capture_output=True, timeout=10)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix='rofi-session-', dir='/tmp/opencode')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.runtime = self.root/'runtime with spaces'
        self.runtime.mkdir(mode=0o700)
        self.pidfile = self.runtime/'rofi.pid'
        (self.runtime/'mode').write_text('apps\n')
        (self.runtime/'monitor').write_text('DP-fixture\n')
        binary = self.root/'bin'
        binary.mkdir()
        hyprctl = binary/'hyprctl'
        hyprctl.write_text('#!/usr/bin/python\nimport os\nprint(os.environ.get("MONITORS",\'[{"name":"DP-new","focused":true}]\'))\n')
        hyprctl.chmod(0o755)
        self.env = {**os.environ, 'PATH': f'{binary}:/usr/bin:/bin'}

    def picker(self, args: list[str] | None = None, *, executable: str | None = None) -> subprocess.Popen[bytes]:
        process = subprocess.Popen([executable or str(self.build/'rofi'), *(args or ['-pid', str(self.pidfile)])])
        self.addCleanup(self.reap, process)
        self.pidfile.write_text(f'{process.pid}\n')
        return process

    @staticmethod
    def reap(process: subprocess.Popen[bytes]) -> None:
        if process.poll() is None:
            process.terminate()
        process.wait(timeout=3)

    def toggle(self, mode: str = 'apps') -> subprocess.CompletedProcess[str]:
        return subprocess.run([str(self.guard), '--toggle', mode, str(self.runtime)], env=self.env,
                              capture_output=True, text=True, timeout=5)

    def test_new_view_selects_focused_monitor_and_preserves_umask(self) -> None:
        result = self.toggle()
        self.assertEqual(result.returncode, 10, result.stderr)
        self.assertEqual(result.stdout, f'{self.pidfile}\n')
        self.assertEqual((self.runtime/'monitor').read_text(), 'DP-new\n')
        self.assertEqual((self.runtime/'mode').read_text(), 'apps\n')

    def test_same_mode_closes_only_verified_picker(self) -> None:
        process = self.picker()
        result = self.toggle()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(process.wait(timeout=2), -15)
        self.assertEqual(result.stdout, '')

    def test_mode_change_closes_old_picker_before_preparing_new_view(self) -> None:
        process = self.picker()
        result = self.toggle('run')
        self.assertEqual(result.returncode, 10, result.stderr)
        self.assertEqual(process.wait(timeout=2), -15)
        self.assertEqual((self.runtime/'mode').read_text(), 'run\n')

    def test_dead_pid_is_recovered(self) -> None:
        process = self.picker()
        self.reap(process)
        self.assertEqual(self.toggle().returncode, 10)

    def test_foreign_process_is_not_signaled(self) -> None:
        process = self.picker(executable='/usr/bin/sleep', args=['30'])
        self.assertEqual(self.toggle().returncode, 2)
        self.assertIsNone(process.poll())

    def test_pid_argument_must_be_unique_and_adjacent(self) -> None:
        for args in (['-pid', '/wrong/rofi.pid', '--other', str(self.pidfile)],
                     ['-pid', str(self.pidfile), '-pid', str(self.pidfile)]):
            with self.subTest(args=args):
                process = self.picker(args)
                self.assertEqual(self.toggle().returncode, 2)
                self.assertIsNone(process.poll())
                self.reap(process)

    def test_wrong_pid_content_does_not_signal_a_different_process(self) -> None:
        process = self.picker()
        self.pidfile.write_text(f'{os.getpid()}\n')
        self.assertEqual(self.toggle().returncode, 2)
        self.assertIsNone(process.poll())

    def test_invalid_mode_or_monitor_metadata_refuses_a_live_picker(self) -> None:
        process = self.picker()
        for name, value in (('mode', 'not-a-mode\n'), ('monitor', '\n')):
            with self.subTest(name=name):
                target = self.runtime/name
                original = target.read_text()
                target.write_text(value)
                self.assertEqual(self.toggle().returncode, 2)
                self.assertIsNone(process.poll())
                target.write_text(original)

    def test_public_or_symlink_runtime_is_rejected(self) -> None:
        self.runtime.chmod(0o755)
        self.assertEqual(self.toggle().returncode, 2)
        self.runtime.chmod(0o700)
        link = self.root/'runtime-link'
        link.symlink_to(self.runtime, target_is_directory=True)
        self.runtime = link
        self.assertEqual(self.toggle().returncode, 2)

    def test_special_pid_and_metadata_files_are_rejected_without_blocking(self) -> None:
        for name in ('rofi.pid', 'mode', 'monitor'):
            for special in ('symlink', 'fifo'):
                with self.subTest(name=name, special=special):
                    target = self.runtime/name
                    original = target.read_bytes() if target.exists() else None
                    target.unlink(missing_ok=True)
                    if special == 'fifo':
                        os.mkfifo(target)
                    else:
                        external = self.root/'external'
                        external.write_text('unchanged\n')
                        target.symlink_to(external)
                    start = time.monotonic()
                    self.assertEqual(self.toggle().returncode, 2)
                    self.assertLess(time.monotonic()-start, 1)
                    if special == 'symlink':
                        self.assertEqual(external.read_text(), 'unchanged\n')
                    target.unlink()
                    if original is not None:
                        target.write_bytes(original)

    def test_invalid_monitor_response_does_not_replace_metadata(self) -> None:
        for response in ('not-json', '{}', '[{"name":"DP-new","focused":1}]'):
            with self.subTest(response=response):
                self.env['MONITORS'] = response
                self.assertEqual(self.toggle().returncode, 2)
                self.assertEqual((self.runtime/'monitor').read_text(), 'DP-fixture\n')


if __name__ == '__main__':
    unittest.main()
