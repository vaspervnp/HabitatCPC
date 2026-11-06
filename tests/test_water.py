#!/usr/bin/env python3
"""Το ισοζύγιο του ρεύματος και του νερού όπως στο Planetbase (βήμα 189,
DESIGN §6.5, §9.2, src/water.asm).

Η πρόζα — οι αποφάσεις του παίκτη:

  ΤΑΒΑΝΙ   το νερό χωρά EC_CAP (600) και ό,τι δίνουν οι θόλοι Storage (100,
           300, 600 κατά μέγεθος), χωριστά από τα αγαθά: το ec_wcap, που το
           γράφει το st_check (stc_wcap). Οι αντλίες γεμίζουν ως εκεί
           (ef_water), και ό,τι άλλο μπαίνει στην αποθήκη μένει στο EC_CAP.
  ΣΕΙΡΑ    όταν λείπει, σταματούν πρώτα οι κήποι και το VITROMEAT (κάτω από
           1,5 x ζωντανούς, R1), μετά το ποτό στο κυλικείο — των αποίκων και το
           γεύμα των επισκεπτών — (κάτω από τους ζωντανούς, R2), και τελευταίες
           οι μηχανές OXYGEN, ως την τελευταία μονάδα. Μία φορά ανά κύκλο ροής
           (ew_cycle), με τους ζωντανούς του προηγούμενου.
  ΠΡΟΣΗΜΑ  η σειρά 0: «PWR+█████ H2O-███░░». Το ρεύμα «-» όταν η ζήτηση περνά
           την παραγωγή· το νερό «-» όταν έπεσε από τον προηγούμενο κύκλο ή
           είναι κάτω από το R1. Τα πέντε κελιά είναι ό,τι είναι αποθηκευμένο
           (τα δείχνει το tests/test_hud.py, byte προς byte).
  ΑΡΧΗ     σε κάθε νέο παιχνίδι, στην αποικία δοκιμών και σε κάθε φόρτωμα
           (wheel_reset -> ew_reset): ταβάνι EC_CAP, όλοι πίνουν, ως τον
           πρώτο κύκλο ροής — όπως το ec_full από το βήμα 122.

Ελέγχει:
  1. ΤΑΒΑΝΙ, ΣΕΙΡΑ, ΠΟΤΟ: ο Z80 του tests/simtest.asm απέναντι στην αναφορά
     (tools/econ.py, tools/entity.py), όλα τα bytes ίδια — ο κύκλος ροής με
     αντλίες στα όρια του ταβανιού, ο κύκλος ροής και ένα σάρωμα της
     παραγωγής στα R1 και R2, και τέσσερις περιστροφές με διψασμένους. Και η
     αναφορά λέει την πρόζα: πάνω από το 600 με Storage, κανένα φυτό και κανένα
     κρέας κάτω από το R1, κανείς δεν πίνει κάτω από το R2.
  2. ΣΤΟ ΠΑΙΧΝΙΔΙ (build/colony.sna): το ew_cycle σε έναν πίνακα από
     περιπτώσεις — τα SMC και τα δύο πρόσημα — και η σειρά 0 στην οθόνη· το
     ew_reset από το wheel_reset· και ο κύκλος ροής που το καλεί.
  3. ΚΟΣΤΟΣ: ο κύκλος ροής με και χωρίς το ew_cycle.

Αρνητικά, με τον κώδικα πειραγμένο στη μνήμη: οι αντλίες με το ec_make του
EC_CAP· ο κύκλος ροής χωρίς το ew_cycle (στον simtest και στο παιχνίδι)· το
st_check χωρίς το stc_wcap· το wheel_reset χωρίς το ew_reset· το R2 με
«jr nc» στη θέση του «sbc a,a» (κανείς δεν σταματά να πίνει).
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import test_sim as TS                                    # noqa: E402
import test_bots as TB                                   # noqa: E402
import codeat                                            # noqa: E402
import hudread                                           # noqa: E402
import econ as EC                                        # noqa: E402
import entity as E                                       # noqa: E402
import graph as G                                        # noqa: E402

FAIL = []
S_WATER = EC.S_WATER
GROWN = (EC.S_STARCH, EC.S_VEG, EC.S_MEDPLANT, EC.S_MEAT)
SWEEP = 4 * EC.ECON_DIV                 # ένα σάρωμα της παραγωγής: οι 64 θόλοι
DRINK_N = 512                           # πριν από τον δεύτερο κύκλο ροής (1.024)


def check(ok, msg):
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ ") + msg)
    if not ok:
        FAIL.append(msg)


def w(v):
    return [v & 255, v >> 8]


# --------------------------------------------------------------------------
# 1. Ο simtest απέναντι στην αναφορά
# --------------------------------------------------------------------------
def colony():
    g = TS.colony_graph()
    dist, nexthop = G.all_pairs(g)
    sim0 = E.Sim(g, nexthop, dist)
    EC.populate(sim0.e)
    E.populate(sim0)
    EC.rooms_rebuild(sim0.e, sim0.pc)
    sim0.e.sollen, sim0.e.daylen = 320, 192
    return g, nexthop, sim0


def keys(z):
    return (z.a.to_bytes(), bytes(z.e.dome), bytes(z.e.struct),
            TS.econ_bytes(z.e), bytes(z.e.job), bytes(z.occ[:128]))


def z80_chain(sym, g, nexthop, st, steps, patch=()):
    """Ο Z80 από την κατάσταση st: για κάθε (θέση, n) n frames με τον τροχό
    καρφωμένο εκεί (None: ελεύθερος), χωρίς να ξαναφορτωθεί."""
    m = TS.z80_load(sym, g, TS.fresh(g, nexthop, st), EC.MAX_DOME + EC.MAX_STRUCT, patch)
    for pin, n in steps:
        m.poke(sym["PIN_SLOT"], 255 if pin is None else pin)
        m.poke(sym["TICK_COUNT"], n & 0xFF)
        m.poke(sym["TICK_COUNT"] + 1, n >> 8)
        TS.enter(m, sym, "RUN_TICKS")
    got = TS.z80_read(m, sym, 0)
    return (got[0], got[3], got[4], got[5], got[6], got[1])


def ref_chain(g, nexthop, st, steps):
    sim = TS.fresh(g, nexthop, st)
    for pin, n in steps:
        for _ in range(n):
            if pin == 12:
                TS.slot12(sim)
            elif pin == 11:
                EC.production_slice(sim.e, plant_class=sim.pc)
            else:
                sim.tick()
    return sim


def find_call(sym, start, target, span=600, op=0xCD):
    """Η διεύθυνση του «call target» (CD, ή op: C4 το call nz) μετά το start,
    στον simtest."""
    code = TS.run_peek(sym, start, span)
    pat = [op] + w(target)
    for k in range(span - 2):
        if code[k:k + 3] == pat:
            return start + k
    return None


def pumps_on(e):
    """Ρεύμα για τις αντλίες σε αυτόν τον κύκλο: γεμάτη μπαταρία (το ef_try
    δανείζεται ως τη ρεζέρβα)."""
    e.power_store = 4000


def pumps_off(e):
    for i in range(EC.MAX_STRUCT):
        if e.struct[i * EC.STRUCT_REC + EC.ST_KIND] == EC.K_EXTRACTOR:
            e.struct[i * EC.STRUCT_REC + EC.ST_STATE] = EC.DS_BUILDING


def store_size(e, size):
    """Ο θόλος Storage της αποικίας: μέγεθος 0-2, ή None για κανέναν."""
    d = e.room_list[EC.R_STORAGE * EC.ROOM_MAX]
    if size is None:
        e.dome[d * EC.DOME_REC + EC.D_STATE] = EC.DS_BUILDING
    else:
        e.dome[d * EC.DOME_REC + EC.D_SIZE] = size
    EC.rooms_rebuild(e, None)


def cap_cases(sym, g, nexthop, sim0):
    """ΤΑΒΑΝΙ: ένας κύκλος ροής με τις αντλίες, στα όρια του ec_wcap."""
    out = {}
    # (όνομα, μέγεθος του Storage, νερό πριν, ec_wcap): οι δύο αντλίες L της
    # αποικίας βγάζουν 10 τον κύκλο, και οι τρεις πρώτες φτάνουν στο ταβάνι.
    cases = (("Storage M, 895 -> 900", 1, 895, 900),
             ("Storage L, 1.195 -> 1.200", 2, 1195, 1200),
             ("χωρίς Storage, 595 -> 600", None, 595, 600),
             ("Storage S, από το μηδέν", 0, 0, 700))
    flow = [(12, 1)]
    for name, size, water, cap in cases:
        st = TS.fresh(g, nexthop, sim0)
        store_size(st.e, size)
        pumps_on(st.e)
        st.e.stock[S_WATER] = water
        st.e.flow_div = 1
        ref = ref_chain(g, nexthop, st, flow)
        got = ref.e.stock[S_WATER]
        rose = got > water
        ok = ref.e.wcap == cap and rose and (got == cap) == (water > 0)
        if not ok:
            check(False, f"ΤΑΒΑΝΙ «{name}»: η αναφορά λέει ec_wcap {ref.e.wcap} (θέλει {cap}), "
                         f"νερό {water} -> {got}")
            continue
        same = z80_chain(sym, g, nexthop, st, flow) == keys(ref)
        check(same, f"ΤΑΒΑΝΙ «{name}»: ec_wcap {cap}, νερό {water} -> {got}, ίδια bytes "
                    f"στον Z80 και στην αναφορά")
        out[name] = st
    # ΑΡΝΗΤΙΚΟ: οι αντλίες με το ec_make, όπως ως το 188 — ταβάνι 600.
    at = find_call(sym, sym["ECON_FLOW"], sym["EF_WATER"], op=0xC4)     # call nz
    st = out.get("Storage M, 895 -> 900")
    if at is None or st is None:
        check(False, f"ΤΑΒΑΝΙ: ΑΡΝΗΤΙΚΟ — κανένα call ef_water στο econ_flow ({at})")
    else:
        bad = z80_chain(sym, g, nexthop, st, flow, [(at + 1, sym["EC_MAKE"] & 255),
                                                    (at + 2, sym["EC_MAKE"] >> 8)])
        check(bad != keys(ref_chain(g, nexthop, st, flow)),
              "ΤΑΒΑΝΙ: ΑΡΝΗΤΙΚΟ — οι αντλίες με το ec_make του EC_CAP: ο Z80 διαφέρει")
    # ΑΡΝΗΤΙΚΟ: το st_check χωρίς το stc_wcap — το ec_wcap μένει όπως ήρθε.
    at = find_call(sym, sym["ST_CHECK"], sym["STC_WCAP"])
    if at is None or st is None:
        check(False, f"ΤΑΒΑΝΙ: ΑΡΝΗΤΙΚΟ — κανένα call stc_wcap στο st_check ({at})")
    else:
        bad = z80_chain(sym, g, nexthop, st, flow, [(at + k, 0) for k in range(3)])
        check(bad != keys(ref_chain(g, nexthop, st, flow)),
              "ΤΑΒΑΝΙ: ΑΡΝΗΤΙΚΟ — το st_check χωρίς το stc_wcap: ο Z80 διαφέρει")


def order_cases(sym, g, nexthop, sim0):
    """ΣΕΙΡΑ: ο κύκλος ροής (χωρίς αντλίες, το νερό μένει) και ένα σάρωμα της
    παραγωγής, στα όρια R1 και R2 των ζωντανών."""
    alive = sim0.e.alive
    r1, r2 = alive + (alive >> 1), alive
    assert r1 < 255, "η αποικία της δοκιμής έχει πάνω από 169 ζωντανούς"
    steps = [(12, 1), (11, SWEEP)]
    seen = {}
    for name, water, plants, drink in (("R1", r1, True, True),
                                       ("R1 - 1", r1 - 1, False, True),
                                       ("R2", r2, False, True),
                                       ("R2 - 1", r2 - 1, False, False),
                                       ("μηδέν", 0, False, False),
                                       ("300, πάνω από ένα byte", 300, True, True)):
        st = TS.fresh(g, nexthop, sim0)
        pumps_off(st.e)
        pumps_on(st.e)                          # η μπαταρία: οι κήποι θέλουν όλο το ρεύμα
        st.e.stock[S_WATER] = water
        st.e.flow_div = 1
        before = list(st.e.stock)
        ref = ref_chain(g, nexthop, st, steps)
        grew = [k for k in GROWN if ref.e.stock[k] > before[k]]
        rule = (ref.e.plant_water == EC.PLANT_WATER, ref.e.vw_q == EC.VW_Q, ref.e.drink)
        if rule != (plants, plants, drink) or bool(grew) != plants:
            check(False, f"ΣΕΙΡΑ νερό {water} ({name}, {alive} ζωντανοί): η αναφορά λέει "
                         f"κήπος/VITROMEAT/ποτό {rule}, ανέβηκαν {grew}")
            continue
        same = z80_chain(sym, g, nexthop, st, steps) == keys(ref)
        check(same, f"ΣΕΙΡΑ νερό {water} ({name}): κήποι και VITROMEAT "
                    f"{'τρέχουν' if plants else 'σταματούν'}, ποτό {'ναι' if drink else 'όχι'}, "
                    f"ανέβηκαν {len(grew)} από τα 4 — ίδια bytes μετά τον κύκλο ροής και "
                    f"{SWEEP} frames παραγωγής")
        seen[name] = st
    # ΑΡΝΗΤΙΚΟ: ο κύκλος ροής χωρίς το ew_cycle — ο κώδικας μένει όπως ήρθε
    # (όλα πίνουν), και στο R1 - 1 οι κήποι τρέχουν.
    at = find_call(sym, sym["ECON_FLOW"], sym["EW_CYCLE"])
    st = seen.get("R1 - 1")
    if at is None or st is None:
        check(False, f"ΣΕΙΡΑ: ΑΡΝΗΤΙΚΟ — κανένα call ew_cycle στο econ_flow ({at})")
        return
    bad = z80_chain(sym, g, nexthop, st, steps, [(at + k, 0) for k in range(3)])
    check(bad != keys(ref_chain(g, nexthop, st, steps)),
          "ΣΕΙΡΑ: ΑΡΝΗΤΙΚΟ — ο κύκλος ροής χωρίς το ew_cycle: ο Z80 διαφέρει")


def drink_cases(sym, g, nexthop, sim0):
    """ΠΟΤΟ: οι μισοί ζωντανοί διψούν (νερό 50, κάτω από το NEED_LOW), και
    DRINK_N frames ελεύθερα, με τον κύκλο ροής στην πρώτη περιστροφή (flow_div
    1) και όχι δεύτερο. Το R2 είναι το EC_ALIVE, που δεν μετρά τα ρομπότ. Η
    θέση 11 τρέχει πριν από τη 12 και οι μηχανές OXYGEN πίνουν: πάνω από το R2
    με περιθώριο (και κάτω από το R1), και ακριβώς ένα κάτω."""
    alive = [i for i in range(E.MAXAGENT) if sim0.a.flags[i] & E.F_ALIVE]
    thirsty = alive[::2]
    steps = [(None, DRINK_N)]
    drank = {}
    r2 = sim0.e.alive
    for name, water in (("R2 + 30", r2 + 30), ("R2 - 1", r2 - 1)):
        st = TS.fresh(g, nexthop, sim0)
        pumps_off(st.e)
        pumps_on(st.e)
        st.e.stock[S_WATER] = water
        st.e.flow_div = 1
        for i in thirsty:
            st.a.water[i] = 50
        ref = ref_chain(g, nexthop, st, steps)
        drank[name] = sum(1 for i in thirsty if ref.a.water[i] > 50)
        same = z80_chain(sym, g, nexthop, st, steps) == keys(ref)
        check(same, f"ΠΟΤΟ νερό {water} ({name}): {drank[name]} από {len(thirsty)} διψασμένους "
                    f"ήπιαν σε {DRINK_N} frames — ίδια bytes στον Z80 και στην αναφορά")
        drank[name + " st"] = st
    check(drank["R2 + 30"] > 0 and drank["R2 - 1"] == 0,
          f"ΠΟΤΟ: πάνω από το R2 πίνουν ({drank['R2 + 30']}), στο R2 - 1 κανείς "
          f"({drank['R2 - 1']})")


# --------------------------------------------------------------------------
# 2. Στο παιχνίδι
# --------------------------------------------------------------------------
class Game(TB.Game):
    def ew(self, alive, water, last, prod=50, use=40):
        e = self.EC["EC_STOCK"]
        self.m.poke(self.EC["EC_ALIVE"], alive)
        self.s16(e + 2 * S_WATER, water)
        self.s16(self.sym["EW_LAST"], last)
        self.s16(e + 32, prod)                  # EC_PPROD, src/const.asm
        self.s16(e + 34, use)                   # EC_PUSE
        self.call("EW_CYCLE")

    def rules(self):
        s = self.sym
        return (self.m.peek(self.L["G_recipes"] + 10 * EC.MT_VITRO + 1),
                self.m.peek(s["ERP_GO"] + 1), codeat.read(self.m, s["NDS_WLD"], 1)[0],
                self.m.peek(s["VIE_W"]), chr(self.m.peek(s["HU_PWR"] + 3)),
                chr(self.m.peek(s["HU_H2O"] + 3)))


def want_rules(alive, water, last, prod, use):
    e = EC.Econ()
    e.alive, e.stock[S_WATER] = alive, water
    EC.water_rules(e)
    low = min(water, 255) < alive + (alive >> 1)
    return (e.vw_q, e.plant_water, 0x3E if e.drink else 0xC9, 0x28 if e.drink else 0x18,
            "-" if prod < use else "+", "-" if water < last or low else "+")


EW_CASES = (
    # (ζωντανοί, νερό, προηγούμενο, παραγωγή, ζήτηση)
    (6, 9, 9, 50, 40), (6, 8, 8, 50, 40), (6, 6, 6, 40, 40), (6, 5, 5, 39, 40),
    (6, 0, 0, 0, 0), (6, 300, 290, 50, 60), (6, 300, 301, 60, 50),
    (160, 239, 239, 50, 40), (160, 240, 240, 50, 40), (160, 159, 159, 50, 40),
    (160, 256, 256, 50, 40), (0, 0, 0, 50, 40), (80, 1200, 1100, 9000, 9001),
)


def game_checks(sym):
    G0 = Game(sym)
    bad = []
    for c in EW_CASES:
        G0.ew(*c)
        got, want = G0.rules(), want_rules(*c)
        if got != want:
            bad.append((c, got, want))
    check(not bad, f"ew_cycle: {len(EW_CASES)} περιπτώσεις — το νερό του VITROMEAT και του "
                   f"κήπου, το ποτό των αποίκων και των επισκεπτών, τα δύο πρόσημα — όπως η "
                   f"αναφορά{'' if not bad else ': ' + str(bad[:3])}")

    # ΑΡΝΗΤΙΚΟ: «xor a» στη θέση του «sbc a,a» μετά το «cp d» — το R2 δεν
    # σταματά κανέναν. Το (6, 5) πρέπει να το πιάσει.
    at = codeat.find(G0.m, sym["EWC_Q"], [0xBA, 0x9F])         # cp d / sbc a,a
    if at:
        G1 = Game(sym)
        codeat.poke(G1.m, at + 1, 0xAF)
        G1.ew(6, 5, 5, 39, 40)
        g1 = G1.rules()
        check(g1[2:4] != want_rules(6, 5, 5, 39, 40)[2:4],
              f"ew_cycle: ΑΡΝΗΤΙΚΟ — με «xor a» αντί για «sbc a,a» το R2 δεν σταματά το "
              f"ποτό (#{g1[2]:02X}, #{g1[3]:02X})")
    else:
        check(False, "ew_cycle: ΑΡΝΗΤΙΚΟ — δεν βρέθηκε το «cp d / sbc a,a» στο ewc_q")

    # Η ΣΕΙΡΑ 0 ΣΤΗΝ ΟΘΟΝΗ, από τα πρόσημα του ew_cycle: χωρίς probe, που
    # αφήνει τον Z80 στο «jr $» του. Στην παύση το HUD δεν ξαναγράφεται
    # (src/main.asm): ταχύτητα 1 για 40 frames, με το ec_fdiv στο 64 ώστε
    # κανένας κύκλος ροής να μην τα ξαναγράψει, και πάλι παύση.
    Gs = Game(sym)
    before = Gs.hud(0)
    Gs.m.poke(sym["HU_PWR"] + 3, ord("-"))
    Gs.m.poke(sym["HU_H2O"] + 3, ord("-"))
    Gs.m.poke(sym["EC_FDIV"], 64)
    Gs.m.poke(sym["UI_SPD"], 1)
    Gs.m.run_frames(40)
    Gs.m.poke(sym["UI_SPD"], 0)
    row = Gs.hud(0)
    check("PWR+" in before and "PWR-" in row and "H2O-" in row,
          f"η σειρά 0 στην οθόνη: «{before.rstrip()}» -> «{row.rstrip()}»")

    # ΑΡΧΗ: το wheel_reset ξαναβάζει όλα (ew_reset).
    G2 = Game(sym)
    G2.ew(6, 5, 9, 10, 20)                       # όλα σταματημένα, «-» και τα δύο
    G2.s16(sym["EC_WCAP"], 1234)
    G2.call("WHEEL_RESET")
    r = G2.rules()
    wc = G2.w16(sym["EC_WCAP"])
    last = G2.w16(sym["EW_LAST"])
    check(r[:4] == (EC.VW_Q, EC.PLANT_WATER, 0x3E, 0x28) and r[5] == "+" and wc == EC.Econ().cap
          and last == 5,
          f"wheel_reset: VITROMEAT {r[0]}, κήπος {r[1]}, ποτό #{r[2]:02X}/#{r[3]:02X}, H2O{r[5]}, "
          f"ec_wcap {wc}, ew_last {last} — όλα πίνουν ως τον πρώτο κύκλο ροής")
    # ΑΡΝΗΤΙΚΟ: το wheel_reset με το ec_setfull του 188.
    at = codeat.find(G2.m, sym["WHEEL_RESET"], [0xCD] + w(sym["EW_RESET"]), 40)
    G3 = Game(sym)
    if at is None:
        check(False, "wheel_reset: ΑΡΝΗΤΙΚΟ — κανένα call ew_reset")
    else:
        for k, v in enumerate([0xCD] + w(sym["EC_SETFULL"])):
            codeat.poke(G3.m, at + k, v)
        G3.ew(6, 5, 9, 10, 20)
        G3.call("WHEEL_RESET")
        check(G3.rules()[:4] != (EC.VW_Q, EC.PLANT_WATER, 0x3E, 0x28),
              "wheel_reset: ΑΡΝΗΤΙΚΟ — με το ec_setfull μόνο, ο κώδικας του νερού μένει σταματημένος")

    # Ο ΚΥΚΛΟΣ ΡΟΗΣ ΤΟΥ ΠΑΙΧΝΙΔΙΟΥ το καλεί: νερό 5 με 160 ζωντανούς (R2 160:
    # ό,τι κι αν βγάλουν οι αντλίες της αποικίας), κανείς δεν πίνει.
    def flow(Gx):
        Gx.s16(Gx.EC["EC_STOCK"] + 2 * S_WATER, 5)
        Gx.call("WHEEL_RESET")
        Gx.m.poke(Gx.EC["EC_ALIVE"], 160)
        Gx.m.poke(sym["EC_FDIV"], 1)
        us = Gx.call("ECON_FLOW", timed=True)
        return Gx.rules(), us
    G4 = Game(sym)
    r4, us4 = flow(G4)
    at = codeat.find(G4.m, sym["EF_WDONE"], [0xCD] + w(sym["EW_CYCLE"]), 8)
    G5 = Game(sym)
    if at is None:
        check(False, "κύκλος ροής: κανένα call ew_cycle στο ef_wdone")
        return
    for k in range(3):
        codeat.poke(G5.m, at + k, 0)
    r5, us5 = flow(G5)
    check(r4[2] == 0xC9 and r5[2] == 0x3E,
          f"κύκλος ροής του παιχνιδιού: με νερό 5 και 160 ζωντανούς το ποτό σταματά "
          f"(#{r4[2]:02X}); ΑΡΝΗΤΙΚΟ — χωρίς το call ew_cycle όχι (#{r5[2]:02X})")
    print(f"\nκόστος: ο κύκλος ροής {us4} us, χωρίς το ew_cycle {us5} us "
          f"(+{us4 - us5} us, μία φορά ανά 64 περιστροφές)")


def main():
    sym = TG.build()[0]
    game_checks(sym)
    ssym = TS.build()
    g, nexthop, sim0 = colony()
    cap_cases(ssym, g, nexthop, sim0)
    order_cases(ssym, g, nexthop, sim0)
    drink_cases(ssym, g, nexthop, sim0)
    print(f"\n{len(FAIL)} ΑΠΟΤΥΧΙΕΣ" if FAIL else "\nΟΛΑ OK")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
