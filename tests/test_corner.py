#!/usr/bin/env python3
"""Οι γωνίες των διαδρόμων (βήμα 129, DESIGN §8.4, tools/corner.py).

Ο παίκτης: «θέλω γωνίες για τους διαδρόμους ώστε να φαίνονται σωστοί, αν δεν
είναι τελείως διαγώνιοι». Η στροφή διαγώνιος -> άξονας ζωγραφίζεται με λοξή
ένωση: η διαγώνιος ως τη γραμμή που διχοτομεί τη γωνία, ο άξονας από εκεί.

  1. Οι τρεις λωρίδες του tools/corner.py, με τον κανόνα του περιγράμματος,
     ΕΙΝΑΙ τα corr_dr, corr_h και corr_v. Αρνητικό: η διαγώνια ένα pixel δεξιά.
  2. Το tools/scene.py ζωγραφίζει την ένωση σε ΚΑΘΕ στροφή με δύο ή
     περισσότερα διαγώνια και τρία ή περισσότερα αξονικά (ως εκεί φτάνει το
     παράθυρο της ένωσης): ως 30 μισά tiles σε κάθε άξονα, κάθε
     μέγεθος και στις δύο άκρες, και οι τέσσερις ζυγότητες της αφετηρίας. Γύρω
     από τη στροφή το σχήμα της ένωσης (καθρεφτισμένο ανά διαγώνιο), αλλού τα
     πλακίδια όπως ήταν, pixel προς pixel, και τίποτα παραπάνω. Αρνητικά: το
     τελευταίο διαγώνιο ολόκληρο (η ουρά), χωρίς το μπάλωμα ή το σχέδιο της
     κάθετης γωνίας, και ένα κάθετο που ξεκινά από το πρώτο του πλακίδιο (το
     κοτσάνι).
  3. Ο Z80 ζωγραφίζει ό,τι η αναφορά, byte προς byte, σε οκτώ σκηνές — οι
     τέσσερις διαγώνιοι, η καθεμία προς οριζόντιο και προς κάθετο, με δύο
     θόλους μεγέθους m. Τις κοντές στροφές (ένα πλακίδιο ως τον θόλο) τις
     συγκρίνει το test_object, μαζί με τα pixels των αρμών τους. Αρνητικά: το
     τελευταίο διαγώνιο ολόκληρο, χωρίς το κομμένο διαγώνιο, το αξονικό από
     το πρώτο του πλακίδιο, τα σχέδια χωρίς καθρέφτισμα.
  4. Το κόστος: ένας διάδρομος με στροφή (ob_corr), με τη γωνία και με τον
     Z80 πειραγμένο ώστε να ζωγραφίζει όπως ως το βήμα 128.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/vasilhs/cpcemu")

import corner                                                           # noqa: E402
import route                                                            # noqa: E402
import scene as S                                                       # noqa: E402

FAIL = []
# Το κόστος ενός διαδρόμου με στροφή, σε µs, απέναντι στο βήμα 128: η γωνία
# ΚΟΣΤΙΖΕΙ ΛΙΓΟΤΕΡΟ (μετρημένο -315 ως -1.876), και το ταβάνι το κρατά.
COST_SLACK = -280


def check(ok, msg):
    print(("OK " if ok else "ΛΑΘΟΣ ") + msg)
    if not ok:
        FAIL.append(msg)


# --- 1. οι λωρίδες -----------------------------------------------------------

def bands():
    try:
        corner.check_bands()
        ok = True
    except AssertionError as e:
        ok = False
        print(e)
    check(ok, "οι τρεις λωρίδες του tools/corner.py, με το περίγραμμα όπου το "
              "σχήμα τελειώνει, είναι τα corr_dr, corr_h και corr_v")
    keep = corner._in_d
    corner._in_d = lambda px, ln: keep(px - 1, ln)
    try:
        corner.check_bands()
        neg = False
    except AssertionError:
        neg = True
    finally:
        corner._in_d = keep
    check(neg, "ΑΡΝΗΤΙΚΟ: η διαγώνια λωρίδα ένα pixel δεξιά δεν είναι το corr_dr")


# --- 2. η αναφορά ζωγραφίζει την ένωση ------------------------------------

def colony(sa, sb, a_at, b_at, side, runs):
    c = S.Colony()
    pts = ((a_at, sa), (b_at, sb))
    if side == 1:
        pts = pts[::-1]
    for i, ((x, y), s_) in enumerate(pts):
        r = bytearray(S.DOME_REC)
        r[S.D_CX], r[S.D_CY], r[S.D_SIZE], r[S.D_STATE] = x & 255, y & 255, s_, S.DS_ACTIVE
        r[5] = 255
        for k in range(8):
            r[S.D_MACH + k] = S.NO_MACH
        c.dome[i * S.DOME_REC:(i + 1) * S.DOME_REC] = r
    c.n_dome = 2
    for k, (d, n) in enumerate(runs):
        rec = [0, 1, d, n, S.DS_ACTIVE] if k == 0 else [255, 255, d, n, S.DS_ACTIVE]
        c.corr[k * 5:(k + 1) * 5] = bytes(rec)
    c.n_corr = len(runs)
    return c


def drawn(a, c):
    """{(px, γραμμή): pen} του διαδρόμου 0 όπως τον ζωγραφίζει το scene, με
    την κάμερα στο 0 (συντεταγμένες χωρίς όρια)."""
    from refrender import unpack_pens
    out = {}

    def put(canvas, rows, x, y, masked, clip):
        for dy, r in enumerate(rows):
            for b in range(len(r) // 2):
                m, v = r[2 * b], r[2 * b + 1]
                pv = unpack_pens(v)
                for k, bit in enumerate((0xAA, 0x55)):
                    if not m & bit:
                        out[(2 * (x + b) + k, y + dy)] = pv[k]
    keep = S.blit
    S.blit = put
    try:
        S.draw_corridor(None, a, S.Camera(), c, 0, S.Clip())
    finally:
        S.blit = keep
    return out


def plain(a, c):
    """Τα πλακίδια όπως ως το βήμα 128: (pixels, (lastx, lasty), d0, d1)."""
    from refrender import unpack_pens
    cam = S.Camera()
    dr, n = c.c(0, S.C_DIR), c.c(0, S.C_LEN)
    fx, fy, qw, qh, sz = S.dome_frame(a, cam, c, 0)
    px = a.conn_points[sz * 16 + dr * 2]
    py = a.conn_points[sz * 16 + dr * 2 + 1]
    x, y = S.corr_origin(fx + px, fy + py, dr, qw, qh, fx, fy, sz)
    sx, sy = S.CORR_STEP[dr]
    tiles = []
    for _ in range(n):
        tiles.append((S.CORR_SPR[dr & 3], x, y))
        lastx, lasty = x, y
        x, y = x + sx, y + sy
    d1 = c.c(1, S.C_DIR)
    x, y = S.corr_bend(lastx, lasty, sx, sy, d1)
    vx, vy = S.CORR_STEP[d1]
    for _ in range(c.c(1, S.C_LEN)):
        tiles.append((S.CORR_SPR[d1 & 3], x, y))
        x, y = x + vx, y + vy
    out = {}
    for name, x, y in tiles:
        for dy, r in enumerate(a.rows(name)):
            for b in range(len(r) // 2):
                m, v = r[2 * b], r[2 * b + 1]
                pv = unpack_pens(v)
                for k, bit in enumerate((0xAA, 0x55)):
                    if not m & bit:
                        out[(2 * (x + b) + k, y + dy)] = pv[k]
    return out, (lastx, lasty), dr, d1


def goal(a, c):
    """Ο,τι πρέπει να ζωγραφίζεται: τα πλακίδια όπως ήταν, και στα κελιά της
    ένωσης (corner.mitre, καθρεφτισμένα ανά διαγώνιο) το σχήμα της."""
    old, (lx, ly), d0, d1 = plain(a, c)
    kind = "h" if d1 in (2, 6) else "v"
    shape, cells = corner.mitre(kind)
    west, north = d0 in (5, 7), d0 in (1, 7)

    def at(p):
        return (2 * lx + (15 - p[0] if west else p[0]), ly + (15 - p[1] if north else p[1]))
    cells = {at(p) for p in cells}
    out = {p: v for p, v in old.items() if p not in cells}
    out.update({at(p): v for p, v in shape.items()})
    return out


def every_bend(span=30):
    """Οι στροφές με δύο ή περισσότερα διαγώνια και τρία ή περισσότερα
    αξονικά: το παράθυρο της ένωσης (corner.WIN) φτάνει ως το τρίτο αξονικό, και
    πιο κοντά στον θόλο ο διάδρομος τελειώνει πριν από αυτό. Τις κοντές τις
    ελέγχει το test_object, απέναντι στην αναφορά."""
    for sa in range(3):
        for sb in range(3):
            for ox in (0, 1):
                for oy in (0, 1):
                    for dx in range(-span, span + 1, 2):
                        for dy in range(-span, span + 1, 2):
                            p = route.plan(ox, oy, sa, ox + dx, oy + dy, sb)
                            if not p or len(p[1]) != 2:
                                continue
                            side, runs = p
                            if runs[0][1] < 2 or runs[1][1] < 3:
                                continue
                            yield sa, sb, (ox, oy), (ox + dx, oy + dy), side, runs


def shape(a):
    n, bad, kinds = 0, [], {}
    for sa, sb, pa, pb, side, runs in every_bend():
        c = colony(sa, sb, pa, pb, side, runs)
        got, want = drawn(a, c), goal(a, c)
        n += 1
        kinds[(runs[0][0], runs[1][0])] = kinds.get((runs[0][0], runs[1][0]), 0) + 1
        if got != want:
            bad.append((sa, sb, pa, pb, runs,
                        sum(1 for p in set(got) | set(want) if got.get(p) != want.get(p))))
    check(not bad and len(kinds) == 8,
          f"η αναφορά ζωγραφίζει την ένωση σε {n} στροφές, και τις οκτώ "
          f"({', '.join(f'{d0}->{d1}: {k}' for (d0, d1), k in sorted(kinds.items()))})"
          + (f" — {len(bad)} διαφέρουν, π.χ. {bad[:2]}" if bad else ""))
    # αρνητικά: με το scene πειραγμένο, κάποιες στροφές διαφέρουν
    sample = [b for i, b in enumerate(every_bend()) if i % 7 == 0]

    def differ():
        k = 0
        for sa, sb, pa, pb, side, runs in sample:
            c = colony(sa, sb, pa, pb, side, runs)
            if drawn(a, c) != goal(a, c):
                k += 1
        return k
    for label, attr, val in (("το τελευταίο διαγώνιο ολόκληρο (η ουρά)", "H_ROWS", 16),):
        keep = getattr(corner, attr)
        setattr(corner, attr, val)
        try:
            k = differ()
        finally:
            setattr(corner, attr, keep)
        check(k > 0, f"ΑΡΝΗΤΙΚΟ: με {label} διαφέρουν {k} από {len(sample)} στροφές")
    keep = S.corner_rows
    S.corner_rows = lambda kind, orient: [bytes([0xFF, 0]) * corner.patch(kind)[2]] * corner.patch(kind)[3]
    try:
        k = differ()
    finally:
        S.corner_rows = keep
    check(k > 0, f"ΑΡΝΗΤΙΚΟ: χωρίς το μπάλωμα και το σχέδιο της κάθετης γωνίας "
                 f"διαφέρουν {k} από {len(sample)} στροφές")
    keep = S.corr_bend
    # το κάθετο από το πρώτο του πλακίδιο: η αφετηρία του ένα βήμα πίσω
    S.corr_bend = lambda lx, ly, sx, sy, d1: (
        keep(lx, ly, sx, sy, d1)[0] - S.CORR_STEP[d1][0] * (d1 in (0, 4)),
        keep(lx, ly, sx, sy, d1)[1] - S.CORR_STEP[d1][1] * (d1 in (0, 4)))
    try:
        k = differ()
    finally:
        S.corr_bend = keep
    check(k > 0, f"ΑΡΝΗΤΙΚΟ: με το κάθετο από το πρώτο του πλακίδιο (το κοτσάνι) "
                 f"διαφέρουν {k} από {len(sample)} στροφές")


# --- 3. ο Z80 εναντίον της αναφοράς -------------------------------------------

CENTRE = (8, 6)


def scenes():
    """Οκτώ στροφές γύρω από το CENTRE: (όνομα, colony, κάμερα)."""
    out = []
    for d0 in (1, 3, 5, 7):
        for axial in ("h", "v"):
            found = None
            for dy in range(-20, 21, 2):
                for dx in range(-24, 25, 2):
                    p = route.plan(*CENTRE, 1, CENTRE[0] + dx, CENTRE[1] + dy, 1)
                    if not p or p[0] != 0 or len(p[1]) != 2:
                        continue
                    (e0, n0), (e1, n1) = p[1]
                    if e0 == d0 and (e1 in (2, 6)) == (axial == "h") and n0 >= 2 and n1 >= 2:
                        found = (dx, dy, p[1])
                        break
                if found:
                    break
            dx, dy, runs = found
            c = colony(1, 1, CENTRE, (CENTRE[0] + dx, CENTRE[1] + dy), 0, runs)
            cam = S.Camera((CENTRE[0] + dx // 2 >> 1) - S.VIEW_TW // 2,
                           (CENTRE[1] + dy // 2 >> 1) - S.VIEW_TH // 2)
            out.append((f"{S.DIRS[d0]} -> {'οριζόντιο' if axial == 'h' else 'κάθετο'} "
                        f"{runs}", c, cam))
    return out


def z80(a):
    import test_object as TO
    import mkcolony
    sym = TO.build()
    _, ag, plane = mkcolony.build()
    variants = a._tab("tile_variants")
    sc = scenes()
    refs = []
    bad = []
    for name, c, cam in sc:
        ref = bytes(TO.reference(a, c, ag, plane, cam, variants).buf[:S.PLAY_LINES * S.SCR_W])
        got, m = TO.shoot_colony(sym, c, cam)
        refs.append(ref)
        n = sum(1 for x, y in zip(got, ref) if x != y)
        if n:
            bad.append((name, n))
            m.screenshot(os.path.join(HERE, "golden", f"corner_got_{len(refs)}.png"), aspect=True)
    check(not bad, f"ο Z80 ζωγραφίζει τις οκτώ γωνίες όπως η αναφορά, byte προς byte: "
                   + ", ".join(n for n, _, _ in sc) + (f" — λάθος {bad}" if bad else ""))

    from cpc import CPC
    m = CPC()
    m.run_frames(60)
    m.quickload(TO.SNA, start=False)

    def find(name, pat, span=320):
        k = bytes(m.read_ram(sym[name], span)).find(bytes(pat))
        assert k >= 0, f"δεν βρέθηκε το {pat} στο {name}"
        return sym[name] + k
    oc_n = sym["OC_N"]
    dec_n = [0x21, oc_n & 255, oc_n >> 8, 0x35]          # ld hl,oc_n · dec (hl)
    i_pre = find("CN_PRE", dec_n) + 3
    # ld hl,oc_n · ld a,(hl) · or a · jr z · dec (hl): το μήκος 0 δεν γίνεται 255
    i_post = find("CN_POST", [0x21, oc_n & 255, oc_n >> 8, 0x7E, 0xB7, 0x28]) + 7
    mv, put = sym["OB_MOVE"], sym["OB_PUT"]
    i_mv = find("CN_POST", [0xCD, mv & 255, mv >> 8, 0x21, oc_n & 255])
    i_c = find("CN_POST", [0xCD, put & 255, put >> 8])   # το πλακίδιο της γωνίας
    i_or = find("CN_POST", [0x79, 0xE6, 0x02]) + 2   # ld a,c · and 2: το κάθετο
    au = sym["OB_ADDU"]
    i_w = find("CN_POST", [0x78, 0xCD, au & 255, au >> 8]) + 1   # ld a,b · call ob_addu
    neg = [("το τελευταίο διαγώνιο ολόκληρο (χωρίς το dec του cn_pre)", [(i_pre, 0)]),
           ("το κομμένο διαγώνιο σβησμένο (nop αντί για call ob_put)",
            [(i_c + k, 0) for k in range(3)]),
           ("το αξονικό από το πρώτο του πλακίδιο",
            [(i_mv + k, 0) for k in range(3)] + [(i_post, 0)]),
           ("τα σχέδια χωρίς κάθετο καθρέφτισμα (and 0)", [(i_or, 0)]),
           ("τα δυτικά με το ανατολικό σχέδιο (χωρίς το ob_addu)",
            [(i_w + k, 0) for k in range(3)])]
    for label, patch in neg:
        n = sum(1 for (_, c, cam), ref in zip(sc, refs)
                if TO.shoot_colony(sym, c, cam, patch)[0] != ref)
        check(n > 0, f"ΑΡΝΗΤΙΚΟ: με {label} διαφέρουν {n} σκηνές")
    return sym, sc, (i_pre, i_post, i_mv, i_c)


# --- 4. το κόστος -------------------------------------------------------------

def cost(sym, sc, at):
    """µs ενός ob_corr (διάδρομος 0) σε κάθε σκηνή, με τη γωνία και όπως ως το
    βήμα 128: το cn_pre χωρίς το dec, το cn_post χωρίς το πλακίδιο της γωνίας,
    το αξονικό από το πρώτο πλακίδιο, και κανένα μπάλωμα (ret πριν από αυτό)."""
    import test_object as TO
    i_pre, i_post, i_mv, i_c = at
    oc = sym["OB_CORR"]
    probe = 0x3E40
    code = bytes([0xF3, 0x31, 0x00, 0x01, 0x01, 0xC6, 0x7F, 0xED, 0x49,   # η 6 μέσα
                  0x3E, 0x00, 0xCD, oc & 255, oc >> 8, 0x18, 0xFE])

    def one(c, cam, patch):
        _, m = TO.shoot_colony(sym, c, cam, patch)
        m.write_ram(probe, code)
        m.set_pc(probe)
        end, t = probe + len(code) - 2, 0
        while not (end <= m.pc <= end + 1):
            m.run_us(1)
            t += 1
        return t
    # ως το 128: το μπάλωμα παραλείπεται με ret στη θέση του jp ob_put
    from cpc import CPC
    m = CPC()
    m.run_frames(60)
    m.quickload(TO.SNA, start=False)
    put = sym["OB_PUT"]
    pin = sym["OB_PUT_IN"]
    raw = bytes(m.read_ram(sym["CN_POST"], 300))
    k = raw.rfind(bytes([0xC3, pin & 255, pin >> 8]))
    assert k >= 0, "δεν βρέθηκε το jp ob_put_in"
    i_ret = sym["CN_POST"] + k
    old = [(i_pre, 0), (i_ret, 0xC9)] + [(i_c + j, 0) for j in range(3)] \
        + [(i_mv + j, 0) for j in range(3)] + [(i_post, 0)]
    rows = []
    for name, c, cam in sc:
        rows.append((name, one(c, cam, ()), one(c, cam, old)))
    worst = max(n - o for _, n, o in rows)
    for name, n, o in rows:
        print(f"    {name:42s} {n:5d} us (ως το 128: {o:5d}, {n - o:+d})")
    check(worst <= COST_SLACK,
          f"ένας διάδρομος με στροφή κοστίζει με τη γωνία το πολύ {worst:+d} us "
          f"απέναντι στο βήμα 128 (ταβάνι {COST_SLACK:+d}): η γωνία είναι φθηνότερη "
          f"από τα πλακίδια που αντικαθιστά")


def main():
    a = S.Assets()
    bands()
    shape(a)
    sym, sc, at = z80(a)
    cost(sym, sc, at)
    if FAIL:
        print(f"\nΑΠΟΤΥΧΙΑ — {len(FAIL)}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
