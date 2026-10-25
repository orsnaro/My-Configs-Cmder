"""The Pleamar calendar shows the existing read-only Google cache beside local reminders."""
from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent
PLM = (ROOT / "vitreus.plm").read_text()
LUAU = (ROOT / "vitreus.luau").read_text()
PANEL = (ROOT / "pages" / "panel_frame.plm").read_text()


class GoogleCalendarIntegration(unittest.TestCase):
    def test_model_marks_the_event_source(self) -> None:
        self.assertIn("model cal_events max 6 { time: text; title: text; done: bool; google: bool; task: bool }", PLM)

    def test_logic_uses_the_shared_google_helper(self) -> None:
        self.assertIn('require("logic/gcal")', LUAU)
        self.assertIn("gcal.on_day", LUAU)
        self.assertIn("gcal.counts", LUAU)
        self.assertIn("gcal.tasks_on_day", LUAU)
        self.assertIn("gcal.task_counts", LUAU)

    def test_logic_reads_the_existing_read_only_cache(self) -> None:
        self.assertIn("gcal/cache.json", LUAU)
        self.assertIn('run("cat"', LUAU)

    def test_logic_reads_the_tasks_from_the_cache(self) -> None:
        self.assertIn("data.tasks", LUAU)

    def test_google_rows_have_no_check_or_delete_controls(self) -> None:
        self.assertIn('show: e.google', PLM)
        self.assertIn("active: not e.google", PLM)

    def test_the_scene_can_refresh_the_read_only_cache(self) -> None:
        self.assertIn('"vitreus-gcal-sync"', PLM)
        self.assertIn("sync_google", LUAU)
        helper = ROOT / "bin" / "vitreus-gcal-sync"
        self.assertTrue(helper.is_file(), "the bounded sync helper is missing")
        self.assertTrue(helper.stat().st_mode & 0o111, "the sync helper must be executable")


if __name__ == "__main__":
    unittest.main()
