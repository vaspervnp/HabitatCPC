#!/usr/bin/env python3
"""Η κάμερα: τι κάνουν πράγματι τα R12/R13 του CRTC (DESIGN §8.2, §15).

Δύο αποτελέσματα, και τα δύο σημαντικά:

  ΘΕΤΙΚΟ   Το offset σκρολάρει ακριβώς όπως λέει το §8.2: μία λέξη = 2 bytes =
           4 pixel του Mode 0. Άρα το σκρολάρισμα ΔΕΝ κοστίζει επανασχεδίαση.

  ΑΡΝΗΤΙΚΟ Εγγραφή στα R12/R13 στη ΜΕΣΗ του frame δεν κάνει τίποτα: ο CRTC
           κλειδώνει τη διεύθυνση έναρξης μία φορά ανά frame. Η τομή δύο
           σελίδων του §8.1 ΔΕΝ γίνεται έτσι.

Το αρνητικό αξίζει μόνο όσο ο έλεγχός του: το split_mode 2 γράφει στο
ΠΕΡΙΓΡΑΜΜΑ στο ίδιο ακριβώς σημείο του frame. Αν το περίγραμμα αλλάζει στη μέση
της οθόνης και η σελίδα όχι, ο χρονισμός είναι σωστός και το συμπέρασμα αφορά
τον CRTC, όχι τον κώδικα.
"""
import collections, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, "/home/vasilhs/cpcemu")

RASM = os.path.expanduser("~/rasm/rasm.exe")
SNA = os.path.join(ROOT, "build", "camtest.sna")

PX_PER_WORD = 16        # pixel του framebuffer ανά λέξη offset (2 bytes = 4 px Mode 0)
SPLIT_DELAY = 1755      # βαθμονομημένο: ~γραμμή 160 της αποδοσμένης εικόνας


def build():
    r = subprocess.run([RASM, "camtest.asm", "-oi", SNA, "-v2", "-s", "-eo"],
                       cwd=HERE, capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(SNA):
        sys.exit("rasm απέτυχε:\n" + r.stdout + r.stderr)
    sym = {}
    for line in open(os.path.join(HERE, "rasmoutput.sym"), encoding="utf-8",
                     errors="replace"):
        p = line.split()
        if len(p) >= 2 and p[1].startswith("#"):
            sym[p[0].upper()] = int(p[1][1:], 16)
    return sym


def line_pos(m, y=60):
    """Πού είναι η κάθετη γραμμή στη γραμμή y της αποδοσμένης εικόνας."""
    img = m.image()
    row = [img.getpixel((x, y)) for x in range(img.size[0])]
    modal = collections.Counter(row).most_common(1)[0][0]
    xs = [x for x, c in enumerate(row) if c != modal]
    return min(xs) if xs else None


def band_changes(m, x=4):
    """Σε ποιες γραμμές αλλάζει το χρώμα της στήλης x (μέσα στο περίγραμμα)."""
    img = m.image()
    col = [img.getpixel((x, y)) for y in range(img.size[1])]
    return [y for y in range(1, len(col)) if col[y] != col[y - 1]]


def content_changes(m, x=384):
    """Σε ποιες γραμμές αλλάζει το περιεχόμενο στο μέσο της οθόνης."""
    img = m.image()
    col = [img.getpixel((x, y)) for y in range(img.size[1])]
    return [y for y in range(1, len(col)) if col[y] != col[y - 1]]


def start(sym, mode=0, off=0):
    from cpc import CPC
    m = CPC()
    m.run_frames(60)
    assert m.quickload(SNA), "quickload απέτυχε"
    m.run_frames(6)
    m.poke(sym["SPLIT_MODE"], mode)
    m.poke(sym["SPLIT_DELAY"], SPLIT_DELAY & 0xFF)
    m.poke(sym["SPLIT_DELAY"] + 1, SPLIT_DELAY >> 8)
    m.poke(sym["CAM_OFF"], off & 0xFF)
    m.poke(sym["CAM_OFF"] + 1, (off >> 8) & 0xFF)
    m.run_frames(16)          # ο βρόχος θέλει λίγα frames να κλειδώσει στο VSync
    return m


def main():
    sym = build()
    fails = 0

    # --- 1. το offset σκρολάρει, και ακριβώς όσο πρέπει ---
    m = start(sym, mode=0, off=0)
    base = line_pos(m)
    assert base is not None, "δεν βρέθηκε η κάθετη γραμμή"
    print(f"offset 0: η γραμμή στο x={base}")
    for off in (1, 2, 4, 8):
        m.poke(sym["CAM_OFF"], off)
        m.poke(sym["CAM_OFF"] + 1, 0)
        m.run_frames(4)
        got = line_pos(m)
        want = base - off * PX_PER_WORD
        ok = got == want
        fails += not ok
        print(f"offset {off}: x={got}  αναμενόμενο {want}  "
              f"{'OK' if ok else 'ΑΠΟΤΥΧΙΑ'}")

    # --- 2. ο έλεγχος: γράψιμο στο περίγραμμα στο σημείο τομής ---
    m = start(sym, mode=2)
    ch = band_changes(m)
    mid = [y for y in ch if 40 < y < 240]
    print(f"\nέλεγχος χρονισμού (περίγραμμα): αλλαγές στις γραμμές {ch[:4]}")
    if not mid:
        print("  ΑΠΟΤΥΧΙΑ — ο χρονισμός δεν πέφτει μέσα στην εικόνα· "
              "το πείραμα της τομής δεν αποδεικνύει τίποτα")
        return 1
    print(f"  OK — το περίγραμμα αλλάζει στη γραμμή {mid[0]}, άρα ο χρονισμός ισχύει")

    # --- 3. η τομή δύο σελίδων: ΔΕΝ γίνεται ---
    m = start(sym, mode=1)
    ch = content_changes(m)
    mid = [y for y in ch if 40 < y < 240]
    print(f"απόπειρα τομής (R12/R13 στη μέση του frame): αλλαγές {ch[:4]}")
    if mid:
        print(f"  Η ΤΟΜΗ ΔΟΥΛΕΥΕΙ στη γραμμή {mid[0]} — το §8.1 στέκει ως έχει")
    else:
        print("  ΕΠΙΒΕΒΑΙΩΜΕΝΟ: καμία αλλαγή. Ο CRTC κλειδώνει τη διεύθυνση")
        print("  έναρξης μία φορά ανά frame — η τομή του §8.1 δεν γίνεται έτσι.")

    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
