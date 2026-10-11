#!/usr/bin/env python3
"""Πρώτα τα υλικά, μετά ο μηχανικός (βήμα 88, DESIGN §6.9), στο main.sna.

Το παιχνίδι όπως το παίζει ο παίκτης, από την άδεια αρχή δίπλα στο σκάφος:

  ΗΛΙΑΚΟ    δίπλα στο σκάφος. Στο FIRE φεύγουν 15 μέταλλο και το εργοτάξιο
            χρωστά 2 φορτία (ST_OWED = #20)· στον πίνακα ΜΙΑ εργασία, Supply
            μετάλλου [7, κόμβος, -, 4, κόμβος], και ΚΑΜΙΑ Build. Ενας άποικος
            φορτώνει στο σκάφος (spare = μέταλλο, εκεί που στέκεται: κόμβος
            64) και ξεφορτώνει στο εργοτάξιο: #20 -> #10 -> #00. Τα αποθέματα
            δεν ξαναπέφτουν. Η Build εμφανίζεται ΜΟΝΟ όταν το χρέος γίνει 0,
            την παίρνει ο μηχανικός (ρόλος 1), και το ηλιακό τελειώνει.
  ΘΟΛΟΣ     ο πρώτος θόλος S (12 μέταλλο, 8 βιοπλαστικό): δύο Supply, μία ανά
            υλικό, D_POWER = 2 και D_OPS = 1. Φορτώνονται και τα δύο υλικά,
            φτάνουν πριν από τη Build, και ο θόλος τελειώνει με D_POWER =
            D_OPS = 0 — το D_OPS είναι οι χειριστές του από εκεί και πέρα. Και
            όταν σφραγίζεται, κανείς δεν μένει μέσα του: ούτε ο χτίστης ούτε
            όσοι έφεραν τα υλικά.
  ΧΩΡΙΣ     μηχανικό (ο μηχανικός της αρχής γίνεται εργάτης): το ηλιακό
            τροφοδοτείται, η Build περιμένει αδιάθετη — κανείς άλλος δεν την
            παίρνει — και η σειρά 2 του HUD λέει NO ENGINEER· όσο ακόμη
            κουβαλιούνται υλικά, όχι. Μόλις ξαναϋπάρξει μηχανικός, τη χτίζει
            και το μήνυμα φεύγει.

Αρνητικά, με το snapshot πειραγμένο: η Build στο FIRE όπως ως το 87 (το
ΗΛΙΑΚΟ αποτυγχάνει), η Build από οποιονδήποτε (το ΗΛΙΑΚΟ: ο μεταφορέας
στέκεται ήδη στο εργοτάξιο), ένα sp_noeng που δεν απαντά ποτέ (το ΧΩΡΙΣ), και
ένα lk_out που βγάζει μόνο τον χτίστη, όπως ως το 87 (ο ΘΟΛΟΣ).
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_game as TG                                   # noqa: E402
import test_outside as TO                                # noqa: E402
import balance as B                                      # noqa: E402
import hudread                                           # noqa: E402

SHIP, SOLAR, DOME = 64, 65, 0
SOLAR_AT, DOME_AT = (8, 0), TO.DOME_AT                   # μισά tiles
DS_BUILDING, DS_ACTIVE = 1, 2
J_BUILD, J_SUPPLY = 0, 7
S_METAL, S_BIOPL = 3, 4
ENGINEER = 2                                             # ο πράκτορας 2 (§10.1)
STEP = 5


class W(TO.World):
    def jobs(self):
        t = self.L["G_job_tbl"]
        return [list(self.m.read_ram(t + 5 * j, 5)) for j in range(32)
                if self.m.peek(t + 5 * j) != 255]

    def agent(self, i):
        a, f = self.L["G_agent_fields"], lambda o: self.b6(self.L["G_agent_fields"] + o + i)[0]
        return {"f": f(0), "role": f(128), "node": f(256), "dest": f(512),
                "edge": f(640), "task": f(896), "spare": f(1920)}

    def struct(self, k):
        return list(self.b6(self.L["G_struct_tbl"] + 8 * k, 8))

    def dome(self, d):
        return list(self.b6(self.L["G_dome_tbl"] + 24 * d, 8))


def watch(w, done, owed, frames=20000):
    """Δείγμα ανά STEP frames ως το done(): τα χρέη ως ιστορία, ποιος
    κουβαλά τι και πού το φόρτωσε, Build πριν από την ώρα της, ποιος ρόλος
    την πήρε. None αν δεν τελείωσε."""
    log = {"owed": [owed()], "loaded": set(), "early": 0, "builders": set(), "metal": set()}
    carrying = [0] * 4
    t = 0
    while t < frames:
        w.m.run_frames(STEP)
        t += STEP
        o = owed()
        if o != log["owed"][-1]:
            log["owed"].append(o)
        for i in range(4):
            a = w.agent(i)
            if a["spare"] and not carrying[i]:
                log["loaded"].add((a["spare"], a["node"]))
            carrying[i] = a["spare"]
        for j in w.jobs():
            if j[0] == J_BUILD:
                if any(o if isinstance(o, tuple) else (o,)):
                    log["early"] += 1
                if j[2] != 255:
                    log["builders"].add(w.agent(j[2])["role"])
        log["metal"].add(w.w16(6))
        if done():
            log["t"] = t
            return log
    return None


def solar(sym, g, patch=(), quiet=False):
    """ΗΛΙΑΚΟ. Η πρώτη διαφορά από την πρόζα, ή None."""
    w = W(sym, g, patch)
    m = w.m
    metal0 = w.w16(6)
    B.build(m, sym, 4, g + 6, at=SOLAR_AT, fit=False)
    m.run_frames(2)
    rec, jobs = w.struct(1), w.jobs()
    if rec[2] != 0 or rec[4] != DS_BUILDING or rec[7] != 0x20:
        return f"το ηλιακό στο FIRE: εγγραφή {rec} — θέλει K_SOLAR, εργοτάξιο, ST_OWED #20"
    if len(jobs) != 1 or jobs[0][0] != J_SUPPLY or jobs[0][3:] != [4, SOLAR] \
            or jobs[0][1] not in (SOLAR, SHIP):
        return f"το ηλιακό στο FIRE: εργασίες {jobs} — θέλει μία Supply μετάλλου, καμία Build"
    if w.w16(6) != metal0 - 15:
        return f"το μέταλλο στο FIRE: {metal0} -> {w.w16(6)}, όχι -15"
    log = watch(w, lambda: w.struct(1)[4] == DS_ACTIVE, lambda: w.struct(1)[7])
    if log is None:
        return f"το ηλιακό δεν τελείωσε: εγγραφή {w.struct(1)}, εργασίες {w.jobs()}"
    if log["owed"] != [0x20, 0x10, 0]:
        return f"τα χρέη του ηλιακού: {[hex(o) for o in log['owed']]}, η πρόζα λέει #20, #10, #00"
    if log["loaded"] != {(S_METAL, SHIP)}:
        return f"φορτώθηκαν {log['loaded']} — θέλει μέταλλο, στο σκάφος"
    if log["early"]:
        return f"Build πριν φτάσουν τα υλικά, σε {log['early']} δείγματα"
    if log["builders"] != {1}:
        return f"τη Build την πήραν ρόλοι {sorted(log['builders'])}, όχι μόνο ο μηχανικός"
    if log["metal"] != {metal0 - 15}:
        return f"το μέταλλο άλλαξε ενώ κουβαλιόταν: {sorted(log['metal'])}"
    if not quiet:
        print(f"    ηλιακό: #20 -> #10 -> #00 από το σκάφος, Build μετά, χτισμένο σε {log['t']} frames")
    return None


def dome(sym, g, patch=(), quiet=False):
    """ΘΟΛΟΣ. Η πρώτη διαφορά από την πρόζα, ή None."""
    w = W(sym, g, patch)
    m = w.m
    B.build(m, sym, 0, g + 6, at=DOME_AT, room=0, fit=False)
    m.run_frames(2)
    d, kinds = w.dome(DOME), sorted(j[0] for j in w.jobs())
    if d[4] != DS_BUILDING or d[6:8] != [2, 1] or kinds != [J_SUPPLY, J_SUPPLY + 1]:
        return f"ο θόλος στο FIRE: εγγραφή {d}, είδη εργασιών {kinds} — θέλει 2/1 και δύο Supply"
    log = watch(w, lambda: w.dome(DOME)[4] == DS_ACTIVE, lambda: tuple(w.dome(DOME)[6:8]))
    if log is None:
        return f"ο θόλος δεν τελείωσε: εγγραφή {w.dome(DOME)}, εργασίες {w.jobs()}"
    if log["owed"][-1] != (0, 0) or w.dome(DOME)[6:8] != [0, 0]:
        return f"ο θόλος τελείωσε με χρέη/χειριστές {w.dome(DOME)[6:8]}: {log['owed']}"
    if {s for s, _ in log["loaded"]} != {S_METAL, S_BIOPL}:
        return f"φορτώθηκαν {log['loaded']} — θέλει μέταλλο και βιοπλαστικό"
    if log["early"] or log["builders"] != {1}:
        return f"Build πριν από τα υλικά {log['early']} φορές, από ρόλους {sorted(log['builders'])}"
    # ΚΑΝΕΙΣ ΔΕΝ ΚΛΕΙΔΩΝΕΤΑΙ ΜΕΣΑ: ο θόλος σφραγίζεται (lk_done), και όσοι
    # στέκονταν στο εργοτάξιο — ο χτίστης ΚΑΙ οι μεταφορείς — είναι έξω στο
    # σκάφος. Με το lk_out του 87, μόνο ο χτίστης.
    m.run_frames(10)
    inside = [i for i in range(4) if w.agent(i)["node"] == DOME]
    if inside:
        return f"μετά τον θόλο έμειναν μέσα του οι {inside}: {[w.agent(i) for i in inside]}"
    if not quiet:
        print(f"    θόλος: χρέη {log['owed']}, φορτία {sorted(log['loaded'])}, χτισμένος σε {log['t']} frames, "
              f"κανείς μέσα του")
    return None


def no_engineer(sym, g, patch=(), quiet=False):
    """ΧΩΡΙΣ μηχανικό. Η πρώτη διαφορά από την πρόζα, ή None."""
    w = W(sym, g, patch)
    m = w.m
    role = w.L["G_agent_fields"] + 128 + ENGINEER
    w.put6(role, [0])                                    # εργάτης
    B.build(m, sym, 4, g + 6, at=SOLAR_AT, fit=False)
    said = []

    # Το χρέος ΚΑΙ η σειρά, στην ίδια στιγμή: το wait διαβάζει πριν ρωτήσει αν
    # τελείωσε, και αν το τελευταίο φορτίο φτάσει μέσα στα ίδια 25 frames, το
    # NO ENGINEER είναι ήδη σωστό. Ως το βήμα 88 ο χρόνος έπεφτε αλλιώς.
    def hud():
        said.append((w.struct(1)[7], hudread.text(m, sym, 2)[20:40].strip()))
    if w.wait(lambda: w.struct(1)[7] == 0, 20000, 25, hud) is None:
        return f"το ηλιακό δεν τροφοδοτήθηκε: εγγραφή {w.struct(1)}, εργασίες {w.jobs()}"
    if any(owed and "NO ENGINEER" in t for owed, t in said):
        return f"NO ENGINEER όσο κουβαλιούνταν ακόμη υλικά: {said}"
    m.run_frames(2000)
    jobs, row = w.jobs(), hudread.text(m, sym, 2)
    if jobs != [[J_BUILD, SOLAR, 255, 5, SOLAR]] or w.struct(1)[4] != DS_BUILDING:
        return f"χωρίς μηχανικό: εργασίες {jobs}, εγγραφή {w.struct(1)} — η Build περιμένει αδιάθετη"
    if "NO ENGINEER" not in row:
        return f"χωρίς μηχανικό η σειρά 2 λέει |{row}|"
    w.put6(role, [1])                                    # ξανά μηχανικός
    if w.wait(lambda: w.struct(1)[4] == DS_ACTIVE, 20000) is None:
        return f"με μηχανικό ξανά, το ηλιακό δεν τελείωσε: {w.struct(1)}, {w.jobs()}"
    m.run_frames(100)
    if "NO ENGINEER" in hudread.text(m, sym, 2):
        return f"το NO ENGINEER έμεινε: |{hudread.text(m, sym, 2)}|"
    if not quiet:
        print(f"    χωρίς μηχανικό: |{row[20:].rstrip()}|, η Build αδιάθετη 2.000 frames· "
              f"με μηχανικό χτίστηκε και το μήνυμα έφυγε")
    return None


def main():
    sym, g = TG.build()
    fails = 0
    for fn, what in ((solar, "ηλιακό: δύο φορτία μετάλλου από το σκάφος, μετά η Build, "
                             "μόνο από τον μηχανικό"),
                     (dome, "θόλος: δύο Supply, και τα δύο υλικά πριν από τη Build, "
                            "τελειώνει χωρίς χρέη"),
                     (no_engineer, "χωρίς μηχανικό: η Build περιμένει και το HUD λέει "
                                   "NO ENGINEER, μόνο τότε")):
        why = fn(sym, g)
        if why:
            print(f"ΑΠΟΤΥΧΙΑ: {why}")
            fails += 1
        else:
            print(f"OK {what}")

    # --- αρνητικά ---
    m = B.boot(sym, TG.SNA)
    find = lambda at, pat, n=64: next((at + k for k in range(n)
                                       if list(m.read_ram(at + k, len(pat))) == pat), None)
    jobs_at = find(sym["BDK_POST"], [0xCD, sym["SP_JOBS"] & 255, sym["SP_JOBS"] >> 8], 8)
    pb = sym["JB_POST_BUILD"]
    scf = find(sym["SPN_AG"], [0x37], 40)                # scf: κανείς
    lko = find(sym["LK_OUT"], [0x01, 0x80, 0], 16)       # ld bc,N_AGENT (lk_each, cpir από το 104)
    for label, fn, patch in (
            ("Build στο FIRE (ως το 87)", solar,
             jobs_at and [(jobs_at + 1, pb & 255), (jobs_at + 2, pb >> 8)]),
            ("Build από οποιονδήποτε", solar, [(sym["JOB_ROLES"], 0xFF)]),
            ("sp_noeng χωρίς απάντηση", no_engineer, scf and [(scf, 0xB7)]),   # or a
            # το lk_each κοιτά μόνο τον χτίστη, όπως το lk_out ως το 87:
            # ld hl,(AG_PG + 1) * 256 -> + ENGINEER, ld bc,N_AGENT -> 1
            ("lk_out μόνο για τον χτίστη", dome,
             lko and [(lko - 3 + 1, ENGINEER), (lko + 1, 1)])):
        if not patch:
            print(f"ΑΠΟΤΥΧΙΑ: δεν βρέθηκε πού να πειραχτεί για «{label}»")
            fails += 1
            continue
        why = fn(sym, g, patch, quiet=True)
        if why:
            print(f"OK ΑΡΝΗΤΙΚΟ: με «{label}» αποτυγχάνει ({why[:90]})")
        else:
            print(f"ΑΠΟΤΥΧΙΑ ΑΡΝΗΤΙΚΟΥ: με «{label}» περνά")
            fails += 1
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
