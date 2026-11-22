#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/../.." && pwd)"
mod="$root/StatusbarApp/VolumeModule.qml"
panel="$root/StatusbarApp/VolumePanel.qml"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
need() { grep -Fq -- "$1" "$2" || fail "$3"; }
need_not() { if grep -Fq -- "$1" "$2"; then fail "$3"; fi; }

need 'id: dwellTimer' "$mod" "dwellTimer must exist"
need 'interval: 120' "$mod" "volume hover should open after 120ms dwell"
need_not 'interval: 250' "$mod" "old 250ms dwell must be removed"

need 'id: closeTimer' "$mod" "closeTimer must exist"
need 'interval: 80' "$mod" "volume close should be near-instant (short grace, no 1000ms linger)"
need_not 'interval: 1000' "$mod" "old 1000ms close linger must be removed"
need_not 'interval: 0' "$mod" "0ms close breaks icon-to-panel handoff; use a short grace instead"

# Panel hover must cover full panel bounds (including inset/padding) for icon↔panel handoff.
need 'HoverHandler' "$panel" "panel must handle hover to cancel/schedule close"
need 'panel.volumeModule.cancelClose()' "$panel" "panel hover must cancel close"
need 'panel.volumeModule.scheduleClose()' "$panel" "panel leave must schedule close"
# Hover handling should not be limited to the inner card only.
if grep -n 'HoverHandler' "$panel" | head -n1 | grep -Fq 'card'; then
  fail "panel hover handling must cover full panel bounds, not card-only"
fi

printf 'PASS: volume hover timing/combined-area close contract\n'
