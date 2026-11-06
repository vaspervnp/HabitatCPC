#!/usr/bin/env python3
"""Οι δύο οθόνες πριν από το μενού (βήμα 194, DESIGN §13.6).

Ο παίκτης: «Έχει τώρα αρκετό χώρο για το revive8b.scr, όπως χρησιμοποιείτε στα
άλλα παιχνίδια; Και ένα ακόμα scr ως splash screen?» Διάλεξε: πρώτα το
REVIVE8BIT, μετά μια οθόνη του Habitat, μετά το μενού, η καθεμιά 10
δευτερόλεπτα ή ως το SPACE· και η οθόνη του Habitat φτιαγμένη από τα γραφικά
του ίδιου του παιχνιδιού.

  build/revive.bin   το art/revive8b.scr (το ίδιο σε όλα τα παιχνίδια του
                     REVIVE8BIT) με τα χρώματα του art/revive8b.txt
  build/splash.bin   ο τίτλος, και μια αποικία πάνω σε κόσμο της ερήμου,
                     ζωγραφισμένη από τις αναφορές του παιχνιδιού: το έδαφος
                     όπως στο μενού (tools/menuworld.py), οι θόλοι, οι διάδρομοι,
                     οι δομές και οι άποικοι από το tools/scene.py

Και τα δύο: 16.384 bytes οθόνης Mode 0 όπως στο #C000 (χωρίς μετατόπιση), και
μετά τα 16 χρώματα firmware των pens — 16.400 bytes, που ο φορτωτής ξεδιπλώνει
στο SP_TMP της τράπεζας 4 (src/boot.asm) και το μενού αντιγράφει στην οθόνη
(src/menu.asm: mw_screen). Το περίγραμμα μαύρο, όπως στο μενού.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

ART = os.path.join(ROOT, "art")
BUILD = os.path.join(ROOT, "build")

PLANET = 0                  # η έρημος
WORLD = 2                   # ο τρίτος κόσμος της ερήμου στη σειρά του μενού


def revive_inks():
    """Τα 16 χρώματα firmware του art/revive8b.txt, από τον πίνακά του: «pen
    firmware hardware χρώμα», μία γραμμή ανά pen."""
    inks = {}
    for line in open(os.path.join(ART, "revive8b.txt"), encoding="ascii"):
        m = re.match(r"\s*(\d+)\s+(\d+)\s+&[0-9A-Fa-f]+\s", line)
        if m:
            inks[int(m.group(1))] = int(m.group(2))
    if sorted(inks) != list(range(16)) or max(inks.values()) > 26:
        sys.exit("το art/revive8b.txt δεν έχει 16 pens με χρώματα firmware 0-26")
    return [inks[p] for p in range(16)]


def revive():
    scr = open(os.path.join(ART, "revive8b.scr"), "rb").read()
    if len(scr) != 0x4000:
        sys.exit(f"το art/revive8b.scr έχει {len(scr)} bytes, όχι 16.384")
    return scr + bytes(revive_inks())


def put(rec, i, size, fields):
    for f, v in fields.items():
        rec[i * size + f] = v & 0xFF


def colony(tx, ty):
    """Η αποικία της οθόνης, σε μισά tiles του κόσμου: ένα μεγάλο θερμοκήπιο
    στη μέση, ένας μικρός θόλος οξυγόνου αριστερά και ένα μικρό κατάλυμα
    δεξιά, με διαδρόμους δύο tiles· ένα ηλιακό και μια ανεμογεννήτρια από
    κάτω, και το σκάφος πάνω δεξιά. Το κέντρο του μεγάλου είναι στη μέση της
    οθόνης, 120 γραμμές κάτω."""
    import scene as S
    import colony as CL
    c = S.Colony()
    cx, cy = 2 * tx + 20, 2 * ty + 15
    domes = [(cx, cy, 2, S.R_GREENHOUSE), (cx - 16, cy, 0, 4), (cx + 16, cy, 0, 2)]
    for d, (x, y, sz, rm) in enumerate(domes):
        put(c.dome, d, S.DOME_REC, {S.D_CX: x, S.D_CY: y, S.D_SIZE: sz, S.D_ROOM: rm,
                                    S.D_STATE: S.DS_ACTIVE, S.D_INTEG: 255})
        for s in range(8):
            c.dome[d * S.DOME_REC + S.D_MACH + s] = S.NO_MACH
        for s in range([1, 4, 8][sz]):
            if rm == S.R_GREENHOUSE:
                m = (s * 5 + d) % 12            # οκτώ διαφορετικά φυτά
            else:
                m = S.MACH.index("oxygen" if rm == 4 else "beds")
            c.dome[d * S.DOME_REC + S.D_MACH + s] = m
            c.dome[d * S.DOME_REC + S.D_HEALTH + s] = 200
    c.n_dome = len(domes)
    put(c.corr, 0, S.CORR_REC, {S.C_A: 1, S.C_B: 0, S.C_DIR: CL.E_DIR, S.C_LEN: 2})
    put(c.corr, 1, S.CORR_REC, {S.C_A: 0, S.C_B: 2, S.C_DIR: CL.E_DIR, S.C_LEN: 2})
    c.n_corr = 2
    structs = [(cx - 15, cy + 7, "solar", 2), (cx + 15, cy + 7, "turbine", 2),
               (cx + 15, cy - 9, "ship", 0)]
    for i, (x, y, kind, sz) in enumerate(structs):
        put(c.struct, i, S.STRUCT_REC, {S.S_CX: x, S.S_CY: y,
                                        S.S_KIND: S.STRUCT_KINDS.index(kind),
                                        S.S_SIZE: sz, S.S_STATE: S.DS_ACTIVE,
                                        S.S_INTEG: 255})
    c.n_struct = len(structs)
    return c


def habitat():
    """(ο καμβάς, τα 16 χρώματα): η οθόνη του Habitat."""
    import scene as S
    import colony as CL
    import menuworld as MW
    import worldgen_ref
    from refrender import Canvas
    seed = MW.seeds(PLANET)[WORLD]
    plane = worldgen_ref.generate(seed, PLANET)
    tx, ty = MW.window(plane)
    c = colony(tx, ty)
    CL.stamp(c, plane)                  # τα θεμέλια: έδαφος κάτω από τους θόλους
    cv = Canvas()
    MW.draw_world(cv, plane, tx, ty)    # 20 x 13 tiles, όπως το μενού
    S.draw_objects(cv, S.Assets(), S.Camera(tx, ty), c, S.Clip(0, 0, 80, 200),
                   CL.agents(c, 10))
    # Ο τίτλος του μενού σε διπλό μέγεθος: κελιά των 2 bytes x 4 γραμμών.
    cells = MW.title_cells()
    x0 = (80 - 2 * len(cells[0])) // 2
    for r, row in enumerate(cells):
        for col, v in enumerate(row):
            if v:
                for k in range(4):
                    for j in range(2):
                        cv[x0 + 2 * col + j, 6 + 4 * r + k] = MW.TITLE_INK if v == 2 else 0
    MW.text(cv, (40 - len(MW.SUBTITLE)) // 2, 6, MW.SUBTITLE)
    return cv, MW.palette(PLANET)


def image(cv, pal):
    """Η οθόνη και τα χρώματά της, όπως τα ξεδιπλώνει ο φορτωτής."""
    return cv.to_screen_ram() + bytes(pal)


def write():
    """Τα δύο αρχεία στο build/, και μια εικόνα της οθόνης του Habitat."""
    from palette import pen_rgb
    os.makedirs(BUILD, exist_ok=True)
    open(os.path.join(BUILD, "revive.bin"), "wb").write(revive())
    cv, pal = habitat()
    open(os.path.join(BUILD, "splash.bin"), "wb").write(image(cv, pal))
    cv.to_png(os.path.join(BUILD, "splash.png"), pen_rgb(pal), scale=2)


if __name__ == "__main__":
    write()
    print("build/revive.bin, build/splash.bin, build/splash.png")
