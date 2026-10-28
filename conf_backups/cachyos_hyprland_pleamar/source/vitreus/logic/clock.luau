-- Settings > Widgets: first the desktop clock, then (below) the desktop system monitor. The desktop clock is a scene of its own (desktopclock/) and keeps its settings in its own desktopclock.json: this page asks it for
-- them when it opens (`pleamar --say desktopclock "get ..."`) and tells it each change (`fact`), and it saves them. `ck_ok` is false when it does not
-- answer, which is when it is not running; the switch then starts it.
return function()
    local SIZES = { 140, 220, 280, 340 }
    local clock, monitor
    local function say(cmd, fn) run("pleamar", { "--say", "desktopclock", cmd }, fn or function() end) end
    local function trim(s) return ((s or ""):gsub("%s+$", "")) end
    -- Which monitor shows the clock and the system monitor: their chips (the same names as the visualiser's, `cv_m.N.name`) light the one they are on.
    local cv_names = {}
    local ck_pref, sy_pref = "", ""
    local function show_wd_mons()
        local ck_at, sy_at = 0, 0
        for i, n in ipairs(cv_names) do
            if n == ck_pref then ck_at = i end
            if n == sy_pref then sy_at = i end
        end
        fact.ck_mon, fact.sy_mon = ck_at, sy_at
    end
    local function refresh()
        if clock and clock.busy() then return end
        local version = clock and clock.version()
        say_many("desktopclock", { "get shown", "get lay", "get px", "get wti", "get cli", "get where", "get h12", "get mon_name" }, function(r)
            if clock and (clock.busy() or clock.version() ~= version) then return end
            if not r then fact.ck_ok = false return end
            ck_pref = trim(r[8]):match("^[%w%._%-]+$") and trim(r[8]) or ""; show_wd_mons()
            fact.ck_ok = true
            fact.ck_on = trim(r[1]):match("true") ~= nil
            local function num(i, key) local n = tonumber(trim(r[i])); if n then fact[key] = n end end
            num(2, "ck_lay"); num(3, "ck_px"); num(4, "ck_wt"); num(5, "ck_cl")
            fact.ck_12h = trim(r[7]):match("true") ~= nil
        end)
    end
    -- The desktop system monitor (desktopsysmon/) is the same: its own scene, asked when the page opens, told each change.
    local function say_sy(cmd, fn) run("pleamar", { "--say", "desktopsysmon", cmd }, fn or function() end) end
    local function refresh_sy()
        if monitor and monitor.busy() then return end
        local version = monitor and monitor.version()
        say_many("desktopsysmon", { "get shown", "get cli", "get where", "get mon_name" }, function(r)
            if monitor and (monitor.busy() or monitor.version() ~= version) then return end
            if not r then fact.sy_ok = false return end
            sy_pref = trim(r[4]):match("^[%w%._%-]+$") and trim(r[4]) or ""; show_wd_mons()
            fact.sy_ok = true
            fact.sy_on = trim(r[1]):match("true") ~= nil
            local n = tonumber(trim(r[2])); if n then fact.sy_cl = n end
        end)
    end
    -- The chips of the clock and the system monitor are the monitors plugged in now (the order hyprctl lists them in).
    local function show_cv_mons()
        for i = 0, 3 do
            local n = cv_names[i + 1]
            fact["cv_m." .. i .. ".on"] = n ~= nil
            text["cv_m." .. i .. ".name"] = n or ""
        end
    end
    local function read_cv_mons()
        run("hyprctl", { "monitors", "-j" }, function(out, code)
            if code ~= 0 or not out then return end
            local names = {}
            local ok, list = pcall(json.decode, out)
            if ok and type(list) == "table" then
                table.sort(list, function(a, b) return (a.id or 0) < (b.id or 0) end)
                for _, m in ipairs(list) do names[#names + 1] = m.name end
            else
                -- pleamar-wm's `hyprctl monitors` is text: "Monitor <name> (ID 1):"
                for name in out:gmatch("Monitor (%S+) %(ID %d+%):") do names[#names + 1] = name end
            end
            cv_names = names
            show_cv_mons()
            show_wd_mons()
        end)
    end
    local function refresh_cv() read_cv_mons() end
    read_cv_mons()
    on("fact:set_page", function(v) if v == "pg_clock" then refresh(); refresh_sy(); refresh_cv() end end)
    -- The settings open again on the page they were left on, and the desktop editor can switch the widgets while it is showing: the page
    -- asks again when the panel opens, and while it is in view it asks (only whether they are on) every couple of seconds.
    on("fact:panel", function(v) if v == "settings" and fact.set_page == "pg_clock" then refresh(); refresh_sy() end end)
    local function refresh_shown()
        local function read(control, scene, key, ok_key)
            if control.busy() then return end
            local version = control.version()
            run("pleamar", { "--say", scene, "get shown" }, function(out, code)
                if control.busy() or control.version() ~= version then return end
                fact[ok_key] = code == 0
                if code == 0 then fact[key] = trim(out) == "true" end
            end)
        end
        read(clock, "desktopclock", "ck_on", "ck_ok")
        read(monitor, "desktopsysmon", "sy_on", "sy_ok")
    end
    every(2000, function() if fact.panel == "settings" and fact.set_page == "pg_clock" then refresh_shown() end end)

    local widget_control = require("logic/widget_control")
    clock = widget_control({ scene = "desktopclock", label = "clock",
        get_visible = function() return fact.ck_on end,
        confirm_visible = function(v) fact.ck_on = v end,
        refresh = function() refresh() end,
        status = function(message) text.ck_status = message; fact.ck_notice = message ~= "" end })
    monitor = widget_control({ scene = "desktopsysmon", label = "system monitor",
        get_visible = function() return fact.sy_on end,
        confirm_visible = function(v) fact.sy_on = v end,
        refresh = refresh_sy,
        status = function(message) text.sy_status = message; fact.sy_notice = message ~= "" end })
    on("ck_toggle", function() clock.set_visible(not clock.target()) end)
    local function pick(event, key, remote, hi)
        on(event, function(i)
            local v = math.max(0, math.min(hi, math.floor(i + 0.5)))
            clock.change(remote, "fact " .. remote .. " " .. v, function() fact[key] = v end)
        end)
    end
    pick("ck_lay_set", "ck_lay", "lay", 5)
    pick("ck_wt_set", "ck_wt", "wti", 2)
    pick("ck_cl_set", "ck_cl", "cli", 2)
    on("ck_12h_set", function(i)
        local b = i >= 0.5
        clock.change("h12", "fact h12 " .. tostring(b), function() fact.ck_12h = b end)
    end)
    on("ck_size_set", function(i)
        local v = SIZES[math.floor(i + 0.5) + 1]
        if v then clock.change("px", "fact px " .. v, function() fact.ck_px = v end) end
    end)

    -- The clock's hours, minutes and divider: each has a weight and a size (a step of a list) and a tint. The Settings page works on the one picked
    -- (`gl_sel`: 0 hours, 1 minutes, 2 divider); what the clock scene holds is read at once from its `gpack`, "w,z,c;" for each of the three.
    local WS = { 0.6, 0.8, 1, 1.25, 1.5 }
    local ZS = { 0.8, 0.9, 1, 1.1, 1.2 }
    local GP = {}
    for i = 0, 2 do GP[i] = { 1, 1, 0 } end
    local function gname(i) return ({ [0] = "h", "m", "s" })[i] end
    local function step(list, v)
        local best, bd = 3, 1e9
        for i, x in ipairs(list) do
            local d = math.abs(x - v)
            if d < bd then best, bd = i, d end
        end
        return best - 1
    end
    -- the example clock in the page draws each part with its own style: the scene's facts follow
    local function mirror()
        for i = 0, 2 do
            local n = gname(i)
            fact["g" .. n .. "w"] = GP[i][1]
            fact["g" .. n .. "z"] = GP[i][2]
            fact["g" .. n .. "c"] = GP[i][3]
        end
    end
    local function show_sel()
        mirror()
        local g = GP[fact.gl_sel] or { 1, 1, 0 }
        fact.gl_w = step(WS, g[1])
        fact.gl_z = step(ZS, g[2])
        fact.gl_c = math.max(0, math.min(4, math.floor(g[3] + 0.5)))
    end
    local function read_glyphs()
        if clock.busy() then return end
        local version = clock.version()
        say("get gpack", function(out, code)
            if clock.busy() or clock.version() ~= version then return end
            if code ~= 0 then return end
            local i = 0
            for w, z, c in trim(out):gmatch("([%d%.]+),([%d%.]+),(%d+)") do
                if i <= 2 then GP[i] = { tonumber(w) or 1, tonumber(z) or 1, tonumber(c) or 0 } end
                i = i + 1
            end
            show_sel()
        end)
    end
    local refresh_clock = refresh
    refresh = function() refresh_clock(); read_glyphs() end
    on("gl_pick", function(i)
        fact.gl_sel = math.max(0, math.min(2, math.floor(i + 0.5)))
        show_sel()
    end)
    local function set_glyph(slot, key, value)
        local i = fact.gl_sel
        local remote = "g" .. gname(i) .. key
        clock.change(remote, "fact " .. remote .. " " .. value, function()
            GP[i][slot] = value
            show_sel()
        end)
    end
    on("gl_w_set", function(j) j = math.max(0, math.min(4, math.floor(j + 0.5))); set_glyph(1, "w", WS[j + 1]) end)
    on("gl_z_set", function(j) j = math.max(0, math.min(4, math.floor(j + 0.5))); set_glyph(2, "z", ZS[j + 1]) end)
    on("gl_c_set", function(j) j = math.max(0, math.min(4, math.floor(j + 0.5))); set_glyph(3, "c", j) end)
    on("gl_reset", function()
        local i = fact.gl_sel
        local n = "g" .. gname(i)
        clock.change("reset-" .. i, { "fact " .. n .. "w 1", "fact " .. n .. "z 1", "fact " .. n .. "c 0" }, function()
            GP[i] = { 1, 1, 0 }; show_sel()
        end)
    end)
    on("gl_reset_all", function()
        clock.change("reset-all", "fact greset 1", function()
            for i = 0, 2 do GP[i] = { 1, 1, 0 } end
            show_sel()
        end)
    end)

    on("sy_toggle", function() monitor.set_visible(not monitor.target()) end)
    on("sy_cl_set", function(i)
        local v = math.max(0, math.min(2, math.floor(i + 0.5)))
        monitor.change("cli", "fact cli " .. v, function() fact.sy_cl = v end)
    end)

    on("ck_mon_set", function(i)
        local n = cv_names[math.floor(i + 0.5)]
        if not n then return end
        clock.change("monitor", "text mon_name " .. n, function() ck_pref = n; show_wd_mons() end)
    end)
    on("sy_mon_set", function(i)
        local n = cv_names[math.floor(i + 0.5)]
        if not n then return end
        monitor.change("monitor", "text mon_name " .. n, function() sy_pref = n; show_wd_mons() end)
    end)
end
