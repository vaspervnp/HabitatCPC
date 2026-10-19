#!/usr/bin/env python3
"""Σαράντα οκτώ δομές σε ένα παιχνίδι (βήμα 156, DESIGN §6.1).

Ως το βήμα 155 οι δομές ήταν 32· η μνήμη για 48 ετοιμάστηκε στα 151-155 και
το βήμα 156 τις άνοιξε (MAX_STRUCT 48). Τα test_twopage, test_dblock,
test_place, test_oibuild, test_impact ρωτούν ένα-ένα τα κομμάτια με γραμμένους
πίνακες· εδώ η αποικία δοκιμών (colony.sna) γεμίζει από τον παίκτη, και το
παιχνίδι τρέχει μόνο του. Η πρόζα:

  ΘΕΣΕΙΣ     ηλιακά, ένα-ένα από τον κατάλογο με το FIRE (tools/balance.py,
             όπως ο παίκτης), το καθένα δίπλα στο προηγούμενο, ως να γεμίσει
             ο πίνακας: κάθε ένα παίρνει την πρώτη άδεια θέση, και ο κόμβος
             του είναι 64 + θέση — ως τον 111.
  ΓΕΜΑΤΟΣ    ένα 49ο, σε θέση που ο κανόνας (tools/reach.py) δέχεται: το FIRE
             δεν βάζει τίποτα, ούτε μια εγγραφή ούτε ένα μέταλλο αλλάζουν.
  ΧΤΙΣΙΜΟ    η αποικία τα χτίζει όλα, ως BUILD_FRAMES: φορτία ως τον κόμβο
             111 και ο χτίστης εκεί, με τις διαδρομές του DIST και του NEXTHOP.
  ΔΡΟΜΟΙ     όταν ησυχάσει η δρομολόγηση (rt_dirty 0), το DIST και το NEXTHOP
             του Z80, σε κάθε θέση που γράφει μια ανοικοδόμηση και για τις 112
             πηγές, = η BFS του tools/graph.py πάνω στον γράφο του ίδιου του
             παιχνιδιού (node_adj, node_deg).
  ΟΘΟΝΗ      με την κάμερα πάνω στις τελευταίες: το st_ord έχει και τις 48,
             κατά cy, η οθόνη = πλήρης σχεδίαση, και η δομή της θέσης 47
             ζωγραφίζεται — χωρίς αυτήν η πλήρης σχεδίαση βγαίνει άλλη.
  ΡΕΥΜΑ      ένας κύκλος ροής μέρα χωρίς σκόνη (econ_flow, με probe): το
             EC_PPROD = το άθροισμα του tools/econ.py για τα έτοιμα ηλιακά και
             τις ανεμογεννήτριες όλου του πίνακα.

Αρνητικά, με τον κώδικα πειραγμένο όπως ήταν ως το βήμα 155, μία θέση τη
φορά: το bd_commit που ψάχνει 32 θέσεις (οι ΘΕΣΕΙΣ σταματούν στην 33η), η
δρομολόγηση με 96 πηγές (rt_n: οι ΔΡΟΜΟΙ), το ob_struct_sort με 32 (η ΟΘΟΝΗ),
το ef_lp του κύκλου ροής με 32 (το ΡΕΥΜΑ).
"""
import contextlib, io, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import test_demolish as D                                # noqa: E402
import test_unlink as U                                  # noqa: E402
import test_fit as TF                                    # noqa: E402
import balance as B                                      # noqa: E402
import econ as EC                                        # noqa: E402
import graph as GR                                       # noqa: E402
import codeat                                            # noqa: E402

FAIL = []
NS = EC.MAX_STRUCT
BUILD_FRAMES = 40_000            # μετρήθηκαν 14.000 μετά το γέμισμα
PROBE = 0x3E80
EC_PPROD, EC_DAY, EC_WIND, EC_STORM = 32, 49, 50, 61
K_SOLAR, K_TURBINE, DS_ACTIVE = 0, 1, 2


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


def table(G):
    """Ο πίνακας των δομών, όπως είναι στην τράπεζα 6."""
    st = layout()["G_struct_tbl"] - 0x4000
    b6 = G.bank(6)
    return bytes(b6[st + k] for k in range(NS * EC.STRUCT_REC))


def quiet_build(G, sym, g, item, at):
    """Το B.build χωρίς το «ΠΡΟΣΟΧΗ» του όταν δεν μπαίνει: το ΓΕΜΑΤΟΣ το θέλει."""
    with contextlib.redirect_stdout(io.StringIO()):
        return B.build(G.m, sym, item, g + 6, at=at, fit=False)


# --------------------------------------------------------------------------
# ΘΕΣΕΙΣ, ΓΕΜΑΤΟΣ
# --------------------------------------------------------------------------
def fill(G, F, sym, g):
    """Ηλιακά από τον παίκτη ως να γεμίσει ο πίνακας. -> (κόμβοι, θέσεις, λάθος)."""
    free = [s for s in range(NS) if not D.rec(G, 64 + s)[4]]
    nodes, spots = [], []
    centre = U.tile(D.centre(G, 65))
    for k, s in enumerate(free):
        at, _ = U.find_spot(G, sym, U.SOLAR, lambda r, a: True, centre, rmax=30)
        if not at:
            return nodes, spots, f"ΘΕΣΕΙΣ: καμία θέση για το ηλιακό {k + 1} γύρω από το {centre}"
        F.set_stocks(TF.STOCK, TF.STOCK)
        n = U.place(G, sym, g, U.SOLAR, at)
        if n != 64 + s:
            return nodes, spots, (f"ΘΕΣΕΙΣ: το ηλιακό {k + 1} στο {at} πήρε τον κόμβο {n}, "
                                  f"η πρόζα λέει {64 + s} (η πρώτη άδεια θέση, {s})")
        nodes.append(n)
        spots.append(at)
        centre = U.tile(at)
    return nodes, spots, None


def full_table(G, F, sym, g, spots):
    """ΓΕΜΑΤΟΣ. None, ή τι άλλαξε."""
    centre = U.tile(spots[-1])
    at, _ = U.find_spot(G, sym, U.SOLAR, lambda r, a: True, centre, rmax=30)
    if not at:
        return f"ΓΕΜΑΤΟΣ: καμία θέση για 49ο ηλιακό γύρω από το {centre}"
    F.set_stocks(TF.STOCK, TF.STOCK)
    # ΜΕ ΤΗΝ ΠΡΟΣΟΜΟΙΩΣΗ ΣΤΑΜΑΤΗΜΕΝΗ: η αποικία χτίζει ακόμη, και η ακεραιότητα
    # και η κατάσταση των εργοταξίων αλλάζουν μόνες τους. Η διεπαφή τρέχει.
    on = G.still()
    t0, s0 = table(G), F.stocks()
    placed = quiet_build(G, sym, g, U.SOLAR, at)
    G.m.run_frames(20)
    t1, s1 = table(G), F.stocks()
    G.go(on)
    if placed:
        return f"ΓΕΜΑΤΟΣ: ένα 49ο ηλιακό μπήκε στο {at}"
    if t1 != t0:
        k = next(i for i in range(len(t0)) if t1[i] != t0[i])
        return f"ΓΕΜΑΤΟΣ: η εγγραφή {k // 8} άλλαξε (byte {k % 8}) με το 49ο"
    if s1 != s0:
        return f"ΓΕΜΑΤΟΣ: τα αποθέματα {s0} -> {s1} με το 49ο"
    return None


# --------------------------------------------------------------------------
# ΧΤΙΣΙΜΟ, ΔΡΟΜΟΙ
# --------------------------------------------------------------------------
def built(G):
    t = 0
    while t < BUILD_FRAMES:
        if all(D.rec(G, 64 + s)[4] == DS_ACTIVE for s in range(NS)):
            return t, None
        G.m.run_frames(1000)
        t += 1000
    left = [64 + s for s in range(NS) if D.rec(G, 64 + s)[4] != DS_ACTIVE]
    return t, f"ΧΤΙΣΙΜΟ: σε {BUILD_FRAMES} frames δεν χτίστηκαν οι {left}"


def routes(G, sym):
    """ΔΡΟΜΟΙ. None, ή η πρώτη διαφορά."""
    for _ in range(400):
        if not G.m.peek(sym["RT_DIRTY"]):
            break
        G.m.run_frames(25)
    else:
        return "ΔΡΟΜΟΙ: η δρομολόγηση δεν ησύχασε σε 10.000 frames"
    L = layout()
    gr = GR.Graph(GR.RT_NODES)
    gr.adj[:] = bytes(G.m.read_ram(L["G_node_adj"], GR.ADJ_SIZE))
    gr.deg[:] = bytes(G.m.read_ram(L["G_rt_nodes"], GR.MAXNODE))
    wd, wn = GR.all_pairs(gr)
    b1, b5 = G.bank(1), G.bank(5)
    dc, nc = GR.z80_cells(GR.RT_NODES)
    for name, cells, img, want in (("DIST", dc, b1, wd), ("NEXTHOP", nc, b5, wn)):
        for o, a, b in cells:
            if img[o] != want[a * GR.MAXNODE + b]:
                return (f"ΔΡΟΜΟΙ: {name}[{a}][{b}] = {img[o]}, η BFS του graph.py λέει "
                        f"{want[a * GR.MAXNODE + b]}")
    return None


# --------------------------------------------------------------------------
# ΟΘΟΝΗ
# --------------------------------------------------------------------------
def screen(G, sym, spots, shot=None):
    """ΟΘΟΝΗ. None, ή τι λείπει."""
    tx, ty = U.tile(spots[-1])
    G.camera(tx - 9, ty - 4)
    G.settle()
    n = G.m.peek(sym["ST_N"])
    order = list(G.m.read_ram(sym["ST_ORD"], n))
    t = table(G)
    live = [s for s in range(NS) if t[8 * s + 4]]
    cy = lambda s: t[8 * s + 1] - 256 if t[8 * s + 1] > 127 else t[8 * s + 1]
    if order != sorted(live, key=lambda s: (cy(s), s)):
        return (f"ΟΘΟΝΗ: st_ord {n} δομές {order[:6]}…, η πρόζα λέει {len(live)} κατά cy "
                f"{sorted(live, key=lambda s: (cy(s), s))[:6]}…")
    pic, ref = G.truth()
    ok, what = D.R.shape(pic, ref)
    if not ok:
        return f"ΟΘΟΝΗ: η εικόνα διαφέρει από την πλήρη σχεδίαση, {what}"
    # Η 47 ΖΩΓΡΑΦΙΖΕΤΑΙ: η πλήρης σχεδίαση με την εγγραφή της άδεια βγαίνει άλλη
    st = layout()["G_struct_tbl"] - 0x4000 + 8 * (NS - 1) + 4
    on = G.still()
    G.full()
    with_it = G.play()
    G.bank(6)[st] = 0
    G.full()
    without = G.play()
    G.bank(6)[st] = DS_ACTIVE
    G.full()
    G.go(on)
    if with_it == without:
        return "ΟΘΟΝΗ: η δομή 47 δεν φαίνεται — η σχεδίαση είναι ίδια χωρίς αυτήν"
    if shot:                        # μετά από γύρους του βρόχου: οι λωρίδες στη θέση τους
        G.settle()
        G.m.run_frames(3)
        G.m.screenshot(shot, aspect=True)
    return None


# --------------------------------------------------------------------------
# ΡΕΥΜΑ
# --------------------------------------------------------------------------
def power(G, sym, g):
    """ΡΕΥΜΑ. (το EC_PPROD, None) ή (τιμή, λάθος). Τελευταίο: αφήνει τον Z80 στο probe."""
    m = G.m
    m.poke(g + EC_DAY, 1)
    m.poke(g + EC_STORM, 0)
    m.poke(sym["EC_FDIV"], 1)
    t, wind = table(G), m.peek(g + EC_WIND)
    want = 0
    for s in range(NS):
        if t[8 * s + 4] != DS_ACTIVE:
            continue
        k, sz = t[8 * s + 2], t[8 * s + 3]
        if k == K_SOLAR:
            want += EC.SOLAR_OUT[sz]
        elif k == K_TURBINE:
            want += EC.TURBINE_OUT[sz] * wind // 3
    f = sym["ECON_FLOW"]
    code = [0xF3, 0x31, 0x00, 0x01, 0x01, 0xC6, 0x7F, 0xED, 0x49,
            0xCD, f & 255, f >> 8, 0x18, 0xFE]
    m.write_ram(PROBE, bytes(code))
    m.set_pc(PROBE)
    end = PROBE + len(code) - 2
    for _ in range(2000):
        if end <= m.pc <= end + 2:
            break
        m.run_us(100)
    else:
        return None, f"ΡΕΥΜΑ: το econ_flow δεν γύρισε (#{m.pc:04X})"
    got = m.peek(g + EC_PPROD) | m.peek(g + EC_PPROD + 1) << 8
    if got != want:
        return got, f"ΡΕΥΜΑ: EC_PPROD {got}, η αναφορά λέει {want}"
    return got, None


# --------------------------------------------------------------------------
def scenario(sym, g, patch=(), quiet=False):
    """Ολο το σενάριο. None, ή το πρώτο λάθος."""
    say = (lambda s: None) if quiet else (lambda s: print("    " + s, flush=True))
    G, F = D.game(sym, g, patch)
    G.run(500_000)
    G.settle()
    before = [64 + s for s in range(NS) if D.rec(G, 64 + s)[4]]
    nodes, spots, why = fill(G, F, sym, g)
    if why:
        return why
    say(f"ΘΕΣΕΙΣ: η αποικία είχε τους {before}· {len(nodes)} ηλιακά, κόμβοι "
        f"{nodes[0]}-{nodes[-1]} με τη σειρά, το τελευταίο στο {spots[-1]}")
    why = full_table(G, F, sym, g, spots)
    if why:
        return why
    say("ΓΕΜΑΤΟΣ: το 49ο δεν μπήκε, ο πίνακας και τα αποθέματα ίδια")
    t, why = built(G)
    if why:
        return why
    say(f"ΧΤΙΣΙΜΟ: και οι {NS} έτοιμες σε {t} frames μετά το γέμισμα")
    why = routes(G, sym)
    if why:
        return why
    say(f"ΔΡΟΜΟΙ: DIST και NEXTHOP = η BFS για τις {GR.RT_NODES} πηγές")
    why = screen(G, sym, spots, None if quiet else os.path.join(ROOT, "build", "fortyeight.png"))
    if why:
        return why
    say(f"ΟΘΟΝΗ: st_ord {NS} κατά cy, η εικόνα = πλήρης σχεδίαση, η 47 φαίνεται "
        "(build/fortyeight.png)")
    got, why = power(G, sym, g)
    if why:
        return why
    say(f"ΡΕΥΜΑ: EC_PPROD {got} = το άθροισμα της αναφοράς για όλο τον πίνακα")
    return None


def negatives(sym):
    m = B.boot(sym, TG.COLONY)

    def find(label, pat, span=400):
        raw = bytes(m.read_ram(sym[label], span))
        i = raw.find(bytes(pat))
        return None if i < 0 else sym[label] + i

    st = layout()["G_struct_tbl"]
    bc = find("BD_COMMIT", [0x01, EC.MAX_DOME + NS, NS >> 2], 120)
    so = find("OB_STRUCT_SORT", [0x01, 0x00, NS - 16], 12)
    # το econ_flow ζει στο b6code (τράπεζα 6): codeat, και το πείραγμα στην 6
    ef = codeat.find(m, sym["ECON_FLOW"], [0xDD, 0x21, st & 255, st >> 8, 0x06, NS], 120)
    return [("το bd_commit που ψάχνει 32 θέσεις",
             bc and [("ram", bc + 1, EC.MAX_DOME + 32), ("ram", bc + 2, 8)]),
            ("η δρομολόγηση με 96 πηγές (rt_n)", [("ram", sym["RT_N"], 96)]),
            ("το ob_struct_sort με 32", so and [("ram", so + 2, 16)]),
            ("το ef_lp με 32", ef and [("hole", (6, ef + 5 - 0x4000), 32)])]


def main():
    sym, g = TG.build()
    why = scenario(sym, g)
    check(why is None, why or f"{NS} δομές: θέσεις, γεμάτος πίνακας, χτίσιμο, δρόμοι, "
                              "οθόνη και ρεύμα όπως λέει η πρόζα")
    for label, patch in negatives(sym):
        if not patch:
            check(False, f"ΑΡΝΗΤΙΚΟ «{label}»: το μοτίβο δεν βρέθηκε")
            continue
        why = scenario(sym, g, patch, quiet=True)
        check(why is not None, f"ΑΡΝΗΤΙΚΟ «{label}»: " + (why or "περνά"))
    if FAIL:
        print(f"\nΑΠΟΤΥΧΙΑ — {len(FAIL)}")
        return 1
    print("\nOK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
