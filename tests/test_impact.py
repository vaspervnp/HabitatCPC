#!/usr/bin/env python3
"""Η βροχή μετεωριτών του src/meteor.asm, κλήση προς κλήση, στο main.sna (§6.10).

Το tests/test_sim.py συγκρίνει τον Z80 με την αναφορά (tools/econ.py) σε μία
αποικία που δουλεύει· το tests/test_meteor.py παίζει μία βροχή στο παιχνίδι.
Εδώ το mt_tick καλείται κατευθείαν, από 400 τυχαίες καταστάσεις: κτίρια
μαζεμένα γύρω από το κέντρο, κέντρα στις άκρες του κόσμου, άδειες εγγραφές
με κέντρο κοντά, εργοτάξια, θόλοι χωρίς μηχανές, ένας κόσμος με κάθε είδος
tile, γεμάτος πίνακας εργασιών, σπόρος που θα έβγαινε μηδέν. Μετά από κάθε
κλήση ΟΛΗ η μνήμη, σε όλες τις τράπεζες, πρέπει να είναι αυτή που λέει:

  η αναφορά       για τη βροχή, τα κτίρια και τις εργασίες (meteor_tick)
  ο κανόνας του   για τον κόσμο: ελεύθερο tile (κατοχή 0) με έδαφος, σκόνη,
  κρατήρα         βράχο ή θεμέλιο γίνεται κρατήρας, και το decor μένει
  η οθόνη         ο κρατήρας μπαίνει στη λίστα αλλαγών (DK_TILE, x, y)· αν η
                  λίστα είναι γεμάτη, σηκώνεται η σημαία
  και ακόμα       mt_boom = 1 σε κάθε κρούση, ec_fdiv = 1 όταν μια δομή ξαναγίνει
                  εργοτάξιο, eb_d/eb_s όταν σταματά μηχανή θόλου, και η τράπεζα 6
                  στο παράθυρο όταν γυρίζει

— και τίποτε άλλο: ούτε ένα byte εκτός από τη στοίβα.

ΓΙΑΤΙ. Στο βήμα 76 το meteor.asm ξαναγράφτηκε. Από 41 σκόπιμα λάθη, τα δύο
δεν αλλάζουν τίποτα με τα δεδομένα του παιχνιδιού (οι μάσκες των διαστάσεων
δομής). Από τα άλλα 39, τα 7 πέρασαν από τα test_sim, test_meteor και
test_loop: ένας σπόρος που μένει μηδέν, η δομή 95 που δεν γίνεται ποτέ κέντρο,
ένα κέντρο που κοιτά την ακεραιότητα, μόνο το x στο όριο του κόσμου, ο θόλος
63 που μετριέται για δομή, κρατήρας και σε διάδρομο, η τράπεζα 4 που μένει
μέσα. Αυτό εδώ πιάνει και τα 39.

Και ο ΧΡΟΝΟΣ, ανά είδος κλήσης, στο χειρότερο που συνάντησε: όχι πιο αργό από
όσο μετρήθηκε στο βήμα 76. Με το meteor.asm του βήματος 75 αποτυγχάνει.

Αρνητικά, με τον κώδικα πειραγμένο στη μνήμη: κρατήρας και πάνω σε διάδρομο,
κρούση έξω από τον κόσμο που δεν γυρίζει, θόλοι με πλευρά 2 + 2*μέγεθος, η
μηχανή από το λάθος byte, το «κοντινό» κέντρο στα 3 tiles.
"""
import copy, ctypes, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import cpc                                               # noqa: E402
import econ as EC                                        # noqa: E402

PROBE = 0x3E00
DK_TILE, DIRTY_N = 4, 32
# µs ανά κλήση, μαζί με τη σκαλωσιά του probe· βήμα 76, και στο 75
CEIL = {
    "ήσυχο": 41,        # καμία βροχή, καμία αρχή                         41
    "αρχή": 7041,       # ξεκινά βροχή (ή δεν βρίσκει κτίριο)           8451
    "έξω": 285,         # κρούση έξω από τον κόσμο                       299
    "κτίριο": 5270,     # κρούση σε κτίριο                              6440
    "έδαφος": 5170,     # κρούση στο έδαφος, με ή χωρίς κρατήρα         6389
}


def layout():
    L = {}
    for line in open(os.path.join(ROOT, "build", "layout.asm"), encoding="utf-8"):
        p = line.split()
        if len(p) >= 3 and p[1] == "equ" and p[2].startswith("#"):
            L[p[0]] = int(p[2][1:], 16)
    return L


def s8(v):
    v &= 255
    return v - 256 if v > 127 else v


def hit_node(e, tx, ty):
    """Ο πρώτος ζωντανός κόμβος που το αποτύπωμά του έχει το tile (αναφορά)."""
    for n in range(EC.MAX_DOME + EC.MAX_STRUCT):
        rec, b = EC._node_rec(e, n)
        if rec[b + EC.D_STATE]:
            x0, y0, w, h = EC._footprint(e, n)
            if ((tx - x0) & 255) < w and ((ty - y0) & 255) < h:
                return n
    return None


class Rig:
    def __init__(self, sym, patch=()):
        self.sym, self.L = sym, layout()
        m = self.m = cpc.CPC()
        m.run_frames(60)
        assert m.quickload(TG.COLONY, start=False), "quickload απέτυχε"
        m.run_frames(400)
        for at, v in patch:
            m.poke(at, v)
        self.ptr = [cpc._lib.cpcemu_ram_ptr(m._h, n) for n in range(8)]
        self.keep = [self.bank(n) for n in range(8)]

    def bank(self, n):
        return ctypes.string_at(self.ptr[n], 0x4000)

    def put(self, n, off, data):
        ctypes.memmove(ctypes.addressof(self.ptr[n].contents) + off, bytes(data), len(data))

    def restore(self):
        for n in range(8):
            self.put(n, 0, self.keep[n])

    def call(self):
        m, ad = self.m, self.sym["MT_TICK"]
        code = [0xF3, 0x31, 0x00, 0x01, 0x01, 0xC6, 0x7F, 0xED, 0x49,   # τράπεζα 6 μέσα
                0xCD, ad & 255, ad >> 8, 0x18, 0xFE]
        m.write_ram(PROBE, bytes(code))
        m.set_pc(PROBE)
        end, t = PROBE + len(code) - 2, 0
        while not (end <= m.pc <= end + 2):
            m.run_us(1)
            t += 1
            if t > 100_000:
                return None
        return t


def scene(R, rnd, case):
    """Μια τυχαία κατάσταση στη μνήμη· γυρίζει (είδος, r1)."""
    L = R.L
    kind = case % 4                        # 0: καμία βροχή, 1-3: κρούση
    mcx, mcy = rnd.randrange(-64, 64), rnd.randrange(-64, 64)
    if rnd.random() < 0.15:
        mcx = rnd.choice([-64, -60, 58, 63])
    if rnd.random() < 0.15:
        mcy = rnd.choice([-64, -61, 59, 63])
    dims = EC.struct_dims()

    def place(rec, b, w, h):
        """Ένα κέντρο κοντά στο κέντρο της βροχής, με όλο το αποτύπωμα μέσα
        στον κόσμο, όπως το εγγυάται το χτίσιμο: ένας θόλος στο x = -61 με
        πλευρά 8 θα τυλιγόταν στο +63, και εκεί η αναφορά τον βρίσκει ενώ το
        φίλτρο «κοντά» του Z80 όχι."""
        for k, (c, n) in enumerate(((mcx, w), (mcy, h))):
            t0 = max(-64, min(64 - n, c + rnd.randrange(-11, 12) - n // 2))
            rec[b + k] = (2 * t0 + n + rnd.randrange(2)) & 255

    # Θόλοι και δομές με ΧΩΡΙΣΤΗ πυκνότητα: οι θόλοι κοιτάζονται πρώτοι, και
    # με πολλούς θόλους γύρω από το κέντρο μια δομή δεν χτυπιέται ποτέ.
    dd = rnd.choice([0.0, 0.0, 0.0, 0.05, 0.2, 0.6, 0.9])
    ds = rnd.choice([0.2, 0.6, 0.9, 0.9])
    dom = bytearray(rnd.randrange(256) for _ in range(EC.MAX_DOME * EC.DOME_REC))
    for d in range(EC.MAX_DOME):
        b = d * EC.DOME_REC
        dom[b + 2] = rnd.randrange(3)      # ένα μέγεθος 174 έχει πλευρά 352: ο
        side = 4 + 2 * dom[b + 2]          # Z80 τη μετρά σε 8 bits, η αναφορά όχι
        if rnd.random() < dd:
            place(dom, b, side, side)
            dom[b + 4] = rnd.choice([1, 2, 2, 2, 3])
        elif rnd.random() < 0.1:           # ζωντανή με περίεργη κατάσταση
            place(dom, b, side, side)
            dom[b + 4] = rnd.randrange(1, 256)
        else:
            dom[b + 4] = 0                 # άδεια — συχνά με κέντρο κοντά
            if rnd.random() < 0.3:
                place(dom, b, side, side)
    st = bytearray(rnd.randrange(256) for _ in range(EC.MAX_STRUCT * EC.STRUCT_REC))
    for s in range(EC.MAX_STRUCT):
        b = s * EC.STRUCT_REC
        kind = rnd.randrange(8)            # 0-3: μεγέθη 0-2 (και 3, χωρίς σχήμα)
        st[b + 2], st[b + 3] = kind, rnd.choice([0, 1, 2, 2, 3] if kind < 4 else [0])
        k = st[b + 2] * 8 + st[b + 3] * 2
        w, h = dims[k] // 4, dims[k + 1] // 16
        if rnd.random() < ds:
            place(st, b, w, h)
            st[b + 4] = rnd.choice([1, 2, 2, 3])
        else:
            st[b + 4] = 0
            if rnd.random() < 0.3:
                place(st, b, w, h)
    if rnd.random() < 0.3:
        # ΤΑ ΟΡΙΑ ΤΩΝ ΠΙΝΑΚΩΝ: ζωντανοί μόνο ένας ως τρεις από τους κόμβους στις
        # άκρες τους. Ο θόλος 63 που μετριέται για δομή, η δομή 95 που δεν
        # ελέγχεται ποτέ ως κέντρο, η πρώτη δομή: με όλο τον πίνακα γεμάτο,
        # κανένα από αυτά δεν φαινόταν (βήμα 76).
        for d in range(EC.MAX_DOME):
            dom[d * EC.DOME_REC + 4] = 0
        for n_ in range(EC.MAX_STRUCT):
            st[n_ * EC.STRUCT_REC + 4] = 0
        for n_ in rnd.sample([0, 62, 63, 64, 65, 94, 95], rnd.randrange(1, 4)):
            if n_ < EC.MAX_DOME:
                b = n_ * EC.DOME_REC
                side = 4 + 2 * dom[b + 2]
                place(dom, b, side, side)
                dom[b + 4] = rnd.choice([1, 2, 2, 2])
            else:
                b = (n_ - EC.MAX_DOME) * EC.STRUCT_REC
                st[b + 2], st[b + 3] = rnd.randrange(4), rnd.randrange(3)
                k = st[b + 2] * 8 + st[b + 3] * 2
                place(st, b, dims[k] // 4, dims[k + 1] // 16)
                st[b + 4] = rnd.choice([1, 2, 2])
    R.put(6, L["G_dome_tbl"] - 0x4000, dom)
    R.put(6, L["G_struct_tbl"] - 0x4000, st)
    R.put(4, 0, bytes(rnd.choice([0, 1, 2, 3, 4, 5, 6, 7, 0x10, 0x21, 0x08, 0x0A, 0x41,
                                  0x87, 0xC2, 0x36, 0x4F, rnd.randrange(256)])
                      for _ in range(0x4000)))
    ge = L["G_econ_state"] - 0x8000
    e = bytearray(R.bank(2)[ge:ge + EC.ECON_BYTES])
    e[86] = 0 if kind == 0 else rnd.randrange(1, 9)
    e[87], e[88] = mcx & 255, mcy & 255
    mr = rnd.randrange(1, 65536)
    e[89], e[90] = mr & 255, mr >> 8
    r1 = rnd.choice([0xFFF0 | rnd.randrange(16)] * 4 + [
                     rnd.randrange(65536), 0xFF00 | rnd.randrange(256),
                     (rnd.randrange(256) << 8) | 0xF0, 0xFFE0 | rnd.randrange(16),
                     0xFFF0 ^ (1 << rnd.randrange(16))])     # δίπλα στο όριο
    fr = r1 if kind == 0 and rnd.random() < 0.05 else rnd.randrange(65536)
    e[52], e[53] = fr & 255, fr >> 8
    R.put(2, ge, e)
    m, sym = R.m, R.sym
    m.poke(sym["EV_R1"], r1 & 255)
    m.poke(sym["EV_R1"] + 1, r1 >> 8)
    jobs = bytearray(rnd.randrange(256) for _ in range(EC.MAX_JOB * EC.JOB_REC))
    free = rnd.choice([0, 0.05, 0.5])
    for j in range(EC.MAX_JOB):
        jobs[j * EC.JOB_REC] = 255 if rnd.random() < free else rnd.randrange(5)
    R.put(2, L["G_job_tbl"] - 0x8000, jobs)
    m.poke(sym["DIRTY_NUM"], rnd.choice([0, 3, 31, 32]))
    m.poke(sym["DIRTY_HEAD"], rnd.randrange(DIRTY_N))
    for v in ("EB_D", "EB_S", "EC_FDIV", "MT_BOOM", "DIRTY_OVER"):
        m.poke(sym[v], rnd.randrange(256) if v != "MT_BOOM" else 0)
    return kind, r1


def expect(R, before, r1):
    """Η μνήμη μετά, από την αναφορά και τον κανόνα· και το είδος της κλήσης."""
    L, sym = R.L, R.sym
    b = [bytearray(x) for x in before]
    ge, gj = L["G_econ_state"] - 0x8000, L["G_job_tbl"] - 0x8000
    gd, gs = L["G_dome_tbl"] - 0x4000, L["G_struct_tbl"] - 0x4000
    e = EC.Econ()
    e.dome = bytearray(b[6][gd:gd + EC.MAX_DOME * EC.DOME_REC])
    e.struct = bytearray(b[6][gs:gs + EC.MAX_STRUCT * EC.STRUCT_REC])
    e.job = bytearray(b[2][gj:gj + EC.MAX_JOB * EC.JOB_REC])
    raw = b[2][ge:ge + EC.ECON_BYTES]
    e.meteor, e.mcx, e.mcy = raw[86], s8(raw[87]), s8(raw[88])
    e.mrnd = raw[89] | (raw[90] << 8)
    e.nbuild = raw[91]                       # EC_NBUILD (βήμα 88)
    e.frame = raw[52] | (raw[53] << 8)
    e.flow_div = 255
    impact = e.meteor > 0
    if impact:
        f = copy.copy(e)
        byte = EC._mbyte(f)
        tx, ty = s8(e.mcx + (byte & 15) - 8), s8(e.mcy + (byte >> 4) - 8)
        inside = -64 <= tx < 64 and -64 <= ty < 64
        node = hit_node(e, tx, ty) if inside else None
    started = not impact and (r1 >> 4) == 0xFFF
    EC.meteor_tick(e, r1)
    b[6][gd:gd + len(e.dome)] = e.dome
    b[6][gs:gs + len(e.struct)] = e.struct
    b[2][gj:gj + len(e.job)] = e.job
    b[2][ge + 86] = e.meteor
    b[2][ge + 87], b[2][ge + 88] = e.mcx & 255, e.mcy & 255
    b[2][ge + 89], b[2][ge + 90] = e.mrnd & 255, e.mrnd >> 8
    b[2][ge + 91] = e.nbuild & 255

    def poke(name, v):
        a = sym[name]
        b[a >> 14 if a < 0x4000 else 2][a & 0x3FFF] = v

    if e.flow_div == 1:
        poke("EC_FDIV", 1)
    if not impact:
        return b, "αρχή" if started else "ήσυχο"
    poke("MT_BOOM", 1)
    if not inside:
        return b, "έξω"
    if node is not None:
        if node < EC.MAX_DOME and e.dome[node * EC.DOME_REC + EC.D_STATE] == EC.DS_ACTIVE:
            poke("EB_D", node)
            poke("EB_S", e.mrnd >> 8)
        return b, "κτίριο"
    at = (ty + 64) * 128 + tx + 64
    t = b[4][at]
    if (t & 0x37) < 3 or (t & 0x37) == 7:
        b[4][at] = (t & 0xC0) | 6
        num = b[0][sym["DIRTY_NUM"]]
        if num < DIRTY_N:
            slot = (b[0][sym["DIRTY_HEAD"]] + num) % DIRTY_N
            r = sym["DIRTY_RING"] + 3 * slot
            b[0][r:r + 3] = bytes([DK_TILE, tx & 255, ty & 255])
            poke("DIRTY_NUM", num + 1)
        else:
            poke("DIRTY_OVER", 1)
    return b, "έδαφος"


def run(sym, patch=(), n=400, times=None):
    R = Rig(sym, patch)
    rnd = random.Random(76)
    for case in range(n):
        R.restore()
        _, r1 = scene(R, rnd, case)
        before = [R.bank(k) for k in range(8)]
        want, what = expect(R, before, r1)
        t = R.call()
        if t is None:
            return f"περίπτωση {case}: το mt_tick δεν γύρισε (PC=#{R.m.pc:04X})"
        if times is not None:
            times[what] = max(times.get(what, 0), t)
        # «Απαιτεί τράπεζα 6»: και την αφήνει μέσα — ο τροχός συνεχίζει με αυτήν
        view = bytes(R.m.peek(0x4000 + 257 * k) for k in range(63))
        if view != bytes(R.bank(6)[257 * k] for k in range(63)):
            return f"περίπτωση {case} ({what}): το mt_tick δεν αφήνει την τράπεζα 6 μέσα"
        for k in range(8):
            got = R.bank(k)
            if got == bytes(want[k]):
                continue
            for off in range(0x4000):
                if got[off] != want[k][off]:
                    if k == 0 and (0x00A0 <= off < 0x0100 or 0x3E00 <= off < 0x3F00):
                        continue
                    a = off + (0x8000 if k == 2 else 0x4000 if k in (4, 6) else 0)
                    return (f"περίπτωση {case} ({what}): τράπεζα {k} #{a:04X} = "
                            f"{got[off]}, ο κανόνας λέει {want[k][off]} "
                            f"(πριν {before[k][off]})")
    return None


def main():
    sym, _ = TG.build()
    fails = 0
    times = {}
    why = run(sym, times=times)
    if why:
        print(f"ΑΠΟΤΥΧΙΑ: {why}")
        fails += 1
    else:
        print("OK 400 κλήσεις του mt_tick = η αναφορά, ο κανόνας του κρατήρα και η "
              "λίστα αλλαγών — και τίποτε άλλο σε καμία τράπεζα")
    for k, c in CEIL.items():
        t = times.get(k, 0)
        if t > c:
            print(f"ΑΠΟΤΥΧΙΑ: {k} {t} us > {c} (βήμα 76)")
            fails += 1
        else:
            print(f"OK {k:7s} {t:5d} us <= {c}")

    m = cpc.CPC()
    m.run_frames(60)
    assert m.quickload(TG.COLONY, start=False)

    def find(at, pat, span=400):
        i = m.read_ram(sym[at], span).find(bytes(pat))
        assert i >= 0, f"δεν βρέθηκε το {pat}"
        return sym[at] + i

    mr1 = sym["EC_MRND"] + 1 if "EC_MRND" in sym else layout()["G_econ_state"] + 90
    neg = [("κρατήρα και πάνω σε διάδρομο", [(find("MT_TICK", [0xE6, 0x37]) + 1, 0x07)]),
           ("κρούση έξω από τον κόσμο που δεν γυρίζει",
            [(find("MT_TICK", [0xB5, 0xF8]) + 1, 0x00)]),
           ("θόλους με πλευρά 2 + 2*μέγεθος", [(find("MSC_NEAR", [0x87, 0xC6, 0x04]) + 2, 2)]),
           ("τη μηχανή από το λάθος byte",
            [(find("MT_TICK", [0x3A, mr1 & 255, mr1 >> 8]) + 1, (mr1 - 1) & 255)]),
           # βήμα 87: το B είναι ήδη x - 4, οπότε ένα παράθυρο 0..7 αντί για
           # 0..8 χάνει τα κέντρα 4 tiles δεξιά
           ("το «κοντινό» κέντρο στα 3 tiles από τη μία μεριά",
            [(find("MSC_LP", [0x90, 0xFE, 0x09]) + 2, 8)]),
           # βήμα 87: cp K_SHIP στο mth_struct γίνεται cp 255 — το σκάφος ξανά
           # εργοτάξιο. Οι τυχαίες σκηνές έχουν σκάφος σε 1 στις 8 δομές.
           ("το σκάφος σαν κτίριο", [(find("MTH_STRUCT", [0xFE, 7]) + 1, 255)])]
    for label, patch in neg:
        why = run(sym, patch, n=400 if "σκάφος" in label else 120)
        if why:
            print(f"OK ΑΡΝΗΤΙΚΟ: με {label} αποτυγχάνει ({why[:90]})")
        else:
            print(f"ΑΠΟΤΥΧΙΑ ΑΡΝΗΤΙΚΟΥ: με {label} περνά")
            fails += 1
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
