#!/usr/bin/env python3
"""Πόσα bytes τρώει κάθε αρχείο του src/, ανά περιοχή μνήμης.

ΓΙΑΤΙ ΥΠΑΡΧΕΙ. Το tools/mkdsk.py λέει «82 bytes ελεύθερα στην τράπεζα 0» και
σταματά εκεί: δεν λέει ΠΟΙΟΣ τα έφαγε. Χωρίς αυτό, το «ελευθέρωσε χώρο» είναι
εικασία — και η εικασία στο μέγεθος κώδικα είναι συνήθως λάθος κατά μια τάξη
μεγέθους.

ΠΩΣ. Φτιάχνει ένα ΑΝΤΙΓΡΑΦΟ του main.asm με μια ετικέτα πριν από κάθε
`include`, το μεταγλωττίζει, και διαβάζει τις διευθύνσεις από τον πίνακα
συμβόλων. Το πραγματικό main.asm δεν αγγίζεται, και το binary που παράγεται
εδώ πετιέται: μετράμε, δεν χτίζουμε.
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
RASM = os.path.expanduser("~/rasm/rasm.exe")
TMP = "zz_sizemap.asm"                  # μέσα στο src/: τα include είναι σχετικά


def build_map():
    text = open(os.path.join(SRC, "main.asm"), encoding="utf-8").read()
    out, names = [], []
    for line in text.splitlines(True):
        m = re.match(r'\s*include\s+"([^"]+)"', line)
        if m:
            n = re.sub(r"\W", "_", os.path.basename(m.group(1)))
            names.append(n)
            out.append(f"zz_sz_{n}:\n")
        out.append(line)
    path = os.path.join(SRC, TMP)
    open(path, "w", encoding="utf-8").write("".join(out))
    try:
        # Το σύμβολο-αρχείο πάει ΔΙΠΛΑ ΣΤΗΝ ΕΞΟΔΟ, όχι στο src/: έτσι η
        # μέτρηση δεν πατάει το rasmoutput.sym που διαβάζουν οι δοκιμές.
        r = subprocess.run([RASM, TMP, "-o", "/tmp/zz_sizemap", "-s", "-eo"],
                           cwd=SRC, capture_output=True, text=True)
        if r.returncode:
            sys.exit("rasm απέτυχε:\n" + r.stdout + r.stderr)
        sym = {}
        for line in open("/tmp/zz_sizemap.sym",
                         encoding="utf-8", errors="replace"):
            p = line.split()
            if len(p) >= 2 and p[1].startswith("#"):
                sym[p[0].upper()] = int(p[1][1:], 16)
    finally:
        os.unlink(path)
    return names, sym


def main():
    names, sym = build_map()
    marks = [(sym[f"ZZ_SZ_{n.upper()}"], n) for n in names
             if f"ZZ_SZ_{n.upper()}" in sym]
    marks.append((sym["ZZ_BANK0_END"], "-- τέλος τράπεζας 0 --"))
    marks.append((sym["START"], "main.asm (ο βρόχος)"))
    marks.append((sym["ZZ_PAGE2_END"], "-- τέλος κώδικα τράπεζας 2 --"))
    marks.sort()
    rows = []
    for (a, n), (b, _) in zip(marks, marks[1:]):
        # Οι δείκτες «τέλος» δεν είναι αρχή αρθρώματος: το διάστημα από εκεί ως
        # τον επόμενο δείκτη είναι το ΚΕΝΟ ανάμεσα σε δύο περιοχές μνήμης.
        if b > a and not n.startswith("--"):
            rows.append((b - a, a, n))
    for lo, hi, title in ((0x0100, 0x4000, "ΤΡΑΠΕΖΑ 0 (#0100-#3F80)"),
                          (0x8000, 0xC000, "ΤΡΑΠΕΖΑ 2, κώδικας"),
                          (0xC000, 0x10000, "ΤΡΑΠΕΖΑ 7, κείμενα")):
        part = [r for r in rows if lo <= r[1] < hi]
        if not part:
            continue
        print(f"\n{title}  σύνολο {sum(r[0] for r in part)} bytes")
        for size, addr, name in sorted(part, reverse=True):
            print(f"  {size:6d}  #{addr:04X}  {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
