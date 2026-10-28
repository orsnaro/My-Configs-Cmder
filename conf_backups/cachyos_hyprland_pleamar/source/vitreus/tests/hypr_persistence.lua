-- Runs the real Settings > Hyprland block against inert commands and timers.
-- Regression: a slider change must not leave the config write latched off.
local root = "."
local source = assert(io.open(root .. "/vitreus.luau", "r")):read("a")
local start = assert(source:find("-- ── Settings > Hyprland", 1, true))
local finish = assert(source:find("-- ── Settings > Pleamar-WM", 1, true))
local block = source:sub(start, finish - 1)

local function sandbox()
    local s = {
        env = setmetatable({ fact = {}, text = {} }, { __index = _G }),
        handlers = {},
        writes = {},
        copies = {},
        timers = {},
        now = 0,
        eval_ok = true,
        eval_code = nil,
    }
    local env = s.env
    env.on = function(name, fn) s.handlers[name] = fn end
    env.after = function(ms, fn) s.timers[#s.timers + 1] = { at = s.now + ms, fn = fn } end
    env.sys = {
        ask = function() return nil end,
        call = function(service, name, value)
            if service == "files.write" then s.writes[name] = value end
            return true
        end,
    }
    env.with_dirs = function(fn)
        fn({ data = "/data/vitreus", conf = "/config/pleamar/shells/vitreus" })
    end
    env.iris_cfg = { look = 0 }
    env.vtheme = {
        current = function() return { id = "glass", round = 22 } end,
        round_of = function() return 22 end,
    }
    env.iris_fx = { CASSETTE = 1, UWU = 2, CYBER = 3 }
    env.glass = {}
    env.run = function(command, args, cb)
        if command == "hyprctl" and args[1] == "eval" then
            s.eval_code = args[2]
            if cb then cb("", s.eval_ok and 0 or 1) end
        elseif command == "cp" then
            s.copies[#s.copies + 1] = args
            if cb then cb("", 0) end
        elseif command == "hyprctl" and args[1] == "--batch" then
            if cb then cb("", 1) end
        elseif cb then
            cb("", 0)
        end
    end
    function s.advance(ms)
        local target = s.now + ms
        while true do
            table.sort(s.timers, function(a, b) return a.at < b.at end)
            local next_ = s.timers[1]
            if not next_ or next_.at > target then break end
            table.remove(s.timers, 1)
            s.now = next_.at
            next_.fn()
        end
        s.now = target
    end
    assert(load(block, "settings-hyprland", "t", env))()
    return s
end

local tests = {}
function tests.rapid_changes_persist_the_latest_state()
    local s = sandbox()
    s.handlers.hy_layout_set(2)       -- Master
    s.handlers.hy_round_set(0.3)      -- 9 px
    s.advance(2000)
    local body = s.writes["vitreus_hypr.lua"]
    assert(body, "rapid changes never wrote vitreus_hypr.lua")
    assert(body:find('layout = "master"', 1, true), "the saved layout is not the latest one")
    assert(body:find("rounding = 9", 1, true), "the saved rounding is not the latest one")
    assert(#s.copies == 1, "expected one config copy, got " .. #s.copies)
end
function tests.flush_writes_now_and_cancels_the_timer()
    local s = sandbox()
    s.handlers.hy_layout_set(2)
    assert(type(s.env.hy_flush) == "function", "Settings > Hyprland has no pending-write flush")
    s.env.hy_flush()
    assert(s.writes["vitreus_hypr.lua"], "flush did not write the pending settings")
    local copies = #s.copies
    s.advance(2000)
    assert(#s.copies == copies, "flush left the old timer to write a second time")
end
function tests.a_rejected_value_is_not_saved()
    local s = sandbox()
    s.eval_ok = false
    s.handlers.hy_layout_set(2)
    s.advance(2000)
    assert(s.writes["vitreus_hypr.lua"] == nil, "a rejected Hyprland value was persisted")
end

local choice = arg[1]
if choice then
    assert(tests[choice], "Unknown Hyprland persistence test: " .. choice)()
    print("hypr persistence " .. choice .. ": PASS")
else
    for _, name in ipairs({
        "rapid_changes_persist_the_latest_state",
        "flush_writes_now_and_cancels_the_timer",
        "a_rejected_value_is_not_saved",
    }) do tests[name]() end
    print("hypr persistence: PASS")
end
