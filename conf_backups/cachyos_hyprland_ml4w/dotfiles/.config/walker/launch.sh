#!/usr/bin/env bash
# Minimal ML4W-compatible walker launcher.
# Forwards all flags (e.g. --height 350, -m clipboard, -d) to walker.
if ! command -v walker >/dev/null 2>&1; then
    echo "walker not installed" >&2
    exit 1
fi
exec walker "$@"
