#!/usr/bin/env python3
"""Offline behavioral regressions for the real Quickshell calendar panel.

Run directly with python3. Only Google subprocesses are replaced; the panel,
Theme, Qt delegates, FileView and Process wiring are the snapshot components.
Every test has a disposable HOME below /tmp/opencode. No credentials are read.
"""

from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
from typing import Any
import unittest


CONFIG = Path(__file__).resolve().parents[2]
TEMP_ROOT = Path("/tmp/opencode")
RESULT = "CALENDAR_TEST_RESULT "
PROCESS_TIMEOUT = 10


def stamp(offset_hours: float = 0) -> str:
    return (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=offset_hours)).isoformat()


def event(title: str, start: str, end: str, all_day: bool = False) -> dict[str, Any]:
    return {"summary": title, "start": start, "end": end, "allDay": all_day}


def agenda(events: list[dict[str, Any]] | None = None,
           tasks: list[dict[str, Any]] | None = None,
           updated: str | None = None) -> dict[str, Any]:
    return {"updated": updated or stamp(), "events": events or [], "tasks": tasks or []}


SYNC_FIXTURE = """\
import json, os, pathlib, signal, sys, time
root = pathlib.Path.home() / '.config/gcal'
(root / 'sync-started').write_text('started')
mode = os.environ['CALENDAR_FIXTURE_MODE']
time.sleep(0.35)
if mode == 'failure':
    (root / 'sync-failed').write_text('exit 7')
    print('fixture OAuth expired; refresh failed', file=sys.stderr)
    sys.exit(7)
if mode == 'sigterm':
    (root / 'sync-signaled').write_text('sigterm')
    os.kill(os.getpid(), signal.SIGTERM)
if mode == 'sigkill':
    (root / 'sync-signaled').write_text('sigkill')
    os.kill(os.getpid(), signal.SIGKILL)
if mode == 'fail_once':
    if not (root / 'sync-failed').exists():
        (root / 'sync-failed').write_text('exit 7')
        print('fixture OAuth expired; refresh failed', file=sys.stderr)
        sys.exit(7)
    data = (root / 'replacement.json').read_text()
    (root / 'cache.json.tmp').write_text(data)
    os.replace(root / 'cache.json.tmp', root / 'cache.json')
    (root / 'atomic-written').write_text('replaced')
if mode in ('success', 'atomic'):
    data = (root / 'replacement.json').read_text()
    (root / 'cache.json.tmp').write_text(data)
    os.replace(root / 'cache.json.tmp', root / 'cache.json')
    (root / 'atomic-written').write_text('replaced')
if mode == 'atomic':
    # Keep stdout open: observing this update must not rely on streamFinished.
    time.sleep(3)
(root / 'sync-completed').write_text('completed')
print('fixture sync completed')
"""

REMINDER_FIXTURE = """\
import pathlib
root = pathlib.Path.home() / '.config/gcal'
with (root / 'reminder-launches').open('a') as stream:
    stream.write('launched\\n')
"""

# QObject IDs remain private. Walk instantiated visual items instead of parsing
# product source or adding test-only aliases to it.
QML = """\
import Quickshell
import Quickshell.Io
import QtQuick
import QtQuick.Window
import QtQuick.Controls
import "StatusbarApp" as Real

ShellRoot {
    id: test
    property var fixture: __FIXTURE__
    property var failures: []
    property var observed: ({})
    property int ticks: 0
    property int stage: 0
    property int since: 0
    property bool done: false
    property var savedLabels: []

    Window {
        visible: true
        width: 800
        height: 500
        Real.CalendarPanel { id: panel; x: 40; openY: 20 }
    }
    FileView {
        id: effects
        path: Quickshell.env("HOME") + "/.config/gcal/" + __EFFECT__
        blockLoading: true
        printErrors: false
    }
    FileView {
        id: completion
        path: Quickshell.env("HOME") + "/.config/gcal/sync-completed"
        blockLoading: true
        printErrors: false
    }
    function effect() { effects.reload(); return effects.text().trim() }
    function check(ok, message) { if (!ok) failures.push(message) }
    function items(root) {
        let found = [root]
        if (root.children) {
            for (let child of root.children) found = found.concat(items(child))
        }
        return found
    }
    function texts(root) {
        return items(root).filter(i => typeof i.text === "string")
    }
    function labels() {
        return texts(panel).filter(i => i.visible && i.opacity > 0).map(i => i.text)
    }
    function titleItem(title) { return texts(panel).find(i => i.text === title) }
    function names() { return panel.agendaEvents.map(e => e.summary) }
    function views() {
        return items(panel).filter(i => typeof i.itemAtIndex === "function"
            && typeof i.positionViewAtIndex === "function")
    }
    function tooltip(item, title) {
        // Inspect only this instantiated delegate, never other agenda rows.
        for (let view of views()) {
            for (let index = 0; index < view.count; index++) {
                let row = view.itemAtIndex(index)
                if (row && items(row).indexOf(item) !== -1)
                    return items(row).some(i => i.ToolTip && i.ToolTip.text.indexOf(title) !== -1)
            }
        }
        return !!item.ToolTip && item.ToolTip.text.indexOf(title) !== -1
    }
    function complete() {
        done = true
        observed.names = names()
        observed.labels = labels()
        console.log("CALENDAR_TEST_RESULT " + JSON.stringify({failures: failures, observed: observed}))
        Qt.quit()
    }
    Component.onCompleted: {
        // Optional assignment keeps the old widget loadable: absence is tested
        // through reminder effects, not a nonexistent property binding.
        if (typeof panel.manageAgendaBackground !== "undefined")
            panel.manageAgendaBackground = __OWNER__
        __START__
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
        interval: 6000
        running: !test.done
        onTriggered: { test.failures.push("case timed out after 6000 ms"); test.complete() }
    }
    function tick() { __BODY__ }
}
"""

# Two real panels sharing one fixture HOME/cache: a side panel whose own
# sync fails, then a center panel whose independent sync succeeds.
TWO_QML = """\
import Quickshell
import Quickshell.Io
import QtQuick
import QtQuick.Window
import QtQuick.Controls
import "StatusbarApp" as Real

ShellRoot {
    id: test
    property var fixture: __FIXTURE__
    property var failures: []
    property var observed: ({})
    property int ticks: 0
    property int stage: 0
    property int since: 0
    property bool done: false

    Window {
        visible: true
        width: 900
        height: 500
        Real.CalendarPanel { id: side; x: 40; openY: 20 }
        Real.CalendarPanel { id: center; x: 460; openY: 20 }
    }
    FileView {
        id: failedMark
        path: Quickshell.env("HOME") + "/.config/gcal/sync-failed"
        blockLoading: true
        printErrors: false
    }
    FileView {
        id: doneMark
        path: Quickshell.env("HOME") + "/.config/gcal/sync-completed"
        blockLoading: true
        printErrors: false
    }
    function failed() { failedMark.reload(); return failedMark.text().trim() }
    function finished() { doneMark.reload(); return doneMark.text().trim() }
    function check(ok, message) { if (!ok) failures.push(message) }
    function items(root) {
        let found = [root]
        if (root.children) {
            for (let child of root.children) found = found.concat(items(child))
        }
        return found
    }
    function texts(root) {
        return items(root).filter(i => typeof i.text === "string")
    }
    function sideLabels() {
        return texts(side).filter(i => i.visible && i.opacity > 0).map(i => i.text)
    }
    function sideNames() { return side.agendaEvents.map(e => e.summary) }
    function errorShown() {
        return sideLabels().some(t => /fail|error|expired|sign.?in|auth/i.test(t))
    }
    function complete() {
        done = true
        observed.sideError = side.agendaError
        observed.centerError = center.agendaError
        observed.sideNames = sideNames()
        observed.sideLabels = sideLabels()
        console.log("CALENDAR_TEST_RESULT " + JSON.stringify({failures: failures, observed: observed}))
        Qt.quit()
    }
    Component.onCompleted: {
        if (typeof center.manageAgendaBackground !== "undefined")
            center.manageAgendaBackground = true
        side.isOpen = true
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
        interval: 6000
        running: !test.done
        onTriggered: { test.failures.push("case timed out after 6000 ms"); test.complete() }
    }
    function tick() { __BODY__ }
}
"""


class CalendarPanelTests(unittest.TestCase):
    """Each QML case runs in a fresh offscreen Quickshell process."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="calendar-panel-", dir=TEMP_ROOT)
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.gcal = self.home / ".config/gcal"
        self.gcal.mkdir(parents=True)
        self.shell = self.home / ".config/quickshell"
        (self.shell / "StatusbarApp").mkdir(parents=True)
        (self.shell / "StatusbarApp/CalendarPanel.qml").symlink_to(
            CONFIG / "quickshell/StatusbarApp/CalendarPanel.qml")
        for name in ("CustomTheme", "shared"):
            (self.shell / name).symlink_to(CONFIG / "quickshell" / name)
        for relative in ("StatusbarApp/CalendarPanel.qml", "CustomTheme", "shared"):
            target = (self.shell / relative).resolve(strict=True)
            self.assertEqual(target, CONFIG / "quickshell" / relative)
            self.assertTrue(target.is_relative_to(CONFIG), "QML imports must stay in the snapshot")
        colors = self.home / ".config/ml4w/colors"
        colors.mkdir(parents=True)
        (colors / "colors.json").write_text("{}", encoding="utf-8")
        self.env = dict(os.environ)
        for name in ("QS_CONFIG_PATH", "QS_CONFIG_NAME", "QS_MANIFEST", "GCAL_DIR",
                     "DISPLAY", "WAYLAND_DISPLAY", "DBUS_SESSION_BUS_ADDRESS"):
            self.env.pop(name, None)
        self.env.update(HOME=str(self.home), QT_QPA_PLATFORM="offscreen",
                        QT_QUICK_BACKEND="software", DRYRUN="1",
                        PYTHONDONTWRITEBYTECODE="1")
        for variable, folder in (("XDG_CONFIG_HOME", ".config"),
                                 ("XDG_CACHE_HOME", ".cache"),
                                 ("XDG_DATA_HOME", ".local/share"),
                                 ("XDG_STATE_HOME", ".local/state"),
                                 ("XDG_RUNTIME_DIR", "runtime")):
            path = self.home / folder
            path.mkdir(parents=True, exist_ok=True)
            path.chmod(0o700)
            self.env[variable] = str(path)
        (self.gcal / ".venv/bin").mkdir(parents=True)
        (self.gcal / ".venv/bin/python").symlink_to(sys.executable)
        (self.gcal / "gcal-sync.py").write_text(SYNC_FIXTURE, encoding="utf-8")
        (self.gcal / "gcal-remind.py").write_text(REMINDER_FIXTURE, encoding="utf-8")

    def run_qml(self, fixture: dict[str, Any], body: str, *, mode: str = "noop",
                owner: bool = False, start: str = "panel.isOpen = true",
                effect: str = "sync-completed",
                replacement: dict[str, Any] | None = None,
                timezone: str | None = None) -> dict[str, Any]:
        executable = shutil.which("quickshell")
        self.assertIsNotNone(executable, "offscreen runtime blocker: quickshell is not installed")
        for filename, data in (("cache.json", fixture),
                               ("replacement.json", replacement or fixture)):
            (self.gcal / filename).write_text(json.dumps(data), encoding="utf-8")
        source = QML
        replacements = {"__FIXTURE__": json.dumps(fixture), "__BODY__": textwrap.dedent(body),
                        "__START__": start, "__OWNER__": str(owner).lower(),
                        "__EFFECT__": json.dumps(effect)}
        for key, value in replacements.items():
            source = source.replace(key, value)
        (self.shell / "shell.qml").write_text(source, encoding="utf-8")
        self.env["CALENDAR_FIXTURE_MODE"] = mode
        env = dict(self.env)
        if timezone is not None:
            env["TZ"] = timezone
        command = [str(executable), "--no-color", "--path", str(self.shell / "shell.qml")]
        try:
            result = subprocess.run(command, env=env, cwd=self.home,
                                    capture_output=True, text=True, timeout=PROCESS_TIMEOUT)
        except subprocess.TimeoutExpired as error:
            self.fail(f"offscreen process timed out after {PROCESS_TIMEOUT}s: {error.stdout!r} {error.stderr!r}")
        output = result.stdout + result.stderr
        matches = re.findall(re.escape(RESULT) + r"(\{[^\n]*\})", output)
        self.assertEqual(len(matches), 1,
                         f"offscreen runtime/load blocker: expected one QML result, exit {result.returncode}\n{output}")
        self.assertEqual(result.returncode, 0, f"Quickshell exited unexpectedly\n{output}")
        report: dict[str, Any] = json.loads(matches[0])
        self.assertNotRegex(output, r"(?:ReferenceError|TypeError|SyntaxError):",
                            f"unexpected QML runtime error\n{output}")
        self.assertFalse(report["failures"], "\n".join(report["failures"])
                         + "\nObserved: " + json.dumps(report["observed"]))
        return report

    def run_two_panel(self, fixture: dict[str, Any], replacement: dict[str, Any],
                        body: str, *, mode: str = "fail_once") -> dict[str, Any]:
        executable = shutil.which("quickshell")
        self.assertIsNotNone(executable, "offscreen runtime blocker: quickshell is not installed")
        (self.gcal / "cache.json").write_text(json.dumps(fixture), encoding="utf-8")
        (self.gcal / "replacement.json").write_text(json.dumps(replacement), encoding="utf-8")
        source = TWO_QML.replace("__FIXTURE__", json.dumps(fixture))
        source = source.replace("__BODY__", textwrap.dedent(body))
        (self.shell / "shell.qml").write_text(source, encoding="utf-8")
        self.env["CALENDAR_FIXTURE_MODE"] = mode
        command = [str(executable), "--no-color", "--path", str(self.shell / "shell.qml")]
        try:
            result = subprocess.run(command, env=self.env, cwd=self.home,
                                    capture_output=True, text=True, timeout=PROCESS_TIMEOUT)
        except subprocess.TimeoutExpired as error:
            self.fail(f"offscreen process timed out after {PROCESS_TIMEOUT}s: {error.stdout!r} {error.stderr!r}")
        output = result.stdout + result.stderr
        matches = re.findall(re.escape(RESULT) + r"(\{[^\n]*\})", output)
        self.assertEqual(len(matches), 1,
                          f"offscreen runtime/load blocker: expected one QML result, exit {result.returncode}\n{output}")
        self.assertEqual(result.returncode, 0, f"Quickshell exited unexpectedly\n{output}")
        report: dict[str, Any] = json.loads(matches[0])
        self.assertNotRegex(output, r"(?:ReferenceError|TypeError|SyntaxError):",
                            f"unexpected QML runtime error\n{output}")
        self.assertFalse(report["failures"], "\n".join(report["failures"])
                         + "\nObserved: " + json.dumps(report["observed"]))
        return report

    def simple_case(self, fixture: dict[str, Any], checks: str) -> None:
        self.run_qml(fixture, """
            if (ticks === 12) panel.parseAgenda(JSON.stringify(fixture))
            if (ticks === 16) {
        """ + checks + "\ncomplete()\n}")

    def all_day_case(self, timezone: str, utc_offset: int, checks: str) -> None:
        # Build dates in the QML child, not the parent's machine timezone. UTC
        # midnight parsing disagrees with local expiry in at least one extreme
        # zone at any hour, and always shifts date labels in the western zone.
        body = """
            if (ticks === 12) {
                let now = new Date()
                observed.timezone = Quickshell.env("TZ")
                observed.utcOffset = now.getTimezoneOffset()
                check(observed.timezone === __ZONE__ && observed.utcOffset === __OFFSET__,
                      "fixture child must use the intended timezone before testing behavior")
                if (failures.length) { complete(); return }
                function day(offset) {
                    let local = new Date(now.getFullYear(), now.getMonth(), now.getDate() + offset, 12)
                    // Qt.formatDate(Date) can convert the calendar date in a
                    // negative zone; extract local fields without that bridge.
                    return local.getFullYear() + "-" + String(local.getMonth() + 1).padStart(2, "0")
                        + "-" + String(local.getDate()).padStart(2, "0")
                }
                fixture = {
                    updated: now.toISOString(), tasks: [], events: [
                        {summary: "Ended at midnight", start: day(-1), end: day(0), allDay: true},
                        {summary: "All day today", start: day(0), end: day(1), allDay: true},
                        {summary: "All day future", start: day(1), end: day(2), allDay: true}
                    ]
                }
                observed.localToday = day(0)
                observed.utcToday = now.toISOString().slice(0, 10)
                observed.utcParsedNames = fixture.events.filter(e => new Date(e.end) > now).map(e => e.summary)
                observed.expectedDateLabel = Qt.formatDateTime(new Date(now.getFullYear(), now.getMonth(),
                                                                        now.getDate() + 1, 12), "d MMM")
                observed.utcParsedDateLabel = Qt.formatDateTime(new Date(fixture.events[2].start), "d MMM")
                if (observed.utcOffset === 720)
                    check(observed.utcParsedDateLabel !== observed.expectedDateLabel,
                          "western fixture must discriminate the UTC-midnight date-label shift")
                if (failures.length) { complete(); return }
                panel.parseAgenda(JSON.stringify(fixture))
            }
            if (ticks === 16) {
        """.replace("__ZONE__", json.dumps(timezone)).replace("__OFFSET__", str(utc_offset))
        self.run_qml(agenda(), body + checks + "\ncomplete()\n}", timezone=timezone)

    def test_timed_events_filter_expired_keep_ongoing_and_future(self) -> None:
        fixture = agenda([event("Expired", stamp(-3), stamp(-2)),
                          event("Ongoing", stamp(-1), stamp(1)),
                          event("Future", stamp(2), stamp(3))])
        self.simple_case(fixture, """
            check(JSON.stringify(names()) === JSON.stringify(["Ongoing", "Future"]),
                  "expired events must be removed; ongoing and future events retained")
            check(!titleItem("Expired") && !!titleItem("Ongoing") && !!titleItem("Future"),
                  "rendered delegates must reflect filtered events")
        """)

    def exclusive_all_day_case(self, timezone: str, utc_offset: int) -> None:
        self.all_day_case(timezone, utc_offset, """
            check(JSON.stringify(names()) === JSON.stringify(["All day today", "All day future"]),
                  "all-day end dates are exclusive local calendar dates")
            check(!titleItem("Ended at midnight"), "expired all-day delegate must be absent")
        """)

    def test_exclusive_all_day_end_east(self) -> None:
        self.exclusive_all_day_case("Etc/GMT-14", -840)

    def test_exclusive_all_day_end_west(self) -> None:
        self.exclusive_all_day_case("Etc/GMT+12", 720)

    def test_invalid_timestamps_are_not_upcoming(self) -> None:
        fixture = agenda([event("Bad start", "not-a-date", stamp(3)),
                          event("Bad end", stamp(1), "not-an-end"),
                          event("Bad all-day", "not-a-date", "not-an-end", True),
                          event("Valid", stamp(2), stamp(3))])
        self.simple_case(fixture, """
            check(JSON.stringify(names()) === JSON.stringify(["Valid"]),
                  "invalid start/end timestamps must not become upcoming rows")
            check(!titleItem("Bad start") && !titleItem("Bad end") && !!titleItem("Valid"),
                  "invalid timestamp delegates must not render")
        """)

    def test_malformed_event_shape_is_not_upcoming(self) -> None:
        instant = stamp(2)
        fixture = agenda([event("Inverted", stamp(3), stamp(2)),
                          {"start": stamp(1), "end": stamp(2)},
                          {"summary": 42, "start": stamp(1), "end": stamp(2)},
                          event("Instant", instant, instant),
                          event("Valid", stamp(2), stamp(3)),
                          None, "oops"])
        self.simple_case(fixture, """
            check(JSON.stringify(names()) === JSON.stringify(["Instant", "Valid"]),
                  "inverted intervals, missing/non-string titles and non-object entries must not become upcoming rows")
            check(!!titleItem("Instant") && !!titleItem("Valid"),
                  "future zero-duration and valid delegates must render")
            check(!titleItem("Inverted"), "inverted-interval delegate must be absent")
        """)

    def test_malformed_json_preserves_last_valid_agenda(self) -> None:
        fixture = agenda([event("Valid retained", stamp(1), stamp(2))], [{"title": "Task retained"}])
        self.simple_case(fixture, """
            panel.parseAgenda("{broken JSON")
            check(JSON.stringify(names()) === JSON.stringify(["Valid retained"]),
                  "malformed JSON must preserve the last usable events")
            check(panel.agendaTasks.length === 1 && !!titleItem("Valid retained"),
                  "malformed JSON must not discard tasks or existing delegates")
        """)

    def test_stale_cache_has_visible_status(self) -> None:
        fixture = agenda([event("Cached future", stamp(24), stamp(25))])
        self.run_qml(fixture, """
            if (ticks === 12) panel.parseAgenda(JSON.stringify(fixture))
            if (ticks === 16) {
                savedLabels = labels()
                fixture.updated = new Date(Date.now() - 7 * 86400000).toISOString()
                panel.parseAgenda(JSON.stringify(fixture))
            }
            if (ticks === 20) {
                let changed = labels().filter(t => savedLabels.indexOf(t) === -1)
                check(changed.some(t => /stale|out.?of.?date|offline|refresh|cached|updated|sync/i.test(t)),
                      "a week-old cache must visibly signal its stale status")
                check(!!titleItem("Cached future"), "usable future cached events must remain visible")
                complete()
            }
        """)

    def test_sync_finishes_after_panel_closes(self) -> None:
        fixture = agenda([event("Before sync", stamp(1), stamp(2))])
        replacement = agenda([event("After sync", stamp(3), stamp(4))])
        self.run_qml(fixture, """
            if (stage === 0 && effect()) {
                completion.reload()
                check(completion.text().trim() === "", "sync must still be in flight at panel close")
                panel.isOpen = false
                stage = 1
                since = ticks
            }
            if (stage === 1 && ticks - since >= 25) {
                completion.reload()
                observed.syncCompleted = completion.text().trim()
                check(observed.syncCompleted === "completed", "closing the panel must not cancel an in-flight sync")
                check(names().indexOf("After sync") !== -1, "completed sync must reload cache while panel is closed")
                complete()
            }
        """, mode="success", effect="sync-started", replacement=replacement,
                     start="panel.isOpen = true")

    def test_failed_sync_surfaces_visible_error(self) -> None:
        fixture = agenda([event("Cached event", stamp(1), stamp(2))])
        self.run_qml(fixture, """
            if (ticks === 25) {
                check(effect() === "exit 7", "failure fixture must actually have exited")
                check(labels().some(t => /fail|error|expired|sign.?in|auth/i.test(t)),
                      "failed sync must surface a visible error, not silently appear fresh")
                check(!!titleItem("Cached event"), "failed sync should retain usable cached data")
                complete()
            }
        """, mode="failure", effect="sync-failed")

    def test_sigterm_exit_stays_silent(self) -> None:
        fixture = agenda([event("Cached event", stamp(1), stamp(2))])
        self.run_qml(fixture, """
            if (ticks === 25) {
                check(effect() === "sigterm", "signal fixture must actually have terminated itself")
                check(!labels().some(t => /fail|error|expired|sign.?in|auth/i.test(t)),
                      "expected SIGTERM from unloading must not surface an error label")
                check(!!titleItem("Cached event"), "cached data must remain after SIGTERM")
                complete()
            }
        """, mode="sigterm", effect="sync-signaled")

    def test_sigkill_crash_surfaces_visible_error(self) -> None:
        fixture = agenda([event("Cached event", stamp(1), stamp(2))])
        self.run_qml(fixture, """
            if (ticks === 25) {
                check(effect() === "sigkill", "crash fixture must actually have been killed")
                check(labels().some(t => /fail|error|expired|sign.?in|auth/i.test(t)),
                      "abnormal sync death must surface a visible error, not look successful")
                check(!!titleItem("Cached event"), "crashed sync should retain usable cached data")
                complete()
            }
        """, mode="sigkill", effect="sync-signaled")

    def test_side_error_retires_on_center_success_newer_cache(self) -> None:
        fixture = agenda([event("Cached event", stamp(1), stamp(2))])
        replacement = agenda([event("Fresh after success", stamp(3), stamp(4))],
                             updated=stamp(1))
        self.run_two_panel(fixture, replacement, """
            if (stage === 0 && side.agendaError !== "" && failed() !== "") {
                check(errorShown(), "side panel must surface its own sync failure")
                if (failures.length) { complete(); return }
                side.parseAgenda(JSON.stringify(fixture))
                check(side.agendaError !== "", "unchanged-cache reload must not retire the error")
                let older = JSON.parse(JSON.stringify(fixture))
                older.updated = new Date(Date.now() - 3600000).toISOString()
                side.parseAgenda(JSON.stringify(older))
                check(side.agendaError !== "", "older snapshot must not retire the error")
                let invalid = JSON.parse(JSON.stringify(fixture))
                invalid.updated = "not-a-timestamp"
                side.parseAgenda(JSON.stringify(invalid))
                check(side.agendaError !== "", "invalid generation must not retire the error")
                if (failures.length) { complete(); return }
                observed.sideErrorKept = side.agendaError
                center.isOpen = true
                stage = 1
            }
            if (stage === 1 && finished() !== "") {
                stage = 2
                since = ticks
            }
            if (stage === 2 && ticks - since >= 20) {
                check(center.agendaError === "", "center panel must be clean after its own success")
                check(center.agendaEvents.map(e => e.summary).indexOf("Fresh after success") !== -1,
                      "center panel must show the fresh generation")
                check(side.agendaError === "",
                      "side panel must retire the obsolete error on the genuinely newer snapshot")
                check(sideNames().indexOf("Fresh after success") !== -1,
                      "side panel must observe the fresh generation through the shared cache")
                complete()
            }
        """)

    def test_non_owner_does_not_launch_reminders(self) -> None:
        self.run_qml(agenda(), """
            if (ticks === 16) {
                check(effect() === "", "non-owner panel must not launch a reminder subprocess")
                complete()
            }
        """, effect="reminder-launches", start="", owner=False)

    def test_owner_launches_reminders(self) -> None:
        self.run_qml(agenda(), """
            if (ticks === 16) {
                check(effect() === "launched", "owner must retain exactly one startup reminder launch")
                complete()
            }
        """, effect="reminder-launches", start="", owner=True)

    def test_atomic_cache_change_reloads_before_sync_exits(self) -> None:
        fixture = agenda([event("Old cache", stamp(1), stamp(2))])
        replacement = agenda([event("Atomic replacement", stamp(3), stamp(4))])
        self.run_qml(fixture, """
            if (stage === 0 && effect()) { stage = 1; since = ticks }
            if (stage === 1 && ticks - since >= 12) {
                completion.reload()
                observed.syncCompleted = completion.text().trim()
                check(observed.syncCompleted === "", "atomic case must be observed before sync exits")
                check(names().indexOf("Atomic replacement") !== -1,
                      "FileView must observe an atomic cache replacement without reopening or sync exit")
                check(!!titleItem("Atomic replacement"), "file-change reload must update instantiated delegates")
                complete()
            }
        """, mode="atomic", effect="atomic-written", replacement=replacement)
        self.assertFalse((self.gcal / "sync-completed").exists(),
                         "atomic case must finish before stdout/exit can reload the cache")

    def all_day_label_case(self, timezone: str, utc_offset: int) -> None:
        self.all_day_case(timezone, utc_offset, """
            let title = titleItem("All day future")
            let rowLabels = title ? texts(title.parent).filter(i => i !== title).map(i => i.text).join(" ") : ""
            check(/all.day/i.test(rowLabels) && rowLabels.indexOf(observed.expectedDateLabel) !== -1,
                  "all-day time label must include its calendar date; got " + rowLabels)
        """)

    def test_all_day_label_includes_date_east(self) -> None:
        self.all_day_label_case("Etc/GMT-14", -840)

    def test_all_day_label_includes_date_west(self) -> None:
        self.all_day_label_case("Etc/GMT+12", 720)

    def test_six_tasks_have_72px_viewport_and_24px_rows(self) -> None:
        fixture = agenda(tasks=[{"title": f"Task row {number}"} for number in range(6)])
        self.run_qml(fixture, """
            if (ticks === 12) panel.parseAgenda(JSON.stringify(fixture))
            if (ticks === 16) {
                let view = views().find(v => v.count === 6)
                check(!!view, "six tasks must produce six model rows")
                if (view) {
                    observed.taskViewport = view.height
                    observed.firstRowHeight = view.itemAtIndex(0) ? view.itemAtIndex(0).height : -1
                    check(Math.abs(view.height - 72) < 0.5, "task viewport must be 72 px, got " + view.height)
                    check(Math.abs(view.contentHeight - 144) < 0.5,
                          "six 24 px task rows must have 144 px content height, got " + view.contentHeight)
                    check(view.itemAtIndex(0) && Math.abs(view.itemAtIndex(0).height - 24) < 0.5,
                          "first task row must be 24 px")
                    view.positionViewAtIndex(5, ListView.End)
                }
            }
            if (ticks === 20) {
                let view = views().find(v => v.count === 6)
                check(view && view.itemAtIndex(5) && Math.abs(view.itemAtIndex(5).height - 24) < 0.5,
                      "sixth task must be instantiated by scrolling and retain a 24 px row")
                check(!!titleItem("Task row 5"), "sixth task must remain reachable")
                complete()
            }
        """)

    def test_title_tooltips_keep_full_event_and_task_text(self) -> None:
        event_title = "Full event title " + "long text " * 16
        task_title = "Full task title " + "long text " * 16
        fixture = agenda([event(event_title, stamp(1), stamp(2))], [{"title": task_title}])
        self.simple_case(fixture, """
            let eventText = titleItem(fixture.events[0].summary)
            let taskText = titleItem(fixture.tasks[0].title)
            check(!!eventText && eventText.truncated && eventText.implicitWidth > eventText.width,
                  "event fixture must actually elide")
            check(!!taskText && taskText.truncated && taskText.implicitWidth > taskText.width,
                  "task fixture must actually elide")
            check(eventText && tooltip(eventText, fixture.events[0].summary),
                  "event title tooltip must retain the full unelided text")
            check(taskText && tooltip(taskText, fixture.tasks[0].title),
                  "task title tooltip must retain the full unelided text")
        """)

    def test_existing_reminder_baseline_with_fixture_home(self) -> None:
        # Run the snapshot reminder with synthetic data and the fixture Python;
        # HOME/GCAL_DIR/state are always disposable, including mktemp.
        (self.gcal / "gcal-remind.py").unlink()
        (self.gcal / "gcal-remind.py").symlink_to(CONFIG / "gcal/gcal-remind.py")
        self.assertEqual((self.gcal / "gcal-remind.py").resolve(strict=True),
                         CONFIG / "gcal/gcal-remind.py")
        self.assertEqual((self.gcal / ".venv/bin/python").resolve(strict=True),
                         Path(sys.executable).resolve(strict=True))
        fixture = agenda([event("Fixture smoke meeting", stamp(5 / 60), stamp(1))],
                         [{"title": "Fixture smoke task", "due": dt.date.today().isoformat(),
                           "list": "Fixture tasks"}])
        (self.gcal / "cache.json").write_text(json.dumps(fixture), encoding="utf-8")
        self.env["TMPDIR"] = str(self.home)
        result = subprocess.run(["bash", str(CONFIG / "gcal/tests/gcal_remind.sh")],
                                env=self.env, cwd=self.home, capture_output=True,
                                text=True, timeout=PROCESS_TIMEOUT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS: reminders fire once", result.stdout)
        self.assertTrue((self.gcal / "notified.json").exists(),
                        "synthetic-cache smoke must create only fixture reminder state")


if __name__ == "__main__":
    unittest.main(verbosity=2)
