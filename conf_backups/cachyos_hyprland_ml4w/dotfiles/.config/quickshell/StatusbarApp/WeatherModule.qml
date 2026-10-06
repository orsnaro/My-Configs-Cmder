import Quickshell
import Quickshell.Io
import QtQuick
import QtQuick.Layouts
import qs.CustomTheme

// Alexandria weather: temperature + condition glyph, data from hypr-weather
// (Open-Meteo, no key) via ~/.cache/weather.json. Click refreshes.
Rectangle {
    id: weather

    property int temp: 0
    property int code: 3
    property bool isDay: true
    property bool focused: false
    readonly property bool active: mouseArea.containsMouse || weather.focused
    // Always shown once the cache has loaded (temp stays 0 with no cache,
    // but the fetch runs at startup so this is only the first seconds).
    readonly property bool collapsed: false

    // WMO weather-code to a widely-covered glyph (DejaVu set, no Nerd
    // Font dependency). Anything undescribed falls through to cloud.
    readonly property string glyph: {
        if (code === 0)
            return isDay ? "☀" : "☾"
        if (code === 71 || code === 73 || code === 75 || code === 77
            || code === 85 || code === 86)
            return "❄"
        if ((code >= 51 && code <= 67) || (code >= 80 && code <= 82)
            || code >= 95)
            return "☂"
        return "☁"
    }

    function parseWeather(src): void {
        try {
            let d = JSON.parse(src)
            weather.temp = d.temp || 0
            weather.code = (d.code === undefined) ? 3 : d.code
            weather.isDay = (d.day === undefined) ? true : (d.day === 1)
        } catch (e) {
            // Keep the previous reading on malformed cache.
        }
    }

    function activate(): void {
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
            text: weather.glyph
            color: weather.active ? Theme.background : Theme.primary
            font.family: Theme.fontFamily
            font.pixelSize: 16
        }
        Text {
            Layout.alignment: Qt.AlignVCenter
            text: weather.temp + "°"
            color: weather.active ? Theme.background : Theme.primary
            font.family: Theme.fontFamily
            font.pixelSize: 14
            font.bold: true
        }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: weather.activate()
    }

    FileView {
        id: cacheFile
        path: Quickshell.env("HOME") + "/.cache/weather.json"
        blockLoading: true
        printErrors: false
        onLoaded: weather.parseWeather(text())
    }

    Process {
        id: fetchProc
        command: [Quickshell.env("HOME") + "/.local/bin/hypr-weather"]
        running: true
        stdout: StdioCollector { onStreamFinished: cacheFile.reload() }
    }
    Timer {
        interval: 1800000
        repeat: true
        running: true
        onTriggered: fetchProc.running = true
    }
}
