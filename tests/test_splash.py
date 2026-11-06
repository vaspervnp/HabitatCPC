#!/usr/bin/env python3
"""Οι δύο οθόνες πριν από το μενού (βήμα 194, DESIGN §13.6).

Ο παίκτης ζήτησε το revive8b.scr των άλλων παιχνιδιών και μία ακόμη οθόνη,
και διάλεξε: πρώτα το REVIVE8BIT, μετά του Habitat, μετά το μενού, η καθεμιά
10 δευτερόλεπτα ή ως το SPACE· του Habitat από τα γραφικά του παιχνιδιού.

  ΑΡΧΕΙΑ   το build/revive.bin είναι το art/revive8b.scr (το αρχείο του
           REVIVE8BIT, με το md5 του) και τα 16 χρώματα του art/revive8b.txt·
           το build/splash.bin ξαναβγαίνει ίδιο από το tools/splash.py, με τα
           χρώματα της ερήμου, και έχει πάνω στον κόσμο τον τίτλο και την
           αποικία (αρνητικό: ο κόσμος μόνος του).
  ΔΙΣΚΟΣ   RUN"HABITAT: η πρώτη οθόνη στη μνήμη της οθόνης byte προς byte με
           το revive8b.scr, και στο framebuffer του εξομοιωτή με τα χρώματά της
           (αρνητικό: με της άλλης)· μένει 10 s χωρίς πλήκτρο· η δεύτερη byte
           προς byte με του Habitat και με τα δικά της χρώματα· ένα SPACE
           κρατημένο από την πρώτη δεν την προσπερνά, ένα καινούργιο ναι· μετά
           το μενού.
  ΑΡΝΗΤΙΚΑ στον κώδικα: το mw_spon να ξεκινά από 2 (ένα SPACE κρατημένο
           προσπερνά και τη δεύτερη)· nop αντί για halt στην αναμονή (η οθόνη
           δεν κρατά 10 s).
"""
import hashlib, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import menuread as MR                                    # noqa: E402
import menuworld as MW                                   # noqa: E402
import mkdsk                                             # noqa: E402
import splash                                            # noqa: E402

DSK = os.path.join(ROOT, "build", "habitat.dsk")
FAIL = []
REVIVE_MD5 = "9eff5c07b0ddc280eaf850d328998ef4"
REVIVE_INKS = [0, 13, 26, 15, 25, 10, 3, 1, 11, 23, 6, 24, 20, 16, 12, 4]


def check(ok, msg):
    print(("OK " if ok else "ΛΑΘΟΣ ") + msg)
    if not ok:
        FAIL.append(msg)


def build():
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "mkdsk.py")],
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit("mkdsk.py απέτυχε:\n" + r.stdout + r.stderr)


def fw_to_hw():
    """Ο πίνακας firmware -> hardware του src/hw.asm (fw_to_hw)."""
    src = open(os.path.join(ROOT, "src", "hw.asm"), encoding="utf-8").read()
    out = []
    for line in src[src.index("fw_to_hw:"):].splitlines()[1:4]:
        out += [int(v.strip().lstrip("#"), 16) for v in line.split("db")[1].split(";")[0].split(",")]
    return out


def colours(m, palettes):
    """Για κάθε παλέτα (16 χρώματα firmware), πόσα pixels του framebuffer
    διαφέρουν από ό,τι θα έδειχνε η μνήμη της οθόνης μ' αυτήν — όπως το
    colours() του tests/test_disc.py. None αν η εικόνα δεν βρέθηκε."""
    hw = fw_to_hw()
    pens = m.decode_screen_ram(mode=0)
    fb = m.framebuffer()

    def image(pal):
        pen_hw = [hw[c] for c in pal]
        return [bytes(pen_hw[p] for p in row for _ in range(4)) for row in pens]

    def bad(img, x0, y0):
        return sum(sum(a != b for a, b in zip(fb[(y0 + r) * 1024 + x0:(y0 + r) * 1024 + x0 + 640],
                                              img[r])) for r in range(200))
    want = image(palettes[0])
    y = max(range(200), key=lambda r: sum(a != b for a, b in zip(want[r], want[r][1:])))
    at = [(fb[fy * 1024:(fy + 1) * 1024].find(want[y]), fy - y)
          for fy in range(y, len(fb) // 1024 - 200 + y + 1)]
    at = [(x0, y0) for x0, y0 in at if 0 <= x0 <= 1024 - 640]
    if not at:
        return None
    x0, y0 = min(at, key=lambda p: bad(want, *p))
    return [bad(image(p), x0, y0) for p in palettes]


def files():
    art = open(os.path.join(ROOT, "art", "revive8b.scr"), "rb").read()
    rev = open(os.path.join(ROOT, "build", "revive.bin"), "rb").read()
    check(hashlib.md5(art).hexdigest() == REVIVE_MD5 and rev == art + bytes(REVIVE_INKS),
          f"ΑΡΧΕΙΑ: το revive.bin είναι το revive8b.scr του REVIVE8BIT (md5 "
          f"{hashlib.md5(art).hexdigest()[:8]}) με τα 16 χρώματα του revive8b.txt")
    spl = open(os.path.join(ROOT, "build", "splash.bin"), "rb").read()
    cv, pal = splash.habitat()
    check(spl == splash.image(cv, pal) and list(spl[0x4000:]) == list(MW.palette(splash.PLANET)),
          f"ΑΡΧΕΙΑ: το splash.bin ξαναβγαίνει ίδιο από το tools/splash.py, με τα "
          f"χρώματα του πλανήτη {splash.PLANET} ({len(spl)} bytes)")
    # ο κόσμος μόνος του: ό,τι διαφέρει είναι ο τίτλος και η αποικία
    import worldgen_ref
    from refrender import Canvas
    plane = worldgen_ref.generate(MW.seeds(splash.PLANET)[splash.WORLD], splash.PLANET)
    tx, ty = MW.window(plane)
    bare = Canvas()
    MW.draw_world(bare, plane, tx, ty)
    title = sum(1 for y in range(6, 6 + 32) for x in range(80)
                if cv[x, y] == MW.TITLE_INK)
    objs = sum(1 for a, b in zip(cv.buf, bare.buf) if a != b)
    check(title > 200 and objs > 4000,
          f"ΑΡΧΕΙΑ: πάνω στον κόσμο ο τίτλος ({title} bytes κίτρινα) και η "
          f"αποικία με τα υπόλοιπα ({objs} bytes διαφορετικά από τον κόσμο μόνο του)")
    return art, spl


def boot(disc):
    from cpc import CPC
    m = CPC()
    m.run_frames(300)
    m.set_joystick_type(0)
    m.insert_disc(disc)
    m.type_text('|disc\n', hold_frames=4, gap_frames=8)
    m.run_frames(60)
    m.type_text('run"habitat\n', hold_frames=4, gap_frames=8)
    return m


def until(m, cond, limit):
    for f in range(limit):
        if cond():
            return f
        m.run_frames(1)
    return None


def screens(art, spl):
    from cpc import KEY_SPACE
    bs = MR.syms(ROOT)
    m = boot(DSK)
    f1 = until(m, lambda: MR.spon(m, bs) == 2, 2000)
    m.run_frames(3)
    scr = m.read_ram(0xC000, 0x4000)
    c = colours(m, [REVIVE_INKS, list(spl[0x4000:])]) if f1 is not None else None
    check(f1 is not None and scr == art and c is not None and c[0] == 0 and c[1] > 0,
          f"ΔΙΣΚΟΣ: η πρώτη οθόνη {f1} frames μετά το RUN, byte προς byte το "
          f"revive8b.scr, και στον εξομοιωτή με τα χρώματά της ({c[0] if c else '-'} "
          f"pixels λάθος· με της άλλης {c[1] if c else '-'})")
    held = until(m, lambda: MR.spon(m, bs) == 0, 900)
    check(held is not None and 475 <= held + 3 <= 550,
          f"ΔΙΣΚΟΣ: χωρίς πλήκτρο μένει {held + 3 if held is not None else '-'} "
          f"frames (10 s = 500)")
    f2 = until(m, lambda: MR.spon(m, bs) == 2, 600)
    m.run_frames(3)
    scr = m.read_ram(0xC000, 0x4000)
    c = colours(m, [list(spl[0x4000:]), REVIVE_INKS]) if f2 is not None else None
    check(f2 is not None and scr == spl[:0x4000] and c is not None and c[0] == 0 and c[1] > 0,
          f"ΔΙΣΚΟΣ: η δεύτερη {f2} frames μετά, byte προς byte του Habitat, με τα "
          f"χρώματά της ({c[0] if c else '-'} pixels λάθος· με του REVIVE8BIT "
          f"{c[1] if c else '-'})")
    MR.skip(m)
    gone = until(m, lambda: MR.spon(m, bs) == 0, 20)
    w = MR.wait(m, bs)
    check(gone is not None and w is not None,
          f"ΔΙΣΚΟΣ: ένα SPACE την προσπερνά ({gone} frames), και το μενού έρχεται "
          f"{w} frames μετά")
    del m
    return bs


def held_space(disc, art):
    """Ενα SPACE στην πρώτη οθόνη, κρατημένο 150 frames: η πρώτη φεύγει, η
    δεύτερη μένει (mw_spon 1) ως να αφεθεί. Γυρίζει (φεύγει η πρώτη, η
    δεύτερη μένει 150 frames με το SPACE κάτω, φεύγει με ένα καινούργιο). Η
    πρώτη αναγνωρίζεται και από την εικόνα: πριν φορτωθεί το μενού, στη θέση
    του mw_spon είναι ό,τι άφησε το BASIC."""
    from cpc import KEY_SPACE
    bs = MR.syms(ROOT)
    m = boot(disc)
    first = until(m, lambda: MR.spon(m, bs) == 2
                  and m.read_ram(0xC000, 64) == art[:64], 2000) is not None
    m.key_down(KEY_SPACE)
    left = until(m, lambda: MR.spon(m, bs) == 0, 20) is not None
    shown = until(m, lambda: MR.spon(m, bs) == 1, 300) is not None
    stays = shown and all(not m.run_frames(1) and MR.spon(m, bs) == 1 for _ in range(150))
    m.key_up(KEY_SPACE)
    up = until(m, lambda: MR.spon(m, bs) == 2, 20) is not None
    MR.skip(m)
    gone = up and until(m, lambda: MR.spon(m, bs) == 0, 20) is not None
    del m
    return first and left, stays, gone


def main():
    build()
    art, spl = files()
    bs = screens(art, spl)
    ok, stays, gone = held_space(DSK, art)
    check(ok and stays and gone,
          f"ΔΙΣΚΟΣ: ένα SPACE κρατημένο από την πρώτη δεν προσπερνά τη δεύτερη "
          f"(μένει 150 frames: {stays}), ένα καινούργιο ναι ({gone})")

    # --- αρνητικά: το MENU.BIN αλλαγμένο, ξανασυμπιεσμένο (mkdsk.variant) ----
    menu = open(os.path.join(ROOT, "build", "menu.bin"), "rb").read()
    org = MW.geom()["MW_ORG"]

    def at(label, pat, span=80):
        base = bs[label] - org
        k = menu[base:base + span].find(bytes(pat))
        assert k >= 0, f"δεν βρέθηκε το {pat} στο {label}"
        return base + k

    on = bs["MW_SPON"]
    # ld hl,mw_spon · ld (hl),1  ->  ld (hl),2
    k = at("MW_SCREEN", [0x21, on & 255, on >> 8, 0x36, 0x01])
    bad = bytearray(menu)
    bad[k + 4] = 2
    path = mkdsk.variant(os.path.join(ROOT, "build", "splash_neg.dsk"), "MENU.BIN", bytes(bad))
    ok, stays, gone = held_space(path, art)
    check(ok and not stays,
          f"ΑΡΝΗΤΙΚΟ: με το mw_spon να ξεκινά από 2, το SPACE κρατημένο από την "
          f"πρώτη προσπερνά και τη δεύτερη (έμεινε 150 frames: {stays})")
    # halt -> nop στην αναμονή
    k = at("MSP_LP", [0xC5, 0x76])
    bad = bytearray(menu)
    bad[k + 1] = 0
    path = mkdsk.variant(os.path.join(ROOT, "build", "splash_neg.dsk"), "MENU.BIN", bytes(bad))
    m = boot(path)
    first = until(m, lambda: MR.spon(m, bs) in (1, 2), 2000)
    held = until(m, lambda: MR.spon(m, bs) == 0, 900) if first is not None else None
    del m
    os.unlink(path)
    check(first is not None and held is not None and held < 400,
          f"ΑΡΝΗΤΙΚΟ: με nop αντί για halt η πρώτη οθόνη μένει "
          f"{held if held is not None else '-'} frames αντί για 500")
    print()
    print("ΟΛΑ ΚΑΛΑ" if not FAIL else f"{len(FAIL)} ΑΠΟΤΥΧΙΕΣ")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
