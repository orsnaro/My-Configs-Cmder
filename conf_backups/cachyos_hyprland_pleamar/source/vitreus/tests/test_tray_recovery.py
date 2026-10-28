"""Startup recovery and zero-polling contracts for the real tray adapter."""
from __future__ import annotations

from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TrayRecoveryTests(unittest.TestCase):
    def test_startup_recovery_and_event_updates(self) -> None:
        for case in ('early_app', 'existing_alias', 'failed_or_gone', 'event_updates'):
            with self.subTest(case=case):
                result = subprocess.run(
                    ['lua5.4', 'tests/tray_recovery.lua', case], cwd=ROOT,
                    text=True, capture_output=True, timeout=10,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
