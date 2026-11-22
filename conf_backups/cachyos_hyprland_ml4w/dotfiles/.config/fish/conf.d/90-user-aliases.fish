# ============================================================
# Personal aliases
# ============================================================

# Git
alias g='git'
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

# --- CP study (Linux port of Win11 cmder user_aliases.cmd) ---
# Win source: ~/Projects/My-Configs-Cmder/cmder/config/user_aliases.cmd
#   cporg=cdv C:\Users\%USERNAME%\repo_CPP_COMP_study
# Linux repo lives at /shared_across_des/repos/cp_study (has CP.cpp/Cp.cs/Cp.sql/cp.py + done_probs/todo_probs)
alias cporg='cd /shared_across_des/repos/cp_study'

# Win: doneprob=save_N_push_solved_prob.bat cpp | csdoneprob=... cs | pydoneprob=... py
# (sqldoneprob did NOT exist on Win — created here as sql equivalent)
alias doneprob='save_N_push_solved_prob cpp'
alias csdoneprob='save_N_push_solved_prob cs'
alias pydoneprob='save_N_push_solved_prob py'
alias sqldoneprob='save_N_push_solved_prob sql'

# Win: addtodo=add_todo_prob.bat cpp | csaddtodo=... cs | pyaddtodo=... py
# (sqladdtodo did NOT exist on Win — created here as sql equivalent)
alias addtodo='add_todo_prob cpp'
alias csaddtodo='add_todo_prob cs'
alias pyaddtodo='add_todo_prob py'
alias sqladdtodo='add_todo_prob sql'
