-- Run the real session logic; only compositor I/O is replaced.
local layers, cursor, commands, bindings, events = {}, nil, {}, {}, {}
local api = {
    get_layers = function() return layers end,
    get_cursor_pos = function() return cursor end,
    exec_cmd = function(command) commands[#commands + 1] = command end,
    on = function(event, callback) events[event] = callback end,
    bind = function(key, callback, options)
        assert(not bindings[key], "duplicate mouse binding")
        local binding = { callback = callback, enabled = true, options = options }
        function binding:set_enabled(value) self.enabled = value end
        bindings[key] = binding
        return binding
    end,
}
local environment = setmetatable({ hl = api }, { __index = _G })
local chunk = loadfile(os.getenv("HOME") .. "/.config/hypr/sherlock_session.lua", "t", environment)
assert(chunk, "Missing Sherlock layer-aware session")
local module = chunk()
local session = module.setup()
assert(module.setup() == session, "setup must be idempotent")
local button = assert(bindings["mouse:272"])
assert(not button.enabled, "hidden Sherlock must not intercept clicks")
session.toggle()
assert(commands[#commands]:match("launcher%.sh"), "hidden toggle must open apps")

local layer = { namespace = "sherlock", mapped = true, pid = 4321,
    x = -1400, y = 100, w = 900, h = 593, monitor = { id = 2 } }
layers = { layer }
events["layer.opened"](layer)
assert(button.enabled, "mapped Sherlock must enable dismissal")
session.toggle()
assert(commands[#commands]:match("close 4321$"), "visible toggle must close its exact PID")

local count = 0
for _, case in ipairs({
    { x = -1400, y = 100, pass = true },
    { x = -501, y = 692, pass = true },
    { x = -500, y = 300, pass = false },
    { x = -1401, y = 300, pass = false },
    { x = -1000, y = 99, pass = false },
    { x = -1000, y = 693, pass = false },
    { x = 3300, y = 800, pass = false },
}) do
    cursor = { x = case.x, y = case.y }
    local before = #commands
    assert(button.callback().pass_event == case.pass, "incorrect logical-coordinate hit test")
    assert(#commands == before + (case.pass and 0 or 1), "inside click must not close")
    count = count + 1
end
cursor = nil
assert(button.callback().pass_event, "missing cursor must pass")
cursor = { x = 3300, y = 800 }
layer.w = nil
assert(button.callback().pass_event, "missing geometry must pass")
layer.w = 900
layer.mapped = false
events["layer.closed"](layer)
assert(not button.enabled, "closed Sherlock must release mouse bindings")
assert(button.callback().pass_event, "unmapped layer must pass")
layer.mapped, layer.namespace = true, "rofi"
assert(button.callback().pass_event, "unrelated namespace must pass")
layer.namespace, layer.pid = "sherlock", -1
assert(button.callback().pass_event, "invalid PID must pass")
layer.pid = 4321
events["config.reloaded"]()
assert(button.enabled, "reload must adopt mapped Sherlock")
for key in pairs(bindings) do
    assert(key:match("^mouse:27[234]$"), "modified mouse shortcuts must remain untouched")
end
print("PASS: toggle, " .. count .. " hit-test cases, pass-through, lifecycle and reload")
