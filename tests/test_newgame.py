#!/usr/bin/env python3
"""Το game_new του src/newgame.asm, στο main.sna, απέναντι στο §10.1.

Η κατάσταση που αφήνει, γραμμένη από την πρόζα και όχι από τον Z80:

  οικονομία  τα 86 πρώτα bytes μηδέν, εκτός από τα αποθέματα (νερό 60, φαΐ 40,
             μετάλλευμα 60, μέταλλο 75, βιοπλαστικό 45, ανταλλακτικά 4), το
             ρολόι (sol 12.000 frames, μέρα 7.200, μέρα 1), τη γεννήτρια
             (#ACE1), το ρεύμα και το οξυγόνο εντάξει, 4 ζωντανούς και ταβάνι 8·
             η μετεωρική βροχή (86-90) όπως ήταν
  εργασίες   το είδος κάθε θέσης 255 (NO_JOB), τα άλλα bytes όπως ήταν
  γράφος     0-1, 0-2, 2-64 (η πλατφόρμα, ακμή εξωτερικού χώρου), και οι δύο
             κατευθύνσεις· κανένας άλλος βαθμός
  τράπεζα 6  από τους πράκτορες ως το τέλος των διαδρόμων μηδέν, εκτός από:
             τρεις μικρούς θόλους (οξυγόνο, κατάλυμα, κυλικείο) στα (0,0),
             (16,0), (0,16), ενεργούς και χτισμένους, με μία μηχανή — τη
             γεννήτρια οξυγόνου του πρώτου, 200 ζωή· την πλατφόρμα στο
             (-16,16)· τους δύο διαδρόμους· τέσσερις αποίκους με γεμάτες
             ανάγκες, στις θέσεις του δακτυλίου που δίνει το corr_fill· και
             τρεις στήλες πρακτόρων στο 255 (θέση, ακμή, εργασία)
  κόσμος     θεμέλιο και κατοχή στα 4x4 των τεσσάρων, με το decor όπως ήταν,
             και μόνο κατοχή στα tiles των δύο διαδρόμων (tools/route.py και
             tiles_of)· τίποτε άλλο
  ρολόι      rt_dirty = 1, wh_slot = 0

Σε οκτώ αφετηρίες: η πρώτη είναι το παιχνίδι όπως τρέχει, οι άλλες γεμίζουν με
σκουπίδια ό,τι σκουπίζει ή γράφει το game_new και όλο το επίπεδο.

ΓΙΑΤΙ. Ως το βήμα 74 το game_new το έβλεπαν μόνο τα σενάρια που ξεκινούν από
αυτό. Από 36 σκόπιμα λάθη του βήματος 74, τα 18 πέρασαν από δεκατέσσερα τεστ
που ξεκινούν από το game_new — όλη η σφραγίδα θεμελίου κάτω από την αποικία
ανάμεσά τους — και ένα δεν αλλάζει τίποτα (βλ. DESIGN §10.1). Αυτό εδώ πιάνει
τα 35.

Και ο ΧΡΟΝΟΣ: όλο το game_new, μαζί με την πρώτη σχεδίαση του ui_init, όχι
πιο αργό από όσο μετρήθηκε στο βήμα 74. Με το newgame.asm του βήματος 73
αποτυγχάνει.

Αρνητικά, με το snapshot πειραγμένο: δύο στήλες πρακτόρων αντί για τρεις,
τρεις σειρές θεμελίου αντί για τέσσερις, ένα ζευγάρι οικονομίας λιγότερο, και
οι ανάγκες σε δύο σελίδες.
"""
import ctypes, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import cpc                                               # noqa: E402
import route                                             # noqa: E402
from test_route import tiles_of                          # noqa: E402
from test_corridor import Ends                           # noqa: E402

PROBE = 0x3E00
CEIL = 480535                                            # µs, βήμα 74· στο 73: 482229
# §10.1 και src/const.asm
STOCK = {0: 60, 1: 40, 2: 60, 3: 75, 4: 45, 6: 4}        # S_* -> απόθεμα
DOMES = [(0, 0, 4), (16, 0, 2), (0, 16, 3)]              # cx, cy, δωμάτιο
PAD = (-16, 16, 6)                                       # cx, cy, K_PAD
ROLES = [(0, 0), (0, 1), (1, 0), (2, 2)]                 # ρόλος, κόμβος
NO_MACH, DS_ACTIVE, NO_JOB = 255, 2, 255


def layout():
    L = {}
    for line in open(os.path.join(ROOT, "build", "layout.asm"), encoding="utf-8"):
        p = line.split()
        if len(p) >= 3 and p[1] == "equ" and p[2].startswith("#"):
            L[p[0]] = int(p[2][1:], 16)
    return L


def sb(v):
    return v - 256 if v > 127 else v


class Game:
    def __init__(self, sym, patch=()):
        self.sym = sym
        m = self.m = cpc.CPC()
        m.run_frames(60)
        assert m.quickload(TG.SNA, start=False), "quickload απέτυχε"
        m.run_frames(400)                                # ξεκίνησε και τρέχει
        for at, v in patch:
            m.poke(at, v)
        self.ptr = [cpc._lib.cpcemu_ram_ptr(m._h, n) for n in range(8)]
        self.keep = [self.bank(n) for n in range(8)]

    def bank(self, n, off=0, size=0x4000):
        return ctypes.string_at(ctypes.addressof(self.ptr[n].contents) + off, size)

    def put(self, n, off, data):
        ctypes.memmove(ctypes.addressof(self.ptr[n].contents) + off, bytes(data), len(data))

    def restore(self):
        for n in range(8):
            self.put(n, 0, self.keep[n])

    def run(self, step=20):
        s, m = self.sym, self.m
        code = [0xF3, 0x31, 0x00, 0x01, 0x01, 0xC0, 0x7F, 0xED, 0x49,
                0xCD, s["GAME_NEW"] & 255, s["GAME_NEW"] >> 8, 0x18, 0xFE]
        m.write_ram(PROBE, bytes(code))
        m.set_pc(PROBE)
        end, t = PROBE + len(code) - 2, 0
        while not (end <= m.pc <= end + 2):
            m.run_us(step)
            t += step
            assert t < 5_000_000, hex(m.pc)
        return t


def rule(L, before, fill):
    """Η αναμενόμενη τράπεζα 2 (οικονομία, εργασίες, γράφος), 6 (πίνακες) και 4."""
    b2, b4 = bytearray(before[2]), bytearray(before[4])
    ge, gj = L["G_econ_state"] - 0x8000, L["G_job_tbl"] - 0x8000
    b2[ge:ge + 86] = bytes(86)
    for s_, v in STOCK.items():
        b2[ge + 2 * s_] = v
    for off, v in ((64, 12000), (66, 7200), (54, 0xACE1)):
        b2[ge + off], b2[ge + off + 1] = v & 255, v >> 8
    for off, v in ((49, 1), (46, 1), (47, 1), (58, 4), (74, 8)):
        b2[ge + off] = v
    for j in range(32):
        b2[gj + 5 * j] = NO_JOB
    nodes, adj = L["G_rt_nodes"] - 0x8000, L["G_node_adj"] - 0x8000
    b2[nodes:nodes + 128] = bytes(128)
    for x, y in ((0, 1), (1, 0), (0, 2), (2, 0), (2, 64), (64, 2)):
        b2[adj + 8 * x + b2[nodes + x]] = y
        b2[nodes + x] += 1
    # τράπεζα 6
    ag, end = L["G_agent_fields"] - 0x4000, L["G_corr_tbl"] + 96 * 5 - 0x4000
    b6 = bytearray(before[6])
    b6[ag:end] = bytes(end - ag)
    for page in (1, 2, 3):                               # θέση, ακμή, εργασία
        o = ag + 256 * page + 128
        b6[o:o + 128] = b"\xff" * 128
    gd, gs, gc = L["G_dome_tbl"] - 0x4000, L["G_struct_tbl"] - 0x4000, L["G_corr_tbl"] - 0x4000
    for d, (cx, cy, room) in enumerate(DOMES):
        rec = [cx & 255, cy & 255, 0, room, DS_ACTIVE, 255, 0, 0] + [NO_MACH] * 8 + [0] * 8
        if d == 0:
            rec[8], rec[16] = 0, 200                     # γεννήτρια οξυγόνου, καινούργια
        b6[gd + 24 * d:gd + 24 * d + 24] = bytes(rec)
    b6[gs:gs + 6] = bytes([PAD[0] & 255, PAD[1], PAD[2], 0, DS_ACTIVE, 255])
    b6[gc:gc + 10] = bytes([0, 1, 2, 4, DS_ACTIVE, 0, 2, 4, 4, DS_ACTIVE])
    occ = L["G_node_occ"] - 0x4000
    for a, (role, node) in enumerate(ROLES):
        slot = next(s_ for s_ in fill if not b6[occ + node] >> s_ & 1)
        b6[occ + node] |= 1 << slot
        b6[ag + a], b6[ag + a + 128] = 3, role           # F_ALIVE + F_INDOORS
        b6[ag + 256 + a], b6[ag + 256 + a + 128] = node, slot
        b6[ag + 512 + a] = node                          # προορισμός
        for page in (4, 5, 6):
            b6[ag + 256 * page + a] = b6[ag + 256 * page + a + 128] = 255
    # ο κόσμος: θεμέλιο και κατοχή κάτω από τα τέσσερα, το decor μένει...
    for cx, cy in [(d[0], d[1]) for d in DOMES] + [PAD[:2]]:
        tx, ty = (cx >> 1) - 2, (cy >> 1) - 2
        for i in range(4):
            for j in range(4):
                k = (ty + j + 64) * 128 + tx + i + 64
                b4[k] = b4[k] & 0xC0 | 0x17
    # ...και ΜΟΝΟ κατοχή στους διαδρόμους (cr_stamp: όχι θεμέλιο, §9.4)
    for b in (1, 2):
        a_, z = (DOMES[0][0], DOMES[0][1], 0), (DOMES[b][0], DOMES[b][1], 0)
        side, runs = route.plan(*a_, *z)
        ends = (a_, z) if side == 0 else (z, a_)
        for x, y in tiles_of(Ends(*ends), 0, runs, 1):
            b4[(y + 64) * 128 + x + 64] |= 0x10
    return b2, b6, b4


def check(sym, patch=(), n=8, timing=False):
    """Η πρώτη διαφορά από τον κανόνα, ή None· και ο χρόνος της πρώτης."""
    G = Game(sym, patch)
    L = layout()
    fill = list(G.bank(2, L["G_corr_fill"] - 0x8000, 8))
    rnd = random.Random(74)
    t0 = None
    for case in range(n):
        G.restore()
        if case:
            G.put(6, 0x2C00, bytes(rnd.randrange(256) for _ in range(0x1400)))
            G.put(2, L["G_econ_state"] - 0x8000,
                  bytes(rnd.randrange(256) for _ in range(0xA500 - L["G_econ_state"])))
            G.put(4, 0, bytes(rnd.choice([0, 1, 7, 0x40, 0x88, 0xC5, 0x17, rnd.randrange(256)])
                              for _ in range(0x4000)))
        before = [G.bank(k) for k in range(8)]
        t = G.run(step=1 if timing and case == 0 else 20)
        if case == 0:
            t0 = t
        b2, b6, b4 = rule(L, before, fill)
        lo = L["G_econ_state"] - 0x8000
        # ως το τέλος των διαδρόμων: μετά είναι η κρυφή μνήμη φιγούρων, που την
        # ξαναχτίζει η πρώτη σχεδίαση του ui_init
        b6end = L["G_corr_tbl"] + 96 * 5 - 0x4000
        for name, k, want, a, z in (("η τράπεζα 2", 2, b2, lo, 0xA500 - 0x8000),
                                    ("η τράπεζα 6", 6, b6, 0x2C00, b6end),
                                    ("ο κόσμος", 4, b4, 0, 0x4000)):
            got = G.bank(k)
            if got[a:z] != bytes(want[a:z]):
                i = next(i for i in range(a, z) if got[i] != want[i])
                base = {2: 0x8000, 6: 0x4000, 4: 0x4000}[k]
                return (f"αφετηρία {case}: {name}, #{base + i:04X} = {got[i]}, ο κανόνας λέει "
                        f"{want[i]}"), t0
        m = G.m
        if (m.peek(sym["RT_DIRTY"]), m.peek(sym["WH_SLOT"])) != (1, 0):
            return f"αφετηρία {case}: rt_dirty {m.peek(sym['RT_DIRTY'])}, wh_slot " \
                   f"{m.peek(sym['WH_SLOT'])}", t0
    return None, t0


def main():
    sym, _ = TG.build()
    fails = 0
    why, t = check(sym, timing=True)
    if why:
        print(f"ΑΠΟΤΥΧΙΑ: {why}")
        fails += 1
    else:
        print("OK το game_new = το §10.1: οικονομία, εργασίες, γράφος, θόλοι, πλατφόρμα, "
              "διάδρομοι, άποικοι, θεμέλιο, σε 8 αφετηρίες")
    print(f"    game_new με το ui_init: {t} us")
    if t > CEIL:
        print(f"ΑΠΟΤΥΧΙΑ: πιο αργό από το βήμα 74: {t} > {CEIL}")
        fails += 1
    else:
        print("OK όχι πιο αργό από το βήμα 74")

    m = cpc.CPC()
    m.run_frames(60)
    assert m.quickload(TG.SNA, start=False)

    def find(pat, span=400):
        i = m.read_ram(sym["GAME_NEW"], span).find(bytes(pat))
        assert i >= 0, f"δεν βρέθηκε το {pat}"
        return sym["GAME_NEW"] + i

    econ_n = (sym["NG_ECON_END"] - sym["NG_ECON"]) // 2
    neg = [("δύο στήλες πρακτόρων", [(find([0x0E, 3, 0x06, 128]) + 1, 2)]),
           ("τρεις σειρές θεμελίου", [(find([0x0E, 4, 0xE5, 0x06, 4]) + 1, 3)]),
           ("ένα ζευγάρι οικονομίας λιγότερο", [(find([0x06, econ_n]) + 1, econ_n - 1)]),
           ("οι ανάγκες σε δύο σελίδες", [(find([0x06, 3, 0x36, 255]) + 1, 2)])]
    for label, patch in neg:
        why, _ = check(sym, patch, n=3)
        if why:
            print(f"OK ΑΡΝΗΤΙΚΟ: με {label} αποτυγχάνει ({why[:90]})")
        else:
            print(f"ΑΠΟΤΥΧΙΑ ΑΡΝΗΤΙΚΟΥ: με {label} περνά")
            fails += 1
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
