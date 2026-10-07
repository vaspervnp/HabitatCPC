#!/usr/bin/env python3
"""Στρώνει τα assets στις τράπεζες.

Βγάζει τις εικόνες των τραπεζών, τις διευθύνσεις για τον assembler, και έναν
λογαριασμό που διαβάζεται. **Σκάει** αν κάτι δεν χωρέσει — αυτός είναι ο λόγος
που υπάρχει: το DESIGN.md §4.2 είναι χαρτί μέχρι να το μετρήσει κάποιος.

Η τράπεζα 2 ήταν σχεδιασμένη να κάνει δύο δουλειές: σελίδα οθόνης του HUD ΚΑΙ
αποθήκη για τα μικρά γραφικά, με τα γραφικά στριμωγμένα σε οκτώ αρένες ανάμεσα
στις γραμμές του HUD. Το tests/test_camera.py έδειξε ότι η τομή δύο σελίδων δεν
γίνεται — ο CRTC κλειδώνει τη διεύθυνση έναρξης μία φορά ανά frame — οπότε το
HUD ζει πλέον στη σελίδα του κάδρου και η τράπεζα 2 είναι ΕΠΙΠΕΔΑ 16 KB.

Το κέρδος δεν είναι μόνο απλότητα: οι αρένες άφηναν 397 bytes ελεύθερα αλλά
κομματιασμένα σε οκτώ κουτιά, με επτά από αυτά γεμάτα. Τώρα είναι συνεχόμενα.
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sprites import load_map, load_bin, ROOT
import buttons

TEXT_MAX = 2080                 # = TEXT_MAX του src/uitext.asm (assert εκεί)

# --- γεωμετρία ------------------------------------------------------------
PAGE2_BASE  = 0x8000                # τράπεζα 2: επίπεδη, πάντα ορατή
WINDOW_BASE = 0x4000                # όπου φαίνονται οι τράπεζες 4-7

BANK_SIZE   = 0x4000
# Ο πίνακας DIST είναι κόμβοι x 128 bytes. Με 96 κόμβους (DESIGN §4.2) πιάνει
# 12 KB από τα 16 της τράπεζας 1, και τα τελευταία 4 KB μένουν — εκεί πάνε τα
# εικονίδια δωματίων m και l, που ελευθερώνουν ισόποσο χώρο ΚΩΔΙΚΑ στην 2.
# Η τράπεζα 1 είναι η ΠΡΟΕΠΙΛΟΓΗ του παραθύρου, οπότε δεν κοστίζει σελίδα σε
# κανέναν εκτός από το πέρασμα αντικειμένων, που έχει την 6 μέσα.
MAX_NODE = 96
BANK1_BASE = WINDOW_BASE + MAX_NODE * 128
BANK1_SIZE = BANK_SIZE - MAX_NODE * 128
# ΚΑΙ Η ΤΡΑΠΕΖΑ 5 (βήμα 85): ο πίνακας NEXTHOP είναι κι αυτός κόμβοι x 128, και
# πάνω του το ευρετήριο αντικειμένων (src/const.asm, OI_END = #73C0). Από το
# #7400 ως το τέλος, 3 KB που δεν χρησιμοποιούσε κανείς: εκεί πάνε οι μηχανές,
# και τα 1.584 bytes τους γίνονται χώρος ΚΩΔΙΚΑ στην τράπεζα 2. Το const.asm
# ελέγχει ότι το ευρετήριο δεν φτάνει ως εδώ.
BANK5_BASE = 0x7400
BANK5_SIZE = 0x8000 - BANK5_BASE


class Fail(SystemExit):
    pass


class Run:
    """Ένα κομμάτι που πρέπει να μείνει ΕΝΙΑΙΟ."""

    def __init__(self, name, size, data=None, align=1, note=""):
        self.name, self.size, self.data = name, size, data
        self.align, self.note = align, note
        self.addr = None
        self.bin = None
        self.members = []       # [(όνομα sprite, μετατόπιση μέσα στο run)]
        if data is not None and len(data) != size:
            raise Fail(f"{name}: δεδομένα {len(data)} != μέγεθος {size}")

    def __repr__(self):
        return f"<{self.name} {self.size}B @{self.addr and hex(self.addr)}>"


# --- κατανομή -------------------------------------------------------------

def pack_flat(runs, base, size, label):
    """Γραμμική τράπεζα: σειριακά, με σεβασμό στη στοίχιση."""
    a = base
    for r in runs:
        if r.align > 1:
            a = (a + r.align - 1) & ~(r.align - 1)
        r.addr = a
        a += r.size
    used = a - base
    if used > size:
        raise Fail(f"{label}: {used} bytes σε χώρο {size} — ξεχειλίζει κατά {used - size}")
    return used





# --- η διάταξη ------------------------------------------------------------

# Τα κελιά της μπάρας του HUD (§9.2), ως γλύφοι Mode 1 μετά τον χαρακτήρα 127.
# Πέντε γραμμές (1-5), όσο το σώμα των κεφαλαίων: η 0, η 6 και η 7 μένουν κενές
# όπως στα γράμματα. Η άδεια μπάρα είναι περίγραμμα, πάνω και κάτω: δίπλα-δίπλα
# τα κελιά της κάνουν ένα κούφιο ορθογώνιο.
def _cell(top, mid, bot):
    return bytes([0, top, mid, mid, mid, bot, 0, 0])


HUD_CELLS = (bytes(8)                      # #80 κενό
             + _cell(0xF0, 0xF0, 0xF0)     # #81 pen 1 — κόκκινο, λίγο
             + _cell(0x0F, 0x0F, 0x0F)     # #82 pen 2 — πράσινο, γεμάτο
             + _cell(0xFF, 0xFF, 0xFF)     # #83 pen 3 — λευκό
             + _cell(0xFF, 0x00, 0xFF))    # #84 άδειο


def mode1_font(m0):
    """Η γραμματοσειρά 4x8 του Mode 0 (2 bytes ανά γραμμή) σε Mode 1 (1 byte).

    Στο Mode 0 το αριστερό pixel ενός byte είναι τα bits 7,5,3,1 και το δεξί
    τα 6,4,2,0· στο Mode 1 το pixel i (0-3) είναι τα bits 7-i και 3-i, και
    pen 3 σημαίνει και τα δύο. Μελάνι = οποιοδήποτε pen εκτός από το 0."""
    out = bytearray()
    for k in range(0, len(m0), 2):
        px = [m0[k] & 0xAA, m0[k] & 0x55, m0[k + 1] & 0xAA, m0[k + 1] & 0x55]
        out.append(sum(0x88 >> i for i in range(4) if px[i]))
    return bytes(out)


def build_runs(smap, blob):
    def spr(name):
        s = smap.get(name)
        if s is None:
            raise Fail(f"λείπει sprite: {name}")
        return Run(name, s.size, blob[s.off:s.off + s.size])

    def group(name, names):
        """Ενιαίο κομμάτι από διαδοχικά sprites — για ό,τι δεικτοδοτείται με
        πολλαπλασιασμό και ΠΡΕΠΕΙ να είναι συνεχόμενο."""
        data, members = b"", []
        for n in names:
            s = smap[n]
            members.append((n, len(data)))
            data += blob[s.off:s.off + s.size]
        r = Run(name, len(data), data)
        r.members = members
        return r

    TERRAIN = ["ground", "dust", "rock", "mountain", "water",
               "deepwater", "crater", "foundation"]
    ROOMS = ["empty", "control", "quarters", "canteen", "oxygen",
             "greenhouse", "storage", "airlock", "factory", "lab",
             "medbay", "lounge"]
    # Δώδεκα, όχι δέκα: η παράδοση τέχνης πρόσθεσε `beds` και `medstore` στο
    # ιατρείο (θέσεις 10 και 11). Οι δέκα πρώτοι δείκτες δεν άλλαξαν.
    MACH = ["oxygen", "iron", "bioplastic", "weapons", "processors",
            "robots", "food", "spares", "medical", "vitromeat",
            "beds", "medstore"]
    PLANTS = ["peas", "rice", "potatoes", "wheat", "maize", "tomatoes",
              "lettuce", "onions", "radishes", "mushrooms", "medicinal", "tree"]
    DIRS = ["n", "ne", "e", "se", "s", "sw", "w", "nw"]
    STRUCTS = ([f"{k}_{s}" for k in ("solar", "turbine", "collector", "extractor")
                for s in ("s", "m", "l")] + ["mine", "airlock", "pad", "ship"])

    arena, bank1, bank5, bank6, bank7 = [], [], [], [], []
    ptr = {}            # όνομα πίνακα -> λίστα ονομάτων run, για 2ο πέρασμα

    # --- έδαφος: συνεχόμενο ΑΝΑ ΚΛΑΣΗ μόνο (tile_ptr[class] + variant*64) ---
    for cls in TERRAIN:
        names = sorted([n for n in smap if n.startswith(f"tile_{cls}_")],
                       key=lambda n: int(n.rsplit("_", 1)[1]))
        arena.append(group(f"tile_{cls}", names))
    arena.append(group("ore_overlay", sorted(n for n in smap if n.startswith("ore_overlay"))))
    ptr["tile_ptr"] = [f"tile_{c}" for c in TERRAIN]

    # --- εικονίδια δωματίων -------------------------------------------------
    # Το SPRITES.md §6 λέει `room_icons_l + type*ICON_L_SZ`, που απαιτεί 2.400
    # bytes ΣΥΝΕΧΟΜΕΝΑ — δεν χωράνε σε αρένα 1.648. Με πίνακα δεικτών κάθε
    # εικονίδιο μπαίνει όπου βρεθεί χώρος, και η αναζήτηση είναι ΚΑΙ πιο
    # γρήγορη: το *200 και το *72 δεν είναι ολισθήσεις.
    # Τα m και l πάνε στην ΤΡΑΠΕΖΑ 1, πάνω από τον πίνακα DIST· τα s μένουν
    # στη 2. Οι πίνακες δεικτών μένουν και οι τρεις στη 2 — διαβάζονται όσο το
    # παράθυρο έχει την 6 μέσα, και η 2 φαίνεται πάντα.
    for size in ("s", "m", "l"):
        names = [f"icon_{size}_{r}" for r in ROOMS]
        dest = arena if size == "s" else bank1
        for n in names:
            dest.append(spr(n))
        ptr[f"icon_{size}_ptr"] = names

    # --- μηχανές: *132, ίδιο σκεπτικό ---------------------------------------
    # ΣΤΗΝ ΤΡΑΠΕΖΑ 5 από το βήμα 85, πάνω από το ευρετήριο. Τις ζωγραφίζει μόνο
    # το πέρασμα αντικειμένων (om_prep, src/object.asm), που σελιδοποιεί ήδη
    # την 7 για τα φυτά του θερμοκηπίου στις ίδιες υποδοχές: τώρα σελιδοποιεί
    # την 5 για τις μηχανές. Ο πίνακας δεικτών μένει στη 2.
    for m in MACH:
        bank5.append(spr(f"mach_{m}"))
    ptr["mach_ptr"] = [f"mach_{m}" for m in MACH]

    # --- διάδρομοι, συνδέσεις, γραμματοσειρά --------------------------------
    for n in ("corr_h", "corr_v", "corr_dr", "corr_dl"):
        arena.append(spr(n))
    arena.append(group("connectors", [f"conn_{d}" for d in DIRS]))   # dir*32
    # Η ΓΡΑΜΜΑΤΟΣΕΙΡΑ ΕΦΥΓΕ ΑΠΟ ΕΔΩ ΣΤΟ ΒΗΜΑ 33 — δες την τράπεζα 7 πιο κάτω.

    # --- πίνακες που έρχονται έτοιμοι από τα assets -------------------------
    # Το tile_base ΔΕΝ περνάει: κρατά μετατοπίσεις από την αρχή ενός ενιαίου
    # μπλοκ που πλέον δεν υπάρχει. Το ξαναφτιάχνουμε ως tile_ptr.
    for n in ("corr_slots", "corr_fill", "plant_class", "machine_count",
              "machine_slots", "machine_rules", "room_machines",
              "interior_ofs", "tile_variants",
              "planet_pens", "conn_points", "struct_dims", "palette_fw"):
        arena.append(spr(n))

    # struct_ptr[kind*4 + size]: τέσσερις θέσεις ανά είδος, με κενά. Το ορυχείο,
    # ο αεροθάλαμος, η πλατφόρμα και το σκάφος υπάρχουν σε ΕΝΑ μέγεθος — το 0 —
    # και οι άλλες τρεις θέσεις τους είναι μηδέν, όπως και στο struct_dims.
    sp = []
    for k in ("solar", "turbine", "collector", "extractor"):
        sp += [f"{k}_{s}" for s in ("s", "m", "l")] + [None]
    for k in ("mine", "airlock", "pad", "ship"):
        sp += [k, None, None, None]
    ptr["struct_ptr"] = sp

    # --- παραγόμενοι πίνακες δεικτών ---------------------------------------
    for tab, names in ptr.items():
        if tab != "plant_ptr":
            arena.append(Run(tab, len(names) * 2, bytes(len(names) * 2),
                             note="παράγεται"))

    # Το ui_cursor (256 bytes, «δεν έχει παραδοθεί») ΕΦΥΓΕ στο βήμα 33: ο
    # κέρσορας είναι το πλαίσιο του φαντάσματος (gh_box) από το βήμα 6b, κανείς
    # δεν διάβασε ποτέ αυτά τα bytes, και κάθονταν πριν από τρεις πίνακες
    # ευθυγραμμισμένους σε σελίδα — άρα κόστιζαν ακριβώς 256 bytes κώδικα.

    # --- συνταγές μηχανών: στατικά δεδομένα, ένα πέρασμα πίνακα (§6.5) ---
    import econ
    rec = bytearray()
    for r in econ.RECIPE:
        rec += bytes(x & 0xFF for x in r)
    arena.append(Run("recipes", len(rec), bytes(rec), note="παράγεται από econ.py"))
    # «θέλει χειριστή;» ως πίνακας: ο πίνακας εργασιών το ρωτά για κάθε
    # μηχανή κάθε θόλου, και ο πολλαπλασιασμός x10 για τη συνταγή ήταν το
    # ακριβότερο κομμάτι της δημοσίευσης.
    arena.append(Run("mach_op", len(econ.RECIPE),
                     bytes(1 if r[9] & econ.MF_OPERATOR else 0
                           for r in econ.RECIPE), note="παράγεται από econ.py"))

    # Η οικονομία και ο πίνακας εργασιών ΕΚΤΟΣ παραθύρου, για δύο λόγους:
    # ο πίνακας εργασιών διαβάζει το DIST (τράπεζα 1) ενώ αναθέτει, και τα
    # αποθέματα τα διαβάζει το HUD σε κάθε frame. Ο,τι διαβάζεται μαζί με
    # σελιδοποιημένο πίνακα δεν μπορεί να ζει στο παράθυρο — το ίδιο μάθημα
    # με τον πάγκο της BFS.
    arena.append(Run("econ_state", econ.ECON_BYTES, None,
                     note="ΔΕΣΜΕΥΣΗ — αποθέματα και ροές"))
    arena.append(Run("job_tbl", 32 * 5, None, note="ΔΕΣΜΕΥΣΗ — 32 εργασίες"))
    arena.append(Run("room_n", 12, None, note="ΔΕΣΜΕΥΣΗ — θόλοι ανά είδος δωματίου"))
    arena.append(Run("room_list", 12 * 8, None, note="ΔΕΣΜΕΥΣΗ — ως 8 ο καθένας"))

    # --- ο γράφος κόμβων και ο πάγκος της BFS -------------------------------
    # Εδώ, και όχι στην τράπεζα 6, για έναν λόγο που δεν συγχωρεί: η BFS γράφει
    # τις γραμμές της στις τράπεζες 1 και 5, άρα το παράθυρο &4000 αλλάζει μέσα
    # στη ρουτίνα. Ο,τι διαβάζει ή γράφει η BFS πρέπει να είναι ΕΚΤΟΣ παραθύρου.
    # Η τράπεζα 2 είναι πάντα ορατή — και έχει χώρο από το βήμα 5.
    arena.append(Run("rt_nodes", 256, None, align=256,
                     note="ΔΕΣΜΕΥΣΗ — node_deg[0..127] + rt_queue[128..255]"))
    arena.append(Run("rt_row", 256, None, align=256,
                     note="ΔΕΣΜΕΥΣΗ — rt_dist[0..127] + rt_next[128..255]"))
    arena.append(Run("node_adj", 1024, None, align=256,
                     note="ΔΕΣΜΕΥΣΗ — 128 κόμβοι x 8 γείτονες"))
    # Η κρυφή μνήμη του HUD: ένας κωδικός ανά κελί για τις σειρές 0-2 (§9.2).
    # Χωρίς αυτήν κάθε επανασχεδίαση ξαναγράφει και τα 120 κελιά — 2,55 frames
    # μετρημένα — ενώ αλλάζουν τρία ή τέσσερα.
    #
    # ΤΕΛΕΥΤΑΙΑ ΕΠΙΤΗΔΕΣ, μετά τον γράφο: το αρχείο σωσίματος γράφει τα 2 KB
    # ΑΜΕΣΩΣ ΚΑΤΩ από αυτήν ως ένα κομμάτι (§11, SV_STATE στο src/save.asm), και
    # ένα assert εκεί ελέγχει ότι το econ_state χωρά μέσα. Η κρυφή μνήμη δεν
    # σώζεται — ξαναχτίζεται μόλις αλλάξει κελί.
    arena.append(Run("hud_shadow", 120, None,
                     note="ΔΕΣΜΕΥΣΗ — ένας κωδικός ανά κελί HUD"))

    # --- τράπεζα 6 ----------------------------------------------------------
    bank6.append(Run("flip_mode0", 256, blob[smap["flip_mode0"].off:
                                             smap["flip_mode0"].off + 256],
                     align=256, note="ΠΡΕΠΕΙ σε σελίδα"))
    for stem in ("dome", "ring"):
        for size in ("s", "m", "l"):
            bank6.append(spr(f"{stem}_{size}_nw"))
    bank6.append(group("corr_slot_gfx",
                       sorted([n for n in smap if n.startswith("slot_")],
                              key=lambda n: smap[n].off)))
    # --- πίνακες οντοτήτων: δομή-από-πίνακες, σελιδοποιημένη (§6.1) ---
    # Το agent_fields ΠΡΕΠΕΙ σε σελίδα: η ανάγνωση πεδίου είναι `ld h,σελίδα /
    # ld l,id`, και χωρίς στοίχιση δεν υπάρχει τέτοια ανάγνωση.
    bank6.append(Run("agent_fields", 2048, None, align=256,
                     note="ΔΕΣΜΕΥΣΗ — 16 πεδία x 128, ΠΡΕΠΕΙ σε σελίδα"))
    bank6.append(Run("node_occ", 256, None, align=256,
                     note="ΔΕΣΜΕΥΣΗ — μάσκες θέσεων[0..127], 128 ελεύθερα"))
    # 24 bytes ο θόλος, όχι 16: το machine_count των assets δίνει 8 υποδοχές
    # στον μεγάλο θόλο, και το §6.1 του έδινε machines[4] health[4].
    bank6.append(Run("dome_tbl", 64 * 24, None, note="ΔΕΣΜΕΥΣΗ — 64 θόλοι x 24"))

    bank6.append(Run("struct_tbl", 32 * 8, None, note="ΔΕΣΜΕΥΣΗ — 32 δομές"))
    bank6.append(Run("corr_tbl", 96 * 5, None, note="ΔΕΣΜΕΥΣΗ — 96 διάδρομοι"))
    # Το seed του κόσμου. Το γράφει η ΓΕΝΝΗΤΡΙΑ, που είναι ξεχωριστό φόρτωμα και
    # σβήνεται μετά· χωρίς αυτά τα τέσσερα bytes το παιχνίδι δεν ξέρει από ποιο
    # seed βγήκε ο κόσμος του, και το αρχείο σωσίματος (§11) δεν έχει τι να
    # γράψει στην κεφαλίδα του. Η τράπεζα 6 φορτώνεται ΠΡΙΝ τρέξει η γεννήτρια
    # και δεν ξαναγράφεται.
    bank6.append(Run("worldinfo", 4, None,
                     note="ΔΕΣΜΕΥΣΗ — seed, πλανήτης, έκδοση γεννήτριας"))
    # Η κρυφή μνήμη φιγούρων ΗΡΘΕ ΕΔΩ από την τράπεζα 2 (βήμα 30). Τη διαβάζει
    # και τη γράφει ΜΟΝΟ το πέρασμα αντικειμένων, που έχει ήδη σελιδοποιημένη
    # την τράπεζα 6 για τα τεταρτημόρια και τις φιγούρες — άρα δεν χρειάζεται
    # να είναι εκτός παραθύρου, και τα 512 bytes της τράπεζας 2 που ελευθερώνει
    # είναι κώδικας που φεύγει από την τράπεζα 0, η μόνη σπάνια (§4.2).
    bank6.append(Run("dome_fig", 64 * 8, None,
                     note="ΔΕΣΜΕΥΣΗ — ποια φιγούρα σε κάθε θέση κάθε θόλου"))
    # Ο πάγκος διαδρομών ΕΦΥΓΕ από εδώ: η BFS σελιδοποιεί το &4000 όσο τρέχει,
    # οπότε δεν μπορεί να κρατά τα δεδομένα της σε σελιδοποιημένη τράπεζα.
    # Ζει τώρα στην τράπεζα 2 (rt_nodes, rt_row, node_adj).

    # --- τράπεζα 7 ----------------------------------------------------------
    for n in STRUCTS:
        bank7.append(spr(n))
    for p in PLANTS:
        bank7.append(spr(f"plant_{p}"))
    ptr["plant_ptr"] = [f"plant_{p}" for p in PLANTS]
    bank7.append(Run("plant_ptr", len(PLANTS) * 2, bytes(len(PLANTS) * 2),
                     note="παράγεται"))
    # 1.280 από το βήμα 79: τα 1.024 είχαν μείνει με επτά ελεύθερα, και το
    # «τι έχει κάτω ο κέρσορας» θέλει τα ονόματα των εδαφών. Η γραμματοσειρά
    # ανεβαίνει 256 bytes· η τράπεζα 7 έχει 952 ελεύθερα από πάνω της.
    # 2.048 από το βήμα 84: η οθόνη βοήθειας λέει όνομα και μια γραμμή για
    # καθένα από τα 33 κουμπιά (790 bytes).
    bank7.append(Run("text", TEXT_MAX, None, note="ΔΕΣΜΕΥΣΗ — τα κείμενα (src/uitext.asm)"))
    # Η ΓΡΑΜΜΑΤΟΣΕΙΡΑ, ΕΚΕΙ ΟΠΟΥ ΗΤΑΝ Η ΔΕΣΜΕΥΣΗ «audio» (βήμα 33). Τα 2.048
    # bytes κρατιούνταν από το §4.2 για μουσική μέσα στο παιχνίδι, και το §9.5
    # αποφάσισε ρητά ΟΧΙ μουσική· δεν τα διάβασε ποτέ τίποτα. Η γραματοσειρά
    # έχει ΕΝΑΝ αναγνώστη (το hc_draw του src/hud.asm), που σελιδοποιεί την 7
    # γύρω από τα δεκαέξι bytes του γλύφου — και τα 1.536 bytes που αφήνει στην
    # τράπεζα 2 γίνονται χώρος κώδικα, αφού ό,τι ακολουθεί την αρένα κατεβαίνει.
    #
    # ΣΕ MODE 1 ΑΠΟ ΤΟ ΒΗΜΑ 83 (§9.2). Το HUD ζει πια στις λωρίδες Mode 1 πάνω
    # και κάτω από το κάδρο, και ο γλύφος είναι ένα byte ανά γραμμή αντί για
    # δύο: 768 bytes. Βγαίνει ΕΔΩ από το font_gfx των assets (δεν αγγίζουμε τα
    # assets): ό,τι pixel έχει μελάνι γίνεται pen 3, τα άλλα pen 0. Στοίχιση 8,
    # ώστε οι οκτώ γραμμές του γλύφου να μη διασχίζουν σελίδα (inc e).
    #
    # ΚΑΙ ΤΑ ΚΕΛΙΑ ΤΗΣ ΜΠΑΡΑΣ είναι γλύφοι, οι κωδικοί #80-#84 (HUD_CELLS): κενό,
    # pen 1, 2, 3, και η άδεια μπάρα. Πέφτουν ακριβώς μετά τον 127, οπότε ο
    # hud_char βρίσκει κάθε κωδικό με τον ίδιο πολλαπλασιασμό.
    s = smap.get("font_gfx")
    if s is None:
        raise Fail("λείπει sprite: font_gfx")
    font = mode1_font(blob[s.off:s.off + s.size]) + HUD_CELLS
    bank7.append(Run("font_m1", len(font), font, align=8,
                     note="παράγεται από το font_gfx"))       # (ch-32)*8
    # ΤΑ ΣΥΜΒΟΛΑ ΤΩΝ ΚΟΥΜΠΙΩΝ (βήμα 84, §9.3): 33 x 17 bytes, ένα bit το pixel,
    # από το tools/buttons.py. Τα διαβάζει μόνο το src/bar.asm, με την τράπεζα 7
    # μέσα όπως για τον γλύφο.
    gfx = buttons.gfx()
    bank7.append(Run("btn_gfx", len(gfx), gfx, note="παράγεται από το tools/buttons.py"))

    return arena, bank1, bank5, bank6, bank7, ptr


def pack():
    """Στρώνει τα πάντα. Επιστρέφει (arena, bank1, bank5, bank6, bank7, ptr,
    images, free, report). Σκάει με Fail αν κάτι δεν χωράει."""
    smap, blob = load_map(), load_bin()
    arena, bank1, bank5, bank6, bank7, ptr = build_runs(smap, blob)

    u2 = pack_flat(arena, PAGE2_BASE, BANK_SIZE, "τράπεζα 2")
    u1 = pack_flat(bank1, BANK1_BASE, BANK1_SIZE, "τράπεζα 1 (πάνω από το DIST)")
    u5 = pack_flat(bank5, BANK5_BASE, BANK5_SIZE, "τράπεζα 5 (πάνω από NEXTHOP και ευρετήριο)")
    u6 = pack_flat(bank6, WINDOW_BASE, BANK_SIZE, "τράπεζα 6")
    u7 = pack_flat(bank7, WINDOW_BASE, BANK_SIZE, "τράπεζα 7")

    by_name = {r.name: r for r in arena + bank1 + bank5 + bank6 + bank7}

    # 2ο πέρασμα: οι πίνακες δεικτών ξέρουν πια πού κάθονται όλα
    for tab, names in ptr.items():
        r = by_name[tab]
        data = bytearray()
        for n in names:
            data += (0 if n is None else by_name[n].addr).to_bytes(2, "little")
        r.data = bytes(data)

    # --- εικόνες ------------------------------------------------------------
    out = os.path.join(ROOT, "build")
    os.makedirs(out, exist_ok=True)

    # Η εικόνα της τράπεζας 2 κόβεται στο ΧΡΗΣΙΜΟΠΟΙΗΜΕΝΟ μέρος: ό,τι μένει από
    # πάνω το παίρνει ο κώδικας (DESIGN §4.3), και ένα incbin 16 KB θα το
    # έσβηνε τη στιγμή του φορτώματος.
    page2 = bytearray(u2)
    for r in arena:
        if r.data:
            o = r.addr - PAGE2_BASE
            page2[o:o + r.size] = r.data
    b1 = bytearray(BANK1_SIZE)
    for r in bank1:
        if r.data:
            o = r.addr - BANK1_BASE
            b1[o:o + r.size] = r.data
    # Η τράπεζα 5 κόβεται κι αυτή στο χρησιμοποιημένο: φορτώνεται σε πρόχειρο
    # και ο φορτωτής την αντιγράφει στη θέση της (src/boot.asm).
    b5 = bytearray(u5)
    for r in bank5:
        if r.data:
            o = r.addr - BANK5_BASE
            b5[o:o + r.size] = r.data
    b6 = bytearray(BANK_SIZE)
    b7 = bytearray(BANK_SIZE)
    for img, runs in ((b6, bank6), (b7, bank7)):
        for r in runs:
            if r.data:
                o = r.addr - WINDOW_BASE
                img[o:o + r.size] = r.data

    images = {"page2": bytes(page2), "bank1": bytes(b1), "bank5": bytes(b5),
              "bank6": bytes(b6), "bank7": bytes(b7)}
    for name, img in images.items():
        with open(os.path.join(out, name + ".bin"), "wb") as f:
            f.write(img)

    # --- διευθύνσεις για τον assembler -------------------------------------
    with open(os.path.join(out, "layout.asm"), "w", encoding="utf-8") as f:
        f.write("; ΠΑΡΑΓΕΤΑΙ από tools/pack.py — μην το επεξεργάζεσαι.\n")
        f.write(f"PAGE2_TOP   equ #{PAGE2_BASE + u2:04X}   ; πρώτο ελεύθερο byte\n")
        f.write(f"B5_BASE     equ #{BANK5_BASE:04X}   ; οι μηχανές στην τράπεζα 5\n")
        f.write(f"B5_LEN      equ {u5}\n")
        f.write("; Οι τράπεζες 6/7 φαίνονται στο &4000 όταν σελιδοποιηθούν.\n\n")
        for label, runs in (("τράπεζα 2", arena), ("τράπεζα 1", bank1),
                            ("τράπεζα 5", bank5), ("τράπεζα 6", bank6),
                            ("τράπεζα 7", bank7)):
            f.write(f"; --- {label} ---\n")
            for r in sorted(runs, key=lambda r: r.addr):
                f.write(f"G_{r.name:<20} equ #{r.addr:04X}\n")
            f.write("\n")

    # --- λογαριασμός --------------------------------------------------------
    lines = []
    for label, runs, used, cap in (("τράπεζα 2", arena, u2, BANK_SIZE),
                                   ("τράπεζα 1", bank1, u1, BANK1_SIZE),
                                   ("τράπεζα 5", bank5, u5, BANK5_SIZE),
                                   ("τράπεζα 6", bank6, u6, BANK_SIZE),
                                   ("τράπεζα 7", bank7, u7, BANK_SIZE)):
        # ΤΟ «ΕΛΕΥΘΕΡΑ» ΤΗΣ ΤΡΑΠΕΖΑΣ 2 ΕΙΝΑΙ ΗΔΗ ΞΟΔΕΜΕΝΟ. Οσα μένουν πάνω από
        # το PAGE2_TOP τα μοιράζει το src/const.asm: αρχείο αναίρεσης
        # φαντάσματος και ο κώδικας που δεν χώρεσε στην τράπεζα 0. Χωρίς αυτή
        # τη σημείωση η γραμμή διαβάζεται ως «πέντε χιλιάδες ελεύθερα» και δεν
        # είναι — το πραγματικό περιθώριο το λέει το tools/mkdsk.py.
        note = ("  (τα παίρνει το const.asm: GH_BUF + κώδικας τράπεζας 2)"
                if label == "τράπεζα 2" else "")
        lines.append(f"{label}: {used}/{cap}  ελεύθερα {cap-used}{note}")
        for r in sorted(runs, key=lambda r: r.addr):
            lines.append(f"      #{r.addr:04X} {r.size:>5}  {r.name}"
                         f"{'  · ' + r.note if r.note else ''}")
        lines.append("")
    report = "\n".join(lines)
    with open(os.path.join(out, "layout.txt"), "w", encoding="utf-8") as f:
        f.write(report)
    return arena, bank1, bank5, bank6, bank7, ptr, images, [BANK_SIZE - u2], report


if __name__ == "__main__":
    print(pack()[-1])
