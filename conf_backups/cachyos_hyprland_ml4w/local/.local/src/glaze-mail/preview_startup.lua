-- Runtime-only rules: select the split before mapping, never move a mapped preview.
return function(spec)
    assert(hl.get_config("general.layout") == "dwindle", "Preview needs Dwindle")
    assert(hl.get_config("dwindle.use_active_for_splits"), "Preview needs active-window splits")
    assert(not hl.get_config("dwindle.permanent_direction_override"), "Preview needs one-shot preselection")
    local function get_mail()
        local mail = hl.get_window("address:" .. spec.mail_address)
        if mail and mail.class == "aerc-mail" and mail.workspace and
                mail.workspace.id == spec.workspace and not mail.floating then
            return mail
        end
    end
    assert(get_mail(), "Mail window is unavailable")

    local old = _G.glaze_mail_preview_startup
    if old then old.stop() end
    local state = {}
    _G.glaze_mail_preview_startup = state
    local function is_preview(window)
        if not window or type(window.class) ~= "string" then return false end
        local id, page = window.class:match("^brave%-.*_glaze%-mail%-preview_" .. spec.invocation ..
                                          "_([0-9a-f]+)_([a-z]+)%.html%-")
        return id and #id == 32 and (page == "blocked" or page == "images")
    end
    state.rule = hl.window_rule({
        name = "glaze-mail-preview-startup",
        match = { class = "^brave-.*_glaze-mail-preview_" .. spec.invocation ..
                          "_[0-9a-f]{32}_(blocked|images)\\.html-.*$" },
        workspace = tostring(spec.workspace), float = false,
    })
    state.early = hl.on("window.open_early", function(window)
        if not is_preview(window) then return end
        local mail = get_mail()
        if not mail then return end
        hl.dispatch(hl.dsp.focus({ window = mail }))
        hl.dispatch(hl.dsp.layout("preselect r"))
        state.armed = window.address
    end)
    state.opened = hl.on("window.open", function(window)
        if window.address ~= state.armed then return end
        hl.dispatch(hl.dsp.layout("preselect none"))
        state.armed = nil
    end)
    function state.stop()
        state.early:remove()
        state.opened:remove()
        state.rule:set_enabled(false)
        if state.timer then state.timer:set_enabled(false) end
        if state.armed then hl.dispatch(hl.dsp.layout("preselect none")) end
        if _G.glaze_mail_preview_startup == state then _G.glaze_mail_preview_startup = nil end
    end
    state.timer = hl.timer(state.stop, { timeout = 10000, type = "oneshot" })
end
