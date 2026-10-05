SHELL := /bin/sh

.PHONY: check check-shell check-audio format-shell

check: check-shell check-audio

check-audio:
	shellcheck --shell=sh sway/.config/sway/scripts/start-audio.sh
	PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s pipewire/tests -v

check-shell:
	shellcheck --shell=bash --external-sources --source-path=SCRIPTDIR bash/.bashrc bash/.bash_profile
	shellcheck --shell=sh bash/.local/bin/manpager
	shfmt --diff --indent 4 --case-indent bash/.bashrc bash/.bash_profile bash/.local/bin/manpager

format-shell:
	shfmt --write --indent 4 --case-indent bash/.bashrc bash/.bash_profile bash/.local/bin/manpager
