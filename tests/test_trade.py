#!/usr/bin/env python3
"""Ο έμπορος (βήμα 93, DESIGN §6.11), στο colony.sna.

Η πρόζα — οι αποφάσεις του παίκτη, και ό,τι είναι του Planetbase:

  ΑΦΙΞΗ      έρχεται μόνος του, όταν τα έντεκα κάτω bits της δεύτερης ζαριάς
             της θέσης 15 είναι #5A5, με πίστα και χωρίς άλλο πλοίο — ένας ανά
             ~2,7 sol, όσο συχνά και οι επισκέπτες. Ερχεται σε 24 περιστροφές,
             όπως κάθε πλοίο, και μένει ΜΙΣΟ SOL (μήκος sol / 32 περιστροφές).
  ΦΟΡΤΙΟ     τρία ή τέσσερα αγαθά, διαφορετικά μεταξύ τους, άλλα κάθε φορά, 1-4
             μονάδες από το καθένα, και το κέρδος του, 35-65%. Τρία bytes από
             οκτώ βήματα του Galois το καθένα, με σπόρο το EC_RND της στιγμής:
             το 1ο δίνει το κέρδος (5 bits, mod 31) και τα τέσσερα (bit 5), το 2ο
             το πρώτο αγαθό (4 κάτω, mod 13) και το βήμα (4 πάνω, mod 12, + 1),
             το 3ο τις μονάδες (2 bits ανά αγαθό). Ίδιο με το tools/econ.py.
  ΤΙΜΕΣ      του Planetbase: τρόφιμα 5, μετάλλευμα 10, μέταλλο 15, βιοπλαστικό
             10, επεξεργαστές 40, ανταλλακτικά 15, φάρμακα 25, όπλα 80, άμυλο,
             λαχανικά, κρέας 5, βότανα 10· ρομπότ 120. Το νερό δεν πουλιέται.
             Τα δικά του: αξία + (αξία x κέρδος + 50) / 100, ανά μονάδα.
  ΓΡΑΜΜΗ     το κουμπί του εμπόρου στη ΜΕΤΑΦΟΡΑ (M) την ανοίγει, όσο είναι εδώ:
               σειρά 3   +47% TAKE  110 GIVE  100
               σειρά 4    <METAL  > SHIP 20 TAKE  5 HAVE 595 @ 15
             η 3 το ζύγι (όσα παίρνεις στις τιμές του, όσα δίνεις στην αξία
             τους, και FIRE=DEAL όταν παίρνεις κάτι και δίνεις τουλάχιστον όσο
             παίρνεις), η 4 ένα αγαθό: όσα φέρνει, όσα παίρνεις ή δίνεις, όσα
             έχεις, η αξία του. Η ταχύτητα στις στήλες 35-39 όπως πάντα.
  ΒΕΛΗ       αριστερά/δεξιά: τα δεκατρία, πρώτα τα δικά του με τη σειρά του
             φορτίου, μετά τα άλλα με τη σειρά των αποθεμάτων, κυκλικά. ΠΑΝΩ:
             μία μονάδα λιγότερη προς αυτόν, ή μία ακόμη από αυτόν ως όσα φέρνει
             και ως το ταβάνι της αποθήκης (600). ΚΑΤΩ: μία λιγότερη από αυτόν,
             ή μία ακόμη προς αυτόν ως όσα έχεις και ως 99. Μονάδα: 10 τρόφιμα,
             μεταλλεύματα, βιοπλαστικά, άμυλο, λαχανικά, βότανα, κρέας· 5 μέταλλα
             και ανταλλακτικά· 4 φάρμακα· 2 επεξεργαστές· 1 όπλο, 1 ρομπότ.
  FIRE, SPACE  αν δεν φτάνει, τίποτα. Αν κάτι από όσα δίνεις λιγόστεψε στο
             μεταξύ, NOT ENOUGH MATERIAL και τίποτα· και χωρίς καμία θέση στον
             πίνακα εργασιών, ή χωρίς πίστα (ένας μετεωρίτης την έριξε), τίποτα.
             (Από το βήμα 115 μια αδιάθετη Operate δίνει τη θέση της, οπότε ο
             γεμάτος πίνακας εδώ είναι 32 Drill: tests/test_repost.py.) Αλλιώς η ανταλλαγή, ΟΠΩΣ ΤΑ
             ΕΡΓΟΤΑΞΙΑ (βήμα 98): όσα δίνεις φεύγουν ακριβώς, και χρωστιούνται
             στον έμπορο σε φορτία ως δέκα (EC_MARKUP)· όσα παίρνεις μένουν στο
             πλοίο του (οι ποσότητες του φορτίου του) ώσπου να κουβαληθούν (tests/
             test_carry.py)· δύο J_TRADE στην πίστα· το σερί της ανεξαρτησίας
             σπάει· ο έμπορος περιμένει, και η γραμμή του δεν ξανανοίγει
             (SK_DEALT)· TRADE DONE, πίσω στο LOOK. Ως το 97 όλα στιγμιαία, και
             ο έμπορος έφευγε.
  ESC        κλείνει, και η προσφορά ξεχνιέται.
  ΝΟΜΙΣΜΑΤΑ  (βήμα 135, όπως στο Planetbase) αμέσως μετά τα δικά του: τα δέχεται,
             αξία 1 το καθένα, και πουλά όσα φέρνει — 0, 50, 100 ή 150 από τα
             bits 6-7 του πρώτου byte του φορτίου — με το κέρδος του: η δεκάδα
             10 + (10 x κέρδος + 50) / 100. Δέκα ανά πάτημα: ΠΑΝΩ ως όσα φέρνει
             και ως το 999, ΚΑΤΩ ως όσα έχεις και ως 990. Η σειρά 4:
               <COINS  > SHIP 150 GIVE 120 HAVE 123
             χωρίς το «@ αξία». Στη συμφωνία αλλάζουν χέρια ΑΜΕΣΩΣ, χωρίς
             φορτία. Δεν ξαναμετριούνται: το ΚΑΤΩ τα κράτησε ως όσα είχες όταν
             άνοιξε η γραμμή, και όσο είναι εδώ ο έμπορος άλλο πλοίο δεν
             έρχεται να πληρώσει.
  ΦΕΥΓΕΙ     όταν τελειώσει το μισό sol η γραμμή κλείνει μόνη της.
  ΚΟΥΜΠΙ     κόκκινο όσο δεν είναι εδώ, και τότε δεν ανοίγει τίποτα· λευκό στη
             γραμμή, με τη ΜΕΤΑΦΟΡΑ στη μπάρα. Η γραμμή του πλοίου (91) δείχνει
             κι αυτή τη ΜΕΤΑΦΟΡΑ — ως το 93 έδειχνε τη ΔΙΑΧΕΙΡΙΣΗ.
  ΜΗΝΥΜΑ     MERCHANT LANDED στη σειρά 2, όταν δεν υπάρχει κάτι χειρότερο.
  ΑΝΕΞΑΡΤΗΣΙΑ  το sol με ανταλλαγή μηδενίζει το σερί χωρίς εμπόριο.
  ΚΟΣΤΟΣ     θέση 15 χωρίς πλοίο όχι πιο αργή από το βήμα 92 (304 us) και την
             πόρτα των εισβολέων του 111 (+8 us: το fo_n, src/foe.asm)· το HUD
             ζεστό όχι πιο αργό (12.046)· η προσγείωση του εμπόρου, μία φορά ανά
             ~2,7 sol, ως 1.300· ένα frame της γραμμής χωρίς πλήκτρο και μία
             επανασχεδίασή της κάτω από τα ταβάνια COST.

Αρνητικά, με τον κώδικα πειραγμένο στη μνήμη. Φορτίο: πάντα τρία, κέρδος
χωρίς mod 31, βήμα χωρίς + 1, μένει οκτώ περιστροφές όπως τα άλλα. Γραμμή:
χωρίς το ταβάνι της αποθήκης, χωρίς το 99, χωρίς το «όσα έχεις», τιμή χωρίς
στρογγύλεμα, τα δικά του όχι πρώτα. Ανταλλαγή: χωρίς το ζύγι, χωρίς τον
έλεγχο του αποθέματος, χωρίς το σερί, η γραμμή του ξανανοίγει, χωρίς
μεταφορείς, συμφωνία με τον πίνακα γεμάτο, συμφωνία χωρίς πίστα, ένα φορτίο
ανά αγαθό, το πλοίο του κρατά όλο το φορτίο. Η γραμμή που δεν κλείνει όταν
φύγει, το κουμπί που δεν κοκκινίζει, το κουμπί που ανοίγει χωρίς έμπορο, η
γραμμή του πλοίου στη ΔΙΑΧΕΙΡΙΣΗ όπως ως το 92, το μήνυμα που λείπει. Από
το βήμα 135: τα νομίσματα ως το 600 της αποθήκης χωρίς δεκάδες, τα νομίσματα έξω
από το ζύγι, νομίσματα που δεν αλλάζουν χέρια, και η θέση 0 του φορτίου που τα
κρατά για να κουβαληθούν.
"""
import os, random, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import test_act as TA                                    # noqa: E402
import test_info as TI                                   # noqa: E402
import test_outside as TO                                # noqa: E402
import barread as B                                      # noqa: E402
import hudread                                           # noqa: E402
import econ as EC                                        # noqa: E402
import cpc                                               # noqa: E402

FAIL = []
UI_LOOK, UI_ACT, TR_MODE = 0, 7, 3
PROBE, FLAG = 0x3E80, 0x3EFF
UP, DOWN, LEFT, RIGHT = cpc.KEY_UP, cpc.KEY_DOWN, cpc.KEY_LEFT, cpc.KEY_RIGHT
KNAME = {UP: "ΠΑΝΩ", DOWN: "ΚΑΤΩ", LEFT: "ΑΡΙΣΤΕΡΑ", RIGHT: "ΔΕΞΙΑ"}

# --- Η ΠΡΟΖΑ: αξίες, μονάδες και ονόματα, ανά απόθεμα (1-13) ---
S = EC
VALUE = {S.S_FOOD: 5, S.S_ORE: 10, S.S_METAL: 15, S.S_BIOPL: 10, S.S_PROC: 40,
         S.S_SPARE: 15, S.S_MEDI: 25, S.S_GUN: 80, S.S_BOT: 120, S.S_STARCH: 5,
         S.S_VEG: 5, S.S_MEDPLANT: 10, S.S_MEAT: 5}
LOT = {S.S_FOOD: 10, S.S_ORE: 10, S.S_METAL: 5, S.S_BIOPL: 10, S.S_PROC: 2,
       S.S_SPARE: 5, S.S_MEDI: 4, S.S_GUN: 1, S.S_BOT: 1, S.S_STARCH: 10,
       S.S_VEG: 10, S.S_MEDPLANT: 10, S.S_MEAT: 10}
NAME = {S.S_FOOD: "MEALS", S.S_ORE: "ORE", S.S_METAL: "METAL", S.S_BIOPL: "PLASTIC",
        S.S_PROC: "CHIPS", S.S_SPARE: "SPARES", S.S_MEDI: "DRUGS", S.S_GUN: "WEAPONS",
        S.S_BOT: "ROBOTS", S.S_STARCH: "STARCH", S.S_VEG: "VEGGIES",
        S.S_MEDPLANT: "HERBS", S.S_MEAT: "MEAT"}
CAP, GIVE_MAX = 600, 99
GOODS = list(range(1, 14))
COINS, COIN_MAX = 0, 999                 # βήμα 135: το απόθεμα 0, σε δεκάδες
VALUE[COINS], LOT[COINS], NAME[COINS] = 10, 1, "COINS"

# Η κατάσταση του περιπάτου: κέρδος 47% (οι επεξεργαστές 40 x 47 = 18,8: το
# στρογγύλεμα φαίνεται), τέσσερα αγαθά, και αποθέματα στις άκρες — μέταλλο
# πέντε κάτω από το ταβάνι, τρόφιμα πάνω από 99, φάρμακα λιγότερα από μία
# μονάδα, επεξεργαστές και ρομπότ μηδέν.
MARKUP = 47
CARGO = [(S.S_METAL, 20), (S.S_PROC, 6), (S.S_BOT, 2), (S.S_FOOD, 40)]
STOCK = {S.S_WATER: 300, S.S_FOOD: 300, S.S_ORE: 120, S.S_METAL: 595, S.S_BIOPL: 45,
         S.S_PROC: 0, S.S_SPARE: 7, S.S_MEDI: 3, S.S_GUN: 0, S.S_BOT: 0,
         S.S_STARCH: 25, S.S_VEG: 0, S.S_MEDPLANT: 10, S.S_MEAT: 15}
HAVE_C, MC = 123, 15                     # νομίσματα: έχεις 123, φέρνει 150
COST = {"θέση 15": 312, "HUD": 12046, "προσγείωση": 1300, "frame": 1500, "σχέδιο": 60000}


def check(ok, msg):
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ ") + msg)
    if not ok:
        FAIL.append(msg)


def x_at(name, k):
    """Ενα πεδίο του EC_X (src/const.asm): στην τράπεζα 6, στο node_occ μετά τον
    χάρτη των εισβολέων (βήμα 172· ως τότε μετά τα σημάδια των πρακτόρων 0-99)."""
    const = open(os.path.join(ROOT, "src", "const.asm"), encoding="utf-8").read()
    mm = re.search(rf"^{name}\s+equ EC_X \+ (\d+)", const, re.M)
    assert mm and int(mm.group(1)) == k, f"{name}: το src/const.asm άλλαξε"
    return TO.layout()["G_node_occ"] + EC.X_OFF + k


X_COINS, X_MCOIN = x_at("EC_COINS", 6), x_at("EC_MCOIN", 11)


def econ_at():
    g = TO.layout()["G_econ_state"]
    const = open(os.path.join(ROOT, "src", "const.asm"), encoding="utf-8").read()
    names = ("EC_STOCK", "EC_SHETA", "EC_SHSTATE", "EC_SHKIND", "EC_MARKUP", "EC_CARGO",
             "EC_TRADED", "EC_NOTRADE", "EC_RND", "EC_SOLLEN", "EC_O2OK", "EC_POK",
             "EC_PADNODE")
    out = {}
    for n in names:
        mm = re.search(rf"^{n}\s+equ G_econ_state(?: \+ (\d+))?", const, re.M)
        out[n] = g + int(mm.group(1) or 0)
    return out


# --------------------------------------------------------------------------
# Η ΓΡΑΜΜΗ, όπως τη λέει η πρόζα
# --------------------------------------------------------------------------
def price(markup, g):
    v = VALUE[g]
    return v + (v * markup + 50) // 100


class Line:
    """Η γραμμή της πρόζας. Τα νομίσματα (COINS) σε δεκάδες: net, LOT, VALUE και
    όσα φέρνει (mc)· όσα έχεις (coins) σε νομίσματα."""
    def __init__(self, markup, cargo, stock, coins=HAVE_C, mc=MC):
        self.mk, self.cargo, self.stock = markup, dict(cargo), dict(stock)
        self.cargo[COINS], self.stock[COINS] = mc, coins
        self.order = ([g for g, _ in cargo] + [COINS]
                      + [g for g in GOODS if g not in self.cargo])
        self.sel, self.net = 0, {g: 0 for g in [COINS] + GOODS}

    def room(self, g):
        return (COIN_MAX - self.stock[g]) // 10 if g == COINS else CAP - self.stock[g]

    def have(self, g):
        return self.stock[g] // 10 if g == COINS else self.stock[g]

    def key(self, k):
        g = self.order[self.sel]
        n, lot = self.net[g], LOT[g]
        if k == LEFT:
            self.sel = (self.sel - 1) % 14
        elif k == RIGHT:
            self.sel = (self.sel + 1) % 14
        elif k == UP:
            self.net[g] = min(n + lot, 0) if n < 0 else \
                min(n + lot, self.cargo.get(g, 0), self.room(g))
        elif k == DOWN:
            self.net[g] = max(n - lot, 0) if n > 0 else \
                -min(-n + lot, self.have(g), GIVE_MAX)

    def totals(self):
        take = sum(n * price(self.mk, g) for g, n in self.net.items() if n > 0)
        give = sum(-n * VALUE[g] for g, n in self.net.items() if n < 0)
        return take, give

    def ok(self):
        take, give = self.totals()
        return take > 0 and give >= take

    def rows(self):
        take, give = self.totals()
        r3 = f"+{self.mk:2d}% TAKE {take:4d} GIVE {give:4d}" + (" FIRE=DEAL" if self.ok() else "")
        g = self.order[self.sel]
        n = self.net[g]
        if g == COINS:
            mid = f" TAKE {10 * n:3d}" if n > 0 else f" GIVE {-10 * n:3d}" if n < 0 else " " * 9
            r4 = (f" <{NAME[g]:7s}> SHIP {10 * self.cargo[g]:3d}" + mid
                  + f" HAVE {self.stock[g]:3d}")
        else:
            mid = f" TAKE {n:2d}" if n > 0 else f" GIVE {-n:2d}" if n < 0 else " " * 8
            r4 = (f" <{NAME[g]:7s}> SHIP {self.cargo.get(g, 0):2d}" + mid
                  + f" HAVE {self.stock[g]:3d} @{VALUE[g]:3d}")
        return TI.same(f"{r3:35s}"), TI.same(f"{r4:40s}")


class Game(TA.Game):
    """Το colony.sna σε παύση. Τα patch6 πειράζουν την τράπεζα 6 (b6code)."""
    def __init__(self, sym, patch=(), patch6=()):
        super().__init__(sym, patch)
        self.EC = econ_at()
        for at, v in patch6:
            self.b6[at - 0x4000] = v

    def w16(self, at):
        return self.m.peek(at) | self.m.peek(at + 1) << 8

    def s16(self, at, v):
        self.m.poke(at, v & 255)
        self.m.poke(at + 1, v >> 8)

    def stock(self, g=None):
        if g is None:
            return {k: self.w16(self.EC["EC_STOCK"] + 2 * k) for k in range(14)}
        return self.w16(self.EC["EC_STOCK"] + 2 * g)

    def set_stock(self, d):
        for k, v in d.items():
            self.s16(self.EC["EC_STOCK"] + 2 * k, v)

    def coins(self):
        return self.b6[X_COINS - 0x4000] | self.b6[X_COINS + 1 - 0x4000] << 8

    def set_coins(self, v):
        self.b6[X_COINS - 0x4000], self.b6[X_COINS + 1 - 0x4000] = v & 255, v >> 8

    def mcoin(self):
        return self.b6[X_MCOIN - 0x4000]

    def merchant(self, markup=MARKUP, cargo=CARGO, eta=300, mc=MC):
        self.b6[X_MCOIN - 0x4000] = mc
        self.s16(self.EC["EC_SHETA"], eta)
        self.m.poke(self.EC["EC_SHSTATE"], 2)
        self.m.poke(self.EC["EC_SHKIND"], 1)
        self.m.poke(self.EC["EC_MARKUP"], markup)
        flat = [v for p in cargo for v in p] + [0] * (8 - 2 * len(cargo))
        for i, v in enumerate(flat):
            self.m.poke(self.EC["EC_CARGO"] + i, v)

    def here(self):
        return self.m.peek(self.EC["EC_SHSTATE"]) == 2 and self.m.peek(self.EC["EC_SHKIND"]) == 1

    def r34(self):
        return TI.same(self.hud(3)[:35]), TI.same(self.hud(4))

    def open(self):
        self.tap("T")
        self.tap("M")
        return self.state() == UI_ACT and self.m.peek(self.sym["AC_MODE"]) == TR_MODE

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


def walk_keys():
    """Κάθε αγαθό: πέντε ΠΑΝΩ (ως όσα φέρνει ή χωράνε), δεκαέξι ΚΑΤΩ (πίσω στο
    μηδέν και ως όσα έχεις ή 99), ένα ΠΑΝΩ — και μετά είκοσι τυχαία."""
    keys = []
    for _ in [COINS] + GOODS:
        keys += [UP] * 5 + [DOWN] * 16 + [UP, RIGHT]
    rnd = random.Random(93)
    keys += [rnd.choice([UP, DOWN, LEFT, RIGHT]) for _ in range(20)]
    return keys


def line(sym, patch=(), quiet=False):
    """ΓΡΑΜΜΗ: κάθε πλήκτρο απέναντι στην πρόζα, σειρές 3-4. Η πρώτη διαφορά, ή None."""
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G = Game(sym, patch)
    G.set_stock(STOCK)
    G.set_coins(HAVE_C)
    G.merchant()
    if not G.open():
        return f"ΓΡΑΜΜΗ: με T, M κατάσταση {G.state()}, «{G.hud(3)}»"
    md = Line(MARKUP, CARGO, STOCK)
    if G.r34() != md.rows() or G.hud(3)[35:] != "PAUSE":
        return f"ΓΡΑΜΜΗ: ανοίγει «{G.hud(3)}» / «{G.hud(4)}» — η πρόζα λέει «{md.rows()[0]}» / «{md.rows()[1]}»"
    bar = G.bar()
    want = B.want_group("transport", lit={"trade"}, red={"ship"})
    if bar != want:
        return f"ΓΡΑΜΜΗ: η μπάρα «{B.show(bar)}», η πρόζα λέει «{B.show(want)}»"
    seen = set()
    for n, k in enumerate(walk_keys()):
        before = dict(md.net)
        md.key(k)
        G.tap(k)
        if G.r34() != md.rows():
            return (f"ΓΡΑΜΜΗ: πλήκτρο {n} ({KNAME[k]}) στο {NAME[md.order[md.sel]]}: "
                    f"«{G.r34()[0]}» / «{G.r34()[1]}» — η πρόζα λέει «{md.rows()[0]}» / «{md.rows()[1]}»")
        g = md.order[md.sel]
        if k in (UP, DOWN) and before[g] == md.net[g] and before[g] != 0:
            seen.add(("όριο", NAME[g]))
        if md.ok():
            seen.add(("FIRE=DEAL",))
    if any(G.stock(k) != v for k, v in STOCK.items()) or G.coins() != HAVE_C:
        return "ΓΡΑΜΜΗ: τα αποθέματα άλλαξαν χωρίς ανταλλαγή"
    # ESC: η προσφορά ξεχνιέται
    G.tap(cpc.KEY_ESC)
    st = G.state()
    G.open()
    md2 = Line(MARKUP, CARGO, STOCK)
    if st != UI_LOOK or G.r34() != md2.rows():
        return f"ESC: κατάσταση {st}, ξανανοίγει «{G.r34()[0]}» — η πρόζα λέει «{md2.rows()[0]}»"
    say(f"ΓΡΑΜΜΗ: {len(walk_keys())} πλήκτρα, ίδια με την πρόζα — όρια στα "
        f"{', '.join(sorted(x[1] for x in seen if x[0] == 'όριο'))}"
        f"{', και FIRE=DEAL' if ('FIRE=DEAL',) in seen else ''}; το ESC ξεχνά την προσφορά")
    return None


def deal(sym, patch=(), quiet=False):
    """FIRE/SPACE: το ζύγι, ο έλεγχος του αποθέματος, η ανταλλαγή."""
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G = Game(sym, patch)
    m = G.m
    jt = TO.layout()["G_job_tbl"]
    G.set_stock(STOCK)
    G.set_coins(HAVE_C)
    G.m.poke(G.EC["EC_TRADED"], 0)
    G.merchant()
    G.open()
    md = Line(MARKUP, CARGO, STOCK)
    # 5 μέταλλα (5 x 22 = 110) για 10 μεταλλεύματα (100): δεν φτάνει
    seq = [UP] + [RIGHT] * 5 + [DOWN]               # μετάλλευμα: μετά τα νομίσματα
    for k in seq:
        md.key(k)
        G.tap(k)
    G.tap(cpc.KEY_SPACE)
    if G.state() != UI_ACT or not G.here() or any(G.stock(k) != v for k, v in STOCK.items()):
        return f"ΖΥΓΙ: με 100 για 110 κατάσταση {G.state()}, έμπορος {G.here()}, αποθέματα {G.stock()}"
    # 20 μεταλλεύματα (200): φτάνει — αλλά στο μεταξύ έμειναν 15
    md.key(DOWN)
    G.tap(DOWN)
    if G.r34() != md.rows() or not md.ok():
        return f"ΖΥΓΙ: «{G.r34()[0]}» — η πρόζα λέει «{md.rows()[0]}»"
    G.set_stock({S.S_ORE: 15})
    G.tap(cpc.KEY_SPACE)
    m.run_frames(4)
    r3 = TI.same(G.hud(3))
    if (G.state() != UI_ACT or not G.here() or G.stock(S.S_ORE) != 15
            or G.stock(S.S_METAL) != 595 or not r3.startswith(TI.same("NOT ENOUGH MATERIAL"))):
        return (f"ΑΠΟΘΕΜΑ: με 15 μεταλλεύματα για 20 κατάσταση {G.state()}, «{r3}», "
                f"μετάλλευμα {G.stock(S.S_ORE)}, μέταλλο {G.stock(S.S_METAL)}")
    # ο πίνακας εργασιών γεμάτος: τίποτα. Με Drill, που δεν δίνουν τη θέση τους·
    # μια αδιάθετη Operate τη δίνει από το βήμα 115 (src/supply.asm).
    G.set_stock({S.S_ORE: 120})
    m.run_frames(120)                              # το μήνυμα κρατά δύο δευτερόλεπτα
    board = m.read_ram(jt, 160)
    full = bytes([EC.J_DRILL, 95, 255, 4, 95] * 32)
    m.write_ram(jt, full)
    before = G.stock()
    G.tap(cpc.KEY_SPACE)
    m.run_frames(4)
    if (G.state() != UI_ACT or not G.here() or G.stock() != before
            or m.read_ram(jt, 160) != full):
        return (f"ΠΙΝΑΚΑΣ ΓΕΜΑΤΟΣ: κατάσταση {G.state()}, έμπορος {G.here()}, αποθέματα "
                f"{'ίδια' if G.stock() == before else G.stock()}")
    m.write_ram(jt, board)
    # χωρίς πίστα — ένας μετεωρίτης τη ρίχνει, EC_PADNODE 255 — τίποτα (σε παύση
    # το πέρασμα δωματίων δεν την ξαναβρίσκει στο μεταξύ)
    pad0 = m.peek(G.EC["EC_PADNODE"])
    m.poke(G.EC["EC_PADNODE"], 255)
    before = G.stock()
    G.tap(cpc.KEY_SPACE)
    m.run_frames(4)
    if (G.state() != UI_ACT or not G.here() or G.stock() != before
            or m.read_ram(jt, 160) != board):
        return (f"ΧΩΡΙΣ ΠΙΣΤΑ: κατάσταση {G.state()}, έμπορος {G.here()}, αποθέματα "
                f"{'ίδια' if G.stock() == before else G.stock()}, εργασίες "
                f"{'ίδιες' if m.read_ram(jt, 160) == board else 'άλλαξαν'}")
    m.poke(G.EC["EC_PADNODE"], pad0)
    # η ανταλλαγή, με SPACE: 5 μέταλλα για 20 μεταλλεύματα
    m.run_frames(120)
    before = G.stock()
    G.tap(cpc.KEY_SPACE)
    m.run_frames(4)
    after = G.stock()
    diff = {k: after[k] - before[k] for k in range(14) if after[k] != before[k]}
    r3, r4 = G.rows()
    pad = m.peek(G.EC["EC_PADNODE"])
    new = [list(m.read_ram(jt + 5 * j, 5)) for j in range(32) if m.peek(jt + 5 * j) == EC.J_TRADE]
    cargo = list(m.read_ram(G.EC["EC_CARGO"], 8))
    got = (diff, G.state(), G.here(), m.peek(G.EC["EC_SHSTATE"]), m.peek(G.EC["EC_SHKIND"]),
           G.w16(G.EC["EC_SHETA"]), m.peek(G.EC["EC_TRADED"]), m.peek(G.EC["EC_MARKUP"]), cargo)
    want = ({S.S_ORE: -20}, UI_LOOK, False, 2, EC.SK_DEALT, 0xFFFF, 1, 2,
            [S.S_METAL, 5, S.S_PROC, 0, S.S_BOT, 0, S.S_FOOD, 0])
    # οι δύο μπορεί να τις πήρε ήδη κάποιος: ο πράκτορας και ο κόμβος αλλάζουν
    if (got != want or not r3.startswith(TI.same("TRADE DONE")) or r4.strip()
            or len(new) != 2 or any(j[0] != EC.J_TRADE or j[3] != 4 or j[4] for j in new)):
        return (f"ΑΝΤΑΛΛΑΓΗ: {got}, «{r3}» / «{r4}», J_TRADE {new} (πίστα {pad}) — η πρόζα "
                f"λέει {want}, δύο J_TRADE άδειες, προτεραιότητα 4")
    # και με FIRE: ένα ρομπότ (176) για 18 μεταλλεύματα (180) — δύο φορτία
    G.merchant()
    m.poke(G.EC["EC_TRADED"], 0)
    G.open()
    for k in [RIGHT, RIGHT, UP, RIGHT, RIGHT, RIGHT, DOWN, DOWN]:
        G.tap(k)
    before = G.stock()
    G.stick(0x10)
    m.run_frames(4)
    after = G.stock()
    diff = {k: after[k] - before[k] for k in range(14) if after[k] != before[k]}
    cargo = list(m.read_ram(G.EC["EC_CARGO"], 8))
    if (diff != {S.S_ORE: -20} or G.here() or m.peek(G.EC["EC_TRADED"]) != 1
            or m.peek(G.EC["EC_MARKUP"]) != 2 or cargo[5] != 1):
        return (f"FIRE: διαφορές {diff}, έμπορος {G.here()}, χρωστιούνται "
                f"{m.peek(G.EC['EC_MARKUP'])}, φορτίο του {cargo}")
    # 5 μέταλλα (110) για 99 τρόφιμα (495): δέκα φορτία, το τελευταίο εννιά
    G.merchant()
    G.set_stock({S.S_FOOD: 300, S.S_METAL: 595})
    G.open()
    for k in [UP] + [RIGHT] * 3 + [DOWN] * 10:      # μέταλλο, και τα τρόφιμα τέταρτα
        G.tap(k)
    G.tap(cpc.KEY_SPACE)
    m.run_frames(4)
    if m.peek(G.EC["EC_MARKUP"]) != 10 or G.stock(S.S_FOOD) != 300 - 99:
        return (f"ΦΟΡΤΙΑ: 99 τρόφιμα, χρωστιούνται {m.peek(G.EC['EC_MARKUP'])} φορτία, "
                f"τρόφιμα {G.stock(S.S_FOOD)} — η πρόζα λέει 10, 201")
    say("FIRE και SPACE: 100 για 110 τίποτα· 20 μεταλλεύματα όταν έμειναν 15, "
        "NOT ENOUGH MATERIAL και τίποτα· με τον πίνακα εργασιών γεμάτο ή χωρίς πίστα τίποτα· 5 μέταλλα "
        "για 20 μεταλλεύματα: τα 20 φεύγουν, 2 φορτία για τον έμπορο, τα 5 στο πλοίο του, "
        "δύο J_TRADE, TRADE DONE, το σερί σπάει, ο έμπορος περιμένει· ένα ρομπότ για 20 "
        "με FIRE· 99 τρόφιμα είναι 10 φορτία")
    return None


CARGO3 = [(S.S_METAL, 20), (S.S_PROC, 6), (S.S_BOT, 2)]     # κενή η τέταρτη θέση


def coins(sym, patch=(), quiet=False):
    """ΝΟΜΙΣΜΑΤΑ (βήμα 135): η γραμμή και η συμφωνία με νομίσματα. Η πρώτη διαφορά,
    ή None."""
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G = Game(sym, patch)
    m = G.m

    def keys(md, seq, tag):
        for n, k in enumerate(seq):
            md.key(k)
            G.tap(k)
            if G.r34() != md.rows():
                return (f"{tag}: πλήκτρο {n} ({KNAME[k]}) στο {NAME[md.order[md.sel]]}: "
                        f"«{G.r34()[0]}» / «{G.r34()[1]}» — η πρόζα λέει «{md.rows()[0]}» / "
                        f"«{md.rows()[1]}»")
        return None

    # --- ΤΟ 999: με 900, ως 90 από τα 150 του ---
    G.set_stock(STOCK)
    G.set_coins(900)
    G.merchant(cargo=CARGO3)
    G.open()
    md = Line(MARKUP, CARGO3, STOCK, coins=900)
    why = keys(md, [RIGHT] * 3 + [UP] * 12, "999")
    if why or md.net[COINS] != 9:
        return why or f"999: παίρνεις {10 * md.net[COINS]}"
    G.tap(cpc.KEY_ESC)
    # --- ΔΙΝΕΙΣ ΝΟΜΙΣΜΑΤΑ: 5 μέταλλα (110) για 120 από τα 123 ---
    G.set_coins(HAVE_C)
    G.set_stock(STOCK)
    m.poke(G.EC["EC_TRADED"], 0)
    G.merchant()
    G.open()
    md = Line(MARKUP, CARGO, STOCK)
    why = keys(md, [UP] + [RIGHT] * 4 + [DOWN] * 13, "ΔΙΝΕΙΣ")
    if why or md.net[COINS] != -12 or not md.ok():
        return why or f"ΔΙΝΕΙΣ: δίνεις {-10 * md.net[COINS]}, συμφωνία {md.ok()}"
    before = G.stock()
    G.tap(cpc.KEY_SPACE)
    m.run_frames(4)
    r3 = TI.same(G.hud(3))
    cargo = list(m.read_ram(G.EC["EC_CARGO"], 8))
    got = (G.coins(), G.stock() == before, G.here(), m.peek(G.EC["EC_SHKIND"]),
           m.peek(G.EC["EC_MARKUP"]), cargo, G.mcoin(), m.peek(G.EC["EC_TRADED"]))
    want = (3, True, False, EC.SK_DEALT, 0, [S.S_METAL, 5, S.S_PROC, 0, S.S_BOT, 0, S.S_FOOD, 0],
            MC, 1)
    if got != want or not r3.startswith(TI.same("TRADE DONE")):
        return f"ΔΙΝΕΙΣ: {got}, «{r3}» — η πρόζα λέει {want}, TRADE DONE"
    # --- ΠΑΙΡΝΕΙΣ ΝΟΜΙΣΜΑΤΑ: 150 (15 x 15 = 225) για 30 μεταλλεύματα (300), με
    # την τέταρτη θέση του φορτίου κενή ---
    G.set_coins(HAVE_C)
    G.set_stock(STOCK)
    G.merchant(cargo=CARGO3)
    G.open()
    md = Line(MARKUP, CARGO3, STOCK)
    why = keys(md, [RIGHT] * 3 + [UP] * 20 + [RIGHT] * 2 + [DOWN] * 3, "ΠΑΙΡΝΕΙΣ")
    if why or md.net[COINS] != MC or md.totals() != (225, 300):
        return why or f"ΠΑΙΡΝΕΙΣ: {md.net[COINS]} δεκάδες, ζύγι {md.totals()}"
    G.tap(cpc.KEY_SPACE)
    m.run_frames(4)
    cargo = list(m.read_ram(G.EC["EC_CARGO"], 8))
    got = (G.coins(), G.mcoin(), G.stock(S.S_ORE), m.peek(G.EC["EC_MARKUP"]), cargo,
           m.peek(G.EC["EC_SHKIND"]))
    want = (HAVE_C + 150, MC, STOCK[S.S_ORE] - 30, 3,
            [S.S_METAL, 0, S.S_PROC, 0, S.S_BOT, 0, 0, 0], EC.SK_DEALT)
    if got != want:
        return f"ΠΑΙΡΝΕΙΣ: {got} — η πρόζα λέει {want}"
    say("ΝΟΜΙΣΜΑΤΑ: με 900 ως 90 από τα 150 του· 5 μέταλλα για 120 από τα 123, 3 "
        "έμειναν, κανένα φορτίο προς αυτόν· 150 του για 30 μεταλλεύματα, 273, τρία "
        "φορτία, και η κενή θέση του φορτίου μένει κενή")
    return None


def leave(sym, patch=(), quiet=False):
    """Η γραμμή κλείνει όταν φύγει· το κουμπί χωρίς έμπορο· το μήνυμα."""
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G = Game(sym, patch)
    m = G.m
    G.set_stock(STOCK)
    G.merchant(eta=2)
    G.open()
    G.tap("2")                                      # x1
    for _ in range(8):
        m.run_frames(16)
        if G.state() == UI_LOOK:
            break
    G.tap("1")
    if G.state() != UI_LOOK or G.here():
        return f"ΦΕΥΓΕΙ: κατάσταση {G.state()}, έμπορος {G.here()} μετά από τρεις περιστροφές"
    # κανένας έμπορος: κόκκινο, και το M δεν ανοίγει τίποτα — ούτε για ένα frame
    m.poke(sym["AC_MODE"], 0)
    G.tap("T")
    bar = G.bar()
    G.tap("M")
    if (bar != B.want_group("transport", lit={"airlock"}, red={"ship", "trade"})
            or G.state() == UI_ACT or m.peek(sym["AC_MODE"]) == TR_MODE):
        return (f"ΚΟΥΜΠΙ: χωρίς έμπορο «{B.show(bar)}», μετά το M κατάσταση {G.state()}, "
                f"γραμμή {m.peek(sym['AC_MODE'])}")
    G.tap(cpc.KEY_ESC)
    # η γραμμή του πλοίου δείχνει κι αυτή τη ΜΕΤΑΦΟΡΑ, με το πλοίο λευκό (ως το
    # 93 τη ΔΙΑΧΕΙΡΙΣΗ, και τα γράμματά της δούλευαν από μέσα της)
    G.tap("C")
    bar = G.bar()
    G.tap(cpc.KEY_ESC)
    if bar != B.want_group("transport", lit={"ship"}, red={"trade"}):
        return f"ΚΟΥΜΠΙ: η γραμμή του πλοίου «{B.show(bar)}»"
    # με έμπορο: πράσινο
    G.merchant()
    G.tap("T")
    bar = G.bar()
    G.tap(cpc.KEY_ESC)
    if bar != B.want_group("transport", lit={"airlock"}, red={"ship"}):
        return f"ΚΟΥΜΠΙ: με έμπορο «{B.show(bar)}»"
    # το μήνυμα: τίποτα χειρότερο, και ο έμπορος εδώ ή όχι. Σε παύση το HUD δεν
    # ξαναγράφεται (src/main.asm): ένα hud_draw με την τράπεζα 1 — ΤΕΛΕΥΤΑΙΟ,
    # γιατί το probe κρατά τη μηχανή.
    m.poke(G.EC["EC_O2OK"], 1)
    m.poke(G.EC["EC_POK"], 1)
    G.call("HUD_DRAW", bank=0xC0)
    yes = TI.same(G.hud(2))
    m.poke(G.EC["EC_SHSTATE"], 0)
    G.call("HUD_DRAW", bank=0xC0)
    no = TI.same(G.hud(2))
    if (hudread.alert(no).rstrip() != TI.same("ALL SYSTEMS OK")
            or hudread.alert(yes).rstrip() != TI.same("MERCHANT LANDED")):
        return f"ΜΗΝΥΜΑ: «{yes}» με έμπορο, «{no}» χωρίς"
    say("ΦΕΥΓΕΙ: η γραμμή κλείνει μόνη της· χωρίς έμπορο το κουμπί κόκκινο και το M "
        "δεν ανοίγει τίποτα, και η γραμμή του πλοίου δείχνει τη ΜΕΤΑΦΟΡΑ με το πλοίο "
        "λευκό· με έμπορο πράσινο· «MERCHANT LANDED» στη σειρά 2, "
        "«ALL SYSTEMS OK» χωρίς")
    return None


# --------------------------------------------------------------------------
# ΦΟΡΤΙΟ — η προσγείωση, μία κλήση του ship_tick ανά σπόρο, απέναντι στην
# αναφορά. Οι σπόροι περνούν από τις άκρες.
# --------------------------------------------------------------------------
def seeds():
    found = {}
    conds = {"τρία": lambda b0, b1, b2: not b0 & 32, "τέσσερα": lambda b0, b1, b2: b0 & 32,
             "κέρδος 31": lambda b0, b1, b2: b0 & 31 == 31,
             "πρώτο 13-15": lambda b0, b1, b2: b1 & 15 >= 13,
             "βήμα 12-15": lambda b0, b1, b2: b1 >> 4 >= 12,
             "βήμα 0": lambda b0, b1, b2: b1 >> 4 == 0}
    for x in range(1, 65536):
        bb = EC.mer_bytes(x, 3)
        for k, c in conds.items():
            if k not in found and c(*bb):
                found[k] = x
        if len(found) == len(conds):
            return found
    return found


def landing(sym, patch6=(), quiet=False):
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G = Game(sym, patch6=patch6)
    m = G.m
    sollen = G.w16(G.EC["EC_SOLLEN"])
    for name, x in seeds().items():
        m.poke(G.EC["EC_SHSTATE"], 1)
        m.poke(G.EC["EC_SHKIND"], 1)
        G.s16(G.EC["EC_SHETA"], 0)
        G.s16(G.EC["EC_RND"], x)
        if G.call("SHIP_TICK") is None:
            return f"ΦΟΡΤΙΟ «{name}»: το ship_tick δεν τερμάτισε"
        e = EC.Econ()
        e.rnd, e.sollen = x, sollen
        EC.land_merchant(e)
        got = (m.peek(G.EC["EC_MARKUP"]), [m.peek(G.EC["EC_CARGO"] + i) for i in range(8)],
               G.w16(G.EC["EC_SHETA"]), m.peek(G.EC["EC_SHSTATE"]))
        want = (e.markup, e.cargo, sollen >> 5, 2)
        goods = [g for g in e.cargo[0::2] if g]
        if got != want or len(set(goods)) != len(goods) or not 35 <= e.markup <= 65:
            return f"ΦΟΡΤΙΟ «{name}» (σπόρος {x:#06x}): ο Z80 {got}, η αναφορά {want}"
    say(f"ΦΟΡΤΙΟ: {len(seeds())} σπόροι στις άκρες — κέρδος, φορτίο και μισό sol "
        f"({sollen >> 5} περιστροφές) ίδια με την αναφορά, τα αγαθά διαφορετικά")
    return None


def voyage(sym, quiet=False):
    """Ολόκληρο: η ζαριά στο παιχνίδι που τρέχει, η άφιξη, μισό sol, η αναχώρηση."""
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G = Game(sym)
    m = G.m
    G.s16(G.EC["EC_SOLLEN"], 1600)                # μισό sol = 50 περιστροφές
    m.poke(G.EC["EC_SHSTATE"], 0)
    roll = next(x for x in range(1, 65536) if EC.lfsr(EC.lfsr(x)) & 0x7FF == EC.MER_ROLL)
    G.s16(G.EC["EC_RND"], roll)
    m.poke(sym["UI_SPD"], 1)                      # x1, χωρίς πλήκτρο: από το frame 0
    seen, eta0, frames, last = [(0, 0)], None, 0, None
    while frames < 16 * 140:
        m.run_frames(1)
        frames += 1
        st, kind = m.peek(G.EC["EC_SHSTATE"]), m.peek(G.EC["EC_SHKIND"])
        if not seen or seen[-1][0] != st:
            seen.append((st, frames))
            if st == 2:
                e = EC.Econ()
                e.rnd, e.sollen = G.w16(G.EC["EC_RND"]), 1600
                EC.land_merchant(e)
                eta0 = G.w16(G.EC["EC_SHETA"])
                got = (kind, m.peek(G.EC["EC_MARKUP"]),
                       [m.peek(G.EC["EC_CARGO"] + i) for i in range(8)], eta0)
                if got != (1, e.markup, e.cargo, 50):
                    return f"ΤΑΞΙΔΙ: προσγειώθηκε με {got}, η αναφορά {(1, e.markup, e.cargo, 50)}"
            if st == 0 and len(seen) > 1:
                break
        last = G.w16(G.EC["EC_SHETA"]) if st == 2 else last
    m.poke(sym["UI_SPD"], 0)
    states = [s for s, _ in seen]
    if states != [0, 1, 2, 0] or last != 0:
        return f"ΤΑΞΙΔΙ: καταστάσεις {seen}, τελευταίο eta {last}"
    t_in, t_land, t_out = seen[1][1], seen[2][1], seen[3][1]
    revs_trip, revs_stay = round((t_land - t_in) / 16), round((t_out - t_land) / 16)
    # 24: η ζαριά και το πρώτο βήμα του ταξιδιού στην ίδια θέση 15· 51: πενήντα
    # περιστροφές μένει, και στην επόμενη φεύγει
    if revs_trip != 24 or revs_stay != 51:
        return f"ΤΑΞΙΔΙ: {revs_trip} περιστροφές ταξίδι, {revs_stay} στάση — η πρόζα λέει 24 και 51"
    say(f"ΤΑΞΙΔΙ: η ζαριά #5A5 στο παιχνίδι που τρέχει, άφιξη σε {revs_trip} περιστροφές, "
        f"φορτίο όπως η αναφορά, στάση {revs_stay} (μισό sol = 50, και η αναχώρηση)")
    return None


def independence(sym):
    G = Game(sym)
    m = G.m
    out = []
    for traded in (1, 0):
        m.poke(G.EC["EC_TRADED"], traded)
        m.poke(G.EC["EC_NOTRADE"], 9)
        G.call("SOL_ROLLOVER")
        out.append((m.peek(G.EC["EC_NOTRADE"]), m.peek(G.EC["EC_TRADED"])))
    return out


# --------------------------------------------------------------------------
# ΚΟΣΤΟΣ
# --------------------------------------------------------------------------
def quiet_seed():
    """Ενας σπόρος που δεν ρίχνει κανένα συμβάν στη θέση 15."""
    x = 1
    while True:
        r1 = EC.lfsr(x)
        r2 = EC.lfsr(r1)
        r3 = EC.lfsr(r2)
        if ((r1 & 15) and (r1 >> 4) != 0xFFF and (r2 >> 7) and (r3 & 0x7F) and (r3 >> 6)
                and (r2 & 0x7FF) not in (0, EC.MER_ROLL)):
            return x
        x += 1


def cost(sym):
    G = Game(sym)
    m = G.m
    base = G.probe([], True)
    G.s16(G.EC["EC_RND"], quiet_seed())
    m.poke(G.EC["EC_SHSTATE"], 0)
    slot15 = G.call("ECON_EVENTS", True) - base
    G.call("HUD_DRAW", True, 0xC0)
    hud = G.call("HUD_DRAW", True, 0xC0) - base
    lands = []
    for x in seeds().values():
        m.poke(G.EC["EC_SHSTATE"], 1)
        m.poke(G.EC["EC_SHKIND"], 1)
        G.s16(G.EC["EC_SHETA"], 0)
        G.s16(G.EC["EC_RND"], x)
        lands.append(G.call("SHIP_TICK", True) - base)
    # η γραμμή ανοιχτή, με προσφορά σε τέσσερα αγαθά
    G.set_stock(STOCK)
    G.merchant()
    G.open()
    for k in [UP, RIGHT, UP, RIGHT, UP, RIGHT, RIGHT, RIGHT, DOWN, RIGHT, DOWN]:
        G.tap(k)
    frame = G.call("UI_TICK", True, 0xC0) - base
    draw = G.probe([0xCD, sym["UI_DIRTY"] & 255, sym["UI_DIRTY"] >> 8,
                    0xCD, sym["UI_PANEL"] & 255, sym["UI_PANEL"] >> 8], True, 0xC0) - base
    return {"θέση 15": slot15, "HUD": hud, "προσγείωση": max(lands), "frame": frame,
            "σχέδιο": draw}


# --------------------------------------------------------------------------
# ΑΡΝΗΤΙΚΑ
# --------------------------------------------------------------------------
def t_addr(sym, x_name):
    """Η σελιδοποιημένη διεύθυνση ενός κειμένου (src/uitext.asm): x_ - TEXT_IMG + G_text."""
    g = TO.layout()["G_text"]
    return sym[x_name] - (0xC000 + g - 0x4000) + g


def find(data, lo, pat):
    return [lo + k for k in range(len(data) - len(pat) + 1) if list(data[k:k + len(pat)]) == pat]


def negatives(sym):
    G = Game(sym)
    m = G.m
    ram = lambda name, n, pat: find(m.read_ram(sym[name], n), sym[name], pat)
    six = lambda name, n, pat: find(bytes(G.b6[sym[name] - 0x4000:sym[name] - 0x4000 + n]),
                                    sym[name], pat)
    out = []

    def add(label, at, edits, in6, test):
        out.append((label, [(at[0] + k, v) for k, v in edits] if len(at) == 1 else None, in6, test))
    # --- φορτίο (τράπεζα 6) ---
    add("πάντα τρία αγαθά", six("SM_LAND", 96, [0xCB, 0x6A, 0x28, 0x01, 0x04]), [(4, 0)],
        True, "landing")                            # bit 5,d · jr z · inc b
    add("κέρδος χωρίς mod 31", six("SM_LAND", 96, [0xFE, 31, 0x38]), [(1, 32)], True, "landing")
    add("βήμα χωρίς + 1", six("SML_D", 4, [0x3C, 0x57]), [(0, 0)], True, "landing")
    eta = G.EC["EC_SHETA"]
    add("μένει οκτώ περιστροφές", six("SML_H", 12, [0x22, eta & 255, eta >> 8]),
        [(0, 0), (1, 0), (2, 0)], True, "landing")   # ld (EC_SHETA),hl
    # --- γραμμή (τράπεζα 0) ---
    cap = 600
    add("χωρίς το ταβάνι της αποθήκης", ram("TRU_TK", 12, [0x21, cap & 255, cap >> 8]),
        [(1, 0xFF), (2, 0x7F)], False, "line")
    add("χωρίς το 99", ram("TRU_GV", 24, [0xFE, 99, 0x38]), [(1, 255)], False, "line")
    add("χωρίς το «όσα έχεις»", ram("TRU_GV", 24, [0x3E, 99, 0x20]), [(2, 0x18)], False, "line")
    add("τιμή χωρίς στρογγύλεμα", ram("TR_PRICE", 24, [0x11, 50, 0]), [(1, 0)], False, "line")
    # η σειρά των αποθεμάτων: το πρώτο πέρασμα δεν γράφει, το δεύτερο γράφει όλα
    a1 = ram("TR_OPEN", 48, [0x1A, 0xB7, 0x28, 0x02, 0x77, 0x2C])
    a2 = ram("TR_OPEN", 96, [0x28, 0x02, 0x71, 0x2C])
    out.append(("τα δικά του όχι πρώτα", [(a1[0] + 4, 0), (a1[0] + 5, 0), (a2[0], 0), (a2[0] + 1, 0)]
                if len(a1) == 1 and len(a2) == 1 else None, False, "line"))
    # --- ανταλλαγή ---
    ok_ = sym["TR_OK"]
    add("χωρίς το ζύγι", ram("TR_DEAL", 12, [0xCD, ok_ & 255, ok_ >> 8, 0xDA]),
        [(3, 0), (4, 0), (5, 0)], False, "deal")
    poor = t_addr(sym, "X_T_POOR")
    add("χωρίς τον έλεγχο του αποθέματος", ram("TR_DEAL", 64, [0x21, poor & 255, poor >> 8, 0xDA]),
        [(3, 0), (4, 0), (5, 0)], False, "deal")
    add("χωρίς το σερί", ram("TR_DEAL", 300, [0x32, G.EC["EC_TRADED"] & 255,
                                               G.EC["EC_TRADED"] >> 8]),
        [(0, 0), (1, 0), (2, 0)], False, "deal")
    add("η γραμμή του ξανανοίγει", ram("TR_DEAL", 300, [0x32, G.EC["EC_SHKIND"] & 255,
                                                         G.EC["EC_SHKIND"] >> 8]),
        [(0, 0), (1, 0), (2, 0)], False, "deal")
    # trd_post: ld a,(EC_PADNODE) -> or 1 · ret (NZ, καμία εργασία)
    add("χωρίς μεταφορείς", [sym["TRD_POST"]], [(0, 0xF6), (1, 1), (2, 0xC9)], False, "deal")
    tp = sym["TRD_POST"]
    add("συμφωνία με τον πίνακα γεμάτο", ram("TR_DEAL", 200, [0xCD, tp & 255, tp >> 8, 0xCA]),
        [(3, 0), (4, 0), (5, 0)], False, "deal")          # call trd_post · jp z,uip_deny
    add("συμφωνία χωρίς πίστα", [sym["TRD_POST"]], [(4, 0)], False, "deal")   # ret z -> nop
    add("ένα φορτίο ανά αγαθό", ram("TR_DEAL", 200, [0xD6, EC.TRADE_LOAD, 0x28]),
        [(4, 0), (5, 0)], False, "deal")                  # sub 10 · jr z · jr nc,trd_ld
    add("το πλοίο του κρατά όλο το φορτίο", ram("TR_DEAL", 300, [0x23, 0x77, 0x23, 0x10]),
        [(1, 0)], False, "deal")                          # trd_cg: inc hl · ld (hl),a
    # --- νομίσματα (βήμα 135) ---
    add("τα νομίσματα ως το 600 της αποθήκης, χωρίς δεκάδες",
        ram("TRU_TK", 24, [0x3A, sym["TR_G"] & 255, sym["TR_G"] >> 8, 0xB7, 0x20]),
        [(4, 0x18)], False, "coins")                    # jr nz,tru_sb -> jr
    nc = sym["TR_NETC"]
    add("τα νομίσματα έξω από το ζύγι",                 # ld c,0 -> ld c,1
        ram("TR_SUM", 16, [0x0E, 0x00, 0xCD, nc & 255, nc >> 8]), [(1, 1)], False, "line")
    add("νομίσματα που δεν αλλάζουν χέρια", ram("TR_DEAL", 300, [0x22, X_COINS & 255, X_COINS >> 8]),
        [(0, 0), (1, 0), (2, 0)], False, "coins")
    tn = sym["TR_NET"] if "TR_NET" in sym else TO.layout()["G_crew"]
    add("η θέση 0 του φορτίου τα κρατά", ram("TR_DEAL", 300, [0x21, tn & 255, tn >> 8, 0x7E, 0x36, 0]),
        [(4, 0), (5, 0)], False, "coins")
    # --- κουμπί, γραμμή που κλείνει, μήνυμα ---
    mh = sym["MER_HERE"]
    add("η γραμμή δεν κλείνει όταν φύγει", ram("TR_TICK", 8, [0xCD, mh & 255, mh >> 8, 0x28]),
        [(3, 0x18)], False, "leave")
    add("το κουμπί δεν κοκκινίζει", ram("BWT_MER", 4, [0xCD, mh & 255, mh >> 8]),
        [(0, 0xAF), (1, 0), (2, 0)], False, "leave")   # xor a: Z, «είναι εδώ»
    add("ανοίγει χωρίς έμπορο", ram("TR_OPEN", 4, [0xCD, mh & 255, mh >> 8]),
        [(0, 0xAF), (1, 0), (2, 0)], False, "leave")
    add("η γραμμή του πλοίου στη ΔΙΑΧΕΙΡΙΣΗ, όπως ως το 92",
        ram("BWW_ACT", 12, [0xFE, 2, 0x38]), [(2, 0x18)], False, "leave")
    # 200: από το βήμα 119 το NO ENGINEER με όνομα και το BROKEN είναι πριν από
    # αυτό, και η κλήση κάθεται στο +137 (ως τότε μέσα στα 120)
    add("το μήνυμα λείπει", ram("HUD_ALERT", 200, [0xCD, mh & 255, mh >> 8]),
        [(0, 0xF6), (1, 1), (2, 0)], False, "leave")    # or 1: NZ, «δεν είναι εδώ»
    return out


def main():
    sym, g = TG.build()

    # Οι πίνακες του Z80 (src/stock.asm) και της αναφοράς είναι οι τιμές της πρόζας.
    G = Game(sym)
    tv = list(G.m.read_ram(sym["TR_VALUE"], 14))
    tl = list(G.m.read_ram(sym["TR_LOT"], 14))
    want_v = [VALUE[k] for k in [COINS] + GOODS]
    want_l = [LOT[k] for k in [COINS] + GOODS]
    check(tv == want_v == EC.TRADE_VALUE and tl == want_l == EC.TRADE_LOT,
          f"τιμές και μονάδες: ο Z80 {tv} / {tl}, η αναφορά ίδια, όπως η πρόζα")

    why = landing(sym)
    check(why is None, why or "φορτίο: όπως η πρόζα και η αναφορά")
    why = voyage(sym)
    check(why is None, why or "ταξίδι: από τη ζαριά ως την αναχώρηση")
    why = line(sym)
    check(why is None, why or "γραμμή: πλήκτρο προς πλήκτρο, όπως η πρόζα")
    why = deal(sym)
    check(why is None, why or "ανταλλαγή: ζύγι, απόθεμα, και ο έμπορος φεύγει")
    why = coins(sym)
    check(why is None, why or "νομίσματα: τα δέχεται και τα πουλά, αμέσως, ως το 999")
    why = leave(sym)
    check(why is None, why or "αναχώρηση, κουμπί και μήνυμα")
    ind = independence(sym)
    check(ind == [(0, 0), (10, 0)],
          f"ανεξαρτησία: το sol με ανταλλαγή μηδενίζει το σερί, χωρίς ανεβαίνει — {ind}")

    got = cost(sym)
    check(all(got[k] <= COST[k] for k in COST),
          "κόστος: " + ", ".join(f"{k} {got[k]} us (ταβάνι {COST[k]})" for k in COST))

    run = {"landing": lambda s, p6: landing(s, patch6=p6, quiet=True),
           "line": lambda s, p: line(s, p, quiet=True),
           "deal": lambda s, p: deal(s, p, quiet=True),
           "coins": lambda s, p: coins(s, p, quiet=True),
           "leave": lambda s, p: leave(s, p, quiet=True)}
    for label, edits, in6, test in negatives(sym):
        if edits is None:
            check(False, f"ΑΡΝΗΤΙΚΟ «{label}»: το σημείο δεν βρέθηκε ακριβώς μία φορά")
            continue
        why = run[test](sym, edits)
        check(why is not None, f"ΑΡΝΗΤΙΚΟ «{label}»: " + (why or "πέρασε — η δοκιμή δεν το βλέπει"))

    print()
    if FAIL:
        print(f"{len(FAIL)} ΑΠΟΤΥΧΙΕΣ")
        return 1
    print("ΟΛΑ ΟΚ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
