#!/usr/bin/env python3
"""Σώσιμο και φόρτωμα στον δίσκο (DESIGN.md §11).

Το παιχνίδι ξεκινά από δισκέτα και γράφει στην ΙΔΙΑ δισκέτα, με δικό του
οδηγό: όταν τρέχει, το AMSDOS δεν υπάρχει πια (ο χώρος εργασίας του είναι
δεδομένα της τράπεζας 2). Ο οδηγός ελέγχεται χωριστά στο test_fdc.py· εδώ
ελέγχεται ότι ΑΥΤΟ που ξαναδιαβάζεται είναι το παιχνίδι.

Η δοκιμή παγώνει τον τροχό (wh_on = 0) γύρω από κάθε φωτογραφία. Χωρίς αυτό,
δύο «ίδιες» καταστάσεις απέχουν όσα frames πέρασαν ανάμεσά τους, και ο έλεγχος
θα ήταν ανοχή αντί για ισότητα.

  0. Ενας θόλος S δίπλα στο σκάφος (βήμα 87: η αρχή μόνη της δεν κουνιέται).
  1. Φωτογραφία Α (παγωμένος κόσμος), S = σώσε.
  2. Ο κόσμος τρέχει 18.000 frames — η οικονομία ΚΑΙ η εικόνα ΠΡΕΠΕΙ να έχουν
     αλλάξει, αλλιώς η δοκιμή δεν δοκιμάζει τίποτα.
  3. L = φόρτωσε. Φωτογραφία Γ: οικονομία, επίπεδο κόσμου και ΕΙΚΟΝΑ πίσω στο Α.
     Και τα ποσοστά των πλοίων (βήμα 91), ο έμπορος, κέρδος και φορτίο
     (βήμα 93), και οι προσγειώσεις ως τους εισβολείς (βήμα 111), αλλαγμένα
     ανάμεσα: γυρίζουν τα σωσμένα. Και το fo_n είναι #80 μετά το φόρτωμα: η
     επόμενη περιστροφή μετρά τους εισβολείς που έφερε. Και το jb_lost (βήμα
     115), μηδενισμένο πριν: #80, και ο πρώτος κύκλος ροής ξαναβρίσκει όποια
     εργασία εργοταξίου είχε χαθεί από γεμάτο πίνακα — η σημαία δεν σώζεται.
  4. Αρνητικός έλεγχος: φόρτωμα από ΑΔΕΙΟ slot πρέπει να απορριφθεί και να μην
     αγγίξει τίποτα. Ενα άδειο slot είναι #E5 παντού — απολύτως έγκυρα bytes.
  5. ΚΑΙ ΑΠΟ ΚΡΥΑ ΕΚΚΙΝΗΣΗ: reset, ξαναφόρτωμα από τον δίσκο — που φτιάχνει
     ΑΛΛΟΝ κόσμο, γιατί το seed βγαίνει από τον καταχωρητή R — και μετά L. Αυτό
     είναι η πραγματική χρήση, και μόνο εδώ αποδεικνύεται ότι το επίπεδο
     αντικαθίσταται ΟΛΟΚΛΗΡΟ: τα 16 KB διαφέρουν παντού πριν το φόρτωμα.
  8. ΣΩΣΙΜΟ ΑΛΛΗΣ ΕΚΔΟΣΗΣ (βήμα 90): ένα σώσιμο με SV_VER - 1 απορρίπτεται
     και δεν αγγίζει τίποτα· με το sv_hdr_ok πειραγμένο να δέχεται τα πάντα,
     το ίδιο σώσιμο φορτώνεται — αυτό που το απέρριψε ήταν η έκδοση.
  Και πριν από όλα, χωρίς εξομοιωτή: Η ΜΟΡΦΗ ΑΝΑ ΕΚΔΟΣΗ. Οι θέσεις των πινάκων
  μέσα στα δύο μπλοκ που σώζονται, γραμμένες εδώ για κάθε SV_VER. Το βήμα 89
  μετακίνησε την οικονομία μέσα στο μπλοκ της τράπεζας 2 (από το byte 0 στο
  109) χωρίς νέα έκδοση, και ένα σώσιμο του 88 θα φόρτωνε σιωπηλά λάθος
  αποθέματα· με αυτόν τον έλεγχο θα αποτύγχανε (η έκδοση 3 πιο κάτω είναι
  του 88).
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
        if line.startswith("G_hud_shadow"):
            # ΤΟ ΜΠΛΟΚ ΚΑΤΑΣΤΑΣΗΣ ΤΟΥ src/save.asm: τα 2 KB κάτω από την κρυφή
            # μνήμη του HUD. Ως το βήμα 33 εδώ στεκόταν ένα 0xA400 — το ίδιο
            # νούμερο με το save.asm, γραμμένο δεύτερη φορά, και θα διαφωνούσαν
            # την πρώτη φορά που θα κουνιόταν η αρένα. Κουνήθηκε.
            global STATE
            STATE = int(line.split("#")[1].strip(), 16) - 0x800
    return sym, g


STATE = None

# Η ΜΟΡΦΗ ΑΝΑ ΕΚΔΟΣΗ (§11): οι πίνακες μέσα στο μπλοκ της τράπεζας 2 (θέση από
# την αρχή του) και στο μπλοκ της τράπεζας 6 (διεύθυνση). Οποιος μετακινεί
# έναν, γράφει νέο SV_VER και νέα γραμμή εδώ.
FORMAT = {
    3: ({"G_econ_state": 0, "G_job_tbl": 92, "G_room_n": 256, "G_room_list": 268,
         "G_rt_nodes": 512, "G_rt_row": 768, "G_node_adj": 1024},           # βήμα 88
        {"G_agent_fields": 0x6C00, "G_node_occ": 0x7400, "G_dome_tbl": 0x7500,
         "G_struct_tbl": 0x7B00, "G_corr_tbl": 0x7C00, "G_worldinfo": 0x7DE0}),
    4: ({"G_mach_op": 91, "G_econ_state": 103, "G_job_tbl": 195, "G_room_n": 355,
         "G_room_list": 367, "G_rt_nodes": 512, "G_rt_row": 768, "G_node_adj": 1024},
        {"G_agent_fields": 0x6C00, "G_node_occ": 0x7400, "G_dome_tbl": 0x7500,
         "G_struct_tbl": 0x7B00, "G_corr_tbl": 0x7C00, "G_worldinfo": 0x7DE0}),
    # βήμα 91: η οικονομία 92 -> 97 (EC_LAND), οι εργασίες και τα δωμάτια +5, και
    # η μνήμη εργασίας του src/crew.asm στο κενό πριν από το rt_nodes: σώζεται
    # μαζί με το μπλοκ, και το cw_count την ξαναγράφει πριν από κάθε χρήση
    5: ({"G_mach_op": 91, "G_econ_state": 103, "G_job_tbl": 200, "G_room_n": 360,
         "G_room_list": 372, "G_crew": 468, "G_rt_nodes": 512, "G_rt_row": 768,
         "G_node_adj": 1024},
        {"G_agent_fields": 0x6C00, "G_node_occ": 0x7400, "G_dome_tbl": 0x7500,
         "G_struct_tbl": 0x7B00, "G_corr_tbl": 0x7C00, "G_worldinfo": 0x7DE0}),
    # βήμα 92: ίδια διάταξη, άλλα νοήματα — οι θέσεις 80-95 είναι των ρομπότ,
    # χωρίς ανάγκες, και ένα σώσιμο του 91 με πάνω από 80 αποίκους θα τους
    # έδινε για ρομπότ
    6: ({"G_mach_op": 91, "G_econ_state": 103, "G_job_tbl": 200, "G_room_n": 360,
         "G_room_list": 372, "G_crew": 468, "G_rt_nodes": 512, "G_rt_row": 768,
         "G_node_adj": 1024},
        {"G_agent_fields": 0x6C00, "G_node_occ": 0x7400, "G_dome_tbl": 0x7500,
         "G_struct_tbl": 0x7B00, "G_corr_tbl": 0x7C00, "G_worldinfo": 0x7DE0}),
    # βήμα 93: η οικονομία 97 -> 106 (ο έμπορος: κέρδος και φορτίο), οι
    # εργασίες, τα δωμάτια και η μνήμη εργασίας +9 — ως το rt_nodes χωρούσαν
    # ακριβώς έντεκα
    7: ({"G_mach_op": 91, "G_econ_state": 103, "G_job_tbl": 209, "G_room_n": 369,
         "G_room_list": 381, "G_crew": 477, "G_rt_nodes": 512, "G_rt_row": 768,
         "G_node_adj": 1024},
        {"G_agent_fields": 0x6C00, "G_node_occ": 0x7400, "G_dome_tbl": 0x7500,
         "G_struct_tbl": 0x7B00, "G_corr_tbl": 0x7C00, "G_worldinfo": 0x7DE0}),
    # βήμα 94: η οικονομία 106 -> 107 (τα ορυχεία, EC_MINES), ό,τι ακολουθεί
    # +1 — ως το rt_nodes μένει ένα· και το έβδομο byte του ορυχείου μετράει
    # όσους σκάβουν
    8: ({"G_mach_op": 91, "G_econ_state": 103, "G_job_tbl": 210, "G_room_n": 370,
         "G_room_list": 382, "G_crew": 478, "G_rt_nodes": 512, "G_rt_row": 768,
         "G_node_adj": 1024},
        {"G_agent_fields": 0x6C00, "G_node_occ": 0x7400, "G_dome_tbl": 0x7500,
         "G_struct_tbl": 0x7B00, "G_corr_tbl": 0x7C00, "G_worldinfo": 0x7DE0}),
    # βήμα 111: η οικονομία 107 -> 108 (οι προσγειώσεις ως τους εισβολείς,
    # EC_LANDS), ό,τι ακολουθεί +1 — ως το rt_nodes δεν μένει κανένα· οι
    # εισβολείς είναι οι θέσεις 96-99, μέσα στο μπλοκ που ήδη σώζεται
    9: ({"G_mach_op": 91, "G_econ_state": 103, "G_job_tbl": 211, "G_room_n": 371,
         "G_room_list": 383, "G_crew": 479, "G_rt_nodes": 512, "G_rt_row": 768,
         "G_node_adj": 1024},
        {"G_agent_fields": 0x6C00, "G_node_occ": 0x7400, "G_dome_tbl": 0x7500,
         "G_struct_tbl": 0x7B00, "G_corr_tbl": 0x7C00, "G_worldinfo": 0x7DE0}),
}


def save_format():
    """Οι πίνακες της διάταξης μέσα στα δύο μπλοκ, όπως τους έχει το build."""
    L = {}
    for line in open(os.path.join(ROOT, "build", "layout.asm"), encoding="utf-8"):
        p = line.split()
        if len(p) >= 3 and p[1] == "equ" and p[2].startswith("#"):
            L[p[0]] = int(p[2][1:], 16)
    st = L["G_hud_shadow"] - 0x800
    b2 = {n: a - st for n, a in L.items()
          if st <= a < st + 0x800 and n.startswith("G_")}
    b6 = {n: L[n] for n in FORMAT[max(FORMAT)][1]}
    return b2, b6


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

    # ΤΟ ΣΩΣΙΜΟ ΖΕΙ ΣΤΙΣ ΤΡΥΠΕΣ ΤΟΥ DIST από το βήμα 103 (src/demolish.asm): οι
    # ετικέτες του δείχνουν στο SV_ORG του GH_BUF, όπου το φέρνει κάθε S και L.
    # Ο,τι διαβάζει ή πειράζει η δοκιμή ΠΡΙΝ από ένα S ή L, το διαβάζει ή το
    # πειράζει εκεί όπου μένει: στις τρύπες της τράπεζας 1, από τη γραμμή μετά
    # την κατεδάφιση (build/ovl.bin).
    import cpc
    b1 = cpc._lib.cpcemu_ram_ptr(m._h, 1)
    rows1 = (os.path.getsize(os.path.join(ROOT, "build", "ovl.bin")) + 31) // 32

    def hole(a):
        k = a - sym["ZZ_OV2"]
        return 128 * (rows1 + (k >> 5)) + 96 + (k & 31)

    def ov_read(a, n):
        return bytes(b1[hole(a + i)] for i in range(n))

    def ov_write(a, data):
        for i, v in enumerate(data):
            b1[hole(a + i)] = v

    # --- η μορφή ανά έκδοση ------------------------------------------------
    ver = ov_read(sym["SV_MAGIC"] + 4, 1)[0]
    have = save_format()
    check(ver in FORMAT and have == FORMAT[ver],
          f"η μορφή της έκδοσης {ver} είναι αυτή που γράφει το FORMAT"
          + ("" if ver in FORMAT and have == FORMAT[ver] else
             f" — ΟΧΙ: {have}, ενώ η έκδοση {ver} λέει {FORMAT.get(ver)}. "
             f"Πίνακας που σώζεται μετακινήθηκε: νέο SV_VER στο src/save.asm"))

    def freeze(on):
        for i in range(16):
            m.poke(sym["WH_ON"] + i, 0 if on else 1)

    def snap():
        """Οικονομία, δείγματα επιπέδου, και η ΕΙΚΟΝΑ του κάδρου."""
        econ = bytes(m.read_ram(STATE, 0x800))
        m.run_code(0x3EC0, blob)
        m.run_frames(2)
        plane = bytes(m.read_ram(0x3F00, 256))
        # Το probe κράτησε τις διακοπές κλειστές τρία frames: πίσω στον βρόχο
        # μέσα από το is_on, όπως ο ίδιος ο δίσκος (src/isr.asm, βήμα 83) —
        # αλλιώς οι λωρίδες χρειάζονται ως δύο frames να ξαναβρούν το βήμα, και
        # η φωτογραφία πέφτει πάνω τους.
        io, top = sym["IS_ON"], sym["MAIN_LOOP"]
        m.run_code(0x3EA0, bytes([0xCD, io & 255, io >> 8, 0xC3, top & 255, top >> 8]),
                   frames=2)
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
        μέση του. Από το βήμα 83 το HUD είναι λωρίδες πάνω ΚΑΙ κάτω από το
        κάδρο, και η εικόνα αρχίζει στη σάρωση 13 (R7 = 33): το κάδρο είναι οι
        σαρώσεις 29-188, οι γραμμές 16-175 της οθόνης."""
        from PIL import Image
        path = os.path.join(ROOT, "build", f"save_{tag}.png")
        m.screenshot(path)
        im = Image.open(path).convert("RGB")
        return list(im.crop((0, 13 + 16, im.size[0], 13 + 176)).getdata())

    # --- η επιλογή θέσης (§11) --------------------------------------------
    # Από το βήμα 22 το S και το L ΔΕΝ σώζουν κατευθείαν: ανοίγουν επιλογή και
    # περιμένουν FIRE. Το FIRE έρχεται από COPY ή από το χειριστήριο· εδώ από
    # το χειριστήριο, που όσο είναι αναμμένο κλέβει τα βελάκια από τη μήτρα —
    # γι' αυτό ανάβει και σβήνει γύρω από κάθε πάτημα.
    from sprites import load_map, load_bin
    from cpc import KEY_RIGHT, KEY_ESC
    import hudread

    def hud_row(row):
        return hudread.text(m, sym, row)

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
                # ΚΑΙ ΕΝΑ FRAME ΜΕΤΑ (βήμα 99): η σειρά μπορεί να πιαστεί στη
                # μέση της σχεδίασης — «LOADED FROM SLOT» χωρίς το ψηφίο, όταν
                # ο κώδικας της τράπεζας 0 μετακινήθηκε και η φάση άλλαξε.
                m.run_frames(1)
                n += 1
                r2 = hud_row(3)
                LAST_MSG = (r2 if "SLOT" in r2 or "ERROR" in r2 else r).rstrip()
                break
        m.run_frames(30)
        return n + 4


    # --- 0. ένας θόλος στο εργοτάξιο ---------------------------------------
    # ΑΠΟ ΤΟ ΒΗΜΑ 87 Η ΑΡΧΗ ΕΙΝΑΙ ΑΚΙΝΗΤΗ: τέσσερις άποικοι δίπλα στο σκάφος,
    # χωρίς τίποτα να κάνουν, και η εικόνα του Β ήταν ίδια με του Α. Ενας
    # θόλος S δίπλα στο σκάφος, πριν από τη φωτογραφία: ο μηχανικός βγαίνει,
    # τον χτίζει και γυρίζει — και το σώσιμο κρατά ένα εργοτάξιο, με τη
    # σύνδεση εδάφους του.
    import balance as B
    check(B.build(m, sym, 0, g + 6, at=(6, 2), room=0, fit=False) is True,
          "ένας θόλος S μπήκε δίπλα στο σκάφος")
    # Η διεπαφή μένει στο PLACE μετά την τοποθέτηση: το fire 2 δύο φορές την
    # γυρίζει στην ήρεμη κατάσταση, αλλιώς το S δεν ανοίγει το σώσιμο.
    m.set_joystick_type(1)
    for _ in range(2):
        m.joystick(0x20)
        m.run_frames(4)
        m.joystick(0)
        m.run_frames(10)
    m.set_joystick_type(0)
    m.run_frames(50)
    assert m.peek(sym["UI_STATE"]) == 0, f"η διεπαφή στην κατάσταση {m.peek(sym['UI_STATE'])}"

    # --- 1. φωτογραφία Α και σώσιμο ---------------------------------------
    # Τα ποσοστά των πλοίων (EC_LAND, βήμα 91) όχι τα αρχικά: πρέπει να
    # γυρίσουν ΑΥΤΑ, και όχι τα 20% που ξαναγράφει κάθε νέο παιχνίδι.
    LAND_A, LAND_B = [1, 0, 3, 2, 4], [2] * 5
    land = lambda: [m.peek(g + 92 + r) for r in range(5)]
    for r in range(5):
        m.poke(g + 92 + r, LAND_A[r])
    # Και ο έμπορος (βήμα 93): το κέρδος και το φορτίο του, +97..+105.
    MER_A, MER_B = [52, 3, 10, 9, 2, 1, 30, 0, 0], [35] + [0] * 8
    mer = lambda: [m.peek(g + 97 + k) for k in range(9)]
    for k, v in enumerate(MER_A):
        m.poke(g + 97 + k, v)
    # Και οι προσγειώσεις (EC_LANDS, βήμα 111), +107.
    LANDS_A, LANDS_B = 5, 0
    m.poke(g + 107, LANDS_A)
    freeze(True)
    m.run_frames(4)
    a_econ, a_plane, a_play = snap()
    a_img = image("a")
    # Ο ΚΩΔΙΚΑΣ ΤΟΥ ΣΩΣΙΜΑΤΟΣ ΕΡΧΕΤΑΙ ΑΠΟ ΤΙΣ ΤΡΥΠΕΣ σε κάθε S (βήμα 103): ό,τι
    # κι αν έχει μείνει στο SV_ORG — εδώ rst 0 ως το τέλος του GH_BUF — το
    # σώσιμο πετυχαίνει.
    sv_org = sym["ZZ_OV2"]
    m.write_ram(sv_org, b"\xC7" * (sym["ZZ_OV2_END"] - sv_org))
    nsave = disc_op("S")
    check(m.peek(sym["SV_SLOT"]) == 0 and m.peek(sym["FD_TRK"]) >= 24,
          f"το σώσιμο έτρεξε (slot {m.peek(sym['SV_SLOT'])}, "
          f"track #{m.peek(sym['FD_TRK'])}), με σκουπίδια στο SV_ORG πριν")

    # --- 2. ο κόσμος προχωρά ----------------------------------------------
    # ΕΝΑΜΙΣΙ SOL, ΟΧΙ ΕΝΑ. Οι άποικοι ξεκινούν με γεμάτες μπάρες και πέφτουν
    # μία μονάδα ανά τέσσερις περιστροφές: κανείς δεν σηκώνεται από τη θέση του
    # πριν από τις ~12.000 frames (§6.6), και από το βήμα 25 η οικονομία δεν
    # κουνάει ούτε τα αποθέματα — η αποικία του §10.1 δεν έχει ρεύμα. Με
    # ακριβώς ένα sol η εικόνα ήταν ΙΔΙΑ και ο έλεγχος «γύρισε» τετριμμένος.
    freeze(False)
    m.run_frames(18000)
    for r in range(5):
        m.poke(g + 92 + r, LAND_B[r])           # ο παίκτης άλλαξε τα ποσοστά
    for k, v in enumerate(MER_B):
        m.poke(g + 97 + k, v)                   # και ήρθε άλλος έμπορος
    m.poke(g + 107, LANDS_B)                    # και ήρθαν οι εισβολείς
    m.poke(sym["FO_N"], 0)                      # ...και έπεσαν
    m.poke(sym["JB_LOST"], 0)                   # τίποτα χαμένο σε αυτή τη συνεδρία
    freeze(True)
    m.run_frames(4)
    b_econ, b_plane, b_play = snap()
    o = g - STATE
    dwater = (b_econ[o] | (b_econ[o + 1] << 8)) - (a_econ[o] | (a_econ[o + 1] << 8))
    check(b_econ != a_econ,
          f"η κατάσταση άλλαξε στα 18.000 frames (νερό {dwater:+d}, "
          f"{sum(1 for x, y in zip(b_econ, a_econ) if x != y)} bytes)")

    # --- 3. φόρτωμα --------------------------------------------------------
    nload = disc_op("L")
    m.run_frames(120)
    c_econ, c_plane, c_play = snap()
    check(c_plane == a_plane, "το επίπεδο κόσμου γύρισε ακριβώς")
    check(land() == LAND_A, f"τα ποσοστά των πλοίων γύρισαν: {land()}, σωσμένα {LAND_A}")
    check(mer() == MER_A, f"ο έμπορος γύρισε: κέρδος και φορτίο {mer()}, σωσμένα {MER_A}")
    check(m.peek(g + 107) == LANDS_A and m.peek(sym["FO_N"]) == 0x80,
          f"οι προσγειώσεις γύρισαν: {m.peek(g + 107)}, σωσμένες {LANDS_A}· "
          f"fo_n #{m.peek(sym['FO_N']):02X} (οι εισβολείς μετριούνται ξανά)")
    check(m.peek(sym["JB_LOST"]) == 0x80,
          f"jb_lost #{m.peek(sym['JB_LOST']):02X} μετά το φόρτωμα, όχι #80: ο πρώτος "
          f"κύκλος ροής ξανασαρώνει τις εργασίες (wheel_load, βήμα 115)")
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
    m.run_code(0x3EC0, bytes([0x3E, 0x02, 0xCD, lo, hi, 0x32, 0x00, 0x3F,
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

    # --- 8. σώσιμο άλλης έκδοσης -----------------------------------------
    # Η εικόνα της προηγούμενης έκδοσης: το sv_magic με SV_VER - 1, σώσιμο
    # στη δεύτερη θέση (άδεια ως εδώ), το sv_magic πίσω, φόρτωμα.
    mg = sym["SV_MAGIC"]
    mine = ov_read(mg, 5)
    ov_write(mg, b"HBT" + bytes([ord("0") + ver - 1, ver - 1]))
    disc_op("S", 1)
    ov_write(mg, mine)
    freeze(True)
    m.run_frames(4)
    j_econ, j_plane, _ = snap()
    disc_op("L", 1)
    m.run_frames(120)
    k_econ, k_plane, _ = snap()
    check("NOTHING IN SLOT 2" in LAST_MSG and k_econ == j_econ and k_plane == j_plane,
          f"ένα σώσιμο της έκδοσης {ver - 1} απορρίπτεται και δεν αγγίζει τίποτα: "
          f"|{LAST_MSG}|, {sum(1 for x, y in zip(k_econ, j_econ) if x != y)} bytes")
    # ΑΡΝΗΤΙΚΟ: το sv_hdr_ok χωρίς τη σύγκριση (jr nz,svo_bad -> nop nop)
    # δέχεται το ίδιο σώσιμο: αυτό που το απέρριψε ήταν η έκδοση.
    hk = next(sym["SV_HDR_OK"] + k for k in range(16)
              if list(ov_read(sym["SV_HDR_OK"] + k, 2)) == [0xBE, 0x20])
    ov_write(hk + 1, b"\x00\x00")
    disc_op("L", 1)
    check("LOADED FROM SLOT 2" in LAST_MSG,
          f"ΑΡΝΗΤΙΚΟ: με το sv_hdr_ok να δέχεται τα πάντα, το ίδιο σώσιμο φορτώνεται: |{LAST_MSG}|")

    # ΑΡΝΗΤΙΚΟ (βήμα 103): χωρίς το ov_copy του sv_ovl (call -> nop) και με
    # σκουπίδια στο SV_ORG, το S δεν σώζει. Τελευταίο: ό,τι τρέξει από εκεί δεν
    # γυρίζει.
    so = sym["SV_OVL"]
    oc = sym["OV_COPY"]
    k = next(k for k in range(16)
             if list(m.read_ram(so + k, 3)) == [0xCD, oc & 255, oc >> 8])
    m.screenshot(os.path.join(ROOT, "build", "save.png"), aspect=True)
    m.write_ram(so + k, b"\0\0\0")
    m.write_ram(sv_org, b"\xC7" * (sym["ZZ_OV2_END"] - sv_org))
    disc_op("S", 0)
    check("SAVED" not in LAST_MSG,
          f"ΑΡΝΗΤΙΚΟ: χωρίς τον κώδικα από τις τρύπες το S δεν σώζει: |{LAST_MSG}|")
    if FAIL:
        print(f"\nΑΠΟΤΥΧΙΑ — {len(FAIL)}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
