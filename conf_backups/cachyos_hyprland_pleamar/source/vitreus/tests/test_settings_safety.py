"""Run actual production safety handlers against inert external-operation sinks."""
from __future__ import annotations

from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SettingsSafetyTests(unittest.TestCase):
    def run_case(self, name: str) -> None:
        result = subprocess.run(
            ["lua5.4", "tests/settings_safety.lua", name], cwd=ROOT,
            text=True, capture_output=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_menu_lock_uses_the_active_locker_after_dismissal(self) -> None:
        self.run_case("lock")

    def test_about_restart_is_managed_with_duplicate_guard_and_failure_retry(self) -> None:
        self.run_case("about")

    def test_topology_restart_is_managed_and_trial_safe(self) -> None:
        self.run_case("topology")


if __name__ == "__main__":
    unittest.main()
