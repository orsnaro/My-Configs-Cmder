#!/usr/bin/env bash
# Merge into a fresh CachyOS + ML4W 2.16 install, preserving copied permissions.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
DOT="$REPO_DIR/dotfiles/.config"
LOC="$REPO_DIR/local/.local"
DRY_ARGS=()
if [[ "${1:-}" == "--dry-run" ]]; then DRY_ARGS=(--dry-run); fi

restore_one() { # $1=src $2=dest
  if [[ -d "$1" ]]; then
    rsync -aL --mkpath --itemize-changes --exclude='.git/' "${DRY_ARGS[@]}" "$1/" "$2/"
  fi
}
for name in hypr kitty quickshell waybar rofi swaync ml4w ml4w-dock ml4w-statusbar fastfetch fish matugen walker elephant ohmyposh hyprland-kde-overrides gtk-3.0 gtk-4.0 gcal; do
  restore_one "$DOT/$name" "$HOME/.config/$name"
done
restore_one "$LOC/bin" "$HOME/.local/bin"
for name in ml4w-dock quickshell-overview ml4w-dotfiles-settings applications; do
  restore_one "$LOC/share/$name" "$HOME/.local/share/$name"
done
# Recreate the launcher without embedding this machine's absolute HOME path.
if [[ -f "$LOC/share/ml4w-dock/bin/ml4w-dock" && ! -e "$HOME/.local/bin/ml4w-dock" && ! -L "$HOME/.local/bin/ml4w-dock" ]]; then
  if [[ ${#DRY_ARGS[@]} -gt 0 ]]; then
    echo 'Would create ~/.local/bin/ml4w-dock -> ../share/ml4w-dock/bin/ml4w-dock'
  else
    mkdir -p "$HOME/.local/bin"
    ln -s ../share/ml4w-dock/bin/ml4w-dock "$HOME/.local/bin/ml4w-dock"
  fi
fi

if [[ ${#DRY_ARGS[@]} -eq 0 ]]; then
  echo "--- kitty system patch (needs sudo, kitty 0.49.2) ---"
  cat "$DOT/kitty/KITTY_PATCH_STATE.txt" 2>/dev/null || true
  read -r -p "Re-apply kitty patch with sudo now? [y/N] " ans || ans="N"
  if [[ "$ans" == [yY]* ]]; then sudo bash ~/.config/kitty/apply-native-patch.sh; fi
  echo "Done. Run: hyprctl reload (then relog for dock/quickshell)."
else
  echo "DRY-RUN done, no changes made."
fi
