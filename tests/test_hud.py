#!/usr/bin/env python3
"""Το HUD: περιεχόμενο, σύνορο με το κάδρο, και το ΚΟΣΤΟΣ του (DESIGN §9.2).

Τρεις ισχυρισμοί, τρεις έλεγχοι:

  1. ΤΟ ΣΥΝΟΡΟ. Το πέρασμα αντικειμένων δεν γράφει ποτέ έξω από το κάδρο. Από
     το βήμα 83 το HUD είναι ΔΥΟ λωρίδες Mode 1 (src/hud.asm): οι 160 bytes
     πριν από το cam_p και οι 240 μετά το cam_p+1600, σε κάθε μία από τις οκτώ
     γραμμές. Γεμίζουμε και τις δύο με σημάδι, σχεδιάζουμε ΧΩΡΙΣ HUD, και το
     σημάδι πρέπει να είναι ακέραιο. Χωρίς αυτό, ένας θόλος στο χείλος γράφει
     πάνω στους αριθμούς και κανείς δεν το προσέχει μέχρι να παίξει.

  2. ΤΟ ΠΕΡΙΕΧΟΜΕΝΟ, byte προς byte με αναφορά γραμμένη από τη διάταξη του §9.2
     (tools/hudref.py): οι 40 γραμμές των λωρίδων, και ό,τι δεν είναι σειρά του
     HUD (το δεξί μισό της πάνω δεύτερης σειράς, οι δύο πρώτες της κάτω) μαύρο.

  3. ΤΟ ΚΟΣΤΟΣ. Κρύο: μετά από ΑΛΜΑ κάμερας (σπίτι, φόρτωμα), όπου οι λωρίδες
     σβήνονται και ξαναγράφονται· ένα ΒΗΜΑ κάμερας δεν ξαναγράφει πια τίποτα,
     τις μετακινεί (το μετρά το test_split). Ζεστό: κάθε τικ HUD.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/vasilhs/cpcemu")

import hudref                                                           # noqa: E402
import hudread                                                          # noqa: E402
import scene as S                                                       # noqa: E402
from test_object import build                                           # noqa: E402

SNA = os.path.join(ROOT, "build", "objtest.sna")
REPS = 20
MARK = 0xAA

EC = dict(STOCK=0, PSTORE=28, PCAP=30, O2PROD=38, O2USE=40, POK=46, O2OK=47,
          DAY=49, SOL=51, ALIVE=58, GAMEOVER=59, STORM=61, POPCAP=74, METEOR=86)

STATE = dict(o2prod=200, o2use=188, pstore=3215, pcap=3240,
             stock=[412, 233, 0, 120, 40, 12, 8, 3, 0, 2, 0, 0, 0, 0],
             alive=34, popcap=48, sol=17, day=1,
             pok=1, o2ok=1, storm=0, gameover=0, coins=16)

# Δεύτερη κατάσταση: μηδενικά, τριψήφια, και συναγερμός. Η πρώτη δεν δοκιμάζει
# ούτε τα μπροστινά μηδενικά ούτε τη γραμμή συναγερμού.
STATE2 = dict(o2prod=12, o2use=190, pstore=0, pcap=3240,
              stock=[7, 0, 0, 600, 5, 0, 1, 0, 0, 0, 0, 0, 0, 0],
              alive=3, popcap=4, sol=100, day=0,
              pok=0, o2ok=1, storm=1, gameover=0)


# Τρίτη (βήμα 52): οι άκρες που καμία από τις δύο δεν άγγιζε. Αριθμοί με
# περισσότερα ψηφία από όσα χωρούν — ο πληθυσμός 100/148 σε δύο, το 1005 και
# το 65535 σε τρία — μηδενική κατανάλωση και μηδενική χωρητικότητα (γεμάτες
# μπάρες, όχι διαίρεση με μηδέν), νερό πάνω από το ταβάνι, και «LOW POWER».
STATE3 = dict(o2prod=0, o2use=0, pstore=5, pcap=0,
              stock=[650, 30, 0, 1005, 65535, 999, 100, 10, 0, 1, 0, 0, 0, 0],
              alive=100, popcap=148, sol=255, day=1,
              pok=2, o2ok=1, storm=0, gameover=0, coins=1005)
# Τέταρτη και πέμπτη: λίγο φαγητό (κάτω από μία μερίδα ανά ζωντανό), και η
# βροχή μετεωριτών, που μπαίνει μπροστά του.
STATE4 = dict(STATE, stock=[412, 33, 0, 120, 40, 12, 8, 3, 0, 2, 0, 0, 0, 0])
STATE5 = dict(STATE4, meteor=3)
# Εκτη και έβδομη (βήμα 122): η αποθήκη γέμισε — και η θύελλα μπαίνει μπροστά της.
STATE6 = dict(STATE, full=1)
STATE7 = dict(STATE, full=1, storm=1)


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
    for k in ("alive", "popcap", "sol", "day", "pok", "o2ok", "storm", "gameover",
              "meteor"):
        m.poke(g + EC[k.upper()], st.get(k, 0))
    m.poke(sym["EC_FULL"], st.get("full", 0))       # τράπεζα 0 (βήμα 122)
    w16(sym["OT_COINS"], st.get("coins", 0))        # βήμα 134: εδώ από μεταβλητή
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
    # σημάδεψε τις λωρίδες ΠΡΙΝ τη σχεδίαση, στις διευθύνσεις που θα έχουν με
    # το offset της τελικής κάμερας
    m.poke(sym["REP_N"], 1)
    run(m, sym, "START")
    cp = hudread.cam_p(m, sym)
    m2 = load(sym, g, STATE, hud=False)
    addrs = hudread.band_addrs(cp)
    for a in addrs:
        m2.poke(a, MARK)
    m2.poke(sym["REP_N"], 1)
    run(m2, sym, "START")
    # Το view_draw της πρώτης σχεδίασης ΣΒΗΝΕΙ τις λωρίδες όταν πηδά η κάμερα
    # (hud_inval): το σημάδι μπαίνει ξανά, και η σχεδίαση γίνεται στην ίδια θέση.
    for a in addrs:
        m2.poke(a, MARK)
    m2.poke(sym["REP_N"], 1)
    run(m2, sym, "START")
    dirty = [a for a in addrs if m2.peek(a) != MARK]
    if dirty or hudread.cam_p(m2, sym) != cp:
        print(f"ΑΠΟΤΥΧΙΑ σύνορο: το κάδρο έγραψε {len(dirty)} bytes μέσα στις λωρίδες, "
              f"πρώτο #{dirty[0] if dirty else 0:04X}")
        fails += 1
    else:
        print(f"OK σύνορο: το πέρασμα αντικειμένων δεν αγγίζει κανένα από τα {len(addrs)} "
              f"bytes των λωρίδων")

    # --- 2. το περιεχόμενο ----------------------------------------------
    for name, st in (("κανονική", STATE), ("μηδενικά + συναγερμός", STATE2),
                     ("υπερχείλιση + LOW POWER", STATE3), ("λίγο φαγητό", STATE4),
                     ("μετεωρίτες", STATE5), ("γεμάτη αποθήκη", STATE6),
                     ("θύελλα και γεμάτη αποθήκη", STATE7)):
        m = load(sym, g, st)
        m.poke(sym["REP_N"], 1)
        run(m, sym, "START")
        got = hudread.band_lines(m.read_ram(0xC000, 0x4000), hudread.cam_p(m, sym))
        want = hudref.Hud().draw(st).to_lines()
        bad = []
        for y, row in want.items():
            bad += [(x, y) for x in range(80) if got[y][x] != row[x]]
        if bad:
            fails += 1
            print(f"ΑΠΟΤΥΧΙΑ περιεχόμενο ({name}): {len(bad)} bytes, "
                  f"π.χ. (στήλη, γραμμή) {bad[:6]}")
        else:
            print(f"OK περιεχόμενο ({name}): οι 40 γραμμές των δύο λωρίδων ταυτόσημες")

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
    print(f"\nκόστος HUD, κρύο (μετά από άλμα κάμερας): {costs[1]:.0f} us = "
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
