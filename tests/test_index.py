#!/usr/bin/env python3
"""Το ευρετήριο αντικειμένων (DESIGN §8.4): κανένα tile δεν χάνει τίποτα.

Το ob_draw_all ζωγραφίζει από το βήμα 39 μόνο όσα αντικείμενα έχουν περίγραμμα
μέσα στο clip. Η ισοδυναμία του σκρολαρίσματος (test_scroll.py) ΔΕΝ το ελέγχει
αυτό: η λωρίδα και η πλήρης σχεδίαση περνούν τώρα ΚΑΙ ΟΙ ΔΥΟ από το ευρετήριο,
και ένα αντικείμενο που λείπει από αυτό λείπει και από τις δύο.

ΤΟ ΕΛΕΓΧΟΜΕΝΟ: σε μαύρη οθόνη, κάθε tile του κάδρου ζωγραφισμένο ΜΟΝΟ ΤΟΥ (clip
ένα tile) είναι ίδιο με το ίδιο tile της πλήρους σχεδίασης. Ενα περίγραμμα
μικρότερο από ό,τι ζωγραφίζει το αντικείμενο το κόβει από τα tiles που
ξεχωρίζουν· η πλήρης σχεδίαση το κρατά, γιατί εκεί το clip είναι όλο το κάδρο.
Οτι το ίδιο το κάδρο είναι σωστό το λέει το test_object.py, απέναντι σε
ανεξάρτητο renderer.

ΑΡΝΗΤΙΚΟ: με το δεξί άκρο ένα tile πιο κοντό (το oi_gx χωρίς το inc a μετά το
tile του τελευταίου byte), κάθε αντικείμενο χάνει το τελευταίο του tile.

ΚΑΙ ΤΟ ΚΟΣΤΟΣ: το πέρασμα χωρίς τίποτα ορατό, που ήταν 49 ms.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/vasilhs/cpcemu")

from test_object import build, CAMERAS                                  # noqa: E402

SNA = os.path.join(ROOT, "build", "objtest.sna")
SCR_W, PLAY, TW, TH = 80, 160, 20, 10
OPEN = (30, 30)                 # μακριά από την αποικία: τίποτα ορατό
EMPTY_MAX = 4.0                 # ms — ήταν 49 πριν από το ευρετήριο
FAIL = []


def check(ok, msg):
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ ") + msg)
    if not ok:
        FAIL.append(msg)


def boot(sym, tx, ty):
    from cpc import CPC
    m = CPC()
    m.run_frames(60)
    assert m.quickload(SNA, start=False), "quickload απέτυχε"
    m.poke(sym["CAM_TX"], tx & 0xFF)
    m.poke(sym["CAM_TY"], ty & 0xFF)
    m.poke(sym["HUD_ON"], 0)
    m.set_pc(sym["START"])
    for _ in range(400):
        if m.peek(sym["DONE_FLAG"]) == 0x5A:
            return m
        m.run_frames(1)
    raise AssertionError("το START δεν τερμάτισε")


def draw(m, sym, clip, reps=1):
    """ob_draw_all με αυτό το clip, πάνω σε μαύρη οθόνη. -> (οθόνη, μs)."""
    m.write_ram(0xC000, bytes(0x4000))
    for k, v in zip(("CLIP_X0", "CLIP_X1", "CLIP_Y0", "CLIP_Y1"), clip):
        m.poke(sym[k], v)
    m.poke(sym["REP_N"], reps)
    m.poke(sym["DONE_FLAG"], 0)
    m.set_pc(sym["OBJ_ONLY"])
    us = 0
    while m.peek(sym["DONE_FLAG"]) != 0x5A:
        m.run_us(100)
        us += 100
        assert us < 20_000_000, "το ob_draw_all δεν τερμάτισε"
    off = m.peek(sym["CAM_OFF"]) | (m.peek(sym["CAM_OFF"] + 1) << 8)
    ram = m.read_ram(0xC000, 0x4000)
    pic = bytes(ram[(y & 7) * 0x800 + (((y >> 3) * SCR_W + x + 2 * off) & 0x7FF)]
                for y in range(PLAY) for x in range(SCR_W))
    return pic, us / reps


def tiles(m, sym):
    """(tiles με κάτι, tiles που διαφέρουν από την πλήρη σχεδίαση)."""
    full, _ = draw(m, sym, (0, SCR_W, 0, PLAY))
    busy, bad = 0, []
    for r in range(TH):
        for c in range(TW):
            pic, _ = draw(m, sym, (4 * c, 4 * c + 4, 16 * r, 16 * r + 16))
            idx = [(16 * r + y) * SCR_W + 4 * c + x
                   for y in range(16) for x in range(4)]
            busy += any(full[i] for i in idx)
            # Το tile όπως στην πλήρη σχεδίαση, και τίποτε άλλο πουθενά.
            inside = set(idx)
            if (any(pic[i] != full[i] for i in idx)
                    or any(pic[i] for i in range(len(pic)) if i not in inside)):
                bad.append((c, r))
    return busy, bad


def main():
    sym = build()

    total_busy = 0
    for tx, ty, why in CAMERAS:
        m = boot(sym, tx, ty)
        busy, bad = tiles(m, sym)
        total_busy += busy
        check(not bad, f"κάμερα ({tx:>4},{ty:>4}): 200 tiles ένα-ένα = πλήρης "
                       f"σχεδίαση, {busy} με αντικείμενα"
                       + (f" — λάθος {bad[:6]}" if bad else ""))

    # --- ΑΡΝΗΤΙΚΟ: το δεξί άκρο ένα tile πιο κοντό ---
    # oi_gx: PUSH HL / ADD HL,DE / DEC HL / CALL oi_t4 / INC A — το INC A, το
    # «ένα μετά το τελευταίο byte», γίνεται NOP, και το ευρετήριο ξαναχτίζεται.
    at = sym["OI_GX"]
    m = boot(sym, *CAMERAS[0][:2])
    code = list(m.read_ram(at, 7))
    t4 = sym["OI_T4"]
    assert code == [0xE5, 0x19, 0x2B, 0xCD, t4 & 0xFF, t4 >> 8, 0x3C], \
        f"το oi_gx δεν είναι αυτό που περιμένει η δοκιμή: {code}"
    m.poke(at + 6, 0x00)
    m.poke(sym["OB_IDX"], 15)               # OB_IX_ALL
    busy, bad = tiles(m, sym)
    check(len(bad) > 0, f"ΑΡΝΗΤΙΚΟ: με το δεξί άκρο ένα tile πιο κοντό "
                        f"{len(bad)} tiles χάνουν κομμάτι αντικειμένου")

    # --- το κόστος ---
    m = boot(sym, *OPEN)
    _, empty = draw(m, sym, (0, SCR_W, 0, PLAY), reps=20)
    nd, nc, ns = (m.peek(sym[k]) for k in ("OI_ND", "OI_NC", "OI_NS"))
    check(empty / 1000 < EMPTY_MAX,
          f"πέρασμα χωρίς τίποτα ορατό: {empty / 1000:.2f} ms (όριο {EMPTY_MAX}, "
          f"ήταν 49) — {nd} θόλοι, {nc} διάδρομοι, {ns} δομές στο ευρετήριο")
    print(f"   {total_busy} tiles με αντικείμενα σε {len(CAMERAS)} κάμερες")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
