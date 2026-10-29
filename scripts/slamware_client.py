"""Minimal Slamware (Slamtec Mapper) JSON-over-TCP client: pose, known area and map bitmap."""
import base64
import json
import random
import socket
import struct

DELIM = b"\n\r\n\r\n"
RLE_HEADER_SIZE = 9

MAP_TYPE_BITMAP8 = 0
MAP_KIND_EXPLORER = 0


def inflate(b64):
    data = base64.b64decode(b64)
    if len(data) < RLE_HEADER_SIZE:
        raise ValueError("missing RLE header")
    s1, s2 = data[3], data[4]
    (size,) = struct.unpack_from("<I", data, 5)
    out = bytearray()
    i = RLE_HEADER_SIZE
    while i < len(data) and len(out) < size:
        if data[i] == s1 and i + 2 < len(data):
            count, value = data[i + 1], data[i + 2]
            if count == 0 and value == s2:
                s1, s2 = s2, s1
            else:
                out.extend([value] * count)
            i += 3
        else:
            out.append(data[i])
            i += 1
    if len(out) != size:
        raise ValueError(f"inflated {len(out)} != {size}")
    return bytes(out)


class SlamwareClient:
    def __init__(self, host="192.168.11.1", port=1445, timeout=3.0):
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.buf = b""

    def close(self):
        self.sock.close()

    def request(self, command, args=None):
        req = {"command": command, "request_id": random.randint(1, 2**31 - 1)}
        if args is not None:
            req["args"] = args
        self.sock.sendall(json.dumps(req).encode() + DELIM)
        while DELIM not in self.buf:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("connection closed")
            self.buf += chunk
        resp, self.buf = self.buf.split(DELIM, 1)
        return json.loads(resp)["result"]

    def pose(self):
        return self.request("getpose")

    def known_area(self, kind=MAP_KIND_EXPLORER):
        return self.request("getknownarea", {"type": MAP_TYPE_BITMAP8, "kind": kind, "partially": False})

    def map_bitmap(self, x, y, width, height, kind=MAP_KIND_EXPLORER):
        r = self.request("getmapdata", {
            "area": {"x": x, "y": y, "width": width, "height": height},
            "type": MAP_TYPE_BITMAP8, "kind": kind, "partially": False})
        r["cells"] = inflate(r["map_data"])
        return r
