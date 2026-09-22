"""Η ΑΝΑΦΟΡΑ του HUD (DESIGN §9.2), γραμμένη από τη διάταξη και όχι από τον Z80.

Σαράντα στήλες, πέντε σειρές, γραμματοσειρά 4x8. Οι ροές είναι μπάρες γιατί
σημασία έχει το περιθώριο· τα αποθέματα αριθμοί γιατί σημασία έχει η ποσότητα.
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sprites import load_map, load_bin

HUD_TOP = 160
COLS, ROWS = 40, 5
BAR_CELLS = 6
PEN_FULL, PEN_EMPTY, PEN_LOW = 9, 1, 8
CAP = 600

# Το byte ενός συμπαγούς pen στο Mode 0: τα bits του αριστερού pixel είναι τα
# 7,3,5,1 και του δεξιού τα 6,2,4,0.
def solid(p):
    return (((p) & 1) * 0xC0 | ((p >> 1) & 1) * 0x0C
            | ((p >> 2) & 1) * 0x30 | ((p >> 3) & 1) * 0x03)


class Hud:
    def __init__(self):
        self.smap, self.blob = load_map(), load_bin()
        f = self.smap["font_gfx"]
        self.font = self.blob[f.off:f.off + f.size]
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
        s = str(int(v))[-n:].rjust(n)
        self.text(s)

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
        self.text("SOL")
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
        if e["gameover"]:
            return "COLONY LOST         "
        if not e["pok"]:
            return "NO POWER            "
        if not e["o2ok"]:
            return "NO OXYGEN           "
        if e["storm"]:
            return "SANDSTORM           "
        return "ALL SYSTEMS OK      "

    # --- σε γραμμικά bytes -------------------------------------------
    def to_lines(self):
        """{γραμμή οθόνης: bytes[80]} για τις γραμμές 160..199."""
        out = {}
        for r in range(ROWS):
            for l in range(8):
                row = bytearray(80)
                for c in range(COLS):
                    kind, v = self.cells[r][c]
                    if kind == "c":
                        o = (v - 32) * 16 + l * 2
                        row[c * 2] = self.font[o]
                        row[c * 2 + 1] = self.font[o + 1]
                    else:
                        row[c * 2] = row[c * 2 + 1] = solid(v)
                out[HUD_TOP + r * 8 + l] = bytes(row)
        return out


def num_leading(v, n):
    """Ο κανόνας των μπροστινών μηδενικών, ξεχωριστά για να ελεγχθεί."""
    return str(int(v))[-n:].rjust(n)
