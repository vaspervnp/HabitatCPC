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
    from cpc import CPC, KEY_SPACE, KEY_RIGHT
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
    check(55 <= stock[0] <= 60 and stock[1] == 40 and stock[3] == 30
          and stock[4] == 10 and stock[6] == 4 and m.peek(g + 58) == 4,
          f"§10.1: 60 νερό / 40 τροφή / 30 μέταλλο / 10 βιοπλαστικό / "
          f"4 ανταλλακτικά, 4 άποικοι — {stock} {m.peek(g + 58)}")
    row2 = hud(2)
    check(row2.startswith("POP  4/"), f"το HUD ξέρει τον πληθυσμό: |{row2}|")

    # --- 2 & 3. η προσομοίωση τρέχει ΚΑΙ φαίνεται ------------------------
    m.run_frames(2000)
    water = w16(g)
    check(water < 55, f"το νερό πέφτει μόνο του: {stock[0]} -> {water}")

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
    m.run_frames(60)                     # μία περιστροφή τροχού για το HUD
    alert1 = hud(2)[20:]
    check(alert0.strip() != alert1.strip()
          and alert1.strip() == "ALL SYSTEMS OK",
          f"το HUD το ΔΕΙΧΝΕΙ χωρίς πάτημα: |{alert0.strip()}| -> "
          f"|{alert1.strip()}|")
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
    bad = sum(1 for a, b in zip(got, full) if a != b)
    # ΔΕΝ είναι μηδέν, και ο λόγος δεν είναι η καλωδίωση: η «κενή» παραλλαγή
    # θέσης δεν επαναφέρει ό,τι ζωγραφίζει το πλήρες πέρασμα (DESIGN §15).
    # Χωρίς σπρωξίματα η διαφορά είναι 26 bytes· με αυτά, 8 — και τα οκτώ
    # είναι μία θέση δακτυλίου στο αριστερό χείλος ενός θόλου. Το όριο είναι
    # εδώ για να πέσει η δοκιμή αν ΧΕΙΡΟΤΕΡΕΨΕΙ.
    check(bad <= 8,
          f"η λίστα κρατά την οθόνη μέσα στο γνωστό όριο: {bad} bytes "
          f"διαφέρουν από πλήρη σχεδίαση (όριο 8)")


if __name__ == "__main__":
    sys.exit(main())
