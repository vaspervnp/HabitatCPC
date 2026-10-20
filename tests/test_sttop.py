#!/usr/bin/env python3
"""Το όριο σάρωσης των δομών (βήμα 157, src/top.asm, DESIGN §4.2).

Από το βήμα 156 ο πίνακας των δομών έχει 48 θέσεις, και κάθε πέρασμά του
πλήρωνε και τις άδειες. Από το 157 σταματούν όλα στο ST_TOP: η ψηλότερη θέση
σε χρήση + 1, ζυγό, τουλάχιστον 2, σε πέντε μορφές στις θέσεις 112-116 του
node_deg (src/const.asm). Η πρόζα:

  ΜΟΡΦΕΣ     για κάθε ζυγό t από 2 ως 48, το st_set (με probe, στο OV_R1)
             γράφει ό,τι λέει το codeat.top_bytes(t) — το αντίγραφο που
             γράφουν οι δοκιμές για τον πίνακα που στήνουν — και rt_n = 64 + t.
  ΜΕΤΡΗΜΑ    σε 60 πίνακες (άδειος, μόνο η 0, η 1, η 2, η 47, και τυχαίοι με
             κενά), το st_recount δίνει τις μορφές του codeat.top_of: η
             ψηλότερη μη άδεια θέση + 1, ζυγό, τουλάχιστον 2.
  ΑΡΧΗ       η εικόνα του παιχνιδιού έχει τις μορφές των 48 (ό,τι τρέχει
             χωρίς να περάσει από το wheel_reset σαρώνει όλο τον πίνακα, όπως
             ως το βήμα 156)· μετά το game_new το main.sna έχει 2 (μόνο το
             σκάφος) και το colony.sna το όριο του πίνακά του. Με τις μορφές
             μηδέν, όπως σε σώσιμο πριν από το βήμα 157, το wheel_load του
             φορτώματος τις ξαναβρίσκει.
  ΑΝΕΒΑΣΜΑ   ηλιακά από τον παίκτη (tools/balance.py) στην αποικία δοκιμών,
             ως τη θέση 10: μετά από κάθε τοποθέτηση οι μορφές είναι του
             top_of του πίνακα, και το rt_n 64 + ST_TOP. Η κατεδάφιση της
             ψηλότερης δεν το κατεβάζει, και το επόμενο ηλιακό μπαίνει στην
             άδεια θέση με το όριο ίδιο.
  ΠΕΡΑΣΜΑΤΑ  μία δομή στη θέση 20 του main.sna, και κάθε πέρασμα τη βλέπει με
             όριο 22 και όχι με 20: το ef_lp του κύκλου ροής (EC_PPROD), το
             rr_pad (EC_PADNODE), το ob_struct_sort (st_ord), το sp_sweep (οι
             Supply του εργοταξίου), το bd_mprice (το ορυχείο δεν είναι πια
             δωρεάν), το al_scans (κοντά στον κέρσορα), η κρούση μετεωρίτη
             (εργοτάξιο ξανά, όχι κρατήρας), η αρχή της βροχής (το κέντρο της
             εκεί, όχι στο σκάφος) και η δρομολόγηση (η γραμμή της στο NEXTHOP).
  ΚΟΣΤΟΣ     τα ίδια εννέα, με όριο 22 και τη δομή 20 μη ορατή εκεί που
             σταματούν (ηλιακό χωρίς πλατφόρμα, κέρσορας μακριά, κρούση στο
             έδαφος, βροχή που γυρίζει ως το σκάφος), κάτω από το ταβάνι τους
             (CEIL): 26 άδειες θέσεις λιγότερες από τις 48 του βήματος 156.

Αρνητικά, με τον κώδικα πειραγμένο, ένα τη φορά: το st_set χωρίς το μισό (οι
ΜΟΡΦΕΣ), το st_count που ξεκινά από τη θέση 31 (το ΜΕΤΡΗΜΑ), το wheel_reset
χωρίς το st_recount (η ΑΡΧΗ), το st_raise που δεν ανεβάζει (το ΑΝΕΒΑΣΜΑ), και
κάθε πέρασμα με τις 48 θέσεις του βήματος 156 αντί για το όριο — η δομή 20
φαίνεται και με όριο 20 (ΠΕΡΑΣΜΑΤΑ), και το κόστος περνά το ταβάνι (ΚΟΣΤΟΣ).
"""
import contextlib, copy, ctypes, io, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import test_demolish as D                                # noqa: E402
import test_unlink as U                                  # noqa: E402
import test_fit as TF                                    # noqa: E402
import test_impact as TI                                 # noqa: E402
import balance as B                                      # noqa: E402
import econ as EC                                        # noqa: E402
import codeat                                            # noqa: E402
import cpc                                               # noqa: E402

FAIL = []
NS, ND = EC.MAX_STRUCT, EC.MAX_DOME
PROBE, CB = 0x3E80, 0x3EF0                # το probe, και η ρουτίνα του al_scans
K = 20                                    # η θέση της δομής των ΠΕΡΑΣΜΑΤΩΝ
LOW, HIGH = K, K + 2                      # όριο που δεν τη βλέπει, και που τη βλέπει
EC_PPROD, EC_DAY, EC_STORM, EC_PADNODE = 32, 49, 61, 81
EC_METEOR, EC_MCX, EC_MCY, EC_MRND = 86, 87, 88, 89
J_SUPPLY = 1                              # src/const.asm
# ΤΑ ΤΑΒΑΝΙΑ ΤΟΥ ΚΟΣΤΟΥΣ, µs με όριο 22. Μετρημένα στο βήμα 157: ροή 1.610,
# πίστα 2.097, ευρετήριο 466, σάρωμα 10.325, τιμή 355, κέρσορας 366, κρούση
# 1.998, βροχή 6.354, δρόμοι 127.430· με τον κώδικα για 48 θέσεις (τα
# αρνητικά) 2.051, 2.539, 855, 11.624, 692, 598, 2.490, 7.393 και 158.220 — 26
# άδειες θέσεις, 17, 17, 15, 50, 13, 9, 19 και 40 µs η καθεμία, και 1.184 η
# μοναχική πηγή. Κάθε ταβάνι είναι περίπου στο ένα τρίτο της απόστασης.
CEIL = {"ροή": 1700, "πίστα": 2200, "ευρετήριο": 560, "σάρωμα": 10700, "τιμή": 450,
        "κέρσορας": 440, "κρούση": 2200, "βροχή": 6700, "δρόμοι": 135000}


def check(ok, msg):
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ ") + msg, flush=True)
    if not ok:
        FAIL.append(msg)


def layout():
    L = {}
    for line in open(os.path.join(ROOT, "build", "layout.asm"), encoding="utf-8"):
        p = line.split()
        if len(p) >= 3 and p[1] == "equ" and p[2].startswith("#"):
            L[p[0]] = int(p[2][1:], 16)
    return L


L = layout()
GS = L["G_struct_tbl"]


class Box:
    """Ενα παιχνίδι μετά το game_new, για κλήσεις με probe. Τα πειράγματα, όπως
    του test_demolish — ("ram", διεύθυνση, τιμή) ή ("hole", (τράπεζα, δείκτης),
    τιμή) — μπαίνουν και πριν από την εκκίνηση (το st_recount τρέχει σε αυτήν)
    και μετά (το OV_R1 το γεμίζει η εκκίνηση). Το restore() γυρίζει και τις οκτώ
    τράπεζες όπως ήταν μετά."""

    def __init__(self, sym, patch=(), sna=None):
        self.sym, self.g = sym, L["G_econ_state"]
        m = self.m = cpc.CPC()
        m.run_frames(60)
        assert m.quickload(sna or TG.SNA, start=False), "quickload απέτυχε"
        self.patch(patch)
        m.run_frames(250)
        self.patch(patch)
        self.keep = [self.bank(n) for n in range(8)]

    def patch(self, patch):
        for where, at, v in patch:
            if where == "ram":
                self.m.poke(at, v)
            else:
                self.ptr(at[0])[at[1]] = v

    def ptr(self, n):
        return cpc._lib.cpcemu_ram_ptr(self.m._h, n)

    def bank(self, n):
        return ctypes.string_at(self.ptr(n), 0x4000)

    def put(self, n, off, data):
        ctypes.memmove(ctypes.addressof(self.ptr(n).contents) + off, bytes(data), len(data))

    def restore(self):
        for n in range(8):
            self.put(n, 0, self.keep[n])

    def put6(self, addr, data):
        self.put(6, addr - 0x4000, data)

    def get6(self, addr, n):
        return self.bank(6)[addr - 0x4000:addr - 0x4000 + n]

    def table(self):
        return self.get6(GS, NS * 8)

    def probe(self, body, bank=0xC6, step=1, limit=2_000_000):
        """di · ld sp · τράπεζα · body · jr $ -> µs, ή None."""
        code = [0xF3, 0x31, 0x00, 0x01, 0x01, bank, 0x7F, 0xED, 0x49] + list(body) + [0x18, 0xFE]
        self.m.write_ram(PROBE, bytes(code))
        self.m.set_pc(PROBE)
        end, t = PROBE + len(code) - 2, 0
        while not (end <= self.m.pc <= end + 2):
            self.m.run_us(step)
            t += step
            if t > limit:
                return None
        return t

    def call(self, name, pre=(), bank=0xC6, step=1):
        a = self.sym[name]
        return self.probe(list(pre) + [0xCD, a & 255, a >> 8], bank, step)


def w(a):
    return [a & 255, a >> 8]


# --------------------------------------------------------------------------
# ΜΟΡΦΕΣ, ΜΕΤΡΗΜΑ, ΑΡΧΗ
# --------------------------------------------------------------------------
def forms(X):
    t, b = codeat.top(X.m)
    return t, b, X.m.peek(X.sym["RT_N"])


def setter(X):
    """ΜΟΡΦΕΣ. None, ή η πρώτη διαφορά."""
    for t in range(2, NS + 1, 2):
        X.restore()
        if X.call("ST_SET", [0x3E, t], bank=0xC0) is None:
            return f"ΜΟΡΦΕΣ: το st_set({t}) δεν γύρισε"
        _, b, rn = forms(X)
        if b != codeat.top_bytes(t) or rn != ND + t:
            return (f"ΜΟΡΦΕΣ: st_set({t}) έγραψε {list(b)} και rt_n {rn}, το codeat λέει "
                    f"{list(codeat.top_bytes(t))} και {ND + t}")
    return None


def counter(X):
    """ΜΕΤΡΗΜΑ. (πόσοι πίνακες, None) ή (…, η πρώτη διαφορά)."""
    rnd = random.Random(157)
    cases = [[], [0], [1], [2], [NS - 1], [0, 1, 2, 3], list(range(NS))]
    while len(cases) < 60:
        top = rnd.randrange(NS)
        cases.append(sorted(set([top] + [s for s in range(top) if rnd.random() < 0.4])))
    for used in cases:
        X.restore()
        st = bytearray(X.table())
        for s in range(NS):
            st[8 * s + 4] = rnd.choice([1, 2]) if s in used else 0
        X.put6(GS, st)
        X.put(2, codeat.TOP_AT - 0x8000, bytes(5))          # ό,τι κι αν ήταν πριν
        if X.call("ST_RECOUNT", bank=0xC0) is None:
            return len(cases), f"ΜΕΤΡΗΜΑ: το st_recount δεν γύρισε με τις {used}"
        want = codeat.top_of(st)
        t, b, rn = forms(X)
        if b != codeat.top_bytes(want) or rn != ND + want:
            return len(cases), (f"ΜΕΤΡΗΜΑ: με τις θέσεις {used} ST_TOP {t} ({list(b)}, rt_n {rn}), "
                                f"η πρόζα λέει {want}")
    return len(cases), None


def start(sym, patch=()):
    """ΑΡΧΗ. None, ή η πρώτη διαφορά."""
    img = open(TG.SNA, "rb").read()
    raw = img[0x100 + codeat.TOP_AT:0x100 + codeat.TOP_AT + 5]
    if raw != codeat.top_bytes(NS) or img[0x100 + sym["RT_N"]] != ND + NS:
        return (f"ΑΡΧΗ: η εικόνα έχει {list(raw)} και rt_n {img[0x100 + sym['RT_N']]}, "
                f"η πρόζα λέει τις 48: {list(codeat.top_bytes(NS))}, {ND + NS}")
    for sna in (TG.SNA, TG.COLONY):
        X = Box(sym, patch, sna)
        want = codeat.top_of(X.table())
        t, b, rn = forms(X)
        if b != codeat.top_bytes(want) or rn != ND + want:
            return (f"ΑΡΧΗ: το {os.path.basename(sna)} μετά το game_new έχει ST_TOP {t} "
                    f"({list(b)}, rt_n {rn}), ο πίνακάς του λέει {want}")
        if sna == TG.SNA and want != 2:
            return f"ΑΡΧΗ: το main.sna έχει δομές {want}, όχι μόνο το σκάφος"
        X.put(2, codeat.TOP_AT - 0x8000, bytes(5))
        if X.call("WHEEL_LOAD", bank=0xC0) is None:
            return "ΑΡΧΗ: το wheel_load δεν γύρισε"
        t, b, rn = forms(X)
        if b != codeat.top_bytes(want) or rn != ND + want:
            return (f"ΑΡΧΗ: το φόρτωμα στο {os.path.basename(sna)} με τις μορφές μηδέν άφησε "
                    f"{list(b)} και rt_n {rn}, όχι {want}")
    return None


# --------------------------------------------------------------------------
# ΑΝΕΒΑΣΜΑ
# --------------------------------------------------------------------------
def raising(sym, g, patch=(), quiet=False):
    """ΑΝΕΒΑΣΜΑ. None, ή η πρώτη διαφορά."""
    G, F = D.game(sym, g, patch)
    G.run(500_000)
    G.settle()
    centre = U.tile(D.centre(G, 65))
    log, spots = [], []

    def now():
        st = bytes(G.bank(6)[GS - 0x4000:GS - 0x4000 + NS * 8])
        return codeat.top_of(st), codeat.top(G.m), G.m.peek(sym["RT_N"])

    while True:
        want, (t, b), rn = now()
        if b != codeat.top_bytes(want) or rn != ND + want:
            return (f"ΑΝΕΒΑΣΜΑ: μετά από {log} το ST_TOP είναι {t} ({list(b)}, rt_n {rn}), "
                    f"ο πίνακας λέει {want}")
        free = next(s for s in range(NS) if not D.rec(G, 64 + s)[4])
        if free > 10:
            break
        at, _ = U.find_spot(G, sym, U.SOLAR, lambda r, a: True, centre, rmax=30)
        if not at:
            return f"ΑΝΕΒΑΣΜΑ: καμία θέση για ηλιακό γύρω από το {centre}"
        F.set_stocks(TF.STOCK, TF.STOCK)
        n = U.place(G, sym, g, U.SOLAR, at)
        if n != 64 + free:
            return f"ΑΝΕΒΑΣΜΑ: το ηλιακό στο {at} πήρε τον κόμβο {n}, όχι τον {64 + free}"
        log.append(n - 64)
        spots.append(at)
        centre = U.tile(at)
    top = codeat.top(G.m)[0]
    D.demolish(G, F, spots[-1])
    if D.rec(G, 64 + log[-1])[4]:
        return f"ΑΝΕΒΑΣΜΑ: η κατεδάφιση της θέσης {log[-1]} δεν την άδειασε"
    if codeat.top(G.m)[0] != top:
        return f"ΑΝΕΒΑΣΜΑ: η κατεδάφιση της {log[-1]} έκανε το όριο {codeat.top(G.m)[0]}, όχι {top}"
    at, _ = U.find_spot(G, sym, U.SOLAR, lambda r, a: True, U.tile(spots[-2]), rmax=30)
    F.set_stocks(TF.STOCK, TF.STOCK)
    n = U.place(G, sym, g, U.SOLAR, at)
    if n != 64 + log[-1] or codeat.top(G.m)[0] != top:
        return (f"ΑΝΕΒΑΣΜΑ: μετά την κατεδάφιση το ηλιακό πήρε τον κόμβο {n} (η άδεια ήταν "
                f"{64 + log[-1]}) και το όριο {codeat.top(G.m)[0]} ({top} πριν)")
    if not quiet:
        print(f"    ΑΝΕΒΑΣΜΑ: θέσεις {log}, όριο {top}· η κατεδάφιση της {log[-1]} το άφησε, "
              f"και το ηλιακό μετά ξαναπήρε τη θέση", flush=True)
    return None


# --------------------------------------------------------------------------
# ΠΕΡΑΣΜΑΤΑ, ΚΟΣΤΟΣ
# --------------------------------------------------------------------------
CX, CY = 40, 40                           # το κέντρο της δομής 20, σε μισά tiles


def limit(X, top):
    """Το όριο με το st_set του παιχνιδιού (όχι με το codeat): έτσι και ένα
    st_set πειραγμένο — το rt_n της δρομολόγησης — φαίνεται."""
    assert X.call("ST_SET", [0x3E, top], bank=0xC0) is not None


def struct(X, kind, state, owed=0, at=(CX, CY)):
    """Η δομή K: μέγεθος 2 (τα ενεργειακά δεν έχουν σχέδιο στα 0 και 1)."""
    X.put6(GS + 8 * K, [at[0] & 255, at[1] & 255, kind, 2, state,
                        255 if state == EC.DS_ACTIVE else 0, 0, owed])


def ef_lp(X, top, seen):
    struct(X, EC.K_SOLAR, EC.DS_ACTIVE)
    g = X.g
    X.m.poke(g + EC_DAY, 1)
    X.m.poke(g + EC_STORM, 0)
    X.m.poke(X.sym["EC_FDIV"], 1)
    limit(X, top)
    t = X.call("ECON_FLOW")
    p = X.m.peek(g + EC_PPROD) | X.m.peek(g + EC_PPROD + 1) << 8
    return t, p == EC.SOLAR_OUT[2], f"EC_PPROD {p}"


def rr_pad(X, top, seen):
    struct(X, EC.K_PAD if seen else EC.K_SOLAR, EC.DS_ACTIVE)
    limit(X, top)
    t = X.call("ROOMS_REBUILD")
    p = X.m.peek(X.g + EC_PADNODE)
    return t, p == 64 + K, f"EC_PADNODE {p}"


def sort(X, top, seen):
    struct(X, EC.K_SOLAR, EC.DS_ACTIVE)
    limit(X, top)
    t = X.call("OB_STRUCT_SORT")
    n = X.m.peek(X.sym["ST_N"])
    order = list(X.m.read_ram(X.sym["ST_ORD"], n))
    return t, K in order, f"st_ord {order}"


def sweep(X, top, seen):
    struct(X, EC.K_SOLAR, EC.DS_BUILDING, owed=0x11)    # χρωστά μέταλλο και βιοπλαστικό
    X.m.write_ram(L["G_job_tbl"], bytes([255] * EC.MAX_JOB * EC.JOB_REC))
    limit(X, top)
    t = X.call("SP_SWEEP")
    jobs = bytes(X.m.read_ram(L["G_job_tbl"], EC.MAX_JOB * EC.JOB_REC))
    mine = [j for j in range(EC.MAX_JOB) if jobs[5 * j] != 255 and jobs[5 * j + 1] == 64 + K]
    return t, len(mine) >= 2, f"εργασίες του {64 + K}: {len(mine)}"


def mprice(X, top, seen):
    struct(X, EC.K_MINE if seen else EC.K_SOLAR, EC.DS_ACTIVE)   # χωρίς ορυχείο: όλο το πέρασμα
    X.m.poke(X.sym["BD_KIND"], 1)                       # BK_STRUCT
    X.m.poke(X.sym["BD_PARAM"], EC.K_MINE)
    X.m.poke(X.sym["BD_METAL"], 77)
    limit(X, top)
    t = X.call("BD_MPRICE", bank=0xC0)
    p = X.m.peek(X.sym["BD_METAL"])
    return t, p != 0, f"bd_metal {p}"


def scans(X, top, seen):
    struct(X, EC.K_SOLAR, EC.DS_ACTIVE)
    far = 0 if seen else 100                            # ο κέρσορας μακριά: όλο το πέρασμα
    X.m.poke(X.sym["CUR_HX"], (CX + far) & 255)
    X.m.poke(X.sym["CUR_HY"], CY & 255)
    X.m.write_ram(CB, bytes([0x32] + w(CB + 8) + [0xC9]) + bytes(4) + b"\xFF")
    limit(X, top)
    t = X.call("AL_SCANS", [0x21] + w(CB))
    got = X.m.peek(CB + 8)
    return t, got == 64 + K, f"το al_scans κάλεσε για {got}"


def impact(X, top, seen):
    struct(X, EC.K_SOLAR, EC.DS_ACTIVE)
    e = EC.Econ()
    e.mrnd = 0x5A17
    byte = EC._mbyte(copy.copy(e))
    tx = (CX >> 1) + (0 if seen else 30)                # στο έδαφος, μακριά
    ty = CY >> 1
    g = X.g
    X.m.poke(g + EC_METEOR, 1)
    X.m.poke(g + EC_MCX, (tx - (byte & 15) + 8) & 255)
    X.m.poke(g + EC_MCY, (ty - (byte >> 4) + 8) & 255)
    X.m.poke(g + EC_MRND, e.mrnd & 255)
    X.m.poke(g + EC_MRND + 1, e.mrnd >> 8)
    limit(X, top)
    if seen:                               # η σκηνή όπως την ξέρει η αναφορά
        f = EC.Econ()
        f.struct = bytearray(X.table())
        f.dome = bytearray(X.get6(L["G_dome_tbl"], ND * EC.DOME_REC))
        assert TI.hit_node(f, tx, ty) == 64 + K, (tx, ty, TI.hit_node(f, tx, ty))
    t = X.call("MT_TICK")
    s = X.get6(GS + 8 * K + 4, 1)[0]
    return t, s == EC.DS_BUILDING, f"η δομή {K} σε κατάσταση {s}"


def routing(X, top, seen):
    struct(X, EC.K_SOLAR, EC.DS_ACTIVE)
    nodes, adj = L["G_rt_nodes"], L["G_node_adj"]
    X.m.poke(nodes + 64, 1)
    X.m.poke(nodes + 64 + K, 1)
    X.m.poke(adj + 8 * 64, 64 + K)
    X.m.poke(adj + 8 * (64 + K), 64)
    row = (64 + K) * 128
    X.put(5, row + 64, b"\xEE")
    limit(X, top)
    b, s = X.sym["RT_BEGIN"], X.sym["RT_SLICE"]
    t = X.probe([0xCD] + w(b) + [0x06, 0xFF, 0xCD] + w(s) + [0x30, 0xF9], step=10)
    got = X.bank(5)[row + 64]
    return t, got == 64, f"NEXTHOP[{64 + K}][64] = {got}"


def shower(X, top, seen):
    """Η αρχή της βροχής από το mts_seed: το κέντρο της είναι το πρώτο ζωντανό
    κτίριο από τον κόμβο 65 και πάνω, με τον κύκλο ως το 127 και πάλι από το 0.
    Αν η 20 δεν φαίνεται, το σκάφος (0, 0) — αφού πρώτα περάσουν όλοι οι άλλοι."""
    struct(X, EC.K_SOLAR, EC.DS_ACTIVE if seen else EC.DS_EMPTY)
    seed = next(v for v in range(1, 65536)
                if EC._mbyte(type("E", (), {"mrnd": v})()) & 127 == 65)
    X.m.poke(X.g + EC_METEOR, 0)
    limit(X, top)
    t = X.call("MTS_SEED", [0x21] + w(seed))
    c = X.m.peek(X.g + EC_MCX)
    return t, c == CX >> 1, f"το κέντρο της βροχής στο x = {c}"


PASSES = (("ροή", ef_lp), ("πίστα", rr_pad), ("ευρετήριο", sort), ("σάρωμα", sweep),
          ("τιμή", mprice), ("κέρσορας", scans), ("κρούση", impact), ("βροχή", shower),
          ("δρόμοι", routing))


def passes(X, cost=None):
    """ΠΕΡΑΣΜΑΤΑ και ΚΟΣΤΟΣ. (κόστη, None) ή (…, η πρώτη διαφορά)."""
    times = {}
    for name, fn in PASSES:
        X.restore()
        t, ok, what = fn(X, HIGH, True)
        if t is None or not ok:
            return times, f"ΠΕΡΑΣΜΑΤΑ: {name}, με όριο {HIGH} η δομή {K} δεν φάνηκε ({what})"
        X.restore()
        t, ok, what = fn(X, LOW, True)
        if t is None or ok:
            return times, f"ΠΕΡΑΣΜΑΤΑ: {name}, με όριο {LOW} η δομή {K} φάνηκε ({what})"
        X.restore()
        t, ok, what = fn(X, HIGH, False)
        if t is None:
            return times, f"ΚΟΣΤΟΣ: {name} δεν γύρισε"
        times[name] = t
        if cost is not None and t > cost[name]:
            return times, f"ΚΟΣΤΟΣ: {name} {t} µs με όριο {HIGH}, ταβάνι {cost[name]}"
    return times, None


# --------------------------------------------------------------------------
def neg_patches(sym):
    """Τα πειράγματα των αρνητικών: (όνομα, ποιο μέρος, πειράγματα ή None)."""
    X = Box(sym)
    m, top, end = X.m, codeat.TOP_AT + 2, codeat.TOP_AT

    def find(label, pat, span=200):
        return codeat.find(m, sym[label], pat, span)

    def b6(at, v):
        return ("hole", (6, at - 0x4000), v) if codeat.in_b6(at) else ("ram", at, v)

    def b1(at, v):                         # το OV_R1, στην τράπεζα 1
        return ("hole", (1, at - 0x4000), v)

    def ld48(at, v=NS):                    # ld a,(nn) -> ld a,v / nop
        return at and [b6(at, 0x3E), b6(at + 1, v), b6(at + 2, 0)]

    ss = sym["ST_SET"]
    raw = bytes(m.read_ram(ss, 24))       # το OV_R1 είναι στην τράπεζα 1, στο παράθυρο
    k = raw.find(bytes([0x0F]))                                    # rrca
    rn = raw.find(bytes([0x32] + w(sym["RT_N"])))                  # ld (rt_n),a
    sc = find("ST_COUNT", [0x06, NS], 12)
    sr = sym["ST_RECOUNT"]
    ef = find("ECON_FLOW", [0x3A] + w(top) + [0x47], 120)
    rr = find("ROOMS_REBUILD", [0x3A] + w(top) + [0x47], 200)
    so = find("OB_STRUCT_SORT", [0xED, 0x4B] + w(codeat.TOP_AT + 3), 12)
    sw = find("SP_SWEEP", [0x3A] + w(end), 12)
    mp = find("BD_MPRICE", [0x3A] + w(top) + [0x47], 40)
    al = find("AL_SCANS", [0xED, 0x4B] + w(end), 20)
    mt = find("MT_IMPACT", [0x3A] + w(top) + [0x57, 0x1E, 8], 200)
    me = mt and codeat.find(m, mt + 3, [0x3A] + w(end), 20)
    ms = find("MTS_SEED", [0x3A] + w(end) + [0x32] + w(sym["MTS_END"] + 1), 40)
    return [
        ("το st_set χωρίς το μισό", "ΜΟΡΦΕΣ", k >= 0 and [b1(ss + k, 0)]),
        ("το st_count από τη θέση 31", "ΜΕΤΡΗΜΑ", sc and [b6(sc + 1, 32)]),
        ("το wheel_reset χωρίς το st_recount", "ΑΡΧΗ", [("ram", sr, 0xC9)]),
        ("το st_raise που δεν ανεβάζει", "ΑΝΕΒΑΣΜΑ", [b1(sym["ST_RAISE"], 0xC9)]),
        ("το ef_lp με 48", "ΠΕΡΑΣΜΑΤΑ", ld48(ef)),
        ("το rr_pad με 48", "ΠΕΡΑΣΜΑΤΑ", ld48(rr)),
        ("το ob_struct_sort με 48", "ΠΕΡΑΣΜΑΤΑ",
         so and [b6(so, 0x01), b6(so + 1, 0), b6(so + 2, NS - 16), b6(so + 3, 0)]),
        ("το sp_sweep με 48", "ΠΕΡΑΣΜΑΤΑ", ld48(sw, ND + NS)),
        ("το bd_mprice με 48", "ΠΕΡΑΣΜΑΤΑ", ld48(mp)),
        ("το al_scans με 48", "ΠΕΡΑΣΜΑΤΑ",
         al and [b6(al, 0x01), b6(al + 1, ND + NS), b6(al + 2, NS // 2), b6(al + 3, 0)]),
        ("η κρούση με 48", "ΠΕΡΑΣΜΑΤΑ", mt and me and ld48(mt) + ld48(me, ND + NS)),
        ("η αρχή της βροχής ως τον 111", "ΠΕΡΑΣΜΑΤΑ", ld48(ms, ND + NS)),
        ("η δρομολόγηση με 112 πηγές", "ΠΕΡΑΣΜΑΤΑ", rn >= 0 and
         [b1(ss + rn + i, 0) for i in range(3)] + [("ram", sym["RT_N"], ND + NS)]),
    ]


def run_part(part, sym, g, patch=(), quiet=False, cost=None):
    """Ενα μέρος της πρόζας: None, ή το πρώτο λάθος."""
    if part == "ΜΟΡΦΕΣ":
        return setter(Box(sym, patch))
    if part == "ΜΕΤΡΗΜΑ":
        return counter(Box(sym, patch))[1]
    if part == "ΑΡΧΗ":
        return start(sym, patch)
    if part == "ΑΝΕΒΑΣΜΑ":
        return raising(sym, g, patch, quiet)
    return passes(Box(sym, patch), cost)[1]


def main():
    sym, g = TG.build()
    X = Box(sym)
    why = setter(X)
    check(why is None, why or f"ΜΟΡΦΕΣ: το st_set = codeat.top_bytes για t = 2, 4, …, {NS}")
    n, why = counter(X)
    check(why is None, why or f"ΜΕΤΡΗΜΑ: το st_recount = το top_of του πίνακα σε {n} πίνακες")
    why = start(sym)
    check(why is None, why or "ΑΡΧΗ: η εικόνα με τις 48, το main.sna με 2, το colony.sna με "
                              "τον πίνακά του, και το φόρτωμα τις ξαναβρίσκει")
    why = raising(sym, g)
    check(why is None, why or "ΑΝΕΒΑΣΜΑ: το όριο ακολουθεί τις τοποθετήσεις, και η κατεδάφιση "
                              "δεν το κατεβάζει")
    times, why = passes(X)
    print("    ΚΟΣΤΟΣ: " + ", ".join(f"{k} {v} µs" for k, v in times.items()), flush=True)
    check(why is None, why or f"ΠΕΡΑΣΜΑΤΑ: τα {len(PASSES)} βλέπουν τη δομή {K} με όριο {HIGH}, "
                              f"όχι με {LOW}")
    for k, v in times.items():
        check(v <= CEIL[k], f"ΚΟΣΤΟΣ: {k} {v} µs με όριο {HIGH} <= {CEIL[k]}")
    for label, part, patch in neg_patches(sym):
        if not patch:
            check(False, f"ΑΡΝΗΤΙΚΟ «{label}»: το μοτίβο δεν βρέθηκε")
            continue
        why = run_part(part, sym, g, patch, quiet=True, cost=CEIL)
        check(why is not None, f"ΑΡΝΗΤΙΚΟ «{label}»: " + (why or "περνά"))
    if FAIL:
        print(f"\nΑΠΟΤΥΧΙΑ — {len(FAIL)}")
        return 1
    print("\nOK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
