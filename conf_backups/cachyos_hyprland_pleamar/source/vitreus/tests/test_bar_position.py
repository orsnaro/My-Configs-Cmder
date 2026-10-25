"""The frame's wide gap must not be saved as the next run's original gap."""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]


class BarPositionGaps(unittest.TestCase):
    def test_generated_frame_room_is_not_original(self) -> None:
        lua = shutil.which("lua5.4") or shutil.which("lua")
        self.assertIsNotNone(lua, "a Lua interpreter is required for the logic harness")
        result = subprocess.run(
            [lua, "tests/bar_position.lua"], cwd=ROOT, text=True, capture_output=True
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("PASS", result.stdout)

    def test_gaps_wait_for_the_original_read(self) -> None:
        source = (ROOT / "vitreus.luau").read_text()
        self.assertIn("if not o then return nil end", source,
                      "the bar gaps must not be applied before the startup original read lands")


if __name__ == "__main__":
    unittest.main()
