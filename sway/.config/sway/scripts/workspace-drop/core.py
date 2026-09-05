"""Standard-library-only Sway IPC and workspace-drop geometry."""

from dataclasses import dataclass
import json
import socket
import struct

APP_ID = "sway-workspace-drop"
MODE = "workspace-drop"
BEGIN = 'focus; nop workspace-drop:begin; mode "workspace-drop"'
RELEASE = "nop workspace-drop:release"
CANCEL = "nop workspace-drop:cancel"
STOP = "workspace-drop:stop"
HEADER = struct.Struct("<6sII")
MAX_PAYLOAD = 16 * 1024 * 1024
WINDOW, BINDING, MODE_EVENT = 0x80000003, 0x80000005, 0x80000002
WORKSPACE, OUTPUT, SHUTDOWN, TICK = 0x80000000, 0x80000001, 0x80000006, 0x80000007
WIDTH, HEIGHT = 336, 360
PAD, GRID_Y, CELL_W, CELL_H, GAP = 18, 78, 94, 70, 9


def packet(kind, value):
    data = value.encode() if isinstance(value, str) else json.dumps(value).encode()
    return HEADER.pack(b"i3-ipc", len(data), kind) + data


class Decoder:
    def __init__(self):
        self.data = bytearray()

    def feed(self, data):
        self.data.extend(data)
        messages = []
        while len(self.data) >= HEADER.size:
            magic, size, kind = HEADER.unpack_from(self.data)
            if magic != b"i3-ipc" or size > MAX_PAYLOAD:
                raise ValueError("Invalid Sway IPC header")
            end = HEADER.size + size
            if len(self.data) < end:
                break
            messages.append((kind, json.loads(self.data[HEADER.size:end])))
            del self.data[:end]
        return messages


class IPC:
    def __init__(self, path):
        self.path = path
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(2)
        self.sock.connect(path)

    def close(self):
        self.sock.close()

    def request(self, kind, value=""):
        self.sock.sendall(packet(kind, value))
        decoder = Decoder()
        while True:
            data = self.sock.recv(65536)
            if not data:
                raise ConnectionError("Sway disconnected")
            messages = decoder.feed(data)
            if messages:
                reply_kind, reply = messages[0]
                if reply_kind != kind:
                    raise ValueError("Unexpected Sway IPC reply")
                return reply

    def command(self, text):
        result = self.request(0, text)
        failures = [r.get("error", "Unknown Sway error") for r in result if not r.get("success")]
        if failures:
            raise RuntimeError("; ".join(failures))
        return result


def walk(node, workspace=None, output=None):
    if node.get("type") == "output":
        output = node
    if node.get("type") == "workspace":
        workspace = node
    yield node, workspace, output
    for child in node.get("nodes", []) + node.get("floating_nodes", []):
        yield from walk(child, workspace, output)


def is_window(node):
    return node.get("app_id") is not None or node.get("window") is not None


@dataclass(frozen=True)
class Target:
    id: int
    title: str
    workspace: str
    number: int
    rect: dict
    area: dict


def find_target(tree, node_id):
    for node, ws, output in walk(tree):
        if node.get("id") != node_id:
            continue
        if not is_window(node) or node.get("app_id") == APP_ID or not ws or not output:
            return None
        if ws.get("name") == "__i3_scratch":
            return None
        return Target(node_id, node.get("name") or node.get("app_id") or "Window",
                      ws["name"], ws.get("num", -1), node["rect"], ws["rect"])
    return None


def counts(tree):
    result = {i: 0 for i in range(1, 10)}
    for node, ws, _ in walk(tree):
        if ws and ws.get("num") in result and is_window(node) and node.get("app_id") != APP_ID:
            result[ws["num"]] += 1
    return result


def cell_rect(number):
    if number not in range(1, 10):
        raise ValueError("Workspace must be 1–9")
    row, col = divmod(number - 1, 3)
    return PAD + col * (CELL_W + GAP), GRID_Y + row * (CELL_H + GAP), CELL_W, CELL_H


def hit_test(x, y):
    for number in range(1, 10):
        left, top, width, height = cell_rect(number)
        if left <= x < left + width and top <= y < top + height:
            return number
    return None


def popup_position(target):
    """Below the source title bar, clamped to the source workspace's usable area."""
    area, rect = target.area, target.rect
    x = rect["x"] + (rect["width"] - WIDTH) // 2
    y = rect["y"] + 24
    if y + HEIGHT + 12 > area["y"] + area["height"]:
        y = rect["y"] - HEIGHT - 40
    max_x = max(area["x"], area["x"] + area["width"] - WIDTH)
    max_y = max(area["y"], area["y"] + area["height"] - HEIGHT)
    return max(area["x"], min(x, max_x)), max(area["y"], min(y, max_y))


def move_command(node_id, number):
    # Never interpolate a window title or an unvalidated workspace label into IPC.
    if type(node_id) is not int or node_id <= 0 or type(number) is not int or number not in range(1, 10):
        raise ValueError("Invalid window ID or workspace")
    return f"[con_id={node_id}] move --no-auto-back-and-forth container to workspace number {number}"
