import Quickshell
import QtQuick
import "StatusbarApp"

ShellRoot {
    QtObject { id: window; property string title: "Terminal" }
    Item {
        width: 1000
        height: 40
        Rectangle { id: center; x: 420; width: 160; height: 30 }
        Row {
            id: left
            x: 16
            spacing: 14
            Rectangle { id: workspaces; width: 100; height: 30 }
            FocusedTitleModule {
                id: focused
                toplevel: window
                availableWidth: Math.max(0, center.x - left.x - workspaces.width - left.spacing - 20)
            }
        }
        Timer {
            interval: 100
            running: true
            onTriggered: {
                function check(ok, message) {
                    if (!ok) throw new Error(message)
                }
                try {
                    check(focused.displayTitle === "Terminal", "initial focused title")
                    window.title = "<b>عربي — 日本語 — literal title</b>".repeat(20)
                    Qt.callLater(() => {
                        try {
                            check(focused.displayTitle === window.title, "title changes must be reactive")
                            check(focused.width <= 220, "long title must be capped")
                            check(focused.children[0].textFormat === Text.PlainText, "titles must not render markup")
                            check(focused.children[0].elide === Text.ElideRight, "long title must elide")
                            workspaces.width = 350
                            Qt.callLater(() => {
                                try {
                                    check(left.x + focused.x + focused.width <= center.x - 20, "title must shrink before centered clock")
                                    focused.toplevel = null
                                    check(focused.collapsed && focused.implicitWidth === 0, "desktop must collapse title")
                                    focused.toplevel = window
                                    window.title = ""
                                    check(focused.collapsed, "empty title must collapse")
                                    console.log("PASS: reactive plain title and constrained layout")
                                    Qt.quit()
                                } catch (error) { console.error("FAIL:", error.message); Qt.exit(1) }
                            })
                        } catch (error) { console.error("FAIL:", error.message); Qt.exit(1) }
                    })
                } catch (error) { console.error("FAIL:", error.message); Qt.exit(1) }
            }
        }
    }
}
