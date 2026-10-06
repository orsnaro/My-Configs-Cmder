#!/usr/bin/env bash
set -euo pipefail
# Volume dropdown contract: hover shows sinks + slider on all 3 bars.
# Click (pavucontrol) / right-click (mute) / wheel (step) stay as-is.
app="$HOME/.config/quickshell/StatusbarApp"
shell="$HOME/.config/quickshell/shell.qml"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
need() { grep -q "$2" "$1" || fail "$3"; }

[[ -f "$app/VolumeModule.qml" ]] || fail "VolumeModule.qml missing"
[[ -f "$app/VolumePanel.qml" ]] || fail "VolumePanel.qml missing"

# Panel lists output sinks and switches default + slider for level.
need "$app/VolumePanel.qml" "Pipewire" "VolumePanel must use Pipewire service"
need "$app/VolumePanel.qml" "isSink" "VolumePanel must list sink nodes"
need "$app/VolumePanel.qml" "preferredDefaultAudioSink" "VolumePanel must switch default sink"
need "$app/VolumePanel.qml" "Slider" "VolumePanel must have a volume slider"
need "$app/VolumePanel.qml" "audio.volume" "VolumePanel slider must drive sink volume"
need "$app/VolumePanel.qml" "cancelClose" "VolumePanel hover must cancel hide (gap crossable)"
need "$app/VolumePanel.qml" "scheduleClose" "VolumePanel leave must re-arm hide"
grep -q "hiddenY" "$app/VolumePanel.qml" && fail "VolumePanel must not slide (hover steal loop)"

# Module keeps click/wheel contract and gains hover dwell like Media/CPU.
# Click map (swapped): left = mute, right = pavucontrol.
need "$app/VolumeModule.qml" "pavucontrol" "VolumeModule right-click must open pavucontrol"
need "$app/VolumeModule.qml" "toggleMute" "VolumeModule left-click must mute"
need "$app/VolumeModule.qml" "onWheel" "VolumeModule wheel must still step volume"
need "$app/VolumeModule.qml" "volumeOpenRequested" "VolumeModule must request dropdown open"
need "$app/VolumeModule.qml" "volumeCloseRequested" "VolumeModule must request dropdown close"
need "$app/VolumeModule.qml" "dwellTimer" "VolumeModule must open dropdown after hover dwell"
need "$app/VolumeModule.qml" "interval: 250" "VolumeModule dwell must be 250ms"
need "$app/VolumeModule.qml" "closeTimer" "VolumeModule must auto-hide dropdown on leave"
need "$app/VolumeModule.qml" "cancelClose" "VolumeModule must expose cancelClose for panel hover"
need "$app/VolumeModule.qml" "scheduleClose" "VolumeModule must expose scheduleClose for panel hover"

# Center bar owns the panel state and places it under the volume pill.
need "$app/StatusbarWindow.qml" "volumeOpen" "StatusbarWindow must own volume panel state"
need "$app/StatusbarWindow.qml" "VolumePanel" "StatusbarWindow must place VolumePanel"
need "$app/StatusbarWindow.qml" "volumeRef" "StatusbarWindow must track volume pill for anchoring"

# Slim side bars reuse the same panel so all 3 screens match.
need "$app/SlimBarWindow.qml" "VolumePanel" "SlimBarWindow must host VolumePanel (all 3 screens)"
need "$app/SlimBarWindow.qml" "volumeOpen" "SlimBarWindow must own volume panel state"

# Click map: right-click opens mixer, left-click mutes (exact swap).
grep -A2 "Qt.RightButton" "$app/VolumeModule.qml" | grep -q "activate" \
    || fail "VolumeModule right-click must call activate() (pavucontrol)"
# Order: logo left next to launcher; right ends keyboard, volume, power.
python3 - "$app/StatusbarWindow.qml" "$app/config.json" <<'PY' || exit 1
import re, sys, pathlib
for p in sys.argv[1:]:
    t = pathlib.Path(p).read_text()
    m = re.search(r'"right":\s*\[([^\]]+)\]', t)
    assert m, f'{p}: missing right module list'
    order = re.findall(r'"(\w+)"', m.group(1))
    assert order == ["cpu", "mem", "updates", "battery", "powerprofile",
                     "systemtray", "volume", "keyboard", "power"], \
        f'{p}: right must be cpu,mem,updates,battery,powerprofile,systemtray,volume,keyboard,power, got {order}'
    m2 = re.search(r'"left":\s*\[([^\]]+)\]', t)
    assert m2, f'{p}: missing left module list'
    left = re.findall(r'"(\w+)"', m2.group(1))
    assert left == ["launcher", "logo", "workspaces", "media"], \
        f'{p}: left must be launcher,logo,workspaces,media, got {left}'
PY
# Slider must match the theme (custom groove + handle, not default Controls look).
need "$app/VolumePanel.qml" "handle:" "Volume slider must define a themed handle"
need "$app/VolumePanel.qml" "volSlider.pressed" "Volume slider handle must react to press"
printf 'PASS: volume dropdown wired on all bars\n'
