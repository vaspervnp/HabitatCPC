"""Independent Python reference renderer for Mode 0.

Deliberately NOT a port of the Z80 code: it implements assets/SPRITES.md from
the prose, so when it and the Z80 blitter agree byte-for-byte, both agree with
the spec. Works in linear 80x200 byte space; screen interleave is applied only
at the comparison boundary.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sprites import load_map, load_bin

SCR_W = 80          # bytes per line
SCR_H = 200         # lines


def flip_byte(b):
    """Swap the two Mode 0 pixels in a byte: bit pairs (7,6)(5,4)(3,2)(1,0)."""
    return ((b & 0xAA) >> 1) | ((b & 0x55) << 1)


def unpack_pens(b):
    """Byte -> (left pen, right pen). Mode 0 bit layout."""
    p0 = ((b >> 7) & 1) | (((b >> 3) & 1) << 1) | (((b >> 5) & 1) << 2) | (((b >> 1) & 1) << 3)
    p1 = ((b >> 6) & 1) | (((b >> 2) & 1) << 1) | (((b >> 4) & 1) << 2) | (((b >> 0) & 1) << 3)
    return p0, p1


class Canvas:
    def __init__(self, fill=0):
        self.buf = bytearray([fill]) * (SCR_W * SCR_H)

    def __getitem__(self, xy):
        x, y = xy
        return self.buf[y * SCR_W + x]

    def __setitem__(self, xy, v):
        x, y = xy
        self.buf[y * SCR_W + x] = v

    # -- blits ---------------------------------------------------------
    def opaque(self, rows, x, y):
        for dy, row in enumerate(rows):
            ty = y + dy
            if not (0 <= ty < SCR_H):
                continue
            for dx, b in enumerate(row):
                tx = x + dx
                if 0 <= tx < SCR_W:
                    self.buf[ty * SCR_W + tx] = b

    def masked(self, rows, x, y):
        """rows are mask,data,mask,data... per line."""
        for dy, row in enumerate(rows):
            ty = y + dy
            if not (0 <= ty < SCR_H):
                continue
            for i in range(0, len(row), 2):
                tx = x + i // 2
                if not (0 <= tx < SCR_W):
                    continue
                o = ty * SCR_W + tx
                self.buf[o] = (self.buf[o] & row[i]) | row[i + 1]

    # -- output --------------------------------------------------------
    def to_screen_ram(self, base=0xC000):
        """Linear -> CPC interleaved 16K block."""
        ram = bytearray(0x4000)
        for y in range(SCR_H):
            off = (y & 7) * 0x800 + (y >> 3) * SCR_W
            ram[off:off + SCR_W] = self.buf[y * SCR_W:(y + 1) * SCR_W]
        return bytes(ram)

    def to_pens(self):
        out = []
        for y in range(SCR_H):
            row = []
            for x in range(SCR_W):
                row.extend(unpack_pens(self.buf[y * SCR_W + x]))
            out.append(row)
        return out

    def to_png(self, path, palette_rgb, scale=2):
        from PIL import Image
        pens = self.to_pens()
        img = Image.new("RGB", (SCR_W * 2, SCR_H))
        px = img.load()
        for y, row in enumerate(pens):
            for x, p in enumerate(row):
                px[x, y] = palette_rgb[p]
        if scale != 1:
            img = img.resize((img.width * scale, img.height * scale * 2), Image.NEAREST)
        img.save(path)
        return path


# -- quadrant synthesis, straight from SPRITES.md section 5 ---------------

def quad_rows(blob, spr, orient):
    """orient in nw/ne/sw/se. `spr` is always the stored nw quadrant."""
    stride = spr.stride
    raw = [blob[spr.off + y * stride: spr.off + (y + 1) * stride] for y in range(spr.h)]

    if orient in ("sw", "se"):
        raw = raw[::-1]                       # lines bottom-to-top

    if orient in ("ne", "se"):
        flipped = []
        for row in raw:
            pairs = [row[i:i + 2] for i in range(0, len(row), 2)]
            pairs.reverse()                   # reverse PAIRS, not bytes
            out = bytearray()
            for mask, data in pairs:
                out.append(flip_byte(mask))
                out.append(flip_byte(data))
            flipped.append(bytes(out))
        raw = flipped

    return raw


def draw_quads(canvas, blob, smap, stem, size, x, y):
    """Draw a full dome/ring frame from its single stored nw quadrant."""
    spr = smap[f"{stem}_{size}_nw"]
    qw, qh = spr.w, spr.h
    for orient, (ox, oy) in (("nw", (0, 0)), ("ne", (qw, 0)),
                             ("sw", (0, qh)), ("se", (qw, qh))):
        canvas.masked(quad_rows(blob, spr, orient), x + ox, y + oy)
