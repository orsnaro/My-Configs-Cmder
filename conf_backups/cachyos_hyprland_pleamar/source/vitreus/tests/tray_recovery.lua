-- Exercise the real tray adapter with an inert D-Bus boundary.
local choice = arg[1]
local function sandbox(options)
    options = options or {}
    local s = { watchers = {}, events = {}, registered = {}, commands = {}, scans = 0 }
    local owner = {
        ['org.kde.StatusNotifierItem-proton'] = ':1.10',
        ['org.kde.StatusNotifierItem-alias'] = ':1.10',
        ['org.example.Existing'] = ':1.10',
    }
    local payloads, next_payload = {}, 0
    local env = setmetatable({ fact = {}, text = {}, model = {} }, { __index = _G })
    env.on = function(name, fn) s.events[name] = fn end
    env.after = function() error('tray recovery must not install a retry timer') end
    env.every = function() error('tray recovery must not poll') end
    env.json = { decode = function(out) return assert(payloads[out], 'unexpected JSON payload') end }
    env.sys = {
        ask = function() return {} end,
        call = function() end,
        watch = function(name, fn) s.watchers[name] = fn end,
    }
    env.run = function(command, args, callback)
        assert(command == 'busctl', 'recovery must not scan processes or start a daemon')
        s.commands[#s.commands + 1] = args
        assert(args[3] == '--timeout=2s', 'D-Bus recovery calls need a bounded timeout')
        local function reply(data, code)
            next_payload = next_payload + 1
            local token = tostring(next_payload)
            payloads[token] = { data = data }
            callback(token, code or 0)
        end
        if args[8] == 'ListNames' then
            s.scans = s.scans + 1
            if options.fail_scan then return reply(nil, 1) end
            return reply({options.names or {
                'org.kde.StatusNotifierWatcher', 'org.example.Unrelated',
                'org.kde.StatusNotifierItem-proton', 'org.kde.StatusNotifierItem-alias',
            }})
        elseif args[8] == 'GetNameOwner' then
            return reply({owner[args[10]]}, owner[args[10]] and 0 or 1)
        elseif args[4] == 'get-property' then
            assert(args[6] == '/StatusNotifierItem' and args[8] == 'Id')
            return reply('proton.vpn.app.gtk', options.disappeared and 1 or 0)
        elseif args[8] == 'RegisterStatusNotifierItem' then
            s.registered[#s.registered + 1] = args[10]
            return reply({})
        end
        error('unexpected D-Bus operation: ' .. table.concat(args, ' '))
    end
    assert(loadfile('logic/tray.luau', 't', env))()(function() end)
    s.env = env
    return s
end

local tests = {}
function tests.early_app()
    local s = sandbox()
    s.watchers.tray({})
    assert(#s.registered == 1, 'existing advertised Proton item was not recovered exactly once')
    assert(s.registered[1] == 'org.kde.StatusNotifierItem-proton', 'unrelated service was registered')
    assert(s.scans == 1, 'startup discovery must run exactly once')
end
function tests.existing_alias()
    for _, key in ipairs({':1.10/StatusNotifierItem', 'org.example.Existing/StatusNotifierItem'}) do
        local s = sandbox()
        s.watchers.tray({{ key = key, id = 'proton.vpn.app.gtk' }})
        assert(#s.registered == 0, 'an already registered item was duplicated through its bus alias')
    end
end
function tests.failed_or_gone()
    for _, options in ipairs({{fail_scan = true}, {disappeared = true},
                              {names = {'org.kde.StatusNotifierItem-gone'}}}) do
        local s = sandbox(options)
        s.watchers.tray({})
        assert(#s.registered == 0, 'a failed or disappeared item must not be registered')
        assert(#s.env.model.bartrays == 0, 'failed recovery must not invent a tray entry')
    end
end
function tests.event_updates()
    local s = sandbox()
    s.watchers.tray({})
    local operations = #s.commands
    s.watchers.tray({{key = ':1.10/StatusNotifierItem', id = 'proton.vpn.app.gtk', icon = 'vpn'}})
    assert(#s.env.model.bartrays == 1, 'recovered event did not reach the normal tray renderer')
    s.watchers.tray({{key = ':1.11/StatusNotifierItem', id = 'later', icon = 'later'}})
    assert(#s.env.model.bartrays == 1 and s.env.model.bartrays[1].icon == 'later', 'later apps must still arrive through events')
    s.watchers.tray({})
    assert(#s.env.model.bartrays == 0, 'departed apps must disappear')
    assert(#s.commands == operations and s.scans == 1, 'normal tray events started extra discovery work')
end
assert(tests[choice], 'unknown recovery test')()
print('tray recovery ' .. choice .. ': PASS')
