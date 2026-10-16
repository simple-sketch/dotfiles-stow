# dotfiles

My personal dotfiles for Void Linux and a Sway/Noctalia desktop, managed with GNU Stow.

## Install

Requires Git and GNU Stow.

```sh
git clone https://github.com/simple-sketch/dotfiles-stow.git "$HOME/dotfiles-stow"
cd "$HOME/dotfiles-stow"
stow --target="$HOME" bash foot sway
```

Each top-level directory is a Stow package. Replace the package names with the configurations you want, or use `stow --target="$HOME" */` to install everything.

The [Zed package](zed/README.md) adds a minimal Vim setup with a Space leader,
programming shortcuts, and a few Helix-inspired selection bindings:

```sh
stow --target="$HOME" zed
```
