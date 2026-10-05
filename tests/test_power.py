#!/usr/bin/env python3
"""ΠΟΙΟΣ ΣΤΑΜΑΤΑ ΠΡΩΤΟΣ ΟΤΑΝ ΛΕΙΨΕΙ ΤΟ ΡΕΥΜΑ (DESIGN §6.5).

Ο πίνακας ροών του §6.5 γράφει για την αστοχία ρεύματος: «machines stop, THEN
oxygen stops». Ο κώδικας δεν είχε «then»: το power_ok ήταν μία σημαία για
ολόκληρη την αποικία, οπότε το ίδιο μπλακάουτ που σταματούσε τις αντλίες
σταματούσε και τη γεννήτρια οξυγόνου.

Και τιμωρούσε τη σωστή κίνηση. Το βήμα 31 μέτρησε ότι η απάντηση στο νερό είναι
δεύτερη αντλία· η δεύτερη αντλία πάει τη ζήτηση από 22 σε 28 απέναντι σε 36
παραγωγής, η μέρα αποταμιεύει ~50 και η νύχτα θέλει ~130. Μετρημένο στο ίδιο
binary, δύο αντλίες, 8.000 frames:

    δείγματα χωρίς ρεύμα: 13/80   παραγωγή O2 20 -> 0   οξυγόνο αποίκου 208

Δύο τμήματα, γιατί δύο πράγματα μπορούν να σπάσουν:

  1. Ο ΚΑΝΟΝΑΣ, στην αναφορά (tools/econ.py) και χωρίς εξομοιωτή: πόσο δανείζει
     η μπαταρία στις μηχανές πριν κρατήσει τα υπόλοιπα για την υποστήριξη ζωής.
     Το tests/test_sim.py συγκρίνει ΟΛΗ την οικονομία του Z80 με την αναφορά
     byte προς byte, οπότε ο κανόνας εδώ είναι ο κανόνας και εκεί.
  2. Η ΑΠΟΙΚΙΑ, στο κανονικό binary: η νύχτα έρχεται, το φορτίο πέφτει, και το
     οξυγόνο ΔΕΝ σβήνει.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/vasilhs/cpcemu")

from sprites import load_map, load_bin                             # noqa: E402
import econ as E                                                   # noqa: E402
import balance as B                                                # noqa: E402
import test_game as T                                              # noqa: E402
import agents as A                                                 # noqa: E402

FAIL = []


def check(ok, msg):
    print(("OK " if ok else "ΛΑΘΟΣ ") + msg)
    if not ok:
        FAIL.append(msg)


def night(store, use, ess, solar=0, cap=360):
    """Μια περιστροφή ισοζυγίου με δεδομένη μπαταρία και ζήτηση.

    `solar` = παραγωγή που έρχεται από πάνελ· 0 σημαίνει νύχτα.
    """
    e = E.Econ()
    e.mach_power, e.ess_power, e.power_store = use, ess, store
    e.day, e.storm = (1 if solar else 0), 0
    n = 0
    if solar:                                   # ένα μεγάλο πάνελ βγάζει 18
        while n * E.SOLAR_OUT[2] < solar:
            b = n * E.STRUCT_REC
            e.struct[b + E.ST_KIND] = E.K_SOLAR
            e.struct[b + E.ST_SIZE] = 2
            e.struct[b + E.ST_STATE] = E.DS_ACTIVE
            n += 1
    b = n * E.STRUCT_REC                        # και ένας συλλέκτης για ταβάνι
    e.struct[b + E.ST_KIND] = E.K_COLLECTOR
    e.struct[b + E.ST_SIZE] = 2
    e.struct[b + E.ST_STATE] = E.DS_ACTIVE
    E.flow_cycle(e)
    return e


def rule():
    """1. Ο κανόνας: η ρεζέρβα της υποστήριξης ζωής."""
    # Νύχτα, ζήτηση 28, υποστήριξη ζωής 4: η ρεζέρβα είναι 4 x 8 = 32, άρα οι
    # μηχανές δανείζονται μόνο αν η μπαταρία έχει 28 + 32 = 60.
    e = night(200, 28, 4)
    check(e.power_ok == E.POWER_ALL and e.power_store == 172,
          f"γεμάτη μπαταρία: όλα γυρίζουν και η νύχτα πληρώνεται από αυτήν "
          f"(στάθμη {e.power_ok}, μπαταρία 200 -> {e.power_store})")
    e = night(59, 28, 4)
    check(e.power_ok == E.POWER_ESS and e.power_store == 55,
          f"ΕΝΑ ΚΑΤΩ ΑΠΟ ΤΟ ΚΑΤΩΦΛΙ (59 < 28+32): πέφτει το φορτίο και η "
          f"μπαταρία πληρώνει ΜΟΝΟ την υποστήριξη ζωής, 4 τον κύκλο "
          f"(στάθμη {e.power_ok}, 59 -> {e.power_store})")
    e = night(60, 28, 4)
    check(e.power_ok == E.POWER_ALL and e.power_store == 32,
          f"και ΕΝΑ ΠΑΝΩ (60): ακόμη όλα, και μένει ακριβώς η ρεζέρβα "
          f"(στάθμη {e.power_ok}, 60 -> {e.power_store})")
    # Το κατώφλι είναι το ΣΗΜΕΙΟ ΟΛΗΣ ΤΗΣ ΑΛΛΑΓΗΣ: χωρίς αυτό, οι μηχανές
    # αδειάζουν τη μπαταρία στους δύο πρώτους κύκλους της νύχτας και το οξυγόνο
    # σβήνει ούτως ή άλλως — δηλαδή η σειρά «πρώτα οι μηχανές» δεν αγοράζει
    # τίποτα. Με 56 στη μπαταρία και 4 ανά κύκλο, η υποστήριξη ζωής αντέχει
    # δεκατέσσερις κύκλους· η νύχτα είναι 4,7.
    e = night(3, 28, 4)
    check(e.power_ok == E.POWER_NONE and e.power_store == 0,
          f"και όταν δεν φτάνει ούτε γι' αυτήν, μπλακάουτ — η στάθμη υπάρχει, "
          f"δεν εξαφανίστηκε (στάθμη {e.power_ok})")
    # Μέρα με αμμοθύελλα ή λίγο πάνελ: η παραγωγή καλύπτει την υποστήριξη ζωής
    # αλλά όχι τις μηχανές. Το περίσσευμα ΦΟΡΤΙΖΕΙ — αλλιώς η αποικία δεν
    # ξαναβγαίνει ποτέ από το πέσιμο φορτίου.
    e = night(10, 28, 4, solar=18)
    check(e.power_ok == E.POWER_ESS and e.power_store == 24,
          f"με μισό ήλιο: πέφτει το φορτίο ΚΑΙ φορτίζει (10 + 18 - 4 = "
          f"{e.power_store}, στάθμη {e.power_ok})")

    # --- ΓΙΑΤΙ ΥΠΑΡΧΕΙ Η ΡΕΖΕΡΒΑ, με το αρνητικό της δείγμα από δίπλα -------
    # Το αρνητικό δείγμα της αποικίας παρακάτω περνά ΚΑΙ με ρεζέρβα μηδέν: εκεί
    # το οξυγόνο το σώζει η ΣΤΑΘΜΗ (P_ESS), όχι η ρεζέρβα, γιατί η νύχτα είναι
    # κοντή και η μπαταρία δεν προλαβαίνει να αδειάσει. Η ρεζέρβα πληρώνεται σε
    # ΜΕΓΑΛΗ νύχτα — αμμοθύελλα, ή μεγαλύτερη βάση — και αυτό μετριέται εδώ,
    # χωρίς εξομοιωτή: οκτώ κύκλοι στο σκοτάδι, ζήτηση 16, υποστήριξη ζωής 4.
    def darkness(cycles, store, use, ess, reserve):
        keep = E.RESERVE_CYCLES
        E.RESERVE_CYCLES = reserve
        e = E.Econ()
        e.mach_power, e.ess_power, e.power_store = use, ess, store
        e.day, e.storm = 0, 0
        e.struct[E.ST_KIND] = E.K_COLLECTOR
        e.struct[E.ST_SIZE] = 2
        e.struct[E.ST_STATE] = E.DS_ACTIVE
        out = []
        for _ in range(cycles):
            E.flow_cycle(e)
            out.append(e.power_ok)
        E.RESERVE_CYCLES = keep
        return out, e.power_store

    with_res, left = darkness(8, 56, 16, 4, E.RESERVE_CYCLES)
    none_res, _ = darkness(8, 56, 16, 4, 0)
    check(E.POWER_NONE not in with_res and left,
          f"οκτώ κύκλοι σκοτάδι ΜΕ ρεζέρβα: κανένα μπλακάουτ και μένει "
          f"μπαταρία {left} για την αυγή — {with_res}")
    check(E.POWER_NONE in none_res,
          f"και ΧΩΡΙΣ ρεζέρβα η ίδια νύχτα σβήνει: οι μηχανές τρώνε τη "
          f"μπαταρία σε τρεις κύκλους και μετά δεν αναπνέει κανείς — "
          f"{none_res}")


def colony():
    """2. Η αποικία: δύο αντλίες, και η νύχτα δεν παίρνει το οξυγόνο."""
    sym, g = T.build()
    m = B.boot(sym, T.SNA)
    for k in (3, 4):                             # RICH: υλικά για την αλυσίδα
        m.poke(g + B.EC["STOCK"] + k * 2, 500 & 255)
        m.poke(g + B.EC["STOCK"] + k * 2 + 1, 500 >> 8)
    # ΤΟ ΣΕΝΑΡΙΟ ΤΟΥ ΒΗΜΑΤΟΣ 31, αυτούσιο: δύο ηλιακά, ΔΥΟ αντλίες, συλλέκτης
    # και η αλυσίδα της τροφής. Με μία αντλία το νερό στερεύει (§15) και με δύο
    # έπεφτε το οξυγόνο κάθε νύχτα — η δοκιμή θέλει ακριβώς αυτή την αποικία.
    items = (4, 4, 7, 7, 6, (1, 3), (0, 5), (0, 1))
    spots, res, k = B.clear_spots(6, 10), {}, 0
    for it in items:
        item, room = it if isinstance(it, tuple) else (it, None)
        w = (4, 6, 8)[item] if item <= 2 else (4 if item == 8 else 3)
        spot, k = B.pick_spot(item, spots, k, res)
        if spot is None or not B.build(m, sym, item, g + 6,
                                       at=(2 * spot[0] + w, 2 * spot[1] + w),
                                       room=room):
            # ΜΕ ΤΟ check, ΟΧΙ ΜΕ print: ως το βήμα 67 αυτό τυπωνόταν και η δοκιμή
            # έβγαινε με 0. Ενα bd_res που αρνιόταν το ορυχείο περνούσε, αφού
            # η αποικία δεν στηνόταν ποτέ και τίποτα παρακάτω δεν ελεγχόταν.
            check(False, f"δεν μπήκε το κτίσμα {item} — η δοκιμή δεν στήθηκε")
            return
    m.poke(sym["UI_SPD"], 4)

    def w16(a):
        return m.peek(a) | (m.peek(a + 1) << 8)

    smap, blob = load_map(), load_bin()
    f = smap["font_gfx"]
    font = blob[f.off:f.off + f.size]
    glyph = {bytes(font[i * 16:(i + 1) * 16]): chr(32 + i) for i in range(96)}

    def alert():
        # Η γραμμή συναγερμού: το δεξί μισό της σειράς 2 του HUD.
        off = m.peek(sym["CAM_OFF"]) | (m.peek(sym["CAM_OFF"] + 1) << 8)
        ram = m.read_ram(0xC000, 0x4000)

        def byte(x, y):
            return ram[(y & 7) * 0x800 + (((y >> 3) * 80 + x + 2 * off) & 0x7FF)]
        return "".join(glyph.get(bytes(byte(c * 2 + k, 176 + l)
                                       for l in range(8) for k in range(2)), "#")
                       for c in range(20, 40)).strip()

    shed = dark = said = 0
    o2_zero, minox, water = 0, 255, []
    for _ in range(80):
        m.run_frames(100)
        pok = m.peek(g + B.EC["POK"])
        shed += pok == 2
        dark += pok == 0
        if pok == 2 and "LOW POWER" in alert():
            said += 1
        if not w16(g + B.EC["O2PROD"]):
            o2_zero += 1
        live = [a for a in A.snap(m, sym) if a["flags"] & A.F_ALIVE]
        minox = min([minox] + [a["oxygen"] for a in live])
        water.append((pok, w16(g)))

    check(shed, f"η νύχτα ΠΕΦΤΕΙ ΤΟ ΦΟΡΤΙΟ: {shed}/80 δείγματα στη στάθμη 2 — "
                f"χωρίς αυτό η δοκιμή δεν δοκιμάζει τίποτα")
    check(not dark and not o2_zero,
          f"και το οξυγόνο ΔΕΝ σβήνει: {dark} δείγματα μπλακάουτ, {o2_zero} με "
          f"μηδενική παραγωγή O2 (πριν: 13 και 13 στα 80)")
    check(minox > 240,
          f"ούτε αδειάζει η μπάρα κανενός: χαμηλότερο οξυγόνο {minox} "
          f"(πριν: 208)")
    # ΚΑΙ ΤΟ ΤΙΜΗΜΑ, ΜΕΤΡΗΜΕΝΟ: οι αντλίες είναι από τα φορτία που πέφτουν,
    # άρα το νερό ανεβαίνει μόνο με ρεύμα. Ο έλεγχος είναι ότι ΔΕΝ ανεβαίνει
    # όσο το φορτίο είναι πεσμένο — αλλιώς κάποιος θα είχε ξεχάσει τις αντλίες
    # στην άλλη μεριά του κλαδιού.
    #
    # ΚΑΙ ΤΑ ΔΥΟ ΑΚΡΑ ΤΟΥ ΔΙΑΣΤΗΜΑΤΟΣ ΠΕΣΜΕΝΑ, όχι μόνο το πρώτο: το δείγμα
    # είναι κάθε 100 πραγματικά frames και ο κύκλος ροής ~272, οπότε ένα
    # διάστημα που αρχίζει στη στάθμη 2 μπορεί να περιέχει την αυγή — και τότε
    # το νερό ανεβαίνει νόμιμα. Με την πρώτη, αφελή μορφή του ελέγχου αυτό
    # έβγαινε «3 δείγματα» και έμοιαζε με σφάλμα του κώδικα.
    rose = sum(1 for (p, w), (p2, w2) in zip(water, water[1:])
               if p == 2 and p2 == 2 and w2 > w)
    check(rose == 0,
          f"και οι αντλίες όντως σταματούν: {rose} διαστήματα με το νερό να "
          f"ανεβαίνει ενώ το φορτίο ήταν πεσμένο σε όλο τους το μήκος")
    check(water[-1][1] > water[0][1],
          f"η αποικία πάντως κερδίζει νερό μέσα στη μέρα: "
          f"{water[0][1]} -> {water[-1][1]}")
    # ΚΑΙ ΤΟ ΛΕΕΙ. Οι σταματημένες μηχανές δεν φαίνονται πουθενά αλλού: η μόνη
    # ορατή διαφορά είναι ότι τα αποθέματα πάψανε να ανεβαίνουν, και αυτό δεν
    # το προσέχει κανείς μέσα στη νύχτα.
    check(said, f"και η γραμμή συναγερμού λέει LOW POWER όσο το φορτίο είναι "
                f"πεσμένο: {said}/{shed} δείγματα")


def main():
    rule()
    colony()
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
