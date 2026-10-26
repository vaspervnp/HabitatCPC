#!/usr/bin/env python3
"""Τα βελάκια του κέρσορα στο πραγματικό παιχνίδι (colony.sna, με τη διακοπή).

Ο παίκτης ζήτησε μετά το βήμα 174: «να μετακινείται μία θέση, και όταν πατάω
το βελάκι να μην το παίρνει σαν επανάληψη αν δεν έχουν περάσει 200 ms». Η
πρόζα (DESIGN §9.1, ui_move στο src/ui.asm):

  ΡΟΛΟΙ       το is_fc της διακοπής (src/isr.asm) ανεβαίνει ακριβώς μία φορά
              σε κάθε frame, ό,τι κι αν κάνει ο βρόχος.
  ΠΑΤΗΜΑ      ένα σύντομο πάτημα (3 frames) κινεί τον κέρσορα ΜΙΑ θέση, ένα
              tile, και αμέσως: το πολύ ένα frame μετά.
  ΔΥΟ ΠΑΤΗΜΑΤΑ δύο πατήματα με 6 frames ανάμεσα κινούν δύο θέσεις: ένα νέο
              πάτημα δεν περιμένει τα 200 ms.
  ΚΡΑΤΗΜΕΝΟ   ένα βελάκι κρατημένο 150 frames: η πρώτη κίνηση αμέσως, και
              ανάμεσα σε δύο κινήσεις τουλάχιστον UM_REP = 10 frames (200 ms)
              του ρολογιού, και όχι πάνω από 10 + 4 όσο σκρολάρει.
  ΚΟΣΤΟΣ      ένας γύρος του LOOK χωρίς πλήκτρο: το ui_move δεν κάνει τίποτα.

Αρνητικά, με τον κώδικα πειραγμένο: το cp UM_REP σε cp 1 (κάθε γύρος του
βρόχου, όπως ως το βήμα 174) — το ΚΡΑΤΗΜΕΝΟ πέφτει· το and (hl) του act_hit σε
nop (κάθε γύρος με κρατημένο βελάκι κινεί, και δύο πατήματα των 3 frames κάνουν
8 tiles) — το ΔΥΟ ΠΑΤΗΜΑΤΑ πέφτει· και το inc a του ρολογιού σε nop — το ΡΟΛΟΙ
πέφτει. Ως το βήμα 174 ένα πάτημα 3 frames έκανε 4 tiles, και 50 frames 28.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import test_info as TI                                   # noqa: E402
from cpc import KEY_RIGHT, KEY_LEFT                      # noqa: E402

FAIL = []
UM_REP = 10                                              # src/ui.asm


def check(ok, msg):
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ ") + msg)
    if not ok:
        FAIL.append(msg)
    return ok


def s8(v):
    return v - 256 if v > 127 else v


def find(m, at, n, pat):
    ram = m.read_ram(at, n)
    hits = [at + i for i in range(n - len(pat) + 1) if list(ram[i:i + len(pat)]) == pat]
    return hits


def scene(sym, patch=()):
    G = TI.Game(sym, patch)
    G.cursor(0, 0)
    G.m.run_frames(20)
    return G


def clock(G):
    return G.m.peek(G.sym["IS_FC"])


def hx(G):
    return s8(G.m.peek(G.sym["CUR_HX"]))


def tap_moves(sym, patch=()):
    G = scene(sym, patch)
    m = G.m
    x0 = hx(G)
    m.key_down(KEY_RIGHT)
    first = None
    for f in range(3):
        m.run_frames(1)
        if first is None and hx(G) != x0:
            first = f
    m.key_up(KEY_RIGHT)
    m.run_frames(20)
    one = hx(G) - x0
    # δύο πατήματα, 6 frames ανάμεσα
    x1 = hx(G)
    for _ in range(2):
        m.key_down(KEY_LEFT)
        m.run_frames(3)
        m.key_up(KEY_LEFT)
        m.run_frames(6)
    m.run_frames(20)
    two = x1 - hx(G)
    return one, first, two


def held(sym, frames=150, patch=()):
    G = scene(sym, patch)
    m = G.m
    x = hx(G)
    log = []
    m.key_down(KEY_RIGHT)
    for f in range(frames):
        m.run_frames(1)
        nx = hx(G)
        if nx != x:
            log.append((f, clock(G), nx - x))
            x = nx
    m.key_up(KEY_RIGHT)
    m.run_frames(10)
    return log


def main():
    sym, _ = TG.build()

    # --- ΡΟΛΟΙ ---
    G = scene(sym)
    c0 = clock(G)
    G.m.run_frames(50)
    c1 = clock(G)
    check((c1 - c0) & 255 == 50, f"ΡΟΛΟΙ: το is_fc ανέβηκε {(c1 - c0) & 255} σε 50 frames")
    inc = find(G.m, sym["IS_VS"], sym["IS_END"] - sym["IS_VS"],
               [0x3A, sym["IS_FC"] & 255, sym["IS_FC"] >> 8, 0x3C])
    check(len(inc) == 1, "ΡΟΛΟΙ: ld a,(is_fc) · inc a μία φορά στο is_vs")

    # --- ΠΑΤΗΜΑ, ΔΥΟ ΠΑΤΗΜΑΤΑ ---
    one, first, two = tap_moves(sym)
    check(one == 2 and first is not None and first <= 1,
          f"ΠΑΤΗΜΑ: 3 frames πατημένο -> {one // 2} tile, η κίνηση στο frame {first}")
    check(two == 4, f"ΔΥΟ ΠΑΤΗΜΑΤΑ με 6 frames ανάμεσα -> {two // 2} tiles")

    # --- ΚΡΑΤΗΜΕΝΟ ---
    log = held(sym)
    gaps = [(b[1] - a[1]) & 255 for a, b in zip(log, log[1:])]
    check(log and log[0][0] <= 1 and all(d == 2 for _, _, d in log)
          and gaps and min(gaps) >= UM_REP and max(gaps) <= UM_REP + 4,
          f"ΚΡΑΤΗΜΕΝΟ 150 frames: {len(log)} βήματα του ενός tile, το πρώτο στο frame "
          f"{log[0][0] if log else None}, ανάμεσα {sorted(set(gaps))} frames του ρολογιού "
          f"(τουλάχιστον {UM_REP}: 200 ms)")

    # --- ΑΡΝΗΤΙΚΑ ---
    um = sym["UI_MOVE"]
    cp = find(G.m, um, 40, [0xFE, UM_REP])
    andh = find(G.m, um, 40, [0xA6, 0x3A, sym["IS_FC"] & 255, sym["IS_FC"] >> 8])
    if check(len(cp) == 1 and len(andh) == 1, "τα αρνητικά βρήκαν το cp UM_REP και το and (hl)"):
        nlog = held(sym, patch=[(cp[0] + 1, 1)])
        ngaps = [(b[1] - a[1]) & 255 for a, b in zip(nlog, nlog[1:])]
        check(ngaps and min(ngaps) < UM_REP,
              f"ΑΡΝΗΤΙΚΟ «cp 1»: {len(nlog)} βήματα, ανάμεσα ως {min(ngaps) if ngaps else None} "
              f"frames — το ΚΡΑΤΗΜΕΝΟ θα έπεφτε")
        n1, nf, n2 = tap_moves(sym, patch=[(andh[0], 0)])
        check(n2 != 4, f"ΑΡΝΗΤΙΚΟ «χωρίς το act_hit»: δύο πατήματα -> {n2 // 2} tiles — "
              f"το ΔΥΟ ΠΑΤΗΜΑΤΑ θα έπεφτε")
    G2 = scene(sym, patch=[(inc[0] + 3, 0)] if inc else [])
    c0 = clock(G2)
    G2.m.run_frames(50)
    check((clock(G2) - c0) & 255 != 50, f"ΑΡΝΗΤΙΚΟ «χωρίς το inc a»: το ρολόι ανέβηκε "
          f"{(clock(G2) - c0) & 255} — το ΡΟΛΟΙ θα έπεφτε")

    print("ΟΛΑ ΚΑΛΑ" if not FAIL else f"{len(FAIL)} ΑΠΟΤΥΧΙΕΣ")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
