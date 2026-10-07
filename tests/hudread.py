"""Το HUD όπως είναι στη μνήμη της οθόνης (DESIGN §9.2) — για τις δοκιμές.

ΑΠΟ ΤΟ ΒΗΜΑ 83 ΤΟ HUD ΕΙΝΑΙ ΔΥΟ ΛΩΡΙΔΕΣ MODE 1, πάνω και κάτω από το κάδρο, και
οι πέντε λογικές σειρές των σαράντα στηλών κάθονται έτσι:

    σειρά 0   πάνω λωρίδα, σειρά οθόνης 0, στήλες  0-39
    σειρά 1   πάνω λωρίδα, σειρά οθόνης 0, στήλες 40-79
    σειρά 2   πάνω λωρίδα, σειρά οθόνης 1, στήλες  0-39
    σειρά 3   κάτω λωρίδα, σειρά οθόνης 24, στήλες  0-39
    σειρά 4   κάτω λωρίδα, σειρά οθόνης 24, στήλες 40-79

Ενα byte ανά γραμμή γλύφου. Οι θέσεις είναι μέσα στο δαχτυλίδι των 2.048 bytes,
από το cam_p (= 2 x cam_off): η πάνω λωρίδα είναι τα 160 bytes ΠΡΙΝ από αυτό.

Ως το βήμα 82 κάθε δοκιμή είχε το δικό της αντίγραφο αυτού του αναγνώστη
(Mode 0, γραμμές 160-199)· τώρα ζει εδώ, μία φορά.

Η ΓΡΑΜΜΑΤΟΣΕΙΡΑ ΕΡΧΕΤΑΙ ΑΠΟ ΤΗΝ ΑΝΑΦΟΡΑ (tools/hudref.py), που τη γράφει από τα
pixel του font_gfx και όχι με τον κώδικα του tools/pack.py: αν το pack.py
μετέτρεπε λάθος, οι δοκιμές δεν θα το επαναλάμβαναν.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tools"))

ROW_OFF = (-160, -120, -80, 1760, 1800)      # η στήλη 0 κάθε λογικής σειράς
TOP_OFF, TOP_BYTES = -160, 160               # η πάνω λωρίδα, ολόκληρη
BOT_OFF, BOT_BYTES = 1600, 240               # η κάτω (B0, B1, B2)

# Η γραμματοσειρά και τα κελιά της μπάρας: από την αναφορά του HUD (tools/hudref.py).
from hudref import m0_pens, m1_pens, font_m1, CELLS                     # noqa: E402,F401


_GLYPH = None


def glyphs():
    """bytes(8) -> χαρακτήρας. Το 0 και το O έχουν τον ίδιο γλύφο· κερδίζει το O,
    όπως στους παλιούς αναγνώστες."""
    global _GLYPH
    if _GLYPH is None:
        _GLYPH = {g: chr(32 + i) for i, g in enumerate(font_m1())}
    return _GLYPH


def cam_p(m, sym):
    return 2 * (m.peek(sym["CAM_OFF"]) | m.peek(sym["CAM_OFF"] + 1) << 8)


def screen(m):
    return m.read_ram(0xC000, 0x4000)


def cell(ram, cp, row, col):
    """Τα 8 bytes του κελιού (σειρά, στήλη)."""
    p = cp + ROW_OFF[row] + col
    return bytes(ram[ln * 0x800 + (p & 0x7FF)] for ln in range(8))


def text(m, sym, row, ram=None, unknown="#"):
    """Οι 40 στήλες της λογικής σειράς ως κείμενο· ό,τι δεν είναι γλύφος: unknown."""
    ram = screen(m) if ram is None else ram
    cp, g = cam_p(m, sym), glyphs()
    return "".join(g.get(cell(ram, cp, row, c), unknown) for c in range(40))


def raw(m, sym, row, ram=None):
    """Τα 40 κελιά της σειράς ως 320 bytes, κελί-κελί (8 γραμμές το καθένα)."""
    ram = screen(m) if ram is None else ram
    cp = cam_p(m, sym)
    return b"".join(cell(ram, cp, row, c) for c in range(40))


def band_lines(ram, cp):
    """{γραμμή οθόνης: 80 bytes} για τις 40 γραμμές των δύο λωρίδων: 0-15 και 176-199."""
    out = {}
    for y in range(16):
        base = cp + TOP_OFF + (y >> 3) * 80
        out[y] = bytes(ram[(y & 7) * 0x800 + ((base + x) & 0x7FF)] for x in range(80))
    for y in range(176, 200):
        base = cp + BOT_OFF + ((y - 176) >> 3) * 80
        out[y] = bytes(ram[(y & 7) * 0x800 + ((base + x) & 0x7FF)] for x in range(80))
    return out


def band_addrs(cp):
    """Οι 3.200 διευθύνσεις (#C000-#FFFF) των δύο λωρίδων."""
    out = []
    for off, n in ((TOP_OFF, TOP_BYTES), (BOT_OFF, BOT_BYTES)):
        for ln in range(8):
            out += [0xC000 + ln * 0x800 + ((cp + off + x) & 0x7FF) for x in range(n)]
    return out
