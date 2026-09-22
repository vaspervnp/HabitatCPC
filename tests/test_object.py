#!/usr/bin/env python3
"""Το πέρασμα αντικειμένων, byte προς byte με την αναφορά (DESIGN §8.4).

Η αναφορά (tools/scene.py) γράφτηκε από την πρόζα του SPRITES.md §10 και του
§3.4, όχι από τον Z80. Οταν συμφωνούν, συμφωνούν και οι δύο με το χαρτί.

ΟΙ ΚΑΜΕΡΕΣ ΔΙΑΛΕΧΤΗΚΑΝ ΓΙΑ ΝΑ ΣΠΑΣΟΥΝ ΠΡΑΓΜΑΤΑ. Η σημαντικότερη είναι εκείνη
όπου το σημείο τυλίγματος του δαχτυλιδιού των 2 KB πέφτει ΜΕΣΑ σε θόλο: εκεί
μια γραμμή sprite σπάει στα δύο, και μια υλοποίηση που το αγνοεί γράφει 2 KB
πιο πίσω — δηλαδή κάπου αλλού στην οθόνη, σιωπηλά.
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")

import scene as S                                                       # noqa: E402
import colony, mkcolony, palette                                        # noqa: E402
import world as W                                                       # noqa: E402
from refrender import Canvas, SCR_W                                     # noqa: E402

RASM = os.path.expanduser("~/rasm/rasm.exe")
SNA = os.path.join(ROOT, "build", "objtest.sna")
PLAY = S.PLAY_LINES

# (tx, ty, γιατί)
CAMERAS = [
    (-21, -13, "δύο θόλοι, διαγώνιος διάδρομος, φιγούρες στον δακτύλιο"),
    (-14,  -8, "μεγάλος θόλος κομμένος στο ΚΑΤΩ χείλος του κάδρου"),
    (-40,  -6, "δομές στο δυτικό άκρο — πλατφόρμα, ορυχείο, αεροθάλαμος"),
    (  4,  -2, "θόλος κομμένος στο ΑΡΙΣΤΕΡΟ χείλος, δηλαδή clip σε καθρεφτισμένο"),
    (-18,  -3, "το τύλιγμα του δαχτυλιδιού μέσα στην εικόνα"),
]


def build():
    for tool in ("mkoffsets.py", "pack.py", "mkcolony.py"):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", tool)],
                           capture_output=True, text=True)
        if r.returncode:
            sys.exit(f"{tool} απέτυχε:\n{r.stdout}{r.stderr}")
    r = subprocess.run([RASM, "objtest.asm", "-oi", SNA, "-v2", "-s", "-eo"],
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


def reference(a, c, ag, plane, cam, variants):
    cv = Canvas()
    for row in range(S.VIEW_TH):
        for col in range(S.VIEW_TW):
            tx, ty = cam.tx + col, cam.ty + row
            b = plane.get(tx, ty)
            cls = W.cls_of(b)
            cv.opaque(a.rows(f"tile_{W.CLASS_NAMES[cls]}_"
                             f"{plane.variant(tx, ty, variants)}"),
                      col * 4, row * 16)
            if cls == W.MOUNTAIN and W.res_of(b):
                cv.masked(a.rows(f"ore_overlay_{W.decor_of(b) & 1}"),
                          col * 4, row * 16)
    S.draw_objects(cv, a, cam, c, ag=ag)
    return cv


def main():
    sym = build()
    a = S.Assets()
    c, ag, plane = mkcolony.build()
    variants = a._tab("tile_variants")
    from cpc import CPC

    fails, frames = 0, None
    for tx, ty, why in CAMERAS:
        m = CPC()
        m.run_frames(60)
        assert m.quickload(SNA, start=False), "quickload απέτυχε"
        m.poke(sym["CAM_TX"], tx & 0xFF)
        m.poke(sym["CAM_TY"], ty & 0xFF)
        m.set_pc(sym["START"])
        n = 0
        while m.peek(sym["DONE_FLAG"]) != 0x5A and n < 400:
            m.run_frames(1)
            n += 1
        assert m.peek(sym["DONE_FLAG"]) == 0x5A, \
            f"δεν τερμάτισε σε {n} frames, PC=#{m.pc:04X}"
        frames = frames or n

        cam = S.Camera(tx, ty)
        got_off = m.peek(sym["CAM_OFF"]) | (m.peek(sym["CAM_OFF"] + 1) << 8)
        tag = f"κάμερα ({tx:>4},{ty:>4})"
        if got_off != cam.off:
            print(f"ΑΠΟΤΥΧΙΑ {tag}: offset CRTC {got_off} != {cam.off}")
            fails += 1
            continue

        ref = reference(a, c, ag, plane, cam, variants)
        ram = m.read_ram(0xC000, 0x4000)
        bad = []
        for y in range(PLAY):
            hi = (y & 7) * 0x800
            row = (y >> 3) * SCR_W
            for x in range(SCR_W):
                p = (row + x + 2 * cam.off) & 0x7FF
                if ram[hi + p] != ref.buf[y * SCR_W + x]:
                    bad.append((x, y))
        if bad:
            fails += 1
            print(f"ΑΠΟΤΥΧΙΑ {tag}: {len(bad)} bytes — {why}")
            xs = sorted({x for x, _ in bad})
            ys = sorted({y for _, y in bad})
            print(f"    x {xs[0]}..{xs[-1]}   y {ys[0]}..{ys[-1]}   "
                  f"πρώτο {bad[0]}")
            ref.to_png(os.path.join(HERE, "golden", f"obj_ref_{tx}_{ty}.png"),
                       palette.pen_rgb(a.palette_fw))
            m.screenshot(os.path.join(HERE, "golden", f"obj_got_{tx}_{ty}.png"),
                         aspect=True)
        else:
            print(f"OK {tag}  {why}")
            m.screenshot(os.path.join(HERE, "golden", f"obj_{tx}_{ty}.png"),
                         aspect=True)

    us = frames * 19968
    print(f"\nπλήρης σχεδίαση κάδρου: {frames} frames = {us/1000:.0f} ms")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
