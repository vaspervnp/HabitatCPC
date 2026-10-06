#!/usr/bin/env python3
"""TOO FAR: διάδρομος ανάμεσα σε θόλους 64 tiles ή περισσότερο, στο main.sna
(DESIGN §9.4, βήμα 81).

Ως το βήμα 80 το cr_side αφαιρούσε τα κέντρα — μισά tiles, -128..127 — σε 8
bits, και πέρα από ±127 η διαφορά αναδιπλωνόταν: η διαδρομή σχεδιαζόταν προς
την άλλη μεριά, και όση έμενε στον κόσμο περνούσε τον έλεγχο. Η πρόζα λέει
τώρα:

  θόλοι που απέχουν 64 tiles ή περισσότερο σε έναν άξονα δεν παίρνουν
  διάδρομο, όποιος κι αν διαλέχτηκε πρώτος· η σειρά 4 του LINK λέει
  «TOO FAR», το φάντασμα είναι κόκκινο (ui_bad = 2), και το FIRE δεν χτίζει
  τίποτα. Στα 63 tiles η διαδρομή υπάρχει. Ενα σχήμα που δεν βγαίνει (η ζώνη
  «σχεδόν διαγώνιος») λέει, όπως πριν, «NO ROUTE FROM THERE» (ui_bad = 1).

Θόλοι γραμμένοι στον πίνακα, μακριά από την αποικία: ο A, ο B στα 64 tiles
ακριβώς στο x (από τον A το -64 χωρά σε 8 bits, από τον B όχι — και οι δύο
σειρές επιλογής), ο E στα 65 στο y, ο C στα 63, και ένας D σε «σχεδόν
διαγώνιο» που η αναφορά (tools/route.py) δεν δρομολογεί. Ο κέρσορας μπαίνει
πάνω τους με poke και το φάντασμα ξαναϋπολογίζεται με ui_hide/ui_show, όπως
σε κάθε βήμα.

Αρνητικά, με τον κώδικα πειραγμένο στη μνήμη: η σειρά 4 με το NO ROUTE και για
το μακριά, το ln_plan που δεν ξεχωρίζει τα δύο, και ο δρομολογητής χωρίς τους
τρεις ελέγχους (ο δρομολογητής του βήματος 80).
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import test_info as TI                                   # noqa: E402
import cpc                                               # noqa: E402
import route                                             # noqa: E402

FAIL = []
PROBE = 0x3E00
I_CORR, UI_LINK = 3, 3
CORR_BYTES = 96 * 5


def check(ok, msg):
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ ") + msg)
    if not ok:
        FAIL.append(msg)


def corr_tbl():
    for line in open(os.path.join(ROOT, "build", "layout.asm"), encoding="utf-8"):
        p = line.split()
        if p and p[0] == "G_corr_tbl":
            return int(p[2].lstrip("#"), 16)
    raise SystemExit("δεν βρέθηκε το G_corr_tbl")


# Κέντρα σε μισά tiles, μέγεθος S (πλευρά 4 tiles): ζυγά, όπως στο παιχνίδι.
A = (-100, -20)
B = (A[0] + 128, A[1])                   # 64 tiles στο x
E = (A[0], A[1] + 130)                   # 65 tiles στο y
C = (A[0] + 126, A[1] + 40)              # 63 tiles: διαδρομή υπάρχει


def near_none():
    """Ενας D κοντά στον A που η αναφορά δεν δρομολογεί, όχι μακριά."""
    for dx in range(-60, 61, 2):
        for dy in range(-60, 61, 2):
            d = (A[0] + dx, A[1] + dy)
            if abs(dx) >= 12 and abs(dy) >= 12 and max(abs(v + 1) for v in d) <= 120 \
                    and route.plan(*A, 0, *d, 0) is None \
                    and not route.too_far(*A, *d):
                return d
    raise SystemExit("κανένας D")


class Game(TI.Game):
    def __init__(self, sym, patch=()):
        super().__init__(sym, patch)
        self.slots = {}
        free = [d for d in range(64) if not self.b6[TI.DOMES - 0x4000 + 24 * d + 4]]
        self.D = near_none()
        for k, (name, c) in enumerate((("A", A), ("B", B), ("E", E), ("C", C),
                                       ("D", self.D))):
            b = TI.DOMES - 0x4000 + 24 * free[k]
            for i, v in enumerate((c[0] & 255, c[1] & 255, 0, 4, 2, 255)):
                self.b6[b + i] = v
            self.slots[name] = (free[k], c)
        self.corr = corr_tbl() - 0x4000

    def stick(self, bits):
        m = self.m
        m.set_joystick_type(1)
        m.joystick(bits)
        m.run_frames(4)
        m.joystick(0)
        m.run_frames(8)
        m.set_joystick_type(0)

    def probe(self, names):
        m, top = self.m, self.sym["MAIN_LOOP"]
        for _ in range(40000):
            if top <= m.pc < top + 13:
                break
            m.run_us(50)
        code = []
        for n in names:
            code += [0xCD, self.sym[n] & 0xFF, self.sym[n] >> 8]
        m.run_code(PROBE, bytes(code + [0x18, 0xFE]), frames=100)
        m.set_pc(top)

    def on(self, name):
        """Ο κέρσορας στο κέντρο του θόλου."""
        c = self.slots[name][1]
        self.m.poke(self.sym["CUR_HX"], c[0] & 255)
        self.m.poke(self.sym["CUR_HY"], c[1] & 255)

    def link(self):
        """LOOK -> SPACE SPACE -> ο διάδρομος -> FIRE: LINK, χωρίς αφετηρία."""
        G, m = self, self.m
        G.tap(cpc.KEY_SPACE, 2)
        for _ in range(14):
            if m.peek(self.sym["UI_SEL"]) == I_CORR:
                break
            G.tap(cpc.KEY_RIGHT)
        G.stick(0x10)
        return m.peek(self.sym["UI_STATE"]) == UI_LINK

    def pick(self, frm):
        """Αφετηρία ο θόλος frm (ESC πρώτα: χωρίς αφετηρία)."""
        if self.m.peek(self.sym["LN_A"]) != 255:
            self.stick(0x20)
        self.on(frm)
        self.stick(0x10)
        return self.m.peek(self.sym["LN_A"]) == self.slots[frm][0]

    def aim(self, to):
        self.on(to)
        self.probe(["UI_HIDE", "UI_SHOW"])
        return self.m.peek(self.sym["UI_BAD"]), TI.same(self.hud(4))


FAR = TI.same(f"{'TOO FAR':40s}")
NOROUTE = TI.same(f"{'NO ROUTE FROM THERE':40s}")


def run(sym, patch=()):
    """-> το πρώτο λάθος ή None, και πόσες περιπτώσεις."""
    G = Game(sym, patch)
    m = G.m
    if not G.link():
        return "το LINK δεν άνοιξε", 0
    n = 0
    for frm, to in (("A", "B"), ("B", "A"), ("A", "E"), ("E", "A")):
        if not G.pick(frm):
            return f"ο {frm} δεν έγινε αφετηρία (ln_a = {m.peek(sym['LN_A'])})", n
        bad, r4 = G.aim(to)
        if bad != 2 or r4 != FAR:
            return f"{frm} -> {to}: ui_bad {bad}, «{r4.rstrip()}», η πρόζα λέει 2, «TOO FAR»", n
        before = bytes(G.b6[G.corr:G.corr + CORR_BYTES])
        G.stick(0x10)                                    # FIRE: τίποτα
        if bytes(G.b6[G.corr:G.corr + CORR_BYTES]) != before \
                or m.peek(sym["UI_STATE"]) != UI_LINK \
                or m.peek(sym["LN_A"]) != G.slots[frm][0]:
            return f"{frm} -> {to}: το FIRE έχτισε ή άλλαξε κατάσταση", n
        n += 1
    for frm, to in (("A", "C"), ("C", "A")):
        G.pick(frm)
        bad, r4 = G.aim(to)
        if r4 in (FAR, NOROUTE) or m.peek(sym["CR_N"]) == 0:
            return f"{frm} -> {to}, 63 tiles: «{r4.rstrip()}», cr_n {m.peek(sym['CR_N'])}", n
        n += 1
    for frm, to in (("A", "D"), ("D", "A")):
        G.pick(frm)
        bad, r4 = G.aim(to)
        if bad != 1 or r4 != NOROUTE:
            return f"{frm} -> {to} (σχήμα): ui_bad {bad}, «{r4.rstrip()}»", n
        n += 1
    return None, n


def main():
    sym, _ = TG.build()
    why, n = run(sym)
    check(why is None, f"TOO FAR σε {n} περιπτώσεις: 64 tiles στο x από τις δύο μεριές, 65 "
                       f"στο y, ui_bad = 2 και κανένας διάδρομος με το FIRE· τα 63 tiles "
                       f"δρομολογούνται· η «σχεδόν διαγώνιος» λέει NO ROUTE"
          + (f" — {why}" if why else ""))

    m = Game(sym).m

    def find(at, pat, span=60):
        i = m.read_ram(sym[at], span).find(bytes(pat))
        assert i >= 0, f"δεν βρέθηκε το {pat} στο {at}"
        return sym[at] + i

    # t_far = x_t_far - TEXT_IMG + G_text, και TEXT_IMG = #C000 + G_text - #4000
    far, ln2 = sym["X_T_FAR"] - 0x8000, sym["X_T_LN2"] - 0x8000
    assert find("UIP_LN", [0x21, ln2 & 255, ln2 >> 8], 40), "το t_ln2 δεν βγαίνει έτσι"
    code = m.read_ram(sym["CR_SIDE"], 80)
    pe = [sym["CR_SIDE"] + i for i in range(79) if code[i:i + 2] == bytes([0x96, 0xEA])]
    assert len(pe) == 2, f"sub (hl) · jp pe: {len(pe)} φορές"
    neg = [("τη σειρά 4 που λέει NO ROUTE και για το μακριά",
            [(find("UIP_LN", [0x21, far & 255, far >> 8], 40) + 1, ln2 & 255),
             (find("UIP_LN", [0x21, far & 255, far >> 8], 40) + 2, ln2 >> 8)]),
           ("το ln_plan που δεν ξεχωρίζει", [(find("LNP_NONE", [0x3C], 6), 0)]),
           ("τον δρομολογητή του βήματος 80, χωρίς κανένα όριο",
            [(at + k, 0) for at in pe for k in (1, 2, 3)]                 # jp pe x 2
            + [(find("CR_SIDE", [0xCB, 0x77, 0xC2], 120) + k, 0) for k in (2, 3, 4)])]
    for label, patch in neg:
        why, _ = run(sym, patch)
        check(why is not None, f"ΑΡΝΗΤΙΚΟ: με {label} αποτυγχάνει"
                               + (f" ({why[:100]})" if why else ""))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
