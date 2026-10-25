"""The screenshot capture must use the monitor under the pointer.

Hyprland's `focused` monitor can stay on DP-2 while the pointer is over an empty
part of a side monitor, which made Print capture the middle screen. The helper
is the single place that resolves the output; capture_power.luau must use it.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "bin" / "vitreus-output-under-pointer"
CAPTURE = ROOT / "logic" / "capture_power.luau"
SCENE = ROOT / "vitreus.plm"
LITE = ROOT / "pages" / "lite_bars.plm"
SNAP = ROOT / "snap" / "snap.luau"

MONITORS = [
    {"name": "DP-2", "x": 2404, "y": 381, "width": 2560, "height": 1440, "focused": True},
    {"name": "HDMI-A-2", "x": 1038, "y": 768, "width": 1366, "height": 768, "focused": False},
    {"name": "DP-1", "x": 4964, "y": 768, "width": 1440, "height": 900, "focused": False},
]


class OutputUnderPointerTest(unittest.TestCase):
    def run_helper(self, cursor: dict[str, int] | None) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cursor_file = tmp_path / "cursor.json"
            monitors_file = tmp_path / "monitors.json"
            if cursor is None:
                cursor_file.write_text("")
            else:
                cursor_file.write_text(json.dumps(cursor))
            monitors_file.write_text(json.dumps(MONITORS))
            fake = tmp_path / "hyprctl"
            fake.write_text(
                "#!/bin/sh\n"
                'case "$*" in\n'
                '  "-j cursorpos") cat "$FAKE_CURSOR"; exit 0 ;;\n'
                '  "-j monitors") cat "$FAKE_MONITORS"; exit 0 ;;\n'
                "  *) exit 1 ;;\n"
                "esac\n"
            )
            fake.chmod(0o755)
            env = os.environ | {
                "PATH": f"{tmp_path}:{os.environ['PATH']}",
                "FAKE_CURSOR": str(cursor_file),
                "FAKE_MONITORS": str(monitors_file),
            }
            result = subprocess.run(
                [str(HELPER)], capture_output=True, text=True, env=env, timeout=5
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            return result.stdout.strip()

    def test_pointer_on_side_monitor_wins_over_focused_main(self) -> None:
        self.assertEqual(self.run_helper({"x": 1200, "y": 800}), "HDMI-A-2")

    def test_pointer_on_right_monitor(self) -> None:
        self.assertEqual(self.run_helper({"x": 5200, "y": 1000}), "DP-1")

    def test_missing_cursor_falls_back_to_focused_monitor(self) -> None:
        self.assertEqual(self.run_helper(None), "DP-2")

    def test_capture_power_uses_the_helper(self) -> None:
        source = CAPTURE.read_text()
        self.assertIn("vitreus-output-under-pointer", source)
        self.assertNotIn(
            'select(.focused) | .name',
            source,
            "capture_power must not choose the focused monitor directly",
        )

    def test_snap_uses_the_system_swapchain(self) -> None:
        # Pleamar's own dmabuf frames die on surfaces whose width is not a
        # multiple of 64 px: DP-1 (1440) and HDMI-A-2 (1366). Snap is a still
        # picture, so the compositor's swapchain is the stable path there.
        self.assertIn("PLEAMAR_SWAPCHAIN=1", CAPTURE.read_text())

    def test_snap_capture_includes_cursor(self) -> None:
        self.assertIn('grim -c -l 0 ${o:+-o "$o"} "$d/shot.png"', SNAP.read_text())

    def test_snap_lends_the_side_strip_reserve_while_open(self) -> None:
        # The side strips reserve 36 px plus their top gap. Without lending it
        # back, Snap only gets 848 px on DP-1 and 722 px on HDMI-A-2.
        self.assertIn("fact snap_open = false", SCENE.read_text())
        self.assertIn("fact snap_target = 0", SCENE.read_text())
        snap = SNAP.read_text()
        # Snap captures first, then asks for the reserve; the screenshot must
        # not be taken after the target monitor's windows have reflowed.
        self.assertIn('"fact snap_target $t" "fact snap_open true"', snap)
        # Snap must not clear the fact itself: a late clear from a closing
        # instance can race a new Print and restore the reserve under it.
        self.assertNotIn("fact snap_open false", snap)
        bars = LITE.read_text()
        self.assertIn("reserve: 36 while bar_lite_dp1 and not (snap_open and snap_target == 1)", bars)
        self.assertIn("reserve: 36 while bar_lite_hdmi and not (snap_open and snap_target == 2)", bars)

    def test_a_stale_snap_launch_gives_the_reserve_back(self) -> None:
        source = CAPTURE.read_text()
        self.assertIn("every(1000", source)
        self.assertIn("snap_grace_until", source)
        self.assertIn("g == snap_gen", source)
        self.assertIn(r'"^(.*/)?(pleamar|sh|bash) .*snap/snap\\.plm"', source)


if __name__ == "__main__":
    unittest.main()
