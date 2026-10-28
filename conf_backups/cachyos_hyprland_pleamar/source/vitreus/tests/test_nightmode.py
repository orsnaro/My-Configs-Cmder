"""Night mode must keep the latest choice across restarts until the next schedule boundary."""
from __future__ import annotations

from pathlib import Path
import os
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]


class NightMode(unittest.TestCase):
    def test_regressions_pass_in_cairo_time(self) -> None:
        result = subprocess.run(
            ["lua5.4", "tests/nightmode.lua"],
            cwd=ROOT, text=True, capture_output=True, timeout=60,
            env={**os.environ, "TZ": "Africa/Cairo"},
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("nightmode: PASS", result.stdout)

    def test_the_scene_contract_declares_night_set(self) -> None:
        scene = (ROOT / "vitreus.plm").read_text()
        self.assertIn("event night_set ->", scene,
                      "the scene contract does not declare night_set, so the absolute control cannot emit it")


if __name__ == "__main__":
    unittest.main()
