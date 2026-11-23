-- Exercise shortcut registration without dispatching live desktop commands.
local bindings = {}
local function dispatcher(name)
    return setmetatable({}, {
        __index = function(_, key)
            return dispatcher(name == "" and key or name .. "." .. key)
        end,
        __call = function(_, args) return { name = name, args = args } end,
    })
end
local hl = {
    dsp = dispatcher(""),
    bind = function(key, action)
        bindings[key] = bindings[key] or {}
        table.insert(bindings[key], action)
    end,
}
local environment = setmetatable({ hl = hl }, { __index = _G })
assert(loadfile(os.getenv("HOME") .. "/.config/hypr/conf/keybindings/default.lua", "t", environment))()

local failures = 0
local function check(condition, message)
    if condition then
        print("PASS: " .. message)
    else
        failures = failures + 1
        print("FAIL: " .. message)
    end
end
local combined = bindings["SUPER + SHIFT + S"] or {}
check(#combined == 1 and type(combined[1]) == "table"
    and combined[1].name == "exec_cmd"
    and combined[1].args == "~/.config/hypr/scripts/gamemode-dock.sh",
    "Shift+Meta+S runs only the combined game-mode/dock toggle")
check(bindings["SUPER + SHIFT + A"] == nil, "Shift+Meta+A is unbound")
local scratchpad = bindings["SUPER + S"] or {}
check(#scratchpad == 1 and scratchpad[1].name == "workspace.toggle_special"
    and scratchpad[1].args == "scratchpad", "plain Meta+S is unchanged")
assert(failures == 0, tostring(failures) .. " shortcut regression(s)")
