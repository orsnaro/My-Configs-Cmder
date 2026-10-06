import Quickshell
import Quickshell.Io
import QtQuick
import QtQuick.Layouts
import qs.CustomTheme

// CPU pill: usage percent + clock. Left click opens the shared system
// panel; data comes from hypr-sysinfo via ~/.cache/sysinfo.json.
Rectangle {
    id: cpu

    signal sysToggleRequested
    signal sysOpenRequested
    signal sysCloseRequested

    property int pct: 0
    property real ghz: 0
    property bool focused: false
    readonly property bool active: mouseArea.containsMouse || cpu.focused
    readonly property bool collapsed: false

    function parseSys(src): void {
        try {
            let d = JSON.parse(src)
            cpu.pct = d.cpu_pct || 0
            cpu.ghz = d.cpu_ghz || 0
        } catch (e) {
            // Keep the previous reading on malformed cache.
        }
    }

    function activate(): void {
        cpu.sysToggleRequested()
    }

    function refresh(): void {
        fetchProc.running = true
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
            text: "CPU"
            color: cpu.active ? Theme.background : Theme.primary
            font.family: Theme.fontFamily
            font.pixelSize: 12
            font.bold: true
        }
        Text {
            Layout.alignment: Qt.AlignVCenter
            text: cpu.pct + "% · " + cpu.ghz.toFixed(1) + "GHz"
            color: cpu.active ? Theme.background : Theme.primary
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
                cpu.sysToggleRequested()
            else
                cpu.activate()
        }
        onEntered: {
            closeTimer.stop()
            dwellTimer.start()
        }
        onPositionChanged: dwellTimer.restart()
        // Leaving schedules a hide; reaching the panel in time cancels it.
        onExited: {
            dwellTimer.stop()
            closeTimer.start()
        }
    }

    Timer {
        id: dwellTimer
        interval: 250
        onTriggered: cpu.sysOpenRequested()
    }
    Timer {
        id: closeTimer
        interval: 1000
        onTriggered: cpu.sysCloseRequested()
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
        onLoaded: cpu.parseSys(text())
    }

    Process {
        id: fetchProc
        command: [Quickshell.env("HOME") + "/.local/bin/hypr-sysinfo"]
        running: true
        stdout: StdioCollector { onStreamFinished: cacheFile.reload() }
    }
    Timer {
        interval: 3000
        repeat: true
        running: true
        onTriggered: fetchProc.running = true
    }
}
