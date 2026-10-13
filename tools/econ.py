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
    # ΔΥΟ ΜΕΤΑΛΛΑ ΑΠΟ ΔΥΟ ΜΕΤΑΛΛΕΥΜΑΤΑ (βήμα 125), όχι ένα: με 1 καμία αποικία
    # των έξι δεν μεγάλωνε σε 40 sol — η μηχανή περιμένει χειριστή, και το
    # μετάλλευμα στη φλέβα έφτανε τα 140 με το μέταλλο κάτω από 25. Με 2 τρεις
    # από τους δώδεκα κόσμους του tools/play.py φτάνουν τους 18-20 (DESIGN §10.1).
    # Δεν προσθέτει στην αποθήκη (2 -> 2, όχι MF_ADDS): δουλεύει και γεμάτη.
    (S_ORE, 2, NO_STOCK, 0, NO_STOCK, 0, S_METAL, 2, 3, MF_OPERATOR),   # iron
    (S_STARCH, 2, NO_STOCK, 0, NO_STOCK, 0, S_BIOPL, 1, 3, MF_OPERATOR),
    (S_METAL, 2, S_PROC, 1, NO_STOCK, 0, S_GUN, 1, 5, MF_OPERATOR),     # weapons
    (S_METAL, 2, NO_STOCK, 0, NO_STOCK, 0, S_PROC, 1, 5, MF_OPERATOR),
    (S_METAL, 2, S_PROC, 1, S_BIOPL, 1, S_BOT, 1, 8, MF_OPERATOR),      # robots
    (S_STARCH, 1, S_VEG, 1, S_MEAT, 1, S_FOOD, 1, 4, MF_OPERATOR),      # food
    (S_METAL, 1, S_BIOPL, 1, NO_STOCK, 0, S_SPARE, 1, 3, MF_OPERATOR),
    (S_MEDPLANT, 2, NO_STOCK, 0, NO_STOCK, 0, S_MEDI, 1, 3, MF_OPERATOR),
    # ΔΥΟ ΚΡΕΑΤΑ ΑΝΑ ΓΥΡΟ, όχι ένα: το mach_food θέλει άμυλο ΚΑΙ λαχανικά ΚΑΙ
    # κρέας, τα φυτά δίνουν 3 και 2 ανά γύρο, και το κρέας έδινε 1 — δηλαδή η
    # αλυσίδα ήταν 1:1 πάνω στο πιο εύθραυστο σκέλος της. Μετρημένο: ένα
    # στελεχωμένο εργαστήριο βγάζει 6-7 το sol (ο χειριστής τρώει και κοιμάται
    # κι αυτός), άρα με 1 ανά γύρο το κυλικείο μαγείρευε μόνο όταν συνέπιπταν
    # οι δύο μηχανές — και η τροφή έπεφτε με τέσσερις αποίκους.
    (S_WATER, 2, NO_STOCK, 0, NO_STOCK, 0, S_MEAT, 2, 4, MF_OPERATOR),  # vitromeat
    # Τα δύο του ιατρείου δεν ΠΑΡΑΓΟΥΝ: είναι έπιπλα που κάνουν το δωμάτιο να
    # δουλεύει. Τα κρεβάτια θέλουν γιατρό από πάνω τους, η φαρμακαποθήκη όχι.
    # Παραμένουν εγγραφές συνταγής ώστε το πέρασμα παραγωγής να μην ξέρει από
    # ειδικές περιπτώσεις.
    (NO_STOCK, 0, NO_STOCK, 0, NO_STOCK, 0, NO_STOCK, 0, 1, MF_OPERATOR),
    (NO_STOCK, 0, NO_STOCK, 0, NO_STOCK, 0, NO_STOCK, 0, 0, 0),
]

# ΠΡΟΣΘΕΤΕΙ ΣΤΗΝ ΑΠΟΘΗΚΗ (βήμα 124): βγάζει απόθεμα που μετρά (όχι νερό) σε
# περισσότερες μονάδες απ' όσες τρώει από τα μετρημένα. Μόνο αυτή σταματά με
# γεμάτη αποθήκη (src/econ.asm, erm_inf)· σήμερα μόνο το VITROMEAT (2 νερό ->
# 2 κρέας). Υπολογίζεται εδώ, και το pack.py το γράφει στη συνταγή.
MF_ADDS = 4


def _adds(r):
    used = sum(q for st, q in ((r[0], r[1]), (r[2], r[3]), (r[4], r[5]))
               if st not in (NO_STOCK, S_WATER))
    return r[6] not in (NO_STOCK, S_WATER) and r[7] > used


RECIPE = [r[:9] + (r[9] | (MF_ADDS if _adds(r) else 0),) for r in RECIPE]

# ΤΟ ΑΠΟΘΕΜΑ ΜΕΤΑΛΛΟΥ (βήμα 127, src/econ.asm, erm_ink): όσες τρώνε μέταλλο
# σταματούν όταν πέσει κάτω από KEEP_METAL. Ο Z80 κοιτάζει μόνο την ΠΡΩΤΗ
# είσοδο, οπότε όποια το τρώει πρέπει να το έχει πρώτο.
KEEP_METAL = 30
assert all(r[0] == S_METAL for r in RECIPE
           if S_METAL in (r[0], r[2], r[4])), "το μέταλλο όχι πρώτη είσοδος"

# --- θόλοι ----------------------------------------------------------------
DOME_REC = 24
MAX_DOME = 64
MACH_SLOTS = 8
# Η ΥΓΕΙΑ ΜΙΑΣ ΥΠΟΔΟΧΗΣ (βήμα 99, src/install.asm): 0 σταματημένη ή άδεια,
# MACH_HP δουλεύει (bit 7), και ό,τι είναι από κάτω περιμένει: MACH_OWED
# χρωστά μέταλλο (bit 0) και βιοπλαστικό (bit 1), MACH_READY + 32k περιμένει
# τον χτίστη. Η παραγωγή, ο χειριστής και η βλάβη κοιτάζουν μόνο το bit 7.
MACH_HP, MACH_OWED, MACH_READY = 200, 7, 4
MACHINE_COUNT = [1, 4, 8]           # ανά μέγεθος s/m/l — από τα assets

D_CX, D_CY, D_SIZE, D_ROOM, D_STATE, D_INTEG, D_POWER, D_OPS = range(8)
N_ROOM_F = 12               # είδη δωματίων — βλ. rooms_rebuild
D_MACH = 8                          # 8 bytes
D_HEALTH = 16                       # 8 bytes

DS_EMPTY, DS_BUILDING, DS_ACTIVE = 0, 1, 2

# --- δομές ----------------------------------------------------------------
STRUCT_REC = 8
MAX_STRUCT = 32          # §4.2: 64 θόλοι + 32 δομές = 96 κόμβοι
# Το έβδομο byte είναι το ST_JOINED των airlock (βήμα 87)· το όγδοο, από το
# βήμα 88, ό,τι χρωστιέται σε ένα εργοτάξιο: μέταλλο<<4 | βιοπλαστικό.
ST_CX, ST_CY, ST_KIND, ST_SIZE, ST_STATE, ST_INTEG, ST_OUT, ST_OWED = range(8)
ST_OPS = ST_OUT                 # ορυχείο: όσοι σκάβουν (βήμα 94, src/drill.asm)

# είδη δομών, με τη σειρά του STRUCTS στο pack.py (solar/turbine/collector/
# extractor σε τρία μεγέθη, μετά mine/airlock/pad/ship)
K_SOLAR, K_TURBINE, K_COLLECTOR, K_EXTRACTOR, K_MINE, K_AIRLOCK, K_PAD, K_SHIP \
    = range(8)

SOLAR_OUT = [2, 8, 18]              # §6.5, ανά μέγεθος
TURBINE_OUT = [3, 12, 27]
COLLECTOR_CAP = [40, 160, 360]
EXTRACTOR_OUT = [1, 2, 5]      # ανά κύκλο ροής — δες FLOW_DIV
EXTRACTOR_POWER = [1, 3, 6]     # ένα τρίτο πάνελ, όχι δύο — βλ. src/econ.asm
MINE_OUT, MINE_POWER = 2, 8         # MINE_OUT: με ΕΝΑΝ που σκάβει (βήμα 94)
MINE_OPS = 3                        # ως τρεις σε κάθε ορυχείο, όπως το Planetbase
# Η ΜΕΤΑΦΟΡΑ (βήμα 95, src/haul.asm): το μετάλλευμα μένει σε σωρό στο ορυχείο
# (ST_OWED), ως HAUL_CAP, και το κουβαλούν φορτία των HAUL_LOAD. Το bit ST_HAUL
# του ST_OPS λέει ότι η Haul του υπάρχει (το 0x80 είναι της Drill).
HAUL_LOAD, HAUL_CAP = 10, 30
ST_HAUL = 0x40
ST_HALF, ST_FREE = 0x04, 0x08     # το ST_OPS ενός ορυχείου (βήμα 123): εκτός φλέβας, δωρεάν
# Η DRILL ΤΟΥ ΔΕΥΤΕΡΟΥ ΚΑΙ ΤΟΥ ΤΡΙΤΟΥ ΚΑΤΩ ΑΠΟ ΤΙΣ ΜΗΧΑΝΕΣ (βήμα 126, src/drill.asm):
# με κάποιον ήδη να σκάβει δημοσιεύεται με DRILL_LOW και το ST_DLOW· άδειο το
# ορυχείο πριν έρθει ο επόμενος, ο κύκλος ροής την ξαναπηγαίνει στο DRILL_PRIO.
ST_DLOW = 0x10
DRILL_PRIO, DRILL_LOW = 4, 2

O2_PER_COLONIST = 2
CW_N = 5                            # οι ειδικότητες των πλοίων αποίκων (βήμα 91)


class Econ:
    """Ο,τι κρατά η οικονομία ανάμεσα σε δύο frames."""

    def __init__(self):
        self.prod_div = 1               # §6.5: το ρολόι της οικονομίας
        self.flow_div = 1
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
        self.power_ok = POWER_ALL           # το buffer που διαβάζει η παραγωγή
        self.o2_ok = 1
        # συσσωρευτές του τρέχοντος σαρώματος παραγωγής
        self.acc_power = 0
        # Η ΖΗΤΗΣΗ ΤΗΣ ΥΠΟΣΤΗΡΙΞΗΣ ΖΩΗΣ ΞΕΧΩΡΙΣΤΑ (§6.5). Μόνο οι μηχανές
        # MF_FLOW — δηλαδή το οξυγόνο — μπαίνουν εδώ, και μόνο αυτές συνεχίζουν
        # να τρέχουν όταν το ρεύμα δεν φτάνει για όλους.
        self.ess_power = 0
        self.acc_ess = 0
        # Η βροχή μετεωριτών (§6.10, src/meteor.asm): κρούσεις που μένουν,
        # κέντρο σε tiles, και η δική της γεννήτρια.
        self.meteor = 0
        self.mcx = 0
        self.mcy = 0
        self.mrnd = 0
        self.nbuild = 0                 # EC_NBUILD: Build στον πίνακα (βήμα 88)
        # EC_LAND (βήμα 91): το ποσοστό κάθε ειδικότητας στα πλοία αποίκων, σε
        # δέκατα — εργάτης, μηχανικός, βιολόγος, γιατρός, φρουρός. Αθροισμα 10.
        self.land = [2] * CW_N
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
        # Η ΗΣΥΧΙΑ (βήμα 121): πότε άρχισε η τελευταία καταστροφή και πότε
        # έγινε το τελευταίο γεγονός, [sol, frame] — [0, 0] είναι «ποτέ». Στα
        # άδεια του node_occ στον Z80 (EC_X, src/const.asm), όχι στην
        # οικονομία — βλ. x_bytes.
        self.ldis = [0, 0]
        self.lev = [0, 0]
        # ΓΕΜΑΤΗ ΑΠΟΘΗΚΗ (βήμα 122): το ec_full του Z80, στην τράπεζα 0 (src/stock.asm).
        self.full = 0
        # ΤΟ ΑΠΟΘΕΜΑ ΜΕΤΑΛΛΟΥ (βήμα 127): το ec_keep, δίπλα του.
        self.keep = 0
        self.amenity = 0            # δέντρα και σαλόνια — παρηγοριά (§6.6)
        # Το μήκος του sol είναι ΔΕΔΟΜΕΝΟ και όχι σταθερά: μια δοκιμή που
        # θέλει να δει πέντε sols δεν μπορεί να περιμένει 60.000 frames.
        self.sollen = SOL_FRAMES
        self.daylen = DAY_FRAMES
        # --- πλοία (§6.11) ---
        self.ship_state = 0         # 0 κανένα · 1 έρχεται · 2 προσγειωμένο
        self.ship_kind = 0          # 0 άποικοι · 1 έμπορος · 2 επισκέπτες
        self.ship_eta = 0           # περιστροφές ως την άφιξη
        self.pop_cap = POP_BASE     # το Control ανεβάζει το ταβάνι
        self.pad_node = 255         # η πλατφόρμα προσγείωσης, ως κόμβος
        # --- ορόσημα (§10.2) ---
        self.prod_mask = 0          # ποια αποθέματα φτιάχτηκαν ΕΔΩ
        self.milestones = 0
        self.deaths_sol = 0
        self.no_death_sols = 0
        self.green_sols = 0
        self.no_trade_sols = 0
        self.traded = 0
        # --- ο έμπορος (βήμα 93) — όσο είναι προσγειωμένος ---
        self.markup = 0             # το κέρδος του, 35-65 (%)
        self.cargo = [0] * (2 * MER_SLOTS)  # [αγαθό, ποσότητα] x 4· αγαθό 0: κενό
        self.mines = 0              # έτοιμα ορυχεία, από τον κύκλο ροής (βήμα 94)
        self.lands = 0              # EC_LANDS: προσγειώσεις από τους τελευταίους εισβολείς (βήμα 111)
        self.air_out = 255          # airlock που ξανάγινε εργοτάξιο (βήμα 90)
        # jb_lost (βήμα 115, src/supply.asm): μια εργασία εργοταξίου δεν χώρεσε.
        # Το σηκώνει και κάθε φόρτωση (wheel_load), όχι το νέο παιχνίδι.
        self.lost = False
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
# Το ρολόι της οικονομίας: μία παραγωγή (και μία άντληση) ανά 16 περιστροφές.
# Βλ. src/econ.asm και §6.5 — οι ρυθμοί έτρεχαν 750 φορές το sol ενώ ο πίνακας
# τους έγραφε ΑΝΑ SOL, και η αρχική αποικία πέθαινε σε ενάμιση sol.
ECON_DIV = 16
# Και ο κύκλος της ροής: τέσσερις επισκέψεις παραγωγής χρειάζονται για να δουν
# και τους 64 θόλους, άρα μια μηχανή τρέχει ανά 64 περιστροφές. Η μπαταρία και
# οι αντλίες πατάνε στον ίδιο κύκλο — βλ. src/econ.asm.
FLOW_DIV = ECON_DIV * 4

# ΤΡΕΙΣ ΣΤΑΘΜΕΣ ΡΕΥΜΑΤΟΣ, ΟΧΙ ΔΥΟ (§6.5: «machines stop, THEN oxygen stops»).
# Ως το βήμα 32 το power_ok ήταν μία σημαία για ολόκληρη την αποικία: στο
# μπλακάουτ σταματούσε ΚΑΙ η γεννήτρια οξυγόνου, οπότε μια δεύτερη αντλία —
# που είναι η σωστή απάντηση στο νερό — αγόραζε το νερό με το οξυγόνο κάθε
# νύχτα. Μετρημένο: 13 στα 80 δείγματα χωρίς ρεύμα, O2 παραγωγή 20 -> 0.
POWER_NONE, POWER_ALL, POWER_ESS = 0, 1, 2
# Πόσους κύκλους ροής κρατά η ρεζέρβα της μπαταρίας για την υποστήριξη ζωής.
# Οκτώ, επειδή η νύχτα είναι το 40% ενός sol και ένας κύκλος είναι 1/11,7 του
# sol: 4,7 κύκλοι νύχτα, και οκτώ αφήνουν περιθώριο για αμμοθύελλα.
RESERVE_SH = 3                          # src/econ.asm: ρεζέρβα = ζήτηση << 3
RESERVE_CYCLES = 1 << RESERVE_SH


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
    e.acc_power += PLANT_POWER          # ζητάει, είτε το πάρει είτε όχι
    if e.power_ok != POWER_ALL:         # ο κήπος δεν είναι υποστήριξη ζωής
        return
    e.stock[S_WATER] -= PLANT_WATER
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
    k = 0                                       # μηχανές με χειριστή ως εδώ
    for s in range(n):
        if green:
            p = e.dome[base + D_MACH + s]
            if p == NO_MACH or not e.dome[base + D_HEALTH + s] & 0x80:
                continue
            if not ops:                         # ΕΝΑΣ βιολόγος ποτίζει όλο
                continue                        # τον κήπο (βλ. src/econ.asm)
            if e.full:                          # γεμάτη αποθήκη (βήμα 122)
                continue
            run_plant(e, base, s, p, plant_class)
            continue
        m = e.dome[base + D_MACH + s]
        if m == NO_MACH:
            continue
        if not e.dome[base + D_HEALTH + s] & 0x80:  # χαλασμένη, ή δεν στήθηκε
            continue
        r = RECIPE[m]
        if r[9] & MF_OPERATOR:
            # Η k-οστή που θέλει χειριστή τρέχει αν ο θόλος έχει k, όποια
            # υποδοχή κι αν πιάνει (βήμα 45· ως τότε s >= ops, src/econ.asm).
            k += 1
            if k > ops:
                continue
        if e.keep and r[0] == S_METAL:              # βήμα 127: το μέταλλο κάτω από
            continue                                # KEEP_METAL, ούτε τρώει ούτε ζητά
        ins = ((r[0], r[1]), (r[2], r[3]), (r[4], r[5]))
        if any(st != NO_STOCK and e.stock[st] < q for st, q in ins):
            continue                                # λείπει είσοδος: δεν καίει
        if e.full and r[9] & MF_ADDS:               # γεμάτη αποθήκη (βήμα 122): ό,τι
            continue                                # προσθέτει (βήμα 124) ούτε τρώει
                                                    # ούτε ζητά ρεύμα
        # Το ρεύμα μετράει ως ΖΗΤΗΣΗ: όσα θα έτρεχαν αν υπήρχε. Με «όσα κάηκαν»
        # το μπλακάουτ μηδένιζε τη ζήτηση και το ρεύμα ξαναγύριζε μόνο του.
        e.acc_power += r[8]
        if r[9] & MF_FLOW:
            e.acc_ess += r[8]                       # υποστήριξη ζωής
        if e.power_ok != POWER_ALL:
            # POWER_NONE: τίποτα. POWER_ESS: μόνο η υποστήριξη ζωής (§6.5 —
            # «machines stop, THEN oxygen stops»).
            if e.power_ok == POWER_NONE or not (r[9] & MF_FLOW):
                continue
        for st, q in ins:
            if st != NO_STOCK:
                e.stock[st] -= q
        if r[9] & MF_FLOW:
            e.acc_o2 += r[7]
        elif r[6] != NO_STOCK:              # τα κρεβάτια δεν παράγουν τίποτα
            add_stock(e, r[6], r[7])
            e.prod_mask |= 1 << r[6]        # φτιάχτηκε ΕΔΩ (§10.2)


def production_slice(e, count=PROD_DOMES, plant_class=None):
    """Θέση 11: PROD_DOMES θόλοι. Στο τέλος του σαρώματος δημοσιεύει."""
    e.prod_div -= 1
    if e.prod_div:
        return
    e.prod_div = ECON_DIV

    for _ in range(count):
        run_dome(e, e.prod_dome, plant_class)
        e.prod_dome += 1
        if e.prod_dome >= MAX_DOME:
            e.prod_dome = 0
            e.mach_power = e.acc_power      # ό,τι τράβηξαν οι μηχανές
            e.ess_power = e.acc_ess
            e.o2_prod = e.acc_o2
            e.acc_power = 0
            e.acc_ess = 0
            e.acc_o2 = 0


def flow_balance(e, alive, inside):
    """Θέση 12: παραγωγή απέναντι σε κατανάλωση, και η μπαταρία. `inside` =
    οι ζωντανοί με F_INDOORS: μόνο αυτοί αναπνέουν τον αέρα της αποικίας
    (βήμα 87)· οι άλλοι είναι στη στολή."""
    e.flow_div -= 1
    if e.flow_div == 0:
        e.flow_div = FLOW_DIV
        flow_cycle(e)
    # Η μέτρηση ζωντανών είναι η συνθήκη ήττας (§10.3): κάθε περιστροφή.
    e.o2_use = inside * O2_PER_COLONIST
    e.o2_ok = 1 if e.o2_prod >= e.o2_use else 0
    e.alive = alive
    if alive == 0:
        e.gameover = 1


def flow_cycle(e):
    store_check(e)                      # η αποθήκη (βήμα 122): πριν σκάψουν τα ορυχεία
    prod = cap = water = 0
    use = e.mach_power
    e.mines = 0
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
            # ΣΚΑΒΕΙ ΟΠΟΙΟΣ ΕΙΝΑΙ ΕΚΕΙ (βήμα 94, src/flow.asm και src/drill.asm),
            # και όσο λείπει κάποιος, μια εργασία Drill, εδώ στο σάρωμα
            # (dr_post). Το ρεύμα το τρώει ούτως ή άλλως. Το μετάλλευμα πάει
            # στον σωρό, με το ρεύμα του τελευταίου ισοζυγίου (haul_pile, βήμα 95).
            use += MINE_POWER
            e.mines += 1
            n = e.struct[st + ST_OPS] & (0x83 | ST_DLOW)   # όχι το ST_HAUL
            # το bit 7: η Drill του υπάρχει ήδη, ως να φτάσει κάποιος (dr_post)
            if n < MINE_OPS:
                low = n & MINE_OPS                  # βήμα 126: κάποιος ήδη σκάβει
                if post_drill(e, MAX_DOME + i, DRILL_LOW if low else DRILL_PRIO):
                    e.struct[st + ST_OPS] |= 0x80 | (ST_DLOW if low else 0)
            elif n == 0x80 | ST_DLOW:               # άδειο, η Drill χαμηλά (dr_raise)
                raise_drill(e, i)
            haul_pile(e, i)
    if e.lost:                              # βήμα 115: src/repost.asm
        sweep(e)

    e.power_prod, e.power_cap, e.power_use = prod, cap, use
    if prod >= use:
        e.power_store = min(e.power_store + prod - use, cap)
        e.power_ok = POWER_ALL
    elif e.power_store >= (use - prod) + e.ess_power * RESERVE_CYCLES:
        # ΜΕ ΡΕΖΕΡΒΑ, ΟΧΙ ΩΣ ΤΗΝ ΤΕΛΕΥΤΑΙΑ ΜΟΝΑΔΑ. Η μπαταρία δανείζεται στις
        # μηχανές μόνο όσο μένει πίσω ό,τι χρειάζεται η υποστήριξη ζωής για
        # οκτώ κύκλους — δηλαδή για μια νύχτα. Χωρίς αυτό η σειρά «πρώτα οι
        # μηχανές, μετά το οξυγόνο» δεν σημαίνει τίποτα: οι μηχανές αδειάζουν
        # τη μπαταρία στους δύο πρώτους κύκλους της νύχτας και το οξυγόνο
        # σβήνει ούτως ή άλλως.
        e.power_store -= use - prod
        e.power_ok = POWER_ALL
    elif prod >= e.ess_power:
        # Ρίχνει φορτίο: αντλίες, ορυχεία, εργοστάσια, κήποι σταματούν και το
        # περίσσευμα φορτίζει.
        e.power_store = min(e.power_store + prod - e.ess_power, cap)
        e.power_ok = POWER_ESS
    elif e.power_store >= e.ess_power - prod:
        e.power_store -= e.ess_power - prod
        e.power_ok = POWER_ESS
    else:
        e.power_store = 0
        e.power_ok = POWER_NONE

    if e.power_ok == POWER_ALL:             # οι αντλίες θέλουν ρεύμα
        add_stock(e, S_WATER, water)
        # Το νερό βγαίνει από ΔΟΜΕΣ, όχι από μηχανές θόλου, αλλά βγαίνει εδώ —
        # και το §10.2 το θέλει. Το μετάλλευμα από το βήμα 95 στην παράδοση.
        if water:
            e.prod_mask |= 1 << S_WATER


def mine_rate(n, half=False):
    """Μετάλλευμα ανά κύκλο με n που σκάβουν (βήμα 94): 0, 2, 3, 4. Εκτός
    φλέβας (βήμα 123) τα μισά, προς τα πάνω: 0, 1, 2, 2."""
    r = MINE_OUT + n - 1 if n else 0
    return (r + 1) >> 1 if half else r


def haul_pile(e, i):
    """Το hl_pile (βήμα 95, src/haul.asm), στο σάρωμα, για το έτοιμο ορυχείο
    i: με όλο το ρεύμα ΤΟΥ ΤΕΛΕΥΤΑΙΟΥ ΙΣΟΖΥΓΙΟΥ (όπως οι μηχανές της θέσης 11)
    ο σωρός παίρνει τον ρυθμό του, ως HAUL_CAP· και με ή χωρίς, ένας σωρός
    από HAUL_LOAD χωρίς Haul παίρνει μία."""
    st = i * STRUCT_REC
    if e.power_ok == POWER_ALL and not e.full:      # βήμα 122: ούτε γεμάτη αποθήκη
        ops = e.struct[st + ST_OPS]
        r = mine_rate(ops & MINE_OPS, ops & ST_HALF)
        if r:
            e.struct[st + ST_OWED] = min(HAUL_CAP, e.struct[st + ST_OWED] + r)
    if e.struct[st + ST_OWED] >= HAUL_LOAD and not e.struct[st + ST_OPS] & ST_HAUL:
        if post_job(e, J_HAUL, MAX_DOME + i):
            e.struct[st + ST_OPS] |= ST_HAUL


STORM_LEN = 32          # περιστροφές — περίπου δέκα δευτερόλεπτα
# ΟΙ ΚΑΤΑΣΤΡΟΦΕΣ ΑΡΑΙΕΣ (βήμα 121, η απόφαση του χρήστη): θύελλα, έκλαμψη και
# βροχή μετεωριτών μόνο με DIS_POP ζωντανούς, και ποτέ μέσα σε CALM_REVS
# περιστροφές (δύο sol) από την προηγούμενη· οι βλάβες είναι φθορά, από την
# αρχή, με FAULT_GAP περιστροφές ανάμεσα — και ανάμεσα σε βλάβη και καταστροφή.
DIS_POP, FAULT_GAP = 20, 64
# Η ΧΩΡΗΤΙΚΟΤΗΤΑ ΤΩΝ ΑΠΟΘΗΚΩΝ (βήμα 122): συνολική, όλα τα αγαθά εκτός από το
# νερό, κάτω από το αμπάρι του σκάφους και τους θόλους Storage κατά μέγεθος.
STORE_BASE, STORE_SIZE = 500, (100, 300, 600)


def store_check(e):
    """st_check (src/needs.asm): στην αρχή κάθε κύκλου ροής, πόσα
    χωράνε — το αμπάρι και ως ROOM_MAX θόλοι Storage — και αν χωρά άλλο."""
    cap = STORE_BASE
    for k in range(e.room_n[R_STORAGE]):
        d = e.room_list[R_STORAGE * ROOM_MAX + k]
        cap += STORE_SIZE[e.dome[d * DOME_REC + D_SIZE]]
    e.full = 1 if sum(e.stock[1:]) >= cap else 0
    e.keep = 1 if e.stock[S_METAL] < KEEP_METAL else 0     # βήμα 127


def break_one(e, x):
    """Μια μηχανή σταματά. Οχι «χαλάει λίγο»: υγεία μηδέν, και μένει εκεί ως
    να έρθει μηχανικός με ένα ανταλλακτικό (§6.7 Repair)."""
    d = x % MAX_DOME
    b = d * DOME_REC
    if e.dome[b + D_STATE] != DS_ACTIVE:
        return
    n = MACHINE_COUNT[e.dome[b + D_SIZE]]
    s = (x >> 6) % n
    # Μόνο μία που δουλεύει: μια που περιμένει υλικά ή χτίστη (βήμα 99) δεν
    # χάνει όσα της έφεραν, και μια άδεια υποδοχή έχει υγεία 0.
    if not e.dome[b + D_HEALTH + s] & 0x80:
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

    # ΟΙ ΤΡΕΙΣ ΣΥΧΝΟΤΗΤΕΣ ΕΙΝΑΙ ΜΕΤΡΗΜΕΝΕΣ, ΟΧΙ ΕΙΚΑΣΜΕΝΕΣ (tools/balance.py):
    # η θύελλα ήταν 1/128 ανά περιστροφή επί 32 περιστροφές = ένα τέταρτο του
    # sol χωρίς ήλιο· η βλάβη 1/32, δηλαδή η μηχανή οξυγόνου της αρχικής
    # αποικίας σταματούσε κάθε 1,3 sol και τα τέσσερα ανταλλακτικά του §10.1
    # τελείωναν σε τρία sols — μετά την πρώτη βλάβη χωρίς ανταλλακτικό,
    # ασφυξία. Και η έκλαμψη 1/256, δηλαδή τρεις φορές το sol.
    # Η ΗΣΥΧΙΑ (βήμα 121, src/econ.asm): καμία καταστροφή με λιγότερους από
    # DIS_POP ζωντανούς, μέσα σε δύο sol από την προηγούμενη, ή μέσα σε
    # FAULT_GAP περιστροφές από οποιοδήποτε γεγονός (may) — ρωτημένα μόνο
    # αφού πέσει η ζαριά.
    if e.storm:                             # αμμοθύελλα: τα πάνελ σκεπάζονται
        e.storm -= 1
    elif r2 >= 0xFFE0 and may(e):           # 1/2048· όχι r2 < 32 (βήμα 124): ένα μικρό
                                            # r2 έρχεται πάντα αμέσως μετά από ζαριά βλάβης
        e.storm = STORM_LEN
        mark(e)

    # 1/256 από το βήμα 120: και το bit 0 του r1, που δεν είναι μέρος του r3
    # (src/econ.asm, ev_fault). Φθορά από το βήμα 121: με FAULT_GAP ανάμεσα.
    if ((r3 & 0x7F) == 0 and not r1 & 1     # απλή βλάβη: τα χαμηλά του τρίτου
            and since(e, e.lev) >= FAULT_GAP * 16):
        e.lev = [e.sol, e.frame]
        # Ο ΔΕΙΚΤΗΣ ΑΠΟ ΤΑ BITS ΠΟΥ ΠΕΡΙΣΣΕΨΑΝ, και από ΚΑΝΕΝΑ άλλο νούμερο:
        # το r2 είναι η προηγούμενη ρίψη του ίδιου Galois, και ο πολλαπλασιαστής
        # #B400 δεν αγγίζει το χαμηλό byte — άρα με μηδενικά τα χαμηλά του r3
        # το r2 % 64 είναι ΠΑΝΤΑ 0. Κάθε βλάβη χτυπούσε τον θόλο 0, που είναι
        # η μοναδική γεννήτρια οξυγόνου: επτά βλάβες το sol, όλες στο ίδιο
        # μηχάνημα. Μετρημένο· δεν φαινόταν διαβάζοντας.
        break_one(e, r3 >> 7)

    # Ενας επισκέπτης ανά ~2,7 sol, όχι δώδεκα το sol: βλ. src/econ.asm — με
    # 1/64 ανά περιστροφή οι επισκέπτες έτρωγαν 70 τρόφιμα το sol.
    if (r2 & 0x7FF) == 0 and e.ship_state == SHIP_NONE and e.pad_node != 255:
        call_ship(e, unbidden(e, SK_VISITOR))   # απρόσκλητοι (§6.11)
    # Ο ΕΜΠΟΡΟΣ ΕΡΧΕΤΑΙ ΜΟΝΟΣ ΤΟΥ (βήμα 93), με την ίδια συχνότητα από τα ίδια
    # έντεκα bits: μηδέν είναι επισκέπτης, MER_ROLL έμπορος. Το MER_ROLL έχει
    # ένα στο bit 0 (όχι αλλαγή ανέμου), στο 2 (όχι βλάβη), στο 7 (όχι θύελλα,
    # όχι έκλαμψη) και μηδέν στο 3 (όχι μετεωρίτες): δεν συμπίπτει με κανένα.
    if (r2 & 0x7FF) == MER_ROLL and e.ship_state == SHIP_NONE and e.pad_node != 255:
        call_ship(e, unbidden(e, SK_MERCHANT))

    # ηλιακή έκλαμψη: τα ψηλά του ίδιου, και από το βήμα 121 μία περιστροφή στις
    # τέσσερις του ρολογιού (1/4096): οι στόχοι θέλουν όλα τα 64 του r3, και το
    # r3 < 64 ορίζει ήδη το r1 — στις τρεις ζαριές δεν μένει ελεύθερο bit.
    # Από το βήμα 124 r3 >= #FFC0, όχι r3 < 64 (βλ. τη θύελλα), και οι στόχοι
    # από τα έξι χαμηλά bits.
    if (r3 >> 6) == 0x3FF and (e.frame >> 4) & 3 == 0 and may(e):
        mark(e)
        t = r3 & 63
        break_one(e, t + 37)
        break_one(e, (t >> 3) + 101)
        break_one(e, (t >> 1) + 173)

    meteor_tick(e, r1)
    return new_sol


def since(e, t):
    """ev_since: frames από το γεγονός t = [sol, frame]. 0xFFFF από τρία sol
    και πάνω, και για το [0, 0], «ποτέ»."""
    if t == [0, 0]:
        return 0xFFFF
    d = (e.sol - t[0]) & 0xFF
    if d >= 3:
        return 0xFFFF
    return (d * e.sollen + e.frame - t[1]) & 0xFFFF


def may(e):
    """ev_may: μπορεί να αρχίσει καταστροφή τώρα;"""
    return (e.alive >= DIS_POP and since(e, e.lev) >= FAULT_GAP * 16
            and since(e, e.ldis) >= 2 * e.sollen)


def mark(e):
    """ev_mark: μια καταστροφή άρχισε τώρα — και είναι το τελευταίο γεγονός."""
    e.ldis = [e.sol, e.frame]
    e.lev = [e.sol, e.frame]


def x_bytes(e):
    """Τα πεδία του βήματος 121 όπως κάθονται στο EC_X (τράπεζα 6, στο πάνω
    μισό του node_occ, θέση X_OFF): [sol, frame] της τελευταίας καταστροφής,
    και του τελευταίου γεγονότος."""
    return bytes([e.ldis[0]]) + int(e.ldis[1]).to_bytes(2, "little") + \
        bytes([e.lev[0]]) + int(e.lev[1]).to_bytes(2, "little")


X_OFF = 128 + 96 + 4                    # AG_FOE0 + AG_NFOE στο πάνω μισό
X_N = 6


def occ_hi(e):
    """Το πάνω μισό της σελίδας node_occ για το harness: τα σημάδια των
    φιγούρων μηδέν, και τα πεδία του EC_X στη θέση τους."""
    return bytes(X_OFF - 128) + x_bytes(e) + bytes(256 - X_OFF - X_N)


# --- η βροχή μετεωριτών (§6.10) — το src/meteor.asm, γραμμή προς γραμμή -----
#
# Τα δώδεκα ψηλά bits του r1 ΟΛΑ ΕΝΑ: 1 στις 4.096 περιστροφές. Οι άλλες ζαριές
# ζητούν μηδενικά στα ίδια bits της ροής, οπότε η βροχή δεν συμπίπτει ποτέ με
# θύελλα, βλάβη, έκλαμψη ή επισκέπτη. Οι θέσεις έρχονται από ΔΙΚΗ της
# γεννήτρια (mrnd), οκτώ βήματα ανά byte. Τον κρατήρα — τον κόσμο — δεν τον
# ξέρει η αναφορά· τον ελέγχει το tests/test_meteor.py στο κανονικό binary.
METEOR_N = 8
_DIMS = None


def struct_dims():
    """(πλάτος bytes, ύψος γραμμών) ανά kind*4 + size: το struct_dims των
    assets, ίδιο με το G_struct_dims που διαβάζει ο Z80."""
    global _DIMS
    if _DIMS is None:
        from sprites import load_map, load_bin
        t = load_map()["struct_dims"]
        _DIMS = load_bin()[t.off:t.off + t.size]
    return _DIMS


def _s8(v):
    v &= 0xFF
    return v - 256 if v > 127 else v


def _mbyte(e):
    for _ in range(8):
        e.mrnd = lfsr(e.mrnd)
    return e.mrnd & 0xFF


def _node_rec(e, n):
    if n < MAX_DOME:
        return e.dome, n * DOME_REC
    return e.struct, (n - MAX_DOME) * STRUCT_REC


def _footprint(e, n):
    rec, b = _node_rec(e, n)
    if n < MAX_DOME:
        w = h = 4 + 2 * rec[b + D_SIZE]
    else:
        dims = struct_dims()
        k = (rec[b + ST_KIND] * 8 + rec[b + ST_SIZE] * 2) & 0xFF
        w, h = dims[k] // 4, dims[k + 1] // 16
    x0 = _s8(rec[b + D_CX] - w) >> 1
    y0 = _s8(rec[b + D_CY] - h) >> 1
    return x0, y0, w, h


def meteor_tick(e, r1):
    if e.meteor:
        _impact(e)
        return
    if (r1 >> 4) != 0xFFF:
        return
    if not may(e):                          # βήμα 121: ev_may
        return
    e.mrnd = (r1 ^ e.frame) & 0xFFFF or 1
    c = _mbyte(e) & 127
    for _ in range(128):
        if c < MAX_DOME + MAX_STRUCT:
            rec, b = _node_rec(e, c)
            if rec[b + D_STATE]:
                e.mcx = _s8(rec[b + D_CX]) >> 1
                e.mcy = _s8(rec[b + D_CY]) >> 1
                e.meteor = METEOR_N
                mark(e)
                return
        c = (c + 1) & 127


def _impact(e):
    e.meteor -= 1
    b = _mbyte(e)
    s = e.mrnd >> 8                         # ποια μηχανή, αν πέσει σε θόλο
    tx = _s8(e.mcx + (b & 15) - 8)
    ty = _s8(e.mcy + (b >> 4) - 8)
    if not (-64 <= tx < 64 and -64 <= ty < 64):
        return
    for n in range(MAX_DOME + MAX_STRUCT):
        rec, base = _node_rec(e, n)
        if not rec[base + D_STATE]:
            continue
        x0, y0, w, h = _footprint(e, n)
        if ((tx - x0) & 0xFF) < w and ((ty - y0) & 0xFF) < h:
            break
    else:
        return                              # έδαφος: ο κρατήρας είναι του κόσμου
    if rec[base + D_STATE] != DS_ACTIVE:
        rec[base + D_INTEG] = 0             # εργοτάξιο: χάνει την πρόοδο
    elif n < MAX_DOME:
        break_one(e, n + 64 * s)            # μία μηχανή σταματά
    elif rec[base + ST_KIND] == K_SHIP:
        return                              # το σκάφος δεν είναι κτίριο (βήμα 87)
    else:
        rec[base + ST_STATE] = DS_BUILDING  # ξανά εργοτάξιο
        rec[base + ST_INTEG] = 0
        rec[base + ST_OWED] = 0             # ο σωρός ενός ορυχείου σκορπίζει (βήμα 115)
        e.flow_div = 1
        # Ενα airlock χωρίς αέρα: όσοι στέκονταν μέσα του βγαίνουν (βήμα 90,
        # lk_air_out). Οι πράκτορες δεν είναι εδώ: το κάνει το Sim.tick.
        if rec[base + ST_KIND] == K_AIRLOCK:
            e.air_out = n
        post_build(e, n)


def indoor_node(e, n):
    """Το en_in του src/entity.asm (βήμα 87): μέρος με αέρα είναι ένας έτοιμος
    θόλος ή ένα έτοιμο airlock. Το εργοτάξιο, η δομή και το σκάφος είναι έξω."""
    if n < MAX_DOME:
        return e.dome[n * DOME_REC + D_STATE] == DS_ACTIVE
    b = (n - MAX_DOME) * STRUCT_REC
    return (e.struct[b + ST_KIND] == K_AIRLOCK
            and e.struct[b + ST_STATE] == DS_ACTIVE)


def post_build(e, node):
    """Μία εργασία Build στην πρώτη ελεύθερη θέση (src/supply.asm, jb_post_build).
    Με τον πίνακα γεμάτο (βήμα 115), στη θέση της αδιάθετης Operate ή Repair
    με τη χαμηλότερη προτεραιότητα (την πρώτη στην ισοπαλία)· αν δεν υπάρχει,
    τίποτα, και το jb_lost."""
    at = next((j * JOB_REC for j in range(MAX_JOB)
               if e.job[j * JOB_REC + J_KIND] == NO_JOB), None)
    if at is None:
        best = 255
        for j in range(MAX_JOB):
            b = j * JOB_REC
            if e.job[b + J_KIND] in (J_OPERATE, J_REPAIR) and e.job[b + J_AGENT] == 255 \
                    and e.job[b + J_PRIO] < best:
                best, at = e.job[b + J_PRIO], b
    if at is None:
        e.lost = True
        return None
    e.job[at:at + JOB_REC] = bytes([J_BUILD, node, 255, 5, node])
    e.nbuild += 1                           # EC_NBUILD (βήμα 88, sp_build)
    return at


SP_PRIO = 4                 # src/supply.asm: κάτω από το Build


def post_supply(e, node, kind):
    """Το sp_post: μια Build που γίνεται Supply του είδους kind."""
    b = post_build(e, node)
    if b is not None:
        e.job[b + J_KIND] = kind
        e.job[b + J_PRIO] = SP_PRIO
        e.nbuild -= 1                           # δεν είναι Build
    return b


def want(e, n):
    """Το sp_want (βήμα 115, src/repost.asm): οι εργασίες που ζητά η κατάσταση
    του κόμβου — bit 0 Supply μετάλλου, 1 βιοπλαστικού, 2 Build."""
    if n >= MAX_DOME:
        b = (n - MAX_DOME) * STRUCT_REC
        if e.struct[b + ST_STATE] != DS_BUILDING:
            return 0
        o = e.struct[b + ST_OWED]
        return (1 if o >= 0x10 else 0) | (2 if o & 15 else 0) if o else 4
    b = n * DOME_REC
    st = e.dome[b + D_STATE]
    if not st:
        return 0
    w = 0
    for s in range(MACHINE_COUNT[e.dome[b + D_SIZE]]):
        h = e.dome[b + D_HEALTH + s]
        if h and not h & 0x80:
            w |= h & 3 if h & 3 else 4
    if st != DS_BUILDING:
        return w
    w &= 3                                  # τις έτοιμες τις στήνει ο χτίστης του
    p, o = e.dome[b + D_POWER], e.dome[b + D_OPS]
    if not p | o:
        return w | 4
    return w | (1 if p else 0) | (2 if o else 0)


def sweep(e):
    """Το sp_sweep (βήμα 115): για κάθε κόμβο, όποια εργασία ζητά η κατάστασή
    του και λείπει από τον πίνακα· στην πρώτη που δεν χωρά, τέλος."""
    e.lost = False
    for n in range(MAX_DOME + MAX_STRUCT):
        w = want(e, n)
        for bit, kind in ((1, J_SUPPLY), (2, J_SUPPLY + 1), (4, J_BUILD)):
            if w & bit and not find_job(e, kind, n):
                b = post_build(e, n) if kind == J_BUILD else post_supply(e, n, kind)
                if b is None:
                    return


def owed(e, node, mat):
    """Το sp_owed: (πίνακας, θέση αυτού του υλικού, θέση του άλλου, ένα
    φορτίο, μάσκα). Θόλος: μέταλλο στο D_POWER, βιοπλαστικό στο D_OPS. Δομή:
    και τα δύο στο ST_OWED, μέταλλο στα πάνω τέσσερα bits."""
    if node < MAX_DOME:
        b = node * DOME_REC
        me, other = (b + D_POWER, b + D_OPS) if mat == 0 else (b + D_OPS, b + D_POWER)
        return e.dome, me, other, 1, 0xFF
    b = (node - MAX_DOME) * STRUCT_REC + ST_OWED
    return (e.struct, b, b, 0x10, 0xF0) if mat == 0 else (e.struct, b, b, 1, 0x0F)


def supply_source(e, node):
    """Το sp_take: η πηγή πιο κοντά στον κόμβο `node` — το σκάφος (δομή 0,
    αν είναι σκάφος) και οι αποθήκες σε λειτουργία, με αυτή τη σειρά, και η
    πρώτη στην ισοπαλία. Μόνο ό,τι φτάνει (DIST < 255)· αλλιώς 255."""
    cands = []
    if e.struct[ST_KIND] == K_SHIP:
        cands.append(MAX_DOME)
    rn = getattr(e, "room_n", None)
    if rn is not None:
        cands += list(e.room_list[R_STORAGE * ROOM_MAX:R_STORAGE * ROOM_MAX + rn[R_STORAGE]])
    best, bd = 255, 255
    for c in cands:
        d = e.dist[node * 128 + c]
        if d < bd:
            best, bd = c, d
    return best


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
    # ΣΤΟ ΤΕΛΟΣ, ΚΑΙ ΕΠΙΤΗΔΕΣ: δεκάδες δοκιμές και εργαλεία ξέρουν απ' έξω ότι
    # το power_ok είναι στο +46 και οι ζωντανοί στο +58. Δύο πεδία στη μέση θα
    # τα μετακινούσαν όλα.
    out += int(e.ess_power).to_bytes(2, "little")
    out += int(e.acc_ess).to_bytes(2, "little")
    out += bytes([e.meteor, e.mcx & 0xFF, e.mcy & 0xFF])   # βήμα 38
    out += int(e.mrnd).to_bytes(2, "little")
    out += bytes([e.nbuild])                                 # βήμα 88
    out += bytes(e.land)                                     # βήμα 91
    out += bytes([e.markup] + list(e.cargo))                 # βήμα 93
    out += bytes([e.mines])                                  # βήμα 94
    out += bytes([e.lands])                                  # βήμα 111
    return bytes(out)


# + μετεωρίτες, Build, ειδικότητες, έμπορος, ορυχεία, προσγειώσεις = 108
ECON_BYTES = 64 + 8 + 10 + 4 + 5 + 1 + 5 + 9 + 1 + 1


POP_DOME, POP_STRUCT = 24, 30          # η αποικία του populate (tests/test_sim.py)


def populate(e, n_dome=POP_DOME, n_struct=POP_STRUCT, seed=11):
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
    # ΚΑΙ ΧΩΡΟΥΝ (βήμα 122): η αποθήκη είναι συνολική, και αυτή η αποικία έχει
    # το αμπάρι (500) και έναν θόλο Storage M (300). Ως τότε κουβαλούσε 2.380
    # αγαθά και κάθε σάρωμα θα την έβρισκε γεμάτη — τίποτα δεν θα παραγόταν.
    # 630 αφήνουν 170 για ό,τι φτιάχνει μέσα στα παράθυρα του tests/test_sim.py.
    for s, q in ((S_WATER, 600), (S_FOOD, 200), (S_ORE, 80), (S_STARCH, 40),
                 (S_VEG, 40), (S_MEDPLANT, 40), (S_MEDI, 30), (S_SPARE, 40),
                 (S_BIOPL, 60), (S_PROC, 40), (S_METAL, 60)):
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
        # ΕΝΑΣ ΣΚΑΒΕΙ ΣΕ ΚΑΘΕ ΟΡΥΧΕΙΟ (βήμα 94): ως τότε το ορυχείο έβγαζε
        # μόνο του, και η «ανεξαρτησία» του §10.2 θέλει μετάλλευμα φτιαγμένο
        # εδώ. Σαν ρομπότ γεώτρησης, που δεν φεύγει ποτέ.
        if k == K_MINE:
            e.struct[b + ST_OPS] = 1
            # ΚΑΙ ΔΥΟ ΦΟΡΤΙΑ ΣΤΟΝ ΣΩΡΟ (βήμα 95): ο κύκλος ροής δημοσιεύει Haul
            # αμέσως, και οι σκηνές του tests/test_sim.py περνούν από φόρτωμα
            # και παράδοση χωρίς να περιμένουν πέντε κύκλους.
            e.struct[b + ST_OWED] = 2 * HAUL_LOAD
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
# Το πέμπτο byte είναι ο κόμβος της εργασίας (βήμα 88)· το J_NODE είναι πού
# πηγαίνει ο πράκτορας. Διαφέρουν μόνο στο πρώτο σκέλος μιας Supply.
J_KIND, J_NODE, J_AGENT, J_PRIO, J_SITE = range(5)
NO_JOB = 255

J_BUILD, J_OPERATE, J_HAUL, J_DRILL, J_REPAIR, J_HEAL, J_DEFEND, J_SUPPLY = range(8)
J_TRADE = 9                 # τα αγαθά του εμπόρου (βήμα 98, src/carry.asm)
# J_SUPPLY μέταλλο, J_SUPPLY + 1 βιοπλαστικό (βήμα 88, src/supply.asm)

# ποιοι ρόλοι δέχονται ποια εργασία — bitmask ανά είδος (§6.7). Η Supply:
# όλοι οι άποικοι και το ρομπότ μεταφοράς.
JOB_ROLES = [0x22, 0x05, 0x41, 0x81, 0x02, 0x08, 0x10, 0x5F, 0x5F, 0x5F]
JOB_PRIO = [5, 3, 5, 4, 6, 8, 9]        # η Haul 5 από το βήμα 95: πάνω από τη Drill
BUILD_STEP = 32                     # src/jobs.asm — οκτώ επισκέψεις
# Το OPERATE δεν έχει μία προτεραιότητα αλλά μία ανά ΔΩΜΑΤΙΟ (§6.7): με κοινή
# τιμή η ισοπαλία έσπαγε πάντα στην απόσταση, που δεν αλλάζει ποτέ, και ο
# κοντινότερος θόλος κρατούσε όλο τον κόσμο.
ROOM_PRIO = [3, 3, 3, 5, 5, 4, 3, 3, 3, 4, 4, 3]

JOB_SCAN = 4                # θόλοι ανά επίσκεψη
JOB_ASSIGN = 4              # αναθέσεις ανά επίσκεψη (§6.7)
JOB_LOOK = 32               # πράκτορες που εξετάζονται ανά επίσκεψη
NO_TASK = 255


def needs_operators(e, d):
    """Πόσες υποδοχές αυτού του θόλου θέλουν κάποιον από πάνω τους.

    Το θερμοκήπιο ζητάει ΕΝΑΝ όσα φυτά κι αν έχει: ένας βιολόγος ποτίζει όλο
    τον κήπο (run_dome). Οσο ζητούσε έναν ανά γλάστρα, ένα μεσαίο θερμοκήπιο
    ρουφούσε τέσσερις ανθρώπους και το κυλικείο δίπλα του δεν έβρισκε μαγείρα.
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
        if green:
            return 1
        if not e.dome[base + D_HEALTH + s] & 0x80:
            continue                            # δεν στήθηκε ακόμη (βήμα 99)
        if RECIPE[m][9] & MF_OPERATOR:
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


def build_done(e, a, rec, rb, node, F_ALIVE):
    """Ενα εργοτάξιο τελείωσε (ja_build)."""
    rec[rb + D_STATE] = DS_ACTIVE
    # Το lk_done του src/door.asm (βήμα 87). Ενας θόλος με σύνδεση
    # εδάφους σφραγίζεται: φεύγει, και όσοι στέκονται εκεί βγαίνουν —
    # αυτό θέλει τον γράφο, και το ελέγχει το tests/test_outside.py
    # στο ίδιο το παιχνίδι. Ενα airlock: όσοι στέκονται εκεί, ο
    # χτίστης και οι μεταφορείς του (βήμα 88), είναι πια μέσα. Κάθε
    # άλλη δομή: ήταν ήδη έξω.
    if node < MAX_DOME:
        # Η αναφορά δεν έχει γράφο εδώ: οι σκηνές της είναι θόλοι με
        # διαδρόμους ως ακμές, που το lk_done αφήνει όπως είναι.
        pass
    elif indoor_node(e, node):
        for k in range(MAXAGENT_J):
            if a.node[k] == node and a.edge[k] == 255 and a.flags[k] & F_ALIVE:
                a.flags[k] |= 2         # F_INDOORS
    e.flow_div = 1


def find_job(e, kind, node):
    """Το sp_find: υπάρχει εργασία αυτού του είδους με J_SITE τον κόμβο;"""
    return any(e.job[k * JOB_REC + J_KIND] == kind
               and e.job[k * JOB_REC + J_SITE] == node for k in range(MAX_JOB))


def mach_live(e, node):
    """Το mc_live: θόλος σε λειτουργία — τα χρωστάνε μόνο οι μηχανές του."""
    return node < MAX_DOME and e.dome[node * DOME_REC + D_STATE] == DS_ACTIVE


def mach_arrive(e, node, mat, done):
    """Το mc_arrive (done = False) και το mc_tail (True). Το φορτίο του
    υλικού mat πάει στην πρώτη μηχανή που το χρωστά· αν εκείνη δεν χρωστά πια
    τίποτα και ο θόλος δουλεύει, μία Build αν δεν υπάρχει. True = κάποια το
    χρωστά ακόμη: η εργασία ξανανοίγει."""
    if node >= MAX_DOME:
        return False
    b = node * DOME_REC
    bit = mat + 1
    for s in range(MACHINE_COUNT[e.dome[b + D_SIZE]]):
        h = e.dome[b + D_HEALTH + s]
        if not h & bit:
            continue
        if done:
            return True
        h ^= bit
        e.dome[b + D_HEALTH + s] = h
        if h == MACH_READY and e.dome[b + D_STATE] == DS_ACTIVE \
           and not find_job(e, J_BUILD, node):
            post_build(e, node)
        return mach_arrive(e, node, mat, True)
    return False


def ready_slot(e, node):
    """Το jab_inst: η πρώτη υποδοχή που πήρε τα υλικά της και περιμένει τον
    χτίστη (1-127 χωρίς τα bits των υλικών), ή None."""
    if node >= MAX_DOME:
        return None
    b = node * DOME_REC
    for s in range(MACHINE_COUNT[e.dome[b + D_SIZE]]):
        h = e.dome[b + D_HEALTH + s]
        if h and not h & 0x83:
            return s
    return None


def order_machine(e, node):
    """Το mc_order του fit_set: μία Supply ανά υλικό, αν δεν υπάρχει ήδη."""
    for kind in (J_SUPPLY, J_SUPPLY + 1):
        if not find_job(e, kind, node):
            post_supply(e, node, kind)


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
            # μια Supply γυρίζει στο εργοτάξιο· μια Haul όχι: φορτωμένη, ο
            # επόμενος παραδίδει ό,τι έμεινε στη μέση (βήμα 95). Ούτε μια
            # J_TRADE: το J_SITE της είναι το φορτίο (βήμα 98)
            if jb[b + J_KIND] not in (J_HAUL, J_TRADE):
                jb[b + J_NODE] = jb[b + J_SITE]

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
        if jb[b + J_KIND] == J_TRADE:
            # ΤΑ ΑΓΑΘΑ ΤΟΥ ΕΜΠΟΡΟΥ (βήμα 98, tr_arrive): το φορτίο είναι της
            # εργασίας (J_SITE). Στην πίστα ένα φορτίο από το πλοίο του και ο
            # προορισμός του sp_take· σε αποθήκη ή στο σκάφος ένα δικό του
            # στα αποθέματα, και ένα για τον έμπορο.
            pad = e.pad_node
            store = node != pad
            done = False
            if not store:
                load = trade_pick(e)
                if load or e.markup:
                    jb[b + J_SITE] = load
                    a.spare[i] = 0
                    dst = supply_source(e, node)
                    if dst != 255:
                        jb[b + J_NODE] = dst
                        a.dest[i] = dst
                        continue
                    store = True        # καμία αποθήκη δεν φτάνεται: εδώ
                else:
                    done = True
            if store:
                ld = jb[b + J_SITE]
                if ld != TRADE_GIVE:    # ένα για τον έμπορο, αφημένο: συνεχίζει
                    if ld > TRADE_GIVE:
                        add_stock(e, ld & 15, ld >> 4)
                    jb[b + J_SITE] = 0
                    if e.markup:
                        e.markup -= 1
                        jb[b + J_SITE] = TRADE_GIVE
                    elif not any(e.cargo[2 * k + 1] for k in range(MER_SLOTS)):
                        done = True
                if not done:
                    if pad != 255:      # η πίστα έπεσε: περιμένει εδώ (tra_go)
                        jb[b + J_NODE] = pad
                        a.dest[i] = pad
                    continue
            trade_bye(e)
            a.task[i] = NO_TASK
            jb[b + J_KIND] = NO_JOB
            continue
        if jb[b + J_KIND] >= J_SUPPLY:
            # ΤΡΟΦΟΔΟΣΙΑ (βήμα 88, sp_arrive): στην πηγή φορτώνει και πάει
            # στο εργοτάξιο· στο εργοτάξιο ξεφορτώνει.
            mat = jb[b + J_KIND] - J_SUPPLY
            site = jb[b + J_SITE]
            if node != site:
                jb[b + J_NODE] = site
                a.spare[i] = S_METAL + mat
                a.dest[i] = site
                continue
            a.spare[i] = 0
            # ΚΑΙ ΟΙ ΜΗΧΑΝΕΣ (βήμα 99, mc_live / mc_arrive / mc_tail): ένας
            # θόλος σε λειτουργία δεν χρωστά ο ίδιος, και ό,τι δεν χρωστά το
            # εργοτάξιο πάει στην πρώτη μηχανή που το χρωστά.
            rec, me, other, unit, mask = owed(e, site, mat)
            if not mach_live(e, site) and rec[me] & mask:
                rec[me] = (rec[me] - unit) & 0xFF
                if rec[me] & mask:
                    more = True
                else:
                    if not (rec[me] | rec[other]):
                        post_build(e, site)     # όλα έφτασαν: σειρά του χτίστη
                    more = mach_arrive(e, site, mat, True)
            else:
                more = mach_arrive(e, site, mat, False)
            if more:
                jb[b + J_AGENT] = 255           # κι άλλο ταξίδι: ξανανοίγει
                a.task[i] = NO_TASK
                continue
            a.task[i] = NO_TASK
            jb[b + J_KIND] = NO_JOB
            continue
        if jb[b + J_KIND] == J_HAUL:
            # ΜΕΤΑΦΟΡΑ (βήμα 95, hl_arrive): στο ορυχείο ένα φορτίο από τον
            # σωρό και ο προορισμός του sp_take· στον προορισμό — ή εκεί, αν
            # δεν φτάνεται κανένας — το φορτίο στα αποθέματα.
            mine = jb[b + J_SITE]
            if node == mine:
                ms = (mine - MAX_DOME) * STRUCT_REC
                e.struct[ms + ST_OPS] &= ~ST_HAUL & 0xFF
                if e.struct[ms + ST_OWED] < HAUL_LOAD:
                    a.task[i] = NO_TASK
                    jb[b + J_KIND] = NO_JOB
                    continue
                e.struct[ms + ST_OWED] -= HAUL_LOAD
                a.spare[i] = 0
                dst = supply_source(e, node)
                if dst != 255:
                    jb[b + J_NODE] = dst
                    a.dest[i] = dst
                    a.spare[i] = S_ORE
                    continue
            a.spare[i] = 0
            add_stock(e, S_ORE, HAUL_LOAD)
            e.prod_mask |= 1 << S_ORE
            a.task[i] = NO_TASK
            jb[b + J_KIND] = NO_JOB
            continue
        if jb[b + J_KIND] == J_BUILD:
            # Ο ΕΡΓΑΤΗΣ ΜΕΝΕΙ ΚΑΙ ΧΤΙΖΕΙ (src/jobs.asm, ja_build): η πρόοδος
            # είναι η ακεραιότητα, BUILD_STEP ανά επίσκεψη ως το 255. Ως το
            # βήμα 38 η αναφορά τον έκανε χειριστή — δεν το είχε ζητήσει καμία
            # δοκιμή, γιατί η αποικία της δεν έχει εργοτάξια.
            rec, rb = _node_rec(e, node)
            if rec[rb + D_STATE] != DS_ACTIVE:
                v = min(255, rec[rb + D_INTEG] + BUILD_STEP)
                rec[rb + D_INTEG] = v
                if v != 255:
                    continue
                build_done(e, a, rec, rb, node, F_ALIVE)
            # ΟΙ ΜΗΧΑΝΕΣ ΤΟΥ (βήμα 99, jab_inst): η πρώτη που πήρε τα υλικά
            # της ανεβαίνει BUILD_STEP, και η εργασία μένει όσο βρίσκει μία.
            s = ready_slot(e, node)
            if s is not None:
                h = e.dome[node * DOME_REC + D_HEALTH + s] + BUILD_STEP
                e.dome[node * DOME_REC + D_HEALTH + s] = MACH_HP if h & 0x80 else h
                a.dest[i] = node                # το lk_done τον έβγαλε ίσως έξω
                continue
            e.nbuild -= 1                       # EC_NBUILD
            a.task[i] = NO_TASK
            jb[b + J_KIND] = NO_JOB
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
            e.dome[node * DOME_REC + D_HEALTH + s] = MACH_HP
            a.task[i] = NO_TASK
            jb[b + J_KIND] = NO_JOB
            continue
        if node < MAX_DOME:
            e.dome[node * DOME_REC + D_OPS] += 1
        else:                               # το ορυχείο (βήμα 94, op_ptr)
            # ΟΧΙ `b`: είναι η εγγραφή της εργασίας, που σβήνει πιο κάτω. Ως το
            # βήμα 95 εδώ ήταν `b`, και η αναφορά έσβηνε ένα byte άλλης εργασίας.
            sb = (node - MAX_DOME) * STRUCT_REC + ST_OPS
            e.struct[sb] = (e.struct[sb] + 1) & 0x7F & ~ST_DLOW   # και η Drill του έφυγε
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
                jb[k * JOB_REC + J_PRIO] = (
                    ROOM_PRIO[e.dome[d * DOME_REC + D_ROOM]]
                    if kind == J_OPERATE else JOB_PRIO[kind])
                jb[k * JOB_REC + J_SITE] = d
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
        if jb[best * JOB_REC + J_KIND] >= J_SUPPLY:
            # sp_take: πρώτα στην πηγή, με άδεια χέρια
            a.spare[i] = 0
            src = supply_source(e, a.node[i])
            if src != 255:
                jb[best * JOB_REC + J_NODE] = src
                a.dest[i] = src
        done += 1
    e.job_agent = (e.job_agent + JOB_LOOK) & (MAXAGENT_J - 1)


MAXAGENT_J = 128
# ΟΙ ΘΕΣΕΙΣ ΤΩΝ ΡΟΜΠΟΤ (βήμα 92, src/const.asm): 0-79 άποικοι, 80-95 ρομπότ —
# τα 80 + 16 του §6.1. Τα ρομπότ δεν έχουν ανάγκες, δεν πιάνουν θέση στο
# ταβάνι και δεν αναπνέουν: ο μετρητής ζωντανών της θέσης 12 μετρά τους 80.
AG_BOT0, AG_NBOT = 80, 16
RL_CBOT, RL_CARRY = 5, 6            # κατασκευής, μεταφοράς (§6.1)
RL_DRILL = 7                        # γεώτρησης (βήμα 94)


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
    e.pop_cap = min(AG_BOT0, POP_BASE + POP_PER_CONTROL * e.room_n[R_CONTROL])
    e.pad_node = 255
    for i in range(MAX_STRUCT):
        b = i * STRUCT_REC
        if e.struct[b + ST_STATE] == DS_ACTIVE and e.struct[b + ST_KIND] == K_PAD:
            e.pad_node = MAX_DOME + i
            break


# --- οι στολές (βήμα 90, src/suit.asm) -------------------------------------
# Μία μονάδα = δύο επισκέψεις αναγκών = 128 frames.
SUIT_START = 234            # 10 λεπτά: οι τέσσερις του σκάφους
SUIT_TRIP = 70              # 3 λεπτά, σε κάθε έξοδο
SUIT_LOW = 23               # 1 λεπτό: γυρίζει στο airlock


def nearest_airlock(e, node):
    """Το su_lock: το κοντινότερο έτοιμο airlock στον γράφο, ή 255.
    Ισοπαλία: η πρώτη δομή."""
    best, best_d = 255, 255
    for s in range(MAX_STRUCT):
        b = s * STRUCT_REC
        if e.struct[b + ST_KIND] != K_AIRLOCK or e.struct[b + ST_STATE] != DS_ACTIVE:
            continue
        d = e.dist[node * 128 + MAX_DOME + s]
        if d < best_d:
            best, best_d = MAX_DOME + s, d
    return best


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
SK_DEALT = 3                # ο έμπορος μετά τη συμφωνία, ώσπου να κουβαληθούν όλα
SK_FOE = 4                  # οι εισβολείς (βήμα 111)
TRADE_JOBS = 2              # εργασίες J_TRADE ανά συμφωνία (src/carry.asm)
TRADE_LOAD = 10
TRADE_GIVE = 0x0F           # J_SITE μιας J_TRADE: ένα φορτίο ΓΙΑ τον έμπορο
SHIP_TRIP = 24              # περιστροφές ταξιδιού
SHIP_STAY = 8               # πόσο μένει προσγειωμένο
COLONISTS_PER_SHIP = 4
VISITOR_FOOD = 6
VISITOR_MORALE = 24
# Πρώτη εκτίμηση, όπως όλα τα νούμερα ισορροπίας: με 8 ανά Control, μια
# αποικία των ενενήντα δεν χωρούσε ούτε τον εαυτό της και κανένα πλοίο
# αποίκων δεν είχε νόημα.
POP_PER_CONTROL = 48
POP_BASE = 6                # το πλήρωμα του σκάφους (βήμα 120· ως τότε 4)

M_FOOTHOLD, M_INDUSTRY, M_INDEPENDENCE, M_AUTOMATION, M_HABITAT = (
    1, 2, 4, 8, 16)

INDUSTRY_STOCKS = (S_METAL, S_BIOPL, S_SPARE)
# Τα δέκα αγαθά του §6.5. Τα τέσσερα ενδιάμεσα του θερμοκηπίου δεν μετράνε
# για την «ανεξαρτησία»: είναι πρώτη ύλη, όχι προϊόν.
INDEPENDENCE_STOCKS = tuple(range(10))


# --- ο έμπορος (βήμα 93, §6.11) ------------------------------------------
# Οπως στο Planetbase: έρχεται μόνος του, φέρνει λίγα αγαθά (τρία ή τέσσερα,
# άλλα κάθε φορά), τα δικά του τα λογαριάζει με το κέρδος του (35-65%) και τα
# δικά σου στην τιμή τους, και η ανταλλαγή γίνεται όταν δίνεις τουλάχιστον όσο
# παίρνεις. Μετά φεύγει· αλλιώς μένει μισό sol. Οι τιμές είναι του Planetbase
# (meal 5, ore 10, metal 15, bioplastic 10, semiconductors 40, spares 15,
# medical supplies 25, gun 80, starch/vegetables/vitromeat 5, medicinal 10)·
# το ρομπότ 120, ανάμεσα στο ρομπότ μεταφοράς (80) και κατασκευής (160), γιατί
# εδώ ένα Bot γίνεται εναλλάξ το ένα ή το άλλο. Το νερό δεν είναι εμπόρευμα,
# όπως εκεί.
TRADE_VALUE = [0, 5, 10, 15, 10, 40, 15, 25, 80, 120, 5, 5, 10, 5]   # ανά απόθεμα
# Η ΜΟΝΑΔΑ ΤΟΥ ΒΕΛΟΥΣ, ~50-100 σε αξία: 10 τρόφιμα, 5 μέταλλα, 2 επεξεργαστές,
# 1 ρομπότ. Και του φορτίου: ο έμπορος φέρνει 1-4 μονάδες από το καθένα.
TRADE_LOT = [0, 10, 10, 5, 10, 2, 5, 4, 1, 1, 10, 10, 10, 10]
TRADE_N = 13                # τα αποθέματα 1-13: όλα εκτός από το νερό
MER_SLOTS = 4
MER_ROLL = 0x5A5            # (r2 & 0x7FF): το μηδέν είναι ο επισκέπτης
MARKUP_MIN = 35             # + 0..30
TRADE_MAX = 99              # ως 99 από ένα αγαθό σε μία προσφορά: δύο ψηφία


def mer_bytes(seed, n):
    """n bytes από ΔΙΚΟ τους βήματα του Galois, οκτώ ανά byte (όπως η βροχή
    μετεωριτών): ο σπόρος είναι το EC_RND, που ΔΕΝ αλλάζει — η ακολουθία των
    συμβάντων μένει ίδια, με ή χωρίς έμπορο."""
    out, x = [], seed
    for _ in range(n):
        for _ in range(8):
            x = lfsr(x)
        out.append(x & 0xFF)
    return out


def land_merchant(e):
    """Το φορτίο και το κέρδος, τη στιγμή που προσγειώνεται. Τρία bytes:
    το πρώτο δίνει το κέρδος (5 bits, ως 30) και αν φέρνει τέσσερα (bit 5), το
    δεύτερο το πρώτο αγαθό (χαμηλά 4 bits, mod 13) και το βήμα ανάμεσά τους
    (ψηλά 4, mod 12, + 1), το τρίτο τις μονάδες, δύο bits το καθένα. Το 13 είναι
    πρώτος αριθμός: s, s + d, s + 2d, s + 3d (mod 13) είναι πάντα διαφορετικά."""
    b0, b1, b2 = mer_bytes(e.rnd, 3)
    m = b0 & 31
    e.markup = MARKUP_MIN + (m - 31 if m >= 31 else m)
    k = 4 if b0 & 32 else 3
    t = b1 & 15
    t = t - 13 if t >= 13 else t
    d = b1 >> 4
    d = (d - 12 if d >= 12 else d) + 1
    cargo = []
    for i in range(MER_SLOTS):
        if i < k:
            g = 1 + t
            cargo += [g, TRADE_LOT[g] * (1 + (b2 & 3))]
            b2 >>= 2
            t += d
            t = t - 13 if t >= 13 else t
        else:
            cargo += [0, 0]
    e.cargo = cargo
    e.ship_eta = e.sollen >> 5          # μισό sol, σε περιστροφές


def mer_here(e):
    return e.ship_state == SHIP_LANDED and e.ship_kind == SK_MERCHANT


def trade_price(e, g):
    """Ενα από τα δικά του: η τιμή και το κέρδος του, στρογγυλεμένα ανά
    μονάδα. Το βιοπλαστικό με 40% κάνει 14, όπως στο παράδειγμα του Planetbase."""
    v = TRADE_VALUE[g]
    return v + (v * e.markup + 50) // 100


def trade_totals(e, net):
    """net[απόθεμα]: > 0 παίρνεις από αυτόν, < 0 του δίνεις. (παίρνεις, δίνεις)
    σε αξία: τα δικά του με το κέρδος, τα δικά σου στην τιμή τους."""
    take = sum(n * trade_price(e, g) for g, n in enumerate(net) if n > 0)
    give = sum(-n * TRADE_VALUE[g] for g, n in enumerate(net) if n < 0)
    return take, give


def trade(e, net):
    """Η ανταλλαγή, αν γίνεται: κάτι παίρνεις, και δίνεις τουλάχιστον όσο
    παίρνεις, από όσα έχεις ΤΩΡΑ, και υπάρχει θέση για τους μεταφορείς. Μετά
    ο έμπορος περιμένει ώσπου να κουβαληθούν όλα (βήμα 98, Planetbase· ως το
    97 η παράδοση ήταν στιγμιαία). Σπάει το σερί της ανεξαρτησίας."""
    if not mer_here(e):
        return False
    take, give = trade_totals(e, net)
    if take == 0 or give < take:
        return False
    if any(n < 0 and -n > e.stock[g] for g, n in enumerate(net)):
        return False
    # ΟΙ ΜΕΤΑΦΟΡΕΙΣ ΠΡΩΤΑ (trd_post): χωρίς θέση στον πίνακα, ή χωρίς πίστα,
    # ούτε συμφωνία
    posted = 0
    for _ in range(TRADE_JOBS if e.pad_node != 255 else 0):
        b = post_build(e, e.pad_node)
        if b is None:
            break
        e.nbuild -= 1                           # δεν είναι Build
        e.job[b + J_KIND] = J_TRADE
        e.job[b + J_PRIO] = SP_PRIO
        e.job[b + J_SITE] = 0                   # άδεια: το φορτίο της
        posted += 1
    if not posted:
        return False
    # ΟΠΩΣ ΤΑ ΕΡΓΟΤΑΞΙΑ (βήμα 98): όσα δίνεις φεύγουν τώρα, σε φορτία των
    # δέκα που οφείλονται στον έμπορο (στο markup, που δεν χρειάζεται πια)·
    # όσα παίρνεις μένουν στο πλοίο του (οι ποσότητες του cargo) ώσπου να
    # κουβαληθούν. Ο έμπορος περιμένει (SK_DEALT, eta #FFFF).
    loads = 0
    for g, n in enumerate(net):
        if n < 0:
            e.stock[g] += n
            loads += (-n + TRADE_LOAD - 1) // TRADE_LOAD
    for k in range(MER_SLOTS):
        g = e.cargo[2 * k]
        e.cargo[2 * k + 1] = max(net[g], 0) if g else 0
    e.markup = loads
    e.traded = 1
    e.ship_kind = SK_DEALT
    e.ship_eta = 0xFFFF
    return True


def trade_pick(e):
    """Το tra_pick: ένα φορτίο από το πλοίο του εμπόρου, ποσότητα << 4 | αγαθό,
    από την πρώτη θέση με κάτι ακόμη, ως TRADE_LOAD· 0 αν δεν μένει τίποτα."""
    for k in range(MER_SLOTS):
        q = e.cargo[2 * k + 1]
        if q:
            n = min(q, TRADE_LOAD)
            e.cargo[2 * k + 1] = q - n
            return (n << 4) | e.cargo[2 * k]
    return 0


def trade_bye(e):
    """Το tra_bye: η εργασία τελειώνει. Οι άλλες J_TRADE χωρίς πράκτορα και
    χωρίς φορτίο σβήνουν· αν δεν μένει καμία άλλη, ο έμπορος φεύγει."""
    out = 0
    for j in range(MAX_JOB):
        b = j * JOB_REC
        if e.job[b + J_KIND] != J_TRADE:
            continue
        if e.job[b + J_AGENT] == 255 and e.job[b + J_SITE] == 0:
            e.job[b + J_KIND] = NO_JOB
        else:
            out += 1
    if out == 1:
        e.ship_eta = 0


def call_ship(e, kind):
    """Ο παίκτης καλεί πλοίο από το Control. Ενα τη φορά, και θέλει πίστα."""
    if e.ship_state != SHIP_NONE or e.pad_node == 255:
        return False
    e.ship_state = SHIP_INCOMING
    e.ship_kind = kind
    e.ship_eta = SHIP_TRIP
    return True


def ship_tick(e, a, spawn_node, F_ALIVE, occ):
    """Μία περιστροφή του πλοίου. Τρέχει στη θέση 15, μαζί με τα συμβάντα."""
    if e.ship_state == SHIP_NONE:
        return
    if e.ship_eta:
        e.ship_eta -= 1
        return
    if e.ship_state == SHIP_INCOMING:
        e.ship_state = SHIP_LANDED
        e.ship_eta = SHIP_STAY
        # ΜΕΤΡΑΝΕ ΟΛΕΣ ΟΙ ΠΡΟΣΓΕΙΩΣΕΙΣ (βήμα 111, η απόφαση του παίκτη): άποικοι,
        # επισκέπτες, έμποροι. Των εισβολέων μηδενίζει το μέτρημα.
        if e.ship_kind == SK_FOE:
            e.lands = 0
            land_foes(e, a, spawn_node, F_ALIVE, occ)
            return
        e.lands = min(255, e.lands + 1)
        if e.ship_kind == SK_COLONIST:
            land_colonists(e, a, spawn_node, F_ALIVE, occ)
        elif e.ship_kind == SK_VISITOR:
            visit(e, a, F_ALIVE)
        else:
            land_merchant(e)            # βήμα 93
        return
    e.ship_state = SHIP_NONE            # έφυγε


def land_colonists(e, a, node, F_ALIVE, occ):
    """Καινούργιοι άποικοι στην πλατφόρμα. Οσοι χωράνε στο ταβάνι. Ο καθένας
    παίρνει θέση στην πίστα όπως σε κάθε άφιξη (βήμα 89: έτσι φαίνεται εκεί),
    με τη σειρά γεμίσματος του entity.py, ή 255 αν γέμισε."""
    n = 0
    # ΜΟΝΟ ΟΙ ΘΕΣΕΙΣ ΑΠΟΙΚΩΝ (βήμα 92): οι ζωντανοί και οι ελεύθερες, 0-79.
    count = [sum(1 for i in range(AG_BOT0)
                 if a.flags[i] & F_ALIVE and a.role[i] == r) for r in range(CW_N)]
    for i in range(AG_BOT0):
        if n >= COLONISTS_PER_SHIP or e.alive + n >= e.pop_cap:
            break
        if a.flags[i] & F_ALIVE:
            continue
        born(a, i, F_ALIVE, pick_role(e, count), node, occ)
        n += 1
    e.alive += n
    return n


def born(a, i, flags, role, node, occ):
    """Το sh_born / sb_rest (src/ship.asm): σημαίες, ρόλος, κόμβος, θέση στον
    κόμβο (με τη σειρά γεμίσματος, ή 255), γεμάτες μπάρες. Ο άποικος στην πίστα,
    έξω· το ρομπότ στο εργοστάσιο, μέσα (βήμα 92)."""
    a.flags[i] = flags
    a.role[i] = role
    a.node[i] = node
    a.dest[i] = node
    a.edge[i] = 255
    a.slot[i] = next((t for t in (0, 4, 2, 6, 1, 5, 3, 7)
                      if not (occ[node] >> t) & 1), 255)
    if a.slot[i] != 255:
        occ[node] |= 1 << a.slot[i]
    a.task[i] = 255
    a.progress[i] = 0
    a.o2[i] = 200
    a.water[i] = 200
    a.food[i] = 200
    a.sleep[i] = 200
    a.health[i] = 200
    a.morale[i] = 160
    a.suit[i] = SUIT_TRIP               # κατεβαίνει έξω, με στολή (βήμα 90)
    a.spare[i] = 0


M_ROBOTS = MACH.index("robots")


def bot_tick(e, a, occ, F_ALIVE=1, F_INDOORS=2):
    """Τα ρομπότ από το απόθεμα Bots (βήμα 92, src/bots.asm), μία φορά ανά
    περιστροφή στη θέση 15, πριν από το πλοίο. Με ένα Bot στο απόθεμα και μια
    ελεύθερη από τις θέσεις 80-95 (η πρώτη), ένα ρομπότ ξυπνά στον πρώτο θόλο
    Factory του ευρετηρίου που έχει μηχανή robots σε κάποια από τις οκτώ
    υποδοχές, και το απόθεμα πέφτει κατά ένα. Ζυγή θέση: κατασκευής, μονή:
    μεταφοράς. Επιστρέφει την ταυτότητα, ή None."""
    if e.stock[S_BOT] == 0:
        return None
    i = next((k for k in range(AG_BOT0, AG_BOT0 + AG_NBOT)
              if not a.flags[k] & F_ALIVE), None)
    if i is None:
        return None
    for k in range(e.room_n[R_FACTORY]):
        d = e.room_list[R_FACTORY * ROOM_MAX + k]
        b = d * DOME_REC + D_MACH
        if M_ROBOTS in e.dome[b:b + MACH_SLOTS]:
            break
    else:
        return None
    e.stock[S_BOT] -= 1
    role = RL_DRILL if drill_need(e, a, F_ALIVE) else RL_CBOT + (i & 1)
    born(a, i, F_ALIVE | F_INDOORS, role, d, occ)
    return i


def drill_need(e, a, F_ALIVE=1):
    """Το dr_need (βήμα 94, src/bots.asm): θέλουν τα ορυχεία γεωτρύπανο;
    MINE_OPS θέσεις για κάθε έτοιμο ορυχείο — όσα μέτρησε ο τελευταίος
    κύκλος ροής, e.mines — μείον τα ζωντανά γεωτρύπανα."""
    places = MINE_OPS * e.mines             # όπως τα μέτρησε ο κύκλος ροής
    drills = sum(1 for i in range(AG_BOT0, AG_BOT0 + AG_NBOT)
                 if a.flags[i] & F_ALIVE and a.role[i] == RL_DRILL)
    return places > drills


def post_drill(e, node, prio=DRILL_PRIO):
    """Το dr_post (βήμα 94): από το βήμα 126 με την προτεραιότητα που γράφει
    στο job_prio — DRILL_LOW όταν κάποιος ήδη σκάβει."""
    return post_job(e, J_DRILL, node, prio)


def raise_drill(e, i):
    """Το dr_raise (βήμα 126, src/flow.asm): το ορυχείο i άδειασε με τη Drill
    του χαμηλά — πίσω στο DRILL_PRIO, και το ST_DLOW σβήνει. Η πρώτη εργασία
    στον κόμβο του που είναι Drill· χωρίς καμία σβήνει και το bit 7, και ο
    επόμενος κύκλος τη δημοσιεύει ξανά."""
    e.struct[i * STRUCT_REC + ST_OPS] &= ~ST_DLOW & 0xFF
    jb = e.job
    for k in range(MAX_JOB):
        b = k * JOB_REC
        if jb[b + J_NODE] == MAX_DOME + i and jb[b + J_KIND] == J_DRILL:
            jb[b + J_PRIO] = DRILL_PRIO
            return
    e.struct[i * STRUCT_REC + ST_OPS] &= 0x7F


def post_job(e, kind, node, prio=None):
    """Το st_post μέσω του jp_have (src/drill.asm, src/jobs.asm): μια εργασία
    του είδους για τον κόμβο, αν δεν υπάρχει ήδη, στην πρώτη ελεύθερη θέση·
    τίποτα αν ο πίνακας γέμισε. True αν υπάρχει πια."""
    jb = e.job
    if any(jb[k * JOB_REC + J_KIND] == kind and jb[k * JOB_REC + J_NODE] == node
           for k in range(MAX_JOB)):
        return True
    for k in range(MAX_JOB):
        b = k * JOB_REC
        if jb[b + J_KIND] == NO_JOB:
            jb[b + J_KIND] = kind
            jb[b + J_NODE] = node
            jb[b + J_AGENT] = 255
            jb[b + J_PRIO] = JOB_PRIO[kind] if prio is None else prio
            jb[b + J_SITE] = node
            return True
    return False


def pick_role(e, count):
    """Η ειδικότητα του καινούργιου (βήμα 91, src/crew.asm): αυτή που λείπει
    περισσότερο από την αποικία. Με N ζωντανούς ανθρώπους και count[r] από την
    r, μετά από αυτόν θα έπρεπε να είναι land[r] (N + 1) / 10, και λείπουν
    land[r] (N + 1) - 10 count[r] δέκατα. Το μεγαλύτερο, το πρώτο σε ισοπαλία.
    Ποτέ ρομπότ."""
    k = sum(count) + 1
    d = [e.land[r] * k - 10 * count[r] for r in range(CW_N)]
    r = d.index(max(d))
    count[r] += 1
    return r


def visit(e, a, F_ALIVE):
    """Επισκέπτες: τρώνε και ανεβάζουν το ηθικό. Ενοχλητικοί όταν πεινάς."""
    take = min(VISITOR_FOOD, e.stock[S_FOOD])
    e.stock[S_FOOD] -= take
    for i in range(AG_BOT0):            # οι άποικοι· τα ρομπότ δεν έχουν ηθικό (92)
        if a.flags[i] & F_ALIVE:
            a.morale[i] = min(255, a.morale[i] + VISITOR_MORALE)


# --- οι εισβολείς (βήμα 111, §6.10) -----------------------------------------
# ΟΠΩΣ ΣΤΟ PLANETBASE, με τις αποφάσεις του παίκτη: έρχονται με δικό τους
# πλοίο, το επόμενο απρόσκλητο αφού μετρηθούν FOE_EVERY προσγειώσεις — ποτέ το
# πλοίο αποίκων που καλείς — και ποτέ με λιγότερους από FOE_POP αποίκους. Δύο
# με 20-39, τρεις με 40-59, τέσσερις με 60 και πάνω. Ζουν στις θέσεις 96-99,
# που ως τώρα δεν είχαν κανέναν: χωρίς ανάγκες, χωρίς εργασίες (T_FIGHT), με
# τον ρόλο 8 και τη δική τους κόκκινη φιγούρα.
FOE_POP = 20
FOE_EVERY = 8
AG_FOE0, AG_NFOE = 96, 4
RL_GUARD = 4
RL_FOE = 8
T_FIGHT = 253               # εισβολέας, ή φρουρός στη μάχη: όχι δείκτης εργασίας
F_GUN = 128                 # ο φρουρός έχει όπλο, για πάντα
FOE_HP = 160                # η υγεία του εισβολέα όταν κατεβαίνει
FOE_HIT = 32                # ό,τι παίρνει από έναν άποικο, ανά περιστροφή
HAND_HIT = 32               # ό,τι του παίρνει ένας φρουρός με τα χέρια, δίπλα του
GUN_HIT = 64                # ...και με όπλο, ως έναν κόμβο μακριά


def unbidden(e, kind):
    """Το απρόσκλητο πλοίο (src/econ.asm, ev_ship): οι εισβολείς, αν μετρήθηκαν
    FOE_EVERY προσγειώσεις και ζουν FOE_POP άποικοι· αλλιώς ό,τι έφερε η ζαριά."""
    return SK_FOE if e.alive >= FOE_POP and e.lands >= FOE_EVERY else kind


def land_foes(e, a, node, F_ALIVE, occ):
    """Το in_land (src/ship.asm): 2-4 εισβολείς στην πίστα, έξω, στις πρώτες
    ελεύθερες από τις θέσεις 96-99. Γεννιούνται όπως ο άποικος (born) και
    μετά: εργασία T_FIGHT, υγεία FOE_HP."""
    n = 2 + (e.alive >= 40) + (e.alive >= 60)
    for i in range(AG_FOE0, AG_FOE0 + AG_NFOE):
        if not n:
            break
        if a.flags[i] & F_ALIVE:
            continue
        born(a, i, F_ALIVE, RL_FOE, node, occ)
        a.task[i] = T_FIGHT
        a.health[i] = FOE_HP
        n -= 1


def sol_rollover(e, a, F_ALIVE, F_WORKING, NEED_LOW):
    """Μία φορά ανά sol: τα σερί, και μετά τα ορόσημα (§10.2).

    Ολα τα μετρήματα γίνονται ΕΔΩ και όχι μέσα στα καυτά περάσματα: μία
    σάρωση 128 πρακτόρων ανά 750 περιστροφές δεν φαίνεται πουθενά.
    """
    # «Ολες οι ανάγκες πράσινες» είναι η ένδειξη της ΑΠΟΙΚΙΑΣ, όχι η μπάρα
    # κάθε ατόμου: με ενενήντα αποίκους κάποιος είναι πάντα καθ' οδόν προς
    # την καντίνα, και ένα ορόσημο που δεν πιάνεται ποτέ δεν είναι ορόσημο.
    # ΚΑΙ «ρεύμα» ΣΗΜΑΙΝΕΙ ΓΙΑ ΟΛΟΥΣ: ένα sol που η αποικία πέρασε ρίχνοντας
    # φορτίο (POWER_ESS) δεν είναι πράσινο sol — οι μηχανές της σταμάτησαν.
    green = bool(e.o2_ok and e.power_ok == POWER_ALL
                 and e.stock[S_WATER] and e.stock[S_FOOD])
    # ΟΚΤΩ ΖΩΝΤΑΝΑ ΡΟΜΠΟΤ (βήμα 92), στις θέσεις τους. Ως το 91 «δουλεύουν»
    # (F_WORKING), που δεν το παίρνει ποτέ ρομπότ: το ορόσημο δεν πιανόταν.
    bots = sum(a.flags[i] & F_ALIVE for i in range(AG_BOT0, AG_BOT0 + AG_NBOT))

    # ΚΑΙ ΤΑ ΤΡΙΑ ΣΤΑΜΑΤΟΥΝ ΣΤΟ 255, όπως στον Z80. Ως το βήμα 57 το πράσινο
    # σερί δεν σταματούσε: το 256 δεν χωρούσε στο to_bytes και η αναφορά
    # έσκαγε — κανένα τεστ δεν είχε φτάσει 255 πράσινα sols.
    e.green_sols = min(255, e.green_sols + 1) if green else 0
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
