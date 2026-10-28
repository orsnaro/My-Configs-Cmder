import Quickshell
import QtQuick

// Keep relative imports inside a real config root for current Quickshell.
ShellRoot {
    Loader { source: "StatusbarApp/tests/" + Quickshell.env("QS_LEGACY_FIXTURE") }
}
