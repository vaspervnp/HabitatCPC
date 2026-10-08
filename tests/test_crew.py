#!/usr/bin/env python3
"""Ποιοι έρχονται με το πλοίο αποίκων (βήμα 91, DESIGN §6.11), στο colony.sna.

Η πρόζα — οι αποφάσεις του παίκτη:

  ΓΡΑΜΜΗ     το C στο LOOK, και το κουμπί του πλοίου στη ΜΕΤΑΦΟΡΑ, ανοίγουν
             τη γραμμή του πλοίου στις σειρές 3-4:
               σειρά 3   SHIP UP/DN=10% FIRE=CALL ESC=BACK
               σειρά 4    >WRK 20 ENG 20 BIO 20 MED 20 GRD 20
             με την ταχύτητα στις στήλες 35-39 όπως πάντα. Νέο παιχνίδι: 20%
             η καθεμία.
  ΑΡΙΣΤΕΡΑ/ΔΕΞΙΑ  διαλέγουν ειδικότητα, κυκλικά· το «>» πάει μαζί.
  ΠΑΝΩ       +10% στη διαλεγμένη, -10% από τη μεγαλύτερη από τις άλλες· στο
             100% τίποτα.
  ΚΑΤΩ       -10% στη διαλεγμένη, +10% στη μικρότερη από τις άλλες· στο 0%
             τίποτα. Σε ισοπαλία η πρώτη. Το άθροισμα είναι πάντα 100, και ό,τι
             φαίνεται είναι ό,τι κρατά το παιχνίδι (EC_LAND).
  ESC        πίσω στο LOOK χωρίς πλοίο· τα ποσοστά μένουν, και η γραμμή
             ξανανοίγει όπως ήταν.
  FIRE, SPACE  καλούν το πλοίο: COLONIST SHIP CALLED, η σειρά 4 κενή. Χωρίς
             αίθουσα ελέγχου ό,τι έλεγε ως τώρα το C: NEED A CONTROL ROOM.
  ΚΑΝΟΝΑΣ    κάθε νεοφερμένος παίρνει την ειδικότητα που λείπει περισσότερο
             από τους ζωντανούς ανθρώπους, ως προς τα ποσοστά· στην ισοπαλία
             η πρώτη. Ποτέ ρομπότ, ποτέ ειδικότητα με 0%. Οι νεκροί και τα
             ρομπότ δεν μετράνε. Οι ρόλοι γράφονται εδώ με το χέρι, ΚΑΙ
             βγαίνουν ίδιοι από την αναφορά (tools/econ.py, pick_role).
  ΠΛΟΙΟ      όλη η διαδρομή: ποσοστά από τα πλήκτρα, FIRE, το πλοίο
             προσγειώνεται, και οι τέσσερις είναι όσοι λέει ο κανόνας για την
             αποικία της στιγμής εκείνης.
  ΚΟΣΤΟΣ     η προσγείωση (ship_crew, τέσσερις καινούργιοι) με 4, 48 και 76
             ζωντανούς κάτω από τα ταβάνια COST: 3.198, 4.386 και 5.148 us. Στο
             βήμα 90 με 4 και 48 ήταν 1.692 και 2.220· η πρώτη γραφή του 91
             ήθελε 6.655 και 8.151. Ως το 92 μετριόταν και με 124, που δεν
             χωρούν πια (οι άποικοι είναι ως 80).

Αρνητικά, με τον κώδικα πειραγμένο στη μνήμη. Γραμμή: ΠΑΝΩ χωρίς δότη, χωρίς
ταβάνι στο 100%, χωρίς πάτωμα στο 0%, ο παραλήπτης του ΚΑΤΩ η μεγαλύτερη, η
οθόνη που δεν ξαναζωγραφίζεται, το SPACE που δεν καλεί, το C που καλεί
κατευθείαν όπως ως το βήμα 90. Κόστος: η μέτρηση χωρίς την πρόωρη έξοδο
περνά το ταβάνι των 4. Κανόνας: ταυτότητα & 7 όπως ως το 90, χωρίς
το cw_count, η ισοπαλία στον τελευταίο, οι νεκροί που μετράνε, ο πρώτος νεκρός
(από όπου ψάχνει θέσεις το ship_crew) που γίνεται ο τελευταίος.
"""
import os, random, re, sys, types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import test_act as TA                                    # noqa: E402
import test_info as TI                                   # noqa: E402
import test_outside as TO                                # noqa: E402
import econ as EC                                        # noqa: E402
import cpc                                               # noqa: E402

FAIL = []
UI_LOOK, UI_ACT = 0, 7
NAMES = ["WRK", "ENG", "BIO", "MED", "GRD"]
KEYS = "SHIP UP/DN=10% FIRE=CALL ESC=BACK"
PROBE, FLAG = 0x3E00, 0x3EFF
SHIP_LANDED = 2
R_CONTROL, VOY_DOME = 1, 2                  # src/const.asm· ο θόλος 2 του colony.sna


def check(ok, msg):
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ ") + msg)
    if not ok:
        FAIL.append(msg)


def econ_at():
    """{όνομα: διεύθυνση} για όσα EC_ θέλει η δοκιμή, από το src/const.asm."""
    g = TO.layout()["G_econ_state"]
    const = open(os.path.join(ROOT, "src", "const.asm"), encoding="utf-8").read()
    return {n: g + int(re.search(rf"^{n}\s+equ G_econ_state \+ (\d+)", const, re.M).group(1))
            for n in ("EC_LAND", "EC_ALIVE", "EC_POPCAP", "EC_SHSTATE", "EC_PADNODE")}


class Game(TA.Game):
    def __init__(self, sym, patch=()):
        super().__init__(sym, patch)
        self.EC = econ_at()
        self.ag = TO.layout()["G_agent_fields"] - 0x4000
        self.pad = self.m.peek(self.E["PAD"])   # η πίστα του colony.sna (64)

    def land(self):
        return [self.m.peek(self.EC["EC_LAND"] + r) for r in range(5)]

    def r34(self):
        """Η σειρά 3 ως τον δείκτη ταχύτητας, και η 4 ολόκληρη."""
        return TI.same(self.hud(3)[:35]), TI.same(self.hud(4))

    def agents(self):
        return ([self.b6[self.ag + i] for i in range(128)],
                [self.b6[self.ag + 128 + i] for i in range(128)])

    def probe(self, body):
        m = self.m
        code = ([0xF3, 0x31, 0x00, 0x01, 0x01, 0xC6, 0x7F, 0xED, 0x49] + body   # τράπεζα 6
                + [0x3E, 0x5A, 0x32, FLAG & 255, FLAG >> 8, 0x18, 0xFE])
        m.write_ram(PROBE, bytes(code))
        m.poke(FLAG, 0)
        m.set_pc(PROBE)
        for _ in range(2000):
            m.run_us(100)
            if m.peek(FLAG) == 0x5A:
                return True
        return False


def want_rows(land, sel):
    r3 = f"{KEYS:35s}"
    r4 = " " + "".join((">" if r == sel else " ") + NAMES[r] + f"{10 * land[r]:3d}"
                       for r in range(5))
    return TI.same(r3), TI.same(f"{r4:40s}")


class Model:
    """Η πρόζα της γραμμής, πλήκτρο προς πλήκτρο."""
    def __init__(self, land, sel=0):
        self.t, self.sel = list(land), sel

    def key(self, k):
        t, s = self.t, self.sel
        others = [r for r in range(5) if r != s]
        if k == cpc.KEY_LEFT:
            self.sel = (s - 1) % 5
        elif k == cpc.KEY_RIGHT:
            self.sel = (s + 1) % 5
        elif k == cpc.KEY_UP and t[s] < 10:
            t[s] += 1
            t[min(others, key=lambda r: (-t[r], r))] -= 1      # η μεγαλύτερη, η πρώτη
        elif k == cpc.KEY_DOWN and t[s] > 0:
            t[s] -= 1
            t[min(others, key=lambda r: (t[r], r))] += 1       # η μικρότερη, η πρώτη


def find(m, lo, hi, pat):
    """Οι διευθύνσεις του pat στη μνήμη [lo, hi)."""
    ram = m.read_ram(lo, hi - lo)
    return [lo + k for k in range(len(ram) - len(pat) + 1) if list(ram[k:k + len(pat)]) == pat]


# --------------------------------------------------------------------------
# ΓΡΑΜΜΗ
# --------------------------------------------------------------------------
UP, DOWN, LEFT, RIGHT = cpc.KEY_UP, cpc.KEY_DOWN, cpc.KEY_LEFT, cpc.KEY_RIGHT
WALK = ([UP] * 9                         # ο εργάτης ως το 100%, και ένα ακόμη: τίποτα
        + [RIGHT, DOWN]                  # ο μηχανικός στο 0%: τίποτα
        + [LEFT, LEFT]                   # κυκλικά: ο φρουρός
        + [UP, UP, UP, DOWN, DOWN]
        + [RIGHT, DOWN] * 3              # ο εργάτης κάτω, στις μικρότερες
        + [RIGHT] * 5 + [LEFT] * 6)


def chooser(sym, patch=(), quiet=False):
    """ΓΡΑΜΜΗ ως FIRE. Η πρώτη διαφορά από την πρόζα, ή None."""
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G = Game(sym, patch)
    m = G.m
    G.ship(1, G.pad, 0)
    if G.land() != [2] * 5:
        return f"ΓΡΑΜΜΗ: το EC_LAND είναι {G.land()} — νέο παιχνίδι, 20% η καθεμία"
    G.tap("C")
    md = Model(G.land())
    if G.state() != UI_ACT or G.r34() != want_rows(md.t, 0) or G.hud(3)[35:] != "PAUSE":
        return (f"ΓΡΑΜΜΗ: με το C κατάσταση {G.state()}, «{G.hud(3)}» / «{G.hud(4)}» — "
                f"η πρόζα λέει «{want_rows(md.t, 0)[0]}PAUSE» / «{want_rows(md.t, 0)[1]}»")
    rnd = random.Random(91)
    keys = WALK + [rnd.choice([UP, UP, DOWN, LEFT, RIGHT]) for _ in range(60)]
    seen = {"100": 0, "0": 0, "tie": 0}
    for n, k in enumerate(keys):
        before = list(md.t)
        md.key(k)
        G.tap(k)
        if G.land() != md.t or G.r34() != want_rows(md.t, md.sel) or sum(G.land()) != 10:
            name = {UP: "ΠΑΝΩ", DOWN: "ΚΑΤΩ", LEFT: "ΑΡΙΣΤΕΡΑ", RIGHT: "ΔΕΞΙΑ"}[k]
            return (f"ΓΡΑΜΜΗ: πλήκτρο {n} ({name}) από {before}: EC_LAND {G.land()}, "
                    f"«{G.hud(4).rstrip()}» — η πρόζα λέει {md.t}, «{want_rows(md.t, md.sel)[1]}»")
        seen["100"] += 10 in md.t
        seen["0"] += 0 in md.t
        seen["tie"] += k in (UP, DOWN) and before != md.t and len(set(
            before[r] for r in range(5) if r != md.sel)) < 4
    if not all(seen.values()):
        return f"ΓΡΑΜΜΗ: ο περίπατος δεν πέρασε από όλα τα όρια {seen}"
    say(f"ΓΡΑΜΜΗ: {len(keys)} πλήκτρα, ίδια με την πρόζα στην οθόνη και στο EC_LAND, "
        f"άθροισμα πάντα 100· στο 100% {seen['100']} φορές, στο 0% {seen['0']}, "
        f"ισοπαλίες {seen['tie']}")
    # ESC: τίποτα δεν φεύγει, και ξανανοίγει όπως ήταν
    G.tap(cpc.KEY_ESC)
    if G.state() != UI_LOOK or m.peek(G.E["SHIP"]) != 0 or G.land() != md.t:
        return f"ESC: κατάσταση {G.state()}, πλοίο {m.peek(G.E['SHIP'])}, EC_LAND {G.land()}"
    G.tap("T")                                      # το κουμπί της ΜΕΤΑΦΟΡΑΣ
    G.tap("C")
    if G.state() != UI_ACT or G.r34() != want_rows(md.t, md.sel):
        return f"το κουμπί του πλοίου: κατάσταση {G.state()}, «{G.hud(4).rstrip()}»"
    say(f"ESC: πίσω στο LOOK χωρίς πλοίο· το κουμπί του πλοίου ξανανοίγει τη γραμμή "
        f"όπως ήταν, «{G.hud(4).strip()}»")
    return calls(G, md, say)


def calls(G, md, say):
    m = G.m
    for how in ("FIRE", "SPACE"):
        G.ship(1, G.pad, 0)
        if G.state() != UI_ACT:
            G.tap("C")
        if how == "FIRE":
            G.stick(0x10)
        else:
            G.tap(cpc.KEY_SPACE)
        m.run_frames(20)
        r3, r4 = G.rows()
        if (G.state() != UI_LOOK or m.peek(G.E["SHIP"]) == 0
                or not r3.startswith(TI.same("COLONIST SHIP CALLED")) or r4.strip()):
            return f"{how}: κατάσταση {G.state()}, πλοίο {m.peek(G.E['SHIP'])}, «{r3}» / «{r4}»"
        if G.land() != md.t:
            return f"{how}: το EC_LAND έγινε {G.land()}"
    G.ship(0, G.pad, 0)                             # χωρίς αίθουσα ελέγχου
    G.tap("C")
    G.stick(0x10)
    m.run_frames(20)
    r3 = G.rows()[0]
    if G.state() != UI_LOOK or m.peek(G.E["SHIP"]) != 0 or not r3.startswith(
            TI.same("NEED A CONTROL ROOM")):
        return f"χωρίς αίθουσα ελέγχου: κατάσταση {G.state()}, πλοίο {m.peek(G.E['SHIP'])}, «{r3}»"
    say("FIRE και SPACE: COLONIST SHIP CALLED, η σειρά 4 κενή· χωρίς αίθουσα ελέγχου "
        "NEED A CONTROL ROOM και κανένα πλοίο")
    return None


# --------------------------------------------------------------------------
# ΚΑΝΟΝΑΣ — (όνομα, ποσοστά σε δέκατα, (σημαίες, ρόλοι), πόσο πάνω από τους
# ζωντανούς είναι το EC_ALIVE, οι ρόλοι των τεσσάρων).
# --------------------------------------------------------------------------
def population(alive, dead):
    """Οι ζωντανοί ανά ρόλο στις πρώτες ταυτότητες, οι νεκροί στις επόμενες,
    και οι καινούργιοι στις πρώτες νεκρές."""
    flags, roles = [0] * 128, [7] * 128
    i = 0
    for alive_, counts in ((3, alive), (0, dead)):
        for r, n in enumerate(counts):
            for _ in range(n):
                flags[i], roles[i] = alive_, r
                i += 1
    return flags, roles


def scattered():
    """Ζωντανοί στις ζυγές 0-38 (10 εργάτες, 5 μηχανικοί, 5 βιολόγοι), νεκροί
    στις μονές, και ένα ρομπότ στην 127: οι καινούργιοι στις 1, 3, 5, 7, και
    το cw_count μετρά ως την 127."""
    flags, roles = [0] * 128, [7] * 128
    for k, r in enumerate([0] * 10 + [1] * 5 + [2] * 5):
        flags[2 * k], roles[2 * k] = 3, r
    flags[127], roles[127] = 3, 6
    return flags, roles


RULE_CASES = (
    ("άδεια αποικία, 20% η καθεμία", [2] * 5, population([], []), 0, [0, 1, 2, 3]),
    ("20 εργάτες, 100% φρουροί", [0, 0, 0, 0, 10], population([20], []), 0, [4, 4, 4, 4]),
    ("λείπουν γιατροί, και 18 ρομπότ", [3, 2, 2, 2, 1],
     population([10, 10, 10, 4, 10, 6, 6, 6], []), 0, [3, 3, 0, 3]),
    ("ένας από τον καθένα: ισοπαλίες", [2] * 5, population([1, 1, 1, 1, 1], []), 0, [0, 1, 2, 3]),
    ("30 νεκροί εργάτες δεν μετράνε", [5, 5, 0, 0, 0], population([4, 4], [30]), 0, [0, 1, 0, 1]),
    # 76: τέσσερις ακόμη χωρούν στις 80 θέσεις αποίκων (βήμα 92· ως τότε 120)
    ("76 ζωντανοί, 0% εργάτες", [0, 2, 2, 3, 3], population([36, 20, 10, 5, 5], []), 0,
     [3, 4, 3, 4]),
    ("100% εργάτες", [10, 0, 0, 0, 0], population([0, 0, 0, 0, 5], []), 0, [0, 0, 0, 0]),
    ("κενά ανάμεσα, ένα ρομπότ στην 127", [2] * 5, scattered(), 0, [3, 4, 3, 4]),
    ("EC_ALIVE 7 πάνω: θάνατοι πριν από τη μέτρηση", [3, 2, 2, 2, 1],
     population([10, 10, 10, 4, 10, 6, 6, 6], [7]), 7, [3, 3, 0, 3]),
)


def reference(land, flags, roles):
    count = [sum(1 for i in range(128) if flags[i] & 1 and roles[i] == r) for r in range(5)]
    e = types.SimpleNamespace(land=land)
    return [EC.pick_role(e, count) for _ in range(4)]


def rules(sym, patch=()):
    """[(όνομα, ρόλοι των καινούργιων με τη σειρά των ταυτοτήτων τους)] — ένα
    μηχάνημα, ένα probe ανά περίπτωση."""
    G = Game(sym, patch)
    out = []
    for name, land, (flags, roles), stale, _ in RULE_CASES:
        for i in range(128):
            G.b6[G.ag + i], G.b6[G.ag + 128 + i] = flags[i], roles[i]
        n = sum(1 for f in flags if f & 1)
        for r in range(5):
            G.m.poke(G.EC["EC_LAND"] + r, land[r])
        G.m.poke(G.EC["EC_ALIVE"], n + stale)
        G.m.poke(G.EC["EC_POPCAP"], n + stale + 4)
        G.m.poke(G.EC["EC_PADNODE"], G.pad)
        if not G.probe([0xCD, sym["SHIP_CREW"] & 255, sym["SHIP_CREW"] >> 8]):
            return None
        f2, r2 = G.agents()
        born = [i for i in range(128) if f2[i] & 1 and not flags[i] & 1]
        out.append((name, [r2[i] for i in born], born))
    return out


def rule_check(sym):
    got = rules(sym)
    if got is None:
        return "ΚΑΝΟΝΑΣ: το ship_crew δεν τερμάτισε"
    for (name, land, (flags, roles), stale, want), (_, z80, born) in zip(RULE_CASES, got):
        ref = reference(land, flags, roles)
        first = [i for i in range(128) if not flags[i] & 1][:4]
        if ref != want:
            return f"ΚΑΝΟΝΑΣ «{name}»: η αναφορά λέει {ref}, η πρόζα {want}"
        if z80 != want or born != first:
            return (f"ΚΑΝΟΝΑΣ «{name}»: ο Z80 έφερε {z80} στις {born}, η πρόζα λέει "
                    f"{want} στις {first}")
    print(f"    ΚΑΝΟΝΑΣ: {len(RULE_CASES)} αποικίες — " + "; ".join(
        f"{c[0]}: {''.join(NAMES[r][0] for r in c[4])}" for c in RULE_CASES))
    return None


# --------------------------------------------------------------------------
# ΠΛΟΙΟ — όλη η διαδρομή
# --------------------------------------------------------------------------
def voyage(sym, quiet=False):
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G = Game(sym)
    m = G.m
    # Μία αληθινή αίθουσα ελέγχου: ο θόλος 2 γίνεται Control, και το
    # rooms_rebuild τη μετρά — πλοίο που καλείται κανονικά, ταβάνι 4 + 48.
    G.b6[TO.layout()["G_dome_tbl"] - 0x4000 + 24 * VOY_DOME + 3] = R_CONTROL
    m.poke(sym["UI_SPD"], 1)
    m.run_frames(100)
    m.poke(sym["UI_SPD"], 0)
    if m.peek(G.E["CTL"]) != 1 or m.peek(G.EC["EC_POPCAP"]) != 52 or G.pad == 255:
        return (f"ΠΛΟΙΟ: αίθουσες ελέγχου {m.peek(G.E['CTL'])}, ταβάνι "
                f"{m.peek(G.EC['EC_POPCAP'])}, πίστα {G.pad}")
    G.tap("C")
    md = Model(G.land())
    for k in [RIGHT] * 3 + [UP] * 3:                # ο γιατρός στο 50%
        md.key(k)
        G.tap(k)
    if G.land() != md.t or md.t != [1, 1, 1, 5, 2]:
        return f"ΠΛΟΙΟ: τα ποσοστά {G.land()}, όχι {md.t}"
    G.stick(0x10)
    if m.peek(G.E["SHIP"]) == 0:
        return f"ΠΛΟΙΟ: το FIRE δεν κάλεσε πλοίο: «{G.rows()[0]}»"
    m.poke(sym["UI_SPD"], 4)                        # x4
    prev = G.agents()
    for t in range(6000):
        m.run_frames(1)
        if m.peek(G.EC["EC_SHSTATE"]) == SHIP_LANDED:
            break
        prev = G.agents()
    else:
        return "ΠΛΟΙΟ: δεν προσγειώθηκε σε 6.000 frames"
    # Το frame μπορεί να κλείσει στη μέση του ship_crew (128 πράκτορες): η
    # κατάσταση είναι 2 πριν φανούν οι γεννήσεις. Η αποικία του κανόνα είναι
    # το τελευταίο δείγμα πριν από την προσγείωση.
    m.run_frames(4)
    now = G.agents()
    born = [i for i in range(128) if now[0][i] & 1 and not prev[0][i] & 1]
    got = [now[1][i] for i in born]
    want = reference(md.t, *prev)
    if got != want or len(got) != 4:
        return f"ΠΛΟΙΟ: ήρθαν {got}, ο κανόνας λέει {want}"
    say(f"ΠΛΟΙΟ: ποσοστά {[10 * x for x in md.t]} από τα πλήκτρα, προσγείωση μετά από "
        f"{t} frames· η αποικία {[sum(1 for i in range(128) if prev[0][i] & 1 and prev[1][i] == r) for r in range(5)]}, "
        f"ήρθαν {' '.join(NAMES[r] for r in got)} (ταυτότητες {born}) — όπως ο κανόνας")
    return None


# --------------------------------------------------------------------------
# ΚΟΣΤΟΣ — μετρημένο στο βήμα 91: 3.198, 4.386, 6.438 us
# --------------------------------------------------------------------------
# 76, όχι 124 (βήμα 92): οι άποικοι είναι ως 80, και με 124 στις πρώτες θέσεις το
# ship_crew δεν βρίσκει πια θέση και δεν μετρά τίποτα.
COST = ((4, 3400), (48, 4600), (76, 5400))        # (ζωντανοί, ταβάνι σε us)


def cost(sym, patch=()):
    """[(ζωντανοί, us του ship_crew)] σε αποικίες χωρίς κενά, ρόλοι κυκλικά."""
    out = []
    for n, _ in COST:
        G = Game(sym, patch)
        m = G.m
        for i in range(128):
            G.b6[G.ag + i], G.b6[G.ag + 128 + i] = (3 if i < n else 0), i % 5
        m.poke(G.EC["EC_ALIVE"], n)
        m.poke(G.EC["EC_POPCAP"], n + 4)

        def timed(body):
            m.write_ram(PROBE, bytes([0xF3, 0x31, 0x00, 0x01, 0x01, 0xC6, 0x7F, 0xED, 0x49]
                                     + body + [0x3E, 0x5A, 0x32, FLAG & 255, FLAG >> 8,
                                               0x18, 0xFE]))
            m.poke(FLAG, 0)
            m.set_pc(PROBE)
            us = 0
            while m.peek(FLAG) != 0x5A and us < 20000:
                m.run_us(1)
                us += 1
            return us
        base = timed([])
        out.append((n, timed([0xCD, sym["SHIP_CREW"] & 255, sym["SHIP_CREW"] >> 8]) - base))
    return out


def main():
    sym, g = TG.build()

    why = chooser(sym)
    check(why is None, why or "γραμμή: C, βελάκια, ESC, κουμπί, FIRE και SPACE όπως η πρόζα")

    why = rule_check(sym)
    check(why is None, why or "κανόνας: οι τέσσερις κάθε αποικίας όπως η πρόζα και η αναφορά")

    why = voyage(sym)
    check(why is None, why or "πλοίο: από τα πλήκτρα ως την προσγείωση")

    got = cost(sym)
    check(all(us <= top for (n, us), (_, top) in zip(got, COST)),
          "κόστος της προσγείωσης: " + ", ".join(f"{n} ζωντανοί {us} us (ταβάνι {top})"
                                                for (n, us), (_, top) in zip(got, COST)))

    # --- ΑΡΝΗΤΙΚΑ ΤΗΣ ΓΡΑΜΜΗΣ ---
    m = Game(sym).m
    ud, ext = sym["CW_UD"], sym["CW_EXT"]
    call_ext = find(m, ud, ud + 48, [0xCD, ext & 255, ext >> 8])
    ceil = find(m, ud, ud + 48, [0xFE, 0x0A, 0xD0])
    floor = find(m, ud, ud + 48, [0xB7, 0xC8])
    xor = find(m, ext, ext + 24, [0xA9])
    dirty = find(m, sym["CW_DRAW"], sym["CW_DRAW"] + 8,
                 [0xCD, sym["UI_DIRTY"] & 255, sym["UI_DIRTY"] >> 8])
    space = find(m, sym["CW_TICK"], sym["CW_TICK"] + 8, [0xE6, 0x50])
    cw = sym["CW_OPEN"]
    jc = find(m, 0x0100, 0x3D40, [0xC3, cw & 255, cw >> 8]) + \
        find(m, 0x8000, 0xC000, [0xC3, cw & 255, cw >> 8])
    ship = sym["UI_SHIP"]
    ui_negs = (
        ("ΠΑΝΩ χωρίς δότη", call_ext[:1] and [(call_ext[0] + 3, 0)]),
        ("χωρίς ταβάνι στο 100%", ceil and [(ceil[0] + 2, 0)]),
        ("χωρίς πάτωμα στο 0%", floor and [(floor[0] + 1, 0)]),
        ("ο παραλήπτης του ΚΑΤΩ η μεγαλύτερη", xor and [(xor[0], 0)]),
        ("η οθόνη δεν ξαναζωγραφίζεται", dirty and [(dirty[0] + k, 0) for k in range(3)]),
        ("το SPACE δεν καλεί", space and [(space[0] + 1, 0x10)]),
        ("το C καλεί κατευθείαν, όπως ως το 90",
         len(jc) == 1 and [(jc[0] + 1, ship & 255), (jc[0] + 2, ship >> 8)]),
    )
    for label, patch in ui_negs:
        why = patch and chooser(sym, patch, quiet=True)
        check(bool(why), f"ΑΡΝΗΤΙΚΟ γραμμής: με «{label}» " +
              (f"πιάνεται — {why}" if why else "ΔΕΝ πιάνεται (ή δεν βρέθηκε)"))

    # --- ΑΡΝΗΤΙΚΑ ΤΟΥ ΚΑΝΟΝΑ ---
    good = [r for _, r, _ in rules(sym)]
    pk, cn, born = sym["CW_PICK"], sym["CW_COUNT"], sym["SH_BORN"]
    cpick = find(m, born, born + 16, [0xCD, pk & 255, pk >> 8])
    ccount = find(m, sym["SHIP_CREW"], sym["SHIP_CREW"] + 4, [0xCD, cn & 255, cn >> 8])
    tie = find(m, pk, pk + 40, [0x79, 0x93, 0x78, 0x9A, 0x30])     # BC - DE: CY αν d >
    dead = find(m, cn, cn + 48, [0x1F, 0x38])                       # rra · jr c,ζωντανός
    first = find(m, cn, cn + 48, [0xCB, 0x79, 0x28])                # bit 7,c · jr z
    rule_negs = (
        ("ταυτότητα & 7, όπως ως το 90", cpick and [(cpick[0], 0x7D), (cpick[0] + 1, 0xE6),
                                                    (cpick[0] + 2, 0x07)]),
        ("χωρίς cw_count", ccount and [(ccount[0] + k, 0) for k in range(3)]),
        # DE - BC: CY αν d < του καλύτερου, άρα και το ίσο τον αντικαθιστά
        ("η ισοπαλία στον τελευταίο", tie and [(tie[0] + k, v) for k, v in
                                              enumerate([0x7B, 0x91, 0x7A, 0x98, 0x38])]),
        ("μετρούν και οι νεκροί", dead and [(dead[0] + 1, 0x18)]),
        ("ο πρώτος νεκρός είναι ο τελευταίος", first and [(first[0] + 2, 0), (first[0] + 3, 0)]),
    )
    # Χωρίς την πρόωρη έξοδο: το jr z μετά το dec b γίνεται δύο nop.
    early = find(m, cn, cn + 64, [0x05, 0x28])
    slow = early and cost(sym, [(early[0] + 1, 0), (early[0] + 2, 0)])
    check(bool(slow) and slow[0][1] > COST[0][1],
          f"ΑΡΝΗΤΙΚΟ κόστους: χωρίς την πρόωρη έξοδο, 4 ζωντανοί "
          f"{slow and slow[0][1]} us — πάνω από το ταβάνι {COST[0][1]}")
    for label, patch in rule_negs:
        got = patch and rules(sym, patch)
        diff = got and [n for (n, r, _), w in zip(got, good) if r != w]
        check(bool(diff), f"ΑΡΝΗΤΙΚΟ κανόνα: με «{label}» " +
              (f"διαφέρουν: {', '.join(diff)}" if diff else "ΔΕΝ πιάνεται (ή δεν βρέθηκε)"))

    print()
    if FAIL:
        print(f"{len(FAIL)} ΑΠΟΤΥΧΙΕΣ")
        return 1
    print("ΟΛΑ ΟΚ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
