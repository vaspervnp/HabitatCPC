#!/usr/bin/env python3
"""Η ΙΣΟΡΡΟΠΙΑ ΩΣ ΔΟΚΙΜΗ — η αποικία του §10.1 χωρίς παίκτη.

Το tools/balance.py μετράει την καμπύλη ολόκληρη· εδώ κρατιέται ό,τι από
αυτήν είναι ΥΠΟΣΧΕΣΗ του σχεδίου. Το §10.1 τη γράφει σε μία πρόταση:
«αρκετά για να ζήσεις περίπου δύο sols χωρίς να κάνεις τίποτα, όσο ακριβώς
χρειάζεται για να καταλάβεις ότι θέλεις ρεύμα πριν από οτιδήποτε άλλο».

Τρία πράγματα, και τα τρία έχουν σπάσει:

  1. ΧΩΡΙΣ ΡΕΥΜΑ ΔΕΝ ΥΠΑΡΧΕΙ ΟΞΥΓΟΝΟ — καθόλου, όχι τις μισές φορές. Οσο το
     mach_power ήταν «ό,τι κάηκε» κι όχι «ό,τι ζητήθηκε», το μπλακάουτ
     μηδένιζε τη ζήτηση, το ισοζύγιο έβρισκε 0 >= 0 και το ρεύμα ξαναγύριζε
     μόνο του. Η αποικία έπαιρνε δωρεάν το μισό της οξυγόνο και ζούσε πέντε
     sols. Ο έλεγχος κοιτάζει ΚΑΘΕ δείγμα, όχι το τελικό αποτέλεσμα.
  2. ΠΕΘΑΙΝΟΥΝ ΑΠΟ ΑΕΡΑ, όχι από δίψα: την ώρα του πρώτου θανάτου υπάρχει
     ακόμη νερό και τροφή στην αποθήκη. Οταν η οικονομία έτρεχε 750 φορές το
     sol, η μηχανή οξυγόνου έπινε τα εξήντα νερά σε είκοσι δευτερόλεπτα.
  3. ΜΕΣΑ ΣΕ ΠΑΡΑΘΥΡΟ: ο πρώτος θάνατος ανάμεσα στο sol 1 και στο 3.

Τρέχει το ΚΑΝΟΝΙΚΟ binary στο x4, όπως το tools/balance.py.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")

import test_game as T                                                   # noqa: E402

# μετατοπίσεις στο G_econ_state — βλ. src/const.asm
O_STOCK, O_PPROD, O_O2PROD, O_POK, O_SOL, O_ALIVE = 0, 32, 38, 46, 51, 58
PER_SOL = int(12000 / 3.76)     # πραγματικά frames ανά sol στο x4 (§9.1)
FAIL = []


def check(ok, msg):
    print(("OK " if ok else "ΛΑΘΟΣ ") + msg)
    if not ok:
        FAIL.append(msg)


def main():
    from cpc import CPC
    sym, g = T.build()
    m = CPC()
    m.run_frames(60)
    assert m.quickload(T.SNA), "quickload απέτυχε"
    m.run_frames(250)
    m.poke(sym["UI_SPD"], 4)

    def w16(a):
        return m.peek(a) | (m.peek(a + 1) << 8)

    rows, first_death = [], None
    for _ in range(4 * PER_SOL // 200):
        m.run_frames(200)
        r = dict(alive=m.peek(g + O_ALIVE), sol=m.peek(g + O_SOL),
                 water=w16(g + O_STOCK), food=w16(g + O_STOCK + 2),
                 pprod=w16(g + O_PPROD), o2p=w16(g + O_O2PROD),
                 pok=m.peek(g + O_POK))
        rows.append(r)
        if r["alive"] < 4 and first_death is None:
            first_death = r
        if r["alive"] == 0:
            break

    # 1. ούτε ρεύμα ούτε οξυγόνο, σε κανένα δείγμα αφού καθίσει η σκόνη.
    # Το μπλακάουτ θέλει ΤΡΕΙΣ κύκλους για να φανεί στο o2_prod: ο πρώτος
    # σαρώνει και δημοσιεύει τη ζήτηση, ο δεύτερος σβήνει το ρεύμα, ο τρίτος
    # δημοσιεύει μηδενική παραγωγή. 64 περιστροφές ο καθένας, ~1.024 frames.
    settled = rows[20:]                 # μετά τα ~4.000 frames
    lit = [i for i, r in enumerate(settled) if r["pok"] or r["o2p"]]
    check(not lit,
          f"χωρίς πάνελ δεν ανάβει τίποτα: {len(lit)} από {len(settled)} "
          f"δείγματα βρήκαν ρεύμα ή οξυγόνο"
          + (f" (πρώτο: {settled[lit[0]]})" if lit else ""))
    check(all(r["pprod"] == 0 for r in rows),
          "η παραγωγή ρεύματος είναι μηδέν σε όλη τη διαδρομή")

    # 2. τους τελειώνει ο αέρας, όχι το νερό
    check(first_death is not None, "κάποιος πέθανε μέσα σε 4 sols")
    if first_death:
        check(first_death["water"] > 0 and first_death["food"] > 0,
              f"πέθαναν από αέρα: στον πρώτο θάνατο έμεναν "
              f"{first_death['water']} νερό και {first_death['food']} τροφή")
        check(1 <= first_death["sol"] <= 3,
              f"«περίπου δύο sols» (§10.1): ο πρώτος θάνατος στο sol "
              f"{first_death['sol']}")
    check(rows[-1]["alive"] == 0,
          f"χωρίς παίκτη η αποικία σβήνει: {rows[-1]['alive']} ζωντανοί στο "
          f"sol {rows[-1]['sol']}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
