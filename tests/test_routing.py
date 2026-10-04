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

Και από το βήμα 62 δύο ακόμη, γιατί τα λάθη τους περνούσαν όλα τα παραπάνω:

  ΛΟΓΑΡΙΑΣΜΟΣ κάθε φέτα κάνει ΑΚΡΙΒΩΣ B μονάδες: οι κλήσεις είναι
               ⌈Σ (R(s) + 2) / B⌉, με R(s) όσους κόμβους φτάνει η πηγή s. Ενα
               άνοιγμα ή κλείσιμο που δεν μετράει χωρούσε στο ±30 % που
               δεχόταν ως τότε η δοκιμή — και το frame ξεπερνούσε το ταβάνι του.
  ΞΑΝΑ ΑΠΟ ΤΗΝ ΑΡΧΗ  rt_mark στη μέση μιας ανοικοδόμησης, πάνω σε άλλον
               γράφο: ό,τι βγαίνει πρέπει να είναι ο νέος γράφος ολόκληρος. Ετσι
               δουλεύει το παιχνίδι — κάθε διάδρομος που χτίζεται ενώ ο τροχός
               δρομολογεί — και κανείς δεν το δοκίμαζε.
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


def run_z80(sym, g, entry="START", slice_b=None, patch=()):
    """Γράφει τον γράφο, τρέχει, και γυρίζει (DIST, NEXTHOP, frames, φέτες)."""
    from cpc import CPC
    m = CPC()
    m.run_frames(60)
    assert m.quickload(SNA, start=False), "quickload απέτυχε"
    for at, v in patch:
        m.poke(at, v)

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


PROBE = 0x3F00


def probe(m, code):
    """di · ld sp · τράπεζα 1 · code · push af · pop hl · ld (#3FF0),hl · jr $.
    Γυρίζει το F."""
    code = ([0xF3, 0x31, 0x00, 0x01, 0x01, 0xC0, 0x7F, 0xED, 0x49] + code +
            [0xF5, 0xE1, 0x22, 0xF0, 0x3F, 0x18, 0xFE])
    m.write_ram(PROBE, bytes(code))
    m.set_pc(PROBE)
    end, t = PROBE + len(code) - 2, 0
    while not (end <= m.pc <= end + 2):
        m.run_us(200)
        t += 200
        assert t < 10_000_000, f"δεν γύρισε: #{m.pc:04X}"
    return m.peek(0x3FF0)


def units(g):
    """Οι μονάδες μιας ανοικοδόμησης: ανά πηγή ένα άνοιγμα, μία αφαίρεση ανά
    κόμβο που φτάνει, και η τελευταία, άδεια, μαζί με το κλείσιμο."""
    return sum(2 + sum(1 for d in G.bfs_row(g, s)[0] if d != G.UNREACH)
               for s in range(g.hw))


def slices_check(sym, patch=()):
    """Ακριβές πλήθος κλήσεων σε πέντε γράφους και τρία B. Η πρώτη διαφορά ή None."""
    for name in ("worst", "colony", "split", "isolated", "star"):
        g = G.GRAPHS[name]()
        u = units(g)
        for bsz in (1, 3, 12):
            _, _, _, got = run_z80(sym, g, entry="SLICED", slice_b=bsz, patch=patch)
            if got != -(-u // bsz):
                return f"{name}, B={bsz}: {got} κλήσεις, {u} μονάδες θέλουν {-(-u // bsz)}"
    return None


def restart(sym, ga, gb, bsz, k, patch=()):
    """Ο ga κομμένος σε φέτες των bsz· μετά από k φέτες ο γράφος γίνεται gb και
    έρχεται rt_mark, και οι φέτες συνεχίζουν ως το τέλος. Γυρίζει (DIST, NEXTHOP
    ως το hw του gb, rt_dirty, (rt_src, rt_phase) τη στιγμή του rt_mark).

    Πριν από το rt_mark η σειρά και η ουρά γεμίζουν σκουπίδια, όπως τις αφήνει
    ένα φόρτωμα: το μπλοκ της αποθήκευσης τις καλύπτει, το rt_tail όχι (βήμα 63)."""
    import ctypes, random
    import cpc
    m = cpc.CPC()
    m.run_frames(60)
    assert m.quickload(SNA, start=False), "quickload απέτυχε"
    for at, v in patch:
        m.poke(at, v)
    fn = lambda nm: [0xCD, sym[nm] & 255, sym[nm] >> 8]
    for g in (ga, gb):
        m.write_ram(sym["G_NODE_ADJ"], bytes(g.adj))
        m.write_ram(sym["G_RT_NODES"], bytes(g.deg))
        m.poke(sym["RT_N"], g.hw)
        if g is ga:
            m.poke(sym["RT_DIRTY"], 0)
            probe(m, fn("RT_BEGIN"))
            for _ in range(k):
                assert not probe(m, [0x06, bsz] + fn("RT_SLICE")) & 1, "τελείωσε νωρίς"
            at = (m.peek(sym["RT_SRC"]), m.peek(sym["RT_PHASE"]))
            rnd = random.Random(k)
            m.write_ram(sym["G_RT_ROW"], bytes(rnd.randrange(256) for _ in range(256)))
            m.write_ram(sym["G_RT_NODES"] + 128, bytes(rnd.randrange(128) for _ in range(128)))
            probe(m, fn("RT_MARK"))
            dirty = m.peek(sym["RT_DIRTY"])
    n = 0
    while not probe(m, [0x06, bsz] + fn("RT_SLICE")) & 1:
        n += 1
        assert n < 20000, "δεν τελειώνει"
    lim = gb.hw * 128
    row = lambda bank: ctypes.string_at(cpc._lib.cpcemu_ram_ptr(m._h, bank), lim)
    return row(1), row(5), dirty, at


def restart_check(sym, patch=()):
    """rt_mark σε τρία σημεία: στη μέση μιας πηγής, αμέσως μετά από κλείσιμο,
    αμέσως μετά από άνοιγμα. Η πρώτη διαφορά ή None."""
    ga, gb = G.GRAPHS["worst"](), G.GRAPHS["colony"]()
    wd, wn = G.all_pairs(gb)
    lim = gb.hw * 128
    # worst: 130 μονάδες ανά πηγή — 50 x 12 = 600 είναι η πηγή 4 στη μέση,
    # 130 x 1 μόλις έκλεισε την πηγή 0, 131 x 1 μόλις άνοιξε την 1
    for bsz, k, phase in ((12, 50, True), (1, 130, False), (1, 131, True)):
        dist, nxt, dirty, (src, ph) = restart(sym, ga, gb, bsz, k, patch)
        assert src > 0 and bool(ph) == phase, \
            f"το rt_mark δεν ήρθε εκεί που έπρεπε: rt_src {src}, φάση {ph}"
        if dirty != 1:
            return f"B={bsz}, μετά από {k} φέτες: το rt_mark άφησε rt_dirty = {dirty}"
        if (dist, nxt) != (bytes(wd[:lim]), bytes(wn[:lim])):
            bad = sum(1 for i in range(lim) if dist[i] != wd[i] or nxt[i] != wn[i])
            first = next(i for i in range(lim) if dist[i] != wd[i] or nxt[i] != wn[i])
            return (f"B={bsz}, rt_mark μετά από {k} φέτες (πηγή {src}): {bad} θέσεις του "
                    f"νέου γράφου λάθος, πρώτη [{first >> 7}][{first & 127}]")
    return None


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
    why = slices_check(sym)
    if why:
        print(f"ΑΠΟΤΥΧΙΑ: ο προϋπολογισμός της φέτας ΔΕΝ τηρείται ακριβώς — {why}")
        return 1
    print(f"OK φέτες    B=3 -> {counts[3]} κλήσεις, B=12 -> {counts[12]}, "
          f"ταυτόσημο αποτέλεσμα και με τα δύο")
    print("OK φέτες    ακριβώς ⌈μονάδες / B⌉ κλήσεις, σε 5 γράφους με B = 1, 3, 12")
    why = restart_check(sym)
    if why:
        print(f"ΑΠΟΤΥΧΙΑ: rt_mark στη μέση της ανοικοδόμησης — {why}")
        return 1
    print("OK rt_mark  στη μέση πηγής, μετά από κλείσιμο, μετά από άνοιγμα, με τη σειρά "
          "και την ουρά όπως τις αφήνει ένα φόρτωμα: ο νέος γράφος ολόκληρος, και το "
          "rt_dirty σηκωμένο")

    # --- αρνητικά: οι δύο έλεγχοι πιάνουν αυτό που λένε ---
    sl, op, bg = sym["RT_SLICE"], sym["RT_OPEN"], sym["RT_BEGIN"]
    from cpc import CPC
    m = CPC()
    m.run_frames(60)
    assert m.quickload(SNA, start=False)
    k = next((k for k in range(40) if list(m.read_ram(sl + k, 4)) ==
              [0xCD, op & 255, op >> 8, 0x05]), None)              # call rt_open · dec b
    if k is None or slices_check(sym, [(sl + k + 3, 0)]) is None:
        print("ΑΠΟΤΥΧΙΑ: ΑΡΝΗΤΙΚΟ — με το άνοιγμα να μη μετράει, το πλήθος των φετών "
              "δεν άλλαξε")
        return 1
    print("OK ΑΡΝΗΤΙΚΟ: με το άνοιγμα να μη μετράει, το πλήθος των φετών αλλάζει")
    if m.peek(bg) != 0xAF or m.peek(bg + 1) != 0x32 or \
            restart_check(sym, [(bg + 1, 0), (bg + 2, 0), (bg + 3, 0)]) is None:
        print("ΑΠΟΤΥΧΙΑ: ΑΡΝΗΤΙΚΟ — με το rt_begin να μη μηδενίζει το rt_src, το "
              "rt_mark στη μέση πέρασε")
        return 1
    print("OK ΑΡΝΗΤΙΚΟ: με το rt_begin να μη μηδενίζει το rt_src, οι πρώτες σειρές "
          "μένουν του παλιού γράφου")
    k = next((k for k in range(16) if list(m.read_ram(bg + k, 3)) == [0x21, 128, 0]), None)
    if k is None or restart_check(sym, [(bg + k + 1, 129)]) is None:            # ld hl,128
        print("ΑΠΟΤΥΧΙΑ: ΑΡΝΗΤΙΚΟ — με το rt_begin να μη λέει «άγνωστη σειρά», το "
              "rt_mark μετά από φόρτωμα πέρασε")
        return 1
    print("OK ΑΡΝΗΤΙΚΟ: με το rt_begin να μη λέει «άγνωστη σειρά», ό,τι άφησε το "
          "φόρτωμα στη σειρά μένει")

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
