#!/usr/bin/env python3
"""Δρομολόγηση διαδρόμου: ο Z80 εναντίον του tools/route.py (DESIGN §9.4).

Τέσσερις ισχυρισμοί:

  1. Για ΚΑΘΕ ζεύγος θόλων της δοκιμαστικής αποικίας, ο Z80 και η αναφορά
     συμφωνούν σε τρία πράγματα: αν υπάρχει διαδρομή, από ποιον θόλο ξεκινά,
     και ποια τρεξίματα την αποτελούν. Οι δύο υλοποιήσεις γράφτηκαν χωριστά
     από την ίδια πρόζα.
  2. Συμφωνούν και στα ΠΛΑΚΙΔΙΑ που πατά — αυτά είναι που ελέγχονται για
     κατοχή και αυτά που σφραγίζονται.
  3. Ο έλεγχος λέει όχι όταν η διαδρομή περνά πάνω από θόλο.
  4. Η τοποθέτηση γράφει ΔΥΟ εγγραφές για τη διαδρομή με στροφή, η δεύτερη με
     C_A = 255, δεσμεύει τα tiles, πληρώνει ανά πλακίδιο και προσθέτει ΜΙΑ
     ακμή στον γράφο.

Και ένα αρνητικό: αν η στροφή του renderer (oc_bend) πάει ένα tile λάθος, η
εικόνα αλλάζει — ο έλεγχος 5 το δείχνει συγκρίνοντας με τον Python renderer.
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/vasilhs/cpcemu")

import route                                                            # noqa: E402
import colony as C                                                      # noqa: E402
import scene as S                                                       # noqa: E402
from test_build import build, sb                                        # noqa: E402

FAIL = []


def check(ok, msg):
    print(("OK " if ok else "ΛΑΘΟΣ ") + msg)
    if not ok:
        FAIL.append(msg)


def boot(sym, g):
    from cpc import CPC
    m = CPC()
    m.run_frames(60)
    m.quickload(os.path.join(ROOT, "build", "uitest.sna"))
    n = 0
    while m.peek(sym["READY_FLAG"]) != 0x5A and n < 900:
        m.run_frames(1)
        n += 1
    if n >= 900:
        sys.exit("δεν ξεκίνησε")
    for idx in (3, 4):                       # μέταλλο και βιοπλαστικό
        m.poke(g + idx * 2, 0xE8)
        m.poke(g + idx * 2 + 1, 0x03)        # 1000
    return m


def entry(m, sym, name):
    m.poke(sym["DONE_FLAG"], 0)
    m.set_pc(sym[name])
    k = 0
    while m.peek(sym["DONE_FLAG"]) != 0x5A and k < 400:
        m.run_frames(1)
        k += 1
    if k >= 400:
        sys.exit(f"το {name} δεν τελείωσε")


def z80_plan(m, sym, a, b):
    m.poke(sym["PLAN_A"], a)
    m.poke(sym["PLAN_B"], b)
    entry(m, sym, "DO_PLAN")
    n = m.peek(sym["CR_N"])
    if n == 0:
        return None
    runs = [(m.peek(sym["CR_D0"]), m.peek(sym["CR_L0"]))]
    if n > 1:
        runs.append((m.peek(sym["CR_D1"]), m.peek(sym["CR_L1"])))
    nt = m.peek(sym["WALK_N"])
    base = sym["WALK_BUF"]
    tiles = [(sb(m.peek(base + 2 * i)), sb(m.peek(base + 2 * i + 1)))
             for i in range(nt)]
    return m.peek(sym["CR_FROM"]), runs, tiles, m.peek(sym["PLAN_BAD"])


def main():
    sym, g = build()
    col = C.build()
    m = boot(sym, g)

    # --- 1 & 2: κάθε ζεύγος θόλων ----------------------------------------
    bad_plan, bad_tile, npair, nroute, nbend = [], [], 0, 0, 0
    for a in range(col.n_dome):
        for b in range(a + 1, col.n_dome):
            npair += 1
            ref = route.plan(sb(col.d(a, S.D_CX)), sb(col.d(a, S.D_CY)),
                             col.d(a, S.D_SIZE),
                             sb(col.d(b, S.D_CX)), sb(col.d(b, S.D_CY)),
                             col.d(b, S.D_SIZE))
            got = z80_plan(m, sym, a, b)
            if ref is None:
                if got is not None:
                    bad_plan.append((a, b, None, got[:2]))
                continue
            side, runs = ref
            frm = a if side == 0 else b
            if got is None or got[0] != frm or got[1] != runs:
                bad_plan.append((a, b, (frm, runs), got and got[:2]))
                continue
            nroute += 1
            if len(runs) > 1:
                nbend += 1
            # τα πλακίδια, από τη γεωμετρία της αναφοράς
            src = frm
            fx, fy = sb(col.d(src, S.D_CX)), sb(col.d(src, S.D_CY))
            want = tiles_of(col, src, runs, a if frm == b else b)
            if got[2] != want:
                bad_tile.append((a, b, want, got[2]))
    check(not bad_plan,
          f"δρομολόγηση: {npair} ζεύγη, {nroute} διαδρομές ({nbend} με στροφή)"
          + ("" if not bad_plan else f" — {bad_plan[:2]}"))
    check(not bad_tile,
          "τα ίδια πλακίδια με την αναφορά"
          + ("" if not bad_tile else f" — {bad_tile[:1]}"))

    # --- 3: ο έλεγχος πάνω από θόλο --------------------------------------
    # Οι θόλοι 0 και 2 είναι στην ίδια σειρά με τον 1 ανάμεσά τους.
    got = z80_plan(m, sym, 0, 2)
    check(got is not None and got[3] > 0,
          "η διαδρομή που περνά πάνω από θόλο απορρίπτεται: "
          f"{got[3] if got else '-'} άκυρα πλακίδια")
    got = z80_plan(m, sym, 0, 1)
    check(got is not None and got[3] == 0,
          "δύο γειτονικοί θόλοι: καθαρή διαδρομή")

    commit_and_render(sym, g, col)
    ui_flow(sym, g, col)
    return 1 if FAIL else 0


def ui_flow(sym, g, col):
    """Ολη η διαδρομή του παίκτη: μενού -> CORRIDOR -> θόλος -> θόλος.

    Τα δύο πρώτα φυτεμένα σημεία είναι σε ΚΑΘΑΡΟ έδαφος (το βρήκε σάρωση του
    επιπέδου), άρα εδώ περνά και ο έλεγχος — σε αντίθεση με το do_link, που
    τον παρακάμπτει επίτηδες.
    """
    from cpc import KEY_SPACE, KEY_RIGHT
    gd, gc = layout("G_dome_tbl"), layout("G_corr_tbl")
    m = boot(sym, g)
    for idx, hx, hy in PLANT[:2]:
        plant(m, sym, 0xC6, gd + 24 * idx, dome_rec(hx, hy))
    m.set_pc(sym["LOOP"])                # το do_plant κρεμάει· πίσω στον βρόχο
    m.run_frames(4)

    def tap(key, n=1):
        for _ in range(n):
            m.key_down(key)
            m.run_frames(3)
            m.key_up(key)
            m.run_frames(4)

    def fire():
        m.joystick(0x10)
        m.run_frames(4)
        m.joystick(0)
        m.run_frames(10)

    def goto(hx, hy, st):
        m.poke(sym["GOTO_X"], hx & 0xFF)
        m.poke(sym["GOTO_Y"], hy & 0xFF)
        m.poke(sym["GOTO_ST"], st)
        entry(m, sym, "DO_GOTO")
        m.set_pc(sym["LOOP"])
        m.run_frames(4)

    tap(KEY_SPACE)                       # -> MENU, είδος 0
    tap(KEY_RIGHT, 3)                    # -> CORRIDOR
    m.key_up("\x01")
    m.set_joystick_type(1)
    check(m.peek(sym["BD_KIND"]) == 2, "ο κατάλογος έφτασε στο CORRIDOR")
    fire()
    check(m.peek(sym["UI_STATE"]) == 3 and m.peek(sym["LN_A"]) == 255,
          "το FIRE στο CORRIDOR μπαίνει στην κατάσταση LINK χωρίς αφετηρία")
    goto(PLANT[0][1], PLANT[0][2], 3)
    fire()
    check(m.peek(sym["LN_A"]) == 12,
          f"το πρώτο FIRE διάλεξε τον θόλο {m.peek(sym['LN_A'])}")
    goto(PLANT[1][1], PLANT[1][2], 3)
    check(m.peek(sym["UI_BAD"]) == 0 and m.peek(sym["CR_N"]) == 2,
          "το φάντασμα δείχνει έγκυρη διαδρομή με στροφή")
    # --- το κόστος ενός βήματος κέρσορα, μετρημένο ------------------------
    def cost():
        m.poke(sym["DONE_FLAG"], 0)
        m.set_pc(sym["DO_COST"])
        k = 0
        while m.peek(sym["DONE_FLAG"]) != 0x5A and k < 600:
            m.run_frames(1)
            k += 1
        m.set_pc(sym["LOOP"])
        m.run_frames(2)
        return k * 19968 / 16

    link_us = cost()
    goto(PLANT[1][1], PLANT[1][2], 0)
    look_us = cost()
    goto(PLANT[1][1], PLANT[1][2], 3)
    print(f"   βήμα κέρσορα: LOOK {look_us:.0f} us · LINK {link_us:.0f} us "
          f"(διαδρομή {m.peek(sym['CR_L0']) + m.peek(sym['CR_L1'])} πλακιδίων)")
    check(look_us < 20000 and link_us < 60000,
          "ο κέρσορας κοστίζει κάτω από ένα frame, το φάντασμα διαδρομής "
          "κάτω από τρία")

    before = m.peek(g + 3 * 2) | (m.peek(g + 3 * 2 + 1) << 8)
    fire()
    rec = snoop(m, sym, 0xC6, gc + S.CORR_REC * col.n_corr, S.CORR_REC * 2)
    after = m.peek(g + 3 * 2) | (m.peek(g + 3 * 2 + 1) << 8)
    check(rec[0] == 12 and rec[1] == 13 and rec[5] == 255
          and m.peek(sym["LN_A"]) == 255 and after < before,
          f"το δεύτερο FIRE έχτισε: {list(rec[:5])} {list(rec[5:])}, "
          f"μέταλλο {before} -> {after}")


def tiles_of(col, frm, runs, to):
    """Τα πλακίδια της διαδρομής σε συντεταγμένες κόσμου — η αναφορά."""
    fx, fy = sb(col.d(frm, S.D_CX)), sb(col.d(frm, S.D_CY))
    tx, ty = sb(col.d(to, S.D_CX)), sb(col.d(to, S.D_CY))
    sa = col.d(frm, S.D_SIZE)
    btx, bty = fx >> 1, fy >> 1
    ka, ra = route.DIAG_K[sa], route.RADIUS[sa] // 2
    sx, sy = (tx - fx) // 2, (ty - fy) // 2
    Sd, Td = abs(sx), abs(sy)
    ux = (sx > 0) - (sx < 0)
    uy = (sy > 0) - (sy < 0)
    out = []
    d0, n0 = runs[0]
    if d0 & 1:
        for i in range(n0):
            j = ka + i
            lx, ly = ux * j, uy * j
            if ux == uy:
                out += [(lx - 1, ly - 1), (lx, ly)]
            else:
                out += [(lx - 1, ly), (lx, ly - 1)]
        if len(runs) > 1:
            d1, n1 = runs[1]
            vx, vy = route.DIR_U[d1]
            if vx:
                c = ux * Td - (1 if ux > 0 else 0)
                r = uy * Td
                for _ in range(n1):
                    out.append((c, r))
                    c += vx
            else:
                r = uy * (Sd - 1) - (1 if uy < 0 else 0)
                c = ux * Sd
                for _ in range(n1):
                    out.append((c, r))
                    r += vy
    elif d0 in (2, 6):
        c = ra if ux > 0 else -ra - 1
        for _ in range(n0):
            out.append((c, 0))
            c += ux
    else:
        r = ra if uy > 0 else -ra - 1
        for _ in range(n0):
            out.append((0, r))
            r += uy
    return [(x + btx, y + bty) for x, y in out]


# --- οι τρεις θόλοι που φυτεύονται, σε μισά tiles -------------------------
# Μακριά από την αποικία, και ΑΔΙΑΦΟΡΟ αν το έδαφος τους επιτρέπει: εδώ
# δοκιμάζεται ο renderer, όχι ο έλεγχος θέσης.
PLANT = [(12, -74, -100), (13, -58, -94), (14, -68, -76)]
LINKS = [(12, 13), (12, 14)]            # ο πρώτος στρίβει σε οριζόντιο, ο
                                        # δεύτερος σε κάθετο
CAMS = [(-68, -94), (-68, -88)]


def dome_rec(hx, hy):
    r = bytearray(24)
    r[0] = hx & 0xFF
    r[1] = hy & 0xFF
    r[2] = 0                             # μικρός
    r[3] = 0                             # χωρίς δωμάτιο
    r[4] = 2                             # DS_ACTIVE
    r[5] = 255
    for k in range(8):
        r[8 + k] = 255                   # NO_MACH
    return r


def plant(m, sym, bank, addr, data):
    m.poke(sym["SNOOP_BK"], bank)
    m.poke(sym["SNOOP_AD"], addr & 0xFF)
    m.poke(sym["SNOOP_AD"] + 1, addr >> 8)
    m.poke(sym["SNOOP_N"], len(data))
    for k, b in enumerate(data):
        m.poke(sym["SNOOP_BUF"] + k, b)
    entry(m, sym, "DO_PLANT")


def snoop(m, sym, bank, addr, n):
    m.poke(sym["SNOOP_BK"], bank)
    m.poke(sym["SNOOP_AD"], addr & 0xFF)
    m.poke(sym["SNOOP_AD"] + 1, addr >> 8)
    m.poke(sym["SNOOP_N"], n)
    entry(m, sym, "DO_SNOOP")
    return bytes(m.peek(sym["SNOOP_BUF"] + k) for k in range(n))


def commit_and_render(sym, g, col):
    import mkcolony, palette, world as W
    from refrender import Canvas
    from cpc import CPC
    a = S.Assets()
    c, ag, plane = mkcolony.build()
    variants = a._tab("tile_variants")
    gd, gc = layout("G_dome_tbl"), layout("G_corr_tbl")
    m = boot(sym, g)

    for idx, hx, hy in PLANT:
        plant(m, sym, 0xC6, gd + 24 * idx, dome_rec(hx, hy))
        c.dome[idx * S.DOME_REC:(idx + 1) * S.DOME_REC] = dome_rec(hx, hy)
    c.n_dome = 15

    metal0 = m.peek(g + 3 * 2) | (m.peek(g + 3 * 2 + 1) << 8)
    slot = col.n_corr
    for aa, bb in LINKS:
        m.poke(sym["PLAN_A"], aa)
        m.poke(sym["PLAN_B"], bb)
        entry(m, sym, "DO_LINK")

    # --- 4: οι εγγραφές ---------------------------------------------------
    raw = snoop(m, sym, 0xC6, gc + S.CORR_REC * slot, S.CORR_REC * 4)
    c.corr[slot * S.CORR_REC:(slot + 4) * S.CORR_REC] = raw
    c.n_corr = slot + 4
    r0 = list(raw[0:5])
    r1 = list(raw[5:10])
    check(r0[0] == 12 and r0[1] == 13 and r1[0] == 255 and r1[1] == 255
          and r0[4] == 2 and r1[4] == 2,
          f"δύο εγγραφές για μία διαδρομή, η δεύτερη C_A=255: {r0} {r1}")
    ntile = r0[3] + r1[3] + raw[13] + raw[18]
    metal1 = m.peek(g + 3 * 2) | (m.peek(g + 3 * 2 + 1) << 8)
    check(metal0 - metal1 == 6 * ntile,
          f"πληρώθηκε ανά πλακίδιο: {ntile} x 6 = {metal0 - metal1}")

    deg = layout("G_rt_nodes")
    adj = layout("G_node_adj")
    d12 = m.peek(deg + 12)
    n12 = [m.peek(adj + 12 * 8 + k) for k in range(d12)]
    check(d12 == 2 and sorted(n12) == [13, 14],
          f"ο γράφος πήρε ΜΙΑ ακμή ανά διαδρομή: deg[12]={d12} {n12}")

    # ένα πλακίδιο που ΠΑΤΑΕΙ η διαδρομή, όχι το κέντρο του θόλου
    wt = tiles_of(c, 12, [(r0[2], r0[3]), (r1[2], r1[3])], 13)
    nocc = 0
    for tx, ty in set(wt):
        b = snoop(m, sym, 0xC4, 0x4000 + ((ty + 64) * 128) + (tx + 64), 1)[0]
        if b & 0x30:
            nocc += 1
    check(nocc == len(set(wt)),
          f"δεσμεύτηκαν {nocc} από {len(set(wt))} πλακίδια της διαδρομής")

    # --- 5: η εικόνα, εναντίον του Python renderer ------------------------
    bad_cam = []
    for cx, cy in CAMS:
        m.poke(sym["GOTO_X"], cx & 0xFF)
        m.poke(sym["GOTO_Y"], cy & 0xFF)
        m.poke(sym["GOTO_ST"], 0)
        entry(m, sym, "DO_GOTO")
        entry(m, sym, "DO_HIDE")
        cam = S.Camera((cx >> 1) - S.VIEW_TW // 2, (cy >> 1) - S.VIEW_TH // 2)
        cv = Canvas()
        for row in range(S.VIEW_TH):
            for col_ in range(S.VIEW_TW):
                tx, ty = cam.tx + col_, cam.ty + row
                b = plane.get(tx, ty)
                cls = W.cls_of(b)
                cv.opaque(a.rows(f"tile_{W.CLASS_NAMES[cls]}_"
                                 f"{plane.variant(tx, ty, variants)}"),
                          col_ * 4, row * 16)
                if cls == W.MOUNTAIN and W.res_of(b):
                    cv.masked(a.rows(f"ore_overlay_{W.decor_of(b) & 1}"),
                              col_ * 4, row * 16)
        S.draw_objects(cv, a, cam, c, ag=ag)
        ram = m.read_ram(0xC000, 0x4000)
        bad = 0
        for y in range(S.PLAY_LINES):
            hi = (y & 7) * 0x800
            base = (y >> 3) * 80
            for x in range(80):
                if ram[hi + ((base + x + 2 * cam.off) & 0x7FF)] != \
                        cv.buf[y * 80 + x]:
                    bad += 1
        gold = os.path.join(HERE, "golden", f"route_{cx}_{cy}")
        if bad:
            bad_cam.append((cx, cy, bad))
            cv.to_png(gold + "_ref.png", palette.pen_rgb(a.palette_fw))
            m.screenshot(gold + "_got.png", aspect=True)
        else:
            m.screenshot(gold + ".png", aspect=True)
    check(not bad_cam,
          "η στροφή ζωγραφίζεται εκεί που λέει η αναφορά, και στους δύο άξονες"
          + ("" if not bad_cam else f" — {bad_cam}"))


def layout(name):
    for line in open(os.path.join(ROOT, "build", "layout.asm"),
                     encoding="utf-8"):
        if line.startswith(name + " ") or line.startswith(name + "\t"):
            return int(line.split("#")[1].strip(), 16)
    raise KeyError(name)


if __name__ == "__main__":
    sys.exit(main())
