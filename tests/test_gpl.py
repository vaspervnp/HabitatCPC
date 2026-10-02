#!/usr/bin/env python3
"""Το assets/palette.gpl λέει την αλήθεια για τα bytes του παιχνιδιού (§8.6).

Το .gpl είναι για ΑΝΘΡΩΠΟΥΣ: κάποιος ανοίγει το GIMP ή το Aseprite και
ζωγραφίζει με αυτό. Αν πει άλλο χρώμα από αυτό που φορτώνει το παιχνίδι, ή αν
ένα pen γλιστρήσει μία θέση, το sprite βγαίνει λάθος χωρίς κανένα σφάλμα.
Γι' αυτό συγκρίνεται με το palette_fw και το planet_pens του sprites.bin — όχι
με το tools/palette.py του CPCArt, από όπου παράγεται.

Διαβάζεται όπως το διαβάζει το Aseprite, που είναι ο πιο αυστηρός: γραμμή
χρώματος χωρίς όνομα την προσπερνά σιωπηλά, και τότε κάθε επόμενο pen πέφτει
μία θέση πιο πάνω. Το GIMP 3.2 το φόρτωσε μία φορά στο χέρι (βήμα 48): 16
χρώματα, σωστή σειρά, ονόματα ακέραια.
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))

from sprites import load_map, load_bin                                  # noqa: E402
from palette import FW_RGB                                              # noqa: E402

GPL = os.path.join(ROOT, "assets", "palette.gpl")
TERRAIN_PENS = [7, 11, 12, 14]                  # §8.6
FAIL = []


def check(ok, msg):
    print(("OK " if ok else "ΛΑΘΟΣ ") + msg)
    if not ok:
        FAIL.append(msg)


def read_gpl(text):
    """-> (κεφαλίδα εντάξει, [(rgb, όνομα)], [σχόλια], [γραμμές χωρίς όνομα])"""
    lines = text.split("\n")
    head = lines[0].strip() == "GIMP Palette"
    entries, comments, nameless = [], [], []
    for line in lines[1:]:
        t = line.strip()
        if not t:
            continue
        if t.startswith("#"):
            comments.append(line)
            continue
        if not t[0].isdigit():                  # Name:, Columns:
            continue
        m = re.match(r"(\d+)\s+(\d+)\s+(\d+)(?:\s+(.*))?$", t)
        if not m or not m.group(4):
            nameless.append(line)               # το Aseprite την πετά
            continue
        entries.append((tuple(int(v) for v in m.group(1, 2, 3)), m.group(4)))
    return head, entries, comments, nameless


def problems(text, base, planets):
    out = []
    head, entries, comments, nameless = read_gpl(text)
    if not head:
        out.append("η πρώτη γραμμή δεν είναι «GIMP Palette» — το GIMP το αρνείται")
    if nameless:
        out.append("%d γραμμές χρώματος χωρίς όνομα — το Aseprite τις προσπερνά"
                   % len(nameless))
    if len(entries) != 16:
        out.append("%d χρώματα αντί για 16" % len(entries))
    for pen, (rgb, name) in enumerate(entries[:16]):
        want = FW_RGB[base[pen]] if pen < len(base) else None
        if rgb != want:
            out.append("θέση %d: %s, ενώ το palette_fw δίνει fw %d = %s"
                       % (pen, rgb, base[pen], want))
        if not name.startswith("pen %d " % pen):
            out.append("θέση %d: λέγεται «%s»" % (pen, name))

    # ο πίνακας του εδάφους: «#  pen 7  pen 11 ...» και μία σειρά ανά πλανήτη
    hdr = [c for c in comments if re.match(r"#\s+pen \d+\s", c)]
    rows = [(m.group(1), [int(n) for n in re.findall(r"(\d+) [A-Z]", m.group(2))])
            for m in (re.match(r"#   ([a-z]+)\s+(.*)$", c) for c in comments) if m]
    if len(hdr) != 1 or [int(n) for n in re.findall(r"pen (\d+)", hdr[0])] != TERRAIN_PENS:
        out.append("η κεφαλίδα του πίνακα εδάφους δεν είναι τα pens %s" % TERRAIN_PENS)
    want_rows = [planets[i:i + 4] for i in range(0, len(planets), 4)]
    if [fws for _, fws in rows] != want_rows:
        out.append("έδαφος ανά πλανήτη %s, ενώ το planet_pens δίνει %s"
                   % ([fws for _, fws in rows], want_rows))
    if rows and [fws for _, fws in rows][0] != [base[p] for p in TERRAIN_PENS]:
        out.append("ο πρώτος πλανήτης δεν είναι αυτός του palette_fw")
    return out


def main():
    smap, blob = load_map(), load_bin()
    s = smap["palette_fw"]
    base = list(blob[s.off:s.off + s.size])
    s = smap["planet_pens"]
    planets = list(blob[s.off:s.off + s.size])
    text = open(GPL, encoding="utf-8").read()

    bad = problems(text, base, planets)
    for b in bad:
        print("   " + b)
    head, entries, _, _ = read_gpl(text)
    check(not bad, "το palette.gpl: %d pens ίσα με το palette_fw, %d πλανήτες ίσοι "
          "με το planet_pens" % (len(entries), len(planets) // 4))
    check("palette.gpl" in open(os.path.join(ROOT, "assets", "README.md"),
                                encoding="utf-8").read(),
          "το assets/README.md το αναφέρει")

    # ΑΡΝΗΤΙΚΑ: κάθε αλλοίωση πρέπει να πιαστεί.
    lines = text.split("\n")
    at = {int(re.search(r"\tpen (\d+) ", l).group(1)): i
          for i, l in enumerate(lines) if "\tpen " in l}

    def swap_rgb(a, b):
        L = list(lines)
        ra, na = L[at[a]].split("\t", 1)
        rb, nb = L[at[b]].split("\t", 1)
        L[at[a]], L[at[b]] = rb + "\t" + na, ra + "\t" + nb
        return "\n".join(L)

    def swap_line(a, b):
        L = list(lines)
        L[at[a]], L[at[b]] = L[at[b]], L[at[a]]
        return "\n".join(L)

    def unname(p):
        L = list(lines)
        L[at[p]] = L[at[p]].split("\t", 1)[0]
        return "\n".join(L)

    ice = next(i for i, l in enumerate(lines) if l.startswith("#   ice "))
    mutants = [
        ("τα χρώματα των pens 11 και 12 ανταλλαγμένα", swap_rgb(11, 12)),
        # ίδιο RGB (fw 3): μόνο το όνομα δείχνει ότι το pen του εδάφους μπήκε
        # στη θέση του εικονιδίου
        ("οι γραμμές των pens 11 και 13 ανταλλαγμένες", swap_line(11, 13)),
        ("το pen 5 χωρίς όνομα", unname(5)),
        ("ο πάγος με fw 15 αντί για 14 στο pen 7",
         "\n".join(lines[:ice] + [lines[ice].replace("14 Pastel blue", "15 Orange", 1)]
                   + lines[ice + 1:])),
        ("«GIMP palette» με μικρό p", text.replace("GIMP Palette", "GIMP palette", 1)),
    ]
    for label, mutant in mutants:
        assert mutant != text, label
        got = problems(mutant, base, planets)
        check(bool(got), "ΑΡΝΗΤΙΚΟ: %s — %s" % (label, got[0] if got else "ΔΕΝ ΠΙΑΣΤΗΚΕ"))

    print("\n%d/%d" % (len(mutants) + 2 - len(FAIL), len(mutants) + 2))
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
