---@type LazySpec
return {
  {
    "neovim/nvim-lspconfig",
    opts = {
      -- Keep hints hidden until they are toggled with <leader>uh.
      inlay_hints = { enabled = false },
    },
  },
}
