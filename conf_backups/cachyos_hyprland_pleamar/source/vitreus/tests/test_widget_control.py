"""Exercise the real Luau handlers against controlled IPC/startup timing."""
from __future__ import annotations

from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class WidgetControl(unittest.TestCase):
    def test_widget_startup_delivery_and_confirmation(self) -> None:
        result = subprocess.run(["lua5.4", "tests/widget_control.lua"], cwd=ROOT,
                                text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Widgets behavior: 15 passed", result.stdout)

    def test_widgets_scene_compiles_with_the_installed_runtime(self) -> None:
        result = subprocess.run(["pleamar", "--check", "vitreus.plm"], cwd=ROOT,
                                text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_widget_errors_have_visible_existing_subtitle_slots(self) -> None:
        scene = (ROOT / "vitreus.plm").read_text()
        page = (ROOT / "pages/clock.plm").read_text()
        for name in ("ck_status", "sy_status"):
            self.assertRegex(scene, rf'\btext {name} = ""')
            self.assertRegex(page, rf'text [^\n]*\b{name}\b[^\n]*\{{[^\n]*show:')


if __name__ == "__main__":
    unittest.main()
