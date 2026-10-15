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
import ctypes, os, random, re, subprocess, sys, types

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


def run_z80(sym, g, sim, ticks, move_n=None, decay_n=None, off=(), pin=None,
            rt_n=None, patch=()):
    m = z80_load(sym, g, sim, rt_n, patch)
    for slot in off:
        m.poke(sym["WH_ON"] + slot, 0)
    if pin is not None:
        m.poke(sym["PIN_SLOT"], pin)
    if move_n is not None:
        m.poke(sym["WH_MOVE_N"], move_n)
    if decay_n is not None:
        m.poke(sym["WH_DECAY_N"], decay_n)
    m.poke(sym["TICK_COUNT"], ticks & 0xFF)
    m.poke(sym["TICK_COUNT"] + 1, ticks >> 8)
    frames = enter(m, sym, "RUN_TICKS")
    return z80_read(m, sym, frames)


def z80_read(m, sym, frames):
    """Ο,τι επιστρέφει το run_z80, από έναν Z80 που έτρεξε."""
    enter(m, sym, "SAVE_STATE")
    return (m.read_ram(STAGE_AG, 2048), m.read_ram(STAGE_OCC, 128), frames,
            m.read_ram(STAGE_DOME, 1536), m.read_ram(STAGE_STR, 32 * 8),
            m.read_ram(sym["G_ECON_STATE"], EC.ECON_BYTES) +
            m.read_ram(STAGE_OCC + EC.X_OFF, EC.X_N) +  # EC_X (βήμα 121)
            bytes([m.peek(sym["EC_FULL"]),              # η αποθήκη (βήμα 122)
                   m.peek(sym["EC_KEEP"]),              # το μέταλλο (βήμα 127)
                   m.peek(STAGE_OCC + EC.VIN_OFF)]),    # οι επισκέπτες μέσα (βήμα 136)
            m.read_ram(sym["G_JOB_TBL"], EC.MAX_JOB * EC.JOB_REC),
            m.read_ram(sym["G_ROOM_N"], 12) +
            m.read_ram(sym["G_ROOM_LIST"], 96))


def tick_us(m, sym):
    """Ενα frame του τροχού, μετρημένο ανά 10 us (βήμα 111): όσα run_frames
    μετρά το enter, εδώ με ακρίβεια."""
    m.poke(sym["TICK_COUNT"], 1)
    m.poke(sym["TICK_COUNT"] + 1, 0)
    m.poke(sym["DONE_FLAG"], 0)
    m.set_pc(sym["RUN_TICKS"])
    us = 0
    while m.peek(sym["DONE_FLAG"]) != 0x5A:
        m.run_us(10)
        us += 10
    return us


def z80_load(sym, g, sim, rt_n=None, patch=()):
    """Ο Z80 με την κατάσταση της αναφοράς φορτωμένη, πριν από το πρώτο frame."""
    from cpc import CPC
    m = CPC()
    m.run_frames(60)
    assert m.quickload(SNA, start=False), "quickload απέτυχε"

    m.write_ram(sym["G_NODE_ADJ"], bytes(g.adj))
    m.write_ram(sym["G_RT_NODES"], bytes(g.deg))
    # Ο γράφος της δοκιμής έχει μόνο θόλους (g.hw = 48), και αρκεί να
    # χτιστούν αυτές οι γραμμές. Οταν κάποιος πρέπει να πάει σε ΔΟΜΗ (κόμβος
    # 64 και πάνω), χτίζονται όλες: αλλιώς ο Z80 διαβάζει σκουπίδια εκεί που
    # η αναφορά ξέρει «απρόσιτο» (βήμα 38).
    m.poke(sym["RT_N"], g.hw if rt_n is None else rt_n)
    enter(m, sym, "BUILD_ROUTES")

    m.write_ram(STAGE_AG, sim.a.to_bytes())
    # Το πάνω μισό της σελίδας: τα σημάδια των φιγούρων μηδέν, και από το
    # βήμα 121 η ησυχία των καταστροφών στα άδεια των πρακτόρων 100-127.
    m.write_ram(STAGE_OCC, bytes(sim.occ[:128]) + EC.occ_hi(sim.e))
    m.write_ram(STAGE_DOME, bytes(sim.e.dome))
    m.write_ram(STAGE_STR, bytes(sim.e.struct))
    m.write_ram(sym["G_ECON_STATE"], EC.to_bytes(sim.e))   # τράπεζα 2, βασική
    m.write_ram(sym["G_JOB_TBL"], bytes(sim.e.job))
    m.write_ram(sym["G_ROOM_N"], bytes(sim.e.room_n))
    m.write_ram(sym["G_ROOM_LIST"], bytes(sim.e.room_list))
    m.poke(sym["EC_FULL"], sim.e.full)      # τράπεζα 0· το LOAD_STATE βάζει και
                                            # τον κώδικά του (ec_setfull, βήμα 122)
    m.poke(sym["EC_KEEP"], sim.e.keep)      # και του μετάλλου (βήμα 127)
    enter(m, sym, "LOAD_STATE")

    for at, v in patch:                     # τα αρνητικά: κώδικας αλλαγμένος
        m.poke(at, v)
    return m


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


def econ_bytes(e):
    """Η οικονομία όπως τη διαβάζει το run_z80: τα ECON_BYTES της τράπεζας 2,
    από το βήμα 121 τα έξι του EC_X (η ησυχία) στην τράπεζα 6, και από το 122
    το ec_full της τράπεζας 0, από το 127 και το ec_keep."""
    return EC.to_bytes(e) + EC.x_bytes(e) + bytes([e.full, e.keep, e.vin])


def fresh(g, nexthop, src):
    """Αντίγραφο της αρχικής κατάστασης — ο Z80 και η αναφορά ξεκινούν ίδια."""
    s = E.Sim(g, nexthop, src.e.dist)
    s.a.from_bytes(src.a.to_bytes())
    s.occ = bytearray(src.occ)
    s.e.dome = bytearray(src.e.dome)
    s.e.struct = bytearray(src.e.struct)
    s.e.stock = list(src.e.stock)
    s.e.job = bytearray(src.e.job)
    s.e.room_n = bytearray(src.e.room_n)
    s.e.room_list = bytearray(src.e.room_list)
    s.e.land = list(src.e.land)
    s.e.cargo = list(src.e.cargo)                       # βήμα 93
    for f in ("power_store", "power_cap", "power_prod", "power_use",
              "mach_power", "o2_prod", "o2_use", "acc_power", "acc_o2",
              "power_ok", "o2_ok", "prod_dome", "day", "wind", "sol",
              "frame", "rnd", "n_dome", "n_struct", "job_dome", "job_agent",
              "alive", "gameover", "gloom", "storm", "amenity",
              "sollen", "daylen", "prod_mask", "ship_state", "ship_kind",
              "ship_eta", "pop_cap", "pad_node", "milestones", "deaths_sol",
              "no_death_sols", "green_sols", "no_trade_sols", "traded",
              "meteor", "mcx", "mcy", "mrnd", "nbuild", "markup", "lands",
              "ldis", "lev", "full", "keep",
              "coins", "prestige", "goodwill", "visacc",     # βήμα 134
              "mcoins",                                     # βήμα 135
              "vin"):                                       # βήμα 136
        setattr(s.e, f, getattr(src.e, f))
    return s


def colony_graph():
    """Ο γράφος της αποικίας, και οι δομές της οικονομίας (64 + i, όσες βάζει
    το EC.populate) δεμένες σε θόλους. ΑΠΟ ΤΟ ΒΗΜΑ 95: ως τότε οι δομές του
    populate δεν υπήρχαν στον γράφο (το g_colony έχει τις δικές του στο 32-47),
    οπότε κανείς δεν έφτανε ποτέ σε ορυχείο — ούτε η Drill του 94, ούτε η Haul
    — και ό,τι γίνεται στην άφιξη εκεί δεν το έλεγχε τίποτα."""
    g = G.GRAPHS["colony"]()
    g.n = g.hw = EC.MAX_DOME + EC.MAX_STRUCT
    for i in range(EC.POP_STRUCT):
        g.link(EC.MAX_DOME + i, (i * 7) % EC.POP_DOME)
    return g


def main():
    sym = build()
    g = colony_graph()
    dist, nexthop = G.all_pairs(g)

    sim0 = E.Sim(g, nexthop, dist)
    EC.populate(sim0.e)
    E.populate(sim0)
    EC.rooms_rebuild(sim0.e, sim0.pc)
    # Sol 20 περιστροφών αντί για 750: τα ορόσημα του §10.2 μετριούνται σε
    # sols, και μια δοκιμή που θέλει πέντε δεν μπορεί να περιμένει 60.000
    # frames. Το μήκος είναι δεδομένο ακριβώς γι' αυτό.
    sim0.e.sollen, sim0.e.daylen = 320, 192
    before = E.Agents().from_bytes(sim0.a.to_bytes())

    # Ολες οι γραμμές του DIST (βήμα 91): οι νεογέννητοι του πλοίου είναι πια
    # άνθρωποι και ψάχνουν δουλειά από την πίστα (κόμβος 64 και πάνω). Ως το
    # 90 οι ταυτότητες 5, 21, 37, 53 έβγαιναν ρομπότ και δεν έψαχναν.
    got_a, got_occ, frames, got_dome, got_str, got_econ, got_job, got_room = \
        run_z80(sym, g, fresh(g, nexthop, sim0), TICKS,
                rt_n=EC.MAX_DOME + EC.MAX_STRUCT)

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
    if got_room != bytes(sim.e.room_n) + bytes(sim.e.room_list):
        print("ΑΠΟΤΥΧΙΑ ευρετήριο δωματίων:")
        print(f"    Z80      {list(got_room[:12])}")
        print(f"    αναφορά  {list(sim.e.room_n)}")
        return 1
    if got_job != bytes(sim.e.job):
        bad = [j for j in range(EC.MAX_JOB)
               if got_job[j*5:j*5+5] != sim.e.job[j*5:j*5+5]]
        print(f"ΑΠΟΤΥΧΙΑ πίνακας εργασιών: {len(bad)} εγγραφές διαφέρουν")
        for j in bad[:6]:
            print(f"    {j:2d}  Z80 {list(got_job[j*5:j*5+5])} != "
                  f"αναφορά {list(sim.e.job[j*5:j*5+5])}")
        return 1
    want_econ = econ_bytes(sim.e)
    if got_econ != want_econ:
        # Η διάταξη περιγράφεται μία φορά, εδώ, και ακολουθεί την to_bytes.
        w16 = [f"stock:{n}" for n in EC.STOCKS] + [
            "power_store", "power_cap", "power_prod", "power_use",
            "mach_power", "o2_prod", "o2_use", "acc_power", "acc_o2"]
        groups = [(0, 2, w16),
                  (46, 1, ["power_ok", "o2_ok", "prod_dome", "day", "wind",
                           "sol"]),
                  (52, 2, ["frame", "rnd"]),
                  (56, 1, ["job_dome", "job_agent", "alive", "gameover",
                           "gloom", "storm", "amenity", "pad"]),
                  (64, 2, ["sollen", "daylen", "prod_mask", "ship_eta"]),
                  (72, 1, ["ship_state", "ship_kind", "pop_cap", "milestones",
                           "deaths_sol", "no_death_sols", "green_sols",
                           "no_trade_sols", "traded", "pad_node"]),
                  (108, 1, ["ldis_sol"]), (109, 2, ["ldis_frame"]),   # βήμα 121
                  (111, 1, ["lev_sol"]), (112, 2, ["lev_frame"]),
                  (114, 1, ["full", "keep"])]                       # βήματα 122, 127
        print("ΑΠΟΤΥΧΙΑ οικονομία:")
        for base, width, names in groups:
            for j, n in enumerate(names):
                i = base + j * width
                gv = (got_econ[i] if width == 1
                      else got_econ[i] | got_econ[i + 1] << 8)
                wv = (want_econ[i] if width == 1
                      else want_econ[i] | want_econ[i + 1] << 8)
                if gv != wv:
                    print(f"    {n:18s} Z80 {gv:6d} != αναφορά {wv:6d}")
        return 1

    # --- τα θερμοκήπια, οι θύελλες και οι βλάβες (§6.8, §6.10) ---
    #
    # Αυτά τρέχουν στην ΑΝΑΦΟΡΑ: μόλις αποδείχθηκε ότι ο Z80 βγάζει τα ίδια
    # bytes, οπότε ό,τι ισχύει για τη μία ισχύει και για τον άλλον. Και έτσι
    # μπορούν να παρακολουθηθούν μεταβάσεις μέσα στο τρέξιμο, που ένα
    # στιγμιότυπο στο τέλος δεν τις δείχνει.
    # Τετραπλάσιο παράθυρο: η βλάβη ρίχνεται μία στις 32 περιστροφές και η
    # έκλαμψη μία στις 256, οπότε σαράντα περιστροφές τις χάνουν συχνά. Ο
    # κώδικας είναι ο ίδιος που μόλις αποδείχθηκε ταυτόσημος με τον Z80.
    # ΟΚΤΑΠΛΑΣΙΟ από το βήμα 120: η βλάβη είναι 1/256 (η απόφαση του χρήστη),
    # και στις 160 περιστροφές του τετραπλάσιου δεν έπεφτε καμία.
    HAZ = TICKS * 8
    broke = repaired = storm_revs = 0
    landings = crew_landed = 0
    was_landed = False
    watch = fresh(g, nexthop, sim0)
    # ΜΙΑ ΒΛΑΒΗ ΣΤΗΝ ΠΡΩΤΗ ΖΑΡΙΑ (βήμα 121). Με 1/256 ανά περιστροφή και το
    # κενό FAULT_GAP οι 320 περιστροφές του παραθύρου τη χάνουν συχνά, και ως
    # το 120 τη βρίσκαν από τύχη. Ο σπόρος διαλέγεται ώστε η πρώτη ζαριά της
    # θέσης 15 να σταματήσει μια μηχανή που δουλεύει: ο κύκλος του §6.10 —
    # βλάβη, επισκευή με ανταλλακτικό — κλείνει μέσα στο παράθυρο.
    def first_fault(x):
        r1 = EC.lfsr(x)
        r3 = EC.lfsr(EC.lfsr(r1))
        if r3 & 0x7F or r1 & 1:
            return False
        e = fresh(g, nexthop, sim0).e
        before = bytes(e.dome)
        EC.break_one(e, r3 >> 7)
        return bytes(e.dome) != before
    hz_seed = next(x for x in range(1, 65536) if first_fault(x))
    watch.e.rnd = hz_seed
    head_before = sum(1 for i in range(128) if watch.a.flags[i] & E.F_ALIVE)
    prev = bytes(watch.e.dome)
    for _ in range(HAZ):
        watch.tick()
        now = bytes(watch.e.dome)
        for d in range(EC.MAX_DOME):
            for sl in range(EC.MACH_SLOTS):
                k = d * EC.DOME_REC + EC.D_HEALTH + sl
                if prev[k] and not now[k]:
                    broke += 1
                elif not prev[k] and now[k]:
                    repaired += 1
        if watch.e.storm:
            storm_revs += 1
        # Η άφιξη πιάνεται ΤΗ ΣΤΙΓΜΗ που γίνεται. «Ηταν νεκρός, τώρα ζει» δεν
        # δουλεύει: οι καινούργιοι παίρνουν τις ταυτότητες όσων πέθαναν.
        head = sum(1 for i in range(128) if watch.a.flags[i] & E.F_ALIVE)
        if watch.e.ship_state == EC.SHIP_LANDED and not was_landed:
            if watch.e.ship_kind == EC.SK_COLONIST:
                crew_landed += head - head_before
            landings += 1
        was_landed = watch.e.ship_state == EC.SHIP_LANDED
        head_before = head
        prev = now

    # Το θερμοκήπιο συνεισφέρει; Το ίδιο τρέξιμο με άδειες γλάστρες.
    bare = fresh(g, nexthop, sim0)
    bare.e.rnd = hz_seed
    for d in range(EC.MAX_DOME):
        b = d * EC.DOME_REC
        if bare.e.dome[b + EC.D_ROOM] == EC.R_GREENHOUSE:
            for sl in range(EC.MACH_SLOTS):
                bare.e.dome[b + EC.D_MACH + sl] = EC.NO_MACH
    EC.rooms_rebuild(bare.e, bare.pc)
    for _ in range(HAZ):
        bare.tick()

    grown = watch.e.stock[EC.S_STARCH] - bare.e.stock[EC.S_STARCH]
    if grown <= 0:
        print(f"ΑΠΟΤΥΧΙΑ: τα θερμοκήπια δεν παρήγαγαν τίποτα "
              f"({watch.e.stock[EC.S_STARCH]} με φυτά, "
              f"{bare.e.stock[EC.S_STARCH]} χωρίς)")
        return 1
    if broke == 0 or repaired == 0:
        print(f"ΑΠΟΤΥΧΙΑ: {broke} βλάβες, {repaired} επισκευές — "
              f"ο κύκλος του §6.10 δεν έκλεισε")
        return 1
    if storm_revs == 0 or got_econ[61] != 0:
        print(f"ΑΠΟΤΥΧΙΑ: η αμμοθύελλα δεν έτρεξε ({storm_revs} περιστροφές, "
              f"υπόλοιπο {got_econ[61]})")
        return 1
    if got_econ[62] == 0:
        print("ΑΠΟΤΥΧΙΑ: καμία παρηγοριά — δέντρα και σαλόνια δεν μετρήθηκαν")
        return 1
    print(f"OK χλωρίδα:  +{grown} άμυλο από τα θερμοκήπια σε {HAZ} frames, "
          f"παρηγοριά {got_econ[62]}")
    print(f"OK κίνδυνοι: {storm_revs} frames αμμοθύελλας, {broke} βλάβες, "
          f"{repaired} επισκευές με ανταλλακτικό")

    # --- πλοία, εμπόριο, ορόσημα (§6.11, §10.2) ---
    if landings == 0 or crew_landed <= 0:
        print(f"ΑΠΟΤΥΧΙΑ πλοία: {landings} προσγειώσεις, {crew_landed} άποικοι")
        return 1

    # Τα ορόσημα μετριούνται σε sols· τα βλέπουμε στο μακρύ παράθυρο.
    mile = watch.e.milestones
    want_bits = EC.M_FOOTHOLD | EC.M_INDUSTRY | EC.M_INDEPENDENCE
    if mile & want_bits != want_bits:
        print(f"ΑΠΟΤΥΧΙΑ ορόσημα: {mile:05b} — λείπουν "
              f"{(want_bits & ~mile):05b} μετά από {watch.e.sol} sols")
        return 1

    # Το εμπόριο είναι πράξη του παίκτη: εδώ ο μηχανισμός της αναφοράς (βήμα
    # 93· η γραμμή και ο Z80 στο tests/test_trade.py). Τέσσερα μέταλλα με 40%
    # είναι 4 x 21 = 84, και εννιά μεταλλεύματα 90: γίνεται, και από το βήμα
    # 98 όπως τα εργοτάξια — τα 9 φεύγουν, ένα φορτίο για τον έμπορο, τα 4
    # μένουν στο πλοίο του, δύο J_TRADE, και ο έμπορος περιμένει.
    tr = fresh(g, nexthop, sim0)
    tr.e.ship_state, tr.e.ship_kind = EC.SHIP_LANDED, EC.SK_MERCHANT
    tr.e.markup, tr.e.cargo = 40, [EC.S_METAL, 10] + [0] * 6
    tr.e.stock[EC.S_ORE] = 50
    tr.e.no_trade_sols = 9
    before_metal = tr.e.stock[EC.S_METAL]
    net = [0] * EC.N_STOCK
    net[EC.S_METAL], net[EC.S_ORE] = 4, -8
    if EC.trade(tr.e, net):
        print("ΑΠΟΤΥΧΙΑ: η ανταλλαγή έγινε με 80 για 84")
        return 1
    net[EC.S_ORE] = -9
    if not EC.trade(tr.e, net):
        print("ΑΠΟΤΥΧΙΑ: η ανταλλαγή με τον έμπορο δεν έγινε")
        return 1
    tj = [tr.e.job[b:b + EC.JOB_REC] for b in range(0, EC.MAX_JOB * EC.JOB_REC, EC.JOB_REC)
          if tr.e.job[b + EC.J_KIND] == EC.J_TRADE]
    if (tr.e.stock[EC.S_METAL] != before_metal or tr.e.stock[EC.S_ORE] != 41
            or not tr.e.traded or tr.e.ship_state != EC.SHIP_LANDED
            or tr.e.ship_kind != EC.SK_DEALT or tr.e.ship_eta != 0xFFFF or tr.e.markup != 1
            or tr.e.cargo != [EC.S_METAL, 4] + [0] * 6
            or [list(j) for j in tj] != [[EC.J_TRADE, tr.e.pad_node, 255, 4, 0]] * 2):
        print("ΑΠΟΤΥΧΙΑ: η ανταλλαγή δεν έγινε όπως τα εργοτάξια (βήμα 98): μέταλλο "
              f"{tr.e.stock[EC.S_METAL] - before_metal:+}, μετάλλευμα {tr.e.stock[EC.S_ORE]}, "
              f"πλοίο {tr.e.ship_state}/{tr.e.ship_kind}/{tr.e.ship_eta:#x}, χρωστιούνται "
              f"{tr.e.markup}, φορτίο του {tr.e.cargo}, J_TRADE {[list(j) for j in tj]}")
        return 1
    print(f"OK πλοία:    {landings} προσγειώσεις, {crew_landed} άποικοι στην "
          f"πίστα (κόμβος {got_econ[81]}), ταβάνι {got_econ[74]}")
    print(f"OK ορόσημα:  {mile:05b} μετά από {watch.e.sol} sols "
          f"— εμπόριο δοκιμασμένο, το σερί έσπασε")

    # --- οι ανάγκες όντως δάγκωσαν; ---
    ag0 = E.Agents().from_bytes(sim0.a.to_bytes())
    agz = E.Agents().from_bytes(got_a)
    # Οι ζωντανοί της θέσης 12 είναι οι 80 των αποίκων (βήμα 92, en_count).
    alive0 = sum(1 for i in range(EC.AG_BOT0) if ag0.flags[i] & E.F_ALIVE)
    alive1 = sum(1 for i in range(EC.AG_BOT0) if agz.flags[i] & E.F_ALIVE)
    # ΚΑΙ ΟΙ ΘΕΣΕΙΣ 80-95 ΔΕΝ ΕΧΟΥΝ ΑΝΑΓΚΕΣ (βήμα 92). Ο πληθυσμός της δοκιμής
    # τις γεμίζει με κάθε ρόλο, κι όμως σε 640 frames κανενός δεν άλλαξε ούτε
    # οξυγόνο ούτε νερό ούτε τροφή ούτε ύπνος — ενώ κάτω από το 80 τρώνε και
    # κοιμούνται (πιο κάτω). Ως το 91 τους επισκεπτόταν το πέρασμα των αναγκών.
    botz = range(EC.AG_BOT0, EC.AG_BOT0 + EC.AG_NBOT)
    moved = [i for i in botz if ag0.flags[i] & E.F_ALIVE and any(
        getattr(agz, f)[i] != getattr(ag0, f)[i] for f in ("o2", "water", "food", "sleep"))]
    nbots = sum(1 for i in botz if ag0.flags[i] & E.F_ALIVE)
    if moved or nbots < 8:
        print(f"ΑΠΟΤΥΧΙΑ: οι θέσεις των ρομπότ ({nbots} ζωντανοί) άλλαξαν ανάγκες: {moved[:8]}")
        return 1
    print(f"OK ρομπότ:   {nbots} ζωντανοί στις θέσεις 80-95, καμία ανάγκη τους δεν άλλαξε")
    fed = sum(1 for i in range(128) if agz.food[i] > ag0.food[i])
    slept = sum(1 for i in range(128) if agz.sleep[i] > ag0.sleep[i])
    healed = sum(1 for i in range(128) if agz.health[i] > ag0.health[i])
    seeking = sum(1 for i in range(128)
                  if agz.flags[i] & E.F_ALIVE and agz.dest[i] != agz.node[i])
    gloom = got_econ[60]
    for what, n in (("θάνατοι", alive0 - alive1), ("φαγητό", fed),
                    ("ύπνος", slept), ("ίαση", healed), ("μετακίνηση", seeking)):
        if n == 0:
            print(f"ΑΠΟΤΥΧΙΑ: καμία {what} σε {TICKS} frames — "
                  f"η διαδρομή δεν εκτελέστηκε ποτέ")
            return 1
    if gloom == 0:
        print("ΑΠΟΤΥΧΙΑ: κανένα πένθος, άρα κανένας θάνατος δεν καταγράφηκε")
        return 1
    if got_econ[58] != alive1:
        print(f"ΑΠΟΤΥΧΙΑ: το econ λέει {got_econ[58]} ζωντανούς, "
              f"οι πράκτορες λένε {alive1}")
        return 1
    print(f"OK ανάγκες:   {alive0} -> {alive1} ζωντανοί, {fed} έφαγαν, "
          f"{slept} κοιμήθηκαν, {healed} γιατρεύτηκαν")
    print(f"              {seeking} σε μετακίνηση για ανάγκη, πένθος {gloom}")

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
          f"{('ΜΠΛΑΚΑΟΥΤ', 'ΟΚ', 'ΠΕΣΜΕΝΟ ΦΟΡΤΙΟ')[e.power_ok]}")
    print(f"              οξυγόνο {e.o2_prod}/{e.o2_use} "
          f"{'ΟΚ' if e.o2_ok else 'ΕΛΛΕΙΜΜΑ'}, sol {e.sol} "
          f"{'μέρα' if e.day else 'νύχτα'}, άνεμος {e.wind}")

    # --- ο k-οστός χειριστής, όχι η υποδοχή k (βήμα 45) ---
    if ordinal():
        return 1

    # --- κάθε κλάδος του ισοζυγίου, Z80 απέναντι στην αναφορά (βήμα 46) ---
    if flow_branches(sym, g, nexthop, sim0):
        return 1

    # --- η βροχή μετεωριτών (§6.10, src/meteor.asm) ---
    if meteors(sym, g, nexthop, sim0):
        return 1

    # --- πρώτα τα υλικά, μετά ο μηχανικός (βήμα 88, src/supply.asm) ---
    if supply(sym, g, nexthop, sim0):
        return 1

    # --- τα αγαθά του εμπόρου κουβαλιούνται (βήμα 98, src/carry.asm) ---
    if carry(sym, g, nexthop, sim0):
        return 1

    # --- οι μηχανές κουβαλιούνται και στήνονται (βήμα 99, src/install.asm) ---
    if machines(sym, g, nexthop, sim0):
        return 1

    # --- κάθε ζαριά της θέσης 15, στημένη (βήμα 46) ---
    if event_branches(sym, g, nexthop, sim0):
        return 1

    # --- η ησυχία των καταστροφών και το κενό των βλαβών (βήμα 121) ---
    if calm_branches(sym, g, nexthop, sim0):
        return 1

    # --- η χωρητικότητα των αποθηκών (βήμα 122) ---
    if store_branches(sym, g, nexthop, sim0):
        return 1

    # --- το απόθεμα μετάλλου (βήμα 127) ---
    if keep_branches(sym, g, nexthop, sim0):
        return 1

    # --- οι ανάγκες στα όριά τους (βήμα 53) ---
    if need_branches(sym, g, nexthop, sim0):
        return 1

    # --- πλοία, σερί και ορόσημα στα όριά τους (βήμα 57) ---
    if ship_branches(sym, g, nexthop, sim0):
        return 1

    # --- η μάχη με τους εισβολείς (βήμα 111) ---
    if foe_battle(sym, g, nexthop, sim0):
        return 1

    # --- η κίνηση στα όριά της (βήμα 59) ---
    if move_check(sym, sim0):
        return 1

    # --- κόστος ανά θέση, μετρημένο ΚΑΤΕΥΘΕΙΑΝ ---
    # Ο τροχός καρφώνεται σε μία θέση και τρέχει PIN_TICKS φορές. Η παλιότερη
    # μέθοδος — τρέξε τα πάντα, μετά σβήσε ένα, κράτα τη διαφορά — έπαψε να
    # ισχύει μόλις τα περάσματα άρχισαν να αλληλοεξαρτώνται.
    PIN_TICKS = 200

    def pinned(slot):
        fr = run_z80(sym, g, fresh(g, nexthop, sim0), PIN_TICKS, pin=slot)[2]
        return fr * FRAME_US / PIN_TICKS

    rows = [("κίνηση", pinned(0), 1800, f"{E.WH_MOVE_N} πράκτορες"),
            ("ανάγκες", pinned(8), 433, f"{E.WH_NEED_N} άποικοι"),
            ("παραγωγή", pinned(11), 4000, f"{EC.PROD_DOMES} θόλοι"),
            ("ισοζύγιο", pinned(12), 2000, "64 δομές + 128 πράκτορες"),
            ("εργασίες", pinned(13), 3000,
             f"{EC.JOB_SCAN} θόλοι, {EC.JOB_LOOK} πράκτορες"),
            ("δωμάτια", pinned(14), 0, "64 θόλοι — η θέση 14 δεν είχε προϋπολογισμό"),
            ("συμβάντα", pinned(15), 500, "μία ζαριά")]

    print(f"\nκόστος ανά θέση τροχού (καρφωμένος τροχός, {PIN_TICKS} κλήσεις):")
    for name, got, budget, what in rows:
        if budget == 0:
            mark = "  —  "
        elif got <= budget:
            mark = "OK   "
        elif got <= budget * 1.05:
            mark = "οριακά"
        else:
            mark = f"{got/budget:.1f}x  "
        print(f"  {name:9s} {got:7.0f} us  (προϋπ. {budget:5d})  {mark} {what}")

    total = frames * FRAME_US / (TICKS // 16)
    print(f"  ολόκληρη περιστροφή: {total:.0f} us σε 16 frames "
          f"({100*total/(16*FRAME_US):.0f}% της συνολικής CPU)")

    worst_name, worst = max(((n, v) for n, v, _, _ in rows), key=lambda r: r[1])
    print(f"  χειρότερο frame: {worst:.0f} us ({worst_name}) από τα 19.968 "
          f"= {100*worst/FRAME_US:.0f}%")

    if worst > FRAME_US:
        print("ΑΠΟΤΥΧΙΑ: η πιο ακριβή θέση δεν χωράει σε ένα frame")
        return 1
    return 0


def ordinal():
    """Ο ΧΕΙΡΙΣΤΗΣ ΠΑΕΙ ΣΤΗ ΜΗΧΑΝΗ, ΟΧΙ ΣΤΗΝ ΥΠΟΔΟΧΗ (βήμα 45).

    Με τον εξοπλισμό του παίκτη (src/fit.asm) μια μηχανή μπορεί να κάθεται
    στην υποδοχή 3 με τις 0-2 άδειες. Ο κανόνας ως τότε (υποδοχή < χειριστές)
    την ήθελε με ΤΕΣΣΕΡΙΣ ανθρώπους μέσα· ένας θόλος με έναν χειριστή και
    μία μηχανή στη «λάθος» θέση δεν έβγαζε τίποτα. Τώρα μετράει η σειρά της
    ανάμεσα σε όσες θέλουν χειριστή.

    Μόνο η αναφορά εδώ: η ταυτότητα με τον Z80 πάνω σε αραιές υποδοχές
    ελέγχεται ήδη από το κοινό τρέξιμο — το populate αφήνει μία στις πέντε
    άδεια, με τυχαίους χειριστές.
    """
    def metal(ops):
        e = EC.Econ()
        e.stock[EC.S_ORE] = 100
        b = 0
        e.dome[b + EC.D_STATE], e.dome[b + EC.D_SIZE] = EC.DS_ACTIVE, 2
        e.dome[b + EC.D_ROOM], e.dome[b + EC.D_OPS] = EC.R_FACTORY, ops
        for sl in range(EC.MACH_SLOTS):
            e.dome[b + EC.D_MACH + sl] = EC.NO_MACH
        for sl in (3, 6):                        # δύο σίδερα, με τρύπες πριν
            e.dome[b + EC.D_MACH + sl] = 1
            e.dome[b + EC.D_HEALTH + sl] = 200
        EC.run_dome(e, 0)
        return e.stock[EC.S_METAL]
    got = [metal(k) for k in (0, 1, 2, 3)]
    q = EC.RECIPE[1][7]                         # ανά σίδερο: 2 από το βήμα 125, ως τότε 1
    want = [0, q, 2 * q, 2 * q]
    if got != want:
        print(f"ΑΠΟΤΥΧΙΑ χειριστές: σίδερο στις υποδοχές 3 και 6 με 0-3 "
              f"χειριστές έβγαλε {got}, περίμενα {want} (ο κανόνας "
              f"«υποδοχή < χειριστές» θα έδινε [0, 0, 0, 0])")
        return 1
    print(f"OK χειριστές: σίδερο στις υποδοχές 3 και 6 — με 0-3 χειριστές "
          f"βγάζει {got}: μετράει η σειρά της μηχανής, όχι η υποδοχή")
    return 0


# Οι κλάδοι του ισοζυγίου. Το κοινό τρέξιμο περνά από όποιον κλάδο τύχει (στο
# τέλος του: 90 παραγωγή, 28 χρήση), και κανείς δεν έλεγχε ποιους — ενώ το
# βήμα 46 ξανάγραψε το έλλειμμα, το ρίξιμο φορτίου και το μπλακάουτ. Εδώ
# στήνεται ο καθένας.
# Δομές: ηλιακός L, ανεμογεννήτριες S/M/L, συλλέκτης M, αντλία S, ορυχείο. Με
# άνεμο 2 η παραγωγή είναι 18 + (2 + 8 + 18) = 46 τη μέρα, η ζήτηση
# μηχανές + 1 + 8, το ταβάνι 160.
#         όνομα                    μηχ  ζωή  μπατ  άνεμ μέρα θύελ
FLOW_CASES = (
    ("πλεόνασμα",                   5,   4, 100,   2,  1,  0),
    ("πλεόνασμα ως το ταβάνι",      5,   4, 150,   2,  1,  0),
    ("παραγωγή ίση με ζήτηση",     37,   4, 100,   2,  1,  0),
    ("έλλειμμα, η μπαταρία φτάνει", 60,   4, 100,   2,  1,  0),
    ("μπαταρία ΑΚΡΙΒΩΣ έλλειμμα + ρεζέρβα", 60, 4, 55, 2, 1, 0),
    ("μία μονάδα κάτω: ρίχνει φορτίο, φορτίζει", 60, 4, 54, 2, 1, 0),
    ("νύχτα: η ζωή από τη μπαταρία", 60,  20, 100,   1,  0,  0),
    ("νύχτα, άδεια μπαταρία: μπλακάουτ", 60, 20, 5,   1,  0,  0),
    ("θύελλα τη μέρα",             10,   4, 100,   2,  1, 20),
    ("άπνοια",                     10,   4, 100,   0,  1,  0),
    ("ανεμοθύελλα: 3 + 12 + 27",   10,   4, 100,   3,  0,  0),
)


def flow_branches(sym, g, nexthop, sim0, patch=(), quiet=False):
    """Μία πυροδότηση του econ_flow ανά περίπτωση, και ΟΛΟ το econ_state
    απέναντι στο flow_balance της αναφοράς. Επιστρέφει πόσες διέφεραν."""
    from cpc import CPC
    kinds = ((EC.K_SOLAR, 2), (EC.K_TURBINE, 0), (EC.K_TURBINE, 1),
             (EC.K_TURBINE, 2), (EC.K_COLLECTOR, 1), (EC.K_EXTRACTOR, 0),
             (EC.K_MINE, 0))
    bad = []
    for name, mach, ess, store, wind, day, storm in FLOW_CASES:
        sim = fresh(g, nexthop, sim0)
        e = sim.e
        e.struct = bytearray(EC.MAX_STRUCT * EC.STRUCT_REC)
        for k, (kind, size) in enumerate(kinds):
            b = k * EC.STRUCT_REC
            e.struct[b + EC.ST_KIND], e.struct[b + EC.ST_SIZE] = kind, size
            e.struct[b + EC.ST_STATE], e.struct[b + EC.ST_INTEG] = EC.DS_ACTIVE, 255
        e.n_struct = len(kinds)
        e.mach_power, e.ess_power, e.power_store = mach, ess, store
        e.wind, e.day, e.storm = wind, day, storm
        e.flow_div = 1

        m = CPC()
        m.run_frames(60)
        assert m.quickload(SNA, start=False), "quickload απέτυχε"
        m.write_ram(STAGE_AG, sim.a.to_bytes())
        m.write_ram(STAGE_OCC, bytes(sim.occ) + bytes(128))
        m.write_ram(STAGE_DOME, bytes(e.dome))
        m.write_ram(STAGE_STR, bytes(e.struct))
        m.write_ram(sym["G_ECON_STATE"], EC.to_bytes(e))
        enter(m, sym, "LOAD_STATE")
        for at, v in patch:
            m.poke(at, v)
        m.poke(sym["EC_FDIV"], 1)
        code = [0xF3, 0x31, 0x00, 0x01,                  # di / ld sp,#0100
                0x01, 0xC6, 0x7F, 0xED, 0x49,            # τράπεζα 6
                0xCD, sym["ECON_FLOW"] & 0xFF, sym["ECON_FLOW"] >> 8,
                0x3E, 0x5A, 0x32, sym["DONE_FLAG"] & 0xFF, sym["DONE_FLAG"] >> 8,
                0x18, 0xFE]
        m.write_ram(0xE000, bytes(code))
        m.poke(sym["DONE_FLAG"], 0)
        m.set_pc(0xE000)
        for _ in range(50):
            if m.peek(sym["DONE_FLAG"]) == 0x5A:
                break
            m.run_frames(1)
        got = m.read_ram(sym["G_ECON_STATE"], EC.ECON_BYTES)

        alive = sum(1 for i in range(EC.AG_BOT0) if sim.a.flags[i] & E.F_ALIVE)
        inside = sum(1 for i in range(EC.AG_BOT0)
                     if sim.a.flags[i] & E.F_ALIVE and sim.a.flags[i] & E.F_INDOORS)
        EC.flow_balance(e, alive, inside)
        want = EC.to_bytes(e)
        if got != want:
            diff = [k for k in range(len(want)) if got[k] != want[k]]
            bad.append(name)
            if not quiet:
                print(f"ΑΠΟΤΥΧΙΑ ισοζύγιο «{name}»: bytes {diff[:6]} — Z80 "
                      f"{[got[k] for k in diff[:6]]}, αναφορά "
                      f"{[want[k] for k in diff[:6]]}")
    if quiet:
        return len(bad)
    if bad:
        return 1
    # ΑΡΝΗΤΙΚΟ: η ρεζέρβα κομμένη (τα `add hl,hl` του repeat σε nop) — οι
    # δύο περιπτώσεις του ορίου πρέπει να το δουν.
    at = sym["EF_BALANCE"]
    k = next(k for k in range(96)
             if [m.peek(at + k + j) for j in range(3)] == [0x29] * EC.RESERVE_SH)
    nbad = flow_branches(sym, g, nexthop, sim0, quiet=True,
                         patch=[(at + k + j, 0) for j in range(EC.RESERVE_SH)])
    if not nbad:
        print("ΑΠΟΤΥΧΙΑ: ΑΡΝΗΤΙΚΟ — χωρίς ρεζέρβα οι κλάδοι του ισοζυγίου "
              "βγαίνουν ίδιοι: η δοκιμή δεν έχει δόντια")
        return 1
    print(f"OK ισοζύγιο: {len(FLOW_CASES)} περιπτώσεις — πλεόνασμα, ταβάνι, "
          f"έλλειμμα και τα όριά του, ρίξιμο φορτίου, μπλακάουτ, θύελλα, άνεμος "
          f"0-3 — ίδια bytes στον Z80 και στην αναφορά. ΑΡΝΗΤΙΚΟ: χωρίς "
          f"ρεζέρβα διαφέρουν {nbad}")
    return 0


def event_branches(sym, g, nexthop, sim0):
    """Η γεννήτρια στημένη ώστε η ΠΡΩΤΗ ζαριά της θέσης 15 να ρίξει ό,τι
    σπάνια ρίχνει: έκλαμψη (1/2048 ανά περιστροφή), βλάβη (1/256 από το
    βήμα 120· 1/128 ως τότε), θύελλα,
    επισκέπτες. Το κοινό τρέξιμο είναι 40 περιστροφές και τα βλέπει, αν τα
    δει, από τύχη — και το βήμα 46 έκανε την έκλαμψη βρόχο από πίνακα."""
    base = fresh(g, nexthop, sim0)
    spread(base.e)
    EC.rooms_rebuild(base.e, base.pc)
    base.e.storm = 0

    def rolls(x):
        r1 = EC.lfsr(x)
        r2 = EC.lfsr(r1)
        return r1, r2, EC.lfsr(r2)

    def broken_by(x):
        """Πόσες γερές μηχανές θα σταματούσε η έκλαμψη του r3."""
        e = fresh(g, nexthop, base).e
        r3 = rolls(x)[2] & 63                   # οι στόχοι από τα έξι χαμηλά (βήμα 124)
        before = sum(1 for v in e.dome if v)
        for v in (r3 + 37, (r3 >> 3) + 101, (r3 >> 1) + 173):
            EC.break_one(e, v)
        return before - sum(1 for v in e.dome if v)

    def faulted(x):
        """Πόσες γερές μηχανές θα σταματούσε η βλάβη του r3, αν έπεφτε."""
        e = fresh(g, nexthop, base).e
        before = sum(1 for v in e.dome if v)
        EC.break_one(e, rolls(x)[2] >> 7)
        return before - sum(1 for v in e.dome if v)

    # Η ΒΛΑΒΗ ΔΥΟ ΦΟΡΕΣ από το βήμα 120: 1/256, τα χαμηλά επτά του r3 ΚΑΙ το
    # bit 0 του r1. Η δεύτερη έχει τα επτά μηδέν και το r1 περιττό, και θα
    # σταματούσε μια γερή μηχανή αν το bit δεν κοιταζόταν (το αρνητικό).
    # Από το βήμα 121 η έκλαμψη θέλει και μία περιστροφή στις τέσσερις του
    # ρολογιού (το frame της στημένης κατάστασης) και η θύελλα 1/2048, και οι
    # (βήμα 124: θύελλα r2 >= #FFE0, έκλαμψη r3 >= #FFC0, όχι τα μικρά r2, r3),
    # δύο ΟΧΙ μέσα στην ησυχία: η αποικία της δοκιμής έχει 80 ζωντανούς, και
    # το calm και το fgap ξεκινούν από μηδέν (calm_branches για τα όρια).
    cases = (
        ("έκλαμψη", lambda r1, r2, r3: r3 >= 0xFFC0 and r2 < 0xFFE0),   # όχι θύελλα πρώτα
        ("βλάβη", lambda r1, r2, r3: r3 & 0x7F == 0 and r3 >> 8 and not r1 & 1),
        ("βλάβη που κόβει το r1", lambda r1, r2, r3: r3 & 0x7F == 0 and r3 >> 8 and r1 & 1),
        ("θύελλα", lambda r1, r2, r3: r2 >= 0xFFE0),
        ("επισκέπτες", lambda r1, r2, r3: r2 & 0x7FF == 0),
    )
    flare_x = cut_x = None
    for name, hit in cases:
        xs = [x for x in range(1, 65536) if hit(*rolls(x))]
        if name == "έκλαμψη":
            x = flare_x = max(xs, key=broken_by)
        elif name == "βλάβη που κόβει το r1":
            x = cut_x = max(xs, key=faulted)
        else:
            x = xs[0]
        st = fresh(g, nexthop, base)
        st.e.rnd = x
        # Η ζαριά βλέπει frame + 16: 64, μία περιστροφή στις τέσσερις (βήμα 121).
        st.e.frame = 48
        if same(sym, g, nexthop, st, 20, f"ζαριά: {name}") is None:
            return 1
    n = broken_by(flare_x)
    # ΑΡΝΗΤΙΚΟ: η πρώτη μετατόπιση της έκλαμψης 37 -> 38 στον πίνακα.
    st = fresh(g, nexthop, base)
    st.e.rnd, st.e.frame = flare_x, 48
    if n == 0 or same(sym, g, nexthop, st, 20, "", quiet=True,
                      patch=[(sym["EV_FL_TAB"] + 1, 38)]) is not None:
        print(f"ΑΠΟΤΥΧΙΑ ζαριά: η έκλαμψη σταμάτησε {n} μηχανές, και με "
              f"πειραγμένο πίνακα ο Z80 βγαίνει ακόμη ίδιος")
        return 1
    # ΑΡΝΗΤΙΚΟ (βήμα 120): το jr c μετά το rra του r1 γίνεται nop nop — η
    # βλάβη 1/128 όπως ως το 119.
    at = sym["EV_FAULT"]
    code = run_peek(sym, at, 32)
    k = next(j for j in range(28) if code[j] == 0x3A and code[j + 3] == 0x1F
             and code[j + 4] == 0x38)
    st = fresh(g, nexthop, base)
    st.e.rnd = cut_x
    if faulted(cut_x) == 0 or same(sym, g, nexthop, st, 20, "", quiet=True,
                                   patch=[(at + k + 4, 0), (at + k + 5, 0)]) is not None:
        print(f"ΑΠΟΤΥΧΙΑ ζαριά: χωρίς το bit του r1 η βλάβη ({faulted(cut_x)} "
              f"μηχανές) βγαίνει ακόμη ίδια με την αναφορά")
        return 1
    print(f"OK ζαριές:   έκλαμψη ({n} μηχανές σταμάτησαν), βλάβη, βλάβη που κόβει το "
          f"r1, θύελλα, επισκέπτες — ίδια bytes στον Z80 και στην αναφορά. ΑΡΝΗΤΙΚΑ: "
          f"με 37 -> 38 στον πίνακα της έκλαμψης, και χωρίς το bit του r1 στη "
          f"βλάβη, διαφέρουν")
    return 0


def calm_branches(sym, g, nexthop, sim0):
    """Η ΗΣΥΧΙΑ (βήμα 121, src/econ.asm): η θέση 15 καρφωμένη, με σπόρους που
    ρίχνουν θύελλα, έκλαμψη, βροχή μετεωριτών και βλάβη στην πρώτη ζαριά — με
    19 και με 20 ζωντανούς, ακριβώς στα δύο sol μετά την προηγούμενη
    καταστροφή και μία περιστροφή νωρίτερα, ακριβώς FAULT_GAP περιστροφές μετά
    από το τελευταίο γεγονός και μία νωρίτερα. Ολα τα bytes ίδια στον Z80 και
    στην αναφορά, και το αποτέλεσμα όπως το θέλει ο κανόνας. Μετά 12 sol ζαριών
    με 20 ζωντανούς: τα κενά."""
    base = fresh(g, nexthop, sim0)
    spread(base.e)
    EC.rooms_rebuild(base.e, base.pc)
    base.e.storm = 0
    # Το πραγματικό sol (12.000 frames, όχι 320): τα δύο sol και οι FAULT_GAP
    # περιστροφές (1.024 frames) θέλουν να χωρούν στο ίδιο ρολόι. Η ζαριά
    # βλέπει sol 1, frame 2.048: μία περιστροφή στις τέσσερις, για την έκλαμψη.
    base.e.sollen, base.e.daylen = EC.SOL_FRAMES, EC.DAY_FRAMES
    base.e.sol, base.e.frame = 1, 2032
    NOW = [1, 2048]
    keys = lambda z: (z.a.to_bytes(), bytes(z.e.dome), bytes(z.e.struct),
                      econ_bytes(z.e), bytes(z.e.job), bytes(z.occ[:128]))

    def z80(st, n, patch=()):
        got = run_z80(sym, g, fresh(g, nexthop, st), n, pin=15,
                      rt_n=EC.MAX_DOME + EC.MAX_STRUCT, patch=patch)
        return (got[0], got[3], got[4], got[5], got[6], got[1])

    def rolls(x):
        r1 = EC.lfsr(x)
        r2 = EC.lfsr(r1)
        return r1, r2, EC.lfsr(r2)

    def first(hit):
        return next(x for x in range(1, 65536) if hit(*rolls(x)))

    storm_x = first(lambda r1, r2, r3: r2 >= 0xFFE0 and (r3 & 0x7F or r1 & 1))
    flare_x = first(lambda r1, r2, r3: r3 >= 0xFFC0 and r2 < 0xFFE0)   # όχι θύελλα πρώτα
    # ΘΥΕΛΛΑ ΚΑΙ ΒΛΑΒΗ ΔΕΝ ΠΕΦΤΟΥΝ ΠΙΑ ΣΤΗΝ ΙΔΙΑ ΖΑΡΙΑ (βήμα 124): με r2 >= #FFE0
    # καμία από τις 65.535 θέσεις του Galois — και κάθε θύελλα του r2 < 32
    # είχε ζαριά βλάβης στις 64 περιστροφές πριν, και δεν περνούσε ποτέ.
    pos, x = [], 0xACE1
    for _ in range(65535):
        x = EC.lfsr(x)
        pos.append(x)
    both = sum(1 for i in range(65535) if pos[(i + 1) % 65535] >= 0xFFE0
               and not pos[(i + 2) % 65535] & 0x7F and not pos[i] & 1)
    gated = [any(not pos[(i - 3 * k + 2) % 65535] & 0x7F and not pos[(i - 3 * k) % 65535] & 1
                 for k in range(1, EC.FAULT_GAP + 1))
             for i in range(65535) if pos[(i + 1) % 65535] >= 0xFFE0]
    old = [any(not pos[(i - 3 * k + 2) % 65535] & 0x7F and not pos[(i - 3 * k) % 65535] & 1
               for k in range(1, EC.FAULT_GAP + 1))
           for i in range(65535) if pos[(i + 1) % 65535] < 32]
    if both or sum(gated) * 2 > len(gated) or not all(old):
        print(f"ΑΠΟΤΥΧΙΑ ησυχία: θύελλα και βλάβη μαζί σε {both} θέσεις· κομμένες από "
              f"βλάβη {sum(gated)} από {len(gated)} (r2 >= #FFE0), {sum(old)} από "
              f"{len(old)} (r2 < 32)")
        return 1
    rain_x = first(lambda r1, r2, r3: r1 >> 4 == 0xFFF)
    fault_x = first(lambda r1, r2, r3: not r3 & 0x7F and not r1 & 1 and r2 < 0xFFE0)
    N = [0, 0]                                  # ποτέ
    TWO = 2 * EC.SOL_FRAMES                     # 24.000 frames πριν: sol 255
    GAP = EC.FAULT_GAP * 16
    at = lambda back: [(NOW[0] * EC.SOL_FRAMES + NOW[1] - back) // EC.SOL_FRAMES & 255,
                       (NOW[0] * EC.SOL_FRAMES + NOW[1] - back) % EC.SOL_FRAMES]
    # (όνομα, σπόρος, ζωντανοί, ldis, lev, ό,τι πρέπει να ισχύει μετά)
    cases = (
        ("θύελλα, 20 ζωντανοί", storm_x, 20, N, N,
         lambda e: e.storm == EC.STORM_LEN and e.ldis == NOW and e.lev == NOW),
        ("θύελλα, 19 ζωντανοί", storm_x, 19, N, N,
         lambda e: e.storm == 0 and e.ldis == N),
        ("θύελλα ακριβώς δύο sol μετά", storm_x, 20, at(TWO), N,
         lambda e: e.storm == EC.STORM_LEN and e.ldis == NOW),
        ("θύελλα μία περιστροφή νωρίτερα", storm_x, 20, at(TWO - 16), N,
         lambda e: e.storm == 0 and e.ldis == at(TWO - 16)),
        ("θύελλα ακριβώς FAULT_GAP μετά από βλάβη", storm_x, 20, N, at(GAP),
         lambda e: e.storm == EC.STORM_LEN),
        ("θύελλα μία περιστροφή νωρίτερα από το κενό", storm_x, 20, N, at(GAP - 16),
         lambda e: e.storm == 0 and e.lev == at(GAP - 16)),
        ("έκλαμψη, 20 ζωντανοί", flare_x, 20, N, N, lambda e: e.ldis == NOW),
        ("έκλαμψη, 19 ζωντανοί", flare_x, 19, N, N, lambda e: e.ldis == N),
        ("βροχή, 20 ζωντανοί", rain_x, 20, N, N,
         lambda e: e.meteor == EC.METEOR_N and e.ldis == NOW),
        ("βροχή, 19 ζωντανοί", rain_x, 19, N, N, lambda e: e.meteor == 0),
        ("βροχή στην ησυχία", rain_x, 20, at(GAP), at(GAP),
         lambda e: e.meteor == 0 and e.ldis == at(GAP)),
        ("βλάβη, 3 ζωντανοί", fault_x, 3, N, N,
         lambda e: e.lev == NOW and e.ldis == N),
        ("βλάβη μία περιστροφή νωρίτερα", fault_x, 3, N, at(GAP - 16),
         lambda e: e.lev == at(GAP - 16)),
        ("βλάβη στο κενό μιας καταστροφής", fault_x, 20, at(GAP - 16), at(GAP - 16),
         lambda e: e.lev == at(GAP - 16)),
    )
    starts = {}
    for name, x, alive, ldis, lev, ok in cases:
        st = fresh(g, nexthop, base)
        st.e.rnd, st.e.alive, st.e.ldis, st.e.lev = x, alive, list(ldis), list(lev)
        want = fresh(g, nexthop, st)
        slot15(want, 1)
        if not ok(want.e):
            print(f"ΑΠΟΤΥΧΙΑ ησυχία: «{name}» — η αναφορά: θύελλα {want.e.storm}, "
                  f"βροχή {want.e.meteor}, ldis {want.e.ldis}, lev {want.e.lev}")
            return 1
        if z80(st, 1) != keys(want):
            print(f"ΑΠΟΤΥΧΙΑ ησυχία: «{name}» — ο Z80 διαφέρει από την αναφορά")
            return 1
        starts[name] = (st, keys(want))

    # 12 SOL ΖΑΡΙΩΝ: 9.000 περιστροφές με 20 ζωντανούς, ίδια bytes στο τέλος,
    # και στην αναφορά κάθε καταστροφή απέχει από την προηγούμενη τουλάχιστον
    # δύο sol, κάθε βλάβη τουλάχιστον FAULT_GAP περιστροφές από ό,τι έγινε πριν
    # ή μετά της.
    LONG = 9000
    st = fresh(g, nexthop, base)
    st.e.rnd, st.e.alive = 0xBEEF, 20
    sim = fresh(g, nexthop, st)
    t = lambda v: v[0] * EC.SOL_FRAMES + v[1]
    dis, faults = [], []
    for _ in range(LONG):
        d0, v0 = sim.e.ldis, sim.e.lev
        slot15(sim, 1)
        if sim.e.ldis != d0:
            dis.append(t(sim.e.ldis))
        elif sim.e.lev != v0:
            faults.append(t(sim.e.lev))
    want = keys(sim)
    if z80(st, LONG) != want:
        print(f"ΑΠΟΤΥΧΙΑ ησυχία: {LONG} περιστροφές — ο Z80 διαφέρει από την αναφορά")
        return 1
    gaps = [b - a for a, b in zip(dis, dis[1:])]
    events = sorted(dis + faults)
    near = [b for a, b in zip(events, events[1:]) if b - a < GAP]
    if len(dis) < 2 or min(gaps) < TWO or near:
        print(f"ΑΠΟΤΥΧΙΑ ησυχία: καταστροφές στα frames {dis}, κενά {gaps}, "
              f"γεγονότα πιο κοντά από {GAP} {near}")
        return 1
    print(f"OK ησυχία:   {len(cases)} ζαριές στα όρια — θύελλα, έκλαμψη και βροχή με "
          f"20 ζωντανούς και όχι με 19, ακριβώς δύο sol μετά την προηγούμενη και όχι "
          f"μία περιστροφή νωρίτερα, ακριβώς {EC.FAULT_GAP} περιστροφές μετά από "
          f"βλάβη και όχι νωρίτερα, βλάβη και "
          f"με 3 ζωντανούς — ίδια bytes στον Z80 και στην αναφορά· {LONG} περιστροφές "
          f"ίδιες, {len(dis)} καταστροφές με κενά {min(gaps) / EC.SOL_FRAMES:.2f}-"
          f"{max(gaps) / EC.SOL_FRAMES:.2f} sol, {len(faults)} βλάβες, κανένα γεγονός "
          f"πιο κοντά από {EC.FAULT_GAP} περιστροφές· θύελλα και βλάβη ποτέ στην ίδια "
          f"ζαριά, και {sum(gated)} από τις {len(gated)} θύελλες του Galois κομμένες από "
          f"βλάβη (όλες οι {len(old)} με το r2 < 32 του 121)")

    # ΑΡΝΗΤΙΚΑ: ο Z80 πειραγμένος, η αναφορά όχι.
    def code_at(name, pat, span=64):
        a = sym[name]
        code = run_peek(sym, a, span)
        k = next((k for k in range(span - len(pat) + 1)
                  if code[k:k + len(pat)] == pat), None)
        return None if k is None else a + k
    may = sym["EV_MAY"]
    negs = []
    a = code_at("EV_MAY", [0xFE, EC.DIS_POP, 0xD8])
    negs.append(("καταστροφές από 19 ζωντανούς", "θύελλα, 19 ζωντανοί",
                 a and [(a + 1, 19)]))
    a = code_at("EV_MAY", [0xD8, 0xED, 0x42, 0xC9])
    negs.append(("ησυχία ενός sol", "θύελλα μία περιστροφή νωρίτερα",
                 a and [(a + 1, 0), (a + 2, 0)]))
    a = code_at("EV_FAULT", [0x01, GAP & 255, GAP >> 8])
    negs.append(("βλάβη χωρίς κενό", "βλάβη μία περιστροφή νωρίτερα",
                 a and [(a + 1, 0), (a + 2, 0)]))
    a = code_at("MT_TICK", [0xCD, may & 255, may >> 8, 0xD8])
    negs.append(("βροχή χωρίς ησυχία", "βροχή, 19 ζωντανοί", a and [(a + 3, 0)]))
    for what, case, patch in negs:
        st, want = starts[case]
        if not patch or z80(st, 1, patch=patch) == want:
            print(f"ΑΠΟΤΥΧΙΑ ησυχία: ΑΡΝΗΤΙΚΟ «{what}» — "
                  f"{'το μοτίβο δεν βρέθηκε' if not patch else 'ο Z80 βγαίνει ίδιος'}")
            return 1
    print(f"OK ησυχία:   ΑΡΝΗΤΙΚΑ — {', '.join(n for n, _, _ in negs)}: ο Z80 "
          f"διαφέρει από την αναφορά")
    return 0


# Ο κύκλος ροής της αποικίας της δοκιμής, το πρώτο frame μετά τη φόρτωση (το
# βαρύτερο): 8.360 us στο βήμα 121· το st_check του 122 +250 με τον θόλο M της,
# και 54 us κάθε θόλος Storage ακόμη (8.610 και 8.990). Βήμα 123: η μισή
# απόδοση εκτός φλέβας, ένα bit σε κάθε ορυχείο που σκάβει — δύο εδώ, +20.
# Βήμα 126: ο δεύτερος και ο τρίτος χαμηλά — το dr_post διαλέγει προτεραιότητα
# και bits, και το hl_pile κοιτάζει για άδειο ορυχείο με τη Drill του
# χαμηλά: 8.630 -> 8.670, 9.000 -> 9.050.
# Βήμα 127: το απόθεμα μετάλλου — το ec_keep στο st_check και η πρώτη
# κλήση εισόδου στο ec_setfull: 8.670 -> 8.710, 9.050 -> 9.090.
STORE_FLOW_US, STORE_FLOW8_US = 8720, 9100
# Οι βαριές επισκέψεις της θέσης 11 με το απόθεμα μετάλλου ενεργό (βήμα 127):
# το erm_ink περνά 5 us σε κάθε μηχανή που δεν τρώει μέταλλο, και οι τέσσερις
# που το τρώνε σταματούν. Εδώ 7.090 και 12.160 us, χωρίς το απόθεμα 8.390 και
# 12.520: φθηνότερο. Μια ομάδα θόλων χωρίς καμία τέτοια μηχανή θα πλήρωνε 5 us
# ανά μηχανή (DESIGN §6.5).
KEEP_SWEEP_US = 12170


def store_branches(sym, g, nexthop, sim0):
    """Η ΑΠΟΘΗΚΗ (βήμα 122): ο κύκλος ροής (θέση 12) στα όρια της
    χωρητικότητας — ένα λιγότερο, ακριβώς, πολύ πάνω· χωρίς τον θόλο Storage·
    με τον θόλο L — που ανάβει ή σβήνει το ec_full και σκάβει (ή όχι) στα
    ορυχεία· και μετά ένα ολόκληρο σάρωμα της παραγωγής (θέση 11 καρφωμένη,
    64 περιστροφές) με το ec_full όπως το άφησε. Ολα τα bytes ίδια στον Z80 και
    στην αναφορά. Γεμάτη: κανένα αγαθό δεν αλλάζει (ούτε φτιάχνεται ούτε
    τρώγεται) και ο σωρός δεν μεγαλώνει· αλλιώς φτιάχνονται."""
    base = fresh(g, nexthop, sim0)
    EC.rooms_rebuild(base.e, base.pc)
    keys = lambda z: (z.a.to_bytes(), bytes(z.e.dome), bytes(z.e.struct),
                      econ_bytes(z.e), bytes(z.e.job), bytes(z.occ[:128]))
    store = [base.e.room_list[EC.R_STORAGE * EC.ROOM_MAX + k]
             for k in range(base.e.room_n[EC.R_STORAGE])]
    if len(store) != 1:
        print(f"ΑΠΟΤΥΧΙΑ αποθήκη: η αποικία της δοκιμής έχει θόλους Storage {store}, όχι έναν")
        return 1
    sd = store[0] * EC.DOME_REC

    def cap(e):
        return EC.STORE_BASE + sum(
            EC.STORE_SIZE[e.dome[e.room_list[EC.R_STORAGE * EC.ROOM_MAX + k] * EC.DOME_REC
                                 + EC.D_SIZE]] for k in range(e.room_n[EC.R_STORAGE]))

    def total(e, n):
        """Τα όπλα (που καμία μηχανή δεν τρώει) ώστε το σύνολο να είναι n."""
        e.stock[EC.S_GUN] += n - sum(e.stock[1:])
        assert e.stock[EC.S_GUN] >= 0

    def no_store(e):
        e.dome[sd + EC.D_STATE] = EC.DS_BUILDING
        EC.rooms_rebuild(e, None)

    def large(e):
        e.dome[sd + EC.D_SIZE] = 2
    # (όνομα, πριν από τον κύκλο ροής, γεμάτη;)
    cases = (
        ("ένα λιγότερο", lambda e: total(e, cap(e) - 1), 0),
        ("ακριβώς γεμάτη", lambda e: total(e, cap(e)), 1),
        ("πολύ πάνω", lambda e: total(e, cap(e) + 700), 1),
        ("χωρίς θόλο Storage", lambda e: (no_store(e), total(e, 700)), 1),
        ("θόλος L, ένα λιγότερο", lambda e: (large(e), total(e, cap(e) - 1)), 0),
        ("θόλος L, ακριβώς", lambda e: (large(e), total(e, cap(e))), 1),
    )

    def z80(st, n, pin, patch=()):
        got = run_z80(sym, g, fresh(g, nexthop, st), n, pin=pin,
                      rt_n=EC.MAX_DOME + EC.MAX_STRUCT, patch=patch)
        return (got[0], got[3], got[4], got[5], got[6], got[1])

    def sweep(sim, n):
        for _ in range(n):
            EC.production_slice(sim.e, plant_class=sim.pc)

    def chain(st, patch=()):
        """Ο Z80: ένας κύκλος ροής (θέση 12) και μετά SWEEP κλήσεις της θέσης
        11, χωρίς να ξαναφορτωθεί — η παραγωγή ακούει τον κώδικα που άλλαξε
        το ec_setfull, όχι αυτόν που έβαλε το LOAD_STATE."""
        m = z80_load(sym, g, fresh(g, nexthop, st), EC.MAX_DOME + EC.MAX_STRUCT, patch)
        for pin, n in ((12, 1), (11, SWEEP)):
            m.poke(sym["PIN_SLOT"], pin)
            m.poke(sym["TICK_COUNT"], n & 0xFF)
            m.poke(sym["TICK_COUNT"] + 1, n >> 8)
            enter(m, sym, "RUN_TICKS")
        got = z80_read(m, sym, 0)
        return (got[0], got[3], got[4], got[5], got[6], got[1])

    def piles(e):
        return [e.struct[i * EC.STRUCT_REC + EC.ST_OWED] for i in range(EC.MAX_STRUCT)
                if e.struct[i * EC.STRUCT_REC + EC.ST_KIND] == EC.K_MINE]
    SWEEP = 4 * EC.ECON_DIV
    starts = {}
    pile0 = piles(base.e)
    dug = None
    for name, setup, full in cases:
        st = fresh(g, nexthop, base)
        setup(st.e)
        st.e.flow_div = 1                       # ο κύκλος ροής σε αυτή την κλήση
        flow = fresh(g, nexthop, st)
        slot12(flow)
        if flow.e.full != full or (piles(flow.e) == pile0) != bool(full):
            print(f"ΑΠΟΤΥΧΙΑ αποθήκη: «{name}» — η αναφορά: γεμάτη {flow.e.full}, "
                  f"σύνολο {sum(st.e.stock[1:])} από {cap(st.e)}, σωροί "
                  f"{pile0} -> {piles(flow.e)}")
            return 1
        if z80(st, 1, 12) != keys_flow(flow):
            print(f"ΑΠΟΤΥΧΙΑ αποθήκη: «{name}» — ο κύκλος ροής του Z80 διαφέρει "
                  f"από την αναφορά")
            return 1
        if not full:
            dug = piles(flow.e)
        want, before = flow, list(flow.e.stock)    # όχι fresh(): δεν αντιγράφει το mines
        sweep(want, SWEEP)
        after = want.e.stock
        # ΓΕΜΑΤΗ (βήμα 124): ό,τι προσθέτει σταματά — οι κήποι και το VITROMEAT —
        # και οι μετατροπές συνεχίζουν: τα αγαθά αλλάζουν, το σύνολο δεν ανεβαίνει,
        # και κανένα από τα τέσσερα που βγάζουν κήποι και VITROMEAT δεν ανεβαίνει.
        grown = [k for k in (EC.S_STARCH, EC.S_VEG, EC.S_MEDPLANT, EC.S_MEAT)
                 if after[k] > before[k]]
        moved = after[1:] != before[1:]
        ok = (moved and not grown and sum(after[1:]) <= sum(before[1:])) if full else moved
        if not ok:
            print(f"ΑΠΟΤΥΧΙΑ αποθήκη: «{name}» — η αναφορά: γεμάτη {full}, σύνολο "
                  f"{sum(before[1:])} -> {sum(after[1:])}, ανέβηκαν {grown}, αγαθά "
                  f"{'άλλαξαν' if moved else 'ίδια'} στο σάρωμα")
            return 1
        if full:
            conv = sum(before[1:]) - sum(after[1:])
        if chain(st) != keys(want):
            print(f"ΑΠΟΤΥΧΙΑ αποθήκη: «{name}» — το σάρωμα του Z80 διαφέρει από την αναφορά")
            return 1
        starts[name] = (st, keys(want))
    # Και ανάποδα: ο κώδικας της γεμάτης αποθήκης από το LOAD_STATE, και ένας
    # κύκλος ροής που βρίσκει χώρο τον ξαναγυρίζει.
    st = fresh(g, nexthop, starts["ένα λιγότερο"][0])
    st.e.full = 1
    if chain(st) != starts["ένα λιγότερο"][1]:
        print("ΑΠΟΤΥΧΙΑ αποθήκη: από γεμάτη σε «ένα λιγότερο» ο Z80 διαφέρει από την αναφορά")
        return 1
    # ΤΟ ΚΟΣΤΟΣ: ο κύκλος ροής, ένα frame της θέσης 12 κάθε 64 περιστροφές, με
    # τον θόλο M της αποικίας και με οκτώ (ROOM_MAX) θόλους Storage.
    def flow_us(st):
        m = z80_load(sym, g, fresh(g, nexthop, st), EC.MAX_DOME + EC.MAX_STRUCT)
        m.poke(sym["PIN_SLOT"], 12)
        return tick_us(m, sym)
    st8 = fresh(g, nexthop, starts["ένα λιγότερο"][0])
    st8.e.room_n[EC.R_STORAGE] = EC.ROOM_MAX
    for k in range(EC.ROOM_MAX):
        st8.e.room_list[EC.R_STORAGE * EC.ROOM_MAX + k] = k
    us1, us8 = flow_us(starts["ένα λιγότερο"][0]), flow_us(st8)
    if us1 > STORE_FLOW_US or us8 > STORE_FLOW8_US:
        print(f"ΑΠΟΤΥΧΙΑ αποθήκη: ο κύκλος ροής {us1} us με έναν θόλο Storage (ταβάνι "
              f"{STORE_FLOW_US}), {us8} με οκτώ ({STORE_FLOW8_US})")
        return 1
    print(f"OK αποθήκη:  {len(cases)} κύκλοι ροής στα όρια — ένα λιγότερο, ακριβώς, "
          f"πολύ πάνω, χωρίς θόλο Storage (500), με θόλο L (1.100) — και μετά από "
          f"τον καθένα ένα σάρωμα της παραγωγής στον ίδιο Z80, και ένα από γεμάτη "
          f"σε «ένα λιγότερο»: ίδια bytes με την αναφορά· οι σωροί {pile0} -> {dug} "
          f"όταν χωρά, ίδιοι όταν γεμίσει· γεμάτη, κήποι και VITROMEAT σταματούν και οι "
          f"μετατροπές τρέχουν (βήμα 124: το σύνολο πέφτει {conv} σε ένα σάρωμα)")
    print(f"              ο κύκλος ροής {us1} us με τον θόλο M (8360 στο 121, 8610 στο 122, 8630 στο 123, 8670 στο 126, ταβάνι "
          f"{STORE_FLOW_US}), {us8} με οκτώ θόλους Storage ({STORE_FLOW8_US})")

    # ΑΡΝΗΤΙΚΑ: ο Z80 πειραγμένος, η αναφορά όχι.
    full = sym["EC_FULL"]

    def code_at(name, pat, span=160):
        a = sym[name]
        code = run_peek(sym, a, span)
        k = next((k for k in range(span - len(pat) + 1)
                  if code[k:k + len(pat)] == pat), None)
        return None if k is None else a + k
    stock1 = sym["G_ECON_STATE"] + 2
    negs = []
    a = code_at("ST_CHECK", [0x2A, stock1 & 255, stock1 >> 8], 80)
    negs.append(("το νερό αντί για την τροφή", "ένα λιγότερο",
                 a and [(a + 1, (stock1 - 2) & 255)]))
    a = code_at("ERM_INF", [0xDD, 0x7E, 0x09, 0xE6, 4], 20)
    negs.append(("το VITROMEAT δεν σταματά", "ακριβώς γεμάτη",
                 a and [(a + 4, 0)]))                         # and 0: ποτέ
    negs.append(("σταματούν όλες, και το οξυγόνο", "ακριβώς γεμάτη",
                 a and [(a + 4, 0xFF)]))                      # and #FF: κάθε σημαία
    a = code_at("EC_SETFULL", [0x0E, 0xAF], 20)
    negs.append(("οι κήποι δεν σταματούν", "ακριβώς γεμάτη", a and [(a + 1, 0xB7)]))
    a = code_at("EC_SETFULL", [0x21, sym["ERM_INF"] & 255, sym["ERM_INF"] >> 8], 20)
    negs.append(("η τρίτη κλήση μένει erm_in", "ακριβώς γεμάτη",
                 a and [(a + 1, sym["ERM_IN"] & 255), (a + 2, sym["ERM_IN"] >> 8)]))
    a = code_at("HL_PILE", [0x3A, full & 255, full >> 8, 0xB7, 0x20], 40)
    negs.append(("τα ορυχεία σκάβουν", "ακριβώς γεμάτη", a and [(a + 4, 0), (a + 5, 0)]))
    a = sym["STC_CAPS"] + 2
    negs.append(("ο θόλος M χωρά 200", "ένα λιγότερο", [(a, 200), (a + 1, 0)]))
    for what, case, patch in negs:
        st, want = starts[case]
        if not patch or chain(st, patch) == want:
            print(f"ΑΠΟΤΥΧΙΑ αποθήκη: ΑΡΝΗΤΙΚΟ «{what}» — "
                  f"{'το μοτίβο δεν βρέθηκε' if not patch else 'ο Z80 βγαίνει ίδιος'}")
            return 1
    print(f"OK αποθήκη:  ΑΡΝΗΤΙΚΑ — {', '.join(n for n, _, _ in negs)}: ο Z80 "
          f"διαφέρει από την αναφορά")
    return 0


# ΟΣΕΣ ΤΡΩΝΕ ΜΕΤΑΛΛΟ (βήμα 127): οι συνταγές με πρώτη είσοδο το μέταλλο, και
# τα προϊόντα τους.
EATERS = [m for m, r in enumerate(EC.RECIPE) if r[0] == EC.S_METAL]
EATEN = sorted({EC.RECIPE[m][6] for m in EATERS})


def keep_branches(sym, g, nexthop, sim0):
    """ΤΟ ΑΠΟΘΕΜΑ ΜΕΤΑΛΛΟΥ (βήμα 127): ο κύκλος ροής (θέση 12) με το μέταλλο στα
    όρια — 29, 30 — και πολύ πάνω (200), που ανάβει ή σβήνει το ec_keep, και
    μετά ένα ολόκληρο σάρωμα της παραγωγής (θέση 11, 64 κλήσεις) στον ίδιο Z80,
    με τον κώδικα που άφησε το ec_setfull. Ολα τα bytes ίδια με την αναφορά.
    Με 29: κανένα προϊόν τους δεν φτιάχνεται και το μέταλλο δεν πέφτει. Με 30
    και 200 φτιάχνονται — αλλιώς η δοκιμή δεν δοκιμάζει τίποτα. Και ανάποδα: από
    το ec_keep του LOAD_STATE ένας κύκλος με 200 το σβήνει. Το κόστος: οι δύο
    βαριές επισκέψεις της θέσης 11 με το απόθεμα ενεργό, απέναντι σε αυτές με
    μέταλλο."""
    base = fresh(g, nexthop, sim0)
    EC.rooms_rebuild(base.e, base.pc)
    keys = lambda z: (z.a.to_bytes(), bytes(z.e.dome), bytes(z.e.struct),
                      econ_bytes(z.e), bytes(z.e.job), bytes(z.occ[:128]))
    SWEEP = 4 * EC.ECON_DIV

    def metal(n):
        def set_(e):
            e.stock[EC.S_METAL] = n
        return set_
    cases = (("29", metal(29), 1), ("30", metal(30), 0), ("200", metal(200), 0))

    def chain(st, patch=()):
        m = z80_load(sym, g, fresh(g, nexthop, st), EC.MAX_DOME + EC.MAX_STRUCT, patch)
        for pin, n in ((12, 1), (11, SWEEP)):
            m.poke(sym["PIN_SLOT"], pin)
            m.poke(sym["TICK_COUNT"], n & 0xFF)
            m.poke(sym["TICK_COUNT"] + 1, n >> 8)
            enter(m, sym, "RUN_TICKS")
        got = z80_read(m, sym, 0)
        return (got[0], got[3], got[4], got[5], got[6], got[1])

    starts, made = {}, {}
    for name, setup, keep in cases:
        st = fresh(g, nexthop, base)
        setup(st.e)
        st.e.flow_div = 1
        want = fresh(g, nexthop, st)
        slot12(want)
        if want.e.keep != keep or want.e.full:
            print(f"ΑΠΟΤΥΧΙΑ μέταλλο: «{name}» — η αναφορά: ec_keep {want.e.keep}, γεμάτη "
                  f"{want.e.full}· η πρόζα λέει {keep}, όχι γεμάτη")
            return 1
        before = list(want.e.stock)
        for _ in range(SWEEP):
            EC.production_slice(want.e, plant_class=want.pc)
        after = want.e.stock
        made[name] = sum(after[k] - before[k] for k in EATEN)
        if keep and (made[name] or after[EC.S_METAL] < before[EC.S_METAL]):
            print(f"ΑΠΟΤΥΧΙΑ μέταλλο: «{name}» — με το απόθεμα φτιάχτηκαν {made[name]} "
                  f"από όσα τρώνε μέταλλο, μέταλλο {before[EC.S_METAL]} -> {after[EC.S_METAL]}")
            return 1
        if not keep and made[name] <= 0:
            print(f"ΑΠΟΤΥΧΙΑ μέταλλο: «{name}» — καμία μηχανή που τρώει μέταλλο δεν "
                  f"έτρεξε: η δοκιμή δεν δοκιμάζει τίποτα")
            return 1
        if chain(st) != keys(want):
            print(f"ΑΠΟΤΥΧΙΑ μέταλλο: «{name}» — ο Z80 διαφέρει από την αναφορά")
            return 1
        starts[name] = (st, keys(want))
    st = fresh(g, nexthop, starts["200"][0])
    st.e.keep = 1
    if chain(st) != starts["200"][1]:
        print("ΑΠΟΤΥΧΙΑ μέταλλο: από το ec_keep σε 200 ο Z80 διαφέρει από την αναφορά")
        return 1

    # ΤΟ ΚΟΣΤΟΣ: οι κλήσεις της θέσης 11 που σαρώνουν (οι άλλες είναι 160 us).
    def visits(st, keep):
        s = fresh(g, nexthop, st)
        s.e.keep = keep
        m = z80_load(sym, g, s, EC.MAX_DOME + EC.MAX_STRUCT)
        m.poke(sym["PIN_SLOT"], 11)
        us = [tick_us(m, sym) for _ in range(SWEEP)]
        return sorted(u for u in us if u > 200)[-2:]
    hi = visits(starts["29"][0], 0)
    lo = visits(starts["29"][0], 1)
    if max(lo) > KEEP_SWEEP_US:
        print(f"ΑΠΟΤΥΧΙΑ μέταλλο: οι βαριές επισκέψεις με το απόθεμα {lo} us, ταβάνι "
              f"{KEEP_SWEEP_US} (χωρίς {hi})")
        return 1

    # ΑΡΝΗΤΙΚΑ: ο Z80 πειραγμένος, η αναφορά όχι.
    def code_at(name, pat, span=160):
        a = sym[name]
        code = run_peek(sym, a, span)
        k = next((k for k in range(span - len(pat) + 1)
                  if code[k:k + len(pat)] == pat), None)
        return None if k is None else a + k
    negs = []
    a = code_at("ERM_INK", [0xFE, EC.S_METAL, 0xC2], 8)
    negs.append(("όλες περνούν", "29", a and [(a + 1, 0xFE)]))
    k = sym["ERM_INK"]
    a = code_at("EC_SETFULL", [0x21, k & 255, k >> 8], 40)
    negs.append(("η πρώτη κλήση μένει erm_in", "29",
                 a and [(a + 1, sym["ERM_IN"] & 255), (a + 2, sym["ERM_IN"] >> 8)]))
    a = code_at("STC_SET", [0x11, (-EC.KEEP_METAL) & 255, 0xFF], 12)
    negs.append(("το όριο 31", "30", a and [(a + 1, (-31) & 255)]))
    a = code_at("STC_SET", [0x11, (-EC.KEEP_METAL) & 255, 0xFF], 12)
    negs.append(("το όριο 29", "29", a and [(a + 1, (-29) & 255)]))
    for what, case, patch in negs:
        st, want = starts[case]
        if not patch or chain(st, patch) == want:
            print(f"ΑΠΟΤΥΧΙΑ μέταλλο: ΑΡΝΗΤΙΚΟ «{what}» — "
                  f"{'το μοτίβο δεν βρέθηκε' if not patch else 'ο Z80 βγαίνει ίδιος'}")
            return 1
    print(f"OK μέταλλο:  {len(cases)} κύκλοι ροής — μέταλλο 29, 30, 200 — και μετά από τον "
          f"καθένα ένα σάρωμα της παραγωγής στον ίδιο Z80, και ένα από το ec_keep σε 200: "
          f"ίδια bytes με την αναφορά· με 29 οι {len(EATERS)} που τρώνε μέταλλο σταματούν "
          f"(0 προϊόντα, το μέταλλο δεν πέφτει), με 30 και 200 φτιάχνουν "
          f"{made['30']} και {made['200']}")
    print(f"              οι βαριές επισκέψεις της θέσης 11 με το απόθεμα {lo} us, χωρίς {hi} "
          f"(ταβάνι {KEEP_SWEEP_US})")
    print(f"OK μέταλλο:  ΑΡΝΗΤΙΚΑ — " + ", ".join(w for w, _, _ in negs) +
          ": ο Z80 διαφέρει από την αναφορά")
    return 0


def slot12(sim):
    """Η θέση 12 της αναφοράς, όπως τη τρέχει το Sim.tick (tools/entity.py)."""
    alive = sum(1 for i in range(EC.AG_BOT0) if sim.a.flags[i] & E.F_ALIVE)
    inside = sum(1 for i in range(EC.AG_BOT0)
                 if sim.a.flags[i] & E.F_ALIVE and sim.a.flags[i] & E.F_INDOORS)
    EC.flow_balance(sim.e, alive, inside)


def keys_flow(z):
    """Ο,τι συγκρίνει ένας κύκλος ροής της θέσης 12: όπως οι άλλοι."""
    return (z.a.to_bytes(), bytes(z.e.dome), bytes(z.e.struct),
            econ_bytes(z.e), bytes(z.e.job), bytes(z.occ[:128]))


# (όνομα, οξυγόνο, νερό, τροφή, ύπνος, υγεία, ηθικό) — βήμα 53
NEED_CASES = (
    ("οξυγόνο κρίσιμο",          10, 200, 200, 200, 150, 100),
    ("νερό κρίσιμο",            200,  10, 200, 200, 150, 100),
    ("τροφή κρίσιμη",           200, 200,  10, 200, 150, 100),
    ("οξυγόνο και νερό",         10,  10, 200, 200, 150, 100),
    ("και τα τρία",              10,  10,  10, 200,  60, 100),
    ("η ζημιά ως τον θάνατο",    10,  10,  10, 200,   5, 100),
    ("ανάρρωση",                200, 200, 200, 200, 100, 100),
    ("ανάρρωση στο ταβάνι",     200, 200, 200, 200, 255, 255),
    ("τροφή 63: όχι ανάρρωση",  200, 200,  63, 200, 100, 100),
    ("ηθικό στο πάτωμα",        200, 200, 200,  10, 150,   1),
    ("ηθικό ανάμεσα",           200, 200, 200,  40, 150, 100),
    ("υγεία χαμηλή: ιατρείο",   200, 200, 200, 200,  50, 100),
    ("πείνα: κυλικείο",         200, 200,  50, 200, 150, 100),
    ("δίψα: κυλικείο",          200,  50, 200, 200, 150, 100),
    ("νύστα: κοιτώνας",         200, 200, 200,  50, 150, 100),
)


def need_branches(sym, g, nexthop, sim0):
    """Οι ζωντανοί στημένοι κυκλικά στις NEED_CASES, και τέσσερις περιστροφές
    — όλοι περνούν από το πέρασμα αναγκών — απέναντι στην αναφορά.

    Το κοινό τρέξιμο δεν τα βλέπει: στην αποικία του κανείς δεν κατεβαίνει
    στο κρίσιμο, και το βήμα 53 έγραψε τη ζημιά από την αρχή (τα carry των
    συγκρίσεων ως bits). Με το οξυγόνο να ζυγίζει 2 αντί για 4 το κοινό
    τρέξιμο έμενε πράσινο."""
    base = fresh(g, nexthop, sim0)
    alive = [i for i in range(128) if base.a.flags[i] & E.F_ALIVE]
    for k, i in enumerate(alive):
        _, o2, wa, fo, sl, he, mo = NEED_CASES[k % len(NEED_CASES)]
        a = base.a
        a.o2[i], a.water[i], a.food[i], a.sleep[i] = o2, wa, fo, sl
        a.health[i], a.morale[i] = he, mo
    base.e.gloom = 40                       # και το πένθος, όπου δεν παρηγορεί κανείς
    end = same(sym, g, nexthop, base, 64, "ανάγκες στα όρια")
    if end is None:
        return 1
    hurt = sum(1 for i in alive if 0 < end.a.health[i] < base.a.health[i])
    died = sum(1 for i in alive if not end.a.flags[i] & E.F_ALIVE)
    healed = sum(1 for i in alive if end.a.health[i] > base.a.health[i])
    if not (hurt and died and healed):
        print(f"ΑΠΟΤΥΧΙΑ ανάγκες: οι περιπτώσεις δεν έπιασαν — {hurt} χτυπήθηκαν, "
              f"{died} πέθαναν, {healed} γιατρεύτηκαν")
        return 1
    # ΑΡΝΗΤΙΚΟ: το πρώτο `rl e` (CB 13) — το bit του οξυγόνου — γίνεται nop nop.
    at = sym["ND_LOAD"]
    k = next(k for k in range(64) if run_peek(sym, at + k, 2) == [0xCB, 0x13])
    if same(sym, g, nexthop, base, 64, "", quiet=True,
            patch=[(at + k, 0), (at + k + 1, 0)]) is not None:
        print("ΑΠΟΤΥΧΙΑ ανάγκες: ΑΡΝΗΤΙΚΟ — χωρίς τη ζημιά του οξυγόνου ο Z80 "
              "βγαίνει ίδιος με την αναφορά: η δοκιμή δεν έχει δόντια")
        return 1
    print(f"OK ανάγκες:  {len(NEED_CASES)} περιπτώσεις σε {len(alive)} άποικους — "
          f"{hurt} χτυπήθηκαν, {died} πέθαναν, {healed} γιατρεύτηκαν — ίδια bytes "
          f"στον Z80 και στην αναφορά. ΑΡΝΗΤΙΚΟ: χωρίς το bit του οξυγόνου διαφέρουν")
    return o2_branches(sym, g, nexthop, sim0)


def o2_branches(sym, g, nexthop, sim0):
    """ΜΕΣΑ ΚΑΙ ΕΞΩ, ΜΕ ΟΞΥΓΟΝΟ ΚΑΙ ΧΩΡΙΣ (βήμα 87). Το κοινό τρέξιμο πέφτει
    σε έλλειμμα από τη δεύτερη περιστροφή, και κανείς δεν είναι στο 0 μέσα
    σε θόλο όταν το οξυγόνο φτάνει: η μία πρόσθεση του nd_ok, «max(o2 - 1, 0)
    + R», έμενε αδοκίμαστη ακριβώς στη γωνία της. Εδώ οι πρώτοι 64 στημένοι:
    οξυγόνο 0, 255, 254, 1, και κάθε πέμπτος έξω. Δύο ΑΡΝΗΤΙΚΑ: χωρίς το
    «ήταν 0» του nd_ok, και χωρίς τον έλεγχο «έξω» του nd_def."""
    base = fresh(g, nexthop, sim0)
    k = 0
    for i in range(64):
        if base.a.flags[i] & E.F_ALIVE:
            base.a.o2[i] = (0, 255, 254, 1)[k % 4]
            if k % 5 == 4:
                E.set_in(base.a, i, False)
            k += 1
    inside = sum(1 for i in range(64) if base.a.flags[i] & 3 == 3)
    outside = sum(1 for i in range(64) if base.a.flags[i] & 3 == 1)
    ok_at = def_at = None
    at = sym["ND_OK"]
    code = run_peek(sym, at, 32)
    # cp O2_REFILL - 1 / jr nz / inc a — το «ήταν 0»
    ok_at = next(at + j + 4 for j in range(28)
                 if code[j] == 0xFE and code[j + 2] == 0x20 and code[j + 4] == 0x3C)
    code = run_peek(sym, sym["ND_DEF"], 16)
    # rr e / jr nc — ο έλεγχος «έξω»
    def_at = next(sym["ND_DEF"] + j + 2 for j in range(12)
                  if code[j:j + 2] == [0xCB, 0x1B] and code[j + 2] == 0x30)
    for ok, name, neg in ((1, "φτάνει", [(ok_at, 0)]),
                          (0, "έλλειμμα", [(def_at, 0), (def_at + 1, 0)])):
        st = fresh(g, nexthop, base)
        st.e.o2_ok = ok
        st.e.o2_prod = st.e.acc_o2 = 400 * ok
        if same(sym, g, nexthop, st, 128, f"οξυγόνο που {name}") is None:
            return 1
        if same(sym, g, nexthop, st, 128, "", quiet=True, patch=neg) is not None:
            print(f"ΑΠΟΤΥΧΙΑ οξυγόνο που {name}: ΑΡΝΗΤΙΚΟ — με πειραγμένο "
                  f"κώδικα ο Z80 βγαίνει ακόμη ίδιος με την αναφορά")
            return 1
    print(f"OK οξυγόνο: {inside} μέσα και {outside} έξω, στο 0, 1, 254, 255, "
          f"με οξυγόνο που φτάνει και σε έλλειμμα — ίδια bytes στον Z80 και "
          f"στην αναφορά. ΑΡΝΗΤΙΚΑ: χωρίς το «ήταν 0» του nd_ok και χωρίς το "
          f"«έξω» του nd_def διαφέρουν")
    return suit_branches(sym)


# --- οι στολές (βήμα 90, src/suit.asm) ----------------------------------------
# (στολή, φάση, ρόλος ή None, εργασία ή None): η τελευταία μονάδα και στις δύο
# φάσεις, γύρω από το SUIT_LOW, ρομπότ με άδεια στολή, και κάποιος που πάει ήδη
# μέσα (T_NEED) με λίγο αέρα.
SUIT_CASES = [(1, 0, None, None), (1, 1, None, None), (EC.SUIT_LOW + 1, 1, None, None),
              (EC.SUIT_LOW + 2, 1, None, None), (EC.SUIT_LOW, 0, None, None),
              (200, 0, None, None), (1, 1, 5, None), (2, 1, 7, None),
              (EC.SUIT_LOW - 3, 0, None, E.T_NEED), (EC.SUIT_LOW + 1, 1, None, None)]
SUIT_LOCKS = (64, 66, 69)           # airlock, κρεμασμένα σε θόλους
SUIT_OUT = (65, 67, 68, 70, 71, 90, 91)     # δομές έξω· 90-91 δεν φτάνουν πουθενά
SUIT_TICKS = 640


def suit_graph():
    """Ο γράφος της αποικίας με δομές (64-71) σε θόλους, μία πίσω από το
    airlock 64 και μία πίσω από το 66, και ένα ζευγάρι 90-91 μόνο του."""
    g = G.GRAPHS["colony"]()
    g.n = g.hw = 93
    for k, s in enumerate(range(64, 72)):
        if s not in (65, 67):
            g.link(k * 5 % 48, s)
    g.link(64, 65)
    g.link(66, 67)
    g.link(90, 91)
    return g


def suit_scene():
    """Οι πρώτοι ζωντανοί στις δομές έξω (και σε δύο airlock μέσα, με
    προορισμό δομή έξω: φεύγουν, και το emd_put τους γεμίζει τη στολή), με
    τις SUIT_CASES κυκλικά."""
    g = suit_graph()
    dist, nexthop = G.all_pairs(g)
    st = E.Sim(g, nexthop, dist)
    EC.populate(st.e)
    E.populate(st)
    for n in SUIT_LOCKS + SUIT_OUT:
        b = (n - EC.MAX_DOME) * EC.STRUCT_REC
        st.e.struct[b:b + 8] = bytes([0, 0, EC.K_AIRLOCK if n in SUIT_LOCKS else 0, 0,
                                      EC.DS_ACTIVE, 255, 0, 0])
    EC.rooms_rebuild(st.e, st.pc)
    a = st.a
    alive = [i for i in range(E.MAX_COLONIST)
             if a.flags[i] & E.F_ALIVE]
    for k, i in enumerate(alive[:48]):
        E.release(st.occ, a.node[i], a.slot[i])
        if k % 8 == 7:                      # μέσα, σε airlock, και φεύγει έξω
            n = SUIT_LOCKS[k % 3]
            a.node[i], a.dest[i] = n, SUIT_OUT[k % 5]
            a.flags[i] = (a.flags[i] | E.F_INDOORS) & ~E.F_WORKING & 0xFF
            a.suit[i] = 3
        else:
            n = SUIT_OUT[k % len(SUIT_OUT)]
            a.node[i] = a.dest[i] = n
            a.flags[i] &= ~(E.F_INDOORS | E.F_WORKING | E.F_SUITPH) & 0xFF
            suit, ph, role, task = SUIT_CASES[k % len(SUIT_CASES)]
            a.suit[i] = suit
            a.flags[i] |= E.F_SUITPH if ph else 0
            if role is not None:
                a.role[i] = role
            if task is not None:
                a.task[i] = task
                a.dest[i] = SUIT_LOCKS[0]
        a.slot[i] = E.claim(st.occ, n)
        a.edge[i] = E.NO_EDGE
        a.progress[i] = 0
        # οι ανάγκες ψηλά: εδώ μετρά μόνο η στολή
        a.water[i] = a.food[i] = a.sleep[i] = a.health[i] = 220
    return g, nexthop, st


def suit_branches(sym):
    """ΟΙ ΣΤΟΛΕΣ, byte προς byte. Και τι έγινε, στην αναφορά: πέθαναν ΜΟΝΟ όσοι
    είχαν μία μονάδα (και άνθρωποι), όσοι έπεσαν στο SUIT_LOW πήγαν σε airlock
    και μπήκαν, κανείς από το 90-91 (κανένα airlock δεν φτάνεται), τα ρομπότ
    ανέγγιχτα, και όποιος βγήκε από airlock βγήκε με SUIT_TRIP. ΑΡΝΗΤΙΚΑ: ο
    Z80 με τη στολή να αδειάζει σε κάθε επίσκεψη, χωρίς airlock, με το
    T_NEED να σβήνει και έξω, και χωρίς γέμισμα στην έξοδο."""
    g, nexthop, st = suit_scene()
    end = same(sym, g, nexthop, st, SUIT_TICKS, "στολές")
    if end is None:
        return 1
    a0, a1 = st.a, end.a
    out = [i for i in range(96) if a0.flags[i] & 3 == E.F_ALIVE and a0.node[i] in SUIT_OUT]
    died = [i for i in out if not a1.flags[i] & E.F_ALIVE]
    bots = [i for i in out if a0.role[i] >= E.BOT_CONSTR]
    went = [i for i in out if a1.flags[i] & E.F_ALIVE and a1.node[i] in SUIT_LOCKS
            and a1.flags[i] & E.F_INDOORS]
    left = [i for i in range(96) if a0.flags[i] & 3 == 3 and a0.node[i] in SUIT_LOCKS
            and a0.dest[i] in SUIT_OUT]
    why = []
    if any(a0.suit[i] > 2 or a0.role[i] >= E.BOT_CONSTR for i in died):
        why.append(f"πέθαναν και άλλοι: {[(i, a0.suit[i], a0.role[i]) for i in died]}")
    if any(a1.suit[i] != a0.suit[i] or not a1.flags[i] & 1 for i in bots):
        why.append("τα ρομπότ άλλαξαν")
    if not went or any(a0.node[i] in (90, 91) for i in went):
        why.append(f"μπήκαν σε airlock {went}")
    gone = [i for i in left if a1.flags[i] & 3 == E.F_ALIVE]       # βγήκαν (από θόλο ίσως όχι ακόμη)
    if not gone or not all(a1.suit[i] >= EC.SUIT_TRIP - 6 for i in gone):
        why.append(f"όσοι βγήκαν: {[(a1.flags[i], a1.node[i], a1.suit[i]) for i in left]}")
    if why:
        print("ΑΠΟΤΥΧΙΑ στολές: " + "· ".join(why))
        return 1
    # ΑΡΝΗΤΙΚΑ
    m = boot_only()
    find = lambda at, pat, n=96: next((at + k for k in range(n)
                                       if list(m.read_ram(at + k, len(pat))) == pat), None)
    ph = find(sym["SU_TICK"], [0xCB, 0x76, 0x20], 40)          # bit 6,(hl) · jr nz
    lk = find(sym["SU_TICK"], [0xCD, sym["SU_LOCK"] & 255, sym["SU_LOCK"] >> 8], 96)
    sd = find(sym["ND_SATED"], [0xCB, 0x4E, 0xC8], 24)
    fill = find(sym["EMD_PUT"], [0x26, (sym["G_AGENT_FIELDS"] >> 8) + 7, 0x36, EC.SUIT_TRIP], 16)
    for label, patch in (("η στολή αδειάζει σε κάθε επίσκεψη", ph and [(ph + 2, 0x18)]),   # jr: πάντα
                         ("κανένα airlock", lk and [(lk, 0x3E), (lk + 1, 0xFF), (lk + 2, 0)]),
                         ("το T_NEED σβήνει και έξω", sd and [(sd + 2, 0)]),
                         ("χωρίς γέμισμα στην έξοδο", fill and [(fill + k, 0) for k in range(4)])):
        if not patch or same(sym, g, nexthop, st, SUIT_TICKS, label, patch, quiet=True):
            print(f"ΑΠΟΤΥΧΙΑ ΑΡΝΗΤΙΚΟ στολών: με «{label}» ο Z80 συμφώνησε (ή δεν βρέθηκε)")
            return 1
    print(f"OK στολές: {len(out)} έξω σε {len(SUIT_CASES)} περιπτώσεις — {len(died)} πέθαναν "
          f"(μόνο με μία μονάδα), {len(went)} γύρισαν σε airlock και μπήκαν, κανείς από "
          f"το 90-91, {len(bots)} ρομπότ ανέγγιχτα, {len(gone)} βγήκαν με γεμάτη στολή — "
          f"ίδια bytes στον Z80 και στην αναφορά. ΑΡΝΗΤΙΚΑ: κάθε επίσκεψη, κανένα "
          f"airlock, T_NEED που σβήνει έξω, χωρίς γέμισμα — διαφέρουν")
    return 0


def _sol(e):
    """Η επόμενη περιστροφή κλείνει το sol."""
    e.frame = e.sollen - 16


def _green(e):
    e.o2_ok, e.power_ok = 1, EC.POWER_ALL
    e.stock[EC.S_WATER], e.stock[EC.S_FOOD] = 50, 50


def _bots(n, first=EC.AG_BOT0):
    """n ζωντανά ρομπότ από τη θέση first, και οι θέσεις 80-95 αλλιώς άδειες.
    Το Automation είναι οκτώ ζωντανά ΣΤΙΣ ΘΕΣΕΙΣ ΤΟΥΣ (βήμα 92): με first = 0
    τα ίδια οκτώ στις θέσεις των αποίκων δεν μετρούν."""
    def f(e, a):
        _sol(e)
        e.milestones = 0
        for i in range(EC.AG_BOT0, EC.AG_BOT0 + EC.AG_NBOT):
            a.flags[i] = 0
        for i in range(first, first + n):
            a.flags[i], a.role[i] = E.F_ALIVE, EC.RL_CBOT + (i & 1)
    return f


def _robots(stock, alive=0, holes=(), where=1, sol=False):
    """Το απόθεμα Bots (βήμα 92, src/bots.asm): δύο εργοστάσια στο ευρετήριο,
    η μηχανή robots στο δεύτερο (where = 1), στο πρώτο (0) ή σε κανένα (None).
    Οι θέσεις 80-95: οι πρώτες `alive` ζωντανές, οι `holes` νεκρές."""
    def f(e, a):
        e.stock[EC.S_BOT] = stock
        if sol:
            _sol(e)
            e.milestones = 0
        e.dome[ROBOTS_2ND * EC.DOME_REC + EC.D_ROOM] = EC.R_FACTORY
        for d in range(EC.MAX_DOME):
            b = d * EC.DOME_REC
            if e.dome[b + EC.D_ROOM] == EC.R_FACTORY:
                for k in range(EC.MACH_SLOTS):
                    if e.dome[b + EC.D_MACH + k] == EC.M_ROBOTS:
                        e.dome[b + EC.D_MACH + k] = EC.M_ROBOTS - 1
        EC.rooms_rebuild(e, E.Sim.PLANT_CLASS)
        fac = [e.room_list[EC.R_FACTORY * EC.ROOM_MAX + k]
               for k in range(e.room_n[EC.R_FACTORY])]
        assert len(fac) == 2, fac
        if where is not None:
            b = fac[where] * EC.DOME_REC
            n = EC.MACHINE_COUNT[e.dome[b + EC.D_SIZE]]
            e.dome[b + EC.D_MACH + n - 1] = EC.M_ROBOTS     # η τελευταία υποδοχή
        for k in range(EC.AG_NBOT):
            i = EC.AG_BOT0 + k
            a.flags[i] = E.F_ALIVE if k < alive and i not in holes else 0
            a.role[i] = EC.RL_CBOT + (i & 1)
    return f


ROBOTS_2ND = 21             # ο δεύτερος θόλος Factory των περιπτώσεων ρομπότ


def _crew(room):
    """Πλοίο αποίκων που προσγειώνεται τώρα, με ταβάνι ζωντανοί + room. Το
    e.alive το μετρά μόνο η θέση 12, οπότε εδώ μετριέται με το χέρι."""
    def f(e, a):
        e.alive = sum(1 for i in range(EC.AG_BOT0) if a.flags[i] & E.F_ALIVE)
        e.ship_state, e.ship_kind, e.ship_eta = EC.SHIP_INCOMING, EC.SK_COLONIST, 0
        e.pop_cap = e.alive + room
    return f


def _land(land, room):
    """Το ίδιο, με ποσοστά ειδικοτήτων (βήμα 91, src/crew.asm)."""
    crew = _crew(room)

    def f(e, a):
        crew(e, a)
        e.land = list(land)
    return f


def _visit_roll(want=0):
    """Ο σπόρος που ρίχνει επισκέπτες στην πρώτη ζαριά (event_branches) — ή,
    με want = MER_ROLL, έμπορο (βήμα 93)."""
    return next(x for x in range(1, 65536) if EC.lfsr(EC.lfsr(x)) & 0x7FF == want)


def _mer_seed(cond):
    """Ο πρώτος σπόρος του οποίου η προσγείωση δίνει τα bytes που θέλει το
    cond(b0, b1, b2): η θέση 15 τραβά πρώτα τρεις ζαριές, και το φορτίο βγαίνει
    από το EC_RND μετά από αυτές (src/ship.asm, sm_land)."""
    def l3(x):
        for _ in range(3):
            x = EC.lfsr(x)
        return x
    return next(x for x in range(1, 65536) if cond(*EC.mer_bytes(l3(x), 3)))


def _merchant(cond):
    """Ο έμπορος προσγειώνεται τώρα, με σπόρο που περνά από την άκρη cond."""
    def f(e, a):
        e.ship_state, e.ship_kind, e.ship_eta = EC.SHIP_INCOMING, EC.SK_MERCHANT, 0
        e.rnd = _mer_seed(cond)
    return f


# (όνομα, περιστροφές, στήσιμο) — βήμα 57. Κάθε μία είναι ένα κενό που βρήκαν
# τα σκόπιμα λάθη του βήματος: ο κώδικας άλλαζε, και ούτε το κοινό τρέξιμο
# ούτε το tests/test_game.py το έβλεπαν.
# --- ΟΙ ΕΙΣΒΟΛΕΙΣ (βήμα 111): η ζαριά, η προσγείωση και η μάχη ---------------

def _foe_due(alive, lands, roll=0):
    """Η ζαριά των απρόσκλητων (επισκέπτες, ή έμπορος με roll = MER_ROLL) με
    alive ζωντανούς και lands προσγειώσεις μετρημένες."""
    return lambda e, a: (setattr(e, "ship_state", 0), setattr(e, "rnd", _visit_roll(roll)),
                         setattr(e, "alive", alive), setattr(e, "lands", lands))


def _foe_land(alive, taken=0):
    """Το πλοίο των εισβολέων προσγειώνεται με alive ζωντανούς· οι πρώτες taken
    από τις θέσεις 96-99 έχουν ήδη εισβολέα (μιας προηγούμενης φοράς)."""
    def f(e, a):
        e.ship_state, e.ship_kind, e.ship_eta = EC.SHIP_INCOMING, EC.SK_FOE, 0
        e.alive, e.lands = alive, 9
        for k in range(EC.AG_NFOE):
            i = EC.AG_FOE0 + k
            if k < taken:
                EC.born(a, i, E.F_ALIVE, EC.RL_FOE, e.pad_node, bytearray(256))
                a.task[i], a.health[i] = EC.T_FIGHT, EC.FOE_HP
                a.slot[i] = 255
    return f


def _lands(kind, n):
    """Ενα πλοίο προσγειώνεται με n προσγειώσεις ήδη μετρημένες."""
    return lambda e, a: (setattr(e, "ship_state", EC.SHIP_INCOMING),
                         setattr(e, "ship_kind", kind), setattr(e, "ship_eta", 0),
                         setattr(e, "lands", n))


FOE_SHIP_CASES = (
    # ΟΙ ΕΙΣΒΟΛΕΙΣ (βήμα 111): από τη ζαριά των απρόσκλητων, στα όριά της —
    # 20 ζωντανοί και 8 προσγειώσεις φέρνουν εισβολείς, 19 ή 7 όχι, και από τη
    # ζαριά του εμπόρου το ίδιο.
    ("εισβολείς: 20 ζωντανοί, 8 προσγειώσεις", 2, _foe_due(20, 8)),
    ("εισβολείς: 19 ζωντανοί", 2, _foe_due(19, 8)),
    ("εισβολείς: 7 προσγειώσεις", 2, _foe_due(20, 7)),
    ("εισβολείς: η ζαριά του εμπόρου", 2, _foe_due(41, 200, EC.MER_ROLL)),
    ("εισβολείς: προσγείωση με 39 ζωντανούς", 2, _foe_land(39)),
    ("εισβολείς: με 40", 2, _foe_land(40)),
    ("εισβολείς: με 59", 2, _foe_land(59)),
    ("εισβολείς: με 60", 2, _foe_land(60)),
    ("εισβολείς: με 80, και τρεις ήδη εδώ", 2, _foe_land(80, taken=3)),
    ("προσγειώσεις: οι επισκέπτες μετράνε", 1, _lands(EC.SK_VISITOR, 7)),
    ("προσγειώσεις: ως το 255", 1, _lands(EC.SK_MERCHANT, 255)),
)


SHIP_CASES = (
    # Ο ΕΛΕΓΧΟΣ ΤΗΣ ΠΙΣΤΑΣ στο ship_call: το C τον κάνει μόνο του πριν το
    # καλέσει, οπότε μόνο οι επισκέπτες της ζαριάς φτάνουν εδώ χωρίς πίστα.
    ("επισκέπτες από τη ζαριά, χωρίς πίστα", 3,
     lambda e, a: (setattr(e, "pad_node", 255), setattr(e, "ship_state", 0),
                   setattr(e, "rnd", _visit_roll()))),
    ("επισκέπτες με τροφή 5, ηθικό ως το 255", 2,
     lambda e, a: (setattr(e, "ship_state", EC.SHIP_INCOMING),
                   setattr(e, "ship_kind", EC.SK_VISITOR), setattr(e, "ship_eta", 0),
                   e.stock.__setitem__(EC.S_FOOD, 5),
                   [a.morale.__setitem__(i, (i * 37) & 0xFF) for i in range(128)])),
    # Ο ΕΜΠΟΡΟΣ (βήμα 93): από τη ζαριά, με πίστα και χωρίς άλλο πλοίο· το
    # φορτίο στις άκρες του — τρία και τέσσερα αγαθά, κέρδος 31 -> 0 (35%),
    # πρώτο αγαθό 13-15 -> mod 13, βήμα 12-15 -> mod 12 — και μισό sol.
    ("έμπορος από τη ζαριά", 2,
     lambda e, a: (setattr(e, "ship_state", 0), setattr(e, "rnd", _visit_roll(EC.MER_ROLL)))),
    ("έμπορος από τη ζαριά, χωρίς πίστα", 2,
     lambda e, a: (setattr(e, "pad_node", 255), setattr(e, "ship_state", 0),
                   setattr(e, "rnd", _visit_roll(EC.MER_ROLL)))),
    ("έμπορος από τη ζαριά, πλοίο ήδη", 2,
     lambda e, a: (setattr(e, "ship_state", EC.SHIP_INCOMING), setattr(e, "ship_eta", 50),
                   setattr(e, "ship_kind", EC.SK_COLONIST),
                   setattr(e, "rnd", _visit_roll(EC.MER_ROLL)))),
    ("έμπορος: τρία αγαθά", 3, _merchant(lambda b0, b1, b2: not b0 & 32)),
    ("έμπορος: τέσσερα αγαθά", 3, _merchant(lambda b0, b1, b2: b0 & 32)),
    ("έμπορος: κέρδος 31 -> 35%", 1, _merchant(lambda b0, b1, b2: b0 & 31 == 31)),
    ("έμπορος: πρώτο αγαθό 13-15", 1, _merchant(lambda b0, b1, b2: b1 & 15 >= 13)),
    ("έμπορος: βήμα 12-15", 1, _merchant(lambda b0, b1, b2: b1 >> 4 >= 12)),
    # βήμα 135: και νομίσματα, τα bits 6-7 του πρώτου byte x 50
    ("έμπορος: χωρίς νομίσματα", 1, _merchant(lambda b0, b1, b2: b0 >> 6 == 0)),
    ("έμπορος: 50 νομίσματα", 1, _merchant(lambda b0, b1, b2: b0 >> 6 == 1)),
    ("έμπορος: 150 νομίσματα", 1, _merchant(lambda b0, b1, b2: b0 >> 6 == 3)),
    ("έμπορος φεύγει", 1,
     lambda e, a: (setattr(e, "ship_state", EC.SHIP_LANDED),
                   setattr(e, "ship_kind", EC.SK_MERCHANT), setattr(e, "ship_eta", 0))),
    ("άποικοι, ταβάνι για δύο", 2, _crew(2)),
    ("άποικοι, ταβάνι ήδη ξεπερασμένο", 2, _crew(-1)),
    # ΟΙ ΕΙΔΙΚΟΤΗΤΕΣ (βήμα 91): 50% βιολόγοι, 50% γιατροί, σε μια αποικία με
    # κάθε ρόλο και ρομπότ — ο Z80 μετρά όπως η αναφορά, και ρομπότ δεν έρχονται.
    ("άποικοι, 50% βιολόγοι και 50% γιατροί", 2, _land([0, 0, 5, 5, 0], 4)),
    ("τρία σερί στο 255", 1,
     lambda e, a: (_sol(e), _green(e), setattr(e, "green_sols", 255),
                   setattr(e, "no_death_sols", 255), setattr(e, "deaths_sol", 0),
                   setattr(e, "no_trade_sols", 255), setattr(e, "traded", 0))),
    # ΤΟ AUTOMATION (βήμα 92): οκτώ ζωντανά στις θέσεις 80-95, όχι «οκτώ με
    # F_WORKING και ρόλο 5+», που δεν το έπιανε ποτέ κανένα ρομπότ.
    ("επτά ρομπότ", 1, _bots(7)),
    ("οκτώ ρομπότ: αυτοματισμός", 1, _bots(8)),
    ("οκτώ ρομπότ στις θέσεις αποίκων", 1, _bots(8, 0)),
    # ΤΑ ΡΟΜΠΟΤ ΑΠΟ ΤΟ ΑΠΟΘΕΜΑ (βήμα 92, src/bots.asm), ένα ανά περιστροφή.
    ("ρομπότ: απόθεμα 3, η μηχανή στο δεύτερο εργοστάσιο", 4, _robots(3)),
    ("ρομπότ: η μηχανή στο πρώτο εργοστάσιο", 1, _robots(1, where=0)),
    ("ρομπότ: απόθεμα, κανένα εργοστάσιο με μηχανή", 2, _robots(5, where=None)),
    ("ρομπότ: δεκαέξι ήδη", 2, _robots(5, alive=16)),
    ("ρομπότ: τρύπα στη θέση 85", 2, _robots(4, alive=16, holes=(85,))),
    ("ρομπότ: επτά, και το όγδοο στην περιστροφή του sol", 1,
     _robots(1, alive=7, sol=True)),
    ("μέταλλο και βιοπλαστικό, όχι ανταλλακτικά", 1,
     lambda e, a: (_sol(e), setattr(e, "prod_mask", 0x18), setattr(e, "milestones", 0))),
    ("εννιά από τα δέκα αγαθά", 1,
     lambda e, a: (_sol(e), setattr(e, "prod_mask", 0x1FF), setattr(e, "no_trade_sols", 9),
                   setattr(e, "milestones", 0))),
    ("habitat: ανεξάρτητοι, όχι βιομήχανοι", 1,
     lambda e, a: (_sol(e), setattr(e, "alive", 80), setattr(e, "no_death_sols", 4),
                   setattr(e, "deaths_sol", 0), setattr(e, "milestones", 4),
                   setattr(e, "prod_mask", 0))),
    ("habitat: βιομήχανοι, όχι ανεξάρτητοι", 1,
     lambda e, a: (_sol(e), setattr(e, "alive", 80), setattr(e, "no_death_sols", 9),
                   setattr(e, "deaths_sol", 0), setattr(e, "milestones", 2),
                   setattr(e, "prod_mask", 0x58))),
)


SHIP_CASES += FOE_SHIP_CASES             # βήμα 111


# --- ΕΠΙΣΚΕΠΤΕΣ ΠΟΥ ΠΛΗΡΩΝΟΥΝ ΚΑΙ ΚΥΡΟΣ (βήμα 134), ΠΟΥ ΠΕΡΠΑΤΟΥΝ (βήμα 136) ---

def _visitors(prestige=0, canteen=1, food=50, water=50, amenity=1, coins=0, goodwill=50,
              lounge=1, sollen=12000):
    """Το πλοίο επισκεπτών προσγειώνεται τώρα, με το κύρος, τα αποθέματα και τα
    δωμάτια στις άκρες που θέλει η περίπτωση. Από το βήμα 136 περπατούν, και
    το sol είναι μεγάλο (το πλοίο μένει μισό sol): στην αποικία της δοκιμής η
    επίσκεψη με σαλόνι κρατά 133 περιστροφές, χωρίς 44."""
    def f(e, a):
        e.ship_state, e.ship_kind, e.ship_eta = EC.SHIP_INCOMING, EC.SK_VISITOR, 0
        e.prestige, e.coins, e.goodwill, e.amenity = prestige, coins, goodwill, amenity
        e.sollen = sollen
        e.room_n[EC.R_CANTEEN] = canteen
        if not lounge:
            e.room_n[EC.R_LOUNGE] = 0
        e.stock[EC.S_FOOD], e.stock[EC.S_WATER] = food, water
    return f


def _lost(e, a):
    """Το πλοίο εδώ, και δύο επισκέπτες στο κυλικείο 11 για το σαλόνι: ο 112
    έχασε την εργασία του (NO_TASK, όπως μετά από κατεδάφιση) και την ξαναπαίρνει,
    ο 113 κάθεται ακόμη τρεις περιστροφές."""
    e.ship_state, e.ship_kind, e.ship_eta = EC.SHIP_LANDED, EC.SK_VISITOR, 300
    e.sollen = 12000
    for i, task, stay in ((112, E.NO_TASK, 0), (113, EC.T_VISIT, 3)):
        a.flags[i], a.role[i] = E.F_ALIVE | E.F_INDOORS, EC.RL_VIS
        a.node[i] = a.dest[i] = 11
        a.edge[i], a.slot[i] = E.NO_EDGE, E.NO_SLOT
        a.task[i], a.progress[i], a.health[i] = task, stay, EC.VP_FUN


def _prestige(mile=0, alive=6, nodeath=0, amenity=0, goodwill=0, visacc=0,
              ship=False, pad=True, lands=0):
    """Η επόμενη περιστροφή κλείνει το sol, με ό,τι μπαίνει στο κύρος."""
    def f(e, a):
        _sol(e)
        e.milestones, e.alive, e.no_death_sols, e.deaths_sol = mile, alive, nodeath, 0
        e.amenity, e.goodwill, e.visacc, e.lands = amenity, goodwill, visacc, lands
        if ship:
            e.ship_state, e.ship_kind, e.ship_eta = EC.SHIP_INCOMING, EC.SK_COLONIST, 50
        else:
            e.ship_state = 0
        if not pad:
            e.pad_node = 255
    return f


VISIT_CASES = (
    ("επισκέπτες: δύο κατεβαίνουν στην πίστα", 1, _visitors()),
    ("επισκέπτες: στο κυλικείο, πληρώνουν, κάθονται, αναπνέουν", 12, _visitors()),
    ("επισκέπτες: όλη η επίσκεψη, κυλικείο και σαλόνι, ανεβαίνουν", 136, _visitors()),
    ("επισκέπτες: χωρίς σαλόνι, τα δέντρα πληρώνουν", 46, _visitors(lounge=0)),
    ("επισκέπτες: χωρίς σαλόνι ή δέντρο", 46, _visitors(lounge=0, amenity=0)),
    ("επισκέπτες: χωρίς κυλικείο, η εύνοια ως το 0", 6, _visitors(canteen=0, goodwill=10)),
    ("επισκέπτες: ένα τρόφιμο", 12, _visitors(food=1)),
    ("επισκέπτες: χωρίς νερό", 12, _visitors(water=0)),
    ("επισκέπτες: κύρος 63, δύο", 1, _visitors(prestige=63)),
    ("επισκέπτες: κύρος 64, τρεις", 1, _visitors(prestige=64)),
    ("επισκέπτες: κύρος 250, πέντε, τα νομίσματα ως το 999", 12,
     _visitors(prestige=250, coins=990)),
    ("επισκέπτες: η εύνοια ως το 100", 12, _visitors(goodwill=98)),
    ("επισκέπτες: το μισό sol, φεύγουν με το πλοίο", 14, _visitors(sollen=320)),
    ("επισκέπτες: ένας χάνει τον δρόμο, ένας κάθεται", 3, _lost),
    ("κύρος: όλα στις άκρες", 1,
     _prestige(mile=31, alive=80, nodeath=255, amenity=9, goodwill=100)),
    ("κύρος: σερί 29, σαλόνια 5", 1, _prestige(nodeath=28, amenity=5, goodwill=1)),
    ("κύρος: ο συσσωρευτής ως το 255, χωρίς πλοίο", 1, _prestige(alive=10, visacc=200)),
    ("κύρος: πάνω από 255, πλοίο επισκεπτών", 2, _prestige(alive=80, visacc=250)),
    ("κύρος: πάνω από 255 με πλοίο ήδη, μένει 255", 1,
     _prestige(alive=80, visacc=250, ship=True)),
    ("κύρος: πάνω από 255 χωρίς πίστα, μένει 255", 1,
     _prestige(alive=80, visacc=250, pad=False)),
    ("κύρος: πάνω από 255, εισβολείς", 2, _prestige(alive=40, visacc=250, lands=8)),
)
SHIP_CASES += VISIT_CASES


def ship_branches(sym, g, nexthop, sim0):
    """Η θέση 15 καρφωμένη: κάθε SHIP_CASES από την ίδια κατάσταση, στον Z80
    και στην αναφορά (slot15), και όλα τα bytes ίδια."""
    # ΚΑΙ ΟΙ ΜΑΣΚΕΣ ΘΕΣΕΩΝ (βήμα 92): ένας καινούργιος πιάνει θέση στον κόμβο
    # του, και ως εδώ η σύγκριση δεν το κοίταζε.
    keys = lambda z: (z.a.to_bytes(), bytes(z.e.dome), bytes(z.e.struct),
                      econ_bytes(z.e), bytes(z.e.job), bytes(z.occ[:128]))

    def z80(st, n, patch=()):
        got = run_z80(sym, g, fresh(g, nexthop, st), n, pin=15,
                      rt_n=EC.MAX_DOME + EC.MAX_STRUCT, patch=patch)
        return (got[0], got[3], got[4], got[5], got[6], got[1])

    starts = {}
    for name, n, setup in SHIP_CASES:
        st = fresh(g, nexthop, sim0)
        setup(st.e, st.a)
        want = fresh(g, nexthop, st)
        slot15(want, n)
        if z80(st, n) != keys(want):
            print(f"ΑΠΟΤΥΧΙΑ πλοία και sol: «{name}» — ο Z80 διαφέρει από την αναφορά")
            return 1
        starts[name] = (st, n, keys(want))
    # ΑΡΝΗΤΙΚΟ: ο αυτοματισμός από 9 ρομπότ (cp 8 -> cp 9 στο sol_rollover).
    at = sym["SOL_ROLLOVER"]
    code = run_peek(sym, at, 256)
    k = next(k for k in range(254) if code[k:k + 3] == [0xFE, 0x08, 0x38])
    st, n, want = starts["οκτώ ρομπότ: αυτοματισμός"]
    if z80(st, n, patch=[(at + k + 1, 9)]) == want:
        print("ΑΠΟΤΥΧΙΑ πλοία και sol: ΑΡΝΗΤΙΚΟ — με τον αυτοματισμό από 9 "
              "ρομπότ ο Z80 βγαίνει ίδιος με την αναφορά")
        return 1
    print(f"OK πλοία και sol: {len(SHIP_CASES)} περιπτώσεις στα όρια — πίστα, τροφή "
          f"και ηθικό επισκεπτών, έμπορος και φορτίο, ταβάνι, ειδικότητες, σερί στο 255, "
          f"ρομπότ, οι δύο μάσκες, "
          f"habitat — ίδια bytes στον Z80 και στην αναφορά. ΑΡΝΗΤΙΚΟ: με "
          f"αυτοματισμό από 9 ρομπότ διαφέρουν")
    # ΑΡΝΗΤΙΚΟ (βήμα 111): οι εισβολείς από 19 ζωντανούς (cp FOE_POP -> cp 19
    # στο ev_kind· στο ev_ship ως το βήμα 133).
    at = sym["EV_KIND"]
    code = run_peek(sym, at, 16)
    k = next((k for k in range(14) if code[k:k + 2] == [0xFE, EC.FOE_POP]), None)
    st, n, want = starts["εισβολείς: 19 ζωντανοί"]
    if k is None or z80(st, n, patch=[(at + k + 1, 19)]) == want:
        print("ΑΠΟΤΥΧΙΑ πλοία και sol: ΑΡΝΗΤΙΚΟ — με εισβολείς από 19 ζωντανούς "
              "ο Z80 βγαίνει ίδιος με την αναφορά")
        return 1
    print("OK πλοία και sol: εισβολείς από τη ζαριά των απρόσκλητων με 20 ζωντανούς "
          "και 8 προσγειώσεις, όχι με 19 ή 7· 2, 3, 3, 4 στην πίστα με 39, 40, 59, 60· "
          "οι προσγειώσεις ως το 255. ΑΡΝΗΤΙΚΟ: από 19 ζωντανούς διαφέρουν")
    # ΤΑ ΑΡΝΗΤΙΚΑ ΤΟΥ ΒΗΜΑΤΟΣ 134: τέσσερα σκόπιμα λάθη, το καθένα στην
    # περίπτωση που το βλέπει.
    def fault(label, sym_at, pat, k_off, val, case):
        at = sym[sym_at]
        code = run_peek(sym, at, 160)
        k = next((k for k in range(160 - len(pat)) if code[k:k + len(pat)] == pat), None)
        st, n, want = starts[case]
        caught = k is not None and z80(st, n, patch=[(at + k + k_off, val)]) != want
        return caught, label
    bad = [lab for ok, lab in (
        fault("η εύνοια δεν σβήνει", "SR_PRES", [0x28, 0x01, 0x35], 2, 0x00,
              "κύρος: σερί 29, σαλόνια 5"),
        # βήμα 136: ret nc -> ret, χωρίς το ταβάνι (src/visit0.asm)
        fault("τα νομίσματα χωρίς ταβάνι", "VI_PAY", [0x19, 0xD0], 1, 0xC9,
              "επισκέπτες: κύρος 250, πέντε, τα νομίσματα ως το 999"),
        # cp e / ret z -> ret nz: «εδώ» όταν ΔΕΝ είναι
        fault("ο έλεγχος του κυλικείου ανάποδα", "VIA_GO", [0xBB, 0xC8], 1, 0xC0,
              "επισκέπτες: στο κυλικείο, πληρώνουν, κάθονται, αναπνέουν"),
        fault("δεν κάθονται", "VIA_STAY", [0x36, EC.VIS_STAY], 1, 0,
              "επισκέπτες: στο κυλικείο, πληρώνουν, κάθονται, αναπνέουν"),
        fault("δεν ανεβαίνουν", "VIA_BOARD", [0xC3], 0, 0xC9,
              "επισκέπτες: όλη η επίσκεψη, κυλικείο και σαλόνι, ανεβαίνουν"),
        # ld a,c / ld (EC_VIN),a -> ld a,c / ld a,(EC_VIN): δεν μετριούνται
        fault("όσοι είναι μέσα δεν μετριούνται", "VI_TICK", [0x79, 0x32], 1, 0x3A,
              "επισκέπτες: στο κυλικείο, πληρώνουν, κάθονται, αναπνέουν"),
        fault("το σαλόνι χωρίς τα δέντρα", "VIA_TREE", [0xB7, 0x28], 1, 0x18,
              "επισκέπτες: χωρίς σαλόνι, τα δέντρα πληρώνουν"),
        fault("ο συσσωρευτής ξεχνά το πλοίο που δεν ήρθε", "SR_PRES", [0x3E, 0xFF], 1, 0x00,
              "κύρος: πάνω από 255 με πλοίο ήδη, μένει 255"),
        # βήμα 135: and 3 -> and 1 μετά τα δύο rlca, μόνο το bit 6
        fault("τα νομίσματα του εμπόρου μόνο από το bit 6", "SM_LAND",
              [0x07, 0x07, 0xE6, 0x03], 3, 0x01, "έμπορος: 150 νομίσματα"),
    ) if not ok]
    if bad:
        print(f"ΑΠΟΤΥΧΙΑ πλοία και sol: ΑΡΝΗΤΙΚΑ των βημάτων 134-136 που δεν πιάστηκαν: {bad}")
        return 1
    print(f"OK επισκέπτες και κύρος (βήματα 134, 136): {len(VISIT_CASES)} περιπτώσεις — "
          f"κατεβαίνουν, περπατούν ως το κυλικείο και το σαλόνι, πληρώνουν, κάθονται, "
          f"αναπνέουν, ανεβαίνουν, τα δέντρα, χωρίς κυλικείο, τρόφιμο, νερό, 2-5 επισκέπτες "
          f"από το κύρος, νομίσματα ως το 999, εύνοια 0-100, το μισό sol, ένας χαμένος· το "
          f"κύρος στις άκρες του, ο συσσωρευτής με πλοίο, χωρίς, με άλλο πλοίο, χωρίς πίστα, "
          f"και εισβολείς. ΑΡΝΗΤΙΚΑ: η εύνοια που δεν σβήνει, νομίσματα χωρίς ταβάνι, το "
          f"κυλικείο ανάποδα, ο συσσωρευτής που ξεχνά, δεν κάθονται, δεν ανεβαίνουν, δεν "
          f"μετριούνται μέσα, το σαλόνι χωρίς δέντρα — διαφέρουν")
    print("OK τα νομίσματα του εμπόρου (βήμα 135): χωρίς, 50 και 150 στην προσγείωσή του, "
          "ίδια bytes στον Z80 και στην αναφορά. ΑΡΝΗΤΙΚΟ: μόνο από το bit 6 διαφέρουν")
    return 0


# --- Η ΜΑΧΗ (βήμα 111, src/foe.asm): εισβολείς, άποικοι και φρουροί ---------
FOE_PIN = 12                # περιστροφές της καρφωμένης θέσης 15
FOE_TICKS = 16 * 40         # frames του ολόκληρου τροχού


def foe_state(g, nexthop, sim0):
    """Ο συναγερμός στημένος σε κάθε κλάδο του fo_tick: ο 96 στέκεται στον
    κόμβο του φρουρού 4 και ενός ακόμη, ο 97 στον κόμβο του φρουρού 44, ο 98 σε
    γειτονικό κόμβο του φρουρού 12 που έχει ήδη όπλο, ο 99 περπατά προς κόμβο
    με κόσμο. Δύο Gun στο απόθεμα για τους υπόλοιπους εννέα φρουρούς, ο 36 πάει
    για ανάγκη (T_NEED), ο 28 περπατά."""
    st = fresh(g, nexthop, sim0)
    a, e = st.a, st.e

    def put(i, node, edge=E.NO_EDGE, prog=0):
        a.flags[i] = E.F_ALIVE | (E.F_INDOORS if EC.indoor_node(e, node) else 0)
        a.role[i], a.node[i], a.dest[i], a.edge[i] = EC.RL_FOE, node, node, edge
        a.slot[i] = E.claim(st.occ, node) if edge == E.NO_EDGE else E.NO_SLOT
        a.task[i], a.health[i], a.progress[i] = EC.T_FIGHT, EC.FOE_HP, prog
    near = next(n for n in (g.adj[47 * G.MAXDEG + q] for q in range(g.deg[47]))
                if not any(a.flags[c] & E.F_ALIVE and a.role[c] == EC.RL_GUARD
                           and a.node[c] == n for c in range(EC.AG_BOT0)))
    put(96, a.node[4])
    put(97, a.node[44])
    put(98, near)
    put(99, 6, edge=0, prog=200)
    a.flags[12] |= EC.F_GUN
    a.task[36] = E.T_NEED
    E.release(st.occ, a.node[28], a.slot[28])
    a.slot[28], a.edge[28], a.progress[28] = E.NO_SLOT, 0, 50
    e.stock[EC.S_GUN] = 2
    return st


def foe_battle(sym, g, nexthop, sim0):
    """Η μάχη στον Z80 και στην αναφορά (tools/entity.py, foe_tick), byte προς
    byte: πρώτα η θέση 15 καρφωμένη, μετά ολόκληρος ο τροχός."""
    st = foe_state(g, nexthop, sim0)
    keys = lambda z: (z.a.to_bytes(), bytes(z.e.dome), bytes(z.e.struct),
                      econ_bytes(z.e), bytes(z.e.job), bytes(z.occ[:128]))

    def z80(patch=()):
        got = run_z80(sym, g, fresh(g, nexthop, st), FOE_PIN, pin=15,
                      rt_n=EC.MAX_DOME + EC.MAX_STRUCT, patch=patch)
        return (got[0], got[3], got[4], got[5], got[6], got[1]), got[2]

    want = fresh(g, nexthop, st)
    want.foe = {"pk": 0}
    slot15(want, FOE_PIN)
    got, _ = z80()
    if got != keys(want):
        bad = [(k, [(i, x, y) for i, (x, y) in enumerate(zip(a_, b_)) if x != y][:5])
               for k, (a_, b_) in enumerate(zip(got, keys(want))) if a_ != b_]
        print(f"ΑΠΟΤΥΧΙΑ μάχη: η θέση 15 καρφωμένη, {FOE_PIN} περιστροφές — "
              f"ο Z80 διαφέρει από την αναφορά: {bad}")
        return 1
    n = want.foe["n"]
    need = ("χτυπήματα εισβολέων", "άποικοι έπεσαν", "εισβολείς έπεσαν", "όπλα",
            "με όπλο, από γειτονικό", "με όπλο, στον κόμβο", "με τα χέρια")
    if any(not n.get(k) for k in need) or want.e.stock[EC.S_GUN] != 0 \
            or want.a.task[36] != E.T_NEED:
        print(f"ΑΠΟΤΥΧΙΑ μάχη: η σκηνή δεν περνά από όλους τους κλάδους: {n}")
        return 1
    def find(label, pat, span=80):
        code = run_peek(sym, sym[label], span)
        k = next((k for k in range(span - len(pat)) if code[k:k + len(pat)] == pat), None)
        return None if k is None else sym[label] + k
    w = lambda v: [v & 255, v >> 8]
    # ΤΟ ΚΟΣΤΟΣ, ΑΝΑ ΠΕΡΙΣΤΡΟΦΗ ΚΑΙ ΜΕ ΑΚΡΙΒΕΙΑ: η θέση 15 ολόκληρη (ζαριές, πλοίο
    # και εισβολείς), στη χειρότερη από τις FOE_PIN· και χωρίς εισβολείς.
    # Χωρίς πλοίο: η προσγείωση αποίκων της αποικίας της δοκιμής κοστίζει
    # μόνη της ~4,5 ms στην 7η περιστροφή, και δεν είναι των εισβολέων.
    calm_st = fresh(g, nexthop, st)
    calm_st.e.ship_state = EC.SHIP_NONE
    m = z80_load(sym, g, calm_st, EC.MAX_DOME + EC.MAX_STRUCT)
    m.poke(sym["PIN_SLOT"], 15)
    per = [tick_us(m, sym) for _ in range(FOE_PIN)]
    pin_us = max(per)
    calm_st = fresh(g, nexthop, sim0)
    calm_st.e.ship_state = EC.SHIP_NONE
    m = z80_load(sym, g, calm_st, EC.MAX_DOME + EC.MAX_STRUCT)
    m.poke(sym["PIN_SLOT"], 15)
    calm = [tick_us(m, sym) for _ in range(4)]
    # ΑΡΝΗΤΙΚΟ του κόστους: χωρίς την πόρτα του fo_n (jp z,ship_tick -> nop)
    # η θέση 15 μετρά τους εισβολείς και ελευθερώνει φρουρούς σε κάθε περιστροφή.
    gate = find("FO_TICK", [0xCA] + w(sym["SHIP_TICK"]), 8)
    m = z80_load(sym, g, calm_st, EC.MAX_DOME + EC.MAX_STRUCT,
                 patch=gate and [(gate + k, 0) for k in range(3)])
    m.poke(sym["PIN_SLOT"], 15)
    open_gate = [tick_us(m, sym) for _ in range(4)]
    if not gate or max(open_gate[1:]) <= FOE_CALM_US:
        print(f"ΑΠΟΤΥΧΙΑ μάχη: ΑΡΝΗΤΙΚΟ — χωρίς την πόρτα του fo_n η θέση 15 κοστίζει "
              f"{open_gate} us, όχι πάνω από το ταβάνι {FOE_CALM_US}")
        return 1
    # ΑΡΝΗΤΙΚΑ: ο κώδικας πειραγμένος, και ο Z80 πρέπει να διαφέρει.
    gh = find("FOG_TGT", [0x06, EC.GUN_HIT], 80)            # ld b,GUN_HIT
    nb = find("FO_ZONE", [0x0C, 0x0D, 0xC8], 30)            # inc c / dec c / ret z
    fv = find("FOV_H", [0x2F, 0xA1, 0x4F], 10)              # cpl / and c / ld c,a
    tn = find("FO_GUARD", [0xFE, E.T_NEED])                 # cp T_NEED
    pk = find("FOS_GO", [0x32] + w(sym["FO_PK"]))           # ld (fo_pk),a
    mv = find("FO_TICK", [0xCD] + w(sym["ENT_MOVE_SLICE"]), 40)
    for label, patch in (
            ("το όπλο όσο τα χέρια", gh and [(gh + 1, EC.HAND_HIT)]),
            ("κανείς γειτονικός", nb and [(nb, 0xC9)]),
            ("ο εισβολέας χτυπά όλους στον κόμβο", fv and [(fv + 2, 0)]),
            ("και όποιος πάει για ανάγκη στη μάχη", tn and [(tn + 1, 0)]),
            ("ο επόμενος στόχος πάντα από τον πρώτο", pk and [(pk + k, 0) for k in range(3)]),
            ("οι εισβολείς δεν κινούνται", mv and [(mv + k, 0) for k in range(3)])):
        if not patch:
            print(f"ΑΠΟΤΥΧΙΑ μάχη: δεν βρέθηκε πού να πειραχτεί για «{label}»")
            return 1
        if z80(patch)[0] == got:
            print(f"ΑΠΟΤΥΧΙΑ μάχη: ΑΡΝΗΤΙΚΟ — με «{label}» ο Z80 βγαίνει ίδιος")
            return 1
    # ΚΑΙ ΟΛΟΚΛΗΡΟΣ Ο ΤΡΟΧΟΣ: οι άποικοι και οι φρουροί κινούνται, οι ανάγκες
    # και ο πίνακας εργασιών ανάμεσα.
    if same(sym, g, nexthop, st, FOE_TICKS, "μάχη, ολόκληρος ο τροχός") is None:
        return 1
    print(f"OK μάχη: {FOE_PIN} περιστροφές της θέσης 15 — "
          + ", ".join(f"{k} {v}" for k, v in sorted(n.items()))
          + f" — και {FOE_TICKS // 16} ολόκληρες· ίδια bytes στον Z80 και στην "
          f"αναφορά. ΑΡΝΗΤΙΚΑ: όπλο = χέρια, χωρίς γειτονικούς, χτυπά όλους, "
          f"και η ανάγκη στη μάχη, ο στόχος από την αρχή, ακίνητοι — διαφέρουν")
    print(f"              η θέση 15 με τέσσερις εισβολείς, 80 αποίκους και 10 "
          f"φρουρούς: ως {pin_us} us (μέση {sum(per) // len(per)}, ταβάνι "
          f"{FOE_PIN_US})· χωρίς εισβολείς {calm[1:]} us (ταβάνι {FOE_CALM_US}), "
          f"{calm[0]} η πρώτη, που τους μετρά· ΑΡΝΗΤΙΚΟ: χωρίς την πόρτα του fo_n "
          f"{open_gate[1:]}")
    if pin_us > FOE_PIN_US or max(calm[1:]) > FOE_CALM_US:
        print(f"ΑΠΟΤΥΧΙΑ μάχη: η θέση 15 κοστίζει πάνω από το ταβάνι")
        return 1
    return 0


# ΤΑΒΑΝΙΑ, μετρημένα στο βήμα 111. Με εισβολείς η θέση 15 είναι η ακριβότερη
# του τροχού όσο ζουν (η 14 είναι 4,7 ms): ο συναγερμός κρατά δευτερόλεπτα.
# Χωρίς, ό,τι ήταν στο 110 και ένα byte (fo_n) με ένα άλμα.
FOE_PIN_US = 6200
FOE_CALM_US = 480


def move_graph():
    """Ο γράφος της αποικίας και ό,τι δεν έχει: δομές (64-71) κρεμασμένες σε
    θόλους και μία σε άλλη δομή, ένα ζευγάρι 90-91 που δεν φτάνει πουθενά, ο
    92 μόνος του. Ο θόλος 7 και ο 3 αλλάζουν ΜΕΤΑ τη δρομολόγηση (MOVE_STALE)."""
    g = G.GRAPHS["colony"]()
    g.n = g.hw = 93
    for k, s in enumerate(range(64, 72)):
        g.link(k * 5 % 48, s)
    g.link(64, 65)
    g.link(90, 91)
    return g


# Μετά τη δρομολόγηση: ο θόλος 7 χωρίς ακμές, ο 3 με έναν γείτονα που το
# NEXTHOP δεν ξέρει. Και τα δύο «δεν συμβαίνουν» — και τα δύο έχουν κλάδο.
MOVE_STALE = ((G.ADJ_SIZE + 7, 0), (3 * G.MAXDEG, 92))     # (θέση στο adj+deg, τιμή)
MOVE_SLICES = ((0, 128), (0, 128), (120, 16), (5, 0), (64, 64), (0, 128), (127, 1),
               (0, 128), (33, 40))
MOVE_REC = 0x3100                       # ο καταγραφέας του wh_push, πάνω από τον κώδικα


def move_state(rnd, g):
    """Πράκτορες σε κάθε κλάδο: νεκροί, σε ακμή με πρόοδο στο όριο της άφιξης,
    στάσιμοι στον προορισμό, με προορισμό προσιτό ή απρόσιτο, εργαζόμενοι, με
    και χωρίς θέση· μάσκες κατοχής άδειες, γεμάτες, μισές."""
    nodes = [n for n in range(g.hw) if g.deg[n]] + [92, 7]  # ο 7: deg 0 μετά το MOVE_STALE
    a = E.Agents()
    for i in range(128):
        alive = rnd.random() < 0.85
        a.flags[i] = (rnd.randrange(256) | E.F_ALIVE) if alive else \
            (rnd.randrange(256) & ~E.F_ALIVE & 0xFF)
        n = rnd.choice(nodes)
        a.node[i], a.role[i] = n, rnd.randrange(8)
        speed = E.ROLE_SPEED[a.role[i]]
        if g.deg[n] and rnd.random() < 0.45:
            a.edge[i] = rnd.randrange(g.deg[n])
            a.progress[i] = rnd.choice([0, 255 - speed, 256 - speed, 255, 100])
        else:
            a.edge[i], a.progress[i] = E.NO_EDGE, rnd.randrange(256)
        r = rnd.random()
        a.dest[i] = (n if r < 0.35 else rnd.choice(nodes) if r < 0.8 else
                     rnd.choice([92, 90, 91, 7, 3]))
        a.slot[i] = rnd.randrange(8) if rnd.random() < 0.6 else E.NO_SLOT
        a.task[i] = rnd.randrange(256)
    # Και όσα η τύχη μπορεί να μη φέρει, σε κάθε κατάσταση: στον 3 με προορισμό
    # τον γείτονα που ξέχασε το MOVE_STALE, στον 7 χωρίς ακμές, στον 92 που δεν
    # φτάνει πουθενά, και εργαζόμενος που φεύγει από δομή.
    col = G.GRAPHS["colony"]()
    for i, (n, d) in zip((1, 2, 3, 4), ((3, col.adj[3 * G.MAXDEG]), (7, col.adj[7 * G.MAXDEG]),
                                        (92, 0), (64, 0))):
        a.flags[i] |= E.F_ALIVE | E.F_WORKING
        a.node[i], a.dest[i], a.edge[i] = n, d, E.NO_EDGE
    occ = bytearray(rnd.choice([0, 0xFF, 0x7F, 0xFE, 0x55, rnd.randrange(256)])
                    for _ in range(G.MAXNODE))
    dome = bytearray(rnd.randrange(256) for _ in range(EC.MAX_DOME * EC.DOME_REC))
    for d in range(EC.MAX_DOME):
        dome[d * EC.DOME_REC + EC.D_OPS] |= 1           # η αναφορά δεν πάει κάτω από 0
    return a, occ, dome


DK_AGENT = 8                            # src/const.asm (βήμα 89)


def move_ref(a, occ, dome, g, nexthop, first, count, marks, st):
    """Η αναφορά, πράκτορα προς πράκτορα — και οι wh_push που πρέπει να βγουν:
    όποιος άφησε θέση θόλου, όποιος πήρε θέση θόλου.

    ΚΑΙ Η ΦΙΓΟΥΡΑ ΕΞΩ (βήμα 89, src/figure.asm): ένα DK_AGENT όταν αλλάζει κάτι
    που φαίνεται έξω, με ένα σημάδι ανά πράκτορα (marks) — μόνο αν δεν ήταν
    ήδη σημειωμένος. Αλλάζει όταν βηματίζει στο έδαφος (όχι στον σωλήνα), όταν
    φτάνει από έξω ή σε δομή, και όταν φεύγει — εκτός από θόλο, μέσα, προς
    μέρος με αέρα: εκεί δεν φαινόταν ούτε πριν ούτε μετά."""
    e, out = types.SimpleNamespace(dome=dome, struct=st), []
    for k in range(count):
        i = (first + k) % 128
        node, slot, edge, f0 = a.node[i], a.slot[i], a.edge[i], a.flags[i]
        E.move_one(a, i, g, nexthop, occ, e)
        fig = False
        if edge == E.NO_EDGE and a.edge[i] != E.NO_EDGE:
            if slot != E.NO_SLOT and node < EC.MAX_DOME:
                out += [0, node, slot]
            fig = not (f0 & E.F_INDOORS and a.flags[i] & E.F_INDOORS
                       and node < EC.MAX_DOME)
        elif edge != E.NO_EDGE and a.edge[i] == E.NO_EDGE:
            if a.slot[i] != E.NO_SLOT and a.node[i] < EC.MAX_DOME:
                out += [0, a.node[i], a.slot[i]]
            fig = not f0 & E.F_INDOORS or a.node[i] >= EC.MAX_DOME
        elif edge != E.NO_EDGE and f0 & E.F_ALIVE:
            fig = not f0 & E.F_INDOORS
        if fig and not marks[i]:
            marks[i] = 1
            out += [DK_AGENT, i, 0]
    return out


def pushes(rec):
    """Οι εγγραφές του wh_push, με το τρίτο byte του DK_AGENT μηδέν: εκεί δεν
    σημαίνει τίποτα, και το fg_mark δεν ξοδεύει εντολή για να το γράψει."""
    rec = list(rec)
    for j in range(0, len(rec) - 2, 3):
        if rec[j] == DK_AGENT:
            rec[j + 2] = 0
    return rec


STRUCTS = None                          # ο πίνακας δομών της κίνησης (move_branches)


def move_branches(sym, sim0, n=12, patch=(), quiet=False):
    """Το ent_move_slice απευθείας, σε φτιαγμένες καταστάσεις, απέναντι στο
    tools/entity.py: πεδία, κατοχή, πίνακας θόλων και οι wh_push μετά από ΚΑΘΕ
    φέτα. Γυρίζει την πρώτη διαφορά ή None."""
    import cpc
    from cpc import CPC
    global STRUCTS
    STRUCTS = sim0.e.struct             # το en_in τις διαβάζει (βήμα 87)
    g = move_graph()
    _, nexthop = G.all_pairs(g)
    for at, v in MOVE_STALE:
        (g.adj if at < G.ADJ_SIZE else g.deg)[at % G.ADJ_SIZE] = v
    rnd = random.Random(59)
    rec = MOVE_REC + 0x80
    hook = bytes([0x57, 0x2A, rec & 255, rec >> 8, 0x72, 0x23, 0x70, 0x23, 0x71, 0x23,
                  0x22, rec & 255, rec >> 8,             # γράφει A, B, C
                  0x3E, 0xA5, 0x16, 0x5A, 0x21, 0xAD, 0xDE, 0xB7, 0xC9])   # και χαλάει ό,τι το dirty_push
    for sc in range(n):
        a, occ, dome = move_state(rnd, g)
        # Ο πίνακας δομών κι αυτός (βήμα 94): όποιος φεύγει από ορυχείο με
        # F_WORKING κατεβάζει το ST_OPS του. Αντίγραφο ανά κατάσταση.
        st = bytearray(sim0.e.struct)
        m = CPC()
        m.run_frames(60)
        assert m.quickload(SNA, start=False), "quickload απέτυχε"
        g0 = move_graph()
        m.write_ram(sym["G_NODE_ADJ"], bytes(g0.adj))
        m.write_ram(sym["G_RT_NODES"], bytes(g0.deg))
        m.poke(sym["RT_N"], g0.hw)
        enter(m, sym, "BUILD_ROUTES")
        for at, v in MOVE_STALE:
            m.poke((sym["G_NODE_ADJ"] if at < G.ADJ_SIZE else sym["G_RT_NODES"])
                   + at % G.ADJ_SIZE, v)
        m.write_ram(STAGE_AG, a.to_bytes())
        m.write_ram(STAGE_OCC, bytes(occ) + bytes(128))
        m.write_ram(STAGE_DOME, bytes(dome))
        m.write_ram(STAGE_STR, bytes(st))
        m.write_ram(sym["G_ECON_STATE"], EC.to_bytes(sim0.e))
        m.write_ram(sym["G_JOB_TBL"], bytes(sim0.e.job))
        m.write_ram(sym["G_ROOM_N"], bytes(sim0.e.room_n))
        m.write_ram(sym["G_ROOM_LIST"], bytes(sim0.e.room_list))
        enter(m, sym, "LOAD_STATE")
        m.write_ram(MOVE_REC, hook)
        m.poke(sym["WH_HOOK"], MOVE_REC & 255)
        m.poke(sym["WH_HOOK"] + 1, MOVE_REC >> 8)
        for at, v in patch:
            m.poke(at, v)
        bank6 = lambda: ctypes.string_at(cpc._lib.cpcemu_ram_ptr(m._h, 6), 0x4000)
        spans = [(sym[n] - 0x4000, k) for n, k in (("G_AGENT_FIELDS", 2048),
                 ("G_NODE_OCC", 256), ("G_DOME_TBL", len(dome)), ("G_STRUCT_TBL", 256))]
        mk0 = sym["G_NODE_OCC"] - 0x4000 + 128          # τα σημάδια των φιγούρων
        marks = bytearray(bank6()[mk0:mk0 + 128])
        rest = lambda b: b"".join(b[s + k:e] for (s, k), (e, _) in
                                  zip([(0, 0)] + spans, spans + [(0x4000, 0)]))
        rest0 = rest(bank6())
        for first, count in MOVE_SLICES:
            want = move_ref(a, occ, dome, g, nexthop, first, count, marks, st)
            m.write_ram(rec, bytes([(rec + 2) & 255, (rec + 2) >> 8]))
            # di · ld sp · ld bc,#7FC6: out (c),c (τράπεζα 6) · ld bc · call ·
            # ld a,#5A: ld (σημαία),a · jr $
            flag = rec - 1
            m.poke(flag, 0)
            code = bytes([0xF3, 0x31, 0x00, 0x30, 0x01, 0xC6, 0x7F, 0xED, 0x49,
                          0x01, first, count, 0xCD, sym["ENT_MOVE_SLICE"] & 255,
                          sym["ENT_MOVE_SLICE"] >> 8, 0x3E, 0x5A, 0x32, flag & 255,
                          flag >> 8, 0x18, 0xFE])
            m.run_code(0x3000, code, frames=12)
            assert m.peek(flag) == 0x5A, f"το ent_move_slice δεν γύρισε: #{m.pc:04X}"
            b6 = bank6()
            ag = b6[sym["G_AGENT_FIELDS"] - 0x4000:][:2048]
            oc = b6[sym["G_NODE_OCC"] - 0x4000:][:G.MAXNODE]
            dm = b6[sym["G_DOME_TBL"] - 0x4000:][:len(dome)]
            sb = b6[sym["G_STRUCT_TBL"] - 0x4000:][:256]
            p = m.peek(rec) | (m.peek(rec + 1) << 8)
            got = pushes(m.read_ram(rec + 2, p - rec - 2))
            mk = b6[mk0:mk0 + 128]
            for what, x, y in (("πεδία", ag, a.to_bytes()), ("κατοχή", oc, bytes(occ)),
                               ("θόλοι", dm, bytes(dome)), ("δομές", sb, bytes(st)),
                               ("wh_push", got, want),
                               ("σημάδια φιγούρων", mk, bytes(marks)),
                               ("η υπόλοιπη τράπεζα 6", rest(b6), rest0)):
                if bytes(x) != bytes(y):
                    if what == "πεδία":
                        i = next(j for j in range(2048) if x[j] != y[j])
                        f = E.FIELDS[(i // 256) * 2 + ((i % 256) >= 128)]
                        what += f" (πράκτορας {i % 128}, {f}: Z80 {x[i]}, αναφορά {y[i]})"
                    elif what == "wh_push":
                        what += f" (Z80 {len(x) // 3}, αναφορά {len(y) // 3})"
                    return f"κατάσταση {sc}, φέτα {first},{count}: {what}"
    return None

def move_check(sym, sim0):
    """Η κίνηση στα όρια, και το αρνητικό της: χωρίς το τύλιγμα της φέτας στο
    128 (res 7,c -> nop nop) η φέτα 120,16 διαβάζει «πράκτορες» 128-135."""
    why = move_branches(sym, sim0)
    if why:
        print(f"ΑΠΟΤΥΧΙΑ κίνηση στα όρια: {why}")
        return 1
    at = sym["ENT_MOVE_SLICE"]
    code = run_peek(sym, at, 16)
    k = next((k for k in range(15) if code[k:k + 2] == [0xCB, 0xB9]), None)
    if k is None:
        print("ΑΠΟΤΥΧΙΑ κίνηση στα όρια: το ent_move_slice δεν τυλίγει με res 7,c")
        return 1
    if move_branches(sym, sim0, n=1, patch=[(at + k, 0), (at + k + 1, 0)]) is None:
        print("ΑΠΟΤΥΧΙΑ κίνηση στα όρια: ΑΡΝΗΤΙΚΟ — χωρίς το τύλιγμα στο 128 ο "
              "Z80 βγαίνει ίδιος με την αναφορά")
        return 1
    print(f"OK κίνηση στα όρια: {12 * len(MOVE_SLICES)} φέτες σε 12 καταστάσεις — "
          f"άφιξη σε γεμάτο δαχτυλίδι και σε δομή, απρόσιτος, κόμβος χωρίς ακμές, "
          f"μπαγιάτικο NEXTHOP, εργαζόμενος που φεύγει από θόλο και από δομή, φέτα "
          f"που τυλίγει — πεδία, μάσκες, θόλοι και wh_push ίδια με την αναφορά, η "
          f"υπόλοιπη τράπεζα 6 ανέγγιχτη. ΑΡΝΗΤΙΚΟ: χωρίς το τύλιγμα στο 128 διαφέρουν")
    return 0


def run_peek(sym, at, n):
    """n bytes του κώδικα στο at, από το snapshot."""
    from cpc import CPC
    m = CPC()
    m.run_frames(60)
    assert m.quickload(SNA, start=False)
    return [m.peek(at + j) for j in range(n)]


def spread(e):
    """Τα κτίρια σε πλέγμα. Η αποικία της αναφοράς τα έχει ΟΛΑ στο (0,0) —
    η οικονομία δεν ρωτά πού είναι — και ο μετεωρίτης θα έβρισκε πάντα τον
    θόλο 0. Θόλοι ανά 10 tiles, δομές ανάμεσά τους, και τίποτε άλλο αλλάζει."""
    for d in range(EC.MAX_DOME):
        b = d * EC.DOME_REC
        if e.dome[b + EC.D_STATE]:
            e.dome[b + EC.D_CX] = (2 * (-30 + (d % 6) * 10)) & 0xFF
            e.dome[b + EC.D_CY] = (2 * (-20 + (d // 6) * 10)) & 0xFF
    for k in range(EC.MAX_STRUCT):
        b = k * EC.STRUCT_REC
        if e.struct[b + EC.ST_STATE]:
            e.struct[b + EC.ST_CX] = (2 * (-25 + (k % 6) * 10) + 1) & 0xFF
            e.struct[b + EC.ST_CY] = (2 * (-15 + (k // 6) * 10) + 1) & 0xFF


def same(sym, g, nexthop, start, ticks, what, patch=(), quiet=False):
    """Z80 και αναφορά από την ίδια κατάσταση: ΟΛΑ τα bytes ίδια. Επιστρέφει
    την αναφορά στο τέλος, ή None αν διαφέρουν."""
    got = run_z80(sym, g, fresh(g, nexthop, start), ticks,
                  rt_n=EC.MAX_DOME + EC.MAX_STRUCT, patch=patch)
    sim = fresh(g, nexthop, start)
    for _ in range(ticks):
        sim.tick()
    want = (sim.a.to_bytes(), bytes(sim.occ), None, bytes(sim.e.dome),
            bytes(sim.e.struct), econ_bytes(sim.e), bytes(sim.e.job))
    for name, i in (("πεδία", 0), ("μάσκες", 1), ("θόλοι", 3), ("δομές", 4),
                    ("οικονομία", 5), ("εργασίες", 6)):
        if got[i] != want[i]:
            bad = [k for k in range(len(want[i])) if got[i][k] != want[i][k]]
            if not quiet:
                print(f"ΑΠΟΤΥΧΙΑ {what}: {name} — {len(bad)} bytes, πρώτα "
                      f"{[(k, got[i][k], want[i][k]) for k in bad[:4]]}")
            return None
    return sim


LONG_N = 120                # κρούσεις της μακριάς βροχής


def slot15(sim, n):
    """Η θέση 15 της αναφοράς, n φορές — ό,τι κάνει ο καρφωμένος τροχός."""
    for _ in range(n):
        new_sol = EC.events(sim.e)
        if sim.e.air_out != 255:                # βήμα 90: ένα airlock χτυπήθηκε
            E.air_out(sim.a, sim.e.air_out, sim.g)
            sim.e.air_out = 255
        if new_sol:
            EC.sol_rollover(sim.e, sim.a, E.F_ALIVE, E.F_WORKING, E.NEED_LOW)
        EC.bot_tick(sim.e, sim.a, sim.occ)
        E.foe_tick(sim.e, sim.a, sim.g, sim.nexthop, sim.occ, sim.foe)   # βήμα 111
        E.ship_tick(sim.e, sim.a, sim.g, sim.nexthop, sim.occ)  # βήμα 136: και οι επισκέπτες


def edge_tiles(e):
    """Τα tiles θόλων L ακριβώς MT_REACH = 4 tiles από το κέντρο τους στο x —
    όσα ένα όριο 3 θα έχανε."""
    out = set()
    for d in range(EC.MAX_DOME):
        r = d * EC.DOME_REC
        if e.dome[r + EC.D_STATE] and e.dome[r + EC.D_SIZE] == 2:
            x0, y0, w, h = EC._footprint(e, d)
            c = EC._s8(e.dome[r]) >> 1
            out |= {(x, y) for x in range(x0, x0 + w) for y in range(y0, y0 + h)
                    if abs(x - c) == 4}
    return out


def edge_hits(e, seed, n, tiles):
    """Πόσες από τις n κρούσεις του σπόρου πέφτουν σε αυτά τα tiles."""
    f = EC.Econ()
    f.mrnd = seed
    hits = 0
    for _ in range(n):
        b = EC._mbyte(f)
        hits += (EC._s8(e.mcx + (b & 15) - 8),
                 EC._s8(e.mcy + (b >> 4) - 8)) in tiles
    return hits


def edges(sym, g, nexthop, base):
    large = [d for d in range(EC.MAX_DOME)
             if base.e.dome[d * EC.DOME_REC + EC.D_STATE]
             and base.e.dome[d * EC.DOME_REC + EC.D_SIZE] == 2]
    if not large:
        print("ΑΠΟΤΥΧΙΑ άκρες: η αποικία της δοκιμής δεν έχει θόλο L")
        return 1
    st = fresh(g, nexthop, base)
    r = large[0] * EC.DOME_REC
    st.e.meteor = LONG_N
    st.e.mcx, st.e.mcy = EC._s8(st.e.dome[r]) >> 1, EC._s8(st.e.dome[r + 1]) >> 1
    tiles = edge_tiles(st.e)
    st.e.mrnd = max(range(1, 400), key=lambda v: edge_hits(st.e, v, LONG_N, tiles))
    edge = edge_hits(st.e, st.e.mrnd, LONG_N, tiles)
    want = fresh(g, nexthop, st)
    slot15(want, LONG_N)
    keys = lambda z: (bytes(z.e.dome), bytes(z.e.struct), econ_bytes(z.e),
                      bytes(z.e.job))

    def z80(patch=()):
        got = run_z80(sym, g, fresh(g, nexthop, st), LONG_N, pin=15,
                      rt_n=EC.MAX_DOME + EC.MAX_STRUCT, patch=patch)
        return (got[3], got[4], got[5], got[6]), got[2]

    got, frames = z80()
    hit = sum(1 for a, b in zip(bytes(st.e.dome) + bytes(st.e.struct),
                                want.e.dome + want.e.struct) if a != b)
    if got != keys(want) or not edge or want.e.meteor:
        bad = [(k, [(i, x, y) for i, (x, y) in enumerate(zip(a, b)) if x != y][:6])
               for k, (a, b) in enumerate(zip(got, keys(want))) if a != b]
        print(f"ΑΠΟΤΥΧΙΑ άκρες: {LONG_N} κρούσεις ({edge} στην άκρη θόλου L), "
              f"διαφέρουν τα {bad}")
        return 1
    # ΑΡΝΗΤΙΚΟ: CP 9 μετά το SUB B του msc_lp -> CP 8. Από το βήμα 87 το B
    # είναι ήδη x - MT_REACH (χωρίς το ADD A,4 σε κάθε εγγραφή), οπότε ένα
    # παράθυρο 0..7 είναι MT_REACH 3 στην αριστερή μεριά — εκεί που πέφτουν.
    at = sym["MSC_LP"]
    code = [0x7E, 0xCB, 0x2F, 0x90, 0xFE, 0x09]
    m_code = list(base_code(sym, at, len(code)))
    if m_code != code:
        print(f"ΑΠΟΤΥΧΙΑ άκρες: το msc_lp δεν είναι αυτό που περιμένει η δοκιμή "
              f"{[hex(v) for v in m_code]}")
        return 1
    neg, _ = z80([(at + 5, 8)])
    if neg == keys(want):
        print(f"ΑΠΟΤΥΧΙΑ άκρες: με MT_REACH 3 ο Z80 συμφωνεί ακόμη — η δοκιμή "
              f"δεν βλέπει τις άκρες")
        return 1
    print(f"OK μετεωρίτες: {LONG_N} κρούσεις γύρω από θόλο L, {edge} στην "
          f"αριστερή του στήλη, {hit} bytes κτιρίων άλλαξαν — ίδια στον Z80 και "
          f"στην αναφορά. ΑΡΝΗΤΙΚΟ: με MT_REACH 3 διαφέρουν")
    print(f"              {frames * FRAME_US / LONG_N:.0f} us ανά κρούση "
          f"(θέση 15 καρφωμένη, {sum(1 for n in range(96) if EC._node_rec(st.e, n)[0][EC._node_rec(st.e, n)[1] + EC.D_STATE])} κτίρια)")
    return 0


def base_code(sym, at, n):
    """Τα bytes του κώδικα όπως τα συναρμολόγησε ο rasm, από το στιγμιότυπο."""
    from cpc import CPC
    m = CPC()
    m.run_frames(60)
    assert m.quickload(SNA, start=False), "quickload απέτυχε"
    return m.read_ram(at, n)


def meteors(sym, g, nexthop, sim0):
    """Η βροχή στον Z80 και στην αναφορά, byte προς byte (§6.10)."""
    base = fresh(g, nexthop, sim0)
    spread(base.e)
    EC.rooms_rebuild(base.e, base.pc)

    # 1. Η ζαριά: μια κατάσταση της γεννήτριας που δίνει «δώδεκα ψηλά bits
    # ένα» στο ΕΠΟΜΕΝΟ τράβηγμα, και η διπλανή της που δεν δίνει.
    for want_on in (True, False):
        x = next(v for v in range(1, 65536)
                 if (EC.lfsr(v) >> 4 == 0xFFF) == want_on
                 and (want_on or EC.lfsr(v) >> 4 == 0xFFE))
        st = fresh(g, nexthop, base)
        st.e.rnd = x
        sim = same(sym, g, nexthop, st, 20, "ζαριά μετεωριτών")
        if sim is None:
            return 1
        on = sim.e.meteor > 0
        live = any(sim.e.dome[d * EC.DOME_REC + EC.D_STATE]
                   and (EC._s8(sim.e.dome[d * EC.DOME_REC]) >> 1) == sim.e.mcx
                   and (EC._s8(sim.e.dome[d * EC.DOME_REC + 1]) >> 1) == sim.e.mcy
                   for d in range(EC.MAX_DOME)) or any(
                   sim.e.struct[k * 8 + EC.ST_STATE]
                   and (EC._s8(sim.e.struct[k * 8]) >> 1) == sim.e.mcx
                   and (EC._s8(sim.e.struct[k * 8 + 1]) >> 1) == sim.e.mcy
                   for k in range(EC.MAX_STRUCT))
        if on != want_on or (on and not live):
            print(f"ΑΠΟΤΥΧΙΑ ζαριά: r1 = #{EC.lfsr(x):04X}, βροχή {sim.e.meteor}, "
                  f"κέντρο {(sim.e.mcx, sim.e.mcy)} {'σε κτίριο' if live else 'ΣΤΟ ΚΕΝΟ'}")
            return 1
        print(f"OK μετεωρίτες: r1 = #{EC.lfsr(x):04X} -> "
              + (f"βροχή {sim.e.meteor} κρούσεων γύρω από το {(sim.e.mcx, sim.e.mcy)}, "
                 f"ίδια στον Z80" if on else "καμία βροχή, ίδια στον Z80"))

    # 2. Η βροχή: κέντρο η δομή 0, σπόρος 1 — δύο κρούσεις σε θόλο, μία σε
    # δομή, πέντε στο έδαφος (βρέθηκε με την αναφορά).
    st = fresh(g, nexthop, base)
    st.e.meteor, st.e.mrnd = EC.METEOR_N, 1
    st.e.mcx = EC._s8(st.e.struct[EC.ST_CX]) >> 1
    st.e.mcy = EC._s8(st.e.struct[EC.ST_CY]) >> 1
    sim = same(sym, g, nexthop, st, METEOR_TICKS, "βροχή μετεωριτών")
    if sim is None:
        return 1
    # ΤΙ ΕΓΙΝΕ ΣΤΗ ΔΙΑΔΡΟΜΗ, στην αναφορά — που μόλις βγήκε ίδια με τον Z80:
    # οι μηχανές που σταμάτησαν έχουν επισκευαστεί ως το τέλος.
    walk = fresh(g, nexthop, st)
    broke = fixed = 0
    prev = bytes(walk.e.dome)
    sites, jobs = set(), 0
    for _ in range(METEOR_TICKS):
        walk.tick()
        now = bytes(walk.e.dome)
        for d in range(EC.MAX_DOME):
            for k in range(8):
                i = d * EC.DOME_REC + EC.D_HEALTH + k
                broke += bool(prev[i] and not now[i])
                fixed += bool(not prev[i] and now[i])
        prev = now
        sites |= {k for k in range(EC.MAX_STRUCT)
                  if walk.e.struct[k * 8 + EC.ST_STATE] == EC.DS_BUILDING}
        jobs = max(jobs, sum(1 for k in range(EC.MAX_JOB)
                             if walk.e.job[k * EC.JOB_REC + EC.J_KIND] == EC.J_BUILD))
    # Η δομή που χτυπήθηκε έγινε εργοτάξιο, πήρε εργασία Build, και — από το
    # βήμα 95, που οι δομές της αποικίας μπήκαν στον γράφο (colony_graph) —
    # ξαναχτίστηκε ως το τέλος. Ως τότε καμία δομή δεν φτανόταν, και έμενε
    # εργοτάξιο· το ξαναχτίσιμο το έλεγχε μόνο το tests/test_meteor.py.
    rebuilt = [k for k in sites
               if sim.e.struct[k * 8 + EC.ST_STATE] == EC.DS_ACTIVE]
    if sim.e.meteor or not broke or not sites or not jobs or rebuilt != sorted(sites):
        print(f"ΑΠΟΤΥΧΙΑ βροχή: έμειναν {sim.e.meteor} κρούσεις, {broke} μηχανές "
              f"σταμάτησαν, δομές εργοτάξια {sorted(sites)}, ξαναχτισμένες {rebuilt}, "
              f"ως {jobs} εργασίες Build")
        return 1
    print(f"OK μετεωρίτες: οκτώ κρούσεις, {broke} μηχανές σταμάτησαν ({fixed} "
          f"επισκευάστηκαν), {len(sites)} δομή ξανά εργοτάξιο με εργασία Build, "
          f"και ξαναχτίστηκε — {METEOR_TICKS} frames, ίδια bytes στον Z80 και στην αναφορά")

    # 4. ΟΙ ΑΚΡΕΣ ΤΩΝ ΑΠΟΤΥΠΩΜΑΤΩΝ (mt_scan). Ο Z80 ρωτά το αποτύπωμα μόνο
    # για κτίρια με κέντρο ως MT_REACH tiles μακριά στο x· η αναφορά τα ρωτά
    # όλα. Μια μακριά βροχή με τον τροχό καρφωμένο στη θέση 15 — μία κρούση
    # ανά frame — και ένας σπόρος που ρίχνει κρούσεις στην αριστερή στήλη
    # θόλων L, τέσσερα tiles από το κέντρο: εκεί θα έχανε ένα μικρότερο όριο.
    # ΑΡΝΗΤΙΚΟ: με MT_REACH 3 ο Z80 ΠΡΕΠΕΙ να διαφωνήσει.
    if edges(sym, g, nexthop, base):
        return 1

    # 3. Και η κατασκευή η ίδια (ja_build), που η αναφορά δεν ήξερε ως το
    # βήμα 38: ένας θόλος γίνεται εργοτάξιο και κάποιος έρχεται να τον χτίσει.
    st = fresh(g, nexthop, base)
    b = 0 * EC.DOME_REC
    st.e.dome[b + EC.D_STATE], st.e.dome[b + EC.D_INTEG] = EC.DS_BUILDING, 0
    EC.post_build(st.e, 0)
    sim = same(sym, g, nexthop, st, METEOR_TICKS, "κατασκευή")
    if sim is None:
        return 1
    if sim.e.dome[b + EC.D_STATE] != EC.DS_ACTIVE:
        print(f"ΑΠΟΤΥΧΙΑ κατασκευή: ο θόλος 0 έμεινε εργοτάξιο, ακεραιότητα "
              f"{sim.e.dome[b + EC.D_INTEG]}")
        return 1
    print(f"OK κατασκευή:  ένα εργοτάξιο ξαναχτίστηκε, ίδια bytes στον Z80 και "
          f"στην αναφορά")

    # 5. Ο ΙΔΙΟΣ Ο ΤΡΟΧΟΣ (βήμα 65), και τέσσερα αρνητικά: με τον προϋπολογισμό
    # της δρομολόγησης ένα λιγότερο, με την 6 να μένει στο παράθυρο, με τις
    # σβηστές θέσεις να τρέχουν, και με το wheel_reset να μη μηδενίζει τη θέση
    # ή την αποθήκη (βήμα 122).
    why = wheel_check(sym, g, nexthop, base)
    if why:
        print(f"ΑΠΟΤΥΧΙΑ τροχός: {why}")
        return 1
    print(f"OK τροχός:     η δρομολόγηση σε ακριβώς ⌈μονάδες / {WH_RT_B}⌉ frames με την 1 "
          f"στο παράθυρο μετά από καθένα, οι σβηστές θέσεις δεν αγγίζουν τίποτα, το "
          f"wheel_reset ξεκινά από τη θέση 0 με την αποθήκη να χωρά")
    m = boot_only()
    wt, wf, wr = sym["WHEEL_TICK"], sym["WH_FRAME"], sym["WHEEL_RESET"]
    find = lambda at, pat, n=64: next((at + k for k in range(n)
                                       if list(m.read_ram(at + k, len(pat))) == pat), None)
    b_at = find(wf, [0x06, WH_RT_B])                         # ld b,WH_RT_B
    w_at = find(wt + 3, [0x01, 0xC0, 0x7F])                  # ld bc,GA_PORT + PAGE_B1
    o_at = find(wf + 10, [0xB7, 0xC8])                       # or a · ret z (wh_on)
    r_at = find(wr, [0xAF, 0x32], 4)                         # xor a · ld (wh_slot),a
    sf = sym["EC_SETFULL"]
    f_at = find(wr, [0xCD, sf & 255, sf >> 8], 16)           # call ec_setfull
    ek = sym["EC_KEEP"]
    k_at = find(wr, [0x32, ek & 255, ek >> 8], 16)           # ld (ec_keep),a (βήμα 127)
    for label, patch in (("προϋπολογισμός ένα λιγότερο", b_at and [(b_at + 1, WH_RT_B - 1)]),
                         ("η 6 μένει στο παράθυρο", w_at and [(w_at + 1, 0xC6)]),
                         ("οι σβηστές θέσεις τρέχουν", o_at and [(o_at + 1, 0x00)]),
                         ("το wheel_reset κρατά τη θέση", r_at and [(r_at + 1, 0), (r_at + 2, 0),
                                                                  (r_at + 3, 0)]),
                         ("το wheel_reset κρατά τη γεμάτη αποθήκη",
                          f_at and [(f_at, 0), (f_at + 1, 0), (f_at + 2, 0)]),
                         ("το wheel_reset κρατά το απόθεμα μετάλλου",
                          k_at and [(k_at, 0), (k_at + 1, 0), (k_at + 2, 0)])):
        if not patch or wheel_check(sym, g, nexthop, base, patch) is None:
            print(f"ΑΠΟΤΥΧΙΑ ΑΡΝΗΤΙΚΟ τροχού: με «{label}» ο έλεγχος πέρασε")
            return 1
        print(f"OK ΑΡΝΗΤΙΚΟ τροχού: με «{label}» ο έλεγχος αποτυγχάνει")
    return 0


WH_RT_B = 15                    # src/wheel.asm, DESIGN §7.2

SUPPLY_TICKS = 2400             # 150 περιστροφές: ταξίδια, παραδόσεις, χτίσιμο (2.173 με αποθήκη)
SITES = ((12, 2, 1), (5, 0, 2), (9, 3, 0))      # θόλος, φορτία μετάλλου, βιοπλαστικού


def supply_scene(g, nexthop, sim0, storage=True):
    """Τρεις θόλοι της αποικίας ξαναγίνονται εργοτάξια που χρωστούν φορτία, με
    τις εργασίες Supply τους, όπως τα αφήνει το sp_place. Οι χειριστές τους
    σταματούν (το D_OPS είναι πια χρέος· στο παιχνίδι ένας θόλος δεν γυρίζει
    ποτέ πίσω σε εργοτάξιο). Χωρίς αποθήκη, ο θόλος της γίνεται σαλόνι."""
    st = fresh(g, nexthop, sim0)
    for d, m, b in SITES:
        r = d * EC.DOME_REC
        st.e.dome[r + EC.D_STATE], st.e.dome[r + EC.D_INTEG] = EC.DS_BUILDING, 0
        st.e.dome[r + EC.D_POWER], st.e.dome[r + EC.D_OPS] = m, b
        for i in range(EC.MAXAGENT_J):
            if st.a.node[i] == d:
                st.a.flags[i] &= ~E.F_WORKING & 0xFF
        if m:
            EC.post_supply(st.e, d, EC.J_SUPPLY)
        if b:
            EC.post_supply(st.e, d, EC.J_SUPPLY + 1)
    if not storage:
        for d in range(EC.MAX_DOME):
            if st.e.dome[d * EC.DOME_REC + EC.D_ROOM] == EC.R_STORAGE:
                st.e.dome[d * EC.DOME_REC + EC.D_ROOM] = EC.R_LOUNGE
    EC.rooms_rebuild(st.e, st.pc)
    return st


def supply(sym, g, nexthop, sim0):
    """Η τροφοδοσία στον Z80 και στην αναφορά, byte προς byte, και τι έγινε.

    Με αποθήκη: η πηγή είναι η αποθήκη (το σκάφος δεν υπάρχει σε αυτή την
    αποικία, και ο γράφος της δεν φτάνει δομές). Χωρίς: κατευθείαν στο
    εργοτάξιο. Και στα δύο: φορτία φεύγουν, τα χρέη πέφτουν στο μηδέν, η Build
    έρχεται ΜΕΤΑ, και την παίρνει μόνο μηχανικός ή ρομπότ κατασκευής.
    ΑΡΝΗΤΙΚΑ: ο Z80 χωρίς αποθήκες στην πηγή, και με το «κι άλλο ταξίδι» να
    κλείνει την εργασία, ΠΡΕΠΕΙ να διαφωνήσει με την αναφορά.
    """
    for storage in (True, False):
        what = "τροφοδοσία " + ("από αποθήκη" if storage else "χωρίς πηγή")
        st = supply_scene(g, nexthop, sim0, storage)
        if same(sym, g, nexthop, st, SUPPLY_TICKS, what) is None:
            return 1
        # ΤΙ ΕΓΙΝΕ, στην αναφορά — που μόλις βγήκε ίδια με τον Z80
        walk = fresh(g, nexthop, st)
        store = walk.e.room_list[EC.R_STORAGE * EC.ROOM_MAX] if storage else None
        carried = at_store = 0
        builders, early = set(), []
        for _ in range(SUPPLY_TICKS):
            walk.tick()
            jb = walk.e.job
            carried = max(carried, sum(1 for i in range(EC.MAXAGENT_J) if walk.a.spare[i]))
            for j in range(EC.MAX_JOB):
                b = j * EC.JOB_REC
                k = jb[b + EC.J_KIND]
                if k >= EC.J_SUPPLY and jb[b + EC.J_NODE] == store:
                    at_store += 1
                if k == EC.J_BUILD and jb[b + EC.J_AGENT] != 255:
                    builders.add(walk.a.role[jb[b + EC.J_AGENT]])
                if k == EC.J_BUILD:
                    r = jb[b + EC.J_NODE] * EC.DOME_REC
                    if walk.e.dome[r + EC.D_POWER] or walk.e.dome[r + EC.D_OPS]:
                        early.append(jb[b + EC.J_NODE])
        done = [d for d, _, _ in SITES
                if walk.e.dome[d * EC.DOME_REC + EC.D_STATE] == EC.DS_ACTIVE]
        owed = [walk.e.dome[d * EC.DOME_REC + EC.D_POWER] + walk.e.dome[d * EC.DOME_REC + EC.D_OPS]
                for d, _, _ in SITES]
        # χωρίς πηγή κανείς δεν φορτώνει: πηγαίνει κατευθείαν, με άδειο spare
        if (bool(carried) != storage or bool(at_store) != storage
                or early or not builders or builders - {E.ENGINEER, E.BOT_CONSTR}
                or len(done) != len(SITES) or any(owed)):
            print(f"ΑΠΟΤΥΧΙΑ {what}: ως {carried} κουβαλούσαν μαζί, {at_store} δείγματα "
                  f"με πηγή την αποθήκη, Build πριν από τα υλικά {early[:3]}, χτίστες "
                  f"ρόλων {sorted(builders)}, χτίστηκαν {done}, χρωστιούνται {owed}")
            return 1
        print(f"OK {what}: ως {carried} άποικοι κουβαλούσαν μαζί"
              + (f", η αποθήκη πηγή σε {at_store} δείγματα" if storage else
                 ", κανείς δεν πήγε σε πηγή ούτε φόρτωσε")
              + f"; τα {len(SITES)} εργοτάξια πήραν όλα τους τα φορτία και μετά "
              f"Build, μόνο από ρόλους {sorted(builders)}; ίδια bytes στον Z80")

    # ΑΡΝΗΤΙΚΑ: ο Z80 αλλαγμένος, η αναφορά όχι
    st = supply_scene(g, nexthop, sim0, True)
    m = boot_only()
    find = lambda at, pat, n=160: next((at + k for k in range(n)
                                        if list(m.read_ram(at + k, len(pat))) == pat), None)
    rn = sym["G_ROOM_N"] + EC.R_STORAGE
    s_at = find(sym["SP_TAKE"], [0x3A, rn & 255, rn >> 8])          # ld a,(G_room_n + R_STORAGE)
    c_at = find(sym["JA_SUPPLY"], [0x38], 6)                         # jr c,ja_fail
    for label, patch in (("χωρίς αποθήκες στην πηγή", s_at and [(s_at, 0xAF), (s_at + 1, 0),
                                                                (s_at + 2, 0)]),
                         ("το «κι άλλο ταξίδι» κλείνει την εργασία", c_at and [(c_at, 0), (c_at + 1, 0)])):
        if not patch or same(sym, g, nexthop, st, SUPPLY_TICKS, label, patch, quiet=True):
            print(f"ΑΠΟΤΥΧΙΑ ΑΡΝΗΤΙΚΟ τροφοδοσίας: με «{label}» ο Z80 συμφώνησε")
            return 1
        print(f"OK ΑΡΝΗΤΙΚΟ τροφοδοσίας: με «{label}» ο Z80 διαφωνεί με την αναφορά")
    return 0


CARRY_TICKS = 2400              # 150 περιστροφές: τέσσερα φορτία για τον έμπορο, τρία δικά του
CARRY_PAD = 12                  # η «πίστα»: ο γράφος της αποικίας δεν φτάνει δομές


def carry_scene(g, nexthop, sim0, storage=True):
    """Ο έμπορος μόλις έκλεισε συμφωνία, με τη συμφωνία της αναφοράς (EC.trade):
    12 μέταλλα και ένας επεξεργαστής (252 + 56) για 31 μεταλλεύματα (310) —
    τέσσερα φορτία για τον έμπορο (10, 10, 10, 1), τρία δικά του (10, 2, 1).
    Η «πίστα» είναι ένας θόλος. Χωρίς αποθήκη, ο θόλος της γίνεται σαλόνι."""
    st = fresh(g, nexthop, sim0)
    e = st.e
    if not storage:
        for d in range(EC.MAX_DOME):
            if e.dome[d * EC.DOME_REC + EC.D_ROOM] == EC.R_STORAGE:
                e.dome[d * EC.DOME_REC + EC.D_ROOM] = EC.R_LOUNGE
    EC.rooms_rebuild(e, st.pc)
    e.pad_node = CARRY_PAD
    e.ship_state, e.ship_kind, e.ship_eta, e.markup = EC.SHIP_LANDED, EC.SK_MERCHANT, 100, 40
    e.cargo = [EC.S_METAL, 12, EC.S_PROC, 6, EC.S_BOT, 2, 0, 0]
    e.stock[EC.S_ORE], e.stock[EC.S_METAL], e.stock[EC.S_PROC] = 100, 50, 0
    net = [0] * EC.N_STOCK
    net[EC.S_METAL], net[EC.S_PROC], net[EC.S_ORE] = 12, 1, -31
    assert EC.trade(e, net)
    return st


def carry(sym, g, nexthop, sim0):
    """Η μεταφορά στον Z80 και στην αναφορά, byte προς byte, και τι έγινε.

    Με αποθήκη: οι μεταφορείς ανάμεσα στην πίστα και στην αποθήκη. Χωρίς:
    όλα στην πίστα. Και στα δύο: +12 μέταλλα και +1 επεξεργαστής, ένα φορτίο τη
    φορά, ο έμπορος φεύγει μετά το τελευταίο, καμία J_TRADE στο τέλος.
    ΑΡΝΗΤΙΚΑ: ο Z80 χωρίς το «ως δέκα», και με τον έμπορο που δεν φεύγει ποτέ,
    ΠΡΕΠΕΙ να διαφωνήσει με την αναφορά. (Το μάζεμα που γυρίζει τη J_TRADE στο
    J_SITE της δεν φαίνεται εδώ: κανείς δεν την αφήνει στη μέση· το πιάνει το
    tests/test_carry.py.)
    """
    for storage in (True, False):
        what = "μεταφορά " + ("από αποθήκη" if storage else "χωρίς αποθήκη")
        st = carry_scene(g, nexthop, sim0, storage)
        if same(sym, g, nexthop, st, CARRY_TICKS, what) is None:
            return 1
        # ΤΙ ΕΓΙΝΕ, στην αναφορά: ό,τι λείπει από το φορτίο του εμπόρου είναι
        # ένα φορτίο που πάρθηκε, και ένα φορτίο του που φεύγει από το J_SITE
        # μιας J_TRADE μια παράδοση — χωρίς αποθήκη, στο ίδιο tick, οπότε δεν
        # φαίνεται. Τα αποθέματα δεν μετρούν: αλλάζουν και από τα εργοστάσια.
        walk = fresh(g, nexthop, st)
        store = walk.e.room_list[EC.R_STORAGE * EC.ROOM_MAX] if storage else None
        picks, drops, at_store, left, carriers = [], [], 0, None, set()
        held, cargo = {}, list(walk.e.cargo)
        for t in range(CARRY_TICKS):
            walk.tick()
            for k in range(1, 8, 2):
                if walk.e.cargo[k] != cargo[k]:
                    picks.append((cargo[k] - walk.e.cargo[k], cargo[k - 1], walk.e.ship_state))
            cargo = list(walk.e.cargo)
            jb = walk.e.job
            now = {}
            for b in range(0, EC.MAX_JOB * EC.JOB_REC, EC.JOB_REC):
                if jb[b + EC.J_KIND] == EC.J_TRADE:
                    now[b] = jb[b + EC.J_SITE]
                    at_store += jb[b + EC.J_NODE] == store
                    if jb[b + EC.J_AGENT] != 255:
                        carriers.add(jb[b + EC.J_AGENT])
            for b, ld in held.items():
                if ld > EC.TRADE_GIVE and now.get(b) != ld:
                    drops.append((ld >> 4, ld & 15, walk.e.ship_state))
            held = now
            if left is None and walk.e.ship_state == EC.SHIP_NONE:
                left = t
        want = [(10, EC.S_METAL, EC.SHIP_LANDED), (2, EC.S_METAL, EC.SHIP_LANDED),
                (1, EC.S_PROC, EC.SHIP_LANDED)]
        if (picks != want or sorted(drops) != (sorted(want) if storage else [])
                or left is None or held or bool(at_store) != storage or len(carriers) < 2):
            print(f"ΑΠΟΤΥΧΙΑ {what}: πάρθηκαν {picks}, παραδόσεις {drops} (μονάδες, "
                  f"απόθεμα, πλοίο), έφυγε "
                  f"{left}, J_TRADE στο τέλος {len(held)}, {at_store} δείγματα προς την "
                  f"αποθήκη, μεταφορείς {sorted(carriers)}")
            return 1
        print(f"OK {what}: {len(carriers)} μεταφορείς, 10 + 2 μέταλλα και 1 επεξεργαστής "
              + ("κουβαλήθηκαν ως την αποθήκη" if storage else "παραδόθηκαν στην πίστα")
              + f" με τον έμπορο εδώ, και φεύγει στο tick {left}"
              + (f", {at_store} δείγματα προς την αποθήκη" if storage else "")
              + "; ίδια bytes στον Z80")

    # ΑΡΝΗΤΙΚΑ: ο Z80 αλλαγμένος, η αναφορά όχι
    st = carry_scene(g, nexthop, sim0, True)
    m = boot_only()
    find = lambda at, pat, n=200: next((at + k for k in range(n)
                                        if list(m.read_ram(at + k, len(pat))) == pat), None)
    l_at = find(sym["TR_ARRIVE"], [0xD6, EC.TRADE_LOAD, 0x30])      # sub TRADE_LOAD · jr nc
    const = open(os.path.join(ROOT, "src", "const.asm"), encoding="utf-8").read()
    eta = sym["G_ECON_STATE"] + int(re.search(r"^EC_SHETA\s+equ G_econ_state \+ (\d+)",
                                              const, re.M).group(1))
    e_at = find(sym["TRA_BYE"], [0x22, eta & 255, eta >> 8], 60)      # ld (EC_SHETA),hl
    for label, patch in (("χωρίς το «ως δέκα»", l_at and [(l_at + 1, 0)]),
                         ("ο έμπορος δεν φεύγει ποτέ", e_at and [(e_at, 0), (e_at + 1, 0),
                                                                 (e_at + 2, 0)])):
        if not patch or same(sym, g, nexthop, st, CARRY_TICKS, label, patch, quiet=True):
            print(f"ΑΠΟΤΥΧΙΑ ΑΡΝΗΤΙΚΟ μεταφοράς: με «{label}» ο Z80 συμφώνησε")
            return 1
        print(f"OK ΑΡΝΗΤΙΚΟ μεταφοράς: με «{label}» ο Z80 διαφωνεί με την αναφορά")
    return 0


MACH_TICKS = 2400               # 150 περιστροφές: φορτία, Build, τέσσερα στησίματα ανά μηχανή
STAGE = {EC.MACH_OWED: 0, 5: 1, 6: 1, EC.MACH_READY: 2, 36: 3, 68: 4, 100: 5, EC.MACH_HP: 6}


def mach_scene(g, nexthop, sim0):
    """Μηχανές που μόλις μπήκαν στο FIT (βήμα 99): οι δύο πρώτες υποδοχές με
    μηχανή σε δύο θόλους σε λειτουργία (μεσαίοι ή μεγάλοι, όχι θερμοκήπια), και
    η πρώτη ενός θόλου που ξαναγίνεται εργοτάξιο που χρωστά (όπως στο
    supply_scene). Υγεία MACH_OWED, και οι Supply του mc_order."""
    st = fresh(g, nexthop, sim0)
    e, picked = st.e, []
    for d in range(EC.MAX_DOME):
        r = d * EC.DOME_REC
        if (e.dome[r + EC.D_STATE] != EC.DS_ACTIVE or e.dome[r + EC.D_SIZE] == 0
                or e.dome[r + EC.D_ROOM] == EC.R_GREENHOUSE or d == SITES[0][0]):
            continue
        slots = [k for k in range(EC.MACHINE_COUNT[e.dome[r + EC.D_SIZE]])
                 if e.dome[r + EC.D_MACH + k] != EC.NO_MACH][:2]
        if len(slots) < 2:
            continue
        for k in slots:
            e.dome[r + EC.D_HEALTH + k] = EC.MACH_OWED
        EC.order_machine(e, d)
        picked.append((d, slots))
        if len(picked) == 2:
            break
    d, mt, bi = SITES[0]
    r = d * EC.DOME_REC
    e.dome[r + EC.D_STATE], e.dome[r + EC.D_INTEG] = EC.DS_BUILDING, 0
    e.dome[r + EC.D_POWER], e.dome[r + EC.D_OPS] = mt, bi
    for i in range(EC.MAXAGENT_J):
        if st.a.node[i] == d:
            st.a.flags[i] &= ~E.F_WORKING & 0xFF
    k = next(k for k in range(EC.MACHINE_COUNT[e.dome[r + EC.D_SIZE]])
             if e.dome[r + EC.D_MACH + k] != EC.NO_MACH)
    e.dome[r + EC.D_HEALTH + k] = EC.MACH_OWED
    if mt:
        EC.post_supply(e, d, EC.J_SUPPLY)
    if bi:
        EC.post_supply(e, d, EC.J_SUPPLY + 1)
    EC.order_machine(e, d)
    picked.append((d, [k]))
    EC.rooms_rebuild(e, st.pc)
    return st, picked


def machines(sym, g, nexthop, sim0):
    """Οι μηχανές κουβαλιούνται και στήνονται (βήμα 99), στον Z80 και στην
    αναφορά, byte προς byte, και τι έγινε: κάθε υποδοχή περνά τα στάδια με τη
    σειρά (7, 5 ή 6, 4, 36, 68, 100, 200) και φτάνει στο 200· ΜΙΑ Supply ανά
    υλικό ανά θόλο· τις Build τις παίρνει μόνο μηχανικός ή ρομπότ κατασκευής.
    ΑΡΝΗΤΙΚΑ: ο Z80 χωρίς τη Build της μηχανής, και με την παραγωγή να τρέχει
    κάθε υγεία όχι μηδέν όπως ως το 98, ΠΡΕΠΕΙ να διαφωνήσει με την αναφορά."""
    what = "μηχανές που κουβαλιούνται"
    st, picked = mach_scene(g, nexthop, sim0)
    sup = sorted((st.e.job[b], st.e.job[b + EC.J_SITE]) for b in range(0, 160, 5)
                 if st.e.job[b] in (EC.J_SUPPLY, EC.J_SUPPLY + 1))
    if sup != sorted((k, d) for d, _ in picked for k in (EC.J_SUPPLY, EC.J_SUPPLY + 1)):
        print(f"ΑΠΟΤΥΧΙΑ {what}: οι Supply στην αρχή {sup}, θόλοι {picked}")
        return 1
    if same(sym, g, nexthop, st, MACH_TICKS, what) is None:
        return 1
    walk = fresh(g, nexthop, st)
    seen = {(d, k): [EC.MACH_OWED] for d, ks in picked for k in ks}
    builders, done_at = set(), {}
    for t in range(MACH_TICKS):
        walk.tick()
        for (d, k), hist in seen.items():
            h = walk.e.dome[d * EC.DOME_REC + EC.D_HEALTH + k]
            if (d, k) not in done_at and h != hist[-1]:
                hist.append(h)
                if h == EC.MACH_HP:
                    done_at[(d, k)] = t
        jb = walk.e.job
        for b in range(0, EC.MAX_JOB * EC.JOB_REC, EC.JOB_REC):
            if jb[b] == EC.J_BUILD and jb[b + EC.J_AGENT] != 255:
                builders.add(walk.a.role[jb[b + EC.J_AGENT]])
    bad = {s: h for s, h in seen.items()
           if any(v not in STAGE for v in h) or h[-1] != EC.MACH_HP
           or [STAGE[v] for v in h] != sorted(STAGE[v] for v in h)}
    if bad or not builders or builders - {E.ENGINEER, E.BOT_CONSTR}:
        print(f"ΑΠΟΤΥΧΙΑ {what}: υγείες εκτός σειράς {bad}, χτίστες ρόλων {sorted(builders)}")
        return 1
    print(f"OK {what}: {len(seen)} υποδοχές σε {len(picked)} θόλους (ο τελευταίος "
          f"εργοτάξιο) πέρασαν τα στάδια ως το 200, στα ticks {sorted(done_at.values())}; "
          f"Build από ρόλους {sorted(builders)}; ίδια bytes στον Z80")

    # ΑΡΝΗΤΙΚΑ: ο Z80 αλλαγμένος, η αναφορά όχι
    m = boot_only()
    find = lambda at, pat, n=60: next((at + k for k in range(n)
                                       if list(m.read_ram(at + k, len(pat))) == pat), None)
    sb = sym["SP_BUILD"]
    b_at = find(sym["MCA_GOT"], [0xC4, sb & 255, sb >> 8])          # call nz,sp_build
    p_at = find(sym["ERD_LP"], [0xCB, 0x7E, 0xC4], 24)               # bit 7,(hl) · call nz
    for label, patch in (("καμία Build για τη μηχανή", b_at and [(b_at, 0), (b_at + 1, 0),
                                                                (b_at + 2, 0)]),
                         ("παραγωγή με «υγεία όχι μηδέν»", p_at and [(p_at, 0x34),
                                                                     (p_at + 1, 0x35)])):
        if not patch or same(sym, g, nexthop, st, MACH_TICKS, label, patch, quiet=True):
            print(f"ΑΠΟΤΥΧΙΑ ΑΡΝΗΤΙΚΟ μηχανών: με «{label}» ο Z80 συμφώνησε")
            return 1
        print(f"OK ΑΡΝΗΤΙΚΟ μηχανών: με «{label}» ο Z80 διαφωνεί με την αναφορά")
    return 0


def boot_only():
    from cpc import CPC
    m = CPC()
    m.run_frames(60)
    assert m.quickload(SNA, start=False), "quickload απέτυχε"
    return m


def wheel_check(sym, g, nexthop, base, patch=()):
    """Ο τροχός απευθείας, wheel_tick ένα-ένα: η πρώτη διαφορά ή None.

      1. rt_mark και frames ως το rt_dirty = 0: ακριβώς ⌈Σ(R(s) + 2) / WH_RT_B⌉
         για τις 96 πηγές, και μετά από ΚΑΘΕ frame η τράπεζα 1 στο παράθυρο
         (§7.4: ο τροχός μπαίνει με την 6 και βγαίνει με την 1).
      2. όλες οι θέσεις σβηστές, 32 frames: η τράπεζα 6 και η οικονομία ίδιες.
      3. wheel_reset: wh_slot = 0 και rt_dirty = 0, και η αποθήκη «χωρά» —
         το ec_full και ο κώδικάς του (ec_setfull, βήμα 122): ένα νέο παιχνίδι
         μετά από μια γεμάτη αποικία δεν περιμένει τον κύκλο ροής.
    """
    import ctypes
    import cpc
    m = boot_only()
    sim = fresh(g, nexthop, base)
    m.write_ram(sym["G_NODE_ADJ"], bytes(g.adj))
    m.write_ram(sym["G_RT_NODES"], bytes(g.deg))
    m.poke(sym["RT_N"], 96)
    enter(m, sym, "BUILD_ROUTES")
    m.write_ram(STAGE_AG, sim.a.to_bytes())
    m.write_ram(STAGE_OCC, bytes(sim.occ) + bytes(128))
    m.write_ram(STAGE_DOME, bytes(sim.e.dome))
    m.write_ram(STAGE_STR, bytes(sim.e.struct))
    m.write_ram(sym["G_ECON_STATE"], EC.to_bytes(sim.e))
    m.write_ram(sym["G_JOB_TBL"], bytes(sim.e.job))
    m.write_ram(sym["G_ROOM_N"], bytes(sim.e.room_n))
    m.write_ram(sym["G_ROOM_LIST"], bytes(sim.e.room_list))
    enter(m, sym, "LOAD_STATE")
    for at, v in patch:
        m.poke(at, v)
    bank = lambda n, size=0x4000: ctypes.string_at(cpc._lib.cpcemu_ram_ptr(m._h, n), size)

    def run(name):
        a = sym[name]
        code = [0xF3, 0x31, 0x00, 0x01, 0xCD, a & 255, a >> 8,
                0x21, 0x00, 0x40, 0x11, 0x80, 0x3F, 0x01, 0x40, 0x00, 0xED, 0xB0,  # &4000 -> &3F80
                0x18, 0xFE]
        m.write_ram(0x3F00, bytes(code))
        m.set_pc(0x3F00)
        end = 0x3F00 + len(code) - 2
        for _ in range(4000):
            if end <= m.pc <= end + 2:
                return m.read_ram(0x3F80, 64)
            m.run_us(100)
        raise AssertionError(f"το {name} δεν γύρισε: #{m.pc:04X}")

    units = sum(2 + sum(1 for d in G.bfs_row(g, s)[0] if d != G.UNREACH) for s in range(96))
    want = -(-units // WH_RT_B)
    run("RT_MARK")
    n = 0
    while m.peek(sym["RT_DIRTY"]):
        seen = run("WHEEL_TICK")
        n += 1
        if seen != bank(1, 64) or seen == bank(6, 64):
            return f"μετά το frame {n} το &4000 δεν είναι η τράπεζα 1"
        if n > 2 * want:
            break
    if n != want:
        return f"η δρομολόγηση τελείωσε σε {n} frames, {units} μονάδες θέλουν {want}"
    for k in range(16):
        m.poke(sym["WH_ON"] + k, 0)
    before = (bank(6), m.read_ram(sym["G_ECON_STATE"], EC.ECON_BYTES))
    slot = m.peek(sym["WH_SLOT"])
    for _ in range(32):
        run("WHEEL_TICK")
    if (bank(6), m.read_ram(sym["G_ECON_STATE"], EC.ECON_BYTES)) != before:
        return "με όλες τις θέσεις σβηστές άλλαξαν η τράπεζα 6 ή η οικονομία"
    if m.peek(sym["WH_SLOT"]) != slot:
        return f"32 frames πήγαν το wh_slot από {slot} σε {m.peek(sym['WH_SLOT'])}"
    m.poke(sym["WH_SLOT"], 7)
    m.poke(sym["RT_DIRTY"], 1)
    inf, c3 = sym["ERM_INF"], sym["ERM_C3"] + 1
    full = lambda: (m.peek(sym["EC_FULL"]), m.peek(sym["ERP_FULL"]),
                    m.peek(c3) | m.peek(c3 + 1) << 8)
    for at, v in ((sym["EC_FULL"], 1), (sym["ERP_FULL"], 0xAF), (c3, inf & 255), (c3 + 1, inf >> 8)):
        m.poke(at, v)
    # και το απόθεμα μετάλλου (βήμα 127): το ec_keep και η πρώτη κλήση
    ink, c1 = sym["ERM_INK"], sym["ERM_C1"] + 1
    keep = lambda: (m.peek(sym["EC_KEEP"]), m.peek(c1) | m.peek(c1 + 1) << 8)
    for at, v in ((sym["EC_KEEP"], 1), (c1, ink & 255), (c1 + 1, ink >> 8)):
        m.poke(at, v)
    run("WHEEL_RESET")
    if (m.peek(sym["WH_SLOT"]), m.peek(sym["RT_DIRTY"])) != (0, 0):
        return f"μετά το wheel_reset wh_slot {m.peek(sym['WH_SLOT'])}, rt_dirty " \
               f"{m.peek(sym['RT_DIRTY'])}"
    if full() != (0, 0xB7, sym["ERM_IN"]):
        return "μετά το wheel_reset η αποθήκη μένει γεμάτη: ec_full, κήπος, τρίτη κλήση " \
               + ", ".join(f"#{v:02X}" for v in full())
    if keep() != (0, sym["ERM_IN"]):
        return "μετά το wheel_reset μένει το απόθεμα μετάλλου: ec_keep, πρώτη κλήση " \
               + ", ".join(f"#{v:02X}" for v in keep())
    return None


METEOR_TICKS = 1600             # 100 περιστροφές: οκτώ κρούσεις, δρόμος, χτίσιμο


if __name__ == "__main__":
    sys.exit(main())
