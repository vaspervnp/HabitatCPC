#!/usr/bin/env python3
"""Η μεταφορά (βήμα 95, DESIGN §6.7).

Η πρόζα — οι αποφάσεις του παίκτη, όπως στο Planetbase:

  ΣΩΡΟΣ      ό,τι σκάβεται μένει στο ορυχείο, στο όγδοο byte της εγγραφής
             (ST_OWED): με όλο το ρεύμα στο τελευταίο ισοζύγιο (EC_POK, όπως οι
             μηχανές της θέσης 11), 2, 3, 4 ανά κύκλο ροής με 1, 2, 3 που
             σκάβουν, ως 30. Γεμάτος, το ορυχείο δεν βγάζει τίποτα όσο κι αν
             σκάβουν. Ενα εργοτάξιο, που χρωστά υλικά στο ίδιο byte, δεν το
             αγγίζει τίποτα.
  ΕΡΓΑΣΙΑ    με σωρό από 10 και πάνω, μία Haul για το ορυχείο — κόμβος 64 +
             δομή, αδιάθετη, προτεραιότητα 5, J_SITE ο ίδιος κόμβος — με ή
             χωρίς ρεύμα, και το bit 6 του ST_OPS ως να φορτώσει κάποιος. Οχι
             δεύτερη· τίποτα, ούτε το bit, με τον πίνακα γεμάτο. Η Drill του
             ίδιου ορυχείου δημοσιεύεται όπως στο 94, με ή χωρίς το bit 6, και
             πριν από τη Haul του: και οι δύο στο σάρωμα, δομή προς δομή.
  ΦΟΡΤΙΟ     στο ορυχείο το bit σβήνει, 10 φεύγουν από τον σωρό, και ο
             πράκτορας κουβαλά μετάλλευμα (spare) ως την κοντινότερη αποθήκη ή το
             σκάφος (J_NODE και dest· το J_SITE μένει το ορυχείο). Χωρίς κανένα
             που να φτάνεται, το φορτίο παραδίδεται εκεί. Με σωρό κάτω από 10
             δεν παίρνει τίποτα, και η εργασία κλείνει.
  ΠΑΡΑΔΟΣΗ   στον προορισμό: +10 μετάλλευμα, «φτιάχτηκε εδώ» (EC_PRODM, §10.2),
             spare 0, η εργασία κλείνει.
  ΜΙΣΟΔΡΟΜΙΣ ένας φορτωμένος που αφήνει τη Haul — πεθαίνει, πάει για ανάγκη — την
             αφήνει ανοιχτή και να δείχνει τον προορισμό: ο επόμενος παραδίδει
             το φορτίο που έμεινε στη μέση. Μια Supply γυρίζει στο εργοτάξιο,
             όπως από το βήμα 88.
  ΠΟΙΟΙ      εργάτες και ρομπότ μεταφοράς (job_roles #41), με τη Haul (5) πάνω
             από τη Drill (4): ένας εργάτης με τις δύο ανοιχτές κουβαλά.
  ΑΛΥΣΙΔΑ    στο παιχνίδι που τρέχει, με την πλατφόρμα της αποικίας δοκιμών
             σκάφος, όπως σε νέο παιχνίδι: το ορυχείο στη φλέβα, ο ένας εργάτης
             σκάβει, ο σωρός φτάνει τα 10, ο άλλος το κουβαλά στο σκάφος και το
             μετάλλευμα ανεβαίνει 10· και ένα ρομπότ μεταφοράς κάνει το ίδιο.
  ΚΟΣΤΟΣ     η θέση 13 με μια άφιξη στο ορυχείο και στον προορισμό, κάτω από
             τα ταβάνια COST. Ο κύκλος ροής με ορυχεία: tests/test_drill.py.

Αρνητικά, με τον κώδικα πειραγμένο στη μνήμη: το hl_pile δεν καλείται· βγάζει
και χωρίς ρεύμα· χωρίς ταβάνι· η Haul χωρίς το bit 6· η Drill που βλέπει το
bit 6· το bit που δεν σβήνει στο φόρτωμα· φόρτωμα που δεν παίρνει από τον
σωρό· παράδοση που δεν φτιάχνει μετάλλευμα· ποτέ προορισμός· το μάζεμα γυρίζει
μια φορτωμένη Haul στο ορυχείο· η Haul στην προτεραιότητα του 94 (2)· και από
το βήμα 123, το ορυχείο εκτός φλέβας με ολόκληρη απόδοση.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import test_drill as TD                                  # noqa: E402
import balance as B                                      # noqa: E402
import econ as EC                                        # noqa: E402

FAIL = []
HAUL_LOAD, HAUL_CAP, BIT = 10, 30, 0x40
HALF, FREE = EC.ST_HALF, EC.ST_FREE                     # βήμα 123
J_HAUL, J_DRILL, J_SUPPLY = EC.J_HAUL, EC.J_DRILL, EC.J_SUPPLY
K_MINE, K_SHIP, K_PAD = EC.K_MINE, EC.K_SHIP, EC.K_PAD
DS_BUILDING, DS_ACTIVE = 1, 2
ST_KIND, ST_OPS, ST_OWED = EC.ST_KIND, EC.ST_OPS, EC.ST_OWED
S_ORE = EC.S_ORE
RL_WORKER, RL_CARRY = 0, EC.RL_CARRY
POK, JAGENT, PRODM = 46, 57, 68                          # μέσα στο econ_state
F_ALIVE, F_WORKING = 1, 32


def check(ok, msg):
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ ") + msg)
    if not ok:
        FAIL.append(msg)


class Game(TD.Game):
    """Το colony.sna σε παύση, με ό,τι χρειάζεται η μεταφορά."""

    def job(self, j):
        return list(self.jobs()[5 * j:5 * j + 5])

    def put_job(self, j, v):
        self.m.write_ram(self.jt + 5 * j, bytes(v))

    def free_job(self):
        return self.jobs()[::5].index(255)

    def ag_set(self, i, **f):
        """Πεδία πράκτορα: flags, role, node, slot, dest, edge, task, spare."""
        at = {"flags": 0, "role": 128, "node": 256, "slot": 384, "dest": 512, "edge": 640,
              "task": 896, "spare": 1920}
        for k, v in f.items():
            self.b6[self.ag + at[k] + i] = v

    def ag_get(self, i, k):
        at = {"flags": 0, "role": 128, "node": 256, "dest": 512, "edge": 640, "task": 896,
              "spare": 1920}
        return self.b6[self.ag + at[k] + i]


# --------------------------------------------------------------------------
# ΠΙΝΑΚΕΣ
# --------------------------------------------------------------------------
def tables(sym):
    m = Game(sym).m
    roles = m.peek(sym["JOB_ROLES"] + J_HAUL)
    prio = [m.peek(sym["JOB_PRIO"] + k) for k in (J_HAUL, J_DRILL)]
    if (roles, prio) != (0x41, [5, 4]) or (EC.JOB_ROLES[J_HAUL], EC.JOB_PRIO[J_HAUL]) != (0x41, 5) \
            or (EC.HAUL_LOAD, EC.HAUL_CAP, EC.ST_HAUL) != (HAUL_LOAD, HAUL_CAP, BIT):
        return (f"ΠΙΝΑΚΕΣ: Haul ρόλοι #{roles:02X}, προτεραιότητες Haul/Drill {prio}, αναφορά "
                f"#{EC.JOB_ROLES[J_HAUL]:02X}/{EC.JOB_PRIO[J_HAUL]}, φορτίο/ταβάνι/bit "
                f"{EC.HAUL_LOAD}/{EC.HAUL_CAP}/{EC.ST_HAUL:#x} — η πρόζα λέει #41, 5 πάνω από 4, 10/30/#40")
    return None


# --------------------------------------------------------------------------
# ΣΩΡΟΙ — ο κύκλος ροής με ορυχεία, απέναντι στην πρόζα και στην αναφορά
# --------------------------------------------------------------------------
# (δομή, εγγραφή, ο σωρός μετά με ρεύμα, χωρίς, Haul με/χωρίς, Drill)
PSCENE = [(5, [-30, 20, K_MINE, 0, DS_ACTIVE, 255, 1, 0], 2, 0, 0, 0, 1),
          (6, [-24, 20, K_MINE, 0, DS_ACTIVE, 255, 3, 8], 12, 8, 1, 0, 0),
          (7, [-18, 20, K_MINE, 0, DS_ACTIVE, 255, 2, 29], 30, 29, 1, 1, 1),
          (8, [-12, 20, K_MINE, 0, DS_ACTIVE, 255, BIT, 15], 15, 15, 0, 0, 1),
          (9, [-6, 20, K_MINE, 0, DS_ACTIVE, 255, BIT | 1, 30], 30, 30, 0, 0, 1),
          (10, [0, 30, K_MINE, 0, DS_BUILDING, 0, 0, 0x21], 0x21, 0x21, 0, 0, 0),
          # ΕΚΤΟΣ ΦΛΕΒΑΣ (βήμα 123): τα μισά, προς τα πάνω — 1, 2, 2. Το ST_FREE
          # δεν αλλάζει τίποτα, και η Drill δεν βλέπει κανένα από τα δύο bits.
          (11, [6, 20, K_MINE, 0, DS_ACTIVE, 255, HALF | 1, 0], 1, 0, 0, 0, 1),
          (12, [12, 20, K_MINE, 0, DS_ACTIVE, 255, HALF | 2, 9], 11, 9, 1, 0, 1),
          (13, [18, 20, K_MINE, 0, DS_ACTIVE, 255, HALF | FREE | 3, 28], 30, 28, 1, 1, 0)]


def piles(sym, patch=(), patch6=(), quiet=False):
    """ΣΩΡΟΙ. Η πρώτη διαφορά, ή None."""
    for power in (True, False):
        G = Game(sym, patch, patch6)
        for k, v, *_ in PSCENE:
            G.put_rec(k, [b & 255 for b in v])
        G.m.poke(G.g + 46, EC.POWER_ALL if power else EC.POWER_NONE)   # EC_POK
        G.s16(G.g + 28, 30000 if power else 0)
        ore0, jobs0 = G.ore(), G.jobs()
        (want_ore, want_mines, want_jobs), want_st = TD.ref_flow(G)
        if TD.cycle(G) is None:
            return "ΣΩΡΟΙ: το econ_flow δεν τερμάτισε"
        # η πρόζα: στο σάρωμα, με τη σειρά των δομών, η Drill και μετά η Haul
        posts = []
        for k, _, _, _, hp, hn, d in PSCENE:
            posts += [(J_DRILL, 64 + k, 4)] if d else []
            posts += [(J_HAUL, 64 + k, 5)] if (hp if power else hn) else []
        free = [j for j in range(32) if jobs0[5 * j] == 255]
        prose = bytearray(jobs0)
        for j, (kind, node, pr) in zip(free, posts):
            prose[5 * j:5 * j + 5] = bytes([kind, node, 255, pr, node])
        want_piles = [(wp if power else wn) for _, _, wp, wn, *_ in PSCENE]
        want_ops = [(v[6] | (0x80 if d else 0) | (BIT if (hp if power else hn) else 0))
                    for _, v, _, _, hp, hn, d in PSCENE]
        got_piles = [G.rec(k)[ST_OWED] for k, *_ in PSCENE]
        got_ops = [G.rec(k)[ST_OPS] for k, *_ in PSCENE]
        if (G.ore(), G.jobs(), got_piles, got_ops) != (ore0, bytes(prose), want_piles, want_ops):
            return (f"ΣΩΡΟΙ ({'με' if power else 'χωρίς'} ρεύμα): σωροί {got_piles}, ST_OPS "
                    f"{[hex(v) for v in got_ops]}, μετάλλευμα {ore0} -> {G.ore()}, νέες εργασίες "
                    f"{[list(G.jobs()[5 * j:5 * j + 5]) for j in range(32) if G.jobs()[5 * j:5 * j + 5] != jobs0[5 * j:5 * j + 5]]}"
                    f" — η πρόζα λέει σωροί {want_piles}, ST_OPS {[hex(v) for v in want_ops]}, "
                    f"το μετάλλευμα ίδιο, εργασίες {posts}")
        if (G.ore(), G.mines(), G.jobs()) != (want_ore, want_mines, want_jobs) \
                or bytes(G.b6[G.st:G.st + 256]) != want_st:
            return "ΣΩΡΟΙ: ο Z80 διαφέρει από την αναφορά (tools/econ.py, flow_cycle και haul_pile)"
        # ένας δεύτερος κύκλος: καμία διπλή
        jobs1 = G.jobs()
        TD.cycle(G)
        if G.jobs() != jobs1:
            return "ΣΩΡΟΙ: ο δεύτερος κύκλος ξαναδημοσίευσε"
    # ο πίνακας γεμάτος: τίποτα, ούτε το bit
    G = Game(sym, patch, patch6)
    for k, v, *_ in PSCENE:
        G.put_rec(k, [b & 255 for b in v])
    G.s16(G.g + 28, 30000)
    full = bytes([EC.J_OPERATE, 0, 255, 3, 0] * 32)
    G.m.write_ram(G.jt, full)
    TD.cycle(G)
    if G.jobs() != full or [G.rec(k)[ST_OPS] & BIT for k in (6, 7)] != [0, 0]:
        return "ΣΩΡΟΙ: με τον πίνακα γεμάτο κάτι γράφτηκε, ή μπήκε το bit 6"
    if not quiet:
        print("    ΣΩΡΟΙ: 0+2, 8+4 = 12 και Haul, 29+3 = 30 (ταβάνι) και Haul, 15 με το bit "
              "χωρίς δεύτερη, 30 γεμάτος, το εργοτάξιο ανέγγιχτο· εκτός φλέβας (βήμα 123) "
              "0+1, 9+2 = 11 και Haul, 28+2 = 30 και Haul· χωρίς ρεύμα κανένας δεν "
              "μεγαλώνει και Haul μόνο για το 29 και το 28· οι Drill όπως στο 94 και με τα "
              "bits 2, 3 και 6· τίποτα με τον πίνακα γεμάτο· όπως η αναφορά")
    return None


# --------------------------------------------------------------------------
# ΑΦΙΞΗ — η θέση 13 με μια Haul στο ορυχείο και στον προορισμό
# --------------------------------------------------------------------------
# Το «ορυχείο» είναι το airlock της αποικίας δοκιμών (δομή 1, κόμβος 65) με
# την εγγραφή ορυχείου: ο κόμβος του έχει γράφο και γραμμή DIST. Η πλατφόρμα
# (δομή 0, κόμβος 64) είναι πότε σκάφος και πότε όχι. Ο πράκτορας είναι ο
# δεύτερος εργάτης (1).
MINE, SHIP, WHO = 65, 64, 1


def scene(sym, patch=(), ship=True, pile=20, at=MINE, loaded=False, alive=True):
    G = Game(sym, patch)
    rec = G.rec(1)
    G.put_rec(1, rec[:2] + [K_MINE, 0, DS_ACTIVE, 255, BIT | 1, pile])
    G.b6[G.st + ST_KIND] = K_SHIP if ship else K_PAD
    j = G.free_job()
    G.put_job(j, [J_HAUL, SHIP if loaded else MINE, WHO, 5, MINE])
    G.ag_set(WHO, flags=F_ALIVE if alive else 0, node=at, dest=at, edge=255, task=j,
             spare=S_ORE if loaded else 0)
    G.s16(G.g + 2 * S_ORE, 100)
    G.m.poke(G.g + PRODM, 0)
    return G, j


def arrive(sym, patch=(), quiet=False):
    """ΑΦΙΞΗ. Η πρώτη διαφορά, ή None."""
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    # (i) στο ορυχείο, με σκάφος
    G, j = scene(sym, patch)
    G.call("JOBS_TICK")
    got = (G.job(j), G.rec(1)[ST_OWED], G.rec(1)[ST_OPS], G.ag_get(WHO, "dest"),
           G.ag_get(WHO, "spare"), G.ag_get(WHO, "task"), G.ore())
    want = ([J_HAUL, SHIP, WHO, 5, MINE], 10, 1, SHIP, S_ORE, j, 100)
    if got != want:
        return (f"ΦΟΡΤΙΟ: εργασία {got[0]}, σωρός {got[1]}, ST_OPS {got[2]:#x}, dest {got[3]}, "
                f"spare {got[4]}, task {got[5]}, μετάλλευμα {got[6]} — η πρόζα λέει {want}")
    say(f"ΦΟΡΤΙΟ: στο ορυχείο (κόμβος {MINE}) ο σωρός 20 -> 10, το bit σβήνει, κουβαλά "
        f"μετάλλευμα προς το σκάφος ({SHIP}), η εργασία δική του")
    # (ii) στο ορυχείο, χωρίς σκάφος και αποθήκη: παραδίδει εκεί
    G, j = scene(sym, patch, ship=False)
    G.call("JOBS_TICK")
    got = (G.job(j)[0], G.rec(1)[ST_OWED], G.rec(1)[ST_OPS], G.ag_get(WHO, "spare"),
           G.ag_get(WHO, "task"), G.ore(), G.m.peek(G.g + PRODM) & (1 << S_ORE))
    want = (255, 10, 1, 0, 255, 110, 1 << S_ORE)
    if got != want:
        return f"ΦΟΡΤΙΟ ΧΩΡΙΣ ΠΡΟΟΡΙΣΜΟ: {got} — η πρόζα λέει {want}"
    # (iii) σωρός κάτω από φορτίο
    G, j = scene(sym, patch, pile=5)
    G.call("JOBS_TICK")
    got = (G.job(j)[0], G.rec(1)[ST_OWED], G.rec(1)[ST_OPS], G.ag_get(WHO, "spare"), G.ore())
    if got != (255, 5, 1, 0, 100):
        return f"ΣΩΡΟΣ ΚΑΤΩ ΑΠΟ ΦΟΡΤΙΟ: {got} — η πρόζα λέει (255, 5, 1, 0, 100)"
    say("ΧΩΡΙΣ ΠΡΟΟΡΙΣΜΟ: το φορτίο παραδίδεται στο ορυχείο (+10, «φτιάχτηκε εδώ»)· με "
        "σωρό 5 δεν παίρνει τίποτα και η εργασία κλείνει")
    # (iv) στον προορισμό
    G, j = scene(sym, patch, at=SHIP, loaded=True)
    G.call("JOBS_TICK")
    got = (G.job(j)[0], G.ag_get(WHO, "spare"), G.ag_get(WHO, "task"), G.ore(),
           G.m.peek(G.g + PRODM) & (1 << S_ORE), G.rec(1)[ST_OWED])
    want = (255, 0, 255, 110, 1 << S_ORE, 20)
    if got != want:
        return f"ΠΑΡΑΔΟΣΗ: {got} — η πρόζα λέει {want}"
    say("ΠΑΡΑΔΟΣΗ: στο σκάφος +10 μετάλλευμα, «φτιάχτηκε εδώ», spare 0, η εργασία κλείνει")
    # (v) το μάζεμα: φορτωμένος νεκρός — η Haul ανοιχτή προς τον προορισμό
    G, j = scene(sym, patch, at=SHIP, loaded=True, alive=False)
    G.ag_set(WHO, node=100)                         # μακριά: να μην την ξαναπάρει
    js = [k for k in range(32) if G.jobs()[5 * k] == 255 and k != j][0]
    G.put_job(js, [J_SUPPLY, SHIP, 2, 4, MINE])     # μια Supply στο πρώτο σκέλος
    G.ag_set(2, task=js)
    G.ag_set(2, flags=0)
    G.call("JOBS_TICK")
    got = (G.job(j)[:3], G.job(js)[:3])
    # η Haul μπορεί να ξαναπιαστεί αμέσως από άλλον εργάτη: το J_NODE μετρά
    if got[0][:2] != [J_HAUL, SHIP] or got[1][:2] != [J_SUPPLY, MINE]:
        return (f"ΜΙΣΟΔΡΟΜΙΣ: Haul {got[0]}, Supply {got[1]} — η πρόζα λέει η Haul μένει "
                f"προς το {SHIP}, η Supply γυρίζει στο {MINE}")
    say(f"ΜΙΣΟΔΡΟΜΙΣ: ο φορτωμένος πέθανε — η Haul μένει προς το σκάφος, η Supply γυρίζει "
        f"στο εργοτάξιο")
    # (vi) Haul και Drill ανοιχτές στο ίδιο ορυχείο, ένας εργάτης ελεύθερος
    G = Game(sym, patch)
    rec = G.rec(1)
    G.put_rec(1, rec[:2] + [K_MINE, 0, DS_ACTIVE, 255, 0xC0, 20])
    # οι προτεραιότητες από τον πίνακα του Z80, όπως τις γράφει το jp_have
    pr = lambda kind: G.m.peek(G.sym["JOB_PRIO"] + kind)
    jd = G.free_job()
    G.put_job(jd, [J_DRILL, MINE, 255, pr(J_DRILL), MINE])
    jh = G.free_job()
    G.put_job(jh, [J_HAUL, MINE, 255, pr(J_HAUL), MINE])
    for i in range(4):
        if i != WHO:
            G.ag_set(i, flags=G.ag_get(i, "flags") | F_WORKING)
    G.ag_set(WHO, flags=F_ALIVE | 2, task=255, edge=255)
    G.m.poke(G.g + JAGENT, 0)
    G.call("JOBS_TICK")
    if (G.job(jh)[2], G.job(jd)[2], G.ag_get(WHO, "task")) != (WHO, 255, jh):
        return (f"ΠΟΙΟΙ: Haul {G.job(jh)}, Drill {G.job(jd)}, task {G.ag_get(WHO, 'task')} — "
                f"η πρόζα λέει ο εργάτης παίρνει τη Haul (5 πάνω από 4)")
    say("ΠΟΙΟΙ: με Haul και Drill ανοιχτές, ο εργάτης κουβαλά")
    return None


# --------------------------------------------------------------------------
# ΑΛΥΣΙΔΑ — στο παιχνίδι που τρέχει
# --------------------------------------------------------------------------
def chain(sym, g, patch=(), patch6=(), quiet=False):
    """ΑΛΥΣΙΔΑ. Η πρώτη διαφορά, ή None."""
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G = Game(sym, patch, patch6)
    m = G.m
    G.b6[G.st + ST_KIND] = K_SHIP           # η πλατφόρμα σκάφος, όπως σε νέο παιχνίδι
    G.s16(G.g + 2 * EC.S_METAL, 200)
    B.build(m, sym, 8, g + 6, at=TD.MINE_AT, fit=False)
    k = next((k for k in range(32) if G.rec(k)[ST_KIND] == K_MINE), None)
    if k is None:
        return "ΑΛΥΣΙΔΑ: το ορυχείο δεν μπήκε στη φλέβα"
    node = 64 + k
    m.poke(sym["UI_SPD"], 4)

    def run(cond, limit, step=20):
        t = 0
        while t < limit and not cond():
            G.s16(G.g + 28, 30000)          # ρεύμα: η μπαταρία γεμάτη
            m.run_frames(step)
            t += step
        return t

    t = run(lambda: G.rec(k)[4] == DS_ACTIVE, 30000, 50)
    if G.rec(k)[4] != DS_ACTIVE:
        return f"ΑΛΥΣΙΔΑ: το ορυχείο δεν χτίστηκε σε {t} frames"

    def haul():
        return [j for j in range(32) if G.job(j)[:2] == [J_HAUL, node]
                or (G.job(j)[0] == J_HAUL and G.job(j)[4] == node)]

    def trip(who_ok, what):
        """Μια Haul ως το τέλος: δημοσίευση, φόρτωμα, παράδοση."""
        t = run(lambda: haul() and G.rec(k)[ST_OPS] & BIT, 40000)
        if not haul():
            return f"{what}: καμία Haul σε {t} frames (σωρός {G.rec(k)[ST_OWED]}, ST_OPS {G.rec(k)[ST_OPS]:#x})"
        j = haul()[0]
        t = run(lambda: G.job(j)[1] == SHIP or G.job(j)[0] != J_HAUL, 30000, 5)
        a = G.job(j)[2]
        if G.job(j)[:2] != [J_HAUL, SHIP] or not who_ok(a) or G.ag_get(a, "spare") != S_ORE:
            return (f"{what}: σε {t} frames η Haul {G.job(j)}, ο πράκτορας {a} "
                    f"(ρόλος {G.ag_get(a, 'role') if a < 128 else '-'}) spare "
                    f"{G.ag_get(a, 'spare') if a < 128 else '-'}")
        pile = G.rec(k)[ST_OWED]
        ore = G.ore()
        t2 = run(lambda: G.job(j)[0] != J_HAUL, 30000, 5)
        if G.job(j)[0] == J_HAUL or G.ore() - ore != HAUL_LOAD or G.ag_get(a, "spare"):
            return (f"{what}: η παράδοση — εργασία {G.job(j)}, μετάλλευμα {ore} -> {G.ore()}, "
                    f"spare {G.ag_get(a, 'spare')}")
        say(f"{what}: ο {a} φόρτωσε στο ορυχείο (κόμβος {node}, σωρός ως {pile} μετά), "
            f"παρέδωσε στο σκάφος σε {t2} frames: μετάλλευμα {ore} -> {G.ore()}")
        return None

    why = trip(lambda a: a < 80 and G.ag_get(a, "role") == RL_WORKER, "ΕΡΓΑΤΗΣ")
    if why:
        return why
    # ένα ρομπότ μεταφοράς στη θέση ενός εργάτη που δεν δουλεύει: παίρνει τα
    # πεδία του (και τη θέση του στο δαχτυλίδι), και ο εργάτης φεύγει
    t = run(lambda: any(G.ag_get(i, "flags") & F_ALIVE and G.ag_get(i, "role") == RL_WORKER
                        and not G.ag_get(i, "flags") & F_WORKING and G.ag_get(i, "task") == 255
                        and G.ag_get(i, "edge") == 255 for i in range(80)), 20000, 5)
    w = next((i for i in range(80) if G.ag_get(i, "flags") & F_ALIVE
              and G.ag_get(i, "role") == RL_WORKER and not G.ag_get(i, "flags") & F_WORKING
              and G.ag_get(i, "task") == 255 and G.ag_get(i, "edge") == 255), None)
    if w is None:
        return f"ΡΟΜΠΟΤ: κανένας εργάτης ελεύθερος σε {t} frames"
    for f in range(16):
        G.b6[G.ag + 128 * f + 80] = G.b6[G.ag + 128 * f + w]
    G.ag_set(80, role=RL_CARRY)
    G.ag_set(w, flags=0)
    for i in range(80):                      # οι άλλοι εργάτες απασχολημένοι
        if G.ag_get(i, "flags") & F_ALIVE and G.ag_get(i, "role") == RL_WORKER \
                and not G.ag_get(i, "flags") & F_WORKING and i != w:
            G.ag_set(i, flags=G.ag_get(i, "flags") | F_WORKING)
    return trip(lambda a: a == 80, "ΡΟΜΠΟΤ")


# --------------------------------------------------------------------------
# ΚΟΣΤΟΣ
# --------------------------------------------------------------------------
# Πάνω από μια θέση 13 χωρίς εργασία (μετρημένα στο βήμα 95: 322 και 255 us). Το
# φόρτωμα περνά από το sp_take, την αναζήτηση της πηγής μιας Supply.
COST = {"θέση 13, φόρτωμα στο ορυχείο": 340, "θέση 13, παράδοση": 270}


def cost(sym):
    out = {}
    G, j = scene(sym)
    G.put_job(j, [255] * 5)
    G.ag_set(WHO, task=255)
    base = G.call("JOBS_TICK", timed=True)
    G, j = scene(sym)
    out["θέση 13, φόρτωμα στο ορυχείο"] = G.call("JOBS_TICK", timed=True) - base
    G, j = scene(sym, at=SHIP, loaded=True)
    out["θέση 13, παράδοση"] = G.call("JOBS_TICK", timed=True) - base
    return out


# --------------------------------------------------------------------------
# ΑΡΝΗΤΙΚΑ
# --------------------------------------------------------------------------
def negatives(sym, g):
    G = Game(sym)
    m = G.m
    w = lambda a: [a & 255, a >> 8]
    out = []

    def at6(label, name, n, pat, edits, test):
        lo = sym[name] - 0x4000
        hits = TD.find(bytes(G.b6[lo:lo + n]), sym[name], pat)
        out.append((label, [(hits[0] + k, v) for k, v in edits] if len(hits) == 1 else None,
                    True, test))

    def at0(label, name, n, pat, edits, test):
        hits = TD.find(m.read_ram(sym[name], n), sym[name], pat)
        out.append((label, [(hits[0] + k, v) for k, v in edits] if len(hits) == 1 else None,
                    False, test))

    # econ_flow: call hl_pile -> nop
    at6("το hl_pile δεν καλείται", "ECON_FLOW", 400, [0xCD] + w(sym["HL_PILE"]),
        [(0, 0), (1, 0), (2, 0)], "piles")
    # hl_pile: ld a,(EC_POK) · cp P_ALL · jr nz -> nop nop
    at0("βγάζει και χωρίς ρεύμα", "HL_PILE", 10, [0xFE, EC.POWER_ALL, 0x20], [(2, 0), (3, 0)],
        "piles")
    # hl_pile: cp HAUL_CAP + 1 -> cp 255
    at0("χωρίς ταβάνι", "HL_PILE", 40, [0xFE, HAUL_CAP + 1], [(1, 255)], "piles")
    # hl_pile: bit ST_HALF,(ix+ST_OPS) · jr z -> jr: ολόκληρη απόδοση και εκτός φλέβας
    at0("εκτός φλέβας ολόκληρο", "HL_PILE", 40, [0xDD, 0xCB, ST_OPS, 0x56, 0x28],
        [(4, 0x18)], "piles")
    # st_post: ld a,(ix+ST_OPS) · or c · ld (ix+ST_OPS),a -> το or c nop
    at0("η Haul χωρίς το bit 6", "ST_POST", 40, [0xDD, 0x7E, ST_OPS, 0xB1], [(3, 0)], "piles")
    # econ_flow: and #83 -> nop nop
    at6("η Drill βλέπει το bit 6", "ECON_FLOW", 200, [0xE6, 0x83, 0xFE], [(0, 0), (1, 0)], "piles")
    # hl_arrive: res ST_HAUL,(hl) -> nop nop
    at0("το bit μένει στο φόρτωμα", "HL_ARRIVE", 40, [0xCB, 0xB6], [(0, 0), (1, 0)], "arrive")
    # hl_arrive: sub HAUL_LOAD · jr c · ld (hl),a -> το ld nop
    at0("το φόρτωμα δεν παίρνει από τον σωρό", "HL_ARRIVE", 40, [0xD6, HAUL_LOAD, 0x38],
        [(4, 0)], "arrive")
    # hla_drop: call ec_make -> nop
    at0("η παράδοση δεν φτιάχνει μετάλλευμα", "HL_ARRIVE", 100, [0xCD] + w(sym["EC_MAKE"]),
        [(0, 0), (1, 0), (2, 0)], "arrive")
    # hl_arrive: cp (hl) · jr z,hla_drop -> jr hla_drop
    at0("ποτέ προορισμός", "HL_ARRIVE", 80, [0xBE, 0x28], [(1, 0x18)], "arrive")
    # jr_free: cp J_HAUL · jr z,jr_pop -> nop nop
    at0("το μάζεμα γυρίζει μια φορτωμένη Haul", "JB_REAP", 60, [0xFE, J_HAUL, 0x28],
        [(2, 0), (3, 0)], "arrive")
    # job_prio: η Haul 2
    out.append(("η Haul στην προτεραιότητα του 94", [(sym["JOB_PRIO"] + J_HAUL, 2)]
                if m.peek(sym["JOB_PRIO"] + J_HAUL) == 5 else None, False, "arrive"))
    return out


def run_negative(sym, g, patch, bank6, test):
    p0, p6 = ((), patch) if bank6 else (patch, ())
    if test == "piles":
        return piles(sym, p0, p6, quiet=True)
    return arrive(sym, p0, quiet=True)


def main():
    sym, g = TG.build()

    why = tables(sym)
    check(why is None, why or "πίνακες: Haul για εργάτη και ρομπότ μεταφοράς, προτεραιότητα 5 "
          "πάνω από τη Drill, φορτίο 10, ταβάνι 30, bit 6")

    why = piles(sym)
    check(why is None, why or "σωροί: ρυθμός, ταβάνι, Haul και Drill όπως η πρόζα και η αναφορά")

    why = arrive(sym)
    check(why is None, why or "άφιξη: φόρτωμα, προορισμός, παράδοση, μισοδρομίς, προτεραιότητα")

    why = chain(sym, g)
    check(why is None, why or "αλυσίδα: ορυχείο, σωρός, εργάτης και ρομπότ μεταφοράς ως το σκάφος")

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
