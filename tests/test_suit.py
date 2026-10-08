#!/usr/bin/env python3
"""Οι στολές (βήμα 90, DESIGN §6.6), στο main.sna.

Εξω από τη βάση ο άποικος αναπνέει από τη στολή του. Η πρόζα — οι αποφάσεις
του παίκτη — σε λεπτά, και η μονάδα της (src/suit.asm) δύο επισκέψεις
αναγκών, 128 frames του τροχού:

  ΑΡΧΗ       οι τέσσερις του σκάφους με ΔΕΚΑ λεπτά αέρα, που πέφτουν μία
             μονάδα ανά 128 frames του τροχού. Χωρίς airlock κανείς δεν
             κουνιέται για αέρα. Το HUD δεν λέει SUIT AIR LOW όσο όλοι έχουν
             πάνω από ένα λεπτό· το λέει μόλις κάποιος πέσει κάτω. Οποιος
             αδειάσει πεθαίνει ΑΜΕΣΩΣ, με την υγεία του ανέγγιχτη ως τότε.
  ΕΞΟΔΟΣ     θόλος και airlock χτισμένα από τον παίκτη· ένας άποικος μέσα,
             με σχεδόν άδεια στολή, βγαίνει: στο έδαφος η στολή του είναι
             γεμάτη, ΤΡΙΑ λεπτά.
  ΕΠΙΣΤΡΟΦΗ  ο ίδιος, έξω στο σκάφος, μόλις πέσει στο ένα λεπτό: αφήνει ό,τι
             κάνει (T_NEED), πάει στο airlock (όχι στο σκάφος, που δεν έχει
             αέρα), μπαίνει, και ξαναγίνεται διαθέσιμος μέσα — ζωντανός.
  ΜΕΤΕΩΡΙΤΗΣ ένα airlock ξαναγίνεται εργοτάξιο (lk_air_out): όσοι στέκονταν
             μέσα του είναι έξω, με γεμάτη στολή, και φαίνονται (DK_AGENT)·
             κανείς άλλος δεν αλλάζει.
  ΕΡΓΟΤΑΞΙΟ  ένα εργοτάξιο κοιτώνα, και ο χτίστης του στέκεται εκεί, έξω,
             με ύπνο 10: δεν κοιμάται. Εξω κανένα δωμάτιο δεν δίνει τίποτα —
             ως το βήμα 89 ο ύπνος του γινόταν 255 στην πρώτη επίσκεψη.
  ΠΙΣΤΑ      χωρίς πλατφόρμα, ένας έτοιμος διάδρομος 0 με κατεύθυνση 6 στον
             πίνακα: το rooms_rebuild δεν βρίσκει πίστα. Ως το βήμα 89 κοίταζε
             64 «δομές», οι 32 τελευταίες ήταν ο πίνακας διαδρόμων, και ο
             διάδρομος γινόταν πίστα στον κόμβο 96 — που δεν υπάρχει.

Αρνητικά, με το snapshot πειραγμένο: χωρίς τη γραμμή του HUD (η ΑΡΧΗ), χωρίς
το γέμισμα στην έξοδο (η ΕΞΟΔΟΣ), χωρίς airlock στο su_lock (η ΕΠΙΣΤΡΟΦΗ:
πεθαίνει), ο μετρητής του HUD που μετρά μόνο όταν φαίνεται (η ΕΠΙΣΤΡΟΦΗ),
το lks_out χωρίς το F_INDOORS (ο ΜΕΤΕΩΡΙΤΗΣ), το su_tick που γυρίζει στο
nd_d2 όπως ως το βήμα 89 (το ΕΡΓΟΤΑΞΙΟ), και 64 δομές στο rooms_rebuild (η
ΠΙΣΤΑ).
"""
import ctypes, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import test_outside as TO                                # noqa: E402
import balance as B                                      # noqa: E402
import hudread                                           # noqa: E402
import cpc                                               # noqa: E402

UNIT = 128                  # frames του τροχού ανά μονάδα στολής
MIN = 3000                  # frames σε ένα λεπτό (50 το δευτερόλεπτο)
SHIP, LOCK, DOME = 64, 65, 0
F_ALIVE, F_INDOORS, F_SUITPH = 1, 2, 64
T_NEED, NO_TASK = 254, 255
SU_TTL = 10                 # τικ του HUD (src/suit.asm)
QUARTERS = 2                # σειρά στον κατάλογο δωματίων (rm_list, src/rooms.asm)
PROBE, FLAG = 0x3E00, 0x3EFF
FAIL = []


def check(ok, msg):
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ ") + msg)
    if not ok:
        FAIL.append(msg)


class W(TO.World):
    def a(self, i):
        f = lambda o: self.b6(self.L["G_agent_fields"] + o + i)[0]
        return {"f": f(0), "role": f(128), "node": f(256), "dest": f(512),
                "edge": f(640), "task": f(896), "sleep": f(1408), "health": f(1536),
                "suit": f(1792)}

    def put(self, i, off, v):
        self.put6(self.L["G_agent_fields"] + off + i, [v])

    def t(self):
        """Ο χρόνος του τροχού σε frames (sol x sollen + frame)."""
        return self.m.peek(self.g + 51) * self.w16(64) + self.w16(52)

    def hud(self):
        return hudread.text(self.m, self.sym, 2)

    def run(self, frames, step, each):
        """Τρέχει ως `frames` του τροχού, με δείγμα ανά `step` frames οθόνης."""
        t0 = self.t()
        while self.t() - t0 < frames:
            self.m.run_frames(step)
            if each() is False:
                return False
        return True

    def probe(self, body):
        m = self.m
        code = ([0xF3, 0x31, 0x00, 0x01, 0x01, 0xC6, 0x7F, 0xED, 0x49] + body   # τράπεζα 6
                + [0x3E, 0x5A, 0x32, FLAG & 255, FLAG >> 8, 0x18, 0xFE])
        m.write_ram(PROBE, bytes(code))
        m.poke(FLAG, 0)
        m.set_pc(PROBE)
        for _ in range(2000):
            m.run_us(100)
            if m.peek(FLAG) == 0x5A:
                return True
        return False


def call(sym, name):
    a = sym[name]
    return [0xCD, a & 255, a >> 8]


def start(sym, g, patch=(), quiet=False):
    """ΑΡΧΗ. Η πρώτη διαφορά από την πρόζα, ή None."""
    w = W(sym, g, patch)
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    m = w.m
    m.poke(sym["UI_SPD"], 4)
    crew = [w.a(i) for i in range(4)]
    if any(abs(c["suit"] * UNIT - 10 * MIN) > 4 * UNIT for c in crew):
        return f"ΑΡΧΗ: στολές {[c['suit'] for c in crew]} — η πρόζα λέει δέκα λεπτά"
    # Ο ΡΥΘΜΟΣ, σε 50 μονάδες: ο αέρας του καθενός ως συνάρτηση του χρόνου.
    t0, s0 = w.t(), [c["suit"] for c in crew]
    seen = {"hud": set(), "moved": []}

    def look():
        seen["hud"].add("SUIT AIR LOW" in w.hud())
        for i in range(4):
            x = w.a(i)
            if (x["node"], x["dest"], x["edge"]) != (SHIP, SHIP, 255):
                seen["moved"].append((i, x))
    w.run(50 * UNIT, 8, look)
    dt = w.t() - t0
    got = [s0[i] - w.a(i)["suit"] for i in range(4)]
    if any(abs(k * UNIT - dt) > 2 * UNIT for k in got):
        return f"ΑΡΧΗ: σε {dt} frames οι στολές έπεσαν {got} — μία μονάδα ανά {UNIT}"
    if seen["moved"] or True in seen["hud"]:
        return (f"ΑΡΧΗ: με αέρα για λεπτά, κινήθηκαν {seen['moved'][:2]}, "
                f"SUIT AIR LOW {True in seen['hud']}")
    say(f"ΑΡΧΗ: στολές {s0} ({s0[0] * UNIT / MIN:.1f} λεπτά), σε {dt} frames "
        f"έπεσαν {got} μονάδες, κανείς δεν κουνήθηκε, το HUD σιωπηλό")
    # ΤΟ ΤΕΛΟΣ: ο 0 με τρεις μονάδες, ο 1 με ένα λεπτό και λίγο. Χωρίς airlock
    # κανείς δεν πάει πουθενά· ο 0 πεθαίνει όταν αδειάσει, όχι νωρίτερα.
    hp = w.a(0)["health"]
    m.poke(sym["UI_SPD"], 1)                 # x1: το HUD ανά 16 frames του τροχού
    w.put(0, 1792, 3)
    w.put(1, 1792, (MIN // UNIT) + 2)
    log = []

    def end():
        x0, x1 = w.a(0), w.a(1)
        log.append((w.t(), x0["f"] & 1, x0["suit"], x0["health"], x1["suit"],
                    "SUIT AIR LOW" in w.hud(), x1["dest"]))
        return bool(x0["f"] & 1)
    t1 = w.t()
    w.run(20 * UNIT, 4, end)
    alive = [r for r in log if r[1]]
    dead = [r for r in log if not r[1]]
    if not dead:
        return f"ΑΡΧΗ: ο 0 δεν πέθανε με άδεια στολή: {log[-3:]}"
    if alive and (alive[-1][2] > 1 or alive[-1][3] < hp):
        return (f"ΑΡΧΗ: ο 0 πριν πεθάνει: στολή {alive[-1][2]}, υγεία {alive[-1][3]} από "
                f"{hp} — πεθαίνει όταν αδειάσει, με την υγεία ανέγγιχτη")
    if abs(dead[0][0] - t1 - 3 * UNIT) > 2 * UNIT:
        return f"ΑΡΧΗ: τρεις μονάδες κράτησαν {dead[0][0] - t1} frames, όχι {3 * UNIT}"
    # Το HUD το λέει ως 16 frames μετά την επίσκεψη (ένα τικ του): τα τέσσερα
    # πρώτα δείγματα είναι χάρη.
    low = [r for r in log if r[4] * UNIT < MIN]
    if len(low) < 16 or not all(r[5] for r in low[4:]) or any(r[6] != SHIP for r in log):
        return (f"ΑΡΧΗ: ο 1 κάτω από ένα λεπτό: {[(r[4], r[5], r[6]) for r in log[-4:]]} — "
                f"θέλει SUIT AIR LOW, και να μένει στο σκάφος (κανένα airlock)")
    say(f"ΑΡΧΗ: ο 0 πέθανε {dead[0][0] - t1} frames μετά από τρεις μονάδες, υγεία "
        f"{alive[-1][3] if alive else hp} ως το τέλος· ο 1 κάτω από ένα λεπτό: SUIT AIR LOW, "
        f"μένει στο σκάφος")
    return None


def base(sym, g, patch=(), quiet=False):
    """Θόλος και airlock, όπως στο test_outside. -> (κόσμος, ή λάθος)."""
    w = W(sym, g, patch)
    m = w.m
    B.build(m, sym, 0, g + 6, at=TO.DOME_AT, room=0, fit=False)
    if w.wait(lambda: w.dome_state() == TO.DS_ACTIVE, 20000) is None:
        return None, "ο θόλος δεν τελείωσε"
    B.build(m, sym, 9, g + 6, at=TO.LOCK_AT, fit=False)
    if w.wait(lambda: w.lock()[4] == TO.DS_ACTIVE, 20000) is None:
        return None, "το airlock δεν τελείωσε"
    m.run_frames(20)
    return w, None


def trip(sym, g, patch=(), quiet=False):
    """ΕΞΟΔΟΣ και ΕΠΙΣΤΡΟΦΗ. Η πρώτη διαφορά από την πρόζα, ή None."""
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    w, why = base(sym, g, patch, quiet)
    if why:
        return why
    m = w.m
    inside = [i for i in range(4) if w.a(i)["f"] & 3 == 3 and w.a(i)["edge"] == 255]
    if not inside:
        return f"κανείς μέσα μετά το airlock: {[w.a(i) for i in range(4)]}"
    i = inside[0]
    w.put(i, 1792, 5)
    w.put(i, 512, SHIP)
    out = []

    def step():
        x = w.a(i)
        if x["f"] & 3 == F_ALIVE:
            out.append(x["suit"])
    if w.wait(lambda: (w.a(i)["node"], w.a(i)["edge"]) == (SHIP, 255), 6000, 2, step) is None:
        return f"ΕΞΟΔΟΣ: ο {i} δεν έφτασε στο σκάφος: {w.a(i)}"
    if not out or abs(out[0] * UNIT - 3 * MIN) > 2 * UNIT:
        return f"ΕΞΟΔΟΣ: στο έδαφος η στολή του {i} ήταν {out[:3]} — τρία λεπτά, όχι το 5 που είχε"
    say(f"ΕΞΟΔΟΣ: ο {i} μέσα με στολή 5, στο έδαφος {out[0]} ({out[0] * UNIT / MIN:.1f} λεπτά)")
    # ΕΠΙΣΤΡΟΦΗ: στο σκάφος, έξω· η επόμενη επίσκεψη τον ρίχνει κάτω από ένα λεπτό
    lim = MIN // UNIT
    w.put(i, 1792, lim + 1)
    w.put(i, 0, w.a(i)["f"] | F_SUITPH)
    trail, hud = [], set()

    def back():
        x = w.a(i)
        hud.add(w.hud()[20:40].strip())
        k = (x["node"], x["edge"] == 255, bool(x["f"] & F_INDOORS), x["task"], x["dest"])
        if not trail or trail[-1] != k:
            trail.append(k)
    if w.wait(lambda: w.a(i)["f"] & 3 == 3 and w.a(i)["task"] != T_NEED, 8000, 4, back) is None:
        return f"ΕΠΙΣΤΡΟΦΗ: ο {i}: {w.a(i)}, διαδρομή {trail[-6:]}"
    if not any(t[3] == T_NEED and t[4] == LOCK and not t[2] for t in trail):
        return f"ΕΠΙΣΤΡΟΦΗ: έξω χωρίς T_NEED προς το airlock: {trail}"
    x = w.a(i)
    if not x["f"] & F_ALIVE or x["node"] != LOCK:
        return f"ΕΠΙΣΤΡΟΦΗ: τέλος {x}"
    # Η γραμμή: SUIT AIR LOW, ή κάτι που σκοτώνει όλους (§9.2) — εδώ ο θόλος
    # δεν έχει γεννήτρια και λέει NO OXYGEN. Και ο μετρητής του SUIT AIR LOW
    # σβήνει όσο το λέει: ως τη διόρθωση του βήματος 90 έμενε παγωμένος, και
    # το SUIT AIR LOW θα έβγαινε όταν ερχόταν το οξυγόνο, για κάποιον μέσα.
    if not hud or not hud <= {"SUIT AIR LOW", "NO OXYGEN", "NO POWER"}:
        return f"ΕΠΙΣΤΡΟΦΗ: η γραμμή όσο ήταν έξω με λίγο αέρα: {hud}"
    w.m.run_frames(SU_TTL * 16 + 16)
    left = w.m.peek(sym["SU_ALARM"])
    if left:
        return f"ΕΠΙΣΤΡΟΦΗ: μέσα από {SU_TTL * 16 + 16} frames, ο μετρητής του SUIT AIR LOW είναι {left}"
    say(f"ΕΠΙΣΤΡΟΦΗ: κάτω από ένα λεπτό ο {i} άφησε το σκάφος για το airlock (T_NEED), "
        f"μπήκε, και είναι πάλι διαθέσιμος· η γραμμή: {sorted(hud)}, και ο μετρητής "
        f"της έσβησε όταν μπήκε")
    return None


def meteor(sym, g, patch=(), quiet=False):
    """ΜΕΤΕΩΡΙΤΗΣ. Η πρώτη διαφορά από την πρόζα, ή None."""
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    w, why = base(sym, g, patch, quiet)
    if why:
        return why
    m = w.m
    m.poke(sym["UI_SPD"], 0)
    m.run_frames(4)
    # Κάποιος στέκεται στο airlock (ο χτίστης του, ή τον βάζουμε), μέσα.
    at = [i for i in range(4) if (w.a(i)["node"], w.a(i)["edge"]) == (LOCK, 255)]
    if not at:
        return f"ΜΕΤΕΩΡΙΤΗΣ: κανείς στο airlock: {[w.a(i) for i in range(4)]}"
    before = {i: w.a(i) for i in range(4)}
    mk = w.L["G_node_occ"] + 128
    for i in range(4):
        w.put6(mk + i, [0])
    if not w.probe([0x3E, LOCK] + call(sym, "LK_AIR_OUT")):
        return "ΜΕΤΕΩΡΙΤΗΣ: το lk_air_out δεν γύρισε"
    for i in range(4):
        x, y = before[i], w.a(i)
        mark = w.b6(mk + i)[0]
        if i in at:
            if y["f"] & F_INDOORS or abs(y["suit"] * UNIT - 3 * MIN) > 2 * UNIT or not mark:
                return f"ΜΕΤΕΩΡΙΤΗΣ: ο {i} στο airlock: {x} -> {y}, σημάδι {mark}"
        elif y != x or mark:
            return f"ΜΕΤΕΩΡΙΤΗΣ: ο {i} αλλού άλλαξε: {x} -> {y}, σημάδι {mark}"
    say(f"ΜΕΤΕΩΡΙΤΗΣ: οι {at} στο airlock βγήκαν έξω με γεμάτη στολή, οι άλλοι ίδιοι")
    return None


def site(sym, g, patch=(), quiet=False):
    """ΕΡΓΟΤΑΞΙΟ. Η πρώτη διαφορά από την πρόζα, ή None."""
    w = W(sym, g, patch)
    m = w.m
    B.build(m, sym, 0, g + 6, at=TO.DOME_AT, room=QUARTERS, fit=False)

    def there():
        return [i for i in range(4) if (w.a(i)["node"], w.a(i)["edge"]) == (DOME, 255)
                and w.a(i)["f"] & 3 == F_ALIVE and w.dome_state() != TO.DS_ACTIVE]
    if w.wait(there, 20000, 4) is None:
        return "ΕΡΓΟΤΑΞΙΟ: κανείς δεν στάθηκε στο εργοτάξιο του κοιτώνα"
    i = there()[0]
    w.put(i, 1408, 10)                      # ύπνος
    log = []

    def look():
        x = w.a(i)
        log.append((i in there(), x["sleep"]))
    w.wait(lambda: i not in there(), 1200, 4, look)
    stood = [z for k, z in log if k]
    # Μία επίσκεψη τουλάχιστον εκεί (ο ύπνος έπεσε), και ποτέ πάνω από το 10.
    if not stood or min(stood) == 10 or max(stood) > 10:
        return (f"ΕΡΓΟΤΑΞΙΟ: ο {i} στο εργοτάξιο του κοιτώνα, έξω, με ύπνο 10: "
                f"{stood[:6]}…{stood[-3:]} σε {len(stood)} δείγματα — το εργοτάξιο δεν κοιμίζει")
    if not quiet:
        print(f"    ΕΡΓΟΤΑΞΙΟ: ο {i} στάθηκε {4 * len(stood)} frames στο εργοτάξιο του "
              f"κοιτώνα, έξω· ο ύπνος του 10 -> {stood[-1]}")
    return None


def pad(sym, g, patch=(), quiet=False):
    """ΠΙΣΤΑ. Η πρώτη διαφορά από την πρόζα, ή None."""
    w = W(sym, g, patch)
    c = w.L["G_corr_tbl"]
    w.put6(c, [0, 1, 6, 2, TO.DS_ACTIVE])
    if not w.probe(call(sym, "ROOMS_REBUILD")):
        return "ΠΙΣΤΑ: το rooms_rebuild δεν γύρισε"
    p = w.m.peek(w.g + 81)
    if p != 255:
        return f"ΠΙΣΤΑ: χωρίς πλατφόρμα, πίστα ο κόμβος {p} — ο διάδρομος 0 διαβάστηκε ως δομή"
    if not quiet:
        print("    ΠΙΣΤΑ: χωρίς πλατφόρμα και με τον διάδρομο 0 = (0, 1, 6, 2, έτοιμος): καμία πίστα")
    return None


def main():
    sym, g = TG.build()
    for fn, what in ((start, "ΑΡΧΗ: δέκα λεπτά, μία μονάδα ανά 128 frames, θάνατος όταν "
                             "αδειάσει, SUIT AIR LOW κάτω από ένα λεπτό"),
                     (trip, "ΕΞΟΔΟΣ και ΕΠΙΣΤΡΟΦΗ: γεμάτη στολή στην έξοδο, μόνος του "
                            "στο airlock με ένα λεπτό"),
                     (meteor, "ΜΕΤΕΩΡΙΤΗΣ: όσοι στέκονταν στο airlock, έξω με στολή"),
                     (site, "ΕΡΓΟΤΑΞΙΟ: έξω κανένα δωμάτιο δεν δίνει τίποτα"),
                     (pad, "ΠΙΣΤΑ: οι δομές είναι 32")):
        why = fn(sym, g)
        check(why is None, why or what)

    # --- αρνητικά ---
    m = B.boot(sym, TG.SNA)

    def find(at, pat, n=64):
        return next((at + k for k in range(n)
                     if list(m.read_ram(at + k, len(pat))) == pat), None)
    w = lambda a: [a & 255, a >> 8]
    ag7 = (TO.layout()["G_agent_fields"] >> 8) + 7
    hd = find(sym["HUD_ALERT"], [0x3A] + w(sym["SU_ALARM"]), 160)  # ld a,(su_alarm)
    fl = find(sym["EMD_PUT"], [0x26, ag7, 0x36], 40)
    lk = find(sym["SU_TICK"], [0xCD] + w(sym["SU_LOCK"]), 96)
    sh = find(sym["HUD_ALERT"], [0xCD] + w(sym["SU_HUD"]), 8)
    lo = find(sym["LKS_OUT"], [0xCB, 0x8E], 8)                  # res 1,(hl)
    rr = find(sym["ROOMS_REBUILD"], [0x01, 64, 32], 200)        # ld bc,32*256+64
    # το su_tick γυρίζει στο nd_d2, όπως ως το βήμα 89: ξανά το nd_sat έξω
    ld = find(sym["SU_TICK"], [0xC3] + w(sym["ND_LOAD"]), 200)
    while ld is not None and find(ld + 1, [0xC3] + w(sym["ND_LOAD"]), 8) is not None:
        ld = find(ld + 1, [0xC3] + w(sym["ND_LOAD"]), 8)      # το τελευταίο jp
    for label, fn, patch in (
            ("χωρίς τη γραμμή του HUD", start, hd and [(hd, 0xAF), (hd + 1, 0), (hd + 2, 0)]),
            ("χωρίς γέμισμα στην έξοδο", trip, fl and [(fl + k, 0) for k in range(4)]),
            ("ο μετρητής του HUD μόνο όταν φαίνεται", trip, sh and [(sh + k, 0) for k in range(3)]),
            ("χωρίς airlock στο su_lock", trip, lk and [(lk, 0x3E), (lk + 1, 0xFF), (lk + 2, 0)]),
            ("το lks_out χωρίς το F_INDOORS", meteor, lo and [(lo, 0), (lo + 1, 0)]),
            ("64 δομές στο rooms_rebuild", pad, rr and [(rr + 2, 64)]),
            ("το nd_sat και έξω", site, ld and [(ld + 1 + k, v) for k, v in enumerate(w(sym["ND_D2"]))])):
        if not patch:
            check(False, f"δεν βρέθηκε πού να πειραχτεί για «{label}»")
            continue
        why = fn(sym, g, patch, quiet=True)
        check(why is not None, f"ΑΡΝΗΤΙΚΟ: με «{label}» αποτυγχάνει ({(why or '')[:100]})")

    if FAIL:
        print(f"\nΑΠΟΤΥΧΙΑ — {len(FAIL)}")
        return 1
    print("\nOK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
