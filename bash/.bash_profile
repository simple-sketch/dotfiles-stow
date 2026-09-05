# .bash_profile -- read once per login shell.
#
# Everything that belongs in the *environment* lives here rather than in
# .bashrc, because .bashrc runs again for every nested interactive shell
# (tmux panes, `bash` inside vim, foot windows spawned by sway).

# --- PATH ------------------------------------------------------------------
# Idempotent so re-sourcing this file cannot duplicate entries.
path_prepend() {
    [ -d "$1" ] || return 0
    case ":$PATH:" in
        *":$1:"*) ;;
        *) PATH="$1${PATH:+:$PATH}" ;;
    esac
}

path_prepend "$HOME/.local/bin"
unset -f path_prepend
export PATH

# --- XDG base directories --------------------------------------------------
# Set explicitly so tools that read them without applying the spec defaults
# still land in the right place.
export XDG_CONFIG_HOME="$HOME/.config"
export XDG_DATA_HOME="$HOME/.local/share"
export XDG_STATE_HOME="$HOME/.local/state"
export XDG_CACHE_HOME="$HOME/.cache"

# --- Preferred programs ----------------------------------------------------
export EDITOR=vim
export VISUAL=vim
export SUDO_EDITOR=vim # `sudo -e` / `sudoedit`
export PAGER=less
# Keep this command in sync with `set $browser` in the Sway config.
export BROWSER=firefox

# -R keeps colour escapes, -F skips the pager for output shorter than a
# screen, -X stops less from wiping the screen when it exits.
export LESS='-R -F -X -i -M -j.5'
export LESSHISTFILE="$XDG_STATE_HOME/less_history"

# --- Wayland / sway session hints ------------------------------------------
# These are exported for every login shell, not just the tty1 branch below,
# so a session started some other way (a display manager, `sway` run by hand)
# gets the same environment.
export MOZ_ENABLE_WAYLAND=1          # Firefox/Waterfox native Wayland
export GDK_BACKEND=wayland,x11       # GTK, with XWayland fallback
export QT_QPA_PLATFORM='wayland;xcb' # Qt, with XWayland fallback
export QT_WAYLAND_DISABLE_WINDOWDECORATION=1
export _JAVA_AWT_WM_NONREPARENTING=1     # fixes blank JetBrains/Java windows
export ELECTRON_OZONE_PLATFORM_HINT=auto # VS Code, Discord et al. go native
export XCURSOR_THEME=Bibata-Modern-Ice   # System cursor theme
export XCURSOR_SIZE=24

# --- Interactive setup -----------------------------------------------------
# shellcheck source=.bashrc
[ -f "$HOME/.bashrc" ] && . "$HOME/.bashrc"

# --- sway autostart --------------------------------------------------------
if [ -z "$WAYLAND_DISPLAY" ] && [ "$(tty)" = "/dev/tty1" ]; then
    export XDG_CURRENT_DESKTOP=sway
    export XDG_SESSION_DESKTOP=sway
    export XDG_SESSION_TYPE=wayland

    # elogind has no user service manager, so nothing has started a session bus
    # by this point. dbus-run-session starts one, exports its address and execs
    # sway inside it, which ties the bus to the session instead of to the boot.
    #
    # The log redirect is what you read after a failed start: without it a sway
    # crash on tty1 scrolls past and is gone.
    mkdir -p "$XDG_STATE_HOME"
    exec dbus-run-session sway >"$XDG_STATE_HOME/sway.log" 2>&1
fi
