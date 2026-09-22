#!/usr/bin/env python3
"""Δρομολόγηση: ταυτότητα με την αναφορά, ισοδυναμία φετών, και το κόστος.

Τέσσερα πράγματα, και χρειάζονται και τα τέσσερα:

  ΤΑΥΤΟΤΗΤΑ    ο Z80 βγάζει τους ΔΥΟ πίνακες byte-προς-byte όπως η αναφορά,
               σε γράφους που έχουν επιλεγεί για να σπάνε διαφορετικά πράγματα.
  ΣΥΝΕΠΕΙΑ     κάθε διαδρομή που δίνει το NEXTHOP έχει μήκος ακριβώς όσο λέει
               το DIST. Αυτό πιάνει δύο σωστά-φαινόμενους πίνακες που δεν
               ταιριάζουν μεταξύ τους.
  ΦΕΤΕΣ        η διακοπτόμενη μορφή δίνει ΤΟ ΙΔΙΟ αποτέλεσμα με την αδιάκοπη.
               Αυτή θα τρέξει στο παιχνίδι· η άλλη υπάρχει για μέτρηση.
  ΚΟΣΤΟΣ       πόσο κάνει στ' αλήθεια, στη χειρότερη περίπτωση. Το §6.4
               υπολόγιζε 30 us ανά χαλάρωση.
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")

import graph as G                                                # noqa: E402

RASM = os.path.expanduser("~/rasm/rasm.exe")
SNA = os.path.join(ROOT, "build", "graphtest.sna")
FRAME_US = 19968


def build():
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "pack.py")],
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit("pack.py απέτυχε:\n" + r.stdout + r.stderr)
    r = subprocess.run([RASM, "graphtest.asm", "-oi", SNA, "-v2", "-s", "-eo"],
                       cwd=HERE, capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(SNA):
        sys.exit("rasm απέτυχε:\n" + r.stdout + r.stderr)
    sym = {}
    for line in open(os.path.join(HERE, "rasmoutput.sym"), encoding="utf-8",
                     errors="replace"):
        p = line.split()
        if len(p) >= 2 and p[1].startswith("#"):
            sym[p[0].upper()] = int(p[1][1:], 16)
    # Οι σταθερές `equ` του layout.asm δεν μπαίνουν στο .sym του rasm — τις
    # διαβάζουμε από την πηγή τους, που είναι έτσι κι αλλιώς η pack.py.
    for line in open(os.path.join(ROOT, "build", "layout.asm"), encoding="utf-8"):
        p = line.split()
        if len(p) == 3 and p[1] == "equ" and p[2].startswith("#"):
            sym[p[0].upper()] = int(p[2][1:], 16)
    return sym


def run_z80(sym, g, entry="START", slice_b=None):
    """Γράφει τον γράφο, τρέχει, και γυρίζει (DIST, NEXTHOP, frames, φέτες)."""
    from cpc import CPC
    m = CPC()
    m.run_frames(60)
    assert m.quickload(SNA, start=False), "quickload απέτυχε"

    m.write_ram(sym["G_NODE_ADJ"], bytes(g.adj))
    m.write_ram(sym["G_RT_NODES"], bytes(g.deg))          # deg στο κάτω μισό
    m.poke(sym["RT_N"], g.hw)                              # ανώτατο id + 1
    if slice_b is not None:
        m.poke(sym["SLICE_B"], slice_b)

    m.poke(sym["DONE_FLAG"], 0)
    m.set_pc(sym[entry])
    n = 0
    while m.peek(sym["DONE_FLAG"]) != 0x5A and n < 1200:
        m.run_frames(1)
        n += 1
    assert m.peek(sym["DONE_FLAG"]) == 0x5A, \
        f"δεν τερμάτισε σε {n} frames, PC=#{m.pc:04X}"

    dist = m.read_ram(0x4000, G.MAT_SIZE)                 # τράπεζα 1 = βασική

    m.poke(sym["DUMP_FLAG"], 0)
    m.set_pc(sym["DUMP_NEXT"])
    k = 0
    while m.peek(sym["DUMP_FLAG"]) != 0xA5 and k < 60:
        m.run_frames(1)
        k += 1
    assert m.peek(sym["DUMP_FLAG"]) == 0xA5, "η μεταφορά της τράπεζας 5 κόλλησε"
    nxt = m.read_ram(0xC000, G.MAT_SIZE)

    slices = m.peek(sym["SLICE_COUNT"]) | (m.peek(sym["SLICE_COUNT"] + 1) << 8)
    return dist, nxt, n, slices


def diff(got, want, label, g):
    bad = [i for i in range(len(want)) if got[i] != want[i]]
    print(f"  ΑΠΟΤΥΧΙΑ {label}: {len(bad)} από {len(want)} bytes διαφέρουν")
    for i in bad[:6]:
        a, b = i >> 7, i & 127
        print(f"    [{a:3d}][{b:3d}]  Z80 {got[i]:3d} != αναφορά {want[i]:3d}"
              f"   (γείτονες του {a}: {g.neighbours(a)})")
    return len(bad)


def consistent(dist, nxt, g):
    """Κάθε διαδρομή του NEXTHOP πρέπει να έχει μήκος ακριβώς DIST."""
    for a in range(g.n):
        for b in range(g.n):
            d = dist[a * 128 + b]
            p = G.walk(nxt, a, b)
            if d == G.UNREACH:
                if p is not None:
                    return f"[{a}][{b}] DIST λέει απρόσιτος, το NEXTHOP βγάζει {p}"
            elif p is None:
                return f"[{a}][{b}] DIST λέει {d}, το NEXTHOP δεν φτάνει"
            elif len(p) - 1 != d:
                return f"[{a}][{b}] DIST λέει {d}, η διαδρομή έχει {len(p)-1}: {p}"
    return None


def main():
    sym = build()
    fails = 0
    worst_frames = None

    cost = {}
    for name in ("single", "isolated", "split", "line", "star", "ring",
                 "tree", "colony", "bounded", "worst"):
        g = G.GRAPHS[name]()
        wd, wn = G.all_pairs(g)
        dist, nxt, frames, _ = run_z80(sym, g)
        cost[name] = (g, frames)

        # Η σύγκριση σταματά στο hw: πάνω από εκεί ο Z80 δεν γράφει καθόλου,
        # και καμία ερώτηση δεν διαβάζει εκείνες τις σειρές (βλ. rt_begin).
        lim = g.hw * 128
        dist, nxt = dist[:lim], nxt[:lim]
        wd, wn = wd[:lim], wn[:lim]

        bad = 0
        if dist != wd:
            bad += diff(dist, wd, f"{name} DIST", g)
        if nxt != wn:
            bad += diff(nxt, wn, f"{name} NEXTHOP", g)
        if bad:
            fails += 1
            continue

        why = consistent(dist, nxt, g)
        if why:
            print(f"  ΑΠΟΤΥΧΙΑ {name}: οι δύο πίνακες δεν συμφωνούν — {why}")
            fails += 1
            continue

        print(f"OK {name:9s} n={g.n:3d} ακμές={len(g.edges()):4d}  "
              f"{2*lim} bytes ταυτόσημα, οι διαδρομές συμφωνούν με τις αποστάσεις")
        if name == "worst":
            worst_frames = frames

    if fails:
        return 1

    # --- η διακοπτόμενη μορφή: ίδιο αποτέλεσμα ΚΑΙ πραγματικά κομμένη ---
    #
    # Το δεύτερο μισό δεν είναι διακοσμητικό. Η πρώτη γραφή αυτού του κώδικα
    # έχανε το B μέσα στο ldir του rt_open, οπότε κάθε φέτα γινόταν ολόκληρη:
    # το αποτέλεσμα έβγαινε σωστό και η δοκιμή περνούσε χωρίς να δοκιμάζει
    # τίποτα. Ο μετρητής κλήσεων είναι αυτό που το έπιασε.
    g = G.GRAPHS["worst"]()
    a_d, a_n, _, _ = run_z80(sym, g)
    counts = {}
    for bsz in (3, 12):
        b_d, b_n, _, counts[bsz] = run_z80(sym, g, entry="SLICED", slice_b=bsz)
        if (a_d, a_n) != (b_d, b_n):
            print(f"ΑΠΟΤΥΧΙΑ: με B={bsz} η κομμένη ανοικοδόμηση δίνει άλλο αποτέλεσμα")
            return 1

    # 128 πηγές x (1 άνοιγμα + 128 κόμβοι + 1 κλείσιμο) = 16.640 μονάδες
    units = 128 * 130
    for bsz, got in counts.items():
        want = units // bsz
        if not 0.7 * want <= got <= 1.4 * want:
            print(f"ΑΠΟΤΥΧΙΑ: με B={bsz} περίμενα ~{want} κλήσεις, έγιναν {got}."
                  f"\n  Ο προϋπολογισμός της φέτας ΔΕΝ τηρείται — η δουλειά δεν κόβεται.")
            return 1
    if counts[3] <= counts[12]:
        print("ΑΠΟΤΥΧΙΑ: μικρότερο B δεν έδωσε περισσότερες κλήσεις")
        return 1
    print(f"OK φέτες    B=3 -> {counts[3]} κλήσεις, B=12 -> {counts[12]}, "
          f"ταυτόσημο αποτέλεσμα και με τα δύο")

    # --- κόστος: η χειρότερη περίπτωση ΚΑΙ η πραγματική ---
    print("\nκόστος πλήρους ανοικοδόμησης (CPU, όχι απλωμένο σε frames):")
    for name in ("colony", "tree", "bounded", "worst"):
        g, fr = cost[name]
        us = fr * FRAME_US
        rel = sum(g.deg[:g.hw]) * g.hw          # χαλαρώσεις συνολικά
        print(f"  {name:7s} n={g.hw:3d} μέσος βαθμός {sum(g.deg[:g.hw])/g.hw:4.1f}  "
              f"{fr:4d} frames = {us/1e6:5.2f} s   ανά πηγή {us/g.hw/1000:5.1f} ms"
              f"   ανά χαλάρωση {us/max(rel,1):4.1f} us")
    gb, fb = cost["bounded"]
    unit = fb * FRAME_US / (gb.hw * (gb.hw + 2))
    print(f"\n  Ο 'worst' ΔΕΝ μπορεί να συμβεί: 96 θέσεις διαδρόμων στον §6.1, όχι 512.")
    print(f"  Το πραγματικό ταβάνι είναι ο 'bounded': "
          f"{fb*FRAME_US/1e6:.2f} s καθαρής CPU.")
    print(f"  Το κόστος είναι O(n^2) σε ΚΟΜΒΟΥΣ, όχι O(ακμές): "
          f"{unit:.0f} us ανά επέκταση κόμβου.")
    for n in (16, 32, 64, 128):
        print(f"    n={n:3d}  ~{n*n*unit/1e6:5.2f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
