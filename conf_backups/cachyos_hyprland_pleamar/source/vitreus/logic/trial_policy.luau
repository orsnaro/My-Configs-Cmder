-- Safety boundary for this disposable trial, not a security sandbox. Persistent
-- user policy stays owned by the existing desktop; ordinary bar actions work.
return function()
    local raw_run, raw_on = run, on
    local P = {}
    local function companion(s)
        return s:find("vitreus-keep", 1, true) or s:find("pleamar --scene", 1, true)
            or s:find("/vitreus/", 1, true)
    end
    function P.desktop(cmd)
        if cmd == 'pleamar --say lockscreen "fact locked true"' then
            return "$HOME/.config/pleamar/shells/vitreus/bin/vitreus-lock"
        end
        if companion(cmd) then log("trial: optional scene launch disabled"); return nil end
        return cmd
    end
    run = function(cmd, args, done)
        local joined = table.concat(args or {}, " ")
        local blocked = false
        if cmd == "hyprctl" then
            blocked = args[1] == "eval" or args[1] == "reload" or args[1] == "keyword" or args[1] == "hyprsunset"
            if joined:find("exec_cmd", 1, true) and companion(joined) then blocked = true end
        elseif cmd == "pkill" then
            blocked = joined:find("hypridle", 1, true) or joined:find("hyprsunset", 1, true)
                or joined:find("mpvpaper", 1, true) or joined:find("awww", 1, true) or joined:find("-f", 1, true)
        elseif cmd == "systemctl" then
            blocked = joined:find("hypridle", 1, true) or joined:find("hyprsunset", 1, true)
        elseif cmd == "awww" then
            blocked = args[1] ~= "query"
        elseif cmd == "setsid" then
            blocked = companion(joined)
        end
        if blocked then
            log("trial: desktop-policy command disabled", cmd)
            if done then done("", 1) end
            return
        end
        return raw_run(cmd, args, done)
    end
    on = function(event, fn)
        if event:match("^caf_") or event:match("^night_") or event:match("^wp_")
            or event:match("^disp_") or event == "bar_pick_pos" or event == "bar_pick_scr" then
            return
        end
        return raw_on(event, fn)
    end
    return P
end
