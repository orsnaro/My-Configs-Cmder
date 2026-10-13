//@ pragma UseQApplication
import Quickshell
import Quickshell.Io
import QtQuick
import QtTest
import qs.DockApp

// Run with dock_reorder.py, never with the user's real HOME. QtTest's normal
// logger is not initialized by qs, so export its actual counts explicitly.
ShellRoot {
    id: harness
    readonly property string artifacts: Quickshell.env("DOCK_REORDER_ARTIFACTS")
    readonly property bool restarting: Quickshell.env("DOCK_REORDER_PHASE") === "restart"
    property var dock: null
    property var heldPoint: null
    property int heldButton: Qt.NoButton

    FileView { id: fixtureFile; path: harness.artifacts + "/fixture.json"; blockLoading: true }
    FileView {
        id: configFile
        path: Quickshell.env("HOME") + "/.config/ml4w-dock/config.json"
        blockLoading: true
        blockAllReads: true
        blockWrites: true
    }
    FileView {
        id: activationFile
        path: harness.artifacts + "/activations.log"
        blockLoading: true
        blockAllReads: true
    }
    FileView { id: savesFile; path: harness.artifacts + "/writes.txt"; blockAllReads: true }
    FileView {
        id: resultFile
        path: harness.artifacts + (harness.restarting ? "/restart-result.json" : "/gestures-result.json")
        blockWrites: true
        printErrors: false
    }
    Component { id: dockComponent; DockWindow {} }
    Component { id: itemComponent; DockItem {} }
    SignalSpy { id: settingsReloadSpy; target: DockSettings; signalName: "settingsChanged" }

    TestCase {
        id: tests
        name: "PinnedReorder"
        when: !harness.restarting && harness.artifacts !== "" && DockSettings.ready
        optional: harness.restarting
        windowShown: true
        property var baseFixture: null
        property int activationBaseline: 0
        property int saveBaseline: 0

        function check(condition, message) {
            if (!condition)
                console.log("REORDER_ASSERT", qtest_results.functionName, message)
            verify(condition, message)
        }
        function equal(actual, expected, message) {
            if (JSON.stringify(actual) !== JSON.stringify(expected))
                console.log("REORDER_ASSERT", qtest_results.functionName, message,
                            "actual=" + JSON.stringify(actual), "expected=" + JSON.stringify(expected))
            compare(actual, expected, message)
        }
        function eventually(predicate, message) {
            let deadline = Date.now() + 3000
            while (!predicate() && Date.now() < deadline)
                wait(25)
            check(predicate(), message)
        }
        function disk() {
            configFile.reload()
            return JSON.parse(configFile.text())
        }
        function saves() {
            savesFile.reload()
            return Number(savesFile.text().trim())
        }
        function activations() {
            activationFile.reload()
            let text = activationFile.text().trim()
            return text === "" ? 0 : text.split("\n").length
        }
        function walk(item, result) {
            if (item.entry !== undefined && item.dockWindow === harness.dock)
                result.push(item)
            for (let child of item.children || [])
                walk(child, result)
        }
        function items() {
            let result = []
            walk(harness.dock.contentItem, result)
            return result.sort((a, b) => a.mapToItem(harness.dock.contentItem, 0, 0).x
                                      - b.mapToItem(harness.dock.contentItem, 0, 0).x)
        }
        function item(key) {
            let found = items().filter(candidate => candidate.entry.key === key)
            check(found.length === 1, "exactly one real delegate for " + key)
            return found[0]
        }
        function point(candidate) {
            return candidate.mapToItem(harness.dock.contentItem, candidate.width / 2, candidate.height / 2)
        }
        function press(candidate, button) {
            let p = point(candidate)
            harness.heldPoint = p
            harness.heldButton = button === undefined ? Qt.LeftButton : button
            mouseMove(harness.dock.contentItem, p.x, p.y)
            mousePress(harness.dock.contentItem, p.x, p.y, harness.heldButton)
        }
        function hold(candidate) {
            press(candidate)
            wait(200)
            check(harness.dock.draggingPinned === false, "hold must not arm before 250ms")
            wait(100)
            check(harness.dock.draggingPinned === true, "250ms hold must arm a drag by 300ms")
            equal(harness.dock.pinnedDragKey, candidate.entry.key, "source key belongs to held delegate")
        }
        function move(p) {
            harness.heldPoint = p
            mouseMove(harness.dock.contentItem, p.x, p.y, 20, harness.heldButton)
            wait(25)
        }
        function release(p) {
            p = p || harness.heldPoint
            mouseRelease(harness.dock.contentItem, p.x, p.y, harness.heldButton)
            harness.heldButton = Qt.NoButton
            harness.heldPoint = null
            wait(150)
        }
        function unchanged(message) {
            equal(disk(), baseFixture, message + ": persisted JSON unchanged")
            equal(saves(), saveBaseline, message + ": no save")
            equal(activations(), activationBaseline, message + ": no activation")
        }
        function cleared() {
            check(harness.dock.draggingPinned === false, "drag state clears")
            equal(harness.dock.pinnedDragKey, "", "source key clears")
            equal(harness.dock.pinnedDropKey, "", "target key clears")
        }
        function installFixture(pins) {
            let fixture = JSON.parse(fixtureFile.text())
            if (pins)
                fixture.apps.pinned = pins
            configFile.reload()
            configFile.text() // Synchronize this view before replacing another writer's data.
            configFile.setText(JSON.stringify(fixture) + "\n")
            wait(100)
            settingsReloadSpy.clear()
            DockSettings.reloadSettings()
            // reloadSettings applies immediately, then again after async I/O;
            // both must finish before a test creates/presses a delegate.
            eventually(() => settingsReloadSpy.count >= 2
                             && JSON.stringify(DockSettings.settings.apps.pinned)
                              === JSON.stringify(fixture.apps.pinned), "isolated fixture loaded")
            baseFixture = fixture
            check(settingsReloadSpy.count >= 2, "fixture reload must finish before creating pointer-owning delegates")
        }
        function initTestCase() {
            check(harness.artifacts.indexOf("/tmp/opencode/dock-reorder-") === 0,
                  "runner must supply an isolated test home")
            eventually(() => DesktopEntries.heuristicLookup("dock-reorder-a") !== null,
                       "safe fixture desktop entries indexed before any mouse press")
        }
        function init() {
            console.log("REORDER_CASE", qtest_results.functionName)
            if (!harness.restarting)
                installFixture()
            harness.dock = dockComponent.createObject(harness)
            check(harness.dock !== null, "production DockWindow created")
            eventually(() => harness.dock.width > 0 && items().filter(candidate => candidate.pinned).length === 4,
                       "production pinned delegates laid out")
            wait(100)
            for (let letter of ["a", "b", "c", "d"])
                check(item("dock-reorder-" + letter).desktopEntry !== null,
                      "clicks may target only safe real fixture desktop entries")
            activationBaseline = activations()
            saveBaseline = saves()
        }
        function cleanup() {
            if (!harness.dock)
                return
            if (harness.heldButton !== Qt.NoButton)
                release()
            harness.dock.closeMenu()
            harness.dock.closePreviews()
            harness.dock.destroy()
            harness.dock = null
            wait(50)
        }
        onCompletedChanged: {
            if (completed)
                resultFile.setText(JSON.stringify({passed: qtest_results.passCount,
                                                  failed: qtest_results.failCount,
                                                  skipped: qtest_results.skipCount}) + "\n")
        }

        // Wrong insertion direction, premature mutation, repeated writes, and
        // release activation are observable through JSON/native save telemetry.
        function test_bidirectionalMultiSlot_data() {
            return [
                {tag: "right", source: "a", target: "d", expected: ["dock-reorder-b", "dock-reorder-c", "dock-reorder-d", "dock-reorder-a"]},
                {tag: "left", source: "d", target: "a", expected: ["dock-reorder-d", "dock-reorder-a", "dock-reorder-b", "dock-reorder-c"]}
            ]
        }
        function test_bidirectionalMultiSlot(data) {
            if (harness.restarting) return
            let source = item("dock-reorder-" + data.source)
            let target = item("dock-reorder-" + data.target)
            let positions = items().filter(candidate => candidate.pinned).map(candidate => point(candidate).x)
            hold(source)
            equal(harness.dock.pinnedDragSnapshot, baseFixture.apps.pinned, "drag snapshots stored IDs")
            move(point(target))
            equal(harness.dock.pinnedDropKey, target.entry.key, "target follows a multi-slot move")
            unchanged("pointer movement before release")
            equal(items().filter(candidate => candidate.pinned).map(candidate => point(candidate).x), positions,
                  "delegates stay stationary throughout the gesture")
            let images = source.children.filter(child => child.source !== undefined
                && String(child.source) === source.iconSource)
            check(images.length === 1, "source uses one existing icon image")
            check(images[0].x > source.width || images[0].x < -images[0].width,
                  "the icon visibly follows a multi-slot drag while its delegate stays still")
            release()
            eventually(() => JSON.stringify(disk().apps.pinned) === JSON.stringify(data.expected),
                       "valid release persists the new order")
            let expected = JSON.parse(JSON.stringify(baseFixture))
            expected.apps.pinned = data.expected
            equal(disk(), expected, "only pin order changes; all other settings preserved")
            equal(saves(), saveBaseline + 1, "one changed drop produces exactly one save")
            equal(activations(), activationBaseline, "reorder release must not activate or launch")
            cleared()
        }
        function test_invalidDrops_data() {
            return [{tag: "above", location: "above"}, {tag: "below", location: "below"},
                    {tag: "launcher", location: "launcher"}, {tag: "running", location: "running"},
                    {tag: "same", location: "same"}]
        }
        function test_invalidDrops(data) {
            if (harness.restarting) return
            let source = item("dock-reorder-a")
            let target = item("dock-reorder-c")
            let p = point(target)
            let top = target.mapToItem(harness.dock.contentItem, 0, 0).y
            if (data.location === "above") p.y = top - 20
            if (data.location === "below") p.y = top + target.height + 10
            if (data.location === "launcher") p.x = point(source).x - source.width - 15
            if (data.location === "running") {
                let running = items().filter(candidate => !candidate.pinned)
                check(running.length > 0, "Wayland session supplies a real running-only drop target")
                p = point(running[0]) // Only hover/drop here; never click the user's running apps.
            }
            if (data.location === "same") p = point(source)
            hold(source)
            if (data.location !== "same") move(p)
            release(p)
            unchanged("invalid/no-motion drop " + data.location)
            cleared()
        }
        function test_cancelSuppressesRelease() {
            if (harness.restarting) return
            hold(item("dock-reorder-a"))
            harness.dock.cancelPinnedDrag()
            release()
            unchanged("explicit cancellation")
            cleared()
        }
        function test_modelReplacementCancels() {
            if (harness.restarting) return
            hold(item("dock-reorder-a"))
            move(point(item("dock-reorder-d")))
            let replacement = JSON.parse(JSON.stringify(baseFixture))
            replacement.apps.pinned = ["dock-reorder-d", "dock-reorder-c", "dock-reorder-b", "dock-reorder-a"]
            configFile.setText(JSON.stringify(replacement) + "\n")
            wait(100)
            DockSettings.reloadSettings()
            wait(100)
            let externalSaves = saves()
            release()
            equal(disk(), replacement, "model replacement wins over stale drag snapshot")
            equal(saves(), externalSaves, "canceled stale gesture must not write")
            equal(activations(), activationBaseline, "model replacement release must not activate")
            cleared()
        }
        function test_windowHiddenCancels() {
            if (harness.restarting) return
            hold(item("dock-reorder-a"))
            harness.dock.visible = false
            wait(50)
            cleared()
            harness.dock.visible = true
            wait(50)
            release()
            unchanged("hidden window cancellation")
        }
        function test_onlyPinnedLeftHold_data() {
            return [{tag: "right", button: Qt.RightButton}, {tag: "middle", button: Qt.MiddleButton},
                    {tag: "unpinned", button: Qt.LeftButton, unpinned: true}]
        }
        function test_onlyPinnedLeftHold(data) {
            if (harness.restarting) return
            let candidate = item("dock-reorder-a")
            let temporary = null
            if (data.unpinned) {
                let entry = Object.assign({}, candidate.entry, {pinned: false, key: "test-unpinned"})
                temporary = itemComponent.createObject(harness.dock.contentItem,
                    {entry: entry, dockWindow: harness.dock, x: 20, y: 20, width: 48, height: 50})
                candidate = temporary // Same production DockItem handlers; safe desktop entry.
            }
            press(candidate, data.button)
            wait(850)
            let armed = harness.dock.draggingPinned === true
            release()
            if (temporary) temporary.destroy()
            check(!armed, "only a pinned LEFT hold may arm")
            equal(saves(), saveBaseline, "non-reorder buttons/entries do not save")
            if (data.button === Qt.RightButton)
                check(harness.dock.menuOpen, "held right click still opens the context menu")
            else
                eventually(() => activations() === activationBaseline + 1,
                           "held middle/unpinned clicks retain their original launch behavior: " + data.tag)
        }
        function test_ordinaryButtons() {
            if (harness.restarting) return
            let p = point(item("dock-reorder-a"))
            mouseClick(harness.dock.contentItem, p.x, p.y, Qt.LeftButton)
            eventually(() => activations() === activationBaseline + 1, "ordinary left click still launches")
            mouseClick(harness.dock.contentItem, p.x, p.y, Qt.MiddleButton)
            eventually(() => activations() === activationBaseline + 2, "ordinary middle click still launches a new instance")
            mouseClick(harness.dock.contentItem, p.x, p.y, Qt.RightButton)
            check(harness.dock.menuOpen, "ordinary right click opens the production menu")
            mouseClick(harness.dock.contentItem, p.x, p.y, Qt.RightButton)
            check(!harness.dock.menuOpen, "second right click closes menu")
            equal(activations(), activationBaseline + 2, "right clicks never launch")
            equal(saves(), saveBaseline, "ordinary clicks do not write pin order")
        }
        function tooltip(candidate) {
            let popups = Array.from(candidate.data).filter(node => node.anchor !== undefined && node.contentItem !== undefined)
            check(popups.length === 1, "production tooltip available through QObject data")
            return popups[0]
        }
        function test_hoverClosedDuringPressAndDrag() {
            if (harness.restarting) return
            let candidate = item("dock-reorder-a")
            let tip = tooltip(candidate)
            let p = point(candidate)
            mouseMove(harness.dock.contentItem, 1, 1)
            mouseMove(harness.dock.contentItem, p.x, p.y)
            eventually(() => tip.visible, "ordinary hover still opens real tooltip")
            // Use a real running entry: an empty popup has zero height and is
            // invalid on Wayland. Press immediately, before its capture timer.
            let running = items().filter(entry => entry.windows.length > 0)
            check(running.length > 0, "session supplies a real preview target")
            harness.dock.openPreviewsFor(running[0])
            press(candidate)
            wait(50)
            check(!tip.visible && harness.dock.previewItem === null, "pinned press immediately closes tooltip/previews")
            wait(800)
            check(!tip.visible && harness.dock.previewItem === null, "hover remains closed throughout the hold")
            move(point(item("dock-reorder-c")))
            wait(450)
            check(!tip.visible && harness.dock.previewItem === null, "drag movement never reopens hover UI")
            release()
        }
        function test_autohideStaysRevealedDuringDrag() {
            if (harness.restarting) return
            hold(item("dock-reorder-a"))
            harness.dock.autohide = true
            harness.dock.pointerHeld = false
            check(harness.dock.revealed, "autohide must keep the dock revealed during drag")
            harness.dock.autohide = false
            release()
            unchanged("autohide no-motion hold")
        }
        function test_duplicateAliasDoesNotShiftStoredIndex_data() {
            return [
                {tag: "unmoved-alias", pins: ["dock-reorder-a", "dock-reorder-alias-a", "dock-reorder-b", "dock-reorder-c", "dock-reorder-d"],
                 source: "c", target: "d", expected: ["dock-reorder-a", "dock-reorder-alias-a", "dock-reorder-b", "dock-reorder-d", "dock-reorder-c"]},
                {tag: "source-alias-right", pins: ["dock-reorder-a", "dock-reorder-alias-a", "dock-reorder-b", "dock-reorder-c", "dock-reorder-d"],
                 source: "a", target: "d", expected: ["dock-reorder-b", "dock-reorder-c", "dock-reorder-d", "dock-reorder-a", "dock-reorder-alias-a"]},
                {tag: "source-alias-left", pins: ["dock-reorder-a", "dock-reorder-b", "dock-reorder-c", "dock-reorder-d", "dock-reorder-alias-d"],
                 source: "d", target: "a", expected: ["dock-reorder-d", "dock-reorder-alias-d", "dock-reorder-a", "dock-reorder-b", "dock-reorder-c"]},
                {tag: "target-alias-right", pins: ["dock-reorder-a", "dock-reorder-b", "dock-reorder-c", "dock-reorder-d", "dock-reorder-alias-d"],
                 source: "b", target: "d", expected: ["dock-reorder-a", "dock-reorder-c", "dock-reorder-d", "dock-reorder-alias-d", "dock-reorder-b"]}
            ]
        }
        function test_duplicateAliasDoesNotShiftStoredIndex(data) {
            if (harness.restarting) return
            harness.dock.destroy()
            harness.dock = null
            installFixture(data.pins)
            harness.dock = dockComponent.createObject(harness)
            wait(150)
            equal(items().filter(candidate => candidate.pinned).length, 4, "alias duplicate collapses to one rendered delegate")
            saveBaseline = saves()
            hold(item("dock-reorder-" + data.source))
            move(point(item("dock-reorder-" + data.target)))
            release()
            equal(disk().apps.pinned, data.expected,
                  "move uses stored ID indexes, preserving duplicate aliases")
            equal(saves(), saveBaseline + 1, "alias-aware changed drop saves once")
            equal(activations(), activationBaseline, "alias-aware drag never launches")
        }
        function test_z_persistenceAcrossFreshProcess() {
            let expected = ["dock-reorder-b", "dock-reorder-c", "dock-reorder-d", "dock-reorder-a"]
            hold(item("dock-reorder-a"))
            move(point(item("dock-reorder-d")))
            release()
            eventually(() => JSON.stringify(disk().apps.pinned) === JSON.stringify(expected),
                       "final fixture reorder persisted before quitting")
        }
    }

    TestCase {
        name: "PersistedOrder"
        when: harness.restarting && DockSettings.ready
        optional: !harness.restarting
        windowShown: true
        property int saveBaseline: 0
        property int activationBaseline: 0

        function initTestCase() {
            verify(harness.artifacts.indexOf("/tmp/opencode/dock-reorder-") === 0,
                   "restart must use an isolated test home")
            saveBaseline = tests.saves()
            activationBaseline = tests.activations()
        }
        function test_freshProcessReloadsOrder() {
            const expected = ["dock-reorder-b", "dock-reorder-c", "dock-reorder-d", "dock-reorder-a"]
            harness.dock = dockComponent.createObject(harness)
            verify(harness.dock !== null, "fresh process creates production dock")
            tryVerify(() => harness.dock.width > 0
                && tests.items().filter(candidate => candidate.pinned).length === 4)
            compare(harness.dock.pinnedApps, expected, "fresh process reloads persisted order")
            compare(tests.items().filter(candidate => candidate.pinned).map(candidate => candidate.entry.key),
                    expected, "fresh process renders persisted order")
            compare(tests.saves(), saveBaseline, "loading does not write settings")
            compare(tests.activations(), activationBaseline, "loading never launches apps")
            harness.dock.destroy()
            harness.dock = null
        }
        onCompletedChanged: {
            if (completed)
                resultFile.setText(JSON.stringify({passed: qtest_results.passCount,
                                                   failed: qtest_results.failCount,
                                                   skipped: qtest_results.skipCount}) + "\n")
        }
    }
}
