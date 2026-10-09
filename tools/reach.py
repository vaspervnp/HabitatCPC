"""Πώς ένα νέο κτίσμα δένεται με την αποικία — ο κανόνας των βημάτων 85 και 86
(DESIGN §9.3), σε εκτελέσιμη μορφή. Η αναφορά των δοκιμών και του
tools/balance.py· γραμμένη από την πρόζα, όχι από τον Z80.

  * Κάθε κτίσμα θέλει κάποιο του σωστού είδους ως RANGE = 12 tiles μακριά. Αν
    δεν υπάρχει ΚΑΝΕΝΑ τέτοιο σε όλο τον κόσμο, μπαίνει όπου το επιτρέπει το
    έδαφος (το πρώτο κτίσμα).
  * ΘΟΛΟΣ: σκεπαστός διάδρομος (tools/route.py) προς ΚΑΘΕ θόλο, με τη σειρά του
    πίνακα, και μετά προς κάθε airlock που δεν έχει ακόμη τον διάδρομό του
    (ST_JOINED, βήμα 87· ως το 86 «χωρίς ακμή»), που ο διάδρομος
    φτάνει με το πολύ 12 πλακίδια και πατά μόνο tiles που χτίζονται — ή tiles
    των δύο άκρων — ως MAX = 4. Κάθε διάδρομος που διαλέγεται πιάνει τα tiles
    του για τους επόμενους. «Υπάρχει» = υπάρχει θόλος. Χωρίς διάδρομο: κόκκινος
    (βήμα 86· ως το 85 έπαιρνε μονοπάτι).
  * AIRLOCK: ΕΝΑΣ διάδρομος, προς τον θόλο με τον κοντύτερο (σε ισοπαλία τον
    πρώτο του πίνακα). Το airlock είναι άκρο μεγέθους -1 και ο διάδρομος βγαίνει
    από τον θόλο. «Υπάρχει» = υπάρχει θόλος.
  * ΔΟΜΗ: μονοπάτι στο έδαφος προς το κοντινότερο airlock ή άλλη δομή (64 +
    δομή), ποτέ σε θόλο: ένα Γ από το κεντρικό tile της νέας στο κεντρικό tile
    της άλλης, πρώτα κατά x και μετά κατά y, ή ανάποδα· μετρούν τα tiles έξω από
    τα δύο αποτυπώματα, το πολύ 12, όλα να χτίζονται. Το κοντύτερο· σε ισοπαλία
    το πρώτο που βρέθηκε. «Υπάρχει» = υπάρχει δομή.
  * ΤΟ ΣΚΑΦΟΣ (βήμα 87) δεν είναι κτίριο: δεν είναι «κοντά», ούτε κάνει μια
    δομή να μην είναι η πρώτη. Στέκεται στη θέση 0 των δομών.
  * Αλλιώς ο λόγος: 4 PATH BLOCKED αν κάποιος διάδρομος ή Γ ως 12 βρήκε έδαφος
    που δεν χτίζεται· αλλιώς 5 NO CORRIDOR FITS αν ένας υποψήφιος θόλος ήταν
    τόσο κοντά που ένας αξονικός θα χωρούσε (max(S, T) - ακτίνες <= 12) αλλά
    σχήμα δεν βγαίνει· αλλιώς 3 TOO FAR.

Ο,τι ΔΕΝ πήρε μονοπάτι (θόλος, airlock, η πρώτη δομή) παίρνει στο FIRE μια
σύνδεση εδάφους ως την «άγκυρα» (anchor): το κοντινότερο σκάφος ή airlock, σε
max(|dx|, |dy|) μισά tiles. Οι διάδρομοι γράφονται τότε, αλλά γίνονται ακμές
μόνο όταν είναι έτοιμες και οι δύο άκρες τους (βήμα 87).

Υποψήφιος είναι ό,τι το κέντρο του απέχει ως REACH μισά tiles σε κάθε άξονα
(το al_far: διαφορά σε 8 bits, και ό,τι ξεχειλίζει είναι μακριά).

Οι συντεταγμένες είναι του Z80: κέντρα σε μισά tiles σε ένα byte, tiles
προσημασμένα. Ένα «έξω από τον κόσμο» σε τυχαίο πίνακα κάνει ό,τι και το byte
(sb), ώστε η σύγκριση να πιάνει και αυτό.
"""
import route

RANGE = 12
MAX = 4
REACH = 2 * (RANGE + 8)         # μισά tiles: το al_far
K_AIRLOCK = 5
K_SHIP = 7
MAX_DEGREE = 8
CORR_M, CORR_B = 6, 3           # ο διάδρομος ανά πλακίδιο (κατάλογος του build.asm)
W_OCC_PATH = 0x20
FOUNDATION = 7


def sb(v):
    v &= 255
    return v - 256 if v > 127 else v


def ok_tile(b):
    """Το bd_ok: χωρίς κατοχή, και έδαφος, σκόνη ή θεμέλιο."""
    return not b & 0x30 and b & 7 in (0, 1, 7)


def widx(x, y):
    return (y + 64) * 128 + x + 64


def corridor_tiles(f, fs, t, runs):
    """Τα tiles που πατά ένας διάδρομος από το f (κέντρο, μέγεθος fs) προς το
    t, με τη σειρά, το καθένα μία φορά — το cr_walk."""
    btx, bty = sb(f[0]) >> 1, sb(f[1]) >> 1
    ka, ra = route.DIAG_K[fs], route.RADIUS[fs] // 2
    sx, sy = (sb(t[0]) - sb(f[0])) // 2, (sb(t[1]) - sb(f[1])) // 2
    Sd, Td = abs(sx), abs(sy)
    ux, uy = (sx > 0) - (sx < 0), (sy > 0) - (sy < 0)
    out = []
    d0, n0 = runs[0]
    if d0 & 1:
        for i in range(n0):
            j = ka + i
            lx, ly = ux * j, uy * j
            t1, t2 = (((lx - 1, ly - 1), (lx, ly)) if ux == uy
                      else ((lx - 1, ly), (lx, ly - 1)))
            back, front = (t1, t2) if ux > 0 else (t2, t1)
            out += ([back] if i == 0 else []) + [front]
        if len(runs) > 1:
            d1, n1 = runs[1]
            vx, vy = route.DIR_U[d1]
            if vx:
                c, r = ux * Td - (1 if ux > 0 else 0), uy * Td
                for _ in range(n1):
                    if (c, r) not in out:
                        out.append((c, r))
                    c += vx
            else:
                r, c = uy * (Sd - 1) - (1 if uy < 0 else 0), ux * Sd
                for _ in range(n1):
                    if (c, r) not in out:
                        out.append((c, r))
                    r += vy
    elif d0 in (2, 6):
        c = ra if ux > 0 else -ra - 1
        for _ in range(n0):
            out.append((c, 0))
            c += ux
    else:
        r = ra if uy > 0 else -ra - 1
        for _ in range(n0):
            out.append((0, r))
            r += uy
    return [(sb(x + btx), sb(y + bty)) for x, y in out]


def in_dome(cx, cy, size, x, y):
    """Το tile μέσα στο τετράγωνο αποτύπωμα ενός θόλου (crk_in)."""
    r = size + 2
    return ((x - (sb(cx) >> 1) + r) & 255) < 2 * r and ((y - (sb(cy) >> 1) + r) & 255) < 2 * r


def in_rect(rc, x, y):
    x0, y0, w, h = rc
    return ((x - x0) & 255) < w and ((y - y0) & 255) < h


def footprint(node, domes, structs, dims):
    """(rect, κεντρικό tile) ενός κόμβου, ή None για άδεια θέση."""
    if node < 64:
        cx, cy, size, st = domes[node][:4]
        w = h = 4 + 2 * size
    else:
        cx, cy, kind, size, st = structs[node - 64][:5]
        i = (kind * 8 + size * 2) & 255
        w, h = (dims[i] >> 2) & 0x3F, (dims[i + 1] >> 4) & 0x0F
    if not st:
        return None
    rc = (sb(cx - w) >> 1, sb(cy - h) >> 1, w, h)
    return rc, (sb(cx) >> 1, sb(cy) >> 1)


def lwalk(p, q, ori):
    """Τα tiles του Γ από το p στο q, χωρίς το p: ori 0 = πρώτα κατά x."""
    k = (q[0], p[1]) if ori == 0 else (p[0], q[1])
    out = []
    x, y = p
    for b in (k, q):
        dx = (b[0] > x) - (b[0] < x)
        dy = (b[1] > y) - (b[1] < y)
        while (x, y) != b:
            x, y = x + dx, y + dy
            out.append((x, y))
    return out


def near(a, b):
    """Το al_far: |b - a| <= REACH μισά tiles, με τη διαφορά σε 8 bits."""
    d = sb(b) - sb(a)
    return -128 <= d <= 127 and abs(d) <= REACH


def joined(s):
    """Το ST_JOINED μιας εγγραφής δομής (cx, cy, kind, size, state[, integ,
    joined]): το airlock έχει ήδη τον διάδρομό του."""
    return s[6] if len(s) > 6 else 0


def ship0(structs):
    """Η θέση 0 είναι το σκάφος: το πέρασμα των δομών ξεκινά από την 1."""
    return 1 if structs[0][2] == K_SHIP else 0


def plan(world, domes, structs, dims, kind, param, w, h, cx, cy):
    """Ο κανόνας για ένα αποτύπωμα που ΗΔΗ πατά.

    world: 16 KB, το επίπεδο (δεν αλλάζει)· domes: 64 x (cx, cy, size, state)·
    structs: 32 x (cx, cy, kind, size, state[, integ, joined])· dims: το
    struct_dims.
    Out: dict με ok, reason (0, 3 TOO FAR, 4 PATH BLOCKED, 5 NO CORRIDOR FITS),
    corridors [(κόμβος, από, προς, runs, tiles)], pieces, path (κόμβος, ori,
    tiles) ή None, και any (υπάρχει κάτι του είδους του).
    """
    wl = bytearray(world)
    out = {"corridors": [], "pieces": 0, "path": None, "reason": 0, "any": False}
    why = {"blocked": False, "shape": False}
    new = ((sb(cx) - w) >> 1, (sb(cy) - h) >> 1, w, h)
    lock = kind != 0 and param == K_AIRLOCK

    def corridor(node, a, bb, hold):
        """Ο διάδρομος ανάμεσα στο a και στο bb (cx, cy, size), ή None. Θυμάται
        γιατί όχι στο why."""
        r = route.plan(sb(a[0]), sb(a[1]), a[2], sb(bb[0]), sb(bb[1]), bb[2])
        if r is None:
            S = abs(sb(bb[0]) - sb(a[0])) // 2
            T = abs(sb(bb[1]) - sb(a[1])) // 2
            if max(S, T) - (a[2] + 2) - (bb[2] + 2) <= RANGE:
                why["shape"] = True
            return None
        side, runs = r
        pieces = sum(n for _, n in runs)
        if pieces > RANGE:
            return None
        f, t = (a, bb) if side == 0 else (bb, a)
        tl = corridor_tiles(f[:2], f[2], t[:2], runs)
        for x, y in tl:
            if not (-64 <= x < 64 and -64 <= y < 64):
                why["blocked"] = True
                return None
            if ok_tile(wl[widx(x, y)]):
                continue
            if in_dome(*a, x, y) or in_dome(*bb, x, y):
                continue
            why["blocked"] = True
            return None
        if hold:                            # πιάνει τα tiles του, έξω από τα άκρα
            for x, y in tl:
                if not (in_dome(*a, x, y) or in_dome(*bb, x, y)):
                    wl[widx(x, y)] |= 0x20
        return (node, f, t, runs, tl), pieces

    if kind == 0:
        a = (cx, cy, param)
        targets = [(b, (bcx, bcy, bs)) for b, (bcx, bcy, bs, st) in
                   ((b, domes[b][:4]) for b in range(64)) if st]
        out["any"] = bool(targets)
        targets += [(64 + k, (structs[k][0], structs[k][1], route.AIRLOCK))
                    for k in range(ship0(structs), 32)
                    if structs[k][4] and structs[k][2] == K_AIRLOCK
                    and not joined(structs[k])]
        for node, bb in targets:
            if len(out["corridors"]) == MAX:
                break
            if not (near(cx, bb[0]) and near(cy, bb[1])):
                continue
            c = corridor(node, a, bb, True)
            if c:
                out["corridors"].append(c[0])
                out["pieces"] += c[1]
    elif lock:
        a = (cx, cy, route.AIRLOCK)
        best = None
        for b in range(64):
            bcx, bcy, bs, st = domes[b][:4]
            if not st:
                continue
            out["any"] = True
            if not (near(cx, bcx) and near(cy, bcy)):
                continue
            c = corridor(b, a, (bcx, bcy, bs), False)
            if c and (best is None or c[1] < best[1]):
                best = c
        if best:
            out["corridors"].append(best[0])
            out["pieces"] = best[1]
    else:
        p = (sb(cx) >> 1, sb(cy) >> 1)
        best = RANGE + 1
        for node in range(64 + ship0(structs), 96):
            fp = footprint(node, domes, structs, dims)
            if fp is None:
                continue
            out["any"] = True
            rc, q = fp
            if abs(q[0] - p[0]) > RANGE + 8 or abs(q[1] - p[1]) > RANGE + 8:
                continue
            for ori in (0, 1):
                cnt, bad = 0, False
                tl = []
                for x, y in lwalk(p, q, ori):
                    if in_rect(new, x, y) or in_rect(rc, x, y):
                        continue
                    if not ok_tile(world[widx(x, y)]):
                        bad = True
                    cnt += 1
                    tl.append((x, y))
                    if cnt > RANGE:
                        break
                if cnt > RANGE:
                    continue
                if bad:
                    why["blocked"] = True
                    continue
                if cnt < best:
                    best = cnt
                    out["path"] = (node, ori, tl)
    if out["corridors"] or out["path"] or not out["any"]:
        out["ok"] = True
        return out
    out["ok"] = False
    out["reason"] = 4 if why["blocked"] else 5 if why["shape"] else 3
    return out


def anchor(structs, deg, node, cx, cy):
    """Το lk_anchor: το κοντινότερο σκάφος ή airlock (ζωντανό ή εργοτάξιο),
    όχι ο ίδιος ο `node`, με βαθμό κάτω από MAX_DEGREE· απόσταση max(|dx|,
    |dy|) σε μισά tiles από το (cx, cy), με τη διαφορά σε 8 bits (254 αν
    ξεχειλίζει). Σε ισοπαλία το πρώτο. 255 αν κανένα."""
    best, out = 255, 255
    for k in range(32):
        s = structs[k]
        n = 64 + k
        if not s[4] or s[2] not in (K_SHIP, K_AIRLOCK) or n == node \
                or deg[n] >= MAX_DEGREE:
            continue
        d = 0
        for a, b in ((s[0], cx), (s[1], cy)):
            v = sb(a) - sb(b)
            d = max(d, 254 if not -128 <= v <= 127 else abs(v))
        if d < best:
            best, out = d, n
    return out


def ground(world, new, p, fp):
    """Η σύνδεση εδάφους ζωγραφισμένη (βήμα 94, lk_draw και al_cbr): το Γ
    πρώτα κατά x από το κεντρικό tile p του νέου (αποτύπωμα new) ως το κεντρικό
    tile της άγκυρας (fp = footprint(...)), έξω από τα δύο αποτυπώματα.
    Θεμέλιο ΧΩΡΙΣ κατοχή όπου το tile είναι ελεύθερο έδαφος που χτίζεται
    (ok_tile), με το decor του· αλλού τίποτα. Χωρίς όριο μήκους."""
    wl = bytearray(world)
    rc, q = fp
    for x, y in lwalk(p, q, 0):
        if in_rect(new, x, y) or in_rect(rc, x, y):
            continue
        i = widx(x, y)
        if ok_tile(wl[i]):
            wl[i] = wl[i] & 0xC0 | FOUNDATION
    return bytes(wl)


def stamp(world, res):
    """Ο κόσμος μετά το FIRE: τα tiles του μονοπατιού θεμέλιο με κατοχή 2, το
    decor μένει· των διαδρόμων κατοχή 1 (cr_stamp)."""
    wl = bytearray(world)
    if res["path"]:
        for x, y in res["path"][2]:
            i = widx(x, y)
            wl[i] = wl[i] & 0xC0 | W_OCC_PATH | FOUNDATION
    for c in res["corridors"]:
        for x, y in c[4]:
            if -64 <= x < 64 and -64 <= y < 64:
                wl[widx(x, y)] |= 0x10
    return bytes(wl)
