#!/usr/bin/env python3
"""Η γραμμή ειδοποιήσεων λέει ΠΟΙΑ μηχανή (βήμα 119, DESIGN §9.2).

Η πρόζα — οι αποφάσεις του παίκτη:

  NO ENGINEER  λέει και τι περιμένει: μια μηχανή που ήρθαν τα υλικά της και
               θέλει να στηθεί («NO ENGINEER METAL»), ή ένα κτίριο-εργοτάξιο
               («NO ENGINEER SOLAR», «NO ENGINEER DOME M»). Η πρώτη Build του
               πίνακα που έχει κάτι να ονομάσει· χωρίς τέτοια, μόνο του. Μια
               μηχανή που χρωστά ακόμη υλικά δεν «περιμένει μηχανικό».
  ΧΩΡΑΕΙ      19 στήλες: «NO ENGINEER » και επτά. Οι μηχανές χωράνε όλες
               (CABINET, PLASTIC)· το COLLECTOR και το EXTRACTOR γίνονται
               COLLECT και EXTRACT. Η σειρά 3 δεν αγγίζεται.
  BROKEN       και ποια μηχανή, όσο μια μηχανή έχει υγεία 0: η πιο πρόσφατη
               που χάλασε. Οχι φυτό — ένα μαραμένο φυτό δεν είναι «χαλασμένο»,
               ούτε σβήνει από τη γραμμή μια μηχανή που περιμένει ακόμη.
               Επισκευάστηκε αυτή και υπάρχει άλλη: λέγεται η άλλη.
  ΣΕΙΡΑ        αμέσως μετά το NO ENGINEER: κάτω από αυτό και ό,τι είναι πάνω
               του (LOW ON FOOD), πάνω από το SANDSTORM και το MERCHANT LANDED.

Πώς το ξέρει χωρίς σάρωμα σε κάθε τικ (src/alert6.asm): το al_brk κρατά μία
(θόλος, υποδοχή). Το γράφει το ec_break_d όταν χαλάει μια μηχανή, και το
jp_one της δημοσίευσης όταν βρίσκει μια χαλασμένη και δεν κρατιέται καμία. Το
HUD ρωτά μόνο αν η κρατημένη είναι ακόμη χαλασμένη, και την αφήνει όταν πάψει.

Στο colony.sna σε παύση, με το HUD να ζωγραφίζεται από probe και τα πιο
επείγοντα μηνύματα ήσυχα (ρεύμα, οξυγόνο, φαγητό, νερό, μετεωρίτες):

  ΟΝΟΜΑΤΑ      κάθε μηχανή 0-11 χαλασμένη: «BROKEN» και το όνομά της· τα
               τέσσερα φυτά, η άδεια υποδοχή, ο θόλος που δεν είναι σε
               λειτουργία: τίποτα, και το al_brk αφήνεται.
  ΠΕΡΙΜΕΝΕΙ    χωρίς μηχανικό, μία Build: κάθε μηχανή που στήνεται (υγεία
               4 + 32k) με το όνομά της· μία που χρωστά, χαλασμένη ή που
               δουλεύει: μόνο NO ENGINEER· φυτό μπροστά της: η μηχανή· οι
               θόλοι-εργοτάξια S, M, L· οι οκτώ δομές· δύο Build, η πρώτη
               χωρίς όνομα· η Build τελευταία σε γεμάτο πίνακα.
  ΣΕΙΡΑ        μια χαλασμένη μαζί με καθένα από τα γειτονικά μηνύματα.
  ΓΡΑΦΟΥΝ      το ec_break_d (μηχανή ναι, φυτό όχι, η πιο πρόσφατη κερδίζει)
               και το jb_post (μόνο αν δεν κρατιέται καμία, και με γεμάτο
               πίνακα).
  ΚΟΣΤΟΣ       το hud_draw με «ALL SYSTEMS OK», με κρατημένη χαλασμένη, με NO
               ENGINEER και τη Build τελευταία σε γεμάτο πίνακα· το jb_post
               που κρατά μια χαλασμένη.

Στο παιχνίδι που τρέχει, στην αποικία δοκιμών, χωρίς τυχαίες βλάβες:

  ΒΛΑΒΗ        ένα μεσαίο εργοστάσιο, METAL και PLASTIC στημένες. Χαλάει η
               PLASTIC, μετά η METAL: η γραμμή λέει τη METAL και την κρατά. Με
               ένα ανταλλακτικό ο μηχανικός επισκευάζει τη METAL, και η γραμμή
               λέει την PLASTIC· με δεύτερο, καμία.
  ΣΤΗΣΙΜΟ      ένα μεσαίο εργοστάσιο, ο μηχανικός γίνεται εργάτης, FIT μιας
               METAL: οι άποικοι κουβαλούν, και η γραμμή λέει «NO ENGINEER
               METAL». Ξανά μηχανικός: τη στήνει, και το μήνυμα φεύγει.

Αρνητικά, με τον κώδικα πειραγμένο στη μνήμη: το ec_break_d δεν γράφει· γράφει
και για φυτά· το jp_one δεν γράφει· το al_is δέχεται φυτά· το al_broken δεν
αφήνει· το HUD δεν ρωτά ποτέ· το al_wait ονομάζει και όσες χρωστούν· τα
κτίρια με εννιά γράμματα.
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import test_haul as TH                                   # noqa: E402
import test_info as TI                                   # noqa: E402
import test_outside as TO                                # noqa: E402
import test_reveal as R                                  # noqa: E402
import test_fit as TF                                    # noqa: E402
import test_mark as TM                                   # noqa: E402
import hudread                                           # noqa: E402
import econ as EC                                        # noqa: E402

FAIL = []
PROBE, FLAG = 0x3E00, 0x3EFF                             # όπως του tests/test_bots.py
J_BUILD, J_OPERATE, J_REPAIR, NO_JOB = 0, 1, 4, 255
DS_BUILDING, DS_ACTIVE = 1, 2
OWED, READY, HP = 7, 4, 200
FT_CLS, NO_MACH = 250, 255
ENGINEER, CBOT = 1, 5
D = 1                                                    # ο θόλος των σκηνών σε παύση
ST = 1                                                   # η δομή τους (κόμβος 65)
# Τα ονόματα όπως τα λέει η πρόζα, όχι όπως τα διαβάζει ο κώδικας
MACH = ["OXYGEN", "METAL", "PLASTIC", "WEAPONS", "CHIPS", "ROBOTS", "MEALS", "SPARES",
        "DRUGS", "MEAT", "BEDS", "CABINET"]
STRUCT = ["SOLAR", "TURBINE", "COLLECT", "EXTRACT", "MINE", "AIRLOCK", "LANDING", "SHIP"]
DOME = ["DOME S", "DOME M", "DOME L"]
OK_LINE = "ALL SYSTEMS OK"
# µs, ο χειρότερος από πέντε μετρήσεις, με το ίδιο probe. Το hud_draw
# ξαναγράφει εδώ όλο το HUD. Στο βήμα 118: «ALL SYSTEMS OK» 9.391, NO ENGINEER
# (χωρίς όνομα) 10.836, jb_post με μια χαλασμένη 1.835. Η συνηθισμένη γραμμή
# πληρώνει ένα byte της τράπεζας 0 (+7 µs) και κερδίζει 255 από το hud_blank, που
# από το βήμα 119 προσπερνά τα ήδη κενά κελιά σε σφιχτό βρόχο· το BROKEN πληρώνει
# τη σελιδοποίηση, το al_is και τα γράμματα· το NO ENGINEER το σάρωμα των 32
# εργασιών (~370 µs), μόνο όσο λέγεται· το jb_post το jp_rep (+21 µs), μόνο σε
# θόλο με χαλασμένη. Μετρημένα: 9.143, 9.363, 11.319, 1.856.
# ΜΕ 100 ΤΡΟΦΙΜΑ ΑΠΟ ΤΟ ΒΗΜΑ 122 (calm_bytes): η μπάρα της τροφής είναι κόκκινη
# κάτω από το ένα τρίτο, +27 µs. Τα ταβάνια είναι το βήμα 121 με αυτά: 9.170,
# 9.390, 11.346· το 122, με το STORAGE FULL στη σειρά, 9.163, 9.373, 11.329.
# ΚΑΙ ΤΑ ΝΟΜΙΣΜΑΤΑ (βήμα 134): $ και ένας αριθμός ακόμη στη σειρά 1, εκεί που
# ως τότε το hud_blank προσπερνούσε τέσσερα κενά. Γραμμένα κάθε φορά +372 µs και
# στις τρεις· μόνο όταν άλλαξαν (hud_cw) +12, το hd_b6 που τα διαβάζει από την
# τράπεζα 6 και η σύγκριση — 9.175, 9.385, 11.341.
COST = {"hud_draw, ALL SYSTEMS OK": 9_182,
        "hud_draw, BROKEN κρατημένη": 9_397,
        "hud_draw, NO ENGINEER, Build τελευταία σε γεμάτο πίνακα": 11_353,
        "jb_post, κρατά μια χαλασμένη": 1_870}


def check(ok, msg):
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ ") + msg)
    if not ok:
        FAIL.append(msg)


def same(s):
    return TI.same(s)


def econ_at():
    g = TO.layout()["G_econ_state"]
    const = open(os.path.join(ROOT, "src", "const.asm"), encoding="utf-8").read()
    out = {"EC_STOCK": g}
    for n, k in re.findall(r"^(EC_\w+)\s+equ G_econ_state \+ (\d+)", const, re.M):
        out[n] = g + int(k)
    return out


def calm_bytes(sym, E):
    """(διεύθυνση, τιμή): ό,τι κάθεται πάνω από το NO ENGINEER στη γραμμή,
    ήσυχο, και ο έμπορος και η θύελλα σβηστά."""
    out = [(E["EC_GAMEOVER"], 0), (E["EC_POK"], 1), (E["EC_O2OK"], 1),
           (E["EC_METEOR"], 0), (E["EC_STORM"], 0), (E["EC_SHSTATE"], 0),
           (sym["FO_N"], 0), (sym["SU_ALARM"], 0)]
    # Τροφή 100, όχι 500 (βήμα 122): ένα γεύμα ανά ζωντανό φτάνει για να μη
    # βγει LOW ON FOOD, και με 500 τα αγαθά της αποικίας περνούσαν τα 600 της
    # (το αμπάρι και ο θόλος Storage S) — η γραμμή έλεγε STORAGE FULL. Το νερό
    # δεν μετρά στην αποθήκη.
    for k, n in ((EC.S_FOOD, 100), (EC.S_WATER, 500)):
        a = E["EC_STOCK"] + 2 * k
        out += [(a, n & 255), (a + 1, n >> 8)]
    return out


class Game(TH.Game):
    """Το colony.sna σε παύση. Το probe παίρνει και την τράπεζα (το hud_draw
    θέλει την 1, το ec_break_d και το jb_post την 6)."""

    def __init__(self, sym, patch=(), patch6=()):
        super().__init__(sym, patch, patch6)
        self.sym, self.X, self.was = sym, econ_at(), {}
        self.dt = self.L["G_dome_tbl"] - 0x4000
        for j in range(32):
            self.put_job(j, [NO_JOB] * 5)
        self.m.poke(self.X["EC_NBUILD"], 0)
        self.set_dome(D, size=2)
        self.brk(None)

    def probe(self, body, timed=False, bank=0xC6):
        m = self.m
        code = ([0xF3, 0x31, 0x00, 0x01, 0x01, bank, 0x7F, 0xED, 0x49] + body
                + [0x3E, 0x5A, 0x32, FLAG & 255, FLAG >> 8, 0x18, 0xFE])
        m.write_ram(PROBE, bytes(code))
        m.poke(FLAG, 0)
        m.set_pc(PROBE)
        us, step = 0, (1 if timed else 100)
        while m.peek(FLAG) != 0x5A and us < 300000:
            m.run_us(step)
            us += step
        return us if m.peek(FLAG) == 0x5A else None

    def call(self, name, timed=False, bank=0xC6):
        a = self.sym[name]
        return self.probe([0xCD, a & 255, a >> 8], timed, bank)

    # --- ο θόλος D και η δομή ST ------------------------------------------
    def set_dome(self, d, size=2, state=DS_ACTIVE, mach=(), hp=()):
        b = self.dt + 24 * d
        self.b6[b + 2], self.b6[b + 3], self.b6[b + 4] = size, EC.R_FACTORY, state
        for k in range(8):
            self.b6[b + 8 + k] = mach[k] if k < len(mach) else NO_MACH
            self.b6[b + 16 + k] = hp[k] if k < len(hp) else 0

    def slot(self, s, code, hp, d=D):
        b = self.dt + 24 * d
        self.b6[b + 8 + s], self.b6[b + 16 + s] = code, hp

    def hp(self, s, d=D):
        return self.b6[self.dt + 24 * d + 16 + s]

    def kind(self, k):
        self.put_rec(ST, self.rec(ST)[:2] + [k] + self.rec(ST)[3:])

    # --- το al_brk -----------------------------------------------------------
    def brk(self, v):
        """v = (θόλος, υποδοχή) ή None."""
        d, s = v if v else (255, 0)
        self.m.poke(self.sym["AL_BRK"], s)
        self.m.poke(self.sym["AL_BRK"] + 1, d)

    def kept(self):
        d = self.m.peek(self.sym["AL_BRK"] + 1)
        return None if d == 255 else (d, self.m.peek(self.sym["AL_BRK"]))

    # --- ο μηχανικός ---------------------------------------------------------
    def engineers(self, on):
        for i in range(128):
            if self.ag_get(i, "flags") & 1:
                r = self.ag_get(i, "role")
                if on and i in self.was:
                    self.ag_set(i, role=self.was[i])
                elif not on and r & 7 in (ENGINEER, CBOT):
                    self.was[i] = r
                    self.ag_set(i, role=r & ~7)

    def builds(self, nodes, at=0):
        for j in range(32):
            self.put_job(j, [NO_JOB] * 5)
        for k, n in enumerate(nodes):
            self.put_job(at + k, [J_BUILD, n, 255, 5, n])
        self.m.poke(self.X["EC_NBUILD"], len(nodes))

    # --- η γραμμή --------------------------------------------------------------
    def beyond(self):
        """Ό,τι είναι ΠΕΡΑ από τη στήλη 39 της σειράς 2: το δεξί μισό της T1 στην
        οθόνη, και τα bytes μετά τα 120 κελιά της κρυφής μνήμης (G_hud_shadow).
        Ενα 20ό γράμμα πέφτει εκεί, και το hud_to μετά γράφει 254 κενά."""
        m = self.m
        lines = hudread.band_lines(hudread.screen(m), hudread.cam_p(m, self.sym))
        sh = self.L["G_hud_shadow"] + 120
        return b"".join(lines[y][40:] for y in range(8, 16)) + bytes(m.read_ram(sh, 136))

    def line(self, *extra, timed=False):
        for a, v in calm_bytes(self.sym, self.X) + list(extra):
            self.m.poke(a, v)
        was = self.beyond()
        us = self.call("HUD_DRAW", timed, 0xC0)
        spill = "" if self.beyond() == was else " |ΞΕΧΕΙΛΙΣΕ πέρα από τη στήλη 39"
        return us if timed else same(self.hud(2)[21:].rstrip()) + spill


# --------------------------------------------------------------------------
# ΟΝΟΜΑΤΑ — κάθε μηχανή χαλασμένη, και ό,τι δεν είναι
# --------------------------------------------------------------------------
def names(sym, patch=(), patch6=(), quiet=False):
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G = Game(sym, patch, patch6)
    for code, name in enumerate(MACH):
        G.slot(3, code, 0)
        G.brk((D, 3))
        got = G.line()
        if got != same("BROKEN " + name) or G.kept() != (D, 3):
            return f"ΟΝΟΜΑΤΑ: η μηχανή {code} χαλασμένη: «{got}», al_brk {G.kept()} — η πρόζα λέει «BROKEN {name}»"
    say(f"ΟΝΟΜΑΤΑ: οι δώδεκα μηχανές χαλασμένες, «BROKEN OXYGEN» ως «BROKEN CABINET»")
    G.slot(3, 1, HP)
    got = G.line()
    if got != same(OK_LINE) or G.kept() is not None:
        return f"ΟΝΟΜΑΤΑ: επισκευασμένη: «{got}», al_brk {G.kept()} — η πρόζα λέει τίποτα, και αφήνεται"
    for what, code, state in [(f"φυτό {c - FT_CLS}", c, DS_ACTIVE) for c in range(FT_CLS, FT_CLS + 4)] + \
                             [("άδεια υποδοχή", NO_MACH, DS_ACTIVE), ("θόλος-εργοτάξιο", 1, DS_BUILDING)]:
        G.set_dome(D, state=state)
        G.slot(3, code, 0)
        G.brk((D, 3))
        got = G.line()
        if got != same(OK_LINE) or G.kept() is not None:
            return f"ΟΝΟΜΑΤΑ: {what} με υγεία 0: «{got}», al_brk {G.kept()} — η πρόζα λέει τίποτα"
    say("ΟΝΟΜΑΤΑ: επισκευασμένη, τα τέσσερα φυτά μαραμένα, η άδεια υποδοχή, ο θόλος-εργοτάξιο: "
        "«ALL SYSTEMS OK», και το al_brk αφήνεται")
    return None


# --------------------------------------------------------------------------
# ΠΕΡΙΜΕΝΕΙ — NO ENGINEER και τι περιμένει
# --------------------------------------------------------------------------
def waits(sym, patch=(), patch6=(), quiet=False):
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G = Game(sym, patch, patch6)
    G.line()
    row3 = G.hud(3)
    G.engineers(False)
    G.builds([D])
    for code, name in enumerate(MACH):
        for hp in (READY, READY + 32 * (code % 4)):
            G.set_dome(D)
            G.slot(code % 8, code, hp)
            got = G.line()
            if got != same("NO ENGINEER " + name):
                return (f"ΠΕΡΙΜΕΝΕΙ: η μηχανή {code} με υγεία {hp} στην υποδοχή {code % 8}: «{got}» — "
                        f"η πρόζα λέει «NO ENGINEER {name}»")
    for hp in (OWED, 5, 6, 3, 0, HP):
        G.set_dome(D)
        G.slot(2, 1, hp)
        got = G.line()
        if got != same("NO ENGINEER"):
            return f"ΠΕΡΙΜΕΝΕΙ: η μηχανή με υγεία {hp}: «{got}» — η πρόζα λέει μόνο «NO ENGINEER»"
    G.set_dome(D, mach=[FT_CLS, FT_CLS + 2, 2], hp=[READY, READY, READY])
    if G.line() != same("NO ENGINEER PLASTIC"):
        return f"ΠΕΡΙΜΕΝΕΙ: δύο φυτά και μετά μια PLASTIC: «{G.line()}»"
    say("ΠΕΡΙΜΕΝΕΙ: οι δώδεκα μηχανές που στήνονται, με το όνομά τους· όσες χρωστούν, χαλασμένες "
        "ή δουλεύουν: «NO ENGINEER»· τα φυτά μπροστά παραλείπονται")
    for size, name in enumerate(DOME):
        G.set_dome(D, size=size, state=DS_BUILDING)
        if G.line() != same("NO ENGINEER " + name):
            return f"ΠΕΡΙΜΕΝΕΙ: θόλος-εργοτάξιο μεγέθους {size}: «{G.line()}» — «NO ENGINEER {name}»"
    G.set_dome(D)
    G.builds([64 + ST])
    keep = G.rec(ST)
    for k, name in enumerate(STRUCT):
        G.kind(k)
        got = G.line()
        if got != same("NO ENGINEER " + name) or G.hud(3) != row3:
            return (f"ΠΕΡΙΜΕΝΕΙ: δομή είδους {k}: «{got}», σειρά 3 «{G.hud(3)}» — η πρόζα λέει "
                    f"«NO ENGINEER {name}» και η σειρά 3 όπως ήταν")
    G.put_rec(ST, keep)
    G.kind(2)
    say("ΠΕΡΙΜΕΝΕΙ: «NO ENGINEER DOME S/M/L», και οι οκτώ δομές ως «NO ENGINEER COLLECT», "
        "«EXTRACT»· η σειρά 3 όπως ήταν")
    G.builds([D, 64 + ST])
    if G.line() != same("NO ENGINEER COLLECT"):
        return f"ΠΕΡΙΜΕΝΕΙ: Build σε θόλο χωρίς τίποτα να στηθεί, μετά σε δομή: «{G.line()}»"
    for j in range(32):
        G.put_job(j, [J_OPERATE, 2 + j % 8, 255, 3, 2 + j % 8])
    G.put_job(31, [J_BUILD, 64 + ST, 255, 5, 64 + ST])
    if G.line() != same("NO ENGINEER COLLECT"):
        return f"ΠΕΡΙΜΕΝΕΙ: η Build τελευταία σε γεμάτο πίνακα: «{G.line()}»"
    G.builds([])
    G.m.poke(G.X["EC_NBUILD"], 1)
    if G.line() != same("NO ENGINEER"):
        return f"ΠΕΡΙΜΕΝΕΙ: EC_NBUILD χωρίς Build στον πίνακα: «{G.line()}»"
    G.builds([64 + ST])
    G.engineers(True)
    if G.line() != same(OK_LINE):
        return f"ΠΕΡΙΜΕΝΕΙ: με μηχανικό: «{G.line()}»"
    say("ΠΕΡΙΜΕΝΕΙ: δύο Build, η πρώτη χωρίς όνομα: η δεύτερη· τελευταία σε γεμάτο πίνακα: "
        "βρίσκεται· χωρίς Build στον πίνακα: μόνο «NO ENGINEER»· με μηχανικό: τίποτα")
    return None


# --------------------------------------------------------------------------
# ΣΕΙΡΑ — μια χαλασμένη και τα γειτονικά μηνύματα
# --------------------------------------------------------------------------
def order(sym, patch=(), patch6=(), quiet=False):
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G = Game(sym, patch, patch6)
    X = G.X
    storm = [(X["EC_STORM"], 3)]
    mer = [(X["EC_SHSTATE"], 2), (X["EC_SHKIND"], 1)]          # SHIP_LANDED, SK_MERCHANT
    food = [(X["EC_STOCK"] + 2 * EC.S_FOOD, 0), (X["EC_STOCK"] + 2 * EC.S_FOOD + 1, 0)]
    G.slot(5, 1, 0)
    cases = [("μόνη της", [], "BROKEN METAL"),
             ("με αμμοθύελλα", storm, "BROKEN METAL"),
             ("με τον έμπορο", mer, "BROKEN METAL"),
             ("με λίγο φαγητό", food, "LOW ON FOOD")]
    for what, extra, want in cases:
        G.brk((D, 5))
        got = G.line(*extra)
        if got != same(want):
            return f"ΣΕΙΡΑ: χαλασμένη METAL {what}: «{got}» — η πρόζα λέει «{want}»"
    G.engineers(False)
    G.builds([64 + ST])
    G.kind(0)
    got = G.line()
    G.kind(2)
    G.engineers(True)
    G.builds([])
    if got != same("NO ENGINEER SOLAR"):
        return f"ΣΕΙΡΑ: χαλασμένη METAL και ηλιακό χωρίς μηχανικό: «{got}» — «NO ENGINEER SOLAR»"
    G.slot(5, 1, HP)
    for what, extra, want in (("με αμμοθύελλα", storm, "SANDSTORM"),
                              ("με τον έμπορο", mer, "MERCHANT LANDED"),
                              ("μόνη της", [], OK_LINE)):
        got = G.line(*extra)
        if got != same(want):
            return f"ΣΕΙΡΑ: επισκευασμένη, {what}: «{got}» — η πρόζα λέει «{want}»"
    say("ΣΕΙΡΑ: «BROKEN METAL» πάνω από το SANDSTORM και το MERCHANT LANDED, κάτω από το LOW ON "
        "FOOD και το NO ENGINEER· επισκευασμένη, εκείνα ξανά")
    return None


# --------------------------------------------------------------------------
# ΓΡΑΦΟΥΝ — το ec_break_d και το jb_post
# --------------------------------------------------------------------------
def writers(sym, patch=(), patch6=(), quiet=False):
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G = Game(sym, patch, patch6)
    m = G.m
    G.set_dome(D, mach=[FT_CLS, 1, 2, 3, 4, 5, 6, 7], hp=[HP] * 8)

    def brk(s):
        m.poke(sym["EB_D"], D)
        m.poke(sym["EB_S"], s)
        G.call("EC_BREAK_D")

    brk(4)
    if G.hp(4) != 0 or G.kept() != (D, 4) or G.line() != same("BROKEN CHIPS"):
        return f"ΓΡΑΦΟΥΝ: ec_break_d στην υποδοχή 4: υγεία {G.hp(4)}, al_brk {G.kept()}, «{G.line()}»"
    brk(6)
    if G.kept() != (D, 6) or G.line() != same("BROKEN MEALS"):
        return f"ΓΡΑΦΟΥΝ: ec_break_d και στην 6: al_brk {G.kept()}, «{G.line()}» — η πιο πρόσφατη"
    brk(0)
    if G.hp(0) != 0 or G.kept() != (D, 6) or G.line() != same("BROKEN MEALS"):
        return (f"ΓΡΑΦΟΥΝ: το φυτό της υποδοχής 0 μαράθηκε: υγεία {G.hp(0)}, al_brk {G.kept()}, "
                f"«{G.line()}» — η πρόζα λέει η MEALS μένει")
    say("ΓΡΑΦΟΥΝ: ec_break_d: «BROKEN CHIPS», μετά «BROKEN MEALS» (η πιο πρόσφατη)· ένα φυτό "
        "που μαραίνεται δεν τη σβήνει")
    # το jb_post: ο θόλος D με χαλασμένες τις 0 (φυτό), 4 και 6
    G.slot(6, 6, HP)
    G.brk(None)
    m.poke(G.X["EC_JDOME"], D)
    G.call("JB_POST")
    reps = [G.job(j) for j in range(32) if G.job(j)[0] == J_REPAIR]
    if G.kept() != (D, 0):
        return f"ΓΡΑΦΟΥΝ: jb_post χωρίς κρατημένη: al_brk {G.kept()}, Repair {reps} — η πρώτη χαλασμένη, (1, 0)"
    if G.line() != same(OK_LINE) or G.kept() is not None:
        return f"ΓΡΑΦΟΥΝ: το φυτό που κράτησε το jb_post: «{G.line()}», al_brk {G.kept()} — τίποτα, και αφήνεται"
    G.slot(0, FT_CLS, HP)
    for j in range(32):
        G.put_job(j, [NO_JOB] * 5)
    m.poke(G.X["EC_JDOME"], D)
    G.call("JB_POST")
    if G.kept() != (D, 4) or G.line() != same("BROKEN CHIPS"):
        return f"ΓΡΑΦΟΥΝ: jb_post, η CHIPS χαλασμένη: al_brk {G.kept()}, «{G.line()}»"
    G.set_dome(D + 1, size=2, mach=[3], hp=[0])
    m.poke(G.X["EC_JDOME"], D + 1)
    G.call("JB_POST")
    if G.kept() != (D, 4):
        return f"ΓΡΑΦΟΥΝ: jb_post με κρατημένη ήδη: al_brk {G.kept()} — η πρόζα λέει μένει (1, 4)"
    G.brk(None)
    for j in range(32):
        G.put_job(j, [J_OPERATE, 8 + j % 8, 255, 3, 8 + j % 8])
    m.poke(G.X["EC_JDOME"], D + 1)
    G.call("JB_POST")
    reps = [G.job(j) for j in range(32) if G.job(j)[0] == J_REPAIR]
    if G.kept() != (D + 1, 0) or reps or G.line() != same("BROKEN WEAPONS"):
        return (f"ΓΡΑΦΟΥΝ: jb_post με γεμάτο πίνακα: al_brk {G.kept()}, Repair {reps}, «{G.line()}» — "
                f"η πρόζα λέει (2, 0), «BROKEN WEAPONS», καμία Repair")
    say("ΓΡΑΦΟΥΝ: jb_post χωρίς κρατημένη: την πρώτη χαλασμένη (ένα φυτό: το HUD το αφήνει, και "
        "την επόμενη φορά την CHIPS)· με κρατημένη: τίποτα· με γεμάτο πίνακα: την κρατά, χωρίς Repair")
    return None


# --------------------------------------------------------------------------
# ΚΟΣΤΟΣ
# --------------------------------------------------------------------------
def cost(sym):
    G = Game(sym)
    base = G.probe([], True)

    def hud(n=5):
        G.line()
        return max(G.line(timed=True) - base for _ in range(n))
    out = {"hud_draw, ALL SYSTEMS OK": hud()}
    G.slot(5, 11, 0)
    G.brk((D, 5))
    out["hud_draw, BROKEN κρατημένη"] = hud()
    G.slot(5, 11, HP)
    G.engineers(False)
    for j in range(32):
        G.put_job(j, [J_OPERATE, 2 + j % 8, 255, 3, 2 + j % 8])
    G.put_job(31, [J_BUILD, 64 + ST, 255, 5, 64 + ST])
    G.m.poke(G.X["EC_NBUILD"], 1)
    out["hud_draw, NO ENGINEER, Build τελευταία σε γεμάτο πίνακα"] = hud()
    G.engineers(True)
    G.builds([])
    worst = 0
    for _ in range(5):
        G.brk(None)
        G.slot(5, 11, 0)
        G.m.poke(G.X["EC_JDOME"], D)
        worst = max(worst, G.call("JB_POST", True) - base)
        if G.kept() != (D, 5):
            worst = 10 ** 6
        for j in range(32):
            G.put_job(j, [NO_JOB] * 5)
    out["jb_post, κρατά μια χαλασμένη"] = worst
    return out


# --------------------------------------------------------------------------
# ΣΤΟ ΠΑΙΧΝΙΔΙ ΠΟΥ ΤΡΕΧΕΙ
# --------------------------------------------------------------------------
def gline(G, sym, X):
    """Η γραμμή με τα πιο επείγοντα ήσυχα: η αποικία δοκιμών λέει NO POWER
    και NO OXYGEN κατά διαστήματα. Ενα hud_draw από την κορυφή του βρόχου, και
    οι τιμές πίσω όπως ήταν."""
    m = G.m
    calm = calm_bytes(sym, X)
    keep = [(a, m.peek(a)) for a, _ in calm]
    for a, v in calm:
        m.poke(a, v)
    G.probe(["HUD_DRAW"])
    got = same(hudread.text(m, sym, 2)[21:].rstrip())
    for a, v in keep:
        m.poke(a, v)
    return got


def no_random(G, sym):
    """Χωρίς τυχαίες βλάβες (ec_break: ret), ώστε η γραμμή να λέει μόνο τις δικές μας."""
    G.m.poke(sym["EC_BREAK"], 0xC9)


def roomy(G, F, sym):
    """Μετά την πληρωμή: 100 μέταλλο και 100 βιοπλαστικό αντί για τα 500 + 500
    του TF.STOCK, ώστε τα αγαθά να χωρούν στα 600 της αποικίας (βήμα 122) και
    η τελευταία γραμμή να είναι «ALL SYSTEMS OK», όχι «STORAGE FULL». Το
    ec_full το ξαναμετρά ο επόμενος κύκλος ροής· εδώ μηδενίζεται για να μην
    τον περιμένει η γραμμή."""
    F.set_stocks(100, 100)
    G.m.poke(sym["EC_FULL"], 0)


def game_break(sym, g, patch=(), quiet=False, frames=60_000_000):
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    X = econ_at()
    G, F, node, at, ok = TM.dome_here(sym, g, TF.RM_FACTORY, patch)
    no_random(G, sym)
    if not ok:
        return f"ΒΛΑΒΗ: το εργοστάσιο {node} δεν τελείωσε"
    if not F.enter(at):
        return f"ΒΛΑΒΗ: ο εξοπλισμός δεν άνοιξε (κατάσταση {F.peek('UI_STATE')})"
    F.put(0, 1)
    F.put(1, 2)
    F.look()
    roomy(G, F, sym)
    G.run(frames, until=lambda: F.rec(node)[16:18] == [HP, HP])
    rec = F.rec(node)
    if rec[8:10] != [1, 2] or rec[16:18] != [HP, HP]:
        return f"ΒΛΑΒΗ: μηχανές {rec[8:12]}, υγείες {rec[16:20]} — θέλει METAL και PLASTIC στημένες"
    TM.spares(G, g, 0)
    TM.break_slot(G, sym, node, 1)
    G.run(400_000)
    got = gline(G, sym, X)
    if got != same("BROKEN PLASTIC"):
        return f"ΒΛΑΒΗ: χάλασε η PLASTIC: «{got}»"
    TM.break_slot(G, sym, node, 0)
    G.run(400_000)
    said = set()
    for _ in range(10):
        said.add(gline(G, sym, X))
        G.run(500_000)
    if said != {same("BROKEN METAL")}:
        return f"ΒΛΑΒΗ: χάλασε και η METAL, πέντε δευτερόλεπτα: {sorted(said)} — μόνο «BROKEN METAL»"
    say("ΒΛΑΒΗ: χάλασε η PLASTIC: «BROKEN PLASTIC»· μετά η METAL: «BROKEN METAL», και την κρατά "
        "πέντε δευτερόλεπτα")
    TM.spares(G, g, 1)
    G.run(frames, until=lambda: F.rec(node)[16] == HP)
    t0 = G.t
    if F.rec(node)[16:18] != [HP, 0]:
        return f"ΕΠΙΣΚΕΥΗ: με ένα ανταλλακτικό υγείες {F.rec(node)[16:20]} — η METAL πρώτα"
    seen = []
    G.run(20_000_000, until=lambda: seen.append(gline(G, sym, X)) or seen[-1] == same("BROKEN PLASTIC"),
          step=250_000)
    if not seen or seen[-1] != same("BROKEN PLASTIC"):
        return f"ΕΠΙΣΚΕΥΗ: η METAL επισκευάστηκε, η PLASTIC όχι: {sorted(set(seen))} — «BROKEN PLASTIC»"
    t1 = G.t
    TM.spares(G, g, 1)
    G.run(frames, until=lambda: F.rec(node)[17] == HP)
    G.run(400_000)
    got = gline(G, sym, X)
    if F.rec(node)[16:18] != [HP, HP] or got != same(OK_LINE):
        return f"ΕΠΙΣΚΕΥΗ: και η PLASTIC: υγείες {F.rec(node)[16:20]}, «{got}»"
    say(f"ΕΠΙΣΚΕΥΗ: ο μηχανικός επισκεύασε τη METAL, και {(t1 - t0) / 1e6:.1f} s αργότερα η γραμμή "
        f"έλεγε «BROKEN PLASTIC» (το jp_one)· με δεύτερο ανταλλακτικό, «ALL SYSTEMS OK»")
    return None


def game_wait(sym, g, patch=(), quiet=False, frames=60_000_000):
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    X = econ_at()
    G, F, node, at, ok = TM.dome_here(sym, g, TF.RM_FACTORY, patch)
    no_random(G, sym)
    if not ok:
        return f"ΣΤΗΣΙΜΟ: το εργοστάσιο {node} δεν τελείωσε"
    b6, ag = G.bank(6), TO.layout()["G_agent_fields"] - 0x4000
    was = {}
    for i in range(128):
        if b6[ag + i] & 1 and b6[ag + 128 + i] & 7 in (ENGINEER, CBOT):
            was[i] = b6[ag + 128 + i]
            b6[ag + 128 + i] &= ~7 & 255
    if not was:
        return "ΣΤΗΣΙΜΟ: η αποικία δεν έχει μηχανικό να γίνει εργάτης"
    if not F.enter(at):
        return f"ΣΤΗΣΙΜΟ: ο εξοπλισμός δεν άνοιξε (κατάσταση {F.peek('UI_STATE')})"
    F.put(0, 1)
    F.look()
    roomy(G, F, sym)
    ready = lambda: (lambda h: 0 < h < 128 and h & 3 == 0)(F.rec(node)[16])
    G.run(frames, until=ready)
    if not ready():
        return f"ΣΤΗΣΙΜΟ: τα υλικά δεν ήρθαν: υγεία {F.rec(node)[16]}"
    G.run(2_000_000)
    got = gline(G, sym, X)
    if got != same("NO ENGINEER METAL") or F.rec(node)[16] & 0x80:
        return f"ΣΤΗΣΙΜΟ: χωρίς μηχανικό, υγεία {F.rec(node)[16]}: «{got}» — «NO ENGINEER METAL»"
    for i, r in was.items():
        b6[ag + 128 + i] = r
    G.run(frames, until=lambda: F.rec(node)[16] == HP)
    G.run(400_000)
    got = gline(G, sym, X)
    if F.rec(node)[16] != HP or got != same(OK_LINE):
        return f"ΣΤΗΣΙΜΟ: με μηχανικό ξανά: υγεία {F.rec(node)[16]}, «{got}»"
    say("ΣΤΗΣΙΜΟ: χωρίς μηχανικό τα υλικά ήρθαν και η γραμμή λέει «NO ENGINEER METAL»· ξανά "
        "μηχανικός, τη στήνει, «ALL SYSTEMS OK»")
    return None


# --------------------------------------------------------------------------
# ΑΡΝΗΤΙΚΑ
# --------------------------------------------------------------------------
def negatives(sym, g):
    G = Game(sym)
    m = G.m
    w = lambda a: [a & 255, a >> 8]

    def find(name, n, pat, b6=False):
        at = sym[name]
        data = bytes(G.b6[at - 0x4000 + k] for k in range(n)) if b6 else m.read_ram(at, n)
        hits = [at + k for k in range(n - len(pat) + 1) if list(data[k:k + len(pat)]) == pat]
        return hits[0] if len(hits) == 1 else None

    out = []

    def add(label, at, edits, tests, b6=False):
        if at is None:
            out.append((label, None, tests, b6))
        else:
            out.append((label, [(at + k, v) for k, v in edits], tests, b6))

    brk = sym["AL_BRK"]
    a = find("EC_BREAK_D", 80, [0xED, 0x43] + w(brk))
    add("το ec_break_d δεν γράφει", a, [(0, 0), (1, 0), (2, 0), (3, 0)], [writers, game_break])
    a = find("EC_BREAK_D", 80, [0xFE, FT_CLS, 0xD2])
    add("το ec_break_d γράφει και για φυτά", a, [(2, 0), (3, 0), (4, 0)], [writers])
    a = find("JP_REP", 8, [0x7E, 0x3C, 0x20])
    add("το jp_one δεν γράφει", a, [(2, 0x18)], [writers, game_break])
    a = find("AL_IS", 48, [0xFE, FT_CLS, 0x30], b6=True)
    add("το al_is δέχεται φυτά", a, [(2, 0), (3, 0)], [names], b6=True)
    a = find("AL_BROKEN", 16, [0x3E, 0xFF, 0x32] + w(brk + 1), b6=True)
    add("το al_broken δεν αφήνει", a, [(2, 0), (3, 0), (4, 0)], [names, writers], b6=True)
    a = find("HD_BRK", 8, [0x3A] + w(brk + 1) + [0x3C, 0x28])
    add("το HUD δεν ρωτά ποτέ", a, [(4, 0x18)], [names, order])
    a = find("ALW_MACH", 32, [0xE6, 0x03], b6=True)
    add("το al_wait ονομάζει και όσες χρωστούν", a, [(1, 0)], [waits], b6=True)
    a = find("HD_NAMED", 32, [0x06, 0x07])
    add("τα κτίρια με εννιά γράμματα", a, [(1, 9)], [waits])
    return out


def run_negative(sym, g, label, edits, tests, b6):
    """Η πρώτη αποτυχία από τις σκηνές του, ή None. Οι σκηνές του παιχνιδιού
    που τρέχει (R.Game) δεν παίρνουν πείραγμα της τράπεζας 6."""
    for test in tests:
        if test in (game_break, game_wait):
            assert not b6
            why = test(sym, g, edits, quiet=True)
        else:
            why = test(sym, (), edits, quiet=True) if b6 else test(sym, edits, quiet=True)
        if why:
            return why
    return None


def main():
    sym, g = TG.build()
    for fn in (names, waits, order, writers):
        why = fn(sym)
        check(why is None, why or f"{fn.__name__.upper()}: όπως η πρόζα")
    got = cost(sym)
    for k, c in COST.items():
        check(got[k] <= c, f"ΚΟΣΤΟΣ {k}: {got[k]} µs (ταβάνι {c})")
    for fn in (game_break, game_wait):
        why = fn(sym, g)
        check(why is None, why or f"{fn.__name__.upper()}: όπως η πρόζα")
    for label, edits, tests, b6 in negatives(sym, g):
        if edits is None:
            check(False, f"ΑΡΝΗΤΙΚΟ «{label}»: δεν βρέθηκε πού να πειραχτεί")
            continue
        why = run_negative(sym, g, label, edits, tests, b6)
        check(why is not None, f"ΑΡΝΗΤΙΚΟ «{label}»: " +
              (f"αποτυγχάνει ({why[:100]})" if why else "περνά"))
    print(f"\n{'ΑΠΟΤΥΧΙΕΣ: ' + str(len(FAIL)) if FAIL else 'ΟΛΑ ΚΑΛΑ'}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
