#!/usr/bin/env python3
"""Το jb_post_build του src/jobpost.asm, στο main.sna, απέναντι στον κανόνα.

  Η πρώτη θέση με είδος NO_JOB γίνεται [J_BUILD, κόμβος, 255, 5, 0] (§6.7:
  αδιάθετη, προτεραιότητα 5 από το job_prio). Τίποτε άλλο δεν αλλάζει — ούτε
  μέσα στον πίνακα ούτε 64 bytes πριν και μετά. Με γεμάτο πίνακα, τίποτα.

Πίνακες: άδειος, γεμάτος, η μόνη ελεύθερη σε κάθε θέση 0..31, η πρώτη ελεύθερη
σε κάθε θέση με κι άλλες μετά, και τυχαίοι. Τα άλλα bytes των εγγραφών τυχαία,
μαζί και 255 εκεί που δεν είναι είδος.

ΓΙΑΤΙ. Ως το βήμα 70 το έβλεπαν σενάρια που χτίζουν κάτι ή ρίχνουν μετεωρίτη, σε
πίνακα με λίγες εργασίες. Δύο λάθη πέρασαν όλες τις δοκιμές: η τελευταία θέση
(31) να μη χρησιμοποιείται ποτέ, και ένας γεμάτος πίνακας να γράφει 5 bytes
ΜΕΤΑ το τέλος του.

Και ο ΧΡΟΝΟΣ: θέση 0, θέση 31 και γεμάτος πίνακας, όχι πιο αργά από όσο
μετρήθηκε στο βήμα 70. Με το jobpost.asm του βήματος 69 αποτυγχάνουν και τα τρία.

Αρνητικά, με το snapshot πειραγμένο: χωρίς ret όταν γέμισε, 31 θέσεις, και
χωρίς το dec (hl) που επαναφέρει μια πιασμένη θέση.
"""
import os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import cpc                                               # noqa: E402

PROBE, AROUND = 0x3E00, 64
MAX_JOB, JOB_REC, NO_JOB, J_BUILD = 32, 5, 255, 0        # src/const.asm
# µs με το probe: θέση 0, θέση 31, γεμάτος (βήμα 70)
CEIL = (47, 512, 502)


def job_tbl():
    for line in open(os.path.join(ROOT, "build", "layout.asm"), encoding="utf-8"):
        if line.startswith("G_job_tbl"):
            return int(line.split("#")[1].split()[0], 16)
    raise SystemExit("δεν βρέθηκε το G_job_tbl στο build/layout.asm")


def check(sym, patch=(), timing=True):
    """Η πρώτη διαφορά από τον κανόνα, ή None."""
    m = cpc.CPC()
    m.run_frames(60)
    assert m.quickload(TG.COLONY, start=False), "quickload απέτυχε"
    for at, v in patch:
        m.poke(at, v)
    tbl, jp = job_tbl(), sym["JB_POST_BUILD"]
    base, size = tbl - AROUND, MAX_JOB * JOB_REC + 2 * AROUND

    def run(node, step=20):
        code = [0xF3, 0x31, 0x00, 0x01, 0x3E, node, 0xCD, jp & 255, jp >> 8, 0x18, 0xFE]
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

    cases = [set(), set(range(MAX_JOB))] + [{i} for i in range(MAX_JOB)]
    cases += [{i} | {j for j in range(i + 1, MAX_JOB) if rnd.random() < 0.4} for i in range(MAX_JOB)]
    cases += [{j for j in range(MAX_JOB) if rnd.random() < p} for p in (0.05, 0.2, 0.5, 0.9) for _ in range(10)]
    for free in cases:
        before = table(free)
        m.write_ram(base, bytes(before))
        node = rnd.randrange(256)
        if run(node) is None:
            return f"ελεύθερες {sorted(free)}: δεν γύρισε"
        want = bytearray(before)
        if free:
            at = AROUND + JOB_REC * min(free)
            want[at:at + JOB_REC] = bytes([J_BUILD, node, 255, 5, 0])
        got = m.read_ram(base, size)
        if got != bytes(want):
            k = next(i for i in range(size) if got[i] != want[i])
            where = "πριν από τον πίνακα" if k < AROUND else "μετά τον πίνακα" if k >= size - AROUND else \
                f"θέση {(k - AROUND) // JOB_REC}, byte {(k - AROUND) % JOB_REC}"
            return f"ελεύθερες {sorted(free)[:6]}, κόμβος {node}: {where} = {got[k]}, ο κανόνας λέει {want[k]}"
    if not timing:
        return None
    slow, got = [], []
    for label, free, ceil in (("θέση 0", {0}, CEIL[0]), ("θέση 31", {31}, CEIL[1]), ("γεμάτος", set(), CEIL[2])):
        m.write_ram(base, bytes(table(free)))
        t = run(7, step=1)
        got.append(t)
        if t > ceil:
            slow.append(f"{label} {t} > {ceil} us")
    print(f"    θέση 0, θέση 31, γεμάτος: {got} us")
    return "πιο αργό από το βήμα 70: " + ", ".join(slow) if slow else None


def main():
    sym, _ = TG.build()
    fails = 0
    why = check(sym)
    if why:
        print(f"ΑΠΟΤΥΧΙΑ: {why}")
        fails += 1
    else:
        print("OK jb_post_build = ο κανόνας σε 106 πίνακες (άδειος, γεμάτος, κάθε θέση), "
              "τίποτα δεν αλλάζει γύρω από τον πίνακα")
        print("OK όχι πιο αργό από το βήμα 70")

    # --- αρνητικά ---
    m = cpc.CPC()
    m.run_frames(60)
    assert m.quickload(TG.COLONY, start=False)
    jp = sym["JB_POST_BUILD"]
    code = m.read_ram(jp, 32)
    ib = code.find(bytes([0x06, MAX_JOB]))                       # ld b,MAX_JOB
    il = code.find(bytes([0x34, 0x28]))                          # inc (hl) · jr z
    assert ib >= 0 and il >= 0 and code[il + 3] == 0x35, "δεν βρέθηκαν τα ld b / inc (hl) / dec (hl)"
    iret = il + 3 + 4                                            # dec (hl) · add hl,de · djnz e · ret
    assert code[iret] == 0xC9, "δεν βρέθηκε το ret μετά το djnz"
    for label, patch in (("το ret όταν γέμισε σβησμένο", [(jp + iret, 0)]),
                         ("31 θέσεις", [(jp + ib + 1, MAX_JOB - 1)]),
                         ("το dec (hl) σβησμένο", [(jp + il + 3, 0)])):
        why = check(sym, patch, timing=False)
        if why:
            print(f"OK ΑΡΝΗΤΙΚΟ: με {label} αποτυγχάνει ({why[:80]})")
        else:
            print(f"ΑΠΟΤΥΧΙΑ ΑΡΝΗΤΙΚΟΥ: με {label} περνά")
            fails += 1
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
