#!/bin/sh
# Vitreus: install it, keep it up to date, take it away. One script for all.
#
#   curl -fsSL https://raw.githubusercontent.com/natepayn3/Vitreus/main/install.sh | sh
#   ./install.sh                   install (or, if it is there, update)
#   ./install.sh --yes             don't ask anything: answer yes to everything
#   ./install.sh --dry-run         say what it would do, and do nothing
#   ./install.sh --no-deps         only the shell itself: no packages, no font, no pleamar
#   ./install.sh --no-autostart    don't touch ~/.config/pleamar/autostart
#   ./install.sh --no-binds        don't touch ~/.config/hypr (the key binds, and what Settings saves there)
#   ./install.sh --no-wm           don't set up pleamar-wm (its login-screen entry, keys, window scene and autostart lines)
#   ./install.sh --refresh         what Settings > About runs after it has pulled: no questions, no sudo, nothing downloaded; it
#                                  links the new helpers, adds the new autostart lines and binds, and lists the packages that are missing
#   ./install.sh --force           install even when another Quickshell desktop shell is in use
#   ./install.sh --test            try it next to another shell (Quickshell): no autostart, key binds or pleamar-wm; stops that
#                                  shell and starts Vitreus now
#   ./install.sh --stop            end a --test: stop Vitreus and start the other shell again
#   ./install.sh --uninstall       take the shell away (your data in ~/.local/share stays)
#
# What it does, in order:
#   1. the packages Vitreus uses      (Arch and its relatives: pacman, and yay/paru for the AUR;
#                                      on any other distribution it lists what to install by hand).
#                                      hyprsunset is required on Hyprland (Night mode): without it, this stops
#   2. pleamar, the runtime           (its own installer, into your home; a few minutes to build)
#   3. the fonts                      (Space Grotesk, and the three the Retro, UwU and Cyber themes are drawn in: Audiowide, Mochiy Pop One and Orbitron;
#                                      into ~/.local/share/fonts, no sudo)
#   4. the shell                      (into ~/.config/pleamar/shells/vitreus: cloned, or updated)
#   5. your palette, autostart entry  (made once and never written over)
#   5b. the helpers                  (bin/vitreus-clipimg, vitreus-polkit-agent, vitreus-sysmon, vitreus-term, vitreus-files and vitreus-report, linked into ~/.local/bin)
#   6. its Hyprland key binds         (hypr_vitreus.lua linked into ~/.config/hypr, and loaded from hyprland.lua)
#   6b. the daemons                   (awww, hypridle and the clipboard history: lines in ~/.config/pleamar/autostart, run on any compositor)
#   7. pleamar-wm, as a session       (pleamar-wm/: its keys, window scene, hyprctl shim, and, with sudo,
#                                      its entry in the login screen; only if pleamar-wm is installed)
#
# It never installs a compositor: Vitreus is developed on Hyprland, and needs one that has layer-shell.
set -eu

repo="${VITREUS_REPO:-https://github.com/natepayn3/Vitreus.git}"
pleamar_installer="${PLEAMAR_INSTALLER:-https://raw.githubusercontent.com/k4ditano/pleamar/main/install.sh}"
font_url="https://github.com/google/fonts/raw/main/ofl/spacegrotesk/SpaceGrotesk%5Bwght%5D.ttf"
# The Retro theme's typeface, Audiowide (a rounded sci-fi face), and the UwU theme's (both Google Fonts, OFL).
# Both are optional: without one, that theme keeps Space Grotesk.
dot_url="https://github.com/google/fonts/raw/main/ofl/audiowide/Audiowide-Regular.ttf"
dot_licence_url="https://github.com/google/fonts/raw/main/ofl/audiowide/OFL.txt"
mochiy_url="https://github.com/google/fonts/raw/main/ofl/mochiypopone/MochiyPopOne-Regular.ttf"
# The Cyber theme's typeface, Orbitron (a squared techno face; Google Fonts, OFL).
orbitron_url="https://github.com/google/fonts/raw/main/ofl/orbitron/Orbitron%5Bwght%5D.ttf"
orbitron_licence_url="https://github.com/google/fonts/raw/main/ofl/orbitron/OFL.txt"

conf="${XDG_CONFIG_HOME:-$HOME/.config}"
data="${XDG_DATA_HOME:-$HOME/.local/share}"
dest="$conf/pleamar/shells/vitreus"
autostart="$conf/pleamar/autostart"
fonts="$data/fonts/SpaceGrotesk"
fonts_dot="$data/fonts/Audiowide"
fonts_mochiy="$data/fonts/MochiyPopOne"
fonts_orbitron="$data/fonts/Orbitron"

# Official-repo packages, then AUR ones: what each is for is in the README.
pacman_pkgs="git curl jq python fontconfig socat imagemagick cava playerctl networkmanager bluez bluez-utils brightnessctl hypridle hyprsunset libnotify xdg-user-dirs xdg-utils wl-clipboard cliphist awww ffmpeg grim slurp wf-recorder power-profiles-daemon polkit python-gobject python-pyte ttf-space-mono-nerd pipewire-audio sound-theme-freedesktop tesseract tesseract-data-eng"
aur_pkgs="iris-colors mpvpaper"

assume_yes=false
dry=false
deps=true
do_autostart=true
do_binds=true
do_wm=true
force=false
refresh=false
trial=false
action=install
for a in "$@"; do
    case "$a" in
        --yes|-y) assume_yes=true ;;
        --dry-run) dry=true ;;
        --no-deps) deps=false ;;
        --no-autostart) do_autostart=false ;;
        --no-binds) do_binds=false ;;
        --no-wm) do_wm=false ;;
        --refresh) refresh=true ;;
        --force) force=true ;;
        --test) trial=true; force=true; do_autostart=false; do_binds=false; do_wm=false ;;
        --stop) action=stop ;;
        --uninstall) action=uninstall ;;
        --help|-h) sed -n '2,29p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) printf 'vitreus · I do not know "%s" (try --help)\n' "$a" >&2; exit 1 ;;
    esac
done

# What this run said and what failed, kept short in ~/.local/state/vitreus/install.log: `vitreus-report` reads it, so a person whose
# install stopped half way can send it without knowing what to look for. (Nothing is written with --dry-run.)
installlog="${XDG_STATE_HOME:-$HOME/.local/state}/vitreus/install.log"
log() { $dry || printf '%s\n' "$*" >> "$installlog" 2> /dev/null || true; }
if ! $dry; then
    {
        mkdir -p "$(dirname "$installlog")"
        if [ -f "$installlog" ]; then tail -n 300 "$installlog" > "$installlog.tmp" && mv "$installlog.tmp" "$installlog"; fi
        printf '\n=== %s · install.sh %s ===\n' "$(date)" "$*" >> "$installlog"
    } 2> /dev/null || true
fi
trap 'rc=$?; [ "$rc" -eq 0 ] || log "stopped with status $rc"' EXIT

say()  { log "$*"; printf '\033[1;36mvitreus ·\033[0m %s\n' "$*"; }
warn() { log "warning: $*"; printf '\033[1;33mvitreus ·\033[0m %s\n' "$*" >&2; }
fail() { log "FAILED: $*"; printf '\033[1;31mvitreus ·\033[0m %s\n' "$*" >&2; exit 1; }
have() { command -v "$1" > /dev/null 2>&1; }

# Do a command, or, with --dry-run, only say it.
run() {
    if $dry; then printf '    would run: %s\n' "$*"; else
        if "$@"; then :; else rc=$?; log "command failed ($rc): $*"; return "$rc"; fi
    fi
}

# ask "question": yes/no, default yes. Reads the keyboard even when the script itself was piped in.
# ask_no "question": the same, default no, for what cannot be undone; with no keyboard (and no --yes) it is a no.
tty_ok() { [ -r /dev/tty ] && ( exec < /dev/tty ) 2> /dev/null; }
ask() {
    $refresh && return 1
    $assume_yes && return 0
    if tty_ok; then
        printf '\033[1;36mvitreus ·\033[0m %s [Y/n] ' "$1" > /dev/tty
        read -r answer < /dev/tty || answer=y
        case "$answer" in n|N|no|No) return 1 ;; *) return 0 ;; esac
    fi
    warn "no keyboard to ask on: $1 (answering yes; use --yes to skip questions)"
    return 0
}
ask_no() {
    $refresh && return 1
    $assume_yes && return 0
    if tty_ok; then
        printf '\033[1;36mvitreus ·\033[0m %s [y/N] ' "$1" > /dev/tty
        read -r answer < /dev/tty || answer=n
        case "$answer" in y|Y|yes|Yes) return 0 ;; *) return 1 ;; esac
    fi
    warn "no keyboard to ask on: $1 (answering no; --yes says yes)"
    return 1
}

[ "$(id -u)" -ne 0 ] || fail "run this as yourself, not as root: it installs into your home (and asks for sudo only for packages)"
[ "$(uname -s)" = Linux ] || fail "Vitreus is a Linux (Wayland) shell"

# ── uninstall ──────────────────────────────────────────────────────────────
if [ "$action" = uninstall ]; then
    say "taking Vitreus away"
    if [ -f "$autostart" ] && grep -q 'vitreus.plm' "$autostart"; then
        run sed -i '/vitreus\.plm/d' "$autostart"
        say "removed its line from $autostart"
    fi
    # The lock screen, the wallpaper transition and the desktop clock are scenes of their own, each with its line.
    if [ -f "$autostart" ] && grep -q 'vitreus/lockscreen/lockscreen.plm' "$autostart"; then
        run sed -i '/vitreus\/lockscreen\/lockscreen\.plm/d' "$autostart"
        say "removed the lock screen's line from $autostart (hypridle and any key binding that lock with it are yours to change)"
    fi
    if [ -f "$autostart" ] && grep -q 'vitreus/wptrans/wptrans.plm' "$autostart"; then
        run sed -i '/vitreus\/wptrans\/wptrans\.plm/d' "$autostart"
        say "removed the wallpaper transition's line from $autostart"
    fi
    if [ -f "$autostart" ] && grep -q 'vitreus/desktopclock/desktopclock.plm' "$autostart"; then
        run sed -i '/vitreus\/desktopclock\/desktopclock\.plm/d' "$autostart"
        say "removed the desktop clock's line from $autostart"
    fi
    if [ -f "$autostart" ] && grep -q 'vitreus/desktopsysmon/desktopsysmon.plm' "$autostart"; then
        run sed -i '/vitreus\/desktopsysmon\/desktopsysmon\.plm/d' "$autostart"
        say "removed the desktop system monitor's line from $autostart"
    fi
    if [ -f "$autostart" ] && grep -q 'vitreus/desktopcava/desktopcava.plm' "$autostart"; then
        run sed -i '/vitreus\/desktopcava\/desktopcava\.plm/d' "$autostart"
        say "removed the desktop audio visualiser's line from $autostart"
    fi
    if [ -f "$autostart" ] && grep -q 'vitreus/desktopnotes/desktopnotes.plm' "$autostart"; then
        run sed -i '/vitreus\/desktopnotes\/desktopnotes\.plm/d' "$autostart"
        say "removed the desktop notes' line from $autostart"
    fi
    if [ -f "$autostart" ] && grep -q 'vitreus/desktopmenu/desktopmenu.plm' "$autostart"; then
        run sed -i '/vitreus\/desktopmenu\/desktopmenu\.plm/d' "$autostart"
        say "removed the desktop menu's line from $autostart"
    fi
    hyprlua="$conf/hypr/hyprland.lua"
    if [ -f "$hyprlua" ] && grep -q '^-- >>> vitreus' "$hyprlua"; then
        run sed -i '/^-- >>> vitreus/,/^-- <<< vitreus/d' "$hyprlua"
        say "removed Vitreus's lines from $hyprlua (SUPER + L and SUPER + Space go back to what hypr_style.lua binds)"
    fi
    if [ -f "$autostart" ] && grep -q -E '^# >>> vitreus \((pleamar-wm|session)\)' "$autostart"; then
        run sed -i -E '/^# >>> vitreus \((pleamar-wm|session)\)/,/^# <<< vitreus/d' "$autostart"
        say "removed its daemon lines from $autostart"
    fi
    # Marea and swaybg, which the pleamar-wm step turned off, are turned back on.
    if [ -f "$autostart" ] && grep -q '  (turned off by Vitreus: it is the bar now)$' "$autostart"; then
        run sed -i 's/^# \(.*\)  (turned off by Vitreus: it is the bar now)$/\1/' "$autostart"
        say "turned Marea (and swaybg) back on in $autostart"
    fi
    if [ -f "$autostart" ] && grep -q '^# wm: swaybg' "$autostart"; then
        say "an older install commented out «wm: swaybg» in $autostart without a mark: uncomment it if you want it back"
    fi
    for l in "$conf/pleamar/keys.conf" "$conf/pleamar/wm" "$HOME/.local/bin/hyprctl"; do
        case "$(readlink -f "$l" 2> /dev/null)" in "$(readlink -f "$dest")"/*) run rm -f "$l"; say "removed the link $l" ;; esac
    done
    if [ -f /usr/share/wayland-sessions/pleamar-wm.desktop ]; then
        say "pleamar-wm's login-screen entry is left in place; to take it away: sudo sh $dest/pleamar-wm/install-session.sh --remove"
    fi
    if [ -L "$HOME/.local/bin/vitreus-clipimg" ]; then run rm -f "$HOME/.local/bin/vitreus-clipimg"; fi
    if [ -L "$HOME/.local/bin/vitreus-polkit-agent" ]; then run rm -f "$HOME/.local/bin/vitreus-polkit-agent"; fi
    if [ -L "$HOME/.local/bin/vitreus-sysmon" ]; then run rm -f "$HOME/.local/bin/vitreus-sysmon"; fi
    if [ -L "$HOME/.local/bin/vitreus-term" ]; then run rm -f "$HOME/.local/bin/vitreus-term"; fi
    if [ -L "$HOME/.local/bin/vitreus-keep" ]; then run rm -f "$HOME/.local/bin/vitreus-keep"; fi
    if [ -L "$HOME/.local/bin/vitreus-report" ]; then run rm -f "$HOME/.local/bin/vitreus-report"; fi
    if [ -L "$conf/hypr/hypr_vitreus.lua" ]; then run rm -f "$conf/hypr/hypr_vitreus.lua"; fi
    run rm -f "$conf/hypr/vitreus_monitors.lua" "$conf/hypr/vitreus_hypr.lua" "$conf/hypr/vitreus_colors.lua"
    if [ -d "$dest" ] && ask_no "delete $dest?"; then run rm -rf "$dest"; fi
    say "left as they were: your data in $data/pleamar/vitreus, the caches in ${XDG_CACHE_HOME:-$HOME/.cache}/pleamar/vitreus"
    say "and .../pleamar/lockscreen, and pleamar and the packages. To remove the data too: rm -rf $data/pleamar/vitreus"
    exit 0
fi

# ── --stop: end a --test and bring the other shell back ───────────────────
trial_file="$data/pleamar/vitreus/test-restore"
if [ "$action" = stop ]; then
    say "stopping Vitreus"
    run pkill -f "vitreus-keep $dest/"
    run pkill -f "pleamar --scene $dest/"
    if [ -f "$trial_file" ] && ! $dry; then
        sleep 1
        while IFS= read -r cmd; do
            [ -n "$cmd" ] || continue
            say "starting your other shell again: $cmd"
            setsid sh -c "$cmd" > /dev/null 2>&1 < /dev/null &
        done < "$trial_file"
        rm -f "$trial_file"
    else
        say "(no other shell was stopped by --test, so none is started again)"
    fi
    exit 0
fi

# ── another desktop shell ──────────────────────────────────────────────────
# Vitreus is a whole desktop shell, not an add-on: it starts its own bar, notifications, launcher, lock screen and wallpaper, takes SUPER + Space,
# L, B, D and TAB, and sets Hyprland's gaps, borders, layout and monitors. Next to another shell the two fight over the same jobs (only one can
# own the notifications, the wallpaper or the polkit agent), so this stops before touching anything. Which shell does not matter: Quickshell is
# running (qs or quickshell) and it has a configuration of any kind in ~/.config/quickshell or the system's XDG_CONFIG_DIRS (/etc/xdg).
# --yes does not skip it, since it is not a question of packages: only --force does. An update of Vitreus itself is not stopped.
if [ "$action" = install ] && ! $force && ! $refresh && ! { [ -f "$autostart" ] && grep -q 'vitreus.plm' "$autostart"; }; then
    if pgrep -x qs > /dev/null 2>&1 || pgrep -x quickshell > /dev/null 2>&1; then
        # Any configuration at all (a folder, or a shell.qml directly in it), where Quickshell looks: the user's, then the system's (XDG_CONFIG_DIRS).
        qsdir=""
        for d in "$conf" $(printf '%s' "${XDG_CONFIG_DIRS:-/etc/xdg}" | tr ':' ' '); do
            if [ -n "$(find "$d/quickshell" -mindepth 1 -maxdepth 1 2> /dev/null | head -n 1)" ]; then qsdir="$d/quickshell"; break; fi
        done
        if [ -n "$qsdir" ]; then
            warn "Quickshell is running, and $qsdir has a configuration: another desktop shell is in use"
            warn "Vitreus is a whole shell, not an add-on. Installed next to it, both start at login and fight over the notifications, the wallpaper,"
            warn "the lock screen and the polkit agent; it also takes SUPER + Space, L, B, D and TAB from you and sets Hyprland's gaps, borders,"
            warn "layout and monitors. To switch to Vitreus: take the other shell's autostart line out of your hyprland.lua (and its key binds), log out,"
            warn "and run this again. To install anyway: ./install.sh --force"
            if $dry; then
                say "(--dry-run: this is where it would stop)"
            elif ! $assume_yes && tty_ok && ask_no "install Vitreus next to it anyway?"; then
                say "going on, as you said"
            else
                fail "stopped before changing anything. Nothing was installed."
            fi
        fi
    fi
fi

# ── 1. packages ────────────────────────────────────────────────────────────
if $deps; then
    if have pacman; then
        missing=""
        for p in $pacman_pkgs; do pacman -Qi "$p" > /dev/null 2>&1 || missing="$missing $p"; done
        if [ -n "$missing" ] && $refresh; then
            # Settings reads this line: the update itself needs no sudo, so it only says what is missing.
            printf 'vitreus-missing:%s\n' "$missing"
        elif [ -n "$missing" ]; then
            say "packages to install:$missing"
            if ask "install them with sudo pacman?"; then
                run sudo pacman -S --needed --noconfirm $missing
            else
                warn "skipped: parts of Vitreus will stay quiet without them"
            fi
        else
            say "the packages are all there"
        fi
        aur_missing=""
        for p in $aur_pkgs; do pacman -Qi "$p" > /dev/null 2>&1 || aur_missing="$aur_missing $p"; done
        if [ -n "$aur_missing" ] && ! $refresh; then
            helper=""
            have yay && helper=yay
            [ -z "$helper" ] && have paru && helper=paru
            if [ -n "$helper" ]; then
                say "from the AUR (with $helper):$aur_missing"
                if ask "install them?"; then
                    run "$helper" -S --needed --noconfirm $aur_missing
                fi
            else
                warn "from the AUR, and no helper (yay, paru) was found:$aur_missing"
                for p in $aur_missing; do
                    echo "    git clone https://aur.archlinux.org/$p.git && cd $p && makepkg -si"
                done
            fi
        fi
    else
        say "this is not an Arch-family system, so nothing is installed for you. Vitreus uses these programs"
        say "(all optional except pleamar, and hyprsunset on Hyprland: each of the others only enables one feature):"
        cat <<'LIST'
    cava            the bass pulse and the equalizer
    playerctl       cover art
    awww            the wallpaper picker
    mpvpaper (AUR), ffmpeg  video wallpapers (mp4, webm, mov): mpvpaper plays them, ffmpeg takes the frame the rest of the shell reads; ffmpeg also reads the webcam
    iris            theming from the wallpaper (https://aur.archlinux.org/packages/iris-colors)
    imagemagick     wallpaper thumbnails, the launcher's picture previews, Snap's marked-up picture
    wl-clipboard    the launcher copying (wl-copy: results, snippets), and Capture copying a screenshot
    polkit, python-gobject  the authentication dialog (Vitreus asks for your password when something wants admin rights)
    python-pyte, SpaceMono Nerd Font  the Desk's terminal (pyte keeps its screen; the font is Space Grotesk's monospaced sibling)
    pipewire (pw-play), sound-theme-freedesktop  the sounds notifications make
    tesseract       reading the text of a screenshot (Copy text, Ask), on the screenshot card, and in Snap (Copy text, Blur private info)
    grim, slurp     Capture's screenshots (slurp picks the region for a recording; Snap picks a screenshot's)
    jq              Snap finding the focused monitor and its windows (from Hyprland's monitors and clients)
    wf-recorder     Capture's screen recording (slurp picks the region)
    power-profiles-daemon  the power profile in Power (powerprofilesctl)
    cliphist        the launcher's clipboard search (something must run: wl-paste --watch cliphist store)
    xdg-utils       the launcher opening a file or a web search (xdg-open)
    curl            weather, remote cover art and the launcher's web answers
    NetworkManager  Wi-Fi (nmcli)
    BlueZ           Bluetooth (bluetoothctl)
    brightnessctl   the brightness slider
    hypridle        Caffeine
    hyprsunset      Night mode (REQUIRED on Hyprland: https://github.com/hyprwm/hyprsunset)
    libnotify       calendar reminders (notify-send)
    xdg-user-dirs   finding your Pictures folder
    git, fontconfig
    python          the font setup of the Retro and UwU themes and the font picker (bin/vitreus-fonts)
    Audiowide, Mochiy Pop One, Orbitron  the typefaces of the Retro, UwU and Cyber themes (Space Grotesk's neighbours, installed into ~/.local/share/fonts)
LIST
    fi
    # On Hyprland hyprsunset is not optional: Night mode is driven by it. Without it the shell would have to fall back to a Hyprland
    # screen shader, which makes Hyprland rebuild its buffers on every change and flicker while a panel is open. Elsewhere Night
    # mode is not there anyway, so it is only a note.
    if ! $dry && ! have hyprsunset; then
        if { have Hyprland || have hyprland; } && ! $refresh; then
            fail "hyprsunset is required on Hyprland (it is what Night mode uses) and it is not installed. Install it and run this again: sudo pacman -S hyprsunset (Arch), or your distribution's package (https://github.com/hyprwm/hyprsunset)"
        fi
        warn "hyprsunset is not installed: Night mode (Hyprland only) will not work"
    fi
    have hyprctl || warn "Hyprland was not found. Vitreus needs a Wayland compositor with layer-shell; the list of running windows needs Hyprland."

    # ── 2. pleamar ──
    if $refresh; then :  # pleamar and the fonts are not touched here
    elif have pleamar || [ -x "$HOME/.local/bin/pleamar" ]; then
        pv=$( { pleamar --version 2> /dev/null || "$HOME/.local/bin/pleamar" --version 2> /dev/null; } | sed -n 's/^pleamar \([0-9][0-9.]*\).*/\1/p' | head -1)
        say "pleamar is installed${pv:+ ($pv)}"
        if $do_wm && ! have pleamar-wm && [ ! -x "$HOME/.local/bin/pleamar-wm" ] && have pleamar-update; then
            say "pleamar-wm, pleamar's window manager, is not installed"
            if ask "install it now? (built from source; Vitreus then also runs as a session at the login screen)"; then
                if $dry; then echo "    would run: pleamar-update --all"
                else pleamar-update --all || warn "pleamar-update --all failed: run it yourself to get pleamar-wm"
                fi
            fi
        fi
        # 0.4.14 is where text `size:` takes expressions; older pleamar stops at "expected a number here" and the shell does not load.
        pleamar_min="0.4.14"
        if [ -n "$pv" ] && [ "$(printf '%s\n%s\n' "$pleamar_min" "$pv" | sort -V | head -1)" != "$pleamar_min" ]; then
            warn "Vitreus needs pleamar $pleamar_min or newer (this is $pv): older ones fail to load the scene with \"expected a number here\""
            if have pleamar-update; then
                if ask "update pleamar now? (built from source; a few minutes)"; then
                    if $dry; then echo "    would run: pleamar-update"
                    else pleamar-update || warn "pleamar-update failed: run it yourself before starting Vitreus"
                    fi
                fi
            else
                warn "pleamar-update was not found: reinstall pleamar from https://github.com/k4ditano/pleamar"
            fi
        fi
    else
        say "pleamar, the runtime Vitreus is written for, is not installed"
        if ask "install it now? (it is built from source; the first time takes a few minutes)"; then
            # pleamar's installer brings the window manager (pleamar-wm) and Marea too unless told --alone: ask first.
            pleamar_args=""
            if $do_wm && ! ask "install pleamar-wm, the window manager, as well? (otherwise only pleamar, for Hyprland and other compositors)"; then
                pleamar_args="-s -- --alone"
                do_wm=false
            fi
            if $dry; then
                echo "    would run: curl -fsSL $pleamar_installer | sh $pleamar_args"
            else
                have curl || fail "curl is needed to fetch pleamar's installer"
                # shellcheck disable=SC2086
                curl -fsSL "$pleamar_installer" | sh $pleamar_args || fail "pleamar's installer failed (see above); Vitreus needs it"
            fi
        else
            warn "without pleamar Vitreus cannot run. Install it from https://github.com/k4ditano/pleamar"
        fi
    fi

    # ── 3. the font ──
    # (Settings > About runs this with --refresh, which downloads what a theme draws in without asking: a theme added by an update has its typeface.)
    ask_font() { $refresh && return 0; ask "$1"; }
    if $deps; then
    if have fc-list && fc-list 2> /dev/null | grep -qi 'space grotesk'; then
        say "the Space Grotesk font is installed"
    elif ask_font "install the Space Grotesk font (into $fonts)?"; then
        if $dry; then
            echo "    would download $font_url"
        else
            mkdir -p "$fonts"
            curl -fsSL -m 120 "$font_url" -o "$fonts/SpaceGrotesk[wght].ttf" || warn "could not download the font: install Space Grotesk yourself"
            have fc-cache && fc-cache -f "$fonts" > /dev/null 2>&1 || true
        fi
    fi
    # The Retro theme's Audiowide and the UwU theme's Mochiy Pop One: what Settings > Theme draws the shell in on those themes (the font picker can
    # choose any other). Without them the theme keeps Space Grotesk.
    if have fc-list && fc-list 2> /dev/null | grep -qi 'audiowide'; then
        say "the Audiowide font is installed"
    elif ask_font "install the Audiowide font, for the Retro theme (into $fonts_dot)?"; then
        if $dry; then
            echo "    would download $dot_url"
        else
            mkdir -p "$fonts_dot"
            curl -fsSL -m 120 "$dot_url" -o "$fonts_dot/Audiowide-Regular.ttf" || warn "could not download Audiowide: the Retro theme will use Space Grotesk until you install it"
            curl -fsSL -m 120 "$dot_licence_url" -o "$fonts_dot/OFL.txt" 2> /dev/null || true
            have fc-cache && fc-cache -f "$fonts_dot" > /dev/null 2>&1 || true
        fi
    fi
    if have fc-list && fc-list 2> /dev/null | grep -qi 'mochiy pop one'; then
        say "the Mochiy Pop One font is installed"
    elif ask_font "install the Mochiy Pop One font, for the UwU theme (into $fonts_mochiy)?"; then
        if $dry; then
            echo "    would download $mochiy_url"
        else
            mkdir -p "$fonts_mochiy"
            curl -fsSL -m 120 "$mochiy_url" -o "$fonts_mochiy/MochiyPopOne-Regular.ttf" || warn "could not download Mochiy Pop One: the UwU theme will use Space Grotesk until you install it"
            have fc-cache && fc-cache -f "$fonts_mochiy" > /dev/null 2>&1 || true
        fi
    fi
    if have fc-list && fc-list 2> /dev/null | grep -qi 'orbitron'; then
        say "the Orbitron font is installed"
    elif ask_font "install the Orbitron font, for the Cyber theme (into $fonts_orbitron)?"; then
        if $dry; then
            echo "    would download $orbitron_url"
        else
            mkdir -p "$fonts_orbitron"
            curl -fsSL -m 120 "$orbitron_url" -o "$fonts_orbitron/Orbitron[wght].ttf" || warn "could not download Orbitron: the Cyber theme will use Space Grotesk until you install it"
            curl -fsSL -m 120 "$orbitron_licence_url" -o "$fonts_orbitron/OFL.txt" 2> /dev/null || true
            have fc-cache && fc-cache -f "$fonts_orbitron" > /dev/null 2>&1 || true
        fi
    fi
    fi
fi

# ── 4. the shell itself ────────────────────────────────────────────────────
have git || fail "git is needed to fetch Vitreus"
if $refresh; then
    :  # Settings has pulled already
elif [ -d "$dest/.git" ]; then
    if $dry; then echo "    would run: git -C $dest pull --ff-only (your changes, and the monitors Settings chose, carried across)"; else
        g() { git -C "$dest" -c user.name=vitreus -c user.email=vitreus@localhost "$@"; }
        before=$(g rev-parse HEAD)
        # Settings keeps which monitors show the bar and the lock in the scenes' own `screens:` lines. They are put back to the stock
        # ones for the pull, so that they never stand in its way, and the chosen ones are written again after it.
        bar_sed='/^    surface \{/{s/.*screens: ([^;]*);.*/\1/p;q;}'
        lock_sed='/^        screens: /{s/^        screens: (.*)$/\1/p;q;}'
        set_screens() {
            if [ -n "$1" ] && [ -f "$dest/vitreus.plm" ]; then sed -i -E "/^    surface \{/s/screens: [^;]*;/screens: $1;/" "$dest/vitreus.plm"; fi
            if [ -n "$2" ] && [ -f "$dest/lockscreen/lockscreen.plm" ]; then sed -i -E "/^        screens: /s/screens: .*/screens: $2/" "$dest/lockscreen/lockscreen.plm"; fi
        }
        bar_s=$(sed -n -E "$bar_sed" "$dest/vitreus.plm" 2> /dev/null || true)
        lock_s=$(sed -n -E "$lock_sed" "$dest/lockscreen/lockscreen.plm" 2> /dev/null || true)
        set_screens "$(g show HEAD:vitreus.plm 2> /dev/null | sed -n -E "$bar_sed")" "$(g show HEAD:lockscreen/lockscreen.plm 2> /dev/null | sed -n -E "$lock_sed")"
        # wm-palette.plm was tracked once and is git-ignored now (Vitreus writes it): kept aside, so the pull that takes it out of git
        # does not take it off the disk, or trip over the colours Vitreus wrote into it.
        wmpal=""
        if g ls-files --error-unmatch wm-palette.plm > /dev/null 2>&1; then
            wmpal=$(mktemp)
            cp "$dest/wm-palette.plm" "$wmpal"
            g checkout --quiet -- wm-palette.plm
        fi
        # Anything else of yours (a tuned pleamar-wm scene or keys.conf, which are linked here, or your own edits) is set aside for
        # the pull and put back on top of it. If it no longer fits the new version, nothing is updated and your changes stay.
        stashed=false
        held=false
        if ! { g diff --quiet && g diff --cached --quiet; }; then
            g stash push --quiet -m "install.sh: your changes, set aside for an update" && stashed=true
        fi
        g pull --ff-only --quiet || warn "could not bring it up to date (left as it was)"
        if $stashed && ! g stash pop --quiet > /dev/null 2>&1; then
            warn "your changes in $dest do not fit the new version: it is left as it was, with your changes"
            held=true
            g reset --quiet --hard "$before"
            g stash pop --quiet || warn "your changes are kept in git's stash: git -C $dest stash list"
        fi
        set_screens "$bar_s" "$lock_s"
        if [ -n "$wmpal" ]; then
            cp "$wmpal" "$dest/wm-palette.plm"
            rm -f "$wmpal"
        fi
        after=$(g rev-parse HEAD)
        if [ "$before" != "$after" ]; then
            say "new since last time:"
            g log --oneline --no-decorate "$before..$after" | sed 's/^/    /' | head -20
        elif ! $held; then
            say "Vitreus is up to date"
        fi
    fi
elif [ -e "$dest" ]; then
    fail "$dest exists and is not a copy of Vitreus: move it away and run this again"
else
    say "fetching Vitreus into $dest"
    run mkdir -p "$(dirname "$dest")"
    run git clone --quiet --depth 1 "$repo" "$dest"
fi

# ── 5. the palettes ────────────────────────────────────────────────────────
# Vitreus rewrites both from your wallpaper, so git ignores them: the stock ones are the `.default` copies. palette.plm is the lock
# screen's, wm-palette.plm pleamar-wm's (its window borders).
for pal in palette wm-palette; do
    if [ -f "$dest/$pal.plm" ]; then
        say "$pal.plm is there (Vitreus rewrites it from your wallpaper)"
    elif [ -f "$dest/$pal.default.plm" ] || $dry; then
        say "making $pal.plm from the stock colours"
        run cp "$dest/$pal.default.plm" "$dest/$pal.plm"
    fi
done

# ── the launcher's helper ──────────────────────────────────────────────────
# Clipboard pictures cannot go through the logic (its command output is text), so a small script does the piping.
# It is linked into ~/.local/bin, where pleamar looks for programs.
if [ -x "$dest/bin/vitreus-clipimg" ] || $dry; then
    run mkdir -p "$HOME/.local/bin"
    run ln -sf "$dest/bin/vitreus-clipimg" "$HOME/.local/bin/vitreus-clipimg"
    # The authentication dialog's agent, which the shell starts by itself. Only one polkit agent can hold a session: if another is
    # already running (polkit-gnome, hyprpolkitagent...), it keeps answering and this one says so and ends.
    [ -x "$dest/bin/vitreus-polkit-agent" ] && run ln -sf "$dest/bin/vitreus-polkit-agent" "$HOME/.local/bin/vitreus-polkit-agent"
    # Settings > System monitor's data source: started by the shell while that page is showing, and stopped when it is not.
    [ -x "$dest/bin/vitreus-sysmon" ] && run ln -sf "$dest/bin/vitreus-sysmon" "$HOME/.local/bin/vitreus-sysmon"
    [ -x "$dest/bin/vitreus-term" ] && run ln -sf "$dest/bin/vitreus-term" "$HOME/.local/bin/vitreus-term"
    # The keeper the autostart lines run each scene under: it starts a scene again when it stops (a crash on a monitor's wake).
    [ -x "$dest/bin/vitreus-files" ] && run ln -sf "$dest/bin/vitreus-files" "$HOME/.local/bin/vitreus-files"
    [ -x "$dest/bin/vitreus-keep" ] && run ln -sf "$dest/bin/vitreus-keep" "$HOME/.local/bin/vitreus-keep"
    # For a problem report that does not need the shell to be running: `vitreus-report` writes one text file to read and send.
    [ -x "$dest/bin/vitreus-report" ] && run ln -sf "$dest/bin/vitreus-report" "$HOME/.local/bin/vitreus-report"
    case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) warn "$HOME/.local/bin is not in your PATH: the launcher's clipboard pictures need it" ;; esac
# Hyprland does not read ~/.bashrc: if ~/.local/bin is only added there, its binds and exec-once lines never find
# `pleamar`. hypr_vitreus.lua adds it to PATH itself; whatever you start from hyprland.lua has to do the same.
fi

# ── 6. Hyprland key binds ──────────────────────────────────────────────────
# hypr_vitreus.lua (SUPER + L lock, SUPER + Space Settings) is linked into ~/.config/hypr and loaded from hyprland.lua
# after hypr_style.lua. Settings > Display and > Hyprland keep what you choose in vitreus_monitors.lua and
# vitreus_hypr.lua, loaded the same way (they do not exist until something is kept, hence pcall); so does vitreus_colors.lua, the
# window border colours Iris sets.
hyprdir="$conf/hypr"
hyprlua="$hyprdir/hyprland.lua"
if $do_binds; then
    if [ ! -f "$hyprlua" ]; then
        say "no $hyprlua, so no key binds set up (hyprland.conf users: bind a key to  pleamar --say vitreus \"emit settings_toggle\" )"
    elif grep -q 'hypr_vitreus' "$hyprlua"; then
        say "hyprland.lua already loads hypr_vitreus.lua"
        run ln -sf "$dest/hypr_vitreus.lua" "$hyprdir/hypr_vitreus.lua"
        # An install from before a file existed never loaded it (vitreus_colors.lua keeps the room the left bar takes; without
        # it, every reload of the config gives the gaps back): add what is missing, inside the block if it is there.
        for mod in vitreus_monitors vitreus_hypr vitreus_colors; do
            grep -q "$mod" "$hyprlua" && continue
            if $dry; then
                echo "    would add pcall(require, \"$mod\") to $hyprlua"
            else
                line="pcall(require, \"$mod\")"
                if grep -q '^-- <<< vitreus' "$hyprlua"; then
                    tmp=$(mktemp)
                    awk -v l="$line" '/^-- <<< vitreus/ { print l } { print }' "$hyprlua" > "$tmp" && cat "$tmp" > "$hyprlua"
                    rm -f "$tmp"
                else
                    echo "$line" >> "$hyprlua"
                fi
                say "added $line to $hyprlua"
            fi
        done
    elif ask "load Vitreus's key binds (SUPER + L, SUPER + Space) from $hyprlua?"; then
        run ln -sf "$dest/hypr_vitreus.lua" "$hyprdir/hypr_vitreus.lua"
        if $dry; then
            echo "    would back up $hyprlua and add four pcall(require, ...) lines to its end"
        else
            cp "$hyprlua" "$hyprlua.before-vitreus"
            {
                echo ""
                echo "-- >>> vitreus (added by its installer; ./install.sh --uninstall takes it out)"
                echo 'pcall(require, "hypr_vitreus")'
                grep -q 'vitreus_monitors' "$hyprlua" || echo 'pcall(require, "vitreus_monitors")'
                grep -q 'vitreus_hypr' "$hyprlua" || echo 'pcall(require, "vitreus_hypr")'
                grep -q 'vitreus_colors' "$hyprlua" || echo 'pcall(require, "vitreus_colors")'
                echo "-- <<< vitreus"
            } >> "$hyprlua"
            say "added to $hyprlua (the old one is $hyprlua.before-vitreus); Hyprland reloads it by itself"
        fi
    fi
fi

# ── start with the desktop ─────────────────────────────────────────────────
# Each scene runs under bin/vitreus-keep, which starts it again if it stops while the session lasts.
line="vitreus-keep $dest/vitreus.plm \"\$HOME/.local/share/pleamar/vitreus/vitreus.log\""
# PLEAMAR_SWAPCHAIN=1: pleamar 0.4's own frames let the lock commit its region before its first frame, and Hyprland kills a lock
# surface for that ("Null buffer attached"): the lock screen died the moment it showed. Take it out once pleamar fixes it.
lockline="PLEAMAR_SWAPCHAIN=1 vitreus-keep $dest/lockscreen/lockscreen.plm"
transline="vitreus-keep $dest/wptrans/wptrans.plm"
clockline="vitreus-keep $dest/desktopclock/desktopclock.plm"
sysmonline="vitreus-keep $dest/desktopsysmon/desktopsysmon.plm"
cavaline="vitreus-keep $dest/desktopcava/desktopcava.plm"
if $do_autostart; then
    # Lines from before the keeper started the scenes straight, once: they go through it now (with or without VAR=value words in front: a line that
    # keeps the shell outside the keeper is one that nothing starts again when Settings stops it to apply a theme's font).
    envp='([A-Za-z_][A-Za-z0-9_]*=[^ ]+ )*'
    if [ -f "$autostart" ] && grep -qE "^${envp}pleamar --scene $dest/.*\.plm --no-hud\$" "$autostart"; then
        if $dry; then echo "    would put the scenes in $autostart under vitreus-keep"; else
            sed -i -E "s|^(${envp})pleamar --scene ($dest/vitreus\.plm) --no-hud\$|\1vitreus-keep \3 \"\$HOME/.local/share/pleamar/vitreus/vitreus.log\"|; s|^(${envp})pleamar --scene ($dest/[^ ]*\.plm) --no-hud\$|\1vitreus-keep \3|" "$autostart"
            say "the scenes in $autostart now run under vitreus-keep, which starts them again if they stop"
        fi
    fi
    if [ -f "$autostart" ] && grep -q 'vitreus.plm' "$autostart"; then
        say "it is already in $autostart"
    elif ask "start Vitreus with the desktop (add a line to $autostart)?"; then
        run mkdir -p "$(dirname "$autostart")"
        if $dry; then echo "    would add to $autostart: $line"; else printf '%s\n' "$line" >> "$autostart"; fi
    fi
    # The lock screen is a scene of its own (a session lock has to be its own program, so that restarting the shell cannot unlock
    # the session), and the lock buttons and SUPER + L only work while it runs: it always starts with the desktop.
    if [ -f "$autostart" ] && grep -q "^vitreus-keep $dest/lockscreen/lockscreen\.plm" "$autostart"; then
        if $dry; then echo "    would start the lock screen in $autostart with PLEAMAR_SWAPCHAIN=1"; else
            sed -i "s|^vitreus-keep \($dest/lockscreen/lockscreen\.plm\)|PLEAMAR_SWAPCHAIN=1 vitreus-keep \1|" "$autostart"
            say "the lock screen in $autostart now starts with PLEAMAR_SWAPCHAIN=1 (pleamar 0.4 otherwise crashes it on lock)"
        fi
    elif [ -f "$autostart" ] && grep -q 'lockscreen/lockscreen.plm' "$autostart"; then
        say "the lock screen is already in $autostart"
    else
        run mkdir -p "$(dirname "$autostart")"
        if $dry; then echo "    would add to $autostart: $lockline"; else printf '%s\n' "$lockline" >> "$autostart"; fi
        say "the lock screen starts with the desktop too (a line in $autostart): the lock buttons and SUPER + L need it"
    fi
    # The wallpaper picker's hexagon dissolve is a scene of its own as well; without it a pick uses awww's own transition.
    if [ -f "$autostart" ] && grep -q 'wptrans/wptrans.plm' "$autostart"; then
        say "the wallpaper transition is already in $autostart"
    else
        if $dry; then echo "    would add to $autostart: $transline"; else printf '%s\n' "$transline" >> "$autostart"; fi
        say "the wallpaper picker's hexagon dissolve starts with the desktop too (a line in $autostart)"
    fi
    # The desktop clock (digits of glass on the bottom layer) is a scene of its own as well; it starts shown, and turns off from the launcher.
    if [ -f "$autostart" ] && grep -q 'desktopclock/desktopclock.plm' "$autostart"; then
        say "the desktop clock is already in $autostart"
    else
        if $dry; then echo "    would add to $autostart: $clockline"; else printf '%s\n' "$clockline" >> "$autostart"; fi
        say "the desktop clock starts with the desktop too (a line in $autostart); \"Desktop clock: toggle\" in the launcher turns it off"
    fi
    # The desktop system monitor (a small glass card on the bottom layer) is a scene of its own too; it starts hidden, and "Desktop system monitor: toggle" in the launcher shows it.
    if [ -f "$autostart" ] && grep -q 'desktopsysmon/desktopsysmon.plm' "$autostart"; then
        say "the desktop system monitor is already in $autostart"
    else
        if $dry; then echo "    would add to $autostart: $sysmonline"; else printf '%s\n' "$sysmonline" >> "$autostart"; fi
        say "the desktop system monitor starts with the desktop too, hidden (a line in $autostart); \"Desktop system monitor: toggle\" in the launcher shows it"
    fi
    # The desktop audio visualiser (cava's bars on the bottom layer) is a scene of its own too; it starts hidden, and "Desktop audio visualiser: toggle" in the launcher, the desktop's menu or Settings > Widgets shows it.
    if [ -f "$autostart" ] && grep -q 'desktopcava/desktopcava.plm' "$autostart"; then
        say "the desktop audio visualiser is already in $autostart"
    else
        if $dry; then echo "    would add to $autostart: $cavaline"; else printf '%s\n' "$cavaline" >> "$autostart"; fi
        say "the desktop audio visualiser starts with the desktop too, hidden (a line in $autostart); \"Desktop audio visualiser: toggle\" in the launcher shows it"
    fi
    # The desktop stickers and the desktop's right-click menu are scenes of their own too, but Vitreus starts them itself (see vitreus.luau), so they have no line here.
fi

# ── the daemons Vitreus talks to ───────────────────────────────────────────
# awww (the wallpaper picker drives it), hypridle (Caffeine, and the idle lock) and the clipboard history (the launcher's clipboard
# search has nothing without it). No `wm:` prefix: pleamar runs these lines on Hyprland (`pleamar --autostart`) and in pleamar-wm
# alike. Each is guarded, so one that is already running (yours, or one from hyprland.lua) is not started twice; the guard
# matches on the process name, because pgrep -f would find the very `sh -c` that runs the line.
if $do_autostart; then
    if [ -f "$autostart" ] && grep -q '^# >>> vitreus (session)' "$autostart"; then
        say "the daemon lines are already in $autostart"
    else
        if $dry; then echo "    would add to $autostart: awww-daemon, awww restore, hypridle, wl-paste --watch cliphist store"; else
            mkdir -p "$(dirname "$autostart")"
            # older versions wrote these as `wm:` lines, which Hyprland never ran: replace them
            if [ -f "$autostart" ] && grep -q '^# >>> vitreus (pleamar-wm)' "$autostart"; then
                sed -i '/^# >>> vitreus (pleamar-wm)/,/^# <<< vitreus/d' "$autostart"
            fi
            {
                echo "# >>> vitreus (session) (added by its installer; ./install.sh --uninstall takes it out)"
                for l in "pgrep -x awww-daemon > /dev/null || awww-daemon" \
                         "sleep 1; awww restore" \
                         "pgrep -x hypridle > /dev/null || hypridle" \
                         "pgrep -x wl-paste > /dev/null || wl-paste --watch cliphist store"; do
                    echo "$l"
                done
                echo "# <<< vitreus"
            } >> "$autostart"
            say "added the daemons (wallpaper, idle lock, clipboard history) to $autostart"
        fi
    fi
fi

# ── 7. pleamar-wm ──────────────────────────────────────────────────────────
# Vitreus runs on pleamar-wm (a session chosen at the login screen) as well as on Hyprland. Everything below is skipped when
# pleamar-wm is not installed, and each file of yours is only replaced when it is still the stock one.
wmdir="$dest/pleamar-wm"
if $do_wm && [ -d "$wmdir" ] && { have pleamar-wm || [ -x "$HOME/.local/bin/pleamar-wm" ]; }; then
    # `wm:` lines are read by pleamar-wm's session only. Marea is the shell pleamar-wm comes with: with Vitreus as the bar,
    # she and swaybg (which needs a wallpaper file that is not there) are turned off, not deleted.
    # (The daemons Vitreus needs are started for every compositor, in the section above.)
    if $do_autostart && [ -f "$autostart" ] && ! $dry; then
        sed -i -e 's/^marea start\([[:space:]].*\)\{0,1\}$/# \0  (turned off by Vitreus: it is the bar now)/' \
               -e 's/^wm: swaybg\(.*\)$/# wm: swaybg\1  (turned off by Vitreus: it is the bar now)/' "$autostart"
    fi
    # keys: Vitreus's launcher, Settings, lock, wallpaper picker, capture, volume. Only over the stock file (just `defaults` and comments).
    keys="$conf/pleamar/keys.conf"
    if [ -L "$keys" ] && [ "$(readlink -f "$keys")" = "$(readlink -f "$wmdir/keys.conf")" ]; then
        say "pleamar-wm's keys are already Vitreus's"
    elif [ ! -e "$keys" ] || ! grep -qvE '^[[:space:]]*(#|$|defaults[[:space:]]*$)' "$keys"; then
        run mkdir -p "$conf/pleamar"
        run ln -sf "$wmdir/keys.conf" "$keys"
        say "pleamar-wm's keys are Vitreus's now ($keys)"
    else
        warn "$keys has bindings of yours: left alone (Vitreus's are in $wmdir/keys.conf)"
    fi
    # the window manager's scene (slim glass title bars): only where there is none of yours.
    wmscene="$conf/pleamar/wm"
    if [ -L "$wmscene" ] && [ "$(readlink -f "$wmscene")" = "$(readlink -f "$wmdir/wm")" ]; then
        say "pleamar-wm's window scene is Vitreus's"
    elif [ ! -e "$wmscene" ] || { [ -d "$wmscene" ] && [ -z "$(ls -A "$wmscene" 2> /dev/null)" ]; }; then
        run rm -rf "$wmscene"
        run ln -sfn "$wmdir/wm" "$wmscene"
        say "pleamar-wm's window scene is Vitreus's now ($wmscene)"
    else
        warn "$wmscene has a scene of yours: left alone (Vitreus's is in $wmdir/wm)"
    fi
    # hyprctl for a desktop that is not Hyprland (ahead of /usr/bin; on Hyprland it hands over to the real one).
    if [ ! -e "$HOME/.local/bin/hyprctl" ] || [ -L "$HOME/.local/bin/hyprctl" ]; then
        run mkdir -p "$HOME/.local/bin"
        run ln -sf "$wmdir/hyprctl" "$HOME/.local/bin/hyprctl"
    fi
    # the login-screen entry: needs root, so it is asked for. It installs the session wrapper (/usr/local/bin/pleamar-wm-session), the
    # entry in /usr/share/wayland-sessions and pleamar-wm's portals. The wrapper starts `pleamar-wm session` with the desktop's names and PATH.
    if [ -x /usr/local/bin/pleamar-wm-session ] && grep -q '^Exec=pleamar-wm-session' /usr/share/wayland-sessions/pleamar-wm.desktop 2> /dev/null; then
        say "pleamar-wm is in the login screen's list of sessions"
    elif ask "put pleamar-wm in the login screen's list of sessions (needs sudo)?"; then
        run sudo sh "$wmdir/install-session.sh" || warn "could not: run  sudo sh $wmdir/install-session.sh  yourself"
    fi
elif $do_wm && [ -d "$wmdir" ]; then
    say "pleamar-wm is not installed, so no session for it (pleamar's installer has it: https://github.com/k4ditano/pleamar)"
fi

# ── services it talks to ───────────────────────────────────────────────────
if have systemctl; then
    systemctl is-active --quiet bluetooth 2> /dev/null || say "Bluetooth is off: sudo systemctl enable --now bluetooth"
    systemctl is-active --quiet NetworkManager 2> /dev/null || say "NetworkManager is not running: Wi-Fi needs it (sudo systemctl enable --now NetworkManager)"
    have powerprofilesctl && { systemctl is-active --quiet power-profiles-daemon 2> /dev/null || say "power-profiles-daemon is not running: the power profile in Power needs it (sudo systemctl enable --now power-profiles-daemon)"; }
fi

say "done."
$refresh && exit 0
# ── --test: run Vitreus now, in place of the other shell, and nothing else changed ──
if $trial; then
    if $dry; then
        say "(--dry-run: --test would stop Quickshell, if it is running, and start Vitreus)"
    else
        [ -n "${WAYLAND_DISPLAY:-}" ] || fail "--test starts Vitreus on the screen: run it from inside your Wayland session"
        mkdir -p "$data/pleamar/vitreus"
        : > "$trial_file"
        # Remember how each running Quickshell was started (qs -c name ...), so --stop can start it again.
        for pid in $(pgrep -x qs; pgrep -x quickshell); do
            args=$(tr '\0' ' ' < "/proc/$pid/cmdline" 2> /dev/null | sed 's/ $//')
            case "$args" in *" ipc "*|*" kill"*|*" list"*|"") continue ;; esac
            grep -qxF "$args" "$trial_file" || echo "$args" >> "$trial_file"
        done
        if [ -s "$trial_file" ]; then
            say "stopping your Quickshell (./install.sh --stop starts it again)"
            pkill -x qs; pkill -x quickshell
            sleep 1
        fi
        export PATH="$HOME/.local/bin:$PATH"
        setsid vitreus-keep "$dest/vitreus.plm" "$data/pleamar/vitreus/vitreus.log" > /dev/null 2>&1 < /dev/null &
        say "Vitreus is starting. Nothing starts at login and no key binds were added."
        say "To go back to your shell: ./install.sh --stop     To keep Vitreus: ./install.sh"
    fi
    exit 0
fi

echo
echo "  Start it now:          $line"
echo "  Lock screen, too:      $lockline"
echo "  Hexagon dissolve:      $transline"
echo "  With the desktop:      autostart is read by pleamar's own session; on Hyprland run \`pleamar --autostart\`:"
echo "                         hyprland.lua:   hl.on(\"hyprland.start\", function () hl.exec_cmd(\"PATH=\\\"\$HOME/.local/bin:\$PATH\\\" pleamar --autostart\") end)"
echo "                         hyprland.conf:  exec-once = ~/.local/bin/pleamar --autostart   (Hyprland's PATH may lack ~/.local/bin)"
echo "  Keys (with the binds): SUPER + Space launcher, SUPER + SHIFT + Space settings, SUPER + B wallpaper picker, SUPER + L lock (see lockscreen/README.md)"
echo "  Daemons:               awww, hypridle and the clipboard history start from $autostart (nothing to add to hyprland.lua)"
echo "  pleamar-wm:            log out and choose «pleamar-wm» in the login screen (SDDM: click the session name at the bottom right)"
echo "  Update later:          run this script again"
echo "  Its settings:          $data/pleamar/vitreus  (iris.json, weather-config.json, ...)"
echo
echo "  It becomes the desktop's notification server when it starts, and gives that back when it exits."
