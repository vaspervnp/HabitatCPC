"""Κώδικας του παιχνιδιού, όπου κι αν ζει: για τις δοκιμές που τον διαβάζουν ή
τον πειράζουν (βήμα 110).

Το peek/poke του εξομοιωτή βλέπει ό,τι είναι στο παράθυρο &4000-&7FFF τη
στιγμή εκείνη, συνήθως η τράπεζα 1. Ο κώδικας του τροχού στο b6code
(src/bots.asm και ό,τι ακολουθεί στο src/main.asm) ζει στην τράπεζα 6, στις
ίδιες διευθύνσεις. Από το βήμα 110 εκεί είναι και οι ανάγκες και οι
μετεωρίτες, που πολλές δοκιμές πειράζουν για τα αρνητικά τους· ένα poke στη
διεύθυνσή τους θα έγραφε στο DIST της τράπεζας 1, και το αρνητικό θα «περνούσε»
επειδή δεν πείραξε τίποτα.
"""
import ctypes, os

import cpc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B6_END = 0x6C00                         # G_agent_fields: εκεί τελειώνει το b6code


def _b6code():
    for line in open(os.path.join(ROOT, "build", "layout.asm"), encoding="utf-8"):
        p = line.split()
        if len(p) >= 3 and p[0] == "G_b6code":
            return int(p[2].lstrip("#"), 16)
    raise KeyError("G_b6code")


B6_START = _b6code()


def in_b6(addr):
    return B6_START <= addr < B6_END


def _b6(m):
    return cpc._lib.cpcemu_ram_ptr(m._h, 6)


def read(m, addr, n):
    """n bytes κώδικα από το addr, από την τράπεζα 6 αν είναι στο b6code."""
    if in_b6(addr):
        return ctypes.string_at(ctypes.addressof(_b6(m).contents) + addr - 0x4000, n)
    return bytes(m.read_ram(addr, n))


def poke(m, addr, v):
    if in_b6(addr):
        _b6(m)[addr - 0x4000] = v
    else:
        m.poke(addr, v)


def find(m, addr, pat, span=400):
    """Η διεύθυνση του pat μετά το addr, ή None."""
    i = read(m, addr, span).find(bytes(pat))
    return None if i < 0 else addr + i
