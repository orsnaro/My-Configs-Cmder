local root = os.getenv("HOME") .. "/.config/hypr/"
local bindings, workspaces, rules, unbound = {}, {}, {}, {}
local dispatched = {}
local adjacent_monitors, monitor_queries = {}, {}
local active_window, all_windows, all_monitors = nil, {}, { { active_workspace = { id = 8 } } }

local function operation(name)
    return function(arg)
        return { name = name, arg = arg }
    end
end

hl = {
    bind = function(key, action, options)
        assert(not bindings[key], "duplicate binding: " .. key)
        bindings[key] = { action = action, options = options or {} }
    end,
    unbind = function(key) unbound[key] = true end,
    on = function(...) end,
    dispatch = function(action) dispatched[#dispatched + 1] = action end,
    get_active_window = function() return active_window end,
    get_windows = function() return all_windows end,
    get_monitors = function() return all_monitors end,
    get_monitor = function(selector)
        monitor_queries[#monitor_queries + 1] = selector
        return adjacent_monitors[selector]
    end,
    exec_cmd = operation("exec"),
    workspace_rule = function(rule) workspaces[rule.workspace] = rule end,
    window_rule = function(rule) rules[rule.name] = rule end,
    layer_rule = function(...) end,
    config = function(...) end,
    dsp = {
        exec_cmd = operation("exec"), focus = operation("focus"),
        send_shortcut = operation("send_shortcut"),
        window = {
            move = operation("move"), float = operation("float"),
            fullscreen = operation("fullscreen"), resize = operation("resize"),
        },
        workspace = { toggle_special = operation("toggle_special") },
    },
}

dofile(root .. "custom.lua")

local function is_action(key, name, arg_key, value)
    local binding = assert(bindings[key], "missing binding: " .. key)
    assert(binding.action.name == name, key .. " should perform " .. name)
    if arg_key then assert(binding.action.arg[arg_key] == value, key .. " wrong " .. arg_key) end
end

for id, monitor in pairs({
    [1] = "DP-2", [9] = "DP-2",
    [2] = "HDMI-A-2", [3] = "HDMI-A-2", [4] = "HDMI-A-2",
    [5] = "HDMI-A-2", [6] = "HDMI-A-2", [7] = "HDMI-A-2",
    [8] = "DP-1",
}) do
    assert(workspaces[tostring(id)] ~= nil, "missing workspace rule " .. id)
    assert(workspaces[tostring(id)].monitor == monitor, "wrong monitor for workspace " .. id)
end

local id_keys = {
    { key = "grave", id = 1 }, { key = "1", id = 2 },
    { key = "2", id = 3 }, { key = "3", id = 4 },
    { key = "4", id = 5 }, { key = "5", id = 6 },
    { key = "F1", id = 7 }, { key = "F2", id = 8 },
    { key = "F3", id = 9 },
}
for _, ws in ipairs(id_keys) do
    is_action("ALT + " .. ws.key, "focus", "workspace", ws.id)
    is_action("ALT + SHIFT + " .. ws.key, "move", "workspace", ws.id)
    assert(bindings["ALT + SHIFT + " .. ws.key].action.arg.follow == true,
        "workspace move should follow the window: " .. ws.key)
end

is_action("ALT + X", "fullscreen", "mode", "maximized")
is_action("ALT + F", "fullscreen", "mode", "fullscreen")
assert(bindings["ALT + F"].action.arg.action == "toggle", "ALT+F should toggle fullscreen")
assert(unbound["SUPER + F"], "old fullscreen shortcut should be removed")
is_action("CTRL + SHIFT + W", "exec")
assert(bindings["CTRL + SHIFT + W"].action.arg == "~/.config/hypr/scripts/killactive.sh",
    "CTRL+SHIFT+W should close the focused window via the panel-aware script")
assert(unbound["SUPER + Q"], "old close shortcut should be removed")
is_action("ALT + SHIFT + SPACE", "float", "action", "toggle")
is_action("ALT + M", "exec")
assert(bindings["ALT + M"].action.arg:find("glaze-minimize hide", 1, true))
is_action("ALT + SHIFT + M", "exec")
assert(bindings["ALT + SHIFT + M"].action.arg:find("glaze-minimize restore-all", 1, true))
-- ALT+letters focus Hyprland windows, passing through to Kitty panes
-- while a Kitty window is focused (function binds: runtime class check).
for _, spec in ipairs({ {"J", "left"}, {"L", "right"}, {"I", "up"}, {"K", "down"} }) do
    local binding = assert(bindings["ALT + " .. spec[1]],
        "missing ALT+" .. spec[1] .. " focus-with-passthrough binding")
    assert(type(binding.action) == "function",
        "ALT+" .. spec[1] .. " must check the active window class at runtime")
    is_action("ALT + " .. spec[2], "focus", "direction", spec[2])
end
-- SHIFT+ALT arrows focus; CTRL+ALT+SHIFT letters focus.
for _, spec in ipairs({ {"J", "left"}, {"L", "right"}, {"I", "up"}, {"K", "down"} }) do
    is_action("ALT + SHIFT + " .. spec[2], "focus", "direction", spec[2])
    is_action("CTRL + ALT + SHIFT + " .. spec[1], "focus", "direction", spec[2])
end
-- ALT+letter runtime behavior: Kitty keeps original event, others focus once.
local function fake_window(class, x, y, w, h, ws, pid, address)
    return { class = class, pid = pid, address = address,
        at = { x = x, y = y }, size = { x = w, y = h },
        workspace = { id = ws or 8 } }
end
assert(_reset_nav == nil, "no test-only nav reset in production")
all_monitors = { { active_workspace = { id = 8 } } }
for _, spec in ipairs({ {"J", "left"}, {"L", "right"}, {"I", "up"}, {"K", "down"} }) do
    for _, class in ipairs({ "kitty", "quake-kitty" }) do
        dispatched = {}
        active_window = fake_window(class, 200, 0, 100, 100, 8, 111)
        all_windows = { active_window, fake_window("brave-browser", 0, 0, 100, 100, 8) }
        local ret = bindings["ALT + " .. spec[1]].action()
        assert(type(ret) == "table" and ret.pass_event == true,
            "ALT+" .. spec[1] .. " in " .. class .. " must return original event")
        assert(#dispatched == 0, "ALT+" .. spec[1] .. " in " .. class .. " must not dispatch")
    end
end
local dir_candidate = {
    left = { 0, 200 }, right = { 400, 200 }, up = { 200, 0 }, down = { 200, 400 },
}
for _, spec in ipairs({ {"J", "left"}, {"L", "right"}, {"I", "up"}, {"K", "down"} }) do
    dispatched = {}
    active_window = fake_window("brave-browser", 200, 200, 100, 100, 8)
    local c = dir_candidate[spec[2]]
    all_windows = { active_window, fake_window("brave-browser", c[1], c[2], 100, 100, 8) }
    bindings["ALT + " .. spec[1]].action()
    assert(#dispatched == 1 and dispatched[1].name == "focus"
        and dispatched[1].arg.direction == spec[2],
        "ALT+" .. spec[1] .. " must focus " .. spec[2])
end
dispatched = {}
active_window = fake_window("brave-browser", 200, 200, 100, 100, 8)
all_windows = { active_window, fake_window("brave-browser", 0, 200, 100, 100, 8) }
bindings["ALT + J"].action()
bindings["ALT + J"].action()
bindings["ALT + J"].action()
assert(#dispatched == 3, "consecutive non-Kitty callbacks must each dispatch once")
dispatched = {}
active_window = fake_window("kitty", 200, 200, 100, 100, 8, 111)
all_windows = { active_window }
assert(bindings["ALT + J"].action().pass_event == true, "Kitty must keep original event")
assert(#dispatched == 0, "Kitty must not dispatch")
active_window = fake_window("brave-browser", 200, 200, 100, 100, 8)
all_windows = { active_window, fake_window("brave-browser", 0, 200, 100, 100, 8) }
bindings["ALT + J"].action()
assert(#dispatched == 1, "non-Kitty after Kitty must dispatch")
active_window = fake_window("kitty", 200, 200, 100, 100, 8, 111)
all_windows = { active_window }
assert(bindings["ALT + J"].action().pass_event == true, "Kitty again must keep original event")
assert(#dispatched == 1, "Kitty after non-Kitty must not dispatch")
dispatched = {}
active_window = fake_window("brave-browser", 200, 0, 100, 100, 8)
all_windows = { active_window }
bindings["ALT + L"].action()
assert(#dispatched == 0, "ALT+L with nothing right must stop, not cycle")
-- Cross-monitor: candidate on another VISIBLE workspace counts.
dispatched = {}
all_monitors = { { active_workspace = { id = 8 } }, { active_workspace = { id = 1 } } }
active_window = fake_window("brave-browser", 2500, 800, 600, 400, 8)
all_windows = { active_window, fake_window("kitty", 2400, 800, 600, 400, 1) }
bindings["ALT + J"].action()
assert(#dispatched == 1 and dispatched[1].name == "focus",
    "ALT+J toward a visible other-monitor window must dispatch")
-- Hidden workspaces never count (prevents cycling back).
dispatched = {}
all_monitors = { { active_workspace = { id = 8 } } }
bindings["ALT + J"].action()
assert(#dispatched == 0, "ALT+J toward a hidden workspace must stop")
-- checked_focus: single gate used by binds and kitty fallthrough alike.
dispatched = {}
all_monitors = { { active_workspace = { id = 8 } } }
active_window = fake_window("brave-browser", 200, 0, 100, 100, 8)
all_windows = { active_window }
checked_focus("right")
assert(#dispatched == 0, "checked_focus with no candidate must stay silent")
all_windows = { active_window, fake_window("kitty", 0, 0, 100, 100, 8) }
checked_focus("left")
assert(#dispatched == 1 and dispatched[1].name == "focus"
    and dispatched[1].arg.direction == "left",
    "checked_focus with a candidate must dispatch once")
-- Real ws8 geometry: brave (5696..6386) above kitty (4982..6386);
-- kitty's center x=5684 sits 12px outside brave's span: overlap, not
-- center containment, must count.
dispatched = {}
active_window = fake_window("brave-browser", 5696, 822, 690, 402, 8)
all_windows = { active_window, fake_window("kitty", 4982, 1248, 1404, 402, 8) }
bindings["ALT + K"].action()
assert(#dispatched == 1 and dispatched[1].name == "focus"
    and dispatched[1].arg.direction == "down",
    "ALT+K onto a partially overlapped window must focus it")
dispatched = {}
active_window = nil
all_windows = {}
bindings["ALT + J"].action()
assert(#dispatched == 0, "nil active window must stay silent")
checked_focus("left")
assert(#dispatched == 0, "checked_focus with nil window must stay silent")
-- Empty desktops must remain navigable, even through another empty monitor.
for _, spec in ipairs({ {"J", "left", "l"}, {"L", "right", "r"},
    {"I", "up", "u"}, {"K", "down", "d"} }) do
    local target = { id = 0 }
    adjacent_monitors = { [spec[3]] = target }
    active_window, all_windows = nil, {}
    dispatched, monitor_queries = {}, {}
    bindings["ALT + " .. spec[1]].action()
    assert(#dispatched == 1 and dispatched[1].name == "focus"
        and dispatched[1].arg.monitor == target.id,
        "empty desktop must focus adjacent monitor " .. spec[2])
    assert(#monitor_queries == 1 and monitor_queries[1] == spec[3],
        "monitor lookup must use native direction " .. spec[3])
    dispatched, monitor_queries = {}, {}
    checked_focus(spec[2], 100, "0xaaa")
    checked_focus(spec[2], nil, "0xaaa")
    assert(#dispatched == 0 and #monitor_queries == 0,
        "stale guarded Kitty requests must never escape an empty desktop")
    active_window = fake_window("brave-browser", 200, 200, 100, 100, 8)
    all_windows = { active_window }
    dispatched, monitor_queries = {}, {}
    bindings["ALT + " .. spec[1]].action()
    assert(#dispatched == 1 and dispatched[1].arg.monitor == target.id,
        "window edge must permit moving to adjacent empty monitor " .. spec[2])
    local candidate = dir_candidate[spec[2]]
    all_windows = { active_window,
        fake_window("brave-browser", candidate[1], candidate[2], 100, 100, 8) }
    dispatched, monitor_queries = {}, {}
    checked_focus(spec[2])
    assert(#dispatched == 1 and dispatched[1].arg.direction == spec[2]
        and #monitor_queries == 0, "window neighbor must win over monitor fallback")
    active_window = fake_window("kitty", 200, 200, 100, 100, 8, 100, "0xaaa")
    all_windows = { active_window }
    dispatched = {}
    checked_focus(spec[2], 999, "0xaaa")
    checked_focus(spec[2], 100, "0xbbb")
    assert(#dispatched == 0, "caller guards must also protect monitor fallback")
    checked_focus(spec[2], 100, "0xaaa")
    assert(#dispatched == 1 and dispatched[1].arg.monitor == target.id,
        "valid Kitty edge request may focus an empty neighbor monitor")
    adjacent_monitors = {}
    active_window, all_windows = nil, {}
    dispatched = {}
    checked_focus(spec[2])
    assert(#dispatched == 0, "outer monitor edge must not wrap " .. spec[2])
end
adjacent_monitors, monitor_queries = {}, {}
dispatched = {}
active_window = fake_window("brave-browser", 200, 200, 100, 100, 8)
all_windows = { active_window, fake_window("brave-browser", 200, 400, 100, 100, 8) }
checked_focus("diagonal")
assert(#dispatched == 0, "invalid direction must stay silent")
for _, class in ipairs({ "kitty", "quake-kitty" }) do
    dispatched = {}
    active_window = fake_window(class, 200, 200, 100, 100, 8, 100)
    all_windows = { active_window, fake_window("brave-browser", 0, 200, 100, 100, 8) }
    checked_focus("left", 999)
    assert(#dispatched == 0, "mismatched PID must stay silent in " .. class)
    checked_focus("left", 100)
    assert(#dispatched == 1 and dispatched[1].arg.direction == "left",
        "matching PID must dispatch in " .. class)
end
dispatched = {}
active_window = fake_window("brave-browser", 200, 200, 100, 100, 8, 200)
all_windows = { active_window, fake_window("brave-browser", 0, 200, 100, 100, 8) }
checked_focus("left", 200)
assert(#dispatched == 0, "non-Kitty caller must stay silent even with matching PID")
-- Another OS window of the same Kitty process must not satisfy a stale source.
for _, class in ipairs({ "kitty", "quake-kitty" }) do
    dispatched = {}
    local first = fake_window(class, 200, 200, 100, 100, 8, 100, "0xaaa")
    local second = fake_window(class, 400, 200, 100, 100, 8, 100, "0xbbb")
    active_window = second
    all_windows = { first, second }
    checked_focus("left", 100, first.address)
    assert(#dispatched == 0,
        "same PID/class with a different address must reject stale source in " .. class)
    checked_focus("left", nil, first.address)
    assert(#dispatched == 0, "address guard must also work without a PID")
    checked_focus("left", 100, second.address)
    assert(#dispatched == 1 and dispatched[1].arg.direction == "left",
        "matching PID/class/address must dispatch exactly once in " .. class)
end
for _, key in ipairs({ "J", "L", "I", "K" }) do
    assert(bindings["CTRL + ALT + " .. key] == nil,
        "CTRL+ALT+" .. key .. " must stay unbound for resize")
end
-- SHIFT+ALT letters move Hyprland windows.
for _, spec in ipairs({ {"J", "left"}, {"L", "right"}, {"I", "up"}, {"K", "down"} }) do
    is_action("ALT + SHIFT + " .. spec[1], "exec")
    assert(bindings["ALT + SHIFT + " .. spec[1]].action.arg:find("glaze-move-window " .. spec[2], 1, true))
    assert(bindings["CTRL + ALT + SHIFT + " .. spec[2]] == nil,
        "quad focus is letters-only: " .. spec[2])
end
for _, key in ipairs({ "U", "P", "O", "H" }) do is_action("ALT + SHIFT + " .. key, "exec") end
for _, direction in ipairs({ "left", "right", "up", "down" }) do
    assert(bindings["ALT + CTRL + " .. direction] == nil,
        "monitor-arrow move removed, use ALT+SHIFT+J/K/L/I: " .. direction)
end
is_action("SUPER + grave", "exec")
is_action("SUPER + SPACE", "exec")
assert(bindings["SUPER + SPACE"].action.arg:find("hypr-switch-xkblayout", 1, true))
is_action("SUPER + R", "exec")
assert(bindings["SUPER + R"].action.arg:find("rofi -show run", 1, true))
assert(unbound["SUPER + SPACE"], "statusbar bind must be replaced, not duplicated")
is_action("SUPER + CTRL + SPACE", "exec")
is_action("SUPER + SUPER_L", "exec")
assert(bindings["SUPER + SUPER_L"].options.release, "bare Super should trigger on release")
is_action("ALT + SHIFT + R", "exec")
assert(bindings["ALT + SHIFT + R"].action.arg:find("glaze-reset", 1, true))
is_action("ALT + Tab", "exec")
assert(bindings["ALT + Tab"].action.arg == "~/.local/bin/qs-lazy-toggle ~/.local/share/quickshell-overview overview toggle",
    "ALT+Tab should open the same window picker as SUPER+Tab")
assert(unbound["SUPER + Tab"] == nil, "SUPER+Tab must stay bound")
assert(bindings["ALT + SHIFT + W"] == nil, "redraw binding is not requested")

for class, workspace in pairs({
    code = 2, ["code-oss"] = 2,
    kate = 2, ["org.kde.kate"] = 2,
    firefox = 3, ["brave-browser"] = 3,
    obsidian = 4, ["md.obsidian.Obsidian"] = 4,
    ["org.gnome.TextEditor"] = 4,
    Discord = 5, discord = 5,
    Spotify = 7, spotify = 7,
    ["org.kde.kmail2"] = 6, thunderbird = 6,
    geary = 6, evolution = 6,
    kitty = 8, konsole = 8,
    Alacritty = 8,
    steam = 9, heroic = 9, lutris = 9,
}) do
    local rule = assert(rules["glaze-app-" .. class], "missing app rule " .. class)
    assert(rule.workspace == tostring(workspace) .. " silent", "wrong target for " .. class)
    assert(rule.match.modal == false and rule.match.float == false,
        "startup rule must leave modal and floating dialogs with their parent")
    assert(("quake-kitty"):match(rule.match.class) == nil, "Quake must not be sent to terminal workspace")
    assert(("dotfiles-floating"):match(rule.match.class) == nil, "ML4W helper must be exempt")
end
for rule_name, target in pairs({
    ["focus-code"] = 2, ["focus-kate"] = 2,
    ["focus-browser"] = 3, ["focus-term"] = 8,
    ["focus-notes"] = 4,
}) do
    local rule = assert(rules[rule_name], "missing focus rule " .. rule_name)
    assert(rule.workspace == tostring(target), "wrong focus target for " .. rule_name)
end
assert(workspaces["1"] ~= nil, "main workspace must exist with nothing routed to it")
assert(rules["glaze-app-brave-browser"].match.class == "^brave-browser$",
    "hyphenated app IDs must match without a regex escape")
assert(rules["glaze-app-org.kde.kmail2"].match.class == "^org\\.kde\\.kmail2$",
    "dots in app IDs must be literal")
local quake = assert(rules["glaze-quake"], "Quake must have its own window rule")
assert(quake.match.class == "^quake-kitty$", "Quake must match only its Kitty class")
assert(quake.float == true and quake.workspace == "special:quake silent")

print("PASS: workspace, movement, window and launcher bindings")
