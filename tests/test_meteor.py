#!/usr/bin/env python3
"""Η βροχή μετεωριτών στο κανονικό παιχνίδι (DESIGN §6.10).

Το tests/test_sim.py δείχνει ότι ο Z80 και η αναφορά (tools/econ.py) συμφωνούν
byte προς byte για το ΤΙ χτυπά. Εδώ, στο binary που φορτώνει ο παίκτης, τα
όσα η αναφορά δεν ξέρει — κόσμο, οθόνη, ήχο — και αν η αποικία συνέρχεται:

  ΚΡΑΤΗΡΕΣ   Η αναφορά προβλέπει ποια tiles ελεύθερης γης γίνονται κρατήρες,
             και αλλάζουν ΑΚΡΙΒΩΣ αυτά: κανένα κατειλημμένο, κανένα άλλο.
  ΟΘΟΝΗ      Οι κρατήρες ζωγραφίζονται από τη λίστα αλλαγών (DK_TILE) χωρίς
             πλήρη σχεδίαση — το κανάρινι ζει — και η εικόνα είναι η πλήρης
             σχεδίαση. ΑΡΝΗΤΙΚΟ: χωρίς το wh_push οι κρατήρες είναι στον χάρτη
             αλλά όχι στην οθόνη. ΑΡΝΗΤΙΚΟ (βήμα 96): ο διάδρομος στο κέντρο
             του θόλου πατά μισό πλάτος στο διπλανό tile, και χωρίς τη
             σφραγίδα του (cr_stampx) ο κρατήρας εκεί σβήνει τη λωρίδα του.
  ΑΠΟΙΚΙΑ    Η πίστα γίνεται εργοτάξιο και ξαναχτίζεται· η μηχανή οξυγόνου
             σταματά και την επισκευάζουν.
  ΣΗΜΑ       (βήμα 109) Η πίστα που χτύπησε έχει στην οθόνη το σήμα του
             εργοταξίου, χωρίς πλήρη σχεδίαση: το DK_TILE του st_redraw.
             ΑΡΝΗΤΙΚΟ: χωρίς αυτό η πίστα μένει όπως ήταν ως να ξαναχτιστεί.
  ΠΑΙΚΤΗΣ    Ο πίνακας γράφει METEOR SHOWER, ο ήχος της κρούσης παίζει.
  ΣΥΧΝΟΤΗΤΑ  Η ζαριά μία ανά ~5 sol, και ΠΟΤΕ στον ίδιο γύρο με θύελλα,
             βλάβη, έκλαμψη ή επισκέπτη (η γεννήτρια των συμβάντων, στην
             αναφορά). Από το βήμα 121 η βροχή περιμένει και 20 ζωντανούς και
             την ησυχία μετά από άλλη καταστροφή (ev_may, tests/test_sim.py).
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/vasilhs/cpcemu")

import econ as EC                                                  # noqa: E402
import test_reveal as R                                            # noqa: E402
import codeat                                                      # noqa: E402
import world as W                                                  # noqa: E402
import reach                                                       # noqa: E402
import route                                                       # noqa: E402
from test_route import hud_row                                     # noqa: E402

def _lay(name):
    """Μια διεύθυνση του build/layout.asm (βήμα 154: οι πίνακες της 6 κουνήθηκαν)."""
    for line in open(os.path.join(ROOT, "build", "layout.asm"), encoding="utf-8"):
        p = line.split()
        if len(p) >= 3 and p[0] == name and p[1] == "equ":
            return int(p[2].lstrip("#"), 16)
    raise SystemExit(f"δεν βρέθηκε το {name}")


FAIL = []
DOME_TBL, STRUCT_TBL = _lay("G_dome_tbl") - 0x4000, _lay("G_struct_tbl") - 0x4000   # μέσα στην τράπεζα 6
PAD_NODE = 64                            # η δομή 0 της αρχικής αποικίας
CENTER = (-8, 8)                         # το κέντρο της πίστας, σε tiles
CAM = (-18, 3)                           # η πίστα στη μέση του κάδρου
WORST_MAX = 120                          # ms ανά γύρο κατά τη βροχή
# μετατοπίσεις από το G_econ_state (src/const.asm)
EC_POK, EC_O2OK = 46, 47
EC_METEOR, EC_MCX, EC_MCY, EC_MRND = 86, 87, 88, 89
EC_JOBS = EC.ECON_BYTES                  # ο G_job_tbl ακολουθεί (build/layout.asm)


def check(ok, msg):
    print(("OK " if ok else "ΛΑΘΟΣ ") + msg)
    if not ok:
        FAIL.append(msg)


def predict(G, seed):
    """(κόμβοι που χτυπήθηκαν, tiles που γίνονται κρατήρες) — η αναφορά για τα
    κτίρια, και ο κανόνας του mt_ground για τον κόσμο."""
    b6, b4 = G.bank(6), G.bank(4)
    e = EC.Econ()
    e.dome = bytearray(b6[DOME_TBL:DOME_TBL + EC.MAX_DOME * EC.DOME_REC])
    e.struct = bytearray(b6[STRUCT_TBL:STRUCT_TBL + EC.MAX_STRUCT * EC.STRUCT_REC])
    e.meteor, e.mrnd, (e.mcx, e.mcy) = EC.METEOR_N, seed, CENTER
    hits, craters, free = [], [], []
    for _ in range(EC.METEOR_N):
        b = EC._mbyte(e)
        tx = EC._s8(e.mcx + (b & 15) - 8)
        ty = EC._s8(e.mcy + (b >> 4) - 8)
        if not (-64 <= tx < 64 and -64 <= ty < 64):
            continue
        for n in range(EC.MAX_DOME + EC.MAX_STRUCT):
            rec, base = EC._node_rec(e, n)
            if rec[base + EC.D_STATE]:
                x0, y0, w, h = EC._footprint(e, n)
                if ((tx - x0) & 0xFF) < w and ((ty - y0) & 0xFF) < h:
                    hits.append(n)
                    break
        else:
            free.append((tx, ty))
            v = b4[W.index(tx, ty)]
            if not v & 0x30 and (v & 7) in (W.GROUND, W.DUST, W.ROCK,
                                             W.FOUNDATION):
                if (tx, ty) not in craters:
                    craters.append((tx, ty))
    predict.free = free                  # κάθε πτώση έξω από κτίριο, πιασμένη ή όχι
    return hits, craters


def half_tiles():
    """Τα tiles του μισού πλάτους (βήμα 96, cr_stampx) των τριών διαδρόμων της
    αποικίας δοκιμών, από τον θόλο 0 προς τον 1, τον 2 και το airlock
    (src/colony.asm), όπως τα βγάζει το reach.half_tiles — όσα απέχουν δύο
    tiles και πάνω από κάθε θόλο. Μετρημένο στο βήμα 132: μια πτώση στο (-1, 5),
    δίπλα στον θόλο 2, άφησε την οθόνη σωστή (0 bytes)· μία στο (-2, 3) έσβησε
    τη λωρίδα στα (-1, 3) και (-1, 4), 32 bytes, όπως στο βήμα 131."""
    a, out = (0, 0, 0), set()
    for z in ((16, 0, 0), (0, 16, 0), (0, -10, route.AIRLOCK)):
        side, runs = route.plan(*a, *z)
        f, t = (a, z) if side == 0 else (z, a)
        out.update(reach.half_tiles(f, t, runs))
    near = lambda x, y, cx, cy: cx - 3 <= x <= cx + 2 and cy - 3 <= y <= cy + 2
    return {(x, y) for x, y in out
            if not any(near(x, y, cx, cy) for cx, cy in ((0, 0), (8, 0), (0, 8)))}


def seen(t):
    return 0 <= t[0] - CAM[0] < 20 and 0 <= t[1] - CAM[1] < 10


def shower(sym, g, cut_push=False, no_half=False, cut_mark=False):
    if no_half:
        # cr_stampx -> JP cr_stamp ΠΡΙΝ χτιστεί η αποικία (src/colony.asm,
        # στα καρέ του balance.boot): τα tiles του μισού πλάτους μένουν άδεια.
        boot = R.B.boot

        def unstamped(sym_, snapshot):
            from cpc import CPC
            m = CPC()
            m.run_frames(60)
            assert m.quickload(snapshot), "quickload απέτυχε"
            at, st = sym["CR_STAMPX"], sym["CR_STAMP"]
            m.write_ram(at, bytes([0xC3, st & 0xFF, st >> 8]))
            m.run_frames(250)
            return m
        R.B.boot = unstamped
        try:
            G = R.Game(sym, g)
        finally:
            R.B.boot = boot
    else:
        G = R.Game(sym, g)
    # ΩΣ ΤΗΝ ΠΡΩΤΗ ΔΗΜΟΣΙΕΥΣΗ ΤΗΣ ΡΟΗΣ: πριν από αυτήν το EC_O2PROD είναι 0
    # και ο πίνακας λέει «NO OXYGEN», που είναι σοβαρότερο από τη βροχή.
    for _ in range(300):
        if G.m.peek(g + EC_O2OK) and G.m.peek(g + EC_POK) == 1:
            break
        G.m.run_frames(10)
    G.camera(*CAM)
    # Ο ΣΠΟΡΟΣ ΒΡΙΣΚΕΤΑΙ, ΔΕΝ ΚΑΡΦΩΝΕΤΑΙ: ο πρώτος που χτυπά την πίστα και
    # τον θόλο οξυγόνου και αφήνει τουλάχιστον τρεις κρατήρες στο κάδρο. ΚΑΙ
    # ΜΙΑ ΠΤΩΣΗ ΩΣ ΕΝΑ TILE ΑΠΟ TILE ΤΟΥ ΜΙΣΟΥ ΠΛΑΤΟΥΣ, μέσα στο κάδρο (βήμα
    # 132): ο κρατήρας ξαναζωγραφίζει και τα γύρω του, και εκεί η κατοχή του
    # cr_stampx κρατά τη λωρίδα — μόνο εκεί πιάνει το αρνητικό του. Ως το
    # βήμα 131 ο σπόρος 215 την είχε κατά τύχη· ο κόσμος με το πλατό 8 έδωσε
    # πρώτο τον 53, χωρίς αυτήν, και το αρνητικό δεν έπιανε τίποτα.
    half = half_tiles()
    by = lambda t: any(max(abs(t[0] - x), abs(t[1] - y)) <= 1 for x, y in half)
    for seed in range(1, 4000):
        hits, craters = predict(G, seed)
        if (PAD_NODE in hits and 0 in hits and sum(map(seen, craters)) >= 3
                and any(by(t) and seen(t) for t in predict.free)):
            break
    else:
        sys.exit("κανένας σπόρος δεν χτυπά πίστα, θόλο και έδαφος")
    if cut_push:
        # JP wh_push -> RET, στο τέλος του mt_ground
        # Στο b6code από το βήμα 110: codeat, όχι peek/poke (τράπεζα 6).
        at, wp = sym["MTG_BACK"], sym["WH_PUSH"]          # βήμα 76: ήταν mtg_no
        a = codeat.find(G.m, at, [0xC3, wp & 0xFF, wp >> 8], 32)
        if a is None:
            sys.exit("δεν βρέθηκε το JP wh_push στο mt_ground")
        codeat.poke(G.m, a, 0xC9)
    if cut_mark:
        # CALL st_redraw -> τρία NOP, στο mth_struct
        at, sr = sym["MTH_STRUCT"], sym["ST_REDRAW"]
        a = codeat.find(G.m, at, [0xCD, sr & 0xFF, sr >> 8], 48)
        if a is None:
            sys.exit("δεν βρέθηκε το CALL st_redraw στο mth_struct")
        for k in range(3):
            codeat.poke(G.m, a + k, 0)
    world0 = bytes(G.bank(4)[:W.SIZE])
    pic0 = G.play()
    # Το κανάρινι μακριά από κάθε κρατήρα και τον 3x3 γύρω του.
    far = [(x, y) for y in range(10) for x in range(20)
           if all(max(abs(x + CAM[0] - c[0]), abs(y + CAM[1] - c[1])) > 2
                  for c in craters)]
    cx, cy = far[-1]
    c = G.canary(cx * 4 + 1, cy * 16 + 4)

    m = G.m
    m.poke(g + EC_METEOR, EC.METEOR_N)
    m.poke(g + EC_MRND, seed & 0xFF)
    m.poke(g + EC_MRND + 1, seed >> 8)
    m.poke(g + EC_MCX, CENTER[0] & 0xFF)
    m.poke(g + EC_MCY, CENTER[1] & 0xFF)
    texts, booms, hp_min = set(), 0, 255
    fx0, fx1 = sym["FX_METEOR"], sym["FX_DEATH"]
    G.iters = []
    for k in range(400):
        G.run(20_000)
        ptr = m.peek(sym["SN_ST"] + 1) | (m.peek(sym["SN_ST"] + 2) << 8)   # wait, δείκτης, FX
        booms += fx0 <= ptr < fx1
        hp_min = min(hp_min, G.bank(6)[DOME_TBL + EC.D_HEALTH])
        if (k % 4 == 0 and m.peek(g + EC_METEOR) and m.peek(g + EC_POK) == 1
                and m.peek(g + EC_O2OK)):
            t = hud_row(m, sym, 2)[20:].strip()
            if "#" not in t:             # το HUD πριν ξαναγραφτεί
                texts.add(t)
        if m.peek(g + EC_METEOR) == 0 and k > 30:
            break
    worst = G.worst()
    pad = G.state(PAD_NODE)
    jobs = bytes(m.peek(g + EC_JOBS + i) for i in range(EC.MAX_JOB * EC.JOB_REC))
    built = any(jobs[j * 5] == EC.J_BUILD and jobs[j * 5 + 1] == PAD_NODE
                for j in range(EC.MAX_JOB))
    alive = G.alive(c)                   # ΠΡΙΝ: το truth() ξανασχεδιάζει
    pic, ref = G.truth()
    world1 = bytes(G.bank(4)[:W.SIZE])
    b6 = G.bank(6)
    sx = lambda v: v - 256 if v > 127 else v
    pc = (sx(b6[STRUCT_TBL + (PAD_NODE - 64) * 8]),
          sx(b6[STRUCT_TBL + (PAD_NODE - 64) * 8 + 1]))
    return dict(G=G, seed=seed, hits=hits, craters=craters, world0=world0,
                world1=world1, pic0=pic0, pic=pic, ref=ref, alive=alive,
                mark=R.site_mark(pic, *pc, CAM), mark_ref=R.site_mark(ref, *pc, CAM),
                spot=(cy * 16 + 4) * 80 + cx * 4 + 1,
                texts=texts, booms=booms, hp_min=hp_min, worst=worst, pad=pad,
                job=built)


def main():
    sym, g = R.T.build()

    s = shower(sym, g)
    G, cr = s["G"], s["craters"]
    print(f"   σπόρος {s['seed']}: κρούσεις σε κόμβους {s['hits']}, κρατήρες {cr}")
    changed = [(x, y) for y in range(-64, 64) for x in range(-64, 64)
               if s["world0"][W.index(x, y)] != s["world1"][W.index(x, y)]]
    exact = sorted(changed) == sorted(cr) and all(
        s["world1"][W.index(*t)] == (s["world0"][W.index(*t)] & 0xC0) | W.CRATER
        for t in cr)
    check(exact, f"κρατήρες: άλλαξαν ακριβώς τα {len(cr)} tiles που προέβλεψε η "
                 f"αναφορά, κρατήρας με το decor τους — {len(changed)} άλλαξαν")

    ok, how = R.shape(s["pic"], s["ref"], skip={s["spot"]})
    drawn = [t for t in cr if seen(t) and any(
        s["pic0"][(t[1] - CAM[1]) * 16 * 80 + y * 80 + (t[0] - CAM[0]) * 4 + x]
        != s["pic"][(t[1] - CAM[1]) * 16 * 80 + y * 80 + (t[0] - CAM[0]) * 4 + x]
        for y in range(16) for x in range(4))]
    check(s["alive"] and ok and len(drawn) == sum(map(seen, cr)),
          f"οθόνη: {len(drawn)} κρατήρες ζωγραφίστηκαν χωρίς πλήρη σχεδίαση "
          f"(κανάρινι {'ζει' if s['alive'] else 'ΝΕΚΡΟ'}), και η εικόνα "
          f"είναι η πλήρης σχεδίαση — {how}")
    check(s["worst"] < WORST_MAX,
          f"ο χειρότερος γύρος κατά τη βροχή ήταν {s['worst']:.0f} ms "
          f"(όριο {WORST_MAX})")
    check(s["pad"][0] == EC.DS_BUILDING and s["job"],
          f"η πίστα χτυπήθηκε: κατάσταση {s['pad'][0]} (εργοτάξιο), "
          f"ακεραιότητα {s['pad'][1]}, εργασία Build "
          f"{'δημοσιευμένη' if s['job'] else 'ΚΑΜΙΑ'}")
    check(s["mark"] and s["mark_ref"],
          "και έχει το σήμα του εργοταξίου στο κέντρο της, όπως και στην πλήρη "
          "σχεδίαση (βήμα 109)")
    check(s["hp_min"] == 0, f"η μηχανή οξυγόνου σταμάτησε (υγεία ως {s['hp_min']})")
    check("METEOR SHOWER" in s["texts"],
          f"ο πίνακας έγραψε {sorted(s['texts'])}")
    check(s["booms"] > 0, f"ο ήχος της κρούσης έπαιξε ({s['booms']} καρέ)")

    # --- η αποικία συνέρχεται -------------------------------------------
    on = [1] * 16
    G.go(on)
    pad = hp = None
    for _ in range(600):
        G.m.run_frames(25)
        pad = G.state(PAD_NODE)
        hp = G.bank(6)[DOME_TBL + EC.D_HEALTH]
        if pad[0] == EC.DS_ACTIVE and hp:
            break
    check(pad[0] == EC.DS_ACTIVE and hp > 0,
          f"και η αποικία συνήλθε: πίστα {'ξαναχτισμένη' if pad[0] == EC.DS_ACTIVE else 'ΕΡΓΟΤΑΞΙΟ'}, "
          f"μηχανή οξυγόνου υγεία {hp}")

    # --- ΑΡΝΗΤΙΚΟ: ο κρατήρας χωρίς τη λίστα αλλαγών ----------------------
    n = shower(sym, g, cut_push=True)
    bad = sum(1 for i, (a, b) in enumerate(zip(n["pic"], n["ref"]))
              if a != b and i != n["spot"])
    check(bad > 0 and n["world1"] == s["world1"],
          f"ΑΡΝΗΤΙΚΟ: χωρίς το wh_push οι ίδιοι κρατήρες είναι στον χάρτη αλλά "
          f"όχι στην οθόνη — {bad} λάθος bytes")

    # --- ΑΡΝΗΤΙΚΟ: η πίστα χωρίς το σήμα της (βήμα 109) --------------------
    # Ως το 109 έτσι ήταν: μια δομή που χτύπησε φαινόταν ίδια ως να ξαναχτιστεί.
    k = shower(sym, g, cut_mark=True)
    bad = sum(1 for i, (a, b) in enumerate(zip(k["pic"], k["ref"]))
              if a != b and i != k["spot"])
    check(not k["mark"] and k["mark_ref"] and bad > 0,
          f"ΑΡΝΗΤΙΚΟ: χωρίς το st_redraw του mth_struct η πίστα δεν έχει σήμα "
          f"στην οθόνη, ενώ στην πλήρη σχεδίαση έχει — {bad} λάθος bytes")

    # --- ΑΡΝΗΤΙΚΟ: χωρίς τα tiles του μισού πλάτους (βήμα 96) ---------------
    # Ετσι ήταν η πρώτη εκδοχή του 96, και η δοκιμή βρήκε 32 bytes.
    h = shower(sym, g, no_half=True)
    bad = sum(1 for i, (a, b) in enumerate(zip(h["pic"], h["ref"]))
              if a != b and i != h["spot"])
    check(bad > 0,
          f"ΑΡΝΗΤΙΚΟ: χωρίς τη σφραγίδα του μισού πλάτους (cr_stampx = cr_stamp) "
          f"ο κρατήρας σβήνει τη λωρίδα του διαδρόμου στο κέντρο — {bad} λάθος "
          f"bytes (σπόρος {h['seed']}, κρατήρες {h['craters']})")

    frequency()
    return 1 if FAIL else 0


def frequency():
    """Η ζαριά, στην αναφορά. ΣΥΧΝΟΤΗΤΑ: 200 sols της ίδιας γεννήτριας με
    τρεις τιμές ανά γύρο. ΣΥΜΠΤΩΣΗ: εξαντλητικά — οι τιμές που ρίχνουν βροχή
    είναι μόλις 16 (#FFF0-#FFFF), και οι r2, r3 που τις ακολουθούν είναι
    καθορισμένες· ο Galois ολισθαίνει, και ο ίδιος κίνδυνος έριχνε κάποτε
    θύελλα και βλάβη πάντα μαζί."""
    x, n = 1, 0
    for _ in range(200 * 12000 // 16):
        x = EC.lfsr(x)
        n += x >> 4 == 0xFFF
        x = EC.lfsr(EC.lfsr(x))
    clash = []
    for r1 in range(0xFFF0, 0x10000):
        r2 = EC.lfsr(r1)
        r3 = EC.lfsr(r2)
        # Οι ζαριές του βήματος 124: θύελλα r2 >= #FFE0, έκλαμψη r3 >= #FFC0
        # (ως τότε τα μικρά r2 και r3), βλάβη, επισκέπτης.
        if (r2 >= 0xFFE0 or (r3 & 0x7F) == 0 or (r2 & 0x7FF) == 0
                or r3 >= 0xFFC0):
            clash.append(hex(r1))
    check(25 <= n <= 50 and not clash,
          f"συχνότητα: {n} βροχές σε 200 sols (μία ανά {200 / max(n, 1):.1f}), "
          f"και από τις 16 τιμές που τη ρίχνουν {len(clash)} φέρνουν στον ίδιο "
          f"γύρο θύελλα, βλάβη, έκλαμψη ή επισκέπτη {clash}")


if __name__ == "__main__":
    sys.exit(main())
