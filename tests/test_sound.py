#!/usr/bin/env python3
"""Ο ήχος, όπως τον βλέπει ο ΙΔΙΟΣ Ο AY (DESIGN §9.5).

Ο εξομοιωτής δίνει τώρα τους 16 καταχωρητές του AY-3-8912
(`cpcemu_psg_reg`), οπότε αυτή η δοκιμή δεν ρωτά τον κώδικα τι νομίζει ότι
έπαιξε: ρωτά τον ήχο τι άκουσε. Ολη η αλυσίδα μπαίνει μέσα — πίνακας εφέ,
snd_tick, το πρωτόκολλο του PPI, ο PSG.

Τέσσερις ισχυρισμοί:

  1. ΤΟ ΠΡΩΤΟΚΟΛΛΟ φτάνει. Χωρίς αυτό δεν αλλάζει ΚΑΝΕΝΑΣ καταχωρητής και τα
     πάντα σιωπούν αθόρυβα — ακριβώς το είδος βλάβης που δεν φαίνεται.
  2. ΚΑΘΕ ΕΦΕ, tick προς tick, ταυτόσημο με αναφορά γραμμένη σε Python από την
     προδιαγραφή της μορφής, που διαβάζει τα ΙΔΙΑ bytes από τη μνήμη.
  3. Η ΠΡΟΤΕΡΑΙΟΤΗΤΑ: ο κέρσορας δεν κόβει τον συναγερμό, ο συναγερμός κόβει
     τον κέρσορα, και στο τέλος κάθε εφέ το κανάλι μένει σιωπηλό και ελεύθερο.
  4. ΤΟ ΠΛΗΚΤΡΟΛΟΓΙΟ ΕΠΙΖΕΙ. Ηχος και πλήκτρα περνούν από το ίδιο PPI και από
     την ίδια θύρα Α· μια λάθος κατεύθυνση θύρας ή ένα bit 6 στον R7 σβήνει το
     πληκτρολόγιο. Εδώ σαρώνονται εναλλάξ.
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")

RASM = os.path.expanduser("~/rasm/rasm.exe")
SNA = os.path.join(ROOT, "build", "sndtest.sna")
FRAME_US = 19968
FAIL = []

FX = ["MOVE", "MENU", "DENY", "BUILD", "DONE", "SHIP", "ALERT", "DEATH"]


def check(ok, msg):
    print(("OK " if ok else "ΛΑΘΟΣ ") + msg)
    if not ok:
        FAIL.append(msg)


def build():
    for tool in ("mkoffsets.py", "pack.py"):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", tool)],
                           capture_output=True, text=True)
        if r.returncode:
            sys.exit(f"{tool} απέτυχε:\n{r.stdout}{r.stderr}")
    r = subprocess.run([RASM, "sndtest.asm", "-oi", SNA, "-v2", "-s", "-eo"],
                       cwd=HERE, capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(SNA):
        sys.exit("rasm απέτυχε:\n" + r.stdout + r.stderr)
    sym = {}
    for line in open(os.path.join(HERE, "rasmoutput.sym"),
                     encoding="utf-8", errors="replace"):
        p = line.split()
        if len(p) >= 2 and p[1].startswith("#"):
            sym[p[0].upper()] = int(p[1][1:], 16)
    return sym


def boot(sym):
    from cpc import CPC
    m = CPC()
    m.run_frames(60)
    assert m.quickload(SNA), "quickload απέτυχε"
    n = 0
    while m.peek(sym["DONE_FLAG"]) != 0x5A and n < 300:
        m.run_frames(1)
        n += 1
    assert m.peek(sym["DONE_FLAG"]) == 0x5A, "το harness δεν ξεκίνησε"
    return m


def entry(m, sym, name, limit=600):
    m.poke(sym["DONE_FLAG"], 0)
    m.set_pc(sym[name])
    n = 0
    while m.peek(sym["DONE_FLAG"]) != 0x5A and n < limit:
        m.run_frames(1)
        n += 1
    assert m.peek(sym["DONE_FLAG"]) == 0x5A, f"{name}: PC=#{m.pc:04X}"
    return n


def play(m, sym, fx):
    m.poke(sym["REQ"], fx)
    entry(m, sym, "DO_PLAY")


def tick(m, sym, n=1):
    m.poke(sym["REQ"], n)
    return entry(m, sym, "DO_TICK")


# --- η αναφορά -------------------------------------------------------------
# Γραμμένη από την προδιαγραφή της μορφής (κεφαλίδα του src/sound.asm), όχι από
# τον κώδικα. Διαβάζει τα ΙΔΙΑ bytes εφέ από τη μνήμη του εξομοιωτή: αυτό που
# δοκιμάζεται είναι ο παίκτης, όχι τα δεδομένα.
class Ref:
    def __init__(self, mem, tab):
        self.mem = mem
        self.tab = tab                     # [(κανάλι, προτ/τα, addr βημάτων)]
        self.ptr = [0, 0, 0]
        self.wait = [0, 0, 0]
        self.pri = [0, 0, 0]
        self.reg = [0] * 16
        self.reg[7] = 0x3F

    def play(self, fx):
        ch, pri, addr = self.tab[fx]
        if pri < self.pri[ch]:
            return
        self.ptr[ch], self.wait[ch], self.pri[ch] = addr, 0, pri

    def tick(self):
        for c in range(3):
            if self.ptr[c] == 0:
                continue
            if self.wait[c]:
                self.wait[c] -= 1
                continue
            p = self.ptr[c]
            frames = self.mem[p]
            tbit, nbit = 1 << c, 8 << c
            if frames == 0:
                self.ptr[c] = self.pri[c] = 0
                self.reg[8 + c] = 0
                self.reg[7] |= tbit | nbit
                continue
            vol, lo, hi = self.mem[p + 1], self.mem[p + 2], self.mem[p + 3]
            self.ptr[c] = p + 4
            self.wait[c] = frames - 1
            self.reg[8 + c] = vol & 15
            self.reg[7] |= tbit | nbit
            if vol & 0x80:
                self.reg[6] = lo & 31
                self.reg[7] &= ~nbit & 0xFF
            else:
                self.reg[2 * c] = lo
                self.reg[2 * c + 1] = hi
                self.reg[7] &= ~tbit & 0xFF


def read_table(m, sym):
    """Ο πίνακας εφέ, από τη μνήμη: (κανάλι, προτεραιότητα, διεύθυνση βημάτων)."""
    base = sym["SN_TAB"]
    out = []
    for i in range(len(FX)):
        a = m.peek(base + i * 2) | (m.peek(base + i * 2 + 1) << 8)
        out.append((m.peek(a), m.peek(a + 1), a + 2))
    return out


def main():
    sym = build()
    from cpc import CPC                                              # noqa: F401
    fails_before = len(FAIL)

    # --- 1. το πρωτόκολλο ---------------------------------------------
    m = boot(sym)
    regs0 = m.psg_regs()
    check(regs0[7] == 0x3F and regs0[8:11] == [0, 0, 0],
          f"το snd_init σώπασε τον AY: R7=#{regs0[7]:02X}, εντάσεις "
          f"{regs0[8:11]}")

    play(m, sym, 0)                                  # SFX_MOVE
    tick(m, sym)
    r = m.psg_regs()
    ok = (r[4] == 120 and r[5] == 0 and r[10] == 6
          and not r[7] & 0x04 and r[7] & 0x20)
    check(ok, f"το πρώτο βήμα έφτασε στον AY: περίοδος C={r[4]}/{r[5]}, "
              f"ένταση C={r[10]}, μίκτης #{r[7]:02X}")

    # --- 2. κάθε εφέ, tick προς tick ----------------------------------
    mem = m.read_ram(0x0000, 0x4000)
    table = read_table(m, sym)
    bad = []
    for fx in range(len(FX)):
        m = boot(sym)
        ref = Ref(mem, table)
        play(m, sym, fx)
        ref.play(fx)
        for t in range(48):
            tick(m, sym)
            ref.tick()
            got = m.psg_regs()
            # Ο R14 είναι η θύρα Α — το πληκτρολόγιο, όχι ο ήχος.
            if got[:14] != ref.reg[:14]:
                bad.append((FX[fx], t, got[:14], ref.reg[:14]))
                break
    if bad:
        for name, t, got, want in bad[:3]:
            print(f"ΛΑΘΟΣ {name} στο tick {t}:")
            print(f"   AY       {got}")
            print(f"   αναφορά  {want}")
        FAIL.append("εφέ")
    else:
        print(f"OK και τα {len(FX)} εφέ: 48 tick το καθένα, ταυτόσημα με την "
              f"αναφορά")

    # --- 3. προτεραιότητα και σιωπή -----------------------------------
    m = boot(sym)
    play(m, sym, 6)                                  # ALERT, κανάλι 0, προτ. 8
    tick(m, sym)
    before = m.psg_regs()[0:2]
    play(m, sym, 5)                                  # SHIP, ίδιο κανάλι, προτ. 6
    tick(m, sym)
    check(m.psg_regs()[0:2] == before,
          f"ο συναγερμός δεν κόβεται από το πλοίο (περίοδος {before})")

    m = boot(sym)
    play(m, sym, 5)                                  # SHIP πρώτα
    tick(m, sym)
    play(m, sym, 6)                                  # ALERT από πάνω
    tick(m, sym)
    r = m.psg_regs()
    check(r[0] == 28 and r[1] == 1,
          f"ο συναγερμός κόβει το πλοίο: περίοδος A={r[0]}/{r[1]}")

    # το ίδιο κανάλι ξαναδέχεται μικρό εφέ ΜΟΛΙΣ τελειώσει το μεγάλο
    tick(m, sym, 40)
    r = m.psg_regs()
    check(r[8] == 0 and r[7] & 0x09 == 0x09,
          f"στο τέλος το κανάλι σιωπά: ένταση A={r[8]}, μίκτης #{r[7]:02X}")
    play(m, sym, 5)
    tick(m, sym)
    check(m.psg_regs()[8] != 0, "και ελευθερώνεται για το επόμενο εφέ")

    # --- 4. το πληκτρολόγιο επιζεί ------------------------------------
    from cpc import KEY_SPACE
    m = boot(sym)
    play(m, sym, 4)                                  # DONE: μακρύ, με τόνο
    m.key_down(KEY_SPACE)
    m.poke(sym["REQ"], 8)
    entry(m, sym, "DO_KEYS")
    keys = [m.peek(sym["KEY_NOW"] + i) for i in range(10)]
    sound = m.psg_regs()[9]
    m.key_up(KEY_SPACE)
    check(keys[5] & 0x80 and sound != 0,
          f"ήχος και πλήκτρα μαζί: γραμμή 5 = #{keys[5]:02X} (SPACE), "
          f"ένταση B = {sound}")
    others = sum(1 for i, v in enumerate(keys) if i != 5 and v)
    check(others == 0,
          f"και καμία άλλη γραμμή δεν «πατήθηκε» από τις εγγραφές του ήχου "
          f"({others})")

    # --- 5. το κόστος --------------------------------------------------
    # Ενα εφέ είναι 24 tick και ένα frame 20 ms: χωρίς επανάληψη δεν μετριέται
    # τίποτα. Το do_busy παίζει το ίδιο εφέ 64 φορές από 32 tick.
    REPS, PER = 64, 32
    m = boot(sym)
    m.poke(sym["REQ2"], 6)                           # ALERT
    m.poke(sym["REQ"], REPS)
    busy = entry(m, sym, "DO_BUSY", limit=900) * FRAME_US / (REPS * PER)
    idle = boot(sym)
    idle.poke(sym["REQ2"], 16)
    quiet = entry(idle, sym, "DO_BULK", limit=900) * FRAME_US / (16 * 250)
    print(f"\nκόστος ανά frame: {quiet:.0f} us στη σιωπή, {busy:.0f} us όσο "
          f"παίζει ένα εφέ ({busy * 100 / FRAME_US:.1f}% του frame)")
    check(quiet < 200 and busy < 600,
          f"ο ήχος μένει κάτω από το 3% του frame")

    # --- 5β. ΚΑΙ ΝΑ ΑΚΟΥΓΕΤΑΙ -----------------------------------------
    # Ο ήχος δεν κοιτιέται. Το αντίστοιχο του «κοίταξέ το» είναι ένα αρχείο που
    # μπορεί να παίξει ο άνθρωπος — φτιαγμένο από τους καταχωρητές που ΠΗΡΕ ο
    # AY, όχι από τον πίνακα εφέ.
    import ayrender                                                 # noqa: E402
    ticks = []
    for fx in range(len(FX)):
        m = boot(sym)
        play(m, sym, fx)
        for _ in range(40):
            tick(m, sym)
            ticks.append(m.psg_regs())
        ticks += [[0] * 7 + [0x3F] + [0] * 8] * 10        # ανάσα ανάμεσα
    wav = os.path.join(ROOT, "build", "sounds.wav")
    secs = ayrender.write_wav(wav, ayrender.render_ticks(ticks))
    print(f"\nbuild/sounds.wav: {secs:.1f} s — τα οκτώ εφέ με τη σειρά "
          f"({', '.join(FX)})")

    # --- 6. ΜΕΣΑ ΣΤΟ ΠΑΙΧΝΙΔΙ ------------------------------------------
    # Ως εδώ δοκιμάστηκε ο παίκτης. Εδώ δοκιμάζεται ότι κάποιος τον καλεί:
    # πλήκτρο -> ήχος, μέσα στον κανονικό βρόχο του src/main.asm.
    sys.path.insert(0, HERE)
    import test_game                                                # noqa: E402
    gsym, _ = test_game.build()
    from cpc import CPC, KEY_SPACE, KEY_RIGHT
    g = CPC()
    g.run_frames(60)
    assert g.quickload(test_game.SNA), "quickload του παιχνιδιού απέτυχε"
    g.run_frames(200)
    quiet = g.psg_regs()
    check(quiet[8:11] == [0, 0, 0],
          f"το παιχνίδι ξεκινά σιωπηλό: εντάσεις {quiet[8:11]}")

    def tap_game(key, frames=3):
        g.key_down(key)
        g.run_frames(frames)
        g.key_up(key)

    # Ο κέρσορας: το εφέ είναι ΕΝΑ frame, οπότε το πιάνουμε frame προς frame.
    seen = 0
    tap_game(KEY_RIGHT)
    for _ in range(12):
        g.run_frames(1)
        if g.psg_regs()[10]:
            seen += 1
    check(seen > 0, f"το βήμα κέρσορα ακούγεται ({seen} frames με ένταση στο C)")

    tap_game(KEY_SPACE)
    seen = 0
    for _ in range(12):
        g.run_frames(1)
        r = g.psg_regs()
        if r[10] and r[4] in (95, 60):
            seen += 1
    check(seen > 0, f"το μενού ακούγεται ({seen} frames)")

    # Η ΑΡΝΗΣΗ: FIRE πάνω στην αποικία. Ο κέρσορας ξεκινά ακριβώς εκεί, οπότε
    # το ui_validate λέει όχι — και αυτό πρέπει να ΑΚΟΥΓΕΤΑΙ, αλλιώς ο παίκτης
    # πατά και δεν γίνεται τίποτα χωρίς εξήγηση.
    g.poke(gsym["CUR_HX"], 0)            # πάνω στην αποικία: εκεί ΔΕΝ χτίζεται
    g.poke(gsym["CUR_HY"], 0)
    g.set_joystick_type(1)               # κλέβει τα βελάκια όσο είναι αναμμένο
    g.run_frames(2)
    g.joystick(0x10)                     # το πρώτο FIRE μπαίνει στο PLACE
    g.run_frames(4)
    g.joystick(0)
    g.run_frames(14)                     # και το μπιπ του καταλόγου τελειώνει
    g.joystick(0x10)                     # το δεύτερο ΠΡΟΣΠΑΘΕΙ να χτίσει
    g.run_frames(4)
    g.joystick(0)
    noise = 0
    for _ in range(12):                  # η άρνηση είναι 7 frames: δειγματίζεται
        g.run_frames(1)                  # ΟΣΟ παίζει, όχι αφού τελειώσει
        r = g.psg_regs()
        if r[10] and not r[7] & 0x20:    # ένταση στο C, θόρυβος ανοιχτός
            noise += 1
    g.set_joystick_type(0)
    check(noise > 0,
          f"η άκυρη θέση ακούγεται ως άρνηση ({noise} frames θορύβου)")

    # Ο συναγερμός: το ml_alert καλείται από το ρολόι του HUD, αλλά εδώ το
    # καλούμε κατευθείαν ώστε η δοκιμή να μην περιμένει τον τροχό.
    def call(name, sym=None):
        sym = sym or gsym
        return [0xCD, sym[name] & 0xFF, sym[name] >> 8]
    ec = gsym["G_ECON_STATE"] if "G_ECON_STATE" in gsym else None
    if ec is None:
        for line in open(os.path.join(ROOT, "build", "layout.asm"),
                         encoding="utf-8"):
            if line.startswith("G_econ_state"):
                ec = int(line.split("#")[1].strip(), 16)
    g.poke(ec + 46, 1)                              # POK
    g.poke(ec + 47, 1)                              # O2OK
    g.run_code(0x3F00, bytes(call("ML_ALERT") + [0x18, 0xFE]))
    g.run_frames(2)
    before = g.psg_regs()[8]
    g.poke(ec + 46, 0)                              # έπεσε το ρεύμα
    g.run_code(0x3F00, bytes(call("ML_ALERT") + call("SND_TICK") + [0x18, 0xFE]))
    g.run_frames(2)
    r = g.psg_regs()
    check(before == 0 and r[8] == 11 and r[0] == 28 and r[1] == 1,
          f"ο συναγερμός χτυπά ΜΟΝΟ στην ακμή: πριν ένταση {before}, "
          f"μετά {r[8]} με περίοδο {r[0]}/{r[1]}")

    return 1 if len(FAIL) > fails_before else 0


if __name__ == "__main__":
    sys.exit(main())
