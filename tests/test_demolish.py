#!/usr/bin/env python3
"""Η κατεδάφιση (βήμα 101, DESIGN §9.3).

Η πρόζα — οι αποφάσεις του παίκτη:

  ΤΙ        θόλοι και δομές, τελειωμένα ή εργοτάξια· ποτέ το σκάφος. Οι διάδρομοι
            ενός θόλου φεύγουν μαζί του. Ούτε η πίστα ή μια αποθήκη όσο έρχεται
            ή κάθεται πλοίο.
  ΠΙΣΩ      τα μισά υλικά, όπως μια μηχανή που βγαίνει στο FIT: του κτιρίου,
            των διαδρόμων του (6 μέταλλο, 3 βιοπλαστικό το πλακίδιο) και των
            μηχανών του. Ενα εργοτάξιο δίνει πίσω όλα όσα πληρώθηκαν.
  ΠΩΣ       M, D (ή το DEMOLISH στη ΔΙΑΧΕΙΡΙΣΗ), και το FIRE γκρεμίζει· αμέσως.
            Κόκκινο το κουμπί εκεί που δεν γίνεται, και το FIRE δεν κάνει τίποτα.
  ΑΝΘΡΩΠΟΙ  όσοι στέκονται εκεί πάνε στο κοντινότερο airlock ή στο σκάφος, με
            γεμάτη στολή, χωρίς δουλειά και όχι πια χειριστές· μέσα, αν το
            airlock είναι έτοιμο. Οι εργασίες του κόμβου σβήνουν.

Και ό,τι μένει πίσω πρέπει να είναι σαν να μην υπήρξε ποτέ: η εγγραφή άδεια,
καμία ακμή προς αυτόν σε καμία λίστα, κανένας διάδρομός του (ούτε η δεύτερη
εγγραφή μιας στροφής), τα δωμάτια χωρίς αυτόν ΑΜΕΣΩΣ, και ο κόσμος (το bit 4
της κατοχής) ΑΚΡΙΒΩΣ ό,τι βγάζει ένα μοντέλο σε Python από τις εγγραφές που
μένουν (tools/reach.py και tools/route.py: αποτυπώματα, πλακίδια διαδρόμων και
μισού πλάτους). Η οθόνη ίδια με πλήρη σχεδίαση, και πάλι ίδια όταν ο κέρσορας
φύγει από εκεί που ήταν.

ΤΟ ΚΟΣΤΟΣ: η εικόνα ξαναζωγραφίζεται ορθογώνιο ορθογώνιο από τη λίστα αλλαγών
(DK_RSIZE + DK_RECT), ένα ανά πέρασμα — ο χειρότερος γύρος από το FIRE ως να
αδειάσει η λίστα ως CEIL_US, σε ένα εργοστάσιο και στον θόλο 0 της αποικίας
που τον βλέπουν τρεις θόλοι.

Ο ΚΩΔΙΚΑΣ ΤΗΣ ΚΑΤΕΔΑΦΙΣΗΣ ΖΕΙ ΣΤΙΣ ΤΡΥΠΕΣ ΤΟΥ DIST (στήλες 96-127, src/demolish.asm)
και τρέχει από το GH_BUF· οι δύο χειριστές της λίστας τρέχουν από την τρύπα
της γραμμής 0. Ελέγχεται ότι οι τρύπες έχουν ό,τι λέει το build
(build/ovl.bin), και τα αρνητικά του πειράζουν τα bytes ΕΚΕΙ: το ov_run τον
ξαναφέρνει από εκεί κάθε φορά.

Αρνητικά, με τον κώδικα πειραγμένο στη μνήμη: καμία επιστροφή· όλα πίσω και από
χτισμένο· οι διάδρομοι μένουν· ο κόσμος δεν ξαναγράφεται· ο διάδρομος χωρίς το
tile γύρω του· μόνο το αποτύπωμα, όχι οι διάδρομοι· τα δωμάτια μένουν ως τον
τροχό· οι εργασίες μένουν· οι άνθρωποι μένουν· οι ακμές μένουν· ο κόμβος πίσω
στη λίστα του γείτονα· το airlock μένει ενωμένο· το σκάφος γκρεμίζεται· κανένα
ορθογώνιο στη λίστα· το ορθογώνιο χωρίς να σηκωθεί το φάντασμα· όλα τα
ορθογώνια σε ένα πέρασμα· το δωρεάν ορυχείο δίνει 30.

ΤΑ ΟΡΥΧΕΙΑ (βήμα 123): το πρώτο της αποικίας μπαίνει δωρεάν (ST_FREE) και,
γκρεμισμένο, δεν δίνει τίποτα πίσω· ένα δεύτερο πληρώνει 30 και τα παίρνει
πίσω όλα από εργοτάξιο.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import test_reveal as R                                  # noqa: E402
import test_fit as TF                                    # noqa: E402
import test_outside as TO                                # noqa: E402
import balance as B                                      # noqa: E402
import route                                             # noqa: E402
import reach                                             # noqa: E402

FAIL = []
DOME = {0: (12, 8), 1: (24, 14), 2: (40, 24)}            # bld_items: μέταλλο, βιοπλαστικό
AIRLOCK = (10, 6)
CORR = (6, 3)                                            # ανά πλακίδιο
K_MINE, K_AIRLOCK, K_PAD, K_SHIP = 4, 5, 6, 7
R_FACTORY = 8                                           # src/const.asm (R_*, G_room_n)
F_ALIVE, F_INDOORS, F_WORKING = 1, 2, 32
NO_TASK, SUIT_TRIP = 255, 70
AF_DEMO = 2
DK_RSIZE, DK_RECT = 9, 10                                # src/const.asm (βήμα 101)
MS = 1000
CEIL_US = 150_000         # ο χειρότερος γύρος από το FIRE ως να αδειάσει η λίστα:
                          # 92 ms το εργοστάσιο, 125 ο θόλος 0 της αποικίας
WORST = {}


def check(ok, msg):
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ ") + msg)
    if not ok:
        FAIL.append(msg)


L = TO.layout()
_OV = os.path.join(ROOT, "build", "ovl.bin")
OVL = open(_OV, "rb").read() if os.path.exists(_OV) else b""
GH = L["PAGE2_TOP"]
sb = reach.sb


# --------------------------------------------------------------------------
# ανάγνωση
# --------------------------------------------------------------------------
def b6(G):
    return G.bank(6)


def dome(G, d):
    t = L["G_dome_tbl"] - 0x4000 + 24 * d
    return list(b6(G)[t:t + 24])


def struct(G, n):
    t = L["G_struct_tbl"] - 0x4000 + 8 * (n - 64)
    return list(b6(G)[t:t + 8])


def rec(G, n):
    return dome(G, n) if n < 64 else struct(G, n)


def corridors(G):
    """[a, b, dir, len, κατάσταση] ανά θέση, όπως ως το βήμα 153: από το 154 οι
    εγγραφές είναι 4 bytes στην τράπεζα 5, και η κατάσταση βγαίνει από το C_A
    (254 άδεια, 2 κάθε άλλη — και η συνέχεια μιας στροφής, C_A 255)."""
    t = L["G_corr_tbl"] - 0x4000
    b5 = G.bank(5)
    return [list(b5[t + 4 * k:t + 4 * k + 4]) + [0 if b5[t + 4 * k] == 254 else 2]
            for k in range(96)]


def jobs(G):
    """(εργασία, J_KIND, J_NODE, J_AGENT, J_PRIO, J_SITE) όσων υπάρχουν."""
    return [(j, *G.m.read_ram(L["G_job_tbl"] + 5 * j, 5)) for j in range(32)
            if G.m.peek(L["G_job_tbl"] + 5 * j) != 255]


def deg(G, n):
    return G.m.peek(L["G_rt_nodes"] + n)


def adj(G, n):
    return [G.m.peek(L["G_node_adj"] + 8 * n + k) for k in range(deg(G, n))]


AG = L["G_agent_fields"] - 0x4000


def ag(G, a, field, hi=False):
    return b6(G)[AG + 256 * field + (128 if hi else 0) + a]


def standing(G, n):
    """Οι ζωντανοί που στέκονται στον κόμβο n (όχι στον δρόμο)."""
    return [a for a in range(128) if ag(G, a, 0) & F_ALIVE and ag(G, a, 1) == n
            and ag(G, a, 2, True) == 255]


def econ(G, k):
    return G.m.peek(L["G_econ_state"] + k)


def rooms(G):
    n = [G.m.peek(L["G_room_n"] + r) for r in range(12)]
    return n, [[G.m.peek(L["G_room_list"] + 8 * r + k) for k in range(n[r])]
               for r in range(12)]


def holes(G):
    b1 = G.bank(1)
    return bytes(b1[128 * (k >> 5) + 96 + (k & 31)] for k in range(len(OVL)))


def centre(G, n):
    r = rec(G, n)
    return sb(r[0]), sb(r[1])


# --------------------------------------------------------------------------
# ο κόσμος από τις εγγραφές (tools/reach.py, tools/route.py)
# --------------------------------------------------------------------------
def model(G, base=None):
    """Η τράπεζα 4 όπως πρέπει να είναι: ό,τι είναι (ή το base, βήμα 102), με
    το bit 4 από την αρχή, από όσα μένουν — τα αποτυπώματα (reach.footprint),
    τα πλακίδια κάθε διαδρόμου όπως τα βγάζει η διαδρομή του tools/route.py από
    τα δύο άκρα του (reach.corridor_tiles), και τα tiles του μισού πλάτους όπου
    δεν έχει μονοπάτι (reach.half_tiles). Το bit 4 είναι ένωση: η σειρά δεν
    μετρά."""
    if base is None:
        base = bytes(G.bank(4)[:0x4000])
    wl = bytearray(b & 0xEF for b in base)
    on = lambda x, y: -64 <= x < 64 and -64 <= y < 64
    domes = [[r[0], r[1], r[2], r[4]] for r in (dome(G, d) for d in range(64))]
    structs = [struct(G, n) for n in range(64, 96)]
    dims = G.m.read_ram(L["G_struct_dims"], 64)
    for n in range(96):
        fp = reach.footprint(n, domes, structs, dims)
        if fp is None:
            continue
        x0, y0, w, h = fp[0]
        for y in range(y0, y0 + h):
            for x in range(x0, x0 + w):
                if on(x, y):
                    wl[reach.widx(x, y)] |= 0x10
    for c in corridors(G):
        if not c[4] or c[0] == 255:
            continue
        a = (sb(domes[c[0]][0]), sb(domes[c[0]][1]), domes[c[0]][2])
        if c[1] < 64:
            z = (sb(domes[c[1]][0]), sb(domes[c[1]][1]), domes[c[1]][2])
        else:
            z = (sb(structs[c[1] - 64][0]), sb(structs[c[1] - 64][1]), route.AIRLOCK)
        side, runs = route.plan(*a, *z)
        f, t = (a, z) if side == 0 else (z, a)
        for x, y in reach.corridor_tiles(f[:2], f[2], t[:2], runs):
            if on(x, y):
                wl[reach.widx(x, y)] |= 0x10
        for x, y in reach.half_tiles(f, t, runs):
            if on(x, y) and not wl[reach.widx(x, y)] & 0x20:
                wl[reach.widx(x, y)] |= 0x10
    return bytes(wl)


def world_ok(G):
    got, want = bytes(G.bank(4)[:0x4000]), model(G)
    bad = [k for k in range(0x4000) if got[k] != want[k]]
    if not bad:
        return True, ""
    k = bad[0]
    return False, (f"{len(bad)} tiles, πρώτο ({k % 128 - 64}, {k // 128 - 64}) "
                   f"#{got[k]:02X} αντί #{want[k]:02X}")


# --------------------------------------------------------------------------
# ο παίκτης
# --------------------------------------------------------------------------
def game(sym, g, patch=(), sna=None):
    """Το παιχνίδι στην αποικία δοκιμών (ή στο sna), με τα πειράγματα: ("ram",
    διεύθυνση, τιμή) ή ("hole", δείκτης στην τράπεζα 1, τιμή)."""
    old = R.T.COLONY
    R.T.COLONY = sna or old
    try:
        G = R.Game(sym, g)
    finally:
        R.T.COLONY = old
    for where, at, v in patch:
        if where == "ram":
            G.m.poke(at, v)
        else:
            G.bank(1)[at] = v
    F = TF.Fit(G, sym, g)
    F.set_stocks(TF.STOCK, TF.STOCK)
    return G, F


def demolish(G, F, at, fire=True):
    """LOOK, κέρσορας στο at (μισά tiles), M, D, FIRE. -> (ac_fit μετά το M,
    ac_sel μετά το D, αποθέματα πριν από το FIRE, μετά, ο χειρότερος γύρος σε
    µs από το FIRE ως τρεις γύρους μετά)."""
    F.look()
    G.m.poke(F.sym["CUR_HX"], at[0] & 0xFF)
    G.m.poke(F.sym["CUR_HY"], at[1] & 0xFF)
    F.key("M")
    fit = F.peek("AC_FIT")
    F.key("D")
    sel = F.peek("AC_SEL")
    s0 = F.stocks()
    G.iters = []
    if fire:
        F.fire()
    s1 = F.stocks()
    G.run(3_000_000, until=lambda: G.m.peek(F.sym["DIRTY_NUM"]) == 0)
    G.settle()
    return fit, sel, s0, s1, max(G.iters, default=0)


def truth(G):
    pic, ref = G.truth()
    return R.shape(pic, ref)


def common(G, F, n, nbrs):
    """Ο,τι λέει η πρόζα για κάθε κατεδάφιση: None, ή το πρώτο που λείπει."""
    if rec(G, n)[4]:
        return f"η εγγραφή του {n} δεν άδειασε (κατάσταση {rec(G, n)[4]})"
    if b6(G)[L["G_node_occ"] - 0x4000 + n]:
        return f"θέσεις του {n} πιασμένες ακόμη"
    if deg(G, n):
        return f"ο {n} έχει ακόμη {deg(G, n)} ακμές: {adj(G, n)}"
    for v in nbrs:
        if n in adj(G, v):
            return f"ο γείτονας {v} έχει ακόμη τον {n}"
        if deg(G, v) < 8 and G.m.peek(L["G_node_adj"] + 8 * v + deg(G, v)) == n:
            return f"η θέση μετά την τελευταία του γείτονα {v} δείχνει ακόμη τον {n}"
    if any(c[4] and n in c[:2] for c in corridors(G)):
        return f"ένας διάδρομος του {n} έμεινε"
    mine = [j for j in jobs(G) if n in (j[2], j[5]) and j[1] != 9]
    if mine:
        return f"εργασίες του {n}: {mine}"
    if standing(G, n):
        return f"στέκονται ακόμη στον {n}: {standing(G, n)}"
    if any(n in lst for lst in rooms(G)[1]):
        return f"ο {n} είναι ακόμη σε λίστα δωματίων {rooms(G)[1]}"
    ok, why = world_ok(G)
    if not ok:
        return "ο κόσμος δεν είναι ό,τι λένε οι εγγραφές: " + why
    # ΜΙΑ ΠΕΡΙΣΤΡΟΦΗ ΤΟΥ ΤΡΟΧΟΥ ΠΡΙΝ ΑΠΟ ΤΗΝ ΟΘΟΝΗ (βήμα 113). Οποιος περπατά
    # προς τον κόμβο τη στιγμή του FIRE δεν τον αγγίζει το dm_do. Τον βρίσκει η
    # δική του υποδοχή κίνησης, το πολύ 16 γύρους αργότερα: ο προορισμός δεν
    # φτάνεται πια, και μένει στον κόμβο του (§6.3). Ως τότε η οθόνη τον δείχνει
    # εκεί που ήταν, και η πλήρης σχεδίαση δεν μπορεί να τον βάλει πουθενά,
    # γιατί η ακμή του δεν υπάρχει πια. Στο ΕΡΓΟΤΑΞΙΟ είναι ο 1, στο 192/255 της
    # ακμής από το airlock 65, και καταλήγει μέσα σε αυτό. Ως το βήμα 112 η
    # σύγκριση έπεφτε σε φάση όπου ένα ορθογώνιο είχε μόλις σβήσει τη φιγούρα
    # του, με τους πράκτορες ίδιους byte προς byte. Το 113 έφερε την εκκίνηση
    # 0,2 ms αργότερα (μία γραμμή ακόμη στο ov_install), και η φιγούρα ήταν
    # ζωγραφισμένη: 13 bytes. Ο,τι μένει στην οθόνη μετά από μια περιστροφή δεν
    # το διορθώνει κανείς.
    n0 = len(G.iters)
    G.run(5_000_000, until=lambda: len(G.iters) >= n0 + 16)
    G.run(3_000_000, until=lambda: G.m.peek(F.sym["DIRTY_NUM"]) == 0)
    same = truth(G)
    if not same[0]:
        return "οθόνη/πλήρης σχεδίαση: " + same[1]
    # Ο ΚΕΡΣΟΡΑΣ ΦΕΥΓΕΙ: το πλαίσιό του καθόταν πάνω στον θόλο, και η αναίρεσή
    # του γράφει πίσω ό,τι κρατά το αρχείο του. Αν ένα ορθογώνιο ζωγραφίστηκε
    # χωρίς να σηκωθεί, ο θόλος ξαναφαίνεται εκεί που ήταν το πλαίσιο.
    for _ in range(3):
        F.key(TF.KEY_RIGHT)
    same = truth(G)
    if not same[0]:
        return "με τον κέρσορα αλλού, οθόνη/πλήρης σχεδίαση: " + same[1]
    return None


# --------------------------------------------------------------------------
# ΣΚΗΝΕΣ
# --------------------------------------------------------------------------
def tables(sym, g):
    G, F = game(sym, g)
    if holes(G) != OVL:
        return "ΠΙΝΑΚΕΣ: οι τρύπες του DIST δεν έχουν τον κώδικα του build/ovl.bin"
    ok, why = world_ok(G)
    if not ok:
        return "ΠΙΝΑΚΕΣ: ο κόσμος της αποικίας δεν είναι το μοντέλο: " + why
    before = bytes(G.bank(4)[:0x4000])
    G.m.write_ram(GH, OVL)
    r = sym["DMV_R"]                                       # ένα ορθογώνιο: όλος ο κόσμος
    G.m.write_ram(r, bytes([0xC0, 0xC0, 128, 128]))
    G.m.write_ram(sym["DMV_P"], bytes([(r + 4) & 255, (r + 4) >> 8]))
    G.probe(["DM_WORLD"], frames=400)
    after = bytes(G.bank(4)[:0x4000])
    if after != before:
        k = next(k for k in range(0x4000) if after[k] != before[k])
        return (f"ΠΙΝΑΚΕΣ: το dm_world σε όλο τον κόσμο άλλαξε το ({k % 128 - 64}, "
                f"{k // 128 - 64}): #{before[k]:02X} -> #{after[k]:02X}")
    print(f"    ΠΙΝΑΚΕΣ: {len(OVL)} bytes κώδικα στις τρύπες, όπως στο build· ο κόσμος της "
          f"αποικίας = το μοντέλο, και ξαναγραμμένος ολόκληρος μένει ίδιος")
    return None


def at_once(sym, g, patch=(), quiet=False):
    """ΑΜΕΣΩΣ: το dm_do μόνο του, από την κορυφή του βρόχου, χωρίς να τρέξει ο
    τροχός μετά. Τα δωμάτια ξαναμετριούνται και στη θέση 14 του τροχού, μία
    φορά ανά περιστροφή· η κατεδάφιση δεν τα αφήνει παλιά ως τότε — κανείς δεν
    πρέπει να διαλέξει για κυλικείο ή οξυγόνο έναν θόλο που δεν υπάρχει."""
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G, F = game(sym, g, patch)
    G.run(500_000)
    G.settle()
    n = 0
    room = dome(G, n)[3]
    before = rooms(G)[0][room]
    G.m.poke(sym["DM_N"], n)
    G.probe(["UI_HIDE", "OV_RUN"], frames=100)
    after = rooms(G)[0][room]
    if after != before - 1 or any(n in lst for lst in rooms(G)[1]):
        return f"ΑΜΕΣΩΣ: δωμάτια του είδους {room}: {before} -> {after}, λίστες {rooms(G)[1]}"
    say(f"ΑΜΕΣΩΣ: ο θόλος {n} βγήκε από τα δωμάτια του είδους {room} μέσα στο ίδιο το "
        f"dm_do ({before} -> {after})")
    return None


def factory(sym, g, patch=(), quiet=False):
    """Ενα μεσαίο εργοστάσιο, δύο μηχανές στημένες, και ο διάδρομός του.
    Επιστρέφει τον χειρότερο γύρο (µs), ή το πρώτο που λείπει."""
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G, F = game(sym, g, patch)
    tx, ty = B.clear_spots(8, 1, dome=True)[0]
    G.camera(tx - 6, ty - 1)
    at = (2 * tx + 8, 2 * ty + 8)
    B.build(G.m, sym, TF.I_DOME_M, g + 6, at=at, room=TF.RM_FACTORY, fit=False)
    n = G.m.peek(sym["BD_NODE"])
    R.finish(G, n)
    G.settle()
    if not F.enter(at):
        return "ΕΡΓΟΣΤΑΣΙΟ: το FIT δεν άνοιξε"
    for s, i in enumerate([1, 4]):
        F.put(s, i)
    F.look()
    G.run(60_000_000, until=lambda: dome(G, n)[16:18] == [200, 200])
    G.settle()
    r = dome(G, n)
    if r[16:18] != [200, 200]:
        return f"ΕΡΓΟΣΤΑΣΙΟ: οι μηχανές δεν στήθηκαν: {r[8:12]}, {r[16:20]}"
    mach = [m for m in r[8:12] if m != 255]
    tiles = sum(c[3] for c in corridors(G) if c[4] and n in c[:2])
    nbrs = adj(G, n)
    price = (DOME[1][0] + CORR[0] * tiles + sum(TF.COST[m][0] for m in mach),
             DOME[1][1] + CORR[1] * tiles + sum(TF.COST[m][1] for m in mach))
    rn0 = rooms(G)[0][R_FACTORY]
    fit, sel, s0, s1, worst = demolish(G, F, at)
    got = (s1[0] - s0[0], s1[1] - s0[1])
    want = (price[0] // 2, price[1] // 2)
    if not fit & AF_DEMO:
        return f"ΕΡΓΟΣΤΑΣΙΟ: το DEMOLISH κόκκινο (ac_fit {fit}, ac_sel {sel})"
    if got != want:
        return (f"ΕΡΓΟΣΤΑΣΙΟ: πίσω {got}, η πρόζα λέει τα μισά του {price} = {want} "
                f"(θόλος M, {tiles} πλακίδια διαδρόμου, οι μηχανές {mach})")
    if rooms(G)[0][R_FACTORY] != rn0 - 1:
        return f"ΕΡΓΟΣΤΑΣΙΟ: εργοστάσια {rn0} -> {rooms(G)[0][R_FACTORY]}"
    why = common(G, F, n, nbrs)
    if why:
        return "ΕΡΓΟΣΤΑΣΙΟ: " + why
    say(f"ΕΡΓΟΣΤΑΣΙΟ: ο θόλος {n}, οι μηχανές {mach} και ο διάδρομός του ({tiles} "
        f"πλακίδια) έφυγαν, πίσω {got} = τα μισά του {price}· ο κόσμος = το μοντέλο, η "
        f"οθόνη = πλήρης σχεδίαση· ο χειρότερος γύρος {worst / MS:.1f} ms")
    if not quiet:
        WORST["ένα εργοστάσιο M"] = worst
        G.m.screenshot(os.path.join(ROOT, "build", "demolish_factory.png"), aspect=True)
    elif worst > CEIL_US:
        return f"ΕΡΓΟΣΤΑΣΙΟ: ο χειρότερος γύρος {worst / MS:.1f} ms > {CEIL_US / MS:.0f}"
    return None


def bend(sym, g, patch=(), quiet=False):
    """Ενας θόλος M δίπλα στην αποικία, όπου τον βάζει ο κανόνας της (το πρώτο
    σημείο από την αποικία προς τα έξω, balance.live_spot): ο διάδρομός του
    από τον θόλο 0 είναι διαγώνιος με στροφή, δύο εγγραφές. Και οι δύο
    φεύγουν, πληρώνονται όλα τα πλακίδια, και ο κόσμος και η οθόνη είναι σαν
    να μην υπήρξε."""
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G, F = game(sym, g, patch)
    G.run(500_000)
    G.settle()
    at = B.live_spot(G.m, sym, TF.I_DOME_M, (0, 24))
    G.camera((at[0] >> 1) - 10, (at[1] >> 1) - 7)
    B.build(G.m, sym, TF.I_DOME_M, g + 6, at=at, room=TF.RM_FACTORY, fit=False)
    n = G.m.peek(sym["BD_NODE"])
    R.finish(G, n)
    G.settle()
    cs = corridors(G)
    mine = [k for k, c in enumerate(cs) if c[4] and n in c[:2]]
    runs = [cs[k][2:4] for k in mine] + [cs[k + 1][2:4] for k in mine if cs[k + 1][0] == 255]
    if rec(G, n)[4] != 2 or not any(d & 1 for d, _ in runs) or len(runs) < 2:
        return f"ΣΤΡΟΦΗ: η σκηνή θέλει θόλο με διαγώνιο διάδρομο και στροφή: {rec(G, n)[:5]}, {runs}"
    tiles = sum(n_ for _, n_ in runs)
    nbrs = adj(G, n)
    price = (DOME[1][0] + CORR[0] * tiles, DOME[1][1] + CORR[1] * tiles)
    _, _, s0, s1, _ = demolish(G, F, at)
    got = (s1[0] - s0[0], s1[1] - s0[1])
    if got != (price[0] // 2, price[1] // 2):
        return f"ΣΤΡΟΦΗ: πίσω {got}, η πρόζα λέει τα μισά του {price} ({runs})"
    if any(c[4] for k, c in enumerate(corridors(G)) if k in mine or k - 1 in mine):
        return "ΣΤΡΟΦΗ: μία από τις δύο εγγραφές του διαδρόμου έμεινε"
    why = common(G, F, n, nbrs)
    if why:
        return "ΣΤΡΟΦΗ: " + why
    say(f"ΣΤΡΟΦΗ: ο θόλος {n} στο {at}, με τον διάδρομο {runs} από τον θόλο 0: πίσω "
        f"{got}, και οι δύο εγγραφές έφυγαν")
    return None


def site(sym, g, patch=(), quiet=False):
    """Ενα εργοτάξιο θόλου: όλα πίσω, και οι εργασίες του σβήνουν."""
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G, F = game(sym, g, patch)
    tx, ty = B.clear_spots(8, 1, dome=True)[0]
    G.camera(tx - 6, ty - 1)
    at = (2 * tx + 8, 2 * ty + 8)
    s0 = F.stocks()
    B.build(G.m, sym, TF.I_DOME_M, g + 6, at=at, room=TF.RM_FACTORY, fit=False)
    n = G.m.peek(sym["BD_NODE"])
    s1 = F.stocks()
    paid = (s0[0] - s1[0], s0[1] - s1[1])
    G.run(3_000_000)
    mine = [j for j in jobs(G) if n in (j[2], j[5])]
    if rec(G, n)[4] != 1 or not mine:
        return f"ΕΡΓΟΤΑΞΙΟ: η σκηνή θέλει εργοτάξιο με εργασίες: {rec(G, n)[4]}, {mine}"
    nbrs = adj(G, n)
    fit, sel, s2, s3, _ = demolish(G, F, at)
    got = (s3[0] - s2[0], s3[1] - s2[1])
    if got != paid:
        return f"ΕΡΓΟΤΑΞΙΟ: πληρώθηκαν {paid}, πίσω {got} — η πρόζα λέει όλα"
    builds = sum(1 for j in jobs(G) if j[1] == 0)
    if econ(G, 91) != builds:
        return f"ΕΡΓΟΤΑΞΙΟ: EC_NBUILD {econ(G, 91)}, Build στον πίνακα {builds}"
    why = common(G, F, n, nbrs)
    if why:
        return "ΕΡΓΟΤΑΞΙΟ: " + why
    say(f"ΕΡΓΟΤΑΞΙΟ: το εργοτάξιο {n} με τις εργασίες του (είδη {[j[1] for j in mine]}) "
        f"έφυγε, πίσω όλα όσα πληρώθηκαν {paid}")
    return None


def people(sym, g, patch=(), quiet=False):
    """Ο θόλος της αποικίας με τους περισσότερους μέσα."""
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G, F = game(sym, g, patch)
    G.run(2_000_000)
    G.settle()
    live = [d for d in range(64) if dome(G, d)[4] == 2]
    n = max(live, key=lambda d: len(standing(G, d)))
    who = standing(G, n)
    if len(who) < 2:
        return f"ΑΝΘΡΩΠΟΙ: η σκηνή θέλει δύο μέσα, ο {n} έχει {who}"
    nbrs = adj(G, n)
    tail = [v for v in nbrs if adj(G, v) and adj(G, v)[-1] == n]
    if not tail:
        return f"ΑΝΘΡΩΠΟΙ: η σκηνή θέλει γείτονα με τον {n} τελευταίο: {[adj(G, v) for v in nbrs]}"
    x, y = centre(G, n)
    G.camera((x >> 1) - 10, (y >> 1) - 5)
    worst = demolish(G, F, (x, y))[4]
    if not quiet:
        WORST["ο θόλος %d της αποικίας" % n] = worst
    elif worst > CEIL_US:
        return f"ΑΝΘΡΩΠΟΙ: ο χειρότερος γύρος {worst / MS:.1f} ms > {CEIL_US / MS:.0f}"
    to = {ag(G, a, 1) for a in who}
    t = min(to)
    if len(to) != 1 or not 64 <= t < 96 or struct(G, t)[2] not in (K_AIRLOCK, K_SHIP):
        return f"ΑΝΘΡΩΠΟΙ: οι {who} πήγαν στους κόμβους {to}, όχι σε ένα airlock ή στο σκάφος"
    inside = struct(G, t)[4] == 2
    for a in who:
        fl = ag(G, a, 0)
        if (fl & F_WORKING or ag(G, a, 3, True) != NO_TASK or ag(G, a, 7) != SUIT_TRIP
                or bool(fl & F_INDOORS) != inside):
            return (f"ΑΝΘΡΩΠΟΙ: ο {a}: σημαίες #{fl:02X}, εργασία {ag(G, a, 3, True)}, "
                    f"στολή {ag(G, a, 7)} — η πρόζα λέει όχι χειριστής, καμία, "
                    f"{SUIT_TRIP}, {'μέσα' if inside else 'έξω'}")
    why = common(G, F, n, nbrs)
    if why:
        return "ΑΝΘΡΩΠΟΙ: " + why
    G.run(30_000_000)
    dead = [a for a in who if not ag(G, a, 0) & F_ALIVE]
    if dead:
        return f"ΑΝΘΡΩΠΟΙ: μετά από 30 s πέθαναν οι {dead}"
    same = truth(G)
    if not same[0]:
        return "ΑΝΘΡΩΠΟΙ: μετά από 30 s οθόνη/πλήρης σχεδίαση: " + same[1]
    say(f"ΑΝΘΡΩΠΟΙ: ο θόλος {n} με τους {who}: στο airlock {t}, "
        f"{'μέσα' if inside else 'έξω'}, χωρίς δουλειά και με γεμάτη στολή, ζωντανοί "
        f"30 s μετά· γείτονες {nbrs}, και ήταν ο τελευταίος στη λίστα των {tail}")
    if not quiet:
        G.m.screenshot(os.path.join(ROOT, "build", "demolish_people.png"), aspect=True)
    return None


def mines(sym, g, patch=(), quiet=False):
    """ΤΟ ΔΩΡΕΑΝ ΟΡΥΧΕΙΟ ΔΕΝ ΕΠΙΣΤΡΕΦΕΙ ΤΙΠΟΤΑ (βήμα 123). Το πρώτο ορυχείο της
    αποικίας μπαίνει χωρίς μέταλλο, με ST_FREE· ένα δεύτερο πληρώνει 30. Το
    δεύτερο γκρεμίζεται εργοτάξιο και δίνει πίσω και τα 30· το πρώτο τίποτα —
    αλλιώς ένα δωρεάν εργοτάξιο, βαλμένο και γκρεμισμένο, θα έδινε 30 μέταλλο
    κάθε φορά, για πάντα."""
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G, F = game(sym, g, patch)
    G.run(1_000_000)
    G.settle()
    g_metal = L["G_econ_state"] + 6
    metal = lambda: G.m.peek(g_metal) | G.m.peek(g_metal + 1) << 8
    spots = B.res_spots("ore", 4, 2)
    if len(spots) < 2:
        return f"ΟΡΥΧΕΙΑ: η σκηνή θέλει δύο θέσεις στη φλέβα: {spots}"
    nodes, paid = [], []
    for tx, ty in spots:
        m0 = metal()
        if not B.build(G.m, sym, 8, g_metal, at=(2 * tx + 4, 2 * ty + 4)):
            return f"ΟΡΥΧΕΙΑ: το ορυχείο στο ({tx}, {ty}) δεν μπήκε"
        new = [64 + k for k in range(32) if 64 + k not in nodes
               and struct(G, 64 + k)[2] == K_MINE and struct(G, 64 + k)[4]]
        if len(new) != 1:
            return f"ΟΡΥΧΕΙΑ: μετά το FIRE ορυχεία {new} καινούργια"
        nodes += new
        paid.append(m0 - metal())
    ops = [struct(G, n)[6] & 0x08 for n in nodes]
    if paid != [0, 30] or ops != [0x08, 0]:
        return (f"ΟΡΥΧΕΙΑ: πλήρωσαν {paid}, ST_FREE {ops} — η πρόζα λέει [0, 30] και "
                f"το πρώτο μόνο")
    back = []
    for n in reversed(nodes):
        G.settle()
        x, y = centre(G, n)
        G.camera((x >> 1) - 10, (y >> 1) - 5)
        _, _, s0, s1, _ = demolish(G, F, (x, y))
        back.append(s1[0] - s0[0])
        if struct(G, n)[4]:
            return f"ΟΡΥΧΕΙΑ: το {n} δεν γκρεμίστηκε: {struct(G, n)}"
    if back != [30, 0]:
        return (f"ΟΡΥΧΕΙΑ: γκρεμισμένα εργοτάξια, πίσω {back} — η πρόζα λέει 30 από το "
                f"δεύτερο και 0 από το δωρεάν")
    say(f"ΟΡΥΧΕΙΑ: το πρώτο μπήκε δωρεάν (ST_FREE), το δεύτερο πλήρωσε 30· γκρεμισμένα "
        f"εργοτάξια, πίσω 30 και 0")
    return None


def airlock(sym, g, patch=(), quiet=False):
    """Το airlock της αποικίας (65) φεύγει με τον διάδρομό του. Και όταν φεύγει
    ο θόλος στην άλλη άκρη, το airlock μένει χωρίς διάδρομο: ελεύθερο."""
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G, F = game(sym, g, patch)
    G.run(1_000_000)
    G.settle()
    n = 65
    if struct(G, n)[2] != K_AIRLOCK or struct(G, n)[6] != 1:
        return f"AIRLOCK: η σκηνή θέλει το 65 ενωμένο airlock: {struct(G, n)}"
    mine = [c for c in corridors(G) if c[4] and n in c[:2]]
    tiles = sum(c[3] for c in mine)
    d = mine[0][0]
    nbrs = adj(G, n)
    free0 = econ(G, 63)
    x, y = centre(G, n)
    G.camera((x >> 1) - 10, (y >> 1) - 5)
    _, _, s0, s1, _ = demolish(G, F, (x, y))
    price = (AIRLOCK[0] + CORR[0] * tiles, AIRLOCK[1] + CORR[1] * tiles)
    got = (s1[0] - s0[0], s1[1] - s0[1])
    if got != (price[0] // 2, price[1] // 2):
        return f"AIRLOCK: πίσω {got}, η πρόζα λέει τα μισά του {price}"
    if econ(G, 63) != free0:
        return f"AIRLOCK: τα ελεύθερα airlock {free0} -> {econ(G, 63)}"
    why = common(G, F, n, nbrs)
    if why:
        return "AIRLOCK: " + why
    # --- ο θόλος στην άλλη άκρη, σε καινούργιο παιχνίδι ---
    G, F = game(sym, g, patch)
    G.run(1_000_000)
    G.settle()
    nbrs = adj(G, d)
    x, y = centre(G, d)
    G.camera((x >> 1) - 10, (y >> 1) - 5)
    demolish(G, F, (x, y))
    if struct(G, n)[6] != 0 or econ(G, 63) != free0 + 1:
        return (f"AIRLOCK: ο θόλος {d} έφυγε, και το airlock {n} έχει ST_JOINED "
                f"{struct(G, n)[6]}, ελεύθερα {econ(G, 63)} — η πρόζα λέει 0 και {free0 + 1}")
    why = common(G, F, d, nbrs)
    if why:
        return f"AIRLOCK, ο θόλος {d}: " + why
    say(f"AIRLOCK: το {n} και ο διάδρομός του ({tiles} πλακίδια) έφυγαν, πίσω {got}· όταν "
        f"φεύγει ο θόλος {d}, το {n} μένει χωρίς διάδρομο και μετρά στα ελεύθερα")
    return None


def refuse(sym, g, patch=(), quiet=False):
    """Κόκκινο, και ούτε το D ούτε το FIRE κάνουν τίποτα: το σκάφος (στο
    main.sna, η δομή 64), η πίστα όσο έρχεται πλοίο, το κενό έδαφος."""
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    out = []
    for what in ("σκάφος", "πίστα", "τίποτα"):
        G, F = game(sym, g, patch, TG.SNA if what == "σκάφος" else None)
        G.run(1_000_000)
        G.settle()
        if what == "σκάφος" and struct(G, 64)[2] != K_SHIP:
            return f"ΑΡΝΗΣΗ: η δομή 64 του main.sna δεν είναι το σκάφος: {struct(G, 64)}"
        if what == "πίστα":
            if struct(G, 64)[2] != K_PAD:
                return f"ΑΡΝΗΣΗ: η δομή 64 της αποικίας δεν είναι η πίστα: {struct(G, 64)}"
            G.m.poke(L["G_econ_state"] + 72, 1)              # EC_SHSTATE: έρχεται
        if what == "τίποτα":
            tx, ty = B.clear_spots(8, 1, dome=True)[0]
            at = (2 * tx + 8, 2 * ty + 8)
        else:
            at = centre(G, 64)
        G.camera((at[0] >> 1) - 10, (at[1] >> 1) - 5)
        before = (struct(G, 64), deg(G, 64), [c for c in corridors(G) if 64 in c[:2]])
        fit, sel, _, _, _ = demolish(G, F, at, fire=False)
        F.fire()
        G.settle()
        after = (struct(G, 64), deg(G, 64), [c for c in corridors(G) if 64 in c[:2]])
        if fit & AF_DEMO or after != before:
            return f"ΑΡΝΗΣΗ ({what}): ac_fit {fit}, {before} -> {after}"
        out.append(what)
    say(f"ΑΡΝΗΣΕΙΣ: κόκκινο, και τίποτα δεν αλλάζει — {', '.join(out)}")
    return None


# --------------------------------------------------------------------------
# ΑΡΝΗΤΙΚΑ
# --------------------------------------------------------------------------
def at_ovl(sym, name, n, pat, edits, hits=1):
    """Τα bytes του κώδικα των τρυπών: το pat μέσα σε n bytes από την ετικέτα,
    ακριβώς `hits` φορές· τα edits σε καθένα. -> [("hole", δείκτης στην
    τράπεζα 1, τιμή)], ή None."""
    o = sym[name] - GH
    at = [o + k for k in range(n - len(pat) + 1) if list(OVL[o + k:o + k + len(pat)]) == pat]
    if len(at) != hits:
        return None
    return [("hole", 128 * ((h + d) >> 5) + 96 + ((h + d) & 31), v)
            for h in at for d, v in edits]


def negatives(sym, g):
    G, _ = game(sym, g)
    w = lambda a: [a & 255, a >> 8]
    cd = lambda name: [0xCD] + w(sym[name])
    nop3 = [(0, 0), (1, 0), (2, 0)]

    def ram(name, n, pat, edits):
        data = G.m.read_ram(sym[name], n)
        at = [k for k in range(n - len(pat) + 1) if list(data[k:k + len(pat)]) == pat]
        if len(at) != 1:
            return None
        return [("ram", sym[name] + at[0] + d, v) for d, v in edits]

    # dmc_axis: add a,3 · ... · sub 64 + 1 -> add a,1 · sub 64: από κέντρο σε κέντρο
    pad = at_ovl(sym, "DMCA_S", 8, [0xC6, 3], [(1, 1)])
    pad2 = at_ovl(sym, "DMCA_S", 20, [0xD6, 65], [(1, 64)])
    return [
        ("καμία επιστροφή", at_ovl(sym, "DMR_ALL", 13, cd("EC_ADD_STOCK"), nop3, hits=2),
         factory),
        ("όλα πίσω και από χτισμένο", at_ovl(sym, "DMK_NX", 30, [0xFE, 2, 0x20], [(2, 0x18)]),
         factory),
        # ld (hl),CT_EMPTY · dec hl · ld (hl),CT_EMPTY -> nop (βήμα 154: οι δύο άκρες)
        ("οι διάδρομοι μένουν", at_ovl(sym, "DMK_ME", 12, [0x36, 0xFE, 0x2B, 0x36, 0xFE],
                                       [(0, 0), (1, 0), (3, 0), (4, 0)]),
         factory),
        ("ο κόσμος δεν ξαναγράφεται", at_ovl(sym, "DMW_GO", 4, cd("DM_WORLD"), nop3), factory),
        ("ο διάδρομος χωρίς το tile γύρω του", pad and pad2 and pad + pad2, airlock),
        ("μόνο το αποτύπωμα, όχι οι διάδρομοι", at_ovl(sym, "DMK_AIR", 10, cd("DM_CRECT"), nop3),
         factory),
        ("τα δωμάτια μένουν", at_ovl(sym, "DMW_GO", 12, cd("ROOMS_REBUILD"), nop3), at_once),
        ("οι εργασίες μένουν", at_ovl(sym, "DMJ_DEL", 6, [0x36, 0xFF], [(0, 0), (1, 0)]), site),
        ("οι άνθρωποι μένουν", at_ovl(sym, "DMP_T", 40, cd("LK_EACH"), nop3), people),
        ("οι ακμές μένουν", at_ovl(sym, "DMP_T", 80, cd("LK_CUT"), nop3), people),
        ("ο κόμβος πίσω στη λίστα του γείτονα",
         at_ovl(sym, "DMG_LP", 30, [0xBE, 0x20, 0x01, 0x73], [(3, 0)]), people),
        ("το airlock μένει ενωμένο", at_ovl(sym, "DMK_AIR", 30, [0x36, 0x00, 0x21],
                                            [(0, 0), (1, 0)]), airlock),
        ("το σκάφος γκρεμίζεται", ram("DMC_ST", 4, [0xFE, K_SHIP, 0x28], [(2, 0), (3, 0)]),
         refuse),
        ("κανένα ορθογώνιο στη λίστα", at_ovl(sym, "DMV_LP", 30, [0x3E, DK_RECT] + cd("DIRTY_PUSH"),
                                              [(2, 0), (3, 0), (4, 0)]), factory),
        # bit ST_FREE,(hl) -> bit 0,(hl): ποτέ δωρεάν (βήμα 123)
        ("το δωρεάν ορυχείο δίνει 30", at_ovl(sym, "DMD_IT", 64, [0xCB, 0x5E], [(1, 0x46)]),
         mines),
        ("το ορθογώνιο χωρίς να σηκωθεί το φάντασμα",
         at_ovl(sym, "DHO_RECT", 20, cd("DT_GHOST_RECT"), nop3), factory),
        ("όλα τα ορθογώνια σε ένα πέρασμα",
         [("ram", sym["DIRTY_COST"] + 2 * DK_RSIZE + k, 0) for k in (0, 1)], people),
    ]


def main():
    sym, g = TG.build()
    if not OVL:
        check(False, "λείπει το build/ovl.bin")
        sys.exit(1)
    err = tables(sym, g)
    check(err is None, err or "ΠΙΝΑΚΕΣ: ο κώδικας στις τρύπες, ο κόσμος = το μοντέλο")
    for fn, what in ((at_once, "ΑΜΕΣΩΣ: τα δωμάτια χωρίς αυτόν, πριν τρέξει ο τροχός"),
                     (factory, "ΕΡΓΟΣΤΑΣΙΟ: τα μισά πίσω, ο θόλος και ο διάδρομός του φεύγουν"),
                     (bend, "ΣΤΡΟΦΗ: ο διαγώνιος διάδρομος με τη στροφή του φεύγει όλος"),
                     (site, "ΕΡΓΟΤΑΞΙΟ: όλα πίσω, οι εργασίες του σβήνουν"),
                     (people, "ΑΝΘΡΩΠΟΙ: βγαίνουν, ζουν, χωρίς δουλειά"),
                     (airlock, "AIRLOCK: φεύγει με τον διάδρομό του, και μένει ελεύθερο"),
                     (mines, "ΟΡΥΧΕΙΑ: το δωρεάν δεν δίνει τίποτα πίσω, το πληρωμένο όλα"),
                     (refuse, "ΑΡΝΗΣΕΙΣ: το σκάφος, η πίστα με πλοίο, το κενό")):
        err = fn(sym, g)
        check(err is None, err or what)
    for what, us in WORST.items():
        check(us <= CEIL_US, f"ΚΟΣΤΟΣ: {what}, ο χειρότερος γύρος από το FIRE ως να "
                             f"αδειάσει η λίστα {us / MS:.1f} ms <= {CEIL_US / MS:.0f}")
    for label, patch, test in negatives(sym, g):
        if not patch:
            check(False, f"ΑΡΝΗΤΙΚΟ «{label}»: το μοτίβο δεν βρέθηκε")
            continue
        try:
            err = test(sym, g, patch, quiet=True)
        except AssertionError as e:
            err = f"assert: {e}"
        check(err is not None,
              f"ΑΡΝΗΤΙΚΟ «{label}»: {err or 'ΔΕΝ ΠΙΑΣΤΗΚΕ'}")
    if FAIL:
        print(f"\n{len(FAIL)} ΑΠΟΤΥΧΙΕΣ")
        sys.exit(1)
    print("\nΟΛΑ ΚΑΛΑ")


if __name__ == "__main__":
    main()
