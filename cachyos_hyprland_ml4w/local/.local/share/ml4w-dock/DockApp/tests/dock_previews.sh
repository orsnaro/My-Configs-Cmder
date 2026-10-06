#!/usr/bin/env bash
set -euo pipefail
# Dock hover previews contract: one live thumbnail card per window.
dock="$HOME/.local/share/ml4w-dock/DockApp"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
need() { grep -q "$2" "$1" || fail "$3"; }

[[ -f "$dock/DockPreviewCard.qml" ]] || fail "DockPreviewCard.qml missing"
need "$dock/DockPreviewCard.qml" "ScreencopyView" "card must use ScreencopyView"
need "$dock/DockPreviewCard.qml" "property var toplevel" "card must take a toplevel"
[[ -f "$dock/DockPreviewPopup.qml" ]] || fail "DockPreviewPopup.qml missing"
need "$dock/DockPreviewPopup.qml" "function openFor" "popup must expose openFor"
need "$dock/DockPreviewPopup.qml" "PopupWindow" "popup must be its own surface (in-window clips)"
need "$dock/DockPreviewPopup.qml" "captureAll" "popup must drive captures"
need "$dock/DockPreviewPopup.qml" "interval: 2000" "popup refresh must be 2s"
need "$dock/DockPreviewPopup.qml" "running:.*[iI]sOpen" "refresh must run only while open"
need "$dock/DockPreviewPopup.qml" "slice(0, popup.maxCards)" "popup must cap cards to fit"
need "$dock/DockItem.qml" "openPreviewsFor" "DockItem must branch to previews"
need "$dock/DockWindow.qml" "previewItem" "DockWindow must own previewItem"
need "$dock/DockWindow.qml" "DockPreviewPopup" "DockWindow must place the popup"
need "$dock/DockPreviewPopup.qml" "dropWindow" "popup must drop closed windows"
need "$dock/DockPreviewPopup.qml" "maxCards" "popup must fit vertically"
printf 'PASS: dock previews wired\n'
