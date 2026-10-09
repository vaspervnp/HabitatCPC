#!/usr/bin/env python3
"""Διάδρομοι ανάμεσα σε θόλους που έβαλε ο ΠΑΙΚΤΗΣ (DESIGN §9.4, §15).

Ως το βήμα 36 κανένας διάδρομος με διαγώνιο δεν χτιζόταν στο παιχνίδι. Η
διαγώνιος ξεκινά DIAG_K βήματα από το κέντρο, εκεί που ξεφεύγει ο κυκλικός
δακτύλιος, και τα πρώτα της tiles είναι η γωνία του ΤΕΤΡΑΓΩΝΟΥ αποτυπώματος —
που το bd_commit σφραγίζει κατειλημμένη. Το tests/test_route.py δεν το έβλεπε
ποτέ: εκεί οι θόλοι φυτεύονται στον πίνακα χωρίς κατοχή. Εδώ μπαίνουν από τη
διεπαφή, όπως τους βάζει ο άνθρωπος, και ο διάδρομος ζητιέται με τον κέρσορα.

  ΣΑΡΩΣΗ    Γεωμετρίες με διαγώνιο προς τις τέσσερις κατευθύνσεις, με στροφή
            σε οριζόντιο και σε κάθετο, καθαρές διαγώνιες που καταλήγουν στη
            γωνία του προορισμού, και τα τρία μεγέθη στην αφετηρία. Ο Z80
            συμφωνεί με το tools/route.py στη διαδρομή, και ο έλεγχος λέει 0
            κακά tiles — ενώ η διαδρομή ΠΕΡΝΑ από κατειλημμένα tiles των δύο
            άκρων, αλλιώς η δοκιμή δεν δοκιμάζει τίποτα.
  ΑΡΝΗΤΙΚΑ  Η εξαίρεση είναι ΜΟΝΟ για τα δύο άκρα: μια πέτρα στη μέση της
            διαδρομής και ένας τρίτος θόλος πάνω της την κόβουν. Και με τον
            παλιό έλεγχο (το crk_in κομμένο) η σάρωση ξαναβρίσκει τις γωνίες.
  ΧΤΙΣΙΜΟ   Ο διάδρομος χτίζεται, πληρώνεται, και η οθόνη είναι byte προς
            byte η πλήρης σχεδίαση — από το βήμα 96 με τους αρμούς στα δύο
            άκρα, πάνω από τα κελύφη. Και ο προορισμός παίρνει αρμό στην
            αντίθετη του ΤΕΛΕΥΤΑΙΟΥ τρεξίματος (ως το 95 πόρτα): ως το βήμα 36
            την έπαιρνε στην αντίθετη της διαγωνίου, όπου δεν φτάνει τίποτα —
            το ίδιο λάθος στον Z80 και στην αναφορά σε Python, γι' αυτό η
            σύγκρισή τους περνούσε.
  ΣΕΙΡΑ-ΣΕΙΡΑ  Από το βήμα 37 η διαγώνιος βγαίνει μία σειρά tiles ανά γύρο
            (DK_CROW), όσες σειρές της φαίνονται, και ο κέρσορας την περιμένει.
            Σε κάθε καρέ ό,τι ήδη φαινόταν πρέπει να μένει· ένας κέρσορας πάνω
            σε σειρές που δεν βγήκαν ακόμη δεν πρέπει να αφήνει ίχνος· και μια
            προεπισκόπηση που κρύβεται δεν πρέπει να αφήνει σημάδια — και στις
            ΒΟΡΕΙΕΣ στροφές σε οριζόντιο, που ως το βήμα 40 άφηναν ένα.
  ΑΡΧΕΙΟ    Η προεπισκόπηση γράφει στο αρχείο του φαντάσματος ΑΚΡΙΒΩΣ το
            πλαίσιο του κέρσορα (56) και ένα σημάδι (12) ανά ορατό tile της
            διαδρομής. Η χειρότερη, από εξαντλητική αναζήτηση στο tools/route.py
            (21.836 γεωμετρίες, κάθε κάμερα που δείχνει τον προορισμό), είναι
            21 ορατά tiles: 308 bytes από τα 1.600 (βήμα 40).

Το έδαφος καθαρίζεται με το χέρι στην τράπεζα 4 πριν μπουν οι θόλοι: το
μεγαλύτερο καθαρό τετράγωνο του χάρτη είναι 14 tiles, πάνω στην αποικία, και
μια διαγώνιος ανάμεσα σε δύο L θέλει 20.

Από το βήμα 85 κάθε θόλος θέλει κτίσμα ως 12 tiles μακριά και παίρνει μόνος του
τους διαδρόμους του (src/link.asm). Εδώ ο κανόνας σβήνει (balance.no_link): το
χωράφι είναι μακριά από την αποικία, και ο διάδρομος που δοκιμάζεται είναι ο
χειροκίνητος. Τον κανόνα τον ελέγχει το tests/test_reach.py.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/vasilhs/cpcemu")

import balance as B                                                # noqa: E402
import route                                                       # noqa: E402
import scene as S                                                  # noqa: E402
import test_reveal as R                                            # noqa: E402
import world as W                                                  # noqa: E402
from cpc import KEY_SPACE, KEY_RIGHT, JOY_FIRE                     # noqa: E402

FAIL = []
WID = [4, 6, 8]                          # πλευρά του αποτυπώματος σε tiles
W_OCC = 0x30
CORR_REC = 5
METAL_PER_TILE = 6                       # ο κατάλογος του src/build.asm
LAID_MAX = 160
FLICKER_MAX = 24                         # μετρημένο 13 (βήμα 37)· με έδαφος 96,
                                         # 51 από το ευρετήριο του βήματος 39·
                                         # 18 και 96 με τέσσερα δείγματα το καρέ·
                                         # 9 και 88 στο βήμα 96, με τους
                                         # διαδρόμους κάτω από τα κελύφη
FLICKER_PER = 4                          # δείγματα ανά καρέ (βήμα 80)
FIELD = (-50, 20)                        # το καθαρό χωράφι, μακριά από την αποικία


def check(ok, msg):
    print(("OK " if ok else "ΛΑΘΟΣ ") + msg)
    if not ok:
        FAIL.append(msg)


def layout(name):
    for line in open(os.path.join(ROOT, "build", "layout.asm"), encoding="utf-8"):
        if line.startswith(name):
            return int(line.split("#")[1].split()[0], 16)
    raise KeyError(name)


def tiles(f, fs, t, runs):
    """Τα tiles που πατά η διαδρομή, το καθένα μία φορά, με τη σειρά του
    cr_walk. Η ίδια γεωμετρία με το tiles_of του tests/test_route.py."""
    btx, bty = f[0] >> 1, f[1] >> 1
    ka, ra = route.DIAG_K[fs], route.RADIUS[fs] // 2
    sx, sy = (t[0] - f[0]) // 2, (t[1] - f[1]) // 2
    Sd, Td = abs(sx), abs(sy)
    ux, uy = (sx > 0) - (sx < 0), (sy > 0) - (sy < 0)
    out = []
    d0, n0 = runs[0]
    if d0 & 1:
        for i in range(n0):
            j = ka + i
            lx, ly = ux * j, uy * j
            t1, t2 = (((lx - 1, ly - 1), (lx, ly)) if ux == uy
                      else ((lx - 1, ly), (lx, ly - 1)))
            # Δύο διαδοχικά πλακίδια μοιράζονται ένα tile: το «πίσω» μόνο στο
            # πρώτο βήμα, μετά μόνο το «μπροστινό» (T2 αν ux > 0, T1 αλλιώς).
            back, front = (t1, t2) if ux > 0 else (t2, t1)
            out += ([back] if i == 0 else []) + [front]
        if len(runs) > 1:
            d1, n1 = runs[1]
            vx, vy = route.DIR_U[d1]
            # Η στροφή δεν ξαναπερνά tile της διαγωνίου: κατεβαίνοντας είναι το
            # τελευταίο μπροστινό, ανεβαίνοντας προς οριζόντιο το τελευταίο
            # «πίσω» (βήμα 40 — ως τότε η αναφορά κοίταζε μόνο το πρώτο).
            if vx:
                c, r = ux * Td - (1 if ux > 0 else 0), uy * Td
                for _ in range(n1):
                    if (c, r) not in out:
                        out.append((c, r))
                    c += vx
            else:
                r, c = uy * (Sd - 1) - (1 if uy < 0 else 0), ux * Sd
                for _ in range(n1):
                    if (c, r) not in out:
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


def rows(f, fs, runs, cam):
    """Οι σειρές που σπρώχνει το crr_rows, [(x0, y)] σε tiles του κόσμου,
    τρία tiles η καθεμία, μόνο όσες φαίνονται — και αν καλύπτουν ό,τι αγγίζουν
    τα πλακίδια.

    Τα δύο από ΧΩΡΙΣΤΟΥΣ δρόμους: η λωρίδα με τον τύπο του Z80 (x0 = ux*v - 1,
    ένα αριστερότερα για «/»), τα αγγίγματα από τη γεωμετρία του sprite — το
    πλακίδιο j πιάνει τις στήλες ux*j - 1, ux*j και μισό tile πάνω και κάτω από
    τη γραμμή uy*j (tools/route.py, origins).
    """
    d0, n0 = runs[0]
    if not d0 & 1:
        return [], True
    btx, bty = f[0] >> 1, f[1] >> 1
    ux, uy = route.DIR_U[d0]
    ka = route.DIAG_K[fs]
    touch = {}                               # σειρά -> στήλες
    for j in range(ka, ka + n0):
        for r in (uy * j - 1, uy * j):
            touch.setdefault(r, set()).update((ux * j - 1, ux * j))
    out, ok = [], True
    v0 = ka - (uy > 0)
    for v in range(v0, v0 + n0 + 1):
        r = uy * v
        x0 = ux * v - 1 - (ux != uy)
        ok &= touch.pop(r, {None}) <= set(range(x0, x0 + 3))
        out.append((btx + x0, bty + r))
    ok &= not touch
    return [(x, y) for x, y in out
            if 0 <= y - cam[1] < S.VIEW_TH
            and 0 <= x - cam[0] + 2 < S.VIEW_TW + 2], ok


def inside(t, c, size):
    x0, y0 = (c[0] - WID[size]) >> 1, (c[1] - WID[size]) >> 1
    return x0 <= t[0] < x0 + WID[size] and y0 <= t[1] < y0 + WID[size]


class Pair:
    """Δύο θόλοι από τη διεπαφή, και η διεπαφή στο LINK με τον a διαλεγμένο.

    `dx, dy` = η απόσταση των ΠΑΝΩ-ΑΡΙΣΤΕΡΩΝ γωνιών σε tiles· τα κέντρα
    απέχουν dx + (wb - wa)/2.
    """

    def __init__(self, sym, g, sa, sb, dx, dy, third=None, patch=None):
        self.sym, self.g, self.sa, self.sb = sym, g, sa, sb
        wa, wb = WID[sa], WID[sb]
        wide = max(wa, dx + wb) - min(0, dx) + 2
        high = max(wa, dy + wb) - min(0, dy) + 2
        ox, oy = FIELD[0] + 1 - min(0, dx), FIELD[1] + 1 - min(0, dy)
        self.ca = (2 * ox + wa, 2 * oy + wa)
        self.cb = (2 * (ox + dx) + wb, 2 * (oy + dy) + wb)
        G = self.G = R.Game(sym, g)
        b4 = G.bank(4)
        for j in range(high):
            for i in range(wide):
                b4[W.index(FIELD[0] + i, FIELD[1] + j)] = 0
        for k, v in (patch or {}).items():
            G.m.poke(k, v)
        B.no_link(G.m, sym)                  # ο διάδρομος ζητιέται με το χέρι
        G.camera(FIELD[0] + wide // 2 - 10, FIELD[1] + high // 2 - 5)
        B.build(G.m, sym, sa, g + 6, at=self.ca, room=R.R_FACTORY)
        B.build(G.m, sym, sb, g + 6, at=self.cb, room=R.R_FACTORY)
        if third:                            # (μέγεθος, πάνω-αριστερά από τον a)
            s, (tx, ty) = third
            B.build(G.m, sym, s, g + 6,
                    at=(2 * (ox + tx) + WID[s], 2 * (oy + ty) + WID[s]),
                    room=R.R_FACTORY)
        self.link()

    def link(self):
        G, m, sym = self.G, self.G.m, self.sym

        def tap(key):
            m.key_down(key)
            m.run_frames(5)
            m.key_up(key)
            m.run_frames(8)

        m.set_joystick_type(1)
        G.stick(0x20)
        G.stick(0x20)
        m.set_joystick_type(0)
        tap(KEY_SPACE)                  # -> ACT (βήμα 80)
        tap(KEY_SPACE)                  # -> MENU: το BUILD είναι πρώτο
        for _ in range(14):
            if m.peek(sym["UI_SEL"]) == R.I_CORR:
                break
            tap(KEY_RIGHT)
        m.key_up("\x01")
        m.set_joystick_type(1)
        G.stick(JOY_FIRE)                    # -> LINK
        m.poke(sym["CUR_HX"], self.ca[0] & 0xFF)
        m.poke(sym["CUR_HY"], self.ca[1] & 0xFF)
        G.stick(JOY_FIRE)                    # η αφετηρία
        m.set_joystick_type(0)
        self.node_a = m.peek(sym["LN_A"])
        self.aim()

    def aim(self):
        """Ο κέρσορας πάνω στον b — το ui_show ξαναϋπολογίζει τη διαδρομή,
        όπως σε κάθε βήμα του κέρσορα (uis_link -> ln_plan)."""
        m = self.G.m
        m.poke(self.sym["CUR_HX"], self.cb[0] & 0xFF)
        m.poke(self.sym["CUR_HY"], self.cb[1] & 0xFF)
        self.G.probe(["UI_HIDE", "UI_SHOW"])
        self.n = m.peek(self.sym["CR_N"])
        self.bad = m.peek(self.sym["UI_BAD"])
        runs = [(m.peek(self.sym["CR_D0"]), m.peek(self.sym["CR_L0"]))]
        if self.n > 1:
            runs.append((m.peek(self.sym["CR_D1"]), m.peek(self.sym["CR_L1"])))
        self.runs = runs if self.n else None
        self.frm = m.peek(self.sym["CR_FROM"])

    def ref(self):
        """(από τον a;, τρεξίματα, tiles της αναφοράς)"""
        r = route.plan(self.ca[0], self.ca[1], self.sa,
                       self.cb[0], self.cb[1], self.sb)
        if r is None:
            return None
        side, runs = r
        f, fs, t = ((self.ca, self.sa, self.cb) if side == 0
                    else (self.cb, self.sb, self.ca))
        return side, runs, tiles(f, fs, t, runs)

    def occupied(self, path):
        b4 = self.G.bank(4)
        return [p for p in path if b4[W.index(*p)] & W_OCC]


# --- ΣΑΡΩΣΗ -----------------------------------------------------------------
# (μέγεθος a, μέγεθος b, dx, dy) — σχόλιο: τι δοκιμάζει
SWEEP = [
    (0, 0, 10, 10),      # S -> S καθαρή διαγώνιος, γωνία και στα δύο άκρα
    (1, 1, 12, -12),     # M -> M καθαρή διαγώνιος, βορειοανατολικά
    (2, 2, -10, 10),     # L -> L: δύο tiles της γωνίας σε κάθε άκρο
    (0, 2, 10, 10),      # S -> L: καταλήγει στη γωνία του L
    (0, 0, 12, 6),       # διαγώνιος -> οριζόντιος
    (1, 0, -12, -8),     # το ίδιο, προς βορειοδυτικά
    (0, 0, 6, 12),       # διαγώνιος -> κάθετος
    (2, 1, 6, 12),       # από L, -> κάθετος
    (0, 0, 5, 3),        # η στροφή πέφτει ακριβώς στην πόρτα (n2 = 1)
    (2, 0, 8, 0),        # L δίπλα σε S: ξεκινά από τον b, και n2 = 1
    (0, 0, 8, 0),        # ευθύς: δούλευε και πριν, και πρέπει να δουλεύει
]


def sweep(sym, g, cases, patch=None):
    """Επιστρέφει [(case, ui_bad, κατειλημμένα tiles της διαδρομής)]."""
    out = []
    for c in cases:
        P = Pair(sym, g, *c, patch=patch)
        r = P.ref()
        if r is None:
            out.append((c, None, None, P))
            continue
        side, runs, path = r
        agree = P.runs == runs and (P.frm == P.node_a) == (side == 0)
        out.append((c, P.bad if agree else ("ΔΙΑΦΩΝΙΑ", P.runs, runs),
                    P.occupied(path), P))
    return out


def stone(sym, g):
    """Μια πέτρα στη μέση της διαγωνίου: ένα tile ΕΞΩ από τα δύο άκρα."""
    P = Pair(sym, g, 0, 0, 10, 10)
    _, runs, path = P.ref()
    mid = path[len(path) // 2]
    assert not inside(mid, P.ca, 0) and not inside(mid, P.cb, 0)
    P.G.bank(4)[W.index(*mid)] |= 0x10
    P.aim()
    check(path.count(mid) == 1 and P.bad == 1,
          f"ΑΡΝΗΤΙΚΟ: μια πέτρα στη μέση της διαγωνίου, στο {mid}, κόβει τη "
          f"διαδρομή — {P.bad} κακό tile")


def third(sym, g):
    """Ενας ΤΡΙΤΟΣ θόλος πάνω στη διαγώνιο: το αποτύπωμά του δεν είναι του
    διαδρόμου, όσο κι αν είναι κι αυτό αποτύπωμα θόλου."""
    P = Pair(sym, g, 0, 0, 14, 14, third=(0, (6, 6)))
    _, runs, path = P.ref()
    cc = (2 * (FIELD[0] + 1 + 6) + 4, 2 * (FIELD[1] + 1 + 6) + 4)
    on = [p for p in path if inside(p, cc, 0)]
    check(on and P.bad == len(on),
          f"ΑΡΝΗΤΙΚΟ: ένας τρίτος θόλος στη μέση της διαγωνίου την κόβει — "
          f"{P.bad} κακά, όσα tiles του περνά η διαδρομή ({len(on)})")


# --- ΧΤΙΣΙΜΟ ----------------------------------------------------------------
def build(sym, g, sa, sb, dx, dy, what, patch=None):
    """Χτίζει τον διάδρομο ως το τέλος της εμφάνισης. Με `patch`, μόνο τα
    λάθος bytes, οι γύροι και οι περισσότερες σειρές σε έναν, για αρνητικό
    δείγμα."""
    P = Pair(sym, g, sa, sb, dx, dy, patch=patch)
    G, m = P.G, P.G.m
    side, runs, path = P.ref()
    f, fs = (P.ca, sa) if side == 0 else (P.cb, sb)
    tbl = layout("G_corr_tbl") - 0x4000     # μέσα στην τράπεζα 6
    # Η ΠΡΟΣΟΜΟΙΩΣΗ ΣΤΑΜΑΤΑ πριν από το FIRE, για να μετριέται μόνο ο
    # διάδρομος. (Ως το βήμα 42 ήταν και αναγκαίο: ένας άποικος που άφηνε
    # θέση δακτυλίου στο μεταξύ άφηνε 2-7 λάθος bytes, §15.)
    on = G.still()
    c = G.canary()
    metal = m.peek(g + 6) | (m.peek(g + 7) << 8)
    slot = None
    b6 = G.bank(6)
    for k in range(96):
        if b6[tbl + k * CORR_REC + 4] == 0:
            slot = k
            break
    cam = tuple(v - 256 if v > 127 else v
                for v in (m.peek(sym["CAM_TX"]), m.peek(sym["CAM_TY"])))
    want_rows, geo = rows(f, fs, runs, cam)
    G.run(40_000)
    G.iters, G.pend = [], []
    m.set_joystick_type(1)
    G.stick(JOY_FIRE)                        # ο προορισμός: χτίζει
    m.set_joystick_type(0)
    # ΩΣ ΝΑ ΞΑΝΑΜΠΕΙ ΤΟ ΦΑΝΤΑΣΜΑ: οι σειρές της διαγωνίου βγαίνουν μία ανά
    # γύρο και ο κέρσορας περιμένει την τελευταία (ui_owed).
    G.run(4_000_000, until=lambda: m.peek(sym["RV_PEND"]) == 0
          and m.peek(sym["UI_OWED"]) == 0)
    laid = G.worst()
    alive = G.alive(c)
    done = m.peek(sym["RV_PEND"]) == 0 and m.peek(sym["UI_OWED"]) == 0
    gp = m.peek(sym["GH_PTR"]) | (m.peek(sym["GH_PTR"] + 1) << 8)
    bands = sum(1 for a, b in zip(G.pend, G.pend[1:]) if b < a)
    most = max((a - b for a, b in zip(G.pend, G.pend[1:])), default=0)
    pic, ref = G.truth()                     # το byte 0 είναι το κανάρινι
    bad = sum(1 for i, (a, b) in enumerate(zip(pic, ref)) if a != b and i)
    if patch:
        G.go(on)
        return bad, bands, most
    paid = metal - (m.peek(g + 6) | (m.peek(g + 7) << 8))
    rec = [bytes(b6[tbl + (slot + k) * CORR_REC:
                    tbl + (slot + k + 1) * CORR_REC]) for k in range(2)]
    node_a, node_b = rec[0][0], rec[0][1]
    want = [(rec[0][2], rec[0][3])] + ([(rec[1][2], rec[1][3])]
                                       if rec[1][0] == 255 and rec[1][4] else [])
    check(paid == METAL_PER_TILE * sum(n for _, n in runs) and want == runs,
          f"{what}: χτίστηκε — {[list(r) for r in rec[:len(want)]]}, "
          f"μέταλλο -{paid}")
    # ΜΕΤΡΗΜΕΝΟ: ήταν 160-220 ms ο γύρος του FIRE (βήμα 36), όσο μεγάλωνε το
    # τετράγωνο που ξαναζωγραφιζόταν. Το κανάρινι λέει ότι δεν ξαναζωγραφίστηκε
    # ολόκληρο το κάδρο (~700).
    check(alive and laid < LAID_MAX,
          f"{what}: κανάρινι {'ζει' if alive else 'ΝΕΚΡΟ'}, "
          f"{laid:.0f} ms ο χειρότερος γύρος (όριο {LAID_MAX}· ήταν ως 220)")
    check(geo and bands == len(want_rows) and most <= 1,
          f"{what}: η διαγώνιος βγήκε σε {bands} γύρους, το πολύ {most} σειρά "
          f"ανά γύρο — όσες σειρές της φαίνονται ({len(want_rows)}), και η "
          f"λωρίδα των τριών καλύπτει ό,τι αγγίζουν τα πλακίδια: "
          f"{'ναι' if geo else 'ΟΧΙ'}")
    # Ο κέρσορας είναι πάνω στον b, που μπορεί να πέφτει έξω από το κάδρο: η
    # κάμερα εδώ μπαίνει στη μέση του ζευγαριού, δεν τον ακολουθεί.
    seen = (0 <= (P.cb[0] >> 1) - cam[0] < S.VIEW_TW
            and 0 <= (P.cb[1] >> 1) - cam[1] < S.VIEW_TH)
    check(done and (gp != G.ghbuf) == seen,
          f"{what}: και μετά ο κέρσορας ξαναμπήκε — "
          + (f"{gp - G.ghbuf} bytes στο αρχείο του φαντάσματος" if seen
             else "έξω από το κάδρο, άδειο αρχείο"))
    check(bad == 0, f"{what}: η οθόνη είναι η πλήρης σχεδίαση, διάδρομος και "
                    f"αρμοί — {bad} λάθος bytes")
    # Ποιοι αρμοί: το dome_conn, ένα bit ανά κατεύθυνση (ως το 95 οι πόρτες).
    conn = sym["DOME_CONN"]
    da, db = m.peek(conn + node_a), m.peek(conn + node_b)
    joint_a, joint_b = runs[0][0], (runs[-1][0] + 4) & 7
    wrong = (runs[0][0] + 4) & 7
    check(da == 1 << joint_a and db == 1 << joint_b,
          f"{what}: αρμοί {da:08b} / {db:08b} — ο a στο {joint_a}, ο b στο "
          f"{joint_b}, την αντίθετη του τελευταίου τρεξίματος"
          + (f" (όχι στο {wrong})" if wrong != joint_b else ""))
    G.go(on)
    return laid


def trail(sym, g, sa, sb, dx, dy, patch=None):
    """Η προεπισκόπηση μιας διαγωνίου και μετά απόκρυψη: η οθόνη πρέπει να
    είναι η πλήρης σχεδίαση. Ως το βήμα 37 το cr_walk περνούσε ΔΥΟ φορές από
    το tile που μοιράζονται δύο διαδοχικά πλακίδια, το φάντασμα ζωγράφιζε το
    σημάδι του δύο φορές, η δεύτερη εγγραφή κρατούσε για «φόντο» το πρώτο
    σημάδι — και η αναίρεση, που πάει μπροστά, το έγραφε τελευταίο. Ο κέρσορας
    άφηνε πίσω του ένα σημάδι ανά βήμα διαγωνίου. Επιστρέφει τα λάθος bytes."""
    P = Pair(sym, g, sa, sb, dx, dy, patch=patch)
    G = P.G
    G.still()
    G.probe(["UI_HIDE"])
    hid = G.play()
    G.probe(["OB_CLIP_FULL", "VIEW_DRAW"])
    return sum(1 for a, b in zip(hid, G.play()) if a != b), P.runs


def north_patch(sym):
    """Το LD (crw_ly),BC του crw_h1 σε τέσσερα NOP: η βόρεια στροφή ξεχνά ότι
    το πρώτο tile του οριζόντιου το πέρασε ήδη η διαγώνιος."""
    at, ly = sym["CRW_H1"], sym["CRW_LY"]
    from cpc import CPC
    m = CPC()
    m.run_frames(60)
    assert m.quickload(R.T.COLONY, start=False)
    for k in range(40):
        if (m.peek(at + k) == 0xED and m.peek(at + k + 1) == 0x43
                and m.peek(at + k + 2) == ly & 0xFF and m.peek(at + k + 3) == ly >> 8):
            return {at + k + i: 0 for i in range(4)}
    raise SystemExit("δεν βρέθηκε το LD (crw_ly),BC στο crw_h1")


VW, VH = 20, 10                          # το κάδρο σε tiles
GH_FRAME, GH_MARK = 56, 12               # πλαίσιο κέρσορα 1x1, ένα σημάδι 2x4


def ghost_log(sym, g, sa, sb, dx, dy, cam=None):
    """(μετρημένο gh_ptr - GH_BUF, 56 + 12 x ορατά tiles, ορατά, κάμερα).

    Ο κέρσορας σε tile του προορισμού μέσα στο κάδρο — εκεί τον κρατά πάντα το
    παιχνίδι. Χωρίς κάμερα: εκείνη που δείχνει τα περισσότερα tiles."""
    P = Pair(sym, g, sa, sb, dx, dy)
    ts = P.ref()[2]
    wb = WID[sb]
    bx0, by0 = (P.cb[0] - wb) >> 1, (P.cb[1] - wb) >> 1
    foot = [(bx0 + i, by0 + j) for j in range(wb) for i in range(wb)]

    def seen(c):
        return [t for t in ts if 0 <= t[0] - c[0] < VW and 0 <= t[1] - c[1] < VH]
    if cam is None:
        cams = [(x, y) for y in range(by0 - VH + 1, by0 + wb)
                for x in range(bx0 - VW + 1, bx0 + wb)]
        cam = max(cams, key=lambda c: len(seen(c)))
    else:
        cam = (bx0 + cam[0], by0 + cam[1])
    cur = next(t for t in foot if 0 <= t[0] - cam[0] < VW and 0 <= t[1] - cam[1] < VH)
    G, m = P.G, P.G.m
    G.camera(*cam)
    m.poke(sym["CUR_HX"], (2 * cur[0] + 1) & 0xFF)
    m.poke(sym["CUR_HY"], (2 * cur[1] + 1) & 0xFF)
    G.probe(["UI_HIDE", "UI_SHOW"])
    got = (m.peek(sym["GH_PTR"]) | (m.peek(sym["GH_PTR"] + 1) << 8)) - G.ghbuf
    n = len(seen(cam))
    return got, GH_FRAME + GH_MARK * n, n, P.runs


def flicker(sym, g, terrain=False):
    """Ο,τι ήδη φαίνεται δεν σβήνει όσο βγαίνουν οι σειρές.

    Η οθόνη δειγματίζεται ΤΕΣΣΕΡΙΣ ΦΟΡΕΣ σε κάθε καρέ από το FIRE ως το
    τέλος της εμφάνισης. Με ένα δείγμα στο τέλος του καρέ η μέτρηση έβλεπε
    μία μόνο φάση: στο βήμα 80 ο βρόχος έφτασε στο FIRE λίγο αλλιώς (δύο
    SPACE ως τον κατάλογο, ένα tick του LOOK 21 µs φθηνότερο), το γυμνό
    έδαφος του αρνητικού έπεφτε πια ανάμεσα σε δύο δείγματα, και το αρνητικό
    έβγαζε 18 όσο και το θετικό. Με τέσσερα, το βήμα 79 και το 80 δίνουν το
    ίδιο: 18 και 96. Ενα byte που έχει ήδη την τελική του τιμή — από την αρχή, όπως
    οι θόλοι, ή από ένα προηγούμενο καρέ, όπως η στροφή που μπαίνει με το
    FIRE — και μετά τη χάνει, είναι κάτι που ο παίκτης είδε να σβήνει. Το
    «ούτε πριν ούτε μετά» δεν το πιάνει: γυμνό έδαφος εκεί που μόλις μπήκε ο
    οριζόντιος έχει ακριβώς την τιμή του «πριν». Με `terrain` το dh_crow
    ζωγραφίζει πρώτα το έδαφος (vr_tiles αντί για vr_clip), όπως στην πρώτη
    μορφή του βήματος 37. Επιστρέφει το χειρότερο καρέ σε bytes.
    """
    patch = None
    if terrain:
        at = sym["DH_CROW"]
        m0 = R.Game(sym, g).m
        clip = sym["VR_CLIP"]
        for k in range(48):
            if (m0.peek(at + k) == 0xCD and m0.peek(at + k + 1) == clip & 0xFF
                    and m0.peek(at + k + 2) == clip >> 8):
                break
        else:
            raise SystemExit("δεν βρέθηκε το CALL VR_CLIP στο dh_crow")
        tiles_ = sym["VR_TILES"]
        patch = {at + k + 1: tiles_ & 0xFF, at + k + 2: tiles_ >> 8}
    P = Pair(sym, g, 0, 2, 12, 6, patch=patch)
    G, m = P.G, P.G.m
    on = G.still()
    G.probe(["UI_HIDE"])                     # «πριν» = χωρίς την προεπισκόπηση
    before = G.play()
    frames = []
    m.set_joystick_type(1)
    m.joystick(JOY_FIRE)
    for k in range(400 * FLICKER_PER):
        m.run_us(20000 // FLICKER_PER)
        if k == 4 * FLICKER_PER:
            m.joystick(0)
        frames.append(G.play())
        if k > 10 * FLICKER_PER and m.peek(sym["RV_PEND"]) == 0 \
                and m.peek(sym["UI_OWED"]) == 0:
            break
    m.set_joystick_type(0)
    m.run_frames(4)
    after = G.play()
    G.go(on)
    reached = [b == a for b, a in zip(before, after)]
    worst = 0
    for fr in frames:
        lost = 0
        for i, (f, a) in enumerate(zip(fr, after)):
            if f == a:
                reached[i] = True
            elif reached[i]:
                lost += 1
        worst = max(worst, lost)
    return worst


def ghost_over(sym, g, cut=False):
    """Ο παίκτης φέρνει τον κέρσορα πάνω στη διαγώνιο ΠΡΙΝ βγουν οι σειρές της.

    Το ui_show ξεχρεώνει το φάντασμα αμέσως (ui_owed = 0) και το ζωγραφίζει
    εκεί που δεν έχει έρθει ακόμη ο διάδρομος. Κάθε σειρά που περνά από κάτω
    πρέπει να το σηκώσει (dt_ghost_rect) — αλλιώς, όταν ο κέρσορας φύγει, η
    αναίρεση γράφει πίσω το έδαφος ΧΩΡΙΣ διάδρομο. Επιστρέφει τα λάθος bytes.
    """
    P = Pair(sym, g, 0, 0, 10, 10,
             patch={sym["DT_GHOST_RECT"]: 0xC9} if cut else None)
    G, m = P.G, P.G.m
    on = G.still()
    m.set_joystick_type(1)
    m.joystick(JOY_FIRE)
    for _ in range(100):
        m.run_frames(1)
        if m.peek(sym["RV_PEND"]):
            break
    m.joystick(0)
    m.set_joystick_type(0)
    pend = m.peek(sym["RV_PEND"])
    # Πάνω στις τελευταίες σειρές, κοντά στον b: βγαίνουν τελευταίες.
    _, runs, path = P.ref()
    tx, ty = path[-3]
    m.poke(sym["CUR_HX"], (2 * tx) & 0xFF)
    m.poke(sym["CUR_HY"], (2 * ty) & 0xFF)
    G.probe(["UI_HIDE", "UI_SHOW"])          # ένα βήμα κέρσορα
    gp = m.peek(sym["GH_PTR"]) | (m.peek(sym["GH_PTR"] + 1) << 8)
    for _ in range(400):
        if m.peek(sym["RV_PEND"]) == 0:
            break
        m.run_frames(1)
    m.poke(sym["CUR_HX"], (P.ca[0] - 8) & 0xFF)  # και φεύγει
    m.poke(sym["CUR_HY"], P.ca[1] & 0xFF)
    G.probe(["UI_HIDE", "UI_SHOW"])
    pic, ref = G.truth()
    G.go(on)
    if not cut:
        check(pend > 2 and gp != G.ghbuf,
              f"ο κέρσορας μπήκε πάνω στη διαγώνιο με {pend} σειρές ακόμη "
              f"στη λίστα ({gp - G.ghbuf} bytes φαντάσματος)")
    return sum(1 for a, b in zip(pic, ref) if a != b)


def main():
    sym, g = R.T.build()

    res = sweep(sym, g, SWEEP)
    for c, bad, occ, P in res:
        diag = P.runs and P.runs[0][0] & 1
        check(bad == 0 and (bool(occ) == bool(diag)),
              f"{c}: διαδρομή {P.runs}, {bad} κακά tiles, ενώ περνά από "
              f"{len(occ or [])} κατειλημμένα των δύο άκρων")

    # Το κόψιμο του crk_in είναι ο έλεγχος ως το βήμα 36: «κατειλημμένο =
    # κακό». OR A / RET: χωρίς κρατούμενο, «έξω από το αποτύπωμα».
    old = sweep(sym, g, [SWEEP[0], SWEEP[2], SWEEP[4]],
                patch={sym["CRK_IN"]: 0xB7, sym["CRK_IN"] + 1: 0xC9})
    for c, bad, occ, P in old:
        check(bad == len(occ) > 0,
              f"ΑΡΝΗΤΙΚΟ: με τον παλιό έλεγχο το {c} δεν χτίζεται — {bad} "
              f"κακά, ακριβώς τα {len(occ)} tiles των αποτυπωμάτων")
    stone(sym, g)
    third(sym, g)

    # Και οι τέσσερις φορές της διαγωνίου: η λωρίδα του «/» ξεκινά ένα tile
    # αριστερότερα από του «\\», και ανεβαίνοντας η πρώτη σειρά είναι άλλη.
    build(sym, g, 0, 0, 10, 10, "S -> S διαγώνιος, νοτιοανατολικά")
    build(sym, g, 0, 0, -10, 10, "S -> S διαγώνιος, νοτιοδυτικά")
    build(sym, g, 1, 1, 12, -12, "M -> M διαγώνιος, βορειοανατολικά")
    build(sym, g, 1, 0, -12, -8, "M -> S βορειοδυτικά, στροφή σε οριζόντιο")
    build(sym, g, 0, 2, 12, 6, "S -> L με στροφή σε οριζόντιο")
    build(sym, g, 2, 1, 6, 12, "L -> M με στροφή σε κάθετο")
    build(sym, g, 2, 0, 8, 0, "L δίπλα σε S, στροφή στην πόρτα")
    for c in [(0, 0, 10, 10), (0, 0, -10, 10), (1, 1, 12, -12), (0, 2, 12, 6),
              (0, 0, 12, -6), (0, 0, -12, -6)]:
        bad, runs = trail(sym, g, *c)
        check(bad == 0, f"{c}: η προεπισκόπηση {runs} κρύβεται χωρίς ίχνος — "
                        f"{bad} λάθος bytes")
    bad, runs = trail(sym, g, 0, 0, 12, -6, patch=north_patch(sym))
    check(bad > 0, f"ΑΡΝΗΤΙΚΟ: χωρίς το crw_h1 να θυμάται το πρώτο tile, η "
                   f"βόρεια στροφή {runs} αφήνει σημάδι — {bad} λάθος bytes")

    # --- το αρχείο του φαντάσματος: η χειρότερη προεπισκόπηση, και το μοντέλο
    # «πλαίσιο + ένα σημάδι ανά ορατό tile» σε κάθε είδος διαδρομής ---
    for c, cam in [((0, 0, 23, -2), None),         # η χειρότερη: 21 ορατά
                   ((0, 0, 12, -6), (-14, -4)),    # ΒΑ -> Α
                   ((0, 0, -12, -6), (-2, -4)),    # ΒΔ -> Δ
                   ((1, 0, 9, -11), (-12, 0)),     # ΒΑ -> Β
                   ((2, 1, 10, 10), (-14, -8)),    # καθαρή διαγώνιος, L -> M
                   ((2, 2, 24, 0), (-18, -4))]:    # αξονικός, L -> L
        got, want, n, runs = ghost_log(sym, g, *c, cam=cam)
        check(got == want, f"{c} {runs}: {n} ορατά tiles, αρχείο φαντάσματος "
                           f"{got} bytes (56 + 12 x {n} = {want})")
    worst = flicker(sym, g)
    check(worst <= FLICKER_MAX,
          f"ό,τι ήδη φαινόταν δεν σβήνει όσο βγαίνουν οι σειρές: το χειρότερο "
          f"καρέ χάνει {worst} bytes (όριο {FLICKER_MAX})")
    # ΤΟ ΑΡΝΗΤΙΚΟ ΠΡΕΠΕΙ ΝΑ ΑΠΟΤΥΓΧΑΝΕΙ ΣΤΟ ΘΕΤΙΚΟ, όχι να φτάνει ένα νούμερο:
    # το «64» ήταν τα 96 του βήματος 37 με περιθώριο, και με το γρηγορότερο
    # πέρασμα αντικειμένων (βήμα 39) το γυμνό έδαφος φαίνεται σε λιγότερα καρέ.
    worst = flicker(sym, g, terrain=True)
    check(worst > FLICKER_MAX,
          f"ΑΡΝΗΤΙΚΟ: με το έδαφος πρώτα, το χειρότερο καρέ χάνει {worst} bytes "
          f"— η στροφή του διαδρόμου γίνεται γυμνό έδαφος")
    bad = ghost_over(sym, g)
    check(bad == 0, f"οι σειρές πέρασαν κάτω από τον κέρσορα και, όταν αυτός "
                    f"έφυγε, η οθόνη είναι η πλήρης σχεδίαση — {bad} λάθος bytes")
    bad = ghost_over(sym, g, cut=True)
    check(bad > 0, f"ΑΡΝΗΤΙΚΟ: με το dt_ghost_rect κομμένο, ο κέρσορας που "
                   f"φεύγει γράφει πίσω το έδαφος χωρίς διάδρομο — {bad} λάθος "
                   f"bytes")
    # ΑΡΝΗΤΙΚΟ: χωρίς το DEC B του crr_rows η λωρίδα πέφτει ένα tile δεξιά, και
    # η αριστερή στήλη που αγγίζει το πλακίδιο μένει με το έδαφος από κάτω. Ως
    # το βήμα 71 ήταν μόνο του «/»· από το βήμα 72 η πρώτη στήλη βγαίνει από το
    # πρώτο tile του cr_walk για κάθε διαγώνιο, και το DEC B είναι κοινό.
    at = sym["CRRW_BS"] - 1
    m0 = R.Game(sym, g).m
    assert m0.peek(at) == 0x05, f"στο #{at:04X} δεν είναι DEC B"
    bad, _, _ = build(sym, g, 0, 0, -10, 10, "", patch={at: 0x00})
    check(bad > 0, f"ΑΡΝΗΤΙΚΟ: με τη λωρίδα του «/» ένα tile δεξιά, η οθόνη "
                   f"δεν είναι η πλήρης σχεδίαση — {bad} λάθος bytes")
    # ΑΡΝΗΤΙΚΟ για τη μέτρηση των γύρων (βήμα 62, βλ. test_reveal.Game.hook):
    # με τη σειρά διαγωνίου στα 6.000 αντί 12.000 χωρούν δύο σε έναν γύρο, και
    # η μέτρηση πρέπει να το δει.
    dc = sym["DIRTY_COST"] + 2 * 7                      # DK_CROW
    assert m0.peek(dc) | (m0.peek(dc + 1) << 8) == 12000, "το dirty_cost άλλαξε"
    _, bands, most = build(sym, g, 0, 2, 12, 6, "",
                           patch={dc: 6000 & 255, dc + 1: 6000 >> 8})
    check(most >= 2, f"ΑΡΝΗΤΙΚΟ: με τη σειρά διαγωνίου στα 6.000 βγαίνουν δύο σε "
                     f"έναν γύρο — {bands} γύροι, το πολύ {most} σειρές σε έναν")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
