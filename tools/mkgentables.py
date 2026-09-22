#!/usr/bin/env python3
"""build/gen_tables.asm — οι πίνακες της γεννήτριας, από την αναφορά.

Ο Z80 και η Python ΠΡΕΠΕΙ να δουν τα ίδια νούμερα. Παράγονται εδώ, μία φορά.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import worldgen_ref as G
from sprites import ROOT

out = os.path.join(ROOT, "build", "gen_tables.asm")
os.makedirs(os.path.dirname(out), exist_ok=True)


def sb(v):
    return v & 0xFF


with open(out, "w", encoding="utf-8") as f:
    f.write("; ΠΑΡΑΓΕΤΑΙ από tools/mkgentables.py — μην το επεξεργάζεσαι.\n")
    f.write(f"; γεννήτρια έκδοση {G.GEN_VERSION}\n\n")
    f.write(f"GEN_VERSION equ {G.GEN_VERSION}\n")
    f.write(f"GEN_MID     equ {G.MID}\n")
    f.write(f"GEN_COARSE  equ {G.COARSE}\n")
    f.write(f"GEN_MSALT   equ {G.MOIST_SALT}\n")
    f.write(f"GEN_OSALT   equ {G.ORE_SALT}\n")
    f.write(f"GEN_DIRS    equ {G.DIRS}\n")
    f.write(f"GEN_ANCHORS equ {G.ANCHORS}\n")
    f.write(f"R_PLATEAU   equ {G.R_PLATEAU}\n")
    f.write(f"R_BLEND     equ {G.R_BLEND}\n")
    f.write(f"R_RIM       equ {G.R_RIM}\n\n")

    f.write("; 24 κατευθύνσεις, κλίμακα 64, προσημασμένες\ngen_dir:\n")
    for dx, dy in G.DIR:
        f.write(f"        db {sb(dx):>4}, {sb(dy):>4}\n")

    f.write("\n; ανά πλανήτη: W2 βαθύ, W1 ρηχό, M1 βράχος, M2 βουνό, F γονιμ., OT φλέβα\n")
    f.write("gen_planets:\n")
    for p in G.PLANETS:
        f.write("        db " + ",".join(f"{v:>4}" for v in p) + "\n")

    # (kind, lo, mask) ανά άγκυρα· kind 0=lake 1=ridge 2=basin 3=wild
    KIND = {"lake": 0, "ridge": 1, "basin": 2, "wild": 3}
    spec = [("lake", 12, 15), ("lake", 12, 15), ("ridge", 14, 15),
            ("ridge", 14, 15), ("basin", 8, 7), ("wild", 20, 15)]
    f.write("\n; ανά άγκυρα: είδος, ελάχιστη ακτίνα, mask τυχαιότητας\ngen_spec:\n")
    for k, lo, mask in spec:
        f.write(f"        db {KIND[k]}, {lo:>3}, {mask:>3}\n")

    f.write("\n; βάρος ανάμειξης για r = R_PLATEAU..R_BLEND\ngen_blend:\n        db ")
    f.write(",".join(str(((r - G.R_PLATEAU) * 255) // (G.R_BLEND - G.R_PLATEAU))
                     for r in range(G.R_PLATEAU, G.R_BLEND + 1)))

    f.write("\n\n; ανύψωση χείλους για r = R_RIM..64\ngen_rim:\n        db ")
    f.write(",".join(str(min(255, (r - G.R_RIM + 1) * 40)) for r in range(G.R_RIM, 65)))
    f.write("\n")
print(f"{out}")
