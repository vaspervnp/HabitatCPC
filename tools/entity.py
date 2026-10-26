"""Οι οντότητες και η κίνησή τους (DESIGN.md §6.1, §6.3).

ΔΟΜΗ-ΑΠΟ-ΠΙΝΑΚΕΣ, σελιδοποιημένη. Ενα πεδίο ανά πίνακα, το id του πράκτορα
είναι ο δείκτης — ώστε μια ανάγνωση πεδίου να είναι δύο εντολές:

        ld      h,σελίδα
        ld      l,id
        ld      a,(hl)

Ενα πεδίο σε κάθε σελίδα των 256 bytes, από το βήμα 172 (DESIGN §6.1: τα 160
άποικοι): δεκαέξι πεδία = δεκαέξι σελίδες = 4.096 bytes, και οι ids 188-255
κάθε σελίδας για άλλα. Το πρώτο πεδίο κάθε ζεύγους μένει στη σελίδα k, το
δεύτερο πάει στην 8 + k (page_of). Ως το 171 δύο πεδία των 128 μοιράζονταν
σελίδα, το δεύτερο στο id+128: οκτώ σελίδες, 2.048 bytes.

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

MAXAGENT = 188              # οι ids σε χρήση (§6.1: 160 άποικοι, 16 ρομπότ, 4 εισβολείς, 8 επισκέπτες· 128 ως το βήμα 172)
NSLOT = 8                   # θέσεις δαχτυλιδιού ανά κόμβο
NO_EDGE = 255
NO_SLOT = 255
NO_TASK = 255

# σειρά γεμίσματος θέσεων — από το corr_fill των assets, ώστε οι άνθρωποι να
# μη μοιάζουν στοιβαγμένοι
FILL = [0, 4, 2, 6, 1, 5, 3, 7]

# πεδία, ανά ζεύγη· το i-οστό στη σελίδα page_of(i): i//2 για τα πρώτα, 8 + i//2
# για τα δεύτερα (βήμα 172· ως τότε η σελίδα i//2 και μετατόπιση (i%2)*128)
FIELDS = ["flags", "role", "node", "slot", "dest", "edge", "progress", "task",
          "o2", "water", "food", "sleep", "health", "morale", "suit", "spare"]
AG_HI = 8                   # = AG_HI του src/const.asm
NPAGE = 16                  # σελίδες των πεδίων


def page_of(i):
    """Η σελίδα του πεδίου i (FIELDS), από την αρχή του agent_fields."""
    return i // 2 + AG_HI * (i % 2)


def field_ofs(name):
    """Από την αρχή του agent_fields ως το πεδίο `name` (του πράκτορα 0)."""
    return page_of(FIELDS.index(name)) * 256


def field_at(i):
    """Ενα byte i του agent_fields -> (πεδίο, πράκτορας)."""
    p = i // 256
    return FIELDS[2 * (p % AG_HI) + p // AG_HI], i % 256

F_ALIVE, F_INDOORS, F_ASLEEP, F_SICK, F_IDLE = 1, 2, 4, 8, 16
F_WORKING = 32              # στέκεται στη θέση εργασίας και μετράει ως χειριστής
F_SUITPH = 64               # 1: η επόμενη επίσκεψη έξω παίρνει μονάδα στολής (βήμα 90)

# ρόλοι (§6.1) και ταχύτητα ανά βήμα κίνησης. Τα ρομπότ είναι γρηγορότερα.
WORKER, ENGINEER, BIOLOGIST, MEDIC, GUARD, BOT_CONSTR, BOT_CARRY, BOT_DRILL = range(8)
# Πρώτη φορά που έτρεξε ολόκληρος ο κύκλος, φάνηκε ότι οι αριθμοί του §6.5
# δίνουν αποικία όπου κανείς δεν δουλεύει ποτέ: με ταχύτητα 40, μια ακμή
# θέλει 6 περιστροφές, μια διαδρομή 5 αλμάτων 30 — όσο ακριβώς κρατά και η
# ανάγκη που σε έστειλε. Ολη η ζωή ήταν μετακίνηση. Διπλάσια ταχύτητα:
# μια ακμή σε 2-3 περιστροφές.
ROLE_SPEED = [96, 96, 88, 104, 112, 128, 144, 120]


class Agents:
    """Οι 188 πράκτορες ως 16 πίνακες των 188 bytes (βήμα 173· ως τότε 128)."""

    def __init__(self):
        for f in FIELDS:
            setattr(self, f, bytearray(MAXAGENT))
        for i in range(MAXAGENT):
            self.edge[i] = NO_EDGE
            self.slot[i] = NO_SLOT
            self.task[i] = NO_TASK      # 0 θα σήμαινε «κρατάει την εργασία 0»

    def to_bytes(self):
        """Η μνήμη όπως τη βλέπει ο Z80: 16 σελίδες, ένα πεδίο η καθεμία. Οι
        ουρές τους (ids 188-255) όπως ήρθαν από το from_bytes — εκεί είναι η
        κρυφή μνήμη φιγούρων του renderer (src/object.asm, of_at) — ή μηδέν."""
        out = bytearray(getattr(self, "tails", bytes(NPAGE * 256)))
        for i, f in enumerate(FIELDS):
            p = page_of(i) * 256
            out[p:p + MAXAGENT] = getattr(self, f)
        return bytes(out)

    def from_bytes(self, blob):
        for i, f in enumerate(FIELDS):
            p = page_of(i) * 256
            setattr(self, f, bytearray(blob[p:p + MAXAGENT]))
        if len(blob) == NPAGE * 256:
            self.tails = bytes(blob)
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
        p = a.progress[i] + ROLE_SPEED[a.role[i] & 7]   # ο εισβολέας (8): όπως ο εργάτης
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
        # Οποιος ταξίδευε μέσα φτάνει μέσα — η αναχώρηση ρώτησε ήδη τον
        # στόχο. Μόνο όποιος ερχόταν απ' έξω ρωτά (βήμα 87).
        if not a.flags[i] & F_INDOORS:
            set_in(a, i, EC.indoor_node(e, dst))
        return

    # --- ΣΤΑΘΕΡΟΣ ---
    if a.dest[i] == a.node[i]:
        return
    nh = nexthop[a.node[i] * G.MAXNODE + a.dest[i]]
    if nh == G.UNREACH:
        # Παραιτείται ΚΑΙ αφήνει τη δουλειά: αλλιώς ο πίνακας εργασιών κρατά
        # την ανάθεση πάνω σε κάποιον που δεν πρόκειται να ξεκινήσει ποτέ —
        # βλ. src/entity.asm.
        a.dest[i] = a.node[i]
        a.task[i] = NO_TASK
        return
    base = a.node[i] * G.MAXDEG
    for k in range(g.deg[a.node[i]]):
        if g.adj[base + k] == nh:
            # φεύγει: αν δούλευε, ο θόλος χάνει έναν χειριστή
            if e is not None and a.flags[i] & F_WORKING:
                if a.node[i] < EC.MAX_DOME:
                    e.dome[a.node[i] * EC.DOME_REC + EC.D_OPS] -= 1
                else:                   # ένα ορυχείο (βήμα 94, op_ptr): dec (hl)
                    b = (a.node[i] - EC.MAX_DOME) * EC.STRUCT_REC + EC.ST_OPS
                    e.struct[b] = (e.struct[b] - 1) & 0xFF
                a.flags[i] &= ~F_WORKING & 0xFF
            release(occ, a.node[i], a.slot[i])
            a.slot[i] = NO_SLOT
            a.edge[i] = k
            a.progress[i] = 0
            # Οποιος ξεκινά έξω μένει έξω. Οποιος ξεκινά μέσα μένει μέσα μόνο
            # σε διάδρομο προς έτοιμο μέρος με αέρα, και όχι από δομή σε δομή
            # (δύο airlock τα ενώνει το έδαφος). Το «ξεκινά μέσα» είναι η
            # σημαία, όχι ξανά το en_in του κόμβου: ένα en_in λιγότερο.
            x = a.node[i]
            if a.flags[i] & F_INDOORS:
                set_in(a, i, not (x >= EC.MAX_DOME and nh >= EC.MAX_DOME)
                       and EC.indoor_node(e, nh))
                if not a.flags[i] & F_INDOORS:
                    a.suit[i] = EC.SUIT_TRIP        # βγαίνει με γεμάτη στολή (βήμα 90)
            return
    # το NEXTHOP δείχνει γείτονα που δεν υπάρχει στη λίστα: ο πίνακας είναι
    # μπαγιάτικος ΚΑΙ λάθος. Δεν συμβαίνει· αν συμβεί, δεν κουνιέται.


def set_in(a, i, inside):
    """Το en_put: το F_INDOORS του i."""
    a.flags[i] = (a.flags[i] | F_INDOORS) if inside else (a.flags[i] & ~F_INDOORS & 0xFF)


def move_slice(a, g, nexthop, occ, first, count, e=None):
    """Η φέτα του §7.2: count πράκτορες από τον first, με αύξουσα σειρά."""
    for k in range(count):
        move_one(a, first + k, g, nexthop, occ, e)     # ως το βήμα 172 mod 128


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
        i = first + k                   # ως το βήμα 172 mod 128
        if a.flags[i] & F_ALIVE:
            need_one(a, e, occ, i)


def need_one(a, e, occ, i):
    inside = a.flags[i] & F_INDOORS
    # 0. ΕΞΩ, Η ΣΤΟΛΗ (βήμα 90, src/suit.asm): αδειάζει μία μονάδα κάθε δεύτερη
    #    επίσκεψη, και όταν αδειάσει ο άποικος πεθαίνει αμέσως. Με ένα λεπτό
    #    αέρα αφήνει τη δουλειά και πάει στο κοντινότερο airlock — το κοιτά
    #    μόνο στην επίσκεψη που αδειάζει η στολή. Τα ρομπότ δεν αναπνέουν (το
    #    bit της φάσης γυρίζει και σε αυτά: η μισή επίσκεψη δεν κοιτά ρόλο).
    if not inside:
        a.flags[i] ^= F_SUITPH
        if not a.flags[i] & F_SUITPH and a.role[i] < BOT_CONSTR:
            a.suit[i] = (a.suit[i] - 1) & 0xFF
            if a.suit[i] == 0:
                die(a, e, occ, i)
                return
            if a.suit[i] <= EC.SUIT_LOW and a.task[i] != T_NEED:
                n = EC.nearest_airlock(e, a.node[i])
                if n != 255:
                    a.dest[i] = n
                    a.task[i] = T_NEED
    # 1. φθορά. Το οξυγόνο μόνο μέσα (βήμα 87): έξω αναπνέει από τη στολή, και
    #    ως το βήμα 89 η στολή δεν αδειάζει.
    for f, r in zip(NEED_FIELDS, NEED_RATE):
        if f == "o2" and not inside:
            continue
        arr = getattr(a, f)
        arr[i] = sub_sat(arr[i], r)

    # 2. το οξυγόνο είναι ροή, όχι ταξίδι: το αναπνέει όποιος είναι μέσα
    if e.o2_ok and inside:
        a.o2[i] = min(255, a.o2[i] + O2_REFILL)

    # 3. αν στέκεται στο σωστό δωμάτιο, το παίρνει — ΜΟΝΟ ΜΕΣΑ (βήμα 90). Εξω
    #    στέκεται σε θόλο μόνο αν ο θόλος είναι εργοτάξιο, και ως το βήμα 89 ο
    #    χτίστης κοιμόταν σε εργοτάξιο κοιτώνα και έτρωγε σε εργοτάξιο κυλικείου.
    if inside and a.edge[i] == NO_EDGE and a.node[i] < EC.MAX_DOME:
        satisfy(a, e, i, a.node[i])

    # 4. υγεία
    dmg = 0
    if a.o2[i] < NEED_CRIT:
        dmg += 4
    if a.water[i] < NEED_CRIT:
        dmg += 2
    if a.food[i] < NEED_CRIT:
        dmg += 1
    # Η αμμοθύελλα χτυπά όποιον είναι έξω, γιατί αυτό ακριβώς κάνει τους
    # αεροφράκτες απόφαση (§6.2). Από το βήμα 87 «έξω» είναι το F_INDOORS.
    if e.storm and not inside:
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
    if a.flags[i] & F_WORKING:
        if a.node[i] < EC.MAX_DOME:
            e.dome[a.node[i] * EC.DOME_REC + EC.D_OPS] -= 1
        else:                           # ένα ορυχείο (βήμα 94, op_ptr): dec (hl)
            b = (a.node[i] - EC.MAX_DOME) * EC.STRUCT_REC + EC.ST_OPS
            e.struct[b] = (e.struct[b] - 1) & 0xFF
    bury(a, occ, i)
    e.gloom = min(255, e.gloom + 16)
    e.deaths_sol = min(255, e.deaths_sol + 1)


def bury(a, occ, i):
    """Το nd_bury (βήμα 111): θέση, σημαίες, ακμή, εργασία, πρόοδος — ό,τι
    κάνει ο θάνατος εκτός από χειριστή και πένθος. Και ο εισβολέας που πέφτει."""
    release(occ, a.node[i], a.slot[i])
    a.flags[i] = 0
    a.slot[i] = NO_SLOT
    a.edge[i] = NO_EDGE
    a.task[i] = NO_TASK
    a.progress[i] = 0


# --- οι εισβολείς (βήμα 111, src/foe.asm) --------------------------------
#
# Μία φορά ανά περιστροφή, στη θέση 15 μετά τα ρομπότ και πριν από το πλοίο.
# Ολα με τη σειρά που τα κάνει ο Z80, γιατί η δοκιμή συγκρίνει bytes:
#
#   1. αν δεν ζει κανείς από τους 96-99: όποιος φρουρός είναι ακόμη στη μάχη
#      (T_FIGHT) γίνεται διαθέσιμος, και τέλος.
#   2. κινούνται, όπως κάθε πράκτορας (move_slice 96, 4).
#   3. ποιος στέκεται πού (fn), ποιος ζει πού (an), ποιοι ζουν (tg).
#   4. οι άποικοι 0-79 με τη σειρά. Οποιος ΣΤΕΚΕΤΑΙ σε κόμβο όπου στέκεται
#      εισβολέας που δεν χτύπησε ακόμη, τρώει FOE_HIT από αυτόν — ο καθένας
#      χτυπά τον πρώτο που βρίσκει, μία φορά. Στο μηδέν πεθαίνει (die).
#      Ο φρουρός που ζει, και δεν είναι έξω στον δρόμο για μέσα (T_NEED χωρίς
#      F_INDOORS: η στολή· βήμα 150, ως τότε κάθε T_NEED): T_FIGHT, ένα όπλο
#      αν δεν έχει και υπάρχει στο απόθεμα, ο στόχος του κατά σειρά (gi mod
#      ζωντανοί), και αν στέκεται: χτυπά τον πρώτο που φτάνει — με τα χέρια
#      όποιον στέκεται στον κόμβο του, με όπλο και όποιον είναι στον κόμβο
#      του ή σε γειτονικό — και μένει· αλλιώς πάει στον κόμβο του στόχου.
#   5. οι εισβολείς: T_FIGHT ξανά (μια απρόσιτη διαδρομή το σβήνει), και όποιος
#      στέκεται: αν χτύπησε μένει, αν έφτασε στον προορισμό ψάχνει τον επόμενο
#      άποικο που στέκεται αλλού, από εκεί που σταμάτησε ο προηγούμενος (pk).
#   6. αν δεν ζει πια κανείς, όπως το 1.
FOE_STATE = {"pk": 0}           # το fo_pk του Z80: ο τελευταίος στόχος


def foe_free(a):
    for c in range(EC.AG_BOT0):
        if a.task[c] == EC.T_FIGHT:
            a.task[c] = NO_TASK


def foe_tick(e, a, g, nexthop, occ, st=FOE_STATE):
    foes = range(EC.AG_FOE0, EC.AG_FOE0 + EC.AG_NFOE)
    if not any(a.flags[i] & F_ALIVE for i in foes):
        foe_free(a)
        return
    move_slice(a, g, nexthop, occ, EC.AG_FOE0, EC.AG_NFOE, e)
    fn, an = [255] * EC.AG_NFOE, [255] * EC.AG_NFOE
    for k, i in enumerate(foes):
        if a.flags[i] & F_ALIVE:
            an[k] = a.node[i]
            if a.edge[i] == NO_EDGE:
                fn[k] = a.node[i]
    tg = [k for k in range(EC.AG_NFOE) if an[k] != 255]
    an0 = list(an)
    hit, gi = [False] * EC.AG_NFOE, 0
    n = st.setdefault("n", {})          # μετρητές για τις δοκιμές, όχι κατάσταση

    def count(k):
        n[k] = n.get(k, 0) + 1

    def foe_down(k):
        i = EC.AG_FOE0 + k
        bury(a, occ, i)
        fn[k] = an[k] = 255
        count("εισβολείς έπεσαν")

    # ΠΡΩΤΑ ΧΤΥΠΟΥΝ ΟΙ ΕΙΣΒΟΛΕΙΣ
    for c in range(EC.AG_BOT0):
        if not a.flags[c] & F_ALIVE or a.edge[c] != NO_EDGE:
            continue
        for k in range(EC.AG_NFOE):
            if fn[k] == a.node[c] and not hit[k]:
                hit[k] = True
                count("χτυπήματα εισβολέων")
                a.health[c] = max(0, a.health[c] - EC.FOE_HIT)
                if not a.health[c]:
                    die(a, e, occ, c)
                    count("άποικοι έπεσαν")
                    break
    # ΜΕΤΑ ΑΠΑΝΤΟΥΝ ΟΙ ΦΡΟΥΡΟΙ
    for c in range(EC.AG_BOT0):
        if not a.flags[c] & F_ALIVE:
            continue
        here = a.node[c]
        stand = a.edge[c] == NO_EDGE
        if a.role[c] != EC.RL_GUARD or (a.task[c] == T_NEED and not a.flags[c] & F_INDOORS):
            continue
        a.task[c] = EC.T_FIGHT
        if not a.flags[c] & EC.F_GUN and e.stock[EC.S_GUN]:
            e.stock[EC.S_GUN] -= 1
            a.flags[c] |= EC.F_GUN
            count("όπλα")
        t = tg[(gi & 3) % len(tg)]      # fo_ts[g & 3]: ο κόμβος του στην αρχή
        gi += 1
        gun = a.flags[c] & EC.F_GUN
        j = None
        if stand:
            # ΤΟ ΟΠΛΟ ΦΤΑΝΕΙ από τον κόμβο του εισβολέα στους γείτονές του —
            # η λίστα γειτνίασης του ΕΙΣΒΟΛΕΑ, όπως τη γράφει ο χάρτης του Z80.
            for k in range(EC.AG_NFOE):
                if an[k] == 255:
                    continue
                near = (an[k] == here or here in
                        (g.adj[an[k] * G.MAXDEG + q] for q in range(g.deg[an[k]])))
                if fn[k] == here or (gun and near):
                    j = k
                    break
        if j is not None:
            count("με όπλο, από γειτονικό" if gun and an[j] != here else
                  "με όπλο, στον κόμβο" if gun else "με τα χέρια")
            i = EC.AG_FOE0 + j
            a.health[i] = max(0, a.health[i] - (EC.GUN_HIT if gun else EC.HAND_HIT))
            if not a.health[i]:
                foe_down(j)
            a.dest[c] = here
        else:
            a.dest[c] = an0[t]          # κι αν έπεσε στο μεταξύ: εκεί πάει

    for k, i in enumerate(foes):
        if an[k] == 255:
            continue
        a.task[i] = EC.T_FIGHT
        if fn[k] == 255:
            continue
        if hit[k]:
            a.dest[i] = a.node[i]
        elif a.node[i] == a.dest[i]:
            for q in range(1, EC.AG_BOT0 + 1):
                c = (st["pk"] + q) % EC.AG_BOT0
                if a.flags[c] & F_ALIVE and a.edge[c] == NO_EDGE and a.node[c] != a.node[i]:
                    a.dest[i] = a.node[c]
                    st["pk"] = c
                    break
    if not any(a.flags[i] & F_ALIVE for i in foes):
        foe_free(a)


# --- οι επισκέπτες που περπατούν (βήμα 136, src/visit.asm) ----------------
#
# Μία φορά ανά περιστροφή, όσο είναι προσγειωμένο πλοίο επισκεπτών: στη θέση
# 15, στην αρχή του ship_tick. Με τη σειρά του Z80:
#
#   1. κινούνται (move_slice 112, 8).
#   2. ο καθένας που ζει: μετριέται (και αν είναι μέσα, για το οξυγόνο), η
#      εργασία του ξαναγίνεται T_VISIT (τη σβήνει μια απρόσιτη διαδρομή ή μια
#      κατεδάφιση), και αν στέκεται εκεί που πήγαινε, αποφασίζει (visit_at) —
#      κι αυτός που βρήκε τον δρόμο απρόσιτο: το move_one κάνει προορισμό
#      τον κόμβο του.
#   3. EC_VIN = όσοι ήταν μέσα· αν δεν ζούσε κανείς, το πλοίο φεύγει τώρα.

def visit_tick(e, a, g, nexthop, occ):
    move_slice(a, g, nexthop, occ, EC.AG_VIS0, EC.AG_NVIS, e)
    alive = inside = 0
    for i in range(EC.AG_VIS0, EC.AG_VIS0 + EC.AG_NVIS):
        if not a.flags[i] & F_ALIVE:
            continue
        alive += 1
        if a.flags[i] & F_INDOORS:
            inside += 1
        a.task[i] = EC.T_VISIT
        if a.edge[i] == NO_EDGE and a.dest[i] == a.node[i]:
            visit_at(e, a, occ, i)
    e.vin = inside
    if not alive:
        e.ship_eta = 0


def visit_at(e, a, occ, i):
    """Το vi_at: όσο κάθεται (η πρόοδος) μένει. Μετά, κατά τη φάση: στο
    κυλικείο τρώει, πίνει, πληρώνει και κάθεται· στο σαλόνι πληρώνει και
    κάθεται· αλλιώς πάει στο κοντινότερο, και αν δεν φτάνει σε κανένα, ή στο
    κυλικείο δεν έχει τι να φάει, γυρίζει στο πλοίο — όπου ανεβαίνει."""
    if a.progress[i]:
        a.progress[i] -= 1
        return
    node = a.node[i]

    def go(room):
        if node < EC.MAX_DOME and e.dome[node * EC.DOME_REC + EC.D_ROOM] == room:
            return "εδώ"
        d = EC.nearest_room(e, room, node)
        if d == 255:
            return None
        a.dest[i] = d
        return "πάει"

    def pay(n):
        e.coins = min(EC.COIN_MAX, e.coins + n)

    def stay():
        a.health[i] += 1
        a.progress[i] = EC.VIS_STAY

    def home():
        a.health[i] = EC.VP_HOME
        if node == e.pad_node:
            bury(a, occ, i)             # ανέβηκε
        else:
            a.dest[i] = e.pad_node

    ph = a.health[i]
    if ph == EC.VP_EAT:
        r = go(EC.R_CANTEEN)
        if r == "πάει":
            return
        if r == "εδώ" and e.stock[EC.S_FOOD] and e.stock[EC.S_WATER]:
            e.stock[EC.S_FOOD] -= 1
            e.stock[EC.S_WATER] -= 1
            e.goodwill = min(EC.GOOD_MAX, e.goodwill + EC.GOOD_UP)
            pay(EC.COIN_MEAL)
            stay()
            return
        e.goodwill = max(0, e.goodwill - EC.GOOD_DOWN)
        home()
    elif ph == EC.VP_FUN:
        r = go(EC.R_LOUNGE)
        if r == "πάει":
            return
        if r == "εδώ":
            pay(EC.COIN_FUN)
            stay()
            return
        if e.amenity:                   # δέντρα: πληρώνει εκεί που έφαγε (βήμα 134)
            pay(EC.COIN_FUN)
        home()
    else:
        home()


T_NEED = 254        # «πάω για φαγητό» — δεν είναι δείκτης εργασίας (§6.7)


def seek(a, e, i):
    """Οι δικές του ανάγκες υπερισχύουν του πίνακα εργασιών (§6.7).

    Με αυτή τη σειρά: υγεία, φαγητό, νερό, ύπνος. Οποιος έχει ανάγκη αφήνει τη
    δουλειά του — ο πίνακας εργασιών θα ξαναδώσει την εργασία σε άλλον μόνος
    του, στο μάζεμα — και ΚΡΑΤΑΕΙ το T_NEED ώσπου να χορτάσει, αλλιώς η
    ανάθεση τον ξαναπαίρνει στον επόμενο κόμβο και δεν φτάνει ποτέ στο
    κυλικείο (βλ. tests/test_needs.py).

    Από το βήμα 120, μια ανάγκη που το δωμάτιό της δεν υπάρχει (room_n 0)
    περνά στην επόμενη, και αν δεν μένει καμία, ό,τι ο χορτάτος· ένα δωμάτιο
    που υπάρχει αλλά δεν φτάνει εκεί, ό,τι ο χορτάτος (src/needs.asm, nd_far).
    Ως τότε έμενε όπως ήταν: χωρίς κοιτώνα ο άποικος που είχε πάει για νερό
    κρατούσε το T_NEED για πάντα, και χωρίς ιατρείο ένας τραυματίας δεν
    ξαναπήγαινε για φαγητό.
    """
    for low, room in ((a.health[i] < NEED_LOW, EC.R_MEDBAY),
                      (a.food[i] < NEED_LOW, EC.R_CANTEEN),
                      (a.water[i] < NEED_LOW, EC.R_CANTEEN),
                      (a.sleep[i] < NEED_LOW, EC.R_QUARTERS)):
        if not low or not e.room_n[room]:
            continue
        # Ηδη πάει (ή είναι) σε τέτοιο δωμάτιο; Τότε τίποτα. Χωρίς αυτόν τον
        # έλεγχο κάθε άποικος ξαναέψαχνε το κοντινότερο δωμάτιο σε ΚΑΘΕ
        # επίσκεψη, μαζί με τη σελιδοποίηση και τις οκτώ αναγνώσεις του DIST.
        d = a.dest[i]
        if d < EC.MAX_DOME and e.dome[d * EC.DOME_REC + EC.D_ROOM] == room:
            return
        d = EC.nearest_room(e, room, a.node[i])
        if d == 255:
            break                           # υπάρχει, αλλά δεν φτάνει εκεί
        a.task[i] = T_NEED
        a.dest[i] = d
        return
    sated(a, i)


def sated(a, i):
    """Χορτάτος: ξαναγίνεται διαθέσιμος — μέσα. Εξω το T_NEED τον πηγαίνει
    μέσα (η στολή), και αν το έσβηνε ο πίνακας εργασιών θα τον ξανάστελνε στη
    δουλειά, η στολή πίσω, ως να αδειάσει (βήμα 90)."""
    if a.task[i] == T_NEED and a.flags[i] & F_INDOORS:
        a.task[i] = NO_TASK


# --- ο τροχός (§7.2) ------------------------------------------------------
WH_SLOTS = 16
WH_NMOVE = 7                # θέσεις κίνησης 0-6 (βήμα 173· ως τότε 8)
WH_MOVE_N = 25              # πράκτορες ανά θέση κίνησης, και η 6 έναν ακόμη (12 ως το 172)
# Δέκα ανά θέση: 4 x 10 = 40 άποικοι ανά περιστροφή, καθένας κάθε τέσσερις
# (βήμα 173· ως τότε 3 x 8 από τους 96). Το πλήρες πέρασμα κοστίζει ~740 us ανά
# άποικο και δεν υπάρχει ένα σημείο που να φταίει — απλώς κάνει πολλά. Το §7.3
# δίνει ακριβώς αυτόν τον μοχλό. Και ο αραιότερος ρυθμός είναι ΠΙΟ κοντά στην
# οικονομία του §6.5: μια μπάρα των 255 κρατά τώρα 1.020 περιστροφές, δηλαδή
# περίπου ενάμισι sol.
WH_NNEED = 4                # θέσεις αναγκών 7-10
WH_NEED_N = 10              # άποικοι ανά θέση αναγκών
WH_NEED_SPAN = WH_NNEED * WH_NEED_N
MAX_COLONIST = 160          # οι άποικοι του §6.1 (96 ως το βήμα 172, με τα ρομπότ)


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
        self.foe = {"pk": 0}            # το fo_pk (βήμα 111)
        if Sim.PLANT_CLASS is None:
            Sim.PLANT_CLASS = EC.load_plant_class()
        self.pc = Sim.PLANT_CLASS

    def tick(self):
        """Ενα frame: μία θέση του τροχού. Η δρομολόγηση δεν είναι θέση."""
        s = self.slot
        self.slot = (s + 1) & (WH_SLOTS - 1)
        if s < WH_NMOVE:
            n = WH_MOVE_N + (s == WH_NMOVE - 1)     # οι 176 στα επτά: 150-175 (wm_last)
            move_slice(self.a, self.g, self.nexthop, self.occ,
                       s * WH_MOVE_N, n, self.e)
        elif s < WH_NMOVE + WH_NNEED:
            # Το πλήρες πέρασμα αναγκών κοστίζει 348 us ανά άποικο. Τρεις
            # θέσεις x 32 δεν χωρούσαν άνετα σε frame, οπότε ο τροχός κάνει
            # αυτό ακριβώς που λέει το §7.3: μισούς ανά περιστροφή, τον
            # καθένα κάθε δεύτερη. Οι ανάγκες απλώς κρατάνε διπλάσιο χρόνο.
            # Οι φέτες δεν φτάνουν ποτέ τα ρομπότ (160-175, βήμα 173): η
            # βάση κάνει τον κύκλο 0, 40, 80, 120.
            first = self.need_base + (s - WH_NMOVE) * WH_NEED_N
            needs_slice(self.a, self.e, self.occ, first, WH_NEED_N)
            if s == WH_NMOVE + WH_NNEED - 1:
                self.need_base = (self.need_base + WH_NEED_SPAN) % MAX_COLONIST
        elif s == 11:
            EC.production_slice(self.e, plant_class=self.pc)
        elif s == 12:
            alive, inside = en_count(self.a, self.e.alive)
            EC.flow_balance(self.e, alive, inside)
        elif s == 14:
            EC.rooms_rebuild(self.e, self.pc)
        elif s == 13:
            EC.jobs_tick(self.e, self.a, F_ALIVE, F_WORKING)
        elif s == 15:
            new_sol = EC.events(self.e)
            if self.e.air_out != 255:
                air_out(self.a, self.e.air_out, self.g)
                self.e.air_out = 255
            if new_sol:
                EC.sol_rollover(self.e, self.a, F_ALIVE, F_WORKING, NEED_LOW)
            EC.bot_tick(self.e, self.a, self.occ)
            foe_tick(self.e, self.a, self.g, self.nexthop, self.occ, self.foe)
            ship_tick(self.e, self.a, self.g, self.nexthop, self.occ)
        # 13 πίνακας εργασιών, 14 ελεύθερη — δεν έχουν γραφτεί, ούτε εδώ ούτε
        # στον Z80.


def en_count(a, upto):
    """Το en_count του Z80 (src/door.asm): (ζωντανοί, ζωντανοί μέσα), μόνο οι 160
    των αποίκων (βήμα 173· 80 από το 92), ανά οκτώ, και σταματά μετά την οκτάδα
    όπου βρέθηκαν `upto` (το EC_ALIVE ως τώρα: ποτέ κάτω από τους ζωντανούς)."""
    alive = inside = 0
    for g in range(0, EC.AG_BOT0, 8):
        for i in range(g, g + 8):
            if a.flags[i] & F_ALIVE:
                alive += 1
                inside += bool(a.flags[i] & F_INDOORS)
        if alive >= upto:
            break
    return alive, inside


def ship_tick(e, a, g, nexthop, occ):
    """Το ship_tick του Z80 (src/ship.asm): με πλοίο επισκεπτών προσγειωμένο
    πρώτα οι επισκέπτες (βήμα 136), και μετά το πλοίο."""
    if e.ship_state == EC.SHIP_LANDED and e.ship_kind == EC.SK_VISITOR:
        visit_tick(e, a, g, nexthop, occ)
    EC.ship_tick(e, a, e.pad_node, F_ALIVE, occ, g)


def air_out(a, n, g):
    """Το lk_air_out (src/door.asm, βήμα 90): ένα airlock ξανάγινε εργοτάξιο,
    και όσοι στέκονταν μέσα του είναι έξω, με γεμάτη στολή. Και από το βήμα
    104 όσοι ταξιδεύουν μέσα προς αυτό: ζωντανοί, με το F_INDOORS, και ο
    κόμβος στην άλλη άκρη της ακμής τους (η άφιξη, move_one) είναι το n."""
    for k in range(MAXAGENT):
        if not a.flags[k] & F_ALIVE:
            continue
        if a.edge[k] == NO_EDGE:
            out = a.node[k] == n
        else:
            out = (a.flags[k] & F_INDOORS
                   and g.adj[a.node[k] * G.MAXDEG + a.edge[k]] == n)
        if out:
            a.flags[k] &= ~F_INDOORS & 0xFF
            a.suit[k] = EC.SUIT_TRIP


def pop_id(k):
    """Η ταυτότητα του k-οστού της σκηνής (βήμα 173): οι 40 πρώτοι στα 0-39, οι
    40 επόμενοι στα 120-159 — πάνω από το 128, όπου ως το 172 δεν ζούσε
    κανείς — και οι 16 τελευταίοι στα ρομπότ, 160-175. Ως το 172 ο k ήταν ο
    k: άποικοι 0-79, ρομπότ 80-95."""
    return k if k < 40 else k + 80


def populate(sim, n_agents=96, seed=7):
    """Μια αρχική κατάσταση που ασκεί τις γωνίες: γεμάτοι κόμβοι, απρόσιτοι
    προορισμοί, νεκροί ανάμεσα στους ζωντανούς, όλοι οι ρόλοι. Ο k-οστός
    στην ταυτότητα pop_id(k), με τα ίδια bytes που είχε ως το βήμα 172."""
    a, g = sim.a, sim.g
    x = seed
    for k in range(n_agents):
        i = pop_id(k)
        x = ((x * 75) + 74) & 0xFFFF
        # ΟΧΙ από τη γεννήτρια. Ο LCG `x = 75x + 74` έχει αδύναμα χαμηλά bits:
        # το (x>>3)&7 έβγαζε ΜΟΝΟ τους ρόλους 0 και 2, δηλαδή κάθε αποικία
        # δοκιμής ήταν εργάτες και βιολόγοι — ούτε ένας μηχανικός, ούτε ένας
        # γιατρός. Η επισκευή και η ίαση δεν είχαν εκτελεστεί ποτέ.
        a.role[i] = k & 7
        a.flags[i] = F_ALIVE if (x & 31) else 0      # ~3% νεκροί εξαρχής
        # Οι άποικοι ζουν ΣΤΟΥΣ ΘΟΛΟΥΣ. Σκορπισμένοι σε όλο τον γράφο, οι
        # μισοί ξεκινούσαν πάνω σε εξωτερικές δομές και το ταξίδι ως την
        # κοντινότερη καντίνα κρατούσε περισσότερο από την ίδια την ανάγκη:
        # κανείς δεν προλάβαινε ποτέ να πιάσει δουλειά.
        ndome = min(EC.MAX_DOME, g.n)
        node = (x >> 6) % ndome
        a.node[i] = node
        a.dest[i] = ((x >> 9) * 7 + k) % ndome
        a.o2[i] = 190 + (x & 63)
        a.water[i] = 150 + ((x >> 2) & 63)
        a.food[i] = 120 + ((x >> 4) & 63)
        a.sleep[i] = 110 + ((x >> 5) & 63)
        # Μερικοί μπαίνουν ήδη πεινασμένοι, διψασμένοι ή άυπνοι. Χωρίς αυτούς
        # οι μπάρες θέλουν εκατοντάδες περιστροφές για να πέσουν κάτω από το
        # κατώφλι, και η δοκιμή τελειώνει πριν φάει ποτέ κανείς.
        if k % 4 == 1:
            a.food[i] = 30
        if k % 5 == 2:
            a.water[i] = 30
        if k % 3 == 0:
            a.sleep[i] = 30
        a.health[i] = 200
        a.morale[i] = 150
        a.suit[i] = EC.SUIT_TRIP
        # Εξι άποικοι μπαίνουν ετοιμοθάνατοι. Χωρίς αυτούς η διαδρομή του
        # θανάτου — θέση, δουλειά, χειριστής, πένθος — δεν εκτελείται ποτέ
        # μέσα στη διάρκεια της δοκιμής.
        if k % 16 == 5:
            a.health[i] = 6
            a.o2[i] = 4
            a.water[i] = 4
        if a.flags[i] & F_ALIVE:
            a.slot[i] = claim(sim.occ, node)          # μπορεί να γυρίσει 255
            # Μέσα, όπως θα τους άφηνε το en_put (βήμα 87). Χωρίς αυτό οι
            # θόλοι της σκηνής ήταν «έξω» ως την πρώτη μετακίνηση: κανείς δεν
            # ανέπνεε, και η θέση των αναγκών μετρούσε τη φτηνή της διαδρομή.
            set_in(a, i, EC.indoor_node(sim.e, node))
    # ΤΟ EC_ALIVE ΟΣΟΙ ΖΟΥΝ (βήμα 173): στο παιχνίδι δεν είναι ποτέ κάτω από
    # τους ζωντανούς, και το en_count σταματά εκεί (src/door.asm). Με το 0 του
    # EC.populate η πρώτη μέτρηση έβρισκε 7 και δεν ξανάβλεπε τους άλλους.
    sim.e.alive = sum(1 for i in range(EC.AG_BOT0) if a.flags[i] & F_ALIVE)
    return sim
