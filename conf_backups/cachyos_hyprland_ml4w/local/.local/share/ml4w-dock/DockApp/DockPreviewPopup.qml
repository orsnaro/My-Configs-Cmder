import Quickshell
import QtQuick
import QtQuick.Layouts
import qs.DockApp

// Hover preview popup: one DockPreviewCard per window of the hovered app.
// A separate PopupWindow (like the item tooltip), NOT an in-window item: the
// dock window only reserves room for the context menu, so a tall in-window
// popup gets its top cut off. Its own surface also needs no input-mask work.
PopupWindow {
    id: popup

    // Item the popup hangs off; set by openFor for anchoring.
    property var targetItem: null
    // Windows to show; cleared on close so card views (and captures) die.
    property var windows: []
    property string appName: ""
    // Cards that fit above the dock; DockWindow passes it from the space
    // available (a 6-card stack is taller than short screens).
    property int maxCards: 6
    property int overflow: 0

    readonly property bool isOpen: popup.visible

    function openFor(item, maxCards): void {
        if (maxCards !== undefined)
            popup.maxCards = Math.max(1, maxCards)
        popup.targetItem = item
        popup.windows = item.windows.slice(0, popup.maxCards)
        popup.overflow = Math.max(0, item.windows.length - popup.windows.length)
        popup.appName = item.appName
        popup.visible = true
        for (const w of popup.windows) {
            if (w && w.closed)
                w.closed.connect(() => popup.dropWindow(w))
        }
        // Delayed past first map: capturing before the recording context is
        // ready just logs an error. The 2s refresh covers any miss.
        initialCapture.restart()
    }
    function close(): void {
        initialCapture.stop()
        popup.visible = false
        popup.windows = []
        popup.targetItem = null
    }

    // Drop a window that closed mid-open. Last one out hides the popup
    // (DockWindow retargets previewItem on the next hover).
    function dropWindow(w): void {
        const kept = popup.windows.filter(x => x !== w)
        if (kept.length === popup.windows.length)
            return
        if (kept.length === 0) {
            popup.close()
            return
        }
        popup.windows = kept
    }

    function captureAll(): void {
        for (let i = 0; i < rep.count; i++) {
            const card = rep.itemAt(i)
            if (card)
                card.capture()
        }
    }

    color: "transparent"
    implicitWidth: 296
    implicitHeight: cards.implicitHeight + (overflowLabel.visible ? 26 : 0)

    anchor.item: popup.targetItem
    anchor.edges: Edges.Top
    anchor.gravity: Edges.Top
    anchor.margins.bottom: 8

    visible: false

    Timer {
        id: initialCapture
        interval: 500
        onTriggered: popup.captureAll()
    }

    ColumnLayout {
        id: cards
        anchors.fill: parent
        spacing: 8

        Repeater {
            id: rep
            model: popup.windows
            DockPreviewCard {
                Layout.fillWidth: true
                toplevel: modelData
                appName: popup.appName
                windowIndex: index
                windowCount: popup.windows.length
            }
        }

        Text {
            id: overflowLabel
            visible: popup.overflow > 0
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
            text: "+" + popup.overflow + " more"
            color: DockTheme.on_surface
            font.family: DockTheme.fontFamily
            font.pixelSize: 12
        }
    }

    // Snapshot + refresh: first frame shortly after map, re-captured every
    // 2s while open. Bound to visibility — never fires while closed (spec
    // hard requirement: no background captures).
    Timer {
        interval: 2000
        repeat: true
        running: popup.isOpen
        onTriggered: popup.captureAll()
    }

    // Hovering the popup cancels the icon's scheduled hide (crossing the
    // gap); leaving it re-arms the hide.
    HoverHandler {
        id: previewHover
        onHoveredChanged: {
            const item = popup.targetItem
            if (!item || !item.cancelPreviewClose)
                return
            if (previewHover.hovered)
                item.cancelPreviewClose()
            else
                item.schedulePreviewClose()
        }
    }
}
