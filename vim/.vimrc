" Yazi replaces Vim's bundled netrw file browser.
let g:loaded_netrw = 1
let g:loaded_netrwPlugin = 1

source $VIMRUNTIME/defaults.vim

set nomodeline
set confirm

let mapleader = ' '
let maplocalleader = ' '

" Briefly show the region copied by a yank.
let g:hlyank_duration = 400

" Useful packages bundled with Vim 9.
packadd! comment
packadd! hlyank
packadd! matchit

" Bootstrap the minimalist vim-plug manager once.
let s:vim_dir = expand('~/.vim')
let s:plug_path = s:vim_dir . '/autoload/plug.vim'
let s:plug_url = 'https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim'

if !filereadable(s:plug_path) && executable('curl')
  call mkdir(fnamemodify(s:plug_path, ':h'), 'p', 0700)
  call system('curl -fsSLo ' . shellescape(s:plug_path) . ' ' . shellescape(s:plug_url))
  if v:shell_error
    call delete(s:plug_path)
  endif
endif

if filereadable(s:plug_path)
  call plug#begin(s:vim_dir . '/plugged')

  Plug 'dracula/vim', { 'as': 'dracula' }
  Plug 'editorconfig/editorconfig-vim'
  Plug 'tpope/vim-repeat'
  Plug 'tpope/vim-surround'
  Plug 'wellle/targets.vim'
  Plug 'justinmk/vim-sneak'
  Plug 'junegunn/fzf.vim'
  Plug 'jlanzarotta/bufexplorer'
  Plug 'airblade/vim-gitgutter'
  Plug 'mbbill/undotree', { 'on': 'UndotreeToggle' }
  Plug 'voldikss/vim-floaterm', { 'on': 'FloatermNew' }

  call plug#end()

  function! s:InstallMissingPlugins() abort
    if empty(filter(values(g:plugs), '!isdirectory(v:val.dir)'))
      return
    endif
    PlugInstall --sync
    " plug#end() loads newly installed plugins, but the colorscheme check below
    " has already run during startup, so apply it explicitly on the first run.
    if !empty(globpath(&runtimepath, 'colors/dracula.vim'))
      colorscheme dracula
    endif
  endfunction

  augroup PlugBootstrap
    autocmd!
    autocmd VimEnter * call <SID>InstallMissingPlugins()
  augroup END
else
  echohl WarningMsg
  echom 'vim-plug is unavailable; install curl and restart Vim'
  echohl None
endif

" Editing defaults. Project .editorconfig files override indentation as needed.
set autoindent
set expandtab
set shiftwidth=4
set softtabstop=-1
set tabstop=4
set hidden
set linebreak
set breakindent

" Search and command-line completion.
set ignorecase
set smartcase
set hlsearch
set wildmode=longest:full,full
set wildoptions=pum

if executable('rg')
  set grepprg=rg\ --vimgrep\ --smart-case
  set grepformat=%f:%l:%c:%m
endif

" Interface.
set number
set relativenumber
set signcolumn=yes
set laststatus=2
set statusline=%<%f\ %h%m%r%=%y\ %l:%c\ %P
set splitbelow
set splitright
set updatetime=250

if has('clipboard')
  set clipboard=unnamedplus
endif

if has('termguicolors')
  set termguicolors
endif

set background=dark
if !empty(globpath(&runtimepath, 'colors/dracula.vim'))
  colorscheme dracula
endif

" Keep recovery files out of project directories.
let s:swap_dir = s:vim_dir . '/swp'
let s:undo_dir = s:vim_dir . '/undo'
for s:dir in [s:swap_dir, s:undo_dir]
  if !isdirectory(s:dir)
    call mkdir(s:dir, 'p', 0700)
  endif
endfor
let &directory = s:swap_dir . '//'
let &undodir = s:undo_dir . '//'
set undofile

" Show absolute line numbers while inserting, relative numbers otherwise.
augroup NumberToggle
  autocmd!
  autocmd InsertEnter * setlocal norelativenumber
  autocmd InsertLeave * setlocal relativenumber
augroup END

" Search, project files, buffers, and undo history.
" Complete replacement text from unique words in the current buffer.
function! s:BufferWords(ArgLead, CmdLine, CursorPos) abort
  let l:prefix = tolower(a:ArgLead)
  let l:words = {}
  for l:line in getline(1, '$')
    for l:word in split(l:line, '\W\+')
      if !empty(l:word) && stridx(tolower(l:word), l:prefix) == 0
        let l:words[l:word] = 1
      endif
    endfor
  endfor
  return sort(keys(l:words))
endfunction

let s:buffer_word_completion = 'customlist,' . expand('<SID>') . 'BufferWords'

function! s:PromptReplacement() abort
  call inputsave()
  try
    let l:replacement = input('Replace with: ', '', s:buffer_word_completion)
  finally
    call inputrestore()
  endtry
  if empty(l:replacement)
    echo 'Replacement cancelled'
    return
  endif
  execute '%s//' . escape(l:replacement, '\/&~') . '/gc'
endfunction

" Replace the word under the cursor or selected text throughout the file.
function! s:ReplaceVisualSelection() abort
  let l:saved_register = getreg('z')
  let l:saved_register_type = getregtype('z')
  normal! gv"zy
  let l:selection = substitute(getreg('z'), "\n$", '', '')
  call setreg('z', l:saved_register, l:saved_register_type)
  let @/ = '\V' . escape(l:selection, '\')
  call s:PromptReplacement()
endfunction

" Open Lazygit at the current buffer's project root in a popup terminal.
function! s:OpenLazygit() abort
  if !executable('lazygit')
    echohl ErrorMsg
    echom 'lazygit is not installed or not on $PATH'
    echohl None
    return
  endif
  FloatermNew --name=lazygit --cwd=<buffer-root> --width=0.8 --height=0.8 --autoclose=smart lazygit
endfunction

nnoremap <leader>r *N:<C-u>call <SID>PromptReplacement()<CR>
xnoremap <silent> <leader>r :<C-u>call <SID>ReplaceVisualSelection()<CR>
nnoremap <silent> <leader>gg <Cmd>call <SID>OpenLazygit()<CR>
nnoremap <silent> <Esc><Esc> <Cmd>nohlsearch<CR>
nnoremap <silent> <F5> <Cmd>UndotreeToggle<CR>
nnoremap <silent> <leader>ff <Cmd>Files<CR>
nnoremap <silent> <leader>fg <Cmd>Rg<CR>
nnoremap <silent> <leader>fb <Cmd>Buffers<CR>

" Keep comment text objects on ic/ac; use ih/ah for GitGutter hunks.
omap ih <Plug>(GitGutterTextObjectInnerPending)
omap ah <Plug>(GitGutterTextObjectOuterPending)
xmap ih <Plug>(GitGutterTextObjectInnerVisual)
xmap ah <Plug>(GitGutterTextObjectOuterVisual)

" Move between splits without the extra Ctrl-W chord.
nnoremap <C-h> <C-w><C-h>
nnoremap <C-j> <C-w><C-j>
nnoremap <C-k> <C-w><C-k>
nnoremap <C-l> <C-w><C-l>
