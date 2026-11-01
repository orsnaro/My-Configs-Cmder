#!/usr/bin/env bash
set -euo pipefail
here=$(dirname -- "$(readlink -f -- "$0")")
build=$(mktemp -d "$here/.dismiss-build-XXXXXXXX")
trap 'rm -f -- "$build"/*.c "$build"/*.h "$build/guard"; rmdir -- "$build"' EXIT
read -r -a flags <<< "$(pkg-config --cflags --libs json-c)"
cc -std=c11 -O2 -Wall -Wextra -Werror -Wno-unused-parameter -I"$build" \
    "$here/dismiss-guard.c" "$here/session.c" \
    "${flags[@]}" -o "$build/guard"
chmod 755 "$build/guard"
mv -- "$build/guard" "$here/dismiss-guard"
