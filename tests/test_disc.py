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
  4. Ο κόσμος είναι ΠΑΡΑΓΜΕΝΟΣ: η γεννήτρια έτρεξε ως ξεχωριστό φόρτωμα και
     γέμισε την τράπεζα 4. Το snapshot φορτώνει έτοιμο επίπεδο· ο δίσκος δεν
     έχει τέτοιο αρχείο.
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


def main():
    sym, g = build()
    from cpc import CPC
    smap, blob = load_map(), load_bin()
    f = smap["font_gfx"]
    font = blob[f.off:f.off + f.size]
    glyph = {bytes(font[i * 16:(i + 1) * 16]): chr(32 + i) for i in range(96)}

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
    for _ in range(120):          # η γεννήτρια μόνη της θέλει 13,5 s
        m.run_frames(30)
        frames += 30
        started = w16(g + 2) == 40 and m.peek(g + 58) == 4
        if seen_title is None and frames >= 300:
            ram = scr()
            # ο φορτωτής μετράει σειρές από το 1 (firmware), η μνήμη από το 0
            seen_title = (inked(ram, 4, 3), inked(ram, 0, 2))
        # ΜΟΝΟ ΟΣΟ ΦΟΡΤΩΝΕΙ: μόλις ξεκινήσει το παιχνίδι, τα bytes της μπάρας
        # είναι εικόνα του κάδρου. Το όριο ήταν σταθερός αριθμός frames και
        # έσπασε μόλις μπήκε ένα ένατο αρχείο στον δίσκο (§4.2).
        if frames >= 300 and not started:
            bars.append(bar_bytes(scr()))
        # Και ο ΗΧΟΣ της αναμονής (§9.5): η γεννήτρια έχει δικό της παίκτη,
        # γιατί ο ήχος του παιχνιδιού ζει στην τράπεζα 2 που δεν υπάρχει ακόμη.
        # Δειγματοληψία ανά 30 frames· μια νότα κρατά ~25, οπότε περνούν όλες
        # από μπροστά μας έστω μία φορά.
        if not started:
            r = m.psg_regs()
            tones.append((r[0] | ((r[1] & 15) << 8), r[8], r[10]))
        if started:
            running = True
            break
    check(running, f"το RUN\"HABITAT έφτασε στο game_new "
                   f"(PC=#{m.pc:04X}, τροφή {w16(g + 2)})")

    # --- 1β. η οθόνη φόρτωσης --------------------------------------------
    title, basic = seen_title
    check(title > 0 and basic == 0,
          f"η οθόνη φόρτωσης έσβησε το BASIC: {title} bytes τίτλου, "
          f"{basic} στις δύο πρώτες σειρές (εκεί έγραφε το «Amstrad 128K»)")
    # Η μπάρα είναι το ΜΟΝΟ πράγμα που κινείται επί 13,5 δευτερόλεπτα: πρέπει
    # να ξεκινά άδεια, να μη γυρίζει ποτέ πίσω, και να φτάνει ως το τέρμα.
    mono = all(b <= c for b, c in zip(bars, bars[1:]))
    check(bars and bars[0] == 0 and mono and max(bars) == 64,
          f"η μπάρα προχώρησε 0 -> {max(bars) if bars else 0} από 64, "
          f"μονότονα ({len(bars)} δείγματα)")

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
    check(50 <= stock[0] <= 60 and stock[1] == 40 and stock[2] == 60
          and stock[3] == 75 and stock[4] == 45 and stock[6] == 4 and pop == 4,
          f"§10.1 από τον δίσκο: {stock} πληθυσμός {pop}")

    # --- 3. το HUD είναι γραμμένο ----------------------------------------
    off = w16(sym["CAM_OFF"])
    ram = m.read_ram(0xC000, 0x4000)

    def byte(x, y):
        return ram[(y & 7) * 0x800 + (((y >> 3) * 80 + x + 2 * off) & 0x7FF)]

    row2 = "".join(glyph.get(bytes(byte(c * 2 + k, 176 + l)
                                   for l in range(8) for k in range(2)), "#")
                   for c in range(40))
    check(row2.startswith("POP  4/"), f"το HUD σχεδιάστηκε: |{row2}|")

    # --- 4. ο κόσμος είναι παραγμένος ------------------------------------
    m.run_code(0x3E00, open(os.path.join(ROOT, "build", "plane.bin"), "rb").read())
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

    m.screenshot(os.path.join(ROOT, "build", "disc.png"), aspect=True)

    # --- 5. το σβήσιμο της οθόνης ----------------------------------------
    # Ο φορτωτής αφήνει τη δική του οθόνη και το παιχνίδι ξεκινά ΠΑΝΩ της. Ως
    # το βήμα 21 το «run"habitat» φαινόταν γραμμένο μέσα στην αποικία μέχρι την
    # πρώτη πλήρη σχεδίαση. Εδώ ελέγχεται η ίδια η ρουτίνα, με σημάδι.
    m.write_ram(0xC000, bytes([0xAA]) * 0x4000)
    m.run_code(0x3E00, bytes([0xCD, sym["HW_CLEAR"] & 0xFF,
                              sym["HW_CLEAR"] >> 8, 0x18, 0xFE]))
    m.run_frames(10)                     # 16 KB ldir = 86 ms, δηλαδή 4,3 frames
    left = sum(1 for b in m.read_ram(0xC000, 0x4000) if b)
    check(left == 0, f"το hw_clear σβήνει και τα 16 KB της οθόνης ({left} bytes "
                     f"έμειναν)")
    print(f"\nεκκίνηση: {frames} frames = {frames / 50:.0f} s από το ENTER ως "
          f"την αποικία (τα 13,5 είναι η γεννήτρια)")
    print(f"build/habitat.dsk: {os.path.getsize(DSK)} bytes, "
          f"build/disc.png γράφτηκε")
    if FAIL:
        print(f"\nΑΠΟΤΥΧΙΑ — {len(FAIL)}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
