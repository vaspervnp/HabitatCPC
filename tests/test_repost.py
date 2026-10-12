#!/usr/bin/env python3
"""Τίποτα δεν περιμένει για πάντα έναν γεμάτο πίνακα εργασιών (βήμα 115,
DESIGN §6.7).

Ως το βήμα 114 οι εργασίες ενός εργοταξίου δημοσιεύονταν μία φορά, τη στιγμή
που χρειάζονταν, και με τον πίνακα γεμάτο δεν έμπαιναν ποτέ. Μετρημένο στο
main.sna του 114: ένα ηλιακό τοποθετημένο με τους 32 πιασμένους έμεινε
εργοτάξιο 30.000 frames αφού ο πίνακας άδειασε, χωρίς καμία εργασία, με τα 15
μέταλλα πληρωμένα.

  ΣΑΡΩΜΑ    Το sp_sweep (src/repost.asm) απέναντι στο sweep της αναφοράς
            (tools/econ.py), byte προς byte: ο πίνακας, το EC_NBUILD, το
            jb_lost, και θόλοι και δομές ανέγγιχτα.
            - ένας «ζωολογικός κήπος» με κάθε κλάδο: εργοτάξια θόλων με
              χρέη και μηχανές (που χρωστούν, έτοιμες), θόλοι σε λειτουργία με
              μηχανές σε κάθε στάδιο (7, 6, 5, 4, 36, 68, 100, 200, 0), δομές
              που χρωστούν #20, #05, #25, #00, ορυχείο με σωρό, κενός θόλος με
              σκουπίδια· εργασίες ήδη εκεί, και μία στο πρώτο σκέλος (J_NODE
              η πηγή, J_SITE το εργοτάξιο)·
            - 60 τυχαίες αποικίες με πίνακες από άδειους ως γεμάτους·
            - γεμάτος πίνακας με Operate για έξωση, και χωρίς.
  ΧΡΟΝΟΣ    Μια μεγάλη αποικία χωρίς τίποτα χαμένο (48 θόλοι με οκτώ μηχανές,
            24 δομές): το σάρωμα που κάνει κάθε φόρτωση, 16,6 ms (ταβάνι
            17.500 us) — ένα frame της θέσης 12, μία φορά. Και 30 εργοτάξια με
            τον πίνακα γεμάτο χωρίς έξωση: σταματά στο πρώτο που δεν χωρά, 9,9
            ms (ταβάνι 10.500), οι 64 άδειοι θόλοι τα περισσότερα· χωρίς το
            «σταματά» 74,6.
  ΕΞΩΣΗ     Στο παιχνίδι (main.sna): οι 32 θέσεις Operate αδιάθετες, μία με
            προτεραιότητα 2 οι άλλες 3. Ενα ηλιακό: στο FIRE η Supply του στη
            θέση εκείνης, οι άλλες 31 ίδιες, το jb_lost 0. Οταν φύγουν οι
            Operate, χτίζεται.
  ΧΑΜΕΝΗ    Οι 32 θέσεις Drill, που δεν δίνουν τη θέση τους. Στο FIRE τίποτα,
            και το jb_lost ≠ 0. Οταν φύγουν, ο επόμενος κύκλος ροής βάζει τη
            Supply (ως 1.100 frames: 64 περιστροφές των 16), το jb_lost
            γίνεται 0, και το ηλιακό χτίζεται.
  ΜΕΤΕΩΡΙΤΗΣ Ενα ορυχείο σε λειτουργία με σωρό 25 που χτυπά (mt_hit):
            εργοτάξιο, ακεραιότητα 0, σωρός 0, μία Build και καμία Supply· και
            το σάρωμα μετά δεν προσθέτει τίποτα.

Αρνητικά, με το snapshot πειραγμένο:
  - ΣΑΡΩΜΑ: χωρίς το «τις έτοιμες τις στήνει ο χτίστης» (res 2,e), χωρίς το
    sp_find, χωρίς τη Build της έτοιμης μηχανής (set 2,e), το μέταλλο από το
    bit 0 (cp #01), με τις μηχανές που δουλεύουν (jp m), με το jb_lost που δεν
    σβήνει στην αρχή·
  - ΧΡΟΝΟΣ: χωρίς το «σταματά στο πρώτο» (ret c)·
  - ΕΞΩΣΗ: ο γεμάτος πίνακας γυρίζει αμέσως, όπως ως το 114·
  - ΧΑΜΕΝΗ: ο κύκλος ροής χωρίς το call nz,sp_sweep·
  - ΜΕΤΕΩΡΙΤΗΣ: ο σωρός μένει (το σάρωμα τον διαβάζει για χρέος).
Το φόρτωμα σηκώνει το jb_lost (wheel_load): tests/test_save.py.
"""
import ctypes, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import test_supply as TS                                 # noqa: E402
import balance as B                                      # noqa: E402
import econ as EC                                        # noqa: E402
import codeat                                            # noqa: E402
import cpc                                               # noqa: E402
from test_outside import layout                          # noqa: E402

PROBE = 0x3E00
MAX_JOB, JOB_REC, NO_JOB = 32, 5, 255
J_BUILD, J_OPERATE, J_DRILL, J_SUPPLY = 0, 1, 3, 7
DOME_REC, STRUCT_REC = 24, 8
D_SIZE, D_STATE, D_POWER, D_OPS, D_MACH, D_HEALTH = 2, 4, 6, 7, 8, 16
ST_KIND, ST_STATE, ST_INTEG, ST_OPS, ST_OWED = 2, 4, 5, 6, 7
K_MINE = 8
EC_NBUILD = 91
CEIL_BIG = 17_500                       # us: η μεγάλη αποικία, τίποτα χαμένο (16.648)
CEIL_FULL = 10_500                      # us: 30 εργοτάξια, πίνακας γεμάτος (9.916)
CEIL_FIRST = 1_100                      # frames ως τη Supply μετά το άδειασμα
FAIL = []


def say(ok, msg):
    print(("OK " if ok else "ΛΑΘΟΣ ") + msg, flush=True)
    if not ok:
        FAIL.append(msg)


def call(m, addr, pre=(), step=20, limit=400_000):
    """di · ld sp · ld bc,#7FC6 · out (c),c · [pre] · call addr · jr $ — us, ή None."""
    code = ([0xF3, 0x31, 0x00, 0x01, 0x01, 0xC6, 0x7F, 0xED, 0x49] + list(pre)
            + [0xCD, addr & 255, addr >> 8, 0x18, 0xFE])
    m.write_ram(PROBE, bytes(code))
    m.set_pc(PROBE)
    end, t = PROBE + len(code) - 2, 0
    while not (end <= m.pc <= end + 2):
        m.run_us(step)
        t += step
        if t > limit:
            return None
    return t


class Box:
    """Ενα main.sna σταματημένο (start=False), για κλήσεις με probe."""

    def __init__(self, sym, L, patch=()):
        self.sym, self.L = sym, L
        self.m = cpc.CPC()
        self.m.run_frames(60)
        assert self.m.quickload(TG.SNA, start=False), "quickload απέτυχε"
        self.b6p = cpc._lib.cpcemu_ram_ptr(self.m._h, 6)
        for at, v in patch:
            codeat.poke(self.m, at, v)

    def put6(self, addr, data):
        ctypes.memmove(ctypes.addressof(self.b6p.contents) + addr - 0x4000, bytes(data), len(data))

    def get6(self, addr, n):
        return ctypes.string_at(ctypes.addressof(self.b6p.contents) + addr - 0x4000, n)

    def call(self, addr, pre=(), step=20, limit=400_000):
        return call(self.m, addr, pre, step, limit)

    def sweep(self, domes, structs, board, nbuild=3, step=20):
        """Το sp_sweep σε αυτή την αποικία: (πίνακας, nbuild, jb_lost, χρόνος)."""
        L, m, g = self.L, self.m, self.L["G_econ_state"]
        self.put6(L["G_dome_tbl"], domes)
        self.put6(L["G_struct_tbl"], structs)
        m.write_ram(L["G_job_tbl"], bytes(board))
        m.poke(g + EC_NBUILD, nbuild)
        m.poke(self.sym["JB_LOST"], 0x80)
        t = self.call(self.sym["SP_SWEEP"], step=step)
        if self.get6(L["G_dome_tbl"], len(domes)) != bytes(domes) \
                or self.get6(L["G_struct_tbl"], len(structs)) != bytes(structs):
            return None, None, None, "οι θόλοι ή οι δομές άλλαξαν"
        return (bytes(m.read_ram(L["G_job_tbl"], MAX_JOB * JOB_REC)),
                m.peek(g + EC_NBUILD), m.peek(self.sym["JB_LOST"]), t)


def ref(domes, structs, board, nbuild=3):
    e = EC.Econ()
    e.dome[:] = domes
    e.struct[:] = structs
    e.job[:] = board
    e.nbuild = nbuild
    e.lost = True
    EC.sweep(e)
    return bytes(e.job), e.nbuild, e.lost


def dome(size, state, p=0, o=0, health=(), garbage=0):
    r = bytearray([garbage] * DOME_REC) if garbage else bytearray(DOME_REC)
    r[D_SIZE], r[D_STATE], r[D_POWER], r[D_OPS] = size, state, p, o
    for s in range(8):
        r[D_MACH + s] = 255
    for s, h in enumerate(health):
        r[D_HEALTH + s] = h
        r[D_MACH + s] = 3
    return r


def struct(kind, state, owed=0, ops=0):
    r = bytearray(STRUCT_REC)
    r[0], r[1], r[ST_KIND], r[ST_STATE], r[ST_OPS], r[ST_OWED] = 10, 10, kind, state, ops, owed
    return r


def empty_board():
    return bytearray([NO_JOB, 0, 255, 0, 0] * MAX_JOB)


def zoo():
    domes = bytearray(64 * DOME_REC)
    for d, r in ((0, dome(1, 1, 2, 1, (7, 4, 0, 0))),          # χρωστά· μηχανή 7 και μια έτοιμη
                 (1, dome(0, 1, 0, 0, (6,))),                  # δεν χρωστά· μηχανή βιοπλ.
                 (2, dome(2, 1, 3, 0, (5, 0))),                # μέταλλο, και η μηχανή
                 (3, dome(2, 2, 9, 4, (200, 0, 7, 6, 5, 4, 36, 100))),
                 (4, dome(1, 2, 9, 2, (200, 200, 0, 0))),      # τίποτα
                 (5, dome(0, 2, 9, 1, (68,))),                 # μόνο Build
                 (6, dome(2, 0, garbage=7)),                   # κενός, με σκουπίδια
                 (7, dome(0, 1, 0, 4, (200,))),                # μόνο βιοπλαστικό
                 (9, dome(1, 1, 0, 0, (4, 4, 0, 0)))):         # Build, όχι για τις μηχανές
        domes[d * DOME_REC:(d + 1) * DOME_REC] = r
    structs = bytearray(32 * STRUCT_REC)
    for s, r in ((0, struct(11, 2)),                           # το σκάφος
                 (1, struct(0, 1, 0x20)), (2, struct(0, 1, 0x05)),
                 (3, struct(1, 1, 0x25)), (4, struct(2, 1, 0x00)),
                 (5, struct(K_MINE, 2, 0x19, 0x41)),           # ορυχείο με σωρό
                 (7, struct(0, 2, 0x00))):
        structs[s * STRUCT_REC:(s + 1) * STRUCT_REC] = r
    board = empty_board()
    for j, rec in ((2, [J_SUPPLY, 0, 255, 4, 0]),              # του θόλου 0, ήδη
                   (5, [J_BUILD, 68, 3, 5, 68]),               # της δομής 4, ανατεθειμένη
                   (6, [J_SUPPLY, 64, 2, 4, 65]),              # πρώτο σκέλος: στην πηγή
                   (11, [J_OPERATE, 4, 255, 3, 4])):
        board[j * JOB_REC:(j + 1) * JOB_REC] = bytes(rec)
    return domes, structs, board


def colony(rnd, free):
    domes = bytearray(64 * DOME_REC)
    for d in range(64):
        st = rnd.choice([0, 0, 0, 1, 2, 2])
        hs = [rnd.choice([0, 4, 5, 6, 7, 36, 68, 100, 200, 200, 200, rnd.randrange(256)])
              for _ in range(8)]
        r = dome(rnd.randrange(3), st, rnd.choice([0, 0, 1, 2, 5]), rnd.choice([0, 0, 1, 3]), hs,
                 garbage=rnd.randrange(256) if st == 0 else 0)
        r[D_STATE] = st
        domes[d * DOME_REC:(d + 1) * DOME_REC] = r
    structs = bytearray(32 * STRUCT_REC)
    for s in range(32):
        r = struct(rnd.randrange(12), rnd.choice([0, 0, 1, 2]),
                   rnd.choice([0, 0x10, 0x20, 0x05, 0x25, 0x01, rnd.randrange(256)]))
        structs[s * STRUCT_REC:(s + 1) * STRUCT_REC] = r
    board = empty_board()
    for j in range(MAX_JOB):
        if rnd.random() < free:
            continue
        if rnd.random() < 0.4:                                 # μια εργασία που ίσως ζητείται
            n = rnd.randrange(96)
            rec = [rnd.choice([J_SUPPLY, J_SUPPLY + 1, J_BUILD]), rnd.randrange(128),
                   rnd.choice([255, rnd.randrange(96)]), rnd.randrange(10), n]
        else:
            rec = [rnd.randrange(10), rnd.randrange(128), rnd.choice([255, rnd.randrange(96)]),
                   rnd.randrange(10), rnd.randrange(128)]
        board[j * JOB_REC:(j + 1) * JOB_REC] = bytes(rec)
    return domes, structs, board


def cases():
    rnd = random.Random(115)
    out = [("ζωολογικός κήπος",) + zoo()]
    for k in range(60):
        out.append((f"τυχαία {k}",) + colony(rnd, rnd.choice([0, 0.1, 0.3, 0.6, 0.9])))
    d, s, _ = zoo()
    full = bytearray([J_OPERATE, 40, 255, 3, 40] * MAX_JOB)
    full[7 * JOB_REC + 3] = 2
    out.append(("γεμάτος, με Operate", d, s, full))
    out.append(("γεμάτος, χωρίς έξωση", d, s, bytearray([J_DRILL, 95, 255, 4, 95] * MAX_JOB)))
    return out


def sweep_cases(sym, L, patch=(), quiet=False):
    """Η πρώτη διαφορά από την αναφορά, ή None."""
    box = Box(sym, L, patch)
    for name, d, s, b in cases():
        got_b, got_n, got_l, t = box.sweep(d, s, b)
        if t is None:
            return f"{name}: το sp_sweep δεν γύρισε"
        if isinstance(t, str):
            return f"{name}: {t}"
        want_b, want_n, want_l = ref(d, s, b)
        if got_b != want_b:
            k = next(i for i in range(len(want_b)) if got_b[i] != want_b[i])
            return (f"{name}: θέση {k // JOB_REC}: {list(got_b[k // JOB_REC * 5:][:5])}, "
                    f"η αναφορά {list(want_b[k // JOB_REC * 5:][:5])}")
        if got_n != want_n or (got_l != 0) != want_l:
            return f"{name}: EC_NBUILD {got_n} jb_lost {got_l}, η αναφορά {want_n} {want_l}"
        if name == "ζωολογικός κήπος" and not quiet:
            posted = [list(got_b[j * 5:][:5]) for j in range(MAX_JOB) if got_b[j * 5:][:5] != b[j * 5:][:5]]
            print(f"    ζωολογικός κήπος: {len(posted)} νέες σε {t} us — {posted}")
    return None


def timing(sym, L, patch=()):
    box = Box(sym, L, patch)
    domes = bytearray(64 * DOME_REC)
    for d in range(48):
        domes[d * DOME_REC:(d + 1) * DOME_REC] = dome(2, 2, 9, 4, (200,) * 8)
    structs = bytearray(32 * STRUCT_REC)
    for s in range(24):
        structs[s * STRUCT_REC:(s + 1) * STRUCT_REC] = struct(0, 2)
    board = empty_board()
    for j in range(20):
        board[j * JOB_REC:(j + 1) * JOB_REC] = bytes([J_OPERATE, j, 7, 3, j])
    _, _, _, big = box.sweep(domes, structs, board, step=1)
    domes = bytearray(64 * DOME_REC)
    structs = bytearray(32 * STRUCT_REC)
    for s in range(1, 31):
        structs[s * STRUCT_REC:(s + 1) * STRUCT_REC] = struct(0, 1, 0x21)
    full = bytearray([J_DRILL, 95, 255, 4, 95] * MAX_JOB)
    for s in range(1, 31):                       # οι Supply μετάλλου τους υπάρχουν
        full[s * JOB_REC:(s + 1) * JOB_REC] = bytes([J_SUPPLY, 64 + s, 255, 4, 64 + s])
    _, _, lost, stuck = box.sweep(domes, structs, full, step=1)
    return big, stuck, lost


# --- στο παιχνίδι -----------------------------------------------------------

def game(sym, g, fill, patch=()):
    """Ενα ηλιακό με τον πίνακα γεμάτο από fill. (στο FIRE, λίστα συμβάντων) ή
    μήνυμα λάθους."""
    w = TS.W(sym, g)
    m, jt, lost = w.m, w.L["G_job_tbl"], sym["JB_LOST"]
    for at, v in patch:
        codeat.poke(m, at, v)
    # Η ΘΕΣΗ 13 ΠΑΓΩΜΕΝΗ ως να φύγουν τα γεμίσματα: αλλιώς στα 30 frames του
    # FIRE κάποιος παίρνει μια Operate ή μια Drill για κόμβο που δεν υπάρχει.
    m.poke(sym["WH_ON"] + 13, 0)
    m.write_ram(jt, bytes(fill))
    m.poke(lost, 0)
    B.build(m, sym, 4, g + 6, at=TS.SOLAR_AT, fit=False)
    m.run_frames(2)
    at_fire = (bytes(m.read_ram(jt, 160)), m.peek(lost), w.struct(1))
    for j in range(MAX_JOB):                     # η αποικία προλαβαίνει: τα γεμίσματα φεύγουν
        if bytes(m.read_ram(jt + 5 * j, 5)) == bytes(fill[j * 5:][:5]):
            m.write_ram(jt + 5 * j, bytes([NO_JOB] * 5))
    m.poke(sym["WH_ON"] + 13, 1)
    t, first, built = 0, None, None
    while t < 9000:
        m.run_frames(10)
        t += 10
        if first is None and any(j[0] == J_SUPPLY and j[4] == 65 for j in w.jobs()):
            first = (t, m.peek(lost))
        if w.struct(1)[4] == 2:
            built = t
            break
    return at_fire, first, built


def main():
    sym, g = TG.build()
    L = layout()

    # --- ΣΑΡΩΜΑ ------------------------------------------------------------
    why = sweep_cases(sym, L)
    say(why is None, "ΣΑΡΩΜΑ: το sp_sweep = το sweep της αναφοράς σε 63 αποικίες (ο ζωολογικός "
        "κήπος, 60 τυχαίες, δύο γεμάτοι πίνακες) — πίνακας, EC_NBUILD, jb_lost, θόλοι και "
        "δομές ανέγγιχτα" + (f" — ΟΧΙ: {why}" if why else ""))

    box0 = Box(sym, L)

    def at(label, pat, span=200, k=0, start=None):
        a = codeat.find(box0.m, sym[label] if start is None else start, pat, span)
        assert a is not None, f"δεν βρέθηκε {pat} μετά το {label}"
        return a + k

    spf, lost, sk = sym["SP_FIND"], sym["JB_LOST"], sym["SRP_KIND"]
    jpm = at("SP_WANT", [0xDD, 0x7E, 0x08, 0xB7, 0x28], k=6)       # ld a,(ix+8) · or a · jr z · jp m
    assert codeat.read(box0.m, jpm, 1) == b"\xFA"
    negs = [("χωρίς το «τις στήνει ο χτίστης» (res 2,e)", [(at("SP_WANT", [0xCB, 0x93]), 0),
                                                           (at("SP_WANT", [0xCB, 0x93], k=1), 0)]),
            ("χωρίς το sp_find", [(at("SRP_KIND", [0xCD, spf & 255, spf >> 8, 0x28], k=3), 0),
                                  (at("SRP_KIND", [0xCD, spf & 255, spf >> 8, 0x28], k=4), 0)]),
            ("χωρίς τη Build της έτοιμης μηχανής (set 2,e)", [(at("SP_WANT", [0xCB, 0xD3]), 0),
                                                              (at("SP_WANT", [0xCB, 0xD3], k=1), 0)]),
            ("το μέταλλο από το bit 0 (cp #01)", [(at("SP_WANT", [0xFE, 0x10], k=1), 0x01)]),
            ("με τις μηχανές που δουλεύουν (χωρίς jp m)", [(jpm + i, 0) for i in range(3)]),
            ("το jb_lost που δεν σβήνει", [(at("SP_SWEEP", [0x32, lost & 255, lost >> 8], k=i), 0)
                                          for i in range(3)])]
    for label, patch in negs:
        why = sweep_cases(sym, L, patch, quiet=True)
        say(why is not None, f"ΑΡΝΗΤΙΚΟ ΣΑΡΩΜΑΤΟΣ: {label} — "
            + (f"διαφέρει ({why[:90]})" if why else "ΠΕΡΝΑ"))

    # --- ΧΡΟΝΟΣ ------------------------------------------------------------
    big, stuck, lost_v = timing(sym, L)
    say(big <= CEIL_BIG and stuck <= CEIL_FULL and lost_v,
        f"ΧΡΟΝΟΣ: μεγάλη αποικία χωρίς τίποτα χαμένο {big} us (ταβάνι {CEIL_BIG}), 30 εργοτάξια "
        f"με τον πίνακα γεμάτο {stuck} us (ταβάνι {CEIL_FULL}), και το jb_lost ξανά {lost_v}")
    rets, a = [], sym["SP_SWEEP"]
    for _ in range(3):                           # call srp_kind · ret c
        a = at("SP_SWEEP", [0xCD, sk & 255, sk >> 8, 0xD8], 60, k=3, start=a + 1)
        rets.append((a, 0))
    _, stuck2, _ = timing(sym, L, rets)
    say(stuck2 > CEIL_FULL, f"ΑΡΝΗΤΙΚΟ ΧΡΟΝΟΥ: χωρίς το «σταματά στο πρώτο» (ret c) τα 30 "
        f"εργοτάξια {stuck2} us, πάνω από το ταβάνι {CEIL_FULL}")

    # --- ΕΞΩΣΗ -------------------------------------------------------------
    fill = bytearray([J_OPERATE, 40, 255, 3, 40] * MAX_JOB)
    fill[9 * JOB_REC + 3] = 2
    (board, lv, rec), first, built = game(sym, g, fill)
    want = bytearray(fill)
    want[9 * JOB_REC:10 * JOB_REC] = bytes([J_SUPPLY, 65, 255, 4, 65])
    ok = board == bytes(want) and lv == 0 and rec[4] == 1 and built is not None
    say(ok, f"ΕΞΩΣΗ: στο FIRE η Supply του ηλιακού στη θέση 9 (της Operate με προτεραιότητα 2), "
        f"οι άλλες 31 ίδιες, jb_lost {lv}· χτίστηκε {built} frames αφού έφυγαν οι Operate"
        + ("" if ok else f" — ΟΧΙ: {[list(board[j * 5:][:5]) for j in range(32) if board[j * 5:][:5] != want[j * 5:][:5]]}"))
    full_at = at("JB_POST_BUILD", [0x35, 0x19, 0x10], 24, k=4)    # dec (hl) · add hl,de · djnz · push ix
    assert codeat.read(box0.m, full_at, 2) == b"\xDD\xE5"
    (board, lv, rec), first, built = game(sym, g, fill, [(full_at, 0xC9)])
    say(board == bytes(fill), f"ΑΡΝΗΤΙΚΟ ΕΞΩΣΗΣ: ο γεμάτος πίνακας γυρίζει αμέσως, όπως ως το 114 — "
        f"στο FIRE {'τίποτα' if board == bytes(fill) else 'ΚΑΤΙ ΜΠΗΚΕ'}, χτίστηκε: {built}")

    # --- ΧΑΜΕΝΗ ------------------------------------------------------------
    fill = bytearray([J_DRILL, 95, 255, 4, 95] * MAX_JOB)
    (board, lv, rec), first, built = game(sym, g, fill)
    ok = (board == bytes(fill) and lv != 0 and first is not None and first[0] <= CEIL_FIRST
          and first[1] == 0 and built is not None)
    say(ok, f"ΧΑΜΕΝΗ: στο FIRE τίποτα και jb_lost #{lv:02X}· η Supply {first[0] if first else None} "
        f"frames αφού άδειασε ο πίνακας (ταβάνι {CEIL_FIRST}), jb_lost τότε "
        f"{first[1] if first else None}· χτίστηκε στα {built}")
    gate = codeat.find(box0.m, sym["ECON_FLOW"], [0xC4, sym["SP_SWEEP"] & 255, sym["SP_SWEEP"] >> 8], 300)
    (board, lv, rec), first, built = game(sym, g, fill, [(gate + i, 0) for i in range(3)])
    say(first is None and built is None, f"ΑΡΝΗΤΙΚΟ ΧΑΜΕΝΗΣ: ο κύκλος ροής χωρίς το call nz,sp_sweep — "
        f"Supply: {first}, χτίστηκε: {built} (9.000 frames)")

    # --- ΜΕΤΕΩΡΙΤΗΣ ---------------------------------------------------------
    for label, patch in (("", ()), ("ΑΡΝΗΤΙΚΟ ", "keep")):
        w = TS.W(sym, g)                         # ένα παιχνίδι που τρέχει: το st_redraw θέλει οθόνη
        m = w.m
        if patch == "keep":
            a = codeat.find(m, sym["MTH_STRUCT"], [0x23, 0x23, 0x36, 0x00], 40)
            for i in range(4):
                codeat.poke(m, a + i, 0)
        mine = 5
        rec_at = L["G_struct_tbl"] + mine * STRUCT_REC
        w.put6(rec_at, struct(K_MINE, 2, 25, 0x41))
        m.write_ram(L["G_job_tbl"], bytes(empty_board()))
        # mt_hit: HL = η εγγραφή, A - D = ο κόμβος
        node = 64 + mine
        t = call(m, sym["MT_HIT"], pre=[0x21, rec_at & 255, rec_at >> 8, 0x3E, 96, 0x16, 96 - node])
        r = w.b6(rec_at, STRUCT_REC)
        jobs1 = [list(m.read_ram(L["G_job_tbl"] + 5 * j, 5)) for j in range(32)
                 if m.peek(L["G_job_tbl"] + 5 * j) != NO_JOB]
        m.poke(sym["JB_LOST"], 0x80)
        call(m, sym["SP_SWEEP"])
        jobs2 = [list(m.read_ram(L["G_job_tbl"] + 5 * j, 5)) for j in range(32)
                 if m.peek(L["G_job_tbl"] + 5 * j) != NO_JOB]
        ok = (t is not None and r[ST_STATE] == 1 and r[ST_INTEG] == 0 and r[ST_OWED] == 0
              and jobs1 == [[J_BUILD, node, 255, 5, node]] and jobs2 == jobs1)
        if label:
            say(not ok, f"ΑΡΝΗΤΙΚΟ ΜΕΤΕΩΡΙΤΗ: με τον σωρό να μένει — σωρός {r[ST_OWED]}, μετά το "
                f"σάρωμα {jobs2}")
        else:
            say(ok, f"ΜΕΤΕΩΡΙΤΗΣ: το ορυχείο με σωρό 25 χτυπά — κατάσταση {r[ST_STATE]}, "
                f"ακεραιότητα {r[ST_INTEG]}, σωρός {r[ST_OWED]}, εργασίες {jobs1}, μετά το σάρωμα {jobs2}")

    print("ΟΛΑ ΚΑΛΑ" if not FAIL else f"{len(FAIL)} ΑΠΟΤΥΧΙΕΣ")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
