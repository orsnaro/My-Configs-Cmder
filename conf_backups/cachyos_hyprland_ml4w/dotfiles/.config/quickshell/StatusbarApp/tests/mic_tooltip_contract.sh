#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/../.." && pwd)"
mic="$root/StatusbarApp/MicModule.qml"
fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
need() { grep -Fq -- "$1" "$2" || fail "$3"; }

need 'import QtQuick.Controls' "$mic" "MicModule must import QtQuick.Controls for tooltip"
need 'ToolTip.visible' "$mic" "MicModule must show a hover tooltip"
need 'ToolTip.text' "$mic" "MicModule tooltip must have text"
need 'Math.round' "$mic" "MicModule tooltip must include computed percentage"
need '%' "$mic" "MicModule tooltip must display percent sign"
need 'onWheel' "$mic" "MicModule must preserve wheel-to-adjust volume"

printf 'PASS: mic tooltip percentage contract\n'
