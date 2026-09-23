#!/usr/bin/env python3
"""Ο οδηγός δισκέτας (DESIGN.md §11).

Το AMSDOS δεν υπάρχει την ώρα που τρέχει το παιχνίδι — ο χώρος εργασίας του
είναι δεδομένα της τράπεζας 2 και τα ROM είναι σβηστά. Το save/load μιλά
κατευθείαν στον μPD765.

Τρεις έλεγχοι, και ο πρώτος είναι που δεν μπορεί να εξαπατηθεί:

  1. Διαβάζει τον ΚΑΤΑΛΟΓΟ του δίσκου (track 0, τομέας #C1) και τα bytes
     συγκρίνονται με την εικόνα .dsk στον host. Ενας οδηγός που δεν μιλά στον
     ελεγκτή δεν μπορεί να τα μαντέψει.
  2. Γράφει μοτίβο σε τρεις άδειους τομείς και τους ξαναδιαβάζει.
  3. Ο ΓΕΙΤΟΝΑΣ: ο τομέας #C5 του ίδιου track πρέπει να είναι ακόμη #E5 —
     αλλιώς η εγγραφή πήγε κάπου αλλού εκτός από εκεί που της είπαμε.
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")

from dsk import Dsk                                                     # noqa: E402

RASM = os.path.expanduser("~/rasm/rasm.exe")
SNA = os.path.join(ROOT, "build", "fdctest.sna")
DSK = os.path.join(ROOT, "build", "habitat.dsk")
NSECT = 3
FAIL = []


def check(ok, msg):
    print(("OK " if ok else "ΛΑΘΟΣ ") + msg)
    if not ok:
        FAIL.append(msg)


def build():
    r = subprocess.run([RASM, "fdctest.asm", "-oi", SNA, "-v2", "-s"],
                       cwd=HERE, capture_output=True, text=True)
    if r.returncode or not os.path.exists(SNA):
        sys.exit("rasm απέτυχε:\n" + r.stdout + r.stderr)
    sym = {}
    for line in open(os.path.join(HERE, "rasmoutput.sym"),
                     encoding="utf-8", errors="replace"):
        p = line.split()
        if len(p) >= 2 and p[1].startswith("#"):
            sym[p[0].upper()] = int(p[1][1:], 16)
    return sym


def main():
    if not os.path.exists(DSK):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "mkdsk.py")],
                           capture_output=True, text=True)
        if r.returncode:
            sys.exit("mkdsk απέτυχε:\n" + r.stdout + r.stderr)
    sym = build()
    from cpc import CPC

    d = Dsk(DSK)
    m = CPC()
    m.run_frames(30)
    m.insert_disc(DSK)
    assert m.quickload(SNA), "quickload απέτυχε"
    for _ in range(60):
        m.run_frames(10)
        if m.peek(sym["DONE_FLAG"]) == 0x5A:
            break
    check(m.peek(sym["DONE_FLAG"]) == 0x5A,
          f"ο οδηγός τελείωσε (PC=#{m.pc:04X})")

    st = {n: m.peek(sym[n.upper()]) for n in ("r_read", "r_write", "r_back", "r_nbr")}
    check(all(v == 0 for v in st.values()),
          f"καμία εντολή δεν γύρισε λάθος: {st}")

    got = bytes(m.read_ram(0x8000, 512))
    want = d.sector(0, 0xC1)
    check(got == want,
          "ο κατάλογος του δίσκου διαβάστηκε byte-προς-byte "
          f"(πρώτο όνομα: {bytes(got[1:12]).decode('latin1')!r})")

    src = bytes(m.read_ram(0x9000, NSECT * 512))
    back = bytes(m.read_ram(0xA000, NSECT * 512))
    check(src == back,
          f"{NSECT} τομείς γράφτηκαν και ξαναδιαβάστηκαν ίδιοι")
    check(len(set(src)) > 100 and src[:512] != src[512:1024],
          f"το μοτίβο ποικίλλει ({len(set(src))} διαφορετικά bytes) και δεν "
          "επαναλαμβάνεται ανά τομέα")

    nbr = bytes(m.read_ram(0xB000, 512))
    check(nbr == b"\xE5" * 512,
          f"ο γείτονας #C5 δεν αγγίχτηκε ({nbr[:4].hex()})")

    if FAIL:
        print(f"\nΑΠΟΤΥΧΙΑ — {len(FAIL)}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
