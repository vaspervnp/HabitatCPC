#!/usr/bin/env python3
"""Το πέρασμα εδάφους: ορθότητα σε τέσσερις θέσεις κάμερας, και κόστος.

Η αναφορά υλοποιεί το autotiling από το SPRITES.md §3 — τέσσερις ορθογώνιοι
γείτονες, bit όταν είναι ΙΔΙΑΣ ΟΙΚΟΓΕΝΕΙΑΣ, το βαθύ νερό μετράει ως νερό.

Οι θέσεις κάμερας διαλέχτηκαν για να σπάσουν πράγματα, όχι για να δείχνουν
όμορφες: η γωνία του κόσμου βγάζει τους γείτονες εκτός ορίων, που είναι η μόνη
περίπτωση όπου η μηχανή δεν κάνει απλή αριθμητική.

ΤΡΙΑ ΚΕΝΑ, από τα σκόπιμα λάθη του βήματος 56 — όλα παλαιότερα από αυτό:
  * Η «αντίθετη γωνία» ήταν η (44, 53), που με δέκα σειρές σταματά στο y = 62:
    η τελευταία σειρά του κόσμου δεν ζωγραφιζόταν ποτέ, και ένα ta_same που
    έβγαζε το #7Fxx εκτός κόσμου περνούσε. Ούτε η (44, 54) το πιάνει: ο κόσμος
    της δοκιμής δεν έχει εκεί autotiled έδαφος δίπλα σε άλλη οικογένεια.
    Γράφεται λοιπόν μια λίμνη στις σειρές 61-63.
  * Ο κόσμος της δοκιμής δεν έχει πουθενά βουνό που να αγγίζει νερό, δηλαδή
    δύο autotiled οικογένειες που διαφέρουν κατά 1 (3 και 4). Μια σύγκριση
    οικογενειών που έλεγε «ίσες» και για διαφορά 1 περνούσε. Εδώ γράφονται
    βουνά στην ακτή της λίμνης — στον κόσμο του εξομοιωτή ΚΑΙ στης αναφοράς.
  * Το cam_p ήταν πάντα 0, οπότε καμία σειρά δεν περνούσε το τέλος του
    δαχτυλιδιού των 2.048 bytes: το «#C8 -> #C0» ανάμεσα σε δύο tiles δεν το
    έλεγχε κανείς, ούτε πριν (and #C7) ούτε μετά.
"""
import copy, os, subprocess, sys

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
    (-10, -5,  "λίμνη με βαθύ κέντρο και βουνό με φλέβα", {}),
    (-64, -64, "ΓΩΝΙΑ ΚΟΣΜΟΥ — οι γείτονες βγαίνουν εκτός και στους δύο άξονες", {}),
    (44,  54,  "αντίθετη γωνία — το τελευταίο ορατό tile είναι το +63,+63", {}),
    (-16,  4,  "κρατήρας και θεμέλια — κλάσεις με 2 παραλλαγές, όχι 4", {}),
    (44,  54,  "ΛΙΜΝΗ ΣΤΗ ΝΟΤΙΑ ΑΚΡΗ — autotile στις σειρές 62-63, στο #7Fxx",
     {"lake": (50, 61, 4, 3)}),
    (-10, -5,  "ΒΟΥΝΟ ΣΤΗΝ ΑΚΤΗ — autotiled οικογένειες που διαφέρουν κατά 1",
     {"shore": True}),
    (-10, -5,  "ΤΟ ΔΑΧΤΥΛΙΔΙ — cam_p 2008, κάθε σειρά τυλίγει στη στήλη 10",
     {"cam_p": 2008}),
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


def shore(plane, cam_tx, cam_ty):
    """Τα tiles του κάδρου που δεν είναι νερό αλλά αγγίζουν νερό: εκεί μπαίνει
    βουνό, ένα δαχτυλίδι γύρω από τη λίμνη — βουνό με βουνό ΚΑΙ βουνό με νερό."""
    wet = lambda tx, ty: world.FAMILY[world.cls_of(plane.get(tx, ty))] == world.WATER
    return [(tx, ty)
            for ty in range(cam_ty, cam_ty + VIEW_TH)
            for tx in range(cam_tx, cam_tx + VIEW_TW)
            if not wet(tx, ty) and any(wet(tx + dx, ty + dy) for dx, dy in
                                       ((1, 0), (-1, 0), (0, 1), (0, -1)))]


def main():
    sym = build()
    smap, blob = load_map(), load_bin()
    variants = list(blob[smap["tile_variants"].off:smap["tile_variants"].off + 8])
    plane = world.test_world()

    from cpc import CPC
    fails = 0
    frames_used = None

    import cpc
    for cam_tx, cam_ty, why, opts in CAMERAS:
        m = CPC()
        m.run_frames(60)
        assert m.quickload(SNA, start=False), "quickload απέτυχε"
        m.poke(sym["CAM_TX"], cam_tx & 0xFF)
        m.poke(sym["CAM_TY"], cam_ty & 0xFF)
        p = opts.get("cam_p", 0)
        m.poke(sym["CAM_P"], p & 0xFF)
        m.poke(sym["CAM_P"] + 1, p >> 8)
        pl = plane
        if opts.get("shore") or opts.get("lake"):
            # ΣΤΟΥΣ ΔΥΟ ΚΟΣΜΟΥΣ: του εξομοιωτή (τράπεζα 4) και της αναφοράς.
            pl = copy.deepcopy(plane)
            b4 = cpc._lib.cpcemu_ram_ptr(m._h, 4)
            if opts.get("shore"):
                spots, cls = shore(pl, cam_tx, cam_ty), world.MOUNTAIN
                assert len(spots) >= 3, f"μόνο {len(spots)} σημεία ακτής στο κάδρο"
                why += f" ({len(spots)} βουνά)"
            else:
                x0, y0, w, h = opts["lake"]
                spots = [(x0 + i, y0 + j) for j in range(h) for i in range(w)]
                cls = world.WATER
            for tx, ty in spots:
                pl.set(tx, ty, world.byte(cls))
                b4[world.index(tx, ty)] = world.byte(cls)
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
        ref = reference(pl, cam_tx, cam_ty, smap, blob, variants)
        bad = []
        for y in range(SCR_H):
            base = (y & 7) * 0x800
            got = bytes(ram[base + (((y >> 3) * SCR_W + x + p) & 0x7FF)]
                        for x in range(SCR_W))
            want = bytes(ref.buf[y * SCR_W:(y + 1) * SCR_W])
            if got != want:
                bad += [(x, y) for x in range(SCR_W) if got[x] != want[x]]

        tag = f"κάμερα ({cam_tx:>4},{cam_ty:>4})"
        if bad:
            fails += 1
            tiles = sorted({(x // 4, y // 16) for x, y in bad})
            print(f"ΑΠΟΤΥΧΙΑ {tag}: {len(bad)} bytes σε {len(tiles)} tiles — {why}")
            for tcol, trow in tiles[:6]:
                tx, ty = cam_tx + tcol, cam_ty + trow
                b = pl.get(tx, ty)
                print(f"    tile ({tx:>4},{ty:>4}) κλάση "
                      f"{world.CLASS_NAMES[world.cls_of(b)]:<10} "
                      f"παραλλαγή {pl.variant(tx, ty, variants):>2} "
                      f"autotile {pl.autotile(tx, ty):>2}")
        else:
            print(f"OK {tag}  {why}")
            # Το DONE_FLAG ανεβαίνει όταν γραφτεί και το ΤΕΛΕΥΤΑΙΟ tile· το
            # framebuffer είναι το καρέ που η δέσμη ίσως πέρασε από εκεί πριν.
            # Δύο ακόμη καρέ (ο βρόχος κρέμεται), και το PNG είναι η RAM που
            # μόλις ελέγχθηκε — αλλιώς άλλαζε με κάθε αλλαγή στον χρονισμό
            # (βήμα 42: το tile_src, και το κάτω δεξιά tile στο (-10,-5)).
            # Οι δύο τελευταίες ξαναζωγραφίζουν το (-10,-5): δικό τους PNG
            # θα έγραφε πάνω στο κανονικό, και το δαχτυλίδι φαίνεται μόνο με
            # το offset του CRTC, που εδώ δεν στήνεται.
            if not opts:
                m.run_frames(2)
                m.screenshot(os.path.join(HERE, "golden",
                                          f"tiles_{cam_tx}_{cam_ty}.png"), aspect=True)

    # --- κόστος ---
    tiles = VIEW_TW * VIEW_TH
    us = frames_used * 19968 / REPS
    print(f"\nκόστος: {frames_used} frames για {REPS} περάσματα "
          f"-> {us/1000:.1f} ms ανά πλήρες κάδρο = {us/tiles:.0f} us ανά tile")
    print(f"  πλήρες κάδρο {us/19968:.1f} frames · μία στήλη "
          f"{us/tiles*VIEW_TH/1000:.1f} ms · μία σειρά {us/tiles*VIEW_TW/1000:.1f} ms")
    # Το DESIGN §2.2 καταγράφει 889 us μετρημένα (968 ως το βήμα 55). Αν αυτό
    # αλλάξει — προς τα πάνω ή προς τα κάτω — το έγγραφο θέλει ενημέρωση, όχι
    # σιωπή.
    per = us / tiles
    if not 840 <= per <= 940:
        print(f"  ΑΠΟΤΥΧΙΑ: το DESIGN §2.2 λέει 889 us ανά tile, μετρήθηκαν {per:.0f}."
              f"\n  Αν η αλλαγή είναι σκόπιμη, ενημέρωσε το §2.2 και αυτό το όριο.")
        fails += 1
    else:
        print(f"  (το DESIGN §2.2 καταγράφει 889 us ανά tile — συμφωνεί)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
