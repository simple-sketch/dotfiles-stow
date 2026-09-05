vim9script noclear

# Open Yazi in vim-floaterm and edit the files selected with Enter.
if exists('g:loaded_simple_yazi')
  finish
endif

# Fall back to netrw when the external Yazi executable is unavailable.
if !executable('yazi')
  nnoremap <silent> <leader>e <Cmd>Explore<CR>
  finish
endif

g:loaded_simple_yazi = 1

def Error(message: string)
  echohl ErrorMsg
  echomsg message
  echohl None
enddef

def InitialPath(argument: string): string
  # :Yazi's file argument is already expanded by Vim; argv() is literal.
  final path = empty(argument) ? expand('%:p') : argument
  if empty(path) || path =~# '^[[:alnum:].+-]\+://'
    return getcwd()
  endif
  return fnamemodify(path, ':p')
enddef

def Open(argument: string)
  if !executable('yazi')
    Error('Yazi executable not found in PATH')
    return
  endif
  # The API does not trigger vim-plug's lazy :FloatermNew command stub.
  if exists('*plug#load')
    plug#load('vim-floaterm')
  endif
  if !get(g:, 'loaded_floaterm', false)
    Error('vim-floaterm is unavailable')
    return
  endif

  # Pass the path through the job's environment, not Ex or shell source.
  # This preserves %, #, !, quotes and whitespace through Floaterm's wrapper.
  floaterm#new(false, 'yazi "$VIM_YAZI_PATH"', {
    env: {VIM_YAZI_PATH: InitialPath(argument)},
  }, {
    name: 'yazi',
    width: 0.8,
    height: 0.8,
    autoclose: 'always',
    opener: 'edit',
  })
enddef

command! -nargs=? -complete=file Yazi Open(<q-args>)
nnoremap <silent> <leader>e <Cmd>Yazi<CR>

# Prefer Yazi for `vim DIRECTORY`; netrw remains the fallback underneath.
def OpenDirectoryArgument()
  if argc() == 1 && isdirectory(argv(0))
    Open(argv(0))
  endif
enddef

augroup YaziDirectoryStartup
  autocmd!
  autocmd VimEnter * OpenDirectoryArgument()
augroup END

defcompile
