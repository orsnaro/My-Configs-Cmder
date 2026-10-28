-- desktop-stack managed
hl.on("hyprland.start", function ()
    local HOME = os.getenv("HOME")

    -- Read wallpaper app setting
    local wallpaper_app = "quickshell"
    local f = io.open(HOME .. "/.config/ml4w/settings/wallpaper-app", "r")
    if f then
        wallpaper_app = f:read("*l"):match("^%s*(.-)%s*$")
        f:close()
    end

    -- Export variables to systemd
    hl.exec_cmd("dbus-update-activation-environment --systemd WAYLAND_DISPLAY XDG_CURRENT_DESKTOP")
    -- The permanent shell is managed by systemd, not by a trial watcher.
    hl.exec_cmd('"' .. HOME .. '/.local/bin/desktop-stack" resume')

    -- Vitreus's own lock screen: a separate scene so that restarting the shell cannot unlock the session.
    -- PLEAMAR_SWAPCHAIN=1 is required on pleamar 0.4 or Hyprland kills the lock surface on the first lock.
    -- DRI_PRIME/VK_DRIVER_FILES keep it on the same AMD GPU as the main scene instead of the Intel iGPU.
    -- Native lock startup is owned by desktop-stack.

    -- Restart portals so they catch the environment
    hl.exec_cmd("systemctl --user stop xdg-desktop-portal xdg-desktop-portal-hyprland")
    hl.exec_cmd("systemctl --user start xdg-desktop-portal-hyprland xdg-desktop-portal")

    -- awww daemon
    hl.exec_cmd("awww-daemon")

    -- Load cursor
    hl.exec_cmd("hyprctl setcursor Bibata-Modern-Ice 24")

    -- Start listeners
    hl.exec_cmd("~/.config/ml4w/listeners.sh --startall")

    -- Start waybar
    -- permanent Pleamar: waybar is closed, not uninstalled
    -- hl.exec_cmd(HOME .. "/.config/waybar/launch.sh")

    -- Start polkit daemon
    -- permanent Pleamar: Vitreus's own polkit agent owns authentication
    -- hl.exec_cmd("/usr/lib/polkit-gnome/polkit-gnome-authentication-agent-1")

    -- Restore wallpaper (skip for quickshell — handled inside ml4w-autostart)
    if wallpaper_app ~= "quickshell" then
        hl.exec_cmd("~/.config/ml4w/scripts/ml4w-wallpaper-app --restore")
    end

    -- Autostart scripts
    -- permanent Pleamar: ML4W/Quickshell/dock startup is retired
    -- hl.exec_cmd("~/.config/ml4w/scripts/ml4w-autostart > ~/.mydotfiles/ml4w-autostart.log 2>&1")

    -- Load GTK settings
    hl.exec_cmd("~/.config/hypr/scripts/gtk.sh")

    -- Start swaync
    -- permanent Pleamar owns notifications
    -- hl.exec_cmd("swaync")

    -- Walker launcher backend + UI service (needs elephant for providers)
    -- permanent Pleamar: Walker backend is not started
    -- hl.exec_cmd("elephant")
    -- permanent Pleamar: Walker UI is not started
    -- hl.exec_cmd("walker --gapplication-service")

    -- Start hypridle
    hl.exec_cmd("hypridle")

    -- Vitreus starts and controls hyprsunset from its shared saved night-mode settings.
    -- Do not start a competing daemon/schedule here.

    -- Load cliphist history
    hl.exec_cmd("wl-paste --watch cliphist store")

    -- Start autostart cleanup
    hl.exec_cmd("~/.config/hypr/scripts/cleanup.sh")
end)
