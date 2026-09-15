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
# Git branch text is expanded from a separate variable, never parsed as PS1.
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
alias xq='xbps-query -Rs'            # search repository packages
alias xl='xbps-query -l'             # list installed
alias xf='xbps-query -Rf'            # files in a package
alias xo='xbps-query -o'             # which package owns a file
alias xclean='sudo xbps-remove -Ooy' # drop orphans and cached packages

# --- Sway / Wayland --------------------------------------------------------
alias swayreload='swaymsg reload'
alias swaytree='swaymsg -t get_tree | jq'
# Disabled outputs have no current_mode, so label them instead of asking jq to
# divide null by 1000. Remove the old alias when re-sourcing this file.
unalias swayoutputs 2>/dev/null || :
swayoutputs() {
    local outputs
    outputs=$(command swaymsg -t get_outputs) || return
    command jq -r '.[] | "\(.name)  \(.make // "unknown") \(.model // "unknown")  \(if .current_mode then "\(.current_mode.width)x\(.current_mode.height)@\(.current_mode.refresh / 1000)" else "disabled" end)"' <<<"$outputs"
}
alias swaylog='less +G "${XDG_STATE_HOME:-$HOME/.local/state}/sway.log"'

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

# --- fzf -------------------------------------------------------------------
if command -v fzf >/dev/null; then
    export FZF_DEFAULT_OPTS="
        --height=45% --layout=reverse --border=rounded --info=inline
        --bind=ctrl-/:toggle-preview,ctrl-u:preview-page-up,ctrl-d:preview-page-down"

    # Live project-text search: rerun ripgrep on every query change, preview
    # the selected match, then open it at the matching line in $VISUAL/$EDITOR.
    rgf() {
        local dependency query="$*" selection encoded file rest line editor
        local decode_status rg_command jq_filter
        local -a editor_command

        for dependency in rg jq fzf bat base64 xargs; do
            if ! command -v -- "$dependency" >/dev/null; then
                printf 'rgf: required command is not installed: %s\n' \
                    "$dependency" >&2
                return 127
            fi
        done

        # Keep machine-readable metadata separate from the displayed match.
        # The path is Base64-encoded so every valid Unix filename is safe,
        # including names containing colons, tabs, or newlines.
        jq_filter='
            def escape_controls:
                reduce (explode[]) as $codepoint ("";
                    . + (if $codepoint < 32 then
                             (([$codepoint] | implode | @json)[1:-1])
                         elif $codepoint >= 127 and $codepoint <= 159 then
                             "<control>"
                         else
                             ([$codepoint] | implode)
                         end)
                );

            def byte_index($byte_offset):
                reduce (explode[]) as $codepoint (
                    {bytes: 0, index: 0};
                    if .bytes < $byte_offset then
                        .bytes += ([$codepoint] | implode | utf8bytelength)
                        | .index += 1
                    else .
                    end
                )
                | .index;

            def highlight_matches($text; $matches):
                reduce $matches[] as $match (
                    {text: "", index: 0};
                    ($text | byte_index($match.start)) as $start
                    | ($text | byte_index($match.end)) as $end
                    | .index as $previous
                    | .text += (($text[$previous:$start] | escape_controls)
                               + "\u001b[1m\u001b[31m"
                               + ($text[$start:$end] | escape_controls)
                               + "\u001b[0m")
                    | .index = $end
                )
                | .index as $end
                | .text + ($text[$end:] | escape_controls);

            select(.type == "match")
            | .data as $d
            | ($d.line_number | tostring) as $line
            | (($d.submatches[0].start + 1) | tostring) as $column
            | (($d.path.text // "<non-UTF-8 path>") | escape_controls)
              as $display_path
            | (if $d.lines.text != null
               then (($d.lines.text | rtrimstr("\n")) as $text
                     | highlight_matches($text; $d.submatches))
               else "<non-UTF-8 matching line>"
               end) as $display_line
            | [
                (if $d.path.text != null
                 then ($d.path.text | @base64)
                 else $d.path.bytes
                 end),
                $line,
                $column,
                ("\u001b[35m" + $display_path + "\u001b[0m:"
                 + "\u001b[32m" + $line + "\u001b[0m:"
                 + $column + ":" + $display_line)
              ]
            | @tsv + "\u0000"
        '
        rg_command='if test -n {q}; then command rg --json --smart-case -- {q} | command jq -jrc "$RGF_JQ_FILTER"; fi'

        selection=$(
            RGF_JQ_FILTER=$jq_filter command fzf --ansi --disabled --read0 \
                --query="$query" --prompt='RG> ' --delimiter=$'\t' \
                --with-nth=4 --nth=4 \
                --preview='printf %s {1} | base64 --decode | xargs -0 -r bat --color=always --style=numbers --highlight-line {2} --' \
                --preview-window='right,60%,border-left,+{2}/2' \
                --bind="start:reload:$rg_command || true" \
                --bind="change:reload:$rg_command || true"
        ) || return

        encoded=${selection%%$'\t'*}
        rest=${selection#*$'\t'}
        line=${rest%%$'\t'*}

        if [[ -z $encoded || ! $line =~ ^[0-9]+$ ]]; then
            printf 'rgf: invalid selection metadata\n' >&2
            return 1
        fi

        # The sentinel preserves any trailing newlines in the decoded path;
        # command substitution would otherwise remove them.
        file=$(
            printf '%s' "$encoded" | command base64 --decode
            decode_status=${PIPESTATUS[1]}
            printf '\034'
            exit "$decode_status"
        ) || {
            printf 'rgf: could not decode selected path\n' >&2
            return 1
        }
        file=${file%$'\034'}

        editor=${VISUAL:-${EDITOR:-vim}}
        if command -v -- "$editor" >/dev/null 2>&1; then
            editor_command=("$editor")
        else
            read -r -a editor_command <<<"$editor"
        fi

        if [ "${#editor_command[@]}" -eq 0 ] ||
            ! command -v -- "${editor_command[0]}" >/dev/null 2>&1; then
            printf 'rgf: editor is not executable: %s\n' "$editor" >&2
            return 127
        fi

        command "${editor_command[@]}" "+$line" -- "$file"
    }

    # Ctrl-F is the terminal counterpart of Vim's <leader>fg.
    bind -m emacs-standard -x '"\C-f": rgf'
    bind -m vi-command -x '"\C-f": rgf'
    bind -m vi-insert -x '"\C-f": rgf'

    if command -v fd >/dev/null; then
        export FZF_DEFAULT_COMMAND='fd --type=f --hidden --follow --exclude=.git'
        export FZF_CTRL_T_COMMAND="$FZF_DEFAULT_COMMAND"
        export FZF_ALT_C_COMMAND='fd --type=d --hidden --follow --exclude=.git'
    fi

    command -v bat >/dev/null &&
        export FZF_CTRL_T_OPTS="--preview 'bat -n --color=always --line-range :300 -- {}'"
    command -v eza >/dev/null &&
        export FZF_ALT_C_OPTS="--preview 'eza --tree --level=2 --icons=auto --color=always -- {}'"

    # fzf's Shift-Delete rewrites HISTFILE from this shell's history, losing
    # commands saved by other terminals. Override it even without wl-copy.
    # Reset first so exported bindings never accumulate in nested shells.
    FZF_CTRL_R_OPTS='--bind=shift-delete:ignore'

    if command -v wl-copy >/dev/null; then
        # Generic selections use the whole row. History rows have a numeric
        # index in field one, so Ctrl-Y must drop that field there only.
        FZF_DEFAULT_OPTS+="
        --bind='ctrl-y:execute-silent(printf %s {} | wl-copy)+abort'"
        # fzf, rather than Bash, parses these literal quotes.
        # shellcheck disable=SC2089
        FZF_CTRL_R_OPTS+=" --bind='ctrl-y:execute-silent(printf %s {2..} | wl-copy)+abort'"
    fi
    # shellcheck disable=SC2090
    export FZF_CTRL_R_OPTS

    # Ctrl-T file, Ctrl-R history, Alt-C cd
    [ -r /usr/share/fzf/key-bindings.bash ] && . /usr/share/fzf/key-bindings.bash
    [ -r /usr/share/fzf/completion.bash ] && . /usr/share/fzf/completion.bash
fi

# --- Prompt ----------------------------------------------------------------
# Resolve only the current branch (or abbreviated commit for a detached HEAD),
# without inspecting tracked or untracked files. The title escape gives
# foot/ghostty the useful name shown in noctalia's window switcher; OSC 7 tells
# the terminal the cwd so a new window opens here.
__prompt_osc7() {
    local LC_ALL=C
    local path="$PWD" host="${HOSTNAME-}" encoded='' byte char
    local i

    # OSC 7 takes a file URI. Work byte-by-byte so spaces, URI delimiters and
    # non-ASCII UTF-8 bytes are percent-encoded while path separators remain.
    for ((i = 0; i < ${#path}; i++)); do
        char=${path:i:1}
        case "$char" in
            [a-zA-Z0-9.~_/-]) encoded+="$char" ;;
            *)
                printf -v byte '%%%02X' "'$char"
                encoded+="$byte"
                ;;
        esac
    done

    host=${host%%.*}
    printf '\001\033]7;file://%s%s\033\\\002' "$host" "$encoded"
}

__prompt_git() {
    local branch
    branch=$(command git symbolic-ref --quiet --short HEAD 2>/dev/null) ||
        branch=$(command git rev-parse --short HEAD 2>/dev/null) ||
        return 0

    # Render non-printable bytes visibly, but leave ordinary branch names
    # literal. This is display formatting, NOT a defense against PS1 expansion.
    if [[ $branch == *[![:print:]]* ]]; then
        printf -v branch '%q' "$branch"
    fi

    printf ' \001\033[0;33m\002(%s)\001\033[0m\002' "$branch"
}

__prompt() {
    local status=$?
    local reset='\[\033[0m\]' blue='\[\033[1;34m\]' green='\[\033[0;32m\]'
    local red='\[\033[1;31m\]' dim='\[\033[2m\]'
    local title='\[\033]0;\u@\h: \w\007\]'
    local osc7 mark

    osc7=$(__prompt_osc7)
    # Keep branch-controlled text out of PS1's source. Bash expands this global
    # variable at render time without reinterpreting its contents as commands
    # or prompt escapes. It must outlive this function, so do not make it local.
    __prompt_git_segment=$(__prompt_git)

    if [ "$status" -eq 0 ]; then
        mark="${green}\$${reset}"
    else
        mark="${red}${status}\$${reset}"
    fi

    # root gets a red host so a stray sudo -i is obvious
    if [ "$EUID" -eq 0 ]; then
        PS1="${title}${osc7}${red}\u@\h${reset}${dim}:${reset}${blue}\w${reset}\${__prompt_git_segment}\n${mark} "
    else
        PS1="${title}${osc7}${green}\u@\h${reset}${dim}:${reset}${blue}\w${reset}\${__prompt_git_segment}\n${mark} "
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
