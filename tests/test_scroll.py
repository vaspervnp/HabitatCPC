#!/usr/bin/env python3
"""Σκρολάρισμα: ισοδυναμία με πλήρη σχεδίαση, και το πραγματικό του κόστος.

Ο ΙΣΧΥΡΙΣΜΟΣ (DESIGN §8.2): το σκρολάρισμα είναι δύο εγγραφές στον CRTC και
μία λωρίδα επανασχεδίασης· η υπόλοιπη εικόνα δεν αγγίζεται. Ο έλεγχος είναι η
ισοδυναμία: ξεκίνα k tiles πιο πίσω, σχεδίασε πλήρως, σκρολάρισε k φορές, και
η μνήμη οθόνης πρέπει να είναι ΤΑΥΤΟΣΗΜΗ με πλήρη σχεδίαση στο τέλος.

Αν κάτι λείπει από τη λωρίδα — ένα τεταρτημόριο, μια πόρτα, ένα φυτό — η
σύγκριση το δείχνει· το μάτι δεν το δείχνει, γιατί η προηγούμενη εικόνα είναι
σχεδόν σωστή.

Ο ΧΡΟΝΟΣ ΣΕ us (βήμα 108): η πλήρης σχεδίαση στο BASE και ένα βήμα προς κάθε
κατεύθυνση ως εκεί, με ταβάνια. Οι θόλοι και οι δακτύλιοι ζωγραφίζουν από το
108 μόνο τα διαστήματα που έχουν κάτι (src/span.asm). Αρνητικό: το ob_shell
χωρίς τον πίνακα ξεπερνά τα ταβάνια.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/vasilhs/cpcemu")

from test_object import build                                           # noqa: E402

SNA = os.path.join(ROOT, "build", "objtest.sna")
DIRS = {0: (0, -1, "βορράς"), 1: (1, 0, "ανατολή"),
        2: (0, 1, "νότος"), 3: (-1, 0, "δύση")}
BASE = (-18, -3)          # το τύλιγμα του δαχτυλιδιού πέφτει μέσα στην εικόνα
OPEN = (30, 30)           # μακριά από την αποικία: μόνο έδαφος
STEPS = 5

# Μετρημένα όρια, όχι ευχές. Το §8.2 έλεγε 0,9 frames ανά βήμα μετρώντας ΜΟΝΟ
# το έδαφος· ένα βήμα μέσα στη βάση ξαναζωγραφίζει και ό,τι πατάει τη λωρίδα.
LIMIT_OPEN = 4.0
LIMIT_BASE = 10.0

# ΤΟ ΒΗΜΑ 108 ΣΕ us, όχι σε frames: η πλήρης σχεδίαση στο BASE και ένα βήμα
# προς κάθε κατεύθυνση ως εκεί. Τα θόλοι και οι δακτύλιοι ζωγραφίζουν μόνο τα
# διαστήματά τους (src/span.asm), και ο βρόχος του ob_blit έχει ό,τι δεν
# αλλάζει μέσα στις εντολές του.
EXACT_CEIL = {"πλήρης": 520_000, "βορράς": 76_000, "ανατολή": 14_500,
              "νότος": 24_500, "δύση": 76_000}
EXACT_WAS = {"πλήρης": 642_284, "βορράς": 93_328, "ανατολή": 14_412,
             "νότος": 24_448, "δύση": 90_604}


def main():
    sym = build()
    from cpc import CPC

    def full(tx, ty):
        m = CPC()
        m.run_frames(60)
        assert m.quickload(SNA, start=False)
        m.poke(sym["CAM_TX"], tx & 0xFF)
        m.poke(sym["CAM_TY"], ty & 0xFF)
        m.poke(sym["HUD_ON"], 0)        # εδώ μετριέται ο ΚΟΣΜΟΣ· το HUD το
        # μετράει το test_hud, και από το βήμα 83 το βήμα κάμερας των λωρίδων
        # του (hud_move, ~0,9 frames) και το σβήσιμό τους στο άλμα (hud_inval)
        # το test_split: εδώ δεν κάνουν τίποτα.
        m.poke(sym["HUD_MOVE"], 0xC9)
        m.poke(sym["HUD_INVAL"], 0xC9)
        m.set_pc(sym["START"])
        n = 0
        while m.peek(sym["DONE_FLAG"]) != 0x5A and n < 400:
            m.run_frames(1)
            n += 1
        return m, n

    def scroll(m, d, k):
        m.poke(sym["DONE_FLAG"], 0)
        m.poke(sym["SC_DIR"], d)
        m.poke(sym["SC_N"], k)
        m.set_pc(sym["DO_SCROLL"])
        n = 0
        while m.peek(sym["DONE_FLAG"]) != 0x5A and n < 400:
            m.run_frames(1)
            n += 1
        return n

    fails = 0
    cost = {}
    ref, full_frames = full(*BASE)
    want = ref.read_ram(0xC000, 0x4000)
    want_off = ref.peek(sym["CAM_OFF"]) | (ref.peek(sym["CAM_OFF"] + 1) << 8)

    for d, (dx, dy, name) in DIRS.items():
        m, _ = full(BASE[0] - dx * STEPS, BASE[1] - dy * STEPS)
        n = scroll(m, d, STEPS)
        cost[name] = n * 19968 / STEPS
        off = m.peek(sym["CAM_OFF"]) | (m.peek(sym["CAM_OFF"] + 1) << 8)
        got = m.read_ram(0xC000, 0x4000)
        bad = []
        for y in range(160):
            hi = (y & 7) * 0x800
            row = (y >> 3) * 80
            for x in range(80):
                p = (row + x + 2 * off) & 0x7FF
                if got[hi + p] != want[hi + p]:
                    bad.append((x, y))
        if off != want_off:
            print(f"ΑΠΟΤΥΧΙΑ {name}: offset {off} != {want_off}")
            fails += 1
        elif bad:
            print(f"ΑΠΟΤΥΧΙΑ {name} x{STEPS}: {len(bad)} bytes διαφορά, "
                  f"πρώτο {bad[0]}")
            fails += 1
        else:
            print(f"OK {name:9s} x{STEPS} ταυτόσημο με πλήρη σχεδίαση  "
                  f"({cost[name]/1000:.1f} ms ανά βήμα)")

    # --- και το άλλο άκρο: σκρολάρισμα σε άδειο έδαφος ---
    openc = {}
    for d, (dx, dy, name) in DIRS.items():
        m, _ = full(OPEN[0] - dx * STEPS, OPEN[1] - dy * STEPS)
        openc[name] = scroll(m, d, STEPS) * 19968 / STEPS

    print(f"\nπλήρης σχεδίαση: {full_frames} frames = "
          f"{full_frames*19968/1000:.0f} ms")
    hi = max(cost.values()) / 19968
    lo = min(openc.values()) / 19968
    print("   (χωρίς το HUD: από το βήμα 83 οι λωρίδες του ΜΕΤΑΚΙΝΟΥΝΤΑΙ σε κάθε βήμα, "
          "άλλα ~0,9 frames — το test_split· ως το βήμα 82 ξαναγράφονταν, 2,6)")
    print(f"σκρολάρισμα ανά tile:  ανοιχτό έδαφος {lo:.1f} - "
          f"{max(openc.values())/19968:.1f} frames"
          f"   ·  μέσα στη βάση {min(cost.values())/19968:.1f} - {hi:.1f}")
    if lo > LIMIT_OPEN:
        print(f"  ΑΠΟΤΥΧΙΑ: {lo:.1f} frames σε ΑΔΕΙΟ έδαφος — το πέρασμα πληρώνει "
              f"αντικείμενα που δεν φαίνονται")
        fails += 1
    if hi > LIMIT_BASE:
        print(f"  ΑΠΟΤΥΧΙΑ: {hi:.1f} frames μέσα στη βάση, πάνω από το "
              f"μετρημένο {LIMIT_BASE}")
        fails += 1
    if fails == 0:
        print("  (το DESIGN §8.2 καταγράφει αυτά τα δύο νούμερα — συμφωνούν)")

    # --- και σε us (βήμα 108) ---
    def exact(patch=()):
        out = {}
        for name, d in (("πλήρης", None),) + tuple((n, k) for k, (_, _, n) in DIRS.items()):
            m = CPC()
            m.run_frames(60)
            assert m.quickload(SNA, start=False)
            dx, dy = (0, 0) if d is None else DIRS[d][:2]
            m.poke(sym["CAM_TX"], (BASE[0] - dx) & 0xFF)
            m.poke(sym["CAM_TY"], (BASE[1] - dy) & 0xFF)
            m.poke(sym["HUD_ON"], 0)
            m.poke(sym["HUD_MOVE"], 0xC9)
            m.poke(sym["HUD_INVAL"], 0xC9)
            for at, v in patch:
                m.poke(at, v)
            m.set_pc(sym["START"])
            if d is not None:
                while m.peek(sym["DONE_FLAG"]) != 0x5A:
                    m.run_frames(1)
                m.poke(sym["DONE_FLAG"], 0)
                m.poke(sym["SC_DIR"], d)
                m.poke(sym["SC_N"], 1)
                m.set_pc(sym["DO_SCROLL"])
            t = 0
            while m.peek(sym["DONE_FLAG"]) != 0x5A:
                m.run_us(20)
                t += 20
            out[name] = t
        return out

    got = exact()
    for k, v in got.items():
        ok = v <= EXACT_CEIL[k]
        print(f"{'OK' if ok else 'ΑΠΟΤΥΧΙΑ'} {k}: {v} us (ταβάνι {EXACT_CEIL[k]}, "
              f"{EXACT_WAS[k]} στο βήμα 107)")
        fails += not ok
    # ΑΡΝΗΤΙΚΟ: το ob_shell χωρίς τον πίνακα — κάθε τεταρτημόριο ολόκληρο.
    at = sym["OB_SHELL"]
    m = CPC()
    m.run_frames(60)
    assert m.quickload(SNA, start=False)
    body = m.read_ram(at, 80)
    i = body.find(bytes([0x22, sym["OB_SPT"] & 255, sym["OB_SPT"] >> 8]))
    assert i >= 0, "δεν βρέθηκε το ld (ob_spt),hl στο ob_shell"
    bad = exact([(at + i + k, 0) for k in range(3)])
    over = [k for k, v in bad.items() if v > EXACT_CEIL[k]]
    print(f"{'OK' if over else 'ΑΠΟΤΥΧΙΑ'} ΑΡΝΗΤΙΚΟ: χωρίς τα διαστήματα ξεπερνούν το ταβάνι "
          f"{', '.join(f'{k} {bad[k]}' for k in over) or 'κανένα'}")
    fails += not over
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
