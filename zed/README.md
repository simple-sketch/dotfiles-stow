# Zed: Vim keys in editors and lists

This configuration uses Zed's Vim mode in editors and list navigation in panels.
It uses a small Space leader in editors, empty panes, and non-editing panel lists.
It also uses some Helix selection keys. One key set covers common tasks without a new modal system.
The theme and icon theme need their named extensions.
Panel contexts and built-in keys were checked against Zed 1.25.3
(`8dd255c3eafb5231056fe4e6f601cedd011f1c93`).

## Install

From the repository root:

```sh
stow --simulate --verbose --target="$HOME" zed
stow --target="$HOME" zed
```

This links `settings.json`, `keymap.json`, and `tasks.json` into `~/.config/zed/`. Stow reports a
conflict if an existing file would be replaced; move that file to a backup before
retrying. Zed reloads these files automatically. To unlink the package:

```sh
stow --delete --target="$HOME" zed
```

## Editing defaults

- Vim Normal mode on startup; relative line numbers in Normal mode and absolute
  numbers in Insert mode. Yanks use the system clipboard and briefly highlight.
  Deletes and changes preserve the system clipboard; use `"+p` to paste from it
  explicitly after a deletion.
- Space is the leader. Pause for 500 ms to see the available key continuations.
- Smart-case search: lowercase queries ignore case; uppercase makes it exact.
- Manual save and formatting. Use `:w`, `Ctrl-s`, or `Space w w` to save, and
  `Space c f` to format on demand. Formatting on save is disabled; project
  settings can override user defaults.
- Automatic indentation, indentation on paste, LSP formatting on supported
  trigger characters, and whitespace cleanup use Zed's built-in defaults.
  Java and Python inherit four-space indentation; JS/TS/TSX override it to two.
- Java keeps JDTLS formatting. It requires the Java extension and a working JDK;
  see [Zed's Java documentation](https://zed.dev/docs/languages/java).
- JavaScript, TypeScript, and TSX use Zed's default Prettier integration and honor
  project Prettier settings. JSX is covered by JavaScript settings; see
  [Zed's JavaScript documentation](https://zed.dev/docs/languages/javascript) and
  [TypeScript documentation](https://zed.dev/docs/languages/typescript).
- Python uses Zed's default Ruff formatter; see
  [Zed's Python documentation](https://zed.dev/docs/languages/python).
- macOS Classic Dark theme, Material Icon Theme, animated cursor, no minimap or
  inline blame, and inlay hints off until requested. Install both named theme
  extensions. Inline diagnostic text is hidden. Diagnostic navigation remains.
- Files wrap at the preferred line length of 120 when bounded wrapping applies.
  Other indentation and language tools use Zed/project defaults and `.editorconfig`.

## Custom shortcuts

Keys separated by spaces are pressed in sequence. Uppercase letters mean Shift.
Leader shortcuts work in Normal and Visual mode in full editors, except Git file
diff and hunk restore, which are Normal-mode only.

Split navigation with `Ctrl-w h/j/k/l` works across editor panes and non-editor dock views.
Space leader keys also work in the project, outline, and Git lists.
Insert mode, search fields, and picker input keep their usual keys.
Use `Ctrl-p` / `Ctrl-n` to move up / down in picker results while you type.

`Ctrl-Alt-1` returns focus to the active center pane from panels, including the
terminal, and is available in every Vim mode. It avoids `Ctrl-1`, which Zed uses
in the Git panel, settings, welcome screen, and image viewer.

| Keys | Action |
| --- | --- |
| `Space f f` | Find file |
| `Space f g` | Search project |
| `Space f b` | Pick an open buffer in the current pane |
| `Space b b` | Pick an open buffer across panes in the editor |
| `Space f l` | Search in the current buffer |
| `Space f s` / `Space f S` | Find symbol in file / project |
| `Space f p` | Open recent project |
| `Space e` | Toggle project panel focus |
| `Space r` | Open text replacement, seeded from cursor/selection |
| `n` / `Shift-n` | Next / previous search match in Vim Normal mode |
| `Space c r` | Rename symbol through the language server |
| `Space c a` | Code actions |
| `Space c f` | Format |
| `Space x x` | Project diagnostics |
| `Space m p` | Toggle the current Markdown file’s preview/source |
| `Space g g` | Toggle Git panel focus |
| `Space g d` | Open file diff (Normal mode) |
| `Space g f` | Open Git file history |
| `Space g h p` | Preview/toggle selected Git hunks |
| `Space g h r` | Restore selected Git hunks (Normal mode; discards changes) |
| `Space t t` | Toggle terminal panel |
| `Space t r` / `Space t R` | Pick task / rerun last task |
| `Space w w` / `Space w W` | Save file / all files |
| `Ctrl-s` | Save the current file from any editor mode |
| `Space w v` / `Space w s` | Split right / below |
| `Ctrl-w h/j/k/l` | Focus pane or dock left / down / up / right |
| `Ctrl-Alt-1` | Focus the active center pane (all Vim modes and panels) |
| `Space b d` | Close active tab, with normal save prompts |
| `Space u i` | Toggle inlay hints |
| `Space u w` | Toggle line wrapping |
| `Space u z` | Toggle focused pane zoom |
| `Space ,` / `Space ?` | Open settings file / keymap editor |

### Navigation outside the editor

The project, outline, and Git lists use `j/k` to select entries. The project
and outline lists use `h/l` to collapse and expand entries. Git changes use
`h/l` for the same actions. Use `g g` / `G` to select the first / last entry
in the project, outline, and Git changes lists. Zed supplies most of these list keys.

Git history does not use these end-of-list keys. In the project, outline, and Git lists,
`Space f f` finds a file, `Space f g` searches the project,
and `Space f p` opens a recent project. `Space e` opens the project panel,
`Space g g` opens the Git panel, and `Space t t` opens the terminal panel.
These leader keys do not apply in text fields or terminal input.
The shared `Space f f` chord replaces the Project Panel's built-in `Space f` chord.

Use `Ctrl-w w` or `Ctrl-Alt-1` to return to the center pane from a dock.
Dock editors keep their text keys. Terminal `Ctrl-w` chords take precedence over shell and terminal-UI keys.

### Yazi-style project panel

When the Project Panel has focus, its file operations use familiar Yazi keys:

| Keys | Action |
| --- | --- |
| `j` / `k` | Move down / up |
| `h` / `l` | Collapse / expand directory |
| `Enter` / `o` | Open permanently / preview |
| `y` / `x` / `p` | Copy / cut / paste |
| `d` / `D` | Move to trash / permanently delete |
| `a` / `A` | Create file / directory |
| `r` / `.` | Rename / toggle hidden files |
| `Backspace` / `q` | Select parent / leave panel focus |

`A` is written as `Shift-A` in Zed's keymap syntax. Mark multiple entries with
`Shift-Up` / `Shift-Down`, which is the Project Panel's native equivalent of
Yazi's selection mode.

The Java run indicator uses `Run Java file: <filename>` from `tasks.json`. It saves
the active file and runs `java <file>` from that file's directory. This is intended
for standalone programs and avoids the Java extension's recursive compilation,
which can include unrelated files and the `~/.java` directory. It is also available
through `Space t r`. A JDK is required; use Java 25+ for `IO.println` and instance
`void main()` without preview flags.

For Maven or Gradle applications, define the appropriate build command in the
project's `.zed/tasks.json` with the `java-main` tag; project tasks take precedence
over this global standalone-file task. See [Zed's task documentation](https://zed.dev/docs/tasks#binding-runnable-tags-to-task-templates).

Other task commands use tasks supplied by the project or language support.
Language server actions require the appropriate language support and a running
server; install a language extension from Zed when the language is not bundled.

## Helix-inspired selection and identifier editing

| Keys | Action |
| --- | --- |
| `Space .` | Show jump labels at visible word starts; type a label to jump |
| `Alt-o` / `Alt-i` | Expand / shrink a syntax selection |
| `Alt-p` / `Alt-n` in Visual mode | Select previous / next syntax sibling |
| `Alt-s` in Visual mode | Split selection into a selection per line |
| `Alt-w` / `Alt-b` / `Alt-e` | Next subword start / previous start / next end |
| `S` in Visual mode, then a delimiter | Surround selection |
| `Shift-X` in Visual mode | Exchange the selected block with another selection |

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
| `Ctrl-w h/j/k/l` | Move between panes and docks |
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

Version-specific reference: [Zed Vim keymap](https://github.com/zed-industries/zed/blob/8dd255c3eafb5231056fe4e6f601cedd011f1c93/assets/keymaps/vim.json).
