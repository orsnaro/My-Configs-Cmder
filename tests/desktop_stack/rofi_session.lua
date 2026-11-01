-- Behavioral contract for the compositor module; no desktop IPC or user input.
local paths = {
    "conf_backups/cachyos_hyprland_ml4w/dotfiles/.config/hypr/rofi_session.lua",
    "conf_backups/cachyos_hyprland_pleamar/config/hypr/rofi_session.lua",
}
for _, path in ipairs(paths) do
    local bindings, events, commands = {}, {}, {}
    local layers, cursor = {}, { id = 2 }
    _G.rofi_trial_session = nil
    hl = {
        bind = function(key, callback, options)
            assert(not bindings[key], "duplicate binding")
            local binding = { callback = callback, options = options, enabled = true }
            function binding:set_enabled(enabled) self.enabled = enabled end
            bindings[key] = binding
            return binding
        end,
        on = function(name, callback)
            assert(not events[name], "duplicate subscription")
            events[name] = callback
        end,
        get_layers = function(filter)
            assert(filter.namespace == "rofi")
            return layers
        end,
        get_monitor_at_cursor = function() return cursor end,
        exec_cmd = function(command) commands[#commands+1] = command end,
    }
    local module = dofile(path)
    module.setup()
    module.setup()
    local session = assert(_G.rofi_trial_session)
    local function enabled(want)
        for _, key in ipairs({ "mouse:272", "mouse:273", "mouse:274" }) do
            local binding = assert(bindings[key])
            assert(binding.enabled == want)
            assert(not binding.options.ignore_mods and not binding.options.release)
        end
    end
    enabled(false)
    assert(not events["input.pointer.motion"] and not events["input.keyboard.key"])
    events["config.reloaded"]()
    assert(#commands == 0, "closed reload must not spawn a helper")
    assert(session.register(101))
    enabled(true)
    layers = { { namespace = "rofi", pid = 101, mapped = true, monitor = { id = 2 } } }
    for _, binding in pairs(bindings) do
        assert(binding.callback().pass_event == true, "inside clicks must pass")
    end
    assert(#commands == 0)
    cursor = { id = 3 }
    local old_open, old_execute = io.open, os.execute
    io.open = function() error("click callback performed file I/O") end
    os.execute = function() error("click callback ran synchronous shell") end
    for _, binding in pairs(bindings) do
        assert(binding.callback().pass_event == false, "outside clicks must be consumed")
        assert(commands[#commands]:match("%-%-dismiss 101$"))
    end
    io.open, os.execute = old_open, old_execute
    assert(#commands == 3)
    session.unregister(99)
    enabled(true)
    assert(session.register(202))
    layers = { { namespace = "rofi", pid = 202, mapped = true, monitor = { id = 2 } } }
    assert(type(session.adopt) == "function", "reload adoption must recheck the mapped layer at IPC delivery")
    assert(session.adopt(101) == false, "a late adoption must not replace a newer live session")
    session.unregister(101)
    events["layer.closed"]({ namespace = "rofi", pid = 101 })
    enabled(true)
    layers = {
        { namespace = "other", pid = 202, mapped = true, monitor = { id = 2 } },
        { namespace = "rofi", pid = 202, mapped = false, monitor = { id = 2 } },
        { namespace = "rofi", pid = 999, mapped = true, monitor = { id = 2 } },
    }
    local before = #commands
    assert(bindings["mouse:272"].callback().pass_event == true)
    assert(#commands == before, "foreign or unmapped layers must not cancel")
    events["layer.closed"]({ namespace = "rofi", pid = 202 })
    enabled(false)
    layers = {
        { namespace = "rofi", pid = 303, mapped = true, monitor = { id = 2 } },
        { namespace = "rofi", pid = 303, mapped = true, monitor = { id = 2 } },
        { namespace = "rofi", pid = 404, mapped = false, monitor = { id = 2 } },
    }
    events["config.reloaded"]()
    assert(#commands == before+1 and commands[#commands]:match("%-%-adopt 303$"))
    enabled(false) -- Adoption must be verified natively, not inferred from a layer.
    assert(session.register("303") == false)
    assert(session.register(1) == false)
    assert(session.register(303))
    cursor = nil
    assert(bindings["mouse:272"].callback().pass_event == true)
    session.unregister(303)
    enabled(false)
end
print("PASS: Rofi session buttons, pass-through, PID cleanup and reload adoption")
