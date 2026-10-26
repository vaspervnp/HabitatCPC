"""Πού ζει κάθε byte του κώδικα των τρυπών (βήμα 155, src/ov_inst.asm): για
τις δοκιμές που τον διαβάζουν εκεί ή τον πειράζουν για τα αρνητικά τους.

Ως το βήμα 154 όλα ήταν στις στήλες 96-127 του DIST, 32 bytes ανά γραμμή, με
τη σειρά. Από το 155 τρία σημεία (src/const.asm):

  OV_R1   βασική τράπεζα 1, #6000, συνεχές: οι χειριστές της κατεδάφισης
          (src/dm_hand.asm, από το DH_RSIZE), οι γραμμές του tutorial (TU_TXT),
          ο κώδικάς του (build/ovl4.bin, από το ZZ_TUT_END).
  OV_R2   βασική τράπεζα 1, οι στήλες 112-127 των γραμμών θόλων του DIST, 16
          bytes ανά γραμμή: το σώσιμο (build/ovl2.bin), και από την επόμενη
          γραμμή του η βοήθεια (build/ovl3.bin).
  OV_R3   τράπεζα 5, οι στήλες 112-127 του NEXTHOP: η κατεδάφιση
          (build/ovl.bin).

Οι διευθύνσεις είναι του παραθύρου (&4000-&7FFF)· το bank(n)[a - 0x4000] του
εξομοιωτή είναι το byte, όποια τράπεζα κι αν φαίνεται τη στιγμή εκείνη.
"""
import ctypes, os

import cpc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNIT, NODE_CAP = 16, 112
OV_R1, OV_R2, OV_R3 = 0x6000, 0x4000 + NODE_CAP, 0x4000 + NODE_CAP
TU_LINES = 16 * 32


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


def spread(start, n):
    """Οι διευθύνσεις n bytes, UNIT σε κάθε γραμμή των 128 από το start."""
    return [start + (k // UNIT) * 128 + k % UNIT for k in range(n)]


def pieces(sym):
    """όνομα -> (τράπεζα, διευθύνσεις ανά byte, πού τρέχει το byte 0, τα bytes
    του build). Τα "hand" και "tutext" δεν έχουν δικό τους αρχείο· είναι μέσα
    στο "r1", το OV_R1 ολόκληρο (build/ovr1.bin)."""
    dm, sv, hp, tu = _bin("ovl.bin"), _bin("ovl2.bin"), _bin("ovl3.bin"), _bin("ovl4.bin")
    r1 = _bin("ovr1.bin")                   # όλο το OV_R1, όπως φτάνει
    rows2 = -(-len(sv) // UNIT)
    hand = sym["TU_TXT"] - sym["DH_RSIZE"]
    return {
        "dm": (5, spread(OV_R3, len(dm)), GH, dm),
        "save": (1, spread(OV_R2, len(sv)), GH, sv),     # στο GH_BUF + 512 ως το βήμα 174
        "help": (1, spread(OV_R2 + rows2 * 128, len(hp)), GH, hp),
        "tutor": (1, list(range(sym["ZZ_TUT_END"], sym["ZZ_TUT_END"] + len(tu))), GH, tu),
        "tutext": (1, list(range(sym["TU_TXT"], sym["TU_TXT"] + TU_LINES)), sym["TU_TXT"], None),
        "hand": (1, list(range(sym["DH_RSIZE"], sym["DH_RSIZE"] + hand)), sym["DH_RSIZE"], None),
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
