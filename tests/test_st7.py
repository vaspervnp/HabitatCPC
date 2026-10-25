#!/usr/bin/env python3
"""Οι δομές χωρίς μάσκα, με κάθε clip (βήμα 170, src/st7.asm, DESIGN §8.4).

ΤΙ ΑΛΛΑΞΕ. Τα επτά sprites των δομών με μάσκα (όλα εκτός από την πλατφόρμα)
κρατούσαν μάσκα δίπλα σε κάθε byte. Η μάσκα κάθε κελιού τους είναι ακριβώς τα
pixel του με pen 0, και κανένα αδιαφανές κελί δεν έχει pen 0· το tools/pack.py
το ελέγχει για κάθε κελί (struct_data). Μένει μόνο το χρώμα: 3.840 bytes αντί
για 7.680, και ένας πίνακας μάσκας 256 bytes. Τα ζωγραφίζει κώδικας της
τράπεζας 7 (st7_put), με τον βρόχο του ob_line και έναν ξετυλιγμένο πυρήνα.

Η ΣΥΓΚΡΙΣΗ. Ο Z80 ζωγραφίζει ΜΙΑ δομή με το ob_struct πάνω σε τυχαία bytes,
με αυθαίρετο clip, και η αναφορά κάνει το ίδιο από τα sprites ΜΕ τη μάσκα τους
(tools/scene.py, blit): κάθε byte των 16 KB της οθόνης ίδιο, και τίποτα έξω
από το clip. Η κάμερα είναι εκείνη του test_object όπου το τύλιγμα του
δαχτυλιδιού των 2 KB πέφτει μέσα στην εικόνα, στη σειρά χαρακτήρων 3. Για
κάθε ένα από τα οκτώ είδη:

  ΟΛΟΚΛΗΡΗ      μέσα στο κάδρο.
  ΑΚΡΕΣ         κομμένη αριστερά, δεξιά, πάνω, κάτω, κατά 2 ή 8, μισή, και
                όλη εκτός από 2 ή 8.
  CLIP ΠΑΝΩ     το clip αρχίζει 1-7 γραμμές μέσα της.
  ΤΥΛΙΓΜΑ       το σημείο του τυλίγματος στο πρώτο, στο μεσαίο και στο
                τελευταίο κελί: η γραμμή σπάει στα δύο (s7_wchk).
  ΣΤΗΛΕΣ        το clip του σκρολαρίσματος, 4 bytes και όλο το ύψος.
  ΚΕΛΙΑ         το clip μιας φιγούρας έξω, 2 bytes x 8 γραμμές, σε κάθε θέση
                πάνω στη δομή και γύρω της.
  ΤΥΧΑΙΑ        δώδεκα τυχαία clip και θέσεις.

ΤΟ ΚΟΣΤΟΣ, μετρημένο ανά κλήση του ob_struct (σονδα, µs, με τη φάση της
μέτρησης αφαιρεμένη). Στο βήμα 169, με τις ίδιες περιπτώσεις, και τώρα:

  είδος        ολόκληρη         στήλη 4 bytes     κελί 2x8
  solar        14.209 -> 11.276  7.309 -> 5.912   1.722 -> 1.469
  turbine      14.209 -> 11.276  7.311 -> 5.912   1.722 -> 1.469
  collector    14.209 -> 11.276  7.309 -> 5.914   1.722 -> 1.469
  extractor    14.209 -> 11.276  7.311 -> 5.912   1.722 -> 1.469
  mine         23.247 -> 18.346  9.435 -> 7.606   1.724 -> 1.473
  airlock       7.475 ->  5.998  5.183 -> 4.218   1.724 -> 1.469
  pad          11.149 -> 11.144  6.553 -> 6.548   1.556 -> 1.551
  ship          7.475 ->  5.998  5.183 -> 4.218   1.724 -> 1.469

ΚΑΘΕ μία από τις 608 περιπτώσεις έγινε φθηνότερη (η πλατφόρμα κατά 5 µs: το
ob_struct μίκρυνε, ο δρόμος της είναι ο ίδιος), και όλες μαζί 16,1 %. Το
κελί των 48 T (59 το blt_mask_line) κερδίζει σε κάθε πλάτος· η πρώτη μορφή του
βήματος, γραμμές με μάσκα μόνο στις άκρες και ldir στο αδιαφανές, ήταν 36-41 %
φθηνότερη ολόκληρη αλλά διπλάσια στις στήλες και στα κελιά, όπου το κόψιμο
έψαχνε μέσα σε κάθε γραμμή, και δεν κρατήθηκε. Τα ταβάνια εδώ είναι τα
σημερινά με 1 %, και κάθε μέτρηση κάτω από τα νούμερα του 169.

ΟΙ ΔΙΑΔΡΟΜΟΙ ΚΑΙ ΟΙ ΓΩΝΙΕΣ (βήμα 171). Τα τέσσερα σχέδια των διαδρόμων και τα
τέσσερα των γωνιών είναι στην 7 χωρίς μάσκα από το βήμα 171, και τα ζωγραφίζει
ο ίδιος κώδικας: το ob_put7 (s7_clip), και καθρεφτισμένα κάθετα το ob_put7v
(s7_clipv), όπως τα βόρεια σχέδια των γωνιών. Καθένα και με τα δύο, ολόκληρο,
κομμένο σε κάθε πλευρά κατά 1 ως όλο εκτός από 1 (και 1-7 γραμμές από πάνω),
με το τύλιγμα μέσα, σε κάθε στήλη και κελί πάνω του, και δώδεκα τυχαία:
απέναντι στο blit της αναφοράς με τις γραμμές ανάποδα για το καθρέφτισμα. Το
κόστος του ολόκληρου κάτω από ταβάνι. Αρνητικά: το s7_clipv χωρίς το neg (το
βήμα +w), χωρίς το dec (η γραμμή h - st), και χωρίς να ξαναβάλει το 0 στο πάνω
byte του βήματος (οι επόμενοι χωρίς καθρέφτισμα).

Αρνητικά, με τον κώδικα της τράπεζας 7 πειραγμένο: χωρίς το σπάσιμο του
τυλίγματος, το H πίσω κατά 0 αντί για 8, χωρίς το clip από αριστερά (ob_addu),
η πρώτη γραμμή χωρίς το ob_st, το βήμα της γραμμής 0, ο πίνακας της μάσκας μία
σελίδα πιο πέρα. Καθένα πρέπει να βγάλει λάθος σε κάποια περίπτωση.
"""
import ctypes, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_object as TO                                  # noqa: E402
import scene as S                                         # noqa: E402
import codeat                                             # noqa: E402
import cpc                                                # noqa: E402
from refrender import Canvas                              # noqa: E402

PLAY, SCR_W = S.PLAY_LINES, 80
CAM = S.Camera(-18, -3)                 # το τύλιγμα μέσα στην εικόνα (test_object)
PROBE = 0x3E80
KINDS = ["solar", "turbine", "collector", "extractor", "mine", "airlock", "pad", "ship"]
# (ολόκληρη, στήλη, κελί): τα χειρότερα του βήματος 169, και τα ταβάνια από το 171
# (στο 170 ο ηλιακός 11.276, 5.912, 1.469· το βήμα 16 bit του 171 είναι 6 T η γραμμή)
OLD = {0: (14209, 7311, 1722), 1: (14209, 7311, 1722), 2: (14209, 7311, 1722),
       3: (14209, 7311, 1722), 4: (23247, 9435, 1724), 5: (7475, 5183, 1724),
       6: (11149, 6553, 1556), 7: (7475, 5183, 1724)}
NOW = {0: (11228, 5864, 1461), 1: (11228, 5864, 1461), 2: (11228, 5864, 1461),
       3: (11228, 5864, 1461), 4: (18282, 7542, 1463), 5: (5966, 4186, 1461),
       6: (11144, 6548, 1549), 7: (5966, 4186, 1461)}       # βήμα 171
CEIL = {k: tuple(v + v // 100 for v in t) for k, t in NOW.items()}

FAIL = []


def check(ok, msg):
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ ") + msg)
    if not ok:
        FAIL.append(msg)


def dims(a, kind):
    for size in range(4):
        w = a.struct_dims[kind * 8 + size * 2]
        if w:
            return size, w, a.struct_dims[kind * 8 + size * 2 + 1]


def addr(x, y):
    return (y & 7) * 0x800 + (((y >> 3) * SCR_W + x + 2 * CAM.off) & 0x7FF)


def wraps():
    """(σειρά χαρακτήρων, x) όπου τυλίγει το δαχτυλίδι μέσα στην εικόνα."""
    out = []
    for r in range(PLAY // 8):
        st = (r * SCR_W + 2 * CAM.off) & 0x7FF
        if st + SCR_W > 0x800:
            out.append((r, 0x800 - st))
    return out


def cases(a, rnd):
    """(είδος, όνομα, (cx, cy), clip)."""
    full = (0, SCR_W, 0, PLAY)
    r, xw = wraps()[0]
    out = []
    for kind in range(8):
        size, w, h = dims(a, kind)

        def at(fx, fy):                 # fx = 2 cx + 72 - w/2, fy = 8 cy + 48 - h/2
            return (fx + w // 2 - 4 * -CAM.tx) // 2, (fy + h // 2 - 16 * -CAM.ty) // 8
        c = [("ολόκληρη", at(32, 40), full)]
        for k in (2, w // 2, w - 2):
            c += [(f"αριστερά -{k}", at(-k, 40), full),
                  (f"δεξιά +{k}", at(SCR_W - w + k, 40), full)]
        for k in (8, h // 2, h - 8):
            c += [(f"πάνω -{k}", at(32, -k), full),
                  (f"κάτω +{k}", at(32, PLAY - h + k), full)]
        cx, cy = at(32, 40)
        fx, fy = CAM.sx(cx) - w // 2, CAM.sy(cy) - h // 2
        c += [(f"clip πάνω +{s}", (cx, cy), (0, SCR_W, fy + s, PLAY)) for s in range(1, 8)]
        for dx in (1, w // 2, w - 1):
            c.append((f"τύλιγμα {dx}", at(xw - dx, 8 * r - h // 2 + 4), full))
        c += [(f"στήλη {x0 - fx}", (cx, cy), (x0, x0 + 4, 0, PLAY))
              for x0 in range(0, SCR_W, 4) if x0 + 4 > fx and x0 < fx + w]
        c += [(f"κελί {x0 - fx},{y0 - fy}", (cx, cy), (x0, x0 + 2, y0, y0 + 8))
              for y0 in range(0, PLAY, 8) for x0 in range(0, SCR_W, 2)
              if fx - 2 < x0 < fx + w and fy - 8 < y0 < fy + h]
        for i in range(12):
            x0, y0 = rnd.randrange(0, SCR_W - 1), rnd.randrange(0, PLAY - 1)
            cl = (x0, rnd.randrange(x0 + 1, SCR_W + 1), y0, rnd.randrange(y0 + 1, PLAY + 1))
            c.append((f"τυχαίο {i}", at(rnd.randrange(-w, SCR_W) & ~1,
                                        rnd.randrange(-h, PLAY) & ~7), cl))
        out += [(kind,) + x for x in c]
    return out


class Rig:
    def __init__(self, sym):
        self.sym = sym
        m = self.m = cpc.CPC()
        m.run_frames(60)
        assert m.quickload(TO.SNA, start=False), "quickload απέτυχε"
        m.poke(sym["CAM_TX"], CAM.tx & 0xFF)
        m.poke(sym["CAM_TY"], CAM.ty & 0xFF)
        m.set_pc(sym["START"])
        n = 0
        while m.peek(sym["DONE_FLAG"]) != 0x5A and n < 400:
            m.run_frames(1)
            n += 1
        assert m.peek(sym["DONE_FLAG"]) == 0x5A, "η πλήρης σχεδίαση δεν τελείωσε"
        self.b6 = cpc._lib.cpcemu_ram_ptr(m._h, 6)
        self.b7 = cpc._lib.cpcemu_ram_ptr(m._h, 7)
        self.stb = TO.layout_addr("G_struct_tbl")

    def b7_read(self, at, n):
        return ctypes.string_at(ctypes.addressof(self.b7.contents) + at - 0x4000, n)

    def b7_poke(self, at, v):
        self.b7[at - 0x4000] = v

    def find7(self, label, pat, span=200):
        at = self.sym[label]
        i = self.b7_read(at, span).find(bytes(pat))
        assert i >= 0, f"δεν βρέθηκε το {[hex(x) for x in pat]} μετά το {label}"
        return at + i

    def draw(self, a, kind, cx, cy, cl, rnd):
        """(µs, λάθος bytes) μιας κλήσης του ob_struct."""
        m, sym = self.m, self.sym
        size, w, h = dims(a, kind)
        rec = bytes([cx & 255, cy & 255, kind, size, S.DS_ACTIVE, 0, 0, 0])
        ctypes.memmove(ctypes.addressof(self.b6.contents) + self.stb - 0x4000, rec, 8)
        base = bytes(rnd.getrandbits(8) for _ in range(0x4000))
        m.write_ram(0xC000, base)
        x0, x1, y0, y1 = cl
        m.write_ram(sym["CLIP_X0"], bytes([x0, x1, y0, y1]))
        ob = sym["OB_STRUCT"]
        code = [0xF3, 0x31, 0x00, 0x01, 0x01, 0xC6, 0x7F, 0xED, 0x49,   # η 6 μέσα
                0x3E, 0, 0xCD, ob & 255, ob >> 8, 0x18, 0xFE]
        ph = codeat.phase(m)
        m.write_ram(PROBE, bytes(code))
        m.set_pc(PROBE)
        end, t = PROBE + len(code) - 2, 0
        while not (end <= m.pc <= end + 2):
            m.run_us(1)
            t += 1
            if t > 200_000:
                return None, 0x4000
        got = bytes(m.read_ram(0xC000, 0x4000))
        cv = Canvas()
        for y in range(PLAY):
            for x in range(SCR_W):
                cv.buf[y * SCR_W + x] = base[addr(x, y)]
        name = S.struct_sprite(a, kind, size)
        S.blit(cv, a.rows(name), CAM.sx(S.signed(cx & 255)) - w // 2,
               CAM.sy(S.signed(cy & 255)) - h // 2, a.smap[name].masked,
               S.Clip(x0, y0, x1, y1))
        want = bytearray(base)
        for y in range(PLAY):
            for x in range(SCR_W):
                want[addr(x, y)] = cv.buf[y * SCR_W + x]
        return t - ph, sum(1 for p, q in zip(got, want) if p != q)


# --- ΟΙ ΔΙΑΔΡΟΜΟΙ ΚΑΙ ΟΙ ΓΩΝΙΕΣ (βήμα 171) ---------------------------------
# Το ολόκληρο, (ob_put7, ob_put7v), µs: μετρημένα στο βήμα 171, ταβάνι +1 %.
D_NOW = {"corr_dr": (3051, 3087), "corr_dl": (3051, 3087), "corr_h": (1316, 1350),
         "corr_v": (1707, 1743), "cn_hpat": (538, 566), "cn_hpatw": (538, 566),
         "cn_vpat": (1428, 1462), "cn_vpatw": (1428, 1462)}


def drawings(a):
    """(όνομα, διεύθυνση στην 7, w, h, γραμμές με μάσκα όπως τα sprites)."""
    import corner
    from refrender import flip_byte
    out = []
    for n in ("corr_dr", "corr_dl", "corr_h", "corr_v"):
        s = a.smap[n]
        out.append((n, TO.layout_addr(f"G_{n}"), s.w, s.h, a.rows(n)))
    base = TO.layout_addr("G_corner_spr")
    for name, off in corner.spr_data()[1]:
        x0, y0, w, h, rows = corner.patch(name[3])
        if name.endswith("w"):
            rows = [[(flip_byte(m), flip_byte(d)) for m, d in reversed(r)] for r in rows]
        out.append((name, base + off, w, h, [bytes(b for c in r for b in c) for r in rows]))
    return out


def put7(X, a, d, fx, fy, cl, flip, rnd):
    """(µs, λάθος bytes) ενός ob_put7 / ob_put7v."""
    m, sym = X.m, X.sym
    name, at, w, h, rows = d
    base = bytes(rnd.getrandbits(8) for _ in range(0x4000))
    m.write_ram(0xC000, base)
    m.write_ram(sym["OB_SRC"], bytes([at & 255, at >> 8]))
    m.write_ram(sym["OB_X"], (fx & 0xFFFF).to_bytes(2, "little"))
    m.write_ram(sym["OB_Y"], (fy & 0xFFFF).to_bytes(2, "little"))
    m.write_ram(sym["OB_W"], bytes([w, h]))
    m.write_ram(sym["CLIP_X0"], bytes(cl))
    ent = sym["OB_PUT7V" if flip else "OB_PUT7"]
    code = [0xF3, 0x31, 0x00, 0x01, 0x01, 0xC6, 0x7F, 0xED, 0x49,
            0xCD, ent & 255, ent >> 8, 0x18, 0xFE]
    ph = codeat.phase(m)
    m.write_ram(PROBE, bytes(code))
    m.set_pc(PROBE)
    end, t = PROBE + len(code) - 2, 0
    while not (end <= m.pc <= end + 2):
        m.run_us(1)
        t += 1
        if t > 200_000:
            return None, 0x4000
    got = bytes(m.read_ram(0xC000, 0x4000))
    cv = Canvas()
    for y in range(PLAY):
        for x in range(SCR_W):
            cv.buf[y * SCR_W + x] = base[addr(x, y)]
    S.blit(cv, rows[::-1] if flip else rows, fx, fy, True, S.Clip(cl[0], cl[2], cl[1], cl[3]))
    want = bytearray(base)
    for y in range(PLAY):
        for x in range(SCR_W):
            want[addr(x, y)] = cv.buf[y * SCR_W + x]
    return t - ph, sum(1 for p, q in zip(got, want) if p != q)


def dcases(d, rnd):
    """(όνομα, fx, fy, clip) για ένα σχέδιο."""
    name, at, w, h, rows = d
    full = (0, SCR_W, 0, PLAY)
    r, xw = wraps()[0]
    c = [("ολόκληρο", 30, 40, full)]
    for k in sorted({1, w // 2, w - 1} - {0}):
        c += [(f"αριστερά -{k}", -k, 40, full), (f"δεξιά +{k}", SCR_W - w + k, 40, full)]
    for k in sorted({1, 5, h // 2, h - 1} - {0}):
        c += [(f"πάνω -{k}", 30, -k, full), (f"κάτω +{k}", 30, PLAY - h + k, full)]
    for dx in sorted({0, w // 2, w - 1}):
        c.append((f"τύλιγμα {dx}", xw - dx, 8 * r - h // 2 + 4, full))
    c += [(f"στήλη {x0}", 30, 40, (x0, x0 + 4, 0, PLAY)) for x0 in range(28, 30 + w, 4)]
    c += [(f"κελί {x0},{y0}", 30, 40, (x0, x0 + 2, y0, y0 + 8))
          for x0 in range(28, 30 + w, 2) for y0 in range(32, 40 + h, 8)]
    for i in range(12):
        x0, y0 = rnd.randrange(0, SCR_W - 1), rnd.randrange(0, PLAY - 1)
        c.append((f"τυχαίο {i}", rnd.randrange(-w, SCR_W), rnd.randrange(-h, PLAY),
                  (x0, rnd.randrange(x0 + 1, SCR_W + 1), y0, rnd.randrange(y0 + 1, PLAY + 1))))
    return c


def corridors(X, a, rnd):
    ds = drawings(a)
    allc = [(d, flip) + cc for d in ds for flip in (False, True) for cc in dcases(d, rnd)]
    bad, whole = [], {}
    for d, flip, label, fx, fy, cl in allc:
        us, n = put7(X, a, d, fx, fy, cl, flip, rnd)
        if n:
            bad.append((d[0], flip, label, n))
        if label == "ολόκληρο":
            whole[(d[0], flip)] = us
    check(not bad, f"διάδρομοι και γωνίες: {len(allc)} περιπτώσεις, ob_put7 και ob_put7v, "
                   f"κάθε byte ίδιο με την αναφορά" + (f" — λάθος {bad[:6]}" if bad else ""))
    for n, (c0, c1) in D_NOW.items():
        got = (whole[(n, False)], whole[(n, True)])
        ceil = (c0 + c0 // 100, c1 + c1 // 100)
        check(got[0] <= ceil[0] and got[1] <= ceil[1],
              f"{n:<9} ολόκληρο {got[0]:>5} µs, καθρεφτισμένο {got[1]:>5} (ταβάνια {ceil})")
    # --- αρνητικά στο s7_clipv ---
    sub = allc[::4]                     # και τα δύο, ανακατεμένα
    neg = [("το s7_clipv χωρίς το neg (το βήμα +w)",
            [(X.find7("S7_CLIPV", [0xED, 0x44]) + k, 0) for k in range(2)]),
           ("το s7_clipv χωρίς το dec (η γραμμή h - st)",
            [(X.find7("S7_CLIPV", [0x3D, 0x90]), 0)]),
           ("το s7_clipv χωρίς το 0 πίσω στο πάνω byte του βήματος",
            [(X.find7("S7_CLIPV", [0xAF, 0x32, (X.sym["S7_W"] + 2) & 255]), 0)])]
    for label, patch in neg:
        keep = [(at, X.b7_read(at, 1)[0]) for at, _ in patch]
        for at, v in patch:
            X.b7_poke(at, v)
        n = sum(1 for d, flip, _, fx, fy, cl in sub if put7(X, a, d, fx, fy, cl, flip, rnd)[1])
        for at, v in keep:
            X.b7_poke(at, v)
        check(n > 0, f"ΑΡΝΗΤΙΚΟ: με {label} λάθος σε {n} από τις {len(sub)} περιπτώσεις")


def main():
    sym = TO.build()
    a = S.Assets()
    X = Rig(sym)
    rnd = random.Random(170)
    allc = cases(a, rnd)
    print(f"το τύλιγμα στην εικόνα: {wraps()}, {len(allc)} περιπτώσεις")

    # --- η σύγκριση και το κόστος ---
    worst = {}
    for kind, label, (cx, cy), cl in allc:
        us, bad = X.draw(a, kind, cx, cy, cl, rnd)
        if bad:
            check(False, f"{KINDS[kind]} {label}: {bad} λάθος bytes (clip {cl})")
        g = label.split()[0]
        worst[(kind, g)] = max(worst.get((kind, g), 0), us or 10**9)
    check(not FAIL, f"{len(allc)} περιπτώσεις, κάθε byte της οθόνης ίδιο με την αναφορά")
    for kind in range(8):
        got = (worst[(kind, "ολόκληρη")], worst[(kind, "στήλη")], worst[(kind, "κελί")])
        ok = all(g <= c and g < o for g, c, o in zip(got, CEIL[kind], OLD[kind]))
        check(ok, f"{KINDS[kind]:<10} ολόκληρη {got[0]:>6} µs, στήλη {got[1]:>5}, κελί "
                  f"{got[2]:>5} (ταβάνια {CEIL[kind]}, βήμα 169 {OLD[kind]})")

    # --- αρνητικά: ο κώδικας της 7 πειραγμένος ---
    mpage = TO.layout_addr("G_st_mask") >> 8
    sub = [c for c in allc if c[1].split()[0] in ("αριστερά", "τύλιγμα", "clip", "ολόκληρη")]
    neg = [("χωρίς το σπάσιμο του τυλίγματος (jr z,$+2 στο s7_row)",
            [(X.find7("S7_ROW", [0xF6, 0xF8, 0x3C, 0x28]) + 4, 0)]),
           ("το H πίσω κατά 0 αντί για 8 (s7_wchk)",
            [(X.find7("S7_WCHK", [0xD6, 0x08]) + 1, 0)]),
           ("χωρίς το clip από αριστερά (χωρίς το call ob_addu)",
            [(X.find7("S7_CLIP", [0xCD, sym["OB_ADDU"] & 255, sym["OB_ADDU"] >> 8]) + k, 0)
             for k in range(3)]),
           ("η πρώτη γραμμή χωρίς το ob_st (xor a)",
            [(X.find7("S7_CLIP", [0x3A, sym["OB_ST"] & 255, sym["OB_ST"] >> 8]) + k, v)
             for k, v in enumerate((0xAF, 0, 0))]),
           ("το βήμα της γραμμής 0 (χωρίς το ld (s7_w+1),a)",
            [(X.find7("S7_CLIP", [0x32, (sym["S7_W"] + 1) & 255, (sym["S7_W"] + 1) >> 8]) + k, 0)
             for k in range(3)]),
           ("ο πίνακας της μάσκας μία σελίδα πιο πέρα",
            [(X.find7("S7_CLIP", [0x06, mpage]) + 1, mpage + 1)])]
    for label, patch in neg:
        keep = [(at, X.b7_read(at, 1)[0]) for at, _ in patch]
        for at, v in patch:
            X.b7_poke(at, v)
        n = sum(1 for kind, _, (cx, cy), cl in sub if X.draw(a, kind, cx, cy, cl, rnd)[1])
        for at, v in keep:
            X.b7_poke(at, v)
        check(n > 0, f"ΑΡΝΗΤΙΚΟ: με {label} λάθος σε {n} από τις {len(sub)} περιπτώσεις")
    corridors(X, a, rnd)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
