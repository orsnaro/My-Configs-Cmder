"""Real-process regressions; every desktop-facing command uses a sandbox HOME."""

from __future__ import annotations

import os
import json
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile
import time
from typing import BinaryIO, Callable
import unittest


ROOT = Path(__file__).resolve().parents[3]
AUTOMATION = ROOT / "ml4w/scripts/ml4w-wallpaper-automation"
LISTENER = ROOT / "ml4w/listeners/gtk-theme-switcher.sh"
WALLPAPER = ROOT / "ml4w/scripts/ml4w-wallpaper"
THEME = ROOT / "quickshell/CustomTheme/Theme.qml"
PANEL = ROOT / "quickshell/WallpaperApp/WallpaperWindow.qml"
AUTOSTART = ROOT / "ml4w/scripts/ml4w-autostart"


class WallpaperRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp(prefix="wallpaper-runtime-", dir="/tmp/opencode"))
        self.settings = self.home / ".config/ml4w/settings"
        self.scripts = self.home / ".config/ml4w/scripts"
        self.cache = self.home / ".cache/ml4w/hyprland-dotfiles"
        self.bin = self.home / "bin"
        for directory in (self.settings, self.scripts, self.cache, self.bin,
                          self.home / ".config/gtk-3.0"):
            directory.mkdir(parents=True)
        self.log = self.home / "calls.log"
        self.log.touch()
        self.env = {
            "HOME": str(self.home), "PATH": f"{self.bin}:/usr/bin:/bin",
            "AUDIT_LOG": str(self.log), "XDG_RUNTIME_DIR": str(self.home),
        }
        self.processes: list[subprocess.Popen[bytes]] = []
        self.logs: list[BinaryIO] = []
        self.write(self.settings / "wallpaper-automation", "300")
        self.write(self.settings / "wallpaper-theming", "false")
        self.write(self.settings / "wallpaper-effect", "off")
        self.write(self.settings / "wallpaper-transition-effect", "simple")
        self.write(self.settings / "blur.sh", "0x0")
        self.write(self.home / ".config/gtk-3.0/settings.ini",
                   "[Settings]\ngtk-application-prefer-dark-theme=1\n")
        self.write(self.scripts / "ml4w-notification-handler", "notify_user() { :; }\n")
        self.executable(self.scripts / "ml4w-wallpaper",
                        'printf "WALLPAPER %s\\n" "$*" >> "$AUDIT_LOG"\n')

    @staticmethod
    def write(path: Path, text: str) -> None:
        path.write_text(text)

    @staticmethod
    def executable(path: Path, body: str) -> None:
        path.write_text("#!/usr/bin/bash\n" + body)
        path.chmod(0o700)

    def tearDown(self) -> None:
        # Kill only process groups created by this test, including real sleeps.
        for process in self.processes:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=3)
        for log in self.logs:
            log.close()
        # Daemon-fixture PIDs belong to this sandbox, never the desktop.
        for path in self.home.glob("fixture-*.pid"):
            try:
                os.kill(int(path.read_text()), signal.SIGKILL)
            except (ProcessLookupError, ValueError):
                pass

    def start(self, *arguments: str) -> subprocess.Popen[bytes]:
        log = (self.home / f"process-{len(self.processes)}.log").open("wb")
        self.logs.append(log)
        process = subprocess.Popen(
            ["bash", str(AUTOMATION), *arguments], env=self.env, cwd=self.home,
            stdout=log, stderr=log, start_new_session=True,
        )
        self.processes.append(process)
        return process

    def command(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(AUTOMATION), *arguments], env=self.env, cwd=self.home,
            capture_output=True, text=True, timeout=8, check=False,
        )

    def wait_until(self, predicate: Callable[[], bool], message: str) -> None:
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(0.02)
        self.fail(message)

    def running_pid(self) -> int:
        return int((self.cache / "wallpaper-automation.pid").read_text())

    def test_real_sleep_stops_promptly_and_restarts(self) -> None:
        process = self.start("--start")
        self.wait_until(lambda: "WALLPAPER" in self.log.read_text(), "slideshow did not start")
        time.sleep(0.1)  # allow the real 300-second sleep to start
        before = time.monotonic()
        result = self.command("--stop")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertLess(time.monotonic() - before, 1.5, "stop waits for sleep instead of cancelling it")
        process.wait(timeout=2)
        self.assertEqual((self.settings / "wallpaper-slideshow").read_text().strip(), "false")
        second = self.start("--start")
        self.wait_until(lambda: self.log.read_text().count("WALLPAPER") >= 2,
                        "a stopped loop left an inherited lock blocking restart")
        self.assertIsNone(second.poll())

    def test_wallpaper_background_child_does_not_inherit_loop_lock(self) -> None:
        self.executable(self.scripts / "ml4w-wallpaper",
                        '/bin/sleep 20 >/dev/null 2>&1 &\n'
                        'printf "%s" "$!" > "$HOME/fixture-daemon.pid"\n'
                        'printf "WALLPAPER\\n" >> "$AUDIT_LOG"\n')
        self.start("--start")
        self.wait_until(lambda: "WALLPAPER" in self.log.read_text(), "slideshow did not start")
        lock_path = self.cache / ".wallpaper-automation.lock"
        daemon_pid = int((self.home / "fixture-daemon.pid").read_text())
        inherited = []
        for fd in Path(f"/proc/{daemon_pid}/fd").iterdir():
            try:
                if fd.resolve() == lock_path:
                    inherited.append(fd.name)
            except FileNotFoundError:
                pass
        self.assertEqual(inherited, [], "wallpaper children inherited the lifetime flock")

    def test_stop_during_wallpaper_cancels_owned_work(self) -> None:
        self.executable(self.scripts / "ml4w-wallpaper",
                        'printf "%s" "$$" > "$HOME/fixture-worker.pid"\n'
                        'printf "WALLPAPER\\n" >> "$AUDIT_LOG"\n'
                        '/bin/sleep 20\n'
                        'printf "LATE_CHANGE\\n" >> "$AUDIT_LOG"\n')
        self.start("--start")
        self.wait_until(lambda: "WALLPAPER" in self.log.read_text(), "wallpaper work did not start")
        worker = int((self.home / "fixture-worker.pid").read_text())
        before = time.monotonic()
        self.assertEqual(self.command("--stop").returncode, 0)
        self.assertLess(time.monotonic() - before, 1.5)
        self.wait_until(lambda: not Path(f"/proc/{worker}").exists(), "wallpaper child survived stop")
        self.assertNotIn("LATE_CHANGE", self.log.read_text())

    def test_gtk_event_does_not_regenerate_when_theming_is_off(self) -> None:
        self.executable(self.bin / "inotifywait", 'printf "test CLOSE_WRITE settings.ini\\n"\n')
        for name in ("matugen", "qs", "nohup", "swaync-client", "walker", "pkill"):
            self.executable(self.bin / name, f'printf "{name} %s\\n" "$*" >> "$AUDIT_LOG"\n')
        self.write(self.cache / "current_wallpaper", str(self.home / "input.png"))
        result = subprocess.run(["bash", str(LISTENER)], env=self.env, cwd=self.home,
                                capture_output=True, text=True, timeout=3, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("matugen ", self.log.read_text(), "GTK listener bypassed theme-off preference")

    def run_qml(self, source: str, imports: Path | None = None) -> None:
        qml = self.home / "qml-tests"
        qml.mkdir()
        (qml / "shell.qml").write_text(source)
        environment = dict(self.env, QT_QPA_PLATFORM="offscreen", QSG_RHI_BACKEND="software")
        if imports is not None:
            environment["QML_IMPORT_PATH"] = str(imports)
        log = (self.home / "qml.log").open("wb")
        self.logs.append(log)
        process = subprocess.Popen(["/usr/bin/qs", "-p", str(qml), "--no-color"],
                                   env=environment, cwd=self.home, stdout=log,
                                   stderr=log, start_new_session=True)
        self.processes.append(process)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            output = (self.home / "qml.log").read_text()
            if "QML_TEST_PASS" in output:
                return
            if "QML_TEST_FAIL" in output or process.poll() is not None:
                self.fail(output)
            time.sleep(0.02)
        self.fail((self.home / "qml.log").read_text())

    def test_saved_palette_loads_without_wallpaper_regeneration(self) -> None:
        colors = self.home / ".config/ml4w/colors"
        colors.mkdir()
        (colors / "colors.json").write_text('{"background":"#123456","primary":"#abcdef"}')
        imports = self.home / "imports"
        module = imports / "qs/CustomTheme"
        module.mkdir(parents=True)
        shutil.copyfile(THEME, module / "Theme.qml")
        (module / "qmldir").write_text("module qs.CustomTheme\nsingleton Theme 1.0 Theme.qml\n")
        self.run_qml('''import QtQuick
import Quickshell
import qs.CustomTheme 1.0
ShellRoot {
    Timer {
        interval: 50; repeat: true; running: true
        property int attempts: 0
        onTriggered: {
            if (String(Theme.background) === "#123456" && String(Theme.primary) === "#abcdef") {
                console.log("QML_TEST_PASS"); stop()
            } else if (++attempts > 60) {
                console.error("QML_TEST_FAIL: saved palette was not loaded on startup"); stop()
            }
        }
    }
}
''', imports)

    def test_real_checkbox_persists_and_reloads_setting(self) -> None:
        # Reuse the actual persistence block and checkbox handlers, without
        # creating any real Wayland window or touching the desktop HOME.
        text = PANEL.read_text()
        persistence = text[text.index("    property string themingSettingFile:"):
                           text.index("    FileView {\n        id: transitionEffectSettingFileHandler")]
        checkbox = re.search(r'id: shouldUpdateTheming\s+(checked:[^\n]+)', text)
        toggle = re.search(r'onToggled: ([^\n]+)', text)
        assert checkbox and toggle
        self.run_qml('''import QtQuick
import QtQuick.Controls
import Quickshell
import Quickshell.Io
ShellRoot {
    id: root
''' + persistence + '''
    CheckBox {
        id: shouldUpdateTheming
        width: 180; height: 60
        ''' + checkbox.group(1) + '''
        onToggled: ''' + toggle.group(1) + '''
    }
    Timer {
        interval: 50; repeat: true; running: true
        property int stage: 0
        property int attempts: 0
        onTriggered: {
            if (++attempts > 60) {
                console.error("QML_TEST_FAIL: checkbox persistence failed at stage", stage); stop()
            } else if (stage === 0 && !shouldUpdateTheming.checked) {
                shouldUpdateTheming.toggle()
                shouldUpdateTheming.toggled()
                stage = 1
            } else if (stage === 1 && root.themingEnabled && themingSettingFileHandler.text().trim() === "true") {
                themingSettingFileHandler.setText("false")
                stage = 2
            } else if (stage === 2 && !root.themingEnabled && !shouldUpdateTheming.checked) {
                themingSettingFileHandler.reload()
                stage = 3
            } else if (stage === 3 && !root.themingEnabled && !shouldUpdateTheming.checked) {
                console.log("QML_TEST_PASS"); stop()
            }
        }
    }
}
''')

    def test_login_restore_finishes_before_slideshow_starts(self) -> None:
        for name in ("nm-applet", "killall", "pgrep", "qs", "ml4w-dock"):
            self.executable(self.bin / name, "exit 0\n")
        self.executable(self.bin / "awww-daemon", 'echo "awww-daemon 0.12.1"\n')
        self.executable(self.scripts / "ml4w-wallpaper",
                        'printf "RESTORE_START\\n" >> "$AUDIT_LOG"\n'
                        '/bin/sleep 0.2\n'
                        'printf "RESTORE_END\\n" >> "$AUDIT_LOG"\n')
        self.executable(self.scripts / "ml4w-wallpaper-automation",
                        'if [[ "$1" == "--status" ]]; then exit 1; fi\n'
                        'printf "SLIDESHOW_START\\n" >> "$AUDIT_LOG"\n')
        (self.home / ".cache/ml4w-welcome-autostart").touch()
        self.write(self.cache / "current_wallpaper", str(self.home / "input.png"))
        self.write(self.settings / "wallpaper-slideshow", "true")
        environment = dict(self.env, QS_ICON_THEME="test")
        subprocess.run(["bash", str(AUTOSTART)], env=environment, cwd=self.home,
                       capture_output=True, text=True, timeout=5, check=True)
        self.wait_until(lambda: "RESTORE_END" in self.log.read_text(), "restore never completed")
        self.wait_until(lambda: "SLIDESHOW_START" in self.log.read_text(), "slideshow never resumed")
        calls = self.log.read_text().splitlines()
        self.assertLess(calls.index("RESTORE_END"), calls.index("SLIDESHOW_START"),
                        "login restore and random update race over shared wallpaper/cache")

    def test_idle_loop_uses_no_cpu_or_extra_updates(self) -> None:
        self.start("--start")
        self.wait_until(lambda: "WALLPAPER" in self.log.read_text(), "slideshow did not start")
        pid = self.running_pid()
        time.sleep(0.1)

        def ticks() -> int:
            fields = Path(f"/proc/{pid}/stat").read_text().split(") ", 1)[1].split()
            return int(fields[11]) + int(fields[12])

        before = ticks()
        time.sleep(1)
        used = ticks() - before
        self.assertLessEqual(used, 1, "slideshow polls while idle")
        self.assertEqual(self.log.read_text().count("WALLPAPER"), 1)
        rss = next(line for line in Path(f"/proc/{pid}/status").read_text().splitlines()
                   if line.startswith("VmRSS:"))
        (self.home / "idle-metrics.json").write_text(json.dumps({"cpu_ticks_in_1s": used, "rss": rss}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
