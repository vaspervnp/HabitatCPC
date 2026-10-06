#!/usr/bin/env python3
"""Πληκτρολόγιο και χειριστήριο (DESIGN §9.1).

Το πληκτρολόγιο του CPC κρέμεται από τον ήχο και η ακολουθία των θυρών είναι
αυστηρή· ένα βήμα λιγότερο και δεν διαβάζεται τίποτα. Αυτό δεν ελέγχεται
διαβάζοντας — ελέγχεται πατώντας.

ΔΥΟ ΙΣΧΥΡΙΣΜΟΙ:
  1. Κάθε ενέργεια ανάβει από το πλήκτρο της ΚΑΙ μόνο από αυτό.
  2. Το act_hit είναι ακμή: κράτημα δέκα frames μετράει ΜΙΑ φορά. Χωρίς αυτό
     ένα «χτίσε» θα έχτιζε πενήντα θόλους το δευτερόλεπτο.

Ο εξομοιωτής δεν πατά COPY, C ούτε το δεύτερο κουμπί του χειριστηρίου, και
στο βήμα 64 ένα TAB στο λάθος bit πέρασε όλα τα tests (από το βήμα 79 η θέση
του TAB, που δεν τη διάβασε ποτέ τίποτα, είναι το I). Γι' αυτό υπάρχει και ο
έλεγχος της ΛΟΓΙΚΗΣ: το in_scan κόβεται, το key_now γράφεται από εδώ με τη μήτρα
του CPC, και κάθε πλήκτρο και κάθε bit της γραμμής 9 περνά από πάτημα, κράτημα
και άφημα, με in_hit και in_held και για τις 16 ενέργειες.
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, "/home/vasilhs/cpcemu")

RASM = os.path.expanduser("~/rasm/rasm.exe")
SNA = os.path.join(ROOT, "build", "inputtest.sna")

A_UP, A_DOWN, A_LEFT, A_RIGHT, A_FIRE, A_CANCEL, A_MENU, A_INFO, A_HOME, \
    A_SPD1, A_SPD2, A_SPD3, A_SPD4, A_SAVE, A_LOAD = range(15)
NAMES = ["πάνω", "κάτω", "αριστερά", "δεξιά", "FIRE", "ακύρωση", "μενού",
         "πληροφορίες", "κέντρο", "ταχ.1", "ταχ.2", "ταχ.3", "ταχ.4", "σώσε",
         "φόρτωσε"]


def build():
    r = subprocess.run([RASM, "inputtest.asm", "-oi", SNA, "-v2", "-s", "-eo"],
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


# Η ΜΗΤΡΑ ΤΟΥ CPC (γραμμή, bit), από το υλικό και όχι από τον πίνακα του input.asm.
A_SHIP = 15
KEYS = {A_UP: (0, 0), A_DOWN: (0, 2), A_LEFT: (1, 0), A_RIGHT: (0, 1),
        A_FIRE: (1, 1),                                  # COPY
        A_CANCEL: (8, 2), A_MENU: (5, 7), A_INFO: (4, 3), A_HOME: (5, 4),
        A_SPD1: (8, 0), A_SPD2: (8, 1), A_SPD3: (7, 1), A_SPD4: (7, 0),
        A_SAVE: (7, 4), A_LOAD: (4, 4), A_SHIP: (7, 6)}
JOY = [A_UP, A_DOWN, A_LEFT, A_RIGHT, A_FIRE, A_CANCEL, None, None]   # γραμμή 9, bits 0-7
PROBE, BUF = 0x3000, 0x3800


def logic(sym, patch=()):
    """Η πρώτη διαφορά από τη μήτρα, ή None."""
    from cpc import CPC
    m = CPC()
    m.run_frames(60)
    assert m.quickload(SNA, start=False), "quickload απέτυχε"
    ir, sc = sym["IN_READ"], sym["IN_SCAN"]
    assert list(m.read_ram(ir, 3)) == [0xCD, sc & 255, sc >> 8], "το in_read δεν ξεκινά με in_scan"
    m.write_ram(ir, bytes(3))
    for at, v in patch:
        m.poke(at, v)
    w = lambda a: m.peek(a) | (m.peek(a + 1) << 8)
    call = lambda n: [0xCD, sym[n] & 255, sym[n] >> 8]

    def run(code):
        code = [0xF3, 0x31, 0x00, 0x01] + code + [0x18, 0xFE]
        m.write_ram(PROBE, bytes(code))
        m.set_pc(PROBE)
        end = PROBE + len(code) - 2
        for _ in range(2000):
            if end <= m.pc <= end + 2:
                return
            m.run_us(100)
        raise AssertionError(f"δεν γύρισε: #{m.pc:04X}")

    q = []                                      # 16 in_hit και 16 in_held, C = #5A, DE = #1234
    for k, name in enumerate(("IN_HIT", "IN_HELD")):
        for a in range(16):
            at = BUF + 8 * (16 * k + a)
            q += [0x01, 0x5A, 0xC3, 0x11, 0x34, 0x12, 0x3E, a] + call(name)
            q += [0xF5, 0xE1, 0x22, at & 255, at >> 8, 0xED, 0x43, (at + 2) & 255, (at + 2) >> 8,
                  0xED, 0x53, (at + 4) & 255, (at + 4) >> 8]

    def step(pressed, want_now, want_hit, label):
        rows = [0xFF] * 10                      # 0 = πατημένο, όπως το δίνει ο PSG
        for line, bit in pressed:
            rows[line] &= ~(1 << bit) & 0xFF
        m.write_ram(sym["KEY_NOW"], bytes(rows))
        run(call("IN_READ"))
        got = (w(sym["ACT_NOW"]), w(sym["ACT_HIT"]))
        if got != (want_now, want_hit):
            return f"{label}: act_now #{got[0]:04X}, act_hit #{got[1]:04X}, " \
                   f"περίμενα #{want_now:04X}, #{want_hit:04X}"
        run(q)
        for i in range(32):
            b = m.read_ram(BUF + 8 * i, 6)
            nz, c, de = not (b[0] & 0x40), b[2], b[4] | (b[5] << 8)
            word = want_hit if i < 16 else want_now
            if nz != bool(word >> (i & 15) & 1) or c != 0x5A or de != 0x1234:
                return f"{label}: {'in_hit' if i < 16 else 'in_held'}({i & 15}) " \
                       f"{'NZ' if nz else 'Z'}, C #{c:02X}, DE #{de:04X}"
        return None

    cases = [(f"πλήκτρο της ενέργειας {a}", [lb], 1 << a) for a, lb in KEYS.items()]
    cases += [(f"γραμμή 9 bit {b}", [(9, b)], 0 if a is None else 1 << a) for b, a in enumerate(JOY)]
    used = set(KEYS.values()) | {(9, b) for b in range(8)}
    cases.append(("όλα τα άλλα πλήκτρα", [(l, b) for l in range(9) for b in range(8)
                                          if (l, b) not in used], 0))
    cases.append(("όλα μαζί", [(l, b) for l in range(10) for b in range(8)], 0xFFFF))
    for label, keys, want in cases:
        for st, (pr, now, hit) in enumerate(((keys, want, want), (keys, want, 0), ([], 0, 0))):
            why = step(pr, now, hit, f"{label}, {('πάτημα', 'κράτημα', 'άφημα')[st]}")
            if why:
                return why
    return None


def main():
    sym = build()
    from cpc import CPC, KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_ESC, \
        KEY_SPACE, KEY_F9, JOY_UP, JOY_DOWN, JOY_LEFT, JOY_RIGHT, JOY_FIRE

    # ΕΝΑ ΠΛΗΚΤΡΟ ΔΕΝ ΔΟΚΙΜΑΖΕΤΑΙ ΚΑΤΕΥΘΕΙΑΝ: το COPY δεν έχει ASCII. Μοιράζεται
    # όμως ΓΡΑΜΜΗ της μήτρας με πλήκτρο που δοκιμάζεται (τη γραμμή 1 με τον
    # αριστερό κέρσορα), και η τρίτη στήλη παρακάτω ελέγχει το ΩΜΟ bit — άρα η
    # γραμμή επαληθεύεται. Ως το βήμα 79 το ίδιο ίσχυε για το TAB, που ο
    # κωδικός του (9) συγκρούεται με το KEY_RIGHT του εξομοιωτή· η θέση του
    # είναι από τότε το I, που πατιέται.
    CASES = [
        ("κέρσορας πάνω",    dict(key=KEY_UP),    A_UP,     0, 0x01),
        ("κέρσορας κάτω",    dict(key=KEY_DOWN),  A_DOWN,   0, 0x04),
        ("κέρσορας αριστ.",  dict(key=KEY_LEFT),  A_LEFT,   1, 0x01),
        ("κέρσορας δεξιά",   dict(key=KEY_RIGHT), A_RIGHT,  0, 0x02),
        ("ESC",              dict(key=KEY_ESC),   A_CANCEL, 8, 0x04),
        ("SPACE",            dict(key=KEY_SPACE), A_MENU,   5, 0x80),
        ("H",                dict(key="H"),       A_HOME,   5, 0x10),
        ("I πληροφορίες",    dict(key="I"),       A_INFO,   4, 0x08),
        ("1",                dict(key="1"),       A_SPD1,   8, 0x01),
        ("2",                dict(key="2"),       A_SPD2,   8, 0x02),
        ("3",                dict(key="3"),       A_SPD3,   7, 0x02),
        ("4",                dict(key="4"),       A_SPD4,   7, 0x01),
        ("S σώσε",           dict(key="S"),       A_SAVE,   7, 0x10),
        ("L φόρτωσε",        dict(key="L"),       A_LOAD,   4, 0x10),
        ("joy πάνω",         dict(joy=JOY_UP),    A_UP,     9, 0x01),
        ("joy κάτω",         dict(joy=JOY_DOWN),  A_DOWN,   9, 0x02),
        ("joy αριστερά",     dict(joy=JOY_LEFT),  A_LEFT,   9, 0x04),
        ("joy δεξιά",        dict(joy=JOY_RIGHT), A_RIGHT,  9, 0x08),
        ("joy fire",         dict(joy=JOY_FIRE),  A_FIRE,   9, 0x10),
    ]

    fails = 0
    for name, how, want, line, bit in CASES:
        m = CPC()
        m.run_frames(60)
        assert m.quickload(SNA), "quickload απέτυχε"
        m.run_frames(6)
        if "joy" in how:
            m.set_joystick_type(1)
            m.run_frames(2)
            m.joystick(how["joy"])
            m.run_frames(6)
            raw = m.peek(sym["KEY_NOW"] + line)
            m.run_frames(4)
            m.joystick(0)
        else:
            m.key_down(how["key"])
            m.run_frames(6)
            raw = m.peek(sym["KEY_NOW"] + line)
            m.run_frames(4)
            m.key_up(how["key"])
        m.run_frames(4)
        if raw & bit:                       # 0 = πατημένο, όπως το δίνει ο PSG
            fails += 1
            print(f"ΑΠΟΤΥΧΙΑ {name:18s} ωμή γραμμή {line} = #{raw:02X}, "
                  f"περίμενα το bit #{bit:02X} μηδέν")
            continue
        hits = [m.peek(sym["HIT_N"] + i) for i in range(len(NAMES))]
        got = [i for i, h in enumerate(hits) if h]
        if got == [want] and hits[want] == 1:
            print(f"OK {name:18s} -> {NAMES[want]}, μία ακμή σε 10 frames")
        else:
            fails += 1
            detail = ", ".join(f"{NAMES[i]}={hits[i]}" for i in got) or "τίποτα"
            print(f"ΑΠΟΤΥΧΙΑ {name:18s} περίμενα μόνο {NAMES[want]}=1, "
                  f"πήρα {detail}")

    why = logic(sym)
    if why:
        fails += 1
        print(f"ΑΠΟΤΥΧΙΑ λογική: {why}")
    else:
        print("OK λογική: τα 16 πλήκτρα (μαζί COPY και C) και τα 8 bits της γραμμής 9, "
              "πάτημα-κράτημα-άφημα, in_hit και in_held για τις 16 ενέργειες, C και DE κρατημένα")
    # --- αρνητικά ---
    from cpc import CPC
    m = CPC()
    m.run_frames(60)
    assert m.quickload(SNA, start=False)
    ir = sym["IN_READ"]
    joy = next((k for k in range(64) if list(m.read_ram(ir + k, 2)) == [0xE6, 0x3F]), None)
    info = sym["ACT_SRC"] + 2 * A_INFO + 1
    for label, patch in (("I στο bit 4, εκεί που είναι το L", [(info, 0x10)] if m.peek(info) == 0x08 else None),
                         ("χειριστήριο χωρίς fire 2", [(ir + joy + 1, 0x1F)] if joy is not None else None),
                         ("in_held από το act_hit", [(sym["IN_HELD"] + 1, sym["ACT_HIT"] & 255)])):
        if patch is None or logic(sym, patch) is None:
            fails += 1
            print(f"ΑΠΟΤΥΧΙΑ ΑΡΝΗΤΙΚΟ: με {label} η λογική πέρασε")
        else:
            print(f"OK ΑΡΝΗΤΙΚΟ: με {label} η λογική αποτυγχάνει")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
