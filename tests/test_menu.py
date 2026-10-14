#!/usr/bin/env python3
"""Το μενού πάνω σε κομμάτι κόσμου (βήμα 130, DESIGN §13.2): το MENU.BIN
μόνο του, χωρίς δίσκο.

Ο παίκτης: «θέλω το μενού να έχει και γραφικά, ζωγραφισμένο πάνω σε τμήμα
κόσμου — ένας τυχαίος κόσμος κάθε φορά». Τι ελέγχεται εδώ (ό,τι θέλει
δίσκο, το tests/test_disc.py):

  1. ΟΙ ΚΟΣΜΟΙ. Οκτώ ανά πλανήτη, ο πλανήτης του καθενός αυτός που βγάζει
     το seed του στο gen_entry, κανένα seed δύο φορές, και κανένα κομμάτι
     δεν πιάνει κρατήρα (το tile του δεν έχει διπλές γραμμές).
  2. Η ΣΧΕΔΙΑΣΗ. Ο Z80 (mw_show) ζωγραφίζει και τους MW_N κόσμους με το μενού
     byte προς byte όπως το tools/menuworld.py, που παίρνει τα tiles από τον
     ίδιο τον κόσμο της γεννήτριας αναφοράς — όχι από τα δεδομένα του
     MENU.BIN — με τη σχεδίαση του tests/test_object.py. Με διαλεγμένη κάθε
     φορά άλλη γραμμή. Και το πάνελ της φόρτωσης (mw_load) για καθεμιά.
  3. ΤΟ ΚΟΣΤΟΣ: η σχεδίαση κρατά λιγότερο από το ταβάνι· ο παίκτης τη
     βλέπει μόνο τελειωμένη (μαύρη παλέτα ως το τέλος, στο mw_run).
  4. ΑΡΝΗΤΙΚΑ, ένα για κάθε κομμάτι της αποκωδικοποίησης: οι γείτονες του
     autotile ανάποδα, το βαθύ νερό όχι νερό, η φλέβα χωρίς τα bits της, οι
     γραμμές του tile μία φορά, το RLE χωρίς το bit της φλέβας, η τελευταία
     σειρά ολόκληρη, η διαλεγμένη ίσια, το περίγραμμα του τίτλου κίτρινο, το
     BUILDING THE WORLD αναμμένο από την αρχή.
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")

import menuworld as MW                                                  # noqa: E402

RASM = os.path.expanduser("~/rasm/rasm.exe")
FAIL = []
PROBE = 0x8000
SHOW_CEIL = 500_000         # µs (μετρημένο: ~466.000)


def check(ok, msg):
    print(("OK " if ok else "ΛΑΘΟΣ ") + msg)
    if not ok:
        FAIL.append(msg)


def build():
    MW.write()
    src = os.path.join(ROOT, "src")
    r = subprocess.run([RASM, "menu.asm", "-oi", os.path.join(ROOT, "build", "menu.sna"),
                        "-v2", "-s", "-os", os.path.join(ROOT, "build", "menu.sym")],
                       cwd=src, capture_output=True, text=True)
    if r.returncode:
        sys.exit("rasm απέτυχε:\n" + r.stdout + r.stderr)
    sym = {}
    for line in open(os.path.join(ROOT, "build", "menu.sym"), encoding="utf-8",
                     errors="replace"):
        p = line.split()
        if len(p) >= 2 and p[1].startswith("#"):
            sym[p[0].upper()] = int(p[1][1:], 16)
    return sym, open(os.path.join(ROOT, "build", "menu.bin"), "rb").read()


class Rig:
    """BASIC ως το Ready, και το MENU.BIN στο MW_ORG: οι δύο είσοδοι χωρίς
    firmware καλούνται από ένα probe στο #8000, με κλειστές διακοπές."""

    def __init__(self, blob):
        from cpc import CPC
        self.m = CPC()
        self.m.run_frames(300)
        self.blob = blob

    def call(self, entry, a, b=0, patch=(), step=100):
        m = self.m
        img = bytearray(self.blob)
        for at, v in patch:
            img[at - MW.geom()["MW_ORG"]] = v
        m.write_ram(MW.geom()["MW_ORG"], bytes(img))
        code = bytes([0xF3, 0x31, 0x00, 0x8F, 0x3E, a, 0x06, b,
                      0xCD, entry & 255, entry >> 8, 0x18, 0xFE])
        m.write_ram(PROBE, code)
        m.set_pc(PROBE)
        end, t = PROBE + len(code) - 2, 0
        while m.pc != end and t < 3_000_000:
            m.run_us(step)
            t += step
        return t, bytes(m.read_ram(0xC000, 0x4000))


def diff(a, b):
    return sum(1 for x, y in zip(a, b) if x != y)


def main():
    sym, blob = build()
    g = MW.geom()
    ws = MW.worlds()

    # --- 1. οι κόσμοι --------------------------------------------------------
    per = [sum(1 for w in ws if w[1] == p) for p in range(4)]
    seeds = [w[0] for w in ws]
    check(len(ws) == g["MW_N"] and per == [MW.PER_PLANET] * 4
          and all(MW.planet_of(s) == p for s, p, *_ in ws)
          and len(set(seeds)) == len(seeds),
          f"{len(ws)} κόσμοι, ανά πλανήτη {per}, ο πλανήτης του καθενός από το "
          f"seed του (H xor L), κανένα seed δύο φορές")
    import world as WD
    craters = [i for i, (s, p, tx, ty, pl) in enumerate(ws)
               if any(WD.cls_of(pl.get(tx + c, ty + r)) >= MW.TILE_CLASSES
                      for r in range(g["MW_ROWS"]) for c in range(g["MW_COLS"]))]
    check(not craters, f"κανένα κομμάτι με κρατήρα ή foundation ({craters})")
    size = len(blob)
    end = sym["ZZ_MENU_END"] + (g["MW_COLS"] + 2) * (g["MW_ROWS"] + 2)
    check(end <= 0x8000,
          f"MENU.BIN {size} bytes από το #{g['MW_ORG']:04X}, με το παράθυρο των "
          f"κλάσεων ως το #{end:04X} (ταβάνι #8000)")

    # --- 2. η σχεδίαση -------------------------------------------------------
    rig = Rig(blob)
    show, load = sym["MW_SHOW_E"], sym["MW_LOAD_E"]
    bad = []
    for k in range(g["MW_N"]):
        sel = k % 5
        _, got = rig.call(show, k, sel)
        n = diff(got, MW.screen_menu(k, sel).to_screen_ram())
        if n:
            bad.append((k, n))
    check(not bad, f"ο Z80 ζωγραφίζει και τους {g['MW_N']} κόσμους με το μενού όπως "
                   f"η αναφορά, byte προς byte" + (f" — λάθος {bad[:6]}" if bad else ""))
    bad = []
    for sel in range(5):
        k = 7 * sel + 3
        rig.call(show, k, sel)
        _, got = rig.call(load, sel)
        n = diff(got, MW.screen_loading(k, sel).to_screen_ram())
        if n:
            bad.append((sel, n))
    check(not bad, "και το πάνελ της φόρτωσης για κάθε επιλογή: ο κόσμος, LOADING, "
                   "η άδεια μπάρα, BUILDING THE WORLD σβηστό"
                   + (f" — λάθος {bad}" if bad else ""))

    # --- 3. το κόστος ----------------------------------------------------------
    worst = max(rig.call(show, k, 0, step=10)[0] for k in (0, 9, 18, 27))
    check(worst <= SHOW_CEIL,
          f"η σχεδίαση του μενού κρατά ως {worst} µs (ταβάνι {SHOW_CEIL}), με "
          f"μαύρη παλέτα ως το τέλος της")

    # --- 4. αρνητικά -------------------------------------------------------------
    def find(name, pat, nth=0, span=200):
        base = sym[name] - g["MW_ORG"]
        raw = blob[base:base + span]
        k = -1
        for _ in range(nth + 1):
            k = raw.find(bytes(pat), k + 1)
            assert k >= 0, f"δεν βρέθηκε το {pat} στο {name}"
        return sym[name] + k

    dec = sym["MW_DEC"]
    w = find("MTL_AUTO", [0x01, 0xFF, 0xFF])
    e = find("MTL_AUTO", [0x01, 0x01, 0x00])
    ldi4 = [0xED, 0xA0] * 4
    l2 = find("MTL_LN", ldi4, 1)
    negs = [
        ("τους γείτονες δυτικά και ανατολικά ανάποδα",
         [(w + 1, 1), (w + 2, 0), (e + 1, 0xFF), (e + 2, 0xFF)], None),
        ("το βαθύ νερό όχι νερό (ret στο mw_fam)",
         [(find("MW_FAM", [0xC0]), 0xC9)], None),
        ("τη φλέβα χωρίς τα bits decor της",
         [(find("MTL_ORE", [0xCD, dec & 255, dec >> 8]) + k, 0) for k in range(3)], None),
        ("κάθε γραμμή του tile μία φορά",
         [(l2 + k, 0) for k in range(8)], None),
        ("το RLE χωρίς το bit της φλέβας (and 7)",
         [(find("MW_WORLD", [0xE6, 0x0F]) + 1, 7)], None),
        ("την τελευταία σειρά ολόκληρη (16 γραμμές)",
         [(find("MWT_ROW", [0x3E, 0x08]) + 1, 16)], None),
        ("τη διαλεγμένη ίσια (XOR 0)",
         [(find("MW_OPT", [0x3E, 0xF0]) + 1, 0)], None),
        ("το περίγραμμα του τίτλου κίτρινο",
         [(find("MW_TITLE", [0x3D, 0x28]) + k, 0) for k in (1, 2)], None),
        ("το BUILDING THE WORLD αναμμένο από την αρχή",
         [(find("MW_LOAD", [0x06, 0x3F]) + 1, 0xFF)], "load"),
    ]
    for label, patch, what in negs:
        n = 0
        for k in (2, 13, 21, 30):
            sel = k % 5
            if what == "load":
                rig.call(show, k, sel)
                _, got = rig.call(load, sel, patch=patch)
                n += diff(got, MW.screen_loading(k, sel).to_screen_ram())
            else:
                _, got = rig.call(show, k, sel, patch=patch)
                n += diff(got, MW.screen_menu(k, sel).to_screen_ram())
        check(n > 0, f"ΑΡΝΗΤΙΚΟ: με {label} διαφέρουν {n} bytes σε τέσσερις κόσμους")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
