import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import (APP_ID, Decoder, HEADER, HEIGHT, MAX_PAYLOAD, Target, WIDTH,
                  cell_rect, counts, find_target, hit_test, move_command, packet)


def tree():
    return {"type": "root", "nodes": [
        {"type": "output", "name": "DP-1", "nodes": [
            {"type": "workspace", "name": "3: work", "num": 3,
             "rect": {"x": -1280, "y": 30, "width": 1280, "height": 690},
             "nodes": [{"type": "con", "id": 11, "app_id": "foot", "name": "Title; [x]",
                        "rect": {"x": -1200, "y": 55, "width": 700, "height": 500}}],
             "floating_nodes": [
                 {"type": "floating_con", "id": 12, "window": 1234, "name": "X11", "rect": {}},
                 {"type": "floating_con", "id": 13, "app_id": APP_ID, "rect": {}}]}]}]}


class CoreTests(unittest.TestCase):
    def test_decoder_fragmented_and_multiple(self):
        decoder = Decoder()
        data = packet(4, {"title": "žą日本語"}) + packet(2, {"success": True})
        messages = []
        for byte in data:
            messages.extend(decoder.feed(bytes([byte])))
        self.assertEqual(messages, [(4, {"title": "žą日本語"}), (2, {"success": True})])
        self.assertFalse(decoder.data)

    def test_decoder_rejects_bad_magic_and_length(self):
        for header in (HEADER.pack(b"broken", 0, 0), HEADER.pack(b"i3-ipc", MAX_PAYLOAD + 1, 0)):
            with self.assertRaises(ValueError):
                Decoder().feed(header)

    def test_decoder_partial_header_and_body(self):
        data = packet(1, [{"num": 3}])
        decoder = Decoder()
        self.assertEqual(decoder.feed(data[:5]), [])
        self.assertEqual(decoder.feed(data[5:-1]), [])
        self.assertEqual(decoder.feed(data[-1:]), [(1, [{"num": 3}])])

    def test_all_nine_cells_and_edges(self):
        for n in range(1, 10):
            x, y, w, h = cell_rect(n)
            self.assertEqual(hit_test(x + w / 2, y + h / 2), n)
            self.assertEqual(hit_test(x, y), n)
            self.assertIsNone(hit_test(x + w, y))
            self.assertIsNone(hit_test(x, y + h))
        for point in [(0, 0), (-1, 100), (100, -1), (WIDTH, HEIGHT), (100, 335)]:
            self.assertIsNone(hit_test(*point))

    def test_target_numbered_name_and_xwayland(self):
        target = find_target(tree(), 11)
        self.assertEqual(target.workspace, "3: work")
        self.assertEqual(target.number, 3)
        self.assertEqual(target.title, "Title; [x]")
        self.assertEqual(find_target(tree(), 12).id, 12)
        self.assertIsNone(find_target(tree(), 13))
        self.assertIsNone(find_target(tree(), 9999))

    def test_counts_exclude_helper_include_floating(self):
        result = counts(tree())
        self.assertEqual(result[3], 2)
        self.assertEqual(sum(result.values()), 2)

    def test_clamp_negative_offset_and_small_areas(self):
        from core import popup_position
        for area in ({"x": -1280, "y": 30, "width": 1280, "height": 690},
                     {"x": 2560, "y": -900, "width": 900, "height": 1400}):
            for x, y in [(area['x'] - 800, area['y'] - 300),
                         (area['x'] + area['width'] + 500, area['y'] + area['height'])]:
                t = Target(1, "", "1", 1, {"x": x, "y": y, "width": 600, "height": 400}, area)
                px, py = popup_position(t)
                self.assertGreaterEqual(px, area['x'])
                self.assertGreaterEqual(py, area['y'])
                self.assertLessEqual(px + WIDTH, area['x'] + area['width'])
                self.assertLessEqual(py + HEIGHT, area['y'] + area['height'])

    def test_numeric_commands_no_auto_back_and_forth(self):
        self.assertEqual(move_command(123, 3),
                         '[con_id=123] move --no-auto-back-and-forth container to workspace number 3')
        for node, number in [("1] kill", 3), (1, "3; exit"), (1, 10), (0, 3), (1, True)]:
            with self.assertRaises(ValueError):
                move_command(node, number)


if __name__ == "__main__":
    unittest.main()
