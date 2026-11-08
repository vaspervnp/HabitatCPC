"""Πού ζει κάθε byte του κώδικα των τρυπών (βήμα 155, src/ov_inst.asm): για
τις δοκιμές που τον διαβάζουν εκεί ή τον πειράζουν για τα αρνητικά τους.

Ως το βήμα 154 όλα ήταν στις στήλες 96-127 του DIST, 32 bytes ανά γραμμή, με
τη σειρά. Από το 155 τρία σημεία (src/const.asm):

  OV_R1   βασική τράπεζα 1, #6000, συνεχές: οι χειριστές της κατεδάφισης
          (src/dm_hand.asm, από το DH_RSIZE), το bar_sync (βήμα 199,
          src/sync1.asm, από το BAR_SYNC), οι σειρές του εργοταξίου που
          υψώνεται (βήμα 200, src/rise1.asm, από το DH_RISE), ο κώδικας του
          tutorial (build/ovl4.bin, από το TU_AT· ως το βήμα 198 μετά τις
          γραμμές του· από το 201 μόνο το πρώτο μέρος του).
  OV_R2   βασική τράπεζα 1, οι στήλες 112-127 των γραμμών θόλων του DIST, 16
          bytes ανά γραμμή: το σώσιμο (build/ovl2.bin), και από την επόμενη
          γραμμή του η βοήθεια (build/ovl3.bin).
  OV_R3   τράπεζα 5, οι στήλες 112-127 του NEXTHOP: η κατεδάφιση
          (build/ovl.bin), και από την επόμενη γραμμή της ο χάρτης (βήμα 186,
          build/ovl5.bin).
  TX_HOLE βασική τράπεζα 1, οι στήλες 48-63 των γραμμών 0-31 του μπλοκ των
          δομών (#6430, 16 bytes ανά γραμμή των 64): οι γραμμές του tutorial
          (βήμα 199, build/ovtx.bin· ως τότε στο OV_R1, από το TU_TXT).
  TB_HOLE οι ίδιες στήλες των γραμμών 32-47 (#6C30): το δεύτερο μέρος του
          κώδικα του tutorial (βήμα 201, src/tutor2.asm, build/ovtb.bin), που
          τρέχει στο GH_BUF + TU_ALEN, από το ZZ_TUB.

Οι διευθύνσεις είναι του παραθύρου (&4000-&7FFF)· το bank(n)[a - 0x4000] του
εξομοιωτή είναι το byte, όποια τράπεζα κι αν φαίνεται τη στιγμή εκείνη.
"""
import ctypes, os

import cpc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNIT, NODE_CAP = 16, 112
OV_R1, OV_R2, OV_R3 = 0x6000, 0x4000 + NODE_CAP, 0x4000 + NODE_CAP
TU_LINES = 16 * 32
TX_HOLE = 0x6400 + 48                   # DB_ROW + MAX_STRUCT (src/const.asm)
TB_HOLE = TX_HOLE + 32 * 64             # TX_HOLE + TX_UNITS * DB_STRIDE (βήμα 201)


def _bin(name):
    p = os.path.join(ROOT, "build", name)
    return open(p, "rb").read() if os.path.exists(p) else b""


def _gh():
    for line in open(os.path.join(ROOT, "build", "layout.asm"), encoding="utf-8"):
        p = line.split()
        if len(p) >= 3 and p[0] == "PAGE2_TOP":
            return int(p[2].lstrip("#"), 16)
    raise KeyError("PAGE2_TOP")


GH = _gh()


def spread(start, n, stride=128):
    """Οι διευθύνσεις n bytes, UNIT σε κάθε γραμμή των stride από το start."""
    return [start + (k // UNIT) * stride + k % UNIT for k in range(n)]


def pieces(sym):
    """όνομα -> (τράπεζα, διευθύνσεις ανά byte, πού τρέχει το byte 0, τα bytes
    του build). Τα "hand", "sync" και "rise" δεν έχουν δικό τους αρχείο· είναι μέσα
    στο "r1", το OV_R1 ολόκληρο (build/ovr1.bin)."""
    dm, sv, hp, tu = _bin("ovl.bin"), _bin("ovl2.bin"), _bin("ovl3.bin"), _bin("ovl4.bin")
    mp, tx, tb = _bin("ovl5.bin"), _bin("ovtx.bin"), _bin("ovtb.bin")
    r1 = _bin("ovr1.bin")                   # όλο το OV_R1, όπως φτάνει
    rows2 = -(-len(sv) // UNIT)
    rows3 = -(-len(dm) // UNIT)
    hand = sym["BAR_SYNC"] - sym["DH_RSIZE"]
    return {
        "dm": (5, spread(OV_R3, len(dm)), GH, dm),
        "map": (5, spread(OV_R3 + rows3 * 128, len(mp)), GH, mp),
        "save": (1, spread(OV_R2, len(sv)), GH, sv),     # στο GH_BUF + 512 ως το βήμα 174
        "help": (1, spread(OV_R2 + rows2 * 128, len(hp)), GH, hp),
        "tutor": (1, list(range(sym["TU_AT"], sym["TU_AT"] + len(tu))), GH, tu),
        "tutext": (1, spread(TX_HOLE, TU_LINES, 64), sym["TU_TXT"], tx),
        "tutb": (1, spread(TB_HOLE, len(tb), 64), sym["ZZ_TUB"], tb),
        "hand": (1, list(range(sym["DH_RSIZE"], sym["DH_RSIZE"] + hand)), sym["DH_RSIZE"], None),
        "sync": (1, list(range(sym["BAR_SYNC"], sym["DH_RISE"])), sym["BAR_SYNC"], None),
        "rise": (1, list(range(sym["DH_RISE"], sym["TU_AT"])), sym["DH_RISE"], None),
        "r1": (1, list(range(OV_R1, OV_R1 + len(r1))), OV_R1, r1),
    }


def bank(m, n):
    return cpc._lib.cpcemu_ram_ptr(m._h, n)


def read(m, sym, name):
    """Τα bytes ενός κομματιού όπως είναι στη μνήμη του m."""
    b, at, _, _ = pieces(sym)[name]
    p = bank(m, b)
    return bytes(p[a - 0x4000] for a in at)


def at(sym, name, label_or_addr):
    """(τράπεζα, διεύθυνση) του byte του κομματιού που τρέχει στο label (ή στη
    διεύθυνση εκτέλεσης)."""
    b, ats, org, _ = pieces(sym)[name]
    a = sym[label_or_addr] if isinstance(label_or_addr, str) else label_or_addr
    return b, ats[a - org]


def poke(m, sym, name, run_addr, v):
    """Ένα byte του κομματιού, από τη διεύθυνση όπου τρέχει."""
    b, a = at(sym, name, run_addr)
    bank(m, b)[a - 0x4000] = v
