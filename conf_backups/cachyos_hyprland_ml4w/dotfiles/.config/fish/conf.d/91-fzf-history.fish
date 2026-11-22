if not status is-interactive; or not command -q fzf
    return
end

set -gx FZF_CTRL_R_OPTS (string join ' ' -- \
    '--height=40% --min-height=10 --layout=reverse --border=rounded --padding=0,1' \
    '--info=inline-right --with-nth=3..' \
    "--prompt='history> ' --border-label=' Command history '" \
    "--header='Enter: insert | Esc: cancel | Ctrl+R: sort'" \
    '--color=dark,fg:#dee3e5,bg:#0f1416,fg+:#f0f4f8,bg+:#243b45,hl:#84d2e6,hl+:#84d2e6' \
    '--color=border:#84d2e6,prompt:#84d2e6,pointer:#84d2e6,marker:#a6e3a1,info:#b2cbd2,header:#b2cbd2,spinner:#84d2e6')

# Command-scoped overrides also shadow globals inside the setup function.
# Use bindings-only setup so Ctrl+T, Alt+C and Shift+Tab stay unchanged.
FZF_CTRL_T_COMMAND= FZF_ALT_C_COMMAND= fzf_key_bindings
