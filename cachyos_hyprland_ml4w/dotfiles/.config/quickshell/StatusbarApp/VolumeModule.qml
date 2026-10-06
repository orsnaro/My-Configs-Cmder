import Quickshell
import Quickshell.Services.Pipewire
import QtQuick
import QtQuick.Effects
import QtQuick.Layouts
import qs.CustomTheme

// Shows the default output sink's volume next to a speaker icon.
//   • left click           → mute; left click again restores it
//   • right click / Return → open pavucontrol
//   • mouse wheel (hovered)  → raise/lower the volume in 5% steps
//   • Up / Down arrows (keyboard-focused) → raise/lower the volume
// Volume and mute come from the Pipewire service; PwObjectTracker keeps the
// sink's audio properties bound while this module is alive.
Rectangle {
    id: volume

    signal volumeOpenRequested
    signal volumeCloseRequested

    // The system default output sink (speakers/headphones).
    readonly property PwNode sink: Pipewire.defaultAudioSink
    // The sink's audio binding is only valid once the node is ready and is an
    // audio node; guard every access against it being null.
    readonly property bool ready: sink !== null && sink.ready && sink.audio !== null
    // Current volume as a 0.0–1.0 fraction and its rounded percentage.
    readonly property real level: ready ? sink.audio.volume : 0
    readonly property bool muted: ready ? sink.audio.muted : false
    readonly property int percent: muted ? 0 : Math.round(level * 100)

    // How much one wheel notch / arrow press changes the volume.
    readonly property real stepSize: 0.05

    // Set by the keyboard navigation in StatusbarWindow.
    property bool focused: false

    // Size overrides so the slim side bars can run a touch smaller than the
    // center bar. Defaults preserve the center bar byte for byte.
    property int pillHeight: 30
    property int fontSize: 14
    property int iconSize: 18

    // Keep the sink's audio (volume/muted) properties live and writable.
    PwObjectTracker { objects: sink !== null ? [sink] : [] }

    // Set the volume to an absolute fraction, unmuting first so a scroll/arrow
    // while muted brings the sound back.
    function setVolume(v: real): void {
        if (!ready)
            return
        sink.audio.muted = false
        sink.audio.volume = Math.max(0, Math.min(1, v))
    }

    // Raise (dir > 0) or lower (dir < 0) the volume by one step. Called by the
    // mouse wheel and by the Up/Down keys when this module is keyboard-focused.
    function step(dir: int): void {
        setVolume(level + dir * stepSize)
    }

    // Right click: toggle mute. Pipewire keeps the volume value while muted, so
    // un-muting restores exactly the level from before.
    function toggleMute(): void {
        if (ready)
            sink.audio.muted = !sink.audio.muted
    }

    // Left click / keyboard Return: open the volume control GUI.
    function activate(): void {
        Quickshell.execDetached(["pavucontrol"])
    }

    readonly property bool active: mouseArea.containsMouse || volume.focused

    implicitWidth: row.implicitWidth + 6
    implicitHeight: volume.pillHeight
    radius: volume.pillHeight / 2

    // Same accent-filled highlight as the other modules on hover/selection.
    color: active ? Theme.primary : "transparent"

    // Fade the accent circle in/out like BarButton does.
    Behavior on color {
        ColorAnimation { duration: 500; easing.type: Easing.OutQuint }
    }

    RowLayout {
        id: row
        anchors.centerIn: parent
        spacing: 4

        Image {
            Layout.alignment: Qt.AlignVCenter
            source: volume.percent <= 0
                ? "../shared/icons/volume-muted.svg"
                : "../shared/icons/volume.svg"
            sourceSize.width: volume.iconSize
            sourceSize.height: volume.iconSize
            width: volume.iconSize
            height: volume.iconSize
            fillMode: Image.PreserveAspectFit
            layer.enabled: true
            layer.effect: MultiEffect {
                colorization: 1.0
                colorizationColor: volume.active ? Theme.background : Theme.primary
                Behavior on colorizationColor {
                    ColorAnimation { duration: 500; easing.type: Easing.OutQuint }
                }
            }
        }

        Text {
            Layout.alignment: Qt.AlignVCenter
            text: volume.percent + "%"
            color: volume.active ? Theme.background : Theme.primary
            font.family: Theme.fontFamily
            font.pixelSize: volume.fontSize
            font.bold: true
            Behavior on color {
                ColorAnimation { duration: 500; easing.type: Easing.OutQuint }
            }
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
                volume.activate()
            else
                volume.toggleMute()
        }
        onWheel: wheel => volume.step(wheel.angleDelta.y > 0 ? 1 : -1)
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
        onTriggered: volume.volumeOpenRequested()
    }
    Timer {
        id: closeTimer
        interval: 1000
        onTriggered: volume.volumeCloseRequested()
    }

    function cancelClose(): void {
        closeTimer.stop()
    }
    function scheduleClose(): void {
        closeTimer.restart()
    }
}
