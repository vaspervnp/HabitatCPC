#!/usr/bin/env python3
"""Το επίπεδο κόσμου ενός ΝΕΟΥ παιχνιδιού, από τη γεννήτρια αναφοράς.

Η γεννήτρια σε Z80 δεν χωράει στην τράπεζα 0 μαζί με το παιχνίδι (DESIGN §4.2):
είναι ξεχωριστό φόρτωμα. Ωσότου γραφτεί ο φορτωτής, το επίπεδο έρχεται από εδώ
— και είναι ΤΟ ΙΔΙΟ επίπεδο, byte-προς-byte, που θα έβγαζε ο Z80 για το ίδιο
seed· αυτό το επιβάλλει το tests/test_worldgen.py.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import worldgen_ref as G

SEED = 0xACE1                   # το NG_SEED του src/newgame.asm


def build(seed=SEED, planet=0):
    plane = G.generate(seed, planet)
    out = os.path.join(ROOT, "build", "world_new.bin")
    open(out, "wb").write(bytes(plane.buf))
    return plane


if __name__ == "__main__":
    p = build()
    import world as W
    n = {}
    for ty in range(-14, 12):
        for tx in range(-14, 12):
            c = W.cls_of(p.get(tx, ty))
            n[c] = n.get(c, 0) + 1
    print("build/world_new.bin —", {W.CLASS_NAMES[k]: v for k, v in sorted(n.items())},
          "γύρω από την αποικία")
