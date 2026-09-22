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
        "robots", "food", "spares", "medical", "vitromeat"]
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
]

# --- θόλοι ----------------------------------------------------------------
DOME_REC = 24
MAX_DOME = 64
MACH_SLOTS = 8
MACHINE_COUNT = [1, 4, 8]           # ανά μέγεθος s/m/l — από τα assets

D_CX, D_CY, D_SIZE, D_ROOM, D_STATE, D_INTEG, D_POWER, D_OPS = range(8)
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


def run_dome(e, d):
    """Μία επίσκεψη σε έναν θόλο: όσες μηχανές του μπορούν, τρέχουν."""
    base = d * DOME_REC
    if e.dome[base + D_STATE] != DS_ACTIVE:
        return
    n = MACHINE_COUNT[e.dome[base + D_SIZE]]
    ops = e.dome[base + D_OPS]
    for s in range(n):
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
        else:
            add_stock(e, r[6], r[7])


def production_slice(e, count=PROD_DOMES):
    """Θέση 11: PROD_DOMES θόλοι. Στο τέλος του σαρώματος δημοσιεύει."""
    for _ in range(count):
        run_dome(e, e.prod_dome)
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
            if e.day:
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

    e.o2_use = alive * O2_PER_COLONIST
    e.o2_ok = 1 if e.o2_prod >= e.o2_use else 0


def events(e):
    """Θέση 15: μία ζαριά. Ρολόι, μέρα/νύχτα, άνεμος."""
    e.frame += 16                           # μία περιστροφή
    if e.frame >= SOL_FRAMES:
        e.frame -= SOL_FRAMES
        e.sol = (e.sol + 1) & 0xFF
    e.day = 1 if e.frame < DAY_FRAMES else 0
    e.rnd = lfsr(e.rnd)
    if (e.rnd & 15) == 0:                   # ο άνεμος αλλάζει σπάνια
        e.wind = (e.rnd >> 4) & 3


def to_bytes(e):
    """Η οικονομία όπως κάθεται στη μνήμη, για σύγκριση με τον Z80."""
    out = bytearray()
    for v in e.stock:
        out += int(v).to_bytes(2, "little")
    for v in (e.power_store, e.power_cap, e.power_prod, e.power_use,
              e.mach_power, e.o2_prod, e.o2_use, e.acc_power, e.acc_o2):
        out += int(v).to_bytes(2, "little")
    out += bytes([e.power_ok, e.o2_ok, e.prod_dome, e.day, e.wind, e.sol])
    out += int(e.frame).to_bytes(2, "little")
    out += int(e.rnd).to_bytes(2, "little")
    return bytes(out)


ECON_BYTES = N_STOCK * 2 + 9 * 2 + 6 + 2 + 2        # 28 + 18 + 10 = 56


def populate(e, n_dome=24, n_struct=20, seed=11):
    """Μια αποικία που όντως δουλεύει: παραγωγοί ρεύματος, αντλίες, ορυχείο,
    και θόλοι με μηχανές που έχουν πού να τραβήξουν. Ντετερμινιστική."""
    x = seed
    def rnd():
        nonlocal x
        x = ((x * 75) + 74) & 0xFFFF
        return x

    # λίγο απόθεμα για να ξεκινήσει η αλυσίδα
    for s, q in ((S_WATER, 200), (S_ORE, 300), (S_STARCH, 150),
                 (S_VEG, 120), (S_MEDPLANT, 90)):
        e.stock[s] = q

    kinds = [K_SOLAR, K_SOLAR, K_TURBINE, K_COLLECTOR, K_EXTRACTOR, K_MINE]
    for i in range(n_struct):
        b = i * STRUCT_REC
        k = kinds[i % len(kinds)]
        e.struct[b + ST_KIND] = k
        e.struct[b + ST_SIZE] = 0 if k in (K_MINE,) else (rnd() >> 3) % 3
        e.struct[b + ST_STATE] = DS_ACTIVE
        e.struct[b + ST_INTEG] = 255
    e.n_struct = n_struct

    # Δύο μικροί θόλοι με γεννήτρια οξυγόνου, εγγυημένα: το machine_rules
    # επιτρέπει το mach_oxygen μόνο σε μικρούς, και χωρίς αυτούς ο κλάδος της
    # ΡΟΗΣ (MF_FLOW) δεν δοκιμάζεται ποτέ.
    forced = {0: (0, 0), 1: (0, 0)}
    for d in range(n_dome):
        b = d * DOME_REC
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
        for s in range(n):
            r = rnd() >> 5
            if r % 5 == 0:
                continue                                 # άδεια υποδοχή
            m = r % N_MACH
            if m == 0 and size != 0:                     # machine_rules: bit0
                m = 1                                    # οξυγόνο μόνο σε μικρό
            e.dome[b + D_MACH + s] = m
            e.dome[b + D_HEALTH + s] = 0 if (r % 17) == 0 else 200
    e.n_dome = n_dome
    return e
