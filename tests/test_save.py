#!/usr/bin/env python3
"""Σώσιμο και φόρτωμα στον δίσκο (DESIGN.md §11).

Το παιχνίδι ξεκινά από δισκέτα και γράφει στην ΙΔΙΑ δισκέτα, με δικό του
οδηγό: όταν τρέχει, το AMSDOS δεν υπάρχει πια (ο χώρος εργασίας του είναι
δεδομένα της τράπεζας 2). Ο οδηγός ελέγχεται χωριστά στο test_fdc.py· εδώ
ελέγχεται ότι ΑΥΤΟ που ξαναδιαβάζεται είναι το παιχνίδι.

Η δοκιμή παγώνει τον τροχό (wh_on = 0) γύρω από κάθε φωτογραφία. Χωρίς αυτό,
δύο «ίδιες» καταστάσεις απέχουν όσα frames πέρασαν ανάμεσά τους, και ο έλεγχος
θα ήταν ανοχή αντί για ισότητα.

  1. Φωτογραφία Α (παγωμένος κόσμος), S = σώσε.
  2. Ο κόσμος τρέχει 4.000 frames — η οικονομία ΠΡΕΠΕΙ να έχει αλλάξει,
     αλλιώς η δοκιμή δεν δοκιμάζει τίποτα.
  3. L = φόρτωσε. Φωτογραφία Γ: οικονομία, επίπεδο κόσμου και ΕΙΚΟΝΑ πίσω στο Α.
  4. Αρνητικός έλεγχος: φόρτωμα από ΑΔΕΙΟ slot πρέπει να απορριφθεί και να μην
     αγγίξει τίποτα. Ενα άδειο slot είναι #E5 παντού — απολύτως έγκυρα bytes.
  5. ΚΑΙ ΑΠΟ ΚΡΥΑ ΕΚΚΙΝΗΣΗ: reset, ξαναφόρτωμα από τον δίσκο — που φτιάχνει
     ΑΛΛΟΝ κόσμο, γιατί το seed βγαίνει από τον καταχωρητή R — και μετά L. Αυτό
     είναι η πραγματική χρήση, και μόνο εδώ αποδεικνύεται ότι το επίπεδο
     αντικαθίσταται ΟΛΟΚΛΗΡΟ: τα 16 KB διαφέρουν παντού πριν το φόρτωμα.
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")

RASM = os.path.expanduser("~/rasm/rasm.exe")
DSK = os.path.join(ROOT, "build", "habitat.dsk")
PLANE = os.path.join(ROOT, "build", "plane.bin")
FAIL = []


def check(ok, msg):
    print(("OK " if ok else "ΛΑΘΟΣ ") + msg)
    if not ok:
        FAIL.append(msg)


def build():
    for cmd in ([sys.executable, os.path.join(ROOT, "tools", "mkdsk.py")],
                [RASM, "plane.asm"]):
        r = subprocess.run(cmd, cwd=HERE if cmd[0] == RASM else ROOT,
                           capture_output=True, text=True)
        if r.returncode:
            sys.exit(f"{cmd[0]} απέτυχε:\n{r.stdout}{r.stderr}")
    sym = {}
    for line in open(os.path.join(ROOT, "src", "rasmoutput.sym"),
                     encoding="utf-8", errors="replace"):
        p = line.split()
        if len(p) >= 2 and p[1].startswith("#"):
            sym[p[0].upper()] = int(p[1][1:], 16)
    g = None
    for line in open(os.path.join(ROOT, "build", "layout.asm"), encoding="utf-8"):
        if line.startswith("G_econ_state"):
            g = int(line.split("#")[1].strip(), 16)
    return sym, g


def main():
    sym, g = build()
    from cpc import CPC
    blob = open(PLANE, "rb").read()

    m = CPC()
    m.run_frames(300)
    m.insert_disc(DSK)
    m.type_text('|disc\n', hold_frames=4, gap_frames=8)
    m.run_frames(60)
    m.type_text('run"habitat\n', hold_frames=4, gap_frames=8)

    def w16(a):
        return m.peek(a) | (m.peek(a + 1) << 8)

    for _ in range(120):
        m.run_frames(30)
        if w16(g + 2) == 40 and m.peek(g + 58) == 4:
            break
    else:
        sys.exit("το παιχνίδι δεν ξεκίνησε από τον δίσκο")
    m.run_frames(200)

    def freeze(on):
        for i in range(16):
            m.poke(sym["WH_ON"] + i, 0 if on else 1)

    def snap():
        """Οικονομία, δείγματα επιπέδου, και η ΕΙΚΟΝΑ του κάδρου."""
        econ = bytes(m.read_ram(0xA400, 0x800))
        m.run_code(0x3E00, blob)
        m.run_frames(2)
        plane = bytes(m.read_ram(0x3F00, 256))
        m.set_pc(sym["MAIN_LOOP"])
        m.run_frames(2)
        off = w16(sym["CAM_OFF"])
        ram = m.read_ram(0xC000, 0x4000)
        play = bytes(ram[(y & 7) * 0x800 + (((y >> 3) * 80 + x + 2 * off) & 0x7FF)]
                     for y in range(160) for x in range(80))
        return econ, plane, play

    def tap(key, frames=400):
        m.key_down(key)
        m.run_frames(4)
        m.key_up(key)
        m.run_frames(frames)

    def tap_timed(key):
        """Πατά το πλήκτρο και μετρά ΠΟΣΑ frames κρατά η κίνηση της κεφαλής."""
        m.poke(sym["FD_TRK"], 0)
        m.key_down(key)
        m.run_frames(4)
        m.key_up(key)
        n = 0
        while n < 900 and m.peek(sym["FD_TRK"]) < 29:
            m.run_frames(1)
            n += 1
        m.run_frames(30)
        return n + 4

    # --- 1. φωτογραφία Α και σώσιμο ---------------------------------------
    freeze(True)
    m.run_frames(4)
    a_econ, a_plane, a_play = snap()
    nsave = tap_timed("S")
    check(m.peek(sym["SV_SLOT"]) == 0 and m.peek(sym["FD_TRK"]) >= 24,
          f"το σώσιμο έτρεξε (slot {m.peek(sym['SV_SLOT'])}, "
          f"track #{m.peek(sym['FD_TRK'])})")

    # --- 2. ο κόσμος προχωρά ----------------------------------------------
    freeze(False)
    m.run_frames(12000)
    freeze(True)
    m.run_frames(4)
    b_econ, b_plane, b_play = snap()
    o = g - 0xA400
    dwater = (b_econ[o] | (b_econ[o + 1] << 8)) - (a_econ[o] | (a_econ[o + 1] << 8))
    check(b_econ != a_econ,
          f"η κατάσταση άλλαξε στα 12.000 frames (νερό {dwater:+d}, "
          f"{sum(1 for x, y in zip(b_econ, a_econ) if x != y)} bytes)")

    # --- 3. φόρτωμα --------------------------------------------------------
    nload = tap_timed("L")
    m.run_frames(120)
    c_econ, c_plane, c_play = snap()
    check(c_plane == a_plane, "το επίπεδο κόσμου γύρισε ακριβώς")
    same = sum(1 for x, y in zip(c_econ, a_econ) if x == y)
    check(same >= len(a_econ) - 8,
          f"η κατάσταση γύρισε: {len(a_econ) - same} bytes διαφορά στα "
          f"{len(a_econ)} (πριν το φόρτωμα: "
          f"{sum(1 for x, y in zip(b_econ, a_econ) if x != y)})")
    diff = sum(1 for x, y in zip(c_play, a_play) if x != y)
    bdiff = sum(1 for x, y in zip(b_play, a_play) if x != y)
    check(diff <= 8 and bdiff > 8,
          f"η εικόνα γύρισε: {diff} bytes διαφορά από το Α "
          f"(πριν το φόρτωμα: {bdiff})")

    # --- 4. άδειο slot -----------------------------------------------------
    lo, hi = sym["SV_LOAD"] & 0xFF, sym["SV_LOAD"] >> 8
    m.run_code(0x3E00, bytes([0x3E, 0x02, 0xCD, lo, hi, 0x32, 0x00, 0x3F,
                              0x18, 0xFE]))
    m.run_frames(120)
    rc = m.peek(0x3F00)
    m.set_pc(sym["MAIN_LOOP"])
    m.run_frames(4)
    d_econ, _, _ = snap()
    check(rc != 0, f"το άδειο slot 3 απορρίφθηκε (κωδικός #{rc:02X})")
    check(d_econ == c_econ, "και δεν άγγιξε την κατάσταση")

    print(f"\nκόστος: σώσιμο {nsave} frames, φόρτωμα {nload} frames "
          f"— 46 τομείς, 23 KB")
    # --- 5. κρύα εκκίνηση, άλλος κόσμος, και μετά φόρτωμα ------------------
    m.reset()
    m.run_frames(300)
    m.type_text('|disc\n', hold_frames=4, gap_frames=8)
    m.run_frames(60)
    m.type_text('run"habitat\n', hold_frames=4, gap_frames=8)
    for _ in range(120):
        m.run_frames(30)
        if w16(g + 2) == 40 and m.peek(g + 58) == 4:
            break
    else:
        sys.exit("το παιχνίδι δεν ξαναξεκίνησε μετά το reset")
    m.run_frames(200)
    freeze(True)
    m.run_frames(4)
    e_econ, e_plane, e_play = snap()
    check(e_plane != a_plane,
          f"η κρύα εκκίνηση έφτιαξε ΑΛΛΟΝ κόσμο "
          f"({sum(1 for x, y in zip(e_plane, a_plane) if x != y)}/256 δείγματα "
          f"διαφέρουν)")
    tap_timed("L")
    m.run_frames(120)
    f_econ, f_plane, f_play = snap()
    check(f_plane == a_plane, "το σωσμένο επίπεδο αντικατέστησε ολόκληρο το νέο")
    same = sum(1 for x, y in zip(f_econ, a_econ) if x == y)
    check(same >= len(a_econ) - 8,
          f"η αποικία γύρισε μετά από reset: {len(a_econ) - same} bytes διαφορά")
    fdiff = sum(1 for x, y in zip(f_play, a_play) if x != y)
    check(fdiff <= 8,
          f"και η εικόνα: {fdiff} bytes διαφορά από το Α")

    m.screenshot(os.path.join(ROOT, "build", "save.png"), aspect=True)
    if FAIL:
        print(f"\nΑΠΟΤΥΧΙΑ — {len(FAIL)}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
