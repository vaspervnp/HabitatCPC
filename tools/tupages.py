#!/usr/bin/env python3
"""tupages.py — οι σελίδες του tutorial (βήμα 175, DESIGN §9.6).

Ο παίκτης ζήτησε μετά το βήμα 174: «Το tutorial δεν έχει οδηγίες. Βάλε να έχει
οδηγίες. Χρησιμοποίησε και αρχείο στην δισκέττα αν χρειάζεσαι για τα κείμενά
του.» Και διάλεξε μια σελίδα σε κάθε βήμα, σε όλη την οθόνη όπως η βοήθεια,
στα αγγλικά.

Από το src/tupages.txt φτιάχνει:
  build/tutor.txt    το TUTOR.TXT του δίσκου (tools/mkdsk.py): ASCII, CR LF,
                     όπως θα το έδειχνε ένα TYPE. Κάθε σελίδα ξεκινά με «@»,
                     ο τίτλος της ανάμεσα σε αστερίσκους (λευκός), μια κενή
                     γραμμή, και οι γραμμές της. Στο τέλος #1A.
  build/tupages.asm  TP_N και tp_idx: πού ξεκινά κάθε σελίδα μέσα στο αρχείο,
                     μετά το «@» (src/tpage.asm). Ο δίσκος δίνει τα blocks του
                     αρχείου από τον κατάλογό του· το πού μέσα σε αυτά το ξέρει
                     ήδη ο κώδικας.

Οι κανόνες, που τους ελέγχει εδώ (και το tests/test_tupage.py ξανά):
  - μόνο οι χαρακτήρες της γραμματοσειράς, 32-95: κεφαλαία, ψηφία, σημεία·
    όχι το «@», που χωρίζει σελίδες·
  - ως TP_W χαρακτήρες η γραμμή χωρίς τους αστερίσκους, και ζυγοί αστερίσκοι·
  - ως TP_H γραμμές το σώμα μιας σελίδας (οι σειρές 3-22 της οθόνης);
  - το «^» μόνο στις σελίδες του G και του τέλους (βήμα 177), και πάντα με
    ένα από τα πεδία του FIELDS μετά: το πλάτος του μετρά όσο το πιο πλατύ
    που μπορεί να γράψει.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "src", "tupages.txt")
BUILD = os.path.join(ROOT, "build")

TP_W = 76                       # στήλες 2-77 (src/tpage.asm: TP_COL)
TP_H = 20                       # σειρές 3-22 (TP_BROW ως πριν από το υποσέλιδο)
TP_N = 23                       # εισαγωγή, 14 βήματα (TU_N), «THE COLONY IS YOURS»,
                                # και από το βήμα 177 τα πέντε ορόσημα, το G και το τέλος
TP_FLD = 21                     # από αυτήν τα πεδία «^» (src/tpage.asm, tp_field)
FIELDS = {**{c: 4 for c in "01234"},            # «DONE» ή τέσσερα κενά
          **{c: 5 for c in "ABCDEFGHIJKL"}}     # ένας αριθμός, ως 65535


class Fail(Exception):
    pass


def parse(path=SRC):
    """[(τίτλος, [γραμμές])], με τα σχόλια (;) έξω και τις κενές γραμμές στο
    τέλος μιας σελίδας κομμένες."""
    pages = []
    for n, line in enumerate(open(path, encoding="utf-8"), 1):
        line = line.rstrip("\r\n").rstrip()
        if line.startswith(";"):
            continue
        if line.startswith("@"):
            pages.append((line[1:].strip(), [], n))
            continue
        if not pages:
            if line:
                raise Fail(f"γραμμή {n}: κείμενο πριν από την πρώτη σελίδα")
            continue
        pages[-1][1].append((line, n))
    out = []
    for title, body, n in pages:
        while body and not body[-1][0]:
            body.pop()
        out.append((title, n, body))
    return out


def check(pages):
    if len(pages) != TP_N:
        raise Fail(f"{len(pages)} σελίδες, όχι {TP_N}")
    for k, (title, n, body) in enumerate(pages):
        rows = [(title, n)] + body
        for text, ln in rows:
            for c in text:
                if not 32 <= ord(c) <= 95 or c == "@":
                    raise Fail(f"γραμμή {ln}: «{c}» δεν είναι στη γραμματοσειρά")
            if text.count("*") % 2:
                raise Fail(f"γραμμή {ln}: μονός αριθμός αστερίσκων")
            w = len(text.replace("*", ""))
            for m in re.finditer(r"\^(.?)", text):
                if k < TP_FLD or m.group(1) not in FIELDS:
                    raise Fail(f"γραμμή {ln}: «^{m.group(1)}» δεν είναι πεδίο εδώ")
                w += FIELDS[m.group(1)] - 2
            if w > TP_W:
                raise Fail(f"γραμμή {ln}: {w} χαρακτήρες, ως {TP_W}")
        if len(body) > TP_H:
            raise Fail(f"σελίδα «{title}» (γραμμή {n}): {len(body)} γραμμές, ως {TP_H}")


def image(pages):
    """Τα bytes του TUTOR.TXT και οι αρχές των σελίδων (μετά το «@»)."""
    data = bytearray()
    idx = []
    for title, _, body in pages:
        data += b"@"
        idx.append(len(data))
        data += b"*" + title.encode("ascii") + b"*\r\n\r\n"
        for text, _ in body:
            data += text.encode("ascii") + b"\r\n"
    data += b"\x1a"
    return bytes(data), idx


def write():
    pages = parse()
    check(pages)
    data, idx = image(pages)
    os.makedirs(BUILD, exist_ok=True)
    with open(os.path.join(BUILD, "tutor.txt"), "wb") as f:
        f.write(data)
    with open(os.path.join(BUILD, "tupages.asm"), "w", encoding="utf-8") as f:
        f.write("; ΠΑΡΑΓΕΤΑΙ από το tools/tupages.py (βήμα 175) — μην το επεξεργάζεσαι.\n"
                f"; TUTOR.TXT: {len(data)} bytes, {TP_N} σελίδες.\n"
                f"TP_N        equ {TP_N}\n"
                f"TP_SIZE     equ {len(data)}\n"
                "tp_idx:\n")
        for i in range(0, TP_N, 8):
            f.write("        dw      " + ", ".join(str(v) for v in idx[i:i + 8]) + "\n")
    return data, idx


if __name__ == "__main__":
    try:
        data, idx = write()
    except Fail as e:
        sys.exit(f"tupages: {e}")
    print(f"build/tutor.txt: {len(data)} bytes, {len(idx)} σελίδες")
