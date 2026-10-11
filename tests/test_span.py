#!/usr/bin/env python3
"""Το ob_blit ένα sprite τη φορά, απέναντι σε μοντέλο (βήμα 108, DESIGN §8.4).

ΓΙΑΤΙ ΧΩΡΙΣΤΑ. Από το βήμα 108 τα τεταρτημόρια των θόλων και των δακτυλίων
ζωγραφίζονται σε κομμάτια των οκτώ γραμμών πηγής, και σε καθένα μόνο το
διάστημα που έχει κάτι (src/span.asm, build/span_tables.asm). Τα test_object
και test_scroll τα βλέπουν μέσα από σκηνές, με πέντε κάμερες και τέσσερις
λωρίδες· εδώ κάθε μέγεθος, δακτύλιος και θόλος, και οι τέσσερις
προσανατολισμοί, σε τυχαίες θέσεις — και έξω από το κάδρο — με τυχαίο clip:
ολόκληρο, στήλη των 4 bytes, σειρά των 16 γραμμών, ή ό,τι να 'ναι. Ο βρόχος
του ob_blit άλλαξε για όλα τα sprites (κομμάτια, πηγή και βήμα μέσα στις
εντολές), οπότε και τα ίδια τεταρτημόρια χωρίς διαστήματα, και αδιαφανή.

Το μοντέλο είναι η πρόζα του §8.2 και του SPRITES.md §2: για κάθε byte του
clip που καλύπτει το sprite, η γραμμή πηγής (ανάποδα αν καθρεφτίζεται κάθετα),
το ζεύγος (ανάποδα και με το flip_mode0 αν οριζόντια), και η οθόνη στο
#C000 + (y & 7) * #800 + ((y >> 3) * 80 + x + cam_p) & #7FF. Η οθόνη ξεκινά
με σκουπίδια, και όλα τα 16 KB της συγκρίνονται.

Και ο ΧΡΟΝΟΣ: όλα τα τεταρτημόρια με τα διαστήματα κοστίζουν λιγότερο από τα
ίδια χωρίς — μετρημένο, όχι υποτιθέμενο.

Αρνητικά, με τον κώδικα πειραγμένο: ο πίνακας μία στήλη πιο δεξιά, η κάθετη
κατεύθυνση των ομάδων ανάποδα, το DE που δεν ξαναβρίσκεται σε κάθε ομάδα, η
πηγή που δεν μετακινείται με το διάστημα, και το κομμάτι που δεν κόβεται
στις γραμμές που μένουν. Και ένα που φαίνεται μόνο στον χρόνο: η άδεια ομάδα
που ζωγραφίζει γράφει μόνο ζεύγη (#FF, 0), άρα την ίδια εικόνα, αργότερα.
"""
import ctypes, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import cpc                                               # noqa: E402
from test_object import build, SNA                       # noqa: E402

PROBE, FLAG = 0x3E00, 0x3EFF
FAIL = 0
FLIP = [((x & 0xAA) >> 1) | ((x & 0x55) << 1) for x in range(256)]
SIZES = (("s", 8, 32), ("m", 12, 48), ("l", 16, 64))


def check(ok, msg):
    global FAIL
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ ") + msg)
    if not ok:
        FAIL += 1


def layout():
    out = {}
    for line in open(os.path.join(ROOT, "build", "layout.asm"), encoding="utf-8"):
        p = line.split()
        if len(p) >= 3 and p[1] == "equ" and p[2].startswith("#"):
            out[p[0].upper()] = int(p[2][1:], 16)
    return out


def model(scr, b6, cam, c):
    src, x, y, w, h, fl, (x0, x1, y0, y1) = c
    masked = not fl & 4
    stride = w * 2 if masked else w
    for yy in range(max(y, y0), min(y + h, y1)):
        r = yy - y
        if fl & 2:
            r = h - 1 - r
        row = src - 0x4000 + r * stride
        for xx in range(max(x, x0), min(x + w, x1)):
            k = xx - x
            if fl & 1:
                k = w - 1 - k
            a = (yy & 7) * 0x800 + (((yy >> 3) * 80 + xx + cam) & 0x7FF)
            if masked:
                m, d = b6[row + 2 * k], b6[row + 2 * k + 1]
                if fl & 1:
                    m, d = FLIP[m], FLIP[d]
                scr[a] = (scr[a] & m) | d
            else:
                scr[a] = b6[row + k]


class Z80:
    def __init__(self, sym, patch=()):
        self.sym = sym
        m = self.m = cpc.CPC()
        m.run_frames(60)
        assert m.quickload(SNA, start=False), "quickload απέτυχε"
        for at, v in patch:
            m.poke(at, v)
        self.b6 = ctypes.string_at(cpc._lib.cpcemu_ram_ptr(m._h, 6), 0x4000)

    def w16(self, name, v):
        self.m.poke(self.sym[name], v & 255)
        self.m.poke(self.sym[name] + 1, (v >> 8) & 255)

    def blit(self, c, cam, spt, scr):
        """Ενα blit· γυρίζει (οθόνη, us)."""
        s, m = self.sym, self.m
        src, x, y, w, h, fl, (x0, x1, y0, y1) = c
        m.write_ram(0xC000, bytes(scr))
        self.w16("OB_SRC", src)
        self.w16("OB_X", x)
        self.w16("OB_Y", y)
        m.poke(s["OB_W"], w)
        m.poke(s["OB_H"], h)
        m.poke(s["OB_FL"], fl)
        for k, v in zip(("CLIP_X0", "CLIP_X1", "CLIP_Y0", "CLIP_Y1"), (x0, x1, y0, y1)):
            m.poke(s[k], v)
        self.w16("CAM_P", cam)
        self.w16("OB_SPT", spt)
        at = s["OB_BSPAN"] if spt else s["OB_BLIT"]
        # di · sp · τράπεζα 6 · call · ld a,#5A · ld (FLAG),a · jr $
        code = [0xF3, 0x31, 0x00, 0x01, 0x01, 0xC6, 0x7F, 0xED, 0x49,
                0xCD, at & 255, at >> 8, 0x3E, 0x5A, 0x32, FLAG & 255, FLAG >> 8,
                0x18, 0xFE]
        m.write_ram(PROBE, bytes(code))
        m.poke(FLAG, 0)
        m.set_pc(PROBE)
        t = 0
        while m.peek(FLAG) != 0x5A:
            m.run_us(20)
            t += 20
            if t > 400_000:
                return None, t
        return bytearray(m.read_ram(0xC000, 0x4000)), t


def cases(L, rnd, n):
    """(πίνακας, sprite) ανά μέγεθος, δακτύλιος και θόλος, προσανατολισμός."""
    out = []
    for size, w, h in SIZES:
        for kind in ("ring", "dome"):
            src = L[f"G_{kind.upper()}_{size.upper()}_NW"]
            for fl in range(4):
                for i in range(n):
                    j = i % 4
                    if j == 0:                       # όλο το κάδρο
                        clip = (0, 80, 0, 160)
                    elif j == 1:                     # μια στήλη, όπως ανατολικά/δυτικά
                        cx = rnd.randrange(0, 77)
                        clip = (cx, cx + 4, 0, 160)
                    elif j == 2:                     # μια σειρά, όπως βόρεια/νότια
                        cy = rnd.randrange(0, 145)
                        clip = (0, 80, cy, cy + 16)
                    else:
                        a, b = sorted(rnd.sample(range(81), 2))
                        c, d = sorted(rnd.sample(range(161), 2))
                        clip = (a, b, c, d)
                    x0, x1, y0, y1 = clip
                    x = rnd.randrange(x0 - w + 1, x1)
                    y = rnd.randrange(y0 - h + 1, y1)
                    out.append(((size, kind), (src, x, y, w, h, fl, clip)))
    return out


def run(sym, L, patch=(), n=6, plain=True, seed=108):
    """Η πρώτη διαφορά από το μοντέλο ή None, και οι χρόνοι (με, χωρίς)."""
    rnd = random.Random(seed)
    z = Z80(sym, patch)
    t_span = t_plain = 0
    for (size, kind), c in cases(L, rnd, n):
        spt = sym[f"SPT_{size.upper()}"] + (0 if kind == "ring" else c[4] // 8)
        cam = rnd.randrange(0, 1024) * 2
        scr = bytearray(rnd.randbytes(0x4000))
        want = bytearray(scr)
        model(want, z.b6, cam, c)
        for path in (("span", spt),) + ((("plain", 0),) if plain else ()):
            got, t = z.blit(c, cam, path[1], scr)
            if got is None:
                return f"{kind}_{size} fl {c[5]} {path[0]}: κόλλησε ({c})", 0, 0
            if got != want:
                bad = [i for i in range(0x4000) if got[i] != want[i]]
                return (f"{kind}_{size} fl {c[5]} {path[0]}: {len(bad)} bytes, πρώτο "
                        f"#{0xC000 + bad[0]:04X} — x {c[1]} y {c[2]} clip {c[6]} cam {cam}"), 0, 0
            if path[0] == "span":
                t_span += t
            else:
                t_plain += t
    return None, t_span, t_plain


def others(sym, L, rnd, n=40):
    """Ο ίδιος βρόχος για ό,τι δεν έχει διαστήματα: με μάσκα, και αδιαφανή."""
    z = Z80(sym)
    for i in range(n):
        if i % 2:                                     # με μάσκα: διάδρομος, ό,τι να 'ναι
            src, w, h, fl = L["G_CORR_DR"], 8, 16, rnd.randrange(4)
        else:                                         # αδιαφανές: bytes ενός τεταρτημορίου
            src, w, h, fl = L["G_DOME_M_NW"] + rnd.randrange(0, 256), rnd.randrange(1, 13), \
                rnd.randrange(1, 30), 4 | (rnd.randrange(2) << 1)
        a, b = sorted(rnd.sample(range(81), 2))
        c, d = sorted(rnd.sample(range(161), 2))
        c_ = (src, rnd.randrange(a - w + 1, b), rnd.randrange(c - h + 1, d), w, h, fl, (a, b, c, d))
        cam = rnd.randrange(0, 1024) * 2
        scr = bytearray(rnd.randbytes(0x4000))
        want = bytearray(scr)
        model(want, z.b6, cam, c_)
        got, _ = z.blit(c_, cam, 0, scr)
        if got != want:
            return f"fl {fl} w {w} h {h}: {c_}"
    return None


def main():
    sym = build()
    L = layout()
    why, ts, tp = run(sym, L)
    n = len(SIZES) * 2 * 4 * 6
    check(why is None, f"{n} τεταρτημόρια, με και χωρίς διαστήματα, = το μοντέλο"
          + (f" — {why}" if why else ""))
    if why is None:
        check(ts < tp, f"με τα διαστήματα {ts} us, χωρίς {tp} us ({100 * ts // max(tp, 1)}%)")
    why = others(sym, L, random.Random(1080))
    check(why is None, "40 άλλα sprites, με μάσκα σε κάθε προσανατολισμό και αδιαφανή, = το μοντέλο"
          + (f" — {why}" if why else ""))

    m = Z80(sym).m

    def find(at, pat, span=200):
        i = m.read_ram(sym[at], span).find(bytes(pat))
        assert i >= 0, f"δεν βρέθηκε το {[hex(b) for b in pat]} στο {at}"
        return sym[at] + i

    w = lambda a: [a & 255, a >> 8]
    tbl = sym["SPT_L"]
    neg = [("ο πίνακας μία στήλη πιο δεξιά",
            [(tbl + k, m.peek(tbl + k) + 0x10 - 1) for k in range(1, 16) if m.peek(tbl + k)]),
           ("οι ομάδες ανάποδα στο κάθετο καθρέφτισμα", [(find("SP_FIRST", [0x06, 0xFF]) + 1, 1)]),
           ("το DE χωρίς scr_addr σε κάθε ομάδα",
            [(find("SPG_YY", [0xC3] + w(sym["SCR_ADDR"])), 0xC9)]),
           ("η πηγή που δεν ακολουθεί το διάστημα",
            [(find("SPG_O", [0x22] + w(sym["OBL_P"] + 1)) + i, 0) for i in range(3)]),
           ("το κομμάτι ως το τέλος της ομάδας, όχι του blit",
            [(find("SP_GRP", [0x38]), 0x18)])]
    for label, patch in neg:
        why, _, _ = run(sym, L, patch, n=4, plain=False)
        check(why is not None, f"ΑΡΝΗΤΙΚΟ: με {label} αποτυγχάνει" + (f" ({why[:100]})" if why else ""))
    # Η ΑΔΕΙΑ ΟΜΑΔΑ ΔΕΝ ΦΑΙΝΕΤΑΙ ΣΤΗΝ ΕΙΚΟΝΑ: αν ζωγράφιζε, θα έγραφε ζεύγη
    # (#FF, 0), που δεν αλλάζουν τίποτα. Φαίνεται μόνο στον χρόνο.
    _, t0, _ = run(sym, L, n=4, plain=False)
    why, t1, _ = run(sym, L, [(find("SPG_NONE", [0x22] + w(sym["OBL_K"] + 1)) + i, 0)
                              for i in range(3)], n=4, plain=False)
    check(why is None and t1 > t0, f"ΑΡΝΗΤΙΚΟ: με την άδεια ομάδα να ζωγραφίζει, η ίδια "
                                   f"εικόνα σε {t1} us αντί για {t0}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
