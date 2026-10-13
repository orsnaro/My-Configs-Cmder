#!/usr/bin/env bash
set -euo pipefail
# QML persistence contracts for the wallpaper panel.
qml="$HOME/.config/quickshell/WallpaperApp/WallpaperWindow.qml"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
need() { grep -q -- "$1" "$qml" || fail "$2"; }
need_not() { if grep -q -- "$1" "$qml"; then fail "$2"; fi; }

# Theming checkbox persists via a watched FileView on settings/wallpaper-theming.
need "wallpaper-theming" "checkbox must be wired to settings/wallpaper-theming"
need "watchChanges" "theming FileView must watch the settings file"
need "themingSettingFileHandler.setText" "toggling the checkbox must persist the setting"
# The checkbox must reflect the file, not a hardcoded default...
need "shouldUpdateTheming" "checkbox id must still exist"
need_not "shouldUpdateTheming.checked = true" "collapsing Advanced Options must not reset the checkbox"
# ...but a safe default when the file is missing must remain.
need "checked:" "checkbox must still declare its checked binding"

# Slideshow menu label reflects the persisted enabled state.
need "wallpaper-slideshow" "menu must be wired to settings/wallpaper-slideshow"
need "Stop Slideshow" "menu must show a Stop label when enabled"

# Explicit theming flags on manual and random actions.
need "--skip-theming" "manual/random actions must pass explicit theming flags"
need "--theming" "manual/random actions must pass explicit theming flags"

printf 'PASS: wallpaper QML persistence contracts hold\n'
