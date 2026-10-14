#!/usr/bin/env python3
"""Τα μονοπάτια που φεύγουν (βήμα 102, DESIGN §9.3).

Η πρόζα:

  ΚΡΑΤΙΕΤΑΙ  κάθε δομή θυμάται πού πήγε η σύνδεσή της τη στιγμή που μπήκε,
             ένα byte στις θέσεις 96-127 του node_deg (LK_OWN): ο κόμβος στην
             άλλη άκρη, το bit 7 αν το μονοπάτι πάει πρώτα κατά y, το bit 5
             (LKO_GROUND) αν είναι σύνδεση εδάφους. Ενας θόλος δεν γράφει
             τίποτα: η σύνδεσή του φεύγει όταν τελειώσει.
  ΦΕΥΓΕΙ     όταν γκρεμίζεται μια δομή, φεύγει η σύνδεσή της, και κάθε
             σύνδεση που τελείωνε σε αυτήν. Τα tiles του μονοπατιού μένουν
             θεμέλιο χωρίς κατοχή, όπως ήταν από την τοποθέτηση (βήμα 131· ως
             το 130 είχαν κατοχή 2, το bit 5, και το έχαναν εδώ): χτίζεται
             πάλι πάνω τους.
  ΞΑΝΑΔΕΝΕΤΑΙ  όποια δομή κρεμόταν από αυτήν — η σύνδεσή της, μονοπάτι ή
             εδάφους, τελείωνε εκεί — κρέμεται πια από εκεί που κρεμόταν εκείνη,
             με σύνδεση εδάφους ζωγραφισμένη: ο ίδιος δρόμος ως το σκάφος, κανένας
             κύκλος, καμία διπλή ακμή, ό,τι κι αν κρέμεται από τα ορφανά. Από το
             βήμα 116 (dm_up): αν ο γονιός έχει ήδη οκτώ ακμές, ο δικός του
             γονιός, και πάει λέγοντας· αν εκείνη δεν κρεμόταν από πουθενά, το
             σκάφος. Η αποικία δοκιμών δεν έχει σκάφος, και το airlock της δεν
             κρεμόταν από πουθενά: εκεί μένουν χωρίς σύνδεση. Και ένα εργοτάξιο
             θόλου που έμεινε χωρίς ακμή παίρνει σύνδεση εδάφους ως το
             κοντινότερο airlock ή το σκάφος (dm_sites, χωρίς ζωγραφιά, όπως στην
             τοποθέτηση). Ολα αυτά στο tests/test_leftover.py.

Ο κόσμος μετά από κάθε κατεδάφιση είναι ΑΚΡΙΒΩΣ ένα μοντέλο σε Python: ο
κόσμος πριν, με το bit 4 από τις εγγραφές που μένουν (tests/test_demolish.py),
και με τις νέες συνδέσεις εδάφους μία-μία με τη σειρά των κόμβων
(tools/reach.py: ground). Και κανένα tile με bit 5 σε όλο τον κόσμο, και κάθε
μονοπάτι που λένε τα LK_OWN θεμέλιο: το Γ τους (το bit 7) είναι εκείνο που
περπατούν οι άποικοι (src/walk6.asm, βήμα 118). Η οθόνη = πλήρης σχεδίαση, ο
κέρσορας εκεί που ήταν, ο χειρότερος γύρος ως CEIL_US.

Αρνητικά, με τον κώδικα πειραγμένο: πάντα πρώτα κατά x (στο lk_keepp από το
βήμα 131· ως τότε στην κατεδάφιση, μαζί με το «το μονοπάτι μένει», που δεν
έχει πια τι να σβήσει)· τίποτα δεν κρατιέται· η σύνδεση εδάφους σαν μονοπάτι· μόνο το δικό του
μονοπάτι· κανένα ξαναδέσιμο· χωρίς γονιό, δένεται κάπου· τα σκέλη δεν
ζωγραφίζονται. Το «ο γονιός ξεχνιέται» πήγε στο tests/test_leftover.py στο
βήμα 116: εδώ ο γονιός του γκρεμισμένου είναι το σκάφος, που από τότε είναι
και η εφεδρεία όταν γονιός δεν υπάρχει, και το αρνητικό δεν μπορούσε πια να
αποτύχει.
"""
import ctypes, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import test_demolish as D                                # noqa: E402
import balance as B                                      # noqa: E402
import reach                                             # noqa: E402

FAIL = []
SOLAR, AIRLOCK = 4, 9                                    # σειρές του bld_items
K_SHIP = 7                                               # src/const.asm
LKG, LOST = 0x20, 0xFF                                   # LKO_GROUND, LKO_LOST
MS = 1000
CEIL_US = D.CEIL_US
WORST = {}
L = D.L
sb = reach.sb


def check(ok, msg):
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ ") + msg)
    if not ok:
        FAIL.append(msg)


# --------------------------------------------------------------------------
# ανάγνωση
# --------------------------------------------------------------------------
def own(G, n):
    return G.m.peek(L["G_rt_nodes"] + 96 + n - 64)


def owns(G):
    return {n: own(G, n) for n in range(64, 96) if own(G, n)}


def recs(G):
    b6 = bytes(G.bank(6)[:0x4000])
    gd, gs = L["G_dome_tbl"] - 0x4000, L["G_struct_tbl"] - 0x4000
    domes = [[b6[gd + 24 * d + k] for k in (0, 1, 2, 4)] for d in range(64)]  # cx cy size state
    structs = [list(b6[gs + 8 * k:gs + 8 * k + 7]) for k in range(32)]
    return domes, structs, G.m.read_ram(L["G_struct_dims"], 64)


def world(G):
    return bytes(G.bank(4)[:0x4000])


def snap(G):
    return dict(owns=owns(G), deg=[D.deg(G, n) for n in range(96)],
                adj=[D.adj(G, n) for n in range(96)], recs=recs(G), world=world(G),
                cur=(G.m.peek(G.sym["CUR_HX"]), G.m.peek(G.sym["CUR_HY"])))


def fp(rc, n):
    return reach.footprint(n, *rc)


def path_tiles(rc, n, b):
    """Τα tiles του μονοπατιού του n όπως τα λέει το byte b: το Γ από κέντρο σε
    κέντρο, έξω από τα δύο αποτυπώματα (al_walk)."""
    a, ori = b & 0x5F, b >> 7
    fn, fa = fp(rc, n), fp(rc, a)
    return [(x, y) for x, y in reach.lwalk(fn[1], fa[1], ori)
            if not reach.in_rect(fn[0], x, y) and not reach.in_rect(fa[0], x, y)]


def paths_ok(G):
    """Κανένα tile με bit 5 (από το βήμα 131 το μονοπάτι δεν έχει κατοχή), και
    κάθε μονοπάτι των LK_OWN θεμέλιο: το Γ του bit 7 είναι αυτό που χτίστηκε."""
    rc = recs(G)
    w = world(G)
    five = [(k % 128 - 64, k // 128 - 64) for k in range(0x4000) if w[k] & 0x20]
    if five:
        return f"bit 5 σε {len(five)} tiles (π.χ. {five[:3]})"
    for n, b in owns(G).items():
        if b & LKG or b == LOST or not rc[1][n - 64][4]:
            continue
        bad = [t for t in path_tiles(rc, n, b) if w[reach.widx(*t)] & 7 != 7]
        if bad:
            return f"το μονοπάτι του {n} (#{b:02X}) δεν είναι θεμέλιο στα {bad[:3]}"
    return None


def look(G):
    """Η οθόνη = πλήρης σχεδίαση; Σαν το G.truth, αλλά ΧΩΡΙΣ ΙΧΝΟΣ: η πλήρης
    σχεδίαση της σύγκρισης διορθώνει την οθόνη ΚΑΙ γράφει τα αρχεία του
    renderer — πού ζωγραφίστηκε κάθε φιγούρα, το αρχείο του κέρσορα. Το βήμα
    102 επανέφερε μόνο την οθόνη, και όταν η πρώτη ματιά έπεφτε σε δύο
    αποίκους που επικαλύπτονται, η οθόνη γύριζε πίσω ενώ τα αρχεία έμεναν: η
    φιγούρα σβηνόταν αργότερα από αλλού και άφηνε υπόλειμμα, που η επόμενη
    ματιά έβρισκε (βήμα 103). Τώρα στην κορυφή του βρόχου κρατιούνται και οι
    οκτώ τράπεζες, και γυρίζουν όλες."""
    on = G.still()
    G.probe([])                                          # στην κορυφή του βρόχου
    keep = [bytes(G.bank(n)[:0x4000]) for n in range(8)]
    pic = G.play()
    G.full()
    ref = G.play()
    for n in range(8):
        ctypes.memmove(G.bank(n), keep[n], 0x4000)
    G.m.set_pc(G.top)
    G.go(on)
    return D.R.shape(pic, ref)


def dups(G):
    """Κόμβοι με τον ίδιο γείτονα δύο φορές."""
    return {n: D.adj(G, n) for n in range(96) if len(set(D.adj(G, n))) != len(D.adj(G, n))}


def shot(G, name):
    """build/name, με τις λωρίδες της διακοπής ανοιχτές: το probe του truth
    αφήνει di, και το HUD βγαίνει στο mode του κάδρου.

    Οπως το G.probe(["IS_ON"]) ως το βήμα 119, χωρίς τον έλεγχο του PC στο
    τέλος: με τις διακοπές ανοιχτές το PC πέφτει κάποτε μέσα στη διακοπή, όσο
    ~6 % του χρόνου, και το βήμα 119, που άλλαξε τη φάση, το βρήκε (pc=#0138)."""
    m, top, io = G.m, G.top, G.sym["IS_ON"]
    for _ in range(40000):
        if top <= m.pc < top + 13:
            break
        m.run_us(50)
    m.run_code(D.R.PROBE, bytes([0xF3, 0xCD, io & 255, io >> 8, 0x18, 0xFE]), frames=100)
    m.set_pc(top)
    G.last, G.inw = None, False
    G.m.run_frames(3)
    G.m.screenshot(os.path.join(ROOT, "build", name), aspect=True)


def dist(G, a, b):
    return G.bank(1)[128 * a + b]


# --------------------------------------------------------------------------
# θέσεις και τοποθέτηση
# --------------------------------------------------------------------------
def find_spot(G, sym, item, pred, centre, rmax=18):
    """Ο πρώτος κέρσορας, από το centre (tiles) προς τα έξω, όπου το item
    μπαίνει (reach.plan) και το pred(res, at) αληθεύει. -> (at, res)."""
    w = world(G)
    domes, structs, dims = recs(G)
    kind, param, wd, ht = G.m.read_ram(sym["BLD_ITEMS"] + 8 * item, 4)
    for r in range(rmax):
        for ty in range(centre[1] - r, centre[1] + r + 1):
            for tx in range(centre[0] - r, centre[0] + r + 1):
                if max(abs(tx - centre[0]), abs(ty - centre[1])) != r:
                    continue
                if not (-60 <= tx and tx + wd <= 60 and -60 <= ty and ty + ht <= 60):
                    continue
                if not all(reach.ok_tile(w[reach.widx(tx + i, ty + j)])
                           for i in range(wd) for j in range(ht)):
                    continue
                at = (2 * tx + wd, 2 * ty + ht)
                res = reach.plan(w, domes, structs, dims, kind, param, wd, ht, *at)
                if res["ok"] and pred(res, at):
                    return at, res
    return None, None


def place(G, sym, g, item, at):
    """Ο παίκτης το βάζει στο at. -> ο κόμβος, ή None."""
    ok = B.build(G.m, sym, item, g + 6, at=at, fit=False)
    G.settle()
    return G.m.peek(sym["BD_NODE"]) if ok else None


def tile(at):
    return (at[0] >> 1, at[1] >> 1)


def path_to(node, ori=None, least=2):
    return lambda res, at: (res["path"] is not None and res["path"][0] == node
                            and (ori is None or res["path"][1] == ori)
                            and len(res["path"][2]) >= least)


def y_path(least):
    return lambda res, at: (res["path"] is not None and res["path"][1] == 1
                            and len(res["path"][2]) >= least)


def anchor_is(G, node):
    def pred(res, at):
        domes, structs, dims = recs(G)
        deg = [D.deg(G, n) for n in range(96)]
        return reach.anchor(structs, deg, 255, at[0], at[1]) == node
    return pred


# --------------------------------------------------------------------------
# το μοντέλο της κατεδάφισης
# --------------------------------------------------------------------------
def expect(G, s, gone):
    """Από το snap s πριν, με τον gone γκρεμισμένο: (ο κόσμος, τα LK_OWN, οι
    νέες ακμές) όπως τα λέει η πρόζα."""
    domes, structs, dims = [[list(r) for r in t] for t in s["recs"][:2]] + [s["recs"][2]]
    rc0 = s["recs"]
    cleared, lost = [], []
    own2 = dict(s["owns"])
    for n, b in s["owns"].items():
        if n == gone:
            del own2[n]
        elif b & 0x5F == gone:
            lost.append(n)
            del own2[n]
        else:
            continue
        if not b & LKG:
            cleared += path_tiles(rc0, n, b)
    if gone < 64:
        domes[gone][3] = 0
    else:
        structs[gone - 64][4] = 0
    deg = list(s["deg"])
    for v in s["adj"][gone]:
        deg[v] -= 1
    deg[gone] = 0
    par = s["owns"][gone] & 0x5F if gone in s["owns"] else None

    def up(p):
        """Το dm_up (βήμα 116): ο γονιός αν έχει θέση, αλλιώς ο δικός του, και
        πάει λέγοντας· χωρίς γονιό το σκάφος, αν η δομή 0 είναι σκάφος."""
        if p is None:
            p = 64 if structs[0][2] == K_SHIP else None
        for _ in range(32):
            if p is None or deg[p] < 8:
                return p
            p = own2.get(p, 0) & 0x5F or None
        return None
    grounds = []
    for t in sorted(lost):
        a = up(par)
        if a is not None:
            own2[t] = a | LKG
            deg[t] += 1
            deg[a] += 1
            grounds.append((t, a))
    # ΕΝΑ ΕΡΓΟΤΑΞΙΟ ΘΟΛΟΥ ΧΩΡΙΣ ΑΚΜΗ (βήμα 116, dm_sites): σύνδεση εδάφους από
    # το κέντρο του ως το κοντινότερο airlock ή το σκάφος, χωρίς ζωγραφιά.
    sites = []
    for d in range(64):
        if domes[d][3] == 1 and deg[d] == 0:
            a = reach.anchor(structs, deg, d, domes[d][0], domes[d][1])
            if a != 255:
                deg[d] += 1
                deg[a] += 1
                sites.append((d, a))
    wl = D.model(G, s["world"])             # τα tiles των μονοπατιών μένουν (βήμα 131)
    rc = (domes, structs, dims)
    for t, a in grounds:
        ft = fp(rc, t)
        wl = reach.ground(wl, ft[0], ft[1], fp(rc, a))
    return bytes(wl), own2, grounds + sites, cleared, lost


def after(G, F, s, gone, what, worst):
    """Ο,τι λέει η πρόζα μετά από την κατεδάφιση του gone: None, ή το πρώτο
    που λείπει."""
    want, own2, grounds, cleared, lost = expect(G, s, gone)
    got = world(G)
    if got != want:
        bad = [k for k in range(0x4000) if got[k] != want[k]]
        k = bad[0]
        return (f"{what}: ο κόσμος δεν είναι το μοντέλο: {len(bad)} tiles, πρώτο "
                f"({k % 128 - 64}, {k // 128 - 64}) #{got[k]:02X} αντί #{want[k]:02X}")
    if owns(G) != own2:
        return f"{what}: LK_OWN {owns(G)}, η πρόζα λέει {own2}"
    why = paths_ok(G)
    if why:
        return f"{what}: {why}"
    for t, a in grounds:
        if t not in D.adj(G, a) or a not in D.adj(G, t):
            return f"{what}: καμία ακμή {t}-{a}: {D.adj(G, t)}, {D.adj(G, a)}"
    if dups(G):
        return f"{what}: διπλές ακμές {dups(G)}"
    cur = (G.m.peek(G.sym["CUR_HX"]), G.m.peek(G.sym["CUR_HY"]))
    if cur != s["cur"]:
        return f"{what}: ο κέρσορας {s['cur']} -> {cur}"
    # Η ΟΘΟΝΗ ΤΩΡΑ, Ή ΩΣ ΔΕΚΑ ΔΕΥΤΕΡΟΛΕΠΤΑ ΜΕΤΑ. Δύο άποικοι που περπατούν μαζί
    # στην ίδια ακμή — όσοι βγήκαν από αυτό που γκρεμίστηκε — ζωγραφίζονται ο
    # ένας πάνω στον άλλο με άλλη σειρά από τη λίστα αλλαγών (fg_draw) και άλλη
    # από την πλήρη σχεδίαση: 9-26 bytes σε ένα-δύο tiles, ώσπου να χωρίσουν,
    # και στο βήμα 101 (DESIGN §15). Ενα σκέλος που δεν ζωγραφίστηκε δεν
    # διορθώνεται μόνο του: αποτυγχάνει και τις πέντε φορές. Κάθε ματιά αφήνει
    # την οθόνη όπως την ζωγράφισε το παιχνίδι (look).
    for _ in range(5):
        same = look(G)
        if same[0]:
            break
        G.run(2_000_000)
        G.settle()
    if not same[0]:
        return f"{what}: οθόνη/πλήρης σχεδίαση: " + same[1]
    if worst > CEIL_US:
        return f"{what}: ο χειρότερος γύρος {worst / MS:.1f} ms > {CEIL_US / MS:.0f}"
    return None


def gone_at(G, F, s, n, what):
    """LOOK, M, D, FIRE πάνω στον n, και ο έλεγχος. -> (λάθος, ο χειρότερος γύρος)."""
    at = D.centre(G, n)
    worst = D.demolish(G, F, at)[4]
    if D.rec(G, n)[4]:
        return f"{what}: ο {n} δεν γκρεμίστηκε", worst
    return after(G, F, s, n, what, worst), worst


def snap_at(G, n):
    """Ο κέρσορας στον n πριν από το snap: ο κέρσορας του snap είναι εκεί."""
    at = D.centre(G, n)
    G.m.poke(G.sym["CUR_HX"], at[0] & 0xFF)
    G.m.poke(G.sym["CUR_HY"], at[1] & 0xFF)
    return snap(G)


# --------------------------------------------------------------------------
# ΣΚΗΝΕΣ
# --------------------------------------------------------------------------
def colony_two(sym, g, patch=()):
    """Η αποικία, και δύο ηλιακά: το S1 με μονοπάτι πρώτα κατά x ως το airlock
    65, το S2 με μονοπάτι πρώτα κατά y (το x το κόβει κάτι). -> (G, F, S1, S2,
    res1, res2)."""
    G, F = D.game(sym, g, patch)
    G.run(500_000)
    G.settle()
    c = tile(D.centre(G, 65))
    at1, res1 = find_spot(G, sym, SOLAR, path_to(65, 0, 3), (c[0] + 5, c[1] - 3))
    assert at1, "καμία θέση για ηλιακό με μονοπάτι κατά x ως το 65"
    G.camera(c[0] - 6, c[1] - 7)
    s1 = place(G, sym, g, SOLAR, at1)
    assert s1, f"ο ηλιακός δεν μπήκε στο {at1}"
    at2, res2 = find_spot(G, sym, SOLAR, y_path(3), (c[0] - 4, c[1] - 5))
    assert at2, "καμία θέση για ηλιακό με μονοπάτι κατά y"
    s2 = place(G, sym, g, SOLAR, at2)
    assert s2, f"ο δεύτερος ηλιακός δεν μπήκε στο {at2}"
    return G, F, s1, s2, res1, res2


def kept(sym, g, patch=(), quiet=False):
    """ΚΡΑΤΙΕΤΑΙ: δύο μονοπάτια (κατά x, κατά y), ένα airlock με σύνδεση
    εδάφους, ένας θόλος που δεν γράφει τίποτα."""
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G, F = D.game(sym, g, patch)
    G.run(500_000)
    G.settle()
    c = tile(D.centre(G, 65))
    G.camera(c[0] - 6, c[1] - 7)
    w0 = world(G)
    at1, res1 = find_spot(G, sym, SOLAR, path_to(65, 0, 3), (c[0] + 5, c[1] - 3))
    s1 = place(G, sym, g, SOLAR, at1)
    if not s1:
        return f"ΚΡΑΤΙΕΤΑΙ: ο ηλιακός δεν μπήκε στο {at1}"
    w1 = world(G)
    fp1 = ((at1[0] - 3) >> 1, (at1[1] - 3) >> 1, 3, 3)
    new7 = {(k % 128 - 64, k // 128 - 64) for k in range(0x4000)
            if w1[k] & 7 == 7 and w0[k] & 7 != 7}
    new7 = {t for t in new7 if not reach.in_rect(fp1, *t)}
    if own(G, s1) != 65 or new7 != set(res1["path"][2]) - {t for t in res1["path"][2]
                                                             if w0[reach.widx(*t)] & 7 == 7}:
        return (f"ΚΡΑΤΙΕΤΑΙ: ο {s1}: LK_OWN #{own(G, s1):02X}, η πρόζα λέει #41 (65, κατά x)· "
                f"νέο θεμέλιο έξω από το αποτύπωμα {sorted(new7)}, το μονοπάτι {res1['path'][2]}")
    at2, res2 = find_spot(G, sym, SOLAR, y_path(3), (c[0] - 4, c[1] - 5))
    if not at2:
        return "ΚΡΑΤΙΕΤΑΙ: καμία θέση για ηλιακό με μονοπάτι κατά y"
    s2 = place(G, sym, g, SOLAR, at2)
    p2 = res2["path"][0]
    if not s2 or own(G, s2) != p2 | 0x80:
        return f"ΚΡΑΤΙΕΤΑΙ: ο {s2}: LK_OWN #{own(G, s2 or 64):02X}, η πρόζα λέει #{p2 | 0x80:02X}"
    why = paths_ok(G)
    if why:
        return "ΚΡΑΤΙΕΤΑΙ: " + why
    # ένα airlock: διάδρομος ως τον κοντινότερο θόλο, και σύνδεση εδάφους
    d0 = tile(D.centre(G, 1))
    at3, res3 = find_spot(G, sym, AIRLOCK, lambda r, a: bool(r["corridors"]), (d0[0] + 6, d0[1] + 2))
    domes, structs, dims = recs(G)
    want = reach.anchor(structs, [D.deg(G, n) for n in range(96)], 255, *at3)
    a3 = place(G, sym, g, AIRLOCK, at3)
    if not a3 or own(G, a3) != want | LKG:
        return (f"ΚΡΑΤΙΕΤΑΙ: το airlock {a3}: LK_OWN #{own(G, a3 or 64):02X}, η πρόζα λέει "
                f"#{want | LKG:02X} (σύνδεση εδάφους ως το {want})")
    # ένας θόλος: τίποτα στο LK_OWN, και ο βαθμός του = η λίστα του
    o0 = owns(G)
    at4, _ = find_spot(G, sym, 0, lambda r, a: bool(r["corridors"]), (d0[0] - 2, d0[1] + 8))
    d4 = place(G, sym, g, 0, at4)
    if not d4 or owns(G) != o0:
        return f"ΚΡΑΤΙΕΤΑΙ: ο θόλος {d4} άλλαξε τα LK_OWN: {o0} -> {owns(G)}"
    say(f"ΚΡΑΤΙΕΤΑΙ: ο ηλιακός {s1} -> 65 κατά x (#{own(G, s1):02X}, {len(res1['path'][2])} "
        f"tiles), ο {s2} -> {p2} κατά y (#{own(G, s2):02X}), το airlock {a3} -> {want} στο "
        f"έδαφος (#{own(G, a3):02X}), ο θόλος {d4} τίποτα· κανένα bit 5, τα μονοπάτια των "
        f"LK_OWN θεμέλιο")
    return None


def mine(sym, g, patch=(), quiet=False):
    """ΔΙΚΟ ΤΟΥ: ο S2 (μονοπάτι κατά y ως τον S1) γκρεμίζεται. Η σύνδεσή του
    φεύγει, τα tiles του μονοπατιού μένουν θεμέλιο, και ένας ηλιακός χτίζεται
    πάνω τους."""
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G, F, s1, s2, res1, res2 = colony_two(sym, g, patch)
    old = res2["path"][2]
    s = snap_at(G, s2)
    err, worst = gone_at(G, F, s, s2, "ΔΙΚΟ ΤΟΥ")
    if err:
        return err
    w0, w1 = s["world"], world(G)
    for x, y in old:
        b0, b1 = w0[reach.widx(x, y)], w1[reach.widx(x, y)]
        if b1 & 0x37 != 7 or b1 & 0xC0 != b0 & 0xC0:
            return f"ΔΙΚΟ ΤΟΥ: το ({x}, {y}) του μονοπατιού #{b0:02X} -> #{b1:02X}, όχι θεμέλιο"
    if not quiet:
        WORST["ένας ηλιακός με το μονοπάτι του"] = worst
        shot(G, "unlink_mine.png")
    # χτίζεται πάλι: ένας ηλιακός που πατά tiles του παλιού μονοπατιού
    wd = 3
    on = lambda r, at: any(reach.in_rect(((at[0] - wd) >> 1, (at[1] - wd) >> 1, wd, wd), x, y)
                           for x, y in old)
    at, _ = find_spot(G, sym, SOLAR, on, old[len(old) // 2], rmax=4)
    if not at:
        return f"ΔΙΚΟ ΤΟΥ: κανένας ηλιακός δεν μπαίνει πάνω στο παλιό μονοπάτι {old}"
    n = place(G, sym, g, SOLAR, at)
    if not n or D.rec(G, n)[:2] != [at[0] & 255, at[1] & 255]:
        return f"ΔΙΚΟ ΤΟΥ: ο ηλιακός στο {at}, πάνω στο παλιό μονοπάτι, δεν μπήκε"
    say(f"ΔΙΚΟ ΤΟΥ: ο {s2} έφυγε με το μονοπάτι του ({len(old)} tiles, κατά y): θεμέλιο χωρίς "
        f"κατοχή, το decor ίδιο· του {s1} μένει· ένας ηλιακός μπήκε πάνω του στο {at}· "
        f"ο χειρότερος γύρος {worst / MS:.1f} ms")
    return None


def anchor_gone(sym, g, patch=(), quiet=False):
    """ΑΓΚΥΡΑ, στο main.sna με το σκάφος. Το airlock A1 κρέμεται από το σκάφος
    (σύνδεση εδάφους), ο ηλιακός S1 από το A1 (μονοπάτι), ο S2 από τον S1
    (μονοπάτι), το airlock A2 από το A1 και το A3 από το A2 (σύνδεση εδάφους,
    το κοντινότερο τη στιγμή που μπήκαν). Γκρεμίζεται το A1: το μονοπάτι του S1
    φεύγει, του S2 μένει· ο S1 και το A2 κρέμονται πια από το σκάφος, το A3
    μένει στο A2 — και το κοντινότερο airlock του A2 θα ήταν το A3, που κρέμεται
    από αυτό. Ολοι φτάνουν ως το σκάφος. Μετά γκρεμίζεται ο S1: ο S2 κρέμεται
    από το σκάφος, εκεί που κρεμόταν ο S1."""
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G, F = D.game(sym, g, patch, TG.SNA)
    G.run(500_000)
    G.settle()
    sh = tile(D.centre(G, 64))
    at, _ = find_spot(G, sym, AIRLOCK, lambda r, a: True, (sh[0] + 9, sh[1]))
    G.camera(sh[0] - 3, sh[1] - 6)
    a1 = place(G, sym, g, AIRLOCK, at)
    if not a1 or own(G, a1) != 64 | LKG:
        return f"ΑΓΚΥΡΑ: το A1 {a1}: LK_OWN #{own(G, a1 or 64):02X}, όχι σύνδεση εδάφους ως το σκάφος"
    c1 = tile(at)
    at, _ = find_spot(G, sym, SOLAR, path_to(a1, None, 3), (c1[0] + 1, c1[1] - 5))
    s1 = at and place(G, sym, g, SOLAR, at)
    at, _ = find_spot(G, sym, SOLAR, path_to(s1, None, 2), (tile(at)[0] + 5, tile(at)[1] - 1))
    s2 = at and place(G, sym, g, SOLAR, at)
    at, _ = find_spot(G, sym, AIRLOCK, anchor_is(G, a1), (c1[0] + 5, c1[1] + 3))
    a2 = at and place(G, sym, g, AIRLOCK, at)
    at, _ = find_spot(G, sym, AIRLOCK, anchor_is(G, a2), (tile(at)[0] + 5, tile(at)[1] + 1))
    a3 = at and place(G, sym, g, AIRLOCK, at)
    if not (s1 and s2 and a2 and a3):
        return f"ΑΓΚΥΡΑ: η σκηνή δεν στήθηκε: S1 {s1}, S2 {s2}, A2 {a2}, A3 {a3}"
    if own(G, a2) != a1 | LKG or own(G, a3) != a2 | LKG:
        return (f"ΑΓΚΥΡΑ: A2 {a2} #{own(G, a2):02X}, A3 {a3} #{own(G, a3):02X}: η σκηνή "
                f"θέλει το A2 στο A1 και το A3 στο A2")
    G.run(3_000_000)
    G.settle()
    if not quiet:
        shot(G, "unlink_before.png")
    s = snap_at(G, a1)
    s2path = path_tiles(s["recs"], s2, s["owns"][s2])
    # Το κοντινότερο airlock του A2 χωρίς το A1: αυτό θα διάλεγε το lk_ground.
    domes, structs, dims = [list(t) for t in s["recs"][0]], [list(t) for t in s["recs"][1]], 0
    structs[a1 - 64][4] = 0
    near = reach.anchor(structs, s["deg"], a2, structs[a2 - 64][0], structs[a2 - 64][1])
    err, worst = gone_at(G, F, s, a1, "ΑΓΚΥΡΑ")
    if err:
        return err
    w = world(G)
    if not all(w[reach.widx(x, y)] & 0x37 == 7 for x, y in s2path):
        return f"ΑΓΚΥΡΑ: το μονοπάτι του S2 {s2} (ως τον S1) δεν έμεινε θεμέλιο"
    if [own(G, n) for n in (s1, a2, a3)] != [64 | LKG, 64 | LKG, a2 | LKG]:
        return (f"ΑΓΚΥΡΑ: S1 #{own(G, s1):02X}, A2 #{own(G, a2):02X}, A3 #{own(G, a3):02X}: "
                f"η πρόζα λέει το σκάφος, το σκάφος, το A2")
    if not quiet:
        WORST["το airlock A1, δύο ξαναδεμένοι"] = worst
        shot(G, "unlink_after.png")
    G.run(3_000_000)
    G.settle()
    far = [n for n in (s1, s2, a2, a3) if dist(G, n, 64) == 255]
    if far:
        return f"ΑΓΚΥΡΑ: οι {far} δεν φτάνουν ως το σκάφος (DIST)"
    say(f"ΑΓΚΥΡΑ: το A1 {a1} έφυγε· η σύνδεση του S1 {s1} μαζί του, του S2 {s2} έμεινε· "
        f"ο S1 και το A2 {a2} κρέμονται πια από το σκάφος, το A3 {a3} από το A2 (το "
        f"κοντινότερο του A2 θα ήταν το {near})· όλοι φτάνουν ως το σκάφος· ο χειρότερος "
        f"γύρος {worst / MS:.1f} ms")
    s = snap_at(G, s1)
    err, worst = gone_at(G, F, s, s1, "ΑΓΚΥΡΑ, ο S1")
    if err:
        return err
    if own(G, s2) != 64 | LKG:
        return f"ΑΓΚΥΡΑ: ο S2 {s2} δεν κρέμεται από το σκάφος: LK_OWN #{own(G, s2):02X}"
    if not quiet:
        WORST["ο ηλιακός S1, ένας ξαναδεμένος"] = worst
    say(f"ΑΓΚΥΡΑ: μετά ο S1 {s1}: η σύνδεση του S2 {s2} έφυγε, και ο S2 κρέμεται από το "
        f"σκάφος· ο χειρότερος γύρος {worst / MS:.1f} ms")
    return None


def orphan(sym, g, patch=(), quiet=False):
    """ΧΩΡΙΣ ΓΟΝΙΟ, στην αποικία δοκιμών: το airlock 65 της δεν κρέμεται από
    πουθενά (η αποικία δεν έχει σκάφος, και το colony.asm δεν γράφει LK_OWN).
    Δύο airlock με σύνδεση εδάφους ως αυτό· όταν φεύγει, μένουν χωρίς σύνδεση,
    όπως ως το βήμα 101, και καμία ακμή δεν γίνεται."""
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G, F = D.game(sym, g, patch)
    G.run(500_000)
    G.settle()
    out = []
    for dx, dy in ((7, 3), (-7, 3)):
        c = tile(D.centre(G, 1 if dx > 0 else 2))
        at, _ = find_spot(G, sym, AIRLOCK,
                          lambda r, a: bool(r["corridors"]) and anchor_is(G, 65)(r, a),
                          (c[0] + dx, c[1] + dy))
        n = at and place(G, sym, g, AIRLOCK, at)
        if not n or own(G, n) != 65 | LKG:
            return f"ΧΩΡΙΣ ΓΟΝΙΟ: το airlock {n} στο {at}: LK_OWN #{own(G, n or 64):02X}, όχι ως το 65"
        out.append(n)
    c = tile(D.centre(G, 65))
    G.camera(c[0] - 10, c[1] - 4)
    s = snap_at(G, 65)
    if 65 in s["owns"]:
        return f"ΧΩΡΙΣ ΓΟΝΙΟ: το 65 της αποικίας έχει LK_OWN #{s['owns'][65]:02X}"
    err, _ = gone_at(G, F, s, 65, "ΧΩΡΙΣ ΓΟΝΙΟ")
    if err:
        return err
    if any(own(G, n) for n in out) or any(D.deg(G, n) != s["deg"][n] - s["adj"][65].count(n)
                                          for n in out):
        return (f"ΧΩΡΙΣ ΓΟΝΙΟ: LK_OWN {[own(G, n) for n in out]}, βαθμοί "
                f"{[D.deg(G, n) for n in out]} (πριν {[s['deg'][n] for n in out]})")
    say(f"ΧΩΡΙΣ ΓΟΝΙΟ: το 65 έφυγε· τα {out} έμειναν χωρίς σύνδεση και χωρίς νέα ακμή")
    return None


def saved(sym, g):
    """Τα LK_OWN σώζονται με τον γράφο (SV_STATE, 2 KB κάτω από το
    G_hud_shadow), και το game_new τα μηδενίζει μαζί με το node_deg."""
    lo = L["G_hud_shadow"] - 2048
    a = L["G_rt_nodes"] + 96
    if not (lo <= a and a + 32 <= L["G_hud_shadow"]):
        return f"ΣΩΖΕΤΑΙ: το LK_OWN #{a:04X} έξω από το SV_STATE #{lo:04X}-#{L['G_hud_shadow']:04X}"
    G, F = D.game(sym, g, (), TG.SNA)
    if owns(G):
        return f"ΣΩΖΕΤΑΙ: νέο παιχνίδι με LK_OWN {owns(G)}"
    print(f"    ΣΩΖΕΤΑΙ: LK_OWN στο #{a:04X}-#{a + 31:04X}, μέσα στο SV_STATE "
          f"#{lo:04X}-#{L['G_hud_shadow'] - 1:04X}· νέο παιχνίδι: όλα μηδέν")
    return None


# --------------------------------------------------------------------------
# ΑΡΝΗΤΙΚΑ
# --------------------------------------------------------------------------
def negatives(sym, g):
    G, _ = D.game(sym, g)
    w = lambda a: [a & 255, a >> 8]
    cd = lambda name: [0xCD] + w(sym[name])
    nop3 = [(0, 0), (1, 0), (2, 0)]
    ovl = lambda *a, **k: D.at_ovl(sym, *a, **k)

    def ram(name, n, pat, edits):
        data = G.m.read_ram(sym[name], n)
        at = [k for k in range(n - len(pat) + 1) if list(data[k:k + len(pat)]) == pat]
        if len(at) != 1:
            return None
        return [("ram", sym[name] + at[0] + d, v) for d, v in edits]

    return [
        # ld a,(al_po) στο lk_keepp γίνεται xor a: το LK_OWN πάντα «πρώτα κατά x»
        ("πάντα πρώτα κατά x", ram("LK_KEEPP", 8, [0x3A] + w(sym["AL_PO"]),
                                   [(0, 0xAF), (1, 0), (2, 0)]), kept),
        ("τίποτα δεν κρατιέται", ram("LK_KEEP", 8, [0x77, 0xC3], [(0, 0)]), kept),
        ("η σύνδεση εδάφους σαν μονοπάτι", ram("LK_GROUND", 24, [0xF6, LKG], [(1, 0)]), kept),
        ("μόνο το δικό του μονοπάτι", ovl("DMP_LP", 30, [0xB8, 0x20], [(1, 0x18)]), anchor_gone),
        ("κανένα ξαναδέσιμο", ovl("DMV_LP", 40, cd("DM_RELINK"), nop3), anchor_gone),
        ("χωρίς γονιό, δένεται κάπου", ovl("DML_LP", 24, cd("DM_UP") + [0x30], [(3, 0), (4, 0)]), orphan),
        ("τα σκέλη δεν ζωγραφίζονται", ovl("DMV_LEG", 4, [0x2A], [(0, 0xC9)]), anchor_gone),
    ]


def main():
    sym, g = TG.build()
    err = saved(sym, g)
    check(err is None, err or "ΣΩΖΕΤΑΙ: με τον γράφο, μηδέν σε νέο παιχνίδι")
    for fn, what in ((kept, "ΚΡΑΤΙΕΤΑΙ: το Γ και η άκρη κάθε σύνδεσης, τίποτα για θόλο"),
                     (mine, "ΔΙΚΟ ΤΟΥ: η σύνδεση φεύγει, το μονοπάτι μένει θεμέλιο, χτίζεται πάλι"),
                     (anchor_gone, "ΑΓΚΥΡΑ: φεύγουν όσα τελείωναν εκεί, κρέμονται από τον γονιό, ως το σκάφος"),
                     (orphan, "ΧΩΡΙΣ ΓΟΝΙΟ: μένουν χωρίς σύνδεση, καμία ακμή")):
        try:
            err = fn(sym, g)
        except AssertionError as e:
            err = f"assert: {e}"
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
        except Exception as e:                           # ένα πείραγμα μπορεί να ρίξει και τη σκηνή
            err = f"{type(e).__name__}: {e}"
        check(err is not None, f"ΑΡΝΗΤΙΚΟ «{label}»: {err or 'ΔΕΝ ΠΙΑΣΤΗΚΕ'}")
    if FAIL:
        print(f"\n{len(FAIL)} ΑΠΟΤΥΧΙΕΣ")
        sys.exit(1)
    print("\nΟΛΑ ΚΑΛΑ")


if __name__ == "__main__":
    main()
