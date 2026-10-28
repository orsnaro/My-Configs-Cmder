"""Launcher entrance timings stay isolated from the shared drawer animation."""
from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class LauncherTiming(unittest.TestCase):
    def setUp(self) -> None:
        self.source = (ROOT / "vitreus.plm").read_text()

    def rule(self, condition: str) -> str:
        match = re.search(
            r"on change panel while " + re.escape(condition) + r"\s*\{([^}]*)\}",
            self.source,
        )
        self.assertIsNotNone(match, f"missing panel rule: {condition}")
        return " ".join(match.group(1).split())

    def test_launcher_content_fades_in_within_180_ms(self) -> None:
        match = re.search(r"\bprop\s+fl\s*=\s*0\s*~(\d+)ms\b", self.source)
        self.assertIsNotNone(match)
        self.assertEqual(int(match.group(1)), 180)

    def test_launcher_content_starts_after_100_ms_without_delaying_focus(self) -> None:
        self.assertEqual(
            self.rule("panel == launch"),
            "fl: 1 after 100ms; focus lq; emit launch_open",
        )

    def test_quick_close_resets_content_after_pending_entrance(self) -> None:
        self.assertEqual(
            self.rule("panel != launch"),
            "fl: 0 ~80ms; fl: 0 ~80ms after 105ms",
        )

    def test_frame_cap_and_shared_motion_are_unchanged(self) -> None:
        for pattern in (
            r"\brate:\s*75\s*;",
            r"\bspring\s+dripl\s*=\s*46,\s*8\b",
            r"\bspring\s+drip\s*=\s*170,\s*18\b",
            r"\bprop\s+dl\s*=\s*0\s*~drip\b",
            r"\bprop\s+dtrav\s*=\s*0\s*~dripl\b",
        ):
            with self.subTest(pattern=pattern):
                self.assertTrue(re.search(pattern, self.source), pattern)

    def test_other_panel_entrances_are_unchanged(self) -> None:
        self.assertEqual(
            self.rule("panel == calendar"),
            "f1: 1 after 220ms; f4: 1 after 300ms",
        )
        self.assertEqual(self.rule("panel == settings"), "fs: 1 after 220ms")
        self.assertEqual(
            self.rule("panel == player or panel == tray"), "f3: 1 after 200ms"
        )


if __name__ == "__main__":
    unittest.main()
