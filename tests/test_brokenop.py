#!/usr/bin/env python3
"""Σταματά μόνο η χαλασμένη (βήμα 140, DESIGN §6.7· η επιλογή του χρήστη).

Ως το βήμα 139 ένας θόλος με μία χαλασμένη μηχανή δημοσίευε μόνο Repair: το
jp_one του src/jobs.asm τη ζητούσε σε κάθε επίσκεψη, την έβρισκε ήδη στον
πίνακα και γύριζε, χωρίς να ρωτήσει για χειριστές. Οσοι δούλευαν εκεί έφευγαν
να φάνε ή να κοιμηθούν, και κανείς δεν τους ξαναζητούσε· οι άλλες τρεις μηχανές
ενός μεσαίου θόλου σταματούσαν ως να έρθει ανταλλακτικό. Ο σεναριακός παίκτης
(tools/play.py, 60 sol) το βρήκε στο 1048 3: τριάντα νεκροί από πείνα με 184
άμυλο, 157 λαχανικά και 99 κρέας στην αποθήκη — τα δύο κυλικεία, ένα μικρό κι
ένα μεσαίο με τέσσερις MEALS, χωρίς μάγειρα για επτά sol.

Τώρα, όπως στο Planetbase, σταματά μόνο η χαλασμένη. ΕΝΑΛΛΑΞ: ο δείκτης
EC_JDOME τρέχει 0-255, ο θόλος είναι τα έξι χαμηλά του bits και το bit 6 (μετά
το +1) το σάρωμα των 64. Ενας θόλος με χαλασμένη ζητά τη Repair στα ζυγά
σαρώματα και την Operate για όσες δουλεύουν στα μονά — μία σάρωση των 32 ανά
επίσκεψη, όπως πριν. Και τις δύο στην ίδια επίσκεψη ήθελε δεύτερη σάρωση:
3.414 µs αντί για 1.808 στο χειρότερο (μετρημένο, πρώτη γραφή του βήματος).

Στο colony.sna σε παύση, το jb_post με το EC_JDOME στον θόλο D (+64 για μονό
σάρωμα· JOB_SCAN = 4 θόλοι από εκεί). Ο θόλος D είναι εργοστάσιο:

  ΜΕΣΑΙΟΣ   τέσσερις METAL, η πρώτη χαλασμένη, κανένας χειριστής. Ζυγό: μόνο η
            Repair [4, D, 255, 6, D]. Μονό: και η Operate [1, D, 255, 5, D]
            (ROOM_PRIO του εργοστασίου). Ζυγό και μονό ξανά: τίποτα νέο.
  ΜΟΝΟ ΠΡΩΤΑ ο ίδιος, πρώτα σε μονό: η Operate· στο επόμενο ζυγό η Repair.
  ΟΛΟΙ ΕΚΕΙ με τρεις χειριστές (D_OPS = 3, όσες δουλεύουν): στο μονό τίποτα.
  ΜΙΚΡΟΣ    η μόνη του μηχανή χαλασμένη: ποτέ Operate (δεν δουλεύει καμία).
  ΓΕΜΑΤΟΣ   η Repair του D και 31 Operate άλλων θόλων: στο μονό τίποτα.
  ΑΝΑΦΟΡΑ   ο πίνακας και ο δείκτης του Z80 μετά την επίσκεψη, απέναντι στο
            post_jobs του tools/econ.py από την ίδια κατάσταση, σε 200
            τυχαίους συνδυασμούς μεγέθους, βλαβών, χειριστών, πίνακα και
            δείκτη 0-255.

Και ο ΧΡΟΝΟΣ: το jb_post στο μονό σάρωμα, ο θόλος με χαλασμένη να ψάχνει την
Operate σε πίνακα με 31 Operate άλλων θόλων — μία σάρωση — όχι πιο αργά από
έναν θόλο χωρίς βλάβη που ζητά χειριστή στον ίδιο πίνακα, δρόμο που υπήρχε
ήδη: το χειρότερο του jb_post δεν ανεβαίνει. Και ταβάνι.

Αρνητικά, με το snapshot πειραγμένο: and 0 αντί για and MAX_DOME (πάντα η
Repair, το 139)· jr nz αντί για jr z (η Repair στα μονά)· το and MAX_DOME - 1
του θόλου σβηστό (ο δείκτης 64-255 ως θόλος).
"""
import os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import test_alertname as TA                              # noqa: E402
import econ as EC                                        # noqa: E402

J_OPERATE, J_REPAIR, NO_JOB = 1, 4, 255
METAL, NO_MACH, HP = 1, 255, 200
D = 1
D_OPS = 7
ODD = 64
# µs με το probe, το χειρότερο από πέντε: μονό σάρωμα, ο D ψάχνει την Operate
# σε πίνακα με 31 Operate άλλων θόλων και μία ελεύθερη θέση, και οι τρεις
# θόλοι μετά τον D σαρώνουν γεμάτο πίνακα. Μετρημένα στο βήμα 140: 2.454· ο ίδιος
# θόλος χωρίς βλάβη 2.543, το ζυγό με τη Repair ήδη εκεί 1.815 (1.808 με τον
# κώδικα του 139). Με τη δεύτερη σάρωση της πρώτης γραφής 3.414.
CEIL = 2_490
FAIL = []


def check(ok, msg):
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ ") + msg)
    if not ok:
        FAIL.append(msg)


class Game(TA.Game):
    def ops(self, n, d=D):
        self.b6[self.dt + 24 * d + D_OPS] = n

    def table(self):
        return [self.job(j) for j in range(32)]

    def mine(self, d=D):
        return sorted(tuple(j) for j in self.table() if j[0] != NO_JOB and j[1] == d)

    def visit(self, at=D, timed=False):
        self.m.poke(self.X["EC_JDOME"], at)
        return self.call("JB_POST", timed)


def reference(G, at):
    """Το post_jobs του tools/econ.py από την κατάσταση του Z80, με τον δείκτη
    στο at. -> (πίνακας, δείκτης) μετά."""
    e = EC.Econ()
    for k in range(EC.MAX_DOME):
        b = G.dt + 24 * k
        e.dome[k * EC.DOME_REC:(k + 1) * EC.DOME_REC] = bytes(G.b6[b:b + 24])
    jb = bytearray()
    for j in range(32):
        jb += bytes(G.job(j))
    e.job_dome = at
    EC.post_jobs(e, jb)
    return [list(jb[5 * j:5 * j + 5]) for j in range(32)], e.job_dome


def medium(G):
    G.set_dome(D, size=1, mach=[METAL] * 4, hp=[0, HP, HP, HP])
    G.ops(0)


def scenes(sym, patch=(), quiet=False):
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    rep = (J_REPAIR, D, 255, EC.JOB_PRIO[J_REPAIR], D)
    op = (J_OPERATE, D, 255, EC.ROOM_PRIO[EC.R_FACTORY], D)
    # ΜΕΣΑΙΟΣ
    G = Game(sym, patch)
    medium(G)
    want = [[rep], sorted([rep, op]), sorted([rep, op]), sorted([rep, op])]
    for k, at in enumerate((D, D + ODD, D, D + ODD)):
        if G.visit(at) is None:
            return f"ΜΕΣΑΙΟΣ: το jb_post δεν τελείωσε (επίσκεψη {k + 1})"
        if G.mine() != want[k]:
            return (f"ΜΕΣΑΙΟΣ: επίσκεψη {k + 1} ({'μονό' if at & ODD else 'ζυγό'}): {G.mine()} — "
                    f"η πρόζα λέει {want[k]}")
    say("ΜΕΣΑΙΟΣ: στο ζυγό η Repair, στο μονό και η Operate, μετά τίποτα νέο")
    # ΜΟΝΟ ΠΡΩΤΑ
    G = Game(sym, patch)
    medium(G)
    G.visit(D + ODD)
    if G.mine() != [op]:
        return f"ΜΟΝΟ ΠΡΩΤΑ: {G.mine()} — η πρόζα λέει η Operate {op}"
    G.visit(D)
    if G.mine() != sorted([rep, op]):
        return f"ΜΟΝΟ ΠΡΩΤΑ: μετά το ζυγό {G.mine()} — και η Repair"
    say("ΜΟΝΟ ΠΡΩΤΑ: η Operate, και στο ζυγό η Repair")
    # ΟΛΟΙ ΕΚΕΙ
    G = Game(sym, patch)
    medium(G)
    G.ops(3)
    G.visit(D)
    G.visit(D + ODD)
    if G.mine() != [rep]:
        return f"ΟΛΟΙ ΕΚΕΙ: {G.mine()} — με τρεις χειριστές για τρεις που δουλεύουν, μόνο η Repair"
    say("ΟΛΟΙ ΕΚΕΙ: τρεις χειριστές, καμία Operate")
    # ΜΙΚΡΟΣ
    G = Game(sym, patch)
    G.set_dome(D, size=0, mach=[METAL], hp=[0])
    G.ops(0)
    for at in (D, D + ODD, D, D + ODD):
        G.visit(at)
    if G.mine() != [rep]:
        return f"ΜΙΚΡΟΣ: {G.mine()} — η μόνη του χαλασμένη: μόνο η Repair"
    say("ΜΙΚΡΟΣ: η μόνη χαλασμένη, μόνο η Repair")
    # ΓΕΜΑΤΟΣ
    G = Game(sym, patch)
    medium(G)
    G.put_job(0, list(rep))
    for j in range(1, 32):
        nd = 10 + j % 20
        G.put_job(j, [J_OPERATE, nd, 255, 3, nd])
    before = G.table()
    if G.visit(D + ODD) is None:
        return "ΓΕΜΑΤΟΣ: το jb_post δεν τελείωσε"
    if G.table() != before:
        return f"ΓΕΜΑΤΟΣ: ο πίνακας άλλαξε: {[t for t, u in zip(G.table(), before) if t != u]}"
    say("ΓΕΜΑΤΟΣ: η Repair και 31 Operate, στο μονό τίποτα")
    return None


def against_ref(sym, patch=(), n=200, quiet=False):
    rnd = random.Random(140)
    for t in range(n):
        G = Game(sym, patch)
        at = rnd.randrange(256)
        for k in range(4):
            d = (at + k) % EC.MAX_DOME
            size = rnd.randrange(3)
            c = EC.MACHINE_COUNT[size]
            mach = [rnd.choice([METAL, METAL, 6, 7, NO_MACH]) for _ in range(c)]
            hp = [rnd.choice([0, HP, HP]) for _ in range(c)]
            G.set_dome(d, size=size, mach=mach, hp=hp)
            G.ops(rnd.randrange(c + 1), d)
        for j in range(32):
            if rnd.random() < 0.4:
                G.put_job(j, [NO_JOB] * 5)
            else:
                nd = rnd.choice([(at + k) % EC.MAX_DOME for k in range(4)] + [40, 50])
                G.put_job(j, [rnd.choice([J_OPERATE, J_REPAIR, 0, 2]), nd, 255, 3, nd])
        want, wp = reference(G, at)
        if G.visit(at) is None:
            return f"ΑΝΑΦΟΡΑ: συνδυασμός {t}: το jb_post δεν τελείωσε"
        got, gp = G.table(), G.m.peek(G.X["EC_JDOME"])
        if got != want or gp != wp:
            diff = [(j, g, w) for j, (g, w) in enumerate(zip(got, want)) if g != w]
            return f"ΑΝΑΦΟΡΑ: συνδυασμός {t} (δείκτης {at}): Z80 != αναφορά {diff[:3]}, δείκτης {gp}/{wp}"
    if not quiet:
        print(f"    ΑΝΑΦΟΡΑ: {n} τυχαίοι συνδυασμοί, πίνακας και δείκτης ίδιοι με το tools/econ.py")
    return None


def cost(sym, patch=(), at=D + ODD, need_op=True, fault=True):
    G = Game(sym, patch)
    base = G.probe([], True)
    worst = 0
    for _ in range(5):
        medium(G)
        if not fault:
            G.slot(0, METAL, HP)
        for j in range(32):
            nd = 10 + j % 20
            G.put_job(j, [J_OPERATE, nd, 255, 3, nd])
        G.put_job(30, [NO_JOB] * 5)
        G.put_job(31, [J_REPAIR, D, 255, 6, D])
        us = G.visit(at, timed=True)
        if us is None or need_op and (J_OPERATE, D, 255, EC.ROOM_PRIO[EC.R_FACTORY], D) not in G.mine():
            return 10 ** 6
        worst = max(worst, us - base)
    return worst


def main():
    sym, _ = TG.build()
    err = scenes(sym)
    check(err is None, err or "οι σκηνές: ΜΕΣΑΙΟΣ, ΜΟΝΟ ΠΡΩΤΑ, ΟΛΟΙ ΕΚΕΙ, ΜΙΚΡΟΣ, ΓΕΜΑΤΟΣ")
    err = against_ref(sym)
    check(err is None, err or "ο πίνακας και ο δείκτης ίδιοι με την αναφορά")
    us, even, plain = cost(sym), cost(sym, at=D, need_op=False), cost(sym, fault=False)
    check(us <= CEIL and us <= plain,
          f"ΧΡΟΝΟΣ: jb_post στο μονό, ο θόλος με χαλασμένη ψάχνει την Operate: {us} µs "
          f"(ταβάνι {CEIL}· ο ίδιος χωρίς βλάβη {plain}· στο ζυγό, η Repair ήδη εκεί, {even})")

    # --- αρνητικά --------------------------------------------------------------
    m = Game(sym).m
    one, post = sym["JP_ONE"], sym["JB_POST"]
    c1, c2 = bytes(m.read_ram(one, 40)), bytes(m.read_ram(post, 24))
    a = one + next(k for k in range(36) if c1[k] == 0xE6 and c1[k + 1] == 64)   # and MAX_DOME
    assert c1[a - one + 2] == 0x28, "μετά το and MAX_DOME ένα jr z"
    b = post + next(k for k in range(20) if c2[k] == 0xE6 and c2[k + 1] == 63)  # and MAX_DOME - 1
    negs = [("and 0 αντί για and MAX_DOME (πάντα η Repair, το 139)", [(a + 1, 0)]),
            ("jr nz αντί για jr z (η Repair στα μονά)", [(a + 2, 0x20)]),
            ("χωρίς το and MAX_DOME - 1 του θόλου", [(b + 1, 0xFF)])]
    for label, patch in negs:
        err = scenes(sym, patch, quiet=True) or against_ref(sym, patch, n=40, quiet=True)
        if err:
            print(f"OK ΑΡΝΗΤΙΚΟ: με {label} αποτυγχάνει ({err[:90]})")
        else:
            print(f"ΑΠΟΤΥΧΙΑ ΑΡΝΗΤΙΚΟΥ: με {label} περνά")
            FAIL.append(label)
    if FAIL:
        print(f"\n{len(FAIL)} ΑΠΟΤΥΧΙΕΣ")
        return 1
    print("\nΟΛΑ ΚΑΛΑ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
