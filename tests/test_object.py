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

ΟΙ ΚΟΝΤΕΣ ΣΤΡΟΦΕΣ (βήμα 97, ο παίκτης: «κλείσε και τα λευκά pixels μετά τις
στροφές»). Ενας διάδρομος που φτάνει στον θόλο οριζόντια με ΕΝΑ tile μετά τη
στροφή αφήνει τη διαγώνιο να ακουμπά το περίγραμμα δίπλα στον αρμό: ένα pixel
ακόμα, που ο Z80 βάζει από τις σημαίες του src/bend.asm και η αναφορά το
βρίσκει ζωγραφίζοντας (scene.bend). Δώδεκα σκηνές, μία για κάθε μέγεθος και
πλευρά, και δύο ελέγχου — οριζόντιος με δύο tiles μετά τη στροφή, κάθετος με
ένα, με κι έναν οριζόντιο στον ίδιο θόλο — όπου δεν μπαίνει τίποτα. Κάθε
σκηνή διαφέρει χωρίς τη στροφή στην αναφορά, αλλιώς δεν δοκιμάζει τίποτα.
Αρνητικά: ο διακόπτης του jtd_end κλειστός, η διαγώνιος από την άλλη πλευρά,
χωρίς τον έλεγχο του μήκους, χωρίς τον έλεγχο του οριζόντιου, και το pixel μία
γραμμή πάνω. Η σκηνή ελέγχου με τον κάθετο βρήκε και ένα λάθος: το CY που
άφηνε το ob_addu, όταν ο πίνακας περνούσε σελίδα, έμπαινε στο πρώτο rra του
jtb_dome σαν στροφή στην πλευρά 8. Ο βρόχος έχει πια srl, και το CY της
εισόδου δεν μετρά.

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


# --- οι κοντές στροφές (βήμα 97) -------------------------------------------

BEND_T = (8, 6)                          # ο θόλος με τη στροφή, σε μισά tiles


def bend_route(sz, want):
    """Ενας μικρός θόλος από όπου το route.plan φτάνει στον BEND_T (μέγεθος
    sz) με στροφή που ικανοποιεί το want(d0, d1, l1): (f, τρεξίματα)."""
    import route
    tx, ty = BEND_T
    for dy in range(-30, 31):
        for dx in range(-60, 61):
            p = route.plan(tx + dx, ty + dy, 0, tx, ty, sz)
            if p and p[0] == 0 and len(p[1]) == 2 and want(p[1][0][0], *p[1][1]):
                return (tx + dx, ty + dy), p[1]
    raise AssertionError(f"καμία διαδρομή για το μέγεθος {sz}")


def bend_scenes():
    """(όνομα, colony, κάμερα): οι δώδεκα κοντές στροφές και οι δύο έλεγχοι."""
    out = []
    cases = [(f"στροφή {'sml'[sz]} k={k}", sz,
              lambda d0, d1, l1, k=k: l1 == 1 and d1 in (2, 6) and (d0 + 4) & 7 == k)
             for sz in range(3) for k in (1, 3, 5, 7)]
    cases += [("έλεγχος: οριζόντιος, δύο tiles", 1,
               lambda d0, d1, l1: l1 == 2 and d1 in (2, 6)),
              ("έλεγχος: κάθετος, ένα tile, και οριζόντιος", 1,
               lambda d0, d1, l1: l1 == 1 and d1 in (0, 4))]
    for name, sz, want in cases:
        f, runs = bend_route(sz, want)
        c = S.Colony()
        c.n_dome, c.n_corr = 2, 2
        for i, (cx, cy, s_) in enumerate(((f[0], f[1], 0), (*BEND_T, sz))):
            b = i * S.DOME_REC
            c.dome[b + S.D_CX], c.dome[b + S.D_CY] = cx & 255, cy & 255
            c.dome[b + S.D_SIZE], c.dome[b + S.D_STATE] = s_, S.DS_ACTIVE
            c.dome[b + 5] = 255
            for k in range(8):
                c.dome[b + S.D_MACH + k] = S.NO_MACH
        (d0, n0), (d1, n1) = runs
        c.corr[0:2 * S.CORR_REC] = bytes([0, 1, d0, n0, S.DS_ACTIVE,
                                          255, 255, d1, n1, S.DS_ACTIVE])
        if d1 in (0, 4):
            # Κι ένας οριζόντιος αξονικός στον ίδιο θόλο, από την άλλη μεριά
            # της διαγωνίου: ο θόλος έχει αρμό ανατολικά ή δυτικά, και μόνο ο
            # έλεγχος του οριζόντιου στο jtm_bend κρατά έξω τον κάθετο.
            import route
            ux = 1 if d0 in (1, 3) else -1
            for dx in range(8, 40):
                g = (BEND_T[0] + ux * dx, BEND_T[1])
                p = route.plan(*BEND_T, sz, *g, 0)
                if p and p[0] == 0 and len(p[1]) == 1:
                    break
            b = 2 * S.DOME_REC
            c.dome[b + S.D_CX], c.dome[b + S.D_CY] = g[0] & 255, g[1] & 255
            c.dome[b + S.D_SIZE], c.dome[b + S.D_STATE] = 0, S.DS_ACTIVE
            c.dome[b + 5] = 255
            for k in range(8):
                c.dome[b + S.D_MACH + k] = S.NO_MACH
            c.corr[2 * S.CORR_REC:3 * S.CORR_REC] = bytes([1, 2, *p[1][0], S.DS_ACTIVE])
            c.n_dome, c.n_corr = 3, 3
        cam = S.Camera((BEND_T[0] >> 1) - S.VIEW_TW // 2, (BEND_T[1] >> 1) - S.VIEW_TH // 2)
        out.append((name, c, cam))
    return out


def layout_addr(name):
    for line in open(os.path.join(ROOT, "build", "layout.asm"), encoding="utf-8"):
        p = line.split()
        if len(p) >= 3 and p[0] == name and p[1] == "equ":
            return int(p[2].lstrip("#"), 16)
    raise KeyError(name)


def shoot_colony(sym, c, cam, patch=()):
    """Η πλήρης σχεδίαση με ΑΥΤΟΥΣ τους θόλους και διαδρόμους (και καμία δομή)
    στην τράπεζα 6: η οθόνη, γραμμική."""
    import ctypes
    from cpc import CPC, _lib
    m = CPC()
    m.run_frames(60)
    assert m.quickload(SNA, start=False), "quickload απέτυχε"
    b6 = _lib.cpcemu_ram_ptr(m._h, 6)
    for name, data in (("G_dome_tbl", c.dome), ("G_struct_tbl", c.struct),
                       ("G_corr_tbl", c.corr)):
        ctypes.memmove(ctypes.addressof(b6.contents) + layout_addr(name) - 0x4000,
                       bytes(data), len(data))
    for at, v in patch:
        m.poke(at, v)
    m.poke(sym["CAM_TX"], cam.tx & 0xFF)
    m.poke(sym["CAM_TY"], cam.ty & 0xFF)
    m.set_pc(sym["START"])
    n = 0
    while m.peek(sym["DONE_FLAG"]) != 0x5A and n < 400:
        m.run_frames(1)
        n += 1
    m.run_frames(2)
    ram = m.read_ram(0xC000, 0x4000)
    return bytes(ram[(y & 7) * 0x800 + (((y >> 3) * SCR_W + x + 2 * cam.off) & 0x7FF)]
                 for y in range(PLAY) for x in range(SCR_W)), m


def bends(sym, a, ag, plane, variants):
    fails = 0
    scenes = bend_scenes()
    refs = []
    for name, c, cam in scenes:
        ref = bytes(reference(a, c, ag, plane, cam, variants).buf[:PLAY * SCR_W])
        keep = S.dome_bends
        S.dome_bends = lambda c_, d: set()
        plain = bytes(reference(a, c, ag, plane, cam, variants).buf[:PLAY * SCR_W])
        S.dome_bends = keep
        refs.append(ref)
        got, m = shoot_colony(sym, c, cam)
        bad = sum(1 for x, y in zip(got, ref) if x != y)
        seen = sum(1 for x, y in zip(plain, ref) if x != y)
        control = name.startswith("έλεγχος")
        ok = bad == 0 and (seen == 0 if control else seen > 0)
        print(("OK " if ok else "ΑΠΟΤΥΧΙΑ ") + f"{name}: {bad} λάθος bytes, "
              f"{seen} bytes κάνει η στροφή στην αναφορά"
              + (" (έλεγχος: κανένα)" if control else ""))
        if not ok:
            fails += 1
            m.screenshot(os.path.join(HERE, "golden", f"bend_got_{len(refs)}.png"),
                         aspect=True)
    # --- αρνητικά: ο Z80 πειραγμένος, κάποια σκηνή πρέπει να διαφέρει ----
    from cpc import CPC
    m = CPC()
    m.run_frames(60)
    m.quickload(SNA, start=False)

    def find(at, pat, span=40):
        k = bytes(m.read_ram(at, span)).find(bytes(pat))
        assert k >= 0, f"δεν βρέθηκε το {pat} μετά το #{at:04X}"
        return at + k
    jm, jp, jb = sym["JTB_MARK"], sym["JTB_PX"], sym["JTM_BEND"]
    # Ο διακόπτης του jtd_end (jtd_sw) τον ανοίγει το jtm_bend στη μέτρηση: ένα
    # ret στη θέση του θα το έσβηνε, γι' αυτό πειράζεται το ld a,#21.
    neg = [("τον διακόπτη κλειστό (ld a,#C9 στο jtm_bend)", [(find(jb, [0x3E, 0x21]) + 1, 0xC9)]),
           ("η διαγώνιος από την άλλη πλευρά (add a,0 στο jtb_mark)",
            [(find(jm, [0xC6, 4]) + 1, 0)]),
           ("χωρίς τον έλεγχο του μήκους (jtm_bend)", [(find(jb, [0x25, 0xC0]) + 1, 0)]),
           ("χωρίς τον έλεγχο του οριζόντιου (jtm_bend)",
            [(find(jb, [0xCB, 0x4D, 0xC8]) + 2, 0)]),
           ("το pixel από κάτω μία γραμμή πάνω (add a,8)", [(find(jp, [0xC6, 9]) + 1, 8)])]
    for label, patch in neg:
        n = sum(1 for (_, c, cam), ref in zip(scenes, refs)
                if shoot_colony(sym, c, cam, patch)[0] != ref)
        if n:
            print(f"OK ΑΡΝΗΤΙΚΟ: με {label} διαφέρουν {n} σκηνές")
        else:
            print(f"ΑΠΟΤΥΧΙΑ ΑΡΝΗΤΙΚΟΥ: με {label} καμία σκηνή δεν διαφέρει")
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
    fails += bends(sym, a, ag, plane, variants)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
