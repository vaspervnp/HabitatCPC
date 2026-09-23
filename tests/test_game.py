#!/usr/bin/env python3
"""Το παιχνίδι ολόκληρο, σε ένα binary (DESIGN §10.1, §6.9, §7.2).

Ως το βήμα 12 τα δύο μισά δεν είχαν μπει ποτέ μαζί: το uitest έδενε τον
renderer με το build mode, το simtest την οικονομία με τον τροχό. Αυτή η δοκιμή
τρέχει το src/main.asm — τον ΒΡΟΧΟ — και ελέγχει την αλυσίδα που περνά και από
τα δύο:

  1. Η κατάσταση εκκίνησης του §10.1 είναι εκεί: αποθέματα, τέσσερις άποικοι.
  2. Η προσομοίωση τρέχει μέσα στον βρόχο — το νερό πέφτει μόνο του.
  3. Η ΟΘΟΝΗ το δείχνει χωρίς ο παίκτης να αγγίξει τίποτα. Αυτό είναι που
     έλειπε: το HUD ξαναγραφόταν μόνο σε ενέργεια παίκτη, οπότε το νερό
     πήγαινε 60 -> 0 με τη μπάρα γεμάτη.
  4. Ο παίκτης χτίζει ηλιακό, και το κτίριο ΤΕΛΕΙΩΝΕΙ: κάποιος πάει, δουλεύει,
     η ακεραιότητα φτάνει στο 255, η κατάσταση γίνεται DS_ACTIVE και το ρεύμα
     εμφανίζεται στην οικονομία. Περνά από δρομολόγηση, πίνακα εργασιών,
     κίνηση πράκτορα και σχεδίαση — αν σπάσει οποιοσδήποτε κρίκος, εδώ φαίνεται.
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")

from sprites import load_map, load_bin                                  # noqa: E402

RASM = os.path.expanduser("~/rasm/rasm.exe")
SNA = os.path.join(ROOT, "build", "main.sna")
FAIL = []


def sb(v):
    return v - 256 if v > 127 else v


def check(ok, msg):
    print(("OK " if ok else "ΛΑΘΟΣ ") + msg)
    if not ok:
        FAIL.append(msg)


def build():
    for tool in ("mkoffsets.py", "pack.py", "mknew.py"):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", tool)],
                           capture_output=True, text=True)
        if r.returncode:
            sys.exit(f"{tool} απέτυχε:\n{r.stdout}{r.stderr}")
    r = subprocess.run([RASM, "main.asm", "-oi", SNA, "-v2", "-s", "-eo"],
                       cwd=os.path.join(ROOT, "src"), capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(SNA):
        sys.exit("rasm απέτυχε:\n" + r.stdout + r.stderr)
    sym = {}
    for line in open(os.path.join(ROOT, "src", "rasmoutput.sym"),
                     encoding="utf-8", errors="replace"):
        p = line.split()
        if len(p) >= 2 and p[1].startswith("#"):
            sym[p[0].upper()] = int(p[1][1:], 16)
    g = None
    for line in open(os.path.join(ROOT, "build", "layout.asm"), encoding="utf-8"):
        if line.startswith("G_econ_state"):
            g = int(line.split("#")[1].strip(), 16)
    return sym, g


def main():
    sym, g = build()
    from cpc import CPC, KEY_SPACE, KEY_RIGHT, KEY_LEFT, KEY_UP
    smap, blob = load_map(), load_bin()
    f = smap["font_gfx"]
    font = blob[f.off:f.off + f.size]
    glyph = {bytes(font[i * 16:(i + 1) * 16]): chr(32 + i) for i in range(96)}

    m = CPC()
    m.run_frames(60)
    assert m.quickload(SNA), "quickload απέτυχε"
    m.run_frames(120)                    # το game_new κάνει πλήρη σχεδίαση

    def w16(a):
        return m.peek(a) | (m.peek(a + 1) << 8)

    def hud(row):
        off = m.peek(sym["CAM_OFF"]) | (m.peek(sym["CAM_OFF"] + 1) << 8)
        ram = m.read_ram(0xC000, 0x4000)

        def byte(x, y):
            return ram[(y & 7) * 0x800 + (((y >> 3) * 80 + x + 2 * off) & 0x7FF)]
        return "".join(glyph.get(bytes(byte(c * 2 + k, 160 + row * 8 + l)
                                       for l in range(8) for k in range(2)), "#")
                       for c in range(40))

    def hudrow_bytes(row):
        """Η σειρά του HUD ως ωμά bytes — οι μπάρες δεν είναι γλύφοι."""
        off = m.peek(sym["CAM_OFF"]) | (m.peek(sym["CAM_OFF"] + 1) << 8)
        ram = m.read_ram(0xC000, 0x4000)
        return bytes(ram[(y & 7) * 0x800 +
                         (((y >> 3) * 80 + x + 2 * off) & 0x7FF)]
                     for y in range(160 + row * 8, 160 + row * 8 + 8)
                     for x in range(80))

    # --- 1. η κατάσταση εκκίνησης ----------------------------------------
    stock = [w16(g + i * 2) for i in range(7)]
    # Το νερό έχει ήδη πέσει λίγο: ο βρόχος τρέχει από το πρώτο frame.
    check(55 <= stock[0] <= 60 and stock[1] == 40 and stock[3] == 55
          and stock[4] == 30 and stock[6] == 4 and m.peek(g + 58) == 4,
          f"§10.1: 60 νερό / 40 τροφή / 55 μέταλλο / 30 βιοπλαστικό / "
          f"4 ανταλλακτικά, 4 άποικοι — {stock} {m.peek(g + 58)}")
    row2 = hud(2)
    check(row2.startswith("POP  4/"), f"το HUD ξέρει τον πληθυσμό: |{row2}|")

    # --- 2 & 3. η προσομοίωση τρέχει ΚΑΙ φαίνεται ------------------------
    m.run_frames(2000)
    water = w16(g)
    # ΜΙΚΡΗ ΠΤΩΣΗ, ΚΑΙ ΣΩΣΤΑ: η αποικία του §10.1 δεν έχει ρεύμα, οπότε η
    # μηχανή οξυγόνου πίνει μόνο ως το πρώτο ισοζύγιο (~64 περιστροφές) και
    # μετά σταματά. Οι άποικοι δεν διψούν παρά κατά το πρώτο sol. Ο έλεγχος
    # είναι «κινείται», όχι «πόσο»: με παγωμένη προσομοίωση μένει 58.
    check(water < stock[0], f"το νερό πέφτει μόνο του: {stock[0]} -> {water}")

    # --- 4. χτίσιμο που ΤΕΛΕΙΩΝΕΙ ----------------------------------------
    # Ο κέρσορας πηγαίνει δίπλα στην αποικία χωρίς να περπατήσει: το βήμα
    # κέρσορα είναι δοκιμασμένο αλλού, εδώ μας νοιάζει η αλυσίδα μετά το FIRE.
    # Το (7, 5) σε μισά tiles είναι το κοντινότερο καθαρό 3x3 σε αυτό το seed:
    # έδαφος, χωρίς κατοχή, έξω από την αποικία.
    m.poke(sym["CUR_HX"], 7)
    m.poke(sym["CUR_HY"], 5)

    def tap(key, n=1):
        for _ in range(n):
            m.key_down(key)
            m.run_frames(3)
            m.key_up(key)
            m.run_frames(4)

    def fire():
        m.joystick(0x10)
        m.run_frames(4)
        m.joystick(0)
        m.run_frames(10)

    tap(KEY_SPACE)                       # -> MENU
    tap(KEY_RIGHT, 4)                    # -> SOLAR
    m.key_up("\x01")
    m.set_joystick_type(1)
    check(m.peek(sym["BD_PARAM"]) == 0 and m.peek(sym["BD_KIND"]) == 1,
          f"ο κατάλογος έφτασε στο SOLAR (είδος {m.peek(sym['BD_KIND'])}, "
          f"παράμετρος {m.peek(sym['BD_PARAM'])})")
    fire()                               # -> PLACE
    metal0 = w16(g + 3 * 2)
    fire()                               # -> τοποθέτηση
    metal1 = w16(g + 3 * 2)
    check(metal1 == metal0 - 15,
          f"πληρώθηκε ο ηλιακός: μέταλλο {metal0} -> {metal1}")
    if metal1 != metal0 - 15:
        print(f"    (ui_bad={m.peek(sym['UI_BAD'])} — το έδαφος είπε όχι)")
        return 1

    # Από εδώ και κάτω ο παίκτης ΔΕΝ αγγίζει τίποτα: ό,τι αλλάξει στην οθόνη
    # το έφερε η προσομοίωση.
    alert0 = hud(2)[20:]
    got = 0
    for _ in range(40):                  # ως 40 x 50 frames = ~40 δευτερόλεπτα
        m.run_frames(50)
        if w16(g + 32) > 0:
            got = 1
            break
    check(got, f"το κτίριο τελείωσε και βγάζει ρεύμα: παραγωγή {w16(g + 32)}")
    # Το ρεύμα ήρθε· το οξυγόνο θέλει ακόμη ένα ΣΑΡΩΜΑ παραγωγής για να
    # ξαναδημοσιευτεί (64 περιστροφές, βλ. FLOW_DIV στο src/econ.asm).
    for _ in range(40):
        m.run_frames(50)
        if hud(2)[20:].strip() == "ALL SYSTEMS OK":
            break
    alert1 = hud(2)[20:]
    check(alert0.strip() != alert1.strip()
          and alert1.strip() == "ALL SYSTEMS OK",
          f"το HUD το ΔΕΙΧΝΕΙ χωρίς πάτημα: |{alert0.strip()}| -> "
          f"|{alert1.strip()}|")
    # --- 5. ένας θόλος που ο παίκτης του δίνει δουλειά (§6.1) -------------
    # ΚΑΝΕΝΑΣ ΘΟΛΟΣ ΤΟΥ ΠΑΙΚΤΗ ΔΕΝ ΤΕΛΕΙΩΝΕ ΠΟΤΕ ως το βήμα 26: το bd_link
    # έψαχνε τον κοντινότερο ζωντανό θόλο για να δώσει ακμή στο εργοτάξιο, και
    # ο κοντινότερος ήταν το ΙΔΙΟ το εργοτάξιο — απόσταση μηδέν. Επιστροφή
    # χωρίς ακμή, κόμβος απρόσιτος, εργασία Build για πάντα ανοιχτή. Οι δομές
    # δεν το έδειχναν (παίρνουν κόμβο 64+), και καμία δοκιμή δεν είχε περιμένει
    # θόλο να τελειώσει.
    import world as W
    plane = open(os.path.join(ROOT, "build", "world_new.bin"), "rb").read()
    ok = {W.GROUND, W.DUST, W.FOUNDATION}
    at = None
    for r in range(6, 16):
        for ty in range(-r, r + 1):
            for tx in range(-r, r + 1):
                if at or max(abs(tx), abs(ty)) != r:
                    continue
                if all(W.cls_of(plane[W.index(tx + i, ty + j)]) in ok
                       for i in range(4) for j in range(4)):
                    at = (2 * tx + 4, 2 * ty + 4)
    m.set_joystick_type(1)
    for _ in range(2):                   # πίσω στην ήρεμη κατάσταση
        m.joystick(0x20)
        m.run_frames(4)
        m.joystick(0)
        m.run_frames(10)
    m.set_joystick_type(0)
    tap(KEY_SPACE)                       # -> MENU· θυμάται πού έμεινε (SOLAR)
    tap(KEY_LEFT, 4)                     # -> DOME S
    # Το δωμάτιο έμεινε CANTEEN από το πέρασμα στους μεγάλους θόλους, όπου το
    # οξυγόνο δεν χωράει: ένα πάτημα πάνω το γυρίζει.
    tap(KEY_UP)
    check(m.peek(sym["BD_KIND"]) == 0 and m.peek(sym["BD_RSEL"]) == 0,
          f"ο κατάλογος στο DOME S / OXYGEN (είδος "
          f"{m.peek(sym['BD_KIND'])}, δωμάτιο {m.peek(sym['BD_RSEL'])})")
    # Ο ΚΕΡΣΟΡΑΣ ΜΠΑΙΝΕΙ ΤΕΛΕΥΤΑΙΟΣ: κάθε αλλαγή αντικειμένου τον κουμπώνει
    # στην ισοτιμία του πλάτους (§3.4), οπότε ένα poke πριν από τον κατάλογο
    # μετακινείται από κάτω του — τέσσερα βήματα αριστερά τον πήγαιναν +2.
    m.poke(sym["CUR_HX"], at[0] & 0xFF)
    m.poke(sym["CUR_HY"], at[1] & 0xFF)
    m.key_up("\x01")
    m.set_joystick_type(1)
    fire()                               # -> PLACE
    metal0 = w16(g + 3 * 2)
    mpow0, o2p0 = w16(g + 36), w16(g + 38)
    fire()                               # -> τοποθέτηση
    m.set_joystick_type(0)
    m.run_frames(30)
    check(w16(g + 3 * 2) == metal0 - 20,
          f"πληρώθηκε ο θόλος στο {at}: μέταλλο {metal0} -> {w16(g + 3 * 2)} "
          f"(ui_bad={m.peek(sym['UI_BAD'])}, κέρσορας "
          f"{sb(m.peek(sym['CUR_HX']))},{sb(m.peek(sym['CUR_HY']))})")
    # Η ΕΡΓΑΣΙΑ BUILD ΕΙΝΑΙ Η ΑΠΑΝΤΗΣΗ: φεύγει από τον πίνακα μόνο όταν η
    # ακεραιότητα φτάσει 255 και ο θόλος γίνει DS_ACTIVE (§6.9). Η ζήτηση
    # ρεύματος δεν κάνει για σημάδι — τα κρεβάτια θέλουν χειριστή και ο
    # χειριστής πάει για φαγητό.
    jt = None
    for line in open(os.path.join(ROOT, "build", "layout.asm"), encoding="utf-8"):
        if line.startswith("G_job_tbl"):
            jt = int(line.split("#")[1].strip(), 16)
    node = m.peek(sym["BD_NODE"])

    def building():
        return any(m.peek(jt + j * 5) == 0 and m.peek(jt + j * 5 + 1) == node
                   for j in range(32))

    # ΜΕΤΡΗΜΕΝΟ: 400 frames. Ηταν 10.800 όσο ο πράκτορας που έβρισκε τον
    # προορισμό απρόσιτο κρατούσε τη δουλειά του (§6.3) — η εργασία κολλούσε
    # πάνω του ώσπου να πεινάσει. Το παράθυρο είναι δεκαπλάσιο του μετρημένου:
    # ο μηχανικός εξακολουθεί να πηγαίνει όποτε τον αφήνουν οι ανάγκες του.
    got, took = 0, 0
    for k in range(80):
        m.run_frames(50)
        if not building():
            got, took = 1, 50 * (k + 1)
            break
    check(got, f"ο θόλος {node} τελείωσε: η εργασία Build έκλεισε σε "
               f"{took} frames")

    # ΚΑΙ ΔΟΥΛΕΥΕΙ. Το ρολόι πάει στην αρχή του sol ώστε να είναι μέρα: χωρίς
    # ήλιο δεν υπάρχει ρεύμα, χωρίς ρεύμα δεν παράγει καμία μηχανή, και η
    # δοκιμή θα μετρούσε τη νύχτα αντί για τον θόλο.
    m.poke(g + 52, 0)
    m.poke(g + 53, 0)
    for _ in range(60):
        m.run_frames(50)
        if w16(g + 38) >= 2 * o2p0:
            break
    check(w16(g + 38) >= 2 * o2p0,
          f"και η γεννήτρια μέσα του παράγει: οξυγόνο {o2p0} -> {w16(g + 38)}")

    live(sym, g)
    return 1 if FAIL else 0


def live(sym, g):
    """Η αποικία κινείται ΚΑΙ φαίνεται να κινείται (§8.5).

    Η λίστα βρώμικων υπόσχεται ένα πράγμα: ό,τι δείχνει η οθόνη μετά από μια
    σειρά μεταλλάξεων είναι ταυτόσημο με πλήρη σχεδίαση της ίδιας κατάστασης.
    Ως το βήμα 13 η προσομοίωση δεν έσπρωχνε τίποτα μέσα της, οπότε η υπόσχεση
    ήταν κενή: οι άποικοι μετακινούνταν στους πίνακες και όχι στα pixel.

    Εδώ τρέχει ο κανονικός βρόχος, μετά σταματά η προσομοίωση, αδειάζει η
    λίστα, και η εικόνα συγκρίνεται με πλήρη σχεδίαση. Και για να μην είναι
    η ισότητα τετριμμένη, ελέγχεται πρώτα ότι η εικόνα ΑΛΛΑΞΕ.
    """
    from cpc import CPC
    m = CPC()
    m.run_frames(60)
    assert m.quickload(SNA), "quickload απέτυχε"
    m.run_frames(120)

    def play():
        off = m.peek(sym["CAM_OFF"]) | (m.peek(sym["CAM_OFF"] + 1) << 8)
        ram = m.read_ram(0xC000, 0x4000)
        return bytes(ram[(y & 7) * 0x800 +
                         (((y >> 3) * 80 + x + 2 * off) & 0x7FF)]
                     for y in range(160) for x in range(80))

    before = play()
    # Ενα sol. Οι ανάγκες πέφτουν ~20 ανά 1.500 frames και το NEED_LOW είναι
    # 64, οπότε πριν από τα ~13.000 frames κανείς δεν σηκώνεται από τη θέση
    # του — και μια ισότητα χωρίς κίνηση δεν λέει τίποτα.
    m.run_frames(14000)
    # η προσομοίωση σταματά, η λίστα αδειάζει
    for k in range(16):
        m.poke(sym["WH_ON"] + k, 0)
    for _ in range(120):
        if m.peek(sym["DIRTY_NUM"]) == 0:
            break
        m.run_frames(1)
    check(m.peek(sym["DIRTY_NUM"]) == 0,
          f"η λίστα άδειασε ({m.peek(sym['DIRTY_NUM'])} έμειναν)")
    got = play()
    moved = sum(1 for a, b in zip(before, got) if a != b)
    check(moved > 0, f"η αποικία κινήθηκε στην οθόνη: {moved} bytes")

    # πλήρης σχεδίαση της ΙΔΙΑΣ κατάστασης
    def call(name):
        return [0xCD, sym[name] & 0xFF, sym[name] >> 8]
    # Το ui_show μπαίνει κι αυτό: αλλιώς η πλήρης σχεδίαση δεν έχει κέρσορα
    # ενώ η τρέχουσα εικόνα έχει, και η διαφορά είναι το κουτί του.
    code = bytes(call("UI_HIDE") + call("OB_CLIP_FULL") + call("VIEW_DRAW")
                 + call("UI_SHOW") + [0x18, 0xFE])
    m.run_code(0x3F00, code)
    m.run_frames(120)
    full = play()
    bad = [(i % 80, i // 80) for i, (a, b) in enumerate(zip(got, full)) if a != b]
    # ΔΕΝ είναι μηδέν, και ο λόγος δεν είναι η καλωδίωση: η «κενή» παραλλαγή
    # θέσης δεν επαναφέρει ό,τι ζωγραφίζει το πλήρες πέρασμα (DESIGN §15).
    #
    # ΤΟ ΟΡΙΟ ΔΕΝ ΕΙΝΑΙ ΑΘΡΟΙΣΜΑ BYTES, ΚΑΙ ΗΤΑΝ: το «bad <= 8» έπεσε στο βήμα
    # 19 με 16 bytes, όχι επειδή χειροτέρεψε η σχεδίαση αλλά επειδή έφθηνε το
    # HUD — στα ίδια 14.000 πραγματικά frames η προσομοίωση προχωράει τώρα
    # ~1.200 τικ παραπάνω (§9.1), άρα ΔΥΟ θέσεις δακτυλίου έχουν αδειάσει αντί
    # για μία. Στα 12.780 frames, δηλαδή στην ΙΔΙΑ πρόοδο προσομοίωσης με πριν,
    # η διαφορά είναι πάλι ακριβώς 8. Ενα άθροισμα bytes μετράει πόσο έτρεξε ο
    # κόσμος· αυτό που θέλουμε να φυλάξουμε είναι το ΣΧΗΜΑ της βλάβης:
    #
    #   * κάθε χαλασμένο tile το πολύ 8 λάθος bytes — μία θέση δακτυλίου,
    #   * μέσα σε δύο μόνο στήλες bytes — το πλάτος της θέσης, το παράθυρο
    #     όπου κόβει λάθος το πέρασμα αντικειμένων,
    #   * και λίγα τέτοια tiles συνολικά.
    #
    # Αν σπάσει κάτι άλλο στη λίστα, η βλάβη ΔΕΝ θα έχει αυτό το σχήμα.
    tiles = {}
    for x, y in bad:
        tiles.setdefault((x // 4, y // 16), []).append((x, y))
    worst = max((len(v) for v in tiles.values()), default=0)
    span = max((max(x for x, _ in v) - min(x for x, _ in v) + 1
                for v in tiles.values()), default=0)
    check(len(tiles) <= 4 and worst <= 8 and span <= 2,
          f"η λίστα κρατά την οθόνη στο γνωστό ΣΧΗΜΑ: {len(bad)} bytes σε "
          f"{len(tiles)} tiles (όριο 4), το χειρότερο {worst} bytes (όριο 8) "
          f"σε {span} στήλες (όριο 2)")


if __name__ == "__main__":
    sys.exit(main())
