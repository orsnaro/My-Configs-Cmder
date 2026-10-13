#!/usr/bin/env bash
#                                      __   
#   ___ ____ ___ _  ___ __ _  ___  ___/ /__ 
#  / _ `/ _ `/  ' \/ -_)  ' \/ _ \/ _  / -_)
#  \_, /\_,_/_/_/_/\__/_/_/_/\___/\_,_/\__/ 
# /___/                                     
# 


ml4w_cache_folder="$HOME/.cache/ml4w/hyprland-dotfiles"

# Notifications
source "$HOME/.config/ml4w/scripts/ml4w-notification-handler"
APP_NAME="System"
NOTIFICATION_ICON="joystick"

if [ -f $HOME/.config/ml4w/settings/gamemode-enabled ]; then
  if [ -f $ml4w_cache_folder/restart-wpauto ]; then
    rm $ml4w_cache_folder/restart-wpauto
    $HOME/.config/ml4w/scripts/ml4w-wallpaper-automation --start &
  fi
  hyprctl reload
  rm $HOME/.config/ml4w/settings/gamemode-enabled
  notify_user --a "${APP_NAME}" \
            --i "${NOTIFICATION_ICON}" \
            --s "Gamemode deactivated" \
            --m "Animations and blur are now enabled."
else
  if $HOME/.config/ml4w/scripts/ml4w-wallpaper-automation --status >/dev/null 2>&1; then
    touch $ml4w_cache_folder/restart-wpauto
    $HOME/.config/ml4w/scripts/ml4w-wallpaper-automation --stop
  elif [ -f $ml4w_cache_folder/wallpaper-automation ]; then
    # Legacy marker from before pid tracking: treat as a running slideshow once.
    touch $ml4w_cache_folder/restart-wpauto
    rm -f $ml4w_cache_folder/wallpaper-automation
  fi
  hyprctl eval "activate_gamemode()"
  touch $HOME/.config/ml4w/settings/gamemode-enabled
  notify_user --a "${APP_NAME}" \
          --i "${NOTIFICATION_ICON}" \
          --s "Gamemode activated" \
          --m "Animations and blur are now disabled."
fi