-- Night mode: a warm tint over the whole screen, by hand or on a schedule (Settings > Night mode). It is done with
-- `hyprsunset`, Hyprland's own blue-light filter: a daemon that hands the compositor a colour transform, so nothing is
-- re-rendered. It is started when it is first needed (in identity, so it changes nothing by itself), and driven with
-- `hyprctl hyprsunset temperature <K>` and `identity`. Without it installed, this falls back to a Hyprland screen
-- shader (a few lines of GLSL, `hyprctl eval` to set `decoration:screen_shader`), which works but makes Hyprland rebuild
-- its buffers on every change, and flickers while a blurred panel is open. The temperature is what the slider says; the
-- schedule is here, not in hyprsunset, so the same page drives both. Only what this file set is ever cleared. Kept in
-- night.json.
return function(with_dirs)
    local WARM_K, COOL_K = 2500, 6500                 -- the slider's ends: 1 is the warmest
    local N = { on = false, auto = false, t = 0.65, start = 42, stop = 12, applied = false, last_should = nil, timer = false, sun = nil,
                boundary = nil, starting = false, applying = false, dirty = false, retry = false }
    local file = nil                                    -- the shader's path, once the data folder is known

    -- What a blackbody of `k` kelvin looks like, as a multiplier per channel (Tanner Helland's fit).
    local function kelvin(k)
        local t = k / 100
        local r, g, b
        if t <= 66 then r = 255 else r = 329.698727446 * (t - 60) ^ -0.1332047592 end
        if t <= 66 then g = 99.4708025861 * math.log(t) - 161.1195681661 else g = 288.1221695283 * (t - 60) ^ -0.0755148492 end
        if t >= 66 then b = 255 elseif t <= 19 then b = 0 else b = 138.5177312231 * math.log(t - 10) - 305.0447927307 end
        local function c(v) return math.max(0, math.min(1, v / 255)) end
        return c(r), c(g), c(b)
    end
    local function temp() return math.floor((COOL_K - N.t * (COOL_K - WARM_K)) / 100 + 0.5) * 100 end

    local function shader()
        local r, g, b = kelvin(temp())
        return string.format([[#version 300 es
precision highp float;

in vec2 v_texcoord;
uniform sampler2D tex;
out vec4 fragColor;

void main() {
    vec4 base = texture(tex, v_texcoord);
    fragColor = vec4(base.rgb * vec3(%.4f, %.4f, %.4f) * 0.8, base.a);   // the same 80%% gamma the daemon gets
}
]], r, g, b)
    end

    -- Half hours, 0 to 47, as the clock is read here.
    local function slot_text(i)
        local m = i * 30
        local h, mm = m // 60, m % 60
        local h12 = h % 12
        if h12 == 0 then h12 = 12 end
        return string.format("%d:%02d %s", h12, mm, h < 12 and "AM" or "PM")
    end

    local function in_window(now)                        -- now, in minutes; handles a window that crosses midnight
        local a, z = N.start * 30, N.stop * 30
        if a == z then return false end
        if a < z then return now >= a and now < z end
        return now >= a or now < z
    end

    local function minutes_at(now)
        local t = os.date("*t", now)
        return t.hour * 60 + t.min
    end
    local function minutes_now() return minutes_at(os.time()) end

    -- A schedule edge is identified by the local wall clock (202610272100), not by a timestamp: os.date writes local
    -- time while os.time may read a table as UTC (logic/ask.luau notes the same), and a wall-clock key needs no
    -- conversion, so neither that mismatch nor a daylight-saving change can move, invent or lose an edge. Midnight is
    -- not one of these: only the start and the stop are. A day back is a calendar day (day - 1), never 86400 seconds.
    local function boundary_key(y, mo, d, h, mi)
        return y * 100000000 + mo * 1000000 + d * 10000 + h * 100 + mi
    end

    local function days_in_month(y, m)
        if m == 2 and (y % 4 == 0 and (y % 100 ~= 0 or y % 400 == 0)) then return 29 end
        return ({ 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31 })[m]
    end

    local function latest_boundary(now)
        now = now or os.time()
        local d = os.date("*t", now)
        local now_key = boundary_key(d.year, d.month, d.day, d.hour, d.min)
        local py, pm, pd = d.year, d.month, d.day - 1
        if pd < 1 then
            pm = pm - 1
            if pm < 1 then pm = 12; py = py - 1 end
            pd = days_in_month(py, pm)
        end
        local best = nil
        for _, day in ipairs({ { d.year, d.month, d.day }, { py, pm, pd } }) do
            for _, slot in ipairs({ N.start, N.stop }) do
                local key = boundary_key(day[1], day[2], day[3], slot * 30 // 60, slot * 30 % 60)
                if key <= now_key and (best == nil or key > best) then best = key end
            end
        end
        return best
    end

    local function show()
        fact.night_on = N.on
        fact.night_auto = N.auto
        fact.night_t = N.t
        text.night_temp_text = string.format("%d K", temp())
        text.night_start_text = slot_text(N.start)
        text.night_end_text = slot_text(N.stop)
        if N.auto then
            text.night_status = N.on and ("On until " .. slot_text(N.stop)) or ("Off · starts at " .. slot_text(N.start))
        else
            text.night_status = N.on and "On" or "Off"
        end
    end

    local function save()
        pcall(sys.call, "files.write", "night.json",
            { on = N.on, auto = N.auto, t = N.t, start = N.start, stop = N.stop, boundary = N.boundary })
    end

    -- Save a new choice as this schedule period's: it holds until the next boundary. If one has gone by since the last
    -- save and the minute watch has not run yet, this period's verdict is taken now, so the tick leaves the choice alone.
    local function save_now()
        if N.auto then
            local latest = latest_boundary()
            if latest and (N.boundary == nil or latest > N.boundary) then
                N.boundary = latest
                N.last_should = in_window(minutes_now())
            end
        end
        save()
    end

    local function set_option(value)
        run("hyprctl", { "eval", 'hl.config({ decoration = { screen_shader = "' .. value .. '" } })' }, function() end)
    end

    -- hyprsunset: make sure its daemon is there (started in identity: it changes nothing until told), then call back.
    -- One start at a time: a second event while it is starting reuses it, and the callback applies whatever is current
    -- by the time it runs, so a quick On then Off cannot leave a stale tint behind.
    local function with_sunset(fn)
        run("pgrep", { "-x", "hyprsunset" }, function(_, code)
            if code == 0 then return fn() end
            if N.starting then return end
            N.starting = true
            -- Its output goes nowhere: `run` waits for the pipe it reads to close, and the daemon (which logs to stdout) kept it open for
            -- as long as it lived, so the callback never came and the first toggle after a login did nothing (the daemon was started, never told).
            -- Through `setsid` (allowed), not `sh` (not in the scene's permissions: the toggle failed with "no permission to run 'sh'"). The
            -- redirections are made by the shell setsid starts, before it becomes hyprsunset, so run's pipe closes with setsid's parent.
            run("setsid", { "-f", "sh", "-c", "exec hyprsunset -i >/dev/null 2>&1 </dev/null" }, function()
                after(300, function()
                    N.starting = false
                    fn()
                end)
            end)
        end)
    end

    -- niri has no night light of its own, but it lets a client set the gamma (wlr-gamma-control), which is what `wlsunset` does: here it is started at a
    -- fixed temperature (its two temperatures one kelvin apart: it refuses them equal; and times it needs and never uses) and stopped by the arguments it was started with, so another
    -- wlsunset of the user's is left alone. Without wlsunset installed, nothing happens (the page says so).
    local WLS = "wlsunset -t %d -T %d -S 06:00 -s 18:00 -g 1.0000"
    local WLS_KILL = "wlsunset -t [0-9]+ -T [0-9]+ -S 06:00 -s 18:00 -g 1.0000"
    local function apply_niri()
        run("pkill", { "-f", WLS_KILL }, function()
            if N.on then
                local k = temp()
                run("setsid", { "-f", "sh", "-c", "exec " .. string.format(WLS, k, k + 1) .. " >/dev/null 2>&1 </dev/null" }, function() N.applied = true end)
            else
                N.applied = false
            end
        end)
    end

    -- Make the screen agree with `N.on`. `clearing` makes an Off clear a tint this shell did not set (a restart, or a
    -- crash while the filter was on). Every deferred step reads N.on and the temperature when it actually runs.
    local function apply(clearing)
        if N.niri then return apply_niri() end
        if N.sun == nil then return end                     -- not known yet: init calls this again
        if N.sun then
            -- Serialize IPC chains: a late temperature/gamma callback must never undo a newer Off.
            if N.applying then N.dirty = true; return end
            if not N.on and not (N.applied or clearing or N.retry) then return end
            N.applying = true
            local requested_on, requested_temp = N.on, temp()
            local function finish(success)
                N.applying = false
                N.retry = not success
                if success then N.applied = requested_on end
                if N.dirty or N.on ~= requested_on or (N.on and temp() ~= requested_temp) then
                    N.dirty = false
                    apply(true)
                end
            end
            if N.on then
                with_sunset(function()
                    if not N.on then return finish(false) end
                    requested_temp = temp()
                    run("hyprctl", { "hyprsunset", "temperature", tostring(requested_temp) }, function(_, code)
                        if code ~= 0 then return finish(false) end
                        run("hyprctl", { "hyprsunset", "gamma", "80" }, function(_, gcode)
                            finish(gcode == 0)
                        end)
                    end)
                end)
            else
                run("pgrep", { "-x", "hyprsunset" }, function(_, present)
                    if present ~= 0 then return finish(true) end -- Off needs no daemon and no retry loop.
                    run("hyprctl", { "hyprsunset", "identity" }, function(_, code)
                        run("hyprctl", { "hyprsunset", "gamma", "100" }, function(_, gcode)
                            finish(code == 0 and gcode == 0)
                        end)
                    end)
                end)
            end
            return
        end
        with_dirs(function(d)
            file = d.data .. "/night.frag"
            if file:find('"', 1, true) then return end     -- it goes inside a string that Hyprland reads
            if N.on then
                pcall(sys.call, "files.write", "night.frag", shader())
                set_option(file)
                N.applied = true
            elseif N.applied or clearing then
                set_option("")
                N.applied = false
            end
        end)
    end

    -- The slider sends a stream of values: the shader is rewritten at most every 150 ms, and only while it is on.
    local function apply_soon()
        if N.timer then return end
        N.timer = true
        after(150, function() N.timer = false; if N.on then apply() end end)
    end

    local function set_on(v)
        N.on = v
        show()
        save_now()
        apply()
    end

    -- The schedule: at a boundary it puts night mode where the schedule says, and then leaves it to be changed by hand
    -- until the next one. Turning it on, or moving a time, decides at once.
    local function evaluate(now, force)
        if not N.auto then return end
        local should = in_window(now)
        local boundary = latest_boundary()
        local crossed = boundary and (N.boundary == nil or boundary > N.boundary)
        if force or crossed or N.last_should == nil or should ~= N.last_should then
            N.boundary = boundary
            N.last_should = should
            if N.on ~= should then set_on(should) else show(); save() end
        end
    end

    on("night_toggle", function() set_on(not N.on) end)
    on("night_set", function(v)                           -- absolute, for the desktop controls: 1 is On, anything else Off
        local n = tonumber(v)
        set_on(n ~= nil and n > 0)
    end)
    on("night_auto_toggle", function()
        N.auto = not N.auto
        N.last_should = nil
        if N.auto then evaluate(minutes_now(), true) else show() end
        save_now()
    end)
    on("night_temp_set", function(v)
        N.t = math.max(0, math.min(1, v))
        show()
        save_now()
        apply_soon()
    end)
    on("night_start_step", function(d)
        N.start = (N.start + (d < 0 and -1 or 1)) % 48
        show(); evaluate(minutes_now(), true); save_now()
    end)
    on("night_end_step", function(d)
        N.stop = (N.stop + (d < 0 and -1 or 1)) % 48
        show(); evaluate(minutes_now(), true); save_now()
    end)

    -- Every minute: the schedule, and that Hyprland still has the shader.
    sys.watch("clock", function(c)
        evaluate(c.hour * 60 + c.minute, false)
        if N.retry then
            -- Reuse the existing minute watch to recover slow startup/IPC failures, without another timer.
            apply(true)
        elseif N.on and N.applied then
            if N.niri then
                run("pgrep", { "-f", WLS_KILL }, function(_, code) if code ~= 0 then apply() end end)
            elseif N.sun then
                -- the daemon was stopped (it crashed, or somebody killed it): start it again with the tint
                run("pgrep", { "-x", "hyprsunset" }, function(_, code) if code ~= 0 then apply() end end)
            else
                run("hyprctl", { "getoption", "decoration:screen_shader", "-j" }, function(out)
                    if out and not out:find("night.frag", 1, true) then apply() end
                end)
            end
        end
    end)

    local ok, saved = pcall(sys.ask, "files.read", "night.json", "json")
    local now = os.time()
    if ok and type(saved) == "table" then
        N.on = saved.on == true
        N.auto = saved.auto == true
        if type(saved.t) == "number" then N.t = math.max(0, math.min(1, saved.t)) end
        if type(saved.start) == "number" then N.start = math.floor(saved.start) % 48 end
        if type(saved.stop) == "number" then N.stop = math.floor(saved.stop) % 48 end
        if type(saved.boundary) == "number" and saved.boundary >= 1e11 then N.boundary = saved.boundary end
        -- (a key is a local date and time, 202610272100; a smaller number is an epoch from the intermediate build that
        -- stored one, which cannot be compared with a key, so that file is evaluated instead)
    end
    local changed = false
    if N.auto then
        -- The saved choice was made in the period `boundary` starts: only an edge crossed since then (including while the
        -- shell was not running) lets the schedule take over. A file from before this field existed has none, so it is
        -- evaluated now. `last_should` is the schedule's own verdict, so a manual choice is left alone by the minute watch.
        local latest = latest_boundary(now)
        local mins = minutes_at(now)
        if N.boundary == nil or (latest and latest > N.boundary) then
            N.boundary = latest
            N.on = in_window(mins)
            changed = true
        end
        N.last_should = in_window(mins)
    end
    show()
    run("printenv", { "NIRI_SOCKET" }, function(o, c)       -- (asked here: a module sees the globals as they were when it was required)
        if c == 0 and (o or "") ~= "" then
            N.niri = true
            run("which", { "wlsunset" }, function(_, code)
                if code ~= 0 then text.night_status = "Needs wlsunset (pacman -S wlsunset)" return end
                if N.on then apply() end
            end)
        end
    end)
    if changed then save() end
    run("which", { "hyprsunset" }, function(_, code)
        N.sun = code == 0
        -- A shader this file left behind (the shell died with night mode on, or an earlier version used one) is taken
        -- off, so it never stacks with the new tint; anybody else's stays. Where the shader is the way, and night mode is
        -- on, it is put back by `apply` below.
        run("hyprctl", { "getoption", "decoration:screen_shader", "-j" }, function(out)
            if out and out:find("night.frag", 1, true) and (N.sun or not N.on) then set_option("") end
            -- `clearing`: a restored Off must take off a tint left by the session before, even though this one has
            -- applied nothing yet. The shader branch only clears its own file, above.
            if N.sun then apply(true) elseif N.on then apply() end
        end)
    end)
end
