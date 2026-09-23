"""Οι οντότητες και η κίνησή τους (DESIGN.md §6.1, §6.3).

ΔΟΜΗ-ΑΠΟ-ΠΙΝΑΚΕΣ, σελιδοποιημένη. Ενα πεδίο ανά πίνακα, το id του πράκτορα
είναι ο δείκτης — ώστε μια ανάγνωση πεδίου να είναι δύο εντολές:

        ld      h,σελίδα
        ld      l,id
        ld      a,(hl)

Δύο πεδία των 128 μοιράζονται σελίδα 256 bytes: το δεύτερο στο id+128. Δεκαέξι
πεδία = οκτώ σελίδες = 2.048 bytes.

Η ΚΙΝΗΣΗ έχει δύο καταστάσεις και τίποτε άλλο:

        AT      στον κόμβο node, θέση slot
        TRANS   πάνω στην ακμή edge του node, με πρόοδο progress

Δεν υπάρχει pathfinding στο τρέξιμο: ο επόμενος κόμβος είναι μία ανάγνωση από
το NEXTHOP. Αυτό το αρχείο είναι η ΑΝΑΦΟΡΑ — ο Z80 πρέπει να βγάζει τα ίδια
bytes, αλλιώς ένας από τους δύο έχει άδικο.

ΜΙΑ ΑΠΟΚΛΙΣΗ ΑΠΟ ΤΟ §6.1, ΣΚΟΠΙΜΗ: το πεδίο `edge` δεν κρατά καθολικό id
διαδρόμου αλλά **τη θέση του γείτονα μέσα στη λίστα γειτνίασης του κόμβου**
(0..7, 255 = δεν ταξιδεύει). Ετσι ο επόμενος κόμβος βγαίνει με μία ανάγνωση
από το node_adj αντί για ψάξιμο στον πίνακα διαδρόμων.
"""
import graph as G
import econ as EC

MAXAGENT = 128              # η πλευρά των πινάκων (§6.1: 80 άποικοι + 16 ρομπότ)
NSLOT = 8                   # θέσεις δαχτυλιδιού ανά κόμβο
NO_EDGE = 255
NO_SLOT = 255
NO_TASK = 255

# σειρά γεμίσματος θέσεων — από το corr_fill των assets, ώστε οι άνθρωποι να
# μη μοιάζουν στοιβαγμένοι
FILL = [0, 4, 2, 6, 1, 5, 3, 7]

# πεδία, με τη σειρά που κάθονται στη μνήμη· το i-οστό στη σελίδα i//2,
# μετατόπιση (i%2)*128
FIELDS = ["flags", "role", "node", "slot", "dest", "edge", "progress", "task",
          "o2", "water", "food", "sleep", "health", "morale", "skill", "spare"]

F_ALIVE, F_INDOORS, F_ASLEEP, F_SICK, F_IDLE = 1, 2, 4, 8, 16
F_WORKING = 32              # στέκεται στη θέση εργασίας και μετράει ως χειριστής

# ρόλοι (§6.1) και ταχύτητα ανά βήμα κίνησης. Τα ρομπότ είναι γρηγορότερα.
WORKER, ENGINEER, BIOLOGIST, MEDIC, GUARD, BOT_CONSTR, BOT_CARRY, BOT_DRILL = range(8)
# Πρώτη φορά που έτρεξε ολόκληρος ο κύκλος, φάνηκε ότι οι αριθμοί του §6.5
# δίνουν αποικία όπου κανείς δεν δουλεύει ποτέ: με ταχύτητα 40, μια ακμή
# θέλει 6 περιστροφές, μια διαδρομή 5 αλμάτων 30 — όσο ακριβώς κρατά και η
# ανάγκη που σε έστειλε. Ολη η ζωή ήταν μετακίνηση. Διπλάσια ταχύτητα:
# μια ακμή σε 2-3 περιστροφές.
ROLE_SPEED = [96, 96, 88, 104, 112, 128, 144, 120]


class Agents:
    """Οι 128 πράκτορες ως 16 πίνακες των 128 bytes."""

    def __init__(self):
        for f in FIELDS:
            setattr(self, f, bytearray(MAXAGENT))
        for i in range(MAXAGENT):
            self.edge[i] = NO_EDGE
            self.slot[i] = NO_SLOT
            self.task[i] = NO_TASK      # 0 θα σήμαινε «κρατάει την εργασία 0»

    def to_bytes(self):
        """Η μνήμη όπως τη βλέπει ο Z80: 8 σελίδες, δύο πεδία η καθεμία."""
        out = bytearray()
        for p in range(len(FIELDS) // 2):
            out += getattr(self, FIELDS[p * 2])
            out += getattr(self, FIELDS[p * 2 + 1])
        return bytes(out)

    def from_bytes(self, blob):
        for p in range(len(FIELDS) // 2):
            base = p * 256
            setattr(self, FIELDS[p * 2], bytearray(blob[base:base + 128]))
            setattr(self, FIELDS[p * 2 + 1], bytearray(blob[base + 128:base + 256]))
        return self


def claim(occ, node):
    """Πρώτη ελεύθερη θέση στη σειρά γεμίσματος, ή NO_SLOT αν ο κόμβος γέμισε."""
    m = occ[node]
    for s in FILL:
        if not (m >> s) & 1:
            occ[node] = m | (1 << s)
            return s
    return NO_SLOT


def release(occ, node, slot):
    if slot != NO_SLOT:
        occ[node] &= ~(1 << slot) & 0xFF


def move_one(a, i, g, nexthop, occ, e=None):
    """Ενα βήμα κίνησης για τον πράκτορα i. Η καρδιά του §6.3."""
    if not a.flags[i] & F_ALIVE:
        return

    if a.edge[i] != NO_EDGE:
        # --- ΤΑΞΙΔΕΥΕΙ ---
        p = a.progress[i] + ROLE_SPEED[a.role[i]]
        if p < 256:
            a.progress[i] = p
            return
        # έφτασε: ο κόμβος προορισμού του βήματος
        dst = g.adj[a.node[i] * G.MAXDEG + a.edge[i]]
        # Μπαίνει ΠΑΝΤΑ. Η θέση στο δαχτυλίδι είναι περιορισμός ΣΧΕΔΙΑΣΗΣ —
        # οκτώ θέσεις έχει το sprite — όχι πόρτα. Οταν ήταν πόρτα, ένας
        # γεμάτος θόλος με χαλασμένη μηχανή δεν επισκευαζόταν ΠΟΤΕ: ο
        # μηχανικός περίμενε έξω και οι οκτώ μέσα δεν είχαν λόγο να φύγουν.
        # Ο ένατος είναι μέσα, απλώς δεν ζωγραφίζεται.
        s = claim(occ, dst)
        a.node[i] = dst
        a.slot[i] = s
        a.edge[i] = NO_EDGE
        a.progress[i] = 0
        return

    # --- ΣΤΑΘΕΡΟΣ ---
    if a.dest[i] == a.node[i]:
        return
    nh = nexthop[a.node[i] * G.MAXNODE + a.dest[i]]
    if nh == G.UNREACH:
        a.dest[i] = a.node[i]            # απρόσιτος: παραιτείται, δεν κολλάει
        return
    base = a.node[i] * G.MAXDEG
    for k in range(g.deg[a.node[i]]):
        if g.adj[base + k] == nh:
            # φεύγει: αν δούλευε, ο θόλος χάνει έναν χειριστή
            if e is not None and a.flags[i] & F_WORKING:
                if a.node[i] < EC.MAX_DOME:
                    e.dome[a.node[i] * EC.DOME_REC + EC.D_OPS] -= 1
                a.flags[i] &= ~F_WORKING & 0xFF
            release(occ, a.node[i], a.slot[i])
            a.slot[i] = NO_SLOT
            a.edge[i] = k
            a.progress[i] = 0
            return
    # το NEXTHOP δείχνει γείτονα που δεν υπάρχει στη λίστα: ο πίνακας είναι
    # μπαγιάτικος ΚΑΙ λάθος. Δεν συμβαίνει· αν συμβεί, δεν κουνιέται.


def move_slice(a, g, nexthop, occ, first, count, e=None):
    """Η φέτα του §7.2: count πράκτορες από τον first, με αύξουσα σειρά."""
    for k in range(count):
        move_one(a, (first + k) & (MAXAGENT - 1), g, nexthop, occ, e)


# --- ανάγκες: φθορά, ικανοποίηση, υγεία, θάνατος (§6.6) -------------------
#
# Το §6.6 έλεγε «φθορά έξι bytes ανά άποικο, ~40 us· το ακριβό είναι να
# ΑΠΟΦΑΣΙΣΕΙΣ τι θα κάνεις γι' αυτό, και αυτό είναι πρόβλημα του πίνακα
# εργασιών». Δεν είναι: ο πίνακας εργασιών δίνει δουλειές, δεν στέλνει κόσμο
# για φαγητό. Η απόφαση ζει εδώ, στο ίδιο πέρασμα που ξέρει ήδη τα νούμερα.

NEED_FIELDS = ["o2", "water", "food", "sleep"]
# Το §6.5 λέει ότι ένας άποικος καταναλώνει 2 νερό και 1 γεύμα ΑΝΑ SOL, και
# ένα sol είναι 750 περιστροφές. Οι ρυθμοί 3/2/1/2 ανά περιστροφή ήταν έξι
# φορές πιο γρήγοροι από την ίδια του την οικονομία: η μπάρα άδειαζε σε 40
# δευτερόλεπτα και όλη η ζωή ενός αποίκου ήταν μετακίνηση. Ενα ανά επίσκεψη
# αδειάζει σε 255 περιστροφές, δηλαδή στο ένα τρίτο ενός sol.
NEED_RATE = [1, 1, 1, 1]
NEED_LOW = 64               # κάτω από αυτό, ψάχνει πού να το λύσει
NEED_CRIT = 16              # κάτω από αυτό, η υγεία πληρώνει
MORALE_QUIT = 48            # κάτω από αυτό, δεν δέχεται δουλειά
O2_REFILL = 2               # όσο αναπνέει αέρα αποικίας


def sub_sat(v, d):
    return v - d if v > d else 0


def needs_slice(a, e, occ, first, count):
    """Η φέτα των θέσεων 8-10: count άποικοι, με αύξουσα σειρά."""
    for k in range(count):
        i = (first + k) & (MAXAGENT - 1)
        if a.flags[i] & F_ALIVE:
            need_one(a, e, occ, i)


def need_one(a, e, occ, i):
    # 1. φθορά
    for f, r in zip(NEED_FIELDS, NEED_RATE):
        arr = getattr(a, f)
        arr[i] = sub_sat(arr[i], r)

    # 2. το οξυγόνο είναι ροή, όχι ταξίδι: το αναπνέει όποιος είναι μέσα
    if e.o2_ok:
        a.o2[i] = min(255, a.o2[i] + O2_REFILL)

    # 3. αν στέκεται στο σωστό δωμάτιο, το παίρνει
    if a.edge[i] == NO_EDGE and a.node[i] < EC.MAX_DOME:
        satisfy(a, e, i, a.node[i])

    # 4. υγεία
    dmg = 0
    if a.o2[i] < NEED_CRIT:
        dmg += 4
    if a.water[i] < NEED_CRIT:
        dmg += 2
    if a.food[i] < NEED_CRIT:
        dmg += 1
    # Η αμμοθύελλα χτυπά όποιον είναι έξω — και έξω σημαίνει «σε εξωτερική
    # δομή», γιατί αυτό ακριβώς κάνει τους αεροφράκτες απόφαση (§6.2).
    if e.storm and a.node[i] >= EC.MAX_DOME:
        dmg += 4
    if dmg:
        a.health[i] = sub_sat(a.health[i], dmg)
    elif min(a.o2[i], a.water[i], a.food[i]) >= NEED_LOW:
        a.health[i] = min(255, a.health[i] + 1)

    # 5. θάνατος
    if a.health[i] == 0:
        die(a, e, occ, i)
        return

    # 6. ηθικό
    if min(a.o2[i], a.water[i], a.food[i], a.sleep[i]) < NEED_CRIT:
        a.morale[i] = sub_sat(a.morale[i], 2)
    elif min(a.o2[i], a.water[i], a.food[i], a.sleep[i]) >= NEED_LOW:
        a.morale[i] = min(255, a.morale[i] + 1)
    # Ενα δέντρο ή ένα σαλόνι δεν φέρνει πίσω κανέναν, αλλά κρατά το πένθος
    # από το να τρώει το ηθικό όλων (§6.6).
    if e.gloom and not e.amenity:
        a.morale[i] = sub_sat(a.morale[i], 1)

    # 7. πού πρέπει να πάει
    seek(a, e, i)


def satisfy(a, e, i, d):
    """Στέκεται στον θόλο d. Οτι έχει να του δώσει, του το δίνει."""
    room = e.dome[d * EC.DOME_REC + EC.D_ROOM]
    # Γεμάτη μπάρα, όχι +64: βλ. src/needs.asm — με +64 ένας άποικος έτρωγε
    # δώδεκα φορές το sol και η αρχική αποικία πέθαινε από πείνα σε ένα.
    if room == EC.R_QUARTERS:
        a.sleep[i] = 255
    elif room == EC.R_CANTEEN:
        if a.food[i] < NEED_LOW and e.stock[EC.S_FOOD] > 0:
            e.stock[EC.S_FOOD] -= 1
            a.food[i] = 255
        if a.water[i] < NEED_LOW and e.stock[EC.S_WATER] > 0:
            e.stock[EC.S_WATER] -= 1
            a.water[i] = 255
    elif room == EC.R_MEDBAY:
        if a.health[i] < NEED_LOW and e.stock[EC.S_MEDI] > 0:
            e.stock[EC.S_MEDI] -= 1
            a.health[i] = min(255, a.health[i] + 32)


def die(a, e, occ, i):
    """Ο θάνατος αφήνει πίσω του μια θέση, μια δουλειά και πένθος."""
    if a.flags[i] & F_WORKING and a.node[i] < EC.MAX_DOME:
        e.dome[a.node[i] * EC.DOME_REC + EC.D_OPS] -= 1
    release(occ, a.node[i], a.slot[i])
    a.flags[i] = 0
    a.slot[i] = NO_SLOT
    a.edge[i] = NO_EDGE
    a.task[i] = NO_TASK
    a.progress[i] = 0
    e.gloom = min(255, e.gloom + 16)
    e.deaths_sol = min(255, e.deaths_sol + 1)


def seek(a, e, i):
    """Οι δικές του ανάγκες υπερισχύουν του πίνακα εργασιών (§6.7).

    Με αυτή τη σειρά: υγεία, φαγητό, νερό, ύπνος. Οποιος έχει ανάγκη αφήνει τη
    δουλειά του — ο πίνακας εργασιών θα ξαναδώσει την εργασία σε άλλον μόνος
    του, στο μάζεμα.
    """
    if a.health[i] < NEED_LOW:
        room = EC.R_MEDBAY
    elif a.food[i] < NEED_LOW:
        room = EC.R_CANTEEN
    elif a.water[i] < NEED_LOW:
        room = EC.R_CANTEEN
    elif a.sleep[i] < NEED_LOW:
        room = EC.R_QUARTERS
    else:
        return
    # Ηδη πάει (ή είναι) σε τέτοιο δωμάτιο; Τότε τίποτα. Χωρίς αυτόν τον
    # έλεγχο κάθε άποικος ξαναέψαχνε το κοντινότερο δωμάτιο σε ΚΑΘΕ επίσκεψη,
    # μαζί με τη σελιδοποίηση και τις οκτώ αναγνώσεις του DIST που αυτό θέλει.
    d = a.dest[i]
    if d < EC.MAX_DOME and e.dome[d * EC.DOME_REC + EC.D_ROOM] == room:
        return
    d = EC.nearest_room(e, room, a.node[i])
    if d == 255:
        return                              # δεν υπάρχει τέτοιο δωμάτιο
    a.task[i] = NO_TASK
    a.dest[i] = d


# --- ο τροχός (§7.2) ------------------------------------------------------
WH_SLOTS = 16
WH_MOVE_N = 12              # πράκτορες ανά θέση κίνησης
# Οκτώ ανά θέση: 3 x 8 = 24 άποικοι ανά περιστροφή, καθένας κάθε τέσσερις.
# Το πλήρες πέρασμα κοστίζει ~740 us ανά άποικο και δεν υπάρχει ένα σημείο
# που να φταίει — απλώς κάνει πολλά. Το §7.3 δίνει ακριβώς αυτόν τον μοχλό.
# Και ο αραιότερος ρυθμός είναι ΠΙΟ κοντά στην οικονομία του §6.5: μια μπάρα
# των 255 κρατά τώρα 1.020 περιστροφές, δηλαδή περίπου ενάμισι sol.
WH_NEED_N = 8               # άποικοι ανά θέση αναγκών
WH_NEED_SPAN = 24           # 3 θέσεις x 8
MAX_COLONIST = 96           # το ταβάνι του §6.1: 80 άποικοι + 16 ρομπότ


class Sim:
    """Ο,τι χρειάζεται ένα frame προσομοίωσης, και τίποτε άλλο."""

    PLANT_CLASS = None

    def __init__(self, g, nexthop, dist=None):
        self.a = Agents()
        self.g = g
        self.nexthop = nexthop
        self.occ = bytearray(G.MAXNODE)
        self.slot = 0
        self.need_base = 0
        self.e = EC.Econ()
        self.e.dist = dist
        if Sim.PLANT_CLASS is None:
            Sim.PLANT_CLASS = EC.load_plant_class()
        self.pc = Sim.PLANT_CLASS

    def tick(self):
        """Ενα frame: μία θέση του τροχού. Η δρομολόγηση δεν είναι θέση."""
        s = self.slot
        self.slot = (s + 1) & (WH_SLOTS - 1)
        if s < 8:
            move_slice(self.a, self.g, self.nexthop, self.occ,
                       s * WH_MOVE_N, WH_MOVE_N, self.e)
        elif s < 11:
            # Το πλήρες πέρασμα αναγκών κοστίζει 348 us ανά άποικο. Τρεις
            # θέσεις x 32 δεν χωρούσαν άνετα σε frame, οπότε ο τροχός κάνει
            # αυτό ακριβώς που λέει το §7.3: μισούς ανά περιστροφή, τον
            # καθένα κάθε δεύτερη. Οι ανάγκες απλώς κρατάνε διπλάσιο χρόνο.
            needs_slice(self.a, self.e, self.occ,
                        self.need_base + (s - 8) * WH_NEED_N, WH_NEED_N)
            if s == 10:
                self.need_base = (self.need_base + WH_NEED_SPAN) % MAX_COLONIST
        elif s == 11:
            EC.production_slice(self.e, plant_class=self.pc)
        elif s == 12:
            alive = sum(1 for i in range(MAXAGENT)
                        if self.a.flags[i] & F_ALIVE)
            EC.flow_balance(self.e, alive)
        elif s == 14:
            EC.rooms_rebuild(self.e, self.pc)
        elif s == 13:
            EC.jobs_tick(self.e, self.a, F_ALIVE, F_WORKING)
        elif s == 15:
            if EC.events(self.e):
                EC.sol_rollover(self.e, self.a, F_ALIVE, F_WORKING, NEED_LOW)
            EC.ship_tick(self.e, self.a, self.e.pad_node, F_ALIVE)
        # 13 πίνακας εργασιών, 14 ελεύθερη — δεν έχουν γραφτεί, ούτε εδώ ούτε
        # στον Z80.


def populate(sim, n_agents=96, seed=7):
    """Μια αρχική κατάσταση που ασκεί τις γωνίες: γεμάτοι κόμβοι, απρόσιτοι
    προορισμοί, νεκροί ανάμεσα στους ζωντανούς, όλοι οι ρόλοι."""
    a, g = sim.a, sim.g
    x = seed
    for i in range(n_agents):
        x = ((x * 75) + 74) & 0xFFFF
        # ΟΧΙ από τη γεννήτρια. Ο LCG `x = 75x + 74` έχει αδύναμα χαμηλά bits:
        # το (x>>3)&7 έβγαζε ΜΟΝΟ τους ρόλους 0 και 2, δηλαδή κάθε αποικία
        # δοκιμής ήταν εργάτες και βιολόγοι — ούτε ένας μηχανικός, ούτε ένας
        # γιατρός. Η επισκευή και η ίαση δεν είχαν εκτελεστεί ποτέ.
        a.role[i] = i & 7
        a.flags[i] = F_ALIVE if (x & 31) else 0      # ~3% νεκροί εξαρχής
        # Οι άποικοι ζουν ΣΤΟΥΣ ΘΟΛΟΥΣ. Σκορπισμένοι σε όλο τον γράφο, οι
        # μισοί ξεκινούσαν πάνω σε εξωτερικές δομές και το ταξίδι ως την
        # κοντινότερη καντίνα κρατούσε περισσότερο από την ίδια την ανάγκη:
        # κανείς δεν προλάβαινε ποτέ να πιάσει δουλειά.
        ndome = min(EC.MAX_DOME, g.n)
        node = (x >> 6) % ndome
        a.node[i] = node
        a.dest[i] = ((x >> 9) * 7 + i) % ndome
        a.o2[i] = 190 + (x & 63)
        a.water[i] = 150 + ((x >> 2) & 63)
        a.food[i] = 120 + ((x >> 4) & 63)
        a.sleep[i] = 110 + ((x >> 5) & 63)
        # Μερικοί μπαίνουν ήδη πεινασμένοι, διψασμένοι ή άυπνοι. Χωρίς αυτούς
        # οι μπάρες θέλουν εκατοντάδες περιστροφές για να πέσουν κάτω από το
        # κατώφλι, και η δοκιμή τελειώνει πριν φάει ποτέ κανείς.
        if i % 4 == 1:
            a.food[i] = 30
        if i % 5 == 2:
            a.water[i] = 30
        if i % 3 == 0:
            a.sleep[i] = 30
        a.health[i] = 200
        a.morale[i] = 150
        # Εξι άποικοι μπαίνουν ετοιμοθάνατοι. Χωρίς αυτούς η διαδρομή του
        # θανάτου — θέση, δουλειά, χειριστής, πένθος — δεν εκτελείται ποτέ
        # μέσα στη διάρκεια της δοκιμής.
        if i % 16 == 5:
            a.health[i] = 6
            a.o2[i] = 4
            a.water[i] = 4
        if a.flags[i] & F_ALIVE:
            a.slot[i] = claim(sim.occ, node)          # μπορεί να γυρίσει 255
    return sim
