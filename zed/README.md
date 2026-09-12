# Zed: Vim editing with a little Helix

A small configuration using Zed's built-in Vim mode, language servers, Git UI,
tasks, and syntax selections. No keybinding or theme extensions are needed.
Settings and action names were checked against Zed 1.19.2
(`df181c6f58d02677b385fa947d6bfde6d3530078`).

## Install

From the repository root:

```sh
stow --simulate --verbose --target="$HOME" zed
stow --target="$HOME" zed
```

This links `settings.json` and `keymap.json` into `~/.config/zed/`. Stow reports a
conflict if an existing file would be replaced; move that file to a backup before
retrying. Zed reloads these files automatically. To unlink the package:

```sh
stow --delete --target="$HOME" zed
```

## Editing defaults

- Vim Normal mode on startup; relative line numbers in Normal mode and absolute
  numbers in Insert mode. Yanks use the system clipboard and briefly highlight.
- Space is the leader. Pause for 500 ms to see the available key continuations.
- Smart-case search: lowercase queries ignore case; uppercase makes it exact.
- Manual save and formatting, matching this repository's Neovim preference.
  Use `Space c f` to format. Project settings can override user defaults.
- Built-in One Dark theme, steady cursor, reduced UI motion, no minimap or inline
  blame, and inlay hints off until requested. Inline diagnostic text is hidden;
  diagnostic navigation and the diagnostics view are still available.
- Code stays unwrapped; Markdown and plain text wrap at the editor width.
  Markdown trailing spaces are preserved because they can mean hard line breaks.
  Indentation and language tools use Zed/project defaults and `.editorconfig`.

## Custom shortcuts

Keys separated by spaces are pressed in sequence. Uppercase letters mean Shift.
Leader shortcuts work in Normal and Visual mode in full editors. Split navigation
with Ctrl-H/J/K/L works in Normal mode, the project panel, and empty panes.
Insert mode, search fields, menus, and terminal input retain their usual bindings.

| Keys | Action |
| --- | --- |
| `Space f f` | Find file |
| `Space f g` or `Space /` | Search project |
| `Space f b` or `Space b` | Pick an open buffer across panes |
| `Space f s` / `Space f S` | Find symbol in file / project |
| `Space f p` | Open recent project |
| `Space e` | Toggle project panel focus |
| `Space r` | Open text replacement, seeded from cursor/selection |
| `Space c r` | Rename symbol through the language server |
| `Space c a` or `Space a` | Code actions |
| `Space c f` | Format |
| `Space k` | Hover documentation |
| `Space x x` | Project diagnostics |
| `Space g g` | Toggle Git panel focus |
| `Space g d` | Expand/collapse selected Git hunks |
| `[g` / `]g` | Previous / next Git change (Helix aliases) |
| `Space t t` | Toggle terminal panel |
| `Space t r` / `Space t R` | Pick task / rerun last task |
| `Space w w` / `Space w W` | Save file / all files |
| `Space w v` / `Space w s` | Split right / below |
| `Ctrl-h/j/k/l` | Focus pane left / down / up / right |
| `Space w q` | Close active tab, with normal save prompts |
| `Space u i` | Toggle inlay hints |
| `Space u w` | Toggle line wrapping |
| `Space u z` | Toggle focused pane zoom |
| `Space ,` / `Space ?` | Open settings file / keymap editor |

Task commands use tasks supplied by the project or language support. Language
server actions require the appropriate language support and a running server;
install a language extension from Zed when the language is not bundled.

## Helix-inspired selection and identifier editing

| Keys | Action |
| --- | --- |
| `Space .` | Show jump labels at visible word starts; type a label to jump |
| `Alt-o` / `Alt-i` | Expand / shrink a syntax selection |
| `Alt-p` / `Alt-n` in Visual mode | Select previous / next syntax sibling |
| `Alt-s` in Visual mode | Split selection into a selection per line |
| `Alt-w` / `Alt-b` / `Alt-e` | Next subword start / previous start / next end |
| `S` in Visual mode, then a delimiter | Surround selection |

For example, put the cursor inside a function argument and press `Alt-o` repeatedly
to select progressively larger syntax nodes; press `Alt-i` to shrink again. Then
use ordinary Vim `c`, `d`, or `y`. Use `c Alt-e` to change a part of a `camelCase`
or `snake_case` identifier. Select text and press `S )` to surround it in parentheses.

Full Helix mode is deliberately disabled: normal Vim `x`, `s`, `%`, `;`, `,`, marks,
macros, and text objects keep their meanings. Helix's `gw` jump is on `Space .`,
leaving Vim `gw`/`gq` for rewrapping. Visual `S` is the one deliberate Vim override;
`c`/`s` still change the selection, and `R` retains the linewise substitute action.

## Useful built-ins to learn

These already ship with Zed's Vim mode, so the keymap does not duplicate them.

| Keys | Action |
| --- | --- |
| `gd` / `gD` / `gy` / `gI` | Definition / declaration / type / implementation |
| `gA` or `grr` | Find all references |
| `K` / `g.` | Hover / code actions |
| `[d` / `]d` | Previous / next diagnostic |
| `[c` / `]c` | Previous / next Git change |
| `[m` / `]m` | Previous / next method |
| `[b` / `]b` | Previous / next tab |
| `[Space` / `]Space` | Add blank line above / below without entering Insert |
| `[e` / `]e` | Move line or selected lines up / down |
| `gl` / `gL` | Add next / previous matching selection |
| `g>` / `g<` | Skip to next / previous matching selection |
| `ga` | Select all matches; then `c` to edit together |
| `gcc` / Visual `gc` | Toggle line / selection comments |
| `ysiw)` / `cs"'` / `ds"` | Surround word / change quotes / remove quotes |
| `vif` / `vaf` | Select inside / around function |
| `via` / `vaa` | Select inside / around argument |
| `Ctrl-o` / `Ctrl-i` | Jump back / forward |
| `Ctrl-w h/j/k/l` | Move between panes |
| ``Ctrl-` `` | Toggle terminal panel, including from the terminal |
| `:w` / `:q` / `:noh` | Save / close / clear search highlights |

Press `Escape` to cancel a selection or pending command. If a shortcut behaves
unexpectedly, run `dev: open key context view` from the command palette to inspect
which context is active.

## References

The approach combines the existing Vim/Neovim habits in this repository with a
small leader layer, as seen in [Zed's community tips](https://github.com/zed-industries/zed/discussions/39680)
and [zed-titus](https://github.com/ChrisTitusTech/zed-titus). Actions and contexts
follow the [official Vim guide](https://zed.dev/docs/vim) and
[keybinding guide](https://zed.dev/docs/key-bindings); selection shortcuts take
inspiration from the [Helix keymap](https://docs.helix-editor.com/keymap.html).

Version-specific references: [Zed default settings](https://github.com/zed-industries/zed/blob/df181c6f58d02677b385fa947d6bfde6d3530078/assets/settings/default.json)
and [Vim/Helix keymap](https://github.com/zed-industries/zed/blob/df181c6f58d02677b385fa947d6bfde6d3530078/assets/keymaps/vim.json).
