"""Build and identity/lifecycle checks without opening Wayland surfaces."""
from __future__ import annotations

import os
import fcntl
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[2]/'conf_backups/cachyos_hyprland_ml4w/local/.local/lib/rofi-trial'


class GuardTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix='rofi-guard-build-', dir='/tmp/opencode')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.helpers = self.root/'helpers with spaces'
        shutil.copytree(SOURCE, self.helpers)
        result = subprocess.run(['bash', str(self.helpers/'build-smart.sh')],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.guard = self.helpers/'dismiss-guard'
        self.assertTrue(self.guard.is_file(), 'Native cross-monitor guard was not built')

    def test_foreign_pid_is_rejected_before_connecting_to_wayland(self) -> None:
        pidfile = self.root/'rofi.pid'
        pidfile.write_text(str(os.getpid()))
        result = subprocess.run([str(self.guard), str(pidfile), 'DP-fixture', str(os.getpid())],
                                env={**os.environ, 'WAYLAND_DISPLAY': 'nonexistent-rofi-test-display'},
                                capture_output=True, text=True, timeout=3)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('not this launcher', result.stderr)

    def test_missing_launcher_and_dead_owner_leave_no_waiting_helper(self) -> None:
        owner = subprocess.Popen(['/usr/bin/true'])
        owner.wait(timeout=2)
        result = subprocess.run([str(self.guard), str(self.root/'absent.pid'), 'DP-fixture', str(owner.pid)],
                                env={**os.environ, 'WAYLAND_DISPLAY': 'nonexistent-rofi-test-display'},
                                capture_output=True, text=True, timeout=3)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')

    def test_dead_owner_releases_inherited_startup_lock(self) -> None:
        owner = subprocess.Popen(['/usr/bin/true'])
        owner.wait(timeout=2)
        with (self.root/'startup.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            process = subprocess.Popen([str(self.guard), str(self.root/'absent.pid'), 'DP-fixture',
                                        str(owner.pid), str(lock.fileno())],
                                       pass_fds=(lock.fileno(),), stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, text=True)
        _, stderr = process.communicate(timeout=3)
        self.assertEqual(process.returncode, 0, stderr)
        with (self.root/'startup.lock').open('r') as available:
            fcntl.flock(available, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def test_invalid_startup_descriptor_is_rejected(self) -> None:
        result = subprocess.run([str(self.guard), str(self.root/'absent.pid'), 'DP-fixture',
                                 str(os.getpid()), '999999'], capture_output=True, text=True, timeout=3)
        self.assertEqual(result.returncode, 2)
        self.assertIn('startup descriptor', result.stderr)


if __name__ == '__main__':
    unittest.main()
