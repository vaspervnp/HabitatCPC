#!/usr/bin/env python3
"""ΕΠΙΣΚΕΠΤΕΣ ΠΟΥ ΠΕΡΠΑΤΟΥΝ ΚΑΙ ΠΛΗΡΩΝΟΥΝ, ΚΑΙ ΤΟ ΚΥΡΟΣ (βήματα 134 και 136,
DESIGN §6.11).

Η αναφορά (tools/entity.py: visit_tick· tools/econ.py: land_visitors,
sol_rollover) και ο Z80 στις άκρες τους είναι στο tests/test_sim.py:
κυλικείο, σαλόνι, δέντρα, τρόφιμο, νερό, δύο ως πέντε επισκέπτες, το ταβάνι
των νομισμάτων, η εύνοια, ο συσσωρευτής, το μισό sol. Εδώ το παιχνίδι, στο
colony.sna, που τρέχει:

  ΠΕΡΠΑΤΟΥΝ   ένα πλοίο επισκεπτών: δύο επισκέπτες στην πίστα (οι 112 και 113,
              ρόλος 9, T_VISIT, φάση VP_EAT), χωρίς νομίσματα ακόμη. Εξω στη
              λίστα των φιγούρων με το FC_VISITOR, ολόκληροι στην οθόνη·
              στο κυλικείο μέσα, στον δακτύλιό του (DOME_FIG = FC_VISITOR).
              Εκεί πληρώνουν πέντε ο καθένας, η εύνοια +6, και η σειρά 1 του
              HUD γράφει «$ 10». ΑΝΑΠΝΕΟΥΝ: όσο είναι μέσα, EC_VIN = όσοι είναι
              μέσα.
              ΚΑΘΟΝΤΑΙ τουλάχιστον VIS_STAY περιστροφές στο κυλικείο, γυρίζουν
              στην πίστα, ανεβαίνουν, και το πλοίο φεύγει μόλις ανέβει και ο
              δεύτερος — πολύ πριν από το μισό sol. Και το EC_VIN ξανά 0.
  ΣΑΛΟΝΙ      με τον θόλο 1 σαλόνι: πέντε στο κυλικείο, και τρία ακόμη ο
              καθένας στο σαλόνι, όπου πάνε μετά: 10 και μετά 16.
  ΟΞΥΓΟΝΟ     με EC_VIN 3 το ef_o2 βγάζει ζήτηση 2 x (άποικοι μέσα + 3).
  ΚΥΡΟΣ       στο τέλος του sol, στο παιχνίδι που τρέχει: το κύρος είναι ο τύπος
              της πρόζας από τα bytes του ίδιου του παιχνιδιού, και με τον
              συσσωρευτή στο 250 έρχεται πλοίο επισκεπτών — που προσγειώνεται,
              και οι επισκέπτες του πληρώνουν στο κυλικείο.
  ΠΛΗΡΗΣ      με επισκέπτες έξω, μια πλήρης σχεδίαση (view_draw) από άδεια λίστα
              τους ξαναβάζει: το fg_build φτάνει στους 112-119 (βήμα 136).
  ΣΒΗΣΙΜΟ     το HUD γράφει τα νομίσματα μόνο όταν άλλαξαν (hud_cw)· όταν οι
              λωρίδες σβήνουν (hud_inval: άλμα κάμερας, βοήθεια, δίσκος) τα
              ξαναγράφει, ίδια κι ας είναι: το hud_inval κάνει το hud_cw -1.
  ΑΛΜΑ        τα νομίσματα, το κύρος, η εύνοια, ο συσσωρευτής, τα νομίσματα του
              εμπόρου και οι ώρες ηρεμίας του βήματος 121 (τα 12 bytes του
              EC_X), το EC_VIN και το EC_TU, μένουν ίδια σε ένα view_draw —
              άλμα κάμερας, βοήθεια, φόρτωμα. Ως το βήμα 133 το fg_build τα
              μηδένιζε (σημάδια των πρακτόρων 100-127· από το 172 στο node_occ,
              μετά τον χάρτη των εισβολέων, και τα σημάδια σελίδα τους).
  ΚΟΣΤΟΣ      η προσγείωση πέντε επισκεπτών, η περιστροφή όπου αποφασίζουν και
              οι πέντε, η περιστροφή όπου ξεκινούν, το πλοίο που φεύγει με
              πέντε ακόμη έξω, το τέλος του sol με το κύρος και το πλοίο του, και
              το HUD με τα ίδια νομίσματα (το συνηθισμένο) και με νέα.

Αρνητικά: η πληρωμή που δεν γράφεται, το HUD που διαβάζει μηδέν, ο
συσσωρευτής που δεν φέρνει πλοίο, το HUD που δεν βλέπει το σβήσιμο, το
καθάρισμα της κρυφής μνήμης φιγούρων στη σελίδα του node_occ (το ΑΛΜΑ· ως το
βήμα 171 το fg_build σε όλους τους 128 πράκτορες) — και του βήματος 136: το
fg_build χωρίς τους επισκέπτες (η ΠΛΗΡΗΣ), ο επισκέπτης με τη φιγούρα του
αποίκου, επισκέπτες που δεν μετριούνται μέσα, οξυγόνο χωρίς αυτούς, που δεν
κάθονται, που δεν ανεβαίνουν.
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/vasilhs/cpcemu")

import test_game as TG                                     # noqa: E402
import test_trade as TT                                    # noqa: E402
import test_outside as TO                                  # noqa: E402
import test_intruder as TI                                 # noqa: E402
import hudread                                             # noqa: E402
import econ as EC                                          # noqa: E402
import entity as E                                         # noqa: E402
import pack                                                # noqa: E402

FAIL = []
SK_VISITOR, SK_COLONIST = 2, 0
PAD, CANTEEN, LOUNGE = TI.PAD, TI.CANTEEN, 1             # src/colony.asm
FC_VISITOR = pack.fig_code(pack.FIG_ALL.index(pack.VIS_FIG))
FC_COLONIST = pack.fig_code(pack.FIG_ALL.index("colonist"))
VIS = range(EC.AG_VIS0, EC.AG_VIS0 + EC.AG_NVIS)
# Μετρημένα στο βήμα 136, και λίγο πάνω. Στο βήμα 134 η προσγείωση πέντε
# επισκεπτών, που έτρωγαν και πλήρωναν εκεί, ήταν 1.689 us, το τέλος του sol
# 472 και το HUD 8.810 (DESIGN §6.11).
COST = {"προσγείωση, πέντε": 3600, "περιστροφή, πέντε αποφασίζουν": 1700,
        "περιστροφή, πέντε ξεκινούν": 1700, "φεύγει, με πέντε έξω": 1600,
        "τέλος του sol, με πλοίο": 500, "HUD, τα ίδια $998": 8900, "HUD, 998 -> $999": 9600}


def check(ok, msg):
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ ") + msg)
    if not ok:
        FAIL.append(msg)


def addrs():
    """Οι διευθύνσεις του src/const.asm που θέλει η δοκιμή: της οικονομίας στην
    τράπεζα 2, και του EC_X και του EC_VIN στην 6."""
    L = TO.layout()
    g, occ = L["G_econ_state"], L["G_node_occ"]
    const = open(os.path.join(ROOT, "src", "const.asm"), encoding="utf-8").read()
    out = {}
    for n in ("EC_STOCK", "EC_SHETA", "EC_SHSTATE", "EC_SHKIND", "EC_AMENITY", "EC_ALIVE",
              "EC_MILE", "EC_NODEATH", "EC_FRAME", "EC_SOLLEN", "EC_SOL", "EC_LANDS",
              "EC_O2USE"):
        mm = re.search(rf"^{n}\s+equ G_econ_state(?: \+ (\d+))?", const, re.M)
        out[n] = g + int(mm.group(1) or 0)
    x = occ + EC.X_OFF                                       # EC_X (βήμα 172: μετά τον χάρτη των εισβολέων)
    for n, k in (("EC_COINS", 6), ("EC_PREST", 8), ("EC_GOOD", 9), ("EC_VISACC", 10)):
        mm = re.search(rf"^{n}\s+equ EC_X \+ (\d+)", const, re.M)
        assert mm and int(mm.group(1)) == k, f"{n}: το src/const.asm άλλαξε"
        out[n] = x + k
    assert re.search(r"^EC_VIN\s+equ EC_X \+ 12", const, re.M)
    out["EC_VIN"] = occ + EC.VIN_OFF
    return out


A = addrs()


class Game(TT.Game):
    """Το colony.sna σε παύση (tests/test_trade.py)."""
    def b6v(self, at, n=1):
        v = self.b6[at - 0x4000:at - 0x4000 + n]
        return v[0] if n == 1 else v[0] | v[1] << 8

    def b6s(self, at, v, n=1):
        self.b6[at - 0x4000] = v & 255
        if n == 2:
            self.b6[at - 0x4000 + 1] = v >> 8

    def visitors(self, eta):
        self.m.poke(A["EC_SHSTATE"], 1)
        self.m.poke(A["EC_SHKIND"], SK_VISITOR)
        self.s16(A["EC_SHETA"], eta)


class Run(TI.Game):
    """Το colony.sna που τρέχει, με την κάμερα στην πίστα και το κυλικείο
    (tests/test_intruder.py)."""
    def x6(self, at, n=1):
        b = self.b6()
        return b[at - 0x4000] if n == 1 else b[at - 0x4000] | b[at - 0x3FFF] << 8

    def w16(self, at):
        return self.m.peek(at) | self.m.peek(at + 1) << 8

    def visitors(self, lounge=False, prest=0):
        b6 = self.b6()
        if lounge:
            b6[self.L["G_dome_tbl"] - 0x4000 + LOUNGE * EC.DOME_REC + EC.D_ROOM] = EC.R_LOUNGE
        b6[A["EC_PREST"] - 0x4000] = prest
        m, ec = self.m, self.EC
        m.poke(ec["EC_SHETA"], 0)
        m.poke(ec["EC_SHETA"] + 1, 0)
        m.poke(ec["EC_SHKIND"], SK_VISITOR)
        m.poke(ec["EC_SHSTATE"], EC.SHIP_INCOMING)

    def vis(self):
        a = self.a()
        return [i for i in VIS if a.flags[i] & E.F_ALIVE]


def walk(sym, g, patch=(), patch6=(), lounge=False, quiet=False):
    """ΠΕΡΠΑΤΟΥΝ (και ΣΑΛΟΝΙ, με lounge): η πρώτη διαφορά από την πρόζα, ή None."""
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    tag = "ΣΑΛΟΝΙ" if lounge else "ΠΕΡΠΑΤΟΥΝ"
    G = Run(sym, g, patch, patch6)
    m = G.m
    good0, sollen = G.x6(A["EC_GOOD"]), G.w16(A["EC_SOLLEN"])
    G.visitors(lounge)
    if not G.until(lambda: G.vis(), 64, 1):
        return f"{tag}: κανείς στις θέσεις 112-119 μετά από 64 frames"
    a, vis = G.a(), G.vis()
    bad = [i for i in vis if (a.role[i], a.node[i], a.task[i], a.health[i],
                              a.flags[i] & E.F_INDOORS) != (EC.RL_VIS, PAD, EC.T_VISIT,
                                                             EC.VP_EAT, 0)]
    coins = G.x6(A["EC_COINS"], 2)
    eta = G.w16(A["EC_SHETA"])
    if vis != [112, 113] or bad or coins:
        return (f"{tag}: στις 112-119 {vis}, λάθος "
                f"{[(i, a.role[i], a.node[i], a.task[i], a.health[i], a.flags[i]) for i in bad]}, "
                f"νομίσματα {coins}")
    if eta != sollen >> 5:
        return f"{tag}: το πλοίο μένει {eta} περιστροφές, όχι μισό sol ({sollen >> 5})"
    # --- ως το τέλος, ανά 8 frames: πού, τι φαίνεται, πόσα ---
    seen_out, seen_ring, breath, pays = set(), set(), [], []
    rooms, stay, f, gone, hud = set(), {}, 0, None, ""
    while f < 4000:
        G.m.run_frames(8)
        f += 8
        if m.peek(G.EC["EC_SHSTATE"]) == 0:
            gone = f
            break
        a, b6 = G.a(), G.b6()
        c = G.x6(A["EC_COINS"], 2)
        if not pays or pays[-1][1] != c:
            pays.append((f, c))
            if c == 10:
                G.m.run_frames(40)              # το HUD ανά 16 frames
                f += 40
                hud = hudread.text(m, sym, 1)
                a, b6 = G.a(), G.b6()
        for i in G.vis():
            if a.edge[i] == E.NO_EDGE and a.node[i] < EC.MAX_DOME:
                rooms.add(a.node[i])
                stay.setdefault((i, a.node[i]), [f, f])[1] = f
        # έξω: στη λίστα με το FC_VISITOR, και ολόκληροι στην οθόνη
        w, figs = G.figs()
        mine = [x for x in figs if x[0] in VIS]
        if any(x[3] != FC_VISITOR for x in mine):
            return f"{tag}: στη λίστα με κωδικό {[x[3] for x in mine]}, όχι {FC_VISITOR}"
        nv, missing = w.shown(mine, w.play())
        if missing:
            return f"{tag}: δεν φαίνονται ολόκληροι {missing}"
        if nv:
            seen_out |= {x[0] for x in mine}
        # μέσα: στον δακτύλιο, και αναπνέουν
        inside = [i for i in G.vis() if a.flags[i] & E.F_INDOORS]
        for i in inside:
            if a.edge[i] == E.NO_EDGE and a.slot[i] != E.NO_SLOT and a.node[i] < EC.MAX_DOME:
                # η κρυφή μνήμη φιγούρων στις ουρές των πεδίων (βήμα 172, of_at)
                if b6[G.L["G_agent_fields"] - 0x4000 + (8 + a.slot[i]) * 256 + 192 + a.node[i]] == FC_VISITOR:
                    seen_ring.add(i)
        if inside and all(a.edge[i] == E.NO_EDGE for i in G.vis()):
            breath.append((len(inside), G.x6(A["EC_VIN"])))
    if gone is None:
        return f"{tag}: σε 4000 frames το πλοίο δεν έφυγε, ζουν {G.vis()}"
    want = [0, 10, 16] if lounge else [0, 10]
    got = [c for _, c in pays]
    if got != want:
        return f"{tag}: τα νομίσματα {got}, η πρόζα λέει {want}"
    if G.x6(A["EC_GOOD"]) - good0 != 6:
        return f"{tag}: η εύνοια {good0} -> {G.x6(A['EC_GOOD'])}, όχι +6"
    if hud[36:40].replace("O", "0") != "$ 10":        # το 0 του font διαβάζεται O (hudread)
        return f"{tag}: η σειρά 1 του HUD λέει |{hud}|, όχι «$ 10» στο τέλος"
    if seen_out != {112, 113} or seen_ring != {112, 113}:
        return f"{tag}: φάνηκαν έξω {sorted(seen_out)}, στον δακτύλιο {sorted(seen_ring)}"
    want_rooms = {CANTEEN, LOUNGE} if lounge else {CANTEEN}
    if not want_rooms <= rooms:
        return f"{tag}: στάθηκαν στους θόλους {sorted(rooms)}, όχι σε όλους τους {sorted(want_rooms)}"
    # ΑΝΑΠΝΕΟΥΝ: κάθε δείγμα όπου όλοι στέκονται και κάποιοι είναι μέσα — το
    # vi_tick τους μέτρησε μετά την κίνηση, στην ίδια περιστροφή (το ef_o2
    # που τους προσθέτει είναι το ΟΞΥΓΟΝΟ, πιο κάτω)
    wrong = [b for b in breath if b[1] != b[0]]
    if len(breath) < 8 or wrong:
        return f"{tag}: (μέσα, EC_VIN) σε {len(breath)} δείγματα: {wrong[:3]}"
    # ΚΑΘΟΝΤΑΙ: στο κυλικείο τουλάχιστον VIS_STAY περιστροφές (μείον ένα δείγμα)
    sat = min(stay[(i, CANTEEN)][1] - stay[(i, CANTEEN)][0] for i in (112, 113))
    if sat < 16 * EC.VIS_STAY - 16:
        return f"{tag}: στο κυλικείο κάθισαν {sat} frames, όχι {16 * EC.VIS_STAY}"
    # ΑΝΕΒΑΙΝΟΥΝ: όλοι, το EC_VIN 0, και το πλοίο πριν από το μισό sol
    if G.vis() or G.x6(A["EC_VIN"]) or gone >= 16 * (sollen >> 5):
        return (f"{tag}: ζουν {G.vis()}, EC_VIN {G.x6(A['EC_VIN'])}, το πλοίο έφυγε "
                f"στο frame {gone} (το μισό sol: {16 * (sollen >> 5)})")
    say(f"{tag}: οι 112 και 113 στην πίστα, ρόλος 9, T_VISIT, χωρίς νομίσματα· έξω με το "
        f"FC_VISITOR ({FC_VISITOR}) ολόκληροι, μέσα στον δακτύλιο· στάθηκαν στους θόλους "
        f"{sorted(rooms)}, νομίσματα {got}, εύνοια +6, «$ 10»· EC_VIN = όσοι μέσα σε "
        f"{len(breath)} δείγματα, κάθισαν {sat} frames στο κυλικείο, ανέβηκαν, και το "
        f"πλοίο έφυγε στο frame {gone} (μισό sol {16 * (sollen >> 5)})")
    return None


def shots(sym, g):
    """Οι εικόνες της αναφοράς: έξω, και στο κυλικείο."""
    G = Run(sym, g)
    G.visitors(True, 130)
    out, f, done = os.path.join(ROOT, "build"), 0, set()
    while f < 900 and len(done) < 2:
        G.m.run_frames(4)
        f += 4
        a = G.a()
        vis = G.vis()
        if "out" not in done and vis and all(a.edge[i] != E.NO_EDGE for i in vis):
            G.m.screenshot(os.path.join(out, "visit_walk.png"), aspect=True)
            done.add("out")
        if "in" not in done and vis and all(a.node[i] == CANTEEN and a.edge[i] == E.NO_EDGE
                                            for i in vis):
            G.m.run_frames(32)
            G.m.screenshot(os.path.join(out, "visit_canteen.png"), aspect=True)
            done.add("in")
    return done


def prestige(sym, patch6=(), quiet=False):
    """ΚΥΡΟΣ, στο παιχνίδι που τρέχει: το τέλος του sol. Η πρώτη διαφορά, ή None."""
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G = Game(sym, patch6=patch6)
    m = G.m
    m.poke(A["EC_SHSTATE"], 0)
    G.b6s(A["EC_VISACC"], 250)
    G.b6s(A["EC_GOOD"], 40)
    G.s16(A["EC_FRAME"], G.w16(A["EC_SOLLEN"]) - 40)
    sol0 = m.peek(A["EC_SOL"])
    m.poke(sym["UI_SPD"], 1)
    for _ in range(200):
        m.run_frames(1)
        if m.peek(A["EC_SOL"]) != sol0:
            break
    m.poke(sym["UI_SPD"], 0)
    if m.peek(A["EC_SOL"]) == sol0:
        return "ΚΥΡΟΣ: το sol δεν άλλαξε"
    mile, alive = m.peek(A["EC_MILE"]), m.peek(A["EC_ALIVE"])
    nodeath, amen, good = m.peek(A["EC_NODEATH"]), m.peek(A["EC_AMENITY"]), G.b6v(A["EC_GOOD"])
    want = 10 * bin(mile).count("1") + (alive >> 1) + min(nodeath, 30) + 5 * min(amen, 6) + good
    got, acc = G.b6v(A["EC_PREST"]), G.b6v(A["EC_VISACC"])
    ship = (m.peek(A["EC_SHSTATE"]), m.peek(A["EC_SHKIND"]))
    if good != 39 or got != want:
        return (f"ΚΥΡΟΣ: {got}, ο τύπος {want} (ορόσημα {mile:05b}, ζωντανοί {alive}, σερί "
                f"{nodeath}, σαλόνια {amen}, εύνοια 40 -> {good})")
    if ship != (1, SK_VISITOR) or acc != 250 + want - 256:
        return f"ΚΥΡΟΣ: πλοίο {ship}, συσσωρευτής {acc} — η πρόζα λέει (1, 2) και {250 + want - 256}"
    # και προσγειώνεται, και οι επισκέπτες του πληρώνουν στο κυλικείο
    c0 = G.b6v(A["EC_COINS"], 2)
    m.poke(sym["UI_SPD"], 1)
    for _ in range(16 * 60):
        m.run_frames(1)
        if G.b6v(A["EC_COINS"], 2) > c0:
            break
    m.poke(sym["UI_SPD"], 0)
    c1 = G.b6v(A["EC_COINS"], 2)
    if c1 <= c0:
        return f"ΚΥΡΟΣ: οι επισκέπτες του πλοίου του κύρους δεν πλήρωσαν ({c0} -> {c1})"
    say(f"ΚΥΡΟΣ: στο τέλος του sol {want} = 10 x {bin(mile).count('1')} + {alive >> 1} + "
        f"{min(nodeath, 30)} + 5 x {min(amen, 6)} + {good}; ο συσσωρευτής 250 -> {acc} με "
        f"πλοίο επισκεπτών, που προσγειώθηκε, και οι επισκέπτες του έδωσαν {c1 - c0}")
    return None


def breathe(sym, patch6=()):
    """ΟΞΥΓΟΝΟ: το ef_o2 (src/flow.asm) με τρεις επισκέπτες μέσα (EC_VIN 3):
    η ζήτηση είναι 2 x (άποικοι μέσα + 3). Χωρίς κύκλο ροής (ec_fdiv 2)."""
    G = Game(sym, patch6=patch6)
    m = G.m
    ag = TO.layout()["G_agent_fields"] - 0x4000
    col = sum(1 for k in range(EC.AG_BOT0) if G.b6[ag + k] & 1 and G.b6[ag + k] & 2)
    G.b6s(A["EC_VIN"], 3)
    m.poke(sym["EC_FDIV"], 2)
    G.call("ECON_FLOW")
    use = G.w16(A["EC_O2USE"])
    if use != 2 * (col + 3):
        return f"ΟΞΥΓΟΝΟ: ζήτηση {use} με {col} αποίκους μέσα και 3 επισκέπτες — η πρόζα λέει {2 * (col + 3)}"
    print(f"    ΟΞΥΓΟΝΟ: {col} άποικοι μέσα και 3 επισκέπτες, ζήτηση {use}")
    return None


def full(sym, g, patch=(), patch6=(), quiet=False):
    """ΠΛΗΡΗΣ: επισκέπτες έξω, και η πλήρης σχεδίαση τους κρατά στη λίστα."""
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G = Run(sym, g, patch, patch6)
    G.visitors()
    if not G.until(lambda: [i for i in G.vis() if G.a().edge[i] != E.NO_EDGE], 200, 2):
        return "ΠΛΗΡΗΣ: κανείς επισκέπτης στον δρόμο"
    # ΜΕ ΤΗ ΛΙΣΤΑ ΑΔΕΙΑ: όσοι ήταν ήδη μέσα τους ξαναβάζει το πρώτο πέρασμα
    # του fg_build, ό,τι κι αν κάνει το δεύτερο — αυτό ψάχνει τους 112-119
    w, before = G.figs()
    G.m.poke(sym["FG_N"], 0)
    G.full()
    w, after = G.figs()
    mine = sorted(x for x in after if x[0] in VIS)
    if sorted(x for x in before if x[0] in VIS) != mine or len(mine) != 2:
        return (f"ΠΛΗΡΗΣ: οι επισκέπτες στη λίστα πριν {sorted(x for x in before if x[0] in VIS)}, "
                f"μετά την πλήρη σχεδίαση από άδεια λίστα {mine}")
    say(f"ΠΛΗΡΗΣ: {mine} ίδιοι πριν και μετά την πλήρη σχεδίαση από άδεια λίστα")
    return None


def cold(sym, patch0=()):
    """ΣΒΗΣΙΜΟ: $999 στο HUD, οι λωρίδες σβήνουν, και το HUD τα ξαναγράφει."""
    G = Game(sym)
    m = G.m
    G.b6s(A["EC_COINS"], 999, 2)
    G.call("HUD_DRAW", False, 0xC0)
    first = hudread.text(m, sym, 1)
    for at, v in patch0:
        m.poke(at, v)
    G.call("HUD_INVAL", False, 0xC0)
    G.call("HUD_DRAW", False, 0xC0)
    hud = hudread.text(m, sym, 1)
    if first[36:40] != "$999" or hud[36:40] != "$999":
        return f"ΣΒΗΣΙΜΟ: πριν |{first[36:40]}|, μετά |{hud[36:40]}| — όχι «$999» και τα δύο"
    return None


def jump(sym, patch0=()):
    """ΑΛΜΑ: το EC_X, το EC_VIN και το EC_TU μένουν σε ένα view_draw. Η πρώτη διαφορά, ή None."""
    G = Game(sym)
    m = G.m
    for at, v in patch0:
        m.poke(at, v)
    x = A["EC_COINS"] - 6                                      # EC_X
    keep = list(range(14))      # EC_X, EC_VIN, EC_TU (ως το βήμα 171 τα σημάδια 100-111 και 120-127)
    want = {k: (0x37 * k + 0x11) & 255 for k in keep}
    for k, v in want.items():
        G.b6s(x + k, v)
    G.call("VIEW_DRAW", False, 0xC0)
    got = {k: G.b6v(x + k) for k in keep}
    if got != want:
        return f"ΑΛΜΑ: το EC_X μετά το view_draw {[got[k] for k in keep]}, ήταν {[want[k] for k in keep]}"
    return None


def cost(sym):
    G = Game(sym)
    m = G.m
    base = G.probe([], True)
    out = {}
    # πέντε επισκέπτες (κύρος 250)
    G.visitors(0)
    G.b6s(A["EC_PREST"], 250)
    G.set_stock({EC.S_FOOD: 300, EC.S_WATER: 300})
    out["προσγείωση, πέντε"] = G.call("SHIP_TICK", True) - base
    # η επόμενη: στέκονται στην πίστα που «πήγαιναν», και ψάχνουν κυλικείο
    out["περιστροφή, πέντε αποφασίζουν"] = G.call("SHIP_TICK", True) - base
    out["περιστροφή, πέντε ξεκινούν"] = G.call("SHIP_TICK", True) - base
    G.s16(A["EC_SHETA"], 0)                     # το μισό sol τελείωσε
    out["φεύγει, με πέντε έξω"] = G.call("SHIP_TICK", True) - base
    left = [i for i in VIS if G.b6[TO.layout()["G_agent_fields"] - 0x4000 + i] & 1]
    assert not left, f"ΚΟΣΤΟΣ: έμειναν {left}"
    # το τέλος του sol με το πλοίο του κύρους
    m.poke(A["EC_SHSTATE"], 0)
    G.b6s(A["EC_VISACC"], 255)
    out["τέλος του sol, με πλοίο"] = G.call("SOL_ROLLOVER", True) - base
    G.b6s(A["EC_COINS"], 998, 2)
    G.call("HUD_DRAW", True, 0xC0)
    out["HUD, τα ίδια $998"] = G.call("HUD_DRAW", True, 0xC0) - base
    G.b6s(A["EC_COINS"], 999, 2)
    out["HUD, 998 -> $999"] = G.call("HUD_DRAW", True, 0xC0) - base
    return out


def main():
    sym, g = TG.build()
    why = walk(sym, g)
    check(why is None, why or "περπατούν: στην πίστα, έξω, στο κυλικείο μέσα, πληρώνουν, "
                              "αναπνέουν, κάθονται, ανεβαίνουν, και το πλοίο φεύγει")
    why = walk(sym, g, lounge=True)
    check(why is None, why or "σαλόνι: πέντε στο κυλικείο και τρία στο σαλόνι ο καθένας")
    got = shots(sym, g)
    check(got == {"out", "in"}, f"εικόνες: build/visit_walk.png και build/visit_canteen.png "
                                f"({sorted(got)})")
    why = prestige(sym)
    check(why is None, why or "κύρος: ο τύπος της πρόζας, και το πλοίο του συσσωρευτή")
    why = breathe(sym)
    check(why is None, why or "οξυγόνο: αναπνέουν όσοι επισκέπτες είναι μέσα")
    why = full(sym, g)
    check(why is None, why or "πλήρης σχεδίαση: οι επισκέπτες μένουν στη λίστα")
    got = cost(sym)
    why = jump(sym)
    check(why is None, why or "άλμα: νομίσματα, κύρος, ώρες ηρεμίας και EC_VIN μένουν σε ένα view_draw")
    why = cold(sym)
    check(why is None, why or "σβήσιμο: τα νομίσματα ξαναγράφονται, ίδια κι ας είναι")
    check(all(got[k] <= COST[k] for k in COST),
          "κόστος: " + ", ".join(f"{k} {got[k]} us (ταβάνι {COST[k]})" for k in COST))

    # --- ΑΡΝΗΤΙΚΑ ---
    G = Game(sym)
    m = G.m
    w = lambda v: [v & 255, v >> 8]
    b6 = lambda name, n: bytes(G.b6[sym[name] - 0x4000:sym[name] - 0x4000 + n])
    find6 = lambda name, n, pat: [sym[name] + k for k in range(n - len(pat) + 1)
                                  if list(b6(name, n)[k:k + len(pat)]) == pat]
    find0 = lambda name, n, pat: [sym[name] + k for k in range(n - len(pat) + 1)
                                  if list(m.read_ram(sym[name] + k, len(pat))) == pat]

    def neg(label, at, patch_of, test):
        if len(at) != 1:
            check(False, f"ΑΡΝΗΤΙΚΟ «{label}»: δεν βρέθηκε ο κώδικας ({len(at)} θέσεις)")
            return
        why = test(patch_of(at[0]))
        check(why is not None, f"ΑΡΝΗΤΙΚΟ «{label}»: {why or 'ΔΕΝ ΠΙΑΣΤΗΚΕ'}"[:300])

    c, sc = A["EC_COINS"], sym["SHIP_CALL"]
    # η πληρωμή, στην τράπεζα 0 (src/visit0.asm): ld (EC_COINS),hl -> nop
    neg("η πληρωμή δεν γράφεται", find0("VI_PAY", 12, [0x22] + w(c)),
        lambda a: [(a + k, 0) for k in range(3)], lambda p: walk(sym, g, patch=p, quiet=True))
    neg("το HUD διαβάζει μηδέν", find6("VS_COINS", 3, [0x2A] + w(c)),
        lambda a: [(a, 0x21), (a + 1, 0), (a + 2, 0)], lambda p: walk(sym, g, patch6=p, quiet=True))
    neg("ο συσσωρευτής δεν φέρνει πλοίο", find6("SR_PRES", 120, [0xCD] + w(sc)),
        lambda a: [(a + k, 0) for k in range(3)], lambda p: prestige(sym, patch6=p, quiet=True))
    # το hud_inval δεν ξεχνά τα νομίσματα
    cw = sym["HUD_CW"]
    neg("το HUD δεν βλέπει το σβήσιμο", find0("HUD_INVAL", 6, [0x21, 0xFF, 0xFF, 0x22] + w(cw)),
        lambda a: [(a + k, 0) for k in (3, 4, 5)], lambda p: cold(sym, p))
    # ΤΟ ΑΛΜΑ: ως το βήμα 171 το αρνητικό ήταν το fg_build σε όλους τους 128
    # πράκτορες, που έσβηνε τα σημάδια τους — και τα σημάδια των 100-127 ήταν
    # το EC_X. Από το 172 τα σημάδια έχουν σελίδα, και εκείνο δεν σβήνει τίποτα
    # (δοκιμάστηκε: ΔΕΝ ΠΙΑΣΤΗΚΕ). Το EC_X είναι στο 240 του node_occ, και ό,τι
    # γράφει εκεί είναι το λάθος: το καθάρισμα της κρυφής μνήμης φιγούρων του
    # ob_fig_scan, μέσα στο view_draw, σε λάθος σελίδα — ld hl,DF_PG*256 +
    # DF_L με H = node_occ: το 192-255 του node_occ μηδέν.
    occ_pg, df_pg = TO.layout()["G_node_occ"] >> 8, (TO.layout()["G_agent_fields"] >> 8) + 8
    neg("το καθάρισμα των φιγούρων στο node_occ", find0("OB_FIG_SCAN", 4, [0x21, 192, df_pg]),
        lambda a: [(a + 2, occ_pg)], lambda p: jump(sym, p))
    # ld bc,AG_NVIS * 256 + AG_VIS0 - 1 -> το ίδιο με το δεύτερο (χωρίς τους
    # επισκέπτες: το δεύτερο κομμάτι βλέπει C = 255 και τελειώνει)
    neg("το fg_build χωρίς τους επισκέπτες",
        find0("FGB_ALL", 4, [0x01, EC.AG_VIS0 - 1, EC.AG_NVIS]),
        lambda a: [(a + 1, 0xFF), (a + 2, 100)], lambda p: full(sym, g, patch=p, quiet=True))
    # ο επισκέπτης με τη φιγούρα του αποίκου: role_fig[9]
    neg("ο επισκέπτης με τη φιγούρα του αποίκου",
        [sym["ROLE_FIG"] + EC.RL_VIS] if m.peek(sym["ROLE_FIG"] + EC.RL_VIS) == FC_VISITOR else [],
        lambda a: [(a, FC_COLONIST)], lambda p: walk(sym, g, patch=p, quiet=True))
    # δεν αναπνέουν: το ld (EC_VIN),a του vi_tick -> nop
    vin = A["EC_VIN"]
    neg("οι επισκέπτες μέσα δεν μετριούνται", find6("VI_TICK", 80, [0x32] + w(vin)),
        lambda a: [(a + k, 0) for k in range(3)], lambda p: walk(sym, g, patch6=p, quiet=True))
    # ...και το ef_o2 δεν τους προσθέτει: ld a,(EC_VIN) -> ld a,0 / nop
    neg("το οξυγόνο χωρίς τους επισκέπτες", find6("EF_ALIVE", 16, [0x3A] + w(vin)),
        lambda a: [(a, 0x3E), (a + 1, 0), (a + 2, 0)], lambda p: breathe(sym, p))
    # δεν κάθονται: ld (hl),VIS_STAY -> ld (hl),0
    neg("οι επισκέπτες δεν κάθονται", find6("VIA_STAY", 8, [0x36, EC.VIS_STAY]),
        lambda a: [(a + 1, 0)], lambda p: walk(sym, g, patch6=p, quiet=True))
    # δεν ανεβαίνουν: jp nd_bury -> ret, nop, nop
    neg("οι επισκέπτες δεν ανεβαίνουν", find6("VIA_BOARD", 8, [0xC3] + w(sym["ND_BURY"])),
        lambda a: [(a, 0xC9), (a + 1, 0), (a + 2, 0)], lambda p: walk(sym, g, patch6=p, quiet=True))
    print("ΟΛΑ ΟΚ" if not FAIL else f"{len(FAIL)} ΑΠΟΤΥΧΙΕΣ")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
