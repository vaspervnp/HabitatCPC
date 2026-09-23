#!/usr/bin/env python3
"""Η γεννήτρια κόσμου: ταυτότητα με την αναφορά, ντετερμινισμός, παιξιμότητα.

Τρία διαφορετικά πράγματα, και χρειάζονται και τα τρία:

  ΤΑΥΤΟΤΗΤΑ    ο Z80 βγάζει ό,τι και το tools/worldgen_ref.py, byte-προς-byte.
               Αυτό πιάνει λάθος αλγόριθμο.
  ΝΤΕΤΕΡΜΙΝΙΣΜΟΣ  δύο ΨΥΧΡΕΣ εκκινήσεις με το ίδιο seed δίνουν το ίδιο επίπεδο.
               Αυτό πιάνει εξάρτηση από αδιευκρίνιστη μνήμη ή από χρονισμό —
               που η ταυτότητα μπορεί να μην την πιάσει, αν τύχει.
  ΠΑΙΞΙΜΟΤΗΤΑ  κάθε seed έχει νερό ΚΑΙ φλέβα μέσα σε 30 tiles.
"""
import collections, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")

import world                                                    # noqa: E402
import worldgen_ref as G                                        # noqa: E402

RASM = os.path.expanduser("~/rasm/rasm.exe")
SNA = os.path.join(ROOT, "build", "gentest.sna")
SEEDS = [0x1234, 0xACE1, 0x0001, 0xFFFF]
SWEEP = 64        # πλήρης σάρωση χιλιάδων seeds: χωριστά, πριν από έκδοση


def build():
    for tool in ("mkoffsets.py", "pack.py", "mkgentables.py"):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", tool)],
                           capture_output=True, text=True)
        if r.returncode:
            sys.exit(f"{tool} απέτυχε:\n{r.stdout}{r.stderr}")
    r = subprocess.run([RASM, "gentest.asm", "-oi", SNA, "-v2", "-s", "-eo"],
                       cwd=HERE, capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(SNA):
        sys.exit("rasm απέτυχε:\n" + r.stdout + r.stderr)
    sym = {}
    for line in open(os.path.join(HERE, "rasmoutput.sym"), encoding="utf-8",
                     errors="replace"):
        p = line.split()
        if len(p) >= 2 and p[1].startswith("#"):
            sym[p[0].upper()] = int(p[1][1:], 16)
    return sym


def run_z80(sym, seed, planet=0):
    """Ψυχρή εκκίνηση, γέννηση, και το επίπεδο πίσω από τη βασική τράπεζα 1."""
    from cpc import CPC
    m = CPC()
    m.run_frames(60)
    assert m.quickload(SNA, start=False), "quickload απέτυχε"
    m.poke(sym["GEN_SEED"], seed & 0xFF)
    m.poke(sym["GEN_SEED"] + 1, (seed >> 8) & 0xFF)
    m.poke(sym["GEN_PLANET"], planet)
    m.set_pc(sym["START"])
    n = 0
    while m.peek(sym["DONE_FLAG"]) != 0x5A and n < 900:
        m.run_frames(1)
        n += 1
    assert m.peek(sym["DONE_FLAG"]) == 0x5A, \
        f"δεν τερμάτισε σε {n} frames, PC=#{m.pc:04X}"
    return m.read_ram(0x4000, 0x4000), n


def diff_report(got, want, seed):
    bad = [i for i in range(world.SIZE) if got[i] != want[i]]
    print(f"ΑΠΟΤΥΧΙΑ seed {seed:04X}: {len(bad)} από {world.SIZE} bytes διαφέρουν")
    for i in bad[:6]:
        u, v = i & 127, i >> 7
        g, w = got[i], want[i]
        print(f"    tile ({u-64:>4},{v-64:>4})  Z80 #{g:02X} "
              f"({world.CLASS_NAMES[g & 7]},decor {g >> 6}) "
              f"!= αναφορά #{w:02X} ({world.CLASS_NAMES[w & 7]},decor {w >> 6})")
    return len(bad)


COL = {0: (196, 128, 64), 1: (230, 180, 96), 2: (150, 120, 100),
       3: (110, 100, 95), 4: (60, 130, 220), 5: (20, 50, 150),
       6: (90, 70, 60), 7: (220, 220, 200)}


def save_png(plane, seed):
    """Ένας ντετερμινιστικός χάρτης μπορεί να είναι και κακός χάρτης."""
    from PIL import Image
    img = Image.new("RGB", (world.W, world.W))
    px = img.load()
    for i, b in enumerate(plane):
        c = b & 7
        px[i & 127, i >> 7] = (230, 60, 60) if (c == 3 and (b >> 3) & 1) else COL[c]
    img.resize((world.W * 3, world.W * 3), Image.NEAREST).save(
        os.path.join(HERE, "golden", f"world_{seed:04X}.png"))


def main():
    sym = build()
    fails = 0
    frames = None

    # --- ταυτότητα με την αναφορά ---
    for seed in SEEDS:
        got, n = run_z80(sym, seed)
        frames = frames or n
        want = bytes(G.generate(seed).buf)
        if got != want:
            diff_report(got, want, seed)
            fails += 1
        else:
            print(f"OK seed {seed:04X}: 16384 bytes ταυτόσημα με την αναφορά")
            save_png(got, seed)

    # --- και οι τέσσερις πλανήτες (§5.7) ---
    # Ο πλανήτης είναι επτά κατώφλια, τίποτε άλλο· ο Z80 τα αντιγράφει από τον
    # gen_planets και η αναφορά από το PLANETS. Ως το βήμα 17 δοκιμαζόταν μόνο
    # ο 0, και η γεννήτρια δεν είχε κληθεί ποτέ με άλλον — ούτε από το παιχνίδι,
    # που έγραφε πάντα μηδέν.
    for planet in (1, 2, 3):
        got, _ = run_z80(sym, 0xACE1, planet)
        want = bytes(G.generate(0xACE1, planet).buf)
        if got != want:
            diff_report(got, want, 0xACE1)
            fails += 1
        else:
            cls = collections.Counter(b & 7 for b in got)
            print(f"OK πλανήτης {planet}: 16384 bytes ταυτόσημα, "
                  f"νερό {cls[4] + cls[5]:>5}  βουνό {cls[3]:>5}  "
                  f"γόνιμο {sum(1 for b in got if b & 7 == 0 and b & 8):>5}")

    if fails:
        return 1

    # --- ντετερμινισμός από ψυχρή εκκίνηση ---
    a, _ = run_z80(sym, 0x1234)
    b, _ = run_z80(sym, 0x1234)
    if a != b:
        print("ΑΠΟΤΥΧΙΑ: δύο ψυχρές εκκινήσεις με το ίδιο seed διαφέρουν")
        return 1
    print("OK ντετερμινισμός: δύο ψυχρές εκκινήσεις, ταυτόσημα")

    # --- παιξιμότητα, στην αναφορά (ίδια με τον Z80, μόλις το αποδείξαμε) ---
    N = SWEEP
    for planet in range(4):
        bad = [s for s in range(0x4000, 0x4000 + N)
               if not all(G.playable(G.generate(s, planet)))]
        print(f"OK παιξιμότητα πλανήτη {planet}: {N - len(bad)}/{N} seeds με νερό "
              f"και φλέβα σε 30 tiles")
        if bad:
            print(f"   απέτυχαν: {[f'{s:04X}' for s in bad[:5]]}")
            return 1

    sec = frames * 19968 / 1e6
    print(f"\nκόστος: {frames} frames = {sec:.2f} s για έναν κόσμο")
    # Το §5.9 καταγράφει 13,5 s μετρημένα, και το §5.10 στηρίζεται πάνω του: με
    # αυτόν τον αριθμό η αναγέννηση στη φόρτωση δεν στέκει. Αν πέσει, το §5.10
    # ξανασυζητιέται· αν ανέβει, χειροτερεύει. Και στις δύο περιπτώσεις, όχι σιωπή.
    if not 12.5 <= sec <= 14.5:
        print(f"  ΑΠΟΤΥΧΙΑ: το DESIGN §5.9 λέει 13,5 s, μετρήθηκαν {sec:.2f}."
              f"\n  Ενημέρωσε το §5.9, ξανακοίτα το §5.10, και διόρθωσε αυτό το όριο.")
        return 1
    print("  (το DESIGN §5.9 καταγράφει 13,5 s — συμφωνεί)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
