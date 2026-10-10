#!/usr/bin/env python3
"""Τα αγαθά του εμπόρου κουβαλιούνται (βήμα 98, DESIGN §6.11).

Η πρόζα — οι αποφάσεις του παίκτη, όπως στο Planetbase:

  ΣΥΜΦΩΝΙΑ   (tests/test_trade.py) όσα δίνεις φεύγουν από τα αποθέματα στο
             FIRE, και χρωστιούνται στον έμπορο σε φορτία ως δέκα μονάδες ενός
             αγαθού (EC_MARKUP)· όσα παίρνεις μένουν στο πλοίο του (οι
             ποσότητες του EC_CARGO). Δύο εργασίες J_TRADE στην πίστα,
             αδιάθετες, προτεραιότητα 4, άδειες. Ο έμπορος περιμένει (SK_DEALT,
             EC_SHETA #FFFF).
  ΦΟΡΤΙΟ     της ΕΡΓΑΣΙΑΣ, στο J_SITE της: 0 άδεια, #0F ένα για τον έμπορο,
             ποσότητα x 16 + απόθεμα ένα δικό του. Οχι του πράκτορα.
  ΣΤΗΝ ΠΙΣΤΑ ό,τι φέρνει μένει εκεί· παίρνει από το πλοίο, από την πρώτη θέση
             του φορτίου με κάτι ακόμη, ως δέκα μονάδες, και πάει στο
             κοντινότερο σκάφος ή αποθήκη — και άδειος, αν χρωστιούνται κι άλλα
             στον έμπορο.
  ΣΕ ΑΠΟΘΗΚΗ ένα φορτίο του εμπόρου μπαίνει στα αποθέματα, με το ταβάνι των 600·
             παίρνει ένα για τον έμπορο αν χρωστιέται, και πάει στην πίστα — και
             άδειος, αν μένει κάτι στο πλοίο του.
  ΧΩΡΙΣ      σκάφος ή αποθήκη που να φτάνεται, το φορτίο παραδίδεται στην πίστα.
  ΜΙΣΟΔΡΟΜΙΣ όποιος αφήνει μια J_TRADE — πεθαίνει, πάει για ανάγκη — την αφήνει
             ανοιχτή με το φορτίο της και τον προορισμό της: ο επόμενος συνεχίζει.
             Ενα για τον έμπορο που φτάνει σε αποθήκη συνεχίζει για την πίστα.
  ΧΩΡΙΣ ΠΙΣΤΑ (ένας μετεωρίτης τη ρίχνει: EC_PADNODE 255) όποιος θα πήγαινε εκεί
             μένει όπου είναι, με την εργασία και το φορτίο της.
  ΤΕΛΟΣ      χωρίς τίποτα από καμία μεριά η εργασία κλείνει· οι άλλες J_TRADE
             χωρίς πράκτορα και χωρίς φορτίο σβήνουν, και αν δεν μένει καμία, ο
             έμπορος φεύγει στην επόμενη περιστροφή (EC_SHETA 0).
  ΠΟΙΟΙ      όλοι οι άποικοι και τα ρομπότ μεταφοράς (job_roles #5F).
  ΑΛΥΣΙΔΑ    στο παιχνίδι που τρέχει, όπως σε νέο παιχνίδι: το σκάφος, και μια
             πίστα που χτίζει ο παίκτης. Συμφωνία από τη γραμμή του εμπόρου, και
             οι μεταφορείς κουβαλούν ως το τέλος· τα αποθέματα ανεβαίνουν ανά
             φορτίο, και ο έμπορος φεύγει μόνο μετά το τελευταίο.
  ΚΟΣΤΟΣ     η θέση 13 με μια άφιξη στην πίστα, σε αποθήκη και στο τέλος, κάτω
             από τα ταβάνια COST.

ΣΤΙΣ ΣΚΗΝΕΣ Η «ΠΙΣΤΑ» ΕΙΝΑΙ ΤΟ AIRLOCK της αποικίας δοκιμών (κόμβος 65) και το
σκάφος η πλατφόρμα της (δομή 0, κόμβος 64), όπως στο tests/test_haul.py: η
αποικία δεν έχει αποθήκη, και το sp_take ξέρει σκάφος μόνο στη δομή 0. Μόνο η
θέση 13 τρέχει εκεί· στο παιχνίδι που τρέχει το πέρασμα δωματίων ξαναβρίσκει
την πίστα, οπότε η αλυσίδα χτίζει μία. Ο γύρος περνά έξω, με στολές.

Αρνητικά, με τον κώδικα πειραγμένο στη μνήμη: η J_TRADE ως Supply· η πίστα
ως αποθήκη· ποτέ σκάφος· χωρίς το «ως δέκα»· το φορτίο του εμπόρου δεν
μπαίνει στα αποθέματα· κανένα για τον έμπορο· ένα αφημένο για τον έμπορο
ξαναπληρώνεται· το μάζεμα γυρίζει τη J_TRADE· σβήνουν εργασίες με φορτίο· ο
έμπορος φεύγει ενώ άλλος κουβαλά· ο έμπορος δεν φεύγει ποτέ· χωρίς πίστα,
στον κόμβο 255.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import test_haul as TH                                   # noqa: E402
import test_trade as TT                                  # noqa: E402
import test_drill as TD                                  # noqa: E402
import balance as B                                      # noqa: E402
import econ as EC                                        # noqa: E402
import cpc                                               # noqa: E402

FAIL = []
J_TRADE, J_SUPPLY, NO_JOB = EC.J_TRADE, EC.J_SUPPLY, 255
LOAD, GIVE, JOBS, PRIO = 10, 0x0F, 2, 4
SK_MERCHANT, SK_DEALT, LANDED = 1, 3, 2
K_SHIP, K_PAD, ST_KIND = EC.K_SHIP, EC.K_PAD, EC.ST_KIND
S = EC
F_ALIVE, F_WORKING = 1, 32
PAD, SHIP, WHO = 65, 64, 1
CAP = 600


def check(ok, msg):
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ ") + msg)
    if not ok:
        FAIL.append(msg)


def load(n, g):
    return n << 4 | g


class Game(TH.Game):
    """Το colony.sna σε παύση, με τον έμπορο μετά τη συμφωνία."""

    def __init__(self, sym, patch=(), patch6=()):
        super().__init__(sym, patch, patch6)
        self.EC = TT.econ_at()

    # τα βοηθητικά της γραμμής του εμπόρου (tests/test_trade.py)
    stock, set_stock, merchant, here, r34, open = (TT.Game.stock, TT.Game.set_stock,
                                                    TT.Game.merchant, TT.Game.here,
                                                    TT.Game.r34, TT.Game.open)

    def ec(self, name):
        return self.m.peek(self.EC[name])

    def cargo(self):
        return list(self.m.read_ram(self.EC["EC_CARGO"], 8))

    def dealt(self, owed, cargo):
        """Ο έμπορος μετά τη συμφωνία, με την «πίστα» στο airlock."""
        self.merchant(markup=owed, cargo=cargo, eta=0xFFFF)
        self.m.poke(self.EC["EC_SHKIND"], SK_DEALT)
        self.m.poke(self.EC["EC_PADNODE"], PAD)

    def trades(self):
        return [self.job(j) for j in range(32) if self.job(j)[0] == J_TRADE]


# --------------------------------------------------------------------------
# ΠΙΝΑΚΕΣ
# --------------------------------------------------------------------------
def tables(sym):
    m = Game(sym).m
    roles = m.peek(sym["JOB_ROLES"] + J_TRADE)
    if roles != 0x5F or EC.JOB_ROLES[J_TRADE] != 0x5F \
            or (EC.TRADE_LOAD, EC.TRADE_GIVE, EC.TRADE_JOBS, EC.SK_DEALT) != (LOAD, GIVE, JOBS, SK_DEALT):
        return (f"ΠΙΝΑΚΕΣ: J_TRADE ρόλοι #{roles:02X}, αναφορά #{EC.JOB_ROLES[J_TRADE]:02X}, "
                f"φορτίο/για τον έμπορο/εργασίες/είδος {EC.TRADE_LOAD}/{EC.TRADE_GIVE:#x}/"
                f"{EC.TRADE_JOBS}/{EC.SK_DEALT} — η πρόζα λέει #5F, 10/#0F/2/3")
    return None


# --------------------------------------------------------------------------
# ΑΦΙΞΗ — η θέση 13 με μια J_TRADE, σκηνή προς σκηνή
# --------------------------------------------------------------------------
CARGO = [(S.S_METAL, 25), (S.S_PROC, 6)]


def scene(sym, patch=(), at=PAD, ld=0, owed=2, cargo=CARGO, ship=True, alive=True,
          to=None, task=True):
    G = Game(sym, patch)
    G.b6[G.st + ST_KIND] = K_SHIP if ship else K_PAD
    G.dealt(owed, cargo)
    j = G.free_job()
    G.put_job(j, [J_TRADE, at if to is None else to, WHO, PRIO, ld])
    G.ag_set(WHO, flags=F_ALIVE if alive else 0, node=at, dest=at if to is None else to,
             edge=255, task=j if task else 255)
    G.set_stock({S.S_METAL: 100, S.S_PROC: 0})
    return G, j


def flat(cargo):
    return [v for p in cargo for v in p] + [0] * (8 - 2 * len(cargo))


def arrive(sym, patch=(), quiet=False):
    """ΑΦΙΞΗ. Η πρώτη διαφορά, ή None."""
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))

    def look(G, j):
        return (G.job(j), G.ag_get(WHO, "dest"), G.ag_get(WHO, "task"), G.ec("EC_MARKUP"),
                G.cargo(), G.stock(S.S_METAL), G.stock(S.S_PROC), G.w16(G.EC["EC_SHETA"]))

    # (i) στην πίστα, άδεια: δέκα μέταλλα από το πλοίο, προς το σκάφος
    G, j = scene(sym, patch)
    G.call("JOBS_TICK")
    want = ([J_TRADE, SHIP, WHO, PRIO, load(10, S.S_METAL)], SHIP, j, 2,
            flat([(S.S_METAL, 15), (S.S_PROC, 6)]), 100, 0, 0xFFFF)
    if look(G, j) != want:
        return f"ΣΤΗΝ ΠΙΣΤΑ: {look(G, j)} — η πρόζα λέει {want}"
    # (ii) στο σκάφος με τα δέκα: +10, και ένα για τον έμπορο
    G, j = scene(sym, patch, at=SHIP, ld=load(10, S.S_METAL), cargo=[(S.S_METAL, 15), (S.S_PROC, 6)])
    G.call("JOBS_TICK")
    want = ([J_TRADE, PAD, WHO, PRIO, GIVE], PAD, j, 1,
            flat([(S.S_METAL, 15), (S.S_PROC, 6)]), 110, 0, 0xFFFF)
    if look(G, j) != want:
        return f"ΣΤΟ ΣΚΑΦΟΣ: {look(G, j)} — η πρόζα λέει {want}"
    # (iii) στην πίστα με ένα για τον έμπορο, τα μέταλλα τελειωμένα: οι έξι
    # επεξεργαστές, όλοι
    G, j = scene(sym, patch, ld=GIVE, owed=1, cargo=[(S.S_METAL, 0), (S.S_PROC, 6)])
    G.call("JOBS_TICK")
    want = ([J_TRADE, SHIP, WHO, PRIO, load(6, S.S_PROC)], SHIP, j, 1,
            flat([(S.S_METAL, 0), (S.S_PROC, 0)]), 100, 0, 0xFFFF)
    if look(G, j) != want:
        return f"ΤΟ ΕΠΟΜΕΝΟ ΑΓΑΘΟ: {look(G, j)} — η πρόζα λέει {want}"
    say("ΓΥΡΟΣ: στην πίστα 10 από τα 25 μέταλλα και προς το σκάφος· εκεί +10 και "
        "ένα φορτίο για τον έμπορο (2 -> 1) προς την πίστα· εκεί, με τα μέταλλα "
        "τελειωμένα, και οι 6 επεξεργαστές")
    # (iv) το τέλος: στο σκάφος με τους επεξεργαστές, τίποτα άλλο
    G, j = scene(sym, patch, at=SHIP, ld=load(6, S.S_PROC), owed=0, cargo=[(S.S_PROC, 0)])
    G.call("JOBS_TICK")
    got = look(G, j)
    if G.trades() or got[6] != 6 or got[7] != 0:
        return (f"ΤΕΛΟΣ: εργασίες J_TRADE {G.trades()}, επεξεργαστές {got[6]}, EC_SHETA "
                f"{got[7]:#x} — η πρόζα λέει η εργασία κλείνει, +6, EC_SHETA 0")
    G.call("SHIP_TICK")
    if G.ec("EC_SHSTATE") != 0:
        return f"ΤΕΛΟΣ: μετά το ship_tick το πλοίο είναι ακόμη {G.ec('EC_SHSTATE')}"
    say("ΤΕΛΟΣ: +6 επεξεργαστές, η εργασία κλείνει, EC_SHETA 0, και το ship_tick "
        "παίρνει τον έμπορο")
    # (v) στο σκάφος άδειος, τίποτα για τον έμπορο, κάτι στο πλοίο του
    G, j = scene(sym, patch, at=SHIP, owed=0, cargo=[(S.S_METAL, 5)])
    G.call("JOBS_TICK")
    want = ([J_TRADE, PAD, WHO, PRIO, 0], PAD, j, 0, flat([(S.S_METAL, 5)]), 100, 0, 0xFFFF)
    if look(G, j) != want:
        return f"ΑΔΕΙΟΣ ΠΡΟΣ ΤΗΝ ΠΙΣΤΑ: {look(G, j)} — η πρόζα λέει {want}"
    # (vi) στην πίστα, τίποτα στο πλοίο, ένα ακόμη για τον έμπορο
    G, j = scene(sym, patch, ld=GIVE, owed=1, cargo=[(S.S_METAL, 0)])
    G.call("JOBS_TICK")
    want = ([J_TRADE, SHIP, WHO, PRIO, 0], SHIP, j, 1, flat([(S.S_METAL, 0)]), 100, 0, 0xFFFF)
    if look(G, j) != want:
        return f"ΑΔΕΙΟΣ ΠΡΟΣ ΤΟ ΣΚΑΦΟΣ: {look(G, j)} — η πρόζα λέει {want}"
    say("ΑΔΕΙΟΣ: χωρίς τίποτα για τον έμπορο στην πίστα, για ό,τι μένει στο πλοίο του· "
        "χωρίς τίποτα στο πλοίο του στο σκάφος, για ό,τι του χρωστιέται")
    # (vii) οι άλλες: μία με πράκτορα, μία ανοιχτή άδεια, μία ανοιχτή με φορτίο
    G, j = scene(sym, patch, ld=GIVE, owed=0, cargo=[])
    k1, k2, k3 = [k for k in range(32) if G.job(k)[0] == NO_JOB and k != j][:3]
    G.put_job(k1, [J_TRADE, SHIP, 2, PRIO, load(10, S.S_METAL)])
    G.ag_set(2, task=k1)
    G.put_job(k2, [J_TRADE, PAD, 255, PRIO, 0])
    G.put_job(k3, [J_TRADE, SHIP, 255, PRIO, load(5, S.S_PROC)])
    G.call("JOBS_TICK")
    got = [G.job(k)[0] == J_TRADE for k in (j, k1, k2, k3)] + [G.job(k3)[4],
                                                                G.w16(G.EC["EC_SHETA"])]
    want = [False, True, False, True, load(5, S.S_PROC), 0xFFFF]
    if got != want:
        return (f"ΟΙ ΑΛΛΕΣ: είδη αυτής/με πράκτορα/ανοιχτής άδειας/ανοιχτής με φορτίο "
                f"J_TRADE {got[:4]}, φορτίο {got[4]:#x}, EC_SHETA {got[5]:#x} — η πρόζα "
                f"λέει {want}")
    G, j = scene(sym, patch, ld=GIVE, owed=0, cargo=[])
    k2 = [k for k in range(32) if G.job(k)[0] == NO_JOB and k != j][0]
    G.put_job(k2, [J_TRADE, PAD, 255, PRIO, 0])
    G.call("JOBS_TICK")
    if G.trades() or G.w16(G.EC["EC_SHETA"]) != 0:
        return (f"ΟΙ ΑΛΛΕΣ: με μία ανοιχτή άδεια εργασίες {G.job(j)}, {G.job(k2)}, EC_SHETA "
                f"{G.w16(G.EC['EC_SHETA']):#x} — η πρόζα λέει σβήνουν και οι δύο, EC_SHETA 0")
    say("ΟΙ ΑΛΛΕΣ: στο τέλος μιας, η ανοιχτή άδεια σβήνει, η ανοιχτή με φορτίο και αυτή "
        "με πράκτορα μένουν, και ο έμπορος περιμένει· χωρίς αυτές φεύγει")
    # (viii) χωρίς σκάφος: το φορτίο παραδίδεται στην πίστα, και ένα για τον έμπορο
    G, j = scene(sym, patch, ship=False)
    G.call("JOBS_TICK")
    want = ([J_TRADE, PAD, WHO, PRIO, GIVE], PAD, j, 1,
            flat([(S.S_METAL, 15), (S.S_PROC, 6)]), 110, 0, 0xFFFF)
    if look(G, j) != want:
        return f"ΧΩΡΙΣ ΣΚΑΦΟΣ: {look(G, j)} — η πρόζα λέει {want}"
    # (ix) το ταβάνι
    G, j = scene(sym, patch, at=SHIP, ld=load(10, S.S_METAL))
    G.set_stock({S.S_METAL: 595})
    G.call("JOBS_TICK")
    if G.stock(S.S_METAL) != CAP:
        return f"ΤΑΒΑΝΙ: 595 + 10 μέταλλα = {G.stock(S.S_METAL)} — η πρόζα λέει {CAP}"
    say("ΧΩΡΙΣ ΣΚΑΦΟΣ: τα 10 μέταλλα παραδίδονται στην πίστα (100 -> 110) και παίρνει "
        "ένα για τον έμπορο· ΤΑΒΑΝΙ: 595 + 10 = 600")
    # (x) μισοδρομίς: ο φορτωμένος πάει για ανάγκη (task 255), κανείς άλλος
    # ελεύθερος — η εργασία μένει ανοιχτή, προς το σκάφος, με το φορτίο της
    for dead in (False, True):
        G, j = scene(sym, patch, at=PAD, to=SHIP, ld=load(10, S.S_METAL), task=dead,
                     alive=not dead)
        G.ag_set(WHO, node=100)                     # μακριά, και απασχολημένος
        G.ag_set(WHO, flags=G.ag_get(WHO, "flags") | F_WORKING)
        for i in range(80):
            if i != WHO and G.ag_get(i, "flags") & F_ALIVE:
                G.ag_set(i, flags=G.ag_get(i, "flags") | F_WORKING)
        G.call("JOBS_TICK")
        want = [J_TRADE, SHIP, 255, PRIO, load(10, S.S_METAL)]
        if G.job(j) != want:
            return (f"ΜΙΣΟΔΡΟΜΙΣ ({'νεκρός' if dead else 'για ανάγκη'}): εργασία {G.job(j)} — "
                    f"η πρόζα λέει {want}")
    # (xi) ένα αφημένο για τον έμπορο φτάνει σε αποθήκη: συνεχίζει, χωρίς άλλο
    G, j = scene(sym, patch, at=SHIP, ld=GIVE, owed=1, cargo=[(S.S_METAL, 5)])
    G.call("JOBS_TICK")
    want = ([J_TRADE, PAD, WHO, PRIO, GIVE], PAD, j, 1, flat([(S.S_METAL, 5)]), 100, 0, 0xFFFF)
    if look(G, j) != want:
        return f"ΑΦΗΜΕΝΟ ΓΙΑ ΤΟΝ ΕΜΠΟΡΟ: {look(G, j)} — η πρόζα λέει {want}"
    say("ΜΙΣΟΔΡΟΜΙΣ: για ανάγκη ή νεκρός, η εργασία μένει ανοιχτή προς το σκάφος με τα "
        "10 μέταλλα· ένα για τον έμπορο σε αποθήκη συνεχίζει, και δεν χρωστιέται άλλο")
    # (xii) χωρίς πίστα: στο σκάφος, με ένα για τον έμπορο ή με ένα δικό του
    for ld, owed, want_ld, want_owed, metal in ((GIVE, 1, GIVE, 1, 100),
                                                (load(10, S.S_METAL), 2, GIVE, 1, 110)):
        G, j = scene(sym, patch, at=SHIP, ld=ld, owed=owed, cargo=[(S.S_METAL, 5)])
        G.m.poke(G.EC["EC_PADNODE"], 255)
        G.call("JOBS_TICK")
        want = ([J_TRADE, SHIP, WHO, PRIO, want_ld], SHIP, j, want_owed, flat([(S.S_METAL, 5)]),
                metal, 0, 0xFFFF)
        if look(G, j) != want:
            return f"ΧΩΡΙΣ ΠΙΣΤΑ: {look(G, j)} — η πρόζα λέει {want}"
    say("ΧΩΡΙΣ ΠΙΣΤΑ: στο σκάφος με ένα για τον έμπορο μένει εκεί· με ένα δικό του το "
        "παραδίδει, παίρνει ένα για τον έμπορο, και μένει")
    return None


# --------------------------------------------------------------------------
# ΑΛΥΣΙΔΑ — στο παιχνίδι που τρέχει, από τη γραμμή του εμπόρου ως την αναχώρηση
# --------------------------------------------------------------------------
def chain(sym, g, patch=(), quiet=False):
    """ΑΛΥΣΙΔΑ. Η πρώτη διαφορά, ή None."""
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G = Game(sym, patch)
    m = G.m
    # όπως σε νέο παιχνίδι: η πλατφόρμα της αποικίας δοκιμών γίνεται το σκάφος,
    # και ο παίκτης χτίζει πίστα (το 10ο του καταλόγου, 45 μέταλλα)
    G.b6[G.st + ST_KIND] = K_SHIP
    G.set_stock({S.S_METAL: 200, S.S_ORE: 120, S.S_PROC: 0})
    tx, ty = B.clear_spots(4, 1)[0]
    B.build(m, sym, 10, g + 6, at=(2 * tx + 4, 2 * ty + 4), fit=False)
    k = next((k for k in range(1, 32) if G.rec(k)[ST_KIND] == K_PAD), None)
    if k is None:
        return f"ΑΛΥΣΙΔΑ: η πίστα δεν μπήκε στο ({tx}, {ty})"
    pad = 64 + k
    m.poke(sym["UI_SPD"], 4)

    def run(cond, limit, step=10):
        t = 0
        while t < limit and not cond():
            G.s16(G.g + 28, 30000)          # ρεύμα: η μπαταρία γεμάτη
            m.run_frames(step)
            t += step
        return t

    t = run(lambda: G.ec("EC_PADNODE") == pad, 40000, 50)
    if G.ec("EC_PADNODE") != pad:
        return f"ΑΛΥΣΙΔΑ: η πίστα (κόμβος {pad}) δεν χτίστηκε σε {t} frames"
    say(f"ΠΙΣΤΑ: χτίστηκε στο ({tx}, {ty}), κόμβος {pad}, σε {t} frames (x4)")
    G.set_stock({S.S_ORE: 120, S.S_METAL: 100, S.S_PROC: 0})
    G.merchant(markup=47, cargo=[(S.S_METAL, 20), (S.S_PROC, 6), (S.S_BOT, 2)], eta=300)
    # μετά την τοποθέτηση η διεπαφή μένει στο PLACE: το fire 2, όπως το B.build
    for _ in range(2):
        G.stick(0x20)
    if not G.open():
        return f"ΑΛΥΣΙΔΑ: η γραμμή του εμπόρου δεν άνοιξε (κατάσταση {G.state()})"
    # 10 μέταλλα (2 x 5, 22 το ένα) και 2 επεξεργαστές (59) για 40 μεταλλεύματα:
    # 338 για 400. Η σειρά: μέταλλο, επεξεργαστές, ρομπότ, τρόφιμα, μετάλλευμα
    for key in [TT.UP, TT.UP, TT.RIGHT, TT.UP] + [TT.RIGHT] * 3 + [TT.DOWN] * 4:
        G.tap(key)
    jobs0 = G.trades()
    G.tap(cpc.KEY_SPACE)
    m.run_frames(4)
    tj = [j for j in range(32) if G.job(j)[0] == J_TRADE and G.job(j) not in jobs0]
    got = (G.stock(S.S_ORE), G.stock(S.S_METAL), G.stock(S.S_PROC), G.ec("EC_MARKUP"),
           G.cargo(), G.ec("EC_SHKIND"), G.ec("EC_SHSTATE"), G.w16(G.EC["EC_SHETA"]))
    want = (80, 100, 0, 4, flat([(S.S_METAL, 10), (S.S_PROC, 2), (S.S_BOT, 0)]), SK_DEALT,
            LANDED, 0xFFFF)
    # οι δύο μπορεί να τις πήραν ήδη: ο πράκτορας και ο προορισμός αλλάζουν. Και το
    # EC_SHETA, εδώ που το παιχνίδι τρέχει, μετρά ήδη περιστροφές από το #FFFF.
    if got[:7] != want[:7] or got[7] < 0xFF00 or len(tj) != JOBS or any(G.job(j)[0] != J_TRADE or G.job(j)[3] != PRIO
                                             for j in tj):
        return f"ΣΥΜΦΩΝΙΑ: {got}, J_TRADE {[G.job(j) for j in tj]} — η πρόζα λέει {want}"
    say("ΣΥΜΦΩΝΙΑ: 40 μεταλλεύματα φεύγουν (4 φορτία για τον έμπορο), 10 μέταλλα και 2 "
        "επεξεργαστές μένουν στο πλοίο του, δύο J_TRADE στην πίστα, ο έμπορος περιμένει")
    t, events, who = 0, [], set()
    last = (G.stock(S.S_METAL), G.stock(S.S_PROC), G.stock(S.S_ORE))
    while t < 60000 and G.ec("EC_SHSTATE"):
        G.s16(G.g + 28, 30000)
        m.run_frames(10)
        t += 10
        now = (G.stock(S.S_METAL), G.stock(S.S_PROC), G.stock(S.S_ORE))
        for j in tj:
            if G.job(j)[0] == J_TRADE and G.job(j)[2] != 255:
                who.add(G.job(j)[2])
        if now != last:
            events.append((t, now[0] - last[0], now[1] - last[1], now[2] - last[2],
                           G.ec("EC_SHSTATE")))
            last = now
    if G.ec("EC_SHSTATE"):
        return (f"ΑΛΥΣΙΔΑ: σε {t} frames ο έμπορος δεν έφυγε — φορτία {events}, εργασίες "
                f"{G.trades()}, χρωστιούνται {G.ec('EC_MARKUP')}, πλοίο του {G.cargo()}")
    gains = [(dm, dp) for _, dm, dp, _, _ in events if dm > 0 or dp > 0]
    if sorted(gains) != [(0, 2), (10, 0)] or G.trades() or any(e[4] != LANDED for e in events):
        return (f"ΑΛΥΣΙΔΑ: φορτία {events} (frames, μέταλλα, επεξεργαστές, μεταλλεύματα, "
                f"πλοίο), εργασίες {G.trades()} — η πρόζα λέει +10 μέταλλα και +2 επεξεργαστές, "
                f"με τον έμπορο εδώ, και καμία J_TRADE στο τέλος")
    say(f"ΑΛΥΣΙΔΑ: οι {sorted(who)} κουβάλησαν: " + ", ".join(
        f"+{dm or dp} {'μέταλλα' if dm else 'επεξεργαστές'} στο frame {f}"
        for f, dm, dp, _, _ in events if dm > 0 or dp > 0)
        + f" (x4)· ο έμπορος έφυγε στο {t}, καμία J_TRADE")
    return None


# --------------------------------------------------------------------------
# ΚΟΣΤΟΣ
# --------------------------------------------------------------------------
# Πάνω από μια θέση 13 χωρίς εργασία. Η άφιξη στην πίστα περνά από το sp_take.
# Μετρημένα στο βήμα 98: 330, 261 και 799 us. Το τέλος σαρώνει τις 32 εργασίες
# (tra_bye), μία φορά ανά έμπορο.
COST = {"θέση 13, στην πίστα": 360, "θέση 13, στο σκάφος": 290, "θέση 13, το τέλος": 880}


def cost(sym):
    out = {}
    G, j = scene(sym)
    G.put_job(j, [255] * 5)
    G.ag_set(WHO, task=255)
    base = G.call("JOBS_TICK", timed=True)
    G, j = scene(sym)
    out["θέση 13, στην πίστα"] = G.call("JOBS_TICK", timed=True) - base
    G, j = scene(sym, at=SHIP, ld=load(10, S.S_METAL))
    out["θέση 13, στο σκάφος"] = G.call("JOBS_TICK", timed=True) - base
    G, j = scene(sym, at=SHIP, ld=load(6, S.S_PROC), owed=0, cargo=[(S.S_PROC, 0)])
    out["θέση 13, το τέλος"] = G.call("JOBS_TICK", timed=True) - base
    return out


# --------------------------------------------------------------------------
# ΑΡΝΗΤΙΚΑ
# --------------------------------------------------------------------------
def negatives(sym):
    G = Game(sym)
    m = G.m
    w = lambda a: [a & 255, a >> 8]
    out = []

    def at0(label, name, n, pat, edits):
        hits = TD.find(m.read_ram(sym[name], n), sym[name], pat)
        out.append((label, [(hits[0] + k, v) for k, v in edits] if len(hits) == 1 else None))

    tra = sym["TR_ARRIVE"]
    # sp_arrive: cp J_TRADE · jp z,tr_arrive -> nop
    at0("η J_TRADE ως Supply", "SP_ARRIVE", 8, [0xFE, J_TRADE, 0xCA] + w(tra),
        [(2, 0), (3, 0), (4, 0)])
    # tr_arrive: cp c · jr z,tra_pad -> nop nop
    at0("η πίστα ως αποθήκη", "TR_ARRIVE", 12, [0xB9, 0x28], [(1, 0), (2, 0)])
    # tra_tk: call sp_take · pop hl · jp z,tra_store -> jp
    at0("ποτέ σκάφος", "TR_ARRIVE", 200, [0xCD] + w(sym["SP_TAKE"]) + [0xE1, 0xCA], [(4, 0xC3)])
    # trk_got: sub TRADE_LOAD -> sub 0
    at0("χωρίς το «ως δέκα»", "TR_ARRIVE", 200, [0xD6, LOAD, 0x30], [(1, 0)])
    # tra_store: call ec_add_stock -> nop
    at0("το φορτίο του εμπόρου δεν μπαίνει", "TR_ARRIVE", 100, [0xCD] + w(sym["EC_ADD_STOCK"]),
        [(0, 0), (1, 0), (2, 0)])
    # tra_e: ld (hl),TRADE_GIVE -> ld (hl),0
    at0("κανένα για τον έμπορο", "TR_ARRIVE", 100, [0x36, GIVE], [(1, 0)])
    # tra_store: cp TRADE_GIVE · jr z,tra_go -> nop nop
    at0("ένα αφημένο για τον έμπορο ξαναπληρώνεται", "TR_ARRIVE", 30, [0xFE, GIVE, 0x28],
        [(2, 0), (3, 0)])
    # jr_free: cp J_TRADE · jr z,jr_pop -> nop nop
    at0("το μάζεμα γυρίζει τη J_TRADE", "JB_REAP", 80, [0xFE, J_TRADE, 0x28], [(2, 0), (3, 0)])
    # tra_bye: or (hl) -> nop
    at0("σβήνουν εργασίες με φορτίο", "TRA_BYE", 40, [0x3C, 0x20, 0x01, 0xB6], [(3, 0)])
    # tra_bye: dec c · jr nz,trb_out -> nop nop
    at0("φεύγει ενώ άλλος κουβαλά", "TRA_BYE", 60, [0x0D, 0x20], [(1, 0), (2, 0)])
    # tra_bye: ld (EC_SHETA),hl -> nop
    eta = G.EC["EC_SHETA"]
    at0("δεν φεύγει ποτέ", "TRA_BYE", 60, [0x22] + w(eta), [(0, 0), (1, 0), (2, 0)])
    # tra_go: ld a,(EC_PADNODE) · inc a · ret z -> nop
    pad = G.EC["EC_PADNODE"]
    at0("χωρίς πίστα, στον κόμβο 255", "TR_ARRIVE", 200, [0x3A] + w(pad) + [0x3C, 0xC8],
        [(4, 0)])
    return out


def main():
    sym, g = TG.build()

    why = tables(sym)
    check(why is None, why or "πίνακες: J_TRADE για όλους τους αποίκους και τα ρομπότ "
          "μεταφοράς, φορτίο 10, #0F για τον έμπορο, δύο εργασίες, SK_DEALT 3")

    why = arrive(sym)
    check(why is None, why or "άφιξη: πίστα, σκάφος, άδειος, τέλος, οι άλλες, χωρίς σκάφος, "
          "ταβάνι, μισοδρομίς")

    why = chain(sym, g)
    check(why is None, why or "αλυσίδα: συμφωνία, μεταφορά ως το τέλος, αναχώρηση")

    got = cost(sym)
    check(all(got[k] <= COST[k] for k in COST),
          "κόστος: " + ", ".join(f"{k} {got[k]} us (ταβάνι {COST[k]})" for k in COST))

    for name, patch in negatives(sym):
        if patch is None:
            check(False, f"ΑΡΝΗΤΙΚΟ «{name}»: το σημείο δεν βρέθηκε μία φορά")
            continue
        why = arrive(sym, patch, quiet=True)
        check(why is not None, f"ΑΡΝΗΤΙΚΟ «{name}»: " + (why or "ΔΕΝ το έπιασε τίποτα"))

    print()
    print("ΟΛΑ ΟΚ" if not FAIL else f"{len(FAIL)} ΑΠΟΤΥΧΙΕΣ")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
