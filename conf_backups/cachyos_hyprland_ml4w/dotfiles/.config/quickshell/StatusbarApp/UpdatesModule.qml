import Quickshell
import Quickshell.Io
import QtQuick
import QtQuick.Effects
import QtQuick.Layouts
import qs.CustomTheme

// Shows the number of pending updates next to a package icon. The count is
// read from Cachy Update's (arch-update) cached aggregate state, which lists
// one pending entry per line across system packages, the AUR and Flatpak. The
// module hides itself completely while nothing is cached; clicking it opens
// the interactive `arch-update` run in the configured ML4W terminal. Updates
// stay manual: nothing here checks for or installs packages.
Rectangle {
    id: updates

    // Number of available updates (0 = nothing pending, module hidden).
    property int count: 0
    // True when there is nothing to show. The right Repeater reads this to
    // collapse the layout slot, and rebuildNavItems skips collapsed modules.
    // It is deliberately independent of the (effective) `visible` property:
    // binding a Loader's visibility to a child's effective visibility latches
    // off once the right area collapses while the pill is in collapsed mode.
    readonly property bool collapsed: count <= 0
    // Set by the keyboard navigation in StatusbarWindow.
    property bool focused: false

    // XDG state dir, falling back to ~/.local/state when unset or empty.
    // Quickshell.env() yields null (not "") for an unset variable.
    readonly property string stateHome: Quickshell.env("XDG_STATE_HOME")
        || (Quickshell.env("HOME") + "/.local/state")
    // arch-update writes one line per pending update here; absent = nothing.
    readonly property string cachePath: stateHome + "/arch-update/last_updates_check"

    // Configured ML4W terminal (settings/terminal.sh); kitty when unset.
    property string terminal: "kitty"

    // Open the interactive Cachy Update run in the configured terminal, keeping
    // the ML4W floating window class. Never --check or an unattended update.
    function activate(): void {
        Quickshell.execDetached(["bash", "-c",
            updates.terminal + " --class dotfiles-floating -e arch-update"])
    }

    // Hidden (and collapsed to zero size) when there is nothing to update.
    visible: !collapsed

    readonly property bool active: mouseArea.containsMouse || updates.focused

    // Tight 3px padding each side so the module sits close to its neighbours.
    implicitWidth: collapsed ? 0 : row.implicitWidth + 6
    implicitHeight: 30
    radius: 15

    // Same accent-filled highlight as BarButton on hover/selection.
    color: active ? Theme.primary : "transparent"

    // Fade the accent circle in/out like BarButton does.
    Behavior on color {
        ColorAnimation { duration: 500; easing.type: Easing.OutQuint }
    }

    RowLayout {
        id: row
        anchors.centerIn: parent
        spacing: 4

        Image {
            Layout.alignment: Qt.AlignVCenter
            source: "../shared/icons/package.svg"
            sourceSize.width: 18
            sourceSize.height: 18
            width: 18
            height: 18
            fillMode: Image.PreserveAspectFit
            layer.enabled: true
            layer.effect: MultiEffect {
                colorization: 1.0
                colorizationColor: updates.active ? Theme.background : Theme.primary
                Behavior on colorizationColor {
                    ColorAnimation { duration: 500; easing.type: Easing.OutQuint }
                }
            }
        }

        Text {
            Layout.alignment: Qt.AlignVCenter
            text: updates.count
            color: updates.active ? Theme.background : Theme.primary
            font.family: Theme.fontFamily
            font.pixelSize: 14
            font.bold: true
            Behavior on color {
                ColorAnimation { duration: 500; easing.type: Easing.OutQuint }
            }
        }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: updates.activate()
    }

    // Count nonblank lines in a cached aggregate (system + AUR + Flatpak);
    // blank separator lines are not updates.
    function countCache(source): int {
        const raw = source || ""
        let total = 0
        for (const line of raw.split("\n"))
            if (line.trim() !== "")
                total++
        return total
    }

    // Re-read the cached aggregate on demand: the 1800s fallback timer and the
    // `updates refresh` IPC call. This never runs a check or install command.
    function refresh(): void {
        cacheView.reload()
    }

    // Cachy Update owns this file; FileView only watches it, so live writes,
    // atomic replacements and the updater clearing it all refresh the count.
    FileView {
        id: cacheView
        path: updates.cachePath
        blockLoading: true
        printErrors: false
        watchChanges: true
        onLoaded: updates.count = updates.countCache(text())
        onLoadFailed: updates.count = 0
        onFileChanged: cacheView.reload()
    }

    // Follow the configured ML4W terminal so the click keeps the user's choice.
    FileView {
        id: terminalFile
        path: Quickshell.env("HOME") + "/.config/ml4w/settings/terminal.sh"
        blockLoading: true
        printErrors: false
        watchChanges: true
        onLoaded: {
            const value = text().trim()
            if (value !== "")
                updates.terminal = value
        }
        onFileChanged: terminalFile.reload()
    }

    // Keep the existing 1800s cadence, but only re-read the cache the updater
    // already wrote; Cachy's own timer is what performs real checks.
    Timer {
        interval: 1800 * 1000
        running: true
        repeat: true
        onTriggered: updates.refresh()
    }

    // Let external scripts drive the module via `qs ipc call updates ...`.
    // `reset` clears the count immediately (e.g. right after an update run,
    // so the module hides itself without waiting for the next poll); `refresh`
    // re-reads the cached aggregate on demand.
    IpcHandler {
        target: "updates"
        function reset(): void { updates.count = 0 }
        function refresh(): void { updates.refresh() }
    }
}
