//@ pragma UseQApplication
// Regression test for the shell-local tray icon overlay.
//
// The bar draws tray icons and QsMenuAnchor draws menu entries through
// Quickshell.iconPath(), whose image provider substitutes a black/purple
// checkerboard and logs `Could not load icon ...` when a name is missing
// (see src/core/iconimageprovider.cpp in Quickshell 0.3.2). A missing name
// therefore stays Image.Ready, so this test checks both hasThemeIcon() and a
// real Image load; tray_icons.sh also rejects the checkerboard warning.
//
// Names below are Blueman's tray states plus every icon-name currently
// exported by the live applet menu, read without activating anything:
//   gdbus/busctl com.canonical.dbusmenu.GetLayout on org.blueman.Tray
//   /org/blueman/sni/menu (captured 2026-10-29).
import Quickshell
import QtQuick

Window {
    id: root
    visible: false
    width: 64
    height: 64

    // blueman-tray + normal/active/disabled tray states, then live menu icons.
    readonly property var requiredNames: [
        "blueman-tray",
        "bluetooth-symbolic",
        "blueman-active",
        "blueman-disabled",
        "bluetooth-disabled-symbolic",
        "blueman-send-symbolic",
        "document-open-recent-symbolic",
        "audio-headset",
        "document-properties-symbolic",
        "application-x-addon-symbolic",
        "help-about-symbolic",
        "application-exit-symbolic",
        "edit-find-symbolic"
    ]

    // Unrelated tray icons must keep coming from the inherited theme.
    readonly property var inheritedNames: [
        "network-wireless-symbolic",
        "network-wired",
        "steam",
        "kdeconnect",
        "audio-card-symbolic",
        "network-workgroup",
        "blueman-serial"
    ]

    readonly property var sizes: [16, 18]
    property int ticks: 0
    readonly property int timeoutTicks: 60

    Column {
        id: iconColumn
        Repeater {
            id: images
            model: {
                const out = []
                for (const name of root.requiredNames)
                    for (const size of root.sizes)
                        out.push({ iconName: name, iconSize: size })
                for (const name of root.inheritedNames)
                    out.push({ iconName: name, iconSize: 18 })
                return out
            }

            delegate: Image {
                required property var modelData
                readonly property string iconName: modelData.iconName
                readonly property int iconSize: modelData.iconSize

                width: iconSize
                height: iconSize
                sourceSize.width: iconSize
                sourceSize.height: iconSize
                fillMode: Image.PreserveAspectFit
                // Unchecked URL on purpose: this mirrors SystemTrayModule/
                // QsMenuAnchor and surfaces the image provider warning.
                source: Quickshell.iconPath(iconName)
            }
        }
    }

    function settled(): bool {
        if (ticks < 2)
            return false
        for (let i = 0; i < images.count; i++) {
            const img = images.itemAt(i)
            if (!img || img.status === Image.Loading || img.status === Image.Null)
                return false
        }
        return true
    }

    function evaluate(): void {
        let failures = 0
        const fail = msg => {
            failures++
            console.error("FAIL: " + msg)
        }

        for (const name of root.requiredNames) {
            if (!Quickshell.hasThemeIcon(name))
                fail("missing theme icon: " + name)
            if (Quickshell.iconPath(name, true) === "")
                fail("unresolved icon path: " + name)
        }

        for (let i = 0; i < images.count; i++) {
            const img = images.itemAt(i)
            if (img.status !== Image.Ready) {
                fail("image did not load (status " + img.status + "): "
                     + img.iconName + " @" + img.iconSize + "px")
            } else if (img.source === "") {
                fail("empty image source: " + img.iconName)
            }
        }

        for (const name of root.inheritedNames) {
            if (!Quickshell.hasThemeIcon(name))
                fail("inherited icon disappeared: " + name)
        }

        if (failures > 0) {
            console.error("FAIL: tray icon overlay: " + failures + " problem(s)")
            Qt.exit(1)
            return
        }

        console.log("PASS: blueman tray/menu icons render at 16px and 18px; inherited icons intact")
        Qt.exit(0)
    }

    Timer {
        interval: 100
        repeat: true
        running: true
        onTriggered: {
            root.ticks++
            if (root.settled() || root.ticks >= root.timeoutTicks)
                root.evaluate()
        }
    }
}
