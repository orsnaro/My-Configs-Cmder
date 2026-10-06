import Quickshell
import Quickshell.Io
import QtQuick
import QtQuick.Layouts
import qs.CustomTheme
import "SystemMetricFormat.js" as Metrics

// Display-only RAM pill for side bars: same reading as the primary bar's
// MemModule (used GiB from ~/.cache/sysinfo.json, same memoryUsed format)
// but no click/hover and no SystemPanel. The center bar owns the
// sysinfo fetcher; this only re-reads the shared cache.
Rectangle {
    id: slimMem

    property real used: 0
    property int pillHeight: 26
    property int fontSize: 12

    function parseSys(src): void {
        try {
            let d = JSON.parse(src)
            slimMem.used = d.mem_used || 0
        } catch (e) {
            // Keep the previous reading on malformed cache.
        }
    }

    implicitWidth: row.implicitWidth + 12
    implicitHeight: slimMem.pillHeight
    radius: slimMem.pillHeight / 2
    color: "transparent"

    RowLayout {
        id: row
        anchors.centerIn: parent
        spacing: 6

        Text {
            Layout.alignment: Qt.AlignVCenter
            text: "RAM"
            color: Theme.primary
            font.family: Theme.fontFamily
            font.pixelSize: 12
            font.bold: true
        }
        Text {
            Layout.alignment: Qt.AlignVCenter
            text: Metrics.memoryUsed(slimMem.used)
            color: Theme.primary
            font.family: Theme.fontFamily
            font.pixelSize: slimMem.fontSize
            font.bold: true
        }
    }

    FileView {
        id: cacheFile
        path: Quickshell.env("HOME") + "/.cache/sysinfo.json"
        blockLoading: true
        printErrors: false
        onLoaded: slimMem.parseSys(text())
    }
    Timer {
        interval: 3000
        repeat: true
        running: true
        onTriggered: cacheFile.reload()
    }
}
