-- Unmodified outside-monitor clicks only; identity and signals stay native.
local M = {}

function M.setup()
    if M.session then return M.session end
    local active, buttons = nil, {}
    local helper = os.getenv("HOME") .. "/.local/lib/rofi-trial/dismiss-guard"
    local quoted_helper = "'" .. helper:gsub("'", "'\\''") .. "'"

    local function valid_pid(pid)
        return type(pid) == "number" and pid > 1 and pid <= 2147483647 and pid % 1 == 0
    end
    local function enable(value)
        for _, button in ipairs(buttons) do button:set_enabled(value) end
    end
    local function mapped(pid)
        for _, layer in ipairs(hl.get_layers({ namespace = "rofi" })) do
            if layer.namespace == "rofi" and layer.mapped and layer.pid == pid then return layer end
        end
    end
    local session = {}
    function session.register(pid)
        if not valid_pid(pid) then return false end
        active = pid
        enable(true)
        return true
    end
    function session.unregister(pid)
        if active == pid then active = nil; enable(false) end
        return true
    end
    local function click()
        local layer = active and mapped(active)
        local cursor = layer and hl.get_monitor_at_cursor()
        if not layer or not layer.monitor or not cursor or layer.monitor.id == cursor.id then
            return { pass_event = true }
        end
        hl.exec_cmd(quoted_helper .. " --dismiss " .. string.format("%d", active))
        return { pass_event = false }
    end
    for _, key in ipairs({ "mouse:272", "mouse:273", "mouse:274" }) do
        local button = hl.bind(key, click, { description = "Dismiss this Rofi session on another monitor" })
        button:set_enabled(false)
        buttons[#buttons+1] = button
    end
    hl.on("layer.closed", function(layer)
        if layer.namespace == "rofi" then session.unregister(layer.pid) end
    end)
    hl.on("config.reloaded", function()
        local seen = {}
        for _, layer in ipairs(hl.get_layers({ namespace = "rofi" })) do
            local pid = layer.pid
            if layer.namespace == "rofi" and layer.mapped and valid_pid(pid) and not seen[pid] then
                seen[pid] = true
                hl.exec_cmd(quoted_helper .. " --adopt " .. string.format("%d", pid))
            end
        end
    end)
    M.session = session
    _G.rofi_trial_session = session
    return session
end

return M
