"""Desktop night-mode controls must persist through Vitreus, not toggle its backend."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


CONFIG = Path.home() / ".config"
CONTROL = CONFIG / "ml4w/scripts/ml4w-toggle-hyprsunset"


class NightModeControls(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.log = self.root / "args.json"
        self.stub = self.root / "pleamar"
        self.stub.write_text(
            "#!/usr/bin/python3\n"
            "import json, os, pathlib, sys\n"
            "pathlib.Path(os.environ['ARGS_LOG']).write_text(json.dumps(sys.argv[1:]))\n"
            "print(os.environ.get('STUB_OUTPUT', ''))\n"
            "sys.exit(int(os.environ.get('STUB_EXIT', '0')))\n"
        )
        self.stub.chmod(0o755)
        self.env = dict(os.environ, PATH=str(self.root), ARGS_LOG=str(self.log))

    def invoke(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["/usr/bin/bash", str(CONTROL), *args], env=self.env,
            text=True, capture_output=True, timeout=5,
        )

    def test_default_and_explicit_toggle_emit_the_shared_event(self) -> None:
        for args in ((), ("toggle",)):
            with self.subTest(args=args):
                result = self.invoke(*args)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(self.log.read_text()), ["--say", "vitreus", "emit night_toggle"])

    def test_absolute_controls_emit_saved_on_and_off(self) -> None:
        for action, value in (("on", "1"), ("off", "0")):
            with self.subTest(action=action):
                result = self.invoke(action)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(self.log.read_text()), ["--say", "vitreus", f"emit night_set {value}"])

    def test_status_returns_the_actual_saved_ui_state(self) -> None:
        for value in ("true", "false"):
            with self.subTest(value=value):
                self.env["STUB_OUTPUT"] = value
                result = self.invoke("status")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, value + "\n")
                self.assertEqual(json.loads(self.log.read_text()), ["--say", "vitreus", "get night_on"])

    def test_ipc_failures_are_not_reported_as_success(self) -> None:
        self.env["STUB_EXIT"] = "1"
        for action in ("toggle", "on", "off", "status"):
            with self.subTest(action=action):
                result = self.invoke(action)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Vitreus", result.stderr)

    def test_invalid_status_is_rejected(self) -> None:
        self.env["STUB_OUTPUT"] = "unknown fact"
        result = self.invoke("status")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")

    def test_invalid_arguments_do_not_send_commands(self) -> None:
        for args in (("invalid",), ("on", "off")):
            with self.subTest(args=args):
                result = self.invoke(*args)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.log.exists())
                self.assertIn("Usage:", result.stderr)

    def test_missing_pleamar_fails_without_starting_a_daemon(self) -> None:
        self.stub.rename(self.root / "pleamar.disabled")
        result = self.invoke("on")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("pleamar", result.stderr)


class NightModeOwnership(unittest.TestCase):
    def test_backend_has_no_competing_profiles_or_autostart(self) -> None:
        config = (CONFIG / "hypr/hyprsunset.conf").read_text()
        self.assertIsNone(re.search(r"^\s*profile\s*\{", config, re.MULTILINE))
        startup = (CONFIG / "hypr/conf/autostart.lua").read_text()
        self.assertIsNone(re.search(r'^\s*hl\.exec_cmd\("hyprsunset', startup, re.MULTILINE))

    def test_sidebar_uses_shared_status_and_absolute_controls(self) -> None:
        source = (CONFIG / "quickshell/SidebarApp/SidebarWindow.qml").read_text()
        block = source[source.index("// BLUE LIGHT FILTER"):source.index("// --- MPRIS PLAYERS")]
        self.assertIn("Shared with Vitreus", block)
        self.assertIn("ml4w-toggle-hyprsunset status", block)
        self.assertIn('checked ? "on" : "off"', block)
        self.assertNotIn("pgrep", block)
        self.assertNotIn("pkill", block)


if __name__ == "__main__":
    unittest.main()
