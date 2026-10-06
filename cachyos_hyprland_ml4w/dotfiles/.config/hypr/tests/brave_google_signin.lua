-- Repro: Brave Google sign-in popup starts as Untitled, then navigates to Sign in.
-- Hyprland static effects evaluate once at open, so title==initialTitle at match time.
-- Old rule required title="^Sign in..." + initial_title="^Untitled...", which can never both match at open.
local root = os.getenv("HOME") .. "/.config/hypr/"
local rules = {}
local function operation(name)
    return function(arg) return { name = name, arg = arg } end
end

hl = {
    bind = function() end,
    unbind = function() end,
    on = function() end,
    config = function() end,
    env = function() end,
    exec_cmd = operation("exec"),
    workspace_rule = function() end,
    window_rule = function(rule) rules[rule.name] = rule end,
    layer_rule = function(...) end,
    config = function(...) end,
    dsp = {
        exec_cmd = operation("exec"),
        focus = operation("focus"),
        window = {
            move = operation("move"),
            float = operation("float"),
            fullscreen = operation("fullscreen"),
            resize = operation("resize"),
        },
        workspace = { toggle_special = operation("toggle_special") },
    },
}
dofile(root .. "custom.lua")

local rule = assert(rules["float-brave-google-signin"],
    "FAIL: missing float-brave-google-signin rule")

-- Simulate Hyprland static matching at window open:
-- observed popup: class brave-browser, title Untitled - Brave, initial Untitled - Brave
-- (later navigates to Sign in - Google Accounts - Brave, but static rules never re-evaluate)

local m = rule.match
-- Static float evaluates once at open when title==initialTitle==Untitled,
-- so rule must NOT require final "Sign in" title. It must match popups
-- (Untitled) while excluding main windows (New Tab).
assert(m.title == nil,
    "FAIL: static rule must not match final title (never fires at open, see window-rules docs).")
assert(m.class and m.class:find("brave-browser", 1, true),
    "FAIL: rule must match brave-browser class")
assert(m.initial_title and m.initial_title:find("Untitled", 1, true),
    "FAIL: rule must match Untitled initial_title to catch popups at open")
assert(rule.float == true and rule.center == true,
    "FAIL: rule must float+center")
print("PASS: Brave Google sign-in floats at open")
