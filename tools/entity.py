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

MAXAGENT = 128              # η πλευρά των πινάκων (§6.1: 80 άποικοι + 16 ρομπότ)
NSLOT = 8                   # θέσεις δαχτυλιδιού ανά κόμβο
NO_EDGE = 255
NO_SLOT = 255

# σειρά γεμίσματος θέσεων — από το corr_fill των assets, ώστε οι άνθρωποι να
# μη μοιάζουν στοιβαγμένοι
FILL = [0, 4, 2, 6, 1, 5, 3, 7]

# πεδία, με τη σειρά που κάθονται στη μνήμη· το i-οστό στη σελίδα i//2,
# μετατόπιση (i%2)*128
FIELDS = ["flags", "role", "node", "slot", "dest", "edge", "progress", "task",
          "o2", "water", "food", "sleep", "health", "morale", "skill", "spare"]

F_ALIVE, F_INDOORS, F_ASLEEP, F_SICK, F_IDLE = 1, 2, 4, 8, 16

# ρόλοι (§6.1) και ταχύτητα ανά βήμα κίνησης. Τα ρομπότ είναι γρηγορότερα.
WORKER, ENGINEER, BIOLOGIST, MEDIC, GUARD, BOT_CONSTR, BOT_CARRY, BOT_DRILL = range(8)
ROLE_SPEED = [40, 40, 36, 44, 48, 56, 64, 52]


class Agents:
    """Οι 128 πράκτορες ως 16 πίνακες των 128 bytes."""

    def __init__(self):
        for f in FIELDS:
            setattr(self, f, bytearray(MAXAGENT))
        for i in range(MAXAGENT):
            self.edge[i] = NO_EDGE
            self.slot[i] = NO_SLOT

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


def move_one(a, i, g, nexthop, occ):
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
        s = claim(occ, dst)
        if s == NO_SLOT:
            # ο κόμβος είναι γεμάτος — περιμένει στο σωλήνα, ξαναδοκιμάζει
            a.progress[i] = 255
            return
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
            release(occ, a.node[i], a.slot[i])
            a.slot[i] = NO_SLOT
            a.edge[i] = k
            a.progress[i] = 0
            return
    # το NEXTHOP δείχνει γείτονα που δεν υπάρχει στη λίστα: ο πίνακας είναι
    # μπαγιάτικος ΚΑΙ λάθος. Δεν συμβαίνει· αν συμβεί, δεν κουνιέται.


def move_slice(a, g, nexthop, occ, first, count):
    """Η φέτα του §7.2: count πράκτορες από τον first, με αύξουσα σειρά."""
    for k in range(count):
        move_one(a, (first + k) & (MAXAGENT - 1), g, nexthop, occ)


# --- φθορά αναγκών (§6.6), η δεύτερη πραγματική εργασία του τροχού ---------
NEED_FIELDS = ["o2", "water", "food", "sleep"]
NEED_RATE = [3, 2, 1, 2]


def decay_slice(a, first, count):
    """Οι ανάγκες πέφτουν, και δεν γυρίζουν ποτέ κάτω από το μηδέν."""
    for k in range(count):
        i = (first + k) & (MAXAGENT - 1)
        if not a.flags[i] & F_ALIVE:
            continue
        for f, r in zip(NEED_FIELDS, NEED_RATE):
            arr = getattr(a, f)
            arr[i] = arr[i] - r if arr[i] > r else 0


# --- ο τροχός (§7.2) ------------------------------------------------------
WH_SLOTS = 16
WH_MOVE_N = 12              # πράκτορες ανά θέση κίνησης
WH_DECAY_N = 32             # πράκτορες ανά θέση φθοράς


class Sim:
    """Ο,τι χρειάζεται ένα frame προσομοίωσης, και τίποτε άλλο."""

    def __init__(self, g, nexthop):
        self.a = Agents()
        self.g = g
        self.nexthop = nexthop
        self.occ = bytearray(G.MAXNODE)
        self.slot = 0

    def tick(self):
        """Ενα frame: μία θέση του τροχού. Η δρομολόγηση δεν είναι θέση."""
        s = self.slot
        self.slot = (s + 1) & (WH_SLOTS - 1)
        if s < 8:
            move_slice(self.a, self.g, self.nexthop, self.occ,
                       s * WH_MOVE_N, WH_MOVE_N)
        elif s < 11:
            decay_slice(self.a, (s - 8) * WH_DECAY_N, WH_DECAY_N)
        # 11-15: παραγωγή, ισοζύγιο, εργασίες, ελεύθερη, συμβάντα — δεν έχουν
        # γραφτεί ακόμη, ούτε εδώ ούτε στον Z80.


def populate(sim, n_agents=96, seed=7):
    """Μια αρχική κατάσταση που ασκεί τις γωνίες: γεμάτοι κόμβοι, απρόσιτοι
    προορισμοί, νεκροί ανάμεσα στους ζωντανούς, όλοι οι ρόλοι."""
    a, g = sim.a, sim.g
    x = seed
    for i in range(n_agents):
        x = ((x * 75) + 74) & 0xFFFF
        a.role[i] = (x >> 3) & 7
        a.flags[i] = F_ALIVE if (x & 31) else 0      # ~3% νεκροί εξαρχής
        node = (x >> 6) % g.n
        a.node[i] = node
        a.dest[i] = ((x >> 9) * 7 + i) % g.n
        a.o2[i] = 100 + (x & 63)
        a.water[i] = 90 + ((x >> 2) & 63)
        a.food[i] = 80 + ((x >> 4) & 63)
        a.sleep[i] = 70 + ((x >> 5) & 63)
        a.health[i] = 200
        a.morale[i] = 150
        if a.flags[i] & F_ALIVE:
            a.slot[i] = claim(sim.occ, node)          # μπορεί να γυρίσει 255
    return sim
