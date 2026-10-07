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

from sprites import load_map, load_bin
import hudread                                  # noqa: E402

RASM = os.path.expanduser("~/rasm/rasm.exe")
SNA = os.path.join(ROOT, "build", "uitest.sna")
UI_LOOK, UI_MENU, UI_PLACE = 0, 1, 2
BLD_N = 11                              # src/build.asm: τα είδη του καταλόγου


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


# --- τα δωμάτια απέναντι σε μοντέλο (βήμα 60) --------------------------------
# Από την πρόζα του §6.5: τι δέχεται το δωμάτιο (room_machines), τι χωράει στο
# μέγεθος (machine_rules), η κύρια μηχανή πρώτη (rm_pref), το θερμοκήπιο με τη
# σειρά των κλάσεων (rm_plants). Και ο κατάλογος: πάνω-κάτω πηγαίνει στο
# επόμενο δωμάτιο που ΧΩΡΑΕΙ, κυκλικά.
R_GREENHS_ = 5
RM_LIST = [4, 3, 2, 5, 8, 9, 10, 1, 6, 11]       # οξυγόνο, καντίνα, ... σαλόνι
RM_PREF = {8: 1, 9: 9, 10: 10}                    # εργοστάσιο, εργαστήριο, ιατρείο
RM_PLANTS = [0, 5, 10, 11, 1, 6, 2, 7, 3, 8, 4, 9]


def rooms_model(rmach, rules, room, size):
    """(λίστα, CY): CY αν το δωμάτιο θέλει μηχανήματα και κανένα δεν χωρά."""
    if room == R_GREENHS_:
        return list(RM_PLANTS), False
    mask = rmach[2 * room] | rmach[2 * room + 1] << 8
    if not mask:
        return [], False
    got = [c for c in range(12) if mask >> c & 1 and rules[c] >> size & 1]
    if not got:
        return [], True
    p = RM_PREF.get(room)
    if p in got:
        got.remove(p)
        got.insert(0, p)
    return got, False


def rooms_step(rmach, rules, sel, d, size):
    fits = lambda k: not rooms_model(rmach, rules, RM_LIST[k], size)[1]
    for _ in range(len(RM_LIST)):
        sel = (sel + d) % len(RM_LIST)
        if fits(sel):
            break
    return sel


def rooms_check(sym, patch=(), n=24):
    """rm_build για κάθε δωμάτιο και μέγεθος, rm_step από κάθε θέση και προς τις
    δύο μεριές, rm_fix για θόλο και για δομή — με τους πραγματικούς πίνακες και
    με n τυχαίους, ώστε η κύρια μηχανή να πέφτει σε κάθε θέση της λίστας. Η
    πρώτη διαφορά, ή None."""
    from cpc import CPC
    import random
    m = CPC()
    m.run_frames(60)
    assert m.quickload(SNA, start=False), "quickload απέτυχε"
    for at, v in patch:
        m.poke(at, v)
    def layout_addr(name):
        for line in open(os.path.join(ROOT, "build", "layout.asm"), encoding="utf-8"):
            if line.split()[:1] == [name]:
                return int(line.split("#")[1].split()[0], 16)
    rm_at, mr_at = layout_addr("G_room_machines"), layout_addr("G_machine_rules")
    real = (m.read_ram(rm_at, 24), m.read_ram(mr_at, 12))
    rnd = random.Random(60)
    tables = [real] + [(bytes(b for _ in range(12) for b in (
        lambda x: (x & 255, x >> 8))(rnd.choice([0, rnd.randrange(4096),
                                                rnd.randrange(4096) | 0x602]))),
        bytes(rnd.randrange(8) for _ in range(12))) for _ in range(n)]

    def call(code):
        """BC, DE, HL φορτωμένα #1234, #5678, #9ABC πριν από την κλήση· μετά
        γράφονται, μαζί με το AF, στο #3FF1.. — το fit_enter θέλει το rm_build
        να τα κρατά."""
        m.poke(0x3FF0, 0)
        m.run_code(0x3F00, bytes([0xF3, 0x31, 0x00, 0x01] + code[:-3] +
                                 [0x01, 0x34, 0x12, 0x11, 0x78, 0x56, 0x21, 0xBC, 0x9A] +
                                 code[-3:] +
                                 [0xF5, 0xED, 0x43, 0xF3, 0x3F, 0xED, 0x53, 0xF5, 0x3F,
                                  0x22, 0xF7, 0x3F, 0xE1, 0x22, 0xF1, 0x3F,   # AF -> #3FF1
                                  0x3E, 0x5A, 0x32, 0xF0, 0x3F, 0x18, 0xFE]), frames=1)
        assert m.peek(0x3FF0) == 0x5A, f"δεν γύρισε: #{m.pc:04X}"
        return m.peek(0x3FF2), m.peek(0x3FF1)               # A, F
    regs = lambda: list(m.read_ram(0x3FF3, 6))
    fn = lambda name: [0xCD, sym[name] & 255, sym[name] >> 8]
    for ti, (rmach, rules) in enumerate(tables):
        m.write_ram(rm_at, rmach)
        m.write_ram(mr_at, rules)
        for size in range(3):
            m.poke(sym["BD_PARAM"], size)
            for room in range(12):
                a, f = call([0x3E, room] + fn("RM_BUILD"))
                got = (list(m.read_ram(sym["RM_BUF"], a)), bool(f & 1))
                want = rooms_model(rmach, rules, room, size)
                if got != want or m.peek(sym["RM_NBUF"]) != a:
                    return (f"πίνακες {ti}, δωμάτιο {room}, μέγεθος {size}: "
                            f"Z80 {got}, μοντέλο {want}")
                if regs() != [0x34, 0x12, 0x78, 0x56, 0xBC, 0x9A]:
                    return (f"πίνακες {ti}, δωμάτιο {room}: το rm_build δεν κράτησε τα "
                            f"BC, DE, HL — {[hex(x) for x in regs()]}")
            for sel in range(len(RM_LIST)):
                for d in (1, 255):
                    m.poke(sym["BD_RSEL"], sel)
                    call([0x3E, d] + fn("RM_STEP"))
                    want = rooms_step(rmach, rules, sel, 1 if d == 1 else -1, size)
                    if m.peek(sym["BD_RSEL"]) != want:
                        return (f"πίνακες {ti}, rm_step από {sel} προς {d}, μέγεθος "
                                f"{size}: {m.peek(sym['BD_RSEL'])}, μοντέλο {want}")
                for kind in (0, 1):
                    m.poke(sym["BD_RSEL"], sel)
                    m.poke(sym["BD_KIND"], kind)
                    call(fn("RM_FIX"))
                    fits = not rooms_model(rmach, rules, RM_LIST[sel], size)[1]
                    want = sel if kind or fits else rooms_step(rmach, rules, sel, 1, size)
                    m.poke(sym["BD_KIND"], 0)
                    if m.peek(sym["BD_RSEL"]) != want:
                        return (f"πίνακες {ti}, rm_fix από {sel}, είδος {kind}, μέγεθος "
                                f"{size}: {m.peek(sym['BD_RSEL'])}, μοντέλο {want}")
    return None


def main():
    sym, g = build()
    from cpc import CPC, KEY_SPACE, KEY_RIGHT, KEY_LEFT, KEY_UP, KEY_DOWN, KEY_ESC
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
        return hudread.text(m, sym, row)

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
    m.key_up(KEY_RIGHT)
    # Ο emulator βγάζει το πλήκτρο από τη μήτρα στο ΤΕΛΟΣ του επόμενου frame:
    # το kbd_key_up των chips μόνο το σημαδεύει, και το σβήνει το kbd_update που
    # τρέχει μετά τους κύκλους του frame (chips/kbd.h, systems/cpc.h). Για ένα
    # frame ακόμη λοιπόν ο βρόχος το διαβάζει πατημένο, και οι κύκλοι μετριούνται
    # ως εκεί. Φάνηκε στο βήμα 52: το HUD έγινε γρηγορότερο, ένας κύκλος άρχισε
    # να πέφτει μέσα σε εκείνο το frame, και τα βήματα βγήκαν κύκλοι + 2.
    m.run_frames(1)
    t1 = m.peek(sym["TICK_N"])
    m.run_frames(19)
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
    # Από το βήμα 83 ένα βήμα κάμερας ΜΕΤΑΚΙΝΕΙ τις λωρίδες του HUD μαζί με το
    # δαχτυλίδι (hud_move) και ο πίνακας δεν ξαναγράφεται. Αν η μετακίνηση
    # λείπει, οι σειρές διαβάζονται τέσσερα bytes μετατοπισμένες — τέσσερις
    # στήλες — και η σύγκριση των σαράντα στηλών το πιάνει. (Ως το βήμα 82
    # σημαδεύαμε εδώ τη μνήμη, για να φανεί ότι ο πίνακας ξαναγράφτηκε.)
    #
    # και το βήμα πρέπει να είναι ΒΗΜΑ ΚΑΜΕΡΑΣ: αν ο κέρσορας κουνηθεί μέσα στο
    # κάδρο, τίποτα δεν μετακινείται και η δοκιμή θα έλεγε ψέματα.
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
    # κουνάει στην οθόνη αλλά αλλάζει τη θέση των bytes του. Στο βήμα 19 ο
    # πίνακας δεν το ήξερε: δεκαεπτά tiles αργότερα ήταν ΕΔΑΦΟΣ και δεν
    # επρόκειτο να ξαναγραφεί ποτέ. Φάνηκε σε screenshot, όχι σε δοκιμή· αυτή
    # εδώ είναι η δοκιμή.
    #
    # Η σύγκριση είναι με ΟΛΟΚΛΗΡΕΣ τις σαράντα στήλες, γιατί το ίδιο
    # screenshot έδειξε και το δεύτερο: το uip_row4 καθάριζε 40-24 στήλες για
    # κείμενο 20 χαρακτήρων, κι έμεναν τέσσερις με ό,τι βρισκόταν από κάτω.
    # Βήμα 45: το FIRE στο LOOK ανοίγει τον εξοπλισμό (src/fit.asm), και το
    # λέει η σειρά 3· η σειρά 4 έλεγε «FIRE=PLACE», που στο LOOK ήταν ψέμα.
    want = {3: "SPACE=MENU I=INFO FIRE=FIT C=SHIP" + "  " + "  x1 ",
            4: " " * 40}
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
    # --- Η ΑΝΑΔΙΠΛΩΣΗ ΤΟΥ ΚΑΤΑΛΟΓΟΥ (ui_lr, βήμα 44) ------------------
    # Αριστερά από το πρώτο πάει στο τελευταίο, δεξιά από το τελευταίο ξανά
    # στο πρώτο. Κανένα άλλο πάτημα εδώ δεν περνά το όριο, και το ui_lr είναι
    # καινούργιο: ένα για τη θέση δίσκου και τον κατάλογο. Σε δικό του
    # μηχάνημα, γιατί το bd_select μετακινεί τον κέρσορα για την ισοτιμία.
    def wrap(patch=None):
        mm = boot()
        if patch:
            at = sym["UI_LR"]
            # ld e,c / dec e: από το βήμα 45 το ui_lr αρχίζει με ld d,A_RIGHT
            # και κοινό σώμα με το ui_ud, και ένα σκέτο 0x1D θα μπορούσε να
            # είναι και byte διεύθυνσης.
            k = next(i for i in range(24)
                     if mm.peek(at + i) == 0x59 and mm.peek(at + i + 1) == 0x1D)
            mm.poke(at + k + 1, 0x00)
        tap(mm, KEY_SPACE)
        tap(mm, KEY_LEFT)
        mm.run_frames(20)
        last, row = mm.peek(sym["UI_SEL"]), hud(mm, 3)
        tap(mm, KEY_RIGHT)
        return last, row, mm.peek(sym["UI_SEL"])
    last, row, back = wrap()
    if last != BLD_N - 1 or "LANDING" not in row or back != 0:
        print(f"ΑΠΟΤΥΧΙΑ αναδίπλωση: αριστερά -> {last} |{row.rstrip()}|, "
              f"δεξιά -> {back}")
        fails += 1
    else:
        print(f"OK ο κατάλογος αναδιπλώνεται: αριστερά από το 0 -> {last} "
              f"(LANDING), δεξιά -> {back}")
    nlast, _, _ = wrap(patch=True)
    if nlast == BLD_N - 1:
        print("ΑΠΟΤΥΧΙΑ: ΑΡΝΗΤΙΚΟ — χωρίς το dec e το αριστερά αναδιπλώνεται ακόμη")
        fails += 1
    else:
        print(f"OK ΑΡΝΗΤΙΚΟ: χωρίς το dec e του ui_lr το αριστερά μένει στο {nlast}")

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
    # ΚΑΙ ΑΔΕΙΟΣ (βήμα 45), όπως στο Planetbase: οι μηχανές μπαίνουν μία-μία
    # από τον εξοπλισμό (src/fit.asm, tests/test_fit.py) και πληρώνονται
    # χωριστά. Ως το βήμα 44 εδώ η υποδοχή 0 έπαιρνε μόνη της mach_oxygen.
    if rec[8:16] != [255] * 8 or rec[16:24] != [0] * 8:
        print(f"ΑΠΟΤΥΧΙΑ: ο θόλος δεν μπήκε άδειος: υποδοχές {rec[8:16]}, "
              f"υγείες {rec[16:24]}")
        fails += 1
    else:
        print("OK ο θόλος μπήκε άδειος: οκτώ NO_MACH, καμία υγεία")

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

    # Το κέλυφος μόνο: 12, όχι 20 — οι μηχανές πληρώνονται στον εξοπλισμό.
    # ΚΑΙ ΟΙ ΔΙΑΔΡΟΜΟΙ ΤΟΥ (βήμα 85): ο θόλος δένεται με κάθε θόλο της
    # αποικίας που φτάνει διάδρομος ως 12 πλακιδίων, 6 μέταλλο το πλακίδιο, με
    # τον κανόνα του tools/reach.py πάνω στον δοκιμαστικό κόσμο.
    import reach
    s_ = load_map()["struct_dims"]
    dims = load_bin()[s_.off:s_.off + s_.size]
    domes = [list(colony_.dome[24 * d:24 * d + 4]) for d in range(64)]
    structs = [list(colony_.struct[8 * k:8 * k + 5]) for k in range(32)]
    res = reach.plan(bytes(plane.buf), domes, structs, dims, 0, 0, 4, 4,
                     2 * tx + 4, 2 * ty + 4)
    cost = 12 + reach.CORR_M * res["pieces"]
    fe1 = m4.peek(g + 6) | (m4.peek(g + 7) << 8)
    if fe1 != fe0 - cost:
        print(f"ΑΠΟΤΥΧΙΑ κόστος: μέταλλο {fe0} -> {fe1}, περίμενα -{cost} "
              f"({len(res['corridors'])} διάδρομοι, {res['pieces']} πλακίδια)")
        fails += 1
    else:
        print(f"OK πληρώθηκε: μέταλλο {fe0} -> {fe1} — το κέλυφος και "
              f"{len(res['corridors'])} διάδρομοι, {res['pieces']} πλακίδια")

    # --- 5. ΠΟΙΑ μηχανήματα, και με ποια ΣΕΙΡΑ (§6.5) --------------------
    # Η σειρά ήταν ως το βήμα 44 η σειρά του αυτόματου γεμίσματος: με την
    # αριθμητική σειρά της room_machines το εργαστήριο έβγαζε επεξεργαστές και
    # ποτέ vitromeat, και το θερμοκήπιο φύτευε μόνο αμυλούχα. Από το βήμα 45
    # είναι η σειρά της λίστας του εξοπλισμού, και η πρώτη μηχανή η
    # προεπιλογή του: η κύρια μηχανή του δωματίου είναι ένα FIRE μακριά.
    def fitout(room, size):
        m4.poke(sym["BD_PARAM"], size)
        m4.run_code(0x3F00, bytes([0x3E, room,
                                   0xCD, sym["RM_BUILD"] & 0xFF,
                                   sym["RM_BUILD"] >> 8, 0x18, 0xFE]), frames=2)
        n = m4.peek(sym["RM_NBUF"])
        return [m4.peek(sym["RM_BUF"] + i) for i in range(n)]

    # plant_class: 0-4 άμυλο, 5-9 λαχανικά, 10 φάρμακα, 11 δέντρο
    green = fitout(5, 1)                 # R_GREENHOUSE
    if green != [0, 5, 10, 11, 1, 6, 2, 7, 3, 8, 4, 9]:
        print(f"ΑΠΟΤΥΧΙΑ θερμοκήπιο: {green}")
        fails += 1
    elif green[:4] == [0, 1, 2, 3]:
        print("ΑΠΟΤΥΧΙΑ: το θερμοκήπιο φυτεύει με την αρίθμηση")
        fails += 1
    else:
        print(f"OK το θερμοκήπιο εναλλάσσει κλάσεις: {green[:4]} = άμυλο, "
              f"λαχανικά, φάρμακα, δέντρο")
    lab = fitout(9, 1)                   # R_LAB
    if not lab or lab[0] != 9:
        print(f"ΑΠΟΤΥΧΙΑ εργαστήριο: {lab}, περίμενα το vitromeat (9) πρώτο")
        fails += 1
    else:
        print(f"OK το εργαστήριο βάζει πρώτο το vitromeat: {lab}")
    fac = fitout(8, 1)                   # R_FACTORY
    if not fac or fac[0] != 1:
        print(f"ΑΠΟΤΥΧΙΑ εργοστάσιο: {fac}, περίμενα το mach_iron (1) πρώτο")
        fails += 1
    else:
        print(f"OK το εργοστάσιο βάζει πρώτο το σίδερο: {fac}")
    # ΚΑΙ ΤΟ ΟΡΙΟ ΜΕΓΕΘΟΥΣ ΜΕΝΕΙ: το mach_oxygen μπαίνει μόνο σε μικρό θόλο.
    if fitout(4, 0) != [0] or fitout(4, 1) != []:
        print(f"ΑΠΟΤΥΧΙΑ οξυγόνο: μικρό {fitout(4, 0)}, μεσαίο {fitout(4, 1)}")
        fails += 1
    else:
        print("OK το οξυγόνο μόνο σε μικρό θόλο, όπως λέει το machine_rules")

    bad2 = m4.peek(sym["UI_BAD"])
    if bad2 == 0:
        print("ΑΠΟΤΥΧΙΑ: η ίδια θέση δείχνει ακόμη ελεύθερη μετά το χτίσιμο")
        fails += 1
    else:
        print(f"OK η θέση δεν ξαναχτίζεται: {bad2} άκυρα tiles")

    # --- 6. τα δωμάτια απέναντι στο μοντέλο (βήμα 60) ----------------------
    why = rooms_check(sym)
    if why:
        print(f"ΑΠΟΤΥΧΙΑ δωμάτια: {why}")
        fails += 1
    else:
        # ΑΡΝΗΤΙΚΟ: 11 γύροι αντί για 12 στο rm_build — η μηχανή 11 χάνεται
        at = sym["RM_BUILD"]
        m5 = CPC()
        m5.run_frames(60)
        assert m5.quickload(SNA, start=False)
        k = next((k for k in range(80) if [m5.peek(at + k + j) for j in range(3)]
                  == [0x01, 0x00, 12]), None)
        if k is None or rooms_check(sym, patch=[(at + k + 2, 11)], n=8) is None:
            print("ΑΠΟΤΥΧΙΑ δωμάτια: ΑΡΝΗΤΙΚΟ — με 11 γύρους στο rm_build το μοντέλο "
                  "δεν διαφωνεί" if k is not None else
                  "ΑΠΟΤΥΧΙΑ δωμάτια: το rm_build δεν ξεκινά με ld bc,RM_MACH * 256")
            fails += 1
        else:
            print("OK δωμάτια: rm_build για κάθε δωμάτιο και μέγεθος (και κρατά τα BC, "
                  "DE, HL), rm_step από κάθε θέση και προς τις δύο μεριές, rm_fix για "
                  "θόλο και δομή — με τους πραγματικούς πίνακες και με 24 τυχαίους, "
                  "ίδια με το μοντέλο. ΑΡΝΗΤΙΚΟ: με 11 γύρους διαφέρουν")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
