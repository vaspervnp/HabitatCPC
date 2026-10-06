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
  οι πόρτες       με το bit των φιγούρων, το dome_conn: ένα bit ανά κατεύθυνση
                  με διάδρομο, ο b με την κατεύθυνση της συνέχειας (scene.py)
  και ακόμα       ob_idx = 0, ob_meas = 0, η κάμερα όπως ήταν, η τράπεζα 6 στο
                  παράθυρο

— και τίποτε άλλο: μόνο η στοίβα, οι πρόχειρες μεταβλητές του περάσματος
αντικειμένων (ob_x ως st_ord, oiw_fn, d_id) και του χτισίματος (oi_e, oi_ptr, oi_k),
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
όσο μετρήθηκε στο βήμα 77, συν το 1 µs της διόρθωσης του βήματος 82. Με το
objindex.asm του βήματος 76 αποτυγχάνει.

Αρνητικά, με τον κώδικα πειραγμένο στη μνήμη: η δομή με το id της θέσης της
στο st_ord, το κάτω άκρο στρογγυλεμένο προς τα κάτω, το ob_meas που μένει 1,
και οι άδειες εγγραφές μέσα στο ευρετήριο, οι κατηγορίες από το A των
σαρώσεων, και το oi_build του βήματος 81, που δεν ξεχνά τον θόλο του ob_corr.
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

PROBE = 0x3E00
OI_REC = 5
OI_DOME = 0x4000 + 96 * 128             # πάνω από το NEXTHOP[96][128]
OI_CORR = OI_DOME + S.MAX_DOME * OI_REC
OI_STRUCT = OI_CORR + S.MAX_CORR * OI_REC
FIG, DOME, CORR, STRUCT = 1, 2, 4, 8    # OB_IX_*
# µs ανά κλήση του ob_index, μαζί με τη σκαλωσιά του probe· βήμα 82, και στο 76.
# Το 82 είναι το 77 συν 1 µs: το oi_build γράφει και το d_id μαζί με το ob_meas
# (ld (d_id),hl αντί για inc (hl)), η τιμή της διόρθωσης.
CEIL = {
    "θόλοι": 52169,         # μόνο οι θόλοι                                 53660
    "διάδρομοι": 118687,    # μόνο οι διάδρομοι                            120011
    "δομές": 40359,         # μόνο οι δομές                                 40528
    "όλα": 150172,          # οι τρεις κατηγορίες                          152511
    "όλα + πόρτες": 165237, # και οι σαρώσεις των πορτών και των φιγούρων  167358
}
KIND = {DOME: "θόλοι", CORR: "διάδρομοι", STRUCT: "δομές",
        DOME | CORR | STRUCT: "όλα", 15: "όλα + πόρτες"}


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
        assert m.quickload(TG.SNA, start=False), "quickload απέτυχε"
        m.run_frames(400)
        for at, v in patch:
            m.poke(at, v)
        self.ptr = [cpc._lib.cpcemu_ram_ptr(m._h, n) for n in range(8)]
        self.keep = [self.bank(n) for n in range(8)]

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
        return t


# --- η αναφορά ------------------------------------------------------------

def box(rects):
    """Ορθογώνια (x, y, w, h) σε bytes/γραμμές -> (x0, x1, y0, y1) σε tiles +128."""
    x0 = min(x >> 2 for x, y, w, h in rects)
    x1 = max(-(-(x + w) >> 2) for x, y, w, h in rects)
    y0 = min(y >> 4 for x, y, w, h in rects)
    y1 = max(-(-(y + h) >> 4) for x, y, w, h in rects)
    return tuple((v + 128) & 255 for v in (x0, x1, y0, y1))


def corridor_rects(a, col, i):
    """Τα πλακίδια που ζωγραφίζει το scene.draw_corridor, με την κάμερα στο 0."""
    out = []
    keep = S.blit
    S.blit = lambda canvas, rows, x, y, masked, clip: out.append(
        (x, y, len(rows[0]) // (2 if masked else 1), len(rows)))
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
        if col.c(i, S.C_STATE) and col.c(i, S.C_A) != 255 and col.c(i, S.C_LEN):
            corrs.append(box(corridor_rects(a, col, i)) + (i,))
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


def doors(col):
    """dome_conn: ένα bit ανά κατεύθυνση με διάδρομο (scene.dome_dirs)."""
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
    col.corr[:] = bytes(rnd.randrange(256) for _ in range(len(col.corr)))
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
        prev = col.corr[b - S.CORR_REC: b] if i else b"\0" * 5
        if i and prev[4] and prev[0] != 255 and prev[2] & 1 and rnd.random() < 0.6:
            # η συνέχεια μιας διαγωνίου: αξονική, C_A = C_B = 255 (crm_put)
            col.corr[b:b + 5] = bytes([255, 255, rnd.choice([0, 2, 4, 6]),
                                       rnd.choice([0, 1, 2, 3, 6]), S.DS_ACTIVE])
        elif rnd.random() < dens or (edges and ids and i in (0, 95) and rnd.random() < 0.5):
            col.corr[b:b + 5] = bytes([rnd.choice(ids), rnd.choice(ids), rnd.randrange(8),
                                       rnd.choice([1, 1, 2, 3, 4, 7, 0]),
                                       rnd.choice([S.DS_BUILDING, S.DS_ACTIVE])])
        else:
            col.corr[b + 4] = S.DS_EMPTY
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
            col.struct[b + 3] = (rnd.choice([0, 1, 2, 2, 3]) if kind < 4 else
                                 rnd.choice([0, 0, 0, 1]))          # 3, 1: χωρίς σχήμα
            col.struct[b + 4] = rnd.choice([S.DS_BUILDING, S.DS_ACTIVE])
        else:
            col.struct[b + 4] = S.DS_EMPTY
    L, m, sym = R.L, R.m, R.sym
    R.put(6, L["G_dome_tbl"] - 0x4000, col.dome)
    R.put(6, L["G_struct_tbl"] - 0x4000, col.struct)
    R.put(6, L["G_corr_tbl"] - 0x4000, col.corr)
    # το παλιό ευρετήριο και οι μετρητές του: ό,τι δεν ξαναχτίζεται μένει
    R.put(5, OI_DOME - 0x4000, bytes(rnd.randrange(256)
                                     for _ in range(OI_STRUCT + S.MAX_STRUCT * OI_REC - OI_DOME)))
    for v in ("OI_ND", "OI_NC", "OI_NS", "ST_N"):
        m.poke(sym[v], rnd.randrange(256))
    R.put(0, sym["ST_ORD"], bytes(rnd.randrange(256) for _ in range(S.MAX_STRUCT)))
    R.put(0, sym["DOME_CONN"], bytes(rnd.randrange(256) for _ in range(S.MAX_DOME)))
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
    if mask & FIG:
        for k, v in enumerate(doors(col)):
            poke("DOME_CONN", v, k)
    poke("OB_IDX", 0)
    free = {(0, off) for off in range(0x00A0, 0x0100)}                 # η στοίβα
    free |= {(0, off) for off in range(0x3E00, 0x3F00)}                # το probe
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
                   if col.c(i, S.C_STATE) and col.c(i, S.C_A) < S.MAX_DOME]
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
        print("OK 300 κλήσεις του ob_index = το ευρετήριο, οι μετρητές και οι πόρτες "
              "της πρόζας — και τίποτε άλλο σε καμία τράπεζα")
    for k, c in CEIL.items():
        t = times.get(k, 0)
        if t > c:
            print(f"ΑΠΟΤΥΧΙΑ: {k} {t} us > {c} (βήμα 82)")
            fails += 1
        else:
            print(f"OK {k:13s} {t:6d} us <= {c}")

    m = cpc.CPC()
    m.run_frames(60)
    assert m.quickload(TG.SNA, start=False)

    def find(at, pat, span=120):
        i = m.read_ram(sym[at], span).find(bytes(pat))
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
             for k, v in enumerate([0x21, meas & 255, meas >> 8, 0x34, 0x00])])]
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
