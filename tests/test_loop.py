#!/usr/bin/env python3
"""Ο βρόχος του main.asm, γύρο προς γύρο, απέναντι στον κανόνα (§7.1, §9.1).

  Ενας γύρος καλεί, με αυτή τη σειρά:
    wheel_tick              ui_spd φορές (0 = παύση)
    snd_play(SFX_METEOR)    αν mt_boom, που γίνεται 0
    dirty_reset, ui_hide, view_draw, ui_show     αν dirty_over (και το ui_panel,
                            όπου τελειώνει το ui_show στο LOOK)
    ml_alert, [snd_play(SFX_ALERT)], hud_draw, ui_panel
                            όταν το ρολόι του HUD φτάσει 0: μετρά 16 γύρους
                            ΕΚΤΟΣ παύσης, και ξεκινά από 1
    snd_tick, dirty_tick, ui_tick

  Το ml_alert: τρεις κλήσεις αναμονής, και μετά A = EC_O2OK αν EC_POK != 0,
  αλλιώς 0· ο συναγερμός ηχεί μόνο στο 1 -> 0, και το ml_alarm κρατά το A.

ΠΩΣ. Στην είσοδο κάθε ρουτίνας μπαίνει ένα stub που γράφει (ρουτίνα, A, EC_POK,
EC_O2OK) σε ημερολόγιο — μόνο όταν η διεύθυνση επιστροφής είναι ο ίδιος ο
βρόχος, ώστε οι κλήσεις του ui_tick ή του view_draw να μη μετρούν. Το `jp
main_loop` πηγαίνει σε hook που περιμένει: ανάμεσα σε δύο γύρους η δοκιμή
διαβάζει το ημερολόγιο και βάζει τις εισόδους του επόμενου. Ταχύτητες x1, x2,
x4 και παύση· μετεωρίτης, ξεχείλισμα και ρεύμα που πέφτει και επανέρχεται, σε
όλες. Ο τροχός δεν ρίχνει δικούς του μετεωρίτες (EC_METEOR = 0).

ΓΙΑΤΙ. Ως το βήμα 71 τον βρόχο τον έβλεπαν μόνο ολόκληρες δοκιμές παιχνιδιού,
και το test_sound καλεί το ml_alert μόνο του. Από 18 σκόπιμα λάθη του βήματος
71, το test_sound και το test_game έπιασαν τα 4: όχι ένα ρολόι HUD 15 αντί 16,
ούτε ένα mt_boom που δεν σβήνει στην παύση, ούτε έναν συναγερμό και στο 0 -> 1,
ούτε μία κλήση αναμονής λιγότερη. Και ο ΧΡΟΝΟΣ: σε δεύτερο πέρασμα, χωρίς stubs,
ο χρόνος μέσα στον ίδιο τον κώδικα του βρόχου (όχι στις ρουτίνες που καλεί, ούτε
στην αναμονή του vsync) ανά είδος γύρου, όχι πιο αργός από όσο μετρήθηκε στο
βήμα 71. Με το main.asm του βήματος 70 αποτυγχάνουν όλα.

Και η αρχή: το wh_hook δείχνει στο dirty_push από τη μεταγλώττιση, και το
περίγραμμα είναι μαύρο (το pal_border του start· το βήμα 71 το βρήκε χωρίς
καμία δοκιμή).

Αρνητικά, με το snapshot πειραγμένο: ρολόι 15, ret z αντί ret nc στον
συναγερμό, το mt_boom που δεν σβήνει, χωρίς το ui_show μετά την πλήρη σχεδίαση,
δύο κλήσεις αναμονής αντί τριών, και άλλο περίγραμμα.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import cpc                                               # noqa: E402

# Ο ελεύθερος χώρος της τράπεζας 0 κάτω από τη σκαλωσιά (#3EC0): stubs και
# ημερολόγιο. Ο κώδικας του παιχνιδιού τελειώνει πριν από το STUBS (assert).
# Ενα #100 πιο πάνω από το βήμα 84, όταν τα κουμπιά έφεραν την τράπεζα 0 στο
# #3B08· το ημερολόγιο τελειώνει ακόμη κάτω από τη σκαλωσιά του #3EC0.
STUBS, LOG, LOG_TOP = 0x3C00, 0x3D00, 0x3E00
HOOK, GO, PTR, CNT = 0x3EC0, 0x3EF0, 0x3EF2, 0x3EF4
SFX_ALERT, SFX_METEOR = 6, 8                             # src/sound.asm
TARGETS = ["WHEEL_TICK", "SND_PLAY", "DIRTY_RESET", "UI_HIDE", "VIEW_DRAW", "UI_SHOW",
           "ML_ALERT", "HUD_DRAW", "UI_PANEL", "SND_TICK", "DIRTY_TICK", "UI_TICK"]
# µs μέσα στον κώδικα του βρόχου, ανά είδος γύρου, ο χειρότερος (βήμα 71· στο
# βήμα 70: 81, 97, 129, 56, 183, 91, 101 και 38.177). «HUD» είναι γύρος του
# ρολογιού σε οποιαδήποτε ταχύτητα, «όλοι» το άθροισμα των 399.
CEIL = {"x1": 73, "x2": 89, "x4": 121, "παύση": 51, "HUD": 167,
        "μετεωρίτης": 81, "ξεχείλισμα": 92, "όλοι": 34871}


def ilen(code, i):
    """Μήκος της εντολής στο code[i] — μόνο ό,τι μετακινείται αυτούσιο."""
    op = code[i]
    if op in (0x10, 0x18, 0x20, 0x28, 0x30, 0x38) or op in (0xDD, 0xED, 0xFD, 0x76):
        return None
    if op == 0xCB or op & 0xC7 == 0x06 or op & 0xC7 == 0xC6:
        return 2
    if op & 0xCF == 0x01 or op in (0x22, 0x2A, 0x32, 0x3A) or op & 0xC7 in (0xC2, 0xC4) \
            or op in (0xC3, 0xCD):
        return 3
    return 1


def labels():
    lab = {}
    for line in open(os.path.join(ROOT, "src", "rasmoutput.sym"), encoding="utf-8", errors="replace"):
        p = line.split()
        if len(p) >= 4 and p[1].startswith("#") and p[3] == "L":
            lab[p[0].upper()] = int(p[1][1:], 16)
    return lab


class Loop:
    def __init__(self, sym, g, patch=(), log=True):
        self.sym, self.g = sym, g
        lab = labels()
        own = [a for n, a in lab.items() if n.startswith(("ML_", "MLA_", "MLW_"))]
        self.own_end = min(a for a in lab.values() if a > max(own))
        assert sym["ZZ_BANK0_END"] <= STUBS, "ο κώδικας έφτασε στα stubs της δοκιμής"
        # Ο εξομοιωτής δείχνει PC = X - 1 στο πρώτο µs μιας εντολής στο X: χωρίς
        # το - 1, το scr_nextline που ακολουθεί μετρούσε ως βρόχος (838 µs σε μια
        # πλήρη σχεδίαση).
        self.own = [(sym["ML_HIGH"] + 5, lab["ACT_SRC"]), (sym["ML_HUDW"], self.own_end - 1)]
        m = self.m = cpc.CPC()
        m.run_frames(60)
        assert m.quickload(TG.SNA, start=False), "quickload απέτυχε"
        self.hook0 = m.peek(sym["WH_HOOK"]) | m.peek(sym["WH_HOOK"] + 1) << 8
        for at, v in patch:
            m.poke(at, v)
        top, ut = sym["MAIN_LOOP"], sym["UI_TICK"]
        k = next(k for k in range(256) if list(m.read_ram(top + k, 6)) ==
                 [0xCD, ut & 255, ut >> 8, 0xC3, top & 255, top >> 8])
        # Ο γύρος μετριέται με μετρητή, ΟΧΙ με το PC: στο πρώτο µs του ld a,(GO)
        # ο εξομοιωτής δείχνει HOOK - 1, και ένα «βγήκε από το hook» βγαίνει
        # αληθές ενώ ο Z80 περιμένει ακόμη — ένας γύρος μετρούσε μηδέν και το
        # επόμενο είδος γύρου έπαιρνε λάθος όνομα.
        m.write_ram(HOOK, bytes([0x21, CNT & 255, CNT >> 8, 0x34,               # ld hl,CNT · inc (hl)
                                 0x3A, GO & 255, GO >> 8, 0xB7, 0x28, 0xFA,     # ld a,(GO) · or a · jr z
                                 0xAF, 0x32, GO & 255, GO >> 8,                  # xor a · ld (GO),a
                                 0xC3, top & 255, top >> 8]))                    # jp main_loop
        m.poke(GO, 0)
        m.poke(CNT, 0)
        m.write_ram(top + k + 4, bytes([HOOK & 255, HOOK >> 8]))
        if log:
            self.stubs()

    def stubs(self):
        m, sym = self.m, self.sym
        w = lambda v: [v & 255, (v >> 8) & 255]
        pok, o2 = self.g + 46, self.g + 47
        rec = ([0xE5, 0xD5, 0xC5, 0x4F,                         # push hl,de,bc · ld c,a
                0x21, 10, 0, 0x39, 0x5E, 0x23, 0x56]            # DE = η επιστροφή του καλούντα
               + [0x21] + w(-self.own_end) + [0x19, 0x38, "out"]        # >= own_end: έξω
               + [0x21] + w(-sym["MAIN_LOOP"]) + [0x19, 0x30, "out"]    # < main_loop: έξω
               + [0x21, 9, 0, 0x39, 0x46,                       # B = το A του καλούντα
                  0x2A] + w(PTR) + [0x7C, 0xFE, LOG_TOP >> 8, 0x30, "out",
                  0x71, 0x23, 0x70, 0x23, 0x73, 0x23, 0x72, 0x23,         # id, A, επιστροφή
                  0x3A] + w(pok) + [0x77, 0x23, 0x3A] + w(o2) + [0x77, 0x23,
                  0x22] + w(PTR)
               + [0xC1, 0xD1, 0xE1, 0xC9])                      # out: pop bc,de,hl · ret
        out = len(rec) - 4
        rec = [out - (j + 1) if v == "out" else v for j, v in enumerate(rec)]
        code = list(rec)
        for n, name in enumerate(TARGETS):
            t = sym[name]
            head = m.read_ram(t, 8)
            k = 0
            while k < 3:
                ln = ilen(head, k)
                assert ln, f"{name}: η πρώτη εντολή δεν μετακινείται (#{head[k]:02X})"
                k += ln
            m.write_ram(t, bytes([0xC3] + w(STUBS + len(code))))
            code += [0xF5, 0x3E, n, 0xCD] + w(STUBS) + [0xF1] + list(head[:k]) + [0xC3] + w(t + k)
        assert STUBS + len(code) <= LOG, "τα stubs δεν χωρούν"
        m.write_ram(STUBS, bytes(code))
        self.reset_log()

    def reset_log(self):
        self.m.write_ram(PTR, bytes([LOG & 255, LOG >> 8]))

    def read_log(self):
        m = self.m
        end = m.peek(PTR) | m.peek(PTR + 1) << 8
        raw = m.read_ram(LOG, end - LOG)
        recs = [raw[i:i + 6] for i in range(0, len(raw), 6)]
        self.full = end >= LOG_TOP
        return [(TARGETS[r[0]], r[1], r[4], r[5]) for r in recs]

    def go(self, timing=False):
        """Ενας γύρος. Γυρίζει µs μέσα στον κώδικα του βρόχου (με timing)."""
        m, own, t = self.m, self.own, 0
        c = m.peek(CNT)
        m.poke(GO, 1)
        us = 0
        while m.peek(CNT) == c:
            if timing:
                pc = m.pc
                if own[0][0] <= pc < own[0][1] or own[1][0] <= pc < own[1][1]:
                    t += 1
                m.run_us(1)
                us += 1
            else:
                m.run_us(50)
                us += 50
            # ο μακρύτερος γύρος είναι μια πλήρης σχεδίαση, ~2 s
            assert us < 5_000_000, f"ο γύρος δεν έκλεισε σε 5 s (pc #{m.pc:04X})"
        return t

    def first(self):
        """Ως το πρώτο hook: start, game_new, πρώτος γύρος."""
        n = 0
        while not self.m.peek(CNT):
            self.m.run_us(100)
            n += 1
            assert n < 100_000, "το start δεν έφτασε στον βρόχο"


def scenario(i):
    """Οι είσοδοι πριν από τον γύρο i: (ui_spd ή None, boom, over, (POK, O2OK) ή None)."""
    # Η δεύτερη παύση πιάνει το ρολόι του HUD στο 1 (χτύπησε στο 336): το
    # επόμενο χτύπημα είναι στο 360, όχι στο 352.
    spd = {130: 2, 175: 4, 230: 0, 262: 4, 300: 1, 352: 0, 360: 2, 380: 1}.get(i)
    boom = i in (70, 145, 190, 235, 250, 305, 355)
    over = i in (90, 160, 205, 240, 320, 357)
    # το ρεύμα πριν από γύρους του ρολογιού: ναι, όχι, ESS με O2, χωρίς O2, ...
    # Ο γύρος 32 είναι η τρίτη αναμονή: ρεύμα ΝΑΙ εκεί, ώστε μια αναμονή μία
    # κλήση κοντύτερη να σηκώσει το ml_alarm νωρίς, και μία μακρύτερη να μην
    # το σηκώσει στο 48.
    power = {32: (1, 1), 48: (1, 1), 64: (0, 1), 80: (2, 1), 96: (2, 0), 112: (1, 1), 128: (1, 1),
             140: (0, 0), 150: (1, 1), 178: (2, 0), 190: (2, 1), 210: (0, 1)}.get(i)
    return spd, boom, over, power


def run(sym, g, patch=(), timing=False, n=400):
    """Οι κανόνες (ή ο χρόνος) σε n γύρους. Η πρώτη διαφορά, ή None· με timing
    ένα dict είδος -> µs."""
    if timing:
        # Ο ΧΡΟΝΟΣ ΜΕΤΡΙΕΤΑΙ ΧΩΡΙΣ ΔΙΑΚΟΠΕΣ (βήμα 83). Μια διακοπή που πέφτει
        # ενώ ο Z80 είναι στον κώδικα του βρόχου χρεώνει σε αυτόν την αποδοχή
        # της (5 µs), και ο x1 έβγαινε 78 με τον ίδιο κώδικα. Το ei του βρόχου
        # γίνεται nop· το κόστος της διακοπής το μετρά το test_split.
        patch = list(patch) + [(sym["MAIN_LOOP"], 0x00)]
    L = Loop(sym, g, patch, log=not timing)
    m = L.m
    if timing:
        assert L.m.read_ram(sym["MAIN_LOOP"], 1) == b"\x00"
    if L.hook0 != sym["DIRTY_PUSH"]:
        return f"το wh_hook στο snapshot είναι #{L.hook0:04X}, όχι το dirty_push"
    L.first()
    if not timing:
        # το start: περίγραμμα στο firmware 0, μαύρο — οι τέσσερις γωνίες
        im = m.image()
        px = [im.getpixel((x, y)) for x in (2, im.width - 3) for y in (2, im.height - 3)]
        if max(max(p) for p in px) > 16:
            return f"το περίγραμμα μετά το start δεν είναι μαύρο: {px}"
    spd_a, boom_a, over_a = sym["UI_SPD"], sym["MT_BOOM"], sym["DIRTY_OVER"]
    hudw, warm, alarm = 16, 2, 0          # ο γύρος 0 ζωγράφισε HUD: μία αναμονή
    seen = {"alert": 0, "rise": 0, "hud": 0, "boom": 0, "over": 0, "pause_hud_skip": 0}
    times = {}
    for i in range(1, n):
        s, boom, over, power = scenario(i)
        if s is not None:
            m.poke(spd_a, s)
        if boom:
            m.poke(boom_a, 1)
        if over:
            m.poke(over_a, 1)
        if power:
            m.poke(g + 46, power[0])
            m.poke(g + 47, power[1])
        m.poke(g + 86, 0)                 # EC_METEOR: ο τροχός δεν ρίχνει μόνος
        spd = m.peek(spd_a)
        boom, over = m.peek(boom_a), m.peek(over_a)
        if not timing:
            L.reset_log()
        t = L.go(timing)
        want = ["WHEEL_TICK"] * spd
        if boom:
            want.append(("SND_PLAY", SFX_METEOR))
            seen["boom"] += 1
        if over:
            # το ui_show στο LOOK τελειώνει με jp ui_panel: η επιστροφή του είναι
            # του βρόχου, και το stub το βλέπει ως κλήση του
            want += ["DIRTY_RESET", "UI_HIDE", "VIEW_DRAW", "UI_SHOW", "UI_PANEL"]
            seen["over"] += 1
        hud = False
        if spd:
            hudw -= 1
            if hudw == 0:
                hudw, hud = 16, True
        elif hudw == 1:
            seen["pause_hud_skip"] += 1
        if timing:
            kind = ("μετεωρίτης" if boom else "ξεχείλισμα" if over else "HUD" if hud
                    else {0: "παύση", 1: "x1", 2: "x2", 4: "x4"}[spd])
            if not ((boom or over) and (hud or spd != 1)):
                times[kind] = max(times.get(kind, 0), t)
            times["όλοι"] = times.get("όλοι", 0) + t
            continue
        got = L.read_log()
        if L.full:
            return f"γύρος {i}: το ημερολόγιο γέμισε"
        if hud:
            seen["hud"] += 1
            want.append("ML_ALERT")
            at = next((r for r in got if r[0] == "ML_ALERT"), None)
            if warm:
                warm -= 1
            elif at:
                a = at[3] if at[2] else 0
                if a < alarm:
                    want.append(("SND_PLAY", SFX_ALERT))
                    seen["alert"] += 1
                elif a > alarm:
                    seen["rise"] += 1
                alarm = a
            want += ["HUD_DRAW", "UI_PANEL"]
        want += ["SND_TICK", "DIRTY_TICK", "UI_TICK"]
        have = [(r[0], r[1]) if r[0] == "SND_PLAY" else r[0] for r in got]
        if have != want:
            return f"γύρος {i} (ταχύτητα {spd}): κλήσεις {have}, ο κανόνας λέει {want}"
        if m.peek(boom_a):
            return f"γύρος {i}: το mt_boom έμεινε {m.peek(boom_a)}"
        if m.peek(sym["ML_HUDW"]) != hudw:
            return f"γύρος {i}: ml_hudw = {m.peek(sym['ML_HUDW'])}, ο κανόνας λέει {hudw}"
        if m.peek(sym["ML_ALARM"]) != alarm:
            return f"γύρος {i}: ml_alarm = {m.peek(sym['ML_ALARM'])}, ο κανόνας λέει {alarm}"
    if timing:
        return times
    if not (seen["alert"] >= 2 and seen["rise"] >= 2 and seen["hud"] >= 15 and seen["boom"] >= 5
            and seen["over"] >= 5 and seen["pause_hud_skip"] >= 1):
        return f"το σενάριο δεν έπιασε ό,τι έπρεπε: {seen}"
    print(f"    σενάριο: {seen}")
    return None


def main():
    sym, g = TG.build()
    fails = 0
    why = run(sym, g)
    if why:
        print(f"ΑΠΟΤΥΧΙΑ: {why}")
        fails += 1
    else:
        print("OK 399 γύροι = ο κανόνας: τροχός ανά ταχύτητα, μετεωρίτης, ξεχείλισμα, "
              "ρολόι HUD που σταματά στην παύση, συναγερμός μόνο στο 1 -> 0")
        print("OK το wh_hook δείχνει στο dirty_push από τη μεταγλώττιση, το περίγραμμα είναι μαύρο")
    times = run(sym, g, timing=True)
    print("    µs στον κώδικα του βρόχου: " + ", ".join(f"{k} {v}" for k, v in times.items()))
    slow = [f"{k} {times.get(k)} > {c}" for k, c in CEIL.items() if times.get(k, 10 ** 9) > c]
    if slow:
        print("ΑΠΟΤΥΧΙΑ: πιο αργός από το βήμα 71: " + ", ".join(slow))
        fails += 1
    else:
        print("OK κανένα είδος γύρου πιο αργό από το βήμα 71")

    # --- αρνητικά ---
    m = cpc.CPC()
    m.run_frames(60)
    assert m.quickload(TG.SNA, start=False)
    top, al = sym["MAIN_LOOP"], sym["ML_ALERT"]
    loop = m.read_ram(top, sym["ML_NOHUD"] - top)
    i16 = loop.find(bytes([0x36, 16]))                          # ld (hl),16
    ib = loop.find(bytes([0x70, 0x3E, SFX_METEOR]))             # ld (hl),b · ld a,SFX_METEOR
    show = sym["UI_SHOW"]
    ish = loop.find(bytes([0xCD, show & 255, show >> 8]))
    inc = m.read_ram(al, 32).find(bytes([0xD0, 0x3E, SFX_ALERT]))   # ret nc · ld a,SFX_ALERT
    pb = sym["PAL_BORDER"]
    ixa = m.read_ram(sym["START"], top - sym["START"]).find(bytes([0xAF, 0xCD, pb & 255, pb >> 8]))
    assert min(i16, ib, ish, inc, ixa) >= 0, \
        "δεν βρέθηκαν τα ld (hl),16 / ld (hl),b / call ui_show / ret nc / xor a · call pal_border"
    for label, patch in (("ρολόι 15", [(top + i16 + 1, 15)]),
                         ("ret z αντί ret nc", [(al + inc, 0xC8)]),
                         ("το mt_boom χωρίς σβήσιμο", [(top + ib, 0)]),
                         ("το ui_show σβησμένο", [(top + ish + j, 0) for j in range(3)]),
                         ("δύο κλήσεις αναμονής", [(sym["ML_WARM"], 7)]),
                         ("inc a αντί xor a πριν το pal_border", [(sym["START"] + ixa, 0x3C)])):
        why = run(sym, g, patch)
        if why:
            print(f"OK ΑΡΝΗΤΙΚΟ: με {label} αποτυγχάνει ({why[:90]})")
        else:
            print(f"ΑΠΟΤΥΧΙΑ ΑΡΝΗΤΙΚΟΥ: με {label} περνά")
            fails += 1
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
