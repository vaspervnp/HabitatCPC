#!/usr/bin/env python3
"""Η λίστα αλλαγών: ελάχιστη επανασχεδίαση, και ο προϋπολογισμός (DESIGN §8.5).

ΔΥΟ ΔΡΟΜΟΙ, ΕΝΑ ΑΠΟΤΕΛΕΣΜΑ. Η ίδια μετάλλαξη εφαρμόζεται δύο φορές: μια μέσω
της λίστας (που ξαναζωγραφίζει μόνο ό,τι άλλαξε) και μια με πλήρη
επανασχεδίαση. Αν οι δύο οθόνες δεν είναι ταυτόσημες, η «ελάχιστη
επανασχεδίαση» ενός είδους είναι ελλιπής — και αυτό είναι ακριβώς το λάθος που
κανείς δεν βλέπει παίζοντας, γιατί η οθόνη δείχνει ΚΑΤΙ.

Ο ΕΛΕΓΧΟΣ ΠΟΥ ΑΠΟΔΕΙΚΝΥΕΙ ΟΤΙ Ο ΕΛΕΓΧΟΣ ΔΟΥΛΕΥΕΙ: με τη μετάλλαξη
απενεργοποιημένη οι δύο οθόνες είναι ΚΑΙ ΟΙ ΔΥΟ η αρχική, οπότε θα συμφωνούσαν
χωρίς να αποδεικνύεται τίποτα. Γι' αυτό συγκρίνουμε και με την ΠΡΙΝ εικόνα:
πρέπει να διαφέρει.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/vasilhs/cpcemu")

from test_object import build                                           # noqa: E402

SNA = os.path.join(ROOT, "build", "objtest.sna")
CAM = (-21, -13)


def main():
    sym = build()
    from cpc import CPC

    def start():
        m = CPC()
        m.run_frames(60)
        assert m.quickload(SNA, start=False)
        m.poke(sym["CAM_TX"], CAM[0] & 0xFF)
        m.poke(sym["CAM_TY"], CAM[1] & 0xFF)
        m.poke(sym["HUD_ON"], 0)
        m.poke(sym["REP_N"], 1)
        run(m, "START")
        return m

    def run(m, entry):
        m.poke(sym["DONE_FLAG"], 0)
        m.set_pc(sym[entry])
        n = 0
        while m.peek(sym["DONE_FLAG"]) != 0x5A and n < 600:
            m.run_frames(1)
            n += 1
        assert m.peek(sym["DONE_FLAG"]) == 0x5A, f"δεν τερμάτισε, PC=#{m.pc:04X}"
        return n

    fails = 0
    m0 = start()
    before = m0.read_ram(0xC000, 0x4000)
    off = m0.peek(sym["CAM_OFF"]) | (m0.peek(sym["CAM_OFF"] + 1) << 8)

    ma = start()
    na = run(ma, "DO_DIRTY")
    ticks = ma.peek(sym["DD_TICKS"])
    got = ma.read_ram(0xC000, 0x4000)

    mb = start()
    nb = run(mb, "DO_FULL")
    want = mb.read_ram(0xC000, 0x4000)

    def diff(a, b):
        out = []
        for y in range(160):
            hi = (y & 7) * 0x800
            row = (y >> 3) * 80
            for x in range(80):
                p = (row + x + 2 * off) & 0x7FF
                if a[hi + p] != b[hi + p]:
                    out.append((x, y))
        return out

    moved = diff(before, want)
    if not moved:
        print("ΑΠΟΤΥΧΙΑ: η μετάλλαξη δεν άλλαξε τίποτα — ο έλεγχος δεν ελέγχει")
        fails += 1
    else:
        print(f"OK η μετάλλαξη αλλάζει {len(moved)} bytes σε "
              f"{len({(x//4, y//16) for x, y in moved})} tiles")

    # Ο προϋπολογισμός πρέπει να ΔΑΓΚΩΝΕΙ: επτά στοιχεία των 29.000 us δεν
    # χωράνε σε ένα frame των 20.000, άρα η λίστα πρέπει να χρειαστεί δεύτερο
    # πέρασμα. Αν βγει με ένα, ο προϋπολογισμός δεν υπάρχει.
    if ticks < 2:
        print("ΑΠΟΤΥΧΙΑ: η λίστα άδειασε σε ένα πέρασμα — "
              "ο προϋπολογισμός δεν κόβει")
        fails += 1
    else:
        print(f"OK ο προϋπολογισμός κόβει: {ticks} περάσματα για 7 αλλαγές "
              f"(29.000 us σε frames των 20.000)")

    bad = diff(got, want)
    if bad:
        fails += 1
        print(f"ΑΠΟΤΥΧΙΑ: η λίστα αφήνει {len(bad)} bytes λάθος, πρώτο {bad[0]}")
        xs = sorted({x for x, _ in bad})
        ys = sorted({y for _, y in bad})
        print(f"    x {xs[0]}..{xs[-1]}  y {ys[0]}..{ys[-1]}")
    else:
        print("OK η λίστα δίνει ΤΟ ΙΔΙΟ με πλήρη επανασχεδίαση")

    # --- το κόστος κάθε είδους, μετρημένο, κόντρα στον πίνακα dirty_cost ---
    KINDS = [("θέση δακτυλίου", 0, 0, 1, 40),
             ("μηχάνημα", 1, 0, 2, 20),
             ("εικονίδιο", 2, 0, 0, 20),
             ("πόρτα", 3, 0, 4, 20),
             ("tile, ελεύθερο", 4, -8 & 0xFF, -6 & 0xFF, 2),
             ("tile, κάτω από θόλο", 4, -16 & 0xFF, -9 & 0xFF, 2)]
    print("\nκόστος ανά είδος (μετρημένο / πίνακας):")
    for name, kind, a, b, reps in KINDS:
        m = start()
        m.poke(sym["OO_KIND"], kind)
        m.poke(sym["OO_A"], a)
        m.poke(sym["OO_B"], b)
        m.poke(sym["REP_N"], reps)
        n = run(m, "DO_ONE")
        us = n * 19968 / reps
        tab = (m.peek(sym["DIRTY_COST"] + kind * 2)
               | (m.peek(sym["DIRTY_COST"] + kind * 2 + 1) << 8))
        # Το tile κάτω από θόλο ξαναπερνά ΟΛΑ τα αντικείμενα και ξεπερνά τον
        # προϋπολογισμό μόνο του. Είναι γνωστό και καταγραμμένο (§8.5), όχι
        # αστοχία του πίνακα: ο πίνακας κρατά τη ΣΥΝΗΘΗ περίπτωση.
        if "θόλο" in name:
            print(f"  {name:20s} {us:8.0f} us   (ξεπερνά τον προϋπολογισμό — §8.5)")
            continue
        ok = 0.5 * tab <= us <= 2.0 * tab
        print(f"  {name:20s} {us:8.0f} us   πίνακας {tab:6d}"
              f"   {'OK' if ok else 'ΑΠΟΤΥΧΙΑ — ο πίνακας ψεύδεται'}")
        if not ok:
            fails += 1

    ua, ub = na * 19968, nb * 19968
    print(f"\nκόστος: λίστα {ua:.0f} us ({na} frames) · "
          f"πλήρης {ub:.0f} us ({nb} frames) · κέρδος {ub/max(ua,1):.0f}x")
    if ua >= ub:
        print("  ΑΠΟΤΥΧΙΑ: η λίστα δεν είναι φθηνότερη από την πλήρη σχεδίαση")
        fails += 1
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
