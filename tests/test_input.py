#!/usr/bin/env python3
"""Πληκτρολόγιο και χειριστήριο (DESIGN §9.1).

Το πληκτρολόγιο του CPC κρέμεται από τον ήχο και η ακολουθία των θυρών είναι
αυστηρή· ένα βήμα λιγότερο και δεν διαβάζεται τίποτα. Αυτό δεν ελέγχεται
διαβάζοντας — ελέγχεται πατώντας.

ΔΥΟ ΙΣΧΥΡΙΣΜΟΙ:
  1. Κάθε ενέργεια ανάβει από το πλήκτρο της ΚΑΙ μόνο από αυτό.
  2. Το act_hit είναι ακμή: κράτημα δέκα frames μετράει ΜΙΑ φορά. Χωρίς αυτό
     ένα «χτίσε» θα έχτιζε πενήντα θόλους το δευτερόλεπτο.
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, "/home/vasilhs/cpcemu")

RASM = os.path.expanduser("~/rasm/rasm.exe")
SNA = os.path.join(ROOT, "build", "inputtest.sna")

A_UP, A_DOWN, A_LEFT, A_RIGHT, A_FIRE, A_CANCEL, A_MENU, A_NEXT, A_HOME, \
    A_SPD1, A_SPD2, A_SPD3, A_SPD4 = range(13)
NAMES = ["πάνω", "κάτω", "αριστερά", "δεξιά", "FIRE", "ακύρωση", "μενού",
         "επόμενο", "κέντρο", "ταχ.1", "ταχ.2", "ταχ.3", "ταχ.4"]


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


def main():
    sym = build()
    from cpc import CPC, KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_ESC, \
        KEY_SPACE, KEY_F9, JOY_UP, JOY_DOWN, JOY_LEFT, JOY_RIGHT, JOY_FIRE

    # ΔΥΟ ΠΛΗΚΤΡΑ ΔΕΝ ΔΟΚΙΜΑΖΟΝΤΑΙ ΚΑΤΕΥΘΕΙΑΝ: το COPY δεν έχει ASCII και ο
    # κωδικός του TAB (9) συγκρούεται με το KEY_RIGHT του εξομοιωτή. Και τα δύο
    # όμως μοιράζονται ΓΡΑΜΜΗ της μήτρας με πλήκτρα που δοκιμάζονται (το COPY
    # τη γραμμή 1 με τον αριστερό κέρσορα, το TAB τη γραμμή 8 με το ESC), και η
    # τρίτη στήλη παρακάτω ελέγχει το ΩΜΟ bit — άρα η γραμμή επαληθεύεται.
    CASES = [
        ("κέρσορας πάνω",    dict(key=KEY_UP),    A_UP,     0, 0x01),
        ("κέρσορας κάτω",    dict(key=KEY_DOWN),  A_DOWN,   0, 0x04),
        ("κέρσορας αριστ.",  dict(key=KEY_LEFT),  A_LEFT,   1, 0x01),
        ("κέρσορας δεξιά",   dict(key=KEY_RIGHT), A_RIGHT,  0, 0x02),
        ("ESC",              dict(key=KEY_ESC),   A_CANCEL, 8, 0x04),
        ("SPACE",            dict(key=KEY_SPACE), A_MENU,   5, 0x80),
        ("H",                dict(key="H"),       A_HOME,   5, 0x10),
        ("1",                dict(key="1"),       A_SPD1,   8, 0x01),
        ("2",                dict(key="2"),       A_SPD2,   8, 0x02),
        ("3",                dict(key="3"),       A_SPD3,   7, 0x02),
        ("4",                dict(key="4"),       A_SPD4,   7, 0x01),
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
        if not raw & bit:
            fails += 1
            print(f"ΑΠΟΤΥΧΙΑ {name:18s} ωμή γραμμή {line} = #{raw:02X}, "
                  f"περίμενα το bit #{bit:02X}")
            continue
        hits = [m.peek(sym["HIT_N"] + i) for i in range(13)]
        got = [i for i, h in enumerate(hits) if h]
        if got == [want] and hits[want] == 1:
            print(f"OK {name:18s} -> {NAMES[want]}, μία ακμή σε 10 frames")
        else:
            fails += 1
            detail = ", ".join(f"{NAMES[i]}={hits[i]}" for i in got) or "τίποτα"
            print(f"ΑΠΟΤΥΧΙΑ {name:18s} περίμενα μόνο {NAMES[want]}=1, "
                  f"πήρα {detail}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
