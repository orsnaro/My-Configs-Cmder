function e --wraps=nautilus --description 'Open nautilus in background'
    command nautilus --new-window $argv >/dev/null 2>&1 &
    disown
end
