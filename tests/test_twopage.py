#!/usr/bin/env python3
"""Ο πίνακας των δομών σε δύο σελίδες (βήμα 154, DESIGN §4.2).

Η πρόζα:

  ΠΙΝΑΚΑΣ    384 bytes, 48 εγγραφές των 8, αμέσως μετά τους θόλους: οι 16
             πρώτες στο πάνω μισό μιας ζυγής σελίδας, οι 32 άλλες στην
             επόμενη. Κάθε σελίδα τελειώνει σε όριο εγγραφής.
  ΕΓΓΡΑΦΗ    Από τον κόμβο 64 + δομή (ή τη δομή): add a,a / add a,a / add
             a,STB_C + πεδίο/2 / ld l,a / ld h,STB_H / add hl,hl — και για τις
             48 (το παιχνίδι είχε 32 ως το βήμα 155). Εδώ το mt_rec, το
             op_ptr, το osa_key, το en_in, το fw_xy, το cr_read, το sp_want
             και το alw_node, για κάθε κόμβο 64-111.
  ΚΟΜΒΟΣ     Από τον δείκτη της εγγραφής (st_post): ld a,ixh / rra / ld a,ixl
             / rra x 3 / add a,48 — 32 x (σελίδα & 1) + L / 8.
  AIRLOCK    Το su_lock περπατά και τις δύο σελίδες: το κοντινότερο έτοιμο
             airlock στο DIST, όπου κι αν είναι — στις 16, στις 16-31, στις
             32-47 — και ισοπαλία η πρώτη δομή.

Οι εγγραφές 32-47 τις γράφει η δοκιμή· ως το βήμα 155 το παιχνίδι δεν είχε
τόσες, από το 156 τις έχει, και τις γεμίζει ο παίκτης στο tests/test_fortyeight.py.
Τα DIST των κόμβων 96-111 είναι από το βήμα 155 στήλες των γραμμών των θόλων
(ως τότε τρύπες, πάνω στον κώδικα των overlays), που από το 156 τις γράφει η
δρομολόγηση· εδώ τα γράφει η δοκιμή. Το su_lock από δομή, στο μπλοκ, το ρωτά
το test_dblock.

Αρνητικά, με τον κώδικα πειραγμένο: το mt_rec χωρίς το add hl,hl· το su_lock
χωρίς τη δεύτερη σελίδα (jr c,sul_lp -> nop)· ο κόμβος του st_post πάντα από
την πρώτη σελίδα (rra -> or a)· το osa_key χωρίς το inc l (διαβάζει το cx)· το
fw_xy με STB_C 0.
"""
import os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import codeat                                            # noqa: E402
import cpc                                               # noqa: E402

FAIL = []
PROBE, OUT = 0x3E80, 0x3F00
NS = 48                                                  # ο πίνακας, όχι το MAX_STRUCT
K_AIRLOCK, DS_BUILDING, DS_ACTIVE = 5, 1, 2
ST_OPS = 6


def check(ok, msg):
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ ") + msg)
    if not ok:
        FAIL.append(msg)


def layout():
    L = {}
    for line in open(os.path.join(ROOT, "build", "layout.asm"), encoding="utf-8"):
        p = line.split()
        if len(p) >= 3 and p[1] == "equ" and p[2].startswith("#"):
            L[p[0]] = int(p[2][1:], 16)
    return L


L = layout()
BASE = L["G_struct_tbl"]


def rec(s):
    return BASE + 8 * s


class M:
    """Το main.sna, σταματημένο, με έναν πίνακα δομών που γράφει η δοκιμή."""

    def __init__(self, sym, patch=()):
        self.sym = sym
        m = self.m = cpc.CPC()
        m.run_frames(60)
        assert m.quickload(TG.SNA, start=False)
        for at, v in patch:
            codeat.poke(m, at, v)
        self.b6 = cpc._lib.cpcemu_ram_ptr(m._h, 6)
        self.b1 = cpc._lib.cpcemu_ram_ptr(m._h, 1)
        self.dims = m.read_ram(L["G_struct_dims"], 64)

    def table(self, rows):
        """rows: 48 εγγραφές των 8 bytes."""
        for s, r in enumerate(rows):
            for k, v in enumerate(r):
                self.b6[rec(s) - 0x4000 + k] = v

    def call(self, name, a=0, bc=0, de=0, hl=0, ix=0, bank=0xC6):
        """call name, με τους καταχωρητές, την τράπεζα στο παράθυρο και di: (A, F,
        BC, DE, HL, IX) μετά."""
        sym, m = self.sym, self.m
        w = lambda v: [v & 255, (v >> 8) & 255]
        o = lambda k: w(OUT + k)
        code = ([0xF3, 0x31, 0x00, 0x01, 0x01, bank, 0x7F, 0xED, 0x49,
                 0xDD, 0x21] + w(ix) + [0x21] + w(hl) + [0x11] + w(de) + [0x01] + w(bc)
                + [0x3E, a, 0xCD] + w(sym[name])
                + [0x22] + o(0) + [0xED, 0x53] + o(2) + [0xED, 0x43] + o(4)
                + [0xDD, 0x22] + o(6) + [0xF5, 0xE1, 0x22] + o(8) + [0x18, 0xFE])
        m.write_ram(PROBE, bytes(code))
        m.set_pc(PROBE)
        end, t = PROBE + len(code) - 2, 0
        while not (end <= m.pc <= end + 2) and t < 50_000:
            m.run_us(20)
            t += 20
        if t >= 50_000:
            raise AssertionError(f"το {name} δεν γύρισε")
        r = m.read_ram(OUT, 10)
        g = lambda k: r[k] | r[k + 1] << 8
        return dict(a=r[9], f=r[8], bc=g(4), de=g(2), hl=g(0), ix=g(6))


def rows_random(rnd):
    """48 εγγραφές: cx, cy διάφορα, είδος 0-7 με το μόνο του μέγεθος, κατάσταση,
    ακεραιότητα, τα δύο τελευταία."""
    out = []
    for s in range(NS):
        kind = rnd.randrange(8)
        size = 2 if kind < 4 else 0
        state = rnd.choice([0, DS_BUILDING, DS_ACTIVE, DS_ACTIVE])
        owed = rnd.choice([0, 0x10, 0x03, 0x21])
        out.append([(s * 5 + 7) & 255, (200 - s * 3) & 255, kind, size, state,
                    255, rnd.randrange(256), owed])
    return out


def readers(sym, patch=()):
    """Κάθε αναγνώστης για κάθε κόμβο 64-111: η πρώτη διαφορά, ή None."""
    M_ = M(sym, patch)
    rnd = random.Random(154)
    rows = rows_random(rnd)
    M_.table(rows)
    for s in range(NS):
        n = 64 + s
        r = rows[s]
        got = M_.call("MT_REC", a=n)["hl"]
        if got != rec(s):
            return f"mt_rec({n}) = #{got:04X}, όχι #{rec(s):04X}"
        got = M_.call("OP_PTR", a=n)["hl"]
        if got != rec(s) + ST_OPS:
            return f"op_ptr({n}) = #{got:04X}, όχι #{rec(s) + ST_OPS:04X}"
        got = M_.call("OSA_KEY", a=s)["a"]
        if got != (r[1] + 128) & 255:
            return f"osa_key({s}) = {got}, όχι {(r[1] + 128) & 255}"
        cy = M_.call("EN_IN", a=n)["f"] & 1
        want = int(r[2] == K_AIRLOCK and r[4] == DS_ACTIVE)
        if cy != want:
            return f"en_in({n}): CY {cy}, όχι {want} (είδος {r[2]}, κατάσταση {r[4]})"
        q = M_.call("FW_XY", a=n)
        h = M_.dims[(r[2] * 4 + r[3]) * 2 + 1] >> 4
        d, e, b = q["de"] >> 8, q["de"] & 255, q["bc"] >> 8
        if (d, e, b) != (r[0], (r[1] + h) & 255, h):
            return f"fw_xy({n}) = D {d}, E {e}, B {b}, όχι {r[0]}, {(r[1] + h) & 255}, {h}"
        q = M_.call("CR_READ", a=n, de=OUT + 16)
        want_ok = r[2] == K_AIRLOCK and r[4] != 0
        if (not q["f"] & 1) != want_ok or (want_ok and (
                q["de"] != OUT + 19 or M_.m.read_ram(OUT + 16, 3) != bytes([r[0], r[1], 255]))):
            return f"cr_read({n}): {q}, εγγραφή {r}"
        e = M_.call("SP_WANT", a=n)["de"] & 255
        if r[4] != DS_BUILDING:
            want = 0
        elif r[7] == 0:
            want = 4
        else:
            want = (1 if r[7] >= 0x10 else 0) | (2 if r[7] & 15 else 0)
        if e != want:
            return f"sp_want({n}) = E {e}, όχι {want} (κατάσταση {r[4]}, χρωστά #{r[7]:02X})"
        q = M_.call("ALW_NODE", a=n)
        if (q["a"], q["hl"]) != (2, sym["T_SOLAR"] + 10 * r[2]):
            return f"alw_node({n}) = A {q['a']}, HL #{q['hl']:04X}"
        q = M_.call("ST_POST", a=4, bc=0x80, ix=rec(s))
        jd = M_.m.peek(sym["JB_D"])
        if jd != n:
            return f"st_post με IX #{rec(s):04X}: ο κόμβος {jd}, όχι {n}"
    print(f"    ΕΓΓΡΑΦΗ: οκτώ αναγνώστες σε {NS} κόμβους, και ο κόμβος του st_post")
    return None


def lock(sym, patch=()):
    """su_lock σε σκηνές με airlocks και στις τρεις ζώνες: η πρώτη διαφορά."""
    M_ = M(sym, patch)
    rnd = random.Random(1540)
    src = 5                                              # ένας θόλος
    row = src * 128                                      # DIST[src], τράπεζα 1
    n_ok = 0
    zones = {"0-15": 0, "16-31": 0, "32-47": 0}
    for case in range(60):
        rows = [[0, 0, rnd.randrange(5), 0, DS_ACTIVE, 255, 0, 0] for _ in range(NS)]
        locks = rnd.sample(range(NS), rnd.randrange(1, 6))
        for s in locks:
            rows[s][2] = K_AIRLOCK
            rows[s][4] = rnd.choice([DS_ACTIVE, DS_ACTIVE, DS_BUILDING])
        M_.table(rows)
        dist = {}
        for s in range(NS):
            v = rnd.choice([3, 5, 9, 9, 20, 255])
            dist[s] = v
            M_.b1[row + 64 + s] = v
        live = [s for s in locks if rows[s][4] == DS_ACTIVE and dist[s] < 255]
        want = 64 + min(live, key=lambda s: (dist[s], s)) if live else 255
        got = M_.call("SU_LOCK", de=src << 8)["a"]
        if got != want:
            return f"σκηνή {case}: su_lock = {got}, ο κανόνας {want} (airlocks {sorted(locks)})"
        if live:
            z = want - 64
            zones["0-15" if z < 16 else "16-31" if z < 32 else "32-47"] += 1
        n_ok += 1
    if not patch and min(zones.values()) < 5:
        return f"οι σκηνές δεν πιάνουν κάθε ζώνη: {zones}"
    print(f"    AIRLOCK: {n_ok} σκηνές, το κοντινότερο στις δομές {zones}")
    return None


def place():
    """Ο πίνακας εκεί που τον θέλει η διευθυνσιοδότηση."""
    if not (BASE & 7 == 0 and BASE & 255 == 128 and (BASE + 8 * NS) & 255 == 0
            and (BASE >> 8) & 1 == 0 and ((BASE >> 1) & 255) + 4 * 47 + 3 <= 255):
        return f"ο πίνακας στο #{BASE:04X}"
    if BASE != L["G_dome_tbl"] + 64 * 24:
        return f"ο πίνακας στο #{BASE:04X}, όχι μετά τους θόλους (#{L['G_dome_tbl']:04X})"
    print(f"    ΠΙΝΑΚΑΣ: #{BASE:04X}-#{BASE + 8 * NS - 1:04X}, 16 εγγραφές στη σελίδα "
          f"#{BASE >> 8:02X} και 32 στην #{(BASE >> 8) + 1:02X}")
    return None


def negatives(sym):
    m = cpc.CPC()
    m.run_frames(60)
    assert m.quickload(TG.SNA, start=False)
    f = lambda name, pat, span=40: codeat.find(m, sym[name], pat, span)
    mt = f("MT_REC", [0x29, 0xC9])                       # add hl,hl · ret
    sl = f("SU_LOCK", [0xFE, (BASE + 8 * NS) >> 8, 0x38], 80)   # cp · jr c
    sp = f("ST_POST", [0xDD, 0x7C, 0x1F])                # ld a,ixh · rra
    ok = f("OSA_KEY", [0x2C, 0x7E])                      # inc l · ld a,(hl)
    fw = f("FW_XY", [0xC6, (BASE >> 1) & 255], 40)       # add a,STB_C
    assert min(x if x is not None else -1 for x in (mt, sl, sp, ok, fw)) >= 0, \
        (mt, sl, sp, ok, fw)
    return [
        ("το mt_rec χωρίς το add hl,hl", readers, [(mt, 0)]),
        ("το su_lock χωρίς τη δεύτερη σελίδα", lock, [(sl + 2, 0), (sl + 3, 0)]),
        ("τον κόμβο του st_post πάντα από την πρώτη σελίδα", readers, [(sp + 2, 0xB7)]),
        ("το osa_key χωρίς το inc l", readers, [(ok, 0)]),
        ("το fw_xy με STB_C 0", readers, [(fw + 1, 0)]),
    ]


def main():
    sym, _ = TG.build()
    err = place()
    check(err is None, err or "ΠΙΝΑΚΑΣ: 384 bytes μετά τους θόλους, δύο σελίδες σε όριο εγγραφής")
    err = readers(sym)
    check(err is None, err or "ΕΓΓΡΑΦΗ: κάθε αναγνώστης βρίσκει τις 48 εγγραφές")
    err = lock(sym)
    check(err is None, err or "AIRLOCK: το su_lock περπατά και τις δύο σελίδες")
    for label, fn, patch in negatives(sym):
        why = fn(sym, patch)
        check(why is not None, f"ΑΡΝΗΤΙΚΟ: με {label} "
              + (f"αποτυγχάνει ({why[:90]})" if why else "ΠΕΡΝΑ"))
    print("\n" + ("ΟΛΑ ΚΑΛΑ" if not FAIL else f"ΑΠΟΤΥΧΙΑ — {len(FAIL)}"))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
