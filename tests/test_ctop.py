#!/usr/bin/env python3
"""Το όριο σάρωσης των διαδρόμων (βήμα 159, CT_TOP, src/const.asm, DESIGN §4.2).

Από το βήμα 159 ο πίνακας των διαδρόμων έχει 128 εγγραφές (96 ως το 158), και
όσα περάσματα τον διατρέχουν σταματούν στο CT_TOP: η ψηλότερη εγγραφή που δεν
είναι CT_EMPTY + 1 (και η συνέχεια μιας στροφής, CT_CONT), τουλάχιστον 1, ένα
byte στη θέση 117 του node_deg. Το ανεβάζει το cr_commit (tests/test_corridor.py
το ελέγχει σε 400 τοποθετήσεις), και η πρόζα εδώ:

  ΜΕΤΡΗΜΑ    σε 60 πίνακες (άδειος, μόνο η 0, μόνο η 127, μια στροφή που
             τελειώνει στην 127, η 95 και η 96 στο όριο του βήματος 158, και
             τυχαίοι με κενά, με την άδεια εγγραφή 128 πότε άδεια και πότε όχι),
             το ct_recount δίνει το codeat.ctop_of του πίνακα.
  ΑΡΧΗ       η εικόνα έχει 128 (ό,τι τρέχει χωρίς να έχει περάσει από το
             wheel_reset διατρέχει όλο τον πίνακα)· μετά το game_new το main.sna
             έχει 1 (κανένας διάδρομος) και το colony.sna 3 (οι τρεις του)· με το
             όριο μηδέν, όπως πριν από ένα φόρτωμα, το wheel_load το ξαναβρίσκει.
  ΠΕΡΑΣΜΑΤΑ  οι τρεις διάδρομοι της αποικίας δοκιμών μετακινημένοι στις θέσεις
             120-122, και κάθε πέρασμα τους βλέπει με όριο 123 και όχι με 120:
             το χτίσιμο του ευρετηρίου (oi_build: τρεις εγγραφές με id 120-122),
             το lk_done (lkd_corr: η ακμή 0-2 που έλειπε ξαναγίνεται), η
             κατοχή της κατεδάφισης (dm_world: ένα ορθογώνιο πάνω στον διάδρομο
             0-1 σβήνει και ξαναγράφεται ίδιο) και η ίδια η κατεδάφιση του θόλου
             2 από τον παίκτη (dmk_lp: ο διάδρομός του φεύγει, και όλα όσα
             ελέγχει το tests/test_demolish.py μετά από μια κατεδάφιση).
  ΚΟΣΤΟΣ     το ευρετήριο των διαδρόμων και το lkd_corr στην αποικία δοκιμών,
             με το όριο της (3), κάτω από ταβάνια λίγο πάνω από αυτό που
             μετρήθηκε: με 128 θέσεις ήταν 125 άδειες ακόμη.

Αρνητικά, με τον κώδικα πειραγμένο, ένα τη φορά: το ct_recount από την
εγγραφή 95 (το ΜΕΤΡΗΜΑ), το wheel_reset χωρίς το ct_recount (η ΑΡΧΗ), και κάθε
πέρασμα με τις 128 θέσεις αντί για το όριο — βλέπει τους διαδρόμους και με
όριο 120 (ΠΕΡΑΣΜΑΤΑ), και το κόστος περνά το ταβάνι (ΚΟΣΤΟΣ).
"""
import os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import test_sttop as T                                   # noqa: E402
import test_demolish as D                                # noqa: E402
import test_fit as TF                                    # noqa: E402
import codeat                                            # noqa: E402
import ovmap as OV                                       # noqa: E402

FAIL = []
L = T.L
GC = L["G_corr_tbl"]
MC, CR, CT_EMPTY, CT_CONT = codeat.MAX_CORR, codeat.CORR_REC, codeat.CT_EMPTY, 255
OB_IX_CORR, OI_REC, MAX_DOME = 4, 5, 64
HI = 120                                  # οι τρεις της αποικίας: 120-122
SEE, MISS = HI + 3, HI
# ΤΑΒΑΝΙΑ, στην αποικία δοκιμών με το όριο της (3): μετρημένα 4.213 και 467 µs
# στο βήμα 159. Με 128 θέσεις, 125 άδειες ακόμη, ~117 µs η καθεμία στο ευρετήριο
# και ~26 στο lkd_corr.
CEIL = {"ευρετήριο": 4300, "lkd_corr": 500}


def check(ok, msg):
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ ") + msg, flush=True)
    if not ok:
        FAIL.append(msg)


def w(a):
    return [a & 255, a >> 8]


def table(X):
    """Οι 129 εγγραφές (και η άδεια μετά από αυτές), από την τράπεζα 5."""
    return bytes(X.bank(5)[GC - 0x4000:GC - 0x4000 + (MC + 1) * CR])


def shift(X, top):
    """Οι τρεις διάδρομοι της αποικίας (0-1, 0-2, 0-65) στις θέσεις 120-122, οι
    0-2 άδειες, και το όριο top."""
    t = bytearray(table(X))
    t[HI * CR:(HI + 3) * CR] = t[0:3 * CR]
    t[0:3 * CR] = bytes([CT_EMPTY]) * (3 * CR)
    X.put(5, GC - 0x4000, t)
    codeat.set_ctop(X.m, top)


# --------------------------------------------------------------------------
# ΜΕΤΡΗΜΑ
# --------------------------------------------------------------------------
def counter(X):
    """ΜΕΤΡΗΜΑ. (πόσοι πίνακες, None) ή (…, η πρώτη διαφορά)."""
    rnd = random.Random(159)
    cases = [set(), {0}, {127}, {126, 127}, {95}, {96}, set(range(MC))]
    while len(cases) < 60:
        cases.append({k for k in range(MC) if rnd.random() < rnd.choice([0.05, 0.3, 0.8])})
    for n, used in enumerate(cases):
        X.restore()
        t = bytearray()
        for k in range(MC):
            if k in used:
                a = CT_CONT if k - 1 in used and rnd.random() < 0.3 else rnd.randrange(112)
                t += bytes([a, rnd.randrange(112), rnd.randrange(8), rnd.randrange(1, 20)])
            else:
                t += bytes([CT_EMPTY, rnd.randrange(256), rnd.randrange(256), rnd.randrange(256)])
        # η εγγραφή 128, πάντα άδεια στο παιχνίδι: εδώ και σκουπίδια
        t += bytes([CT_EMPTY if n % 2 else rnd.randrange(112), 0, 0, 0])
        X.put(5, GC - 0x4000, t)
        codeat.set_ctop(X.m, rnd.choice([1, 77, MC]))
        if X.call("CT_RECOUNT") is None:
            return n, f"ΜΕΤΡΗΜΑ: το ct_recount δεν γύρισε (πίνακας {n})"
        want, got = codeat.ctop_of(t), codeat.ctop(X.m)
        if got != want:
            return n, (f"ΜΕΤΡΗΜΑ: πίνακας {n} με {len(used)} εγγραφές (ψηλότερη "
                       f"{max(used) if used else '-'}): CT_TOP {got}, ο πίνακας λέει {want}")
    return len(cases), None


# --------------------------------------------------------------------------
# ΑΡΧΗ
# --------------------------------------------------------------------------
def start(sym, patch=()):
    """ΑΡΧΗ. None, ή η πρώτη διαφορά."""
    img = open(TG.SNA, "rb").read()
    if img[0x100 + codeat.CT_AT] != MC:
        return f"ΑΡΧΗ: η εικόνα έχει CT_TOP {img[0x100 + codeat.CT_AT]}, η πρόζα λέει {MC}"
    for sna, n in ((TG.SNA, 1), (TG.COLONY, 3)):
        X = T.Box(sym, patch, sna)
        want = codeat.ctop_of(table(X))
        if want != n:
            return f"ΑΡΧΗ: ο πίνακας του {os.path.basename(sna)} λέει {want}, όχι {n}"
        if codeat.ctop(X.m) != want:
            return (f"ΑΡΧΗ: το {os.path.basename(sna)} μετά το game_new έχει CT_TOP "
                    f"{codeat.ctop(X.m)}, ο πίνακάς του λέει {want}")
        X.m.poke(codeat.CT_AT, 0)
        if X.call("WHEEL_LOAD", bank=0xC0) is None:
            return "ΑΡΧΗ: το wheel_load δεν γύρισε"
        if codeat.ctop(X.m) != want:
            return (f"ΑΡΧΗ: το φόρτωμα στο {os.path.basename(sna)} με το όριο μηδέν άφησε "
                    f"{codeat.ctop(X.m)}, όχι {want}")
    return None


# --------------------------------------------------------------------------
# ΠΕΡΑΣΜΑΤΑ και ΚΟΣΤΟΣ
# --------------------------------------------------------------------------
def index(X, top, moved=True):
    """oi_build των διαδρόμων: (µs, τους βλέπει;, τι είδε)."""
    if moved:
        shift(X, top)
    else:
        codeat.set_ctop(X.m, top)
    t = X.call("OI_BUILD", pre=[0x3E, OB_IX_CORR >> 1])
    n = X.m.peek(X.sym["OI_NC"])
    b5 = X.bank(5)
    oi = L["G_obj_index"] - 0x4000 + MAX_DOME * OI_REC
    ids = sorted(b5[oi + OI_REC * k + 4] for k in range(n))
    want = list(range(HI, HI + 3)) if moved else [0, 1, 2]
    return t, ids == want, f"{n} εγγραφές, id {ids}"


def adj(X, v):
    deg = X.m.peek(L["G_rt_nodes"] + v)
    return list(X.m.read_ram(L["G_node_adj"] + 8 * v, deg))


def cut(X, a, b):
    """Η ακμή a-b βγαίνει από τις λίστες και των δύο."""
    for x, y in ((a, b), (b, a)):
        rest = [v for v in adj(X, x) if v != y]
        X.m.write_ram(L["G_node_adj"] + 8 * x, bytes(rest + [0] * (8 - len(rest))))
        X.m.poke(L["G_rt_nodes"] + x, len(rest))


def lkd(X, top, moved=True):
    """lkd_corr για τον θόλο 2 χωρίς την ακμή του προς τον 0: (µs, την ξανάφτιαξε;)."""
    if moved:
        shift(X, top)
    else:
        codeat.set_ctop(X.m, top)
    cut(X, 0, 2)
    X.m.poke(X.sym["LK_N"], 2)
    t = X.call("LKD_CORR")
    return t, 0 in adj(X, 2) and 2 in adj(X, 0), f"γείτονες του 2: {adj(X, 2)}"


def world(X, top):
    """dm_world σε ένα ορθογώνιο πάνω στον διάδρομο 0-1 (τώρα 120): (µs, η
    κατοχή ίδια;). Η επικάλυψη της κατεδάφισης στο GH_BUF, όπως την φέρνει το
    dm_run."""
    shift(X, top)
    X.m.write_ram(OV.GH, OV.read(X.m, X.sym, "dm"))  # από τις τρύπες: και τα πειράγματα
    x0, y0, wd, ht = 1, -2, 6, 4                    # tiles: ανάμεσα στους θόλους 0 και 1
    r = X.sym["DMV_R"]
    X.m.write_ram(r, bytes([x0 & 255, y0 & 255, wd, ht]))
    X.m.write_ram(X.sym["DMV_P"], bytes(w(r + 4)))

    def occ():
        b4 = X.bank(4)
        return [b4[(y + 64) * 128 + x + 64] & 0x10 for y in range(y0, y0 + ht)
                for x in range(x0, x0 + wd)]
    before = occ()
    t = X.call("DM_WORLD")
    after = occ()
    return t, after == before and any(before), f"{sum(1 for v in before if v)} -> " \
                                                f"{sum(1 for v in after if v)} tiles με κατοχή"


def demolition(sym, g, top, patch=()):
    """Ο θόλος 2 κατεδαφίζεται από τον παίκτη, με τους διαδρόμους στις 120-122:
    (έφυγε ο διάδρομός του από τη θέση 121;, None ή ό,τι λέει το test_demolish
    ότι λείπει)."""
    G, F = D.game(sym, g, patch)
    t = bytearray(G.bank(5)[GC - 0x4000:GC - 0x4000 + (MC + 1) * CR])
    t[HI * CR:(HI + 3) * CR] = t[0:3 * CR]
    t[0:3 * CR] = bytes([CT_EMPTY]) * (3 * CR)
    for k, v in enumerate(t):
        G.bank(5)[GC - 0x4000 + k] = v
    codeat.set_ctop(G.m, top)
    G.m.poke(sym["OB_IDX"], G.m.peek(sym["OB_IDX"]) | OB_IX_CORR)   # το ευρετήριο με τα νέα id
    G.run(1_000_000)
    G.settle()
    D.demolish(G, F, D.centre(G, 2))
    gone = G.bank(5)[GC - 0x4000 + (HI + 1) * CR] == CT_EMPTY    # ο 0-2, στη θέση 121
    return gone, D.common(G, F, 2, [0])


PASSES = [("ευρετήριο", index), ("lkd_corr", lkd), ("dm_world", world)]


def passes(sym, g, patch=(), cost=None):
    """ΠΕΡΑΣΜΑΤΑ και ΚΟΣΤΟΣ: (κόστη, None) ή (…, η πρώτη διαφορά)."""
    times = {}
    X = T.Box(sym, patch, TG.COLONY)
    for name, fn in PASSES:
        X.restore()
        t, ok, what = fn(X, SEE)
        if t is None or not ok:
            return times, f"ΠΕΡΑΣΜΑΤΑ: {name}, με όριο {SEE} οι διάδρομοι 120-122 δεν φάνηκαν ({what})"
        X.restore()
        t, ok, what = fn(X, MISS)
        if t is None or ok:
            return times, f"ΠΕΡΑΣΜΑΤΑ: {name}, με όριο {MISS} οι διάδρομοι 120-122 φάνηκαν ({what})"
        if name in CEIL:
            X.restore()
            t, ok, what = fn(X, 3, moved=False)          # η αποικία όπως είναι, όριο 3
            if t is None or not ok:
                return times, f"ΚΟΣΤΟΣ: {name} στην αποικία ({what})"
            times[name] = t
            if cost is not None and t > cost[name]:
                return times, f"ΚΟΣΤΟΣ: {name} {t} µs με όριο 3, ταβάνι {cost[name]}"
    gone, why = demolition(sym, g, SEE, patch)
    if why or not gone:
        return times, f"ΠΕΡΑΣΜΑΤΑ: η κατεδάφιση του θόλου 2 με όριο {SEE}: {why or 'ο 121 έμεινε'}"
    # ΜΕ ΟΡΙΟ 120 ο διάδρομος 121 μένει (dmk_lp)· το ότι και το test_demolish
    # βρίσκει τότε τον κόσμο λάθος είναι του dm_world, που έχει δικό του έλεγχο
    gone, _ = demolition(sym, g, MISS, patch)
    if gone:
        return times, f"ΠΕΡΑΣΜΑΤΑ: η κατεδάφιση του θόλου 2 με όριο {MISS} πήρε τον διάδρομο 121"
    return times, None


# --------------------------------------------------------------------------
def neg_patches(sym):
    """Τα πειράγματα των αρνητικών: (όνομα, ποιο μέρος, πειράγματα ή None)."""
    X = T.Box(sym)
    m, ct = X.m, codeat.CT_AT

    def find(label, pat, span=200):
        return codeat.find(m, sym[label], pat, span)

    def all128(at):                        # ld a,(CT_TOP) / ld b,a -> ld b,128 / nop / nop
        return at and [("ram", at, 0x06), ("ram", at + 1, MC), ("ram", at + 2, 0), ("ram", at + 3, 0)]

    cr = sym["CT_RECOUNT"]
    hl = find("CT_RECOUNT", [0x21] + w(GC + (MC - 1) * CR), 8)
    bb = find("CT_RECOUNT", [0x06, MC], 12)
    oi = find("OI_BUILD", [0x3A] + w(ct) + [0x47], 80)
    lk = find("LKD_CORR", [0x3A] + w(ct) + [0x47], 12)
    sr = sym["ST_RECOUNT"]
    # ΤΑ ΔΥΟ ΤΗΣ ΚΑΤΕΔΑΦΙΣΗΣ ζουν στις τρύπες της 5 (OV_R3): το ovmap λέει πού
    # είναι κάθε byte της, από τη διεύθυνση όπου τρέχει στο GH_BUF
    dm = OV.read(m, sym, "dm")
    pat = bytes([0x3A] + w(ct) + [0x47])
    k1 = dm.find(pat)
    k2 = dm.find(pat, k1 + 1) if k1 >= 0 else -1

    def hole128(k):
        if k < 0:
            return None
        out = []
        for i, v in enumerate((0x06, MC, 0, 0)):
            b, a = OV.at(sym, "dm", OV.GH + k + i)
            out.append(("hole", (b, a - 0x4000), v))
        return out
    return [
        ("το ct_recount από την εγγραφή 95", "ΜΕΤΡΗΜΑ",
         hl and bb and [("ram", hl + 1, (GC + 95 * CR) & 255), ("ram", hl + 2, (GC + 95 * CR) >> 8),
                        ("ram", bb + 1, 96)]),
        ("το wheel_reset χωρίς το ct_recount", "ΑΡΧΗ",
         [("ram", cr, 0xC3), ("ram", cr + 1, sr & 255), ("ram", cr + 2, sr >> 8)]),
        ("το ευρετήριο με 128", "ΠΕΡΑΣΜΑΤΑ", all128(oi)),
        ("το lkd_corr με 128", "ΠΕΡΑΣΜΑΤΑ", all128(lk)),
        ("η κατεδάφιση (dmk_lp) με 128", "ΠΕΡΑΣΜΑΤΑ", hole128(k1)),
        ("η κατοχή της κατεδάφισης (dm_world) με 128", "ΠΕΡΑΣΜΑΤΑ", hole128(k2)),
    ]


def run_part(part, sym, g, patch=()):
    if part == "ΜΕΤΡΗΜΑ":
        return counter(T.Box(sym, patch))[1]
    if part == "ΑΡΧΗ":
        return start(sym, patch)
    return passes(sym, g, patch, cost=CEIL)[1]


def main():
    sym, g = TG.build()
    X = T.Box(sym)
    n, why = counter(X)
    check(why is None, why or f"ΜΕΤΡΗΜΑ: το ct_recount = το ctop_of του πίνακα σε {n} πίνακες")
    why = start(sym)
    check(why is None, why or "ΑΡΧΗ: η εικόνα με 128, το main.sna με 1, το colony.sna με 3, και "
                              "το φόρτωμα το ξαναβρίσκει")
    times, why = passes(sym, g)
    print("    ΚΟΣΤΟΣ: " + ", ".join(f"{k} {v} µs" for k, v in times.items()), flush=True)
    check(why is None, why or f"ΠΕΡΑΣΜΑΤΑ: το ευρετήριο, το lkd_corr, το dm_world και η "
                              f"κατεδάφιση βλέπουν τους 120-122 με όριο {SEE}, όχι με {MISS}")
    for k, v in times.items():
        check(v <= CEIL[k], f"ΚΟΣΤΟΣ: {k} {v} µs με όριο 3 <= {CEIL[k]}")
    for label, part, patch in neg_patches(sym):
        if not patch:
            check(False, f"ΑΡΝΗΤΙΚΟ «{label}»: το μοτίβο δεν βρέθηκε")
            continue
        why = run_part(part, sym, g, patch)
        check(why is not None, f"ΑΡΝΗΤΙΚΟ «{label}»: " + (why or "περνά"))
    if FAIL:
        print(f"\nΑΠΟΤΥΧΙΑ — {len(FAIL)}")
        return 1
    print("\nOK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
