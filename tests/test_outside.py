#!/usr/bin/env python3
"""Μέσα και έξω (βήμα 87, DESIGN §6.2, §6.6, §6.9, §10.1), στο main.sna.

Το παιχνίδι ξεκινά άδειο δίπλα στο σκάφος, και ό,τι χτίζεται χτίζεται από έξω.
Ένα σενάριο όπως το παίζει ο παίκτης — ο πρώτος θόλος, μετά το airlock του,
μετά ένας άποικος που μπαίνει — και σε κάθε βήμα ό,τι λέει η πρόζα:

  ΑΡΧΗ      τέσσερις άποικοι στο σκάφος (κόμβος 64), όλοι ΕΞΩ (χωρίς
            F_INDOORS), το σκάφος χωρίς ακμή, και η ζήτηση οξυγόνου 0: έξω
            αναπνέουν από τη στολή.
  ΘΟΛΟΣ     ο πρώτος θόλος μπαίνει μόνος του (κανένας διάδρομος) και δένεται
            στο έδαφος με το σκάφος: 0 <-> 64. Ο μηχανικός δουλεύει στο
            εργοτάξιο ΕΞΩ. Μόλις τελειώσει ο θόλος σφραγίζεται: καμία ακμή
            του, και ο μηχανικός είναι πίσω στο σκάφος, έξω, με προορισμό
            εκεί — αλλιώς θα είχε κλειδωθεί στον μόνο θόλο χωρίς πόρτα.
  AIRLOCK   το airlock κάτω από τον θόλο παίρνει τον διάδρομό του στον πίνακα
            και σημειώνεται ST_JOINED, δένεται στο έδαφος με το σκάφος, αλλά
            ο διάδρομος ΔΕΝ είναι ακόμη ακμή: το εργοτάξιο δεν έχει αέρα. Μόλις
            τελειώσει, ο διάδρομος γίνεται ακμή και ο χτίστης στέκεται ΜΕΣΑ.
  ΜΠΑΙΝΕΙ   ένας άποικος από το σκάφος στον θόλο: σκάφος -> airlock έξω, με το
            οξυγόνο του ίδιο όσο περπατά στο έδαφος· στο airlock μέσα· στον
            διάδρομο και στον θόλο μέσα, και το οξυγόνο του πέφτει (η αποικία
            δεν έχει ακόμη γεννήτρια: έλλειμμα).
  ΖΗΤΗΣΗ    EC_O2USE = 2 x όσοι ζωντανοί είναι μέσα, και όχι 2 x όλοι· και
            στο έλλειμμα που φέρνουν, όσοι είναι έξω μένουν γεμάτοι.

Αρνητικά, με το snapshot πειραγμένο, το καθένα σε άλλο βήμα: ο θόλος κρατά
τη σύνδεση εδάφους, ο χτίστης μένει μέσα στον θόλο, ο διάδρομος γίνεται ακμή
στην τοποθέτηση, το airlock δεν έχει αέρα, έξω αναπνέουν, η ζήτηση μετρά όλους.
"""
import ctypes, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import balance as B                                      # noqa: E402
import cpc                                               # noqa: E402

SHIP, LOCK, DOME = 64, 65, 0
F_ALIVE, F_INDOORS = 1, 2
DS_ACTIVE, K_AIRLOCK = 2, 5
DOME_AT, LOCK_AT = (6, 2), (6, 12)                       # μισά tiles: ο θόλος S, το airlock κάτω του
ENGINEER, WALKER = 2, 0                                  # ρόλοι 0, 0, 1, 2 (§10.1)
FAIL = []


def layout():
    L = {}
    for line in open(os.path.join(ROOT, "build", "layout.asm"), encoding="utf-8"):
        p = line.split()
        if len(p) >= 3 and p[1] == "equ" and p[2].startswith("#"):
            L[p[0]] = int(p[2][1:], 16)
    return L


class World:
    def __init__(self, sym, g, patch=()):
        self.sym, self.g, self.L = sym, g, layout()
        self.m = B.boot(sym, TG.SNA)
        for at, v in patch:
            self.m.poke(at, v)
        self.b6p = cpc._lib.cpcemu_ram_ptr(self.m._h, 6)

    def b6(self, addr, n=1):
        return ctypes.string_at(ctypes.addressof(self.b6p.contents) + addr - 0x4000, n)

    def put6(self, addr, data):
        ctypes.memmove(ctypes.addressof(self.b6p.contents) + addr - 0x4000, bytes(data), len(data))

    def ag(self, i):
        a = self.L["G_agent_fields"]
        f = lambda o: self.b6(a + o + i)[0]
        return {"f": f(0), "node": f(256), "dest": f(512), "edge": f(640), "o2": f(1024)}

    def nb(self, n):
        m, L = self.m, self.L
        return [m.peek(L["G_node_adj"] + 8 * n + j) for j in range(m.peek(L["G_rt_nodes"] + n))]

    def dome_state(self):
        return self.b6(self.L["G_dome_tbl"] + 4)[0]

    def lock(self):
        return list(self.b6(self.L["G_struct_tbl"] + 8, 8))

    def corridors(self):
        c = self.L["G_corr_tbl"]
        return [list(self.b6(c + 5 * k, 5)) for k in range(96) if self.b6(c + 5 * k + 4)[0]]

    def w16(self, off):
        return self.m.peek(self.g + off) | self.m.peek(self.g + off + 1) << 8

    def wait(self, pred, frames, step=50, each=None):
        t = 0
        while t < frames:
            self.m.run_frames(step)
            t += step
            if each:
                each()
            if pred():
                return t
        return None


def scenario(sym, g, patch=(), quiet=False):
    """Το σενάριο. Η πρώτη διαφορά από την πρόζα, ή None."""
    w = World(sym, g, patch)
    m = w.m
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))

    # --- ΑΡΧΗ
    crew = [w.ag(i) for i in range(4)]
    if any(a["node"] != SHIP or a["f"] & 3 != F_ALIVE for a in crew) or w.nb(SHIP):
        return f"η αρχή: {crew}, το σκάφος με γείτονες {w.nb(SHIP)}"
    m.run_frames(100)
    if w.w16(40) != 0:                                   # EC_O2USE
        return f"η αρχή: ζήτηση οξυγόνου {w.w16(40)}, ενώ όλοι είναι έξω"

    # --- ΘΟΛΟΣ: ο πρώτος, χωρίς διάδρομο, δεμένος στο έδαφος με το σκάφος
    B.build(m, sym, 0, g + 6, at=DOME_AT, room=0, fit=False)
    m.run_frames(20)
    if w.nb(DOME) != [SHIP] or DOME not in w.nb(SHIP) or w.corridors():
        return (f"ο θόλος στο FIRE: γείτονες {w.nb(DOME)}, του σκάφους {w.nb(SHIP)}, "
                f"διάδρομοι {w.corridors()}")
    seen = {"στο εργοτάξιο, έξω": 0, "στο εργοτάξιο, μέσα": 0}

    def at_site():
        e = w.ag(ENGINEER)
        if e["node"] == DOME and e["edge"] == 255 and w.dome_state() != DS_ACTIVE:
            seen["στο εργοτάξιο, μέσα" if e["f"] & F_INDOORS else "στο εργοτάξιο, έξω"] += 1
    if w.wait(lambda: w.dome_state() == DS_ACTIVE, 20000, 25, at_site) is None:
        return f"ο θόλος δεν τελείωσε ποτέ: μηχανικός {w.ag(ENGINEER)}"
    m.run_frames(10)
    e = w.ag(ENGINEER)
    if not seen["στο εργοτάξιο, έξω"] or seen["στο εργοτάξιο, μέσα"]:
        return f"ο μηχανικός στο εργοτάξιο: {seen}"
    if w.nb(DOME) or DOME in w.nb(SHIP):
        return f"ο θόλος τελείωσε: γείτονες {w.nb(DOME)}, του σκάφους {w.nb(SHIP)} — έμεινε η σύνδεση εδάφους"
    if (e["node"], e["dest"], e["f"] & F_INDOORS) != (SHIP, SHIP, 0):
        return f"ο θόλος τελείωσε: ο μηχανικός {e} — όχι έξω στο σκάφος"
    say(f"θόλος: δεμένος στο σκάφος ως εργοτάξιο, ο μηχανικός δούλεψε έξω "
        f"({seen['στο εργοτάξιο, έξω']} δείγματα) και βγήκε στο σκάφος")

    # --- AIRLOCK: διάδρομος στον πίνακα, όχι ακόμη ακμή
    B.build(m, sym, 9, g + 6, at=LOCK_AT, fit=False)
    m.run_frames(20)
    lk, cr = w.lock(), w.corridors()
    if lk[2] != K_AIRLOCK or lk[6] != 1 or len(cr) != 1 or cr[0][:2] != [DOME, LOCK]:
        return f"το airlock στο FIRE: εγγραφή {lk}, διάδρομοι {cr}"
    if w.nb(LOCK) != [SHIP] or w.nb(DOME):
        return (f"το airlock στο FIRE: γείτονες {w.nb(LOCK)} (θέλει [{SHIP}], το έδαφος), "
                f"του θόλου {w.nb(DOME)} (θέλει κανέναν: ο διάδρομος περιμένει)")
    if w.wait(lambda: w.lock()[4] == DS_ACTIVE, 20000) is None:
        return f"το airlock δεν τελείωσε ποτέ: {w.lock()}"
    m.run_frames(10)
    if w.nb(DOME) != [LOCK] or sorted(w.nb(LOCK)) != sorted([SHIP, DOME]):
        return f"το airlock τελείωσε: γείτονες {w.nb(LOCK)}, του θόλου {w.nb(DOME)}"
    e = w.ag(ENGINEER)
    if (e["node"], e["f"] & F_INDOORS) != (LOCK, F_INDOORS):
        return f"το airlock τελείωσε: ο χτίστης {e} — όχι μέσα στο airlock"
    say("airlock: ο διάδρομος στον πίνακα από το FIRE, ακμή μόνο όταν τελείωσε· "
        "ο χτίστης μέσα")

    # --- ΜΠΑΙΝΕΙ: από το σκάφος στον θόλο
    a = w.ag(WALKER)
    if a["node"] != SHIP or a["edge"] != 255:
        return f"ο άποικος {WALKER} δεν είναι στο σκάφος: {a}"
    o2_0 = a["o2"]
    if o2_0 != 255:
        return (f"ο άποικος {WALKER} έχει οξυγόνο {o2_0} μετά από δύο κτίσματα στο σκάφος: "
                f"έξω δεν ξοδεύει, και ξεκίνησε γεμάτος")
    w.put6(w.L["G_agent_fields"] + 512 + WALKER, [DOME])
    trail, outside = [], []

    def step():
        a = w.ag(WALKER)
        where = ("ακμή", a["node"]) if a["edge"] != 255 else ("κόμβος", a["node"])
        if not a["f"] & F_INDOORS:
            outside.append(a["o2"])
        if not trail or trail[-1][:2] != where:
            trail.append(where + (bool(a["f"] & F_INDOORS), a["o2"]))
    step()
    if w.wait(lambda: (w.ag(WALKER)["node"], w.ag(WALKER)["edge"]) == (DOME, 255),
              6000, 2, step) is None:
        return f"ο άποικος δεν έφτασε στον θόλο: {w.ag(WALKER)}, διαδρομή {trail}"
    m.run_frames(300)
    step()
    want = [("κόμβος", SHIP, False), ("ακμή", SHIP, False), ("κόμβος", LOCK, True),
            ("ακμή", LOCK, True), ("κόμβος", DOME, True)]
    if [t[:3] for t in trail] != want:
        return f"η διαδρομή του αποίκου: {trail}, η πρόζα λέει {want}"
    if any(v != o2_0 for v in outside):
        return (f"το οξυγόνο του έξω: {sorted(set(outside))}, ξεκίνησε {o2_0} — έξω δεν "
                f"ξοδεύει (ως το 89)")
    if trail[-1][3] >= o2_0:
        return f"το οξυγόνο του στον θόλο: {trail[-1][3]} από {o2_0} — μέσα, σε έλλειμμα, πέφτει"
    say(f"άποικος: γεμάτος μετά από δύο κτίσματα έξω, σκάφος -> airlock έξω "
        f"({len(outside)} δείγματα, οξυγόνο {o2_0}), airlock -> θόλος μέσα "
        f"(οξυγόνο {trail[-1][3]})")

    # --- ΖΗΤΗΣΗ
    m.run_frames(40)
    inside = sum(1 for i in range(128) if w.ag(i)["f"] & 3 == 3)
    alive = sum(1 for i in range(128) if w.ag(i)["f"] & 1)
    if w.w16(40) != 2 * inside or inside == alive:
        return f"η ζήτηση οξυγόνου {w.w16(40)}: {inside} μέσα από {alive} ζωντανούς"
    # Σε έλλειμμα (καμία γεννήτρια ακόμη) όσοι είναι έξω μένουν γεμάτοι: όσο
    # φτάνει το οξυγόνο η ροή θα τους ξαναγέμιζε ούτως ή άλλως, και μόνο εδώ
    # φαίνεται αν η στολή «αναπνέει» από την αποικία.
    out_o2 = [w.ag(i)["o2"] for i in range(128) if w.ag(i)["f"] & 3 == F_ALIVE]
    if m.peek(g + 47) != 0 or not out_o2 or any(v != 255 for v in out_o2):
        return (f"σε έλλειμμα (EC_O2OK {m.peek(g + 47)}) όσοι είναι έξω: οξυγόνο {out_o2} — "
                f"έξω δεν ξοδεύουν")
    say(f"ζήτηση: {w.w16(40)} = 2 x {inside} μέσα, από {alive} ζωντανούς· σε έλλειμμα "
        f"οι {len(out_o2)} έξω μένουν στο 255")
    return None


def find(m, at, pat, span):
    code = m.read_ram(at, span + len(pat))
    k = next((k for k in range(span) if list(code[k:k + len(pat)]) == pat), None)
    assert k is not None, f"το μοτίβο {pat} δεν βρέθηκε μετά το #{at:04X}"
    return at + k


def main():
    sym, g = TG.build()
    err = scenario(sym, g)
    check = lambda ok, msg: (print(("OK " if ok else "ΛΑΘΟΣ ") + msg), ok or FAIL.append(msg))
    check(err is None, err or "μέσα και έξω: θόλος από έξω, airlock-πόρτα, άποικος που μπαίνει")

    m = B.boot(sym, TG.SNA)
    w = lambda a: [a & 255, a >> 8]
    cut = find(m, sym["LK_DONE"], [0xCD] + w(sym["LK_CUT"]), 40)
    out = find(m, sym["LK_DONE"], [0xCD] + w(sym["LK_OUT"]), 40)
    neg = [("ο θόλος κρατά τη σύνδεση εδάφους", [(cut + k, 0) for k in range(3)]),
           ("ο χτίστης μένει μέσα στον θόλο", [(out + k, 0) for k in range(3)]),
           # το cr_commit καλεί το cr_link στη θέση του cr_pay: ο διάδρομος
           # γίνεται ακμή στην τοποθέτηση, όπως ως το βήμα 86
           ("ο διάδρομος γίνεται ακμή στην τοποθέτηση",
            [(find(m, sym["CR_COMMIT"], [0xCD] + w(sym["CR_PAY"]), 120) + 1 + k, v)
             for k, v in enumerate(w(sym["CR_LINK"]))]),
           # en_in: cp K_AIRLOCK γίνεται cp 255
           ("το airlock δεν έχει αέρα", [(find(m, sym["EN_IN"], [0xFE, K_AIRLOCK], 40) + 1, 255)]),
           # nd_def: rr e · jr nc,nd_d2 — το jr γίνεται nop nop
           ("έξω αναπνέουν", [(find(m, sym["ND_DEF"], [0xCB, 0x1B, 0x30], 16) + 2 + k, 0)
                              for k in range(2)]),
           # ef_o2: ld l,e γίνεται ld l,c — η ζήτηση από όλους τους ζωντανούς
           ("η ζήτηση μετρά όλους", [(find(m, sym["EF_ALIVE"], [0x6B], 4), 0x69)])]
    for label, patch in neg:
        err = scenario(sym, g, patch, quiet=True)
        check(err is not None, f"ΑΡΝΗΤΙΚΟ «{label}»: " + (err[:110] if err else "ΔΕΝ το έπιασε τίποτα"))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
