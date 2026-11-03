-- Exercise the real personal config without launching desktop applications.
local root = os.getenv("HOME") .. "/.config/hypr/"
local rules, handlers, commands = {}, {}, {}
local function operation(name)
    return function(arg) return { name = name, arg = arg } end
end
hl = {
    bind = function() return { set_enabled = function() end } end,
    get_layers = function() return {} end,
    animation = function() end,
    unbind = function() end, env = function() end,
    on = function(event, callback)
        handlers[event] = handlers[event] or {}
        table.insert(handlers[event], callback)
    end,
    exec_cmd = function(command) table.insert(commands, command) end,
    workspace_rule = function() end,
    window_rule = function(rule) rules[rule.name] = rule end,
    layer_rule = function() end, config = function() end,
    dsp = {
        exec_cmd = operation("exec"), focus = operation("focus"),
        window = { move = operation("move"), float = operation("float"),
            fullscreen = operation("fullscreen"), resize = operation("resize") },
        workspace = { toggle_special = operation("toggle_special") },
    },
}
dofile(root .. "custom.lua")
assert(#commands == 0, "reading/reloading config must not start mail immediately")
local mapped = assert(rules["glaze-app-aerc-mail"], "aerc-mail needs an exact TSV mail-workspace mapping")
assert(mapped.match.class == "^aerc-mail$" and mapped.workspace == "6 silent",
    "aerc-mail must route only its own class silently to workspace 6")
local tiled = assert(rules["glaze-mail-tiled"], "mail needs an explicit tiled rule")
assert(tiled.match.class == "^aerc-mail$" and tiled.float == false and tiled.workspace == "6 silent",
    "the mail window must remain tiled on workspace 6")
for _, callback in ipairs(assert(handlers["hyprland.start"])) do callback() end
local count = 0
for _, command in ipairs(commands) do
    if command == "~/.local/bin/glaze-mail" then count = count + 1 end
end
assert(count == 1, "Hyprland desktop startup must invoke the owned mail launcher exactly once")
print("PASS: mail exact-class workspace-6 tiling and Hyprland-only startup")
