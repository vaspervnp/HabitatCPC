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


def run_z80(sym, g, sim, ticks, move_n=None, decay_n=None, off=(), pin=None,
            rt_n=None, patch=()):
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
    m.write_ram(STAGE_OCC, bytes(sim.occ) + bytes(128))
    m.write_ram(STAGE_DOME, bytes(sim.e.dome))
    m.write_ram(STAGE_STR, bytes(sim.e.struct))
    m.write_ram(sym["G_ECON_STATE"], EC.to_bytes(sim.e))   # τράπεζα 2, βασική
    m.write_ram(sym["G_JOB_TBL"], bytes(sim.e.job))
    m.write_ram(sym["G_ROOM_N"], bytes(sim.e.room_n))
    m.write_ram(sym["G_ROOM_LIST"], bytes(sim.e.room_list))
    enter(m, sym, "LOAD_STATE")

    for at, v in patch:                     # τα αρνητικά: κώδικας αλλαγμένος
        m.poke(at, v)
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

    enter(m, sym, "SAVE_STATE")
    return (m.read_ram(STAGE_AG, 2048), m.read_ram(STAGE_OCC, 128), frames,
            m.read_ram(STAGE_DOME, 1536), m.read_ram(STAGE_STR, 32 * 8),
            m.read_ram(sym["G_ECON_STATE"], EC.ECON_BYTES),
            m.read_ram(sym["G_JOB_TBL"], EC.MAX_JOB * EC.JOB_REC),
            m.read_ram(sym["G_ROOM_N"], 12) +
            m.read_ram(sym["G_ROOM_LIST"], 96))


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
    s.e.room_n = bytearray(src.e.room_n)
    s.e.room_list = bytearray(src.e.room_list)
    for f in ("power_store", "power_cap", "power_prod", "power_use",
              "mach_power", "o2_prod", "o2_use", "acc_power", "acc_o2",
              "power_ok", "o2_ok", "prod_dome", "day", "wind", "sol",
              "frame", "rnd", "n_dome", "n_struct", "job_dome", "job_agent",
              "alive", "gameover", "gloom", "storm", "amenity",
              "sollen", "daylen", "prod_mask", "ship_state", "ship_kind",
              "ship_eta", "pop_cap", "pad_node", "milestones", "deaths_sol",
              "no_death_sols", "green_sols", "no_trade_sols", "traded",
              "meteor", "mcx", "mcy", "mrnd"):
        setattr(s.e, f, getattr(src.e, f))
    return s


def main():
    sym = build()
    g = G.GRAPHS["colony"]()
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

    got_a, got_occ, frames, got_dome, got_str, got_econ, got_job, got_room = \
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
    want_econ = EC.to_bytes(sim.e)
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
                           "no_trade_sols", "traded", "pad_node"])]
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
    HAZ = TICKS * 4
    broke = repaired = storm_revs = 0
    landings = crew_landed = 0
    was_landed = False
    watch = fresh(g, nexthop, sim0)
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

    # Το εμπόριο είναι πράξη του παίκτη: εδώ δοκιμάζεται ο μηχανισμός.
    tr = fresh(g, nexthop, sim0)
    tr.e.ship_state, tr.e.ship_kind = EC.SHIP_LANDED, EC.SK_MERCHANT
    tr.e.no_trade_sols = 9
    before_metal = tr.e.stock[EC.S_METAL]
    if not EC.trade(tr.e, EC.S_ORE, 10, EC.S_METAL, 4):
        print("ΑΠΟΤΥΧΙΑ: η ανταλλαγή με τον έμπορο δεν έγινε")
        return 1
    if tr.e.stock[EC.S_METAL] != before_metal + 4 or not tr.e.traded:
        print("ΑΠΟΤΥΧΙΑ: η ανταλλαγή δεν άλλαξε τα αποθέματα σωστά")
        return 1
    print(f"OK πλοία:    {landings} προσγειώσεις, {crew_landed} άποικοι στην "
          f"πίστα (κόμβος {got_econ[81]}), ταβάνι {got_econ[74]}")
    print(f"OK ορόσημα:  {mile:05b} μετά από {watch.e.sol} sols "
          f"— εμπόριο δοκιμασμένο, το σερί έσπασε")

    # --- οι ανάγκες όντως δάγκωσαν; ---
    ag0 = E.Agents().from_bytes(sim0.a.to_bytes())
    agz = E.Agents().from_bytes(got_a)
    alive0 = sum(1 for i in range(128) if ag0.flags[i] & E.F_ALIVE)
    alive1 = sum(1 for i in range(128) if agz.flags[i] & E.F_ALIVE)
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

    # --- η βροχή μετεωριτών (§6.10, src/meteor.asm) ---
    if meteors(sym, g, nexthop, sim0):
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


def same(sym, g, nexthop, start, ticks, what):
    """Z80 και αναφορά από την ίδια κατάσταση: ΟΛΑ τα bytes ίδια. Επιστρέφει
    την αναφορά στο τέλος, ή None αν διαφέρουν."""
    got = run_z80(sym, g, fresh(g, nexthop, start), ticks, rt_n=EC.MAX_DOME + EC.MAX_STRUCT)
    sim = fresh(g, nexthop, start)
    for _ in range(ticks):
        sim.tick()
    want = (sim.a.to_bytes(), bytes(sim.occ), None, bytes(sim.e.dome),
            bytes(sim.e.struct), EC.to_bytes(sim.e), bytes(sim.e.job))
    for name, i in (("πεδία", 0), ("μάσκες", 1), ("θόλοι", 3), ("δομές", 4),
                    ("οικονομία", 5), ("εργασίες", 6)):
        if got[i] != want[i]:
            bad = [k for k in range(len(want[i])) if got[i][k] != want[i][k]]
            print(f"ΑΠΟΤΥΧΙΑ {what}: {name} — {len(bad)} bytes, πρώτα "
                  f"{[(k, got[i][k], want[i][k]) for k in bad[:4]]}")
            return None
    return sim


LONG_N = 120                # κρούσεις της μακριάς βροχής


def slot15(sim, n):
    """Η θέση 15 της αναφοράς, n φορές — ό,τι κάνει ο καρφωμένος τροχός."""
    for _ in range(n):
        if EC.events(sim.e):
            EC.sol_rollover(sim.e, sim.a, E.F_ALIVE, E.F_WORKING, E.NEED_LOW)
        EC.ship_tick(sim.e, sim.a, sim.e.pad_node, E.F_ALIVE)


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
    keys = lambda z: (bytes(z.e.dome), bytes(z.e.struct), EC.to_bytes(z.e),
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
    # ΑΡΝΗΤΙΚΟ: ADD A,4 / CP 9 μετά το SUB B του msc_lp -> ADD A,3 / CP 7
    at = sym["MSC_LP"]
    code = [0x7E, 0xCB, 0x2F, 0x90, 0xC6, 0x04, 0xFE, 0x09]
    m_code = list(base_code(sym, at, len(code)))
    if m_code != code:
        print(f"ΑΠΟΤΥΧΙΑ άκρες: το msc_lp δεν είναι αυτό που περιμένει η δοκιμή "
              f"{[hex(v) for v in m_code]}")
        return 1
    neg, _ = z80([(at + 5, 3), (at + 7, 7)])
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
    for _ in range(METEOR_TICKS):
        walk.tick()
        now = bytes(walk.e.dome)
        for d in range(EC.MAX_DOME):
            for k in range(8):
                i = d * EC.DOME_REC + EC.D_HEALTH + k
                broke += bool(prev[i] and not now[i])
                fixed += bool(not prev[i] and now[i])
        prev = now
    # Η δομή που χτυπήθηκε έγινε εργοτάξιο και πήρε εργασία Build. Ξαναχτίζεται
    # μόνο στο κανονικό παιχνίδι (tests/test_meteor.py): ο γράφος αυτής της
    # δοκιμής έχει μόνο θόλους, και καμία δομή δεν φτάνεται.
    sites = sum(1 for k in range(EC.MAX_STRUCT)
                if sim.e.struct[k * 8 + EC.ST_STATE] == EC.DS_BUILDING)
    jobs = sum(1 for k in range(EC.MAX_JOB)
               if sim.e.job[k * EC.JOB_REC + EC.J_KIND] == EC.J_BUILD)
    if sim.e.meteor or not broke or not sites or not jobs:
        print(f"ΑΠΟΤΥΧΙΑ βροχή: έμειναν {sim.e.meteor} κρούσεις, {broke} μηχανές "
              f"σταμάτησαν, {sites} δομές εργοτάξια, {jobs} εργασίες Build")
        return 1
    print(f"OK μετεωρίτες: οκτώ κρούσεις, {broke} μηχανές σταμάτησαν ({fixed} "
          f"επισκευάστηκαν), {sites} δομή ξανά εργοτάξιο με εργασία Build — "
          f"{METEOR_TICKS} frames, ίδια bytes στον Z80 και στην αναφορά")

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
    return 0


METEOR_TICKS = 1600             # 100 περιστροφές: οκτώ κρούσεις, δρόμος, χτίσιμο


if __name__ == "__main__":
    sys.exit(main())
