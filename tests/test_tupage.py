#!/usr/bin/env python3
"""Οι σελίδες του tutorial (βήμα 175, DESIGN §9.6, src/tpage.asm).

Ο παίκτης: «Το tutorial δεν έχει οδηγίες. Βάλε να έχει οδηγίες.
Χρησιμοποίησε και αρχείο στην δισκέττα αν χρειάζεσαι για τα κείμενά του.»
Διάλεξε μια σελίδα σε κάθε βήμα, σε όλη την οθόνη όπως η βοήθεια, στα
αγγλικά. Η πρόζα, και τι ελέγχεται:

  ΚΕΙΜΕΝΟ   το src/tupages.txt περνά τους κανόνες του tools/tupages.py (ως 76
            στήλες, ως 20 γραμμές, μόνο η γραμματοσειρά, ζυγοί αστερίσκοι, 16
            σελίδες), το build/tutor.txt είναι η εικόνα του, και κάθε αρχή του
            tp_idx είναι μετά από ένα «@». Αρνητικά: μια σελίδα από κάθε παράβαση.
  ΔΙΣΚΟΣ    το TUTOR.TXT στον κατάλογο (χρήστης 0, έκταση 0), τα blocks του ίσα
            με το build/tutor.txt, η BANK6.BIN χωρίς τα μηδενικά του τέλους της,
            και κανένα αρχείο ως τα slots του §11.
  ΣΕΛΙΔΕΣ   από τη δισκέτα, TUTORIAL: η εισαγωγή και το βήμα 1 πριν από
            οτιδήποτε άλλο, ένα ένα, ΔΙΑΒΑΣΜΕΝΑ ΑΠΟ ΤΗΝ ΟΘΟΝΗ γράμμα γράμμα και
            χρώμα χρώμα απέναντι στο αρχείο· μετά το παιχνίδι. Ο ηλιακός με τα
            πλήκτρα του παίκτη φέρνει τη σελίδα του βήματος 2. Το «?» την
            ξαναδείχνει, και ένα δεύτερο «?» πάνω της τη βοήθεια. Χωρίς δίσκο, η
            σελίδα λέει πού είναι. Σε άλλον κόσμο καμία σελίδα, και το «?» είναι
            η βοήθεια. Και μετά τις σελίδες η επιλογή κτιρίου μένει ακέραιη: το
            βήμα του κέρσορα στο PLACE δεν κουνά την κάμερα (το σώσιμο του §11).
  ΚΟΣΤΟΣ    frames ως να φανεί η σελίδα, από το FIRE και από την επιλογή.

Αρνητικά στο παιχνίδι: το tp_idx με τη σελίδα 2 στη θέση της 3· ο αστερίσκος
χωρίς χρώμα (xor 0)· το tuo_go χωρίς τη σελίδα του βήματος 2 (cp 2 -> cp 3)·
και το «?» χωρίς το tutorial (jr nz -> jr).
"""
import os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import tupages as TP                                     # noqa: E402
import menuread as MR                                    # noqa: E402
import hudread as HR                                     # noqa: E402
from dsk import Dsk                                      # noqa: E402

DSK = os.path.join(ROOT, "build", "habitat.dsk")
FAIL = []
FOOT = "*ANY KEY*  GO ON             *?*  WHAT EVERY BUTTON DOES"   # src/tpage.asm, ο λόγος
NODISC = ["*THIS PAGE IS ON THE GAME'S DISC*", "",
          "PUT THE DISC BACK IN THE DRIVE, AND PRESS *?* TO SEE IT."]
HELP_FOOT = "THE LETTER ON A BUTTON IS ITS KEY."
SAVE_T0 = 24                                             # src/save.asm


def check(ok, msg):
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ ") + msg)
    if not ok:
        FAIL.append(msg)
    return ok


def build():
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "mkdsk.py")],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"mkdsk απέτυχε:\n{r.stdout}{r.stderr}")
    sym = {}
    for line in open(os.path.join(ROOT, "src", "rasmoutput.sym"), encoding="utf-8",
                     errors="replace"):
        p = line.split()
        if len(p) >= 2 and p[1].startswith("#"):
            sym[p[0].upper()] = int(p[1][1:], 16)
    return sym


# --------------------------------------------------------------------------
# ΚΕΙΜΕΝΟ
# --------------------------------------------------------------------------
def text():
    pages = TP.parse()
    try:
        TP.check(pages)
        ok = True
    except TP.Fail as e:
        ok = str(e)
    check(ok is True, f"ΚΕΙΜΕΝΟ: το src/tupages.txt περνά τους κανόνες ({ok})")
    data, idx = TP.image(pages)
    disk = open(os.path.join(ROOT, "build", "tutor.txt"), "rb").read()
    check(data == disk and len(idx) == TP.TP_N and all(data[i - 1] == 64 for i in idx),
          f"ΚΕΙΜΕΝΟ: το build/tutor.txt είναι η εικόνα του ({len(disk)} bytes), "
          f"{len(idx)} σελίδες, κάθε αρχή μετά από «@»")
    src = open(TP.SRC, encoding="utf-8").read()
    first = next(l for l in src.splitlines() if l and not l.startswith((";", "@")))
    bad = [("μια γραμμή 77 στηλών", src.replace(first, "X" * 77, 1)),
           ("πεζά", src.replace(first, first.lower(), 1)),
           ("ένας αστερίσκος μόνος", src.replace(first, "*" + first[:70], 1)),
           ("21 γραμμές σε μια σελίδα", src.replace(first, "\n".join(["A"] * 21), 1)),
           ("15 σελίδες", src[:src.rindex("\n@")] + "\n"),
           ("«@» μέσα σε γραμμή", src.replace(first, first[:40] + "@", 1))]
    for what, s in bad:
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                         encoding="utf-8") as f:
            f.write(s)
        try:
            TP.check(TP.parse(f.name))
            got = None
        except TP.Fail as e:
            got = str(e)
        os.unlink(f.name)
        check(got is not None, f"ΑΡΝΗΤΙΚΟ ΚΕΙΜΕΝΟΥ: {what} -> «{got}»")
    return data, idx


# --------------------------------------------------------------------------
# ΔΙΣΚΟΣ
# --------------------------------------------------------------------------
def disc(data):
    d = Dsk(DSK)
    ent, top = None, 0
    for si in range(4):
        sec = d.sector(0, 0xC1 + si)
        for e in range(0, len(sec), 32):
            x = sec[e:e + 32]
            if x[0] == 0xE5:
                continue
            top = max([top] + list(x[16:32]))
            if x[:13] == b"\0TUTOR   TXT\0":
                ent = x
    blocks = [b for b in ent[16:32] if b] if ent else []
    got = b""
    for b in blocks:
        for s in (2 * b, 2 * b + 1):
            got += d.sector(s // 9, 0xC1 + s % 9)
    check(ent is not None and got[:len(data)] == data,
          f"ΔΙΣΚΟΣ: το TUTOR.TXT στον κατάλογο, blocks {blocks}, ίσο με το build/tutor.txt")
    b6 = open(os.path.join(ROOT, "build", "bank6.bin"), "rb").read()
    trim = len(b6.rstrip(b"\0"))
    b6e = None
    for si in range(4):
        sec = d.sector(0, 0xC1 + si)
        for e in range(0, len(sec), 32):
            if sec[e:e + 13] == b"\0BANK6   BIN\0":
                b6e = sec[e:e + 32]
    b6len = None
    if b6e:
        s = 2 * b6e[16]
        hdr = d.sector(s // 9, 0xC1 + s % 9)
        b6len = hdr[64] | hdr[65] << 8 | hdr[66] << 16   # το μήκος της κεφαλίδας AMSDOS
    check(b6len == trim and trim < len(b6) - 8192,
          f"ΔΙΣΚΟΣ: η BANK6.BIN {b6len} bytes, χωρίς τα {len(b6) - trim} μηδενικά του τέλους")
    last = 2 * top + 1
    free = SAVE_T0 * 9 - 1 - last
    check(last // 9 < SAVE_T0,
          f"ΔΙΣΚΟΣ: τα αρχεία ως τον τομέα {last} (track {last // 9}), {free} ελεύθεροι "
          f"ως τα slots στο track {SAVE_T0}")


def boot6(dsk, garbage):
    """Η τράπεζα 6 ένα δευτερόλεπτο μετά την εκκίνηση του πλανήτη 0. Με
    garbage, γεμάτη #A5 πριν από το RUN: ένα 6128 δεν ξεκινά με μηδενική μνήμη."""
    from cpc import CPC
    import cpc
    m = CPC()
    m.run_frames(300)
    b6 = cpc._lib.cpcemu_ram_ptr(m._h, 6)
    if garbage:
        for i in range(0x4000):
            b6[i] = 0xA5
    m.insert_disc(dsk)
    m.type_text('|disc\n', hold_frames=4, gap_frames=8)
    m.run_frames(60)
    m.type_text('run"habitat\n', hold_frames=4, gap_frames=8)
    MR.pick(m, MR.syms(ROOT), 0)
    m.run_frames(900)
    return bytes(b6[i] for i in range(0x4000))


def zero6():
    """Ο ΦΟΡΤΩΤΗΣ ΜΗΔΕΝΙΖΕΙ ΤΗΝ ΤΡΑΠΕΖΑ 6 (src/boot.asm), αφού η BANK6.BIN δεν
    φέρνει πια τα 12 KB μηδενικά της. Με σκουπίδια πριν από την εκκίνηση η 6
    είναι ίδια με μιας καθαρής· το αρνητικό είναι ο ίδιος δίσκος με το ldir
    του φορτωτή σβηστό (ld (hl),l / ldir -> ld (hl),l / nop nop)."""
    clean, dirty = boot6(DSK, False), boot6(DSK, True)
    raw = bytearray(open(DSK, "rb").read())
    k = raw.find(bytes([0x01, 0xFF, 0x3F, 0x75, 0xED, 0xB0]))
    bad = None
    if k >= 0 and raw.find(bytes([0x01, 0xFF, 0x3F, 0x75, 0xED, 0xB0]), k + 1) < 0:
        raw[k + 4:k + 6] = b"\0\0"
        path = os.path.join(ROOT, "build", "nozero6.dsk")
        open(path, "wb").write(raw)
        bad = boot6(path, True)
        os.unlink(path)
    nd = sum(1 for x, y in zip(clean, dirty) if x != y)
    check(nd == 0, f"ΔΙΣΚΟΣ: με σκουπίδια στην τράπεζα 6 πριν από το RUN, η 6 του "
                   f"παιχνιδιού ίδια με μιας καθαρής εκκίνησης ({nd} bytes διαφορά)")
    nb = sum(1 for x, y in zip(clean, bad) if x != y) if bad else None
    check(nb, f"ΑΡΝΗΤΙΚΟ: χωρίς το ldir του φορτωτή, {nb} bytes της 6 μένουν σκουπίδια")


# --------------------------------------------------------------------------
# ΣΕΛΙΔΕΣ
# --------------------------------------------------------------------------
def expect_rows(lines, row0):
    """{σειρά: [(χαρακτήρας, χρώμα)]} από γραμμές με «*», όπως τις γράφει το
    tp_put: πράσινα στην αρχή κάθε γραμμής, ο αστερίσκος αλλάζει χρώμα."""
    out = {}
    for k, line in enumerate(lines):
        col, cells = "g", []
        for c in line:
            if c == "*":
                col = "w" if col == "g" else "g"
                continue
            cells.append((c, col if c != " " else None))
        out[row0 + k] = cells
    return out


def page_lines(data, idx, n):
    a = idx[n]
    b = data.index(b"@", a) if b"@" in data[a:] else data.index(b"\x1a", a)
    return data[a:b].decode("ascii").replace("\r\n", "\n").rstrip("\n").split("\n")


class Screen:
    def __init__(self):
        g = HR.glyphs()
        self.white = g
        self.green = {}
        for bs, c in g.items():
            self.green.setdefault(bytes(x & 0x0F for x in bs), c)

    def read(self, m, sym, row, n=80):
        ram = HR.screen(m)
        cp = HR.cam_p(m, sym)
        out = []
        for col in range(n):
            p = cp - 160 + 80 * row + col
            cell = bytes(ram[ln * 0x800 + (p & 0x7FF)] for ln in range(8))
            if not any(cell):
                out.append((" ", None))
            elif cell in self.white:
                out.append((self.white[cell], "w"))
            elif cell in self.green:
                out.append((self.green[cell], "g"))
            else:
                out.append(("#", None))
        return out


def same(a, b):
    """Γράμματα ίδια (το 0 και το O έχουν τον ίδιο γλύφο), και το χρώμα όπου
    δεν είναι κενό."""
    for (c1, k1), (c2, k2) in zip(a, b):
        if c1.replace("0", "O") != c2.replace("0", "O"):
            return False
        if c1 != " " and k1 != k2:
            return False
    return True


def compare(S, m, sym, want):
    """Οι σειρές της οθόνης απέναντι στο want (σειρά -> κελιά από τη στήλη 2),
    και κενές όλες οι άλλες. Γυρίζει τις σειρές που διαφέρουν."""
    bad = []
    for row in range(25):
        got = S.read(m, sym, row)
        w = [(" ", None)] * 2 + want.get(row, [])
        w += [(" ", None)] * (80 - len(w))
        if not same(got, w):
            bad.append(row)
    return bad


def page_want(data, idx, n):
    lines = page_lines(data, idx, n)
    want = expect_rows(lines, 1)
    want.update(expect_rows([FOOT], 24))
    return want


class Run:
    def __init__(self, sym, planet, patches=()):
        from cpc import CPC
        import cpc
        self.sym = sym
        self.m = m = CPC()
        self.bs = MR.syms(ROOT)
        m.run_frames(300)
        m.insert_disc(DSK)
        m.type_text('|disc\n', hold_frames=4, gap_frames=8)
        m.run_frames(60)
        m.type_text('run"habitat\n', hold_frames=4, gap_frames=8)
        self.b7 = cpc._lib.cpcemu_ram_ptr(m._h, 7)
        self.b1 = cpc._lib.cpcemu_ram_ptr(m._h, 1)
        self.f_pick = MR.pick(m, self.bs, planet)
        # Ως να φορτωθεί το TEXT.BIN (ο φορτωτής, μετά την επιλογή): ως τότε
        # η τράπεζα 7 είναι μηδενικά και το tp_pg λέει «σελίδα 0».
        name = self.sym["TP_NAME"] + 1 - 0x4000
        for self.f_text in range(3000):
            if bytes(self.b7[name:name + 11]) == b"TUTOR   TXT":
                break
            m.run_frames(1)
        for fn in patches:
            fn(self)

    def pg(self):
        return self.b7[self.sym["TP_PG"] - 0x4000]

    def wait(self, want, limit=900):
        """Ως να ανοίξει η σελίδα want ΚΑΙ να γραφτεί το υποσέλιδό της, που
        μπαίνει τελευταίο: πριν από αυτό ανάβει το μοτέρ (0,46 s) και
        διαβάζονται ο κατάλογος και η σελίδα. Γυρίζει τα frames, ή None."""
        foot = "".join(c for c, _ in expect_rows([FOOT], 24)[24])
        S = Screen()
        for f in range(limit):
            if self.pg() == want:
                row = "".join(c for c, _ in S.read(self.m, self.sym, 24))[2:2 + len(foot)]
                if row.replace("0", "O") == foot.replace("0", "O"):
                    self.m.run_frames(2)
                    return f
            self.m.run_frames(1)
        return None

    def game(self, limit=900):
        """Ως να γυρίσει στο παιχνίδι: καμία σελίδα, διακοπές (το is_fc τρέχει)."""
        for f in range(limit):
            if self.pg() == 0xFF:
                a = self.m.peek(self.sym["IS_FC"])
                self.m.run_frames(2)
                if self.m.peek(self.sym["IS_FC"]) != a:
                    self.m.run_frames(20)
                    return f
            self.m.run_frames(1)
        return None

    def tap(self, key, gap=20):
        self.m.key_down(key)
        self.m.run_frames(4)
        self.m.key_up(key)
        self.m.run_frames(gap)


def solar(R):
    """Ο ηλιακός με τα πλήκτρα του παίκτη: P S, έξι δεξιά και τέσσερα πάνω από
    το σκάφος (εκεί είναι ελεύθερο, READY), και SPACE (μετά το βήμα 174)."""
    from cpc import KEY_RIGHT, KEY_UP, KEY_SPACE
    R.tap("p")
    R.tap("s")
    for _ in range(6):
        R.tap(KEY_RIGHT, 12)
    for _ in range(4):
        R.tap(KEY_UP, 12)
    ok = R.m.peek(R.sym["UI_STATE"]) == 2 and R.m.peek(R.sym["UI_BAD"]) == 0
    R.m.key_down(KEY_SPACE)
    R.m.run_frames(4)
    R.m.key_up(KEY_SPACE)
    return ok


def pages(sym, data, idx):
    from cpc import KEY_SPACE, KEY_RIGHT
    S = Screen()
    R = Run(sym, 4)
    f0 = R.wait(0)
    bad = compare(S, R.m, sym, page_want(data, idx, 0)) if f0 is not None else ["καμία"]
    check(f0 is not None and not bad,
          f"ΣΕΛΙΔΑ 0, η εισαγωγή, {f0} frames μετά την επιλογή του μενού: ίδια με το "
          f"αρχείο γράμμα γράμμα και χρώμα χρώμα (λάθος σειρές {bad})")
    R.tap(KEY_SPACE, 4)
    f1 = R.wait(1)
    bad = compare(S, R.m, sym, page_want(data, idx, 1)) if f1 is not None else ["καμία"]
    check(f1 is not None and not bad,
          f"ΣΕΛΙΔΑ 1 μετά από ένα πλήκτρο ({f1} frames): ίδια με το αρχείο (λάθος σειρές {bad})")
    R.tap(KEY_SPACE, 4)
    fg = R.game()
    check(fg is not None and R.m.peek(sym["UI_STATE"]) == 0,
          f"ΠΑΙΧΝΙΔΙ μετά από ένα ακόμη πλήκτρο ({fg} frames), στο LOOK")
    ready = solar(R)
    f2 = R.wait(2)
    bad = compare(S, R.m, sym, page_want(data, idx, 2)) if f2 is not None else ["καμία"]
    check(ready and f2 is not None and not bad,
          f"ΣΕΛΙΔΑ 2: ο ηλιακός με τα πλήκτρα (READY {ready}) τη φέρνει {f2} frames "
          f"μετά το SPACE, ίδια με το αρχείο (λάθος σειρές {bad})")
    R.tap(KEY_SPACE, 4)
    R.game()
    st, c0 = R.m.peek(sym["UI_STATE"]), R.m.peek(sym["CAM_TX"])
    R.tap(KEY_RIGHT, 40)
    check(st == 2 and R.m.peek(sym["CAM_TX"]) == c0,
          f"ΜΕΤΑ ΤΙΣ ΣΕΛΙΔΕΣ ένα βήμα του κέρσορα στο PLACE δεν κουνά την κάμερα "
          f"(cam_tx {c0} -> {R.m.peek(sym['CAM_TX'])}): το bd_select ακέραιο")
    from cpc import KEY_ESC
    R.tap(KEY_ESC)
    R.tap(KEY_ESC)
    R.tap("/", 4)
    fq = R.wait(2)
    bad = compare(S, R.m, sym, page_want(data, idx, 2)) if fq is not None else ["καμία"]
    check(fq is not None and not bad,
          f"«?»: η σελίδα του βήματος ξανά ({fq} frames), ίδια (λάθος σειρές {bad})")
    R.tap("/", 4)
    help_ok = False
    for _ in range(120):
        R.m.run_frames(5)
        row = "".join(c for c, _ in Screen().read(R.m, sym, 24))
        if R.pg() == 0xFF and HELP_FOOT in row:
            help_ok = True
            break
    check(help_ok, "«?» πάνω στη σελίδα: η βοήθεια, με το υποσέλιδό της")
    R.tap(KEY_SPACE, 4)
    check(R.game() is not None and R.m.peek(sym["UI_STATE"]) == 0,
          "και ένα πλήκτρο πίσω στο παιχνίδι")
    R.m.remove_disc()
    R.tap("/", 4)
    fn = R.wait(2)
    want = expect_rows(NODISC, 1)
    want.update(expect_rows([FOOT], 24))
    bad = compare(S, R.m, sym, want) if fn is not None else ["καμία"]
    check(fn is not None and not bad,
          f"ΧΩΡΙΣ ΔΙΣΚΟ η σελίδα λέει πού είναι ({fn} frames, λάθος σειρές {bad})")
    R.tap(KEY_SPACE, 4)
    check(R.game() is not None, "και γυρίζει στο παιχνίδι")
    return f0, f1, f2


def other(sym):
    """Ο πλανήτης 0: καμία σελίδα στην αρχή, και το «?» είναι η βοήθεια."""
    from cpc import KEY_SPACE
    R = Run(sym, 0)
    seen = set()
    for _ in range(300):
        R.m.run_frames(4)
        seen.add(R.pg())
    R.tap("/", 4)
    help_ok = False
    for _ in range(120):
        R.m.run_frames(5)
        seen.add(R.pg())
        row = "".join(c for c, _ in Screen().read(R.m, sym, 24))
        if HELP_FOOT in row:
            help_ok = True
            break
    check(seen == {0xFF} and help_ok,
          f"ΑΛΛΟΣ ΚΟΣΜΟΣ: καμία σελίδα σε 1.200 frames ({sorted(seen)}), και το «?» "
          f"είναι η βοήθεια ({help_ok})")


# --------------------------------------------------------------------------
# ΑΡΝΗΤΙΚΑ
# --------------------------------------------------------------------------
def find7(R, at, n, pat):
    b = R.b7
    o = at - 0x4000
    return [at + i for i in range(n) if all(b[o + i + k] == v for k, v in enumerate(pat))]


def negatives(sym, data, idx):
    from cpc import KEY_SPACE
    S = Screen()
    span = sym["TP_FOOT"] - sym["TP_SHOW"]

    # 1. το tp_idx με τη σελίδα 2 στη θέση της 3: η σελίδα 2 λέει το βήμα 3
    def swap_idx(R):
        o = sym["TP_IDX"] - 0x4000 + 4
        R.b7[o], R.b7[o + 1] = idx[3] & 255, idx[3] >> 8
    R = Run(sym, 4, [swap_idx])
    R.wait(0); R.tap(KEY_SPACE, 4); R.wait(1); R.tap(KEY_SPACE, 4); R.game()
    solar(R)
    f = R.wait(2)
    bad = compare(S, R.m, sym, page_want(data, idx, 2)) if f is not None else ["καμία"]
    check(bool(bad), f"ΑΡΝΗΤΙΚΟ: το tp_idx λάθος, η σελίδα 2 διαφέρει από το αρχείο στις σειρές {bad[:6]}")

    # 2. ο αστερίσκος χωρίς χρώμα: xor TP_WHITE ^ TP_GREEN -> xor 0
    def no_ink(R):
        k = find7(R, sym["TP_SHOW"], span, [0xEE, 0xF0])
        R.b7[k[0] + 1 - 0x4000] = 0
    R = Run(sym, 4, [no_ink])
    R.wait(0)
    bad = compare(S, R.m, sym, page_want(data, idx, 0))
    check(bool(bad), f"ΑΡΝΗΤΙΚΟ: ο αστερίσκος χωρίς χρώμα, η εισαγωγή διαφέρει στις σειρές {bad[:6]}")

    # 3. το tuo_go χωρίς τη σελίδα του βήματος 2: cp 2 -> cp 3 στο OV_R1, όπου
    # το βάζει το ov_install στην εκκίνηση: μετά τις πρώτες σελίδες
    def no_step2(R):
        at = sym["ZZ_TUT_END"]                   # TU_AT: ο κώδικας του tutorial στο OV_R1
        n = sym["ZZ_OV4_END"] - sym["TUO_GO"]
        o = at - 0x4000
        k = [i for i in range(n) if R.b1[o + i] == 0xFE and R.b1[o + i + 1] == 2
             and R.b1[o + i + 2] == 0xD8]
        R.b1[o + k[0] + 1] = 3
    R = Run(sym, 4)
    R.wait(0); R.tap(KEY_SPACE, 4); R.wait(1); R.tap(KEY_SPACE, 4); R.game()
    no_step2(R)
    solar(R)
    f = R.wait(2, 300)
    check(f is None, f"ΑΡΝΗΤΙΚΟ: χωρίς το «cp 2» του tuo_go ο ηλιακός δεν φέρνει σελίδα ({f})")

    # 4. το «?» χωρίς το tutorial: το jr nz,hp_h του hp_show -> jr hp_h
    def plain_help(R):
        hs = sym["HP_SHOW"]
        k = [hs + i for i in range(12) if R.m.peek(hs + i) == 0xB7 and R.m.peek(hs + i + 1) == 0x20]
        R.m.poke(k[0] + 1, 0x18)
    R = Run(sym, 4)
    R.wait(0); R.tap(KEY_SPACE, 4); R.wait(1); R.tap(KEY_SPACE, 4); R.game()
    plain_help(R)
    R.tap("/", 4)
    seen = set()
    for _ in range(100):
        R.m.run_frames(4)
        seen.add(R.pg())
    check(seen == {0xFF}, f"ΑΡΝΗΤΙΚΟ: με το «?» χωρίς το tutorial δεν φαίνεται σελίδα ({sorted(seen)})")


def main():
    sym = build()
    data, idx = text()
    disc(data)
    zero6()
    f0, f1, f2 = pages(sym, data, idx)
    other(sym)
    negatives(sym, data, idx)
    print(f"\nκόστος: η εισαγωγή {f0} frames μετά την επιλογή, η σελίδα 1 {f1} μετά το "
          f"πλήκτρο, η σελίδα 2 {f2} μετά το SPACE του ηλιακού (0,46 s είναι το μοτέρ)")
    print("ΟΛΑ ΚΑΛΑ" if not FAIL else f"{len(FAIL)} ΑΠΟΤΥΧΙΕΣ")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
