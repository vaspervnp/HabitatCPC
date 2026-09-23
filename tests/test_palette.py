#!/usr/bin/env python3
"""Η μετάφραση firmware -> υλικό, και οι τέσσερις πλανήτες (§8.6, §5.7).

ΤΙ ΔΕΝ ΕΛΕΓΧΕ ΚΑΝΕΙΣ. Ολες οι άλλες δοκιμές συγκρίνουν ΑΡΙΘΜΟΥΣ PEN: ο
renderer γράφει pen 6 και η αναφορά περιμένει pen 6. Κανείς δεν ρωτούσε τι
ΧΡΩΜΑ βγάζει το pen 6 στην οθόνη — και ο πίνακας fw_to_hw είχε τρεις λάθος
εγγραφές από το πρώτο βήμα: οι άποικοι (pen 6, bright yellow) σχεδιάζονταν
σκούρο μπλε.

Η μέθοδος: η οθόνη γεμίζει με μοτίβο όπου το pen n πιάνει n+1 bytes, οπότε
κάθε pen έχει ΓΝΩΣΤΟ μερίδιο pixel. Το framebuffer δίνει χρώματα· τα μερίδια
τα δένουν με pens. Το tools/palette.py λέει τι RGB σημαίνει κάθε αριθμός
firmware και το tools/refrender.py πώς κωδικοποιείται ένα pen σε byte Mode 0 —
καμία νέα παραδοχή, και τα δύο υπάρχουν από πριν.
"""
import collections, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")

from sprites import load_map, load_bin                                  # noqa: E402
from palette import FW_RGB                                              # noqa: E402
from refrender import unpack_pens                                       # noqa: E402

RASM = os.path.expanduser("~/rasm/rasm.exe")
SNA = os.path.join(ROOT, "build", "paltest.sna")
TERRAIN_PENS = [7, 11, 12, 14]                  # §8.6
FAIL = []


def check(ok, msg):
    print(("OK " if ok else "ΛΑΘΟΣ ") + msg)
    if not ok:
        FAIL.append(msg)


def build():
    r = subprocess.run([RASM, "paltest.asm", "-oi", SNA, "-v2", "-s"],
                       cwd=HERE, capture_output=True, text=True)
    if r.returncode or not os.path.exists(SNA):
        sys.exit("rasm απέτυχε:\n" + r.stdout + r.stderr)
    sym = {}
    for line in open(os.path.join(HERE, "rasmoutput.sym"),
                     encoding="utf-8", errors="replace"):
        p = line.split()
        if len(p) >= 2 and p[1].startswith("#"):
            sym[p[0].upper()] = int(p[1][1:], 16)
    return sym


def solid_bytes():
    """Το byte Mode 0 όπου ΚΑΙ ΤΑ ΔΥΟ pixel είναι το pen n."""
    out = {}
    for b in range(256):
        p0, p1 = unpack_pens(b)
        if p0 == p1:
            out[p0] = b
    assert len(out) == 16, out
    return [out[p] for p in range(16)]


def main():
    sym = build()
    from PIL import Image
    from cpc import CPC

    smap, blob = load_map(), load_bin()
    s = smap["palette_fw"]
    base = list(blob[s.off:s.off + s.size])
    s = smap["planet_pens"]
    pens = list(blob[s.off:s.off + s.size])

    solid = solid_bytes()
    # το pen n, n+1 φορές: 136 bytes περίοδος
    period = bytes(b for n in range(16) for b in [solid[n]] * (n + 1))
    fill = (period * (0x4000 // len(period) + 1))[:0x4000]
    # ΚΑΙ έξω από τους πλανήτες: το πρώτο χρώμα εκτός βάσης ήταν το 2, που το
    # ζητούν ο πάγος και η άγονη σελήνη — και το περίγραμμα το έτρωγε από τη
    # μέτρηση.
    used = set(base) | set(pens)
    border = next(c for c in range(27) if c not in used)
    tmp = os.path.join(ROOT, "build", "pal.png")

    m = CPC()
    m.run_frames(30)
    assert m.quickload(SNA), "quickload απέτυχε"

    def shot(planet):
        m.poke(sym["PL_PLANET"], planet if planet is not None else 0xFF)
        m.poke(sym["PL_BORDER"], border)
        m.set_pc(sym["START"])
        m.run_frames(6)
        m.write_ram(0xC000, fill)
        m.run_frames(4)
        m.screenshot(tmp)
        px = list(Image.open(tmp).convert("RGB").getdata())
        h = collections.Counter(px)
        h.pop(near_rgb(FW_RGB[border], h), None)        # το περίγραμμα έξω
        return h

    def near_rgb(want, keys):
        return min(keys, key=lambda c: sum((a - b) ** 2 for a, b in zip(want, c)))

    def fw_of(c):
        return min(range(27), key=lambda i: sum((a - b) ** 2
                                                for a, b in zip(FW_RGB[i], c)))

    def verify(palette, label):
        """Το μερίδιο pixel κάθε χρώματος πρέπει να είναι αυτό που ορίζει το
        μοτίβο. Ποσοστά και όχι κατάταξη: δύο pens μπορεί να ζητούν το ίδιο
        χρώμα (11 και 13 ζητούν και τα δύο το 3) και τότε η σειρά τους είναι
        ισοπαλία, ενώ το ΑΘΡΟΙΣΜΑ των μεριδίων τους είναι ορισμένο."""
        h = shot(None if palette is base else palette_planet)
        share = collections.Counter()
        for pen, fw in enumerate(palette):
            share[fw] += pen + 1
        got = collections.Counter()
        for colour, n in h.items():
            got[fw_of(colour)] += n
        total = sum(got[fw] for fw in share)
        worst, worst_fw = 0.0, None
        for fw, sh in share.items():
            want = sh / sum(share.values())
            have = got.get(fw, 0) / total
            if abs(want - have) > worst:
                worst, worst_fw = abs(want - have), fw
        missing = [fw for fw in share if fw not in got]
        check(not missing and worst < 0.01,
              f"{label}: {len(share)} χρώματα, μέγιστη απόκλιση μεριδίου "
              f"{worst * 100:.2f}% (χρώμα {worst_fw})"
              + (f", ΛΕΙΠΟΥΝ {missing}" if missing else ""))
        return h

    palette_planet = None
    verify(base, "η παλέτα του παιχνιδιού")

    for p in range(4):
        palette_planet = p
        pal = list(base)
        for i, pen in enumerate(TERRAIN_PENS):
            pal[pen] = pens[p * 4 + i]
        verify(pal, f"πλανήτης {p}")

    if FAIL:
        print(f"\nΑΠΟΤΥΧΙΑ — {len(FAIL)}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
