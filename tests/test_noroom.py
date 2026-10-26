#!/usr/bin/env python3
"""Μια ανάγκη χωρίς το δωμάτιό της (βήμα 120, DESIGN §6.6).

Ο παίκτης-σενάριο του βήματος 120 (tools/play.py) χτίζει από την άδεια αρχή
με τα πλήκτρα του παίκτη. Στο πρώτο του τρέξιμο, από το sol 2 και μετά, και οι
τέσσερις άποικοι στέκονταν στο κυλικείο με την εργασία T_NEED, και τα δύο
εργοτάξια περίμεναν τα υλικά τους χωρίς κανέναν. Είχαν πάει για νερό, ο ύπνος
τους είχε πέσει κάτω από το κατώφλι, και κοιτώνας δεν υπήρχε: το ψάξιμο δεν
έβρισκε τίποτα και το πέρασμα αναγκών γύριζε χωρίς να αλλάξει κάτι — ούτε να
σβήσει το «πάω για φαγητό» που θα τους ξανάδινε στον πίνακα εργασιών. Από την
ίδια τρύπα, χωρίς ιατρείο ένας τραυματίας δεν ξαναπήγαινε ποτέ για φαγητό ή
νερό: η υγεία κοιτάζεται πρώτη.

Η πρόζα:

  ΧΩΡΙΣ ΚΟΙΤΩΝΑ   ο νυσταγμένος που κρατά το T_NEED από το κυλικείο το αφήνει
                  (NO_TASK, διαθέσιμος)· ο νυσταγμένος χωρίς εργασία δεν
                  κουνιέται. Κανείς δεν ψάχνει (G_room_n).
  ΧΩΡΙΣ ΙΑΤΡΕΙΟ   ο τραυματίας και διψασμένος πάει στο κυλικείο· ο τραυματίας
                  και νυσταγμένος στον κοιτώνα.
  ΑΠΡΟΣΙΤΟ        κοιτώνας υπάρχει αλλά δεν φτάνει εκεί (DIST 255): το T_NEED
                  σβήνει, όπως του χορτάτου.
  ΜΕ ΟΛΑ          όπως ως το βήμα 119: ο νυσταγμένος στον κοιτώνα, ο
                  τραυματίας στο ιατρείο, ο χορτάτος αφήνει το T_NEED.
  ΑΝΑΦΟΡΑ         τα ίδια bytes στον Z80 και στο tools/entity.py (seek).
  ΚΟΣΤΟΣ          η θέση αναγκών καρφωμένη, δέκα άποικοι (οκτώ ως το βήμα 172),
                  σε παραλλαγές: κανένα
                  ταβάνι πάνω από τον χειρότερο γύρο του βήματος 119 (4.550 µs,
                  νυσταγμένοι μέσα), ο χορτάτος ως 2.970 (3.010 στο 119), οι
                  νυσταγμένοι χωρίς κοιτώνα ως 3.050 (3.707 στο 119, που
                  έψαχναν σε κάθε επίσκεψη), οι απρόσιτοι διψασμένοι ως 3.950.
                  Από το βήμα 173 η φέτα έχει δέκα, και τα ταβάνια ανέβηκαν
                  όσο οι δύο ακόμη, με τα περιθώρια του 172: 5.630, 3.640,
                  3.740, 3.730, 4.830 (μετρημένα 5.430, 3.600, 3.680, 3.680,
                  4.680· με οκτώ στο 172 4.350, 2.930, 2.990, 3.000, 3.800).
                  Ο καθένας κοστίζει όσο κόστιζε: +540 ο νυσταγμένος, +335 ο
                  χορτάτος, +440 ο απρόσιτος.
  ΣΤΟ ΠΑΙΧΝΙΔΙ    το άνοιγμα του tools/play.py ως το sol 2,4 στο main.sna,
                  χωρίς κοιτώνα: νυστάζουν και οι έξι, και κανείς δεν κρατά
                  T_NEED με υγεία, φαΐ και νερό πάνω από το κατώφλι.

Αρνητικά, με τον κώδικα πειραγμένο: όπως ως το βήμα 119 (χωρίς τον έλεγχο του
κοιτώνα και με το nd_far = ret z) πέφτουν το ΧΩΡΙΣ ΚΟΙΤΩΝΑ και το ΣΤΟ
ΠΑΙΧΝΙΔΙ (τουλάχιστον τέσσερις κολλημένοι)· χωρίς τον έλεγχο του ιατρείου, το ΧΩΡΙΣ ΙΑΤΡΕΙΟ· μόνο το nd_far =
ret z, το ΑΠΡΟΣΙΤΟ· μόνο χωρίς τον έλεγχο του κοιτώνα, το ΚΟΣΤΟΣ.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")

import test_sim as S                                         # noqa: E402

E, EC = S.E, S.EC
FAIL = []
T_NEED, NO_TASK = 254, 255
INSIDE = [9, 6, 11, 21, 3, 7, 12, 19, 16, 20]  # θόλοι του γράφου colony (δύο ακόμη από το βήμα 173)
NSL = E.WH_NEED_N                               # μια φέτα αναγκών: 10 (8 ως το βήμα 172)
CEIL = {"μέσα, νυσταγμένοι": 5630, "μέσα, χορτάτοι": 3640,         # δέκα από το βήμα 173
        "νυσταγμένοι χωρίς κοιτώνα": 3740, "τραυματίες χωρίς ιατρείο": 3730,
        "έξω, απρόσιτοι, διψασμένοι": 4830}


def check(ok, msg):
    print(("OK " if ok else "ΛΑΘΟΣ ") + msg)
    if not ok:
        FAIL.append(msg)


class Rig:
    """Η αποικία του test_sim, και η θέση αναγκών καρφωμένη: κάθε κλήση
    περνά τους δέκα πρώτους αποίκους (η θέση 7 από το βήμα 173, η πρώτη των
    τεσσάρων· ως τότε η 8 και οι οκτώ)."""

    def __init__(self):
        self.sym = S.build()
        self.g = S.colony_graph()
        dist, self.nexthop = S.G.all_pairs(self.g)
        sim0 = E.Sim(self.g, self.nexthop, dist)
        EC.populate(sim0.e)
        E.populate(sim0)
        EC.rooms_rebuild(sim0.e, sim0.pc)
        sim0.e.sollen, sim0.e.daylen = 320, 192
        self.sim0 = sim0

    def state(self, people, gone=(), far=()):
        """people: {i: dict(πεδίο=τιμή)} πάνω σε «μέσα, χορτάτος»· gone:
        δωμάτια που δεν υπάρχουν (room_n 0)· far: (i, δωμάτιο) απρόσιτα."""
        st = S.fresh(self.g, self.nexthop, self.sim0)
        a = st.a
        for k in range(NSL):
            a.flags[k] = E.F_ALIVE | E.F_INDOORS
            a.node[k] = a.dest[k] = INSIDE[k]
            a.edge[k] = E.NO_EDGE
            a.task[k] = NO_TASK
            a.health[k] = a.food[k] = a.water[k] = a.sleep[k] = a.o2[k] = 200
            for f, v in people.get(k, {}).items():
                getattr(a, f)[k] = v
        for r in gone:
            st.e.room_n[r] = 0
        st.far = list(far)
        return st

    def load(self, st, patch=()):
        import cpc
        m = S.z80_load(self.sym, self.g, st, patch=patch)
        m.poke(self.sym["PIN_SLOT"], E.WH_NMOVE)      # η πρώτη θέση αναγκών (8 ως το βήμα 172)
        b1 = cpc._lib.cpcemu_ram_ptr(m._h, 1)
        for i, room in st.far:                 # το DIST της τράπεζας 1
            for k in range(st.e.room_n[room]):
                d, n = st.e.room_list[room * EC.ROOM_MAX + k], st.a.node[i]
                # από δομή, η γραμμή του θόλου (βήμα 153): το ίδιο byte είναι και
                # το DIST[d][n], και η αναφορά το μαθαίνει κι αυτό
                b1[S.G.zd_off(n, d)] = 255
                st.e.dist[n * 128 + d] = 255
                if n >= S.G.MAX_DOME:
                    st.e.dist[d * 128 + n] = 255
        return m

    def run(self, st, ticks=4, patch=()):
        m = self.load(st, patch)
        m.poke(self.sym["TICK_COUNT"], ticks)
        m.poke(self.sym["TICK_COUNT"] + 1, 0)
        S.enter(m, self.sym, "RUN_TICKS")
        S.enter(m, self.sym, "SAVE_STATE")
        return E.Agents().from_bytes(m.read_ram(S.STAGE_AG, S.AG_BYTES))

    def cost(self, st, n=60, patch=()):
        m = self.load(st, patch)
        t = [S.tick_us(m, self.sym) for _ in range(n)]
        return max(t)

    def room_of(self, st, d):
        return st.e.dome[d * EC.DOME_REC + EC.D_ROOM] if d < EC.MAX_DOME else None


def code(rig):
    """Οι διευθύνσεις των αρνητικών: τα jr nz,nd_want του ιατρείου και του
    κοιτώνα (μετά το ld a,(G_room_n + R)), και το jr z,nd_far."""
    sym = rig.sym
    m = S.z80_load(sym, rig.g, rig.state({}))
    rn = sym["G_ROOM_N"]

    def after_load(room):
        pat = [0x3A, (rn + room) & 255, (rn + room) >> 8, 0xB7, 0x3E, room, 0x20]
        blob = m.read_ram(sym["ND_SEEK0"], 200)
        k = bytes(blob).find(bytes(pat))
        assert k >= 0, f"δεν βρέθηκε ο έλεγχος του δωματίου {room}"
        return sym["ND_SEEK0"] + k + len(pat) - 1         # το 20 (jr nz)

    blob = m.read_ram(sym["ND_SEARCH"], 40)
    k = next(j for j in range(36) if blob[j] == 0x3C and blob[j + 1] == 0x28)  # inc a / jr z
    return dict(med=after_load(EC.R_MEDBAY), bed=after_load(EC.R_QUARTERS),
                far=sym["ND_SEARCH"] + k + 1)


def main():
    rig = Rig()
    at = code(rig)
    old_far = [(at["far"], 0xC8), (at["far"] + 1, 0x00)]          # ret z / nop
    no_bed = [(at["bed"], 0x18)]                                   # jr nd_want
    no_med = [(at["med"], 0x18)]
    q = EC.R_QUARTERS

    # --- ΧΩΡΙΣ ΚΟΙΤΩΝΑ ---
    def nobed():
        return rig.state({0: dict(sleep=30, task=T_NEED, dest=INSIDE[0]),
                          1: dict(sleep=30)}, gone=[q])
    a = rig.run(nobed())
    check(a.task[0] == NO_TASK and a.task[1] == NO_TASK and a.dest[1] == INSIDE[1],
          f"ΧΩΡΙΣ ΚΟΙΤΩΝΑ: ο νυσταγμένος με T_NEED το αφήνει ({a.task[0]}), ο "
          f"νυσταγμένος χωρίς εργασία μένει ({a.task[1]}, προς {a.dest[1]})")
    a = rig.run(nobed(), patch=old_far + no_bed)
    check(a.task[0] == T_NEED, f"ΑΡΝΗΤΙΚΟ ΧΩΡΙΣ ΚΟΙΤΩΝΑ: όπως ως το 119, το T_NEED "
          f"μένει ({a.task[0]})")

    # --- ΧΩΡΙΣ ΙΑΤΡΕΙΟ ---
    def nomed():
        # ο 2 σε θόλο οξυγόνου, όχι στο κυλικείο όπου στέκεται κανονικά: εκεί
        # θα έπινε χωρίς να χρειαστεί να πάει πουθενά
        return rig.state({2: dict(health=30, water=30, node=INSIDE[0], dest=INSIDE[0]),
                          3: dict(health=30, sleep=30)}, gone=[EC.R_MEDBAY])
    st = nomed()
    a = rig.run(st)
    r2, r3 = rig.room_of(st, a.dest[2]), rig.room_of(st, a.dest[3])
    check(a.task[2] == T_NEED and r2 == EC.R_CANTEEN and a.task[3] == T_NEED and r3 == q,
          f"ΧΩΡΙΣ ΙΑΤΡΕΙΟ: ο τραυματίας και διψασμένος στο κυλικείο (δωμάτιο {r2}, "
          f"εργασία {a.task[2]}), ο τραυματίας και νυσταγμένος στον κοιτώνα ({r3}, "
          f"εργασία {a.task[3]})")
    st = nomed()
    a = rig.run(st, patch=no_med)
    check(a.task[2] != T_NEED, f"ΑΡΝΗΤΙΚΟ ΧΩΡΙΣ ΙΑΤΡΕΙΟ: χωρίς τον έλεγχο, ο "
          f"τραυματίας δεν πάει να πιει ({a.task[2]})")

    # --- ΑΠΡΟΣΙΤΟ ---
    def far():
        return rig.state({4: dict(sleep=30, task=T_NEED)}, far=[(4, q)])
    a = rig.run(far())
    check(a.task[4] == NO_TASK, f"ΑΠΡΟΣΙΤΟ: κοιτώνας χωρίς δρόμο, το T_NEED σβήνει "
          f"({a.task[4]})")
    a = rig.run(far(), patch=old_far)
    check(a.task[4] == T_NEED, f"ΑΡΝΗΤΙΚΟ ΑΠΡΟΣΙΤΟ: με nd_far = ret z μένει "
          f"({a.task[4]})")

    # --- ΜΕ ΟΛΑ ---
    st = rig.state({5: dict(sleep=30), 6: dict(health=30), 7: dict(task=T_NEED)})
    a = rig.run(st)
    r5, r6 = rig.room_of(st, a.dest[5]), rig.room_of(st, a.dest[6])
    check(a.task[5] == T_NEED and r5 == q and a.task[6] == T_NEED and r6 == EC.R_MEDBAY
          and a.task[7] == NO_TASK,
          f"ΜΕ ΟΛΑ: νυσταγμένος στον κοιτώνα ({r5}), τραυματίας στο ιατρείο ({r6}), "
          f"ο χορτάτος αφήνει το T_NEED ({a.task[7]})")

    # --- ΑΝΑΦΟΡΑ ---
    for name, st in (("χωρίς κοιτώνα", nobed()), ("χωρίς ιατρείο", nomed()),
                     ("απρόσιτο", far())):
        m = rig.load(st)
        m.poke(rig.sym["TICK_COUNT"], 4)
        m.poke(rig.sym["TICK_COUNT"] + 1, 0)
        S.enter(m, rig.sym, "RUN_TICKS")
        S.enter(m, rig.sym, "SAVE_STATE")
        got = m.read_ram(S.STAGE_AG, S.AG_BYTES)
        for _ in range(4):
            E.needs_slice(st.a, st.e, st.occ, 0, NSL)
        check(bytes(got) == st.a.to_bytes(), f"ΑΝΑΦΟΡΑ {name}: ίδια bytes στον Z80 "
              f"και στο tools/entity.py")

    # --- ΚΟΣΤΟΣ ---
    def every(**kw):
        return {k: dict(kw) for k in range(NSL)}
    out = {k: dict(flags=E.F_ALIVE, node=(63, 62, 48)[k % 3], dest=(63, 62, 48)[k % 3],
                   water=30, suit=200) for k in range(NSL)}
    cases = {"μέσα, νυσταγμένοι": rig.state(every(sleep=30)),
             "μέσα, χορτάτοι": rig.state({}),
             "νυσταγμένοι χωρίς κοιτώνα": rig.state(every(sleep=30), gone=[q]),
             "τραυματίες χωρίς ιατρείο": rig.state(every(health=30), gone=[EC.R_MEDBAY]),
             "έξω, απρόσιτοι, διψασμένοι": rig.state(out)}
    got = {}
    for name, st in cases.items():
        got[name] = rig.cost(st)
        check(got[name] <= CEIL[name], f"ΚΟΣΤΟΣ {name}: {got[name]} µs (ταβάνι "
              f"{CEIL[name]})")
    worse = rig.cost(rig.state(every(sleep=30), gone=[q]), patch=no_bed)
    check(worse > CEIL["νυσταγμένοι χωρίς κοιτώνα"],
          f"ΑΡΝΗΤΙΚΟ ΚΟΣΤΟΣ: χωρίς τον έλεγχο του κοιτώνα οι νυσταγμένοι ψάχνουν σε "
          f"κάθε επίσκεψη, {worse} µs")

    # --- ΣΤΟ ΠΑΙΧΝΙΔΙ ---
    import play as P
    P.make([(0xACE1, 0)])
    game(False)
    game(True)
    if FAIL:
        print(f"\n{len(FAIL)} ΑΠΟΤΥΧΙΕΣ")
        return 1
    print("\nΟΛΑ ΚΑΛΑ")
    return 0


def game(old):
    """Το άνοιγμα του tools/play.py ως το sol 2,4 στο main.sna. old: ο κώδικας
    όπως ως το βήμα 119 (στο b6code, tests/codeat.py)."""
    import play as P
    import codeat
    sym, g = P.syms()
    G = P.Game(sym, g, P.sna_path(0xACE1, 0))
    if old:
        m = G.m
        rn = P.layout()["G_room_n"]
        bed = codeat.find(m, sym["ND_SEEK0"], [0x3A, (rn + 2) & 255, (rn + 2) >> 8,
                                               0xB7, 0x3E, 2, 0x20])
        codeat.poke(m, bed + 6, 0x18)
        far = codeat.find(m, sym["ND_SEARCH"], [0x4F, 0x3C, 0x28], 40)
        codeat.poke(m, far + 2, 0xC8)
        codeat.poke(m, far + 3, 0x00)
    P.play(G, P.plan_base(), 2.4)
    ag = {i: a for i, a in G.agents().items() if i < 80}
    tasks = [a["task"] for a in ag.values()]
    # Ενα T_NEED χωρίς λόγο: υγεία, τροφή και νερό πάνω από το κατώφλι — το
    # μόνο που λείπει είναι ο ύπνος, και κοιτώνας δεν υπάρχει ακόμη.
    stuck = [i for i, a in ag.items() if a["task"] == T_NEED
             and min(a["health"], a["food"], a["water"]) >= 64]
    sleepy = sum(1 for a in ag.values() if a["sleep"] < 64)
    if not old:
        check(not stuck and sleepy == len(ag) == 6,
              f"ΣΤΟ ΠΑΙΧΝΙΔΙ: sol {G.sol():.2f}, νυσταγμένοι {sleepy} από {len(ag)}, "
              f"κανείς δεν κρατά T_NEED χωρίς λόγο (εργασίες {tasks})")
        return
    check(len(stuck) >= 4, f"ΑΡΝΗΤΙΚΟ ΣΤΟ ΠΑΙΧΝΙΔΙ: όπως ως το 119, {len(stuck)} από "
          f"{len(ag)} κρατούν T_NEED με φαΐ και νερό ({tasks})")


if __name__ == "__main__":
    sys.exit(main())
