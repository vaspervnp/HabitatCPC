#!/usr/bin/env python3
"""Η τοποθέτηση του src/build.asm, στο main.sna, απέναντι στους κανόνες της.

  bd_ok      Z αν το byte του κόσμου επιτρέπεται: χωρίς κατοχή (#30), και
             έδαφος, σκόνη ή θεμέλιο (0, 1, 7) — και τα 256
  bd_select  η εγγραφή του καταλόγου στο bd_kind..bd_name, ο κέρσορας στην
             ισοτιμία του αποτυπώματος (μισό tile πιο πέρα, ή πίσω στο 127),
             το μέγεθος της δομής· τίποτα για αντικείμενο έξω από τον κατάλογο
  bd_rect    (κέντρο - μήκος) / 2, και CY αν το αποτύπωμα βγαίνει από το
             -64..63 — με το bd_ty όπως ήταν όταν φταίει το x
  bd_check   τα κακά tiles ανά σειρά (bit ανά στήλη) και το πλήθος τους, 255
             έξω από τον κόσμο, αλλιώς το bd_res (το model του test_terrain)
  bd_afford  Z και A = 0 αν φτάνουν μέταλλο και βιοπλαστικό, NZ και A = 1 αν όχι
  bd_stock_pay  τα δύο αποθέματα μείον το κόστος, 16 bit
  bd_commit  η πρώτη άδεια θέση θόλου ή δομής και η εγγραφή της, το θεμέλιο
             και η κατοχή στο αποτύπωμα, η πληρωμή, η εργασία Build, το ob_idx
             — ή 255 και καμία αλλαγή. ΚΑΜΙΑ ακμή από το βήμα 85: ως τότε έδενε
             το κτίσμα με τον κοντινότερο θόλο όσο μακριά κι αν ήταν· τώρα τους
             δεσμούς τους βάζει το al_commit (tests/test_reach.py)
  bd_redraw  ο θόλος σε DK_SITE, μία ανά σειρά, και NZ· η δομή στο vr_* και,
             αν φαίνεται, ob_struct και ob_clip_full, και Z (stubs)

ΓΙΑΤΙ. Ως το βήμα 73 το build.asm το έβλεπαν σενάρια που χτίζουν μέσα από το
interface (test_build, test_map, test_game, test_reveal, test_link): λίγες
θέσεις, λίγα αντικείμενα. Από 35 σκόπιμα λάθη του βήματος 73, τα 15 πέρασαν και
τα έξι τεστ (μαζί με το test_terrain) — βλ. DESIGN §9.3. Αυτό εδώ τα πιάνει όλα.

Ο κόσμος των δοκιμών έχει βουνό χωρίς φλέβα στο |x|, |y| >= 62, όπως τον
αφήνει η γεννήτρια (§5.5): το περιθώριο του bd_res μένει τότε μέσα στο
επίπεδο, όπως στο παιχνίδι.

Και ο ΧΡΟΝΟΣ: bd_check για κάθε μέγεθος αποτυπώματος σε καθαρό έδαφος και
έξω από τον κόσμο, bd_rect, bd_afford, bd_commit με τη θέση στο τέλος του
πίνακα — όχι πιο αργά από όσο μετρήθηκαν στο βήμα 73. Με το build.asm του
βήματος 72 αποτυγχάνουν όλα.

Αρνητικά, με το snapshot πειραγμένο: το θεμέλιο να μην επιτρέπεται, το πρώτο
tile ένα δεξιότερα, η επόμενη σειρά του ελέγχου +64, επτά NO_MACH, το θεμέλιο
χωρίς κατοχή, A = 255 αντί 1 στο afford, και ο θόλος να γυρνά Z.

ΤΟ ΟΡΥΧΕΙΟ ΠΑΝΤΟΥ (βήμα 123). Το bd_select δίνει στο ορυχείο τιμή 0 όταν ο
πίνακας δεν έχει άλλο — έτοιμο ή εργοτάξιο· μια άδεια εγγραφή που λέει ακόμη
«ορυχείο» δεν μετρά — και μηδενίζει το bd_half. Το bd_check κρατά το bd_half
του bd_res. Το bd_commit ενός ορυχείου γράφει στο ST_OPS το bd_half και, αν
μπήκε δωρεάν, το ST_FREE· πληρώνει το bd_metal· και μετά το bd_mprice ξαναβάζει
την τιμή του καταλόγου (τώρα υπάρχει ορυχείο) και μηδενίζει το bd_half. Τέσσερα
αρνητικά: το bd_select χωρίς bd_mprice, οι άδειες εγγραφές να μετρούν, χωρίς
ST_FREE, και το επόμενο ορυχείο δωρεάν κι αυτό.
"""
import ctypes, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import cpc                                               # noqa: E402
from test_terrain import model, HALF                     # noqa: E402

PROBE, OUT = 0x3E00, 0x3EF0
# Τα stubs ΠΑΝΩ από το PROBE, στο #3F00 (βήμα 95· ως τότε στο #3D60, ακριβώς πάνω
# από τον κώδικα της τράπεζας 0, που κρατούσε έτσι 160 bytes άδεια για τις
# δοκιμές). Το #3F00-#3FBF δεν το αγγίζει το παιχνίδι· το #3FC0 είναι το
# επίμετρο του φορτωτή (src/boot.asm, ENDGAME).
LOG, LPTR, FLAG, STUB = 0x3800, 0x3EFC, 0x3EFE, 0x3F00   # τα stubs του bd_redraw
B1, B4 = 0xC0, 0xC4
K_MINE, NO_MACH, DS_BUILDING, DK_SITE = 4, 255, 1, 6     # src/const.asm
FREE = 1 << 3                                            # ST_FREE, βήμα 123
OB_IX_FIG, OB_IX_DOME, OB_IX_STRUCT = 1, 2, 8
MAX_DEGREE = 8
# µs με το probe (βήμα 73). Στο βήμα 72: 1779, 3344, 5469, 1221, 2407, 208,
# 127, 71, 15514 και 11825.
# Βήμα 123, το ορυχείο παντού: ο έλεγχος του ορυχείου πάνω σε φλέβα 1.424 ->
# 1.437 (το bd_half: ποιο από τα δύο, άλλαξε;)· το commit μιας δομής 892 ->
# 927 (bd_mflags και bd_mprice, που για ό,τι δεν είναι ορυχείο γυρίζουν
# αμέσως)· και το commit ενός ορυχείου, νέο: 1.530, με το bd_mprice να ψάχνει
# στις 31 γεμάτες εγγραφές για ορυχείο (~600 us, μόνο στο FIRE).
CEIL = {"έλεγχος 4x4": 796, "έλεγχος 6x6": 1365, "έλεγχος 8x8": 2124,
        "έλεγχος 3x3": 599, "έλεγχος 4x4 ορυχείο": 1440, "έλεγχος έξω": 153,
        "rect": 66, "afford": 63, "commit θόλου": 4656, "commit δομής": 930,
        "commit ορυχείου": 1540}
# Το commit από το βήμα 85: χωρίς την αναζήτηση του κοντινότερου θόλου (9.362
# και 5.591 ως τότε)· τους δεσμούς τους βάζει το al_commit.


def sb(v):
    return v - 256 if v > 127 else v


def wrld(seed, pool=None):
    """Τυχαίο επίπεδο, με το περίγραμμα βουνό χωρίς φλέβα (§5.5)."""
    r = random.Random(seed)
    pool = pool or [0, 0, 0, 0, 1, 7, 0x40, 0x81, 0xC7, 2, 3, 11, 4, 5, 6, 0x10, 0x20,
                    0x30, 0x17, 0x08, 0x0F]
    p = bytearray(r.choice(pool) for _ in range(0x4000))
    for i in range(0x4000):
        if max(abs((i & 127) - 64), abs((i >> 7) - 64)) >= 62:
            p[i] = 3
    return bytes(p)


class Game:
    def __init__(self, sym, patch=(), stubs=False):
        self.sym = sym
        m = self.m = cpc.CPC()
        m.run_frames(60)
        assert m.quickload(TG.COLONY, start=False), "quickload απέτυχε"
        m.run_frames(150)                                # game_new
        if stubs:
            patch = list(patch) + redraw_stubs(sym)
        for at, v in patch:
            m.poke(at, v)
        self.ptr = [cpc._lib.cpcemu_ram_ptr(m._h, n) for n in range(8)]
        self.keep = [ctypes.string_at(self.ptr[n], 0x4000) for n in range(8)]
        L = {}
        for line in open(os.path.join(ROOT, "build", "layout.asm"), encoding="utf-8"):
            p = line.split()
            if len(p) >= 3 and p[1] == "equ" and p[2].startswith("#"):
                L[p[0]] = int(p[2][1:], 16)
        self.gd, self.gs = L["G_dome_tbl"] - 0x4000, L["G_struct_tbl"] - 0x4000
        self.g, self.jobs = L["G_econ_state"], L["G_job_tbl"]
        self.nodes, self.adj = L["G_rt_nodes"], L["G_node_adj"]
        self.items = [bytes(m.read_ram(sym["BLD_ITEMS"] + 8 * i, 8)) for i in range(11)]

    def restore(self):
        for n in range(8):
            ctypes.memmove(self.ptr[n], self.keep[n], 0x4000)

    def w16(self, a):
        return self.m.peek(a) | self.m.peek(a + 1) << 8

    def bank(self, n, off=0, size=0x4000):
        return ctypes.string_at(ctypes.addressof(self.ptr[n].contents) + off, size)

    def put(self, n, off, data):
        ctypes.memmove(ctypes.addressof(self.ptr[n].contents) + off, bytes(data), len(data))

    def run(self, name, pre=(), step=20):
        """(µs από την αρχή του probe, A, F)."""
        s = self.sym
        code = ([0xF3, 0x31, 0x00, 0x01, 0x01, B1, 0x7F, 0xED, 0x49] + list(pre)
                + [0xCD, s[name] & 255, s[name] >> 8,
                   0xF5, 0xE1, 0x22, OUT & 255, OUT >> 8, 0x18, 0xFE])
        self.m.write_ram(PROBE, bytes(code))
        self.m.set_pc(PROBE)
        end, t = PROBE + len(code) - 2, 0
        while not (end <= self.m.pc <= end + 2):
            self.m.run_us(step)
            t += step
            assert t < 2_000_000, (name, hex(self.m.pc))
        af = self.w16(OUT)
        return t, af >> 8, af & 0xFF

    def cursor(self, cx, cy):
        self.m.poke(self.sym["CUR_HX"], cx & 255)
        self.m.poke(self.sym["CUR_HY"], cy & 255)

    def item(self, i):
        """Η επιλογή όπως την αφήνει το bd_select, χωρίς τον κέρσορα."""
        self.m.write_ram(self.sym["BD_KIND"], self.items[i])
        self.m.poke(self.sym["BD_SIZE"], 2 if self.items[i][1] < K_MINE else 0)


def redraw_stubs(sym):
    """dirty_push: (A, B, C)· vr_tiles: (#FE, vr_tx, vr_ty, vr_w, vr_h) και
    Z/NZ από το FLAG· ob_struct: (#FD, A)· ob_clip_full: (#FC). Το dirty_push
    κρατά B, C, E όπως το αληθινό."""
    lo, hi = LPTR & 255, LPTR >> 8
    dp = [0x2A, lo, hi, 0x77, 0x23, 0x70, 0x23, 0x71, 0x23, 0x22, lo, hi, 0xC9]
    vt = [0x2A, lo, hi, 0x36, 0xFE, 0x23]
    for k in ("VR_TX", "VR_TY", "VR_W", "VR_H"):
        vt += [0x3A, sym[k] & 255, sym[k] >> 8, 0x77, 0x23]
    vt += [0x22, lo, hi, 0x3A, FLAG & 255, FLAG >> 8, 0xB7, 0xC9]
    os_ = [0x2A, lo, hi, 0x36, 0xFD, 0x23, 0x77, 0x23, 0x22, lo, hi, 0xC9]
    oc = [0x2A, lo, hi, 0x36, 0xFC, 0x23, 0x22, lo, hi, 0xC9]
    assert sym["ZZ_BANK0_END"] <= STUB, "ο κώδικας έφτασε στα stubs"
    code = {STUB: dp, STUB + 0x20: vt, STUB + 0x50: os_, STUB + 0x70: oc}
    for name, at in (("DIRTY_PUSH", STUB), ("VR_TILES", STUB + 0x20),
                     ("OB_STRUCT", STUB + 0x50), ("OB_CLIP_FULL", STUB + 0x70)):
        code[sym[name]] = [0xC3, at & 255, at >> 8]
    return [(at + i, v) for at, bs in code.items() for i, v in enumerate(bs)]


def rect_rule(cx, cy, w, h):
    """(tx, ty ή None, εκτός κόσμου)."""
    tx = (sb(cx) - w) >> 1
    if tx < -64 or tx + w > 64:
        return tx, None, True
    ty = (sb(cy) - h) >> 1
    return tx, ty, ty < -64 or ty + h > 64


def snap_rule(c, w):
    """Το κέντρο στην ισοτιμία του πλάτους: μισό tile πιο πέρα — εκτός από το
    127, όπου το «πιο πέρα» είναι η απέναντι άκρη του κόσμου, και πάει μισό
    tile πίσω (βήμα 78)."""
    if not (c ^ w) & 1:
        return c
    return 126 if c == 127 else (c + 1) & 255


def ok_rule(b):
    return not b & 0x30 and b & 7 in (0, 1, 7)


def rules(sym, patch=(), n=600):
    """ok, select, rect, check, afford, pay: η πρώτη διαφορά, ή None."""
    G = Game(sym, patch)
    m = G.m
    rnd = random.Random(73)
    seen = {"έξω από τον κόσμο": 0, "κακά tiles": 0, "χωρίς υλικό": 0, "επιτρέπεται": 0,
            "λίγα υλικά": 0, "δωρεάν": 0}
    for v in range(256):
        G.restore()
        _, _, F = G.run("BD_OK", [0x3E, v])
        if bool(F & 0x40) != ok_rule(v):
            return f"bd_ok #{v:02X}: Z = {bool(F & 0x40)}, ο κανόνας λέει {ok_rule(v)}"
    for case in range(n // 3):
        G.restore()
        i, cx, cy = rnd.choice(list(range(13)) + [8] * 4), rnd.randrange(256), rnd.randrange(256)
        if case % 8 < 2:                    # το ανατολικό και το νότιο χείλος
            cx, cy = (127, cy) if case % 8 == 0 else (cx, 127)
        G.cursor(cx, cy)
        G.item(rnd.randrange(11))
        # ΤΟ ΠΡΩΤΟ ΟΡΥΧΕΙΟ ΔΩΡΕΑΝ (βήμα 123): κάπου-κάπου ένα ορυχείο στον
        # πίνακα — έτοιμο, εργοτάξιο, ή άδεια εγγραφή που λέει ακόμη «ορυχείο».
        structs = bytearray(G.bank(6, G.gs, 32 * 8))
        if rnd.random() < 0.5:
            k = rnd.randrange(32)
            structs[8 * k + 2], structs[8 * k + 4] = K_MINE, rnd.choice([0, 1, 2])
            G.put(6, G.gs, structs)
        mine = any(structs[8 * k + 2] == K_MINE and structs[8 * k + 4] for k in range(32))
        m.poke(sym["BD_HALF"], HALF)
        before = m.read_ram(sym["BD_KIND"], 9)
        G.run("BD_SELECT", [0x3E, i])
        got = (m.read_ram(sym["BD_KIND"], 9), m.peek(sym["CUR_HX"]), m.peek(sym["CUR_HY"]),
               m.peek(sym["BD_HALF"]))
        if i < 11:
            it = bytearray(G.items[i])
            if i == 8 and not mine:
                it[4] = 0
                seen["δωρεάν"] += 1
            want = (bytes(it) + bytes([2 if it[1] < K_MINE else 0]),
                    snap_rule(cx, it[2]), snap_rule(cy, it[3]), 0)
        else:
            want = (before, cx, cy, HALF)
        if got != want:
            return f"bd_select {i} με κέρσορα ({cx}, {cy}): {got}, ο κανόνας λέει {want}"
    for case in range(n):
        G.restore()
        cx, cy, w, h = rnd.randrange(256), rnd.randrange(256), rnd.randrange(1, 9), rnd.randrange(1, 9)
        G.cursor(cx, cy)
        m.write_ram(sym["BD_W"], bytes([w, h]))
        old_ty = rnd.randrange(256)
        m.poke(sym["BD_TY"], old_ty)
        _, _, F = G.run("BD_RECT")
        tx, ty, out = rect_rule(cx, cy, w, h)
        got = (sb(m.peek(sym["BD_TX"])), sb(m.peek(sym["BD_TY"])), bool(F & 1))
        want = (tx, sb(old_ty) if ty is None else ty, out)
        if got != want:
            return f"bd_rect ({sb(cx)}, {sb(cy)}) {w}x{h}: {got}, ο κανόνας λέει {want}"
    for case in range(n):
        G.restore()
        i = rnd.choice([0, 1, 2, 4, 5, 6, 7, 7, 8, 8, 9, 10])
        G.item(i)
        kind, param, w, h = G.items[i][:4]
        if rnd.random() < 0.3:
            cx = rnd.choice([-128 + w, 128 - w, rnd.randrange(-128, 128)]) + rnd.randrange(-4, 5)
            cy = rnd.choice([-128 + h, 128 - h, rnd.randrange(-128, 128)]) + rnd.randrange(-4, 5)
        else:
            cx, cy = rnd.randrange(-110, 110), rnd.randrange(-110, 110)
        cx, cy = max(-128, min(127, cx + ((cx ^ w) & 1))), max(-128, min(127, cy + ((cy ^ h) & 1)))
        G.cursor(cx, cy)
        pool = [0, 0, 0, 1, 7, 0x40, 0x80, 0x87] if rnd.random() < 0.5 else None
        world = wrld(case, pool)
        G.put(4, 0, world)
        m.write_ram(sym["BD_BAD"], bytes(rnd.randrange(256) for _ in range(8)))
        m.poke(sym["BD_NRES"], rnd.randrange(3))
        nres0 = m.peek(sym["BD_NRES"])
        half0 = rnd.choice([0, HALF])                    # το bd_half πριν (βήμα 123)
        m.poke(sym["BD_HALF"], half0)
        _, A, _ = G.run("BD_CHECK", [0x01, B4, 0x7F, 0xED, 0x49])
        half = half0
        tx, ty, out = rect_rule(cx, cy, w, h)
        bad = [0] * 8
        if out:
            want_a, nres = 255, nres0
            seen["έξω από τον κόσμο"] += 1
        else:
            nb = 0
            for r in range(h):
                for c in range(w):
                    if not ok_rule(world[(ty + r + 64) * 128 + tx + c + 64]):
                        bad[r] |= 1 << c
                        nb += 1
            if nb:
                want_a, nres = nb, nres0
                seen["κακά tiles"] += 1
            else:
                want_a, nres, half = model(world, kind, param, w, h, tx, ty, half0)
                seen["χωρίς υλικό" if want_a else "επιτρέπεται"] += 1
        got = (A, list(m.read_ram(sym["BD_BAD"], 8)), m.peek(sym["BD_NRES"]),
               m.peek(sym["BD_HALF"]))
        if got != (want_a, bad, nres, half):
            return (f"bd_check {i} στο ({cx}, {cy}): A, bd_bad, bd_nres, bd_half = {got}, "
                    f"ο κανόνας λέει {(want_a, bad, nres, half)}")
    for case in range(n):
        G.restore()
        cm, cb = rnd.randrange(50), rnd.randrange(30)
        m.write_ram(sym["BD_METAL"], bytes([cm, cb]))
        sm = max(0, cm + rnd.choice([-1, 0, 1, rnd.randrange(-300, 300)]))
        sp = max(0, cb + rnd.choice([-1, 0, 1, rnd.randrange(-300, 300)]))
        if rnd.random() < 0.1:
            sm, sp = rnd.randrange(65536), rnd.randrange(65536)
        m.write_ram(G.g + 6, bytes([sm & 255, sm >> 8, sp & 255, sp >> 8]))
        _, A, F = G.run("BD_AFFORD")
        ok = sm >= cm and sp >= cb
        if (A, bool(F & 0x40)) != ((0, True) if ok else (1, False)):
            return f"bd_afford {cm}/{cb} με {sm}/{sp}: A = {A}, Z = {bool(F & 0x40)}"
        seen["λίγα υλικά"] += not ok
        G.run("BD_STOCK_PAY")
        got = (G.w16(G.g + 6), G.w16(G.g + 8))
        if got != ((sm - cm) & 0xFFFF, (sp - cb) & 0xFFFF):
            return f"bd_stock_pay {cm}/{cb} από {sm}/{sp}: {got}"
    if not patch and min(seen.values()) < 20:
        return f"το σενάριο δεν έπιασε ό,τι έπρεπε: {seen}"
    print(f"    {seen}")
    return None


def commit_rules(sym, patch=(), n=300):
    """bd_commit: η πρώτη διαφορά από τον κανόνα, ή None."""
    G = Game(sym, patch)
    m = G.m
    rnd = random.Random(7373)
    rm_list = m.read_ram(sym["RM_LIST"], 16)
    seen = {"θόλοι": 0, "δομές": 0, "γεμάτος": 0, "Supply": 0, "Build": 0,
            "ορυχεία": 0, "ορυχεία δωρεάν": 0}
    for case in range(n):
        G.restore()
        i = rnd.choice([0, 1, 2, 4, 5, 6, 7, 8, 8, 9, 10])   # το ορυχείο διπλό (βήμα 123)
        G.item(i)
        kind, param, w, h = G.items[i][:4]
        size = 2 if param < K_MINE else 0
        cx, cy = rnd.randrange(-100, 100), rnd.randrange(-100, 100)
        cx, cy = cx + ((cx ^ w) & 1), cy + ((cy ^ h) & 1)
        G.cursor(cx, cy)
        # το bd_tx, bd_ty όπως τα αφήνει ο έλεγχος πριν από κάθε τοποθέτηση
        m.write_ram(sym["BD_TX"], bytes([((cx - w) >> 1) & 255, ((cy - h) >> 1) & 255]))
        rsel = rnd.randrange(12)
        m.poke(sym["BD_RSEL"], rsel)
        m.poke(sym["BD_NODE"], rnd.randrange(256))
        m.write_ram(G.g + 6, bytes([0xE8, 3, 0xE8, 3]))
        m.poke(sym["RT_DIRTY"], 0)
        m.poke(sym["OB_IDX"], 0)
        # και με το bit 3 (του πόρου, §3.5): η σφραγίδα κρατά μόνο το decor
        world = wrld(case, [0, 1, 7, 0x40, 0x81, 0xC7, 0x08, 0x4B, 0x3F])
        G.put(4, 0, world)
        # οι θόλοι και οι δομές
        k = rnd.random()
        domes = bytearray(G.bank(6, G.gd, 64 * 24))
        for d in range(64):
            o = 24 * d
            if 0.1 <= k < 0.2:
                domes[o + 4] = 0                         # κανένας: το πρώτο κτίριο
            elif k < 0.1 or rnd.random() < 0.5:
                domes[o:o + 2] = bytes([rnd.randrange(-128, 128) & 255 for _ in range(2)])
                domes[o + 4] = rnd.choice([1, 2])
            else:
                domes[o + 4] = 0
        structs = bytearray(G.bank(6, G.gs, 32 * 8))
        for s_ in range(32):
            structs[8 * s_ + 4] = 2 if k < 0.05 or (k < 0.9 and rnd.random() < 0.6) else 0
        G.put(6, G.gd, domes)
        G.put(6, G.gs, structs)
        deg = bytearray(m.read_ram(G.nodes, 96))
        for x in range(96):
            deg[x] = rnd.choice([0, 1, 3, 7, 8]) if rnd.random() < 0.3 else deg[x] & 7
        m.write_ram(G.nodes, bytes(deg))
        adj = bytearray(m.read_ram(G.adj, 8 * 96))
        jobs = bytearray(m.read_ram(G.jobs, 5 * 32))
        full = rnd.random() < 0.1                        # γεμάτος πίνακας εργασιών
        for j in range(32):
            jobs[5 * j] = 0 if full or rnd.random() < 0.7 else 255
        m.write_ram(G.jobs, bytes(jobs))
        # ΤΟ ΣΥΝΟΛΟ ΤΟΥ al_plan (βήμα 88): ό,τι κόστισε, με τους διαδρόμους.
        # Μια δομή ως 15 φορτία το υλικό (το assert του src/link.asm), ένας
        # θόλος ως 255· και κάπου-κάπου τίποτα, που φέρνει κατευθείαν Build.
        lim = 150 if kind else 400
        cm = 0 if rnd.random() < 0.2 else rnd.randrange(1, lim + 1)
        cb = 0 if rnd.random() < 0.3 else rnd.randrange(1, lim // 2 + 1)
        m.write_ram(sym["CR_METAL"], bytes([cm & 255, cm >> 8]))
        m.write_ram(sym["CR_BIOP"], bytes([cb & 255, cb >> 8]))
        lm, lb = -(-cm // 10), -(-cb // 10)
        # ΤΟ ΟΡΥΧΕΙΟ (βήμα 123): εκτός φλέβας ή όχι (bd_half), δωρεάν ή όχι
        # (bd_metal, που το έγραψε το bd_mprice) — και τα δύο στο ST_OPS.
        half = rnd.choice([0, HALF])
        bm = rnd.choice([0, G.items[i][4]]) if param == K_MINE and kind == 1 else G.items[i][4]
        m.poke(sym["BD_HALF"], half)
        m.poke(sym["BD_METAL"], bm)
        _, A, _ = G.run("BD_COMMIT")
        # --- ο κανόνας ---
        want_d, want_s, want_w = bytearray(domes), bytearray(structs), bytearray(world)
        want_deg, want_adj, want_jobs = bytearray(deg), bytearray(adj), bytearray(jobs)
        stock, dirty, idx = (1000, 1000), 0, 0
        if kind == 0:
            slot = next((d for d in range(64) if domes[24 * d + 4] == 0), None)
            node = slot
            if slot is not None:
                o = 24 * slot
                want_d[o:o + 24] = bytes([cx & 255, cy & 255, param, rm_list[rsel], DS_BUILDING,
                                          0, lm, lb] + [NO_MACH] * 8 + [0] * 8)
        else:
            slot = next((s_ for s_ in range(32) if structs[8 * s_ + 4] == 0), None)
            node = None if slot is None else 64 + slot
            if slot is not None:
                ops = (half | (0 if bm else FREE)) if param == K_MINE else 0
                want_s[8 * slot:8 * slot + 8] = bytes([cx & 255, cy & 255, param, size,
                                                       DS_BUILDING, 0, ops, lm << 4 | lb])
                seen["ορυχεία δωρεάν" if param == K_MINE and not bm else
                     "ορυχεία" if param == K_MINE else "δομές"] += param == K_MINE
        if node is None:
            want_a = 255
            seen["γεμάτος"] += 1
        else:
            want_a = node
            seen["θόλοι" if kind == 0 else "δομές"] += 1
            tx, ty = (cx - w) >> 1, (cy - h) >> 1
            for r in range(h):
                for c in range(w):
                    a = (ty + r + 64) * 128 + tx + c + 64
                    # θόλος: το έδαφός του, μόνο κατοχή (βήμα 94)· δομή: θεμέλιο
                    want_w[a] = (want_w[a] & 0xCF | 0x10 if kind == 0
                                 else want_w[a] & 0xC0 | 0x17)
            stock = (1000 - bm, 1000 - G.items[i][5])
            # ο γράφος δεν αλλάζει (βήμα 85): ούτε βαθμοί, ούτε γείτονες, ούτε rt_dirty
            # Supply για ό,τι χρωστιέται, μέταλλο πρώτα· αν τίποτα, Build
            for k, n_ in ((7, lm), (8, lb)) if lm or lb else ((0, 1),):
                j = next((j for j in range(32) if want_jobs[5 * j] == 255), None)
                if n_ and j is not None:
                    want_jobs[5 * j:5 * j + 5] = bytes([k, node, 255, 4 if k else 5, node])
                    seen["Supply" if k else "Build"] += 1
            idx = OB_IX_FIG + (OB_IX_DOME if kind == 0 else OB_IX_STRUCT)
        got = {"A": A, "θόλοι": G.bank(6, G.gd, 64 * 24), "δομές": G.bank(6, G.gs, 32 * 8),
               "κόσμος": G.bank(4), "αποθέματα": (G.w16(G.g + 6), G.w16(G.g + 8)),
               "βαθμοί": m.read_ram(G.nodes, 96), "γείτονες": m.read_ram(G.adj, 8 * 96),
               "εργασίες": m.read_ram(G.jobs, 5 * 32), "rt_dirty": m.peek(sym["RT_DIRTY"]),
               "ob_idx": m.peek(sym["OB_IDX"]),
               "bd_metal, bd_half": (m.peek(sym["BD_METAL"]), m.peek(sym["BD_HALF"]))}
        want = {"A": want_a, "θόλοι": bytes(want_d), "δομές": bytes(want_s),
                "κόσμος": bytes(want_w), "αποθέματα": stock, "βαθμοί": bytes(want_deg),
                "γείτονες": bytes(want_adj), "εργασίες": bytes(want_jobs), "rt_dirty": dirty,
                "ob_idx": idx,
                # μετά από τοποθέτηση το bd_mprice: το επόμενο ορυχείο πληρώνει, το
                # bd_half από την αρχή· με γεμάτο πίνακα τίποτα από τα δύο
                "bd_metal, bd_half": ((bm, half) if node is None else
                                      (G.items[8][4] if param == K_MINE and kind == 1 else bm, 0))}
        for key in got:
            if got[key] != want[key]:
                g_, w_ = got[key], want[key]
                if isinstance(g_, bytes):
                    at = next(j for j in range(len(g_)) if g_[j] != w_[j])
                    g_, w_ = f"byte {at}: {g_[at]}", w_[at]
                return f"bd_commit {i} στο ({cx}, {cy}): {key} {g_}, ο κανόνας λέει {w_}"
    if not patch and min(seen.values()) < 10:
        return f"το σενάριο του commit δεν έπιασε ό,τι έπρεπε: {seen}"
    print(f"    {n} commit: {seen}")
    return None


def redraw_rules(sym, patch=(), n=200):
    """bd_redraw με stubs: η πρώτη διαφορά από τον κανόνα, ή None."""
    G = Game(sym, patch, stubs=True)
    m = G.m
    rnd = random.Random(737)
    for case in range(n):
        G.restore()
        i = rnd.choice([0, 1, 2, 4, 5, 6, 7, 8, 9, 10])
        G.item(i)
        kind, w, h = G.items[i][0], G.items[i][2], G.items[i][3]
        cx, cy = rnd.randrange(-100, 100), rnd.randrange(-100, 100)
        cx, cy = cx + ((cx ^ w) & 1), cy + ((cy ^ h) & 1)
        G.cursor(cx, cy)
        node = rnd.randrange(64) if kind == 0 else 64 + rnd.randrange(32)
        m.poke(sym["BD_NODE"], node)
        pend = rnd.randrange(200)
        m.poke(sym["RV_PEND"], pend)
        vis = rnd.randrange(2)
        m.poke(FLAG, vis)
        m.write_ram(LPTR, bytes([LOG & 255, LOG >> 8]))
        _, A, F = G.run("BD_REDRAW")
        got = (list(m.read_ram(LOG, G.w16(LPTR) - LOG)), m.peek(sym["RV_PEND"]), bool(F & 0x40))
        tx, ty = ((cx - w) >> 1) & 255, ((cy - h) >> 1) & 255
        if kind == 0:
            want = ([v for r in range(h) for v in (DK_SITE, node, r)], (pend + h) & 255, False)
        else:
            want = ([0xFE, tx, ty, w, h] + ([0xFD, node - 64, 0xFC] if vis else []), pend, True)
        if got != want:
            return f"bd_redraw {i} στο ({cx}, {cy}): {got}, ο κανόνας λέει {want}"
    print(f"    {n} redraw")
    return None


def timing(sym):
    """µs ανά περίπτωση του CEIL."""
    G = Game(sym)
    m = G.m
    out = {}
    clear = bytes(0x4000)
    for name, i, c in (("έλεγχος 4x4", 0, (0, 0)), ("έλεγχος 6x6", 1, (0, 0)),
                       ("έλεγχος 8x8", 2, (0, 0)), ("έλεγχος 3x3", 4, (1, 1)),
                       ("έλεγχος 4x4 ορυχείο", 8, (0, 0)), ("έλεγχος έξω", 2, (-126, 0))):
        G.restore()
        G.item(i)
        G.cursor(*c)
        w = bytearray(clear)
        if i == 8:
            w[(0 + 64) * 128 + 3 + 64] = 11                # φλέβα στο περιθώριο
        G.put(4, 0, w)
        out[name] = G.run("BD_CHECK", [0x01, B4, 0x7F, 0xED, 0x49], step=1)[0]
    G.restore()
    G.item(2)
    G.cursor(-127, 0)
    out["rect"] = G.run("BD_RECT", step=1)[0]
    m.write_ram(G.g + 6, bytes([0xE8, 3, 0xE8, 3]))
    out["afford"] = G.run("BD_AFFORD", step=1)[0]
    for name, i in (("commit θόλου", 0), ("commit δομής", 4), ("commit ορυχείου", 8)):
        G.restore()
        G.item(i)
        G.cursor(0, 0)
        G.run("BD_RECT")
        G.put(4, 0, clear)
        m.write_ram(G.g + 6, bytes([0xE8, 3, 0xE8, 3]))
        d = bytearray(G.bank(6, G.gd, 64 * 24))
        for k in range(64):
            d[24 * k + 4] = 0 if k == 63 else 2          # η τελευταία θέση
        s_ = bytearray(G.bank(6, G.gs, 32 * 8))
        for k in range(32):
            s_[8 * k + 4] = 0 if k == 31 else 2
        G.put(6, G.gd, d)
        G.put(6, G.gs, s_)
        # το κόστος του ίδιου του κτίσματος, όπως το αφήνει το al_plan (βήμα 88)
        m.write_ram(sym["CR_METAL"], bytes([G.items[i][4], 0]))
        m.write_ram(sym["CR_BIOP"], bytes([G.items[i][5], 0]))
        out[name] = G.run("BD_COMMIT", step=1)[0]
    return out


def main():
    sym, _ = TG.build()
    fails = 0
    for fn, what in ((rules, "bd_ok (256), bd_select, bd_rect, bd_check, bd_afford, "
                              "bd_stock_pay = οι κανόνες"),
                     (commit_rules, "bd_commit = η θέση, η εγγραφή, το θεμέλιο, η πληρωμή, "
                                    "η εργασία, το ob_idx — και καμία ακμή"),
                     (redraw_rules, "bd_redraw = DK_SITE ανά σειρά για θόλο, vr_* και "
                                    "ob_struct για δομή")):
        why = fn(sym)
        if why:
            print(f"ΑΠΟΤΥΧΙΑ: {why}")
            fails += 1
        else:
            print(f"OK {what}")
    got = timing(sym)
    slow = [f"{k} {got[k]} > {c}" for k, c in CEIL.items() if got[k] > c]
    print("    " + ", ".join(f"{k} {v}" for k, v in got.items()) + " us")
    if slow:
        print("ΑΠΟΤΥΧΙΑ: πιο αργό από τα ταβάνια (βήμα 73, και 123 για το ορυχείο): " + ", ".join(slow))
        fails += 1
    else:
        print("OK τίποτα πιο αργό από τα ταβάνια (βήμα 73, και 123 για το ορυχείο)")

    # --- αρνητικά ---
    m = cpc.CPC()
    m.run_frames(60)
    assert m.quickload(TG.COLONY, start=False)

    def call(label):
        return [0xCD, sym[label] & 255, sym[label] >> 8]

    def find(label, pat, span=64):
        i = m.read_ram(sym[label], span).find(bytes(pat))
        assert i >= 0, f"δεν βρέθηκε το {pat} στο {label}"
        return sym[label] + i

    neg = [("θεμέλιο όχι", rules, [(find("BD_OK", [0xFE, 6]) + 1, 7)]),
           ("πρώτο tile ένα δεξιότερα", rules, [(find("BDR_ONE", [0xD6, 64]) + 1, 63)]),
           ("επόμενη σειρά +64", rules, [(find("BD_CHECK", [0xC6, 128], 96) + 1, 64)]),
           ("επτά NO_MACH", commit_rules, [(find("BD_COMMIT", [0x01, NO_MACH, 8], 160) + 2, 7)]),
           # ld de,#C000 + W_FOUNDATION + W_OCC_STRUCT (βήμα 88· ως τότε or #17)
           ("το θεμέλιο χωρίς κατοχή", commit_rules,
            [(find("BD_LINK", [0x11, 0x17, 0xC0]) + 1, 0x07)]),
           # ld a,(bd_kind) · or a · jr nz,bst_rl γίνεται jr: θεμέλιο και ο θόλος (ως το 93)
           ("ο θόλος με θεμέλιο", commit_rules,
            [(find("BD_LINK", [0xB7, 0x20], 40) + 1, 0x18)]),
           # ΤΑ ΧΡΕΗ (βήμα 88): με το ld (hl),d του D_OPS σβησμένο, ο θόλος δεν
           # χρωστά βιοπλαστικό ενώ η εργασία του δημοσιεύεται
           ("το D_OPS χωρίς το βιοπλαστικό", commit_rules,
            [(find("BD_COMMIT", [0x2B, 0x73, 0x23, 0x72], 160) + 3, 0)]),
           ("A = 255 στο afford", rules,
            [(a, 0) for a in (lambda p: (p, p + 1))(find("BDA_NO", [0xED, 0x44]))]),
           ("ο θόλος γυρνά Z", redraw_rules, [(find("BDR_LP", [0x1C, 0xC9]), 0)]),
           # ΤΟ ΠΡΩΤΟ ΟΡΥΧΕΙΟ ΔΩΡΕΑΝ (βήμα 123)
           ("το bd_select χωρίς το bd_mprice", rules,
            [(a, 0) for a in (lambda p: (p, p + 1, p + 2))(find("BD_SELECT", call("BD_MPRICE"), 32))]),
           ("το bd_mprice μετρά και τις άδειες εγγραφές", rules,
            [(find("BMP_MINE", [0xB7, 0x28], 16) + 2, 0)]),
           ("το δωρεάν ορυχείο χωρίς ST_FREE", commit_rules,
            [(find("BD_MFLAGS", [0xF6, 8], 24) + 1, 0)]),
           ("το επόμενο ορυχείο δωρεάν κι αυτό", commit_rules,
            [(a, 0) for a in (lambda p: (p, p + 1, p + 2))(find("BDK_POST", call("BD_MPRICE"), 8))])]
    for label, fn, patch in neg:
        why = fn(sym, patch, n=150)
        if why:
            print(f"OK ΑΡΝΗΤΙΚΟ: με {label} αποτυγχάνει ({why[:90]})")
        else:
            print(f"ΑΠΟΤΥΧΙΑ ΑΡΝΗΤΙΚΟΥ: με {label} περνά")
            fails += 1
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
