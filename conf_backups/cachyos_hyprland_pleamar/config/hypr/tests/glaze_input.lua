local input
hl = { config = function(options) input = options.input end }
dofile(os.getenv("HOME") .. "/.config/hypr/input.lua")
assert(input.kb_layout == "us,ara", "keep the configured US/Arabic layout")
assert(not input.kb_options:find("alt_shift_toggle", 1, true),
    "Alt+Shift must reach window-manager bindings, not layout switching")
assert(not input.kb_options:find("caps_toggle", 1, true),
    "Caps Lock must not switch keyboard layouts")
print("PASS: Caps Lock and Alt+Shift are not layout toggles")
