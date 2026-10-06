-- -----------------------------------------------------
-- Input
-- -----------------------------------------------------

hl.config({
    input = {
        kb_layout    = "us,ara",
        kb_variant   = "",
        kb_model     = "",
        kb_options   = "", -- Keep Caps Lock normal; SUPER+Return switches layouts in custom.lua.
        kb_rules     = "",
        -- Layout-independent binds: resolve by keycode (physical position),
        -- not by symbol, so SUPER+Q etc. work identically in us and ara.
        -- First layout (us) defines the bind symbols; ara only changes typed text.
        resolve_binds_by_sym = false,

        follow_mouse = 1,

        sensitivity  = 0, -- -1.0 - 1.0, 0 means no modification.

        touchpad     = {
            natural_scroll = true,
        },
    },
})
