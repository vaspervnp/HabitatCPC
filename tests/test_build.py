#!/usr/bin/env python3
"""Το build mode: κέρσορας, φάντασμα, έλεγχος, τοποθέτηση (DESIGN §6.9, §9.3).

Τέσσερις ισχυρισμοί:

  1. Ο κέρσορας κινείται και η κάμερα τον ακολουθεί στο χείλος, σκρολάροντας.
  2. Το φάντασμα ΔΕΝ ΑΦΗΝΕΙ ΙΧΝΟΣ: μετά από δέκα κινήσεις και μια απόκρυψη, η
     μνήμη οθόνης πρέπει να είναι ταυτόσημη με πλήρη σχεδίαση. Το αρχείο
     αναίρεσης είναι ο μόνος λόγος που ο κέρσορας δεν κοστίζει επανασχεδίαση,
     και ένα λάθος εκεί αφήνει σκουπίδια που δεν φεύγουν ποτέ.
  3. Ο έλεγχος θέσης λέει όχι πάνω σε θόλο και ναι σε ανοιχτό έδαφος.
  4. Η τοποθέτηση γράφει εγγραφή, σφραγίζει τα tiles, δημοσιεύει εργασία Build
     και πληρώνει.
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/vasilhs/cpcemu")

from sprites import load_map, load_bin                                  # noqa: E402

RASM = os.path.expanduser("~/rasm/rasm.exe")
SNA = os.path.join(ROOT, "build", "uitest.sna")
UI_LOOK, UI_MENU, UI_PLACE = 0, 1, 2


def build():
    for tool in ("mkoffsets.py", "pack.py", "mkcolony.py"):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", tool)],
                           capture_output=True, text=True)
        if r.returncode:
            sys.exit(f"{tool} απέτυχε:\n{r.stdout}{r.stderr}")
    r = subprocess.run([RASM, "uitest.asm", "-oi", SNA, "-v2", "-s", "-eo"],
                       cwd=HERE, capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(SNA):
        sys.exit("rasm απέτυχε:\n" + r.stdout + r.stderr)
    sym = {}
    for line in open(os.path.join(HERE, "rasmoutput.sym"), encoding="utf-8",
                     errors="replace"):
        p = line.split()
        if len(p) >= 2 and p[1].startswith("#"):
            sym[p[0].upper()] = int(p[1][1:], 16)
    g = None
    for line in open(os.path.join(ROOT, "build", "layout.asm"), encoding="utf-8"):
        if line.startswith("G_econ_state"):
            g = int(line.split("#")[1].strip(), 16)
    return sym, g


def sb(v):
    return v - 256 if v > 127 else v


def main():
    sym, g = build()
    from cpc import CPC, KEY_SPACE, KEY_RIGHT, KEY_LEFT, KEY_UP, KEY_DOWN, KEY_ESC
    smap, blob = load_map(), load_bin()
    f = smap["font_gfx"]
    font = blob[f.off:f.off + f.size]
    glyph = {bytes(font[i * 16:(i + 1) * 16]): chr(32 + i) for i in range(96)}

    def boot():
        m = CPC()
        m.run_frames(60)
        assert m.quickload(SNA), "quickload απέτυχε"
        n = 0
        while m.peek(sym["READY_FLAG"]) != 0x5A and n < 900:
            m.run_frames(1)
            n += 1
        assert m.peek(sym["READY_FLAG"]) == 0x5A, "δεν ξεκίνησε"
        # υλικά: χωρίς αυτά το FIRE δεν χτίζει τίποτα και ο έλεγχος δεν ελέγχει
        for idx, v in ((3, 400), (4, 400)):
            m.poke(g + idx * 2, v & 0xFF)
            m.poke(g + idx * 2 + 1, v >> 8)
        return m

    def tap(m, key, times=1):
        for _ in range(times):
            m.key_down(key)
            m.run_frames(3)
            m.key_up(key)
            m.run_frames(3)

    def hud(m, row):
        off = m.peek(sym["CAM_OFF"]) | (m.peek(sym["CAM_OFF"] + 1) << 8)
        ram = m.read_ram(0xC000, 0x4000)

        def byte(x, y):
            hi = (y & 7) * 0x800
            base = (y >> 3) * 80
            return ram[hi + ((base + x + 2 * off) & 0x7FF)]
        out = ""
        for c in range(40):
            cell = bytes(byte(c * 2 + k, 160 + row * 8 + l)
                         for l in range(8) for k in range(2))
            out += glyph.get(cell, "#")
        return out

    def play(m):
        """Η περιοχή παιχνιδιού, ως γραμμικά bytes."""
        off = m.peek(sym["CAM_OFF"]) | (m.peek(sym["CAM_OFF"] + 1) << 8)
        ram = m.read_ram(0xC000, 0x4000)
        out = bytearray()
        for y in range(160):
            hi = (y & 7) * 0x800
            base = (y >> 3) * 80
            for x in range(80):
                out.append(ram[hi + ((base + x + 2 * off) & 0x7FF)])
        return bytes(out)

    fails = 0

    def entry(mm, name, limit=400):
        mm.poke(sym["DONE_FLAG"], 0)
        mm.set_pc(sym[name])
        k = 0
        while mm.peek(sym["DONE_FLAG"]) != 0x5A and k < limit:
            mm.run_frames(1)
            k += 1
        assert mm.peek(sym["DONE_FLAG"]) == 0x5A, f"{name} δεν τερμάτισε"

    def goto(mm, hx, hy, state=0):
        mm.poke(sym["GOTO_X"], hx & 0xFF)
        mm.poke(sym["GOTO_Y"], hy & 0xFF)
        mm.poke(sym["GOTO_ST"], state)
        entry(mm, "DO_GOTO")
        mm.set_pc(sym["LOOP"])
        mm.run_frames(4)

    # --- 1. κέρσορας και κάμερα -----------------------------------------
    # Η κίνηση διαβάζει ΣΤΑΘΜΗ: κρατημένο πλήκτρο = ένα tile ανά κύκλο, και ο
    # κύκλος κρατά 3 ως 9 frames όταν σκρολάρει. Ο έλεγχος είναι ακριβώς αυτό.
    m = boot()
    cam0 = sb(m.peek(sym["CAM_TX"]))
    t0 = m.peek(sym["TICK_N"])
    m.key_down(KEY_RIGHT)
    m.run_frames(60)
    t1 = m.peek(sym["TICK_N"])
    m.key_up(KEY_RIGHT)
    m.run_frames(20)
    cur = sb(m.peek(sym["CUR_HX"]))
    cam1 = sb(m.peek(sym["CAM_TX"]))
    ticks = (t1 - t0) & 0xFF
    moves = cur // 2
    if not (ticks - 2 <= moves <= ticks + 1):
        print(f"ΑΠΟΤΥΧΙΑ κέρσορας: {ticks} κύκλοι κρατημένου πλήκτρου -> "
              f"{moves} βήματα")
        fails += 1
    elif cam1 <= cam0:
        print(f"ΑΠΟΤΥΧΙΑ κάμερα: δεν ακολούθησε ({cam0} -> {cam1})")
        fails += 1
    elif cur % 2:
        print(f"ΑΠΟΤΥΧΙΑ: ο κέρσορας έχασε την ισοτιμία (cur_hx={cur})")
        fails += 1
    else:
        print(f"OK κέρσορας: {moves} tiles σε {ticks} κύκλους, "
              f"η κάμερα ακολούθησε {cam0} -> {cam1}")

    # --- 1β. οι σειρές 3-4 ΜΕΤΑ το σκρολάρισμα ---------------------------
    # Σημαδεύουμε ΠΡΩΤΑ τη μνήμη των σειρών 3-4 και μετά σκρολάρουμε ένα tile:
    # ό,τι δεν ξαναγράψει ο πίνακας μένει #AA και βγαίνει «#» στην ανάγνωση.
    # Χωρίς το σημάδι η δοκιμή δεν έχει δόντια — στο uitest η μνήμη εκεί είναι
    # ήδη μαύρη, οπότε μια παράλειψη φαίνεται σωστή.
    def mark_hud(mm, rows=(3, 4), val=0xAA):
        off = mm.peek(sym["CAM_OFF"]) | (mm.peek(sym["CAM_OFF"] + 1) << 8)
        for row in rows:
            for y in range(160 + row * 8, 168 + row * 8):
                hi = (y & 7) * 0x800
                base = (y >> 3) * 80
                # 88 και όχι 80: μετά το βήμα το παράθυρο του HUD μετακινείται
                # τέσσερα bytes μέσα στο δαχτυλίδι, και τα θέλουμε σημαδεμένα.
                for x in range(88):
                    mm.poke(0xC000 + hi + ((base + x + 2 * off) & 0x7FF), val)

    # και το βήμα πρέπει να είναι ΒΗΜΑ ΚΑΜΕΡΑΣ: αν ο κέρσορας κουνηθεί μέσα στο
    # κάδρο, ο πίνακας σωστά δεν ξαναγράφεται και η δοκιμή θα έλεγε ψέματα.
    mark_hud(m)
    cam_a = sb(m.peek(sym["CAM_TX"]))
    m.key_down(KEY_RIGHT)
    for _ in range(60):
        m.run_frames(1)
        if sb(m.peek(sym["CAM_TX"])) != cam_a:
            break
    m.key_up(KEY_RIGHT)
    m.run_frames(12)
    cam_b = sb(m.peek(sym["CAM_TX"]))
    assert cam_b != cam_a, "η κάμερα δεν κουνήθηκε — η δοκιμή δεν δοκιμάζει"

    # Το HUD ζει μέσα στο ίδιο δαχτυλίδι με το κάδρο: ένα βήμα κάμερας δεν το
    # κουνάει στην οθόνη αλλά αλλάζει τα bytes του, οπότε οι σειρές 3-4
    # δείχνουν έδαφος ώσπου να τις ξαναγράψει ο πίνακας. Απο το βήμα 19 ο
    # πίνακας τις κρατά μόνος του και ξαναγράφει ΜΟΝΟ όταν αλλάζει η υπογραφή
    # του — και η υπογραφή δεν ήξερε από κάμερα: δεκαεπτά tiles αργότερα ο
    # πίνακας ήταν ΕΔΑΦΟΣ και δεν επρόκειτο να ξαναγραφεί ποτέ. Φάνηκε σε
    # screenshot, όχι σε δοκιμή· αυτή εδώ είναι η δοκιμή.
    #
    # Η σύγκριση είναι με ΟΛΟΚΛΗΡΕΣ τις σαράντα στήλες, γιατί το ίδιο
    # screenshot έδειξε και το δεύτερο: το uip_row4 καθάριζε 40-24 στήλες για
    # κείμενο 20 χαρακτήρων, κι έμεναν τέσσερις με ό,τι βρισκόταν από κάτω.
    want = {3: "LOOK  SPACE=BUILD  " + " " * 16 + "  x1 ",
            4: "FIRE=PLACE ESC=BACK " + " " * 20}
    for row, w in want.items():
        got = hud(m, row)
        if got != w:
            print(f"ΑΠΟΤΥΧΙΑ σειρά {row} μετά το σκρολάρισμα:")
            print(f"   βρήκα   |{got}|")
            print(f"   περίμενα|{w}|")
            fails += 1
        else:
            print(f"OK σειρά {row} μετά από {moves} tiles: |{got.rstrip()}|")

    # --- 2. το φάντασμα δεν αφήνει ίχνος --------------------------------
    m2 = boot()
    tap(m2, KEY_RIGHT, 3)
    tap(m2, KEY_DOWN, 2)
    entry(m2, "DO_HIDE")
    dirty = play(m2)
    entry(m2, "DO_REDRAW")
    clean = play(m2)
    if dirty != clean:
        n = sum(1 for a, b2 in zip(dirty, clean) if a != b2)
        print(f"ΑΠΟΤΥΧΙΑ φάντασμα: {n} bytes έμειναν πίσω μετά την αναίρεση")
        fails += 1
    else:
        print("OK το φάντασμα σβήνει χωρίς ίχνος (ταυτόσημο με πλήρη σχεδίαση)")

    # --- 3. μενού και έλεγχος θέσης -------------------------------------
    m3 = boot()
    tap(m3, KEY_SPACE)
    if m3.peek(sym["UI_STATE"]) != UI_MENU:
        print("ΑΠΟΤΥΧΙΑ: το SPACE δεν άνοιξε το μενού")
        fails += 1
    # Ο ΘΟΛΟΣ ΔΕΝ ΕΧΕΙ ΟΝΟΜΑ, ΕΧΕΙ ΔΩΜΑΤΙΟ (§6.1). Ο κατάλογος δείχνει το
    # δωμάτιο και το μέγεθος ως γράμμα: «OXYGEN     S».
    row3 = hud(m3, 3)
    if "OXYGEN" not in row3 or " S " not in row3:
        print(f"ΑΠΟΤΥΧΙΑ μενού: σειρά 3 = |{row3}|")
        fails += 1
    else:
        print(f"OK μενού: |{row3.rstrip()}|")
    row4 = hud(m3, 4)
    if "UP/DN=ROOM" not in row4:
        print(f"ΑΠΟΤΥΧΙΑ: η σειρά 4 δεν λέει για το δωμάτιο: |{row4}|")
        fails += 1
    else:
        print(f"OK η σειρά 4 λέει πώς: |{row4.rstrip()}|")
    tap(m3, KEY_DOWN)                   # -> CANTEEN
    m3.run_frames(20)                   # ο πίνακας γράφεται στο ρολόι του HUD
    if "CANTEEN" not in hud(m3, 3):
        print(f"ΑΠΟΤΥΧΙΑ: το κάτω δεν άλλαξε δωμάτιο: |{hud(m3, 3)}|")
        fails += 1
    else:
        print("OK το κάτω βελάκι αλλάζει δωμάτιο: CANTEEN")
    tap(m3, KEY_RIGHT, 2)               # -> DOME L
    m3.run_frames(20)
    if m3.peek(sym["BD_W"]) != 8:
        print(f"ΑΠΟΤΥΧΙΑ: δύο δεξιά -> πλάτος {m3.peek(sym['BD_W'])}, περίμενα 8")
        fails += 1
    # Η γεννήτρια οξυγόνου χωράει ΜΟΝΟ σε μικρό θόλο (machine_rules bit0), άρα
    # το δωμάτιο έπρεπε να αλλάξει μόνο του όταν μεγάλωσε ο θόλος.
    if "OXYGEN" in hud(m3, 3):
        print(f"ΑΠΟΤΥΧΙΑ: οξυγόνο σε μεγάλο θόλο: |{hud(m3, 3)}|")
        fails += 1
    else:
        print(f"OK ο μεγάλος θόλος δεν δέχεται οξυγόνο: |{hud(m3, 3).rstrip()}|")
    # Η ΕΠΙΛΟΓΗ ΕΙΝΑΙ ΚΟΛΛΗΜΕΝΗ, ΟΧΙ ΜΝΗΜΟΝΙΚΗ: γυρίζοντας σε μικρό θόλο το
    # δωμάτιο μένει αυτό που βρέθηκε, και το οξυγόνο θέλει ένα πάτημα πάνω.
    tap(m3, KEY_LEFT, 2)
    m3.run_frames(20)
    if "CANTEEN" not in hud(m3, 3):
        print(f"ΑΠΟΤΥΧΙΑ: το δωμάτιο δεν κράτησε: |{hud(m3, 3)}|")
        fails += 1
    tap(m3, KEY_UP)
    m3.run_frames(20)
    if "OXYGEN" not in hud(m3, 3):
        print(f"ΑΠΟΤΥΧΙΑ: το πάνω δεν γύρισε στο οξυγόνο: |{hud(m3, 3)}|")
        fails += 1
    else:
        print("OK και το πάνω βελάκι γυρίζει πίσω: OXYGEN")
    tap(m3, KEY_RIGHT, 2)               # -> DOME L για τη συνέχεια
    m3.run_frames(20)
    m3.key_down("\x01")                 # COPY δεν στέλνεται· το FIRE έρχεται
    m3.key_up("\x01")                   # από το joystick παρακάτω
    m3.set_joystick_type(1)
    m3.run_frames(2)
    m3.joystick(0x10)
    m3.run_frames(4)
    m3.joystick(0)
    m3.run_frames(4)
    if m3.peek(sym["UI_STATE"]) != UI_PLACE:
        print(f"ΑΠΟΤΥΧΙΑ: το FIRE δεν πέρασε σε PLACE "
              f"(κατάσταση {m3.peek(sym['UI_STATE'])})")
        fails += 1
        return 1
    bad_here = m3.peek(sym["UI_BAD"])
    if bad_here == 0:
        print("ΑΠΟΤΥΧΙΑ: το κέντρο της αποικίας θα έπρεπε να φράζει")
        fails += 1
    else:
        print(f"OK ο έλεγχος λέει όχι πάνω στην αποικία: {bad_here} άκυρα tiles")

    # --- 4. τοποθέτηση σε καθαρό έδαφος ---------------------------------
    import mkcolony, world as W
    colony_, agents_, plane = mkcolony.build()

    def clear_spot(w, h):
        """Μια θέση w x h tiles που περνά τον έλεγχο του §6.9."""
        for ty in range(4, 40):
            for tx in range(4, 40):
                ok = True
                for y in range(ty, ty + h):
                    for x in range(tx, tx + w):
                        b = plane.get(x, y)
                        if (b >> 4) & 3 or W.cls_of(b) not in (0, 1, 7):
                            ok = False
                            break
                    if not ok:
                        break
                if ok:
                    return tx, ty
        return None

    spot = clear_spot(4, 4)
    assert spot, "δεν βρέθηκε καθαρή θέση στον δοκιμαστικό κόσμο"
    tx, ty = spot
    m4 = boot()
    tap(m4, KEY_SPACE)                  # -> MENU, είδος 0 = DOME S
    m4.set_joystick_type(1)
    m4.run_frames(2)
    m4.joystick(0x10)
    m4.run_frames(4)
    m4.joystick(0)
    m4.run_frames(6)
    goto(m4, 2 * tx + 4, 2 * ty + 4, 2)
    bad = m4.peek(sym["UI_BAD"])
    if bad:
        print(f"ΑΠΟΤΥΧΙΑ: καθαρή θέση ({tx},{ty}) αλλά {bad} άκυρα tiles")
        fails += 1
        return 1
    print(f"OK καθαρή θέση ({tx},{ty}): ο έλεγχος λέει ναι")
    if "READY" not in hud(m4, 4):
        print(f"ΑΠΟΤΥΧΙΑ πίνακας: |{hud(m4, 4)}|")
        fails += 1

    fe0 = m4.peek(g + 6) | (m4.peek(g + 7) << 8)
    m4.joystick(0x10)
    m4.run_frames(6)
    m4.joystick(0)
    m4.run_frames(60)

    def snoop(mm, bank, addr, n):
        mm.poke(sym["SNOOP_BK"], bank)
        mm.poke(sym["SNOOP_AD"], addr & 0xFF)
        mm.poke(sym["SNOOP_AD"] + 1, addr >> 8)
        mm.poke(sym["SNOOP_N"], n)
        entry(mm, "DO_SNOOP")
        out = [mm.peek(sym["SNOOP_BUF"] + i) for i in range(n)]
        mm.set_pc(sym["LOOP"])
        mm.run_frames(2)
        return out

    node = m4.peek(sym["BD_NODE"])
    if node == 255:
        print("ΑΠΟΤΥΧΙΑ: το FIRE δεν τοποθέτησε τίποτα")
        return 1
    dome_tbl = None
    for line in open(os.path.join(ROOT, "build", "layout.asm"), encoding="utf-8"):
        if line.startswith("G_dome_tbl"):
            dome_tbl = int(line.split("#")[1].strip(), 16)
    # R_OXYGEN = 4: ο μικρός θόλος του καταλόγου ξεκινά στο πρώτο δωμάτιο.
    rec = snoop(m4, 0xC6, dome_tbl + node * 24, 24)
    want = [(2 * tx + 4) & 0xFF, (2 * ty + 4) & 0xFF, 0, 4, 1]
    if rec[:5] != want:
        print(f"ΑΠΟΤΥΧΙΑ εγγραφή θόλου {node}: {rec[:5]}, περίμενα {want}")
        fails += 1
    else:
        print(f"OK ο θόλος {node} μπήκε ως DS_BUILDING στο ({tx},{ty}), "
              f"δωμάτιο οξυγόνου")
    # ΚΑΙ ΜΕ ΤΟ ΜΗΧΑΝΗΜΑ ΜΕΣΑ. Η υποδοχή 0 παίρνει mach_oxygen (0) με υγεία
    # 200· οι υπόλοιπες επτά μένουν NO_MACH, γιατί ο μικρός θόλος έχει μία.
    if rec[8] != 0 or rec[16] != 200 or rec[9] != 255:
        print(f"ΑΠΟΤΥΧΙΑ εξοπλισμός: υποδοχές {rec[8:12]}, υγείες {rec[16:20]}")
        fails += 1
    else:
        print("OK και το μηχάνημα μέσα: υποδοχή 0 = mach_oxygen, υγεία 200")

    w = snoop(m4, 0xC4, 0x4000 + ((ty + 64) << 7) + (tx + 64), 4)
    if any((b & 7) != 7 or not (b & 0x30) for b in w):
        print(f"ΑΠΟΤΥΧΙΑ θεμέλια: τα tiles είναι {[hex(b) for b in w]}")
        fails += 1
    else:
        print("OK τα tiles έγιναν θεμέλιο και δεσμευμένα")

    job_tbl = None
    for line in open(os.path.join(ROOT, "build", "layout.asm"), encoding="utf-8"):
        if line.startswith("G_job_tbl"):
            job_tbl = int(line.split("#")[1].strip(), 16)
    jobs = [(m4.peek(job_tbl + j * 5), m4.peek(job_tbl + j * 5 + 1))
            for j in range(32)]
    if (0, node) not in jobs:
        print(f"ΑΠΟΤΥΧΙΑ: καμία εργασία Build για τον κόμβο {node}")
        fails += 1
    else:
        print(f"OK δημοσιεύτηκε εργασία Build στον κόμβο {node} — το πρώτο "
              f"είδος που δέχονται τα ρομπότ")

    fe1 = m4.peek(g + 6) | (m4.peek(g + 7) << 8)
    if fe1 != fe0 - 20:
        print(f"ΑΠΟΤΥΧΙΑ κόστος: μέταλλο {fe0} -> {fe1}, περίμενα -20")
        fails += 1
    else:
        print(f"OK πληρώθηκε: μέταλλο {fe0} -> {fe1}")

    bad2 = m4.peek(sym["UI_BAD"])
    if bad2 == 0:
        print("ΑΠΟΤΥΧΙΑ: η ίδια θέση δείχνει ακόμη ελεύθερη μετά το χτίσιμο")
        fails += 1
    else:
        print(f"OK η θέση δεν ξαναχτίζεται: {bad2} άκυρα tiles")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
