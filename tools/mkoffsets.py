#!/usr/bin/env python3
"""Emit build/sprite_offsets.asm from assets/sprites_map.txt.

Hand-typed offsets go stale the first time a sprite moves. These do not.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sprites import load_map, ROOT

out = os.path.join(ROOT, "build", "sprite_offsets.asm")
smap = load_map()
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "w", encoding="utf-8") as f:
    f.write("; ΠΑΡΑΓΕΤΑΙ από tools/mkoffsets.py — μην το επεξεργάζεσαι.\n")
    f.write(f"; {len(smap)} sprites από assets/sprites_map.txt\n\n")
    for name, s in sorted(smap.items(), key=lambda kv: kv[1].off):
        f.write(f"SPR_{name:<22} equ #{s.off:04X}\n")
        f.write(f"SZ_{name:<23} equ {s.size}\n")
print(f"{out}: {len(smap)} sprites")

# --- σταθερές από το assets/sprites.asm -------------------------------------
# Το sprites.asm είναι 7.000 γραμμές με τα ΔΕΔΟΜΕΝΑ μέσα· δεν γίνεται include
# για να πάρουμε δυο equ. Τις βγάζουμε σε δικό τους αρχείο.
import re
src = os.path.join(ROOT, "assets", "sprites.asm")
dst = os.path.join(ROOT, "build", "sprite_consts.asm")
rx = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s+equ\s+(\S+)", re.I)
n = 0
with open(dst, "w", encoding="utf-8") as f:
    f.write("; ΠΑΡΑΓΕΤΑΙ από tools/mkoffsets.py — σταθερές του assets/sprites.asm.\n\n")
    for line in open(src, encoding="utf-8"):
        m = rx.match(line)
        if m:
            f.write(f"{m.group(1):<12} equ {m.group(2)}\n")
            n += 1
print(f"{dst}: {n} σταθερές")
