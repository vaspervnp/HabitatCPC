"""Ο γράφος κόμβων και οι δύο πίνακες δρομολόγησης (DESIGN.md §6.2, §6.4).

Η αποικία είναι γράφος, όχι πλέγμα. Κόμβος είναι κάθε θόλος, κάθε εξωτερική
δομή, η πλατφόρμα προσγείωσης και ως 8 προσωρινά εργοτάξια — ως 128 συνολικά.
Ακμή είναι ένας διάδρομος ή μια εξωτερική διαδρομή από αεροφράκτη. Βαθμός ως 8,
ένας ανά κατεύθυνση σύνδεσης.

Η δρομολόγηση στο τρέξιμο είναι **μία ανάγνωση πίνακα**:

    NEXTHOP[from][to]   ο επόμενος κόμβος, 255 = απρόσιτος
    DIST[from][to]      απόσταση σε άλματα, 254 = μακριά, 255 = απρόσιτος

Το κόστος πληρώνεται στο χτίσιμο: μια BFS από κάθε πηγή. Αυτό το αρχείο είναι η
ΑΝΑΦΟΡΑ — γράφτηκε από την προδιαγραφή, όχι μεταφρασμένο από τον Z80, ώστε η
σύγκριση των δύο να σημαίνει κάτι.

Δύο σειρές βγαίνουν από την ΙΔΙΑ BFS, και αυτό είναι το κόλπο: όταν η αναζήτηση
φτάνει πρώτη φορά σε γείτονα u της πηγής, ο πρώτος κόμβος της διαδρομής είναι ο
ίδιος ο u· όταν φτάνει σε v μέσω u, κληρονομεί τον πρώτο κόμβο του u. Δεν
χρειάζεται δεύτερο πέρασμα ούτε αποθήκευση διαδρομών.
"""

MAXNODE = 128           # η πλευρά των πινάκων
MAXDEG = 8              # conn_points ανά θόλο
UNREACH = 255           # και στους δύο πίνακες
FAR = 254               # ανώτατη αποθηκεύσιμη απόσταση

ADJ_SIZE = MAXNODE * MAXDEG     # 1.024 bytes
MAT_SIZE = MAXNODE * MAXNODE    # 16.384 bytes — ακριβώς μία τράπεζα


class Graph:
    """Λίστα γειτνίασης σταθερού πλάτους: ο κόμβος n στο adj[n*8 ...].

    Σταθερό πλάτος επειδή ο Z80 θέλει τη διεύθυνση με μία ολίσθηση. Ο βαθμός
    κρατιέται χωριστά ώστε ο βρόχος να μη διαβάζει σκουπίδια.
    """

    def __init__(self, n=0):
        self.n = n                              # πόσοι κόμβοι ζουν
        self.hw = n                             # ανώτατο id + 1 (rt_n του Z80)
        self.deg = bytearray(MAXNODE)
        self.adj = bytearray(ADJ_SIZE)

    def link(self, a, b):
        """Ακμή και προς τις δύο κατευθύνσεις. Οι διάδρομοι δεν έχουν φορά."""
        assert a < self.n and b < self.n and a != b, f"άκυρη ακμή {a}-{b}"
        for x, y in ((a, b), (b, a)):
            if y in self.neighbours(x):
                continue
            assert self.deg[x] < MAXDEG, f"ο κόμβος {x} έχει ήδη {MAXDEG} ακμές"
            self.adj[x * MAXDEG + self.deg[x]] = y
            self.deg[x] += 1

    def neighbours(self, n):
        base = n * MAXDEG
        return list(self.adj[base:base + self.deg[n]])

    def edges(self):
        return sorted({(min(a, b), max(a, b))
                       for a in range(self.n) for b in self.neighbours(a)})


def bfs_row(g, src):
    """Μία πηγή: επιστρέφει (dist_row, next_row), 128 bytes η καθεμία.

    Ουρά με δείκτες, χωρίς αφαιρέσεις — η ουρά δεν ξεπερνά ποτέ τους 128 κόμβους
    γιατί κάθε κόμβος μπαίνει το πολύ μία φορά.
    """
    dist = bytearray([UNREACH] * MAXNODE)
    nxt = bytearray([UNREACH] * MAXNODE)

    dist[src] = 0
    nxt[src] = src                      # «είμαι ήδη εκεί»
    queue = bytearray(MAXNODE)
    queue[0] = src
    head, tail = 0, 1

    while head < tail:
        u = queue[head]
        head += 1
        d = dist[u] + 1
        if d > FAR:
            d = FAR
        for v in g.neighbours(u):
            if dist[v] != UNREACH:
                continue
            dist[v] = d
            # ο πρώτος κόμβος της διαδρομής: ο ίδιος ο v αν είναι γείτονας της
            # πηγής, αλλιώς κληρονομείται από τον u
            nxt[v] = v if u == src else nxt[u]
            queue[tail] = v
            tail += 1

    return dist, nxt


def all_pairs(g):
    """Και οι δύο πίνακες, 16 KB ο καθένας, σε σειρά πηγής.

    Τρέχουν οι πηγές 0 ως hw-1, όπου hw = ανώτατο id + 1. Ενας κόμβος μέσα στο
    διάστημα που δεν υπάρχει είναι απλώς απομονωμένος: dist[s][s]=0,
    next[s][s]=s, όλα τα άλλα απρόσιτα — ακριβώς ό,τι βγάζει μια BFS από μονήρη
    κόμβο. Οι σειρές πάνω από το hw μένουν 255 εδώ και ΑΠΕΙΡΑΧΤΕΣ στον Z80·
    κανείς δεν τις διαβάζει, οπότε η σύγκριση σταματά κι αυτή στο hw.
    """
    dist = bytearray([UNREACH] * MAT_SIZE)
    nxt = bytearray([UNREACH] * MAT_SIZE)
    for s in range(g.hw):
        d, x = bfs_row(g, s)
        dist[s * MAXNODE:(s + 1) * MAXNODE] = d
        nxt[s * MAXNODE:(s + 1) * MAXNODE] = x
    return dist, nxt


def walk(nxt, a, b, limit=MAXNODE):
    """Ακολουθεί το NEXTHOP από το a στο b. Η διαδρομή, ή None."""
    if nxt[a * MAXNODE + b] == UNREACH:
        return None
    path = [a]
    while a != b:
        a = nxt[a * MAXNODE + b]
        if a == UNREACH or len(path) > limit:
            return None
        path.append(a)
    return path


# --- γράφοι για δοκιμή ----------------------------------------------------
# Ο καθένας πιάνει κάτι διαφορετικό. Οι εκφυλισμένοι πρώτοι: ένας κόμβος χωρίς
# ακμές, και δύο συστάδες που δεν βλέπονται ποτέ.

def g_single():
    return Graph(1)


def g_isolated():
    """Τέσσερις κόμβοι, καμία ακμή: όλα απρόσιτα εκτός από τον εαυτό."""
    return Graph(4)


def g_split():
    """Δύο συστάδες. Η αποικία ΞΕΚΙΝΑ έτσι, πριν χτιστεί ο πρώτος διάδρομος."""
    g = Graph(8)
    for a, b in ((0, 1), (1, 2), (2, 0), (4, 5), (5, 6), (6, 7)):
        g.link(a, b)
    return g


def g_line(n=16):
    """Αλυσίδα: η μεγαλύτερη απόσταση, η μακρύτερη ουρά."""
    g = Graph(n)
    for i in range(n - 1):
        g.link(i, i + 1)
    return g


def g_star(n=9):
    """Ένας κόμβος στον μέγιστο βαθμό — το όριο των conn_points."""
    g = Graph(n)
    for i in range(1, n):
        g.link(0, i)
    return g


def g_ring(n=32):
    g = Graph(n)
    for i in range(n):
        g.link(i, (i + 1) % n)
    return g


def g_tree(n=128):
    """Δυαδικό δέντρο 128 κόμβων: συνεκτικό, μικρός βαθμός, βαθιά ουρά."""
    g = Graph(n)
    for i in range(1, n):
        g.link(i, (i - 1) // 2)
    return g


def g_worst(n=MAXNODE):
    """Η ΧΕΙΡΟΤΕΡΗ περίπτωση, και χωρίς τύχη: κάθε κόμβος ακριβώς στον βαθμό 8.

    Κυκλικός γράφος με βήματα 1, 2, 4, 8 — 128 κόμβοι x 8 = 1.024 κατευθυνόμενες
    ακμές, δηλαδή ακριβώς το «1.024 χαλαρώσεις ανά πηγή» του §6.4. Είναι και
    συνεκτικός, οπότε καμία BFS δεν κόβεται νωρίς: κάθε πηγή πληρώνει το πλήρες
    τίμημα. Αν κάτι χωράει σε αυτόν τον γράφο, χωράει σε κάθε αποικία.
    """
    g = Graph(n)
    for i in range(n):
        for step in (1, 2, 4, 8):
            g.link(i, (i + step) % n)
    return g


def g_colony(domes=32, structs=16):
    """Πώς μοιάζει ΣΤΑ ΑΛΗΘΕΙΑ μια αποικία, κι όχι η χειρότερη περίπτωση.

    Οι θόλοι δένονται με διαδρόμους σε αραιό πλέγμα — αλυσίδα με μερικά
    παρακάμψεις, βαθμός 2 ως 4. Οι εξωτερικές δομές κρέμονται από έναν θόλο η
    καθεμία (βαθμός 1): δεν συνδέονται ποτέ με διάδρομο, βγαίνεις και περπατάς.
    """
    n = domes + structs
    g = Graph(n)
    for i in range(domes - 1):
        g.link(i, i + 1)
    for i in range(0, domes - 4, 5):            # μερικές παρακάμψεις
        g.link(i, i + 4)
    for k in range(structs):
        g.link(domes + k, (k * 7) % domes)      # κάθε δομή σε έναν θόλο
    return g


def g_bounded(domes=64, structs=64, corridors=96):
    """Η ΠΡΑΓΜΑΤΙΚΗ χειρότερη περίπτωση — αυτή που επιτρέπουν οι πίνακες.

    Ο g_worst (βαθμός 8 παντού, 512 ακμές) δεν μπορεί να συμβεί: ο πίνακας
    διαδρόμων του §6.1 έχει 96 θέσεις, και οι εξωτερικές δομές δεν συνδέονται
    ποτέ με διάδρομο — κρέμονται από έναν αεροφράκτη η καθεμία. Αρα το ταβάνι
    είναι 128 κόμβοι με 96 + 64 ακμές, δηλαδή μέσος βαθμός 2,5, όχι 8.

    Αυτό αλλάζει τον λογαριασμό: το κόστος της BFS κυβερνιέται από τους κόμβους
    που βγαίνουν από την ουρά (n ανά πηγή, n^2 συνολικά), όχι από τις ακμές.
    """
    n = domes + structs
    g = Graph(n)
    used = 0
    for i in range(domes - 1):                  # αλυσίδα: συνεκτικό
        g.link(i, i + 1)
        used += 1
    k = 0
    while used < corridors:                     # οι υπόλοιποι διάδρομοι
        a, b = k % domes, (k * 5 + 3) % domes
        k += 1
        if a != b and b not in g.neighbours(a) \
           and g.deg[a] < MAXDEG and g.deg[b] < MAXDEG:
            g.link(a, b)
            used += 1
        if k > 5000:
            break
    for j in range(structs):                    # κάθε δομή σε έναν θόλο
        g.link(domes + j, (j * 3) % domes)
    return g


GRAPHS = {
    "single": g_single, "isolated": g_isolated, "split": g_split,
    "line": g_line, "star": g_star, "ring": g_ring,
    "tree": g_tree, "colony": g_colony, "bounded": g_bounded,
    "worst": g_worst,
}
