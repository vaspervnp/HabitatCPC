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

    arena, bank1, bank6, bank7 = [], [], [], []
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
    for m in MACH:
        arena.append(spr(f"mach_{m}"))
    ptr["mach_ptr"] = [f"mach_{m}" for m in MACH]

    # --- διάδρομοι, συνδέσεις, γραμματοσειρά --------------------------------
    for n in ("corr_h", "corr_v", "corr_dr", "corr_dl"):
        arena.append(spr(n))
    arena.append(group("connectors", [f"conn_{d}" for d in DIRS]))   # dir*32
    arena.append(spr("font_gfx"))                                    # (ch-32)*16

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

    arena.append(Run("ui_cursor", 256, bytes(256), note="ΔΕΣΜΕΥΣΗ — δεν έχει παραδοθεί"))

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
    arena.append(Run("econ_state", 82, None, note="ΔΕΣΜΕΥΣΗ — αποθέματα και ροές"))
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
    # ΤΕΛΕΥΤΑΙΑ ΕΠΙΤΗΔΕΣ, μετά τον γράφο: το αρχείο σωσίματος γράφει το
    # #A400-#ABFF ως ένα κομμάτι (§11) και ό,τι μπει πριν σπρώχνει τον γράφο
    # έξω από αυτό. Η κρυφή μνήμη δεν σώζεται — ξαναχτίζεται μόλις αλλάξει
    # κελί.
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
    bank7.append(Run("text", 1024, None, note="ΔΕΣΜΕΥΣΗ — δεν έχει παραδοθεί"))
    bank7.append(Run("audio", 2048, None, note="ΔΕΣΜΕΥΣΗ — δεν έχει παραδοθεί"))

    return arena, bank1, bank6, bank7, ptr


def pack():
    """Στρώνει τα πάντα. Επιστρέφει (arena, bank6, bank7, ptr, images).
    Σκάει με Fail αν κάτι δεν χωράει."""
    smap, blob = load_map(), load_bin()
    arena, bank1, bank6, bank7, ptr = build_runs(smap, blob)

    u2 = pack_flat(arena, PAGE2_BASE, BANK_SIZE, "τράπεζα 2")
    u1 = pack_flat(bank1, BANK1_BASE, BANK1_SIZE, "τράπεζα 1 (πάνω από το DIST)")
    u6 = pack_flat(bank6, WINDOW_BASE, BANK_SIZE, "τράπεζα 6")
    u7 = pack_flat(bank7, WINDOW_BASE, BANK_SIZE, "τράπεζα 7")

    by_name = {r.name: r for r in arena + bank1 + bank6 + bank7}

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
    b6 = bytearray(BANK_SIZE)
    b7 = bytearray(BANK_SIZE)
    for img, runs in ((b6, bank6), (b7, bank7)):
        for r in runs:
            if r.data:
                o = r.addr - WINDOW_BASE
                img[o:o + r.size] = r.data

    images = {"page2": bytes(page2), "bank1": bytes(b1),
              "bank6": bytes(b6), "bank7": bytes(b7)}
    for name, img in images.items():
        with open(os.path.join(out, name + ".bin"), "wb") as f:
            f.write(img)

    # --- διευθύνσεις για τον assembler -------------------------------------
    with open(os.path.join(out, "layout.asm"), "w", encoding="utf-8") as f:
        f.write("; ΠΑΡΑΓΕΤΑΙ από tools/pack.py — μην το επεξεργάζεσαι.\n")
        f.write(f"PAGE2_TOP   equ #{PAGE2_BASE + u2:04X}   ; πρώτο ελεύθερο byte\n")
        f.write("; Οι τράπεζες 6/7 φαίνονται στο &4000 όταν σελιδοποιηθούν.\n\n")
        for label, runs in (("τράπεζα 2", arena), ("τράπεζα 1", bank1),
                            ("τράπεζα 6", bank6), ("τράπεζα 7", bank7)):
            f.write(f"; --- {label} ---\n")
            for r in sorted(runs, key=lambda r: r.addr):
                f.write(f"G_{r.name:<20} equ #{r.addr:04X}\n")
            f.write("\n")

    # --- λογαριασμός --------------------------------------------------------
    lines = []
    for label, runs, used, cap in (("τράπεζα 2", arena, u2, BANK_SIZE),
                                   ("τράπεζα 1", bank1, u1, BANK1_SIZE),
                                   ("τράπεζα 6", bank6, u6, BANK_SIZE),
                                   ("τράπεζα 7", bank7, u7, BANK_SIZE)):
        lines.append(f"{label}: {used}/{cap}  ελεύθερα {cap-used}")
        for r in sorted(runs, key=lambda r: r.addr):
            lines.append(f"      #{r.addr:04X} {r.size:>5}  {r.name}"
                         f"{'  · ' + r.note if r.note else ''}")
        lines.append("")
    report = "\n".join(lines)
    with open(os.path.join(out, "layout.txt"), "w", encoding="utf-8") as f:
        f.write(report)
    return arena, bank1, bank6, bank7, ptr, images, [BANK_SIZE - u2], report


if __name__ == "__main__":
    print(pack()[-1])
