-- Obsidian Settings must float on the current workspace/monitor,
-- while the main Obsidian window stays pinned to workspace 4.
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

local rule = assert(rules["float-obsidian-settings"],
    "Obsidian Settings needs a dedicated floating rule")
assert(rule.match.class and rule.match.class:find("obsidian", 1, true),
    "the rule must match the Obsidian window class")
assert(rule.match.title and rule.match.title:find("Settings", 1, true),
    "the rule must target only the Settings title")
assert(rule.float == true and rule.center == true,
    "Settings should float and center by default")
assert(rule.workspace == nil, "Settings should stay on its current workspace")

local notes = assert(rules["focus-notes"], "main Obsidian routing must still exist")
assert(notes.workspace == "4", "main Obsidian window must stay on workspace 4")
assert(notes.match.modal == false,
    "main Obsidian rule must exclude modals so Settings is not dragged to workspace 4")
print("PASS: Obsidian Settings floating rule")
