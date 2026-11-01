#!/usr/bin/env bash
set -euo pipefail
here=$(dirname -- "$(readlink -f -- "$0")")
temporary=$(mktemp "$here/.smart-build-XXXXXXXX.so")
trap 'rm -f -- "$temporary"' EXIT
# pkg-config returns toolchain arguments, never launcher query text.
read -r -a flags <<< "$(pkg-config --cflags --libs glib-2.0 gio-2.0 gmodule-2.0 cairo pango libqalculate)"
c++ -std=c++20 -O2 -fPIC -shared -Wall -Wextra -Werror -Wno-missing-field-initializers \
    -I/usr/include/rofi "$here/smart.cpp" "${flags[@]}" -o "$temporary"
chmod 755 "$temporary"
mv -- "$temporary" "$here/smart.so"
bash "$here/build-dismiss.sh"
