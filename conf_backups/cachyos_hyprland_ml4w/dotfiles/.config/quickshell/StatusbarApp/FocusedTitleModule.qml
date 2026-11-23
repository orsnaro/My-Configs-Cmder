import QtQuick
import Quickshell.Wayland
import qs.CustomTheme

// Window change signals update this display; no polling or subprocesses.
Item {
    id: root
    property var toplevel: ToplevelManager.activeToplevel
    property real availableWidth: 220
    readonly property string displayTitle: toplevel ? (toplevel.title || "") : ""
    readonly property bool collapsed: displayTitle.length === 0 || implicitWidth <= 0
    implicitWidth: displayTitle.length ? Math.max(0, Math.min(220, availableWidth, label.implicitWidth)) : 0
    implicitHeight: 30

    Text {
        id: label
        anchors.fill: parent
        text: root.displayTitle
        textFormat: Text.PlainText
        elide: Text.ElideRight
        verticalAlignment: Text.AlignVCenter
        color: Theme.primary
        font.family: Theme.fontFamily
        font.pixelSize: 12
    }
}
