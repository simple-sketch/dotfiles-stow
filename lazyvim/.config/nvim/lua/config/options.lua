-- Options are automatically loaded before lazy.nvim startup
-- Default options that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/options.lua
-- Add any additional options here

-- Keep editing quiet by default. Formatting remains available manually with
-- <leader>cf, but saving a file never formats it.
vim.g.autoformat = false

-- Disable every animation implemented through Snacks.
vim.g.snacks_animate = false

-- Diagnostic display is opt-in with <leader>ud.
vim.diagnostic.enable(false)
