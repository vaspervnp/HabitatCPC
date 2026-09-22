"""Η ΑΝΑΦΟΡΑ του περάσματος αντικειμένων (DESIGN §8.4, SPRITES.md §10).

Γράφτηκε από την πρόζα, όχι από τον Z80: όταν τα δύο συμφωνούν byte προς byte,
συμφωνούν και τα δύο με την προδιαγραφή.

Η σειρά σχεδίασης είναι του SPRITES.md §10, με τη διόρθωση του §8.4 για τους
διαδρόμους — μπαίνουν ΑΝΑΜΕΣΑ στους θόλους και στα σημεία σύνδεσης, γιατί το
`conn_{dir}` ανοίγει την πόρτα ΠΑΝΩ στον δακτύλιο και πρέπει να μείνει από πάνω:

    1. δακτύλιοι + θόλοι όλων των θόλων        (μάσκα)
    2. διάδρομοι                                (μάσκα)
    3. ανά θόλο: πόρτες, εικονίδιο, μηχανές/φυτά, φιγούρες
    4. εξωτερικές δομές, ταξινομημένες κατά cy

ΘΕΣΗ: κάθε αντικείμενο κρατά το ΚΕΝΤΡΟ του σε μισά tiles (§3.4). Η οθόνη
βγαίνει με δύο ολισθήσεις ανά άξονα και καμία διαίρεση:

    sx = 2*cx - 4*cam_tx - w/2          (bytes)
    sy = 8*cy - 16*cam_ty - h/2         (γραμμές)
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sprites import load_map, load_bin
from refrender import Canvas, quad_rows, SCR_W, SCR_H

# --- εγγραφές, ίδιες με τον Z80 -------------------------------------------
DOME_REC = 24
D_CX, D_CY, D_SIZE, D_ROOM, D_STATE, D_INTEG, D_POWER, D_OPS = range(8)
D_MACH, D_HEALTH = 8, 16

STRUCT_REC = 8
S_CX, S_CY, S_KIND, S_SIZE, S_STATE, S_INTEG, S_OUT = range(7)

CORR_REC = 5
C_A, C_B, C_DIR, C_LEN, C_STATE = range(5)

MAX_DOME, MAX_STRUCT, MAX_CORR = 64, 64, 96
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


def dome_dirs(colony, d):
    """Ποιες κατευθύνσεις του θόλου έχουν διάδρομο."""
    out = set()
    for i in range(colony.n_corr):
        if colony.c(i, C_STATE) == DS_EMPTY:
            continue
        a_, b_, dr = colony.c(i, C_A), colony.c(i, C_B), colony.c(i, C_DIR)
        if a_ == d:
            out.add(dr)
        if b_ == d:
            out.add((dr + 4) & 7)
    return out


def draw_fittings(canvas, a, cam, colony, d, clip, agents=None):
    """Βήματα 3-6: πόρτες, εικονίδιο, μηχανές ή φυτά, φιγούρες."""
    fx, fy, qw, qh, sz = dome_frame(a, cam, colony, d)

    for dr in sorted(dome_dirs(colony, d)):
        px = a.conn_points[sz * 16 + dr * 2]
        py = a.conn_points[sz * 16 + dr * 2 + 1]
        blit(canvas, a.rows(f"conn_{DIRS[dr]}"), fx + px, fy + py, True, clip)

    room = colony.d(d, D_ROOM)
    ix = signed(a.interior_ofs[sz * 2])
    iy = signed(a.interior_ofs[sz * 2 + 1])
    icon = f"icon_{SIZES[sz]}_{ROOMS[room]}"
    iw, ih = a.dims(icon)
    blit(canvas, a.rows(icon), fx + qw + ix, fy + qh + iy, False, clip)

    green = room == R_GREENHOUSE
    for s in range(a.machine_count[sz]):
        m = colony.d(d, D_MACH + s)
        if m == NO_MACH:
            continue
        px = a.machine_slots[sz * 16 + s * 2]
        py = a.machine_slots[sz * 16 + s * 2 + 1]
        if px == 255:
            continue
        name = f"plant_{PLANTS[m]}" if green else f"mach_{MACH[m]}"
        blit(canvas, a.rows(name), fx + px, fy + py, False, clip)

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
    dr = colony.c(i, C_DIR)
    n = colony.c(i, C_LEN)
    fx, fy, qw, qh, sz = dome_frame(a, cam, colony, d)
    px = a.conn_points[sz * 16 + dr * 2]
    py = a.conn_points[sz * 16 + dr * 2 + 1]
    x, y = corr_origin(fx + px, fy + py, dr, qw, qh, fx, fy, sz)
    sx, sy = CORR_STEP[dr]
    name = CORR_SPR[dr & 3]
    rows = a.rows(name)
    for _ in range(n):
        blit(canvas, rows, x, y, True, clip)
        x += sx
        y += sy


def corr_origin(cx, cy, dr, qw, qh, fx, fy, sz):
    """Πάνω-αριστερά του ΠΡΩΤΟΥ πλακιδίου διαδρόμου.

    Οι ΑΞΟΝΙΚΟΙ βγαίνουν από το σημείο σύνδεσης: αυτό κάθεται πάνω στον
    δακτύλιο και ο διάδρομος ξεκινά ακριβώς εκεί που τελειώνει, προς τα έξω.
    Οι ΔΙΑΓΩΝΙΟΙ όχι — βγαίνουν από το πλέγμα του DIAG_K, μετρημένο από το
    ΚΕΝΤΡΟ του θόλου, γιατί μόνο έτσι κουμπώνουν τα δύο άκρα μεταξύ τους.
    """
    if dr == 0:                     # n: κάθετος, προς τα πάνω
        return cx, cy - 16
    if dr == 4:                     # s
        return cx, cy + 8
    if dr == 2:                     # e: οριζόντιος, 4 bytes x 8
        return cx + 2, cy
    if dr == 6:                     # w
        return cx - 4, cy
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
    for d in live:
        draw_shell(canvas, a, cam, colony, d, clip)
    for i in range(colony.n_corr):
        if colony.c(i, C_STATE) != DS_EMPTY:
            draw_corridor(canvas, a, cam, colony, i, clip)
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
