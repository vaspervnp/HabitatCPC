"""Το μενού του πλανήτη (βήμα 128, πάνω σε κομμάτι κόσμου από το 130:
src/menu.asm, το MENU.BIN) — για τις δοκιμές που ξεκινούν από τον δίσκο: τι
γράφει η οθόνη του, και πώς διαλέγει κανείς.

Από το βήμα 130 το μενού είναι σε MODE 0, με τη γραμματοσειρά 3x5 του
παιχνιδιού (font_gfx των assets), και όχι με το firmware σε MODE 1. Ενας
χαρακτήρας είναι πάλι 2 bytes x 8 γραμμές: οι γλύφοι είναι στις πένες 0 και
5, ανάποδα (η διαλεγμένη γραμμή) XOR #F0, σβηστά (το BUILDING THE WORLD πριν
από τη γεννήτρια) AND #3F. Ο αναγνώστης τους διαβάζει από τα ίδια τα assets,
όχι από το MENU.BIN. Η θέση κάθε γραμμής είναι του src/menugeom.asm
(tools/menuworld.py: geom).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))

import menuworld as MW                                                  # noqa: E402

_TABLE = None


def cell(ram, row, col):
    """Τα 16 bytes του χαρακτήρα στη σειρά row, στήλη col (από το 0), με την
    οθόνη στο #C000 χωρίς μετατόπιση (ram = τα 16 KB της)."""
    return bytes(ram[line * 0x800 + row * 80 + col * 2 + k]
                 for line in range(8) for k in (0, 1))


def encode(ch, mode="."):
    g = MW.glyph(ch)
    if mode == "I":
        return bytes(b ^ MW.INV for b in g)
    if mode == "d":
        return bytes(b & MW.DIM for b in g)
    return bytes(g)


def text(ram, row, col, n):
    """(κείμενο, τρόπος) για n χαρακτήρες· '?' όπου δεν ταιριάζει κανένας
    γλύφος, και ο τρόπος είναι 'I' (ανάποδα) / '.' (ίσια) / 'd' (σβηστά) /
    '?' ανά χαρακτήρα. Το κενό ίσιο και σβηστό είναι το ίδιο: ίσιο."""
    global _TABLE
    if _TABLE is None:
        _TABLE = {}
        for c in range(32, 128):
            for mode in ("d", "I", "."):            # το «.» κερδίζει στο κενό
                _TABLE[encode(chr(c), mode)] = (chr(c), mode)
    s, f = "", ""
    for k in range(n):
        ch, iv = _TABLE.get(cell(ram, row, col + k), ("?", "?"))
        s, f = s + ch, f + iv
    return s, f


def syms(root):
    """Τα σύμβολα του φορτωτή και του μενού (build/boot.sym, build/menu.sym,
    από το tools/mkdsk.py)."""
    bs = {}
    for name in ("boot.sym", "menu.sym"):
        for line in open(os.path.join(root, "build", name),
                         encoding="utf-8", errors="replace"):
            p = line.split()
            if len(p) >= 2 and p[1].startswith("#"):
                bs[p[0].upper()] = int(p[1][1:], 16)
    return bs


def ready(m, bs):
    """Το μενού περιμένει πλήκτρο: είναι στην οθόνη, ο φορτωτής στη θέση του
    (bt_pl #FF όπως φορτώθηκε) και ο βρόχος έτρεξε μία φορά με τα πλήκτρα
    ελεύθερα (mn_prev από #FF σε 0). Το mn_prev είναι στο MENU.BIN: πριν
    φορτωθεί, στη θέση του είναι ό,τι άφησε το BASIC (συνήθως 0) — γι' αυτό
    και η οθόνη, που τη γράφει το ίδιο το μενού λίγο πριν από τον βρόχο."""
    if m.peek(bs["BT_PL"]) != 0xFF or m.peek(bs["MN_PREV"]) != 0:
        return False
    g = MW.geom()
    return text(m.read_ram(0xC000, 0x4000), g["CHO_ROW"], g["CHO_COL"],
                len(MW.CHOOSE))[0] == MW.CHOOSE


def wait(m, bs, limit=600):
    """Τρέχει ως να είναι έτοιμο το μενού· γυρίζει τα frames, ή None."""
    for f in range(limit):
        if ready(m, bs):
            return f
        m.run_frames(1)
    return None


def press(m, keys, joy=False):
    """Πατά τα keys ('u', 'd', 'f'), ένα ένα: 4 frames κάτω, 8 πάνω. Με joy
    από το χειριστήριο 0, αλλιώς βελάκια και RETURN."""
    from cpc import KEY_DOWN, KEY_UP, KEY_ENTER, JOY_UP, JOY_DOWN, JOY_FIRE
    if joy:
        m.set_joystick_type(1)
        for k in keys:
            m.joystick({"u": JOY_UP, "d": JOY_DOWN, "f": JOY_FIRE}[k])
            m.run_frames(4)
            m.joystick(0)
            m.run_frames(8)
        m.set_joystick_type(0)
    else:
        for k in keys:
            m.tap_key({"u": KEY_UP, "d": KEY_DOWN, "f": KEY_ENTER}[k], 4, 8)


ROWS = tuple(name for name, _, _ in MW.MENU)


def pick(m, bs, planet=None, joy=False):
    """Περιμένει το μενού και διαλέγει: planet 0-3, ή None για τον τυχαίο.
    Ως τον πάτο πηγαίνει από πάνω (ένα βελάκι πάνω από τον τυχαίο), αλλιώς
    κάτω. Γυρίζει τα frames της αναμονής, ή None."""
    f = wait(m, bs)
    if f is None:
        return None
    n = 0 if planet is None else planet + 1
    keys = "u" if n == 4 else "d" * n
    press(m, keys + "f", joy)
    return f
