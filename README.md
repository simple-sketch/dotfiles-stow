# dotfiles

My personal dotfiles for Void Linux and a Sway/Wayland desktop, managed with GNU Stow. They are machine-specific, so review them before use.

## Install

Requires Git and GNU Stow.

```sh
git clone https://github.com/simple-sketch/dotfiles-stow.git "$HOME/dotfiles-stow"
cd "$HOME/dotfiles-stow"
stow --target="$HOME" bash foot sway
```

Each top-level directory is a Stow package. Replace the package names with the configurations you want, or use `stow --target="$HOME" */` to install everything.
