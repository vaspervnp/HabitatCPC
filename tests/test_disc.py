#!/usr/bin/env python3
"""Ο δίσκος (DESIGN.md §13, §4.2).

Ως εδώ το παιχνίδι ξεκινούσε μόνο από snapshot: ο εξομοιωτής έβαζε τις τράπεζες
στη θέση τους και πηδούσε στο #0100. Αυτό δεν είναι μηχάνημα — είναι σκηνικό.
Ενα πραγματικό 6128 ξεκινά με BASIC, AMSDOS, αναμμένα ROM και μια δισκέτα, και
όλα όσα το snapshot έστηνε δωρεάν πρέπει να τα κάνει ο φορτωτής.

Τι ελέγχεται:

  0. ΤΟ ΜΕΝΟΥ ΤΟΥ ΠΛΑΝΗΤΗ (βήμα 128, πάνω σε κομμάτι κόσμου από το 130).
     Πριν από το φόρτωμα ο φορτωτής ρωτά ποιον κόσμο: τυχαίο ή έναν από
     τους τέσσερις του §5.7, με μία γραμμή περιγραφής για τη διαλεγμένη. Η
     οθόνη είναι byte προς byte του tools/menuworld.py για τον κόσμο που
     διάλεξε ο R (mw_k) και τη γραμμή που περιμένουμε, και τα χρώματά της
     η παλέτα του παιχνιδιού με τα τέσσερα του πλανήτη του κόσμου (από το
     framebuffer του εξομοιωτή). Πέντε εκκινήσεις με άλλη αναμονή πριν από
     το RUN δείχνουν άλλους κόσμους, καθένας σωστός. Τα βελάκια και το
     χειριστήριο κινούν την επιλογή, και γυρίζουν από τον πάτο στην κορυφή
     και ανάποδα. Ενα RETURN που κρατιέται από το RUN"HABITAT δεν διαλέγει
     μόνο του (αρνητικό: το mn_prev να ξεκινά από 0). Κάθε επιλογή φτάνει
     στο worldinfo: ο πλανήτης που διάλεξε ο παίκτης, και ο τυχαίος από τον
     R όπως πριν, άλλος για άλλη αναμονή. Και ο κώδικας του seed στη
     γεννήτρια, μόνος του, για 150 περιπτώσεις: αλλάζει μόνο τα δύο κάτω
     bits του L, δεν βγάζει ποτέ μηδέν, και ο πλανήτης μένει ο διαλεγμένος
     (τρία αρνητικά).
  1. Το RUN"HABITAT φτάνει ΜΕΣΑ στον κώδικα του παιχνιδιού. Δύο εκδοχές του
     φορτωτή δεν έτρεξαν ποτέ ούτε μια εντολή (τα ROM σκεπάζουν το #0000-#3FFF
     και το #C000-#FFFF) και μια τρίτη κόλλησε στο «Press PLAY then any key»
     (το AMSDOS ξεκαρφώνεται όταν το BASIC τρέχει δυαδικό). Καμία δεν φαινόταν
     στην οθόνη ως σφάλμα.
  1β. Η ΟΘΟΝΗ ΤΗΣ ΦΟΡΤΩΣΗΣ (βήμα 130): ανά 10 frames ως το παιχνίδι, ο ίδιος
     κόσμος με το πάνελ της φόρτωσης byte προς byte, με τη μπάρα όσο τη
     δείχνει η ίδια η οθόνη. Η μπάρα δεν γυρίζει ποτέ πίσω, τα αρχεία τη
     γεμίζουν ως το BAR_FILES πριν ανάψει το BUILDING THE WORLD, και η
     γεννήτρια μόνο μετά, ως το τέλος.
  2. Η κατάσταση εκκίνησης του §10.1 είναι εκεί — δηλαδή έτρεξε το game_new
     ΚΑΙ τα δεδομένα της τράπεζας 2 μεταφέρθηκαν σωστά από το πρόχειρο.
  3. Το HUD γράφτηκε, άρα ο renderer βρήκε τα γραφικά του σε 6 και 7.
  3β. Ο κώδικας του τροχού (βήμα 92): το B6CODE.BIN κάθεται στη δέσμευση
     b6code της τράπεζας 6, byte προς byte όπως βγήκε από το build. Το
     BANK6.BIN την έχει άδεια, οπότε ένας φορτωτής που ξεχνά το αρχείο αφήνει
     μηδενικά εκεί που πηδά το πρώτο ρομπότ. Από το βήμα 110 εκτός από τα
     τέσσερα bytes που γράφουν οι ανάγκες όσο τρέχει το παιχνίδι.
  3δ. Κανένα out (c),c στα αρχεία του b6code (βήμα 110): τρέχουν από το
     παράθυρο, και μια άλλη τράπεζα εκεί θα έφερνε την επόμενη εντολή από
     αυτήν. Αρνητικό: το mt_ground του βήματος 109.
  4. Ο κόσμος είναι ΠΑΡΑΓΜΕΝΟΣ: η γεννήτρια έτρεξε ως ξεχωριστό φόρτωμα και
     γέμισε την τράπεζα 4. Το snapshot φορτώνει έτοιμο επίπεδο· ο δίσκος δεν
     έχει τέτοιο αρχείο.
  5. Το πρόχειρο του φορτωτή (βήμα 86). Τα δεδομένα της τράπεζας 2 περιμένουν
     στη βασική τράπεζα 1, εκεί που θα σταθεί το DIST, και ο κώδικάς της στην
     τράπεζα 5, εκεί που θα σταθεί το NEXTHOP. Τη στιγμή που το επίμετρο
     πηδά στο #0100 (δεύτερο φόρτωμα, πιασμένο με βήματα 10 µs): η τράπεζα 2,
     οι μηχανές και τα εικονίδια είναι byte προς byte όπως βγήκαν από το
     build, και τα δύο πρόχειρα μηδέν, όπως στο snapshot. Αρνητικό: ένας
     δίσκος με τα δύο σβησίματα του επιμέτρου κομμένα αφήνει γραφικά και
     κώδικα σε αυτά. Από το βήμα 102 η BANK1.BIN αρχίζει στο OV_LOAD, με τον
     κώδικα των τρυπών του DIST κάτω από τα εικονίδια, και το DIST σβήνεται ως
     εκεί.
  6. Ο ΔΙΚΟΣ ΜΑΣ ΑΝΑΓΝΩΣΤΗΣ (βήμα 113). Ο φορτωτής διαβάζει τον κατάλογο και
     τους τομείς με τον ελεγκτή, όχι με το AMSDOS: κανένα αρχείο δεν πήγε στο
     AMSDOS (fl_off), η εκκίνηση κρατά ως 450 frames από την επιλογή του
     μενού (600 από το ENTER ως το βήμα 127), και τη στιγμή της
     παράδοσης ΟΛΑ τα αρχεία είναι στη θέση τους byte προς byte — και οι δύο
     εκτάσεις της BANK7.BIN (και της BANK6.BIN ως το βήμα 175, που την έκοψε
     στα 4 KB). Αρνητικά: η κεφαλίδα ένα byte λάθος, η δεύτερη έκταση από την
     πρώτη εγγραφή.
  7. Η ΕΦΕΔΡΕΙΑ. Ενας δίσκος όπου η PAGE2.BIN είναι τύπου 0 (BASIC, με σωστό
     άθροισμα): ο αναγνώστης την αρνείται, το AMSDOS τη φορτώνει, και η
     εκκίνηση φτάνει ίδια — με το AMSDOS να πιστεύει ότι η κεφαλή είναι στο
     track 0 και στο 1 (βήματα 128, 130). Αρνητικό: χωρίς την επιστροφή της
     κεφαλής στο track 0 πριν από το AMSDOS, με εκείνο στο «0».
  8. Το «εντάξει» του ελεγκτή: IC = 01 με EN είναι επιτυχία στο CPC (το TC
     δεν είναι συνδεδεμένο), για τον φορτωτή (fl_ok) και για το σώσιμο
     (fd_ok). Αρνητικά: ο έλεγχος ως το βήμα 112, και ένας που δέχεται το ND.
"""
import functools, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")

from sprites import load_map, load_bin                                  # noqa: E402
import world as W                                                       # noqa: E402
sys.path.insert(0, HERE)
import menuread as MR                                                   # noqa: E402
import menuworld as MW                                                  # noqa: E402

RASM = os.path.expanduser("~/rasm/rasm.exe")
DSK = os.path.join(ROOT, "build", "habitat.dsk")
FAIL = []


def check(ok, msg):
    print(("OK " if ok else "ΛΑΘΟΣ ") + msg)
    if not ok:
        FAIL.append(msg)


def build():
    for cmd, cwd in ((["mkdsk.py"], os.path.join(ROOT, "tools")),
                     (["plane.asm"], HERE)):
        if cmd[0].endswith(".py"):
            r = subprocess.run([sys.executable, os.path.join(cwd, cmd[0])],
                               capture_output=True, text=True)
        else:
            r = subprocess.run([RASM, cmd[0]], cwd=cwd,
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


def boot_syms():
    """Τα σύμβολα του φορτωτή και του μενού (build/boot.sym, build/menu.sym,
    από το tools/mkdsk.py)."""
    return MR.syms(ROOT)


def sector_at(dsk, track, sid):
    """Πού αρχίζει μέσα στην εικόνα ο τομέας sid του track (τυπικό .dsk, μία
    όψη): οι τομείς ενός track είναι με τη ΣΕΙΡΑ ΤΟΥ ΔΙΣΚΟΥ, πλεγμένοι."""
    size = int.from_bytes(dsk[0x32:0x34], "little")
    t = 0x100 + track * size
    off = t + 0x100
    for i in range(dsk[t + 0x15]):
        e = t + 0x18 + i * 8
        if dsk[e + 2] == sid:
            return off
        off += 128 << dsk[e + 3]
    return None


def file_sector(dsk, name, k=0):
    """Ο τομέας k ενός αρχείου, από τον κατάλογο: θέση μέσα στην εικόνα."""
    want = name.ljust(8).encode() + b"BIN"
    for si in range(4):
        d = sector_at(dsk, 0, 0xC1 + si)
        for e in range(d, d + 512, 32):
            if dsk[e] == 0 and bytes(b & 0x7F for b in dsk[e + 1:e + 12]) == want \
                    and dsk[e + 12] == k // 32:
                s = 2 * dsk[e + 16 + (k % 32) // 2] + (k & 1)
                return sector_at(dsk, s // 9, 0xC1 + s % 9)
    return None


def patch(dsk, pat, new):
    """Αλλάζει το ΜΟΝΑΔΙΚΟ σημείο της εικόνας με τα bytes pat. Γυρίζει πόσα
    βρέθηκαν· αλλάζει μόνο αν ήταν ένα."""
    n, at = 0, -1
    i = dsk.find(pat)
    while i >= 0:
        n, at = n + 1, i
        i = dsk.find(pat, i + 1)
    if n == 1:
        dsk[at:at + len(new)] = new
    return n


# Αντιγράφει όλη την τράπεζα 5 στην οθόνη, για να διαβαστεί με read_ram: το
# read_ram βλέπει μόνο τη βασική RAM. Σκοτώνει το παιχνίδι (jr $).
DUMP_B5 = bytes([0xF3,                      # di
                 0x01, 0xC5, 0x7F,          # ld bc,#7FC5
                 0xED, 0x49,                # out (c),c
                 0x21, 0x00, 0x40,          # ld hl,#4000
                 0x11, 0x00, 0xC0,          # ld de,#C000
                 0x01, 0x00, 0x40,          # ld bc,#4000
                 0xED, 0xB0,                # ldir
                 0x01, 0xC0, 0x7F,          # ld bc,#7FC0
                 0xED, 0x49,                # out (c),c
                 0x18, 0xFE])               # jr $
ENDGAME = 0x3FC0


def endgame(code):
    """Τα bytes του επιμέτρου μέσα στο boot.bin: από το «ld hl,SCRATCH_G2 ·
    ld de,PAGE2_CODE · ldir» ως το «jp #0100»."""
    boot = open(os.path.join(ROOT, "build", "boot.bin"), "rb").read()
    a = boot.find(bytes([0x21, 0x00, 0x40, 0x11, code & 0xFF, code >> 8,
                         0xED, 0xB0]))
    b = boot.find(bytes([0xC3, 0x00, 0x01]), a)
    return boot[a:b + 3] if a >= 0 and b >= 0 else b""


HANDOVER = {}                                   # ό,τι είδε το τελευταίο handover


AMSDOS_TRK = 0xA8A6     # το track όπου το AMSDOS 0.5 του 6128 πιστεύει ότι είναι η κεφαλή


def handover(m, disc, eg, amsdos=None):
    """Από το BASIC ως το ΠΡΩΤΟ μισό χιλιοστό του παιχνιδιού: τη μνήμη όπως
    την παραδίδει το επίμετρο, πριν γράψει το παιχνίδι οτιδήποτε στις
    τράπεζες 1, 2 και 5. Γυρίζει (βασική RAM, τράπεζα 5) ή None.

    Ο εξομοιωτής δεν έχει σημεία διακοπής. Το επίμετρο κρατά ~210 ms (40 KB
    ldir), οπότε ένα δείγμα ανά frame το πιάνει σίγουρα — όταν ο PC είναι
    μέσα του ΚΑΙ τα bytes του στο #3FC0 είναι τα δικά του (πριν αντιγραφεί
    εκεί, ο PC στο #3FC0 είναι η κάτω ROM). Από εκεί βήματα των 10 µs ως να
    βγει: λίγες εντολές του παιχνιδιού. ΟΧΙ «ο PC στην τράπεζα 0»: με βήματα
    των 0,2 ms το παιχνίδι είχε ήδη μπει στο hw_clear της τράπεζας 2."""
    m.run_frames(300)
    m.insert_disc(disc)
    m.type_text('|disc\n', hold_frames=4, gap_frames=8)
    m.run_frames(60)
    m.type_text('run"habitat\n', hold_frames=4, gap_frames=8)
    # Ο τυχαίος, όπως πριν από το μενού (βήμα 128)· τα frames από την επιλογή.
    if MR.pick(m, MR.syms(ROOT)) is None:
        return None
    # Πού πιστεύει το AMSDOS ότι άφησε την κεφαλή: στον τελευταίο τομέα του
    # LOADER.BIN. Με το amsdos γίνεται ό,τι λέει: 0 όπως όταν ο φορτωτής
    # χωρά στο track 0 (ως το βήμα 127, και ξανά από το 130), 1 όπως όταν
    # δεν χωρούσε (128-129)· από εδώ ως το fl_quit το AMSDOS δεν τρέχει.
    HANDOVER["amsdos_trk"] = m.peek(AMSDOS_TRK)
    if amsdos is not None:
        m.poke(AMSDOS_TRK, amsdos)

    def inside():
        return (ENDGAME <= m.pc < ENDGAME + len(eg)
                and m.read_ram(ENDGAME, len(eg)) == eg)
    # Το fl_off του φορτωτή όσο τρέχει η γεννήτρια (βήμα 113): το επίμετρο
    # γράφει μετά πάνω του τα δεδομένα της τράπεζας 2.
    flo = boot_syms()["FL_OFF"]
    HANDOVER["fl_off"] = None
    for f in range(3000):
        m.run_frames(1)
        if HANDOVER["fl_off"] is None and 0x8000 <= m.pc < 0x8E00:
            HANDOVER["fl_off"] = m.peek(flo)
        if inside():
            HANDOVER["frames"] = f + 1
            break
    else:
        return None
    for _ in range(30000):                       # 300 ms
        m.run_us(10)
        if not inside():
            break
    else:
        return None
    ram = m.read_ram(0, 0x10000)
    import ctypes, cpc
    b67 = [ctypes.string_at(ctypes.addressof(cpc._lib.cpcemu_ram_ptr(m._h, b).contents),
                            0x4000) for b in (6, 7)]
    m.run_code(0x3EC0, DUMP_B5, frames=8)        # 16 KB ldir = 86 ms
    return ram, m.read_ram(0xC000, 0x4000), b67[0], b67[1]


def held(m, disc, hold=400):
    """BASIC, |DISC και RUN"HABITAT, με το RETURN του RUN ΚΡΑΤΗΜΕΝΟ για hold
    frames: ως τότε ο φορτωτής έχει φορτωθεί και έχει γράψει το μενού. Γυρίζει
    την οθόνη τη στιγμή πριν αφεθεί το πλήκτρο."""
    from cpc import KEY_ENTER
    m.run_frames(300)                    # το BASIC θέλει τον χρόνο του
    m.insert_disc(disc)
    # Ο εξομοιωτής ξεκινά με κασέτα· σε 6128 με μονάδα ο δίσκος είναι το
    # προεπιλεγμένο και το |DISC περισσεύει. Δεν βλάπτει.
    m.type_text('|disc\n', hold_frames=4, gap_frames=8)
    m.run_frames(60)
    m.type_text('run"habitat', hold_frames=4, gap_frames=8)
    m.key_down(KEY_ENTER)
    m.run_frames(hold)
    ram = m.read_ram(0xC000, 0x4000)
    m.key_up(KEY_ENTER)
    return ram


G = MW.geom()


@functools.lru_cache(maxsize=None)
def ref_menu(k, sel):
    """Η οθόνη του μενού για τον κόσμο k με τη γραμμή sel (tools/menuworld.py)."""
    return bytes(MW.screen_menu(k, sel).to_screen_ram())


def ref_loading(k, sel, files, gen, lit):
    return bytes(MW.screen_loading(k, sel, files, gen, lit).to_screen_ram())


def ndiff(a, b):
    return sum(1 for x, y in zip(a, b) if x != y)


def bar_state(ram):
    """(bytes των αρχείων, bytes της γεννήτριας, αναμμένο το BUILDING THE
    WORLD) όπως τα δείχνει η οθόνη: η γραμμή 1 της μπάρας, και ο τρόπος των
    γραμμάτων στη σειρά WLD_ROW (tests/menuread.py)."""
    base = 0x800 + G["BAR_ROW"] * 80 + G["BAR_X0"]
    row = ram[base:base + G["BAR_W"]]
    files = sum(1 for b in row[:G["BAR_FILES"]] if b == G["BAR_INK"])
    gen = sum(1 for b in row[G["BAR_FILES"]:] if b == G["BAR_INK"])
    mode = MR.text(ram, G["WLD_ROW"], G["WLD_COL"], len(MW.BUILDING))[1]
    return files, gen, "d" not in mode


def fw_to_hw():
    """Ο πίνακας firmware -> hardware του src/hw.asm (fw_to_hw)."""
    src = open(os.path.join(ROOT, "src", "hw.asm"), encoding="utf-8").read()
    out = []
    for line in src[src.index("fw_to_hw:"):].splitlines()[1:4]:
        out += [int(v.strip().lstrip("#"), 16) for v in line.split("db")[1].split(";")[0].split(",")]
    return out


def colours(m, planets):
    """Τι δείχνει ο εξομοιωτής: για κάθε πλανήτη του planets, πόσα pixels του
    framebuffer διαφέρουν από ό,τι θα έδειχνε η μνήμη με την παλέτα του
    (hardware χρώματα, ένα pixel του MODE 0 = 4 του framebuffer). Η εικόνα
    βρίσκεται μέσα στο framebuffer από τη γραμμή της με τα περισσότερα
    χρώματα, με την παλέτα του πρώτου· None αν δεν βρέθηκε. Ο,τι δεν ζωγράφισε
    ο εξομοιωτής είναι 0 εκεί, όσο και το hardware χρώμα 0: μέτρημα ολόκληρου
    του framebuffer δεν θα έλεγε τίποτα."""
    hw = fw_to_hw()
    pens = m.decode_screen_ram(mode=0)
    fb = m.framebuffer()

    def image(planet):
        pen_hw = [hw[c] for c in MW.palette(planet)]
        return [bytes(pen_hw[p] for p in row for _ in range(4)) for row in pens]
    def bad(img, x0, y0):
        return sum(sum(a != b for a, b in zip(fb[(y0 + r) * 1024 + x0:(y0 + r) * 1024 + x0 + 640],
                                              img[r])) for r in range(200))
    # ΟΙ ΓΡΑΜΜΕΣ ΤΟΥ ΕΔΑΦΟΥΣ ΕΙΝΑΙ ΔΙΠΛΕΣ: η ίδια γραμμή βρίσκεται και μία
    # πάνω. Από όλες τις θέσεις όπου ταιριάζει, εκείνη με τα λιγότερα λάθη.
    want = image(planets[0])
    y = max(range(200), key=lambda r: sum(a != b for a, b in zip(want[r], want[r][1:])))
    at = [(fb[fy * 1024:(fy + 1) * 1024].find(want[y]), fy - y)
          for fy in range(y, len(fb) // 1024 - 200 + y + 1)]
    at = [(x0, y0) for x0, y0 in at if 0 <= x0 <= 1024 - 640]
    if not at:
        return None
    x0, y0 = min(at, key=lambda p: bad(want, *p))
    out = [bad(image(pl), x0, y0) for pl in planets]
    return out


def worldinfo(m, b6off):
    """(seed, πλανήτης) από την τράπεζα 6."""
    import cpc
    b6 = cpc._lib.cpcemu_ram_ptr(m._h, 6)
    return b6[b6off] | (b6[b6off + 1] << 8), b6[b6off + 2]


def wi_byte3(m, b6off):
    """Το τέταρτο byte του worldinfo: η έκδοση της γεννήτριας, και το bit 7 για
    τον κόσμο του tutorial (βήμα 149, src/gen.asm)."""
    import cpc
    return cpc._lib.cpcemu_ram_ptr(m._h, 6)[b6off + 3]


def tu_seed():
    """Το TU_SEED του src/gen.asm."""
    import re
    src = open(os.path.join(ROOT, "src", "gen.asm"), encoding="utf-8").read()
    return int(re.search(r"^TU_SEED\s+equ\s+#([0-9A-Fa-f]+)", src, re.M).group(1), 16)


def to_gen(m, b6off, limit=900):
    """Τρέχει ως να μπει η γεννήτρια (που γράφει το worldinfo στην αρχή της)·
    γυρίζει (seed, πλανήτης) ή None."""
    for _ in range(limit):
        m.run_frames(1)
        if 0x8000 <= m.pc < 0x8E00:
            m.run_frames(1)
            return worldinfo(m, b6off)
    return None


def main():
    sym, g = build()
    bs = boot_syms()
    from cpc import CPC
    lay0 = {p[0]: int(p[2].lstrip("#"), 16) for p in (
        line.split() for line in open(os.path.join(ROOT, "build", "layout.asm"),
                                      encoding="utf-8")) if len(p) >= 3 and p[1] == "equ"}
    wi6 = lay0["G_worldinfo"] - 0x4000

    # --- 0. το μενού του πλανήτη (βήμα 128, πάνω σε κόσμο από το 130) -------
    # ΤΟ RETURN ΤΟΥ RUN ΚΡΑΤΙΕΤΑΙ ως να γραφτεί το μενού. Το μενού μετράει
    # μόνο ό,τι πατήθηκε ΑΦΟΥ ξεκίνησε· αλλιώς ένα δάχτυλο αργό στο RETURN θα
    # διάλεγε τον τυχαίο χωρίς να δει ο παίκτης την ερώτηση.
    m = CPC()
    ram = held(m, DSK)
    k0 = m.peek(bs["MW_K"])
    nd = ndiff(ram, ref_menu(k0, 0))
    check(nd == 0 and m.peek(bs["MN_PREV"]) == 4,
          f"με το RETURN κρατημένο 400 frames το μενού περιμένει: ο κόσμος {k0} "
          f"με το RANDOM διαλεγμένο, {nd} bytes διαφορετικά από το "
          f"tools/menuworld.py, mn_prev #{m.peek(bs['MN_PREV']):02X}")
    # Μετά το #FF του mn_ktab: mn_sel 0, mn_prev #FF, mf_y 0 (src/menu.asm).
    dsk = bytearray(open(DSK, "rb").read())
    n = patch(dsk, bytes([76, 4, 77, 4, 0xFF, 0, 0xFF, 0]),
              bytes([76, 4, 77, 4, 0xFF, 0, 0, 0]))
    k = CPC()
    bad = held(k, bytes(dsk)) if n == 1 else None
    # Το mw_k ζει στο MENU.BIN (&4000), που τα αρχεία του παιχνιδιού το έχουν
    # ήδη σκεπάσει όταν το μενού έφυγε: ως το βήμα 130 εκεί έτυχε αριθμός
    # κάτω από 32. Η οθόνη συγκρίνεται με το μενού ΚΑΘΕ κόσμου.
    nd_bad = min(ndiff(bad, ref_menu(j, 0)) for j in range(MW.MW_N)) if bad else 0
    del k
    check(n == 1 and nd_bad > 0,
          f"ΑΡΝΗΤΙΚΟ: με το mn_prev να ξεκινά από 0 ({n} σημείο) το κρατημένο "
          f"RETURN διαλέγει μόνο του και το μενού "
          f"{'έφυγε' if nd_bad else 'έμεινε'} (τουλάχιστον {nd_bad} bytes "
          f"διαφορετικά από καθέναν από τους {MW.MW_N} κόσμους)")
    wait = MR.wait(m, bs)
    nd = ndiff(m.read_ram(0xC000, 0x4000), ref_menu(k0, 0))
    seed, pl = MW.worlds()[k0][:2]
    check(wait is not None and nd == 0,
          f"το μενού: ο κόσμος {k0} (seed {seed:04X}, {MW.MENU[pl + 1][0]}), ο "
          f"τίτλος, «{MW.CHOOSE}», οι {len(MW.MENU)} γραμμές με το RANDOM ανάποδα, η "
          f"περιγραφή του, τα πλήκτρα — {nd} bytes διαφορετικά")
    # ΤΑ ΧΡΩΜΑΤΑ: η μνήμη μόνη της δεν λέει τι βλέπει ο παίκτης. Το mw_inks
    # βάζει την παλέτα του παιχνιδιού και τα τέσσερα του πλανήτη του κόσμου
    # (pal_terrain)· ο εξομοιωτής ζωγραφίζει hardware χρώματα.
    # Δύο frames ακόμη: το μενού είναι «έτοιμο» μία φορά μετά το mw_inks, και
    # το τελευταίο frame του εξομοιωτή μπορεί να είναι μισό με τη μαύρη παλέτα.
    m.run_frames(2)
    bad = colours(m, (pl, (pl + 1) & 3))
    check(bad is not None and bad[0] == 0 and bad[1] > 0,
          f"τα χρώματα του μενού είναι του πλανήτη {pl}: "
          + ("η εικόνα δεν βρέθηκε στο framebuffer" if bad is None else
             f"{bad[0]} pixels διαφορετικά από τη μνήμη με την παλέτα του· "
             f"ΑΡΝΗΤΙΚΟ: με του πλανήτη {(pl + 1) & 3} {bad[1]}"))
    moves = []
    # ΕΞΙ ΓΡΑΜΜΕΣ από το βήμα 149: από την κορυφή πάνω είναι το TUTORIAL, και ένα
    # πάνω ακόμη η BARREN MOON — όπου μένει, για το FIRE πιο κάτω.
    last = len(MW.MENU) - 1
    for keys, joy, want in (("dd", False, 2), ("uuu", False, last),
                            ("d", True, 0), ("u", True, last), ("u", False, last - 1)):
        MR.press(m, keys, joy)
        scr0 = m.read_ram(0xC000, 0x4000)
        got = next((s for s in range(len(MW.MENU)) if ndiff(scr0, ref_menu(k0, s)) == 0),
                   None)
        moves.append((keys, joy, want, got))
    check(all(w == i for _, _, w, i in moves),
          "η επιλογή κινείται, με την περιγραφή της: " + ", ".join(
              f"{'χειριστήριο' if j else 'βελάκια'} {k} -> "
              f"{MR.ROWS[i] if i is not None else 'ΧΑΛΑΣΜΕΝΟ'}"
              f"{'' if w == i else ' (ΕΠΡΕΠΕ ' + MR.ROWS[w] + ')'}"
              for k, j, w, i in moves))
    MR.press(m, "f")                     # BARREN MOON, ο πλανήτης 3

    # --- 1. φτάνει το παιχνίδι; ------------------------------------------
    # Ο μετρητής προγράμματος ΔΕΝ είναι απόδειξη: το #0100-#37AD του παιχνιδιού
    # είναι και η περιοχή της κάτω ROM, οπότε ένα κολλημένο firmware δείχνει
    # μέσα στο παιχνίδι. Το σημάδι είναι η ΜΝΗΜΗ: τα αποθέματα του §10.1 δεν
    # υπάρχουν πουθενά στον δίσκο — τα γράφει το game_new όταν τρέξει.
    def w16(a):
        return m.peek(a) | (m.peek(a + 1) << 8)

    # Στον δρόμο κρατάμε και την ΟΘΟΝΗ: ως το βήμα 21 ο παίκτης κοίταζε μισό
    # λεπτό το «Ready» του BASIC (§13.2). Από το βήμα 130 βλέπει τον κόσμο του
    # μενού με το πάνελ της φόρτωσης και μία μπάρα — και αυτό ελέγχεται εδώ,
    # γιατί υπάρχει μόνο στον δρόμο του δίσκου: το snapshot δεν περνά ποτέ από
    # τον φορτωτή.
    def scr():
        return m.read_ram(0xC000, 0x4000)

    def sample():
        """(frames, αρχεία, γεννήτρια, αναμμένο, bytes διαφορετικά από την
        αναφορά). Ενα δείγμα μπορεί να πέσει ΜΕΣΑ στο γέμισμα ενός byte της
        μπάρας (έξι γραμμές, μία μία): τότε άλλο ένα, 200 µs μετά. Ή μέσα στο
        άναμμα του BUILDING THE WORLD, που ο φορτωτής το κάνει γραμμή-γραμμή σε
        όλο το πλάτος του (bt_lit): τότε ως τέσσερα ακόμη, ανά 1 ms. Στο βήμα
        149 ο R έδωσε άλλον κόσμο και ένα δείγμα έπεσε εκεί, με τις γραμμές 0-3
        αναμμένες και τις 4-5 όχι ακόμη: 53 bytes, και το επόμενο το ίδιο."""
        for again in range(6):
            ram = scr()
            st = bar_state(ram)
            nd = ndiff(ram, ref_loading(k0, 4, *st))
            if nd == 0 or again == 5:
                return (frames,) + st + (nd,)
            m.run_us(200 if again == 0 else 1000)

    running, frames, samples, tones = False, 0, [], []
    mode_pl = m.peek(bs["BT_PL"])
    fl_seen = None
    # ΑΝΑ 10 FRAMES από το βήμα 112: η γεννήτρια κρατά πια ~5 s, και ανά 30 τα
    # δείγματα της μουσικής ήταν δεκαπέντε — τέσσερις νότες, όχι πέντε.
    for _ in range(360):
        m.run_frames(10)
        frames += 10
        started = w16(g + 2) == 100 and m.peek(g + 58) == 6      # §10.1 (βήμα 120)
        # ΜΟΝΟ ΟΣΟ ΦΟΡΤΩΝΕΙ: μόλις ξεκινήσει το παιχνίδι, η οθόνη είναι του
        # κάδρου. Το όριο ήταν σταθερός αριθμός frames και έσπασε μόλις μπήκε
        # ένα ένατο αρχείο στον δίσκο (§4.2).
        if not started:
            samples.append(sample())
        # Ο φορτωτής ζει ακόμη όσο τρέχει η γεννήτρια (τον σβήνει το επίμετρο):
        # τότε λέει αν κάποιο αρχείο πήγε στο AMSDOS (βήμα 113).
        if fl_seen is None and not started and 0x8000 <= m.pc < 0x8E00:
            fl_seen = m.peek(bs["FL_OFF"])
        # Και ο ΗΧΟΣ της αναμονής (§9.5): η γεννήτρια έχει δικό της παίκτη,
        # γιατί ο ήχος του παιχνιδιού ζει στην τράπεζα 2 που δεν υπάρχει ακόμη.
        # Δειγματοληψία ανά 10 frames· μια νότα κρατά ~30, οπότε περνούν όλες
        # από μπροστά μας έστω μία φορά.
        if not started:
            r = m.psg_regs()
            tones.append((r[0] | ((r[1] & 15) << 8), r[8], r[10]))
        if started:
            running = True
            break
    check(running, f"το RUN\"HABITAT έφτασε στο game_new "
                   f"(PC=#{m.pc:04X}, τροφή {w16(g + 2)})")

    # --- 1δ. ο δικός μας αναγνώστης (βήμα 113) ----------------------------
    # Ως το βήμα 112 όλα τα αρχεία περνούσαν από το AMSDOS: 1.460 frames, τα
    # 1.180 τα αρχεία. Το ΤΑΒΑΝΙ είναι ο έλεγχος ότι δεν ξαναγύρισαν εκεί
    # σιωπηλά — η εφεδρεία φορτώνει σωστά, άρα μόνο ο χρόνος θα το έδειχνε.
    check(fl_seen == 0,
          f"κανένα αρχείο δεν πήγε στο AMSDOS: fl_off = {fl_seen} όσο τρέχει η "
          f"γεννήτρια")
    check(frames <= 450,
          f"εκκίνηση {frames} frames από την επιλογή του μενού ως την αποικία, "
          f"ταβάνι 450 (από το ENTER: 1.460 ως το βήμα 112, ~570 ως το 127)")

    # --- 1β. η οθόνη φόρτωσης (βήμα 130) -----------------------------------
    # Ο κόσμος του μενού μένει, και στο πάνελ ο κόσμος που διάλεξε, LOADING,
    # η μπάρα και το BUILDING THE WORLD: σε ΚΑΘΕ δείγμα byte προς byte όπως η
    # αναφορά με τη μπάρα που δείχνει η ίδια η οθόνη. Ως ότου η γεννήτρια
    # σχεδόν τελειώσει· μετά το επίμετρο και το game_new παίρνουν την οθόνη,
    # και το πρώτο δείγμα που δεν ταιριάζει είναι εκείνο.
    # Η μπάρα είναι το ΜΟΝΟ πράγμα που κινείται επί 8 δευτερόλεπτα: δεν
    # γυρίζει ΠΟΤΕ πίσω, τα αρχεία τη γεμίζουν ως το BAR_FILES ΠΡΙΝ ανάψει το
    # BUILDING THE WORLD, και η γεννήτρια μόνο μετά. Η ΦΑΣΗ ΤΗΣ
    # ΔΕΙΓΜΑΤΟΛΗΨΙΑΣ ΑΛΛΑΖΕΙ ΜΕ ΚΑΘΕ ΑΛΛΑΓΗ ΜΕΓΕΘΟΥΣ ΤΟΥ ΚΩΔΙΚΑ (ως το βήμα
    # 129 το «τέρμα» ήταν ≥ 56 από 64 για τον ίδιο λόγο): το τέλος της
    # γεννήτριας είναι «τουλάχιστον BAR_GEN − 2».
    take = next((i for i, sm in enumerate(samples) if sm[4]), len(samples))
    shown = samples[:take]
    end_ok = take == len(samples) or (shown and shown[-1][2] >= G["BAR_GEN"] - 2)
    mono = all(a[1] <= b[1] and a[2] <= b[2] and a[3] <= b[3]
               for a, b in zip(shown, shown[1:]))
    order = all((not lit or fi == G["BAR_FILES"]) and (not ge or lit)
                for _, fi, ge, lit, _ in shown)
    top_f = max((sm[1] for sm in shown), default=0)
    top_g = max((sm[2] for sm in shown), default=0)
    steps = len({sm[1:4] for sm in shown})
    check(shown and end_ok and mono and order and shown[0][1] < G["BAR_FILES"]
          and top_f == G["BAR_FILES"] and top_g >= G["BAR_GEN"] - 2 and steps >= 10,
          f"η οθόνη φόρτωσης σε {len(shown)} δείγματα, όλα byte προς byte "
          f"(ο κόσμος {k0}, BARREN MOON, LOADING): η μπάρα από "
          f"{shown[0][1] if shown else '-'} σε {top_f}/{G['BAR_FILES']} με τα αρχεία, "
          f"μετά BUILDING THE WORLD αναμμένο και {top_g}/{G['BAR_GEN']} με τη "
          f"γεννήτρια, {steps} διαφορετικές εικόνες, "
          f"{'μονότονα' if mono else 'ΜΕ ΠΙΣΩΓΥΡΙΣΜΑ'}"
          f"{'' if order else ', ΜΕ ΛΑΘΟΣ ΣΕΙΡΑ'}"
          + ("" if end_ok else f" — ΤΟ ΔΕΙΓΜΑ {samples[take]} ΔΙΑΦΕΡΕΙ"))

    # --- 1γ. η μουσική της αναμονής --------------------------------------
    pitches = {t[0] for t in tones if t[0]}
    loud = sum(1 for t in tones if t[1] or t[2])
    check(len(pitches) >= 5 and loud >= 10,
          f"η γεννήτρια παίζει: {len(pitches)} διαφορετικές νότες σε "
          f"{len(tones)} δείγματα, {loud} με ένταση")
    # και ΣΩΠΑΙΝΕΙ όταν τελειώσει: το παιχνίδι ξεκινά χωρίς κατάλοιπο
    m.run_frames(60)
    r = m.psg_regs()
    check(r[8] == 0 and r[9] == 0 and r[10] == 0,
          f"και σωπαίνει πριν το παιχνίδι: εντάσεις {r[8:11]}")
    if not running:
        m.screenshot(os.path.join(ROOT, "build", "disc.png"), aspect=True)
        return 1
    m.run_frames(180)                    # αφήνουμε τη σχεδίαση να τελειώσει

    # --- 2. η κατάσταση εκκίνησης ----------------------------------------
    stock = [w16(g + i * 2) for i in range(7)]
    pop = m.peek(g + 58)
    # Από το βήμα 87 δίπλα στο σκάφος, με τα υλικά της παλιάς αποικίας στο
    # φορτίο: μέταλλο 189 και βιοπλαστικό 107 αντί για 75 και 45. Από το 120
    # 100 τρόφιμα, 12 ανταλλακτικά και έξι άποικοι (40, 4 και τέσσερις ως τότε),
    # και από το 133 βιοπλαστικό 137.
    check(50 <= stock[0] <= 60 and stock[1] == 100 and stock[2] == 60
          and stock[3] == 189 and stock[4] == 137 and stock[6] == 12 and pop == 6,
          f"§10.1 από τον δίσκο: {stock} πληθυσμός {pop}")

    # --- 3. το HUD είναι γραμμένο ----------------------------------------
    sys.path.insert(0, HERE)
    import hudread
    row2 = hudread.text(m, sym, 2)
    check(row2.startswith("6/6 SOL"), f"το HUD σχεδιάστηκε: |{row2}|")     # χωρίς «POP » (βήμα 173)

    # --- 3β. ο κώδικας του τροχού στην τράπεζα 6 (βήμα 92) ----------------
    # Το BANK6.BIN του pack.py έχει τη δέσμευση b6code ΑΔΕΙΑ· τον κώδικα (τα
    # ρομπότ, src/bots.asm) τον φέρνει το B6CODE.BIN, και ο φορτωτής πρέπει να
    # τον ρίξει από πάνω. Αν το ξεχάσει, το πρώτο ρομπότ πηδά σε μηδενικά —
    # και κανένα snapshot δεν θα το έδειχνε.
    import ctypes, cpc
    code = open(os.path.join(ROOT, "build", "b6code.bin"), "rb").read()
    b6 = cpc._lib.cpcemu_ram_ptr(m._h, 6)
    lay = {p[0]: int(p[2].lstrip("#"), 16) for p in (
        line.split() for line in open(os.path.join(ROOT, "build", "layout.asm"),
                                      encoding="utf-8")) if len(p) >= 3 and p[1] == "equ"}
    at = lay["G_b6code"]
    got = ctypes.string_at(ctypes.addressof(b6.contents) + at - 0x4000, len(code))
    # ΟΣΑ ΓΡΑΦΕΙ ΤΟ ΠΑΙΧΝΙΔΙ ΟΣΟ ΤΡΕΧΕΙ (βήμα 110): οι ανάγκες ζουν από τότε
    # εδώ, με μία μεταβλητή και τον τελεστή του ens_call (src/needs.asm· το
    # nd_room έφυγε στο βήμα 120, το δωμάτιο μένει στον B). Το δείγμα
    # παίρνεται αφού τρέξει ο τροχός, οπότε αυτά δεν είναι πια του build. Από
    # το βήμα 176 και το ef_pmp του κύκλου ροής (src/flow.asm: το ρεύμα των
    # αντλιών)· σε άδεια αποικία μένει 0, αλλά δεν είναι του build.
    live = {sym["ND_I"], sym["ENS_CALL"] + 1, sym["ENS_CALL"] + 2,
            sym["EF_PMP"], sym["EF_PMP"] + 1}
    labs = sorted((v, k) for k, v in sym.items() if at <= v < at + len(code))
    bad = [at + i for i, (x, y) in enumerate(zip(got, code)) if x != y and at + i not in live]
    where = [next(k for v, k in reversed(labs) if v <= a) + f"+{a - next(v for v, k in reversed(labs) if v <= a)}"
             for a in bad[:4]]
    check(len(code) > 64 and not bad and sym["BOT_TICK"] == at,
          f"ο κώδικας του τροχού ήρθε από τον δίσκο στην τράπεζα 6: {len(code)} bytes στο "
          f"#{at:04X}, {len(bad)} διαφορετικά {where} (έξω από τα {len(live)} που γράφει όσο τρέχει)")

    # --- 3δ. κανένα out (c),c στον κώδικα της τράπεζας 6 (βήμα 110) ----------
    # Ο,τι τρέχει από το b6code τρέχει από το παράθυρο &4000-&7FFF· μια άλλη
    # τράπεζα εκεί και η επόμενη εντολή έρχεται από αυτήν. Η πρώτη σουίτα του
    # βήματος 110 το βρήκε: το mt_ground σελιδοποιούσε τον κόσμο και το
    # nd_nearest το DIST, και το test_needs έβρισκε το PC στο &DAF6. Τα αρχεία
    # του b6code βγαίνουν από το src/main.asm, και κανένα δεν γράφει στη Gate
    # Array· ό,τι το χρειάζεται ζει στο src/b6out.asm.
    import re
    main_src = open(os.path.join(ROOT, "src", "main.asm"), encoding="utf-8").read()
    block = main_src[main_src.index("org     G_b6code"):main_src.index("zz_b6code_end:")]
    b6files = re.findall(r'^\s+include\s+"([^"]+)"', block, re.M)

    def pages(text):
        return [n + 1 for n, line in enumerate(text.splitlines())
                if re.match(r"\s+out\s+\(c\),c", line)]
    hits = [(f, pages(open(os.path.join(ROOT, "src", f), encoding="utf-8").read()))
            for f in b6files]
    hits = [(f, n) for f, n in hits if n]
    check(len(b6files) >= 7 and not hits,
          f"κανένα out (c),c στα {len(b6files)} αρχεία του b6code ({', '.join(b6files)})"
          + (f" — {hits}" if hits else ""))
    # ΑΡΝΗΤΙΚΟ: το mt_ground όπως ήταν ως το βήμα 109
    old = ("        push    bc\n        ld      bc,GA_PORT + PAGE_B4\n"
           "        out     (c),c\n        ld      a,(hl)\n")
    check(pages(old) == [3], "ΑΡΝΗΤΙΚΟ: το mt_ground του βήματος 109 θα πιανόταν")

    # --- 3γ. ο κώδικας των τρυπών (βήματα 101-102, 155) ---------------------
    # Τον φέρνει η BANK1.BIN στο OV_LOAD, κάτω από τα εικονίδια, και το
    # ov_install τον μοιράζει στις τρύπες στην εκκίνηση. Ως το βήμα 101
    # ερχόταν με την PAGE2.BIN στο GH_BUF· ένας δίσκος που τον ξεχνά αφήνει
    # μηδενικά εκεί όπου πηδά το πρώτο M, D, FIRE. Από το βήμα 103 και το
    # σώσιμο με τον οδηγό του δίσκου (build/ovl2.bin): το ίδιο το παιχνίδι το
    # χρειάζεται για να σώσει. Από το 108 η οθόνη βοήθειας (build/ovl3.bin),
    # από το 149 το tutorial (build/ovl4.bin) και οι γραμμές του. ΑΠΟ ΤΟ ΒΗΜΑ
    # 155 σε τρία σημεία (tests/ovmap.py): η κατεδάφιση στις στήλες 112-127 του
    # NEXTHOP της τράπεζας 5, το σώσιμο και η βοήθεια στις 112-127 των
    # γραμμών θόλων του DIST, και το OV_R1 ολόκληρο (build/ovr1.bin) στο
    # #6000: οι χειριστές της κατεδάφισης, οι γραμμές και ο κώδικας του
    # tutorial.
    import ovmap as OV
    got = {n: (OV.read(m, sym, n), OV.pieces(sym)[n][3]) for n in ("dm", "save", "help", "r1")}
    check(len(got["dm"][1]) > 512 and len(got["save"][1]) > 512 and len(got["help"][1]) > 128
          and len(got["r1"][1]) > 512 + 256 and all(x == y for x, y in got.values()),
          "ο κώδικας της κατεδάφισης, του σωσίματος, της βοήθειας και του tutorial ήρθε "
          "από τον δίσκο στις τρύπες: "
          + ", ".join(f"{n} {len(w)} bytes ({sum(a != b for a, b in zip(h, w))} διαφορετικά)"
                      for n, (h, w) in got.items()))

    # --- 4. ο κόσμος είναι παραγμένος ------------------------------------
    m.run_code(0x3EC0, open(os.path.join(ROOT, "build", "plane.bin"), "rb").read())
    m.run_frames(2)
    sample = bytes(m.read_ram(0x3F00, 256))
    classes = {W.cls_of(b) for b in sample}
    check(len(classes) >= 3,
          f"το επίπεδο έχει ποικιλία εδάφους: {sorted(classes)} σε 256 δείγματα")
    check(max(classes) <= W.FOUNDATION,
          f"καμία κλάση εκτός ορίων: {sorted(classes)}")
    ref = open(os.path.join(ROOT, "build", "world_new.bin"), "rb").read()
    check(sample != bytes(ref[i] for i in range(0, 16384, 64)),
          "ο κόσμος ΔΕΝ είναι το έτοιμο επίπεδο του snapshot — τρέχει η γεννήτρια")
    # ΚΑΙ ΕΙΝΑΙ Ο ΚΟΣΜΟΣ ΤΟΥ SEED ΤΟΥ (βήμα 112). Η γεννήτρια του δίσκου είναι
    # το gen.asm, με τη μπάρα και τη μουσική της· το tests/test_worldgen.py
    # ελέγχει το ίδιο worldgen.asm μέσα στη σκαλωσιά του. Εδώ: το seed και ο
    # πλανήτης από το worldinfo της τράπεζας 6, και όλο το επίπεδο της 4
    # απέναντι στο tools/worldgen_ref.py.
    import worldgen_ref
    b4 = cpc._lib.cpcemu_ram_ptr(m._h, 4)
    b6 = cpc._lib.cpcemu_ram_ptr(m._h, 6)
    wi = int(open(os.path.join(ROOT, "build", "layout.asm"), encoding="utf-8").read()
             .split("G_worldinfo")[1].split("#")[1].split()[0], 16) - 0x4000
    seed, planet = b6[wi] | (b6[wi + 1] << 8), b6[wi + 2]
    plane = bytes(b4[k] for k in range(16384))
    # Ο πλανήτης ΒΓΑΙΝΕΙ από το seed (src/gen.asm, §5.7): (hi ^ lo) & 3. Ως το
    # βήμα 111 το byte του worldinfo ήταν #C6 σε κάθε εκκίνηση από δίσκο.
    nd = -1
    if planet == ((seed >> 8) ^ seed) & 3:
        want = bytes(worldgen_ref.generate(seed, planet).buf)
        # Τα bits 4-5 είναι η κατοχή (tools/world.py), και το game_new έχει ήδη
        # γράψει εκεί το σκάφος, 2 x 2 στο κέντρο: η σύγκριση τα αφήνει έξω. Το
        # ότι η γεννήτρια τα αφήνει μηδέν το ελέγχει το tests/test_worldgen.py.
        nd = sum(1 for x, y in zip(plane, want) if (x ^ y) & 0xCF)
    check(planet == 3 and mode_pl == 3,
          f"το BARREN MOON του μενού: bt_pl {mode_pl}, πλανήτης {planet} στο worldinfo")
    check(nd == 0, f"το επίπεδο του δίσκου είναι ο κόσμος του seed {seed:04X}, "
                   f"πλανήτης {planet} όπως τον γράφει το worldinfo, byte προς byte: "
                   + (f"{nd} διαφορετικά" if nd >= 0 else
                      f"ο πλανήτης του seed είναι {((seed >> 8) ^ seed) & 3}"))

    m.screenshot(os.path.join(ROOT, "build", "disc.png"), aspect=True)

    # --- 0β. κάθε επιλογή ως το worldinfo (βήμα 128) ----------------------
    # Ο,τι διάλεξε ο παίκτης το βρίσκει η γεννήτρια στο A και το γράφει στο
    # worldinfo με το seed. Ο τυχαίος δύο φορές, με 37 frames αναμονής
    # παραπάνω τη δεύτερη: ο R τρέχει όσο περιμένει το μενού, και ο κόσμος
    # αλλάζει όπως άλλαζε και πριν.
    # ΚΑΙ Ο ΚΟΣΜΟΣ ΤΟΥ ΜΕΝΟΥ (βήμα 130): ο φορτωτής τον διαλέγει με τον R πριν
    # από το μενού, άρα αλλάζει με την ώρα του RUN — εδώ pre frames ακόμη στο
    # BASIC. Σε ένα 6128 ο R στο ENTER είναι ό,τι έτυχε. Κάθε εκκίνηση δείχνει
    # τον δικό της κόσμο, byte προς byte.
    # ΚΑΙ ΤΟ TUTORIAL (βήμα 149): ο πλανήτης 4 του MR.pick, η έκτη γραμμή. Το
    # seed του είναι πάντα το TU_SEED, η σελήνη, και το bit 7 του τέταρτου byte
    # του worldinfo το λέει στο παιχνίδι· σε καμία άλλη επιλογή.
    picks = []
    TU = tu_seed()
    for pl, joy, extra, pre in ((0, True, 0, 0), (1, False, 0, 7), (2, True, 0, 19),
                                (None, False, 0, 31), (None, False, 37, 31),
                                (4, False, 0, 43)):
        k = CPC()
        k.run_frames(300 + pre)
        k.insert_disc(DSK)
        k.type_text('|disc\n', hold_frames=4, gap_frames=8)
        k.run_frames(60)
        k.type_text('run"habitat\n', hold_frames=4, gap_frames=8)
        kw = nd = None
        if MR.wait(k, bs) is not None:
            kw = k.peek(bs["MW_K"])
            nd = ndiff(k.read_ram(0xC000, 0x4000), ref_menu(kw, 0))
            k.run_frames(extra)
        got = to_gen(k, wi6) if MR.pick(k, bs, pl, joy) is not None else None
        if got:
            got = got + (wi_byte3(k, wi6),)
        del k
        picks.append((pl, joy, got, kw, nd))
    ok = all(got and got[1] == ((got[0] >> 8) ^ got[0]) & 3 and got[0]
             and (pl is None or got[1] == (3 if pl == 4 else pl))
             and (got[0] == TU) == (pl == 4) and bool(got[2] & 0x80) == (pl == 4)
             for pl, _, got, _, _ in picks)
    rnd = [got[0] for pl, _, got, _, _ in picks if pl is None and got]
    check(ok and len(rnd) == 2 and rnd[0] != rnd[1],
          "κάθε επιλογή φτάνει στο worldinfo: " + ", ".join(
              f"{MR.ROWS[0 if pl is None else pl + 1]}"
              f"{' (χειριστήριο)' if joy else ''} -> "
              + (f"seed {got[0]:04X} πλανήτης {got[1]} #{got[2]:02X}" if got else "ΤΙΠΟΤΑ")
              for pl, joy, got, _, _ in picks)
          + f" — ο τυχαίος {'άλλος' if len(set(rnd)) == 2 else 'ΙΔΙΟΣ'} για άλλη αναμονή, "
          f"το TUTORIAL το #{TU:04X} με το bit 7")
    ks = [kw for *_, kw, _ in picks]
    check(None not in ks and all(nd == 0 for *_, nd in picks) and len(set(ks)) >= 3,
          f"ο κόσμος του μενού με άλλη ώρα του RUN: {ks}, "
          f"{len(set(k for k in ks if k is not None))} διαφορετικοί, bytes "
          f"διαφορετικά από την αναφορά {[nd for *_, nd in picks]}")

    # --- 0γ. ο κώδικας του seed στη γεννήτρια, μόνος του ------------------
    # Από το ld a,c μετά τις δύο αναγνώσεις του R: H, L και C τα βάζει ένα
    # κομμάτι στο #9000, και το worldinfo της τράπεζας 6 λέει τι βγήκε. Ο
    # κώδικας της γεννήτριας είναι ο ίδιος του δίσκου (build/gen.bin).
    gen = open(os.path.join(ROOT, "build", "gen.bin"), "rb").read()
    import random
    rng = random.Random(128)
    pairs = [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 0xFF), (1, 0),
             (0xAC, 0xE1), (0xFF, 0xFF), (0x12, 0x34)] + \
            [(rng.randrange(256), rng.randrange(256)) for _ in range(20)]

    def seeds(code):
        """Οι περιπτώσεις που ο κώδικας code (στο #8000) κάνει λάθος. Από το βήμα
        149 από το ld d,0 πριν από το ld a,c: το D κρατά το bit 7 του tutorial."""
        at = code.find(bytes([0x16, 0x00, 0x79, 0xFE, 0x04, 0x38]))
        if at < 0:
            at = code.find(bytes([0x16, 0x00, 0x79, 0xFE, 0x00, 0x38]))
        if at < 0:
            return ["δεν βρέθηκε το ld d,0 · ld a,c · cp 4"]
        k = CPC()
        k.run_frames(60)
        bad = []
        for c in (0, 1, 2, 3, 4, 0xFF):
            for h, l in pairs:
                k.write_ram(0x8000, code)
                k.write_ram(0x9000, bytes([0xF3, 0x31, 0x00, 0x98,
                                           0x21, l, h, 0x0E, c,
                                           0xC3, (0x8000 + at) & 0xFF,
                                           (0x8000 + at) >> 8]))   # di, sp, hl, c, jp
                k.set_pc(0x9000)
                k.run_us(500)
                sd, pl = worldinfo(k, wi6)
                tut = wi_byte3(k, wi6) & 0x80
                old = h << 8 | l
                good = sd != 0 and pl == ((sd >> 8) ^ sd) & 3 and bool(tut) == (c == 4)
                if c < 4:
                    # μόνο τα δύο κάτω bits του L· ή #AC00, αν θα έβγαινε μηδέν
                    good = good and pl == c and (
                        (sd ^ old) & ~3 == 0 or (sd == 0xAC00 and old & ~3 == 0))
                elif c == 4:
                    good = good and sd == TU    # το tutorial: πάντα το ίδιο
                else:
                    good = good and sd == (old or 0xAC00)
                if not good:
                    bad.append(f"{old:04X}/{c:02X}->{sd:04X}:{pl}")
        del k
        return bad
    bad = seeds(gen)
    check(not bad, f"ο κώδικας του seed: {6 * len(pairs)} περιπτώσεις (H, L, "
                   f"πλανήτης 0-3, 4 το tutorial ή #FF), μηδέν δεν βγαίνει, αλλάζουν "
                   f"μόνο τα δύο κάτω bits του L, ο πλανήτης ο διαλεγμένος, το "
                   f"tutorial το #{TU:04X} με το bit 7 και μόνο αυτό"
                   + (f" — λάθος {bad[:4]}" if bad else ""))
    for old, new, what in (
            ([0x79, 0xFE, 0x04], [0x79, 0xFE, 0x00], "χωρίς το ταίριασμα (cp 0)"),
            ([0x16, 0x80], [0x16, 0x00], "το tutorial χωρίς το bit 7 (ld d,0)"),
            ([0x20, 0x02, 0x26, 0xAC], [0x20, 0x02, 0x26, 0xAD], "με H = #AD στο μηδέν"),
            ([0x20, 0x02, 0x26, 0xAC], [0x18, 0x02, 0x26, 0xAC], "χωρίς τον έλεγχο του μηδενός")):
        i = gen.find(bytes(old))
        bad = seeds(gen[:i] + bytes(new) + gen[i + len(new):]) if i >= 0 else []
        check(i >= 0 and bad, f"ΑΡΝΗΤΙΚΟ seed: {what} — {len(bad)} λάθος, π.χ. {bad[:2]}")

    # --- 5. το πρόχειρο του φορτωτή --------------------------------------
    # Ως το βήμα 85 και τα τρία περίμεναν στην τράπεζα 5· στο 86 έγιναν 16.475
    # bytes, 91 πάνω από την τράπεζα, και τα δεδομένα πήγαν στη βασική 1. Η
    # μνήμη ελέγχεται τη στιγμή που το επίμετρο δίνει τη σκυτάλη: μετά, το
    # παιχνίδι γράφει τις μεταβλητές του μέσα στα ίδια αρχεία και τη
    # δρομολόγηση πάνω στο πρόχειρο.
    def img(name):
        return open(os.path.join(ROOT, "build", name), "rb").read()
    page2, game2 = img("page2.bin"), img("game2.bin")
    # Η BANK1.BIN από το βήμα 94 είναι το bank1c.bin: τα εικονίδια ΚΑΙ ο κώδικας
    # της τοποθέτησης στη δέσμευση b1code (src/commit.asm), όπως τα έγραψε το
    # src/main.asm — το bank1.bin του pack.py έχει τη δέσμευση άδεια. Το ίδιο η
    # BANK5.BIN από το βήμα 97: bank5c.bin, οι αρμοί ΚΑΙ ο κώδικας των κοντών
    # στροφών (src/bend.asm) στη δέσμευση b5code — και οι μηχανές ως το βήμα
    # 150, που τις πήρε η BANK7.BIN.
    mach, icons = img("bank5c.bin"), img("bank1c.bin")
    # ...ΚΑΙ ΑΠΟ ΤΟ ΒΗΜΑ 102 ο κώδικας των τρυπών του DIST από κάτω τους: το
    # bank1c.bin πάει από το OV_LOAD ως το #8000 (src/main.asm, tools/mkdsk.py).
    ov = 0x8000 - len(icons)
    code = sym["ZZ_PAGE2_END"] - len(game2)
    b5base = None
    for line in open(os.path.join(ROOT, "build", "layout.asm"), encoding="utf-8"):
        if line.startswith("B5_BASE"):
            b5base = int(line.split("#")[1].split()[0], 16)
    eg = endgame(code)

    def diff(got, want):
        return sum(x != y for x, y in zip(got, want)) + abs(len(got) - len(want))

    # Οι τράπεζες 6 και 7 όπως πρέπει να είναι στην παράδοση (βήμα 113): η
    # BANK6.BIN με τον κώδικα του τροχού από πάνω, η BANK7.BIN με τα κείμενα.
    # Μόνο τα τέσσερα bytes του worldinfo τα γράφει η γεννήτρια, και μένουν έξω.
    want6, want7 = bytearray(img("bank6.bin")), bytearray(img("bank7.bin"))
    code6, text7 = img("b6code.bin"), img("text.bin")
    want6[lay["G_b6code"] - 0x4000:lay["G_b6code"] - 0x4000 + len(code6)] = code6
    want7[lay["G_text"] - 0x4000:lay["G_text"] - 0x4000 + len(text7)] = text7
    wi6 = lay["G_worldinfo"] - 0x4000
    game = img("game.bin")

    def scratch_state(disc, eg, amsdos=None):
        """(διαφορές τράπεζας 2, μηχανών, εικονιδίων, μη μηδενικά του DIST
        και του NEXTHOP, διαφορές τράπεζας 6, τράπεζας 7, κώδικα της τράπεζας
        0) τη στιγμή της παράδοσης, ή None."""
        h = CPC()
        got = handover(h, disc, eg, amsdos)
        del h
        if got is None:
            return None
        ram, b5, b6, b7 = got
        b6 = bytearray(b6)
        b6[wi6:wi6 + 4] = want6[wi6:wi6 + 4]
        return (diff(ram[0x8000:0x8000 + len(page2)], page2),
                diff(ram[code:code + len(game2)], game2),
                diff(b5[b5base - 0x4000:b5base - 0x4000 + len(mach)], mach),
                diff(ram[ov:ov + len(icons)], icons),
                sum(1 for x in ram[0x4000:ov] if x),
                sum(1 for x in b5[:b5base - 0x4000] if x),
                diff(bytes(b6), want6), diff(b7, want7),
                diff(ram[0x100:0x100 + len(game)], game))

    st = scratch_state(DSK, eg) if eg else None
    check(st is not None, f"το επίμετρο ({len(eg)} bytes) πιάστηκε τη στιγμή "
                          f"που πηδά στο #0100")
    if st:
        d2, dg, dm, di, z1, z5, d6, d7, d0 = st
        check(d6 == 0 and d7 == 0 and d0 == 0 and HANDOVER["fl_off"] == 0,
              f"από τον αναγνώστη τομέων, byte προς byte: η τράπεζα 6 με τον "
              f"κώδικα του τροχού ({d6} διαφορετικά), η 7 με τα κείμενα ({d7}), "
              f"ο κώδικας της τράπεζας 0 στο #0100 ({len(game)} bytes, {d0}) — "
              f"fl_off {HANDOVER['fl_off']}, παράδοση στο frame {HANDOVER['frames']}")
        check(d2 == 0 and dg == 0,
              f"η τράπεζα 2 όπως βγήκε από το build: {len(page2)} bytes "
              f"δεδομένων ({d2} διαφορετικά), {len(game2)} κώδικα στο "
              f"#{code:04X} ({dg})")
        check(dm == 0 and di == 0,
              f"οι μηχανές στο #{b5base:04X} της τράπεζας 5 ({len(mach)} bytes, "
              f"{dm} διαφορετικά) και ο κώδικας των τρυπών με τα εικονίδια και τον "
              f"κώδικα της τοποθέτησης στο #{ov:04X} ({len(icons)}, {di})")
        check(z1 == 0 and z5 == 0,
              f"το πρόχειρο σβήστηκε όπως στο snapshot: {z1} bytes μη μηδενικά "
              f"στο DIST (#4000-#{ov - 1:04X}), {z5} στο NEXTHOP ως τις μηχανές")

    # Αρνητικό: τα δύο ldir που σβήνουν το πρόχειρο γίνονται nop, μέσα στο
    # LOADER.BIN του ίδιου δίσκου. Το επίμετρο ψάχνεται ολόκληρο, όχι το
    # LOADER.BIN: οι τομείς ενός αρχείου δεν κάθονται απαραίτητα στη σειρά.
    dsk = bytearray(open(DSK, "rb").read())
    at = dsk.find(eg) if eg else -1
    cut = 0
    for n in (b5base - 0x4001, ov - 0x4001):
        k = eg.find(bytes([0x01, n & 0xFF, n >> 8, 0xED, 0xB0]))
        if at >= 0 and k >= 0:
            dsk[at + k + 3:at + k + 5] = b"\0\0"
            cut += 1
    st = (scratch_state(bytes(dsk), bytes(dsk[at:at + len(eg)]))
          if cut == 2 else None)
    # ΤΟ ΜΙΣΟ ΑΠΟ ΟΣΑ ΦΟΡΤΩΘΗΚΑΝ ΕΚΕΙ, όχι 4.000: το βήμα 89 έβγαλε τον διάδρομο
    # και τις πόρτες από την τράπεζα 2, και τα μη μηδενικά της έπεσαν κάτω
    # από τα 4.000 που έγραφε εδώ ένας σταθερός αριθμός.
    nz2, nzg = sum(1 for x in page2 if x), sum(1 for x in game2 if x)
    check(st is not None and st[4] > nz2 // 2 and st[5] > nzg // 2,
          f"ΑΡΝΗΤΙΚΟ: χωρίς τα δύο σβησίματα ({cut} από 2 κομμένα) μένουν "
          f"{st[4] if st else '-'} bytes στο DIST (από {nz2} μη μηδενικά της "
          f"τράπεζας 2) και {st[5] if st else '-'} στο NEXTHOP (από {nzg} του κώδικά της)")

    # --- 6. το σβήσιμο της οθόνης ----------------------------------------
    # Ο φορτωτής αφήνει τη δική του οθόνη και το παιχνίδι ξεκινά ΠΑΝΩ της. Ως
    # το βήμα 21 το «run"habitat» φαινόταν γραμμένο μέσα στην αποικία μέχρι την
    # πρώτη πλήρη σχεδίαση. Εδώ ελέγχεται η ίδια η ρουτίνα, με σημάδι.
    m.write_ram(0xC000, bytes([0xAA]) * 0x4000)
    m.run_code(0x3EC0, bytes([0xCD, sym["HW_CLEAR"] & 0xFF,
                              sym["HW_CLEAR"] >> 8, 0x18, 0xFE]))
    m.run_frames(10)                     # 16 KB ldir = 86 ms, δηλαδή 4,3 frames
    left = sum(1 for b in m.read_ram(0xC000, 0x4000) if b)
    check(left == 0, f"το hw_clear σβήνει και τα 16 KB της οθόνης ({left} bytes "
                     f"έμειναν)")

    # --- 6β. ο αναγνώστης τομέων με φυτεμένο σφάλμα (βήμα 113) -----------
    # Μέσα στο LOADER.BIN του δίσκου, όπως το αρνητικό του επιμέτρου. Ο
    # έλεγχος είναι ο ίδιος με πάνω: η μνήμη τη στιγμή της παράδοσης.
    def planted(pat, new):
        d = bytearray(open(DSK, "rb").read())
        n = patch(d, pat, new)
        return (scratch_state(bytes(d), eg) if n == 1 else None), n
    import re
    sb = int(re.search(r"^SECT_BUF\s+equ\s+#([0-9A-Fa-f]+)",
                       open(os.path.join(ROOT, "src", "boot.asm"), encoding="utf-8").read(),
                       re.M).group(1), 16)
    # η κεφαλίδα ένα byte πιο κοντά: τα πρώτα 384 bytes κάθε αρχείου
    # μετατοπισμένα κατά ένα (οι επόμενοι τομείς πάνε κατευθείαν στη θέση
    # τους). Στο βήμα 113 αυτό έριχνε τη γεννήτρια πριν από την παράδοση· με
    # τη διάταξη του 114 φτάνει, με εκατοντάδες bytes λάθος. Η σωστή εκκίνηση
    # δίνει 0 (πιο πάνω), οπότε οποιαδήποτε διαφορά είναι το σφάλμα.
    st, n = planted(bytes([0x21, 0x80, (sb + 128) >> 8]),
                    bytes([0x21, 0x7F, (sb + 128) >> 8]))
    check(n == 1 and (st is None or st[6] > 0 or st[8] > 0),
          f"ΑΡΝΗΤΙΚΟ: η κεφαλίδα 127 bytes αντί για 128 ({n} σημείο) — "
          + (f"τράπεζα 6 {st[6]} διαφορετικά, κώδικας {st[8]}" if st else
             "η εκκίνηση δεν φτάνει στην παράδοση"))
    # η δεύτερη έκταση από την εγγραφή της πρώτης: μόνο η BANK7.BIN έχει δύο
    # από το βήμα 175 (η BANK6.BIN είναι 4 KB χωρίς τα μηδενικά της, και η 6
    # έμενε ίδια)
    ff = bs["FL_FIND"]
    st, n = planted(bytes([0x07, 0x07, 0x07, 0xE6, 0x07, 0xCD, ff & 0xFF, ff >> 8]),
                    bytes([0x07, 0x07, 0x07, 0xE6, 0x00]))
    check(n == 1 and (st is None or st[7] > 0),
          f"ΑΡΝΗΤΙΚΟ: η δεύτερη έκταση από την πρώτη εγγραφή ({n} σημείο) — "
          + (f"τράπεζα 7 {st[7]} διαφορετικά (η 6, με μία έκταση, {st[6]})" if st else
             "η εκκίνηση δεν φτάνει στην παράδοση"))

    # --- 7. η εφεδρεία: το AMSDOS (βήμα 113) ----------------------------
    # Η PAGE2.BIN γίνεται τύπου 0 (BASIC), με σωστό άθροισμα. Για το AMSDOS
    # είναι αρχείο σαν όλα, και το CAS IN DIRECT το φορτώνει. Ο αναγνώστης
    # δέχεται μόνο δυαδικά: την αρνείται ΑΦΟΥ έχει διαβάσει πέντε αρχεία και η
    # κεφαλή του είναι στο track 11. Από εκεί όλα με το AMSDOS.
    fb = bytearray(open(DSK, "rb").read())
    h = file_sector(fb, "PAGE2")
    if h is not None:
        fb[h + 18] = 0
        ck = sum(fb[h:h + 67]) & 0xFFFF
        fb[h + 67:h + 69] = ck.to_bytes(2, "little")
    st = scratch_state(bytes(fb), eg) if h is not None else None
    ok = st is not None and not any(st[:4]) and not any(st[4:6]) and not any(st[6:])
    check(ok and HANDOVER["fl_off"] == 1,
          f"η PAGE2.BIN τύπου 0 φορτώνει από το AMSDOS: fl_off "
          f"{HANDOVER.get('fl_off')}, όλα τα αρχεία στη θέση τους "
          f"({st if st else 'καμία παράδοση'}), παράδοση στο frame "
          f"{HANDOVER.get('frames') if st else '-'}")
    fb_frames = HANDOVER.get("frames") if st else None
    # ΤΟ AMSDOS ΔΕΝ ΚΙΝΕΙ ΤΗΝ ΚΕΦΑΛΗ ΑΝ ΠΙΣΤΕΥΕΙ ΟΤΙ ΕΙΝΑΙ ΗΔΗ ΕΚΕΙ. Το CAS IN
    # OPEN διαβάζει πρώτα τον κατάλογο, στο track 0. Ως το βήμα 127 ο φορτωτής
    # χωρούσε στο track 0, το AMSDOS έμενε με «track 0», και χωρίς το SEEK του
    # fl_quit διάβαζε «κατάλογο» από το track 12 (ο ελεγκτής του εξομοιωτή δεν
    # κοιτάζει το C του τομέα). Από το 128 ο φορτωτής είναι 1.677 bytes, ο
    # τελευταίος του τομέας στο track 1, και το AMSDOS πηγαίνει μόνο του στο 0:
    # το αρνητικό δεν έπιανε πια τίποτα. Γι' αυτό το byte του AMSDOS γίνεται 0
    # μετά την επιλογή του μενού — ο φορτωτής ενός track — και ελέγχονται και
    # οι δύο δρόμοι με αυτό.
    # ΑΠΟ ΤΟ ΒΗΜΑ 130 ΑΝΑΠΟΔΑ: το μενού έγινε αρχείο, ο φορτωτής 1.188 bytes
    # χωρά ξανά στο track 0, και το AMSDOS μένει μόνο του στο «0» — αυτόν τον
    # δρόμο τον περπάτησε ήδη η εφεδρεία παραπάνω. Ο άλλος, ενός φορτωτή που
    # θα ξαναμεγαλώσει, με το byte στο 1.
    left = HANDOVER.get("amsdos_trk")
    st = scratch_state(bytes(fb), eg, amsdos=1) if h is not None else None
    ok = st is not None and not any(st[:4]) and not any(st[4:6]) and not any(st[6:])
    check(ok and left == 0,
          f"και με το AMSDOS να πιστεύει «track 1» (μόνο του το άφησε στο {left}, "
          f"τον τελευταίο τομέα του LOADER.BIN): {st if st else 'καμία παράδοση'}")
    # ΑΡΝΗΤΙΚΟ: χωρίς το SEEK στο track 0 του fl_quit, με το AMSDOS στο «0»:
    # δεν κινεί την κεφαλή, διαβάζει «κατάλογο» από το track 12 και γράφει
    # «.BIN not found».
    q = bs["FL_QUIT"]
    sk = bs["FL_SEEK"]
    n = patch(fb, bytes([0xAF, 0xCD, sk & 0xFF, sk >> 8, 0xFB, 0xC9]),
              bytes([0xAF, 0, 0, 0, 0xFB, 0xC9]))
    st = scratch_state(bytes(fb), eg, amsdos=0) if n == 1 else None
    bad = st is None or any(st[:4]) or any(st[6:])
    check(n == 1 and bad,
          f"ΑΡΝΗΤΙΚΟ: χωρίς την επιστροφή στο track 0 ({n} σημείο, fl_quit "
          f"#{q:04X}) " + ("η εκκίνηση δεν φτάνει στην παράδοση" if st is None
                           else f"φτάνει με {st}"))

    # --- 8. το «εντάξει» του ελεγκτή (βήμα 113) --------------------------
    # Στο CPC το TC του μPD765 δεν είναι συνδεδεμένο: κάθε διάβασμα και
    # γράψιμο φτάνει στο EOT και τελειώνει με IC = 01 (ST0 #40) και EN (ST1
    # #80). Ο ελεγκτής του εξομοιωτή δίνει IC = 00, οπότε ο έλεγχος γίνεται
    # εδώ με τα ίδια τα bytes: ο φορτωτής (fl_ok) και το σώσιμο (fd_ok).
    CASES = [((0x00, 0x00, 0x00), True, "εξομοιωτής"),
             ((0x40, 0x80, 0x00), True, "CPC: EN"),
             ((0x40, 0x84, 0x00), False, "ND"),
             ((0x40, 0xA0, 0x20), False, "CRC"),
             ((0x40, 0x81, 0x00), False, "MA"),
             ((0x40, 0x80, 0x40), False, "CM"),
             ((0x48, 0x00, 0x00), False, "NR"),
             ((0x80, 0x00, 0x00), False, "άκυρη"),
             ((0xC0, 0x00, 0x00), False, "IC 11")]

    def verdicts(run, at, res, code):
        """Ο κώδικας του ελέγχου στο at, τα ST0-ST2 στο res: A = 0 σημαίνει
        εντάξει. Γυρίζει τις περιπτώσεις που κρίθηκαν λάθος."""
        wrong = []
        for st3, good, name in CASES:
            got = run(at, res, code, st3)
            if (got == 0) != good:
                wrong.append(name)
        return wrong

    # ο φορτωτής: σε ένα 6128 με BASIC, με το boot.bin στο #9000
    boot = img("boot.bin")
    k = CPC()
    k.run_frames(200)

    def run_boot(at, res, code, st3):
        k.write_ram(0x9000, code)
        k.write_ram(res, bytes(st3))
        k.write_ram(0xA3F0, b"\xEE")
        k.run_code(0xA300, bytes([0xF3, 0xCD, at & 0xFF, at >> 8,
                                  0x32, 0xF0, 0xA3, 0x18, 0xFE]))
        return k.read_ram(0xA3F0, 1)[0]

    fo, fs = bs["FL_OK"], bs["FL_ST"]
    w = verdicts(run_boot, fo, fs, boot)
    check(not w, f"το fl_ok του φορτωτή κρίνει σωστά {len(CASES)} περιπτώσεις "
                 f"ST0/ST1/ST2" + (f" — λάθος: {w}" if w else ""))

    def fault(code, at, old, new):
        """Το code με το ΠΡΩΤΟ old μετά το at (σχετικό) αλλαγμένο σε new."""
        c = bytearray(code)
        i = c.find(bytes(old), at)
        if i >= 0:
            c[i:i + len(old)] = bytes(new)
        return bytes(c), i >= 0
    for old, new, what in (([0xE6, 0x88], [0xE6, 0xC8], "ο έλεγχος ως το βήμα 112 (IC = 00 μόνο)"),
                           ([0xE6, 0x7F], [0xE6, 0x7B], "ένας που δέχεται το ND")):
        bad, found = fault(boot, fo - 0x9000, old, new)
        w = verdicts(run_boot, fo, fs, bad) if found else []
        check(found and w, f"ΑΡΝΗΤΙΚΟ fl_ok: {what} — λάθος στα {w}")
    del k

    # το σώσιμο: το fd_ok του δεύτερου κομματιού (src/fdc.asm), στη θέση όπου
    # τρέχει (SV_ORG), μέσα στο παιχνίδι που ξεκίνησε από τον δίσκο
    ov2 = img("ovl2.bin")

    def run_game(at, res, code, st3):
        m.write_ram(sym["ZZ_OV2"], code)
        m.write_ram(res, bytes(st3))
        m.write_ram(0x3F00, b"\xEE")
        m.run_code(0x3EC0, bytes([0xF3, 0xCD, at & 0xFF, at >> 8,
                                  0x32, 0x00, 0x3F, 0x18, 0xFE]))
        return m.read_ram(0x3F00, 1)[0]

    do, dr = sym["FD_OK"], sym["FD_RES"]
    w = verdicts(run_game, do, dr, ov2)
    check(not w, f"το fd_ok του σωσίματος κρίνει σωστά τις ίδιες {len(CASES)}"
                 + (f" — λάθος: {w}" if w else ""))
    for old, new, what in (([0xE6, 0x88], [0xE6, 0xC0], "ο έλεγχος ως το βήμα 112"),
                           ([0xE6, 0x7F], [0xE6, 0x7B], "ένας που δέχεται το ND")):
        bad, found = fault(ov2, do - sym["ZZ_OV2"], old, new)
        w = verdicts(run_game, do, dr, bad) if found else []
        check(found and w, f"ΑΡΝΗΤΙΚΟ fd_ok: {what} — λάθος στα {w}")

    print(f"\nεκκίνηση: {frames} frames = {frames / 50:.1f} s από την επιλογή του "
          f"μενού ως την αποικία (από το ENTER: 1.460 = 29 s ως το βήμα 112, ~570 ως "
          f"το 127· τα 5 s είναι η γεννήτρια)")
    if fb_frames:
        print(f"με την εφεδρεία από την PAGE2.BIN: παράδοση στο frame {fb_frames}")
    print(f"build/habitat.dsk: {os.path.getsize(DSK)} bytes, "
          f"build/disc.png γράφτηκε")
    if FAIL:
        print(f"\nΑΠΟΤΥΧΙΑ — {len(FAIL)}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
