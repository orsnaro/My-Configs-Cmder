-- Regression: the latest night-mode choice must survive a Vitreus restart until the next schedule boundary, and a
-- boundary crossed while the shell was down must be applied at once. Runs the real module against a sandboxed scene.
-- The wrapper sets TZ=Africa/Cairo; the clock is fake (os.time() with no argument) while os.date/os.time(table) are the
-- real ones, so the daylight-saving cases are genuine.
local root = "."
local module_path = os.getenv("NIGHTMODE_MODULE") or (root .. "/logic/nightmode.luau")
local real_time, real_date = os.time, os.date

-- A local wall-clock time as a timestamp, DST included (os.time alone reads a bare table as standard time).
local function at(y, mo, d, h, mi)
    local t = real_time({ year = y, month = mo, day = d, hour = h, min = mi, sec = 0, isdst = false })
    local back = real_date("*t", t)
    if back.hour ~= h or back.min ~= mi then
        t = real_time({ year = y, month = mo, day = d, hour = h, min = mi, sec = 0, isdst = true })
    end
    return t
end

-- The module keys a saved schedule edge by the local wall clock; the tests build the same key.
local function key(y, mo, d, h, mi)
    return y * 100000000 + mo * 1000000 + d * 10000 + h * 100 + mi
end

local function copy(v)
    if type(v) ~= "table" then return v end
    local t = {}
    for k, x in pairs(v) do t[k] = copy(x) end
    return t
end

local function eq(actual, expected, message)
    assert(actual == expected, string.format("%s: expected %s, got %s", message, tostring(expected), tostring(actual)))
end

local function has(list, wanted)
    for _, v in ipairs(list) do if v == wanted then return true end end
    return false
end

local function contains(list, part)
    for _, v in ipairs(list) do if v:find(part, 1, true) then return true end end
    return false
end

local function sandbox(opts)
    opts = opts or {}
    local s = {
        env = setmetatable({ fact = {}, text = {} }, { __index = _G }),
        handlers = {}, writes = {}, timers = {}, commands = {},
        now_ms = 0, clock = nil, ipc_callbacks = {},
    }
    s.now = opts.now or at(2026, 10, 26, 22, 0)
    s.state = opts.state
    s.sun_installed = opts.sun_installed ~= false
    s.sun_running = opts.sun_running or false
    s.shader = opts.shader or ""
    s.fail = opts.fail
    local env = s.env
    env.on = function(name, fn) s.handlers[name] = fn end
    env.after = function(ms, fn) s.timers[#s.timers + 1] = { at = s.now_ms + ms, fn = fn } end
    env.os = {
        time = function(t) if t == nil then return s.now end return real_time(t) end,
        date = function(fmt, t) return real_date(fmt, t == nil and s.now or t) end,
    }
    env.sys = {
        ask = function(service, name)
            if service == "files.read" and name == "night.json" then return s.state and copy(s.state) or nil end
            return nil
        end,
        call = function(service, name, value)
            if service == "files.write" then s.writes[name] = copy(value) end
            return true
        end,
        watch = function(name, fn) if name == "clock" then s.clock = fn end end,
    }
    env.with_dirs = function(fn) fn({ data = "/data/vitreus", conf = "/config/pleamar/shells/vitreus" }) end
    env.run = function(command, args, cb)
        s.commands[#s.commands + 1] = { command = command, args = args }
        local out, code = "", 0
        if command == "which" then
            code = s.sun_installed and 0 or 1
        elseif command == "pgrep" then
            code = s.sun_running and 0 or 1
        elseif command == "setsid" then
            s.sun_running = true
            if cb then cb("", 0) end
            return
        elseif command == "hyprctl" then
            if args[1] == "getoption" then
                out = '{"str": "' .. s.shader .. '"}'
            elseif s.fail and s.fail(command, args) then
                code = 1
            end
        end
        if opts.defer_ipc and command == "hyprctl" and args[1] == "hyprsunset" then
            s.ipc_callbacks[#s.ipc_callbacks + 1] = function() if cb then cb(out, code) end end
        elseif cb then cb(out, code) end
    end
    function s.advance(ms)
        local target = s.now_ms + ms
        while true do
            table.sort(s.timers, function(a, b) return a.at < b.at end)
            local nxt = s.timers[1]
            if not nxt or nxt.at > target then break end
            table.remove(s.timers, 1)
            s.now_ms = nxt.at
            nxt.fn()
        end
        s.now_ms = target
    end
    function s.tick(y, mo, d, h, mi)
        s.now = at(y, mo, d, h, mi)
        assert(s.clock, "the module never watched the clock")
        s.clock({ hour = h, minute = mi })
    end
    function s.emit(name, value)
        assert(s.handlers[name], "no handler for " .. name)(value)
    end
    function s.finish_ipc()
        local count = 0
        while #s.ipc_callbacks > 0 do
            count = count + 1
            assert(count < 30, "IPC reconciliation never settled")
            table.remove(s.ipc_callbacks, 1)()
        end
    end
    function s.hyprsunset_calls()
        local list = {}
        for _, c in ipairs(s.commands) do
            if c.command == "hyprctl" and c.args[1] == "hyprsunset" then
                local label = tostring(c.args[2])
                if c.args[3] ~= nil then label = label .. " " .. tostring(c.args[3]) end
                list[#list + 1] = label
            end
        end
        return list
    end
    function s.last_hyprsunset()
        local list = s.hyprsunset_calls()
        return list[#list]
    end
    s.module = assert(loadfile(module_path, "t", env))()
    s.module(env.with_dirs)
    return s
end

local function state(over)
    local st = { on = true, auto = true, t = 0.8719794750213623, start = 42, stop = 12 }
    for k, v in pairs(over or {}) do st[k] = v end
    return st
end

local tests = {}

function tests.restores_the_saved_warmth_and_half_hours()
    local s = sandbox({
        now = at(2026, 10, 27, 3, 30),
        state = state({ on = true, auto = false }),
    })
    s.advance(300)
    eq(s.env.fact.night_t, 0.8719794750213623, "saved warmth")
    eq(s.env.text.night_temp_text, "3000 K", "temperature")
    eq(s.env.text.night_start_text, "9:00 PM", "start")
    eq(s.env.text.night_end_text, "6:00 AM", "end")
    eq(s.env.fact.night_auto, false, "automatic")
    eq(s.env.fact.night_on, true, "on")
end

function tests.a_restored_off_clears_the_running_filter()
    local s = sandbox({
        now = at(2026, 10, 27, 10, 0),
        state = state({ on = false, auto = false }),
        sun_running = true,
    })
    s.advance(300)
    local calls = s.hyprsunset_calls()
    assert(has(calls, "identity"), "a restored Off did not clear the filter: " .. table.concat(calls, ", "))
    assert(has(calls, "gamma 100"), "a restored Off did not restore gamma 100")
end

function tests.a_manual_off_survives_a_restart_in_the_same_period()
    local first = sandbox({
        now = at(2026, 10, 27, 22, 0),
        state = state({ on = true, auto = true, boundary = key(2026, 10, 27, 21, 0) }),
        sun_running = true,
    })
    first.advance(300)
    first.emit("night_toggle")
    local saved = first.writes["night.json"]
    assert(saved, "Off was not saved")
    eq(saved.on, false, "saved on")
    eq(saved.boundary, key(2026, 10, 27, 21, 0), "saved boundary")
    local again = sandbox({ now = at(2026, 10, 27, 22, 30), state = saved })
    again.advance(300)
    eq(again.env.fact.night_on, false, "the manual Off was lost across the restart")
    again.tick(2026, 10, 27, 22, 31)
    eq(again.env.fact.night_on, false, "a minute tick reverted the manual Off after the restart")
end

function tests.a_manual_on_survives_a_restart_in_the_same_period()
    local first = sandbox({
        now = at(2026, 10, 27, 22, 0),
        state = state({ on = false, auto = true, boundary = key(2026, 10, 27, 21, 0) }),
        sun_running = true,
    })
    first.advance(300)
    eq(first.env.fact.night_on, false, "precondition: the manual Off stood at the start")
    first.emit("night_toggle")
    local saved = first.writes["night.json"]
    eq(saved.on, true, "saved on")
    local again = sandbox({ now = at(2026, 10, 27, 22, 30), state = saved })
    again.advance(300)
    eq(again.env.fact.night_on, true, "the manual On was lost across the restart")
    again.tick(2026, 10, 27, 22, 31)
    eq(again.env.fact.night_on, true, "a minute tick reverted the manual On after the restart")
end

function tests.a_boundary_missed_while_the_shell_was_down_is_applied()
    local evening = sandbox({
        now = at(2026, 10, 27, 22, 0),
        state = state({ on = false, auto = true, boundary = key(2026, 10, 27, 6, 0) }),
        sun_running = true,
    })
    evening.advance(300)
    eq(evening.env.fact.night_on, true, "the 21:00 boundary crossed during downtime was not applied")
    assert(has(evening.hyprsunset_calls(), "temperature 3000"), "the restored tint was not applied")
    local morning = sandbox({
        now = at(2026, 10, 27, 7, 0),
        state = state({ on = true, auto = true, boundary = key(2026, 10, 26, 21, 0) }),
        sun_running = true,
    })
    morning.advance(300)
    eq(morning.env.fact.night_on, false, "the 06:00 boundary crossed during downtime was not applied")
    assert(has(morning.hyprsunset_calls(), "identity"), "the filter was left on after the missed boundary")
end

function tests.a_manual_choice_stands_with_automatic_off()
    local on = sandbox({
        now = at(2026, 11, 5, 12, 0),
        state = state({ on = true, auto = false, boundary = key(2026, 10, 26, 21, 0) }),
    })
    eq(on.env.fact.night_on, true, "a manual On did not survive with Automatic off")
    local off = sandbox({
        now = at(2026, 11, 5, 23, 0),
        state = state({ on = false, auto = false, boundary = key(2026, 10, 26, 21, 0) }),
    })
    eq(off.env.fact.night_on, false, "a manual Off did not survive with Automatic off")
end

function tests.midnight_is_not_a_boundary_for_a_window_that_crosses_it()
    local s = sandbox({
        now = at(2026, 10, 27, 22, 0),
        state = state({ on = true, auto = true, boundary = key(2026, 10, 27, 21, 0) }),
        sun_running = true,
    })
    s.advance(300)
    s.emit("night_set", 0)
    eq(s.env.fact.night_on, false, "night_set 0 did not turn it off")
    s.tick(2026, 10, 27, 23, 59)
    eq(s.env.fact.night_on, false, "23:59 reverted the override")
    s.tick(2026, 10, 28, 0, 0)
    eq(s.env.fact.night_on, false, "midnight reverted the override")
    s.tick(2026, 10, 28, 5, 59)
    eq(s.env.fact.night_on, false, "05:59 reverted the override")
    s.tick(2026, 10, 28, 6, 0)
    eq(s.env.fact.night_on, false, "the 06:00 boundary leaves the schedule off")
    s.tick(2026, 10, 28, 21, 0)
    eq(s.env.fact.night_on, true, "the 21:00 boundary did not start the schedule")
end

function tests.a_daytime_on_survives_midnight()
    local s = sandbox({
        now = at(2026, 10, 27, 15, 0),
        state = state({ on = false, auto = true, boundary = key(2026, 10, 27, 6, 0) }),
        sun_running = true,
    })
    s.advance(300)
    eq(s.env.fact.night_on, false, "precondition: the schedule is off in the daytime")
    s.emit("night_set", 1)
    eq(s.env.fact.night_on, true, "night_set 1 did not turn it on")
    s.tick(2026, 10, 27, 23, 59)
    s.tick(2026, 10, 28, 0, 1)
    eq(s.env.fact.night_on, true, "midnight reverted a daytime On")
    s.tick(2026, 10, 28, 5, 59)
    eq(s.env.fact.night_on, true, "the daytime On did not last to the 06:00 boundary")
    s.tick(2026, 10, 28, 6, 0)
    eq(s.env.fact.night_on, false, "the 06:00 boundary did not end the daytime On")
end

function tests.the_exact_boundaries_flip_the_schedule()
    local s = sandbox({
        now = at(2026, 10, 27, 5, 59),
        state = state({ on = true, auto = true, boundary = key(2026, 10, 26, 21, 0) }),
        sun_running = true,
    })
    s.advance(300)
    eq(s.env.fact.night_on, true, "precondition: inside the window at 05:59")
    s.tick(2026, 10, 27, 6, 0)
    eq(s.env.fact.night_on, false, "06:00 did not end the window")
    s.tick(2026, 10, 27, 20, 59)
    eq(s.env.fact.night_on, false, "20:59 is still outside the window")
    s.tick(2026, 10, 27, 21, 0)
    eq(s.env.fact.night_on, true, "21:00 did not start the window")
end

function tests.equal_times_are_an_empty_window()
    local s = sandbox({
        now = at(2026, 10, 27, 12, 0),
        state = state({ on = true, auto = false, start = 42, stop = 42 }),
    })
    s.emit("night_auto_toggle")
    eq(s.env.fact.night_auto, true, "Automatic did not turn on")
    eq(s.env.fact.night_on, false, "an empty window evaluated to On")
end

function tests.enabling_automatic_applies_the_schedule_at_once()
    local s = sandbox({
        now = at(2026, 10, 27, 22, 0),
        state = state({ on = false, auto = false }),
        sun_running = true,
    })
    s.emit("night_auto_toggle")
    eq(s.env.fact.night_auto, true, "Automatic did not turn on")
    eq(s.env.fact.night_on, true, "enabling Automatic did not apply the 21:00-06:00 window")
end

function tests.moving_a_time_applies_the_schedule_at_once()
    local s = sandbox({
        now = at(2026, 10, 27, 15, 0),
        state = state({ on = false, auto = true, boundary = key(2026, 10, 27, 6, 0) }),
        sun_running = true,
    })
    s.advance(300)
    eq(s.env.fact.night_on, false, "precondition: 15:00 is outside 21:00-06:00")
    for _ = 1, 12 do s.emit("night_start_step", -1) end       -- 21:00 back to 15:00
    eq(s.writes["night.json"] and s.writes["night.json"].start, 30, "the moved start was not saved")
    eq(s.env.fact.night_on, true, "moving the start onto now did not apply the schedule at once")
end

function tests.moving_the_start_onto_the_stop_empties_the_window()
    local s = sandbox({
        now = at(2026, 10, 27, 3, 0),
        state = state({ on = true, auto = true, boundary = key(2026, 10, 26, 21, 0) }),
        sun_running = true,
    })
    s.advance(300)
    eq(s.env.fact.night_on, true, "precondition: inside the window")
    for _ = 1, 18 do s.emit("night_start_step", 1) end        -- 21:00 forward to 06:00
    eq(s.writes["night.json"].start, 12, "the start did not reach the stop")
    eq(s.env.fact.night_on, false, "start == stop did not empty the window")
end

function tests.a_pending_start_applies_the_latest_state()
    local s = sandbox({
        now = at(2026, 10, 27, 22, 0),
        state = state({ on = true, auto = false }),
        sun_running = false,
    })
    s.emit("night_set", 0)                                     -- Off while the daemon start is still pending
    s.advance(300)
    local calls = s.hyprsunset_calls()
    assert(not has(calls, "temperature 3000"), "a pending On was applied after Off: " .. table.concat(calls, ", "))
    assert(has(calls, "identity"), "Off never cleared the daemon")
    eq(s.last_hyprsunset(), "gamma 100", "Off did not end on gamma 100")
end

function tests.a_pending_start_applies_the_latest_temperature()
    local s = sandbox({
        now = at(2026, 10, 27, 22, 0),
        state = state({ on = true, auto = false }),
        sun_running = false,
    })
    s.emit("night_temp_set", 1)                                -- 2500 K
    s.emit("night_temp_set", 0)                                -- 6500 K, the latest
    s.advance(1000)
    local calls = s.hyprsunset_calls()
    local last_temp
    for _, c in ipairs(calls) do if c:find("^temperature") then last_temp = c end end
    eq(last_temp, "temperature 6500", "the latest slider value was not applied: " .. table.concat(calls, ", "))
end

function tests.gamma_is_eighty_on_and_a_hundred_off()
    local s = sandbox({
        now = at(2026, 10, 27, 22, 0),
        state = state({ on = true, auto = false }),
        sun_running = true,
    })
    s.advance(300)
    assert(has(s.hyprsunset_calls(), "gamma 80"), "On did not set gamma 80")
    s.emit("night_set", 0)
    s.advance(300)
    local calls = s.hyprsunset_calls()
    assert(has(calls, "identity"), "Off did not reset identity")
    eq(s.last_hyprsunset(), "gamma 100", "Off did not end on gamma 100")
end

function tests.a_failed_command_is_not_applied_and_a_control_retries()
    local failing = true
    local s = sandbox({
        now = at(2026, 10, 27, 22, 0),
        state = state({ on = true, auto = false }),
        sun_running = true,
        fail = function(command, args) return failing and command == "hyprctl" and args[1] == "hyprsunset" end,
    })
    s.advance(300)
    assert(#s.hyprsunset_calls() > 0, "no command was attempted")
    assert(not has(s.hyprsunset_calls(), "gamma 80"), "a rejected temperature continued the On chain")
    s.sun_running = false                                      -- the daemon dies
    failing = false
    s.emit("night_set", 1)
    s.advance(300)
    assert(has(s.hyprsunset_calls(), "temperature 3000"), "the retry did not set the saved temperature")
    eq(s.last_hyprsunset(), "gamma 80", "the retry did not set gamma 80")
end

function tests.an_off_during_inflight_temperature_finishes_off()
    local s = sandbox({ state = state({ auto = false }), sun_running = true, defer_ipc = true })
    s.emit("night_set", 0)
    s.finish_ipc()
    eq(s.env.fact.night_on, false, "latest UI choice")
    eq(s.last_hyprsunset(), "gamma 100", "an old On callback dimmed the screen after Off")
    assert(has(s.hyprsunset_calls(), "identity"), "the in-flight tint was not cleared")
end

function tests.a_full_day_missed_by_the_clock_ends_an_override()
    local s = sandbox({
        now = at(2026, 10, 27, 22, 0),
        state = state({ boundary = key(2026, 10, 27, 21, 0) }), sun_running = true,
    })
    s.emit("night_set", 0)
    s.tick(2026, 10, 28, 22, 0)
    eq(s.env.fact.night_on, true, "resume after a full day must respect crossed boundaries")
end

function tests.a_cold_start_failure_recovers_on_the_existing_clock()
    local failing = true
    local s = sandbox({ state = state({ auto = false }), sun_running = true,
        fail = function() return failing end })
    failing = false
    s.tick(2026, 10, 26, 22, 1)
    eq(s.last_hyprsunset(), "gamma 80", "a failed saved On was never retried after startup")
end

function tests.restored_off_without_a_daemon_stays_idle()
    local s = sandbox({ state = state({ on = false, auto = false }), sun_running = false })
    eq(#s.hyprsunset_calls(), 0, "Off must not send IPC to an absent backend")
    local commands = #s.commands
    s.tick(2026, 10, 26, 22, 1)
    eq(#s.commands, commands, "idle Off must not poll or retry an absent backend")
end

function tests.a_month_and_year_roll_over_in_the_day_arithmetic()
    -- 1 March: "yesterday" is in February (28th, or the 29th in a leap year), not "now minus a day" guessed wrongly.
    local march = sandbox({
        now = at(2026, 3, 1, 1, 0),
        state = state({ on = false, auto = true, boundary = key(2026, 2, 28, 21, 0) }),
        sun_running = true,
    })
    march.advance(300)
    eq(march.env.fact.night_on, false, "the February period was not found on 1 March")
    local january = sandbox({
        now = at(2026, 1, 1, 22, 0),
        state = state({ on = false, auto = true, boundary = key(2025, 12, 31, 6, 0) }),
        sun_running = true,
    })
    january.advance(300)
    eq(january.env.fact.night_on, true, "the 31 December 21:00 boundary was not found on 1 January")
    local leap = sandbox({
        now = at(2028, 3, 1, 1, 0),
        state = state({ on = false, auto = true, boundary = key(2028, 2, 29, 21, 0) }),
        sun_running = true,
    })
    leap.advance(300)
    eq(leap.env.fact.night_on, false, "29 February was not found on 1 March 2028")
end

function tests.local_dates_keep_overrides_across_cairo_dst()
    -- Egypt's DST starts on the last Friday of April (2026-04-24). A manual Off at 01:00 on the 24th belongs to the
    -- 23rd's 21:00 period, and a restart 90 minutes later is still that period.
    local first = sandbox({
        now = at(2026, 4, 24, 1, 0),
        state = state({ on = true, auto = true, boundary = key(2026, 4, 23, 21, 0) }),
        sun_running = true,
    })
    first.advance(300)
    first.emit("night_set", 0)
    local saved = first.writes["night.json"]
    eq(saved.boundary, key(2026, 4, 23, 21, 0), "the saved boundary is not the 23rd's 21:00")
    local again = sandbox({ now = at(2026, 4, 24, 2, 30), state = saved })
    eq(again.env.fact.night_on, false, "the DST change invented a boundary and reverted the manual Off")
    -- A boundary crossed while the shell was down, on the DST day: the schedule takes over at once.
    local missed = sandbox({
        now = at(2026, 4, 24, 7, 0),
        state = state({ on = true, auto = true, boundary = key(2026, 4, 23, 21, 0) }),
        sun_running = true,
    })
    missed.advance(300)
    eq(missed.env.fact.night_on, false, "the 06:00 boundary on the DST day was not applied")
    -- And the DST end (last Thursday of October, 2026-10-29): a manual Off at 23:30 still belongs to the 21:00 period.
    local ending = sandbox({
        now = at(2026, 10, 30, 1, 0),
        state = state({ on = false, auto = true, boundary = key(2026, 10, 29, 21, 0) }),
        sun_running = true,
    })
    ending.advance(300)
    eq(ending.env.fact.night_on, false, "the DST end invented a boundary and reverted the manual Off")
end

function tests.the_shader_fallback_still_works_and_clears_its_own_file()
    local on = sandbox({
        now = at(2026, 10, 27, 22, 0),
        state = state({ on = true, auto = false }),
        sun_installed = false,
    })
    local frag = on.writes["night.frag"]
    assert(frag, "the fallback never wrote a shader")
    assert(frag:find("* 0.8", 1, true), "the fallback shader has no 80% brightness")
    local last_eval
    for _, c in ipairs(on.commands) do
        if c.command == "hyprctl" and c.args[1] == "eval" then last_eval = c.args[2] end
    end
    assert(last_eval and last_eval:find("night.frag", 1, true), "the fallback shader was never set")
    local off = sandbox({
        now = at(2026, 10, 27, 22, 0),
        state = state({ on = false, auto = false }),
        sun_installed = false,
        shader = "/data/vitreus/night.frag",
    })
    last_eval = nil
    for _, c in ipairs(off.commands) do
        if c.command == "hyprctl" and c.args[1] == "eval" then last_eval = c.args[2] end
    end
    assert(last_eval and last_eval:find('screen_shader = ""', 1, true), "a restored Off left its shader behind")
end

local only = arg[1]
if only then
    assert(tests[only], "unknown nightmode test: " .. only)()
    print("nightmode " .. only .. ": PASS")
else
    for _, name in ipairs({
        "restores_the_saved_warmth_and_half_hours",
        "a_restored_off_clears_the_running_filter",
        "a_manual_off_survives_a_restart_in_the_same_period",
        "a_manual_on_survives_a_restart_in_the_same_period",
        "a_boundary_missed_while_the_shell_was_down_is_applied",
        "a_manual_choice_stands_with_automatic_off",
        "midnight_is_not_a_boundary_for_a_window_that_crosses_it",
        "a_daytime_on_survives_midnight",
        "the_exact_boundaries_flip_the_schedule",
        "equal_times_are_an_empty_window",
        "enabling_automatic_applies_the_schedule_at_once",
        "moving_a_time_applies_the_schedule_at_once",
        "moving_the_start_onto_the_stop_empties_the_window",
        "a_pending_start_applies_the_latest_state",
        "a_pending_start_applies_the_latest_temperature",
        "gamma_is_eighty_on_and_a_hundred_off",
        "a_failed_command_is_not_applied_and_a_control_retries",
        "a_month_and_year_roll_over_in_the_day_arithmetic",
        "local_dates_keep_overrides_across_cairo_dst",
        "the_shader_fallback_still_works_and_clears_its_own_file",
        "an_off_during_inflight_temperature_finishes_off",
        "a_full_day_missed_by_the_clock_ends_an_override",
        "a_cold_start_failure_recovers_on_the_existing_clock",
        "restored_off_without_a_daemon_stays_idle",
    }) do tests[name]() end
    print("nightmode: PASS")
end
