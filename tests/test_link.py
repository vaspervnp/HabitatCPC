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
            byte η πλήρης σχεδίαση. Και ο προορισμός παίρνει πόρτα στην
            αντίθετη του ΤΕΛΕΥΤΑΙΟΥ τρεξίματος: ως το βήμα 36 την έπαιρνε στην
            αντίθετη της διαγωνίου, όπου δεν φτάνει τίποτα — το ίδιο λάθος στον
            Z80 και στην αναφορά σε Python, γι' αυτό η σύγκρισή τους περνούσε.

Το έδαφος καθαρίζεται με το χέρι στην τράπεζα 4 πριν μπουν οι θόλοι: το
μεγαλύτερο καθαρό τετράγωνο του χάρτη είναι 14 tiles, πάνω στην αποικία, και
μια διαγώνιος ανάμεσα σε δύο L θέλει 20.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/vasilhs/cpcemu")

import balance as B                                                # noqa: E402
import route                                                       # noqa: E402
import test_reveal as R                                            # noqa: E402
import world as W                                                  # noqa: E402
from cpc import KEY_SPACE, KEY_RIGHT, JOY_FIRE                     # noqa: E402

FAIL = []
WID = [4, 6, 8]                          # πλευρά του αποτυπώματος σε tiles
W_OCC = 0x30
CORR_REC = 5
METAL_PER_TILE = 6                       # ο κατάλογος του src/build.asm
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
    """Τα tiles που πατά η διαδρομή, με τις επαναλήψεις του cr_walk: δύο
    διαδοχικά διαγώνια πλακίδια μοιράζονται ένα tile και το μετρούν δύο φορές.
    Η ίδια γεωμετρία με το tiles_of του tests/test_route.py."""
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
            out += ([(lx - 1, ly - 1), (lx, ly)] if ux == uy
                    else [(lx - 1, ly), (lx, ly - 1)])
        if len(runs) > 1:
            d1, n1 = runs[1]
            vx, vy = route.DIR_U[d1]
            if vx:
                c, r = ux * Td - (1 if ux > 0 else 0), uy * Td
                for _ in range(n1):
                    out.append((c, r))
                    c += vx
            else:
                r, c = uy * (Sd - 1) - (1 if uy < 0 else 0), ux * Sd
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
        tap(KEY_SPACE)
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
    want = path.count(mid)
    check(P.bad == want, f"ΑΡΝΗΤΙΚΟ: μια πέτρα στη μέση της διαγωνίου, στο "
                         f"{mid}, κόβει τη διαδρομή — {P.bad} κακά "
                         f"(το cr_walk την περνά {want} φορές)")


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
def build(sym, g, sa, sb, dx, dy, what):
    P = Pair(sym, g, sa, sb, dx, dy)
    G, m = P.G, P.G.m
    side, runs, path = P.ref()
    tbl = layout("G_corr_tbl") - 0x4000     # μέσα στην τράπεζα 6
    # Η ΠΡΟΣΟΜΟΙΩΣΗ ΣΤΑΜΑΤΑ πριν από το FIRE: ένας άποικος που αφήνει θέση
    # δακτυλίου στο μεταξύ αφήνει 2-7 λάθος bytes (§15, γνωστό και άσχετο
    # με τον διάδρομο), και εδώ η σύγκριση είναι byte προς byte.
    on = G.still()
    c = G.canary()
    metal = m.peek(g + 6) | (m.peek(g + 7) << 8)
    slot = None
    b6 = G.bank(6)
    for k in range(96):
        if b6[tbl + k * CORR_REC + 4] == 0:
            slot = k
            break
    G.run(40_000)
    G.iters = []
    m.set_joystick_type(1)
    G.stick(JOY_FIRE)                        # ο προορισμός: χτίζει
    m.set_joystick_type(0)
    G.settle()
    laid = G.worst()
    paid = metal - (m.peek(g + 6) | (m.peek(g + 7) << 8))
    rec = [bytes(b6[tbl + (slot + k) * CORR_REC:
                    tbl + (slot + k + 1) * CORR_REC]) for k in range(2)]
    node_a, node_b = rec[0][0], rec[0][1]
    want = [(rec[0][2], rec[0][3])] + ([(rec[1][2], rec[1][3])]
                                       if rec[1][0] == 255 and rec[1][4] else [])
    # ΜΕΤΡΗΜΕΝΟ (βήμα 36): 160-220 ms, όσο μεγαλώνει το περίγραμμα. Μια
    # διαγώνιος n βημάτων ξαναζωγραφίζει ένα τετράγωνο n x n — ο ευθύς είναι
    # 120 (§6.9). Το κανάρινι λέει ότι δεν ξαναζωγραφίστηκε το κάδρο (~700).
    check(paid == METAL_PER_TILE * sum(n for _, n in runs)
          and want == runs and G.alive(c) and laid < 300,
          f"{what}: χτίστηκε — {[list(r) for r in rec[:len(want)]]}, "
          f"μέταλλο -{paid}, κανάρινι {'ζει' if G.alive(c) else 'ΝΕΚΡΟ'}, "
          f"{laid:.0f} ms ο χειρότερος γύρος (όριο 300)")
    pic, ref = G.truth()                     # το byte 0 είναι το κανάρινι
    bad = sum(1 for i, (a, b) in enumerate(zip(pic, ref)) if a != b and i)
    check(bad == 0, f"{what}: η οθόνη είναι η πλήρης σχεδίαση, διάδρομος και "
                    f"πόρτες — {bad} λάθος bytes")
    conn = sym["DOME_CONN"]
    da, db = m.peek(conn + node_a), m.peek(conn + node_b)
    door_a, door_b = runs[0][0], (runs[-1][0] + 4) & 7
    wrong = (runs[0][0] + 4) & 7
    check(da == 1 << door_a and db == 1 << door_b,
          f"{what}: πόρτες {da:08b} / {db:08b} — ο a στο {door_a}, ο b στο "
          f"{door_b}, την αντίθετη του τελευταίου τρεξίματος"
          + (f" (όχι στο {wrong})" if wrong != door_b else ""))
    G.go(on)
    return P, laid


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

    build(sym, g, 0, 0, 10, 10, "S -> S διαγώνιος")
    build(sym, g, 0, 2, 12, 6, "S -> L με στροφή σε οριζόντιο")
    build(sym, g, 2, 1, 6, 12, "L -> M με στροφή σε κάθετο")
    build(sym, g, 2, 0, 8, 0, "L δίπλα σε S, στροφή στην πόρτα")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
