vim9script

# Yazi replaces Vim's bundled netrw file browser.
g:loaded_netrw = 1
g:loaded_netrwPlugin = 1

set nomodeline
set confirm

# Vim enables Kitty's CSI-u key protocol in Kitty, Foot, and Ghostty. It can
# make a physical Escape fail to match an <Esc> mapping, so use legacy keys.
if &term =~# 'kitty\|foot\|ghostty'
  set keyprotocol=kitty:none,foot:none,ghostty:none
  &term = &term
endif

g:mapleader = ' '
g:maplocalleader = ' '

# Briefly show the region copied by a yank.
g:hlyank_duration = 400

# Useful packages bundled with Vim 9.
packadd! comment
packadd! editorconfig
packadd! hlyank
packadd! matchit

# Bootstrap the minimalist vim-plug manager once.
final vim_dir = expand('~/.vim')
final plug_path = vim_dir .. '/autoload/plug.vim'
const plug_url = 'https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim'

def Error(message: string)
  echohl ErrorMsg
  echomsg message
  echohl None
enddef

if !filereadable(plug_path) && executable('curl')
  mkdir(fnamemodify(plug_path, ':h'), 'p', 0o700)
  system('curl -fsSLo ' .. shellescape(plug_path) .. ' ' .. shellescape(plug_url))
  if v:shell_error != 0
    delete(plug_path)
  endif
endif

if filereadable(plug_path)
  plug#begin(vim_dir .. '/plugged')

  Plug 'joshdick/onedark.vim'
  Plug 'tpope/vim-repeat'
  Plug 'tpope/vim-surround'
  Plug 'wellle/targets.vim'
  Plug 'justinmk/vim-sneak'
  Plug 'junegunn/fzf.vim'
  Plug 'airblade/vim-gitgutter'
  Plug 'mbbill/undotree', { 'on': 'UndotreeToggle' }
  Plug 'voldikss/vim-floaterm', { 'on': 'FloatermNew' }

  plug#end()

  def InstallMissingPlugins()
    for plugin in values(g:plugs)
      if !isdirectory(get(plugin, 'dir', ''))
        execute 'PlugInstall --sync'
        # plug#end() loads newly installed plugins, but the colorscheme check
        # below has already run during startup, so apply it on the first run.
        if !empty(globpath(&runtimepath, 'colors/onedark.vim'))
          colorscheme onedark
        endif
        return
      endif
    endfor
  enddef

  augroup PlugBootstrap
    autocmd!
    autocmd VimEnter * InstallMissingPlugins()
  augroup END
else
  Error('vim-plug is unavailable; install curl and restart Vim')
endif

# vim-plug configures filetypes itself; load the remaining Vim defaults after
# it so that filetype detection is not needlessly rebuilt during startup.
source $VIMRUNTIME/defaults.vim

# Editing defaults. Project .editorconfig files override indentation as needed.
set autoindent
set expandtab
set shiftwidth=4
set softtabstop=-1
set tabstop=4
set hidden
set linebreak
set breakindent
set smoothscroll

# Search and command-line completion.
set ignorecase
set smartcase
set hlsearch
set wildmode=longest:full,full
set wildoptions=pum

if executable('rg')
  set grepprg=rg\ --vimgrep\ --smart-case
  set grepformat=%f:%l:%c:%m
endif

# Interface.
set number
set relativenumber
set signcolumn=yes
set laststatus=2
set statusline=%<%f\ %h%m%r%=%y\ %l:%c\ %P
set splitbelow
set splitright
set updatetime=250

if has('unnamedplus')
  set clipboard=unnamedplus
endif

if has('termguicolors')
  set termguicolors
endif

set background=dark
if !empty(globpath(&runtimepath, 'colors/onedark.vim'))
  colorscheme onedark
endif

# Keep recovery files out of project directories.
final swap_dir = vim_dir .. '/swp'
final undo_dir = vim_dir .. '/undo'
for directory in [swap_dir, undo_dir]
  if !isdirectory(directory)
    mkdir(directory, 'p', 0o700)
  endif
endfor
&directory = swap_dir .. '//'
&undodir = undo_dir .. '//'
set undofile

# Show absolute line numbers while inserting, relative numbers otherwise.
augroup NumberToggle
  autocmd!
  autocmd InsertEnter * setlocal norelativenumber
  autocmd InsertLeave * setlocal relativenumber
augroup END

# Put a literal Visual selection in the search register without changing any
# registers. The mapping below then opens Vim's built-in :substitute command.
def SetVisualSearch()
  execute "normal! \<Esc>"
  final selected_lines = getregion(getpos("'<"), getpos("'>"), {
    type: visualmode(),
    exclusive: &selection ==# 'exclusive',
  })
  if empty(selected_lines)
    return
  endif
  final escaped_lines = mapnew(selected_lines, (_, line) => escape(line, '\'))
  @/ = '\V' .. join(escaped_lines, '\n')
enddef

# Open Lazygit at the current buffer's project root in a popup terminal.
def OpenLazygit()
  if !executable('lazygit')
    Error('lazygit is not installed or not on $PATH')
    return
  endif
  if exists(':FloatermNew') != 2
    Error('vim-floaterm is unavailable')
    return
  endif
  execute 'FloatermNew --name=lazygit --cwd=<buffer-root> --width=0.8 --height=0.8 --autoclose=smart lazygit'
enddef

# Rename matches in this buffer with :substitute's built-in confirmation UI.
# Type the replacement, press Enter, then use y/n/a/q for each occurrence.
nnoremap <leader>r *N:%s///gc<Left><Left><Left>
xnoremap <leader>r <ScriptCmd>SetVisualSearch()<CR>:%s///gc<Left><Left><Left>
nnoremap <leader>gg <ScriptCmd>OpenLazygit()<CR>
nnoremap <silent> <Esc><Esc> <Cmd>nohlsearch<CR>
nnoremap <silent> <F5> <Cmd>UndotreeToggle<CR>
nnoremap <silent> <leader>ff <Cmd>Files<CR>
nnoremap <silent> <leader>fg <Cmd>Rg<CR>
nnoremap <silent> <leader>fb <Cmd>Buffers<CR>

# Vim otherwise sends Ctrl-Alt-X to terminal jobs as U+0098, which fzf ignores.
tnoremap <silent> <C-M-x> <Esc><C-x>

# Keep comment text objects on ic/ac; use ih/ah for GitGutter hunks.
omap ih <Plug>(GitGutterTextObjectInnerPending)
omap ah <Plug>(GitGutterTextObjectOuterPending)
xmap ih <Plug>(GitGutterTextObjectInnerVisual)
xmap ah <Plug>(GitGutterTextObjectOuterVisual)

# Move between splits without the extra Ctrl-W chord.
nnoremap <C-h> <C-w><C-h>
nnoremap <C-j> <C-w><C-j>
nnoremap <C-k> <C-w><C-k>
nnoremap <C-l> <C-w><C-l>

defcompile
