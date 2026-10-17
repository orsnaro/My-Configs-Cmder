#!/usr/bin/env python3
"""Offline behavioral regressions for the real Quickshell updates module.

Run directly with python3. Only the external terminal/updater boundary is
replaced (log-only fakes on PATH and in the fixture HOME); the module, its
FileView watchers, the IPC handlers and the real QML scene are the snapshot
components. Every case runs in a disposable HOME below /tmp/opencode and no
package manager, update check or installer is ever allowed to execute.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import textwrap
from typing import Any
import unittest


CONFIG = Path(__file__).resolve().parents[3]
QUICKSHELL = CONFIG / "quickshell"
MODULE = QUICKSHELL / "StatusbarApp/UpdatesModule.qml"
TEMP_ROOT = Path("/tmp/opencode")
RESULT = "UPDATES_TEST_RESULT "
PROCESS_TIMEOUT = 20

# The scene instantiates the real module and drives it through real file
# changes performed by a child bash process. `__CACHE__` and `__BODY__` are
# filled per case; nothing else is templated.
QML = """\
import Quickshell
import Quickshell.Io
import QtQuick
import QtQuick.Window
import "StatusbarApp" as Real

ShellRoot {
    id: test
    property var failures: []
    property var observed: ({})
    property int ticks: 0
    property int stage: 0
    property bool done: false
    readonly property string cache: __CACHE__

    Window {
        visible: false
        width: 300
        height: 40
        Real.UpdatesModule { id: mod }
    }

    FileView {
        id: audit
        path: Quickshell.env("AUDIT_LOG")
        blockLoading: true
        printErrors: false
    }

    Process { id: mutator }

    function auditLines(): var {
        audit.reload()
        const raw = audit.text().trim()
        return raw === "" ? [] : raw.split("\\n")
    }

    function check(ok, message) { if (!ok) failures.push(message) }

    function mutate(script) {
        mutator.command = ["bash", "-c", script]
        mutator.running = true
    }

    function complete() {
        done = true
        observed.audit = auditLines()
        console.log("UPDATES_TEST_RESULT " + JSON.stringify({failures: failures, observed: observed}))
        Qt.quit()
    }

    Timer {
        interval: 40
        repeat: true
        running: !test.done
        onTriggered: {
            test.ticks++
            try { test.tick() }
            catch (error) { test.failures.push("QML test exception: " + error); test.complete() }
        }
    }

    Timer {
        interval: 9000
        running: !test.done
        onTriggered: { test.failures.push("case timed out after 9000 ms"); test.complete() }
    }

    function tick() { __BODY__ }
}
"""


class UpdatesModuleTests(unittest.TestCase):
    """Each QML case runs in a fresh offscreen Quickshell process."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="updates-module-", dir=TEMP_ROOT)
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)

        config = self.home / ".config"
        self.qs = config / "quickshell"
        (self.qs / "StatusbarApp").mkdir(parents=True)
        (self.qs / "StatusbarApp/UpdatesModule.qml").symlink_to(MODULE)
        for name in ("CustomTheme", "shared"):
            (self.qs / name).symlink_to(QUICKSHELL / name)
        for relative in ("StatusbarApp/UpdatesModule.qml", "CustomTheme", "shared"):
            target = (self.qs / relative).resolve(strict=True)
            self.assertEqual(target, QUICKSHELL / relative,
                             "QML imports must stay inside the snapshot")

        ml4w = config / "ml4w"
        settings = ml4w / "settings"
        scripts = ml4w / "scripts"
        settings.mkdir(parents=True)
        scripts.mkdir(parents=True)
        self.bin = self.home / "bin"
        self.bin.mkdir()
        self.audit = self.home / "audit.log"
        self.audit.touch()

        # Configured ML4W terminal, and log-only stand-ins for every external
        # boundary the module might reach. None of them perform package work.
        self.write(settings / "terminal.sh", "fixture-term\n")
        self.executable(self.bin / "fixture-term",
                        "printf 'TERMINAL %s :: %s\\n' \"$(basename \"$0\")\" \"$*\" >> \"$AUDIT_LOG\"\n")
        for path, tag in ((scripts / "ml4w-check-system-updates", "CHECK"),
                          (settings / "installupdates.sh", "LEGACY_INSTALLUPDATES"),
                          (scripts / "ml4w-install-system-updates", "ML4W_INSTALL"),
                          (self.bin / "arch-update", "ARCH_UPDATE_DIRECT"),
                          (self.bin / "pacman", "PACMAN"),
                          (self.bin / "flatpak", "FLATPAK")):
            self.executable(path, f"printf '{tag}\\n' >> \"$AUDIT_LOG\"\n")

        self.env = dict(os.environ)
        for name in ("QS_CONFIG_PATH", "QS_CONFIG_NAME", "QS_MANIFEST", "GCAL_DIR",
                     "DISPLAY", "WAYLAND_DISPLAY", "DBUS_SESSION_BUS_ADDRESS"):
            self.env.pop(name, None)
        self.env.update(HOME=str(self.home), PATH=f"{self.bin}:/usr/bin:/bin",
                        AUDIT_LOG=str(self.audit), QT_QPA_PLATFORM="offscreen",
                        QT_QUICK_BACKEND="software", DRYRUN="1", PYTHONDONTWRITEBYTECODE="1")
        for variable, folder in (("XDG_CONFIG_HOME", ".config"),
                                 ("XDG_CACHE_HOME", ".cache"),
                                 ("XDG_DATA_HOME", ".local/share"),
                                 ("XDG_STATE_HOME", ".local/state"),
                                 ("XDG_RUNTIME_DIR", "runtime")):
            path = self.home / folder
            path.mkdir(parents=True, exist_ok=True)
            path.chmod(0o700)
            self.env[variable] = str(path)

    @staticmethod
    def write(path: Path, text: str) -> None:
        path.write_text(text, encoding="utf-8")

    @staticmethod
    def executable(path: Path, body: str) -> None:
        path.write_text("#!/usr/bin/bash\n" + body, encoding="utf-8")
        path.chmod(0o700)

    @staticmethod
    def cache_for(state: Path) -> Path:
        return state / "arch-update/last_updates_check"

    def write_cache(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def run_qml(self, body: str, *, cache: Path, xdg_state: str | None = "default") -> dict[str, Any]:
        executable = shutil.which("quickshell")
        self.assertIsNotNone(executable, "offscreen runtime blocker: quickshell is not installed")
        source = QML.replace("__CACHE__", json.dumps(str(cache)))
        source = source.replace("__BODY__", textwrap.dedent(body))
        (self.qs / "shell.qml").write_text(source, encoding="utf-8")

        env = dict(self.env)
        if xdg_state is None:
            env.pop("XDG_STATE_HOME", None)
        elif xdg_state != "default":
            env["XDG_STATE_HOME"] = xdg_state

        command = [str(executable), "--no-color", "--path", str(self.qs / "shell.qml")]
        try:
            result = subprocess.run(command, env=env, cwd=self.home,
                                    capture_output=True, text=True, timeout=PROCESS_TIMEOUT)
        except subprocess.TimeoutExpired as error:
            self.fail(f"offscreen process timed out after {PROCESS_TIMEOUT}s: "
                      f"{error.stdout!r} {error.stderr!r}")
        output = result.stdout + result.stderr
        matches = re.findall(re.escape(RESULT) + r"(\{[^\n]*\})", output)
        self.assertEqual(len(matches), 1,
                         f"offscreen runtime/load blocker: expected one QML result, "
                         f"exit {result.returncode}\n{output}")
        self.assertEqual(result.returncode, 0, f"Quickshell exited unexpectedly\n{output}")
        report: dict[str, Any] = json.loads(matches[0])
        self.assertNotRegex(output, r"(?:ReferenceError|TypeError|SyntaxError):",
                            f"unexpected QML runtime error\n{output}")
        self.assertFalse(report["failures"], "\n".join(report["failures"])
                         + "\nObserved: " + json.dumps(report["observed"]))
        return report

    # The aggregate arch-update leaves behind lists system, AUR and Flatpak
    # entries together; blank separator lines must not be counted.
    AGGREGATE = "pkg-a 1 -> 2\npkg-b 1 -> 2\n\naur-x 1 -> 2\nflatpak-z 1 -> 2\n"

    def test_counts_nonblank_aggregate_lines_including_flatpak(self) -> None:
        state = self.home / "state-xdg"
        cache = self.cache_for(state)
        self.write_cache(cache, self.AGGREGATE)
        # A decoy with a different size in the HOME fallback must be ignored.
        self.write_cache(self.cache_for(self.home / ".local/state"),
                         "d1\nd2\nd3\nd4\nd5\nd6\nd7\nd8\nd9\n")
        self.run_qml("""
            if (stage === 0 && mod.count === 4) {
                stage = 1
                check(!mod.collapsed, "four nonblank entries must not be collapsed")
                check(mod.visible === true, "a populated cache must show the module")
                observed.count = mod.count
                complete()
            }
            if (ticks > 150) {
                check(false, "aggregate count never reached 4 (module count " + mod.count + ")")
                complete()
            }
        """, cache=cache, xdg_state=str(state))

    def test_missing_cache_hides_module(self) -> None:
        cache = self.cache_for(self.home / ".local/state")
        self.run_qml("""
            if (ticks === 15) {
                check(mod.count === 0, "a missing cache must report zero updates")
                check(mod.collapsed, "a missing cache must collapse the module")
                check(!mod.visible, "a missing cache must hide the module")
                complete()
            }
        """, cache=cache)

    def test_empty_cache_hides_module(self) -> None:
        cache = self.cache_for(self.home / ".local/state")
        self.write_cache(cache, "")
        self.run_qml("""
            if (ticks === 15) {
                check(mod.count === 0, "an empty cache must report zero updates")
                check(mod.collapsed, "an empty cache must collapse the module")
                check(!mod.visible, "an empty cache must hide the module")
                complete()
            }
        """, cache=cache)

    def test_state_falls_back_to_home_local_state(self) -> None:
        cache = self.cache_for(self.home / ".local/state")
        self.write_cache(cache, "pkg-a 1 -> 2\npkg-b 1 -> 2\n")
        self.run_qml("""
            if (stage === 0 && mod.count === 2) {
                stage = 1
                check(mod.visible === true, "the HOME fallback cache must show the module")
                complete()
            }
            if (ticks > 150) {
                check(false, "HOME fallback count never reached 2 (module count " + mod.count + ")")
                complete()
            }
        """, cache=cache, xdg_state=None)

    def test_state_path_with_spaces(self) -> None:
        state = self.home / "state dir with spaces"
        cache = self.cache_for(state)
        self.write_cache(cache, "pkg-a 1 -> 2\npkg-b 1 -> 2\npkg-c 1 -> 2\n")
        self.run_qml("""
            if (stage === 0 && mod.count === 3) {
                stage = 1
                check(mod.visible === true, "a spaced state path must still be readable")
                complete()
            }
            if (ticks > 150) {
                check(false, "spaced-path count never reached 3 (module count " + mod.count + ")")
                complete()
            }
        """, cache=cache, xdg_state=str(state))

    def test_in_place_write_updates_count(self) -> None:
        cache = self.cache_for(self.home / ".local/state")
        self.write_cache(cache, "pkg-a 1 -> 2\npkg-b 1 -> 2\n")
        self.run_qml("""
            if (stage === 0 && mod.count === 2) {
                observed.before = 2
                stage = 1
                mutate("printf 'a\\\\nb\\\\nc\\\\nd\\\\ne\\\\n' > '" + cache + "'")
                return
            }
            if (stage === 1 && mod.count === 5) {
                observed.after = 5
                check(mod.visible === true, "an in-place rewrite must keep the module visible")
                complete()
                return
            }
            if (ticks > 150) {
                check(false, "in-place rewrite never updated the count (stage " + stage
                      + ", count " + mod.count + ")")
                complete()
            }
        """, cache=cache)

    def test_atomic_replacement_updates_count(self) -> None:
        cache = self.cache_for(self.home / ".local/state")
        self.write_cache(cache, "pkg-a 1 -> 2\n")
        self.run_qml("""
            if (stage === 0 && mod.count === 1) {
                stage = 1
                mutate("printf 'a\\\\nb\\\\nc\\\\n' > '" + cache + ".tmp' && mv '" + cache + ".tmp' '" + cache + "'")
                return
            }
            if (stage === 1 && mod.count === 3) {
                observed.count = 3
                complete()
                return
            }
            if (ticks > 150) {
                check(false, "atomic replacement never updated the count (stage " + stage
                      + ", count " + mod.count + ")")
                complete()
            }
        """, cache=cache)

    def test_clearing_cache_hides_module(self) -> None:
        cache = self.cache_for(self.home / ".local/state")
        self.write_cache(cache, "pkg-a 1 -> 2\npkg-b 1 -> 2\npkg-c 1 -> 2\n")
        self.run_qml("""
            if (stage === 0 && mod.count === 3) {
                stage = 1
                mutate(": > '" + cache + "'")
                return
            }
            if (stage === 1 && mod.count === 0) {
                check(mod.collapsed, "an emptied cache must collapse the module")
                check(!mod.visible, "an emptied cache must hide the module")
                observed.cleared = true
                complete()
                return
            }
            if (ticks > 150) {
                check(false, "cleared cache never reported zero (stage " + stage
                      + ", count " + mod.count + ")")
                complete()
            }
        """, cache=cache)

    def test_deleted_cache_hides_module(self) -> None:
        cache = self.cache_for(self.home / ".local/state")
        self.write_cache(cache, "pkg-a 1 -> 2\npkg-b 1 -> 2\npkg-c 1 -> 2\n")
        self.run_qml("""
            if (stage === 0 && mod.count === 3) {
                stage = 1
                mutate("rm -f '" + cache + "'")
                return
            }
            if (stage === 1 && mod.count === 0) {
                check(mod.collapsed, "a deleted cache must collapse the module")
                check(!mod.visible, "a deleted cache must hide the module")
                observed.deleted = true
                complete()
                return
            }
            if (ticks > 150) {
                check(false, "deleted cache never reported zero (stage " + stage
                      + ", count " + mod.count + ")")
                complete()
            }
        """, cache=cache)

    def test_click_launches_configured_terminal_with_arch_update(self) -> None:
        cache = self.cache_for(self.home / ".local/state")
        self.write_cache(cache, "pkg-a 1 -> 2\n")
        report = self.run_qml("""
            if (stage === 0 && ticks === 8) {
                mod.activate()
                stage = 1
                return
            }
            if (stage === 1 && auditLines().length > 0) {
                stage = 2
                complete()
                return
            }
            if (ticks > 150) {
                check(false, "activate() never launched the configured terminal")
                complete()
            }
        """, cache=cache)
        audit = "\n".join(report["observed"].get("audit", []))
        self.assertIn("TERMINAL fixture-term :: --class dotfiles-floating -e arch-update", audit,
                      "activate() must run arch-update in the configured ML4W terminal")
        self.assertNotIn("--check", audit, "the interactive launch must not use --check")
        for forbidden in ("CHECK", "LEGACY_INSTALLUPDATES", "ML4W_INSTALL",
                          "ARCH_UPDATE_DIRECT", "PACMAN", "FLATPAK"):
            self.assertNotIn(forbidden, audit,
                             f"interactive launch must not invoke {forbidden}")

    def test_load_and_refresh_never_run_external_commands(self) -> None:
        cache = self.cache_for(self.home / ".local/state")
        self.write_cache(cache, "pkg-a 1 -> 2\npkg-b 1 -> 2\n")
        report = self.run_qml("""
            if (stage === 0 && ticks === 8) { mod.refresh(); stage = 1; return }
            if (stage === 1 && ticks === 16) { mod.refresh(); stage = 2; return }
            if (stage === 2 && ticks === 24) {
                observed.count = mod.count
                check(mod.count === 2, "refresh() must re-read the cached aggregate")
                complete()
                return
            }
        """, cache=cache)
        self.assertEqual(report["observed"].get("audit"), [],
                         "load/refresh must not run update checks, installers or package managers")


if __name__ == "__main__":
    unittest.main(verbosity=2)
