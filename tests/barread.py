"""Η μπάρα των κουμπιών όπως είναι στην οθόνη (DESIGN §9.3, βήμα 84) — για τις δοκιμές.

Η ΑΝΑΦΟΡΑ ΓΡΑΦΕΤΑΙ ΕΔΩ, από την πρόζα, όχι από τον Z80:

  Θέση: 16 θέσεις των 5 bytes στις γραμμές 177-191 (η 176 μαύρη). Η θέση s
  είναι τα bytes 5s..5s+4 των γραμμών 1-7 της σειράς οθόνης 22 και 0-7 της 23.
  Κουμπί: οκτάγωνο 18x15 στις στήλες pixel 1-18 της θέσης, πάνω και κάτω
  πλευρά 12 pixel (στήλες 4-15), λοξές γωνίες τριών. Μέσα, στις στήλες 4-15 και
  γραμμές 2-12, το σύμβολο 12x11 του tools/buttons.py. Στο byte 0 των γραμμών
  10-14, πάνω από ό,τι άλλο, οι γραμμές 1-5 του γλύφου του γράμματος (λευκό).
  Χρώματα: πράσινο κουμπί και σύμβολο· λευκά και τα δύο όταν είναι
  διαλεγμένο· πράσινο κουμπί με κόκκινο σύμβολο όταν δεν γίνεται εκεί.

Τα γράμματα και η σειρά των κουμπιών είναι της πρόζας (DESIGN §9.3), όχι του
πίνακα bt_tab του src/bar.asm: αν ο πίνακας έλεγε άλλο γράμμα, η δοκιμή θα το
έβλεπε.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tools"))
from hudref import font_m1, m1_pens, m1_byte                          # noqa: E402
import buttons                                                         # noqa: E402

# (όνομα του συμβόλου, γράμμα), με τη σειρά των κουμπιών
BUTTONS = [("domes", "D"), ("small", "S"), ("medium", "M"), ("large", "L"),
           ("oxygen", "O"), ("canteen", "C"), ("quarters", "Q"), ("greenhouse", "G"),
           ("factory", "F"), ("lab", "B"), ("medbay", "E"), ("control", "N"),
           ("storage", "T"), ("lounge", "U"),
           ("corridor", "R"),
           ("power", "P"), ("solar", "S"), ("turbine", "T"), ("collector", "C"),
           ("resources", "E"), ("extractor", "X"), ("mine", "M"),
           ("transport", "T"), ("airlock", "A"), ("pad", "P"), ("ship", "C"),
           ("trade", "M"),                                     # βήμα 93: ο έμπορος
           ("manage", "M"), ("info", "I"), ("fit", "F"), ("save", "S"), ("load", "L"),
           ("centre", "H"), ("help", "?")]
ID = {n: i for i, (n, _) in enumerate(BUTTONS)}
GROUPS = ["domes", "corridor", "power", "resources", "transport", "manage"]
# Ο,τι ανοίγει κάθε ομάδα στην ίδια μπάρα (η ίδια πρώτη)
GROUP_BAR = {"domes": ["domes", "small", "medium", "large", "oxygen", "canteen", "quarters",
                       "greenhouse", "factory", "lab", "medbay", "control", "storage", "lounge"],
             "power": ["power", "solar", "turbine", "collector"],
             "resources": ["resources", "extractor", "mine"],
             "transport": ["transport", "airlock", "pad", "ship", "trade"],
             "manage": ["manage", "info", "fit", "save", "load", "centre"]}
# Ο κατάλογος του src/build.asm (ui_sel) -> το κουμπί του
ITEM_BTN = ["small", "medium", "large", "corridor", "solar", "turbine", "collector",
            "extractor", "mine", "airlock", "pad"]
GREEN, WHITE, RED = "green", "white", "red"
SLOTS, SLOT_W = 16, 5
BAR_OFF = 1600                      # η σειρά οθόνης 22, από το cam_p

_FACES = None
_FONT = None


def _font():
    global _FONT
    if _FONT is None:
        _FONT = font_m1()
    return _FONT


def _octagon():
    rows = []
    for y in range(15):
        row = [0] * 20
        if y in (0, 14):
            for x in range(4, 16):
                row[x] = 1
        else:
            c = max(0, 3 - y, y - 11)
            row[1 + c] = row[18 - c] = 1
        rows.append(row)
    return rows


def face(name, state):
    """Τα 75 bytes του κουμπιού, γραμμή-γραμμή (5 ανά γραμμή)."""
    pen_o, pen_i = {GREEN: (2, 2), WHITE: (3, 3), RED: (2, 1)}[state]
    letter = dict(BUTTONS)[name]
    px = [[pen_o if v else 0 for v in row] for row in _octagon()]
    pic = buttons.pixels(name)
    for y in range(11):
        for x in range(12):
            if pic[y][x]:
                px[2 + y][4 + x] = pen_i
    g = _font()[ord(letter) - 32]
    for i in range(5):
        for x, p in enumerate(m1_pens(g[1 + i])):
            px[10 + i][x] = p
    out = bytearray()
    for y in range(15):
        for b in range(SLOT_W):
            out.append(m1_byte(px[y][4 * b:4 * b + 4]))
    return bytes(out)


def faces():
    global _FACES
    if _FACES is None:
        _FACES = {face(n, st): (n, st) for n, _ in BUTTONS for st in (GREEN, WHITE, RED)}
    return _FACES


def cam_p(m, sym):
    return 2 * (m.peek(sym["CAM_OFF"]) | m.peek(sym["CAM_OFF"] + 1) << 8)


def slot_bytes(ram, cp, off):
    """75 bytes από τη θέση off (από το cam_p) της σειράς οθόνης του κουμπιού."""
    out = bytearray()
    for y in range(15):
        ln = (1 + y) & 7
        row = off + ((1 + y) >> 3) * 80
        out += bytes(ram[ln * 0x800 + ((cp + row + b) & 0x7FF)] for b in range(SLOT_W))
    return bytes(out)


def read_off(ram, cp, off):
    """-> (όνομα, κατάσταση), None για άδεια θέση, ή '?' για ό,τι δεν είναι κουμπί."""
    b = slot_bytes(ram, cp, off)
    if not any(b):
        return None
    return faces().get(b, "?")


def bar(m, sym, ram=None):
    """Οι 16 θέσεις της μπάρας."""
    ram = m.read_ram(0xC000, 0x4000) if ram is None else ram
    cp = cam_p(m, sym)
    return [read_off(ram, cp, BAR_OFF + SLOT_W * s) for s in range(SLOTS)]


def line176(m, sym, ram=None):
    ram = m.read_ram(0xC000, 0x4000) if ram is None else ram
    cp = cam_p(m, sym)
    return bytes(ram[(cp + BAR_OFF + x) & 0x7FF] for x in range(80))


def want_groups(lit=None):
    """Η μπάρα των ομάδων: οι έξι στις θέσεις 0-5, το ? στη 15."""
    out = [(g, WHITE if g == lit else GREEN) for g in GROUPS] + [None] * 9
    out.append(("help", WHITE if lit == "help" else GREEN))
    return out


def want_group(group, lit=(), red=()):
    """Η μπάρα μιας ανοιχτής ομάδας: η ίδια λευκή στη θέση 0."""
    names = GROUP_BAR[group]
    out = [(n, WHITE if (i == 0 or n in lit) else RED if n in red else GREEN)
           for i, n in enumerate(names)]
    out += [None] * (15 - len(out)) + [("help", GREEN)]
    return out


def show(slots):
    """Για τα μηνύματα: «domes* small ...», * λευκό, ! κόκκινο."""
    return " ".join("." if s is None else "?" if s == "?" else
                    s[0] + {"green": "", "white": "*", "red": "!"}[s[1]] for s in slots)
