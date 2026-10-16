#!/usr/bin/env python3
"""Το χείλος του κόσμου, στο main.sna (DESIGN §8.2, §9.1).

Ο κόσμος είναι τα tiles -64..63 και στους δύο άξονες. Ως το βήμα 78 ο
κέρσορας τυλιγόταν από το -64 στο 63, και η κάμερα, που δεν είχε όριο, τον
ακολουθούσε δυτικά μέσα από τις 128 στήλες έξω από τον κόσμο: σκουπίδια στην
οθόνη, και λεπτά ολόκληρα σκρολάρισμα. Η πρόζα λέει:

  ο κέρσορας      σταματά στο τελευταίο tile· ένα βήμα προς τα έξω δεν κάνει
                  τίποτα
  η κάμερα        δεν δείχνει ποτέ τίποτα έξω από τον κόσμο: πάνω-αριστερά
                  x -64..44, y -64..54· στο χείλος το περιθώριο του ενός tile
                  χάνεται και ο κέρσορας φτάνει ως το τελευταίο

ΤΕΣΣΕΡΑ ΤΑΞΙΔΙΑ, από την αρχή ως τις τέσσερις γωνίες, με δύο κατευθύνσεις
πατημένες μαζί. Σε κάθε frame: ο κέρσορας μέσα στον κόσμο, η κάμερα μέσα στα
όριά της, και κανένας από τους δύο δεν πάει πίσω ή πάνω από ένα tile τη φορά.
Στο τέλος: ο κέρσορας στη γωνία, η κάμερα στη δική της, και το κάδρο —
χτισμένο λωρίδα-λωρίδα στο σκρολάρισμα — ίδιο με πλήρη σχεδίαση στην ίδια
κάμερα.

ΤΟ ΚΟΥΜΠΩΜΑ ΜΙΣΟΥ TILE. Ενα αποτύπωμα με περιττό πλάτος έχει κέντρο στη μέση
tile, και ο ηλιακός (3 x 3) φτάνει το κέντρο στο 127 στο ανατολικό χείλος.
Αλλάζοντας σε θόλο (άρτιο πλάτος), το bd_select πήγαινε το κέντρο μισό tile
πιο πέρα: στο 128, δηλαδή στο -128, την άλλη άκρη του κόσμου. Τώρα πάει μισό
tile πίσω, στο 126.

Αρνητικά, με τον κώδικα πειραγμένο στη μνήμη: ο κέρσορας χωρίς το όριό του στο
x, η κάμερα χωρίς το δυτικό και χωρίς το νότιο όριο, το κούμπωμα που τυλίγεται.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
from cpc import CPC, KEY_LEFT, KEY_RIGHT, KEY_UP, KEY_DOWN, KEY_SPACE  # noqa: E402

PROBE = 0x3E80
CAM_X, CAM_Y = (-64, 44), (-64, 54)
FAIL = []


def check(ok, msg):
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ ") + msg)
    if not ok:
        FAIL.append(msg)


def s8(v):
    return v - 256 if v > 127 else v


class Game:
    def __init__(self, sym, patch=()):
        self.sym = sym
        m = self.m = CPC()
        m.run_frames(60)
        assert m.quickload(TG.COLONY), "quickload απέτυχε"
        m.run_frames(120)
        for at, v in patch:
            m.poke(at, v)

    def state(self):
        """((κέρσορας x, y) σε tiles, (κάμερα x, y))."""
        p = self.m.peek
        return ((s8(p(self.sym["CUR_HX"])) >> 1, s8(p(self.sym["CUR_HY"])) >> 1),
                (s8(p(self.sym["CAM_TX"])), s8(p(self.sym["CAM_TY"]))))

    def probe(self, names):
        """Κώδικας του παιχνιδιού από την αναμονή του βρόχου, και πίσω εκεί."""
        m, top = self.m, self.sym["MAIN_LOOP"]
        for _ in range(40000):
            if top <= m.pc < top + 13:
                break
            m.run_us(50)
        # di πρώτα (βήμα 83): αλλιώς η διακοπή των λωρίδων τρέχει πάνω στο jr $,
        # και ο έλεγχος του PC την πετυχαίνει μέσα της. Το ei το ξανακάνει ο βρόχος.
        code = [0xF3]
        for n in names:
            code += [0xCD, self.sym[n] & 0xFF, self.sym[n] >> 8]
        m.run_code(PROBE, bytes(code + [0x18, 0xFE]), frames=100)
        assert PROBE + len(code) - 1 <= m.pc <= PROBE + len(code) + 1, \
            f"το {names} δεν τελείωσε: pc={m.pc:#06x}"
        m.set_pc(top)

    def play(self):
        """Οι 160 γραμμές του κάδρου, όπως τις δείχνει το CRTC."""
        m = self.m
        off = m.peek(self.sym["CAM_OFF"]) | (m.peek(self.sym["CAM_OFF"] + 1) << 8)
        ram = m.read_ram(0xC000, 0x4000)
        return bytes(ram[(y & 7) * 0x800 + (((y >> 3) * 80 + x + 2 * off) & 0x7FF)]
                     for y in range(160) for x in range(80))


def walk(sym, keys, corner, patch=()):
    """Από την αρχή ως τη γωνία με τα πλήκτρα πατημένα. -> λάθος ή None."""
    G = Game(sym, patch)
    m = G.m
    sx, sy = corner[0] > 0 and 1 or -1, corner[1] > 0 and 1 or -1
    cam_corner = (CAM_X[sx > 0], CAM_Y[sy > 0])
    for k in keys:
        m.key_down(k)
    prev = G.state()
    still = 0
    for f in range(2400):
        m.run_frames(1)
        cur, cam = G.state()
        for axis, s in ((0, sx), (1, sy)):
            dc, dk = cur[axis] - prev[0][axis], cam[axis] - prev[1][axis]
            if not (-64 <= cur[axis] <= 63):
                return f"frame {f}: ο κέρσορας στο {cur} — έξω από τον κόσμο"
            lim = (CAM_X, CAM_Y)[axis]
            if not (lim[0] <= cam[axis] <= lim[1]):
                return f"frame {f}: η κάμερα στο {cam} — έξω από τα όριά της"
            if dc * s < 0 or abs(dc) > 1:
                return f"frame {f}: ο κέρσορας πήγε από {prev[0]} στο {cur}"
            if dk * s < 0 or abs(dk) > 1:
                return f"frame {f}: η κάμερα πήγε από {prev[1]} στο {cam}"
        still = still + 1 if (cur, cam) == prev else 0
        prev = (cur, cam)
        if still >= 60 and cur == corner:
            break
    for k in keys:
        m.key_up(k)
    m.run_frames(10)
    cur, cam = G.state()
    if cur != corner or cam != cam_corner:
        return f"ο κέρσορας στο {cur}, η κάμερα στο {cam}: η πρόζα λέει {corner}, {cam_corner}"
    G.probe(["UI_HIDE"])
    strips = G.play()
    G.probe(["OB_CLIP_FULL", "VIEW_DRAW"])
    full = G.play()
    bad = [i for i in range(len(full)) if full[i] != strips[i]]
    if bad:
        return (f"στη γωνία {corner} το κάδρο του σκρολαρίσματος διαφέρει από πλήρη "
                f"σχεδίαση σε {len(bad)} bytes, πρώτο (x={bad[0] % 80}, y={bad[0] // 80})")
    return None


def snap(sym, patch=()):
    """Ηλιακός στο ανατολικό χείλος, μετά θόλος S. -> λάθος ή None."""
    G = Game(sym, patch)
    m = G.m

    def tap(key, n=1):
        for _ in range(n):
            m.key_down(key)
            m.run_frames(3)
            m.key_up(key)
            m.run_frames(4)

    def joy(bits):
        m.set_joystick_type(1)
        m.joystick(bits)
        m.run_frames(4)
        m.joystick(0)
        m.run_frames(10)
        m.set_joystick_type(0)

    tap(KEY_SPACE, 2)                       # -> ACT -> MENU: το BUILD είναι πρώτο
    tap(KEY_RIGHT, 4)                       # -> SOLAR
    if m.peek(sym["BD_KIND"]) != 1:
        return f"ο κατάλογος δεν έφτασε στον ηλιακό (είδος {m.peek(sym['BD_KIND'])})"
    joy(0x10)                               # FIRE -> PLACE
    m.key_down(KEY_RIGHT)
    for _ in range(1200):
        m.run_frames(1)
        if m.peek(sym["CUR_HX"]) == 127 and G.state()[1][0] == CAM_X[1]:
            break
    m.run_frames(60)
    m.key_up(KEY_RIGHT)
    m.run_frames(10)
    if m.peek(sym["CUR_HX"]) != 127:
        return f"ο ηλιακός δεν έφτασε στο 127 (cur_hx = {s8(m.peek(sym['CUR_HX']))})"
    joy(0x20)                               # ESC -> MENU
    tap(KEY_LEFT, 4)                        # -> DOME S: bd_select, άρτιο πλάτος
    hx = s8(m.peek(sym["CUR_HX"]))
    joy(0x10)                               # FIRE -> PLACE
    m.key_down(KEY_RIGHT)
    m.run_frames(100)
    m.key_up(KEY_RIGHT)
    m.run_frames(10)
    cur, cam = G.state()
    if hx != 126 or cur[0] != 63 or cam[0] != CAM_X[1]:
        return (f"μετά το κούμπωμα cur_hx = {hx}, κέρσορας {cur}, κάμερα {cam}: η πρόζα "
                f"λέει 126, x = 63, κάμερα x = {CAM_X[1]}")
    return None


TRIPS = [((KEY_LEFT, KEY_UP), (-64, -64), "βορειοδυτική"),
         ((KEY_RIGHT, KEY_UP), (63, -64), "βορειοανατολική"),
         ((KEY_RIGHT, KEY_DOWN), (63, 63), "νοτιοανατολική"),
         ((KEY_LEFT, KEY_DOWN), (-64, 63), "νοτιοδυτική")]


def main():
    sym, _ = TG.build()
    for keys, corner, name in TRIPS:
        why = walk(sym, keys, corner)
        check(why is None, f"ως τη {name} γωνία {corner}: κέρσορας και κάμερα μέσα στον "
                           f"κόσμο σε κάθε frame, και στο τέλος το κάδρο = πλήρης σχεδίαση"
                           + (f" — {why}" if why else ""))
    why = snap(sym)
    check(why is None, "το κούμπωμα μισού tile στο ανατολικό χείλος μένει στο 126"
                       + (f" — {why}" if why else ""))

    m = Game(sym).m

    def find(at, pat, span=200):
        i = m.read_ram(sym[at], span).find(bytes(pat))
        assert i >= 0, f"δεν βρέθηκε το {pat} στο {at}"
        return sym[at] + i

    west = find("UI_FOLLOW", [0x7E, 0xFE, 0xC0, 0x28])
    south = find("UI_FOLLOW", [0x7E, 0xFE, CAM_Y[1], 0xC8])
    neg = [("τον κέρσορα χωρίς όριο στο x", walk,
            [(find("UI_MOVE", [0x83, 0xE2]) + 1, 0xC3)],             # jp po -> jp
            (TRIPS[0][0], TRIPS[0][1])),
           ("την κάμερα χωρίς δυτικό όριο", walk, [(west + 3, 0), (west + 4, 0)],
            (TRIPS[0][0], TRIPS[0][1])),
           ("την κάμερα χωρίς νότιο όριο", walk, [(south + 3, 0)],
            (TRIPS[2][0], TRIPS[2][1])),
           ("το κούμπωμα που τυλίγεται", snap,
            [(find("BD_SELECT", [0x34, 0xE2]) + 1, 0xC3)], ())]
    for label, fn, patch, args in neg:
        why = fn(sym, *args, patch=patch)
        check(why is not None, f"ΑΡΝΗΤΙΚΟ: με {label} αποτυγχάνει"
                               + (f" ({why[:100]})" if why else ""))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
