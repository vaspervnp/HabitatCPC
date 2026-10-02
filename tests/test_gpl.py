#!/usr/bin/env python3
"""Τα assets/palette*.gpl λένε την αλήθεια για τα bytes του παιχνιδιού (§8.6).

Τα .gpl είναι για ΑΝΘΡΩΠΟΥΣ: κάποιος ανοίγει το GIMP ή το Aseprite και
ζωγραφίζει με αυτά. Αν πουν άλλο χρώμα από αυτό που φορτώνει το παιχνίδι, ή αν
ένα pen γλιστρήσει μία θέση, το sprite βγαίνει λάθος χωρίς κανένα σφάλμα.
Γι' αυτό συγκρίνονται με το palette_fw και το planet_pens του sprites.bin — όχι
με το tools/palette.py του CPCArt, από όπου παράγονται.

Ένα αρχείο ανά πλανήτη: palette.gpl ο πρώτος (το palette_fw, από όπου ξεκινά
το παιχνίδι), palette_<όνομα>.gpl οι άλλοι, με τα ονόματα από τη γραμμή
PLANETS του sprites.asm. Σε κάθε πλανήτη τα pens του εδάφους είναι η σειρά του
στο planet_pens και όλα τα άλλα του palette_fw — ό,τι κάνει και το pal_planet.

Διαβάζονται όπως τα διαβάζει το Aseprite, που είναι ο πιο αυστηρός: γραμμή
χρώματος χωρίς όνομα την προσπερνά σιωπηλά, και τότε κάθε επόμενο pen πέφτει
μία θέση πιο πάνω. Το GIMP 3.2 τα φόρτωσε στο χέρι (βήματα 48-49): 16 χρώματα
το καθένα, σωστή σειρά, ονόματα ακέραια.
"""
import glob, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ASSETS = os.path.join(ROOT, "assets")
sys.path.insert(0, os.path.join(ROOT, "tools"))

from sprites import load_map, load_bin                                  # noqa: E402
from palette import FW_RGB                                              # noqa: E402

TERRAIN_PENS = [7, 11, 12, 14]                  # §8.6
FAIL, RUN = [], [0]


def check(ok, msg):
    RUN[0] += 1
    print(("OK " if ok else "ΛΑΘΟΣ ") + msg)
    if not ok:
        FAIL.append(msg)


def gpl_name(i, names):
    return "palette.gpl" if i == 0 else "palette_%s.gpl" % names[i]


def read_gpl(text):
    """-> (κεφαλίδα εντάξει, Name, [(rgb, όνομα)], [σχόλια], [γραμμές χωρίς όνομα])"""
    lines = text.split("\n")
    head = lines[0].strip() == "GIMP Palette"
    title, entries, comments, nameless = None, [], [], []
    for line in lines[1:]:
        t = line.strip()
        if not t:
            continue
        if t.startswith("#"):
            comments.append(line)
            continue
        if not t[0].isdigit():                  # Name:, Columns:
            if t.startswith("Name:"):
                title = t[5:].strip()
            continue
        m = re.match(r"(\d+)\s+(\d+)\s+(\d+)(?:\s+(.*))?$", t)
        if not m or not m.group(4):
            nameless.append(line)               # το Aseprite την πετά
            continue
        entries.append((tuple(int(v) for v in m.group(1, 2, 3)), m.group(4)))
    return head, title, entries, comments, nameless


def problems(text, want, planets, pname):
    """want = οι 16 αριθμοί firmware που περιμένουμε, pen 0..15."""
    out = []
    head, title, entries, comments, nameless = read_gpl(text)
    if not head:
        out.append("η πρώτη γραμμή δεν είναι «GIMP Palette» — το GIMP το αρνείται")
    if title != "Habitat CPC Mode 0 (%s)" % pname:
        out.append("λέγεται «%s» — το GIMP ξεχωρίζει τις παλέτες με το όνομα" % title)
    if nameless:
        out.append("%d γραμμές χρώματος χωρίς όνομα — το Aseprite τις προσπερνά"
                   % len(nameless))
    if len(entries) != 16:
        out.append("%d χρώματα αντί για 16" % len(entries))
    for pen, (rgb, name) in enumerate(entries[:16]):
        if rgb != FW_RGB[want[pen]]:
            out.append("θέση %d: %s, ενώ το παιχνίδι δίνει fw %d = %s"
                       % (pen, rgb, want[pen], FW_RGB[want[pen]]))
        if not name.startswith("pen %d " % pen) or "(fw %d)" % want[pen] not in name:
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
    return out


def main():
    smap, blob = load_map(), load_bin()
    s = smap["palette_fw"]
    base = list(blob[s.off:s.off + s.size])
    s = smap["planet_pens"]
    planets = list(blob[s.off:s.off + s.size])
    asm = open(os.path.join(ASSETS, "sprites.asm"), encoding="utf-8").read()
    m = re.search(r"^PLANETS\s+equ\s+(\d+)\s*;\s*(.+)$", asm, re.M)
    names = [n.strip() for n in m.group(2).split(",")]
    n_pl = len(planets) // 4
    check(int(m.group(1)) == len(names) == n_pl,
          "%d πλανήτες: %s — όσοι και οι σειρές του planet_pens" % (n_pl, ", ".join(names)))

    def palette_of(i):
        fw = list(base)
        for pen, f in zip(TERRAIN_PENS, planets[4 * i:4 * i + 4]):
            fw[pen] = f
        return fw

    # Το palette.gpl δεν λέει όνομα πλανήτη: στηρίζεται στο ότι το palette_fw
    # ΕΙΝΑΙ ο πρώτος πλανήτης.
    check(palette_of(0) == base, "το palette_fw είναι ο %s, το έδαφός του %s"
          % (names[0], planets[0:4]))

    files = {}
    for i, pname in enumerate(names):
        fn = gpl_name(i, names)
        path = os.path.join(ASSETS, fn)
        if not os.path.exists(path):
            check(False, "λείπει το %s" % fn)
            continue
        files[fn] = text = open(path, encoding="utf-8").read()
        bad = problems(text, palette_of(i), planets, pname)
        for b in bad:
            print("   " + b)
        _, _, entries, _, _ = read_gpl(text)
        check(not bad, "%-20s %d pens ίσα με το παιχνίδι στον %s" % (fn, len(entries), pname))
    extra = sorted(set(map(os.path.basename, glob.glob(os.path.join(ASSETS, "palette*.gpl"))))
                   - set(files))
    check(not extra, "κανένα ξεχασμένο .gpl στο assets/" + (": %s" % extra if extra else ""))
    readme = open(os.path.join(ASSETS, "README.md"), encoding="utf-8").read()
    check("palette.gpl" in readme and all(n in readme for n in names[1:]),
          "το assets/README.md τα αναφέρει")

    if len(files) < n_pl:
        print("\nλείπουν αρχεία — τα αρνητικά δεν τρέχουν")
        sys.exit(1)

    # ΑΡΝΗΤΙΚΑ: κάθε αλλοίωση πρέπει να πιαστεί.
    def edit(fn):
        lines = files[fn].split("\n")
        at = {int(re.search(r"\tpen (\d+) ", l).group(1)): i
              for i, l in enumerate(lines) if "\tpen " in l}
        return lines, at

    def swap_rgb(fn, a, b):
        L, at = edit(fn)
        ra, na = L[at[a]].split("\t", 1)
        rb, nb = L[at[b]].split("\t", 1)
        L[at[a]], L[at[b]] = rb + "\t" + na, ra + "\t" + nb
        return "\n".join(L)

    def swap_line(fn, a, b):
        L, at = edit(fn)
        L[at[a]], L[at[b]] = L[at[b]], L[at[a]]
        return "\n".join(L)

    def unname(fn, p):
        L, at = edit(fn)
        L[at[p]] = L[at[p]].split("\t", 1)[0]
        return "\n".join(L)

    def table(fn, row, old, new):
        L, _ = edit(fn)
        k = next(i for i, l in enumerate(L) if l.startswith("#   %s " % row))
        assert old in L[k]
        L[k] = L[k].replace(old, new, 1)
        return "\n".join(L)

    first, last = gpl_name(0, names), gpl_name(n_pl - 1, names)
    second = gpl_name(1, names)
    mutants = [
        (first, 0, "τα χρώματα των pens 11 και 12 ανταλλαγμένα", swap_rgb(first, 11, 12)),
        # ίδιο RGB (fw 3): μόνο το όνομα δείχνει ότι το pen του εδάφους μπήκε
        # στη θέση του εικονιδίου
        (first, 0, "οι γραμμές των pens 11 και 13 ανταλλαγμένες", swap_line(first, 11, 13)),
        # το ίδιο στον τελευταίο πλανήτη, όπου το έδαφος (7) πέφτει πάνω στο 10
        (last, n_pl - 1, "οι γραμμές των pens 7 και 10 ανταλλαγμένες", swap_line(last, 7, 10)),
        (first, 0, "το pen 5 χωρίς όνομα", unname(first, 5)),
        (first, 0, "στον πίνακα, ο %s με fw 15 στο pen 7" % names[1],
         table(first, names[1], "%d " % planets[4], "15 ")),
        (first, 0, "«GIMP palette» με μικρό p",
         files[first].replace("GIMP Palette", "GIMP palette", 1)),
        # το αρχείο του δεύτερου πλανήτη με τα χρώματα του πρώτου
        (second, 1, "το %s με το περιεχόμενο του %s" % (second, first), files[first]),
        (second, 1, "το %s με Name του %s" % (second, names[0]),
         files[second].replace("(%s)" % names[1], "(%s)" % names[0], 1)),
    ]
    for fn, i, label, mutant in mutants:
        assert mutant != files[fn], label
        got = problems(mutant, palette_of(i), planets, names[i])
        check(bool(got), "ΑΡΝΗΤΙΚΟ: %s — %s" % (label, got[0] if got else "ΔΕΝ ΠΙΑΣΤΗΚΕ"))

    print("\n%d/%d" % (RUN[0] - len(FAIL), RUN[0]))
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
