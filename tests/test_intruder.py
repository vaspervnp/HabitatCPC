#!/usr/bin/env python3
"""Οι εισβολείς (βήμα 111, DESIGN §6.10), στο παιχνίδι, με την αποικία δοκιμών.

Η πρόζα — οι αποφάσεις του παίκτη, όπως στο Planetbase:

  ΠΛΟΙΟ      το πλοίο τους (SK_FOE) προσγειώνεται στην πίστα όπως κάθε πλοίο, και
             κατεβαίνουν δύο (η αποικία έχει λιγότερους από 40) στις θέσεις
             96-99: ρόλος 8, εργασία T_FIGHT, υγεία 160, έξω, στην πίστα. Το
             μέτρημα των προσγειώσεων (EC_LANDS) γίνεται 0, και στην επόμενη
             περιστροφή το fo_n λέει 2 και το HUD «INTRUDERS». Ποιο απρόσκλητο
             πλοίο είναι δικό τους, με πόσους αποίκους και προσγειώσεις, και πόσοι
             κατεβαίνουν, στα όριά τους, το ελέγχει το tests/test_sim.py απέναντι
             στην αναφορά — και τη μάχη byte προς byte.
  ΚΟΚΚΙΝΟΙ   φαίνονται. Έξω η λίστα φιγούρων έχει τον καθένα με τον κωδικό
             FC_INTRUDER, και κάθε αδιαφανές bit της φιγούρας του (fig_gfx) είναι
             στην οθόνη· όσο είναι έξω, η οθόνη έχει κόκκινα pixels (pen 8) που
             πριν δεν είχε, ενώ η αποικία δεν έχει γιατρό ούτε χαλασμένη μηχανή.
  ΜΠΑΙΝΟΥΝ   περπατούν από την πίστα, μπαίνουν από το airlock (F_INDOORS) και
             φτάνουν σε θόλο όπου στέκεται άποικος. Εκεί στέκονται στον δακτύλιο
             (DOME_FIG = FC_INTRUDER), και τα κόκκινα pixels είναι μέσα στον θόλο.
  ΧΤΥΠΟΥΝ    όποιος άποικος στέκεται στον κόμβο τους χάνει υγεία· χωρίς φρουρούς
             πεθαίνουν (EC_DEATHS), και οι εισβολείς ζουν ακόμη.
  ΦΡΟΥΡΟΙ    δύο φρουροί και δύο Gun: τα παίρνουν (F_GUN, απόθεμα 0) και οι
             εισβολείς πέφτουν. Μετά οι φρουροί έχουν ξανά εργασία NO_TASK (ή πάνε
             για ανάγκη), το fo_n είναι 0 και το HUD δεν λέει INTRUDERS.
  ΔΙΨΑ       (βήμα 150) ένας φρουρός διψασμένος μέσα, νερό 40 και το απόθεμα
             νερού 0 (το κυλικείο δεν δίνει): με τον συναγερμό αφήνει το T_NEED
             για τη μάχη, με το νερό του ακόμη κάτω από 64, και ως να πέσουν οι
             εισβολείς δεν κάνει κανένα βήμα με T_NEED, σε κανένα frame — ας του
             το ξαναγράφουν οι ανάγκες: η θέση 15 τρέχει πριν από την κίνηση.
  ΣΥΝΑΓΕΡΜΟΣ (βήμα 166) ο 1 βγαίνει και στέκεται στην πίστα, χωρίς δουλειά,
             και εκεί προσγειώνονται οι εισβολείς. Με την προσγείωση έχει
             T_FIGHT και προορισμό το airlock της αποικίας· μπαίνει (F_INDOORS)
             χωρίς να τον χτυπήσει κανείς — η υγεία του όση ήταν — ενώ οι
             εισβολείς ζουν ακόμη.

Αρνητικά, με τον κώδικα πειραγμένο: το πλοίο τους χωρίς το cp SK_FOE του
st_here (ΠΛΟΙΟ)· ο ρόλος 8 με τη φιγούρα του αποίκου (ΚΟΚΚΙΝΟΙ)· το HUD χωρίς το
INTRUDERS (ΠΛΟΙΟ)· οι φρουροί χωρίς το set 7,(hl) του όπλου, και χωρίς το
NO_TASK του fo_over (ΦΡΟΥΡΟΙ)· ο κανόνας ως το βήμα 149, όποιος πάει για ανάγκη
δεν πολεμά (το and F_INDOORS του fg_need -> and 0) (ΔΙΨΑ)· η προσγείωση χωρίς
τον συναγερμό (το call fo_alert του fo_land -> nop) (ΣΥΝΑΓΕΡΜΟΣ).
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_reveal as R                                  # noqa: E402
import test_figure as F                                  # noqa: E402
import test_outside as TO                                # noqa: E402
import hudread                                           # noqa: E402
import codeat                                            # noqa: E402
import econ as EC                                        # noqa: E402
import entity as E                                       # noqa: E402
import pack                                              # noqa: E402

FAIL = []
FC_INTRUDER = pack.fig_code(pack.FIG_ALL.index(pack.FOE_FIG))
FC_COLONIST = pack.fig_code(pack.FIG_ALL.index("colonist"))
PAD, CANTEEN = EC.MAX_DOME, 2                 # η πίστα είναι η δομή 0 (src/colony.asm)
CAM_OUT = (-14, 1)                            # η πίστα στο κάδρο (10 tiles ύψος)


def check(ok, msg):
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ ") + msg)
    if not ok:
        FAIL.append(msg)


def ec_at(g):
    const = open(os.path.join(ROOT, "src", "const.asm"), encoding="utf-8").read()
    return {n: g + int(re.search(rf"^{n}\s+equ G_econ_state \+ (\d+)", const, re.M).group(1))
            for n in ("EC_SHSTATE", "EC_SHKIND", "EC_SHETA", "EC_LANDS", "EC_DEATHS",
                      "EC_ALIVE")}


class Game(R.Game):
    """Το colony.sna: τρεις θόλοι, η πίστα, ένα airlock, τέσσερις άποικοι."""

    def __init__(self, sym, g, patch=(), patch6=()):
        super().__init__(sym, g)
        self.L, self.EC = TO.layout(), ec_at(g)
        self.ag = self.L["G_agent_fields"] - 0x4000
        for at, v in patch:
            codeat.poke(self.m, at, v)
        for at, v in patch6:
            codeat.poke(self.m, at, v)
        self.cam = CAM_OUT
        self.camera(*CAM_OUT)
        # ΤΟ NO OXYGEN ΤΗΣ ΑΠΟΙΚΙΑΣ ΔΟΚΙΜΩΝ ΠΡΩΤΑ (βήμα 110, §15): κρατά 11,2 s από
        # την αρχή, και στο HUD είναι πάνω από το INTRUDERS — η ασφυξία σκοτώνει
        # όλους, οι εισβολείς όσους βρουν.
        econ = TO.layout()["G_econ_state"]
        assert self.until(lambda: self.m.peek(econ + 47), 1200), "το O2OK δεν ήρθε"
        self.m.run_frames(60)

    def b6(self):
        return self.bank(6)

    def a(self):
        return E.Agents().from_bytes(bytes(self.b6()[self.ag:self.ag + 2048]))

    def alive(self, lo, hi):
        b = self.b6()
        return [i for i in range(lo, hi) if b[self.ag + i] & 1]

    def land(self):
        """Το πλοίο τους, στην πίστα στην επόμενη περιστροφή."""
        m, ec = self.m, self.EC
        m.poke(ec["EC_LANDS"], 9)
        m.poke(ec["EC_SHETA"], 0)
        m.poke(ec["EC_SHETA"] + 1, 0)
        m.poke(ec["EC_SHKIND"], EC.SK_FOE)
        m.poke(ec["EC_SHSTATE"], EC.SHIP_INCOMING)

    def until(self, cond, frames, step=8):
        for _ in range(0, frames, step):
            if cond():
                return True
            self.m.run_frames(step)
        return cond()

    def hud(self):
        return hudread.text(self.m, self.sym, 2)

    def red(self):
        """Πόσα pixels pen 8 έχει το κάδρο."""
        n = 0
        for b in self.play():
            pl, pr = pack._m0_pens(b)
            n += (pl == 8) + (pr == 8)
        return n

    def red_in(self, node):
        """Τα κόκκινα pixels μέσα στο αποτύπωμα του θόλου node."""
        b6, d = self.b6(), self.L["G_dome_tbl"] - 0x4000 + 24 * node
        cx, cy = F.sb(b6[d]), F.sb(b6[d + 1])
        half = 4 + 2 * b6[d + 2]                     # μισή πλευρά, σε μισά tiles
        x0 = 2 * (cx - half - 2 * self.cam[0])       # bytes: δύο ανά μισό tile
        y0 = 8 * (cy - half - 2 * self.cam[1])       # γραμμές: οκτώ ανά μισό tile
        play, n = self.play(), 0
        for y in range(max(0, y0), min(160, y0 + 16 * half)):
            for x in range(max(0, x0), min(80, x0 + 4 * half)):
                pl, pr = pack._m0_pens(play[y * 80 + x])
                n += (pl == 8) + (pr == 8)
        return n

    def figs(self):
        w = F.G(self.sym, None, m=self.m)
        return w, w.figs()


def ship(sym, g, patch=(), patch6=(), quiet=False):
    """ΠΛΟΙΟ, ΚΟΚΚΙΝΟΙ, ΜΠΑΙΝΟΥΝ, ΧΤΥΠΟΥΝ — χωρίς φρουρούς. Η πρώτη διαφορά από
    την πρόζα, ή None."""
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G = Game(sym, g, patch, patch6)
    red0, hud0 = G.red(), G.hud()
    G.land()
    if not G.until(lambda: G.alive(EC.AG_FOE0, EC.AG_FOE0 + EC.AG_NFOE), 64):
        return "ΠΛΟΙΟ: κανείς στις θέσεις 96-99 μετά από 64 frames"
    a = G.a()
    foes = G.alive(EC.AG_FOE0, EC.AG_FOE0 + EC.AG_NFOE)
    bad = [i for i in foes if (a.role[i], a.node[i], a.task[i], a.health[i],
                               a.flags[i] & E.F_INDOORS) != (EC.RL_FOE, PAD, EC.T_FIGHT,
                                                              EC.FOE_HP, 0)]
    if foes != [96, 97] or bad or G.m.peek(G.EC["EC_LANDS"]) != 0:
        return (f"ΠΛΟΙΟ: στις 96-99 {foes}, λάθος {[(i, a.role[i], a.node[i], a.task[i], a.health[i], a.flags[i]) for i in bad]}, "
                f"προσγειώσεις {G.m.peek(G.EC['EC_LANDS'])}")
    G.m.run_frames(40)
    n, hud = G.m.peek(sym["FO_N"]), G.hud()
    if n != 2 or "INTRUDERS" not in hud or "INTRUDERS" in hud0:
        return f"ΠΛΟΙΟ: fo_n {n}, το HUD «{hud.strip()}» (πριν «{hud0.strip()}»)"
    say(f"ΠΛΟΙΟ: οι 96 και 97 στην πίστα, ρόλος 8, T_FIGHT, υγεία 160· fo_n 2, «{hud.strip()}»")
    # --- ΚΟΚΚΙΝΟΙ, έξω ---
    seen, reds = set(), 0
    for _ in range(40):
        w, figs = G.figs()
        mine = [f for f in figs if f[0] in foes]
        if any(f[3] != FC_INTRUDER for f in mine):
            return f"ΚΟΚΚΙΝΟΙ: στη λίστα με κωδικό {[f[3] for f in mine]}, όχι {FC_INTRUDER}"
        nv, missing = w.shown(mine, w.play())
        if missing:
            return f"ΚΟΚΚΙΝΟΙ: δεν φαίνονται ολόκληροι {missing}"
        if nv:
            seen |= {f[0] for f in mine}
            reds = max(reds, G.red() - red0)
        if seen == set(foes) and reds:
            break
        G.m.run_frames(16)
    if seen != set(foes) or reds < 8:
        return f"ΚΟΚΚΙΝΟΙ: έξω φάνηκαν {sorted(seen)}, {reds} κόκκινα pixels παραπάνω"
    say(f"ΚΟΚΚΙΝΟΙ: έξω και οι δύο με το FC_INTRUDER ({FC_INTRUDER}), ολόκληροι στην "
        f"οθόνη, και ως {reds} κόκκινα pixels που πριν δεν υπήρχαν")
    # --- ΜΠΑΙΝΟΥΝ ---
    def inside():
        a = G.a()
        return [i for i in foes if a.flags[i] & E.F_INDOORS and a.node[i] < EC.MAX_DOME
                and a.edge[i] == E.NO_EDGE and a.slot[i] != E.NO_SLOT]
    if not G.until(inside, 3000):
        a = G.a()
        return f"ΜΠΑΙΝΟΥΝ: σε 3000 frames κανείς σε θόλο: {[(i, a.node[i], a.flags[i]) for i in foes]}"
    i = inside()[0]
    a = G.a()
    d, sl = a.node[i], a.slot[i]
    b6 = G.b6()
    r = G.L["G_dome_tbl"] - 0x4000 + 24 * d
    G.cam = (F.sb(b6[r]) // 2 - 10, F.sb(b6[r + 1]) // 2 - 5)      # ο θόλος στη μέση: 20 x 10 tiles
    G.camera(*G.cam)
    dfig = G.b6()[G.L["G_dome_fig"] - 0x4000 + 8 * d + sl]
    rd = G.red_in(d)
    if dfig != FC_INTRUDER or rd < 6:
        return f"ΜΠΑΙΝΟΥΝ: ο {i} στον θόλο {d}, θέση {sl}: DOME_FIG {dfig}, {rd} κόκκινα pixels στον θόλο"
    say(f"ΜΠΑΙΝΟΥΝ: ο {i} στον δακτύλιο του θόλου {d} (θέση {sl}, FC_INTRUDER), "
        f"{rd} κόκκινα pixels μέσα στον θόλο")
    # --- ΧΤΥΠΟΥΝ ---
    hp0 = {c: G.a().health[c] for c in range(4)}
    if not G.until(lambda: G.m.peek(G.EC["EC_DEATHS"]) or len(G.alive(0, 4)) < 4, 6000, 32):
        a = G.a()
        return f"ΧΤΥΠΟΥΝ: σε 6000 frames κανείς δεν πέθανε: υγείες {[a.health[c] for c in range(4)]} (ήταν {hp0})"
    left = G.alive(EC.AG_FOE0, EC.AG_FOE0 + EC.AG_NFOE)
    if left != foes:
        return f"ΧΤΥΠΟΥΝ: χωρίς φρουρούς έπεσαν εισβολείς: ζουν {left}"
    say(f"ΧΤΥΠΟΥΝ: χωρίς φρουρούς πέθανε άποικος ({4 - len(G.alive(0, 4))} από 4), "
        f"οι εισβολείς ζουν")
    return None


def guards(sym, g, patch=(), patch6=(), quiet=False):
    """ΦΡΟΥΡΟΙ: οι 2 και 3 φρουροί, δύο Gun. Η πρώτη διαφορά, ή None."""
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G = Game(sym, g, patch, patch6)
    b6 = G.b6()
    for c in (2, 3):
        b6[G.ag + 128 + c] = EC.RL_GUARD
    gun = g + 2 * EC.S_GUN
    G.m.poke(gun, 2)
    G.m.poke(gun + 1, 0)
    G.land()
    if not G.until(lambda: G.alive(96, 100), 64):
        return "ΦΡΟΥΡΟΙ: δεν κατέβηκαν"
    if not G.until(lambda: not G.alive(96, 100), 8000, 32):
        a = G.a()
        return (f"ΦΡΟΥΡΟΙ: σε 8000 frames ζουν ακόμη {G.alive(96, 100)}, υγεία "
                f"{[a.health[i] for i in G.alive(96, 100)]}, όπλα {[a.flags[c] >> 7 for c in (2, 3)]}")
    G.m.run_frames(40)
    a = G.a()
    armed = [c for c in (2, 3) if a.flags[c] & EC.F_GUN or not a.flags[c] & E.F_ALIVE]
    stock = G.m.peek(gun) | G.m.peek(gun + 1) << 8
    tasks = [a.task[c] for c in (2, 3) if a.flags[c] & E.F_ALIVE]
    n, hud = G.m.peek(sym["FO_N"]), G.hud()
    if armed != [2, 3] or stock or any(t == EC.T_FIGHT for t in tasks) or n or "INTRUDERS" in hud:
        return (f"ΦΡΟΥΡΟΙ: όπλα {armed}, απόθεμα {stock}, εργασίες {tasks}, fo_n {n}, "
                f"HUD «{hud.strip()}»")
    say(f"ΦΡΟΥΡΟΙ: πήραν τα δύο Gun, οι εισβολείς έπεσαν, εργασίες {tasks}, fo_n 0, "
        f"«{hud.strip()}», ζουν {len(G.alive(0, 4))} από τους 4")
    return None


def thirst(sym, g, patch=(), patch6=(), quiet=False):
    """ΔΙΨΑ: ο 2 φρουρός, νερό 40, απόθεμα νερού 0. Η πρώτη διαφορά, ή None."""
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G = Game(sym, g, patch, patch6)
    b6, c = G.b6(), 2
    b6[G.ag + 128 + c] = EC.RL_GUARD
    water = g + 2 * EC.S_WATER
    G.m.poke(water, 0)
    G.m.poke(water + 1, 0)
    b6[G.ag + 1024 + 128 + c] = 40                  # AG_O2 + 128: το νερό του
    if not b6[G.ag + c] & E.F_INDOORS:
        return "ΔΙΨΑ: ο φρουρός δεν είναι μέσα"
    if not G.until(lambda: G.b6()[G.ag + 768 + 128 + c] == E.T_NEED, 200, 1):
        return f"ΔΙΨΑ: δεν πήγε για νερό (εργασία {G.b6()[G.ag + 768 + 128 + c]})"
    G.land()
    if not G.until(lambda: G.alive(96, 100), 64):
        return "ΔΙΨΑ: δεν κατέβηκαν"
    pos = lambda b: (b[G.ag + 256 + c], b[G.ag + 512 + 128 + c], b[G.ag + 768 + c])
    fought, back, frames, tried = None, None, 0, 0
    was = pos(G.b6())
    while G.alive(96, 100) and frames < 3000:
        G.m.run_frames(1)
        frames += 1
        b = G.b6()
        if not b[G.ag + c] & E.F_ALIVE:
            break
        t, w, now = b[G.ag + 768 + 128 + c], b[G.ag + 1024 + 128 + c], pos(b)
        if fought is None and t == EC.T_FIGHT and w < 64:
            fought = (frames, w)
        elif fought is not None and t == E.T_NEED and G.alive(96, 100):
            tried += 1
            if now != was and back is None:
                back = (frames, w, was, now)
        was = now
    if fought is None:
        return f"ΔΙΨΑ: σε {frames} frames ο φρουρός δεν πήγε στη μάχη με νερό κάτω από 64"
    if back is not None:
        return (f"ΔΙΨΑ: στο frame {back[0]} ο φρουρός έκανε βήμα με T_NEED (νερό {back[1]}, "
                f"{back[2]} -> {back[3]}), με εισβολείς ζωντανούς")
    say(f"ΔΙΨΑ: ο φρουρός με νερό {fought[1]} στη μάχη από το frame {fought[0]} ως το "
        f"τέλος της, {frames} frames· T_NEED από τις ανάγκες σε {tried} frames, κανένα "
        f"βήμα με αυτό· ζουν εισβολείς {len(G.alive(96, 100))}")
    return None


def alert(sym, g, patch=(), patch6=(), quiet=False):
    """ΣΥΝΑΓΕΡΜΟΣ: ο 1 στην πίστα όταν προσγειώνονται. Η πρώτη διαφορά, ή None."""
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G = Game(sym, g, patch, patch6)
    b6, c = G.b6(), 1
    st = G.L["G_struct_tbl"] - 0x4000
    locks = [EC.MAX_DOME + k for k in range(EC.MAX_STRUCT)
             if b6[st + 8 * k + EC.ST_KIND] == EC.K_AIRLOCK
             and b6[st + 8 * k + EC.ST_STATE] == EC.DS_ACTIVE]
    if len(locks) != 1:
        return f"ΣΥΝΑΓΕΡΜΟΣ: η αποικία έχει airlock {locks}, όχι ένα"
    # Στην πίστα με T_FIGHT, που ο πίνακας εργασιών δεν το πιάνει (κανένας
    # εισβολέας ακόμη: fo_n 0, και κανένα fo_over δεν το σβήνει).
    b6[G.ag + 512 + c] = PAD                        # προορισμός
    b6[G.ag + 768 + 128 + c] = EC.T_FIGHT           # εργασία

    def at_pad():
        a = G.a()
        return a.node[c] == PAD and a.edge[c] == E.NO_EDGE and not a.flags[c] & E.F_INDOORS
    if not G.until(at_pad, 3000):
        a = G.a()
        return f"ΣΥΝΑΓΕΡΜΟΣ: ο 1 δεν έφτασε στην πίστα ({a.node[c]}, {a.flags[c]:#x})"
    G.b6()[G.ag + 768 + 128 + c] = E.NO_TASK
    hp = G.a().health[c]
    G.land()
    if not G.until(lambda: G.alive(EC.AG_FOE0, EC.AG_FOE0 + EC.AG_NFOE), 64, 1):
        return "ΣΥΝΑΓΕΡΜΟΣ: δεν κατέβηκαν"
    a = G.a()
    if (a.task[c], a.dest[c]) != (EC.T_FIGHT, locks[0]):
        return (f"ΣΥΝΑΓΕΡΜΟΣ: με την προσγείωση ο 1 έχει εργασία {a.task[c]}, προορισμό "
                f"{a.dest[c]}, όχι T_FIGHT και το airlock {locks[0]}")
    if not G.until(lambda: G.a().flags[c] & E.F_INDOORS, 2000, 4):
        a = G.a()
        return f"ΣΥΝΑΓΕΡΜΟΣ: ο 1 δεν μπήκε σε 2000 frames ({a.node[c]}, υγεία {a.health[c]})"
    a = G.a()
    foes = G.alive(EC.AG_FOE0, EC.AG_FOE0 + EC.AG_NFOE)
    if a.health[c] != hp or not foes:
        return f"ΣΥΝΑΓΕΡΜΟΣ: μέσα με υγεία {a.health[c]} (ήταν {hp}), εισβολείς {foes}"
    say(f"ΣΥΝΑΓΕΡΜΟΣ: ο 1 στην πίστα πήρε T_FIGHT και το airlock {locks[0]} με την "
        f"προσγείωση, και μπήκε (κόμβος {a.node[c]}) με την υγεία του, {hp}· ζουν "
        f"εισβολείς {foes}")
    return None


def main():
    sym, g = R.T.build()
    for name, fn in (("ΠΛΟΙΟ ως ΧΤΥΠΟΥΝ", ship), ("ΦΡΟΥΡΟΙ", guards), ("ΔΙΨΑ", thirst),
                     ("ΣΥΝΑΓΕΡΜΟΣ", alert)):
        why = fn(sym, g)
        check(why is None, f"{name}: όπως λέει η πρόζα" + (f" — {why}" if why else ""))

    # --- ΑΡΝΗΤΙΚΑ ---
    m0 = Game(sym, g).m
    w = lambda v: [v & 255, v >> 8]
    at = lambda label, pat, span=160: codeat.find(m0, sym[label], pat, span)
    sk = at("ST_HERE", [0xFE, EC.SK_FOE])                          # cp SK_FOE
    rf = sym["ROLE_FIG"] + EC.RL_FOE
    hf = at("HUD_ALERT", [0x3D, 0xFE, EC.AG_NFOE, 0x21], 200)     # dec a / cp 4 / ld hl,txt_foe
    gn = at("FO_GUARD", [0xCB, 0xFE], 80)                          # set 7,(hl): το όπλο
    nt = at("FOO_LP", [0x36, E.NO_TASK], 12)                       # ld (hl),NO_TASK
    fi = at("FG_NEED", [0xE6, E.F_INDOORS], 16)                    # and F_INDOORS
    fa = at("FO_LAND", [0xCD] + w(sym["FO_ALERT"]), 64)            # call fo_alert
    for label, fn, patch in (
            ("το πλοίο τους χωρίς το cp SK_FOE", ship, sk and [(sk + 1, 99)]),
            ("ο ρόλος 8 με τη φιγούρα του αποίκου", ship, [(rf, FC_COLONIST)]),
            ("το HUD χωρίς το INTRUDERS", ship, hf and [(hf + 7, 0)]),     # jr c,hd_say
            ("οι φρουροί χωρίς όπλο", guards, gn and [(gn, 0), (gn + 1, 0)]),
            ("οι φρουροί μένουν στη μάχη", guards, nt and [(nt, 0), (nt + 1, 0)]),
            ("όποιος πάει για ανάγκη δεν πολεμά", thirst, fi and [(fi + 1, 0)]),
            ("η προσγείωση χωρίς τον συναγερμό", alert, fa and [(fa + k, 0) for k in range(3)])):
        if not patch:
            check(False, f"δεν βρέθηκε πού να πειραχτεί για «{label}»")
            continue
        why = fn(sym, g, patch=patch, quiet=True)
        check(why is not None, f"ΑΡΝΗΤΙΚΟ: με «{label}» αποτυγχάνει ({(why or '')[:110]})")

    print()
    if FAIL:
        print(f"ΑΠΟΤΥΧΙΑ — {len(FAIL)} προβλήματα")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
