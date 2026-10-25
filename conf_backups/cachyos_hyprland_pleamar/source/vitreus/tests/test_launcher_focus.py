"""Focus-follows-mouse must not dismiss the Pleamar launcher."""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]


class LauncherFocus(unittest.TestCase):
    def test_focus_changes_leave_the_launcher_open(self) -> None:
        lua = shutil.which("lua5.4") or shutil.which("lua")
        self.assertIsNotNone(lua, "a Lua interpreter is required for the controller harness")
        result = subprocess.run(
            [lua, "tests/trial_status.lua"], cwd=ROOT, text=True, capture_output=True
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("PASS", result.stdout)


if __name__ == "__main__":
    unittest.main()
