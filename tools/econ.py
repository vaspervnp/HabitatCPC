"""Η οικονομία: αποθέματα, συνταγές, παραγωγή, ισοζύγιο ροών (§6.5, §6.8).

ΤΡΕΙΣ ΑΠΟΦΑΣΕΙΣ ΠΟΥ ΤΟ §6.5 ΑΦΗΝΕΙ ΑΝΟΙΧΤΕΣ, και δεν μπορούσαν να μείνουν:

1. ΔΕΚΑ ΑΠΟΘΕΜΑΤΑ, ΔΕΚΑΤΕΣΣΕΡΑ ΧΡΕΙΑΖΟΝΤΑΙ. Η αλυσίδα του ίδιου τμήματος
   καταναλώνει Starch, Vegetables, Medicinal και Vitromeat — τίποτα από τα
   τέσσερα δεν είναι στη λίστα των δέκα. Χωρίς αυτά το θερμοκήπιο παράγει στο
   κενό και τρεις μηχανές δεν έχουν είσοδο.

2. ΟΚΤΩ BYTES Η ΣΥΝΤΑΓΗ, ΤΡΕΙΣ ΕΙΣΟΔΟΙ. Το §6.5 ορίζει εγγραφή
   `in1,qty1,in2,qty2,out,qty,power,flags` και στην ίδια σελίδα δίνει δύο
   συνταγές με τρεις εισόδους (robots, food). Η εγγραφή γίνεται δέκα bytes.
   Κόστος: 20 bytes συνολικά.

3. ΤΕΣΣΕΡΙΣ ΥΠΟΔΟΧΕΣ, ΟΚΤΩ ΕΧΕΙ Ο ΜΕΓΑΛΟΣ ΘΟΛΟΣ. Το §6.1 δίνει στον θόλο
   `machines[4] health[4]`, αλλά το machine_count των assets λέει 1/4/8. Η
   εγγραφή θόλου γίνεται 24 bytes ώστε ο μεγάλος θόλος να έχει τις οκτώ του.

Η ΠΑΡΑΓΩΓΗ ΔΙΑΒΑΖΕΙ ΤΟ ΙΣΟΖΥΓΙΟ ΤΗΣ ΠΡΟΗΓΟΥΜΕΝΗΣ ΠΕΡΙΣΤΡΟΦΗΣ. Αλλιώς οι δύο
; θέσεις θα ήθελαν η μία την άλλη μέσα στο ίδιο frame. Το §6.5 λέει ήδη
«buffered», και αυτό είναι το buffer.
"""

def load_plant_class():
    """Η κατηγορία κάθε φυτού έρχεται από τα assets, όχι από εδώ."""
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from sprites import load_map, load_bin
    m, b = load_map(), load_bin()
    sp = m["plant_class"]
    return list(b[sp.off:sp.off + sp.size])


# --- αποθέματα ------------------------------------------------------------
STOCKS = ["water", "food", "ore", "metal", "bioplastic", "processors",
          "spares", "medicine", "guns", "bots",
          "starch", "vegetables", "medicinal", "vitromeat"]
N_STOCK = len(STOCKS)
S_WATER, S_FOOD, S_ORE, S_METAL, S_BIOPL, S_PROC, S_SPARE, S_MEDI, S_GUN, \
    S_BOT, S_STARCH, S_VEG, S_MEDPLANT, S_MEAT = range(N_STOCK)
NO_STOCK = 255

# --- μηχανές, με τη σειρά του MACH στο pack.py ----------------------------
MACH = ["oxygen", "iron", "bioplastic", "weapons", "processors",
        "robots", "food", "spares", "medical", "vitromeat",
        "beds", "medstore"]
N_MACH = len(MACH)
NO_MACH = 255

MF_OPERATOR = 1         # θέλει χειριστή στη θέση εργασίας
MF_FLOW = 2             # η έξοδος είναι ροή, όχι απόθεμα (οξυγόνο)

# in1,q1, in2,q2, in3,q3, out,q, power, flags
RECIPE = [
    (S_WATER, 1, NO_STOCK, 0, NO_STOCK, 0, NO_STOCK, 20, 4, MF_FLOW),   # oxygen
    (S_ORE, 2, NO_STOCK, 0, NO_STOCK, 0, S_METAL, 1, 3, MF_OPERATOR),   # iron
    (S_STARCH, 2, NO_STOCK, 0, NO_STOCK, 0, S_BIOPL, 1, 3, MF_OPERATOR),
    (S_METAL, 2, S_PROC, 1, NO_STOCK, 0, S_GUN, 1, 5, MF_OPERATOR),     # weapons
    (S_METAL, 2, NO_STOCK, 0, NO_STOCK, 0, S_PROC, 1, 5, MF_OPERATOR),
    (S_METAL, 2, S_PROC, 1, S_BIOPL, 1, S_BOT, 1, 8, MF_OPERATOR),      # robots
    (S_STARCH, 1, S_VEG, 1, S_MEAT, 1, S_FOOD, 1, 4, MF_OPERATOR),      # food
    (S_METAL, 1, S_BIOPL, 1, NO_STOCK, 0, S_SPARE, 1, 3, MF_OPERATOR),
    (S_MEDPLANT, 2, NO_STOCK, 0, NO_STOCK, 0, S_MEDI, 1, 3, MF_OPERATOR),
    (S_WATER, 2, NO_STOCK, 0, NO_STOCK, 0, S_MEAT, 1, 4, MF_OPERATOR),  # vitromeat
    # Τα δύο του ιατρείου δεν ΠΑΡΑΓΟΥΝ: είναι έπιπλα που κάνουν το δωμάτιο να
    # δουλεύει. Τα κρεβάτια θέλουν γιατρό από πάνω τους, η φαρμακαποθήκη όχι.
    # Παραμένουν εγγραφές συνταγής ώστε το πέρασμα παραγωγής να μην ξέρει από
    # ειδικές περιπτώσεις.
    (NO_STOCK, 0, NO_STOCK, 0, NO_STOCK, 0, NO_STOCK, 0, 1, MF_OPERATOR),
    (NO_STOCK, 0, NO_STOCK, 0, NO_STOCK, 0, NO_STOCK, 0, 0, 0),
]

# --- θόλοι ----------------------------------------------------------------
DOME_REC = 24
MAX_DOME = 64
MACH_SLOTS = 8
MACHINE_COUNT = [1, 4, 8]           # ανά μέγεθος s/m/l — από τα assets

D_CX, D_CY, D_SIZE, D_ROOM, D_STATE, D_INTEG, D_POWER, D_OPS = range(8)
N_ROOM_F = 12               # είδη δωματίων — βλ. rooms_rebuild
D_MACH = 8                          # 8 bytes
D_HEALTH = 16                       # 8 bytes

DS_EMPTY, DS_BUILDING, DS_ACTIVE = 0, 1, 2

# --- δομές ----------------------------------------------------------------
STRUCT_REC = 8
MAX_STRUCT = 64
ST_CX, ST_CY, ST_KIND, ST_SIZE, ST_STATE, ST_INTEG, ST_OUT, ST_SPARE = range(8)

# είδη δομών, με τη σειρά του STRUCTS στο pack.py (solar/turbine/collector/
# extractor σε τρία μεγέθη, μετά mine/airlock/pad/ship)
K_SOLAR, K_TURBINE, K_COLLECTOR, K_EXTRACTOR, K_MINE, K_AIRLOCK, K_PAD, K_SHIP \
    = range(8)

SOLAR_OUT = [2, 8, 18]              # §6.5, ανά μέγεθος
TURBINE_OUT = [3, 12, 27]
COLLECTOR_CAP = [40, 160, 360]
EXTRACTOR_OUT = [6, 24, 54]
EXTRACTOR_POWER = [2, 6, 12]
MINE_OUT, MINE_POWER = 20, 8

O2_PER_COLONIST = 2


class Econ:
    """Ο,τι κρατά η οικονομία ανάμεσα σε δύο frames."""

    def __init__(self):
        self.stock = [0] * N_STOCK
        self.cap = 600                      # από τους θόλους αποθήκευσης
        self.dome = bytearray(MAX_DOME * DOME_REC)
        self.struct = bytearray(MAX_STRUCT * STRUCT_REC)
        self.n_dome = 0
        self.n_struct = 0
        # ισοζύγιο (§6.5) — 16-bit το καθένα
        self.power_store = 0
        self.power_cap = 0
        self.power_prod = 0
        self.power_use = 0
        self.mach_power = 0         # ό,τι τράβηξαν οι μηχανές στο τελευταίο σάρωμα
        self.o2_prod = 0
        self.o2_use = 0
        self.power_ok = 1                   # το buffer που διαβάζει η παραγωγή
        self.o2_ok = 1
        # συσσωρευτές του τρέχοντος σαρώματος παραγωγής
        self.acc_power = 0
        self.acc_o2 = 0
        self.prod_dome = 0                  # πού έφτασε το σάρωμα
        # ρολόι και καιρός (§6.10)
        self.sol = 0
        self.frame = 0
        self.day = 1
        self.wind = 2                       # 0..3
        self.rnd = 0xACE1
        # πίνακας εργασιών (§6.7) και οι δύο περιστροφικοί του δείκτες
        self.job = bytearray(MAX_JOB * JOB_REC)
        for j in range(MAX_JOB):
            self.job[j * JOB_REC + J_KIND] = NO_JOB
            self.job[j * JOB_REC + J_AGENT] = 255
        self.job_dome = 0
        self.job_agent = 0
        self.room_n = bytearray(12)
        self.room_list = bytearray(12 * 8)
        self.alive = 0
        self.gameover = 0
        self.gloom = 0              # πένθος: ανεβαίνει με κάθε θάνατο
        self.storm = 0              # περιστροφές αμμοθύελλας που απομένουν
        self.amenity = 0            # δέντρα και σαλόνια — παρηγοριά (§6.6)
        # Το μήκος του sol είναι ΔΕΔΟΜΕΝΟ και όχι σταθερά: μια δοκιμή που
        # θέλει να δει πέντε sols δεν μπορεί να περιμένει 60.000 frames.
        self.sollen = SOL_FRAMES
        self.daylen = DAY_FRAMES
        # --- πλοία (§6.11) ---
        self.ship_state = 0         # 0 κανένα · 1 έρχεται · 2 προσγειωμένο
        self.ship_kind = 0          # 0 άποικοι · 1 έμπορος · 2 επισκέπτες
        self.ship_eta = 0           # περιστροφές ως την άφιξη
        self.pop_cap = 4            # το Control ανεβάζει το ταβάνι
        self.pad_node = 255         # η πλατφόρμα προσγείωσης, ως κόμβος
        # --- ορόσημα (§10.2) ---
        self.prod_mask = 0          # ποια αποθέματα φτιάχτηκαν ΕΔΩ
        self.milestones = 0
        self.deaths_sol = 0
        self.no_death_sols = 0
        self.green_sols = 0
        self.no_trade_sols = 0
        self.traded = 0
        self.dist = None            # ο πίνακας αποστάσεων, δίνεται απ' έξω


def dome_field(e, d, f):
    return e.dome[d * DOME_REC + f]


def set_dome(e, d, f, v):
    e.dome[d * DOME_REC + f] = v & 0xFF


def add_stock(e, s, q):
    v = e.stock[s] + q
    e.stock[s] = min(v, e.cap)


def take_stock(e, s, q):
    e.stock[s] -= q


SOL_FRAMES = 12000          # §10.4 — τέσσερα πραγματικά λεπτά
DAY_FRAMES = SOL_FRAMES * 3 // 5
PROD_DOMES = 16             # θόλοι ανά επίσκεψη (§7.2) — σάρωμα σε 4 περιστροφές


def lfsr(x):
    """Ο ίδιος Galois με τη γεννήτρια κόσμου, ΞΕΧΩΡΙΣΤΗ κατάσταση: ο κόσμος
    πρέπει να μένει αναπαράξιμος από το seed του και μόνο."""
    bit = x & 1
    x >>= 1
    if bit:
        x ^= 0xB400
    return x


# Ενα θερμοκήπιο κρατά ΦΥΤΑ στις ίδιες υποδοχές όπου ένας άλλος θόλος κρατά
# μηχανές: ίδιο πεδίο, άλλο νόημα, και το είδος δωματίου λέει ποιο.
# plant_class: 0 άμυλο · 1 λαχανικά · 2 φάρμακα · 3 ηθικό (δέντρο)
PLANT_OUT = [(S_STARCH, 3), (S_VEG, 2), (S_MEDPLANT, 2), (None, 0)]
PLANT_WATER = 1
PLANT_POWER = 1


def run_plant(e, base, s, plant, plant_class):
    """Μία υποδοχή θερμοκηπίου. Νερό και ρεύμα μέσα, χλωρίδα έξω."""
    if e.stock[S_WATER] < PLANT_WATER:
        return
    e.stock[S_WATER] -= PLANT_WATER
    e.acc_power += PLANT_POWER
    out, qty = PLANT_OUT[plant_class[plant] & 3]
    if out is not None:
        add_stock(e, out, qty)
        e.prod_mask |= 1 << out


def run_dome(e, d, plant_class=None):
    """Μία επίσκεψη σε έναν θόλο: όσες μηχανές του μπορούν, τρέχουν."""
    base = d * DOME_REC
    if e.dome[base + D_STATE] != DS_ACTIVE:
        return
    n = MACHINE_COUNT[e.dome[base + D_SIZE]]
    ops = e.dome[base + D_OPS]
    green = e.dome[base + D_ROOM] == R_GREENHOUSE
    for s in range(n):
        if green:
            p = e.dome[base + D_MACH + s]
            if p == NO_MACH or e.dome[base + D_HEALTH + s] == 0:
                continue
            if s >= ops or not e.power_ok:      # τα φυτά θέλουν φροντίδα
                continue
            run_plant(e, base, s, p, plant_class)
            continue
        m = e.dome[base + D_MACH + s]
        if m == NO_MACH:
            continue
        if e.dome[base + D_HEALTH + s] == 0:        # χαλασμένη
            continue
        r = RECIPE[m]
        if (r[9] & MF_OPERATOR) and s >= ops:       # χωρίς χειριστή
            continue
        if not e.power_ok:                          # μπλακάουτ
            continue
        ins = ((r[0], r[1]), (r[2], r[3]), (r[4], r[5]))
        if any(st != NO_STOCK and e.stock[st] < q for st, q in ins):
            continue                                # λείπει είσοδος: δεν καίει
        for st, q in ins:
            if st != NO_STOCK:
                e.stock[st] -= q
        e.acc_power += r[8]
        if r[9] & MF_FLOW:
            e.acc_o2 += r[7]
        elif r[6] != NO_STOCK:              # τα κρεβάτια δεν παράγουν τίποτα
            add_stock(e, r[6], r[7])
            e.prod_mask |= 1 << r[6]        # φτιάχτηκε ΕΔΩ (§10.2)


def production_slice(e, count=PROD_DOMES, plant_class=None):
    """Θέση 11: PROD_DOMES θόλοι. Στο τέλος του σαρώματος δημοσιεύει."""
    for _ in range(count):
        run_dome(e, e.prod_dome, plant_class)
        e.prod_dome += 1
        if e.prod_dome >= MAX_DOME:
            e.prod_dome = 0
            e.mach_power = e.acc_power      # ό,τι τράβηξαν οι μηχανές
            e.o2_prod = e.acc_o2
            e.acc_power = 0
            e.acc_o2 = 0


def flow_balance(e, alive):
    """Θέση 12: παραγωγή απέναντι σε κατανάλωση, και η μπαταρία."""
    prod = cap = water = ore = 0
    use = e.mach_power
    for i in range(MAX_STRUCT):
        st = i * STRUCT_REC
        if e.struct[st + ST_STATE] != DS_ACTIVE:
            continue
        k, sz = e.struct[st + ST_KIND], e.struct[st + ST_SIZE]
        if k == K_SOLAR:
            if e.day and not e.storm:       # η σκόνη σκεπάζει τα πάνελ
                prod += SOLAR_OUT[sz]
        elif k == K_TURBINE:
            prod += TURBINE_OUT[sz] * e.wind // 3
        elif k == K_COLLECTOR:
            cap += COLLECTOR_CAP[sz]
        elif k == K_EXTRACTOR:
            use += EXTRACTOR_POWER[sz]
            water += EXTRACTOR_OUT[sz]
        elif k == K_MINE:
            use += MINE_POWER
            ore += MINE_OUT

    e.power_prod, e.power_cap, e.power_use = prod, cap, use
    if prod >= use:
        e.power_store = min(e.power_store + prod - use, cap)
        e.power_ok = 1
    else:
        short = use - prod
        if e.power_store >= short:
            e.power_store -= short
            e.power_ok = 1
        else:
            e.power_store = 0
            e.power_ok = 0

    if e.power_ok:                          # οι αντλίες θέλουν ρεύμα
        add_stock(e, S_WATER, water)
        add_stock(e, S_ORE, ore)
        # Το νερό και το μετάλλευμα βγαίνουν από ΔΟΜΕΣ, όχι από μηχανές
        # θόλου, αλλά βγαίνουν εδώ — και η «ανεξαρτησία» του §10.2 τα θέλει.
        if water:
            e.prod_mask |= 1 << S_WATER
        if ore:
            e.prod_mask |= 1 << S_ORE

    e.o2_use = alive * O2_PER_COLONIST
    e.o2_ok = 1 if e.o2_prod >= e.o2_use else 0
    e.alive = alive
    if alive == 0:                      # §10.3 — η μόνη συνθήκη ήττας
        e.gameover = 1


STORM_LEN = 32          # περιστροφές — περίπου δέκα δευτερόλεπτα


def break_one(e, x):
    """Μια μηχανή σταματά. Οχι «χαλάει λίγο»: υγεία μηδέν, και μένει εκεί ως
    να έρθει μηχανικός με ένα ανταλλακτικό (§6.7 Repair)."""
    d = x % MAX_DOME
    b = d * DOME_REC
    if e.dome[b + D_STATE] != DS_ACTIVE:
        return
    n = MACHINE_COUNT[e.dome[b + D_SIZE]]
    s = (x >> 6) % n
    if e.dome[b + D_MACH + s] == NO_MACH or e.dome[b + D_HEALTH + s] == 0:
        return
    e.dome[b + D_HEALTH + s] = 0


def events(e):
    """Θέση 15: μία ζαριά. Ρολόι, μέρα/νύχτα, άνεμος, θύελλα, βλάβες (§6.10).

    Τραβάει ΠΑΝΤΑ τρεις τιμές από τη γεννήτρια, είτε τις χρειαστεί είτε όχι.
    Μια ζαριά υπό όρους θα σήμαινε ότι η ακολουθία εξαρτάται από το αποτέλεσμα
    της προηγούμενης, και η αναπαραγωγή θα γινόταν δουλειά.
    """
    e.frame += 16                           # μία περιστροφή
    if e.frame >= e.sollen:
        e.frame -= e.sollen
        e.sol = (e.sol + 1) & 0xFF
        new_sol = True
    else:
        new_sol = False
    e.day = 1 if e.frame < e.daylen else 0
    if e.gloom:                             # το πένθος περνάει, αργά
        e.gloom -= 1

    e.rnd = lfsr(e.rnd)
    r1 = e.rnd
    e.rnd = lfsr(e.rnd)
    r2 = e.rnd
    e.rnd = lfsr(e.rnd)
    r3 = e.rnd

    # Κάθε ζαριά κοιτάζει ΑΛΛΟ κομμάτι του αριθμού. Ο Galois ολισθαίνει δεξιά,
    # άρα δύο διαδοχικά τραβήγματα είναι σχεδόν το ίδιο νούμερο μετατοπισμένο:
    # όταν και οι δύο δοκιμές κοιτούσαν τα χαμηλά bits, η θύελλα και η βλάβη
    # έπεφταν μαζί ή καθόλου.
    if (r1 & 15) == 0:                      # ο άνεμος αλλάζει σπάνια
        e.wind = (r1 >> 4) & 3

    if e.storm:                             # αμμοθύελλα: τα πάνελ σκεπάζονται
        e.storm -= 1
    elif (r2 >> 9) == 0:                    # τα ΨΗΛΑ bits του δεύτερου
        e.storm = STORM_LEN

    if (r3 & 0x1F) == 0:                    # απλή βλάβη: τα χαμηλά του τρίτου
        break_one(e, r3 >> 5)

    if (r2 & 0x3F) == 0 and e.ship_state == SHIP_NONE and e.pad_node != 255:
        call_ship(e, SK_VISITOR)            # απρόσκλητοι (§6.11)

    if (r3 >> 8) == 0:                      # ηλιακή έκλαμψη: τα ψηλά του ίδιου
        break_one(e, r3 + 37)
        break_one(e, (r3 >> 3) + 101)
        break_one(e, (r3 >> 1) + 173)

    return new_sol


def to_bytes(e):
    """Η οικονομία όπως κάθεται στη μνήμη, για σύγκριση με τον Z80."""
    out = bytearray()
    for v in e.stock:
        out += int(v).to_bytes(2, "little")
    for v in (e.power_store, e.power_cap, e.power_prod, e.power_use,
              e.mach_power, e.o2_prod, e.o2_use, e.acc_power, e.acc_o2):
        out += int(v).to_bytes(2, "little")
    out += bytes([e.power_ok, e.o2_ok, e.prod_dome, e.day, e.wind, e.sol])
    # (το job_dome/job_agent μπαίνουν στο τέλος, βλ. ECON_BYTES)
    out += int(e.frame).to_bytes(2, "little")
    out += int(e.rnd).to_bytes(2, "little")
    out += bytes([e.job_dome, e.job_agent, e.alive, e.gameover, e.gloom,
                  e.storm, e.amenity, 0])
    out += int(e.sollen).to_bytes(2, "little")
    out += int(e.daylen).to_bytes(2, "little")
    out += int(e.prod_mask).to_bytes(2, "little")
    out += int(e.ship_eta).to_bytes(2, "little")
    out += bytes([e.ship_state, e.ship_kind, e.pop_cap, e.milestones,
                  e.deaths_sol, e.no_death_sols, e.green_sols,
                  e.no_trade_sols, e.traded, e.pad_node])
    return bytes(out)


ECON_BYTES = 64 + 8 + 10                            # + sol/ship/ορόσημα = 82


def populate(e, n_dome=24, n_struct=36, seed=11):
    """Μια αποικία που όντως δουλεύει: παραγωγοί ρεύματος, αντλίες, ορυχείο,
    και θόλοι με μηχανές που έχουν πού να τραβήξουν. Ντετερμινιστική."""
    x = seed
    def rnd():
        nonlocal x
        x = ((x * 75) + 74) & 0xFFFF
        return x

    # Μια αποικία που ΕΧΕΙ προμήθειες. Οχι για να είναι εύκολη: με άδεια
    # ντουλάπια όλοι τρέχουν συνέχεια για φαγητό και κανείς δεν πιάνει ποτέ
    # δουλειά, οπότε ο πίνακας εργασιών δεν δοκιμάζεται καθόλου.
    # Λίγο βιοπλαστικό και επεξεργαστές στην αρχή: η αλυσίδα των ρομπότ
    # θέλει Metal + Processors + Bioplastic μαζί, και χωρίς απόθεμα εκκίνησης
    # δεν γυρίζει ποτέ — οπότε η «ανεξαρτησία» του §10.2 δεν πιάνεται.
    for s, q in ((S_WATER, 600), (S_FOOD, 400), (S_ORE, 600), (S_STARCH, 200),
                 (S_VEG, 200), (S_MEDPLANT, 300), (S_MEDI, 200), (S_SPARE, 40),
                 (S_BIOPL, 120), (S_PROC, 120), (S_METAL, 200)):
        e.stock[s] = q
    # Μια θύελλα ήδη σε εξέλιξη. Η ζαριά τη ρίχνει μία στις 128 περιστροφές,
    # που σημαίνει ότι ένα παράθυρο 40 περιστροφών τη χάνει τις δύο φορές
    # στις τρεις — και τότε ο κλάδος της δεν δοκιμάζεται καθόλου.
    e.storm = 20
    # Ενα πλοίο αποίκων ήδη καθ' οδόν, ώστε η προσγείωση — και η γέννηση
    # τεσσάρων ανθρώπων στην πίστα — να συμβεί μέσα στο παράθυρο της δοκιμής.
    e.ship_state = SHIP_INCOMING
    e.ship_kind = SK_COLONIST
    e.ship_eta = 6

    # Περισσότερη γεννήτρια: με δύο ηλιακά ανά έξι δομές η αποικία έσβηνε
    # κάθε νύχτα, οι συλλέκτες δεν προλάβαιναν ποτέ να φορτίσουν, και το
    # «όλα πράσινα» του §10.2 ήταν ανέφικτο.
    # Αρκετή γεννήτρια για να ΠΕΡΑΣΕΙ ΤΗ ΝΥΧΤΑ. Με λιγότερη, η αποικία
    # μπλακάουταρε κάθε βράδυ, το «όλα πράσινα» του §10.2 δεν πιανόταν ποτέ,
    # και το ευκολότερο ορόσημο ήταν το μόνο ανέφικτο.
    kinds = [K_SOLAR, K_SOLAR, K_COLLECTOR, K_TURBINE, K_SOLAR, K_COLLECTOR,
             K_SOLAR, K_TURBINE, K_COLLECTOR, K_SOLAR, K_EXTRACTOR, K_MINE]
    for i in range(n_struct):
        b = i * STRUCT_REC
        # Μία πλατφόρμα προσγείωσης: χωρίς αυτήν κανένα πλοίο δεν έχει πού να
        # κατέβει, και όλο το §6.11 μένει αδοκίμαστο.
        k = K_PAD if i == n_struct - 1 else kinds[i % len(kinds)]
        e.struct[b + ST_KIND] = k
        e.struct[b + ST_SIZE] = 0 if k in (K_MINE, K_PAD) else 2
        e.struct[b + ST_STATE] = DS_ACTIVE
        e.struct[b + ST_INTEG] = 255
    e.n_struct = n_struct

    # Δέκα μικροί θόλοι με γεννήτρια οξυγόνου. Οχι δύο: 2 x 20 = 40 O2 για
    # 96 αποίκους που θέλουν 192 σημαίνει αποικία που ασφυκτιά σιωπηλά από το
    # πρώτο frame — η υγεία έπεφτε συνέχεια και κανείς δεν πρόφτανε να
    # δουλέψει. Το machine_rules επιτρέπει το mach_oxygen μόνο σε μικρούς.
    forced = {d: (0, 0) for d in range(10)}
    # Κάθε αποικία χρειάζεται καντίνα, κοιτώνες και ιατρείο, αλλιώς οι
    # ανάγκες δεν έχουν πού να ικανοποιηθούν και όλοι πεθαίνουν.
    rooms = [R_CONTROL, R_CANTEEN, R_QUARTERS, R_GREENHOUSE, R_FACTORY,
             R_MEDBAY, R_CANTEEN, R_QUARTERS, R_GREENHOUSE, R_LAB,
             R_STORAGE, R_GREENHOUSE, R_LOUNGE, R_CONTROL]
    for d in range(n_dome):
        b = d * DOME_REC
        e.dome[b + D_ROOM] = (R_OXYGEN if d in forced
                              else rooms[(d - len(forced)) % len(rooms)])
        size = forced[d][0] if d in forced else (rnd() >> 4) % 3
        e.dome[b + D_SIZE] = size
        e.dome[b + D_STATE] = DS_ACTIVE
        e.dome[b + D_INTEG] = 255
        n = MACHINE_COUNT[size]
        e.dome[b + D_OPS] = (rnd() >> 6) % (n + 1)      # χειριστές, ίσως 0
        for s in range(MACH_SLOTS):
            e.dome[b + D_MACH + s] = NO_MACH
            e.dome[b + D_HEALTH + s] = 0
        if d in forced:
            e.dome[b + D_OPS] = 1
            e.dome[b + D_MACH] = forced[d][1]
            e.dome[b + D_HEALTH] = 200
            continue
        if e.dome[b + D_ROOM] == R_GREENHOUSE:
            # Τα φυτά κάθονται στις ίδιες υποδοχές. Ενα δέντρο (κατηγορία 3)
            # σε κάθε θερμοκήπιο, ώστε να δοκιμάζεται και η παρηγοριά.
            e.dome[b + D_OPS] = n
            for t in range(n):
                e.dome[b + D_MACH + t] = 11 if t == 0 else (t * 3) % 11
                e.dome[b + D_HEALTH + t] = 200
            continue
        # Ο τύπος μηχανής βγαίνει από τη ΘΕΣΗ, όχι από τη γεννήτρια — και ο
        # λόγος δεν είναι τα bits: ήταν ο ίδιος αριθμός σε δύο ρόλους. Το
        # «άδεια υποδοχή αν r%5==0» και το «μηχανή r%10» συμφωνούν όποτε
        # r%10==5, οπότε το εργοστάσιο ρομπότ ήταν ΑΔΥΝΑΤΟ να τοποθετηθεί.
        # Χωρίς ρομπότ, η «ανεξαρτησία» του §10.2 είναι απρόσιτη εξ ορισμού.
        for s in range(n):
            r = rnd() >> 5
            if r % 5 == 0:
                continue                                 # άδεια υποδοχή
            m = (d * 3 + s) % N_MACH
            if m == 0 and size != 0:                     # machine_rules: bit0
                m = 1                                    # οξυγόνο μόνο σε μικρό
            e.dome[b + D_MACH + s] = m
            e.dome[b + D_HEALTH + s] = 0 if (r % 17) == 0 else 200
    e.n_dome = n_dome
    return e


# --- ο πίνακας εργασιών (§6.7) --------------------------------------------
# ΜΙΑ ΣΥΜΒΑΣΗ ΠΟΥ ΤΟ §6.2 ΥΠΟΝΟΕΙ ΧΩΡΙΣ ΝΑ ΤΗ ΛΕΕΙ: το id κόμβου ΕΙΝΑΙ το id
# θόλου για τους πρώτους 64, και δομή n-64 από κει και πάνω. 64 + 64 = 128,
# ακριβώς το ταβάνι κόμβων. Χωρίς αυτό δεν υπάρχει τρόπος να πάει κανείς από
# «εργασία στον κόμβο 12» σε «θόλος 12».

MAX_JOB = 32
JOB_REC = 5
J_KIND, J_NODE, J_AGENT, J_PRIO, J_AGE = range(5)
NO_JOB = 255

J_BUILD, J_OPERATE, J_HAUL, J_DRILL, J_REPAIR, J_HEAL, J_DEFEND = range(7)

# ποιοι ρόλοι δέχονται ποια εργασία — bitmask ανά είδος (§6.7)
JOB_ROLES = [0x22, 0x05, 0x41, 0x81, 0x02, 0x08, 0x10]
JOB_PRIO = [5, 3, 2, 4, 6, 8, 9]

JOB_SCAN = 4                # θόλοι ανά επίσκεψη
JOB_ASSIGN = 4              # αναθέσεις ανά επίσκεψη (§6.7)
JOB_LOOK = 32               # πράκτορες που εξετάζονται ανά επίσκεψη
NO_TASK = 255


def needs_operators(e, d):
    """Πόσες υποδοχές αυτού του θόλου θέλουν κάποιον από πάνω τους.

    Το θερμοκήπιο μετράει ΚΑΘΕ φυτό: τα φυτά θέλουν φροντίδα, όχι χειρισμό,
    αλλά από τη σκοπιά του πίνακα εργασιών είναι το ίδιο πράγμα.
    """
    base = d * DOME_REC
    if e.dome[base + D_STATE] != DS_ACTIVE:
        return 0
    green = e.dome[base + D_ROOM] == R_GREENHOUSE
    n = 0
    for s in range(MACHINE_COUNT[e.dome[base + D_SIZE]]):
        m = e.dome[base + D_MACH + s]
        if m == NO_MACH or e.dome[base + D_HEALTH + s] == 0:
            continue
        if green or (RECIPE[m][9] & MF_OPERATOR):
            n += 1
    return n


def broken_slot(e, d):
    """Η πρώτη σταματημένη υποδοχή αυτού του θόλου, ή None."""
    base = d * DOME_REC
    if e.dome[base + D_STATE] != DS_ACTIVE:
        return None
    for s in range(MACHINE_COUNT[e.dome[base + D_SIZE]]):
        if e.dome[base + D_MACH + s] != NO_MACH \
           and e.dome[base + D_HEALTH + s] == 0:
            return s
    return None


def jobs_tick(e, a, F_ALIVE, F_WORKING):
    """Θέση 13: μάζεψε, ολοκλήρωσε, δημοσίευσε, ανάθεσε — με αυτή τη σειρά."""
    jb = e.job

    # 1. όσοι έφυγαν ή πέθαναν αφήνουν την εργασία τους ανοιχτή
    for j in range(MAX_JOB):
        b = j * JOB_REC
        if jb[b + J_KIND] == NO_JOB:
            continue
        i = jb[b + J_AGENT]
        if i == 255:
            continue
        if not (a.flags[i] & F_ALIVE) or a.task[i] != j:
            jb[b + J_AGENT] = 255

    # 2. όποιος έφτασε, πιάνει δουλειά: ο θόλος αποκτά χειριστή
    for j in range(MAX_JOB):
        b = j * JOB_REC
        if jb[b + J_KIND] == NO_JOB:
            continue
        i = jb[b + J_AGENT]
        if i == 255:
            continue
        node = jb[b + J_NODE]
        if a.node[i] != node or a.edge[i] != 255:
            continue
        if jb[b + J_KIND] == J_REPAIR:
            # Ο μηχανικός φτάνει με ένα ανταλλακτικό και φεύγει. Δεν πιάνει
            # θέση χειριστή — η επισκευή δεν είναι δουλειά που κρατάει.
            s = broken_slot(e, node)
            if s is None or e.stock[S_SPARE] < 1:
                jb[b + J_AGENT] = 255       # τζάμπα δρόμος· μένει ανοιχτή
                a.task[i] = NO_TASK
                continue
            e.stock[S_SPARE] -= 1
            e.dome[node * DOME_REC + D_HEALTH + s] = 200
            a.task[i] = NO_TASK
            jb[b + J_KIND] = NO_JOB
            continue
        if node < MAX_DOME:
            e.dome[node * DOME_REC + D_OPS] += 1
        a.flags[i] |= F_WORKING
        a.task[i] = NO_TASK
        jb[b + J_KIND] = NO_JOB

    # 3. δημοσίευση, JOB_SCAN θόλοι ανά επίσκεψη. Μία εργασία ανά θόλο ανά
    #    επίσκεψη, και η επισκευή προηγείται: μια σταματημένη μηχανή δεν
    #    χρειάζεται χειριστή, χρειάζεται μηχανικό.
    for _ in range(JOB_SCAN):
        d = e.job_dome
        e.job_dome = (d + 1) % MAX_DOME
        if broken_slot(e, d) is not None:
            kind = J_REPAIR
        elif e.dome[d * DOME_REC + D_OPS] < needs_operators(e, d):
            kind = J_OPERATE
        else:
            continue
        if any(jb[k * JOB_REC + J_KIND] == kind
               and jb[k * JOB_REC + J_NODE] == d for k in range(MAX_JOB)):
            continue
        for k in range(MAX_JOB):
            if jb[k * JOB_REC + J_KIND] == NO_JOB:
                jb[k * JOB_REC + J_KIND] = kind
                jb[k * JOB_REC + J_NODE] = d
                jb[k * JOB_REC + J_AGENT] = 255
                jb[k * JOB_REC + J_PRIO] = JOB_PRIO[kind]
                jb[k * JOB_REC + J_AGE] = 0
                break

    # 4. ανάθεση: ως JOB_ASSIGN, με αύξουσα σειρά ταυτότητας από περιστροφική
    #    αρχή. Ισοπαλία προτεραιότητας σπάει με το DIST (§6.7).
    done = 0
    for step in range(JOB_LOOK):
        i = (e.job_agent + step) & (MAXAGENT_J - 1)
        if done >= JOB_ASSIGN:
            break
        if not (a.flags[i] & F_ALIVE) or (a.flags[i] & F_WORKING):
            continue
        if a.task[i] != NO_TASK:
            continue
        rolebit = 1 << a.role[i]
        best, best_p, best_d = NO_JOB, 0, 255
        for j in range(MAX_JOB):
            b = j * JOB_REC
            k = jb[b + J_KIND]
            if k == NO_JOB or jb[b + J_AGENT] != 255:
                continue
            if not (JOB_ROLES[k] & rolebit):
                continue
            p = jb[b + J_PRIO]
            dist = e.dist[a.node[i] * 128 + jb[b + J_NODE]]
            if p > best_p or (p == best_p and dist < best_d):
                best, best_p, best_d = j, p, dist
        if best == NO_JOB:
            continue
        jb[best * JOB_REC + J_AGENT] = i
        a.task[i] = best
        a.dest[i] = jb[best * JOB_REC + J_NODE]
        done += 1
    e.job_agent = (e.job_agent + JOB_LOOK) & (MAXAGENT_J - 1)


MAXAGENT_J = 128


# --- ευρετήριο δωματίων (θέση 14) -----------------------------------------
# Ενας πεινασμένος άποικος πρέπει να βρει την ΚΟΝΤΙΝΟΤΕΡΗ καντίνα. Σάρωση 64
# θόλων με μία ανάγνωση DIST στον καθένα θα κόστιζε 1.300 us ανά άτομο. Αντί
# γι' αυτό, μία φορά ανά περιστροφή, η ελεύθερη θέση 14 χτίζει λίστες ανά
# είδος δωματίου: ως ROOM_MAX θόλοι ο καθένας, και η αναζήτηση γίνεται οκτώ
# αναγνώσεις.
N_ROOM = 12
ROOM_MAX = 8
R_EMPTY, R_CONTROL, R_QUARTERS, R_CANTEEN, R_OXYGEN, R_GREENHOUSE, \
    R_STORAGE, R_AIRLOCK, R_FACTORY, R_LAB, R_MEDBAY, R_LOUNGE = range(N_ROOM)


def rooms_rebuild(e, plant_class=None):
    """Θέση 14: ποιοι θόλοι είναι τι. 64 εγγραφές, μία φορά ανά περιστροφή.

    Μετράει στο ίδιο πέρασμα και την **παρηγοριά**: σαλόνια και δέντρα. Το
    §6.6 θέλει το ηθικό να ανεβαίνει με ένα δέντρο στο θερμοκήπιο, και αυτό
    είναι το μόνο πέρασμα που κοιτάζει ούτως ή άλλως κάθε θόλο.
    """
    e.room_n = bytearray(N_ROOM)
    e.room_list = bytearray(N_ROOM * ROOM_MAX)
    amenity = 0
    for d in range(MAX_DOME):
        b = d * DOME_REC
        if e.dome[b + D_STATE] != DS_ACTIVE:
            continue
        r = e.dome[b + D_ROOM]
        if r == R_LOUNGE:
            amenity += 1
        elif r == R_GREENHOUSE and plant_class is not None:
            for s in range(MACHINE_COUNT[e.dome[b + D_SIZE]]):
                p = e.dome[b + D_MACH + s]
                if p != NO_MACH and (plant_class[p] & 3) == 3:
                    amenity += 1
        if r >= N_ROOM or e.room_n[r] >= ROOM_MAX:
            continue
        e.room_list[r * ROOM_MAX + e.room_n[r]] = d
        e.room_n[r] += 1
    e.amenity = min(255, amenity)
    # Το ταβάνι πληθυσμού είναι δουλειά του Control (§6.8), και η πλατφόρμα
    # είναι ο κόμβος όπου κατεβαίνει ο κόσμος (§6.11). Και τα δύο βγαίνουν
    # από περάσματα που γίνονται ούτως ή άλλως.
    e.pop_cap = min(MAXAGENT_J, 4 + POP_PER_CONTROL * e.room_n[R_CONTROL])
    e.pad_node = 255
    for i in range(MAX_STRUCT):
        b = i * STRUCT_REC
        if e.struct[b + ST_STATE] == DS_ACTIVE and e.struct[b + ST_KIND] == K_PAD:
            e.pad_node = MAX_DOME + i
            break


def nearest_room(e, room, node):
    """Ο κοντινότερος θόλος αυτού του είδους, ή 255. Ισοπαλία: μικρότερο id."""
    best, best_d = 255, 255
    for k in range(e.room_n[room]):
        d = e.room_list[room * ROOM_MAX + k]
        dist = e.dist[node * 128 + d]
        if dist < best_d:
            best, best_d = d, dist
    return best


# --- πλοία, εμπόριο, ορόσημα (§6.11, §10.2) --------------------------------
SHIP_NONE, SHIP_INCOMING, SHIP_LANDED = 0, 1, 2
SK_COLONIST, SK_MERCHANT, SK_VISITOR = 0, 1, 2
SHIP_TRIP = 24              # περιστροφές ταξιδιού
SHIP_STAY = 8               # πόσο μένει προσγειωμένο
COLONISTS_PER_SHIP = 4
VISITOR_FOOD = 6
VISITOR_MORALE = 24
# Πρώτη εκτίμηση, όπως όλα τα νούμερα ισορροπίας: με 8 ανά Control, μια
# αποικία των ενενήντα δεν χωρούσε ούτε τον εαυτό της και κανένα πλοίο
# αποίκων δεν είχε νόημα.
POP_PER_CONTROL = 48

M_FOOTHOLD, M_INDUSTRY, M_INDEPENDENCE, M_AUTOMATION, M_HABITAT = (
    1, 2, 4, 8, 16)

INDUSTRY_STOCKS = (S_METAL, S_BIOPL, S_SPARE)
# Τα δέκα αγαθά του §6.5. Τα τέσσερα ενδιάμεσα του θερμοκηπίου δεν μετράνε
# για την «ανεξαρτησία»: είναι πρώτη ύλη, όχι προϊόν.
INDEPENDENCE_STOCKS = tuple(range(10))


def call_ship(e, kind):
    """Ο παίκτης καλεί πλοίο από το Control. Ενα τη φορά, και θέλει πίστα."""
    if e.ship_state != SHIP_NONE or e.pad_node == 255:
        return False
    e.ship_state = SHIP_INCOMING
    e.ship_kind = kind
    e.ship_eta = SHIP_TRIP
    return True


def trade(e, give_stock, give_qty, take_stock, take_qty):
    """Ανταλλαγή με τον έμπορο. Επιστρέφει αν έγινε.

    Το εμπόριο είναι πράξη του παίκτη, όχι του τροχού: εδώ υπάρχει ο
    μηχανισμός, και το κουμπί που τον καλεί θα ζήσει στο §9.
    """
    if e.ship_state != SHIP_LANDED or e.ship_kind != SK_MERCHANT:
        return False
    if e.stock[give_stock] < give_qty:
        return False
    e.stock[give_stock] -= give_qty
    add_stock(e, take_stock, take_qty)
    e.traded = 1                        # σπάει το σερί της ανεξαρτησίας
    return True


def ship_tick(e, a, spawn_node, F_ALIVE):
    """Μία περιστροφή του πλοίου. Τρέχει στη θέση 15, μαζί με τα συμβάντα."""
    if e.ship_state == SHIP_NONE:
        return
    if e.ship_eta:
        e.ship_eta -= 1
        return
    if e.ship_state == SHIP_INCOMING:
        e.ship_state = SHIP_LANDED
        e.ship_eta = SHIP_STAY
        if e.ship_kind == SK_COLONIST:
            land_colonists(e, a, spawn_node, F_ALIVE)
        elif e.ship_kind == SK_VISITOR:
            visit(e, a, F_ALIVE)
        return
    e.ship_state = SHIP_NONE            # έφυγε


def land_colonists(e, a, node, F_ALIVE):
    """Καινούργιοι άποικοι στην πλατφόρμα. Οσοι χωράνε στο ταβάνι."""
    n = 0
    for i in range(MAXAGENT_J):
        if n >= COLONISTS_PER_SHIP or e.alive + n >= e.pop_cap:
            break
        if a.flags[i] & F_ALIVE:
            continue
        a.flags[i] = F_ALIVE
        a.role[i] = i & 7
        a.node[i] = node
        a.dest[i] = node
        a.edge[i] = 255
        a.slot[i] = 255
        a.task[i] = 255
        a.progress[i] = 0
        a.o2[i] = 200
        a.water[i] = 200
        a.food[i] = 200
        a.sleep[i] = 200
        a.health[i] = 200
        a.morale[i] = 160
        n += 1
    e.alive += n
    return n


def visit(e, a, F_ALIVE):
    """Επισκέπτες: τρώνε και ανεβάζουν το ηθικό. Ενοχλητικοί όταν πεινάς."""
    take = min(VISITOR_FOOD, e.stock[S_FOOD])
    e.stock[S_FOOD] -= take
    for i in range(MAXAGENT_J):
        if a.flags[i] & F_ALIVE:
            a.morale[i] = min(255, a.morale[i] + VISITOR_MORALE)


def sol_rollover(e, a, F_ALIVE, F_WORKING, NEED_LOW):
    """Μία φορά ανά sol: τα σερί, και μετά τα ορόσημα (§10.2).

    Ολα τα μετρήματα γίνονται ΕΔΩ και όχι μέσα στα καυτά περάσματα: μία
    σάρωση 128 πρακτόρων ανά 750 περιστροφές δεν φαίνεται πουθενά.
    """
    # «Ολες οι ανάγκες πράσινες» είναι η ένδειξη της ΑΠΟΙΚΙΑΣ, όχι η μπάρα
    # κάθε ατόμου: με ενενήντα αποίκους κάποιος είναι πάντα καθ' οδόν προς
    # την καντίνα, και ένα ορόσημο που δεν πιάνεται ποτέ δεν είναι ορόσημο.
    green = bool(e.o2_ok and e.power_ok
                 and e.stock[S_WATER] and e.stock[S_FOOD])
    bots = 0
    for i in range(MAXAGENT_J):
        if a.flags[i] & F_ALIVE and a.role[i] >= 5 and (a.flags[i] & F_WORKING):
            bots += 1

    e.green_sols = e.green_sols + 1 if green else 0
    e.no_death_sols = 0 if e.deaths_sol else min(255, e.no_death_sols + 1)
    e.deaths_sol = 0
    e.no_trade_sols = 0 if e.traded else min(255, e.no_trade_sols + 1)
    e.traded = 0

    m = e.milestones
    if e.alive >= 10 and e.green_sols >= 1:
        m |= M_FOOTHOLD
    if all(e.prod_mask & (1 << s) for s in INDUSTRY_STOCKS):
        m |= M_INDUSTRY
    if all(e.prod_mask & (1 << s) for s in INDEPENDENCE_STOCKS) \
       and e.no_trade_sols >= 5:
        m |= M_INDEPENDENCE
    if bots >= 8:
        m |= M_AUTOMATION
    if e.alive >= 80 and (m & M_INDEPENDENCE) and e.no_death_sols >= 5:
        m |= M_HABITAT
    e.milestones = m
