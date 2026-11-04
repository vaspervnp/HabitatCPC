#!/usr/bin/env python3
"""Τα κιβώτια του σκάφους (βήμα 181, DESIGN §10.1, src/crates.asm).

Η πρόζα — οι αποφάσεις του παίκτη (AskUserQuestion, 2026-11-04): 150 μέταλλο
και 100 βιοπλαστικό, το αμπάρι μένει, μόνο με airlock και αποθήκη, σωρός στη
θέση του που ζει 10 sol.

  ΚΑΝΟΝΑΣ    το σκάφος γκρεμίζεται μόνο με ένα airlock έτοιμο και έναν θόλο
             αποθήκης σε λειτουργία. Αλλιώς το D βουίζει και ανοίγει στο
             κόκκινο DEMOLISH, το FIRE δεν κάνει τίποτα, και η σειρά 4 λέει τι
             λείπει: NEEDS AIRLOCK, NEEDS STORAGE, NEEDS AIRLOCK + STORAGE. Με
             τα δύο λέει τι αφήνει: LEAVES 150 FE + 100 BI FOR 10 SOLS. Τα
             κιβώτια δεν γκρεμίζονται: το D βουίζει και μένει εκεί που ήταν.
  ΚΙΒΩΤΙΑ    στο FIRE η δομή 0 γίνεται κιβώτια στην ίδια εγγραφή: K_CRATES, το
             πλαίσιο του σκάφους (CR_BOX), ακεραιότητα 255, η λήξη στο sol + 10
             (& 63), ο σωρός 250 — και μία Haul για τον κόμβο 64, J_SITE ο ίδιος.
             Ο κόμβος, οι ακμές, οι κάτοχοι, η κατοχή του κόσμου και τα
             αποθέματα ίδια· η οθόνη όση η πλήρης σχεδίαση, με τα κιβώτια εκεί
             που ήταν το σκάφος. Το I πάνω τους: CRATES    FE 150 BI 100 10 SOL.
  ΦΟΡΤΙΟ     όπως από ορυχείο, 10 το ταξίδι, προς την αποθήκη: μέταλλο όσο ο
             σωρός που μένει είναι από 100 και πάνω, μετά βιοπλαστικό. Το αγαθό
             στο J_SITE (#80 | απόθεμα) και στο spare, και αμέσως η επόμενη Haul.
             Χωρίς αποθήκη που να φτάνεται, παραδίδεται εκεί, με το αγαθό του,
             και Haul δεν μπαίνει ως το επόμενο sol.
  ΠΑΡΑΔΟΣΗ   στην αποθήκη +10 του αγαθού, «φτιάχτηκε εδώ», spare 0· ένα φορτίο
             που ένας άφησε στη μέση το παραδίδει ο επόμενος, με το ίδιο αγαθό·
             μια αποθήκη που γκρεμίζεται με ένα φορτίο καθ' οδόν το παίρνει
             στα αποθέματα, και η εργασία κλείνει αντί να γυρίσει στο J_SITE.
  ΤΕΛΟΣ      το τελευταίο φορτίο, ή το sol της λήξης με ό,τι μένει να χάνεται:
             CR_GONE, τα 2x2 tiles χωρίς κατοχή, ο κόμβος και οι ακμές του
             μένουν. Ενα άλλο sol: μια Haul αν δεν υπήρχε, και τίποτα άλλο.
  ΜΕΤΕΩΡΙΤΗΣ μια κρούση στα κιβώτια δεν αλλάζει τίποτα: δεν είναι κτίριο, όπως
             το σκάφος.
  ΟΛΟ        στο παιχνίδι που τρέχει, από το FIRE: 150 μέταλλο και 100
             βιοπλαστικό φτάνουν στην αποθήκη, και τα κιβώτια φεύγουν· η οθόνη
             όση η πλήρης σχεδίαση, χωρίς αυτά.

Στην αποικία δοκιμών, με την πλατφόρμα σκάφος όπως στο tests/test_haul.py: στη
θέση της και με την κατοχή του σκάφους, τα 2x2 tiles του κέντρου της.

Αρνητικά, με τον κώδικα πειραγμένο στη μνήμη: μόνο μέταλλο· το αγαθό που δεν
γράφεται στο J_SITE· καμία επόμενη Haul· η παράδοση ως μετάλλευμα· η κατοχή που
δεν σβήνει· η λήξη που δεν έρχεται· το sol και χωρίς κιβώτια· ο μετεωρίτης που
χτυπά τα κιβώτια· το σκάφος πάντα
γκρεμίσιμο· ο σωρός που δεν γράφεται· η εργασία που γυρίζει στο J_SITE ενός
φορτίου.
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import test_haul as TH                                   # noqa: E402
import test_demolish as TDm                              # noqa: E402
import test_fit as TF                                    # noqa: E402
import test_outside as TO                                # noqa: E402
import graph as GR                                       # noqa: E402
import hudread                                           # noqa: E402
import econ as EC                                        # noqa: E402
import ovmap as OV                                       # noqa: E402
import cpc                                               # noqa: E402

FAIL = []


def check(ok, msg):
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ ") + msg)
    if not ok:
        FAIL.append(msg)


def consts():
    """Οι σταθερές του src/const.asm, όπως τις βλέπει ο assembler."""
    src = open(os.path.join(ROOT, "src", "const.asm"), encoding="utf-8").read()
    out = {}
    for n in ("K_CRATES", "CR_BOX", "CR_GONE", "CR_BIO", "CR_SOLS", "CR_SMASK",
              "K_SHIP", "K_PAD", "K_AIRLOCK", "R_STORAGE"):
        m = re.search(rf"^{n}\s+equ\s+(\d+)", src, re.M)
        out[n] = int(m.group(1))
    m = re.search(r"^CR_PILE\s+equ\s+(\d+)\s*\+\s*(\d+)", src, re.M)
    out["CR_PILE"] = int(m.group(1)) + int(m.group(2))
    return out


C = consts()
K_CRATES, CR_BOX, CR_GONE = C["K_CRATES"], C["CR_BOX"], C["CR_GONE"]
CR_PILE, CR_BIO, CR_SOLS, CR_SMASK = C["CR_PILE"], C["CR_BIO"], C["CR_SOLS"], C["CR_SMASK"]
K_SHIP, K_PAD, K_AIRLOCK, R_STORAGE = C["K_SHIP"], C["K_PAD"], C["K_AIRLOCK"], C["R_STORAGE"]
S_METAL, S_BIOPL, S_ORE = EC.S_METAL, EC.S_BIOPL, EC.S_ORE
J_HAUL = EC.J_HAUL
BIT = 0x40                                              # ST_HAUL
DS_BUILDING, DS_ACTIVE = 1, 2
SOL = 51                                                # EC_SOL μέσα στο econ_state
PRODM = 68
L = TO.layout()
SHIP = 64
WHO = 1                                                 # ο δεύτερος εργάτης


# --------------------------------------------------------------------------
# η αποικία δοκιμών με σκάφος
# --------------------------------------------------------------------------
def ship_tiles(cx, cy):
    """Τα 2x2 tiles του πλαισίου του σκάφους (al_node: (c - 2) / 2)."""
    x0, y0 = (TDm.sb(cx) - 2) >> 1, (TDm.sb(cy) - 2) >> 1
    return [(x0 + dx, y0 + dy) for dy in (0, 1) for dx in (0, 1)]


def pad_tiles(cx, cy):
    x0, y0 = (TDm.sb(cx) - 4) >> 1, (TDm.sb(cy) - 4) >> 1
    return [(x0 + dx, y0 + dy) for dy in range(4) for dx in range(4)]


def bank(G, n):
    return cpc._lib.cpcemu_ram_ptr(G.m._h, n)


def same(t):
    """Ο γλύφος του 0 και του O είναι ο ίδιος (tests/hudread.py)."""
    return t.replace("O", "0")


def w_at(x, y):
    """Το byte του tile (x, y) στην τράπεζα 4 (tile_addr)."""
    return (y + 64) * 128 + x + 64


def as_ship(b4, b6, storage=True, ready=True):
    """Η πλατφόρμα της αποικίας σκάφος, με την κατοχή του (ng_ship): τα 2x2
    του κέντρου της. Ο θόλος 1 αποθήκη αν storage· το airlock (δομή 1) εργοτάξιο
    αν όχι ready."""
    st = L["G_struct_tbl"] - 0x4000
    cx, cy = b6[st], b6[st + 1]
    b6[st + 2], b6[st + 3] = K_SHIP, 0
    for x, y in pad_tiles(cx, cy):
        b4[w_at(x, y)] &= ~0x10
    for x, y in ship_tiles(cx, cy):
        b4[w_at(x, y)] |= 0x10
    b6[st + 8 + 4] = DS_ACTIVE if ready else DS_BUILDING
    if storage:
        b6[L["G_dome_tbl"] - 0x4000 + 24 * 1 + 3] = R_STORAGE
    return cx, cy


def storages(m, d):
    m.poke(L["G_room_n"] + R_STORAGE, 1 if d is not None else 0)
    if d is not None:
        m.poke(L["G_room_list"] + R_STORAGE * EC.ROOM_MAX, d)


# --------------------------------------------------------------------------
# ΚΑΝΟΝΑΣ και ΚΙΒΩΤΙΑ — στο παιχνίδι, με τον κέρσορα, M, D, FIRE
# --------------------------------------------------------------------------
def ui(sym, g, patch=(), storage=True, ready=True, crates=False, pause=False):
    """M και D πάνω στο σκάφος (ή στα κιβώτια): (ac_fit, η σειρά 4, G, F). Με
    pause, πρώτα το 1: ο τροχός σταματά, το UI όχι."""
    G, F = TDm.game(sym, g, patch)
    F.set_stocks(200, 200)
    b4, b6 = G.bank(4), G.bank(6)
    cx, cy = as_ship(b4, b6, storage, ready)
    st = L["G_struct_tbl"] - 0x4000
    if crates:
        for k, v in enumerate([K_CRATES, CR_BOX, DS_ACTIVE, 255, 0, CR_PILE]):
            b6[st + 2 + k] = v
    G.run(1_000_000)
    G.settle()
    at = TDm.centre(G, SHIP)
    G.camera((at[0] >> 1) - 10, (at[1] >> 1) - 5)
    F.look()
    if pause:
        F.key("1")
    G.m.poke(sym["CUR_HX"], at[0] & 0xFF)
    G.m.poke(sym["CUR_HY"], at[1] & 0xFF)
    F.key("M")
    fit = F.peek("AC_FIT")
    F.key("D")
    return fit, hudread.text(G.m, sym, 4).rstrip(), G, F


def rule(sym, g, patch=(), quiet=False):
    """ΚΑΝΟΝΑΣ. Η πρώτη διαφορά, ή None."""
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    cases = [("airlock και αποθήκη", dict(), True, "LEAVES 150 FE + 100 BI FOR 10 SOLS"),
             ("χωρίς αποθήκη", dict(storage=False), False, "NEEDS STORAGE"),
             ("με το airlock εργοτάξιο", dict(ready=False), False, "NEEDS AIRLOCK"),
             ("χωρίς τα δύο", dict(storage=False, ready=False), False, "NEEDS AIRLOCK + STORAGE"),
             ("τα κιβώτια", dict(crates=True), False, "WHAT IS HERE")]
    for what, kw, can, line in cases:
        fit, row4, G, F = ui(sym, g, patch, **kw)
        if bool(fit & TDm.AF_DEMO) != can or not same(row4).startswith(same(line)):
            return (f"ΚΑΝΟΝΑΣ ({what}): DEMOLISH {'ναι' if fit & TDm.AF_DEMO else 'όχι'}, "
                    f"σειρά 4 «{row4}» — η πρόζα λέει {'ναι' if can else 'όχι'}, «{line}»")
        if not can:
            before = TDm.struct(G, SHIP)
            F.fire()
            G.settle()
            if TDm.struct(G, SHIP) != before:
                return f"ΚΑΝΟΝΑΣ ({what}): το FIRE άλλαξε τη δομή 0: {before} -> {TDm.struct(G, SHIP)}"
    say("ΚΑΝΟΝΑΣ: με airlock και αποθήκη το DEMOLISH ανοίγει και λέει τι αφήνει· χωρίς "
        "αποθήκη, με το airlock εργοτάξιο, χωρίς τα δύο, κόκκινο με αυτό που λείπει, και "
        "το FIRE δεν αλλάζει τίποτα· τα κιβώτια κόκκινα")
    return None


def convert(sym, g, patch=(), quiet=False):
    """ΚΙΒΩΤΙΑ. Η πρώτη διαφορά, ή None."""
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    fit, row4, G, F = ui(sym, g, patch, pause=True)    # κανείς δεν φορτώνει ακόμη
    m = G.m
    sol = m.peek(g + SOL)
    before = (TDm.struct(G, SHIP), TDm.adj(G, SHIP), TDm.standing(G, SHIP), F.stocks(),
              bytes(G.bank(4)[0:16384]))
    owners = [G.m.peek(L["G_node_adj"] + 768 + 128 + k) for k in range(EC.MAX_STRUCT)]
    F.fire()
    G.run(3_000_000, until=lambda: m.peek(sym["DIRTY_NUM"]) == 0)
    G.settle()
    r = TDm.struct(G, SHIP)
    want = before[0][:2] + [K_CRATES, CR_BOX, DS_ACTIVE, 255,
                            ((sol + CR_SOLS) & CR_SMASK) | BIT, CR_PILE]
    if r != want:
        return f"ΚΙΒΩΤΙΑ: η εγγραφή {r} — η πρόζα λέει {want}"
    hauls = [list(j[1:]) for j in TDm.jobs(G) if j[1] == J_HAUL and j[5] == SHIP]
    if hauls != [[J_HAUL, SHIP, 255, 5, SHIP]]:
        return f"ΚΙΒΩΤΙΑ: οι Haul των κιβωτίων {hauls} — η πρόζα λέει μία, για τον κόμβο 64"
    owners1 = [G.m.peek(L["G_node_adj"] + 768 + 128 + k) for k in range(EC.MAX_STRUCT)]
    now = (TDm.adj(G, SHIP), F.stocks(), bytes(G.bank(4)[0:16384]))
    if now != (before[1], before[3], before[4]) or owners1 != owners:
        return (f"ΚΙΒΩΤΙΑ: ακμές {before[1]} -> {now[0]}, αποθέματα {before[3]} -> {now[1]}, "
                f"ο κόσμος {'ίδιος' if now[2] == before[4] else 'άλλος'}, τα LK_OWN "
                f"{'ίδια' if owners1 == owners else 'άλλα'} — η πρόζα λέει όλα ίδια")
    ok = TDm.truth(G)
    if not ok[0]:
        return "ΚΙΒΩΤΙΑ: οθόνη/πλήρης σχεδίαση: " + ok[1]
    F.look()
    at = TDm.centre(G, SHIP)
    G.m.poke(sym["CUR_HX"], at[0] & 0xFF)
    G.m.poke(sym["CUR_HY"], at[1] & 0xFF)
    F.key("I")
    row3 = hudread.text(G.m, sym, 3)[:35].rstrip()
    want3 = f"CRATES    FE 150 BI 100 {CR_SOLS:2d} SOL"
    if same(row3) != same(want3):
        return f"ΚΙΒΩΤΙΑ: το I λέει «{row3}» — η πρόζα λέει «{want3}»"
    say(f"ΚΙΒΩΤΙΑ: η δομή 0 {r}, μία Haul για τον κόμβο 64· ακμές, LK_OWN, κόσμος και "
        f"αποθέματα ίδια, η οθόνη όση η πλήρης σχεδίαση, το I «{row3}»")
    return None


# --------------------------------------------------------------------------
# ΦΟΡΤΙΟ, ΠΑΡΑΔΟΣΗ — η θέση 13 με μια Haul στα κιβώτια και στην αποθήκη
# --------------------------------------------------------------------------
def near_dome(G):
    """Ο θόλος της αποικίας που φτάνεται από τον κόμβο 64, ο κοντινότερος."""
    b1 = cpc._lib.cpcemu_ram_ptr(G.m._h, 1)
    by = sorted((b1[GR.zd_off(SHIP, d)], d) for d in range(EC.MAX_DOME)
                if 0 < b1[GR.zd_off(SHIP, d)] < 255)
    return by[0][1]


def scene(sym, patch=(), pile=CR_PILE, carry=None, store=True, alive=True, expiry=0):
    """Τα κιβώτια στη δομή 0 και ο εργάτης WHO με μια Haul: στα κιβώτια, ή με
    carry (το αγαθό) στην αποθήκη, τον κοντινότερο θόλο."""
    G = TH.Game(sym, patch)
    rec = G.rec(0)
    G.put_rec(0, rec[:2] + [K_CRATES, CR_BOX, DS_ACTIVE, 255, expiry, pile])
    d = near_dome(G)
    storages(G.m, d if store else None)
    j = G.free_job()
    at = SHIP if carry is None else d
    G.put_job(j, [J_HAUL, at, WHO, 5, SHIP if carry is None else 0x80 | carry])
    G.ag_set(WHO, flags=TH.F_ALIVE if alive else 0, node=at, dest=at, edge=255, task=j,
             spare=carry or 0)
    for k in (S_METAL, S_BIOPL, S_ORE):
        G.s16(G.g + 2 * k, 100)
    G.m.poke(G.g + PRODM, 0)
    return G, j, d


def stocks(G):
    return tuple(G.w16(G.g + 2 * k) for k in (S_METAL, S_BIOPL, S_ORE))


def crates_hauls(G, j):
    return [list(G.jobs()[5 * k:5 * k + 5]) for k in range(32)
            if k != j and G.jobs()[5 * k] == J_HAUL and G.jobs()[5 * k + 4] == SHIP]


def loads(sym, patch=(), quiet=False):
    """ΦΟΡΤΙΟ και ΠΑΡΑΔΟΣΗ. Η πρώτη διαφορά, ή None."""
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    # στα κιβώτια: ο σωρός πριν, το αγαθό, ο σωρός μετά
    for pile, good in ((CR_PILE, S_METAL), (CR_BIO + 10, S_METAL), (CR_BIO, S_BIOPL),
                       (20, S_BIOPL)):
        G, j, d = scene(sym, patch, pile=pile)
        G.call("JOBS_TICK")
        got = (G.job(j), G.rec(0)[TH.ST_OWED], G.ag_get(WHO, "spare"), G.ag_get(WHO, "dest"),
               crates_hauls(G, j), G.rec(0)[TH.ST_OPS] & BIT, stocks(G))
        want = ([J_HAUL, d, WHO, 5, 0x80 | good], pile - 10, good, d,
                [[J_HAUL, SHIP, 255, 5, SHIP]], BIT, (100, 100, 100))
        if got != want:
            return (f"ΦΟΡΤΙΟ από σωρό {pile}: εργασία {got[0]}, σωρός {got[1]}, spare {got[2]}, "
                    f"dest {got[3]}, νέες Haul {got[4]}, bit {got[5]:#x}, αποθέματα {got[6]} — "
                    f"η πρόζα λέει {want}")
    say(f"ΦΟΡΤΙΟ: από 250 και 110 μέταλλο, από 100 και 20 βιοπλαστικό, 10 λιγότερα στον "
        f"σωρό, το αγαθό στο J_SITE και στο spare, προς την αποθήκη, και αμέσως η επόμενη Haul")
    # χωρίς αποθήκη που να φτάνεται: εκεί, με το αγαθό του, και καμία Haul
    G, j, d = scene(sym, patch, store=False)
    G.call("JOBS_TICK")
    got = (G.job(j)[0], G.rec(0)[TH.ST_OWED], G.rec(0)[TH.ST_OPS] & BIT, crates_hauls(G, j),
           stocks(G), G.m.peek(G.g + PRODM) & (1 << S_METAL), G.ag_get(WHO, "spare"))
    want = (255, CR_PILE - 10, 0, [], (110, 100, 100), 1 << S_METAL, 0)
    if got != want:
        return f"ΦΟΡΤΙΟ ΧΩΡΙΣ ΑΠΟΘΗΚΗ: {got} — η πρόζα λέει {want}"
    # στην αποθήκη: μέταλλο, βιοπλαστικό
    for good in (S_METAL, S_BIOPL):
        G, j, d = scene(sym, patch, carry=good)
        G.call("JOBS_TICK")
        want_s = tuple(110 if k == good else 100 for k in (S_METAL, S_BIOPL, S_ORE))
        got = (G.job(j)[0], stocks(G), G.m.peek(G.g + PRODM) & (1 << good),
               G.ag_get(WHO, "spare"), G.rec(0)[TH.ST_OWED])
        want = (255, want_s, 1 << good, 0, CR_PILE)
        if got != want:
            return f"ΠΑΡΑΔΟΣΗ ({'μέταλλο' if good == S_METAL else 'βιοπλαστικό'}): {got} — η πρόζα λέει {want}"
    # στη μέση: ο φορτωμένος πέθανε, ο επόμενος βρίσκει το ίδιο αγαθό
    G, j, d = scene(sym, patch, carry=S_BIOPL, alive=False)
    G.ag_set(WHO, node=100)
    G.call("JOBS_TICK")
    if G.job(j)[0:2] != [J_HAUL, d] or G.job(j)[4] != 0x80 | S_BIOPL:
        return (f"ΣΤΗ ΜΕΣΗ: η εργασία {G.job(j)} — η πρόζα λέει μένει προς την αποθήκη {d} "
                f"με το βιοπλαστικό")
    say("ΠΑΡΑΔΟΣΗ: χωρίς αποθήκη το φορτίο μένει εκεί, μέταλλο, χωρίς Haul· στην αποθήκη "
        "+10 μέταλλο ή βιοπλαστικό, «φτιάχτηκε εδώ», spare 0· ένα αφημένο στη μέση μένει "
        "προς την αποθήκη με το αγαθό του")
    return None


# --------------------------------------------------------------------------
# ΤΕΛΟΣ — το τελευταίο φορτίο, και το sol
# --------------------------------------------------------------------------
def occupied(G, cx, cy):
    b4 = bank(G, 4)
    return [b4[w_at(x, y)] & 0x10 for x, y in ship_tiles(cx, cy)]


def day(G):
    """Το sol των κιβωτίων όπως το τρέχει το ev_after (src/econ.asm), μετά το
    sol_rollover: τα bytes του παιχνιδιού από το eva_cr ως το eva_bot, ως probe."""
    a, b = G.sym["EVA_CR"], G.sym["EVA_BOT"]
    return G.probe(list(G.m.read_ram(a, b - a)))


def gone(sym, patch=(), quiet=False):
    """ΤΕΛΟΣ. Η πρώτη διαφορά, ή None."""
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    # το τελευταίο φορτίο: φεύγουν
    G, j, d = scene(sym, patch, pile=10)
    cx, cy = G.rec(0)[0], G.rec(0)[1]
    b4 = bank(G, 4)
    for x, y in ship_tiles(cx, cy):
        b4[w_at(x, y)] |= 0x10
    w0 = bytes(b4[0:16384])
    edges = TDm.adj(G, SHIP)
    G.call("JOBS_TICK")
    w1 = bytes(b4[0:16384])
    moved = [k for k in range(16384) if w0[k] != w1[k]]
    want_moved = sorted(w_at(x, y) for x, y in ship_tiles(cx, cy))
    got = (G.rec(0)[2:4], G.rec(0)[TH.ST_OWED], crates_hauls(G, j), occupied(G, cx, cy),
           moved, TDm.adj(G, SHIP), G.job(j)[4])
    want = ([K_CRATES, CR_GONE], 0, [], [0, 0, 0, 0], want_moved, edges, 0x80 | S_BIOPL)
    if got != want:
        return (f"ΤΕΛΟΣ (το τελευταίο φορτίο): είδος/μέγεθος {got[0]}, σωρός {got[1]}, Haul "
                f"{got[2]}, κατοχή {got[3]}, άλλαξαν {len(got[4])} bytes του κόσμου, ακμές "
                f"{got[5]}, J_SITE {got[6]:#x} — η πρόζα λέει {want[0]}, 0, καμία, χωρίς κατοχή "
                f"τα 4 tiles και μόνο αυτά, οι ακμές {edges}, βιοπλαστικό")
    # το sol: η λήξη, και ένα άλλο sol
    for when, expiry, pile, want_r, want_h in (
            ("η λήξη", 5, 120, [K_CRATES, CR_GONE, 0], []),
            ("ένα άλλο sol", 9, 120, [K_CRATES, CR_BOX, 120], [[J_HAUL, SHIP, 255, 5, SHIP]])):
        G, j, d = scene(sym, patch, pile=pile, expiry=expiry)
        G.put_job(j, [255] * 5)
        G.ag_set(WHO, task=255)
        G.m.poke(G.g + SOL, 64 + 5)             # το sol 69: & 63 = 5
        day(G)
        r = G.rec(0)
        got = ([r[2], r[3], r[TH.ST_OWED]], crates_hauls(G, None))
        if got != (want_r, want_h):
            return (f"ΤΕΛΟΣ ({when}): είδος, μέγεθος, σωρός {got[0]}, Haul {got[1]} — η πρόζα "
                    f"λέει {want_r}, {want_h}")
    # χωρίς κιβώτια (η πλατφόρμα) και αφού έφυγαν: τίποτα
    for what, kind, size in (("η πλατφόρμα", K_PAD, 0), ("έφυγαν", K_CRATES, CR_GONE)):
        G = TH.Game(sym, patch)
        G.put_rec(0, G.rec(0)[:2] + [kind, size, DS_ACTIVE, 255, 5, 120])
        G.m.poke(G.g + SOL, 5)
        jobs0, r0 = G.jobs(), G.rec(0)
        day(G)
        if (G.jobs(), G.rec(0)) != (jobs0, r0):
            return f"ΤΕΛΟΣ ({what}): το sol άλλαξε κάτι: {r0} -> {G.rec(0)}"
    say("ΤΕΛΟΣ: με το τελευταίο φορτίο φεύγουν — CR_GONE, τα 2x2 tiles χωρίς κατοχή και "
        "τίποτε άλλο, οι ακμές ίδιες· στο sol της λήξης ό,τι μένει χάνεται· ένα άλλο sol "
        "βάζει την Haul που έλειπε· η πλατφόρμα και ό,τι έφυγε δεν αλλάζουν")
    return None


# --------------------------------------------------------------------------
# ΜΕΤΕΩΡΙΤΗΣ — μια κρούση στα κιβώτια (mt_hit, src/meteor.asm)
# --------------------------------------------------------------------------
def meteor(sym, patch=(), quiet=False, patch6=()):
    """ΜΕΤΕΩΡΙΤΗΣ: τα κιβώτια δεν είναι κτίριο, όπως το σκάφος — καμία αλλαγή, καμία
    εργασία. Το patch6 στον κώδικα της τράπεζας 6 (mth_struct). Η πρώτη διαφορά, ή
    None."""
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G, j, d = scene(sym, patch)
    for at, v in patch6:
        G.b6[at - 0x4000] = v
    r0, jobs0 = G.rec(0), G.jobs()
    rec, hit = L["G_struct_tbl"], sym["MT_HIT"]
    # mt_hit: HL = η εγγραφή, A - D = ο κόμβος
    t = G.probe([0x21, rec & 255, rec >> 8, 0x3E, 96, 0x16, 96 - SHIP,
                 0xCD, hit & 255, hit >> 8])
    if t is None or (G.rec(0), G.jobs()) != (r0, jobs0):
        return (f"ΜΕΤΕΩΡΙΤΗΣ: μια κρούση στα κιβώτια: {r0} -> {G.rec(0)}, εργασίες "
                f"{jobs0} -> {G.jobs()} — η πρόζα λέει τίποτα")
    say("ΜΕΤΕΩΡΙΤΗΣ: μια κρούση στα κιβώτια δεν αλλάζει την εγγραφή ούτε τον πίνακα εργασιών")
    return None


# --------------------------------------------------------------------------
# Η ΑΠΟΘΗΚΗ ΓΚΡΕΜΙΖΕΤΑΙ με ένα φορτίο καθ' οδόν
# --------------------------------------------------------------------------
def store_goes(sym, g, patch=(), quiet=False):
    """Η ΑΠΟΘΗΚΗ ΓΚΡΕΜΙΖΕΤΑΙ: ο θόλος 1, αποθήκη, με ένα φορτίο βιοπλαστικού των
    κιβωτίων προς αυτόν, και χωρίς — τα μισά υλικά του θόλου και των μηχανών του
    είναι και στα δύο. Η πρώτη διαφορά, ή None."""
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    out = []
    for load in (False, True):
        G, F = TDm.game(sym, g, patch)
        F.set_stocks(200, 200)
        b6 = G.bank(6)
        as_ship(G.bank(4), b6)
        st = L["G_struct_tbl"] - 0x4000
        for k, v in enumerate([K_CRATES, CR_BOX, DS_ACTIVE, 255, 0, 100]):
            b6[st + 2 + k] = v
        G.run(1_000_000)
        G.settle()
        F.key("1")                              # παύση: κανείς δεν την παίρνει
        jt = L["G_job_tbl"]
        if load:
            j = [k for k in range(32) if G.m.peek(jt + 5 * k) == 255][0]
            G.m.write_ram(jt + 5 * j, bytes([J_HAUL, 1, 255, 5, 0x80 | S_BIOPL]))
        at = TDm.centre(G, 1)
        G.camera((at[0] >> 1) - 10, (at[1] >> 1) - 5)
        s0 = F.stocks()
        TDm.demolish(G, F, at)
        left = [J for J in TDm.jobs(G) if J[1] == J_HAUL and J[5] == 0x80 | S_BIOPL]
        out.append((F.stocks()[0] - s0[0], F.stocks()[1] - s0[1], left, TDm.struct(G, 65)[4]))
    (m0, b0, _, _), (m1, b1, left, _) = out
    if (m1, b1, left) != (m0, b0 + 10, []):
        return (f"Η ΑΠΟΘΗΚΗ ΓΚΡΕΜΙΖΕΤΑΙ: +{m1} μέταλλο, +{b1} βιοπλαστικό, η εργασία {left} — "
                f"η πρόζα λέει +{m0}, +{b0 + 10} (το φορτίο), και η εργασία κλείνει")
    say(f"Η ΑΠΟΘΗΚΗ ΓΚΡΕΜΙΖΕΤΑΙ: +{m1} μέταλλο, +{b1} βιοπλαστικό, 10 περισσότερα από το "
        f"ίδιο γκρέμισμα χωρίς το φορτίο, και η εργασία κλείνει")
    return None


# --------------------------------------------------------------------------
# ΟΛΟ — στο παιχνίδι που τρέχει
# --------------------------------------------------------------------------
def whole(sym, g, patch=(), quiet=False):
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    fit, row4, G, F = ui(sym, g, patch)
    m = G.m
    s0 = F.stocks()
    F.fire()
    t = 0
    # ως το CR_GONE, και ως το τέλος του τελευταίου φορτίου: φεύγουν όταν
    # φεύγει από τον σωρό, όχι όταν φτάνει
    carried = lambda: [j for j in TDm.jobs(G) if j[1] == J_HAUL and j[5] & 0x80]
    while (TDm.struct(G, SHIP)[3] != CR_GONE or carried()) and t < 400:
        G.run(1_000_000)
        t += 1
    G.run(3_000_000, until=lambda: m.peek(sym["DIRTY_NUM"]) == 0)
    G.settle()
    G.run(2_000_000)
    G.run(3_000_000, until=lambda: m.peek(sym["DIRTY_NUM"]) == 0)
    s1 = F.stocks()
    if TDm.struct(G, SHIP)[3] != CR_GONE or (s1[0] - s0[0], s1[1] - s0[1]) != (150, 100):
        return (f"ΟΛΟ: σε {t} s η δομή 0 {TDm.struct(G, SHIP)}, αποθέματα {s0} -> {s1}, "
                f"φορτία καθ' οδόν {carried()} — η πρόζα λέει +150, +100 και CR_GONE")
    ok = TDm.truth(G)
    if not ok[0]:
        return "ΟΛΟ: οθόνη/πλήρης σχεδίαση: " + ok[1]
    say(f"ΟΛΟ: σε {t} s παιχνιδιού +150 μέταλλο, +100 βιοπλαστικό, τα κιβώτια έφυγαν, η "
        f"οθόνη όση η πλήρης σχεδίαση")
    return None


# --------------------------------------------------------------------------
# ΑΡΝΗΤΙΚΑ
# --------------------------------------------------------------------------
def find(G, sym, name, pat, n=200):
    a = sym[name]
    ram = G.m.read_ram(a, n)
    k = bytes(ram).find(bytes(pat))
    assert k >= 0, f"δεν βρέθηκε το {pat} στο {name}"
    return a + k


def negatives(sym, g):
    G = TH.Game(sym)
    cr = lambda name: [0xCD, sym[name] & 255, sym[name] >> 8]
    jr = lambda name: None
    neg = []
    # μόνο μέταλλο: το jr nc,hla_take μετά το cp CR_BIO γίνεται jr
    a = find(G, sym, "CR_ARRIVE", [0xFE, CR_BIO, 0x0E, S_METAL, 0x30])
    neg.append(("μόνο μέταλλο", loads, [("ram", a + 4, 0x18)]))
    # το αγαθό δεν γράφεται στο J_SITE: ld (hl),a -> nop
    a = find(G, sym, "CR_ARRIVE", [0xF6, 0x80, 0x77])
    neg.append(("το J_SITE χωρίς αγαθό", loads, [("ram", a + 2, 0x00)]))
    # καμία επόμενη Haul: call cr_next -> 3 x nop
    a = find(G, sym, "CR_ARRIVE", cr("CR_NEXT"))
    neg.append(("καμία επόμενη Haul", loads, [("ram", a + k, 0) for k in range(3)]))
    # η παράδοση ως μετάλλευμα: το jr c,hla_crd του hla_drop -> nop nop
    a = find(G, sym, "HLA_DROP", [0x7E, 0x87, 0x38])
    neg.append(("η παράδοση ως μετάλλευμα", loads, [("ram", a + 2, 0), ("ram", a + 3, 0)]))
    # η κατοχή μένει: το πρώτο res 4,(hl) του cr_vanish -> nop nop
    a = find(G, sym, "CR_VANISH", [0xCB, 0xA6])
    neg.append(("η κατοχή που μένει", gone, [("ram", a, 0), ("ram", a + 1, 0)]))
    # η λήξη: ld (ix+ST_OWED),a του cr_sol -> 3 x nop
    a = find(G, sym, "CR_SOL", [0xDD, 0x77, TH.ST_OWED])
    neg.append(("η λήξη που δεν έρχεται", gone, [("ram", a + k, 0) for k in range(3)]))
    # το sol χωρίς κιβώτια: το cp CR_BOX του ev_after γίνεται cp 0, της πλατφόρμας
    a = find(G, sym, "EVA_CR", [0xFE, CR_BOX], 8)
    neg.append(("το sol και χωρίς κιβώτια", gone, [("ram", a + 1, 0)]))
    # ο μετεωρίτης στα κιβώτια: το ret nc μετά το cp K_SHIP του mth_struct γίνεται
    # ret z, όπως ως το βήμα 180
    o = sym["MTH_STRUCT"] - 0x4000                       # b6code: στην τράπεζα 6
    k = bytes(G.b6[o:o + 20]).find(bytes([0xFE, K_SHIP, 0xD0]))
    assert k >= 0, "δεν βρέθηκε το cp K_SHIP / ret nc στο MTH_STRUCT"
    hit6 = [(sym["MTH_STRUCT"] + k + 2, 0xC8)]
    # το σκάφος πάντα: το cp 1 του dmc_shp γίνεται cp 4
    a = find(G, sym, "DM_CAN", [0x79, 0xFE, 0x01], 120)
    neg.append(("το σκάφος πάντα γκρεμίσιμο", rule, [("ram", a + 2, 4)]))
    out = []
    for label, fn, patch in neg:
        ram = [(at, v) for _, at, v in patch]
        if fn in (rule,):
            why = fn(sym, g, [("ram", at, v) for at, v in ram], quiet=True)
        elif fn is loads or fn is gone:
            why = fn(sym, ram, quiet=True)
        out.append((label, why))
    out.append(("ο μετεωρίτης που χτυπά τα κιβώτια", meteor(sym, quiet=True, patch6=hit6)))
    # ο σωρός του dm_ship, στις τρύπες: ld (hl),CR_PILE -> ld (hl),0
    o = TDm.at_ovl(sym, "DM_SHIP", 60, [0x36, CR_PILE], [(1, 0)])
    out.append(("ο σωρός που δεν γράφεται",
                convert(sym, g, o, quiet=True) if o else "δεν βρέθηκε το ld (hl),CR_PILE"))
    # η εργασία γυρίζει στο J_SITE ενός φορτίου: bit 7,d / jr nz -> nop x 4
    o = TDm.at_ovl(sym, "DM_DO", 600, [0xCB, 0x7A, 0x20], [(0, 0), (1, 0), (2, 0), (3, 0)])
    out.append(("η εργασία που γυρίζει στο J_SITE",
                store_goes(sym, g, o, quiet=True) if o else "δεν βρέθηκε το bit 7,d"))
    for label, why in out:
        check(why is not None, f"ΑΡΝΗΤΙΚΟ: με {label} αποτυγχάνει"
                               + (f" ({why[:120]})" if why else ""))


def main():
    sym, g = TG.build()
    # το test_demolish διαβάζει τις τρύπες όταν φορτώνεται, πριν από το build
    TDm.OVL = open(TDm._OV, "rb").read()
    for name, fn in (("ΚΑΝΟΝΑΣ", lambda: rule(sym, g)),
                     ("ΚΙΒΩΤΙΑ", lambda: convert(sym, g)),
                     ("ΦΟΡΤΙΟ", lambda: loads(sym)),
                     ("ΤΕΛΟΣ", lambda: gone(sym)),
                     ("ΜΕΤΕΩΡΙΤΗΣ", lambda: meteor(sym)),
                     ("Η ΑΠΟΘΗΚΗ ΓΚΡΕΜΙΖΕΤΑΙ", lambda: store_goes(sym, g)),
                     ("ΟΛΟ", lambda: whole(sym, g))):
        why = fn()
        check(why is None, name + (f" — {why}" if why else ""))
    negatives(sym, g)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
