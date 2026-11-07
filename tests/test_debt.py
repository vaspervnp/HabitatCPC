#!/usr/bin/env python3
"""Το χρέος των εργοταξίων (βήμα 198, DESIGN §6.9): τοποθέτηση και FIT χωρίς τα
υλικά, και κάθε φορτίο πληρώνεται τη στιγμή που το σηκώνει ο μεταφορέας.

Ο παίκτης: «Να μπορώ να τοποθετώ για χτίσιμο ακόμα και αν δεν έχω τα resources
που χρειάζομαι. Όπως παράγονται, πηγαίνουν.» Πληρωμή στο σήκωμα· και οι μηχανές
(τα φυτά όχι)· ένα εργοτάξιο που γκρεμίζεται δίνει ό,τι κουβαλήθηκε.

  ΣΗΚΩΜΑ    στο main.sna, δίπλα στο σκάφος, ΧΩΡΙΣ μέταλλο: το ηλιακό μπαίνει
            (ST_OWED #20), τα 15 στο χρέος (EC_DEBT), το απόθεμα 0. Για 2.500
            frames κανείς δεν φορτώνει, το εργοτάξιο χρωστά #20, και το EC_WAIT
            λέει ότι το μέταλλο περιμένει. Με 12 μέταλλο: ένα φορτίο των 10
            (απόθεμα 2, χρέος 5, #10)· το δεύτερο θέλει 5 και δεν φτάνουν —
            2.500 frames ακόμη χωρίς αλλαγή. Με 7: το δεύτερο, των 5, και το
            ηλιακό χτίζεται με απόθεμα 2 και χρέος 0.
  ΣΥΝΟΛΟ    δύο ηλιακά με 100 μέταλλο: 30 στο χρέος, τέσσερα φορτία, και
            στο τέλος ακριβώς 70 — 10, 10, 10 και ένα τζάμπα: το χρέος είναι
            ένα για όλη την αποικία, όσο κι αν στρογγυλεύουν τα φορτία.
  ΓΚΡΕΜΙΣΜΑ στην αποικία δοκιμών, χωρίς μέταλλο: ένα ηλιακό μπαίνει και
            γκρεμίζεται πριν φτάσει τίποτα — το χρέος γυρίζει στο 0, και τα
            αποθέματα δεν παίρνουν τίποτα (ως το 197 έπαιρναν και τα 15).
  ΜΗΧΑΝΗ    σε εργοστάσιο έτοιμο, χωρίς αποθέματα: σίδερο στο FIT (8/2 στο
            χρέος, τίποτα από τα αποθέματα)· ΑΔΕΙΟ στη θέση του πριν
            κουβαληθεί: το χρέος πίσω στο 0 και τα αποθέματα 0 (ως το 197 τα
            μισά πίσω, που δεν είχαν πληρωθεί). Ξανά σίδερο, και ο θόλος
            γκρεμίζεται: τα μισά του θόλου και των διαδρόμων του, και η μηχανή
            μόνο από το χρέος.

Αρνητικά, με τον κώδικα πειραγμένο στη μνήμη: το sp_go χωρίς πληρωμή· το
sp_wake ένα ret· το sp_wake χωρίς το EC_WAIT· φορτίο πάντα 10 (sp_can χωρίς το
χρέος)· το db_cut ένα ret (χωρίς χρέος πρώτα)· η μηχανή που βγαίνει πάντα τα
μισά (mc_out).
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import test_supply as TS                                 # noqa: E402
import test_demolish as TD                               # noqa: E402
import test_fit as TF                                    # noqa: E402
import test_reveal as R                                  # noqa: E402
import balance as B                                      # noqa: E402
import codeat as CA                                      # noqa: E402

SOLAR = 65
DS_BUILDING, DS_ACTIVE = 1, 2
I_SOLAR = 4
WAIT = 2500                                              # frames: πάνω από έναν κύκλο ροής (1.024)
FAIL = []


def say(ok, msg):
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ: ") + msg)
    if not ok:
        FAIL.append(msg)


def set_metal(w, v):
    w.m.poke(w.g + 6, v & 255)
    w.m.poke(w.g + 7, v >> 8)


def pickup(sym, g, patch=(), quiet=False):
    """ΣΗΚΩΜΑ. None, ή η πρώτη διαφορά από την πρόζα."""
    w = TS.W(sym, g, patch)
    m = w.m
    set_metal(w, 0)
    B.build(m, sym, I_SOLAR, g + 6, at=TS.SOLAR_AT, fit=False)
    m.run_frames(2)
    rec = w.struct(1)
    if rec[4] != DS_BUILDING or rec[7] != 0x20 or w.w16(6) != 0 or CA.debt(m) != (15, 0):
        return (f"ΣΗΚΩΜΑ: στο FIRE εγγραφή {rec}, μέταλλο {w.w16(6)}, χρέος {CA.debt(m)} — "
                f"θέλει εργοτάξιο με #20, 0 και (15, 0)")
    waited = loaded = 0
    for _ in range(WAIT // 5):
        m.run_frames(5)
        waited += CA.wait(m) & 1
        loaded += any(w.agent(i)["spare"] for i in range(4))
    rec = w.struct(1)
    if rec[7] != 0x20 or w.w16(6) != 0 or CA.debt(m) != (15, 0) or loaded or not waited:
        return (f"ΣΗΚΩΜΑ: χωρίς μέταλλο {WAIT} frames: ST_OWED #{rec[7]:02X}, μέταλλο {w.w16(6)}, "
                f"χρέος {CA.debt(m)}, φορτωμένοι σε {loaded} δείγματα, EC_WAIT σε {waited} — "
                f"θέλει #20, 0, (15, 0), κανείς, και το EC_WAIT")
    set_metal(w, 12)
    t1 = w.wait(lambda: w.struct(1)[7] == 0x10, 4000, 5)
    metal1, debt1 = w.w16(6), CA.debt(m)
    m.run_frames(WAIT)
    rec = w.struct(1)
    if t1 is None or (metal1, debt1) != (2, (5, 0)) or rec[7] != 0x10 \
            or rec[4] != DS_BUILDING or (w.w16(6), CA.debt(m)) != (2, (5, 0)):
        return (f"ΣΗΚΩΜΑ: με 12 μέταλλο το πρώτο φορτίο σε {t1} frames, μέταλλο {metal1}, χρέος "
                f"{debt1}· {WAIT} frames μετά #{rec[7]:02X}, μέταλλο {w.w16(6)}, χρέος "
                f"{CA.debt(m)} — θέλει 2, (5, 0), #10 και να μείνει εκεί")
    set_metal(w, 7)
    t2 = w.wait(lambda: w.struct(1)[4] == DS_ACTIVE, 6000, 10)
    if t2 is None or w.w16(6) != 2 or CA.debt(m) != (0, 0):
        return (f"ΣΗΚΩΜΑ: με 7 μέταλλο το ηλιακό σε {t2} frames, μέταλλο {w.w16(6)}, χρέος "
                f"{CA.debt(m)} — θέλει χτισμένο, 2 και (0, 0)")
    if not quiet:
        print(f"    ΣΗΚΩΜΑ: χωρίς μέταλλο τίποτα για {WAIT} frames (EC_WAIT σε {waited} δείγματα)· "
              f"με 12 ένα φορτίο σε {t1} frames (2 μένουν, χρέος 5), και το δεύτερο περιμένει· "
              f"με 7 χτίστηκε σε {t2} frames, μέταλλο 2, χρέος 0")
    return None


def total(sym, g, patch=(), quiet=False):
    """ΣΥΝΟΛΟ. None, ή η πρώτη διαφορά."""
    w = TS.W(sym, g, patch)
    m = w.m
    set_metal(w, 100)
    B.build(m, sym, I_SOLAR, g + 6, at=TS.SOLAR_AT, fit=False)
    at2 = B.live_spot(m, sym, I_SOLAR, (TS.SOLAR_AT[0] + 8, TS.SOLAR_AT[1] + 8))
    B.build(m, sym, I_SOLAR, g + 6, at=at2, fit=False)
    m.run_frames(2)
    sites = [k for k in range(1, 8) if w.struct(k)[4] == DS_BUILDING]
    if len(sites) != 2 or CA.debt(m)[0] + (100 - w.w16(6)) != 30:
        return (f"ΣΥΝΟΛΟ: εργοτάξια {sites}, μέταλλο {w.w16(6)}, χρέος {CA.debt(m)} — "
                f"θέλει δύο, και 30 στο χρέος (μείον ό,τι σηκώθηκε ήδη)")
    seen = set()
    t = w.wait(lambda: all(w.struct(k)[4] == DS_ACTIVE for k in sites), 20000, 10,
               lambda: seen.add(w.w16(6)))
    if t is None or w.w16(6) != 70 or CA.debt(m) != (0, 0) or not seen <= {100, 90, 80, 70}:
        return (f"ΣΥΝΟΛΟ: σε {t} frames, μέταλλο {w.w16(6)} (είδε {sorted(seen)}), χρέος "
                f"{CA.debt(m)} — θέλει και τα δύο χτισμένα, 70, (0, 0), τίποτα εκτός από "
                f"100, 90, 80, 70")
    if not quiet:
        print(f"    ΣΥΝΟΛΟ: δύο ηλιακά, μέταλλο {sorted(seen, reverse=True)}, χτισμένα σε {t} "
              f"frames: ακριβώς 30, και το τέταρτο φορτίο τζάμπα")
    return None


def colony(sym, g, patch):
    G, F = TD.game(sym, g, patch)
    G.run(500_000)
    G.settle()
    return G, F


def razed(sym, g, patch=(), quiet=False):
    """ΓΚΡΕΜΙΣΜΑ. None, ή η πρώτη διαφορά."""
    G, F = colony(sym, g, patch)
    F.set_stocks(0, 0)
    at = B.live_spot(G.m, sym, I_SOLAR, (0, 24))
    G.camera((at[0] >> 1) - 10, (at[1] >> 1) - 5)
    d0 = CA.debt(G.m)
    if not B.build(G.m, sym, I_SOLAR, G.g + 6, at=at, fit=False):
        return f"ΓΚΡΕΜΙΣΜΑ: το ηλιακό δεν μπήκε στο {at}"
    n = G.m.peek(sym["BD_NODE"])
    d1 = CA.debt(G.m)
    x, y = TD.centre(G, n)
    _, _, s0, s1, _ = TD.demolish(G, F, (x, y))
    if d0 != (0, 0) or d1 != (15, 0) or TD.struct(G, n)[4] or s1 != s0 or s1 != (0, 0) \
            or G.debt1 != (0, 0):
        return (f"ΓΚΡΕΜΙΣΜΑ: χρέος {d0} -> {d1} στο FIRE, {G.debt0} -> {G.debt1} στο γκρέμισμα, "
                f"αποθέματα {s0} -> {s1}, εγγραφή {TD.struct(G, n)[:5]} — θέλει (15, 0), μετά "
                f"(0, 0), και τα αποθέματα 0")
    if not quiet:
        print(f"    ΓΚΡΕΜΙΣΜΑ: ηλιακό {n} χωρίς μέταλλο, χρέος 15 -> 0, αποθέματα {s1}")
    return None


def machine(sym, g, patch=(), quiet=False):
    """ΜΗΧΑΝΗ. None, ή η πρώτη διαφορά."""
    G, F = colony(sym, g, patch)
    tx, ty = B.clear_spots(8, 1, dome=True)[0]
    G.camera(tx - 6, ty - 1)
    at = (2 * tx + 8, 2 * ty + 8)
    B.build(G.m, sym, TF.I_DOME_M, G.g + 6, at=at, room=TF.RM_FACTORY, fit=False)
    n = G.m.peek(sym["BD_NODE"])
    if not R.finish(G, n):
        return f"ΜΗΧΑΝΗ: το εργοστάσιο {n} δεν τελείωσε"
    G.settle()
    if CA.debt(G.m) != (0, 0):
        return f"ΜΗΧΑΝΗ: το εργοστάσιο τελείωσε με χρέος {CA.debt(G.m)}"
    F.set_stocks(0, 0)
    if not F.enter(at):
        return "ΜΗΧΑΝΗ: το FIT δεν άνοιξε"
    F.put(0, 1)                                          # σίδερο, 8/2
    a = (F.rec(n)[8], F.rec(n)[16], F.stocks(), CA.debt(G.m))
    F.put(0, 0)                                          # ΑΔΕΙΟ
    b = (F.rec(n)[8], F.stocks(), CA.debt(G.m))
    F.put(0, 1)
    F.look()
    if a != (1, TF.MACH_OWED if hasattr(TF, "MACH_OWED") else 7, (0, 0), (8, 2)) \
            or b != (TF.NO_MACH, (0, 0), (0, 0)):
        return (f"ΜΗΧΑΝΗ: στο FIT (υποδοχή, υγεία, αποθέματα, χρέος) {a}, μετά το ΑΔΕΙΟ "
                f"{b} — θέλει (1, 7, (0, 0), (8, 2)) και (255, (0, 0), (0, 0))")
    tiles = sum(c[3] for c in TD.corridors(G) if c[4] and n in c[:2])
    half = ((TD.DOME[1][0] + TD.CORR[0] * tiles) // 2, (TD.DOME[1][1] + TD.CORR[1] * tiles) // 2)
    _, _, s0, s1, _ = TD.demolish(G, F, at)
    got = (s1[0] - s0[0], s1[1] - s0[1])
    if TD.dome(G, n)[4] or got != half or G.debt0 != (8, 2) or G.debt1 != (0, 0):
        return (f"ΜΗΧΑΝΗ: γκρεμισμένο εργοστάσιο ({tiles} πλακίδια) με το σίδερο ακόμη στο "
                f"χρέος: πίσω {got}, χρέος {G.debt0} -> {G.debt1} — θέλει {half} (τα μισά του "
                f"θόλου και των διαδρόμων) και (8, 2) -> (0, 0)")
    if not quiet:
        print(f"    ΜΗΧΑΝΗ: σίδερο στο FIT με αποθέματα 0 -> χρέος (8, 2)· ΑΔΕΙΟ -> χρέος 0, "
              f"αποθέματα 0· γκρεμισμένο το εργοστάσιο: πίσω {got}, η μηχανή μόνο από το χρέος")
    return None


def main():
    sym, g = TG.build()
    for fn, what in ((pickup, "ΣΗΚΩΜΑ: χωρίς μέταλλο τίποτα, κάθε φορτίο πληρώνεται στο σήκωμα, "
                              "min(10, χρέος)"),
                     (total, "ΣΥΝΟΛΟ: δύο ηλιακά, ακριβώς οι τιμές τους"),
                     (razed, "ΓΚΡΕΜΙΣΜΑ: εργοτάξιο χωρίς φορτία, πρώτα το χρέος"),
                     (machine, "ΜΗΧΑΝΗ: FIT χωρίς υλικά, ΑΔΕΙΟ και γκρέμισμα από το χρέος")):
        why = fn(sym, g)
        say(why is None, why or what)

    # --- αρνητικά ---
    w = TS.W(sym, g)
    find = lambda name, pat, n=24: CA.find(w.m, sym[name], pat, n)
    hole6 = lambda at, v: ("hole", (6, at - 0x4000), v)
    go = find("SP_GO", [0xFE, 2, 0x30])                  # cp 2 · jr nc,spg_take
    can = find("SP_CAN", [0xB7, 0x20], 32)               # or a · jr nz,spc_x
    wake = find("SP_WAKE", [0xB7, 0x28], 8)              # or a · jr z,spw_lost
    out = find("MC_OUT", [0xFE, 127, 0x30])              # cp 127 · jr nc,mco_half
    if None in (go, can, wake, out):
        say(False, f"τα σημεία των αρνητικών δεν βρέθηκαν: {go, can, wake, out}")
        return 1
    for label, fn, patch in (
            ("το sp_go χωρίς πληρωμή", pickup, [(go + 2, 0x18)]),
            ("το sp_go χωρίς πληρωμή", total, [(go + 2, 0x18)]),
            ("το sp_wake ένα ret", pickup, [(sym["SP_WAKE"], 0xC9)]),
            ("το sp_wake χωρίς το EC_WAIT", pickup, [(wake + 1, 0x18)]),
            ("φορτίο πάντα 10", total, [(can + 1, 0x18)]),
            ("το db_cut ένα ret", razed, [hole6(sym["DB_CUT"], 0xC9)]),
            ("το db_cut ένα ret", machine, [hole6(sym["DB_CUT"], 0xC9)]),
            ("η μηχανή που βγαίνει πάντα τα μισά", machine, [hole6(out + 2, 0x18)])):
        why = fn(sym, g, patch, quiet=True)
        say(why is not None, f"ΑΡΝΗΤΙΚΟ «{label}»: " + (why[:110] if why else "ΠΕΡΝΑ"))
    print(f"\n{len(FAIL)} ΑΠΟΤΥΧΙΕΣ" if FAIL else "\nΟΛΑ ΚΑΛΑ")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
