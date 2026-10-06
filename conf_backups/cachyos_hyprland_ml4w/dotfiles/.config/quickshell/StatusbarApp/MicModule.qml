import Quickshell
import Quickshell.Services.Pipewire
import QtQuick
import QtQuick.Effects
import qs.CustomTheme

// Shows the default input source's (microphone) mute state as an icon.
//   • left click / Return → toggle mute; toggling back restores the level
//   • right click         → open pavucontrol
//   • mouse wheel (hovered) → raise/lower the mic volume in 5% steps
//   • Up / Down arrows (keyboard-focused) → raise/lower the mic volume
// Volume and mute come from the Pipewire service; PwObjectTracker keeps the
// source's audio properties bound while this module is alive.
Rectangle {
    id: mic

    // The system default input source (microphone).
    readonly property PwNode micSource: Pipewire.defaultAudioSource
    // The source's audio binding is only valid once the node is ready and is
    // an audio node; guard every access against it being null.
    readonly property bool ready: micSource !== null && micSource.ready && micSource.audio !== null
    // Current volume as a 0.0–1.0 fraction.
    readonly property real level: ready ? micSource.audio.volume : 0
    readonly property bool muted: ready ? micSource.audio.muted : false

    // How much one wheel notch / arrow press changes the volume.
    readonly property real stepSize: 0.05

    // Set by the keyboard navigation in StatusbarWindow.
    property bool focused: false

    // Size overrides so the slim side bars can run a touch smaller than the
    // center bar. Defaults preserve the center bar byte for byte.
    property int pillHeight: 30
    property int iconSize: 18

    // Keep the source's audio (volume/muted) properties live and writable.
    PwObjectTracker { objects: micSource !== null ? [micSource] : [] }

    // Set the volume to an absolute fraction, unmuting first so a scroll/arrow
    // while muted brings the mic back.
    function setVolume(v: real): void {
        if (!ready)
            return
        micSource.audio.muted = false
        micSource.audio.volume = Math.max(0, Math.min(1, v))
    }

    // Raise (dir > 0) or lower (dir < 0) the volume by one step. Called by the
    // mouse wheel and by the Up/Down keys when this module is keyboard-focused.
    function step(dir: int): void {
        setVolume(level + dir * stepSize)
    }

    // Toggle mute. Pipewire keeps the volume value while muted, so
    // un-muting restores exactly the level from before.
    function toggleMute(): void {
        if (ready)
            micSource.audio.muted = !micSource.audio.muted
    }

    // Keyboard Return: toggle mute (the primary action for an icon-only pill).
    function activate(): void {
        toggleMute()
    }

    // Right click: open the volume control GUI.
    function openMixer(): void {
        Quickshell.execDetached(["pavucontrol"])
    }

    readonly property bool active: mouseArea.containsMouse || mic.focused

    implicitWidth: mic.iconSize
    implicitHeight: mic.pillHeight
    radius: mic.pillHeight / 2

    // Same accent-filled highlight as the other modules on hover/selection.
    color: active ? Theme.primary : "transparent"

    // Fade the accent circle in/out like BarButton does.
    Behavior on color {
        ColorAnimation { duration: 500; easing.type: Easing.OutQuint }
    }

    Image {
        anchors.centerIn: parent
        source: mic.muted
            ? "../shared/icons/mic-muted.svg"
            : "../shared/icons/mic.svg"
        sourceSize.width: mic.iconSize
        sourceSize.height: mic.iconSize
        width: mic.iconSize
        height: mic.iconSize
        fillMode: Image.PreserveAspectFit
        layer.enabled: true
        layer.effect: MultiEffect {
            colorization: 1.0
            colorizationColor: mic.active ? Theme.background : (mic.muted ? Theme.error : Theme.primary)
            Behavior on colorizationColor {
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
                mic.openMixer()
            else
                mic.toggleMute()
        }
        onWheel: wheel => mic.step(wheel.angleDelta.y > 0 ? 1 : -1)
    }
}
