#!/usr/bin/env python3
"""Το μπλοκ των αποστάσεων των δομών και οι τρεις τρύπες (βήμα 155, DESIGN §4.2).

Με 112 κόμβους οι γραμμές του DIST δεν χωρούν για όλους: οι 64 γραμμές των
θόλων κρατούν όλες τις στήλες, και κάθε δομή μόνο τις στήλες των δομών, σε
ΜΠΛΟΚ των 64 bytes ανά γραμμή στο DB_ROW (#6400, src/const.asm). Ο κώδικας
που ζούσε στις στήλες 96-127 πήγε σε τρία σημεία (src/ov_inst.asm).

Η πρόζα:

  ΓΡΑΜΜΗ     Το blk_row (src/jobs.asm), για κάθε κόμβο δομής s 64-111: H η
             σελίδα της γραμμής του στο μπλοκ, και L + t, σε 8 bits, η στήλη
             της δομής t, για κάθε t 64-111: DB_ROW + 64 (s - 64) + t - 64.
  ΕΡΓΑΣΙΑ    Το jb_best από δομή και από θόλο, με στόχους θόλους ΚΑΙ δομές:
             ως θόλο η γραμμή του θόλου (στη στήλη της πηγής), ως δομή από δομή
             η γραμμή της πηγής στο μπλοκ. Η εργασία που διαλέγει είναι του
             κανόνα: ανοιχτή, του ρόλου, η μεγαλύτερη προτεραιότητα, μετά η
             μικρότερη απόσταση, στην ισοπαλία η πρώτη.
  AIRLOCK    Το su_lock από δομή (η γραμμή της στο μπλοκ) και από θόλο: το
             κοντινότερο ΕΤΟΙΜΟ airlock που φτάνεται, στην ισοπαλία η πρώτη δομή.
  ΠΗΓΗ       Το sp_take από δομή και από θόλο: το σκάφος — από δομή η γραμμή
             του σκάφους στο μπλοκ — ή η κοντινότερη αποθήκη, που είναι θόλος:
             η γραμμή της. Στην ισοπαλία το σκάφος· χωρίς καμία, το εργοτάξιο.
  ΤΡΥΠΕΣ     Μετά την εκκίνηση της αποικίας δοκιμών και μια πλήρη
             δρομολόγηση, το OV_R1, το OV_R2 και το OV_R3 έχουν ό,τι λέει το
             build (tests/ovmap.py) — και ολόκληρη η εικόνα του OV_LOAD είναι
             πια μπλοκ: το rt_flush γράφει τη γραμμή κάθε δομής εκεί.

Σε κάθε σκηνή οι αποστάσεις είναι τυχαίες σε ΟΛΗ την τράπεζα 1, όχι μόνο εκεί
που διαβάζει ο σωστός αναγνώστης: ο λάθος βρίσκει άλλους αριθμούς και άλλη
απάντηση. Κόμβοι ως το 111, αν και το παιχνίδι έχει 32 δομές ως το βήμα 156.
Τυχαίες και άρα όχι συμμετρικές: η σκηνή ορίζει ΠΟΙΑ γραμμή διαβάζει κάθε
αναγνώστης· στο παιχνίδι η απόσταση από το a στο b είναι ίδια και στις δύο.

Αρνητικά, με τον κώδικα πειραγμένο: το jb_best χωρίς το jr nc,jbs_bk (στόχος
δομή από τη γραμμή του θόλου, όπως ως το 154)· το su_lock χωρίς το jr
nc,sul_st· το sp_take χωρίς το jr nc,sps_bk· το blk_row με τη γραμμή μία πιο
κάτω (add a,#C0 -> add a,#00)· το ov_install χωρίς το call ovi_half, που
φέρνει μόνο το πρώτο μισό της κατεδάφισης.
"""
import os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import test_twopage as TP                                # noqa: E402
import codeat                                            # noqa: E402
import ovmap as OV                                       # noqa: E402
import graph as GR                                       # noqa: E402
import cpc                                               # noqa: E402

FAIL = []
NODES = range(64, 112)                                   # οι δομές, ως το NODE_CAP
DB_ROW = 0x4000 + GR.DB_OFF
NO_JOB, MAX_JOB, JOB_REC = 255, 32, 5
K_AIRLOCK, K_SHIP, DS_BUILDING, DS_ACTIVE = 5, 7, 1, 2
R_STORAGE, ROOM_MAX = 6, 8
L = TP.L


def check(ok, msg):
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ ") + msg)
    if not ok:
        FAIL.append(msg)


def scatter(M_, rnd):
    """Τυχαίες αποστάσεις σε ολόκληρη την τράπεζα 1 ως τα εικονίδια."""
    for o in range(0x3000):
        M_.b1[o] = rnd.choice((1, 2, 3, 5, 8, 13, 21, 34, 60, 100, 254, 255))


def dist(M_, a, b):
    """Το DIST[a][b] εκεί που το έχει το βήμα 155 (tools/graph.py, zd_off)."""
    return M_.b1[GR.zd_off(a, b)]


# --------------------------------------------------------------------------
# ΓΡΑΜΜΗ
# --------------------------------------------------------------------------
def rows(sym, patch=()):
    M_ = TP.M(sym, patch)
    for s in NODES:
        hl = M_.call("BLK_ROW", a=s)["hl"]
        for t in NODES:
            got = (hl & 0xFF00) | ((hl + t) & 255)
            want = DB_ROW + 64 * (s - 64) + t - 64
            if got != want:
                return f"blk_row({s}) = #{hl:04X}: η στήλη του {t} στο #{got:04X}, όχι στο #{want:04X}"
    print(f"    ΓΡΑΜΜΗ: {len(NODES)} κόμβοι x {len(NODES)} στήλες, από το #{DB_ROW:04X} "
          f"ως το #{DB_ROW + 64 * len(NODES) - 1:04X}")
    return None


# --------------------------------------------------------------------------
# ΕΡΓΑΣΙΑ
# --------------------------------------------------------------------------
def jobs(sym, patch=()):
    M_ = TP.M(sym, patch)
    rnd = random.Random(1551)
    roles = M_.m.read_ram(sym["JOB_ROLES"], 10)
    wins = {"θόλος από δομή": 0, "δομή από δομή": 0, "από θόλο": 0}
    for case in range(160):
        scatter(M_, rnd)
        tbl = []
        for j in range(MAX_JOB):
            kind = rnd.choice(list(range(10)) + [NO_JOB] * 3)
            node = rnd.choice([rnd.randrange(64), rnd.choice(NODES)])
            agent = rnd.choice([255, 255, 255, rnd.randrange(100)])
            tbl.append([kind, node, agent, rnd.randrange(4), 0])
        M_.m.write_ram(L["G_job_tbl"], bytes(sum(tbl, [])))
        mask = rnd.choice([0xFF, 1 << rnd.randrange(8)])
        for lbl in ("JBB_RB", "JBS_RB"):
            M_.m.poke(sym[lbl] + 1, mask)
        src = rnd.choice(NODES) if case % 4 else rnd.randrange(64)
        best, bp, bd = NO_JOB, 0, 255
        for j, (kind, node, agent, prio, _) in enumerate(tbl):
            if kind == NO_JOB or agent != 255 or not roles[kind] & mask:
                continue
            c = dist(M_, src, node)
            if prio < bp or (prio == bp and c >= bd):
                continue
            best, bp, bd = j, prio, c
        got = M_.call("JB_BEST", a=src)["a"]
        if got != best:
            return (f"σκηνή {case}: jb_best από τον {src} = {got}, ο κανόνας {best}"
                    + (f" (κόμβος {tbl[best][1]})" if best != NO_JOB else ""))
        if best != NO_JOB:
            t = tbl[best][1]
            wins["από θόλο" if src < 64 else "δομή από δομή" if t >= 64 else "θόλος από δομή"] += 1
    if not patch and min(wins.values()) < 10:
        return f"οι σκηνές δεν πιάνουν κάθε δρόμο: {wins}"
    print(f"    ΕΡΓΑΣΙΑ: 160 σκηνές, η εργασία του κανόνα — {wins}")
    return None


# --------------------------------------------------------------------------
# AIRLOCK
# --------------------------------------------------------------------------
def locks(sym, patch=()):
    M_ = TP.M(sym, patch)
    rnd = random.Random(1552)
    wins = {"από δομή": 0, "από θόλο": 0}
    for case in range(80):
        scatter(M_, rnd)
        rows_ = [[0, 0, rnd.randrange(5), 0, DS_ACTIVE, 255, 0, 0] for _ in range(TP.NS)]
        for s in rnd.sample(range(TP.NS), rnd.randrange(1, 8)):
            rows_[s][2] = K_AIRLOCK
            rows_[s][4] = rnd.choice([DS_ACTIVE, DS_ACTIVE, DS_BUILDING])
        M_.table(rows_)
        src = rnd.choice(NODES) if case % 3 else rnd.randrange(64)
        live = [s for s in range(TP.NS) if rows_[s][2] == K_AIRLOCK and rows_[s][4] == DS_ACTIVE
                and dist(M_, src, 64 + s) < 255]
        want = 64 + min(live, key=lambda s: (dist(M_, src, 64 + s), s)) if live else 255
        got = M_.call("SU_LOCK", de=src << 8)["a"]
        if got != want:
            return f"σκηνή {case}: su_lock από τον {src} = {got}, ο κανόνας {want}"
        if live:
            wins["από θόλο" if src < 64 else "από δομή"] += 1
    if not patch and min(wins.values()) < 10:
        return f"οι σκηνές δεν πιάνουν και τους δύο δρόμους: {wins}"
    print(f"    AIRLOCK: 80 σκηνές, το κοντινότερο έτοιμο — {wins}")
    return None


# --------------------------------------------------------------------------
# ΠΗΓΗ
# --------------------------------------------------------------------------
def sources(sym, patch=()):
    M_ = TP.M(sym, patch)
    rnd = random.Random(1553)
    ag = L["G_agent_fields"]
    job = L["G_job_tbl"]
    wins = {"σκάφος από δομή": 0, "αποθήκη από δομή": 0, "από θόλο": 0, "καμία": 0}
    for case in range(120):
        scatter(M_, rnd)
        ship = rnd.random() < 0.8
        rows_ = [[0, 0, rnd.randrange(5), 0, DS_ACTIVE, 255, 0, 0] for _ in range(TP.NS)]
        rows_[0][2] = K_SHIP if ship else 4
        M_.table(rows_)
        stores = rnd.sample(range(64), rnd.randrange(0, 5))
        M_.m.poke(L["G_room_n"] + R_STORAGE, len(stores))
        M_.m.write_ram(L["G_room_list"] + R_STORAGE * ROOM_MAX, bytes(stores) or b"\0")
        n = rnd.choice(NODES) if case % 3 else rnd.randrange(64)
        aid = rnd.randrange(64)
        M_.b6[ag + 256 + aid - 0x4000] = n                  # AG_PG + 1: ο κόμβος του
        site = 99
        M_.m.write_ram(job, bytes([7, site, aid, 3, 0]))
        c, best = 255, None
        if ship and dist(M_, 64, n) < c:
            c, best = dist(M_, 64, n), 64
        for t in stores:
            if dist(M_, t, n) < c:
                c, best = dist(M_, t, n), t
        M_.call("SP_TAKE", de=((ag >> 8) + 2) << 8 | aid, hl=job + 2)
        got = M_.m.peek(job + 1)
        dest = M_.b6[ag + 512 + aid - 0x4000]
        want = site if best is None else best
        if got != want or (best is not None and dest != best):
            return (f"σκηνή {case}: sp_take από τον {n} → J_NODE {got}, προορισμός {dest}· "
                    f"ο κανόνας {want} (σκάφος {ship}, αποθήκες {stores})")
        wins["καμία" if best is None else "από θόλο" if n < 64
             else "σκάφος από δομή" if best == 64 else "αποθήκη από δομή"] += 1
    if not patch and min(wins.values()) < 5:
        return f"οι σκηνές δεν πιάνουν κάθε δρόμο: {wins}"
    print(f"    ΠΗΓΗ: 120 σκηνές, η πηγή του κανόνα — {wins}")
    return None


# --------------------------------------------------------------------------
# ΤΡΥΠΕΣ
# --------------------------------------------------------------------------
def holes(sym, patch=None):
    """patch: δύο-τρία bytes του εγκαταστάτη στο snapshot, (μοτίβο, νέα)."""
    d = bytearray(open(TG.COLONY, "rb").read())
    if patch:
        at = 0x100 + sym["ZZ_OVI"]                       # ο εγκαταστάτης, στην εικόνα
        k = bytes(d[at:at + 80]).find(bytes(patch[0]))
        if k < 0:
            return None
        d[at + k:at + k + len(patch[1])] = bytes(patch[1])
    m = cpc.CPC()
    m.run_frames(60)
    assert m.quickload(bytes(d))
    names = ("dm", "save", "help", "r1")
    want = {n: OV.pieces(sym)[n][3] for n in names}
    m.run_frames(50)                        # το hw_clear πριν από το ov_install: ~5 frames
    first = {n: OV.read(m, sym, n) for n in names}
    if first != want:
        bad = [n for n in names if first[n] != want[n]]
        return f"μετά την εκκίνηση οι τρύπες {bad} δεν έχουν το build"
    # Η αποικία ξεκινά με rt_mark: όλη η δρομολόγηση, με τις δομές της στο μπλοκ.
    k = 0
    while k < 3000 and (k < 50 or m.peek(sym["RT_DIRTY"])):
        m.run_frames(10)
        k += 10
    if m.peek(sym["RT_DIRTY"]):
        return f"η δρομολόγηση δεν τελείωσε σε {k} frames"
    after = {n: OV.read(m, sym, n) for n in names}
    if after != want:
        bad = [n for n in names if after[n] != want[n]]
        return f"μετά από {k} frames δρομολόγησης οι τρύπες {bad} άλλαξαν"
    b1 = OV.bank(m, 1)
    hw = m.peek(sym["RT_N"])
    ns = [s for s in range(64, hw) if m.peek(L["G_rt_nodes"] + s)]   # δομές με ακμές
    blk = [b1[GR.zd_off(s, t)] for s in ns for t in ns]
    if not ns or all(v == blk[0] for v in blk):
        return f"το μπλοκ δεν γράφτηκε: {len(ns)} δομές με ακμές, τιμές {sorted(set(blk))[:6]}"
    print(f"    ΤΡΥΠΕΣ: {', '.join(f'{n} {len(want[n])}' for n in names)} bytes όπως στο "
          f"build, και μετά από {k} frames δρομολόγησης· {len(ns)} δομές στο μπλοκ")
    return None


def negatives(sym):
    m = cpc.CPC()
    m.run_frames(60)
    assert m.quickload(TG.SNA, start=False)
    f = lambda name, pat, span=80: codeat.find(m, sym[name], pat, span)
    jb = f("JBS_LP", [0x7B, 0xFE, 0x40, 0x30])           # ld a,e · cp 64 · jr nc
    sl = f("SU_LOCK", [0x7A, 0xFE, 0x40, 0x30], 8)       # ld a,d · cp 64 · jr nc
    sp = f("SP_TAKE", [0x7B, 0xFE, 0x40, 0x30], 60)
    br = f("BLK_ROW", [0xC6, 0xC0], 8)                   # add a,#C0
    assert None not in (jb, sl, sp, br), (jb, sl, sp, br)
    nop2 = lambda a: [(a + 3, 0), (a + 4, 0)]
    w = lambda a: [a & 255, a >> 8]
    return [
        ("το jb_best χωρίς το jr nc,jbs_bk", jobs, nop2(jb)),
        ("το su_lock χωρίς το jr nc,sul_st", locks, nop2(sl)),
        ("το sp_take χωρίς το jr nc,sps_bk", sources, nop2(sp)),
        ("το blk_row με τη γραμμή μία πιο κάτω", rows, [(br + 1, 0)]),
        ("το ov_install με ένα μισό της κατεδάφισης (χωρίς το call ovi_half)", holes,
         ([0xCD] + w(sym["OVI_HALF"]), [0, 0, 0])),
    ]


def main():
    sym, _ = TG.build()
    for fn, what in ((rows, "ΓΡΑΜΜΗ: κάθε δομή 64-111 βρίσκει τη γραμμή της στο μπλοκ"),
                     (jobs, "ΕΡΓΑΣΙΑ: το jb_best διαβάζει θόλο από τη γραμμή του, δομή από το μπλοκ"),
                     (locks, "AIRLOCK: το su_lock από δομή διαβάζει τη γραμμή της στο μπλοκ"),
                     (sources, "ΠΗΓΗ: το sp_take από δομή διαβάζει τη γραμμή του σκάφους στο μπλοκ")):
        err = fn(sym)
        check(err is None, err or what)
    err = holes(sym)
    check(err is None, err or "ΤΡΥΠΕΣ: οι τρεις περιοχές όπως στο build, και η δρομολόγηση δεν τις αγγίζει")
    for label, fn, patch in negatives(sym):
        why = fn(sym, patch)
        check(why is not None, f"ΑΡΝΗΤΙΚΟ: με {label} "
              + (f"αποτυγχάνει ({why[:100]})" if why else "ΠΕΡΝΑ"))
    print("\n" + ("ΟΛΑ ΚΑΛΑ" if not FAIL else f"ΑΠΟΤΥΧΙΑ — {len(FAIL)}"))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
