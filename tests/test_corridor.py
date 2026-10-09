#!/usr/bin/env python3
"""Ο δρομολογητής του src/route.asm, στο main.sna, απέναντι στις αναφορές του.

  cr_plan    η διαδρομή, η αφετηρία, τα τρεξίματα: tools/route.py· και καμία,
             με cr_far = 1, όταν οι θόλοι απέχουν 64 tiles ή περισσότερο σε
             έναν άξονα (βήμα 81)
  cr_walk    τα tiles, ΜΕ ΤΗ ΣΕΙΡΑ τους: το tiles_of του tests/test_route.py
  cr_check   πόσα tiles δεν επιτρέπονται: έξω από τον κόσμο, κατειλημμένα ή
             όχι έδαφος/σκόνη/θεμέλιο (bd_ok) — εκτός αν πέφτουν στο
             αποτύπωμα ενός από τα δύο άκρα (§9.4)
  cr_stamp   bit 4 (W_OCC_STRUCT) στα tiles της διαδρομής μέσα στον κόσμο,
             και καμία άλλη αλλαγή σε καμία τράπεζα
  cr_cost    l0 (+ l1) πλακίδια επί την τιμή ανά πλακίδιο, 16 bit
  cr_afford  Z και A = 0 αν φτάνουν και τα δύο υλικά, NZ και A = 1 αν όχι
  cr_commit  η πρώτη άδεια θέση του πίνακα, δύο διπλανές για στροφή, ποτέ
             μετά την τελευταία· πληρωμή μόνο τότε, και ΚΑΜΙΑ ακμή (βήμα 87)
  cr_commit_ln  το ίδιο για το LINK, και η ακμή μόνο αν και οι δύο θόλοι
             είναι έτοιμοι — με έναν από τους δύο εργοτάξιο, όχι
  cr_redraw  οι δύο αρμοί (DK_CONN· ως το 95 οι πόρτες), μία DK_CROW για κάθε
             ορατή σειρά της διαγωνίου, το περίγραμμα του αξονικού κομματιού —
             από το βήμα 96 με τη στήλη αριστερά ή τη σειρά πάνω όταν ο άξονας
             του b πέφτει σε όριο tile (stubs στο dirty_push και στο view_add)

Δύο θόλοι στις θέσεις 50 και 51 του πίνακα, σε 1.500 τυχαίες θέσεις: αξονικοί,
καθαρές διαγώνιες, «σχεδόν» διαγώνιες, μονές αποστάσεις, άδειες θέσεις, θόλοι
υπό κατασκευή, γύρω από τα 64 tiles σε έναν άξονα (126, 128 και 130 μισά tiles,
και ως 254, από τις δύο μεριές), και τα τρία μεγέθη σε κάθε άκρο. Ο έλεγχος τρέχει σε τυχαίο κόσμο, ώστε κάθε
περίπτωση του bd_ok και του αποτυπώματος να συμβαίνει.

ΓΙΑΤΙ. Ως το βήμα 72 ο δρομολογητής τον έβλεπαν το test_route, στα 66 ζεύγη
της δοκιμαστικής αποικίας, και το test_link σε 26 γεωμετρίες με θόλους του
παίκτη. Από 28 σκόπιμα λάθη του βήματος 72, τα 7 πέρασαν και τα δύο (και το
test_game) — βλ. DESIGN §9.4.

Και ο ΧΡΟΝΟΣ: έξι γεωμετρίες (αξονική, διαγώνιος, διαγώνιος και οριζόντιος,
διαγώνιος και κάθετος, από την άλλη μεριά, καμία), για cr_plan, cr_walk με
κενό callback, cr_check, cr_afford και cr_commit με άδειες μόνο τις δύο
τελευταίες θέσεις — όχι πιο αργά από όσο μετρήθηκαν στο βήμα 72, και το
cr_plan όχι πιο αργά από το βήμα 81. Με το route.asm του βήματος 71
αποτυγχάνουν όλα, με του βήματος 80 το cr_plan σε κάθε γεωμετρία.

Αρνητικά, με το snapshot πειραγμένο: ακτίνα size+3, το x χωρίς όριο (ο
δρομολογητής του βήματος 80, που αναδιπλωνόταν), το -64 κοντά, ο πίνακας κατευθύνσεων
ένα byte πίσω, το αποτύπωμα των άκρων στον έλεγχο ένα tile μικρότερο, ο
έλεγχος που δεν βλέπει το y έξω από τον κόσμο, η σφραγίδα χωρίς το όριο του
κόσμου, ζευγάρι εγγραφών και στην τελευταία θέση, και σειρά διαγωνίου ορατή
μόνο από τη στήλη -1.

ΤΟ x ΕΞΩ ΑΠΟ ΤΟΝ ΚΟΣΜΟ ΔΕΝ ΦΤΑΝΕΤΑΙ: σε 2.709.202 διαδρομές της αναφοράς, με
τον ένα θόλο σε κάθε άκρη, κανένα tile δεν βγήκε έξω στο x. Ενα λάθος στον
έλεγχο του x του cr_cb_chk δεν το βλέπει καμία δοκιμή (βήμα 72) — αυτή
αποτυγχάνει μόνο επειδή δεν βρίσκει πια τα bytes που πειράζουν τα αρνητικά.
"""
import ctypes, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import cpc                                               # noqa: E402
import route                                             # noqa: E402
import scene as S                                        # noqa: E402
from test_route import tiles_of                          # noqa: E402

PROBE, OUT, CB, CBRET, PTR, LOG = 0x3E00, 0x3EF0, 0x3E80, 0x3EA0, 0x3EF8, 0x3400
SA, SB = 50, 51
W_OCC_MASK, W_DUST, W_FOUNDATION = 0x30, 1, 7            # src/const.asm
MAX_CORR, CORR_REC, MAX_DEGREE = 96, 5, 8
DK_CONN, DK_CROW, VIEW_TW, VIEW_TH = 3, 7, 20, 10
# Τα stubs ΠΑΝΩ από το PROBE, στο #3F00 (βήμα 95· ως τότε στο #3D60): βλ. test_place.
RLOG, RPTR, STUB = 0x3800, 0x3EFC, 0x3F00                 # το ημερολόγιο του cr_redraw
# µs με το probe (βήμα 72): plan, walk, check, afford, commit ανά γεωμετρία.
# Στο βήμα 71: 623/939/2496/342/3816, 637/2778/5326/334/5856,
# 741/2853/5873/347/6205, 739/3070/6512/347/6721, 1087/2095/3475/343/5035 και 413.
# Το plan από το βήμα 81, με τον έλεγχο της απόστασης και το cr_sgn και το
# crs_rk γραμμένα μέσα στο cr_side· ως το 80: 475, 486, 551, 551, 865, 376.
GEOM = {
    "αξονική":            ((-40, -20, 1, -4, -20, 0), (447, 910, 2143, 327, 3193)),
    "διαγώνιος":          ((-40, -20, 0, 0, 20, 2), (458, 1212, 3172, 319, 3644)),
    "+ οριζόντιος":       ((-40, -20, 1, 10, 10, 1), (523, 1586, 3914, 332, 4244)),
    "+ κάθετος":          ((-40, -20, 2, -10, 40, 0), (523, 1900, 4594, 332, 4779)),
    "από την άλλη μεριά": ((-40, -20, 0, -70, -46, 1), (808, 1040, 2156, 328, 3390)),
    "καμία":              ((-40, -20, 1, -37, 10, 1), (275, None, None, None, None)),
}


# ΚΑΙ ΕΞΩ ΑΠΟ ΤΟΝ ΚΟΣΜΟ. Μια στροφή σε οριζόντιο με τον προορισμό στη σειρά
# -64 πατά τη -65: το «μπροστινό» tile της διαγωνίου που ανεβαίνει. Με τον b ως
# τέσσερα μισά πλακίδια από μια άκρη του κόσμου: 289.549 από 2.709.202
# διαδρομές της αναφοράς, όλες στη -65· στο x καμία. 40 από αυτές, για να τις
# δει ο έλεγχος — το τυχαίο σενάριο δεν πέφτει πάνω τους. Ολες με |Δ| <= 127
# μισά πλακίδια: πιο μακριά, από το βήμα 81, δεν υπάρχει διάδρομος (TOO FAR).
EDGE = [(28, -76, 0, 116, -128, 1), (69, -128, 1, 127, -76, 2), (-26, -112, 0, -50, -128, 1),
        (-11, -80, 2, -81, -128, 1), (103, -40, 0, -19, -128, 2), (50, -128, 0, 126, -56, 1),
        (-122, -68, 2, -2, -128, 1), (82, -72, 1, -6, -128, 1), (124, -108, 1, 20, -128, 2),
        (20, -128, 0, 126, -26, 2), (-20, -108, 1, 38, -128, 0), (-102, -108, 0, 22, -128, 0),
        (80, -112, 1, 48, -128, 0), (31, -128, 2, 125, -120, 2), (-96, -40, 2, 10, -128, 0),
        (-26, -128, 2, -126, -122, 0), (97, -64, 0, -29, -128, 0), (-62, -96, 1, -20, -128, 1),
        (-43, -60, 2, 45, -128, 2), (115, -116, 2, 53, -128, 0), (121, -80, 2, 47, -128, 2),
        (42, -128, 1, 124, -122, 0), (8, -128, 0, 126, -124, 0), (-119, -120, 1, -47, -128, 2),
        (13, -128, 2, 125, -122, 0), (45, -128, 1, 127, -122, 1), (19, -128, 2, 125, -122, 1),
        (-62, -64, 0, 32, -128, 2), (37, -44, 2, -87, -128, 1), (-128, -100, 0, -50, -128, 0),
        (54, -100, 2, 4, -128, 0), (-47, -112, 0, -93, -128, 0), (82, -120, 1, 62, -128, 0),
        (-24, -100, 2, 88, -128, 2), (13, -52, 0, -105, -128, 2), (-3, -20, 1, 121, -128, 0),
        (-6, -108, 0, 88, -128, 0), (15, -128, 1, 127, -22, 2), (-85, -84, 2, 39, -128, 0),
        (67, -112, 0, -17, -128, 2)]


class Ends:
    """Τα δύο άκρα όπως τα θέλει το tiles_of: d(i, πεδίο)."""

    def __init__(self, a, b):
        self.v = {0: a, 1: b}

    def d(self, i, f):
        return self.v[i][{S.D_CX: 0, S.D_CY: 1, S.D_SIZE: 2}[f]]


def sb(v):
    return v - 256 if v > 127 else v


class Game:
    def __init__(self, sym, patch=()):
        self.sym = sym
        m = self.m = cpc.CPC()
        m.run_frames(60)
        assert m.quickload(TG.COLONY, start=False), "quickload απέτυχε"
        m.run_frames(150)                                # game_new
        m.write_ram(CB, bytes([0x2A, PTR & 255, PTR >> 8, 0x70, 0x23, 0x71, 0x23,
                               0x22, PTR & 255, PTR >> 8, 0xC9]))
        m.write_ram(CBRET, bytes([0xC9]))
        for at, v in patch:
            m.poke(at, v)
        self.ptr = [cpc._lib.cpcemu_ram_ptr(m._h, n) for n in range(8)]
        self.keep = [ctypes.string_at(self.ptr[n], 0x4000) for n in range(8)]
        for line in open(os.path.join(ROOT, "build", "layout.asm"), encoding="utf-8"):
            if line.startswith("G_dome_tbl"):
                self.gd = int(line.split("#")[1].split()[0], 16) - 0x4000
            if line.startswith("G_econ_state"):
                self.g = int(line.split("#")[1].split()[0], 16)
            if line.startswith("G_corr_tbl"):
                self.gc = int(line.split("#")[1].split()[0], 16) - 0x4000
            if line.startswith("G_rt_nodes"):
                self.nodes = int(line.split("#")[1].split()[0], 16)
            if line.startswith("G_node_adj"):
                self.adj = int(line.split("#")[1].split()[0], 16)

    def restore(self):
        for n in range(8):
            ctypes.memmove(self.ptr[n], self.keep[n], 0x4000)

    def w16(self, a):
        return self.m.peek(a) | self.m.peek(a + 1) << 8

    def run(self, name, step=20):
        m, sym = self.m, self.sym
        code = [0xF3, 0x31, 0x00, 0x01, 0x01, 0xC0, 0x7F, 0xED, 0x49,
                0xCD, sym[name] & 255, sym[name] >> 8,
                0xF5, 0xE1, 0x22, OUT & 255, OUT >> 8, 0x18, 0xFE]
        m.write_ram(PROBE, bytes(code))
        m.set_pc(PROBE)
        end, t = PROBE + len(code) - 2, 0
        while not (end <= m.pc <= end + 2):
            m.run_us(step)
            t += step
            if t > 2_000_000:
                return None, 0, 0
        af = self.w16(OUT)
        return t, af >> 8, af & 0xFF

    def dome(self, slot, cx, cy, size, state=2):
        rec = bytearray(24)
        rec[0], rec[1], rec[2], rec[4] = cx & 255, cy & 255, size, state
        ctypes.memmove(ctypes.addressof(self.ptr[6].contents) + self.gd + 24 * slot,
                       bytes(rec), 24)

    def plan(self, a, b, st=(2, 2)):
        self.dome(SA, *a, st[0])
        self.dome(SB, *b, st[1])
        self.m.poke(self.sym["CR_A"], SA)
        self.m.poke(self.sym["CR_B"], SB)
        return self.run("CR_PLAN")

    def walk(self, cb=CB, step=20):
        self.m.write_ram(self.sym["CR_CB"], bytes([cb & 255, cb >> 8]))
        self.m.write_ram(PTR, bytes([LOG & 255, LOG >> 8]))
        t, _, _ = self.run("CR_WALK", step)
        raw = self.m.read_ram(LOG, self.w16(PTR) - LOG)
        return t, [(sb(raw[i]), sb(raw[i + 1])) for i in range(0, len(raw), 2)]


def check_rule(world, tiles, ends):
    """Ο κανόνας του cr_check, σε Python."""
    bad = 0
    for x, y in tiles:
        if not (-64 <= x < 64 and -64 <= y < 64):
            bad += 1
            continue
        b = world[(y + 64) * 128 + x + 64]
        if not (b & W_OCC_MASK) and (b & 7) in (0, W_DUST, W_FOUNDATION):
            continue
        inside = False
        for cx, cy, size in ends:
            r = size + 2
            if ((x - ((cx >> 1) - r)) & 255) < 2 * r and ((y - ((cy >> 1) - r)) & 255) < 2 * r:
                inside = True
        if not inside:
            bad += 1
    return bad


def rules(sym, patch=(), n=1500):
    """Η πρώτη διαφορά από τις αναφορές, ή None."""
    G = Game(sym, patch)
    m = G.m
    rnd = random.Random(72)
    seen = {"διαδρομές": 0, "στροφές": 0, "από τον b": 0, "κακά tiles": 0, "λίγα υλικά": 0,
            "μακριά": 0}
    seen["έξω από τον κόσμο"] = seen["υπό κατασκευή"] = 0
    for case in range(n):
        G.restore()
        sa, sbz = rnd.randrange(3), rnd.randrange(3)
        ax, ay = rnd.randrange(-120, 120), rnd.randrange(-120, 120)
        k = rnd.random()
        if k < 0.15:
            d = rnd.randrange(-60, 61)
            dx, dy = (d, 0) if rnd.random() < 0.5 else (0, d)
        elif k < 0.30:
            d = rnd.randrange(-50, 51)
            dx, dy = d, d * rnd.choice([1, -1])
        elif k < 0.40:
            d = rnd.randrange(-50, 51)
            dx, dy = d, d * rnd.choice([1, -1]) + rnd.choice([-4, -2, 2, 4])
        elif k < 0.55:                                   # βήμα 81: γύρω από τα 64 tiles
            d = rnd.choice([126, 128, 128, 130, rnd.randrange(100, 255)])
            o = rnd.randrange(-80, 81)
            far_axis = rnd.randrange(2)
            dx, dy = (d, o) if far_axis == 0 else (o, d)
        else:
            dx, dy = rnd.randrange(-80, 81), rnd.randrange(-80, 81)
        if rnd.random() < 0.85:
            dx, dy = dx & ~1, dy & ~1
        if 0.40 <= k < 0.55:                             # ο a εκεί που χωρά και ο b
            c = rnd.randrange(-128, 128 - (dx, dy)[far_axis])
            ax, ay = (c, ay) if far_axis == 0 else (ax, c)
        bx, by = max(-128, min(127, ax + dx)), max(-128, min(127, ay + dy))
        if 0.40 <= k < 0.55 and rnd.random() < 0.5:      # και ανάποδα
            ax, ay, bx, by = bx, by, ax, ay
        # άδειος (0), υπό κατασκευή (1), ενεργός (2): διάδρομος σε ό,τι δεν είναι άδειο
        st = tuple(0 if r < 0.03 else 1 if r < 0.2 else 2 for r in (rnd.random(), rnd.random()))
        a, b = (ax, ay, sa), (bx, by, sbz)
        if case < len(EDGE):
            a, b, st = EDGE[case][:3], EDGE[case][3:], (2, 2)
        where = f"θόλοι {a} -> {b}" + (f" κατάσταση {st}" if st != (2, 2) else "")
        t, A, _ = G.plan(a, b, st)
        if t is None:
            return f"{where}: το cr_plan δεν γύρισε"
        ref = route.plan(*a, *b) if 0 not in st else None
        n_ = m.peek(sym["CR_N"])
        # ΜΑΚΡΙΑ (βήμα 81): όταν δεν υπάρχει διαδρομή, cr_far = 1 αν οι θόλοι
        # απέχουν >= 64 tiles σε έναν άξονα, αλλιώς 0. Μονή διαφορά δεν γίνεται
        # στο παιχνίδι (τα κέντρα είναι ζυγά μισά tiles, §3.4): εκεί κρίνει
        # όποιος άξονας ρωτηθεί πρώτος.
        far = route.too_far(a[0], a[1], b[0], b[1]) and 0 not in st
        if A == 0 and (b[0] - a[0]) % 2 == 0 and (b[1] - a[1]) % 2 == 0 \
                and m.peek(sym["CR_FAR"]) != far:
            return f"{where}: cr_far {m.peek(sym['CR_FAR'])}, ο κανόνας λέει {int(far)}"
        seen["μακριά"] += far
        if ref is None:
            if A or n_:
                return f"{where}: διαδρομή {n_} τρεξίματα, η αναφορά λέει καμία"
            continue
        side, runs = ref
        got = [(m.peek(sym["CR_D0"]), m.peek(sym["CR_L0"]))]
        if n_ > 1:
            got.append((m.peek(sym["CR_D1"]), m.peek(sym["CR_L1"])))
        frm, to = m.peek(sym["CR_FROM"]), m.peek(sym["CR_TO"])
        want_ft = (SA, SB) if side == 0 else (SB, SA)
        if A != len(runs) or n_ != len(runs) or got != runs or (frm, to) != want_ft:
            return (f"{where}: A {A}, τρεξίματα {got}, από {frm} προς {to}· "
                    f"η αναφορά λέει {runs} από {want_ft[0]}")
        seen["διαδρομές"] += 1
        seen["υπό κατασκευή"] += 1 in st
        seen["στροφές"] += len(runs) > 1
        seen["από τον b"] += side
        ends = (a, b) if side == 0 else (b, a)
        want = tiles_of(Ends(*ends), 0, runs, 1)
        t, tiles = G.walk()
        if tiles != want:
            k_ = next((i for i in range(min(len(tiles), len(want))) if tiles[i] != want[i]),
                      min(len(tiles), len(want)))
            return (f"{where}, {runs}: tile {k_} = {tiles[k_:k_ + 1]}, η αναφορά λέει "
                    f"{want[k_:k_ + 1]} ({len(tiles)} / {len(want)} tiles)")
        # ο έλεγχος σε τυχαίο κόσμο
        wr = random.Random(case)
        world = bytes(wr.choice([0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 0x10, 0x20, 0x30, 0x17, 0x11])
                      for _ in range(0x4000))
        ctypes.memmove(G.ptr[4], world, 0x4000)
        _, A, _ = G.run("CR_CHECK")
        wb = check_rule(world, want, ends)
        if A != wb:
            return f"{where}, {runs}: cr_check {A}, ο κανόνας λέει {wb}"
        seen["κακά tiles"] += wb > 0
        # η σφραγίδα, στον ίδιο κόσμο: bit 4 σε κάθε tile της διαδρομής μέσα
        # στον κόσμο, και τίποτα άλλο — ούτε στις άλλες τράπεζες (ένα tile της
        # -65 χωρίς το ret m θα έπεφτε στο #BFxx της τράπεζας 2)
        was = [ctypes.string_at(G.ptr[k], 0x4000) for k in range(8)]
        G.run("CR_STAMP")
        ww = bytearray(world)
        for x, y in want:
            if -64 <= x < 64 and -64 <= y < 64:
                ww[(y + 64) * 128 + x + 64] |= 0x10
        if ctypes.string_at(G.ptr[4], 0x4000) != bytes(ww):
            return f"{where}, {runs}: το cr_stamp δεν σφράγισε ό,τι λέει ο κανόνας"
        cb = sym["CR_CB"] - 0x8000                       # η μόνη μεταβλητή που αλλάζει
        for k in (1, 2, 3, 5, 6, 7):
            now = bytearray(ctypes.string_at(G.ptr[k], 0x4000))
            if k == 2:
                now[cb:cb + 2] = was[2][cb:cb + 2]
            if now != was[k]:
                return f"{where}, {runs}: το cr_stamp άλλαξε την τράπεζα {k}"
        seen["έξω από τον κόσμο"] += any(not -64 <= y < 64 for _, y in want)
        # κόστος και afford
        pm, pb = rnd.randrange(21), rnd.randrange(21)
        m.poke(sym["BD_METAL"], pm)
        m.poke(sym["BD_BIOP"], pb)
        G.run("CR_COST")
        nt = sum(length for _, length in runs)
        cm, cb_ = G.w16(sym["CR_METAL"]), G.w16(sym["CR_BIOP"])
        if (cm, cb_) != (nt * pm, nt * pb):
            return f"{where}: κόστος {cm}/{cb_}, ο κανόνας λέει {nt * pm}/{nt * pb}"
        for _ in range(3):
            sm = max(0, cm + rnd.choice([-1, 0, 1, rnd.randrange(-50, 50)]))
            sp = max(0, cb_ + rnd.choice([-1, 0, 1, rnd.randrange(-50, 50)]))
            m.write_ram(G.g + 6, bytes([sm & 255, sm >> 8, sp & 255, sp >> 8]))
            _, A, F = G.run("CR_AFFORD")
            ok = sm >= cm and sp >= cb_
            if (A, bool(F & 0x40)) != ((0, True) if ok else (1, False)):
                return (f"{where}: afford A={A} Z={bool(F & 0x40)} με αποθέματα {sm}/{sp} "
                        f"και κόστος {cm}/{cb_}")
            seen["λίγα υλικά"] += not ok
    if not patch and min(seen.values()) < 20:
        return f"το σενάριο δεν έπιασε ό,τι έπρεπε: {seen}"
    print(f"    {n} ζεύγη: {seen}")
    return None


def commit_rule(states, n):
    """Η θέση του cr_commit: η πρώτη άδεια, και για στροφή με άδεια και την επόμενη."""
    for i in range(MAX_CORR):
        if states[i] == 0 and (n < 2 or (i + 1 < MAX_CORR and states[i + 1] == 0)):
            return i
    return None


def commit_rules(sym, patch=(), n=400):
    """cr_commit_ln (cr_commit, cr_pay, cr_lnk) σε τυχαίους πίνακες διαδρόμων,
    με τον έναν θόλο ή και τους δύο καμιά φορά εργοτάξιο: η πρώτη διαφορά από
    τον κανόνα, ή None."""
    G = Game(sym, patch)
    m = G.m
    rnd = random.Random(7272)
    seen = {"στροφές": 0, "χωρίς θέση": 0, "τελευταία θέση": 0, "γεμάτος βαθμός": 0,
            "ζευγάρι μόνο με την τελευταία": 0, "εργοτάξιο: καμία ακμή": 0}
    tbl = ctypes.addressof(G.ptr[6].contents) + G.gc
    span = MAX_CORR * CORR_REC + 32                       # και 32 bytes μετά τον πίνακα
    pairs = {1: [], 2: []}                                # ευθείες και στροφές, μισές-μισές
    while min(len(v) for v in pairs.values()) < 30:
        a = (rnd.randrange(-100, 100) & ~1, rnd.randrange(-100, 100) & ~1, rnd.randrange(3))
        d = rnd.randrange(-60, 61) & ~1
        dx, dy = rnd.choice([(d, 0), (0, d), (d, d), (d, -d),
                             (d, rnd.randrange(-60, 61) & ~1)])
        b = (a[0] + dx, a[1] + dy, rnd.randrange(3))
        r = max(abs(b[0]), abs(b[1])) < 128 and route.plan(*a, *b)
        if r and len(pairs[len(r[1])]) < 30:
            pairs[len(r[1])].append((a, b))
    pairs = [p for ab in zip(pairs[1], pairs[2]) for p in ab]
    for case in range(n):
        G.restore()
        a, b = pairs[case % len(pairs)]
        side, runs = route.plan(*a, *b)
        kind = case % 7
        st = [rnd.choice([1, 2, 2, 2, 7]) for _ in range(MAX_CORR)]
        if kind == 0:
            pass                                         # γεμάτος
        elif kind == 1:
            st[-1] = 0                                   # μόνο η τελευταία
        elif kind == 2:
            st[-2] = st[-1] = 0                          # οι δύο τελευταίες
        elif kind == 3:
            st[rnd.randrange(MAX_CORR)] = 0              # ένα κενό
        elif kind == 4:
            k = rnd.randrange(MAX_CORR - 1)
            st[k] = st[k + 1] = 0                        # δύο διπλανά κενά
        elif kind == 5:
            st = [0 if rnd.random() < 0.3 else v for v in st]
        else:
            st = [0] * MAX_CORR
        raw = bytearray(rnd.randrange(256) for _ in range(span))
        for i in range(MAX_CORR):
            raw[CORR_REC * i + 4] = st[i]
        # μετά τον πίνακα είναι το G_worldinfo και το G_dome_fig, και το byte
        # «κατάστασης» μιας 97ης εγγραφής είναι το πρώτο της κρυφής μνήμης
        # φιγούρων: μπορεί να είναι 0, και μόνο τότε φαίνεται το λάθος
        if rnd.random() < 0.5:
            raw[CORR_REC * MAX_CORR + 4] = 0
        ctypes.memmove(tbl, bytes(raw), span)
        deg = [rnd.choice([0, 1, 3, 7, 8, 8]) for _ in range(2)]
        m.poke(G.nodes + SA, deg[0])
        m.poke(G.nodes + SB, deg[1])
        adj0 = m.read_ram(G.adj, 8 * 128)
        m.write_ram(G.g + 6, bytes([0xE8, 3, 0xE8, 3]))   # 1.000 και 1.000
        m.poke(sym["BD_METAL"], 6)
        m.poke(sym["BD_BIOP"], 3)
        # ΕΡΓΟΤΑΞΙΟ (βήμα 87): ένας διάδρομος προς θόλο που χτίζεται δεν
        # είναι ακμή ακόμη. Στο ένα πέμπτο ο ένας ή και οι δύο είναι DS_SITE.
        live = rnd.choice([(2, 2), (2, 2), (2, 2), (2, 2), (1, 2), (2, 1), (1, 1)])
        t, A, _ = G.plan(a, b, live)
        if A != len(runs):
            return f"θόλοι {a} -> {b}: το cr_plan έδωσε {A}"
        _, A, _ = G.run("CR_COMMIT_LN")
        where = f"θόλοι {a} -> {b}, {runs}, πίνακας είδους {kind}"
        got = ctypes.string_at(tbl, span)
        at = commit_rule(st, len(runs))
        want = bytearray(raw)
        frm, to = (SA, SB) if side == 0 else (SB, SA)
        if at is not None:
            (d0, l0) = runs[0]
            want[CORR_REC * at:CORR_REC * at + 5] = bytes([frm, to, d0, l0, 2])
            if len(runs) > 1:
                (d1, l1) = runs[1]
                want[CORR_REC * (at + 1):CORR_REC * (at + 2)] = bytes([255, 255, d1, l1, 2])
        if (A == 0) != (at is not None) or got != bytes(want):
            k = next((i for i in range(span) if got[i] != want[i]), None)
            return (f"{where}: A = {A}, η θέση κατά τον κανόνα {at}, πρώτο λάθος byte "
                    f"{k} ({got[k] if k is not None else '-'} αντί {want[k] if k is not None else '-'})")
        nt = sum(length for _, length in runs)
        stock = (G.w16(G.g + 6), G.w16(G.g + 8))
        want_st = (1000 - 6 * nt, 1000 - 3 * nt) if at is not None else (1000, 1000)
        if stock != want_st:
            return f"{where}: αποθέματα {stock}, ο κανόνας λέει {want_st}"
        # οι ακμές: ο ένας στους γείτονες του άλλου, αν χωράει — και μόνο αν
        # είναι έτοιμοι και οι δύο
        wdeg, wadj = list(deg), bytearray(adj0)
        if at is not None and live == (2, 2):
            for i, (x, y) in enumerate(((frm, to), (to, frm))):
                d = wdeg[x - SA]
                if d < MAX_DEGREE:
                    wadj[8 * x + d] = y
                    wdeg[x - SA] = d + 1
        gdeg = [m.peek(G.nodes + SA), m.peek(G.nodes + SB)]
        if gdeg != wdeg or m.read_ram(G.adj, 8 * 128) != bytes(wadj):
            return f"{where}: βαθμοί {gdeg} αντί {wdeg}, ή γείτονες λάθος"
        seen["στροφές"] += len(runs) > 1 and at is not None
        seen["χωρίς θέση"] += at is None
        seen["τελευταία θέση"] += at == MAX_CORR - 1
        seen["γεμάτος βαθμός"] += at is not None and MAX_DEGREE in deg
        seen["εργοτάξιο: καμία ακμή"] += at is not None and live != (2, 2)
        seen["ζευγάρι μόνο με την τελευταία"] += kind == 1 and len(runs) > 1
    if not patch and min(seen.values()) < 10:
        return f"το σενάριο του commit δεν έπιασε ό,τι έπρεπε: {seen}"
    print(f"    {n} commit: {seen}")
    return None


def redraw_stubs(sym):
    """dirty_push και view_add γράφουν ό,τι τους δίνεται στο RLOG: (A, B, C) και
    (#FF, vr_tx, vr_ty, vr_w, vr_h). Το stub κρατά B, C, E όπως το αληθινό."""
    lo, hi = RPTR & 255, RPTR >> 8
    dp = [0x2A, lo, hi, 0x77, 0x23, 0x70, 0x23, 0x71, 0x23, 0x22, lo, hi, 0xC9]
    va = [0x2A, lo, hi, 0x36, 0xFF, 0x23]
    for k in ("VR_TX", "VR_TY", "VR_W", "VR_H"):
        va += [0x3A, sym[k] & 255, sym[k] >> 8, 0x77, 0x23]
    va += [0x22, lo, hi, 0xC9]
    assert sym["ZZ_BANK0_END"] <= STUB, "ο κώδικας έφτασε στα stubs"
    code = {STUB: dp, STUB + 0x20: va,
            sym["DIRTY_PUSH"]: [0xC3, STUB & 255, STUB >> 8],
            sym["VIEW_ADD"]: [0xC3, (STUB + 0x20) & 255, (STUB + 0x20) >> 8]}
    return [(at + i, v) for at, bs in code.items() for i, v in enumerate(bs)]


def redraw_rule(ends, side, runs, cam):
    """Ο κανόνας του cr_redraw: οι δύο αρμοί (ως το 95 οι πόρτες), μία DK_CROW
    για κάθε σειρά της διαγωνίου που φαίνεται (τρεις στήλες, από το tile της
    μείον ένα), και το περίγραμμα του αξονικού κομματιού — όλης της διαδρομής, ή μόνο της στροφής —, με μία στήλη
    αριστερά (κάθετος) ή μία σειρά πάνω (οριζόντιος) όταν ο άξονας του b είναι
    ζυγός σε μισά tiles: ο διάδρομος στο κέντρο πατά μισό πλάτος εκεί (βήμα 96)."""
    (fx, fy, fs), (tx, ty, ts) = ends
    want = tiles_of(Ends(*ends), 0, runs, 1)
    d0, l0 = runs[0]
    frm, to = (SA, SB) if side == 0 else (SB, SA)
    out = [DK_CONN, frm, d0, DK_CONN, to, (runs[-1][0] + 4) & 7]
    rows = 0

    def box(ts_):
        if not ts_:
            # καμία: το min μένει +127 και το max -128, άρα (127, 127) και 2 x 2
            # (8 bit) — έξω από τον κόσμο, και το view_add δεν το βλέπει
            r = [0xFF, 127, 127, 2, 2]
        else:
            xs, ys = [x for x, _ in ts_], [y for _, y in ts_]
            r = [0xFF, min(xs) & 255, min(ys) & 255, max(xs) - min(xs) + 1,
                 max(ys) - min(ys) + 1]
        k = 1 + ((runs[-1][0] & 2) >> 1)                 # 1: x (n, s), 2: y (e, w)
        if not (tx, ty)[k - 1] & 1:
            r[k] = (r[k] - 1) & 255
            r[k + 2] += 1
        return r

    if not d0 & 1:
        return out + box(want), rows
    for x, y in want[:l0 + 1]:
        b, c = x - 1, y
        if ((b - cam[0] + 2) & 255) < VIEW_TW + 2 and ((c - cam[1]) & 255) < VIEW_TH:
            out += [DK_CROW, b & 255, c & 255]
            rows += 1
    if len(runs) > 1:
        bx, by = fx >> 1, fy >> 1
        ux = ((tx - fx) > 0) - ((tx - fx) < 0)
        uy = ((ty - fy) > 0) - ((ty - fy) < 0)
        S_, T_ = abs(tx - fx) // 2, abs(ty - fy) // 2
        d1, n1 = runs[1]
        vx, vy = route.DIR_U[d1]
        if vx:                                           # ο οριζόντιος, μόνος του
            t1 = [(ux * T_ - (ux > 0) + k * vx, uy * T_) for k in range(n1)]
            if uy < 0:
                t1 = t1[1:]                              # το «πίσω» της διαγωνίου
        else:
            t1 = [(ux * S_, uy * (S_ - 1) - (uy < 0) + k * vy) for k in range(n1)]
        out += box([(x + bx, y + by) for x, y in t1])
    return out, rows


def redraw_rules(sym, patch=(), n=500):
    """cr_redraw, με stubs στο dirty_push και στο view_add: η πρώτη διαφορά από
    τον κανόνα, ή None."""
    G = Game(sym, list(patch) + redraw_stubs(sym))
    m = G.m
    rnd = random.Random(7373)
    seen = {"αξονικοί": 0, "διαγώνιοι": 0, "στροφές": 0, "μισές σειρές": 0, "τίποτα ορατό": 0}
    case = 0
    while case < n:
        a = (rnd.randrange(-110, 110) & ~1, rnd.randrange(-110, 110) & ~1, rnd.randrange(3))
        d = rnd.randrange(-50, 51) & ~1
        dx, dy = rnd.choice([(d, 0), (0, d), (d, d), (d, -d),
                             (d, rnd.randrange(-50, 51) & ~1), (d, rnd.randrange(-50, 51) & ~1)])
        b = (a[0] + dx, a[1] + dy, rnd.randrange(3))
        ref = max(abs(b[0]), abs(b[1])) < 128 and route.plan(*a, *b)
        if not ref:
            continue
        case += 1
        side, runs = ref
        ends = (a, b) if side == 0 else (b, a)
        G.restore()
        G.plan(a, b)
        want_t = tiles_of(Ends(*ends), 0, runs, 1)
        x, y = rnd.choice(want_t)
        cam = (x - rnd.randrange(-4, VIEW_TW + 4), y - rnd.randrange(-3, VIEW_TH + 3))
        m.poke(sym["CAM_TX"], cam[0] & 255)
        m.poke(sym["CAM_TY"], cam[1] & 255)
        m.poke(sym["RV_PEND"], 0)
        m.write_ram(RPTR, bytes([RLOG & 255, RLOG >> 8]))
        _, A, F = G.run("CR_REDRAW")
        got = list(m.read_ram(RLOG, G.w16(RPTR) - RLOG))
        want, rows = redraw_rule(ends, side, runs, cam)
        if got != want or bool(F & 0x40) != (rows == 0):
            return (f"θόλοι {a} -> {b}, {runs}, κάμερα {cam}: {got} Z={bool(F & 0x40)}, "
                    f"ο κανόνας λέει {want}")
        seen["αξονικοί"] += not runs[0][0] & 1
        seen["διαγώνιοι"] += runs[0][0] & 1
        seen["στροφές"] += len(runs) > 1
        seen["μισές σειρές"] += 0 < rows < runs[0][1] + 1
        seen["τίποτα ορατό"] += runs[0][0] & 1 and rows == 0
    if not patch and min(seen.values()) < 20:
        return f"το σενάριο του redraw δεν έπιασε ό,τι έπρεπε: {seen}"
    print(f"    {n} redraw: {seen}")
    return None


def timing(sym):
    """µs ανά γεωμετρία: plan, walk (κενό callback), check, afford, και commit
    με τον πίνακα γεμάτο εκτός από τις δύο τελευταίες θέσεις."""
    G = Game(sym)
    m = G.m
    out = {}
    for name, (geo, _) in GEOM.items():
        G.restore()
        G.dome(SA, *geo[:3])
        G.dome(SB, *geo[3:])
        m.poke(sym["CR_A"], SA)
        m.poke(sym["CR_B"], SB)
        t_plan, A, _ = G.run("CR_PLAN", step=1)
        t_walk = t_check = t_aff = t_com = None
        if A:
            t_walk, _ = G.walk(CBRET, step=1)
            t_check, _, _ = G.run("CR_CHECK", step=1)
            m.poke(sym["BD_METAL"], 6)
            m.poke(sym["BD_BIOP"], 3)
            m.write_ram(G.g + 6, bytes([0xE8, 3, 0xE8, 3]))
            t_aff, _, _ = G.run("CR_AFFORD", step=1)
            raw = bytearray(MAX_CORR * CORR_REC)
            for i in range(MAX_CORR - 2):
                raw[CORR_REC * i + 4] = 2
            ctypes.memmove(ctypes.addressof(G.ptr[6].contents) + G.gc, bytes(raw), len(raw))
            t_com, _, _ = G.run("CR_COMMIT", step=1)
        out[name] = (t_plan, t_walk, t_check, t_aff, t_com)
    return out


def main():
    sym, _ = TG.build()
    fails = 0
    why = rules(sym)
    if why:
        print(f"ΑΠΟΤΥΧΙΑ: {why}")
        fails += 1
    else:
        print("OK cr_plan = tools/route.py, cr_walk = tiles_of (με τη σειρά), cr_check και "
              "cr_stamp = οι κανόνες σε τυχαίο κόσμο, cr_cost και cr_afford = η αριθμητική")
    why = commit_rules(sym)
    if why:
        print(f"ΑΠΟΤΥΧΙΑ: {why}")
        fails += 1
    else:
        print("OK cr_commit = η πρώτη θέση που χωρά (δύο διπλανές για στροφή, ποτέ μετά την "
              "τελευταία), και πληρωμή και ακμές μόνο τότε")
    why = redraw_rules(sym)
    if why:
        print(f"ΑΠΟΤΥΧΙΑ: {why}")
        fails += 1
    else:
        print("OK cr_redraw = οι δύο αρμοί, οι ορατές σειρές της διαγωνίου, το περίγραμμα "
              "του άξονα, και Z μόνο χωρίς σειρές")
    got = timing(sym)
    slow = []
    for name, (_, ceil) in GEOM.items():
        print(f"    {name:20s} plan, walk, check, afford, commit: {got[name]} us")
        for what, t, c in zip(("plan", "walk", "check", "afford", "commit"), got[name], ceil):
            if c is not None and (t is None or t > c):
                slow.append(f"{name} {what} {t} > {c}")
    if slow:
        print("ΑΠΟΤΥΧΙΑ: πιο αργό από τα βήματα 72 και 81: " + ", ".join(slow))
        fails += 1
    else:
        print("OK καμία γεωμετρία πιο αργή από τα βήματα 72 (walk ως commit) και 81 (plan)")

    # --- αρνητικά ---
    m = cpc.CPC()
    m.run_frames(60)
    assert m.quickload(TG.COLONY, start=False)
    rk, dr, ki, ck = sym["CRS_RK"], sym["CR_DIR"], sym["CRK_IN"], sym["CR_CB_CHK"]
    st = sym["CR_CB_STP"]
    im = m.read_ram(st, 12).find(bytes([0xB3, 0xF8]))            # or e · ret m
    cm = sym["CR_COMMIT"]
    il = m.read_ram(cm, 40).find(bytes([0x78, 0x3D, 0x28]))      # ld a,b · dec a · jr z
    rr = sym["CRR_ROWS"]
    iv = m.read_ram(rr, 60).find(bytes([0xC6, 2, 0xFE, VIEW_TW + 2]))   # add a,2 · cp
    # βήμα 96: bit 0,(hl) · jp nz (crr_half)
    hh = sym["CRR_HALF"]
    ih = m.read_ram(hh, 30).find(bytes([0xCB, 0x46, 0xC2]))
    iy = m.read_ram(ck, 12).find(bytes([0x79, 0xC6, 64, 0xB3]))   # ld a,c · add a,64 · or e
    # η ακτίνα size + 2 είναι δύο inc από το βήμα 86, με τον έλεγχο του airlock
    # (μέγεθος 255) ανάμεσα: inc a · ret z · inc a
    i2 = m.read_ram(rk, 8).find(bytes([0x3C, 0xC8, 0x3C]))
    i4 = m.read_ram(dr, 8).find(bytes([0xC6]))                   # add a,cr_dtab+4
    ik = m.read_ram(ki, 8).find(bytes([0x7E, 0xC6, 2]))          # ld a,(hl) · add a,2
    cs = sym["CR_SIDE"]
    ipe = m.read_ram(cs, 20).find(bytes([0x96, 0xEA]))          # sub (hl) · jp pe
    i64 = m.read_ram(cs, 120).find(bytes([0xCB, 0x77, 0xC2]))    # bit 6,a · jp nz
    assert min(i2, i4, ik, iy, im, il, iv, ipe, i64, ih) >= 0, \
        "δεν βρέθηκαν τα inc a,ret z,inc a / add a,cr_dtab+4 / ld a,c / ret m / jr z / cp VIEW_TW+2" \
        " / jp pe / bit 6,a"
    for label, patch in (("ακτίνα size+3", [(rk + i2 + 1, 0x3C)]),
                         ("το x χωρίς όριο (αναδιπλώνεται, βήμα 80)",
                          [(cs + ipe + 1, 0), (cs + ipe + 2, 0), (cs + ipe + 3, 0)]),
                         ("το -64 κοντά (bit 7 αντί για 6)", [(cs + i64 + 1, 0x7F)]),
                         ("τον πίνακα κατευθύνσεων ένα byte πίσω",
                          [(dr + i4 + 1, (m.peek(dr + i4 + 1) - 1) & 255)]),
                         ("αποτύπωμα size+1 στον έλεγχο", [(ki + ik + 2, 1)]),
                         ("το y έξω από τον κόσμο αόρατο", [(ck + iy, 0x78)]),
                         ("σφραγίδα και έξω από τον κόσμο", [(st + im + 1, 0)])):
        why = rules(sym, patch, n=400)
        if why:
            print(f"OK ΑΡΝΗΤΙΚΟ: με {label} αποτυγχάνει ({why[:90]})")
        else:
            print(f"ΑΠΟΤΥΧΙΑ ΑΡΝΗΤΙΚΟΥ: με {label} περνά")
            fails += 1
    for label, fn, patch in (("ζευγάρι και στην τελευταία θέση", commit_rules,
                              [(cm + il + 2, 0), (cm + il + 3, 0)]),
                             # cr_lnk: το ret nz πριν από το cr_link γίνεται nop
                             ("ακμή και προς εργοτάξιο", commit_rules,
                              [(sym["CR_LINK"] - 1, 0)]),
                             ("σειρά ορατή μόνο από τη στήλη -1", redraw_rules,
                              [(rr + iv + 1, 1)]),
                             ("χωρίς τη μισή στήλη ή σειρά", redraw_rules,
                              [(hh + ih + 2, 0xC3)])):
        why = fn(sym, patch, n=150)
        if why:
            print(f"OK ΑΡΝΗΤΙΚΟ: με {label} αποτυγχάνει ({why[:90]})")
        else:
            print(f"ΑΠΟΤΥΧΙΑ ΑΡΝΗΤΙΚΟΥ: με {label} περνά")
            fails += 1
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
