#!/usr/bin/env python3
"""Ο παίκτης εφέ του src/sound.asm, στο main.sna, απέναντι στο §9.5.

Το tests/test_sound.py ακούει τον AY σε ένα δικό του harness, ένα εφέ τη φορά.
Εδώ οι ρουτίνες καλούνται ΜΕΣΑ στο παιχνίδι, με τυχαία σειρά — snd_tick,
snd_play, snd_ping, snd_off, snd_init — ώστε να συναντηθούν όσα δεν συναντά
ένα εφέ μόνο του: τρία κανάλια που αλλάζουν βήμα στο ίδιο tick, δύο θόρυβοι
που μοιράζονται τον R6, ένα εφέ που κόβει ή δεν κόβει άλλο, ένα snd_off στη
μέση. Μετά από κάθε κλήση, απέναντι σε ένα μοντέλο γραμμένο από την πρόζα:

  AY        οι καταχωρητές 0-13 (ο AY κρατά 5 bits στους R6 και R8-R10, 4 στους
            R1/R3/R5 — η ένταση πάει με το bit 7 του θορύβου μέσα)
  κανάλια   κάθε εγγραφή του sn_st: wait (τα frames που μένουν στο βήμα, 0 =
            σιωπή), δείκτης στο επόμενο βήμα, το byte FX του εφέ
  μίκτης    sn_mix = R7, και τα bits 6-7 μηδέν (το πληκτρολόγιο)
  μνήμη     τίποτε άλλο σε καμία τράπεζα, εκτός από τη στοίβα
  καταχωρ.  το snd_ping κρατά BC, DE, HL· το snd_play κρατά το BC

Και τα ίδια τα εφέ: ο πίνακας του §9.5 (κανάλι, προτεραιότητα) και τα βήματα
όπως ακούγονται από το βήμα 2 — διαβασμένα από τη μνήμη με τη μορφή της
κεφαλίδας του sound.asm, όχι με τον κώδικα.

ΓΙΑΤΙ. Στο βήμα 75 ο παίκτης ξαναγράφτηκε και η μορφή των εφέ άλλαξε (βήματα
θορύβου τριών bytes, πίνακας αποστάσεων, ένα byte FX). Από 34 σκόπιμα λάθη,
τα 7 πέρασαν από τα test_sound, loop, fit και meteor — ένα snd_off που αφήνει
τον R10 ή ένα byte της εγγραφής, ένα ping που χαλάει το DE, ένας δείκτης που
δεν παίρνει το high byte του, η προτεραιότητα του πλοίου 5, και δύο που αφήνουν
το πλοίο να κόψει τον συναγερμό (αυτά τα δύο τα πιάνει τώρα και το test_sound).
Αυτό εδώ πιάνει και τα 34.

Και ο ΧΡΟΝΟΣ, ανά ρουτίνα, στο χειρότερο που συνάντησε (μαζί με ένα tick όπου
και τα τρία κανάλια φορτώνουν βήμα, και ένα όπου και τα τρία τελειώνουν): όχι
πιο αργό από όσο μετρήθηκε στο βήμα 75. Με το sound.asm του βήματος 74
αποτυγχάνει παντού.

Αρνητικά, με τον κώδικα πειραγμένο στη μνήμη: ο μίκτης με το D αντί για το E,
το «γράψε» του PSG χωρίς strobe, το πρώτο βήμα ένα frame αργότερα, ένα ping
που χαλάει το DE, μια περίοδος του συναγερμού αλλαγμένη.
"""
import ctypes, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import cpc                                               # noqa: E402

PROBE, OUT = 0x3E80, 0x3EF0
SND_CH, SND_REC = 3, 4
FX = ["MOVE", "MENU", "DENY", "BUILD", "DONE", "SHIP", "ALERT", "DEATH", "METEOR"]
SFX = {n: k for k, n in enumerate(FX)}
# §9.5: (κανάλι, προτεραιότητα, [(frames, ένταση, περίοδος, θόρυβος)])
SOUND = [
    (2, 1, [(1, 6, 120, 0)]),
    (2, 2, [(2, 9, 95, 0), (2, 8, 60, 0)]),
    (2, 4, [(3, 10, 22, 1), (4, 6, 28, 1)]),
    (1, 3, [(3, 10, 142, 0), (3, 10, 120, 0), (4, 9, 95, 0)]),
    (1, 5, [(4, 11, 120, 0), (4, 11, 95, 0), (4, 11, 80, 0), (8, 10, 60, 0)]),
    (0, 6, [(8, 12, 8, 1), (8, 11, 12, 1), (8, 9, 17, 1), (8, 6, 23, 1)]),
    (0, 8, [(6, 11, 284, 0), (6, 11, 240, 0), (6, 11, 284, 0), (6, 11, 240, 0)]),
    (0, 9, [(6, 11, 284, 0), (6, 10, 340, 0), (6, 10, 400, 0), (10, 8, 481, 0)]),
    (0, 7, [(2, 15, 31, 1), (4, 12, 31, 1), (6, 8, 31, 1), (8, 4, 31, 1)]),
]
# µs ανά κλήση, μαζί με τη σκαλωσιά του probe· βήμα 75, και στο 74
CEIL = {
    "silent": 113,      # snd_tick, σιωπή                              124
    "tick": 1034,       # snd_tick, το χειρότερο                       1456
    "load3": 974,       # snd_tick, τρία κανάλια φορτώνουν βήμα        1386
    "end3": 638,        # snd_tick, τρία κανάλια τελειώνουν             907
    "SND_PLAY": 104,    #                                               126
    "SND_PING": 126,    #                                               155
    "SND_OFF": 416,     #                                               445
    "SND_INIT": 416,    #                                               553
}
AYMASK = [0xFF, 0x0F, 0xFF, 0x0F, 0xFF, 0x0F, 0x1F, 0xFF, 0x1F, 0x1F, 0x1F,
          0xFF, 0xFF, 0x0F]


def decode(peek, sym, k):
    """Το εφέ k, με τη μορφή της κεφαλίδας: (κανάλι, προτ., βήματα, addr)."""
    tab = sym["SN_TAB"]
    e = tab + k + peek(tab + k)
    h = peek(e)
    a, out = e + 1, []
    while peek(a):
        v = peek(a)
        if v & 0x80:
            out.append((peek(a + 2), v & 0x7F, peek(a + 1), 1))
            a += 3
        else:
            out.append((peek(a + 3), v, peek(a + 1) | (peek(a + 2) << 8), 0))
            a += 4
    return (h >> 2) & 3, h >> 4, out, e, h


class Model:
    """Ο παίκτης όπως τον περιγράφουν το §9.5 και η κεφαλίδα του sound.asm."""

    def __init__(self, peek, sym, regs):
        self.peek, self.sym = peek, sym
        self.reg = list(regs)
        self.rec = [[0, 0, 0] for _ in range(SND_CH)]   # wait, δείκτης, FX
        self.mix = 0x3F

    def off(self):
        self.rec = [[0, 0, 0] for _ in range(SND_CH)]
        self.mix = self.reg[7] = 0x3F
        self.reg[8:11] = [0, 0, 0]

    def play(self, k):
        ch, _, _, e, h = decode(self.peek, self.sym, k)
        if h >= self.rec[ch][2]:
            self.rec[ch] = [1, e + 1, h]

    def tick(self):
        pk = self.peek
        for c in range(SND_CH):
            r = self.rec[c]
            if r[0] == 0:
                continue
            r[0] -= 1
            if r[0]:
                continue
            p, v = r[1], pk(r[1])
            both = 9 << c
            if v == 0:                                   # τέλος
                self.reg[8 + c] = 0
                self.mix |= both
                self.rec[c] = [0, 0, 0]
            else:
                self.reg[8 + c] = v & 0x1F
                if v & 0x80:
                    self.reg[6] = pk(p + 1) & 0x1F
                    r[0], r[1] = pk(p + 2), p + 3
                    self.mix = (self.mix | both) & ~(8 << c)
                else:
                    self.reg[2 * c] = pk(p + 1)
                    self.reg[2 * c + 1] = pk(p + 2) & 0x0F
                    r[0], r[1] = pk(p + 3), p + 4
                    self.mix = (self.mix | both) & ~(1 << c)
            self.reg[7] = self.mix


class Rig:
    def __init__(self, sym, patch=()):
        self.sym = sym
        m = self.m = cpc.CPC()
        m.run_frames(60)
        assert m.quickload(TG.COLONY, start=False), "quickload απέτυχε"
        m.run_frames(400)
        for at, v in patch:
            m.poke(at, v)
        self.ptr = [cpc._lib.cpcemu_ram_ptr(m._h, n) for n in range(8)]
        self.keep = [self.bank(n) for n in range(8)]
        self.st = sym["SN_ST"]
        self.mixa = sym["SN_MIX"]

    def bank(self, n):
        return ctypes.string_at(self.ptr[n], 0x4000)

    def restore(self):
        for n in range(8):
            ctypes.memmove(self.ptr[n], self.keep[n], 0x4000)

    def call(self, name, a=0, bc=0, de=0, hl=0):
        m, ad = self.m, self.sym[name]
        code = [0xF3, 0x31, 0x00, 0x01, 0x01, 0xC0, 0x7F, 0xED, 0x49,
                0x01, bc & 255, bc >> 8, 0x11, de & 255, de >> 8,
                0x21, hl & 255, hl >> 8, 0x3E, a,
                0xCD, ad & 255, ad >> 8,
                0xED, 0x43, OUT & 255, OUT >> 8,
                0xED, 0x53, (OUT + 2) & 255, OUT >> 8,
                0x22, (OUT + 4) & 255, OUT >> 8,
                0x18, 0xFE]
        m.write_ram(PROBE, bytes(code))
        before = [self.bank(n) for n in range(8)]
        m.set_pc(PROBE)
        end, t = PROBE + len(code) - 2, 0
        while not (end <= m.pc <= end + 2):
            m.run_us(1)
            t += 1
            if t > 20_000:
                return t, f"{name} δεν γύρισε (PC=#{m.pc:04X})", None
        w = lambda x: m.peek(x) | (m.peek(x + 1) << 8)
        # τίποτε άλλο στη μνήμη
        mine = set(range(self.st, self.st + SND_CH * SND_REC)) | {self.mixa}
        for n in range(8):
            now = self.bank(n)
            if now == before[n]:
                continue
            for off in range(0x4000):
                if now[off] != before[n][off]:
                    if n == 0 and (0x00A0 <= off < 0x0100 or PROBE <= off < 0x3F00):
                        continue
                    if n == 2 and off + 0x8000 in mine:
                        continue
                    return t, f"{name} έγραψε τράπεζα {n} #{off:04X}", None
        return t, None, (w(OUT), w(OUT + 2), w(OUT + 4))

    def state(self):
        m = self.m
        rec = []
        for c in range(SND_CH):
            r = self.st + SND_REC * c
            rec.append([m.peek(r), m.peek(r + 1) | (m.peek(r + 2) << 8), m.peek(r + 3)])
        return rec, m.peek(self.mixa), m.psg_regs()[:14]


def data_rules(peek, sym):
    for k, (ch, pri, steps) in enumerate(SOUND):
        c, p, got, _, _ = decode(peek, sym, k)
        if (c, p) != (ch, pri):
            return f"{FX[k]}: κανάλι/προτεραιότητα {c}/{p}, το §9.5 λέει {ch}/{pri}"
        if got != steps:
            return f"{FX[k]}: βήματα {got}, έπρεπε {steps}"
    return None


def run(sym, patch=(), n=12, ops=110, times=None):
    """Η πρώτη διαφορά από το μοντέλο, ή None. Οι χρόνοι στο times."""
    R = Rig(sym, patch)
    m = R.m
    why = data_rules(m.peek, sym)
    if why:
        return why
    rnd = random.Random(75)

    def step(M, name, k=0, label=None):
        bc, de, hl = (rnd.randrange(65536) for _ in range(3))
        t, why, regs = R.call(name, k, bc, de, hl)
        if why:
            return why
        if name == "SND_TICK":
            silent = all(r[0] == 0 for r in M.rec)
            M.tick()
        elif name in ("SND_PLAY", "SND_PING"):
            M.play(k)
        else:
            M.off()
        if times is not None:
            key = label or ("silent" if name == "SND_TICK" and silent else
                            "tick" if name == "SND_TICK" else name)
            times[key] = max(times.get(key, 0), t)
            if key in ("silent", "load3", "end3"):
                times["tick"] = max(times.get("tick", 0), t)
        rec, mix, ay = R.state()
        if name == "SND_PING" and regs != (bc, de, hl):
            return f"το snd_ping χάλασε BC/DE/HL: {(bc, de, hl)} -> {regs}"
        if name == "SND_PLAY" and regs[0] != bc:
            return f"το snd_play χάλασε το BC: #{bc:04X} -> #{regs[0]:04X}"
        if rec != M.rec:
            return f"{name}({k}): κανάλια {rec}, το μοντέλο {M.rec}"
        if mix != M.mix or mix & 0xC0:
            return f"{name}({k}): sn_mix #{mix:02X}, το μοντέλο #{M.mix:02X}"
        want = [v & AYMASK[i] for i, v in enumerate(M.reg[:14])]
        if ay != want:
            bad = [i for i in range(14) if ay[i] != want[i]]
            return f"{name}({k}): AY R{bad[0]} = {ay[bad[0]]}, το μοντέλο {want[bad[0]]}"
        return None

    def fresh():
        R.restore()
        t, why, _ = R.call("SND_INIT")
        if why:
            return None, why
        M = Model(m.peek, sym, m.psg_regs()[:16])
        M.off()
        rec, mix, ay = R.state()
        if rec != M.rec or mix != 0x3F or ay[7:11] != [0x3F, 0, 0, 0]:
            return None, f"το snd_init δεν σώπασε: {rec}, #{mix:02X}, {ay[7:11]}"
        if times is not None:
            times["SND_INIT"] = max(times.get("SND_INIT", 0), t)
        return M, None

    # τρία κανάλια φορτώνουν βήμα στο ίδιο tick: θόρυβος, τόνος, τόνος
    M, why = fresh()
    if why:
        return why
    for k in ("SHIP", "BUILD", "MENU"):
        why = step(M, "SND_PLAY", SFX[k])
        if why:
            return why
    why = step(M, "SND_TICK", label="load3")
    if why:
        return why
    # και τρία τελειώνουν: ο μετεωρίτης και το «τελείωσε» στο tick 21, ο
    # κέρσορας παιγμένος μετά το 19
    M, why = fresh()
    if why:
        return why
    for k in ("METEOR", "DONE"):
        why = step(M, "SND_PLAY", SFX[k])
        if why:
            return why
    for i in range(21):
        if i == 19:
            why = step(M, "SND_PLAY", SFX["MOVE"])
            if why:
                return why
        why = step(M, "SND_TICK", label="end3" if i == 20 else None)
        if why:
            return why
    if any(r != [0, 0, 0] for r in M.rec):
        return f"η σκαλωσιά του end3 δεν τελείωσε και τα τρία: {M.rec}"

    for case in range(n):
        M, why = fresh()
        if why:
            return why
        for _ in range(ops):
            x = rnd.random()
            if x < 0.62:
                why = step(M, "SND_TICK")
            elif x < 0.90:
                why = step(M, "SND_PLAY", rnd.randrange(9))
            elif x < 0.96:
                why = step(M, "SND_PING", rnd.randrange(9))
            elif x < 0.98:
                why = step(M, "SND_OFF")
            else:
                why = step(M, "SND_INIT")
            if why:
                return f"περίπτωση {case}: {why}"
    return None


def main():
    sym, _ = TG.build()
    fails = 0
    times = {}
    why = run(sym, times=times)
    if why:
        print(f"ΑΠΟΤΥΧΙΑ: {why}")
        fails += 1
    else:
        print("OK τα εννέα εφέ = το §9.5, και 12 x 110 κλήσεις = το μοντέλο: AY, κανάλια, "
              "μίκτης, μνήμη, καταχωρητές")
    for k, c in CEIL.items():
        t = times.get(k, 0)
        if t > c:
            print(f"ΑΠΟΤΥΧΙΑ: {k} {t} us > {c} (βήμα 75)")
            fails += 1
        else:
            print(f"OK {k:8s} {t:4d} us <= {c}")

    m = cpc.CPC()
    m.run_frames(60)
    assert m.quickload(TG.COLONY, start=False)

    def find(at, pat, span=400):
        i = m.read_ram(sym[at], span).find(bytes(pat))
        assert i >= 0, f"δεν βρέθηκε το {pat}"
        return sym[at] + i

    ping = sym["SND_PING"]
    _, _, steps, e, _ = decode(m.peek, sym, SFX["ALERT"])
    neg = [("τον μίκτη με το D", [(find("SND_TICK", [0xAE, 0xA3, 0xAE]) + 1, 0xA2)]),
           ("το «γράψε» χωρίς strobe", [(find("SND_REG", [0x01, 0x80, 0xF6]) + 1, 0x00)]),
           ("το πρώτο βήμα ένα frame αργότερα", [(find("SND_PLAY", [0x36, 0x01, 0xC9]) + 1, 2)]),
           ("ένα ping που χαλάει το DE", [(ping, 0), (find("SND_PING", [0xE1, 0xD1, 0xC9]) + 1, 0)]),
           ("μια περίοδο του συναγερμού αλλαγμένη", [(e + 2, 29)])]
    for label, patch in neg:
        why = run(sym, patch, n=3, ops=80)
        if why:
            print(f"OK ΑΡΝΗΤΙΚΟ: με {label} αποτυγχάνει ({why[:90]})")
        else:
            print(f"ΑΠΟΤΥΧΙΑ ΑΡΝΗΤΙΚΟΥ: με {label} περνά")
            fails += 1
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
