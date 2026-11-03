local bindings = {}
local function dispatcher()
    return setmetatable({}, {
        __index = function() return dispatcher() end,
        __call = function() return function() end end,
    })
end
local hl = {
    dsp = dispatcher(),
    bind = function(key, action, options)
        if options and options.mouse then
            bindings[key] = (bindings[key] or 0) + 1
        end
    end,
}
local path = os.getenv("HOME") .. "/.config/hypr/conf/keybindings/default.lua"
local environment = setmetatable({ hl = hl }, { __index = _G })
assert(loadfile(path, "t", environment))()
for _, key in ipairs({ "SUPER + mouse:272", "SUPER + mouse:273" }) do
    assert(bindings[key] == 1, key .. " must register once, got " .. tostring(bindings[key]))
end
print("PASS: one mouse drag and one mouse resize binding")
