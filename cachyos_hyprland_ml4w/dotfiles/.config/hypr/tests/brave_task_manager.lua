-- Check the rule registered by the real personal Hyprland configuration.
local root = os.getenv("HOME") .. "/.config/hypr/"
local rules = {}
local function operation(name)
    return function(arg) return { name = name, arg = arg } end
end

hl = {
    bind = function() end,
    unbind = function() end,
    on = function() end,
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

local rule = assert(rules["float-brave-task-manager"],
    "Brave Task Manager needs a dedicated floating rule")
assert(rule.match.title == "^Task Manager - Brave$",
    "the rule must target only the observed Brave Task Manager title")
assert(rule.float == true and rule.center == true,
    "Task Manager should float and center by default")
assert(rule.workspace == nil, "Task Manager should stay on its current workspace")
print("PASS: Brave Task Manager floating rule")
