#!/usr/bin/env python3
"""Σώσιμο και φόρτωμα στον δίσκο (DESIGN.md §11).

Το παιχνίδι ξεκινά από δισκέτα και γράφει στην ΙΔΙΑ δισκέτα, με δικό του
οδηγό: όταν τρέχει, το AMSDOS δεν υπάρχει πια (ο χώρος εργασίας του είναι
δεδομένα της τράπεζας 2). Ο οδηγός ελέγχεται χωριστά στο test_fdc.py· εδώ
ελέγχεται ότι ΑΥΤΟ που ξαναδιαβάζεται είναι το παιχνίδι.

Η δοκιμή παγώνει τον τροχό (wh_on = 0) γύρω από κάθε φωτογραφία. Χωρίς αυτό,
δύο «ίδιες» καταστάσεις απέχουν όσα frames πέρασαν ανάμεσά τους, και ο έλεγχος
θα ήταν ανοχή αντί για ισότητα.

  1. Φωτογραφία Α (παγωμένος κόσμος), S = σώσε.
  2. Ο κόσμος τρέχει 4.000 frames — η οικονομία ΠΡΕΠΕΙ να έχει αλλάξει,
     αλλιώς η δοκιμή δεν δοκιμάζει τίποτα.
  3. L = φόρτωσε. Φωτογραφία Γ: οικονομία, επίπεδο κόσμου και ΕΙΚΟΝΑ πίσω στο Α.
  4. Αρνητικός έλεγχος: φόρτωμα από ΑΔΕΙΟ slot πρέπει να απορριφθεί και να μην
     αγγίξει τίποτα. Ενα άδειο slot είναι #E5 παντού — απολύτως έγκυρα bytes.
  5. ΚΑΙ ΑΠΟ ΚΡΥΑ ΕΚΚΙΝΗΣΗ: reset, ξαναφόρτωμα από τον δίσκο — που φτιάχνει
     ΑΛΛΟΝ κόσμο, γιατί το seed βγαίνει από τον καταχωρητή R — και μετά L. Αυτό
     είναι η πραγματική χρήση, και μόνο εδώ αποδεικνύεται ότι το επίπεδο
     αντικαθίσταται ΟΛΟΚΛΗΡΟ: τα 16 KB διαφέρουν παντού πριν το φόρτωμα.
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")

RASM = os.path.expanduser("~/rasm/rasm.exe")
DSK = os.path.join(ROOT, "build", "habitat.dsk")
PLANE = os.path.join(ROOT, "build", "plane.bin")
FAIL = []
LAST_MSG = ""


def check(ok, msg):
    print(("OK " if ok else "ΛΑΘΟΣ ") + msg)
    if not ok:
        FAIL.append(msg)


def build():
    for cmd in ([sys.executable, os.path.join(ROOT, "tools", "mkdsk.py")],
                [RASM, "plane.asm"]):
        r = subprocess.run(cmd, cwd=HERE if cmd[0] == RASM else ROOT,
                           capture_output=True, text=True)
        if r.returncode:
            sys.exit(f"{cmd[0]} απέτυχε:\n{r.stdout}{r.stderr}")
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
    from cpc import CPC
    blob = open(PLANE, "rb").read()

    m = CPC()
    m.run_frames(300)
    m.insert_disc(DSK)
    m.type_text('|disc\n', hold_frames=4, gap_frames=8)
    m.run_frames(60)
    m.type_text('run"habitat\n', hold_frames=4, gap_frames=8)

    def w16(a):
        return m.peek(a) | (m.peek(a + 1) << 8)

    for _ in range(120):
        m.run_frames(30)
        if w16(g + 2) == 40 and m.peek(g + 58) == 4:
            break
    else:
        sys.exit("το παιχνίδι δεν ξεκίνησε από τον δίσκο")
    m.run_frames(200)

    def freeze(on):
        for i in range(16):
            m.poke(sym["WH_ON"] + i, 0 if on else 1)

    def snap():
        """Οικονομία, δείγματα επιπέδου, και η ΕΙΚΟΝΑ του κάδρου."""
        econ = bytes(m.read_ram(0xA400, 0x800))
        m.run_code(0x3E00, blob)
        m.run_frames(2)
        plane = bytes(m.read_ram(0x3F00, 256))
        m.set_pc(sym["MAIN_LOOP"])
        m.run_frames(2)
        off = w16(sym["CAM_OFF"])
        ram = m.read_ram(0xC000, 0x4000)
        play = bytes(ram[(y & 7) * 0x800 + (((y >> 3) * 80 + x + 2 * off) & 0x7FF)]
                     for y in range(160) for x in range(80))
        return econ, plane, play

    def image(tag):
        """Το ΚΑΔΡΟ με τα χρώματά του. Τα bytes της οθόνης είναι αριθμοί pen:
        αν το φόρτωμα ξεχνούσε την παλέτα του πλανήτη (§5.7), θα ήταν ίδια ως
        το τελευταίο byte και άλλη στο μάτι.

        ΧΩΡΙΣ ΤΟ HUD, για δύο λόγους που δεν έχουν σχέση με την παλέτα: μετά
        το φόρτωμα η σειρά 3 γράφει «LOADED SLOT 1», και από το βήμα 18 το HUD
        ξαναγράφεται με δικό του ρολόι — μια φωτογραφία μπορεί να πέσει στη
        μέση του. Το κάδρο είναι οι πρώτες 160 γραμμές, δηλαδή ό,τι είναι πάνω
        από τη γραμμή 200 της εικόνας."""
        from PIL import Image
        path = os.path.join(ROOT, "build", f"save_{tag}.png")
        m.screenshot(path)
        im = Image.open(path).convert("RGB")
        return list(im.crop((0, 0, im.size[0], 200)).getdata())

    # --- η επιλογή θέσης (§11) --------------------------------------------
    # Από το βήμα 22 το S και το L ΔΕΝ σώζουν κατευθείαν: ανοίγουν επιλογή και
    # περιμένουν FIRE. Το FIRE έρχεται από COPY ή από το χειριστήριο· εδώ από
    # το χειριστήριο, που όσο είναι αναμμένο κλέβει τα βελάκια από τη μήτρα —
    # γι' αυτό ανάβει και σβήνει γύρω από κάθε πάτημα.
    from sprites import load_map, load_bin
    from cpc import KEY_RIGHT, KEY_ESC
    smap, sblob = load_map(), load_bin()
    _f = smap["font_gfx"]
    _font = sblob[_f.off:_f.off + _f.size]
    GLYPH = {bytes(_font[i * 16:(i + 1) * 16]): chr(32 + i) for i in range(96)}

    def hud_row(row):
        off = w16(sym["CAM_OFF"])
        ram = m.read_ram(0xC000, 0x4000)

        def byte(x, y):
            return ram[(y & 7) * 0x800 + (((y >> 3) * 80 + x + 2 * off) & 0x7FF)]
        return "".join(GLYPH.get(bytes(byte(c * 2 + k, 160 + row * 8 + l)
                                       for l in range(8) for k in range(2)), "#")
                       for c in range(40))

    def press(key, frames=24):
        # 4 + 24 > 16: ΤΟ ΡΟΛΟΙ ΤΟΥ HUD. Ο πίνακας ξαναγράφεται ανά δεκαέξι
        # frames (§9.2), οπότε με μικρότερη αναμονή η οθόνη μπορεί να δείχνει
        # ακόμη την προηγούμενη κατάσταση — και η δοκιμή να πέφτει στα ίσα.
        m.key_down(key)
        m.run_frames(4)
        m.key_up(key)
        m.run_frames(frames)

    def fire(frames=12):
        m.set_joystick_type(1)
        m.run_frames(2)
        m.joystick(0x10)
        m.run_frames(4)
        m.joystick(0)
        m.set_joystick_type(0)
        m.run_frames(frames)

    SV_SLOTS = 3

    def disc_op(key, slot=0):
        """S ή L, μετά (slot) φορές δεξιά, μετά FIRE. Γυρίζει τα frames που
        κράτησε η κεφαλή."""
        press(key)
        # Η επιλογή ΘΥΜΑΤΑΙ την τελευταία θέση — γι' αυτό πάμε προς τα εκεί
        # αντί να μετράμε πατήματα από το μηδέν.
        n = 0
        while m.peek(sym["SL_PICK"]) != slot and n < 2 * SV_SLOTS:
            press(KEY_RIGHT)
            n += 1
        assert m.peek(sym["SL_PICK"]) == slot, "η επιλογή δεν έφτασε στη θέση"
        m.poke(sym["FD_TRK"], 0)
        fire(4)
        # ΤΟ ΤΕΛΟΣ ΤΗΣ ΔΟΥΛΕΙΑΣ ΕΙΝΑΙ ΤΟ ΜΗΝΥΜΑ, όχι η θέση της κεφαλής: μια
        # άδεια θέση απορρίπτεται στην πρώτη πίστα και η κεφαλή δεν φτάνει ποτέ
        # εκεί που θα έφτανε ένα κανονικό φόρτωμα. Και το μήνυμα είναι
        # στιγμιαίο — το πρώτο ui_panel, μέσα σε δεκαέξι frames, το σβήνει —
        # οπότε διαβάζεται κάθε frame.
        global LAST_MSG
        LAST_MSG = ""
        n = 0
        while n < 300:
            m.run_frames(1)
            n += 1
            r = hud_row(3)
            if "SLOT" in r or "ERROR" in r:
                LAST_MSG = r.rstrip()
                break
        m.run_frames(30)
        return n + 4


    # --- 1. φωτογραφία Α και σώσιμο ---------------------------------------
    freeze(True)
    m.run_frames(4)
    a_econ, a_plane, a_play = snap()
    a_img = image("a")
    nsave = disc_op("S")
    check(m.peek(sym["SV_SLOT"]) == 0 and m.peek(sym["FD_TRK"]) >= 24,
          f"το σώσιμο έτρεξε (slot {m.peek(sym['SV_SLOT'])}, "
          f"track #{m.peek(sym['FD_TRK'])})")

    # --- 2. ο κόσμος προχωρά ----------------------------------------------
    # ΕΝΑΜΙΣΙ SOL, ΟΧΙ ΕΝΑ. Οι άποικοι ξεκινούν με γεμάτες μπάρες και πέφτουν
    # μία μονάδα ανά τέσσερις περιστροφές: κανείς δεν σηκώνεται από τη θέση του
    # πριν από τις ~12.000 frames (§6.6), και από το βήμα 25 η οικονομία δεν
    # κουνάει ούτε τα αποθέματα — η αποικία του §10.1 δεν έχει ρεύμα. Με
    # ακριβώς ένα sol η εικόνα ήταν ΙΔΙΑ και ο έλεγχος «γύρισε» τετριμμένος.
    freeze(False)
    m.run_frames(18000)
    freeze(True)
    m.run_frames(4)
    b_econ, b_plane, b_play = snap()
    o = g - 0xA400
    dwater = (b_econ[o] | (b_econ[o + 1] << 8)) - (a_econ[o] | (a_econ[o + 1] << 8))
    check(b_econ != a_econ,
          f"η κατάσταση άλλαξε στα 18.000 frames (νερό {dwater:+d}, "
          f"{sum(1 for x, y in zip(b_econ, a_econ) if x != y)} bytes)")

    # --- 3. φόρτωμα --------------------------------------------------------
    nload = disc_op("L")
    m.run_frames(120)
    c_econ, c_plane, c_play = snap()
    check(c_plane == a_plane, "το επίπεδο κόσμου γύρισε ακριβώς")
    same = sum(1 for x, y in zip(c_econ, a_econ) if x == y)
    check(same >= len(a_econ) - 8,
          f"η κατάσταση γύρισε: {len(a_econ) - same} bytes διαφορά στα "
          f"{len(a_econ)} (πριν το φόρτωμα: "
          f"{sum(1 for x, y in zip(b_econ, a_econ) if x != y)})")
    diff = sum(1 for x, y in zip(c_play, a_play) if x != y)
    bdiff = sum(1 for x, y in zip(b_play, a_play) if x != y)
    check(diff <= 8 and bdiff > 8,
          f"η εικόνα γύρισε: {diff} bytes διαφορά από το Α "
          f"(πριν το φόρτωμα: {bdiff})")

    # --- 4. άδειο slot -----------------------------------------------------
    lo, hi = sym["SV_LOAD"] & 0xFF, sym["SV_LOAD"] >> 8
    m.run_code(0x3E00, bytes([0x3E, 0x02, 0xCD, lo, hi, 0x32, 0x00, 0x3F,
                              0x18, 0xFE]))
    m.run_frames(120)
    rc = m.peek(0x3F00)
    m.set_pc(sym["MAIN_LOOP"])
    m.run_frames(4)
    d_econ, _, _ = snap()
    check(rc != 0, f"το άδειο slot 3 απορρίφθηκε (κωδικός #{rc:02X})")
    check(d_econ == c_econ, "και δεν άγγιξε την κατάσταση")

    print(f"\nκόστος: σώσιμο {nsave} frames, φόρτωμα {nload} frames "
          f"— 46 τομείς, 23 KB")
    # --- 5. κρύα εκκίνηση, άλλος κόσμος, και μετά φόρτωμα ------------------
    m.reset()
    m.run_frames(300)
    m.type_text('|disc\n', hold_frames=4, gap_frames=8)
    m.run_frames(60)
    m.type_text('run"habitat\n', hold_frames=4, gap_frames=8)
    for _ in range(120):
        m.run_frames(30)
        if w16(g + 2) == 40 and m.peek(g + 58) == 4:
            break
    else:
        sys.exit("το παιχνίδι δεν ξαναξεκίνησε μετά το reset")
    m.run_frames(200)
    freeze(True)
    m.run_frames(4)
    e_econ, e_plane, e_play = snap()
    check(e_plane != a_plane,
          f"η κρύα εκκίνηση έφτιαξε ΑΛΛΟΝ κόσμο "
          f"({sum(1 for x, y in zip(e_plane, a_plane) if x != y)}/256 δείγματα "
          f"διαφέρουν)")
    disc_op("L")
    m.run_frames(120)
    f_econ, f_plane, f_play = snap()
    check(f_plane == a_plane, "το σωσμένο επίπεδο αντικατέστησε ολόκληρο το νέο")
    same = sum(1 for x, y in zip(f_econ, a_econ) if x == y)
    check(same >= len(a_econ) - 8,
          f"η αποικία γύρισε μετά από reset: {len(a_econ) - same} bytes διαφορά")
    fdiff = sum(1 for x, y in zip(f_play, a_play) if x != y)
    check(fdiff <= 8,
          f"και η εικόνα: {fdiff} bytes διαφορά από το Α")
    f_img = image("f")
    pdiff = sum(1 for x, y in zip(f_img, a_img) if x != y)
    check(pdiff == 0,
          f"και ΤΑ ΧΡΩΜΑΤΑ: {pdiff} pixel διαφορά — ο πλανήτης ήρθε με το "
          f"σωσμένο παιχνίδι")

    # --- 6. Η ΕΠΙΛΟΓΗ ΘΕΣΗΣ, ΚΑΙ ΟΙ ΑΛΛΕΣ ΔΥΟ ΘΕΣΕΙΣ ----------------------
    # Ο δίσκος είχε τρεις θέσεις από το βήμα 16· το UI έδινε πάντα `xor a`,
    # οπότε 46 KB δεν είχαν γραφτεί ΠΟΤΕ — ούτε από δοκιμή. Εδώ γράφονται.
    press("S")
    r3 = hud_row(3)
    check(m.peek(sym["UI_STATE"]) == 4 and "SAVE TO SLOT   1" in r3
          and r3.rstrip().endswith("x1"),
          f"το S ανοίγει επιλογή: |{r3.rstrip()}|")
    press(KEY_RIGHT)
    r3b = hud_row(3)
    check("SAVE TO SLOT   2" in r3b and m.peek(sym["SL_PICK"]) == 1,
          f"το δεξί βελάκι αλλάζει θέση: |{r3b.rstrip()}|")
    trk = m.peek(sym["FD_TRK"])
    press(KEY_ESC)
    check(m.peek(sym["UI_STATE"]) == 0 and m.peek(sym["FD_TRK"]) == trk,
          f"το ESC ακυρώνει χωρίς να αγγίξει τον δίσκο (κατάσταση "
          f"{m.peek(sym['UI_STATE'])}, κεφαλή {m.peek(sym['FD_TRK'])})")

    # η τρίτη θέση ζει στα tracks 36-41: η κεφαλή δεν έχει πάει ποτέ εκεί
    freeze(False)
    m.run_frames(9000)                   # όχι 3.000: με τόσο λίγη προσομοίωση
    freeze(True)                         # οι δύο καταστάσεις διέφεραν 8 bytes,
    m.run_frames(4)                      # δηλαδή όσο και η ανοχή του ελέγχου
    g_econ, _, _ = snap()
    disc_op("S", 2)
    check(m.peek(sym["SV_SLOT"]) == 2 and m.peek(sym["FD_TRK"]) >= 36,
          f"σώθηκε στην τρίτη θέση (slot {m.peek(sym['SV_SLOT'])}, "
          f"track #{m.peek(sym['FD_TRK'])})")
    check("SAVED TO SLOT 3" in LAST_MSG, f"και το λέει: |{LAST_MSG}|")

    # η πρώτη θέση δεν πειράχτηκε: φόρτωσέ την και γύρνα στο Α
    disc_op("L", 0)
    m.run_frames(120)
    h_econ, h_plane, _ = snap()
    check(h_plane == a_plane and
          sum(1 for x, y in zip(h_econ, a_econ) if x != y) <= 8,
          "η πρώτη θέση έμεινε ανέπαφη από το γράψιμο της τρίτης")

    # και η τρίτη έχει το ΔΙΚΟ της παιχνίδι
    disc_op("L", 2)
    m.run_frames(120)
    i_econ, _, _ = snap()
    check(sum(1 for x, y in zip(i_econ, g_econ) if x != y) <= 8 and
          sum(1 for x, y in zip(i_econ, a_econ) if x != y) > 8,
          f"και η τρίτη το δικό της: {sum(1 for x, y in zip(i_econ, g_econ) if x != y)} "
          f"bytes από το Γ, {sum(1 for x, y in zip(i_econ, a_econ) if x != y)} από το Α")

    # --- 7. άδεια θέση ΔΕΝ είναι βλάβη δίσκου -----------------------------
    disc_op("L", 1)
    check("NOTHING IN SLOT 2" in LAST_MSG,
          f"η άδεια θέση το λέει με λόγια, όχι «DISC ERROR»: |{LAST_MSG}|")

    m.screenshot(os.path.join(ROOT, "build", "save.png"), aspect=True)
    if FAIL:
        print(f"\nΑΠΟΤΥΧΙΑ — {len(FAIL)}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
