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
import econ as EC                                                # noqa: E402

RASM = os.path.expanduser("~/rasm/rasm.exe")
SNA = os.path.join(ROOT, "build", "simtest.sna")
FRAME_US = 19968
TICKS = 640                 # 40 πλήρεις περιστροφές
STAGE_AG, STAGE_OCC, STAGE_DOME, STAGE_STR = 0xC000, 0xC800, 0xC900, 0xCF00


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


def run_z80(sym, g, sim, ticks, move_n=None, decay_n=None, off=()):
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
    m.write_ram(STAGE_DOME, bytes(sim.e.dome))
    m.write_ram(STAGE_STR, bytes(sim.e.struct))
    m.write_ram(sym["G_ECON_STATE"], EC.to_bytes(sim.e))   # τράπεζα 2, βασική
    m.write_ram(sym["G_JOB_TBL"], bytes(sim.e.job))
    enter(m, sym, "LOAD_STATE")

    for slot in off:
        m.poke(sym["WH_ON"] + slot, 0)
    if move_n is not None:
        m.poke(sym["WH_MOVE_N"], move_n)
    if decay_n is not None:
        m.poke(sym["WH_DECAY_N"], decay_n)
    m.poke(sym["TICK_COUNT"], ticks & 0xFF)
    m.poke(sym["TICK_COUNT"] + 1, ticks >> 8)
    frames = enter(m, sym, "RUN_TICKS")

    enter(m, sym, "SAVE_STATE")
    return (m.read_ram(STAGE_AG, 2048), m.read_ram(STAGE_OCC, 128), frames,
            m.read_ram(STAGE_DOME, 1536), m.read_ram(STAGE_STR, 512),
            m.read_ram(sym["G_ECON_STATE"], EC.ECON_BYTES),
            m.read_ram(sym["G_JOB_TBL"], EC.MAX_JOB * EC.JOB_REC))


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


def fresh(g, nexthop, src):
    """Αντίγραφο της αρχικής κατάστασης — ο Z80 και η αναφορά ξεκινούν ίδια."""
    s = E.Sim(g, nexthop, src.e.dist)
    s.a.from_bytes(src.a.to_bytes())
    s.occ = bytearray(src.occ)
    s.e.dome = bytearray(src.e.dome)
    s.e.struct = bytearray(src.e.struct)
    s.e.stock = list(src.e.stock)
    s.e.job = bytearray(src.e.job)
    for f in ("power_store", "power_cap", "power_prod", "power_use",
              "mach_power", "o2_prod", "o2_use", "acc_power", "acc_o2",
              "power_ok", "o2_ok", "prod_dome", "day", "wind", "sol",
              "frame", "rnd", "n_dome", "n_struct", "job_dome", "job_agent"):
        setattr(s.e, f, getattr(src.e, f))
    return s


def main():
    sym = build()
    g = G.GRAPHS["colony"]()
    dist, nexthop = G.all_pairs(g)

    sim0 = E.populate(E.Sim(g, nexthop, dist))
    EC.populate(sim0.e)
    before = E.Agents().from_bytes(sim0.a.to_bytes())

    got_a, got_occ, frames, got_dome, got_str, got_econ, got_job = \
        run_z80(sym, g, fresh(g, nexthop, sim0), TICKS)

    sim = fresh(g, nexthop, sim0)
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

    # --- η οικονομία ---
    if got_dome != bytes(sim.e.dome) or got_str != bytes(sim.e.struct):
        n = sum(1 for i in range(1536) if got_dome[i] != sim.e.dome[i])
        print(f"ΑΠΟΤΥΧΙΑ πίνακες: {n} bytes θόλων διαφέρουν")
        return 1
    if got_job != bytes(sim.e.job):
        bad = [j for j in range(EC.MAX_JOB)
               if got_job[j*5:j*5+5] != sim.e.job[j*5:j*5+5]]
        print(f"ΑΠΟΤΥΧΙΑ πίνακας εργασιών: {len(bad)} εγγραφές διαφέρουν")
        for j in bad[:6]:
            print(f"    {j:2d}  Z80 {list(got_job[j*5:j*5+5])} != "
                  f"αναφορά {list(sim.e.job[j*5:j*5+5])}")
        return 1
    want_econ = EC.to_bytes(sim.e)
    if got_econ != want_econ:
        names = ([f"stock:{n}" for n in EC.STOCKS] +
                 ["power_store", "power_cap", "power_prod", "power_use",
                  "mach_power", "o2_prod", "o2_use", "acc_power", "acc_o2"])
        print("ΑΠΟΤΥΧΙΑ οικονομία:")
        for i, n in enumerate(names):
            gv = got_econ[i*2] | got_econ[i*2+1] << 8
            wv = want_econ[i*2] | want_econ[i*2+1] << 8
            if gv != wv:
                print(f"    {n:18s} Z80 {gv:6d} != αναφορά {wv:6d}")
        for j, n in enumerate(["power_ok", "o2_ok", "prod_dome", "day",
                               "wind", "sol"]):
            i = 46 + j
            if got_econ[i] != want_econ[i]:
                print(f"    {n:18s} Z80 {got_econ[i]:6d} != "
                      f"αναφορά {want_econ[i]:6d}")
        for n, i in (("frame", 52), ("rnd", 54)):
            gv = got_econ[i] | got_econ[i+1] << 8
            wv = want_econ[i] | want_econ[i+1] << 8
            if gv != wv:
                print(f"    {n:18s} Z80 {gv:6d} != αναφορά {wv:6d}")
        return 1

    # --- ο πίνακας εργασιών όντως δούλεψε; ---
    # Χωρίς αυτό, δύο άδειοι πίνακες συμφωνούν μια χαρά και δεν δοκιμάζεται
    # τίποτα: ούτε δημοσίευση, ούτε ανάθεση, ούτε ο κύκλος που κλείνει όταν
    # κάποιος φτάσει και ο θόλος αποκτήσει χειριστή.
    ag = E.Agents().from_bytes(got_a)
    open_jobs = sum(1 for j in range(EC.MAX_JOB)
                    if got_job[j * 5] != EC.NO_JOB)
    claimed = sum(1 for j in range(EC.MAX_JOB)
                  if got_job[j * 5] != EC.NO_JOB and got_job[j * 5 + 2] != 255)
    working = sum(1 for i in range(128) if ag.flags[i] & E.F_WORKING)
    tasked = sum(1 for i in range(128) if ag.task[i] != EC.NO_TASK)
    ops_now = sum(got_dome[d * EC.DOME_REC + EC.D_OPS] for d in range(64))
    ops_before = sum(sim0.e.dome[d * EC.DOME_REC + EC.D_OPS] for d in range(64))
    if working == 0 or open_jobs == 0:
        print(f"ΑΠΟΤΥΧΙΑ: ο πίνακας εργασιών δεν έκανε τίποτα — "
              f"{open_jobs} ανοιχτές, {working} στη δουλειά")
        return 1
    if ops_now <= ops_before:
        print(f"ΑΠΟΤΥΧΙΑ: οι χειριστές δεν αυξήθηκαν ({ops_before} -> "
              f"{ops_now}) — ο κύκλος δεν κλείνει")
        return 1
    print(f"OK εργασίες:  {open_jobs} ανοιχτές ({claimed} πιασμένες), "
          f"{tasked} πράκτορες σε αποστολή, {working} στη θέση τους")
    print(f"              χειριστές στους θόλους {ops_before} -> {ops_now}")

    e = sim.e
    produced = [EC.STOCKS[i] for i in range(EC.N_STOCK)
                if e.stock[i] != sim0.e.stock[i]]
    if len(produced) < 3:
        print(f"ΑΠΟΤΥΧΙΑ: η αλυσίδα δεν κινήθηκε — άλλαξαν μόνο {produced}")
        return 1
    print(f"OK οικονομία: {len(produced)} αποθέματα κινήθηκαν "
          f"({', '.join(produced[:6])}...)")
    print(f"              ρεύμα {e.power_prod} παραγωγή / {e.power_use} χρήση, "
          f"μπαταρία {e.power_store}/{e.power_cap}, "
          f"{'ΟΚ' if e.power_ok else 'ΜΠΛΑΚΑΟΥΤ'}")
    print(f"              οξυγόνο {e.o2_prod}/{e.o2_use} "
          f"{'ΟΚ' if e.o2_ok else 'ΕΛΛΕΙΜΜΑ'}, sol {e.sol} "
          f"{'μέρα' if e.day else 'νύχτα'}, άνεμος {e.wind}")

    # --- κόστος ανά ΕΙΔΟΣ θέσης ---
    # Σβήνουμε μία κατηγορία τη φορά και κρατάμε τη διαφορά. Χωρίς αυτό η
    # «διανομή» φαίνεται να κοστίζει 967 us, που είναι στην πραγματικότητα η
    # οικονομία κρυμμένη μέσα της.
    def timed(off):
        return run_z80(sym, g, fresh(g, nexthop, sim0), TICKS,
                       off=off)[2] * FRAME_US

    REV = TICKS // 16
    t_all = frames * FRAME_US
    t1 = timed(tuple(range(8)))                       # χωρίς κίνηση
    t2 = timed(tuple(range(11)))                      # ούτε φθορά
    t3 = timed(tuple(range(12)))                      # ούτε παραγωγή
    t4 = timed(tuple(range(13)))                      # ούτε ισοζύγιο
    t45 = timed(tuple(range(14)))                     # ούτε εργασίες
    t5 = timed(tuple(range(16)))                      # τίποτα: μόνο διανομή

    move_us = (t_all - t1) / (REV * 8)
    decay_us = (t1 - t2) / (REV * 3)
    prod_us = (t2 - t3) / REV
    flow_us = (t3 - t4) / REV
    job_us = (t4 - t45) / REV
    event_us = (t45 - t5) / REV
    over_us = t5 / TICKS

    print(f"\nκόστος ανά θέση τροχού ({TICKS} θέσεις = {REV} περιστροφές):")
    rows = [("κίνηση", move_us, 1800, f"{E.WH_MOVE_N} πράκτορες"),
            ("φθορά", decay_us, 433, f"{E.WH_DECAY_N} πράκτορες"),
            ("παραγωγή", prod_us, 4000, f"{EC.PROD_DOMES} θόλοι"),
            ("ισοζύγιο", flow_us, 2000, "64 δομές + 128 πράκτορες"),
            ("εργασίες", job_us, 3000,
             f"{EC.JOB_SCAN} θόλοι, {EC.JOB_LOOK} πράκτορες"),
            ("συμβάντα", event_us, 500, "μία ζαριά")]
    for name, got, budget, what in rows:
        if got <= budget:
            mark = "OK   "
        elif got <= budget * 1.05:
            mark = "οριακά"
        else:
            mark = f"{got/budget:.1f}x  "
        print(f"  {name:9s} {got:7.0f} us  (προϋπ. {budget:5d})  {mark} {what}")
    print(f"  {'διανομή':9s} {over_us:7.0f} us  (κάθε frame)")

    worst_name, worst = max(((n, v) for n, v, _, _ in rows), key=lambda r: r[1])
    worst += over_us
    print(f"  χειρότερο frame: {worst:.0f} us ({worst_name}) από τα 19.968 "
          f"= {100*worst/FRAME_US:.0f}%")

    if worst > FRAME_US:
        print("ΑΠΟΤΥΧΙΑ: η πιο ακριβή θέση δεν χωράει σε ένα frame")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
