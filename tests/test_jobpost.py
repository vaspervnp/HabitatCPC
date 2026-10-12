#!/usr/bin/env python3
"""Το jb_post_build και το sp_post του src/supply.asm, στο main.sna, απέναντι
στον κανόνα.

  Η πρώτη θέση με είδος NO_JOB γίνεται [J_BUILD, κόμβος, 255, 5, κόμβος] (§6.7:
  αδιάθετη, προτεραιότητα 5 από το job_prio, και από το βήμα 88 ο κόμβος και
  στο J_SITE). Τίποτε άλλο δεν αλλάζει — ούτε μέσα στον πίνακα ούτε 64 bytes
  πριν και μετά. Το sp_post (βήμα 88) το ίδιο, με [είδος, κόμβος, 255, 4,
  κόμβος] για τα δύο είδη Supply, και κρατά τα A, C.

  ΜΕ ΓΕΜΑΤΟ ΠΙΝΑΚΑ (βήμα 115): η εγγραφή μπαίνει στη θέση μιας Operate (1) ή
  Repair (4) με J_AGENT = 255 — της χαμηλότερης J_PRIO, και στην ισοπαλία της
  πρώτης· μια προτεραιότητα 255 δεν μετρά (ξεκινά από εκεί). Αν δεν υπάρχει
  καμία, τίποτα, και το jb_lost γίνεται ≠ 0· αλλιώς μένει όπως ήταν. Ως το
  114 ο γεμάτος πίνακας δεν έγραφε ποτέ, και ένα εργοτάξιο τοποθετημένο τότε
  δεν χτιζόταν ποτέ (tests/test_repost.py).

Ως το βήμα 87 ζούσε στο src/jobpost.asm, στην τράπεζα 0· το 88 το πήγε στην
τράπεζα 2, ίδιο εκτός από το τελευταίο byte.

Πίνακες: άδειος, γεμάτος, η μόνη ελεύθερη σε κάθε θέση 0..31, η πρώτη ελεύθερη
σε κάθε θέση με κι άλλες μετά, και τυχαίοι. Τα άλλα bytes των εγγραφών τυχαία,
μαζί και 255 εκεί που δεν είναι είδος.

ΓΙΑΤΙ. Ως το βήμα 70 το έβλεπαν σενάρια που χτίζουν κάτι ή ρίχνουν μετεωρίτη, σε
πίνακα με λίγες εργασίες. Δύο λάθη πέρασαν όλες τις δοκιμές: η τελευταία θέση
(31) να μη χρησιμοποιείται ποτέ, και ένας γεμάτος πίνακας να γράφει 5 bytes
ΜΕΤΑ το τέλος του.

Και ο ΧΡΟΝΟΣ: θέση 0 και θέση 31 όχι πιο αργά από όσο μετρήθηκε στο βήμα 70
(με το jobpost.asm του βήματος 69 αποτυγχάνουν και τα δύο). Ο γεμάτος πίνακας
ήταν 502 us ως το 114· από το 115 ψάχνει και τη θέση που θα πάρει, ένα
δεύτερο πέρασμα των 32: ~1.360 us, ταβάνι 1.400, και με και χωρίς Operate
να δώσει.

Αρνητικά, με το snapshot πειραγμένο: 31 θέσεις, χωρίς το dec (hl) που
επαναφέρει μια πιασμένη θέση, και πέντε του βήματος 115 — χωρίς έξωση (ο
γεμάτος πίνακας γυρίζει αμέσως, όπως ως το 114), έξωση και ανατεθειμένης, η
υψηλότερη προτεραιότητα αντί για τη χαμηλότερη, η Drill (3) αντί για τη
Repair, και το jb_lost που δεν σηκώνεται.
"""
import os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import cpc                                               # noqa: E402

PROBE, AROUND = 0x3E00, 64
MAX_JOB, JOB_REC, NO_JOB, J_BUILD, J_SUPPLY = 32, 5, 255, 0, 7   # src/const.asm
# µs με το probe: θέση 0, θέση 31 (βήμα 70), γεμάτος (βήμα 115· 502 ως το 114)
CEIL = (47, 512, 1400)
J_OPERATE, J_REPAIR = 1, 4


def job_tbl():
    for line in open(os.path.join(ROOT, "build", "layout.asm"), encoding="utf-8"):
        if line.startswith("G_job_tbl"):
            return int(line.split("#")[1].split()[0], 16)
    raise SystemExit("δεν βρέθηκε το G_job_tbl στο build/layout.asm")


def check(sym, patch=(), timing=True, kind=None):
    """Η πρώτη διαφορά από τον κανόνα, ή None. kind = None: jb_post_build·
    αλλιώς sp_post με C = kind."""
    m = cpc.CPC()
    m.run_frames(60)
    assert m.quickload(TG.COLONY, start=False), "quickload απέτυχε"
    for at, v in patch:
        m.poke(at, v)
    tbl, jp = job_tbl(), sym["JB_POST_BUILD" if kind is None else "SP_POST"]
    lost = sym["JB_LOST"]
    base, size = tbl - AROUND, MAX_JOB * JOB_REC + 2 * AROUND

    def run(node, step=20):
        # di · ld sp · ld a,κόμβος · [ld c,είδος] · call · ld (ξ),a · ld a,c · ld (ξ+1),a · jr $
        pre = [] if kind is None else [0x0E, kind]
        out = PROBE + 0x40
        # (τα δύο ld μόνο για το sp_post: ο χρόνος του jb_post_build μετριέται
        # με το probe του βήματος 70)
        keep = [] if kind is None else [0x32, out & 255, out >> 8, 0x79,
                                        0x32, (out + 1) & 255, (out + 1) >> 8]
        code = ([0xF3, 0x31, 0x00, 0x01, 0x3E, node] + pre + [0xCD, jp & 255, jp >> 8]
                + keep + [0x18, 0xFE])
        m.write_ram(PROBE, bytes(code))
        m.set_pc(PROBE)
        end, t = PROBE + len(code) - 2, 0
        while not (end <= m.pc <= end + 2):
            m.run_us(step)
            t += step
            if t > 100_000:
                return None
        return t

    rnd = random.Random(70)

    def table(free):
        """free = οι ελεύθερες θέσεις. Τα άλλα bytes τυχαία, και 255 συχνά."""
        t = bytearray(rnd.choice([rnd.randrange(256), 255]) for _ in range(size))
        for i in range(MAX_JOB):
            t[AROUND + JOB_REC * i] = NO_JOB if i in free else rnd.randrange(7)
        return t

    def evict(t):
        """Η θέση που δίνει ένας γεμάτος πίνακας: Operate ή Repair αδιάθετη, η
        χαμηλότερη προτεραιότητα κάτω από 255, η πρώτη. None αν καμία."""
        best, at = 255, None
        for i in range(MAX_JOB):
            r = t[AROUND + JOB_REC * i:][:JOB_REC]
            if r[0] in (J_OPERATE, J_REPAIR) and r[2] == 255 and r[3] < best:
                best, at = r[3], AROUND + JOB_REC * i
        return at

    def none_to_evict(t):
        for i in range(MAX_JOB):
            if t[AROUND + JOB_REC * i] in (J_OPERATE, J_REPAIR):
                t[AROUND + JOB_REC * i + 2] = rnd.randrange(255)
        return t

    cases = [set(), set(range(MAX_JOB))] + [{i} for i in range(MAX_JOB)]
    cases += [set() for _ in range(40)]                     # γεμάτοι: η έξωση
    cases += [{i} | {j for j in range(i + 1, MAX_JOB) if rnd.random() < 0.4} for i in range(MAX_JOB)]
    cases += [{j for j in range(MAX_JOB) if rnd.random() < p} for p in (0.05, 0.2, 0.5, 0.9) for _ in range(10)]
    for free in cases:
        before = table(free)
        m.write_ram(base, bytes(before))
        m.poke(lost, 0)
        node = rnd.randrange(256)
        if run(node) is None:
            return f"ελεύθερες {sorted(free)}: δεν γύρισε"
        want = bytearray(before)
        at = AROUND + JOB_REC * min(free) if free else evict(before)
        if at is not None:
            want[at:at + JOB_REC] = bytes([J_BUILD, node, 255, 5, node] if kind is None
                                          else [kind, node, 255, 4, node])
        got = m.read_ram(base, size)
        if (m.peek(lost) != 0) != (at is None):
            return (f"ελεύθερες {sorted(free)[:6]}: το jb_lost είναι {m.peek(lost)}, "
                    f"και η εργασία {'δεν ' if at is None else ''}μπήκε")
        if kind is not None and list(m.read_ram(PROBE + 0x40, 2)) != [node, kind]:
            return f"sp_post: τα A, C βγήκαν {list(m.read_ram(PROBE + 0x40, 2))}, όχι {[node, kind]}"
        if got != bytes(want):
            k = next(i for i in range(size) if got[i] != want[i])
            where = "πριν από τον πίνακα" if k < AROUND else "μετά τον πίνακα" if k >= size - AROUND else \
                f"θέση {(k - AROUND) // JOB_REC}, byte {(k - AROUND) % JOB_REC}"
            return f"ελεύθερες {sorted(free)[:6]}, κόμβος {node}: {where} = {got[k]}, ο κανόνας λέει {want[k]}"
    if not timing:
        return None
    slow, got = [], []
    full = table(set())
    if evict(full) is None:
        return "ο γεμάτος πίνακας του χρόνου δεν έχει τι να δώσει"
    for label, t0, ceil in (("θέση 0", table({0}), CEIL[0]), ("θέση 31", table({31}), CEIL[1]),
                            ("γεμάτος", full, CEIL[2]),
                            ("γεμάτος χωρίς έξωση", none_to_evict(table(set())), CEIL[2])):
        m.write_ram(base, bytes(t0))
        t = run(7, step=1)
        got.append(t)
        if t > ceil:
            slow.append(f"{label} {t} > {ceil} us")
    print(f"    θέση 0, θέση 31, γεμάτος, γεμάτος χωρίς έξωση: {got} us")
    return "πιο αργό από το ταβάνι: " + ", ".join(slow) if slow else None


def main():
    sym, _ = TG.build()
    fails = 0
    why = check(sym)
    if why:
        print(f"ΑΠΟΤΥΧΙΑ: {why}")
        fails += 1
    else:
        print("OK jb_post_build = ο κανόνας σε 146 πίνακες (άδειος, 41 γεμάτοι, κάθε θέση), "
              "τίποτα δεν αλλάζει γύρω από τον πίνακα, το jb_lost μόνο όταν δεν μπήκε")
        print("OK θέση 0 και 31 όχι πιο αργά από το βήμα 70, ο γεμάτος κάτω από 1.400 us")
    for kind in (J_SUPPLY, J_SUPPLY + 1):
        why = check(sym, timing=False, kind=kind)
        if why:
            print(f"ΑΠΟΤΥΧΙΑ sp_post {kind}: {why}")
            fails += 1
        else:
            print(f"OK sp_post είδους {kind} = ο κανόνας στους ίδιους 146 πίνακες, και τα A, C μένουν")

    # --- αρνητικά ---
    m = cpc.CPC()
    m.run_frames(60)
    assert m.quickload(TG.COLONY, start=False)
    jp, lost = sym["JB_POST_BUILD"], sym["JB_LOST"]
    code = m.read_ram(jp, 96)
    ib = code.find(bytes([0x06, MAX_JOB]))                       # ld b,MAX_JOB
    il = code.find(bytes([0x34, 0x28]))                          # inc (hl) · jr z
    assert ib >= 0 and il >= 0 and code[il + 3] == 0x35, "δεν βρέθηκαν τα ld b / inc (hl) / dec (hl)"
    ifull = il + 3 + 4                                           # dec (hl) · add hl,de · djnz e · push ix
    assert code[ifull:ifull + 2] == bytes([0xDD, 0xE5]), "δεν βρέθηκε το push ix μετά το djnz"
    ia = code.find(bytes([0xDD, 0x7E, 2, 0x3C, 0x20]))           # ld a,(ix+J_AGENT) · inc a · jr nz
    ip = code.find(bytes([0xB9, 0x30]))                          # cp c · jr nc
    ir = code.find(bytes([0xFE, J_REPAIR, 0x20]))                # cp J_REPAIR · jr nz
    ih = code.find(bytes([0x21, lost & 255, lost >> 8, 0x74]))   # ld hl,jb_lost · ld (hl),h
    assert min(ia, ip, ir, ih) >= 0, f"δεν βρέθηκε η έξωση: {ia} {ip} {ir} {ih}"
    for label, patch in (("31 θέσεις", [(jp + ib + 1, MAX_JOB - 1)]),
                         ("το dec (hl) σβησμένο", [(jp + il + 3, 0)]),
                         ("χωρίς έξωση (ret στο γεμάτο, όπως ως το 114)", [(jp + ifull, 0xC9)]),
                         ("έξωση και ανατεθειμένης", [(jp + ia + 4, 0), (jp + ia + 5, 0)]),
                         ("η υψηλότερη αντί για τη χαμηλότερη", [(jp + ip + 1, 0x38)]),
                         ("η Drill αντί για τη Repair", [(jp + ir + 1, 3)]),
                         ("το jb_lost δεν σηκώνεται", [(jp + ih + 3, 0)])):
        why = check(sym, patch, timing=False)
        if why:
            print(f"OK ΑΡΝΗΤΙΚΟ: με {label} αποτυγχάνει ({why[:80]})")
        else:
            print(f"ΑΠΟΤΥΧΙΑ ΑΡΝΗΤΙΚΟΥ: με {label} περνά")
            fails += 1
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
