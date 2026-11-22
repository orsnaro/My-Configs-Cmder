import Quickshell
import QtQuick
import "StatusbarApp"

ShellRoot {
    CpuModule { id: metrics }
    Timer {
        interval: 150
        running: true
        onTriggered: {
            function check(ok, message) {
                if (!ok) throw new Error(message)
            }
            try {
                metrics.parseSys('{"cpu_pct":7,"cpu_ghz":4.1,"gpu":{"usage":12,"vram_used_gb":1.2}}')
                check(metrics.gpuPct === 12, "GPU must use the existing cached sample")
                check(metrics.vramUsed === 1.2, "VRAM must use the existing cached sample")
                check(metrics.gpuText === "12%", "GPU display must include percent")
                check(metrics.vramText === "1.2 GiB", "VRAM must use the existing formatter")
                metrics.parseSys('{"gpu":{"usage":0,"vram_used_gb":0}}')
                check(metrics.gpuText === "0%" && metrics.vramText === "0.0 GiB", "zero is a valid reading")
                metrics.parseSys('{}')
                check(metrics.gpuText === "—" && metrics.vramText === "—", "unavailable is not zero")
                metrics.parseSys('{"gpu":{"usage":"bad","vram_used_gb":-1}}')
                check(metrics.gpuText === "—" && metrics.vramText === "—", "invalid sensor values must not leak into display")
                metrics.parseSys('{"gpu":{"usage":9,"vram_used_gb":0.5}}')
                metrics.parseSys('malformed')
                check(metrics.gpuPct === 9 && metrics.vramUsed === 0.5, "malformed cache must retain last sample")
                console.log("PASS: existing sample GPU/VRAM display")
                Qt.quit()
            } catch (error) {
                console.error("FAIL:", error.message)
                Qt.exit(1)
            }
        }
    }
}
