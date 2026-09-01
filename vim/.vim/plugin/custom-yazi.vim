" Minimal Yazi integration for terminal Vim.
if exists('g:loaded_simple_yazi')
  finish
endif
let g:loaded_simple_yazi = 1

let s:running = 0

function! s:InitialPath(argument) abort
  let l:path = empty(a:argument) ? expand('%:p') : expand(a:argument)
  if empty(l:path) || l:path =~# '^[[:alnum:].+-]\+://'
    return getcwd()
  endif
  return fnamemodify(l:path, ':p')
endfunction

function! s:OpenSelectedFiles(chooser) abort
  if !filereadable(a:chooser)
    return
  endif

  let l:files = filter(readfile(a:chooser), '!empty(v:val)')
  if len(l:files) == 1
    execute 'edit ' . fnameescape(l:files[0])
  elseif len(l:files) > 1
    execute 'args ' . join(map(l:files, 'fnameescape(v:val)'), ' ')
  endif
endfunction

function! s:ShellEscape(value) abort
  " Prevent :! from expanding a literal bang as the previous shell command.
  return escape(shellescape(a:value), '!')
endfunction

function! s:Open(argument) abort
  if !executable('yazi')
    echohl ErrorMsg
    echom 'Yazi executable not found in PATH'
    echohl None
    return
  endif
  if s:running
    return
  endif

  let l:chooser = tempname()
  let l:had_nvim_cwd = exists('$NVIM_CWD')
  let l:previous_nvim_cwd = l:had_nvim_cwd ? $NVIM_CWD : ''
  let l:command = join(map([
        \ exepath('yazi'),
        \ s:InitialPath(a:argument),
        \ '--chooser-file',
        \ l:chooser,
        \ ], 's:ShellEscape(v:val)'), ' ')

  let s:running = 1
  let $NVIM_CWD = getcwd()
  try
    " Run on Foot's real TTY. A nested terminal popup can leave stale cells
    " after Sway resizes or moves the window.
    execute 'silent !' . l:command
    let l:status = v:shell_error
    silent! checktime
    if l:status == 0
      call s:OpenSelectedFiles(l:chooser)
    endif
  finally
    if l:had_nvim_cwd
      let $NVIM_CWD = l:previous_nvim_cwd
    else
      unlet! $NVIM_CWD
    endif
    let s:running = 0
    call delete(l:chooser)
    " :silent suppresses Vim's automatic repaint after an external command.
    redraw!
  endtry
endfunction

command! -nargs=? -complete=file Yazi call <SID>Open(<q-args>)
nnoremap <silent> <leader>e <Cmd>Yazi<CR>

" Remove the resize hook left by the previous popup-based implementation when
" this file is reloaded in an existing Vim session.
augroup SimpleYazi
  autocmd!
augroup END
