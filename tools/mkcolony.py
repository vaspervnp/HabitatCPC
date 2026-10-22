#!/usr/bin/env python3
"""Φτιάχνει τις εικόνες τραπεζών της ΔΟΚΙΜΗΣ του renderer.

    build/bank6_col.bin   η τράπεζα 6 με τους πίνακες της αποικίας μέσα
    build/bank5_col.bin   η τράπεζα 5 με τους διαδρόμους της (βήμα 154)
    build/world_col.bin   το επίπεδο κόσμου με τα θεμέλια των θόλων
    build/col_top.asm     το COL_CTOP: το όριο σάρωσης των διαδρόμων της (βήμα 159)

Οι πίνακες μπαίνουν στην ΕΙΚΟΝΑ και όχι με staging κώδικα, για έναν λόγο που
μετράει εδώ: η περιοχή #C000 που χρησιμοποιούσε το simtest για staging είναι
τώρα η ΟΘΟΝΗ.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import colony, scene as S, world as W, pack


def bank_offsets():
    """Πού κάθεται κάθε πίνακας μέσα στην τράπεζα 6 — και ο πίνακας των
    διαδρόμων, από το βήμα 154 στην τράπεζα 5: η εικόνα της (από το
    pack.BANK5_BASE) και η θέση του μέσα της, στο off["corr5"]."""
    arena, bank1, bank5, bank6, bank7, ptr, images, free, report = pack.pack()
    off = {}
    for r in bank5:
        if r.name == "corr_tbl":
            off["corr5"] = r.addr - pack.BANK5_BASE
    off["bank5"] = images["bank5"]
    for r in bank6:
        off[r.name] = r.addr - pack.WINDOW_BASE
    return images["bank6"], off


def build(seed=1):
    img, off = bank_offsets()
    img = bytearray(img)
    c = colony.build()
    ag = colony.agents(c)
    img[off["dome_tbl"]:off["dome_tbl"] + len(c.dome)] = c.dome
    img[off["struct_tbl"]:off["struct_tbl"] + len(c.struct)] = c.struct
    blob = ag.to_bytes()
    img[off["agent_fields"]:off["agent_fields"] + len(blob)] = blob

    plane = W.Plane(W.byte(W.GROUND))
    # Λίγο έδαφος που να ΜΗΝ είναι μονότονο: αλλιώς ένα λάθος στο autotile
    # κρύβεται μέσα σε 200 ίδια tiles.
    for ty in range(-64, 64):
        for tx in range(-64, 64):
            cls = W.GROUND
            if (tx * 7 + ty * 3) % 23 == 0:
                cls = W.ROCK
            elif (tx + ty) % 31 == 0:
                cls = W.DUST
            plane.set(tx, ty, W.byte(cls, decor=(tx * 5 + ty) & 3))
    colony.stamp(c, plane)

    out = os.path.join(ROOT, "build")
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, "bank6_col.bin"), "wb").write(bytes(img))
    b5 = bytearray(off["bank5"])
    b5[off["corr5"]:off["corr5"] + len(c.corr)] = c.corr
    open(os.path.join(out, "bank5_col.bin"), "wb").write(bytes(b5))
    open(os.path.join(out, "world_col.bin"), "wb").write(bytes(plane.buf))
    # ΤΟ ΟΡΙΟ ΣΑΡΩΣΗΣ ΤΩΝ ΔΙΑΔΡΟΜΩΝ (βήμα 159, CT_TOP): στο παιχνίδι το γράφει
    # το ct_recount όταν φορτώνεται μια αποικία — η ψηλότερη εγγραφή που δεν
    # είναι άδεια, +1. Το objtest και το uitest δεν το τρέχουν· το βάζουν στη
    # σελίδα 2 τους από εδώ, αλλιώς θα είχαν το 128 της εικόνας.
    used = [i for i in range(pack.MAX_CORR) if c.corr[i * S.CORR_REC] != S.CT_EMPTY]
    with open(os.path.join(out, "col_top.asm"), "w", encoding="utf-8") as f:
        f.write(f"COL_CTOP equ {max(used) + 1 if used else 1}\n")
    return c, ag, plane


if __name__ == "__main__":
    c, ag, plane = build()
    print(f"αποικία: {c.n_dome} θόλοι, {c.n_corr} διάδρομοι, {c.n_struct} δομές")
