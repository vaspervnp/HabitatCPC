"""Η γεννήτρια κόσμου — αναφορά σε Python (DESIGN.md §5).

Αυτό είναι η ΠΡΟΔΙΑΓΡΑΦΗ. Ο Z80 πρέπει να βγάζει byte-προς-byte το ίδιο 16 KB
επίπεδο για το ίδιο seed· το tests/test_worldgen.py το επιβάλλει.

Κάθε βήμα είναι καθαρή συνάρτηση του seed: καμία χρήση του R, του μετρητή
frames, ή οτιδήποτε εξαρτάται από χρονισμό. Αλλαγή κατωφλιού αλλάζει ΚΑΘΕ
κόσμο, γι' αυτό υπάρχει το GEN_VERSION και φαίνεται δίπλα στο seed.

ΑΠΟΚΛΙΣΗ ΑΠΟ ΤΟ §5.4: το DESIGN περιγράφει πυραμίδα τεσσάρων επιπέδων με
upsample-and-add. Εδώ υπάρχει ΕΝΑ παρεμβαλλόμενο επίπεδο (πλέγμα 16x16, κελί 8
tiles) συν δύο ΧΟΝΔΡΕΣ οκτάβες χωρίς παρεμβολή. Ο λόγος είναι η μνήμη: η
πυραμίδα θέλει ενδιάμεσα buffers 5,4 KB και το τελευταίο επίπεδο δεν γίνεται
in-place — ενώ το σχήμα εδώ θέλει 256 bytes. Το σχήμα των ηπείρων το δίνει το
χονδρό επίπεδο· οι δύο άλλες οκτάβες προσθέτουν υφή σε 4 και 2 tiles, που
ούτως ή άλλως το autotiling ισοπεδώνει στο όριο του tile.
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import world
from world import (W, HALF, GROUND, DUST, ROCK, MOUNTAIN,
                   WATER, DEEPWATER, FOUNDATION, byte)

GEN_VERSION = 1

MID = 128                      # «μέση στάθμη» — το ύψος του ουδέτερου εδάφους
COARSE = 16                    # σημεία πλέγματος ανά άξονα· κελί = 8 tiles
MOIST_SALT = 97                # άλλο πεδίο θορύβου από το ίδιο P[]
ORE_SALT = 211

R_PLATEAU, R_BLEND, R_RIM = 5, 10, 57
ANCHORS = 6
DIRS = 24                      # 4 υπο-κατευθύνσεις x 6 τομείς

# (W2 βαθύ, W1 ρηχό, M1 βράχος, M2 βουνό, F γονιμότητα, OT φλέβα)
PLANETS = [
    (56,  84, 175, 205, 128, 200),   # 0 desert
    (96, 120, 170, 200, 100, 205),   # 1 ice    — πολύ νερό, λίγη γονιμότητα
    (52,  66, 140, 180, 150, 195),   # 2 storm  — σπασμένο έδαφος, πολύς βράχος
    (30,  40, 150, 190, 250, 185),   # 3 barren — σχεδόν χωρίς νερό, χωρίς γόνιμο
]


def dir_table():
    """24 κατευθύνσεις, κλίμακα 64. Παράγεται εδώ, εξάγεται και για τον Z80,
    ώστε να υπάρχει ΕΝΑ αντίγραφο."""
    import math
    out = []
    for i in range(DIRS):
        a = 2 * math.pi * i / DIRS
        out.append((round(64 * math.cos(a)), round(64 * math.sin(a))))
    return out


DIR = dir_table()


class Rng:
    """LFSR 16-bit Galois. Οκτώ βήματα ανά byte, ώστε διαδοχικά bytes να μη
    συσχετίζονται. Περίοδος 65535 — το μηδέν είναι απορροφητικό, γι' αυτό το
    seed 0 γίνεται #ACE1."""

    def __init__(self, seed):
        self.x = seed & 0xFFFF or 0xACE1

    def step(self):
        bit = self.x & 1
        self.x >>= 1
        if bit:
            self.x ^= 0xB400
        return self.x

    def byte(self):
        for _ in range(8):
            self.step()
        return self.x & 0xFF


def permutation(rng):
    p = list(range(256))
    for i in range(255, 0, -1):
        j = rng.byte()
        p[i], p[j] = p[j], p[i]
    return p


def make_anchors(rng):
    """Έξι άγκυρες, μία ανά τομέα 60°, με τα είδη ΚΑΡΦΩΤΑ.

    Χωρίς αυτές ένα seed μπορεί να μην έχει νερό σε απόσταση περπατήματος και
    να μην παίζεται. Rejection sampling ολόκληρου χάρτη θα ήταν πολύ αργό· οι
    άγκυρες βγαίνουν από το ΙΔΙΟ seed, οπότε ο χάρτης μένει καθαρή συνάρτηση.
    """
    # Οι ακτίνες δεν είναι διακοσμητικές: μια ράχη με ακτίνα 10 δεν ανεβάζει
    # ποτέ το ύψος πάνω από το M2, οπότε δεν γίνεται βουνό, οπότε δεν υπάρχει
    # φλέβα — και το seed βγαίνει απαίξιμο. Το ελάχιστο 14 είναι αυτό που
    # κάνει την εγγύηση αληθινή.
    spec = [("lake", 12, 15), ("lake", 12, 15),
            ("ridge", 14, 15), ("ridge", 14, 15),
            ("basin", 8, 7), ("wild", 20, 15)]
    out = []
    for k, (kind, lo, mask) in enumerate(spec):
        d = (k * 4 + (rng.byte() & 3)) % DIRS
        rad = lo + (rng.byte() & mask)
        if kind == "wild":
            kind = "lake" if (rng.byte() & 1) else "ridge"
        ax = (rad * DIR[d][0]) >> 6
        ay = (rad * DIR[d][1]) >> 6
        out.append((ax, ay, kind, rad, 256 // rad))
    return out


def generate(seed, planet=0):
    rng = Rng(seed)
    P = permutation(rng)
    anchors = make_anchors(rng)
    W2, W1, M1, M2, F, OT = PLANETS[planet]

    def H(gx, gy):
        return P[(P[gx & 255] + gy) & 255]

    # --- χονδρό πλέγμα, ένα ανά πεδίο -------------------------------------
    coarse_e = [H(j, i) for i in range(COARSE) for j in range(COARSE)]
    coarse_m = [H(j, i + MOIST_SALT) for i in range(COARSE) for j in range(COARSE)]

    def field_row(coarse, v):
        """Μία γραμμή 128 τιμών.

        Κάθετα: παρεμβολή ανάμεσα σε δύο γραμμές πλέγματος.
        Οριζόντια: ράμπα με συσσωρευτή 8.8 — acc >> 8 ισούται ΑΚΡΙΒΩΣ με
        a + ((b-a)*f >> 3), χωρίς πολλαπλασιασμό ανά tile.
        """
        cv, fv = v >> 3, v & 7
        top = coarse[cv * COARSE:(cv + 1) * COARSE]
        nv = (cv + 1) & (COARSE - 1)
        bot = coarse[nv * COARSE:(nv + 1) * COARSE]
        lat = [(a + (((b - a) * fv) >> 3)) & 0xFF for a, b in zip(top, bot)]
        row = []
        for c in range(COARSE):
            a, b = lat[c], lat[(c + 1) & (COARSE - 1)]
            acc = a << 8
            stp = (b - a) << 5
            for _ in range(8):
                row.append((acc >> 8) & 0xFF)
                acc = (acc + stp) & 0xFFFF
        return row

    plane = world.Plane()
    ore_ok = bytearray(W * W)

    for v in range(W):
        erow = field_row(coarse_e, v)
        mrow = field_row(coarse_m, v)
        y = v - HALF
        # ποιες άγκυρες αγγίζουν ΑΥΤΗ τη γραμμή — σχεδόν πάντα καμία
        act = [a for a in anchors if abs(y - a[1]) <= a[3]]
        for u in range(W):
            x = u - HALF
            # δύο χοντρές οκτάβες: υφή, όχι σχήμα
            e = erow[u] + (H(u >> 2, v >> 2) >> 3) + (H(u >> 1, v >> 1) >> 4)
            e = min(255, max(0, e - 23))    # μέση τιμή των δύο οκταβών
            m = mrow[u]

            # --- άγκυρες ---
            # ΑΝΑΜΕΙΞΗ, όχι αντικατάσταση. Με `e = min(e, MID - bump)` το
            # ταβάνι δάγκωνε σε ΟΛΟ το τετράγωνο — ακόμη και εκεί που το bump
            # ήταν 0 — και οι λίμνες έβγαιναν κυριολεκτικά τετράγωνες. Εδώ το
            # βάρος πάει στο 255 στο κέντρο (άρα η εγγύηση κρατάει) και σβήνει
            # στο 0 στην άκρη (άρα την άκρη τη γράφει ο θόρυβος).
            #
            # Η απόσταση είναι ΟΚΤΑΓΩΝΙΚΗ: max + min/2. Η Chebyshev έδινε
            # τετράγωνα, η ευκλείδεια θέλει ρίζα· αυτή πέφτει μέσα σε ~6%.
            ore_here = 0
            lake_w = ridge_w = basin_w = 0
            for ax, ay, kind, rad, scale in act:
                dx, dy = abs(x - ax), abs(y - ay)
                d = (dx + (dy >> 1)) if dx > dy else (dy + (dx >> 1))
                if d >= rad:
                    continue
                w = min(255, (rad - d) * scale)
                if kind == "lake":
                    if w > lake_w:
                        lake_w = w
                elif kind == "ridge":
                    if w > ridge_w:
                        ridge_w = w
                    if d < (rad >> 1):
                        ore_here = 1
                else:
                    if w > basin_w:
                        basin_w = w
            if lake_w:
                e = e - ((e * lake_w) >> 8)          # στόχος 0
                ore_here = 0
            elif ridge_w:
                e = e + (((255 - e) * ridge_w) >> 8)  # στόχος 255
            elif basin_w:
                e = e + (((MID - e) * basin_w) >> 8)  # στόχος MID, προσημασμένο

            # --- πλατό κέντρου και ορεινό χείλος ---
            r = max(abs(x), abs(y))
            if r <= R_PLATEAU:
                e = MID
            elif r <= R_BLEND:
                w = ((r - R_PLATEAU) * 255) // (R_BLEND - R_PLATEAU)
                e = MID + (((e - MID) * w) >> 8)
            if r >= R_RIM:
                e = min(255, e + (r - R_RIM + 1) * 40)

            # --- ταξινόμηση ---
            if e < W2:
                c, res = DEEPWATER, 0
            elif e < W1:
                c, res = WATER, 0
            elif e > M2:
                c = MOUNTAIN
                res = 1 if (ore_here and H(u + ORE_SALT, v) > OT) else 0
            elif e > M1:
                c, res = ROCK, 0
            elif m > F:
                c, res = GROUND, 1
            else:
                c, res = DUST, 0
            plane.buf[v * W + u] = byte(c, res=res, decor=H(u, v + 7) & 3)
            ore_ok[v * W + u] = ore_here

    despeckle(plane)
    carve_landing(plane)
    return plane


def despeckle(plane):
    """Ένα πέρασμα: tile που διαφέρει και από τους τέσσερις γείτονες παίρνει
    την κλάση του βόρειου. In-place με σταθερή σειρά σάρωσης — εξαρτάται από
    τη σειρά, αλλά είναι ΝΤΕΤΕΡΜΙΝΙΣΤΙΚΟ, που είναι το μόνο που μετράει."""
    for v in range(1, W - 1):
        for u in range(1, W - 1):
            i = v * W + u
            c = plane.buf[i] & 7
            n = plane.buf[i - W] & 7
            if (c != n and c != (plane.buf[i + W] & 7)
                    and c != (plane.buf[i - 1] & 7)
                    and c != (plane.buf[i + 1] & 7)):
                plane.buf[i] = (plane.buf[i] & 0xF8) | n


def carve_landing(plane):
    """Ό,τι κι αν είπε ο θόρυβος, το κέντρο είναι επίπεδο και χτίσιμο."""
    for y in range(-4, 5):
        for x in range(-4, 5):
            plane.set(x, y, byte(FOUNDATION, decor=(x + y) & 1))


# --- έλεγχος παιξιμότητας (DESIGN §13) -----------------------------------

def playable(plane, reach=30):
    """Νερό ΚΑΙ φλέβα μέσα σε `reach` tiles από το κέντρο."""
    water = ore = False
    for y in range(-reach, reach + 1):
        for x in range(-reach, reach + 1):
            b = plane.get(x, y)
            c = b & 7
            if c in (WATER, DEEPWATER):
                water = True
            elif c == MOUNTAIN and (b >> 3) & 1:
                ore = True
            if water and ore:
                return True, True
    return water, ore
