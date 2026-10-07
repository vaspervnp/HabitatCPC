"""Πώς ένα νέο κτίσμα δένεται με την αποικία — ο κανόνας του βήματος 85
(DESIGN §9.3), σε εκτελέσιμη μορφή. Η αναφορά των δοκιμών και του
tools/balance.py· γραμμένη από την πρόζα, όχι από τον Z80.

  * Το πρώτο κτίσμα του κόσμου μπαίνει όπου το επιτρέπει το έδαφος.
  * Κάθε επόμενο θέλει κάποιο κτίσμα ως RANGE = 12 tiles μακριά:
      - ένας θόλος παίρνει σκεπαστό διάδρομο (tools/route.py) προς ΚΑΘΕ θόλο,
        με τη σειρά του πίνακα, που ο διάδρομος φτάνει με το πολύ 12 πλακίδια
        και πατά μόνο tiles που χτίζονται — ή tiles των δύο άκρων — ως MAX = 4.
        Κάθε διάδρομος που διαλέγεται πιάνει τα tiles του για τους επόμενους.
      - μια δομή, ή ένας θόλος χωρίς διάδρομο, παίρνει μονοπάτι στο έδαφος
        προς το κοντινότερο κτίσμα (θόλοι 0-63 και μετά δομές, 64 + δομή): ένα
        Γ από το κεντρικό tile του νέου στο κεντρικό tile του άλλου, πρώτα κατά
        x και μετά κατά y, ή ανάποδα· μετρούν τα tiles έξω από τα δύο
        αποτυπώματα, το πολύ 12, όλα να χτίζονται. Το κοντύτερο· σε ισοπαλία το
        πρώτο που βρέθηκε.
  * Αλλιώς: «TOO FAR» αν κανένα δεν φτάνει, «PATH BLOCKED» αν κάποιο Γ ως 12
    tiles βρήκε έδαφος που δεν χτίζεται.

Οι συντεταγμένες είναι του Z80: κέντρα σε μισά tiles σε ένα byte, tiles
προσημασμένα. Ένα «έξω από τον κόσμο» σε τυχαίο πίνακα κάνει ό,τι και το byte
(sb), ώστε η σύγκριση να πιάνει και αυτό.
"""
import route

RANGE = 12
MAX = 4
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


def plan(world, domes, structs, dims, kind, param, w, h, cx, cy):
    """Ο κανόνας για ένα αποτύπωμα που ΗΔΗ πατά.

    world: 16 KB, το επίπεδο (δεν αλλάζει)· domes: 64 x (cx, cy, size, state)·
    structs: 32 x (cx, cy, kind, size, state)· dims: το struct_dims.
    Out: dict με ok, reason (0, 3 TOO FAR, 4 PATH BLOCKED), corridors
    [(θόλος, από_κέντρο, μέγεθος, προς, runs, tiles)], pieces, path (κόμβος, ori,
    tiles) ή None, και any (υπάρχει χτισμένο).
    """
    wl = bytearray(world)
    out = {"corridors": [], "pieces": 0, "path": None, "reason": 0, "any": False}
    new = ((sb(cx) - w) >> 1, (sb(cy) - h) >> 1, w, h)
    if kind == 0:
        for b in range(64):
            bcx, bcy, bs, st = domes[b][:4]
            if not st:
                continue
            r = route.plan(sb(cx), sb(cy), param, sb(bcx), sb(bcy), bs)
            if r is None:
                continue
            side, runs = r
            pieces = sum(n for _, n in runs)
            if pieces > RANGE:
                continue
            a = (cx, cy, param)
            bb = (bcx, bcy, bs)
            f, t = (a, bb) if side == 0 else (bb, a)
            tl = corridor_tiles(f[:2], f[2], t[:2], runs)
            bad = False
            for x, y in tl:
                if not (-64 <= x < 64 and -64 <= y < 64):
                    bad = True
                    break
                if ok_tile(wl[widx(x, y)]):
                    continue
                if in_dome(*a, x, y) or in_dome(*bb, x, y):
                    continue
                bad = True
                break
            if bad:
                continue
            for x, y in tl:                 # πιάνει τα tiles του, έξω από τα άκρα
                if not (in_dome(*a, x, y) or in_dome(*bb, x, y)):
                    wl[widx(x, y)] |= 0x20
            out["corridors"].append((b, f, t, runs, tl))
            out["pieces"] += pieces
            if len(out["corridors"]) == MAX:
                break
        if out["corridors"]:
            out["ok"] = True
            return out
    p = (sb(cx) >> 1, sb(cy) >> 1)
    best, why = RANGE + 1, False
    for node in range(96):
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
                why = True
                continue
            if cnt < best:
                best = cnt
                out["path"] = (node, ori, tl)
    if out["path"] or not out["any"]:
        out["ok"] = True
        return out
    out["ok"] = False
    out["reason"] = 4 if why else 3
    return out


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
