"""Η ΑΝΑΦΟΡΑ του περάσματος αντικειμένων (DESIGN §8.4, SPRITES.md §10).

Γράφτηκε από την πρόζα, όχι από τον Z80: όταν τα δύο συμφωνούν byte προς byte,
συμφωνούν και τα δύο με την προδιαγραφή.

Η σειρά σχεδίασης είναι του SPRITES.md §10, με τη διόρθωση του §8.4 για τους
διαδρόμους. ΑΠΟ ΤΟ ΒΗΜΑ 96 ΚΑΤΩ ΑΠΟ ΤΟΥΣ ΘΟΛΟΥΣ, και χωρίς πόρτες: ο διάδρομος
σταματά στο εξωτερικό χείλος του δακτυλίου (ο παίκτης· ως το 95 το `conn_{dir}`
άνοιγε τον δακτύλιο ως τον εσωτερικό κύκλο, και οι διάδρομοι ήταν από πάνω):

    1. διάδρομοι                                (μάσκα)
    2. δακτύλιοι + θόλοι όλων των θόλων        (μάσκα)
    3. ανά θόλο: αρμοί, εικονίδιο, μηχανές/φυτά, φιγούρες
    4. εξωτερικές δομές, ταξινομημένες κατά cy

ΟΙ ΑΡΜΟΙ (βήμα 96, ο παίκτης: «να μπαίνουν 1 pixel πιο μέσα»): δες το joint().

ΘΕΣΗ: κάθε αντικείμενο κρατά το ΚΕΝΤΡΟ του σε μισά tiles (§3.4). Η οθόνη
βγαίνει με δύο ολισθήσεις ανά άξονα και καμία διαίρεση:

    sx = 2*cx - 4*cam_tx - w/2          (bytes)
    sy = 8*cy - 16*cam_ty - h/2         (γραμμές)
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sprites import load_map, load_bin
from refrender import Canvas, quad_rows, SCR_W, SCR_H
import corner

# --- εγγραφές, ίδιες με τον Z80 -------------------------------------------
DOME_REC = 24
D_CX, D_CY, D_SIZE, D_ROOM, D_STATE, D_INTEG, D_POWER, D_OPS = range(8)
D_MACH, D_HEALTH = 8, 16

STRUCT_REC = 8
S_CX, S_CY, S_KIND, S_SIZE, S_STATE, S_INTEG, S_OUT = range(7)

CORR_REC = 5
C_A, C_B, C_DIR, C_LEN, C_STATE = range(5)

MAX_DOME, MAX_STRUCT, MAX_CORR = 64, 32, 96
DS_EMPTY, DS_BUILDING, DS_ACTIVE = 0, 1, 2

SIZES = ("s", "m", "l")
ROOMS = ["empty", "control", "quarters", "canteen", "oxygen", "greenhouse",
         "storage", "airlock", "factory", "lab", "medbay", "lounge"]
MACH = ["oxygen", "iron", "bioplastic", "weapons", "processors", "robots",
        "food", "spares", "medical", "vitromeat", "beds", "medstore"]
PLANTS = ["peas", "rice", "potatoes", "wheat", "maize", "tomatoes", "lettuce",
          "onions", "radishes", "mushrooms", "medicinal", "tree"]
STRUCT_KINDS = ["solar", "turbine", "collector", "extractor",
                "mine", "airlock", "pad", "ship"]
DIRS = ["n", "ne", "e", "se", "s", "sw", "w", "nw"]
R_GREENHOUSE = 5
NO_MACH = 255
NO_SLOT = 255

VIEW_TW, VIEW_TH = 20, 10
PLAY_LINES = 160

# Ο ρόλος της προσομοίωσης -> η φιγούρα της τέχνης (SPRITES.md §7).
#
# Δεν είναι ταυτοτικό και δεν μπορεί να είναι: η τέχνη έχει τέσσερα ρομπότ
# (carrier, driller, engineer, constructor) και η προσομοίωση τρία, με τον
# ΜΗΧΑΝΙΚΟ ΑΝΘΡΩΠΟ. Ο μηχανικός παίρνει τη φιγούρα 7 — αυτήν που η τέχνη
# ονομάζει «ρομπότ engineer» — επειδή σε 6x6 pixel το χρώμα είναι η ταυτότητα
# και το κυανό είναι ήδη «αυτός που φτιάχνει πράγματα».
#         0 worker 1 engineer 2 biologist 3 medic 4 guard
#         5 bot_constr 6 bot_carry 7 bot_drill
ROLE_FIG = [1, 7, 2, 3, 4, 8, 5, 6]

# Το μέγεθος ενός διαδρόμου ανά κατεύθυνση: (sprite, βήμα x σε bytes, βήμα y).
# Ο διάδρομος ΔΕΝ έχει τέσσερις προσανατολισμούς — έχει τέσσερα sprites και
# οκτώ φορές. Το `dir & 3` διαλέγει το sprite:
#     n,s -> corr_v   ne,sw -> corr_dl   e,w -> corr_h   se,nw -> corr_dr
CORR_SPR = ["corr_v", "corr_dl", "corr_h", "corr_dr"]
CORR_STEP = [(0, -16), (4, -16), (4, 0), (4, 16),
             (0, 16), (-4, 16), (-4, 0), (-4, -16)]

# Το ΠΛΕΓΜΑ της διαγωνίου. Το βήμα (4 bytes, 16 γραμμές) είναι ένα tile και
# στους δύο άξονες, άρα δύο θόλοι σε διαγώνιο SPACING μοιράζονται ΤΟ ΙΔΙΟ
# πλέγμα: το πλακίδιο βήματος k έχει το ΚΕΝΤΡΟ του στο (4k, ±16k) από το
# κέντρο του θόλου, και το πάνω-αριστερά του στο (4k-4, ±16k-8).
#
# Το DIAG_K λέει από ποιο βήμα ξεκινά ο διάδρομος ανά μέγεθος. Δεν βγαίνει από
# τύπο: το βήμα είναι 16 γραμμές ενώ η ακτίνα στη διαγώνιο (r/sqrt2) είναι
# 17/28/40 — ποτέ πολλαπλάσιο. Ο πίνακας διαλέχτηκε ΚΟΙΤΑΖΟΝΤΑΣ, με κανόνα
# «καλύτερα λίγη επικάλυψη πάνω στον δακτύλιο παρά κενό»: το γκρι του
# διαδρόμου και το γκρι του δακτυλίου είναι το ίδιο γκρι.
DIAG_K = [2, 3, 3]



class Assets:
    """Ο,τι διαβάζει ο renderer από τα assets, μία φορά."""

    def __init__(self):
        self.smap, self.blob = load_map(), load_bin()
        t = self._tab
        self.conn_points = t("conn_points")
        self.corr_slots = t("corr_slots")
        self.corr_fill = t("corr_fill")
        self.machine_slots = t("machine_slots")
        self.machine_count = t("machine_count")
        self.interior_ofs = t("interior_ofs")
        self.struct_dims = t("struct_dims")
        for k in range(4):              # όπως το tools/pack.py από το βήμα 151:
            self.struct_dims[k * 8:k * 8 + 4] = [0, 0, 0, 0]    # μόνο το l
        self.palette_fw = t("palette_fw")

    def _tab(self, name):
        s = self.smap[name]
        return list(self.blob[s.off:s.off + s.size])

    def rows(self, name):
        """Ενα sprite ως λίστα γραμμών, όπως είναι αποθηκευμένο."""
        s = self.smap[name]
        return [self.blob[s.off + y * s.stride: s.off + (y + 1) * s.stride]
                for y in range(s.h)]

    def dims(self, name):
        s = self.smap[name]
        return s.w, s.h


def signed(b):
    return b - 256 if b > 127 else b


class Colony:
    """Οι τρεις πίνακες της τράπεζας 6, ακριβώς όπως τους βλέπει ο Z80."""

    def __init__(self):
        self.dome = bytearray(MAX_DOME * DOME_REC)
        self.struct = bytearray(MAX_STRUCT * STRUCT_REC)
        self.corr = bytearray(MAX_CORR * CORR_REC)
        self.n_dome = self.n_struct = self.n_corr = 0

    # --- πρόσβαση ---------------------------------------------------------
    def d(self, i, f):
        return self.dome[i * DOME_REC + f]

    def s(self, i, f):
        return self.struct[i * STRUCT_REC + f]

    def c(self, i, f):
        return self.corr[i * CORR_REC + f]


class Camera:
    """Πάνω-αριστερά ορατό tile, και το offset του CRTC που του αντιστοιχεί."""

    def __init__(self, tx=0, ty=0):
        self.tx, self.ty = tx, ty

    @property
    def off(self):
        """Λέξεις offset του CRTC. Το tile (-64,-64) είναι το offset 0."""
        return ((self.tx + 64) * 2 + (self.ty + 64) * 80) & 0x3FF

    def sx(self, hx):
        return 2 * hx - 4 * self.tx

    def sy(self, hy):
        return 8 * hy - 16 * self.ty


class Clip:
    """Το ορθογώνιο μέσα στο οποίο επιτρέπεται να γραφτεί pixel.

    Είναι ο ΙΔΙΟΣ μηχανισμός με το σκρολάρισμα: μια στήλη που μόλις μπήκε στο
    κάδρο σχεδιάζεται ξαναπερνώντας ΟΛΑ τα αντικείμενα με clip τη στήλη, οπότε
    ένας μεγάλος θόλος κοστίζει το ένα όγδοο του εαυτού του αντί για ολόκληρο.
    """

    def __init__(self, x0=0, y0=0, x1=SCR_W, y1=PLAY_LINES):
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1

    def empty(self):
        return self.x0 >= self.x1 or self.y0 >= self.y1


def mark_rows(k):
    """Το σήμα k των μηχανών (0 χαλασμένη, 1 περιμένει), όπως το γράφει το
    tools/pack.py στην τράπεζα 5: αδιαφανές, MARK_W bytes x MARK_H γραμμές."""
    import pack
    data = pack.marks()
    n = pack.MARK_W * pack.MARK_H
    return [data[k * n + y * pack.MARK_W:k * n + (y + 1) * pack.MARK_W]
            for y in range(pack.MARK_H)]


def blit(canvas, rows, x, y, masked, clip):
    """Ενα sprite με clip. Το `rows` είναι ήδη στον σωστό προσανατολισμό."""
    w = len(rows[0]) // (2 if masked else 1)
    h = len(rows)
    for dy in range(h):
        ty = y + dy
        if not (clip.y0 <= ty < clip.y1):
            continue
        row = rows[dy]
        for dx in range(w):
            tx = x + dx
            if not (clip.x0 <= tx < clip.x1):
                continue
            o = ty * SCR_W + tx
            if masked:
                canvas.buf[o] = (canvas.buf[o] & row[2 * dx]) | row[2 * dx + 1]
            else:
                canvas.buf[o] = row[dx]


def frame_of(a, colony, d):
    """(fx, fy, QW, QH) του πλαισίου ενός θόλου, σε συντεταγμένες οθόνης."""
    raise NotImplementedError


# --- ένας θόλος -----------------------------------------------------------

def dome_frame(a, cam, colony, d):
    sz = colony.d(d, D_SIZE)
    qw, qh = a.dims(f"dome_{SIZES[sz]}_nw")
    fx = cam.sx(signed(colony.d(d, D_CX))) - qw
    fy = cam.sy(signed(colony.d(d, D_CY))) - qh
    return fx, fy, qw, qh, sz


def draw_shell(canvas, a, cam, colony, d, clip):
    """Βήματα 1-2: δακτύλιος και θόλος, από το ένα αποθηκευμένο nw."""
    fx, fy, qw, qh, sz = dome_frame(a, cam, colony, d)
    for stem in ("ring", "dome"):
        spr = a.smap[f"{stem}_{SIZES[sz]}_nw"]
        for orient, (ox, oy) in (("nw", (0, 0)), ("ne", (qw, 0)),
                                 ("sw", (0, qh)), ("se", (qw, qh))):
            blit(canvas, quad_rows(a.blob, spr, orient),
                 fx + ox, fy + oy, True, clip)


def draw_fittings(canvas, a, cam, colony, d, clip, agents=None):
    """Βήματα 3-6: αρμοί (ως το 95 οι πόρτες), εικονίδιο, μηχανές ή φυτά, φιγούρες."""
    fx, fy, qw, qh, sz = dome_frame(a, cam, colony, d)

    px = [joint(a, sz, dr) for dr in sorted(dome_dirs(colony, d))]
    px += [bend(a, sz, k) for k in sorted(dome_bends(colony, d))]
    for j in px:
        for (x, y), bits in j.items():
            tx, ty = fx + x // 2, fy + y
            if clip.x0 <= tx < clip.x1 and clip.y0 <= ty < clip.y1:
                o = ty * SCR_W + tx
                canvas.buf[o] = (canvas.buf[o] & ~PIX[x & 1] & 255) | bits

    # Το εργοτάξιο είναι άδειο: κενό εικονίδιο, καμία μηχανή — βλ. ob_fittings
    # στο src/object.asm. Τα μηχανήματα υπάρχουν ήδη στην εγγραφή από την ώρα
    # της τοποθέτησης· απλώς δεν φαίνονται ως να χτιστεί ο θόλος.
    site = colony.d(d, D_STATE) != DS_ACTIVE
    room = 0 if site else colony.d(d, D_ROOM)
    ix = signed(a.interior_ofs[sz * 2])
    iy = signed(a.interior_ofs[sz * 2 + 1])
    icon = f"icon_{SIZES[sz]}_{ROOMS[room]}"
    iw, ih = a.dims(icon)
    blit(canvas, a.rows(icon), fx + qw + ix, fy + qh + iy, False, clip)

    green = room == R_GREENHOUSE
    for s in range(0 if site else a.machine_count[sz]):
        m = colony.d(d, D_MACH + s)
        if m == NO_MACH:
            continue
        px = a.machine_slots[sz * 16 + s * 2]
        py = a.machine_slots[sz * 16 + s * 2 + 1]
        if px == 255:
            continue
        name = f"plant_{PLANTS[m]}" if green else f"mach_{MACH[m]}"
        blit(canvas, a.rows(name), fx + px, fy + py, False, clip)
        # ΤΟ ΣΗΜΑ (βήμα 100, ob_mach_one): πάνω αριστερά, αν δεν δουλεύει —
        # χαλασμένη ή μαραμένο φυτό (0), ή περιμένει να στηθεί (1-127).
        hp = colony.d(d, D_HEALTH + s)
        if not hp & 0x80:
            blit(canvas, mark_rows(0 if hp == 0 else 1), fx + px, fy + py, False, clip)

    if agents is None:
        return
    for slot, fig in agents.get(d, {}).items():
        px = a.corr_slots[sz * 16 + slot * 2]
        py = a.corr_slots[sz * 16 + slot * 2 + 1]
        blit(canvas, a.rows(f"slot_{SIZES[sz]}_{slot}_{FIG_NAMES[fig]}"),
             fx + px, fy + py, False, clip)


FIG_NAMES = ["empty", "colonist", "biologist", "medic", "guard",
             "carrier", "driller", "engineer", "constructor"]


# --- διάδρομοι ------------------------------------------------------------

def draw_corridor(canvas, a, cam, colony, i, clip):
    d = colony.c(i, C_A)
    if d == 255:
        return              # ΣΥΝΕΧΕΙΑ: τη ζωγραφίζει η εγγραφή που την ξεκίνησε
    dr = colony.c(i, C_DIR)
    n = colony.c(i, C_LEN)
    if not n:
        return              # ούτε η συνέχεια
    fx, fy, qw, qh, sz = dome_frame(a, cam, colony, d)
    px = a.conn_points[sz * 16 + dr * 2]
    py = a.conn_points[sz * 16 + dr * 2 + 1]
    x, y = corr_origin(fx + px, fy + py, dr, qw, qh, fx, fy, sz)
    sx, sy = CORR_STEP[dr]
    rows = a.rows(CORR_SPR[dr & 3])
    j = i + 1
    cont = j < MAX_CORR and colony.c(j, C_A) == 255 and colony.c(j, C_STATE) != DS_EMPTY
    d1 = colony.c(j, C_DIR) if cont else None
    horiz = cont and d1 in (2, 6)
    for k in range(n):
        if horiz and k == n - 1:
            # Η ΓΩΝΙΑ (βήμα 129, tools/corner.py): το τελευταίο διαγώνιο ως το
            # κάτω χείλος της οριζόντιας λωρίδας — ή από το πάνω, βόρεια.
            h = corner.H_ROWS
            if sy > 0:
                blit(canvas, rows[:h], x, y, True, clip)
            else:
                blit(canvas, rows[16 - h:], x, y + 16 - h, True, clip)
        else:
            blit(canvas, rows, x, y, True, clip)
        lastx, lasty = x, y
        x += sx
        y += sy
    if not cont:
        return
    x, y = corr_bend(lastx, lasty, sx, sy, d1)
    vx, vy = CORR_STEP[d1]
    rows = a.rows(CORR_SPR[d1 & 3])
    x += vx                                 # το πρώτο αξονικό το σκεπάζει η γωνία
    y += vy
    for _ in range(colony.c(j, C_LEN) - 1):
        blit(canvas, rows, x, y, True, clip)
        x += vx
        y += vy
    # το μπάλωμα της ένωσης, πάνω από όλα του διαδρόμου — προς κάθετο το
    # σχέδιο της γωνίας ολόκληρο, ανάμεσα στη διαγώνιο και στο δεύτερο κάθετο
    kind = "h" if horiz else "v"
    px, py, orient = corner.place(kind, dr)
    blit(canvas, corner_rows(kind, orient), lastx + px, lasty + py, True, clip)


def corner_rows(kind, orient):
    """Το μπάλωμα της γωνίας στον προσανατολισμό orient (bit 0 οριζόντια, bit
    1 κάθετα), όπως το καθρεφτίζει το ob_blit: τα ζεύγη ανάποδα και κάθε byte
    με τα δύο του pixels αλλαγμένα."""
    from refrender import flip_byte
    _, _, w, h, rows = corner.patch(kind)
    raw = [bytes(b for m, d in row for b in (m, d)) for row in rows]
    if orient & 2:
        raw = raw[::-1]
    if orient & 1:
        raw = [bytes(b for i in range(len(r) - 2, -1, -2)
                     for b in (flip_byte(r[i]), flip_byte(r[i + 1]))) for r in raw]
    return raw


PIX = (0xAA, 0x55)                      # τα bits του αριστερού και του δεξιού pixel
N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))


def dome_dirs(colony, d):
    """Ποιες κατευθύνσεις του θόλου έχουν διάδρομο (το dome_conn του Z80)."""
    out = set()
    for i in range(colony.n_corr):
        if colony.c(i, C_STATE) == DS_EMPTY:
            continue
        a_, b_, dr = colony.c(i, C_A), colony.c(i, C_B), colony.c(i, C_DIR)
        if a_ == d:
            out.add(dr & 7)
        if b_ == d:
            # Ο b παίρνει τον αρμό του ΤΕΛΕΥΤΑΙΟΥ τρεξίματος: μια διαδρομή με
            # στροφή συνεχίζει στην επόμενη εγγραφή (C_A = 255, §9.4) και
            # φτάνει στον b με τη δική της κατεύθυνση.
            if i + 1 < MAX_CORR and colony.c(i + 1, C_A) == 255 \
                    and colony.c(i + 1, C_STATE) != DS_EMPTY:
                dr = colony.c(i + 1, C_DIR)
            out.add((dr + 4) & 7)
    return out


def dome_bends(colony, d):
    """Οι ΚΟΝΤΕΣ ΣΤΡΟΦΕΣ του θόλου (βήμα 97): διάδρομοι που φτάνουν σε αυτόν
    με ΕΝΑ tile μετά τη στροφή. Για καθέναν η πλευρά k (1 βα, 3 να, 5 νδ, 7
    βδ) όπου βρίσκεται η διαγώνιος, η αντίθετη της φοράς της — οριζόντια.
    ΚΑΙ ΚΑΘΕΤΑ από το βήμα 129, με τις γωνίες: τότε k - 1 (0, 2, 4, 6)."""
    out = set()
    for i in range(colony.n_corr - 1):
        if colony.c(i, C_STATE) == DS_EMPTY or colony.c(i, C_B) != d:
            continue
        j = i + 1
        if colony.c(j, C_A) == 255 and colony.c(j, C_STATE) != DS_EMPTY \
                and colony.c(j, C_LEN) == 1:
            k = (colony.c(i, C_DIR) + 4) & 7
            out.add(k if colony.c(j, C_DIR) in (2, 6) else k - 1)
    return out


_JOINT = {}


def joint(a, sz, dr):
    """Ο ΑΡΜΟΣ ενός θόλου μεγέθους sz στην κατεύθυνση dr (βήμα 96): {(pixel x,
    γραμμή) στο πλαίσιο: τα bits του pixel}. Ζωγραφίζεται μετά το κέλυφος.

    Από τη ΣΧΕΔΙΑΣΗ ενός θόλου μόνου του και ενός διαδρόμου 3 πλακιδίων μόνου
    του (με αυτό εδώ το module), όχι από πίνακα:
      * το κενό της διαγωνίου — τα pixels του πλακιδίου ΕΝΑ ΒΗΜΑ ΠΡΙΝ από το
        πρώτο (DIAG_K - 1) που φαίνονται: μέσα στο πλαίσιο, όχι κάτω από το
        κέλυφος ή κάτω από τον διάδρομο. Ως το 95 το έκλεινε η διαγώνια πόρτα·
      * το ένα pixel μέσα — τα pixels του εξωτερικού περιγράμματος του
        κελύφους (αδιαφανή, με 4-γείτονα διάφανο) που ακουμπούν 4-γειτονικά
        ένα γκρι pixel του διαδρόμου που φαίνεται: γίνονται γκρι, το γκρι του
        εσωτερικού του corr_h.
    """
    key = (sz, dr)
    if key in _JOINT:
        return _JOINT[key]
    c = Colony()
    c.n_dome, c.n_corr = 1, 1
    c.dome[D_CX], c.dome[D_CY], c.dome[D_SIZE] = 20, 12, sz
    c.dome[D_STATE] = DS_ACTIVE
    c.corr[0:CORR_REC] = bytes([0, 1, dr, 3, DS_ACTIVE])
    cam, clip = Camera(0, 0), Clip(0, 0, SCR_W, SCR_H)
    fx, fy, qw, qh, _ = dome_frame(a, cam, c, 0)

    def opaque(fn):
        bufs = []
        for bg in (0x00, 0xFF):
            cv = Canvas()
            cv.buf[:] = bytes([bg]) * len(cv.buf)
            fn(cv)
            bufs.append(cv.buf)
        A, B = bufs
        return {(o % SCR_W * 2 + p, o // SCR_W): A[o] & PIX[p]
                for o in range(len(A)) for p in (0, 1)
                if A[o] & PIX[p] == B[o] & PIX[p]}
    shell = opaque(lambda cv: draw_shell(cv, a, cam, c, 0, clip))
    run = opaque(lambda cv: draw_corridor(cv, a, cam, c, 0, clip))
    vis = {p: v for p, v in run.items() if p not in shell}
    out = {}
    if dr & 1:
        sx, sy = CORR_STEP[dr]
        x, y = corr_origin(0, 0, dr, qw, qh, fx, fy, sz)
        rows = a.rows(CORR_SPR[dr & 3])
        prev = opaque(lambda cv: blit(cv, rows, x - sx, y - sy, True, clip))
        for p, v in prev.items():
            if p not in shell and p not in run and 0 <= p[0] - 2 * fx < 4 * qw \
                    and 0 <= p[1] - fy < 2 * qh:
                out[p] = v
        vis.update(out)
    grey = a.rows("corr_h")[3][3]                   # γραμμή 3, byte 1: το εσωτερικό
    for p in shell:
        if not any((p[0] + dx, p[1] + dy) not in shell for dx, dy in N4):
            continue
        for dx, dy in N4:
            q = (p[0] + dx, p[1] + dy)
            if q in vis and vis[q] == grey & PIX[q[0] & 1]:
                out[p] = grey & PIX[p[0] & 1]
    _JOINT[key] = {(x - 2 * fx, y - fy): v for (x, y), v in out.items()}
    return _JOINT[key]


_BEND = {}


def _outline_px(a, c, d, run_corr, cam, clip):
    """Τα pixels του περιγράμματος του κελύφους d που ακουμπούν γκρι ορατού
    διαδρόμου, {(x, γραμμή) στο πλαίσιο: bits} — ο κανόνας του αρμού."""
    def opaque(fn):
        bufs = []
        for bg in (0x00, 0xFF):
            cv = Canvas()
            cv.buf[:] = bytes([bg]) * len(cv.buf)
            fn(cv)
            bufs.append(cv.buf)
        A, B = bufs
        return {(o % SCR_W * 2 + p, o // SCR_W): A[o] & PIX[p]
                for o in range(len(A)) for p in (0, 1)
                if A[o] & PIX[p] == B[o] & PIX[p]}
    fx, fy, qw, qh, _ = dome_frame(a, cam, c, d)
    shell = opaque(lambda cv: draw_shell(cv, a, cam, c, d, clip))
    shells = opaque(lambda cv: [draw_shell(cv, a, cam, c, e, clip)
                                for e in range(c.n_dome)])
    run = opaque(lambda cv: [draw_corridor(cv, a, cam, c, i, clip)
                             for i in run_corr])
    vis = {p: v for p, v in run.items() if p not in shells}
    grey = a.rows("corr_h")[3][3]
    out = {}
    for p in shell:
        if not any((p[0] + dx, p[1] + dy) not in shell for dx, dy in N4):
            continue
        for dx, dy in N4:
            q = (p[0] + dx, p[1] + dy)
            if q in vis and vis[q] == grey & PIX[q[0] & 1]:
                out[(p[0] - 2 * fx, p[1] - fy)] = grey & PIX[p[0] & 1]
    return out


def bend(a, sz, k):
    """Ο ΑΡΜΟΣ ΜΙΑΣ ΚΟΝΤΗΣ ΣΤΡΟΦΗΣ (βήμα 97): {(pixel x, γραμμή) στο πλαίσιο:
    bits}, πάνω από το κέλυφος, μαζί με τους άλλους αρμούς.

    Ο διάδρομος φτάνει στον θόλο ΟΡΙΖΟΝΤΙΑ με ένα μόνο tile μετά τη στροφή
    (dome_bends), και η διαγώνιος του, από την πλευρά k, ακουμπά τον δακτύλιο
    δίπλα στον αρμό του οριζόντιου (joint). Ο κανόνας είναι ο ίδιος: τα pixels
    του εξωτερικού περιγράμματος που ακουμπούν γκρι του διαδρόμου γίνονται
    γκρι. Εδώ είναι όσα από αυτά ΔΕΝ είναι ήδη του joint().

    Από τη ΣΧΕΔΙΑΣΗ, όπως το joint(): ένας θόλος μεγέθους sz στο (40, 30) και
    ένας μικρός από όπου το route.plan βγάζει τέτοια διαδρομή, με τον ίδιο τον
    διάδρομο και τα δύο κελύφη. Στις άλλες γεωμετρίες (μακρύτερος) δεν μένει
    κανένα pixel έξω από το joint() — μετρημένο σε όλες τις θέσεις ως 12 tiles
    (βήμα 97).

    ΑΠΟ ΤΟ ΒΗΜΑ 129, ΜΕ ΤΙΣ ΓΩΝΙΕΣ, δύο pixels οριζόντια (το ένα του 97 και
    το διπλανό του προς τον αρμό) και ένα ΚΑΘΕΤΑ, δίπλα στον αρμό του κάθετου:
    η γωνία ακουμπά τον δακτύλιο εκεί όπου ως τότε τον ακουμπούσε το πρώτο
    αξονικό. Το k είναι τότε ζυγό, η πλευρά της διαγωνίου μείον ένα
    (dome_bends).
    """
    key = (sz, k)
    if key in _BEND:
        return _BEND[key]
    import route
    tx, ty = 40, 30
    axial = (2, 6) if k & 1 else (0, 4)     # μονό: οριζόντια· ζυγό: κάθετα (129)
    side = k | 1
    for dy in range(-30, 31):
        for dx in range(-60, 61):
            p = route.plan(tx + dx, ty + dy, 0, tx, ty, sz)
            if p is None or p[0] != 0 or len(p[1]) != 2:
                continue
            (d0, _), (d1, n1) = p[1]
            if n1 == 1 and d1 in axial and (d0 + 4) & 7 == side:
                break
        else:
            continue
        break
    else:
        raise ValueError(f"καμία κοντή στροφή για το ({sz}, {k})")
    c = Colony()
    c.n_dome, c.n_corr = 2, 2
    for i, (cx, cy, s) in enumerate(((tx + dx, ty + dy, 0), (tx, ty, sz))):
        b = i * DOME_REC
        c.dome[b + D_CX], c.dome[b + D_CY] = cx & 255, cy & 255
        c.dome[b + D_SIZE], c.dome[b + D_STATE] = s, DS_ACTIVE
    (d0, n0), (d1, n1) = p[1]
    c.corr[0:2 * CORR_REC] = bytes([0, 1, d0, n0, DS_ACTIVE,
                                    255, 255, d1, n1, DS_ACTIVE])
    cam = Camera((2 * tx - 40) // 4, (8 * ty - 100) // 16)
    need = _outline_px(a, c, 1, (0,), cam, Clip(0, 0, SCR_W, SCR_H))
    have = joint(a, sz, (d1 + 4) & 7)
    _BEND[key] = {p_: v for p_, v in need.items() if have.get(p_) != v}
    return _BEND[key]


def corr_bend(lastx, lasty, sx, sy, d1):
    """Πάνω-αριστερά του πρώτου πλακιδίου ΜΕΤΑ τη στροφή (§9.4).

    Το διαγώνιο πλακίδιο είναι δύο tiles φαρδύ και ένα ψηλό, με το σημείο
    πλέγματός του στο πάνω-αριστερά + (4, 8). Η οριζόντια λωρίδα πιάνει το
    ΠΑΝΩ μισό της σειράς της και η κάθετη το ΑΡΙΣΤΕΡΟ μισό της στήλης της —
    γι' αυτό οι δύο στροφές δεν έχουν τον ίδιο τύπο. Τα δύο σχήματα διαλέχτηκαν
    κοιτάζοντας, όχι υπολογίζοντας· δες το tools/route.py.
    """
    if d1 in (2, 6):                        # -> οριζόντιος
        return lastx + (0 if sx > 0 else 4), lasty + 4
    return lastx + 3 + sx, lasty + sy // 2  # -> κάθετος


def corr_origin(cx, cy, dr, qw, qh, fx, fy, sz):
    """Πάνω-αριστερά του ΠΡΩΤΟΥ πλακιδίου διαδρόμου.

    Οι ΑΞΟΝΙΚΟΙ βγαίνουν από το σημείο σύνδεσης, στο εξωτερικό χείλος του
    δακτυλίου, και ΣΤΟ ΚΕΝΤΡΟ του θόλου (βήμα 96): το conn_points έχει την
    αριστερή στήλη μιας κάθετης και την πάνω γραμμή μιας οριζόντιας ακριβώς
    στον άξονα, οπότε ο διάδρομος — 2 bytes x 8 γραμμές — πάει μισό πλάτος
    πίσω, 1 byte ή 4 γραμμές. Ως το 95 έπεφτε όλος από τη μία μεριά.
    Οι ΔΙΑΓΩΝΙΟΙ όχι — βγαίνουν από το πλέγμα του DIAG_K, μετρημένο από το
    ΚΕΝΤΡΟ του θόλου, γιατί μόνο έτσι κουμπώνουν τα δύο άκρα μεταξύ τους.
    """
    if dr == 0:                     # n: κάθετος, προς τα πάνω
        return cx - 1, cy - 16
    if dr == 4:                     # s
        return cx - 1, cy + 8
    if dr == 2:                     # e: οριζόντιος, 4 bytes x 8
        return cx + 2, cy - 4
    if dr == 6:                     # w
        return cx - 4, cy - 4
    k = DIAG_K[sz]
    ox, oy = fx + qw - 4, fy + qh - 8        # το πλακίδιο βήματος 0
    sx, sy = CORR_STEP[dr]
    return ox + sx * k, oy + sy * k


# --- εξωτερικές δομές ------------------------------------------------------

def struct_sprite(a, kind, size):
    k = STRUCT_KINDS[kind]
    return k if kind >= 4 else f"{k}_{SIZES[size]}"


def draw_struct(canvas, a, cam, colony, i, clip):
    kind, size = colony.s(i, S_KIND), colony.s(i, S_SIZE)
    w = a.struct_dims[kind * 8 + size * 2]
    h = a.struct_dims[kind * 8 + size * 2 + 1]
    if w == 0:
        return
    name = struct_sprite(a, kind, size)
    fx = cam.sx(signed(colony.s(i, S_CX))) - w // 2
    fy = cam.sy(signed(colony.s(i, S_CY))) - h // 2
    masked = a.smap[name].masked
    blit(canvas, a.rows(name), fx, fy, masked, clip)


# --- όλη η σκηνή -----------------------------------------------------------

def agents_by_dome(ag):
    """{dome: {slot: fig}} από τους πίνακες πρακτόρων."""
    out = {}
    if ag is None:
        return out
    for i in range(len(ag.flags)):
        if not (ag.flags[i] & 1):               # F_ALIVE
            continue
        if ag.slot[i] == NO_SLOT:
            continue
        node = ag.node[i]
        if node >= MAX_DOME:
            continue                            # δομή, όχι θόλος
        out.setdefault(node, {})[ag.slot[i]] = ROLE_FIG[ag.role[i] & 7]
    return out


def draw_objects(canvas, a, cam, colony, clip=None, ag=None):
    clip = clip or Clip()
    if clip.empty():
        return
    live = [d for d in range(colony.n_dome)
            if colony.d(d, D_STATE) != DS_EMPTY]
    for i in range(colony.n_corr):
        if colony.c(i, C_STATE) != DS_EMPTY:
            draw_corridor(canvas, a, cam, colony, i, clip)
    for d in live:
        draw_shell(canvas, a, cam, colony, d, clip)
    byd = agents_by_dome(ag)
    for d in live:
        draw_fittings(canvas, a, cam, colony, d, clip, byd)
    order = sorted((i for i in range(colony.n_struct)
                    if colony.s(i, S_STATE) != DS_EMPTY),
                   key=lambda i: signed(colony.s(i, S_CY)))
    for i in order:
        draw_struct(canvas, a, cam, colony, i, clip)


# --- η οθόνη με το δαχτυλίδι ----------------------------------------------

def to_screen_ram(canvas, off, base=0xC000):
    """Γραμμικό 80x200 -> τα 16 KB της σελίδας, ΜΕ το offset του CRTC.

    Ο Gate Array πετάει τα MA10/MA11, οπότε το δαχτυλίδι είναι 1.024 λέξεις:
        addr = base + (y&7)*#800 + ((y>>3)*80 + x + 2*off) mod 2048
    """
    ram = bytearray(0x4000)
    for y in range(SCR_H):
        hi = (y & 7) * 0x800
        row = (y >> 3) * SCR_W
        for x in range(SCR_W):
            p = (row + x + 2 * off) & 0x7FF
            ram[hi + p] = canvas.buf[y * SCR_W + x]
    return bytes(ram)
