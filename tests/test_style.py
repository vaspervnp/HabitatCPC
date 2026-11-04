#!/usr/bin/env python3
"""Το στυλ «λευκό μέταλλο, φως από πάνω» (βήμα 178, DESIGN §8.7).

Ο παίκτης διάλεξε την πρόταση Α στο στυλ του Planetbase, με φως από πάνω: οι
θόλοι και οι δακτύλιοι είναι ένα τεταρτημόριο καθρεφτισμένο τέσσερις φορές,
οπότε φως από μία μεριά δεν χωρούσε. Οι κανόνες, διαβασμένοι από το
assets/sprites.bin — ό,τι φορτώνει το παιχνίδι:

  1. Οι διάδρομοι, οι δακτύλιοι και τα σημεία σύνδεσης έχουν λευκό σώμα (pen 5)
     και γκρι άκρες (pen 4).
  2. Ο θόλος είναι γυαλί: πέρα από το χείλος του (pen 3), λωρίδα στο ίδιο pen
     προς τα μέσα, και λάμψεις (pen 5) έξω από τα κουτιά, σε κάθε μέγεθος.
  3. Κάθε φιγούρα πάνω στον δακτύλιο έχει σκιά: μαύρο κάτω δεξιά από κάθε pixel
     της, όπου εκεί δεν είναι φιγούρα. Πάνω στο λευκό ο κίτρινος άποικος αλλιώς
     χάνεται.
  4. Το έδαφος είναι ήσυχο: χώμα, σκόνη και πέτρα με λιγότερα σημάδια από όσα
     είχαν ως το βήμα 177, και η άκρη του χώματος όλη βάση, ώστε οι παραλλαγές
     του να κουμπώνουν σε κάθε διάταξη.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))

from sprites import load_map, load_bin, rows                            # noqa: E402
from refrender import unpack_pens                                       # noqa: E402
from palette import FW_RGB                                              # noqa: E402

FAIL = []
GREY, WHITE, RIM, FLOOR = 4, 5, 3, 2
# Πόσα pixels που δεν είναι βάση επιτρέπονται ανά tile. Ως το βήμα 177: χώμα
# 12-14, σκόνη 24-46, πέτρα 50-54· από τότε 0-8, 16-20, 18-24.
QUIET = {"ground": 8, "dust": 20, "rock": 24}


def check(ok, msg):
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ ") + msg)
    if not ok:
        FAIL.append(msg)


def decode(blob, spr):
    """-> γραμμές από pens· None όπου η μάσκα το αφήνει διαφανές."""
    out = []
    for r in rows(blob, spr):
        row = []
        if spr.masked:
            for i in range(0, len(r), 2):
                mp, dp = unpack_pens(r[i]), unpack_pens(r[i + 1])
                row += [None if mp[k] == 15 else dp[k] for k in range(2)]
        else:
            for b in r:
                row += list(unpack_pens(b))
        out.append(row)
    return out


def lum(rgb):
    """Σχετική φωτεινότητα (WCAG), για τον λόγο αντίθεσης."""
    def ch(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)))
    return (lb + 0.05) / (la + 0.05)


def corridors(smap, blob):
    """1. Λευκό σώμα, γκρι άκρη, και στα τρία σχήματα και στις πόρτες."""
    h = decode(blob, smap["corr_h"])
    check(all(p == GREY for p in h[0]) and all(p == GREY for p in h[7]),
          "corr_h: πάνω και κάτω γραμμή γκρι (pen 4)")
    check(all(p == WHITE for row in h[1:7] for p in row),
          "corr_h: οι έξι μεσαίες γραμμές λευκές (pen 5)")
    v = decode(blob, smap["corr_v"])
    check(all(row[0] == GREY and row[3] == GREY and row[1] == WHITE and row[2] == WHITE
              for row in v), "corr_v: γκρι αριστερά και δεξιά, λευκό στη μέση")
    for name in ("corr_dr", "corr_dl", "ring_s_nw", "ring_m_nw", "ring_l_nw",
                 "conn_n", "conn_ne", "conn_e"):
        px = decode(blob, smap[name])
        used = {p for row in px for p in row if p is not None}
        nw = sum(p == WHITE for row in px for p in row)
        ng = sum(p == GREY for row in px for p in row)
        check(used <= {GREY, WHITE} and nw >= ng,
              "%-9s μόνο γκρι και λευκό, %3d λευκά >= %3d γκρι" % (name, nw, ng))


def glass(smap, blob):
    """2. Το γυαλί: pen 3 και μακριά από το χείλος, και λάμψεις που φαίνονται
    έξω από τα κουτιά (της διάταξης του CPCArt: interior_ofs δεν τα έχει όλα,
    οπότε μετριούνται οι λάμψεις του τεταρτημορίου και φτάνει να υπάρχουν)."""
    for z in "sml":
        px = decode(blob, smap[f"dome_{z}_nw"])
        h, w = len(px), len(px[0])

        def edge(x, y):
            return any(not (0 <= x + dx < w and 0 <= y + dy < h) or px[y + dy][x + dx] is None
                       for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        rim = sum(1 for y in range(h) for x in range(w) if px[y][x] == RIM and edge(x, y))
        band = sum(1 for y in range(h) for x in range(w) if px[y][x] == RIM and not edge(x, y))
        lit = sum(p == WHITE for row in px for p in row)
        check(band >= rim, "dome_%s: λωρίδα %3d pixels πέρα από το χείλος των %d" % (z, band, rim))
        check(lit >= 4, "dome_%s: %d pixels λάμψης στο τεταρτημόριο" % (z, lit))
    # ΑΡΝΗΤΙΚΟ: ο θόλος του βήματος 177, επίπεδο δάπεδο — η λωρίδα σβήνει μέσα
    # στο δάπεδο και δεν μένει τίποτα πέρα από το χείλος.
    px = decode(blob, smap["dome_l_nw"])
    h, w = len(px), len(px[0])
    flat = [[FLOOR if p in (WHITE, RIM) and all(
        0 <= x + dx < w and 0 <= y + dy < h and px[y + dy][x + dx] is not None
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))) else p
        for x, p in enumerate(row)] for y, row in enumerate(px)]
    band = sum(1 for y in range(h) for x in range(w) if flat[y][x] == RIM and all(
        0 <= x + dx < w and 0 <= y + dy < h and flat[y + dy][x + dx] is not None
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))))
    check(band == 0, "ΑΡΝΗΤΙΚΟ: ο θόλος με επίπεδο δάπεδο έχει %d pixels λωρίδας — δεν περνά" % band)


def shadows(smap, blob, fw, strip=False):
    """3. -> πόσες φιγούρες χωρίς σκιά. Με strip=True η σκιά σβήνεται πρώτα (αρνητικό)."""
    names = ["colonist", "biologist", "medic", "guard", "carrier", "driller",
             "engineer", "constructor"]
    bad = []
    for z in "sml":
        for t in range(8):
            e = decode(blob, smap[f"slot_{z}_{t}_empty"])
            for n in names:
                f = decode(blob, smap[f"slot_{z}_{t}_{n}"])
                if strip:
                    f = [[e[y][x] if f[y][x] == 0 and e[y][x] != 0 else f[y][x]
                          for x in range(4)] for y in range(8)]
                body = {(x, y) for y in range(8) for x in range(4)
                        if f[y][x] != e[y][x] and f[y][x] != 0}
                miss = [(x, y) for (x, y) in body
                        if x + 1 < 4 and y + 1 < 8 and (x + 1, y + 1) not in body
                        and f[y + 1][x + 1] != 0]
                if miss:
                    bad.append((z, t, n))
    return bad


def figures(smap, blob, fw):
    bad = shadows(smap, blob, fw)
    check(not bad, "οι φιγούρες στον δακτύλιο: σκιά κάτω δεξιά σε όλες τις 3 x 8 x 8%s"
          % ("" if not bad else " — ΛΕΙΠΕΙ: %s" % bad[:4]))
    yel = contrast(FW_RGB[fw[6]], FW_RGB[fw[WHITE]])
    check(yel < 1.5, "γιατί: ο κίτρινος άποικος πάνω στο λευκό, αντίθεση %.2f προς 1" % yel)
    bad = shadows(smap, blob, fw, strip=True)
    check(len(bad) == 3 * 8 * 8,
          "ΑΡΝΗΤΙΚΟ: χωρίς τη σκιά καμία φιγούρα δεν περνά — %d από %d" % (len(bad), 3 * 8 * 8))


def terrain(smap, blob):
    """4. Ήσυχο έδαφος, που κουμπώνει."""
    for cls in ("ground", "dust", "rock"):
        for v in range(4):
            px = decode(blob, smap[f"tile_{cls}_{v}"])
            marks = sum(p != 7 for row in px for p in row)
            border = [px[y][x] for y in range(16) for x in range(8)
                      if x in (0, 7) or y in (0, 15)]
            # Το χώμα, το συχνότερο, έχει την άκρη του όλη βάση· στη σκόνη και
            # στην πέτρα ένα σημάδι μπορεί να ακουμπά την άκρη.
            edge_ok = cls != "ground" or all(p == 7 for p in border)
            check(marks <= QUIET[cls] and edge_ok,
                  "tile_%s_%d: %2d σημάδια (<= %d)%s" % (cls, v, marks, QUIET[cls],
                                                     ", άκρη όλη βάση" if cls == "ground" else ""))
    # ΑΡΝΗΤΙΚΟ: ο θόρυβος ως το βήμα 177 — τυχαίο σκούρο στο 6% και φωτεινό στο 4%
    # σε ψηφίδες 1 x 2, ακόμη και στην άκρη (terrain.ground των τότε εργαλείων).
    noisy = [[7] * 8 for _ in range(16)]
    st = 101
    for y in range(0, 16, 2):
        for x in range(8):
            st = (st * 1103515245 + 12345) & 0x7FFFFFFF
            k = (st >> 8) % 100
            if k < 10:
                noisy[y][x] = noisy[y + 1][x] = 11 if k < 6 else 12
    marks = sum(p != 7 for row in noisy for p in row)
    border = [noisy[y][x] for y in range(16) for x in range(8) if x in (0, 7) or y in (0, 15)]
    check(not (marks <= QUIET["ground"] and all(p == 7 for p in border)),
          "ΑΡΝΗΤΙΚΟ: ένα tile με τον παλιό θόρυβο (%d σημάδια) δεν περνά" % marks)


def main():
    smap, blob = load_map(), load_bin()
    s = smap["palette_fw"]
    fw = list(blob[s.off:s.off + s.size])
    check(fw[FLOOR] == 23 and fw[RIM] == 11,
          "παλέτα: δάπεδο θόλου Pastel cyan (fw 23), χείλος Sky blue (fw 11)")
    corridors(smap, blob)
    glass(smap, blob)
    figures(smap, blob, fw)
    terrain(smap, blob)
    # ΑΡΝΗΤΙΚΟ για το 1: οι ρόλοι όπως ως το βήμα 177 (λευκή άκρη, γκρι σώμα)
    h = decode(blob, smap["corr_h"])
    old = [[{GREY: WHITE, WHITE: GREY}[p] for p in row] for row in h]
    check(not all(p == WHITE for row in old[1:7] for p in row),
          "ΑΡΝΗΤΙΚΟ: ο διάδρομος του βήματος 177 (γκρι σώμα) δεν περνά τον κανόνα")
    print("\n%s" % ("ΑΠΟΤΥΧΙΑ: %d" % len(FAIL) if FAIL else "OK"))
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
