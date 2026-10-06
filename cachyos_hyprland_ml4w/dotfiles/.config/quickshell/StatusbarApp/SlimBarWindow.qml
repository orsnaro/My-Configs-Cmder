import Quickshell
import Quickshell.Wayland
import Quickshell.Hyprland
import QtQuick
import QtQuick.Layouts
import QtQuick.Effects
import qs.CustomTheme

// Slim companion bar for a side monitor: workspaces + clock (+ calendar,
// volume dropdown, RAM display-only, layout). RAM only re-reads the shared
// sysinfo cache, everything else is event-driven.
PanelWindow {
    id: root

    // Screen this bar belongs to. Injected by the Variants delegate in
    // shell.qml (one entry per side screen): the delegate must declare it
    // to receive it — an undeclared modelData silently stays undefined and
    // the bar hides itself.
    required property var modelData
    readonly property string screenName: (typeof modelData === "string") ? modelData : ""
    // The placed clock module; the calendar panel anchors to it.
    property var clockRef: null
    // Flipped by the clock; the panel reads it.
    property bool calendarOpen: false
    // Volume dropdown state; the panel reads it. Same hover pattern as center.
    property bool volumeOpen: false
    property var volumeRef: null

    screen: {
        const screens = Quickshell.screens
        if (!screens)
            return null
        for (let s = 0; s < screens.length; s++)
            if (screens[s].name === root.screenName)
                return screens[s]
        return null
    }
    // A missing/unplugged side output hides its bar instead of duplicating
    // the center bar via fallback.
    visible: root.screen !== null

    WlrLayershell.layer: WlrLayer.Top
    color: "transparent"

    anchors {
        top: true
        left: true
        right: true
    }
    margins {
        top: 0
    }

    readonly property int barHeight: 36
    // The bar reserves a slim strip so windows tile below it (a touch less
    // than the 40px center bar; the clock text itself stays full-size).
    exclusiveZone: barHeight
    // Room below the bar for the calendar, reserved permanently (resizing a
    // layer surface while the panel opens fights the animation, cf. center).
    readonly property int calendarReserve: calendarPanel.implicitHeight + 40
    readonly property int volumeReserve: volumePanel.implicitHeight + 40
    implicitHeight: barHeight + 40 + Math.max(calendarReserve, volumeReserve)

    // Outside clicks close the panels (focus grab covers other windows).
    HyprlandFocusGrab {
        windows: [root]
        active: root.calendarOpen || root.volumeOpen
        onCleared: {
            root.calendarOpen = false
            root.volumeOpen = false
        }
    }
    Shortcut {
        sequence: "Escape"
        enabled: root.calendarOpen || root.volumeOpen
        onActivated: {
            if (root.calendarOpen)
                root.calendarOpen = false
            else
                root.volumeOpen = false
        }
    }

    // Only the pill takes pointer input; the rest stays click-through.
    // While a panel is open its area is clickable too.
    mask: Region {
        Region {
            x: Math.round(pill.x)
            y: Math.round(pill.y)
            width: Math.round(pill.width)
            height: Math.round(pill.height)
        }
        Region {
            x: Math.round(calendarPanel.x)
            y: Math.max(0, Math.round(calendarPanel.y))
            width: root.calendarOpen ? Math.round(calendarPanel.width) : 0
            height: root.calendarOpen
                ? Math.max(0, Math.round(calendarPanel.y + calendarPanel.height)
                    - Math.max(0, Math.round(calendarPanel.y)))
                : 0
        }
        Region {
            x: Math.round(volumePanel.x)
            y: Math.max(0, Math.round(volumePanel.y))
            width: root.volumeOpen ? Math.round(volumePanel.width) : 0
            height: root.volumeOpen
                ? Math.max(0, Math.round(volumePanel.y + volumePanel.height)
                    - Math.max(0, Math.round(volumePanel.y)))
                : 0
        }
    }

    MouseArea {
        anchors.fill: parent
        enabled: root.calendarOpen || root.volumeOpen
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        onClicked: {
            root.calendarOpen = false
            root.volumeOpen = false
        }
    }

    Item {
        id: pill
        anchors.horizontalCenter: parent.horizontalCenter
        // Fixed at the top: the window grows downward for the calendar, and
        // a centered pill would float mid-screen on a tall window.
        anchors.top: parent.top
        anchors.topMargin: 10
        width: Math.min(parent.width - 32, row.implicitWidth + 28)
        height: 36

        RectangularShadow {
            anchors.fill: pillBg
            radius: pillBg.radius
            blur: 15
            color: Qt.rgba(Theme.shadow.r, Theme.shadow.g, Theme.shadow.b, 0.4)
        }

        // Same treatment as the center pill: gradient border, inner fill.
        Rectangle {
            id: pillBg
            anchors.fill: parent
            radius: 11
            opacity: 0.8
            gradient: Gradient {
                orientation: Gradient.Vertical
                GradientStop { position: 0.0; color: Theme.primary }
                GradientStop { position: 1.0; color: Theme.on_primary }
            }

            Rectangle {
                anchors.fill: parent
                anchors.margins: 2
                radius: parent.radius - anchors.margins
                color: Theme.background
            }
        }

        RowLayout {
            id: row
            anchors.fill: parent
            anchors.leftMargin: 14
            anchors.rightMargin: 14
            spacing: 12

            WorkspacesModule {
                Layout.alignment: Qt.AlignVCenter
                monitorName: root.screenName
                buttonHeight: 23
                buttonFontSize: 12
                buttonPadding: 16
            }
            Item {
                Layout.fillWidth: true
            }
            ClockModule {
                id: clockModule
                Layout.alignment: Qt.AlignVCenter
                onCalendarToggleRequested: root.calendarOpen = !root.calendarOpen
                Component.onCompleted: root.clockRef = clockModule
                Component.onDestruction: {
                    if (root.clockRef === clockModule)
                        root.clockRef = null
                }
            }
            Item {
                Layout.fillWidth: true
            }
            // Right area: RAM (display-only) + layout + volume.
            // Compact variant of the center modules; the clock above is left
            // at full size on purpose. RAM re-reads the shared sysinfo cache
            // owned by the center bar — no fetcher of its own.
            RowLayout {
                id: rightArea
                Layout.alignment: Qt.AlignVCenter
                spacing: 5
                SlimMemModule {
                    Layout.alignment: Qt.AlignVCenter
                    pillHeight: 26
                    fontSize: 12
                }
                KeyboardLayoutModule {
                    Layout.alignment: Qt.AlignVCenter
                    pillHeight: 26
                    fontSize: 12
                }
                VolumeModule {
                    id: volumeModule
                    Layout.alignment: Qt.AlignVCenter
                    pillHeight: 26
                    fontSize: 12
                    iconSize: 16
                    onVolumeOpenRequested: root.volumeOpen = true
                    onVolumeCloseRequested: root.volumeOpen = false
                    Component.onCompleted: root.volumeRef = volumeModule
                    Component.onDestruction: {
                        if (root.volumeRef === volumeModule)
                            root.volumeRef = null
                    }
                }
            }
        }
    }

    // Shared calendar agenda under the side clock, clamped on screen.
    CalendarPanel {
        id: calendarPanel

        isOpen: root.calendarOpen

        x: {
            let holder = root.clockRef ? root.clockRef.parent : null
            if (!holder)
                return Math.round((root.width - width) / 2)
            let center = pill.x + row.x + holder.x + holder.width / 2
            return Math.round(Math.max(8,
                Math.min(root.width - width - 8, center - width / 2)))
        }

        readonly property int calendarGap: 26
        openY: Math.round(pill.y + pill.height + calendarGap - cardInset)
    }

    // Volume dropdown under the side volume pill, clamped on screen.
    VolumePanel {
        id: volumePanel

        isOpen: root.volumeOpen
        volumeModule: root.volumeRef

        x: {
            if (!root.volumeRef)
                return Math.round((root.width - width) / 2)
            let center = pill.x + row.x + rightArea.x + root.volumeRef.x + root.volumeRef.width / 2
            return Math.round(Math.max(8,
                Math.min(root.width - width - 8, center - width / 2)))
        }

        readonly property int volumeGap: 26
        openY: Math.round(pill.y + pill.height + volumeGap - cardInset)
    }
}
