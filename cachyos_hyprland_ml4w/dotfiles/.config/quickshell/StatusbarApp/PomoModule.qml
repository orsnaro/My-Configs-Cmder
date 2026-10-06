import Quickshell
import Quickshell.Io
import QtQuick
import qs.CustomTheme

// Pomo timer pill for the ml4w quickshell statusbar.
// Reads /tmp/pomo-status (written by `pomo`, see --status-file):
//   {"text": "🍅 24:59", "class": "focus", "tooltip": "Focus 1/4 — Set 1"}
// classes: focus (red) / break+long+done+idle (bar accent).
// Missing/unparseable file = idle.
// Left click (or keyboard): start one `pomo` headless in the background
// (the pill itself is the display). Right click: stop it.
Rectangle {
    id: pomo

    property string pomoText: "󰁫 idle"
    property string pomoClass: "idle"
    property string pomoTip: "Pomo idle (start `pomo` in a terminal)"
    property bool focused: false
    readonly property bool active: mouseArea.containsMouse || pomo.focused

    // Size overrides so slim side bars can run smaller. Defaults match
    // the center bar like the other modules.
    property int pillHeight: 30
    property int fontSize: 14

    implicitWidth: Math.max(36, label.implicitWidth + 12)
    implicitHeight: pomo.pillHeight
    radius: pomo.pillHeight / 2
    color: active ? Theme.primary : "transparent"
    Behavior on color { ColorAnimation { duration: 500; easing.type: Easing.OutQuint } }

    // Class -> color. Focus burns red; every other state (breaks, done,
    // idle) uses the wallpaper accent, matching the rest of the bar.
    function stateColor(): string {
        if (pomo.pomoClass === "focus")
            return Theme.error
        return Theme.primary
    }

    // Start one `pomo` headless in the background (default 25/5 timing,
    // default status file), but only when none is running.
    function activate(): void {
        Quickshell.execDetached(["bash", "-c",
            "pgrep -x pomo >/dev/null || exec \"$HOME\"/.local/bin/pomo"])
    }

    Text {
        id: label
        anchors.centerIn: parent
        text: pomo.pomoText
        color: pomo.active ? Theme.background : pomo.stateColor()
        font.family: Theme.fontFamily
        font.pixelSize: pomo.fontSize
        font.bold: true
        Behavior on color { ColorAnimation { duration: 500; easing.type: Easing.OutQuint } }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        cursorShape: Qt.PointingHandCursor
        onClicked: {
            if (mouse.button === Qt.RightButton)
                Quickshell.execDetached(["pkill", "-x", "pomo"])
            else
                pomo.activate()
        }
    }

    // Re-read the status file; FileView alone does not refire when
    // another process rewrites the file each second.
    FileView {
        id: statusFile
        path: "/tmp/pomo-status"
        blockLoading: true
        printErrors: false
        onLoaded: pomo.applyStatus(text())
        onLoadFailed: pomo.setIdle()
    }

    function setIdle(): void {
        pomo.pomoText = "󰁫 idle"
        pomo.pomoClass = "idle"
        pomo.pomoTip = "Pomo idle (start `pomo` in a terminal)"
    }

    function applyStatus(src): void {
        if (!src || src.trim() === "") {
            pomo.setIdle()
            return
        }
        try {
            const d = JSON.parse(src)
            pomo.pomoText = d.text || "󰁫 idle"
            pomo.pomoClass = d.cls || d.class || "idle"
            pomo.pomoTip = d.tooltip || ""
        } catch (e) {
            pomo.setIdle()
        }
    }

    Timer {
        interval: 1000
        running: true
        repeat: true
        onTriggered: statusFile.reload()
    }

    Component.onCompleted: statusFile.reload()
}
