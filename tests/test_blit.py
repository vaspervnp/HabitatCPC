#!/usr/bin/env python3
"""Ο blitter του Z80 απέναντι σε ανεξάρτητο renderer σε Python.

Ο renderer της refrender.py δεν είναι port του Z80 κώδικα — υλοποιεί το
assets/SPRITES.md από το κείμενο. Όταν συμφωνούν byte-προς-byte, συμφωνούν και
οι δύο με την προδιαγραφή· κυρίως για τα τρία τεταρτημόρια που ΔΕΝ υπάρχουν
στα δεδομένα και παράγονται τη στιγμή του blit (DESIGN.md §4.4).
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")

from sprites import load_map, load_bin                      # noqa: E402
from refrender import Canvas, draw_quads, SCR_W, SCR_H      # noqa: E402

RASM = os.path.expanduser("~/rasm/rasm.exe")
SNA = os.path.join(ROOT, "build", "blittest.sna")

# Πρέπει να ταιριάζει με το frametab του blittest.asm.
# (μέγεθος, x σε bytes, y σε γραμμές, W τεταρτημορίου, H τεταρτημορίου)
FRAMES = [("s", 2, 8, 8, 32), ("m", 20, 8, 12, 48), ("l", 46, 8, 16, 64)]

# Η παλέτα δοκιμής του blittest.asm, ως firmware αριθμοί.
PAL_TEST = [0, 1, 11, 23, 13, 26, 24, 15, 6, 18, 10, 5, 25, 3, 19, 16]

FW_RGB = {  # firmware αριθμός -> RGB, αρκετό για προεπισκόπηση
    0: (0, 0, 0), 1: (0, 0, 128), 3: (128, 0, 0), 5: (128, 0, 128),
    6: (255, 0, 0), 10: (0, 128, 128), 11: (0, 128, 255), 13: (128, 128, 128),
    15: (255, 128, 0), 16: (255, 0, 128), 18: (0, 255, 0), 19: (0, 128, 0),
    23: (0, 255, 255), 24: (255, 255, 0), 25: (255, 255, 128), 26: (255, 255, 255),
}


def build():
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "mkoffsets.py")],
                   check=True, capture_output=True)
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "mkslices.py"),
                    "dome_s_nw", "dome_m_nw", "dome_l_nw",
                    "ring_s_nw", "ring_m_nw", "ring_l_nw", "flip_mode0"],
                   check=True, capture_output=True)
    r = subprocess.run([RASM, "blittest.asm", "-oi", SNA, "-v2", "-s",
                        "-eo"], cwd=HERE, capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(SNA):
        sys.exit("rasm απέτυχε:\n" + r.stdout + r.stderr)
    return symbols(os.path.join(HERE, "rasmoutput.sym"))


def symbols(path):
    """rasm -s:  NAME #ADDR Bn L"""
    out = {}
    for line in open(path, encoding="utf-8", errors="replace"):
        parts = line.split()
        if len(parts) >= 2 and parts[1].startswith("#"):
            out[parts[0].upper()] = int(parts[1][1:], 16)
    return out


def reference():
    smap, blob = load_map(), load_bin()
    c = Canvas()
    # ίδιο μοτίβο με το fill_pattern: byte(x,y) = (y*5 + x) & 255
    for y in range(SCR_H):
        base = (y * 5) & 0xFF
        for x in range(SCR_W):
            c[x, y] = (base + x) & 0xFF
    for size, x, y, _, _ in FRAMES:
        draw_quads(c, blob, smap, "ring", size, x, y)
        draw_quads(c, blob, smap, "dome", size, x, y)
    return c


def actual(sym):
    from cpc import CPC
    c = CPC()
    c.run_frames(60)
    assert c.quickload(SNA), "quickload απέτυχε"
    c.run_frames(60)
    assert c.mode == 0, f"περίμενα mode 0, βρήκα {c.mode}"
    flag = c.peek(sym["DONE_FLAG"])
    assert flag == 0x5A, (
        f"το πρόγραμμα δεν τερμάτισε: done_flag=#{flag:02X}, PC=#{c.pc:04X}. "
        "Η σκηνή μπορεί να είναι μισοσχεδιασμένη.")
    ram = c.read_ram(0xC000, 0x4000)
    c.screenshot(os.path.join(HERE, "golden", "blit_actual.png"), aspect=True)
    return ram


def main():
    sym = build()
    ref, ram = reference(), actual(sym)

    bad = []
    for y in range(SCR_H):
        off = (y & 7) * 0x800 + (y >> 3) * SCR_W
        got = ram[off:off + SCR_W]
        want = bytes(ref.buf[y * SCR_W:(y + 1) * SCR_W])
        if got != want:
            for x in range(SCR_W):
                if got[x] != want[x]:
                    bad.append((x, y, want[x], got[x]))

    pal = [FW_RGB.get(f, (255, 0, 255)) for f in PAL_TEST]
    ref.to_png(os.path.join(HERE, "golden", "blit_expected.png"), pal)

    if not bad:
        print(f"OK — {SCR_W * SCR_H} bytes ταυτόσημα "
              f"({len(FRAMES)} μεγέθη x 2 πλαίσια x 4 τεταρτημόρια)")
        return 0

    print(f"ΑΠΟΤΥΧΙΑ — {len(bad)} bytes διαφέρουν από {SCR_W * SCR_H}")
    xs = [b[0] for b in bad]
    ys = [b[1] for b in bad]
    print(f"  περιοχή: x {min(xs)}..{max(xs)}  y {min(ys)}..{max(ys)}")
    for size, fx, fy, qw, qh in FRAMES:
        for name, (ox, oy) in (("nw", (0, 0)), ("ne", (qw, 0)),
                               ("sw", (0, qh)), ("se", (qw, qh))):
            x0, y0 = fx + ox, fy + oy
            n = sum(1 for (x, y, _, _) in bad
                    if x0 <= x < x0 + qw and y0 <= y < y0 + qh)
            if n:
                print(f"  θόλος {size}, τεταρτημόριο {name}: {n} λάθος bytes")
    for x, y, w, g in bad[:8]:
        print(f"    ({x:3d},{y:3d})  want #{w:02X}  got #{g:02X}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
