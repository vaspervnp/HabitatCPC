#!/usr/bin/env python3
"""Κάθε κτίσμα δένεται με ένα κοντινό (βήμα 85, DESIGN §9.3), στο main.sna.

Ο ΚΑΝΟΝΑΣ, όπως τον ζήτησε ο παίκτης (η αναφορά είναι το tools/reach.py):

  * Το πρώτο κτίσμα του κόσμου μπαίνει όπου το επιτρέπει το έδαφος.
  * Κάθε επόμενο θέλει κάποιο κτίσμα ως 12 tiles μακριά. Ένας θόλος παίρνει
    σκεπαστό διάδρομο προς ΚΑΘΕ θόλο που ο διάδρομος φτάνει με το πολύ 12
    πλακίδια (ως τέσσερις, με τη σειρά του πίνακα), χωρίς δύο διαδρόμους στα
    ίδια tiles. Μια δομή — ή ένας θόλος χωρίς διάδρομο — παίρνει μονοπάτι στο
    έδαφος, ένα Γ κέντρο-κέντρο προς το κοντινότερο κτίσμα, με το πολύ 12
    tiles έξω από τα δύο αποτυπώματα, όλα σε έδαφος που χτίζεται.
  * Αλλιώς κόκκινο, και ο πίνακας λέει TOO FAR ή PATH BLOCKED.

  ΚΑΝΟΝΕΣ   Τυχαίες σκηνές — κόσμος με εμπόδια, θόλοι και δομές γύρω από τον
            κέρσορα, κάθε αντικείμενο του καταλόγου — και ο Z80 (ui_validate)
            συμφωνεί με το reach.py: ui_bad (το πλήθος κακών tiles, 255, ή #F0 +
            λόγος), οι διάδρομοι και το μήκος τους, το μονοπάτι και το σχήμα
            του, το bd_nres, το σύνολο του κόστους (cr_metal, cr_biop)· και ο
            κόσμος μένει ΙΔΙΟΣ: οι προσωρινές σφραγίδες φεύγουν.
  ΦΑΝΤΑΣΜΑ  Στο ui_show, ένα σημάδι σε κάθε ορατό tile των διαδρόμων ή του
            μονοπατιού και πουθενά αλλού· το αρχείο αναίρεσης γυρίζει την οθόνη
            όπως ήταν.
  FIRE      Το uist_place χτίζει ό,τι έδειξε το φάντασμα: τα tiles του
            μονοπατιού θεμέλιο με κατοχή 2 και το decor τους, οι διάδρομοι
            στον πίνακα, οι ακμές στον γράφο, το κόστος πληρωμένο ακριβώς, και
            η οθόνη byte προς byte η πλήρης σχεδίαση — και όταν η διαγώνιος
            ξεκινά από τη γωνία του νέου θόλου, που τη ζωγραφίζει και η σειρά
            του εργοταξίου (το test_fit το βρήκε). Ο χειρότερος γύρος του FIRE
            κάτω από 200 ms, όπως η τοποθέτηση του L στο test_reveal· με
            μονοπάτι κάτω από 140, γιατί ξαναζωγραφίζονται μόνο τα tiles του
            (171 ms με το ορθογώνιο κέντρο-γωνία-κέντρο, που έπιανε και τον
            θόλο απέναντι).
  ΠΙΝΑΚΑΣ   Στο παιχνίδι: το σύνολο του κόστους στη σειρά 3, ο λόγος στη 4 —
            και ο λόγος αλλάζει ακόμη κι όταν το ui_bad έμενε ίδιο ως το βήμα 84.
  ΧΡΟΝΟΣ    Ένα βήμα κέρσορα (ui_validate) δίπλα στην αποικία, όχι πιο αργό από
            όσο μετρήθηκε στο βήμα 85.

Αρνητικά, με το snapshot πειραγμένο: εμβέλεια 13, χωρίς την προσωρινή
σφραγίδα, χωρίς το ξεσφράγισμα, μόνο το πρώτο Γ, το γρήγορο «όχι» ένα tile πιο
κοντά, το μονοπάτι με κατοχή 1, οι διάδρομοι στη λίστα αλλαγών πριν από τις
σειρές του εργοταξίου, το bd_nres που μένει από την προηγούμενη θέση,
το ui_bad χωρίς τον λόγο, και ο πίνακας χωρίς το κόστος στην υπογραφή του.
"""
import ctypes, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import test_place as TP                                  # noqa: E402
from test_terrain import model as res_model              # noqa: E402
import reach                                             # noqa: E402
import cpc                                               # noqa: E402

UI_PLACE = 2
FAIL = []


def check(ok, msg):
    print(("OK " if ok else "ΛΑΘΟΣ ") + msg)
    if not ok:
        FAIL.append(msg)


# --- οι σκηνές ---------------------------------------------------------------
def scene(rnd, G, sym):
    """Ένας τυχαίος κόσμος γύρω από τον κέρσορα. Out: (item, cx, cy, world,
    domes, structs) — οι πίνακες όπως γράφτηκαν στην τράπεζα 6."""
    i = rnd.choice([0, 0, 1, 2, 0, 4, 5, 6, 7, 8, 9, 10, 4])
    kind, param, w, h = G.items[i][:4]
    cx = rnd.randrange(-50, 50)
    cy = rnd.randrange(-50, 50)
    if rnd.random() < 0.04:                 # στο χείλος του κόσμου
        cx = rnd.choice([-128 + w - 2, 126 - w + 2])
    cx, cy = cx + ((cx ^ w) & 1), cy + ((cy ^ h) & 1)
    # Ο κόσμος: χτίσιμο παντού, με εμπόδια σε πυκνότητα που αλλάζει.
    dens = rnd.choice([0, 0.02, 0.08, 0.3])
    good = [0, 0, 1, 7, 0x40, 0x81, 0xC7, 0x08]
    badb = [2, 3, 4, 5, 6, 0x10, 0x20, 0x30, 0x17, 0x27]
    wl = bytearray(rnd.choice(good) if rnd.random() >= dens else rnd.choice(badb)
                   for _ in range(0x4000))
    for k in range(0x4000):
        if max(abs((k & 127) - 64), abs((k >> 7) - 64)) >= 62:
            wl[k] = 3
    # το αποτύπωμα του νέου καθαρό, συνήθως
    if rnd.random() < 0.85:
        tx, ty = (cx - w) >> 1, (cy - h) >> 1
        for y in range(ty, ty + h):
            for x in range(tx, tx + w):
                if -64 <= x < 64 and -64 <= y < 64:
                    wl[reach.widx(x, y)] = rnd.choice(good)
    domes = [[0, 0, 0, 0] for _ in range(64)]
    structs = [[0, 0, 0, 0, 0] for _ in range(32)]
    style = rnd.random()
    nd = 0 if style < 0.08 else rnd.randrange(0, 9)
    ns = 0 if style < 0.08 else rnd.randrange(0, 6)
    slots = rnd.sample(range(64), nd)
    for d in slots:
        size = rnd.randrange(3)
        # Πολλοί σε γεωμετρίες που ο διάδρομος βγαίνει: στον ίδιο άξονα, στη
        # διαγώνιο, ή με στροφή· οι άλλοι σκόρπιοι.
        bx, by = cx & ~1, cy & ~1
        k = rnd.random()
        if k < 0.3:
            off = rnd.choice([-1, 1]) * 2 * rnd.randrange(3, 20)
            dx, dy = (off, 0) if rnd.random() < 0.5 else (0, off)
        elif k < 0.5:
            s = 2 * rnd.randrange(3, 16)
            dx, dy = rnd.choice([-s, s]), rnd.choice([-s, s])
        elif k < 0.75:
            dx, dy = 2 * rnd.randrange(-20, 21), 2 * rnd.randrange(-20, 21)
        else:
            dx, dy = 2 * rnd.randrange(-40, 41), 2 * rnd.randrange(-40, 41)
        domes[d] = [(bx + dx) & 255, (by + dy) & 255, size, rnd.choice([1, 2])]
    for s_ in rnd.sample(range(32), ns):
        kd = rnd.randrange(7)
        size = rnd.randrange(3) if kd < 4 else 0
        dx, dy = rnd.randrange(-44, 45), rnd.randrange(-44, 45)
        structs[s_] = [(cx + dx) & 255, (cy + dy) & 255, kd, size, rnd.choice([1, 2])]
    return i, cx & 255, cy & 255, bytes(wl), domes, structs


def put_scene(G, world, domes, structs):
    G.put(4, 0, world)
    d6 = bytearray(G.bank(6, G.gd, 64 * 24))
    for d, (x, y, s, st) in enumerate(domes):
        d6[24 * d:24 * d + 5] = bytes([x, y, s, 0, st])
    s6 = bytearray(G.bank(6, G.gs, 32 * 8))
    for k, (x, y, kd, s, st) in enumerate(structs):
        s6[8 * k:8 * k + 5] = bytes([x, y, kd, s, st])
    G.put(6, G.gd, d6)
    G.put(6, G.gs, s6)


def expect(G, i, cx, cy, world, domes, structs, dims):
    """(ui_bad, bd_nres, reach-αποτέλεσμα ή None) από την πρόζα."""
    kind, param, w, h = G.items[i][:4]
    tx, ty, out = TP.rect_rule(cx, cy, w, h)
    if out:
        return 255, 0, None
    nb = sum(1 for r in range(h) for c in range(w)
             if not TP.ok_rule(world[(ty + r + 64) * 128 + tx + c + 64]))
    if nb:
        return nb, 0, None
    a, nres = res_model(world, kind, param, w, h, tx, ty)
    if a:
        return 0xF0 + nres, nres, None
    res = reach.plan(world, domes, structs, dims, kind, param, w, h, cx, cy)
    if res["ok"]:
        return 0, 0, res
    return 0xF0 + res["reason"], res["reason"], res


def got_of(G, sym):
    m = G.m
    n = m.peek(sym["AL_N"])
    pt = m.peek(sym["AL_PT"])
    return {"n": n, "lst": list(m.read_ram(sym["AL_LST"], n)), "len": m.peek(sym["AL_LEN"]),
            "pt": pt, "po": m.peek(sym["AL_PO"]) if pt != 255 else None,
            "nres": m.peek(sym["BD_NRES"]),
            "metal": G.w16(sym["CR_METAL"]), "biop": G.w16(sym["CR_BIOP"])}


def want_of(G, i, res, nres):
    lst = [c[0] for c in res["corridors"]] if res else []
    pieces = res["pieces"] if res else 0
    pt = res["path"][0] if res and res["ok"] and res["path"] and not lst else 255
    po = res["path"][1] if pt != 255 else None
    m_, b_ = G.items[i][4], G.items[i][5]
    return {"n": len(lst), "lst": lst, "len": pieces, "pt": pt, "po": po, "nres": nres,
            "metal": m_ + reach.CORR_M * pieces, "biop": b_ + reach.CORR_B * pieces}


def plain():
    """Ενας κόσμος όλος έδαφος, με το περίγραμμα βουνό."""
    wl = bytearray(0x4000)
    for k in range(0x4000):
        if max(abs((k & 127) - 64), abs((k >> 7) - 64)) >= 62:
            wl[k] = 3
    return bytes(wl)


def edges():
    """Οι σκηνές στο ΟΡΙΟ, όπου τα αρνητικά της εμβέλειας δαγκώνουν πάντα:
    (αντικείμενο, κέρσορας, θόλοι, τι πρέπει να βγει)."""
    E = [[0, 0, 0, 0]] * 63
    S = [[0, 0, 0, 0, 0]] * 32
    return [
        # θόλος L στο (0, 0) και θόλος L 20 tiles ανατολικά: 20 - 4 - 4 = 12
        # πλακίδια — και τα κέντρα απέχουν ακριβώς AL_REACH μισά tiles.
        (2, (0, 0), [[40, 0, 2, 2]] + E, S, "1 διάδρομος"),
        (2, (0, 0), [[42, 0, 2, 2]] + E, S, "TOO FAR"),            # 13
        # ηλιακός ανατολικά ενός θόλου S: μονοπάτι 12 tiles, και 13
        (4, (31, 1), [[0, 0, 0, 2]] + E, S, "μονοπάτι"),
        (4, (33, 1), [[0, 0, 0, 2]] + E, S, "TOO FAR")]


def rules(sym, patch=(), n=500, seed=8585):
    """ui_validate απέναντι στο reach.py: η πρώτη διαφορά, ή None."""
    G = TP.Game(sym, patch)
    m = G.m
    rnd = random.Random(seed)
    dims = m.read_ram(sym["G_STRUCT_DIMS"] if "G_STRUCT_DIMS" in sym else layout("G_struct_dims"), 64)
    seen = {"πρώτο κτίριο": 0, "1 διάδρομος": 0, "2+ διάδρομοι": 0, "4 διάδρομοι": 0,
            "μονοπάτι δομής": 0, "μονοπάτι θόλου": 0, "TOO FAR": 0, "PATH BLOCKED": 0,
            "κακά tiles": 0, "έξω": 0, "σχήμα y": 0}
    fixed = edges()
    for case in range(n + len(fixed)):
        G.restore()
        if case < len(fixed):
            i, (cx, cy), domes, structs, what = fixed[case]
            world = plain()
        else:
            i, cx, cy, world, domes, structs = scene(rnd, G, sym)
            what = None
        G.item(i)
        G.cursor(cx, cy)
        put_scene(G, world, domes, structs)
        m.poke(sym["UI_STATE"], UI_PLACE)
        m.poke(sym["BD_NRES"], rnd.randrange(5))
        _, A, _ = G.run("UI_VALIDATE")
        bad, nres, res = expect(G, i, cx, cy, world, domes, structs, dims)
        got, want = got_of(G, sym), want_of(G, i, res if bad == 0 or bad >= 0xF3 else None, nres)
        got["A"], want["A"] = A, bad
        w_after = G.bank(4)
        if w_after != world:
            at = next(k for k in range(0x4000) if w_after[k] != world[k])
            return (f"ui_validate {case} ({sb(cx)}, {sb(cy)}), αντικείμενο {i}: ο κόσμος "
                    f"άλλαξε στο tile ({(at & 127) - 64}, {(at >> 7) - 64}): "
                    f"#{world[at]:02X} -> #{w_after[at]:02X}")
        if got != want:
            diff = {k: (got[k], want[k]) for k in got if got[k] != want[k]}
            return (f"ui_validate {case} ({sb(cx)}, {sb(cy)}), αντικείμενο {i}: "
                    f"(Z80, κανόνας) {diff}")
        if what:                            # η σκηνή του ορίου κάνει ό,τι λέει
            ok = {"1 διάδρομος": bad == 0 and res and len(res["corridors"]) == 1,
                  "μονοπάτι": bad == 0 and res and res["path"] and len(res["path"][2]) == 12,
                  "TOO FAR": bad == 0xF3}[what]
            if not ok:
                return f"η σκηνή ορίου {case} δεν βγάζει «{what}»: ui_bad #{bad:02X}"
        if bad == 255:
            seen["έξω"] += 1
        elif 0 < bad < 0xF0:
            seen["κακά tiles"] += 1
        elif bad == 0xF3:
            seen["TOO FAR"] += 1
        elif bad == 0xF4:
            seen["PATH BLOCKED"] += 1
        elif bad == 0:
            if res and not res["any"] and not res["corridors"]:
                seen["πρώτο κτίριο"] += 1
            k = len(res["corridors"])
            if k == 1:
                seen["1 διάδρομος"] += 1
            elif k >= 2:
                seen["2+ διάδρομοι"] += 1
            if k == 4:
                seen["4 διάδρομοι"] += 1
            if res["path"] and not k:
                seen["μονοπάτι θόλου" if G.items[i][0] == 0 else "μονοπάτι δομής"] += 1
                if res["path"][1]:
                    seen["σχήμα y"] += 1
    if not patch and min(seen.values()) < 3:
        return f"το σενάριο δεν έπιασε ό,τι έπρεπε: {seen}"
    print(f"    {n} θέσεις: {seen}")
    return None


def sb(v):
    return reach.sb(v)


VIEW_TW, VIEW_TH = 20, 10                # src/tiles.asm


def scr(cam, x, y):
    """§8.2: η γραμμή y είναι στο μπλοκ y & 7, και κάθε μπλοκ είναι δαχτυλίδι 2 KB."""
    return 0xC000 + (y & 7) * 0x800 + (((y >> 3) * 80 + x + cam) & 0x7FF)


def play(m, cam):
    """Το κάδρο, 80 x 160, όπως το βλέπει το μάτι — όχι οι λωρίδες του HUD."""
    ram = m.read_ram(0xC000, 0x4000)
    return bytes(ram[scr(cam, x, y) - 0xC000] for y in range(160) for x in range(80))


def ghost(sym, patch=(), n=160, seed=8686):
    """Το φάντασμα του ui_show: ένα σημάδι 2x4 σε κάθε ορατό tile των
    διαδρόμων ή του μονοπατιού, κανένα αλλού, και το ui_hide γυρίζει την οθόνη
    όπως ήταν. Η πρώτη διαφορά, ή None."""
    G = TP.Game(sym, patch)
    m = G.m
    rnd = random.Random(seed)
    dims = m.read_ram(layout("G_struct_dims"), 64)
    ghbuf = layout("PAGE2_TOP")
    seen = {"διάδρομοι": 0, "μονοπάτι": 0, "σημάδια": 0, "μέρος εκτός κάδρου": 0}
    case = 0
    while case < n:
        G.restore()
        i, cx, cy, world, domes, structs = scene(rnd, G, sym)
        bad, nres, res = expect(G, i, cx, cy, world, domes, structs, dims)
        if bad or not (res["corridors"] or res["path"]):
            continue
        case += 1
        G.item(i)
        G.cursor(cx, cy)
        put_scene(G, world, domes, structs)
        m.poke(sym["UI_STATE"], UI_PLACE)
        # η κάμερα: ο κέρσορας κάπου μέσα στο κάδρο, και καμιά φορά στην άκρη
        ctx = (sb(cx) >> 1) - rnd.randrange(2, VIEW_TW - 2)
        cty = (sb(cy) >> 1) - rnd.randrange(1, VIEW_TH - 1)
        m.write_ram(sym["CAM_TX"], bytes([ctx & 255, cty & 255]))
        G.run("GH_RESET")
        cam = 2 * (m.peek(sym["CAM_OFF"]) | m.peek(sym["CAM_OFF"] + 1) << 8)
        before = play(m, cam)
        G.run("UI_SHOW")
        tiles = [t for c in res["corridors"] for t in c[4]] + (res["path"][2] if res["path"] and not res["corridors"] else [])
        want = set()
        for x, y in tiles:
            col, row = x - ctx, y - cty
            if 0 <= col < VIEW_TW and 0 <= row < VIEW_TH:
                want.add(scr(cam, 4 * col + 1, 16 * row + 6))
            else:
                seen["μέρος εκτός κάδρου"] += 1
        end = m.peek(sym["GH_PTR"]) | m.peek(sym["GH_PTR"] + 1) << 8
        log = m.read_ram(ghbuf, end - ghbuf)
        got, k = [], 0
        while k < len(log):
            a, w, h = log[k] | log[k + 1] << 8, log[k + 2], log[k + 3]
            if (w, h) == (2, 4):
                got.append(a)
            k += 4 + w * h
        if len(got) != len(set(got)) or set(got) != want:
            return (f"φάντασμα {case} ({sb(cx)}, {sb(cy)}), αντικείμενο {i}, κάμερα "
                    f"({ctx}, {cty}): {len(got)} σημάδια ({len(set(got))} διαφορετικά), "
                    f"ο κανόνας λέει {len(want)}; λείπουν {len(want - set(got))}, "
                    f"περισσεύουν {len(set(got) - want)}")
        G.run("UI_HIDE")
        if play(m, cam) != before:
            return f"φάντασμα {case}: το ui_hide δεν γύρισε την οθόνη όπως ήταν"
        seen["διάδρομοι" if res["corridors"] else "μονοπάτι"] += 1
        seen["σημάδια"] += len(want)
    if not patch and min(seen.values()) < 5:
        return f"το σενάριο του φαντάσματος δεν έπιασε ό,τι έπρεπε: {seen}"
    print(f"    {n} φαντάσματα: {seen}")
    return None


def layout(name):
    for line in open(os.path.join(ROOT, "build", "layout.asm"), encoding="utf-8"):
        if line.startswith(name):
            return int(line.split("#")[1].split()[0], 16)
    raise KeyError(name)


# --- ο πίνακας ------------------------------------------------------------------
def panel(sym, patch=()):
    """Οι σειρές 3-4 στο PLACE: το σύνολο του κόστους και ο λόγος. Ένας θόλος S
    στο (0, 0) σε καθαρό έδαφος, και γύρω του ό,τι χρειάζεται κάθε σκηνή. Το
    ΙΔΙΟ παιχνίδι από σκηνή σε σκηνή, χωρίς restore: ο πίνακας ξαναγράφεται
    μόνο όταν αλλάζει η υπογραφή του, και αυτό ακριβώς ελέγχεται.
    Η πρώτη διαφορά, ή None."""
    import hudread
    from test_info import same
    G = TP.Game(sym, patch)
    m = G.m
    world = bytearray(0x4000)
    for k in range(0x4000):
        if max(abs((k & 127) - 64), abs((k >> 7) - 64)) >= 62:
            world[k] = 3
    for y in range(-2, 2):
        for x in range(-2, 2):
            world[reach.widx(x, y)] = 0x17
    domes = [[0, 0, 0, 2]] + [[0, 0, 0, 0]] * 63
    structs = [[0, 0, 0, 0, 0]] * 32
    rock = bytearray(world)                 # ένας τοίχος από βράχο, x = 2..8
    for y in range(-3, 4):
        for x in range(2, 9):
            rock[reach.widx(x, y)] = 2
    one = bytearray(world)                  # ένα κακό tile κάτω από τον ηλιακό
    one[reach.widx(30, 0)] = 2
    # (αντικείμενο, κέρσορας, κόσμος, σειρά 3 περιέχει, σειρά 4 αρχίζει)
    steps = [(0, (16, 0), world, ["FE 36", "BI 20"], "READY"),          # 4 πλακίδια
             (0, (18, 0), world, ["FE 42", "BI 23"], "READY"),          # 5: μόνο το κόστος
             (4, (61, 1), world, ["FE 15", "BI  0"], "TOO FAR"),
             (4, (21, 1), rock, ["FE 15"], "PATH BLOCKED"),
             (4, (61, 1), one, ["FE 15"], "BLOCKED"),
             (4, (61, 1), world, ["FE 15"], "TOO FAR"),                 # ο λόγος μόνο
             (1, (20, 0), world, ["FE 54", "BI 29"], "READY")]          # M: 10 - 0 - 3 - 2 = 5
    for k, (i, (cx, cy), wl, r3, r4) in enumerate(steps):
        G.item(i)
        G.cursor(cx, cy)
        put_scene(G, bytes(wl), domes, structs)
        m.poke(sym["UI_STATE"], UI_PLACE)
        G.run("UI_HIDE")
        G.run("UI_SHOW")
        t3, t4 = same(hudread.text(m, sym, 3)), same(hudread.text(m, sym, 4))
        if not all(same(x) in t3 for x in r3) or not t4.startswith(same(r4)) \
                or (r4 == "BLOCKED" and "PATH" in t4):
            return f"πίνακας, βήμα {k} ({cx}, {cy}): |{t3}| |{t4}|, η πρόζα λέει {r3} και «{r4}»"
    return None


# --- ο χρόνος ------------------------------------------------------------------
# µs του ui_validate με το probe, βήμα 85, στην αποικία του §10.1 (μετρημένα:
# 9.124, 14.684, 6.956, 3.558· ως το βήμα 84 μόνο το bd_check, 610-820).
CEIL = {"θόλος, διάδρομος": 9700, "θόλος χωρίς διάδρομο": 15500,
        "ηλιακός, μονοπάτι": 7400, "ηλιακός μακριά": 3800}
TIME_AT = [("θόλος, διάδρομος", 0, 16, -12), ("θόλος χωρίς διάδρομο", 0, 8, -10),
           ("ηλιακός, μονοπάτι", 4, -9, -11), ("ηλιακός μακριά", 4, -37, -23)]


def costs(sym, patch=()):
    G = TP.Game(sym, patch)
    m = G.m
    out = {}
    for name, i, cx, cy in TIME_AT:
        best = None
        for _ in range(2):
            G.restore()
            G.item(i)
            G.cursor(cx, cy)
            m.poke(sym["UI_STATE"], UI_PLACE)
            t, _, _ = G.run("UI_VALIDATE", step=1)
            best = t if best is None else min(best, t)
        out[name] = best
    return out


# --- FIRE, στο παιχνίδι ------------------------------------------------------
# Θέσεις δίπλα στην αποικία του §10.1, στο έδαφος του seed (βρέθηκαν κοιτάζοντας
# το επίπεδο: tools/balance.py, plane, και tools/reach.py): ένας μικρός θόλος
# βόρεια του καταλύματος, που παίρνει διάδρομο δύο πλακιδίων, και ένας ηλιακός
# βορειοδυτικά του θόλου οξυγόνου, που παίρνει μονοπάτι επτά tiles.
#
# Ο θόλος M ξεκινά διαγώνιο από τη γωνία του αποτυπώματός του, που τη
# ζωγραφίζει και η σειρά του εργοταξίου (dh_site): το test_fit το βρήκε. Ο S στο
# (8, 8) δένεται και με τους τρεις θόλους της αρχής — ο βαρύτερος γύρος FIRE
# που έχει η αποικία. Το τελευταίο πεδίο ζητά από τον κανόνα να έχει η σκηνή
# αυτό που δοκιμάζει.
diag = lambda cx, cy, p: lambda res: any(c[3][0][0] & 1 and c[1] == (cx, cy, p)
                                          for c in res["corridors"])
FIRE_MS = 200                            # όπως η τοποθέτηση θόλου L (test_reveal)
FIRE_PATH_MS = 140                       # μετρημένο 127: μόνο τα tiles του μονοπατιού·
                                         # 171 με τα ορθογώνια κέντρο-γωνία-κέντρο
FIRE_AT = [("θόλος S", 0, (16, -12), (4, -9), None),
           ("ηλιακός", 4, (-9, -11), (-12, -9), None),
           ("θόλος M, διαγώνιος", 1, (-18, 30), (-18, 10), diag(-18, 30, 1)),
           ("θόλος S, τρεις διάδρομοι", 0, (8, 8), (-6, -2),
            lambda res: len(res["corridors"]) == 3)]


def fire(sym, g, patch=()):
    """Το FIRE χτίζει ό,τι έδειξε το φάντασμα. Η πρώτη διαφορά, ή None."""
    import test_reveal as R
    import balance as B
    from cpc import JOY_FIRE
    G = R.Game(sym, g)
    m = G.m
    for at, v in patch:
        m.poke(at, v)
    dims = m.read_ram(layout("G_struct_dims"), 64)
    nodes, adj = layout("G_rt_nodes"), layout("G_node_adj")
    corr = layout("G_corr_tbl") - 0x4000
    items = [bytes(m.read_ram(sym["BLD_ITEMS"] + 8 * i, 8)) for i in range(11)]
    for name, item, (cx, cy), cam, need in FIRE_AT:
        G.camera(*cam)
        B.build(m, sym, item, g + 6, at=(cx, cy), place=False)
        G.settle()
        kind, param, w, h, cost_m, cost_b = items[item][:6]
        b4 = bytes(G.bank(4)[:0x4000])
        b6 = bytes(G.bank(6)[:0x4000])
        domes = [list(b6[R.DOME_TBL + 24 * d:R.DOME_TBL + 24 * d + 4]) for d in range(64)]
        structs = [list(b6[R.STRUCT_TBL + 8 * k:R.STRUCT_TBL + 8 * k + 5]) for k in range(32)]
        res = reach.plan(b4, domes, structs, dims, kind, param, w, h, cx, cy)
        if not res["ok"] or not (res["corridors"] or res["path"]):
            return f"{name} στο ({cx}, {cy}): ο κανόνας δεν το δένει πουθενά — {res['reason']}"
        if need and not need(res):
            return f"{name}: η σκηνή δεν έχει αυτό που δοκιμάζει — {len(res['corridors'])} διάδρομοι"
        deg0 = m.read_ram(nodes, 96)
        stock0 = (G.m.peek(g + 6) | G.m.peek(g + 7) << 8, G.m.peek(g + 8) | G.m.peek(g + 9) << 8)
        ncorr0 = sum(1 for k in range(96) if b6[corr + 5 * k + 4])
        G.run(40_000)
        G.iters = []                         # μόνο ο γύρος του FIRE και οι σειρές
        G.stick(JOY_FIRE)
        # ΩΣ ΝΑ ΒΓΕΙ Η ΤΕΛΕΥΤΑΙΑ ΣΕΙΡΑ: εργοτάξιο M και διαγώνιος είναι
        # δώδεκα και πλέον στοιχεία της λίστας, ένα-δύο ανά γύρο, και ως τότε το
        # φάντασμα περιμένει (ui_owed) — η πλήρης σχεδίαση το έχει ήδη.
        G.run(5_000_000, until=lambda: not (m.peek(sym["RV_PEND"]) or m.peek(sym["UI_OWED"])
                                            or m.peek(sym["DIRTY_NUM"])))
        laid, cap = G.worst(), FIRE_PATH_MS if res["path"] else FIRE_MS
        if laid >= cap:
            return f"{name}: ο χειρότερος γύρος του FIRE {laid:.0f} ms (όριο {cap})"
        # --- ο κόσμος: το αποτύπωμα θεμέλιο (bd_commit), και οι δεσμοί
        want = bytearray(b4)
        tx, ty = (cx - w) >> 1, (cy - h) >> 1
        for y in range(ty, ty + h):
            for x in range(tx, tx + w):
                k = reach.widx(x, y)
                want[k] = want[k] & 0xC0 | 0x17
        want = reach.stamp(bytes(want), res)
        got = bytes(G.bank(4)[:0x4000])
        if got != want:
            k = next(k for k in range(0x4000) if got[k] != want[k])
            return (f"{name}: ο κόσμος στο tile ({(k & 127) - 64}, {(k >> 7) - 64}) "
                    f"#{got[k]:02X}, ο κανόνας λέει #{want[k]:02X}")
        # --- ο γράφος: ο νέος κόμβος με κάθε άκρη, και ανάποδα
        node = m.peek(sym["BD_NODE"])
        ends = [c[0] for c in res["corridors"]] or [res["path"][0]]
        deg = m.read_ram(nodes, 96)
        nb = lambda a: [m.peek(adj + 8 * a + j) for j in range(deg[a])]
        for e in ends:
            if e not in nb(node) or node not in nb(e):
                return f"{name}: λείπει η ακμή {node} <-> {e}: {nb(node)} / {nb(e)}"
        if deg[node] != len(ends) or sum(deg) - sum(deg0) != 2 * len(ends):
            return f"{name}: βαθμοί {deg[node]} και +{sum(deg) - sum(deg0)}, ο κανόνας {len(ends)}"
        # --- οι διάδρομοι στον πίνακα, και το κόστος
        b6 = bytes(G.bank(6)[:0x4000])
        ncorr = sum(1 for k in range(96) if b6[corr + 5 * k + 4])
        want_c = sum(len(c[3]) for c in res["corridors"])
        stock = (G.m.peek(g + 6) | G.m.peek(g + 7) << 8, G.m.peek(g + 8) | G.m.peek(g + 9) << 8)
        paid = (stock0[0] - stock[0], stock0[1] - stock[1])
        want_p = (cost_m + reach.CORR_M * res["pieces"], cost_b + reach.CORR_B * res["pieces"])
        if ncorr - ncorr0 != want_c or paid != want_p:
            return (f"{name}: εγγραφές διαδρόμων +{ncorr - ncorr0} (κανόνας {want_c}), "
                    f"πληρωμή {paid} (κανόνας {want_p})")
        # --- και η οθόνη
        pic, ref = G.truth()
        if pic != ref:
            k = next(k for k in range(len(pic)) if pic[k] != ref[k])
            return f"{name}: η οθόνη διαφέρει από την πλήρη σχεδίαση στο byte {k % 80}, γραμμή {k // 80}"
        print(f"    {name}: {len(ends)} δεσμός/οί ({'διάδρομος' if res['corridors'] else 'μονοπάτι'}), "
              f"πληρωμή {paid}, χειρότερος γύρος {laid:.0f} ms")
    return None


# --- αρνητικά ------------------------------------------------------------------
def find(m, at, pat, span=96):
    """Η διεύθυνση του μοτίβου μέσα σε `span` bytes από το `at`."""
    code = m.read_ram(at, span + len(pat))
    k = next((k for k in range(span) if list(code[k:k + len(pat)]) == pat), None)
    assert k is not None, f"το μοτίβο {pat} δεν βρέθηκε μετά το #{at:04X}"
    return at + k


def negatives(sym, g):
    m = TP.Game(sym).m
    w = lambda a: [a & 255, a >> 8]
    al_cor, al_cbk = find(m, sym["AL_COR"], [0xFE, 13]), find(m, sym["AL_CBK"], [0x3E, 12])
    alf = find(m, sym["AL_FIND"], [0x3E, 13], 160)
    far = find(m, sym["AL_FAR"], [0xFE, 41])
    neg = [
        ("εμβέλεια 13", rules, [(al_cor + 1, 14), (al_cbk + 1, 13), (alf + 1, 14), (far + 1, 43)]),
        ("χωρίς την προσωρινή σφραγίδα", rules,
         [(find(m, sym["AL_CTMP"], [0xCB, 0xEE]) + k, 0) for k in (0, 1)]),
        ("χωρίς το ξεσφράγισμα", rules,
         [(find(m, sym["AL_CUNT"], [0xCB, 0xAE]) + k, 0) for k in (0, 1)]),
        ("μόνο το πρώτο Γ", rules, [(sym["AL_LTRY"] - 2, 0xC9), (sym["AL_LTRY"] - 1, 0)]),
        ("το γρήγορο «όχι» ένα tile πιο κοντά", rules, [(far + 1, 39)]),
        ("το μονοπάτι με κατοχή 1", "fire", [(find(m, sym["AL_CBS"], [0xF6, 0x27]) + 1, 0x17)]),
        # Η σειρά ως το test_fit: al_commit πριν από το bd_redraw, χωρίς push/pop.
        ("οι διάδρομοι πριν από το εργοτάξιο", "fire",
         list(zip(range(find(m, sym["UIP_FIRE"], [0xCD] + w(sym["BD_REDRAW"]) + [0xF5, 0xCD]
                             + w(sym["AL_COMMIT"]) + [0xF1], 60), 10**6),
                  [0xCD] + w(sym["AL_COMMIT"]) + [0, 0xCD] + w(sym["BD_REDRAW"]) + [0]))),
        ("το bd_nres που μένει από την προηγούμενη θέση", rules,
         [(find(m, sym["UI_VALIDATE"], [0x32] + w(sym["BD_NRES"]), 20) + k, 0) for k in range(3)]),
        ("το ui_bad χωρίς τον λόγο", panel,
         [(find(m, sym["AL_PLAN"], [0xCA] + w(sym["UID_OUT"]), 120), 0xC3)]),
        ("ο πίνακας χωρίς το κόστος στην υπογραφή", panel,
         [(a, v) for a, v in zip(range(find(m, sym["UIP_START"], [0x3A] + w(sym["CR_METAL"]), 200), 10**6),
                                 [0x7E, 0, 0])]),
    ]
    for name, fn, patch in neg:
        err = fire(sym, g, patch) if fn == "fire" else fn(sym, patch)
        check(err is not None, f"αρνητικό «{name}»: " + (err or "ΔΕΝ το έπιασε τίποτα"))


def main():
    sym, g = TG.build()
    err = rules(sym) if not os.environ.get("ONLY") else None
    check(err is None, err or "ui_validate = ο κανόνας του reach.py σε κάθε σκηνή")
    err = ghost(sym) if not os.environ.get("ONLY") else None
    check(err is None, err or "το φάντασμα δείχνει ακριβώς τα tiles των δεσμών, και φεύγει καθαρά")
    err = fire(sym, g)
    check(err is None, err or "το FIRE χτίζει ό,τι έδειξε το φάντασμα, και η οθόνη είναι η πλήρης σχεδίαση")
    err = panel(sym)
    check(err is None, err or "ο πίνακας λέει το σύνολο του κόστους και τον λόγο, και αλλάζει με τον λόγο")
    t = costs(sym)
    for k, v in t.items():
        check(v <= CEIL[k], f"ui_validate, {k}: {v} us (ταβάνι {CEIL[k]})")
    negatives(sym, g)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
