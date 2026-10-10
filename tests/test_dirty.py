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
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/vasilhs/cpcemu")

from test_object import build                                           # noqa: E402

SNA = os.path.join(ROOT, "build", "objtest.sna")
CAM = (-21, -13)

# Ο,ΤΙ ΣΠΡΩΧΝΕΙ ΤΟ push_all ΤΟΥ objtest, με τη σειρά του: (είδος, αδειάζει).
# Η θέση (1,0) αδειάζει και φαίνεται — ο άποικος 2 πήγε στον θόλο 0 — και ο
# dh_slot χρεώνει γι' αυτήν και το DHS_VAC_US.
PUSHED = [(2, False), (1, False), (1, False), (0, False), (0, True), (3, False), (4, False)]


def model(items, cost, bud, vac):
    """Πόσα μένουν μετά από κάθε πέρασμα του dirty_tick (dt_lp, dt_store)."""
    left, trace = list(items), []
    while left:
        spent = 0
        while left:
            kind, vacates = left[0]
            new = spent + cost[kind]
            if spent and (new > 0xFFFF or new > bud):
                break                           # μένει για το επόμενο
            spent = new
            if vacates:
                spent = min(spent + vac, 0xFFFF)
            left.pop(0)
        trace.append(len(left))
    return trace


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

    # Ο προϋπολογισμός πρέπει να ΔΑΓΚΩΝΕΙ — και ΑΚΡΙΒΩΣ όσο λέει ο πίνακας.
    # Ως το βήμα 54 ο έλεγχος ήταν «τουλάχιστον δύο περάσματα», που τα 29.000
    # us τα δίνουν και με διπλό προϋπολογισμό, και χωρίς τον φόρο του
    # αδειάσματος: τα δύο λάθη περνούσαν. Τώρα το objtest κρατά πόσα έμειναν
    # μετά από ΚΑΘΕ πέρασμα, και το μοντέλο εδώ λέει πόσα πρέπει να μείνουν.
    trace = [ma.peek(sym["DD_LEFT"] + i) for i in range(ticks)]
    cost = [ma.peek(sym["DIRTY_COST"] + 2 * k) | (ma.peek(sym["DIRTY_COST"] + 2 * k + 1) << 8)
            for k in range(8)]
    src = open(os.path.join(ROOT, "src", "dirty.asm"), encoding="utf-8").read()
    bud = int(re.search(r"^DIRTY_BUD\s+equ\s+(\d+)", src, re.M).group(1))
    vac = int(re.search(r"^DHS_VAC_US\s+equ\s+(\d+)", src, re.M).group(1))
    want_trace = model(PUSHED, cost, bud, vac)
    if trace != want_trace:
        print(f"ΑΠΟΤΥΧΙΑ: ο προϋπολογισμός δεν κόβει όπου λέει ο πίνακας — "
              f"έμειναν {trace} ανά πέρασμα, το μοντέλο λέει {want_trace}")
        fails += 1
    else:
        print(f"OK ο προϋπολογισμός κόβει όπου λέει ο πίνακας: έμειναν {trace} "
              f"από τα {len(PUSHED)} ({bud} us το πέρασμα, +{vac} το άδειασμα)")
    # ΑΡΝΗΤΙΚΑ του μοντέλου: τα δύο λάθη που ο παλιός έλεγχος άφηνε να περάσουν
    # πρέπει να δίνουν ΑΛΛΟ ίχνος — αλλιώς η σύγκριση δεν ξεχωρίζει τίποτα.
    for label, alt in (("με διπλό προϋπολογισμό", model(PUSHED, cost, 2 * bud, vac)),
                       ("χωρίς τον φόρο του αδειάσματος", model(PUSHED, cost, bud, 0))):
        if alt == want_trace:
            print(f"ΑΠΟΤΥΧΙΑ: {label} το ίχνος είναι πάλι {alt} — το σενάριο "
                  f"δεν το ξεχωρίζει")
            fails += 1
        else:
            print(f"OK {label} θα έμεναν {alt}")

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
             # Βήμα 100: τα όπλα του θόλου 1 είναι χαλασμένα στη μετάλλαξη, και
             # η υποδοχή ζωγραφίζεται με το σήμα της — ίδια τιμή στον πίνακα.
             ("μηχάνημα με σήμα", 1, 1, 0, 20),
             ("εικονίδιο", 2, 0, 0, 20),
             ("αρμός (ως το 95 πόρτα)", 3, 0, 4, 20),
             ("tile, ελεύθερο", 4, -8 & 0xFF, -6 & 0xFF, 2),
             ("tile, κάτω από θόλο", 4, -16 & 0xFF, -9 & 0xFF, 2),
             # Βήμα 34: εικονίδιο + όλες οι μηχανές ενός θόλου M (τέσσερις).
             # Ο θόλος L είναι διπλάσιος και ο S το ένα τρίτο — ο πίνακας
             # κρατά τον μεσαίο, και το «ένα στοιχείο βγαίνει πάντα» καλύπτει
             # τον μεγάλο.
             ("κτίριο που τελείωσε", 5, 0, 0, 10),
             # Βήμα 35: μία σειρά tiles εργοταξίου, η δεύτερη του θόλου M.
             ("σειρά εργοταξίου", 6, 0, 2, 4),
             # Βήμα 37: τρία tiles μιας διαγωνίου. Το ob_draw_all είναι το
             # κόστος, όχι τα tiles — πρώτα σε ελεύθερο έδαφος, μετά πάνω σε
             # θόλο, όπως οι πρώτες και οι τελευταίες σειρές.
             ("σειρά διαγωνίου", 7, -9 & 0xFF, -6 & 0xFF, 4),
             ("σειρά διαγ., κέλυφος", 7, -17 & 0xFF, -9 & 0xFF, 4)]
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
