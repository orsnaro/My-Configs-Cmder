# Bluetooth tray icons: approved bounded design

## Intent and approval

The user reports an emoji-looking Bluetooth badge in the main/center-screen
Quickshell bar and black/pink missing textures in its Bluetooth dropdown.
The user selected **Fix both (Recommended)**: a monochrome Bluetooth symbol
and Quickshell-only fallback icons, preserving desktop theme and bar layout.

## Root cause

Blueman exports `blueman-tray` and GTK-style symbolic menu names.
The running shell uses `QS_ICON_THEME=breeze-dark`. Its inheritance chain
does not contain `bluetooth-symbolic`, `bluetooth-disabled-symbolic`, or
`application-x-addon-symbolic`, and only hicolor supplies `blueman-tray`
(a glossy blue badge). The send-file icon is also a dark GTK asset.

## Design

Register the `ml4w-quickshell` icon overlay from
`shared/icons/ml4w-quickshell` into `~/.local/share/icons` using a symlink.
Use `//@ pragma IconTheme ml4w-quickshell` in `shell.qml`. The overlay
inherits `breeze-dark`, leaving existing app/menu icons unchanged, and
aliases only Blueman's affected names to existing monochrome Breeze Dark
Bluetooth, plugins, and document-send SVGs. Supply normal, active, and
disabled Blueman names. Do not change Bluetooth state or menu actions.

Verify all menu and tray-state names produce real rendered pixmaps in
Quickshell, verify representative unrelated icons remain inherited,
then inspect the live bar and dropdown after a targeted shell restart.

## Reference

Quickshell 0.3 supports a shell-local IconTheme pragma; it takes effect at
process startup: https://quickshell.org/docs/v0.3.0/types/Quickshell/Quickshell/#iconPath
and https://raw.githubusercontent.com/quickshell-mirror/quickshell/v0.3.2/src/launch/launch.cpp.
