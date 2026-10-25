"""The shared lock helper is the only lock path: native scene when it is up, Hyprlock otherwise."""
from __future__ import annotations

from pathlib import Path
import os
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / 'bin/vitreus-lock'


class VitreusLock(unittest.TestCase):
    def test_helper_exists_and_is_executable(self) -> None:
        self.assertTrue(HELPER.is_file(), 'Super+L points at bin/vitreus-lock, so it must exist')
        self.assertTrue(os.access(HELPER, os.X_OK), 'the lock helper must be executable')

    def test_helper_prefers_the_running_native_scene_and_falls_back(self) -> None:
        source = HELPER.read_text()
        self.assertIn('pleamar/lockscreen.sock', source, 'the helper must find the native lock socket')
        self.assertIn('fact locked true', source, 'the helper must ask the native scene to lock')
        self.assertIn('exec hyprlock', source, 'Hyprlock must remain the fallback when the scene is absent')

    def test_super_l_uses_the_helper(self) -> None:
        source = (ROOT / 'hypr_vitreus.lua').read_text()
        self.assertIn('bin/vitreus-lock', source, 'Super+L must call the shared helper')
        self.assertNotIn('pidof hyprlock', source, 'Super+L must not bypass the native lock')

    def test_idle_lock_uses_the_helper_when_configured(self) -> None:
        path = Path.home() / '.config/hypr/hypridle.conf'
        if not path.is_file():
            self.skipTest('this session has no hypridle.conf')
        source = path.read_text()
        self.assertIn('bin/vitreus-lock', source,
                      'idle/sleep must use the same native-first helper as Super+L')
        self.assertNotIn('lock_cmd = pidof hyprlock', source,
                         'the active idle lock must not bypass the native lock')

    def test_power_menu_uses_the_helper(self) -> None:
        source = (ROOT / 'logic/capture_power.luau').read_text()
        self.assertIn('bin/vitreus-lock', source, 'the Power menu Lock must use the shared helper')

    def test_real_locks_are_not_safe_by_default(self) -> None:
        source = (ROOT / 'lockscreen/lockscreen.plm').read_text()
        self.assertIn('fact safe = false', source, 'only Test lock may enable the escape hatch')

    def test_helper_status_reports_the_live_path(self) -> None:
        result = subprocess.run([str(HELPER), '--status'], capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(result.stdout.strip(), {'native', 'hyprlock'})


if __name__ == '__main__':
    unittest.main()
