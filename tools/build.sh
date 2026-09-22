#!/usr/bin/env bash
#
# Χτίζει ό,τι παράγεται και τρέχει τις δοκιμές.
#
#   ./tools/build.sh            παράγωγα + δοκιμές
#   ./tools/build.sh --gen      μόνο τα παράγωγα
#
# Τα assets ΔΕΝ χτίζονται εδώ — έρχονται από το CPCArt με το ./sync-assets.sh.

set -euo pipefail
cd "$(dirname "$0")/.."

RASM="${RASM:-$HOME/rasm/rasm.exe}"
[ -x "$RASM" ] || { echo "δεν βρέθηκε ο rasm στο $RASM" >&2; exit 1; }

echo "== παράγωγα από τα assets =="
python3 tools/mkoffsets.py
python3 tools/mkslices.py \
    dome_s_nw dome_m_nw dome_l_nw \
    ring_s_nw ring_m_nw ring_l_nw \
    flip_mode0 >/dev/null
echo "  build/slices/: $(ls build/slices | wc -l) αρχεία"
python3 tools/pack.py >/dev/null
echo "  build/: page2.bin bank6.bin bank7.bin layout.asm layout.txt"

[ "${1:-}" = "--gen" ] && exit 0

echo "== δοκιμές =="
python3 tests/test_pack.py
python3 tests/test_blit.py
python3 tests/test_pack_z80.py
python3 tests/test_tiles.py
python3 tests/test_worldgen.py
python3 tests/test_camera.py
python3 tests/test_routing.py
python3 tests/test_sim.py
python3 tests/test_object.py
