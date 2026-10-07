#!/usr/bin/env python3
"""Η κάμερα και τα ορθογώνια του view.asm, απέναντι σε μοντέλο (DESIGN §8.2).

Τα άλλα τεστ συγκρίνουν τη ΜΝΗΜΗ οθόνης με πλήρη σχεδίαση. Τι ΦΑΙΝΕΤΑΙ το
αποφασίζουν τα R12/R13 του CRTC, και κανένα δεν τα διάβαζε: στο βήμα 61 μια
σελίδα οθόνης λάθος, ένα R12 γραμμένο δύο φορές και ένα R13 με το λάθος byte
πέρασαν όλα τα τεστ. Ούτε ορθογώνιο εκτός κάδρου έστελνε κανείς στο vr_clip.

Τρεις ισχυρισμοί, στο uitest.sna, με τις ρουτίνες καλεσμένες απευθείας:

  1. view_cam, 1.024 κάμερες (μαζί με τις -66..-64 και 45..47 που φτάνει ο
     κέρσορας έξω από τον κόσμο): cam_off, cam_p = ((tx+64)*2 + (ty+64)*80)
     mod 1024 (8 bit το +64), και ο CRTC όπως τον βλέπει ο εξομοιωτής = σελίδα
     3 και cam_off - 80 mod 1024: από το βήμα 83 η οθόνη αρχίζει δύο σειρές
     νωρίτερα, με την πάνω λωρίδα του HUD (§8.1).
  2. vr_clip, 2.400 ορθογώνια σε 8 κάμερες: η τομή με το κάδρο, στήλες και
     σειρές χωριστά. Εκτός κάδρου ή μηδενικό μήκος -> Z και τίποτε άλλο· αλλιώς
     NZ, τα td_* και το clip (4 bytes ανά tile, 16 γραμμές ανά tile).
  3. view_rect και view_add ολόκληρα εκτός κάδρου: Z, οθόνη ανέγγιχτη, και
     κάτω από 1 ms — αλλιώς ξαναζωγραφίζουν όλα τα αντικείμενα (30-85 ms) για
     να βγάλουν την ίδια εικόνα.

Αρνητικά: το R13 να μη γράφεται, και το dk_clamp να λέει NZ εκτός κάδρου.
"""
import os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/vasilhs/cpcemu")

from test_build import build, SNA                                       # noqa: E402

FAIL = []
PROBE = 0x3F10
VIEW_TW, VIEW_TH = 20, 10


def check(ok, msg):
    print(("OK " if ok else "ΛΑΘΟΣ ") + msg)
    if not ok:
        FAIL.append(msg)


def sb(v):
    v &= 0xFF
    return v - 256 if v > 127 else v


def clamp(start, ln, lim):
    """Η τομή του [start, start+ln) με το [0, lim): (αρχή, πλήθος) ή None."""
    lo, hi = max(start, 0), min(start + ln, lim)
    return (lo, hi - lo) if hi > lo else None


def boot(sym, patch=()):
    from cpc import CPC
    m = CPC()
    m.run_frames(60)
    assert m.quickload(SNA)
    n = 0
    while m.peek(sym["READY_FLAG"]) != 0x5A and n < 900:
        m.run_frames(1)
        n += 1
    assert m.peek(sym["READY_FLAG"]) == 0x5A, "δεν ξεκίνησε"
    for at, v in patch:
        m.poke(at, v)
    return m


def call(m, sym, name, step=10):
    """di · ld sp · τράπεζα 1 · call · AF στο #3FF0 · jr $. Γυρίζει (us, F)."""
    code = [0xF3, 0x31, 0x00, 0x01, 0x01, 0xC0, 0x7F, 0xED, 0x49,
            0xCD, sym[name] & 255, sym[name] >> 8, 0xF5, 0xE1, 0x22, 0xF0, 0x3F, 0x18, 0xFE]
    m.write_ram(PROBE, bytes(code))
    m.set_pc(PROBE)
    end, t = PROBE + len(code) - 2, 0
    while not (end <= m.pc <= end + 2):
        m.run_us(step)
        t += step
        assert t < 2_000_000, f"το {name} δεν γύρισε: #{m.pc:04X}"
    return t, m.peek(0x3FF0)


def cams(sym, m):
    edge = [-66, -65, -64, -63, -1, 0, 1, 44, 45, 46, 47, 63, -128, 127]
    rnd = random.Random(61)
    axis = edge + [rnd.randrange(-70, 70) for _ in range(32 - len(edge))]
    for tx in axis:
        for ty in axis:
            m.poke(sym["CAM_TX"], tx & 0xFF)
            m.poke(sym["CAM_TY"], ty & 0xFF)
            call(m, sym, "VIEW_CAM")
            off = (((tx + 64) & 0xFF) * 2 + ((ty + 64) & 0xFF) * 80) & 0x3FF
            got = (m.peek(sym["CAM_OFF"]) | m.peek(sym["CAM_OFF"] + 1) << 8,
                   m.peek(sym["CAM_P"]) | m.peek(sym["CAM_P"] + 1) << 8, m.crtc_screen_addr)
            want = (off, 2 * off, 0x3000 | (off - 80) & 0x3FF)
            if got != want:
                return f"κάμερα ({tx}, {ty}): cam_off, cam_p, CRTC {got}, περίμενα {want}"
    return None


def rects(sym, m):
    rnd = random.Random(61)
    for cam in [(-10, -5), (-64, -64), (44, 54), (-65, -5), (45, 55), (0, 0), (-30, 20),
                (10, -40)]:
        m.poke(sym["CAM_TX"], cam[0] & 0xFF)
        m.poke(sym["CAM_TY"], cam[1] & 0xFF)
        for k in range(300):
            x = cam[0] + rnd.choice([-70, -30, -8, -4, -3, -1, 0, 1, 5, 17, 18, 19, 20, 21, 60])
            y = cam[1] + rnd.choice([-70, -12, -4, -3, -1, 0, 1, 4, 8, 9, 10, 11, 60])
            w = rnd.choice([0, 1, 2, 3, 4, 8, 19, 20, 21, 40, 64])
            h = rnd.choice([0, 1, 2, 3, 4, 8, 9, 10, 11, 40, 64])
            for nm, v in (("VR_TX", x), ("VR_TY", y), ("VR_W", w), ("VR_H", h)):
                m.poke(sym[nm], v & 0xFF)
            before = [m.peek(sym[n]) for n in ("TD_NC", "TD_C0", "TD_R0", "TD_NR")] + \
                list(m.read_ram(sym["CLIP_X0"], 4))
            _, f = call(m, sym, "VR_CLIP")
            got = (bool(f & 0x40), [m.peek(sym[n]) for n in ("TD_NC", "TD_C0", "TD_R0", "TD_NR")]
                   + list(m.read_ram(sym["CLIP_X0"], 4)))
            cx = clamp(sb(x - cam[0]), w, VIEW_TW)
            cy = clamp(sb(y - cam[1]), h, VIEW_TH)
            if cx is None:
                want = (True, before)
            elif cy is None:
                want = (True, [cx[1], cx[0]] + before[2:])
            else:
                want = (False, [cx[1], cx[0], cy[0], cy[1], 4 * cx[0], 4 * sum(cx),
                                16 * cy[0], 16 * sum(cy)])
            if got != want:
                return f"κάμερα {cam}, ορθογώνιο ({x}, {y}) {w}x{h}: Z, td_*, clip " \
                       f"{got}, μοντέλο {want}"
    return None


def outside(sym, m):
    worst = 0
    for name in ("VIEW_RECT", "VIEW_ADD"):
        for (x, y, w, h) in ((-40, 0, 4, 4), (30, 0, 4, 4), (0, -30, 4, 4), (0, 25, 3, 3),
                             (-14, -9, 3, 3), (20, 0, 8, 8), (0, 10, 3, 1)):
            m.poke(sym["CAM_TX"], 0)
            m.poke(sym["CAM_TY"], 0)
            for nm, v in (("VR_TX", x), ("VR_TY", y), ("VR_W", w), ("VR_H", h)):
                m.poke(sym[nm], v & 0xFF)
            scr = m.read_ram(0xC000, 0x4000)
            t, f = call(m, sym, name)
            worst = max(worst, t)
            if not f & 0x40 or m.read_ram(0xC000, 0x4000) != scr or t > 1000:
                return f"{name.lower()} ({x}, {y}) {w}x{h} εκτός κάδρου: Z {bool(f & 0x40)}, " \
                       f"{t} us, οθόνη {'ίδια' if m.read_ram(0xC000, 0x4000) == scr else 'άλλαξε'}"
    return worst


def main():
    sym, _ = build()
    m = boot(sym)
    m.poke(sym["CAM_TX"], 0)
    m.poke(sym["CAM_TY"], 0)
    call(m, sym, "VIEW_DRAW")

    why = cams(sym, m)
    check(why is None, "view_cam σε 1.024 κάμερες: cam_off, cam_p και ο CRTC (σελίδα 3, "
                       "R12/R13) ίσα με τον τύπο του §8.2" + (f" — {why}" if why else ""))
    why = rects(sym, m)
    check(why is None, "vr_clip σε 2.400 ορθογώνια: η τομή με το κάδρο, Z εκτός κάδρου και "
                       "για μήκος 0, τα td_* και το clip ίσα με το μοντέλο"
          + (f" — {why}" if why else ""))
    m.poke(sym["CAM_TX"], 0)
    m.poke(sym["CAM_TY"], 0)
    call(m, sym, "OB_CLIP_FULL")
    call(m, sym, "VIEW_DRAW")
    got = outside(sym, m)
    check(isinstance(got, int), "view_rect και view_add εκτός κάδρου: Z, οθόνη ανέγγιχτη, "
          + (f"το πολύ {got} us" if isinstance(got, int) else got))

    # --- αρνητικά ---
    cam = sym["VIEW_CAM"]
    m2 = boot(sym)
    k = next((k for k in range(80) if m2.peek(cam + k) == 0x0C and m2.peek(cam + k + 1) == 0xED
              and m2.peek(cam + k + 2) == 0x49), None)          # inc c · out (c),c
    check(k is not None and cams(sym, boot(sym, [(cam + k, 0)])) is not None,
          "ΑΡΝΗΤΙΚΟ: με το R13 άγραφτο ο CRTC διαφωνεί με τον τύπο")
    dk = sym["DK_CLAMP"]
    k = next((k for k in range(60) if m2.peek(dk + k) == 0xAF and m2.peek(dk + k + 1) == 0xC9),
             None)                                              # xor a · ret
    check(k is not None and rects(sym, boot(sym, [(dk + k, 0x37)])) is not None,
          "ΑΡΝΗΤΙΚΟ: με το dk_clamp να λέει NZ εκτός κάδρου (scf αντί xor a) το "
          "vr_clip διαφωνεί με το μοντέλο")

    if FAIL:
        print(f"{len(FAIL)} ΛΑΘΗ")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
