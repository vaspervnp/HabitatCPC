#!/usr/bin/env python3
"""Τι έχει κάτω ο κέρσορας: το I στο LOOK, στο main.sna (DESIGN §9.1).

Η πρόζα λέει: με το I, οι σειρές 3-4 του HUD γράφουν

  σειρά 3   για θόλο      το όνομα του καταλόγου (DOME S/M/L), το δωμάτιο, SITE ή
                          ACTIVE, και HP: η ακεραιότητα στα εκατό (x 101 / 256)
            για δομή      το όνομα του καταλόγου, SITE ή ACTIVE, HP
            αλλιώς        CORRIDOR αν το tile έχει κατοχή, NOTHING BUILT αν όχι —
                          και πάνω σε μονοπάτι, που από το βήμα 131 είναι θεμέλιο
                          χωρίς κατοχή (ως το 130 κατοχή 2, και το I έλεγε PATH)
  σειρά 4   το έδαφος του tile, και ORE VEIN σε βουνό με μετάλλευμα

με την ταχύτητα στις στήλες 35-39 όπως πάντα. Μένουν ώσπου να κουνηθεί ο
κέρσορας ή να πατηθεί το ESC — τότε ξαναγράφουν ό,τι λέει το LOOK — και ένα
δεύτερο I τις ξαναδιαβάζει.

ΟΙ ΘΕΣΕΙΣ. Οι θόλοι και οι δομές της αρχής, σε κάθε tile του αποτυπώματός τους
και ένα πιο έξω· και επιπλέον θόλοι και δομές γραμμένοι στους πίνακες, μακριά
από την αποικία, σε κάθε μέγεθος, είδος, δωμάτιο, κατάσταση και ακεραιότητα
(0, 32, 128, 254, 255)· tiles διαδρόμων, και ενός μονοπατιού· ένα tile από κάθε έδαφος που έχει ο
κόσμος, και βουνό με και χωρίς φλέβα· και οι τέσσερις γωνίες του κόσμου. Το
παιχνίδι είναι σε παύση, ώστε τίποτα να μην αλλάζει από κάτω.

ΠΙΣΩ ΑΠΟ ΜΗΝΥΜΑ. Ενα μήνυμα (ui_msg: σώθηκε, πλοίο...) κρατά τις σειρές 3-4
έξι κλήσεις του ui_panel, και σε παύση δεν το καλεί κανένα ρολόι. Το I το
ζητά ο παίκτης και δεν περιμένει: ως το βήμα 79 δεν έδειχνε τίποτα.

Αρνητικά, με τον κώδικα πειραγμένο στη μνήμη: οι δομές που δεν ψάχνονται, τα
εδάφη ανά δέκα bytes αντί για έντεκα, ο κέρσορας που κουνιέται χωρίς να βγει
από το INFO, το ποσοστό x 100 αντί για x 101, το I που περιμένει το μήνυμα,
και ο έλεγχος της κατοχής ανάποδα (το μονοπάτι θα λεγόταν CORRIDOR).
"""
import os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import cpc                                               # noqa: E402
from sprites import load_map, load_bin                   # noqa: E402
import hudread                                           # noqa: E402
import scene as S                                        # noqa: E402

FAIL = []
DOMES, STRUCTS = 0x7500, 0x7B00
NAMES_D = ["DOME S", "DOME M", "DOME L"]
NAMES_S = ["SOLAR", "TURBINE", "COLLECTOR", "EXTRACTOR", "MINE", "AIRLOCK", "LANDING"]
ROOMS = {4: "OXYGEN", 3: "CANTEEN", 2: "QUARTERS", 5: "GREENHOUSE", 8: "FACTORY",
         9: "LAB", 10: "MEDBAY", 1: "CONTROL", 6: "STORAGE", 11: "LOUNGE"}
TERRAIN = ["GROUND", "DUST", "ROCK", "MOUNTAIN", "WATER", "DEEP WATER", "CRATER",
           "FOUNDATION"]
LOOK3 = "SPACE=MENU I=INFO FIRE=FIT C=SHIP"


def check(ok, msg):
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ ") + msg)
    if not ok:
        FAIL.append(msg)


def s8(v):
    return v - 256 if v > 127 else v


class Game:
    def __init__(self, sym, patch=()):
        self.sym = sym
        m = self.m = cpc.CPC()
        m.run_frames(60)
        assert m.quickload(TG.COLONY), "quickload απέτυχε"
        m.run_frames(120)
        for at, v in patch:
            m.poke(at, v)
        self.tap("1")                       # παύση: ο τροχός δεν αλλάζει τίποτα
        self.b4 = cpc._lib.cpcemu_ram_ptr(m._h, 4)
        self.b6 = cpc._lib.cpcemu_ram_ptr(m._h, 6)

    def tap(self, key, n=1):
        for _ in range(n):
            self.m.key_down(key)
            self.m.run_frames(3)
            self.m.key_up(key)
            self.m.run_frames(6)

    def hud(self, row):
        return hudread.text(self.m, self.sym, row)

    def world(self, tx, ty):
        return self.b4[(ty + 64) * 128 + tx + 64]

    def cursor(self, tx, ty):
        self.m.poke(self.sym["CUR_HX"], (2 * tx) & 255)
        self.m.poke(self.sym["CUR_HY"], (2 * ty) & 255)


def footprints(G, a):
    """[(x0, y0, w, h, 'd'/'s', αριθμός)] των ζωντανών εγγραφών."""
    out = []
    for d in range(64):
        b = DOMES - 0x4000 + 24 * d
        if G.b6[b + 4]:
            side = 4 + 2 * G.b6[b + 2]
            out.append(((s8(G.b6[b]) - side) >> 1, (s8(G.b6[b + 1]) - side) >> 1,
                        side, side, "d", d))
    for s in range(32):
        b = STRUCTS - 0x4000 + 8 * s
        if G.b6[b + 4]:
            k = G.b6[b + 2] * 8 + G.b6[b + 3] * 2
            w, h = a.struct_dims[k] // 4, a.struct_dims[k + 1] // 16
            out.append(((s8(G.b6[b]) - w) >> 1, (s8(G.b6[b + 1]) - h) >> 1, w, h, "s", s))
    return out


def want(G, fps, tx, ty):
    """(σειρά 3, σειρά 4) όπως τις λέει η πρόζα."""
    hit = next((f for f in fps if f[0] <= tx < f[0] + f[2] and f[1] <= ty < f[1] + f[3]),
               None)
    w = G.world(tx, ty)
    if hit:
        b = (DOMES - 0x4000 + 24 * hit[5]) if hit[4] == "d" else (STRUCTS - 0x4000 + 8 * hit[5])
        k, r, st, hp = (G.b6[b + i] for i in (2, 3, 4, 5))
        name = NAMES_D[k] if hit[4] == "d" else NAMES_S[k]
        room = ROOMS.get(r, "") if hit[4] == "d" else ""
        r3 = (f"{name:9s}{room:10s} {'ACTIVE' if st == 2 else 'SITE':6s} "
              f"HP {hp * 101 // 256:3d}%")
    else:
        r3 = "CORRIDOR" if w & 0x30 else "NOTHING BUILT"
    r4 = f"{TERRAIN[w & 7]:10s}" + (" ORE VEIN" if w & 0x0F == 0x0B else "")
    return same(f"{r3:35s}"), same(f"{r4:40s}")


def same(s):
    """Η γραμματοσειρά δίνει στο 0 και στο O τον ίδιο γλύφο: στην οθόνη είναι ένα."""
    return s.replace("O", "0")


def look(G, tx, ty):
    G.cursor(tx, ty)
    G.tap("I")
    return same(G.hud(3)[:35]), same(G.hud(4))


def scene(G, a, rnd):
    """Θόλοι και δομές μακριά από την αποικία, σε κάθε συνδυασμό."""
    spots = []
    d_free = [d for d in range(64) if not G.b6[DOMES - 0x4000 + 24 * d + 4]]
    s_free = [s for s in range(32) if not G.b6[STRUCTS - 0x4000 + 8 * s + 4]]
    x = -56
    for k, (size, room, st, hp) in enumerate([(0, 4, 2, 255), (1, 3, 1, 32), (2, 5, 2, 128),
                                              (0, 0, 2, 0), (1, 7, 1, 254), (2, 11, 2, 200)]):
        d = d_free[k]
        b = DOMES - 0x4000 + 24 * d
        side = 4 + 2 * size
        cx, cy = 2 * x + side, 2 * 40 + side
        for i, v in enumerate((cx & 255, cy & 255, size, room, st, hp)):
            G.b6[b + i] = v
        spots.append((x, 40, side, side))
        x += side + 1
    x = -56
    for k, (kind, size) in enumerate([(0, 0), (1, 1), (2, 2), (3, 0), (4, 0), (5, 0), (6, 0)]):
        s = s_free[k]
        b = STRUCTS - 0x4000 + 8 * s
        dk = kind * 8 + size * 2
        w, h = a.struct_dims[dk] // 4, a.struct_dims[dk + 1] // 16
        cx, cy = 2 * x + w, 2 * 52 + h
        st, hp = rnd.choice([(1, 0), (1, 96), (2, 255), (2, 180)])
        for i, v in enumerate((cx & 255, cy & 255, kind, size, st, hp)):
            G.b6[b + i] = v
        spots.append((x, 52, w, h))
        x += w + 1
    # Ενα μονοπάτι στο έδαφος: θεμέλιο χωρίς κατοχή από το βήμα 131 (ως το 130
    # κατοχή 2), με κάθε decor, και δίπλα του tiles κατοχής 1 και 3.
    for k, v in enumerate((0x07, 0x47, 0x87, 0xC7, 0x10, 0x30)):
        G.b4[(46 + 64) * 128 + (-56 + k) + 64] = v
    return spots


def run(sym, a, patch=(), quick=False):
    """-> το πρώτο λάθος, ή None· και πόσα tiles ελέγχθηκαν."""
    G = Game(sym, patch)
    rnd = random.Random(79)
    spots = scene(G, a, rnd)
    fps = footprints(G, a)
    tiles = []
    for x0, y0, w, h, _, _ in fps:                       # κάθε tile, και ένα γύρω
        for ty in range(y0 - 1, y0 + h + 1):
            for tx in range(x0 - 1, x0 + w + 1):
                tiles.append((tx, ty))
    seen = set()
    for ty in range(-64, 64):                            # ένα από κάθε έδαφος
        for tx in range(-64, 64):
            w = G.world(tx, ty)
            k = (w & 0x0F if w & 7 == 3 else w & 7, bool(w & 0x30))
            if k not in seen:
                seen.add(k)
                tiles.append((tx, ty))
    tiles += [(-64, -64), (63, -64), (63, 63), (-64, 63)]
    if quick:
        tiles = tiles[::7]
    tiles += [(-56 + k, 46) for k in range(6)]          # το μονοπάτι (βήμα 85)
    for tx, ty in tiles:
        got = look(G, tx, ty)
        exp = want(G, fps, tx, ty)
        if got != exp:
            return f"tile ({tx}, {ty}): «{got[0]}» / «{got[1].rstrip()}», η πρόζα λέει «{exp[0]}» / «{exp[1].rstrip()}»", len(tiles)
    # --- ο κέρσορας κουνιέται: πίσω στο LOOK. Σε θόλο της αρχής, μέσα στο
    # κάδρο, ώστε το βήμα να μη σκρολάρει ---
    d0 = next(f for f in fps if f[4] == "d")
    tx, ty = d0[0] + 1, d0[1] + 1
    cam = (s8(G.m.peek(G.sym["CAM_TX"])), s8(G.m.peek(G.sym["CAM_TY"])))
    assert cam[0] + 1 < tx < cam[0] + 18 and cam[1] + 1 < ty < cam[1] + 8, (cam, tx, ty)
    look(G, tx, ty)
    G.m.key_down(cpc.KEY_RIGHT)
    G.m.run_frames(4)
    G.m.key_up(cpc.KEY_RIGHT)
    G.m.run_frames(10)
    if G.hud(3)[:35] != f"{LOOK3:35s}" or G.hud(4).strip():
        return f"μετά από ένα βήμα: «{G.hud(3)}» / «{G.hud(4).rstrip()}»", len(tiles)
    # --- ESC: πίσω στο LOOK ---
    look(G, tx, ty)
    G.tap(cpc.KEY_ESC)
    if G.hud(3)[:35] != f"{LOOK3:35s}" or G.hud(4).strip():
        return f"μετά το ESC: «{G.hud(3)}» / «{G.hud(4).rstrip()}»", len(tiles)
    # --- δεύτερο I: ξαναδιαβάζει ---
    look(G, tx, ty)
    d = next(f for f in fps if f[4] == "d" and f[0] <= tx < f[0] + f[2]
             and f[1] <= ty < f[1] + f[3])
    G.b6[DOMES - 0x4000 + 24 * d[5] + 5] = 77
    G.tap("I")
    if same(G.hud(3)[:35]) != want(G, fps, tx, ty)[0]:
        return f"το δεύτερο I δεν ξαναδιάβασε: «{G.hud(3)}»", len(tiles)
    # --- πίσω από μήνυμα: ένα ui_msg κρατά τις σειρές έξι κλήσεις του
    # ui_panel, και σε παύση δεν το καλεί κανένα ρολόι. Το I το ζήτησε ο
    # παίκτης: δεν περιμένει ---
    G.tap(cpc.KEY_ESC)
    G.m.poke(G.sym["UI_HOLD"], 6)                       # MSG_TICKS, όπως το ui_msg
    got = look(G, tx, ty)
    if got != want(G, fps, tx, ty):
        return f"με μήνυμα στις σειρές, το I έδειξε «{got[0]}» / «{got[1].rstrip()}»", len(tiles)
    return None, len(tiles)


def main():
    sym, _ = TG.build()
    a = S.Assets()
    why, n = run(sym, a)
    check(why is None, f"I σε {n} tiles: θόλοι, δομές, διάδρομοι, κάθε έδαφος, οι γωνίες — "
                       f"οι σειρές 3-4 όπως τις λέει η πρόζα· ένα βήμα ή το ESC τις "
                       f"γυρίζουν στο LOOK, ένα δεύτερο I τις ξαναδιαβάζει"
          + (f" — {why}" if why else ""))

    m = Game(sym).m

    def find(at, pat, span=300):
        i = m.read_ram(sym[at], span).find(bytes(pat))
        assert i >= 0, f"δεν βρέθηκε το {pat} στο {at}"
        return sym[at] + i

    ms = sym["MT_SCAN"]
    # στο MT_CURSOR από το βήμα 101: το ίδιο ερώτημα κάνει και η κατεδάφιση
    st = find("MT_CURSOR", [0xCD, ms & 255, ms >> 8], 40)        # το πρώτο: θόλοι
    st2 = m.read_ram(st + 3, 40).find(bytes([0xCD, ms & 255, ms >> 8])) + st + 3
    neg = [("τις δομές που δεν ψάχνονται", [(st2, 0xB7), (st2 + 1, 0), (st2 + 2, 0)]),
           ("τα εδάφη ανά δέκα bytes", [(find("INP_R3", [0x81, 0x87, 0x81]) + 2, 0x00)]),
           ("τον κέρσορα που μένει στο INFO",
            [(find("UIST_LOOK", [0x36, 0x00]) + 1, 6)]),
           ("το ποσοστό x 100", [(find("INP_STATE", [0x0E, 101]) + 1, 100)]),
           ("το I που περιμένει το μήνυμα", [(find("UI_ASK", [0x36, 0x00], 20) + 1, 6)]),
           # jr nz,inp_name μετά το and W_OCC_MASK γίνεται jr z
           ("τον έλεγχο της κατοχής ανάποδα",
            [(find("INP_NONE", [0xE6, 0x30, 0x21], 20) + 5, 0x28)])]
    for label, patch in neg:
        why, _ = run(sym, a, patch, quick=True)
        check(why is not None, f"ΑΡΝΗΤΙΚΟ: με {label} αποτυγχάνει"
                               + (f" ({why[:110]})" if why else ""))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
