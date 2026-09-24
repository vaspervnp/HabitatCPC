#!/usr/bin/env python3
"""Οι ανάγκες νικούν τον πίνακα εργασιών (DESIGN §6.6, §6.7).

Το §6.6 λέει: «ο άποικος κάτω από το κατώφλι ΑΦΗΝΕΙ τη δουλειά του και
φεύγει». Ο κώδικας το έκανε μισό — έγραφε NO_TASK, δηλαδή «αδρανής» — και ο
πίνακας εργασιών δίνει δουλειά στους αδρανείς. Το αποτέλεσμα ήταν
πηγαινέλα: η ανάγκη έβαζε προορισμό το κυλικείο, η ανάθεση τον ξανάβαζε στον
κόμβο της δουλειάς, και ο άποικος πέθαινε από πείνα ΔΟΥΛΕΥΟΝΤΑΣ, με τα
τρόφιμα στην αποθήκη. Μετρημένο με το tools/agents.py:

    7100 ταξιδεύει κόμβος=1 προς=2 εργασία=-        νερό=3 τροφή=3 υγεία=216
    7125 στέκεται  κόμβος=3 προς=3 εργασία=#1       νερό=2 τροφή=2 υγεία=213
    7150 ταξιδεύει κόμβος=3 προς=2 εργασία=-        νερό=0 τροφή=0 υγεία=207
    ...  (και ούτω καθεξής ως το μηδέν της υγείας)

Η δοκιμή στήνει ΤΗΝ ΙΔΙΑ ΑΠΟΙΚΙΑ που το βρήκε: την αλυσίδα της τροφής του
tools/balance.py — θερμοκήπιο, εργαστήριο, κυλικείο και τέσσερις ενεργειακές
δομές, όλα έξω από την αρχική αποικία — και κοιτάζει τις μπάρες, όχι τους
νεκρούς: ο θάνατος έρχεται χιλιάδες frames μετά το λάθος. Απλοποιημένες
εκδοχές ΔΕΝ το αναπαράγουν· με ένα εργοτάξιο και τέσσερις αποίκους ο
πεινασμένος φτάνει στο κυλικείο σε 150 frames, με ή χωρίς τη διόρθωση.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")

import balance as B                                          # noqa: E402
import test_game as T                                        # noqa: E402
import agents as A                                           # noqa: E402

FAIL = []
T_NEED = 254                                                 # src/needs.asm
NEED_CRIT = 16                                               # src/needs.asm
R_CANTEEN = 3                                                # src/const.asm


def check(ok, msg):
    print(("OK " if ok else "ΛΑΘΟΣ ") + msg)
    if not ok:
        FAIL.append(msg)


def main():
    sym, g = T.build()
    m = B.boot(sym, T.SNA)
    # RICH, όπως το σενάριο «τροφή» του tools/balance.py: εδώ δεν μετριέται τι
    # αγοράζει το άνοιγμα (αυτό είναι δουλειά του §10.1) αλλά τι κάνουν οι
    # άνθρωποι όταν η αποικία έχει περισσότερες δουλειές από ανθρώπους.
    for k in (3, 4):
        m.poke(g + B.EC["STOCK"] + k * 2, 500 & 255)
        m.poke(g + B.EC["STOCK"] + k * 2 + 1, 500 >> 8)
    spots = B.clear_spots(6, 10)
    plan = ((4, None), (4, None), (7, None), (6, None),
            (1, 3), (0, 5), (0, 1))          # θερμοκήπιο M, εργαστήριο, κυλικείο
    # Η ΑΝΤΛΙΑ ΠΑΕΙ ΣΤΗΝ ΟΧΘΗ, όχι στη σειρά. Από το βήμα 31 το bd_res τη
    # δέχεται μόνο δίπλα σε νερό (§6.5), και μια αντλία που δεν μπήκε είναι
    # μια αλυσίδα τροφής που στερεύει — με τη δοκιμή να λέει «πεθαίνουν».
    res, k = {}, 0
    for item, room in plan:
        w = (4, 6, 8)[item] if item <= 2 else 3
        spot, k = B.pick_spot(item, spots, k, res)
        if spot is None:
            print(f"ΛΑΘΟΣ δεν βρέθηκε θέση με υλικό για το {item}")
            return 1
        tx, ty = spot
        if not B.build(m, sym, item, g + 6, at=(2 * tx + w, 2 * ty + w),
                       room=room):
            print(f"ΛΑΘΟΣ δεν μπήκε το κτίσμα {item} — η δοκιμή δεν στήθηκε")
            return 1
    m.poke(sym["UI_SPD"], 4)

    # ΤΟ ΣΗΜΑΔΙ ΕΙΝΑΙ Η ΜΠΑΡΑ, ΟΧΙ Ο ΝΕΚΡΟΣ. Στο πηγαινέλα οι μπάρες κάθονται
    # στο μηδέν για χιλιάδες frames όσο η υγεία στραγγίζει: ο θάνατος είναι το
    # αποτέλεσμα, το μηδέν είναι το λάθος.
    n, seen_need, floor, stuck = A.NAG, set(), 255, 0
    zero_since = {}
    for k in range(90):
        m.run_frames(100)
        fr = (k + 1) * 100
        s = A.snap(m, sym)
        if not m.peek(g + 2) and not m.peek(g + 3):
            break                             # άδειασε η αποθήκη: άλλη ιστορία
        for i in range(n):
            a = s[i]
            if not a["flags"] & A.F_ALIVE:
                continue
            if a["task"] == T_NEED:
                seen_need.add(i)
            low = min(a["food"], a["water"])
            floor = min(floor, low)
            if low:
                zero_since.pop(i, None)
            else:
                stuck = max(stuck, fr - zero_since.setdefault(i, fr))

    check(seen_need,
          f"η ανάγκη γίνεται εργασία: {len(seen_need)} άποικοι πέρασαν από "
          f"task={T_NEED}, που ο πίνακας εργασιών δεν το αγγίζει")
    check(stuck == 0,
          f"καμία μπάρα δεν κόλλησε στο μηδέν: χειρότερη παραμονή {stuck} "
          f"frames (με τα τρόφιμα στην αποθήκη)")
    check(floor > NEED_CRIT,
          f"και καμία δεν κατέβηκε καν στο κρίσιμο: χαμηλότερη {floor} "
          f"(κατώφλι {NEED_CRIT})")
    check(m.peek(g + 58) == 4,
          f"κανένας θάνατος: {m.peek(g + 58)} ζωντανοί από 4")

    # --- ΚΑΙ Ο ΠΙΝΑΚΑΣ ΕΡΓΑΣΙΩΝ ΣΤΕΛΕΧΩΝΕΙ ΤΟ ΣΩΣΤΟ (§6.7) ---------------
    # Το κυλικείο του παίκτη είναι ο τελευταίος κρίκος της τροφής και ήταν ο
    # μόνος που δεν έπιανε ποτέ άνθρωπο: όλα τα OPERATE είχαν την ίδια
    # προτεραιότητα, η ισοπαλία έσπαγε στην απόσταση, και η απόσταση δεν
    # αλλάζει ποτέ. Μετρημένο πριν: 147 δείγματα στη σειρά με την εργασία του
    # αδιάθετη, ενώ το θερμοκήπιο δίπλα στοίβαζε 250 άμυλο.
    d = A.domes(m, sym)
    cans = [i for i, x in enumerate(d) if x["state"] == 2 and x["room"] == R_CANTEEN]
    check(len(cans) == 2, f"δύο κυλικεία: της αποικίας και του παίκτη ({cans})")
    staffed = 0
    for _ in range(60):
        m.run_frames(100)
        if any(A.domes(m, sym)[c]["ops"] for c in cans[1:]):
            staffed = 1
            break
    check(staffed, "το κυλικείο του παίκτη πιάνει χειριστή — αλλιώς το άμυλο "
                   "στοιβάζεται και κανείς δεν μαγειρεύει")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
