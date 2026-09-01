-- Balanced desktop settings for Swayimg 5.5.
-- Swayimg otherwise defaults to a borderless overlay when it detects Sway.
swayimg.mode = "viewer"
swayimg.antialiasing = true
swayimg.fullscreen = false
swayimg.decoration = true
swayimg.overlay = false
swayimg.exif_orientation = true

-- Use natural file ordering and monitor opened directories for changes.
swayimg.imagelist.order = "numeric"
swayimg.imagelist.recursive = false
swayimg.imagelist.fsmon = true

-- Keep decoded-image and thumbnail caches bounded. Full images use much more
-- memory than thumbnails, so the official conservative limits are appropriate.
swayimg.viewer.default_scale = "optimal"
swayimg.viewer.autocenter = true
swayimg.viewer.preload = 1
swayimg.viewer.history = 1
swayimg.gallery.cache = 100
swayimg.gallery.preload = false
swayimg.gallery.embedded_thumb = true
swayimg.gallery.pstore = false -- Avoid an unbounded persistent thumbnail cache.

-- Load the other images in the selected image's directory.
swayimg.imagelist.adjacent = true

-- Require confirmation before Escape closes swayimg.
local close_pending = false

local function request_close()
  if close_pending then
    close_pending = false
    swayimg.text.status = "Close cancelled"
    return
  end

  close_pending = true
  swayimg.text.status = "Close swayimg? Press y to confirm, Esc to cancel"

  swayimg.defer(3, function()
    close_pending = false
  end)
end

local function confirm_close()
  if close_pending then
    swayimg.exit()
  end
end

for _, mode in ipairs({
  swayimg.viewer,
  swayimg.slideshow,
  swayimg.gallery,
}) do
  mode.on_key("Escape", request_close)
  mode.on_key("y", confirm_close)
end

-- Set the selected image as wallpaper, preferring Noctalia when it is running.
local LOG_TAG = "swayimg-wallpaper"
local WALLPAPER_KEY = "w"
local SWAY_MODE = "fill"

local function shell_quote(value)
  return "'" .. value:gsub("'", [['"'"']]) .. "'"
end

local function command_succeeded(ok, _, exit_code)
  return ok == true or ok == 0 or exit_code == 0
end

local function run(command)
  return command_succeeded(os.execute(command .. " >/dev/null 2>&1"))
end

local function log(message)
  os.execute("logger --tag " .. LOG_TAG .. " -- " .. shell_quote(message))
end

local function noctalia_is_running()
  return run("noctalia msg status")
end

local function sway_command_quote(value)
  return '"' .. value:gsub("\\", "\\\\"):gsub('"', '\\"') .. '"'
end

local function set_with_noctalia(path)
  return run("noctalia msg wallpaper-set " .. shell_quote(path))
end

local function set_with_sway(path)
  local sway_command =
    "output * bg " .. sway_command_quote(path) .. " " .. SWAY_MODE
  return run("swaymsg -- " .. shell_quote(sway_command))
end

local function set_wallpaper(mode)
  local image = mode.get_image()
  if not image then
    log("Cannot set wallpaper: swayimg has no selected image")
    return
  end

  if noctalia_is_running() then
    if set_with_noctalia(image.path) then
      log("Set wallpaper with Noctalia: " .. image.path)
      return
    end

    log("Noctalia wallpaper change failed; trying swaymsg: " .. image.path)
  else
    log("Noctalia is not running; using swaymsg: " .. image.path)
  end

  if set_with_sway(image.path) then
    log("Set wallpaper with swaymsg: " .. image.path)
  else
    log("Failed to set wallpaper with swaymsg: " .. image.path)
  end
end

swayimg.viewer.on_key(WALLPAPER_KEY, function()
  set_wallpaper(swayimg.viewer)
end)

swayimg.gallery.on_key(WALLPAPER_KEY, function()
  set_wallpaper(swayimg.gallery)
end)

swayimg.slideshow.on_key(WALLPAPER_KEY, function()
  set_wallpaper(swayimg.slideshow)
end)

local PAN_STEP = 10

local function bind_vim_navigation(mode)
  mode.on_key("h", function()
    local position = mode.get_position()
    mode.set_abs_position(position.x + PAN_STEP, position.y)
  end)
  mode.on_key("j", function()
    mode.open("next")
  end)
  mode.on_key("k", function()
    mode.open("prev")
  end)
  mode.on_key("l", function()
    local position = mode.get_position()
    mode.set_abs_position(position.x - PAN_STEP, position.y)
  end)
end

bind_vim_navigation(swayimg.viewer)
bind_vim_navigation(swayimg.slideshow)

swayimg.gallery.on_key("h", function()
  swayimg.gallery.select("left")
end)
swayimg.gallery.on_key("j", function()
  swayimg.gallery.select("pgdown")
end)
swayimg.gallery.on_key("k", function()
  swayimg.gallery.select("pgup")
end)
swayimg.gallery.on_key("l", function()
  swayimg.gallery.select("right")
end)
