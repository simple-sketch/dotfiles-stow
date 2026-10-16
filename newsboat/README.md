# Newsboat

This package links `config` and `urls`. Newsboat keeps its article cache in a real `~/.newsboat` directory.

For a new installation, create the directory before Stow:

```sh
mkdir -p "$HOME/.newsboat"
stow --simulate --verbose --no-folding --target="$HOME" newsboat
stow --no-folding --target="$HOME" newsboat
```

If `~/.newsboat` is a link to this repository, stop Newsboat before you change the link.
Save the cache in a real directory outside this repository. Remove the old link, then use the commands above.
Do not remove your cache until you verify the new directory and its files.
