#!/usr/bin/env python3
"""Τα κουμπιά της κάτω λωρίδας και η οθόνη βοήθειας, στο main.sna (DESIGN §9.3).

Η πρόζα λέει:

  LOOK         οι έξι ομάδες στις θέσεις 0-5 (ΘΟΛΟΙ D, ΔΙΑΔΡΟΜΟΣ R, ΕΝΕΡΓΕΙΑ P,
               ΠΟΡΟΙ E, ΜΕΤΑΦΟΡΑ T, ΔΙΑΧΕΙΡΙΣΗ M) και το ? στη 15, πράσινα. Η
               γραμμή 176 μαύρη.
  ομάδα        το γράμμα της ανοίγει τα δικά της στην ίδια μπάρα, με την ίδια
               λευκή στη θέση 0: MENU, με το αντικείμενο που ήταν διαλεγμένο αν
               ανήκει εκεί, αλλιώς το πρώτο της. Το ίδιο γράμμα την κλείνει (από
               MENU, PLACE ή LINK). Ο ΔΙΑΔΡΟΜΟΣ είναι μόνος του: MENU με τον
               διάδρομο, και η μπάρα των ομάδων με τον ΔΙΑΔΡΟΜΟ λευκό. Η
               ΔΙΑΧΕΙΡΙΣΗ ανοίγει το μενού των ενεργειών (test_act).
  αντικείμενο  το γράμμα του: αυτό, και κατευθείαν PLACE· λευκό στη μπάρα.
  μέγεθος      S, M, L στους ΘΟΛΟΥΣ: αλλάζει χωρίς να αλλάξει κατάσταση.
  δωμάτιο      το γράμμα του: αυτό και PLACE — αν χωρά στο μέγεθος. Οσα δεν
               χωρούν είναι κόκκινα και το γράμμα τους δεν κάνει τίποτα. Χωρά
               όποιο δεν θέλει μηχανές ή έχει μία που χωρά (assets: room_machines,
               machine_rules). Ενα δωμάτιο που έπαψε να χωρά δίνει τη θέση του
               στο επόμενο που χωρά.
  πλήκτρα      μόνο της μπάρας που φαίνεται. Ενα πάτημα κάνει ένα πράγμα, όσο κι
               αν κρατηθεί — και όταν η μπάρα αλλάξει από κάτω του.
  βελάκια      στο MENU ο κατάλογος όπως ως τώρα, και η μπάρα ακολουθεί.
  SPACE SPACE  ξανανοίγει την τελευταία ομάδα στο ίδιο αντικείμενο.
  κάμερα       η μπάρα μετακινείται με το βήμα κάμερας και ξαναζωγραφίζεται
               μετά από άλμα (H).
  ?            η οθόνη βοήθειας: όλη Mode 1, τα 34 κουμπιά (33 ως το βήμα 92:
               ο έμπορος μετά το πλοίο) σε τρεις στήλες των
               δώδεκα (οι ομάδες λευκές), δεξιά το όνομα λευκό και από κάτω η
               γραμμή του πράσινη, και η σειρά 24. Ενα πλήκτρο γυρίζει πίσω, και
               δεν κάνει τίποτα άλλο: ίδια κατάσταση, ίδια μπάρα, ίδιο κάδρο.
  ταχύτητα     τα 1-4 και το H δουλεύουν όπως πριν (ο δρόμος τους άλλαξε).

ΚΑΙ ΤΟ ΚΟΣΤΟΣ: ένα ui_tick χωρίς πλήκτρα, ανά κατάσταση, και ένα ui_panel που
δεν βρίσκει αλλαγή, ΟΧΙ πιο αργά από το βήμα 83 (μετρημένα εκεί: LOOK 1.455,
MENU 1.259, PLACE 1.252, ui_panel 344 µs). Και η πλήρης μπάρα, και η βοήθεια.

Αρνητικά, με τον κώδικα πειραγμένο στη μνήμη: χωρίς σάρωση γραμμάτων, ακμή
χωρίς μνήμη του κρατημένου πλήκτρου, μπάρα που αγνοεί το σβήσιμο των λωρίδων,
δωμάτια που δεν κοκκινίζουν, κουμπιά χωρίς γράμμα, βοήθεια που δεν περιμένει να
αφεθεί το πλήκτρο, τα 1-4 με λάθος μάσκα, το FIRE του LOOK χαμένο, το H χαμένο.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import test_info as TI                                   # noqa: E402
import barread as B                                      # noqa: E402
import hudread                                           # noqa: E402
import cpc                                               # noqa: E402
from sprites import load_map, load_bin                   # noqa: E402

FAIL = []
UI_LOOK, UI_MENU, UI_PLACE, UI_LINK, UI_FIT, UI_ACT = 0, 1, 2, 3, 5, 7
# Ο κατάλογος δωματίων (src/rooms.asm, rm_list) σε κωδικούς R_* (src/const.asm)
ROOMS = ["oxygen", "canteen", "quarters", "greenhouse", "factory", "lab", "medbay",
         "control", "storage", "lounge"]
R_CODE = [4, 3, 2, 5, 8, 9, 10, 1, 6, 11]
R_GREENHS = 5
# Η οθόνη βοήθειας: όνομα και γραμμή ανά κουμπί, με τη σειρά τους
HELP = [("DOMES", "LIVE AND WORK INSIDE"), ("SMALL DOME", "4X4, ANY ROOM"),
        ("MEDIUM DOME", "6X6, NO OXYGEN"), ("LARGE DOME", "8X8, NO OXYGEN"),
        ("OXYGEN", "AIR FOR THE COLONY"), ("CANTEEN", "COOKS MEALS"),
        ("QUARTERS", "BEDS TO SLEEP IN"), ("GREENHOUSE", "GROWS PLANTS"),
        ("FACTORY", "METAL AND PARTS"), ("LAB", "MEAT AND CHIPS"),
        ("MEDBAY", "HEALS THE SICK"), ("CONTROL", "MORE COLONISTS"),
        ("STORAGE", "ROOM FOR MORE GOODS"), ("LOUNGE", "KEEPS MORALE UP"),
        ("CORRIDOR", "LINKS TWO DOMES"), ("POWER", "MAKE AND STORE POWER"),
        ("SOLAR PANEL", "POWER BY DAY"), ("WIND TURBINE", "POWER FROM WIND"),
        ("COLLECTOR", "STORES POWER"), ("RESOURCES", "WATER AND ORE"),
        ("EXTRACTOR", "WATER FROM GROUND"), ("MINE", "ORE FROM A VEIN"),
        ("TRANSPORT", "COMING AND GOING"), ("AIRLOCK", "WAY IN AND OUT"),
        ("LANDING PAD", "SHIPS LAND HERE"), ("SHIP", "CALL NEW COLONISTS"),
        ("TRADE", "UP TAKES, DOWN GIVES"),                  # βήμα 93
        ("MANAGE", "INFO, DISC, VIEW"), ("INFO", "WHAT IS HERE"),
        ("FIT", "MACHINES IN A DOME"), ("SAVE", "SAVE TO DISC"),
        ("LOAD", "LOAD FROM DISC"), ("CENTRE", "BACK TO THE MIDDLE"),
        ("HELP", "THIS SCREEN")]
FOOT = "THE LETTER ON A BUTTON IS ITS KEY.   PRESS ANY KEY TO GO BACK"
# µs, μετρημένα στο βήμα 83 (ταβάνι: όχι πιο αργά) και στο 84 (ταβάνι: +2-7%).
# «μπάρα» είναι ένα frame της: ΤΟ ΠΟΛΥ δύο κουμπιά, και τα άλλα μετά (bar_more).
OLD = {"LOOK": 1455, "MENU": 1259, "PLACE": 1252, "ui_panel": 344}
CEIL = {"LOOK": 1000, "MENU": 875, "PLACE": 1050, "ui_panel": 305,
        "κουμπί": 3100, "μπάρα": 10000, "βοήθεια": 400000}


def check(ok, msg):
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ ") + msg)
    if not ok:
        FAIL.append(msg)


def fits_table():
    """fits[δωμάτιο][μέγεθος], από τα assets και τον κανόνα της πρόζας."""
    smap, blob = load_map(), load_bin()
    rm = smap["room_machines"]
    mr = smap["machine_rules"]
    out = []
    for code in R_CODE:
        mask = blob[rm.off + 2 * code] | blob[rm.off + 2 * code + 1] << 8
        row = []
        for size in range(3):
            if code == R_GREENHS or not mask:
                row.append(True)
            else:
                row.append(any(mask >> k & 1 and blob[mr.off + k] >> size & 1 for k in range(12)))
        out.append(row)
    return out


class Game(TI.Game):
    def tap(self, key, n=1):
        """Δώδεκα frames μετά το πάτημα: η μπάρα ζωγραφίζεται δύο κουμπιά ανά
        frame (bar_more), και μια ολόκληρη θέλει οκτώ."""
        for _ in range(n):
            self.m.key_down(key)
            self.m.run_frames(3)
            self.m.key_up(key)
            self.m.run_frames(12)

    def bar(self):
        return B.bar(self.m, self.sym)

    def st(self):
        return self.m.peek(self.sym["UI_STATE"])

    def sel(self):
        return self.m.peek(self.sym["UI_SEL"])

    def rsel(self):
        return self.m.peek(self.sym["BD_RSEL"])

    def stick(self, bits):
        m = self.m
        m.set_joystick_type(1)
        m.joystick(bits)
        m.run_frames(4)
        m.joystick(0)
        m.run_frames(8)
        m.set_joystick_type(0)


def run(sym, patch=(), quick=False):
    """-> (το πρώτο λάθος ή None, πόσα ελέγχθηκαν)."""
    G = Game(sym, patch)
    m = G.m
    FIT = fits_table()
    n = 0

    def domes(size, room, red=None):
        bad = [ROOMS[r] for r in range(10) if not FIT[r][size]]
        return B.want_group("domes", lit={["small", "medium", "large"][size], ROOMS[room]},
                            red=bad)

    def expect(what, state, bar, sel=None):
        if G.st() != state or (sel is not None and G.sel() != sel) or G.bar() != bar:
            return (f"{what}: κατάσταση {G.st()}, ui_sel {G.sel()}, μπάρα «{B.show(G.bar())}», "
                    f"η πρόζα λέει {state}, {sel}, «{B.show(bar)}»")
        return None

    # --- 1. LOOK ---
    if G.bar() != B.want_groups():
        return f"LOOK: «{B.show(G.bar())}»", n
    if any(B.line176(m, sym)):
        return "η γραμμή 176 δεν είναι μαύρη", n
    n += 1

    # --- 2. ΘΟΛΟΙ: μέγεθος, δωμάτιο, κόκκινα ---
    G.tap("D")
    room = G.rsel()
    why = expect("D", UI_MENU, domes(0, room), 0)
    if why:
        return why, n
    n += 1
    for size, key in ((1, "M"), (2, "L"), (0, "S")):
        G.tap(key)
        if not FIT[room][size]:
            room = next(r % 10 for r in range(room + 1, room + 11) if FIT[r % 10][size])
        why = expect(f"μέγεθος {key}", UI_MENU, domes(size, room), size)
        if why:
            return why, n
        n += 1
    rooms = list(range(10)) if not quick else [3, 0, 7]
    size = 0
    for r in rooms:
        for sz, key in ((0, "S"), (1, "M"), (2, "L")):
            if quick and sz:
                continue
            G.tap(key)
            if not FIT[room][sz]:
                room = next(q % 10 for q in range(room + 1, room + 11) if FIT[q % 10][sz])
            size = sz
            state0 = G.st()
            G.tap(B.BUTTONS[B.ID[ROOMS[r]]][1])
            if FIT[r][sz]:
                room, state = r, UI_PLACE
            else:
                state = state0                          # κόκκινο: τίποτα
            why = expect(f"{ROOMS[r]} στο μέγεθος {key}", state, domes(sz, room), sz)
            if why:
                return why, n
            n += 1
    G.tap("D")                                          # ανοιχτή: κλείνει
    why = expect("D ξανά", UI_LOOK, B.want_groups())
    if why:
        return why, n

    # --- 3. οι άλλες ομάδες και τα αντικείμενά τους ---
    for gk, group, items in (("P", "power", [("S", 4), ("T", 5), ("C", 6)]),
                             ("E", "resources", [("X", 7), ("M", 8)]),
                             ("T", "transport", [("A", 9), ("P", 10)])):
        G.tap(gk)
        first = items[0][1]
        why = expect(gk, UI_MENU, B.want_group(group, lit={B.ITEM_BTN[first]},
                                               red=_ship_red(G, sym, group)), first)
        if why:
            return why, n
        n += 1
        for ik, sel in items:
            G.tap(ik)
            why = expect(f"{gk} {ik}", UI_PLACE,
                         B.want_group(group, lit={B.ITEM_BTN[sel]}, red=_ship_red(G, sym, group)),
                         sel)
            if why:
                return why, n
            n += 1
        # ένα γράμμα που δεν είναι σε αυτή τη μπάρα δεν κάνει τίποτα
        other = "D" if gk != "D" else "P"
        G.tap(other)
        if G.st() != UI_PLACE or G.sel() != items[-1][1]:
            return f"στη μπάρα {group} το {other} άλλαξε κάτι: {G.st()}, {G.sel()}", n
        G.tap(gk)                                       # κλείνει
        if G.st() != UI_LOOK:
            return f"το {gk} δεν έκλεισε την ομάδα του: {G.st()}", n
        # ...και ανοίγει στο ίδιο αντικείμενο
        G.tap(gk)
        if G.sel() != items[-1][1]:
            return f"το {gk} δεν θυμήθηκε το {items[-1][1]}: {G.sel()}", n
        G.tap(cpc.KEY_ESC)
        n += 1

    # --- 4. ΔΙΑΔΡΟΜΟΣ: MENU, FIRE -> LINK, R κλείνει ---
    G.tap("R")
    why = expect("R", UI_MENU, B.want_groups(lit="corridor"), 3)
    if why:
        return why, n
    G.stick(0x10)
    why = expect("R και FIRE", UI_LINK, B.want_groups(lit="corridor"), 3)
    if why:
        return why, n
    G.tap("R")
    why = expect("R στο LINK", UI_LOOK, B.want_groups())
    if why:
        return why, n
    n += 1

    # --- 5. κρατημένο πλήκτρο: ένα πράγμα. Το E ανοίγει τους ΠΟΡΟΥΣ από τη
    # θέση 3, και στη νέα μπάρα το E είναι στη θέση 0 — κρατημένο, δεν κλείνει ---
    m.key_down("E")
    seen = []
    for _ in range(25):                                 # ΚΑΘΕ frame: η ισοτιμία
        m.run_frames(1)                                 # ενός άνοιξε-έκλεισε δεν
        seen.append(G.st())                             # κρύβεται
    m.key_up("E")
    m.run_frames(6)
    opened = seen.index(UI_MENU) if UI_MENU in seen else None
    if opened is None or any(s != UI_MENU for s in seen[opened:]) or G.st() != UI_MENU:
        return f"κρατημένο E: καταστάσεις {seen} (άνοιξε και ξανάκλεισε;)", n
    n += 1

    # --- 6. τα βελάκια στο MENU: ο κατάλογος, και η μπάρα ακολουθεί ---
    G.tap(cpc.KEY_ESC)
    G.tap("D")
    G.tap("L")                                          # ui_sel 2
    for key, sel, bar in ((cpc.KEY_RIGHT, 3, B.want_groups(lit="corridor")),
                          (cpc.KEY_RIGHT, 4, B.want_group("power", lit={"solar"})),
                          (cpc.KEY_LEFT, 3, B.want_groups(lit="corridor"))):
        G.tap(key)
        why = expect("βελάκι στο MENU", UI_MENU, bar, sel)
        if why:
            return why, n
        n += 1
    G.tap(cpc.KEY_ESC)

    # --- 7. SPACE SPACE: η τελευταία ομάδα, το ίδιο αντικείμενο ---
    G.tap("E")
    G.tap("M")                                          # ορυχείο, PLACE
    G.tap(cpc.KEY_ESC)
    G.tap(cpc.KEY_ESC)
    G.tap(cpc.KEY_SPACE)
    if G.st() != UI_ACT or G.bar() != B.want_groups(lit="resources"):
        return f"SPACE: κατάσταση {G.st()}, «{B.show(G.bar())}»", n
    G.tap(cpc.KEY_SPACE)
    why = expect("SPACE SPACE", UI_MENU, B.want_group("resources", lit={"mine"}), 8)
    if why:
        return why, n
    G.tap(cpc.KEY_ESC)
    n += 1

    # --- 8. ταχύτητα, H, FIRE στο LOOK ---
    for key, spd in (("4", 4), ("3", 2), ("2", 1), ("1", 0)):
        G.tap(key)
        if m.peek(sym["UI_SPD"]) != spd:
            return f"το {key} έδωσε ταχύτητα {m.peek(sym['UI_SPD'])}, όχι {spd}", n
    fit = False
    for f in TI.footprints(G, _assets()):
        if f[4] != "d":
            continue
        G.cursor(f[0] + f[2] // 2, f[1] + f[3] // 2)
        G.stick(0x10)
        if G.st() == UI_FIT:
            fit = True
            G.stick(0x20)
            break
    if not fit:
        return "το FIRE στο LOOK δεν άνοιξε τον εξοπλισμό σε κανέναν θόλο", n
    n += 1

    # --- 9. η μπάρα ακολουθεί το βήμα κάμερας ---
    G.cursor(0, 0)
    cam0 = m.peek(sym["CAM_TX"])
    for _ in range(14):
        G.tap(cpc.KEY_RIGHT)
        if m.peek(sym["CAM_TX"]) != cam0:
            break
    if m.peek(sym["CAM_TX"]) == cam0:
        return "η κάμερα δεν κουνήθηκε", n
    if G.bar() != B.want_groups():
        return f"μετά το βήμα κάμερας η μπάρα: «{B.show(G.bar())}»", n
    n += 1
    # --- ...και το H, που τώρα ΕΙΝΑΙ άλμα κάμερας: οι λωρίδες σβήνουν ---
    G.tap("H")
    m.run_frames(30)
    if (m.peek(sym["CUR_HX"]), m.peek(sym["CUR_HY"]), m.peek(sym["CAM_TX"])) != (0, 0, cam0):
        return "το H δεν έφερε κέρσορα και κάμερα στο κέντρο", n
    if G.bar() != B.want_groups():
        return f"μετά το άλμα της κάμερας (H) η μπάρα: «{B.show(G.bar())}»", n
    n += 1

    # --- 10. η βοήθεια ---
    G.tap("D")
    before = _play(m, sym)
    bar0 = G.bar()
    m.key_down("/")
    m.run_frames(40)
    if m.mode != 1:
        return f"στη βοήθεια το Gate Array είναι σε Mode {m.mode}", n
    why = _help(m, sym, quick)
    if why:
        return why, n
    m.key_up("/")
    m.run_frames(10)
    # ΚΡΑΤΗΜΕΝΟ ΠΕΡΙΣΣΟΤΕΡΟ ΑΠΟ ΟΣΟ ΚΡΑΤΑ Η ΕΠΑΝΑΣΧΕΔΙΑΣΗ (~0,4 s): ένα σύντομο
    # πάτημα έχει αφεθεί πριν γυρίσει ο έλεγχος στο παιχνίδι ούτως ή άλλως
    m.key_down("D")                                     # κλείνει τη βοήθεια ΜΟΝΟ
    m.run_frames(45)
    m.key_up("D")
    m.run_frames(40)
    if G.st() != UI_MENU or G.bar() != bar0:
        return (f"μετά τη βοήθεια: κατάσταση {G.st()}, «{B.show(G.bar())}» "
                f"(το D που την έκλεισε έκλεισε και τους ΘΟΛΟΥΣ;)"), n
    after = _play(m, sym)
    if after != before:
        diff = sum(a != b for a, b in zip(after, before))
        return f"μετά τη βοήθεια το κάδρο διαφέρει σε {diff} bytes", n
    n += 1
    return None, n


def _ship_red(G, sym, group):
    """Τα κόκκινα της ΜΕΤΑΦΟΡΑΣ: το πλοίο χωρίς αίθουσα ελέγχου, πίστα ή με
    πλοίο ήδη· ο έμπορος (βήμα 93) όσο δεν είναι προσγειωμένος έμπορος."""
    if group != "transport":
        return ()
    p = G.m.peek
    E = _equs()
    ok = p(E["CTL"]) != 0 and p(E["PAD"]) != 255 and p(E["SHIP"]) == 0
    mer = p(E["SHIP"]) == 2 and p(E["SHIP"] + 1) == 1
    return (set() if ok else {"ship"}) | (set() if mer else {"trade"})


_EQ = None
_AS = None


def _equs():
    global _EQ
    if _EQ is None:
        import test_act as TA
        _EQ = TA.equs()
    return _EQ


def _assets():
    global _AS
    if _AS is None:
        import scene
        _AS = scene.Assets()
    return _AS


def _play(m, sym):
    """Τα bytes του κάδρου (γραμμές 16-175), από το cam_p."""
    ram = m.read_ram(0xC000, 0x4000)
    cp = hudread.cam_p(m, sym)
    out = bytearray()
    for y in range(16, 176):
        base = cp + ((y >> 3) - 2) * 80
        out += bytes(ram[(y & 7) * 0x800 + ((base + x) & 0x7FF)] for x in range(80))
    return bytes(out)


def _cells(ram, cp, row, col, n):
    """n κελιά της σειράς οθόνης row από τη στήλη col: bytes(8) το καθένα."""
    off = -160 + 80 * row + col
    return [bytes(ram[ln * 0x800 + ((cp + off + c) & 0x7FF)] for ln in range(8))
            for c in range(n)]


def _text(cells, pen=3):
    g = hudread.glyphs()
    if pen == 2:
        g = {bytes(b & 0x0F for b in k): v for k, v in g.items()}
    return "".join(g.get(c, "#") for c in cells)


def _help(m, sym, quick):
    ram = m.read_ram(0xC000, 0x4000)
    cp = hudread.cam_p(m, sym)
    ks = range(len(B.BUTTONS)) if not quick else (0, 13, 14, 25, 32)
    for k in ks:
        col, row = divmod(k, 12)
        off = -160 + 160 * row + 27 * col
        name = B.BUTTONS[k][0]
        exp = (name, B.WHITE if name in B.GROUPS else B.GREEN)
        got = B.read_off(ram, cp, off)
        if got != exp:
            return f"βοήθεια, κουμπί {k}: {got}, η πρόζα λέει {exp}"
        t1 = _text(_cells(ram, cp, 2 * row, 27 * col + 6, 20)).rstrip()
        t2 = _text(_cells(ram, cp, 2 * row + 1, 27 * col + 6, 20), pen=2).rstrip()
        w1, w2 = (TI.same(s) for s in HELP[k])
        if (TI.same(t1.replace("#", " ")).rstrip(), TI.same(t2.replace("#", " ")).rstrip()) != (w1, w2):
            return f"βοήθεια, κουμπί {k}: «{t1}» / «{t2}», η πρόζα λέει «{w1}» / «{w2}»"
    foot = _text(_cells(ram, cp, 24, 0, len(FOOT)))
    if TI.same(foot) != TI.same(FOOT):
        return f"βοήθεια, σειρά 24: «{foot}»"
    return None


# --- κόστος ------------------------------------------------------------------
# πάνω από τον κώδικα της τράπεζας 0: το main.asm τον κρατά ως το #3D60 (βήμα 91· ως τότε #3C00)
PROBE = 0x3D60


def call_us(m, sym, target, reps=3):
    assert sym["ZZ_BANK0_END"] <= PROBE, "ο κώδικας έφτασε στο PROBE"
    on, ml = sym["IS_ON"], sym["MAIN_LOOP"]
    best = None
    for _ in range(reps):
        # di, ld sp, call, και στο σημάδι jr $: με βήματα των 20 us το PC
        # δεν θα πατούσε ποτέ ακριβώς πάνω του
        code = [0xF3, 0x31, 0x00, 0x01, 0xCD, target & 255, target >> 8, 0x18, 0xFE,
                0xCD, on & 255, on >> 8, 0xC3, ml & 255, ml >> 8]
        m.write_ram(PROBE, bytes(code))
        for _ in range(400):                            # στην αναμονή του vsync
            if ml < m.pc < ml + 16:
                break
            m.run_us(50)
        m.set_pc(PROBE)
        n = 0
        while m.pc != PROBE + 7 and n < 2000000:
            m.run_us(1 if n < 3000 else 20)
            n += 1 if n < 3000 else 20
        best = n if best is None else min(best, n)
        m.set_pc(PROBE + 9)
        m.run_frames(3)
    return best


def costs(sym):
    G = Game(sym)
    m = G.m
    out = {"LOOK": call_us(m, sym, sym["UI_TICK"]),
           "ui_panel": call_us(m, sym, sym["UI_PANEL"])}
    G.tap("D")                                          # ΘΟΛΟΙ: 15 γράμματα, τα περισσότερα
    out["MENU"] = call_us(m, sym, sym["UI_TICK"])
    G.tap("G")
    out["PLACE"] = call_us(m, sym, sym["UI_TICK"])
    # ένα κουμπί, και ένα frame της μπάρας στη χειρότερη θέση: οι ΘΟΛΟΙ (δέκα
    # rm_fits στο bar_want) με υπογραφή και θέσεις άκυρες, όπως μετά από άλμα
    m.write_ram(PROBE + 0x40, bytes([0x21, 0x40, 0x06, 0x3E, 7, 0x0E, 0,
                                     0xC3, sym["SL_DRAW"] & 255, sym["SL_DRAW"] >> 8]))
    out["κουμπί"] = call_us(m, sym, PROBE + 0x40)
    m.poke(sym["BSG_WAS"], 255)
    for s in range(16):
        m.poke(sym["BS_ID"] + s, 254)
    out["μπάρα"] = call_us(m, sym, sym["BAR_SYNC"], reps=1)
    left = m.peek(sym["BS_PEND"])
    m.run_frames(12)
    out["μπάρα"] = out["μπάρα"] if left else 10 ** 9     # τα υπόλοιπα σε επόμενα frames
    G.tap(cpc.KEY_ESC)
    G.tap(cpc.KEY_ESC)
    # η βοήθεια ως την αναμονή του πλήκτρου
    m.write_ram(PROBE, bytes([0xF3, 0x31, 0x00, 0x01, 0xCD, sym["HP_SHOW"] & 255,
                              sym["HP_SHOW"] >> 8, 0xC3, sym["MAIN_LOOP"] & 255,
                              sym["MAIN_LOOP"] >> 8]))
    for _ in range(400):
        if sym["MAIN_LOOP"] < m.pc < sym["MAIN_LOOP"] + 16:
            break
        m.run_us(50)
    m.set_pc(PROBE)
    n = 0
    while not (sym["HP_WAIT"] <= m.pc < sym["HP_UP"]) and n < 2000000:
        m.run_us(20)
        n += 20
    out["βοήθεια"] = n
    return out


def main():
    sym, _ = TG.build()
    why, n = run(sym)
    check(why is None, f"η μπάρα σε {n} βήματα: ομάδες, μεγέθη, τα δέκα δωμάτια σε τρία "
                       f"μεγέθη με τα κόκκινα, αντικείμενα, ΔΙΑΔΡΟΜΟΣ, κρατημένο πλήκτρο, "
                       f"βελάκια, SPACE SPACE, 1-4, H, FIRE, βήμα κάμερας, βοήθεια"
          + (f" — {why}" if why else ""))

    c = costs(sym)
    print("\nκόστος (µs):  " + "  ".join(f"{k} {v}" + (f" (βήμα 83: {OLD[k]})" if k in OLD else "")
                                          for k, v in c.items()))
    slow = [f"{k} {c[k]} > {CEIL[k]}" for k in CEIL if c[k] > CEIL[k]]
    check(not slow, "κανένα ui_tick χωρίς πλήκτρα, κανένα ui_panel χωρίς αλλαγή πιο αργό από "
                    "το βήμα 83, και η μπάρα και η βοήθεια κάτω από το ταβάνι τους"
          + (f": {', '.join(slow)}" if slow else ""))

    m = Game(sym).m

    def find(at, pat, span=300):
        i = m.read_ram(sym[at], span).find(bytes(pat))
        assert i >= 0, f"δεν βρέθηκε το {[hex(b) for b in pat]} στο {at}"
        return sym[at] + i

    def w(a):
        return [a & 255, a >> 8]

    scan = find("UIT_STATE", [0xCD] + w(sym["BK_SCAN"]), 40)
    held = find("BK_HIT", [0xED, 0x53] + w(sym["BK_HELD"]), 40)
    gen = find("BSC_GO", [0x21] + w(sym["BS_GEN"]) + [0xBE, 0x28], 120) + 4
    fits = find("BWD_LP", [0xCD] + w(sym["RM_FITS"]), 10)
    letter = find("SLD_PL", [0xFE, 10], 10)
    up = find("HP_WAIT", [0xCD] + w(sym["HP_UP"]), 20)
    neg = [("χωρίς σάρωση γραμμάτων", [(scan, 0xB7), (scan + 1, 0), (scan + 2, 0)]),
           ("ακμή χωρίς μνήμη του κρατημένου", [(held + i, 0) for i in range(4)]),
           ("μπάρα που αγνοεί το σβήσιμο των λωρίδων", [(gen, 0x18)]),
           ("δωμάτια που δεν κοκκινίζουν", [(fits, 0xAF), (fits + 1, 0), (fits + 2, 0)]),
           ("κουμπιά χωρίς γράμμα", [(letter + 1, 15)]),
           ("βοήθεια που δεν περιμένει να αφεθεί το πλήκτρο", [(up + i, 0) for i in range(3)]),
           ("τα 1-4 με λάθος μάσκα", [(find("UI_SPEED", [0xE6, 0x1E], 10) + 1, 0x0E)]),
           ("το FIRE του LOOK χαμένο", [(find("USL_GO", [0xE6, 0x50], 30) + 1, 0x40)]),
           ("το H χαμένο", [(find("UI_TICK", [0x1F, 0x30], 30), 0xB7)])]
    for label, patch in neg:
        why, _ = run(sym, patch, quick=True)
        check(why is not None, f"ΑΡΝΗΤΙΚΟ: με {label} αποτυγχάνει"
                               + (f" ({why[:120]})" if why else ""))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
