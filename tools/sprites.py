"""Parse assets/sprites_map.txt -> a lookup of every sprite in sprites.bin.

Single source of truth for the Python side: the map file is generated next to
the data, so a sprite that moves cannot go stale here.
"""
import os, re

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_HERE)
ASSETS = os.path.join(ROOT, "assets")

_ROW = re.compile(
    r"^\s{2}(\S+)\s+#([0-9A-Fa-f]{4})\s+(\d+)\s*"
    r"(?:(\d+)x(\d+) px\s+(\S+))?"
)


class Sprite:
    __slots__ = ("name", "off", "size", "w_px", "h", "fmt")

    def __init__(self, name, off, size, w_px, h, fmt):
        self.name, self.off, self.size = name, off, size
        self.w_px, self.h, self.fmt = w_px, h, fmt

    @property
    def masked(self):
        return self.fmt == "mask+data"

    @property
    def w(self):
        """DATA bytes per line. A masked line occupies 2x this."""
        return self.w_px // 2

    @property
    def stride(self):
        return self.w * 2 if self.masked else self.w

    def __repr__(self):
        return f"<{self.name} @#{self.off:04X} {self.size}B {self.w_px}x{self.h} {self.fmt}>"


def load_map(path=None):
    path = path or os.path.join(ASSETS, "sprites_map.txt")
    out = {}
    for line in open(path, encoding="utf-8"):
        if line.startswith("#") or not line.strip():
            continue
        m = _ROW.match(line.rstrip())
        if not m:
            continue
        name, off, size, w_px, h, fmt = m.groups()
        out[name] = Sprite(name, int(off, 16), int(size),
                           int(w_px) if w_px else None,
                           int(h) if h else None,
                           fmt)
    return out


def load_bin(path=None):
    path = path or os.path.join(ASSETS, "sprites.bin")
    return open(path, "rb").read()


def rows(blob, spr):
    """Yield one bytes() per line, exactly as stored."""
    base = spr.off
    for y in range(spr.h):
        s = base + y * spr.stride
        yield blob[s:s + spr.stride]
