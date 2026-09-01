SHELL := /bin/sh

.PHONY: check check-shell format-shell

check: check-shell

check-shell:
	shellcheck --shell=bash --external-sources --source-path=SCRIPTDIR bash/.bashrc bash/.bash_profile
	shellcheck --shell=sh bash/.local/bin/manpager
	shfmt --diff --indent 4 --case-indent bash/.bashrc bash/.bash_profile bash/.local/bin/manpager

format-shell:
	shfmt --write --indent 4 --case-indent bash/.bashrc bash/.bash_profile bash/.local/bin/manpager
