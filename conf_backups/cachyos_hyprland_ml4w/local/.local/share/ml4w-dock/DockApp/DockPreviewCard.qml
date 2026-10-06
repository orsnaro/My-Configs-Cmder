import Quickshell
import Quickshell.Wayland
import QtQuick
import QtQuick.Layouts
import qs.DockApp

// One window card in the hover preview popup: live-ish thumbnail, app name,
// click focuses, × closes. The toplevel objects are the same ones
// DockItem.item.windows holds (.activate()/.close()).
// Ruling: Wayland toplevels expose no title, so the header shows the app
// name (+ index for multi-window apps).
Rectangle {
    id: card

    property var toplevel: null
    property string appName: ""
    property int windowIndex: 0
    property int windowCount: 1

    function capture(): void {
        if (card.toplevel)
            view.captureFrame()
    }

    implicitWidth: 280
    implicitHeight: 196
    radius: 10
    color: DockTheme.surface_container_high
    border.width: 1
    border.color: DockTheme.outline_variant

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 6

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 150
            clip: true

            ScreencopyView {
                id: view
                anchors.fill: parent
                captureSource: card.toplevel
                live: false
                constraintSize: Qt.size(280, 150)
            }
            Text {
                anchors.centerIn: parent
                visible: !view.hasContent
                text: card.appName
                color: DockTheme.on_surface
                font.family: DockTheme.fontFamily
                font.pixelSize: 14
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 6
            Text {
                Layout.fillWidth: true
                text: card.windowCount > 1
                    ? card.appName + " — " + (card.windowIndex + 1)
                    : card.appName
                color: DockTheme.on_surface
                font.family: DockTheme.fontFamily
                font.pixelSize: 13
                elide: Text.ElideRight
            }
            Text {
                text: "×"
                color: DockTheme.on_surface
                font.family: DockTheme.fontFamily
                font.pixelSize: 16
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (card.toplevel)
                            card.toplevel.close()
                    }
                }
            }
        }
    }

    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        // Below the × button so close wins its click.
        z: -1
        onClicked: {
            if (card.toplevel)
                card.toplevel.activate()
        }
    }
}
