#!/usr/bin/env python3
"""Οι τρεις πυρήνες γραμμής του blit.asm, ένας-ένας, απέναντι σε μοντέλο του
δαχτυλιδιού των 2 KB (DESIGN §8.2).

ΓΙΑΤΙ ΧΩΡΙΣΤΑ. Τα test_object, test_index και test_scroll βλέπουν τους πυρήνες
μέσα από σκηνές, και μια σκηνή περνά από το σημείο τυλίγματος σε λίγες γραμμές:
στο βήμα 66 το φίλτρο (d&7)==7 με λάθος μάσκα το έπιασαν μόνο σε μία κάμερα, με
3 bytes διαφορά. Και κανένα δεν μετρούσε χρόνο πυρήνα. Εδώ καλείται κάθε
πυρήνας κατευθείαν, οι μισές κλήσεις πάνω στο τύλιγμα:

  blt_op_line    οθόνη = πηγή
  blt_mask_line  οθόνη = (οθόνη & μάσκα) | χρώμα, ζεύγη προς τα εμπρός
  blt_mask_flip  το ίδιο με ζεύγη προς τα ΠΙΣΩ και κάθε byte καθρεφτισμένο

Το μοντέλο γράφει το byte i στο base | ((p + i) & #7FF) — η πρόζα του §8.2,
όχι ο Z80. Ελέγχονται η οθόνη ολόκληρη, το HL (ή το IX του flip) στο τέλος, ότι
ο κώδικας, η πηγή και οι τράπεζες 1, 2 και 6 δεν άλλαξαν, και ο ΧΡΟΝΟΣ: μια γραμμή 80 bytes,
απλή και πάνω στο τύλιγμα, δεν παίρνει περισσότερο από όσο μετρήθηκε στο
βήμα 66 (με τα αρχεία του βήματος 65 αποτυγχάνουν και οι έξι).

Αρνητικά, με το snapshot πειραγμένο: φίλτρο (d&7)==7 με λάθος μάσκα, το DE που
δεν γυρίζει στην αρχή του δαχτυλιδιού, το flip που προχωρά ένα byte αντί για
ζεύγος.
"""
import ctypes, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_pack_z80 as TP                               # noqa: E402
import cpc                                               # noqa: E402

PROBE, SRC, OUT = 0x3F00, 0x2000, 0x3FE0
N = 600                                                  # κλήσεις ανά πυρήνα
# µs ανά κλήση στο probe (setup + πυρήνας), B = 80, μετρημένα στο βήμα 66
CEIL = {"op": (532, 570), "mask": (1489, 1521), "flip": (2619, 2654)}   # (απλή, τύλιγμα)
KERNELS = (("op", "BLT_OP_LINE"), ("mask", "BLT_MASK_LINE"), ("flip", "BLT_MASK_FLIP"))


def flip(x):
    """Mode 0: το pixel 0 στα bits 7,5,3,1, το 1 στα 6,4,2,0 — αντάλλαξέ τα."""
    return ((x & 0xAA) >> 1) | ((x & 0x55) << 1)


def check(sym, patch=(), timing=True):
    """Η πρώτη διαφορά από το μοντέλο, ή None."""
    m = cpc.CPC()
    m.run_frames(60)
    assert m.quickload(TP.SNA, start=False), "quickload απέτυχε"
    top = max(v for k, v in sym.items() if v < 0x4000)
    assert top < SRC, f"το packtest φτάνει ως #{top:04X}"
    for at, v in patch:
        m.poke(at, v)

    def run(code, step=20):
        # di · sp · τράπεζα 6 · code · ld (OUT),hl · ld (OUT+2),ix · jr $
        code = ([0xF3, 0x31, 0x00, 0x01, 0x01, 0xC6, 0x7F, 0xED, 0x49] + code +
                [0x22, OUT & 255, OUT >> 8, 0xDD, 0x22, (OUT + 2) & 255, OUT >> 8, 0x18, 0xFE])
        m.write_ram(PROBE, bytes(code))
        m.set_pc(PROBE)
        end, t = PROBE + len(code) - 2, 0
        while not (end <= m.pc <= end + 2):
            m.run_us(step)
            t += step
            if t > 200_000:
                return None
        return t

    # το read_ram βλέπει τη βασική τράπεζα 1 στο #4000, όχι το παράθυρο
    bank = lambda n: ctypes.string_at(cpc._lib.cpcemu_ram_ptr(m._h, n), 0x4000)
    tab = bank(6)[:256]                                  # FLIPTAB = G_flip_mode0, #4000
    bad = [x for x in range(256) if tab[x] != flip(x)]
    assert not bad, f"το flip_mode0 δεν είναι καθρέφτης mode 0: #{bad[0]:02X} -> #{tab[bad[0]]:02X}"

    rnd = random.Random(66)
    ld = lambda op, v: op + [v & 255, v >> 8]

    def one(kind, name, de, B, step=20):
        scr = bytearray(rnd.randbytes(0x4000))
        src = rnd.randbytes(0x400)
        m.write_ram(0xC000, bytes(scr))
        m.write_ram(SRC, src)
        rest = [m.read_ram(0x0100, 0x3E00)] + [bank(n) for n in (1, 2, 6)]
        hl = SRC + (2 * (B - 1) + 2 if kind == "flip" else rnd.randrange(64))
        t = run(ld([0x11], de) + ld([0x21], hl) + ld([0x01], B << 8 | 0xA5) + ld([0xDD, 0x21], 0x1234)
                + ld([0xCD], sym[name]), step)
        where = f"{kind} B={B} DE=#{de:04X}"
        if t is None:
            return where + ": δεν γύρισε", None
        base, p = de & 0xF800, de & 0x7FF
        for i in range(B):
            a = (base | ((p + i) & 0x7FF)) - 0xC000
            if kind == "op":
                scr[a] = src[hl - SRC + i]
            elif kind == "mask":
                scr[a] = (scr[a] & src[hl - SRC + 2 * i]) | src[hl - SRC + 2 * i + 1]
            else:
                j = hl - SRC - 2 * i
                scr[a] = (scr[a] & flip(src[j])) | flip(src[j + 1])
        got = m.read_ram(0xC000, 0x4000)
        if got != bytes(scr):
            k = next(i for i in range(0x4000) if got[i] != scr[i])
            return f"{where}: η οθόνη διαφέρει, πρώτο στο #{0xC000 + k:04X}", t
        o = m.read_ram(OUT, 4)
        want = {"op": ("HL", 0, hl + B), "mask": ("HL", 0, hl + 2 * B), "flip": ("IX", 2, hl - 2 * B)}[kind]
        if (o[want[1]] | o[want[1] + 1] << 8) != want[2] & 0xFFFF:
            return f"{where}: {want[0]} #{o[want[1]] | o[want[1] + 1] << 8:04X}, περίμενα #{want[2]:04X}", t
        if [m.read_ram(0x0100, 0x3E00)] + [bank(n) for n in (1, 2, 6)] != rest:
            return f"{where}: γράφτηκε έξω από την οθόνη", t
        return None, t

    for k in range(N):
        B = rnd.choice([1, 2, 3, 4, 8, 16, 32, 80, rnd.randrange(1, 81)])
        r = rnd.random()
        if r < 0.3:
            de = 0xC000 + rnd.randrange(0x4000)
        else:
            d = 0xC7 | rnd.randrange(8) << 3
            e = rnd.randrange(max(1, 256 - B), 256) if r < 0.8 else rnd.randrange(0, 256 - B + 1)
            de = d << 8 | e
        for kind, name in KERNELS:
            why, _ = one(kind, name, de, B)
            if why:
                return why
    if not timing:
        return None
    slow = []
    for kind, name in KERNELS:
        for at, (de, ceil) in enumerate(((0xC123, CEIL[kind][0]), (0xEFD0, CEIL[kind][1]))):
            why, t = one(kind, name, de, 80, step=1)
            if why:
                return why
            print(f"    {kind:4s} 80 bytes {('απλή       ', 'στο τύλιγμα')[at]}: {t} us (ταβάνι {ceil})")
            if t > ceil:
                slow.append(f"{kind} {('απλή', 'στο τύλιγμα')[at]} {t} > {ceil} us")
    return "πιο αργά από το βήμα 66: " + ", ".join(slow) if slow else None


def main():
    sym = TP.build()
    fails = 0
    why = check(sym)
    if why:
        print(f"ΑΠΟΤΥΧΙΑ: {why}")
        fails += 1
    else:
        print(f"OK {3 * N} κλήσεις, οι μισές πάνω στο τύλιγμα: οθόνη, HL/IX, τίποτα έξω από την οθόνη")
        print("OK κανένας πυρήνας πιο αργός από το βήμα 66, απλός ή στο τύλιγμα")

    # --- αρνητικά ---
    ml, wr, fr = sym["BLT_MASK_LINE"], sym["BL_WRAP"], sym["BMF_RUN"]
    m = cpc.CPC()
    m.run_frames(60)
    assert m.quickload(TP.SNA, start=False)
    assert m.read_ram(ml, 3) == bytes([0x7A, 0xF6, 0xF8]), "το blt_mask_line δεν ξεκινά με ld a,d / or #F8"
    assert m.read_ram(wr + 9, 2) == bytes([0xD6, 8]), "το bl_wrap δεν έχει sub 8 στο +9"
    code = m.read_ram(fr, 32)
    dix = code.find(bytes([0xDD, 0x2B, 0xDD, 0x2B, 0x10]))
    assert dix > 0, "το bmf_run δεν έχει dec ix / dec ix / djnz"
    for label, patch in (("φίλτρο (d&15)==15", [(ml + 2, 0xF0)]),
                         ("το DE δεν γυρίζει στην αρχή του δαχτυλιδιού", [(wr + 10, 0)]),
                         ("flip ένα byte ανά ζεύγος", [(fr + dix, 0), (fr + dix + 1, 0)])):
        why = check(sym, patch, timing=False)
        if why:
            print(f"OK ΑΡΝΗΤΙΚΟ: με {label} αποτυγχάνει ({why[:70]})")
        else:
            print(f"ΑΠΟΤΥΧΙΑ ΑΡΝΗΤΙΚΟΥ: με {label} περνά")
            fails += 1
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
