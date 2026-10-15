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

## Local voice dictation (Sway/Noctalia)

Stow `voxtype` alongside `sway` for the developer-oriented config and F8
hold-to-talk bindings:

```sh
stow --target="$HOME" sway voxtype
```

The dotfiles configure Voxtype but do not install its binary or speech model.
On Void, `wtype` and `wl-clipboard` are installed by `void-setup-elogind`.
Install the [Voxtype CPU binary](https://github.com/peteonrails/voxtype/releases/latest)
to `~/.local/bin/voxtype`, then download the English model with
`voxtype setup --download`. Log in again to start the Sway-managed daemon, or
run `voxtype daemon` in a terminal for an immediate test. Hold F8 while
speaking, release it to type into the focused app, and review text before
submitting it to an agent or terminal. The optional Noctalia status widget is
`gabedunn/voxtype` from its community plugins.

The [Zed package](zed/README.md) adds a minimal Vim setup with a Space leader,
programming shortcuts, and a few Helix-inspired selection bindings:

```sh
stow --target="$HOME" zed
```
