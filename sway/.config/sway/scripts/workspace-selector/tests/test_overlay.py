"""Check the actual pixels drawn before and after placement without a display."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cairo
from core import HEIGHT, WIDTH, Target
from overlay import Dialog


class OverlayTests(unittest.TestCase):
    def test_first_frame_stays_transparent_until_positioned(self):
        dialog = Dialog.__new__(Dialog)
        dialog.ready = False
        dialog.target = Target(1, "Window", "1", 1, {}, {})
        dialog.counts = {i: 0 for i in range(1, 10)}
        dialog.hover = None
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, WIDTH, HEIGHT)
        ctx = cairo.Context(surface)
        # Even a previously painted background must be cleared before mapping.
        ctx.set_source_rgb(1, 1, 1)
        ctx.paint()
        dialog.draw(None, ctx)
        surface.flush()
        self.assertFalse(any(surface.get_data()))

        dialog.ready = True
        dialog.draw(None, ctx)
        surface.flush()
        self.assertTrue(any(surface.get_data()))


if __name__ == "__main__":
    unittest.main()
