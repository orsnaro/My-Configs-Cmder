# CachyOS Hyprland ML4W configs — backup 2026-10-06

Base: CachyOS + ML4W dotfiles stable 2.16 + kitty 0.49.2
Repo: https://github.com/orsnaro/My-Configs-Cmder.git, folder `cachyos_hyprland_ml4w/`

Source live paths are symlinks:
`~/.config/hypr|kitty|waybar|quickshell|rofi|swaync` -> `~/.mydotfiles/com.ml4w.dotfiles.stable/.config/...`

Layout here mirrors $HOME:
- `dotfiles/.config/...` (hypr, kitty, quickshell, waybar, rofi, swaync, ml4w/scripts+settings, ml4w-dock, ml4w-statusbar, fastfetch, fish)
- `local/.local/bin/...` (hypr-*, qs-lazy-toggle; cemu-mousepad.py excluded)
- `local/.local/share/...` (ml4w-dock QML source, quickshell-overview, ml4w-dotfiles-settings, applications/quake-kitty.desktop)

Excluded: `ml4w/wallpapers/` (209M), `__pycache__/`, `*.pyc`, `kitty/patches/backup-*/` full copies.

Kitty source patch: `dotfiles/.config/kitty/patches/*.diff` + `apply-native-patch.sh`, requires sudo, version-pinned 0.49.2. See `KITTY_PATCH_STATE.txt`.

Dock QML (`local/.local/share/ml4w-dock/`) + quickshell QML are user-space source (plain copy, no sudo). Only kitty needs sudo re-patch.

Matugen regen (do not fight): `hypr/colors.conf`, `hypr/colors.lua`, `kitty/colors-matugen.conf`, `ml4w-dock/colors.json`.

Restore: `./RESTORE.sh [--dry-run]` — copies back, `chmod +x *.sh/*.py`, prompts for kitty sudo patch, then `hyprctl reload`.
Re-backup: `./BACKUP.sh`
