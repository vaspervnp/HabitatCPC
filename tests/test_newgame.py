#!/usr/bin/env python3
"""Το game_new του src/newgame.asm, στο main.sna, απέναντι στο §10.1.

Η κατάσταση που αφήνει, γραμμένη από την πρόζα και όχι από τον Z80. ΑΠΟ ΤΟ
ΒΗΜΑ 87 ΔΥΟ ΑΦΕΤΗΡΙΕΣ: το παιχνίδι ξεκινά άδειο δίπλα στο σκάφος, και η παλιά
αποικία μένει ως εξάρτημα δοκιμών (src/colony.asm, build/colony.sna) — τα
περισσότερα τεστ θέλουν θόλους για να δοκιμάσουν κάτι.

ΑΔΕΙΑ ΑΡΧΗ (main.sna):
  οικονομία  ΟΛΑ τα 97 bytes μηδέν, εκτός από τα αποθέματα (νερό 60, φαΐ 100,
             μετάλλευμα 60, μέταλλο 189, βιοπλαστικό 107, ανταλλακτικά 12 — τα
             σημερινά συν η αξία της παλιάς αποικίας χωρίς την πλατφόρμα· φαΐ
             40 και ανταλλακτικά 4 ως το βήμα 120), το ρολόι (sol 12.000
             frames, μέρα 7.200, μέρα 1), τη γεννήτρια συμβάντων ΑΠΟ ΤΟ SEED
             ΤΟΥ ΚΟΣΜΟΥ (το G_worldinfo της τράπεζας 6, #ACE1 αν είναι μηδέν·
             ως το βήμα 120 πάντα #ACE1), το ρεύμα και το οξυγόνο εντάξει, 6
             ζωντανούς και ταβάνι 6 (κανένα Control· 4 και 4 ως το βήμα 120)·
             και η μετεωρική βροχή (86-90) και οι Build
             (EC_NBUILD, 91) μηδέν: ως το βήμα 87 η βροχή έμενε όπως ήταν, και
             μια νέα παρτίδα μέσα σε βροχή συνέχιζε τη βροχή· και τα πλοία
             αποίκων φέρνουν 20% από κάθε ειδικότητα (EC_LAND, 92-96, βήμα 91)
  εργασίες   το είδος κάθε θέσης 255 (NO_JOB), τα άλλα bytes όπως ήταν
  γράφος     κανένας βαθμός: ούτε θόλος ούτε ακμή
  τράπεζα 6  από τους πράκτορες ως το τέλος των διαδρόμων μηδέν, εκτός από:
             το σκάφος, δομή 0 (κόμβος 64): (0,0), K_SHIP, μέγεθος 0, ενεργό,
             ζωή 255· έξι αποίκους (ρόλοι 0, 0, 1, 2, 0, 0) στον κόμβο 64, ΕΞΩ
             (μόνο F_ALIVE), με γεμάτες ανάγκες και στολή δέκα λεπτών (234,
             βήμα 90), στις θέσεις του δακτυλίου που δίνει το corr_fill· και
             τρεις στήλες πρακτόρων στο 255 (θέση, ακμή, εργασία)
  κόσμος     μόνο κατοχή (bit 4) στα 2x2 tiles του σκάφους, (-1..0, -1..0),
             χωρίς θεμέλιο· τίποτε άλλο

ΑΠΟΙΚΙΑ ΔΟΚΙΜΩΝ (colony.sna) — ό,τι ήταν η αρχή ως το βήμα 86:
  οικονομία  όπως πάνω, με μέταλλο 75, βιοπλαστικό 45 και ταβάνι 8, και τα
             φαΐ 40, ανταλλακτικά 4 και 4 ζωντανοί του βήματος 119
  γράφος     0-1, 0-2, 2-64 (η πλατφόρμα), 0-65 (το airlock), και οι δύο
             κατευθύνσεις· κανένας άλλος βαθμός
  τράπεζα 6  τρεις μικρούς θόλους (οξυγόνο, κατάλυμα, κυλικείο) στα (0,0),
             (16,0), (0,16), ενεργούς, με μία μηχανή — τη γεννήτρια οξυγόνου
             του πρώτου, 200 ζωή· την πλατφόρμα στο (-16,16)· το airlock στο
             (0,-10) με τον διάδρομό του (ST_JOINED, βήμα 87)· τους τρεις
             διαδρόμους· τέσσερις αποίκους ΜΕΣΑ (F_ALIVE + F_INDOORS), με την
             ίδια στολή: τη γεμίζει το ng_people, που είναι κοινό
  κόσμος     θεμέλιο και κατοχή στα 4x4 των τεσσάρων και στα 2x2 του airlock,
             και μόνο κατοχή στα tiles των τριών διαδρόμων
  και στις δύο: rt_dirty = 1, wh_slot = 0

Σε οκτώ αφετηρίες η καθεμία: η πρώτη είναι το παιχνίδι όπως τρέχει, οι άλλες
γεμίζουν με σκουπίδια ό,τι σκουπίζει ή γράφει το game_new και όλο το επίπεδο.

ΓΙΑΤΙ. Ως το βήμα 74 το game_new το έβλεπαν μόνο τα σενάρια που ξεκινούν από
αυτό. Από 36 σκόπιμα λάθη του βήματος 74, τα 18 πέρασαν από δεκατέσσερα τεστ
που ξεκινούν από το game_new — όλη η σφραγίδα θεμελίου κάτω από την αποικία
ανάμεσά τους — και ένα δεν αλλάζει τίποτα (βλ. DESIGN §10.1). Αυτό εδώ πιάνει
τα 35.

Και ο ΧΡΟΝΟΣ: όλο το game_new, μαζί με την πρώτη σχεδίαση του ui_init, όχι
πιο αργό από όσο μετρήθηκε στο βήμα 74. Με το newgame.asm του βήματος 73
αποτυγχάνει.

Οι επτά αφετηρίες με σκουπίδια γράφουν σκουπίδια και στο G_worldinfo: η
γεννήτρια συμβάντων πρέπει να βγαίνει από αυτά, όχι από το #ACE1.

Αρνητικά, με το snapshot πειραγμένο: δύο στήλες πρακτόρων αντί για τρεις,
το σκάφος με μία σειρά κατοχής, οι άποικοι μέσα, ένα ζευγάρι οικονομίας
λιγότερο, οι ανάγκες σε δύο σελίδες, ο σπόρος πάντα #ACE1 και πλήρωμα
τεσσάρων (βήμα 120)· και στην αποικία τρεις σειρές θεμελίου αντί για
τέσσερις και το airlock χωρίς ST_JOINED.
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
import reach                                             # noqa: E402
import econ as EC                                        # noqa: E402
from test_route import tiles_of                          # noqa: E402
from test_corridor import Ends                           # noqa: E402

PROBE = 0x3E00
ECON_N = EC.ECON_BYTES                                   # ως και το EC_NBUILD (βήμα 88)
CEIL = 480535                                            # µs, βήμα 74· στο 73: 482229
# §10.1 και src/const.asm
STOCK = {0: 60, 1: 100, 2: 60, 3: 189, 4: 107, 6: 12}   # S_* -> απόθεμα (βήμα 87, 120)
STOCK_COL = {0: 60, 1: 40, 2: 60, 3: 75, 4: 45, 6: 4}    # η αποικία δοκιμών
SHIP_NODE, K_SHIP = 64, 7
CREW = [0, 0, 1, 2, 0, 0]                                # οι ρόλοι στο σκάφος (βήμα 120)
SUIT_START = 234                                         # δέκα λεπτά (βήμα 90, src/suit.asm)
DOMES = [(0, 0, 4), (16, 0, 2), (0, 16, 3)]              # cx, cy, δωμάτιο
PAD = (-16, 16, 6)                                       # cx, cy, K_PAD
LOCK = (0, -10, 5)                                       # cx, cy, K_AIRLOCK (βήμα 86)
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
    def __init__(self, sym, patch=(), sna=TG.SNA):
        self.sym = sym
        m = self.m = cpc.CPC()
        m.run_frames(60)
        assert m.quickload(sna, start=False), "quickload απέτυχε"
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


def econ_jobs(L, b2, stock, popcap, alive, seed):
    """Η οικονομία και οι εργασίες, κοινές στις δύο αφετηρίες."""
    ge, gj = L["G_econ_state"] - 0x8000, L["G_job_tbl"] - 0x8000
    b2[ge:ge + ECON_N] = bytes(ECON_N)                  # όλη (βήμα 88· 86 ως το 87)
    for s_, v in stock.items():
        b2[ge + 2 * s_] = v
    for off, v in ((64, 12000), (66, 7200), (54, seed or 0xACE1)):
        b2[ge + off], b2[ge + off + 1] = v & 255, v >> 8
    for off, v in ((49, 1), (46, 1), (47, 1), (58, alive), (74, popcap)):
        b2[ge + off] = v
    for r in range(5):
        b2[ge + 92 + r] = 2                             # EC_LAND: 20% η καθεμία (βήμα 91)
    for j in range(32):
        b2[gj + 5 * j] = NO_JOB
    nodes = L["G_rt_nodes"] - 0x8000
    b2[nodes:nodes + 128] = bytes(128)


def wipe6(L, before):
    """Η τράπεζα 6 από τους πράκτορες ως το τέλος των διαδρόμων: μηδέν, και
    τρεις στήλες πρακτόρων στο 255."""
    ag, end = L["G_agent_fields"] - 0x4000, L["G_corr_tbl"] + 96 * 5 - 0x4000
    b6 = bytearray(before[6])
    b6[ag:end] = bytes(end - ag)
    for page in (1, 2, 3):                               # θέση, ακμή, εργασία
        o = ag + 256 * page + 128
        b6[o:o + 128] = b"\xff" * 128
    return b6


def crew(L, b6, fill, people, flags):
    """Οι τέσσερις: (ρόλος, κόμβος), οι σημαίες, οι θέσεις του δακτυλίου."""
    ag, occ = L["G_agent_fields"] - 0x4000, L["G_node_occ"] - 0x4000
    for a, (role, node) in enumerate(people):
        slot = next(s_ for s_ in fill if not b6[occ + node] >> s_ & 1)
        b6[occ + node] |= 1 << slot
        b6[ag + a], b6[ag + a + 128] = flags, role
        b6[ag + 256 + a], b6[ag + 256 + a + 128] = node, slot
        b6[ag + 512 + a] = node                          # προορισμός
        for page in (4, 5, 6):
            b6[ag + 256 * page + a] = b6[ag + 256 * page + a + 128] = 255
        b6[ag + 256 * 7 + a] = SUIT_START                # η στολή· το φορτίο 0


def seed_of(L, before):
    """Ο σπόρος του κόσμου, όπως τον άφησε η γεννήτρια στην τράπεζα 6."""
    w = L["G_worldinfo"] - 0x4000
    return before[6][w] | before[6][w + 1] << 8


def rule_empty(L, before, fill):
    """Η άδεια αρχή δίπλα στο σκάφος (βήμα 87)."""
    b2, b4 = bytearray(before[2]), bytearray(before[4])
    econ_jobs(L, b2, STOCK, 6, 6, seed_of(L, before))
    b6 = wipe6(L, before)
    gs = L["G_struct_tbl"] - 0x4000
    b6[gs:gs + 6] = bytes([0, 0, K_SHIP, 0, DS_ACTIVE, 255])
    crew(L, b6, fill, [(r, SHIP_NODE) for r in CREW], 1)          # F_ALIVE: έξω
    for x in (-1, 0):                                    # κατοχή, όχι θεμέλιο
        for y in (-1, 0):
            b4[(y + 64) * 128 + x + 64] |= 0x10
    return b2, b6, b4


def rule_colony(L, before, fill):
    """Η αποικία δοκιμών: η αρχή ως το βήμα 86, με το ST_JOINED του 87."""
    b2, b4 = bytearray(before[2]), bytearray(before[4])
    econ_jobs(L, b2, STOCK_COL, 8, 4, seed_of(L, before))
    nodes, adj = L["G_rt_nodes"] - 0x8000, L["G_node_adj"] - 0x8000
    for x, y in ((0, 1), (1, 0), (0, 2), (2, 0), (2, 64), (64, 2), (0, 65), (65, 0)):
        b2[adj + 8 * x + b2[nodes + x]] = y
        b2[nodes + x] += 1
    b6 = wipe6(L, before)
    gd, gs, gc = L["G_dome_tbl"] - 0x4000, L["G_struct_tbl"] - 0x4000, L["G_corr_tbl"] - 0x4000
    for d, (cx, cy, room) in enumerate(DOMES):
        rec = [cx & 255, cy & 255, 0, room, DS_ACTIVE, 255, 0, 0] + [NO_MACH] * 8 + [0] * 8
        if d == 0:
            rec[8], rec[16] = 0, 200                     # γεννήτρια οξυγόνου, καινούργια
        b6[gd + 24 * d:gd + 24 * d + 24] = bytes(rec)
    b6[gs:gs + 6] = bytes([PAD[0] & 255, PAD[1], PAD[2], 0, DS_ACTIVE, 255])
    b6[gs + 8:gs + 15] = bytes([LOCK[0], LOCK[1] & 255, LOCK[2], 0, DS_ACTIVE, 255, 1])
    b6[gc:gc + 15] = bytes([0, 1, 2, 4, DS_ACTIVE, 0, 2, 4, 4, DS_ACTIVE,
                            0, 65, 0, 2, DS_ACTIVE])
    crew(L, b6, fill, ROLES, 3)                          # F_ALIVE + F_INDOORS
    # ο κόσμος: έδαφος και κατοχή κάτω από τα τέσσερα, το decor μένει — ΟΧΙ
    # θεμέλιο από το βήμα 94 (src/colony.asm: οι θόλοι στο έδαφός τους)...
    for cx, cy in [(d[0], d[1]) for d in DOMES] + [PAD[:2]]:
        tx, ty = (cx >> 1) - 2, (cy >> 1) - 2
        for i in range(4):
            for j in range(4):
                k = (ty + j + 64) * 128 + tx + i + 64
                b4[k] = b4[k] & 0xC0 | 0x10
    for x in (-1, 0):                                    # το airlock, 2x2
        for y in (-6, -5):
            k = (y + 64) * 128 + x + 64
            b4[k] = b4[k] & 0xC0 | 0x10
    # ...και ΜΟΝΟ κατοχή στους διαδρόμους (cr_stamp: όχι θεμέλιο, §9.4), και
    # από το βήμα 96 στα tiles του μισού πλάτους, όσα είναι ελεύθερα
    # (cr_stampx, το reach.half_tiles): ο διάδρομος στο κέντρο του θόλου πατά
    # 1 byte ή 4 γραμμές στο διπλανό tile.
    for b in (1, 2, 65):
        a_ = (DOMES[0][0], DOMES[0][1], 0)
        z = (LOCK[0], LOCK[1], route.AIRLOCK) if b == 65 else (DOMES[b][0], DOMES[b][1], 0)
        side, runs = route.plan(*a_, *z)
        ends = (a_, z) if side == 0 else (z, a_)
        for x, y in tiles_of(Ends(*ends), 0, runs, 1):
            b4[(y + 64) * 128 + x + 64] |= 0x10
        for x, y in reach.half_tiles(ends[0], ends[1], runs):
            k = (y + 64) * 128 + x + 64
            if not b4[k] & 0x30:
                b4[k] |= 0x10
    return b2, b6, b4


def check(sym, patch=(), n=8, timing=False, colony=False):
    """Η πρώτη διαφορά από τον κανόνα, ή None· και ο χρόνος της πρώτης."""
    G = Game(sym, patch, TG.COLONY if colony else TG.SNA)
    rule = rule_colony if colony else rule_empty
    L = layout()
    fill = list(G.bank(2, L["G_corr_fill"] - 0x8000, 8))
    rnd = random.Random(74)
    t0 = None
    for case in range(n):
        G.restore()
        if case:
            G.put(6, 0x2C00, bytes(rnd.randrange(256) for _ in range(0x1400)))
            G.put(2, L["G_econ_state"] - 0x8000,
                  bytes(rnd.randrange(256) for _ in range(L["G_hud_shadow"] - L["G_econ_state"])))
            G.put(4, 0, bytes(rnd.choice([0, 1, 7, 0x40, 0x88, 0xC5, 0x17, rnd.randrange(256)])
                              for _ in range(0x4000)))
        before = [G.bank(k) for k in range(8)]
        t = G.run(step=1 if timing and case == 0 else 20)
        if case == 0:
            t0 = t
        b2, b6, b4 = rule(L, before, fill)
        lo = L["G_econ_state"] - 0x8000
        # ως την κρυφή μνήμη του HUD, που τη γράφει η πρώτη σχεδίαση· ως το βήμα
        # 84 ήταν σταθερά στο #A500, από το 85 (οι μηχανές στην τράπεζα 5) πιο
        # κάτω — και ένα σταθερό #A500 έγραφε σκουπίδια πάνω στον κώδικα
        # ως το τέλος των διαδρόμων: μετά είναι η κρυφή μνήμη φιγούρων, που την
        # ξαναχτίζει η πρώτη σχεδίαση του ui_init
        b6end = L["G_corr_tbl"] + 96 * 5 - 0x4000
        for name, k, want, a, z in (("η τράπεζα 2", 2, b2, lo, L["G_hud_shadow"] - 0x8000),
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
        print("OK το game_new = το §10.1: οικονομία, εργασίες, κανένας θόλος, το σκάφος, "
              "έξι άποικοι έξω, η κατοχή του σκάφους, ο σπόρος από τον κόσμο, σε 8 "
              "αφετηρίες")
    print(f"    game_new με το ui_init: {t} us")
    if t > CEIL:
        print(f"ΑΠΟΤΥΧΙΑ: πιο αργό από το βήμα 74: {t} > {CEIL}")
        fails += 1
    else:
        print("OK όχι πιο αργό από το βήμα 74")
    why, _ = check(sym, colony=True)
    if why:
        print(f"ΑΠΟΤΥΧΙΑ αποικία δοκιμών: {why}")
        fails += 1
    else:
        print("OK η αποικία δοκιμών (colony.sna) = η αρχή ως το βήμα 86: θόλοι, "
              "πλατφόρμα, airlock με ST_JOINED, διάδρομοι με τα μισά tiles τους, "
              "άποικοι μέσα, θεμέλιο")

    m = cpc.CPC()
    m.run_frames(60)
    assert m.quickload(TG.SNA, start=False)

    def find(pat, at="GAME_NEW", span=400):
        i = m.read_ram(sym[at], span).find(bytes(pat))
        assert i >= 0, f"δεν βρέθηκε το {pat}"
        return sym[at] + i

    econ_n = (sym["NG_ECON_END"] - sym["NG_ECON"]) // 2
    crew = sym["NG_CREW"]
    wi = layout()["G_worldinfo"]
    neg = [("δύο στήλες πρακτόρων", [(find([0x0E, 3, 0x06, 128]) + 1, 2)], False),
           # το τρίτο set 4,(hl) του σκάφους — μετά το ld de,127 · add hl,de
           ("το σκάφος με μία σειρά κατοχής",
            [(find([0x11, 0x7F, 0x00, 0x19, 0xCB, 0xE6]) + 4, 0),
             (find([0x11, 0x7F, 0x00, 0x19, 0xCB, 0xE6]) + 5, 0)], False),
           # ld de,ng_crew · ld a,F_ALIVE γίνεται ld a,F_ALIVE + F_INDOORS
           ("οι άποικοι μέσα",
            [(find([0x11, crew & 255, crew >> 8, 0x3E, 0x01]) + 4, 3)], False),
           ("ένα ζευγάρι οικονομίας λιγότερο", [(find([0x06, econ_n]) + 1, econ_n - 1)], False),
           ("οι ανάγκες σε δύο σελίδες", [(find([0x06, 3, 0x36, 255]) + 1, 2)], False),
           # ld hl,(G_worldinfo) γίνεται ld hl,#ACE1 και ένα nop (βήμα 120)
           ("ο σπόρος πάντα #ACE1",
            [(find([0x2A, wi & 255, wi >> 8]), 0x21), (find([0x2A, wi & 255, wi >> 8]) + 1, 0xE1),
             (find([0x2A, wi & 255, wi >> 8]) + 2, 0xAC)], False),
           # ο πέμπτος του πληρώματος γίνεται το 255 που το κλείνει: τέσσερις
           ("πλήρωμα τεσσάρων, όπως ως το βήμα 120", [(crew + 8, 255)], False),
           # Από το βήμα 86 οι σειρές είναι 2 x ng_r (4 για θόλο, 2 για το airlock):
           # ld a,(ng_r) · add a,a · ld c,a γίνεται ld c,3 και τρία nop.
           ("τρεις σειρές θεμελίου στην αποικία",
            list(zip(range(find([0x3A, sym["NG_R"] & 255, sym["NG_R"] >> 8, 0x87, 0x4F, 0xE5],
                                "NGT_COLONY", 600), 10**6), [0x0E, 3, 0, 0, 0])), True),
           # ld a,1 · ld (struct 1 + ST_JOINED),a γίνεται ld a,0
           ("το airlock της αποικίας χωρίς ST_JOINED",
            [(find([0x3E, 0x01, 0x32], "NGT_COLONY", 600) + 1, 0)], True)]
    for label, patch, col in neg:
        why, _ = check(sym, patch, n=3, colony=col)
        if why:
            print(f"OK ΑΡΝΗΤΙΚΟ: με {label} αποτυγχάνει ({why[:90]})")
        else:
            print(f"ΑΠΟΤΥΧΙΑ ΑΡΝΗΤΙΚΟΥ: με {label} περνά")
            fails += 1
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
