-- One palette message per scene at a time, newest last. A scene that exits
-- before consuming the facts is retried once; a client that never answers is
-- released by a watchdog so one stuck scene cannot wedge the rest.
-- `clock` is injectable so tests/ can drive time without sleeping.
return function(clock)
    clock = clock or { after = after, cancel = cancel }
    local pending, busy, failed = {}, {}, {}

    local function pump(scene)
        if busy[scene] then return end
        local message = pending[scene]
        if not message then return end
        pending[scene] = nil
        local token = {}
        busy[scene] = token
        local watchdog

        local function finish(code)
            if busy[scene] ~= token then return end   -- a watchdog already moved on
            busy[scene] = nil
            if watchdog and clock.cancel then clock.cancel(watchdog) end
            if code ~= 0 and not failed[scene] then
                failed[scene] = true
                pending[scene] = pending[scene] or message
            else
                failed[scene] = nil
            end
            pump(scene)
        end

        -- The client has a 65 s read timeout; five seconds is enough to say it is stuck.
        watchdog = clock.after(5000, function() finish(-1) end)
        local ok, err = pcall(run, "pleamar", message, function(_, code) finish(code) end)
        if not ok then
            if log then log("palette push to " .. scene .. " failed: " .. tostring(err)) end
            finish(-1)
        end
    end

    return function(scene, args)
        pending[scene] = args
        pump(scene)
    end
end
