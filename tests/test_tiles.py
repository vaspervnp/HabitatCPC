#!/usr/bin/env python3
"""Το πέρασμα εδάφους: ορθότητα σε τέσσερις θέσεις κάμερας, και κόστος.

Η αναφορά υλοποιεί το autotiling από το SPRITES.md §3 — τέσσερις ορθογώνιοι
γείτονες, bit όταν είναι ΙΔΙΑΣ ΟΙΚΟΓΕΝΕΙΑΣ, το βαθύ νερό μετράει ως νερό.

Οι θέσεις κάμερας διαλέχτηκαν για να σπάσουν πράγματα, όχι για να δείχνουν
όμορφες: η γωνία του κόσμου βγάζει τους γείτονες εκτός ορίων, που είναι η μόνη
περίπτωση όπου η μηχανή δεν κάνει απλή αριθμητική.
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")

from sprites import load_map, load_bin                                  # noqa: E402
from refrender import Canvas, SCR_W, SCR_H                              # noqa: E402
import world                                                            # noqa: E402

RASM = os.path.expanduser("~/rasm/rasm.exe")
SNA = os.path.join(ROOT, "build", "tiletest.sna")
REPS = 10                    # πρέπει να ταιριάζει με το tiletest.asm
VIEW_TW, VIEW_TH = 20, 10

CAMERAS = [
    (-10, -5,  "λίμνη με βαθύ κέντρο και βουνό με φλέβα"),
    (-64, -64, "ΓΩΝΙΑ ΚΟΣΜΟΥ — οι γείτονες βγαίνουν εκτός και στους δύο άξονες"),
    (44,  53,  "αντίθετη γωνία — το τελευταίο ορατό tile είναι το +63,+63"),
    (-16,  4,  "κρατήρας και θεμέλια — κλάσεις με 2 παραλλαγές, όχι 4"),
]


def build():
    for tool in ("mkoffsets.py", "pack.py", "mkworld.py"):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", tool)],
                           capture_output=True, text=True)
        if r.returncode:
            sys.exit(f"{tool} απέτυχε:\n{r.stdout}{r.stderr}")
    r = subprocess.run([RASM, "tiletest.asm", "-oi", SNA, "-v2", "-s", "-eo"],
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


def reference(plane, cam_tx, cam_ty, smap, blob, variants):
    c = Canvas()

    def rows(name):
        s = smap[name]
        d = blob[s.off:s.off + s.size]
        return [d[y * s.stride:(y + 1) * s.stride] for y in range(s.h)]

    for row in range(VIEW_TH):
        ty = cam_ty + row
        for col in range(VIEW_TW):
            tx = cam_tx + col
            b = plane.get(tx, ty)
            cls = world.cls_of(b)
            var = plane.variant(tx, ty, variants)
            c.opaque(rows(f"tile_{world.CLASS_NAMES[cls]}_{var}"), col * 4, row * 16)
            if cls == world.MOUNTAIN and world.res_of(b):
                c.masked(rows(f"ore_overlay_{world.decor_of(b) & 1}"),
                         col * 4, row * 16)
    return c


def main():
    sym = build()
    smap, blob = load_map(), load_bin()
    variants = list(blob[smap["tile_variants"].off:smap["tile_variants"].off + 8])
    plane = world.test_world()

    from cpc import CPC
    fails = 0
    frames_used = None

    for cam_tx, cam_ty, why in CAMERAS:
        m = CPC()
        m.run_frames(60)
        assert m.quickload(SNA, start=False), "quickload απέτυχε"
        m.poke(sym["CAM_TX"], cam_tx & 0xFF)
        m.poke(sym["CAM_TY"], cam_ty & 0xFF)
        m.set_pc(sym["START"])

        n = 0
        while m.peek(sym["DONE_FLAG"]) != 0x5A and n < 400:
            m.run_frames(1)
            n += 1
        assert m.peek(sym["DONE_FLAG"]) == 0x5A, \
            f"δεν τερμάτισε σε {n} frames, PC=#{m.pc:04X}"
        if frames_used is None:
            frames_used = n

        ram = m.read_ram(0xC000, 0x4000)
        ref = reference(plane, cam_tx, cam_ty, smap, blob, variants)
        bad = []
        for y in range(SCR_H):
            off = (y & 7) * 0x800 + (y >> 3) * SCR_W
            got, want = ram[off:off + SCR_W], bytes(ref.buf[y * SCR_W:(y + 1) * SCR_W])
            if got != want:
                bad += [(x, y) for x in range(SCR_W) if got[x] != want[x]]

        tag = f"κάμερα ({cam_tx:>4},{cam_ty:>4})"
        if bad:
            fails += 1
            tiles = sorted({(x // 4, y // 16) for x, y in bad})
            print(f"ΑΠΟΤΥΧΙΑ {tag}: {len(bad)} bytes σε {len(tiles)} tiles — {why}")
            for tcol, trow in tiles[:6]:
                tx, ty = cam_tx + tcol, cam_ty + trow
                b = plane.get(tx, ty)
                print(f"    tile ({tx:>4},{ty:>4}) κλάση "
                      f"{world.CLASS_NAMES[world.cls_of(b)]:<10} "
                      f"παραλλαγή {plane.variant(tx, ty, variants):>2} "
                      f"autotile {plane.autotile(tx, ty):>2}")
        else:
            print(f"OK {tag}  {why}")
            m.screenshot(os.path.join(HERE, "golden",
                                      f"tiles_{cam_tx}_{cam_ty}.png"), aspect=True)

    # --- κόστος ---
    tiles = VIEW_TW * VIEW_TH
    us = frames_used * 19968 / REPS
    print(f"\nκόστος: {frames_used} frames για {REPS} περάσματα "
          f"-> {us/1000:.1f} ms ανά πλήρες κάδρο = {us/tiles:.0f} us ανά tile")
    print(f"  πλήρες κάδρο {us/19968:.1f} frames · μία στήλη "
          f"{us/tiles*VIEW_TH/1000:.1f} ms · μία σειρά {us/tiles*VIEW_TW/1000:.1f} ms")
    # Το DESIGN §2.2 καταγράφει 929 us μετρημένα. Αν αυτό αλλάξει — προς τα πάνω
    # ή προς τα κάτω — το έγγραφο θέλει ενημέρωση, όχι σιωπή.
    per = us / tiles
    if not 880 <= per <= 980:
        print(f"  ΑΠΟΤΥΧΙΑ: το DESIGN §2.2 λέει 929 us ανά tile, μετρήθηκαν {per:.0f}."
              f"\n  Αν η αλλαγή είναι σκόπιμη, ενημέρωσε το §2.2 και αυτό το όριο.")
        fails += 1
    else:
        print(f"  (το DESIGN §2.2 καταγράφει 929 us ανά tile — συμφωνεί)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
