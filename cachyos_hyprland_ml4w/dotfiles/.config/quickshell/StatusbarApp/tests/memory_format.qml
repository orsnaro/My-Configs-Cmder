import QtQuick
import "../SystemMetricFormat.js" as Metrics

Window {
    visible: false
    Timer {
        interval: 1
        running: true
        onTriggered: {
            const used = Metrics.memory(6, 15.3)
            if (used !== "6.0 / 15.3 GiB") {
                console.error("FAIL: RAM must show used and total in GiB, got", used)
                Qt.exit(1)
                return
            }
            const missing = Metrics.memory(null, null)
            if (missing !== "—") {
                console.error("FAIL: missing VRAM must not display a made-up value")
                Qt.exit(1)
                return
            }
            console.log("PASS: memory units and missing sensors")
            Qt.exit(0)
        }
    }
}
