# .bashrc -- read by every interactive shell, so keep it to shell behaviour:
# history, options, aliases, completion, prompt. Environment and PATH belong
# in .bash_profile, which runs once per login.

# If not running interactively, don't do anything
[[ $- != *i* ]] && return

# --- History ---------------------------------------------------------------
# Default bash keeps 500 lines and *overwrites* ~/.bash_history on exit, so
# with several foot windows open the last one to close wins and the rest of
# the day's history is lost. histappend plus a per-prompt flush fixes that.
HISTSIZE=100000
HISTFILESIZE=200000
HISTCONTROL=ignoreboth:erasedups # skip dupes and leading-space commands
HISTTIMEFORMAT='%F %T  '
HISTIGNORE='ls:ll:la:bg:fg:exit:clear:history:pwd'

shopt -s histappend # append instead of clobbering
shopt -s cmdhist    # multi-line commands stay one entry
shopt -s histverify # !! expands for review, doesn't fire

# Flush after every command so a crashed terminal loses nothing. Note this
# only *writes*; it deliberately does not re-read, because pulling other
# terminals' commands into your up-arrow makes them unusable. The hook is
# installed with the prompt below so the prompt sees the command's exit status.
__history_append() {
    builtin history -a
}

# --- Shell options ---------------------------------------------------------
# Kitty's Bash integration uses command substitution in PS0 to report the
# current command. Keep prompt expansion enabled so that hook is not printed.
# __prompt_git escapes branch-controlled prompt syntax before it reaches PS1.
shopt -s promptvars

shopt -s checkwinsize            # keep $LINES/$COLUMNS right after resize
shopt -s globstar                # ** recurses
shopt -s autocd                  # `..` instead of `cd ..`
shopt -s cdspell dirspell        # fix minor typos in directory names
shopt -s no_empty_cmd_completion # don't scan $PATH on a bare Tab
shopt -s checkjobs               # warn before exiting with running jobs

# --- Colours ---------------------------------------------------------------
if [ -x /usr/bin/dircolors ]; then
    eval "$(dircolors -b "$HOME/.dircolors" 2>/dev/null || dircolors -b)"
fi

alias grep='grep --color=auto'
alias egrep='grep -E --color=auto'
alias fgrep='grep -F --color=auto'
alias diff='diff --color=auto'
alias ip='ip -color=auto'

# --- Listing (eza) ---------------------------------------------------------
if command -v eza >/dev/null; then
    alias ls='eza --group-directories-first --icons=auto'
    alias ll='eza -l --group-directories-first --icons=auto --git --time-style=long-iso'
    alias la='eza -la --group-directories-first --icons=auto --git --time-style=long-iso'
    alias lt='eza --tree --level=2 --group-directories-first --icons=auto'
    alias tree='eza --tree --group-directories-first --icons=auto'
else
    alias ls='ls --color=auto --group-directories-first'
    alias ll='ls -lh --color=auto --group-directories-first'
    alias la='ls -lha --color=auto --group-directories-first'
fi
alias l.='ls -d .*'

# --- Safety ----------------------------------------------------------------
# -I is the tolerable one: it prompts for recursive deletes and for more than
# three files, but stays quiet for `rm one-file`.
alias rm='rm -I --preserve-root'
alias cp='cp -i'
alias mv='mv -i'
# Keep normal mkdir errors visible; use md when parent creation is intended.
unalias mkdir 2>/dev/null || :
alias md='mkdir -p'
alias ln='ln -i'
alias chown='chown --preserve-root'
alias chmod='chmod --preserve-root'

# --- Void package management -----------------------------------------------
alias xu='sudo xbps-install -Suv'    # full system update
alias xr='sudo xbps-remove -R'       # remove + now-orphaned deps
alias xl='xbps-query -l'             # list installed
alias xf='xbps-query -Rf'            # files in a package
alias xo='xbps-query -o'             # which package owns a file
alias xclean='sudo xbps-remove -Ooy' # drop orphans and cached packages

# --- Sway / Wayland --------------------------------------------------------
alias swayreload='swaymsg reload'
alias swaytree='swaymsg -t get_tree | jq'
alias swayoutputs='swaymsg -t get_outputs | jq -r ".[] | \"\(.name)  \(.make) \(.model)  \(.current_mode.width)x\(.current_mode.height)@\(.current_mode.refresh/1000)\""'
alias swaylog='less +G "$XDG_STATE_HOME/sway.log"'

# --- Misc ------------------------------------------------------------------
alias df='df -hT -x tmpfs -x devtmpfs'
alias du='du -h'
alias free='free -h'
alias ports='ss -tulpn'
alias lg='lazygit'

if command -v bat >/dev/null && command -v col >/dev/null; then
    alias bathelp='bat --plain --language=help'
    # Syntax-highlighted man pages. /usr/bin/man is mandoc here, which marks
    # bold/underline with backspace-overstrike rather than ANSI SGR, so strip
    # it with col(1). (MANROFFOPT is a man-db/groff knob; mandoc ignores it.)
    export MANPAGER="$HOME/.local/bin/manpager"
fi

# --- Functions -------------------------------------------------------------
# Print one PATH entry per line without word splitting or pathname expansion.
path() { printf '%s\n' "${PATH//:/$'\n'}"; }

# yazi wrapper: leaves the shell in whatever directory yazi exited from.
y() {
    local tmp cwd='' status=0
    tmp=$(mktemp -t "yazi-cwd.XXXXXX") || {
        printf 'y: could not create a temporary file\n' >&2
        return 1
    }

    command yazi "$@" --cwd-file="$tmp" || status=$?
    if [ -r "$tmp" ]; then
        IFS= read -r -d '' cwd <"$tmp" || :
    fi

    if [ "$status" -eq 0 ] && [ -n "$cwd" ] && [ "$cwd" != "$PWD" ] && [ -d "$cwd" ]; then
        builtin cd -- "$cwd" || status=$?
    fi

    if ! command rm -f -- "$tmp"; then
        [ "$status" -ne 0 ] || status=1
    fi
    return "$status"
}

mkcd() {
    if [ "$#" -ne 1 ]; then
        printf 'usage: mkcd DIRECTORY\n' >&2
        return 2
    fi
    command mkdir -p -- "$1" || return
    builtin cd -- "$1" || return
}

# Extract any archive without remembering the flags.
extract() {
    local archive
    if [ "$#" -ne 1 ]; then
        printf 'usage: extract ARCHIVE\n' >&2
        return 2
    fi
    if [ ! -f "$1" ]; then
        printf 'extract: not a file: %s\n' "$1" >&2
        return 1
    fi

    archive=$1
    [[ $archive == -* ]] && archive="./$archive"

    case "$archive" in
        *.tar.bz2 | *.tbz2) command tar -xjf "$archive" ;;
        *.tar.gz | *.tgz) command tar -xzf "$archive" ;;
        *.tar.xz | *.txz) command tar -xJf "$archive" ;;
        *.tar.zst) command tar --zstd -xf "$archive" ;;
        *.tar) command tar -xf "$archive" ;;
        *.bz2) command bunzip2 -- "$archive" ;;
        *.gz) command gunzip -- "$archive" ;;
        *.xz) command unxz -- "$archive" ;;
        *.zip) command unzip "$archive" ;;
        *.7z) command 7z x -- "$archive" ;;
        *.rar) command unrar x "$archive" ;;
        *)
            printf "extract: unsupported archive: %s\n" "$1" >&2
            return 1
            ;;
    esac
}

# --- fzf -------------------------------------------------------------------
if command -v fzf >/dev/null; then
    export FZF_DEFAULT_OPTS="
        --height=45% --layout=reverse --border=rounded --info=inline
        --bind=ctrl-/:toggle-preview,ctrl-u:preview-page-up,ctrl-d:preview-page-down"

    if command -v fd >/dev/null; then
        export FZF_DEFAULT_COMMAND='fd --type=f --hidden --follow --exclude=.git'
        export FZF_CTRL_T_COMMAND="$FZF_DEFAULT_COMMAND"
        export FZF_ALT_C_COMMAND='fd --type=d --hidden --follow --exclude=.git'
    fi

    command -v bat >/dev/null &&
        export FZF_CTRL_T_OPTS="--preview 'bat -n --color=always --line-range :300 -- {}'"
    command -v eza >/dev/null &&
        export FZF_ALT_C_OPTS="--preview 'eza --tree --level=2 --icons=auto --color=always -- {}'"

    if command -v wl-copy >/dev/null; then
        # Generic selections use the whole row. History rows have a numeric
        # index in field one, so Ctrl-Y must drop that field there only.
        FZF_DEFAULT_OPTS+="
        --bind='ctrl-y:execute-silent(printf %s {} | wl-copy)+abort'"
        FZF_CTRL_R_OPTS="${FZF_CTRL_R_OPTS:+$FZF_CTRL_R_OPTS }"
        # fzf, rather than Bash, parses these literal quotes.
        # shellcheck disable=SC2089
        FZF_CTRL_R_OPTS+="--bind='ctrl-y:execute-silent(printf %s {2..} | wl-copy)+abort'"
        # shellcheck disable=SC2090
        export FZF_CTRL_R_OPTS
    fi

    # Ctrl-T file, Ctrl-R history, Alt-C cd
    [ -r /usr/share/fzf/key-bindings.bash ] && . /usr/share/fzf/key-bindings.bash
    [ -r /usr/share/fzf/completion.bash ] && . /usr/share/fzf/completion.bash
fi

# --- Prompt ----------------------------------------------------------------
# Resolve only the current branch (or abbreviated commit for a detached HEAD),
# without inspecting tracked or untracked files. The title escape gives
# foot/ghostty the useful name shown in noctalia's window switcher; OSC 7 tells
# the terminal the cwd so a new window opens here.
__prompt_git() {
    local branch
    branch=$(command git symbolic-ref --quiet --short HEAD 2>/dev/null) ||
        branch=$(command git rev-parse --short HEAD 2>/dev/null) ||
        return 0

    # promptvars expands PS1 again when Bash draws it. Quote characters that
    # could otherwise execute prompt syntax from an attacker-controlled branch.
    printf -v branch '%q' "$branch"

    printf ' \001\033[0;33m\002(%s)\001\033[0m\002' "$branch"
}

__prompt() {
    local status=$?
    local reset='\[\033[0m\]' blue='\[\033[1;34m\]' green='\[\033[0;32m\]'
    local red='\[\033[1;31m\]' dim='\[\033[2m\]'
    local title='\[\033]0;\u@\h: \w\007\]'
    local osc7='\[\033]7;file://\h\w\033\\\]'
    local mark

    if [ "$status" -eq 0 ]; then
        mark="${green}\$${reset}"
    else
        mark="${red}${status}\$${reset}"
    fi

    # root gets a red host so a stray sudo -i is obvious
    if [ "$EUID" -eq 0 ]; then
        PS1="${title}${osc7}${red}\u@\h${reset}${dim}:${reset}${blue}\w${reset}$(__prompt_git)\n${mark} "
    else
        PS1="${title}${osc7}${green}\u@\h${reset}${dim}:${reset}${blue}\w${reset}$(__prompt_git)\n${mark} "
    fi
}

# Preserve hooks installed by terminal integrations or other startup files.
# An array keeps each hook intact; our prompt must run first to capture $?.
__install_prompt_hooks() {
    local declaration hook
    local -a preserved_hooks=()

    declaration=$(declare -p PROMPT_COMMAND 2>/dev/null) || declaration=
    if [[ $declaration == declare\ -a* ]]; then
        for hook in "${PROMPT_COMMAND[@]}"; do
            case "$hook" in
                __prompt | __history_append | __zoxide_hook) ;;
                *) preserved_hooks+=("$hook") ;;
            esac
        done
    elif [ -n "${PROMPT_COMMAND:-}" ]; then
        # Also migrate the scalar installed by the previous version of this file.
        hook=$PROMPT_COMMAND
        if [[ $hook == '__prompt; history -a'* ]]; then
            hook=${hook#'__prompt; history -a'}
            hook=${hook#;}
            hook=${hook# }
        fi
        hook=${hook%';__zoxide_hook'}
        hook=${hook%'; __zoxide_hook'}
        [ "$hook" = __zoxide_hook ] && hook=
        [ -n "$hook" ] && preserved_hooks+=("$hook")
    fi

    PROMPT_COMMAND=(__prompt __history_append "${preserved_hooks[@]}")
}
__install_prompt_hooks
unset -f __install_prompt_hooks

# --- zoxide ----------------------------------------------------------------
# Must come last so zoxide can install its prompt hook after ours.
# `z foo` jumps to the best match, `zi foo` picks from an fzf list.
command -v zoxide >/dev/null && eval "$(zoxide init bash)"
