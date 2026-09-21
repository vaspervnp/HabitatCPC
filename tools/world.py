"""Το επίπεδο κόσμου: 128x128 bytes, ένα byte ανά tile (DESIGN.md §3.5).

Ένα byte κρατά ό,τι δεν ζει σε λίστα αντικειμένων:

    bits 0-2   κλάση εδάφους
    bit  3     πόρος    (βουνό: φλέβα · νερό: βάθος · χώμα: γόνιμο)
    bits 4-5   κατοχή   (0 ελεύθερο · 1 δομή · 2 διάδρομος · 3 δεσμευμένο)
    bits 6-7   decor    4 παραλλαγές, και η φάση κίνησης του νερού

Η παραλλαγή autotile ΔΕΝ αποθηκεύεται — υπολογίζεται τη στιγμή της σχεδίασης
από τους τέσσερις ορθογώνιους γείτονες. Αυτό απελευθερώνει 4 bits και σημαίνει
ότι μια αλλαγή εδάφους δεν χρειάζεται να διορθώσει τους γείτονές της.
"""

W = 128                     # tiles ανά πλευρά
SIZE = W * W                # 16.384 — ακριβώς μία τράπεζα
HALF = W // 2               # οι συντεταγμένες πάνε -64..+63

GROUND, DUST, ROCK, MOUNTAIN, WATER, DEEPWATER, CRATER, FOUNDATION = range(8)

CLASS_NAMES = ["ground", "dust", "rock", "mountain",
               "water", "deepwater", "crater", "foundation"]

# Το βαθύ νερό μετράει ΩΣ ΝΕΡΟ στον έλεγχο γειτονιάς (SPRITES.md §3): αλλιώς
# κάθε λίμνη αποκτά ακτή γύρω από το βαθύ της κομμάτι, στη μέση του νερού.
FAMILY = [GROUND, DUST, ROCK, MOUNTAIN, WATER, WATER, CRATER, FOUNDATION]

OCC_FREE, OCC_STRUCT, OCC_CORRIDOR, OCC_BLOCKED = range(4)


def byte(cls, res=0, occ=OCC_FREE, decor=0):
    return (cls & 7) | ((res & 1) << 3) | ((occ & 3) << 4) | ((decor & 3) << 6)


def cls_of(b):
    return b & 7


def res_of(b):
    return (b >> 3) & 1


def decor_of(b):
    return (b >> 6) & 3


def index(tx, ty):
    """Συντεταγμένες -64..+63 -> μετατόπιση 0..16383."""
    return ((ty + HALF) << 7) | (tx + HALF)


class Plane:
    def __init__(self, fill=None):
        self.buf = bytearray(SIZE) if fill is None else bytearray([fill]) * SIZE

    def get(self, tx, ty):
        return self.buf[index(tx, ty)]

    def set(self, tx, ty, v):
        self.buf[index(tx, ty)] = v

    # -- autotile ---------------------------------------------------------
    def autotile(self, tx, ty):
        """bit0=N, bit1=E, bit2=S, bit3=W· το bit μπαίνει όταν ο γείτονας
        είναι ΙΔΙΑΣ ΟΙΚΟΓΕΝΕΙΑΣ. 0 = μεμονωμένο, 15 = εσωτερικό.

        Στις γραμμές ±64 ο γείτονας εκτός κόσμου διαβάζεται ως ο ΕΑΥΤΟΣ του
        tile, ώστε να μη ζωγραφιστεί ακτή στην άκρη του κόσμου. Η μηχανή κάνει
        το ίδιο, με έλεγχο ανά ΣΕΙΡΑ και όχι ανά tile.
        """
        me = FAMILY[cls_of(self.get(tx, ty))]
        m = 0
        for bit, (dx, dy) in enumerate(((0, -1), (1, 0), (0, 1), (-1, 0))):
            nx, ny = tx + dx, ty + dy
            if ny < -HALF or ny >= HALF:
                ny = ty                      # πάνω/κάτω άκρη: ο εαυτός του
            if nx < -HALF or nx >= HALF:
                nx = tx                      # αριστερά/δεξιά άκρη
            if FAMILY[cls_of(self.get(nx, ny))] == me:
                m |= 1 << bit
        return m

    def variant(self, tx, ty, variants):
        """variants = ο πίνακας tile_variants των assets.

        Κλάση με 16 παραλλαγές είναι autotiled· οτιδήποτε άλλο παίρνει την
        παραλλαγή του από τα bits decor. Ο κανόνας βγαίνει από τα ΔΕΔΟΜΕΝΑ,
        δεν χρειάζεται δεύτερος πίνακας.
        """
        b = self.get(tx, ty)
        c = cls_of(b)
        if variants[c] == 16:
            return self.autotile(tx, ty)
        return decor_of(b) & (variants[c] - 1)


def test_world(seed=0x1234):
    """Συνθετικός κόσμος για τις δοκιμές — ΟΧΙ η γεννήτρια του §5.

    Φτιάχνεται ώστε να χτυπήσει κάθε περίπτωση που μπορεί να σπάσει: και οι
    οκτώ κλάσεις, λίμνη με βαθύ κέντρο (το βαθύ πρέπει να ΜΗΝ κόβει ακτή),
    βουνό με φλέβα, και έδαφος που αγγίζει και τις τέσσερις άκρες του κόσμου.
    """
    p = Plane()
    rnd = seed

    def nxt():
        nonlocal rnd
        rnd = (rnd * 1103515245 + 12345) & 0xFFFFFFFF
        return (rnd >> 16) & 0xFF

    # βάση: χώμα/σκόνη/βράχος με τυχαίο decor
    for ty in range(-HALF, HALF):
        for tx in range(-HALF, HALF):
            r = nxt()
            c = (GROUND, GROUND, DUST, ROCK)[r & 3]
            p.set(tx, ty, byte(c, decor=(r >> 4) & 3))

    # χείλος βουνού — γι' αυτό η άκρη του κόσμου δεν φαίνεται ποτέ (§5.5)
    for ty in range(-HALF, HALF):
        for tx in range(-HALF, HALF):
            if max(abs(tx), abs(ty)) >= 57:
                p.set(tx, ty, byte(MOUNTAIN, decor=nxt() & 3))

    def blob(cx, cy, r, c, res=0):
        for ty in range(cy - r, cy + r + 1):
            for tx in range(cx - r, cx + r + 1):
                if -HALF <= tx < HALF and -HALF <= ty < HALF:
                    if (tx - cx) ** 2 + (ty - cy) ** 2 <= r * r:
                        p.set(tx, ty, byte(c, res=res, decor=nxt() & 3))

    blob(-8, -4, 6, WATER)            # λίμνη
    blob(-8, -4, 3, DEEPWATER)        # με βαθύ κέντρο
    blob(9, 5, 5, MOUNTAIN, res=1)    # βουνό με φλέβα
    blob(-14, 8, 3, CRATER)
    blob(6, -9, 2, FOUNDATION)
    return p
