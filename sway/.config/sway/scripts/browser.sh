#!/bin/sh
# Focus-or-launch a browser -- or any other app; nothing here is
# browser-specific.
#
#   app is focused on 1       -> open another window on workspace 1
#   app has a window on 1     -> focus it, without opening another window
#   app has a window elsewhere -> bring one window to workspace 1 and focus it
#   app has no window at all   -> launch it on workspace 1
#
# Only this shortcut enforces workspace 1. Detached tabs stay where created.
#
# Usage: browser.sh <command> [args...]
#
# Environment:
#   BROWSER_ID          override the window pattern (see Matching)
#   BROWSER_NEW_WINDOW  space-separated flags for another window (default
#                       --new-window; empty = run the command again)
#
# Matching
#   Sway matches the browser pattern, preferring a window on workspace 1.
#
#     [app_id="..." workspace=__focused__]   is one open on this workspace?
#     [app_id="..."]                         is one open anywhere?
#
#   swaymsg exits 0 when a criteria matches and 2 ("No matching node.") when it
#   does not, which is the entire control flow.
#
#   The pattern is PCRE2 and sway matches it unanchored, so "(?i)" plus the
#   command name finds essentially any browser: (?i)firefox matches "Firefox",
#   "firefox-esr" and "org.mozilla.firefox"; (?i)waterfox matches "waterfox"
#   and "net.waterfox.waterfox"; (?i)brave matches "Brave-browser" and
#   "com.brave.Browser". app_id covers Wayland windows, class covers XWayland
#   ones -- criteria have no OR, so each is a separate probe.
#
#   Two browsers need a hand-written pattern in BROWSER_ID:
#     - one whose app_id does not contain the command name: google-chrome-stable
#       opens windows called "google-chrome", so BROWSER_ID='(?i)google-chrome'
#     - one short enough to collide: "zen" also matches a stray zenity dialog,
#       so BROWSER_ID='(?i)^(app\.zen_browser\.)?zen$'

die() {
    printf 'browser.sh: %s\n' "$1" >&2
    command -v swaynag >/dev/null 2>&1 && swaynag -t warning -m "browser.sh: $1" &
    exit 1
}

[ "$#" -gt 0 ] || die 'usage: browser.sh <command> [args...]'
command -v "$1" >/dev/null 2>&1 || die "command not found: $1"
command -v jq >/dev/null 2>&1 || die 'command not found: jq'

id=${BROWSER_ID:-"(?i)$(basename "$1")"}

focus_on_first() {
    # Pin the selected window across both commands: moving it changes focus.
    # Never move every matching window (some may be detached tabs elsewhere).
    swaymsg -q '[con_id=__focused__] move --no-auto-back-and-forth container to workspace number 1, focus' ||
        die 'cannot move and focus the browser on workspace 1'
}

launch_on_first() {
    # Ask Sway to launch again from workspace 1 so its activation token and PID
    # tracking refer to workspace 1, not the workspace where Super+Y was pressed.
    command_line=
    for argument do
        escaped=$(printf '%s' "$argument" | sed "s/'/'\\\\''/g")
        command_line="$command_line '$escaped'"
    done
    swaymsg -q "exec exec $command_line" || die 'cannot launch the browser on workspace 1'
    exit 0
}

# Check before switching workspaces. A browser focused elsewhere only gets
# brought to workspace 1; another window is requested only when already on 1.
# Use a numeric ID: con_id=__focused__ is ambiguous on an empty workspace.
focused_on_first=$(swaymsg -r -t get_tree | jq -r '
    .. | objects | select(.type == "workspace" and .num == 1)
    | .. | objects
    | select(.focused == true and (.app_id != null or .window != null)) | .id
') || die 'cannot inspect the focused Sway window'
if [ -n "$focused_on_first" ] && {
    swaymsg -q "[con_id=$focused_on_first app_id=\"$id\"] nop" ||
    swaymsg -q "[con_id=$focused_on_first class=\"$id\"] nop"
}; then
    # Intentional splitting allows flags such as qutebrowser's --target window.
    # shellcheck disable=SC2086
    launch_on_first "$@" ${BROWSER_NEW_WINDOW---new-window}
fi

# Prefer a window already on workspace 1; otherwise bring one back from elsewhere.
swaymsg -q 'workspace --no-auto-back-and-forth number 1' || die 'cannot switch to workspace 1'
for criteria in \
    "app_id=\"$id\" workspace=__focused__" \
    "class=\"$id\" workspace=__focused__" \
    "app_id=\"$id\"" \
    "class=\"$id\""
do
    if swaymsg -q "[$criteria] focus"; then
        focus_on_first
        exit 0
    fi
done

# No windows -> launch on the workspace selected above.
launch_on_first "$@"
