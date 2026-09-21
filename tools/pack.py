#!/usr/bin/env python3
"""Στρώνει τα assets στις τράπεζες και στις αρένες του &8000.

Βγάζει τις εικόνες των τραπεζών, τις διευθύνσεις για τον assembler, και έναν
λογαριασμό που διαβάζεται. **Σκάει** αν κάτι δεν χωρέσει — αυτός είναι ο λόγος
που υπάρχει: το DESIGN.md §4.2/§4.3 είναι χαρτί μέχρι να το μετρήσει κάποιος.

Η σελίδα 2 (&8000-&BFFF) κάνει δύο δουλειές ταυτόχρονα: είναι η σελίδα οθόνης
του HUD ΚΑΙ κρατά τα μικρά γραφικά. Η διάταξη οθόνης του CPC είναι

    addr = base + (γραμμή & 7)*&800 + (γραμμή >> 3)*80 + x

οπότε ένα HUD 5 σειρών χαρακτήρων πιάνει μόνο τα bytes &000-&18F καθεμιάς από
τις οκτώ υποσελίδες των &800. Μένουν οκτώ ΑΝΕΞΑΡΤΗΤΕΣ αρένες — τίποτα δεν
επιτρέπεται να πατάει σε δύο.
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sprites import load_map, load_bin, ROOT

# --- γεωμετρία ------------------------------------------------------------
SUBPAGE     = 0x800
HUD_ROWS    = 5                     # DESIGN §8.1: 40 γραμμές = 5 σειρές
HUD_USED    = HUD_ROWS * 80         # &190 ανά υποσελίδα
ARENA_SIZE  = SUBPAGE - HUD_USED    # 1648
ARENA_N     = 8
PAGE2_BASE  = 0x8000
WINDOW_BASE = 0x4000                # όπου φαίνονται οι τράπεζες 4-7
BANK_SIZE   = 0x4000

ARENAS = [(PAGE2_BASE + i * SUBPAGE + HUD_USED, ARENA_SIZE) for i in range(ARENA_N)]


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


def pack_arenas(runs):
    """First-fit-decreasing σε οκτώ ανεξάρτητα κουτιά.

    Φθίνουσα σειρά επειδή τα μεγάλα κομμάτια (γραμματοσειρά 1536, βουνό 1024)
    δεν χωράνε πουθενά αν μπουν τελευταία.
    """
    free = [ARENA_SIZE] * ARENA_N
    head = [a for a, _ in ARENAS]
    for r in sorted(runs, key=lambda r: -r.size):
        for i in range(ARENA_N):
            a = head[i]
            if r.align > 1:
                a = (a + r.align - 1) & ~(r.align - 1)
            pad = a - head[i]
            if r.size + pad <= free[i]:
                r.addr, r.bin = a, i
                free[i] -= r.size + pad
                head[i] = a + r.size
                break
        else:
            raise Fail(
                f"αρένες: το {r.name} ({r.size} B) δεν χωράει πουθενά.\n"
                f"  ελεύθερα ανά αρένα: {free}\n"
                f"  σύνολο ελεύθερο {sum(free)} B — ο χώρος υπάρχει αλλά είναι κομματιασμένος"
                if sum(free) >= r.size else
                f"αρένες: το {r.name} ({r.size} B) δεν χωράει — μένουν μόνο {sum(free)} B")
    return free


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
    MACH = ["oxygen", "iron", "bioplastic", "weapons", "processors",
            "robots", "food", "spares", "medical", "vitromeat"]
    PLANTS = ["peas", "rice", "potatoes", "wheat", "maize", "tomatoes",
              "lettuce", "onions", "radishes", "mushrooms", "medicinal", "tree"]
    DIRS = ["n", "ne", "e", "se", "s", "sw", "w", "nw"]
    STRUCTS = ([f"{k}_{s}" for k in ("solar", "turbine", "collector", "extractor")
                for s in ("s", "m", "l")] + ["mine", "airlock", "pad", "ship"])

    arena, bank6, bank7 = [], [], []
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
    for size in ("s", "m", "l"):
        names = [f"icon_{size}_{r}" for r in ROOMS]
        for n in names:
            arena.append(spr(n))
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
              "machine_slots", "machine_rules", "interior_ofs", "tile_variants",
              "planet_pens", "conn_points", "struct_dims", "palette_fw"):
        arena.append(spr(n))

    # --- παραγόμενοι πίνακες δεικτών ---------------------------------------
    for tab, names in ptr.items():
        if tab != "plant_ptr":
            arena.append(Run(tab, len(names) * 2, bytes(len(names) * 2),
                             note="παράγεται"))

    arena.append(Run("ui_cursor", 256, bytes(256), note="ΔΕΣΜΕΥΣΗ — δεν έχει παραδοθεί"))

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
    bank6.append(Run("entity_tables", 4096, None, note="ΔΕΣΜΕΥΣΗ — RAM"))
    bank6.append(Run("job_board", 256, None, note="ΔΕΣΜΕΥΣΗ — RAM"))
    bank6.append(Run("path_work", 512, None, note="ΔΕΣΜΕΥΣΗ — RAM"))

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

    return arena, bank6, bank7, ptr


def pack():
    """Στρώνει τα πάντα. Επιστρέφει (arena, bank6, bank7, ptr, images).
    Σκάει με Fail αν κάτι δεν χωράει."""
    smap, blob = load_map(), load_bin()
    arena, bank6, bank7, ptr = build_runs(smap, blob)

    free = pack_arenas(arena)
    u6 = pack_flat(bank6, WINDOW_BASE, BANK_SIZE, "τράπεζα 6")
    u7 = pack_flat(bank7, WINDOW_BASE, BANK_SIZE, "τράπεζα 7")

    by_name = {r.name: r for r in arena + bank6 + bank7}

    # 2ο πέρασμα: οι πίνακες δεικτών ξέρουν πια πού κάθονται όλα
    for tab, names in ptr.items():
        r = by_name[tab]
        data = bytearray()
        for n in names:
            data += by_name[n].addr.to_bytes(2, "little")
        r.data = bytes(data)

    # --- εικόνες ------------------------------------------------------------
    out = os.path.join(ROOT, "build")
    os.makedirs(out, exist_ok=True)

    page2 = bytearray(BANK_SIZE)
    for r in arena:
        if r.data:
            o = r.addr - PAGE2_BASE
            page2[o:o + r.size] = r.data
    b6 = bytearray(BANK_SIZE)
    b7 = bytearray(BANK_SIZE)
    for img, runs in ((b6, bank6), (b7, bank7)):
        for r in runs:
            if r.data:
                o = r.addr - WINDOW_BASE
                img[o:o + r.size] = r.data

    images = {"page2": bytes(page2), "bank6": bytes(b6), "bank7": bytes(b7)}
    for name, img in images.items():
        with open(os.path.join(out, name + ".bin"), "wb") as f:
            f.write(img)

    # --- διευθύνσεις για τον assembler -------------------------------------
    with open(os.path.join(out, "layout.asm"), "w", encoding="utf-8") as f:
        f.write("; ΠΑΡΑΓΕΤΑΙ από tools/pack.py — μην το επεξεργάζεσαι.\n")
        f.write("; Οι τράπεζες 6/7 φαίνονται στο &4000 όταν σελιδοποιηθούν.\n\n")
        for label, runs in (("αρένες σελίδας 2", arena),
                            ("τράπεζα 6", bank6), ("τράπεζα 7", bank7)):
            f.write(f"; --- {label} ---\n")
            for r in sorted(runs, key=lambda r: r.addr):
                f.write(f"G_{r.name:<20} equ #{r.addr:04X}\n")
            f.write("\n")

    # --- λογαριασμός --------------------------------------------------------
    lines = []
    lines.append(f"αρένα = {SUBPAGE} - {HUD_USED} (HUD {HUD_ROWS} σειρές) = {ARENA_SIZE} B x {ARENA_N} = {ARENA_SIZE*ARENA_N} B\n")
    for i in range(ARENA_N):
        items = sorted([r for r in arena if r.bin == i], key=lambda r: r.addr)
        used = sum(r.size for r in items)
        lines.append(f"  αρένα {i} @#{ARENAS[i][0]:04X}  {used:>5}/{ARENA_SIZE}  ελεύθερα {free[i]:>4}")
        for r in items:
            lines.append(f"      #{r.addr:04X} {r.size:>5}  {r.name}{'  · ' + r.note if r.note else ''}")
    lines.append(f"\n  σύνολο αρενών: {sum(r.size for r in arena)}/{ARENA_SIZE*ARENA_N}  ελεύθερα {sum(free)}\n")
    for label, runs, used in (("τράπεζα 6", bank6, u6), ("τράπεζα 7", bank7, u7)):
        lines.append(f"{label}: {used}/{BANK_SIZE}  ελεύθερα {BANK_SIZE-used}")
        for r in sorted(runs, key=lambda r: r.addr):
            lines.append(f"      #{r.addr:04X} {r.size:>5}  {r.name}{'  · ' + r.note if r.note else ''}")
        lines.append("")
    report = "\n".join(lines)
    with open(os.path.join(out, "layout.txt"), "w", encoding="utf-8") as f:
        f.write(report)
    return arena, bank6, bank7, ptr, images, free, report


if __name__ == "__main__":
    print(pack()[-1])
