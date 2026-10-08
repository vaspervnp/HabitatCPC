#!/usr/bin/env python3
"""Το μενού χωρίς γράμματα: το SPACE και το M στο LOOK, στο main.sna (DESIGN §9.1,
§9.3· βήμα 80, κουμπιά από το βήμα 84).

Η πρόζα λέει:

  SPACE      εστιάζει στη μπάρα των ομάδων (ΘΟΛΟΙ, ΔΙΑΔΡΟΜΟΣ, ΕΝΕΡΓΕΙΑ, ΠΟΡΟΙ,
             ΜΕΤΑΦΟΡΑ, ΔΙΑΧΕΙΡΙΣΗ, ?), στην ομάδα του αντικειμένου που
             διαλέχτηκε τελευταίο· το διαλεγμένο λευκό. Οι σειρές 3-4:
               σειρά 3   < POWER        >  FIRE=GO ESC=BACK
               σειρά 4   MAKE AND STORE POWER
             με την ταχύτητα στις στήλες 35-39 όπως πάντα.
  M          η ΔΙΑΧΕΙΡΙΣΗ: INFO, FIT, SAVE, LOAD, CENTRE, ?, στο INFO. Το FIT
             κόκκινο εκεί όπου το FIRE στο LOOK δεν θα άνοιγε τον εξοπλισμό.
  ΜΕΤΑΦΟΡΑ   το SHIP κόκκινο εκτός αν υπάρχει αίθουσα ελέγχου, πίστα και
             κανένα πλοίο στον δρόμο.
  αριστερά/δεξιά  το προηγούμενο/επόμενο, κυκλικά· ο κέρσορας και η κάμερα
             μένουν
  FIRE, SPACE     το διαλεγμένο, σαν να πατήθηκε το γράμμα του: INFO -> οι
             σειρές του I, FIT -> ο εξοπλισμός, SAVE/LOAD -> η επιλογή θέσης,
             CENTRE -> ο κέρσορας στο (0, 0)· και το C της ΜΕΤΑΦΟΡΑΣ -> η
             γραμμή του πλοίου (βήμα 91), όπου το FIRE ή το SPACE -> το πλοίο
             και το μήνυμά του (η σειρά 4 κενή)
  ESC        πίσω στο LOOK

ΤΟ FIT ΔΕΝ ΕΛΕΓΧΕΤΑΙ ΑΠΟ ΤΗΝ ΠΡΟΖΑ ΤΟΥ ΚΩΔΙΚΑ ΑΛΛΑ ΑΠΟ ΤΟ ΙΔΙΟ ΤΟ ΠΑΙΧΝΙΔΙ: σε
κάθε θόλο της αρχής και σε θόλους γραμμένους στον πίνακα με κάθε δωμάτιο και
μέγεθος, πρώτα FIRE στο LOOK (ανοίγει ο εξοπλισμός ή όχι;), μετά M (το FIT
κόκκινο ή όχι;). Και σε tiles χωρίς θόλο. Το SHIP στους οκτώ συνδυασμούς των
τριών όρων.

Το παιχνίδι είναι σε παύση, και ένα μήνυμα που κρατά τις σειρές δεν
καθυστερεί το μενού (ui_ask, βήμα 79).

ΚΑΙ Η ΕΠΙΛΟΓΗ ΘΕΣΗΣ ΔΙΣΚΟΥ ΣΕ ΠΑΥΣΗ (βήμα 80): S ή L, και τρία δεξιά, και η
σειρά 3 λέει κάθε φορά τη θέση.

Αρνητικά, με τον κώδικα πειραγμένο στη μνήμη: το FIT παντού πράσινο, το SHIP
πράσινο με πλοίο στον δρόμο, το SPACE που δεν διαλέγει, η σειρά 4 που μένει
μετά το πλοίο, το μενού χωρίς δική του κατάσταση στον διαλογέα (το
αριστερά/δεξιά κουνά τον κέρσορα), η θέση δίσκου που αλλάζει χωρίς να φανεί,
το SPACE που ξεχνά την ομάδα.
"""
import os, random, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import test_info as TI                                   # noqa: E402
import test_bar as TB                                    # noqa: E402
import barread as B                                      # noqa: E402
import cpc                                               # noqa: E402
import scene as S                                        # noqa: E402

FAIL = []
UI_LOOK, UI_MENU, UI_SLOT, UI_FIT, UI_INFO, UI_ACT = 0, 1, 4, 5, 6, 7


def check(ok, msg):
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ ") + msg)
    if not ok:
        FAIL.append(msg)


def equs():
    """Οι διευθύνσεις του πλοίου και του δωματίου ελέγχου, από τα αρχεία."""
    lay = {}
    for line in open(os.path.join(ROOT, "build", "layout.asm"), encoding="utf-8"):
        p = line.split()
        if len(p) >= 3 and p[1] == "equ":
            lay[p[0]] = int(p[2].lstrip("#"), 16)
    const = open(os.path.join(ROOT, "src", "const.asm"), encoding="utf-8").read()

    def ec(name):
        return lay["G_econ_state"] + int(re.search(rf"^{name}\s+equ G_econ_state \+ (\d+)",
                                                   const, re.M).group(1))
    ctl = int(re.search(r"^R_CONTROL\s+equ (\d+)", const, re.M).group(1))
    return {"CTL": lay["G_room_n"] + ctl, "PAD": ec("EC_PADNODE"), "SHIP": ec("EC_SHSTATE")}


class Game(TI.Game):
    def __init__(self, sym, patch=()):
        super().__init__(sym, patch)
        self.E = equs()

    def tap(self, key, n=1):
        """Δώδεκα frames μετά: η μπάρα ζωγραφίζεται δύο κουμπιά ανά frame."""
        for _ in range(n):
            self.m.key_down(key)
            self.m.run_frames(3)
            self.m.key_up(key)
            self.m.run_frames(12)

    def bar(self):
        return B.bar(self.m, self.sym)

    def state(self):
        return self.m.peek(self.sym["UI_STATE"])

    def stick(self, bits):
        m = self.m
        m.set_joystick_type(1)
        m.joystick(bits)
        m.run_frames(4)
        m.joystick(0)
        m.run_frames(8)
        m.set_joystick_type(0)

    def rows(self):
        return TI.same(self.hud(3)[:35]), TI.same(self.hud(4))

    def ship_ok(self):
        p = self.m.peek
        return p(self.E["CTL"]) != 0 and p(self.E["PAD"]) != 255 and p(self.E["SHIP"]) == 0

    def ship(self, ctl, pad, busy):
        self.m.poke(self.E["CTL"], ctl)
        self.m.poke(self.E["PAD"], pad)
        self.m.poke(self.E["SHIP"], busy)


# Η μπάρα των ομάδων με το ? (η λίστα του SPACE), και της ΔΙΑΧΕΙΡΙΣΗΣ
FOCUS = B.GROUPS + ["help"]
MANAGE = ["info", "fit", "save", "load", "centre", "help"]
TEXT = dict(zip([n for n, _ in B.BUTTONS], TB.HELP))


def rows(name):
    """(σειρά 3, σειρά 4) του μενού, με το `name` διαλεγμένο."""
    t, d = TEXT[name]
    return TI.same(f"< {t:13s}>  FIRE=GO ESC=BACK "), TI.same(f"{d:40s}")


def focus_bar(name):
    return B.want_groups(lit=name)


def manage_bar(name, fit):
    bar = B.want_group("manage", lit={name} if name != "help" else (), red=() if fit else {"fit"})
    if name == "help":
        bar[15] = ("help", B.WHITE)
    return bar


LOOK = (TI.same(f"{TI.LOOK3:35s}"), " " * 40)


def run(sym, a, patch=(), quick=False):
    """-> το πρώτο λάθος ή None, και πόσες θέσεις ελέγχθηκαν."""
    G = Game(sym, patch)
    m = G.m
    rnd = random.Random(80)
    TI.scene(G, a, rnd)
    fps = TI.footprints(G, a)
    pad0 = m.peek(G.E["PAD"])

    # --- 1. το FIT, από το ίδιο το παιχνίδι ---
    tiles = [(f[0] + f[2] // 2, f[1] + f[3] // 2) for f in fps if f[4] == "d"]
    tiles += [(f[0], f[1]) for f in fps if f[4] == "s"][:3]
    tiles += [(-30, -30), (63, 63)]
    if quick:
        tiles = tiles[::3]
    n = 0
    for tx, ty in tiles:
        G.cursor(tx, ty)
        G.stick(0x10)                                   # FIRE στο LOOK
        fit = G.state() == UI_FIT
        if fit:
            G.stick(0x20)
        if G.state() != UI_LOOK:
            return f"tile ({tx}, {ty}): μετά το FIRE και το ESC, κατάσταση {G.state()}", n
        G.tap("M")
        got, exp = (G.rows(), G.bar()), (rows("info"), manage_bar("info", fit))
        if G.state() != UI_ACT or got != exp:
            return (f"tile ({tx}, {ty}), FIRE {'ανοίγει' if fit else 'δεν ανοίγει'} τον "
                    f"εξοπλισμό: «{got[0][0]}», «{B.show(got[1])}», η πρόζα λέει "
                    f"«{exp[0][0]}», «{B.show(exp[1])}»"), n
        G.tap(cpc.KEY_ESC)
        if G.state() != UI_LOOK or G.rows() != LOOK or G.bar() != B.want_groups():
            return f"μετά το ESC: κατάσταση {G.state()}, «{G.rows()[0]}»", n
        n += 1

    # --- 2. το SHIP: οι οκτώ συνδυασμοί, στη μπάρα της ΜΕΤΑΦΟΡΑΣ ---
    G.cursor(-30, -30)
    for ctl in (0, 1):
        for pad in (255, pad0 if pad0 != 255 else 3):
            for busy in (0, 1):
                G.ship(ctl, pad, busy)
                G.tap("T")
                ok = ctl and pad != 255 and not busy
                exp = B.want_group("transport", lit={"airlock"}, red=() if ok else {"ship"})
                if G.bar() != exp:
                    return (f"έλεγχος {ctl}, πίστα {pad}, πλοίο {busy}: «{B.show(G.bar())}», "
                            f"η πρόζα λέει «{B.show(exp)}»"), n
                G.tap(cpc.KEY_ESC)
                n += 1

    # --- 3. αριστερά/δεξιά, πάνω σε θόλο της αρχής ---
    d0 = next(f for f in fps if f[4] == "d")
    home = (d0[0] + 1, d0[1] + 1)
    G.ship(1, pad0 if pad0 != 255 else 3, 0)
    G.cursor(*home)
    cur = (m.peek(sym["CUR_HX"]), m.peek(sym["CUR_HY"]), m.peek(sym["CAM_TX"]),
           m.peek(sym["CAM_TY"]))
    G.tap(cpc.KEY_SPACE)
    sel = B.GROUPS.index(B.GROUPS[[0, 0, 0, 1, 2, 2, 2, 3, 3, 4, 4][m.peek(sym["UI_SEL"])]])
    for key, step in [(cpc.KEY_RIGHT, 1)] * (len(FOCUS) + 1) + [(cpc.KEY_LEFT, -1)] * (len(FOCUS) + 2):
        G.tap(key)
        sel = (sel + step) % len(FOCUS)
        name = FOCUS[sel]
        if G.rows() != rows(name) or G.bar() != focus_bar(name):
            return (f"μετά από {'δεξιά' if step > 0 else 'αριστερά'}: «{G.rows()[0]}» / "
                    f"«{G.rows()[1].rstrip()}», «{B.show(G.bar())}», η πρόζα λέει το {name}"), n
        now = (m.peek(sym["CUR_HX"]), m.peek(sym["CUR_HY"]), m.peek(sym["CAM_TX"]),
               m.peek(sym["CAM_TY"]))
        if now != cur:
            return f"ο κέρσορας ή η κάμερα κουνήθηκαν στο μενού: {cur} -> {now}", n
        n += 1
    G.tap(cpc.KEY_ESC)

    # --- 4. κάθε ενέργεια της ΔΙΑΧΕΙΡΙΣΗΣ, με FIRE και με SPACE· και το πλοίο ---
    for k, name in enumerate(MANAGE[:-1] + ["ship"]):
        for how in ("FIRE", "SPACE"):
            G.ship(1, pad0 if pad0 != 255 else 3, 0)
            far = (home[0] + 3, home[1] + 2)
            G.cursor(*(far if name == "centre" else home))
            if name == "ship":
                # Το κουμπί ανοίγει τη γραμμή του πλοίου (βήμα 91), και το
                # FIRE ή το SPACE εκεί το καλούν (tests/test_crew.py).
                G.tap("T")
                G.tap("C")                              # γράμμα: δεν έχει βελάκι
                if G.state() != UI_ACT or "WRK" not in G.hud(4):
                    return f"ship: το κουμπί έδειξε «{G.rows()[0]}» / «{G.hud(4)}»", n
            else:
                G.tap("M")
                for _ in range(k):
                    G.tap(cpc.KEY_RIGHT)
                if G.rows() != rows(name):
                    return f"{name}: το μενού λέει «{G.rows()[0]}»", n
            if how == "FIRE":
                G.stick(0x10)
            else:
                G.tap(cpc.KEY_SPACE)
            m.run_frames(40)                            # το CENTRE ξαναζωγραφίζει
            st, (r3, r4) = G.state(), G.rows()          # όλο το κάδρο
            if name == "fit":
                ok = st == UI_FIT
            elif name == "info":
                ok = st == UI_INFO and (r3, r4) == TI.want(G, fps, *home)
            elif name == "ship":
                ok = (st == UI_LOOK and m.peek(G.E["SHIP"]) != 0
                      and r3.startswith(TI.same("COLONIST SHIP CALLED")) and not r4.strip())
            elif name in ("save", "load"):
                ok = (st == UI_SLOT and m.peek(sym["SL_MODE"]) == (name == "load")
                      and r3.startswith(TI.same(f"{name.upper()} ")))
            else:
                ok = (st == UI_LOOK and m.peek(sym["CUR_HX"]) == 0 and m.peek(sym["CUR_HY"]) == 0
                      and (r3, r4) == LOOK)
            if not ok:
                return (f"{name} με {how}: κατάσταση {st}, «{r3}» / «{r4.rstrip()}»"), n
            if st != UI_LOOK:
                G.tap(cpc.KEY_ESC)
            if G.state() != UI_LOOK:
                return f"μετά το {name} και το ESC: κατάσταση {G.state()}", n
            n += 1

    # --- 5. πίσω από μήνυμα ---
    G.cursor(*home)
    m.poke(sym["UI_HOLD"], 6)
    G.tap("M")
    if G.rows() != rows("info"):
        return f"με μήνυμα στις σειρές, το M έδειξε «{G.rows()[0]}»", n
    G.tap(cpc.KEY_ESC)
    n += 1

    # --- 6. S και L, σε παύση: η επιλογή θέσης φαίνεται, και η θέση που
    # αλλάζει φαίνεται αμέσως ---
    for key, word in (("S", "SAVE TO SLOT"), ("L", "LOAD FROM SLOT")):
        G.tap(key)
        start = m.peek(sym["SL_PICK"])                  # η θέση μένει από πριν
        for slot in [(start + i) % 3 + 1 for i in range(4)]:
            exp = TI.same(f"{word:14s} {slot}")
            if G.state() != UI_SLOT or G.rows()[0][:16] != exp:
                return (f"{key}, θέση {slot}: κατάσταση {G.state()}, «{G.rows()[0]}», η "
                        f"πρόζα λέει «{exp}»"), n
            G.tap(cpc.KEY_RIGHT)
            n += 1
        G.tap(cpc.KEY_ESC)
    return None, n


def main():
    sym, _ = TG.build()
    a = S.Assets()
    why, n = run(sym, a)
    check(why is None, f"το μενού σε {n} θέσεις: FIT κόκκινο όπου το FIRE δεν ανοίγει τον "
                       f"εξοπλισμό, SHIP στους οκτώ συνδυασμούς, αριστερά/δεξιά κυκλικά χωρίς "
                       f"να κουνηθεί ο κέρσορας, κάθε ενέργεια με FIRE και με SPACE, ESC πίσω, "
                       f"και πίσω από μήνυμα"
          + (f" — {why}" if why else ""))

    m = Game(sym).m

    def find(at, pat, span=200):
        i = m.read_ram(sym[at], span).find(bytes(pat))
        assert i >= 0, f"δεν βρέθηκε το {pat} στο {at}"
        return sym[at] + i

    fit = find("BWW_ACT", [0x3A, sym["AC_FIT"] & 255, sym["AC_FIT"] >> 8, 0xB7, 0x20], 40) + 4
    ship = find("BAR_SHIPOK", [0xB7, 0x20], 40)
    neg = [("το FIT παντού πράσινο", [(fit, 0x18)]),
           ("το SHIP πράσινο με πλοίο στον δρόμο", [(ship + 2, 0)]),
           ("το SPACE που δεν διαλέγει", [(find("ACT_FIRE", [0xE6, 0x50]) + 1, 0x10)]),
           ("τη σειρά 4 μετά το πλοίο", [(find("AC_SHIP", [0x06, 40]) + 1, 0)]),
           ("το μενού έξω από τον διαλογέα", [(find("UIT_STATE", [0xFE, UI_ACT]) + 1, 99)]),
           ("τη θέση δίσκου που αλλάζει χωρίς να φανεί",
            [(find("USL_LR", [0xC3, sym["UI_PANEL"] & 255, sym["UI_PANEL"] >> 8], 30), 0xC9)]),
           ("το SPACE που ξεχνά την ομάδα", [(find("AC_OPEN", [0x7E, 0x21], 20), 0xAF)])]
    for label, patch in neg:
        why, _ = run(sym, a, patch, quick=True)
        check(why is not None, f"ΑΡΝΗΤΙΚΟ: με {label} αποτυγχάνει"
                               + (f" ({why[:110]})" if why else ""))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
