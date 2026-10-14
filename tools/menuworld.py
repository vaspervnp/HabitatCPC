"""Το μενού πάνω σε κομμάτι κόσμου (βήμα 130, DESIGN §13.2): οι κόσμοι, τα
δεδομένα του MENU.BIN, και η αναφορά της οθόνης για τις δοκιμές.

Ο παίκτης: «θέλω το μενού να έχει και γραφικά, ζωγραφισμένο πάνω σε τμήμα
κόσμου — ένας τυχαίος κόσμος κάθε φορά». Διάλεξε κόσμους ΕΤΟΙΜΟΥΣ στον δίσκο:
η γεννήτρια του παιχνιδιού θέλει 5 δευτερόλεπτα για έναν κόσμο, και ένα
κομμάτι μόνο του δεν το ξέρει να φτιάξει. Εδώ λοιπόν, όταν χτίζεται ο δίσκος,
η γεννήτρια αναφοράς (tools/worldgen_ref.py, byte προς byte ίδια με του Z80)
βγάζει MW_N κόσμους, οκτώ ανά πλανήτη, και από τον καθένα κρατιέται ένα
κομμάτι οθόνης, 20 x 13 tiles. Ο φορτωτής διαλέγει ένα με τον R.

ΤΙ ΑΠΟΘΗΚΕΥΕΤΑΙ ΑΝΑ ΚΟΣΜΟ, ~140 bytes αντί για 260 (ένα byte ανά tile):
  * οι ΚΛΑΣΕΙΣ ενός παραθύρου 22 x 15 (το κομμάτι και ένα tile γύρω του), σε
    RLE: byte = (μήκος - 1) << 4 | τιμή, τιμή = κλάση | 8 για βουνό με φλέβα.
    Το νερό και το βουνό έχουν 16 παραλλαγές autotile, και ο Z80 τις βγάζει
    από τους τέσσερις γείτονες όπως το παιχνίδι — γι' αυτό το περιθώριο.
  * τα δύο bits decor, ΜΟΝΟ όπου τα κοιτάζει η σχεδίαση: η παραλλαγή των
    κλάσεων με λιγότερες από 16, και ποια φλέβα σε βουνό με φλέβα. Τέσσερα
    ανά byte, το πρώτο tile στα bits 0-1.
Τα tiles βγαίνουν ΑΚΡΙΒΩΣ όπως θα τα ζωγράφιζε το παιχνίδι σε αυτόν τον κόσμο.

Η γεωμετρία είναι του src/menugeom.asm· διαβάζεται από εκεί.
"""
import functools
import hashlib
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from sprites import load_map, load_bin, rows          # noqa: E402
from refrender import Canvas, unpack_pens             # noqa: E402
import world as WD                                    # noqa: E402

PER_PLANET = 8              # κόσμοι ανά πλανήτη: MW_N = 32 στο src/menugeom.asm
SEED0 = 0x3A5D              # η αρχή της ακολουθίας των seeds (seeds())
MENU = [("RANDOM", "ANY OF THE FOUR", "RANDOM WORLD"),
        ("DESERT", "WATER, LAND, SOME ORE", "DESERT"),
        ("ICE", "MUCH WATER, LESS LAND", "ICE"),
        ("STORM", "MOUNTAINS, ORE, DRY", "STORM"),
        ("BARREN MOON", "DUST, ORE, LITTLE WATER", "BARREN MOON")]
SUBTITLE = "a colony on a dead world"
CHOOSE = "CHOOSE A WORLD"
KEYS = "UP/DOWN, FIRE OR ENTER"
LOADING = "LOADING"
BUILDING = "BUILDING THE WORLD"
TITLE = "HABITAT"

# Τα tiles του εδάφους είναι ζωγραφισμένα σε μισή κάθετη ανάλυση: κάθε γραμμή
# τους δύο φορές. Αποθηκεύονται οι μισές (32 bytes αντί για 64), και ο Z80 τη
# διπλασιάζει. Ολες οι κλάσεις ως το βαθύ νερό· ο κρατήρας ΔΕΝ είναι έτσι (και
# το foundation, που η γεννήτρια δεν το βγάζει), οπότε το window() δεν
# διαλέγει κομμάτι με κρατήρα. Οι φλέβες αποθηκεύονται ολόκληρες.
TILE_CLASSES = 6

# Τα bytes του Mode 0 που χρησιμοποιεί η οθόνη (πένα αριστερού / δεξιού pixel).
INV = 0xF0                  # πένα 5 και στα δύο: XOR = ανάποδα, και η μπάρα
DIM = 0x3F                  # AND: η πένα 5 γίνεται 4 (σβηστό κείμενο)
EDGE = 0x30                 # πένα 4 και στα δύο: η γραμμή του πλαισίου
EDGE_L = 0x10               # πένα 4 μόνο δεξιά: το αριστερό χείλος
EDGE_R = 0x20               # πένα 4 μόνο αριστερά: το δεξί
TITLE_INK = 0x3C            # πένα 6 και στα δύο: ο τίτλος


# --- η γεωμετρία ----------------------------------------------------------

@functools.lru_cache(maxsize=None)
def geom():
    """Τα equ του src/menugeom.asm (αριθμοί, #hex, + - * και ονόματα)."""
    g = {}
    pat = re.compile(r"^([A-Z_0-9]+)\s+equ\s+([^;]+)", re.I)
    for line in open(os.path.join(ROOT, "src", "menugeom.asm"), encoding="utf-8"):
        m = pat.match(line)
        if m:
            expr = re.sub(r"#([0-9A-Fa-f]+)", r"0x\1", m.group(2).strip())
            g[m.group(1)] = eval(expr, {}, dict(g))
    return g


# --- τα assets ------------------------------------------------------------

@functools.lru_cache(maxsize=None)
def assets():
    smap, blob = load_map(), load_bin()

    def tab(name, n):
        return list(blob[smap[name].off:smap[name].off + n])
    return smap, blob, tab("palette_fw", 16), tab("planet_pens", 16), tab("tile_variants", 8)


@functools.lru_cache(maxsize=None)
def terrain_pens():
    """Τα τέσσερα pens του πλανήτη, από το pal_terrain του src/hw.asm."""
    for line in open(os.path.join(ROOT, "src", "hw.asm"), encoding="utf-8"):
        if line.startswith("pal_terrain:"):
            return tuple(int(v) for v in line.split("db")[1].split(";")[0].split(","))
    raise SystemExit("δεν βρέθηκε το pal_terrain στο src/hw.asm")


def planet_of(seed):
    """Ο πλανήτης ενός seed, όπως στο gen_entry (§5.7): (H xor L) and 3."""
    return ((seed >> 8) ^ seed) & 3


def palette(planet):
    """Οι 16 αριθμοί firmware της οθόνης για αυτόν τον πλανήτη."""
    _, _, pal, pp, _ = assets()
    p = pal[:]
    for k, pen in enumerate(terrain_pens()):
        p[pen] = pp[planet * 4 + k]
    return p


# --- οι κόσμοι --------------------------------------------------------------

def seeds(planet, n=PER_PLANET):
    """n seeds αυτού του πλανήτη, από μια σταθερή ακολουθία (LCG mod 65537)."""
    out, s = [], (SEED0 + planet) & 0xFFFF
    while len(out) < n:
        s = (s * 75 + 74) % 65537 & 0xFFFF
        if s and planet_of(s) == planet:
            out.append(s)
    return out


def window(plane):
    """Το πάνω-αριστερά (tx, ty) του κομματιού: το πιο ποικίλο στο μέσο του
    κόσμου — κλάσεις, νερό, βουνό, φλέβες. Ολο το παράθυρο με το περιθώριο
    του μένει μακριά από τις άκρες του κόσμου (εκεί το autotile κοιτάζει τον
    εαυτό του, §3.5) και από το χείλος των βουνών του §5.5."""
    best = None
    for ty in range(-40, 28, 3):
        for tx in range(-40, 20, 3):
            cls, ore = {}, 0
            for r in range(13):
                for c in range(20):
                    b = plane.get(tx + c, ty + r)
                    k = WD.cls_of(b)
                    cls[k] = cls.get(k, 0) + 1
                    ore += k == WD.MOUNTAIN and WD.res_of(b)
            if any(k >= TILE_CLASSES for k in cls):
                continue                    # κρατήρας: δεν έχει διπλές γραμμές
            water = cls.get(WD.WATER, 0) + cls.get(WD.DEEPWATER, 0)
            score = (len(cls) * 10 + min(water, 40) + min(cls.get(WD.MOUNTAIN, 0), 40)
                     + min(ore, 8) * 3)
            if best is None or score > best[0]:
                best = (score, tx, ty)
    return best[1], best[2]


@functools.lru_cache(maxsize=None)
def worlds():
    """[(seed, πλανήτης, tx, ty, plane)] — οι MW_N κόσμοι, ανά πλανήτη."""
    import worldgen_ref
    out = []
    for pl in range(4):
        for seed in seeds(pl):
            plane = worldgen_ref.generate(seed, pl)
            tx, ty = window(plane)
            out.append((seed, pl, tx, ty, plane))
    return out


def cell(plane, tx, ty):
    """Η τιμή του RLE: κλάση, και 8 για βουνό με φλέβα."""
    b = plane.get(tx, ty)
    k = WD.cls_of(b)
    return k | (8 if k == WD.MOUNTAIN and WD.res_of(b) else 0)


def encode(plane, tx, ty):
    """(RLE, decor) ενός κομματιού."""
    g = geom()
    _, _, _, _, var = assets()
    vals = [cell(plane, tx + c, ty + r)
            for r in range(-1, g["MW_ROWS"] + 1) for c in range(-1, g["MW_COLS"] + 1)]
    rle, i = bytearray(), 0
    while i < len(vals):
        j = i
        while j < len(vals) and vals[j] == vals[i] and j - i < 16:
            j += 1
        rle.append(((j - i - 1) << 4) | vals[i])
        i = j
    bits = []
    for r in range(g["MW_ROWS"]):
        for c in range(g["MW_COLS"]):
            b = plane.get(tx + c, ty + r)
            k = WD.cls_of(b)
            if var[k] < 16 or (k == WD.MOUNTAIN and WD.res_of(b)):
                bits.append(WD.decor_of(b))
    dec = bytearray((len(bits) + 3) // 4)
    for n, v in enumerate(bits):
        dec[n >> 2] |= v << (2 * (n & 3))
    return bytes(rle), bytes(dec)


# --- τα γράμματα --------------------------------------------------------------

def strings():
    """{ετικέτα: κείμενο} όσων γράφει το MENU.BIN."""
    s = {"s_sub": SUBTITLE, "s_cho": CHOOSE, "s_key": KEYS,
         "s_lod": LOADING, "s_wld": BUILDING}
    for i, (name, desc, full) in enumerate(MENU):
        s[f"s_opt{i}"] = " " + name
        s[f"s_dsc{i}"] = desc
        s[f"s_nam{i}"] = full
    return s


@functools.lru_cache(maxsize=None)
def charset():
    """Οι χαρακτήρες που χρειάζονται, με το κενό πρώτο (γλύφος 0: το γέμισμα)."""
    used = sorted(set("".join(strings().values())) - {" "})
    return [" "] + used


def glyph(ch):
    """Τα 16 bytes του γλύφου (2 ανά γραμμή) από το font_gfx."""
    smap, blob, _, _, _ = assets()
    k = smap["font_gfx"].off + (ord(ch) - 32) * 16
    return blob[k:k + 16]


@functools.lru_cache(maxsize=None)
def title_cells():
    """Ο τίτλος σε κελιά του ενός byte x 2 γραμμών: 0 διάφανο, 1 μαύρο (το
    περίγραμμα), 2 κίτρινο. Κάθε pixel της γραμματοσειράς γίνεται ένα κελί,
    δηλαδή διπλό σε πλάτος και ύψος, και το περίγραμμα είναι οι οκτώ γείτονες."""
    w, h = len(TITLE) * 4 + 2, 8
    g = [[0] * w for _ in range(h)]
    ink = []
    for i, ch in enumerate(TITLE):
        gl = glyph(ch)
        for r in range(6):
            for x in range(4):
                b = gl[2 * r + (x >> 1)]
                if unpack_pens(b)[x & 1]:
                    ink.append((1 + i * 4 + x, r + 1))
    for cx, cy in ink:
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                g[cy + dy][cx + dx] = max(g[cy + dy][cx + dx], 1)
    for cx, cy in ink:
        g[cy][cx] = 2
    return tuple(tuple(r) for r in g)


# --- τα δεδομένα του MENU.BIN ---------------------------------------------------



def data_lines():
    """build/menu_data.asm: ό,τι διαβάζει το src/menu.asm."""
    smap, blob, pal, pp, var = assets()
    g = geom()
    assert len(worlds()) == g["MW_N"] and g["MW_N"] & (g["MW_N"] - 1) == 0
    out = ["; ΠΑΡΑΓΕΤΑΙ από το tools/menuworld.py (βήμα 130) — μην το επεξεργάζεσαι."]

    def db(vals, per=16):
        for i in range(0, len(vals), per):
            out.append("        db      " + ",".join(f"#{v:02X}" for v in vals[i:i + per]))

    # tiles: ανά κλάση, όλες οι παραλλαγές της, 64 bytes η καθεμιά
    out.append("mw_toff:                ; ο αριθμός του πρώτου tile κάθε κλάσης")
    off, offs = 0, []
    for k in range(8):
        offs.append(off if k < TILE_CLASSES else 0)
        off += var[k] if k < TILE_CLASSES else 0
    db(offs)
    out.append("mw_var:                 ; οι παραλλαγές ανά κλάση (tile_variants)")
    db(var)
    out.append("mw_tiles:               ; 8 γραμμές το tile: κάθε γραμμή του δύο φορές")
    for k in range(TILE_CLASSES):
        for v in range(var[k]):
            s = smap[f"tile_{WD.CLASS_NAMES[k]}_{v}"]
            d = blob[s.off:s.off + 64]
            assert s.size == 64 and not s.masked
            assert all(d[8 * i:8 * i + 4] == d[8 * i + 4:8 * i + 8] for i in range(8)), s.name
            db([b for i in range(8) for b in d[8 * i:8 * i + 4]])
    out.append("mw_ore:                 ; οι δύο φλέβες, μάσκα-δεδομένα")
    for v in range(2):
        s = smap[f"ore_overlay_{v}"]
        assert s.size == 128 and s.masked
        db(list(blob[s.off:s.off + 128]))
    # γλύφοι και κείμενα
    cs = charset()
    out.append("mw_glyphs:")
    for ch in cs:
        db(list(glyph(ch)))
    for lab, txt in strings().items():
        out.append(f"{lab}:")
        db([cs.index(ch) for ch in txt] + [0xFF])
    for tab, stem in (("mw_sopt", "s_opt"), ("mw_sdsc", "s_dsc"), ("mw_snam", "s_nam")):
        out.append(f"{tab}:   dw " + ", ".join(f"{stem}{i}" for i in range(len(MENU))))
    # ο τίτλος, 2 bits το κελί
    cells = [v for r in title_cells() for v in r]
    packed = [0] * ((len(cells) + 3) // 4)
    for n, v in enumerate(cells):
        packed[n >> 2] |= v << (2 * (n & 3))
    out.append(f"MW_TW equ {len(title_cells()[0])}")
    out.append(f"MW_TH equ {len(title_cells())}")
    out.append("mw_tcell:")
    db(packed)
    # η παλέτα
    out.append("mw_pal:                 ; palette_fw")
    db(pal)
    out.append("mw_pp:                  ; planet_pens: τέσσερα ανά πλανήτη")
    db(pp)
    out.append("mw_tpen:                ; pal_terrain του src/hw.asm")
    db(list(terrain_pens()))
    # οι κόσμοι
    out.append("mw_ex:                  ; ανά κόσμο: πλανήτης, δείκτης")
    for i, (seed, pl, tx, ty, plane) in enumerate(worlds()):
        out.append(f"        db      {pl}")
        out.append(f"        dw      mw_x{i}          ; seed #{seed:04X}, ({tx}, {ty})")
    for i, (seed, pl, tx, ty, plane) in enumerate(worlds()):
        rle, dec = encode(plane, tx, ty)
        out.append(f"mw_x{i}:")
        db(list(rle) + list(dec))
    return out


def stamp():
    """Ο αποτυπωματικός αριθμός των εισόδων: αν δεν άλλαξε, το build/menu_data.asm
    μένει (οι 32 κόσμοι θέλουν ~10 s)."""
    h = hashlib.sha1()
    for p in ("tools/menuworld.py", "tools/worldgen_ref.py", "tools/world.py",
              "src/menugeom.asm", "src/hw.asm", "assets/sprites.bin",
              "assets/sprites_map.txt"):
        h.update(open(os.path.join(ROOT, p), "rb").read())
    return h.hexdigest()


def write(force=False):
    path = os.path.join(ROOT, "build", "menu_data.asm")
    head = f"; stamp {stamp()}"
    if not force and os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            if f.readline().strip() == head:
                return path
    lines = [head] + data_lines()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return path


# --- η αναφορά -------------------------------------------------------------------

def draw_world(cv, plane, tx, ty):
    """Το κομμάτι, όπως το ζωγραφίζει το παιχνίδι (tests/test_object.py:
    reference): το tile της κλάσης με την παραλλαγή του, και η φλέβα από πάνω."""
    smap, blob, _, _, var = assets()
    g = geom()
    for r in range(g["MW_ROWS"]):
        for c in range(g["MW_COLS"]):
            b = plane.get(tx + c, ty + r)
            k = WD.cls_of(b)
            cv.opaque(list(rows(blob, smap[f"tile_{WD.CLASS_NAMES[k]}_{plane.variant(tx + c, ty + r, var)}"])),
                      c * 4, r * 16)
            if k == WD.MOUNTAIN and WD.res_of(b):
                cv.masked(list(rows(blob, smap[f"ore_overlay_{WD.decor_of(b) & 1}"])),
                          c * 4, r * 16)


def text(cv, col, row, s, width=0, mode=None):
    """mode None, 'inv' (XOR INV) ή 'dim' (AND DIM)· width: κενά ως εκεί."""
    s = s.ljust(width)
    for i, ch in enumerate(s):
        gl = glyph(ch)
        for r in range(8):
            for j in range(2):
                b = gl[2 * r + j]
                if mode == "inv":
                    b ^= INV
                elif mode == "dim":
                    b &= DIM
                cv[(col + i) * 2 + j, row * 8 + r] = b


def frame(cv, x0, x1, y0, y1, fill_lines=()):
    """Γραμμές y0..y1-1, bytes x0..x1-1: στις y0 και y1-1 μηδέν, στις y0+1 και
    y1-2 το πλαίσιο, στις άλλες τα δύο χείλη και μηδέν ανάμεσα."""
    for y in range(y0, y1):
        if y in (y0, y1 - 1):
            row = [0] * (x1 - x0)
        elif y in (y0 + 1, y1 - 2):
            row = [EDGE_L] + [EDGE] * (x1 - x0 - 2) + [EDGE_R]
        else:
            row = [EDGE_L] + [0] * (x1 - x0 - 2) + [EDGE_R]
        for i, v in enumerate(row):
            cv[x0 + i, y] = v


def panel(cv):
    g = geom()
    frame(cv, g["PNL_COL"] * 2, (g["PNL_COL"] + g["PNL_W"]) * 2,
          g["PNL_ROW"] * 8, (g["PNL_ROW"] + g["PNL_H"]) * 8)


def title(cv):
    g = geom()
    for r, row in enumerate(title_cells()):
        for c, v in enumerate(row):
            if v:
                for k in range(2):
                    cv[g["TITLE_X"] + c, g["TITLE_Y"] + 2 * r + k] = TITLE_INK if v == 2 else 0


def bar(cv, files, gen):
    """Το πλαίσιο της μπάρας, με files bytes των αρχείων και gen της γεννήτριας."""
    g = geom()
    x0, y0 = g["BAR_X0"] - 1, g["BAR_ROW"] * 8
    for ln in range(8):
        edge = ln in (0, 7)
        cv[x0, y0 + ln] = EDGE_L
        cv[x0 + g["BAR_W"] + 1, y0 + ln] = EDGE_R
        for i in range(g["BAR_W"]):
            on = i < files or g["BAR_FILES"] <= i < g["BAR_FILES"] + gen
            cv[g["BAR_X0"] + i, y0 + ln] = EDGE if edge else (g["BAR_INK"] if on else 0)


def background(i):
    """Ο κόσμος i, ο τίτλος και ο υπότιτλος: ό,τι μένει σε όλη την αναμονή."""
    g = geom()
    seed, pl, tx, ty, plane = worlds()[i]
    cv = Canvas()
    draw_world(cv, plane, tx, ty)
    title(cv)
    text(cv, g["SUB_COL"], g["SUB_ROW"], SUBTITLE, g["SUB_W"])
    return cv


def screen_menu(i, sel):
    """Η οθόνη του μενού: ο κόσμος i, η γραμμή sel (0 τυχαίος, 1-4) διαλεγμένη."""
    g = geom()
    cv = background(i)
    panel(cv)
    text(cv, g["CHO_COL"], g["CHO_ROW"], CHOOSE)
    for k, (name, desc, full) in enumerate(MENU):
        text(cv, g["OPT_COL"], g["OPT_ROW"] + k, " " + name, g["OPT_W"],
             "inv" if k == sel else None)
    text(cv, g["DSC_COL"], g["DSC_ROW"], MENU[sel][1], g["DSC_W"])
    text(cv, g["KEY_COL"], g["KEY_ROW"], KEYS)
    return cv


def screen_loading(i, sel, files=0, gen=0, lit=False):
    """Η οθόνη της φόρτωσης: το πάνελ με τον κόσμο που διάλεξε, LOADING, τη
    μπάρα, και το BUILDING THE WORLD σβηστό ή αναμμένο."""
    g = geom()
    cv = background(i)
    panel(cv)
    text(cv, g["NAM_COL"], g["NAM_ROW"], MENU[sel][2])
    text(cv, g["LOD_COL"], g["LOD_ROW"], LOADING)
    bar(cv, files, gen)
    text(cv, g["WLD_COL"], g["WLD_ROW"], BUILDING, g["WLD_W"], None if lit else "dim")
    return cv


MW_N = geom()["MW_N"]


if __name__ == "__main__":
    p = write(force="-f" in sys.argv)
    print(p, os.path.getsize(p), "bytes κειμένου;",
          sum(len(encode(pl, tx, ty)[0]) + len(encode(pl, tx, ty)[1])
              for _, _, tx, ty, pl in worlds()), "bytes κόσμων")
