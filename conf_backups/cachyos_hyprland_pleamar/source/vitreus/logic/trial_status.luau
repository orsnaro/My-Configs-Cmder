-- Trial-only bridge to the user's existing scripts; no credentials or login jobs.
return function()
    local defaults = { cpu = "CPU —", ram = "MEM —", gpu = "GPU —", vram = "VMEM —",
        weather = "Weather —", weather_icon = "cloud_off", pomo = "Pomo idle", updates = "—", keyboard = "—" }
    local months = { "JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC" }
    sys.watch("clock", function(c)
        text.trial_date_dm = string.format("%d %s", c.day, months[c.month])
    end)
    local fresh = false
    local function unavailable()
        for k, v in pairs(defaults) do text["trial_" .. k] = v end
    end
    local start
    start = function()
        spawn("vitreus-trial-status", {}, function(line)
            local ok, data = pcall(json.decode, line)
            if not ok or type(data) ~= "table" then unavailable(); return end
            fresh = true
            for k, fallback in pairs(defaults) do
                local value = data[k]
                text["trial_" .. k] = type(value) == "string" and value or fallback
            end
        end, function()
            unavailable()
            after(5000, start)
        end)
    end
    on("trial_pomo_start", function()
        run("pgrep", { "-u", "narol", "-x", "pomo" }, function(_, code)
            if code ~= 0 then exec_on_desktop("pomo") end
        end)
    end)
    on("trial_pomo_stop", function() run("pkill", { "-u", "narol", "-x", "pomo" }, function() end) end)
    on("trial_weather_refresh", function() run("hypr-weather", {}, function() end) end)
    on("trial_keyboard_switch", function() run("hypr-switch-xkblayout", {}, function() end) end)
    on("trial_updates_open", function() exec_on_desktop("kitty --class dotfiles-floating -e arch-update") end)
    on("trial_mic_toggle", function() sys.call("audio.input_mute") end)
    on("trial_volume_toggle", function() sys.call("audio.mute") end)
    local function open_subview(name)
        -- Changing the native panel resets panel_sub in the renderer first.
        after(30, function()
            if fact.panel == "controls" then fact.panel_sub = name end
        end)
    end
    on("trial_power_open", function() open_subview("powview") end)
    on("trial_alerts_open", function() open_subview("notifview") end)
    unavailable()
    start()
    every(10000, function()
        if not fresh then unavailable() end
        fresh = false
    end)
    every(1800000, function() run("hypr-weather", {}, function() end) end)
    --  The workspace app glyphs: the app of each workspace's most recent window, drawn beside the number in
    --  the bar (and on each model row past the five). Event-driven: the compositor's window events on the bar's
    --  unix socket are debounced into a single `hyprctl clients` read, so nothing here ever polls.
    local ws_glyphs = {
        ["brave-browser"] = "language", brave = "language", firefox = "language", librewolf = "language",
        ["google-chrome"] = "language", chromium = "language",
        kitty = "terminal", ["quake-kitty"] = "terminal", alacritty = "terminal", wezterm = "terminal",
        foot = "terminal", ghostty = "terminal", konsole = "terminal", xterm = "terminal",
        ["org.gnome.terminal"] = "terminal", ["org.kde.konsole"] = "terminal",
        ["md.obsidian.obsidian"] = "edit_note",
        ["net.lutris.lutris"] = "sports_esports", lutris = "sports_esports", steam = "sports_esports",
        thunderbird = "mail", betterbird = "mail", ["org.mozilla.thunderbird"] = "mail", evolution = "mail",
        code = "code", ["code-oss"] = "code", codium = "code", zed = "code", ["dev.zed.zed"] = "code",
        vlc = "play_circle", mpv = "movie", ["io.mpv.mpv"] = "movie",
        spotify = "music_note", ["com.spotify.client"] = "music_note",
        discord = "forum", ["org.telegram.desktop"] = "send", telegram = "send",
        nautilus = "folder", ["org.gnome.nautilus"] = "folder", dolphin = "folder", thunar = "folder",
        ["libreoffice-writer"] = "description", ["libreoffice-calc"] = "table",
        ["libreoffice-impress"] = "slideshow",
        gimp = "brush", ["org.gimp.gimp"] = "brush", inkscape = "draw", blender = "view_in_ar",
        obs = "videocam", ["com.obsproject.studio"] = "videocam",
    }
    --  The main bar's fixed glyph per workspace. The side strips keep the dynamic app glyph above.
    local ws_static_icons = {
        "home", "folder", "language", "edit_note", "forum",
        "mail", "terminal", "dashboard", "sports_esports",
    }
    local function ws_static_icon(id)
        return ws_static_icons[id] or "apps"
    end
    --  The range still reaches at least nine; the bar decides which ids keep their fixed glyph while empty.
    --  The scene's model holds this many rows. It bounds the rendered list, never a workspace id: the scan
    --  stops here so an arbitrarily large id cannot spin it. Past 64 visible rows we keep the first 63 plus a
    --  higher active workspace in the final slot instead of mirroring QS's unbounded list: an honest, model-bound
    --  limitation, not full parity.
    local ws_capacity = 64
    local ws_latest = { active = -1, list = {} }
    local ws_glyph = {}
    local function ws_class_glyph(cls)
        if ws_glyphs[cls] then return ws_glyphs[cls] end
        if cls:match("^brave%-discord%.com__")
            or cls:match("^chrome%-discord%.com__")
            or cls:match("^chromium%-discord%.com__") then
            return "forum"
        end
        return "apps"
    end
    local function ws_row_icon(id, occupied)
        if not occupied then return "crop_square" end
        local icon = ws_glyph[id]
        return icon and icon ~= "" and icon or "apps"
    end
    --  Build the switcher's rows: ascending ids, dense zero-based slots, the cached glyph and occupancy of each.
    local function ws_publish()
        local occupied, present = {}, {}
        for _, d in ipairs(ws_latest.list or {}) do
            local id = tonumber(d.id)
            if id and id >= 1 then
                present[id] = true
                if (tonumber(d.windows) or 0) > 0 then occupied[id] = true end
            end
        end
        local active = tonumber(ws_latest.active)
        if not active or active < 1 then active = -1 end
        local max_id = 9
        for id in pairs(present) do if id > max_id then max_id = id end end
        --  A focused workspace the service leaves out still has to be on screen.
        if active > max_id then max_id = active end
        local rows, slot, id = {}, 0, 1
        while id <= max_id and #rows < ws_capacity do
            rows[#rows + 1] = { id = id, slot = slot, icon = ws_row_icon(id, occupied[id]),
                static_icon = ws_static_icon(id), occupied = occupied[id] or false }
            slot = slot + 1
            id = id + 1
        end
        --  A focused workspace past the last retained row takes that final slot, keeping the list dense and ascending.
        if active >= 1 and active <= max_id and rows[#rows].id < active then
            rows[#rows] = { id = active, slot = #rows - 1, icon = ws_row_icon(active, occupied[active]),
                static_icon = ws_static_icon(active), occupied = occupied[active] or false }
        end
        model.trial_workspaces = rows
    end
    local ws_pending = 0
    local function ws_refresh()
        run("hyprctl", { "clients" }, function(out, code)
            if code ~= 0 then return end
            local best, best_id = {}, {}
            local current
            local function take(w)
                if not w or w.mapped ~= "1" then return end
                local n = tonumber((w.workspace or ""):match("^(-?%d+)"))
                if not n or n < 1 then return end
                --  The window used most recently on a workspace is the one worth showing there.
                local id = tonumber(w.focusHistoryID or "")
                if id and (best_id[n] == nil or id < best_id[n]) then
                    best_id[n], best[n] = id, (w.class or ""):lower()
                end
            end
            for line in (out or ""):gmatch("[^\n]+") do
                if line:match("^Window %x+ %->") then
                    take(current)
                    current = {}
                elseif current then
                    local key, value = line:match("^%s+([%w]+): ?(.*)$")
                    if key then current[key] = value end
                end
            end
            take(current)
            local glyph = {}
            for n, cls in pairs(best) do glyph[n] = ws_class_glyph(cls) end
            ws_glyph = glyph
            --  The legacy per-workspace text props stay in step through the tenth; past that the rows carry it.
            for n = 1, 10 do
                local g = glyph[n] or ""
                if text["ws_app" .. n] ~= g then text["ws_app" .. n] = g end
            end
            ws_publish()
        end)
    end
    --  Several events in one moment (a window moving over three workspaces) fold into one read: only the
    --  newest of the watchers survives to run it.
    local function ws_soon()
        ws_pending = ws_pending + 1
        local mine = ws_pending
        after(400, function() if mine == ws_pending then ws_refresh() end end)
    end
    sys.watch("workspaces", function(w)
        local src = w or {}
        ws_latest = { active = src.active, list = src.list or {} }
        ws_publish()
        ws_soon()
    end)
    ws_publish()
    --  Follow window AND monitor focus: an empty output need not send activewindow.
    --  The opening click gets a moment's grace so it cannot dismiss its own drawer.
    local panel_guard = false
    on("panel_opened", function()
        panel_guard = true
        after(400, function() panel_guard = false end)
    end)
    --  The side strips' dropdowns open from a press on a layer surface too, so they get the same grace.
    local side_guard = false
    local function side_opened(v)
        if v == true or v == 1 then
            side_guard = true
            after(400, function() side_guard = false end)
        end
    end
    on("fact:lite_vol_dp1", side_opened)
    on("fact:lite_vol_hdmi", side_opened)
    local function dismiss_panel(monitor_changed)
        --  A window or monitor focus move closes the side dropdowns as it closes the drawer.
        if (fact.lite_vol_dp1 == true or fact.lite_vol_hdmi == true) and not side_guard then
            fact.lite_vol_dp1 = false
            fact.lite_vol_hdmi = false
        end
        --  The launcher is the exception: focus follows the mouse across windows and monitors, so it stays
        --  until its click-away backdrop, Escape/Ctrl+W, its cross, the toggle, or a chosen result.
        if fact.panel == "launch" then return end
        if (fact.panel == nil or fact.panel == "none")
            and not (monitor_changed and (fact.wp_picker_open or fact.ov_open or fact.dash_open)) then return end
        if panel_guard then return end
        fact.panel = "none"
        fact.wp_picker_open = false
        fact.ov_open = false
        fact.dash_open = false
    end

    --  The compositor's own socket: a window opening, closing, moving or taking the focus schedules the same
    --  debounced read. The reader re-arms itself if the socket ever drops.
    local function ws_reader()
        run("printenv", { "HYPRLAND_INSTANCE_SIGNATURE" }, function(sig)
            sig = (sig or ""):gsub("%s+$", "")
            if sig == "" then return end
            run("printenv", { "XDG_RUNTIME_DIR" }, function(runtime)
                runtime = (runtime or ""):gsub("%s+$", "")
                if runtime == "" then return end
                spawn("socat",
                    { "-u", "UNIX-CONNECT:" .. runtime .. "/hypr/" .. sig .. "/.socket2.sock", "-" },
                    function(line)
                        local ev = line:match("^(%w+)>>")
                        if ev == "openwindow" or ev == "closewindow" or ev == "movewindow" or ev == "activewindow" then
                            ws_soon()
                        end
                        if ev == "activewindow" or ev == "focusedmon" or ev == "focusedmonv2" then
                            dismiss_panel(ev ~= "activewindow")
                        end
                    end,
                    function() after(3000, ws_reader) end)
            end)
        end)
    end
    after(1500, ws_reader)
    after(2000, ws_soon)
end
