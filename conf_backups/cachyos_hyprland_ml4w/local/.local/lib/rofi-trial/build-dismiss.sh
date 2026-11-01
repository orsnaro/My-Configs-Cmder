#!/usr/bin/env bash
set -euo pipefail
here=$(dirname -- "$(readlink -f -- "$0")")
build=$(mktemp -d "$here/.dismiss-build-XXXXXXXX")
trap 'rm -f -- "$build"/*.c "$build"/*.h "$build/guard"; rmdir -- "$build"' EXIT
protocols=$(pkg-config --variable=pkgdatadir wayland-protocols)
wayland-scanner client-header "$here/protocols/wlr-layer-shell-unstable-v1.xml" "$build/wlr-layer-shell-client.h"
wayland-scanner private-code "$here/protocols/wlr-layer-shell-unstable-v1.xml" "$build/wlr-layer-shell.c"
wayland-scanner client-header "$protocols/stable/viewporter/viewporter.xml" "$build/viewporter-client.h"
wayland-scanner private-code "$protocols/stable/viewporter/viewporter.xml" "$build/viewporter.c"
wayland-scanner private-code "$protocols/stable/xdg-shell/xdg-shell.xml" "$build/xdg-shell.c"
read -r -a flags <<< "$(pkg-config --cflags --libs wayland-client)"
cc -std=c11 -O2 -Wall -Wextra -Werror -Wno-unused-parameter -I"$build" \
    "$here/dismiss-guard.c" "$build/wlr-layer-shell.c" "$build/viewporter.c" "$build/xdg-shell.c" \
    "${flags[@]}" -o "$build/guard"
chmod 755 "$build/guard"
mv -- "$build/guard" "$here/dismiss-guard"
