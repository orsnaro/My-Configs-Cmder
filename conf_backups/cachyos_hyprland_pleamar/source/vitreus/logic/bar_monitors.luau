-- The Bar page of the settings: which monitors the bar shows on. pleamar reads that (`screens:` on the scene's
-- surface) only when it starts, so choosing rewrites that line of vitreus.plm and queues a restart through
-- the permanent profile's systemd owner. A helper in this service's cgroup cannot outlive its clean quit. What was
-- chosen is kept in bar.json; a chosen monitor that is not plugged in puts the bar on all of them until it is back.
return function(with_dirs)
    local B = { pref = nil, file = nil, mons = {}, busy = false, awake = false }

    local function connected(name)
        for i, m in ipairs(B.mons) do if m.name == name then return i end end
        return nil
    end
    -- Where the bar should be now: the choice, or all of them while the chosen one is away.
    local function target()
        local pref = B.pref or "all"
        if pref ~= "all" and not connected(pref) then return "all" end
        return pref
    end

    -- Tell the window gaps where the bar is (it is where the scene was started, not where it is about to go) and what is plugged in.
    local told = nil
    local function publish()
        if B.file == nil or #B.mons == 0 then return end
        local names = {}
        for _, m in ipairs(B.mons) do names[#names + 1] = m.name end
        local on = (B.file ~= "all" and connected(B.file)) and B.file or "all"
        -- The side strips mirror what is running, not what has just been chosen: a lite copy is open
        -- only while the full bar sits on some other single monitor, and All/fallback-All closes both.
        fact.bar_lite_dp1 = on ~= "all" and on ~= "DP-1"
        fact.bar_lite_hdmi = on ~= "all" and on ~= "HDMI-A-2"
        local sig = on .. "|" .. table.concat(names, ",")
        if sig == told then return end
        told = sig
        bar_fx.on, bar_fx.mons = on, names
        iris_fx.apply_hypr()
    end

    local function show()
        local pref = B.pref or "all"
        local at = pref ~= "all" and connected(pref) or nil
        fact.bar_scr = at and (at - 1) or -1
        for i = 0, 3 do
            local m = B.mons[i + 1]
            fact["bar_m." .. i .. ".on"] = m ~= nil
            if m then
                text["bar_m." .. i .. ".name"] = m.name
                text["bar_m." .. i .. ".sub"] = m.sub
            end
        end
        if B.busy then
            text.bar_msg = "Moving the bar…"
        elseif pref ~= "all" and not at and #B.mons > 0 then
            text.bar_msg = pref .. " isn't plugged in, so the bar is on every monitor until it's back."
        else
            text.bar_msg = ""
        end
    end

    local function restart(to)
        if B.busy then return end
        if to ~= "all" and not to:match("^[%w%._%-]+$") then return end
        B.busy = true
        show()
        with_dirs(function(d)
            local plm = d.conf .. "/vitreus.plm"
            -- Four copies cover the supported monitor count; a lower cap silently hid the extra bars.
            local value = to == "all" and "each max 4" or ('"' .. to .. '"')
            run("sed", { "-i", "-E", "/^    surface \\{/s/screens: [^;]*;/screens: " .. value .. ";/", plm }, function(_, code)
                if code ~= 0 then
                    B.busy = false
                    show()
                    text.bar_msg = "Couldn't change where the bar shows."
                    return
                end
                -- Queue the restart; never block waiting for the process that owns this callback to exit.
                run("systemctl", { "--user", "--no-block", "restart", "pleamar.service" }, function(_, restart_code)
                    if restart_code ~= 0 then
                        B.busy = false
                        show()
                        text.bar_msg = "Couldn't restart the bar service."
                        return
                    end
                    B.file = to
                    bar_mon.name = to
                end)
            end)
        end)
    end

    -- Put the bar where it should be, once what the file says and what is plugged in are both known. Not in the
    -- first seconds after starting, so a monitor that is still waking up does not send it back and forth.
    local function settle()
        if B.busy or B.file == nil or #B.mons == 0 then return end
        if not B.awake then return end
        local to = target()
        if to ~= B.file then restart(to) end
    end

    local function read_mons()
        hypr_monitors(4, function(out, code)
            if code ~= 0 or not out then return end
            local ok, list = pcall(json.decode, out)
            local mons = {}
            if ok and type(list) == "table" then
                for _, j in ipairs(list) do
                    local t = j.transform or 0
                    mons[#mons + 1] = { name = j.name, x = j.x or 0, y = j.y or 0, tall = t == 1 or t == 3 or t == 5 or t == 7 }
                end
            else
                -- pleamar-wm's `hyprctl monitors` is text, even with -j: "Monitor <name> (ID 1):", "2560x1440@164.83 at 1440x733" (its sizes already turned by the rotation).
                for name, body in (out .. "\n\n"):gmatch("Monitor (%S+) %(ID %d+%):\n(.-)\n\n") do
                    local w, h, x, y = body:match("(%d+)x(%d+)@[%d%.]+ at (%-?%d+)x(%-?%d+)")
                    if w then mons[#mons + 1] = { name = name, x = tonumber(x), y = tonumber(y), tall = tonumber(h) > tonumber(w) } end
                end
            end
            if #mons == 0 then return end
            table.sort(mons, function(a, b) if a.x ~= b.x then return a.x < b.x end return a.y < b.y end)
            for i, m in ipairs(mons) do
                local where = #mons == 1 and "" or (i == 1 and "left" or (i == #mons and "right" or "middle"))
                if m.tall then where = where == "" and "portrait" or (where .. ", portrait") end
                m.sub = where
            end
            B.mons = mons
            show()
            publish()
            settle()
        end)
    end

    on("bar_pick_scr", function(i)
        if B.busy then return end
        local pref = "all"
        if i >= 0 then
            local m = B.mons[math.floor(i + 0.5) + 1]
            if not m then return end
            pref = m.name
        end
        B.pref = pref
        pcall(sys.call, "files.write", "bar.json", { screens = pref })
        show()
        local to = target()
        if B.file ~= nil and to ~= B.file then restart(to) end
    end)

    local ok, saved = pcall(sys.ask, "files.read", "bar.json", "json")
    if ok and type(saved) == "table" and type(saved.screens) == "string" then B.pref = saved.screens end
    -- What this bar was started with: the `screens:` of the scene's surface.
    with_dirs(function(d)
        run("grep", { "-o", "-m1", "-E", "screens: [^;]*;", d.conf .. "/vitreus.plm" }, function(out)
            local v = (out or ""):match("screens:%s*(.-)%s*;")
            if v == nil then return end
            B.file = v:match('^"([^"]+)"') or "all"
            bar_mon.name = B.file
            if B.pref == nil then B.pref = B.file end
            show()
            publish()
            settle()
        end)
    end)
    read_mons()
    every(5000, read_mons)
    after(8000, function() B.awake = true; settle() end)
end
