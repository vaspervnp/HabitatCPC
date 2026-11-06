#!/usr/bin/env python3
"""Η σελίδα των πόρων (βήμα 191, DESIGN §9.7): το V, και το κουμπί του στη
ΔΙΑΧΕΙΡΙΣΗ.

Ο παίκτης ζήτησε μια οθόνη που δείχνει σε αριθμούς όλους τους πόρους, κόκκινο
ό,τι είναι λίγο, πράσινο ό,τι είναι πολύ, και άλλο χρώμα το απλά OK. Διάλεξε
μια σελίδα όπως του G, στο V και στη ΔΙΑΧΕΙΡΙΣΗ, με τα όρια του ίδιου του
παιχνιδιού, και λευκό το OK. Τι ελέγχεται, από τη δισκέτα:

  ΚΕΙΜΕΝΟ   τα πεδία «^a»-«^z» μόνο στη σελίδα 23, και μόνο αυτά εκεί.
            Αρνητικά: ένα «^a» στη σελίδα του G, ένα «^A» στη σελίδα των
            πόρων, ένα «^{» (όχι πεδίο), ένα πεζό γράμμα στο κείμενο. ΚΑΙ ΤΑ
            ΚΕΙΜΕΝΑ ΤΟΥ ΚΩΔΙΚΑ: η γραμματοσειρά τελειώνει στο «Z» από αυτό το
            βήμα, οπότε κανένα «"..."» των src/*.asm δεν έχει χαρακτήρα πάνω
            από αυτό (αρνητικό: το «x1» των ταχυτήτων όπως ήταν).
  V         στον πλανήτη 0, από το LOOK: η σελίδα 23, ΔΙΑΒΑΣΜΕΝΗ ΑΠΟ ΤΗΝ ΟΘΟΝΗ
            γράμμα γράμμα και χρώμα χρώμα (λευκό, πράσινο, ΚΑΙ κόκκινο) απέναντι
            στο αρχείο, με κάθε αριθμό σε πέντε στήλες στο χρώμα που δίνει η
            αναφορά εδώ (rule) από τη μνήμη. Ενα πλήκτρο πίσω, στο LOOK.
  ΟΡΙΑ      σε παύση, οι πόροι γραμμένοι στη μνήμη στις άκρες κάθε κανόνα: ένα
            κάτω από το κόκκινο όριο, πάνω του, ένα κάτω από το πράσινο, πάνω
            του — και το ρεύμα με PWR- και χωρίς συλλέκτη, η αποθήκη γεμάτη,
            ένα κάτω, στη μισή και ένα κάτω, πέντε ψηφία στα νομίσματα.
  ΔΙΑΧΕΙΡΙΣΗ  M V ανοίγει την ίδια σελίδα· M, έξι δεξιά και SPACE επίσης·
            μετά το LOOK. Το «?» πάνω στη σελίδα δείχνει τη βοήθεια.
  ΒΟΗΘΕΙΑ   η οθόνη βοήθειας έχει το ALL RESOURCES και τη γραμμή του στη θέση 34
            (RESOURCES σκέτο είναι η ομάδα E).

Αρνητικά, με τον κώδικα πειραγμένο στη μνήμη: ο κανόνας του μετάλλου λευκός,
το SPARES_MAX ένα παραπάνω, το νερό με 2 x ζωντανούς, το πρόσημο του ρεύματος
ανάποδα, η αποθήκη χωρίς το «+1» της μισής, το άθροισμα της αποθήκης από το
ec_wcap (το λάθος που έγινε στο χτίσιμο), οι αριθμοί χωρίς κενά μπροστά, το V
έξω από τη μπάρα των ομάδων, και το κουμπί του που ανοίγει το G.
"""
import glob, os, re, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import tupages as TP                                     # noqa: E402
import hudread as HR                                     # noqa: E402
import test_tupage as TT                                 # noqa: E402

FAIL = []
PG_GOALS, PG_RES = 21, 23                                # src/const.asm
UI_LOOK = 0
STORE_BASE, EC_CAP = 750, 600                            # src/const.asm
FIELDS = "abcdefghijklmnopqrstuvwxyz"


def check(ok, msg):
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ ") + msg)
    if not ok:
        FAIL.append(msg)
    return ok


def layout(name):
    for line in open(os.path.join(ROOT, "build", "layout.asm"), encoding="utf-8"):
        if line.startswith(name + " "):
            return int(line.split("#")[1].split()[0], 16)
    raise KeyError(name)


# --------------------------------------------------------------------------
# Η ΑΝΑΦΟΡΑ: οι τιμές από τη μνήμη, και το χρώμα κάθε πεδίου
# --------------------------------------------------------------------------
def values(R):
    """{πεδίο: τιμή}, και ό,τι χρειάζονται οι κανόνες."""
    m, sym = R.m, R.sym
    ec = layout("G_econ_state")
    w = lambda a: m.peek(a) | m.peek(a + 1) << 8
    v = {FIELDS[i]: w(ec + 2 * i) for i in range(21)}
    wcap = w(sym["EC_WCAP"])
    v["v"] = wcap
    v["w"] = sum(w(ec + 2 * i) for i in range(1, 14))
    v["x"] = wcap + STORE_BASE - EC_CAP
    ex = layout("G_node_occ") + 240 + 6 - 0x4000
    v["y"] = R.b6[ex] | R.b6[ex + 1] << 8
    v["z"] = m.peek(ec + 58)
    sign = chr(m.peek(sym["HU_PWR"] + 3))
    return v, sign


def colour(f, v, sign):
    """Ο κανόνας του πεδίου f, γραμμένος από τον πίνακα που διάλεξε ο παίκτης
    (DESIGN §9.7) και όχι από το src/tpage.asm: «r» λίγο, «g» πολύ, «w» αρκετό."""
    x, alive = v[f], v["z"]

    def lohi(lo, hi):
        if x < lo:
            return "r"
        return "g" if hi > 0 and x >= hi else "w"
    if f == "a":                                        # νερό: R1, και τα 3/4 του χώρου
        return lohi(alive + alive // 2, v["v"] - v["v"] // 4)
    if f == "b":                                        # γεύματα: ένα και τρία ανά ζωντανό
        return lohi(alive, 3 * alive)
    if f == "c":
        return lohi(10, 100)
    if f in "deknl":                                    # μέταλλο, βιοπλαστικό, άμυλο, λαχανικά, κρέας
        return lohi(30, 100)
    if f in "fhim":                                     # επεξεργαστές, φάρμακα, όπλα, βότανα
        return lohi(1, 10)
    if f == "g":                                        # spares: η SPARES σταματά στα 20
        return lohi(4, 20)
    if f == "o":                                        # ρεύμα: το πρόσημο του HUD, και τα 3/4
        if sign == "-":
            return "r"
        return lohi(0, v["p"] - v["p"] // 4)
    if f == "t":                                        # οξυγόνο: όσο αναπνέεται, και ένα τέταρτο
        return lohi(v["u"], v["u"] + v["u"] // 4)
    if f == "w":                                        # αποθήκη: γεμάτη, ή κάτω από τη μισή
        if x >= v["x"]:
            return "r"
        return "g" if 2 * x < v["x"] else "w"
    return "w"


def want_rows(data, idx, v, sign):
    """{σειρά: [(χαρακτήρας, χρώμα)]}: η σελίδα, με τα πεδία σε πέντε στήλες στο
    χρώμα τους, και το υποσέλιδο."""
    out = {}
    for k, line in enumerate(TT.page_lines(data, idx, PG_RES)):
        col, cells, i = "g", [], 0
        while i < len(line):
            c = line[i]
            if c == "*":
                col = "w" if col == "g" else "g"
            elif c == "^":
                f = line[i + 1]
                i += 1
                ink = colour(f, v, sign)
                cells += [(d, None if d == " " else ink) for d in f"{v[f]:5d}"]
                col = "w"                               # το rs_field γυρίζει στο λευκό
            else:
                cells.append((c, col if c != " " else None))
            i += 1
        out[1 + k] = cells
    out.update(TT.expect_rows([TT.FOOT], 24))
    return out


class Screen:
    """Το TT.Screen με το κόκκινο (pen 1) μαζί: ο γλύφος ως λευκός, ως
    πράσινος (τα κάτω μισά των bytes) και ως κόκκινος (τα πάνω)."""
    def __init__(self):
        self.ink = {}
        for g, c in HR.glyphs().items():
            for k, msk in (("w", 0xFF), ("g", 0x0F), ("r", 0xF0)):
                self.ink.setdefault(bytes(x & msk for x in g), (c, k))

    def read(self, m, sym, row, n=80):
        ram = HR.screen(m)
        cp = HR.cam_p(m, sym)
        out = []
        for col in range(n):
            p = cp - 160 + 80 * row + col
            cell = bytes(ram[ln * 0x800 + (p & 0x7FF)] for ln in range(8))
            out.append((" ", None) if not any(cell) else self.ink.get(cell, ("#", None)))
        return out


def compare(S, R, want):
    bad = []
    for row in range(25):
        got = S.read(R.m, R.sym, row)
        w = [(" ", None)] * 2 + want.get(row, [])
        w += [(" ", None)] * (80 - len(w))
        if not TT.same(got, w):
            bad.append(row)
    return bad


def shown(S, R, rows):
    """Οι σειρές όπως φαίνονται, με τα κόκκινα [σε αγκύλες] και τα πράσινα σε
    πεζά: για το μήνυμα μιας αποτυχίας."""
    out = []
    for row in rows:
        s = ""
        for c, k in S.read(R.m, R.sym, row):
            s += f"[{c}]" if k == "r" else (c.lower() if k == "g" else c)
        out.append(f"{row}:{s.rstrip()}")
    return " | ".join(out)


class Run(TT.Run):
    def __init__(self, sym, planet=0):
        super().__init__(sym, planet)
        import cpc
        self.b6 = cpc._lib.cpcemu_ram_ptr(self.m._h, 6)

    def wait_res(self, limit=900):
        return self.wait(PG_RES, limit)

    def open_v(self):
        self.tap("v", 4)
        return self.wait_res()

    def back(self):
        from cpc import KEY_SPACE
        self.tap(KEY_SPACE, 4)
        return self.game() is not None and self.pg() == 0xFF \
            and self.m.peek(self.sym["UI_STATE"]) == UI_LOOK


# --------------------------------------------------------------------------
# ΚΕΙΜΕΝΟ
# --------------------------------------------------------------------------
def text():
    data = open(os.path.join(ROOT, "build", "tutor.txt"), "rb").read()
    pages = TP.parse()
    _, idx = TP.image(pages)
    low = [k for k, (title, _, body) in enumerate(pages)
           if re.search(r"\^[a-z]", title + "".join(t for t, _ in body))]
    used = set(re.findall(r"\^([a-z])", pages[PG_RES][0] + "".join(t for t, _ in pages[PG_RES][2])))
    check(len(pages) == PG_RES + 1 and low == [PG_RES] and used == set(FIELDS) - {"s"},
          f"ΚΕΙΜΕΝΟ: {len(pages)} σελίδες, πεδία «^a»-«^z» μόνο στις {low}, όλα εκτός "
          f"από το «^s» (το EC_MPOWER): λείπουν {sorted(set(FIELDS) - {'s'} - used)}")
    src = open(TP.SRC, encoding="utf-8").read()
    goal = src.index("@MILESTONES")
    gline = next(l for l in src[goal:].splitlines()[1:] if "^" in l)
    res = src.index("@RESOURCES")
    rline = next(l for l in src[res:].splitlines()[1:] if "^" in l)
    bad = [("ένα «^a» στη σελίδα του G", src.replace(gline, re.sub(r"\^.", "^a", gline, 1), 1)),
           ("ένα «^A» στη σελίδα των πόρων", src.replace(rline, re.sub(r"\^.", "^A", rline, 1), 1)),
           ("ένα «^{» στη σελίδα των πόρων", src.replace(rline, re.sub(r"\^.", "^{", rline, 1), 1)),
           ("ένα πεζό γράμμα στο κείμενό της", src.replace(rline, rline.replace("OXYGEN", "Oxygen"), 1))]
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
    src = {os.path.basename(f): open(f, encoding="utf-8", errors="replace").read()
           for f in sorted(glob.glob(os.path.join(ROOT, "src", "*.asm")))}
    over = above_z(src)
    check(not over, f"ΚΕΙΜΕΝΑ ΚΩΔΙΚΑ: κανένα πάνω από το «Z» ({over[:3]})")
    old = dict(src)
    old["uitext.asm"] = old["uitext.asm"].replace('"  ",SMALL_X,"1 "', '"  x1 "')
    check(above_z(old), "ΑΡΝΗΤΙΚΟ: το «x1» όπως ήταν ως το βήμα 190 -> βρέθηκε")
    return data, idx


def above_z(src):
    """Τα «"..."» των db των src/*.asm με χαρακτήρα πάνω από το «Z»: ό,τι
    τυπώνεται με τη γραμματοσειρά Mode 1 (tools/pack.py, FONT_N). Όχι τα
    include, τα incbin και τα save, που είναι ονόματα αρχείων."""
    out = []
    for name, text in src.items():
        for n, line in enumerate(text.splitlines(), 1):
            code = line.split(";")[0]
            if not re.match(r"\s*(\w+:)?\s*db\b", code, re.I):
                continue
            for m in re.finditer(r'"([^"]*)"', code):
                if any(ord(c) > ord("Z") for c in m.group(1)):
                    out.append(f"{name}:{n}")
    return out


# --------------------------------------------------------------------------
# V, ΟΡΙΑ, ΔΙΑΧΕΙΡΙΣΗ, ΒΟΗΘΕΙΑ
# --------------------------------------------------------------------------
def page_ok(S, R, data, idx):
    """Η σελίδα στην οθόνη απέναντι στην αναφορά. Γυρίζει (λάθος σειρές, τιμές)."""
    v, sign = values(R)
    bad = compare(S, R, want_rows(data, idx, v, sign))
    return bad, v, sign


def first(sym, data, idx):
    S = Screen()
    R = Run(sym)
    R.game()
    f = R.open_v()
    bad, v, _ = page_ok(S, R, data, idx) if f is not None else (["καμία"], {}, "")
    check(f is not None and not bad,
          f"V: η σελίδα {PG_RES} {f} frames μετά το πλήκτρο, ίδια με το αρχείο, με τα "
          f"νούμερα και τα χρώματα της μνήμης (ζωντανοί {v.get('z')}, μέταλλο {v.get('d')}, "
          f"αποθήκη {v.get('w')}/{v.get('x')}, λάθος σειρές {bad})"
          + ("" if not bad or bad == ["καμία"] else " — " + shown(S, R, bad)))
    check(R.back(), "και ένα πλήκτρο πίσω στο παιχνίδι, στο LOOK")
    return R


# Οι άκρες: για κάθε κανόνα (κόκκινο όριο LO, πράσινο HI) ένα σενάριο με όλους
# τους πόρους στο ίδιο σημείο. Ζωντανοί 37 (μονός: το 1,5 x κόβει), ο χώρος του
# νερού 700, οι συλλέκτες 720 (HI 540), η ζήτηση οξυγόνου 40 (HI 50).
ALIVE, WCAP, PCAP, O2USE = 37, 700, 720, 40
LIMITS = {"a": (55, 525), "b": (37, 111), "c": (10, 100), "d": (30, 100), "e": (30, 100),
          "f": (1, 10), "g": (4, 20), "h": (1, 10), "i": (1, 10), "k": (30, 100),
          "l": (30, 100), "m": (1, 10), "n": (30, 100), "o": (0, 540), "t": (40, 50)}
# Η αποθήκη χωρά 850: γεμάτη, ένα κάτω, στη μισή, ένα κάτω — με τα ρομπότ
# (πάντα λευκά) να συμπληρώνουν το άθροισμα· στη μισή και κάτω τα άλλα στο
# κόκκινο όριο, αλλιώς το άθροισμά τους ξεπερνά ήδη τη μισή. Και το ρεύμα
# χωρίς συλλέκτη: ποτέ πράσινο.
CAP = WCAP + STORE_BASE - EC_CAP
LO, HI = (lambda lo, hi: lo), (lambda lo, hi: hi)
EDGES = [("ένα κάτω από το κόκκινο, PWR-, γεμάτη", lambda lo, hi: lo - 1, "-", CAP, PCAP),
         ("στο κόκκινο όριο, ένα κάτω από γεμάτη", LO, "+", CAP - 1, PCAP),
         ("ένα κάτω από το πράσινο", lambda lo, hi: hi - 1, "+", 0, PCAP),
         ("στο πράσινο όριο", HI, "+", 0, PCAP),
         ("η αποθήκη στη μισή", LO, "+", (CAP + 1) // 2, PCAP),
         ("η αποθήκη ένα κάτω από τη μισή", LO, "+", (CAP + 1) // 2 - 1, PCAP),
         ("χωρίς συλλέκτη, PWR+", HI, "+", 0, 0)]


def set_edge(R, pick, sign, used, coins=12345, pcap=PCAP):
    m, sym = R.m, R.sym
    ec = layout("G_econ_state")

    def w(a, x):
        m.poke(a, x & 255)
        m.poke(a + 1, x >> 8)
    m.poke(ec + 58, ALIVE)
    w(sym["EC_WCAP"], WCAP)
    w(ec + 30, pcap)
    w(ec + 40, O2USE)
    for f, (lo, hi) in LIMITS.items():
        x = max(0, pick(lo, hi))
        w(ec + 2 * FIELDS.index(f), x)
    rest = sum(m.peek(ec + 2 * i) | m.peek(ec + 2 * i + 1) << 8 for i in range(1, 14) if i != 9)
    w(ec + 2 * 9, max(0, used - rest))                 # τα ρομπότ: το υπόλοιπο
    m.poke(sym["HU_PWR"] + 3, ord(sign))
    ex = layout("G_node_occ") + 240 + 6 - 0x4000
    R.b6[ex], R.b6[ex + 1] = coins & 255, coins >> 8


def edges(sym, data, idx, R=None, patch=None, quiet=False):
    """Τα τέσσερα σενάρια των ορίων και ένα χωρίς συλλέκτη. Γυρίζει τις
    αποτυχίες (για τα αρνητικά)."""
    S = Screen()
    if R is None:
        R = Run(sym)
        R.game()
    if patch:
        patch(R)
    R.tap("1", 8)                                       # παύση: τίποτα δεν ξαναγράφει τη μνήμη
    fails = []
    for what, pick, sign, used, pcap in EDGES:
        set_edge(R, pick, sign, used, pcap=pcap)
        f = R.open_v()
        bad, v, s = page_ok(S, R, data, idx) if f is not None else (["καμία"], {}, "")
        inks = "".join(colour(c, v, s) for c in "abcdefghiklmnotw") if v else ""
        ok = f is not None and not bad and R.back()
        if not ok:
            fails.append(what)
        if not quiet:
            check(ok, f"ΟΡΙΑ, {what}: η σελίδα ίδια με την αναφορά (χρώματα a-w {inks}, "
                      f"ρεύμα {v.get('o')}/{v.get('p')} {s}, αποθήκη {v.get('w')}/{v.get('x')}, "
                      f"νομίσματα {v.get('y')}, λάθος σειρές {bad})"
                  + ("" if not bad or bad == ["καμία"] else " — " + shown(S, R, bad)))
    return fails


def manage(sym, data, idx):
    from cpc import KEY_RIGHT, KEY_SPACE, KEY_ESC
    S = Screen()
    R = Run(sym)
    R.game()
    R.tap("m", 8)
    R.tap("v", 4)
    f = R.wait_res()
    bad = page_ok(S, R, data, idx)[0] if f is not None else ["καμία"]
    check(f is not None and not bad and R.back(),
          f"ΔΙΑΧΕΙΡΙΣΗ: M V, η σελίδα {f} frames μετά, ίδια, και πίσω στο LOOK ({bad})")
    R.tap("m", 8)
    for _ in range(6):
        R.tap(KEY_RIGHT, 8)
    sel = R.m.peek(sym["AC_SEL"])
    R.tap(KEY_SPACE, 4)
    f = R.wait_res()
    check(f is not None and sel == 6 and R.back(),
          f"ΔΙΑΧΕΙΡΙΣΗ: M, έξι δεξιά (το ac_sel {sel}, το ALL RESOURCES) και SPACE, η σελίδα "
          f"{f} frames μετά, και πίσω στο LOOK")
    # Το «?» πάνω στη σελίδα: η βοήθεια, και ένα πλήκτρο πίσω
    f = R.open_v()
    R.tap("/", 4)
    help_at = None
    for k in range(600):
        row = "".join(c for c, _ in TT.Screen().read(R.m, sym, 24))
        if TT.HELP_FOOT.replace("0", "O") in row.replace("0", "O"):
            help_at = k
            break
        R.m.run_frames(1)
    # η θέση 34 της βοήθειας: η τρίτη στήλη (HP_COLW 27), η δέκατη πρώτη σειρά
    name = "".join(c for c, _ in TT.Screen().read(R.m, sym, 20))[2 * 27 + 6:2 * 27 + 26].rstrip()
    line = "".join(c for c, _ in TT.Screen().read(R.m, sym, 21))[2 * 27 + 6:2 * 27 + 26].rstrip()
    check(f is not None and help_at is not None and name == "ALL RESOURCES"
          and line.replace("0", "O") == "HOW MUCH OF EACH",
          f"«?» πάνω στη σελίδα: η βοήθεια {help_at} frames μετά, με το κουμπί 34 "
          f"«{name}» / «{line}»")
    # Ενα πλήκτρο στο ίδιο frame με το υποσέλιδο θα ήταν, για τη βοήθεια, το
    # «?» που την άνοιξε (hp_up): περιμένει να αφεθεί, και μετά ένα άλλο.
    R.m.run_frames(25)
    R.tap(KEY_ESC, 4)
    check(R.game() is not None and R.m.peek(sym["UI_STATE"]) == UI_LOOK,
          "και ένα πλήκτρο πίσω στο παιχνίδι")


# --------------------------------------------------------------------------
# ΑΡΝΗΤΙΚΑ
# --------------------------------------------------------------------------
def find7(R, at, n, pat):
    """Το pat μέσα στα n bytes της τράπεζας 7 από το at (διεύθυνση παραθύρου)."""
    b = bytes(R.b7[at - 0x4000:at - 0x4000 + n])
    i = b.find(bytes(pat))
    assert i >= 0 and b.find(bytes(pat), i + 1) < 0, (hex(at), pat)
    return at - 0x4000 + i


def negatives(sym, data, idx):
    def b7(at, n, pat, new):
        def fn(R):
            i = find7(R, at, n, pat)
            for k, x in enumerate(new):
                R.b7[i + k] = x
        return fn
    wc = sym["EC_WCAP"]
    cases = [
        ("ο κανόνας του μετάλλου λευκός", b7(sym["RS_RULE"], 26, [5, 6, 4, 1, 1], [5, 6, 4, 0, 1])),
        ("το SPARES_MAX ένα παραπάνω", b7(sym["RS_LOHI"], 8, [4, 20], [4, 21])),
        ("το νερό με 2 x ζωντανούς", b7(sym["RSI_SP"], 24, [0xCB, 0x3F, 0x83], [0, 0, 0x83])),
        ("το πρόσημο του ρεύματος ανάποδα", b7(sym["RSI_NP"], 12, [0xFE, ord("-")], [0xFE, ord("+")])),
        ("η αποθήκη χωρίς το +1 της μισής", b7(sym["RSS_OK"], 12, [0xCB, 0x19, 0x03], [0xCB, 0x19, 0])),
        ("το άθροισμα της αποθήκης από το ec_wcap", b7(sym["RSV_USED"], 3, [0x21, 0, 0],
                                                        [0x2A, wc & 255, wc >> 8])),
        ("οι αριθμοί χωρίς κενά μπροστά", b7(sym["RS_FIELD"], 40, [0x3E, 0x20], [0x3E, 0])),
    ]
    for what, fn in cases:
        fails = edges(sym, data, idx, patch=fn, quiet=True)
        check(len(fails) > 0, f"ΑΡΝΗΤΙΚΟ: {what} -> σενάρια που αποτυγχάνουν {fails}")
    # το V έξω από τη μπάρα των ομάδων: το call bkm_id του OV_R1 (τράπεζα 1),
    # και η μπάρα ξαναγραμμένη (M, ESC)
    from cpc import KEY_ESC
    R = Run(sym)
    R.game()
    import cpc
    b1 = cpc._lib.cpcemu_ram_ptr(R.m._h, 1)
    a = sym["BKM_ID"]
    pat = bytes([0xCD, a & 255, a >> 8])
    base = sym["BK_MORE"] - 0x4000
    blob = bytes(b1[base:base + 64])
    i = blob.find(pat)
    for k in range(3):
        b1[base + i + k] = 0
    R.tap("m", 8)
    R.tap(KEY_ESC, 8)
    R.tap("v", 4)
    f = R.wait_res(limit=200)
    check(i >= 0 and f is None, f"ΑΡΝΗΤΙΚΟ: το V έξω από τη μπάρα των ομάδων -> η σελίδα {f}")
    # το κουμπί που ανοίγει το G: ο πίνακας του bt_key (τράπεζα 2), η θέση 8
    R = Run(sym)
    R.game()
    at = sym["BTK_AJP"] + 2 * 8
    R.m.poke(at, sym["MS_KEY"] & 255)
    R.m.poke(at + 1, sym["MS_KEY"] >> 8)
    R.tap("m", 8)
    R.tap("v", 4)
    f = R.wait_res(limit=300)
    check(f is None and R.pg() in (PG_GOALS, 0xFF),
          f"ΑΡΝΗΤΙΚΟ: το κουμπί των πόρων ανοίγει το G -> η σελίδα των πόρων {f}, "
          f"η σελίδα {R.pg()}")


def main():
    sym = TT.build()
    data, idx = text()
    first(sym, data, idx)
    edges(sym, data, idx)
    manage(sym, data, idx)
    negatives(sym, data, idx)
    print(f"\n{'ΟΛΑ ΚΑΛΑ' if not FAIL else f'{len(FAIL)} ΑΠΟΤΥΧΙΕΣ'}")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
