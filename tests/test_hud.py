#!/usr/bin/env python3
"""Το HUD: περιεχόμενο, σύνορο με το κάδρο, και το ΚΟΣΤΟΣ του (DESIGN §9.2).

Τρεις ισχυρισμοί, τρεις έλεγχοι:

  1. ΤΟ ΣΥΝΟΡΟ. Το πέρασμα αντικειμένων δεν γράφει ποτέ κάτω από τη γραμμή 160.
     Γεμίζουμε τις γραμμές 160-199 με σημάδι, σχεδιάζουμε ΧΩΡΙΣ HUD, και το
     σημάδι πρέπει να είναι ακέραιο. Χωρίς αυτό, ένας θόλος στο κάτω χείλος
     γράφει πάνω στους αριθμούς και κανείς δεν το προσέχει μέχρι να παίξει.

  2. ΤΟ ΠΕΡΙΕΧΟΜΕΝΟ, byte προς byte με αναφορά γραμμένη από τη διάταξη του §9.2.

  3. ΤΟ ΚΟΣΤΟΣ. Το §8.1 εκτιμούσε 0,4 frames «όταν υπάρξει ο renderer του HUD».
     Υπάρχει τώρα, και το HUD ξαναγράφεται μετά από ΚΑΘΕ βήμα σκρολαρίσματος.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/vasilhs/cpcemu")

import hudref                                                           # noqa: E402
import scene as S                                                       # noqa: E402
from test_object import build                                           # noqa: E402

SNA = os.path.join(ROOT, "build", "objtest.sna")
REPS = 20
MARK = 0xAA

EC = dict(STOCK=0, PSTORE=28, PCAP=30, O2PROD=38, O2USE=40, POK=46, O2OK=47,
          DAY=49, SOL=51, ALIVE=58, GAMEOVER=59, STORM=61, POPCAP=74)

STATE = dict(o2prod=200, o2use=188, pstore=3215, pcap=3240,
             stock=[412, 233, 0, 120, 40, 12, 8, 3, 0, 2, 0, 0, 0, 0],
             alive=34, popcap=48, sol=17, day=1,
             pok=1, o2ok=1, storm=0, gameover=0)

# Δεύτερη κατάσταση: μηδενικά, τριψήφια, και συναγερμός. Η πρώτη δεν δοκιμάζει
# ούτε τα μπροστινά μηδενικά ούτε τη γραμμή συναγερμού.
STATE2 = dict(o2prod=12, o2use=190, pstore=0, pcap=3240,
              stock=[7, 0, 0, 600, 5, 0, 1, 0, 0, 0, 0, 0, 0, 0],
              alive=3, popcap=4, sol=100, day=0,
              pok=0, o2ok=1, storm=1, gameover=0)


def econ_base():
    for line in open(os.path.join(ROOT, "build", "layout.asm"), encoding="utf-8"):
        if line.startswith("G_econ_state"):
            return int(line.split("#")[1].strip(), 16)
    sys.exit("δεν βρέθηκε το G_econ_state")


def load(sym, g, st, tx=-21, ty=-13, hud=True):
    from cpc import CPC
    m = CPC()
    m.run_frames(60)
    assert m.quickload(SNA, start=False)
    m.poke(sym["CAM_TX"], tx & 0xFF)
    m.poke(sym["CAM_TY"], ty & 0xFF)
    m.poke(sym["HUD_ON"], 1 if hud else 0)

    def w16(a, v):
        m.poke(a, v & 0xFF)
        m.poke(a + 1, (v >> 8) & 0xFF)
    w16(g + EC["O2PROD"], st["o2prod"])
    w16(g + EC["O2USE"], st["o2use"])
    w16(g + EC["PSTORE"], st["pstore"])
    w16(g + EC["PCAP"], st["pcap"])
    for i, v in enumerate(st["stock"]):
        w16(g + EC["STOCK"] + i * 2, v)
    for k in ("alive", "popcap", "sol", "day", "pok", "o2ok", "storm", "gameover"):
        m.poke(g + EC[k.upper()], st[k])
    return m


def run(m, sym, entry):
    m.poke(sym["DONE_FLAG"], 0)
    m.set_pc(sym[entry])
    n = 0
    while m.peek(sym["DONE_FLAG"]) != 0x5A and n < 600:
        m.run_frames(1)
        n += 1
    assert m.peek(sym["DONE_FLAG"]) == 0x5A, f"δεν τερμάτισε, PC=#{m.pc:04X}"
    return n


def screen_line(ram, y, off):
    hi = (y & 7) * 0x800
    row = (y >> 3) * 80
    return bytes(ram[hi + ((row + x + 2 * off) & 0x7FF)] for x in range(80))


def main():
    sym = build()
    g = econ_base()
    fails = 0

    # --- 1. το σύνορο ---------------------------------------------------
    m = load(sym, g, STATE, hud=False)
    off = 0
    # σημάδεψε τις γραμμές 160-199 ΠΡΙΝ τη σχεδίαση, στις διευθύνσεις που θα
    # έχουν με το offset της τελικής κάμερας
    m.poke(sym["REP_N"], 1)
    run(m, sym, "START")
    off = m.peek(sym["CAM_OFF"]) | (m.peek(sym["CAM_OFF"] + 1) << 8)
    m2 = load(sym, g, STATE, hud=False)
    for y in range(160, 200):
        hi = (y & 7) * 0x800
        row = (y >> 3) * 80
        for x in range(80):
            m2.poke(0xC000 + hi + ((row + x + 2 * off) & 0x7FF), MARK)
    m2.poke(sym["REP_N"], 1)
    run(m2, sym, "START")
    ram = m2.read_ram(0xC000, 0x4000)
    dirty = [(x, y) for y in range(160, 200)
             for x, b in enumerate(screen_line(ram, y, off)) if b != MARK]
    if dirty:
        print(f"ΑΠΟΤΥΧΙΑ σύνορο: το κάδρο έγραψε {len(dirty)} bytes μέσα στο HUD, "
              f"πρώτο {dirty[0]}")
        fails += 1
    else:
        print("OK σύνορο: το πέρασμα αντικειμένων σταματά στη γραμμή 160")

    # --- 2. το περιεχόμενο ----------------------------------------------
    for name, st in (("κανονική", STATE), ("μηδενικά + συναγερμός", STATE2)):
        m = load(sym, g, st)
        m.poke(sym["REP_N"], 1)
        run(m, sym, "START")
        off = m.peek(sym["CAM_OFF"]) | (m.peek(sym["CAM_OFF"] + 1) << 8)
        ram = m.read_ram(0xC000, 0x4000)
        want = hudref.Hud().draw(st).to_lines()
        bad = []
        for y, row in want.items():
            got = screen_line(ram, y, off)
            bad += [(x, y) for x in range(80) if got[x] != row[x]]
        if bad:
            fails += 1
            cols = sorted({x // 2 for x, _ in bad})
            print(f"ΑΠΟΤΥΧΙΑ περιεχόμενο ({name}): {len(bad)} bytes, "
                  f"στήλες {cols[:8]}")
        else:
            print(f"OK περιεχόμενο ({name}): 40 στήλες x 5 σειρές ταυτόσημες")

    # --- 3. το κόστος ----------------------------------------------------
    costs = {}
    for cold in (1, 0):
        m = load(sym, g, STATE)
        m.poke(sym["REP_N"], 1)
        run(m, sym, "START")
        m.poke(sym["HU_COLD"], cold)
        m.poke(sym["REP_N"], REPS)
        n = run(m, sym, "DO_HUD")
        costs[cold] = n * 19968 / REPS
    us = costs[1]
    print(f"\nκόστος HUD, κρύο (μετά από βήμα κάμερας): {costs[1]:.0f} us = "
          f"{costs[1]/19968:.2f} frames")
    print(f"           ζεστό (κάθε τικ, τίποτα δεν άλλαξε): {costs[0]:.0f} us = "
          f"{costs[0]/19968:.2f} frames")
    print(f"  (το §8.1 εκτιμούσε 0.4 frames· η κρυφή μνήμη κελιών του §9.2 "
          f"κρατά το ζεστό στο μισό)")
    # Μετρημένο όριο. Ο δρόμος διαφυγής, αν χρειαστεί, είναι να ΜΕΤΑΚΙΝΕΙΤΑΙ το
    # μπλοκ του HUD αντί να ξαναγράφεται: ένα βήμα κάμερας το μετατοπίζει κατά
    # 4 bytes μέσα στο δαχτυλίδι, δηλαδή 3.200 bytes lddr = 0,85 frames.
    if us / 19968 > 3.0:
        print("  ΑΠΟΤΥΧΙΑ: πάνω από 3 frames — ώρα για τη μετακίνηση του μπλοκ")
        fails += 1
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
