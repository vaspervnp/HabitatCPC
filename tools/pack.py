#!/usr/bin/env python3
"""Στρώνει τα assets στις τράπεζες.

Βγάζει τις εικόνες των τραπεζών, τις διευθύνσεις για τον assembler, και έναν
λογαριασμό που διαβάζεται. **Σκάει** αν κάτι δεν χωρέσει — αυτός είναι ο λόγος
που υπάρχει: το DESIGN.md §4.2 είναι χαρτί μέχρι να το μετρήσει κάποιος.

Η τράπεζα 2 ήταν σχεδιασμένη να κάνει δύο δουλειές: σελίδα οθόνης του HUD ΚΑΙ
αποθήκη για τα μικρά γραφικά, με τα γραφικά στριμωγμένα σε οκτώ αρένες ανάμεσα
στις γραμμές του HUD. Το tests/test_camera.py έδειξε ότι η τομή δύο σελίδων δεν
γίνεται — ο CRTC κλειδώνει τη διεύθυνση έναρξης μία φορά ανά frame — οπότε το
HUD ζει πλέον στη σελίδα του κάδρου και η τράπεζα 2 είναι ΕΠΙΠΕΔΑ 16 KB.

Το κέρδος δεν είναι μόνο απλότητα: οι αρένες άφηναν 397 bytes ελεύθερα αλλά
κομματιασμένα σε οκτώ κουτιά, με επτά από αυτά γεμάτα. Τώρα είναι συνεχόμενα.
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sprites import load_map, load_bin, ROOT
import buttons

TEXT_MAX = 2148                 # = TEXT_MAX του src/uitext.asm (assert εκεί)
B6C_MAX = 5815                  # = B6C_MAX του src/bots.asm (assert στο main.asm)· 256 ως το 92, 1.280 ως το 93, 1.298 ως το 95, 1.554 ως το 109 (τα κελύφη, βήμα 110), 5.138 ως το 110 (οι εννιά φιγούρες, βήμα 111), 5.063 ως το 113 (το αδιαφανές τέλος των κελυφών, βήμα 114), 5.831 ως το 135 (ο επισκέπτης, βήμα 136), 5.767 ως το 151 (το struct_ptr, βήμα 152)
B1C_MAX = 488                   # = B1C_MAX του src/commit.asm (assert στο main.asm), βήμα 94· 152: και το bar_want
B5C_MAX = 248                   # = B5C_MAX του src/bend.asm (assert στο main.asm), βήμα 97· 272 ως το 99

# --- γεωμετρία ------------------------------------------------------------
PAGE2_BASE  = 0x8000                # τράπεζα 2: επίπεδη, πάντα ορατή
WINDOW_BASE = 0x4000                # όπου φαίνονται οι τράπεζες 4-7

BANK_SIZE   = 0x4000
# Ο πίνακας DIST είναι κόμβοι x 128 bytes. Με 96 κόμβους (DESIGN §4.2) πιάνει
# 12 KB από τα 16 της τράπεζας 1, και τα τελευταία 4 KB μένουν — εκεί πάνε τα
# εικονίδια δωματίων m και l, που ελευθερώνουν ισόποσο χώρο ΚΩΔΙΚΑ στην 2.
# Η τράπεζα 1 είναι η ΠΡΟΕΠΙΛΟΓΗ του παραθύρου, οπότε δεν κοστίζει σελίδα σε
# κανέναν εκτός από το πέρασμα αντικειμένων, που έχει την 6 μέσα.
MAX_NODE = 96
BANK1_BASE = WINDOW_BASE + MAX_NODE * 128
BANK1_SIZE = BANK_SIZE - MAX_NODE * 128
# ΚΑΙ Η ΤΡΑΠΕΖΑ 5 (βήμα 85): ο πίνακας NEXTHOP είναι κι αυτός κόμβοι x 128, και
# πάνω του το ευρετήριο αντικειμένων (src/const.asm, OI_END = #73C0). Από το
# #7400 ως το τέλος, 3 KB που δεν χρησιμοποιούσε κανείς: εκεί πάνε οι μηχανές,
# και τα 1.584 bytes τους γίνονται χώρος ΚΩΔΙΚΑ στην τράπεζα 2. Το const.asm
# ελέγχει ότι το ευρετήριο δεν φτάνει ως εδώ.
BANK5_BASE = 0x7400
BANK5_SIZE = 0x8000 - BANK5_BASE


class Fail(SystemExit):
    pass


class Run:
    """Ένα κομμάτι που πρέπει να μείνει ΕΝΙΑΙΟ."""

    def __init__(self, name, size, data=None, align=1, note="", page=0, at=None,
                 phase=None):
        self.name, self.size, self.data = name, size, data
        self.align, self.note = align, note
        self.phase = phase      # το κάτω byte της αρχής του (βήμα 111, οι φιγούρες)
        self.at = at            # καρφωμένη διεύθυνση: ό,τι μένει από κάτω είναι κενό
        self.page = page        # τόσα bytes από την αρχή να μη περνούν σελίδα
        self.addr = None
        self.bin = None
        self.members = []       # [(όνομα sprite, μετατόπιση μέσα στο run)]
        if data is not None and len(data) != size:
            raise Fail(f"{name}: δεδομένα {len(data)} != μέγεθος {size}")

    def __repr__(self):
        return f"<{self.name} {self.size}B @{self.addr and hex(self.addr)}>"


# --- κατανομή -------------------------------------------------------------

def pack_flat(runs, base, size, label):
    """Γραμμική τράπεζα: σειριακά, με σεβασμό στη στοίχιση."""
    a = base
    for r in runs:
        if r.at is not None:
            if a > r.at:
                raise Fail(f"{label}: το {r.name} θέλει το #{r.at:04X} και τα από "
                           f"κάτω φτάνουν ως το #{a:04X}")
            r.gap = r.at - a
            a = r.at
        if r.align > 1:
            a = (a + r.align - 1) & ~(r.align - 1)
        if r.page and (a & 255) + r.page > 256:
            a = (a + 255) & ~255
        if r.phase is not None:
            a += (r.phase - a) & 255
        r.addr = a
        a += r.size
    used = a - base
    if used > size:
        raise Fail(f"{label}: {used} bytes σε χώρο {size} — ξεχειλίζει κατά {used - size}")
    return used





# --- η διάταξη ------------------------------------------------------------

# Τα κελιά της μπάρας του HUD (§9.2), ως γλύφοι Mode 1 μετά τον χαρακτήρα 127.
# Πέντε γραμμές (1-5), όσο το σώμα των κεφαλαίων: η 0, η 6 και η 7 μένουν κενές
# όπως στα γράμματα. Η άδεια μπάρα είναι περίγραμμα, πάνω και κάτω: δίπλα-δίπλα
# τα κελιά της κάνουν ένα κούφιο ορθογώνιο.
def _cell(top, mid, bot):
    return bytes([0, top, mid, mid, mid, bot, 0, 0])


FONT_N = 0x7B - 32                         # οι χαρακτήρες 32-122 (βήμα 101)
HUD_CELLS = (bytes(8)                      # #7B κενό (#80 ως το βήμα 100)
             + _cell(0xF0, 0xF0, 0xF0)     # #7C pen 1 — κόκκινο, λίγο
             + _cell(0x0F, 0x0F, 0x0F)     # #7D pen 2 — πράσινο, γεμάτο
             + _cell(0xFF, 0xFF, 0xFF)     # #7E pen 3 — λευκό
             + _cell(0xFF, 0x00, 0xFF))    # #7F άδειο


# --- οι φιγούρες ΕΞΩ (βήμα 89) ----------------------------------------------
# Οι οκτώ φιγούρες του §7 του SPRITES.md υπάρχουν μόνο ψημένες μέσα στις θέσεις
# του δακτυλίου, αδιαφανείς: 2x8 bytes με το δάπεδο του δακτυλίου από κάτω. Έξω
# δεν υπάρχει δάπεδο — θέλουν μάσκα. Βγαίνουν εδώ, χωρίς να αγγίξουμε τα assets:
# pixel της φιγούρας είναι όποιο διαφέρει από την κενή παραλλαγή της ίδιας θέσης,
# σε ΟΠΟΙΑΔΗΠΟΤΕ από τις 24 θέσεις (και μία είναι λίγη: όπου η φιγούρα πέφτει
# πάνω σε ίδιο χρώμα δακτυλίου δεν διαφέρει). Αν δύο θέσεις διαφωνούν για ένα
# pixel, σκάει — η σιλουέτα είναι μία.
#
# ΜΕ ΣΚΙΑ. Μονόχρωμη σιλουέτα 3x6 πάνω στο έδαφος δεν διαβάζεται: ο κίτρινος
# άποικος χάνεται στη σκόνη. Ένα pixel pen 0 κάτω-δεξιά από κάθε pixel της που
# δεν σκεπάζει άλλο δικό της — η στήλη 3 και η γραμμή 7 του κελιού είναι
# άδειες, οπότε η σκιά χωρά πάντα μέσα στα 4x8.
# Οι πίνακες που διαβάζει ΜΟΝΟ το πέρασμα αντικειμένων, με την 6 μέσα: στην
# τράπεζα 6 από το βήμα 90, με αυτή τη σειρά, σε μία σελίδα.
OB6 = ("struct_ptr", "icon_s_ptr", "icon_m_ptr", "icon_l_ptr",
       "corr_slots", "conn_points", "interior_ofs")

FIG_NAMES = ["colonist", "biologist", "medic", "guard", "carrier", "driller",
             "engineer", "constructor"]                      # φιγούρα 1..8

# Ο ΕΙΣΒΟΛΕΑΣ (βήμα 111): ο άποικος ξαναβαμμένος, κόκκινος με μαύρο πρόσωπο,
# ζώνη και μπότες — όπως τα σήματα των μηχανών (MARK_PEN), χωρίς νέο σχέδιο
# στα assets (η απόφαση του παίκτη). Τα μαύρα pixels είναι ΜΕΣΑ στη σιλουέτα
# (fig_grid το ελέγχει)· όλα τα άλλα του αποίκου γίνονται κόκκινα.
FOE_FIG = "intruder"
FOE_BLACK = {(1, 2), (1, 4), (0, 6), (2, 6)}                 # (x, y) στο 4x8
# Ο ΕΠΙΣΚΕΠΤΗΣ (βήμα 136): ο άποικος ξαναβαμμένος κι αυτός, λευκός (pen 5) με
# γαλάζια ζώνη και μπότες (pen 2) — καμία άλλη φιγούρα δεν είναι λευκή, και
# στην άμμο, στο σκούρο έδαφος, στο δάπεδο του διαδρόμου και του θόλου
# διαβάζεται με τη σκιά του. Χωρίς νέο σχέδιο στα assets, όπως ο εισβολέας.
VIS_FIG = "visitor"
VIS_BODY, VIS_ACCENT = 5, 2
VIS_SKY = {(1, 4), (0, 6), (2, 6)}
FIG_ALL = FIG_NAMES + [FOE_FIG, VIS_FIG]
# ΔΕΚΑ ΦΙΓΟΥΡΕΣ ΑΠΟ ΤΟ ΒΗΜΑ 136: ο επισκέπτης μπαίνει πριν από τον εισβολέα
# στην πρώτη σελίδα, στο 160, και το κομμάτι αρχίζει εκεί — 321 bytes, και οι
# εννιά κωδικοί που υπήρχαν μένουν ίδιοι.
# ΕΝΝΙΑ ΦΙΓΟΥΡΕΣ ΣΕ ΔΥΟ ΣΕΛΙΔΕΣ, ΚΑΙ Ο ΚΩΔΙΚΑΣ ΕΙΝΑΙ Η ΔΙΕΥΘΥΝΣΗ (βήμα 111).
# Ως το 110 οκτώ φιγούρες γέμιζαν μία σελίδα, ο ρόλος έδινε τον αριθμό 1-8 και
# ο renderer έκανε dec / rrca x 3 / ld l,a / ld h,σελίδα. Τώρα ο ρόλος δίνει
# το κάτω byte της ίδιας της φιγούρας, και το bit 0 του λέει τη σελίδα: ld l,a
# / and 1 / add a,σελίδα / ld h,a, 22 T-states αντί για 27. Οι επτά πρώτες στα
# 1, 33, ..., 193 της ΔΕΥΤΕΡΗΣ σελίδας, οι δύο τελευταίες στα 192 και 224 της
# πρώτης: το κομμάτι αρχίζει στο 192 μιας σελίδας (phase) και είναι 289 bytes
# με μία τρύπα του ενός byte, όχι δύο σελίδες. Το 0 μένει «κενή θέση».
FIG_LO = 7                                                   # στη δεύτερη σελίδα
FIG_PHASE = 256 - 32 * (len(FIG_ALL) - FIG_LO)               # 160 (192 ως το βήμα 135)


def fig_code(j):
    """Ο κωδικός της φιγούρας j (0 = colonist) — το L της, και το bit 0 η σελίδα.
    Οι 7 πρώτες στη δεύτερη σελίδα, ο εισβολέας στο 192 και ο επισκέπτης στο
    160 της πρώτης — από το τέλος της προς τα πίσω, ώστε ο εισβολέας να μείνει
    εκεί που ήταν."""
    if j < FIG_LO:
        return 1 + 32 * j
    if j < FIG_LO + 2:
        return 192 + 32 * (j - FIG_LO)
    return 192 - 32 * (j - FIG_LO - 1)


def fig_off(j):
    """Πού αρχίζει η φιγούρα j μέσα στο κομμάτι fig_gfx / fig_ring."""
    c = fig_code(j)
    return c + 256 * (c & 1) - FIG_PHASE


FIG_RUN = 256 - FIG_PHASE + 1 + 32 * FIG_LO                 # 321 (289 ως το βήμα 135)


def _m0_pens(b):
    """Byte Mode 0 -> (αριστερό pen, δεξί pen)."""
    def pen(bits):
        return sum(((b >> bit) & 1) << i for i, bit in enumerate(bits))
    return pen((7, 3, 5, 1)), pen((6, 2, 4, 0))


def _m0_byte(left, right):
    out = 0
    for i, bit in enumerate((7, 3, 5, 1)):
        out |= ((left >> i) & 1) << bit
    for i, bit in enumerate((6, 2, 4, 0)):
        out |= ((right >> i) & 1) << bit
    return out


def fig_grid(smap, blob, name):
    """Η σιλουέτα μιας φιγούρας: 8 γραμμές x 4 pixel, pen ή None (διαφανές)."""
    if name == FOE_FIG:
        grid = fig_grid(smap, blob, "colonist")
        for x, y in FOE_BLACK:
            if grid[y][x] is None:
                raise Fail(f"εισβολέας: το μαύρο ({x}, {y}) είναι έξω από τον άποικο")
        return [[None if grid[y][x] is None else
                 MARK_PEN["K" if (x, y) in FOE_BLACK else "R"] for x in range(4)]
                for y in range(8)]
    if name == VIS_FIG:
        grid = fig_grid(smap, blob, "colonist")
        for x, y in VIS_SKY:
            if grid[y][x] is None:
                raise Fail(f"επισκέπτης: το γαλάζιο ({x}, {y}) είναι έξω από τον άποικο")
        return [[None if grid[y][x] is None else
                 (VIS_ACCENT if (x, y) in VIS_SKY else VIS_BODY) for x in range(4)]
                for y in range(8)]
    grid = [[None] * 4 for _ in range(8)]
    for size in "sml":
        for slot in range(8):
            e, f = smap[f"slot_{size}_{slot}_empty"], smap[f"slot_{size}_{slot}_{name}"]
            for y in range(8):
                for xb in range(2):
                    pe = _m0_pens(blob[e.off + y * 2 + xb])
                    pf = _m0_pens(blob[f.off + y * 2 + xb])
                    for k in range(2):
                        if pf[k] != pe[k]:
                            x = xb * 2 + k
                            if grid[y][x] not in (None, pf[k]):
                                raise Fail(f"φιγούρα {name}: οι θέσεις διαφωνούν "
                                           f"στο pixel ({x}, {y})")
                            grid[y][x] = pf[k]
    if not any(v is not None for row in grid for v in row):
        raise Fail(f"φιγούρα {name}: κενή")
    return grid


def out_figs(smap, blob, shadow=True):
    """10 φιγούρες x 8 γραμμές x (μάσκα, data, μάσκα, data), στη θέση του
    fig_off: FIG_RUN bytes, οι δύο τρύπες μηδέν. Με σκιά για έξω (fig_gfx),
    χωρίς για τον δακτύλιο (fig_ring)."""
    data = bytearray(FIG_RUN)
    for j, name in enumerate(FIG_ALL):
        grid = fig_grid(smap, blob, name)
        sha = [[shadow and grid[y][x] is None and 0 < x and 0 < y
                and grid[y - 1][x - 1] is not None
                for x in range(4)] for y in range(8)]
        fig = bytearray()
        for y in range(8):
            for xb in range(2):
                px = [grid[y][xb * 2 + k] for k in range(2)]
                sh = [sha[y][xb * 2 + k] for k in range(2)]
                mask = (0xAA if px[0] is None and not sh[0] else 0) | \
                       (0x55 if px[1] is None and not sh[1] else 0)
                fig += bytes([mask, _m0_byte(px[0] or 0, px[1] or 0)])
        data[fig_off(j):fig_off(j) + 32] = fig
    return bytes(data)


def slot_empty(smap, blob):
    """slot_empty: οι 24 κενές θέσεις, (μέγεθος*8 + θέση) * 16, αδιαφανείς."""
    return b"".join(blob[smap[f"slot_{z}_{t}_empty"].off:][:16]
                    for z in "sml" for t in range(8))


def check_ring(smap, blob, empty, ring):
    """Η κενή θέση με τη φιγούρα από πάνω ΕΙΝΑΙ η ψημένη παραλλαγή, byte προς
    byte, και για τις 24 x 8. Χωρίς αυτό η αλλαγή του βήματος 89 θα άλλαζε τον
    δακτύλιο κάτω από τα πόδια όλων."""
    for i, (z, t) in enumerate((z, t) for z in "sml" for t in range(8)):
        e = empty[i * 16:(i + 1) * 16]
        for f, name in enumerate(FIG_NAMES):
            want = blob[smap[f"slot_{z}_{t}_{name}"].off:][:16]
            spr = ring[fig_off(f):fig_off(f) + 32]
            got = bytes((e[k] & spr[2 * k]) | spr[2 * k + 1] for k in range(16))
            if got != want:
                raise Fail(f"slot_{z}_{t}_{name}: η κενή + η φιγούρα δεν είναι η "
                           f"ψημένη παραλλαγή")


# ---------------------------------------------------------------------------
# ΟΙ ΑΡΜΟΙ ΔΙΑΔΡΟΜΟΥ-ΔΑΚΤΥΛΙΟΥ (βήμα 96). Ο παίκτης: «οι διάδρομοι να μπαίνουν
# 1 pixel πιο μέσα». Ο διάδρομος ζωγραφίζεται κάτω από τα κελύφη και σταματά
# στο εξωτερικό χείλος του δακτυλίου, όπου ένα λευκό περίγραμμα τον χώριζε από
# το γκρι του δακτυλίου. Ο αρμός ενός θόλου σε μια κατεύθυνση, ζωγραφισμένος
# ΜΕΤΑ το κέλυφος (src/joint.asm), είναι:
#   * το κενό της διαγωνίου: τα pixels του πλακιδίου k-1 (ένα βήμα πριν από το
#     πρώτο, DIAG_K) που φαίνονται — μέσα στο πλαίσιο, όχι κάτω από το κέλυφος
#     ή το πρώτο πλακίδιο. Ως το 95 το έκλεινε η διαγώνια πόρτα.
#   * το ένα pixel: όσα pixels του εξωτερικού περιγράμματος του κελύφους
#     ακουμπούν (4-γειτονικά) ένα γκρι pixel του διαδρόμου που φαίνεται —
#     γίνονται γκρι.
# Υπολογίζεται ΕΔΩ από τα sprites, και χωριστά στην tools/scene.py από τη
# σχεδίαση· το tests/test_object.py συγκρίνει τα δύο.
#
# ΕΝΝΙΑ ΣΧΕΔΙΑ με μάσκα στην τράπεζα 5: 0 n, 1 w, 2 e, 3+2s nw, 4+2s ne. Τα
# νότια είναι τα βόρεια με κάθετο καθρέφτισμα (bit 1 του ob_fl), που δεν θέλει
# πίνακα· το οριζόντιο θέλει το flip_mode0 της τράπεζας 6, που δεν φαίνεται
# όσο η 5 είναι στο παράθυρο — γι' αυτό τα ανατολικά είναι δικά τους. Στο
# build/joint_tab.asm: jt_tab (x σε bytes, γραμμή, σχέδιο | 128 για κάθετο
# καθρέφτισμα, ανά 8 x μέγεθος + κατεύθυνση) και jt_spr (διεύθυνση, w, h).
JNT_DIAG_K = (2, 3, 3)          # = diag_k του src/object.asm, DIAG_K του tools/route.py
JNT_STEP = ((0, -16), (4, -16), (4, 0), (4, 16), (0, 16), (-4, 16), (-4, 0), (-4, -16))
JNT_PM = (0xAA, 0x55)


def _jpx(blob, s, w):
    """Τα αδιαφανή pixels ενός sprite με μάσκα: {(x, γραμμή): χρώμα ως αριστερό}."""
    out = {}
    for y in range(s.h):
        for b in range(w):
            m, d = blob[s.off + (y * w + b) * 2], blob[s.off + (y * w + b) * 2 + 1]
            for p in (0, 1):
                if m & JNT_PM[p] != JNT_PM[p]:
                    v = d & JNT_PM[p]
                    out[(2 * b + p, y)] = v if p == 0 else (v << 1) & 0xFF
    return out


def joint_px(smap, blob, sz, dr):
    """Ο αρμός (μέγεθος, κατεύθυνση): {(x, γραμμή) στο πλαίσιο: χρώμα ως αριστερό}."""
    z = "sml"[sz]
    qw, qh = smap[f"ring_{z}_nw"].w, smap[f"ring_{z}_nw"].h
    shell = set()
    for stem in ("ring", "dome"):
        for (x, y) in _jpx(blob, smap[f"{stem}_{z}_nw"], qw):
            for mx in (x, 4 * qw - 1 - x):
                for my in (y, 2 * qh - 1 - y):
                    shell.add((mx, my))
    spr = smap[("corr_v", "corr_dl", "corr_h", "corr_dr")[dr & 3]]
    tile = _jpx(blob, spr, spr.w)
    sx, sy = JNT_STEP[dr]
    if dr & 1:
        k = JNT_DIAG_K[sz]
        ox, oy = qw - 4 + sx * k, qh - 8 + sy * k
    else:
        t = blob[smap["conn_points"].off:]
        px, py = t[sz * 16 + dr * 2], t[sz * 16 + dr * 2 + 1]
        ox, oy = {0: (px - 1, py - 16), 4: (px - 1, py + 8),
                  2: (px + 2, py - 4), 6: (px - 4, py - 4)}[dr]

    def at(j):
        return {(2 * (ox + sx * j) + x, oy + sy * j + y): v for (x, y), v in tile.items()}
    run = {}
    for j in (2, 1, 0):
        run.update(at(j))
    vis = {p: v for p, v in run.items() if p not in shell}
    gap = {}
    if dr & 1:
        gap = {p: v for p, v in at(-1).items() if p not in shell and p not in run
               and 0 <= p[0] < 4 * qw and 0 <= p[1] < 2 * qh}
    vis.update(gap)
    s = smap["corr_h"]
    grey = _jpx(blob, s, s.w)[(2, 3)]                # το εσωτερικό του corr_h
    n4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
    out = dict(gap)
    for p in shell:
        if any((p[0] + dx, p[1] + dy) not in shell for dx, dy in n4) and \
                any(vis.get((p[0] + dx, p[1] + dy)) == grey for dx, dy in n4):
            out[p] = grey
    return out


# ΤΑ ΣΗΜΑΤΑ ΤΩΝ ΜΗΧΑΝΩΝ (βήμα 100): ένα μικρό σήμα πάνω δεξιά σε μια μηχανή
# που δεν δουλεύει, όπως τα εικονίδια του Planetbase πάνω από ένα χαλασμένο
# εξάρτημα. Δύο, επιλογή του παίκτη: ΧΑΛΑΣΜΕΝΗ (υγεία 0 — και μαραμένο φυτό),
# κόκκινο με λευκό θαυμαστικό· ΠΕΡΙΜΕΝΕΙ να στηθεί (1-127, βήμα 99), κίτρινες
# και μαύρες λωρίδες, του εργοταξίου. ΑΔΙΑΦΑΝΗ, 2 bytes x 6 γραμμές: όλο το
# σήμα είναι μέσα στο sprite της μηχανής, που είναι κι αυτό αδιαφανές, οπότε
# όταν η μηχανή ξαναζωγραφιστεί το σήμα σβήνει χωρίς τίποτα άλλο. Χρώματα έξω
# από τα 7, 11, 12, 14 του εδάφους, που αλλάζουν ανά πλανήτη (§8.6).
MARK_PEN = {"R": 8, "W": 5, "Y": 6, "K": 0}
MARKS = (("RWWR", "RWWR", "RWWR", "RRRR", "RWWR", "RRRR"),     # χαλασμένη
         ("YYKK", "YKKY", "KKYY", "KYYK", "YYKK", "YKKY"))     # περιμένει
MARK_W, MARK_H = 2, 6


def marks():
    out = bytearray()
    for m in MARKS:
        if len(m) != MARK_H or any(len(r) != 2 * MARK_W for r in m):
            raise Fail("σήμα: λάθος διαστάσεις")
        for r in m:
            for k in range(MARK_W):
                out.append(_m0_byte(MARK_PEN[r[2 * k]], MARK_PEN[r[2 * k + 1]]))
    return bytes(out)


def joints(smap, blob):
    """Τα εννιά σχέδια (τράπεζα 5), και jt_tab, jt_spr στο build/joint_tab.asm."""
    spr, tab = [None] * 9, []
    for sz in range(3):
        qh = smap[f"ring_{'sml'[sz]}_nw"].h
        for dr in range(8):
            flip = dr in (3, 4, 5)
            north = (4 - dr) & 7 if flip else dr
            px = joint_px(smap, blob, sz, north)
            if flip and joint_px(smap, blob, sz, dr) != \
                    {(x, 2 * qh - 1 - y): v for (x, y), v in px.items()}:
                raise Fail(f"αρμός {sz} {dr}: δεν είναι ο βόρειος καθρεφτισμένος")
            bx, by = min(x for x, _ in px) // 2, min(y for _, y in px)
            w = max(x for x, _ in px) // 2 - bx + 1
            h = max(y for _, y in px) - by + 1
            img = [[0xFF, 0x00] * w for _ in range(h)]
            for (x, y), v in px.items():
                b, p = x // 2 - bx, x & 1
                img[y - by][2 * b] &= ~JNT_PM[p] & 0xFF
                img[y - by][2 * b + 1] |= v if p == 0 else v >> 1
            sid = (0 if north == 0 else 2 if north == 2 else 1) if not north & 1 \
                else 3 + 2 * sz + (north == 1)
            got = (w, h, b"".join(bytes(r) for r in img))
            if spr[sid] is not None and spr[sid] != got:
                raise Fail(f"αρμός {sz} {dr}: το σχέδιο {sid} αλλάζει με το μέγεθος")
            spr[sid] = got
            tab.append((bx, 2 * qh - by - h if flip else by, sid | (128 if flip else 0)))
    data, desc = b"", []
    for w, h, img in spr:
        desc.append((len(data), w, h))
        data += img
    # Η ΠΡΩΤΗ ΓΡΑΜΜΗ ΤΩΝ ΔΥΤΙΚΩΝ ΚΑΙ ΤΩΝ ΑΝΑΤΟΛΙΚΩΝ είναι ένα pixel: το γκρι
    # στο άκρο του πλαισίου, αριστερό (1) ή δεξί (2). Το src/bend.asm τη
    # ζωγραφίζει μόνη της για τις κοντές στροφές (βήμα 97, jt_pxl, jt_pxr).
    s_ = smap["corr_h"]
    grey = _jpx(blob, s_, s_.w)[(2, 3)]
    for sid, p in ((1, 0), (2, 1)):
        w, h, img = spr[sid]
        want = bytes([0xFF & ~JNT_PM[p], grey if p == 0 else grey >> 1])
        if w != 1 or img[:2] != want:
            raise Fail(f"αρμός {sid}: η πρώτη γραμμή δεν είναι το pixel {want.hex()}")
    out = os.path.join(ROOT, "build")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "joint_tab.asm"), "w", encoding="utf-8") as f:
        f.write("; ΠΑΡΑΓΕΤΑΙ από tools/pack.py (joints) — μην το επεξεργάζεσαι.\n")
        f.write("; jt_tab, ανά 8 x μέγεθος + κατεύθυνση: x σε bytes και γραμμή από το\n")
        f.write("; πάνω-αριστερά του πλαισίου, σχέδιο | 128 = κάθετο καθρέφτισμα.\n")
        f.write("jt_tab:\n")
        for sz in range(3):
            f.write("        db      " + ", ".join(f"{x},{y},{k}" for x, y, k in
                                                   tab[8 * sz:8 * sz + 8])
                    + f"   ; {'sml'[sz]}: n ne e se s sw w nw\n")
        f.write("; Η πρώτη γραμμή του δυτικού και του ανατολικού: ένα pixel, μάσκα και\n")
        f.write("; δεδομένα (src/bend.asm· από το βήμα 129 στο b6code, όπου δεν φαίνεται\n")
        f.write("; η τράπεζα 5 — γι' αυτό τα bytes και όχι η διεύθυνσή τους).\n")
        for nm, sid in (("JT_PXL", 1), ("JT_PXR", 2)):
            img = spr[sid][2]
            f.write(f"{nm}_M equ #{img[0]:02X}\n{nm}_D equ #{img[1]:02X}\n")
        f.write("; jt_spr, ανά σχέδιο: διεύθυνση στην τράπεζα 5, πλάτος, ύψος.\n")
        f.write("jt_spr:\n")
        for i, (o, w, h) in enumerate(desc):
            f.write(f"        dw      G_joints + {o}\n        db      {w}, {h}\n")
    return data


def corners():
    """ΟΙ ΓΩΝΙΕΣ ΤΩΝ ΔΙΑΔΡΟΜΩΝ (βήμα 129), από το tools/corner.py: οι θέσεις και
    οι διαστάσεις στο build/corner_tab.asm (src/corner.asm, b6code), τα σχέδια
    στο build/corner_spr.asm (η δέσμευση b5code της τράπεζας 5, src/main.asm)."""
    import corner
    corner.check_bands()
    lines = corner.asm_lines()
    lines.append("; cn_pos: (x bytes, γραμμή) του μπαλώματος από το ΠΡΩΤΟ αξονικό πλακίδιο")
    lines.append("; (corner.first), οριζόντια και μετά κάθετα, ανά προσανατολισμό (1")
    lines.append("; δυτικά, 2 βόρεια).")
    lines.append("cn_pos:")
    for kind in ("h", "v"):
        pos = {}
        for d0 in (1, 3, 5, 7):
            x, y, o = corner.place(kind, d0)
            fx, fy = corner.first(kind, d0)
            pos[o] = (x - fx, y - fy)
        lines.append("        db      " + ", ".join(f"{pos[o][0]},{pos[o][1]}" for o in range(4))
                     + f"   ; {kind}: να, νδ, βα, βδ")
    out = os.path.join(ROOT, "build")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "corner_tab.asm"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(out, "corner_spr.asm"), "w", encoding="utf-8") as f:
        f.write("\n".join(corner.spr_lines()) + "\n")


def mode1_font(m0):
    """Η γραμματοσειρά 4x8 του Mode 0 (2 bytes ανά γραμμή) σε Mode 1 (1 byte).

    Στο Mode 0 το αριστερό pixel ενός byte είναι τα bits 7,5,3,1 και το δεξί
    τα 6,4,2,0· στο Mode 1 το pixel i (0-3) είναι τα bits 7-i και 3-i, και
    pen 3 σημαίνει και τα δύο. Μελάνι = οποιοδήποτε pen εκτός από το 0."""
    out = bytearray()
    for k in range(0, len(m0), 2):
        px = [m0[k] & 0xAA, m0[k] & 0x55, m0[k + 1] & 0xAA, m0[k + 1] & 0x55]
        out.append(sum(0x88 >> i for i in range(4) if px[i]))
    return bytes(out)


def build_runs(smap, blob):
    def spr(name):
        s = smap.get(name)
        if s is None:
            raise Fail(f"λείπει sprite: {name}")
        return Run(name, s.size, blob[s.off:s.off + s.size])

    def group(name, names):
        """Ενιαίο κομμάτι από διαδοχικά sprites — για ό,τι δεικτοδοτείται με
        πολλαπλασιασμό και ΠΡΕΠΕΙ να είναι συνεχόμενο."""
        data, members = b"", []
        for n in names:
            s = smap[n]
            members.append((n, len(data)))
            data += blob[s.off:s.off + s.size]
        r = Run(name, len(data), data)
        r.members = members
        return r

    TERRAIN = ["ground", "dust", "rock", "mountain", "water",
               "deepwater", "crater", "foundation"]
    ROOMS = ["empty", "control", "quarters", "canteen", "oxygen",
             "greenhouse", "storage", "airlock", "factory", "lab",
             "medbay", "lounge"]
    # Δώδεκα, όχι δέκα: η παράδοση τέχνης πρόσθεσε `beds` και `medstore` στο
    # ιατρείο (θέσεις 10 και 11). Οι δέκα πρώτοι δείκτες δεν άλλαξαν.
    MACH = ["oxygen", "iron", "bioplastic", "weapons", "processors",
            "robots", "food", "spares", "medical", "vitromeat",
            "beds", "medstore"]
    PLANTS = ["peas", "rice", "potatoes", "wheat", "maize", "tomatoes",
              "lettuce", "onions", "radishes", "mushrooms", "medicinal", "tree"]
    DIRS = ["n", "ne", "e", "se", "s", "sw", "w", "nw"]
    # ΜΟΝΟ ΤΟ ΜΕΓΑΛΟ ΜΕΓΕΘΟΣ ΤΩΝ ΤΕΣΣΑΡΩΝ ΕΝΕΡΓΕΙΑΚΩΝ (βήμα 151): ο κατάλογος
    # δίνει μόνο αυτό (bds_sz, src/build.asm), και τα s και m, 4 x 640 bytes της
    # τράπεζας 7, δεν τα ζωγράφισε ποτέ το παιχνίδι — μόνο οι δοκιμές.
    STRUCTS = ([f"{k}_l" for k in ("solar", "turbine", "collector", "extractor")]
               + ["mine", "airlock", "pad", "ship"])

    arena, bank1, bank5, bank6, bank7 = [], [], [], [], []
    ptr = {}            # όνομα πίνακα -> λίστα ονομάτων run, για 2ο πέρασμα

    # --- έδαφος: συνεχόμενο ΑΝΑ ΚΛΑΣΗ μόνο (tile_ptr[class] + variant*64) ---
    for cls in TERRAIN:
        names = sorted([n for n in smap if n.startswith(f"tile_{cls}_")],
                       key=lambda n: int(n.rsplit("_", 1)[1]))
        arena.append(group(f"tile_{cls}", names))
    arena.append(group("ore_overlay", sorted(n for n in smap if n.startswith("ore_overlay"))))
    ptr["tile_ptr"] = [f"tile_{c}" for c in TERRAIN]

    # --- εικονίδια δωματίων -------------------------------------------------
    # Το SPRITES.md §6 λέει `room_icons_l + type*ICON_L_SZ`, που απαιτεί 2.400
    # bytes ΣΥΝΕΧΟΜΕΝΑ — δεν χωράνε σε αρένα 1.648. Με πίνακα δεικτών κάθε
    # εικονίδιο μπαίνει όπου βρεθεί χώρος, και η αναζήτηση είναι ΚΑΙ πιο
    # γρήγορη: το *200 και το *72 δεν είναι ολισθήσεις.
    # Τα m και l πάνε στην ΤΡΑΠΕΖΑ 1, πάνω από τον πίνακα DIST· τα s στην
    # ΤΡΑΠΕΖΑ 5 από το βήμα 87, πάνω από τις μηχανές — 864 bytes κώδικα για την
    # τράπεζα 2, όπως οι μηχανές στο 85. Το ob_icon (src/object.asm) διαλέγει
    # τράπεζα κατά μέγεθος. Οι πίνακες δεικτών διαβάζονται όσο το παράθυρο
    # έχει την 6 μέσα: ως το βήμα 89 στη 2, από το 90 στην ίδια την 6 (OB6).
    # ΒΗΜΑ 151: τα s στην ΤΡΑΠΕΖΑ 7, όπου πήγαν και οι μηχανές, για να μείνει η
    # 5 στο NEXTHOP των 48 δομών. Και ΧΩΡΙΣ τα τρία του airlock (400 bytes): το
    # airlock είναι δομή από το βήμα 86, κανένας θόλος δεν έχει πια το δωμάτιο
    # 7 (rm_list, src/rooms.asm), και ο δείκτης του δείχνει το εικονίδιο του
    # άδειου, ώστε οι δείκτες των άλλων να μένουν όπου ήταν.
    for size in ("s", "m", "l"):
        names = [f"icon_{size}_{r}" for r in ROOMS if r != "airlock"]
        dest = bank7 if size == "s" else bank1
        for n in names:
            dest.append(spr(n))
        ptr[f"icon_{size}_ptr"] = [f"icon_{size}_{'empty' if r == 'airlock' else r}"
                                   for r in ROOMS]
    # ΚΑΙ ΚΩΔΙΚΑΣ ΠΑΝΩ ΑΠΟ ΤΑ ΕΙΚΟΝΙΔΙΑ (βήμα 94): η τράπεζα 1 είναι η
    # προεπιλογή του παραθύρου, οπότε ό,τι τρέχει μόνο με αυτήν μέσα — το UI,
    # όταν ό,τι καλεί γυρίζει με την 1 — μπορεί να ζει εδώ. Το γράφει το
    # src/main.asm, και η BANK1.BIN του δίσκου βγαίνει από εκεί (bank1c.bin).
    bank1.append(Run("b1code", B1C_MAX, None, at=BANK1_BASE + BANK1_SIZE - B1C_MAX,
                     note="ΔΕΣΜΕΥΣΗ — κώδικας της τοποθέτησης και της μπάρας (src/commit.asm, src/bar1.asm)"))

    # --- μηχανές: *132, ίδιο σκεπτικό ---------------------------------------
    # ΣΤΗΝ ΤΡΑΠΕΖΑ 5 από το βήμα 85, πάνω από το ευρετήριο. Τις ζωγραφίζει μόνο
    # το πέρασμα αντικειμένων (om_prep, src/object.asm), που σελιδοποιεί ήδη
    # την 7 για τα φυτά του θερμοκηπίου στις ίδιες υποδοχές: τώρα σελιδοποιεί
    # την 5 για τις μηχανές.
    # ΚΑΙ ΣΤΗΝ ΤΡΑΠΕΖΑ 7 από το βήμα 151, δίπλα στα φυτά που μπαίνουν στις ίδιες
    # υποδοχές: το om_prep σελιδοποιεί πια την 7 και για τα δύο, και η 5 κρατά
    # τον χώρο για το NEXTHOP των 48 δομών.
    for m in MACH:
        bank7.append(spr(f"mach_{m}"))
    ptr["mach_ptr"] = [f"mach_{m}" for m in MACH]
    # Ο ΠΙΝΑΚΑΣ ΔΕΙΚΤΩΝ ΜΑΖΙ ΤΟΥΣ από το βήμα 90: το ob_mach_one τον διαβάζει
    # ΑΦΟΥ το om_prep σελιδοποιήσει την 5 (τα φυτά έχουν τον δικό τους στην 7).
    bank7.append(Run("mach_ptr", len(MACH) * 2, bytes(len(MACH) * 2),
                     note="παράγεται", page=len(MACH) * 2))
    # ΟΙ ΑΡΜΟΙ (βήμα 96): ο διάδρομος μπαίνει ΕΝΑ pixel στον δακτύλιο. Τα
    # pixels του λευκού περιγράμματος δίπλα στο γκρι του διαδρόμου γίνονται
    # γκρι, πάνω από το κέλυφος (src/joint.asm). Τα ζωγραφίζει το ob_put_in
    # με την 5 μέσα, όπως τις μηχανές ως το βήμα 150.
    jdata = joints(smap, blob)
    corners()
    bank5.append(Run("joints", len(jdata), jdata,
                     note="παράγεται: οι αρμοί v, h και d ανά μέγεθος"))
    # ΤΑ ΣΗΜΑΤΑ ΤΩΝ ΜΗΧΑΝΩΝ (βήμα 100): στην 5, όπου ζουν οι μηχανές· τα
    # ζωγραφίζει το ob_mach_one με την 5 μέσα, και για τα φυτά. Πήραν 24 bytes
    # από τη δέσμευση του b5code, που είχε 43 ελεύθερα.
    mdata = marks()
    # Στην 7 από το βήμα 151, με τις μηχανές.
    bank7.append(Run("marks", len(mdata), mdata,
                     note="παράγεται: χαλασμένη, περιμένει (βήμα 100)", page=len(mdata)))
    # ΚΑΙ ΚΩΔΙΚΑΣ ΠΑΝΩ ΤΟΥΣ (βήμα 97): οι κοντές στροφές (src/bend.asm), με
    # τις σημαίες τους ανά θόλο. Τρέχει με την 5 στο παράθυρο, μέσα από το
    # jt_b5 (src/object.asm), και ζωγραφίζει με το ob_put τα σχέδια των αρμών
    # που βλέπει δίπλα του. Το γράφει το src/main.asm, και η BANK5.BIN του
    # δίσκου βγαίνει από εκεί (bank5c.bin), όπως η BANK1.BIN του b1code.
    # Ο ΠΙΝΑΚΑΣ ΤΩΝ ΔΙΑΔΡΟΜΩΝ ΑΠΟ ΤΗΝ ΤΡΑΠΕΖΑ 6 (βήμα 154, η απόφαση του
    # χρήστη): 96 εγγραφές των 4 bytes, χωρίς το byte της κατάστασης (άδεια =
    # C_A 254). Η 6 δεν είχε τα 128 bytes του πίνακα των 48 δομών. Στο #7800,
    # όπου το #7800 / 2 είναι αρχή σελίδας: το id x 2 χωρά σε ένα byte, και το
    # add hl,hl δίνει τη διεύθυνση (src/object.asm, ob_corr). Πάνω από τις 112
    # γραμμές του NEXTHOP του βήματος 155, που τελειώνουν στο #77FF.
    # ΚΑΙ ΜΙΑ ΕΓΓΡΑΦΗ ΑΚΟΜΗ, ΠΑΝΤΑ ΑΔΕΙΑ: η κατεδάφιση κοιτάζει την επόμενη
    # εγγραφή για συνέχεια (dmk_lp, src/dm_ovl.asm), και μετά την 95 θα
    # διάβαζε ό,τι τύχαινε από πάνω.
    bank5.append(Run("corr_tbl", 97 * 4, None, at=0x7800,
                     note="ΔΕΣΜΕΥΣΗ — 96 διάδρομοι x 4 και μία άδεια (βήμα 154)"))
    bank5.append(Run("b5code", B5C_MAX, None, at=BANK5_BASE + BANK5_SIZE - B5C_MAX,
                     note="ΔΕΣΜΕΥΣΗ — οι κοντές στροφές (src/bend.asm)"))

    # --- διάδρομοι και συνδέσεις: στην τράπεζα 6 από το βήμα 89 (πιο κάτω) ---
    # Η ΓΡΑΜΜΑΤΟΣΕΙΡΑ ΕΦΥΓΕ ΑΠΟ ΕΔΩ ΣΤΟ ΒΗΜΑ 33 — δες την τράπεζα 7 πιο κάτω.

    # --- πίνακες που έρχονται έτοιμοι από τα assets -------------------------
    # Το tile_base ΔΕΝ περνάει: κρατά μετατοπίσεις από την αρχή ενός ενιαίου
    # μπλοκ που πλέον δεν υπάρχει. Το ξαναφτιάχνουμε ως tile_ptr.
    # ΟΣΟΙ ΔΙΑΒΑΖΟΝΤΑΙ ΜΕ ΤΟ ΚΑΤΩ BYTE ΔΕΝ ΠΕΡΝΟΥΝ ΣΕΛΙΔΑ (τα asserts στα
    # src/rooms.asm, needs.asm, econ.asm, jobs.asm, tiles.asm, entity.asm).
    # Ως το βήμα 86 έπεφταν σωστά από τύχη· στο 87 τα εικονίδια s έφυγαν από
    # μπροστά τους και το machine_rules έπεσε πάνω στο #9200. Το page= το λέει
    # ρητά: ο packer πηδά στην επόμενη σελίδα μόνο όταν χρειάζεται.
    flat = {"corr_fill", "plant_class", "machine_count", "machine_rules",
            "room_machines", "tile_variants"}
    for n in ("corr_fill", "plant_class", "machine_count",
              "machine_slots", "machine_rules", "room_machines",
              "tile_variants", "planet_pens", "struct_dims", "palette_fw"):
        r = spr(n)
        if n == "struct_dims":
            # Τα μεγέθη 0 και 1 των τεσσάρων ενεργειακών ΜΗΔΕΝ (βήμα 151), όπως η
            # τέταρτη θέση: τα sprites τους έφυγαν από την τράπεζα 7, και μια δομή
            # τέτοια δεν ζωγραφίζεται (ob_struct, w = 0) αντί να ζωγραφίσει από
            # το &0000. Ο κατάλογος δίνει μόνο το 2 (bds_sz, src/build.asm).
            d = bytearray(r.data)
            for k in range(4):
                d[k * 8:k * 8 + 4] = bytes(4)
            r = Run(n, len(d), bytes(d))
        if n in flat:
            r.page = r.size
        arena.append(r)

    # struct_ptr[kind]: ΕΝΑ sprite ανά είδος από το βήμα 152. Το ορυχείο, ο
    # αεροθάλαμος, η πλατφόρμα και το σκάφος υπάρχουν σε ΕΝΑ μέγεθος — το 0 —
    # και από το βήμα 151 τα ενεργειακά μόνο στο 2 (l): το παιχνίδι δεν φτιάχνει
    # άλλο (bds_sz). Ποιο μέγεθος υπάρχει το λέει το struct_dims, που μένει
    # τέσσερα ανά είδος με μηδέν στα άλλα, και το ob_struct σταματά εκεί πριν
    # διαβάσει δείκτη (src/object.asm). Ως το 151 ο πίνακας είχε κι αυτός
    # τέσσερις θέσεις ανά είδος, 64 bytes: τα 48 πήγαν στο b6code.
    ptr["struct_ptr"] = ([f"{k}_l" for k in ("solar", "turbine", "collector", "extractor")]
                         + ["mine", "airlock", "pad", "ship"])

    # --- παραγόμενοι πίνακες δεικτών ---------------------------------------
    # Οσοι διαβάζονται μόνο από το πέρασμα αντικειμένων ΕΦΥΓΑΝ από εδώ (βήμα
    # 90): στην τράπεζα 6 ή στην 5, πιο κάτω (OB6, και το mach_ptr).
    for tab, names in ptr.items():
        if tab != "plant_ptr" and tab not in OB6 and tab != "mach_ptr":
            arena.append(Run(tab, len(names) * 2, bytes(len(names) * 2),
                             note="παράγεται",
                             page=len(names) * 2 if tab == "tile_ptr" else 0))

    # Το ui_cursor (256 bytes, «δεν έχει παραδοθεί») ΕΦΥΓΕ στο βήμα 33: ο
    # κέρσορας είναι το πλαίσιο του φαντάσματος (gh_box) από το βήμα 6b, κανείς
    # δεν διάβασε ποτέ αυτά τα bytes, και κάθονταν πριν από τρεις πίνακες
    # ευθυγραμμισμένους σε σελίδα — άρα κόστιζαν ακριβώς 256 bytes κώδικα.

    # --- συνταγές μηχανών: στατικά δεδομένα, ένα πέρασμα πίνακα (§6.5) ---
    import econ
    rec = bytearray()
    for r in econ.RECIPE:
        rec += bytes(x & 0xFF for x in r)
    arena.append(Run("recipes", len(rec), bytes(rec), note="παράγεται από econ.py"))
    # «θέλει χειριστή;» ως πίνακας: ο πίνακας εργασιών το ρωτά για κάθε
    # μηχανή κάθε θόλου, και ο πολλαπλασιασμός x10 για τη συνταγή ήταν το
    # ακριβότερο κομμάτι της δημοσίευσης.
    arena.append(Run("mach_op", len(econ.RECIPE),
                     bytes(1 if r[9] & econ.MF_OPERATOR else 0
                           for r in econ.RECIPE), note="παράγεται από econ.py",
                     page=len(econ.RECIPE)))

    # Η οικονομία και ο πίνακας εργασιών ΕΚΤΟΣ παραθύρου, για δύο λόγους:
    # ο πίνακας εργασιών διαβάζει το DIST (τράπεζα 1) ενώ αναθέτει, και τα
    # αποθέματα τα διαβάζει το HUD σε κάθε frame. Ο,τι διαβάζεται μαζί με
    # σελιδοποιημένο πίνακα δεν μπορεί να ζει στο παράθυρο — το ίδιο μάθημα
    # με τον πάγκο της BFS.
    arena.append(Run("econ_state", econ.ECON_BYTES, None,
                     note="ΔΕΣΜΕΥΣΗ — αποθέματα και ροές",
                     page=econ.ECON_BYTES))  # src/stock.asm: EC_STOCK με το κάτω byte
    arena.append(Run("job_tbl", 32 * 5, None, note="ΔΕΣΜΕΥΣΗ — 32 εργασίες"))
    arena.append(Run("room_n", 12, None, note="ΔΕΣΜΕΥΣΗ — θόλοι ανά είδος δωματίου",
                     page=12 + 12 * 8))     # μαζί με το room_list

    arena.append(Run("room_list", 12 * 8, None, note="ΔΕΣΜΕΥΣΗ — ως 8 ο καθένας"))
    # Η μνήμη εργασίας του src/crew.asm (βήμα 91): οκτώ εγγραφές [d, t, -] —
    # πρώτα οι ζωντανοί ανά ρόλο, μετά πόσο λείπει ο καθένας· 5-7 ρομπότ που
    # μετριούνται και μένουν — και ποιος κέρδισε την επιλογή. Στο κενό πριν από
    # το rt_nodes, μέσα στο μπλοκ που σώζεται: δεν πειράζει, το cw_count τα
    # ξαναγράφει πριν από κάθε πλοίο. Σε μία σελίδα: δείκτες με το κάτω byte.
    arena.append(Run("crew", 33, None, note="ΔΕΣΜΕΥΣΗ — εργασία του src/crew.asm",
                     page=33))

    # --- ο γράφος κόμβων και ο πάγκος της BFS -------------------------------
    # Εδώ, και όχι στην τράπεζα 6, για έναν λόγο που δεν συγχωρεί: η BFS γράφει
    # τις γραμμές της στις τράπεζες 1 και 5, άρα το παράθυρο &4000 αλλάζει μέσα
    # στη ρουτίνα. Ο,τι διαβάζει ή γράφει η BFS πρέπει να είναι ΕΚΤΟΣ παραθύρου.
    # Η τράπεζα 2 είναι πάντα ορατή — και έχει χώρο από το βήμα 5.
    arena.append(Run("rt_nodes", 256, None, align=256,
                     note="ΔΕΣΜΕΥΣΗ — node_deg[0..127] + rt_queue[128..255]"))
    arena.append(Run("rt_row", 256, None, align=256,
                     note="ΔΕΣΜΕΥΣΗ — rt_dist[0..127] + rt_next[128..255]"))
    arena.append(Run("node_adj", 1024, None, align=256,
                     note="ΔΕΣΜΕΥΣΗ — 128 κόμβοι x 8 γείτονες"))
    # Η κρυφή μνήμη του HUD: ένας κωδικός ανά κελί για τις σειρές 0-2 (§9.2).
    # Χωρίς αυτήν κάθε επανασχεδίαση ξαναγράφει και τα 120 κελιά — 2,55 frames
    # μετρημένα — ενώ αλλάζουν τρία ή τέσσερα.
    #
    # ΤΕΛΕΥΤΑΙΑ ΕΠΙΤΗΔΕΣ, μετά τον γράφο: το αρχείο σωσίματος γράφει τα 2 KB
    # ΑΜΕΣΩΣ ΚΑΤΩ από αυτήν ως ένα κομμάτι (§11, SV_STATE στο src/save.asm), και
    # ένα assert εκεί ελέγχει ότι το econ_state χωρά μέσα. Η κρυφή μνήμη δεν
    # σώζεται — ξαναχτίζεται μόλις αλλάξει κελί.
    arena.append(Run("hud_shadow", 120, None,
                     note="ΔΕΣΜΕΥΣΗ — ένας κωδικός ανά κελί HUD"))

    # --- τράπεζα 6 ----------------------------------------------------------
    bank6.append(Run("flip_mode0", 256, blob[smap["flip_mode0"].off:
                                             smap["flip_mode0"].off + 256],
                     align=256, note="ΠΡΕΠΕΙ σε σελίδα"))
    # ΤΑ ΚΕΛΥΦΗ ΜΟΝΟ ΜΕ ΤΑ ΔΙΑΣΤΗΜΑΤΑ ΤΟΥΣ (βήμα 110, shell() πιο κάτω): 7.424
    # bytes -> 3.840. Ο,τι ελευθερώνεται το παίρνει ο κώδικας του τροχού.
    # Σε αυτή τη σειρά καμία κεφαλίδα δεν περνά σελίδα (page) και τα έξι
    # τελείωναν ακριβώς στο #5000, όπου οι φιγούρες θέλουν αρχή σελίδας:
    # με τη σειρά των μεγεθών ο l θα πήγαινε 16 bytes πιο πέρα, και οι
    # φιγούρες μία σελίδα. Από το βήμα 114, χωρίς τις μάσκες του αδιαφανούς
    # τέλους των θόλων, τελειώνουν στο #4CE0: 32 bytes ως τη σελίδα των
    # φιγουρών, και όλα από πάνω τρεις σελίδες πιο κάτω — 768 bytes για το
    # b6code (B6C_MAX).
    for name in ("dome_s", "dome_l", "dome_m", "ring_s", "ring_m", "ring_l"):
        bank6.append(shell(name + "_nw", smap, blob))
    # ΟΙ ΦΙΓΟΥΡΕΣ, ΧΩΡΙΣΤΑ ΑΠΟ ΤΙΣ ΘΕΣΕΙΣ (βήμα 89). Ως τότε εδώ καθόταν το
    # corr_slot_gfx, 3.456 bytes: κάθε φιγούρα ψημένη σε κάθε μία από τις 24
    # θέσεις δακτυλίου, αδιαφανής. Τώρα είναι η κενή θέση (384) και από πάνω
    # η φιγούρα με μάσκα (256) — το ίδιο pixel προς pixel (check_ring) — και
    # οι ίδιες φιγούρες με σκιά για έξω, και η λίστα τους. Στη θέση που
    # μένει μπαίνουν ο διάδρομος και οι πόρτες, από την τράπεζα 2: τις
    # ζωγραφίζει μόνο το πέρασμα αντικειμένων, με την 6 ήδη στο παράθυρο, και
    # τα 896 bytes τους γίνονται χώρος ΚΩΔΙΚΑ εκεί.
    #
    # Η λίστα και οι τρεις ομάδες φιγούρων ΣΕ ΣΕΛΙΔΑ: τέσσερις στήλες των 64
    # στο L (src/figure.asm), και φιγούρα * 32 στο L. Πρώτες, γιατί το #5E00
    # είναι ήδη αρχή σελίδας.
    empty, ring = slot_empty(smap, blob), out_figs(smap, blob, shadow=False)
    check_ring(smap, blob, empty, ring)
    # ΣΕ ΑΥΤΗ ΤΗ ΣΕΙΡΑ ΑΠΟ ΤΟ ΒΗΜΑ 111. Οι δύο ομάδες φιγούρων αρχίζουν στο 192
    # μιας σελίδας (FIG_PHASE) και είναι 289 bytes η καθεμία· ό,τι μπαίνει πριν
    # και ανάμεσα τις φέρνει εκεί με 9 bytes κενά όλα κι όλα — η σειρά βγήκε
    # από αναζήτηση στις 3^12 μοιρασιές, και κανένας δεν τη διαβάζει: όλοι οι
    # πίνακες βρίσκονται με το όνομά τους (G_*).
    def ob6(n):
        if n in ptr:
            r = Run(n, len(ptr[n]) * 2, bytes(len(ptr[n]) * 2), note="παράγεται")
        else:
            r = spr(n)
        r.page = r.size
        return r

    bank6.append(Run("fig_list", 256, None, align=256,
                     note="ΔΕΣΜΕΥΣΗ — 64 φιγούρες έξω: ux, uy, φιγούρα, πράκτορας"))
    bank6.append(Run("slot_empty", len(empty), empty,
                     note="οι 24 κενές θέσεις δακτυλίου, αδιαφανείς"))
    # ΑΠΟ ΤΟ ΒΗΜΑ 136 οι δύο ομάδες αρχίζουν στο 160 (δέκα φιγούρες, 321 bytes η
    # καθεμία): ανάμεσα στις αρχές τους 512, άρα 191 bytes πινάκων ανάμεσα, και
    # 32 πριν από την πρώτη. Τα 64 του struct_ptr πήγαν στο τέλος, κάτω από το
    # b6code, που μίκρυνε κατά τα 64 των δύο νέων φιγούρων. Κενά 8 + 1. (Από το
    # βήμα 152 το struct_ptr είναι 16, και το b6code ξαναπήρε τα 48.)
    bank6 += [spr("corr_dr"), spr("corr_dl"), ob6("icon_m_ptr")]
    bank6.append(Run("fig_gfx", FIG_RUN, out_figs(smap, blob), phase=FIG_PHASE,
                     note="παράγεται από τα slot_*: οι 10 φιγούρες με μάσκα και σκιά (fig_code)"))
    bank6 += [spr("corr_h"), ob6("corr_slots"), ob6("conn_points"),
              ob6("icon_s_ptr"), ob6("interior_ofs")]
    bank6.append(Run("fig_ring", FIG_RUN, ring, phase=FIG_PHASE,
                     note="παράγεται από τα slot_*: οι 10 φιγούρες με μάσκα (fig_code)"))
    bank6 += [spr("corr_v"), ob6("icon_l_ptr"), ob6("struct_ptr")]
    # ΟΙ ΠΟΡΤΕΣ (conn_{dir}, 8 x 32) ΕΦΥΓΑΝ ΣΤΟ ΒΗΜΑ 96: ο διάδρομος σταματά στο
    # εξωτερικό χείλος του δακτυλίου (ο παίκτης), και ό,τι ανοίγει τον
    # δακτύλιο δεν ζωγραφίζεται πια. Τα 256 bytes τους πήγαν στο b6code.
    # ΟΙ ΠΙΝΑΚΕΣ ΤΟΥ ΠΕΡΑΣΜΑΤΟΣ ΑΝΤΙΚΕΙΜΕΝΩΝ (OB6, ob6), ΑΠΟ ΤΗΝ ΤΡΑΠΕΖΑ 2 (βήμα
    # 90). Τους διαβάζει μόνο το src/object.asm, και πάντα με την 6 στο
    # παράθυρο: ο δείκτης ενός εικονιδίου ή μιας δομής ΠΡΙΝ σελιδοποιηθεί η
    # τράπεζα του sprite, οι θέσεις και οι πόρτες με τον θόλο. Τα 238 bytes τους
    # έγιναν χώρος ΚΩΔΙΚΑ στη 2, για τις στολές. Ο καθένας σε ΜΙΑ σελίδα,
    # κανένας πάνω σε όριο: το ob_addu πληρώνει το inc h όταν ένας πίνακας
    # περνά σελίδα (βήμα 89, ob_index).
    assert sorted(OB6) == sorted(r.name for r in bank6 if r.name in OB6)
    # --- πίνακες οντοτήτων: δομή-από-πίνακες, σελιδοποιημένη (§6.1) ---
    # Το agent_fields ΠΡΕΠΕΙ σε σελίδα: η ανάγνωση πεδίου είναι `ld h,σελίδα /
    # ld l,id`, και χωρίς στοίχιση δεν υπάρχει τέτοια ανάγνωση. ΚΑΙ ΣΤΟ #6C00:
    # το σώσιμο γράφει από εκεί (src/save.asm), και οι δοκιμές το διαβάζουν.
    # Ο,τι μένει από κάτω (βήμα 89) είναι ελεύθερο.
    # Ο ΚΩΔΙΚΑΣ ΤΟΥ ΤΡΟΧΟΥ (βήμα 92), αμέσως κάτω από τους πράκτορες: ο
    # τροχός έχει την 6 στο παράθυρο από την αρχή ως το τέλος του (src/wheel.asm),
    # οπότε ό,τι τρέχει μόνο μέσα του μπορεί να ζει εδώ. Το γράφει το
    # src/main.asm, και ο φορτωτής το ρίχνει πάνω στη δέσμευση (B6CODE.BIN).
    bank6.append(Run("b6code", B6C_MAX, None, at=0x6C00 - B6C_MAX,
                     note="ΔΕΣΜΕΥΣΗ — κώδικας του τροχού (src/bots.asm)"))
    bank6.append(Run("agent_fields", 2048, None, align=256, at=0x6C00,
                     note="ΔΕΣΜΕΥΣΗ — 16 πεδία x 128, ΠΡΕΠΕΙ σε σελίδα"))
    # ΘΟΛΟΙ, ΔΟΜΕΣ, ΚΑΤΟΧΗ (βήμα 154). Ο πίνακας των δομών για 48: 384 bytes
    # στο #7A80, αμέσως μετά τους θόλους (το mt_scan περνά από τον έναν στον
    # άλλο). Η εγγραφή βγαίνει από τον κόμβο με add a,a / add a,a / add a,64 /
    # ld l,a / ld h,#3D / add hl,hl (src/const.asm, STB_H, STB_C): το #7A80 / 2
    # είναι #3D40, και 64 + 4 x 47 + 3 χωρά σε ένα byte. Και κάθε σελίδα του
    # τελειώνει σε όριο εγγραφής, 16 δομές στη μία και 32 στην άλλη: όποιος
    # περπατά με add στο L σταματά στο κρατούμενο (su_lock, src/suit.asm). Ως το
    # βήμα 153: node_occ στο #7400, θόλοι στο #7500, δομές μία σελίδα στο
    # #7B00, και οι διάδρομοι μετά — που πήγαν στην τράπεζα 5.
    # 24 bytes ο θόλος, όχι 16: το machine_count των assets δίνει 8 υποδοχές
    # στον μεγάλο θόλο, και το §6.1 του έδινε machines[4] health[4].
    bank6.append(Run("dome_tbl", 64 * 24, None, at=0x7480, note="ΔΕΣΜΕΥΣΗ — 64 θόλοι x 24"))
    bank6.append(Run("struct_tbl", 48 * 8, None,
                     note="ΔΕΣΜΕΥΣΗ — 48 δομές (32 ως το βήμα 155)"))
    bank6.append(Run("node_occ", 256, None, align=256,
                     note="ΔΕΣΜΕΥΣΗ — μάσκες θέσεων[0..127], 128 ελεύθερα"))
    # Το seed του κόσμου. Το γράφει η ΓΕΝΝΗΤΡΙΑ, που είναι ξεχωριστό φόρτωμα και
    # σβήνεται μετά· χωρίς αυτά τα τέσσερα bytes το παιχνίδι δεν ξέρει από ποιο
    # seed βγήκε ο κόσμος του, και το αρχείο σωσίματος (§11) δεν έχει τι να
    # γράψει στην κεφαλίδα του. Η τράπεζα 6 φορτώνεται ΠΡΙΝ τρέξει η γεννήτρια
    # και δεν ξαναγράφεται.
    bank6.append(Run("worldinfo", 4, None,
                     note="ΔΕΣΜΕΥΣΗ — seed, πλανήτης, έκδοση γεννήτριας"))
    # Η κρυφή μνήμη φιγούρων ΗΡΘΕ ΕΔΩ από την τράπεζα 2 (βήμα 30). Τη διαβάζει
    # και τη γράφει ΜΟΝΟ το πέρασμα αντικειμένων, που έχει ήδη σελιδοποιημένη
    # την τράπεζα 6 για τα τεταρτημόρια και τις φιγούρες — άρα δεν χρειάζεται
    # να είναι εκτός παραθύρου, και τα 512 bytes της τράπεζας 2 που ελευθερώνει
    # είναι κώδικας που φεύγει από την τράπεζα 0, η μόνη σπάνια (§4.2).
    bank6.append(Run("dome_fig", 64 * 8, None,
                     note="ΔΕΣΜΕΥΣΗ — ποια φιγούρα σε κάθε θέση κάθε θόλου"))
    # Ο πάγκος διαδρομών ΕΦΥΓΕ από εδώ: η BFS σελιδοποιεί το &4000 όσο τρέχει,
    # οπότε δεν μπορεί να κρατά τα δεδομένα της σε σελιδοποιημένη τράπεζα.
    # Ζει τώρα στην τράπεζα 2 (rt_nodes, rt_row, node_adj).

    # --- τράπεζα 7 ----------------------------------------------------------
    for n in STRUCTS:
        bank7.append(spr(n))
    for p in PLANTS:
        bank7.append(spr(f"plant_{p}"))
    ptr["plant_ptr"] = [f"plant_{p}" for p in PLANTS]
    bank7.append(Run("plant_ptr", len(PLANTS) * 2, bytes(len(PLANTS) * 2),
                     note="παράγεται"))
    # 1.280 από το βήμα 79: τα 1.024 είχαν μείνει με επτά ελεύθερα, και το
    # «τι έχει κάτω ο κέρσορας» θέλει τα ονόματα των εδαφών. Η γραμματοσειρά
    # ανεβαίνει 256 bytes· η τράπεζα 7 έχει 952 ελεύθερα από πάνω της.
    # 2.048 από το βήμα 84: η οθόνη βοήθειας λέει όνομα και μια γραμμή για
    # καθένα από τα 33 κουμπιά (790 bytes).
    # ΤΑ ΣΥΜΒΟΛΑ ΤΩΝ ΚΟΥΜΠΙΩΝ (βήμα 84, §9.3): 33 x 17 bytes, ένα bit το pixel,
    # από το tools/buttons.py. Τα διαβάζει μόνο το src/bar.asm, με την τράπεζα 7
    # μέσα όπως για τον γλύφο. ΠΡΙΝ ΑΠΟ ΤΑ ΚΕΙΜΕΝΑ από το βήμα 111: με τα 2.148
    # bytes τους η γραμματοσειρά (στοίχιση 8) θα πήγαινε 8 πιο πέρα και η
    # τράπεζα δεν θα χωρούσε· έτσι γεμίζει ακριβώς ως το #8000.
    gfx = buttons.gfx()
    bank7.append(Run("btn_gfx", len(gfx), gfx, note="παράγεται από το tools/buttons.py"))
    bank7.append(Run("text", TEXT_MAX, None, note="ΔΕΣΜΕΥΣΗ — τα κείμενα (src/uitext.asm)"))
    # Η ΓΡΑΜΜΑΤΟΣΕΙΡΑ, ΕΚΕΙ ΟΠΟΥ ΗΤΑΝ Η ΔΕΣΜΕΥΣΗ «audio» (βήμα 33). Τα 2.048
    # bytes κρατιούνταν από το §4.2 για μουσική μέσα στο παιχνίδι, και το §9.5
    # αποφάσισε ρητά ΟΧΙ μουσική· δεν τα διάβασε ποτέ τίποτα. Η γραματοσειρά
    # έχει ΕΝΑΝ αναγνώστη (το hc_draw του src/hud.asm), που σελιδοποιεί την 7
    # γύρω από τα δεκαέξι bytes του γλύφου — και τα 1.536 bytes που αφήνει στην
    # τράπεζα 2 γίνονται χώρος κώδικα, αφού ό,τι ακολουθεί την αρένα κατεβαίνει.
    #
    # ΣΕ MODE 1 ΑΠΟ ΤΟ ΒΗΜΑ 83 (§9.2). Το HUD ζει πια στις λωρίδες Mode 1 πάνω
    # και κάτω από το κάδρο, και ο γλύφος είναι ένα byte ανά γραμμή αντί για
    # δύο: 768 bytes. Βγαίνει ΕΔΩ από το font_gfx των assets (δεν αγγίζουμε τα
    # assets): ό,τι pixel έχει μελάνι γίνεται pen 3, τα άλλα pen 0. Στοίχιση 8,
    # ώστε οι οκτώ γραμμές του γλύφου να μη διασχίζουν σελίδα (inc e).
    #
    # ΚΑΙ ΤΑ ΚΕΛΙΑ ΤΗΣ ΜΠΑΡΑΣ είναι γλύφοι, οι κωδικοί #80-#84 (HUD_CELLS): κενό,
    # pen 1, 2, 3, και η άδεια μπάρα. Πέφτουν ακριβώς μετά τον 127, οπότε ο
    # hud_char βρίσκει κάθε κωδικό με τον ίδιο πολλαπλασιασμό.
    s = smap.get("font_gfx")
    if s is None:
        raise Fail("λείπει sprite: font_gfx")
    # ΟΧΙ ΟΙ ΠΕΝΤΕ ΤΕΛΕΥΤΑΙΟΙ (βήμα 101): τους { | } ~ και τον 127 δεν τους
    # τυπώνει κανένα κείμενο, και τα 40 bytes τους πήραν το σύμβολο και τη
    # βοήθεια του DEMOLISH. Τα κελιά έρχονται στη θέση τους, #7B-#7F
    # (HUD_CELL0, src/hud.asm).
    font = mode1_font(blob[s.off:s.off + s.size])[:FONT_N * 8] + HUD_CELLS
    bank7.append(Run("font_m1", len(font), font, align=8,
                     note="παράγεται από το font_gfx"))       # (ch-32)*8

    return arena, bank1, bank5, bank6, bank7, ptr


# ---------------------------------------------------------------------------
# ΤΑ ΚΕΛΥΦΗ ΩΣ ΔΙΑΣΤΗΜΑΤΑ (βήμα 108 οι πίνακες, βήμα 110 η αποθήκευση· src/span.asm,
# DESIGN §8.4).
#
# Ενα ζεύγος (μάσκα #FF, χρώμα 0) αφήνει την οθόνη όπως ήταν. Στους θόλους
# είναι το 40% των ζευγών, στους δακτυλίους το 75% — το εσωτερικό τους, που ο
# θόλος καλύπτει. Κάθε γραμμή κάθε τεταρτημορίου έχει ΕΝΑ διάστημα με κάτι, και
# ό,τι είναι έξω του είναι τέτοιο ζεύγος· ανά οκτώ γραμμές (μία ΟΜΑΔΑ): το byte
# (a << 4) | n, με a το πρώτο ζεύγος της ομάδας που δεν είναι διάφανο και n πόσα
# ως το τελευταίο. Μια ομάδα χωρίς τίποτα είναι 0 (οι οκτώ πρώτες γραμμές κάθε
# θόλου). Συντηρητικό: ένα διάφανο ζεύγος μέσα στο διάστημα κοστίζει όσο πριν,
# ένα αδιάφανο έξω θα έλειπε από την οθόνη — αυτό το αρνείται το assert εδώ.
#
# ΩΣ ΤΟ ΒΗΜΑ 109 ο πίνακας ήταν στην τράπεζα 0 (build/span_tables.asm, 36 bytes)
# και τα τεταρτημόρια ολόκληρα στην 6: 7.424 bytes, τα μισά από αυτά ζεύγη που
# δεν ζωγραφίζονται ποτέ. ΤΩΡΑ κάθε κέλυφος είναι:
#
#   +0  .. +7    το διάστημα κάθε ομάδας (0 = άδεια· μετά την τελευταία, 0)
#   +8  .. +23   η διεύθυνση των δεδομένων κάθε ομάδας (0 για την άδεια)
#   +24 .. +31   k κάθε ομάδας: πόσα ζεύγη στο τέλος του διαστήματος είναι
#                αδιαφανή (βήμα 114)
#   +32 ..       κάθε ομάδα που έχει κάτι: οκτώ γραμμές των 2n - k bytes — τα
#                ζεύγη a .. a+n-k-1 του nw, και μετά μόνο το ΧΡΩΜΑ των k
#
# Η κεφαλίδα σε μία σελίδα (page): το sp_grp προσθέτει μόνο στο L. Οι
# διευθύνσεις μπαίνουν στο δεύτερο πέρασμα του pack(), όταν το κέλυφος έχει θέση.
#
# ΤΟ ΑΔΙΑΦΑΝΕΣ ΤΕΛΟΣ (βήμα 114). Ενα ζεύγος με μάσκα 0 γράφει απλώς το χρώμα του,
# αλλά ο πυρήνας με μάσκα το πληρώνει όσο ένα μισοδιάφανο: 18 us, 32
# καθρεφτισμένο. Στους θόλους, μέσα στα διαστήματα, έτσι είναι 80-90% των
# ζευγών: ο θόλος είναι γεμάτος ως το κέντρο του, που είναι το δεξί άκρο του
# nw. Οσες στήλες στο τέλος του διαστήματος έχουν μάσκα 0 και στις οκτώ
# γραμμές της ομάδας αποθηκεύονται χωρίς τη μάσκα τους, και ζωγραφίζονται με
# αντιγραφή: ldir (5 us), ή ο πίνακας καθρεφτίσματος (18 us). Μόνο όταν είναι
# τουλάχιστον K_MIN: κάθε γραμμή με δύο κομμάτια πληρώνει μια κλήση ακόμη. Οι
# δακτύλιοι έχουν το πολύ δύο τέτοιες στήλες και μένουν όπως ήταν.
# ---------------------------------------------------------------------------
SPAN_G = 8
SHELL_HDR = 4 * SPAN_G          # 8 διαστήματα + 8 διευθύνσεις + 8 k (βήμα 114)
K_MIN = 3


def shell_spans(s, blob):
    """[(a, n) ή None] ανά ομάδα των SPAN_G γραμμών του sprite s."""
    assert s.masked and s.h % SPAN_G == 0 and s.h // SPAN_G <= SPAN_G, s
    out = []
    for g0 in range(0, s.h, SPAN_G):
        cols = [x for y in range(g0, g0 + SPAN_G) for x in range(s.w)
                if blob[s.off + y * s.stride + 2 * x] != 0xFF
                or blob[s.off + y * s.stride + 2 * x + 1] != 0]
        if not cols:
            out.append(None)
            continue
        a, n = min(cols), max(cols) + 1 - min(cols)
        assert a < 16 and 0 < n < 16, (s, g0, a, n)
        out.append((a, n))
    return out


def shell_opaque(s, blob, g, a, n):
    """k της ομάδας g: πόσες στήλες στο τέλος του διαστήματος [a, a+n) έχουν
    μάσκα 0 σε όλες τις γραμμές της — ή 0, αν είναι λιγότερες από K_MIN."""
    k = 0
    while k < n and all(blob[s.off + y * s.stride + 2 * (a + n - 1 - k)] == 0
                        for y in range(g * SPAN_G, (g + 1) * SPAN_G)):
        k += 1
    return k if k >= K_MIN else 0


def shell(name, smap, blob):
    """Το κέλυφος name ως κεφαλίδα και διαστήματα (βλ. πάνω)."""
    s = smap[name]
    sp = shell_spans(s, blob)
    data, groups, ks = bytearray(), [], []
    for g, x in enumerate(sp):
        if x is None:
            groups.append(None)
            ks.append(0)
            continue
        a, n = x
        k = shell_opaque(s, blob, g, a, n)
        ks.append(k)
        groups.append(SHELL_HDR + len(data))
        for y in range(g * SPAN_G, (g + 1) * SPAN_G):
            row = s.off + y * s.stride
            data += blob[row + 2 * a:row + 2 * (a + n - k)]
            data += blob[row + 2 * (a + n - k) + 1:row + 2 * (a + n):2]
    hdr = bytes(0 if x is None else x[0] << 4 | x[1] for x in sp)
    hdr += bytes(SHELL_HDR - SPAN_G - len(hdr))
    hdr += bytes(ks) + bytes(SPAN_G - len(ks))
    r = Run(name, SHELL_HDR + len(data), hdr + bytes(data), page=SHELL_HDR,
            note=f"διαστήματα ({s.h * s.stride} ολόκληρο)")
    r.groups = groups
    return r


def spans(out):
    """build/span_tables.asm: οι σταθερές του src/span.asm."""
    with open(os.path.join(out, "span_tables.asm"), "w", encoding="utf-8") as f:
        f.write("; ΠΑΡΑΓΕΤΑΙ από tools/pack.py — μην το επεξεργάζεσαι.\n")
        f.write(f"SPAN_G      equ {SPAN_G}\n")
        f.write(f"SHELL_HDR   equ {SHELL_HDR}\n")


def pack():
    """Στρώνει τα πάντα. Επιστρέφει (arena, bank1, bank5, bank6, bank7, ptr,
    images, free, report). Σκάει με Fail αν κάτι δεν χωράει."""
    smap, blob = load_map(), load_bin()
    arena, bank1, bank5, bank6, bank7, ptr = build_runs(smap, blob)

    u2 = pack_flat(arena, PAGE2_BASE, BANK_SIZE, "τράπεζα 2")
    u1 = pack_flat(bank1, BANK1_BASE, BANK1_SIZE, "τράπεζα 1 (πάνω από το DIST)")
    u5 = pack_flat(bank5, BANK5_BASE, BANK5_SIZE, "τράπεζα 5 (πάνω από NEXTHOP και ευρετήριο)")
    u6 = pack_flat(bank6, WINDOW_BASE, BANK_SIZE, "τράπεζα 6")
    u7 = pack_flat(bank7, WINDOW_BASE, BANK_SIZE, "τράπεζα 7")

    by_name = {r.name: r for r in arena + bank1 + bank5 + bank6 + bank7}

    # 2ο πέρασμα: οι πίνακες δεικτών ξέρουν πια πού κάθονται όλα
    for tab, names in ptr.items():
        r = by_name[tab]
        data = bytearray()
        for n in names:
            data += (0 if n is None else by_name[n].addr).to_bytes(2, "little")
        r.data = bytes(data)
    # και οι διευθύνσεις των ομάδων κάθε κελύφους (βήμα 110)
    for r in bank6:
        if getattr(r, "groups", None) is not None:
            d = bytearray(r.data)
            for g, rel in enumerate(r.groups):
                if rel is not None:
                    d[SPAN_G + 2 * g:SPAN_G + 2 * g + 2] = (r.addr + rel).to_bytes(2, "little")
            r.data = bytes(d)

    # --- εικόνες ------------------------------------------------------------
    out = os.path.join(ROOT, "build")
    os.makedirs(out, exist_ok=True)

    # Η εικόνα της τράπεζας 2 κόβεται στο ΧΡΗΣΙΜΟΠΟΙΗΜΕΝΟ μέρος: ό,τι μένει από
    # πάνω το παίρνει ο κώδικας (DESIGN §4.3), και ένα incbin 16 KB θα το
    # έσβηνε τη στιγμή του φορτώματος.
    page2 = bytearray(u2)
    for r in arena:
        if r.data:
            o = r.addr - PAGE2_BASE
            page2[o:o + r.size] = r.data
    b1 = bytearray(BANK1_SIZE)
    for r in bank1:
        if r.data:
            o = r.addr - BANK1_BASE
            b1[o:o + r.size] = r.data
    # Η τράπεζα 5 κόβεται κι αυτή στο χρησιμοποιημένο: φορτώνεται σε πρόχειρο
    # και ο φορτωτής την αντιγράφει στη θέση της (src/boot.asm).
    b5 = bytearray(u5)
    for r in bank5:
        if r.data:
            o = r.addr - BANK5_BASE
            b5[o:o + r.size] = r.data
    b6 = bytearray(BANK_SIZE)
    b7 = bytearray(BANK_SIZE)
    for img, runs in ((b6, bank6), (b7, bank7)):
        for r in runs:
            if r.data:
                o = r.addr - WINDOW_BASE
                img[o:o + r.size] = r.data

    images = {"page2": bytes(page2), "bank1": bytes(b1), "bank5": bytes(b5),
              "bank6": bytes(b6), "bank7": bytes(b7)}
    for name, img in images.items():
        with open(os.path.join(out, name + ".bin"), "wb") as f:
            f.write(img)

    # --- διευθύνσεις για τον assembler -------------------------------------
    with open(os.path.join(out, "layout.asm"), "w", encoding="utf-8") as f:
        f.write("; ΠΑΡΑΓΕΤΑΙ από tools/pack.py — μην το επεξεργάζεσαι.\n")
        f.write(f"PAGE2_TOP   equ #{PAGE2_BASE + u2:04X}   ; πρώτο ελεύθερο byte\n")
        f.write(f"B5_BASE     equ #{BANK5_BASE:04X}   ; οι μηχανές στην τράπεζα 5\n")
        f.write(f"B5_LEN      equ {u5}\n")
        f.write("; Οι τράπεζες 6/7 φαίνονται στο &4000 όταν σελιδοποιηθούν.\n\n")
        f.write("; οι κωδικοί των φιγούρων (βήμα 111): το L τους, και το bit 0 η σελίδα\n")
        for j, name in enumerate(FIG_ALL):
            f.write(f"FC_{name.upper():<14} equ {fig_code(j)}\n")
        f.write("\n")
        for label, runs in (("τράπεζα 2", arena), ("τράπεζα 1", bank1),
                            ("τράπεζα 5", bank5), ("τράπεζα 6", bank6),
                            ("τράπεζα 7", bank7)):
            f.write(f"; --- {label} ---\n")
            for r in sorted(runs, key=lambda r: r.addr):
                f.write(f"G_{r.name:<20} equ #{r.addr:04X}\n")
            f.write("\n")

    # --- λογαριασμός --------------------------------------------------------
    lines = []
    for label, runs, used, cap in (("τράπεζα 2", arena, u2, BANK_SIZE),
                                   ("τράπεζα 1", bank1, u1, BANK1_SIZE),
                                   ("τράπεζα 5", bank5, u5, BANK5_SIZE),
                                   ("τράπεζα 6", bank6, u6, BANK_SIZE),
                                   ("τράπεζα 7", bank7, u7, BANK_SIZE)):
        # ΤΟ «ΕΛΕΥΘΕΡΑ» ΤΗΣ ΤΡΑΠΕΖΑΣ 2 ΕΙΝΑΙ ΗΔΗ ΞΟΔΕΜΕΝΟ. Οσα μένουν πάνω από
        # το PAGE2_TOP τα μοιράζει το src/const.asm: αρχείο αναίρεσης
        # φαντάσματος και ο κώδικας που δεν χώρεσε στην τράπεζα 0. Χωρίς αυτή
        # τη σημείωση η γραμμή διαβάζεται ως «πέντε χιλιάδες ελεύθερα» και δεν
        # είναι — το πραγματικό περιθώριο το λέει το tools/mkdsk.py.
        note = ("  (τα παίρνει το const.asm: GH_BUF + κώδικας τράπεζας 2)"
                if label == "τράπεζα 2" else "")
        gaps = sum(getattr(r, "gap", 0) for r in runs)
        if gaps:
            note += f"  (και {gaps} κάτω από καρφωμένο run)"
        lines.append(f"{label}: {used - gaps}/{cap}  ελεύθερα {cap - used + gaps}{note}")
        for r in sorted(runs, key=lambda r: r.addr):
            if getattr(r, "gap", 0):
                lines.append(f"      #{r.addr - r.gap:04X} {r.gap:>5}  (ελεύθερα)")
            lines.append(f"      #{r.addr:04X} {r.size:>5}  {r.name}"
                         f"{'  · ' + r.note if r.note else ''}")
        lines.append("")
    report = "\n".join(lines)
    with open(os.path.join(out, "layout.txt"), "w", encoding="utf-8") as f:
        f.write(report)
    spans(out)
    return arena, bank1, bank5, bank6, bank7, ptr, images, [BANK_SIZE - u2], report


if __name__ == "__main__":
    print(pack()[-1])
