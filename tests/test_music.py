#!/usr/bin/env python3
"""Η μουσική (βήμα 195, src/music.asm, DESIGN §9.5).

Ο χρήστης ζήτησε ατμοσφαιρική μουσική με τη διακοπή, που να ανοιγοκλείνει
από το μενού, και διάλεξε γεννητική, κουμπί στη ΔΙΑΧΕΙΡΙΣΗ με δικό του πλήκτρο,
ανοιχτή στην αρχή και σωσμένη, και το εφέ να παίρνει μόνο το κανάλι του· μετά
το δείγμα, την ένταση στο 1/4.

  ΤΟ ΜΟΝΤΕΛΟ  ο κύριος βρόχος σε halt, η μουσική ανοιχτή: σε 3.000 ticks οι
              καταχωρητές του AY ίδιοι με του tools/music.py (ένταση, και
              περίοδος όπου ακούγεται), ο μίκτης #38. Αρνητικά: μία νότα της
              κλίμακας, η φάση του σβησίματος, ένα σκαλί του βάθους.
  ΚΛΕΙΣΤΗ     το main.sna την έχει κλειστή (mu_off 1, το EC_MUS 1) και ο
              δίσκος ανοιχτή (το GAME.BIN του tools/mkdsk.py)· κλειστή, 300
              frames του παιχνιδιού χωρίς κανένα tick και χωρίς ένταση.
  ΤΑ ΕΦΕ      ο συναγερμός στο A, το «χτίστηκε» στο B, το «όχι» (θόρυβος) στο
              C: όσο παίζουν, το κανάλι τους ίδιο με ένα τρέξιμο χωρίς μουσική·
              τα άλλα με το μοντέλο· μετά και το δικό τους, μέσα σε 33 ticks
              (το βάθος γράφεται κάθε 32), με τον μίκτη ξανά #38. Αρνητικά:
              χωρίς τους ελέγχους του wait, και το τέλος του εφέ με #FF όπως ως
              το βήμα 194.
  Ο AY ΤΟΥ ΒΡΟΧΟΥ  ένας βρόχος που σαρώνει το πληκτρολόγιο και γράφει τον R6
              με το snd_reg, με τη μουσική ανοιχτή: καμία σάρωση χαλασμένη,
              ο R6 πάντα δικός του, και η μουσική προχωρά. Αρνητικό: χωρίς τον
              έλεγχο της σελίδας του PC που διακόπηκε.
  ΤΟ U        από το LOOK και από τη ΔΙΑΧΕΙΡΙΣΗ: κλείνει (σιωπή, κανένα tick,
              το EC_MUS μαζί) και ξανανοίγει, και γυρίζει στο LOOK.
  ΤΟ ΦΟΡΤΩΜΑ  το svx_swap φέρνει το EC_MUS του σωσίματος στο mu_off, και ο
              κώδικας του b6x και των ουρών γυρίζει ίδιος. Αρνητικό: χωρίς την
              εγγραφή. Και από τον δίσκο, ολόκληρο: η μουσική παίζει από την
              αρχή, U και S, U και L — κλειστή όπως σώθηκε· και ανάποδα.
  ΚΟΣΤΟΣ      το mu_tick σε 3.000 ticks: το χειρότερο, ο μέσος όρος, και ένα
              tick με όλα μαζί (καμπάνα, συγχορδία, δύο κανάλια γραμμένα).
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import cpc                                               # noqa: E402
import music as MU                                       # noqa: E402
import codeat as CA                                      # noqa: E402
import menuread as MR                                    # noqa: E402
import test_game as TG                                   # noqa: E402

SNA = os.path.join(ROOT, "build", "main.sna")
DSK = os.path.join(ROOT, "build", "habitat.dsk")
FAIL = []
# ΟΙ ΒΡΟΧΟΙ ΤΩΝ ΔΟΚΙΜΩΝ κάτω από τη στοίβα (#0100, ως το #00CE το βαθύτερο που
# μετρήθηκε): στη θέση του επιμέτρου του φορτωτή, που δεν χρειάζεται πια.
LOOP = 0x0040
FLAG = 0x0090                   # το εφέ που ζητά ο βρόχος, + 1
CNT = 0x0092                    # σαρώσεις χαλασμένες, 16 bit
VAL = 0x0094                    # ό,τι γράφει ο βρόχος στον R6
R6_VAL = 0x15
SFX_DENY, SFX_BUILD, SFX_ALERT = 2, 3, 6        # src/sound.asm
KEY_LINES = 10
# ΤΑ ΤΑΒΑΝΙΑ ΤΟΥ ΚΟΣΤΟΥΣ, µs του mu_tick (χωρίς το is_i5): μετρημένα στο βήμα
# 195 — 803 το χειρότερο σε 3.000 ticks, 124,5 ο μέσος όρος — και λίγο πάνω. Ενα
# tick χωρίς εγγραφή είναι 67-75 µs· κάθε κανάλι που γράφεται ~270, γιατί μία
# εγγραφή στον AY μέσω του PPI (snd_reg) κοστίζει 57.
WORST_US, MEAN_US = 850, 135


def check(ok, msg):
    print(("OK " if ok else "ΛΑΘΟΣ ") + msg)
    if not ok:
        FAIL.append(msg)


def fresh(patch=()):
    """Το main.sna ως τον κύριο βρόχο, με ό,τι αλλάζει το patch (διεύθυνση, byte)."""
    m = cpc.CPC()
    m.quickload(SNA)
    m.run_frames(150)
    for a, v in patch:
        m.poke(a, v)
    return m


def tick(m, sym):
    t = m.read_ram(sym["MU_FR"], 2)
    return t[0] | t[1] << 8


def heard(r):
    """Ο,τι ακούγεται: ανά κανάλι η ένταση, και η περίοδος αν η ένταση δεν είναι 0."""
    return tuple((r[8 + c], (r[2 * c] | r[2 * c + 1] << 8) if r[8 + c] else 0)
                 for c in range(3))


def until_pc(m, lo, hi, limit=40000):
    n = 0
    while not (lo <= m.pc < hi) and n < limit:
        m.run_us(10)
        n += 1
    return n < limit


def halt_loop(m):
    m.write_ram(LOOP, bytes([0xFB, 0x76, 0x18, 0xFD]))      # ei · halt · jr halt
    m.set_pc(LOOP)


def model(sym, n, patch=()):
    """Η μουσική με τον βρόχο σε halt, ένα δείγμα ανά tick. (ticks, λάθος, το
    πρώτο λάθος)."""
    m = fresh(patch)
    halt_loop(m)
    m.poke(sym["MU_OFF"], 0)
    ref = MU.frames(n + 50)
    seen, bad, first = set(), 0, None
    for _ in range(n + 200):
        if tick(m, sym) >= n:
            break
        m.run_frames(1)
        until_pc(m, LOOP, LOOP + 4)
        t = tick(m, sym)
        if t == 0 or t in seen or t > n:
            continue
        seen.add(t)
        r = m.psg_regs()
        if heard(r) != heard(ref[t - 1]) or r[7] != MU.MIXER:
            bad += 1
            if first is None:
                first = (t, heard(r), heard(ref[t - 1]), hex(r[7]))
    return len(seen), bad, first


PARK = LOOP + 26                 # το djnz του fx_loop, όπου διαβάζεται κάθε frame


def fx_loop(m, sym):
    """Ενας κύριος βρόχος όπως του παιχνιδιού για τον ήχο: ένα snd_tick ανά frame
    (έξι halt, όσες οι διακοπές), ένα εφέ όταν το ζητά το FLAG, και 0,8 ms σε
    ένα djnz, όπου η δοκιμή διαβάζει τον AY."""
    tk, pl = sym["SND_TICK"], sym["SND_PLAY"]
    code = [0xFB] + [0x76] * 6 + [0xCD, tk & 255, tk >> 8,            # 0-9
            0x3A, FLAG & 255, FLAG >> 8, 0xB7, 0x28, 0,                # 10-15
            0x3D, 0xCD, pl & 255, pl >> 8, 0xAF, 0x32, FLAG & 255, FLAG >> 8,   # 16-23
            0x06, 0x00, 0x10, 0xFE,                                     # ld b,0 · djnz $
            0x18, 0]
    code[15] = 24 - 16                                                  # jr z,ld b,0
    code[-1] = 0x100 - len(code)
    assert LOOP + 26 == PARK and LOOP + len(code) <= FLAG
    m.write_ram(LOOP, bytes(code))
    m.poke(FLAG, 0)
    m.set_pc(LOOP)


def fx_run(sym, music, patch=(), plan=None):
    """Τρία εφέ πάνω στη μουσική (ή χωρίς αυτήν). Ανά frame: (tick, καταχωρητές,
    τα wait των τριών καναλιών), διαβασμένα μετά το snd_tick του frame· και το
    σχέδιο {frame: εφέ}. Χωρίς σχέδιο, κάθε εφέ ξεκινά όταν η μουσική θα ήθελε
    το κανάλι του: ο συναγερμός με την καμπάνα να σβήνει, το «χτίστηκε» 6 ticks
    πριν από την εγγραφή του βάθους, το «όχι» με την ηχώ να σβήνει."""
    m = fresh(patch)
    fx_loop(m, sym)
    m.poke(sym["MU_OFF"], 0 if music else 1)
    out, made = [], {}
    want = [(150, SFX_ALERT, lambda: m.peek(sym["MU_A"]) >= 5),
            (250, SFX_BUILD, lambda: tick(m, sym) & 31 == 26),
            (330, SFX_DENY, lambda: m.peek(sym["MU_C"]) >= 2)]
    for f in range(560):
        if plan is not None:
            if f in plan:
                m.poke(FLAG, plan[f] + 1)
        elif want and f >= want[0][0] and (want[0][2]() or f >= want[0][0] + 150):
            made[f] = want[0][1]
            m.poke(FLAG, want.pop(0)[1] + 1)
        m.run_frames(1)
        until_pc(m, PARK, PARK + 2)
        st = m.read_ram(sym["SN_ST"], 12)
        out.append((tick(m, sym), list(m.psg_regs()), [st[4 * c] for c in range(3)]))
    return out, (plan if plan is not None else made)


CATCH = 33                      # ticks: το βάθος ξαναγράφεται κάθε 32 (src/music.asm)


def fx_verdict(on, off):
    """(εφέ που κράτησαν το κανάλι τους, κανάλια-frames μουσικής σωστά, εφέ
    μετά από τα οποία η μουσική γύρισε μέσα σε CATCH ticks, λάθη, πρώτο λάθος).
    Μετά από ένα εφέ το κανάλι γυρίζει στη μουσική στην επόμενη αλλαγή του:
    η καμπάνα και η ηχώ μέσα σε 4 ticks όσο ακούγονται, το βάθος ως 32."""
    ref = MU.frames(1000)
    kept = moved = back = bad = 0
    first = None
    since = [None] * 3                  # frames από το τέλος του τελευταίου εφέ
    for f, ((t, r, w), (_, r0, w0)) in enumerate(zip(on, off)):
        for c in range(3):
            if w[c] and not (f and on[f - 1][2][c]):
                since[c] = 0                # ζητήθηκε: το πρώτο βήμα στο επόμενο snd_tick
                continue
            if w[c]:
                tone = (r[7] >> c) & 1 == 0 and r[8 + c] & 15
                same = (r[8 + c] == r0[8 + c] and (r[7] >> c) & 9 == (r0[7] >> c) & 9 and
                        (not tone or r[2 * c:2 * c + 2] == r0[2 * c:2 * c + 2]))
                kept += same
                if not same:
                    bad += 1
                    first = first or (f, c, "εφέ", r[8 + c], r0[8 + c], hex(r[7]), hex(r0[7]))
                since[c] = 0
                continue
            if not t:
                continue
            ok = heard(r)[c] == heard(ref[t - 1])[c] and (r[7] >> c) & 9 == 8
            if since[c] is not None:
                since[c] += 1
                if ok:
                    back += 1
                    since[c] = None
                elif since[c] > CATCH:
                    bad += 1
                    first = first or (f, c, "δεν γύρισε", heard(r)[c], heard(ref[t - 1])[c], hex(r[7]))
                    since[c] = None
                continue
            moved += ok
            if not ok:
                bad += 1
                first = first or (f, c, "μουσική", heard(r)[c], heard(ref[t - 1])[c], hex(r[7]))
    return kept, moved, back, bad, first


def scan_loop(m, sym):
    """Σάρωση του πληκτρολογίου και εγγραφή του R6, ξανά και ξανά: όσο κρατά ο
    βρόχος, σχεδόν κάθε διακοπή πέφτει μέσα στο in_scan ή στο snd_reg."""
    sc, kn, sr = sym["IN_SCAN"], sym["KEY_NOW"], sym["SND_REG"]
    code = [0xFB,                                # 0
            0xCD, sc & 255, sc >> 8,             # 1   call in_scan
            0x21, kn & 255, kn >> 8,             # 4   ld hl,key_now
            0x06, KEY_LINES,                     # 7   ld b,10
            0x7E, 0x3C, 0x28, 9,                 # 9   ld a,(hl) · inc a · jr z,+9
            0xE5, 0x2A, CNT & 255, CNT >> 8,     # 13  push hl · ld hl,(CNT)
            0x23, 0x22, CNT & 255, CNT >> 8, 0xE1,   # 17  inc hl · ld (CNT),hl · pop hl
            0x23, 0x10, 0x100 - 16,              # 22  inc hl · djnz 9
            0x3E, 6, 0x21, VAL & 255, VAL >> 8,  # 25  ld a,6 · ld hl,VAL
            0xCD, sr & 255, sr >> 8,             # 30  call snd_reg
            0x18, 0]                             # 33
    code[-1] = 0x100 - len(code)
    assert LOOP + len(code) <= VAL
    m.write_ram(LOOP, bytes(code))
    m.write_ram(CNT, b"\0\0")
    m.poke(VAL, R6_VAL)
    m.set_pc(LOOP)


def scan_run(sym, patch=()):
    m = fresh(patch)
    scan_loop(m, sym)
    m.poke(sym["MU_OFF"], 0)
    t0, r6bad = tick(m, sym), 0
    for _ in range(600):
        m.run_frames(1)
        r6bad += m.psg_reg(6) != R6_VAL
    cnt = m.peek(CNT) | m.peek(CNT + 1) << 8
    return cnt, r6bad, tick(m, sym) - t0


def mu_cost(m, sym, n):
    """Το mu_tick σε n διαδοχικά ticks, όπως από το is_i5 (AF, BC στη στοίβα,
    τέλος στο is_out), με το ei του is_out σβηστό όσο μετρά: µs ανά tick,
    χωρίς το ίδιο το probe (ένα που πηγαίνει κατευθείαν στο is_out)."""
    out = sym["IS_OUT"]
    ei = out + 2
    assert m.peek(ei) == 0xFB, "το is_out δεν είναι pop bc · pop af · ei · ret"
    stub = LOOP + 0x10

    def probe(target):
        code = [0xF3, 0x31, 0x00, 0x01, 0xCD, stub & 255, stub >> 8, 0x18, 0xFE]
        m.write_ram(LOOP, bytes(code))
        m.write_ram(stub, bytes([0xF5, 0xC5, 0xC3, target & 255, target >> 8]))
        m.set_pc(LOOP)
        t = 0
        while not (LOOP + 7 <= m.pc <= LOOP + 8) and t < 5000:
            m.run_us(1)
            t += 1
        return t
    m.poke(ei, 0)
    base = probe(out)
    ts = [probe(sym["MU_TICK"]) - base for _ in range(n)]
    m.poke(ei, 0xFB)
    return ts


def disc_boot():
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "mkdsk.py")],
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit("mkdsk.py απέτυχε:\n" + r.stdout + r.stderr)
    m = cpc.CPC()
    m.run_frames(300)
    m.insert_disc(DSK)
    m.type_text('|disc\n', hold_frames=4, gap_frames=8)
    m.run_frames(60)
    m.type_text('run"habitat\n', hold_frames=4, gap_frames=8)
    if MR.pick(m, MR.syms(ROOT), 0) is None:
        return None
    return m


def main():
    sym, g = TG.build()
    b6 = lambda m: cpc._lib.cpcemu_ram_ptr(m._h, 6)          # noqa: E731

    # --- κλειστή στο main.sna, ανοιχτή στον δίσκο ---------------------------
    snap = open(SNA, "rb").read()
    import mkdsk
    gb = mkdsk.staged("GAME.BIN", "game.bin")
    raw = open(os.path.join(ROOT, "build", "game.bin"), "rb").read()
    at = sym["MU_OFF"] - 0x0100
    sv6 = 256 + 0x10000 + 2 * 0x4000 + sym["MU_SAVED"] - 0x4000
    check(snap[256 + sym["MU_OFF"]] == 1 and snap[sv6] == 1 and raw[at] == 1 and gb[at] == 0
          and len(gb) == len(raw) and sum(a != b for a, b in zip(gb, raw)) == 1,
          f"κλειστή στο main.sna (mu_off {snap[256 + sym['MU_OFF']]}, EC_MUS {snap[sv6]}), "
          f"ανοιχτή στο GAME.BIN του δίσκου (mu_off {gb[at]}, ένα byte διαφορετικό "
          f"από το game.bin)")
    check(sym["MU_TICK"] == 0x3E80 and sym["ZZ_BANK0_END"] <= 0x3E80 <= sym["ZZ_MUSIC_END"] <= 0x4000,
          f"η μουσική στο #{sym['MU_TICK']:04X}-#{sym['ZZ_MUSIC_END'] - 1:04X}, πάνω από τον "
          f"κώδικα της τράπεζας 0 (ως το #{sym['ZZ_BANK0_END']:04X})")
    m = fresh()
    t0 = tick(m, sym)
    loud = 0
    for _ in range(300):
        m.run_frames(1)
        r = m.psg_regs()
        loud += any(r[8 + c] for c in range(3))
    check(tick(m, sym) == t0 and loud == 0,
          f"κλειστή: 300 frames του παιχνιδιού χωρίς tick ({tick(m, sym) - t0}) και "
          f"χωρίς ένταση ({loud} frames)")
    del m

    # --- το μοντέλο -------------------------------------------------------------
    n, bad, first = model(sym, 3000)
    check(n >= 2970 and bad == 0,
          f"το mu_tick ίδιο με το tools/music.py σε {n} ticks, τόνος και ένταση "
          f"όπου ακούγεται, ο μίκτης #38 ({bad} λάθη{', πρώτο ' + str(first) if first else ''})")
    dc = CA.find(fresh(), sym["MU_TICK"], [0x3C, 0xE6, 0x03], 40)      # inc a · and 3
    dc = dc + 1 if dc else None
    # η νότα που ακούγεται συχνότερα στα πρώτα 1.500 ticks, ένα σκαλί πιο ψηλά
    use = [MU.SCALE.index(r[0]) for r in MU.frames(1500) if r[8] == MU.BELL]
    deg = max(set(use), key=use.count)
    for what, patch in ((f"μία νότα της κλίμακας ({MU.SCALE[deg]} -> {MU.SCALE[deg] + 1})",
                         [(sym["MU_SCALE"] + deg, MU.SCALE[deg] + 1)]),
                        ("το σβήσιμο κάθε 8 frames", [(dc + 1, 7)] if dc else []),
                        ("ένα σκαλί του βάθους (3 -> 4)", [(sym["MU_SWELL"] + 5, 4)])):
        n, bad, _ = model(sym, 1500, patch)
        check(bool(patch) and bad > 0, f"ΑΡΝΗΤΙΚΟ: {what}: {bad} ticks λάθος από {n}")

    # --- τα εφέ παίρνουν μόνο το κανάλι τους -----------------------------------
    on, plan = fx_run(sym, True)
    off, _ = fx_run(sym, False, plan=plan)
    kept, moved, back, bad, first = fx_verdict(on, off)
    busy = [sum(1 for _, _, w in on if w[c]) - 1 for c in range(3)]
    check(min(busy) > 0 and bad == 0 and kept == sum(busy) and moved > 1000 and back == 3,
          f"συναγερμός στο A, «χτίστηκε» στο B, «όχι» στο C ({busy} frames): το "
          f"κανάλι του εφέ ίδιο με χωρίς μουσική ({kept}), τα άλλα με το μοντέλο "
          f"({moved} κανάλια-frames), και μετά τα {back} εφέ η μουσική ξανά μέσα σε "
          f"{CATCH} ticks, μίκτης #38 ({bad} λάθη{', πρώτο ' + str(first) if first else ''})")
    # οι τρεις έλεγχοι του wait: ld a,(sn_st + κανάλι) · or a · jr nz -> nop nop
    m = fresh()
    waits = [CA.find(m, sym["MUO_GO"], [0x3A, (sym["SN_ST"] + 4 * c) & 255,
                                         (sym["SN_ST"] + 4 * c) >> 8, 0xB7, 0x20], 80)
             for c in range(3)]
    end = CA.find(m, sym["STK_END"], [0x3E, 0x38], 24)
    del m
    nowait = [(a + 4 + i, 0) for a in waits if a for i in range(2)]
    neg, _ = fx_run(sym, True, nowait, plan)
    _, _, _, bad, first = fx_verdict(neg, off)
    check(len(nowait) == 6 and bad > 0,
          f"ΑΡΝΗΤΙΚΟ: η μουσική χωρίς τον έλεγχο του wait: {bad} λάθη ({first})")
    neg, _ = fx_run(sym, True, [(end + 1, 0xFF)] if end else [], plan)
    neg0, _ = fx_run(sym, False, [(end + 1, 0xFF)] if end else [], plan)
    _, _, _, bad, _ = fx_verdict(neg, neg0)
    check(bool(end) and bad > 0,
          f"ΑΡΝΗΤΙΚΟ: το τέλος του εφέ με #FF (όπως ως το βήμα 194): {bad} λάθη")

    # --- ο AY του κύριου βρόχου ------------------------------------------------
    cnt, r6bad, moved = scan_run(sym)
    check(cnt == 0 and r6bad == 0 and moved > 100,
          f"σάρωση και snd_reg χωρίς τέλος, με τη μουσική: {cnt} σαρώσεις χαλασμένες, "
          f"ο R6 ξένος σε {r6bad} frames από 600, η μουσική {moved} ticks")
    pcs = []
    m = fresh()
    for page in (sym["IN_SCAN"] >> 8, sym["SND_REG"] >> 8):
        a = CA.find(m, sym["MUO_GO"], [0xFE, page, 0x28], 30)    # cp σελίδα · jr z,muo_done
        if a is not None:
            pcs.append(a + 2)
    del m
    patch = [(p + i, 0) for p in pcs for i in range(2)]
    cnt, r6bad, _ = scan_run(sym, patch)
    check(len(pcs) == 2 and (cnt > 0 or r6bad > 0),
          f"ΑΡΝΗΤΙΚΟ: χωρίς τον έλεγχο του PC: {cnt} σαρώσεις χαλασμένες, ο R6 ξένος "
          f"σε {r6bad} frames")

    # --- το U ------------------------------------------------------------------
    m = fresh([(sym["MU_OFF"], 0)])
    b6(m)[sym["MU_SAVED"] - 0x4000] = 0
    m.run_frames(100)
    m.set_joystick_type(0)

    def tap(k):
        m.tap_key(k, hold_frames=4, gap_frames=20)

    def state(frames):
        t = tick(m, sym)
        loud = 0
        for _ in range(frames):
            m.run_frames(1)
            loud += any(m.psg_reg(8 + c) for c in range(3))
        return m.peek(sym["MU_OFF"]), b6(m)[sym["MU_SAVED"] - 0x4000], tick(m, sym) - t, loud

    s0 = state(200)
    tap("u")
    s1 = state(200)
    tap("u")
    s2 = state(300)
    check(s0[0] == 0 and s0[2] >= 199 and s0[3] > 0 and s1[:3] == (1, 1, 0) and s1[3] == 0
          and s2[:2] == (0, 0) and s2[2] >= 299 and s2[3] > 0,
          f"U στο LOOK: παίζει {s0}, U κλειστή {s1}, U ξανά {s2} "
          f"(mu_off, EC_MUS, ticks, frames με ένταση)")
    tap("m")
    m.run_frames(20)
    acts = m.peek(sym["UI_STATE"])
    tap("u")
    m.run_frames(10)
    s3 = state(100)
    check(s3[:3] == (1, 1, 0) and s3[3] == 0 and m.peek(sym["UI_STATE"]) == 0 and acts != 0,
          f"M και U, από τη ΔΙΑΧΕΙΡΙΣΗ: κλειστή {s3}, και πίσω στο LOOK "
          f"(κατάσταση {acts} -> {m.peek(sym['UI_STATE'])})")
    del m

    # --- το φόρτωμα ------------------------------------------------------------
    def swap(patch=()):
        m = fresh([(sym["MU_OFF"], 1)] + list(patch))
        img = bytes(b6(m)[0:0x4000])
        b6(m)[sym["MU_SAVED"] - 0x4000] = 1
        sw = sym["SVX_SWAP"]
        call = [0xF3, 0x31, 0x00, 0x01, 0xCD, sw & 255, sw >> 8, 0x18, 0xFE]
        m.write_ram(LOOP, bytes(call))
        m.set_pc(LOOP)
        until_pc(m, LOOP + 7, LOOP + 9)
        first = m.peek(sym["MU_OFF"])
        b6(m)[sym["MU_SAVED"] - 0x4000] = 0             # ό,τι έφερε το σώσιμο
        m.set_pc(LOOP)
        until_pc(m, LOOP + 7, LOOP + 9)
        after = bytes(b6(m)[0:0x4000])
        same = sum(1 for i in range(0x4000) if after[i] != img[i]
                   and i != sym["MU_SAVED"] - 0x4000)
        return first, m.peek(sym["MU_OFF"]), same
    first, last, diff = swap()
    check(first == 1 and last == 0 and diff == 0,
          f"το svx_swap: πριν από το σώσιμο το mu_off μένει {first}, μετά γίνεται του "
          f"σωσίματος ({last}), και η τράπεζα 6 γυρίζει ίδια ({diff} bytes αλλιώς)")
    m = fresh()
    st = CA.find(m, sym["SVX_SWAP"], [0x32, sym["MU_OFF"] & 255, sym["MU_OFF"] >> 8], 60)
    del m
    _, last, _ = swap([(st + i, 0) for i in range(3)] if st else [])
    check(bool(st) and last == 1, f"ΑΡΝΗΤΙΚΟ: χωρίς την εγγραφή στο mu_off: μένει {last}")

    # --- από τον δίσκο: παίζει, και το σώσιμο την κρατά --------------------------
    m = disc_boot()
    ok = m is not None
    if ok:
        for _ in range(120):
            m.run_frames(30)
            if m.peek(g + 2) | m.peek(g + 3) << 8 == 100 and m.peek(g + 58) == 6:
                break                                   # §10.1, όπως το test_save
        m.run_frames(200)
        m.set_joystick_type(0)
        st0 = state(200)
        import hudread

        def press(key, frames=24):
            m.key_down(key)
            m.run_frames(4)
            m.key_up(key)
            m.run_frames(frames)

        def disc_op(key, slot):
            press(key)
            n = 0
            while m.peek(sym["SL_PICK"]) != slot and n < 6:
                press(cpc.KEY_RIGHT)
                n += 1
            m.poke(sym["FD_TRK"], 0)
            press(cpc.KEY_SPACE, 4)
            msg = ""
            for _ in range(300):
                m.run_frames(1)
                r = hudread.text(m, sym, 3)
                if "SLOT" in r or "ERROR" in r:
                    msg = r.strip()
                    break
            m.run_frames(60)
            return msg

        tap("u")
        a1 = disc_op("S", 0)
        tap("u")
        on1 = m.peek(sym["MU_OFF"])
        b1 = disc_op("L", 0)
        st1 = state(150)
        tap("u")
        a2 = disc_op("S", 1)
        tap("u")
        off2 = m.peek(sym["MU_OFF"])
        b2 = disc_op("L", 1)
        st2 = state(300)
    check(ok and st0[0] == 0 and st0[2] >= 190 and st0[3] > 0
          and on1 == 0 and st1[:3] == (1, 1, 0) and st1[3] == 0
          and off2 == 1 and st2[:2] == (0, 0) and st2[2] >= 290 and st2[3] > 0,
          f"από τον δίσκο: παίζει {st0 if ok else '-'}; κλειστή σωσμένη "
          f"({a1 if ok else '-'}), ανοιχτή, φόρτωμα ({b1 if ok else '-'}): {st1 if ok else '-'}; "
          f"ανοιχτή σωσμένη, κλειστή, φόρτωμα: {st2 if ok else '-'}")
    del m

    # --- κόστος ----------------------------------------------------------------
    m = fresh()
    ts = mu_cost(m, sym, 3000)
    worst, mean = max(ts), sum(ts) / len(ts)
    # Ο,ΤΙ ΧΕΙΡΟΤΕΡΟ: καμπάνα (δύο φορές η γεννήτρια, η κλίμακα) στο frame της
    # συγχορδίας, με τα κανάλια ελεύθερα: δύο κανάλια γράφονται.
    m.write_ram(sym["MU_FR"], bytes([0, 2]))
    m.poke(sym["MU_BT"], 1)
    m.write_ram(sym["MU_RND"], bytes([0x80, 0x01]))         # -> #C0: νότα
    m.write_ram(sym["SN_ST"], bytes(12))
    full = mu_cost(m, sym, 1)[0]
    bell = m.peek(sym["MU_A"]) == MU.BELL
    check(worst <= WORST_US and full <= WORST_US and mean <= MEAN_US and bell,
          f"το mu_tick: το χειρότερο σε 3.000 ticks {worst} µs, με καμπάνα και "
          f"συγχορδία μαζί {full} µs (ταβάνι {WORST_US}), μέσος όρος {mean:.1f} µs "
          f"(ταβάνι {MEAN_US}) — {mean / 200:.2f}% ενός frame")

    print()
    print("ΟΛΑ ΚΑΛΑ" if not FAIL else f"{len(FAIL)} ΑΠΟΤΥΧΙΕΣ")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
