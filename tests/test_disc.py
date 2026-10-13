#!/usr/bin/env python3
"""Ο δίσκος (DESIGN.md §13, §4.2).

Ως εδώ το παιχνίδι ξεκινούσε μόνο από snapshot: ο εξομοιωτής έβαζε τις τράπεζες
στη θέση τους και πηδούσε στο #0100. Αυτό δεν είναι μηχάνημα — είναι σκηνικό.
Ενα πραγματικό 6128 ξεκινά με BASIC, AMSDOS, αναμμένα ROM και μια δισκέτα, και
όλα όσα το snapshot έστηνε δωρεάν πρέπει να τα κάνει ο φορτωτής.

Τι ελέγχεται:

  1. Το RUN"HABITAT φτάνει ΜΕΣΑ στον κώδικα του παιχνιδιού. Δύο εκδοχές του
     φορτωτή δεν έτρεξαν ποτέ ούτε μια εντολή (τα ROM σκεπάζουν το #0000-#3FFF
     και το #C000-#FFFF) και μια τρίτη κόλλησε στο «Press PLAY then any key»
     (το AMSDOS ξεκαρφώνεται όταν το BASIC τρέχει δυαδικό). Καμία δεν φαινόταν
     στην οθόνη ως σφάλμα.
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
     AMSDOS (fl_off), η εκκίνηση κρατά ως 600 frames, και τη στιγμή της
     παράδοσης ΟΛΑ τα αρχεία είναι στη θέση τους byte προς byte — και οι δύο
     εκτάσεις της BANK6.BIN και της BANK7.BIN. Αρνητικά: η κεφαλίδα ένα byte
     λάθος, η δεύτερη έκταση από την πρώτη εγγραφή.
  7. Η ΕΦΕΔΡΕΙΑ. Ενας δίσκος όπου η PAGE2.BIN είναι τύπου 0 (BASIC, με σωστό
     άθροισμα): ο αναγνώστης την αρνείται, το AMSDOS τη φορτώνει, και η
     εκκίνηση φτάνει ίδια. Αρνητικό: χωρίς την επιστροφή της κεφαλής στο
     track 0 πριν από το AMSDOS.
  8. Το «εντάξει» του ελεγκτή: IC = 01 με EN είναι επιτυχία στο CPC (το TC
     δεν είναι συνδεδεμένο), για τον φορτωτή (fl_ok) και για το σώσιμο
     (fd_ok). Αρνητικά: ο έλεγχος ως το βήμα 112, και ένας που δέχεται το ND.
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")

from sprites import load_map, load_bin                                  # noqa: E402
import world as W                                                       # noqa: E402

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
    """Τα σύμβολα του φορτωτή (build/boot.sym, από το tools/mkdsk.py)."""
    bs = {}
    for line in open(os.path.join(ROOT, "build", "boot.sym"),
                     encoding="utf-8", errors="replace"):
        p = line.split()
        if len(p) >= 2 and p[1].startswith("#"):
            bs[p[0].upper()] = int(p[1][1:], 16)
    return bs


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


def handover(m, disc, eg):
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


def main():
    sym, g = build()
    bs = boot_syms()
    from cpc import CPC
    m = CPC()
    m.run_frames(300)                    # το BASIC θέλει τον χρόνο του
    m.insert_disc(DSK)
    # Ο εξομοιωτής ξεκινά με κασέτα· σε 6128 με μονάδα ο δίσκος είναι το
    # προεπιλεγμένο και το |DISC περισσεύει. Δεν βλάπτει.
    m.type_text('|disc\n', hold_frames=4, gap_frames=8)
    m.run_frames(60)
    m.type_text('run"habitat\n', hold_frames=4, gap_frames=8)

    # --- 1. φτάνει το παιχνίδι; ------------------------------------------
    # Ο μετρητής προγράμματος ΔΕΝ είναι απόδειξη: το #0100-#37AD του παιχνιδιού
    # είναι και η περιοχή της κάτω ROM, οπότε ένα κολλημένο firmware δείχνει
    # μέσα στο παιχνίδι. Το σημάδι είναι η ΜΝΗΜΗ: τα αποθέματα του §10.1 δεν
    # υπάρχουν πουθενά στον δίσκο — τα γράφει το game_new όταν τρέξει.
    def w16(a):
        return m.peek(a) | (m.peek(a + 1) << 8)

    # Στον δρόμο κρατάμε και την ΟΘΟΝΗ: ως το βήμα 21 ο παίκτης κοίταζε μισό
    # λεπτό το «Ready» του BASIC (§13.2). Τώρα βλέπει τίτλο, τελείες ανά αρχείο
    # και μπάρα που προχωρά — και αυτό ελέγχεται εδώ, γιατί υπάρχει μόνο στον
    # δρόμο του δίσκου: το snapshot δεν περνά ποτέ από τον φορτωτή.
    def scr():
        return m.read_ram(0xC000, 0x4000)

    def bar_bytes(ram):
        # πόσα από τα 64 bytes της μπάρας είναι γεμάτα (χαρακτηρο-σειρά 16)
        base = 16 * 80 + 8
        return sum(1 for i in range(64) if ram[base + i] == 0xFF)

    def inked(ram, row, rows=1):
        # μη μηδενικά bytes σε χαρακτηρο-σειρές
        n = 0
        for r in range(row, row + rows):
            for line in range(8):
                o = line * 0x800 + r * 80
                n += sum(1 for i in range(80) if ram[o + i])
        return n

    running, frames, bars, seen_title, tones = False, 0, [], None, []
    fl_seen = None
    # ΑΝΑ 10 FRAMES από το βήμα 112: η γεννήτρια κρατά πια ~5 s, και ανά 30 τα
    # δείγματα της μουσικής ήταν δεκαπέντε — τέσσερις νότες, όχι πέντε.
    for _ in range(360):
        m.run_frames(10)
        frames += 10
        started = w16(g + 2) == 100 and m.peek(g + 58) == 6      # §10.1 (βήμα 120)
        if seen_title is None and frames >= 300:
            ram = scr()
            # ο φορτωτής μετράει σειρές από το 1 (firmware), η μνήμη από το 0
            seen_title = (inked(ram, 4, 3), inked(ram, 0, 2))
        # ΜΟΝΟ ΟΣΟ ΦΟΡΤΩΝΕΙ: μόλις ξεκινήσει το παιχνίδι, τα bytes της μπάρας
        # είναι εικόνα του κάδρου. Το όριο ήταν σταθερός αριθμός frames και
        # έσπασε μόλις μπήκε ένα ένατο αρχείο στον δίσκο (§4.2).
        if frames >= 300 and not started:
            bars.append(bar_bytes(scr()))
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
    check(frames <= 600,
          f"εκκίνηση {frames} frames από το ENTER ως την αποικία, ταβάνι 600 "
          f"(1.460 ως το βήμα 112)")

    # --- 1β. η οθόνη φόρτωσης --------------------------------------------
    title, basic = seen_title
    check(title > 0 and basic == 0,
          f"η οθόνη φόρτωσης έσβησε το BASIC: {title} bytes τίτλου, "
          f"{basic} στις δύο πρώτες σειρές (εκεί έγραφε το «Amstrad 128K»)")
    # Η μπάρα είναι το ΜΟΝΟ πράγμα που κινείται επί 5 δευτερόλεπτα (13,5 ως το βήμα 111): πρέπει
    # να ξεκινά άδεια, να μη γυρίζει ποτέ πίσω, και να φτάνει ως το τέρμα.
    # Η ΔΕΙΓΜΑΤΟΛΗΨΙΑ ΕΙΝΑΙ ΑΝΑ 30 FRAMES ΚΑΙ Η ΦΑΣΗ ΤΗΣ ΑΛΛΑΖΕΙ ΜΕ ΚΑΘΕ
    # ΑΛΛΑΓΗ ΜΕΓΕΘΟΥΣ ΤΟΥ ΚΩΔΙΚΑ. Το «bars[0] == 0 και max == 64» έπεφτε σε
    # άσχετα βήματα — πότε με ένα τελευταίο δείγμα ΜΕΤΑ το σβήσιμο της οθόνης
    # (μπάρα 0, δηλαδή «πισωγύρισμα»), πότε με το τελευταίο δείγμα στο 51
    # επειδή το παιχνίδι ξεκίνησε ανάμεσα σε δύο δείγματα. Η ιδιότητα που
    # μετράει είναι: ξεκινά σχεδόν άδεια, δεν γυρίζει ΠΟΤΕ πίσω, και φτάνει
    # ουσιαστικά ως το τέρμα. Τα μηδενικά μετά το γέμισμα δεν είναι μπάρα.
    while len(bars) > 1 and bars[-1] == 0:
        bars.pop()
    mono = all(b <= c for b, c in zip(bars, bars[1:]))
    check(bars and bars[0] <= 8 and mono and max(bars) >= 56,
          f"η μπάρα προχώρησε {bars[0] if bars else '-'} -> "
          f"{max(bars) if bars else 0} από 64, "
          f"{'μονότονα' if mono else 'ΜΕ ΠΙΣΩΓΥΡΙΣΜΑ'} "
          f"({len(bars)} δείγματα)")

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
    # 100 τρόφιμα, 12 ανταλλακτικά και έξι άποικοι (40, 4 και τέσσερις ως τότε).
    check(50 <= stock[0] <= 60 and stock[1] == 100 and stock[2] == 60
          and stock[3] == 189 and stock[4] == 107 and stock[6] == 12 and pop == 6,
          f"§10.1 από τον δίσκο: {stock} πληθυσμός {pop}")

    # --- 3. το HUD είναι γραμμένο ----------------------------------------
    sys.path.insert(0, HERE)
    import hudread
    row2 = hudread.text(m, sym, 2)
    check(row2.startswith("POP  6/"), f"το HUD σχεδιάστηκε: |{row2}|")

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
    # παίρνεται αφού τρέξει ο τροχός, οπότε αυτά δεν είναι πια του build.
    live = {sym["ND_I"], sym["ENS_CALL"] + 1, sym["ENS_CALL"] + 2}
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

    # --- 3γ. ο κώδικας της κατεδάφισης στις τρύπες του DIST (βήματα 101-102) -
    # Τον φέρνει η BANK1.BIN στο OV_LOAD, κάτω από τα εικονίδια, και το
    # ov_install τον μοιράζει στις στήλες 96-127 στην εκκίνηση. Ως το βήμα 101
    # ερχόταν με την PAGE2.BIN στο GH_BUF· ένας δίσκος που τον ξεχνά αφήνει
    # μηδενικά εκεί όπου πηδά το πρώτο M, D, FIRE.
    # Και από το βήμα 103 το σώσιμο με τον οδηγό του δίσκου, από τη γραμμή μετά
    # (build/ovl2.bin): το ίδιο το παιχνίδι το χρειάζεται για να σώσει.
    # Και από το βήμα 108 η οθόνη βοήθειας (build/ovl3.bin), μετά το σώσιμο.
    ovl = open(os.path.join(ROOT, "build", "ovl.bin"), "rb").read()
    ovl2 = open(os.path.join(ROOT, "build", "ovl2.bin"), "rb").read()
    ovl3 = open(os.path.join(ROOT, "build", "ovl3.bin"), "rb").read()
    b1 = cpc._lib.cpcemu_ram_ptr(m._h, 1)
    holes = bytes(b1[128 * (k >> 5) + 96 + (k & 31)] for k in range(len(ovl)))
    r2 = (len(ovl) + 31) // 32
    holes2 = bytes(b1[128 * (r2 + (k >> 5)) + 96 + (k & 31)] for k in range(len(ovl2)))
    r3 = r2 + (len(ovl2) + 31) // 32
    holes3 = bytes(b1[128 * (r3 + (k >> 5)) + 96 + (k & 31)] for k in range(len(ovl3)))
    check(len(ovl) > 512 and holes == ovl and len(ovl2) > 512 and holes2 == ovl2
          and len(ovl3) > 128 and holes3 == ovl3,
          f"ο κώδικας της κατεδάφισης, του σωσίματος και της βοήθειας ήρθε από τον "
          f"δίσκο στις τρύπες του DIST: {len(ovl)}, {len(ovl2)} και {len(ovl3)} bytes, "
          f"{sum(x != y for x, y in zip(holes, ovl))}, "
          f"{sum(x != y for x, y in zip(holes2, ovl2))} και "
          f"{sum(x != y for x, y in zip(holes3, ovl3))} διαφορετικά")

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
    check(nd == 0, f"το επίπεδο του δίσκου είναι ο κόσμος του seed {seed:04X}, "
                   f"πλανήτης {planet} όπως τον γράφει το worldinfo, byte προς byte: "
                   + (f"{nd} διαφορετικά" if nd >= 0 else
                      f"ο πλανήτης του seed είναι {((seed >> 8) ^ seed) & 3}"))

    m.screenshot(os.path.join(ROOT, "build", "disc.png"), aspect=True)

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
    # BANK5.BIN από το βήμα 97: bank5c.bin, οι μηχανές, οι αρμοί ΚΑΙ ο κώδικας
    # των κοντών στροφών (src/bend.asm) στη δέσμευση b5code.
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

    def scratch_state(disc, eg):
        """(διαφορές τράπεζας 2, μηχανών, εικονιδίων, μη μηδενικά του DIST
        και του NEXTHOP, διαφορές τράπεζας 6, τράπεζας 7, κώδικα της τράπεζας
        0) τη στιγμή της παράδοσης, ή None."""
        h = CPC()
        got = handover(h, disc, eg)
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
    # η δεύτερη έκταση (BANK6.BIN, BANK7.BIN) από την εγγραφή της πρώτης
    ff = bs["FL_FIND"]
    st, n = planted(bytes([0x07, 0x07, 0x07, 0xE6, 0x07, 0xCD, ff & 0xFF, ff >> 8]),
                    bytes([0x07, 0x07, 0x07, 0xE6, 0x00]))
    check(n == 1 and (st is None or (st[6] > 0 and st[7] > 0)),
          f"ΑΡΝΗΤΙΚΟ: η δεύτερη έκταση από την πρώτη εγγραφή ({n} σημείο) — "
          + (f"τράπεζα 6 {st[6]} και 7 {st[7]} διαφορετικά" if st else
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
    # ΑΡΝΗΤΙΚΟ: χωρίς το SEEK στο track 0 του fl_quit. Το AMSDOS πιστεύει ότι η
    # κεφαλή είναι εκεί που την άφησε (στον φορτωτή, track 0), δεν την κινεί,
    # διαβάζει «κατάλογο» από το track 11 και γράφει «PAGE2   .BIN not found».
    q = bs["FL_QUIT"]
    sk = bs["FL_SEEK"]
    n = patch(fb, bytes([0xAF, 0xCD, sk & 0xFF, sk >> 8, 0xFB, 0xC9]),
              bytes([0xAF, 0, 0, 0, 0xFB, 0xC9]))
    st = scratch_state(bytes(fb), eg) if n == 1 else None
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

    print(f"\nεκκίνηση: {frames} frames = {frames / 50:.0f} s από το ENTER ως "
          f"την αποικία (1.460 = 29 s ως το βήμα 112· τα 5 s είναι η γεννήτρια)")
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
