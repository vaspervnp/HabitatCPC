#!/usr/bin/env python3
"""Κάθε εξωτερική δομή φαίνεται πάνω στο έδαφος κάθε πλανήτη (§8.6).

Τα pens 7, 11, 12, 14 του εδάφους αλλάζουν ανά πλανήτη, και μία από τις
τέσσερις αλλαγές μπορεί να πέσει πάνω στο χρώμα που έχει μια δομή στην άκρη
της. Τότε η άκρη χάνεται στο έδαφος και η δομή φαίνεται μικρότερη ή κομμένη —
χωρίς κανένα σφάλμα πουθενά. Ετσι χανόταν η γάστρα του πλοίου στον barren ως
το βήμα 50: pen 10 (Cyan) στην άκρη, Cyan και η βάση του εδάφους (pen 7).

Ο έλεγχος: κάθε pixel στην άκρη του σχήματος (αδιαφανές, με διαφανές ή έξω
από το sprite γείτονα πάνω/κάτω/δεξιά/αριστερά) δεν επιτρέπεται να έχει το
χρώμα της βάσης του εδάφους, σε κανέναν πλανήτη. Τα sprites διαβάζονται από
το assets/sprites.bin, με τη μάσκα τους, και τα χρώματα από τα palette_fw και
planet_pens — ό,τι φορτώνει το παιχνίδι.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))

from sprites import load_map, load_bin, rows                            # noqa: E402
from refrender import unpack_pens                                       # noqa: E402
from palette import FW_RGB                                              # noqa: E402

TERRAIN_PENS = [7, 11, 12, 14]                  # §8.6
FAIL = []


def check(ok, msg):
    print(("OK " if ok else "ΛΑΘΟΣ ") + msg)
    if not ok:
        FAIL.append(msg)


def decode(blob, spr):
    """Sprite με μάσκα -> γραμμές από pens, None όπου είναι διαφανές."""
    out = []
    for r in rows(blob, spr):
        row = []
        for i in range(0, len(r), 2):
            mp, dp = unpack_pens(r[i]), unpack_pens(r[i + 1])
            row += [None if mp[k] == 15 else dp[k] for k in range(2)]
        out.append(row)
    return out


def edge(px):
    """Τα pens της άκρης του σχήματος."""
    h, w = len(px), len(px[0])
    for y in range(h):
        for x in range(w):
            if px[y][x] is None:
                continue
            if any(not (0 <= y + dy < h and 0 <= x + dx < w) or px[y + dy][x + dx] is None
                   for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                yield px[y][x]


def lost(px, palettes):
    """{πλανήτης: πόσα pixel της άκρης έχουν το χρώμα της βάσης του εδάφους}"""
    e = list(edge(px))
    out = {}
    for name, fw in palettes.items():
        ground = FW_RGB[fw[7]]
        n = sum(FW_RGB[fw[p]] == ground for p in e)
        if n:
            out[name] = n
    return out


def main():
    smap, blob = load_map(), load_bin()
    s = smap["palette_fw"]
    base = list(blob[s.off:s.off + s.size])
    s = smap["planet_pens"]
    pp = list(blob[s.off:s.off + s.size])
    asm = open(os.path.join(ROOT, "assets", "sprites.asm"), encoding="utf-8").read()
    names = [n.strip() for n in
             next(l for l in asm.splitlines() if l.startswith("PLANETS"))
             .split(";", 1)[1].split(",")]
    assert len(names) * 4 == len(pp), names

    def palette_of(i, ground=None):
        fw = list(base)
        for pen, f in zip(TERRAIN_PENS, pp[4 * i:4 * i + 4]):
            fw[pen] = f
        if ground is not None:
            fw[7] = ground
        return fw

    palettes = {n: palette_of(i) for i, n in enumerate(names)}
    structs = [n for n, sp in smap.items()
               if sp.fmt == "mask+data" and smap["solar_s"].off <= sp.off <= smap["ship"].off]
    check("ship" in structs and len(structs) >= 15,
          "%d εξωτερικές δομές με μάσκα, από το solar_s ως το ship" % len(structs))
    for n in structs:
        px = decode(blob, smap[n])
        bad = lost(px, palettes)
        check(not bad, "%-12s %3d pixel άκρης, κανένα στο χρώμα του εδάφους%s"
              % (n, len(list(edge(px))),
                 "" if not bad else " — ΧΑΝΟΝΤΑΙ: %s" % bad))

    # ΑΡΝΗΤΙΚΑ
    # 1. Το πλοίο χωρίς το περίγραμμα του βήματος 50: το pen 1 το έχει ΜΟΝΟ
    #    εκεί, οπότε σβήνοντάς το μένει το παλιό σχήμα, γάστρα στην άκρη.
    ship = decode(blob, smap["ship"])
    bare = [[None if p == 1 else p for p in row] for row in ship]
    assert bare != ship
    bad = lost(bare, palettes)
    check(set(bad) == {names[3]},
          "ΑΡΝΗΤΙΚΟ: το πλοίο χωρίς περίγραμμα χάνεται στον %s — %s"
          % (names[3], bad or "ΔΕΝ ΠΙΑΣΤΗΚΕ"))
    # 2. Ενας πλανήτης με βάση εδάφους το γκρι (fw 13) του πλαισίου των ηλιακών.
    grey = dict(palettes, test=palette_of(0, ground=base[4]))
    bad = lost(decode(blob, smap["solar_m"]), grey)
    check(set(bad) == {"test"},
          "ΑΡΝΗΤΙΚΟ: έδαφος στο γκρι fw %d, το solar_m χάνεται — %s"
          % (base[4], bad or "ΔΕΝ ΠΙΑΣΤΗΚΕ"))

    n = len(structs) + 3
    print("\n%d/%d" % (n - len(FAIL), n))
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
