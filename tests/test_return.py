#!/usr/bin/env python3
"""Πίσω στην αποικία μετά από έναν διάδρομο μακριά της, στο main.sna (DESIGN §8.4).

Ο παίκτης χτίζει δύο θόλους και τους ενώνει, 50 tiles από την αποικία, και
μετά σκρολάρει πίσω με τα βελάκια. Το κάδρο, χτισμένο λωρίδα-λωρίδα, πρέπει να
είναι ίδιο με πλήρη σχεδίαση από καθαρό ευρετήριο.

ΓΙΑΤΙ (βήμα 82). Το ob_corr κρατά στη μνήμη τον θόλο αφετηρίας του (d_id) και
δεν τον ξαναδιαβάζει. Μετά τον νέο διάδρομο το ευρετήριο ξαναχτίζει μόνο τους
διαδρόμους, και ο d_id ήταν ό,τι είχε διαβάσει το πέρασμα της οθόνης — με την
κάμερα εκεί, όχι με το (0, 0) της μέτρησης. Οι διάδρομοι της αποικίας που
ξεκινούσαν από εκείνον τον θόλο έπαιρναν κουτιά μετατοπισμένα κατά τη θέση
της κάμερας, και οι λωρίδες του σκρολαρίσματος δεν τους ζωγράφιζαν: η αποικία
γύριζε χωρίς διαδρόμους, ως την επόμενη πλήρη σχεδίαση. 125 bytes, στο πρώτο
από τα σενάρια εδώ.

Αρνητικό: το oi_build του βήματος 81 (ld hl,ob_meas · inc (hl)), που δεν
ξεχνά τον θόλο.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_link as L                                    # noqa: E402
import test_reveal as R                                  # noqa: E402
from cpc import JOY_FIRE, KEY_RIGHT, KEY_UP              # noqa: E402

FAIL = []
# (μέγεθος a, μέγεθος b, dx, dy): το πρώτο είναι αυτό που έπιανε το λάθος
CASES = [(2, 0, -12, 6), (0, 2, 12, 6), (1, 1, 14, 0)]


def check(ok, msg):
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ ") + msg)
    if not ok:
        FAIL.append(msg)


def s8(v):
    return v - 256 if v > 127 else v


def trip(sym, g, case, patch=None):
    """Διάδρομος στο χωράφι, σκρολάρισμα πίσω. -> λάθος bytes, κάμερα."""
    P = L.Pair(sym, g, *case, patch=patch)
    G, m = P.G, P.G.m
    m.set_joystick_type(1)
    m.joystick(JOY_FIRE)                                 # ο διάδρομος
    for k in range(400):
        m.run_frames(1)
        if k == 4:
            m.joystick(0)
        if k > 10 and m.peek(sym["RV_PEND"]) == 0 and m.peek(sym["UI_OWED"]) == 0:
            break
    m.run_frames(10)
    G.stick(0x20)                                        # LINK -> MENU
    G.stick(0x20)                                        # MENU -> LOOK
    m.set_joystick_type(0)

    def cam():
        return s8(m.peek(sym["CAM_TX"])), s8(m.peek(sym["CAM_TY"]))
    m.key_down(KEY_RIGHT)
    m.key_down(KEY_UP)
    for _ in range(3000):
        m.run_frames(1)
        c = cam()
        if c[0] >= -12:
            m.key_up(KEY_RIGHT)
        if c[1] <= -6:
            m.key_up(KEY_UP)
        if c[0] >= -12 and c[1] <= -6:
            break
    m.key_up(KEY_RIGHT)
    m.key_up(KEY_UP)
    m.run_frames(30)
    G.still()
    G.probe(["UI_HIDE"])
    got = G.play()
    m.poke(sym["D_ID"], 255)
    m.poke(sym["OB_IDX"], 15)                            # καθαρό ευρετήριο
    G.probe(["OB_CLIP_FULL", "VIEW_DRAW"])
    want = G.play()
    return sum(a != b for a, b in zip(got, want)), cam()


def main():
    sym, g = R.T.build()
    for case in CASES:
        bad, c = trip(sym, g, case)
        check(bad == 0, f"διάδρομος {case} στο χωράφι, πίσω στην αποικία (κάμερα {c}): το "
                        f"κάδρο των λωρίδων = πλήρης σχεδίαση" + (f" — {bad} bytes" if bad else ""))
    # ΑΡΝΗΤΙΚΟ: τα bytes του βήματος 81 στη θέση του dec l · inc h · ld (d_id),hl
    m = R.Game(sym, g).m
    ob = sym["OI_BUILD"]
    code = m.read_ram(ob, 30)
    at = code.find(bytes([0x2D, 0x24, 0x22, sym["D_ID"] & 255, sym["D_ID"] >> 8]))
    assert at >= 0, "δεν βρέθηκε το dec l · inc h · ld (d_id),hl"
    meas = sym["OB_MEAS"]
    old = [0x21, meas & 255, meas >> 8, 0x34, 0x00]      # ld hl,ob_meas · inc (hl) · nop
    patch = {ob + at + k: v for k, v in enumerate(old)}
    bad, c = trip(sym, g, CASES[0], patch=patch)
    check(bad > 0, f"ΑΡΝΗΤΙΚΟ: με το oi_build του βήματος 81 το κάδρο διαφέρει ({bad} bytes)")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
