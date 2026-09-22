#!/usr/bin/env python3
"""Οντότητες, κίνηση και τροχός (DESIGN §6.1, §6.3, §7.2).

  ΤΑΥΤΟΤΗΤΑ   μετά από εκατοντάδες frames, και οι 2.048 bytes των πεδίων ΚΑΙ
              οι 128 μάσκες θέσεων είναι ίδιες με την tools/entity.py.
  ΚΙΝΗΣΗ      και κάτι όντως έγινε: πράκτορες άλλαξαν κόμβο, μπήκαν σε ακμές,
              έφτασαν κάπου. Μια δοκιμή που περνά επειδή κανείς δεν κουνήθηκε
              δεν δοκιμάζει τίποτα.
  ΣΥΝΕΠΕΙΑ    οι μάσκες θέσεων συμφωνούν με το πού στέκεται ο καθένας.
  ΚΟΣΤΟΣ      us ανά θέση τροχού, απέναντι στα 1.800 us του §7.2.
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")

import graph as G                                                # noqa: E402
import entity as E                                               # noqa: E402

RASM = os.path.expanduser("~/rasm/rasm.exe")
SNA = os.path.join(ROOT, "build", "simtest.sna")
FRAME_US = 19968
TICKS = 640                 # 40 πλήρεις περιστροφές
STAGE_AG, STAGE_OCC = 0xC000, 0xC800


def build():
    r = subprocess.run([RASM, "simtest.asm", "-oi", SNA, "-v2", "-s", "-eo"],
                       cwd=HERE, capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(SNA):
        sys.exit("rasm απέτυχε:\n" + r.stdout + r.stderr)
    sym = {}
    for line in open(os.path.join(HERE, "rasmoutput.sym"), encoding="utf-8",
                     errors="replace"):
        p = line.split()
        if len(p) >= 2 and p[1].startswith("#"):
            sym[p[0].upper()] = int(p[1][1:], 16)
    for line in open(os.path.join(ROOT, "build", "layout.asm"), encoding="utf-8"):
        p = line.split()
        if len(p) == 3 and p[1] == "equ" and p[2].startswith("#"):
            sym[p[0].upper()] = int(p[2][1:], 16)
    return sym


def enter(m, sym, label, limit=600):
    m.poke(sym["DONE_FLAG"], 0)
    m.set_pc(sym[label])
    n = 0
    while m.peek(sym["DONE_FLAG"]) != 0x5A and n < limit:
        m.run_frames(1)
        n += 1
    assert m.peek(sym["DONE_FLAG"]) == 0x5A, \
        f"το {label} δεν τερμάτισε σε {n} frames, PC=#{m.pc:04X}"
    return n


def run_z80(sym, g, sim, ticks, move_n=None, decay_n=None):
    from cpc import CPC
    m = CPC()
    m.run_frames(60)
    assert m.quickload(SNA, start=False), "quickload απέτυχε"

    m.write_ram(sym["G_NODE_ADJ"], bytes(g.adj))
    m.write_ram(sym["G_RT_NODES"], bytes(g.deg))
    m.poke(sym["RT_N"], g.hw)
    enter(m, sym, "BUILD_ROUTES")

    m.write_ram(STAGE_AG, sim.a.to_bytes())
    m.write_ram(STAGE_OCC, bytes(sim.occ) + bytes(128))
    enter(m, sym, "LOAD_STATE")

    if move_n is not None:
        m.poke(sym["WH_MOVE_N"], move_n)
    if decay_n is not None:
        m.poke(sym["WH_DECAY_N"], decay_n)
    m.poke(sym["TICK_COUNT"], ticks & 0xFF)
    m.poke(sym["TICK_COUNT"] + 1, ticks >> 8)
    frames = enter(m, sym, "RUN_TICKS")

    enter(m, sym, "SAVE_STATE")
    return (m.read_ram(STAGE_AG, 2048), m.read_ram(STAGE_OCC, 128), frames)


def describe(blob, sim):
    a = E.Agents().from_bytes(blob)
    moved = sum(1 for i in range(128) if a.node[i] != sim.a.node[i])
    intransit = sum(1 for i in range(128) if a.edge[i] != E.NO_EDGE)
    arrived = sum(1 for i in range(128)
                  if a.flags[i] & E.F_ALIVE and a.dest[i] == a.node[i]
                  and a.edge[i] == E.NO_EDGE)
    return moved, intransit, arrived


def check_occ(blob, occ, g):
    """Κάθε ζωντανός που στέκεται κάπου πρέπει να κρατά τη θέση του, και καμία
    θέση δεν κρατιέται από δύο. Αυτό πιάνει διαρροές που η ταυτότητα δεν πιάνει
    αν λάθος ίδιο βγάζουν και οι δύο πλευρές — εδώ ο έλεγχος είναι ανεξάρτητος."""
    a = E.Agents().from_bytes(blob)
    want = bytearray(G.MAXNODE)
    for i in range(128):
        if not a.flags[i] & E.F_ALIVE:
            continue
        if a.edge[i] != E.NO_EDGE or a.slot[i] == E.NO_SLOT:
            continue
        bit = 1 << a.slot[i]
        if want[a.node[i]] & bit:
            return f"δύο πράκτορες στη θέση {a.slot[i]} του κόμβου {a.node[i]}"
        want[a.node[i]] |= bit
    for n in range(g.hw):
        if want[n] != occ[n]:
            return (f"ο κόμβος {n}: η μάσκα λέει {occ[n]:08b}, "
                    f"οι πράκτορες λένε {want[n]:08b}")
    return None


def main():
    sym = build()
    g = G.GRAPHS["colony"]()
    _, nexthop = G.all_pairs(g)

    sim = E.populate(E.Sim(g, nexthop))
    before = E.Agents().from_bytes(sim.a.to_bytes())
    sim_occ0 = bytes(sim.occ)
    start = E.Sim(g, nexthop)
    start.a.from_bytes(sim.a.to_bytes())
    start.occ = bytearray(sim.occ)

    got_a, got_occ, frames = run_z80(sym, g, start, TICKS)

    for _ in range(TICKS):
        sim.tick()
    want_a, want_occ = sim.a.to_bytes(), bytes(sim.occ)

    if got_a != want_a:
        bad = [i for i in range(2048) if got_a[i] != want_a[i]]
        print(f"ΑΠΟΤΥΧΙΑ πεδία: {len(bad)} από 2048 bytes διαφέρουν")
        for i in bad[:8]:
            f, aid = E.FIELDS[(i // 256) * 2 + ((i % 256) >= 128)], i % 128
            print(f"    πράκτορας {aid:3d} πεδίο {f:9s}  Z80 {got_a[i]:3d} "
                  f"!= αναφορά {want_a[i]:3d}")
        return 1
    if got_occ != want_occ:
        bad = [i for i in range(128) if got_occ[i] != want_occ[i]]
        print(f"ΑΠΟΤΥΧΙΑ μάσκες: κόμβοι {bad[:8]}")
        return 1
    print(f"OK ταυτότητα: {TICKS} frames, 2048 bytes πεδίων + 128 μάσκες "
          f"ταυτόσημα με την αναφορά")

    moved, intransit, arrived = describe(got_a, type("S", (), {"a": before})())
    if moved == 0 or intransit == 0:
        print(f"ΑΠΟΤΥΧΙΑ: κανείς δεν κουνήθηκε ({moved} άλλαξαν κόμβο, "
              f"{intransit} σε ακμή) — η δοκιμή δεν δοκίμασε τίποτα")
        return 1
    print(f"OK κίνηση:    {moved} πράκτορες άλλαξαν κόμβο, {intransit} είναι "
          f"σε ακμή τώρα, {arrived} έφτασαν στον προορισμό τους")

    why = check_occ(got_a, got_occ, g)
    if why:
        print(f"ΑΠΟΤΥΧΙΑ μάσκες θέσεων: {why}")
        return 1
    print("OK θέσεις:    κάθε μάσκα συμφωνεί με το πού στέκεται ο καθένας, "
          "καμία διπλοκρατημένη")

    # --- κόστος ανά ΕΙΔΟΣ θέσης ---
    # Τρία τρεξίματα, και η διαφορά τους απομονώνει το καθένα. Με φέτα 0 η
    # θέση γυρίζει αμέσως, οπότε μένει μόνο ο τροχός.
    def timed(mv, dc):
        st = E.Sim(g, nexthop)
        st.a.from_bytes(before.to_bytes())
        st.occ = bytearray(sim_occ0)
        return run_z80(sym, g, st, TICKS, move_n=mv, decay_n=dc)[2] * FRAME_US

    t_all = frames * FRAME_US
    t_nomove = timed(0, E.WH_DECAY_N)
    t_none = timed(0, 0)

    move_us = (t_all - t_nomove) / (TICKS // 2)         # 8 στις 16 θέσεις
    decay_us = (t_nomove - t_none) / (TICKS * 3 // 16)  # 3 στις 16
    over_us = t_none / TICKS

    print(f"\nκόστος ανά θέση τροχού ({TICKS} θέσεις = {TICKS//16} περιστροφές):")
    print(f"  κίνηση  {move_us:7.0f} us  ({E.WH_MOVE_N} πράκτορες)"
          f"   — το §7.2 προϋπολόγιζε 1.800 us")
    print(f"  φθορά   {decay_us:7.0f} us  ({E.WH_DECAY_N} πράκτορες)"
          f"   — το §7.2 προϋπολόγιζε  433 us")
    print(f"  τροχός  {over_us:7.0f} us  (μόνο η διανομή)")
    worst = max(move_us, decay_us) + over_us
    which = "κίνηση" if move_us > decay_us else "φθορά"
    print(f"  χειρότερο frame: {worst:.0f} us ({which}) από τα 19.968 "
          f"= {100*worst/FRAME_US:.0f}%")

    if worst > FRAME_US:
        print("ΑΠΟΤΥΧΙΑ: η πιο ακριβή θέση δεν χωράει σε ένα frame")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
