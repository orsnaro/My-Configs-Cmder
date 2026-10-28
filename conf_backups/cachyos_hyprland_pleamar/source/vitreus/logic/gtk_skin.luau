-- The glass skin for GTK apps (Nautilus and every other GTK4/libadwaita app, and GTK3 ones): the shell's own palette (the wallpaper's colours, Iris) written as a user stylesheet,
-- ~/.config/gtk-4.0/gtk.css and ~/.config/gtk-3.0/gtk.css. The window, the header bar, the sidebar and the file view are translucent tints of the shell's glass, so Hyprland's blur gives
-- the glass behind them (a tint of 75 to 90 percent: Hyprland does not blur these GTK windows, so the wallpaper shows through only faintly, as tinted glass); popovers and dialogs are nearly opaque
-- so that their text stays easy to read. It is rewritten each time the palette changes (see `iris_fx.apply_palette`), and
-- apps read it when they start (an open window keeps what it had until it is reopened).
--
-- It is on by default; `pleamar --say vitreus "fact gtk_skin false"` takes it off (the files are given back as an empty comment, not deleted), `true` brings it back; the choice is kept in
-- gtk-skin.json. A gtk.css of your own is never overwritten: only a file that begins with our marker line is replaced.
return function(with_dirs)
    local cfg = { on = true }
    local ok, saved = pcall(sys.ask, "files.read", "gtk-skin.json", "json")
    if ok and type(saved) == "table" and type(saved.on) == "boolean" then cfg.on = saved.on end
    fact.gtk_skin = cfg.on

    local MARK = "/* Vitreus glass skin"
    local function rgb(h)
        h = (h or "#000000"):gsub("^#", "")
        return tonumber(h:sub(1, 2), 16) or 0, tonumber(h:sub(3, 4), 16) or 0, tonumber(h:sub(5, 6), 16) or 0
    end
    local function rgba(h, a)
        local r, g, b = rgb(h)
        return string.format("rgba(%d, %d, %d, %.2f)", r, g, b, a)
    end

    local function css4(p)
        local L = {}
        local function def(name, value) L[#L + 1] = string.format("@define-color %s %s;", name, value) end
        L[#L + 1] = MARK .. ": written by Vitreus (logic/gtk_skin.luau) from the wallpaper's colours. Turn it off with: pleamar --say vitreus \"fact gtk_skin false\" */"
        L[#L + 1] = "/* libadwaita's named colours: tints of the shell's glass, a little see-through (Hyprland does not blur these windows, so they stay fairly dense). */"
        def("accent_bg_color", p.mint); def("accent_fg_color", p.onmint); def("accent_color", p.minthi)
        def("destructive_bg_color", p.alert); def("destructive_fg_color", "#ffffff"); def("destructive_color", p.alert)
        def("error_bg_color", p.alert); def("error_fg_color", "#ffffff"); def("error_color", p.alert)
        def("warning_bg_color", p.mintlo); def("warning_fg_color", p.onmint); def("warning_color", p.minthi)
        def("success_bg_color", p.mintlo); def("success_fg_color", p.onmint); def("success_color", p.minthi)
        def("window_bg_color", rgba(p.tint, 0.86)); def("window_fg_color", p.ink)
        def("view_bg_color", rgba(p.tint, 0.4)); def("view_fg_color", p.ink)
        def("headerbar_bg_color", rgba(p.panel, 0.88)); def("headerbar_fg_color", p.ink)
        def("headerbar_border_color", rgba(p.ink, 0.10)); def("headerbar_backdrop_color", rgba(p.panel, 0.82))
        def("headerbar_shade_color", rgba(p.deep, 0.30)); def("headerbar_darker_shade_color", rgba(p.deep, 0.40))
        def("sidebar_bg_color", rgba(p.panel, 0.84)); def("sidebar_fg_color", p.ink)
        def("sidebar_backdrop_color", rgba(p.panel, 0.78)); def("sidebar_shade_color", rgba(p.deep, 0.30))
        def("secondary_sidebar_bg_color", rgba(p.panel, 0.8)); def("secondary_sidebar_fg_color", p.ink)
        def("secondary_sidebar_backdrop_color", rgba(p.panel, 0.74)); def("secondary_sidebar_shade_color", rgba(p.deep, 0.30))
        def("card_bg_color", rgba(p.ink, 0.07)); def("card_fg_color", p.ink); def("card_shade_color", rgba(p.deep, 0.25))
        def("dialog_bg_color", rgba(p.tint, 0.98)); def("dialog_fg_color", p.ink)
        def("popover_bg_color", rgba(p.tint, 0.98)); def("popover_fg_color", p.ink); def("popover_shade_color", rgba(p.deep, 0.30))
        def("thumbnail_bg_color", rgba(p.panel, 0.78)); def("thumbnail_fg_color", p.ink)
        def("shade_color", rgba(p.deep, 0.30)); def("scrollbar_outline_color", rgba(p.deep, 0.60))
        L[#L + 1] = ""
        L[#L + 1] = "/* A rim of light round the window, like the shell's glass, and the soft shadow under it. */"
        L[#L + 1] = string.format("window.csd, window.solid-csd { box-shadow: 0 0 0 1px %s, 0 8px 24px %s; }", rgba(p.ink, 0.16), rgba("#000000", 0.35))
        L[#L + 1] = string.format("headerbar { box-shadow: inset 0 -1px %s; }", rgba(p.ink, 0.08))
        L[#L + 1] = "/* The window's own tint (libadwaita leaves it unpainted under a translucent colour, so the file area would show the wallpaper bare). */"
        L[#L + 1] = "window.background { background-color: @window_bg_color; }"
        L[#L + 1] = ""
        return table.concat(L, "\n")
    end

    local function css3(p)
        local L = {}
        local function def(name, value) L[#L + 1] = string.format("@define-color %s %s;", name, value) end
        L[#L + 1] = MARK .. ": written by Vitreus (logic/gtk_skin.luau) from the wallpaper's colours. Turn it off with: pleamar --say vitreus \"fact gtk_skin false\" */"
        def("theme_bg_color", rgba(p.tint, 0.86)); def("theme_fg_color", p.ink)
        def("theme_base_color", rgba(p.tint, 0.45)); def("theme_text_color", p.ink)
        def("theme_selected_bg_color", p.mint); def("theme_selected_fg_color", p.onmint)
        def("theme_unfocused_bg_color", rgba(p.tint, 0.86)); def("theme_unfocused_fg_color", p.faint)
        def("theme_unfocused_base_color", rgba(p.tint, 0.74)); def("theme_unfocused_text_color", p.faint)
        def("theme_unfocused_selected_bg_color", p.mintlo); def("theme_unfocused_selected_fg_color", p.onmint)
        def("insensitive_bg_color", rgba(p.panel, 0.78)); def("insensitive_fg_color", p.faint)
        def("borders", rgba(p.ink, 0.14)); def("unfocused_borders", rgba(p.ink, 0.08))
        def("warning_color", p.minthi); def("error_color", p.alert); def("success_color", p.mintlo)
        def("content_view_bg", rgba(p.tint, 0.78))
        L[#L + 1] = ""
        return table.concat(L, "\n")
    end

    -- A file of ours is replaced; a file that is somebody's own is left alone (grep says 0 for ours, 1 for another's, 2 when there is none).
    local function put(src, target)
        run("grep", { "-qs", MARK, target }, function(_, code)
            if code == 0 or code == 2 then run("cp", { "-f", src, target }, function() end) end
        end)
    end

    local function apply()
        with_dirs(function(d)
            local base = d.conf:gsub("/pleamar/shells/vitreus$", "")
            local p = iris_fx and (iris_fx.last_pal or iris_fx.saved)
            local c4, c3
            if cfg.on and p then
                c4, c3 = css4(p), css3(p)
            elseif not cfg.on then
                c4 = MARK .. ": off (fact gtk_skin false) */\n"; c3 = c4
            else
                return        -- on, but no palette yet: it is written when the first one arrives
            end
            pcall(sys.call, "files.write", "gtk4.css", c4)
            pcall(sys.call, "files.write", "gtk3.css", c3)
            run("mkdir", { "-p", base .. "/gtk-4.0", base .. "/gtk-3.0" }, function()
                put(d.data .. "/gtk4.css", base .. "/gtk-4.0/gtk.css")
                put(d.data .. "/gtk3.css", base .. "/gtk-3.0/gtk.css")
            end)
        end)
    end

    iris_fx.apply_gtk = apply
    local function set(on)
        cfg.on = on
        pcall(sys.call, "files.write", "gtk-skin.json", cfg)
        apply()
    end
    on("fact:gtk_skin", function(v) set(v == true or v == 1) end)
    after(3000, apply)       -- the palette may already be there
end
