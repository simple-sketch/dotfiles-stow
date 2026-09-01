#!/bin/sh
# Arrange two active Sway outputs horizontally and vertically center them.
#
# Shikane can choose a monitor's preferred mode dynamically, but its position
# field only accepts absolute coordinates. Run this as an output `exec` after
# Shikane has applied modes, transforms and scales; Sway's output rectangles
# then contain the final logical dimensions needed for relative positioning.
#
# Usage: arrange-outputs.sh <left-output> [right-output]
#        arrange-outputs.sh --toggle [extend|portrait]
#
# If right-output is omitted, the sole other active output is used. --toggle
# infers the current left-to-right order and reverses it without a state file.
# An optional profile makes the command mode-aware: it reverses the outputs
# only when that mode is already active and otherwise asks Shikane to apply it.
# Without a profile, a setup that does not have exactly two active outputs
# falls back to "extend" for compatibility.

set -eu

die() {
    printf 'arrange-outputs.sh: %s\n' "$1" >&2
    exit 1
}

toggle_profile=
case $# in
    1)
        left=$1
        requested_right=
        ;;
    2)
        left=$1
        if [ "$left" = --toggle ]; then
            requested_right=
            toggle_profile=$2
            case $toggle_profile in
                extend | portrait) ;;
                *) die 'toggle profile must be extend or portrait' ;;
            esac
        else
            requested_right=$2
        fi
        ;;
    *) die 'usage: arrange-outputs.sh <left-output> [right-output] | --toggle [extend|portrait]' ;;
esac

command -v swaymsg >/dev/null 2>&1 || die 'swaymsg is not installed'
command -v jq >/dev/null 2>&1 || die 'jq is not installed'

if [ "$left" = --toggle ]; then
    # Sort spatially rather than trusting get_outputs array order. When a
    # profile was requested, first verify the connector classes and transforms
    # that distinguish its active mode. A portrait transform may be either 90
    # or 270 because the usable direction depends on how the display is turned.
    # Reversing the resulting names makes the current right output the new left
    # output. Dimensions are fetched again below so this still shares the
    # regular arrangement path used by Shikane's profile hooks.
    if current_order=$(
        swaymsg -t get_outputs -r 2>/dev/null |
            jq -er --arg profile "$toggle_profile" '
                def internal:
                    .name | test("^(eDP|LVDS)-[0-9]+$");
                def external:
                    .name
                    | test("^(DP|HDMI-[AB]|DVI-[ADI]|VGA|USB-C)-[0-9]+(-[0-9]+)*$");
                def rotated_portrait:
                    .transform == "90" or .transform == "270";

                [.[]
                    | select(.active == true)
                    | select(.rect.width > 0 and .rect.height > 0)]
                | select(length == 2)
                | if $profile == "extend" then
                    select(
                        ([.[] | select(internal and .transform == "normal")]
                            | length == 1)
                        and ([.[] | select(external and .transform == "normal")]
                            | length == 1)
                    )
                  elif $profile == "portrait" then
                    select(
                        ([.[] | select(internal and .transform == "normal")]
                            | length == 1)
                        and ([.[] | select(external and rotated_portrait)]
                            | length == 1)
                    )
                  else
                    .
                  end
                | sort_by(.rect.x, .rect.y, .name)
                | [.[0].name, .[1].name]
                | @tsv
            ' 2>/dev/null
    ); then
        old_ifs=$IFS
        IFS="$(printf '\t')"
        read -r requested_right left <<EOF
$current_order
EOF
        IFS=$old_ifs
    else
        command -v shikanectl >/dev/null 2>&1 ||
            die 'shikanectl is not installed'
        exec shikanectl switch "${toggle_profile:-extend}"
    fi
fi

# Connector names normally contain only these characters. Restrict them before
# supplying them to jq or interpolating them into sway commands below.
case $left:$requested_right in
    *[!A-Za-z0-9._:-]*) die 'unsafe character in output name' ;;
esac

# Output commands run only after Shikane reports a successful apply, but give
# Sway IPC a short grace period as well. This also makes resume/dock races less
# brittle. Rect dimensions are logical pixels, so rotation and scaling are
# already accounted for.
attempt=0
layout=
while [ "$attempt" -lt 20 ]; do
    if layout=$(
        swaymsg -t get_outputs -r 2>/dev/null |
            jq -er --arg left "$left" --arg right "$requested_right" '
                . as $outputs
                | ($outputs[]
                    | select(.name == $left and .active == true)) as $l
                | [$outputs[]
                    | select(.active == true and .name != $left)
                    | select(($right == "") or (.name == $right))] as $candidates
                | select($candidates | length == 1)
                | $candidates[0] as $r
                | [$l.rect.width, $l.rect.height,
                   $r.rect.width, $r.rect.height] as $dimensions
                | select(all($dimensions[];
                    type == "number" and . > 0))
                | [$l.name, $dimensions[0], $dimensions[1],
                   $r.name, $dimensions[2], $dimensions[3]]
                | @tsv
            ' 2>/dev/null
    ); then
        break
    fi

    layout=
    attempt=$((attempt + 1))
    sleep 0.05
done

[ -n "$layout" ] ||
    die "could not resolve exactly two active outputs from: $left"

old_ifs=$IFS
IFS="$(printf '\t')"
read -r left_name left_width left_height \
    right_name right_width right_height <<EOF
$layout
EOF
IFS=$old_ifs

# Also validate names discovered from Sway before constructing its commands.
case $left_name:$right_name in
    *[!A-Za-z0-9._:-]*) die 'unsafe character in discovered output name' ;;
esac

# Center the shorter output without introducing negative global coordinates.
if [ "$left_height" -ge "$right_height" ]; then
    left_y=0
    right_y=$(((left_height - right_height) / 2))
else
    left_y=$(((right_height - left_height) / 2))
    right_y=0
fi

swaymsg -q "output $left_name position 0 $left_y"
swaymsg -q "output $right_name position $left_width $right_y"
