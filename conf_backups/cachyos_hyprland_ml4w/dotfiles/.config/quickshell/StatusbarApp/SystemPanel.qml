import Quickshell
import Quickshell.Io
import QtQuick
import QtQuick.Layouts
import QtQuick.Effects
import qs.CustomTheme
import "SystemMetricFormat.js" as Metrics

// Shared system metrics dropdown for the CPU/RAM pills. Appears in place
// with a short fade (never slides: transit steals hover and loops
// dwell/close, cf. MediaPanel).
Item {
    id: panel

    property bool isOpen: false
    property real openY: 0

    property int cpuPct: 0
    property real cpuGhz: 0
    property var cores: []
    property int memPct: 0
    property real memUsed: 0
    property real memTotal: 0
    property int swapPct: 0
    property string load: ""
    property string uptime: ""
    property var topProcs: []
    property var cpuTemp: null
    property var gpu: ({name: null, usage: null, temp: null,
        vram_used_gb: null, vram_total_gb: null})
    property var modA: null
    property var modB: null

    function cancelHides(): void {
        if (modA)
            modA.cancelClose()
        if (modB)
            modB.cancelClose()
    }
    function scheduleHides(): void {
        if (modA)
            modA.scheduleClose()
        if (modB)
            modB.scheduleClose()
    }

    readonly property int cardInset: 22
    y: openY
    visible: isOpen
    opacity: isOpen ? 1 : 0
    Behavior on opacity {
        NumberAnimation { duration: 150; easing.type: Easing.OutQuint }
    }
    width: card.implicitWidth + 2 * cardInset
    implicitHeight: card.implicitHeight + 2 * cardInset
    readonly property bool showPanel: isOpen

    function parseSys(src): void {
        try {
            let d = JSON.parse(src)
            panel.cpuPct = d.cpu_pct || 0
            panel.cpuGhz = d.cpu_ghz || 0
            panel.cores = d.cores || []
            panel.memPct = d.mem_pct || 0
            panel.memUsed = d.mem_used || 0
            panel.memTotal = d.mem_total || 0
            panel.swapPct = d.swap_pct || 0
            panel.load = d.load || ""
            panel.uptime = d.uptime || ""
            panel.topProcs = d.top || []
            panel.cpuTemp = d.cpu_temp === undefined ? null : d.cpu_temp
            panel.gpu = d.gpu || {name: null, usage: null, temp: null,
                vram_used_gb: null, vram_total_gb: null}
        } catch (e) {
            // Keep previous readings on malformed cache.
        }
    }

    component Bar: Rectangle {
        property real frac: 0
        Layout.fillWidth: true
        implicitHeight: 9
        radius: 4
        color: Theme.background
        border.color: Theme.primary
        border.width: 1
        Rectangle {
            width: parent.width * Math.max(0, Math.min(1, parent.frac))
            height: parent.height
            radius: 4
            color: Theme.primary
        }
    }

    component Head: Text {
        Layout.fillWidth: true
        color: Theme.primary
        font.family: Theme.fontFamily
        font.pixelSize: 16
        font.bold: true
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
        implicitWidth: 600
        implicitHeight: list.implicitHeight + 32
        radius: 10
        color: Theme.background
        border.color: Theme.primary
        border.width: 2

        HoverHandler {
            id: cardHover
            onHoveredChanged: {
                if (cardHover.hovered)
                    panel.cancelHides()
                else
                    panel.scheduleHides()
            }
        }

        ColumnLayout {
            id: list
            anchors.fill: parent
            anchors.margins: 16
            spacing: 10

            Head { text: "CPU  ·  " + panel.cpuPct + "%  ·  "
                + panel.cpuGhz.toFixed(1) + "GHz"
                + "  ·  " + (panel.cpuTemp !== null ? panel.cpuTemp + "°C" : "—") }
            Bar { frac: panel.cpuPct / 100 }

            GridLayout {
                Layout.fillWidth: true
                columns: 6
                rowSpacing: 3
                columnSpacing: 6
                Repeater {
                    model: panel.cores
                    Bar { frac: modelData / 100; implicitHeight: 6 }
                }
            }

            Text {
                Layout.fillWidth: true
                text: "load " + panel.load + "   ·   up " + panel.uptime
                color: Theme.on_background
                font.family: Theme.fontFamily
                font.pixelSize: 14
            }

            Head { text: "RAM  ·  " + Metrics.memory(panel.memUsed, panel.memTotal)
                + "  ·  swap " + panel.swapPct + "%" }
            Bar { frac: panel.memPct / 100 }

            Head {
                text: "GPU  ·  " + (panel.gpu.name || "unavailable")
                    + "  ·  " + (panel.gpu.usage !== null ? panel.gpu.usage + "%" : "—")
                    + "  ·  " + (panel.gpu.temp !== null ? panel.gpu.temp + "°C" : "—")
            }
            Bar { frac: (panel.gpu.usage || 0) / 100 }
            Text {
                Layout.fillWidth: true
                text: "VRAM  " + Metrics.memory(panel.gpu.vram_used_gb,
                    panel.gpu.vram_total_gb)
                color: Theme.on_background
                font.family: Theme.fontFamily
                font.pixelSize: 14
            }

            Head { text: "Top processes" }
            Repeater {
                model: panel.topProcs
                delegate: RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    Text {
                        Layout.fillWidth: true
                        text: modelData.name
                        color: Theme.primary
                        font.family: Theme.fontFamily
                        font.pixelSize: 14
                        elide: Text.ElideRight
                    }
                    Text {
                        text: modelData.cpu + "%"
                        color: Theme.on_background
                        font.family: Theme.fontFamily
                        font.pixelSize: 14
                    }
                }
            }
        }
    }

    FileView {
        id: cacheFile
        path: Quickshell.env("HOME") + "/.cache/sysinfo.json"
        blockLoading: true
        printErrors: false
        onLoaded: panel.parseSys(text())
    }
    Timer {
        interval: 3000
        repeat: true
        running: panel.isOpen
        triggeredOnStart: true
        onTriggered: cacheFile.reload()
    }
}
