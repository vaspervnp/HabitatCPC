#!/usr/bin/env bash
#
# Τραβάει τα γραφικά από το repo CPCArt στο assets/.
#
#   ./sync-assets.sh              αντιγράφει ό,τι υπάρχει ήδη χτισμένο
#   ./sync-assets.sh --regen      τρέχει πρώτα τη γεννήτρια στο CPCArt
#   CPCART=/αλλού ./sync-assets.sh
#
# Τα assets είναι ΠΑΡΑΓΟΜΕΝΑ. Μην τα επεξεργάζεσαι εδώ — το επόμενο sync τα σβήνει.

set -euo pipefail

CPCART="${CPCART:-$HOME/repos/CPCArt}"
SRC="$CPCART/planetbase"
DST="$(cd "$(dirname "$0")" && pwd)/assets"
REGEN=0

for arg in "$@"; do
  case "$arg" in
    --regen) REGEN=1 ;;
    -h|--help) sed -n '2,10p' "$0" | sed 's/^# \?//'; exit 0 ;;
    *) echo "άγνωστη επιλογή: $arg" >&2; exit 2 ;;
  esac
done

[ -d "$SRC" ] || { echo "δεν βρέθηκε το $SRC — όρισε CPCART" >&2; exit 1; }

if [ "$REGEN" = 1 ]; then
  echo "== ξαναχτίζω στο CPCArt =="
  python3 "$SRC/tools/make_all.py"
fi

BIN="$SRC/build/sprites/sprites.bin"
[ -f "$BIN" ] || { echo "λείπει το $BIN — τρέξε με --regen" >&2; exit 1; }

# Αν πειράχτηκαν τα εργαλεία μετά το τελευταίο build, το αντίγραφο θα ήταν παλιό.
if [ -n "$(find "$SRC/tools" -type f -newer "$BIN" -print -quit 2>/dev/null)" ]; then
  echo "ΠΡΟΣΟΧΗ: τα tools/ είναι νεότερα από το build. Τρέξε με --regen." >&2
  exit 1
fi

# Το build ΠΡΕΠΕΙ να είναι --quads nw: με --quads all τα δεδομένα δεν χωράνε στον
# χάρτη μνήμης (DESIGN §4.4). Η γεννήτρια βάζει αυτή την επικεφαλίδα μόνο στο nw.
if ! grep -q "ΜΟΝΟ το τεταρτημόριο nw" "$SRC/build/sprites/sprites.asm"; then
  echo "ΣΦΑΛΜΑ: το build δεν είναι --quads nw." >&2
  echo "Με --quads all τα δεδομένα δεν χωράνε (DESIGN §4.4). Ξαναχτίσε:" >&2
  echo "  python3 $SRC/tools/make_all.py" >&2
  exit 1
fi

echo "== αντιγράφω =="
rm -rf "$DST/aseprite" "$DST/preview"
mkdir -p "$DST/aseprite" "$DST/preview"
cp "$SRC"/sprites/* "$DST/aseprite/"
cp "$SRC"/build/sprites/sprites.asm \
   "$SRC"/build/sprites/sprites.bin \
   "$SRC"/build/sprites/sprites_map.txt "$DST/"
cp "$SRC"/SPRITES.md "$DST/"
# Τα ~260 μεμονωμένα PNG ανά sprite δεν αντιγράφονται: πλεονασμός με τα _sheet.png.
cp "$SRC"/build/sprites/preview/composite*.png \
   "$SRC"/build/sprites/preview/scene.png \
   "$SRC"/build/sprites/preview/planet_*.png \
   "$SRC"/build/sprites/preview/sheet.png "$DST/preview/"

REV="$(git -C "$CPCART" rev-parse --short HEAD)"
DIRTY=""
git -C "$CPCART" diff --quiet HEAD -- planetbase || DIRTY=" (με ακοινοποίητες αλλαγές)"

# Το SPRITES.md γράφτηκε για τη θέση του μέσα στο CPCArt· εδώ οι διαδρομές
# διαφέρουν. Αν κάποιο μοτίβο δεν βρεθεί, σταματάμε: ένας οδηγός αναφοράς με
# σπασμένες διαδρομές είναι χειρότερος από το να λείπει.
python3 - "$DST/SPRITES.md" <<'PY'
import sys
path = sys.argv[1]
text = open(path, encoding="utf-8").read()
edits = [
    ("Τι υπάρχει στο `build/sprites/sprites.bin`, σε τι μορφή, και πώς συντίθεται μια\n"
     "οθόνη. Συνοδεύει το `sprites.asm`· το [README](README.md) περιγράφει τη γεννήτρια.",
     "Τι υπάρχει στο `sprites.bin`, σε τι μορφή, και πώς συντίθεται μια οθόνη.\n"
     "Συνοδεύει το `sprites.asm`· το [README](README.md) λέει από πού προέρχονται\n"
     "αυτά τα αρχεία και πώς ξαναπαράγονται."),
    ("> **Παράγεται μαζί με τα δεδομένα.** Κάθε αλλαγή στα `tools/` αλλάζει και αυτό το\n"
     "> αρχείο. Οι αριθμοί εδώ ισχύουν για build με τις προεπιλογές\n"
     "> (`--quads nw`, σφιχτά τεταρτημόρια).",
     "> **Αντίγραφο.** Το πρωτότυπο ζει στο repo `CPCArt` (`planetbase/SPRITES.md`) και\n"
     "> παράγεται μαζί με τα δεδομένα. Οι αριθμοί εδώ ισχύουν για build με τις\n"
     "> προεπιλογές (`--quads nw`, σφιχτά τεταρτημόρια)."),
]
for old, new in edits:
    if old not in text:
        sys.exit("ΣΦΑΛΜΑ: το SPRITES.md άλλαξε και το sync-assets.sh δεν το αναγνωρίζει.\n"
                 "Δεν βρέθηκε:\n---\n%s\n---\nΕνημέρωσε τα edits στο sync-assets.sh." % old)
    text = text.replace(old, new)
open(path, "w", encoding="utf-8").write(text)
PY

cat > "$DST/README.md" <<MD
# assets — γραφικά Mode 0

Τα γραφικά του παιχνιδιού για Amstrad CPC 6128, Mode 0. **Παράγονται αυτόματα** —
μην τα επεξεργάζεσαι εδώ, οι αλλαγές θα χαθούν στο επόμενο \`sync-assets.sh\`.

| | |
|---|---|
| Πηγή | repo \`CPCArt\`, φάκελος \`planetbase/\` |
| Έκδοση | \`$REV\`$DIRTY |
| Συγχρονίστηκε | $(date +%Y-%m-%d) |

\`\`\`bash
./sync-assets.sh --regen      # ξαναχτίζει στο CPCArt και τραβάει εδώ
\`\`\`

## Τι υπάρχει εδώ

| Αρχείο | Περιεχόμενο |
|---|---|
| [\`SPRITES.md\`](SPRITES.md) | **ο οδηγός: κάθε sprite, οι δείκτες, και πώς συντίθεται μια οθόνη** |
| \`sprites.asm\` | πηγαίος κώδικας RASM — αυτό κάνεις include |
| \`sprites.bin\` | τα ίδια bytes σε raw binary, αν προτιμάς φόρτωση από δίσκο |
| \`sprites_map.txt\` | offset και μέγεθος κάθε sprite μέσα στο \`.bin\` |
| \`aseprite/\` | τα spritemaps (\`.aseprite\`) και οι εξαγωγές τους (\`_sheet.png\`, \`_sheet.json\`) |
| \`preview/\` | \`scene.png\` (θόλος, διάδρομος και αεροθάλαμος σε έδαφος), \`planet_*.png\`, \`composite_*.png\`, \`sheet.png\` |

Στο \`preview/\` δεν αντιγράφονται τα ~260 μεμονωμένα PNG ανά sprite — είναι
πλεονασμός με τα \`_sheet.png\` και ξαναπαράγονται όποτε χρειαστεί.

## Το ελάχιστο που πρέπει να ξέρεις

- Φόρτωσε το μπλοκ σε διεύθυνση **πολλαπλάσιο του 256** (το \`flip_mode0\` θέλει σελίδα).
- Τα δεδομένα είναι **γραμμικά**, όχι στη διάταξη της μνήμης οθόνης.
- Χρειάζονται **δύο** ρουτίνες blit: μία με μάσκα και μία αδιαφανής.
- Οι σταθερές \`*_W\` είναι bytes **δεδομένων** ανά γραμμή· σε sprite με μάσκα η
  γραμμή καταλαμβάνει **2× αυτό**.

Τα υπόλοιπα στο [\`SPRITES.md\`](SPRITES.md).
MD

echo "== έτοιμο: CPCArt @ $REV$DIRTY =="
cd "$(dirname "$DST")"
if git diff --quiet -- assets && git diff --cached --quiet -- assets && \
   [ -z "$(git ls-files --others --exclude-standard assets)" ]; then
  echo "καμία αλλαγή."
else
  git status --short -- assets
  echo
  echo "για commit:  git add assets && git commit -m 'assets: sync από CPCArt @ $REV'"
fi
