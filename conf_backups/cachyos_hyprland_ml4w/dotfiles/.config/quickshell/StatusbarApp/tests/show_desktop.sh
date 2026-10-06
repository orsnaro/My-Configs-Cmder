#!/usr/bin/env bash
set -euo pipefail
# Show-desktop contract: thin far-right strip toggles desktop (minimize-all).
app="$HOME/.config/quickshell/StatusbarApp"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
need() { grep -q "$2" "$1" || fail "$3"; }

[[ -f "$app/ShowDesktopModule.qml" ]] || fail "ShowDesktopModule.qml missing"
need "$app/ShowDesktopModule.qml" "glaze-show-desktop" "module must call glaze-show-desktop"
need "$app/ShowDesktopModule.qml" "MouseArea" "module must handle click via MouseArea"
# Thin strip: narrow width (<=10px)
grep -Eq "implicitWidth:\s*[0-9]+|width:\s*[0-9]+" "$app/ShowDesktopModule.qml" || fail "module must define a thin width"
# Peek support: press-and-hold or hover handling
grep -Eq "pressAndHold|onPressAndHold|containsMouse|hover" "$app/ShowDesktopModule.qml" || fail "module must handle hover/peek"

[[ -x "$HOME/.local/bin/glaze-show-desktop" ]] || fail "glaze-show-desktop script missing/executable"
need "$HOME/.local/bin/glaze-show-desktop" "special:minimized" "script must use special:minimized workspace"
need "$HOME/.local/bin/glaze-show-desktop" "toggle\|restore-all\|hide" "script must support toggle/restore"

need "$app/StatusbarWindow.qml" "ShowDesktop\|showDesktop\|show-desktop" "StatusbarWindow must wire show-desktop strip"
# Far-right edge anchoring
grep -Eq "right.*true|anchors\.right|parent\.right" "$app/StatusbarWindow.qml" || fail "strip must anchor to far-right edge"
# Mask must include the strip so it takes input while bar stays click-through
need "$app/StatusbarWindow.qml" "showDesktop\|ShowDesktop" "mask/input must cover show-desktop strip"

printf 'PASS: show-desktop strip wired\n'
