#!/usr/bin/env python3
"""Σκρολάρισμα: ισοδυναμία με πλήρη σχεδίαση, και το πραγματικό του κόστος.

Ο ΙΣΧΥΡΙΣΜΟΣ (DESIGN §8.2): το σκρολάρισμα είναι δύο εγγραφές στον CRTC και
μία λωρίδα επανασχεδίασης· η υπόλοιπη εικόνα δεν αγγίζεται. Ο έλεγχος είναι η
ισοδυναμία: ξεκίνα k tiles πιο πίσω, σχεδίασε πλήρως, σκρολάρισε k φορές, και
η μνήμη οθόνης πρέπει να είναι ΤΑΥΤΟΣΗΜΗ με πλήρη σχεδίαση στο τέλος.

Αν κάτι λείπει από τη λωρίδα — ένα τεταρτημόριο, μια πόρτα, ένα φυτό — η
σύγκριση το δείχνει· το μάτι δεν το δείχνει, γιατί η προηγούμενη εικόνα είναι
σχεδόν σωστή.
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
        m.set_pc(sym["START"])           # μετράει το test_hud, χωριστά
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
    print("   (χωρίς το HUD: το ξαναγράψιμό του είναι άλλα 2,6 frames ανά βήμα)")
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
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
