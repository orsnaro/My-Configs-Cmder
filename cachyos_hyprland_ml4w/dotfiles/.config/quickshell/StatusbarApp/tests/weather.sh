#!/usr/bin/env bash
set -euo pipefail
# Weather module contract: Alexandria temp + condition left of the clock.
mod="$HOME/.config/quickshell/StatusbarApp/WeatherModule.qml"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
need() { grep -q "$2" "$1" || fail "$3"; }

[[ -x "$HOME/.local/bin/hypr-weather" ]] || fail "hypr-weather fetch script missing"
[[ -f "$HOME/.cache/weather.json" ]] || fail "weather cache missing (run hypr-weather)"
python3 -c "import json;d=json.load(open('$HOME/.cache/weather.json'));assert 'temp' in d and 'code' in d" \
    || fail "cache must carry temp and code"
[[ -f "$mod" ]] || fail "WeatherModule.qml missing"
need "$mod" "weather.json" "WeatherModule must read the weather cache"
need "$HOME/.config/quickshell/StatusbarApp/StatusbarWindow.qml" "cWeather" "StatusbarWindow must register cWeather"
need "$HOME/.config/quickshell/StatusbarApp/StatusbarWindow.qml" '"center": \["weather", "clock"' "weather must sit just left of the clock"
printf 'PASS: weather module wired\n'
