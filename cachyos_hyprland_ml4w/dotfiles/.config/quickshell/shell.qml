//@ pragma UseQApplication

import Quickshell
import Quickshell.Io
import QtQuick
import "WelcomeApp"
import "PowerApp"
import "SidebarApp"
import "WallpaperApp"
import "StatusbarApp"
import "CustomTheme"

ShellRoot {
    id: root
    // Test IPC tools: qs ipc show

    IpcHandler {
        target: "theme-manager" 
        function reload(): void {
            Theme.reloadTheme()
        }
    }

    // Side-monitor bars, from ~/.config/ml4w-statusbar/config.json ->
    // {"slimBars": ["HDMI-A-2", "DP-1"]}. Entries may also be
    // {"screen": "..."} objects. Missing file or key = both side screens
    // (today's setup); an empty list = center bar only.
    property var slimScreens: ["HDMI-A-2", "DP-1"]

    // Live-apply slimBars edits: edit ~/.config/ml4w-statusbar/config.json,
    // then `qs ipc call slimbars reload` (FileView does not refire on its
    // own here; same manual pattern as the center bar's reload).
    IpcHandler {
        target: "slimbars"
        function reload(): void {
            slimConfigFile.reload()
        }
    }

    FileView {
        id: slimConfigFile
        path: Quickshell.env("HOME") + "/.config/ml4w-statusbar/config.json"
        blockLoading: true
        printErrors: false
        onLoaded: {
            try {
                const d = JSON.parse(text())
                // No key = built-in default (both side screens); the file is
                // the source of truth on every reload, not just startup.
                if (d && Array.isArray(d.slimBars))
                    root.slimScreens = d.slimBars
                        .map(e => (typeof e === "string") ? e : e.screen)
                        .filter(x => x)
                else
                    root.slimScreens = ["HDMI-A-2", "DP-1"]
            } catch (e) {
                // Unreadable config keeps the built-in default.
            }
        }
    }

    WelcomeWindow {}
    PowerWindow {}
    SidebarWindow {}
    WallpaperWindow {}
    StatusbarWindow {}
    Variants {
        model: root.slimScreens
        delegate: SlimBarWindow {
        }
    }
}