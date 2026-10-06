import Quickshell.Hyprland
import QtQuick
import QtQuick.Layouts
import qs.CustomTheme

// Hyprland workspace switcher.
RowLayout {
    id: wsRoot
    spacing: 6

    // The bar's configured minimum; our named layout always covers 1..9.
    // The list still grows if a higher-numbered workspace exists.
    property int minWorkspaces: 9

    // Display names for the numbered workspaces (must match custom.lua layout).
    readonly property var workspaceNames: ({
        1: "main", 2: "work", 3: "search", 4: "notes", 5: "chat",
        6: "mail", 7: "others", 8: "terminals", 9: "gaming"
    })
    function workspaceName(id: int): string {
        return wsRoot.workspaceNames[id] || ("" + id)
    }

    // The individual workspace buttons, exposed so StatusbarWindow can splice
    // them into its keyboard-navigation list. Rebuilt whenever workspaces are
    // added or removed.
    property var navButtons: []

    // Optional monitor filter (used by the slim side bars): when set, only
    // workspaces currently on that monitor are listed, and the active
    // highlight follows that monitor's active workspace. Empty = today's
    // global behavior, byte for byte.
    property string monitorName: ""

    // Size overrides so the slim side bars can run a touch smaller than the
    // center bar. Defaults preserve the center bar byte for byte.
    property int buttonHeight: 26
    property int buttonFontSize: 13
    property int buttonPadding: 18

    // Active workspace id for the filtered monitor, or -1. Falls back to
    // the global focus when the monitor or its active workspace is missing.
    readonly property int monitorActiveId: {
        if (wsRoot.monitorName === "")
            return -1
        const monitors = Hyprland.monitors.values
        for (let i = 0; i < monitors.length; i++) {
            if (monitors[i].name === wsRoot.monitorName
                && monitors[i].activeWorkspace)
                return monitors[i].activeWorkspace.id
        }
        return Hyprland.focusedWorkspace ? Hyprland.focusedWorkspace.id : -1
    }

    function rebuildNavButtons(): void {
        let a = []
        for (let i = 0; i < rep.count; i++)
            a.push(rep.itemAt(i))
        wsRoot.navButtons = a
    }

    // Workspaces that stay hidden while empty; they appear as soon as they
    // hold windows or take focus. Everything else always shows.
    readonly property var autoHideIds: [2, 7, 9]

    // The workspace ids to render. Unfiltered (center bar): 1..N, where N is
    // at least minWorkspaces and extends to cover the highest-numbered
    // workspace that currently exists. Filtered (side bars): exactly the
    // workspaces currently on that monitor. Reactive only: re-evaluates when
    // Hyprland's workspace list or focus changes, no timers or polling.
    readonly property var workspaceIds: {
        const list = Hyprland.workspaces.values
        if (wsRoot.monitorName !== "") {
            let ids = []
            for (let i = 0; i < list.length; i++)
                if (list[i].monitor && list[i].monitor.name === wsRoot.monitorName)
                    ids.push(list[i].id)
            return ids.sort((a, b) => a - b)
        }
        let maxId = Math.max(9, wsRoot.minWorkspaces)
        for (let i = 0; i < list.length; i++)
            if (list[i].id > maxId)
                maxId = list[i].id
        const focusedId = Hyprland.focusedWorkspace ? Hyprland.focusedWorkspace.id : -1
        let ids = []
        for (let id = 1; id <= maxId; id++) {
            if (wsRoot.autoHideIds.indexOf(id) !== -1 && id !== focusedId) {
                let occupied = false
                for (let j = 0; j < list.length; j++)
                    if (list[j].id === id && list[j].toplevels.values.length > 0) {
                        occupied = true
                        break
                    }
                if (!occupied)
                    continue
            }
            ids.push(id)
        }
        return ids
    }

    // The live Hyprland workspace for an id, or null when it doesn't exist.
    function workspaceById(id: int): var {
        const list = Hyprland.workspaces.values
        for (let i = 0; i < list.length; i++)
            if (list[i].id === id)
                return list[i]
        return null
    }

    Repeater {
        id: rep
        model: wsRoot.workspaceIds

        onItemAdded: wsRoot.rebuildNavButtons()
        onItemRemoved: wsRoot.rebuildNavButtons()

        delegate: Rectangle {
            id: ws
            required property var modelData   // the workspace id (int)
            // Set by StatusbarWindow's keyboard navigation.
            property bool focused: false

            // Whether this workspace is the currently focused one: the
            // monitor's own active workspace when filtered, global focus
            // otherwise (center behavior unchanged).
            readonly property bool isActive: wsRoot.monitorName !== ""
                ? wsRoot.monitorActiveId === ws.modelData
                : Hyprland.focusedWorkspace
                && Hyprland.focusedWorkspace.id === ws.modelData
            // Whether the workspace currently holds windows (exists in Hyprland).
            readonly property bool occupied: wsRoot.workspaceById(ws.modelData) !== null

            // Run this workspace's action (mouse click or keyboard Return).
            // Hyprland with Lua dispatchers ignores the plain "workspace N"
            // string, so branch on usingLua the same way the overview does.
            function activate(): void {
                if (Hyprland.usingLua)
                    Hyprland.dispatch("hl.dsp.focus({workspace = '" + ws.modelData + "'})")
                else
                    Hyprland.dispatch("workspace " + ws.modelData)
            }

            implicitWidth: wsLabel.width + wsRoot.buttonPadding
            implicitHeight: wsRoot.buttonHeight
            radius: wsRoot.buttonHeight / 2

            // Empty, unfocused workspaces are dimmed to set them apart from the
            // ones that hold windows.
            opacity: (ws.isActive || ws.occupied || wsMouse.containsMouse) ? 1 : 0.45
            Behavior on opacity {
                NumberAnimation { duration: 300; easing.type: Easing.OutQuint }
            }

            color: ws.isActive
                ? Theme.primary
                : (wsMouse.containsMouse ? Theme.surface_container_high : "transparent")
            border.color: Theme.primary
            border.width: ws.isActive ? 0 : 1

            // Crossfade the fill between active / hover / inactive states so the
            // background of the active circle fades in and the previous one out.
            Behavior on color {
                ColorAnimation { duration: 500; easing.type: Easing.OutQuint }
            }
            // Fade the outline in/out as the fill takes over on activation.
            Behavior on border.width {
                NumberAnimation { duration: 500; easing.type: Easing.OutQuint }
            }

            // Keyboard-selection ring, distinct from the active-workspace fill.
            Rectangle {
                anchors.fill: parent
                anchors.margins: -3
                radius: width / 2
                color: "transparent"
                border.color: Theme.primary
                border.width: 2
                opacity: ws.focused ? 1 : 0
                Behavior on opacity {
                    NumberAnimation { duration: 150 }
                }
            }

            Text {
                id: wsLabel
                anchors.centerIn: parent
                text: wsRoot.workspaceName(ws.modelData)
                color: ws.isActive ? Theme.background : Theme.on_background
                font.family: Theme.fontFamily
                font.pixelSize: wsRoot.buttonFontSize
                font.bold: true

                // Match the fill crossfade so the label recolors in step.
                Behavior on color {
                    ColorAnimation { duration: 500; easing.type: Easing.OutQuint }
                }
            }

            MouseArea {
                id: wsMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: ws.activate()
            }
        }
    }
}
