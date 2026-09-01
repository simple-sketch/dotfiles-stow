-- Keymaps are automatically loaded on the VeryLazy event
-- Default keymaps that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/keymaps.lua
-- Add any additional keymaps here

-- Replace the word under the cursor throughout the file. `*` populates the
-- search register, `N` returns to the original occurrence, and the cursor is
-- left in the replacement field. Confirm each match with y/n/a/q.
vim.keymap.set("n", "<leader>r", "*N:%s///gc<Left><Left><Left>", { desc = "Replace word in file" })

local function replace_visual_selection()
  local saved_register = vim.fn.getreg("z")
  local saved_register_type = vim.fn.getregtype("z")
  vim.cmd([[normal! gv"zy]])
  local selection = vim.fn.getreg("z"):gsub("\n$", "")
  vim.fn.setreg("z", saved_register, saved_register_type)
  vim.fn.setreg("/", "\\V" .. vim.fn.escape(selection, "\\"))
  local command = vim.api.nvim_replace_termcodes(":%s///gc<Left><Left><Left>", true, false, true)
  vim.api.nvim_feedkeys(command, "n", false)
end

vim.keymap.set("x", "<leader>r", replace_visual_selection, { desc = "Replace selection in file" })

-- Keep format-on-save and animation disabled rather than offering toggles that
-- can accidentally turn them back on. Manual formatting remains <leader>cf.
for _, key in ipairs({ "<leader>uf", "<leader>uF", "<leader>ua", "<leader>uS" }) do
  pcall(vim.keymap.del, "n", key)
end
