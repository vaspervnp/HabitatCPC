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
    # Οι δείκτες με τη σειρά του πηγαίου: σε ίδια διεύθυνση κερδίζει ο
    # τελευταίος (τα equ-μόνο αρχεία δεν πιάνουν χώρο, ο επόμενος ναι).
    main = "main.asm (ο βρόχος)"
    for line in text.splitlines(True):
        m = re.match(r'\s*include\s+"([^"]+)"', line)
        if m:
            n = re.sub(r"\W", "_", os.path.basename(m.group(1)))
            names.append((f"ZZ_SZ_{n.upper()}", n))
            out.append(f"zz_sz_{n}:\n")
        out.append(line)
        if m:
            # ...και ένας ΜΕΤΑ: ό,τι ακολουθεί ως το επόμενο include είναι του
            # main.asm. Από το βήμα 66 το input.asm μπαίνει ανάμεσα στον βρόχο
            # και στις ρουτίνες του, και χωρίς αυτόν οι δεύτερες μετρούσαν στο
            # input.asm.
            names.append((f"ZZ_SZM_{len(names)}", main))
            out.append(f"zz_szm_{len(names) - 1}:\n")
        e = re.match(r"(zz_bank0_end|zz_page2_end):", line)
        if e:
            names.append((e.group(1).upper(), "--"))
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
    marks = [(sym[lab], k, n) for k, (lab, n) in enumerate(names) if lab in sym]
    marks.sort()
    rows = {}
    for (a, _, n), (b, _, _) in zip(marks, marks[1:]):
        # Οι δείκτες «τέλος» δεν είναι αρχή αρθρώματος: το διάστημα από εκεί ως
        # τον επόμενο δείκτη είναι το ΚΕΝΟ ανάμεσα σε δύο περιοχές μνήμης.
        # Το main.asm είναι κομμάτια: ένα άθροισμα, με τη διεύθυνση του πρώτου.
        if b > a and n != "--":
            size, a0 = rows.get(n, (0, a))
            rows[n] = (size + b - a, min(a, a0))
    rows = [(size, a, n) for n, (size, a) in rows.items()]
    # Ο τίτλος έλεγε #3F80 από την εποχή που εκεί καθόταν το επίμετρο· το
    # πραγματικό ταβάνι είναι το TEST_FLOOR του tools/mkdsk.py (#3EC0).
    for lo, hi, title in ((0x0100, 0x4000, "ΤΡΑΠΕΖΑ 0 (#0100-#3EC0)"),
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
