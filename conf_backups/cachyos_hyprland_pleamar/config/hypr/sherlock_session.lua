-- Event-driven dismissal; the resident launcher and its result models stay intact.
local M = {}

function M.setup()
    if M.session then return M.session end
    local buttons, session = {}, {}
    local home = os.getenv("HOME")
    local function quote(value) return "'" .. value:gsub("'", "'\\''") .. "'" end
    local close_command = "/usr/bin/python " .. quote(home .. "/.local/share/sherlock-integration/sherlock_ipc.py") .. " close "

    local function mapped()
        for _, layer in ipairs(hl.get_layers({ namespace = "sherlock" })) do
            local pid = layer.pid
            if layer.namespace == "sherlock" and layer.mapped
                and type(pid) == "number" and pid > 1 and pid <= 2147483647 and pid % 1 == 0 then
                return layer
            end
        end
    end
    local function close(layer)
        hl.exec_cmd(close_command .. string.format("%d", layer.pid))
    end
    local function enable(value)
        for _, button in ipairs(buttons) do button:set_enabled(value) end
    end
    local function refresh() enable(mapped() ~= nil) end

    function session.toggle()
        local layer = mapped()
        if layer then close(layer)
        else hl.exec_cmd(quote(home .. "/.config/hypr/scripts/launcher.sh")) end
    end
    function session.dismiss_outside()
        local layer, cursor = mapped(), hl.get_cursor_pos()
        if not layer or not cursor then return { pass_event = true } end
        for _, key in ipairs({ "x", "y", "w", "h" }) do
            if type(layer[key]) ~= "number" then return { pass_event = true } end
        end
        if type(cursor.x) ~= "number" or type(cursor.y) ~= "number" or layer.w <= 0 or layer.h <= 0 then
            return { pass_event = true }
        end
        if cursor.x >= layer.x and cursor.x < layer.x + layer.w
            and cursor.y >= layer.y and cursor.y < layer.y + layer.h then
            return { pass_event = true }
        end
        close(layer)
        return { pass_event = false }
    end

    for _, key in ipairs({ "mouse:272", "mouse:273", "mouse:274" }) do
        buttons[#buttons + 1] = hl.bind(key, session.dismiss_outside,
            { description = "Dismiss Sherlock on outside click" })
    end
    hl.on("layer.opened", function(layer)
        if layer.namespace == "sherlock" then enable(true) end
    end)
    hl.on("layer.closed", function(layer)
        if layer.namespace == "sherlock" then enable(false) end
    end)
    hl.on("config.reloaded", refresh)
    refresh()
    M.session = session
    return session
end

return M
