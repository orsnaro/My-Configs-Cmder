import QtQuick
import QtQuick.Effects
import qs.CustomTheme

// Reusable round icon button used across the status bar modules.
Rectangle {
    id: btn
    property string iconSrc: ""
    property bool colorize: true
    property real buttonSize: 30
    property real iconSize: 18
    // Set by the keyboard navigation in StatusbarWindow to highlight the
    // currently selected module.
    property bool focused: false
    signal clicked()

    // Run the button's action (mouse click or keyboard Return).
    function activate(): void { btn.clicked() }

    // Highlighted when hovered with the mouse or selected via the keyboard.
    readonly property bool active: mouseArea.containsMouse || btn.focused

    implicitWidth: buttonSize
    implicitHeight: buttonSize
    radius: buttonSize / 2

    // Every button gets the same accent-filled circle on hover/selection.
    // (colorize only controls whether the icon itself is recolored, so the
    // ML4W logo keeps its own colors while still matching the others.)
    color: btn.active ? Theme.primary : "transparent"

    // Fade the accent circle in on hover/selection and out again on leave.
    Behavior on color {
        ColorAnimation { duration: 500; easing.type: Easing.OutQuint }
    }

    Image {
        anchors.centerIn: parent
        source: btn.iconSrc
        width: btn.iconSize
        height: btn.iconSize
        sourceSize.width: btn.iconSize * 2
        sourceSize.height: btn.iconSize * 2
        fillMode: Image.PreserveAspectFit
        layer.enabled: btn.colorize
        layer.effect: MultiEffect {
            colorization: 1.0
            colorizationColor: btn.active ? Theme.background : Theme.primary

            // Recolor the icon in step with the circle fade.
            Behavior on colorizationColor {
                ColorAnimation { duration: 500; easing.type: Easing.OutQuint }
            }
        }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: btn.clicked()
    }
}
