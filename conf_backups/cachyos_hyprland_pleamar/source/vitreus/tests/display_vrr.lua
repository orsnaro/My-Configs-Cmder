-- Execute the real Display handlers; monitor requests and file writes are inert.
local source = assert(io.open('vitreus.luau')):read('a')
local first = assert(source:find('-- ── Display ─', 1, true))
local last = assert(source:find('-- ── Weather,', first, true))
local block = source:sub(first, last - 1)

local function copy(value)
    if type(value) ~= 'table' then return value end
    local out = {}
    for k, v in pairs(value) do out[k] = copy(v) end
    return out
end

local function sandbox(options)
    options = options or {}
    local s = { events = {}, timers = {}, writes = {}, requests = {}, clock = 0, recurring = {} }
    s.monitors = {
        {name = 'DP-2', description = 'Main', make = 'Xiaomi', model = 'Mi', serial = '1',
         width = 2560, height = 1440, refreshRate = 180, x = 2404, y = 381,
         scale = 1, transform = 0, sdrBrightness = 1, sdrSaturation = 1, vrr = false,
         currentFormat = 'XRGB2101010', colorManagementPreset = 'srgb', availableModes = {'2560x1440@180Hz'}},
        {name = 'HDMI-A-2', description = 'Left', width = 1366, height = 768,
         refreshRate = 59.79, x = 1038, y = 768, scale = 1, transform = 0,
         vrr = true, currentFormat = 'XRGB8888', availableModes = {'1366x768@59.79Hz'}},
    }
    local env = setmetatable({fact = {}, text = {}, on_niri = options.niri or false}, {__index = _G})
    env.on = function(name, fn) s.events[name] = fn end
    env.after = function(ms, fn) s.timers[#s.timers + 1] = {at = s.clock + ms, fn = fn} end
    env.every = function(ms, fn) s.recurring[ms] = fn end
    env.json = {decode = function() return copy(s.monitors) end}
    env.hypr_monitors = function(_, cb) cb('monitors-json', 0) end
    env.with_dirs = function(fn) fn({data = '/data/vitreus', conf = '/config/pleamar/shells/vitreus'}) end
    env.set_panel = function() end
    env.iris_fx = {apply_niri = function() end}
    env.sys = {
        ask = function(_, name)
            if name == 'display-profiles.json' then return options.profiles end
        end,
        call = function(service, name, value)
            assert(service == 'files.write')
            s.writes[name] = copy(value)
        end,
    }
    env.run = function(command, args, callback)
        if command == 'hyprctl' then
            assert(args[1] == 'eval')
            if options.reject then return callback('rejected', 1) end
            local context = {hl = {monitor = function(request)
                s.requests[#s.requests + 1] = copy(request)
                for _, m in ipairs(s.monitors) do
                    if m.name == request.output then
                        local x, y = request.position:match('^(%-?%d+)x(%-?%d+)$')
                        m.x, m.y = tonumber(x), tonumber(y)
                        local w, h, hz = request.mode:match('^(%d+)x(%d+)@([%d.]+)$')
                        m.width, m.height, m.refreshRate = tonumber(w), tonumber(h), tonumber(hz)
                        m.scale, m.transform = request.scale, request.transform
                        if request.vrr ~= nil then m.vrr = request.vrr > 0 end
                        if request.bitdepth ~= nil then m.currentFormat = request.bitdepth == 10 and 'XRGB2101010' or 'XRGB8888' end
                    end
                end
            end}}
            assert(load(args[2], 'monitor request', 't', context))()
            return callback('ok', 0)
        end
        if callback then callback('', 0) end
    end
    function s.advance(ms)
        local target = s.clock + ms
        while true do
            table.sort(s.timers, function(a, b) return a.at < b.at end)
            if not s.timers[1] or s.timers[1].at > target then break end
            local timer = table.remove(s.timers, 1)
            s.clock = timer.at
            timer.fn()
        end
        s.clock = target
    end
    assert(load(block, 'Display', 't', env))()
    s.env = env
    return s
end

local function toggle(s)
    assert(s.events.disp_vrr_toggle, 'Display has no VRR toggle handler')()
end

local tests = {}
function tests.selected_monitor()
    local s = sandbox()
    assert(s.env.fact.disp_vrr_available == true, 'VRR control is not enabled on Hyprland')
    assert(s.env.fact.disp_vrr == false, 'main-monitor state is not read')
    s.events.disp_pick_mon(1)
    assert(s.env.fact.disp_vrr == true, 'switch does not follow the selected monitor')
    toggle(s)
    assert(s.env.fact.disp_vrr == false and s.env.fact.disp_dirty, 'toggle did not edit the draft')
    s.events.disp_reset()
    assert(s.env.fact.disp_vrr == true and not s.env.fact.disp_dirty, 'Reset did not restore live VRR')
end
function tests.apply_and_revert()
    local s = sandbox()
    toggle(s)
    s.events.disp_apply()
    s.advance(900)
    assert(#s.requests == 1 and s.requests[1].output == 'DP-2', 'VRR-only Apply touched another monitor')
    local r = s.requests[1]
    assert(r.vrr == 1 and r.bitdepth == 10, 'Apply lost VRR or 10-bit output')
    assert(r.position == '2404x381' and r.mode == '2560x1440@180', 'VRR-only Apply moved or changed the mode')
    assert(s.env.fact.disp_trial == 15, 'VRR changes need the normal safety trial')
    s.events.disp_revert()
    s.advance(900)
    assert(s.requests[2].vrr == 0 and s.requests[2].bitdepth == 10, 'Revert did not restore previous VRR/bitdepth')
end
function tests.keep_and_profiles()
    local s = sandbox()
    toggle(s)
    s.events.disp_apply()
    s.advance(900)
    s.events.disp_keep()
    local saved = assert(s.writes['display.json']).saved
    assert(saved['DP-2'].vrr == 1 and saved['DP-2'].bitdepth == 10, 'Keep did not persist VRR and bit depth')
    assert(saved['HDMI-A-2'].hz == 59.79, 'Keep rounded an untouched monitor refresh rate')
    local persisted = {}
    assert(load(s.writes['vitreus_monitors.lua'], 'saved settings', 't', {hl = {monitor = function(r) persisted[r.output] = r end}}))()
    assert(persisted['DP-2'].vrr == 1 and persisted['DP-2'].bitdepth == 10, 'restart config lost VRR or bit depth')
    s.events.disp_profile_save()
    assert(s.writes['display-profiles.json'].profiles[1].mons['DP-2'].vrr == 1, 'profile save lost VRR')
end
function tests.old_profile_and_rejection()
    local s = sandbox({profiles = {profiles = {{name = 'Old', mons = {['DP-2'] = {
        res = '2560x1440', hz = 144, x = 2404, y = 381, scale = 1, transform = 0,
    }}}}}})
    s.events.disp_profile_apply(0)
    s.advance(900)
    assert(#s.requests == 1, 'old profile did not apply cleanly')
    assert(s.monitors[1].currentFormat == 'XRGB2101010', 'legacy profile downgraded bit depth')
    local rejected = sandbox({reject = true})
    toggle(rejected)
    rejected.events.disp_apply()
    rejected.advance(900)
    assert(not rejected.writes['display.json'] and not rejected.writes['vitreus_monitors.lua'], 'rejected VRR was saved')
end
function tests.timeout_and_backend()
    local s = sandbox()
    toggle(s)
    s.events.disp_apply()
    s.advance(900)
    for _ = 1, 15 do s.recurring[1000]() end
    s.advance(900)
    assert(s.requests[2].vrr == 0, 'unconfirmed VRR did not revert after timeout')
    local other = sandbox({niri = true})
    assert(other.env.fact.disp_vrr_available == false, 'Hyprland-only toggle enabled under Niri')
end
local name = arg[1]
assert(tests[name], 'unknown Display test')()
print('Display VRR ' .. name .. ': PASS')
