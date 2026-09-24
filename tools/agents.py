"""Οι άποικοι, διαβασμένοι από έξω: τι κάνει ο καθένας και πόσο του μένει.

ΓΙΑΤΙ ΥΠΑΡΧΕΙ. Το tools/balance.py βλέπει την ΑΠΟΙΚΙΑ — αποθέματα, ρεύμα,
ζωντανούς. Οταν η αποικία πεθαίνει με γεμάτη αποθήκη (§15), η απάντηση δεν
είναι σε κανένα από αυτά: είναι στο πού στέκεται ο καθένας και τι μπάρα του
τελειώνει. Αυτό το αρχείο διαβάζει τα πεδία των πρακτόρων, που ζουν στην
ΤΡΑΠΕΖΑ 6 και δεν φαίνονται από το peek του εξομοιωτή.

ΠΟΥ ΓΡΑΦΕΙ, ΚΑΙ ΓΙΑΤΙ ΕΚΕΙ. Η σκαλωσιά όλων των δοκιμών ζει πάνω από το #3EC0:
από εκεί ως το #4000 είναι το πάτωμα που επιβάλλει το tools/mkdsk.py
(TEST_FLOOR), δηλαδή ο κώδικας του παιχνιδιού δεν φτάνει ποτέ ως εκεί χωρίς να
σταματήσει το build. Το #3E00 — που έμοιαζε άδειο επειδή ήταν άδειο ως το βήμα
26 — είναι σήμερα ΚΩΔΙΚΑΣ, και ένα probe που έγραφε εκεί έσβηνε είκοσι τέσσερα
bytes του παιχνιδιού: ο θόλος έλειπε από την οθόνη και η αιτία δεν ήταν πουθενά
στον renderer. Το ίδιο ξαναέγινε στο βήμα 31 με το tests/plane.asm, και τότε
έγινε έλεγχος αντί για σχόλιο.
"""

BUF = 0x3EC0                            # 64 bytes: 8 πεδία x 8 άποικοι
CODE = 0x3F10                           # η σκαλωσιά, μέσα στα 199 ελεύθερα
NAG = 8                                 # πόσοι άποικοι ανά δείγμα

AG_BASE = 0x6C00                        # G_agent_fields, τράπεζα 6
DOME_BASE = 0x7500                      # G_dome_tbl, τράπεζα 6
DOME_REC = 24
DOME_HEAD = ("cx", "cy", "size", "room", "state", "integ", "power", "ops")
NDOME = 8                               # 8 x 8 bytes = ακριβώς το BUF
# (όνομα, σελίδα, δεύτερο μισό;) — §6.1, δύο πεδία ανά σελίδα
FIELDS = (("flags", 0, 0), ("node", 1, 0), ("dest", 2, 0), ("edge", 2, 1),
          ("task", 3, 1), ("water", 4, 1), ("food", 5, 0), ("health", 6, 0))

F_ALIVE, F_INDOORS, F_ASLEEP, F_SICK, F_IDLE, F_WORKING = 1, 2, 4, 8, 16, 32
NO_TASK = 255


def _code():
    out = [0xF3,                                    # di
           0x01, 0xC6, 0x7F, 0xED, 0x49,            # ld bc,#7FC6 / out (c),c
           0x11, BUF & 255, BUF >> 8]               # ld de,BUF
    for _, page, half in FIELDS:
        src = AG_BASE + page * 256 + (128 if half else 0)
        out += [0x21, src & 255, src >> 8,          # ld hl,src
                0x01, NAG, 0x00,                    # ld bc,NAG
                0xED, 0xB0]                         # ldir
    out += [0x01, 0xC0, 0x7F, 0xED, 0x49,           # πίσω στην τράπεζα 1
            0x18, 0xFE]                             # jr $ — ΧΩΡΙΣ ei: το
    return bytes(out)                               # παιχνίδι τρέχει με di


def snap(m, sym):
    """Ενα δείγμα: λίστα από dict, ένα ανά άποικο 0..NAG-1.

    ΠΕΡΙΜΕΝΕΙ ΤΟΝ ΒΡΟΧΟ ΣΤΗΝ ΑΝΑΜΟΝΗ ΤΟΥ VSYNC πριν κλέψει τον επεξεργαστή.
    Εκεί ζωντανό είναι μόνο το BC και η στοίβα είναι στη βάση της, οπότε το
    «γύρνα στο main_loop» δεν αφήνει τίποτα πίσω. Χωρίς αυτό, το δείγμα έπεφτε
    στη μέση μιας ρουτίνας, η στοίβα μεγάλωνε ένα καρφί σε κάθε δείγμα και
    μετά από εκατό δείγματα η αποικία είχε 217 ζωντανούς.
    """
    top = sym["MAIN_LOOP"]
    # Με βήμα frame το πετυχαίνει μόνο στην x1: στην x4 ο βρόχος ξεπερνά το
    # καρέ και η αναμονή είναι στιγμιαία. Βήμα 50 us, και το παράθυρο πρέπει να
    # καλύπτει την πλήρη σχεδίαση του ml_built — 41 καρέ χωρίς καμία αναμονή.
    for _ in range(24000):
        if top <= m.pc <= top + 12:
            break
        m.run_us(50)
    else:
        raise RuntimeError("ο βρόχος δεν πέρασε από την αναμονή του vsync")
    m.run_code(CODE, _code(), frames=2)
    raw = [m.peek(BUF + i) for i in range(len(FIELDS) * NAG)]
    m.set_pc(sym["MAIN_LOOP"])
    m.run_frames(1)
    return [{name: raw[k * NAG + i] for k, (name, _, _) in enumerate(FIELDS)}
            for i in range(NAG)]


def what(a):
    """Μια λέξη για το τι κάνει αυτή τη στιγμή."""
    if not a["flags"] & F_ALIVE:
        return "νεκρός"
    if a["edge"] != 255:
        return "ταξιδεύει"
    if a["flags"] & F_WORKING:
        return "δουλεύει"
    if a["dest"] != a["node"]:
        return "ξεκινά"
    return "στέκεται"


def _plant_code(page, half, n):
    src = AG_BASE + page * 256 + (128 if half else 0)
    return bytes([0xF3,                                 # di
                  0x01, 0xC6, 0x7F, 0xED, 0x49,         # τράπεζα 6
                  0x21, BUF & 255, BUF >> 8,            # ld hl,BUF
                  0x11, src & 255, src >> 8,            # ld de,πεδίο
                  0x01, n & 255, n >> 8, 0xED, 0xB0,    # ldir
                  0x01, 0xC0, 0x7F, 0xED, 0x49,         # πίσω στην τράπεζα 1
                  0x18, 0xFE])                          # jr $


def plant(m, sym, field, values):
    """Γράφει ΕΝΑ πεδίο για τους αποίκους 0..len(values)-1.

    Το αντίστροφο του snap, και ο λόγος που υπάρχει είναι ο χρόνος: μια μπάρα
    πέφτει από το 255 στο 64 σε ~2.900 frames, και μια δοκιμή που θέλει να δει
    τι κάνει ένας πεινασμένος άποικος δεν έχει λόγο να τα περιμένει.
    """
    name = [f for f in FIELDS if f[0] == field]
    if not name:
        raise KeyError(field)
    _, page, half = name[0]
    m.write_ram(BUF, bytes(values))
    top = sym["MAIN_LOOP"]
    for _ in range(24000):
        if top <= m.pc <= top + 12:
            break
        m.run_us(50)
    else:
        raise RuntimeError("ο βρόχος δεν πέρασε από την αναμονή του vsync")
    m.run_code(CODE, _plant_code(page, half, len(values)), frames=2)
    m.set_pc(top)
    m.run_frames(1)


def _domes_code(n):
    # ΤΟ -13 ΕΙΝΑΙ ΜΕΤΡΗΜΕΝΟ, ΟΧΙ ΕΙΚΑΣΜΕΝΟ: με -12 το djnz προσγειωνόταν στο
    # `ld bc,8` αντί για το `push bc`, κάθε γύρος έκανε ένα pop χωρίς push, και
    # η στοίβα του παιχνιδιού ανέβαινε 16 bytes ανά δείγμα. Το σύμπτωμα ήταν
    # «η αποικία πάγωσε στο sol 1», που μοιάζει με σφάλμα του παιχνιδιού.
    return bytes([0xF3,                                 # di
                  0x01, 0xC6, 0x7F, 0xED, 0x49,         # τράπεζα 6
                  0x21, DOME_BASE & 255, DOME_BASE >> 8,
                  0x11, BUF & 255, BUF >> 8,
                  0x06, n,                              # ld b,n
                  0xC5,                                 # push bc
                  0x01, 0x08, 0x00, 0xED, 0xB0,         # ld bc,8 / ldir
                  0x01, DOME_REC - 8, 0x00, 0x09,       # ld bc,16 / add hl,bc
                  0xC1, 0x10, 0xF3,                     # pop bc / djnz -13
                  0x01, 0xC0, 0x7F, 0xED, 0x49,         # πίσω στην τράπεζα 1
                  0x18, 0xFE])


def domes(m, sym, n=NDOME):
    """Η κεφαλή κάθε εγγραφής θόλου: μέγεθος, δωμάτιο, κατάσταση, ΧΕΙΡΙΣΤΕΣ.

    Το `ops` είναι το κλειδί για την τροφή: μια μηχανή γυρίζει μόνο αν η
    υποδοχή της είναι μικρότερη από αυτό (§6.5).
    """
    top = sym["MAIN_LOOP"]
    for _ in range(24000):
        if top <= m.pc <= top + 12:
            break
        m.run_us(50)
    else:
        raise RuntimeError("ο βρόχος δεν πέρασε από την αναμονή του vsync")
    m.run_code(CODE, _domes_code(n), frames=2)
    raw = [m.peek(BUF + i) for i in range(8 * n)]
    m.set_pc(top)
    m.run_frames(1)
    return [dict(zip(DOME_HEAD, raw[d * 8:d * 8 + 8])) for d in range(n)]
