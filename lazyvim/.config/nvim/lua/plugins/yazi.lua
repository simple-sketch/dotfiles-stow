---@type LazySpec
return {
  "mikavilpas/yazi.nvim",
  version = "*", -- use the latest stable version
  event = "VeryLazy",
  dependencies = {
    { "nvim-lua/plenary.nvim", lazy = true },
  },
  keys = {
    { "<leader>e", mode = { "n", "v" }, "<cmd>Yazi<cr>", desc = "Yazi (current file)" },
    { "<leader>E", "<cmd>Yazi cwd<cr>", desc = "Yazi (cwd)" },
    { "<leader>y", "<cmd>Yazi toggle<cr>", desc = "Yazi (resume last session)" },
  },
  ---@type YaziConfig | {}
  opts = {
    -- open yazi instead of netrw when a directory is opened
    open_for_directories = true,
    keymaps = {
      show_help = "<f1>",
    },
    integrations = {
      -- defaults are "telescope", which isn't installed in this config
      grep_in_directory = "snacks.picker",
      grep_in_selected_files = "snacks.picker",
    },
  },
  init = function()
    -- mark netrw as loaded so it's not loaded at all
    vim.g.loaded_netrwPlugin = 1
  end,
}
