-- Execute the real font-picker block without stopping any desktop process.
local source = assert(io.open('vitreus.luau')):read('*a')
local first = assert(source:find('-- ── Settings > Theme: the font picker', 1, true))
local last = assert(source:find('-- A wallpaper that Vitreus sets', first, true))
local chunk = source:sub(first, last - 1)
local function fixture(opts)
    opts = opts or {}
    local s = { events = {}, timers = {}, commands = {}, order = {}, writes = 0, fact = {}, text = {} }
    local env = setmetatable({
        fact = s.fact, text = s.text, iris_fx = {},
        vtheme = { current = function() return { id = 'glass', name = 'Glass' } end,
            font_of = function() return 'Space Grotesk' end },
        on = function(name, fn) s.events[name] = fn end,
        after = function(ms, fn) s.timers[#s.timers + 1] = { ms = ms, fn = fn } end,
        with_dirs = function(fn) fn({ data = '/private/data', conf = '/private/config' }) end,
        sys = {
            ask = function() return {} end,
            call = function(action, name, data)
                assert(action == 'files.write' and name == 'fonts.json')
                if opts.write_fail then error('disk is read-only') end
                s.writes = s.writes + 1
                s.saved = data.glass
                s.order[#s.order + 1] = 'save'
            end,
        },
        run = function(cmd, args, done)
            s.commands[#s.commands + 1] = { cmd = cmd, args = args }
            if cmd == 'env' then
                if table.concat(args, ' '):find('fc%-list') then done('Fira Code\nSpace Grotesk\n', 0)
                else done('/private/font.ttf', 0) end
            elseif cmd == 'systemctl' then
                s.order[#s.order + 1] = 'restart'
                done('', opts.restart_fail and 1 or 0)
            elseif cmd == 'pleamar' then done('false', 0)
            else done('', 0) end
        end,
    }, { __index = _G })
    assert(load(chunk, 'font-picker', 't', env))()
    function s.advance(ms)
        local rest = {}
        for _, timer in ipairs(s.timers) do
            if timer.ms <= ms then timer.fn() else rest[#rest + 1] = timer end
        end
        s.timers = rest
    end
    return s
end

local s = fixture()
s.events.font_pick(1)
s.events.font_apply()
s.events.font_apply()
s.advance(600)
local restart
for _, command in ipairs(s.commands) do
    assert(command.cmd ~= 'pkill', 'font Apply must never kill the main shell, widgets or lock screen')
    if command.cmd == 'systemctl' then restart = command end
end
assert(restart and table.concat(restart.args, ' ') == '--user --no-block restart pleamar.service',
       'Apply must request a nonblocking restart from the sole process owner')
assert(s.saved == 'Fira Code' and s.writes == 1)
assert(table.concat(s.order, ',') == 'save,restart', 'persist once before requesting a restart')
print('PASS managed restart, saved font, duplicate click and no broad process kill')

local failed = fixture({ restart_fail = true })
failed.events.font_pick(1); failed.events.font_apply(); failed.advance(600)
assert(failed.fact.font_applying == false and failed.text.font_note:lower():find('restart'),
       'a rejected restart must leave the current shell up with a visible error')
print('PASS rejected restart is visible and retryable')

local unwritable = fixture({ write_fail = true })
unwritable.events.font_pick(1); unwritable.events.font_apply(); unwritable.advance(600)
for _, command in ipairs(unwritable.commands) do
    assert(command.cmd ~= 'systemctl' and command.cmd ~= 'pkill', 'do not restart with an unsaved font choice')
end
assert(unwritable.text.font_note:lower():find('save'), 'saving errors must be visible')
print('PASS a failed save cannot close the shell')

local unchanged = fixture()
unchanged.events.font_apply(); unchanged.advance(600)
assert(unchanged.writes == 0)
for _, command in ipairs(unchanged.commands) do assert(command.cmd ~= 'systemctl') end
print('PASS unchanged choice does not restart')
