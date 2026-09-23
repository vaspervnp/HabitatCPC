"""Μια αποικία με ΘΕΣΕΙΣ — ό,τι θα φτιάξει το build mode, φτιαγμένο στο χέρι.

Ως το βήμα 10 οι θόλοι δεν είχαν συντεταγμένες: η προσομοίωση δεν τις κοίταζε
ποτέ και τα δύο πρώτα bytes της εγγραφής έμεναν μηδέν. Ο renderer είναι ο
πρώτος που τις χρειάζεται, άρα και ο πρώτος που τις γεμίζει.

Η διάταξη είναι πλέγμα, και το πλέγμα δεν είναι τεμπελιά: ο διάδρομος πρέπει
να κουμπώσει ΑΚΡΙΒΩΣ πάνω στα δύο σημεία σύνδεσης, και αυτό απαιτεί το κενό
ανάμεσα στα δύο πλαίσια να είναι ακέραιο πλήθος πλακιδίων διαδρόμου:

    κενό σε μισά tiles = SPACING - r(A) - r(B),  μήκος = κενό / 2

Ολες οι ακτίνες (4, 6, 8 μισά tiles) είναι ζυγές, άρα το κενό είναι πάντα ζυγό
και το μήκος ακέραιο. Το ίδιο ισχύει κάθετα: το πλακίδιο είναι 2 μισά tiles και
στους δύο άξονες.
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene as S
import world as W

SPACING = 24                    # μισά tiles ανάμεσα σε κέντρα θόλων = 12 tiles
RADIUS = [4, 6, 8]              # μισά tiles, μισό πλάτος ανά μέγεθος

N_DIR, NE_DIR, E_DIR, SE_DIR, S_DIR, SW_DIR, W_DIR, NW_DIR = range(8)


def _put(rec, i, size, fields):
    for f, v in fields.items():
        rec[i * size + f] = v & 0xFF


def build(cols=4, rows=3, seed=1):
    """Πλέγμα θόλων με διαδρόμους, δομές γύρω, και ο γράφος που προκύπτει."""
    c = S.Colony()
    sizes, rooms = [], []
    # Μεγέθη και δωμάτια σε σταθερή σειρά: η δοκιμή θέλει να ξέρει τι βλέπει.
    pattern_sz = [1, 0, 2, 0, 1, 2, 0, 1, 0, 2, 1, 0]
    pattern_rm = [1, 4, 5, 3, 2, 8, 4, 5, 10, 9, 2, 11]

    d = 0
    grid = {}
    for j in range(rows):
        for i in range(cols):
            sz = pattern_sz[d % len(pattern_sz)]
            rm = pattern_rm[d % len(pattern_rm)]
            hx = (i - (cols - 1) / 2) * SPACING
            hy = (j - (rows - 1) / 2) * SPACING
            assert hx == int(hx) and hy == int(hy), "το SPACING πρέπει να δίνει ακέραια κέντρα"
            # ΕΝΑΣ ΘΟΛΟΣ ΜΙΣΟΧΤΙΣΜΕΝΟΣ, και όχι για ποικιλία: από το βήμα 26
            # ένα εργοτάξιο ζωγραφίζεται ΑΔΕΙΟ — κενό εικονίδιο, καμία μηχανή
            # — παρόλο που η εγγραφή του έχει ήδη και δωμάτιο και μηχανήματα
            # (§6.9). Χωρίς έναν τέτοιο εδώ, ο κανόνας δεν θα περνούσε ποτέ
            # από τη σύγκριση Z80 προς αναφορά του tests/test_object.py.
            state = S.DS_BUILDING if d == 7 else S.DS_ACTIVE
            _put(c.dome, d, S.DOME_REC, {
                S.D_CX: int(hx), S.D_CY: int(hy), S.D_SIZE: sz, S.D_ROOM: rm,
                S.D_STATE: state, S.D_INTEG: 255 if state == S.DS_ACTIVE else 96,
                S.D_OPS: 0})
            grid[(i, j)] = d
            sizes.append(sz)
            rooms.append(rm)
            d += 1
    c.n_dome = d

    # --- μηχανές ή φυτά στις υποδοχές -----------------------------------
    MC = [1, 4, 8]
    for dd in range(c.n_dome):
        n = MC[sizes[dd]]
        for s in range(8):
            c.dome[dd * S.DOME_REC + S.D_MACH + s] = S.NO_MACH
        if rooms[dd] == S.R_GREENHOUSE:
            for s in range(n):
                c.dome[dd * S.DOME_REC + S.D_MACH + s] = (dd + s * 5) % 12
                c.dome[dd * S.DOME_REC + S.D_HEALTH + s] = 200
        else:
            for s in range(n):
                if (dd + s) % 5 == 4:
                    continue                    # μια άδεια υποδοχή εδώ κι εκεί
                m = (dd * 3 + s) % 12
                if m == 0 and sizes[dd] != 0:
                    m = 1                       # machine_rules: οξυγόνο μόνο σε μικρό
                c.dome[dd * S.DOME_REC + S.D_MACH + s] = m
                c.dome[dd * S.DOME_REC + S.D_HEALTH + s] = 200

    # --- διάδρομοι: ανατολικά και νότια, άρα κάθε ζεύγος μία φορά --------
    k = 0
    for j in range(rows):
        for i in range(cols):
            a = grid[(i, j)]
            for di, dj, direction in ((1, 0, E_DIR), (0, 1, S_DIR),
                                      (1, 1, SE_DIR)):
                b = grid.get((i + di, j + dj))
                if b is None:
                    continue
                if direction == SE_DIR and (i + j) % 3:
                    continue                    # μόνο μερικές διαγώνιες
                if direction == SE_DIR:
                    # Το πλέγμα της διαγωνίου είναι κοινό στους δύο θόλους:
                    # SPACING/2 βήματα από κέντρο σε κέντρο, μείον όσα τρώει
                    # ο κάθε δακτύλιος (DIAG_K).
                    steps = SPACING // 2
                    n = steps - S.DIAG_K[sizes[a]] - S.DIAG_K[sizes[b]] + 1
                else:
                    gap = SPACING - RADIUS[sizes[a]] - RADIUS[sizes[b]]
                    assert gap % 2 == 0, "το κενό πρέπει να είναι ζυγό"
                    n = gap // 2
                _put(c.corr, k, S.CORR_REC, {
                    S.C_A: a, S.C_B: b, S.C_DIR: direction,
                    S.C_LEN: n, S.C_STATE: S.DS_ACTIVE})
                k += 1
    c.n_corr = k

    # --- εξωτερικές δομές: γύρω από το πλέγμα ---------------------------
    kinds = [(0, 2), (1, 2), (2, 2), (3, 2), (4, 0), (6, 0), (5, 0), (0, 1)]
    edge = (cols / 2) * SPACING + 10
    n = 0
    for idx, (kind, size) in enumerate(kinds):
        hx = int(-edge if idx % 2 else edge)
        hy = int((idx - len(kinds) / 2) * 10)
        _put(c.struct, n, S.STRUCT_REC, {
            S.S_CX: hx, S.S_CY: hy, S.S_KIND: kind, S.S_SIZE: size,
            S.S_STATE: S.DS_ACTIVE, S.S_INTEG: 255})
        n += 1
    c.n_struct = n
    return c


def adjacency(c):
    """node_deg / node_adj από τους διαδρόμους — ο γράφος του §6.2."""
    deg = bytearray(128)
    adj = bytearray(128 * 8)
    for i in range(c.n_corr):
        if c.c(i, S.C_STATE) == S.DS_EMPTY:
            continue
        a, b = c.c(i, S.C_A), c.c(i, S.C_B)
        if a == 255:
            continue            # συνέχεια διαδρομής: μία ακμή, όχι δύο (§9.4)
        for u, v in ((a, b), (b, a)):
            if deg[u] < 8:
                adj[u * 8 + deg[u]] = v
                deg[u] += 1
    return deg, adj


def stamp(c, plane):
    """Γράφει την κατοχή στο επίπεδο κόσμου: ό,τι πατάει ο θόλος είναι πιασμένο.

    Χωρίς αυτό ο έλεγχος «τα θεμέλια είναι κάτω από τον θόλο» δεν υπάρχει και
    ο renderer θα ζωγράφιζε θόλους πάνω σε λίμνες.
    """
    import scene
    for d in range(c.n_dome):
        if c.d(d, S.D_STATE) == S.DS_EMPTY:
            continue
        sz = c.d(d, S.D_SIZE)
        r = RADIUS[sz] // 2                      # σε tiles
        cx, cy = scene.signed(c.d(d, S.D_CX)), scene.signed(c.d(d, S.D_CY))
        tx0, ty0 = cx // 2 - r, cy // 2 - r
        for ty in range(ty0, ty0 + 2 * r):
            for tx in range(tx0, tx0 + 2 * r):
                if -64 <= tx < 64 and -64 <= ty < 64:
                    b = plane.get(tx, ty)
                    plane.set(tx, ty, (b & ~0x37) | W.FOUNDATION
                              | (W.OCC_STRUCT << 4))
    return plane


def agents(c, n=40):
    """Αποικοι μέσα στους θόλους, στη σειρά γεμίσματος του corr_fill.

    Οι ρόλοι κυκλώνουν και τους οκτώ ώστε να ζωγραφιστεί ΚΑΘΕ φιγούρα: τα
    χρώματα είναι η ταυτότητα σε 6x6 pixel, και μια δοκιμή που δεν τα δείχνει
    όλα δεν ελέγχει τίποτα.
    """
    import entity as E
    ag = E.Agents()
    i = 0
    for d in range(c.n_dome):
        if c.d(d, S.D_STATE) == S.DS_EMPTY:
            continue
        for k in range(min(8, 2 + d % 5)):
            if i >= n:
                break
            ag.flags[i] = E.F_ALIVE | E.F_INDOORS
            ag.role[i] = (i * 3) % 8
            ag.node[i] = d
            ag.slot[i] = E.FILL[k]
            ag.dest[i] = d
            i += 1
    return ag
