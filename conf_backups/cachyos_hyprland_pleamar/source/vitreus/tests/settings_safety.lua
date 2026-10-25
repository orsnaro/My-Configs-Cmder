-- Execute production logic without starting programs, locking, writing files or changing displays.
local function sandbox()
    local s = { handlers = {}, once = {}, periodic = {}, calls = {}, now = 0, result = 0 }
    local env = setmetatable({ fact = {}, text = {}, model = {} }, { __index = _G })
    s.env = env
    env.on = function(name, fn) s.handlers[name] = fn end
    env.after = function(ms, fn) s.once[#s.once + 1] = { at = s.now + ms, fn = fn } end
    env.every = function(ms, fn) s.periodic[ms] = fn end
    env.run = function(command, args, fn)
        s.calls[#s.calls + 1] = { command = command, args = args }
        if command == "systemctl" then
            if fn then fn("", s.result) end
        elseif fn then fn("", 1) end
    end
    env.exec_on_desktop = function(command)
        s.calls[#s.calls + 1] = { command = "desktop", args = { command } }
    end
    env.sys = { ask = function() return nil end, call = function() error("Unexpected sys.call") end }
    function s:advance(ms)
        local target = self.now + ms
        while true do
            table.sort(self.once, function(a, b) return a.at < b.at end)
            local next_ = self.once[1]
            if not next_ or next_.at > target then break end
            table.remove(self.once, 1)
            self.now = next_.at
            next_.fn()
        end
        self.now = target
    end
    function s:commands(name)
        local found = {}
        for _, call in ipairs(self.calls) do
            if call.command == name then found[#found + 1] = call end
        end
        return found
    end
    return s
end

local function module(s, name, ...)
    assert(loadfile("logic/" .. name .. ".luau", "t", s.env))()(...)
end

local tests = {}
local function assert_restart(call)
    assert(call and call.command == "systemctl" and
           table.concat(call.args, " ") == "--user --no-block restart pleamar.service",
           "Restart must be queued through the owning service, never a detached self-quit helper")
end

function tests.lock()
    local s = sandbox()
    local closed = 0
    module(s, "capture_power", function(panel)
        assert(panel == "none")
        closed = closed + 1
    end)
    s.handlers.pow_press(0)
    assert(closed == 1 and #s:commands("desktop") == 0, "Lock must close its drawer first")
    s:advance(299)
    assert(#s:commands("desktop") == 0, "Lock must retain the300ms dismissal delay")
    s:advance(1)
    local calls = s:commands("desktop")
    assert(#calls == 1 and calls[1].args[1] == "$HOME/.config/pleamar/shells/vitreus/bin/vitreus-lock",
           "Menu Lock must use Super+L's shared native-lock helper, not a second locker")
end

function tests.about()
    local function fixture(result)
        local s = sandbox()
        s.result = result
        module(s, "updates", nil, function(fn)
            fn({ conf = "/fixture/vitreus", data = "/fixture/data/vitreus" })
        end)
        return s
    end
    local s = fixture(0)
    s.handlers.about_restart()
    assert_restart(s.calls[#s.calls])
    assert(s.env.fact.about_restarting == true and s.env.fact.about_busy == true)
    s.handlers.about_restart()
    assert(#s:commands("systemctl") == 1, "Double click must not enqueue another restart")
    assert(#s:commands("setsid") == 0 and #s:commands("desktop") == 0)

    s = fixture(1)
    s.handlers.about_restart()
    assert_restart(s.calls[#s.calls])
    assert(s.env.fact.about_restarting == false and s.env.fact.about_busy == false,
           "A failed restart must re-enable the UI")
    assert((s.env.text.about_msg or ""):find("restart"), "A failed restart needs a visible error")
    s.result = 0
    s.handlers.about_restart()
    assert(#s:commands("systemctl") == 2 and s.env.fact.about_restarting == true,
           "A failed restart must be retryable")

    -- A queued (exit 0) restart that never actually replaces this shell must not latch the page for ever.
    s = fixture(0)
    s.handlers.about_restart()
    s:advance(19999)
    assert(s.env.fact.about_restarting == true, "Do not unlatch before the restart had its chance")
    s:advance(1)
    assert(s.env.fact.about_restarting == false and s.env.fact.about_busy == false,
           "A restart that never replaced the shell must re-enable the UI")
    assert((s.env.text.about_msg or ""):find("restart"), "The latch timeout needs a visible error")
end

function tests.topology()
    local function fixture()
        local s = sandbox()
        s.monitors = {
            { name = "DP-1", width = 1440, height = 2560, scale = 1.0, transform = 0, focused = true },
        }
        s.result = 0
        s.env.hypr_monitors = function(_, fn) fn("fixture", 0) end
        s.env.json = { decode = function() return s.monitors end }
        s.env.sys.ask = function() return s.trial end
        module(s, "monitor_height")
        s.calls = {}
        return s
    end
    local function look(s) s.periodic[4000]() end
    local function geometry(s, height) s.monitors[1].height = height end

    -- Unchanged and focus-only observations never restart.
    local s = fixture()
    s.monitors[1].focused = false
    look(s); look(s); s:advance(1500)
    assert(#s:commands("systemctl") == 0, "Focus changes alone must not restart the shell")

    -- Two changed looks schedule one managed restart after 1500ms.
    geometry(s, 1440)
    look(s)
    assert(#s:commands("systemctl") == 0, "One changed look must not restart yet")
    look(s)
    look(s); look(s)  -- the fast poll must not queue duplicates while one request is pending
    assert(#s:commands("systemctl") == 0, "The restart must wait for the mode switch to settle")
    s:advance(1499)
    assert(#s:commands("systemctl") == 0, "Keep the 1500ms settle delay")
    s:advance(1)
    local calls = s:commands("systemctl")
    assert(#calls == 1, "One pending request must queue exactly one restart")
    assert_restart(calls[1])
    assert(#s:commands("desktop") == 0, "No detached sleep/pkill helper may run")
    look(s); look(s); s:advance(2000)
    assert(#s:commands("systemctl") == 1, "A successful queue must not repeat for the same geometry")

    -- An open trial blocks the restart, whether it is in fact or on disk.
    s = fixture()
    s.trial = { before = { DP1 = {} } }
    geometry(s, 1440); look(s); look(s); s:advance(2000)
    assert(#s:commands("systemctl") == 0, "An open display trial must block restarts")

    -- A trial that starts during the delay cancels the obsolete request.
    s = fixture()
    geometry(s, 1440); look(s); look(s)
    s.trial = { before = { DP1 = {} } }
    s:advance(1500)
    assert(#s:commands("systemctl") == 0, "A trial started during the delay must cancel the restart")
    s.trial = nil
    look(s); look(s); s:advance(1500)
    assert(#s:commands("systemctl") == 1, "Once the trial closes, the current geometry may restart")

    -- Reverting during the delay cancels it; nothing is left to restart.
    s = fixture()
    geometry(s, 1440); look(s); look(s)
    geometry(s, 2560); look(s)  -- back to the layout the shell already has
    s:advance(2000)
    assert(#s:commands("systemctl") == 0, "A reverted geometry must not restart")

    -- A new geometry during the delay supersedes the old target.
    s = fixture()
    geometry(s, 1440); look(s); look(s)
    geometry(s, 1080); look(s)
    s:advance(1500)
    assert(#s:commands("systemctl") == 0, "An obsolete geometry must not restart")
    look(s); look(s); s:advance(1500)
    assert(#s:commands("systemctl") == 1, "The current geometry must still be restartable")

    -- A failed queue leaves the base alone and permits a retry.
    s = fixture()
    s.result = 1
    geometry(s, 1440); look(s); look(s); s:advance(1500)
    assert(#s:commands("systemctl") == 1 and s.result == 1)
    look(s); look(s); s:advance(1500)
    assert(#s:commands("systemctl") == 2, "A failed restart request must be retried")
end

local choice = arg[1]
if choice then
    assert(tests[choice], "Unknown settings safety test: " .. choice)()
    print("settings safety " .. choice .. ": PASS")
else
    for _, name in ipairs({ "lock", "about", "topology" }) do tests[name]() end
    print("settings safety: PASS")
end
