#!/usr/bin/env python3
"""Ο,τι άφηνε πίσω της η κατεδάφιση (βήμα 116, DESIGN §9.3).

Τρία κενά του §15, από τα βήματα 101-102:

  ΕΡΓΟΤΑΞΙΟ  Ενας θόλος που χτίζεται έχει μία ακμή, τη σύνδεση εδάφους ως το
             κοντινότερο airlock ή το σκάφος· οι διάδρομοί του γίνονται ακμές
             όταν τελειώσει. Ως το 115, όταν γκρεμιζόταν εκείνο το airlock, ο
             θόλος έμενε χωρίς ακμή και δεν τον έφτανε κανείς. Τώρα (dm_sites)
             παίρνει σύνδεση εδάφους ως το επόμενο κοντινότερο, χωρίς ζωγραφιά,
             όπως στην τοποθέτηση — και χτίζεται. Στην αποικία δοκιμών: ένα
             airlock, ένας θόλος S που κρέμεται από αυτό, το airlock φεύγει.
  ΣΚΑΦΟΣ     Ενα ορφανό που ο γκρεμισμένος δεν κρεμόταν από πουθενά (ένα σώσιμο
             πριν από το βήμα 102) κρέμεται από το σκάφος, τη ρίζα όλων
             (dm_up), με σύνδεση εδάφους ζωγραφισμένη. Στο main.sna: ηλιακός S1
             με σύνδεση εδάφους ως το σκάφος, S2 με μονοπάτι ως τον S1, S3 ως
             τον S2. Φεύγει ο S2, και ο S3 κρέμεται από τον S1, τον γονιό του·
             μετά, με το LK_OWN του S1 σβησμένο, φεύγει ο S1, και ο S3 κρέμεται
             από το σκάφος.
  ΠΡΟΓΟΝΟΣ   Το dm_up απέναντι στον κανόνα, σε πίνακες: ο γονιός αν έχει θέση
             για ακμή, αλλιώς ο δικός του γονιός και πάει λέγοντας, χωρίς γονιό
             το σκάφος αν η δομή 0 είναι σκάφος, 255 αν κανένας — και ένας κύκλος
             στα LK_OWN τελειώνει.
  ΚΟΣΤΟΣ     Το dm_sites περνά τους 64 θόλους σε κάθε κατεδάφιση: 1.475 us στην
             αποικία δοκιμών (ταβάνι 1.600), 1.902 αν όλοι οι θόλοι είναι
             εργοτάξια με ακμή (ταβάνι 2.000) — μέσα σε ένα frame κατεδάφισης
             των 85-92 ms. Κάθε θόλος που ξαναδένεται κοστίζει ~1,35 ms ακόμη.
  ΦΟΡΤΙΟ     Μια Haul με το φορτίο της (J_NODE ≠ J_SITE) της οποίας γκρεμίζεται
             ο προορισμός ή το ορυχείο το παραδίδει στα αποθέματα: +10
             μεταλλεύματα. Μια Haul χωρίς φορτίο, ή άλλου κόμβου, όχι.

Για το ΕΡΓΟΤΑΞΙΟ και το ΣΚΑΦΟΣ, ο κόσμος, τα LK_OWN, οι ακμές και η οθόνη μετά
είναι ό,τι λέει το μοντέλο του tests/test_unlink.py (expect, after), που
ξέρει από αυτό το βήμα και τα δύο.

Αρνητικά, με τον κώδικα πειραγμένο: χωρίς το call dm_sites (ο θόλος μένει χωρίς
ακμή και δεν χτίζεται)· το σκάφος δεν αναγνωρίζεται (cp K_SHIP -> cp 255)· ο
γονιός ξεχνιέται (ήταν του tests/test_unlink.py, όπου ο γονιός είναι πια
πάντα το σκάφος και το σκάφος είναι και η εφεδρεία)·
χωρίς ανάβαση (djnz dmu_lp -> nop)· το LK_OWN με το bit 7 (and #3F -> and #BF)·
χωρίς το call dm_haul (τα φορτία χάνονται)· ΚΟΣΤΟΣ: κάθε εργοτάξιο
ξαναδένεται, ακόμη κι αν έχει ακμή (χωρίς το jr nz του βαθμού).
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import test_demolish as D                                # noqa: E402
import test_unlink as U                                  # noqa: E402
import codeat                                            # noqa: E402
import cpc                                               # noqa: E402

FAIL = []
L = D.L
DOME_S, SOLAR, AIRLOCK = 0, 4, 9                         # σειρές του bld_items
K_SHIP, K_PAD = 7, 6
J_HAUL, S_ORE, NO_JOB = 2, 2, 255
BUILT_IN = 20_000                                        # frames ως να χτιστεί ο θόλος
PROBE = 0x3E80                                           # όπως του tests/test_bots.py


def check(ok, msg):
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ ") + msg, flush=True)
    if not ok:
        FAIL.append(msg)


def ore(G):
    return G.m.peek(L["G_econ_state"] + 2 * S_ORE) | G.m.peek(L["G_econ_state"] + 2 * S_ORE + 1) << 8


# --------------------------------------------------------------------------
# ΕΡΓΟΤΑΞΙΟ
# --------------------------------------------------------------------------
def site(sym, g, patch=(), quiet=False):
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G, F = D.game(sym, g, patch)
    G.run(500_000)
    G.settle()
    c = U.tile(D.centre(G, 1))
    at, _ = U.find_spot(G, sym, AIRLOCK, lambda r, a: bool(r["corridors"]), (c[0] + 7, c[1] + 3))
    a = at and U.place(G, sym, g, AIRLOCK, at)
    if not a:
        return f"ΕΡΓΟΤΑΞΙΟ: το airlock δεν μπήκε ({at})"
    ca = U.tile(D.centre(G, a))
    at2, _ = U.find_spot(G, sym, DOME_S,
                         lambda r, p: bool(r["corridors"]) and U.anchor_is(G, a)(r, p),
                         (ca[0] + 3, ca[1] + 3))
    d = at2 and U.place(G, sym, g, DOME_S, at2)
    if d is None or d is False or d >= 64 or D.rec(G, d)[4] != 1:
        return f"ΕΡΓΟΤΑΞΙΟ: ο θόλος δεν μπήκε κοντά στο airlock {a} ({at2}, {d})"
    if D.adj(G, d) != [a]:
        return f"ΕΡΓΟΤΑΞΙΟ: ο θόλος {d} κρέμεται από {D.adj(G, d)}, όχι από το {a}"
    G.camera(ca[0] - 10, ca[1] - 5)
    s = U.snap_at(G, a)
    err, worst = U.gone_at(G, F, s, a, "ΕΡΓΟΤΑΞΙΟ")
    if err:
        return err
    if len(D.adj(G, d)) != 1:
        return f"ΕΡΓΟΤΑΞΙΟ: μετά, ο θόλος {d} έχει ακμές {D.adj(G, d)}"
    to = D.adj(G, d)[0]
    t = 0
    while t < BUILT_IN and D.rec(G, d)[4] != 2:
        G.m.run_frames(250)
        t += 250
    if D.rec(G, d)[4] != 2:
        return f"ΕΡΓΟΤΑΞΙΟ: ο θόλος {d} δεν χτίστηκε σε {BUILT_IN} frames ({D.rec(G, d)[:8]})"
    say(f"ΕΡΓΟΤΑΞΙΟ: το airlock {a} έφυγε, ο θόλος {d} κρέμεται πια από τον {to}, "
        f"χτίστηκε σε {t} frames· ο χειρότερος γύρος {worst / 1000:.1f} ms")
    return None


# --------------------------------------------------------------------------
# ΣΚΑΦΟΣ
# --------------------------------------------------------------------------
def ship(sym, g, patch=(), quiet=False):
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G, F = D.game(sym, g, patch, TG.SNA)
    G.run(500_000)
    G.settle()
    c = U.tile(D.centre(G, 64))
    at1, _ = U.find_spot(G, sym, SOLAR, lambda r, a: r["path"] is None, (c[0] + 6, c[1]))
    s1 = at1 and U.place(G, sym, g, SOLAR, at1)
    if not s1 or U.own(G, s1) != U.gnd(64):
        return f"ΣΚΑΦΟΣ: ο S1 στο {at1}: {s1}, LK_OWN #{U.own(G, s1 or 64):02X}, όχι σύνδεση εδάφους ως το 64"
    c1 = U.tile(D.centre(G, s1))
    at2, _ = U.find_spot(G, sym, SOLAR, U.path_to(s1, None, 2), (c1[0] + 5, c1[1] + 2))
    s2 = at2 and U.place(G, sym, g, SOLAR, at2)
    if not s2 or U.end(U.own(G, s2)) != s1:
        return f"ΣΚΑΦΟΣ: ο S2 στο {at2}: {s2}, LK_OWN #{U.own(G, s2 or 64):02X}"
    c2 = U.tile(D.centre(G, s2))
    at3, _ = U.find_spot(G, sym, SOLAR, U.path_to(s2, None, 2), (c2[0] + 4, c2[1] - 3))
    s3 = at3 and U.place(G, sym, g, SOLAR, at3)
    if not s3 or U.end(U.own(G, s3)) != s2:
        return f"ΣΚΑΦΟΣ: ο S3 στο {at3}: {s3}, LK_OWN #{U.own(G, s3 or 64):02X}"
    G.camera(c1[0] - 8, c1[1] - 5)
    # ΠΡΩΤΑ Ο S2: ο γονιός του είναι ο S1, όχι το σκάφος, και ο S3 κρέμεται από
    # αυτόν — ένα dm_par που ξεχνιέται θα τον έδενε στο σκάφος.
    s = U.snap_at(G, s2)
    err, worst = U.gone_at(G, F, s, s2, "ΣΚΑΦΟΣ, ο S2")
    if err:
        return err
    if U.own(G, s3) != U.gnd(s1):
        return f"ΣΚΑΦΟΣ: ο S2 έφυγε, ο S3 {s3}: LK_OWN #{U.own(G, s3):02X}, όχι ο S1 {s1}"
    # ΜΕΤΑ Ο S1, σαν από ένα σώσιμο πριν από το 102: κανένα LK_OWN. Η σύνδεσή του
    # είναι εδάφους, χωρίς bit 5 στα tiles της: τίποτε άλλο δεν θα το έλεγε.
    G.m.poke(U.LK_OWN + s1, U.NONE)
    s = U.snap_at(G, s1)
    err, worst2 = U.gone_at(G, F, s, s1, "ΣΚΑΦΟΣ, ο S1")
    if err:
        return err
    if U.own(G, s3) != U.gnd(64) or 64 not in D.adj(G, s3):
        return f"ΣΚΑΦΟΣ: ο S3 {s3}: LK_OWN #{U.own(G, s3):02X}, ακμές {D.adj(G, s3)}"
    if not quiet:
        U.shot(G, "leftover_ship.png")
    say(f"ΣΚΑΦΟΣ: ο S2 {s2} έφυγε και ο S3 {s3} κρεμάστηκε από τον S1 {s1}· μετά ο S1 "
        f"έφυγε χωρίς γονιό, και ο S3 κρέμεται από το σκάφος (#{U.own(G, s3):02X}), με "
        f"τη σύνδεση εδάφους στον κόσμο· οι χειρότεροι γύροι {worst / 1000:.1f} και "
        f"{worst2 / 1000:.1f} ms")
    return None


# --------------------------------------------------------------------------
# ΠΡΟΓΟΝΟΣ
# --------------------------------------------------------------------------
def up_rule(deg, own, ship_kind, p):
    if p == 255:
        if ship_kind != K_SHIP:
            return 255
        p = 64
    for _ in range(U.NS):                   # το B = MAX_STRUCT του dm_up
        if deg[p] < 8:
            return p
        p = U.end(own.get(p, U.NONE))
        if p >= 64 + U.NS:
            return 255
    return 255


UP_CASES = [
    # (A, βαθμοί, LK_OWN, είδος της δομής 0)
    (70, {70: 3}, {}, K_SHIP),
    (70, {70: 8, 66: 2}, {70: U.gnd(66)}, K_SHIP),
    (70, {70: 8, 66: 8, 65: 7}, {70: 66 | 0x80, 66: 65}, K_SHIP),
    (70, {70: 8}, {}, K_SHIP),
    (255, {64: 2}, {}, K_SHIP),
    (255, {64: 8}, {}, K_SHIP),
    (255, {64: 2}, {}, K_PAD),
    (70, {70: 8, 66: 8, 64: 1}, {70: 66 | 0x80, 66: U.gnd(64)}, K_SHIP),
    (70, {70: 8, 66: 8}, {70: 66, 66: 70}, K_SHIP),          # κύκλος: τελειώνει
]


def ancestors(sym, patch=()):
    """Η πρώτη διαφορά του dm_up από τον κανόνα, ή None."""
    m = cpc.CPC()
    m.run_frames(60)
    assert m.quickload(TG.SNA, start=False)
    for at, v in patch:
        codeat.poke(m, at, v)
    b6 = cpc._lib.cpcemu_ram_ptr(m._h, 6)
    up, res = sym["DM_UP"], sym["DM_N"]                   # το αποτέλεσμα στο dm_n
    for a, deg, own, kind in UP_CASES:
        for n in range(128):
            m.poke(L["G_rt_nodes"] + n, 0)
        for n, v in deg.items():
            m.poke(L["G_rt_nodes"] + n, v)
        for n in range(64, 64 + U.NS):
            m.poke(U.LK_OWN + n, own.get(n, U.NONE))
        b6[L["G_struct_tbl"] - 0x4000 + 2] = kind
        full = [deg.get(n, 0) for n in range(128)]
        want = up_rule(full, own, kind, a)
        # di · ld sp · ld bc,#7FC0 · out (c),c · ld a,A · call dm_up · ld (dm_n),a · jr $
        code = [0xF3, 0x31, 0x00, 0x01, 0x01, 0xC0, 0x7F, 0xED, 0x49, 0x3E, a,
                0xCD, up & 255, up >> 8, 0x32, res & 255, res >> 8, 0x18, 0xFE]
        m.write_ram(PROBE, bytes(code))
        m.set_pc(PROBE)
        end, t = PROBE + len(code) - 2, 0
        while not (end <= m.pc <= end + 2) and t < 20_000:
            m.run_us(20)
            t += 20
        if t >= 20_000:
            return f"A={a} {deg} {own}: δεν γύρισε"
        if m.peek(res) != want:
            return f"A={a} βαθμοί {deg} LK_OWN {own} δομή 0 {kind}: {m.peek(res)}, ο κανόνας {want}"
    return None


# --------------------------------------------------------------------------
# ΚΟΣΤΟΣ
# --------------------------------------------------------------------------
CEIL_SITES = (1600, 2000)                                # us: κανένα εργοτάξιο, όλα με ακμή


def sites_cost(sym, patch=()):
    """(us χωρίς εργοτάξιο, us με τους 64 θόλους εργοτάξια με ακμή)."""
    out = []
    for every in (False, True):
        m = cpc.CPC()
        m.run_frames(60)
        assert m.quickload(TG.COLONY)
        m.run_frames(300)
        for at, v in patch:
            codeat.poke(m, at, v)
        b6 = cpc._lib.cpcemu_ram_ptr(m._h, 6)
        if every:
            for d in range(64):
                base = L["G_dome_tbl"] - 0x4000 + 24 * d
                if b6[base + 4] == 0:
                    b6[base + 4], b6[base], b6[base + 1] = 1, (d % 8) * 8, (d // 8) * 8
                    m.poke(L["G_rt_nodes"] + d, 1)
        a = sym["DM_SITES"]
        code = [0xF3, 0x31, 0x00, 0x01, 0x01, 0xC0, 0x7F, 0xED, 0x49,
                0xCD, a & 255, a >> 8, 0x18, 0xFE]
        m.write_ram(PROBE, bytes(code))
        m.set_pc(PROBE)
        end, t = PROBE + len(code) - 2, 0
        while not (end <= m.pc <= end + 2) and t < 400_000:
            m.run_us(1)
            t += 1
        out.append(t)
    return tuple(out)


# --------------------------------------------------------------------------
# ΦΟΡΤΙΟ
# --------------------------------------------------------------------------
def loads(sym, g, patch=(), quiet=False):
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G, F = D.game(sym, g, patch)
    G.run(500_000)
    G.settle()
    jt = L["G_job_tbl"]
    # Η αποικία δοκιμών: θόλοι 0-2, η πίστα 64 και το airlock 65. Ο θόλος 1 και
    # το 65 γκρεμίζονται· η πίστα είναι μόνο ένα J_SITE που δεν πειράζεται.
    x, y, m1, m2 = 1, 2, 64, 65
    if [D.rec(G, n)[4] for n in (x, y, m1, m2)] != [2, 2, 2, 2]:
        return f"ΦΟΡΤΙΟ: η αποικία δεν έχει τους 1, 2, 64, 65"
    for i in range(16):                                  # ο τροχός σταματά: κανείς δεν
        G.m.poke(sym["WH_ON"] + i, 0)                    # φτιάχνει ή τρώει μεταλλεύματα
    out = []
    for gone, jobs, want_ore, want_jobs in (
            # ο προορισμός x γκρεμίζεται: η φορτωμένη παραδίδει, και ξαναδείχνει το ορυχείο
            (x, [[J_HAUL, x, 255, 5, m1], [J_HAUL, m1, 255, 5, m1], [J_HAUL, y, 255, 5, m2]],
             10, [[J_HAUL, m1, 255, 5, m1], [J_HAUL, m1, 255, 5, m1], [J_HAUL, y, 255, 5, m2]]),
            # το ορυχείο m2 γκρεμίζεται: η φορτωμένη από αυτό παραδίδει, η άδεια όχι
            (m2, [[J_HAUL, y, 255, 5, m2], [J_HAUL, m2, 255, 5, m2], [J_HAUL, y, 255, 5, m1]],
             10, [None, None, [J_HAUL, y, 255, 5, m1]])):
        G.m.write_ram(jt, bytes([NO_JOB] * 160))
        for j, r in enumerate(jobs):
            G.m.write_ram(jt + 5 * j, bytes(r))
        o0 = ore(G)
        D.demolish(G, F, D.centre(G, gone))
        if D.rec(G, gone)[4]:
            return f"ΦΟΡΤΙΟ: ο {gone} δεν γκρεμίστηκε"
        got = [list(G.m.read_ram(jt + 5 * j, 5)) for j in range(3)]
        got = [None if r[0] == NO_JOB else r for r in got]
        if ore(G) - o0 != want_ore or got != want_jobs:
            return (f"ΦΟΡΤΙΟ, ο {gone} γκρεμίζεται: μεταλλεύματα {o0} -> {ore(G)} (θέλει +{want_ore}), "
                    f"εργασίες {got}, θέλει {want_jobs}")
        out.append(f"ο {gone} γκρεμίστηκε: +{ore(G) - o0} μεταλλεύματα, εργασίες {got}")
    say("ΦΟΡΤΙΟ: " + "· ".join(out))
    return None


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

    def raw(p):
        return p and [(at, v) for _, at, v in p]

    return [
        ("χωρίς το call dm_sites", ovl("DMV_LP", 48, cd("DM_SITES"), nop3), site),
        ("το σκάφος δεν αναγνωρίζεται", ram("DM_UP", 24, [0xFE, K_SHIP], [(1, 255)]), ship),
        ("ο γονιός ξεχνιέται (από το test_unlink)",
         ovl("DMP_OWN", 6, [0x32] + w(sym["DM_PAR"]), nop3), ship),
        ("χωρίς το call dm_haul", ovl("DMJ_LP", 16, cd("DM_HAUL"), nop3), loads),
        ("χωρίς ανάβαση", raw(ram("DM_UP", 48, [0x30, 2, 0x10], [(2, 0), (3, 0)])), ancestors),
        ("το LK_OWN με το bit 7", raw(ram("DM_UP", 48, [0xE6, 0x3F], [(1, 0xBF)])), ancestors),
        ("κάθε εργοτάξιο ξαναδένεται", raw(ram("DM_SITES", 24, [0xB6, 0x20], [(1, 0), (2, 0)])),
         sites_cost),
    ]


def main():
    sym, g = TG.build()
    why = ancestors(sym)
    check(why is None, "ΠΡΟΓΟΝΟΣ: το dm_up = ο κανόνας σε 9 πίνακες (γονιός, πρόγονοι, σκάφος, "
          "κανένας, κύκλος)" + (f" — ΟΧΙ: {why}" if why else ""))
    cost = sites_cost(sym)
    check(cost[0] <= CEIL_SITES[0] and cost[1] <= CEIL_SITES[1],
          f"ΚΟΣΤΟΣ: dm_sites {cost[0]} us χωρίς εργοτάξιο (ταβάνι {CEIL_SITES[0]}), "
          f"{cost[1]} us με 64 εργοτάξια με ακμή (ταβάνι {CEIL_SITES[1]})")
    for fn, what in ((site, "ΕΡΓΟΤΑΞΙΟ: ο θόλος που έχασε το airlock του ξαναδένεται και χτίζεται"),
                     (ship, "ΣΚΑΦΟΣ: το ορφανό χωρίς γονιό κρέμεται από το σκάφος"),
                     (loads, "ΦΟΡΤΙΟ: ό,τι κουβαλούσε μια Haul παραδίδεται")):
        try:
            err = fn(sym, g)
        except AssertionError as e:
            err = f"assert: {e}"
        check(err is None, err or what)
    for label, patch, test in negatives(sym, g):
        if not patch:
            check(False, f"ΑΡΝΗΤΙΚΟ «{label}»: το μοτίβο δεν βρέθηκε")
            continue
        try:
            if test is ancestors:
                err = test(sym, patch)
            elif test is sites_cost:
                c = test(sym, patch)
                err = None if c[1] <= CEIL_SITES[1] else f"ΚΟΣΤΟΣ: {c[1]} us > {CEIL_SITES[1]}"
            else:
                err = test(sym, g, patch, quiet=True)
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
        check(err is not None, f"ΑΡΝΗΤΙΚΟ «{label}»: {err or 'ΔΕΝ ΠΙΑΣΤΗΚΕ'}")
    if FAIL:
        print(f"\n{len(FAIL)} ΑΠΟΤΥΧΙΕΣ")
        sys.exit(1)
    print("\nΟΛΑ ΚΑΛΑ")


if __name__ == "__main__":
    main()
