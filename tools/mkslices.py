#!/usr/bin/env python3
"""Cut named sprites out of sprites.bin into build/slices/<name>.bin.

Why not incbin with an offset: rasm evaluates incbin arguments before `equ`
symbols exist, so `incbin "f",SPR_x,SZ_x` loads the WRONG BYTES and does not
warn. Literal offsets would work but go stale the moment a sprite moves.
Slicing here keeps sprites_map.txt as the single source of truth.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sprites import load_map, load_bin, ROOT

OUT = os.path.join(ROOT, "build", "slices")


def main(names):
    smap, blob = load_map(), load_bin()
    os.makedirs(OUT, exist_ok=True)
    if not names:
        names = sorted(smap)
    for n in names:
        s = smap.get(n)
        if s is None:
            sys.exit(f"άγνωστο sprite: {n}")
        data = blob[s.off:s.off + s.size]
        assert len(data) == s.size, f"{n}: κομμένο"
        with open(os.path.join(OUT, n + ".bin"), "wb") as f:
            f.write(data)
        print(f"  {n:<20} #{s.off:04X} {s.size:>6} B")


if __name__ == "__main__":
    main(sys.argv[1:])
