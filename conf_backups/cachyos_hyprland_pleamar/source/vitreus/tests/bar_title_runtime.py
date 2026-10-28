"""Opt-in static-tooltip test, only for a disposable Wayland compositor.

Set XDG_RUNTIME_DIR to its isolated runtime directory and VITREUS_TEST_DISPLAY
to its Wayland socket, then run `python tests/bar_title_runtime.py`.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class NativeTitleTooltip(unittest.TestCase):
    def trace(self, mouse: str, last_event_ms: float) -> list[tuple[float, bool, bool, float]]:
        env = dict(os.environ)
        env["WAYLAND_DISPLAY"] = env["VITREUS_TEST_DISPLAY"]
        motion = ["--reduced-motion"] if env.get("VITREUS_TEST_REDUCED_MOTION") else []
        screen = ["--screen", env["VITREUS_TEST_SCREEN"]] if env.get("VITREUS_TEST_SCREEN") else []
        with tempfile.TemporaryFile(mode="w+t") as log:
            result = subprocess.run(
                ["pleamar", "--scene", str(ROOT / "tests/bar_title_runtime.plm"),
                 "--no-hud", "--seconds", "8", "--mouse", mouse,
                 "--record", "title_tip.0,title_clicked,title_tip_text.0.height", *motion, *screen],
                env=env, stdout=log, stderr=log, timeout=25)
            log.seek(0)
            output = log.read()
        self.assertEqual(result.returncode, 0, output)
        rows: list[tuple[float, bool, bool, float]] = []
        for line in output.splitlines():
            if re.match(r"^\d+(?:\.\d+)?\t", line):
                ms, tip, clicked, height = line.split("\t")
                self.assertNotIn("?", (tip, clicked, height), "static tooltip state/layout is missing")
                rows.append((float(ms), float(tip) > 0.5, float(clicked) > 0.5, float(height)))
        self.assertTrue(rows, output)
        self.assertGreaterEqual(rows[-1][0], last_event_ms, output)
        return rows

    def test_delayed_static_tooltip_wraps_and_does_not_keep_rendering(self) -> None:
        # A changing title/width must not kill an already-hovered tooltip.
        mouse = ("100,45@1200 key:l@2200 out@2600 100,45@3000 out@3100 "
                 "100,45@3600 click@4800 out@5000 100,45@5400 key:s@6400")
        rows = self.trace(mouse, 6400)

        def state_at(ms: float) -> tuple[float, bool, bool, float]:
            return next(row for row in reversed(rows) if row[0] <= ms)

        self.assertFalse(state_at(1500)[1], "must wait 400ms before appearing")
        self.assertTrue(state_at(2100)[1], "full tooltip must appear after hover delay")
        self.assertGreater(state_at(2100)[3], 20, "long full title must wrap onto multiple lines")
        self.assertTrue(state_at(2500)[1], "title/width updates must keep a hovered tooltip visible")
        self.assertFalse(state_at(2850)[1], "leaving the title must dismiss immediately")
        self.assertFalse(state_at(3450)[1], "a quick fly-by must not leave a delayed tooltip")
        self.assertTrue(state_at(4350)[1])
        self.assertFalse(state_at(4950)[1], "click must dismiss the tooltip")
        self.assertTrue(state_at(4950)[2], "existing title click must still fire")
        self.assertTrue(state_at(6100)[1])
        self.assertFalse(state_at(6900)[1], "title change must dismiss the old tooltip")
        self.assertLess(sum(4200 <= row[0] <= 4600 for row in rows), 5,
                        "a stationary visible tooltip must not keep requesting frames")
        self.assertLess(sum(6900 <= row[0] <= 7900 for row in rows), 5,
                        "there must be no residual slide after returning to a short title")

    def test_tooltip_recovers_when_title_becomes_clipped_after_hover_started(self) -> None:
        rows = self.trace("key:s@800 100,45@1200 key:l@2200 out@4000", 4000)

        def state_at(ms: float) -> tuple[float, bool, bool, float]:
            return next(row for row in reversed(rows) if row[0] <= ms)

        self.assertFalse(state_at(1800)[1], "a fitting title must not show a tooltip")
        self.assertTrue(state_at(3200)[1], "late title/layout changes must re-arm hover without moving the pointer")
        self.assertFalse(state_at(4300)[1], "leaving still dismisses a recovered tooltip")
        self.assertLess(sum(3300 <= row[0] <= 3800 for row in rows), 5,
                        "a recovered tooltip must also return to idle")


if __name__ == "__main__":
    if not os.environ.get("VITREUS_TEST_DISPLAY"):
        raise SystemExit("Refusing to use the live desktop: set VITREUS_TEST_DISPLAY for a disposable compositor")
    unittest.main()
