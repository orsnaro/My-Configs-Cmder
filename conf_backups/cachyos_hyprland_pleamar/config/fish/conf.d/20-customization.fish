# -----------------------------------------------------
# CUSTOMIZATION
# -----------------------------------------------------

# -----------------------------------------------------
# Prompt
# -----------------------------------------------------
# Oh My Posh places the active venv after Git; avoid a duplicate leading prefix.
set --global --export VIRTUAL_ENV_DISABLE_PROMPT 1
# Expose Fish's live terminal width to the adaptive path template.
set --global --export COLUMNS $COLUMNS
eval "$($HOME/.local/bin/oh-my-posh init fish --config $HOME/.config/ohmyposh/screenshot.omp.json)"

function __user_prompt_resize --on-variable COLUMNS
    # Refresh Oh My Posh's cache and request a redraw for the new width.
    set --global _omp_new_prompt 1
    if status is-interactive
        commandline --function repaint
    end
end

# Previous theme remains available at $HOME/.config/ohmyposh/zen-box.toml.
# eval "$($HOME/.local/bin/oh-my-posh init fish --config $HOME/.config/ohmyposh/EDM115-newline.omp.json)"
