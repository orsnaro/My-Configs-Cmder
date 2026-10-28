"""Regression coverage for measured count centering and static title tooltips."""
from __future__ import annotations

from pathlib import Path
import subprocess
import unittest

from test_trial_layout import Geometry


ROOT = Path(__file__).resolve().parents[1]


class StatusPolish(unittest.TestCase):
    def test_title_overflow_identifies_when_a_tooltip_is_needed(self) -> None:
        for measured, room, expected in ((60, 100, 0), (100, 100, 0), (350, 100, 250)):
            with self.subTest(measured=measured, room=room):
                g = Geometry(3)
                g.values.update({"win.hw": room + 16.2, "mctl": 0,
                                 "tb_title_full_w.width": measured,
                                 "bs.title": 1, "sb": 1})
                self.assertAlmostEqual(g.value("title.room"), room)
                self.assertAlmostEqual(g.value("title.overflow"), expected)
        for overrides in ({"lm": 1}, {"bs.title": 0}, {"sb": 0}, {"win.hw": 0}):
            g = Geometry(3)
            g.values.update({"win.hw": 116.2, "mctl": 0,
                             "tb_title_full_w.width": 350, "bs.title": 1, "sb": 1})
            g.values.update(overrides)
            self.assertEqual(g.value("title.overflow"), 0)

    def test_tooltip_stays_inside_each_monitor_width(self) -> None:
        for screen_width in (320, 640, 1366, 2560):
            for title_x in (0, screen_width / 2, screen_width - 10):
                with self.subTest(screen=screen_width, title_x=title_x):
                    g = Geometry(3)
                    g.values.update({"screen.width": screen_width, "win.xs": title_x,
                                     "tb_title_full_w.width": 1500})
                    self.assertGreaterEqual(g.value("title.tip_x"), 12 * g.value("u"))
                    self.assertLessEqual(g.value("title.tip_x") + g.value("title.tip_w"),
                                         screen_width - 12 * g.value("u") + 1e-6)

    def test_icon_and_natural_count_are_centered_together(self) -> None:
        # Fixed left offsets must not leave single-digit readings left-heavy.
        for prefix in ("update", "alert"):
            for count_width in (6.0, 13.0, 21.0):
                for scale in (1.0, 1.35, 1.6):
                    with self.subTest(control=prefix, count=count_width, scale=scale):
                        g = Geometry(3)
                        g.values.update({"u": scale,
                                         f"tb_{prefix}_icon_w.width": 18.0,
                                         f"tb_{prefix}_count_w.width": count_width})
                        left = g.value(f"tb.{prefix}_icon") - 9.0
                        right = g.value(f"tb.{prefix}_count") + count_width
                        self.assertAlmostEqual((left + right) / 2,
                                               g.value(f"tb.{prefix}_pill"))
                        self.assertGreater(g.value(f"tb.{prefix}_count") -
                                           (g.value(f"tb.{prefix}_icon") + 9.0), 0)

    def test_title_preserves_unicode_and_invalidates_only_for_title_or_focus(self) -> None:
        result = subprocess.run(["lua5.4", "tests/bar_title.lua"], cwd=ROOT,
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
