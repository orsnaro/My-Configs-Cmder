-- Exercise the release's real dock controller without launching apps or touching saved desktop state.
local function fixture(saved)
    local s = { events = {}, watchers = {}, writes = {}, launches = {}, fact = {}, model = {} }
    local env = setmetatable({
        fact = s.fact, model = s.model,
        dock_fx = { changed = function() end },
        on = function(name, fn) s.events[name] = fn end,
        exec_on_desktop = function(cmd) s.launches[#s.launches + 1] = cmd end,
        sys = {
            ask = function() return saved end,
            call = function(_, name, value) s.writes[name] = value end,
            watch = function(name, fn) s.watchers[name] = fn end,
        },
    }, { __index = _G })
    assert(loadfile('logic/dock.luau', 't', env))()()
    s.env = env
    return s
end

local app = { id = 'test.desktop', name = 'Example', icon = 'example', exec = 'example --new-window %U' }
local first = fixture()
assert(first.env.cdk_toggle(app) == true, 'right-click must pin an app')
assert(first.env.cdk_pinned(app), 'the launcher must recognize pinned apps')
assert(#first.model.cdk_pins == 1 and first.model.cdk_pins[1].icon == 'example')
first.events.cdk_go(0)
assert(first.launches[1] == 'example --new-window', 'launch must strip desktop-entry placeholders')
first.fact.cdk_corner = 1
first.events['fact:cdk_corner']()
local saved = first.writes['dock-pins.json']
assert(saved.corner == 1 and saved.pins[1].id == app.id, 'pins and moved corner must be saved')

local again = fixture(saved)
assert(again.fact.cdk_corner == 1 and again.env.cdk_pinned(app), 'pins and corner must survive restart')
again.events['fact:cdk_on'](false)
assert(again.fact.cdk_on == false and #again.model.cdk_pins == 1, 'hiding must retain pins')
assert(again.writes['dock-pins.json'].on == false, 'visibility must persist')
again.events.cdk_unpin(0)
assert(#again.model.cdk_pins == 0 and not again.env.cdk_pinned(app), 'right-click unpins the selected app')

local full = fixture()
for i = 1, 8 do
    assert(full.env.cdk_toggle({ id = tostring(i), exec = 'example', icon = tostring(i) }) == true)
end
assert(full.env.cdk_toggle({ id = 'ninth', exec = 'example' }) == nil, 'the dock must enforce its eight-pin model limit')
assert(#full.model.cdk_pins == 8)
full.watchers.apps({ { id = '1', icon = 'new-icon' } })
assert(full.model.cdk_pins[1].icon == 'new-icon', 'icon-theme updates must refresh the existing pin')

print('corner dock pin/launch/unpin, restart, corner, visibility and capacity: PASS')
