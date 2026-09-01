# dotfiles

Personal GNU Stow packages for Void Linux and a Sway/Wayland desktop. The
configuration is intentionally machine-specific; review the Sway autostart,
Shikane output profiles, input layout, and application choices before using it
on another system.

## Packages

Each top-level directory is a Stow package whose contents mirror paths below
`$HOME`.

| Package | Installs | Purpose |
| --- | --- | --- |
| `bash` | `~/.bash_profile`, `~/.bashrc`, `~/.local/bin/manpager` | Login environment, Sway startup, interactive Bash, and man-page pager |
| `inputrc` | `~/.inputrc` | Readline completion and history-search keys |
| `sway` | `~/.config/sway` | Compositor configuration and helper scripts |
| `shikane` | `~/.config/shikane` | Automatic docked, undocked, portrait, and extended output profiles |
| `noctalia` | `~/.config/noctalia` | Bar, launcher, lock/idle behavior, and screenshot integration |
| `foot` | `~/.config/foot` | Terminal configuration |
| `kitty` | `~/.config/kitty` | Kitty terminal theme configuration |
| `lazyvim` | `~/.config/nvim` | Neovim/LazyVim configuration and plugin lock file |
| `vim` | `~/.vimrc`, `~/.vim/plugin/custom-yazi.vim`, `~/.local/share/applications/vim.desktop` | Vim configuration, local Yazi integration, and a Foot launcher entry |
| `yazi` | `~/.config/yazi` | File manager and Vim/Neovim integration |
| `lazygit` | `~/.config/lazygit` | Lazygit with delta renderers and confirmed push |
| `swayimg` | `~/.config/swayimg`, `~/.local/share/applications/swayimg.desktop` | Wayland image viewer settings and desktop entry |
| `flameshot`, `satty` | `~/.config/{flameshot,satty}` | Screenshot capture and annotation |
| `xdg-desktop-portal` | `~/.config/xdg-desktop-portal` | GTK portals, with wlr for screenshots and screen sharing |

Git identity/defaults and MIME associations are deliberately not tracked.

## Requirements

Install GNU Stow and Git first. A complete desktop session also expects Sway,
D-Bus, Noctalia, Foot, Firefox, Shikane, Swayimg, `jq`, WirePlumber,
`polkit` (using Noctalia's native authentication agent), and the GTK and wlr
XDG portal backends.

Bindings and optional shell integrations use tools including Alacritty,
Neovide, Yazi, Lazygit, delta, Flameshot, Satty, Grim, Slurp, wl-clipboard,
brightnessctl, `pactl`, playerctl, `bat`, `col`, `eza`, `fzf`, `fd`, and
Zoxide. Missing optional shell tools are skipped or have a fallback, but a
binding for a missing desktop application will not work.

Maintaining the shell configuration additionally requires Make, ShellCheck,
and shfmt. Validate or format all tracked shell files from the repository root:

```bash
make check
make format-shell
```

## Install

Clone directly below `$HOME`, choose the packages wanted on this machine, and
run a dry-run before creating links:

```bash
git clone https://github.com/simple-sketch/dotfiles-stow.git "$HOME/dotfiles-stow"
cd "$HOME/dotfiles-stow"

packages=(bash inputrc sway shikane noctalia foot kitty lazyvim yazi lazygit swayimg flameshot satty xdg-desktop-portal)
stow --simulate --verbose=2 --target="$HOME" "${packages[@]}"
stow --target="$HOME" "${packages[@]}"
```

Use `*/` instead of the array to install every package. Stow stops on conflicts
rather than overwriting an existing file. Move conflicting files to a backup
first; do not use `--adopt` unless moving their contents into this repository
is intentional.

Log out and back in after installing the shell profile. A login on TTY1 starts
Sway automatically. Create the configured screenshot directory if needed:

```bash
mkdir -p "$HOME/Pictures/Screenshots"
```

Restow the same package selection after an update, or remove selected links:

```bash
# Recreate the same selection in each new shell.
packages=(bash inputrc sway shikane noctalia foot kitty lazyvim yazi lazygit swayimg flameshot satty xdg-desktop-portal)
git pull --ff-only
stow --restow --target="$HOME" "${packages[@]}"
stow --delete --target="$HOME" lazyvim
```
