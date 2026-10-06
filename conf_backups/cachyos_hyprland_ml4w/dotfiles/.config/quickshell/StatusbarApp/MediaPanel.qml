import Quickshell
import Quickshell.Services.Mpris
import Quickshell.Services.Pipewire
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import QtQuick.Effects
import qs.CustomTheme

// Dropdown listing every Mpris player with per-row skip controls, plus
// minimal fallback cards for PipeWire-only streams (no track/skip API).
// Scrollable row area (Sidebar pattern): capped height, scrollbar as needed.
// Positioned by the parent under the media pill (see StatusbarWindow).
// place with a short fade: sliding through the pill would steal hover
// mid-transit and retrigger dwell/close in a loop.
Item {
    id: panel

    property bool isOpen: false
    property real openY: 0
    // The placed media module, set by the window. Row clicks pin through it.
    property var mediaModule: null

    readonly property int cardInset: 20
    y: openY
    visible: isOpen
    opacity: isOpen ? 1 : 0
    Behavior on opacity {
        NumberAnimation { duration: 150; easing.type: Easing.OutQuint }
    }
    width: card.implicitWidth + 2 * cardInset
    implicitHeight: card.implicitHeight + 2 * cardInset
    // Kept for the window's mapped-only-to-carry-a-panel gate.
    readonly property bool showPanel: isOpen

    // MPRIS players, de-duplicated: the playerctld proxy mirrors the active
    // player on its own bus name (same identity + track), which would list
    // every source twice. Same-track dupes from any other proxy collapse too;
    // distinct tracks always stay.
    readonly property var mprisPlayers: {
        let out = []
        let seen = ({})
        let all = Mpris.players.values
        for (let i = 0; i < all.length; i++) {
            let p = all[i]
            if (!p)
                continue
            if (p.dbusName !== undefined && ("" + p.dbusName).endsWith("playerctld"))
                continue
            let k = (p.identity || "") + " | " + (p.trackTitle || "") + " | " + (p.trackArtist || "")
            if (seen[k])
                continue
            seen[k] = true
            out.push(p)
        }
        return out
    }
    // PipeWire-only streams: one stream per matching MPRIS player is assumed
    // to back that player's row and is hidden; extra same-app streams (a 2nd
    // Brave tab) stay as fallback cards. Streams with no MPRIS match stay.
    readonly property var mprisNames: mprisPlayers.map(p => ((p.identity || "").toLowerCase()))
    function streamKey(n): string {
        if (n === null || n === undefined)
            return ""
        var viaProps = ""
        if (n.properties !== undefined && n.properties !== null)
            viaProps = n.properties["application.name"] || ""
        return ((viaProps || n.description || n.nickname || n.name || "").toLowerCase())
    }
    readonly property var appStreams: {
        let all = Pipewire.nodes !== null && Pipewire.nodes.values !== undefined ? Pipewire.nodes.values.filter(n => n && n.isStream && n.isSink && n.audio !== null && n.audio !== undefined) : []
        let dropped = ({})
        return all.filter(n => {
            let k = streamKey(n)
            let allow = 0
            for (let i = 0; i < mprisNames.length; i++)
                if (mprisNames[i] === k)
                    allow++
            let d = dropped[k] || 0
            if (d < allow) {
                dropped[k] = d + 1
                return false
            }
            return true
        })
    }

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
        implicitWidth: 360
        implicitHeight: list.implicitHeight + 20
        radius: 10
        color: Theme.background
        border.color: Theme.primary
        border.width: 2

        // Hovering the card cancels the pill's scheduled hide (crossing the
        // gap); leaving it re-arms the hide.
        HoverHandler {
            id: cardHover
            onHoveredChanged: {
                if (!panel.mediaModule)
                    return
                if (cardHover.hovered)
                    panel.mediaModule.cancelClose()
                else
                    panel.mediaModule.scheduleClose()
            }
        }

        ColumnLayout {
            id: list
            anchors.fill: parent
            anchors.margins: 10
            spacing: 6

            Repeater {
                model: panel.mprisPlayers
                delegate: Rectangle {
                    id: row
                    required property var modelData
                    required property int index
                    Layout.fillWidth: true
                    implicitHeight: 44
                    radius: 8
                    readonly property bool isPinned: panel.mediaModule
                        && panel.mediaModule.pinnedIndex === row.index
                    readonly property bool isAutoActive: panel.mediaModule
                        && !panel.mediaModule.pinnedValid
                        && panel.mediaModule.player === row.modelData
                    color: (isPinned || isAutoActive) ? Theme.primary : "transparent"

                    readonly property string title: row.modelData.trackTitle
                        || row.modelData.identity || "No Media"
                    readonly property string artist: row.modelData.trackArtist
                        || (row.modelData.trackArtists && row.modelData.trackArtists.length > 0
                            ? row.modelData.trackArtists[0] : "")

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8
                        spacing: 8

                        // Cover art thumbnail (Sidebar pattern, smaller).
                        // No artwork (e.g. plain audio files) falls back to a
                        // note glyph so the row keeps its shape. Cheap: one
                        // small cached image per row.
                        Rectangle {
                            Layout.alignment: Qt.AlignVCenter
                            implicitWidth: 32
                            implicitHeight: 32
                            radius: 6
                            color: "transparent"
                            border.color: row.color === Theme.primary
                                ? Theme.background : Theme.primary
                            border.width: 1
                            clip: true

                            Image {
                                anchors.fill: parent
                                source: row.modelData.trackArtUrl ? row.modelData.trackArtUrl : ""
                                fillMode: Image.PreserveAspectCrop
                                visible: row.modelData.trackArtUrl !== ""
                            }
                            Text {
                                anchors.centerIn: parent
                                text: "󰝚"
                                font.family: "monospace"
                                font.pixelSize: 16
                                color: row.color === Theme.primary ? Theme.background : Theme.primary
                                visible: !row.modelData.trackArtUrl || row.modelData.trackArtUrl === ""
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 0
                            Text {
                                Layout.fillWidth: true
                                text: row.title
                                elide: Text.ElideRight
                                color: row.color === Theme.primary ? Theme.background : Theme.primary
                                font.family: Theme.fontFamily
                                font.pixelSize: 14
                                font.bold: true
                            }
                            Text {
                                Layout.fillWidth: true
                                text: row.artist
                                elide: Text.ElideRight
                                visible: row.artist !== ""
                                color: row.color === Theme.primary ? Theme.background : Theme.on_background
                                font.family: Theme.fontFamily
                                font.pixelSize: 12
                            }
                        }

                        Text {
                            text: "󰒮"
                            color: row.color === Theme.primary ? Theme.background : Theme.primary
                            opacity: row.modelData.canGoPrevious ? 1 : 0.3
                            font.family: "monospace"
                            font.pixelSize: 18
                            MouseArea {
                                anchors.fill: parent
                                enabled: row.modelData.canGoPrevious
                                cursorShape: Qt.PointingHandCursor
                                onClicked: row.modelData.previous()
                            }
                        }
                        Text {
                            text: row.modelData.isPlaying ? "󰏤" : "󰐊"
                            color: row.color === Theme.primary ? Theme.background : Theme.primary
                            font.family: "monospace"
                            font.pixelSize: 20
                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: panel.mediaModule
                                    ? panel.mediaModule.togglePlayer(row.modelData)
                                    : row.modelData.togglePlaying()
                            }
                        }
                        Text {
                            text: "󰒭"
                            color: row.color === Theme.primary ? Theme.background : Theme.primary
                            opacity: row.modelData.canGoNext ? 1 : 0.3
                            font.family: "monospace"
                            font.pixelSize: 18
                            MouseArea {
                                anchors.fill: parent
                                enabled: row.modelData.canGoNext
                                cursorShape: Qt.PointingHandCursor
                                onClicked: row.modelData.next()
                            }
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        acceptedButtons: Qt.LeftButton
                        cursorShape: Qt.PointingHandCursor
                        // Let the control glyphs get the click first.
                        z: -1
                        onClicked: {
                            if (panel.mediaModule)
                                panel.mediaModule.selectPlayer(row.index)
                        }
                    }
                }
            }

            Text {
                Layout.fillWidth: true
                visible: panel.mprisPlayers.length === 0
                horizontalAlignment: Text.AlignHCenter
                text: "No players"
                color: Theme.on_background
                font.family: Theme.fontFamily
                font.pixelSize: 13
            }

            Text {
                Layout.fillWidth: true
                visible: panel.appStreams.length > 0
                text: "App audio  ·  " + panel.appStreams.length
                color: Theme.primary
                font.family: Theme.fontFamily
                font.pixelSize: 13
                font.bold: true
            }

            Flickable {
                Layout.fillWidth: true
                Layout.preferredHeight: Math.min(streamCol.implicitHeight, 140)
                visible: panel.appStreams.length > 0
                clip: true
                contentWidth: width
                contentHeight: streamCol.implicitHeight
                interactive: streamCol.implicitHeight > 140

                ColumnLayout {
                    id: streamCol
                    width: parent.width
                    spacing: 6

                    Repeater {
                        model: panel.appStreams
                        delegate: Rectangle {
                            id: row
                            required property var modelData
                            required property int index
                            Layout.fillWidth: true
                            implicitHeight: 44
                            radius: 8
                            readonly property bool isPinned: panel.mediaModule
                                && panel.mediaModule.pinnedIndex === panel.mprisPlayers.length + row.index
                            color: isPinned ? Theme.primary : "transparent"
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
                            readonly property bool appMuted: appReady ? modelData.audio.muted : false

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 8
                                anchors.rightMargin: 8
                                spacing: 8

                                Rectangle {
                                    Layout.alignment: Qt.AlignVCenter
                                    implicitWidth: 32
                                    implicitHeight: 32
                                    radius: 6
                                    color: "transparent"
                                    border.color: row.isPinned ? Theme.background : Theme.primary
                                    border.width: 1
                                    Text {
                                        anchors.centerIn: parent
                                        text: "󰝚"
                                        font.family: "monospace"
                                        font.pixelSize: 16
                                        color: row.isPinned ? Theme.background : Theme.primary
                                    }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 0
                                    Text {
                                        Layout.fillWidth: true
                                        text: appLabel
                                        elide: Text.ElideRight
                                        color: row.isPinned ? Theme.background : Theme.primary
                                        font.family: Theme.fontFamily
                                        font.pixelSize: 14
                                        font.bold: true
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        text: appMuted ? "muted" : "playing"
                                        elide: Text.ElideRight
                                        color: row.isPinned ? Theme.background : Theme.on_background
                                        font.family: Theme.fontFamily
                                        font.pixelSize: 12
                                        visible: appReady
                                    }
                                }

                                Text {
                                    text: appMuted ? "󰐊" : "󰏤"
                                    color: row.isPinned ? Theme.background : Theme.primary
                                    font.family: "monospace"
                                    font.pixelSize: 20
                                    opacity: appReady ? 1 : 0.3
                                    MouseArea {
                                        anchors.fill: parent
                                        enabled: appReady
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: {
                                            if (modelData !== null && modelData.audio !== null)
                                                modelData.audio.muted = !modelData.audio.muted
                                        }
                                    }
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                acceptedButtons: Qt.LeftButton
                                cursorShape: Qt.PointingHandCursor
                                z: -1
                                onClicked: {
                                    if (panel.mediaModule && typeof panel.mediaModule.selectStream === "function")
                                        panel.mediaModule.selectStream(row.index)
                                    else if (panel.mediaModule)
                                        panel.mediaModule.selectPlayer(panel.mprisPlayers.length + row.index)
                                }
                            }
                        }
                    }
                }

                ScrollBar.vertical: ScrollBar {
                    policy: streamCol.implicitHeight > 140 ? ScrollBar.AsNeeded : ScrollBar.AlwaysOff
                    interactive: true
                }
            }

            Text {
                Layout.fillWidth: true
                visible: panel.appStreams.length === 0
                horizontalAlignment: Text.AlignHCenter
                text: "No apps playing"
                color: Theme.on_background
                font.family: Theme.fontFamily
                font.pixelSize: 12
            }
        }
    }
}
