"""Settings > Hyprland and > Display are only useful if Hyprland loads them again."""
from __future__ import annotations

from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
HYPR = Path.home() / ".config" / "hypr"
LPATH = HYPR / "hyprland.lua"


class HyprPersistence(unittest.TestCase):
    def test_hyprland_loads_the_settings_vitreus_saves(self) -> None:
        source = LPATH.read_text()
        for module in ("vitreus_monitors", "vitreus_hypr", "vitreus_colors"):
            self.assertIn(
                f'pcall(require, "{module}")', source,
                f"hyprland.lua never loads {module}.lua, so that Settings page cannot persist")

    def test_rapid_hyprland_changes_write_the_latest_value(self) -> None:
        result = subprocess.run(
            ["lua5.4", "tests/hypr_persistence.lua"], cwd=ROOT,
            text=True, capture_output=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
