#!/usr/bin/env python3
"""build/habitat.dsk — ο δίσκος (DESIGN §13).

Το παιχνίδι δεν είναι ένα αρχείο. Είναι δέκα: ο φορτωτής, το μενού, ο κώδικας
της τράπεζας 0, ο κώδικας της τράπεζας 2, η γεννήτρια, οι πέντε εικόνες
δεδομένων (οι τράπεζες 6 και 7 ολόκληρες από το βήμα 193), και οι σελίδες. Το AMSDOS δίνει ΜΙΑ διεύθυνση φόρτωσης ανά αρχείο και δεν ξέρει από
τράπεζες, οπότε ποιο πάει πού το αποφασίζει ο φορτωτής — εδώ απλώς μπαίνουν
στον δίσκο με τα ονόματα που περιμένει το src/boot.asm.

ΤΟ RUN"HABITAT ΔΕΝ ΜΠΟΡΕΙ ΝΑ ΤΡΕΞΕΙ ΤΟΝ ΦΟΡΤΩΤΗ ΚΑΤΕΥΘΕΙΑΝ. Οταν το BASIC
τρέχει ΔΥΑΔΙΚΟ αρχείο, το AMSDOS ξεκαρφώνεται πρώτα: τα διανύσματα CAS IN *
γυρίζουν στην κασέτα και το |DISC δεν υπάρχει πια στην αλυσίδα RSX. Μετρήθηκε:
το #BC77 δείχνει #A88B (RST 3, δηλαδή ROM) στο «Ready» και #A4E5 (RST 1,
δηλαδή κασέτα) μέσα σε τρεχούμενο δυαδικό — και το πρώτο CAS IN OPEN του
φορτωτή ζητούσε «Press PLAY then any key».

Γι' αυτό υπάρχει το HABITAT.BAS, τρεις γραμμές BASIC. Ενα πρόγραμμα που
ξεκινά με CALL από το BASIC κρατά το AMSDOS καρφωμένο — αυτό επίσης
μετρήθηκε. Είναι και ο κλασικός τρόπος του CPC.

Η επικεφαλίδα AMSDOS (-t 1 -c -e) χρειάζεται για το LOAD: το BASIC διαβάζει
από εκεί πόσα bytes να φέρει. Ως το βήμα 192 για τα υπόλοιπα η διεύθυνση της
επικεφαλίδας αγνοούνταν (ο φορτωτής φόρτωνε όπου ήθελε) και γραφόταν σωστή
για να λέει το cat την αλήθεια. ΑΠΟ ΤΟ ΒΗΜΑ 193 ΤΗ ΔΙΑΒΑΖΕΙ: τα αρχεία είναι
ροές ZX0 (tools/zx0.py), και η διεύθυνση είναι πού φορτώνεται η ροή — στο
τέλος του προορισμού, όπου ο φορτωτής την ξεδιπλώνει πάνω στη θέση της.
"""
import functools, os
import re, shutil, subprocess, sys

from dsk import Dsk, to_extended

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUILD = os.path.join(ROOT, "build")
RASM = os.path.expanduser("~/rasm/rasm.exe")
IDSK = os.path.expanduser("~/idsk/iDSK")
DSK = os.path.join(BUILD, "habitat.dsk")

# όνομα στον δίσκο, πηγή, διεύθυνση φόρτωσης, εκτέλεσης (0 = δεδομένα)
# Το MEMORY κατεβάζει το HIMEM κάτω από τον φορτωτή: από το #9000 και πάνω δεν
# ακουμπά πια το BASIC. Η στοίβα του κάθεται στο #8F00-#8FFF, ανάμεσα στη
# γεννήτρια (#8000-#8BFF) και τον φορτωτή — γι\' αυτό το όριο είναι εκεί.
STUB = ('10 MEMORY &8FFF\r\n'
        '20 LOAD"LOADER.BIN",&9000\r\n'
        '30 CALL &9000\r\n\x1a')

# ΜΕ ΤΗ ΣΕΙΡΑ ΠΟΥ ΤΑ ΦΟΡΤΩΝΕΙ Ο ΦΟΡΤΩΤΗΣ (βήμα 113): ο δικός του αναγνώστης
# τομέων προχωρά track προς track, και η κεφαλή δεν πηγαινοέρχεται.
#
# ΣΥΜΠΙΕΣΜΕΝΑ ΑΠΟ ΤΟ ΒΗΜΑ 193 (tools/zx0.py, DESIGN §13.5): όλα εκτός από τον
# φορτωτή, που τον φορτώνει το BASIC, και τις σελίδες, που τις διαβάζει το
# παιχνίδι μία μία. Η τρίτη στήλη είναι πού ΞΕΔΙΠΛΩΝΕΙ ο φορτωτής το αρχείο —
# ένα όνομα του src/boot.asm, του build/layout.asm ή του src/const.asm, ή
# αριθμός — και η κεφαλίδα AMSDOS λέει πού φορτώνεται η ροή: στο τέλος του
# προορισμού, με το περιθώριό της (zx0.unpack), ώστε να ξεδιπλωθεί πάνω του.
# Η τέταρτη είναι πού σταματά το περιθώριο: η ροή δεν φτάνει εκεί.
#
# ΟΙ ΤΡΑΠΕΖΕΣ 6 ΚΑΙ 7 ΕΝΑ ΑΡΧΕΙΟ Η ΚΑΘΕΜΙΑ: ως το βήμα 192 ο φορτωτής μηδένιζε
# την 6 και έφερνε τρία αρχεία (BANK6, B6CODE, B6TAIL), και στην 7 δύο (BANK7,
# TEXT). Τώρα τα ενώνει το banks() με την ίδια σειρά, και ο φορτωτής φέρνει
# ολόκληρη την τράπεζα: τα μηδενικά δεν κοστίζουν σχεδόν τίποτα συμπιεσμένα.
FILES = [
    ("LOADER.BIN",  "boot.bin",   0x9000,       None),
    ("MENU.BIN",    "menu.bin",   "MW_ORG",     0x8000),    # το μενού πάνω σε κόσμο (βήμα 130)
    ("BANK6.BIN",   "bank6",      0x4000,       "GEN_END"), # όλη η 6: + b6code (βήμα 92) + ουρές (188)
    ("BANK7.BIN",   "bank7",      0x4000,       "GEN_END"), # όλη η 7: + τα κείμενα στο G_text
    ("BANK1.BIN",   "bank1c.bin", "OV_LOAD",    "GEN_END"), # ο κώδικας των τρυπών (βήμα 102),
                                                            # τα εικονίδια, ο κώδικας του b1code (βήμα 94)
    ("PAGE2.BIN",   "page2.bin",  "SCRATCH",    "OV_LOAD"), # ως την BANK1.BIN, που ήρθε πριν
    ("BANK5.BIN",   "bank5c.bin", "B5_BASE",    "GEN_END"), # οι διάδρομοι, το ευρετήριο, οι αρμοί,
                                                            # ο κώδικας του b5code (βήμα 97)
    ("GAME2.BIN",   "game2.bin",  "SCRATCH_G2", "B5_BASE"), # ως την BANK5.BIN, που ήρθε πριν
    ("GAME.BIN",    "game.bin",   "GAME_TMP",   0x8000),    # στην τράπεζα 4, και από εκεί στο #0100
    ("GEN.BIN",     "gen.bin",    "GEN_ORG",    "GEN_END"),
    # ΟΙ ΣΕΛΙΔΕΣ ΤΟΥ TUTORIAL (βήμα 175, tools/tupages.py): ASCII, χωρίς
    # κεφαλίδα, και δεν τις φορτώνει ο φορτωτής. Τις διαβάζει το παιχνίδι μία
    # μία, βρίσκοντας το αρχείο στον κατάλογο (src/tpage.asm).
    ("TUTOR.TXT",   "tutor.txt",  None,         None),
]
PLAIN = {"LOADER.BIN", "TUTOR.TXT"}                     # χωρίς συμπίεση


@functools.lru_cache(maxsize=None)
def equs():
    """Τα equ του src/const.asm και του build/layout.asm, όπως τα βλέπει ο
    φορτωτής που τα κάνει include (rasm -sq σε ένα αρχείο μόνο με τα δύο)."""
    work = os.path.join(BUILD, "zx0")
    os.makedirs(work, exist_ok=True)
    probe = os.path.join(work, "equ.asm")
    open(probe, "w").write('        include "../../src/const.asm"\n'
                           '        include "../layout.asm"\n')
    r = subprocess.run([RASM, "equ.asm", "-s", "-sq", "-os", "equ.sym", "-o", "equ"],
                       cwd=work, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"το equ.asm απέτυχε:\n{r.stdout}{r.stderr}")
    out = {}
    for line in open(os.path.join(work, "equ.sym"), encoding="utf-8", errors="replace"):
        p = line.split()
        if len(p) >= 2 and p[1].startswith("#"):
            out[p[0].upper()] = int(p[1][1:], 16)
    return out


def addr(v):
    """Ενας αριθμός, ή το όνομά του: του φορτωτή, του μενού, ή των equ."""
    if isinstance(v, int):
        return v
    if v == "MW_ORG":
        import menuworld
        return menuworld.geom()["MW_ORG"]
    if v in ("SCRATCH", "SCRATCH_G2", "OV_LOAD", "GAME_TMP", "GEN_ORG"):
        return boot_equ(v)
    if v == "GEN_END":
        return GEN_END
    return equs()[v]


@functools.lru_cache(maxsize=None)
def banks():
    """Οι τράπεζες 6 και 7 ολόκληρες, όπως τις άφηνε ο φορτωτής ως το βήμα
    192: η 6 μηδέν, η BANK6.BIN του pack.py, ο κώδικας του τροχού στο
    G_b6code και οι ουρές στο B6T_0· η 7 του pack.py με τα κείμενα στο
    G_text."""
    e = equs()

    def put(img, at, piece, what):
        off = at - 0x4000
        if off < 0 or off + len(piece) > 0x4000:
            sys.exit(f"το {what} ({len(piece)} bytes στο #{at:04X}) βγαίνει από την τράπεζα")
        img[off:off + len(piece)] = piece

    def raw(name):
        return open(os.path.join(BUILD, name), "rb").read()

    b6 = bytearray(0x4000)
    put(b6, 0x4000, raw("bank6.bin"), "bank6.bin")
    put(b6, e["G_B6CODE"], raw("b6code.bin"), "b6code.bin")
    put(b6, e["B6T_0"], raw("b6tail.bin"), "b6tail.bin")
    b7 = bytearray(raw("bank7.bin"))
    put(b7, e["G_TEXT"], raw("text.bin"), "text.bin")
    return bytes(b6), bytes(b7)


def staged(name, src):
    """Τα bytes του αρχείου ΟΠΩΣ ΞΕΔΙΠΛΩΝΟΝΤΑΙ: ό,τι θα βρει ο φορτωτής."""
    if src == "bank6":
        return banks()[0]
    if src == "bank7":
        return banks()[1]
    return open(os.path.join(BUILD, src), "rb").read()


@functools.lru_cache(maxsize=None)
def packed(name, src):
    """(τα bytes στον δίσκο, πού φορτώνονται, πού σταματά η ροή). Για τα
    συμπιεσμένα: η ροή ZX0 στο τέλος του προορισμού με το περιθώριό της."""
    import zx0
    data = staged(name, src)
    if name in PLAIN:
        return data, None, None
    z = zx0.pack(data, name)
    _, margin = zx0.unpack(z)
    dest = addr(dict((f[0], f[2]) for f in FILES)[name])
    end = dest + len(data) + margin
    return z, end - len(z), end


def run(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"{' '.join(cmd)} απέτυχε:\n{r.stdout}{r.stderr}")
    return r.stdout


def assemble():
    """Τα τρία .asm που βγάζουν τα φορτώσιμα κομμάτια."""
    src = os.path.join(ROOT, "src")
    for tool in ("mkoffsets.py", "pack.py", "mknew.py"):
        run([sys.executable, os.path.join(HERE, tool)])
    # Το main.asm γράφει ΚΑΙ το game.bin ΚΑΙ το game2.bin με save.
    run([RASM, "main.asm", "-oi", os.path.join(BUILD, "main.sna"), "-v2", "-s"], cwd=src)
    run([RASM, "gen.asm",  "-oi", os.path.join(BUILD, "gen.sna"),  "-v2"], cwd=src)
    # Το μενού (βήμα 130): οι κόσμοι του από το tools/menuworld.py, και τα
    # σύμβολά του για το tests/test_menu.py.
    import menuworld
    menuworld.write()
    run([RASM, "menu.asm", "-oi", os.path.join(BUILD, "menu.sna"), "-v2",
         "-s", "-os", os.path.join(BUILD, "menu.sym")], cwd=src)
    write_disc_tab()
    # Τα σύμβολα του φορτωτή χωριστά (βήμα 113): το tests/test_disc.py δοκιμάζει
    # τις ρουτίνες του αναγνώστη τομέων μία μία.
    run([RASM, "boot.asm", "-oi", os.path.join(BUILD, "boot.sna"), "-v2",
         "-s", "-os", os.path.join(BUILD, "boot.sym")], cwd=src)


def write_disc_tab():
    """build/disc_tab.asm: το BAR_K του φορτωτή (βήμα 130). Η μπάρα των αρχείων
    έχει BAR_FILES bytes· μετά από κάθε αρχείο ο φορτωτής προσθέτει τομείς x
    BAR_K σε ένα 8.8, και το πάνω byte είναι ως πού γεμίζει. Οι τομείς ενός
    αρχείου: η κεφαλίδα AMSDOS και το μήκος του, ανά 512 — όπως τους μετρά ο
    φορτωτής από το lf_len. Μετριούνται τα αρχεία του ΠΑΙΧΝΙΔΙΟΥ: όχι ο
    φορτωτής (τον φορτώνει το BASIC) και όχι το μενού (πριν από τη μπάρα).
    Από το βήμα 193 οι τομείς των ροών ZX0, όσοι διαβάζονται."""
    import menuworld
    files = menuworld.geom()["BAR_FILES"]
    sect = 0
    for name, src, load, _ in FILES:
        if name in ("LOADER.BIN", "MENU.BIN") or load is None:
            continue
        sect += (len(packed(name, src)[0]) + 128 + 511) // 512
    k = files * 256 // sect
    assert 0 < k < 256 and k * sect <= files * 256
    with open(os.path.join(BUILD, "disc_tab.asm"), "w", encoding="utf-8") as f:
        f.write("; ΠΑΡΑΓΕΤΑΙ από το tools/mkdsk.py (βήμα 130) — μην το επεξεργάζεσαι.\n"
                f"; {sect} τομείς στα αρχεία του παιχνιδιού, {files} bytes μπάρας.\n"
                f"BAR_K equ {k}\n")


# Ο κώδικας της τράπεζας 0 δεν επιτρέπεται να φτάσει εδώ: στο #3F80 ο φορτωτής
# αφήνει το επίμετρό του, και το αντιγράφει ΑΦΟΥ φορτώσει το παιχνίδι. Αν το
# game.bin έφτανε ως εκεί, το επίμετρο θα έγραφε πάνω σε κώδικα που πρόκειται
# να τρέξει — και θα φαινόταν ως τυχαίο κρέμασμα μετά το φόρτωμα, όχι ως
# σφάλμα build. Ηταν #3E00 ως το βήμα 26: το επίμετρο είναι σαράντα bytes και
# κρατούσε πεντακόσια δώδεκα (βλ. src/boot.asm).
def endgame_addr():
    """Το ταβάνι της τράπεζας 0, διαβασμένο ΑΠΟ ΤΟ src/boot.asm."""
    for line in open(os.path.join(ROOT, "src", "boot.asm"), encoding="utf-8"):
        m = re.match(r"ENDGAME\s+equ\s+#([0-9A-Fa-f]+)", line)
        if m:
            return int(m.group(1), 16)
    sys.exit("δεν βρέθηκε το ENDGAME στο src/boot.asm")


ENDGAME = endgame_addr()


def boot_equ(name):
    """Μια σταθερά του φορτωτή, διαβασμένη από το src/boot.asm — όπως το
    ENDGAME, για να μην υπάρχει δεύτερο αντίγραφο που θα διαφωνήσει."""
    for line in open(os.path.join(ROOT, "src", "boot.asm"), encoding="utf-8"):
        m = re.match(rf"{name}\s+equ\s+#([0-9A-Fa-f]+)", line)
        if m:
            return int(m.group(1), 16)
    sys.exit(f"δεν βρέθηκε το {name} στο src/boot.asm")


# ΤΟ ΠΡΟΧΕΙΡΟ ΤΟΥ ΦΟΡΤΩΤΗ. Τα δύο αρχεία που πατάνε πάνω στο AMSDOS — τα
# δεδομένα της τράπεζας 2 και ο κώδικάς της — φορτώνονται σε πρόχειρο, το ένα
# στο SCRATCH και το άλλο στο SCRATCH_G2, και τα αντιγράφει το επίμετρο. Ως το
# βήμα 85 και τα δύο ΣΤΗΝ ΙΔΙΑ ΤΡΑΠΕΖΑ 5: αν το πρώτο έφτανε ως το δεύτερο, το
# δεύτερο το έσβηνε χωρίς κανένα λάθος.
#
# ΑΥΤΟ ΣΥΝΕΒΑΙΝΕ ΩΣ ΤΟ ΒΗΜΑ 33: το page2.bin ήταν 11.384 bytes απέναντι σε
# 11.264, και τα τελευταία 120 — ακριβώς η κρυφή μνήμη του HUD — έφταναν στο
# παιχνίδι γεμάτα κώδικα της τράπεζας 2. Αβλαβές ΜΟΝΟ επειδή εκείνη η κρυφή
# μνήμη ακυρώνεται πριν διαβαστεί· ένα byte πραγματικών δεδομένων από κάτω της
# θα ήταν σφάλμα που φαίνεται μόνο από τον δίσκο και ποτέ από το snapshot.
SCRATCH = boot_equ("SCRATCH")
SCRATCH_G2 = boot_equ("SCRATCH_G2")
ICONS = boot_equ("ICONS")
OV_LOAD = boot_equ("OV_LOAD")

# Τα slots του §11 ζουν στα tracks 24-41, ΧΩΡΙΣ αρχείο AMSDOS από πάνω τους: ο
# δίσκος είναι του παιχνιδιού. Αυτό ισχύει όσο τα αρχεία δεν φτάνουν ως εκεί —
# και αυτό ελέγχεται, γιατί ένα αρχείο που θα έμπαινε στο track 24 θα σβηνόταν
# στο πρώτο σώσιμο, χωρίς κανένα μήνυμα.
SAVE_T0 = 24

# Ο κώδικας της τράπεζας 2 τελειώνει εδώ: πάνω από το #C000 δεν υπάρχει τράπεζα
# 2, υπάρχει η ΟΘΟΝΗ. Ενα game2.bin που ξεπερνά το όριο θα αντιγραφόταν από τον
# φορτωτή πάνω στην εικόνα και θα έτρεχε από εκεί — δηλαδή δεν θα έτρεχε.
PAGE2_END = 0xC000

# Η γεννήτρια φορτώνεται στο #8000 και ΔΕΝ επιτρέπεται να φτάσει στη στοίβα του
# BASIC (#8F00-#8FFF, από το MEMORY &8FFF του stub) ούτε στον φορτωτή (#9000).
# Το AMSDOS είναι ακόμη ζωντανό όταν τρέχει, και το BASIC περιμένει να γυρίσει.
GEN_END = 0x8F00


def symbols():
    sym = {}
    for line in open(os.path.join(ROOT, "src", "rasmoutput.sym"),
                     encoding="utf-8", errors="replace"):
        p = line.split()
        if len(p) >= 2 and p[1].startswith("#"):
            sym[p[0].upper()] = int(p[1][1:], 16)
    return sym


def check_page2(sym):
    # Το game2.bin αρχίζει από τον κώδικα της εκκίνησης, στο τέλος του GH_BUF
    # (βήμα 158, src/startup.asm): ως τότε από το PAGE2_CODE.
    lo, hi = sym["ZZ_BOOT"], sym["ZZ_PAGE2_END"]
    if hi > PAGE2_END:
        sys.exit(f"ο κώδικας της τράπεζας 2 φτάνει στο #{hi:04X} και ξεπερνά "
                 f"το #{PAGE2_END:04X} ({hi - PAGE2_END} bytes πάνω από το όριο)")
    return lo, PAGE2_END - hi


# ΚΑΙ ΕΝΑ ΔΕΥΤΕΡΟ ΠΑΤΩΜΑ, ΠΙΟ ΧΑΜΗΛΑ: ΟΙ ΔΟΚΙΜΕΣ. Το tests/plane.asm και δύο
# probes του tests/test_disc.py τρέχουν στο #3EC0 — εκεί δειγματίζουν το επίπεδο
# κόσμου, που ζει σε σελιδοποιημένη τράπεζα και δεν διαβάζεται αλλιώς από τον
# εξομοιωτή. Ολα γράφουν και τον buffer τους στο #3F00.
#
# ΑΥΤΟ ΤΟ ΠΑΤΩΜΑ ΗΤΑΝ ΑΓΡΑΦΟ ΩΣ ΤΟ ΒΗΜΑ 31, και το πλήρωσε μια ώρα: 350 bytes
# μετακόμισαν στην τράπεζα 0, ο κώδικας έφτασε στο #3EA3, και το test_save
# άρχισε να σβήνει κώδικα του παιχνιδιού λίγο πριν τον δοκιμάσει. Το μήνυμα που
# έβγαινε ήταν «ο δίσκος δεν σώζει» — δηλαδή κατηγορούσε ακριβώς το πράγμα που
# δούλευε. Ενα build που σταματά είναι μια ώρα φθηνότερο.
#
# Το ίδιο το βήμα 31 το ανέβασε από το #3E00 στο #3EC0 — 192 bytes πίσω στην
# τράπεζα 0, επειδή η σκαλωσιά είναι 33 bytes κώδικα και 256 buffer, όχι 512.
# Αν χρειαστούν και τα υπόλοιπα 320, ο δρόμος είναι να πάρει η σκαλωσιά τη
# διεύθυνσή της από το σύμβολο ZZ_BANK0_END και ο buffer της να πάει στο
# GH_BUF της τράπεζας 2 — όχι να κατέβει το πάτωμα σιωπηλά.
TEST_FLOOR = 0x3EC0


def check_fit():
    n = os.path.getsize(os.path.join(BUILD, "game.bin"))
    top = 0x0100 + n
    if top > ENDGAME:
        sys.exit(f"ο κώδικας της τράπεζας 0 φτάνει στο #{top:04X} και πατά το "
                 f"επίμετρο του φορτωτή στο #{ENDGAME:04X} "
                 f"({top - ENDGAME} bytes πάνω από το όριο)")
    if top > TEST_FLOOR:
        sys.exit(f"ο κώδικας της τράπεζας 0 φτάνει στο #{top:04X} και πατά τη "
                 f"σκαλωσιά των δοκιμών στο #{TEST_FLOOR:04X} "
                 f"({top - TEST_FLOOR} bytes πάνω): το tests/plane.asm και τα "
                 f"probes των test_disc/test_save τρέχουν εκεί και θα σβήσουν "
                 f"κώδικα του παιχνιδιού πριν τον δοκιμάσουν")
    # ΤΟ ΝΟΥΜΕΡΟ ΠΟΥ ΜΕΤΡΑΕΙ ΕΙΝΑΙ ΤΟ ΜΙΚΡΟΤΕΡΟ. Ως το βήμα 31 τυπωνόταν η
    # απόσταση ως το επίμετρο, που είναι 192 bytes πιο ψηλά από το πάτωμα των
    # δοκιμών: το «έχεις 512 ελεύθερα» ήταν 320 ελεύθερα και μια δοκιμή που
    # σπάει χωρίς να πει γιατί.
    return min(ENDGAME, TEST_FLOOR) - top


def check_saves():
    """Κανένα αρχείο δεν φτάνει στην περιοχή των slots."""
    d = Dsk(DSK)
    top = 0
    for si in range(4):
        sec = d.sector(0, 0xC1 + si)
        for e in range(0, len(sec), 32):
            if sec[e] == 0xE5:                  # σβησμένη εγγραφή
                continue
            for b in sec[e + 16:e + 32]:
                if b:
                    top = max(top, b)
    track = (top * 2) // 9                      # 1 KB ανά block, 9 τομείς/track
    if track >= SAVE_T0:
        sys.exit(f"τα αρχεία φτάνουν ως το track {track}· τα slots ξεκινούν "
                 f"στο {SAVE_T0}")
    return track


def b5_base():
    """Πού αρχίζουν οι μηχανές στην τράπεζα 5, από το layout."""
    for line in open(os.path.join(BUILD, "layout.asm"), encoding="utf-8"):
        m = re.match(r"B5_BASE\s+equ\s+#([0-9A-Fa-f]+)", line)
        if m:
            return int(m.group(1), 16)
    sys.exit("δεν βρέθηκε το B5_BASE στο build/layout.asm")


def check_ovl():
    """Ο κώδικας που το ov_install μοιράζει στις τρύπες (βήμα 101,
    src/demolish.asm· από το βήμα 155 στις τράπεζες 1 και 5, src/ov_inst.asm)
    έρχεται στο OV_LOAD, στην αρχή της BANK1.BIN (βήμα 102).
    Ο φορτωτής και το παιχνίδι το ξέρουν χωριστά, και πρέπει να είναι το ίδιο:
    το src/main.asm σώζει το bank1c.bin από το δικό του OV_LOAD ως το #8000, ο
    φορτωτής το φορτώνει στο δικό του. (Ενα equ δεν βγαίνει στο
    rasmoutput.sym· το μήκος του αρχείου το λέει.)"""
    n1 = os.path.getsize(os.path.join(BUILD, "bank1c.bin"))
    if OV_LOAD + n1 != 0x8000:
        sys.exit(f"το bank1c.bin ({n1} bytes) αρχίζει στο #{0x8000 - n1:04X} "
                 f"του src/main.asm, και ο φορτωτής το φορτώνει στο OV_LOAD "
                 f"(#{OV_LOAD:04X}): ο κώδικας των τρυπών θα ερχόταν αλλού από "
                 f"εκεί που τον ψάχνει το ov_install")


def check_scratch():
    n2 = os.path.getsize(os.path.join(BUILD, "page2.bin"))
    ng = os.path.getsize(os.path.join(BUILD, "game2.bin"))
    # Από το βήμα 86 σε δύο τράπεζες: τα δεδομένα της τράπεζας 2 στη βασική
    # τράπεζα 1 κάτω από τα εικονίδια, ο κώδικάς της στην τράπεζα 5 κάτω από
    # τις μηχανές, που φορτώνονται κατευθείαν στη θέση τους. Στην τράπεζα 5 και
    # τα τρία μαζί ήταν 16.475 bytes — 91 πάνω από ολόκληρη την τράπεζα.
    if SCRATCH + n2 > OV_LOAD:
        sys.exit(f"το page2.bin ({n2} bytes) φτάνει από το #{SCRATCH:04X} ως το "
                 f"#{SCRATCH + n2:04X} και σβήνεται από το bank1c.bin στο "
                 f"#{OV_LOAD:04X} ({SCRATCH + n2 - OV_LOAD} bytes)")
    base = b5_base()
    if SCRATCH_G2 + ng > base:
        sys.exit(f"το game2.bin ({ng} bytes) φτάνει ως το #{SCRATCH_G2 + ng:04X} "
                 f"και σβήνει τις μηχανές στο #{base:04X} "
                 f"({SCRATCH_G2 + ng - base} bytes πάνω)")
    return OV_LOAD - SCRATCH - n2


def build():
    assemble()
    slack = check_fit()
    check_scratch()
    sym = symbols()
    check_ovl()
    lo, slack2 = check_page2(sym)
    gen_top = 0x8000 + os.path.getsize(os.path.join(BUILD, "gen.bin"))
    if gen_top > GEN_END:
        sys.exit(f"η γεννήτρια φτάνει στο #{gen_top:04X} και πατά τη στοίβα του "
                 f"BASIC στο #{GEN_END:04X} ({gen_top - GEN_END} bytes πάνω)")
    # ΚΑΘΕ ΡΟΗ ΧΩΡΑ ΕΚΕΙ ΠΟΥ ΦΟΡΤΩΝΕΤΑΙ (βήμα 193): από την αρχή του
    # προορισμού ως το τέλος του με το περιθώριο, και όχι ως το επόμενο
    # πράγμα που ήδη κάθεται εκεί — την BANK1.BIN κάτω από την PAGE2.BIN, τις
    # μηχανές κάτω από το GAME2.BIN, τη στοίβα του BASIC κάτω από τη γεννήτρια.
    for name, src, dest, ceil in FILES:
        if name in PLAIN:
            continue
        z, at, end = packed(name, src)
        if at < addr(dest):
            sys.exit(f"η ροή του {name} ({len(z)} bytes) είναι μεγαλύτερη από τα "
                     f"bytes της και αρχίζει στο #{at:04X}, πριν από τον "
                     f"προορισμό της (#{addr(dest):04X})")
        if end > addr(ceil):
            sys.exit(f"η ροή του {name} φτάνει ως το #{end:04X}, πάνω από το "
                     f"{ceil} (#{addr(ceil):04X})")
    print(f"τράπεζα 0: {slack} bytes ως τη σκαλωσιά των δοκιμών· "
          f"τράπεζα 2: κώδικας στο #{lo:04X}, {slack2} bytes ως το #C000· "
          f"γεννήτρια ως το #{gen_top:04X}, {GEN_END - gen_top} bytes ως τη "
          f"στοίβα του BASIC")
    ents = entries()
    write_disc(DSK, ents)
    total = sum(len(e[1]) for e in ents)
    raw = len(STUB) + sum(len(staged(n, s)) for n, s, _, _ in FILES)
    print(f"στον δίσκο {total} bytes, {raw} ξεδιπλωμένα (ZX0, βήμα 193)")
    return total


def entries():
    """Τα αρχεία του δίσκου με τη σειρά τους: (όνομα, bytes, load, exec), με
    load None για ASCII. Η κεφαλίδα των συμπιεσμένων λέει πού φορτώνεται η
    ροή (ο φορτωτής φορτώνει εκεί, και το AMSDOS της εφεδρείας επίσης)· του
    φορτωτή, πού φορτώνεται και τρέχει."""
    out = [("HABITAT.BAS", STUB.encode("ascii"), None, None)]
    for name, src, dest, _ in FILES:
        data, at, _ = packed(name, src)
        if dest is None:                        # ASCII (βήμα 175)
            out.append((name, data, None, None))
        elif name in PLAIN:
            out.append((name, data, dest, dest))
        else:
            out.append((name, data, at, 0))
    return out


def variant(path, name, data, margin=None):
    """Ο δίσκος του build με το αρχείο name ξανά από τα ξεδιπλωμένα bytes data,
    για τις δοκιμές (βήμα 193): ένα byte αλλαγμένο μέσα σε μια ροή ZX0 δεν
    είναι ένα byte αλλαγμένο στο αρχείο. Η ροή μπαίνει όπως παντού, στο τέλος
    του προορισμού με το περιθώριό της — ή με όποιο περιθώριο δοθεί."""
    import zx0
    dest = addr(dict((f[0], f[2]) for f in FILES)[name])
    ents = []
    for e in entries():
        if e[0] == name:
            z = zx0.pack(data, "variant")
            if margin is None:
                _, margin = zx0.unpack(z)
            e = (name, z, dest + len(data) + margin - len(z), 0)
        ents.append(e)
    write_disc(path, ents)
    return path


def write_disc(path, ents):
    """Ενας δίσκος με αυτά τα αρχεία, EXTENDED. Το καλούν και οι δοκιμές
    (tests/test_disc.py), για δίσκους με ένα αρχείο αλλαγμένο."""
    stage = path + ".d"
    shutil.rmtree(stage, ignore_errors=True)
    os.makedirs(stage)
    if os.path.exists(path):
        os.remove(path)
    run([IDSK, path, "-n"])
    for name, data, load, exe in ents:
        f = os.path.join(stage, name)
        open(f, "wb").write(data)
        if load is None:
            run([IDSK, path, "-i", f, "-t", "0"])
        else:
            run([IDSK, path, "-i", f, "-t", "1", "-c", f"{load:04X}", "-e", f"{exe:04X}"])
    # EXTENDED (βήμα 183, tools/dsk.py): το τυπικό του iDSK το χαλούσε ο Retro
    # Virtual Machine στο πρώτο σώσιμο, κρατώντας μόνο το track του.
    data = to_extended(open(path, "rb").read())
    open(path, "wb").write(data)


if __name__ == "__main__":
    total = build()
    last = check_saves()
    print(f"αρχεία ως το track {last}· slots στα {SAVE_T0}-41 "
          f"({(42 - SAVE_T0) // 6} x 6 tracks)")
    print(run([IDSK, DSK, "-l"]).rstrip())
    print(f"build/habitat.dsk: {len(FILES)} αρχεία, {total} bytes")
