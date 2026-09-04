vim9script noclear

# Open Yazi in vim-floaterm and edit the files selected with Enter.
if exists('g:loaded_simple_yazi')
  finish
endif
g:loaded_simple_yazi = 1

def Error(message: string)
  echohl ErrorMsg
  echomsg message
  echohl None
enddef

def InitialPath(argument: string): string
  var path = empty(argument) ? expand('%:p') : expand(argument)
  if empty(path) || path =~# '^[[:alnum:].+-]\+://'
    return getcwd()
  endif
  return fnamemodify(path, ':p')
enddef

def ShellEscape(value: string): string
  # Prevent :execute from expanding a literal bang as the previous command.
  return escape(shellescape(value), '!')
enddef

def Open(argument: string)
  if !executable('yazi')
    Error('Yazi executable not found in PATH')
    return
  endif
  if exists(':FloatermNew') != 2
    Error('vim-floaterm is unavailable')
    return
  endif

  final path = ShellEscape(InitialPath(argument))
  execute 'FloatermNew --name=yazi --width=0.8 --height=0.8 --autoclose=always --opener=edit yazi ' .. path
enddef

command! -nargs=? -complete=file Yazi Open(<q-args>)
nnoremap <silent> <leader>e <Cmd>Yazi<CR>

defcompile
