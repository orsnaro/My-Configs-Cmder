#!/usr/bin/env bash

# -----------------------------------------------------
# Hyprland on-demand Rofi launcher; original wiring remains in ~/.local/state/launcher-trial.
# -----------------------------------------------------
exec "$HOME/.local/bin/rofi-trial" apps "$@"
