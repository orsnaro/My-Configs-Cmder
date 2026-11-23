-- QuickShell's bars reserve their own footprint (4px on the side monitors,
-- 20px on the main bar). Vitreus regenerates vitreus_colors.lua with a 76px
-- top gap on DP-2 (16px elsewhere) for its own frame bar; that gap stacks on
-- the reserved strip and leaves a wide band of empty space above every window.
-- Loaded after vitreus_colors.lua, this zeroes the top edge and sets DP-2's
-- bottom gap to 21px so it matches the under-bar gap (20px + 1px border).
hl.config({ general = { gaps_out = { top = 0, right = 16, bottom = 16, left = 16 } } })
hl.workspace_rule({ workspace = "m[HDMI-A-2]", gaps_out = { top = 0, right = 16, bottom = 16, left = 16 } })
hl.workspace_rule({ workspace = "m[DP-2]", gaps_out = { top = 0, right = 24, bottom = 21, left = 24 } })
hl.workspace_rule({ workspace = "m[DP-1]", gaps_out = { top = 0, right = 16, bottom = 16, left = 16 } })
