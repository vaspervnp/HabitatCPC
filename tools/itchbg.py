#!/usr/bin/env python3
"""Το φόντο και το banner της σελίδας στο itch.io: assets/itch_background.png και
assets/itch_banner.png.

Ο παίκτης: «create in assets a background image for
https://revive8bit.itch.io/habitat page ... την εικόνα την θέλω για το theme
της σελίδας». Ζωγραφισμένο από τα γραφικά και τις αναφορές του ίδιου του
παιχνιδιού, όπως η οθόνη του Habitat (tools/splash.py): τα 16 χρώματα της
ερήμου, pixels Mode 0 διπλά σε πλάτος, χωρίς κανένα φίλτρο.

ΤΙ ΒΛΕΠΕΙ Ο ΑΛΛΟΣ. Η στήλη της σελίδας είναι 960 pixels στη μέση, από την κορυφή
ως το τέλος: το φόντο φαίνεται μόνο δεξιά και αριστερά της. 203 pixels σε οθόνη
1366, 472 σε 1920, 800 σε 2560. Με ένα tile 32 x 32 αυτά είναι 6, 15 και 25 tiles:
μία στήλη θόλων ακριβώς δίπλα στη στήλη της σελίδας φαίνεται παντού, δεύτερη από
το 1920, τρίτη μόνο στις πλατιές οθόνες. Οι διάδρομοι περνούν κάτω από τη σελίδα.

ΕΠΑΝΑΛΑΜΒΑΝΕΤΑΙ ΚΑΙ ΣΤΙΣ ΔΥΟ ΔΙΕΥΘΥΝΣΕΙΣ χωρίς ραφή, για Repeat: Both και Align:
Center: το έδαφος είναι περιοδικό (άθροισμα ημιτόνων με ακέραιες συχνότητες, και
το autotile διαβάζει τους γείτονες με τύλιγμα), και κανένα κτίριο δεν πατά στην
άκρη. Μια σελίδα ψηλότερη από την εικόνα συνεχίζει απλώς από την αρχή.

Ο ΚΑΜΒΑΣ. Το tools/scene.py ζωγραφίζει σε καμβά 80 x 200, με το SCR_W και το SCR_H
σταθερές του module: εδώ αλλάζουν και στα δύο modules, σε αυτή τη διεργασία μόνο,
πριν από τον πρώτο καμβά (big()).

ΤΟ BANNER ΕΙΝΑΙ ΠΑΡΑΘΥΡΟ ΣΤΟΝ ΙΔΙΟ ΚΟΣΜΟ: το κομμάτι που κρύβει η στήλη της σελίδας,
960 pixels, από την κορυφή, με τον τίτλο του μενού (menuworld.title_cells) από πάνω.
Η στήλη αρχίζει στο tile -15 ακριβώς, άρα με Align: Center οι διάδρομοι των
περιθωρίων μπαίνουν στο banner και καταλήγουν στους θόλους του. Με άλλη στοίχιση
χάνεται μόνο η συνέχεια.

    python3 tools/itchbg.py
"""
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import colony as CL                                                     # noqa: E402
import menuworld as MW                                                  # noqa: E402
import palette                                                          # noqa: E402
import refrender                                                        # noqa: E402
import scene as S                                                       # noqa: E402
import world as W                                                       # noqa: E402

OUT = os.path.join(ROOT, "assets", "itch_background.png")
OUT_BANNER = os.path.join(ROOT, "assets", "itch_banner.png")

PLANET = 0                  # η έρημος, όπως στην οθόνη του Habitat και στο βίντεο
SCALE = 2                   # ένα pixel Mode 0 = 4 x 2, ένα tile = 32 x 32
COLS, ROWS = 80, 60         # 2.560 x 1.920: 800 pixels δεξιά και αριστερά της στήλης
SEED = 0x1982
FIGURES = 130
PAGE = 15                   # η στήλη της σελίδας: tiles από το κέντρο, 480 / 32
BANNER_ROWS = 12            # 960 x 384: ως το κάτω χείλος του μεγάλου θόλου
TITLE_W, TITLE_H = 3, 8     # ένα κελί του τίτλου: bytes x γραμμές (24 x 16 pixels)
TITLE_TOP = 4               # γραμμές πάνω από το περίγραμμά του

# Τα tiles μετρούν από το κέντρο της εικόνας κατά x, από την κορυφή κατά y: η
# στήλη της σελίδας είναι τα x από -15 ως 15.
X0 = -COLS // 2

# (x, y κέντρου σε tiles, μέγεθος 0-2, δωμάτιο)
DOMES = [
    # αριστερά, δίπλα στη στήλη
    (-19, 8, 2, "greenhouse"),  # 0
    (-19, 18, 1, "canteen"),    # 1
    (-19, 27, 0, "oxygen"),     # 2
    (-19, 36, 1, "greenhouse"),  # 3
    (-19, 46, 2, "factory"),    # 4
    (-19, 55, 0, "oxygen"),     # 5
    # αριστερά, δεύτερη στήλη
    (-28, 8, 0, "lab"),         # 6
    (-28, 18, 1, "factory"),    # 7
    (-28, 36, 1, "medbay"),     # 8
    (-28, 46, 0, "storage"),    # 9
    # αριστερά, τρίτη
    (-36, 18, 0, "lounge"),     # 10
    (-36, 36, 0, "control"),    # 11
    # δεξιά, δίπλα στη στήλη
    (19, 8, 1, "factory"),      # 12
    (19, 18, 2, "lab"),         # 13
    (19, 28, 1, "medbay"),      # 14: το εργοτάξιο, με την κορδέλα του (βήμα 202)
    (19, 37, 0, "oxygen"),      # 15
    (19, 46, 1, "canteen"),     # 16
    (19, 55, 0, "quarters"),    # 17
    # δεξιά, δεύτερη στήλη
    (28, 8, 0, "quarters"),     # 18
    (28, 18, 1, "greenhouse"),  # 19
    (28, 46, 0, "control"),     # 20
    # δεξιά, τρίτη
    (36, 8, 1, "canteen"),      # 21
    (36, 18, 0, "storage"),     # 22
    # στο banner, κάτω από τη στήλη της σελίδας
    (-9, 8, 1, "canteen"),      # 23
    (0, 8, 2, "factory"),       # 24
    (9, 8, 1, "medbay"),        # 25
]
SITES = {14}

# Από θόλο σε θόλο, σε άξονα ή σε ακριβή διαγώνιο: το μήκος βγαίνει μόνο του.
LINKS = [
    (0, 1), (1, 2), (2, 3), (3, 4), (4, 5),
    (6, 0), (7, 1), (8, 3), (9, 4), (10, 7), (11, 8),
    (12, 13), (13, 14), (14, 15), (15, 16), (16, 17),
    (12, 18), (13, 19), (16, 20), (18, 21), (19, 22),
    (0, 23), (23, 24), (24, 25), (25, 12),  # μέσα από το banner
    (1, 13), (4, 16),               # κάτω από τη στήλη της σελίδας
]

# (είδος, μέγεθος, αριστερά, πάνω σε tiles). 3 x 3 οι ενεργειακές, 2 x 2 το airlock
# και το σκάφος, 4 x 4 το ορυχείο και η πίστα. Με τη σειρά που ζωγραφίζονται στην
# ίδια γραμμή: το σκάφος πάνω στην πίστα.
STRUCTS = [
    ("solar", 2, -32, 25),      # 0
    ("solar", 2, -29, 25),
    ("solar", 2, -26, 25),
    ("solar", 2, -32, 28),
    ("solar", 2, -29, 28),
    ("solar", 2, -26, 28),
    ("turbine", 2, -24, 1),
    ("turbine", 2, -33, 1),
    ("airlock", 0, -34, 45),    # 8
    ("mine", 0, -35, 51),       # 9
    ("ship", 0, 16, 1),         # 10
    ("pad", 0, 25, 25),         # 11
    ("ship", 0, 26, 26),        # 12: σκάφος στην πίστα
    ("turbine", 2, 24, 35),
    ("turbine", 2, 28, 35),
    ("collector", 2, 33, 25),
    ("solar", 2, 25, 52),
    ("solar", 2, 28, 52),
    ("solar", 2, 31, 52),
    ("extractor", 2, 34, 42),   # 19
    ("airlock", 0, 27, 2),      # 20
]
# Διάδρομος ως δομή: (θόλος, δομή, κατεύθυνση). Το μήκος από τα αποτυπώματα.
DOORS = [(9, 8, "w"), (18, 20, "n")]
# Πατούν στο έδαφός τους: το ορυχείο στη φλέβα, η αντλία στη λίμνη.
ON_TERRAIN = {"mine", "extractor"}

GREEN = list(range(12))             # τα φυτά με τη σειρά τους
MACHINES = {
    "canteen": ["food"],
    "factory": ["iron", "bioplastic", "spares", "robots", "weapons"],
    "lab": ["processors", "medical", "vitromeat"],
    "medbay": ["beds", "medstore"],
    "oxygen": ["oxygen"],
}


class Torus(W.Plane):
    """Ο κόσμος της εικόνας: COLS x ROWS tiles που τυλίγονται στις άκρες."""

    def __init__(self):
        self.buf = bytearray(COLS * ROWS)

    def _at(self, tx, ty):
        return (ty % ROWS) * COLS + (tx - X0) % COLS

    def get(self, tx, ty):
        return self.buf[self._at(tx, ty)]

    def set(self, tx, ty, v):
        self.buf[self._at(tx, ty)] = v


def big():
    """Ο καμβάς όσο η εικόνα, και στο refrender και στο scene (βλ. πιο πάνω)."""
    refrender.SCR_W = S.SCR_W = COLS * 4
    refrender.SCR_H = S.SCR_H = ROWS * 16


def waves(rnd, n, top):
    """Περιοδικό πεδίο: n ημίτονα με ακέραιες συχνότητες ως top, άρα χωρίς ραφή."""
    w = [(rnd.randint(-top, top), rnd.randint(1, top), rnd.uniform(0, 6.283),
          rnd.uniform(0.5, 1.0)) for _ in range(n)]

    def f(tx, ty):
        return sum(a * math.sin(6.2832 * (kx * tx / COLS + ky * ty / ROWS) + ph)
                   for kx, ky, ph, a in w)
    return f


def struct_box(kind, tx, ty):
    n = {"mine": 4, "pad": 4, "airlock": 2, "ship": 2}.get(kind, 3)
    return tx, ty, n, n


def boxes(skip=()):
    """Τα αποτυπώματα: (x, y, πλάτος, ύψος) σε tiles."""
    out = []
    for x, y, sz, _ in DOMES:
        r = CL.RADIUS[sz] // 2
        out.append((x - r, y - r, 2 * r, 2 * r))
    for kind, _, tx, ty in STRUCTS:
        if kind not in skip:
            out.append(struct_box(kind, tx, ty))
    return out


def check():
    """Κανένα αποτύπωμα πάνω σε άλλο, εκτός από το σκάφος στην πίστα, και κανένα
    στην άκρη: εκεί θα φαινόταν η ραφή της επανάληψης."""
    b = boxes()
    pad = [struct_box(k, x, y) for k, _, x, y in STRUCTS if k == "pad"]
    for i, (x, y, w, h) in enumerate(b):
        assert X0 < x and x + w < X0 + COLS and 0 < y and y + h < ROWS, ("άκρη", x, y)
        for ox, oy, ow, oh in b[i + 1:]:
            if x < ox + ow and ox < x + w and y < oy + oh and oy < y + h:
                on_pad = any(px <= v[0] and v[0] + v[2] <= px + pw and
                             py <= v[1] and v[1] + v[3] <= py + ph
                             for px, py, pw, ph in pad
                             for v in ((x, y, w, h), (ox, oy, ow, oh)))
                assert on_pad, ("επικάλυψη", (x, y, w, h), (ox, oy, ow, oh))


def terrain():
    """Το έδαφος: ήσυχο, με σκόνη, λίγο βράχο και κρατήρες, ένα βουνό με φλέβα
    γύρω από το ορυχείο και μια λίμνη γύρω από την αντλία, στις πλατιές οθόνες."""
    rnd = random.Random(SEED)
    p = Torus()
    dust, rock = waves(rnd, 6, 6), waves(rnd, 5, 8)
    hill, wet = (-33, 53), (35, 44)     # το κέντρο του βουνού, της λίμνης
    for ty in range(ROWS):
        for tx in range(X0, X0 + COLS):
            decor = rnd.choice((0, 0, 0, 1, 1, 2, 3))
            c = W.GROUND
            if dust(tx, ty) > 1.0:
                c = W.DUST
            elif rock(tx, ty) > 2.2:
                c = W.ROCK
            res = 0
            if math.hypot(tx - hill[0], ty - hill[1]) + 0.5 * rock(tx, ty) < 5.5:
                c = W.MOUNTAIN
                res = rnd.random() < 0.35
            elif math.hypot(tx - wet[0], ty - wet[1]) + 0.4 * dust(tx, ty) < 4.2:
                c = W.WATER
            elif rnd.random() < 0.005:
                c = W.CRATER
            p.set(tx, ty, W.byte(c, res=res, decor=decor))
    # Εδαφος κάτω από τα κτίρια (colony.stamp), χωρίς τις δύο που πατούν στο δικό τους.
    for x, y, w, h in boxes(ON_TERRAIN):
        for ty in range(y, y + h):
            for tx in range(x, x + w):
                p.set(tx, ty, W.byte(W.GROUND, decor=W.decor_of(p.get(tx, ty))))
    return p


def put(rec, i, size, fields):
    for f, v in fields.items():
        rec[i * size + f] = v & 0xFF


def link(da, db):
    """(κατεύθυνση, μήκος) του διαδρόμου από τον θόλο da στον db (tools/colony.py)."""
    ax, ay, sa, _ = da
    bx, by, sb, _ = db
    dx, dy = bx - ax, by - ay
    sx, sy = (dx > 0) - (dx < 0), (dy > 0) - (dy < 0)
    dr = {(0, -1): CL.N_DIR, (1, -1): CL.NE_DIR, (1, 0): CL.E_DIR, (1, 1): CL.SE_DIR,
          (0, 1): CL.S_DIR, (-1, 1): CL.SW_DIR, (-1, 0): CL.W_DIR, (-1, -1): CL.NW_DIR}[sx, sy]
    if dx and dy:
        assert abs(dx) == abs(dy), ("όχι ακριβής διαγώνιος", da, db)
        return dr, abs(dx) - S.DIAG_K[sa] - S.DIAG_K[sb] + 1
    n = abs(dx + dy) - CL.RADIUS[sa] // 2 - CL.RADIUS[sb] // 2
    assert n > 0, ("χωρίς κενό", da, db)
    return dr, n


def colony():
    c = S.Colony()
    for d, (x, y, sz, room) in enumerate(DOMES):
        put(c.dome, d, S.DOME_REC, {
            S.D_CX: 2 * x, S.D_CY: 2 * y, S.D_SIZE: sz, S.D_ROOM: S.ROOMS.index(room),
            S.D_STATE: S.DS_BUILDING if d in SITES else S.DS_ACTIVE, S.D_INTEG: 255})
        at = d * S.DOME_REC
        for s in range(8):
            c.dome[at + S.D_MACH + s] = S.NO_MACH
        for s in range((1, 4, 8)[sz]):
            if room == "greenhouse":
                m = GREEN[(s * 5 + d) % 12]
            elif MACHINES.get(room):
                names = MACHINES[room]
                m = S.MACH.index(names[s % len(names)])
            else:
                continue
            c.dome[at + S.D_MACH + s] = m
            c.dome[at + S.D_HEALTH + s] = 200
    c.n_dome = len(DOMES)

    k = 0
    for a, b in LINKS:
        dr, n = link(DOMES[a], DOMES[b])
        put(c.corr, k, S.CORR_REC, {S.C_A: a, S.C_B: b, S.C_DIR: dr, S.C_LEN: n})
        k += 1
    for d, st, way in DOORS:
        x, y, sz, _ = DOMES[d]
        kind, _, tx, ty = STRUCTS[st]
        _, _, w, h = struct_box(kind, tx, ty)
        r = CL.RADIUS[sz] // 2
        if way == "w":
            assert ty + h // 2 == y, (d, st)
            dr, n = CL.W_DIR, x - r - (tx + w)
        else:
            assert way == "n" and tx + w // 2 == x, (d, st)
            dr, n = CL.N_DIR, y - r - (ty + h)
        assert n > 0, (d, st, n)
        put(c.corr, k, S.CORR_REC, {S.C_A: d, S.C_B: S.MAX_DOME + st, S.C_DIR: dr, S.C_LEN: n})
        k += 1
    c.n_corr = k

    for i, (kind, size, tx, ty) in enumerate(STRUCTS):
        _, _, w, h = struct_box(kind, tx, ty)
        put(c.struct, i, S.STRUCT_REC, {
            S.S_CX: 2 * tx + w, S.S_CY: 2 * ty + h,     # σε μισά tiles, ο κανόνας ισοτιμίας
            S.S_KIND: S.STRUCT_KINDS.index(kind), S.S_SIZE: size,
            S.S_STATE: S.DS_ACTIVE, S.S_INTEG: 255})
    c.n_struct = len(STRUCTS)
    return c


def paint():
    check()
    big()
    a = S.Assets()
    plane = terrain()
    variants = a._tab("tile_variants")
    cv = refrender.Canvas()
    for row in range(ROWS):
        for col in range(COLS):
            tx = X0 + col
            b = plane.get(tx, row)
            k = W.cls_of(b)
            cv.opaque(a.rows(f"tile_{W.CLASS_NAMES[k]}_{plane.variant(tx, row, variants)}"),
                      col * 4, row * 16)
            if k == W.MOUNTAIN and W.res_of(b):
                cv.masked(a.rows(f"ore_overlay_{W.decor_of(b) & 1}"), col * 4, row * 16)
    c = colony()
    S.draw_objects(cv, a, S.Camera(X0, 0), c, S.Clip(0, 0, COLS * 4, ROWS * 16),
                   CL.agents(c, FIGURES))
    return cv


def write(pens, path):
    """Με palette 16 χρωμάτων, όπως η οθόνη: το PNG μένει μικρό, και τα χρώματα
    είναι ακριβώς του CPC."""
    from PIL import Image
    img = Image.new("P", (len(pens[0]), len(pens)))
    rgb = palette.pen_rgb(MW.palette(PLANET))
    img.putpalette([v for c in rgb for v in c])
    img.putdata([p for row in pens for p in row])
    img = img.resize((img.width * 2 * SCALE, img.height * SCALE), Image.NEAREST)
    img.save(path, optimize=True)
    print(f"{path}: {img.width} x {img.height}, {os.path.getsize(path):,} bytes")


def banner(pens):
    """Το κομμάτι κάτω από τη στήλη της σελίδας, με τον τίτλο: pens ανά γραμμή. Το
    περίγραμμα γίνεται κλειστή πλάκα: το μενού έχει τρύπες ενός κελιού ανάμεσα
    στο I και στο T, και σκαλοπάτι στο τέλος, που σε αυτό το μέγεθος φαίνονται."""
    x0 = (-PAGE - X0) * 8
    out = [row[x0:x0 + PAGE * 16] for row in pens[:BANNER_ROWS * 16]]
    cells = MW.title_cells()
    used = [r for r in cells if any(r)]         # η πρώτη γραμμή του είναι κενή
    cols = max(c for r in used for c, v in enumerate(r) if v) + 1
    w = TITLE_W * 2                             # pens ανά κελί
    left = (len(out[0]) - cols * w) // 2
    assert left >= 0, "ο τίτλος δεν χωρά στο banner"
    for r, row in enumerate(used):
        for c, v in enumerate(row[:cols]):
            for y in range(TITLE_H):
                at = out[TITLE_TOP + r * TITLE_H + y]
                at[left + c * w:left + (c + 1) * w] = [6 if v == 2 else 0] * w
    return out


def main():
    pens = paint().to_pens()
    write(pens, OUT)
    write(banner(pens), OUT_BANNER)


if __name__ == "__main__":
    main()
