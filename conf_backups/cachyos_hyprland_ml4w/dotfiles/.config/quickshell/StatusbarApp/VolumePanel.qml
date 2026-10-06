import Quickshell
import Quickshell.Services.Pipewire
import QtQuick
import QtQuick.Layouts
import QtQuick.Effects
import QtQuick.Controls
import qs.CustomTheme

// Volume dropdown: output list on top, master slider under it + expandable per-app volumes.
// Positioned by the parent under the volume pill (see StatusbarWindow,
// SlimBarWindow). Fades in place, never slides (cf. MediaPanel).
Item {
    id: panel

    property bool isOpen: false
    property real openY: 0
    // The placed volume module, set by the window. Hover pins through it.
    property var volumeModule: null
    // Collapsed by default; the small arrow beside the master slider toggles it.
    property bool showApps: false

    readonly property PwNode sink: Pipewire.defaultAudioSink
    readonly property bool ready: sink !== null && sink.ready && sink.audio !== null
    readonly property real level: ready ? sink.audio.volume : 0
    readonly property bool muted: ready ? sink.audio.muted : false
    readonly property int percent: muted ? 0 : Math.round(level * 100)

    PwObjectTracker { objects: sink !== null ? [sink] : [] }

    function setVolume(v: real): void {
        if (!ready)
            return
        sink.audio.muted = false
        sink.audio.volume = Math.max(0, Math.min(1, v))
    }

    function setAppVolume(node: var, v: real): void {
        if (node === null || node === undefined || node.audio === null || node.audio === undefined)
            return
        node.audio.muted = false
        node.audio.volume = Math.max(0, Math.min(1, v))
    }

    function toggleMute(): void {
        if (ready)
            sink.audio.muted = !sink.audio.muted
    }

    // Output sinks only (exclude sources and stream nodes). Recomputed when
    // the node list changes so plugged/unplugged devices appear live.
    readonly property var audioSinks: Pipewire.nodes.values.filter(n => n && n.isSink && !n.isStream)
    // Playback app streams only (programs outputting audio, not hardware).
    // Quickshell marks playback streams isSink=true + isStream=true (type 21).
    // Recomputed live so apps appear/disappear as they play.
    readonly property var appStreams: Pipewire.nodes !== null && Pipewire.nodes.values !== undefined ? Pipewire.nodes.values.filter(n => n && n.isStream && n.isSink && n.audio !== null && n.audio !== undefined) : []

    readonly property int cardInset: 20
    y: openY
    visible: isOpen
    opacity: isOpen ? 1 : 0
    Behavior on opacity {
        NumberAnimation { duration: 150; easing.type: Easing.OutQuint }
    }
    width: card.implicitWidth + 2 * cardInset
    implicitHeight: card.implicitHeight + 2 * cardInset
    readonly property bool showPanel: isOpen

    RectangularShadow {
        anchors.fill: card
        radius: card.radius
        blur: 15
        color: Qt.rgba(Theme.shadow.r, Theme.shadow.g, Theme.shadow.b, 0.4)
    }

    Rectangle {
        id: card
        x: panel.cardInset
        y: panel.cardInset
        implicitWidth: 320
        implicitHeight: list.implicitHeight + 20
        radius: 10
        color: Theme.background
        border.color: Theme.primary
        border.width: 2

        HoverHandler {
            id: cardHover
            onHoveredChanged: {
                if (!panel.volumeModule)
                    return
                if (cardHover.hovered)
                    panel.volumeModule.cancelClose()
                else
                    panel.volumeModule.scheduleClose()
            }
        }

        ColumnLayout {
            id: list
            anchors.fill: parent
            anchors.margins: 10
            spacing: 8

            Text {
                Layout.fillWidth: true
                text: "Output devices"
                color: Theme.primary
                font.family: Theme.fontFamily
                font.pixelSize: 13
                font.bold: true
            }

            Repeater {
                model: panel.audioSinks
                delegate: Rectangle {
                    id: row
                    required property var modelData
                    required property int index
                    Layout.fillWidth: true
                    implicitHeight: 36
                    radius: 8
                    readonly property bool isActive: panel.sink !== null && modelData !== null && panel.sink === modelData
                    color: isActive ? Theme.primary : "transparent"

                    readonly property string label: {
                        if (modelData === null)
                            return ""
                        return modelData.description || modelData.nickname || modelData.name || "Unknown"
                    }

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8
                        spacing: 8
                        Text {
                            text: row.isActive ? "●" : "○"
                            color: row.isActive ? Theme.background : Theme.primary
                            font.pixelSize: 12
                        }
                        Text {
                            Layout.fillWidth: true
                            text: row.label
                            elide: Text.ElideRight
                            color: row.isActive ? Theme.background : Theme.primary
                            font.family: Theme.fontFamily
                            font.pixelSize: 13
                            font.bold: row.isActive
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (row.modelData !== null)
                                Pipewire.preferredDefaultAudioSink = row.modelData
                        }
                    }
                }
            }

            Text {
                Layout.fillWidth: true
                visible: panel.audioSinks.length === 0
                horizontalAlignment: Text.AlignHCenter
                text: "No outputs"
                color: Theme.on_background
                font.family: Theme.fontFamily
                font.pixelSize: 12
            }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: 1
                color: Theme.primary
                opacity: 0.4
            }

            Text {
                Layout.fillWidth: true
                text: panel.muted ? "Volume  ·  muted" : "Volume  ·  " + panel.percent + "%"
                color: Theme.primary
                font.family: Theme.fontFamily
                font.pixelSize: 14
                font.bold: true
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                Slider {
                    id: volSlider
                    Layout.fillWidth: true
                    from: 0
                    to: 1
                    stepSize: 0.01
                    value: panel.level
                    onMoved: panel.setVolume(value)

                    background: Rectangle {
                        x: volSlider.leftPadding
                        y: volSlider.topPadding + volSlider.availableHeight / 2 - height / 2
                        implicitWidth: 200
                        implicitHeight: 8
                        width: volSlider.availableWidth
                        height: implicitHeight
                        radius: 4
                        color: Theme.surface_container_high
                        border.color: Theme.primary
                        border.width: 1
                        Rectangle {
                            width: volSlider.visualPosition * parent.width
                            height: parent.height
                            radius: 4
                            color: panel.muted ? Theme.outline : Theme.primary
                        }
                    }
                    handle: Rectangle {
                        x: volSlider.leftPadding + volSlider.visualPosition
                            * (volSlider.availableWidth - width)
                        y: volSlider.topPadding + volSlider.availableHeight / 2 - height / 2
                        implicitWidth: 18
                        implicitHeight: 18
                        radius: 9
                        color: volSlider.pressed ? Theme.on_primary
                            : (volSlider.hovered ? Theme.primary_fixed : Theme.primary)
                        border.color: Theme.primary
                        border.width: 2
                    }
                }
                Rectangle {
                    Layout.alignment: Qt.AlignVCenter
                    implicitWidth: muteLabel.implicitWidth + 16
                    implicitHeight: 28
                    radius: 14
                    color: muteHover.containsMouse ? Theme.primary : "transparent"
                    border.color: Theme.primary
                    border.width: 1
                    Text {
                        id: muteLabel
                        anchors.centerIn: parent
                        text: panel.muted ? "unmute" : "mute"
                        color: muteHover.containsMouse ? Theme.background : Theme.primary
                        font.family: Theme.fontFamily
                        font.pixelSize: 12
                        font.bold: true
                    }
                    MouseArea {
                        id: muteHover
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: panel.toggleMute()
                    }
                }
                Rectangle {
                    Layout.alignment: Qt.AlignVCenter
                    implicitWidth: 28
                    implicitHeight: 28
                    radius: 14
                    color: expandHover.containsMouse ? Theme.primary : "transparent"
                    border.color: Theme.primary
                    border.width: 1
                    Text {
                        anchors.centerIn: parent
                        text: panel.showApps ? "▲" : "▼"
                        color: expandHover.containsMouse ? Theme.background : Theme.primary
                        font.pixelSize: 12
                        font.bold: true
                    }
                    MouseArea {
                        id: expandHover
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: panel.showApps = !panel.showApps
                    }
                }
            }

            Text {
                Layout.fillWidth: true
                visible: panel.showApps
                text: "Apps  ·  " + panel.appStreams.length
                color: Theme.primary
                font.family: Theme.fontFamily
                font.pixelSize: 13
                font.bold: true
            }

            Repeater {
                model: panel.appStreams
                delegate: RowLayout {
                    required property var modelData
                    required property int index
                    Layout.fillWidth: true
                    visible: panel.showApps
                    spacing: 8
                    // Keep this stream's audio + properties (application.name) live.
                    PwObjectTracker { objects: modelData !== null ? [modelData] : [] }
                    readonly property bool appReady: modelData !== null && modelData.ready && modelData.audio !== null
                    readonly property string appLabel: {
                        if (modelData === null)
                            return "Unknown"
                        var viaProps = ""
                        if (modelData.properties !== undefined && modelData.properties !== null)
                            viaProps = modelData.properties["application.name"] || ""
                        return viaProps || modelData.description || modelData.nickname || modelData.name || "Unknown"
                    }
                    readonly property real appLevel: appReady ? modelData.audio.volume : 0
                    readonly property bool appMuted: appReady ? modelData.audio.muted : false
                    Text {
                        Layout.preferredWidth: 110
                        Layout.alignment: Qt.AlignVCenter
                        text: appLabel
                        elide: Text.ElideRight
                        color: Theme.primary
                        font.family: Theme.fontFamily
                        font.pixelSize: 12
                    }
                    Slider {
                        id: appSlider
                        Layout.fillWidth: true
                        from: 0
                        to: 1
                        stepSize: 0.01
                        value: appLevel
                        enabled: appReady
                        onMoved: panel.setAppVolume(modelData, value)
                        background: Rectangle {
                            x: appSlider.leftPadding
                            y: appSlider.topPadding + appSlider.availableHeight / 2 - height / 2
                            implicitWidth: 200
                            implicitHeight: 8
                            width: appSlider.availableWidth
                            height: implicitHeight
                            radius: 4
                            color: Theme.surface_container_high
                            border.color: Theme.primary
                            border.width: 1
                            Rectangle {
                                width: appSlider.visualPosition * parent.width
                                height: parent.height
                                radius: 4
                                color: appMuted ? Theme.outline : Theme.primary
                            }
                        }
                        handle: Rectangle {
                            x: appSlider.leftPadding + appSlider.visualPosition
                                * (appSlider.availableWidth - width)
                            y: appSlider.topPadding + appSlider.availableHeight / 2 - height / 2
                            implicitWidth: 14
                            implicitHeight: 14
                            radius: 7
                            color: appSlider.pressed ? Theme.on_primary
                                : (appSlider.hovered ? Theme.primary_fixed : Theme.primary)
                            border.color: Theme.primary
                            border.width: 2
                        }
                    }
                    Text {
                        Layout.preferredWidth: 38
                        Layout.alignment: Qt.AlignVCenter
                        horizontalAlignment: Text.AlignRight
                        text: appMuted ? "0%" : Math.round(appLevel * 100) + "%"
                        color: Theme.primary
                        font.family: Theme.fontFamily
                        font.pixelSize: 12
                    }
                }
            }

            Text {
                Layout.fillWidth: true
                visible: panel.showApps && panel.appStreams.length === 0
                horizontalAlignment: Text.AlignHCenter
                text: "No apps playing"
                color: Theme.on_background
                font.family: Theme.fontFamily
                font.pixelSize: 12
            }
        }
    }
}
