import Quickshell
import Quickshell.Hyprland
import Quickshell.Io
import QtQuick
import qs.CustomTheme

// Show the main keyboard's layout and switch all keyboards when clicked.
Rectangle {
    id: indicator

    property string layoutLabel: "--"
    property bool focused: false
    readonly property bool active: mouseArea.containsMouse || focused

    // Size overrides so the slim side bars can run a touch smaller than the
    // center bar. Defaults preserve the center bar byte for byte.
    property int pillHeight: 30
    property int fontSize: 14

    function activate(): void {
        Quickshell.execDetached([Quickshell.env("HOME") + "/.local/bin/hypr-switch-xkblayout"])
    }

    implicitWidth: Math.max(36, label.implicitWidth + 12)
    implicitHeight: indicator.pillHeight
    radius: indicator.pillHeight / 2
    color: active ? Theme.primary : "transparent"
    Behavior on color { ColorAnimation { duration: 500; easing.type: Easing.OutQuint } }

    Text {
        id: label
        anchors.centerIn: parent
        text: indicator.layoutLabel
        color: indicator.active ? Theme.background : Theme.primary
        font.family: Theme.fontFamily
        font.pixelSize: indicator.fontSize
        font.bold: true
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: indicator.activate()
    }

    Process {
        id: layoutProc
        command: [Quickshell.env("HOME") + "/.local/bin/hypr-current-xkblayout"]
        running: true
        stdout: StdioCollector {
            onStreamFinished: indicator.layoutLabel = this.text.trim() || "--"
        }
    }

    // Hyprland emits this event for layout changes from the shortcut, the
    // indicator, or any other source. Query the main keyboard again so the
    // label always follows the actual layout, not a guessed toggle state.
    Connections {
        target: Hyprland
        function onRawEvent(event): void {
            if (event.name === "activelayout")
                layoutProc.exec(layoutProc.command)
        }
    }
}
