-- Vitreus bindings contract test for hypr_vitreus.lua.
-- Stubs the Hyprland API; it never runs a real command.
local bound, unbound, dispatched = {}, {}, {}
local cursor_monitor = { name = "DP-2" }

local hl = {
    dsp = { exec_cmd = function(cmd) return { __cmd = cmd } end },
    bind = function(key, action, opts)
        bound[#bound + 1] = { key = key, action = action, opts = opts or {} }
    end,
    unbind = function(key) unbound[#unbound + 1] = key end,
    dispatch = function(action) dispatched[#dispatched + 1] = action end,
    get_monitor_at_cursor = function() return cursor_monitor end,
}

local chunk, err = loadfile("hypr_vitreus.lua", "t", { hl = hl, ipairs = ipairs })
assert(chunk, "cannot load hypr_vitreus.lua: " .. tostring(err))
chunk()

local failures = {}
local function check(name, cond)
    if cond then
        print("ok - " .. name)
    else
        failures[#failures + 1] = name
        print("FAIL - " .. name)
    end
end

local function bindsFor(key)
    local out = {}
    for _, b in ipairs(bound) do
        if b.key == key then out[#out + 1] = b end
    end
    return out
end

local say = 'PATH="$HOME/.local/bin:$PATH" pleamar --say vitreus'
local expected = say .. ' "emit wp_picker_toggle"'

local w = bindsFor("SUPER + W")
check("exactly one SUPER + W binding", #w == 1)
check("SUPER + W invokes the wallpaper picker command",
    #w == 1 and w[1].action and w[1].action.__cmd == expected)

local meta = bindsFor("SUPER + SUPER_L")
check("bare Meta binding preserved", #meta == 1)
check("bare Meta keeps the release flag", #meta == 1 and meta[1].opts.release == true)

local over = say .. ' "emit ov_toggle"'
local alt = bindsFor("ALT + Tab")
local sup = bindsFor("SUPER + Tab")
check("ALT + Tab overview preserved", #alt == 1 and alt[1].action.__cmd == over)
check("SUPER + Tab overview preserved", #sup == 1 and sup[1].action.__cmd == over)

local function touches(key)
    for _, b in ipairs(bound) do
        if b.key == key then return true end
    end
    for _, k in ipairs(unbound) do
        if k == key then return true end
    end
    return false
end
check("SUPER + Space not bound or unbound", not touches("SUPER + Space"))
check("SUPER + B not bound or unbound", not touches("SUPER + B"))

for _, button in ipairs({ "mouse:272", "mouse:273" }) do
    local bindings = bindsFor(button)
    check(button .. " has one non-consuming click-away binding",
        #bindings == 1 and bindings[1].opts.non_consuming == true
            and type(bindings[1].action) == "function")
    if #bindings == 1 and type(bindings[1].action) == "function" then
        cursor_monitor = { name = "DP-2" }
        local before = #dispatched
        bindings[1].action()
        check(button .. " leaves DP-2 to the existing scene handlers", #dispatched == before)

        for _, monitor in ipairs({ "DP-1", "HDMI-A-2" }) do
            cursor_monitor = { name = monitor }
            bindings[1].action()
            local command = dispatched[#dispatched] and dispatched[#dispatched].__cmd
            check(button .. " on " .. monitor .. " reads panel with one Pleamar command argument",
                #dispatched == before + 1 and type(command) == "string"
                    and command:find('pleamar --say vitreus "get panel"', 1, true)
                    and command:find("= launch", 1, true)
                    and command:find("fact panel none", 1, true))
            before = #dispatched
        end
    end
end

if #failures > 0 then
    print(#failures .. " check(s) failed")
    os.exit(1)
end
print("all checks passed")
