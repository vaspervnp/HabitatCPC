#!/usr/bin/env python3
"""Το πέρασμα αντικειμένων, byte προς byte με την αναφορά (DESIGN §8.4).

Η αναφορά (tools/scene.py) γράφτηκε από την πρόζα του SPRITES.md §10 και του
§3.4, όχι από τον Z80. Οταν συμφωνούν, συμφωνούν και οι δύο με το χαρτί.

ΟΙ ΔΙΑΔΡΟΜΟΙ ΑΠΟ ΤΟ ΒΗΜΑ 96 (ο παίκτης): στο κέντρο του θόλου, κάτω από τους
δακτυλίους, χωρίς πόρτες, και ένα pixel μέσα στον δακτύλιο με τους ΑΡΜΟΥΣ
μετά το κέλυφος — που κλείνουν και το κενό της διαγωνίου ως τον δακτύλιο. Ο
Z80 ζωγραφίζει τα σχέδια που φτιάχνει το tools/pack.py από τα sprites· η
αναφορά υπολογίζει τον ίδιο κανόνα ζωγραφίζοντας (scene.joint). Δύο
υλοποιήσεις: όταν συμφωνούν, συμφωνεί και ο κανόνας. Αρνητικά, με τον Z80
πειραγμένο: ο νότιος και ο ανατολικός διάδρομος όπως ως το 95 (από τον άξονα
προς τα δεξιά ή κάτω), χωρίς αρμούς, ο b χωρίς αρμό, οι νότιοι αρμοί χωρίς
κάθετο καθρέφτισμα, ο ανατολικός αρμός ένα byte δεξιά — καθένα πρέπει να
διαφέρει από την αναφορά σε κάποια κάμερα. Τις στροφές τις συγκρίνει το
test_route, και τον αρμό του b μετά από στροφή το test_link.

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


def shoot(sym, tx, ty, patch=()):
    """Η πλήρης σχεδίαση στην κάμερα: (RAM οθόνης, frames, offset CRTC)."""
    from cpc import CPC
    m = CPC()
    m.run_frames(60)
    assert m.quickload(SNA, start=False), "quickload απέτυχε"
    for at, v in patch:
        m.poke(at, v)
    m.poke(sym["CAM_TX"], tx & 0xFF)
    m.poke(sym["CAM_TY"], ty & 0xFF)
    m.set_pc(sym["START"])
    n = 0
    while m.peek(sym["DONE_FLAG"]) != 0x5A and n < 400:
        m.run_frames(1)
        n += 1
    return m, n


def differs(sym, refs, patch):
    """Σε πόσες κάμερες η σχεδίαση με το patch διαφέρει από την αναφορά."""
    bad = 0
    for (tx, ty, _), ref in zip(CAMERAS, refs):
        m, _ = shoot(sym, tx, ty, patch)
        m.run_frames(2)
        ram = m.read_ram(0xC000, 0x4000)
        off = S.Camera(tx, ty).off
        if any(ram[(y & 7) * 0x800 + (((y >> 3) * SCR_W + x + 2 * off) & 0x7FF)]
               != ref.buf[y * SCR_W + x] for y in range(PLAY) for x in range(SCR_W)):
            bad += 1
    return bad


def negatives(sym, refs):
    from cpc import CPC
    m = CPC()
    m.run_frames(60)
    m.quickload(SNA, start=False)
    fails = 0
    # corr_dir: εννέα bytes ανά κατεύθυνση, η αρχή x, y στα +6, +7. Η αποικία
    # του test_object έχει διαδρόμους μόνο προς e, s και se, και καμία στροφή:
    # τις στροφές τις συγκρίνει με την αναφορά το test_route.
    cd = sym["CORR_DIR"]
    # Οι αρμοί (βήμα 96): το call jt_dome στο ob_fittings, το cp MAX_DOME του
    # jt_mark για τον b, και ο jt_tab — x, γραμμή, σχέδιο | 128 — ανά 8 x
    # μέγεθος + κατεύθυνση.
    jd, jm, jt = sym["JT_DOME"], sym["JT_MARK"], sym["JT_TAB"]
    of = sym["OB_FITTINGS"]
    ic = bytes(m.read_ram(of, 40)).find(bytes([0xCD, jd & 255, jd >> 8]))
    ib = bytes(m.read_ram(jm, 40)).find(bytes([0xFE, S.MAX_DOME]))
    assert m.peek(cd + 4 * 9 + 6) == 0xFF and m.peek(cd + 2 * 9 + 7) == 0xFC \
        and ic >= 0 and ib >= 0, "δεν βρέθηκαν τα bytes των αρνητικών"
    south = [(jt + 3 * (8 * z + d) + 2, m.peek(jt + 3 * (8 * z + d) + 2) & 0x7F)
             for z in range(3) for d in (3, 4, 5)]
    east = [(jt + 3 * (8 * z + 2), m.peek(jt + 3 * (8 * z + 2)) + 1) for z in range(3)]
    for label, patch in (("ο νότιος διάδρομος από τον άξονα (το 95)", [(cd + 4 * 9 + 6, 0)]),
                         ("ο ανατολικός από τον άξονα (το 95)", [(cd + 2 * 9 + 7, 0)]),
                         ("χωρίς αρμούς (το ob_fittings δεν καλεί το jt_dome)",
                          [(of + ic + k, 0) for k in range(3)]),
                         ("ο b χωρίς αρμό (cp 0 στο jt_mark)", [(jm + ib + 1, 0)]),
                         ("οι νότιοι αρμοί χωρίς κάθετο καθρέφτισμα", south),
                         ("ο ανατολικός αρμός ένα byte δεξιά", east)):
        n = differs(sym, refs, patch)
        if n:
            print(f"OK ΑΡΝΗΤΙΚΟ: με {label} διαφέρουν {n} κάμερες")
        else:
            print(f"ΑΠΟΤΥΧΙΑ ΑΡΝΗΤΙΚΟΥ: με {label} καμία κάμερα δεν διαφέρει")
            fails += 1
    return fails


def main():
    sym = build()
    a = S.Assets()
    c, ag, plane = mkcolony.build()
    variants = a._tab("tile_variants")
    from cpc import CPC

    fails, frames, refs = 0, None, []
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
        refs.append(ref)
        ram = m.read_ram(0xC000, 0x4000)
        # Η λήψη είναι το τελευταίο ΟΛΟΚΛΗΡΩΜΕΝΟ καρέ του βίντεο: αν το START
        # τελείωσε στη μέση ενός, το HUD φαίνεται μισό (βήμα 39, όταν η πλήρης
        # σχεδίαση άρχισε να τελειώνει αλλού). Δύο καρέ στο hang, και η εικόνα
        # είναι η μνήμη.
        m.run_frames(2)
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
    if len(refs) == len(CAMERAS):
        fails += negatives(sym, refs)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
