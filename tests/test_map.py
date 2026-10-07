#!/usr/bin/env python3
"""Ο ΧΑΡΤΗΣ ΜΕΤΡΑΕΙ: η αντλία θέλει λίμνη, το ορυχείο θέλει φλέβα (§6.5, §5.6).

Ο πίνακας του §6.5 γράφει «extractor (on water)» και «mine (on ore)» από την
πρώτη σελίδα του σχεδίου. Ο κώδικας δεν το διάβαζε ποτέ: μια αντλία χτιζόταν
μέσα στην αποικία, στη μέση της ερήμου, οπουδήποτε — και έβγαζε νερό. Το ίδιο
το ορυχείο. Δηλαδή ο κόσμος που παράγεται σε 13,5 δευτερόλεπτα (§5) ήταν
ταπετσαρία: καμία απόφαση του παίκτη δεν κοίταζε τι έχει ο τόπος.

Τρεις ισχυρισμοί, και ο τρίτος είναι το αρνητικό δείγμα:

  1. Η αντλία λέει ΟΧΙ σε στεγνό έδαφος, και το λέει με λόγια: ο πίνακας
     γράφει NEEDS WATER NEARBY, όχι BLOCKED. Πάνω σε καθαρό χώμα, ένα σκέτο
     «μπλοκαρισμένο» διαβάζεται ως σφάλμα του παιχνιδιού.
  2. Στην όχθη λέει ΝΑΙ, και το κτίσμα μπαίνει πραγματικά — εγγραφή δομής και
     πληρωμένο μέταλλο. Το ίδιο το ορυχείο στους πρόποδες της φλέβας.
  3. ΣΤΟ ΙΔΙΟ στεγνό έδαφος ένας θόλος χτίζεται κανονικά. Χωρίς αυτό, η δοκιμή
     θα περνούσε και με έναν έλεγχο που λέει όχι παντού.

Η θέση δεν διαλέγεται με το μάτι: το tools/balance.py ξέρει τον ίδιο κανόνα
(has_near) και τον κοιτάζει στο ΙΔΙΟ επίπεδο κόσμου που θα δει το παιχνίδι.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/vasilhs/cpcemu")

from sprites import load_map, load_bin                             # noqa: E402
import hudread                                                     # noqa: E402
import balance as B                                                # noqa: E402
import test_game as T                                              # noqa: E402

FAIL = []
I_DOME_S, I_SOLAR, I_EXTRACT, I_MINE = 0, 4, 7, 8   # σειρά στο bld_items


def check(ok, msg):
    print(("OK " if ok else "ΛΑΘΟΣ ") + msg)
    if not ok:
        FAIL.append(msg)


def main():
    sym, g = T.build()
    g_metal = g + 3 * 2

    m = B.boot(sym, T.SNA)

    def hud(row):
        return hudread.text(m, sym, row)

    def ghost(item, tx, ty, w):
        """Βάζει το φάντασμα εκεί και ΔΕΝ πατά το τελευταίο FIRE."""
        B.build(m, sym, item, g_metal, at=(2 * tx + w, 2 * ty + w), place=False)
        return m.peek(sym["UI_BAD"]), hud(4).strip()

    # --- οι θέσεις, από τον ίδιο κανόνα που ελέγχει το παιχνίδι -----------
    pl = B.plane()
    shore = B.res_spots("water", 3, 1)
    vein = B.res_spots("ore", 4, 1)
    dry3 = [s for s in B.clear_spots(4, 6) if not B.has_near(pl, *s, 3, "water")]
    dry4 = [s for s in B.clear_spots(4, 6) if not B.has_near(pl, *s, 4, "ore")]
    if not (shore and vein and dry3 and dry4):
        print(f"ΛΑΘΟΣ δεν στήθηκε η δοκιμή: όχθη={shore} φλέβα={vein} "
              f"στεγνά={dry3[:1]}/{dry4[:1]}")
        return 1
    print(f"   όχθη {shore[0]}, φλέβα {vein[0]}, στεγνό {dry3[0]}")

    # --- 1. η αντλία σε στεγνό έδαφος ------------------------------------
    bad, say = ghost(I_EXTRACT, *dry3[0], 3)
    check(bad and "NEEDS WATER" in say,
          f"η αντλία λέει όχι σε στεγνό έδαφος {dry3[0]} και λέει γιατί: "
          f"ui_bad={bad} |{say}|")

    # --- 2. και ναι στην όχθη, με το κτίσμα να μπαίνει --------------------
    bad, say = ghost(I_EXTRACT, *shore[0], 3)
    check(not bad and "READY" in say,
          f"και ναι στην όχθη {shore[0]}: ui_bad={bad} |{say}|")
    tx, ty = shore[0]
    check(B.build(m, sym, I_EXTRACT, g_metal, at=(2 * tx + 3, 2 * ty + 3)),
          "και η αντλία μπαίνει στ' αλήθεια — πληρωμένο μέταλλο")

    # --- 3. το ορυχείο, με τον ίδιο κανόνα και άλλο υλικό -----------------
    bad, say = ghost(I_MINE, *dry4[0], 4)
    check(bad and "ORE VEIN" in say,
          f"το ορυχείο λέει όχι μακριά από φλέβα {dry4[0]}: "
          f"ui_bad={bad} |{say}|")
    bad, say = ghost(I_MINE, *vein[0], 4)
    check(not bad and "READY" in say,
          f"και ναι στους πρόποδες {vein[0]}: ui_bad={bad} |{say}|")
    tx, ty = vein[0]
    check(B.build(m, sym, I_MINE, g_metal, at=(2 * tx + 4, 2 * ty + 4)),
          "και το ορυχείο μπαίνει στ' αλήθεια")

    # --- 4. ΤΟ ΑΡΝΗΤΙΚΟ ΔΕΙΓΜΑ: στο ίδιο χώμα, θόλος και ηλιακό ----------
    bad, say = ghost(I_DOME_S, *dry3[0], 4)
    check(not bad and "READY" in say,
          f"ΚΑΙ ΤΟ ΙΔΙΟ ΣΤΕΓΝΟ ΕΔΑΦΟΣ δέχεται θόλο {dry3[0]}: ο κανόνας είναι "
          f"της αντλίας, όχι του τόπου — ui_bad={bad} |{say}|")
    # ΚΑΙ ΜΙΑ ΔΟΜΗ ΠΟΥ ΔΕΝ ΖΗΤΑ ΥΛΙΚΟ, που είναι άλλος δρόμος μέσα στον ίδιο
    # έλεγχο: ο θόλος βγαίνει στην πρώτη σύγκριση (BK_DOME = 0) και θα περνούσε
    # ακόμη κι αν η έξοδος άφηνε σκουπίδια στο A. Ο ηλιακός είναι BK_STRUCT και
    # φτάνει ως τη δεύτερη — εκεί ακριβώς που ο συλλέκτης έβγαινε «2 άκυρα
    # tiles» επειδή το K_COLLECT είναι 2.
    bad, say = ghost(I_SOLAR, *dry3[0], 3)
    check(not bad and "READY" in say,
          f"και ηλιακό στο ίδιο σημείο: μια δομή χωρίς υλικό δεν ελέγχεται "
          f"καθόλου — ui_bad={bad} |{say}|")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
