#!/usr/bin/env bash
# Restore backup to a fresh CachyOS + ML4W 2.16 install. Copies back, chmods, prompts for kitty sudo patch.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
DOT="$REPO_DIR/dotfiles/.config"
LOC="$REPO_DIR/local/.local"
DRY=""
if [[ "${1:-}" == "--dry-run" ]]; then DRY="-n"; fi

restore_one() { # $1=src $2=dest
  mkdir -p "$(dirname "$2")"
  if [[ -e "$1" ]]; then rsync -aL $DRY "$1/" "$2/"; fi
}
restore_one "$DOT/hypr" ~/.config/hypr
restore_one "$DOT/kitty" ~/.config/kitty
restore_one "$DOT/quickshell" ~/.config/quickshell
restore_one "$DOT/waybar" ~/.config/waybar
restore_one "$DOT/rofi" ~/.config/rofi
restore_one "$DOT/swaync" ~/.config/swaync
restore_one "$DOT/ml4w/scripts" ~/.config/ml4w/scripts
restore_one "$DOT/ml4w/settings" ~/.config/ml4w/settings
restore_one "$DOT/ml4w-dock" ~/.config/ml4w-dock
restore_one "$DOT/ml4w-statusbar" ~/.config/ml4w-statusbar
restore_one "$DOT/fastfetch" ~/.config/fastfetch
restore_one "$DOT/fish" ~/.config/fish
mkdir -p ~/.local/bin
cp -a $DRY "$LOC/bin/"* ~/.local/bin/ 2>/dev/null || true
rsync -a $DRY "$LOC/share/ml4w-dock/" ~/.local/share/ml4w-dock/ 2>/dev/null || true
rsync -a $DRY "$LOC/share/quickshell-overview/" ~/.local/share/quickshell-overview/ 2>/dev/null || true
rsync -a $DRY "$LOC/share/ml4w-dotfiles-settings/" ~/.local/share/ml4w-dotfiles-settings/ 2>/dev/null || true
mkdir -p ~/.local/share/applications
cp -a $DRY "$LOC/share/applications/quake-kitty.desktop" ~/.local/share/applications/ 2>/dev/null || true

if [[ -z "$DRY" ]]; then
  chmod +x ~/.config/kitty/*.py ~/.config/kitty/*.sh ~/.config/hypr/scripts/*.sh ~/.local/bin/hypr-* ~/.local/bin/qs-lazy-toggle 2>/dev/null || true
  echo "--- kitty system patch (needs sudo, kitty 0.49.2) ---"
  cat "$DOT/kitty/KITTY_PATCH_STATE.txt" 2>/dev/null || true
  read -r -p "Re-apply kitty patch with sudo now? [y/N] " ans
  if [[ "$ans" == [yY]* ]]; then sudo bash ~/.config/kitty/apply-native-patch.sh; fi
  echo "Done. Run: hyprctl reload (then relog for dock/quickshell)."
else
  echo "DRY-RUN done, no changes made."
fi
