#!/usr/bin/env python3
"""Τα ρομπότ από το απόθεμα Bots (βήμα 92, DESIGN §6.11, §10.2).

Η πρόζα — οι αποφάσεις του παίκτη, και ό,τι ακολουθεί από αυτές:

  ΘΕΣΕΙΣ     οι πράκτορες 0-79 είναι άποικοι και οι 80-95 ρομπότ, τα 80 + 16
             του §6.1.
  ΞΥΠΝΗΜΑ    σε κάθε περιστροφή (θέση 15, πριν από το πλοίο): με ένα Bot στο
             απόθεμα και μια ελεύθερη θέση ρομπότ, ένα ρομπότ ξυπνά στην ΠΡΩΤΗ
             ελεύθερη θέση, στον πρώτο θόλο Factory του ευρετηρίου που έχει
             μηχανή robots σε κάποια από τις οκτώ υποδοχές. Μέσα (F_ALIVE |
             F_INDOORS), με θέση δακτυλιδιού κατά τη σειρά γεμίσματος ή 255, με
             τις μπάρες του νεογέννητου, χωρίς εργασία. Το απόθεμα πέφτει κατά
             ένα. Χωρίς Bot, χωρίς θέση ή χωρίς τέτοιο εργοστάσιο: τίποτα.
  ΡΟΛΟΣ      ζυγή θέση κατασκευής (5), μονή μεταφοράς (6). Κανένα γεωτρύπανο.
             Ο ρόλος, ο κόμβος και η θέση βγαίνουν ίδια και από την αναφορά
             (tools/econ.py, bot_tick).
  ΑΛΥΣΙΔΑ    η μηχανή robots φτιάχνει το Bot από 2 μέταλλο, 1 επεξεργαστή και 1
             βιοπλαστικό, και το ρομπότ ξυπνά στο εργοστάσιό της. Με απόθεμα,
             ένα ανά περιστροφή: 16 frames ανάμεσα σε δύο.
  ΑΝΑΓΚΕΣ    τα ρομπότ δεν τρώνε, δεν πίνουν, δεν κοιμούνται, δεν αναπνέουν:
             οι μπάρες τους δεν κινούνται, δεν πάνε ποτέ για ανάγκη (T_NEED),
             και η ζήτηση οξυγόνου είναι 2 ανά άποικο μέσα, χωρίς αυτά.
  ΤΑΒΑΝΙ     τα ρομπότ δεν μετρούν: το EC_ALIVE και το POP του HUD είναι οι
             άποικοι. Το ταβάνι του Control σταματά στο 80 (ως το 91 στο 128,
             και πάνω από τον 95ο κανείς δεν κινούνταν), και το πλοίο δεν γεννά
             ποτέ σε θέση ρομπότ.
  ΔΟΥΛΕΙΑ    σε νέο παιχνίδι χωρίς μηχανικό, ένα ηλιακό το τροφοδοτεί το
             ρομπότ μεταφοράς και το χτίζει το ρομπότ κατασκευής. Μένουν έξω
             χωρίς στολή και ζουν.
  AUTOMATION οκτώ ζωντανά ρομπότ στην αλλαγή του sol: το bit 3 του EC_MILE.
             Με επτά, όχι.
  ΚΟΣΤΟΣ     το bot_tick χωρίς απόθεμα, με απόθεμα και δεκαέξι ρομπότ, και με
             ξύπνημα στο δεύτερο εργοστάσιο, κάτω από τα ταβάνια COST: 10, 112
             και 715 us μετρημένα, πάνω από ένα σκέτο ship_tick. Το πρώτο το
             πληρώνει η θέση 15 σε κάθε περιστροφή· το δεύτερο όσο η μηχανή
             γεμίζει το απόθεμα και οι θέσεις είναι γεμάτες.

Αρνητικά, με τον κώδικα πειραγμένο στη μνήμη: χωρίς τον έλεγχο του
αποθέματος, χωρίς τη μείωσή του, πάντα κατασκευής, δεκαπέντε θέσεις, μόνο το
πρώτο εργοστάσιο, γεννημένο έξω (ΚΑΝΟΝΑΣ)· οι ανάγκες και στα ρομπότ (ΑΝΑΓΚΕΣ)·
ο μετρητής ζωντανών στις 128 θέσεις (ΑΝΑΓΚΕΣ)· το ταβάνι στο 128 και το
πλοίο που γεννά στις θέσεις ρομπότ όπως ως το 91 (ΤΑΒΑΝΙ)· το Automation με
F_WORKING όπως ως το 91 (AUTOMATION).
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import test_act as TA                                    # noqa: E402
import test_outside as TO                                # noqa: E402
import test_supply as TS                                 # noqa: E402
import balance as B                                      # noqa: E402
import econ as EC                                        # noqa: E402
import entity as E                                       # noqa: E402

FAIL = []
PROBE, FLAG = 0x3E00, 0x3EFF
BOT0, NBOT = EC.AG_BOT0, EC.AG_NBOT
CBOT, CARRY = EC.RL_CBOT, EC.RL_CARRY
R_FACTORY, R_CONTROL = EC.R_FACTORY, EC.R_CONTROL
T_NEED, MB_AUTOMAT = 254, 3
NEWBORN = dict(task=255, edge=255, progress=0, o2=200, water=200, food=200, sleep=200,
               health=200, morale=160, suit=EC.SUIT_TRIP, spare=0)
NEEDS = ("o2", "water", "food", "sleep", "health")


def check(ok, msg):
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ ") + msg)
    if not ok:
        FAIL.append(msg)


def econ_at():
    g = TO.layout()["G_econ_state"]
    const = open(os.path.join(ROOT, "src", "const.asm"), encoding="utf-8").read()
    out = {"EC_STOCK": g}
    for n in ("EC_ALIVE", "EC_POPCAP", "EC_MILE", "EC_SOLLEN", "EC_FRAME", "EC_O2USE",
              "EC_PADNODE"):
        out[n] = g + int(re.search(rf"^{n}\s+equ G_econ_state \+ (\d+)", const, re.M).group(1))
    return out


class Game(TA.Game):
    """Το colony.sna σε παύση: τρεις μικροί θόλοι (οξυγόνο, κοιτώνες, κυλικείο),
    τέσσερις άποικοι. Τα patch6 πειράζουν τον κώδικα της τράπεζας 6."""

    def __init__(self, sym, patch=(), patch6=()):
        super().__init__(sym, patch)
        self.L, self.EC = TO.layout(), econ_at()
        self.ag = self.L["G_agent_fields"] - 0x4000
        self.dome = self.L["G_dome_tbl"] - 0x4000
        self.occ = self.L["G_node_occ"] - 0x4000
        for at, v in patch6:
            self.b6[at - 0x4000] = v

    def w16(self, at):
        return self.m.peek(at) | self.m.peek(at + 1) << 8

    def s16(self, at, v):
        self.m.poke(at, v & 255)
        self.m.poke(at + 1, v >> 8)

    def bots(self):
        return self.w16(self.EC["EC_STOCK"] + 2 * EC.S_BOT)

    def set_bots(self, n):
        self.s16(self.EC["EC_STOCK"] + 2 * EC.S_BOT, n)

    def agent(self, i):
        a = E.Agents().from_bytes(bytes(self.b6[self.ag:self.ag + 2048]))
        return {f: getattr(a, f)[i] for f in E.FIELDS}

    def alive(self, lo, hi):
        return [i for i in range(lo, hi) if self.b6[self.ag + i] & 1]

    def factory(self, d, size=0, robots_at=None):
        b = self.dome + 24 * d
        self.b6[b + 2], self.b6[b + 3] = size, R_FACTORY
        for k in range(8):
            self.b6[b + 8 + k] = 255
            self.b6[b + 16 + k] = 0
        if robots_at is not None:
            self.b6[b + 8 + robots_at], self.b6[b + 16 + robots_at] = EC.M_ROBOTS, 200

    def index(self, factories):
        """Το ευρετήριο δωματίων όπως θα το έγραφε η θέση 14."""
        self.m.poke(self.L["G_room_n"] + R_FACTORY, len(factories))
        for k, d in enumerate(factories):
            self.m.poke(self.L["G_room_list"] + R_FACTORY * EC.ROOM_MAX + k, d)

    def probe(self, body, timed=False):
        m = self.m
        code = ([0xF3, 0x31, 0x00, 0x01, 0x01, 0xC6, 0x7F, 0xED, 0x49] + body   # τράπεζα 6
                + [0x3E, 0x5A, 0x32, FLAG & 255, FLAG >> 8, 0x18, 0xFE])
        m.write_ram(PROBE, bytes(code))
        m.poke(FLAG, 0)
        m.set_pc(PROBE)
        us = 0
        step = 1 if timed else 100
        while m.peek(FLAG) != 0x5A and us < 200000:
            m.run_us(step)
            us += step
        return us if m.peek(FLAG) == 0x5A else None

    def call(self, name, timed=False):
        a = self.sym[name]
        return self.probe([0xCD, a & 255, a >> 8], timed)


# --------------------------------------------------------------------------
# ΚΑΝΟΝΑΣ — (όνομα, απόθεμα, εργοστάσια [(θόλος, μέγεθος, υποδοχή robots)],
# ζωντανές θέσεις ρομπότ, πιασμένο δακτυλίδι του εργοστασίου, τι λέει η
# πρόζα: (ταυτότητα, ρόλος, θόλος) ή None)
# --------------------------------------------------------------------------
ALL = range(BOT0, BOT0 + NBOT)
RULE_CASES = (
    ("απόθεμα 0", 0, [(1, 0, 0)], [], 0, None),
    ("απόθεμα, κανένα εργοστάσιο", 3, [], [], 0, None),
    ("εργοστάσιο χωρίς μηχανή robots", 3, [(1, 0, None)], [], 0, None),
    ("η μηχανή στο δεύτερο εργοστάσιο, υποδοχή 7", 3, [(1, 0, None), (2, 2, 7)], [], 0,
     (80, CBOT, 2)),
    ("80-84 ζωντανά: το 85 μεταφοράς", 2, [(1, 0, 0)], range(80, 85), 0, (85, CARRY, 1)),
    ("μόνο το 95 ελεύθερο", 1, [(1, 0, 0)], range(80, 95), 0, (95, CARRY, 1)),
    ("δεκαέξι ρομπότ", 9, [(1, 0, 0)], ALL, 0, None),
    ("απόθεμα 256", 256, [(1, 0, 0)], [], 0, (80, CBOT, 1)),
    ("γεμάτο δακτυλίδι", 1, [(2, 0, 0)], [81, 83], 0xFF, (80, CBOT, 2)),
)


def setup_rule(G, stock, facs, alive, ring):
    for i in ALL:
        G.b6[G.ag + i], G.b6[G.ag + 128 + i] = (1 if i in alive else 0), CBOT + (i & 1)
    for d in range(3):                               # οι τρεις θόλοι: όχι εργοστάσια
        G.b6[G.dome + 24 * d + 3] = (EC.R_OXYGEN, EC.R_QUARTERS, EC.R_CANTEEN)[d]
    for d, size, at in facs:
        G.factory(d, size, at)
        G.b6[G.occ + d] = ring
    G.index([d for d, _, _ in facs])
    G.set_bots(stock)


def reference(G):
    """Η ίδια κατάσταση στην αναφορά, και τι κάνει το bot_tick εκεί."""
    e = EC.Econ()
    e.stock[EC.S_BOT] = G.bots()
    e.dome = bytearray(G.b6[G.dome:G.dome + 64 * 24])
    e.room_n = bytearray(G.m.read_ram(G.L["G_room_n"], 12))
    e.room_list = bytearray(G.m.read_ram(G.L["G_room_list"], 96))
    a = E.Agents().from_bytes(bytes(G.b6[G.ag:G.ag + 2048]))
    occ = bytearray(G.b6[G.occ:G.occ + 128])
    EC.bot_tick(e, a, occ)
    return a.to_bytes(), e.stock[EC.S_BOT], bytes(occ)


def rules(sym, patch=(), patch6=(), quiet=False):
    """ΚΑΝΟΝΑΣ. Η πρώτη διαφορά, ή None."""
    G = Game(sym, patch, patch6)
    for name, stock, facs, alive, ring, want in RULE_CASES:
        setup_rule(G, stock, facs, alive, ring)
        before = bytes(G.b6[G.ag:G.ag + 2048])
        ref = reference(G)
        if G.call("BOT_TICK") is None:
            return f"ΚΑΝΟΝΑΣ «{name}»: το bot_tick δεν τερμάτισε"
        got = (bytes(G.b6[G.ag:G.ag + 2048]), G.bots(), bytes(G.b6[G.occ:G.occ + 128]))
        born = [i for i in ALL if G.b6[G.ag + i] & 1 and not before[i] & 1]
        if want is None:
            if born or got[1] != stock or got[0] != before:
                return f"ΚΑΝΟΝΑΣ «{name}»: γεννήθηκαν {born}, απόθεμα {stock} -> {got[1]} — η πρόζα λέει τίποτα"
        else:
            i, role, d = want
            a = G.agent(i)
            slot = next((t for t in (0, 4, 2, 6, 1, 5, 3, 7) if not (ring >> t) & 1), 255)
            bad = {k: a[k] for k, v in NEWBORN.items() if a[k] != v}
            if (born != [i] or a["flags"] != 3 or a["role"] != role or a["node"] != d
                    or a["dest"] != d or a["slot"] != slot or bad or got[1] != stock - 1):
                return (f"ΚΑΝΟΝΑΣ «{name}»: γεννήθηκαν {born}, {a}, απόθεμα {stock} -> "
                        f"{got[1]} — η πρόζα λέει {i}, ρόλος {role}, θόλος {d}, θέση {slot}, "
                        f"μέσα, απόθεμα {stock - 1}")
        if got != ref:
            return f"ΚΑΝΟΝΑΣ «{name}»: ο Z80 διαφέρει από την αναφορά"
    if not quiet:
        print(f"    ΚΑΝΟΝΑΣ: {len(RULE_CASES)} καταστάσεις — " + "; ".join(
            f"{c[0]}: {'τίποτα' if c[5] is None else f'{c[5][0]} ' + ('Κ' if c[5][1] == CBOT else 'Μ')}"
            for c in RULE_CASES))
    return None


# --------------------------------------------------------------------------
# ΑΛΥΣΙΔΑ, ΑΝΑΓΚΕΣ, ΤΑΒΑΝΙ του POP — η αποικία τρέχει
# --------------------------------------------------------------------------
FAC = 1                                             # ο θόλος 1 γίνεται εργοστάσιο


def chain(sym, patch=(), patch6=(), quiet=False):
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G = Game(sym, patch, patch6)
    m, st = G.m, G.EC["EC_STOCK"]
    G.factory(FAC, 0, 0)
    for k in (EC.S_METAL, EC.S_BIOPL, EC.S_PROC):
        G.s16(st + 2 * k, 100)
    G.set_bots(0)
    m.poke(G.sym["UI_SPD"], 1)
    for t in range(0, 4000, 16):
        m.run_frames(16)
        if G.alive(BOT0, BOT0 + NBOT):
            break
    else:
        return "ΑΛΥΣΙΔΑ: κανένα ρομπότ σε 4.000 frames"
    used = [100 - G.w16(st + 2 * k) for k in (EC.S_METAL, EC.S_PROC, EC.S_BIOPL)]
    made = len(G.alive(BOT0, BOT0 + NBOT)) + G.bots()
    a = G.agent(80)
    if used != [2 * made, made, made] or a["role"] != CBOT or a["node"] != FAC or a["flags"] != 3:
        return (f"ΑΛΥΣΙΔΑ: ξόδεψε {used} (μέταλλο, επεξεργαστές, βιοπλαστικό) για {made} Bots, "
                f"το 80 είναι {a}")
    say(f"ΑΛΥΣΙΔΑ: η μηχανή robots έφτιαξε {made} Bot με {used[0]} μέταλλο, {used[1]} "
        f"επεξεργαστή, {used[2]} βιοπλαστικό· το 80 ξύπνησε στο εργοστάσιο, κατασκευής, μέσα, "
        f"σε {t + 16} frames")
    # --- ένα ανά περιστροφή ---
    G.set_bots(5)
    seen, t = {}, 0
    while len(seen) < 5 and t < 400:
        m.run_frames(1)
        t += 1
        for i in G.alive(81, BOT0 + NBOT):
            seen.setdefault(i, t)
    order = sorted(seen, key=seen.get)
    gaps = [seen[b] - seen[a] for a, b in zip(order, order[1:])]
    roles = [G.agent(i)["role"] for i in order]
    if order != [81, 82, 83, 84, 85] or gaps != [16] * 4 or roles != [CARRY, CBOT] * 2 + [CARRY]:
        return f"ΡΥΘΜΟΣ: ξύπνησαν {order} με ρόλους {roles}, ανάμεσα {gaps} frames"
    say(f"ΡΥΘΜΟΣ: με απόθεμα 5, τα 81-85 ένα ανά 16 frames, μεταφοράς και κατασκευής εναλλάξ")
    return needs(G, say)


def needs(G, say):
    m = G.m
    bots = G.alive(BOT0, BOT0 + NBOT)
    hum = G.alive(0, BOT0)
    a0 = {i: G.agent(i) for i in bots + hum}
    sought, t = set(), 0
    while t < 3000:
        m.run_frames(50)
        t += 50
        sought |= {i for i in bots if G.agent(i)["task"] == T_NEED}
    moved = [i for i in bots if any(G.agent(i)[k] != a0[i][k] for k in NEEDS)]
    hungry = [i for i in hum if any(G.agent(i)[k] < a0[i][k] for k in NEEDS)]
    if moved or sought or not hungry:
        return (f"ΑΝΑΓΚΕΣ: σε {t} frames άλλαξαν οι μπάρες των ρομπότ {moved}, πήγαν για ανάγκη "
                f"{sorted(sought)}, πείνασαν οι άποικοι {hungry}")
    # Το POP του HUD όπως το γράφει το παιχνίδι που τρέχει, και μετά το
    # EC_ALIVE και η ζήτηση οξυγόνου από ΤΗΝ ΙΔΙΑ στιγμή: σε παύση, η θέση 12
    # (econ_flow) καλείται μία φορά με τις σημαίες που φαίνονται τώρα.
    m.poke(G.sym["UI_SPD"], 0)
    m.run_frames(20)
    pop = TA.TI.same(G.hud(2))[:7]
    alive = G.alive(0, BOT0)
    inside = [i for i in alive if G.b6[G.ag + i] & 2]
    if G.call("ECON_FLOW") is None:
        return "ΤΑΒΑΝΙ: το econ_flow δεν τερμάτισε"
    if (m.peek(G.EC["EC_ALIVE"]) != len(alive) or G.w16(G.EC["EC_O2USE"]) != 2 * len(inside)
            or pop != TA.TI.same(f"POP {len(alive):2d}/")):
        return (f"ΤΑΒΑΝΙ: EC_ALIVE {m.peek(G.EC['EC_ALIVE'])}, ζήτηση οξυγόνου "
                f"{G.w16(G.EC['EC_O2USE'])}, «{pop}» — άποικοι {len(alive)}, μέσα {len(inside)}, "
                f"ρομπότ {len(G.alive(BOT0, BOT0 + NBOT))}")
    say(f"ΑΝΑΓΚΕΣ: {len(bots)} ρομπότ, {t} frames — καμία μπάρα τους δεν κινήθηκε, κανένα δεν "
        f"πήγε για ανάγκη, ενώ οι {len(hungry)} άποικοι πείνασαν· EC_ALIVE {len(alive)}, "
        f"ζήτηση οξυγόνου {2 * len(inside)}, «{G.hud(2)[:8]}»")
    return None


# --------------------------------------------------------------------------
# ΤΑΒΑΝΙ — τρεις αίθουσες ελέγχου, και ένα πλοίο με τις 80 θέσεις γεμάτες
# --------------------------------------------------------------------------
def cap(sym, patch=(), patch6=(), quiet=False):
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G = Game(sym, patch, patch6)
    m = G.m
    for d in range(3):
        G.b6[G.dome + 24 * d + 3] = R_CONTROL
    m.poke(G.sym["UI_SPD"], 1)
    m.run_frames(40)
    m.poke(G.sym["UI_SPD"], 0)
    m.run_frames(4)
    if m.peek(G.EC["EC_POPCAP"]) != 80:
        return f"ΤΑΒΑΝΙ: με τρεις αίθουσες ελέγχου το ταβάνι είναι {m.peek(G.EC['EC_POPCAP'])}, όχι 80"
    # Οι 80 θέσεις αποίκων ζωντανές, οι θέσεις ρομπότ άδειες, και ένα ταβάνι
    # που (με το χέρι) θα χωρούσε τέσσερις ακόμη: κανείς δεν γεννιέται.
    for i in range(128):
        G.b6[G.ag + i] = 3 if i < BOT0 else 0
    m.poke(G.EC["EC_ALIVE"], BOT0)
    m.poke(G.EC["EC_POPCAP"], BOT0 + 4)
    if G.call("SHIP_CREW") is None:
        return "ΤΑΒΑΝΙ: το ship_crew δεν τερμάτισε"
    born = G.alive(BOT0, 128)
    if born:
        return f"ΤΑΒΑΝΙ: με τις 80 θέσεις γεμάτες το πλοίο γέννησε στις {born}"
    say("ΤΑΒΑΝΙ: τρεις αίθουσες ελέγχου, ταβάνι 80 (ως το 91: 128)· με τις 80 θέσεις αποίκων "
        "γεμάτες και ταβάνι 84 με το χέρι, το πλοίο δεν γεννά στις θέσεις ρομπότ")
    return None


# --------------------------------------------------------------------------
# ΔΟΥΛΕΙΑ — νέο παιχνίδι, χωρίς μηχανικό, δύο ρομπότ στο σκάφος
# --------------------------------------------------------------------------
def work(sym, g, patch=(), quiet=False):
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    w = TS.W(sym, g, patch)
    m = w.m
    AGF = w.L["G_agent_fields"]
    w.put6(AGF + 128 + TS.ENGINEER, [0])            # ο μηχανικός γίνεται εργάτης
    # Τα δύο ρομπότ με τα bytes που γράφει το bot_tick, στο σκάφος (κόμβος 64),
    # έξω: η γέννηση ελέγχεται στον ΚΑΝΟΝΑ, εδώ η δουλειά.
    for i, role in ((80, CBOT), (81, CARRY)):
        for k, f in enumerate(E.FIELDS):
            v = {"flags": 1, "role": role, "node": TS.SHIP, "slot": 255, "dest": TS.SHIP,
                 "edge": 255, "progress": 0, "task": 255, "morale": 160,
                 "suit": EC.SUIT_TRIP, "spare": 0}.get(f, 200)
            w.put6(AGF + 128 * k + i, [v])
    B.build(m, sym, 4, g + 6, at=TS.SOLAR_AT, fit=False)
    takers, t = set(), 0
    while t < 6000 and w.struct(1)[4] != TS.DS_ACTIVE:
        m.run_frames(5)
        t += 5
        takers |= {(j[0], j[2]) for j in w.jobs() if j[2] != 255}
    alive = [w.agent(i)["f"] & 1 for i in (80, 81)]
    supply = {a for k, a in takers if k == TS.J_SUPPLY}
    build = {a for k, a in takers if k == TS.J_BUILD}
    if w.struct(1)[4] != TS.DS_ACTIVE or 81 not in supply or build != {80} or alive != [1, 1]:
        return (f"ΔΟΥΛΕΙΑ: σε {t} frames το ηλιακό {w.struct(1)}, Supply από {sorted(supply)}, "
                f"Build από {sorted(build)}, ζωντανά {alive}")
    m.run_frames(3000)
    if [w.agent(i)["f"] & 1 for i in (80, 81)] != [1, 1]:
        return "ΔΟΥΛΕΙΑ: τα ρομπότ πέθαναν έξω"
    say(f"ΔΟΥΛΕΙΑ: χωρίς μηχανικό, το ηλιακό το τροφοδότησε το 81 (μεταφοράς) και το "
        f"έχτισε το 80 (κατασκευής) σε {t} frames· 3.000 frames αργότερα έξω, και τα δύο ζουν")
    return None


# --------------------------------------------------------------------------
# AUTOMATION — οκτώ ζωντανά ρομπότ στην αλλαγή του sol, και επτά
# --------------------------------------------------------------------------
def automation(sym, n, patch=(), patch6=()):
    """Το bit του Automation μετά από sols με n ρομπότ από το απόθεμα."""
    G = Game(sym, patch, patch6)
    m = G.m
    G.factory(FAC, 0, 0)
    G.s16(G.EC["EC_STOCK"] + 2 * EC.S_PROC, 0)      # χωρίς επεξεργαστές: κανένα Bot ακόμη
    G.set_bots(n)
    m.poke(G.EC["EC_MILE"], 0)
    G.s16(G.EC["EC_SOLLEN"], 320)
    G.s16(G.EC["EC_FRAME"], 0)
    m.poke(G.sym["UI_SPD"], 1)
    m.run_frames(320 * 3)
    return (m.peek(G.EC["EC_MILE"]) >> MB_AUTOMAT) & 1, len(G.alive(BOT0, BOT0 + NBOT))


def auto_check(sym, patch=(), patch6=(), quiet=False):
    got8, got7 = automation(sym, 8, patch, patch6), automation(sym, 7, patch, patch6)
    if got8 != (1, 8) or got7 != (0, 7):
        return f"AUTOMATION: με 8 ρομπότ {got8}, με 7 {got7} — (bit, ρομπότ)"
    if not quiet:
        print("    AUTOMATION: οκτώ ρομπότ από το απόθεμα, και το επόμενο sol έδωσε το bit 3· "
              "με επτά όχι")
    return None


# --------------------------------------------------------------------------
# ΚΟΣΤΟΣ — μετρημένο στο βήμα 92
# --------------------------------------------------------------------------
# Μετρημένα στο βήμα 92: 10, 112 και 715 us πάνω από το ship_tick. Με call /
# ret από το econ_events το πρώτο ήταν 16, και με τον βρόχο djnz στις δεκαέξι
# θέσεις, πριν ξετυλιχτεί, το δεύτερο 181 (μαζί με την κλήση). Από το βήμα 111
# κάθε έξοδος περνά από την πόρτα των εισβολέων (fo_tick: ld a,(fo_n) / or a /
# jp z,ship_tick), 8 us: 18, 120 και 741 μετρημένα, και τα ταβάνια +8.
COST = (("χωρίς απόθεμα", 0, [(1, 0, 0)], [], 19),
        ("απόθεμα και δεκαέξι ρομπότ", 5, [(1, 0, 0)], ALL, 128),
        ("ξύπνημα στο δεύτερο εργοστάσιο", 5, [(1, 0, None), (2, 2, 7)], [], 780))


def cost(sym):
    """Ο,τι προσθέτουν τα ρομπότ στη θέση 15: το bot_tick καταλήγει στο
    ship_tick, οπότε μετριέται η διαφορά από ένα σκέτο ship_tick (χωρίς πλοίο)."""
    out = []
    for name, stock, facs, alive, _ in COST:
        G = Game(sym)
        setup_rule(G, stock, facs, alive, 0)
        base = G.call("SHIP_TICK", timed=True)
        out.append(G.call("BOT_TICK", timed=True) - base)
    return out


# --------------------------------------------------------------------------
# ΑΡΝΗΤΙΚΑ
# --------------------------------------------------------------------------
def find(data, lo, pat):
    return [lo + k for k in range(len(data) - len(pat) + 1) if list(data[k:k + len(pat)]) == pat]


def negatives(sym):
    """[(όνομα, αλλαγές, στην τράπεζα 6;, ποια δοκιμή το πιάνει)]: το σημείο
    ψάχνεται στη μνήμη, και πρέπει να βρεθεί ακριβώς μία φορά."""
    G = Game(sym)
    m = G.m
    # Μόνο ο κώδικας των ρομπότ: από το βήμα 93 στην ίδια δέσμευση ζουν και τα
    # πλοία και το μέτρημα των ειδικοτήτων (src/ship.asm, src/crew.asm).
    b6 = bytes(G.b6[sym["BOT_TICK"] - 0x4000:sym["BOT_END"] - 0x4000])
    ram = lambda name, n, pat: find(m.read_ram(sym[name], n), sym[name], pat)
    out = []

    def six(label, pat, k, v, test):
        at = find(b6, sym["BOT_TICK"], pat)
        out.append((label, [(at[0] + k, v)] if len(at) == 1 else None, True, test))

    def zero(label, name, n, pat, edits, test):
        at = ram(name, n, pat)
        out.append((label, [(at[0] + k, v) for k, v in edits] if len(at) == 1 else None,
                    False, test))

    def bank6(label, name, n, pat, edits, test):
        # ό,τι ζει στη δέσμευση b6code από το βήμα 93: το ship_crew και το
        # sol_rollover ήταν στην τράπεζα 0
        lo = sym[name] - 0x4000
        at = find(bytes(G.b6[lo:lo + n]), sym[name], pat)
        out.append((label, [(at[0] + k, v) for k, v in edits] if len(at) == 1 else None,
                    True, test))
    at = find(b6, sym["BOT_TICK"], [0x7C, 0xB5, 0xCA])     # or l / jp z,ship_tick
    out.append(("χωρίς τον έλεγχο του αποθέματος",
                [(at[0] + k, 0) for k in (2, 3, 4)] if len(at) == 1 else None, True, "rules"))
    six("χωρίς τη μείωση του αποθέματος", [0x2B, 0x22], 0, 0, "rules")
    six("πάντα κατασκευής", [0xE6, 0x01, 0xC6, CBOT], 1, 0, "rules")
    # η δέκατη έκτη θέση: το τελευταίο bit 0,(hl) γίνεται bit 0,(hl) πάνω στην
    # ίδια τη 94 — dec l πριν από αυτό, στη θέση του inc l
    at = find(b6, sym["BOT_TICK"], [0x2C, 0xCB, 0x46, 0x28])
    out.append(("δεκαπέντε θέσεις", [(at[-1], 0x2D)] if len(at) == NBOT - 1 else None,
                True, "rules"))
    six("γεννημένο έξω", [0x36, 3], 1, 1, "rules")                # ld (hl),F_ALIVE
    at = find(b6, sym["BOT_TICK"], [0x1C, 0x10])      # inc e / djnz bt_flp
    out.append(("μόνο το πρώτο εργοστάσιο",
                [(at[0] + 1, 0), (at[0] + 2, 0)] if len(at) == 1 else None, True, "rules"))
    # οι ανάγκες στο b6code από το βήμα 110 (src/main.asm)
    bank6("οι ανάγκες και στα ρομπότ", "ENT_NEEDS_SLICE", 8, [0xFE, BOT0, 0xD0],
          [(1, 0xFF)], "chain")
    zero("ο μετρητής ζωντανών στις 128", "EN_COUNT", 12, [0x01, 0x00, BOT0 // 8],
         [(2, 16)], "chain")
    # cp 81 / jr c,+2 / ld a,80 στο rooms_rebuild· ως το 91 cp 129 και 128
    bank6("ταβάνι 128", "ROOMS_REBUILD", 160, [0xFE, BOT0 + 1, 0x38, 0x02, 0x3E, BOT0],
          [(1, 129), (5, 128)], "cap")
    bank6("το πλοίο γεννά στις θέσεις ρομπότ", "SHIP_CREW", 12, [0xD6, BOT0, 0xD0],
          [(1, 128), (2, 0xC8)], "cap")
    bank6("Automation με F_WORKING", "SOL_ROLLOVER", 200, [0xE6, 0x01, 0x81], [(1, 0x20)],
          "auto")
    return out


def main():
    sym, g = TG.build()

    why = rules(sym)
    check(why is None, why or "κανόνας: κάθε κατάσταση όπως η πρόζα και η αναφορά")

    why = chain(sym)
    check(why is None, why or "αλυσίδα, ρυθμός, ανάγκες και POP: από τη μηχανή ως το ρομπότ")

    why = cap(sym)
    check(why is None, why or "ταβάνι: 80, και το πλοίο έξω από τις θέσεις ρομπότ")

    why = work(sym, g)
    check(why is None, why or "δουλειά: Supply από το ρομπότ μεταφοράς, Build από το ρομπότ κατασκευής")

    why = auto_check(sym)
    check(why is None, why or "Automation: οκτώ ζωντανά ρομπότ")

    got = cost(sym)
    check(all(us <= c[4] for us, c in zip(got, COST)),
          "κόστος του bot_tick: " + ", ".join(f"{c[0]} {us} us (ταβάνι {c[4]})"
                                             for us, c in zip(got, COST)))

    run = {"rules": rules, "chain": chain, "cap": cap, "auto": auto_check}
    for label, edits, in6, test in negatives(sym):
        if edits is None:
            check(False, f"ΑΡΝΗΤΙΚΟ «{label}»: το σημείο δεν βρέθηκε ακριβώς μία φορά")
            continue
        kw = {"patch6": edits} if in6 else {"patch": edits}
        why = run[test](sym, quiet=True, **kw)
        check(why is not None, f"ΑΡΝΗΤΙΚΟ «{label}»: " + (why or "πέρασε — η δοκιμή δεν το βλέπει"))

    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
