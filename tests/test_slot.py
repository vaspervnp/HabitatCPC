#!/usr/bin/env python3
"""Θέση δακτυλίου που αδειάζει (DESIGN §8.5, §15).

Οταν ΕΡΧΕΤΑΙ άποικος, το αδιαφανές 2x8 της φιγούρας είναι ό,τι θα έβγαζε το
πλήρες πέρασμα — ο δακτύλιος είναι ψημένος μέσα. Οταν ΦΕΥΓΕΙ, η «κενή»
παραλλαγή είναι ο δακτύλιος πάνω σε ΜΑΥΡΟ, ενώ το πλήρες πέρασμα δείχνει το
ΕΔΑΦΟΣ όπου ο δακτύλιος είναι διαφανής. Ως το βήμα 42 αυτό άφηνε 1-8 bytes
λάθος σε 12 από τις 20 ορατές θέσεις της αποικίας δοκιμής, και το §15 το
χρέωνε στο κόψιμο. Από τότε το dhs_vacate ξαναστρώνει έδαφος και αντικείμενα
κομμένα στο 2x8.

  ΙΣΟΔΥΝΑΜΙΑ  Κάθε ορατή θέση με άποικο, σε πέντε κάμερες: ο άποικος φεύγει,
              ο χειριστής της λίστας τρέχει, και η οθόνη είναι byte προς byte
              η πλήρης σχεδίαση. ΑΡΝΗΤΙΚΟ: χωρίς το dhs_vacate, όχι.
  ΠΡΟΫΠΟΛΟΓΙΣΜΟΣ  Ο πίνακας λέει 1.500 us για το DK_SLOT (άποικος που
              έρχεται)· ένα ορατό άδειασμα κοστίζει πολύ περισσότερο, και το
              λέει μόνο του στον dirty_tick: τίποτε άλλο στο ίδιο καρέ.
              ΑΡΝΗΤΙΚΟ: χωρίς αυτό, δύο αδειάσματα στο ίδιο καρέ.
  ΚΟΣΤΟΣ      Μετρημένο για κάθε θέση, ορατή ή όχι.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/vasilhs/cpcemu")

import test_index as T                                             # noqa: E402

SCR_W, PLAY = 80, 160
PROBE = 0x3F10                      # η σκαλωσιά των δοκιμών (§4.2)
AG = 0x6C00 - 0x4000                # G_agent_fields μέσα στην τράπεζα 6
VAC_US = 18000                      # DHS_VAC_US (src/dirty.asm)
VAC_MAX = 25.0                      # ms, το χειρότερο άδειασμα
FAIL = []


def check(ok, msg):
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ ") + msg)
    if not ok:
        FAIL.append(msg)


class Run:
    def __init__(self, sym, cam, patch=()):
        from cpc import _lib
        self.sym = sym
        self.m = T.boot(sym, *cam)
        self.b6 = _lib.cpcemu_ram_ptr(self.m._h, 6)
        for at, v in patch:
            self.m.poke(at, v)

    def call(self, n):
        return [0xCD, self.sym[n] & 0xFF, self.sym[n] >> 8]

    def st(self, n, v):
        return [0x3E, v, 0x32, self.sym[n] & 0xFF, self.sym[n] >> 8]

    def go(self, code):
        """Τρέχει κώδικα στη σκαλωσιά ως το τέλος του. -> us."""
        s, m = self.sym, self.m
        code = code + self.st("DONE_FLAG", 0x5A) + [0x18, 0xFE]
        m.write_ram(PROBE, bytes(code))
        m.poke(s["DONE_FLAG"], 0)
        m.set_pc(PROBE)
        us = 0
        while m.peek(s["DONE_FLAG"]) != 0x5A:
            m.run_us(20)
            us += 20
            assert us < 5_000_000, "ο κώδικας της δοκιμής δεν τελείωσε"
        return us

    def snap(self):
        m, s = self.m, self.sym
        off = m.peek(s["CAM_OFF"]) | (m.peek(s["CAM_OFF"] + 1) << 8)
        ram = m.read_ram(0xC000, 0x4000)
        return bytes(ram[(y & 7) * 0x800 + (((y >> 3) * SCR_W + x + 2 * off) & 0x7FF)]
                     for y in range(PLAY) for x in range(SCR_W))

    def seated(self):
        """[(άποικος, θόλος, θέση)] — όσοι κάθονται σε θέση δακτυλίου."""
        b6 = self.b6
        return [(i, b6[AG + 256 + i], b6[AG + 384 + i]) for i in range(128)
                if b6[AG + i] & 1 and b6[AG + 256 + i] < 64
                and b6[AG + 384 + i] != 255]

    def leave(self, i):
        """Ο άποικος φεύγει (πεθαίνει) και ο πίνακας φιγούρων ξαναχτίζεται."""
        self.b6[AG + i] &= 0xFE
        self.go([0x01, 0xC6, 0x7F, 0xED, 0x49] + self.call("OB_FIG_SCAN"))

    def slot(self, d, s):
        """Ο χειριστής του DK_SLOT για (θόλος, θέση). -> us."""
        return self.go(self.st("DT_KIND", 0) + self.st("DT_A", d)
                       + self.st("DT_B", s) + self.call("DT_DISPATCH"))

    def full(self):
        m, s = self.m, self.sym
        m.poke(s["DONE_FLAG"], 0)
        m.set_pc(s["START"])
        for _ in range(400):
            if m.peek(s["DONE_FLAG"]) == 0x5A:
                return self.snap()
            m.run_frames(1)
        raise AssertionError("η πλήρης σχεδίαση δεν τελείωσε")


def vacate_all(sym, patch=()):
    """[(κάμερα, θόλος, θέση, άλλαξαν, λάθος, us)] για κάθε θέση με άποικο."""
    out = []
    for tx, ty, _ in T.CAMERAS:
        for i, d, s in Run(sym, (tx, ty)).seated():
            r = Run(sym, (tx, ty), patch)
            before = r.snap()
            r.leave(i)
            us = r.slot(d, s)
            got = r.snap()
            ref = r.full()
            changed = sum(1 for a, b in zip(before, got) if a != b)
            bad = sum(1 for a, b in zip(got, ref) if a != b)
            out.append(((tx, ty), d, s, changed, bad, us))
    return out


def find_call(r, at, target, n=64):
    """Η διεύθυνση του CALL Z,target μέσα στα n bytes από το at."""
    for k in range(n):
        if (r.m.peek(at + k) == 0xCC and r.m.peek(at + k + 1) == target & 0xFF
                and r.m.peek(at + k + 2) == target >> 8):
            return at + k
    raise SystemExit("δεν βρέθηκε το CALL Z,dhs_vacate στο dh_slot")


def find_imm(r, at, value, n=96):
    """Η διεύθυνση του LD DE,value μέσα στα n bytes από το at."""
    for k in range(n):
        if (r.m.peek(at + k) == 0x11 and r.m.peek(at + k + 1) == value & 0xFF
                and r.m.peek(at + k + 2) == value >> 8):
            return at + k
    raise SystemExit(f"δεν βρέθηκε το LD DE,{value} στο dhs_vacate")


def budget(sym, patch=()):
    """Δύο ορατές θέσεις αδειάζουν, δύο DK_SLOT στη λίστα, ΕΝΑΣ dirty_tick.
    -> πόσα στοιχεία έμειναν στη λίστα."""
    cam = T.CAMERAS[0][:2]
    r = Run(sym, cam, patch)
    seen = []
    for i, d, s in r.seated():
        probe = Run(sym, cam)
        probe.leave(i)
        if probe.slot(d, s) > 2000:          # ορατή: πέρασε από το dhs_vacate
            seen.append((i, d, s))
        if len(seen) == 2:
            break
    assert len(seen) == 2, "δεν βρέθηκαν δύο ορατές θέσεις με άποικο"
    for i, d, s in seen:
        r.b6[AG + i] &= 0xFE
    code = [0x01, 0xC6, 0x7F, 0xED, 0x49]
    for i, d, s in seen:
        code += [0x3E, 0, 0x06, d, 0x0E, s] + r.call("DIRTY_PUSH")
    r.go(code)
    r.go(r.call("DIRTY_TICK"))
    return r.m.peek(sym["DIRTY_NUM"])


def main():
    sym = T.build()

    res = vacate_all(sym)
    seen = [x for x in res if x[3]]
    wrong = [x for x in seen if x[4]]
    check(seen and not wrong,
          f"{len(seen)} ορατές θέσεις άδειασαν από τη λίστα, σε {len(T.CAMERAS)} "
          f"κάμερες: η οθόνη είναι η πλήρης σχεδίαση σε όλες"
          + (f" — λάθος {[(x[0], x[1], x[2], x[4]) for x in wrong[:4]]}" if wrong else ""))

    # --- ΑΡΝΗΤΙΚΟ: το CALL Z,dhs_vacate σε NOP ---
    r = Run(sym, T.CAMERAS[0][:2])
    at = find_call(r, sym["DH_SLOT"], sym["DHS_VACATE"])
    neg = vacate_all(sym, patch=[(at + k, 0) for k in range(3)])
    nwrong = [x for x in neg if x[4]]
    check(len(nwrong) > 0,
          f"ΑΡΝΗΤΙΚΟ: χωρίς το dhs_vacate {len(nwrong)} από τις {len(seen)} θέσεις "
          f"αφήνουν λάθος, ως {max((x[4] for x in nwrong), default=0)} bytes")

    # --- ο προϋπολογισμός ---
    left = budget(sym)
    check(left == 1, f"δύο ορατά αδειάσματα στη λίστα, ένας dirty_tick: βγήκε "
                     f"ΕΝΑ, έμεινε {left}")
    imm = find_imm(r, sym["DHS_VACATE"], VAC_US)
    left = budget(sym, patch=[(imm + 1, 0), (imm + 2, 0)])
    check(left == 0, f"ΑΡΝΗΤΙΚΟ: χωρίς το κόστος του αδειάσματος στο dt_spent, "
                     f"βγήκαν και τα δύο στο ίδιο καρέ (έμειναν {left})")

    # --- το κόστος ---
    worst = max(x[5] for x in seen) / 1000
    mean = sum(x[5] for x in seen) / len(seen) / 1000
    hidden = [x[5] for x in res if not x[3]]
    check(worst < VAC_MAX and worst * 1000 < VAC_US + 1500 + 2500,
          f"άδειασμα ορατής θέσης: μέσο {mean:.1f} ms, χειρότερο {worst:.1f} ms "
          f"(όριο {VAC_MAX}· ο πίνακας + το DHS_VAC_US = {(VAC_US + 1500) / 1000:.1f}), "
          f"κρυφής {max(hidden, default=0) / 1000:.1f} ms")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
