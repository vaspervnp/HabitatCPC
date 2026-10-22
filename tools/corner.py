"""Οι ΓΩΝΙΕΣ των διαδρόμων (βήμα 129, DESIGN §8.4): η στροφή διαγώνιος -> άξονας
με λοξή ένωση, όπως θα τη ζωγράφιζε κανείς με το χέρι.

Ο παίκτης: «θέλω γωνίες για τους διαδρόμους ώστε να φαίνονται σωστοί, αν δεν
είναι τελείως διαγώνιοι». Ως το βήμα 128 τα πλακίδια της στροφής κάθονταν το
ένα πάνω στο άλλο όπως τα έβαζε το πλέγμα (tools/route.py): στη στροφή προς
οριζόντιο ο οριζόντιος ξεκινούσε ένα tile πίσω και η διαγώνιος περνούσε από
κάτω του, στη στροφή προς κάθετο ο κάθετος ξεκινούσε μισό tile πιο πάνω από εκεί
που τον έβρισκε η διαγώνιος. Δύο κοτσάνια και μία ουρά σε κάθε στροφή.

ΤΟ ΣΧΗΜΑ ΟΡΙΖΕΤΑΙ ΕΔΩ, ΑΠΟ ΤΗ ΓΕΩΜΕΤΡΙΑ, όχι από τα πλακίδια. Σε «μονάδες»
(x_u = 2 x pixel, γιατί το pixel του Mode 0 είναι διπλό· y_u = γραμμή, κέντρο
pixel στο (2px + 1, ln + 0.5)), με το πάνω-αριστερά του ΤΕΛΕΥΤΑΙΟΥ διαγώνιου
πλακιδίου στο (0, 0) και διαγώνιο που κατεβαίνει δεξιά (νοτιοανατολικά):

  * η διαγώνια λωρίδα: τα pixels με κέντρο ως 6 μονάδες οριζόντια από την
    ευθεία x_u = y_u + 8 — αυτό ΕΙΝΑΙ το corr_dr, και το assert το ελέγχει·
  * η οριζόντια: οι γραμμές 4-11 (το corr_h στο corr_bend του scene)·
  * η κάθετη: τα pixels 14-17 (το corr_v στο byte 7).

Οι δύο άξονες τέμνονται στο J. Η ΓΡΑΜΜΗ ΤΗΣ ΕΝΩΣΗΣ περνά από το J και
διχοτομεί τη γωνία ανάμεσα στο «πίσω» της διαγωνίου και στο «μπρος» του
άξονα: από τη μία μεριά της κρατιέται μόνο η διαγώνιος, από την άλλη μόνο ο
άξονας. Το περίγραμμα (pen 5) είναι κάθε pixel του σχήματος με 4-γείτονα έξω
από αυτό, και το εσωτερικό γκρι (pen 4) — ο ίδιος κανόνας βγάζει ακριβώς και
τα τρία sprites, που είναι η απόδειξη ότι είναι ο κανόνας τους.

ΠΩΣ ΤΟ ΖΩΓΡΑΦΙΖΕΙ ΤΟ ΠΑΙΧΝΙΔΙ — με ό,τι ήδη ξέρει ο blitter, και ένα μικρό
μπάλωμα. Αναζητήθηκε η φθηνότερη συνταγή που δεν αφήνει κανένα pixel έξω από
το σχήμα (ένα «κοτσάνι» δεν σβήνεται με μάσκα· πρέπει να μη ζωγραφιστεί):

  * προς ΟΡΙΖΟΝΤΙΟ: το τελευταίο διαγώνιο μόνο οι 12 γραμμές του ως το κάτω
    χείλος της λωρίδας, το πρώτο οριζόντιο ΚΑΘΟΛΟΥ, και ένα byte μπάλωμα·
  * προς ΚΑΘΕΤΟ: όλα τα διαγώνια, το πρώτο κάθετο καθόλου, και ανάμεσά τους
    ένα σχέδιο 5 bytes x 8 γραμμές: η διαγώνιος ως τη λωρίδα και η ένωση.
    Ως πρώτη σκέψη ήταν ένα ακόμη διαγώνιο κομμένο στις 7 γραμμές του και ένα
    μπάλωμα 3 x 1· μετρημένο, ~520 µs ΠΑΡΑΠΑΝΩ ανά διάδρομο από ό,τι ως το
    βήμα 128 (το πλακίδιο είναι 8 bytes, όπου φαίνονται τα 5), ενώ το σχέδιο
    κοστίζει λιγότερο από το κάθετο πλακίδιο που αντικαθιστά.

Οι άλλες τρεις διαγώνιοι είναι καθρεφτίσματα: δυτικά οριζόντιο (px -> 15 - px
μέσα στο πλακίδιο των 16 pixels), βόρεια κάθετο (γραμμή -> 15 - γραμμή). Τα
σχέδια είναι αποθηκευμένα ανατολικά και δυτικά (spr_lines), γιατί το οριζόντιο
καθρέφτισμα του ob_blit θέλει τον πίνακα της τράπεζας 6 και τα σχέδια είναι
στην 5· το κάθετο (bit 1) το κάνει το ob_blit.
"""
import functools
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

H_ROWS = 12                 # προς οριζόντιο: το τελευταίο διαγώνιο, γραμμές 0-11
WIN = 24                    # μονάδες γύρω από το J όπου το σχήμα είναι της ένωσης

# Οι θέσεις των πλακιδίων γύρω από τη στροφή, σε (bytes, γραμμές) από το
# τελευταίο διαγώνιο, όπως τις βάζει το scene.corr_bend (νοτιοανατολικά).
H_FIRST = (0, 4)            # το πρώτο οριζόντιο· βήμα (4, 0)
V_FIRST = (7, 8)            # το πρώτο κάθετο· βήμα (0, 16)


@functools.lru_cache(maxsize=None)
def _sprite_px(name):
    """{(px, γραμμή): pen} των αδιαφανών pixels ενός sprite με μάσκα."""
    from sprites import load_map, load_bin
    from refrender import unpack_pens
    smap, blob = load_map(), load_bin()
    s = smap[name]
    out = {}
    for y in range(s.h):
        for b in range(s.w):
            m = blob[s.off + y * s.stride + 2 * b]
            v = blob[s.off + y * s.stride + 2 * b + 1]
            pv = unpack_pens(v)
            for k, bit in enumerate((0xAA, 0x55)):
                if not m & bit:
                    out[(2 * b + k, y)] = pv[k]
    return out


def _outline(inside, cells):
    """pen 5 όπου κάποιος 4-γείτονας είναι έξω, αλλιώς 4."""
    return {p: 5 if any(not inside(p[0] + dx, p[1] + dy)
                        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))) else 4
            for p in cells if inside(*p)}


def _in_d(px, ln):
    return abs(2 * px + 1 - (ln + 0.5) - 8) <= 6


def _in_h(px, ln):
    return 4 <= ln < 12


def _in_v(px, ln):
    return 14 <= px < 18


def check_bands():
    """Οι τρεις λωρίδες με τον κανόνα του περιγράμματος ΕΙΝΑΙ τα τρία sprites
    (μέσα σε ένα πλακίδιο: τα άκρα του πλακιδίου δεν είναι άκρα της λωρίδας)."""
    for name, inside, x0, y0, w, h in (("corr_dr", _in_d, 0, 0, 16, 16),
                                        ("corr_h", _in_h, 0, 4, 8, 8),
                                        ("corr_v", _in_v, 14, 8, 4, 16)):
        cells = [(x0 + x, y0 + y) for y in range(-2, h + 2) for x in range(-4, w + 4)]
        band = _outline(inside, cells)
        got = {(x - x0, y - y0): v for (x, y), v in band.items()
               if x0 <= x < x0 + w and y0 <= y < y0 + h}
        want = _sprite_px(name)
        assert got == want, f"η λωρίδα του {name} δεν είναι το sprite"


@functools.lru_cache(maxsize=None)
def mitre(kind):
    """Το σχήμα της ένωσης, {(px, γραμμή): pen}, νοτιοανατολική διαγώνιος που
    στρίβει ανατολικά ('h') ή νότια ('v'), και τα κελιά όπου ισχύει: όσα
    απέχουν ως WIN μονάδες από το J."""
    a = (1 / math.sqrt(2), 1 / math.sqrt(2))
    if kind == "h":
        inA, b = _in_h, (1, 0)
        J = (8 + 8, 8)                       # x_u = y_u + 8 στη γραμμή 8
    else:
        inA, b = _in_v, (0, 1)
        J = (32, 32 - 8)                     # x_u = 32 (pixels 14-17)
    m = (b[0] - a[0], b[1] - a[1])
    n = (-m[1], m[0])
    if n[0] * b[0] + n[1] * b[1] < 0:
        n = (-n[0], -n[1])

    def inside(px, ln):
        s = (2 * px + 1 - J[0]) * n[0] + (ln + 0.5 - J[1]) * n[1]
        return (s <= 0 and _in_d(px, ln)) or (s > 0 and inA(px, ln))
    cells = {(px, ln) for ln in range(int(J[1]) - WIN, int(J[1]) + WIN + 1)
             for px in range((J[0] - WIN) // 2, (J[0] + WIN) // 2 + 1)}
    if kind == "v":
        # ΜΟΝΟ ΩΣ ΤΟ ΤΕΛΟΣ ΤΟΥ ΠΡΩΤΟΥ ΚΑΘΕΤΟΥ: από τη γραμμή 24 η λωρίδα όπως
        # ήταν. Η ένωση θα έφτανε μία γραμμή ακόμη (το εξωτερικό χείλος της
        # διαγωνίου, pixel 13), και τότε, με ΕΝΑ κάθετο ως τον θόλο, θα έπεφτε
        # έξω από το κουτί του διαδρόμου στο ευρετήριο — κάτω από το κέλυφος,
        # αλλά όχι κάτω από την ερώτηση «ποιος είναι εδώ».
        cells = {c for c in cells if c[1] < V_FIRST[1] + 16}
    shape = _outline(inside, {c for c in cells if c[1] < V_FIRST[1] + 16} if kind == "v" else cells)
    return shape, cells


def _tiles(kind, extra_axial=4, back=3):
    """Τα πλακίδια γύρω από τη στροφή, όπως τα βάζει το σχέδιο ως το βήμα 128:
    [(όνομα, x bytes, y γραμμές)] — `back` διαγώνια ως το τελευταίο, και
    `extra_axial` αξονικά από το πρώτο."""
    t = [("corr_dr", -4 * k, -16 * k) for k in range(back, -1, -1)]
    if kind == "h":
        t += [("corr_h", H_FIRST[0] + 4 * j, H_FIRST[1]) for j in range(extra_axial)]
    else:
        t += [("corr_v", V_FIRST[0], V_FIRST[1] + 16 * j) for j in range(extra_axial)]
    return t


def _draw(tiles):
    out = {}
    for name, x, y, *rows in tiles:
        r0, r1 = rows if rows else (0, 99)
        for (px, ln), v in _sprite_px(name).items():
            if r0 <= ln < r1:
                out[(2 * x + px, y + ln)] = v
    return out


def recipe(kind):
    """Τα πλακίδια της συνταγής (χωρίς το μπάλωμα): (όνομα, x, y, r0, r1)."""
    t = _tiles(kind)
    nd = 4                                   # τα διαγώνια είναι τα πρώτα 4
    if kind == "h":
        diag = [d + (0, 16) for d in t[:nd - 1]] + [t[nd - 1] + (0, H_ROWS)]
        axial = [a + (0, 16) for a in t[nd + 1:]]
        return diag + axial
    diag = [d + (0, 16) for d in t[:nd]]
    axial = [a + (0, 16) for a in t[nd + 1:]]
    return diag + axial


@functools.lru_cache(maxsize=None)
def _goal(kind):
    """Το σχήμα που πρέπει να βγει: τα πλακίδια όπως ήταν, και μέσα στο WIN
    γύρω από το J η ένωση."""
    old = _draw(_tiles(kind))
    shape, cells = mitre(kind)
    goal = {p: v for p, v in old.items() if p not in cells}
    goal.update(shape)
    return goal


@functools.lru_cache(maxsize=None)
def patch(kind):
    """Το μπάλωμα: (x bytes, γραμμή, w, h, [(μάσκα, δεδομένα)] ανά γραμμή) από
    το πάνω-αριστερά του τελευταίου διαγώνιου, νοτιοανατολικά."""
    goal = _goal(kind)
    got = _draw(recipe(kind))
    stray = [p for p in got if p not in goal]
    assert not stray, f"η συνταγή {kind} ζωγραφίζει έξω από τη γωνία: {sorted(stray)[:4]}"
    diff = [p for p in goal if got.get(p) != goal[p]]
    x0 = min(p[0] for p in diff) // 2
    x1 = max(p[0] for p in diff) // 2 + 1
    y0 = min(p[1] for p in diff)
    y1 = max(p[1] for p in diff) + 1
    rows = []
    for ln in range(y0, y1):
        row = []
        for b in range(x0, x1):
            m, d = 0xFF, 0
            for k, bit in enumerate((0xAA, 0x55)):
                p = (2 * b + k, ln)
                if p in goal:
                    m &= ~bit & 0xFF
                    d |= _pen_bits(goal[p]) & bit
            row.append((m, d))
        rows.append(row)
    return x0, y0, x1 - x0, y1 - y0, rows


def _pen_bits(p):
    """Τα bits ενός pen και για τα δύο pixels του byte (Mode 0)."""
    left = ((p & 1) << 7) | ((p & 2) << 2) | ((p & 4) << 3) | ((p & 8) >> 2)
    return left | (left >> 1)


@functools.lru_cache(maxsize=None)
def place(kind, d0):
    """(dx bytes, dy γραμμές, προσανατολισμός) του μπαλώματος από το τελευταίο
    διαγώνιο, για τη διαγώνιο d0 (1 βα, 3 να, 5 νδ, 7 βδ)."""
    x0, y0, w, h, _ = patch(kind)
    west, north = d0 in (5, 7), d0 in (1, 7)
    x = 8 - x0 - w if west else x0
    y = 16 - y0 - h if north else y0
    return x, y, (1 if west else 0) | (2 if north else 0)


def first(kind, d0):
    """(dx bytes, dy γραμμές) του ΠΡΩΤΟΥ αξονικού πλακιδίου από το τελευταίο
    διαγώνιο, όπως το βάζει το oc_bend (src/object.asm): οριζόντια
    (dx < 0 ? 4 : 0, 4), κάθετα (dx + 3, dy / 2). Από αυτό μετρά το
    src/corner.asm (cn_pos), γιατί αυτό έχει το cn_post στο ob_x, ob_y."""
    west, north = d0 in (5, 7), d0 in (1, 7)
    if kind == "h":
        return (4 if west else 0), 4
    return (-1 if west else 7), (-8 if north else 8)


@functools.lru_cache(maxsize=None)
def pixels(kind, d0):
    """Τα pixels του μπαλώματος στη θέση του, {(px, γραμμή): pen} από το
    τελευταίο διαγώνιο — για το tools/scene.py."""
    goal = _goal(kind)
    x0, y0, w, h, _ = patch(kind)
    west, north = d0 in (5, 7), d0 in (1, 7)
    out = {}
    for (px, ln), v in goal.items():
        if 2 * x0 <= px < 2 * (x0 + w) and y0 <= ln < y0 + h:
            out[(15 - px if west else px, 15 - ln if north else ln)] = v
    return out


def asm_lines():
    """Οι σταθερές για το src/corner.asm (b6code): θέσεις και διαστάσεις."""
    out = ["; ΠΑΡΑΓΕΤΑΙ από tools/pack.py (tools/corner.py) — μην το επεξεργάζεσαι.",
           "; Οι γωνίες (βήμα 129): x, y από το τελευταίο διαγώνιο, w, h, νοτιοανατολικά."]
    for kind in ("h", "v"):
        x0, y0, w, h, rows = patch(kind)
        for k, v in (("X", x0), ("Y", y0), ("W", w), ("H", h)):
            out.append(f"CN_{kind.upper()}{k} equ {v}")
    out.append(f"CN_HROWS equ {H_ROWS}")
    return out


def spr_data():
    """Τα σχέδια των γωνιών, ανά είδος ανατολικό και δυτικό, ήδη καθρεφτισμένο —
    ο οριζόντιος καθρεφτισμός του ob_blit θέλει το flip_mode0, και στο 5 x 8 της
    κάθετης κόστιζε ~250 µs· το κάθετο καθρέφτισμα (βόρεια) το κάνει το ob_blit.
    -> (bytes, [(ετικέτα, μετατόπιση)], [(είδος, w * h * 2)])."""
    from refrender import flip_byte
    data, labels, sizes = bytearray(), [], []
    for kind in ("h", "v"):
        rows = patch(kind)[4]
        for name, rr in ((f"cn_{kind}pat", rows),
                         (f"cn_{kind}patw", [[(flip_byte(m), flip_byte(d)) for m, d in reversed(r)]
                                             for r in rows])):
            labels.append((name, len(data)))
            for row in rr:
                for m, d in row:
                    data += bytes([m, d])
        x0, y0, w, h, _ = patch(kind)
        sizes.append((kind, w * h * 2))
    return bytes(data), labels, sizes


def spr_lines():
    """Οι ετικέτες των σχεδίων (build/corner_spr.asm): ΣΤΗΝ ΤΡΑΠΕΖΑ 6 από το
    βήμα 159, στο τέλος της (G_corner_spr, tools/pack.py), όπου τα γράφει το
    pack.py ως δεδομένα· ως τότε στη δέσμευση b5code της τράπεζας 5, που την
    πήραν οι 128 διάδρομοι. Τα ζωγραφίζει το ob_put_in με την 6 μέσα
    (src/corner.asm)."""
    _, labels, sizes = spr_data()
    out = ["; ΠΑΡΑΓΕΤΑΙ από tools/pack.py (tools/corner.py) — μην το επεξεργάζεσαι.",
           "; Τα σχέδια των γωνιών (βήμα 129), με μάσκα: νοτιοανατολικά και",
           "; νοτιοδυτικά· βόρεια με το κάθετο καθρέφτισμα του ob_blit. Τα bytes",
           "; είναι στην τράπεζα 6, στο G_corner_spr (βήμα 159· στην 5 ως το 158)."]
    for name, off in labels:
        out.append(f"{name:<11} equ G_corner_spr + {off}")
    for kind, n in sizes:
        out.append(f"        assert  cn_{kind}patw == cn_{kind}pat + {n}"
                   f"   ; το δυτικό αμέσως μετά (src/corner.asm)")
    return out


if __name__ == "__main__":
    check_bands()
    for kind in ("h", "v"):
        print(kind, patch(kind)[:4], [place(kind, d) for d in (1, 3, 5, 7)])
    print("\n".join(asm_lines()))
    print("\n".join(spr_lines()))
