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
  η οθόνη         ο κρατήρας μπαίνει στη λίστα αλλαγών (DK_TILE, x, y), και
                  από το βήμα 100 μια μηχανή θόλου που δούλευε και σταμάτησε
                  (DK_MACH, θόλος, υποδοχή): το σήμα της· από το βήμα 109
                  μια δομή που ξαναγίνεται εργοτάξιο (DK_TILE, το tile του
                  κέντρου της): οι ρίγες του εργοταξίου· αν η λίστα είναι
                  γεμάτη, σηκώνεται η σημαία
  η ησυχία        από το βήμα 121 μια βροχή αρχίζει μόνο αν το ev_may το
                  επιτρέπει (20 ζωντανοί, δύο sol από την προηγούμενη
                  καταστροφή, 64 περιστροφές από το τελευταίο γεγονός), και
                  τότε οι δύο χρονοσφραγίδες στην τράπεζα 6 είναι το τώρα
  και ακόμα       mt_boom = 1 σε κάθε κρούση, ec_fdiv = 1 όταν μια δομή ξαναγίνει
                  εργοτάξιο, eb_d/eb_s όταν σταματά μηχανή θόλου, και η τράπεζα 6
                  στο παράθυρο όταν γυρίζει· από το βήμα 115 το jb_lost (το
                  πάνω byte της διεύθυνσής του) όταν η Build δεν βρίσκει θέση ούτε
                  δίνοντας μια αδιάθετη Operate ή Repair, και ο σωρός ενός
                  ορυχείου που ξαναγίνεται εργοτάξιο 0 (από την αναφορά)

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

ΔΥΟ ΠΕΡΑΣΜΑΤΑ ΑΠΟ ΤΟ ΒΗΜΑ 156, που οι δομές έγιναν 48: οι 400 σκηνές του
βήματος 155 ακριβώς (οι δομές 32-47 άδειες), με τα ταβάνια ως τότε, και οι
ίδιες με δομές και στις 32-47, από δική τους ζαριά (xrnd), με δικά τους. Από
το βήμα 157 κάθε σκηνή γράφει και το όριο σάρωσης του πίνακά της
(codeat.set_top): οι δομές της κρούσης σταματούν εκεί.

Αρνητικά, με τον κώδικα πειραγμένο στη μνήμη: κρατήρας και πάνω σε διάδρομο,
κρούση έξω από τον κόσμο που δεν γυρίζει, θόλοι με πλευρά 2 + 2*μέγεθος, η
μηχανή από το λάθος byte, το «κοντινό» κέντρο στα 3 tiles, το σκάφος σαν
κτίριο, το airlock χωρίς το lk_air_out· και από το βήμα 156 το mt_scan μόνο
στις 32 πρώτες δομές.
"""
import copy, ctypes, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import codeat                                            # noqa: E402
import cpc                                               # noqa: E402
import econ as EC                                        # noqa: E402

PROBE = 0x3E80
OLD_NS = 32                 # οι δομές ως το βήμα 155: η ζαριά τους μένει ίδια
DK_MACH, DK_TILE, DIRTY_N = 1, 4, 32
K_SHIP = 7                               # src/const.asm: δεν είναι κτίριο (βήμα 87)
K_AIRLOCK = 5                            # src/const.asm: η κρούση του βγάζει τον κόσμο έξω
FT_CLS = 250                             # src/const.asm: τα φυτά δεν είναι «χαλασμένα» (βήμα 119)
# µs ανά κλήση, μαζί με τη σκαλωσιά του probe· βήμα 76, και στο 75
CEIL = {
    "ήσυχο": 41,        # καμία βροχή, καμία αρχή                         41
    "αρχή": 7041,       # ξεκινά βροχή (ή δεν βρίσκει κτίριο)           8451
    "ησυχία": 193,      # η ζαριά έπεσε, η ησυχία λέει όχι (βήμα 121)
    "έξω": 285,         # κρούση έξω από τον κόσμο                       299
    "κτίριο": 6330,     # κρούση σε κτίριο                              6440
    "έδαφος": 5450,     # κρούση στο έδαφος, με ή χωρίς κρατήρα         6389
}
# ΤΟ ΕΔΑΦΟΣ ΑΠΟ ΤΟ ΒΗΜΑ 156, 5450 ως τότε (5444): οι δομές 48, και το mt_scan
# περνά 16 θέσεις ακόμη πριν πει «έδαφος», ~20 us η άδεια — 29 όταν το κέντρο
# της (σκουπίδια ή παλιό) πέφτει κοντά: 5444 -> 5904 στις ίδιες σκηνές. Η
# αρχή 1300 -> 1762 για τον ίδιο λόγο, κάτω από το ταβάνι της.
# Και οι ίδιες σκηνές με δομές στις θέσεις 32-47 (xrnd): η αρχή και το κτίριο
# στα ταβάνια τους, το έδαφος 6536.
# ΚΑΙ ΠΙΣΩ ΣΤΟ 5450 ΑΠΟ ΤΟ ΒΗΜΑ 157: το όριο σάρωσης (src/top.asm) σταματά τις
# δομές της κρούσης στην ψηλότερη θέση σε χρήση, και το mt_byte τρέχει τον
# Galois μέσα στον βρόχο του (~80 us): έδαφος 5904 -> 5370, κτίριο 6330 ->
# 6256 (+6 το όριο, -80 το mt_byte), αρχή 1762 -> 1228 (και το mts_lp ως το
# ST_TEND). Με τις 32-47: έδαφος 6536 -> 6464, κτίριο 6256, αρχή 1228.
CEIL48 = {"αρχή": 7041, "κτίριο": 6330, "έδαφος": 6540}
# ΤΟ ΚΤΙΡΙΟ ΚΑΙ ΤΟ ΕΔΑΦΟΣ ΑΠΟ ΤΟ ΒΗΜΑ 151, 5270 και 5170 ως τότε: οι σκηνές
# έχουν τα ενεργειακά στο μέγεθος που φτιάχνει το παιχνίδι, μεγαλύτερα από τα 0
# και 1 που είχαν ως τότε, και ένα από αυτά τα κέντρα χτυπά για πρώτη φορά ένα
# έτοιμο airlock (lk_air_out, ~1,1 ms· το tests/test_suit.py το κρατά κάτω από
# 7.100 από το βήμα 104). Με τον κώδικα του βήματος 150 οι ίδιες σκηνές μετρούν
# ακριβώς το ίδιο, 6.327 και 5.445: δεν άλλαξε το παιχνίδι, άλλαξε το δείγμα.


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
            codeat.poke(m, at, v)               # το mt_tick στο b6code (βήμα 110)
        self.ptr = [cpc._lib.cpcemu_ram_ptr(m._h, n) for n in range(8)]
        self.keep = [self.bank(n) for n in range(8)]
        self.ph = codeat.phase(m)               # η φάση της μέτρησης (βήμα 155)

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
        return t - self.ph


def scene(R, rnd, case, extra=True):
    """Μια τυχαία κατάσταση στη μνήμη· γυρίζει (είδος, r1). Χωρίς extra οι
    δομές 32-47 μένουν άδειες: η σκηνή του βήματος 155 ακριβώς."""
    L = R.L
    mcx, mcy = rnd.randrange(-64, 64), rnd.randrange(-64, 64)
    if rnd.random() < 0.15:
        mcx = rnd.choice([-64, -60, 58, 63])
    if rnd.random() < 0.15:
        mcy = rnd.choice([-64, -61, 59, 63])
    dims = EC.struct_dims()

    def place(rec, b, w, h, z=None):
        """Ένα κέντρο κοντά στο κέντρο της βροχής, με όλο το αποτύπωμα μέσα
        στον κόσμο, όπως το εγγυάται το χτίσιμο: ένας θόλος στο x = -61 με
        πλευρά 8 θα τυλιγόταν στο +63, και εκεί η αναφορά τον βρίσκει ενώ το
        φίλτρο «κοντά» του Z80 όχι."""
        z = z or rnd
        for k, (c, n) in enumerate(((mcx, w), (mcy, h))):
            t0 = max(-64, min(64 - n, c + z.randrange(-11, 12) - n // 2))
            rec[b + k] = (2 * t0 + n + z.randrange(2)) & 255

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
    # ΟΙ 32 ΠΡΩΤΕΣ ΔΟΜΕΣ ΑΠΟ ΤΗΝ ΙΔΙΑ ΖΑΡΙΑ ΜΕ ΤΟ ΒΗΜΑ 155, οι 32-47 (βήμα 156)
    # από δική τους: οι 400 σκηνές μένουν ίδιες, με δομές και πιο πάνω
    xrnd = random.Random(15600 + case)
    st = bytearray(rnd.randrange(256) for _ in range(OLD_NS * EC.STRUCT_REC))
    st += bytes(xrnd.randrange(256) for _ in range((EC.MAX_STRUCT - OLD_NS) * EC.STRUCT_REC))
    for s in range(EC.MAX_STRUCT):
        b = s * EC.STRUCT_REC
        z = rnd if s < OLD_NS else xrnd
        # 0-3: το μέγεθος 2, και το 3 χωρίς σχήμα. Ως το βήμα 150 και τα 0 και 1,
        # που το παιχνίδι δεν φτιάχνει ποτέ: από το 151 είναι χωρίς σχήμα κι αυτά
        # (tools/pack.py). Η ίδια ζαριά (max): το δείγμα μένει όπως ήταν.
        sk = z.randrange(8)
        st[b + 2], st[b + 3] = sk, max(2, z.choice([0, 1, 2, 2, 3])) if sk < 4 else 0
        k = st[b + 2] * 8 + st[b + 3] * 2
        w, h = dims[k] // 4, dims[k + 1] // 16
        if z.random() < ds and (extra or s < OLD_NS):
            place(st, b, w, h, z)
            st[b + 4] = z.choice([1, 2, 2, 3])
        else:
            st[b + 4] = 0
            if z.random() < 0.3:
                place(st, b, w, h, z)
    # ΒΡΟΧΗ ΟΤΑΝ Η ΔΟΜΗ 31 ΔΕΝ ΕΙΝΑΙ ΕΙΔΟΥΣ 0, όχι όταν case % 4 != 0. Ετσι ήταν
    # από το βήμα 76: το kind του βρόχου των δομών σκέπαζε το case % 4, και η
    # τελευταία δομή ήταν η 31. Βγήκε στο βήμα 156, όταν η τελευταία έγινε η 47
    # και οι σκηνές άλλαξαν· μένει, για να μείνουν οι 400 σκηνές ίδιες.
    kind = st[(OLD_NS - 1) * EC.STRUCT_REC + 2]
    if rnd.random() < 0.3:
        # ΤΑ ΟΡΙΑ ΤΩΝ ΠΙΝΑΚΩΝ: ζωντανοί μόνο ένας ως τρεις από τους κόμβους στις
        # άκρες τους. Ο θόλος 63 που μετριέται για δομή, η δομή 95 που δεν
        # ελέγχεται ποτέ ως κέντρο, η πρώτη δομή: με όλο τον πίνακα γεμάτο,
        # κανένα από αυτά δεν φαινόταν (βήμα 76). Από το βήμα 156 και οι 96,
        # 110, 111: η πρώτη της δεύτερης σελίδας και οι δύο τελευταίες.
        for d in range(EC.MAX_DOME):
            dom[d * EC.DOME_REC + 4] = 0
        for n_ in range(EC.MAX_STRUCT):
            st[n_ * EC.STRUCT_REC + 4] = 0
        ends = rnd.sample([0, 62, 63, 64, 65, 94, 95], rnd.randrange(1, 4))
        ends += xrnd.sample([96, 110, 111], xrnd.randrange(0, 3)) if extra else []  # βήμα 156
        for n_ in ends:
            if n_ < EC.MAX_DOME:
                b = n_ * EC.DOME_REC
                side = 4 + 2 * dom[b + 2]
                place(dom, b, side, side)
                dom[b + 4] = rnd.choice([1, 2, 2, 2])
            else:
                b = (n_ - EC.MAX_DOME) * EC.STRUCT_REC
                z = rnd if n_ < EC.MAX_DOME + OLD_NS else xrnd
                st[b + 2], st[b + 3] = z.randrange(4), max(2, z.randrange(3))  # βήμα 151
                k = st[b + 2] * 8 + st[b + 3] * 2
                place(st, b, dims[k] // 4, dims[k + 1] // 16, z)
                st[b + 4] = z.choice([1, 2, 2])
    # ΚΑΝΕΝΑ AIRLOCK ΟΠΟΥ ΣΤΕΚΕΤΑΙ Ή ΦΤΑΝΕΙ ΑΠΟΙΚΟΣ (βήμα 151). Η κρούση σε
    # έτοιμο airlock βγάζει όσους είναι μέσα του έξω (lk_air_out, src/door.asm),
    # και τους δείχνει στο εργοτάξιο (fg_mark) — αυτό το μετρά το
    # tests/test_suit.py. Εδώ ο κανόνας ξέρει μόνο τα δύο bytes του lk_each. Ως
    # το βήμα 150 κανένα έτοιμο airlock δεν χτυπήθηκε σε αυτές τις 400 σκηνές:
    # τα ενεργειακά ήταν και στα μεγέθη 0 και 1, μικρότερα, και τα κέντρα
    # έπεφταν αλλού. Χωρίς rnd: οι σκηνές μένουν όσες ήταν.
    ag, adj = R.bank(6)[L["G_agent_fields"] - 0x4000:], R.bank(2)[L["G_node_adj"] - 0x8000:]
    near = set()
    for i in range(128):
        if ag[i] & 1:                                       # F_ALIVE
            node, edge = ag[256 + i], ag[512 + 128 + i]
            near.add(node if edge == 255 else adj[node * 8 + edge] if ag[i] & 2 else node)
    for s_ in range(EC.MAX_STRUCT):
        if EC.MAX_DOME + s_ in near and st[s_ * EC.STRUCT_REC + 2] == K_AIRLOCK:
            st[s_ * EC.STRUCT_REC + 2] = K_SHIP             # ίδιο σχήμα, δεν χτυπιέται
    R.put(6, L["G_dome_tbl"] - 0x4000, dom)
    R.put(6, L["G_struct_tbl"] - 0x4000, st)
    codeat.set_top(R.m, R.sym, codeat.top_of(st))       # το όριο σάρωσης (βήμα 157)
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
    # Η ΗΣΥΧΙΑ (βήμα 121, ev_may): ζωντανοί, sol, και οι δύο χρονοσφραγίδες
    # [sol, frame] στην τράπεζα 6 — από δική τους γεννήτρια, ώστε οι σκηνές
    # του βήματος 76 να μένουν ίδιες. «Ποτέ» τις μισές φορές, για να αρχίζουν
    # βροχές· πρόσφατη, πριν από τρία sol, ή ό,τι να 'ναι τις άλλες.
    q = random.Random(1210 + case)
    e[58] = q.choice([20, 20, 45, 19, 4])
    e[51] = q.randrange(256)

    def stamp():
        k = q.randrange(6)
        if k < 3:
            return [0, 0, 0]
        if k == 3:
            f = (fr - q.randrange(1, 3000)) & 0xFFFF
            return [e[51], f & 255, f >> 8]
        if k == 4:
            return [(e[51] - 3) & 255, q.randrange(256), q.randrange(256)]
        return [q.randrange(256) for _ in range(3)]
    R.put(6, L["G_node_occ"] - 0x4000 + EC.X_OFF, bytes(stamp() + stamp()))
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
    # η χαλασμένη της γραμμής ειδοποιήσεων (βήμα 119): ένας «θόλος» που δεν
    # υπάρχει, για να φανεί αν γράφτηκε· χωρίς το rnd, ώστε οι 400 περιπτώσεις
    # να μένουν όσες ήταν
    m.poke(sym["AL_BRK"], case & 7)
    m.poke(sym["AL_BRK"] + 1, 200 + (case & 31))
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
    e.alive, e.sol = raw[58], raw[51]        # η ησυχία (βήμα 121)
    e.sollen = raw[64] | (raw[65] << 8)
    gx = L["G_node_occ"] - 0x4000 + EC.X_OFF
    x = b[6][gx:gx + EC.X_N]
    e.ldis, e.lev = [x[0], x[1] | x[2] << 8], [x[3], x[4] | x[5] << 8]
    e.flow_div = 255
    e.lost = False                           # βήμα 115: σηκώνεται μόνο αν δεν χώρεσε
    impact = e.meteor > 0
    if impact:
        f = copy.copy(e)
        byte = EC._mbyte(f)
        tx, ty = s8(e.mcx + (byte & 15) - 8), s8(e.mcy + (byte >> 4) - 8)
        inside = -64 <= tx < 64 and -64 <= ty < 64
        node = hit_node(e, tx, ty) if inside else None
    rolled = not impact and (r1 >> 4) == 0xFFF
    started = rolled and EC.may(e)
    dome0 = bytes(e.dome)                    # η υγεία πριν, για το σήμα (βήμα 100)
    struct0 = bytes(e.struct)                # η κατάσταση πριν, για τις ρίγες (βήμα 109)
    EC.meteor_tick(e, r1)
    b[6][gd:gd + len(e.dome)] = e.dome
    b[6][gs:gs + len(e.struct)] = e.struct
    b[2][gj:gj + len(e.job)] = e.job
    b[2][ge + 86] = e.meteor
    b[2][ge + 87], b[2][ge + 88] = e.mcx & 255, e.mcy & 255
    b[2][ge + 89], b[2][ge + 90] = e.mrnd & 255, e.mrnd >> 8
    b[2][ge + 91] = e.nbuild & 255
    b[6][gx:gx + EC.X_N] = EC.x_bytes(e)

    def poke(name, v):
        a = sym[name]
        b[a >> 14 if a < 0x4000 else 2][a & 0x3FFF] = v

    def push(kind, a, c):
        num = b[0][sym["DIRTY_NUM"]]
        if num < DIRTY_N:
            slot = (b[0][sym["DIRTY_HEAD"]] + num) % DIRTY_N
            r = sym["DIRTY_RING"] + 3 * slot
            b[0][r:r + 3] = bytes([kind, a & 255, c & 255])
            poke("DIRTY_NUM", num + 1)
        else:
            poke("DIRTY_OVER", 1)

    if e.flow_div == 1:
        poke("EC_FDIV", 1)
    if e.lost:
        poke("JB_LOST", sym["JB_LOST"] >> 8)  # ld hl,jb_lost · ld (hl),h
    if started:
        # το όριο σάρωσης στο cp του mts_lp (βήμα 157): το ST_TEND της σκηνής
        b[6][sym["MTS_END"] + 1 - 0x4000] = b[2][codeat.TOP_AT - 0x8000]
    if not impact:
        return b, "αρχή" if started else "ησυχία" if rolled else "ήσυχο"
    poke("MT_BOOM", 1)
    if not inside:
        return b, "έξω"
    if node is not None:
        if node < EC.MAX_DOME and e.dome[node * EC.DOME_REC + EC.D_STATE] == EC.DS_ACTIVE:
            poke("EB_D", node)
            poke("EB_S", e.mrnd >> 8)
            d = node * EC.DOME_REC
            s = (e.mrnd >> 8) & (EC.MACHINE_COUNT[dome0[d + EC.D_SIZE]] - 1)
            h = d + EC.D_HEALTH + s
            if dome0[h] & 0x80 and e.dome[h] == 0:
                push(DK_MACH, node, s)       # σταμάτησε: το σήμα (βήμα 100)
                if dome0[d + EC.D_MACH + s] < FT_CLS:
                    poke("AL_BRK", s)        # και η γραμμή το λέει (βήμα 119),
                    b[0][sym["AL_BRK"] + 1] = node   # όχι για φυτό
        if node >= EC.MAX_DOME:
            r = (node - EC.MAX_DOME) * EC.STRUCT_REC
            if struct0[r + 4] == EC.DS_ACTIVE and struct0[r + 2] == K_AIRLOCK:
                # το lk_air_out (βήμα 90): το lk_n, και η κλήση του lk_each που
                # γράφεται στη δική της διεύθυνση — κανείς μέσα (scene)
                poke("LK_N", node)
                a = sym["LKE_CALL"] + 1
                b[2][a & 0x3FFF], b[2][(a + 1) & 0x3FFF] = sym["LKS_OUT"] & 255, sym["LKS_OUT"] >> 8
            if struct0[r + 4] == EC.DS_ACTIVE and struct0[r + 2] != K_SHIP:
                # ξανά εργοτάξιο: τα 3x3 γύρω από το tile του κέντρου (βήμα 109)
                push(DK_TILE, s8(struct0[r]) >> 1, s8(struct0[r + 1]) >> 1)
        return b, "κτίριο"
    at = (ty + 64) * 128 + tx + 64
    t = b[4][at]
    if (t & 0x37) < 3 or (t & 0x37) == 7:
        b[4][at] = (t & 0xC0) | 6
        push(DK_TILE, tx, ty)
    return b, "έδαφος"


def run(sym, patch=(), n=400, times=None, extra=True):
    R = Rig(sym, patch)
    if times is not None:
        times["_ph"] = R.ph
    rnd = random.Random(76)
    for case in range(n):
        R.restore()
        _, r1 = scene(R, rnd, case, extra)
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
                    if k == 0 and (0x00A0 <= off < 0x0100 or PROBE <= off < 0x3F00):
                        continue
                    a = off + (0x8000 if k == 2 else 0x4000 if k in (4, 6) else 0)
                    return (f"περίπτωση {case} ({what}): τράπεζα {k} #{a:04X} = "
                            f"{got[off]}, ο κανόνας λέει {want[k][off]} "
                            f"(πριν {before[k][off]})")
    return None


def main():
    sym, _ = TG.build()
    fails = 0
    times, times48 = {}, {}
    for extra, tm, what in ((False, times, "οι 400 σκηνές του βήματος 155, δομές ως 32"),
                            (True, times48, "οι ίδιες με δομές και στις 32-47")):
        why = run(sym, times=tm, extra=extra)
        if why:
            print(f"ΑΠΟΤΥΧΙΑ: {what}: {why}")
            fails += 1
        else:
            print(f"OK {what}: 400 κλήσεις του mt_tick = η αναφορά, ο κανόνας του κρατήρα "
                  "και η λίστα αλλαγών — και τίποτε άλλο σε καμία τράπεζα")
    print(f"    ΦΑΣΗ: ο μάρτυρας των {codeat.CTRL_N} nop μετρά +{times.get('_ph', 0)} µs από εδώ, "
          f"και αφαιρείται από κάθε μέτρηση (βήμα 155, tests/codeat.py)")
    for tm, ceil, why in ((times, CEIL, "βήμα 76"), (times48, CEIL48, "βήμα 156, δομές ως 48")):
        for k, c in ceil.items():
            t = tm.get(k, 0)
            if t > c:
                print(f"ΑΠΟΤΥΧΙΑ: {k} {t} us > {c} ({why})")
                fails += 1
            else:
                print(f"OK {k:7s} {t:5d} us <= {c}" + ("" if ceil is CEIL else "   (ως 48 δομές)"))

    m = cpc.CPC()
    m.run_frames(60)
    assert m.quickload(TG.COLONY, start=False)

    def find(at, pat, span=400):
        a = codeat.find(m, sym[at], pat, span)  # στην τράπεζα 6 αν είναι στο b6code
        assert a is not None, f"δεν βρέθηκε το {pat}"
        return a

    mr1 = sym["EC_MRND"] + 1 if "EC_MRND" in sym else layout()["G_econ_state"] + 90
    tp = codeat.TOP_AT + 2                      # ST_TOP (βήμα 157)
    # το and W_OCC_MASK | 7 είναι στο mt_crater (src/b6out.asm) από το βήμα 110
    neg = [("κρατήρα και πάνω σε διάδρομο", [(find("MT_CRATER", [0xE6, 0x37]) + 1, 0x07)]),
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
           ("το σκάφος σαν κτίριο", [(find("MTH_STRUCT", [0xFE, 7]) + 1, 255)]),
           # βήμα 151: το airlock που χτυπά χωρίς το call z,lk_air_out — το
           # χτυπά μία σκηνή από τις 400, η 150
           ("το airlock χωρίς το lk_air_out",
            [(find("MT_TICK", [0xCC, sym["LK_AIR_OUT"] & 255, sym["LK_AIR_OUT"] >> 8], 600) + k, 0)
             for k in range(3)]),
           # βήμα 156: το mt_scan των δομών με B = 32, όπως ως το 155 — οι
           # δομές 32-47 δεν χτυπιούνται ποτέ (και ο κόμβος βγαίνει λάθος). Από
           # το 157 το ld a,(ST_TOP) του ορίου σάρωσης γίνεται ld a,32.
           ("μόνο 32 δομές", [(find("MT_TICK", [0x3A, tp & 255, tp >> 8, 0x57, 0x1E,
                                                EC.STRUCT_REC], 600) + k, v)
                              for k, v in enumerate([0x3E, 32, 0])])]
    for label, patch in neg:
        # τα αρνητικά ως το βήμα 155 στις σκηνές του (με τις ίδιες περιπτώσεις
        # που τα πιάνουν), το «μόνο 32» με δομές και στις 32-47
        why = run(sym, patch, n=400 if "σκάφος" in label or "airlock" in label else 120,
                  extra="32" in label)
        if why:
            print(f"OK ΑΡΝΗΤΙΚΟ: με {label} αποτυγχάνει ({why[:90]})")
        else:
            print(f"ΑΠΟΤΥΧΙΑ ΑΡΝΗΤΙΚΟΥ: με {label} περνά")
            fails += 1
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
