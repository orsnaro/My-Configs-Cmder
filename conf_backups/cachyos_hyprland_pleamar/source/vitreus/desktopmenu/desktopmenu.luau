-- Hyprland only: a right press on the wallpaper opens the desktop editor (desktopedit/), started if it is not running.
on("edit_req", function()
    local mon = math.floor((tonumber(fact.mmon) or 0) + 0.5)
    run("pleamar", { "--say", "desktopedit", "fact emon " .. mon, "fact open true" }, function(_, code)
        if code ~= 0 then
            run("sh", { "-c", 'PATH="$HOME/.local/bin:$PATH" vitreus-keep "$HOME/.config/pleamar/shells/vitreus/desktopedit/desktopedit.plm" >/dev/null 2>&1 &' }, function() end)
            after(3000, function() run("pleamar", { "--say", "desktopedit", "fact emon " .. mon, "fact open true" }, function() end) end)
        end
    end)
end)
