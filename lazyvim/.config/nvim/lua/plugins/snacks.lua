-- disable the LazyVim (snacks) file explorer in favour of yazi.nvim
---@type LazySpec
return {
  "folke/snacks.nvim",
  opts = {
    explorer = { replace_netrw = false },
    indent = { animate = { enabled = false } },
    scroll = { enabled = false },
  },
  keys = {
    { "<leader>e", false },
    { "<leader>E", false },
    { "<leader>fe", false },
    { "<leader>fE", false },
  },
}
