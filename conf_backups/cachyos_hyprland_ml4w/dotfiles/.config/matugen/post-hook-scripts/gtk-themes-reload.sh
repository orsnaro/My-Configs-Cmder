#!/usr/bin/env bash

# Keep the saved GTK choice authoritative, without flashing the opposite mode.
settings="$HOME/.config/gtk-3.0/settings.ini"
preference=""
if [[ -f "$settings" ]]; then
    preference=$(awk -F= '/^gtk-application-prefer-dark-theme=/ { print $2; exit }' "$settings")
fi
case "$preference" in
    0 | false) scheme=prefer-light ;;
    *) scheme=prefer-dark ;;
esac
gsettings set org.gnome.desktop.interface color-scheme "$scheme"
