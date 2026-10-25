if status is-interactive
    set -gx DIRENV_LOG_FORMAT ""
    direnv hook fish | source
end
