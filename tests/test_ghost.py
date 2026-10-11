#!/usr/bin/env python3
"""Το φάντασμα απευθείας, απέναντι σε ένα μοντέλο σε Python (DESIGN §9.3).

Τα άλλα τεστ κοιτούν το φάντασμα απ' έξω: ότι δεν αφήνει ίχνος
(test_build), ότι το χειρότερο χωρά ολόκληρο (test_reveal), ότι σηκώνεται
κάτω από τη λίστα αλλαγών (test_fit, test_reveal). Κανένα δεν κοιτά ΠΟΥ
ζωγραφίζεται: η αναίρεση γράφει πίσω στις ίδιες διευθύνσεις που έσωσε, οπότε
ένα φάντασμα στη λάθος θέση φεύγει εξίσου καθαρά. Στο βήμα 58 δύο σκόπιμα
λάθη στο τύλιγμα του δαχτυλιδιού πέρασαν όλα τα τεστ.

Τρεις ισχυρισμοί:

  1. gh_box, gh_mark, gh_swap, gh_undo, gh_reset και gh_setpen, καλεσμένα
     απευθείας πάνω σε οθόνη γεμάτη θόρυβο, από τέσσερα cam_p (τα δύο
     τυλίγουν το δαχτυλίδι μέσα σε γραμμή) και με αλλαγές του clip: μετά από
     ΚΑΘΕ πράξη η οθόνη, το αρχείο ως το gh_ptr και το περίγραμμα είναι ίσα
     με του μοντέλου, byte προς byte. Το μοντέλο είναι η πρόζα: το ob_clip, η
     διεύθυνση οθόνης του §8.2, η εγγραφή (διεύθυνση, πλάτος, ύψος, bytes), οι
     τέσσερις πλευρές του πλαισίου, το «χωράει».
  2. Το όριο του αρχείου ακριβώς: ένα σημάδι (12 bytes) μπαίνει όταν μένουν
     12, όχι όταν μένουν 11 — και τότε δεν αγγίζει ούτε την οθόνη, ούτε το
     περίγραμμα, ούτε το byte μετά το αρχείο, όπου αρχίζει κώδικας.
  3. Δύο αρνητικά: το `inc d` του gh_wrap γίνεται nop (μια γραμμή που περνά
     το #FF πέφτει 256 bytes πίσω), και το όριο ανεβαίνει ένα byte.
"""
import os, random, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/vasilhs/cpcemu")

from test_build import build, SNA                                       # noqa: E402

FAIL = []
PROBE = 0x3F10                  # όπως το test_sim: πάνω από το τέλος της τράπεζας 0
NOISE = bytes((i * 29 + 7) & 0xFF for i in range(0x4000))
CAMS = (0, 2044, 1996, 1024)    # 2044, 1996: γραμμές που τυλίγουν στο 2 KB


def check(ok, msg):
    print(("OK " if ok else "ΛΑΘΟΣ ") + msg)
    if not ok:
        FAIL.append(msg)


def consts():
    """Οι σταθερές equ δεν μπαίνουν στο .sym του rasm: από τις πηγές τους."""
    v = {}
    for path, names in ((os.path.join(ROOT, "build", "layout.asm"), {"PAGE2_TOP"}),
                        (os.path.join(ROOT, "src", "const.asm"),
                         {"GH_BUF", "GH_HDR", "GH_EDGE", "GH_SIDE", "GH_LOG"}),
                        (os.path.join(ROOT, "src", "tiles.asm"), {"VIEW_TW", "VIEW_TH"})):
        for line in open(path, encoding="utf-8"):
            m = re.match(r"^(\w+)\s+equ\s+([^;]+)", line)
            if m and m.group(1) in names:
                v[m.group(1)] = eval(m.group(2).replace("#", "0x"), {}, dict(v))
    return v


# --- το μοντέλο ------------------------------------------------------------

def sext(a):
    a &= 0xFF
    return a - 256 if a > 127 else a


def clip(pos, ln, lo, hi):
    """ob_clip: (αρχή, πλήθος) ή None. pos 16 bit προσημασμένο, ln 0..255."""
    d = (lo - pos) & 0xFFFF
    if not d & 0x8000:                  # ξεκινά πριν από το lo
        if d > 255:
            return None
        n = ln - d
        if n <= 0:
            return None
        start = lo
    else:
        if (pos & 0xFFFF) >> 8:         # δεξιά/κάτω από την οθόνη
            return None
        start, n = pos & 0xFF, ln
    if hi - start <= 0:
        return None
    return start, min(n, hi - start)


def scr(cam, x, y):
    """§8.2: η γραμμή y είναι στο μπλοκ y & 7, και κάθε μπλοκ είναι δαχτυλίδι 2 KB."""
    return 0xC000 + (y & 7) * 0x800 + (((y >> 3) * 80 + x + cam) & 0x7FF)


def cells(a, w, h):
    """Οι διευθύνσεις ενός ορθογωνίου από τη διεύθυνση της κεφαλίδας του."""
    blk, p = (a - 0xC000) >> 11, (a - 0xC000) & 0x7FF
    for j in range(h):
        line = blk + j
        pj = p + 80 * (line >> 3)
        for i in range(w):
            yield 0xC000 + (line & 7) * 0x800 + ((pj + i) & 0x7FF)


class Ghost:
    def __init__(self, k, cam):
        self.k, self.cam = k, cam
        self.scr = bytearray(NOISE)
        self.log, self.bb, self.pen = bytearray(), [255, 0, 255, 0], 0
        self.clip = [0, 80, 0, 160]

    def put(self, x, y, w, h):
        if len(self.log) + 4 + w * h > self.k["GH_LOG"]:
            return                      # δεν χωρά: τίποτα
        for ax, (st, ln) in enumerate(((x, w), (y, h))):
            if st < self.bb[2 * ax]:
                self.bb[2 * ax] = st
            if (st + ln) & 0xFF >= self.bb[2 * ax + 1]:
                self.bb[2 * ax + 1] = (st + ln) & 0xFF
        a = scr(self.cam, x, y)
        self.log += bytes((a & 0xFF, a >> 8, w, h))
        for c in cells(a, w, h):
            self.log.append(self.scr[c - 0xC000])
            self.scr[c - 0xC000] = self.pen

    def rect(self, x, y, w, h):
        cy = clip(y, h, self.clip[2], self.clip[3])
        cx = cy and clip(x, w, self.clip[0], self.clip[1])
        if cx:
            self.put(cx[0], cy[0], cx[1], cy[1])

    def box(self, bx, by, bw, bh):
        e = self.k["GH_EDGE"]
        self.rect(bx, by, bw, e)
        self.rect(bx, by + sext(bh - e), bw, e)
        if bh - 2 * e <= 0:
            return
        self.rect(bx, by + e, 1, bh - 2 * e)
        self.rect(bx + sext(bw - 1), by + e, 1, bh - 2 * e)

    def mark(self, col, row):
        if col < self.k["VIEW_TW"] and row < self.k["VIEW_TH"]:
            self.put(4 * col + 1, 16 * row + 6, 2, 4)

    def swap(self):
        i = 0
        while i < len(self.log):
            a, w, h = self.log[i] | (self.log[i + 1] << 8), self.log[i + 2], self.log[i + 3]
            i += 4
            for c in cells(a, w, h):
                self.log[i], self.scr[c - 0xC000] = self.scr[c - 0xC000], self.log[i]
                i += 1

    def reset(self):
        self.log, self.bb = bytearray(), [255, 0, 255, 0]


# --- ο Z80 -----------------------------------------------------------------

def boot(sym, cam, patch=()):
    from cpc import CPC
    m = CPC()
    m.run_frames(60)
    assert m.quickload(SNA, start=False)
    for a, v in patch:
        m.poke(a, v)
    m.write_ram(0xC000, NOISE)
    m.poke(sym["CAM_P"], cam & 0xFF)
    m.poke(sym["CAM_P"] + 1, cam >> 8)
    call(m, [0xCD, sym["GH_RESET"] & 0xFF, sym["GH_RESET"] >> 8])
    return m


def call(m, code):
    code = [0xF3, 0x31, 0x00, 0x01] + code + [0x18, 0xFE]       # di, ld sp, ..., jr $
    m.write_ram(PROBE, bytes(code))
    m.set_pc(PROBE)
    end, t = PROBE + len(code) - 2, 0
    while m.pc != end:
        m.run_us(50)
        t += 50
        assert t < 2_000_000, f"δεν γύρισε: pc #{m.pc:04X}"


def word(m, a):
    return m.peek(a) | (m.peek(a + 1) << 8)


def run(sym, k, cam, ops, patch=()):
    """Οι πράξεις στον Z80 και στο μοντέλο. Γυρίζει (πράξεις, πρώτη διαφορά)."""
    m, g = boot(sym, cam, patch), Ghost(k, cam)
    fn = lambda n: [0xCD, sym[n] & 0xFF, sym[n] >> 8]
    for n, op in enumerate(ops):
        kind = op[0]
        if kind == "box":
            _, x, y, w, h = op
            for nm, v in (("GH_BX", x & 0xFFFF), ("GH_BY", y & 0xFFFF)):
                m.poke(sym[nm], v & 0xFF)
                m.poke(sym[nm] + 1, v >> 8)
            m.poke(sym["GH_BW"], w)
            m.poke(sym["GH_BH"], h)
            call(m, fn("GH_BOX"))
            g.box(x, y, w, h)
        elif kind == "mark":
            _, c, r = op
            call(m, [0x06, c & 0xFF, 0x0E, r & 0xFF] + fn("GH_MARK"))
            g.mark(c & 0xFF, r & 0xFF)
        elif kind == "pen":
            call(m, [0x3E, op[1]] + fn("GH_SETPEN"))
            g.pen = m.peek(sym["HUD_SOLID"] + op[1] - 8)        # ο πίνακας, όχι η ρουτίνα
        elif kind == "clip":
            for j, v in enumerate(op[1:]):
                m.poke(sym["CLIP_X0"] + j, v)
            g.clip = list(op[1:])
        elif kind == "swap":
            call(m, fn("GH_SWAP"))
            g.swap()
        elif kind == "undo":
            call(m, fn("GH_UNDO"))
            g.swap()
            g.reset()
        elif kind == "reset":
            call(m, fn("GH_RESET"))
            g.reset()
        ptr = word(m, sym["GH_PTR"]) - k["GH_BUF"]
        got = {"οθόνη": m.read_ram(0xC000, 0x4000),
               "αρχείο": m.read_ram(k["GH_BUF"], ptr) if 0 <= ptr <= k["GH_LOG"] else ptr,
               "περίγραμμα": list(m.read_ram(sym["GH_BBX"], 4))}
        want = {"οθόνη": bytes(g.scr), "αρχείο": bytes(g.log), "περίγραμμα": g.bb}
        bad = [nm for nm in got if got[nm] != want[nm]]
        if bad:
            return n + 1, f"πράξη {n + 1} {op}: {', '.join(bad)}" + (
                f" (gh_ptr +{ptr}, μοντέλο +{len(g.log)})" if "αρχείο" in bad else "")
    return len(ops), None


def program(seed, n):
    """Πράξεις: πλαίσια στα πραγματικά μεγέθη και μικρότερα, μέσα και έξω από
    το κάδρο· σημάδια μέσα και έξω· ανταλλαγές· αλλαγές πένας και clip."""
    rnd, ops = random.Random(seed), []
    for _ in range(n):
        r = rnd.random()
        if r < 0.45:
            x = rnd.choice([-40, -7, -3, -1, 0, 1, 5, 20, 37, 60, 74, 75, 78, 79, 80, 85, 300])
            y = rnd.choice([-130, -20, -3, -2, -1, 0, 1, 10, 40, 80, 130, 150,
                            157, 158, 159, 160, 170, 400])
            w, h = rnd.choice([(6, 22), (4, 16), (34, 124), (26, 92), (16, 64), (1, 1),
                               (2, 3), (3, 4), (3, 5), (2, 5), (10, 4), (1, 30), (30, 1),
                               (80, 129)])
            ops.append(("box", x, y, w, h))
        elif r < 0.70:
            ops.append(("mark", rnd.choice([-1, 0, 1, 7, 18, 19, 20, 25, 200]),
                        rnd.choice([-1, 0, 1, 4, 8, 9, 10, 15, 130])))
        elif r < 0.80:
            ops.append(("swap",))
        elif r < 0.85:
            ops.append(("undo",))
        elif r < 0.90:
            ops.append(("pen", rnd.choice([8, 9, 12, 15])))      # 8-15 (βήμα 103)
        elif r < 0.96:
            ops.append(("clip", rnd.choice([0, 0, 4, 20]), rnd.choice([80, 80, 60, 24]),
                        rnd.choice([0, 0, 16, 64]), rnd.choice([160, 160, 144, 80])))
        else:
            ops.append(("reset",))
    return ops


def limit(sym, k, free, patch=()):
    """Σημάδι με `free` bytes ελεύθερα στο αρχείο: (μπήκε, gh_ptr, οθόνη ίδια,
    περίγραμμα ίδιο, byte μετά το αρχείο ίδιο)."""
    m = boot(sym, 0, patch)
    end = k["GH_BUF"] + k["GH_LOG"]
    m.poke(sym["GH_PTR"], (end - free) & 0xFF)
    m.poke(sym["GH_PTR"] + 1, (end - free) >> 8)
    before = (m.read_ram(0xC000, 0x4000), m.read_ram(sym["GH_BBX"], 4), m.peek(end))
    call(m, [0x06, 3, 0x0E, 2, 0xCD, sym["GH_MARK"] & 0xFF, sym["GH_MARK"] >> 8])
    ptr = word(m, sym["GH_PTR"])
    return (ptr == end - free + 12, ptr - (end - free), m.read_ram(0xC000, 0x4000) == before[0],
            m.read_ram(sym["GH_BBX"], 4) == before[1], m.peek(end) == before[2])


def main():
    sym, _ = build()
    k = consts()
    k["GH_BUF"] = k["PAGE2_TOP"]

    # --- 1. το μοντέλο, πράξη προς πράξη --------------------------------
    total = 0
    for i, cam in enumerate(CAMS):
        n, bad = run(sym, k, cam, program(58 + i, 300))
        total += n
        check(bad is None, f"cam_p {cam}: οθόνη, αρχείο και περίγραμμα ίσα με το "
                           f"μοντέλο μετά από κάθε μία από 300 πράξεις"
                           + (f" — όχι στην {bad}" if bad else ""))

    # --- 2. το όριο του αρχείου -----------------------------------------
    fit12 = limit(sym, k, 12)
    check(fit12 == (True, 12, False, False, True),
          f"με 12 bytes ελεύθερα το σημάδι μπαίνει ολόκληρο και σταματά στο τέλος "
          f"του αρχείου: {fit12}")
    fit11 = limit(sym, k, 11)
    check(fit11 == (False, 0, True, True, True),
          f"με 11 όχι: ούτε οθόνη, ούτε περίγραμμα, ούτε το byte μετά το αρχείο — {fit11}")

    # --- 3. αρνητικά ----------------------------------------------------
    wrap = sym["GH_WRAP"]
    with_inc = boot(sym, 0).peek(wrap) == 0x14                  # inc d
    n, bad = run(sym, k, 2044, program(58 + 1, 300), patch=[(wrap, 0x00)])
    check(with_inc and bad is not None,
          f"ΑΡΝΗΤΙΚΟ: με το gh_wrap χωρίς inc d το μοντέλο διαφωνεί — {bad}")
    put, want = sym["GHR_PUT"], (0x10000 + 4 - (k["GH_BUF"] + k["GH_LOG"] + 1)) & 0xFFFF
    m = boot(sym, 0)
    at = next((put + j for j in range(32) if m.peek(put + j) == 0x21
               and word(m, put + j + 1) == want), None)
    check(at is not None, f"το ghr_put ξεκινά από 4 - όριο = #{want:04X}")
    if at is not None:
        up = limit(sym, k, 11, patch=[(at + 1, (want - 1) & 0xFF), (at + 2, (want - 1) >> 8)])
        check(up[0] and not up[4],
              f"ΑΡΝΗΤΙΚΟ: με το όριο ένα byte πιο πάνω το σημάδι μπαίνει σε 11 bytes "
              f"και γράφει το πρώτο byte μετά το αρχείο — {up}")

    print(f"\n{total} πράξεις σε {len(CAMS)} κάμερες")
    if FAIL:
        print(f"{len(FAIL)} ΛΑΘΗ")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
