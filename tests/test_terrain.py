#!/usr/bin/env python3
"""Το bd_res του src/terrain.asm απέναντι στον κανόνα του DESIGN §6.5.

Ο κανόνας, όπως τον γράφει το κείμενο και όχι ο Z80: η αντλία (K_EXTRACT) θέλει
ρηχό ή βαθύ νερό, το ορυχείο (K_MINE) βουνό με το bit πόρου (§3.5), μέσα στο
αποτύπωμα ΜΕ ΔΥΟ tiles περιθώριο. Οτιδήποτε άλλο δεν ζητά τίποτα. Out: A = 0
αν επιτρέπεται, 1 αν λείπει το υλικό· (bd_nres) = 0, 1 (νερό) ή 2 (φλέβα).

ΓΙΑΤΙ. Ως το βήμα 67 το bd_res το έβλεπαν μόνο σενάρια που χτίζουν κάτι κάπου
(test_needs, test_balance): μια αντλία στην όχθη, ένα ορυχείο στους πρόποδες.
Εδώ καλείται κατευθείαν σε τρία επίπεδα — τον κόσμο του uitest, τον κόσμο του
παιχνιδιού και ένα αραιό συνθετικό με «σχεδόν» τιμές (κρατήρας, θεμέλιο, βουνό
χωρίς φλέβα, bit πόρου πάνω σε νερό) — για κάθε είδος του καταλόγου και
μεγέθη 1x1 ως 8x8, με το bd_nres να ξεκινά από σκουπίδι.

ΣΤΟ BINARY ΤΟΥ ΠΑΙΧΝΙΔΙΟΥ (main.sna), ΟΧΙ ΣΤΟ uitest. Στο βήμα 67 το νέο bd_res
πέρασε 4.500 συγκρίσεις στο uitest και στο παιχνίδι δεν δεχόταν αντλία στην
όχθη: το `ld bc,-RES_NEAR * 129` έβγαινε +258, γιατί στο main.asm το RES_NEAR
οριζόταν ΜΕΤΑ (στο build.asm) και το rasm χάνει τότε το πρόσημο. Στο uitest το
build.asm μπαίνει πρώτο. Ιδιος πηγαίος, άλλα bytes.

Και ο ΧΡΟΝΟΣ: οι δύο χειρότερες αναζητήσεις του καταλόγου, το ορυχείο 4x4
χωρίς φλέβα (8x8 tiles) και η αντλία 3x3 χωρίς νερό (7x7), δεν παίρνουν
περισσότερο από όσο μετρήθηκε στο βήμα 67. Με το αρχείο του βήματος 66
αποτυγχάνουν και οι δύο.

Αρνητικά, με το snapshot πειραγμένο: το βαθύ νερό να μη μετρά (μάσκα 7), η
σειρά να προχωρά 127 bytes, και το «βρέθηκε» να αφήνει το bd_nres.
"""
import ctypes, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import cpc                                               # noqa: E402

PROBE = 0x3F00
K_EXTRACT, K_MINE, RES_NEAR = 3, 4, 2                    # src/const.asm
CEIL = {"ορυχείο 4x4 χωρίς φλέβα": 1021, "αντλία 3x3 χωρίς νερό": 818}   # us, βήμα 67


def synthetic(rnd):
    """Έδαφος με λίγο νερό, βουνά με και χωρίς φλέβα και «σχεδόν» τιμές· στο
    |x|,|y| >= 62 βουνό χωρίς φλέβα, όπως αφήνει η γεννήτρια (§5.5)."""
    p = bytearray(0x4000)
    for i in range(0x4000):
        x, y = (i & 127) - 64, (i >> 7) - 64
        r = rnd.random()
        if max(abs(x), abs(y)) >= 62:
            p[i] = 3
        elif r < 0.008:
            p[i] = rnd.choice([4, 5, 12, 13]) | rnd.randrange(4) << 6
        elif r < 0.016:
            p[i] = rnd.choice([11, 3, 3 | 0x40]) | rnd.randrange(4) << 6
        elif r < 0.03:
            p[i] = rnd.choice([6, 7, 14, 15, 8, 9, 10, 2])
        else:
            p[i] = rnd.choice([0, 0, 1, 7, 0x40, 0x80])
    return bytes(p)


def model(pl, kind, param, w, h, tx, ty):
    """(A, bd_nres) από την πρόζα του §6.5."""
    if kind != 1 or param not in (K_EXTRACT, K_MINE):
        return 0, 0
    for y in range(ty - RES_NEAR, ty + h + RES_NEAR):
        for x in range(tx - RES_NEAR, tx + w + RES_NEAR):
            b = pl[(y + 64) * 128 + x + 64]
            if param == K_EXTRACT and (b & 7) in (4, 5):        # ρηχό, βαθύ νερό
                return 0, 0
            if param == K_MINE and (b & 7) == 3 and b & 8:       # βουνό με φλέβα
                return 0, 0
    return 1, 1 if param == K_EXTRACT else 2


def check(sym, patch=(), timing=True):
    """Η πρώτη διαφορά από τον κανόνα, ή None."""
    m = cpc.CPC()
    m.run_frames(60)
    assert m.quickload(TG.SNA, start=False), "quickload απέτυχε"
    for at, v in patch:
        m.poke(at, v)
    b4 = cpc._lib.cpcemu_ram_ptr(m._h, 4)

    def run(step=20):
        # di · sp · τράπεζα 4 · call bd_res · ld (#3FF0),a · jr $
        r = sym["BD_RES"]
        code = [0xF3, 0x31, 0x00, 0x01, 0x01, 0xC4, 0x7F, 0xED, 0x49, 0xCD, r & 255, r >> 8,
                0x32, 0xF0, 0x3F, 0x18, 0xFE]
        m.write_ram(PROBE, bytes(code))
        m.set_pc(PROBE)
        end, t = PROBE + len(code) - 2, 0
        while not (end <= m.pc <= end + 2):
            m.run_us(step)
            t += step
            if t > 100_000:
                return None, None
        return t, m.peek(0x3FF0)

    def one(pl, kind, param, w, h, tx, ty, step=20):
        for a, v in (("BD_KIND", kind), ("BD_PARAM", param), ("BD_W", w), ("BD_H", h),
                     ("BD_TX", tx & 255), ("BD_TY", ty & 255), ("BD_NRES", 0x77)):
            m.poke(sym[a], v)
        t, A = run(step)
        where = f"είδος {kind} παράμετρος {param}, {w}x{h} στο ({tx},{ty})"
        if t is None:
            return where + ": δεν γύρισε", None
        got, want = (A, m.peek(sym["BD_NRES"])), model(pl, kind, param, w, h, tx, ty)
        if got != want:
            return f"{where}: A = {got[0]}, bd_nres = {got[1]}, ο κανόνας λέει {want}", t
        return None, t

    rnd = random.Random(67)
    worlds = [("ο κόσμος του uitest", open(os.path.join(ROOT, "build", "world_col.bin"), "rb").read()[:0x4000]),
              ("ο κόσμος του παιχνιδιού", open(os.path.join(ROOT, "build", "world_new.bin"), "rb").read()[:0x4000]),
              ("συνθετικό", synthetic(rnd))]
    kinds = [(1, p) for p in range(11)] + [(1, K_EXTRACT), (1, K_MINE)] * 4 + [(0, K_EXTRACT), (2, K_MINE)]
    for name, pl in worlds:
        ctypes.memmove(b4, pl, 0x4000)
        for k in range(400):
            kind, param = rnd.choice(kinds)
            w, h = rnd.choice([(3, 3), (4, 4), (8, 8), (1, 1), (rnd.randint(1, 8), rnd.randint(1, 8))])
            why, _ = one(pl, kind, param, w, h, rnd.randint(-62, 62 - w), rnd.randint(-62, 62 - h))
            if why:
                return f"{name}: {why}"
    if not timing:
        return None
    dry = bytes(0x4000)                                  # μόνο έδαφος: τίποτα να βρεθεί
    ctypes.memmove(b4, dry, 0x4000)
    slow = []
    for label, (param, w) in (("ορυχείο 4x4 χωρίς φλέβα", (K_MINE, 4)), ("αντλία 3x3 χωρίς νερό", (K_EXTRACT, 3))):
        why, t = one(dry, 1, param, w, w, -10, 7, step=1)
        if why:
            return why
        print(f"    {label}: {t} us (ταβάνι {CEIL[label]})")
        if t > CEIL[label]:
            slow.append(f"{label} {t} > {CEIL[label]} us")
    return "πιο αργό από το βήμα 67: " + ", ".join(slow) if slow else None


def main():
    sym, _ = TG.build()
    fails = 0
    why = check(sym)
    if why:
        print(f"ΑΠΟΤΥΧΙΑ: {why}")
        fails += 1
    else:
        print("OK 1.200 κλήσεις του bd_res σε τρία επίπεδα = ο κανόνας του §6.5 (A και bd_nres)")
        print("OK η χειρότερη αναζήτηση όχι πιο αργή από το βήμα 67")

    # --- αρνητικά ---
    r, none = sym["BD_RES"], sym["BDR_NONE"]
    m = cpc.CPC()
    m.run_frames(60)
    assert m.quickload(TG.SNA, start=False)
    code = m.read_ram(r, 80)
    assert code[9:12] == bytes([0x11, 4, 6]), "το bd_res δεν έχει ld de,#0604 στο +9"
    step = code.find(bytes([0x3E, 0x80, 0x91]))
    assert step > 0, "το bd_res δεν έχει ld a,128 / sub c"
    assert m.read_ram(none, 2) == bytes([0xAF, 0x32]), "το bdr_none δεν είναι xor a / ld (nn),a"
    for label, patch in (("το βαθύ νερό να μη μετρά", [(r + 11, 7)]),
                         ("τη σειρά να προχωρά 127 bytes", [(r + step + 1, 127)]),
                         ("το «βρέθηκε» να αφήνει το bd_nres", [(none + 1, 0), (none + 2, 0), (none + 3, 0)])):
        why = check(sym, patch, timing=False)
        if why:
            print(f"OK ΑΡΝΗΤΙΚΟ: με {label} αποτυγχάνει ({why[:80]})")
        else:
            print(f"ΑΠΟΤΥΧΙΑ ΑΡΝΗΤΙΚΟΥ: με {label} περνά")
            fails += 1
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
