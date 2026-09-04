" Open Yazi in vim-floaterm and edit the files selected with Enter.
if exists('g:loaded_simple_yazi')
  finish
endif
let g:loaded_simple_yazi = 1

function! s:InitialPath(argument) abort
  let l:path = empty(a:argument) ? expand('%:p') : expand(a:argument)
  if empty(l:path) || l:path =~# '^[[:alnum:].+-]\+://'
    return getcwd()
  endif
  return fnamemodify(l:path, ':p')
endfunction

function! s:ShellEscape(value) abort
  " Prevent :execute from expanding a literal bang as the previous command.
  return escape(shellescape(a:value), '!')
endfunction

function! s:Open(argument) abort
  if !executable('yazi')
    echohl ErrorMsg
    echom 'Yazi executable not found in PATH'
    echohl None
    return
  endif

  let l:path = s:ShellEscape(s:InitialPath(a:argument))
  execute 'FloatermNew --name=yazi --width=0.8 --height=0.8 --autoclose=always --opener=edit yazi ' . l:path
endfunction

command! -nargs=? -complete=file Yazi call <SID>Open(<q-args>)
nnoremap <silent> <leader>e <Cmd>Yazi<CR>
