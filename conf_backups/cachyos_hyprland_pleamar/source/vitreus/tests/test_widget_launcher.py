"""Run the real keeper without starting a compositor client or touching user state."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
ICD = "/usr/share/vulkan/icd.d/radeon_icd.json"


class WidgetLauncher(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="vitreus-keeper-")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / "home with spaces"
        self.bin = self.home / ".local/bin"
        self.bin.mkdir(parents=True)
        self.runtime = self.home / "run"
        self.runtime.mkdir()
        self.socket = socket.socket(socket.AF_UNIX)
        self.socket.bind(str(self.runtime / "wayland-test"))
        self.addCleanup(self.socket.close)
        self.capture = self.home / "capture.json"
        self.shell = self.home / ".config/pleamar/shells/vitreus"
        (self.shell / "bin").mkdir(parents=True)
        self.keeper = self.shell / "bin/vitreus-keep"
        shutil.copy2(ROOT / "bin/vitreus-keep", self.keeper)
        self.command(self.bin / "pgrep", '#!/bin/sh\nexit "${KEEP_ALREADY_RUNNING:-1}"\n')
        self.command(self.bin / "socat", "#!/bin/sh\nexit 0\n")
        for name in ("vitreus-themes", "vitreus-fonts"):
            self.command(self.shell / "bin" / name, "#!/bin/sh\nexit 0\n")
        self.command(self.bin / "pleamar", """#!/usr/bin/env python3
import json, os, pathlib, sys
keys = ('DRI_PRIME', 'VK_DRIVER_FILES', 'PLEAMAR_SWAPCHAIN')
pathlib.Path(os.environ['KEEP_CAPTURE']).write_text(json.dumps({
    'env': {key: os.environ.get(key) for key in keys}, 'args': sys.argv[1:]}))
print('renderer startup diagnostic', flush=True)
(pathlib.Path(os.environ['XDG_RUNTIME_DIR']) / os.environ['WAYLAND_DISPLAY']).unlink()
""")
        self.env = dict(os.environ)
        for key in ("DRI_PRIME", "VK_DRIVER_FILES", "VK_ICD_FILENAMES", "PLEAMAR_SWAPCHAIN"):
            self.env.pop(key, None)
        self.env.update(HOME=str(self.home), XDG_CONFIG_HOME=str(self.home / ".config"), PATH=f"{self.bin}:/usr/bin:/bin",
                        XDG_DATA_HOME=str(self.home / "data"), XDG_RUNTIME_DIR=str(self.runtime),
                        WAYLAND_DISPLAY="wayland-test", HYPRLAND_INSTANCE_SIGNATURE="test",
                        KEEP_CAPTURE=str(self.capture))

    @staticmethod
    def command(path: Path, content: str) -> None:
        path.write_text(content)
        path.chmod(0o755)

    def launch(self, scene: str = "desktopclock", log: str | None = None,
               installed: bool = True) -> dict[str, object] | None:
        path = self.shell / scene / f"{scene}.plm" if installed else self.home / "other.plm"
        args = [str(self.keeper), str(path)]
        if log is not None:
            args.append(log)
        result = subprocess.run(args, env=self.env, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(self.capture.read_text()) if self.capture.exists() else None

    def test_installed_hyprland_widget_gets_working_amd_defaults(self) -> None:
        result = self.launch()
        self.assertEqual(result["env"]["DRI_PRIME"], "1")
        self.assertEqual(result["env"]["VK_DRIVER_FILES"], ICD)
        self.assertEqual(result["args"], ["--scene", str(self.shell / "desktopclock/desktopclock.plm"), "--no-hud"])

    def test_explicit_gpu_and_lock_overrides_are_preserved(self) -> None:
        self.env.update(DRI_PRIME="0", VK_DRIVER_FILES="/custom/driver.json", PLEAMAR_SWAPCHAIN="1")
        result = self.launch("lockscreen")
        self.assertEqual(result["env"], {"DRI_PRIME": "0", "VK_DRIVER_FILES": "/custom/driver.json", "PLEAMAR_SWAPCHAIN": "1"})

    def test_no_amd_defaults_on_other_desktops(self) -> None:
        self.env.pop("HYPRLAND_INSTANCE_SIGNATURE")
        result = self.launch()
        self.assertIsNone(result["env"]["DRI_PRIME"])
        self.assertIsNone(result["env"]["VK_DRIVER_FILES"])

    def test_no_amd_defaults_for_unrelated_scenes(self) -> None:
        result = self.launch(installed=False)
        self.assertIsNone(result["env"]["DRI_PRIME"])
        self.assertIsNone(result["env"]["VK_DRIVER_FILES"])

    def test_default_log_retains_the_renderer_failure_message(self) -> None:
        self.launch()
        log = self.home / "data/pleamar/vitreus/desktopclock.log"
        self.assertTrue(log.exists(), "widget startup errors must not disappear into /dev/null")
        self.assertIn("renderer startup diagnostic", log.read_text())

    def test_explicit_log_path_is_preserved(self) -> None:
        log = self.home / "custom logs/clock.log"
        self.launch(log=str(log))
        self.assertIn("renderer startup diagnostic", log.read_text())

    def test_explicit_dev_null_stays_quiet(self) -> None:
        self.launch(log="/dev/null")
        self.assertFalse((self.home / "data/pleamar/vitreus/desktopclock.log").exists())

    def test_an_existing_scene_is_not_started_twice(self) -> None:
        self.env["KEEP_ALREADY_RUNNING"] = "0"
        self.assertIsNone(self.launch())


if __name__ == "__main__":
    unittest.main()
