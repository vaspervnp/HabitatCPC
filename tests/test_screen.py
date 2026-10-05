#!/usr/bin/env python3
"""Το scr_addr και το scr_nextline του src/screen.asm, εξαντλητικά, απέναντι στον
τύπο του DESIGN §8.2 — στο main.sna, το binary του παιχνιδιού (βλ. test_terrain
για το γιατί όχι σε δοκιμαστικό build).

       p = ((y>>3)*80 + x + cam_p) & #7FF
       D = #C0 + (y&7)*8 + (p>>8)      E = p & #FF

Για επτά cam_p (ανάμεσά τους το 2008, όπου κάθε σειρά τυλίγει) και κάθε (x, y)
της οθόνης, 0..79 x 0..199:

  scr_addr      DE από τον τύπο, A = D, HL = (y>>3)*80 + x + cam_p, BC ίδιο
  scr_nextline  από το DE του (x, y) στο DE του (x, y+1), HL και BC ίδια

ΓΙΑΤΙ. Ως το βήμα 68 το scr_addr το έβλεπαν μόνο σκηνές — tiles, αντικείμενα,
HUD, φάντασμα — και μια σκηνή ρωτά λίγες θέσεις: ένα tile ανά 16 γραμμές, ένα
αντικείμενο ανά θόλο. Από το βήμα 68 δεν έχει πίνακα αλλά πολλαπλασιασμό
(8r -> x4 -> +8r -> x2), και ένα λάθος σε μία από τις τέσσερις προσθέσεις
αλλάζει μόνο κάποιες σειρές χαρακτήρων.

Και ο ΧΡΟΝΟΣ: μία κλήση του scr_addr, και του scr_nextline στα δύο μονοπάτια
του, όχι περισσότερο από όσο μετρήθηκε στο βήμα 68. Με το screen.asm του
βήματος 67 το scr_addr αποτυγχάνει.

Αρνητικά, με το snapshot πειραγμένο: and #F0 αντί #F8 στο 8r, το scr_addr χωρίς
το ld d,0 (το DE μπαίνει με σκουπίδι), και το scr_nextline χωρίς το δαχτυλίδι
(and #FF αντί #C7).
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import cpc                                               # noqa: E402

PROBE, BUF = 0x3E00, 0x3500             # πάνω από τον κώδικα της τράπεζας 0
CAMS = [0, 2, 48, 876, 1920, 2008, 2046]
# µs, με το probe: (scr_addr, scr_nextline ίδια σειρά, scr_nextline νέα σειρά)
CEIL = (63, 21, 32)


def addr(x, y, cam):
    p = ((y >> 3) * 80 + x + cam) & 0x7FF
    return (0xC0 + (y & 7) * 8 + (p >> 8)) << 8 | (p & 0xFF)


def check(sym, patch=(), timing=True):
    """Η πρώτη διαφορά από τον τύπο, ή None."""
    m = cpc.CPC()
    m.run_frames(60)
    assert m.quickload(TG.SNA, start=False), "quickload απέτυχε"
    top = sym["ZZ_BANK0_END"]
    assert top < BUF, f"ο κώδικας φτάνει ως #{top:04X}"
    for at, v in patch:
        m.poke(at, v)
    sa, sn = sym["SCR_ADDR"], sym["SCR_NEXTLINE"]

    def run(code, step):
        code = [0xF3, 0x31, 0x00, 0x01] + code + [0x18, 0xFE]
        m.write_ram(PROBE, bytes(code))
        m.set_pc(PROBE)
        end, t = PROBE + len(code) - 2, 0
        while not (end <= m.pc <= end + 2):
            m.run_us(step)
            t += step
            if t > 100_000:
                return None
        return t

    for cam in CAMS:
        m.poke(sym["CAM_P"], cam & 255)
        m.poke(sym["CAM_P"] + 1, cam >> 8)
        for y in range(200):
            # ld ix,BUF · ld c,0
            # lp: ld de,#A55A · ld a,y · ld b,#A5 · call scr_addr · (ix+0..6) = E D L H A B C
            #     · call scr_nextline · (ix+7..12) = E D L H B C
            #     · ld de,16 · add ix,de · inc c · ld a,c · cp 80 · jr nz,lp
            # DE με σκουπίδι πριν από το scr_addr: το βήμα 68 έδειξε ένα `ld d,0` που
            # έλειπε και που ένα probe με D = 0 δεν βλέπει
            body = [0x11, 0x5A, 0xA5, 0x3E, y, 0x06, 0xA5, 0xCD, sa & 255, sa >> 8,
                    0xDD, 0x73, 0, 0xDD, 0x72, 1, 0xDD, 0x75, 2, 0xDD, 0x74, 3,
                    0xDD, 0x77, 4, 0xDD, 0x70, 5, 0xDD, 0x71, 6,
                    0xCD, sn & 255, sn >> 8,
                    0xDD, 0x73, 7, 0xDD, 0x72, 8, 0xDD, 0x75, 9, 0xDD, 0x74, 10,
                    0xDD, 0x70, 11, 0xDD, 0x71, 12,
                    0x11, 16, 0, 0xDD, 0x19, 0x0C, 0x79, 0xFE, 80]
            code = [0xDD, 0x21, BUF & 255, BUF >> 8, 0x0E, 0] + body + [0x20, (-(len(body) + 2)) & 255]
            if run(code, 50) is None:
                return f"cam_p {cam}, y {y}: δεν γύρισε"
            buf = m.read_ram(BUF, 16 * 80)
            for x in range(80):
                r = buf[16 * x:16 * x + 13]
                de, hl = r[0] | r[1] << 8, r[2] | r[3] << 8
                where = f"cam_p {cam}, ({x},{y})"
                if de != addr(x, y, cam):
                    return f"{where}: scr_addr #{de:04X}, ο τύπος #{addr(x, y, cam):04X}"
                if r[4] != de >> 8 or hl != (y >> 3) * 80 + x + cam or (r[5], r[6]) != (0xA5, x):
                    return f"{where}: scr_addr A #{r[4]:02X} HL #{hl:04X} BC #{r[5]:02X}{r[6]:02X}"
                if y < 199:
                    nde = r[7] | r[8] << 8
                    if nde != addr(x, y + 1, cam):
                        return f"{where}: scr_nextline #{nde:04X}, ο τύπος #{addr(x, y + 1, cam):04X}"
                    if (r[9] | r[10] << 8, r[11], r[12]) != (hl, 0xA5, x):
                        return f"{where}: το scr_nextline άλλαξε HL ή BC"
    if not timing:
        return None
    m.poke(sym["CAM_P"], 2008 & 255)
    m.poke(sym["CAM_P"] + 1, 2008 >> 8)
    got = (run([0x0E, 37, 0x3E, 101, 0xCD, sa & 255, sa >> 8], 1),
           run([0x11, 0x18, 0xD9, 0xCD, sn & 255, sn >> 8], 1),          # γραμμή 3 -> 4
           run([0x11, 0x18, 0xF9, 0xCD, sn & 255, sn >> 8], 1))          # γραμμή 7 -> νέα σειρά
    names = ("scr_addr", "scr_nextline, ίδια σειρά", "scr_nextline, νέα σειρά")
    for n, t, c in zip(names, got, CEIL):
        print(f"    {n}: {t} us (ταβάνι {c})")
    slow = [f"{n} {t} > {c} us" for n, t, c in zip(names, got, CEIL) if t > c]
    return "πιο αργό από το βήμα 68: " + ", ".join(slow) if slow else None


def main():
    sym, _ = TG.build()
    fails = 0
    why = check(sym)
    if why:
        print(f"ΑΠΟΤΥΧΙΑ: {why}")
        fails += 1
    else:
        print(f"OK scr_addr και scr_nextline = ο τύπος του §8.2 σε {len(CAMS)} κάμερες x 80 x 200 "
              f"θέσεις, με A, HL και BC")
        print("OK κανένα πιο αργό από το βήμα 68")

    # --- αρνητικά ---
    sa, sn = sym["SCR_ADDR"], sym["SCR_NEXTLINE"]
    m = cpc.CPC()
    m.run_frames(60)
    assert m.quickload(TG.SNA, start=False)
    code, nl = m.read_ram(sa, 48), m.read_ram(sn, 20)
    assert code[1:3] == bytes([0xE6, 0xF8]), "το scr_addr δεν ξεκινά με ld l,a / and #F8"
    andc7 = nl.find(bytes([0xE6, 0xC7]))
    assert andc7 > 0, "δεν βρέθηκε το and #C7 του scr_nextline"
    assert code[4:6] == bytes([0x16, 0]), "το scr_addr δεν έχει ld d,0 στο +4"
    for label, patch in (("and #F0 αντί #F8", [(sa + 2, 0xF0)]),
                         ("το scr_addr χωρίς ld d,0", [(sa + 4, 0), (sa + 5, 0)]),
                         ("το scr_nextline χωρίς δαχτυλίδι", [(sn + andc7 + 1, 0xFF)])):
        why = check(sym, patch, timing=False)
        if why:
            print(f"OK ΑΡΝΗΤΙΚΟ: με {label} αποτυγχάνει ({why[:70]})")
        else:
            print(f"ΑΠΟΤΥΧΙΑ ΑΡΝΗΤΙΚΟΥ: με {label} περνά")
            fails += 1
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
