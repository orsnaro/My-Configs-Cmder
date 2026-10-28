import Quickshell
import QtQuick
import qs.DockApp

ShellRoot {
    Timer {
        interval: 50
        running: true
        repeat: true
        onTriggered: {
            if (!DockSettings.ready)
                return
            stop()
            function check(ok, message) {
                if (!ok) throw new Error(message)
            }
            try {
                const settings = DockSettings.settings
                check(DockSettings.enabled, "dock must be enabled")
                check(settings.dock.iconSize === 20, "compact icons must be 20px")
                check(settings.dock.spacing === 5, "compact spacing must be 5px")
                check(settings.pill.padding === 6, "compact pill padding must be 6px")
                check(settings.dock.marginBottom === 6, "compact bottom gap must be 6px")
                check(settings.dock.monitor === "DP-2", "dock must keep its selected monitor")
                check(!DockSettings.autohide, "dock must stay visible rather than autohide")
                check(settings.dock.reserveSpace, "dock must keep tiled windows above it")
                console.log("PASS: enabled compact dock preferences")
                Qt.quit()
            } catch (error) {
                console.error("FAIL:", error.message)
                Qt.exit(1)
            }
        }
    }
}
