-- Palette pusher: one client per scene at a time, newest waiting palette, one retry on failure.
local factory = assert(loadfile('logic/palette_push.luau'))()

local calls, timers, now = {}, {}, 0
run = function(_, args, cb)
    calls[#calls + 1] = { scene = args[2], msg = args[3], cb = cb, done = false }
end
local function advance(ms)
    now = now + ms
    local n = #timers
    for i = 1, n do
        local t = timers[i]
        if not t.fired and not t.cancelled and t.at <= now then
            t.fired = true
            t.fn()
        end
    end
end
local function new_world()
    calls, timers, now = {}, {}, 0
    local clock = {
        after = function(ms, fn)
            local t = { at = now + ms, fn = fn }
            timers[#timers + 1] = t
            return t
        end,
        cancel = function(t) t.cancelled = true end,
    }
    return factory(clock), clock
end
local function pending(scene)
    for i = 1, #calls do
        local c = calls[i]
        if c.scene == scene and not c.done then return i, c end
    end
end
local function flush(scene, code)
    local i, c = pending(scene)
    assert(c, "no pending call for " .. scene)
    c.done = true
    c.cb("", code or 0)
    return i
end
local function last(scene)
    for i = #calls, 1, -1 do
        if calls[i].scene == scene then return calls[i].msg end
    end
end
local function unflushed(scene)
    local n = 0
    for i = 1, #calls do
        if calls[i].scene == scene and not calls[i].done then n = n + 1 end
    end
    return n
end

local SCENES = { 'clock', 'cards', 'edit' }
local function argv(scene, msg) return { '--say', scene, msg } end

-- A, B, A while A is in flight: B is dropped, A is sent again, per scene.
local push = new_world()
for _, s in ipairs(SCENES) do push(s, argv(s, s .. ':A')) end
for _, s in ipairs(SCENES) do push(s, argv(s, s .. ':B')) end
for _, s in ipairs(SCENES) do push(s, argv(s, s .. ':A')) end
assert(#calls == 3, 'only the first palette should be in flight')
for _, s in ipairs(SCENES) do assert(unflushed(s) == 1, 'one client per scene at a time') end
for i = #SCENES, 1, -1 do flush(SCENES[i], 0) end
assert(#calls == 6, 'each scene should receive the newest palette once')
for _, s in ipairs(SCENES) do
    assert(last(s) == s .. ':A', 'the round trip must finish on A, not the middle palette')
    assert(unflushed(s) == 1, 'the repair palette should be the current client')
    flush(s, 0)
end
assert(#calls == 6, 'a successful scene must not duplicate its palette')

-- A stuck scene must not hold up the other scenes.
push = new_world()
push('clock', argv('clock', 'clock:A'))
push('cards', argv('cards', 'cards:A'))
flush('cards', 0)
push('clock', argv('clock', 'clock:B'))
push('cards', argv('cards', 'cards:B'))
assert(last('cards') == 'cards:B', 'cards must not wait for clock')
assert(unflushed('clock') == 1, 'clock still has its first client')
flush('clock', 0)
assert(last('clock') == 'clock:B', 'clock then moves to the newest palette')
flush('clock', 0)

-- A failed client is retried once, and the retry carries the newest palette.
push = new_world()
push('clock', argv('clock', 'clock:A'))
push('clock', argv('clock', 'clock:B'))
assert(#calls == 1, 'B waits for A')
flush('clock', 1)
assert(#calls == 2 and last('clock') == 'clock:B', 'retry must carry B, not the failed A')
flush('clock', 1)
assert(#calls == 2, 'a second failure must not retry forever')
push('clock', argv('clock', 'clock:C'))
assert(#calls == 3 and last('clock') == 'clock:C', 'a later palette must still get through')

-- A client that never answers is released by the watchdog; its late callback is ignored.
push = new_world()
push('clock', argv('clock', 'clock:A'))
assert(#calls == 1)
advance(5000)
assert(#calls == 2 and last('clock') == 'clock:A', 'watchdog must retry the stuck palette')
calls[1].done = true
calls[1].cb('', 0)
assert(#calls == 2, 'a late callback must not start another client')
flush('clock', 0)
assert(#calls == 2)

-- Re-picking the same palette is a repair, not a no-op.
push = new_world()
push('clock', argv('clock', 'clock:A'))
flush('clock', 0)
push('clock', argv('clock', 'clock:A'))
assert(#calls == 2 and last('clock') == 'clock:A', 'same palette must still be delivered')

print('palette push single-flight contracts: PASS')
