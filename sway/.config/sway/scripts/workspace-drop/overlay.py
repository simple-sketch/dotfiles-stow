"""A normal floating GTK surface: Sway bindings, not Wayland, report the drop.

A layer-shell surface cannot be used here: Sway excludes it from mouse bindings,
and wlroots suppresses a release whose press was consumed by the opening binding.
"""

import math
import cairo
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Gdk, Gtk, Pango, PangoCairo

from core import WIDTH, HEIGHT, cell_rect, hit_test


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


def text(ctx, value, x, y, size=11, fg="#c9cddd", width=None, bold=False, center=False):
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
        self.window.set_role("workspace-drop")
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
        self.window.connect("button-press-event", lambda *_: self.cancel("new click") or True)
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
        ctx.set_operator(cairo.OPERATOR_OVER)
        rounded(ctx, 1, 1, WIDTH - 2, HEIGHT - 2, 14)
        color(ctx, "#1b1e28")
        ctx.fill_preserve()
        color(ctx, "#44495e")
        ctx.set_line_width(1.5)
        ctx.stroke()
        text(ctx, "Move window", 18, 14, 17, "#f0eff9", bold=True)
        text(ctx, self.target.title.replace("\n", " "), 18, 42, 12, "#a5acc2", width=WIDTH - 36)
        for number in range(1, 10):
            x, y, w, h = cell_rect(number)
            active = number == self.hover
            current = number == self.target.number
            rounded(ctx, x, y, w, h, 9)
            color(ctx, "#b9a5f7" if active else "#2a2f3e" if current else "#242836")
            ctx.fill_preserve()
            color(ctx, "#d8caff" if active else "#8b7db8" if current else "#383e50")
            ctx.set_line_width(2 if active else 1)
            ctx.stroke()
            text(ctx, str(number), x, y + 8, 23, "#20192f" if active else "#f0eff9", width=w,
                 bold=True, center=True)
            count = self.counts[number]
            label = "current" if current else "empty" if not count else f"{count} window{'s' if count != 1 else ''}"
            text(ctx, label, x, y + 43, 10, "#423451" if active else "#a5acc2", width=w, center=True)
        hint = f"Release → workspace {self.hover}" if self.hover else "Hold left button · point at a number"
        text(ctx, hint, 18, 318, 12, "#d5c5ff", width=WIDTH - 36, center=True)
        text(ctx, "Esc / right-click to cancel · stay here", 18, 340, 10, "#8992aa",
             width=WIDTH - 36, center=True)
        return True
