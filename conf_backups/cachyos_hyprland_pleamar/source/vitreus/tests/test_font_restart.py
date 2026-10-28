"""Font Apply must respect the managed owner, and startup must consume the choice."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class FontApply(unittest.TestCase):
    def test_actual_font_picker_restarts_the_service_without_killing_scenes(self) -> None:
        result = subprocess.run(["lua5.4", "tests/font_apply.lua"], cwd=ROOT,
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class FontStartup(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="vitreus-font-start-")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / "home with spaces"
        self.bin = self.home / ".local/bin"
        self.bin.mkdir(parents=True)
        self.scene = self.home / ".config/pleamar/shells/vitreus"
        (self.scene / "bin").mkdir(parents=True)
        self.config = self.home / "chosen font.conf"
        self.config.write_text("<fontconfig/>")
        self.capture = self.home / "capture.json"
        self.order = self.home / "order.txt"
        source = ROOT / "bin/vitreus-start"
        if not source.exists():
            source = Path.home() / ".local/bin/pleamar-start"
        self.launcher = self.bin / "start-under-test"
        shutil.copy2(source, self.launcher)
        self.command(self.bin / "pleamar", """#!/usr/bin/env python3
import json, os, pathlib, sys
pathlib.Path(os.environ['FONT_TEST_CAPTURE']).write_text(json.dumps({
 'font':os.environ.get('FONTCONFIG_FILE'), 'gpu':os.environ.get('VK_DRIVER_FILES'), 'args':sys.argv[1:]}))
""")
        self.command(self.scene / "bin/vitreus-themes", '#!/bin/sh\nprintf "themes\\n" >> "$FONT_TEST_ORDER"\n')
        self.command(self.scene / "bin/vitreus-fonts", '#!/bin/sh\nprintf "fonts\\n" >> "$FONT_TEST_ORDER"\nprintf "%s\\n" "$FONT_TEST_CONFIG"\n')
        self.env = dict(os.environ)
        self.env.pop("FONTCONFIG_FILE", None)
        self.env.update(HOME=str(self.home), XDG_CONFIG_HOME=str(self.home / ".config"),
                        XDG_DATA_HOME=str(self.home / "data"), XDG_RUNTIME_DIR=str(self.home / "run"),
                        WAYLAND_DISPLAY="wayland-test", HYPRLAND_INSTANCE_SIGNATURE="test",
                        FONT_TEST_CAPTURE=str(self.capture), FONT_TEST_ORDER=str(self.order),
                        FONT_TEST_CONFIG=str(self.config))

    @staticmethod
    def command(path: Path, source: str) -> None:
        path.write_text(source)
        path.chmod(0o755)

    def launch(self) -> dict[str, object]:
        result = subprocess.run([str(self.launcher), "--seconds", "1"], env=self.env,
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(self.capture.read_text())

    def test_font_configuration_is_loaded_before_starting_the_shell(self) -> None:
        result = self.launch()
        self.assertEqual(result["font"], str(self.config))
        self.assertEqual(self.order.read_text().splitlines(), ["themes", "fonts"])

    def test_font_setup_failure_does_not_prevent_the_shell_from_returning(self) -> None:
        self.command(self.scene / "bin/vitreus-fonts", "#!/bin/sh\nexit 1\n")
        self.assertIsNone(self.launch()["font"])

    def test_default_font_does_not_set_a_broken_fontconfig_path(self) -> None:
        self.env["FONT_TEST_CONFIG"] = ""
        self.assertIsNone(self.launch()["font"])

    def test_missing_generated_configuration_falls_back_safely(self) -> None:
        self.config.unlink()
        self.assertIsNone(self.launch()["font"])

    def test_amd_settings_scene_and_extra_arguments_are_preserved(self) -> None:
        result = self.launch()
        self.assertEqual(result["gpu"], "/usr/share/vulkan/icd.d/radeon_icd.json")
        self.assertEqual(result["args"], ["--scene", str(self.scene / "vitreus.plm"), "--no-hud", "--seconds", "1"])


if __name__ == "__main__":
    unittest.main()
