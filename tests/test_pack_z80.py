#!/usr/bin/env python3
"""Η διάταξη μνήμης σε πραγματικό Z80.

Το test_pack.py αποδεικνύει ότι οι εικόνες των τραπεζών έχουν τα σωστά bytes
στις σωστές διευθύνσεις. Αυτό εδώ αποδεικνύει ότι ο Z80 τα ΦΤΑΝΕΙ: σελιδοποιεί
την 6 και την 7 μέσα στην ίδια σκηνή, ακολουθεί τους παραγόμενους πίνακες
δεικτών, και διαβάζει τη σελίδα 2 που είναι ταυτόχρονα σελίδα οθόνης του HUD.

Η αναφορά χτίζεται από το sprites.bin — ΟΧΙ από τις εικόνες των τραπεζών —
ώστε μια λάθος διεύθυνση στο layout.asm να μην μπορεί να «συμφωνήσει» με τον
εαυτό της.
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")

from sprites import load_map, load_bin                                  # noqa: E402
from refrender import Canvas, draw_quads, SCR_W, SCR_H                  # noqa: E402

RASM = os.path.expanduser("~/rasm/rasm.exe")
SNA = os.path.join(ROOT, "build", "packtest.sna")

# πρέπει να ταιριάζουν με το packtest.asm
DOME_X, DOME_Y = 24, 32
STRUCT_X, STRUCT_Y = 60, 40
ICON_X, ICON_Y = 4, 8
TILES_X, TILES_Y = 20, 10

# ίδια σειρά με το TERRAIN του tools/pack.py — αυτή είναι ο δείκτης του tile_ptr
TERRAIN = ["ground", "dust", "rock", "mountain",
           "water", "deepwater", "crater", "foundation"]


def build():
    for tool in ("mkoffsets.py", "pack.py"):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", tool)],
                           capture_output=True, text=True)
        if r.returncode:
            sys.exit(f"{tool} απέτυχε:\n{r.stdout}{r.stderr}")
    r = subprocess.run([RASM, "packtest.asm", "-oi", SNA, "-v2", "-s", "-eo"],
                       cwd=HERE, capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(SNA):
        sys.exit("rasm απέτυχε:\n" + r.stdout + r.stderr)
    sym = {}
    for line in open(os.path.join(HERE, "rasmoutput.sym"), encoding="utf-8",
                     errors="replace"):
        p = line.split()
        if len(p) >= 2 and p[1].startswith("#"):
            sym[p[0].upper()] = int(p[1][1:], 16)
    return sym


def reference():
    smap, blob = load_map(), load_bin()
    c = Canvas()

    def raw(name):
        s = smap[name]
        return blob[s.off:s.off + s.size]

    def rows(name):
        s = smap[name]
        d = raw(name)
        return [d[y * s.stride:(y + 1) * s.stride] for y in range(s.h)]

    # 1. έδαφος — ίδιος ντετερμινιστικός τύπος με το draw_terrain
    variants = raw("tile_variants")
    for ty in range(TILES_Y):
        for tx in range(TILES_X):
            cls = (tx + ty) & 7
            var = (tx * 3 + ty) & (variants[cls] - 1)
            c.opaque(rows(f"tile_{TERRAIN[cls]}_{var}"), tx * 4, ty * 16)

    # 2. δακτύλιος και θόλος από το αποθηκευμένο nw
    draw_quads(c, blob, smap, "ring", "s", DOME_X, DOME_Y)
    draw_quads(c, blob, smap, "dome", "s", DOME_X, DOME_Y)

    # 3. φιγούρα 1 στη θέση 0 του μικρού θόλου
    slots = raw("corr_slots")
    sx, sy = slots[0], slots[1]
    c.opaque(rows("slot_s_0_colonist"), DOME_X + sx, DOME_Y + sy)

    # 4. εξωτερική δομή από την τράπεζα 7 (με μάσκα)
    c.masked(rows("solar_m"), STRUCT_X, STRUCT_Y)

    # 5. εικονίδιο greenhouse μέσω icon_m_ptr[5]
    c.opaque(rows("icon_m_greenhouse"), ICON_X, ICON_Y)
    return c


def main():
    sym = build()
    ref = reference()

    from cpc import CPC
    m = CPC()
    m.run_frames(60)
    assert m.quickload(SNA), "quickload απέτυχε"
    m.run_frames(120)
    flag = m.peek(sym["DONE_FLAG"])
    assert flag == 0x5A, (f"δεν τερμάτισε: done_flag=#{flag:02X}, PC=#{m.pc:04X}")
    ram = m.read_ram(0xC000, 0x4000)
    m.screenshot(os.path.join(HERE, "golden", "pack_actual.png"), aspect=True)

    bad = []
    for y in range(SCR_H):
        off = (y & 7) * 0x800 + (y >> 3) * SCR_W
        got, want = ram[off:off + SCR_W], bytes(ref.buf[y * SCR_W:(y + 1) * SCR_W])
        if got != want:
            bad += [(x, y, want[x], got[x]) for x in range(SCR_W) if got[x] != want[x]]

    if not bad:
        print("OK — σελίδα 2 + τράπεζα 6 + τράπεζα 7, 16000 bytes ταυτόσημα")
        print("     (έδαφος μέσω tile_ptr, εικονίδιο μέσω icon_m_ptr, "
              "τεταρτημόρια, φιγούρα, δομή με μάσκα)")
        return 0

    print(f"ΑΠΟΤΥΧΙΑ — {len(bad)} bytes διαφέρουν")
    zones = {
        "έδαφος (σελίδα 2)": (0, 0, TILES_X * 4, TILES_Y * 16),
        "θόλος/δακτύλιος (τράπεζα 6)": (DOME_X, DOME_Y, 16, 64),
        "δομή (τράπεζα 7)": (STRUCT_X, STRUCT_Y, 8, 32),
        "εικονίδιο (σελίδα 2)": (ICON_X, ICON_Y, 8, 16),
    }
    for label, (zx, zy, zw, zh) in zones.items():
        n = sum(1 for (x, y, _, _) in bad if zx <= x < zx + zw and zy <= y < zy + zh)
        print(f"  {label}: {n}")
    for x, y, w, g in bad[:8]:
        print(f"    ({x:3d},{y:3d})  want #{w:02X}  got #{g:02X}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
