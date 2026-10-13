"""Η ΑΝΑΦΟΡΑ του HUD (DESIGN §9.2), γραμμένη από τη διάταξη και όχι από τον Z80.

Σαράντα στήλες, πέντε σειρές, γραμματοσειρά 4x8. Οι ροές είναι μπάρες γιατί
σημασία έχει το περιθώριο· τα αποθέματα αριθμοί γιατί σημασία έχει η ποσότητα.

ΣΕ MODE 1 ΑΠΟ ΤΟ ΒΗΜΑ 83, στις δύο λωρίδες πάνω και κάτω από το κάδρο: οι
σειρές 0 και 1 μοιράζονται τη σειρά οθόνης 0, η 2 είναι η σειρά 1, οι 3 και 4
μοιράζονται τη σειρά 24. Ενα byte ανά γραμμή γλύφου.

Η γραμματοσειρά Mode 1 γράφεται ΕΔΩ από τα pixel του font_gfx, όχι με τον
κώδικα του tools/pack.py: το test_pack συγκρίνει τα δύο, και το tests/hudread.py
τη χρησιμοποιεί για να διαβάζει την οθόνη.
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sprites import load_map, load_bin

COLS, ROWS = 40, 5
BAR_CELLS = 6
CAP = 600
P_ESS = 2                       # src/const.asm — μόνο η υποστήριξη ζωής
# Η θέση κάθε λογικής σειράς: (γραμμή οθόνης της γραμμής 0 του γλύφου, στήλη byte)
ROW_AT = ((0, 0), (0, 40), (8, 0), (192, 0), (192, 40))
BAND_LINES = list(range(16)) + list(range(176, 200))


def m0_pens(b):
    """Τα δύο pixel ενός byte Mode 0: bits 7,3,5,1 το αριστερό, 6,2,4,0 το δεξί."""
    left = (b >> 7 & 1) | (b >> 3 & 1) << 1 | (b >> 5 & 1) << 2 | (b >> 1 & 1) << 3
    right = (b >> 6 & 1) | (b >> 2 & 1) << 1 | (b >> 4 & 1) << 2 | (b & 1) << 3
    return left, right


def m1_pens(b):
    """Τα τέσσερα pixel ενός byte Mode 1: το pixel i είναι τα bits 7-i και 3-i."""
    return [(b >> (7 - i) & 1) | (b >> (3 - i) & 1) << 1 for i in range(4)]


def m1_byte(pens):
    return sum((p & 1) << (7 - i) | (p >> 1 & 1) << (3 - i) for i, p in enumerate(pens))


def font_m1():
    """Οι 96 γλύφοι του font_gfx σε Mode 1, 8 bytes ο καθένας: μελάνι -> pen 3."""
    smap, blob = load_map(), load_bin()
    f = smap["font_gfx"]
    font = blob[f.off:f.off + f.size]
    out = []
    for i in range(96):
        g = bytearray()
        for ln in range(8):
            px = list(m0_pens(font[i * 16 + 2 * ln])) + list(m0_pens(font[i * 16 + 2 * ln + 1]))
            g.append(m1_byte([3 if p else 0 for p in px]))
        out.append(bytes(g))
    return out


# Τα κελιά της μπάρας (κωδικοί #80-#84 του src/hud.asm): στις γραμμές 1-5, όσο
# το σώμα των κεφαλαίων. Γεμάτο πράσινο (pen 2), λίγο κόκκινο (pen 1), και το
# άδειο ως περίγραμμα πάνω-κάτω σε pen 3.
def _cell(top, mid, bot):
    return bytes([0, top, mid, mid, mid, bot, 0, 0])


_P = {p: m1_byte([p] * 4) for p in range(4)}
CELLS = {"blank": bytes(8), "low": _cell(_P[1], _P[1], _P[1]),
         "full": _cell(_P[2], _P[2], _P[2]), "white": _cell(_P[3], _P[3], _P[3]),
         "empty": _cell(_P[3], 0, _P[3])}
PEN_FULL, PEN_EMPTY, PEN_LOW = "full", "empty", "low"


class Hud:
    def __init__(self):
        self.font = font_m1()
        self.cells = [[None] * COLS for _ in range(ROWS)]   # (kind, value)
        self.col = self.row = 0

    # --- πρωτογενή ---------------------------------------------------
    def put(self, ch):
        self.cells[self.row][self.col] = ("c", ord(ch))
        self.col += 1

    def text(self, s):
        for ch in s:
            self.put(ch)

    def num(self, v, n):
        self.text(num_leading(v, n))

    def cell(self, pen):
        self.cells[self.row][self.col] = ("p", pen)
        self.col += 1

    def bar(self, val, mx):
        if mx == 0:
            val, mx = 1, 1
        full = PEN_LOW if 4 * val < mx else PEN_FULL
        acc = 0
        for _ in range(BAR_CELLS):
            acc += mx
            self.cell(full if val * BAR_CELLS >= acc else PEN_EMPTY)

    # --- η διάταξη ---------------------------------------------------
    def draw(self, e):
        self.row, self.col = 0, 0
        for label, val, mx in (("O2 ", e["o2prod"], e["o2use"]),
                               ("PWR", e["pstore"], e["pcap"]),
                               ("H2O", e["stock"][0], CAP),
                               ("FOD", e["stock"][1], CAP)):
            self.text(label)
            self.bar(val, mx)
            self.put(" ")

        self.row, self.col = 1, 0
        for a, b, idx in (("F", "E", 3), ("B", "I", 4), ("P", "R", 5),
                          ("S", "P", 6), ("M", "E", 7), ("B", "O", 9)):
            self.text(a + b)
            self.num(e["stock"][idx], 3)
            self.put(" ")
        self.text("    ")

        self.row, self.col = 2, 0
        self.text("POP ")
        self.num(e["alive"], 2)
        self.put("/")
        self.num(e["popcap"], 2)
        self.text(" SOL")
        self.num(e["sol"], 3)
        self.put(" ")
        self.text("DAY" if e["day"] else "NGT")
        self.put(" ")
        self.text(self.alert(e))

        for r in (3, 4):
            self.row, self.col = r, 0
            self.text(" " * COLS)
        assert all(all(c is not None for c in row) for row in self.cells), \
            "μια στήλη έμεινε άγραφη — το HUD δεν καλύπτει τις 40"
        return self

    @staticmethod
    def alert(e):
        # Η σειρά του hud_alert (§6.5, §6.10): ό,τι σκοτώνει γρηγορότερα πρώτο.
        # Φαγητό και νερό «λίγα» = κάτω από μία μερίδα ανά ζωντανό (hd_short).
        def short(v):
            return v < 256 and v < e["alive"]
        if e["gameover"]:
            return "COLONY LOST        "
        if not e["pok"]:
            return "NO POWER           "
        if not e["o2ok"]:
            return "NO OXYGEN          "
        if e.get("suit"):                  # κάποιος έξω με < 1 λεπτό αέρα (βήμα 90)
            return "SUIT AIR LOW       "
        if e["pok"] == P_ESS:
            return "LOW POWER          "
        if e.get("meteor"):
            return "METEOR SHOWER      "
        if short(e["stock"][1]):
            return "LOW ON FOOD        "
        if short(e["stock"][0]):
            return "LOW ON WATER       "
        if e["storm"]:
            return "SANDSTORM          "
        if e.get("full"):                  # η αποθήκη γέμισε (βήμα 122)
            return "STORAGE FULL       "
        return "ALL SYSTEMS OK     "

    # --- σε γραμμικά bytes -------------------------------------------
    def to_lines(self):
        """{γραμμή οθόνης: bytes[80]} για τις 40 γραμμές των λωρίδων: 0-15 και
        176-199. Ό,τι δεν είναι σειρά του HUD (το δεξί μισό της T1, η B0 και η
        B1) είναι μαύρο."""
        out = {y: bytearray(80) for y in BAND_LINES}
        for r in range(ROWS):
            y0, x0 = ROW_AT[r]
            for c in range(COLS):
                kind, v = self.cells[r][c]
                g = self.font[v - 32] if kind == "c" else CELLS[v]
                for ln in range(8):
                    out[y0 + ln][x0 + c] = g[ln]
        return {y: bytes(b) for y, b in out.items()}


def num_leading(v, n):
    """Ο κανόνας των μπροστινών μηδενικών, ξεχωριστά για να ελεγχθεί.

    Τιμή με περισσότερα ψηφία από n δείχνει το υπόλοιπο της διαίρεσης με 10^n,
    και ΜΕΤΑ σβήνονται τα μπροστινά μηδενικά: το 1005 σε τρία ψηφία είναι
    «  5», όχι «005». Ετσι έκανε ο Z80 από την αρχή (και με διαιρέσεις, και με
    αφαιρέσεις από το βήμα 52)· ως το βήμα 52 η αναφορά έκοβε τη συμβολοσειρά.
    """
    return str(int(v) % 10 ** n).rjust(n)
