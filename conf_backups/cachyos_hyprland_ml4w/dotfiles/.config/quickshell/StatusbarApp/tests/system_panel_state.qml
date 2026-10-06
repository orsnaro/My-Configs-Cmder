import QtQuick
import ".." as Statusbar

Window {
    visible: false
    property Statusbar.SystemPanelState state: Statusbar.SystemPanelState {}

    function check(ok, reason) {
        if (!ok) {
            console.error("FAIL:", reason)
            Qt.exit(1)
            throw new Error(reason)
        }
    }

    Timer {
        interval: 1
        running: true
        onTriggered: {
            check(!state.isOpen && !state.pinned, "starts closed")
            state.hoverOpen()
            check(state.isOpen && !state.pinned, "hover opens temporarily")
            state.hoverClose()
            check(!state.isOpen, "leaving a hover closes")
            state.hoverOpen()
            state.toggle()
            check(state.isOpen && state.pinned, "click pins an open hover panel")
            state.hoverClose()
            check(state.isOpen, "leaving while pinned keeps it open")
            state.toggle()
            check(!state.isOpen && !state.pinned, "second click closes and unpins")
            state.toggle()
            state.close()
            check(!state.isOpen && !state.pinned, "outside click or Escape closes and unpins")
            console.log("PASS: system panel hover/click state")
            Qt.exit(0)
        }
    }
}
