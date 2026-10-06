import Quickshell
import QtQuick
import qs.CustomTheme

// Windows-style Show Desktop strip: thin rectangle at the far-right edge.
// Click toggles minimize-all/restore-all, press-and-hold peeks (hides).
Rectangle {
    id: showDesktop
    // Set by StatusbarWindow keyboard navigation.
    property bool focused: false
    property bool collapsed: false

    function activate(): void { showDesktop.toggle() }
    function toggle(): void {
        Quickshell.execDetached([Quickshell.env("HOME") + "/.local/bin/glaze-show-desktop", "toggle"])
    }
    function peek(): void {
        Quickshell.execDetached([Quickshell.env("HOME") + "/.local/bin/glaze-show-desktop", "hide"])
    }

    implicitWidth: 8
    implicitHeight: 30
    width: 8
    height: 30
    radius: 2
    color: (mouseArea.containsMouse || showDesktop.focused) ? Theme.primary : Theme.surface_container_high
    opacity: mouseArea.containsMouse ? 1.0 : 0.6

    Behavior on color {
        ColorAnimation { duration: 250; easing.type: Easing.OutQuint }
    }
    Behavior on opacity {
        NumberAnimation { duration: 250; easing.type: Easing.OutQuint }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        // Hold to peek at the desktop (hide without toggling state tracking).
        onPressAndHold: showDesktop.peek()
        onClicked: showDesktop.toggle()
    }
}
