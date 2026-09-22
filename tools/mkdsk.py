#!/usr/bin/env python3
"""build/habitat.dsk — ο δίσκος (DESIGN §13).

Το παιχνίδι δεν είναι ένα αρχείο. Είναι επτά: ο φορτωτής, ο κώδικας της
τράπεζας 0, ο κώδικας της τράπεζας 2, η γεννήτρια, και οι τέσσερις εικόνες
δεδομένων. Το AMSDOS δίνει ΜΙΑ διεύθυνση φόρτωσης ανά αρχείο και δεν ξέρει από
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
από εκεί πόσα bytes να φέρει. Για τα υπόλοιπα η διεύθυνση της επικεφαλίδας
αγνοείται — το CAS IN DIRECT φορτώνει όπου του πει ο φορτωτής στο HL — αλλά
γράφεται σωστή ούτως ή άλλως, για να λέει το cat την αλήθεια.
"""
import os, shutil, subprocess, sys

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

FILES = [
    ("LOADER.BIN",  "boot.bin",  0x9000, 0x9000),
    ("GAME.BIN",    "game.bin",  0x0100, 0x0000),
    ("GAME2.BIN",   "game2.bin", 0xB440, 0x0000),
    ("GEN.BIN",     "gen.bin",   0x8000, 0x8000),
    ("PAGE2.BIN",   "page2.bin", 0x8000, 0x0000),
    ("BANK1.BIN",   "bank1.bin", 0x7000, 0x0000),
    ("BANK6.BIN",   "bank6.bin", 0x4000, 0x0000),
    ("BANK7.BIN",   "bank7.bin", 0x4000, 0x0000),
]


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
    run([RASM, "boot.asm", "-oi", os.path.join(BUILD, "boot.sna"), "-v2"], cwd=src)


def build():
    assemble()
    stage = os.path.join(BUILD, "dsk")
    shutil.rmtree(stage, ignore_errors=True)
    os.makedirs(stage)
    if os.path.exists(DSK):
        os.remove(DSK)
    run([IDSK, DSK, "-n"])
    bas = os.path.join(stage, "HABITAT.BAS")
    open(bas, "w", newline="", encoding="ascii").write(STUB)
    run([IDSK, DSK, "-i", bas, "-t", "0"])
    total = os.path.getsize(bas)
    for name, src, load, exe in FILES:
        path = os.path.join(BUILD, src)
        total += os.path.getsize(path)
        shutil.copy(path, os.path.join(stage, name))
        run([IDSK, DSK, "-i", os.path.join(stage, name),
             "-t", "1", "-c", f"{load:04X}", "-e", f"{exe:04X}"])
    return total


if __name__ == "__main__":
    total = build()
    print(run([IDSK, DSK, "-l"]).rstrip())
    print(f"build/habitat.dsk: {len(FILES)} αρχεία, {total} bytes")
