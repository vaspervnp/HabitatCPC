#!/usr/bin/env python3
"""Το χτίσιμο του ευρετηρίου αντικειμένων (src/objindex.asm), κλήση προς κλήση,
στο main.sna (DESIGN §8.4).

Το tests/test_index.py ζωγραφίζει κάθε tile μόνο του σε μία αποικία και το
συγκρίνει με την πλήρη σχεδίαση: λέει ότι κανένα περίγραμμα δεν είναι ΜΙΚΡΟΤΕΡΟ
από ό,τι ζωγραφίζει το αντικείμενο. Εδώ το ob_index καλείται κατευθείαν, από
300 τυχαίες καταστάσεις — 0 ως 64 θόλοι σε κάθε μέγεθος, διάδρομοι αξονικοί και
διαγώνιοι με τη συνέχειά τους, δομές κάθε είδους και μεγέθους (και χωρίς
σχήμα), ίσα cy, μόνο οι εγγραφές στις άκρες των πινάκων ζωντανές, κάθε
κάμερα, κάθε συνδυασμός κατηγοριών — και μετά ΟΛΗ η μνήμη, σε όλες τις
τράπεζες, πρέπει να είναι αυτή που λέει η πρόζα:

  το ευρετήριο    για κάθε ζωντανό αντικείμενο μιας κατηγορίας που ξαναχτίζεται,
  (τράπεζα 5)     το περίγραμμά του σε tiles του κόσμου +128 — x0, x1, y0, y1 —
                  και το id του, με τη σειρά σχεδίασης: οι θόλοι κατά id, οι
                  διάδρομοι κατά id, οι δομές κατά cy (σταθερά, τα ίσα κατά id).
                  Περίγραμμα: ⌊αρχή/n⌋ ως ⌈τέλος/n⌉, n = 4 bytes ή 16 γραμμές.
                  Ενας θόλος είναι το πλαίσιό του, ένας διάδρομος η ένωση των
                  πλακιδίων του (και της συνέχειας μετά τη στροφή), μια δομή το
                  sprite της. Ό,τι δεν θα ζωγραφιζόταν δεν μπαίνει: κενή θέση,
                  συνέχεια, διάδρομος μήκους 0, δομή χωρίς σχήμα.
                  Οι θέσεις από την tools/scene.py, την αναφορά του test_object.
  οι μετρητές     oi_nd, oi_nc, oi_ns: πόσες εγγραφές· st_n, st_ord: οι ζωντανές
                  δομές ταξινομημένες, όταν ξαναχτίζονται οι δομές
  οι αρμοί        με το bit των ΔΙΑΔΡΟΜΩΝ, το dome_conn: ένα bit ανά κατεύθυνση
                  με διάδρομο, ο b με την κατεύθυνση της συνέχειας (scene.py).
                  Ως το βήμα 95 οι πόρτες, με το bit των φιγούρων· από το 96 το
                  γράφει η ίδια η μέτρηση των διαδρόμων (jt_mark), και ο
                  αρμός ζωγραφίζεται μετά το κέλυφος. Και από το 97 οι
                  κοντές στροφές, στο jtb_flags (τράπεζα 5 ως το βήμα 128, 6
                  από το 129): ένα bit στην πλευρά της διαγωνίου
                  (scene.dome_bends) — και ο διακόπτης jtd_sw του
                  src/object.asm, #C3 (jp· #21, ld hl, ως το 128) αν υπάρχει
                  έστω μία, #C9 (ret) αν όχι
  και ακόμα       ob_idx = 0, ob_meas = 0, η κάμερα όπως ήταν, η τράπεζα 6 στο
                  παράθυρο

— και τίποτε άλλο: μόνο η στοίβα, οι πρόχειρες μεταβλητές του περάσματος
αντικειμένων (ob_x ως st_ord, oiw_fn, d_id) και του χτισίματος (oi_e, oi_ptr, oi_k),
— όχι οι πρόχειρες της γωνίας (βήμα 129, cn_*): η μέτρηση δεν περνά από εκεί,
και οι φιγούρες των θόλων όταν ξαναχτίζονται.

Οι κατηγορίες που ΔΕΝ ξαναχτίζονται μένουν όπως ήταν, εγγραφές και μετρητές.

Η ΜΝΗΜΗ ΕΝΟΣ ΘΟΛΟΥ του ob_corr (d_id, DESIGN §8.4): στις μισές καταστάσεις
ένας θόλος — συνήθως η αφετηρία ενός ζωντανού διαδρόμου — έχει διαβαστεί πριν
από την κλήση με την κάμερα της κατάστασης, όπως τον αφήνει το πέρασμα της
οθόνης, και τα περιγράμματα πρέπει να είναι ίδια. Ως το βήμα 81 δεν ήταν, όταν
ξαναχτίζονταν μόνο οι διάδρομοι: το d_id ήταν εδώ 255 πριν από κάθε κλήση, για
να μη φαίνεται το λάθος.

ΓΙΑΤΙ. Στο βήμα 77 το objindex.asm ξαναγράφτηκε (347 -> 310 bytes).

Και ο ΧΡΟΝΟΣ, ανά είδος κλήσης, στο χειρότερο που συνάντησε: όχι πιο αργό από
όσο μετρήθηκε στο βήμα 89 (το 77, συν το 1 µs της διόρθωσης του βήματος 82,
μείον τις αναζητήσεις σταθερού χρόνου του 89). Με το objindex.asm του βήματος
76 αποτυγχάνει.

Αρνητικά, με τον κώδικα πειραγμένο στη μνήμη: η δομή με το id της θέσης της
στο st_ord, το κάτω άκρο στρογγυλεμένο προς τα κάτω, το ob_meas που μένει 1,
και οι άδειες εγγραφές μέσα στο ευρετήριο, οι κατηγορίες από το A των
σαρώσεων, το oi_build του βήματος 81, που δεν ξεχνά τον θόλο του ob_corr, και
ο διακόπτης των κοντών στροφών που δεν κλείνει ή δεν ανοίγει (βήμα 97).
"""
import ctypes, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import cpc                                               # noqa: E402
import scene as S                                        # noqa: E402
import codeat                                            # noqa: E402

PROBE = 0x3E80
OI_REC = 5
def _obj_index():
    for line in open(os.path.join(ROOT, "build", "layout.asm"), encoding="utf-8"):
        p = line.split()
        if len(p) >= 3 and p[0] == "G_obj_index":
            return int(p[2].lstrip("#"), 16)
    raise KeyError("G_obj_index")


# Πάνω από το NEXTHOP[96][128] ως το βήμα 154 (#7000)· από το 155 μετά τους
# διαδρόμους, στο G_obj_index του tools/pack.py.
OI_DOME = _obj_index()
OI_CORR = OI_DOME + S.MAX_DOME * OI_REC
OI_STRUCT = OI_CORR + S.MAX_CORR * OI_REC
FIG, DOME, CORR, STRUCT = 1, 2, 4, 8    # OB_IX_*
# µs ανά κλήση του ob_index, μαζί με τη σκαλωσιά του probe· βήμα 82, και στο 76.
# Το 82 είναι το 77 συν 1 µs: το oi_build γράφει και το d_id μαζί με το ob_meas
# (ld (d_id),hl αντί για inc (hl)), η τιμή της διόρθωσης. Οι πόρτες από το
# βήμα 86: ο έλεγχος του airlock στο ob_conn_scan έβγαλε 165.502, και το ίδιο
# το ob_conn_scan ξαναγράφτηκε με το IX και πίνακα bits — 158.843.
# Βήμα 89: οι αναζητήσεις σε σταθερούς πίνακες (corr_dir, dome_conn, dome_geo,
# diag_k, struct_dims, struct_ptr) χωρίς ob_addu, σε σταθερό χρόνο — ως τότε
# πλήρωναν το όριο σελίδας όπου έπεφτε ο πίνακας, και ο κώδικας του 89 τα
# μετατόπισε πάνω σε όριο: +134 us χωρίς να αλλάξει εντολή. Κανένα από τα 300
# δεν είναι πιο αργό από το 88. Στη δεξιά στήλη το βήμα 76.
# Βήμα 96: οι αρμοί του dome_conn γράφονται στη μέτρηση των διαδρόμων (jt_mark,
# και το σβήσιμο από το oi_build), και η σάρωση των πορτών έφυγε από το bit
# των φιγούρων. Οι ολισθήσεις του ob_box αντί για το ob_mul τα πλήρωσαν.
CEIL = {
    "θόλοι": 51721,         # μόνο οι θόλοι                                 53660
    "διάδρομοι": 117082,    # μόνο οι διάδρομοι                            120011
    "δομές": 39897,         # μόνο οι δομές                                 40528
    "όλα": 148201,          # οι τρεις κατηγορίες                          152511
    "όλα + φιγούρες": 147178, # και η σάρωση των φιγούρων (ως το 95 και
                            # των πορτών)                                  167358
}
KIND = {DOME: "θόλοι", CORR: "διάδρομοι", STRUCT: "δομές",
        DOME | CORR | STRUCT: "όλα", 15: "όλα + φιγούρες"}


def layout():
    L = {}
    for line in open(os.path.join(ROOT, "build", "layout.asm"), encoding="utf-8"):
        p = line.split()
        if len(p) >= 3 and p[1] == "equ" and p[2].startswith("#"):
            L[p[0]] = int(p[2][1:], 16)
    return L


def s8(v):
    return v - 256 if v > 127 else v


class Rig:
    def __init__(self, sym, patch=()):
        self.sym, self.L = sym, layout()
        m = self.m = cpc.CPC()
        m.run_frames(60)
        assert m.quickload(TG.COLONY, start=False), "quickload απέτυχε"
        m.run_frames(400)
        self.ptr = [cpc._lib.cpcemu_ram_ptr(m._h, n) for n in range(8)]
        # (at, v) στη μνήμη όπως τη βλέπει ο Z80 τώρα· (n, at, v) στην τράπεζα n
        # στο παράθυρο, ό,τι κι αν είναι μέσα (το b6code, από το βήμα 129 και
        # το jtm_bend: η 6 δεν είναι πάντα στο παράθυρο στο frame 400)
        for p in patch:
            if len(p) == 3:
                self.put(p[0], p[1] - 0x4000, [p[2]])
            else:
                m.poke(*p)
        self.keep = [self.bank(n) for n in range(8)]
        self.ph = codeat.phase(m)               # η φάση της μέτρησης (βήμα 155)

    def bank(self, n):
        return ctypes.string_at(self.ptr[n], 0x4000)

    def put(self, n, off, data):
        ctypes.memmove(ctypes.addressof(self.ptr[n].contents) + off, bytes(data), len(data))

    def restore(self):
        for n in range(8):
            self.put(n, 0, self.keep[n])

    def stale(self, k):
        """Ο θόλος k στη μνήμη του ob_corr (d_id, d_rec, το πλαίσιο), διαβασμένος
        με την τρέχουσα κάμερα: ό,τι αφήνει πίσω του το πέρασμα της οθόνης."""
        m, ad = self.m, self.sym["OB_GETDOME"]
        code = [0xF3, 0x31, 0x00, 0x01, 0x01, 0xC6, 0x7F, 0xED, 0x49,
                0x3E, k, 0xCD, ad & 255, ad >> 8, 0x18, 0xFE]
        m.write_ram(PROBE, bytes(code))
        m.set_pc(PROBE)
        end = PROBE + len(code) - 2
        for _ in range(100_000):
            if end <= m.pc <= end + 2:
                return
            m.run_us(1)
        raise SystemExit("το ob_getdome δεν γύρισε")

    def call(self):
        m, ad = self.m, self.sym["OB_INDEX"]
        code = [0xF3, 0x31, 0x00, 0x01, 0x01, 0xC6, 0x7F, 0xED, 0x49,   # τράπεζα 6 μέσα
                0xCD, ad & 255, ad >> 8, 0x18, 0xFE]
        m.write_ram(PROBE, bytes(code))
        m.set_pc(PROBE)
        end, t = PROBE + len(code) - 2, 0
        while not (end <= m.pc <= end + 2):
            m.run_us(1)
            t += 1
            if t > 1_000_000:
                return None
        return t - self.ph


# --- η αναφορά ------------------------------------------------------------

def box(rects):
    """Ορθογώνια (x, y, w, h) σε bytes/γραμμές -> (x0, x1, y0, y1) σε tiles +128."""
    x0 = min(x >> 2 for x, y, w, h in rects)
    x1 = max(-(-(x + w) >> 2) for x, y, w, h in rects)
    y0 = min(y >> 4 for x, y, w, h in rects)
    y1 = max(-(-(y + h) >> 4) for x, y, w, h in rects)
    return tuple((v + 128) & 255 for v in (x0, x1, y0, y1))


def corridor_rects(a, col, i):
    """Τα πλακίδια των δύο τρεξιμάτων ΟΛΟΚΛΗΡΩΝ, με την κάμερα στο 0: το κουτί
    του ευρετηρίου. Από το βήμα 129 το scene.draw_corridor ζωγραφίζει τη γωνία
    — προς οριζόντιο ένα κομμένο διαγώνιο και ένα μπάλωμα, προς κάθετο ένα
    σχέδιο 5 x 8 — και η μέτρηση του Z80 δεν τα κοιτάζει: ό,τι φαίνεται από
    αυτά πέφτει μέσα στα τρεξίματα (opaque_rects, πιο κάτω, και ο έλεγχος στο
    model)."""
    cam = S.Camera()
    d = col.c(i, S.C_A)
    dr, n = col.c(i, S.C_DIR), col.c(i, S.C_LEN)
    fx, fy, qw, qh, sz = S.dome_frame(a, cam, col, d)
    px = a.conn_points[sz * 16 + dr * 2]
    py = a.conn_points[sz * 16 + dr * 2 + 1]
    x, y = S.corr_origin(fx + px, fy + py, dr, qw, qh, fx, fy, sz)
    sx, sy = S.CORR_STEP[dr]
    w, h = a.dims(S.CORR_SPR[dr & 3])
    out = []
    for _ in range(n):
        out.append((x, y, w, h))
        lastx, lasty = x, y
        x, y = x + sx, y + sy
    j = i + 1
    if j < S.MAX_CORR and col.c(j, S.C_A) == S.CT_CONT:
        d1 = col.c(j, S.C_DIR)
        x, y = S.corr_bend(lastx, lasty, sx, sy, d1)
        vx, vy = S.CORR_STEP[d1]
        w, h = a.dims(S.CORR_SPR[d1 & 3])
        for _ in range(col.c(j, S.C_LEN)):
            out.append((x, y, w, h))
            x, y = x + vx, y + vy
    return out


def opaque_rects(a, col, i):
    """Ο,τι ζωγραφίζει ΠΡΑΓΜΑΤΙ το scene.draw_corridor, γωνία μαζί: ανά
    sprite, το ορθογώνιο των bytes του με μάσκα που δεν είναι #FF."""
    out = []

    def grab(canvas, rows, x, y, masked, clip):
        cells = [(bx, by) for by, r in enumerate(rows)
                 for bx in range(len(r) // 2) if r[2 * bx] != 0xFF]
        if cells:
            x0, x1 = min(c[0] for c in cells), max(c[0] for c in cells) + 1
            y0, y1 = min(c[1] for c in cells), max(c[1] for c in cells) + 1
            out.append((x + x0, y + y0, x1 - x0, y1 - y0))
    keep = S.blit
    S.blit = grab
    try:
        S.draw_corridor(None, a, S.Camera(), col, i, S.Clip())
    finally:
        S.blit = keep
    return out


def model(a, col):
    """(θόλοι, διάδρομοι, δομές, st_ord): οι εγγραφές του ευρετηρίου."""
    cam = S.Camera()
    domes = []
    for d in range(S.MAX_DOME):
        if col.d(d, S.D_STATE):
            fx, fy, qw, qh, _ = S.dome_frame(a, cam, col, d)
            domes.append(box([(fx, fy, 2 * qw, 2 * qh)]) + (d,))
    corrs = []
    for i in range(S.MAX_CORR):
        if col.c(i, S.C_A) < S.CT_EMPTY and col.c(i, S.C_LEN):
            b = box(corridor_rects(a, col, i))
            # Ο,τι φαίνεται από τη γωνία (βήμα 129) μέσα στο κουτί των
            # τρεξιμάτων — για στροφή που βγάζει το route: ο άξονας μοιράζεται
            # μία φορά με τη διαγώνιο, και η συνέχεια έχει μήκος. Οι τυχαίες
            # εγγραφές εδώ έχουν και αναστροφές και μήκος 0.
            j = i + 1
            if j < S.MAX_CORR and col.c(j, S.C_A) == S.CT_CONT \
                    and col.c(j, S.C_DIR) in ((col.c(i, S.C_DIR) + 1) & 7,
                                              (col.c(i, S.C_DIR) - 1) & 7) \
                    and col.c(j, S.C_LEN):
                o = box(opaque_rects(a, col, i))
                assert b[0] <= o[0] and o[1] <= b[1] and b[2] <= o[2] and o[3] <= b[3], \
                    f"ο διάδρομος {i} ζωγραφίζει έξω από το κουτί του: {o} > {b}"
            corrs.append(b + (i,))
    live = [s for s in range(S.MAX_STRUCT) if col.s(s, S.S_STATE)]
    order = sorted(live, key=lambda s: s8(col.s(s, S.S_CY)))
    structs = []
    for s in order:
        k = col.s(s, S.S_KIND) * 8 + col.s(s, S.S_SIZE) * 2
        w, h = a.struct_dims[k], a.struct_dims[k + 1]
        if w:
            x = cam.sx(s8(col.s(s, S.S_CX))) - w // 2
            y = cam.sy(s8(col.s(s, S.S_CY))) - h // 2
            structs.append(box([(x, y, w, h)]) + (s,))
    return domes, corrs, structs, order


def bends(col):
    """jtb_flags (src/bend.asm, στο b6code της τράπεζας 6 από το βήμα 129, στην
    5 ως τότε): ένα bit ανά κοντή στροφή, στην πλευρά της διαγωνίου, ή μείον ένα
    κάθετα (scene.dome_bends) — βήμα 97."""
    out = bytearray(S.MAX_DOME)
    for d in range(S.MAX_DOME):
        for k in S.dome_bends(col, d):
            out[d] |= 1 << k
    return out


def doors(col):
    """dome_conn: ένα bit ανά κατεύθυνση με διάδρομο (scene.dome_dirs) — οι
    αρμοί του βήματος 96, ως το 95 οι πόρτες."""
    out = bytearray(S.MAX_DOME)
    for d in range(S.MAX_DOME):
        for dr in S.dome_dirs(col, d):
            out[d] |= 1 << dr
    return out


# --- οι καταστάσεις --------------------------------------------------------

def scene(R, a, rnd, case):
    """Μια τυχαία κατάσταση στη μνήμη· γυρίζει (colony, μάσκα)."""
    col = S.Colony()
    col.n_dome, col.n_struct, col.n_corr = S.MAX_DOME, S.MAX_STRUCT, S.MAX_CORR
    col.dome[:] = bytes(rnd.randrange(256) for _ in range(len(col.dome)))
    col.struct[:] = bytes(rnd.randrange(256) for _ in range(len(col.struct)))
    # ΟΣΑ ΤΥΧΑΙΑ ΚΑΙ ΩΣ ΤΟ ΒΗΜΑ 153 (96 x 5): οι 300 καταστάσεις μένουν ίδιες
    col.corr[:] = bytes(rnd.randrange(256) for _ in range(96 * 5))[:len(col.corr)]
    hub = rnd.randrange(-100, 100), rnd.randrange(-100, 100)

    def near(c, r):
        return max(-120, min(120, c + rnd.randrange(-r, r + 1))) & 255

    nd = rnd.choice([0, 1, 2, 4, 12, 12, 30, 64])
    live = set(rnd.sample(range(S.MAX_DOME), nd))
    edges = rnd.random() < 0.2              # μόνο οι άκρες των πινάκων
    if edges:
        live = set(rnd.sample([0, 1, 62, 63], rnd.randrange(1, 4)))
    for d in range(S.MAX_DOME):
        b = d * S.DOME_REC
        if d in live:
            col.dome[b], col.dome[b + 1] = near(hub[0], 30), near(hub[1], 30)
            if rnd.random() < 0.1:          # στις άκρες του χώρου των μισών tiles
                col.dome[b] = rnd.choice([0x80, 0x81, 0x7E, 0x7F])
            col.dome[b + 2] = rnd.randrange(3)
            col.dome[b + 4] = rnd.choice([S.DS_BUILDING, S.DS_ACTIVE, S.DS_ACTIVE])
        else:
            col.dome[b + 4] = S.DS_EMPTY
    ids = sorted(live)
    dens = 0.0 if not ids else rnd.choice([0.0, 0.1, 0.4, 0.8])
    for i in range(S.MAX_CORR):
        b = i * S.CORR_REC
        prev = col.corr[b - S.CORR_REC: b] if i else bytes([S.CT_EMPTY]) * 4
        if i and prev[0] < S.CT_EMPTY and prev[2] & 1 and rnd.random() < 0.6:
            # η συνέχεια μιας διαγωνίου: αξονική, C_A = C_B = 255 (crm_put)
            col.corr[b:b + 4] = bytes([255, 255, rnd.choice([0, 2, 4, 6]),
                                       rnd.choice([0, 1, 2, 3, 6])])
        elif rnd.random() < dens or (edges and ids and i in (0, 95) and rnd.random() < 0.5):
            col.corr[b:b + 4] = bytes([rnd.choice(ids), rnd.choice(ids), rnd.randrange(8),
                                       rnd.choice([1, 1, 2, 3, 4, 7, 0])])
            rnd.choice([S.DS_BUILDING, S.DS_ACTIVE])     # ως το βήμα 153 η κατάσταση
        else:
            col.corr[b] = S.CT_EMPTY                     # άδεια (βήμα 154: το C_A)
    col.corr[S.MAX_CORR * S.CORR_REC] = S.CT_EMPTY       # η 97η, πάντα άδεια
    ns = rnd.choice([0, 0, 1, 2, 5, 12, 32])
    sl = set(rnd.sample(range(S.MAX_STRUCT), ns))
    if edges:
        sl = set(rnd.sample([0, 1, 30, 31], rnd.randrange(0, 3)))
    for s in range(S.MAX_STRUCT):
        b = s * S.STRUCT_REC
        if s in sl:
            col.struct[b], col.struct[b + 1] = near(hub[0], 40), near(hub[1], 40)
            if rnd.random() < 0.25 and s:   # ίσο cy με την προηγούμενη θέση
                col.struct[b + 1] = col.struct[b + 1 - S.STRUCT_REC]
            kind = rnd.randrange(8)
            col.struct[b + 2] = kind
            # τα ενεργειακά στο 2, και το 3 χωρίς σχήμα: τα 0 και 1, ως το βήμα
            # 150 εδώ, το παιχνίδι δεν τα φτιάχνει, και από το 151 δεν έχουν σχήμα.
            # Η ίδια ζαριά (max): το δείγμα μένει όπως ήταν, μόνο μεγαλύτερο.
            col.struct[b + 3] = (max(2, rnd.choice([0, 1, 2, 2, 3])) if kind < 4 else
                                 rnd.choice([0, 0, 0, 1]))          # 3, 1: χωρίς σχήμα
            col.struct[b + 4] = rnd.choice([S.DS_BUILDING, S.DS_ACTIVE])
        else:
            col.struct[b + 4] = S.DS_EMPTY
    L, m, sym = R.L, R.m, R.sym
    R.put(6, L["G_dome_tbl"] - 0x4000, col.dome)
    R.put(6, L["G_struct_tbl"] - 0x4000, col.struct)
    R.put(5, L["G_corr_tbl"] - 0x4000, col.corr)        # στην τράπεζα 5 (βήμα 154)
    # το παλιό ευρετήριο και οι μετρητές του: ό,τι δεν ξαναχτίζεται μένει
    R.put(5, OI_DOME - 0x4000, bytes(rnd.randrange(256)
                                     for _ in range(OI_STRUCT + S.MAX_STRUCT * OI_REC - OI_DOME)))
    for v in ("OI_ND", "OI_NC", "OI_NS", "ST_N"):
        m.poke(sym[v], rnd.randrange(256))
    R.put(0, sym["ST_ORD"], bytes(rnd.randrange(256) for _ in range(S.MAX_STRUCT)))
    R.put(0, sym["DOME_CONN"], bytes(rnd.randrange(256) for _ in range(S.MAX_DOME)))
    # Βήμα 97: σκουπίδια και στις σημαίες των στροφών — από δικό τους rnd, ώστε
    # οι 300 καταστάσεις, και άρα τα ταβάνια, να μένουν ίδιες.
    frnd = random.Random(9700 + case)
    R.put(6, sym["JTB_FLAGS"] - 0x4000, bytes(frnd.randrange(256) for _ in range(S.MAX_DOME)))
    m.poke(sym["JTD_SW"], frnd.choice((0xC9, 0xC3)))     # ο διακόπτης, ανοιχτός ή κλειστός
    m.poke(sym["CAM_TX"], rnd.randrange(-64, 64) & 255)
    m.poke(sym["CAM_TY"], rnd.randrange(-64, 64) & 255)
    m.poke(sym["D_ID"], 255)
    mask = rnd.choice([DOME, CORR, STRUCT, 14, 15, DOME, CORR, STRUCT, 14, 15,
                       FIG, 3, 5, 6, 9, 10, 12])
    m.poke(sym["OB_IDX"], mask)
    return col, mask


def expect(R, a, before, col, mask):
    """(η μνήμη μετά, και οι διευθύνσεις που επιτρέπεται να αλλάξουν)."""
    L, sym = R.L, R.sym
    b = [bytearray(x) for x in before]
    domes, corrs, structs, order = model(a, col)

    def poke(name, v, k=0):
        at = sym[name] + k
        b[2 if at >= 0x8000 else 0][at & 0x3FFF] = v

    for bit, recs, base, cnt in ((DOME, domes, OI_DOME, "OI_ND"),
                                 (CORR, corrs, OI_CORR, "OI_NC"),
                                 (STRUCT, structs, OI_STRUCT, "OI_NS")):
        if mask & bit:
            flat = bytes(v for r in recs for v in r)
            b[5][base - 0x4000: base - 0x4000 + len(flat)] = flat
            poke(cnt, len(recs))
    if mask & STRUCT:
        poke("ST_N", len(order))
        for k, s in enumerate(order):
            poke("ST_ORD", s, k)
    if mask & CORR:                     # βήμα 96: με τους διαδρόμους
        for k, v in enumerate(doors(col)):
            poke("DOME_CONN", v, k)
        jf = sym["JTB_FLAGS"] - 0x4000  # βήμα 97: και οι κοντές στροφές
        b[6][jf:jf + S.MAX_DOME] = bends(col)
        poke("JTD_SW", 0xC3 if any(bends(col)) else 0xC9)   # jp jtb_dome ή ret
    poke("OB_IDX", 0)
    free = {(0, off) for off in range(0x00A0, 0x0100)}                 # η στοίβα
    free |= {(0, off) for off in range(PROBE, 0x3F00)}                 # το probe
    free |= {(0, off) for off in range(sym["OB_X"], sym["ST_ORD"])} - {(0, sym["ST_N"])}
    free |= {(0, sym["OIW_FN"]), (0, sym["OIW_FN"] + 1)}
    free |= {(0, sym["D_ID"])}                  # η μνήμη του ob_corr (από το βήμα 82 εδώ)
    free |= {(2, at - 0x8000) for at in range(sym["OI_E"], sym["OI_E"] + 8)}
    if mask & FIG:
        g = L["G_dome_fig"] - 0x4000
        free |= {(6, off) for off in range(g, g + S.MAX_DOME * 8)}
    return b, free


def run(sym, a, patch=(), n=300, times=None):
    R = Rig(sym, patch)
    if times is not None:
        times["_ph"] = R.ph
    rnd = random.Random(77)
    for case in range(n):
        R.restore()
        col, mask = scene(R, a, rnd, case)
        # ΜΙΣΕΣ ΦΟΡΕΣ, ΕΝΑΣ ΘΟΛΟΣ ΣΤΗ ΜΝΗΜΗ ΤΟΥ ob_corr (βήμα 82), συνήθως η
        # αφετηρία ενός ζωντανού διαδρόμου, με την κάμερα της κατάστασης. Ως το
        # βήμα 81 ένα ob_index μόνο των διαδρόμων μετρούσε τον πρώτο που ξεκινά
        # από εκεί με το πλαίσιο της κάμερας, όχι του (0, 0). Δικό του rnd: οι
        # 300 καταστάσεις, και άρα τα ταβάνια, μένουν ίδιες.
        srnd = random.Random(8200 + case)
        if srnd.random() < 0.5:
            src = [col.c(i, S.C_A) for i in range(S.MAX_CORR)
                   if col.c(i, S.C_A) < S.MAX_DOME]
            R.stale(srnd.choice(src) if src and srnd.random() < 0.8
                    else srnd.randrange(S.MAX_DOME))
        before = [R.bank(k) for k in range(8)]
        want, free = expect(R, a, before, col, mask)
        t = R.call()
        if t is None:
            return f"περίπτωση {case}: το ob_index δεν γύρισε (PC=#{R.m.pc:04X})"
        if times is not None and mask in KIND:
            times[KIND[mask]] = max(times.get(KIND[mask], 0), t)
        # «Απαιτεί τράπεζα 6»: και την αφήνει μέσα — το ob_draw_all συνεχίζει
        view = bytes(R.m.peek(0x4000 + 257 * k) for k in range(63))
        if view != bytes(R.bank(6)[257 * k] for k in range(63)):
            return f"περίπτωση {case} (μάσκα {mask}): δεν αφήνει την τράπεζα 6 μέσα"
        for k in range(8):
            got = R.bank(k)
            if got == bytes(want[k]):
                continue
            for off in range(0x4000):
                if got[off] != want[k][off] and (k, off) not in free:
                    a_ = off + (0x8000 if k == 2 else 0x4000 if k in (5, 6) else 0)
                    what = ""
                    if k == 5 and OI_DOME <= a_ < OI_STRUCT + S.MAX_STRUCT * OI_REC:
                        cls, base = max((b_, n_) for n_, b_ in (("θόλων", OI_DOME),
                                        ("διαδρόμων", OI_CORR), ("δομών", OI_STRUCT))
                                        if b_ <= a_)[::-1]
                        what = (f" — {cls} εγγραφή {(a_ - base) // OI_REC}, "
                                f"{('x0', 'x1', 'y0', 'y1', 'id')[(a_ - base) % OI_REC]}")
                    return (f"περίπτωση {case} (μάσκα {mask}): τράπεζα {k} #{a_:04X} = "
                            f"{got[off]}, η πρόζα λέει {want[k][off]} "
                            f"(πριν {before[k][off]}){what}")
    return None


def main():
    sym, _ = TG.build()
    a = S.Assets()
    fails = 0
    times = {}
    why = run(sym, a, times=times)
    if why:
        print(f"ΑΠΟΤΥΧΙΑ: {why}")
        fails += 1
    else:
        print("OK 300 κλήσεις του ob_index = το ευρετήριο, οι μετρητές και οι αρμοί "
              "της πρόζας — και τίποτε άλλο σε καμία τράπεζα")
    print(f"    ΦΑΣΗ: ο μάρτυρας των {codeat.CTRL_N} nop μετρά +{times.get('_ph', 0)} µs από εδώ, "
          f"και αφαιρείται από κάθε μέτρηση (βήμα 155, tests/codeat.py)")
    for k, c in CEIL.items():
        t = times.get(k, 0)
        if t > c:
            print(f"ΑΠΟΤΥΧΙΑ: {k} {t} us > {c} (βήματα 82, 86, 89 και 96)")
            fails += 1
        else:
            print(f"OK {k:13s} {t:6d} us <= {c}")

    m = cpc.CPC()
    m.run_frames(60)
    assert m.quickload(TG.COLONY, start=False)

    def find(at, pat, span=120, bank=None):
        if bank is None:
            raw = bytes(m.read_ram(sym[at], span))
        else:                                   # στο παράθυρο, από την τράπεζα
            o = sym[at] - 0x4000
            raw = ctypes.string_at(cpc._lib.cpcemu_ram_ptr(m._h, bank), 0x4000)[o:o + span]
        i = raw.find(bytes(pat))
        assert i >= 0, f"δεν βρέθηκε το {pat} στο {at}"
        return sym[at] + i

    e4 = sym["OI_E"] + 4
    meas = sym["OB_MEAS"]
    neg = [("τη δομή με το id της θέσης της στο st_ord",
            [(find("OI_ST", [0x32, e4 & 255, e4 >> 8]) + k, 0) for k in range(3)]),
           ("το κάτω άκρο στρογγυλεμένο προς τα κάτω",
            [(find("OI_GY", [0x3C, 0x4F]), 0)]),
           ("το ob_meas που μένει 1",
            [(find("OIB_END", [0x32, meas & 255, meas >> 8]) + k, 0) for k in range(3)]),
           ("τις άδειες εγγραφές μέσα στο ευρετήριο",
            [(find("OI_PASS", [0xB7, 0x28]) + 1, 0), (find("OI_PASS", [0xB7, 0x28]) + 2, 0)]),
           ("τις κατηγορίες από το A των σαρώσεων",
            [(find("OB_INDEX", [0xF5, 0xCD]), 0), (find("OB_INDEX", [0xF1, 0xC3]), 0)]),
           ("το oi_build του βήματος 81, που δεν ξεχνά τον θόλο του ob_corr",
            [(find("OI_BUILD", [0x2D, 0x24, 0x22], 30) + k, v)
             for k, v in enumerate([0x21, meas & 255, meas >> 8, 0x34, 0x00])]),
           ("τον διακόπτη που δεν κλείνει (jt_clear)", [(find("JT_CLEAR", [0x3E, 0xC9]) + 1, 0x21)]),
           ("τον διακόπτη που δεν ανοίγει (jtm_bend)",
            [(6, find("JTM_BEND", [0x3E, 0xC3], bank=6) + 1, 0xC9)])]
    for label, patch in neg:
        why = run(sym, a, patch, n=100)
        if why:
            print(f"OK ΑΡΝΗΤΙΚΟ: με {label} αποτυγχάνει ({why[:90]})")
        else:
            print(f"ΑΠΟΤΥΧΙΑ ΑΡΝΗΤΙΚΟΥ: με {label} περνά")
            fails += 1
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
