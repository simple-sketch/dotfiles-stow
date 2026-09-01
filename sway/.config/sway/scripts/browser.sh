#!/bin/sh
# Focus-or-launch a browser -- or any other app; nothing here is
# browser-specific.
#
#   focused window is the app  -> open a second window
#   app has a window elsewhere -> focus it (sway follows to that workspace)
#   app has no window at all   -> launch it
#
# Usage: browser.sh <command> [args...]
#
# Environment:
#   BROWSER_ID          override the window pattern (see Matching)
#   BROWSER_NEW_WINDOW  flag that opens a second window (default --new-window;
#                       empty = just run the command again). qutebrowser wants
#                       "--target window", for example.
#
# Matching
#   Sway does all of it. Every question below is asked as a sway criteria and
#   answered by sway's own matching engine -- there is no tree walking and no
#   string comparison here, because sway already does both better:
#
#     [con_id=__focused__ app_id="..."]      is the focused window the browser?
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
#   Two browsers need a hand-written pattern in BROWSER_ID, and the for_window
#   rules in the sway config need the same widening:
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

id=${BROWSER_ID:-"(?i)$(basename "$1")"}

# Already looking at it -> a second window, right here on this workspace.
if swaymsg -q "[con_id=__focused__ app_id=\"$id\"] nop" ||
   swaymsg -q "[con_id=__focused__ class=\"$id\"] nop"; then
    # Unquoted on purpose: an empty BROWSER_NEW_WINDOW disappears, and a
    # multi-word one ("--target window") splits into separate arguments.
    exec "$@" ${BROWSER_NEW_WINDOW---new-window}
fi

# Open somewhere -> focus it. The workspace=__focused__ probes come first so a
# window on this workspace wins over one that would drag us to another.
for criteria in \
    "app_id=\"$id\" workspace=__focused__" \
    "class=\"$id\" workspace=__focused__" \
    "app_id=\"$id\"" \
    "class=\"$id\""
do
    swaymsg -q "[$criteria] focus" && exit 0
done

# Not running -> launch it. The for_window rules in the sway config put it on
# workspace 1; doing that here instead would only cover windows this script
# launched, and miss every browser window opened by anything else.
exec "$@"
