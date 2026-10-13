#!/usr/bin/env python3
"""ΕΝΑΣ ΠΑΙΚΤΗΣ-ΣΕΝΑΡΙΟ ΑΠΟ ΤΗΝ ΑΔΕΙΑ ΑΡΧΗ (βήμα 120, DESIGN §6.5).

Το tools/balance.py μετρούσε την αποικία δοκιμών του §10.1, που από το βήμα 87
δεν είναι πια η αρχή του παιχνιδιού. Εδώ τρέχει το main.sna όπως το βλέπει ο
παίκτης — τέσσερις άποικοι έξω, δίπλα στο σκάφος, με 189 μέταλλο και 107
βιοπλαστικό — και ένα σενάριο το παίζει με τα ΠΛΗΚΤΡΑ του: κατάλογος, θέση,
FIRE, εξοπλισμός υποδοχή-υποδοχή, C και FIRE για πλοίο. Στο x4.

Το σχέδιο είναι μια λίστα σταδίων. Ενα στάδιο περιμένει να το αγοράζουν τα
αποθέματα, να έχει τελειώσει ό,τι ζητά πριν από αυτό, και να μην υπάρχουν
περισσότερα από OPEN εργοτάξια· τότε χτίζεται, στη φθηνότερη θέση κοντά στον
στόχο του που περνά τον κανόνα του tools/reach.py (λιγότερα κομμάτια
διαδρόμου, μετά η απόσταση).

Κάθε 1/8 του sol ένα δείγμα: αποθέματα, ρεύμα, οξυγόνο, εργοτάξια, και οι
ανάγκες του καθενός. Ενας θάνατος γράφεται με την αιτία του, από το τελευταίο
δείγμα πριν: στολή, αέρας, δίψα, πείνα.

    python3 tools/play.py [--planet P] [--seed S] [--sols N] [--plan ΟΝΟΜΑ]
"""
import argparse, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, "/home/vasilhs/cpcemu")

import balance as B                                      # noqa: E402
import reach                                             # noqa: E402

RASM = os.path.expanduser("~/rasm/rasm.exe")
PER_SOL = 3000                     # πραγματικά frames ανά sol στο x4: 4 ανά frame
STEP = PER_SOL // 8
OPEN = 2                           # εργοτάξια ταυτόχρονα, το πολύ
STOCKS = ["νερό", "τροφή", "μετάλλ", "μέταλ", "βιοπλ", "επεξ", "ανταλ", "φάρμ",
          "όπλα", "ρομπ", "άμυλο", "λαχαν", "βότ", "κρέας"]
S_WATER, S_FOOD, S_ORE, S_METAL, S_BIOPL = 0, 1, 2, 3, 4
O2_PER_COL = 2                     # tools/econ.py O2_PER_COLONIST
ROOM = dict(oxygen=0, canteen=1, quarters=2, green=3, factory=4, lab=5, medbay=6,
            control=7, storage=8, lounge=9)
OXYGEN, METAL, PLASTIC, WEAPONS, CHIPS, ROBOTS, MEALS, SPARES, DRUGS, MEAT = range(10)
STARCH, VEG, HERBS, TREE = 250, 251, 252, 253
DOME_S, DOME_M, DOME_L, CORR, SOLAR, TURBINE, COLLECTOR, EXTRACTOR, MINE, AIRLOCK, PAD = range(11)
COST = {DOME_S: (12, 8), DOME_M: (24, 14), DOME_L: (40, 24), SOLAR: (15, 0),
        TURBINE: (18, 0), COLLECTOR: (14, 0), EXTRACTOR: (22, 0), MINE: (30, 0),
        AIRLOCK: (10, 6), PAD: (45, 0)}
DS_BUILDING, DS_ACTIVE = 1, 2
MINE_K = 4                         # K_MINE, το είδος της δομής
R_GREEN = 5                        # D_ROOM του θερμοκηπίου: οι υποδοχές του είναι φυτά
R_STORAGE = 6                      # D_ROOM της αποθήκης (το ROOM είναι η σειρά του καταλόγου)
STRUCT_NAMES = ["ηλιακός", "ανεμογ.", "συλλέκτης", "αντλία", "ορυχείο", "airlock", "πίστα",
                "σκάφος"]
MACH_NAMES = ["OXYGEN", "METAL", "PLASTIC", "WEAPONS", "CHIPS", "ROBOTS", "MEALS", "SPARES",
              "DRUGS", "MEAT", "BEDS", "CABINET"]
SHIP_KINDS = ["άποικοι", "έμπορος", "επισκέπτες", "έμπορος (συμφωνία)", "εισβολείς"]
ROLES = ["εργάτης", "μηχανικός", "βιολόγος", "γιατρός", "φρουρός", "ρ.κατασκ", "ρ.μεταφ", "ρ.γεωτρ"]


# --------------------------------------------------------------------------
# ο κόσμος
# --------------------------------------------------------------------------
def syms():
    sym = {}
    for line in open(os.path.join(ROOT, "src", "rasmoutput.sym"), encoding="utf-8",
                     errors="replace"):
        p = line.split()
        if len(p) >= 2 and p[1].startswith("#"):
            sym[p[0].upper()] = int(p[1][1:], 16)
    return sym, layout()["G_econ_state"]


def sna_path(seed, planet):
    return os.path.join(ROOT, "build", f"play_{seed:04x}_{planet}.sna")


def make(pairs):
    """build/play_SSSS_P.sna: το main.sna με τον κόσμο (seed, planet). Το
    build/world_new.bin ξαναγίνεται ο κανονικός στο τέλος."""
    import test_game as TG
    import worldgen_ref as Wg
    import mknew
    TG.build()
    world = os.path.join(ROOT, "build", "world_new.bin")
    try:
        for seed, planet in pairs:
            open(world, "wb").write(bytes(Wg.generate(seed, planet).buf))
            out = sna_path(seed, planet)
            r = subprocess.run([RASM, "main.asm", "-oi", out, "-v2", "-s",
                                "-eo"], cwd=os.path.join(ROOT, "src"), capture_output=True,
                               text=True)
            if r.returncode:
                sys.exit("rasm απέτυχε:\n" + r.stdout + r.stderr)
            # ΚΑΙ ΤΟ G_worldinfo, όπως το αφήνει η γεννήτρια του δίσκου (src/gen.asm):
            # από το βήμα 120 τα συμβάντα βγαίνουν από αυτό, και με μηδέν (το
            # main.sna) κάθε κόσμος θα είχε τις καταστροφές του #ACE1. SNA v2:
            # κεφαλίδα 256 bytes, η βασική μνήμη, και μετά οι τράπεζες 4-7.
            wi = layout()["G_worldinfo"] - 0x4000
            d = bytearray(open(out, "rb").read())
            at = 0x100 + 0x10000 + 2 * 0x4000 + wi
            d[at:at + 3] = bytes([seed & 255, seed >> 8, planet])
            open(out, "wb").write(bytes(d))
    finally:
        mknew.build()
        TG.build()


def layout():
    L = {}
    for line in open(os.path.join(ROOT, "build", "layout.asm"), encoding="utf-8"):
        p = line.split()
        if len(p) >= 3 and p[1] == "equ" and p[2].startswith("#"):
            L[p[0]] = int(p[2][1:], 16)
    return L


def econ_at(g):
    const = open(os.path.join(ROOT, "src", "const.asm"), encoding="utf-8").read()
    X = {n: g + int(k) for n, k in
         re.findall(r"^(EC_\w+)\s+equ\s+G_econ_state\s*\+\s*(\d+)", const, re.M)}
    X["EC_STOCK"] = g
    return X


def is_res(b, kind):
    import world as W
    c = W.cls_of(b)
    if kind == "water":
        return c in (W.WATER, W.DEEPWATER)
    return c == W.MOUNTAIN and (b >> 3) & 1


# --------------------------------------------------------------------------
# το παιχνίδι, με τα πλήκτρα του παίκτη
# --------------------------------------------------------------------------
class Game:
    def __init__(self, sym, g, sna):
        import cpc
        self.sym, self.g, self.cpc = sym, g, cpc
        self.m = B.boot(sym, sna)
        self.L, self.X = layout(), econ_at(g)
        self.frames, self.events, self.rows = 0, [], []
        self.alive_prev = {}
        self.built = {}                         # όνομα σταδίου -> (κόμβος, θέση)
        self.fits = []                          # [όνομα, θέση, κωδικοί] που περιμένουν υλικά
        self.spot_cache = {}
        self.m.poke(sym["UI_SPD"], 4)

    # --- μνήμη ---------------------------------------------------------------
    def w16(self, a):
        return self.m.peek(a) | (self.m.peek(a + 1) << 8)

    def stock(self, k):
        return self.w16(self.g + 2 * k)

    def bank(self, n):
        return self.cpc._lib.cpcemu_ram_ptr(self.m._h, n)

    def sol(self):
        return self.m.peek(self.X["EC_SOL"]) + self.w16(self.X["EC_FRAME"]) / 12000

    def domes(self):
        b6, d0 = self.bank(6), self.L["G_dome_tbl"] - 0x4000
        return [list(b6[d0 + 24 * d:d0 + 24 * d + 24]) for d in range(64)]

    def structs(self):
        b6, s0 = self.bank(6), self.L["G_struct_tbl"] - 0x4000
        return [list(b6[s0 + 8 * k:s0 + 8 * k + 8]) for k in range(32)]

    def state(self, node):
        if node < 64:
            return self.domes()[node][4]
        return self.structs()[node - 64][4]

    def jobs(self):
        raw = self.m.read_ram(self.L["G_job_tbl"], 160)
        return [list(raw[5 * j:5 * j + 5]) for j in range(32) if raw[5 * j] != 255]

    def agents(self):
        import entity as E
        b6, a0 = self.bank(6), self.L["G_agent_fields"] - 0x4000
        a = E.Agents().from_bytes(bytes(b6[a0:a0 + 2048]))
        return {i: {f: getattr(a, f)[i] for f in E.FIELDS} for i in range(128)
                if a.flags[i] & 1}

    def capacity(self):
        """Η αποθήκη (βήμα 122): 500 και 100/300/600 ανά θόλο Storage έτοιμο."""
        return 500 + sum((100, 300, 600)[d[2]] for d in self.domes()
                         if d[4] == DS_ACTIVE and d[3] == R_STORAGE)

    def total(self):
        return sum(self.stock(k) for k in range(1, 14))

    def oxy(self):
        """Θόλοι οξυγόνου σε λειτουργία: ο καθένας φτάνει για δέκα (§6.5)."""
        return sum(1 for d in self.domes() if d[4] == DS_ACTIVE and d[3] == 4)

    def sites(self):
        return (sum(1 for d in self.domes() if d[4] == DS_BUILDING)
                + sum(1 for s in self.structs() if s[4] == DS_BUILDING))

    # --- ο χρόνος ------------------------------------------------------------
    def run(self, frames):
        while frames > 0:
            n = min(STEP, frames)
            self.m.run_frames(n)
            self.frames += n
            frames -= n
            self.sample()

    def sample(self):
        X, w, p = self.X, self.w16, self.m.peek
        ag = self.agents()
        for i, a in self.alive_prev.items():
            if i not in ag and i < 80:
                self.event(f"ΘΑΝΑΤΟΣ {i} ({ROLES[a['role'] & 7]}): {cause(a)}")
        self.alive_prev = ag
        self.watch()
        jobs = self.jobs()
        self.rows.append(dict(
            sol=self.sol(), alive=sum(1 for i in ag if i < 80),
            bots=sum(1 for i in ag if 80 <= i < 96),
            out=sum(1 for i, a in ag.items() if i < 80 and not a["flags"] & 2),
            popcap=p(X["EC_POPCAP"]), ship=p(X["EC_SHSTATE"]),
            stock=[self.stock(k) for k in range(14)],
            pp=w(X["EC_PPROD"]), pu=w(X["EC_PUSE"]), bat=w(X["EC_PSTORE"]),
            o2p=w(X["EC_O2PROD"]), o2u=w(X["EC_O2USE"]),
            pok=p(X["EC_POK"]), o2ok=p(X["EC_O2OK"]), storm=p(X["EC_STORM"]),
            cap=self.capacity(), full=p(self.sym["EC_FULL"]),
            mines=[(s[6] & 0x0C, s[7]) for s in self.structs() if s[2] == MINE_K and s[4]],
            sites=self.sites(), jobs=len(jobs),
            jk=[j[0] for j in jobs], jfree=sum(1 for j in jobs if j[2] == 255),
            mile=p(X["EC_MILE"]),
            need={i: (a["o2"], a["water"], a["food"], a["sleep"], a["health"], a["suit"],
                      a["flags"]) for i, a in ag.items() if i < 80}))

    def watch(self):
        """Ο,τι άλλαξε από το προηγούμενο δείγμα: κτίσματα που χτυπήθηκαν,
        μηχανές που χάλασαν, βροχή, θύελλα, πλοία."""
        p = self.m.peek
        ds, ss = self.domes(), self.structs()
        now = dict(st={k: s[4] for k, s in enumerate(ss) if s[4]},
                   brk={(k, j) for k, d in enumerate(ds) if d[4] == DS_ACTIVE and d[3] != R_GREEN
                        for j in range(8) if d[8 + j] < 250 and d[16 + j] == 0},
                   met=p(self.X["EC_METEOR"]), storm=p(self.X["EC_STORM"]),
                   ship=(p(self.X["EC_SHSTATE"]), p(self.X["EC_SHKIND"])))
        was = getattr(self, "seen", None)
        self.seen = now
        if was is None:
            return
        hit = [64 + k for k, v in now["st"].items() if v == DS_BUILDING
               and was["st"].get(k) == DS_ACTIVE]
        if hit:
            names = [STRUCT_NAMES[ss[n - 64][2] & 7] for n in hit]
            self.event(f"ΧΤΥΠΗΘΗΚΑΝ: {', '.join(names)}")
        new = now["brk"] - was["brk"]
        if new:
            self.event("ΧΑΛΑΣΑΝ: " + ", ".join(
                f"{MACH_NAMES[ds[k][8 + j]]} (θόλος {k})" for k, j in sorted(new)))
        if now["met"] and not was["met"]:
            self.event("ΒΡΟΧΗ ΜΕΤΕΩΡΙΤΩΝ")
        if now["storm"] and not was["storm"]:
            self.event("ΑΜΜΟΘΥΕΛΛΑ")
        if now["ship"] != was["ship"]:
            st, kd = now["ship"]
            self.event(f"πλοίο: {['-', 'έρχεται', 'προσγειώθηκε'][st & 3]} "
                       f"({SHIP_KINDS[kd] if kd < len(SHIP_KINDS) else kd})")

    def event(self, s):
        e = f"sol {self.sol():5.2f}  {s}"
        self.events.append(e)
        print("  " + e, flush=True)

    # --- τα πλήκτρα ----------------------------------------------------------
    def stick(self, mask):
        m = self.m
        m.set_joystick_type(1)
        m.joystick(mask)
        m.run_frames(4)
        m.joystick(0)
        m.run_frames(10)
        m.set_joystick_type(0)
        self.frames += 14

    def tap(self, key):
        m = self.m
        m.key_down(key)
        m.run_frames(5)
        m.key_up(key)
        m.run_frames(8)
        self.frames += 13

    def look(self):
        for _ in range(3):
            if self.m.peek(self.sym["UI_STATE"]) == 0:
                return
            self.stick(0x20)

    def world(self):
        return bytes(self.bank(4)[:0x4000])

    def res_near(self, kind):
        """Τα tiles του υλικού, από το κοντινότερο στο σκάφος."""
        b4 = self.world()
        out = []
        for ty in range(-40, 40):
            for tx in range(-40, 40):
                if is_res(b4[reach.widx(tx, ty)], kind):
                    out.append((max(abs(tx), abs(ty)), tx, ty))
        out.sort()
        return [(2 * tx + 1, 2 * ty + 1) for _, tx, ty in out]

    def spot(self, item, near, room=None, need=True):
        """(θέση σε μισά tiles, κομμάτια διαδρόμου) για το item: η φθηνότερη
        που περνά τον κανόνα, κοντά στο near. None αν δεν υπάρχει σε 8 tiles.
        `need` = False: το ορυχείο και χωρίς φλέβα (βήμα 123, μισή απόδοση)."""
        b4 = self.world()
        domes = [d[:4] for d in self.domes()]
        structs = [s[:7] for s in self.structs()]
        dims = self.m.read_ram(self.L["G_struct_dims"], 64)
        kind, param, w, h = self.m.read_ram(self.sym["BLD_ITEMS"] + 8 * item, 4)
        tx0, ty0 = (near[0] - w) >> 1, (near[1] - h) >> 1
        best = None
        for r in range(0, 13):
            for ty in range(ty0 - r, ty0 + r + 1):
                for tx in range(tx0 - r, tx0 + r + 1):
                    if max(abs(tx - tx0), abs(ty - ty0)) != r:
                        continue
                    if not (-60 <= tx and tx + w <= 60 and -60 <= ty and ty + h <= 60):
                        continue
                    if not all(reach.ok_tile(b4[reach.widx(tx + i, ty + j)])
                               for i in range(w) for j in range(h)):
                        self.why["έδαφος"] = self.why.get("έδαφος", 0) + 1
                        continue
                    if need and item in B.NEED and not B.has_near(b4, tx, ty, w, B.NEED[item][0]):
                        continue
                    p = reach.plan(b4, domes, structs, dims, kind, param, w, h,
                                   2 * tx + w, 2 * ty + h)
                    if not p["ok"]:
                        k = f"λόγος {p['reason']}"
                        self.why[k] = self.why.get(k, 0) + 1
                        continue
                    score = (p["pieces"], r)
                    if best is None or score < best[0]:
                        best = (score, (2 * tx + w, 2 * ty + h))
            if best is not None and r >= best[0][1] + 2:
                break
        return (best[1], best[0][0]) if best else None

    def place(self, item, at, room=None):
        """Χτίζει με τα πλήκτρα. -> ο κόμβος, ή None αν δεν μπήκε."""
        d0 = [d[4] for d in self.domes()]
        s0 = [s[4] for s in self.structs()]
        try:
            ok = B.build(self.m, self.sym, item, self.g + 2 * S_METAL, at=at, room=room,
                         fit=False)
        except AssertionError as e:
            self.event(f"ΠΛΗΚΤΡΑ: {e}")
            ok = False
        self.frames += 200
        self.look()
        if not ok:
            return None
        for k, d in enumerate(self.domes()):
            if d[4] and not d0[k]:
                return k
        for k, s in enumerate(self.structs()):
            if s[4] and not s0[k]:
                return 64 + k
        return None

    def fit(self, at, codes):
        """Ο εξοπλισμός του θόλου στο at, υποδοχή-υποδοχή: codes[s] στην
        υποδοχή s (None = άφησέ την). -> οι υποδοχές που έμειναν χωρίς ό,τι
        ζητήθηκε (για αργότερα, όταν φτάσουν τα υλικά)."""
        from cpc import KEY_DOWN, KEY_UP, KEY_RIGHT, KEY_LEFT, JOY_FIRE
        m, sym = self.m, self.sym
        p = lambda n, k=0: m.peek(sym[n] + k)
        self.look()
        m.poke(sym["CUR_HX"], at[0] & 0xFF)
        m.poke(sym["CUR_HY"], at[1] & 0xFF)
        self.stick(JOY_FIRE)
        if p("UI_STATE") != B.FIT_STATE:
            self.look()
            return list(codes)
        n, c, d = p("FIT_N"), p("FIT_C"), p("FIT_D")
        lst = [p("FIT_LST", k) for k in range(c)]
        left = list(codes)
        for s, code in enumerate(codes[:n]):
            if code is None or code not in lst:
                continue
            if self.domes()[d][8 + s] == code:
                left[s] = None
                continue
            for _ in range(16):
                if p("FIT_S") == s:
                    break
                self.tap(KEY_RIGHT if (s - p("FIT_S")) % n <= n // 2 else KEY_LEFT)
            want = lst.index(code)
            for _ in range(2 * c):
                dd = (want - p("FIT_I")) % c
                if not dd:
                    break
                self.tap(KEY_DOWN if dd <= c // 2 else KEY_UP)
            self.stick(JOY_FIRE)
            if self.domes()[d][8 + s] == code:
                left[s] = None
        self.look()
        return left if any(x is not None for x in left) else []

    def call_ship(self):
        from cpc import JOY_FIRE
        self.look()
        self.m.key_down("C")
        self.m.run_frames(6)
        self.m.key_up("C")
        self.m.run_frames(40)
        self.stick(JOY_FIRE)
        self.m.run_frames(30)
        self.look()
        return self.m.peek(self.X["EC_SHSTATE"]) != 0


def cause(a):
    o2, water, food, health, suit = a["o2"], a["water"], a["food"], a["health"], a["suit"]
    where = "μέσα" if a["flags"] & 2 else "έξω"
    if not a["flags"] & 2 and suit < 24:
        return f"στολή ({suit}), {where}"
    worst = min((o2, "αέρας"), (water, "δίψα"), (food, "πείνα"))
    return (f"{worst[1]} {where} (o2 {o2}, νερό {water}, τροφή {food}, υγεία {health}, "
            f"στολή {suit})")


# --------------------------------------------------------------------------
# το σχέδιο
# --------------------------------------------------------------------------
def step(name, item, near, room=None, codes=(), after=(), when=None, again=False):
    return dict(name=name, item=item, near=near, room=room, codes=list(codes),
                after=list(after), when=when, again=again)


def room_free(G, upto=80):
    r = G.rows[-1]
    return r["ship"] == 0 and r["alive"] + 4 <= min(r["popcap"], upto)


def ship_ok(G):
    """Ενα πλοίο αποίκων (τέσσερις) μόνο όταν το οξυγόνο που ΒΓΑΙΝΕΙ — όχι οι
    θόλοι του — φτάνει σε όλο το τελευταίο sol για όλους μαζί με τους τέσσερις,
    και η τροφή φτάνει για πέντε sol και δεν πέφτει (βήμα 127). Ως τότε το
    room_free(G, 10 * G.oxy()) μετρούσε θόλους οξυγόνου: στο ACE1 3 ο ένας από
    τους δύο έμενε συχνά χωρίς χειριστή, 20 από τα 32, και πέθαναν 33."""
    rows = G.rows[-8:]                      # ένα sol: ένα δείγμα ανά όγδοο
    if len(rows) < 8 or not room_free(G):
        return False
    want = rows[-1]["alive"] + 4
    food = [r["stock"][S_FOOD] for r in rows]
    return (min(r["o2p"] for r in rows) >= O2_PER_COL * want
            and food[-1] >= 5 * want and food[-1] >= food[0])


def plan_base():
    """Ενα άνοιγμα όπως του Planetbase: αέρας, πόρτα, νερό, κυλικείο, ρεύμα,
    μέταλλο από το αρχικό μετάλλευμα (60 -> 30), και η αλυσίδα της τροφής
    (άμυλο + λαχανικά + κρέας -> γεύμα) πριν τελειώσουν τα 40 τρόφιμα. Μετά
    ορυχείο, μπαταρία, ύπνος, πληθυσμός."""
    return [
        step("ηλιακός", SOLAR, (10, -6)),
        step("οξυγόνο", DOME_S, (6, 2), "oxygen", [OXYGEN]),
        step("airlock", AIRLOCK, (6, 12), after=["οξυγόνο"]),
        step("αντλία", EXTRACTOR, "water"),
        step("κυλικείο", DOME_S, (18, 2), "canteen", after=["οξυγόνο"]),
        step("ηλιακός 2", SOLAR, (-8, 6)),
        step("εργοστάσιο", DOME_S, (6, -10), "factory", [METAL], after=["οξυγόνο"]),
        step("θερμοκήπιο", DOME_M, (20, 14), "green", [STARCH, STARCH, VEG, VEG],
             after=["κυλικείο"]),
        step("εργαστήριο", DOME_S, (18, -10), "lab", [MEAT], after=["κυλικείο"]),
        step("γεύματα", "fit", "κυλικείο", codes=[MEALS], after=["κυλικείο"]),
        step("ορυχείο", MINE, "ore"),
        step("συλλέκτης", COLLECTOR, (-8, -6)),
        step("ηλιακός 3", SOLAR, (-8, -14)),
        step("κοιτώνες", DOME_S, (30, 2), "quarters", after=["κυλικείο"]),
        step("έλεγχος", DOME_S, (30, -10), "control", after=["κοιτώνες"]),
        step("πίστα", PAD, (-14, -14), after=["έλεγχος"]),
        step("πλοίο", "ship", None, after=["πίστα", "έλεγχος"], when=room_free, again=True),
    ]


def plan_lean():
    """Το φθηνότερο άνοιγμα που τρέφεται: θερμοκήπια S (ένα φυτό το καθένα,
    χωρίς τον διάδρομο του M), μπαταρία πριν από το εργοστάσιο ώστε το
    οξυγόνο να τρέχει και τη νύχτα, ορυχείο όταν τελειώνει το αρχικό
    μετάλλευμα, ανταλλακτικά πριν τελειώσουν τα τέσσερα."""
    return [
        step("ηλιακός", SOLAR, (10, -6)),
        step("οξυγόνο", DOME_S, (6, 2), "oxygen", [OXYGEN]),
        step("airlock", AIRLOCK, (6, 12), after=["οξυγόνο"]),
        step("αντλία", EXTRACTOR, "water"),
        step("κυλικείο", DOME_S, (18, 2), "canteen", after=["οξυγόνο"]),
        step("συλλέκτης", COLLECTOR, (-8, -6)),
        step("εργοστάσιο", DOME_S, (6, -10), "factory", [METAL], after=["οξυγόνο"]),
        step("άμυλο", DOME_S, (20, 14), "green", [STARCH], after=["κυλικείο"]),
        step("λαχανικά", DOME_S, (20, 14), "green", [VEG], after=["κυλικείο"]),
        step("εργαστήριο", DOME_S, (18, -10), "lab", [MEAT], after=["κυλικείο"]),
        step("γεύματα", "fit", "κυλικείο", codes=[MEALS], after=["κυλικείο"]),
        step("ορυχείο", MINE, "ore"),
        step("ανταλλακτικά", DOME_S, (6, -10), "factory", [SPARES], after=["οξυγόνο"]),
        step("ηλιακός 2", SOLAR, (-8, 6)),
        step("κοιτώνες", DOME_S, (30, 2), "quarters", after=["κυλικείο"]),
        step("έλεγχος", DOME_S, (30, -10), "control", after=["κοιτώνες"]),
        step("πίστα", PAD, (-14, -14), after=["έλεγχος"]),
        step("πλοίο", "ship", None, after=["πίστα", "έλεγχος"], when=room_free, again=True),
    ]


def plan_spares():
    """Το lean με τα ανταλλακτικά αμέσως μετά το μέταλλο και τη μπαταρία
    αργότερα: τα τέσσερα της αρχής δεν φτάνουν ως την πρώτη έκλαμψη."""
    return [
        step("ηλιακός", SOLAR, (10, -6)),
        step("οξυγόνο", DOME_S, (6, 2), "oxygen", [OXYGEN]),
        step("airlock", AIRLOCK, (6, 12), after=["οξυγόνο"]),
        step("αντλία", EXTRACTOR, "water"),
        step("κυλικείο", DOME_S, (18, 2), "canteen", after=["οξυγόνο"]),
        step("εργοστάσιο", DOME_S, (6, -10), "factory", [METAL], after=["οξυγόνο"]),
        step("ανταλλακτικά", DOME_S, (6, -10), "factory", [SPARES], after=["οξυγόνο"]),
        step("άμυλο", DOME_S, (20, 14), "green", [STARCH], after=["κυλικείο"]),
        step("λαχανικά", DOME_S, (20, 14), "green", [VEG], after=["κυλικείο"]),
        step("εργαστήριο", DOME_S, (18, -10), "lab", [MEAT], after=["κυλικείο"]),
        step("γεύματα", "fit", "κυλικείο", codes=[MEALS], after=["κυλικείο"]),
        step("ορυχείο", MINE, "ore"),
        step("συλλέκτης", COLLECTOR, (-8, -6)),
        step("ηλιακός 2", SOLAR, (-8, 6)),
        step("κοιτώνες", DOME_S, (30, 2), "quarters", after=["κυλικείο"]),
        step("έλεγχος", DOME_S, (30, -10), "control", after=["κοιτώνες"]),
        step("πίστα", PAD, (-14, -14), after=["έλεγχος"]),
        step("πλοίο", "ship", None, after=["πίστα", "έλεγχος"], when=room_free, again=True),
    ]


def plan_mine():
    """Το ορυχείο αμέσως μετά το μέταλλο, και ένας δεύτερος ηλιακός για το
    ρεύμα του: το μέταλλο της αρχής δεν φτάνει για όλα, και χωρίς ορυχείο το
    αρχικό μετάλλευμα (60 -> 30 μέταλλο) τελειώνει γύρω στο sol 5."""
    return [
        step("ηλιακός", SOLAR, (10, -6)),
        step("οξυγόνο", DOME_S, (6, 2), "oxygen", [OXYGEN]),
        step("airlock", AIRLOCK, (6, 12), after=["οξυγόνο"]),
        step("αντλία", EXTRACTOR, "water"),
        step("κυλικείο", DOME_S, (18, 2), "canteen", after=["οξυγόνο"]),
        step("εργοστάσιο", DOME_S, (6, -10), "factory", [METAL], after=["οξυγόνο"]),
        step("ορυχείο", MINE, "ore"),
        step("ηλιακός 2", SOLAR, (-8, 6)),
        step("ανταλλακτικά", DOME_S, (6, -10), "factory", [SPARES], after=["οξυγόνο"]),
        step("άμυλο", DOME_S, (20, 14), "green", [STARCH], after=["κυλικείο"]),
        step("λαχανικά", DOME_S, (20, 14), "green", [VEG], after=["κυλικείο"]),
        step("εργαστήριο", DOME_S, (18, -10), "lab", [MEAT], after=["κυλικείο"]),
        step("γεύματα", "fit", "κυλικείο", codes=[MEALS], after=["κυλικείο"]),
        step("συλλέκτης", COLLECTOR, (-8, -6)),
        step("πλαστικό", DOME_S, (6, -10), "factory", [PLASTIC], after=["άμυλο"]),
        step("κοιτώνες", DOME_S, (30, 2), "quarters", after=["κυλικείο"]),
        step("έλεγχος", DOME_S, (30, -10), "control", after=["κοιτώνες"]),
        step("πίστα", PAD, (-14, -14), after=["έλεγχος"]),
        step("πλοίο", "ship", None, after=["πίστα", "έλεγχος"], when=room_free, again=True),
    ]


def plan_mine_ns():
    """Το mine χωρίς το εργοστάσιο ανταλλακτικών: η μηχανή SPARES τρώει ό,τι
    μέταλλο και βιοπλαστικό βρει (47 ανταλλακτικά, μέταλλο 3 για οκτώ sol),
    οπότε εδώ τα ανταλλακτικά έρχονται από το --tweak."""
    return [s for s in plan_mine() if s["name"] != "ανταλλακτικά"]


def plan_grow():
    """Ανθρωποι πρώτα: τέσσερις άποικοι έχουν τρεις χειριστές (εργάτες και
    βιολόγος, job_roles), και η τροφή μόνη της θέλει τρεις — θερμοκήπιο,
    MEAT, MEALS — πριν από το μέταλλο και το ορυχείο. Ελεγχος και πίστα
    αμέσως μετά το κυλικείο, πλοίο όποτε χωράει, θερμοκήπιο M (ένας χειριστής
    για τέσσερα φυτά), και δεύτερο οξυγόνο πριν από τους δέκα."""
    more = lambda G: G.rows[-1]["alive"] >= 8
    return [
        step("ηλιακός", SOLAR, (10, -6)),
        step("οξυγόνο", DOME_S, (6, 2), "oxygen", [OXYGEN]),
        step("airlock", AIRLOCK, (6, 12), after=["οξυγόνο"]),
        step("αντλία", EXTRACTOR, "water"),
        step("κυλικείο", DOME_S, (18, 2), "canteen", after=["οξυγόνο"]),
        step("έλεγχος", DOME_S, (30, -10), "control", after=["κυλικείο"]),
        step("πίστα", PAD, (-14, -14), after=["έλεγχος"]),
        step("πλοίο", "ship", None, after=["πίστα", "έλεγχος"],
             when=lambda G: room_free(G, 8 * G.oxy()), again=True),
        step("εργοστάσιο", DOME_S, (6, -10), "factory", [METAL], after=["οξυγόνο"]),
        step("θερμοκήπιο", DOME_M, (20, 14), "green", [STARCH, STARCH, VEG, VEG],
             after=["κυλικείο"]),
        step("εργαστήριο", DOME_S, (18, -10), "lab", [MEAT], after=["κυλικείο"]),
        step("γεύματα", "fit", "κυλικείο", codes=[MEALS], after=["κυλικείο"]),
        step("ορυχείο", MINE, "ore"),
        step("ηλιακός 2", SOLAR, (-8, 6)),
        step("οξυγόνο 2", DOME_S, (6, 2), "oxygen", [OXYGEN], after=["οξυγόνο"], when=more),
        step("ανταλλακτικά", DOME_S, (6, -10), "factory", [SPARES], after=["οξυγόνο"]),
        step("συλλέκτης", COLLECTOR, (-8, -6)),
        step("κοιτώνες", DOME_S, (30, 2), "quarters", after=["κυλικείο"]),
        step("κυλικείο 2", DOME_S, (18, 2), "canteen", [MEALS], after=["κυλικείο"], when=more),
        step("ηλιακός 3", SOLAR, (-8, -14)),
    ]


def storage_due(G):
    """Η αποθήκη (βήμα 122): ένας θόλος Storage όταν τα αγαθά φτάνουν τα 120
    κάτω από τη χωρητικότητα, και όχι ενώ ένας χτίζεται ήδη."""
    return (G.total() >= G.capacity() - 120 and
            not any(d[4] == DS_BUILDING and d[3] == R_STORAGE for d in G.domes()))


def plan_store():
    """Το mine_ns με την αποθήκη (βήμα 124): ένας θόλος Storage S όποτε τα
    αγαθά πλησιάζουν τη χωρητικότητα, πριν σταματήσουν οι μηχανές."""
    plan = plan_mine_ns()
    at = next(k for k, s in enumerate(plan) if s["name"] == "πίστα")
    plan.insert(at, step("αποθήκη", DOME_S, (30, 14), "storage", after=["οξυγόνο"],
                         when=storage_due, again=True))
    return plan


def plan_long():
    """Το store για 40 sols και είκοσι αποίκους (βήμα 124): οι καταστροφές
    περιμένουν τους είκοσι (βήμα 121). Δεύτερο και τρίτο οξυγόνο, κοιτώνες,
    κυλικείο και θερμοκήπιο όσο μεγαλώνει η αποικία, και πλοία όποτε χωρούν
    (όσοι αντέχει το οξυγόνο: δέκα το καθένα)."""
    n = lambda k: (lambda G: G.rows[-1]["alive"] >= k)
    plan = [s for s in plan_store() if s["item"] != "ship"]
    plan += [
        step("πλοίο", "ship", None, after=["πίστα", "έλεγχος"],
             when=ship_ok, again=True),
        step("οξυγόνο 2", DOME_S, (6, 2), "oxygen", [OXYGEN], after=["οξυγόνο"], when=n(7)),
        step("κοιτώνες 2", DOME_S, (30, 2), "quarters", after=["κοιτώνες"], when=n(8)),
        step("θερμοκήπιο 2", DOME_S, (20, 14), "green", [STARCH], after=["άμυλο"], when=n(9)),
        step("λαχανικά 2", DOME_S, (20, 14), "green", [VEG], after=["λαχανικά"], when=n(9)),
        step("εργαστήριο 2", DOME_S, (18, -10), "lab", [MEAT], after=["εργαστήριο"], when=n(10)),
        step("κυλικείο 2", DOME_S, (18, 2), "canteen", [MEALS], after=["κυλικείο"], when=n(10)),
        step("οξυγόνο 3", DOME_S, (6, 2), "oxygen", [OXYGEN], after=["οξυγόνο 2"], when=n(15)),
        step("κοιτώνες 3", DOME_S, (30, 2), "quarters", after=["κοιτώνες 2"], when=n(14)),
        step("θερμοκήπιο 3", DOME_S, (20, 14), "green", [STARCH], after=["άμυλο"], when=n(15)),
        step("λαχανικά 3", DOME_S, (20, 14), "green", [VEG], after=["λαχανικά"], when=n(15)),
        step("ηλιακός 3", SOLAR, (-8, -14), when=n(12)),
    ]
    return plan


PLANS = {"base": plan_base, "lean": plan_lean, "spares": plan_spares, "mine": plan_mine,
         "mine_ns": plan_mine_ns, "grow": plan_grow, "store": plan_store, "long": plan_long}


def tweak(G, spec):
    """Πειράγματα για τη μέτρηση, πάνω στο τρέχον παιχνίδι: spares=N, metal=N,
    bio=N, ore=N, food=N (αποθέματα), nofault (το ec_break = ret: ούτε βλάβες
    ούτε εκλάμψεις ούτε μηχανές από μετεωρίτες), fault=M (η μάσκα της βλάβης,
    #7F = 1/128, #FF = 1/256)."""
    import codeat
    idx = dict(water=0, food=1, ore=2, metal=3, bio=4, spares=6)
    for t in [x for x in spec.split(",") if x]:
        k, _, v = t.partition("=")
        if k in idx:
            n = int(v, 0)
            G.m.poke(G.g + 2 * idx[k], n & 255)
            G.m.poke(G.g + 2 * idx[k] + 1, n >> 8)
        elif k == "nofault":
            codeat.poke(G.m, G.sym["EC_BREAK"], 0xC9)
            codeat.poke(G.m, G.sym["EC_BREAK_D"], 0xC9)
        elif k == "iron":
            # Η απόδοση της μηχανής METAL (βήμα 124): το qty της συνταγής της
            # (G_recipes + 10 * 1 + 7), 1 στο παιχνίδι.
            G.m.poke(G.L["G_recipes"] + 10 * 1 + 7, int(v, 0))
        elif k == "eng_op":
            # Ο μηχανικός και στις Operate (job_roles[J_OPERATE] = εργάτης |
            # μηχανικός | βιολόγος): πόσο λείπει ένας χειριστής.
            G.m.poke(G.sym["JOB_ROLES"] + 1, 0x07)
        elif k == "fault":
            a = codeat.find(G.m, G.sym["EV_FAULT"], [0x7D, 0xE6, 0x7F], 40)
            assert a, "δεν βρέθηκε το and #7F του ev_fault"
            codeat.poke(G.m, a + 2, int(v, 0))
        else:
            raise SystemExit(f"άγνωστο πείραγμα {t}")


def ready(G, s):
    return all(a in G.built and G.state(G.built[a][0]) == DS_ACTIVE for a in s["after"])


def try_step(G, s):
    """-> True αν το στάδιο έγινε (και φεύγει από τη λίστα)."""
    if s["item"] == "ship":
        ok = G.call_ship()
        r = G.rows[-1]
        G.event(f"πλοίο: {'έρχεται' if ok else 'ΔΕΝ ΗΡΘΕ'} (ζωντανοί {r['alive']}/{r['popcap']})")
        return ok
    if s["item"] == "fit":
        node, at = G.built[s["near"]]
        left = G.fit(at, [None] * 8 if False else s["codes"])
        G.event(f"εξοπλισμός «{s['name']}» στον θόλο {node}: "
                f"{'όλος' if not left else 'περιμένει ' + str(left)}")
        if left:
            G.fits.append([s["name"], at, left])
        G.built[s["name"]] = (node, at)
        return True
    m, bp = COST[s["item"]]
    if s["item"] == MINE and not any(t[2] == MINE_K and t[4] for t in G.structs()):
        m = 0                               # το πρώτο ορυχείο δωρεάν (βήμα 123)
    if G.stock(S_METAL) < m or G.stock(S_BIOPL) < bp:
        return False                        # ούτε χωρίς διαδρόμους: μην ψάξεις
    key = (s["name"], sum(1 for d in G.domes() if d[4]) + sum(1 for t in G.structs() if t[4]))
    if G.spot_cache.get(key, 0) is None:
        return None                         # ίδια αποικία, ίδια απάντηση
    near = s["near"]
    if isinstance(near, str):
        cands = G.res_near(near)[:40]
    else:
        # ο στόχος, και αν εκεί δεν χωρά, γύρω από ό,τι έχει χτιστεί, από το
        # κοντινότερο στον στόχο
        sb = lambda v: v - 256 if v > 127 else v
        own = [(sb(d[0]), sb(d[1])) for d in G.domes() if d[4]] + \
              [(sb(t[0]), sb(t[1])) for t in G.structs() if t[4]]
        own.sort(key=lambda c: max(abs(c[0] - near[0]), abs(c[1] - near[1])))
        cands = [near] + own
    got = None
    G.why = {}
    for c in cands:                         # η φθηνότερη από όλους τους στόχους
        g = G.spot(s["item"], c)
        if g and (got is None or g[1] < got[1]):
            got = g
        if got and not got[1]:
            break
    half = False
    if got is None and s["item"] == MINE:
        # ΚΑΜΙΑ ΘΕΣΗ ΣΤΗ ΦΛΕΒΑ (βήμα 123): δίπλα σε ό,τι έχει χτιστεί, με τη
        # μισή απόδοση — ο κόσμος 1048 του βήματος 120.
        sb = lambda v: v - 256 if v > 127 else v
        own = [(sb(d[0]), sb(d[1])) for d in G.domes() if d[4]] + \
              [(sb(t[0]), sb(t[1])) for t in G.structs() if t[4]]
        for c in own:
            g = G.spot(s["item"], c, need=False)
            if g and (got is None or g[1] < got[1]):
                got = g
            if got and not got[1]:
                break
        half = got is not None
    G.spot_cache[key] = got
    if got is None:
        return None                         # καμία θέση ακόμη: ίσως μετά από άλλα
    at, pieces = got
    m += 6 * pieces
    bp += 3 * pieces
    if G.stock(S_METAL) < m or G.stock(S_BIOPL) < bp:
        return False
    node = G.place(s["item"], at, ROOM.get(s["room"]))
    if node is None:
        G.event(f"«{s['name']}» δεν μπήκε στο {at} (μέταλλο {G.stock(S_METAL)}, "
                f"θέλει {m}/{bp})")
        return False
    G.built[s["name"]] = (node, at)
    G.event(f"χτίζεται «{s['name']}» (κόμβος {node}, {at}, {pieces} διάδρ.) -> "
            f"μέταλλο {G.stock(S_METAL)}, βιοπλ. {G.stock(S_BIOPL)}"
            + (", ΕΚΤΟΣ ΦΛΕΒΑΣ (μισό)" if half else ""))
    if s["codes"]:
        left = G.fit(at, s["codes"])
        G.event(f"   εξοπλισμός: {'όλος' if not left else 'περιμένει ' + str(left)}")
        if left:
            G.fits.append([s["name"], at, left])
    return True


def play(G, plan, sols):
    todo = list(plan)
    nowhere = set()
    while G.sol() < sols:
        G.run(STEP)
        if not G.rows[-1]["alive"]:
            G.event("ΤΕΛΟΣ: κανείς ζωντανός")
            break
        for f in list(G.fits):              # εξοπλισμός που περίμενε υλικά
            if G.stock(S_METAL) >= 10 and G.stock(S_BIOPL) >= 4:
                f[2] = G.fit(f[1], f[2])
                if not f[2]:
                    G.event(f"εξοπλισμός «{f[0]}»: όλος")
                    G.fits.remove(f)
        # Με τη σειρά: ένα κτίσμα που δεν πληρώνεται ακόμη κρατά πίσω τα
        # επόμενα κτίσματα — όχι όμως τον εξοπλισμό και τα πλοία, που
        # κοστίζουν λίγα ή τίποτα. Αλλιώς ένα ορυχείο που δεν χωρά πουθενά
        # κρατούσε για πάντα τα έξι μέταλλα του MEALS, και ο παίκτης πέθαινε
        # από πείνα με 300 άμυλο στην αποθήκη.
        held = False
        for s in list(todo):
            cheap = s["item"] in ("ship", "fit")
            if held and not cheap:
                continue
            if not ready(G, s):
                continue
            if s["when"] and not s["when"](G):
                continue
            if not cheap and G.sites() >= OPEN:
                held = True
                continue
            r = try_step(G, s)
            if r is None:
                if s["name"] not in nowhere:
                    G.event(f"καμία θέση για «{s['name']}» ακόμη {G.why}")
                    nowhere.add(s["name"])
                continue
            if r:
                if not s["again"]:
                    todo.remove(s)
                break                       # ένα πράγμα ανά δείγμα
            held = True
    return todo


def report(G):
    print(f"\n{'sol':>5s} {'ζωντ':>6s} {'έξω':>3s} {'νερό':>5s} {'τροφ':>5s} {'μτλλ':>5s} "
          f"{'μέτ':>5s} {'βιο':>5s} {'αν':>3s} {'άμυλ':>5s} {'λαχ':>4s} {'κρέ':>4s} {'ρεύμα':>9s} "
          f"{'μπατ':>5s} {'O2':>7s} {'εργ':>3s} {'δουλ':>4s} {'χαμηλά'}")
    last = -1
    for r in G.rows:
        if int(r["sol"] * 2) == last:
            continue
        last = int(r["sol"] * 2)
        s = r["stock"]
        note = ("" if r["pok"] == 1 else " ΧΩΡΙΣ-ΡΕΥΜΑ" if not r["pok"] else " ΠΕΣΜΕΝΟ") + \
               ("" if r["o2ok"] else " ΧΩΡΙΣ-O2") + (" ΘΥΕΛΛΑ" if r["storm"] else "")
        low = [f"{i}:" + "".join(n for n, v in zip("ONTSH", a[:5]) if v < 64)
               for i, a in sorted(r["need"].items()) if min(a[0], a[1], a[2], a[4]) < 64]
        print(f"{r['sol']:5.1f} {r['alive']:3d}/{r['popcap']:<2d} {r['out']:3d} {s[0]:5d} "
              f"{s[1]:5d} {s[2]:5d} {s[3]:5d} {s[4]:5d} {s[6]:3d} {s[10]:5d} {s[11]:4d} {s[13]:4d} "
              f"{r['pp']:4d}/{r['pu']:<4d} {r['bat']:5d} {r['o2p']:3d}/{r['o2u']:<3d} "
              f"{r['sites']:3d} {r['jobs']:2d}/{r['jfree']:<2d}{note} {' '.join(low)}")


def dump(G):
    """Τι κάνει η αποικία τώρα: εργοτάξια, εργασίες, άποικοι."""
    print(f"\n--- sol {G.sol():.2f}")
    for k, d in enumerate(G.domes()):
        if d[4]:
            print(f"θόλος {k}: ({d[0]-256 if d[0]>127 else d[0]},{d[1]-256 if d[1]>127 else d[1]})"
                  f" μέγ {d[2]} δωμ {d[3]} κατ {d[4]} ακεραιότ {d[5]} μηχ {d[8:16]} υγ {d[16:24]}")
    for k, s in enumerate(G.structs()):
        if s[4]:
            print(f"δομή {64+k}: είδος {s[2]} κατ {s[4]} ακεραιότ {s[5]} b6 {s[6]} οφειλ {s[7]:#04x}")
    for j in G.jobs():
        print(f"εργασία είδος {j[0]} κόμβος {j[1]} πράκτορας {j[2]} προτ {j[3]} εργοτ {j[4]}")
    for i, a in G.agents().items():
        print(f"πράκτορας {i}: {ROLES[a['role'] & 7]} σημ {a['flags']:#04x} κόμβος {a['node']}"
              f" προορ {a['dest']} ακμή {a['edge']} εργ {a['task']} o2 {a['o2']} νερό {a['water']}"
              f" τροφή {a['food']} ύπνος {a['sleep']} υγ {a['health']} στολή {a['suit']}"
              f" spare {a['spare']}")


def worldmap(G, x0=-24, x1=24, y0=-22, y1=22):
    b4 = G.world()
    ch = ".,#^~=o_"
    for ty in range(y0, y1):
        row = ""
        for tx in range(x0, x1):
            b = b4[reach.widx(tx, ty)]
            c = ch[b & 7]
            if (b & 7) == 3 and (b >> 3) & 1:
                c = "*"
            occ = (b >> 4) & 3
            if occ:
                c = "DCX"[occ - 1]
            row += c
        print(f"{ty:4d} {row}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--planet", type=int, default=0)
    ap.add_argument("--seed", type=lambda s: int(s, 0), default=0xACE1)
    ap.add_argument("--sols", type=float, default=20)
    ap.add_argument("--plan", default="base")
    ap.add_argument("--make", action="store_true",
                    help="φτιάξε πρώτα το snapshot (όχι παράλληλα με άλλο play.py)")
    ap.add_argument("--pairs", default=None, help="για --make: seed:planet,...")
    ap.add_argument("--dump", action="store_true")
    ap.add_argument("--tweak", default="", help="π.χ. spares=12,metal=250,nofault,fault=0xFF")
    ap.add_argument("--json", default=None, help="τα δείγματα και τα συμβάντα, για διαγράμματα")
    a = ap.parse_args()
    if a.make:
        pairs = ([(int(x.split(":")[0], 0), int(x.split(":")[1])) for x in a.pairs.split(",")]
                 if a.pairs else [(a.seed, a.planet)])
        make(pairs)
        if a.pairs:
            return 0
    sym, g = syms()
    G = Game(sym, g, sna_path(a.seed, a.planet))
    tweak(G, a.tweak)
    print(f"πλανήτης {a.planet}, seed #{a.seed:04X}, σχέδιο «{a.plan}», {a.sols} sols"
          + (f", πειράγματα {a.tweak}" if a.tweak else ""),
          flush=True)
    left = play(G, PLANS[a.plan](), a.sols)
    report(G)
    deaths = [e for e in G.events if "ΘΑΝΑΤΟΣ" in e]
    r = G.rows[-1]
    print(f"\nΣΥΝΟΨΗ πλανήτης {a.planet} seed #{a.seed:04X} «{a.plan}» {a.tweak}: sol {G.sol():.2f}, "
          f"ζωντανοί {r['alive']}/{r['popcap']}, θάνατοι {len(deaths)}"
          + (f", πρώτος {deaths[0]}" if deaths else "") + f", ορόσημα {r['mile']:#04x}")
    if a.dump:
        dump(G)
        worldmap(G)
    if left:
        print("δεν χτίστηκαν:", ", ".join(s["name"] for s in left if not s["again"]))
    if a.json:
        import json
        json.dump(dict(seed=a.seed, planet=a.planet, plan=a.plan, tweak=a.tweak,
                       rows=[dict(sol=r["sol"], alive=r["alive"], popcap=r["popcap"],
                                  stock=r["stock"], cap=r["cap"], full=r["full"],
                                  storm=r["storm"], pok=r["pok"], o2ok=r["o2ok"],
                                  mines=r["mines"], sites=r["sites"]) for r in G.rows],
                       events=G.events), open(a.json, "w"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
