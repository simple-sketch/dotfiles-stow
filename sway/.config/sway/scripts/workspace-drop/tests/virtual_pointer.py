"""Minimal virtual-pointer client, used ONLY against the private headless test Sway.

Protocol: https://gitlab.freedesktop.org/wlroots/wlr-protocols/-/blob/master/unstable/wlr-virtual-pointer-unstable-v1.xml
No production code imports this module. No physical input devices are read.
"""
import os
import socket
import struct
import time


def wire_string(text):
    value = text.encode() + b"\0"
    return struct.pack("<I", len(value)) + value + b"\0" * (-len(value) % 4)


class Pointer:
    def __init__(self, env, width=2560, height=720):
        self.width, self.height = width, height
        self.held = set()
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(2)
        self.sock.connect(os.path.join(env["XDG_RUNTIME_DIR"], env["WAYLAND_DISPLAY"]))
        self.send(1, 1, struct.pack("<I", 2))  # wl_display.get_registry
        self.send(1, 0, struct.pack("<I", 3))  # wl_display.sync
        manager = None
        while True:
            obj, opcode, data = self.receive()
            if obj == 2 and opcode == 0:
                name, length = struct.unpack("<II", data[:8])
                interface = data[8:8 + length - 1].decode()
                version = struct.unpack_from("<I", data, 8 + ((length + 3) // 4) * 4)[0]
                if interface == "zwlr_virtual_pointer_manager_v1":
                    manager = name, version
            if obj == 3:
                break
        if manager is None:
            raise RuntimeError("Headless Sway has no virtual-pointer protocol")
        self.send(2, 0, struct.pack("<I", manager[0]) + wire_string("zwlr_virtual_pointer_manager_v1") +
                  struct.pack("<II", min(2, manager[1]), 4))
        self.send(4, 0, struct.pack("<II", 0, 5))
        time.sleep(.05)

    def exact(self, size):
        data = bytearray()
        while len(data) < size:
            chunk = self.sock.recv(size - len(data))
            if not chunk:
                raise EOFError("Headless compositor disconnected")
            data.extend(chunk)
        return bytes(data)

    def receive(self):
        obj, word = struct.unpack("<II", self.exact(8))
        return obj, word & 65535, self.exact((word >> 16) - 8)

    def send(self, obj, opcode, data=b""):
        self.sock.sendall(struct.pack("<II", obj, ((len(data) + 8) << 16) | opcode) + data)

    @staticmethod
    def timestamp():
        return int(time.monotonic() * 1000) & 0xffffffff

    def motion(self, x, y):
        self.send(5, 1, struct.pack("<IIIII", self.timestamp(), int(x), int(y), self.width, self.height))
        self.send(5, 4)
        time.sleep(.025)

    def button(self, pressed, button=272):
        self.send(5, 2, struct.pack("<III", self.timestamp(), button, int(pressed)))
        self.send(5, 4)
        if pressed:
            self.held.add(button)
        else:
            self.held.discard(button)
        time.sleep(.025)

    def close(self):
        for button in list(self.held):
            self.button(False, button)
        self.send(5, 8)  # destroy
        self.sock.close()
