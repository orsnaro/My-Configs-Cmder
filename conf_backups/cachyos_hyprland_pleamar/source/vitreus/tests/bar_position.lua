-- Exercise the frame-gap original read with synthetic Hyprland output; no desktop commands run.
-- A generated frame room (76 px on the framed edge) must never become the next run's original.
local function fixture(pos, css)
    local state = { applied = 0, bar_fx = {} }
    local env = setmetatable({
        fact = {},
        bar_fx = state.bar_fx,
        iris_fx = {
            apply_hypr = function() state.applied = state.applied + 1 end,
            push_room = function() end,
        },
        on = function(name, fn) state[name] = fn end,
        sys = {
            ask = function(_, name, kind)
                assert(name == 'bar-position.json' and kind == 'json')
                return { pos = pos }
            end,
            call = function() end,
        },
        run = function(cmd, args, fn)
            assert(cmd == 'hyprctl' and args[1] == 'getoption')
            fn('{"css":"' .. css .. '"}', 0)
        end,
    }, { __index = _G })
    local controller = assert(loadfile('logic/bar_position.luau', 't', env))()
    controller()
    return state
end

local function same(actual, expected)
    assert(#actual == #expected, 'wrong gap count')
    for i, v in ipairs(expected) do assert(actual[i] == v, ('gap %d: %s, wanted %s'):format(i, tostring(actual[i]), tostring(v))) end
end

-- The current bug: a generated top frame room was read as the user's original, then copied to both side monitors.
local generated_top = fixture('ftop', '76 24 24 24')
same(generated_top.bar_fx.orig, { 16, 16, 16, 16 })
assert(generated_top.applied == 1, 'the read must apply the corrected gaps once')

-- A normal top gap is still the original.
local clean_top = fixture('ftop', '16 16 16 16')
same(clean_top.bar_fx.orig, { 16, 16, 16, 16 })

-- The same guard works for a left strip, whose wide edge is the left gap.
local generated_left = fixture('left', '24 24 24 76')
same(generated_left.bar_fx.orig, { 16, 16, 16, 16 })

-- A top Island does not own a frame room; a user's 76 px top gap is kept.
local island = fixture('top', '76 24 24 24')
same(island.bar_fx.orig, { 76, 24, 24, 24 })

print('bar position gap-origin contracts: PASS')
