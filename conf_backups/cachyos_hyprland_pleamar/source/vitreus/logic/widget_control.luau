-- One widget's acknowledged settings, serialized across a bounded cold start.
return function(opts)
    local W = {}
    local pending, order = {}, {}
    local sending, starting, revision, startup = false, false, 0, 0
    local pump
    local function status(message) opts.status(message) end
    local function request(commands, done)
        local args = { "--say", opts.scene }
        if type(commands) == "string" then commands = { commands } end
        for _, command in ipairs(commands) do args[#args + 1] = command end
        local finished = false
        local function finish(ok)
            if finished then return end
            finished = true
            done(ok)
        end
        run("pleamar", args, function(out, code)
            finish(code == 0 and not (out or ""):match("^%s*%?") and not (out or ""):match("\n%s*%?"))
        end)
        after(2500, function() finish(false) end)
    end
    local function start()
        starting = true
        startup = startup + 1
        local mine = startup
        status("Starting " .. opts.label .. "…")
        exec_on_desktop('vitreus-keep "$HOME/.config/pleamar/shells/vitreus/' .. opts.scene .. '/' .. opts.scene .. '.plm"')
        local function poll()
            if not starting or startup ~= mine then return end
            request("get shown", function(ok)
                if not starting or startup ~= mine then return end
                if ok then starting = false; pump() else after(200, poll) end
            end)
        end
        after(10000, function()
            if not starting or startup ~= mine then return end
            starting = false
            startup = startup + 1
            pending, order = {}, {}
            status("Couldn't start " .. opts.label .. "; see " .. opts.scene .. ".log")
        end)
        poll()
    end
    pump = function()
        if sending or starting then return end
        local item
        while #order > 0 do
            local next_item = table.remove(order, 1)
            if pending[next_item.key] == next_item then item = next_item; break end
        end
        if not item then opts.refresh(); return end
        sending = true
        request(item.command, function(ok)
            sending = false
            if pending[item.key] ~= item then pump(); return end
            if ok then
                pending[item.key] = nil
                if item.confirm then item.confirm() end
                status("")
            elseif item.visible == true and not item.retried then
                item.retried = true
                table.insert(order, 1, item)
                start()
                return
            else
                pending[item.key] = nil
                status("Couldn't update " .. opts.label .. "; start it and try again")
            end
            pump()
        end)
    end
    local function enqueue(key, command, confirm, visible)
        revision = revision + 1
        local item = { key = key, command = command, confirm = confirm, visible = visible }
        pending[key] = item
        -- A replacement goes to the end: reset followed by a newer slider change keeps that order.
        order[#order + 1] = item
        pump()
    end
    function W.set_visible(value)
        enqueue("shown", "fact shown " .. tostring(value), function() opts.confirm_visible(value) end, value)
    end
    function W.change(key, command, on_confirmed) enqueue(key, command, on_confirmed) end
    function W.target()
        if pending.shown then return pending.shown.visible end
        return opts.get_visible()
    end
    function W.version() return revision end
    function W.busy() return sending or starting or next(pending) ~= nil end
    return W
end
