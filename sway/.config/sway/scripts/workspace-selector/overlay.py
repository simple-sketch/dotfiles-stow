"""A floating GTK selector: Sway reports clicks and GTK tracks the hovered tile."""

import math
import cairo
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Gdk, Gtk, Pango, PangoCairo

from core import WIDTH, HEIGHT, cell_rect, hit_test


# Nord dark: polar-night surfaces, snow-storm text, and frost accents.
BACKGROUND = "#2e3440"
SURFACE = "#3b4252"
SURFACE_CURRENT = "#434c5e"
OUTLINE = "#4c566a"
PRIMARY = "#88c0d0"
PRIMARY_OUTLINE = "#8fbcbb"
CURRENT_OUTLINE = "#81a1c1"
ON_PRIMARY = "#2e3440"
TEXT = "#eceff4"
TEXT_SECONDARY = "#d8dee9"
TEXT_MUTED = "#a5afc2"


def color(ctx, value):
    value = value.lstrip("#")
    ctx.set_source_rgb(*(int(value[i:i + 2], 16) / 255 for i in (0, 2, 4)))


def rounded(ctx, x, y, w, h, radius):
    ctx.new_sub_path()
    for cx, cy, start in ((x + w - radius, y + radius, -90),
                          (x + w - radius, y + h - radius, 0),
                          (x + radius, y + h - radius, 90),
                          (x + radius, y + radius, 180)):
        ctx.arc(cx, cy, radius, math.radians(start), math.radians(start + 90))
    ctx.close_path()


def text(ctx, value, x, y, size=11, fg=TEXT_SECONDARY, width=None, bold=False, center=False):
    layout = PangoCairo.create_layout(ctx)
    font = Pango.FontDescription()
    font.set_family("Sans")
    font.set_absolute_size(size * Pango.SCALE)
    if bold:
        font.set_weight(Pango.Weight.BOLD)
    layout.set_font_description(font)
    layout.set_text(value, -1)  # Titles are plain text, never markup.
    if width is not None:
        layout.set_width(int(width * Pango.SCALE))
        layout.set_ellipsize(Pango.EllipsizeMode.END)
        if center:
            layout.set_alignment(Pango.Alignment.CENTER)
    color(ctx, fg)
    ctx.move_to(x, y)
    PangoCairo.show_layout(ctx, layout)


class Dialog:
    def __init__(self, target, window_counts, cancel):
        self.target = target
        self.counts = window_counts
        self.hover = None
        self.ready = False
        self.cancel = cancel
        self.window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        self.window.set_title("Move window to workspace")
        self.window.set_role("workspace-selector")
        self.window.set_decorated(False)
        self.window.set_resizable(False)
        self.window.set_default_size(WIDTH, HEIGHT)
        self.window.set_app_paintable(True)
        visual = self.window.get_screen().get_rgba_visual()
        if visual:
            self.window.set_visual(visual)
        self.area = Gtk.DrawingArea()
        self.area.set_size_request(WIDTH, HEIGHT)
        self.window.add(self.area)
        self.area.connect("draw", self.draw)
        self.window.add_events(Gdk.EventMask.POINTER_MOTION_MASK | Gdk.EventMask.ENTER_NOTIFY_MASK |
                               Gdk.EventMask.LEAVE_NOTIFY_MASK | Gdk.EventMask.BUTTON_PRESS_MASK)
        self.window.connect("motion-notify-event", self.motion)
        self.window.connect("enter-notify-event", self.motion)
        self.window.connect("leave-notify-event", self.leave)
        self.window.connect("button-press-event", self.click)
        self.window.connect("delete-event", lambda *_: self.cancel("dialog closed") or True)
        self.window.connect("key-press-event", self.key)
        self.window.show_all()

    def positioned(self):
        self.ready = True
        self.hover = None
        self.area.queue_draw()

    def motion(self, _widget, event):
        if self.ready:
            hover = hit_test(event.x, event.y)
            if hover != self.hover:
                self.hover = hover
                self.area.queue_draw()
        return True

    def click(self, widget, event):
        if event.button == 3:
            self.cancel("right click")
        elif event.button == 1:
            self.motion(widget, event)
        return True

    def leave(self, *_):
        self.hover = None
        self.area.queue_draw()
        return True

    def key(self, _widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.cancel("escape")
        return True

    def destroy(self):
        self.ready = False
        self.window.destroy()

    def draw(self, _widget, ctx):
        ctx.set_operator(cairo.OPERATOR_SOURCE)
        ctx.set_source_rgba(0, 0, 0, 0)
        ctx.paint()
        # Map a transparent surface so Sway can place it before the first visible
        # frame. Drawing immediately would flash at Sway's initial center position.
        if not self.ready:
            return True
        ctx.set_operator(cairo.OPERATOR_OVER)
        rounded(ctx, 1, 1, WIDTH - 2, HEIGHT - 2, 14)
        color(ctx, BACKGROUND)
        ctx.fill_preserve()
        color(ctx, OUTLINE)
        ctx.set_line_width(1.5)
        ctx.stroke()
        text(ctx, "Move window", 18, 14, 17, TEXT, bold=True)
        text(ctx, self.target.title.replace("\n", " "), 18, 42, 12, TEXT_SECONDARY, width=WIDTH - 36)
        for number in range(1, 10):
            x, y, w, h = cell_rect(number)
            active = number == self.hover
            current = number == self.target.number
            rounded(ctx, x, y, w, h, 9)
            color(ctx, PRIMARY if active else SURFACE_CURRENT if current else SURFACE)
            ctx.fill_preserve()
            color(ctx, PRIMARY_OUTLINE if active else CURRENT_OUTLINE if current else OUTLINE)
            ctx.set_line_width(2 if active else 1)
            ctx.stroke()
            text(ctx, str(number), x, y + 8, 23, ON_PRIMARY if active else TEXT, width=w,
                 bold=True, center=True)
            count = self.counts[number]
            label = "current" if current else "empty" if not count else f"{count} window{'s' if count != 1 else ''}"
            text(ctx, label, x, y + 43, 10, ON_PRIMARY if active else TEXT_SECONDARY, width=w, center=True)
        hint = f"Click → workspace {self.hover}" if self.hover else "Click a workspace number"
        text(ctx, hint, 18, 318, 12, PRIMARY, width=WIDTH - 36, center=True)
        text(ctx, "Esc / right-click to cancel · stay here", 18, 340, 10, TEXT_MUTED,
             width=WIDTH - 36, center=True)
        return True
