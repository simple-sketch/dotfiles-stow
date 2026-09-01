
return {
  {
    "Saghen/blink.cmp",
    opts = {
      completion = {
        menu = {
          -- Turn off the automatic menu popup while typing
          auto_show = false,
        },
        ghost_text = {
          -- Optional: Turn off inline ghost suggestions
          enabled = false,
        },
      },
      cmdline = {
        sources = { "buffer", "cmdline" },
      },
      sources = {
        providers = {
          buffer = {
            opts = {
              -- Offer words from the current buffer in :substitute commands.
              enable_in_ex_commands = true,
            },
          },
        },
      },
    },
  },
}
