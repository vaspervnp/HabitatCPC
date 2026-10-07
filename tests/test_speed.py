#!/usr/bin/env python3
"""Η ταχύτητα του παιχνιδιού (DESIGN.md §9.1).

Τα πλήκτρα 1-4 ήταν δεμένα από το βήμα 12 και ΚΑΝΕΙΣ δεν τα διάβαζε: ο πίνακας
του §9.1 τα περιέγραφε σαν υλοποιημένα. Τώρα ο βρόχος τρέχει 0, 1, 2 ή 4
θέσεις τροχού ανά frame.

Το μέτρο είναι το EC_FRAME, ο μετρητής frames της προσομοίωσης: ανεβαίνει 16
ανά περιστροφή, δηλαδή ένα ανά θέση. Σε N frames πραγματικού χρόνου πρέπει να
ανέβει N στο x1, 2N στο x2, 4N στο x4 και ΜΗΔΕΝ στην παύση.

Το x4 δεν είναι εγγυημένο: τέσσερις θέσεις ανά frame είναι τετραπλάσια δουλειά
και ο κανόνας 1 του §7.1 δεν ισχύει πια — το frame ξεφεύγει και η οθόνη χάνει
frames. Η δοκιμή μετρά ΠΟΣΟ πιάνει στην πράξη αντί να υποθέτει.
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")

from sprites import load_map, load_bin                                  # noqa: E402
import hudread                                                          # noqa: E402

RASM = os.path.expanduser("~/rasm/rasm.exe")
SNA = os.path.join(ROOT, "build", "main.sna")
N = 400
FAIL = []


def check(ok, msg):
    print(("OK " if ok else "ΛΑΘΟΣ ") + msg)
    if not ok:
        FAIL.append(msg)


def build():
    for tool in ("mkoffsets.py", "pack.py", "mknew.py"):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", tool)],
                           capture_output=True, text=True)
        if r.returncode:
            sys.exit(f"{tool} απέτυχε:\n{r.stdout}{r.stderr}")
    r = subprocess.run([RASM, "main.asm", "-oi", SNA, "-v2", "-s"],
                       cwd=os.path.join(ROOT, "src"), capture_output=True, text=True)
    if r.returncode or not os.path.exists(SNA):
        sys.exit("rasm απέτυχε:\n" + r.stdout + r.stderr)
    sym = {}
    for line in open(os.path.join(ROOT, "src", "rasmoutput.sym"),
                     encoding="utf-8", errors="replace"):
        p = line.split()
        if len(p) >= 2 and p[1].startswith("#"):
            sym[p[0].upper()] = int(p[1][1:], 16)
    g = None
    for line in open(os.path.join(ROOT, "build", "layout.asm"), encoding="utf-8"):
        if line.startswith("G_econ_state"):
            g = int(line.split("#")[1].strip(), 16)
    return sym, g


def main():
    sym, g = build()
    from cpc import CPC
    m = CPC()
    m.run_frames(60)
    assert m.quickload(SNA), "quickload απέτυχε"
    # Προθέρμανση: τα πρώτα δευτερόλεπτα ο τροχός ξαναχτίζει τη δρομολόγηση
    # (rt_dirty μετά το game_new) και το frame ΞΕΦΕΥΓΕΙ κανονικά. Χωρίς αυτό, η
    # μέτρηση του x1 βγάζει 0,84 και μοιάζει με σφάλμα του βρόχου.
    m.run_frames(900)

    def w16(a):
        return m.peek(a) | (m.peek(a + 1) << 8)

    def hud_row(row):
        return hudread.text(m, sym, row)

    def tap(key):
        m.key_down(key)
        m.run_frames(4)
        m.key_up(key)
        # Στο x4 ένα πέρασμα του βρόχου ΞΕΠΕΡΝΑ το frame, οπότε ένα δείγμα
        # μνήμης μπορεί να πέσει στη μέση της σχεδίασης του πίνακα: οι στήλες
        # έχουν σβηστεί και ο δείκτης δεν έχει γραφτεί ακόμη.
        m.run_frames(30)

    results = {}
    for key, want, label in (("2", 1, "x1"), ("3", 2, "x2"), ("4", 4, "x4"),
                             ("1", 0, "παύση")):
        tap(key)
        check(m.peek(sym["UI_SPD"]) == want,
              f"το πλήκτρο {key} έβαλε ταχύτητα {m.peek(sym['UI_SPD'])} "
              f"(περίμενα {want})")
        row = hud_row(3)
        shown = row[35:40]
        expect = {0: "PAUSE", 1: "  x1 ", 2: "  x2 ", 4: "  x4 "}[want]
        check(shown == expect, f"το HUD δείχνει |{shown}| ({label})")
        over0 = m.peek(sym["DIRTY_OVER"])
        a = w16(g + 52)
        m.run_frames(N)
        b = w16(g + 52)
        results[want] = (b - a) & 0xFFFF
        over = (m.peek(sym["DIRTY_OVER"]) - over0) & 0xFF
        print(f"   {label:>6}: {results[want]:>5} frames προσομοίωσης σε {N} "
              f"πραγματικά = x{results[want] / N:.2f}"
              + (f", υπερχείλιση λίστας {over}" if over else ""))

    check(results[0] == 0, f"η παύση σταματά την προσομοίωση ({results[0]})")
    # ΤΟ x1 ΕΙΝΑΙ 1,00 ΑΠΟ ΤΟ ΒΗΜΑ 52, ΚΑΙ ΤΟ ΟΡΙΟ ΦΥΛΑΕΙ ΤΟ ΚΟΣΤΟΣ ΤΟΥ HUD.
    # Ως τότε μία επανασχεδίαση HUD κόστιζε 1,15 frames και γινόταν κάθε
    # δεκαέξι, άρα η προσομοίωση έπαιρνε 16 από τα 17,2: 0,92 (μετρημένο και με
    # `ret` πάνω από το ml_hud, που έδινε ακριβώς 1,00). Ηταν 0,84 πριν την κρυφή
    # μνήμη του §9.2. Στα 0,65 frames η επανασχεδίαση χωράει στο περιθώριο των
    # γύρω frames· αν το HUD ξαναμεγαλώσει, πέφτει αυτό, και πέφτει κάτω από το
    # όριο — το παλιό 0,92 αποτυγχάνει εδώ.
    check(0.97 <= results[1] / N <= 1.00,
          f"το x1 τρέχει στο {results[1] / N:.2f} του ονομαστικού — το HUD "
          f"(0,65 frames ανά δεκαέξι) δεν του παίρνει πια τίποτα")
    check(results[2] / results[1] > 1.8,
          f"το x2 είναι διπλάσιο του x1 ({results[2] / results[1]:.2f}x)")
    check(results[4] / results[2] > 1.8,
          f"και το x4 διπλάσιο του x2 ({results[4] / results[2]:.2f}x)")

    if FAIL:
        print(f"\nΑΠΟΤΥΧΙΑ — {len(FAIL)}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
