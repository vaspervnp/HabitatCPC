#!/usr/bin/env python3
"""Η γεώτρηση (βήμα 94, DESIGN §6.7, §6.5, §6.11).

Η πρόζα — οι αποφάσεις του παίκτη, όπως στο Planetbase:

  ΣΚΑΒΟΥΝ    ως τρεις σε κάθε ορυχείο (MINE_OPS), εργάτες ή ρομπότ γεώτρησης:
             η εργασία Drill, που υπήρχε στους πίνακες από την αρχή (ρόλοι
             #81, προτεραιότητα 4) και δεν τη δημοσίευε τίποτα.
  ΡΥΘΜΟΣ     μετάλλευμα ανά κύκλο ροής, με ρεύμα: κανείς 0, ένας 2 — όσο ως το
             93 χωρίς κανέναν —, δύο 3, τρεις 4: το 100, 150, 200% του
             Planetbase. Το ρεύμα του (8) το τρώει ούτως ή άλλως. ΑΠΟ ΤΟ ΒΗΜΑ
             95 ΣΤΟΝ ΣΩΡΟ του ορυχείου (ST_OWED), όχι στα αποθέματα: εκεί το
             βάζει η μεταφορά (tests/test_haul.py)· και «με ρεύμα» είναι το
             ρεύμα του τελευταίου ισοζυγίου (EC_POK), όπως για τις μηχανές.
  ΕΡΓΑΣΙΑ    στο σάρωμα του κύκλου ροής: κάθε έτοιμο ορυχείο με λιγότερους από
             τρεις έχει ΜΙΑ εργασία Drill — κόμβος 64 + δομή, αδιάθετη,
             προτεραιότητα 4, εργοτάξιο ο ίδιος κόμβος — στην πρώτη ελεύθερη
             θέση του πίνακα, ακόμη και χωρίς ρεύμα, και το bit 7 του ST_OPS
             του λέει ότι υπάρχει, ως να φτάσει κάποιος. Κανένα εργοτάξιο,
             καμία άλλη δομή· με τον πίνακα γεμάτο, τίποτα, ούτε το bit. Ο
             κύκλος μετρά και τα έτοιμα ορυχεία (EC_MINES).
  ΜΕΤΡΗΜΑ    όποιος φτάνει με Drill στέκεται εκεί με F_WORKING και το έβδομο
             byte του ορυχείου (ST_OPS) ανεβαίνει· όταν φύγει — η στολή γυρίζει
             τον άνθρωπο πίσω — ή πεθάνει, κατεβαίνει.
  ΡΟΜΠΟΤ     ένα νέο ρομπότ είναι γεώτρησης όσο οι θέσεις, 3 x EC_MINES, είναι
             περισσότερες από τα ζωντανά γεωτρύπανα· αλλιώς κατασκευής ή
             μεταφοράς, όπως στο 92. Και τα δύο ίδια με την αναφορά.
  ΑΛΥΣΙΔΑ    στο παιχνίδι που τρέχει: ένα ορυχείο στη φλέβα δίπλα στην αποικία,
             χτισμένο από τον μηχανικό, παίρνει εργάτη, ρίχνει 2 ανά κύκλο στον
             σωρό όσο σκάβει εκείνος και τίποτα όταν τον γυρίσει η στολή· όποιος πεθάνει
             εκεί κατεβάζει το μέτρημα· ένα ρομπότ γεώτρησης που ξυπνά πάει και
             μένει.
  ΑΝΑΘΕΣΗ    μια Drill μένει ανοιχτή όσο το ορυχείο έχει θέση και δεν έρχεται
             εργάτης. Ως το 93 η ανάθεση, με ΜΙΑ αδιάθετη εργασία, έτρεχε το
             jb_best (~1 ms) για κάθε αδρανή από τους 32 που κοιτάζει, όποιος
             κι αν ήταν ο ρόλος του· τώρα μόνο όσοι έχουν ρόλο στη μάσκα των
             ανοιχτών (jb_open, src/drill.asm). Στη θέση 13 του σεναρίου
             ταυτότητας του tests/test_sim.py: 363 ms στα 640 ticks στο 93,
             982 με τη γεώτρηση χωρίς μάσκα, 292 τώρα.
  ΚΟΣΤΟΣ     ο κύκλος ροής με τρία ορυχεία (0, 2, 3 που σκάβουν) — και στις
             τρεις τελευταίες θέσεις του πίνακα, στο ίδιο ταβάνι —, η θέση 12
             χωρίς κύκλο, η θέση 13 — χωρίς ανοιχτή εργασία, και με μια Drill
             που δεν την παίρνει κανείς, χωρίς αδρανή στο παράθυρο και με
             αδρανείς άλλου ρόλου —, και το ξύπνημα ρομπότ, κάτω από τα ταβάνια
             COST: της θέσης 13 κάτω από όσο κόστιζαν στο 93.

Αρνητικά, με τον κώδικα πειραγμένο στη μνήμη: χωρίς δημοσίευση· τα ορυχεία
αμέτρητα· βγάζει χωρίς κανέναν, όπως ως το 93· ένας βγάζει 1· τέσσερις στο
ορυχείο· χωρίς το bit 7 (το σάρωμα των εργασιών σε κάθε κύκλο)· το bit που δεν
σβήνει στην άφιξη· η άφιξη, η αναχώρηση, ο θάνατος που δεν μετρούν· το μέτρημα
στο όγδοο byte· πάντα κατασκευής ή μεταφοράς· τα νεκρά γεωτρύπανα που
μετρούν· μία θέση ανά ορυχείο· η ανάθεση χωρίς τη μάσκα των ρόλων· μια μάσκα
που δεν μαζεύει κανέναν ρόλο.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import test_bots as TB                                   # noqa: E402
import balance as B                                      # noqa: E402
import econ as EC                                        # noqa: E402
import entity as E                                       # noqa: E402

FAIL = []
MINE_OPS, J_DRILL, RL_DRILL, RL_WORKER = 3, EC.J_DRILL, EC.RL_DRILL, 0
K_MINE, K_SOLAR, DS_BUILDING, DS_ACTIVE = EC.K_MINE, EC.K_SOLAR, 1, 2
ST_OPS, ST_OWED = EC.ST_OPS, EC.ST_OWED
OUT = {0: 0, 1: 2, 2: 3, 3: 4}                       # ο ρυθμός της πρόζας
# Μισά tiles: το 4x4 (-11..-8, -3..0), δύο tiles από τη φλέβα που στρώνει το
# colony.sna (tools/balance.py, COLONY_VEIN). Ως το βήμα 131 (-10, -8), στη
# φλέβα της δύσης όπως ήταν με πλατό 5.
MINE_AT = (-18, -2)
EC_MINES_OFS = 106
DRILL_PRIO, DRILL_LOW, ST_DLOW = EC.DRILL_PRIO, EC.DRILL_LOW, EC.ST_DLOW   # βήμα 126


def check(ok, msg):
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ ") + msg)
    if not ok:
        FAIL.append(msg)


class Game(TB.Game):
    """Το colony.sna σε παύση, με ό,τι χρειάζεται η γεώτρηση."""

    def __init__(self, sym, patch=(), patch6=()):
        super().__init__(sym, patch, patch6)
        self.g = self.EC["EC_STOCK"]
        self.st = self.L["G_struct_tbl"] - 0x4000
        self.jt = self.L["G_job_tbl"]

    def rec(self, k):
        return [self.b6[self.st + 8 * k + j] for j in range(8)]

    def put_rec(self, k, v):
        for j, b in enumerate(v):
            self.b6[self.st + 8 * k + j] = b

    def jobs(self):
        return bytes(self.m.read_ram(self.jt, 160))

    def ore(self):
        return self.w16(self.g + 2 * EC.S_ORE)

    def mines(self):
        return self.m.peek(self.g + EC_MINES_OFS)


# --------------------------------------------------------------------------
# ΠΙΝΑΚΕΣ
# --------------------------------------------------------------------------
def tables(sym):
    m = Game(sym).m
    roles = m.peek(sym["JOB_ROLES"] + J_DRILL)
    prio = m.peek(sym["JOB_PRIO"] + J_DRILL)
    if (roles, prio) != (0x81, 4) or (EC.JOB_ROLES[J_DRILL], EC.JOB_PRIO[J_DRILL]) != (0x81, 4) \
            or EC.MINE_OPS != MINE_OPS:
        return (f"ΠΙΝΑΚΕΣ: Drill ρόλοι #{roles:02X}, προτεραιότητα {prio}, αναφορά "
                f"#{EC.JOB_ROLES[J_DRILL]:02X}/{EC.JOB_PRIO[J_DRILL]}/{EC.MINE_OPS} — η πρόζα "
                f"λέει #81 (εργάτης, γεωτρύπανο), 4, τρεις")
    return None


# --------------------------------------------------------------------------
# ΡΟΗ — ο κύκλος με ορυχεία, απέναντι στην πρόζα και στην αναφορά
# --------------------------------------------------------------------------
# (δομή, εγγραφή): τέσσερα έτοιμα ορυχεία με 0-3 που σκάβουν, ένα εργοτάξιο
# ορυχείου, ένα ηλιακό με το έβδομο byte 1
SCENE = [(5, [-30, 20, K_MINE, 0, DS_ACTIVE, 255, 0, 0]),
         (6, [-24, 20, K_MINE, 0, DS_ACTIVE, 255, 1, 0]),
         (7, [-18, 20, K_MINE, 0, DS_ACTIVE, 255, 2, 0]),
         (8, [-12, 20, K_MINE, 0, DS_ACTIVE, 255, 3, 0]),
         (9, [-6, 20, K_MINE, 0, DS_BUILDING, 0, 0, 0]),
         (10, [0, 30, K_SOLAR, 0, DS_ACTIVE, 255, 1, 0])]


def ref_flow(G):
    """Ο κύκλος της αναφοράς πάνω στην ίδια κατάσταση: (μετάλλευμα, ορυχεία,
    πίνακας εργασιών), και ο πίνακας δομών."""
    e = EC.Econ()
    for k in range(14):
        e.stock[k] = G.w16(G.g + 2 * k)
    e.power_store = G.w16(G.g + 28)
    e.power_ok = G.m.peek(G.g + 46)                     # EC_POK: το τελευταίο ισοζύγιο
    e.mach_power = G.w16(G.g + 36)
    e.ess_power = G.w16(G.g + 82)
    e.day, e.wind, e.storm = G.m.peek(G.g + 49), G.m.peek(G.g + 50), G.m.peek(G.g + 61)
    e.struct = bytearray(G.b6[G.st:G.st + 256])
    e.job = bytearray(G.jobs())
    EC.flow_cycle(e)
    return (e.stock[EC.S_ORE], e.mines, bytes(e.job)), bytes(e.struct)


def cycle(G):
    G.m.poke(G.sym["EC_FDIV"], 1)
    return G.call("ECON_FLOW")


def flow(sym, patch=(), patch6=(), quiet=False):
    """ΡΟΗ. Η πρώτη διαφορά, ή None."""
    for power in (True, False):
        G = Game(sym, patch, patch6)
        for k, v in SCENE:
            G.put_rec(k, [b & 255 for b in v])
        # ΤΟ ΡΕΥΜΑ ΤΟΥ ΤΕΛΕΥΤΑΙΟΥ ΙΣΟΖΥΓΙΟΥ γεμίζει τους σωρούς (βήμα 95,
        # hl_pile): το EC_POK. Η μπαταρία κάνει το ισοζύγιο αυτού του κύκλου
        # ίδιο, για τον δεύτερο.
        G.m.poke(G.g + 46, EC.POWER_ALL if power else EC.POWER_NONE)
        G.s16(G.g + 28, 30000 if power else 0)          # EC_PSTORE: η μπαταρία
        ore0, jobs0 = G.ore(), G.jobs()
        (want_ore, want_mines, want_jobs), want_st = ref_flow(G)
        if cycle(G) is None:
            return "ΡΟΗ: το econ_flow δεν τερμάτισε"
        got = (G.ore(), G.mines(), G.jobs())
        ops = [G.rec(k)[ST_OPS] for k, _ in SCENE]
        piles = [G.rec(k)[ST_OWED] for k, _ in SCENE]
        # η πρόζα: 2 + 3 + 4 με ρεύμα στους σωρούς, τρεις εργασίες για τις δομές 5, 6, 7:
        # η 5 χωρίς κανέναν στο DRILL_PRIO, η 6 και η 7, που κάποιος σκάβει ήδη,
        # στο DRILL_LOW με το ST_DLOW (βήμα 126)
        free = [j for j in range(32) if jobs0[5 * j] == 255][:3]
        prose = bytearray(jobs0)
        for j, k, pr in zip(free, (5, 6, 7), (DRILL_PRIO, DRILL_LOW, DRILL_LOW)):
            prose[5 * j:5 * j + 5] = bytes([J_DRILL, 64 + k, 255, pr, 64 + k])
        want_p = (ore0, 4, bytes(prose))
        want_piles = [OUT[n] if power else 0 for n in (0, 1, 2, 3)] + [0, 0]
        if got != want_p or ops != [0x80, 0x91, 0x92, 3, 0, 1] or piles != want_piles:
            return (f"ΡΟΗ ({'με' if power else 'χωρίς'} ρεύμα): μετάλλευμα {ore0} -> {got[0]}, "
                    f"σωροί {piles}, EC_MINES {got[1]}, ST_OPS {[hex(v) for v in ops]}, νέες εργασίες "
                    f"{[list(got[2][5 * j:5 * j + 5]) for j in range(32) if got[2][5 * j:5 * j + 5] != jobs0[5 * j:5 * j + 5]]}"
                    f" — η πρόζα λέει μετάλλευμα {ore0}, σωροί {want_piles}, 4, ST_OPS 80 91 92 3 0 1, "
                    f"Drill για τους 69 (4), 70 και 71 (2)")
        if got != (want_ore, want_mines, want_jobs) or bytes(G.b6[G.st:G.st + 256]) != want_st:
            return "ΡΟΗ: ο Z80 διαφέρει από την αναφορά (tools/econ.py, flow_cycle)"
        # ένας δεύτερος κύκλος: καμία διπλή, και φτηνός (το bit 7)
        jobs1 = G.jobs()
        cycle(G)
        if G.jobs() != jobs1 or [G.rec(k)[ST_OWED] for k, _ in SCENE] != [2 * v for v in want_piles]:
            return "ΡΟΗ: ο δεύτερος κύκλος ξαναδημοσίευσε Drill, ή δεν έβγαλε τα ίδια"
    # ο πίνακας γεμάτος: τίποτα, και τίποτα δεν χαλάει
    G = Game(sym, patch, patch6)
    for k, v in SCENE:
        G.put_rec(k, [b & 255 for b in v])
    full = bytes([EC.J_OPERATE, 0, 255, 3, 0] * 32)
    G.m.write_ram(G.jt, full)
    cycle(G)
    if G.jobs() != full or [G.rec(k)[ST_OPS] for k in (5, 6, 7)] != [0, 1, 2]:
        return "ΡΟΗ: με τον πίνακα γεμάτο κάτι γράφτηκε, ή μπήκε το bit 7"
    if not quiet:
        print(f"    ΡΟΗ: ορυχεία με 0-3 που σκάβουν ρίχνουν 0, 2, 3, 4 στους σωρούς τους με ρεύμα, 0 χωρίς· "
              f"μία Drill για καθένα κάτω από τρεις, με ή χωρίς ρεύμα — στο 4 χωρίς κανέναν, "
              f"στο 2 με το ST_DLOW αν κάποιος ήδη σκάβει (βήμα 126) — καμία για το "
              f"εργοτάξιο και το ηλιακό, καμία διπλή, τίποτα με τον πίνακα γεμάτο· "
              f"EC_MINES 4· όπως η αναφορά")
    return None


# --------------------------------------------------------------------------
# ΧΑΜΗΛΑ (βήμα 126) — ο δεύτερος και ο τρίτος κάτω από τις μηχανές
# --------------------------------------------------------------------------
# (δομή, ST_OPS, η Drill του στον πίνακα: προτεραιότητα ή None): ένα ορυχείο
# που άδειασε με τη Drill του χαμηλά, ένα με δύο που σκάβουν και τη δική του
# χαμηλά, ένα με έναν και τη δική του χαμηλά, ένα άδειο με τα bits αλλά χωρίς
# εργασία (τη σκούπισε κάτι άλλο: σβήνουν και τα δύο), κι ένα άδειο με τη
# Drill του στο 4.
LOW = [(5, 0x90, DRILL_LOW), (6, 0x92, DRILL_LOW), (7, 0x91, DRILL_LOW), (8, 0x90, None),
       (9, 0x80, DRILL_PRIO)]


def low(sym, patch=(), patch6=(), quiet=False):
    """ΧΑΜΗΛΑ. Ο κύκλος ροής: η Drill του άδειου ορυχείου πίσω στο 4 και το
    ST_DLOW σβηστό, οι άλλες όπως ήταν· όπως η αναφορά. Μετά η άφιξη (jb_arrive):
    ένας εργάτης φτάνει με τη χαμηλή Drill, και το ST_OPS μένει μόνο ο μετρητής.
    Η πρώτη διαφορά, ή None."""
    G = Game(sym, patch, patch6)
    jobs = bytearray(G.jobs())
    free = [j for j in range(32) if jobs[5 * j] == 255]
    at = {}
    for (k, ops, pr), j in zip(LOW, free):
        G.put_rec(k, [(-30 + 6 * (k - 5)) & 255, 20, K_MINE, 0, DS_ACTIVE, 255, ops, 0])
        if pr is not None:
            jobs[5 * j:5 * j + 5] = bytes([J_DRILL, 64 + k, 255, pr, 64 + k])
            at[k] = j
    G.m.write_ram(G.jt, bytes(jobs))
    G.s16(G.g + 28, 30000)
    G.m.poke(G.g + 46, EC.POWER_ALL)
    (_, _, want_jobs), want_st = ref_flow(G)
    if cycle(G) is None:
        return "ΧΑΜΗΛΑ: το econ_flow δεν τερμάτισε"
    got = G.jobs()
    ops = {k: G.rec(k)[ST_OPS] for k, _, _ in LOW}
    prio = {k: got[5 * j + 3] for k, j in at.items()}
    want_ops = {5: 0x80, 6: 0x92, 7: 0x91, 8: 0x00, 9: 0x80}
    want_prio = {5: DRILL_PRIO, 6: DRILL_LOW, 7: DRILL_LOW, 9: DRILL_PRIO}
    if ops != want_ops or prio != want_prio:
        return (f"ΧΑΜΗΛΑ: ST_OPS {[hex(ops[k]) for k in sorted(ops)]}, προτεραιότητες "
                f"{prio} — η πρόζα λέει 80 92 91 00 80 και {want_prio}")
    if got != want_jobs or bytes(G.b6[G.st:G.st + 256]) != want_st:
        return "ΧΑΜΗΛΑ: ο Z80 διαφέρει από την αναφορά (tools/econ.py, flow_cycle)"
    # η άφιξη: ένας εργάτης στον κόμβο της χαμηλής Drill της 7, εκτός σωλήνα
    j = at[7]
    w = next(i for i in range(80) if G.b6[G.ag + i] & 1 and G.b6[G.ag + 128 + i] == RL_WORKER)
    for b in range(32):                                 # καμία άλλη εργασία του w
        if got[5 * b + 2] == w:
            G.m.poke(G.jt + 5 * b + 2, 255)
    G.m.poke(G.jt + 5 * j + 2, w)
    G.b6[G.ag + 256 + w] = 64 + 7                       # node
    G.b6[G.ag + 640 + w] = 255                          # edge: έξω από τον σωλήνα
    G.b6[G.ag + 896 + w] = j                            # task
    G.b6[G.ag + w] &= ~32 & 255
    G.call("JB_ARRIVE")
    after = G.rec(7)[ST_OPS]
    if after != 0x02 or G.jobs()[5 * j] != 255 or not G.b6[G.ag + w] & 32:
        return (f"ΑΦΙΞΗ ΧΑΜΗΛΑ: ST_OPS #{after:02X}, η εργασία {list(G.jobs()[5 * j:5 * j + 5])}, "
                f"F_WORKING {bool(G.b6[G.ag + w] & 32)} — η πρόζα λέει 02 (δύο, χωρίς το bit 7 "
                f"και το ST_DLOW), καμία εργασία, F_WORKING")
    if not quiet:
        print(f"    ΧΑΜΗΛΑ: ο κύκλος ροής ξαναπηγαίνει στο 4 τη Drill του ορυχείου που άδειασε "
              f"(ST_OPS 90 -> 80), σβήνει και το bit 7 χωρίς εργασία (90 -> 00), και αφήνει στο 2 όσες έχουν "
              f"κάποιον να σκάβει· όπως η αναφορά. Η άφιξη με τη χαμηλή Drill: ST_OPS 91 -> 02")
    return None


# --------------------------------------------------------------------------
# ΡΟΜΠΟΤ — ποιο είδος ξυπνά (θέσεις 80-95, ζωντανό/νεκρό γεωτρύπανο)
# --------------------------------------------------------------------------
# (όνομα, EC_MINES, ζωντανά γεωτρύπανα, νεκρά γεωτρύπανα, άλλα ζωντανά, τι
# λέει η πρόζα: (ταυτότητα, ρόλος))
ROLE_CASES = (
    ("κανένα ορυχείο", 0, [], [], [], (80, EC.RL_CBOT)),
    ("ένα ορυχείο, κανένα γεωτρύπανο", 1, [], [], [], (80, RL_DRILL)),
    ("ένα ορυχείο, ένα γεωτρύπανο", 1, [80], [], [], (81, RL_DRILL)),
    ("ένα ορυχείο, τρία γεωτρύπανα", 1, [80, 81, 82], [], [], (83, EC.RL_CARRY)),
    ("ένα ορυχείο, δύο ζωντανά κι ένα νεκρό", 1, [80, 81], [82], [], (82, RL_DRILL)),
    ("δύο ορυχεία, τρία γεωτρύπανα", 2, [81, 82, 83], [], [80], (84, RL_DRILL)),
)


def roles(sym, patch=(), patch6=(), quiet=False):
    """ΡΟΜΠΟΤ. Η πρώτη διαφορά, ή None."""
    G = Game(sym, patch, patch6)
    for name, mines, drills, dead, others, want in ROLE_CASES:
        TB.setup_rule(G, 1, [(1, 0, 0)], drills + others, 0)
        for i in drills + dead:
            G.b6[G.ag + 128 + i] = RL_DRILL
        G.m.poke(G.g + EC_MINES_OFS, mines)
        a = E.Agents().from_bytes(bytes(G.b6[G.ag:G.ag + 2048]))
        e = EC.Econ()
        e.stock[EC.S_BOT] = 1
        e.mines = mines
        e.dome = bytearray(G.b6[G.dome:G.dome + 64 * 24])
        e.room_n = bytearray(G.m.read_ram(G.L["G_room_n"], 12))
        e.room_list = bytearray(G.m.read_ram(G.L["G_room_list"], 96))
        occ = bytearray(G.b6[G.occ:G.occ + 128])
        ref = EC.bot_tick(e, a, occ)
        if G.call("BOT_TICK") is None:
            return f"ΡΟΜΠΟΤ «{name}»: το bot_tick δεν τερμάτισε"
        i, role = want
        got = (G.b6[G.ag + i] & 1, G.b6[G.ag + 128 + i])
        if got != (1, role):
            return (f"ΡΟΜΠΟΤ «{name}»: το {i} ξύπνησε {bool(got[0])} με ρόλο {got[1]} — η "
                    f"πρόζα λέει ρόλο {role}")
        if (ref, a.role[i]) != (i, role):
            return f"ΡΟΜΠΟΤ «{name}»: η αναφορά λέει {ref} με ρόλο {a.role[ref]}"
    if not quiet:
        print("    ΡΟΜΠΟΤ: " + "; ".join(
            f"{c[0]}: {c[5][0]} {'Γ' if c[5][1] == RL_DRILL else 'Κ' if c[5][1] == EC.RL_CBOT else 'Μ'}"
            for c in ROLE_CASES))
    return None


# --------------------------------------------------------------------------
# ΑΛΥΣΙΔΑ — το ορυχείο στη φλέβα, στο παιχνίδι που τρέχει
# --------------------------------------------------------------------------
def next_cycle(G, ops=lambda: 0, limit=4000, val=None):
    """Τρέχει ως να τρέξει ο επόμενος κύκλος ροής: το ec_fdiv μετρά από 64
    προς τα κάτω και ξαναγεμίζει στο 64 μέσα στον κύκλο. (frames, ops() πριν
    από το frame του κύκλου, μετάλλευμα που μπήκε σε εκείνο και στο επόμενο
    frame), ή None.

    ΚΑΙ ΣΤΟ ΕΠΟΜΕΝΟ: το run_frames(1) σταματά στο όριο του frame, όπου κι αν
    είναι ο Z80, και ο κύκλος μπορεί να ξαναγεμίσει το ec_fdiv πριν από το όριο
    και να βγάλει το μετάλλευμα μετά. Ετσι μετρήθηκαν κύκλοι με δύο που έσκαβαν
    και 0 μετάλλευμα, και ο επόμενος με 6 (η μπαταρία το ίδιο: 0, και μετά
    διπλό). Ο,τι τρέξει μετά τον κύκλο στο δεύτερο frame δεν αλλάζει το
    μετάλλευμα — εδώ δεν το ξοδεύει κανείς."""
    val = val or G.ore
    fd = G.sym["EC_FDIV"]
    prev = G.m.peek(fd)
    for t in range(1, limit + 1):
        o, n = val(), ops()
        G.m.run_frames(1)
        cur = G.m.peek(fd)
        if cur > prev:
            G.m.run_frames(1)
            return t + 1, n, val() - o
        prev = cur
    return None


def chain(sym, g, patch=(), patch6=(), quiet=False, stop=None):
    """ΑΛΥΣΙΔΑ. `stop`: ως ποιο μέρος να φτάσει ('arrive', 'leave', 'death'),
    για τα αρνητικά. Η πρώτη διαφορά, ή None."""
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G = Game(sym, patch, patch6)
    m = G.m
    G.s16(G.g + 2 * EC.S_METAL, 200)
    B.build(m, sym, 8, g + 6, at=MINE_AT, fit=False)
    k = next((k for k in range(32) if G.rec(k)[2] == K_MINE), None)
    if k is None:
        return "ΑΛΥΣΙΔΑ: το ορυχείο δεν μπήκε στη φλέβα"
    node = 64 + k
    m.poke(sym["UI_SPD"], 4)
    t = 0
    while t < 30000 and G.rec(k)[4] != DS_ACTIVE:
        m.run_frames(50)
        t += 50
    if G.rec(k)[4] != DS_ACTIVE:
        return f"ΑΛΥΣΙΔΑ: το ορυχείο δεν χτίστηκε σε {t} frames: {G.rec(k)}"
    say(f"ΑΛΥΣΙΔΑ: το ορυχείο στη φλέβα (κόμβος {node}) χτίστηκε σε {t} frames")
    G.s16(G.g + 28, 30000)                              # ρεύμα: η μπαταρία γεμάτη

    def ops():
        return G.rec(k)[ST_OPS] & 3

    def drillers():
        return [i for i in range(128) if G.b6[G.ag + i] & 1 and G.b6[G.ag + 256 + i] == node
                and G.b6[G.ag + i] & 32 and G.b6[G.ag + 640 + i] == 255]

    # --- κάποιος έρχεται ---
    t = 0
    while t < 20000 and ops() == 0:
        m.run_frames(20)
        t += 20
    who = drillers()
    if ops() != 1 or len(who) != 1 or G.b6[G.ag + 128 + who[0]] != RL_WORKER:
        return (f"ΑΦΙΞΗ: σε {t} frames ST_OPS {ops()}, στο ορυχείο με F_WORKING {who} "
                f"(ρόλοι {[G.b6[G.ag + 128 + i] for i in who]}) — η πρόζα λέει ένας εργάτης")
    w = who[0]
    say(f"ΑΦΙΞΗ: ο εργάτης {w} έφτασε με Drill σε {t} frames: ST_OPS 1, F_WORKING")
    if stop == "arrive":
        return None
    # --- βγάζει 2 ανά κύκλο όσο σκάβει ---
    # --- ο ρυθμός, κύκλο-κύκλο: το μετάλλευμα που μπήκε στη στιγμή του κύκλου
    # (το ec_fdiv ξαναγεμίζει) με όσους έσκαβαν τότε. Ο εργάτης γυρίζει να
    # γεμίσει τη στολή, και ξανάρχεται, οπότε κάποιοι κύκλοι είναι με 0. ---
    # Με ×1: ένα πέρασμα του τροχού ανά frame, οπότε στο frame του κύκλου
    # κανένα άλλο πέρασμα δεν αλλάζει όσους σκάβουν.
    m.poke(sym["UI_SPD"], 1)
    seen, t = {}, 0

    def pile():
        return G.rec(k)[ST_OWED]
    while t < 60000 and not (seen.get(1) and seen.get(0)):
        # ΣΤΟΝ ΣΩΡΟ (βήμα 95), και ο σωρός άδειος πριν από κάθε κύκλο: καμία
        # Haul δεν δημοσιεύεται, κανείς δεν φορτώνει στη μέση, κανένα ταβάνι.
        G.b6[G.st + 8 * k + ST_OWED] = 0
        # ΜΕ ΡΕΥΜΑ: ο σωρός κοιτάζει το ισοζύγιο του ΠΡΟΗΓΟΥΜΕΝΟΥ κύκλου (EC_POK,
        # βήμα 95), που μπορεί να έγινε τη νύχτα, πριν γεμίσει η μπαταρία.
        G.s16(G.g + 28, 30000)
        G.m.poke(G.g + 46, EC.POWER_ALL)
        r = next_cycle(G, ops, val=pile)
        if r is None:
            return "ΡΥΘΜΟΣ: κανένας κύκλος ροής σε 4.000 frames"
        t += r[0]
        seen.setdefault(r[1], set()).add(r[2])
    bad = {n: v for n, v in seen.items() if v != {OUT[n]}}
    if bad or 1 not in seen:
        return f"ΡΥΘΜΟΣ: στον σωρό ανά κύκλο με όσους σκάβουν: {seen} — η πρόζα λέει {OUT}"
    m.poke(sym["UI_SPD"], 4)
    # --- η στολή τον γυρίζει πίσω ---
    t = 0
    while t < 30000 and ops() == 0:
        m.run_frames(20)
        t += 20
    # ΚΑΙ ΑΝ ΣΚΑΒΟΥΝ ΚΙ ΑΛΛΟΙ (βήμα 123): το πρώτο ορυχείο είναι δωρεάν, κανείς
    # δεν κουβαλά υλικά, και ένας δεύτερος εργάτης έρχεται συχνά πριν φύγει ο
    # πρώτος. Ο μετρητής ακολουθεί τους ανθρώπους: όταν φεύγει ο w, ST_OPS =
    # όσοι μένουν.
    w = drillers()[0] if drillers() else w
    while t < 60000 and w in drillers():
        m.run_frames(20)
        t += 20
    a = G.agent(w)
    if (w in drillers() or ops() != len(drillers()) or a["flags"] & 32
            or a["node"] == node and a["edge"] == 255):
        return (f"ΑΝΑΧΩΡΗΣΗ: σε {t} frames ST_OPS {ops()}, στο ορυχείο {drillers()}, "
                f"ο {w}: {a}")
    say(f"ΡΥΘΜΟΣ: στον σωρό ανά κύκλο με όσους σκάβουν {seen}· η στολή γύρισε τον {w} "
        f"πίσω και το ST_OPS έπεσε στους {ops()} που μένουν, F_WORKING σβηστό")
    if stop == "leave":
        return None
    # --- κάποιος (ξανά)έρχεται, και πεθαίνει εκεί ---
    t, there = 0, set(drillers())
    while t < 30000 and not set(drillers()) - there:
        there &= set(drillers())                        # όσοι φεύγουν, φεύγουν
        m.run_frames(20)
        t += 20
    who = sorted(set(drillers()) - there)
    if not who or ops() != len(drillers()):
        return f"ΘΑΝΑΤΟΣ: κανείς δεν ήρθε σε {t} frames (ST_OPS {ops()}, {drillers()})"
    d = who[0]
    # Η ΤΕΛΕΥΤΑΙΑ ΜΟΝΑΔΑ: το su_tick σκοτώνει στο dec 1 -> 0 (jp z,nd_die).
    # Με 0 το dec πήγαινε στο 255 και ο άποικος ζούσε.
    G.b6[G.ag + 1792 + d] = 1
    t = 0
    while t < 2000 and G.b6[G.ag + d] & 1:
        m.run_frames(5)
        t += 5
    if G.b6[G.ag + d] & 1 or d in drillers() or ops() != len(drillers()):
        return (f"ΘΑΝΑΤΟΣ: ο {d} ζει {bool(G.b6[G.ag + d] & 1)}, ST_OPS {ops()}, στο ορυχείο "
                f"{drillers()} — η πρόζα λέει ένας λιγότερος")
    say(f"ΘΑΝΑΤΟΣ: ο {d} ήρθε, η στολή του άδειασε εκεί, και το ST_OPS έπεσε στους "
        f"{ops()} που μένουν")
    if stop == "death":
        return None
    # --- ένα ρομπότ γεώτρησης ξυπνά, πάει και μένει ---
    G.factory(1, 0, 0)
    G.index([1])
    G.set_bots(1)
    t = 0
    while t < 30000 and not [i for i in drillers() if i >= 80]:
        m.run_frames(20)
        t += 20
    who = [i for i in drillers() if i >= 80]
    if not who or G.b6[G.ag + 128 + who[0]] != RL_DRILL:
        return f"ΓΕΩΤΡΥΠΑΝΟ: σε {t} frames στο ορυχείο {drillers()}"
    bot = who[0]
    m.run_frames(6000)
    if bot not in drillers():
        return f"ΓΕΩΤΡΥΠΑΝΟ: το {bot} έφυγε από το ορυχείο σε 6.000 frames"
    say(f"ΓΕΩΤΡΥΠΑΝΟ: το {bot} ξύπνησε γεώτρησης, έφτασε σε {t} frames και 6.000 frames "
        f"αργότερα σκάβει ακόμη (ST_OPS {ops()})")
    return None


# --------------------------------------------------------------------------
# ΚΟΣΤΟΣ
# --------------------------------------------------------------------------
# Μετρημένα στο βήμα 93 (rep94/cost.py, ίδια αποικία): ο κύκλος 1.782 us χωρίς
# ορυχεία και 2.065 με τρία, η θέση 12 χωρίς κύκλο 684, η θέση 13 2.841, το
# ξύπνημα στο πρώτο και στο δεύτερο εργοστάσιο 570 και 699.
# Η θέση 13 στο 93 (rep94/c13.py, ίδια αποικία, ίδια Drill στη θέση): 2.841
# χωρίς ανοιχτή εργασία, 3.864 με τη Drill και κανέναν στο παράθυρο, 6.117 με
# τους 4 αδρανείς της αποικίας μέσα του και τους εργάτες απασχολημένους.
# Βήμα 95 (rep95/cost2.py): ο σωρός στο σάρωμα και το DE που μένει, 1.577 ->
# 1.472 χωρίς ορυχεία, 1.941 -> 1.834 με τρία, 3.841 -> 3.799 ο πρώτος — και
# ίδια με τα τρία στις τρεις τελευταίες θέσεις του πίνακα. Τα ταβάνια ως το 94
# ήταν 1.790, 4.100 και 2.120.
# Βήμα 115: η πόρτα του σαρώματος των χαμένων εργασιών (src/flow.asm: ld a,
# (jb_lost) · or a · call nz,sp_sweep) σε κάθε κύκλο, 8 us — 1.472 -> 1.480,
# 3.799 -> 3.807, 1.834 -> 1.842. Τα τρία ταβάνια του κύκλου +8, όπως στο 111
# για την πόρτα των εισβολέων· ως το 114 ήταν 1.480, 3.810 και 1.840.
# Βήμα 122: η αποθήκη (st_check, src/needs.asm) στην αρχή κάθε κύκλου — το
# άθροισμα των 13 αποθεμάτων και το ec_setfull, χωρίς θόλο Storage σε αυτή τη
# σκηνή — και το ec_full στο hl_pile κάθε ορυχείου: 1.480 -> 1.660, 3.807 ->
# 4.008, 1.842 -> 2.022. Ως το 121 τα ταβάνια ήταν 1.488, 3.818 και 1.848.
# Βήμα 123: η μισή απόδοση εκτός φλέβας (bit ST_HALF στο hl_pile, 8 us σε κάθε
# ορυχείο που σκάβει) — ο πρώτος κύκλος με τρία 4.008 -> 4.026· ως το 122 4.016.
# Βήμα 126: ο δεύτερος και ο τρίτος χαμηλά — το dr_post διαλέγει προτεραιότητα
# και bits (~20 us ανά δημοσίευση) και το hl_pile κοιτάζει για άδειο ορυχείο
# με τη Drill του χαμηλά (cp · call z, 5 us ανά ορυχείο): ο πρώτος 4.026 ->
# 4.076, οι επόμενοι 2.022 -> 2.037. Ως το 125 τα ταβάνια ήταν 4.034, 2.030 και
# 2.030. Το ανέβασμα (dr_raise) μετριέται με τη Drill στην τελευταία θέση του
# πίνακα, το χειρότερο πέρασμα.
# Βήμα 127: το απόθεμα μετάλλου — το ec_keep στο st_check και η πρώτη κλήση
# εισόδου στο ec_setfull, σε κάθε κύκλο: +35 us σε όλους (1.660 -> 1.695,
# 4.076 -> 4.111, 2.037 -> 2.072, 2.530 -> 2.565). Ως το 126 τα ταβάνια ήταν
# 1.668, 4.084, 2.045, 2.045 και 2.538.
# Βήμα 138: και το όριο του βιοπλαστικού — ένα ακόμη άθροισμα στο st_check και η
# πρώτη κλήση από πίνακα τεσσάρων στο ec_setfull, σε κάθε κύκλο: +21 us σε όλους
# (1.700 -> 1.721, 4.116 -> 4.137, 2.077 -> 2.098, 2.570 -> 2.591). Ως το 137 τα
# ταβάνια ήταν 1.703, 4.119, 2.080, 2.080 και 2.573.
COST = {"κύκλος, χωρίς ορυχεία": 1724, "κύκλος, τρία ορυχεία 0/2/3, ο πρώτος": 4140,
        "κύκλος, τρία ορυχεία 0/2/3, ο επόμενος": 2101,
        "κύκλος, τρία ορυχεία στις θέσεις 29-31, ο επόμενος": 2101,
        "κύκλος, τρία ορυχεία, ένα άδειασε με τη Drill χαμηλά": 2594,
        "θέση 12 χωρίς κύκλο": 690, "θέση 13": 2800,
        "θέση 13, Drill ανοιχτή, κανείς στο παράθυρο": 3500,
        "θέση 13, Drill ανοιχτή, αδρανείς άλλου ρόλου": 3650,
        "ξύπνημα, εργοστάσιο 2": 950}
COST13 = [k for k in COST if k.startswith("θέση 13")]


def cost13(sym, patch=()):
    """Η θέση 13 στην αποικία δοκιμών (4 ζωντανοί, όλοι αδρανείς): χωρίς ανοιχτή
    εργασία· με μια Drill σε μια δομή και το παράθυρο της ανάθεσης (EC_JAGENT)
    στο 32-63, όπου δεν είναι κανείς· και στο 0-31, με τους εργάτες
    απασχολημένους (F_WORKING), ώστε κανείς από τους αδρανείς να μην την παίρνει."""
    out = {}
    G = Game(sym, patch)
    out["θέση 13"] = G.call("JOBS_TICK", timed=True) - G.probe([], timed=True)
    for label, window in (("κανείς στο παράθυρο", 32), ("αδρανείς άλλου ρόλου", 0)):
        G = Game(sym, patch)
        for i in range(128):
            if G.b6[G.ag + i] & 1 and G.b6[G.ag + 128 + i] in (RL_WORKER, RL_DRILL):
                G.b6[G.ag + i] |= 32
        k = G.jobs()[::5].index(255)
        G.m.write_ram(G.jt + 5 * k, bytes([J_DRILL, 64 + 5, 255, 4, 0]))
        G.m.poke(G.g + 57, window)                          # EC_JAGENT
        out[f"θέση 13, Drill ανοιχτή, {label}"] = \
            G.call("JOBS_TICK", timed=True) - G.probe([], timed=True)
        if G.jobs()[5 * k:5 * k + 3] != bytes([J_DRILL, 69, 255]):
            out[f"θέση 13, Drill ανοιχτή, {label}"] = 99999   # την πήρε κάποιος
    return out


def cost(sym):
    out = {}
    G = Game(sym)
    G.m.poke(sym["EC_FDIV"], 1)
    out["κύκλος, χωρίς ορυχεία"] = G.call("ECON_FLOW", timed=True) - G.probe([], timed=True)
    # Ο ΠΡΩΤΟΣ δημοσιεύει δύο Drill (το 0 και το 2)· ο ΕΠΟΜΕΝΟΣ τις βρίσκει
    # από το bit 7 χωρίς να ψάξει τον πίνακα.
    G = Game(sym)
    for j, n in enumerate([0, 2, 3]):
        G.put_rec(5 + j, [(-30 + 6 * j) & 255, 20, K_MINE, 0, DS_ACTIVE, 255, n, 0])
    for label in ("ο πρώτος", "ο επόμενος"):
        G.m.poke(sym["EC_FDIV"], 1)
        out[f"κύκλος, τρία ορυχεία 0/2/3, {label}"] = \
            G.call("ECON_FLOW", timed=True) - G.probe([], timed=True)
    # ΟΙ ΤΕΛΕΥΤΑΙΕΣ ΘΕΣΕΙΣ (βήμα 95): ένα δεύτερο σάρωμα για τους σωρούς θα
    # πλήρωνε κάθε θέση ως το τελευταίο ορυχείο, ~400 us εδώ.
    G = Game(sym)
    for j, n in enumerate([0, 2, 3]):
        G.put_rec(29 + j, [(-30 + 6 * j) & 255, 20, K_MINE, 0, DS_ACTIVE, 255, n, 0])
    for _ in range(2):
        G.m.poke(sym["EC_FDIV"], 1)
        t = G.call("ECON_FLOW", timed=True) - G.probe([], timed=True)
    out["κύκλος, τρία ορυχεία στις θέσεις 29-31, ο επόμενος"] = t
    # ΤΟ ΑΝΕΒΑΣΜΑ (βήμα 126): τα τρία ορυχεία μετά τον πρώτο κύκλο, ο μόνος του
    # ορυχείου με τους δύο έχει φύγει, και η χαμηλή του Drill είναι στην
    # τελευταία θέση του πίνακα: το dr_raise περνά και τις 32 εργασίες.
    G = Game(sym)
    for j, n in enumerate([0x80, 0x90, 3]):
        G.put_rec(5 + j, [(-30 + 6 * j) & 255, 20, K_MINE, 0, DS_ACTIVE, 255, n, 0])
    jobs = bytearray(G.jobs())
    free = [j for j in range(32) if jobs[5 * j] == 255]
    jobs[5 * free[0]:5 * free[0] + 5] = bytes([J_DRILL, 69, 255, DRILL_PRIO, 69])
    last = 31 if jobs[5 * 31] == 255 else free[-1]
    jobs[5 * last:5 * last + 5] = bytes([J_DRILL, 70, 255, DRILL_LOW, 70])
    G.m.write_ram(G.jt, bytes(jobs))
    G.m.poke(sym["EC_FDIV"], 1)
    t = G.call("ECON_FLOW", timed=True) - G.probe([], timed=True)
    out["κύκλος, τρία ορυχεία, ένα άδειασε με τη Drill χαμηλά"] = \
        t if G.jobs()[5 * last + 3] == DRILL_PRIO else 99999
    G = Game(sym)
    G.m.poke(sym["EC_FDIV"], 2)
    out["θέση 12 χωρίς κύκλο"] = G.call("ECON_FLOW", timed=True) - G.probe([], timed=True)
    out.update(cost13(sym))
    G = Game(sym)
    G.factory(3)
    G.factory(4, robots_at=2)
    G.index([3, 4])
    G.m.poke(G.g + EC_MINES_OFS, 1)
    G.set_bots(1)
    out["ξύπνημα, εργοστάσιο 2"] = G.call("BOT_TICK", timed=True) - G.probe([], timed=True)
    return out


# --------------------------------------------------------------------------
# ΑΡΝΗΤΙΚΑ
# --------------------------------------------------------------------------
def find(data, lo, pat):
    return [lo + k for k in range(len(data) - len(pat) + 1) if list(data[k:k + len(pat)]) == pat]


def negatives(sym, g):
    """[(όνομα, αλλαγές στη μνήμη ή None, στην τράπεζα 6;, ποια δοκιμή)]: κάθε
    μοτίβο πρέπει να βρεθεί ακριβώς μία φορά."""
    G = Game(sym)
    m = G.m
    w = lambda a: [a & 255, a >> 8]
    out = []

    def at6(label, name, n, pat, edits, test):
        lo = sym[name] - 0x4000
        hits = find(bytes(G.b6[lo:lo + n]), sym[name], pat)
        out.append((label, [(hits[0] + k, v) for k, v in edits] if len(hits) == 1 else None,
                    True, test))

    def at0(label, name, n, pat, edits, test):
        hits = find(m.read_ram(sym[name], n), sym[name], pat)
        out.append((label, [(hits[0] + k, v) for k, v in edits] if len(hits) == 1 else None,
                    False, test))

    # call c,dr_post στο σάρωμα της θέσης 12 -> nop
    at6("χωρίς δημοσίευση", "ECON_FLOW", 200, [0xDC] + w(sym["DR_POST"]),
        [(0, 0), (1, 0), (2, 0)], "flow")
    # ld hl,EC_MINES · inc (hl) -> nop
    at6("τα ορυχεία αμέτρητα", "ECON_FLOW", 200, [0x21] + w(g + EC_MINES_OFS) + [0x34],
        [(3, 0)], "flow")
    # hl_pile (βήμα 95, src/haul.asm): and MINE_OPS · jr z,hlp_pile · inc a
    hits = find(m.read_ram(sym["HL_PILE"], 40), sym["HL_PILE"], [0xE6, MINE_OPS, 0x28])
    ok = len(hits) == 1 and m.peek(hits[0] + 4) == 0x3C
    # το jr z -> nop nop: κανείς σκάβει και βγάζει, όπως ως το 93
    out.append(("βγάζει χωρίς κανέναν, όπως ως το 93",
                [(hits[0] + 2, 0), (hits[0] + 3, 0)] if ok else None, False, "flow"))
    # το inc a -> nop: ένας βγάζει 1
    out.append(("ένας βγάζει 1", [(hits[0] + 4, 0)] if ok else None, False, "flow"))
    # cp MINE_OPS -> cp 4
    at6("τέσσερις στο ορυχείο", "ECON_FLOW", 200, [0xFE, MINE_OPS, 0xDC], [(1, 4)], "flow")
    # dr_post: ld a,DRILL_PRIO · ld c,#80 -> ld c,0: κανένα bit, το σάρωμα των
    # εργασιών σε κάθε κύκλο (βήμα 95: το bit το γράφει το st_post από τον C)
    at0("χωρίς το bit 7", "DR_POST", 24, [0x3E, DRILL_PRIO, 0x0E, 0x80], [(3, 0)], "flow")
    # dr_post: ld a,DRILL_LOW -> ld a,DRILL_PRIO: όλοι στο 4, όπως ως το 125
    at0("όλοι στο 4", "DR_POST", 24, [0x3E, DRILL_LOW, 0x0E, 0x80 | ST_DLOW], [(1, DRILL_PRIO)],
        "flow")
    # hl_pile: cp #90 · call z,dr_raise -> nop: το άδειο ορυχείο περιμένει χαμηλά
    at0("κανένα ανέβασμα", "HL_PILE", 12, [0xFE, 0x80 | ST_DLOW, 0xCC] + w(sym["DR_RAISE"]),
        [(2, 0), (3, 0), (4, 0)], "low")
    # dr_raise: ld (hl),DRILL_PRIO -> DRILL_LOW
    at6("το ανέβασμα μένει στο 2", "DR_RAISE", 50, [0x36, DRILL_PRIO, 0xC9], [(1, DRILL_LOW)],
        "low")
    # dr_raise: res 7,(ix+ST_OPS) χωρίς εργασία -> nop
    at6("χωρίς εργασία, το bit 7 μένει", "DR_RAISE", 50, [0xDD, 0xCB, ST_OPS, 0xBE, 0xC9],
        [(0, 0), (1, 0), (2, 0), (3, 0)], "low")
    # ja_oper: res ST_DLOW,(hl) -> nop nop
    at0("η άφιξη κρατά το ST_DLOW", "JA_OPER", 12, [0xCB, 0xBE, 0xCB, 0xA6], [(2, 0), (3, 0)],
        "low")
    # ja_oper: res 7,(hl) -> nop nop: η Drill «υπάρχει» για πάντα
    at0("το bit που δεν σβήνει στην άφιξη", "JA_OPER", 10, [0x34, 0xCB, 0xBE],
        [(1, 0), (2, 0)], "death")
    # ja_oper: ld a,c · call op_ptr · inc (hl) -> nop
    at0("η άφιξη δεν μετρά", "JA_OPER", 8, [0x79, 0xCD] + w(sym["OP_PTR"]) + [0x34],
        [(4, 0)], "arrive")
    # entity: call op_ptr · dec (hl) -> nop
    at0("η αναχώρηση δεν μετρά", "ENT_MOVE_SLICE", 400, [0x3A] + w(sym["EM_NODE"]) + [0xCD]
        + w(sym["OP_PTR"]) + [0x35], [(6, 0)], "leave")
    # nd_die: call op_ptr · dec (hl) -> nop (στο b6code από το βήμα 110)
    at6("ο θάνατος δεν μετρά", "ND_DIE", 40, [0xCD] + w(sym["OP_PTR"]) + [0x35],
        [(3, 0)], "death")
    # opp_st: add a,ST_OPS -> add a,ST_OWED
    at0("το μέτρημα στο όγδοο byte", "OP_PTR", 30, [0xC6, ST_OPS, 0x6F], [(1, 7)], "arrive")
    # bt_make: jr c,bt_role -> nop nop
    at6("πάντα κατασκευής ή μεταφοράς", "BOT_TICK", 220, [0x3E, RL_DRILL, 0x38],
        [(2, 0), (3, 0)], "roles")
    # dr_need: bit 0,(hl) · set 7,l · jr z,drn_bn -> nop nop
    at6("τα νεκρά γεωτρύπανα μετρούν", "DR_NEED", 40, [0xCB, 0x46, 0xCB, 0xFD, 0x28],
        [(4, 0), (5, 0)], "roles")
    # dr_need: add a,a · add a,c -> nop nop: μία θέση ανά ορυχείο
    at6("μία θέση ανά ορυχείο", "DR_NEED", 14, [0x87, 0x81], [(0, 0), (1, 0)], "roles")
    # jb_assign: ld a,(jb_om) · and e · jr z,jas_nx -> nop nop: κάθε αδρανής ψάχνει
    at0("η ανάθεση χωρίς τη μάσκα", "JB_ASSIGN", 120, [0x3A] + w(sym["JB_OM"]) + [0xA3, 0x28],
        [(4, 0), (5, 0)], "cost13")
    # jb_open: ld a,c · or (hl) · ld c,a -> or nop: η μάσκα πάντα 0, κανείς δεν παίρνει τίποτα
    at0("μια μάσκα χωρίς ρόλους", "JB_OPEN", 40, [0x79, 0xB6, 0x4F], [(1, 0)], "arrive")
    return out


def run_negative(sym, g, patch, bank6, test):
    p0, p6 = ((), patch) if bank6 else (patch, ())
    if test == "flow":
        return flow(sym, p0, p6, quiet=True)
    if test == "roles":
        return roles(sym, p0, p6, quiet=True)
    if test == "low":
        return low(sym, p0, p6, quiet=True)
    if test == "cost13":
        got = cost13(sym, p0)
        bad = [f"{k} {got[k]} us (ταβάνι {COST[k]})" for k in COST13 if got[k] > COST[k]]
        return "ΚΟΣΤΟΣ: " + ", ".join(bad) if bad else None
    return chain(sym, g, p0, p6, quiet=True, stop=test)


def main():
    sym, g = TG.build()

    why = tables(sym)
    check(why is None, why or "πίνακες: Drill για εργάτη και γεωτρύπανο, προτεραιότητα 4, ως τρεις")

    why = flow(sym)
    check(why is None, why or "ροή: ρυθμός, εργασίες και ορυχεία όπως η πρόζα και η αναφορά")

    why = low(sym)
    check(why is None, why or "χαμηλά: η Drill του δεύτερου και του τρίτου κάτω από τις μηχανές, "
                              "πίσω στο 4 όταν αδειάσει το ορυχείο (βήμα 126)")

    why = roles(sym)
    check(why is None, why or "ρομπότ: γεωτρύπανο όσο τα ορυχεία έχουν θέσεις, όπως η αναφορά")

    why = chain(sym, g)
    check(why is None, why or "αλυσίδα: ορυχείο, εργάτης, στολή, θάνατος, γεωτρύπανο")

    got = cost(sym)
    check(all(got[k] <= COST[k] for k in COST),
          "κόστος: " + ", ".join(f"{k} {got[k]} us (ταβάνι {COST[k]})" for k in COST))

    for name, patch, bank6, test in negatives(sym, g):
        if patch is None:
            check(False, f"ΑΡΝΗΤΙΚΟ «{name}»: το σημείο δεν βρέθηκε μία φορά")
            continue
        why = run_negative(sym, g, patch, bank6, test)
        check(why is not None, f"ΑΡΝΗΤΙΚΟ «{name}»: " + (why or "ΔΕΝ το έπιασε τίποτα"))

    print()
    print("ΟΛΑ ΟΚ" if not FAIL else f"{len(FAIL)} ΑΠΟΤΥΧΙΕΣ")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
