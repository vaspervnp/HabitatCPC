#!/usr/bin/env python3
"""Τα ορόσημα που φαίνονται, και το τέλος (βήμα 177, DESIGN §10.2-10.3).

Ο παίκτης ρώτησε τι λείπει για να είναι πλήρες το παιχνίδι, και διάλεξε:
μια σελίδα όταν πιάνεται ένα ορόσημο, το G για τα πέντε και πόσο απέχει το
καθένα, και μετά το COLONY LOST μια σελίδα με τα sols, τους περισσότερους
αποίκους, τα ορόσημα, το κύρος και τα νομίσματα· από εκεί το L φορτώνει και
κάθε άλλο πλήκτρο ξαναρχίζει από το μενού. Τι ελέγχεται, από τη δισκέτα:

  ΚΕΙΜΕΝΟ   τα πεδία «^» μόνο στις σελίδες του G και του τέλους, και μόνο
            όσα ξέρει το tp_field. Αρνητικά: ένα «^» στο tutorial, ένα «^Z».
  G         στον πλανήτη 0 το G δείχνει τη σελίδα 21, ΔΙΑΒΑΣΜΕΝΗ ΑΠΟ ΤΗΝ ΟΘΟΝΗ
            γράμμα γράμμα και χρώμα χρώμα απέναντι στο αρχείο με τα νούμερα της
            μνήμης στα πεδία· ένα πλήκτρο πίσω στο παιχνίδι.
  ΟΡΟΣΗΜΑ   το Foothold και η Independence μαζί, στο τέλος ενός sol (το EC_MILE
            γραμμένο, το ρολόι λίγο πριν από το sol): ΟΣΟ Ο ΠΑΙΚΤΗΣ ΕΙΝΑΙ ΣΤΟ
            PLACE καμία σελίδα· με το ESC η 16, με ένα πλήκτρο η 18, με άλλο το
            παιχνίδι. Το EC_MSEEN 5, το ms_req #FF, και το G με DONE στα δύο.
  ΤΕΛΟΣ     όλοι νεκροί: η σελίδα 22 με το δικό της υποσέλιδο· L, η επιλογή
            φορτώματος· ESC, το LOOK με COLONY LOST· G, η 22 ξανά· ένα άλλο
            πλήκτρο, το μενού· ένας πλανήτης, μια καινούργια αποικία.

Αρνητικά: το bk_more χωρίς το G· το ms_raise χωρίς τίποτα (ret)· το tp_mnext
χωρίς τη δεύτερη σελίδα· τα νούμερα ένα word πιο πέρα· το L του τέλους όχι
ειδικό (το tp_key ρωτά άλλη σελίδα)· και η λέξη του φορτωτή μηδέν (ένα reset,
όχι το μενού).
"""
import os, re, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import tupages as TP                                     # noqa: E402
import menuread as MR                                    # noqa: E402
import test_tupage as TT                                 # noqa: E402

FAIL = []
PG_MS0, PG_GOALS, PG_END = 16, 21, 22                    # src/const.asm
UI_LOOK, UI_PLACE, UI_SLOT = 0, 2, 4
END_FOOT = "*L*  LOAD A SAVED COLONY     *ANY OTHER KEY*  A NEW COLONY"   # src/tpage.asm


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


EC = None                                               # G_econ_state
EC_X = None                                             # G_node_occ + 240
WI = None                                               # G_worldinfo


# --------------------------------------------------------------------------
# τα πεδία της μνήμης
# --------------------------------------------------------------------------
def values(R):
    """{πεδίο: τιμή} όπως πρέπει να τα γράψει το ms_go, από τη μνήμη, και τα
    bits των οροσήμων."""
    m, b6 = R.m, R.b6
    pk = m.peek
    prodm = pk(EC + 68) | pk(EC + 69) << 8
    bots = sum(b6[layout("G_agent_fields") - 0x4000 + 160 + i] & 1 for i in range(16))
    mile = pk(EC + 75)
    ind = (1 << 3) | (1 << 4) | (1 << 6)                # S_METAL, S_BIOPL, S_SPARE
    v = {"A": pk(EC + 58), "B": pk(EC + 78), "C": bin(prodm & ind).count("1"),
         "D": bin(prodm & 0x3FF).count("1"), "E": pk(EC + 79), "F": bots,
         "G": pk(EC + 77), "H": pk(EC + 51), "I": b6[EC_X + 8 - 0x4000],
         "J": b6[EC_X + 6 - 0x4000] | b6[EC_X + 7 - 0x4000] << 8,
         "K": b6[WI + 4 - 0x4000], "L": bin(mile).count("1")}
    return v, mile


def fill(line, v, mile):
    def one(mt):
        c = mt.group(1)
        if c in "01234":
            return "*DONE*" if mile >> int(c) & 1 else "-   "
        return str(v[c])
    return re.sub(r"\^(.)", one, line)


def want_page(data, idx, n, v=None, mile=0, foot=TT.FOOT):
    lines = TT.page_lines(data, idx, n)
    if v is not None:
        lines = [fill(x, v, mile) for x in lines]
    want = TT.expect_rows(lines, 1)
    want.update(TT.expect_rows([foot], 24))
    return want


class Run(TT.Run):
    def __init__(self, sym, planet, patches=()):
        super().__init__(sym, planet, patches)
        import cpc
        self.b6 = cpc._lib.cpcemu_ram_ptr(self.m._h, 6)
        self.b1 = cpc._lib.cpcemu_ram_ptr(self.m._h, 1)

    def wait_pg(self, want, foot=TT.FOOT, limit=900):
        """Ως να ανοίξει η σελίδα want με το υποσέλιδό της γραμμένο."""
        f = "".join(c for c, _ in TT.expect_rows([foot], 24)[24])
        S = TT.Screen()
        for k in range(limit):
            if self.pg() == want:
                row = "".join(c for c, _ in S.read(self.m, self.sym, 24))[2:2 + len(f)]
                if row.replace("0", "O") == f.replace("0", "O"):
                    self.m.run_frames(2)
                    return k
            self.m.run_frames(1)
        return None

    def quiet(self, n):
        """n frames χωρίς σελίδα; Γυρίζει ό,τι σελίδα είδε."""
        seen = set()
        for _ in range(n):
            self.m.run_frames(1)
            seen.add(self.pg())
        return seen - {0xFF}

    def sol_soon(self, mile):
        """Τα ορόσημα στο EC_MILE, και το ρολόι 40 frames πριν από το sol."""
        m = self.m
        m.poke(EC + 75, mile)
        sollen = m.peek(EC + 64) | m.peek(EC + 65) << 8
        f = sollen - 40
        m.poke(EC + 52, f & 255)
        m.poke(EC + 53, f >> 8)

    def kill(self):
        for i in range(160):
            self.b6[layout("G_agent_fields") - 0x4000 + i] &= 0xFE


# --------------------------------------------------------------------------
# ΚΕΙΜΕΝΟ
# --------------------------------------------------------------------------
def text():
    data = open(os.path.join(ROOT, "build", "tutor.txt"), "rb").read()
    pages = TP.parse()
    _, idx = TP.image(pages)
    have = [k for k, (_, _, body) in enumerate(pages) if any("^" in t for t, _ in body)]
    check(have == [PG_GOALS, PG_END] and len(pages) == PG_END + 1,
          f"ΚΕΙΜΕΝΟ: {len(pages)} σελίδες, πεδία «^» μόνο στις {have}")
    src = open(TP.SRC, encoding="utf-8").read()
    first = next(l for l in src.splitlines() if l and not l.startswith((";", "@")))
    goal = src.index("@MILESTONES")
    line = next(l for l in src[goal:].splitlines()[1:] if "^" in l)
    bad = [("ένα «^A» στο tutorial", src.replace(first, first[:60] + " ^A", 1)),
           ("ένα «^Z» στη σελίδα του G", src.replace(line, re.sub(r"\^.", "^Z", line, 1), 1)),
           ("72 στήλες και ένας αριθμός ως 5 ψηφία: 77",
            src.replace(line, "X" * 72 + "^J", 1))]
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
# G, ΟΡΟΣΗΜΑ, ΤΕΛΟΣ
# --------------------------------------------------------------------------
def goals(sym, data, idx):
    from cpc import KEY_SPACE
    S = TT.Screen()
    R = Run(sym, 0)
    R.game()
    R.tap("g", 4)
    f = R.wait_pg(PG_GOALS)
    v, mile = values(R)
    bad = TT.compare(S, R.m, sym, want_page(data, idx, PG_GOALS, v, mile)) if f is not None else ["καμία"]
    check(f is not None and not bad,
          f"G: η σελίδα {PG_GOALS} {f} frames μετά το πλήκτρο, ίδια με το αρχείο και τα "
          f"νούμερα της μνήμης (ζωντανοί {v['A']}, sol {v['H']}, οι περισσότεροι "
          f"{v['K']}, λάθος σειρές {bad})")
    R.tap(KEY_SPACE, 4)
    check(R.game() is not None and R.m.peek(sym["UI_STATE"]) == UI_LOOK
          and R.m.peek(sym["MS_REQ"]) == 0xFF,
          "και ένα πλήκτρο πίσω στο παιχνίδι, στο LOOK, χωρίς αίτημα")
    return f


def milestones(sym, data, idx):
    from cpc import KEY_SPACE, KEY_ESC
    S = TT.Screen()
    R = Run(sym, 0)
    R.game()
    R.tap("d", 20)                      # οι θόλοι: το MENU, μπάρα χωρίς το G
    R.tap("o", 40)                      # το οξυγόνο: PLACE
    st = R.m.peek(sym["UI_STATE"])
    R.sol_soon(0b00101)                 # Foothold και Independence
    seen = R.quiet(300)
    req = R.m.peek(sym["MS_REQ"])
    seen6 = R.b6[WI + 5 - 0x4000]
    check(st == UI_PLACE and not seen and req == 0b01010 and seen6 == 5,
          f"ΣΤΟ PLACE το sol έρχεται και καμία σελίδα ({sorted(seen)}): το αίτημα "
          f"περιμένει (ms_req {req:#04x}, τα bits 1 και 3), το EC_MSEEN {seen6}")
    R.tap(KEY_ESC, 4)
    R.tap(KEY_ESC, 4)
    f1 = R.wait_pg(PG_MS0)
    bad = TT.compare(S, R.m, sym, want_page(data, idx, PG_MS0)) if f1 is not None else ["καμία"]
    check(f1 is not None and not bad,
          f"ΜΕ ΤΟ ESC στο LOOK η σελίδα του Foothold ({f1} frames), ίδια με το αρχείο "
          f"(λάθος σειρές {bad})")
    R.tap(KEY_SPACE, 4)
    f2 = R.wait_pg(PG_MS0 + 2)
    bad = TT.compare(S, R.m, sym, want_page(data, idx, PG_MS0 + 2)) if f2 is not None else ["καμία"]
    check(f2 is not None and not bad,
          f"ΜΕ ΕΝΑ ΠΛΗΚΤΡΟ η σελίδα της Independence ({f2} frames), ίδια (λάθος σειρές {bad})")
    R.tap(KEY_SPACE, 4)
    fg = R.game()
    check(fg is not None and R.m.peek(sym["MS_REQ"]) == 0xFF and not R.quiet(200),
          "και με άλλο το παιχνίδι: κανένα αίτημα, καμία σελίδα ακόμη")
    R.tap("g", 4)
    f = R.wait_pg(PG_GOALS)
    v, mile = values(R)
    bad = TT.compare(S, R.m, sym, want_page(data, idx, PG_GOALS, v, mile)) if f is not None else ["καμία"]
    check(f is not None and mile == 5 and not bad,
          f"G: DONE στο Foothold και στην Independence, παύλα στα άλλα (λάθος σειρές {bad})")
    R.tap(KEY_SPACE, 4)
    R.game()
    return f1


def end(sym, data, idx):
    from cpc import KEY_ESC
    S = TT.Screen()
    R = Run(sym, 0)
    R.game()
    R.m.run_frames(600)
    R.kill()
    f = R.wait_pg(PG_END, END_FOOT, limit=3000)
    v, mile = values(R)
    bad = TT.compare(S, R.m, sym, want_page(data, idx, PG_END, v, mile, END_FOOT)) if f is not None else ["καμία"]
    over = R.m.peek(EC + 59)
    check(f is not None and not bad and over == 1 and v["A"] == 0 and v["K"] == 6,
          f"ΤΕΛΟΣ: όλοι νεκροί, η σελίδα {PG_END} {f} frames μετά, με το δικό της "
          f"υποσέλιδο και τα νούμερα (sol {v['H']}, οι περισσότεροι {v['K']}, "
          f"λάθος σειρές {bad})")
    R.tap("l", 20)
    st = R.m.peek(sym["UI_STATE"])
    check(R.pg() == 0xFF and st == UI_SLOT, f"L: η επιλογή φορτώματος (ui_state {st})")
    R.tap(KEY_ESC, 20)
    st = R.m.peek(sym["UI_STATE"])
    check(st == UI_LOOK and not R.quiet(300),
          f"ESC: το LOOK, και καμία σελίδα ξανά (ui_state {st}): το τέλος ζητά μία φορά")
    R.tap("g", 4)
    fg = R.wait_pg(PG_END, END_FOOT)
    check(fg is not None, f"G στη νεκρή αποικία: η σελίδα του τέλους ξανά ({fg} frames)")
    R.tap("x", 4)
    fm = MR.wait(R.m, R.bs, limit=1500)
    check(fm is not None, f"ΑΛΛΟ ΠΛΗΚΤΡΟ: το μενού, {fm} frames μετά (το firmware από τη "
          f"ROM, ο φορτωτής από τη δισκέτα)")
    if fm is None:
        return f, fm
    MR.pick(R.m, R.bs, 2)
    R.m.run_frames(1500)
    pk = R.m.peek
    fresh = (pk(EC + 59), pk(EC + 58), R.b6[WI + 5 - 0x4000], R.b6[WI + 4 - 0x4000],
             pk(sym["MS_REQ"]), pk(EC + 75))
    check(fresh == (0, 6, 0, 6, 0xFF, 0),
          f"ΜΙΑ ΚΑΙΝΟΥΡΓΙΑ ΑΠΟΙΚΙΑ στον πλανήτη 2: gameover, ζωντανοί, EC_MSEEN, "
          f"οι περισσότεροι, ms_req, EC_MILE = {fresh}")
    return f, fm


# --------------------------------------------------------------------------
# ΑΡΝΗΤΙΚΑ
# --------------------------------------------------------------------------
def negatives(sym, data, idx):
    from cpc import KEY_SPACE, KEY_ESC
    S = TT.Screen()

    # 1. το bk_more χωρίς το G: jr nz,bkm_end -> jr (OV_R1, μετά το game)
    R = Run(sym, 0)
    R.game()
    o = sym["BK_MORE"] - 0x4000 + 5
    ok = R.b1[o] == 0x20
    R.b1[o] = 0x18
    R.tap("d", 20)
    R.tap(KEY_ESC, 20)                  # η μπάρα ξαναγράφεται με το bk_more
    R.tap("g", 4)
    check(ok and not R.quiet(300), "ΑΡΝΗΤΙΚΟ: το bk_more χωρίς το G -> καμία σελίδα")

    # 2. το ms_raise ret: το sol έρχεται, κανένα αίτημα
    R = Run(sym, 0)
    R.game()
    o = sym["MS_RAISE"] - 0x4000
    R.b6[o] = 0xC9
    R.sol_soon(1)
    check(not R.quiet(300) and R.m.peek(sym["MS_REQ"]) == 0xFF,
          "ΑΡΝΗΤΙΚΟ: το ms_raise ret -> το Foothold χωρίς σελίδα")

    # 3. το tp_mnext χωρίς τίποτα (or a; ret z -> xor a; ret): μόνο η πρώτη
    R = Run(sym, 0)
    R.game()
    o = sym["TP_MNEXT"] - 0x4000
    R.b7[o], R.b7[o + 1] = 0xAF, 0xC9
    R.sol_soon(0b00101)
    f1 = R.wait_pg(PG_MS0)
    R.tap(KEY_SPACE, 4)
    seen = R.quiet(200)
    check(f1 is not None and not seen,
          f"ΑΡΝΗΤΙΚΟ: το tp_mnext χωρίς τίποτα -> μόνο η σελίδα του Foothold ({sorted(seen)})")

    # 4. τα νούμερα ένα word πιο πέρα (ld de,ms_val -> ms_val + 2)
    def shift(R):
        at = TT.find7(R, sym["MS_GO"], 16, [0x11, sym["MS_VAL"] & 255, sym["MS_VAL"] >> 8])
        if at:
            R.b7[at[0] - 0x4000 + 1] += 2
        R.shifted = bool(at)
    R = Run(sym, 0, [shift])
    R.game()
    R.tap("g", 4)
    f = R.wait_pg(PG_GOALS)
    v, mile = values(R)
    bad = TT.compare(S, R.m, sym, want_page(data, idx, PG_GOALS, v, mile)) if f is not None else []
    check(R.shifted and f is not None and bad,
          f"ΑΡΝΗΤΙΚΟ: τα νούμερα ένα word πιο πέρα -> η σελίδα του G διαφέρει (σειρές {bad})")

    # 5. το L του τέλους όχι ειδικό: το tp_key ρωτά για άλλη σελίδα
    def nol(R):
        at = TT.find7(R, sym["TP_KEY"], 24, [0xFE, PG_END])
        if at:
            R.b7[at[0] - 0x4000 + 1] = PG_END + 1
        R.nol = bool(at)
    R = Run(sym, 0, [nol])
    R.game()
    R.kill()
    R.wait_pg(PG_END, END_FOOT, limit=3000)
    R.tap("l", 4)
    fm = MR.wait(R.m, R.bs, limit=1500)
    check(R.nol and fm is not None,
          "ΑΡΝΗΤΙΚΟ: το L όχι ειδικό στο τέλος -> το L ξαναρχίζει (το μενού), δεν φορτώνει")

    # 6. η λέξη του φορτωτή μηδέν: ένα reset, όχι το μενού
    R = Run(sym, 0)
    R.game()
    o = layout("G_text") - 0x4000
    word = R.b7[o] | R.b7[o + 1] << 8
    R.b7[o] = R.b7[o + 1] = 0
    R.kill()
    R.wait_pg(PG_END, END_FOOT, limit=3000)
    R.tap("x", 4)
    fm = MR.wait(R.m, R.bs, limit=900)
    check(word == 0x861C and fm is None,
          f"ΑΡΝΗΤΙΚΟ: η λέξη του jumpblock (#{word:04X}, του φορτωτή) μηδέν -> ένα reset "
          f"στο BASIC, όχι το μενού")


def main():
    global EC, EC_X, WI
    sym = TT.build()
    EC = layout("G_econ_state")
    EC_X = layout("G_node_occ") + 240
    WI = layout("G_worldinfo")
    data, idx = text()
    fg = goals(sym, data, idx)
    fm1 = milestones(sym, data, idx)
    fe, fmenu = end(sym, data, idx)
    negatives(sym, data, idx)
    print(f"\nκόστος: η σελίδα του G {fg} frames μετά το πλήκτρο, του Foothold {fm1} μετά "
          f"το ESC, του τέλους {fe} μετά τον θάνατο, το μενού {fmenu} μετά το πλήκτρο")
    print("ΟΛΑ ΚΑΛΑ" if not FAIL else f"{len(FAIL)} ΑΠΟΤΥΧΙΕΣ")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
