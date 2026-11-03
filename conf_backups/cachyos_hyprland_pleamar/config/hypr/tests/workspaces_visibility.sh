#!/usr/bin/env bash
# Exercise the real WorkspacesModule QML with only Hyprland state replaced.
set -euo pipefail
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/StatusbarApp"
ln -s "$HOME/.config/quickshell/CustomTheme" "$tmp/CustomTheme"

python3 - "$HOME/.config/quickshell/StatusbarApp/WorkspacesModule.qml" "$tmp/StatusbarApp/WorkspacesModule.qml" <<'PY'
import pathlib, sys
source = pathlib.Path(sys.argv[1]).read_text()
source = source.replace('    id: wsRoot\n', '    id: wsRoot\n    property var fixture\n', 1)
source = source.replace('Hyprland.', 'wsRoot.fixture.')
pathlib.Path(sys.argv[2]).write_text(source)
PY

cat > "$tmp/shell.qml" <<'QML'
import Quickshell
import QtQuick
import "StatusbarApp"
ShellRoot {
    Item {
        QtObject {
            id: hypr
            property var focusedWorkspace: ({id: 1})
            property var monitors: ({values: [
                {name: "DP-1", activeWorkspace: {id: 7}},
                {name: "HDMI-A-2", activeWorkspace: {id: 3}}
            ]})
            property var workspaces: ({values: [
                {id: 2, toplevels: {values: []}},
                {id: 7, toplevels: {values: []}},
                {id: 9, toplevels: {values: []}}
            ]})
        }
        // The real status bar passes its older configured minimum of 5.
        WorkspacesModule { id: bar; fixture: hypr; minWorkspaces: 5 }
        function check(label, expected) {
            const got = JSON.stringify(bar.workspaceIds)
            if (got !== JSON.stringify(expected))
                throw new Error(label + " expected " + JSON.stringify(expected) + " got " + got)
        }
        function checkLabels(label, expected) {
            const labels = bar.navButtons.map(button => {
                for (let i = 0; i < button.children.length; i++)
                    if (typeof button.children[i].text === "string")
                        return button.children[i].text
                throw new Error("workspace button has no label")
            })
            if (JSON.stringify(labels) !== JSON.stringify(expected))
                throw new Error(label + " expected " + JSON.stringify(expected)
                    + " got " + JSON.stringify(labels))
        }
        Component.onCompleted: {
            // A workspace object may exist with zero windows. That is still empty.
            check("empty work, terminals and gaming", [1,3,4,5,6,8])
            hypr.focusedWorkspace = {id: 2}
            check("focused empty work", [1,2,3,4,5,6,8])
            hypr.focusedWorkspace = {id: 1}
            hypr.workspaces = {values: [
                {id: 2, toplevels: {values: [{id: "code"}]}},
                {id: 7, toplevels: {values: []}},
                {id: 9, toplevels: {values: []}}
            ]}
            check("occupied work", [1,2,3,4,5,6,8])
            hypr.workspaces = {values: [
                {id: 2, toplevels: {values: []}},
                {id: 7, toplevels: {values: []}},
                {id: 9, toplevels: {values: []}}
            ]}
            hypr.focusedWorkspace = {id: 7}
            check("focused empty terminals", [1,3,4,5,6,7,8])
            hypr.focusedWorkspace = {id: 9}
            check("focused empty gaming", [1,3,4,5,6,8,9])
            hypr.focusedWorkspace = {id: 1}
            hypr.workspaces = {values: [
                {id: 2, toplevels: {values: []}},
                {id: 7, toplevels: {values: []}},
                {id: 9, toplevels: {values: [{id: "game"}]}}
            ]}
            check("occupied gaming", [1,3,4,5,6,8,9])
            hypr.workspaces = {values: [
                {id: 2, monitor: {name: "HDMI-A-2"}, toplevels: {values: []}},
                {id: 3, monitor: {name: "HDMI-A-2"}, toplevels: {values: []}},
                {id: 4, monitor: {name: "HDMI-A-2"}, toplevels: {values: []}},
                {id: 5, monitor: {name: "HDMI-A-2"}, toplevels: {values: []}},
                {id: 6, monitor: {name: "HDMI-A-2"}, toplevels: {values: []}},
                {id: 7, monitor: {name: "DP-1"}, toplevels: {values: [{id: "kitty"}]}},
                {id: 8, monitor: {name: "HDMI-A-2"}, toplevels: {values: []}}
            ]}
            bar.monitorName = "DP-1"
            Qt.callLater(() => {
                check("right monitor workspaces", [7])
                checkLabels("right monitor labels", ["terminals"])
                bar.monitorName = "HDMI-A-2"
                Qt.callLater(() => {
                    check("HDMI monitor workspaces", [2,3,4,5,6,8])
                    checkLabels("HDMI monitor labels", ["work","search","notes","chat","mail","others"])
                    if (bar.workspaceName(10) !== "10")
                        throw new Error("unknown workspace should retain numeric label")
                    console.log("PASS: workspace labels match terminal and other monitor assignments")
                    console.log("PASS: workspace visibility reacts to occupancy and focus")
                })
            })
        }
    }
}
QML

# ShellRoot has no quit handler; stop the isolated, headless test after its marker.
set +e
output=$(timeout 5 env QT_QPA_PLATFORM=offscreen qs --no-color -p "$tmp" 2>&1)
status=$?
set -e
if [[ $status != 124 && $status != 0 ]]; then
    printf '%s\n' "$output" >&2
    exit "$status"
fi
if grep -E 'ERROR|Error:|TypeError|ReferenceError' <<< "$output" >&2; then
    printf '%s\n' "$output" >&2
    exit 1
fi
if ! grep -F 'PASS: workspace visibility reacts to occupancy and focus' <<< "$output"; then
    printf '%s\n' "$output" >&2
    exit 1
fi
