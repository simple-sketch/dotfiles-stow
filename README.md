# dotfiles

My personal dotfiles for Void Linux and a Sway/Noctalia desktop, managed with GNU Stow.

## Install

Requires Git and GNU Stow.

```sh
git clone https://github.com/simple-sketch/dotfiles-stow.git "$HOME/dotfiles-stow"
cd "$HOME/dotfiles-stow"
stow --target="$HOME" bash foot sway pipewire
```

Each top-level directory is a Stow package. Replace the package names with the configurations you want, or use `stow --target="$HOME" */` to install everything.

The [PipeWire package](pipewire/README.md) includes Bluetooth-audio crash
recovery, the PulseAudio compatibility server, clean-machine Void Linux setup,
and isolated tests. Install it alongside `sway` so the audio launcher has its
required drop-ins. It replaces the distribution's unsupervised WirePlumber
example; do not enable a second audio startup mechanism.

The [Zed package](zed/README.md) adds a minimal Vim setup with a Space leader,
programming shortcuts, and a few Helix-inspired selection bindings:

```sh
stow --target="$HOME" zed
```
