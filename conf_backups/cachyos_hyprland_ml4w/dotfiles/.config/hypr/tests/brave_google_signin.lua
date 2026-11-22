-- Run the real configuration against isolated window events and dispatcher calls.
local root = os.getenv("HOME") .. "/.config/hypr/"
local rules, callbacks, calls = {}, {}, {}
local focused = { address = "0xfocused", floating = false }
local during_dispatch

local function operation(name)
    return function(arg) return { name = name, arg = arg } end
end

local function emit(event, window)
    for _, callback in ipairs(callbacks[event] or {}) do callback(window) end
end

hl = {
    bind = function() end,
    unbind = function() end,
    on = function(event, callback)
        callbacks[event] = callbacks[event] or {}
        table.insert(callbacks[event], callback)
    end,
    env = function() end,
    exec_cmd = operation("exec"),
    workspace_rule = function() end,
    window_rule = function(rule) rules[rule.name] = rule end,
    layer_rule = function() end,
    config = function() end,
    dispatch = function(action)
        table.insert(calls, action)
        local args = action.arg
        local target = args.window or focused
        if action.name == "float" then
            if args.action == "on" or args.action == "enable" then
                target.floating = true
            elseif args.action == "off" or args.action == "disable" then
                target.floating = false
            else
                target.floating = not target.floating
            end
        elseif action.name == "resize" then
            target.size = { x = args.x, y = args.y }
        elseif action.name == "center" then
            target.centered = true
        end
        if during_dispatch then during_dispatch(target) end
        return { ok = true }
    end,
    dsp = {
        exec_cmd = operation("exec"),
        focus = operation("focus"),
        window = {
            move = operation("move"),
            float = operation("float"),
            fullscreen = operation("fullscreen"),
            resize = operation("resize"),
            center = operation("center"),
        },
        workspace = { toggle_special = operation("toggle_special") },
    },
}
dofile(root .. "custom.lua")

local function window(address, title, class)
    return {
        address = address, class = class or "brave-browser",
        title = title, initial_title = title, mapped = true,
        floating = false, size = { x = 1300, y = 800 },
    }
end

-- Characterize the exact literal class/title predicates used by the old rule.
-- This is not a general RE2 emulator; other rule engines are outside this test.
local function literal_match(pattern, value)
    return pattern == nil or pattern == value or pattern == "^" .. value .. "$"
end

local function open(w)
    for _, rule in pairs(rules) do
        local match = rule.match
        if rule.float == true and literal_match(match.class, w.class)
            and literal_match(match.title, w.title)
            and literal_match(match.initial_title, w.initial_title) then
            w.floating = true
        end
    end
    emit("window.open", w)
end

local main = window("0xmain", "Untitled - Brave")
open(main)
assert(not main.floating, "ordinary hyperlink window must stay tiled at Untitled startup")
main.title = "Example Domain - Brave"
emit("window.title", main)
assert(not main.floating and #calls == 0,
    "ordinary hyperlink window must stay tiled after its page title loads")
print("PASS: ordinary Untitled hyperlink window stays tiled")

local signin_title = "Sign in - Google Accounts - Brave"
local function assert_signin(w)
    assert(w.floating, "matching sign-in window must float")
    assert(w.size.x == 600 and w.size.y == 700 and w.centered,
        "matching sign-in window must be centered at 600x700")
    assert(#calls == 3, "sign-in must dispatch float, resize, and center once")
    for index, name in ipairs({ "float", "resize", "center" }) do
        assert(calls[index].name == name, "incorrect sign-in operation order")
        assert(calls[index].arg.window == w, "operation must target the event window")
    end
    assert(calls[1].arg.action == "on", "enable floating explicitly; never toggle")
    assert(calls[2].arg.relative ~= true, "sign-in dimensions must be absolute")
    assert(not focused.floating and focused.size == nil and not focused.centered,
        "background sign-in event must not affect the focused unrelated window")
end

local delayed = window("0xdelayed", "Untitled - Brave")
open(delayed)
assert(not delayed.floating and #calls == 0, "wait for an actual sign-in title")
delayed.title = signin_title
emit("window.title", delayed)
assert_signin(delayed)
print("PASS: delayed sign-in title floats only its own window")

calls = {}
emit("window.open", delayed)
emit("window.title", delayed)
assert(#calls == 0, "duplicate open/title events must not resize or toggle again")
delayed.floating = false
delayed.size = { x = 900, y = 800 }
delayed.centered = false
emit("window.title", delayed)
assert(not delayed.floating and delayed.size.x == 900 and not delayed.centered and #calls == 0,
    "later title updates must respect manual tiling and resizing")
print("PASS: repeated events preserve manual window changes")

calls = {}
local immediate = window("0ximmediate", signin_title)
open(immediate)
assert_signin(immediate)
print("PASS: sign-in title already present at open is handled")

calls = {}
local floating = window("0xfloating", signin_title)
floating.floating = true
open(floating)
assert_signin(floating)
print("PASS: already-floating sign-in is not toggled back to tiled")

calls = {}
for index, fixture in ipairs({
    { "brave-browser", "New Tab - Brave" },
    { "brave-browser", "Untitled - Brave" },
    { "brave-browser", "Example Domain - Brave" },
    { "brave-browser", "Sign in - Google Accounts - Brave - Example" },
    { "brave-browser", "Example Sign in - Google Accounts - Brave" },
    { "brave-browser", "Task Manager - Brave" },
    { "firefox", signin_title },
    { "brave-mail.google.com__-Default", signin_title },
    { "Brave-browser", signin_title },
}) do
    local other = window("0xother" .. index, fixture[2], fixture[1])
    emit("window.open", other)
    emit("window.title", other)
    assert(not other.floating and not other.centered and other.size.x == 1300,
        "nonmatching window must stay unchanged: " .. fixture[1] .. " / " .. fixture[2])
end
assert(#calls == 0, "nonmatching events must dispatch nothing")
print("PASS: wrong classes and title lookalikes are ignored")

local unmapped = window("0xunmapped", signin_title)
unmapped.mapped = false
for _, event in ipairs({ "window.open", "window.title", "window.close" }) do
    emit(event, nil)
end
emit("window.open", unmapped)
emit("window.title", unmapped)
assert(not unmapped.floating and #calls == 0, "unmapped sign-in must be ignored")
unmapped.mapped = true
emit("window.open", unmapped)
assert_signin(unmapped)
print("PASS: nil/unmapped events are safe and do not consume later mapped events")

calls = {}
delayed.mapped = false
emit("window.close", delayed)
local reused = window("0xdelayed", signin_title)
open(reused)
assert_signin(reused)
print("PASS: closing a window clears state before address reuse")

calls = {}
local reentrant = window("0xreentrant", signin_title)
during_dispatch = function(w) emit("window.title", w) end
open(reentrant)
during_dispatch = nil
assert_signin(reentrant)
print("PASS: handling is marked before dispatch to prevent reentrant operations")
