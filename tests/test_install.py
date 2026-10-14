#!/usr/bin/env python3
"""Οι μηχανές κουβαλιούνται και στήνονται (βήμα 99, DESIGN §6.9).

Η πρόζα — οι αποφάσεις του παίκτη, όπως στο Planetbase:

  FIT        η μηχανή πληρώνεται αμέσως, όπως ως το 98, και ζωγραφίζεται·
             η υγεία της γίνεται MACH_OWED = 7 (χρωστά μέταλλο, bit 0, και
             βιοπλαστικό, bit 1). ΜΙΑ Supply ανά υλικό για τον θόλο, [7 ή 8,
             θόλος, -, 4, θόλος], όσες μηχανές κι αν μπουν. Τα φυτά του
             θερμοκηπίου μένουν άμεσα: υγεία 200, καμία εργασία.
  ΦΟΡΤΙΟ     μια Supply σε θόλο σε λειτουργία δίνει το υλικό της στην ΠΡΩΤΗ
             μηχανή που το χρωστά, και ξανανοίγει όσο το χρωστά άλλη· το
             D_POWER και το D_OPS του θόλου (ρεύμα, χειριστές) δεν τα αγγίζει.
             Σε εργοτάξιο πρώτα το εργοτάξιο, μετά οι μηχανές του. Αν η μηχανή
             βγήκε στο μεταξύ, η εργασία απλώς τελειώνει.
  BUILD      όταν μια μηχανή σε θόλο σε λειτουργία πάρει και τα δύο (υγεία
             MACH_READY = 4), μία Build [0, θόλος, -, 5, θόλος], αν δεν υπάρχει
             ήδη, και το EC_NBUILD +1. Σε εργοτάξιο καμία: το στήνει ο χτίστης
             του κτιρίου όταν τελειώσει.
  ΣΤΗΣΙΜΟ    ο χτίστης ανεβάζει την πρώτη έτοιμη υποδοχή κατά 32 ανά επίσκεψη
             (4, 36, 68, 100, και μετά 200: δουλεύει). Μένει όσο βρίσκει μία,
             και τελειώνει (EC_NBUILD -1) στην επίσκεψη που δεν βρίσκει. Μια
             χαλασμένη (0) ή μια που χρωστά δεν τη στήνει. Ενα κτίριο που
             τελειώνει συνεχίζει στις έτοιμες μηχανές του από την ίδια επίσκεψη.
  ΣΤΑΜΑΤΗΜΕΝΗ ως το 200 η μηχανή δεν παράγει, δεν ζητά χειριστή, δεν ζητά
             επισκευή, και η βλάβη (ec_break, ο μετεωρίτης) δεν τη μηδενίζει.
  ΑΛΥΣΙΔΑ    στο παιχνίδι που τρέχει, από νέο παιχνίδι: ο πρώτος θόλος S, μια
             γεννήτρια οξυγόνου στο FIT. Οι άποικοι φορτώνουν μέταλλο και
             βιοπλαστικό στο σκάφος, τη Build την παίρνει μόνο ο μηχανικός, και
             η υγεία περνά από 7 στο 4, 36, 68, 100, 200. Και σε εργοτάξιο: ένας
             δεύτερος θόλος με τη γεννήτρια από την τοποθέτηση· όταν τελειώνει
             το lk_done βγάζει τον χτίστη έξω, κι εκείνος ξαναμπαίνει και τη
             στήνει.
  ΚΟΣΤΟΣ     η θέση 13 με ένα φορτίο σε μηχανή, με το τελευταίο (Build), και
             με ένα στήσιμο, κάτω από τα ταβάνια COST.

ΟΙ ΣΚΗΝΕΣ στην αποικία δοκιμών, με μόνο τη θέση 13: ο θόλος 1 γίνεται μεσαίο
εργοστάσιο (τέσσερις υποδοχές), ο πράκτορας 1 στέκεται εκεί με την εργασία,
και όλοι οι ζωντανοί είναι απασχολημένοι ώστε τίποτα να μην ανατεθεί.

Αρνητικά, με τον κώδικα πειραγμένο στη μνήμη: το FIT χωρίς εργασίες· χωρίς
το «αν δεν υπάρχει ήδη»· ένας θόλος σε λειτουργία ως εργοτάξιο· καμία Build
για τη μηχανή· Build και σε εργοτάξιο· το εργοτάξιο πληρώθηκε και η εργασία
τελειώνει ενώ μια μηχανή χρωστά· στήσιμο χωρίς υλικά· η Build δεν στήνει
ποτέ· ο χτίστης μένει έξω όταν τελειώνει το κτίριο· παραγωγή, χειριστής και βλάβη με «υγεία όχι μηδέν» όπως ως το 98.
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import test_haul as TH                                   # noqa: E402
import test_drill as TD                                  # noqa: E402
import test_outside as TO                                # noqa: E402
import test_supply as TS                                 # noqa: E402
import test_reveal as R                                  # noqa: E402
import test_fit as TF                                    # noqa: E402
import balance as B                                      # noqa: E402
import econ as EC                                        # noqa: E402

FAIL = []
J_BUILD, J_OPERATE, J_REPAIR, J_SUPPLY, NO_JOB = 0, 1, 4, 7, 255
OWED, READY, HP, STEP = 7, 4, 200, 32
DS_BUILDING, DS_ACTIVE = 1, 2
D, WHO = 1, 1                       # ο θόλος των σκηνών, ο πράκτορας
MACH = [1, 2, 3, 5]                 # μέταλλο, βιοπλαστικό, όπλα, ρομπότ
F_ALIVE, F_WORKING = 1, 32
S_ORE, S_METAL, S_BIOPL = EC.S_ORE, EC.S_METAL, EC.S_BIOPL
SHIP, ENGINEER = 64, 1
FAR = 40                            # το EC_JDOME των σκηνών: άδειοι θόλοι
COST = {"θέση 13, φορτίο σε μηχανή": 500,                 # το εργοτάξιο, βήμα 98: 267
        "θέση 13, φορτίο σε μηχανή, ξανανοίγει": 1200,     # το εργοτάξιο, βήμα 98: 918
        "θέση 13, το τελευταίο φορτίο (Build)": 2100,      # το εργοτάξιο, βήμα 98: 1003
        "θέση 13, ένα στήσιμο": 400,
        "θέση 13, φορτίο σε εργοτάξιο, ξανανοίγει": 1100,  # βήμα 98: 918
        "θέση 13, το τελευταίο του εργοταξίου": 600,       # βήμα 98: 267
        "θέση 13, το τελευταίο του εργοταξίου (Build)": 1400}  # βήμα 98: 1003


def check(ok, msg):
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ ") + msg)
    if not ok:
        FAIL.append(msg)


def econ_at():
    g = TO.layout()["G_econ_state"]
    const = open(os.path.join(ROOT, "src", "const.asm"), encoding="utf-8").read()
    out = {"EC_STOCK": g}
    for n in ("EC_NBUILD", "EC_PDOME", "EC_JDOME"):
        out[n] = g + int(re.search(rf"^{n}\s+equ G_econ_state \+ (\d+)", const, re.M).group(1))
    return out


class Game(TH.Game):
    """Το colony.sna σε παύση, με ό,τι χρειάζονται οι μηχανές."""

    def __init__(self, sym, patch=(), patch6=()):
        super().__init__(sym, patch, patch6)
        self.X = econ_at()

    def drec(self, d=D):
        return [self.b6[self.dome + 24 * d + k] for k in range(24)]

    def hp(self, n=4):
        return self.drec()[16:16 + n]

    def stock(self, k):
        return self.w16(self.EC["EC_STOCK"] + 2 * k)

    def set_stock(self, d):
        for k, v in d.items():
            self.s16(self.EC["EC_STOCK"] + 2 * k, v)

    def nbuild(self):
        return self.m.peek(self.X["EC_NBUILD"])

    def of(self, kind):
        """Οι εργασίες αυτού του είδους στον θόλο D."""
        return [self.job(j) for j in range(32) if self.job(j)[0] == kind and self.job(j)[4] == D]

    def factory(self, hp, state=DS_ACTIVE, integ=255, owed=(0, 0), ops=2):
        """Ο θόλος D μεσαίο εργοστάσιο, με τις υγείες hp (None = άδεια)."""
        b = self.dome + 24 * D
        self.b6[b + 2], self.b6[b + 3], self.b6[b + 4], self.b6[b + 5] = 1, EC.R_FACTORY, state, integ
        self.b6[b + 6], self.b6[b + 7] = owed if state != DS_ACTIVE else (0, ops)
        for k in range(8):
            h = hp[k] if k < len(hp) else None
            self.b6[b + 8 + k] = 255 if h is None else MACH[k % 4]
            self.b6[b + 16 + k] = 0 if h is None else h

    def calm(self):
        """Κανείς δεν παίρνει εργασία, και η δημοσίευση κοιτάζει άδειους θόλους."""
        for i in range(128):
            f = self.ag_get(i, "flags")
            if f & F_ALIVE:
                self.ag_set(i, flags=f | F_WORKING)
        self.m.poke(self.X["EC_JDOME"], FAR)


def scene(sym, hp, kind=J_SUPPLY, builds=0, patch=(), patch6=(), **dome):
    """Ο θόλος D με τις υγείες hp, και ο WHO εκεί με μια εργασία `kind` — μια
    Supply φέρνει το υλικό της. `builds` Build του θόλου ήδη στον πίνακα."""
    G = Game(sym, patch, patch6)
    G.factory(hp, **dome)
    for j in range(32):
        G.put_job(j, [NO_JOB] * 5)
    for k in range(builds):
        G.put_job(k, [J_BUILD, D, 255, 5, D])
    j = G.free_job()
    G.put_job(j, [kind, D, WHO, 5 if kind == J_BUILD else 4, D])
    G.m.poke(G.X["EC_NBUILD"], builds + (kind == J_BUILD))
    G.calm()
    G.ag_set(WHO, flags=F_ALIVE | F_WORKING, node=D, dest=D, edge=255, task=j,
             spare=S_METAL + kind - J_SUPPLY if kind >= J_SUPPLY else 0)
    return G, j


def look(G, j):
    d = G.drec()
    return (G.job(j), G.hp(), d[4], d[6], d[7], G.nbuild(), G.of(J_BUILD))


GONE = [NO_JOB, D, WHO, 4, D]


# --------------------------------------------------------------------------
# ΦΟΡΤΙΟ — η θέση 13 με μια Supply στον θόλο
# --------------------------------------------------------------------------
def deliver(sym, patch=(), patch6=(), quiet=False):
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    BUILD = [J_BUILD, D, 255, 5, D]
    REOPEN = lambda k: [k, D, 255, 4, D]
    cases = [
        # (όνομα, υγείες, είδος, Build πριν, θόλος, τι λέει η πρόζα)
        ("ΜΙΑ ΜΗΧΑΝΗ: το μέταλλο", [OWED, HP, None, None], J_SUPPLY, 0, {},
         (GONE[:1], [6, HP, 0, 0], DS_ACTIVE, 0, 2, 0, [])),
        ("ΔΥΟ ΤΟ ΧΡΩΣΤΑΝΕ: η πρώτη, και ξανανοίγει", [OWED, HP, OWED, None], J_SUPPLY, 0, {},
         (REOPEN(J_SUPPLY), [6, HP, OWED, 0], DS_ACTIVE, 0, 2, 0, [])),
        ("ΤΟ ΤΕΛΕΥΤΑΙΟ: μία Build", [6, HP, None, None], J_SUPPLY + 1, 0, {},
         (GONE[:1], [READY, HP, 0, 0], DS_ACTIVE, 0, 2, 1, [BUILD])),
        ("ΜΙΑ BUILD ΑΡΚΕΙ", [6, READY, None, None], J_SUPPLY + 1, 1, {},
         (GONE[:1], [READY, READY, 0, 0], DS_ACTIVE, 0, 2, 1, [BUILD])),
        ("ΕΡΓΟΤΑΞΙΟ: καμία Build", [6, None, None, None], J_SUPPLY + 1, 0,
         dict(state=DS_BUILDING, integ=64),
         (GONE[:1], [READY, 0, 0, 0], DS_BUILDING, 0, 0, 0, [])),
        ("ΠΡΩΤΑ ΤΟ ΕΡΓΟΤΑΞΙΟ", [6, None, None, None], J_SUPPLY + 1, 0,
         dict(state=DS_BUILDING, integ=0, owed=(0, 2)),
         (REOPEN(J_SUPPLY + 1), [6, 0, 0, 0], DS_BUILDING, 0, 1, 0, [])),
        ("ΤΟ ΕΡΓΟΤΑΞΙΟ ΠΛΗΡΩΘΗΚΕ, Η ΜΗΧΑΝΗ ΟΧΙ", [6, None, None, None], J_SUPPLY + 1, 0,
         dict(state=DS_BUILDING, integ=0, owed=(0, 1)),
         (REOPEN(J_SUPPLY + 1), [6, 0, 0, 0], DS_BUILDING, 0, 0, 1, [BUILD])),
        ("ΒΓΗΚΕ ΣΤΟ ΜΕΤΑΞΥ", [None, HP, None, None], J_SUPPLY, 0, {},
         (GONE[:1], [0, HP, 0, 0], DS_ACTIVE, 0, 2, 0, [])),
    ]
    for name, hp, kind, builds, dome, want in cases:
        G, j = scene(sym, hp, kind, builds, patch, patch6, **dome)
        G.call("JOBS_TICK")
        got = look(G, j)
        got = (got[0][:1] if got[0][0] == NO_JOB else got[0],) + got[1:]
        if got != want:
            return (f"{name}: (εργασία, υγείες, κατάσταση, D_POWER, D_OPS, EC_NBUILD, Build) = "
                    f"{got} — η πρόζα λέει {want}")
    say("ΦΟΡΤΙΟ: στην πρώτη που το χρωστά (7 -> 6), ξανανοίγει όσο το χρωστά άλλη· "
        "με το τελευταίο υγεία 4 και μία Build (όχι δεύτερη)· οι χειριστές (D_OPS 2) "
        "ανέγγιχτοι")
    say("ΕΡΓΟΤΑΞΙΟ: πρώτα το δικό του χρέος (2 -> 1), και όταν πληρωθεί η δική του "
        "Build ενώ η εργασία ξανανοίγει για τη μηχανή· καμία Build για μηχανή σε "
        "εργοτάξιο· αν η μηχανή βγήκε, η εργασία τελειώνει")
    return None


# --------------------------------------------------------------------------
# ΣΤΗΣΙΜΟ — η θέση 13 με μια Build, επίσκεψη προς επίσκεψη
# --------------------------------------------------------------------------
def install(sym, patch=(), patch6=(), quiet=False):
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G, j = scene(sym, [READY, 0, OWED, 100], J_BUILD, 0, patch, patch6)
    want = [[36, 0, OWED, 100], [68, 0, OWED, 100], [100, 0, OWED, 100],
            [HP, 0, OWED, 100], [HP, 0, OWED, HP]]
    seen = []
    for k, w in enumerate(want):
        G.call("JOBS_TICK")
        seen.append(G.hp())
        if G.hp() != w or G.job(j) != [J_BUILD, D, WHO, 5, D] or G.nbuild() != 1:
            return (f"ΣΤΗΣΙΜΟ, επίσκεψη {k + 1}: υγείες {seen}, εργασία {G.job(j)}, EC_NBUILD "
                    f"{G.nbuild()} — η πρόζα λέει {want[:k + 1]}, η Build μένει, 1")
    G.call("JOBS_TICK")
    if G.job(j)[0] != NO_JOB or G.nbuild() != 0 or G.hp() != want[-1]:
        return (f"ΣΤΗΣΙΜΟ, το τέλος: εργασία {G.job(j)}, EC_NBUILD {G.nbuild()}, υγείες "
                f"{G.hp()} — η πρόζα λέει τελειώνει, 0")
    say(f"ΣΤΗΣΙΜΟ: {[READY, 0, OWED, 100]} -> " + " -> ".join(str(s) for s in seen) +
        ", και στην έκτη επίσκεψη η Build τελειώνει (EC_NBUILD 1 -> 0)· η χαλασμένη και "
        "αυτή που χρωστά έμειναν")
    # το κτίριο τελειώνει: και οι μηχανές του, από την ίδια επίσκεψη
    G, j = scene(sym, [OWED, READY], J_BUILD, 0, patch, patch6, state=DS_BUILDING, integ=224)
    G.call("JOBS_TICK")
    got = (G.drec()[4], G.hp(2), G.job(j), G.nbuild())
    want = (DS_ACTIVE, [OWED, 36], [J_BUILD, D, WHO, 5, D], 1)
    if got != want:
        return f"ΤΟ ΚΤΙΡΙΟ ΤΕΛΕΙΩΝΕΙ: {got} — η πρόζα λέει {want}"
    G, j = scene(sym, [OWED], J_BUILD, 0, patch, patch6, state=DS_BUILDING, integ=224)
    G.call("JOBS_TICK")
    got = (G.drec()[4], G.hp(1), G.job(j)[0], G.nbuild())
    want = (DS_ACTIVE, [OWED], NO_JOB, 0)
    if got != want:
        return f"ΤΟ ΚΤΙΡΙΟ ΤΕΛΕΙΩΝΕΙ, ΚΑΜΙΑ ΕΤΟΙΜΗ: {got} — η πρόζα λέει {want}"
    say("ΤΟ ΚΤΙΡΙΟ ΤΕΛΕΙΩΝΕΙ: ο θόλος σε λειτουργία και η έτοιμη μηχανή 4 -> 36 στην ίδια "
        "επίσκεψη, η Build μένει· χωρίς έτοιμη τελειώνει όπως ως το 98")
    return None


# --------------------------------------------------------------------------
# ΣΤΑΜΑΤΗΜΕΝΗ — παραγωγή, χειριστής, επισκευή, βλάβη
# --------------------------------------------------------------------------
def stopped(sym, patch=(), patch6=(), quiet=False):
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    made = {}
    for h in (OWED, 5, READY, 36, 100, HP):
        G = Game(sym, patch, patch6)
        G.factory([h], ops=1)
        G.set_stock({S_ORE: 100, S_METAL: 50})
        G.m.poke(G.X["EC_PDOME"], D)
        G.call("EC_RUN_DOME")
        made[h] = G.stock(S_METAL) - 50
    q = EC.RECIPE[1][7]                     # ό,τι βγάζει ένα σίδερο: 2 από το βήμα 125
    if made != {OWED: 0, 5: 0, READY: 0, 36: 0, 100: 0, HP: q}:
        return f"ΠΑΡΑΓΩΓΗ: μέταλλο ανά υγεία {made} — η πρόζα λέει μόνο το 200 (+{q})"
    posted = {}
    for ops in (1, 0):
        G = Game(sym, patch, patch6)
        G.factory([OWED, READY, 100, HP], ops=ops)
        for j in range(32):
            G.put_job(j, [NO_JOB] * 5)
        G.calm()
        G.m.poke(G.X["EC_JDOME"], D)
        G.call("JOBS_TICK")
        posted[ops] = sorted({job[0] for k in range(10) for job in G.of(k)})
    if posted != {1: [], 0: [J_OPERATE]}:
        return (f"ΧΕΙΡΙΣΤΗΣ: είδη εργασιών στον θόλο με 1/0 χειριστές {posted} — η πρόζα "
                f"λέει καμία με έναν (μόνο το 200 θέλει), Operate με κανέναν· ποτέ Repair")
    broke = {}
    for h in (OWED, READY, 36, 100, HP):
        G = Game(sym, patch, patch6)
        G.factory([HP, h])
        G.m.poke(sym["EB_D"], D)
        G.m.poke(sym["EB_S"], 1)
        G.call("EC_BREAK_D")
        broke[h] = G.hp(2)[1]
    if broke != {OWED: OWED, READY: READY, 36: 36, 100: 100, HP: 0}:
        return f"ΒΛΑΒΗ: η υγεία μετά το ec_break_d {broke} — η πρόζα λέει μόνο το 200 -> 0"
    say(f"ΣΤΑΜΑΤΗΜΕΝΗ: παράγει μόνο το 200 (+{q} μέταλλο)· με έναν χειριστή καμία Operate "
        "(θέλει μόνο η 200), με κανέναν μία, και ποτέ Repair· η βλάβη μηδενίζει μόνο το 200")
    return None


# --------------------------------------------------------------------------
# FIT — από τα πλήκτρα, σε εργοστάσιο της αποικίας
# --------------------------------------------------------------------------
def fit(sym, g, patch=(), quiet=False):
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G = R.Game(sym, g)
    for at, v in patch:
        G.m.poke(at, v)
    F = TF.Fit(G, sym, g)
    F.set_stocks(TF.STOCK, TF.STOCK)
    tx, ty = B.clear_spots(8, 1, dome=True)[0]
    G.camera(tx - 6, ty - 1)
    at = (2 * tx + 8, 2 * ty + 8)
    B.build(G.m, sym, TF.I_DOME_M, g + 6, at=at, room=TF.RM_FACTORY, fit=False)
    node = G.m.peek(sym["BD_NODE"])
    if not R.finish(G, node):
        return f"FIT: το εργοστάσιο {node} δεν τελείωσε"
    G.settle()
    if not F.enter(at):
        return f"FIT: ο εξοπλισμός δεν άνοιξε (κατάσταση {F.peek('UI_STATE')})"
    # κανείς δεν παίρνει εργασία όσο πατιούνται τα πλήκτρα: χωρίς αποθήκη η
    # αποικία δοκιμών κουβαλά από τον ίδιο τον θόλο, και ένα φορτίο θα έφτανε
    ag, b6 = TO.layout()["G_agent_fields"] - 0x4000, G.bank(6)
    for i in range(128):
        if b6[ag + i] & F_ALIVE:
            b6[ag + i] |= F_WORKING
    jt = TO.layout()["G_job_tbl"]
    mine = lambda: sorted(list(G.m.read_ram(jt + 5 * k, 5)) for k in range(32)
                          if G.m.peek(jt + 5 * k) in (J_SUPPLY, J_SUPPLY + 1)
                          and G.m.peek(jt + 5 * k + 4) == node)
    fe0, bi0 = F.stocks()
    for s, i in enumerate([1, 2, 1, 4]):            # μέταλλο, βιοπλαστικό, μέταλλο, ρομπότ
        F.put(s, i)
    fe1, bi1 = F.stocks()
    rec, jobs = F.rec(node), mine()
    kinds = [(j[0], j[3], j[4]) for j in jobs]
    if rec[16:20] != [OWED] * 4 or kinds != [(J_SUPPLY, 4, node), (J_SUPPLY + 1, 4, node)] \
            or (fe0 - fe1, bi0 - bi1) != (8 + 8 + 8 + 10, 2 + 2 + 2 + 4):
        return (f"FIT: υγείες {rec[16:20]}, Supply του θόλου {jobs}, πληρώθηκαν "
                f"{(fe0 - fe1, bi0 - bi1)} — η πρόζα λέει [7]*4, μία ανά υλικό, (34, 10)")
    say(f"FIT: τέσσερις μηχανές στο εργοστάσιο {node}, υγείες {rec[16:20]}, πληρωμένες "
        f"-{fe0 - fe1}/-{bi0 - bi1}, και ΔΥΟ Supply: {kinds}")
    return None


# --------------------------------------------------------------------------
# ΑΛΥΣΙΔΑ — στο παιχνίδι που τρέχει, από νέο παιχνίδι
# --------------------------------------------------------------------------
def chain(sym, g, patch=(), quiet=False, shots=None):
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    w = TS.W(sym, g, patch)
    m = w.m
    # ο θόλος, και το airlock του: χωρίς αυτό ο θόλος είναι σφραγισμένος και
    # κανείς δεν φτάνει μέσα (βήμα 86)
    B.build(m, sym, 0, g + 6, at=TO.DOME_AT, room=0, fit=False)
    if w.wait(lambda: w.dome(0)[4] == DS_ACTIVE, 30000) is None:
        return f"ΑΛΥΣΙΔΑ: ο θόλος δεν τελείωσε: {w.dome(0)}, {w.jobs()}"
    B.build(m, sym, 9, g + 6, at=TO.LOCK_AT, fit=False)
    if w.wait(lambda: w.lock()[4] == DS_ACTIVE, 30000) is None:
        return f"ΑΛΥΣΙΔΑ: το airlock δεν τελείωσε: {w.lock()}, {w.jobs()}"
    m.run_frames(50)
    m.poke(sym["CUR_HX"], TO.DOME_AT[0])
    m.poke(sym["CUR_HY"], TO.DOME_AT[1])
    full = B.fit_dome(m, sym, how=[1])
    hp = lambda: w.b6(w.L["G_dome_tbl"] + 16)[0]
    mach = w.b6(w.L["G_dome_tbl"] + 8)[0]
    if full != 1 or mach != 0 or hp() != OWED:
        return f"ΑΛΥΣΙΔΑ: μετά το FIT μηχανή {mach}, υγεία {hp()} — η πρόζα λέει οξυγόνο, 7"
    if shots:
        m.screenshot(shots[0])
    log = {"hp": [hp()], "loaded": set(), "builders": set()}
    carrying = [0] * 4
    t = 0
    while t < 30000 and hp() != HP:
        m.run_frames(TS.STEP)
        t += TS.STEP
        if hp() != log["hp"][-1]:
            log["hp"].append(hp())
        for i in range(4):
            a = w.agent(i)
            if a["spare"] and not carrying[i]:
                log["loaded"].add((a["spare"], a["node"]))
            carrying[i] = a["spare"]
        for j in w.jobs():
            if j[0] == J_BUILD and j[2] != 255:
                log["builders"].add(w.agent(j[2])["role"])
    if hp() != HP:
        return f"ΑΛΥΣΙΔΑ: η μηχανή δεν στήθηκε σε {t} frames: υγείες {log['hp']}, {w.jobs()}"
    if shots:
        m.run_frames(100)
        m.screenshot(shots[1])
    # τα δύο φορτία μπορεί να φτάσουν στο ίδιο δείγμα: 7 -> 4 κατευθείαν
    want_hp = [[OWED] + a + [READY, 36, 68, 100, HP] for a in ([5], [6], [])]
    if log["hp"] not in want_hp:
        return f"ΑΛΥΣΙΔΑ: υγείες {log['hp']} — η πρόζα λέει {want_hp[0]} (ή 6 αντί 5)"
    if log["loaded"] != {(S_METAL, SHIP), (S_BIOPL, SHIP)}:
        return f"ΑΛΥΣΙΔΑ: φορτώθηκαν {log['loaded']} — θέλει μέταλλο και βιοπλαστικό στο σκάφος"
    if log["builders"] != {ENGINEER}:
        return f"ΑΛΥΣΙΔΑ: τη Build την πήραν ρόλοι {sorted(log['builders'])} — μόνο ο μηχανικός"
    say(f"ΑΛΥΣΙΔΑ: γεννήτρια οξυγόνου στον πρώτο θόλο, υγείες {log['hp']} σε {t} frames, "
        f"φορτία {sorted(log['loaded'])}, Build από ρόλους {sorted(log['builders'])}")
    return None


def chain_site(sym, g, patch=(), quiet=False, frames=40000):
    """ΑΛΥΣΙΔΑ, ΣΕ ΕΡΓΟΤΑΞΙΟ: μετά τον πρώτο θόλο και το airlock του, ένας
    δεύτερος θόλος οξυγόνου με τη γεννήτρια από το FIT της τοποθέτησης. Οταν
    τελειώνει, το lk_done βγάζει όσους στέκονται εκεί, και τον χτίστη, έξω·
    εκείνος κρατά την εργασία, ξαναμπαίνει από το airlock και τη στήνει."""
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    w = TS.W(sym, g, patch)
    m = w.m
    B.build(m, sym, 0, g + 6, at=TO.DOME_AT, room=0, fit=False)
    if w.wait(lambda: w.dome(0)[4] == DS_ACTIVE, 30000) is None:
        return f"ΣΕ ΕΡΓΟΤΑΞΙΟ: ο πρώτος θόλος δεν τελείωσε: {w.dome(0)}"
    B.build(m, sym, 9, g + 6, at=TO.LOCK_AT, fit=False)
    if w.wait(lambda: w.lock()[4] == DS_ACTIVE, 30000) is None:
        return f"ΣΕ ΕΡΓΟΤΑΞΙΟ: το airlock δεν τελείωσε: {w.lock()}"
    # ΝΟΤΙΟΔΥΤΙΚΑ, ΟΧΙ ΑΝΑΤΟΛΙΚΑ (βήμα 132). Ως το 131 το ανατολικό (+16, 0) δεν
    # χωρούσε και το live_spot έδινε το (-2, 6)· εκεί ο θόλος τελειώνει στην
    # ίδια επίσκεψη με το πρώτο στήσιμο (4 -> 36), το lk_done βγάζει τον χτίστη,
    # και το jabi_go τον ξαναστέλνει μέσα. Με το πλατό 8 το ανατολικό χώρεσε, ο
    # θόλος τελείωνε με τη μηχανή να χρωστά ακόμη (5), και το αρνητικό του
    # jabi_go δεν έπιανε τίποτα. Τώρα η θέση ζητιέται, και η σκηνή ελέγχει ότι
    # το τέλος του θόλου ήρθε μαζί με το πρώτο στήσιμο.
    at = B.live_spot(m, sym, 0, (TO.DOME_AT[0] - 8, TO.DOME_AT[1] + 4))
    B.build(m, sym, 0, g + 6, at=at, room=0, fit=True)
    node = m.peek(sym["BD_NODE"])
    hp = lambda: w.b6(w.L["G_dome_tbl"] + 24 * node + 16)[0]
    if node == 0 or w.dome(node)[4] != DS_BUILDING or hp() != OWED:
        return (f"ΣΕ ΕΡΓΟΤΑΞΙΟ: ο δεύτερος θόλος στο {at}: κόμβος {node}, εγγραφή "
                f"{w.dome(node)}, υγεία {hp()} — η πρόζα λέει εργοτάξιο, 7")
    seen, out = [hp()], 0
    t = 0
    inside, was = None, None            # το τέλος του θόλου μαζί με το πρώτο στήσιμο
    while t < frames and not (w.dome(node)[4] == DS_ACTIVE and hp() == HP):
        m.run_frames(TS.STEP)
        t += TS.STEP
        if hp() != seen[-1]:
            seen.append(hp())
        if inside is None and w.dome(node)[4] == DS_ACTIVE:
            inside = was == 4 and hp() > 4
        elif w.dome(node)[4] != DS_ACTIVE:
            was = hp()
        for j in w.jobs():
            if j[0] == J_BUILD and j[1] == node and j[2] != 255 and w.dome(node)[4] == DS_ACTIVE \
                    and w.agent(j[2])["node"] != node:
                out += 1                # ο χτίστης έξω, με την εργασία δική του
    if hp() != HP:
        return (f"ΣΕ ΕΡΓΟΤΑΞΙΟ: σε {t} frames υγείες {seen}, θόλος {w.dome(node)}, "
                f"εργασίες {w.jobs()} — η πρόζα λέει στήνεται ως το 200")
    if not inside:
        return (f"ΣΕ ΕΡΓΟΤΑΞΙΟ: ο θόλος στο {at} τελείωσε χωρίς στήσιμο στην ίδια "
                f"επίσκεψη (υγείες {seen}) — η σκηνή δεν δοκιμάζει το lk_done με τον "
                f"χτίστη, ούτε το αρνητικό του jabi_go")
    say(f"ΣΕ ΕΡΓΟΤΑΞΙΟ: ο δεύτερος θόλος (κόμβος {node}, στο {at}), υγείες {seen} σε {t} "
        f"frames· τελείωσε μαζί με το πρώτο στήσιμο, ο χτίστης ήταν έξω με τη Build σε "
        f"{out} δείγματα και ξαναμπήκε")
    return None


# --------------------------------------------------------------------------
# ΚΟΣΤΟΣ
# --------------------------------------------------------------------------
def cost(sym):
    """Η θέση 13 με την άφιξη, μείον η ίδια χωρίς εργασία. Και τα δύο φορτία
    του εργοταξίου (βήμα 88), που περνούν πια και από το mc_live."""
    out = {}
    G, j = scene(sym, [OWED, HP])
    G.put_job(j, [NO_JOB] * 5)
    G.ag_set(WHO, task=255)
    base = G.call("JOBS_TICK", timed=True)
    for name, args, kw in (
            ("θέση 13, φορτίο σε μηχανή", ([HP, OWED],), {}),
            ("θέση 13, φορτίο σε μηχανή, ξανανοίγει", ([HP, HP, OWED, OWED],), {}),
            ("θέση 13, το τελευταίο φορτίο (Build)", ([HP, HP, HP, 6], J_SUPPLY + 1), {}),
            ("θέση 13, ένα στήσιμο", ([HP, HP, OWED, READY], J_BUILD), {}),
            ("θέση 13, φορτίο σε εργοτάξιο, ξανανοίγει", ([HP],),
             dict(state=DS_BUILDING, integ=0, owed=(2, 0))),
            ("θέση 13, το τελευταίο του εργοταξίου", ([None],),
             dict(state=DS_BUILDING, integ=0, owed=(1, 1))),
            ("θέση 13, το τελευταίο του εργοταξίου (Build)", ([None],),
             dict(state=DS_BUILDING, integ=0, owed=(1, 0)))):
        G, j = scene(sym, *args, **kw)
        out[name] = G.call("JOBS_TICK", timed=True) - base
    return out


# --------------------------------------------------------------------------
# ΑΡΝΗΤΙΚΑ
# --------------------------------------------------------------------------
def negatives(sym):
    G = Game(sym)
    m = G.m
    w = lambda a: [a & 255, a >> 8]
    out = []

    def at0(label, name, n, pat, edits, test):
        hits = TD.find(m.read_ram(sym[name], n), sym[name], pat)
        out.append((label, [(hits[0] + k, v) for k, v in edits] if len(hits) == 1 else None, test))

    mo, sb, mt, ma = sym["MC_ORDER"], sym["SP_BUILD"], sym["MC_TAIL"], sym["MC_ARRIVE"]
    at0("το FIT χωρίς εργασίες", "FIT_SET", 120, [0xCD] + w(mo), [(0, 0), (1, 0), (2, 0)], "fit")
    at0("χωρίς το «αν δεν υπάρχει ήδη»", "MCO_ONE", 6, [0xC8], [(0, 0)], "fit")
    at0("θόλος σε λειτουργία ως εργοτάξιο", "SPA_SITE", 16, [0xC2] + w(ma),
        [(0, 0), (1, 0), (2, 0)], "deliver")
    at0("καμία Build για τη μηχανή", "MCA_GOT", 40, [0xC4] + w(sb), [(0, 0), (1, 0), (2, 0)],
        "deliver")
    at0("Build και σε εργοτάξιο", "MCA_GOT", 40, [0xCB, 0x4E, 0x28], [(2, 0), (3, 0)], "deliver")
    at0("το εργοτάξιο πληρώθηκε, η εργασία τελειώνει", "SPA_PAID", 12, [0xC3] + w(mt),
        [(0, 0xAF), (1, 0x3C), (2, 0xC9)], "deliver")
    at0("στήσιμο χωρίς υλικά", "JABI_LP", 8, [0xE6, 0x83], [(1, 0x80)], "install")
    at0("η Build δεν στήνει ποτέ", "JAB_INST", 6, [0xFE, 64], [(1, 0)], "install")
    ag2 = (TO.layout()["G_agent_fields"] >> 8) + 2
    at0("ο χτίστης μένει έξω όταν τελειώνει το κτίριο", "JABI_GO", 12, [0x26, ag2, 0x71],
        [(2, 0)], "site")
    at0("παραγωγή με «υγεία όχι μηδέν»", "ERD_LP", 24, [0xCB, 0x7E, 0xC4],
        [(0, 0x34), (1, 0x35)], "stopped")
    at0("χειριστής με «υγεία όχι μηδέν»", "JN_LP", 16, [0xDD, 0xCB, 8, 0x7E],
        [(1, 0x7E), (2, 8), (3, 0xB7)], "stopped")
    at0("βλάβη με «υγεία όχι μηδέν»", "EC_BREAK_D", 60, [0xDD, 0xCB, 16, 0x7E, 0xC8],
        [(1, 0x7E), (2, 16), (3, 0xB7)], "stopped")
    return out


def run_negative(sym, g, patch, test):
    if test == "fit":
        return fit(sym, g, patch, quiet=True)
    if test == "site":
        return chain_site(sym, g, patch, quiet=True, frames=6000)
    return {"deliver": deliver, "install": install, "stopped": stopped}[test](
        sym, patch, quiet=True)


def main():
    sym, g = TG.build()
    shots = [a for a in sys.argv[1:] if a.endswith(".png")]
    # Από το βήμα 108 και το install.asm στην τράπεζα 2: τα 68 bytes του στην
    # τράπεζα 0 τα πήραν τα διαστήματα των θόλων (src/span.asm).
    check(sym["MC_ARRIVE"] >= 0x9C00 and sym["MC_ORDER"] >= 0x9C00,
          f"το mc_arrive (#{sym['MC_ARRIVE']:04X}) και το mc_order (#{sym['MC_ORDER']:04X}) "
          f"στο page2")
    for fn, what in ((deliver, "ΦΟΡΤΙΟ: οκτώ σκηνές, σε θόλο σε λειτουργία και σε εργοτάξιο"),
                     (install, "ΣΤΗΣΙΜΟ: επίσκεψη προς επίσκεψη, και το κτίριο που τελειώνει"),
                     (stopped, "ΣΤΑΜΑΤΗΜΕΝΗ: παραγωγή, χειριστής, επισκευή, βλάβη")):
        err = fn(sym)
        check(err is None, err or what)
    err = fit(sym, g)
    check(err is None, err or "FIT: τέσσερις μηχανές, υγεία 7, δύο Supply")
    err = chain(sym, g, shots=shots[:2] or None)
    check(err is None, err or "ΑΛΥΣΙΔΑ: η μηχανή κουβαλήθηκε και στήθηκε από τον μηχανικό")
    err = chain_site(sym, g)
    check(err is None, err or "ΑΛΥΣΙΔΑ ΣΕ ΕΡΓΟΤΑΞΙΟ: ο χτίστης βγήκε, ξαναμπήκε και τη στήθηκε")
    for k, v in cost(sym).items():
        check(v <= COST[k], f"{k}: {v} us (ταβάνι {COST[k]})")
    for label, patch, test in negatives(sym):
        if patch is None:
            check(False, f"ΑΡΝΗΤΙΚΟ «{label}»: το μοτίβο δεν βρέθηκε μία φορά")
            continue
        err = run_negative(sym, g, patch, test)
        check(err is not None, f"ΑΡΝΗΤΙΚΟ «{label}»: {err or 'ΔΕΝ ΠΙΑΣΤΗΚΕ'}")
    if FAIL:
        print(f"\n{len(FAIL)} ΑΠΟΤΥΧΙΕΣ")
        sys.exit(1)
    print("\nΟΛΑ ΚΑΛΑ")


if __name__ == "__main__":
    main()
