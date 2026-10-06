# ============================================================
# Personal aliases
# ============================================================

# Git
alias log='git log --all --decorate --oneline --source'
alias loga='git log --graph --pretty="%Cred%h%Creset -%C(auto)%d%Creset %s %Cgreen(%ar) %C(bold blue)<%an>%Creset" --stat'
alias logme='git log --all --graph --decorate --stat --author="Omar Rashad" --source'
alias lognf='git log -q --all --graph --decorate --stat'

alias gs='git status'
alias stat='git status'
alias diff='git diff'
alias chk='git switch'
alias com='git commit -m'

# Terminal / tools
alias cls='clear'
alias taskmgr='btop'
alias nv='nvim'
alias os='neofetch'

# Config shortcuts
alias fishconf='micro "$HOME/.config/fish/config.fish"'
alias zshconf='micro "$HOME/.zshrc"'

# Navigation
alias user='cd $HOME'
alias repos='cd /shared_across_des/repos'

# Open default file explorer in current dir, detached (no terminal bloat)
alias e. 'nohup xdg-open . >/dev/null 2>&1 & disown'
