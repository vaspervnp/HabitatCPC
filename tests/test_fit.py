#!/usr/bin/env python3
"""Ο εξοπλισμός ενός θόλου, υποδοχή-υποδοχή (src/fit.asm, βήμα 45).

Ως το βήμα 44 ο θόλος γέμιζε μόνος του, κυκλικά πάνω στη λίστα του δωματίου.
Τώρα μπαίνει άδειος και ο παίκτης διαλέγει, όπως στο Planetbase. Ολα με τα
ΠΛΗΚΤΡΑ, στο κανονικό binary, και τίποτα δεν ελέγχεται με «φαίνεται σωστό»:

  ΜΠΑΙΝΕΙ    οκτώ υποδοχές ενός χτισμένου εργοστασίου L: η εγγραφή λέει ό,τι
             διαλέχτηκε, τα αποθέματα πλήρωσαν ό,τι λέει το fit_cost, και η
             οθόνη είναι ΙΔΙΑ με πλήρη σχεδίαση. Οι μηχανές περιμένουν τα
             υλικά τους και τον μηχανικό (βήμα 99, tests/test_install.py)· τα
             φυτά δουλεύουν αμέσως.
  ΒΓΑΙΝΕΙ    ΑΔΕΙΟ σε μία υποδοχή: NO_MACH, υγεία 0, τα μισά πίσω· ό,τι ήταν
             κάτω από τη μηχανή ξαναστρώνεται (dhv_rect), και η οθόνη είναι
             πάλι η πλήρης σχεδίαση — με κανάρινι που δεν σβήνει. ΑΡΝΗΤΙΚΟ:
             χωρίς το dhv_rect η μηχανή μένει ζωγραφισμένη, και η σύγκριση
             πρέπει να το πιάσει.
  ΑΛΛΑΖΕΙ    μηχανή με άλλη: πληρώνεται η νέα, τα μισά της παλιάς πίσω.
  ΟΧΙ        χωρίς υλικά το FIRE δεν αλλάζει τίποτα και το πλαίσιο είναι
             κόκκινο· κατάλυμα (δωμάτιο χωρίς μηχανές) δεν ανοίγει.
  SPACE      μία επιλογή σε όλες τις υποδοχές, οκτώ αλλαγές μαζί στη λίστα·
             και με υλικά για τρεις: οι τρεις πρώτες, και ο ήχος της άρνησης.
  ΔΕΙΧΝΕΙ    σε κάθε υποδοχή η επιλογή στέκεται σε ό,τι έχει ήδη μέσα (fit_pick)
             — στο θερμοκήπιο, η κλάση του φυτού. ΑΡΝΗΤΙΚΟ: το fit_pick μία
             θέση μετά. Το βήμα 55 βρήκε ότι κανένας έλεγχος δεν το έπιανε: το
             pick() εδώ πατά πάνω-κάτω ΑΠΟ όπου κι αν σταθεί η επιλογή, οπότε
             ένα λάθος fit_pick απλώς έκανε περισσότερα πατήματα.
  ΕΡΓΟΤΑΞΙΟ  θερμοκήπιο εξοπλισμένο ΠΡΙΝ τελειώσει, με καλλιέργειες ανά
             υποδοχή: τίποτα δεν ζωγραφίζεται πάνω στο εργοτάξιο, και τα φυτά
             φαίνονται όταν τελειώσει.
  ΧΡΟΝΟΣ     ο χειρότερος γύρος του βρόχου όταν βγαίνει μηχανή.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/vasilhs/cpcemu")

import balance as B                                                # noqa: E402
import test_game as T                                              # noqa: E402
import test_reveal as R                                            # noqa: E402
from cpc import (JOY_FIRE, KEY_SPACE, KEY_RIGHT, KEY_LEFT,         # noqa: E402
                 KEY_UP, KEY_DOWN)

I_DOME_M, I_DOME_L = 1, 2
RM_GREEN, RM_FACTORY = 3, 4              # θέσεις στο rm_list, όχι R_*
UI_LOOK, UI_FIT = 0, 5
NO_MACH = 255
PEN_NO, PEN_OK = 8, 9
SFX_DENY, SFX_BUILD, SFX_N = 2, 3, 9      # src/sound.asm
FT_CLS = 250                             # src/fit.asm: άμυλο, λαχανικά, βότανα, δέντρο
# fit_cost (src/fit.asm): μέταλλο, βιοπλαστικό ανά μηχανή
COST = {0: (8, 2), 1: (8, 2), 2: (8, 2), 3: (10, 4), 4: (10, 4), 5: (10, 4),
        6: (6, 2), 7: (8, 2), 8: (8, 2), 9: (8, 2), 10: (4, 2), 11: (4, 2)}
STOCK = 500                              # κάτω από το ταβάνι 600: η επιστροφή
                                         # κόβεται εκεί (ec_add_stock)
check = R.check


class Fit:
    """Τα πλήκτρα του παίκτη, με το ρολόι του R.Game να τρέχει."""

    def __init__(self, G, sym, g):
        self.G, self.m, self.sym, self.g = G, G.m, sym, g

    def key(self, k):
        self.m.key_down(k)
        self.G.run(5 * 20_000)
        self.m.key_up(k)
        self.G.run(8 * 20_000)

    def joy(self, mask):
        self.m.set_joystick_type(1)
        self.m.joystick(mask)
        self.G.run(4 * 20_000)
        self.m.joystick(0)
        self.G.run(10 * 20_000)
        self.m.set_joystick_type(0)

    def fire(self):
        self.joy(JOY_FIRE)

    def esc(self):
        self.joy(0x20)

    def peek(self, n, k=0):
        return self.m.peek(self.sym[n] + k)

    def look(self):
        for _ in range(3):
            if self.peek("UI_STATE") == UI_LOOK:
                return
            self.esc()
        assert self.peek("UI_STATE") == UI_LOOK, "δεν γύρισε στο LOOK"

    def enter(self, at):
        """LOOK, κέρσορας στο (cur_hx, cur_hy), FIRE."""
        self.look()
        self.m.poke(self.sym["CUR_HX"], at[0] & 0xFF)
        self.m.poke(self.sym["CUR_HY"], at[1] & 0xFF)
        self.fire()
        return self.peek("UI_STATE") == UI_FIT

    def lst(self):
        return [self.peek("FIT_LST", k) for k in range(self.peek("FIT_C"))]

    def slot(self, s):
        for _ in range(16):
            if self.peek("FIT_S") == s:
                return
            self.key(KEY_RIGHT if (s - self.peek("FIT_S")) % 8 <= 4 else KEY_LEFT)
        assert self.peek("FIT_S") == s, f"η υποδοχή δεν κλείδωσε: {self.peek('FIT_S')}"

    def pick(self, i):
        c = self.peek("FIT_C")
        for _ in range(2 * c):
            d = (i - self.peek("FIT_I")) % c
            if not d:
                return
            self.key(KEY_DOWN if d <= c // 2 else KEY_UP)
        assert self.peek("FIT_I") == i, f"η επιλογή δεν κλείδωσε: {self.peek('FIT_I')}"

    def put(self, s, i):
        self.slot(s)
        self.pick(i)
        self.fire()

    def stocks(self):
        w = lambda a: self.m.peek(a) | (self.m.peek(a + 1) << 8)
        return w(self.g + 6), w(self.g + 8)

    def set_stocks(self, fe, bi):
        for k, v in ((3, fe), (4, bi)):
            self.m.poke(self.g + 2 * k, v & 0xFF)
            self.m.poke(self.g + 2 * k + 1, v >> 8)

    def rec(self, d):
        return B.dome_rec(self.m, self.sym, d)

    def sounds(self, act, *args):
        """Οι ήχοι που ΞΕΚΙΝΗΣΑΝ όσο έτρεχε το act(*args). Το snd_play βάζει
        τον δείκτη ενός καναλιού (sn_st + 1) στο πρώτο βήμα του εφέ — ένα byte
        μετά το εφέ, που είναι sn_tab[k] bytes μετά το sn_tab + k —
        και μετά από ένα πάτημα το εφέ έχει ήδη σβήσει — γι' αυτό κοιτάζεται σε
        κάθε βήμα του ρολογιού, και μόνο όσο κρατά το act."""
        m, sym = self.m, self.sym
        w = lambda a: m.peek(a) | (m.peek(a + 1) << 8)
        tab = sym["SN_TAB"]
        start = {tab + k + m.peek(tab + k) + 1: k for k in range(SFX_N)}
        heard, raw = [], m.run_us
        last = [w(sym["SN_ST"] + 4 * c + 1) for c in range(3)]

        def run_us(us):
            raw(us)
            for c in range(3):
                a = w(sym["SN_ST"] + 4 * c + 1)
                if a != last[c]:
                    last[c] = a
                    if a in start:
                        heard.append(start[a])
        m.run_us = run_us
        try:
            act(*args)
        finally:
            m.run_us = raw
        return heard


def picks(F, node, slots, code=lambda v: v):
    """Οι υποδοχές όπου το fit_pick ΔΕΝ στάθηκε σε ό,τι έχουν ήδη μέσα:
    [(υποδοχή, περιεχόμενο, επιλογή)]. `code` = ο κωδικός της λίστας για ένα
    περιεχόμενο (στο θερμοκήπιο, η κλάση του φυτού)."""
    lst, bad = F.lst(), []
    for s in slots:
        F.slot(s)                            # κάθε βήμα καλεί το fit_pick
        have, i = F.rec(node)[8 + s], F.peek("FIT_I")
        got = lst[i] if i < len(lst) else f"θέση {i}"
        if got != code(have):
            bad.append((s, have, got))
    return bad


def truth(G, what, skip=()):
    pic, ref = G.truth()
    ok, how = R.shape(pic, ref, skip=skip)
    check(ok, f"{what}: η οθόνη είναι η πλήρης σχεδίαση — {how}")
    return ok


def slot_rect(F):
    """Οι θέσεις (x + 80*y) της τρέχουσας υποδοχής στην οθόνη: μέσα στο
    πλαίσιο που της έβαλε το fit_show (gh_bx = x - 1, gh_by = y - 2)."""
    sx = lambda v: v - 65536 if v > 32767 else v
    x = sx(F.peek("GH_BX") | (F.peek("GH_BX", 1) << 8)) + 1
    y = sx(F.peek("GH_BY") | (F.peek("GH_BY", 1) << 8)) + 2
    return {(y + j) * 80 + x + i for j in range(22) for i in range(6)
            if 0 <= x + i < 80 and 0 <= y + j < 160}


def factory(sym, g):
    G = R.Game(sym, g)
    F = Fit(G, sym, g)
    F.set_stocks(STOCK, STOCK)
    tx, ty = B.clear_spots(8, 1, dome=True)[0]
    G.camera(tx - 6, ty - 1)                 # ο θόλος στις στήλες 6-13
    at = (2 * tx + 8, 2 * ty + 8)
    B.build(G.m, sym, I_DOME_L, g + 6, at=at, room=RM_FACTORY, fit=False)
    node = G.m.peek(sym["BD_NODE"])
    rec = F.rec(node)
    check(rec[4] == 1 and rec[8:16] == [NO_MACH] * 8,
          f"εργοστάσιο L στο {(tx, ty)}: κόμβος {node}, εργοτάξιο, άδειο")
    check(R.finish(G, node), f"και τελείωσε (κατάσταση {G.state(node)[0]})")
    G.settle()

    # --- ΜΠΑΙΝΕΙ ---------------------------------------------------------
    check(F.enter(at) and F.peek("FIT_D") == node and F.peek("FIT_N") == 8,
          f"FIRE πάνω του: εξοπλισμός (κατάσταση {F.peek('UI_STATE')}, θόλος "
          f"{F.peek('FIT_D')}, {F.peek('FIT_N')} υποδοχές)")
    lst = F.lst()
    check(lst == [NO_MACH, 1, 2, 3, 5, 7],
          f"η λίστα: ΑΔΕΙΟ και ό,τι δέχεται το εργοστάσιο, σίδερο πρώτο — {lst}")
    on = G.still()
    plan = [1, 2, 3, 4, 5, 1, 2, 3]          # θέσεις στη λίστα
    want = [lst[i] for i in plan]
    fe0, bi0 = F.stocks()
    for s, i in enumerate(plan):
        F.put(s, i)
    fe1, bi1 = F.stocks()
    pay = (sum(COST[k][0] for k in want), sum(COST[k][1] for k in want))
    rec = F.rec(node)
    # ΣΤΑΜΑΤΗΜΕΝΕΣ (βήμα 99): περιμένουν τα υλικά τους και τον μηχανικό, με
    # υγεία κάτω από 128 — 7 στο FIT, λιγότερο αν έφτασε ήδη κάποιο φορτίο
    # όσο πατιούνταν τα πλήκτρα (tests/test_install.py).
    check(rec[8:16] == want and all(0 < h < 128 for h in rec[16:24]),
          f"οκτώ μηχανές μπήκαν: {rec[8:16]}, υγείες {rec[16:24]} (περιμένουν)")
    check((fe0 - fe1, bi0 - bi1) == pay,
          f"και πληρώθηκαν χωριστά: μέταλλο -{fe0 - fe1}, βιοπλαστικό "
          f"-{bi0 - bi1} (fit_cost: {pay})")
    truth(G, "μετά τις οκτώ")

    # --- ΒΓΑΙΝΕΙ: πρώτα το ΑΡΝΗΤΙΚΟ ----------------------------------------
    # Το `jr z,dhm_vac` γίνεται nop nop: η άδεια υποδοχή πέφτει στο
    # ob_mach_one, που δεν ζωγραφίζει τίποτα για NO_MACH — η παλιά μηχανή
    # μένει στην οθόνη.
    at_jr = next(sym["DH_MACH"] + k for k in range(24)
                 if F.peek("DH_MACH", k) == 0x3C and F.peek("DH_MACH", k + 1) == 0x28)
    jr = (G.m.peek(at_jr + 1), G.m.peek(at_jr + 2))
    G.m.poke(at_jr + 1, 0)
    G.m.poke(at_jr + 2, 0)
    F.put(2, 0)
    pic, ref = G.truth()
    same, _ = R.shape(pic, ref)
    check(not same, "ΑΡΝΗΤΙΚΟ: χωρίς το dhv_rect η μηχανή μένει στην οθόνη, "
                   "και η σύγκριση το πιάνει")
    G.m.poke(at_jr + 1, jr[0])
    G.m.poke(at_jr + 2, jr[1])
    F.put(2, 3)                              # πίσω τα όπλα
    G.full()

    # --- ΒΓΑΙΝΕΙ, κανονικά -----------------------------------------------
    rect = slot_rect(F)
    before = G.play()
    fe0, bi0 = F.stocks()
    F.slot(2)
    F.pick(0)
    c = G.canary(79, 0)
    G.iters = []
    F.fire()
    worst = G.worst()
    fe1, bi1 = F.stocks()
    rec = F.rec(node)
    check(rec[10] == NO_MACH and rec[18] == 0,
          f"ΑΔΕΙΟ στην υποδοχή 2: {rec[10]}, υγεία {rec[18]}")
    check((fe1 - fe0, bi1 - bi0) == (5, 2),
          f"και τα μισά πίσω: μέταλλο +{fe1 - fe0}, βιοπλαστικό +{bi1 - bi0} "
          f"(όπλα 10/4)")
    after = G.play()
    moved = sum(1 for k in rect if before[k] != after[k])
    check(moved > 20, f"η μηχανή έφυγε από την οθόνη: {moved} από {len(rect)} "
                      f"bytes της υποδοχής άλλαξαν")
    check(G.alive(c), "χωρίς πλήρη σχεδίαση: το κανάρινι ζει")
    truth(G, "μετά το ΑΔΕΙΟ", skip={79})          # το κανάρινι
    check(worst < 120, f"ο χειρότερος γύρος του FIRE ήταν {worst:.0f} ms")

    # --- ΑΛΛΑΖΕΙ ----------------------------------------------------------
    fe0, bi0 = F.stocks()
    F.slot(0)
    F.pick(4)                                # σίδερο -> ρομπότ
    heard = F.sounds(F.fire)
    fe1, bi1 = F.stocks()
    rec = F.rec(node)
    check(rec[8] == 5 and (fe0 - fe1, bi0 - bi1) == (10 - 4, 4 - 1)
          and heard == [SFX_BUILD],
          f"σίδερο -> ρομπότ: υποδοχή 0 = {rec[8]}, μέταλλο -{fe0 - fe1}, "
          f"βιοπλαστικό -{bi0 - bi1} (10/4 μείον τα μισά του 8/2), ήχοι {heard}")

    # --- ΟΧΙ ----------------------------------------------------------------
    F.set_stocks(3, STOCK)
    F.slot(1)
    F.pick(3)                                # όπλα, 10 μέταλλο
    # Το gh_pen κρατά το byte γεμίσματος, hud_solid[pen] (gh_setpen).
    pen, red = F.peek("GH_PEN"), F.peek("HUD_SOLID", PEN_NO)
    heard = F.sounds(F.fire)
    rec = F.rec(node)
    check(rec[9] == 2 and F.stocks()[0] == 3 and pen == red
          and red != F.peek("HUD_SOLID", PEN_OK) and heard == [SFX_DENY],
          f"με 3 μέταλλο τα όπλα δεν μπαίνουν: υποδοχή 1 = {rec[9]}, μέταλλο "
          f"{F.stocks()[0]}, πλαίσιο #{pen:02X} (κόκκινο #{red:02X}), ήχοι {heard}")
    F.set_stocks(STOCK, STOCK)

    # --- SPACE ----------------------------------------------------------------
    F.pick(1)                                # σίδερο
    F.key(KEY_SPACE)
    G.run(400_000)
    rec = F.rec(node)
    check(rec[8:16] == [1] * 8 and F.peek("FIT_S") == 1,
          f"SPACE: σίδερο σε όλες — {rec[8:16]}, ο κέρσορας έμεινε στην "
          f"υποδοχή {F.peek('FIT_S')}")
    truth(G, "μετά το SPACE")

    # --- SPACE με υλικά για τρεις: από την πρώτη, όσες φτάνουν -------------
    # 25 μέταλλο, όπλα 10 το ένα και 4 πίσω από κάθε σίδερο: 19, 13, 7, και
    # η τέταρτη δεν πληρώνεται. Οι άλλες μένουν όπως ήταν, και ο ήχος λέει
    # «όχι όλες» — ΜΟΝΟ η άρνηση.
    F.set_stocks(25, STOCK)
    F.pick(3)
    heard = F.sounds(F.key, KEY_SPACE)
    G.run(400_000)
    rec = F.rec(node)
    check(rec[8:16] == [3] * 3 + [1] * 5 and F.stocks()[0] == 7
          and heard == [SFX_DENY],
          f"SPACE με 25 μέταλλο: {rec[8:16]}, μέταλλο {F.stocks()[0]}, ήχοι "
          f"{heard} (όπλα στις τρεις πρώτες, 7 μένουν, η άρνηση)")
    F.set_stocks(STOCK, STOCK)

    # --- ΔΕΙΧΝΕΙ: η επιλογή στέκεται σε ό,τι έχει η υποδοχή ------------------
    bad = picks(F, node, (3, 2, 7, 0))
    check(not bad, f"σε κάθε υποδοχή η επιλογή δείχνει ό,τι έχει μέσα"
                   + (f" — ΟΧΙ: {bad}" if bad else ""))
    # ΑΡΝΗΤΙΚΟ: το `sub` που κάνει τη διεύθυνση του cpir θέση, ένα λιγότερο —
    # η επιλογή στέκεται μία θέση μετά.
    at = next(sym["FIT_PICK"] + k for k in range(64)
              if F.peek("FIT_PICK", k) == 0xD6
              and F.peek("FIT_PICK", k + 2) == 0x32
              and F.peek("FIT_PICK", k + 3) == sym["FIT_I"] & 0xFF
              and F.peek("FIT_PICK", k + 4) == sym["FIT_I"] >> 8)
    sub = G.m.peek(at + 1)
    G.m.poke(at + 1, (sub - 1) & 0xFF)
    bad = picks(F, node, (3, 2, 7, 0))
    G.m.poke(at + 1, sub)
    check(bool(bad), f"ΑΡΝΗΤΙΚΟ: με το fit_pick μία θέση μετά, ο έλεγχος το "
                     f"πιάνει — {bad or 'ΔΕΝ ΠΙΑΣΤΗΚΕ'}")
    F.slot(1)
    F.look()
    G.go(on)

    # --- ΟΧΙ: κατάλυμα ------------------------------------------------------
    # Ο θόλος 1 της αρχικής αποικίας, κέντρο (16, 0) σε μισά tiles.
    check(not F.enter((16, 0)) and F.peek("UI_STATE") == UI_LOOK,
          f"το κατάλυμα δεν έχει τι να δεχτεί: κατάσταση {F.peek('UI_STATE')}")
    return G, F


def greenhouse(sym, g):
    G = R.Game(sym, g)
    F = Fit(G, sym, g)
    F.set_stocks(STOCK, STOCK)
    tx, ty = B.clear_spots(8, 1, dome=True)[0]
    G.camera(tx - 6, ty - 2)
    at = (2 * tx + 6, 2 * ty + 6)
    B.build(G.m, sym, I_DOME_M, g + 6, at=at, room=RM_GREEN, fit=False)
    node = G.m.peek(sym["BD_NODE"])
    check(G.state(node)[0] == 1, f"θερμοκήπιο M στο {(tx, ty)}: εργοτάξιο")
    check(F.enter(at) and F.lst() == [NO_MACH, 254, 250, 251, 252, 253],
          f"και ο εξοπλισμός του ανοίγει ΑΠΟ ΤΩΡΑ: ΑΔΕΙΟ, ΜΙΚΤΟ, άμυλο, "
          f"λαχανικά, βότανα, δέντρο — {F.lst()}")
    on = G.still()
    fe0, _ = F.stocks()
    for s, i in enumerate([2, 2, 3, 5]):     # άμυλο, άμυλο, λαχανικά, δέντρο
        F.put(s, i)
    rec = F.rec(node)
    # Η ποικιλία βγαίνει από την υποδοχή: άμυλο 0 + 0, 0 + 1, λαχανικά 5 + 2.
    check(rec[8:12] == [0, 1, 7, 11] and fe0 - F.stocks()[0] == 8
          and rec[16:20] == [200] * 4,
          f"καλλιέργειες ανά υποδοχή: {rec[8:12]} (άμυλο, άμυλο, λαχανικά, "
          f"δέντρο), μέταλλο -{fe0 - F.stocks()[0]}, υγείες {rec[16:20]} (τα φυτά "
          f"μένουν άμεσα, βήμα 99)")
    truth(G, "εξοπλισμός πάνω σε εργοτάξιο: τίποτα δεν ζωγραφίστηκε")
    # Η κλάση από την ποικιλία (rooms.asm): 0-4 άμυλο, 5-9 λαχανικά, 10, 11.
    cls = lambda v: FT_CLS + (0 if v < 5 else 1 if v < 10 else v - 8)
    bad = picks(F, node, (3, 2, 0), code=cls)
    check(not bad, f"και η επιλογή στέκεται στην κλάση του φυτού κάθε υποδοχής"
                   + (f" — ΟΧΙ: {bad}" if bad else ""))
    F.slot(0)
    F.pick(1)                                # ΜΙΚΤΟ σε όλες
    F.key(KEY_SPACE)
    G.run(400_000)
    rec = F.rec(node)
    check(rec[8:12] == [0, 5, 10, 11],
          f"ΜΙΚΤΟ: η παλιά εναλλαγή του rm_plants — {rec[8:12]}")
    F.look()
    G.go(on)
    check(R.finish(G, node), "και τελείωσε")
    G.settle()
    truth(G, "τα φυτά φάνηκαν στην ολοκλήρωση (dh_built)")


def main():
    sym, g = T.build()
    factory(sym, g)
    greenhouse(sym, g)
    if R.FAIL:
        print(f"\n{len(R.FAIL)} ΑΠΟΤΥΧΙΕΣ")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
