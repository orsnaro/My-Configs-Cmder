import Quickshell
import Quickshell.Io
import QtQuick
import QtQuick.Layouts
import qs.CustomTheme
import "SystemMetricFormat.js" as Metrics

// RAM pill: used GiB only (compact). Shares the system panel with the CPU
// pill (either opens it). Reads the same sysinfo cache; the CPU module owns
// the fetch process, this one just re-reads the file on the same cadence.
Rectangle {
    id: mem

    signal sysToggleRequested
    signal sysOpenRequested
    signal sysCloseRequested

    property int pct: 0
    property real used: 0
    property real total: 0
    property bool focused: false
    readonly property bool active: mouseArea.containsMouse || mem.focused
    readonly property bool collapsed: false

    function parseSys(src): void {
        try {
            let d = JSON.parse(src)
            mem.pct = d.mem_pct || 0
            mem.used = d.mem_used || 0
            mem.total = d.mem_total || 0
        } catch (e) {
            // Keep the previous reading on malformed cache.
        }
    }

    function activate(): void {
        mem.sysToggleRequested()
    }

    implicitWidth: row.implicitWidth + 12
    implicitHeight: 30
    radius: 15
    color: active ? Theme.primary : "transparent"
    Behavior on color { ColorAnimation { duration: 500; easing.type: Easing.OutQuint } }

    RowLayout {
        id: row
        anchors.centerIn: parent
        spacing: 6

        Text {
            Layout.alignment: Qt.AlignVCenter
            text: "RAM"
            color: mem.active ? Theme.background : Theme.primary
            font.family: Theme.fontFamily
            font.pixelSize: 12
            font.bold: true
        }
        Text {
            Layout.alignment: Qt.AlignVCenter
            text: Metrics.memoryUsed(mem.used)
            color: mem.active ? Theme.background : Theme.primary
            font.family: Theme.fontFamily
            font.pixelSize: 14
            font.bold: true
        }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        cursorShape: Qt.PointingHandCursor
        onClicked: mouse => {
            if (mouse.button === Qt.RightButton)
                mem.sysToggleRequested()
            else
                mem.activate()
        }
        onEntered: {
            closeTimer.stop()
            dwellTimer.start()
        }
        onPositionChanged: dwellTimer.restart()
        onExited: {
            dwellTimer.stop()
            closeTimer.start()
        }
    }

    Timer {
        id: dwellTimer
        interval: 250
        onTriggered: mem.sysOpenRequested()
    }
    Timer {
        id: closeTimer
        interval: 1000
        onTriggered: mem.sysCloseRequested()
    }

    function cancelClose(): void {
        closeTimer.stop()
    }
    function scheduleClose(): void {
        closeTimer.restart()
    }

    FileView {
        id: cacheFile
        path: Quickshell.env("HOME") + "/.cache/sysinfo.json"
        blockLoading: true
        printErrors: false
        onLoaded: mem.parseSys(text())
    }
    Timer {
        interval: 3000
        repeat: true
        running: true
        onTriggered: cacheFile.reload()
    }
}
