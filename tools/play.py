#!/usr/bin/env python3
"""ΕΝΑΣ ΠΑΙΚΤΗΣ-ΣΕΝΑΡΙΟ ΑΠΟ ΤΗΝ ΑΔΕΙΑ ΑΡΧΗ (βήμα 120, DESIGN §6.5).

Το tools/balance.py μετρούσε την αποικία δοκιμών του §10.1, που από το βήμα 87
δεν είναι πια η αρχή του παιχνιδιού. Εδώ τρέχει το main.sna όπως το βλέπει ο
παίκτης — έξι άποικοι έξω, δίπλα στο σκάφος, με 189 μέταλλο και 137
βιοπλαστικό (107 ως το βήμα 132) — και ένα σενάριο το παίζει με τα ΠΛΗΚΤΡΑ του: κατάλογος, θέση,
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
import argparse, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, "/home/vasilhs/cpcemu")

import balance as B                                      # noqa: E402
import reach                                             # noqa: E402
import econ as EC                                        # noqa: E402

RASM = os.path.expanduser("~/rasm/rasm.exe")
PER_SOL = 3000                     # πραγματικά frames ανά sol στο x4: 4 ανά frame
STEP = PER_SOL // 8
OPEN = 2                           # εργοτάξια ταυτόχρονα, το πολύ
STOCKS = ["νερό", "τροφή", "μετάλλ", "μέταλ", "βιοπλ", "επεξ", "ανταλ", "φάρμ",
          "όπλα", "ρομπ", "άμυλο", "λαχαν", "βότ", "κρέας"]
S_WATER, S_FOOD, S_ORE, S_METAL, S_BIOPL = 0, 1, 2, 3, 4
O2_PER_COL = 2                     # tools/econ.py O2_PER_COLONIST
NECK_C = 40                        # βήμα 165: κάτω από τόσες θέσεις θόλου ο λαιμός μετρά
# βήμα 161: 1 για ένα tile βράχου με κατοχή (#12, ένας διάδρομος από πάνω), 0 αλλιώς
ROCK_CORR = bytes(1 if b & 0x37 == 0x12 else 0 for b in range(256))
ROOM = dict(oxygen=0, canteen=1, quarters=2, green=3, factory=4, lab=5, medbay=6,
            control=7, storage=8, lounge=9)
OXYGEN, METAL, PLASTIC, WEAPONS, CHIPS, ROBOTS, MEALS, SPARES, DRUGS, MEAT = range(10)
STARCH, VEG, HERBS, TREE = 250, 251, 252, 253
DOME_S, DOME_M, DOME_L, CORR, SOLAR, TURBINE, COLLECTOR, EXTRACTOR, MINE, AIRLOCK, PAD = range(11)
COST = {DOME_S: (12, 8), DOME_M: (24, 14), DOME_L: (40, 24), SOLAR: (15, 0),
        TURBINE: (18, 0), COLLECTOR: (14, 0), EXTRACTOR: (22, 0), MINE: (30, 0),
        AIRLOCK: (10, 6), PAD: (45, 0)}
DS_BUILDING, DS_ACTIVE = 1, 2
# Ο ΙΔΙΟΣ ΘΟΛΟΣ ΜΕ ΑΛΛΟ ΑΡΙΘΜΟ (βήμα 140): το ROOM είναι η σειρά του καταλόγου,
# το D_ROOM της εγγραφής του θόλου το R_* του tools/econ.py.
DROOM = dict(oxygen=4, canteen=3, quarters=2, green=5, factory=8, lab=9, medbay=10,
             control=1, storage=6, lounge=11)
MACHINE_COUNT = (1, 4, 8)          # υποδοχές ανά μέγεθος s/m/l (tools/econ.py)
GROW_AT = 14                       # από τόσους αποίκους τα «+» χτίζουν μεσαίο θόλο
CORE_R = (14, 20, 26, 32, 44, 60)  # tiles γύρω από το κέντρο των θόλων, με τη σειρά (44, 60: βήμα 160)
SHORE_AHEAD = 1                    # βήμα 145: ελεύθερες θέσεις αντλίας που κρατά
SHORE_R = 16                       # ως τόσα tiles από το σκάφος
SHORE_AT = GROW_AT                 # από τόσους αποίκους
FAR_R = 40                         # βήμα 147: όχθες ως τόσα tiles, όταν κοντά δεν χωρά
FAR_N = 12                         # οι τόσες κοντινότερες, μία ανά 4x4
FAR_ANCHORS = 6                    # σκαλοπάτια (airlock) για νερό και ρεύμα, το πολύ
SLOT_KEEP = 2                      # θέσεις δομών (STRUCT_SLOTS) που μένουν για αντλίες
STRUCT_SLOTS = 48                  # το MAX_STRUCT του src/const.asm (32 ως το βήμα 155)
MINE_K = 4                         # K_MINE, το είδος της δομής
K_SOLAR, K_COLLECT, K_EXTRACT, K_AIRLOCK = 0, 2, 3, 5   # τα K_* του src/const.asm
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


def sna_path(seed, planet, tut=False):
    return os.path.join(ROOT, "build", f"play_{seed:04x}_{planet}{'_tu' if tut else ''}.sna")


def make(pairs, tut=False):
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
            out = sna_path(seed, planet, tut)
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
            if tut:
                # ...και το bit 7 του τέταρτου, όπως για την έκτη γραμμή του μενού
                # (βήμα 149): ο κόσμος του tutorial, και το πρώτο βήμα στην εκκίνηση.
                d[at + 3] = Wg.GEN_VERSION | 0x80
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
        self.pclass = None                      # βήμα 168: η κλάση κάθε ποικιλίας φυτού
        self.spot_cache = {}
        self.lastb = {}                         # όνομα σταδίου -> sol του τελευταίου
        self.zones = False                      # το σχέδιο big: διάταξη με ζώνες
        self.tut = False                        # το σχέδιο tutorial (βήμα 149)
        self.shore, self.shore_key = [], None   # βήμα 145: οι θέσεις των αντλιών (Game.keep_shore)
        self.shore_path = set()                 # και τα tiles των μονοπατιών τους
        self.anchors = 0                        # βήμα 147: σκαλοπάτια προς μακρινό νερό
        self.neck_n, self.neck_t = 0, 0.0       # βήμα 165: μετρήματα θέσεων, δευτερόλεπτα
        self.feed = None                        # --tweak feed=M:B
        self.plast = None                       # --tweak skeep=N / bmax=N (βήμα 138)
        self.trader = False                     # το εμπόριο (βήμα 139): τα σχέδια big*
        self.lands_seen = None
        self.trades = []                        # (sol, net, έγινε)
        self.grow = False                       # βήμα 140: γέμισμα, μεσαίοι, ακτίνα (big*)
        self.probes = []                        # (sol, ζωντανοί, x1, x4) ανά δύο sol
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
        return [list(b6[s0 + 8 * k:s0 + 8 * k + 8]) for k in range(STRUCT_SLOTS)]

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
        a = E.Agents().from_bytes(bytes(b6[a0:a0 + 4096]))
        return {i: {f: getattr(a, f)[i] for f in E.FIELDS} for i in range(E.MAXAGENT)
                if a.flags[i] & 1}

    def capacity(self):
        """Η αποθήκη (βήμα 122): 500 και 100/300/600 ανά θόλο Storage έτοιμο."""
        return 500 + sum((100, 300, 600)[d[2]] for d in self.domes()
                         if d[4] == DS_ACTIVE and d[3] == R_STORAGE)

    def batcap(self):
        """Η μπαταρία (βήμα 138): 40/160/360 ανά συλλέκτη έτοιμο, κατά μέγεθος
        (DESIGN §6.5)· ο συλλέκτης του καταλόγου είναι ο μεγάλος, 360."""
        return sum((40, 160, 360)[t[3]] for t in self.structs()
                   if t[2] == K_COLLECT and t[4] == DS_ACTIVE)

    def total(self):
        return sum(self.stock(k) for k in range(1, 14))

    def oxy(self):
        """Θόλοι οξυγόνου σε λειτουργία: ο καθένας φτάνει για δέκα (§6.5)."""
        return sum(1 for d in self.domes() if d[4] == DS_ACTIVE and d[3] == 4)

    def sites(self):
        return (sum(1 for d in self.domes() if d[4] == DS_BUILDING)
                + sum(1 for s in self.structs() if s[4] == DS_BUILDING))

    # --- ο χρόνος ------------------------------------------------------------
    def ticks(self):
        return self.m.peek(self.X["EC_SOL"]) * 12000 + self.w16(self.X["EC_FRAME"])

    def speed_probe(self, n1=800, n4=400):
        """ΠΡΟΛΑΒΑΙΝΕΙ; (βήμα 131): n1 frames στο x1 και n4 στο x4, χωρίς πλήκτρα.
        Ο βρόχος περιμένει το VSYNC και τρέχει τόσες θέσεις του τροχού όσες η
        ταχύτητα (src/main.asm): ένα βαρύ frame χάνει το επόμενο VSYNC, και
        τα ticks ανά frame πέφτουν κάτω από την ταχύτητα. Σε 150 frames το
        λάθος ήταν ±7 %, σε 600 ±1,5 %. -> (x1, x4)."""
        out = []
        for spd, n in ((1, n1), (4, n4)):
            self.m.poke(self.sym["UI_SPD"], spd)
            self.m.run_frames(4)
            t0 = self.ticks()
            self.m.run_frames(n)
            out.append((self.ticks() - t0) / n)
        self.m.poke(self.sym["UI_SPD"], 4)
        self.frames += n1 + n4 + 8
        return tuple(out)

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
        if any(EC.AG_FOE0 <= j < EC.AG_FOE0 + EC.AG_NFOE for j in ag) \
                or self.m.peek(self.X["EC_SHKIND"]) == 4:
            self.foe_seen = self.sol()          # εισβολείς ζωντανοί, ή το πλοίο τους
        for i, a in self.alive_prev.items():
            if i not in ag and i < EC.AG_BOT0:
                # Με εισβολείς ζωντανούς (176-179) ο θάνατος είναι δικός τους (βήμα
                # 138): το cause() διάβαζε τις ανάγκες και έγραφε «δίψα» με νερό 200.
                foe = self.sol() - getattr(self, "foe_seen", -9) < 0.5
                why = "ΕΙΣΒΟΛΕΙΣ" if foe and min(a["o2"], a["water"], a["food"]) > 24 else cause(a)
                self.event(f"ΘΑΝΑΤΟΣ {i} ({ROLES[a['role'] & 7]}): {why}")
        self.alive_prev = ag
        self.watch()
        jobs = self.jobs()
        # ΟΙ ΕΠΙΣΚΕΠΤΕΣ ΚΑΙ ΤΑ ΝΟΜΙΣΜΑΤΑ (βήμα 137): το EC_X, στο πάνω μισό του
        # node_occ (τράπεζα 6) — νομίσματα, κύρος, εύνοια, συσσωρευτής.
        b6, x = self.bank(6), self.L["G_node_occ"] - 0x4000 + 240     # EC_X (βήμα 172· ως τότε 128 + 100)
        ds = self.domes()
        self.rows.append(dict(
            vis=sum(1 for i in ag if EC.AG_VIS0 <= i < EC.AG_VIS0 + EC.AG_NVIS),
            coins=b6[x + 6] | b6[x + 7] << 8, prest=b6[x + 8], good=b6[x + 9],
            # οι μηχανές METAL (βήμα 137): ανά θόλο εργοστασίου, πόσες και πόσοι χειριστές
            mm=[(sum(1 for j in range(8) if d[8 + j] == METAL), d[7]) for d in ds
                if d[4] == DS_ACTIVE and d[3] != R_GREEN and METAL in d[8:16]],
            sol=self.sol(), alive=sum(1 for i in ag if i < EC.AG_BOT0),
            bots=sum(1 for i in ag if EC.AG_BOT0 <= i < EC.AG_BOT0 + EC.AG_NBOT),
            out=sum(1 for i, a in ag.items() if i < EC.AG_BOT0 and not a["flags"] & 2),
            popcap=p(X["EC_POPCAP"]), ship=p(X["EC_SHSTATE"]),
            stock=[self.stock(k) for k in range(14)],
            pp=w(X["EC_PPROD"]), pu=w(X["EC_PUSE"]), bat=w(X["EC_PSTORE"]),
            bcap=self.batcap(),
            # οι δομές και οι θόλοι (βήμα 138): είδος ανά δομή έτοιμη, και ανά
            # θόλο έτοιμο δωμάτιο, μέγεθος, χειριστές, μηχανές
            sk=[t[2] for t in self.structs() if t[4] == DS_ACTIVE],
            dm=[(d[3], d[2], d[7], [c for c in d[8:16] if c != 255]) for d in ds
                if d[4] == DS_ACTIVE],
            o2p=w(X["EC_O2PROD"]), o2u=w(X["EC_O2USE"]),
            pok=p(X["EC_POK"]), o2ok=p(X["EC_O2OK"]), storm=p(X["EC_STORM"]),
            cap=self.capacity(), full=p(self.sym["EC_FULL"]),
            mines=[(s[6] & 0x0C, s[7]) for s in self.structs() if s[2] == MINE_K and s[4]],
            sites=self.sites(), jobs=len(jobs),
            jk=[j[0] for j in jobs], jfree=sum(1 for j in jobs if j[2] == 255),
            mile=p(X["EC_MILE"]),
            # οι διάδρομοι (βήμα 159): το CT_TOP, η ψηλότερη εγγραφή σε χρήση +1,
            # και πόσες από τις 128 είναι σε χρήση (με τις συνέχειες των στροφών)
            ct=p(self.L["G_rt_nodes"] + 117), nc=self.corr_used(),
            # βήμα 161: πόσα tiles βράχου έχουν διάδρομο από πάνω (#12)
            rk=bytes(self.world()).translate(ROCK_CORR).count(1),
            need={i: (a["o2"], a["water"], a["food"], a["sleep"], a["health"], a["suit"],
                      a["flags"]) for i, a in ag.items() if i < EC.AG_BOT0}))

    def corr_used(self):
        """Πόσες από τις 128 εγγραφές διαδρόμων (τράπεζα 5) δεν είναι άδειες."""
        b5, c0 = self.bank(5), self.L["G_corr_tbl"] - 0x4000
        return sum(1 for k in range(128) if b5[c0 + 4 * k] != 254)

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

    def spot(self, item, near, room=None, need=True, dry=False):
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
                    if item != EXTRACTOR and self.on_shore(tx, ty, w, h):
                        continue
                    if dry and B.has_near(b4, tx, ty, w, "water"):
                        continue                # το σκαλοπάτι δεν πατά όχθη (βήμα 147)
                    p = reach.plan(b4, domes, structs, dims, kind, param, w, h,
                                   2 * tx + w, 2 * ty + h)
                    if not p["ok"]:
                        k = f"λόγος {p['reason']}"
                        self.why[k] = self.why.get(k, 0) + 1
                        continue
                    if item != EXTRACTOR and self.shore_cut(p):
                        continue
                    score = (p["pieces"], r)
                    if best is None or score < best[0]:
                        best = (score, (2 * tx + w, 2 * ty + h))
            if best is not None and r >= best[0][1] + 2:
                break
        return (best[1], best[0][0]) if best else None

    def own(self):
        """(θόλοι, δομές) σε λειτουργία ή υπό κατασκευή, (x, y) σε μισά tiles."""
        sb = lambda v: v - 256 if v > 127 else v
        return ([(sb(d[0]), sb(d[1])) for d in self.domes() if d[4]],
                [(sb(t[0]), sb(t[1])) for t in self.structs() if t[4]])

    def keep_shore(self):
        """ΚΡΑΤΑ ΤΗΝ ΟΧΘΗ ΓΙΑ ΤΙΣ ΑΝΤΛΙΕΣ (βήμα 145): από SHORE_AT αποίκους,
        SHORE_AHEAD θέσεις 3x3 που περνούν τον κανόνα του bd_res και που μια
        αντλία φτάνει τώρα, όσο πιο κοντά στις αντλίες (αλλιώς στο σκάφος), ως
        SHORE_R tiles από το σκάφος. Κανένας θόλος, δομή, διάδρομος ή μονοπάτι
        δεν πατά τη θέση ή το μονοπάτι της (on_shore, shore_cut). Στον 1048 0 οι
        θόλοι του big είχαν πιάσει όλη την όχθη της λίμνης δίπλα στο σκάφος ως
        το sol 41: από εκατό όχθες ως τα 40 tiles χωρούσαν αντλία μόνο δύο, 25
        tiles βόρεια, και με 34 αποίκους και τρεις αντλίες το νερό έμεινε κάτω
        από 20 πέντε sol (στο g144 του βήματος 144, 23 νεκροί από αέρα).
        Μία φορά ανά αλλαγή της αποικίας."""
        if not self.zones:
            return
        # ΑΠΟ ΤΟΥΣ ΔΕΚΑΤΕΣΣΕΡΙΣ: κρατημένη από την αρχή, η όχθη έπαιρνε τη γη του
        # πυρήνα — στο C0DE 2 το δεύτερο οξυγόνο έπεσε τρία κομμάτια διαδρόμου
        # μακριά, και στο sol 40 οι αποικίες είχαν κατά μέσο 15,2 αντί για 17,1.
        if not self.rows or self.rows[-1]["alive"] < SHORE_AT:
            self.shore, self.shore_key, self.shore_path = [], None, set()
            return
        key = (sum(1 for d in self.domes() if d[4]), sum(1 for t in self.structs() if t[4]))
        if key == self.shore_key:
            return
        self.shore_key = key
        b4 = self.world()
        domes = [d[:4] for d in self.domes()]
        structs = [t[:7] for t in self.structs()]
        dims = self.m.read_ram(self.L["G_struct_dims"], 64)
        kind, param, w, h = self.m.read_ram(self.sym["BLD_ITEMS"] + 8 * EXTRACTOR, 4)

        def fits(tx, ty):
            """-> τα tiles του μονοπατιού της, ή None.
            ΚΑΙ ΝΑ ΦΤΑΝΕΙ (C0DE 1): μια θέση μόνο με το έδαφος ήταν σε λίμνη
            όπου δεύτερη αντλία δεν έβρισκε μονοπάτι, και το νερό έμεινε στο 5."""
            if not (all(reach.ok_tile(b4[reach.widx(tx + i, ty + j)])
                        for i in range(3) for j in range(3))
                    and B.has_near(b4, tx, ty, 3, "water")):
                return None
            if any((tx + i, ty + j) in self.shore_path for i in range(3) for j in range(3)):
                return None
            p = reach.plan(b4, domes, structs, dims, kind, param, w, h, 2 * tx + w, 2 * ty + h)
            return (p["path"][2] if p["path"] else []) if p["ok"] else None
        # ΑΠΟ ΤΗΝ ΑΡΧΗ ΚΑΘΕ ΦΟΡΑ, όχι κολλημένες: ως το πρώτο airlock μια αντλία
        # δίπλα στο σκάφος δεν φτάνει (το σκάφος δεν είναι άγκυρα, ship0), και
        # οι κολλημένες έμεναν δίπλα στον πρώτο ηλιακό, 13 tiles μακριά.
        # ΚΑΙ ΤΟ ΜΟΝΟΠΑΤΙ ΤΗΣ: στο C0DE 2 η κρατημένη θέση έμεινε χωρίς μονοπάτι
        # όταν θόλοι το έκλεισαν, ελευθερώθηκε, και στο sol 51 καμία όχθη ως τα
        # 40 tiles δεν δεχόταν αντλία.
        self.shore, self.shore_path = [], set()
        # ΔΙΠΛΑ ΣΤΙΣ ΑΝΤΛΙΕΣ, αλλιώς στο σκάφος: η αντλία είναι δομή, και το
        # μονοπάτι της επόμενης είναι ένα ή δύο tiles ως αυτήν.
        sb = lambda v: v - 256 if v > 127 else v
        pumps = [((sb(t[0]) - 3) >> 1, (sb(t[1]) - 3) >> 1)
                 for t in self.structs() if t[4] and t[2] == K_EXTRACT] or [(-1, -1)]
        # ΚΑΙ ΩΣ ΤΑ FAR_R ΑΝ ΚΟΝΤΑ ΔΕΝ ΧΩΡΑ, ΜΕΤΑ ΑΠΟ ΣΚΑΛΟΠΑΤΙ (βήμα 147): οι
        # αντλίες της μακρινής όχθης (far_shore) θέλουν κι αυτές τη θέση της
        # επόμενης. Ως τα 40 από την αρχή, μια μακρινή κράτηση έστειλε στο
        # 5A5A 2 έναν ηλιακό αλλού στο sol 30, και στο sol 60 ήταν 22 αντί 32.
        for R in ((SHORE_R, FAR_R) if self.anchors else (SHORE_R,)):
            for _, tx, ty in sorted((min(max(abs(tx - x), abs(ty - y)) for x, y in pumps), tx, ty)
                                    for ty in range(-R - 1, R) for tx in range(-R - 1, R)):
                if any(abs(tx - x) < 3 and abs(ty - y) < 3 for x, y in self.shore):
                    continue
                tl = fits(tx, ty)
                if tl is not None:
                    self.shore.append((tx, ty))
                    self.shore_path.update(tl)
                    if len(self.shore) >= SHORE_AHEAD:
                        break
            if self.shore:
                break

    def far_shore(self):
        """ΟΤΑΝ Η ΟΧΘΗ ΤΕΛΕΙΩΣΕΙ (βήμα 147). Στο g147, 120 sol, ο 1048 0 με 64
        αποίκους και ο 5A5A 2 με 36 δεν βρήκαν θέση για αντλία από το sol 57-59:
        οι κοντινές όχθες είχαν πιάσει, και μια αντλία θέλει δομή ως 12 tiles
        (το σκάφος δεν μετρά). Το νερό τελείωσε, οι μηχανές OXYGEN σταμάτησαν,
        και στο sol 74-75 πέθαναν 56 και 28 από αέρα.
        Οι όχθες ως FAR_R, μία ανά 4x4, από την πιο κοντινή σε μια δομή: πρώτα
        μια αντλία σε όποια από τις FAR_N φτάνει. Αλλιώς ένα σκαλοπάτι: ένα
        airlock ως 10 tiles από μια όχθη, που με αυτό χωρά εκεί αντλία.
        -> ("pump" ή "anchor", (θέση, κομμάτια)) ή None."""
        b4 = self.world()
        sb = lambda v: v - 256 if v > 127 else v
        own = [((sb(t[0]) - 3) >> 1, (sb(t[1]) - 3) >> 1) for t in self.structs()[reach.ship0(
               [u[:7] for u in self.structs()]):] if t[4]]
        if not own:
            return None
        ground = lambda tx, ty: all(reach.ok_tile(b4[reach.widx(tx + i, ty + j)])
                                    for i in range(3) for j in range(3))
        far = lambda tx, ty: min(max(abs(tx - x), abs(ty - y)) for x, y in own)
        R = FAR_R
        shores, seen = [], set()
        for ty in range(-R - 1, R):
            for tx in range(-R - 1, R):
                k = (tx >> 2, ty >> 2)
                if k in seen or not ground(tx, ty) or not B.has_near(b4, tx, ty, 3, "water"):
                    continue
                seen.add(k)
                shores.append((far(tx, ty), tx, ty))
        if not shores:
            return None
        shores.sort()
        for _, tx, ty in shores[:FAR_N]:
            g = self.spot(EXTRACTOR, (2 * tx + 3, 2 * ty + 3))
            if g:
                return "pump", g
        if self.anchors >= FAR_ANCHORS or self.free_structs() < 2:
            return None                         # το σκαλοπάτι και η αντλία του
        # ΤΟ ΣΚΑΛΟΠΑΤΙ ΕΙΝΑΙ AIRLOCK (with_airlock).
        ek, ep, ew, eh = self.m.read_ram(self.sym["BLD_ITEMS"] + 8 * EXTRACTOR, 4)
        X = self.anchor_ctx()
        domes, dims = X["domes"], X["dims"]

        def ground_in(b, tx, ty):
            return all(reach.ok_tile(b[reach.widx(tx + i, ty + j)]) for i in range(3) for j in range(3))

        # ΜΕ ΠΡΟΒΛΕΨΗ: ένα airlock ως 10 tiles από την όχθη μετρά μόνο αν με
        # αυτό χωρά αντλία ως 4 tiles από αυτήν. «Οσο πιο κοντά στην όχθη»
        # σκέτο έβρισκε μόνο νερό και όχθη γύρω της.
        for d0, gx, gy in shores[:FAR_N]:
            for d, tx, ty in sorted((max(abs(tx - gx), abs(ty - gy)), tx, ty)
                                    for ty in range(gy - 10, gy + 11) for tx in range(gx - 10, gx + 11)):
                a = self.with_airlock(tx, ty, X)
                if a is None:
                    continue
                at, pieces, b, sl = a
                for py in range(gy - 4, gy + 5):
                    for px in range(gx - 4, gx + 5):
                        if ground_in(b, px, py) and B.has_near(b, px, py, 3, "water") and \
                                reach.plan(b, domes, sl, dims, ek, ep, ew, eh,
                                           2 * px + ew, 2 * py + eh)["ok"]:
                            return "anchor", (at, pieces)
        return None

    def free_structs(self):
        """Οι ελεύθερες από τις STRUCT_SLOTS θέσεις δομών (MAX_STRUCT)."""
        return sum(1 for t in self.structs() if not t[4])

    def anchor_ctx(self):
        """Ο,τι διαβάζει το with_airlock, μία φορά ανά αναζήτηση."""
        structs = [t[:7] for t in self.structs()]
        kind, param, w, h = self.m.read_ram(self.sym["BLD_ITEMS"] + 8 * AIRLOCK, 4)
        return dict(b4=self.world(), domes=[d[:4] for d in self.domes()], structs=structs,
                    dims=self.m.read_ram(self.L["G_struct_dims"], 64), lock=(kind, param, w, h),
                    slot=next((k for k in range(reach.ship0(structs), STRUCT_SLOTS) if not structs[k][4]), None),
                    size=next((t[3] for t in structs if t[4] and t[2] == K_AIRLOCK), 0))

    def with_airlock(self, tx, ty, X):
        """ΤΟ ΣΚΑΛΟΠΑΤΙ (βήμα 147): ένα airlock στο (tx, ty) που μπαίνει τώρα,
        και η αποικία με αυτό — ο κόσμος με το αποτύπωμα και τον διάδρομό του,
        οι δομές με αυτό. Στον 1048 0 στο sol 58 κανένας ηλιακός ως 16 tiles
        από τις δομές δεν έφτανε μια δομή: οι θόλοι, οι διάδρομοι και τα
        μονοπάτια είχαν περιφράξει την αποικία. Το airlock δεν θέλει μονοπάτι·
        κουμπώνει με διάδρομο σε θόλο, και είναι δομή, η άγκυρα των επόμενων.
        Εκεί 22 θέσεις του έφταναν. -> (θέση, κομμάτια, κόσμος, δομές) ή None."""
        b4, domes, structs, dims, slot = X["b4"], X["domes"], X["structs"], X["dims"], X["slot"]
        kind, param, w, h = X["lock"]
        if slot is None or not (-60 <= tx and tx + w <= 60 and -60 <= ty and ty + h <= 60):
            return None
        if not all(reach.ok_tile(b4[reach.widx(tx + i, ty + j)]) for i in range(w) for j in range(h)) \
                or self.on_shore(tx, ty, w, h):
            return None
        at = (2 * tx + w, 2 * ty + h)
        p = reach.plan(b4, domes, structs, dims, kind, param, w, h, *at)
        if not p["ok"] or self.shore_cut(p):
            return None
        b = bytearray(b4)
        for j in range(h):
            for i in range(w):
                b[reach.widx(tx + i, ty + j)] |= 0x10
        for c in p["corridors"]:
            for x, y in c[4]:
                b[reach.widx(x, y)] |= 0x20             # ο διάδρομός του πιάνει κι αυτός
        sl = [list(t) for t in structs]
        sl[slot] = [at[0] & 255, at[1] & 255, K_AIRLOCK, X["size"], 2, 255, 0]
        return at, p["pieces"], b, sl

    def struct_anchor(self, item):
        """ΚΑΙ ΓΙΑ ΤΟ ΡΕΥΜΑ (βήμα 147): με την ακτίνα 32 ο 1048 0 έφτασε τους 53
        θόλους, και από το sol 52 κανένας ηλιακός δεν έβρισκε θέση. Η
        κατανάλωση πήγε στα 253 με 162 παραγωγή, οι αντλίες σταματούσαν, και
        το σενάριο έχτισε 14. Ενα airlock στην άκρη της αποικίας, από το κέντρο
        των θόλων προς τα έξω, που με αυτό χωρά το item ως 8 tiles γύρω του.
        -> ("anchor", (θέση, κομμάτια)) ή None."""
        sb = lambda v: v - 256 if v > 127 else v
        X = self.anchor_ctx()
        domes, dims = X["domes"], X["dims"]
        own = [(sb(d[0]) >> 1, sb(d[1]) >> 1) for d in domes if d[3]]
        if not own:
            return None
        cx = sum(x for x, _ in own) // len(own)
        cy = sum(y for _, y in own) // len(own)
        kind, param, w, h = self.m.read_ram(self.sym["BLD_ITEMS"] + 8 * item, 4)
        tries = 0
        for _, tx, ty in sorted((max(abs(tx - cx), abs(ty - cy)), tx, ty)
                                for ty in range(cy - FAR_R, cy + FAR_R)
                                for tx in range(cx - FAR_R, cx + FAR_R)):
            a = self.with_airlock(tx, ty, X)
            if a is None:
                continue
            at, pieces, b, sl = a
            for qy in range(ty - 8, ty + 9):
                for qx in range(tx - 8, tx + 9):
                    if not all(reach.ok_tile(b[reach.widx(qx + i, qy + j)]) for i in range(w) for j in range(h)) \
                            or self.on_shore(qx, qy, w, h):
                        continue
                    if reach.plan(b, domes, sl, dims, kind, param, w, h, 2 * qx + w, 2 * qy + h)["ok"]:
                        return "anchor", (at, pieces)
            tries += 1
            if tries >= 40:
                break
        return None

    def on_shore(self, tx, ty, w, h):
        """Το αποτύπωμα πατά μια κρατημένη θέση αντλίας ή το μονοπάτι της."""
        return (any(tx < x + 3 and x < tx + w and ty < y + 3 and y < ty + h
                    for x, y in self.shore)
                or any((tx + i, ty + j) in self.shore_path for i in range(w) for j in range(h)))

    def shore_cut(self, p):
        """Οι διάδρομοι ή το μονοπάτι του reach.plan περνούν από μια κρατημένη θέση
        ή από το μονοπάτι της."""
        tl = [t for c in p["corridors"] for t in c[4]] + (p["path"][2] if p["path"] else [])
        return any(t in self.shore_path or any(x <= t[0] < x + 3 and y <= t[1] < y + 3
                                               for x, y in self.shore) for t in tl)

    def spot_zone(self, item, zone, R=None):
        """Η ΔΙΑΤΑΞΗ (βήμα 131). zone «core»: ένας θόλος στη σειρά ενός άλλου
        αν γίνεται, με ως 4 κομμάτια διαδρόμου αν γίνεται, με τα λιγότερα, όσο
        πιο κοντά στο κέντρο των θόλων. zone «edge»: μια δομή όσο πιο μακριά
        από τους θόλους, ως 12 tiles, ώστε να μην κόβει τους διαδρόμους των
        επόμενων — το σχέδιο long τις έβαζε σε σταθερά σημεία μέσα στη γη της
        αποικίας, και σε κόσμους με χώρο έμενε «PATH BLOCKED».
        -> (θέση, κομμάτια) ή None."""
        domes, structs = self.own()
        if not domes:
            return None
        cx = sum(x for x, _ in domes) // len(domes)
        cy = sum(y for _, y in domes) // len(domes)
        b4 = self.world()
        dl = [d[:4] for d in self.domes()]
        sl = [t[:7] for t in self.structs()]
        dims = self.m.read_ram(self.L["G_struct_dims"], 64)
        kind, param, w, h = self.m.read_ram(self.sym["BLD_ITEMS"] + 8 * item, 4)
        R = R or (CORE_R[0] if zone == "core" else 20)
        tx0, ty0 = (cx - w) >> 1, (cy - h) >> 1
        spots = [(tx, ty) for ty in range(ty0 - R, ty0 + R + 1)
                 for tx in range(tx0 - R, tx0 + R + 1)]
        best = None
        for tx, ty in spots:
            if not (-60 <= tx and tx + w <= 60 and -60 <= ty and ty + h <= 60):
                continue
            if not all(reach.ok_tile(b4[reach.widx(tx + i, ty + j)])
                       for i in range(w) for j in range(h)):
                continue
            if self.on_shore(tx, ty, w, h):
                continue
            hx, hy = 2 * tx + w, 2 * ty + h
            dist = max(abs(hx - cx), abs(hy - cy))
            if zone == "core":
                # ΣΤΗ ΣΕΙΡΑ: ίδιο x ή y με έναν θόλο και κενό ενός tile, ώστε
                # ο διάδρομος να είναι ένα ευθύ κομμάτι και να μη διασταυρώνει
                # κανέναν. «Οσο πιο κοντά στο κέντρο» σκέτο έφτιαχνε σωρό
                # γύρω από το σκάφος, και μετά από τρεις με έξι θόλους κάθε
                # νέος διάδρομος έβρισκε κάτι μπροστά του (PATH BLOCKED)· ένας
                # αυστηρός κάνναβος πάλι δεν χωρούσε σε στενό έδαφος.
                inline = any((hx == x and abs(hy - y) == LATTICE) or
                             (hy == y and abs(hx - x) == LATTICE) for x, y in domes)
                key = (0, 0 if inline else 1, dist)
            else:
                near = min(max(abs(hx - x), abs(hy - y)) for x, y in domes)
                key = (0, -min(near, 24), dist)
            p = reach.plan(b4, dl, sl, dims, kind, param, w, h, hx, hy)
            if not p["ok"]:
                k = f"λόγος {p['reason']}"
                self.why[k] = self.why.get(k, 0) + 1
                continue
            if self.shore_cut(p):
                continue
            key = (p["pieces"],) + key[1:]
            if zone == "core":
                key = (key[0] > 4, key[1], key[0], key[2])
            else:
                # ΤΑ ΜΟΝΟΠΑΤΙΑ ΤΩΝ ΔΟΜΩΝ ΕΧΟΥΝ ΚΑΤΑΛΗΨΗ (§9.3): ένα μακρύ μονοπάτι
                # είναι φράχτης που κανένας θόλος και κανένας διάδρομος δεν
                # περνά. Πρώτα όσα έχουν ως 3 tiles μονοπάτι — οι δομές μαζί,
                # σε ένα «ναυπηγείο» — και από αυτά όσο πιο μακριά από τους θόλους.
                plen = len(p["path"][2]) if p["path"] else 0
                key = (0, plen > 3, key[1], plen, key[2])
            if best is None or key < best[0]:
                best = (key, (hx, hy))
        if not best:
            return None
        return best[1], (best[0][2] if zone == "core" else 0)

    def dome_sites(self, cap, place=None):
        """Ο ΛΑΙΜΟΣ (βήμα 165): πόσες θέσεις μικρού θόλου περνούν τον κανόνα του
        reach.plan σε όλο τον κόσμο, ως cap — με τον θόλο place = (item, θέση)
        χτισμένο πρώτα, αν δοθεί: το αποτύπωμά του κατειλημμένο, οι διάδρομοι
        του σχεδίου του σφραγισμένοι, και ο ίδιος στους θόλους (ως εργοτάξιο)."""
        t0 = time.time()
        b4 = self.world()
        dl = [list(d[:4]) for d in self.domes()]
        sl = [t[:7] for t in self.structs()]
        dims = self.m.read_ram(self.L["G_struct_dims"], 64)
        ks, ps, ws, hs = self.m.read_ram(self.sym["BLD_ITEMS"] + 8 * DOME_S, 4)
        if place:
            it, at = place
            kind, param, w, h = self.m.read_ram(self.sym["BLD_ITEMS"] + 8 * it, 4)
            p = reach.plan(b4, dl, sl, dims, kind, param, w, h, at[0] & 255, at[1] & 255)
            sb = lambda v: v - 256 if v > 127 else v
            tx, ty = (sb(at[0] & 255) - w) >> 1, (sb(at[1] & 255) - h) >> 1
            wl = bytearray(b4)
            for j in range(h):
                for i in range(w):
                    wl[reach.widx(tx + i, ty + j)] |= 0x10
            b4 = reach.stamp(bytes(wl), p) if p["ok"] else bytes(wl)
            slot = next((d for d in range(64) if not dl[d][3]), None)
            if slot is not None:
                dl[slot] = [at[0] & 255, at[1] & 255, param, 1]
        n = 0
        for ty in range(-60, 61 - hs):
            for tx in range(-60, 61 - ws):
                if not all(reach.ok_tile(b4[reach.widx(tx + i, ty + j)])
                           for i in range(ws) for j in range(hs)):
                    continue
                if self.on_shore(tx, ty, ws, hs):
                    continue
                if reach.plan(b4, dl, sl, dims, ks, ps, ws, hs, 2 * tx + ws, 2 * ty + hs)["ok"]:
                    n += 1
                    if n >= cap:
                        break
            if n >= cap:
                break
        self.neck_t += time.time() - t0
        self.neck_n += 1
        return n

    def fill(self, room, code):
        """ΓΕΜΙΣΜΑ ΠΡΩΤΑ (βήμα 140): μια ελεύθερη υποδοχή σε έναν μεσαίο ή μεγάλο
        θόλο του δωματίου που ήδη λειτουργεί, αντί για νέο θόλο — μία μηχανή,
        8 μέταλλα και 2 βιοπλαστικά, χωρίς θέση και χωρίς διάδρομο.
        -> (κόμβος, at, ό,τι περιμένει υλικά) ή None."""
        sb = lambda v: v - 256 if v > 127 else v
        busy = {tuple(f[1]) for f in self.fits}
        for k, d in enumerate(self.domes()):
            if d[4] != DS_ACTIVE or d[3] != DROOM[room] or not d[2]:
                continue
            at = (sb(d[0]), sb(d[1]))
            free = [i for i in range(MACHINE_COUNT[d[2]]) if d[8 + i] == 255]
            if at in busy or not free:
                continue
            return k, at, self.fit(at, [None] * free[0] + [code])
        return None

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
        ζητήθηκε (για αργότερα, όταν φτάσουν τα υλικά). Ενα φυτό είναι «ό,τι
        ζητήθηκε» όταν είναι της κλάσης του (holds, βήμα 168)."""
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
            if self.holds(self.domes()[d][8 + s], code):
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
            if self.holds(self.domes()[d][8 + s], code):
                left[s] = None
        self.look()
        return left if any(x is not None for x in left) else []

    def holds(self, have, code):
        """ΤΟ ΦΥΤΟ ΤΗΣ ΚΛΑΣΗΣ (βήμα 168): η υποδοχή έχει ό,τι ζητήθηκε. Μια μηχανή
        είναι ο αριθμός της. Ενα φυτό ο κατάλογος του εξοπλισμού το δίνει ως κλάση
        (STARCH-TREE = FT_CLS του src/fit.asm), και η υποδοχή κρατά την ποικιλία
        (fit_new: 0-4 άμυλο, 5-9 λαχανικά, G_plant_class). Ως τότε κανένα φυτό
        δεν ήταν «ό,τι ζητήθηκε»: κάθε θερμοκήπιο έμενε για πάντα στα G.fits, το
        fill δεν γέμιζε ποτέ θόλο με εκκρεμότητα, και κάθε μεσαίο θερμοκήπιο είχε
        ένα φυτό στις τέσσερις υποδοχές — στο v166 107 θερμοκήπια, 332 υποδοχές
        και 107 φυτά στους οκτώ κόσμους, και κάθε «άμυλο+» έχτιζε νέο θόλο. Ετσι
        από το βήμα 120."""
        if code < STARCH:
            return have == code
        if self.pclass is None:
            self.pclass = self.m.read_ram(self.L["G_plant_class"], 12)
        return have < len(self.pclass) and self.pclass[have] == code - STARCH

    def trade(self, net):
        """Η γραμμή του εμπόρου (ΜΕΤΑΦΟΡΑ, M), ένα αγαθό τη φορά: δεξιά ώσπου το
        tr_g να είναι αυτό, και ΠΑΝΩ ή ΚΑΤΩ ώσπου το TR_NET του να είναι όσο
        θέλει — με επαλήθευση μετά από κάθε πάτημα, όπως ο κατάλογος του
        tools/balance.py. Μετά SPACE. -> True αν έγινε η συμφωνία, αλλιώς γιατί όχι."""
        from cpc import KEY_UP, KEY_DOWN, KEY_RIGHT, KEY_SPACE
        m, sym = self.m, self.sym
        tn = self.L["G_crew"]                       # TR_NET (src/lines.asm)
        sgn = lambda v: v - 256 if v > 127 else v
        self.look()
        self.tap("T")
        self.tap("M")
        if m.peek(sym["UI_STATE"]) != 7 or m.peek(sym["AC_MODE"]) != 3:
            self.look()
            return "η γραμμή δεν άνοιξε"
        for g, n in enumerate(net):
            if not n:
                continue
            for _ in range(15):
                if m.peek(sym["TR_G"]) == g:
                    break
                self.tap(KEY_RIGHT)
            if m.peek(sym["TR_G"]) != g:
                break
            for _ in range(40):
                have = sgn(m.peek(tn + g))
                if have == n:
                    break
                self.tap(KEY_UP if have < n else KEY_DOWN)
        ok = all(sgn(m.peek(tn + g)) == n for g, n in enumerate(net)) \
            and m.peek(sym["UI_STATE"]) == 7
        if ok:
            self.tap(KEY_SPACE)
            m.run_frames(6)
        done = m.peek(self.X["EC_SHKIND"]) == 3      # SK_DEALT
        self.look()
        return True if done else "SPACE χωρίς συμφωνία" if ok else "η γραμμή δεν δέχτηκε τα ποσά"

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


# --------------------------------------------------------------------------
# ΤΟ ΕΜΠΟΡΙΟ (βήμα 139): ο παίκτης αγοράζει ό,τι του λείπει με ό,τι του περισσεύει
# --------------------------------------------------------------------------
TRADE_NAMES = ["COINS", "FOOD", "ORE", "METAL", "BIOPL", "PROC", "SPARES", "MEDI", "GUNS",
               "BOTS", "STARCH", "VEG", "HERBS", "MEAT"]


def trade_plan(G):
    """Ο,τι θα έκανε ένας παίκτης με τον έμπορο: net[απόθεμα] σε μονάδες — >0
    παίρνει, <0 δίνει — και τα νομίσματα στη θέση 0 σε δεκάδες, όπως η γραμμή
    (src/lines.asm). None αν δεν αξίζει.

    ΠΑΙΡΝΕΙ, με αυτή τη σειρά: μέταλλο ως τα 200· μετάλλευμα ως τα 60, όσο το
    μέταλλο είναι κάτω από 100 και υπάρχει μηχανή METAL (2 -> 2, και φθηνότερο:
    αξία 10 έναντι 15)· όπλα ως τρία από τους δώδεκα αποίκους (οι εισβολείς
    έρχονται στους είκοσι)· ανταλλακτικά ως δέκα· βιοπλαστικό ως 40· και τρόφιμα
    όταν τα γεύματα είναι κάτω από πέντε sol. ΔΙΝΕΙ: πρώτα τα νομίσματα, που
    αλλιώς δεν κάνουν τίποτα· μετά ό,τι περισσεύει πάνω από ένα απόθεμα — το
    βιοπλαστικό πάνω από 60, άμυλο, λαχανικά και κρέας πάνω από έξι ανά άποικο
    (και 60), τα βότανα πάνω από 20. Οσα δίνει κουβαλιούνται σε φορτία των
    δέκα (βήμα 98): τα νομίσματα όχι."""
    import econ as EC
    p, b6 = G.m.peek, G.bank(6)
    x = G.L["G_node_occ"] - 0x4000 + 240                 # EC_X (βήμα 172· ως τότε 128 + 100)
    mk = p(G.X["EC_MARKUP"])
    c0 = G.X["EC_MARKUP"] + 1                            # EC_CARGO
    cargo = {p(c0 + 2 * k): p(c0 + 2 * k + 1) for k in range(EC.MER_SLOTS) if p(c0 + 2 * k)}
    cargo[0] = b6[x + 11]                                # EC_MCOIN, σε δεκάδες
    coins = b6[x + 6] | b6[x + 7] << 8
    st = [G.stock(k) for k in range(14)]
    alive = G.rows[-1]["alive"]
    V, LOT = EC.TRADE_VALUE, EC.TRADE_LOT
    price = lambda g: V[g] + (V[g] * mk + 50) // 100
    net = [0] * 14
    # ό,τι μπορεί να δώσει, σε αξία
    keep = max(60, 6 * alive)
    spare = {4: st[4] - 60, 10: st[10] - keep, 11: st[11] - keep, 13: st[13] - keep,
             12: st[12] - 20}
    spare = {g: min(99, max(0, n)) // LOT[g] * LOT[g] for g, n in spare.items()}
    budget = 10 * min(coins // 10, 99) + sum(n * V[g] for g, n in spare.items())
    # ό,τι θέλει
    metal_mach = any(METAL in d[3] for d in G.rows[-1].get("dm", []))
    # ΤΑ ΑΝΤΑΛΛΑΚΤΙΚΑ ΠΡΩΤΑ ΚΑΤΩ ΑΠΟ ΤΟ ΑΠΟΘΕΜΑ (βήμα 143): πίσω από το μέταλλο
    # ως τα 200 δεν έμενε τίποτα γι' αυτά, και οι 1048 και C0DE δεν αγόρασαν
    # κανένα σε 60 sol.
    res = 4 + alive // 8                                 # spare_res
    want = [(6, res + 4 - st[6])] if st[6] < res else []
    want += [(3, 200 - st[3])]
    if st[3] < 100 and metal_mach:
        want.append((2, 60 - st[2]))
    if alive >= 12:
        want.append((8, 3 - st[8]))
    want += [(6, 10 - st[6]), (4, 40 - st[4])]
    if st[1] < 5 * alive:
        want.append((1, 5 * alive - st[1]))
    take = 0
    for g, n in want:
        while n > 0 and net[g] + LOT[g] <= cargo.get(g, 0) \
                and take + LOT[g] * price(g) <= budget:
            net[g] += LOT[g]
            take += LOT[g] * price(g)
            n -= LOT[g]
    if not take:
        return None
    # ό,τι δίνει: πρώτα νομίσματα, μετά τα περισσεύματα, το μεγαλύτερο πρώτο
    give = 0
    while give < take and -net[0] < min(coins // 10, 99):
        net[0] -= 1
        give += 10
    for g, n in sorted(spare.items(), key=lambda t: -t[1] * V[t[0]]):
        while give < take and -net[g] + LOT[g] <= n:
            net[g] -= LOT[g]
            give += LOT[g] * V[g]
    return net if give >= take else None


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
def step(name, item, near, room=None, codes=(), after=(), when=None, again=False, zone=None,
         fill=False, grow=False, aside=False, seq=False):
    """aside (βήμα 143): το στάδιο δοκιμάζεται σε κάθε δείγμα, έξω από τη σειρά —
    ούτε το κρατά πίσω ένα στάδιο που δεν πληρώνεται, ούτε κρατά αυτό τα
    επόμενα όταν δεν πληρώνεται.
    seq (βήμα 149): τα after φτάνει να ΜΠΗΚΑΝ, όχι να χτίστηκαν — τα βήματα του
    tutorial, όπου το εργοτάξιο μετράει."""
    return dict(name=name, item=item, near=near, room=room, codes=list(codes),
                after=list(after), when=when, again=again, zone=zone, fill=fill, grow=grow,
                aside=aside, seq=seq)


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
    # Η ΤΡΟΦΗ ΝΑ ΑΝΕΒΑΙΝΕΙ ΟΣΟ ΘΑ ΦΑΝΕ ΟΙ ΤΕΣΣΕΡΙΣ (βήμα 138), περίπου ένα
    # γεύμα ο καθένας το sol — όχι απλώς να μην πέφτει: ένα κυλικείο φτάνει
    # για έξι, και μετά το πλοίο η τροφή έπεφτε ως την πείνα. Με γεμάτη
    # αποθήκη τροφίμων (δέκα sol) δεν μπορεί να ανέβει, και φτάνει.
    grows = food[-1] - food[0] >= 4 or food[-1] >= 10 * want
    # ΜΕ ΓΕΜΑΤΗ ΑΠΟΘΗΚΗ (βήμα 163, η επιλογή του χρήστη): το παιχνίδι σταματά
    # τους κήπους και κρατά μόνο το σπανιότερο υλικό κάτω από 30 (βήμα 142),
    # οπότε η τροφή ΔΕΝ μπορεί να ανέβει και τα δύο άλλα υλικά πέφτουν όσο
    # τρώγονται. Στο v162d η αποθήκη ήταν γεμάτη μέσα στο sol στο 86% των
    # δειγμάτων από το sol 40, γεμάτη κυρίως τροφή και υλικά της, και το
    # πλοίο περνούσε στο 4,8%: το «να ανεβαίνει» αποτύγχανε 1.174 φορές στις
    # 2.422. Τότε η αποικία δεν είναι κοντά στην πείνα· την κρατά το όριο.
    # Η τροφή μετρά ως αρκετή χωρίς να ανεβαίνει, και ένα υλικό που πέφτει
    # σταματά το πλοίο μόνο κάτω από ένα sol (want). Οι πέντε μέρες τροφής
    # μένουν: με τρεις (v163b) ήρθαν πλοία με το κρέας στο 0-3 και πέθαναν 39
    # από πείνα. 518 ζωντανοί στο sol 120 αντί για 428, 315 στο sol 60 αντί
    # για 255, κανένας θάνατος από πείνα (n163a, ένα nop: 524).
    full = any(r["full"] for r in rows)
    if full:
        grows = True
    # ΚΑΙ ΤΑ ΥΛΙΚΑ ΤΟΥ ΓΕΥΜΑΤΟΣ ΚΑΙ ΤΟ ΝΕΡΟ (βήμα 140): δεν πέφτουν, ή φτάνουν για
    # πέντε sol. Τα γεύματα ανέβαιναν από τα αποθέματα, και στο BEEF 0 οι
    # τριάντα επτά έμειναν χωρίς νερό για το οξυγόνο, χωρίς θέση για αντλία.
    # Με δέκα sol οι αποικίες έμεναν στους δεκαοκτώ (μέσος 19,0 έναντι 25,3).
    # Το νερό δεν μπαίνει στην αποθήκη (βήμα 122): πάντα πέντε sol.
    for k in ((S_STARCH_I, S_VEG_I, S_MEAT_I, S_WATER) if G.grow else ()):
        v = [r["stock"][k] for r in rows]
        if v[-1] < v[0] and v[-1] < (want if full and k != S_WATER else 5 * want):
            return False
    return (min(r["o2p"] for r in rows) >= O2_PER_COL * want
            and food[-1] >= 5 * want and grows)


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


# --------------------------------------------------------------------------
# ΠΕΡΑ ΑΠΟ ΤΟΥΣ ΕΙΚΟΣΙ (βήμα 131)
# --------------------------------------------------------------------------
LATTICE = 10                       # μισά tiles: θόλος S 4 tiles + διάδρομος 1
# Τα D_ROOM του src/const.asm: ό,τι γράφει ο πίνακας θόλων στο byte 3.
D_CONTROL, D_QUARTERS, D_CANTEEN, D_OXYGEN, D_GREEN, D_STORAGE, D_AIRLOCK, D_FACTORY, \
    D_LAB, D_MEDBAY = range(1, 11)
S_STARCH_I, S_VEG_I, S_MEAT_I, S_SPARE_I = 10, 11, 13, 6


def last(G, n=8):
    """Τα δείγματα του τελευταίου sol (ένα ανά όγδοο)."""
    return G.rows[-n:]


def cool(G, name, sols=1.0):
    """Ενα στάδιο «ξανά» όχι συχνότερα από μία φορά το sol: το αποτέλεσμα ενός
    θόλου φαίνεται αφού χτιστεί και στελεχωθεί."""
    return G.sol() - G.lastb.get(name, -99) >= sols


def spare_res(G):
    """ΤΟ ΑΠΟΘΕΜΑ ΤΩΝ ΑΝΤΑΛΛΑΚΤΙΚΩΝ (βήμα 143, η επιλογή του χρήστη: μόνο ο
    παίκτης): τέσσερα, και ένα ακόμη ανά οκτώ αποίκους. Στο g142 τέσσερις
    αποικίες έμειναν χωρίς αέρα μέσα σε δύο sol από μια βλάβη OXYGEN με 0
    ανταλλακτικά — 90 θάνατοι — και μόνο 2 από τις 24 είχαν μηχανή SPARES: το
    στάδιο ήταν προτελευταίο, και ό,τι δεν πληρωνόταν πιο πάνω το κρατούσε."""
    return 4 + G.rows[-1]["alive"] // 8


def machines(G, code):
    """Οσες μηχανές code έχουν μπει (ή περιμένουν υλικά) σε θόλους."""
    n = sum(d[8:16].count(code) for d in G.domes() if d[4] and d[3] != D_GREEN)
    return n + sum(f[2].count(code) for f in G.fits)


def plants(G, code):
    return sum(d[8:16].count(code) for d in G.domes() if d[4] and d[3] == D_GREEN) + \
        sum(f[2].count(code) for f in G.fits)


def demand(name, test, sols=1.0):
    """Ενα στάδιο «ξανά» που χτίζεται όταν το test(G) το ζητά, όχι πιο συχνά από
    μία φορά στα sols, και ποτέ πριν από ένα ολόκληρο sol δειγμάτων."""
    return lambda G: len(G.rows) >= 8 and cool(G, name, sols) and test(G)


def o2_short(G):
    rows = last(G)
    return max(r["o2p"] for r in rows) < O2_PER_COL * (rows[-1]["alive"] + 4)


def water_short(G):
    w = [r["stock"][S_WATER] for r in last(G)]
    # Και κολλημένο στο μηδέν (βήμα 137): δεν «πέφτει» πια, και ως τότε το
    # σενάριο δεν έχτιζε αντλία με το νερό στο 0 για πάνω από δεκαπέντε sol.
    # ΟΧΙ ΑΝ ΛΕΙΠΕΙ ΤΟ ΡΕΥΜΑ (βήμα 147): χωρίς όλο το ρεύμα οι αντλίες
    # σταματούν, και στον 1048 0 το σενάριο έχτισε 14, έξι ρεύματος η καθεμία,
    # με το ρεύμα κομμένο τα δύο τρίτα του χρόνου. Οι νύχτες είναι το ένα τρίτο.
    if sum(1 for r in last(G) if r["pok"] != 1) * 2 > len(last(G)):
        return False
    return (w[-1] < w[0] or w[-1] < 5) and w[-1] < 60 + 5 * G.rows[-1]["alive"]


def power_short(G, night):
    """Το ρεύμα κόπηκε στο τελευταίο μισό sol, τη μέρα (λείπει παραγωγή) ή τη
    νύχτα (λείπει αποθήκη), και καμία δομή ρεύματος δεν χτίζεται ήδη. Με
    όλο το sol, νύχτες που είχαν περάσει έχτιζαν ξανά και ξανά.

    ΚΑΙ Η ΝΥΧΤΑ ΜΕ ΜΠΑΤΑΡΙΑ ΠΟΥ ΔΕΝ ΓΕΜΙΣΕ ΘΕΛΕΙ ΗΛΙΑΚΟ, ΟΧΙ ΣΥΛΛΕΚΤΗ (βήμα
    138): αν στο τελευταίο sol η μπαταρία δεν έφτασε το 90% της χωρητικότητας,
    η μέρα δεν αφήνει περίσσευμα, και ένας ακόμη συλλέκτης μένει άδειος. Ως
    τότε το σενάριο έχτιζε συλλέκτες στη σειρά — πέντε στο 1048·0 του 136 —
    με δύο ηλιακούς για 28-35 κατανάλωση."""
    rows = last(G, 4)
    if any(r["storm"] for r in rows):
        return False                        # η θύελλα σκεπάζει τα πάνελ: περνά
    if any(t[4] == DS_BUILDING and t[2] in (0, 1, 2) for t in G.structs()):
        return False
    filled = max(r["bat"] for r in last(G)) >= 0.9 * max(1, G.rows[-1]["bcap"])
    cut = lambda dark: any(r["pok"] != 1 and ((r["pp"] == 0) == dark) for r in rows)
    if night:
        return cut(True) and filled
    return cut(False) or (cut(True) and not filled)


def food_short(G, which):
    """Η τροφή πέφτει και δεν φτάνει για πέντε sol: ποιο από τα τρία υλικά του
    MEALS λείπει, ή «meals» αν υπάρχουν όλα (λείπει μάγειρας ή μηχανή)."""
    rows = last(G)
    f = [r["stock"][S_FOOD] for r in rows]
    want = rows[-1]["alive"] + 4
    short = (f[-1] < f[0] or f[-1] < 5) and f[-1] < 5 * want
    # ΚΑΙ ΟΤΑΝ ΔΕΝ ΑΝΕΒΑΙΝΕΙ ΟΣΟ ΘΕΛΕΙ ΤΟ ΠΛΟΙΟ (βήμα 167): το ship_ok θέλει
    # πέντε sol τροφής που ανεβαίνουν τέσσερα το sol, και ως τότε ο παίκτης
    # ζητούσε μάγειρα μόνο όταν η τροφή έπεφτε. Η τροφή ισορροπούσε κάτω από
    # τα πέντε sol — ούτε έπεφτε ούτε έφτανε — και ούτε πλοίο ερχόταν ούτε
    # μηχανή χτιζόταν: στο v166 το 1048 0 και το ACE1 0 έμειναν στους 74 με
    # 2,6 και 3,0 sol τροφής από το sol 90. Με γεμάτη αποθήκη δεν μπορεί να
    # ανέβει, και δεν ζητά. Με τον κανόνα 617 ζωντανοί στο sol 120 αντί για
    # 606, και κανένας κόσμος πιο κάτω (v167c).
    if G.grow and not short and not any(r["full"] for r in rows):
        short = f[-1] < 5 * want and f[-1] - f[0] < 4
    if not short:
        return False
    st = rows[-1]["stock"]
    low = min((st[S_STARCH_I], "starch"), (st[S_VEG_I], "veg"), (st[S_MEAT_I], "meat"))
    return (low[1] if low[0] < 10 else "meals") == which


def ing_falling(G, k):
    """ΤΟ ΥΛΙΚΟ ΠΡΙΝ ΑΠΟ ΤΟ ΓΕΥΜΑ (βήμα 140): το άμυλο, τα λαχανικά ή το κρέας
    έπεσαν στο τελευταίο sol και δεν φτάνουν για πέντε. Το food_short τα
    ζητούσε μόνο κάτω από δέκα, όταν η τροφή είχε ήδη αρχίσει να πέφτει: στο
    1048 0 τα λαχανικά άδειασαν από 85 στο sol 34 ως 0 στο 43 με τους τριάντα,
    και η αποικία πέθανε ως το 60 με 138 άμυλο στην αποθήκη.

    ΚΑΙ ΜΕ ΓΕΜΑΤΗ ΑΠΟΘΗΚΗ, ΚΑΙ ΜΟΝΟ ΤΟ ΠΙΟ ΑΡΓΟ (βήμα 164, η επιλογή του
    χρήστη). Με γεμάτη αποθήκη το παιχνίδι σταματά τους κήπους (βήμα 142), και
    τα τρία πέφτουν όσο τρώγονται — όχι επειδή λείπουν φυτά. Στο v163a 45
    από τα 54 «άμυλο+» μπήκαν έτσι, και στο sol 120 οι οκτώ αποικίες είχαν 62
    φυτά αμύλου (3 τον γύρο το καθένα) για 54 λαχανικών (2) και 52 VITROMEAT
    (2): 186 άμυλο τον γύρο για 108 και 104, ενώ το γεύμα θέλει ένα από το
    καθένα. Το άμυλο γέμιζε την αποθήκη (στο C0DE 0 392-546) και κρατούσε τα
    άλλα δύο στα 30 του κανόνα. Τώρα, με γεμάτη αποθήκη, ένα υλικό που πέφτει
    ζητά μόνο κάτω από ένα sol, όπως στο ship_ok του βήματος 163, και πάνω από
    ένα sol ένα υλικό
    που βγαίνει ήδη γρηγορότερα από κάποιο άλλο δεν ζητά τίποτα (ing_rates):
    38 φυτά αμύλου για 52 και 50, η αποθήκη γεμάτη στο 23% των δειγμάτων από
    το sol 40 αντί για 49%, 547 ζωντανοί στο sol 120 αντί για 518, κανένας
    θάνατος από πείνα (n164b, ένα nop: 548). Μόνο το πρώτο (v164a): 525."""
    rows = last(G)
    v = [r["stock"][k] for r in rows]
    full = any(r["full"] for r in rows)
    want = rows[-1]["alive"] + 4
    if G.grow and v[-1] >= want:
        rate = ing_rates(G)
        if rate[k] > min(q for kk, q in rate.items() if kk != k):
            return False
    return G.grow and v[-1] < v[0] and v[-1] < (1 if full else 5) * want


def ing_rates(G):
    """Πόσο βγάζουν ανά γύρο οι έτοιμοι θόλοι από καθένα από τα τρία υλικά του
    γεύματος (tools/econ.py): ένα φυτό αμύλου 3, ένα λαχανικών 2 (στο
    θερμοκήπιο οι υποδοχές κρατούν φυτά, 0-4 άμυλο και 5-9 λαχανικά), μια
    VITROMEAT 2."""
    rate = {S_STARCH_I: 0, S_VEG_I: 0, S_MEAT_I: 0}
    for d in G.domes():
        if d[4] != DS_ACTIVE:
            continue
        for c in d[8:16]:
            if d[3] == R_GREEN:
                if c < 5:
                    rate[S_STARCH_I] += 3
                elif c < 10:
                    rate[S_VEG_I] += 2
            elif c == MEAT:
                rate[S_MEAT_I] += 2
    return rate


def need_low(G, k):
    """Πόσοι κατά μέσο όρο στο τελευταίο sol είχαν την ανάγκη k κάτω από 64:
    0 o2, 1 νερό, 2 τροφή, 3 ύπνος."""
    rows = last(G)
    return sum(sum(1 for a in r["need"].values() if a[k] < 64) for r in rows) / len(rows)


def open_sites(G):
    """Εργοτάξια ταυτόχρονα: δύο, τρία από τους δώδεκα (βήμα 131). Στο tutorial
    (βήμα 149) όσα ζητούν τα βήματα: ο παίκτης χτίζει μόλις του το πουν."""
    if G.tut:
        return 99
    return OPEN if not G.rows or G.rows[-1]["alive"] < 12 else OPEN + 1


def plan_tutorial():
    """Τα δεκατέσσερα βήματα του tutorial (βήμα 149, src/tutor.asm), με τη σειρά
    τους: το καθένα μόλις ΜΠΕΙ το προηγούμενο — το εργοτάξιο μετράει. Οι μηχανές
    που λέει η γραμμή: OXYGEN, MEALS, METAL, άμυλο και λαχανικά, MEAT. Το πλοίο
    θέλει τον έλεγχο και την πίστα χτισμένα (ship_call). Δεκατρία ήταν, χωρίς τον
    δεύτερο ηλιακό: το ρεύμα κομμένο το 60% του χρόνου ως το πλοίο (DESIGN §9.6).

    ΚΑΙ ΜΕΤΑ ΤΟ ΠΛΟΙΟ ΟΙ ΚΟΙΤΩΝΕΣ (βήμα 168): το «THE COLONY IS YOURS» μένει ως
    το επόμενο γεγονός. Ως το βήμα 167 το έφερνε ένα fit του θερμοκηπίου που ο
    παίκτης ξαναδοκίμαζε για πάντα (holds: τα φυτά του δεν μετρούσαν ποτέ ως
    μπαλμένα)· με τα φυτά διορθωμένα το θερμοκήπιο γεμίζει στο sol 2,5, και ως
    το sol 14 δεν ερχόταν κανένα γεγονός."""
    return [
        step("ηλιακός", SOLAR, (10, -6)),
        step("οξυγόνο", DOME_S, (6, 2), "oxygen", [OXYGEN], after=["ηλιακός"], seq=True),
        step("airlock", AIRLOCK, (6, 12), after=["οξυγόνο"], seq=True),
        step("αντλία", EXTRACTOR, "water", after=["airlock"], seq=True),
        step("κυλικείο", DOME_S, (18, 2), "canteen", [MEALS], after=["αντλία"], seq=True),
        step("ηλιακός 2", SOLAR, (-8, 6), after=["κυλικείο"], seq=True),
        step("συλλέκτης", COLLECTOR, (-8, -6), after=["ηλιακός 2"], seq=True),
        step("ορυχείο", MINE, "ore", after=["συλλέκτης"], seq=True),
        step("εργοστάσιο", DOME_S, (6, -10), "factory", [METAL], after=["ορυχείο"], seq=True),
        step("θερμοκήπιο", DOME_M, (20, 14), "green", [STARCH, STARCH, VEG, VEG],
             after=["εργοστάσιο"], seq=True),
        step("εργαστήριο", DOME_S, (18, -10), "lab", [MEAT], after=["θερμοκήπιο"], seq=True),
        step("έλεγχος", DOME_S, (30, -10), "control", after=["εργαστήριο"], seq=True),
        step("πίστα", PAD, (-14, -14), after=["έλεγχος"], seq=True),
        step("πλοίο", "ship", None, after=["πίστα", "έλεγχος"]),
        step("κοιτώνες", DOME_S, (30, 2), "quarters", when=lambda G: "πλοίο" in G.lastb),
    ]


def plan_big():
    """Ως εκεί όπου σταματά (βήμα 131): θόλοι μαζεμένοι γύρω από το κέντρο
    τους, δομές στην περιφέρεια (Game.spot_zone), πίστα και έλεγχος αμέσως
    μετά την τροφή για να έρθουν χέρια, και από εκεί και πέρα ό,τι ζητούν οι
    μετρήσεις του τελευταίου sol — όχι σταθεροί αριθμοί αποίκων: οξυγόνο
    που δεν φτάνει για όλους μαζί με τέσσερις ακόμη, νερό που πέφτει, ρεύμα
    που κόπηκε (μέρα: ηλιακός, νύχτα: συλλέκτης), τροφή που πέφτει (ό,τι από
    τα τρία λείπει), βιοπλαστικό και μέταλλο που λείπουν με την πρώτη ύλη
    τους εκεί, ύπνος, αποθήκη."""
    alive = lambda G: G.rows[-1]["alive"]
    st = lambda G, k: G.rows[-1]["stock"][k]
    opening = [
        step("οξυγόνο", DOME_S, (6, 2), "oxygen", [OXYGEN]),
        # Το κυλικείο ΠΡΩΤΟ: χωρίς αυτό δεν πίνει κανείς (δίψα σε 1,7 sol), και
        # στον πάγο #ACE1·1 το μονοπάτι της αντλίας του έκλεινε τη θέση.
        step("κυλικείο", DOME_S, None, "canteen", zone="core", after=["οξυγόνο"]),
        step("ηλιακός", SOLAR, None, zone="edge"),
        step("airlock", AIRLOCK, (6, 12), after=["οξυγόνο"]),
        step("αντλία", EXTRACTOR, "water"),
        step("εργοστάσιο", DOME_S, None, "factory", [METAL], zone="core", after=["οξυγόνο"]),
        step("ορυχείο", MINE, "ore"),
        step("ηλιακός 2", SOLAR, None, zone="edge"),
        step("συλλέκτης", COLLECTOR, None, zone="edge"),
        step("άμυλο", DOME_S, None, "green", [STARCH], zone="core", after=["κυλικείο"]),
        step("λαχανικά", DOME_S, None, "green", [VEG], zone="core", after=["κυλικείο"]),
        step("εργαστήριο", DOME_S, None, "lab", [MEAT], zone="core", after=["κυλικείο"]),
        step("γεύματα", "fit", "κυλικείο", codes=[MEALS], after=["κυλικείο"]),
        step("έλεγχος", DOME_S, None, "control", zone="core", after=["κυλικείο"]),
        step("πίστα", PAD, None, zone="edge", after=["έλεγχος"]),
        step("πλαστικό", DOME_S, None, "factory", [PLASTIC], zone="core", after=["άμυλο"]),
        step("κοιτώνες", DOME_S, None, "quarters", zone="core", after=["κυλικείο"]),
    ]
    more = [
        step("πλοίο", "ship", None, after=["πίστα", "έλεγχος"], when=ship_ok, again=True),
        # ΤΟ ΡΕΥΜΑ ΠΡΩΤΟ (βήμα 138): κομμένο, σταματά κάθε μηχανή εκτός από την
        # υποστήριξη ζωής — και τη MEALS. Μετά την τροφή, ένας ηλιακός 15 μετάλλων
        # περίμενε πίσω από ένα κυλικείο 20 που δεν πληρωνόταν, και η αποικία
        # πεινούσε με 190 άμυλο στην αποθήκη (BEEF·3, ρεύμα 36 για 50-56 τη μέρα).
        step("ηλιακός+", SOLAR, None, zone="edge", after=["ηλιακός 2"],
             when=demand("ηλιακός+", lambda G: power_short(G, False)), again=True),
        step("συλλέκτης+", COLLECTOR, None, zone="edge", after=["συλλέκτης"],
             when=demand("συλλέκτης+", lambda G: power_short(G, True)), again=True),
        # ΤΟ ΝΕΡΟ ΠΡΙΝ ΑΠΟ ΤΟ ΟΞΥΓΟΝΟ (βήμα 168): το οξυγόνο γίνεται από νερό.
        # Ενα «οξυγόνο+» με εννέα κομμάτια διαδρόμου μάζευε μέταλλα δυόμισι sol
        # και κρατούσε πίσω την «αντλία+» των 22: στο BEEF 2 του v168d το νερό
        # 229 -> 0, το οξυγόνο σταμάτησε, και 82 πέθαναν από αέρα.
        step("αντλία+", EXTRACTOR, "water", after=["αντλία"],
             when=demand("αντλία+", water_short, 1.5), again=True),
        step("οξυγόνο+", DOME_S, None, "oxygen", [OXYGEN], zone="core", after=["οξυγόνο"],
             when=demand("οξυγόνο+", o2_short), again=True),
        # ΠΡΙΝ ΑΠΟ ΤΗΝ ΤΡΟΦΗ (βήμα 162, η επιλογή του χρήστη): το ιατρείο, η
        # δεύτερη πόρτα και το δεύτερο Control ήταν τελευταία, και κάθε «+» της
        # τροφής που δεν πληρωνόταν τα κρατούσε πίσω — ενώ όταν μάζευε μέταλλα
        # το έπαιρνε πρώτο ένα μεσαίο θερμοκήπιο με τέσσερα ως εννέα κομμάτια
        # διαδρόμου. Στο m161 το ταβάνι κρατούσε την αποικία στο 19% των
        # δειγμάτων από το sol 20, μόνο 2 κόσμοι από τους 8 έφτασαν τα 80, και
        # ιατρείο χτίστηκε σε 3, δεύτερη πόρτα σε 4. Εδώ, μετά το ρεύμα, το
        # οξυγόνο και το νερό (βήμα 138): 2%, 6 στα 80, ιατρείο σε 7 και πόρτα
        # σε 8, 428 ζωντανοί αντί για 410 και 28 θάνατοι αντί για 32 — με 255
        # στο sol 60 αντί για 290: στο BEEF 0 το ιατρείο στο sol 30 πήρε τα
        # μέταλλα, και το δεύτερο Control ήρθε στο sol 97. Μόνο το Control εδώ
        # (v162a): 420, 290 στο sol 60, ιατρείο σε 2 και πόρτα σε 3. Και τα τρία
        # έξω από τη σειρά (v162c), ή μόνο η πόρτα εδώ (v162e): το 1048 0 έφτασε
        # τους 68-76, έμεινε χωρίς νερό και πέθαναν από αέρα (DESIGN §10.1).
        step("ιατρείο", DOME_S, None, "medbay", zone="core", after=["κοιτώνες"],
             when=lambda G: alive(G) >= 16),
        # ΔΕΥΤΕΡΗ ΠΟΡΤΑ (βήμα 140): στο C0DE 2 ένας μετεωρίτης γύρισε το μόνο
        # airlock σε εργοτάξιο, και όσοι ήταν έξω — και όσοι κατέβαιναν από τα
        # πλοία — δεν είχαν πού να μπουν (12 θάνατοι από τη στολή). Τελευταία
        # ως το βήμα 161: πρώτη στη σειρά δεν άλλαξε τίποτα στο βήμα 140
        # (χτίστηκε σε 17-19 κόσμους και έτσι και αλλιώς, μέσος 15,1 και 13,8 στο
        # sol 60) — στο 161 όμως χτιζόταν σε 3 κόσμους από τους 8.
        step("airlock 2", AIRLOCK, (-24, -24), after=["airlock"],
             when=lambda G: G.grow and alive(G) >= 16),
        # ΤΟ ΤΑΒΑΝΙ (βήμα 140): 6 + 48 ανά Control, ως 80. Με ένα, 54.
        step("έλεγχος+", DOME_S, None, "control", zone="core", after=["έλεγχος"],
             when=lambda G: G.grow and G.rows[-1]["popcap"] < 80
             and G.rows[-1]["popcap"] - alive(G) < 8, again=True),
        step("γεύματα+", DOME_S, None, "canteen", [MEALS], zone="core", fill=True, grow=True, after=["γεύματα"],
             when=demand("γεύματα+", lambda G: food_short(G, "meals")), again=True),
        step("άμυλο+", DOME_S, None, "green", [STARCH], zone="core", fill=True, grow=True, after=["άμυλο"],
             when=demand("άμυλο+", lambda G: food_short(G, "starch") or ing_falling(G, S_STARCH_I)),
             again=True),
        step("λαχανικά+", DOME_S, None, "green", [VEG], zone="core", fill=True, grow=True, after=["λαχανικά"],
             when=demand("λαχανικά+", lambda G: food_short(G, "veg") or ing_falling(G, S_VEG_I)),
             again=True),
        step("εργαστήριο+", DOME_S, None, "lab", [MEAT], zone="core", fill=True, grow=True, after=["εργαστήριο"],
             when=demand("εργαστήριο+", lambda G: food_short(G, "meat") or ing_falling(G, S_MEAT_I)),
             again=True),
        # Η ΑΠΟΘΗΚΗ ΜΕΤΑ ΤΗΝ ΤΡΟΦΗ ΚΑΙ ΤΟ ΡΕΥΜΑ (βήμα 138), όχι τελευταία: εκεί
        # την κρατούσε πίσω κάθε στάδιο που δεν πληρωνόταν, και σε 12 κόσμους
        # δεν χτίστηκε καμία — με την αποθήκη γεμάτη το 36% του χρόνου και το
        # ορυχείο σταματημένο μαζί της.
        # ΜΕΣΑΙΑ ΑΠΟ ΤΗΝ ΠΕΜΠΤΗ (βήμα 140, try_step): 300 αντί για 100, και το
        # παιχνίδι μετρά ως οκτώ θόλους Storage (ROOM_MAX) — το σενάριο είχε
        # φτάσει τους δέκα μικρούς σε τέσσερις κόσμους.
        # ΤΑ ΑΝΤΑΛΛΑΚΤΙΚΑ ΕΞΩ ΑΠΟ ΤΗ ΣΕΙΡΑ (βήμα 143): ως τότε το στάδιο ήταν
        # προτελευταίο και χτίστηκε σε 2 κόσμους από τους 24 (g142: 90 θάνατοι από
        # αέρα). Πριν από την αποθήκη, μέσα στη σειρά: σε 13 κόσμους, αλλά στο sol
        # 50-58 — το κρατούσε ό,τι δεν πληρωνόταν πιο πάνω (g143: 63). Εξω από τη
        # σειρά (aside), σε κάθε δείγμα, κάτω από το απόθεμα: 0 θάνατοι από βλάβη
        # χωρίς ανταλλακτικά, 35 θάνατοι αντί για 159 (g143c). Από τους
        # δεκατέσσερις, ως το βήμα 143 χτιζόταν σε 21 κόσμους και μια SPARES δεν
        # σταματούσε ποτέ — 1 μέταλλο τον γύρο, ~10 το sol, 200-270 ανταλλακτικά
        # με το μέταλλο στο 30 του KEEP_METAL, πάνω από είκοσι 5 αποικίες αντί για
        # 18 (g143b). ΑΠΟ ΤΟ ΒΗΜΑ 144 ΣΤΑΜΑΤΑ ΣΤΑ 20 (SPARES_MAX), και από τους
        # δεκατέσσερις είναι το ασφαλέστερο: 18 θάνατοι, κανένας από αέρα, καμία
        # βλάβη OXYGEN χωρίς ανταλλακτικά, μέσος 25,0 στο sol 60 (g144b· μόνο κάτω
        # από το απόθεμα 36 θάνατοι, οι 23 από το νερό της 1048 0, μέσος 25,3,
        # g144). Και γέμισμα πρώτα: μια υποδοχή ενός μεσαίου εργοστασίου.
        step("ανταλλακτικά", DOME_S, None, "factory", [SPARES], zone="core", fill=True,
             after=["εργοστάσιο"], aside=True,
             when=lambda G: alive(G) >= GROW_AT or st(G, S_SPARE_I) < spare_res(G)),
        step("αποθήκη", DOME_S, None, "storage", zone="core", after=["οξυγόνο"],
             when=storage_due, again=True),
        step("κοιτώνες+", DOME_S, None, "quarters", zone="core", after=["κοιτώνες"], grow=True,
             when=demand("κοιτώνες+", lambda G: need_low(G, 3) >= max(2, alive(G) / 4)),
             again=True),
        step("πλαστικό+", DOME_S, None, "factory", [PLASTIC], zone="core", fill=True, grow=True, after=["πλαστικό"],
             when=demand("πλαστικό+", lambda G: st(G, S_BIOPL) < 25 and st(G, S_STARCH_I) >= 40
                         and machines(G, PLASTIC) < 1 + alive(G) // 10), again=True),
        step("μέταλλο+", DOME_S, None, "factory", [METAL], zone="core", fill=True, grow=True, after=["εργοστάσιο"],
             when=demand("μέταλλο+", lambda G: st(G, S_METAL) < 40 and st(G, S_ORE) >= 30
                         and machines(G, METAL) < 1 + alive(G) // 10), again=True),
        # ΔΕΝ ΧΤΙΖΕΤΑΙ ΠΟΤΕ (βρέθηκε στο βήμα 160): ζητείται κάτω από 40 μέταλλα
        # και κοστίζει 30 + 30 του αποθέματος (reserve), οπότε κάθε αποικία μένει
        # με ένα ορυχείο — και το μέταλλο+ έχει παράθυρο 38-39. Χωρίς το αδιέξοδο
        # (x160a, x160c) τα ορυχεία γίνονται 2-5, με μεγάλη διασπορά: ACE1 1 30 ->
        # 78, ACE1 0 68 -> 27 από αέρα χωρίς ανταλλακτικά. Μένει όπως ήταν, με
        # επιλογή του χρήστη, για ένα βήμα μαζί με τα ανταλλακτικά (DESIGN §15).
        step("ορυχείο+", MINE, "ore", after=["ορυχείο"],
             when=demand("ορυχείο+", lambda G: st(G, S_ORE) < 10 and st(G, S_METAL) < 40
                         and len(G.rows[-1]["mines"]) < 1 + alive(G) // 10, 2.0), again=True),
        # ΚΑΙ ΞΑΝΑ (βήμα 140): στο 1048 3 τα ανταλλακτικά ήταν μηδέν για δέκα sol,
        # και κάθε χαλασμένη μηχανή έμεινε χαλασμένη. Από το βήμα 143 κάτω από
        # το απόθεμα (spare_res), όχι κάτω από 6.
        step("ανταλλακτικά+", DOME_S, None, "factory", [SPARES], zone="core",
             after=["ανταλλακτικά"], fill=True, grow=True, again=True,
             when=demand("ανταλλακτικά+", lambda G: G.grow and st(G, S_SPARE_I) < spare_res(G)
                         and machines(G, SPARES) < 1 + alive(G) // 15, 2.0)),
    ]
    return opening + more


def plan_bigs():
    """Το big με την αποθήκη πρώτη (βήμα 137, μέτρηση): ένας θόλος Storage
    μόλις τα αγαθά πλησιάσουν το όριο, πριν από κάθε άλλο «ξανά» — στο big
    ήταν τελευταίο, και κάθε ανάγκη που δεν πληρωνόταν το κρατούσε πίσω:
    καμία αποθήκη σε 12 κόσμους, γεμάτη το 36% του χρόνου μετά το sol 15."""
    plan = plan_big()
    k = next(i for i, s in enumerate(plan) if s["name"] == "αποθήκη")
    s = plan.pop(k)
    plan.insert(next(i for i, t in enumerate(plan) if t["name"] == "πλοίο"), s)
    return plan


PLANS = {"tutorial": plan_tutorial, "base": plan_base, "lean": plan_lean, "spares": plan_spares, "mine": plan_mine,
         "mine_ns": plan_mine_ns, "grow": plan_grow, "store": plan_store, "long": plan_long,
         "big": plan_big, "bigs": plan_bigs}


def tweak(G, spec):
    """Πειράγματα για τη μέτρηση, πάνω στο τρέχον παιχνίδι: spares=N, metal=N,
    bio=N, ore=N, food=N (αποθέματα), nofault (το ec_break = ret: ούτε βλάβες
    ούτε εκλάμψεις ούτε μηχανές από μετεωρίτες), fault=M (η μάσκα της βλάβης,
    #7F = 1/128, #FF = 1/256) — και από το βήμα 137 dig (το ορυχείο σκάβει
    με γεμάτη αποθήκη), raw (και μετάλλευμα και μέταλλο έξω από την αποθήκη),
    land=Ε:Μ:Β:Γ:Φ (τα ποσοστά των πλοίων)."""
    import codeat
    idx = dict(water=0, food=1, ore=2, metal=3, bio=4, spares=6, guns=8)
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
        elif k == "plastic":
            # Η απόδοση της μηχανής PLASTIC (βήμα 131): το qty της συνταγής 2
            # (G_recipes + 10 * 2 + 7), 1 στο παιχνίδι — όπως το iron του 124.
            G.m.poke(G.L["G_recipes"] + 10 * 2 + 7, int(v, 0))
        elif k == "eng_op":
            # Ο μηχανικός και στις Operate (job_roles[J_OPERATE] = εργάτης |
            # μηχανικός | βιολόγος): πόσο λείπει ένας χειριστής.
            G.m.poke(G.sym["JOB_ROLES"] + 1, 0x07)
        elif k == "feed":
            # ΥΛΙΚΑ ΧΩΡΙΣ ΤΕΛΟΣ (βήμα 131, μέτρηση): σε κάθε δείγμα το μέταλλο
            # και το βιοπλαστικό ανεβαίνουν ως M και B — για να φανεί τι γίνεται
            # πάνω από τους είκοσι όταν δεν σταματά τίποτα στην αρχή. Οχι πάνω
            # από την αποθήκη: γεμάτη, σταματούν οι κήποι.
            fm, _, fb = v.partition(":")
            G.feed = (int(fm, 0), int(fb or "0", 0))
        elif k in ("dig", "raw"):
            # ΤΟ ΟΡΥΧΕΙΟ ΣΚΑΒΕΙ ΚΑΙ ΜΕ ΓΕΜΑΤΗ ΑΠΟΘΗΚΗ (βήμα 137, μέτρηση): το
            # «ld a,(ec_full) / or a / jr nz,hlp_pile» του hl_pile χωρίς το jr.
            f = G.sym["EC_FULL"]
            a = codeat.find(G.m, G.sym["HL_PILE"], [0x3A, f & 255, f >> 8, 0xB7, 0x20], 40)
            assert a, "δεν βρέθηκε το ec_full του hl_pile"
            codeat.poke(G.m, a + 4, 0)
            codeat.poke(G.m, a + 5, 0)
            # raw: ΚΑΙ ΜΕΤΑΛΛΕΥΜΑ ΚΑΙ ΜΕΤΑΛΛΟ ΕΞΩ ΑΠΟ ΤΗΝ ΑΠΟΘΗΚΗ, όπως το νερό:
            # το st_check δεν τα αθροίζει (τα «ld de,(EC_STOCK + 4|6) / add
            # hl,de» του ξεδιπλωμένου αθροίσματος γίνονται nop). Το ορυχείο
            # σκάβει με γεμάτη, αφού το μετάλλευμα δεν πιάνει χώρο.
            s = G.g                         # EC_STOCK = G_econ_state
            for off in (4, 6) if k == "raw" else ():
                a = codeat.find(G.m, G.sym["ST_CHECK"],
                                [0xED, 0x5B, (s + off) & 255, (s + off) >> 8, 0x19], 120)
                assert a, f"δεν βρέθηκε το EC_STOCK + {off} του st_check"
                for i in range(5):
                    codeat.poke(G.m, a + i, 0)
        elif k == "land":
            # Η ΓΡΑΜΜΗ ΤΩΝ ΕΙΔΙΚΟΤΗΤΩΝ (βήμα 91) όπως θα την έβαζε ο παίκτης
            # (βήμα 137, μέτρηση): land=Ε:Μ:Β:Γ:Φ σε δέκατα, άθροισμα 10 —
            # εργάτης, μηχανικός, βιολόγος, γιατρός, φρουρός (EC_LAND, +92).
            sh = [int(x) for x in v.split(":")]
            assert len(sh) == 5 and sum(sh) == 10, "land=Ε:Μ:Β:Γ:Φ, άθροισμα 10"
            for i, x in enumerate(sh):
                G.m.poke(G.g + 92 + i, x)
        elif k in ("skeep", "bmax"):
            # Η PLASTIC ΣΤΑΜΑΤΑ (βήμα 138, μέτρηση): σε κάθε δείγμα, όσο το άμυλο
            # είναι κάτω από N (skeep) ή το βιοπλαστικό N και πάνω (bmax), η
            # ποσότητα αμύλου της συνταγής της (G_recipes + 10 * 2 + 1) γίνεται
            # 255 και δεν τρέχει· αλλιώς 2. Η PLASTIC έτρωγε όλο το άμυλο: στο
            # C0DE·1 203 -> 0 σε 18 sol, βιοπλαστικό 8 -> 298, γεύματα 0.
            G.plast = (k, int(v, 0))
        elif k == "nogrow":
            # χωρίς γέμισμα, μεσαίους θόλους, μεγαλύτερη ακτίνα και δεύτερο
            # Control (βήμα 140): ο παίκτης του 139, για σύγκριση
            G.grow = False
        elif k == "notrade":
            # χωρίς εμπόριο (βήμα 139): ο παίκτης του 138, για σύγκριση
            G.trader = False
        elif k == "foehit":
            # Ο,ΤΙ ΠΑΙΡΝΕΙ ΕΝΑΣ ΕΙΣΒΟΛΕΑΣ ΑΠΟ ΕΝΑΝ ΑΠΟΙΚΟ ανά περιστροφή (βήμα
            # 138, μέτρηση): FOE_HIT, 32 στο παιχνίδι («sub FOE_HIT / jr nc» του
            # fo_tick).
            a = codeat.find(G.m, G.sym["FO_TICK"], [0xD6, 32, 0x30], 400)
            assert a, "δεν βρέθηκε το sub FOE_HIT"
            codeat.poke(G.m, a + 1, int(v, 0))
        elif k == "reserve":
            # Η ΡΕΖΕΡΒΑ ΤΗΣ ΜΠΑΤΑΡΙΑΣ (βήμα 138, μέτρηση): RESERVE_CYC κύκλοι
            # υποστήριξης ζωής, 8 στο παιχνίδι (τρία add hl,hl στο ef_balance)·
            # reserve=4 ή 2 σβήνει ένα ή δύο. Μια νύχτα είναι 4,7 κύκλοι.
            e = G.X["EC_EPOWER"]
            a = codeat.find(G.m, G.sym["EF_BALANCE"], [0x2A, e & 255, e >> 8, 0x29, 0x29, 0x29, 0xEB], 80)
            assert a, "δεν βρέθηκε η ρεζέρβα του ef_balance"
            for i in range({8: 0, 4: 1, 2: 2}[int(v)]):
                codeat.poke(G.m, a + 3 + i, 0)
        elif k == "fault":
            a = codeat.find(G.m, G.sym["EV_FAULT"], [0x7D, 0xE6, 0x7F], 40)
            assert a, "δεν βρέθηκε το and #7F του ev_fault"
            codeat.poke(G.m, a + 2, int(v, 0))
        else:
            raise SystemExit(f"άγνωστο πείραγμα {t}")


def ready(G, s):
    if s.get("seq"):
        return all(a in G.built for a in s["after"])
    return all(a in G.built and G.state(G.built[a][0]) == DS_ACTIVE for a in s["after"])


# ΚΑΙ ΤΑ ΓΕΥΜΑΤΑ (βήμα 168): με την αντλία πριν από το οξυγόνο, οι αντλίες
# έπαιρναν πρώτες το μέταλλο, και η «γεύματα+» περίμενε πίσω από τα 30 με
# άμυλο 340 και λαχανικά 315 στην αποθήκη: σε δύο από τα τρία batch 7 πέθαναν
# από πείνα στο sol 106-118. Χωρίς το απόθεμα, κανένας (v168f, n168f).
LIFE = ("οξυγόνο+", "αντλία+", "airlock 2", "γεύματα+")


def reserve(G, s):
    """ΤΟ ΑΠΟΘΕΜΑ ΤΟΥ ΜΕΤΑΛΛΟΥ (βήμα 140): από τους δεκατέσσερις, ένα κτίσμα δεν
    αφήνει λιγότερα από KEEP_METAL (30) — εκτός από το οξυγόνο, το νερό και
    τη δεύτερη πόρτα. Κάτω από 30 το παιχνίδι σταματά ό,τι τρώει μέταλλο
    (βήμα 127), και το σενάριο το κρατούσε εκεί το 57% του χρόνου: χωρίς
    ανταλλακτικά για δέκα sol, και η δεύτερη πόρτα δεν πληρωνόταν ποτέ."""
    if not G.grow or G.rows[-1]["alive"] < GROW_AT or s["name"] in LIFE:
        return 0
    return 30


def try_step(G, s):
    """-> True αν το στάδιο έγινε (και φεύγει από τη λίστα)."""
    G.need = None
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
    if G.grow and s.get("fill") and s["codes"] and G.stock(S_METAL) >= 8 + reserve(G, s) and G.stock(S_BIOPL) >= 2:
        f = G.fill(s["room"], s["codes"][0])
        if f is not None:
            node, at, left = f
            G.event(f"γέμισμα «{s['name']}» στον θόλο {node}: "
                    f"{'όλος' if not left else 'περιμένει ' + str(left)}")
            if left:
                G.fits.append([s["name"], at, left])
            G.built[s["name"]] = (node, at)
            return True
    item = DOME_M if G.grow and s.get("grow") and G.rows[-1]["alive"] >= GROW_AT else s["item"]
    # Η ΑΠΟΘΗΚΗ ΜΕΣΑΙΑ ΜΟΝΟ ΚΟΝΤΑ ΣΤΟ ΟΡΙΟ ΤΩΝ ΟΚΤΩ (ROOM_MAX, βήμα 140): από την
    # πέμπτη, και μόνο όταν πληρώνεται. Πάντα μεσαία, ή μεσαίοι θόλοι μόνο όταν
    # πληρώνονται, το σενάριο έχτιζε 30-36 αποθήκες σε 24 κόσμους αντί για 88,
    # και η αποθήκη έμενε γεμάτη το 40-42% του χρόνου (μέσος 13,8-15,1 αντί
    # για 20,7 στο sol 60).
    if G.grow and s["room"] == "storage":
        n = sum(1 for d in G.domes() if d[4] and d[3] == R_STORAGE)
        item = DOME_M if (n >= 4 and G.stock(S_METAL) >= COST[DOME_M][0] + reserve(G, s)
                          and G.stock(S_BIOPL) >= COST[DOME_M][1]) else DOME_S
    m, bp = COST[item]
    m += reserve(G, s)
    if item == MINE and not any(t[2] == MINE_K and t[4] for t in G.structs()):
        m = 0                               # το πρώτο ορυχείο δωρεάν (βήμα 123)
    if G.stock(S_METAL) < m or G.stock(S_BIOPL) < bp:
        G.need = (m, bp)                    # ΓΙΑ ΤΗ ΜΕΤΡΗΣΗ (βήμα 160): τι θέλει
        return False                        # ούτε χωρίς διαδρόμους: μην ψάξεις
    # ΟΙ ΔΥΟ ΤΕΛΕΥΤΑΙΕΣ ΘΕΣΕΙΣ ΔΟΜΩΝ ΓΙΑ ΤΙΣ ΑΝΤΛΙΕΣ (βήμα 147): στον 1048 0 οι 32
    # γέμισαν (11 ηλιακοί, 8 airlock, 7 αντλίες) και η όγδοη αντλία δεν έμπαινε·
    # το νερό τελείωσε, οι φρουροί πήγαιναν στις ανάγκες τους και δεν πολεμούσαν,
    # και δύο επιδρομές σκότωσαν 78 στα sol 94 και 102.
    if item in (SOLAR, TURBINE, COLLECTOR, MINE, AIRLOCK, PAD) and G.free_structs() <= SLOT_KEEP:
        return None
    key = (s["name"], item, sum(1 for d in G.domes() if d[4]) + sum(1 for t in G.structs() if t[4]))
    if G.spot_cache.get(key, 0) is None:
        return None                         # ίδια αποικία, ίδια απάντηση
    near = s["near"]
    got = None
    anchor = False
    G.why = {}
    G.keep_shore()
    if s.get("zone"):
        # ΟΛΟ ΚΑΙ ΠΙΟ ΜΑΚΡΙΑ (βήμα 140): στα 14 tiles από το κέντρο οι αποικίες
        # των τριάντα δεν έβρισκαν θέση για τροφή, και πέθαιναν ως το sol 60.
        # ΚΑΙ Ο ΜΙΚΡΟΣ ΟΤΑΝ Ο ΜΕΣΑΙΟΣ ΔΕΝ ΧΩΡΑ: στο 1048 1 τα «+» έμειναν χωρίς
        # θέση στους δεκατέσσερις, ενώ έξι αποθήκες βρήκαν.
        # ΚΑΙ ΣΤΑ 32 (βήμα 147): στα 120 sol τέσσερις αποικίες των 47-54 δεν
        # έβρισκαν θέση για δεύτερο Control ως τα 26, και το ταβάνι έμενε 54.
        # ΚΑΙ ΣΤΑ 44 ΚΑΙ 60 (βήμα 160): μια αποικία που γέμισε την κοιλάδα της
        # μεγαλώνει μακρόστενη, και οι θέσεις που περνούν τον κανόνα είναι πια
        # μακριά από το κέντρο των θόλων — στο C0DE 0 του βήματος 159 από το
        # sol 63 όλες έξω από τα 32 (19 σε όλο τον κόσμο, κανένα θερμοκήπιο,
        # αποθήκη ή ιατρείο ως το τέλος, 361 μέταλλα στην αποθήκη). Με τα 60,
        # 42 -> 65 άποικοι στο sol 120. Τα 60 είναι όλος ο κόσμος.
        # Ο ΛΑΙΜΟΣ (βήμα 165): στο 5A5A 2 ο μεσαίος θόλος του γεύματα+ στο
        # (34, 0), στο sol 37, έκλεισε το πέρασμα ανάμεσα στο βουνό και στη
        # λίμνη: από τις 32 θέσεις θόλου του κόσμου έμειναν 13, από το sol 44
        # καμία, και η αποικία έμεινε 18 ως το τέλος. Όταν οι θέσεις είναι
        # λιγότερες από NECK_C, ο μεσαίος μετρά πόσες κλείνει· αν κλείνει
        # πάνω από τρεις φορές όσες ο μικρός (+2), χτίζεται ο μικρός. Ένα
        # σταθερό όριο (κανένας μεσαίος κάτω από 40 θέσεις) έφερε κι αυτό το
        # 5A5A 2 στους 78, αλλά στο 1048 1 οι μικροί θόλοι έφαγαν τις θέσεις
        # του δεύτερου Control και η αποικία έμεινε 50 αντί για 78.
        # ΚΑΙ ΟΤΑΝ ΑΦΗΝΕΙ ΛΙΓΟΤΕΡΕΣ ΑΠΟ ΤΙΣ ΜΙΣΕΣ ΤΟΥ ΜΙΚΡΟΥ (βήμα 168): με τα
        # φυτά διορθωμένα, στο 5A5A 2 στο sol 38,7, από 19 θέσεις ο μεσαίος του
        # λαχανικά+ στο (34, 0) τις έκλεινε όλες και ο μικρός στο (30, -4) 12 —
        # 19 δεν είναι πάνω από 3 x 12 + 2, και η αποικία έμεινε 18 ως το τέλος.
        for it in ((DOME_M, DOME_S) if item == DOME_M else (item,)):
            for R in (CORE_R if s["zone"] == "core" and G.grow else (None,)):
                got = G.spot_zone(it, s["zone"], R)
                if got is not None:
                    break
            if got is not None and it == DOME_M and NECK_C:
                n0 = G.dome_sites(NECK_C)
                if n0 < NECK_C:
                    gs = None
                    for R in (CORE_R if s["zone"] == "core" and G.grow else (None,)):
                        gs = G.spot_zone(DOME_S, s["zone"], R)
                        if gs is not None:
                            break
                    if gs is not None:
                        lm = n0 - G.dome_sites(NECK_C, (DOME_M, got[0]))
                        ls = n0 - G.dome_sites(NECK_C, (DOME_S, gs[0]))
                        if lm > 3 * max(ls, 1) + 2 or 2 * (n0 - lm) < n0 - ls:
                            G.event(f"ο λαιμός: από {n0} θέσεις θόλου ο μεσαίος στο {got[0]} "
                                    f"αφήνει {n0 - lm}, ο μικρός στο {gs[0]} {n0 - ls}")
                            got = None
                            continue
            if got is not None:
                if it != item:
                    item = it
                    m, bp = COST[item]
                    m += reserve(G, s)
                break
        if got is None and item in (SOLAR, COLLECTOR, TURBINE) and G.zones \
                and G.anchors < FAR_ANCHORS and G.free_structs() > SLOT_KEEP + 1:
            f = G.struct_anchor(item)       # βήμα 147: η αποικία περιφραγμένη
            if f:
                got, anchor, item = f[1], True, AIRLOCK
                m, bp = COST[AIRLOCK]
        G.spot_cache[key] = got
        if got is None:
            return None
        cands = []
    elif isinstance(near, str):
        cands = G.res_near(near)[:40]
        if near == "water":                 # πρώτα οι κρατημένες (βήμα 145)
            cands = [(2 * x + 3, 2 * y + 3) for x, y in G.shore] + cands
    else:
        # ο στόχος, και αν εκεί δεν χωρά, γύρω από ό,τι έχει χτιστεί, από το
        # κοντινότερο στον στόχο
        sb = lambda v: v - 256 if v > 127 else v
        own = [(sb(d[0]), sb(d[1])) for d in G.domes() if d[4]] + \
              [(sb(t[0]), sb(t[1])) for t in G.structs() if t[4]]
        own.sort(key=lambda c: max(abs(c[0] - near[0]), abs(c[1] - near[1])))
        cands = [near] + own
    for c in cands:                         # η φθηνότερη από όλους τους στόχους
        g = G.spot(item, c)
        if g and (got is None or g[1] < got[1]):
            got = g
        if got and not got[1]:
            break
    half = False
    if got is None and s["item"] == MINE and G.zones:
        # Στο σχέδιο big (βήμα 131) στην περιφέρεια: δίπλα σε ό,τι έχει
        # χτιστεί έπεφτε στη μέση των θόλων και τους έκοβε τους διαδρόμους.
        got = G.spot_zone(MINE, "edge")
        half = got is not None
    elif got is None and s["item"] == MINE:
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
    if got is None and s["item"] == EXTRACTOR and G.zones:
        f = G.far_shore()                   # βήμα 147: η μακρινή όχθη
        if f and f[0] == "pump":
            got = f[1]
        elif f:
            got, anchor, item = f[1], True, AIRLOCK
            m, bp = COST[AIRLOCK]
    G.spot_cache[key] = got
    if got is None:
        return None                         # καμία θέση ακόμη: ίσως μετά από άλλα
    at, pieces = got
    m += 6 * pieces
    bp += 3 * pieces
    if G.stock(S_METAL) < m or G.stock(S_BIOPL) < bp:
        return False
    node = G.place(item, at, ROOM.get(s["room"]))
    if node is None:
        G.event(f"«{s['name']}» δεν μπήκε στο {at} (μέταλλο {G.stock(S_METAL)}, "
                f"θέλει {m}/{bp})")
        return False
    if anchor:
        # Το στάδιο μένει: η αντλία στο επόμενο δείγμα, με την άγκυρα.
        G.anchors += 1
        G.event(f"χτίζεται σκαλοπάτι για «{s['name']}», «airlock» (κόμβος {node}, {at}, {pieces} διάδρ.) -> "
                f"μέταλλο {G.stock(S_METAL)}")
        return None
    G.built[s["name"]] = (node, at)
    G.event(f"χτίζεται «{s['name']}»{' ΜΕΣΑΙΟΣ' if item == DOME_M else ''} (κόμβος {node}, {at}, {pieces} διάδρ.) -> "
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
        if int(G.sol()) >= 2 * (len(G.probes) + 1):            # ανά δύο sol
            x1, x4 = G.speed_probe()
            G.probes.append((round(G.sol(), 2), G.rows[-1]["alive"], round(x1, 3), round(x4, 3)))
        if G.feed:
            for k, top in ((S_METAL, G.feed[0]), (S_BIOPL, G.feed[1])):
                if G.stock(k) < top:
                    G.m.poke(G.g + 2 * k, top & 255)
                    G.m.poke(G.g + 2 * k + 1, top >> 8)
        if G.plast:
            k, n = G.plast
            stop = G.stock(S_STARCH_I) < n if k == "skeep" else G.stock(S_BIOPL) >= n
            G.m.poke(G.L["G_recipes"] + 10 * 2 + 1, 255 if stop else 2)
        # ΤΟ ΕΜΠΟΡΙΟ (βήμα 139): μία φορά ανά έμπορο που προσγειώθηκε.
        # Η κατάσταση ζωντανά, όχι από το δείγμα: στο 2024 0 ένα πλοίο
        # επισκεπτών έφυγε και ο έμπορος ερχόταν ανάμεσα σε δύο δείγματα, και
        # το «προσγειώθηκε» του δείγματος ήταν των επισκεπτών.
        if G.trader and G.m.peek(G.X["EC_SHSTATE"]) == 2 and G.m.peek(G.X["EC_SHKIND"]) == 1 \
                and G.lands_seen != G.m.peek(G.X["EC_LANDS"]):
            G.lands_seen = G.m.peek(G.X["EC_LANDS"])
            net = trade_plan(G)
            if net:
                before = [G.stock(k) for k in range(14)]
                why = G.trade(net)
                ok = why is True
                G.trades.append((round(G.sol(), 2), net, ok))
                G.event("εμπόριο: " + ("έγινε" if ok else f"ΔΕΝ ΕΓΙΝΕ ({why})") + " — παίρνει "
                        + ", ".join(f"{TRADE_NAMES[g]} {10 * n if not g else n}"
                                    for g, n in enumerate(net) if n > 0)
                        + " · δίνει " + ", ".join(f"{TRADE_NAMES[g]} {-10 * n if not g else -n}"
                                                  for g, n in enumerate(net) if n < 0)
                        + f" (μέταλλο {before[3]})")
        if not G.rows[-1]["alive"]:
            G.event("ΤΕΛΟΣ: κανείς ζωντανός")
            break
        # Εξοπλισμός που περίμενε υλικά: μια μηχανή κοστίζει 8 μέταλλα και 2
        # βιοπλαστικά (DESIGN §6.5). Ως το βήμα 132 το σενάριο ζητούσε 10 και 4,
        # και με 2 βιοπλαστικά το εργοστάσιο πλαστικού έμενε άδειο για πάντα —
        # ένας παίκτης θα το εξόπλιζε (#BEEF·0, sol 12,6 ως 33).
        for f in list(G.fits):
            if G.stock(S_METAL) >= 8 and G.stock(S_BIOPL) >= 2:
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
        G.hb = None                         # ΠΟΙΟ ΚΡΑΤΑ ΤΑ ΕΠΟΜΕΝΑ (βήμα 160), και γιατί
        for s in list(todo):
            cheap = s["item"] in ("ship", "fit")
            if held and not cheap and not s.get("aside"):
                continue
            if not ready(G, s):
                continue
            if s["when"] and not s["when"](G):
                continue
            if not cheap and G.sites() >= open_sites(G):
                if not held and not s.get("aside"):
                    G.hb = (s["name"], "sites")
                held = held or not s.get("aside")
                continue
            r = try_step(G, s)
            if r is None:
                if s["name"] not in nowhere:
                    G.event(f"καμία θέση για «{s['name']}» ακόμη {G.why}")
                    nowhere.add(s["name"])
                continue
            if r:
                G.lastb[s["name"]] = G.sol()
                if not s["again"]:
                    todo.remove(s)
                break                       # ένα πράγμα ανά δείγμα
            if not s.get("aside"):
                if not held:
                    G.hb = (s["name"], G.need)
                held = True
        G.rows[-1]["hb"] = G.hb
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
    ap.add_argument("--ram", default=None,
                    help="στο τέλος, οι οκτώ τράπεζες των 16 KB σε ένα αρχείο (βήμα 160)")
    ap.add_argument("--tutorial", action="store_true",
                    help="ο κόσμος ως κόσμος του tutorial (βήμα 149): για --make και για το τρέξιμο")
    a = ap.parse_args()
    if a.make:
        pairs = ([(int(x.split(":")[0], 0), int(x.split(":")[1])) for x in a.pairs.split(",")]
                 if a.pairs else [(a.seed, a.planet)])
        make(pairs, a.tutorial)
        if a.pairs:
            return 0
    sym, g = syms()
    G = Game(sym, g, sna_path(a.seed, a.planet, a.tutorial))
    G.trader = a.plan.startswith("big")         # το εμπόριο (βήμα 139)· notrade το σβήνει
    G.grow = a.plan.startswith("big")           # βήμα 140· nogrow το σβήνει
    tweak(G, a.tweak)
    print(f"πλανήτης {a.planet}, seed #{a.seed:04X}, σχέδιο «{a.plan}», {a.sols} sols"
          + (f", πειράγματα {a.tweak}" if a.tweak else ""),
          flush=True)
    G.zones = a.plan.startswith("big")
    G.tut = a.plan == "tutorial"
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
    if G.neck_n:
        print(f"ο λαιμός: {G.neck_n} μετρήματα θέσεων, {G.neck_t:.0f} s")
    if a.ram:
        import ctypes
        open(a.ram, "wb").write(b"".join(ctypes.string_at(G.bank(n), 0x4000) for n in range(8)))
    if a.json:
        import json
        json.dump(dict(seed=a.seed, planet=a.planet, plan=a.plan, tweak=a.tweak,
                       rows=[dict(sol=r["sol"], alive=r["alive"], popcap=r["popcap"],
                                  stock=r["stock"], cap=r["cap"], full=r["full"],
                                  storm=r["storm"], pok=r["pok"], o2ok=r["o2ok"],
                                  mines=r["mines"], sites=r["sites"], vis=r["vis"],
                                  coins=r["coins"], prest=r["prest"], good=r["good"],
                                  mm=r["mm"], bots=r["bots"], jfree=r["jfree"],
                                  jk=r["jk"], pp=r["pp"], pu=r["pu"], bat=r["bat"],
                                  bcap=r["bcap"], o2p=r["o2p"], o2u=r["o2u"], sk=r["sk"],
                                  dm=r["dm"], ct=r["ct"], nc=r["nc"], rk=r["rk"],
                                  hb=r.get("hb")) for r in G.rows],
                       events=G.events, probes=G.probes, trades=G.trades), open(a.json, "w"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
