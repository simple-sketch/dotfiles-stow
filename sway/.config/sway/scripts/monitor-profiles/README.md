# Monitor profiles

Sway shortcuts and Shikane hooks share `../monitor-profiles.py`. It serializes
changes, checks the resulting output state, positions displays using their
logical dimensions, and reports results through desktop notifications.

| Shortcut | Action |
| --- | --- |
| Super+P | Open the profile picker in Noctalia's launcher |
| Super+Shift+I | Laptop only, including with an external monitor connected |
| Super+Shift+B | External only, landscape |
| Super+Shift+G | Landscape on both screens; press again to swap sides |
| Super+Shift+V | Portrait external plus laptop; press again to swap sides |

The picker marks the current profile and offers only profiles supported by the
connected displays. Escape cancels. Noctalia's `dmenu` interface is the default;
for a future Swaybar setup, change the picker binding to
`$displays pick --menu wmenu`. Notifications use `notify-send`, which Noctalia
receives through the desktop notification service.

## Lid and workspaces

Closing the lid with one external monitor connected saves the current profile,
left/right order, scaling, portrait direction, visible workspaces and focus,
then selects external-only mode. Reopening restores that layout and returns
existing workspaces to their saved outputs. Repeated lid events and config
reloads do not overwrite the saved open-lid layout.

Closing the lid without an external monitor does not disable the only display
or change the system's suspend policy. If the external monitor is disconnected
while closed, reopening selects the laptop display. A different docking setup
uses the automatic profile instead of restoring settings from other hardware.

Ordinary profile switches also remember workspace destinations before disabling
an output, so returning to two screens restores displaced workspaces. Closed
workspaces are not recreated. Use the controller for manual changes so it can
capture placement before Shikane disables an output.

Shikane starts once per Sway session. Sway's reload hook restores the last
verified layout without restarting or reloading Shikane. State and locks live
under `$XDG_RUNTIME_DIR/sway-monitor-profiles-<session>/`; they expire with the
login session and are not preferences saved across reboots.

## Commands and requirements

```sh
python3 ~/.config/sway/scripts/monitor-profiles.py pick
python3 ~/.config/sway/scripts/monitor-profiles.py switch laptop
python3 ~/.config/sway/scripts/monitor-profiles.py toggle portrait
```

`arrange-outputs.sh` remains a compatibility entry point for explicit output
names and `--toggle [extend|portrait]`. Shikane's profile-level hooks instead use
`monitor-profiles.py applied "$SHIKANE_PROFILE_NAME"`: obsolete hooks are ignored,
and completed swaps are left in place.

Requires Python 3 (standard library only), Sway, Shikane, `notify-send`, and
Noctalia with `noctalia dmenu`. Wmenu is optional. Profiles cover one laptop
panel, with zero or one external monitor. More displays produce a clear error
instead of requesting a profile that cannot match.

## Verification

From `~/.config/sway`:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/monitor-profiles/tests/test_profiles.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/monitor-profiles/tests/integration.py
```

The integration suite starts separate headless Sway and Shikane processes with
private sockets and real Foot windows. It tests profile changes, rotation,
fractional scaling, workspace restoration, lid events, reloads, concurrent hooks
and swaps, and unsuccessful profile requests. Display names are mapped to the
synthetic outputs; notification delivery and picker input are captured instead
of reaching the desktop. It does not simulate physical lid hardware or suspend.

Use `--shikane-config PATH` to test a staged Shikane configuration. Logs remain in
the printed `/tmp/monitor-profiles-integration.*` directory.
