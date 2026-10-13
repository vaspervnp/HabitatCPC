"""Το μενού του πλανήτη (βήμα 128, src/boot.asm) — για τις δοκιμές που ξεκινούν
από τον δίσκο: τι γράφει η οθόνη του, και πώς διαλέγει κανείς.

Ο φορτωτής γράφει με το firmware, σε MODE 1, και η γραμματοσειρά του είναι της
κάτω ROM (#3800 του cpc6128_os.bin): ο αναγνώστης τη διαβάζει από το ίδιο το
αρχείο της ROM που τρέχει ο εξομοιωτής, όχι από κάποιο αντίγραφο του φορτωτή.
Ενας χαρακτήρας είναι 2 bytes x 8 γραμμές: η πένα 1 είναι το bit 0 κάθε pixel,
στο πάνω μισό του byte, οπότε τα δύο bytes μιας γραμμής είναι το πάνω και το
κάτω μισό του byte του γλύφου, στη θέση των bits 7-4. Ανάποδα (το mn_flip) είναι
τα ίδια XOR #F0.
"""
import os

ROMS = "/home/vasilhs/cpcemu/roms"
_FONT = None


def font():
    global _FONT
    if _FONT is None:
        rom = open(os.path.join(ROMS, "cpc6128_os.bin"), "rb").read()
        _FONT = rom[0x3800:0x4000]
    return _FONT


def cell(ram, row, col):
    """Τα 16 bytes του χαρακτήρα στη σειρά row, στήλη col (από το 0), με την
    οθόνη στο #C000 χωρίς μετατόπιση (ram = τα 16 KB της)."""
    return bytes(ram[line * 0x800 + row * 80 + col * 2 + k]
                 for line in range(8) for k in (0, 1))


def encode(ch, inverse=False):
    f = font()[ord(ch) * 8:ord(ch) * 8 + 8]
    x = 0xF0 if inverse else 0
    return bytes(b for g in f for b in ((g & 0xF0) ^ x, ((g << 4) & 0xF0) ^ x))


_TABLE = None


def text(ram, row, col, n):
    """(κείμενο, ανάποδα) για n χαρακτήρες· '?' όπου δεν ταιριάζει κανένας
    γλύφος, και το «ανάποδα» είναι 'I' / '.' / '?' ανά χαρακτήρα."""
    global _TABLE
    if _TABLE is None:
        _TABLE = {}
        for c in range(32, 127):
            for inv in (True, False):              # το κενό: ίσιο κερδίζει
                _TABLE[encode(chr(c), inv)] = (chr(c), "I" if inv else ".")
    s, f = "", ""
    for k in range(n):
        ch, iv = _TABLE.get(cell(ram, row, col + k), ("?", "?"))
        s, f = s + ch, f + iv
    return s, f


def syms(root):
    """Τα σύμβολα του φορτωτή (build/boot.sym, από το tools/mkdsk.py)."""
    bs = {}
    for line in open(os.path.join(root, "build", "boot.sym"),
                     encoding="utf-8", errors="replace"):
        p = line.split()
        if len(p) >= 2 and p[1].startswith("#"):
            bs[p[0].upper()] = int(p[1][1:], 16)
    return bs


def ready(m, bs):
    """Το μενού περιμένει πλήκτρο: είναι στην οθόνη, ο φορτωτής στη θέση του
    (bt_pl #FF όπως φορτώθηκε) και ο βρόχος έτρεξε μία φορά με τα πλήκτρα
    ελεύθερα (mn_prev από #FF σε 0). Πριν φορτωθεί, στο #9000 είναι ό,τι
    άφησε το BASIC — ή, μετά από reset, το προηγούμενο παιχνίδι: γι' αυτό
    και η οθόνη."""
    if m.peek(bs["BT_PL"]) != 0xFF or m.peek(bs["MN_PREV"]) != 0:
        return False
    return text(m.read_ram(0xC000, 0x4000), 9, 13, 14)[0] == "CHOOSE A WORLD"


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


ROWS = ("RANDOM", "DESERT", "ICE", "STORM", "BARREN MOON")


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
