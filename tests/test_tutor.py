#!/usr/bin/env python3
"""Το tutorial (βήμα 149, DESIGN §9.6).

Η πρόζα — οι αποφάσεις του χρήστη:

  ΜΕΝΟΥ        η έκτη γραμμή, TUTORIAL, φτιάχνει πάντα τον ίδιο κόσμο της
               σελήνης (TU_SEED του src/gen.asm), με το bit 7 του τέταρτου
               byte του worldinfo (tests/test_disc.py).
  ΓΡΑΜΜΗ       η γραμμή των πλήκτρων κάτω από τα κουμπιά λέει τι να χτιστεί,
               βήμα-βήμα, με τα γράμματα των κουμπιών· μετά το τελευταίο
               «THE COLONY IS YOURS» ώς το επόμενο γεγονός, και μετά ξανά
               «SPACE=MENU I=INFO FIRE=FIT C=SHIP», όπως σε κάθε παιχνίδι.
  ΒΗΜΑΤΑ       δεκατέσσερα (δεκατρία ήταν το σχέδιο· ο χρήστης διάλεξε δεύτερο
               ηλιακό): ηλιακός, θόλος οξυγόνου με OXYGEN, airlock, αντλία,
               κυλικείο με MEALS, δεύτερος ηλιακός, συλλέκτης, ορυχείο,
               εργοστάσιο με METAL, θερμοκήπιο με φυτά, εργαστήριο με MEAT,
               έλεγχος, πίστα, πλοίο. Ενα βήμα τελειώνει μόλις ΜΠΕΙ το κτίσμα
               του (το εργοτάξιο μετράει) ή η μηχανή που λέει· ό,τι χτίστηκε
               νωρίτερα από τη σειρά του περνά μόλις έρθει.
  ΚΙΝΔΥΝΟΙ     κανένας ως το τέλος: καμία βλάβη (ev_fmask) και καμία καταστροφή
               (θέλουν είκοσι αποίκους).
  ΜΕΤΑ         συνεχίζει ως κανονικό παιχνίδι, και σώζεται όπως κάθε άλλο.

Τι κοιτάζει:

  ΑΡΧΗ         στο main.sna η γραμμή είναι η παλιά και τα δύο SMC στη θέση
               τους· στον κόσμο του tutorial η γραμμή του πρώτου βήματος, στην
               οθόνη.
  ΠΑΙΧΝΙΔΙ     ο παίκτης-σενάριο του tools/play.py (plan_tutorial) παίζει τα
               δεκατέσσερα βήματα με τα πλήκτρα. Κάθε βήμα έρχεται με τη σειρά,
               η γραμμή του είναι στην οθόνη, ένας θόλος χωρίς τη μηχανή του δεν
               προχωρά το βήμα, κανένα γεγονός ως το τέλος, και στο τέλος όλα
               όπως σε κάθε παιχνίδι.
  ΣΕΙΡΑ        ο συλλέκτης πριν από τον θόλο: δεν προχωρά τίποτα, και το βήμα
               του περνά μόνο του όταν έρθει.
  ΔΙΣΚΟΣ       από τον δίσκο, TUTORIAL: η γραμμή του πρώτου βήματος. Ενας
               ηλιακός, σώσιμο, φόρτωμα ενός κανονικού παιχνιδιού (η παλιά
               γραμμή), φόρτωμα του tutorial (το βήμα του, ξανά).
  ΚΟΣΤΟΣ       το γεγονός χωρίς tutorial: ένα call και ένα ret· με tutorial, το
               κομμάτι από τις τρύπες και το μέτρημα, στη χειρότερη αποικία.

Αρνητικά: οι βλάβες ανοιχτές στα ίδια sol (μία χαλάει)· χωρίς το call της
τοποθέτησης, χωρίς το call του ui_redo, το tu_ev πάντα ret.
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import test_bar as TB                                    # noqa: E402
import hudread                                           # noqa: E402
import ovmap as OV                                       # noqa: E402

FAIL = []
TUT_SNA = os.path.join(ROOT, "build", "tutor.sna")
LOOK = "SPACE=MENU I=INFO FIRE=FIT C=SHIP"


def check(ok, msg):
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ ") + msg, flush=True)
    if not ok:
        FAIL.append(msg)


def gen_equ(name):
    src = open(os.path.join(ROOT, "src", "gen.asm"), encoding="utf-8").read()
    return int(re.search(rf"^{name}\s+equ\s+#([0-9A-Fa-f]+)", src, re.M).group(1), 16)


def texts():
    """Οι γραμμές του src/tutext.asm, χωρίς τα κενά του τέλους."""
    src = open(os.path.join(ROOT, "src", "tutext.asm"), encoding="utf-8").read()
    return [t.rstrip() for t in re.findall(r'^tut_\d\d:\s+db\s+"(.{32})"', src, re.M)]


def make_sna(sym):
    """build/tutor.sna: το main.sna με τον κόσμο του TU_SEED στην τράπεζα 4 και το
    worldinfo όπως το αφήνει η γεννήτρια για την έκτη γραμμή του μενού. Το main.sna
    έχει τον κόσμο του ACE1 0 στην τράπεζα 4, και τίποτε άλλο δεν εξαρτάται από
    αυτόν πριν τρέξει το παιχνίδι."""
    import worldgen_ref as Wg
    import play as P
    L = P.layout()
    d = bytearray(open(TG.SNA, "rb").read())
    b4 = 0x100 + 0x10000
    plane = open(os.path.join(ROOT, "build", "world_new.bin"), "rb").read()
    assert bytes(d[b4:b4 + 0x4000]) == plane, "η τράπεζα 4 του main.sna δεν είναι ο κόσμος του"
    seed = gen_equ("TU_SEED")
    d[b4:b4 + 0x4000] = bytes(Wg.generate(seed, 3).buf)
    wi = b4 + 2 * 0x4000 + L["G_worldinfo"] - 0x4000
    d[wi:wi + 4] = bytes([seed & 255, seed >> 8, 3, Wg.GEN_VERSION | 0x80])
    open(TUT_SNA, "wb").write(bytes(d))
    return seed


class Done(Exception):
    pass


class Tut:
    """Ενα παιχνίδι του tools/play.py, με τα bytes του tutorial."""

    def __init__(self, sym, g, sna):
        import play as P
        self.P = P
        self.G = P.Game(sym, g, sna)
        self.G.tut = True
        self.sym, self.m = sym, self.G.m
        L = self.G.L
        self.b6, self.b7, self.b1 = self.G.bank(6), self.G.bank(7), self.G.bank(1)
        self.tu = L["G_node_occ"] + 253 - 0x4000                 # EC_TU (βήμα 172· ως τότε 128 + 121)
        self.lev = L["G_node_occ"] + 240 - 0x4000                # EC_LDIS, EC_LEV (ως τότε 128 + 100)
        self.trace = []
        self.stop = None
        self.watch = False

    def step(self):
        return self.b6[self.tu]

    def line(self):
        o = self.sym["X_T_LOOK"] - 0xC000
        return bytes(self.b7[o:o + 34])

    def smc(self):
        return self.m.peek(self.sym["EV_FMASK"]), self.m.peek(self.sym["TU_EV"])

    def events(self):
        return list(self.b6[self.lev:self.lev + 6])

    def screen(self):
        """Η σειρά 3, αν το UI είναι στο LOOK."""
        if self.m.peek(self.sym["UI_STATE"]) != 0:
            return None
        return hudread.text(self.m, self.sym, 3)[:33].rstrip()

    def note(self, why):
        st = (self.step(), self.line(), self.smc())
        new = not self.trace or self.trace[-1][1] != st[0]
        if new or why != "run" or self.trace[-1][1:4] != st:
            scr = None
            if new and self.watch:
                scr = self.wait_screen(st[1][:33].decode("latin1").rstrip())
            self.trace.append((round(self.G.sol(), 2),) + st + (why, self.events(), scr))
        if self.stop and self.stop(self):
            raise Done()

    def wait_screen(self, want, frames=240):
        """Η σειρά 3 μόλις αλλάξει βήμα: αν το UI είναι στο LOOK, ως να γράψει τη
        γραμμή — το μήνυμα ενός πλοίου την κρατά δύο δευτερόλεπτα (ui_hold)."""
        if self.m.peek(self.sym["UI_STATE"]) != 0:
            return None
        got = None
        for _ in range(frames // 8):
            self.m.run_frames(8)
            got = self.screen()
            if got == want:
                break
        return got

    def hook(self):
        G = self.G
        run0, place0, fit0, ship0 = G.run, G.place, G.fit, G.call_ship

        def run(n):
            run0(n)
            self.note("run")

        def place(*a, **k):
            r = place0(*a, **k)
            self.note(("place", a[0], k.get("room", a[2] if len(a) > 2 else None)))
            return r

        def fit(*a, **k):
            r = fit0(*a, **k)
            self.note(("fit", tuple(a[1])))
            return r

        def ship():
            r = ship0()
            self.note(("ship",))
            return r
        G.run, G.place, G.fit, G.call_ship = run, place, fit, ship

    def play(self, plan, sols, stop=None):
        self.stop = stop
        try:
            self.P.play(self.G, plan, sols)
        except Done:
            pass

    def holes(self):
        """Η θέση στην τράπεζα 1 κάθε byte του κώδικα του tutorial
        (build/ovl4.bin): από το βήμα 155 συνεχής στο OV_R1, μετά τις γραμμές
        του (tests/ovmap.py· ως τότε στις τρύπες του DIST, 32 ανά γραμμή)."""
        at = OV.pieces(self.sym)["tutor"][1]
        return lambda k: at[k] - 0x4000

    def patch_code(self, old, new):
        """Πειράζει τον κώδικα του tutorial εκεί που ζει, στις τρύπες."""
        code = open(os.path.join(ROOT, "build", "ovl4.bin"), "rb").read()
        k = code.find(bytes(old))
        if k < 0:
            return False
        at = self.holes()
        for i, v in enumerate(new):
            self.b1[at(k + i)] = v
        return True


# --------------------------------------------------------------------------
# ΑΡΧΗ
# --------------------------------------------------------------------------
def start(sym, g, T):
    import play as P
    want = texts()
    old = Tut(sym, g, TG.SNA)
    tut = Tut(sym, g, TUT_SNA)
    out = []
    for name, t, line, fm, ev in (("main.sna", old, LOOK, 0xE6, 0xC9),
                                  ("κόσμος του tutorial", tut, want[0], 0xF6, 0x00)):
        t.G.look()
        t.m.run_frames(40)
        scr = t.screen()
        got = t.line()
        ok = (scr == line and got[:33].decode("latin1").rstrip() == line and got[33] == 0
              and t.smc() == (fm, ev) and t.step() == 0)
        out.append(ok)
        check(ok, f"ΑΡΧΗ {name}: η σειρά 3 λέει «{scr}», το x_t_look «{got[:33].decode('latin1')}» "
                  f"με {got[33]} στο τέλος, ev_fmask #{t.smc()[0]:02X} (θέλει #{fm:02X}), "
                  f"tu_ev #{t.smc()[1]:02X} (θέλει #{ev:02X}), EC_TU {t.step()}")
    return old, tut


# --------------------------------------------------------------------------
# ΠΑΙΧΝΙΔΙ
# --------------------------------------------------------------------------
def game(sym, g):
    import play as P
    want = texts()
    t = Tut(sym, g, TUT_SNA)
    t.watch = True
    t.hook()
    t.play(P.plan_tutorial(), 14, lambda t: t.step() == 16)
    steps = [r[1] for r in t.trace]
    order = [s for i, s in enumerate(steps) if i == 0 or s != steps[i - 1]]
    sol_end = next((r[0] for r in t.trace if r[1] == 16), None)
    check(order == [0] + list(range(2, 17)),
          f"ΠΑΙΧΝΙΔΙ: τα βήματα με τη σειρά {order} — το 1 είναι το 0 ως το πρώτο "
          f"γεγονός (το game_new μηδενίζει το EC_TU), τέλος στο sol {sol_end}")
    bad = []
    for s in range(2, 17):
        line = LOOK if s == 16 else want[s - 1]
        rec = next((r for r in t.trace if r[1] == s), None)
        got = rec[2][:33].decode("latin1").rstrip() if rec else None
        scr = next((r[6] for r in t.trace if r[1] == s and r[6] is not None), None)
        if scr is None:
            # σε άλλη κατάσταση του UI όταν άλλαξε: η οθόνη στο πρώτο LOOK του βήματος
            scr = "(δεν φάνηκε)"
        if got != line or scr != line:
            bad.append((s, got, scr, line))
    check(not bad, "ΠΑΙΧΝΙΔΙ: κάθε βήμα με τη γραμμή του, στο x_t_look και στην οθόνη "
                   "(σειρά 3, στο LOOK)" + (f" — λάθος {bad[:3]}" if bad else ""))
    # Η ΜΗΧΑΝΗ ΚΑΝΕΙ ΤΟ ΒΗΜΑ, ΟΧΙ Ο ΘΟΛΟΣ: μετά την τοποθέτηση κάθε θόλου με
    # μηχανή το βήμα μένει, και το πρώτο ίχνος του επόμενου είναι ένας εξοπλισμός.
    rooms = {0: 2, 1: 5, 4: 9, 3: 10, 5: 11}         # ROOM του tools/play.py -> βήμα
    held = []
    for room, k in rooms.items():
        pl = next((r for r in t.trace if isinstance(r[4], tuple) and r[4][0] == "place"
                   and r[4][2] == room), None)
        nxt = next((r for r in t.trace if r[1] == k + 1), None)
        held.append((k, pl[1] if pl else None, nxt[4][0] if nxt else None))
    ok = all(s == k and w == "fit" for k, s, w in held)
    check(ok, f"ΠΑΙΧΝΙΔΙ: οξυγόνο, κυλικείο, εργοστάσιο, θερμοκήπιο, εργαστήριο — μετά τον "
              f"θόλο το βήμα μένει, το επόμενο το φέρνει ο εξοπλισμός: {held}")
    pre = [r for r in t.trace if r[1] < 15]
    quiet = all(r[5] == [0] * 6 for r in pre)
    check(quiet and pre, f"ΠΑΙΧΝΙΔΙ: κανένα γεγονός ως το τελευταίο βήμα — EC_LDIS και "
                         f"EC_LEV {pre[-1][5] if pre else None} στο sol {pre[-1][0] if pre else None}, "
                         f"ev_fmask #{pre[-1][3][0]:02X}")
    end = t.trace[-1]
    check(end[1] == 16 and end[2][:33].decode("latin1") == LOOK and end[2][33] == 0
          and end[3] == (0xE6, 0xC9),
          f"ΠΑΙΧΝΙΔΙ: στο τέλος EC_TU {end[1]}, η γραμμή «{end[2][:33].decode('latin1')}», "
          f"ev_fmask #{end[3][0]:02X}, tu_ev #{end[3][1]:02X} — όπως σε κάθε παιχνίδι")
    last = None
    for r in t.trace:
        if r[1] != last:
            last = r[1]
            why = r[4] if isinstance(r[4], str) else r[4][0]
            print(f"  sol {r[0]:6.2f} βήμα {r[1]:2d} |{r[2][:33].decode('latin1')}| "
                  f"#{r[3][0]:02X} #{r[3][1]:02X} {why} οθόνη «{r[6]}»")
    return t, sol_end


def faults(sym, g, sol_end):
    """ΑΡΝΗΤΙΚΟ: το tutorial αφήνει το and (ld a,#E6 αντί για #F6)· στα ίδια sol
    χαλάει μηχανή — το EC_LEV γράφεται."""
    import play as P
    t = Tut(sym, g, TUT_SNA)
    ok = t.patch_code([0x3E, 0xF6], [0x3E, 0xE6])
    t.hook()
    t.play(P.plan_tutorial(), sol_end + 0.5, lambda t: t.events()[3:] != [0, 0, 0])
    lev = t.events()
    check(ok and lev[3:] != [0, 0, 0],
          f"ΑΡΝΗΤΙΚΟ: με τις βλάβες ανοιχτές στο tutorial μια μηχανή χαλάει ως το sol "
          f"{t.G.sol():.2f} (EC_LEV {lev[3:]}, βήμα {t.step()})")


def order(sym, g):
    """Ο συλλέκτης πριν από τον θόλο: το βήμα του περνά μόνο του."""
    import play as P
    t = Tut(sym, g, TUT_SNA)
    t.hook()
    plan = P.plan_tutorial()
    names = [s["name"] for s in plan]
    col = plan.pop(names.index("συλλέκτης"))
    col["after"] = ["ηλιακός"]
    plan.insert(1, col)
    plan[2]["after"] = ["συλλέκτης"]
    plan[names.index("ορυχείο")]["after"] = ["ηλιακός 2"]
    t.play(plan, 4, lambda t: t.step() >= 8)
    steps = [r[1] for r in t.trace]
    seq = [s for i, s in enumerate(steps) if i == 0 or s != steps[i - 1]]
    after_col = next((r[1] for r in t.trace
                      if isinstance(r[4], tuple) and r[4][0] == "place" and r[4][1] == P.COLLECTOR), None)
    check(seq == [0, 2, 3, 4, 5, 6, 8] and after_col == 2,
          f"ΣΕΙΡΑ: ο συλλέκτης δεύτερος — τα βήματα {seq}: το 2 μένει μετά τον "
          f"συλλέκτη, και ο δεύτερος ηλιακός φέρνει το 8, όχι το 7")


def negatives(sym, g):
    """Χωρίς τα σημεία που καλούν το tutorial, ο ηλιακός δεν προχωρά τίποτα."""
    import play as P
    out = []
    for label, at, new in (("χωρίς το call της τοποθέτησης (uip_fire)", "UIP_LATE", None),
                           ("με το tu_ev πάντα ret", "TU_EV", [0xC9])):
        t = Tut(sym, g, TUT_SNA)
        if at == "UIP_LATE":
            # το call tu_ev είναι αμέσως πριν από το pop af του uip_late
            a = sym["UIP_LATE"] - 4
            ok = [t.m.peek(a + i) for i in range(3)] == [0xCD, sym["TU_EV"] & 255, sym["TU_EV"] >> 8]
            for i in range(3):
                t.m.poke(a + i, 0)
        else:
            ok = t.m.peek(sym["TU_EV"]) == 0
            if at == "TU_EV":
                # και το tutorial δεν το ξαναγράφει: το ld (tu_ev),a του tuo_go -> nop nop nop
                ok = ok and t.patch_code([0x32, sym["TU_EV"] & 255, sym["TU_EV"] >> 8], [0, 0, 0])
                t.m.poke(sym["TU_EV"], 0xC9)
        t.hook()
        plan = P.plan_tutorial()[:2]
        t.play(plan, 1.0, lambda t: any(isinstance(r[4], tuple) and r[4][0] == "place"
                                        for r in t.trace))
        line = t.line()[:33].decode("latin1").rstrip()
        check(ok and t.step() == 0 and line == texts()[0],
              f"ΑΡΝΗΤΙΚΟ «{label}»: μετά τον ηλιακό EC_TU {t.step()}, η γραμμή «{line}»")
    # Το ui_redo: ο θόλος οξυγόνου μπαίνει (βήμα 2 -> μένει 2), και η μηχανή του
    # δεν το προχωρά χωρίς το call tu_ev του ui_redo.
    t = Tut(sym, g, TUT_SNA)
    a = sym["UI_REDO"] + 3
    ok = [t.m.peek(a + i) for i in range(3)] == [0xCD, sym["TU_EV"] & 255, sym["TU_EV"] >> 8]
    for i in range(3):
        t.m.poke(a + i, 0)
    t.hook()
    t.play(P.plan_tutorial()[:2], 1.2, lambda t: any(isinstance(r[4], tuple) and r[4][0] == "fit"
                                                    for r in t.trace))
    check(ok and t.step() == 2, f"ΑΡΝΗΤΙΚΟ «χωρίς το call του ui_redo»: με το OXYGEN στον θόλο "
                                f"EC_TU {t.step()} (θέλει 2)")


# --------------------------------------------------------------------------
# ΚΟΣΤΟΣ
# --------------------------------------------------------------------------
# µs: το call_us του tu_ev — di, ld sp (4) και το call, ret (8), και ένα µs φάσης: το
# probe αρχίζει όπου βρει τον κύριο βρόχο, και τα βήματα του 1 µs μετρούν από εκεί.
# Μετρημένο στο βήμα 153, σε ένα ret που δεν άλλαξε: 13 σε 21 από 24 φάσεις, 12 σε 3·
# ως τότε 12, γιατί η φάση εκεί έπεφτε έτσι.
COST_OFF = 13
COST_ON = 5000          # µs: το κομμάτι από τις τρύπες, δεκατρία μετρήματα, η γραμμή


def cost(sym, g, t_end, old):
    m = old.m
    m.poke(sym["UI_SPD"], 0)
    m.run_frames(4)
    off = TB.call_us(m, sym, sym["TU_EV"])
    check(m.peek(sym["TU_EV"]) == 0xC9 and off <= COST_OFF,
          f"ΚΟΣΤΟΣ: το γεγονός χωρίς tutorial {off} µs μαζί με τα 4 του probe (ταβάνι "
          f"{COST_OFF}): ένα call και ένα ret")
    # Με tutorial: η αποικία στο τέλος του. Το φάντασμα σβηστό (ui_hide), και το
    # tu_run από το βήμα 16 — μόνο το κομμάτι και η γραμμή — και από το 1:
    # δεκατρία μετρήματα που περνούν, το πλοίο που όχι.
    m = t_end.m
    m.poke(sym["UI_SPD"], 0)
    m.run_frames(4)
    TB.call_us(m, sym, sym["UI_HIDE"], reps=1)
    got = {}
    for s0 in (16, 1, 1):
        t_end.b6[t_end.tu] = s0
        us = TB.call_us(m, sym, sym["TU_RUN"], reps=1)
        got[s0] = max(got.get(s0, 0), us)
        got[(s0, "->")] = t_end.step()
    TB.call_us(m, sym, sym["UI_SHOW"], reps=1)
    check(got[1] <= COST_ON and got[(1, "->")] == 14 and got[(16, "->")] == 16,
          f"ΚΟΣΤΟΣ: ένα γεγονός με tutorial ως {got[1]} µs (ταβάνι {COST_ON}), από το βήμα 1 "
          f"ως το {got[(1, '->')]}: {got[16]} το φέρσιμο του κώδικα και της γραμμής, "
          f"{got[1] - got[16]} τα δεκατρία μετρήματα")


# --------------------------------------------------------------------------
# ΔΙΣΚΟΣ
# --------------------------------------------------------------------------
def disc(sym, g):
    import menuread as MR
    from cpc import CPC, KEY_RIGHT
    import balance as B
    bs = MR.syms(ROOT)
    dsk = os.path.join(ROOT, "build", "habitat.dsk")
    want = texts()
    m = CPC()
    L = __import__("play").layout()
    tu = L["G_node_occ"] + 253 - 0x4000                       # EC_TU
    wi = L["G_worldinfo"] - 0x4000

    def boot(planet, first):
        m.run_frames(300)
        if first:
            m.insert_disc(dsk)
        m.type_text('|disc\n', hold_frames=4, gap_frames=8)
        m.run_frames(60)
        m.type_text('run"habitat\n', hold_frames=4, gap_frames=8)
        MR.pick(m, bs, planet)
        for _ in range(120):
            m.run_frames(30)
            if m.peek(g + 2) == 100 and m.peek(g + 58) == 6:
                break
        else:
            return False
        m.run_frames(200)
        m.poke(sym["UI_SPD"], 4)
        return True

    def press(key, frames=24):
        m.key_down(key)
        m.run_frames(4)
        m.key_up(key)
        m.run_frames(frames)

    def fire(frames=12):
        m.set_joystick_type(1)
        m.run_frames(2)
        m.joystick(0x10)
        m.run_frames(4)
        m.joystick(0)
        m.set_joystick_type(0)
        m.run_frames(frames)

    def disc_op(key, slot):
        press(key)
        n = 0
        while m.peek(sym["SL_PICK"]) != slot and n < 6:
            press(KEY_RIGHT)
            n += 1
        m.poke(sym["FD_TRK"], 0)
        fire(4)
        msg = ""
        for _ in range(400):
            m.run_frames(1)
            r = hudread.text(m, sym, 3)
            if "SLOT" in r or "ERROR" in r:
                m.run_frames(1)
                msg = hudread.text(m, sym, 3).rstrip()
                break
        m.run_frames(60)
        return msg

    def state():
        b = TG_bank(m, 6)
        o = sym["X_T_LOOK"] - 0xC000
        line = bytes(TG_bank(m, 7)[o:o + 33]).decode("latin1").rstrip()
        return (b[tu], line, m.peek(sym["EV_FMASK"]), m.peek(sym["TU_EV"]))

    def screen(want=None):
        """Η σειρά 3 στο LOOK, ως να γράψει want: μετά από S ή L το μήνυμα την
        κρατά δύο δευτερόλεπτα (ui_hold)."""
        for _ in range(3):
            if m.peek(sym["UI_STATE"]) == 0:
                break
            m.set_joystick_type(1)
            m.joystick(0x20)
            m.run_frames(4)
            m.joystick(0)
            m.set_joystick_type(0)
            m.run_frames(10)
        got = None
        for _ in range(30):
            m.run_frames(8)
            got = hudread.text(m, sym, 3)[:33].rstrip()
            if want is None or got == want:
                break
        return got

    ok = boot(0, True)
    s0 = disc_op("S", 2) if ok else ""
    check(ok and "SAVED" in s0, f"ΔΙΣΚΟΣ: DESERT από τον δίσκο, σώσιμο στο slot 3: «{s0}»")
    m.reset()
    ok = boot(4, False)
    b = TG_bank(m, 6)
    seed = b[wi] | b[wi + 1] << 8
    st, scr = state(), screen(want[0])
    check(ok and seed == gen_equ("TU_SEED") and b[wi + 2] == 3 and b[wi + 3] & 0x80
          and st[1:] == (want[0], 0xF6, 0x00) and scr == want[0],
          f"ΔΙΣΚΟΣ: TUTORIAL — seed {seed:04X}, πλανήτης {b[wi + 2]}, #{b[wi + 3]:02X}, "
          f"η σειρά 3 «{scr}», ev_fmask #{st[2]:02X}, tu_ev #{st[3]:02X}")
    # ένας ηλιακός, με τα πλήκτρα, εκεί που τον βάζει ο παίκτης-σενάριο
    okb = B.build(m, sym, 4, g + 6, at=(9, -7), fit=False)
    m.run_frames(100)
    screen()                                # πίσω στο LOOK: το S δουλεύει μόνο εκεί
    st = state()
    check(okb and st[0] == 2 and st[1] == want[1],
          f"ΔΙΣΚΟΣ: ο ηλιακός — EC_TU {st[0]}, «{st[1]}»")
    s1 = disc_op("S", 0)
    l2 = disc_op("L", 2)
    st2, scr2 = state(), screen(LOOK)
    check("SAVED" in s1 and "LOADED" in l2 and st2 == (0, LOOK, 0xE6, 0xC9) and scr2 == LOOK,
          f"ΔΙΣΚΟΣ: σώσιμο στο slot 1 («{s1}»), φόρτωμα του DESERT («{l2}»): EC_TU {st2[0]}, "
          f"«{scr2}», ev_fmask #{st2[2]:02X}, tu_ev #{st2[3]:02X} — κανονικό παιχνίδι")
    l1 = disc_op("L", 0)
    st1, scr1 = state(), screen(want[1])
    check("LOADED" in l1 and st1 == (2, want[1], 0xF6, 0x00) and scr1 == want[1],
          f"ΔΙΣΚΟΣ: φόρτωμα του tutorial («{l1}»): EC_TU {st1[0]}, «{scr1}», "
          f"ev_fmask #{st1[2]:02X}, tu_ev #{st1[3]:02X}")
    # ΑΡΝΗΤΙΚΟ: χωρίς το call tu_run του sv_load, ένα κανονικό παιχνίδι που
    # φορτώνεται πάνω στο tutorial κρατά τη γραμμή του και τις βλάβες σβηστές.
    tr = sym["TU_RUN"]
    at = next((sym["SV_LOAD"] + i for i in range(24)
               if [m.peek(sym["SV_LOAD"] + i + k) for k in range(3)] == [0xCD, tr & 255, tr >> 8]), None)
    if at:
        for k in range(3):
            m.poke(at + k, 0)
    ln = disc_op("L", 2)
    stn = state()
    check(at and "LOADED" in ln and stn == (0, want[1], 0xF6, 0x00),
          f"ΑΡΝΗΤΙΚΟ «χωρίς το call tu_run του sv_load»: το DESERT («{ln}») με EC_TU {stn[0]}, "
          f"«{stn[1]}», ev_fmask #{stn[2]:02X}")


def TG_bank(m, n):
    import cpc
    return cpc._lib.cpcemu_ram_ptr(m._h, n)


def main():
    sym, g = TG.build()
    import subprocess
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "mkdsk.py")],
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit("mkdsk απέτυχε:\n" + r.stdout + r.stderr)
    seed = make_sna(sym)
    print(f"κόσμος του tutorial: seed #{seed:04X}, πλανήτης 3, {len(texts())} γραμμές")
    old, _ = start(sym, g, None)
    t_end, sol_end = game(sym, g)
    cost(sym, g, t_end, old)
    order(sym, g)
    faults(sym, g, sol_end or 8)
    negatives(sym, g)
    disc(sym, g)
    print(f"\n{'ΑΠΟΤΥΧΙΕΣ: ' + str(len(FAIL)) if FAIL else 'ΟΛΑ ΚΑΛΑ'}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
