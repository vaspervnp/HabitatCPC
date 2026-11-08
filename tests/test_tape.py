#!/usr/bin/env python3
"""Η κορδέλα του εργοταξίου (βήμα 202, DESIGN §6.9).

Ο παίκτης: «να φαίνεται περίγραμμα εκεί που θα ζωγραφιστεί αυτό που ζήτησα να
χτίσω». Οι αποφάσεις του: πλαίσιο όπως το πράσινο της τοποθέτησης, κίτρινο
όπως το σήμα του εργοταξίου, διακεκομμένο, ως να τελειώσει ο μηχανικός, και
πάνω στο κτίριο, σαν κορδέλα.

  ΚΟΡΔΕΛΑ     όσο ένα κτίριο είναι εργοτάξιο, η οθόνη διαφέρει από τη
              σχεδίαση χωρίς κορδέλα (το tk_draw ένα ret) ΜΟΝΟ στις θέσεις
              της πρόζας, και εκεί είναι κίτρινη (pen 6, #3C): στο πλαίσιο του
              θόλου (2 QW bytes x 2 QH γραμμές από το d_fx, d_fy) ή της δομής
              (το struct_dims, κέντρο μείον το μισό), οι δύο πάνω και οι δύο
              κάτω γραμμές στα bytes x με x mod 4 = 0 ή 3, και το πρώτο και το
              τελευταίο byte στις γραμμές y με (y + 4) mod 16 < 8 — από την
              αρχή του πλαισίου. Τουλάχιστον τα 4/5 των θέσεων κίτρινα· όσες
              όχι, τις σκεπάζει κάτι που ζωγραφίζεται μετά (οι άποικοι).
  ΑΛΗΘΕΙΑ     μετά από κάθε φορτίο, και όταν τελειώσει, η οθόνη είναι ίδια με
              πλήρη σχεδίαση: οι σειρές που φάνηκαν ξαναζωγραφίζονται με την
              κορδέλα (dh_rise), ο αρμός ενός νέου διαδρόμου επίσης (dh_conn).
  ΤΕΛΟΣ       όταν τελειώσει ο μηχανικός, όλο το αποτύπωμα ξαναζωγραφίζεται
              (st_site): καμία θέση δεν διαφέρει από τη σχεδίαση χωρίς κορδέλα.
  ΚΟΜΜΑΤΙΑ    η κορδέλα του θόλου L μόνη της, με το clip σε λωρίδες γραμμών,
              στοιχισμένες στις τέσσερις και όχι: πάνω σε σχεδίαση χωρίς
              κορδέλα αλλάζουν ακριβώς οι θέσεις της πρόζας μέσα στη λωρίδα.
  ΜΕΤΕΩΡΙΤΗΣ  μια δομή που ένας μετεωρίτης κάνει πάλι εργοτάξιο έχει ξανά
              κορδέλα, και η οθόνη είναι η πλήρης σχεδίαση.

Στην αποικία δοκιμών, χωρίς αποθέματα: θόλος S (οι θέσεις 3 και 4 του
δακτυλίου πέφτουν στην αριστερή πλευρά), θόλος L, ηλιακό, ορυχείο (4x4),
airlock (2x2). Ο S και το ηλιακό μετά με αποθέματα ως να τελειώσουν. Δύο θόλοι
S εργοτάξια στην ίδια σειρά: ο διάδρομος του δεύτερου φέρνει αρμό στον πρώτο.

Αρνητικά, με τον κώδικα πειραγμένο στη μνήμη: ο θόλος χωρίς κορδέλα (το
ob_fittings με jp ob_figures)· η δομή χωρίς κορδέλα (το st_mark με jp
ob_mark)· οι κάθετες παύλες ανά τέσσερις γραμμές (bit 2 αντί για bit 3), στις
τετράδες και γραμμή γραμμή· το
st_built χωρίς το αποτύπωμα (ret στη θέση του st_site)· ο αρμός χωρίς κορδέλα
(το call c,ob_tapef του dh_conn τρία nop).

Κόστος: η πλήρης σχεδίαση με τον θόλο L-εργοτάξιο στην οθόνη, με και χωρίς
κορδέλα· ο χειρότερος γύρος όταν τελειώνει ο S (το DK_BUILT και το
αποτύπωμα του st_site).
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import test_reveal as R                                  # noqa: E402
import test_fit as TF                                    # noqa: E402
import test_rise as RI                                   # noqa: E402
import balance as B                                      # noqa: E402

FAIL = []
TK_PEN = 0x3C                                            # pen 6 στα δύο pixels
COLS, LINES = 80, 160
DOME_Q = ((8, 32), (12, 48), (16, 64))                   # QW, QH (build/sprite_consts.asm)
DS_BUILDING, DS_ACTIVE = 1, 2
I_DOME_S, I_DOME_L, I_SOLAR, I_MINE, I_LOCK = 0, 2, 4, 8, 9


def say(ok, msg):
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ: ") + msg)
    if not ok:
        FAIL.append(msg)


def s8(v):
    return v - 256 if v > 127 else v


def tape_on(x0, y0, w, h):
    """Η πρόζα: οι θέσεις (x, y) της οθόνης που ανάβει η κορδέλα ενός πλαισίου."""
    out = set()
    for y in (y0, y0 + 1, y0 + h - 2, y0 + h - 1):
        out |= {(x0 + dx, y) for dx in range(w) if dx % 4 in (0, 3)}
    for x in (x0, x0 + w - 1):
        out |= {(x, y0 + dy) for dy in range(h) if (dy + 4) & 8 == 0}
    return {(x, y) for x, y in out if 0 <= x < COLS and 0 <= y < LINES}


def frame(G, sym, node):
    """(x, y, w, h) του πλαισίου στην οθόνη: ob_frame για θόλο, ob_struct για δομή."""
    r = RI.rec(G, node)
    sx = 2 * (s8(r[0]) - 2 * s8(G.m.peek(sym["CAM_TX"])))
    sy = 8 * (s8(r[1]) - 2 * s8(G.m.peek(sym["CAM_TY"])))
    if node < 64:
        qw, qh = DOME_Q[r[2]]
        return sx - qw, sy - qh, 2 * qw, 2 * qh
    d = G.m.read_ram(R._lay("G_struct_dims") + 8 * r[2] + 2 * r[3], 2)
    return sx - d[0] // 2, sy - d[1] // 2, d[0], d[1]


def views(G, sym):
    """Με σταματημένη προσομοίωση: (η οθόνη, πλήρης σχεδίαση, και χωρίς τον
    κέρσορα — που ζωγραφίζεται τελευταίος, πάνω και στην κορδέλα — πλήρης
    σχεδίαση με κορδέλα και χωρίς, με το tk_draw ένα ret στο OV_R1)."""
    on = G.still()
    pic = G.play()
    G.full()
    ref = G.play()
    G.probe(["UI_HIDE", "OB_CLIP_FULL", "VIEW_DRAW"])
    with_ = G.play()
    b1, at = G.bank(1), sym["TK_DRAW"] - 0x4000
    keep = b1[at]
    b1[at] = 0xC9
    G.probe(["OB_CLIP_FULL", "VIEW_DRAW"])
    bare = G.play()
    b1[at] = keep
    G.full()
    G.go(on)
    return pic, ref, with_, bare


def tape(G, sym, node, what, also=()):
    """ΚΟΡΔΕΛΑ και ΑΛΗΘΕΙΑ: (None, θέσεις, όχι κίτρινες), ή τι δεν πάει. Το
    `also`: άλλα εργοτάξια στην οθόνη, που οι κορδέλες τους δεν είναι λάθος."""
    pic, ref, img, bare = views(G, sym)
    same = R.shape(pic, ref)
    want = tape_on(*frame(G, sym, node))
    others = set().union(*[tape_on(*frame(G, sym, n)) for n in also])
    diff = {(i % COLS, i // COLS) for i, (a, b) in enumerate(zip(img, bare)) if a != b}
    yellow = {p for p in want if img[p[1] * COLS + p[0]] == TK_PEN}
    wrong = {p for p in diff if img[p[1] * COLS + p[0]] != TK_PEN}
    if (not same[0] or diff - want - others or wrong or not want
            or len(yellow) * 5 < len(want) * 4):
        return (f"{what}: οθόνη/πλήρης σχεδίαση: {same[1]}· πλαίσιο {frame(G, sym, node)}: "
                f"{len(want)} θέσεις, {len(yellow)} κίτρινες, {len(diff - want - others)} αλλαγές "
                f"έξω από αυτές {sorted(diff - want - others)[:6]}, {len(wrong)} όχι κίτρινες")
    return None, len(want), len(want) - len(yellow)


def bands(G, sym, node):
    """ΚΟΜΜΑΤΙΑ: η κορδέλα του θόλου μόνη της, με το clip σε λωρίδες γραμμών —
    στοιχισμένες στις τέσσερις (οι τετράδες του tk_col) και όχι (γραμμή
    γραμμή, όπως όταν αδειάζει μια θέση του δακτυλίου): πάνω σε σχεδίαση χωρίς
    κορδέλα, αλλάζουν ακριβώς οι θέσεις της πρόζας μέσα στη λωρίδα."""
    x0, y0, w, h = frame(G, sym, node)
    want = tape_on(x0, y0, w, h)
    on = G.still()
    b1, at = G.bank(1), sym["TK_DRAW"] - 0x4000
    keep = b1[at]
    w16 = lambda a: [a & 255, a >> 8]
    out = None
    for top, n in ((17, 9), (3, 6), (61, 13), (16, 32), (100, 28)):
        ya, yb = max(y0 + top, 0), min(y0 + top + n, LINES)
        if ya >= yb:
            continue
        b1[at] = 0xC9
        G.probe(["UI_HIDE", "OB_CLIP_FULL", "VIEW_DRAW"])
        bare = G.play()
        b1[at] = keep
        code = ([0xF3, 0xCD] + w16(sym["UI_HIDE"]) + [0x01] + w16(0x7F00 + 0xC6) + [0xED, 0x49]
                 + [0x3E, node, 0xCD] + w16(sym["OB_GETDOME"])
                 + [0x21] + w16(yb << 8 | ya) + [0x22] + w16(sym["CLIP_Y0"])
                 + [0xCD] + w16(sym["OB_TAPEF"])
                 + [0x01] + w16(0x7F00 + 0xC0) + [0xED, 0x49]
                 + [0xCD] + w16(sym["OB_CLIP_FULL"]))
        for _ in range(40000):
            if G.top <= G.m.pc < G.top + 13:
                break
            G.m.run_us(50)
        G.m.run_code(R.PROBE, bytes(code + [0x18, 0xFE]), frames=10)
        G.m.set_pc(G.top)
        G.last, G.inw = None, False
        pic = G.play()
        bad = [(x, y) for y in range(LINES) for x in range(COLS)
               if pic[y * COLS + x] != (TK_PEN if ya <= y < yb and (x, y) in want
                                       else bare[y * COLS + x])]
        if bad:
            out = (f"ΚΟΜΜΑΤΙΑ: ο {node}, οι γραμμές {ya}-{yb - 1} του πλαισίου {y0}+{h}: "
                   f"{len(bad)} bytes όχι όπως λέει η πρόζα {bad[:6]}")
            break
    b1[at] = keep
    G.full()
    G.go(on)
    return out


def clean(G, sym, what, also=()):
    """ΤΕΛΟΣ: η οθόνη η πλήρης σχεδίαση, και καμία κορδέλα πουθενά — εκτός από
    των άλλων εργοταξίων (`also`)."""
    pic, ref, img, bare = views(G, sym)
    same = R.shape(pic, ref)
    others = set().union(*[tape_on(*frame(G, sym, n)) for n in also])
    diff = {(i % COLS, i // COLS) for i, (a, b) in enumerate(zip(img, bare)) if a != b} - others
    if not same[0] or diff:
        return (f"{what}: οθόνη/πλήρης σχεδίαση: {same[1]}· {len(diff)} bytes της κορδέλας "
                f"μένουν {sorted(diff)[:6]}")
    return None


def parity(G, sym, item, at):
    """Ο κέρσορας όπως τον κάνει το παιχνίδι όταν διαλέγεται το κτίσμα (bds_lp,
    src/build.asm): μισό tile πιο πέρα αν το κέντρο δεν έχει την ισοτιμία του
    πλάτους, και ο κέρσορας κινείται ανά tile. Το B.build γράφει το cur_hx
    μετά την επιλογή, και ένα ηλιακό 3x3 με κέντρο ζυγό έπεφτε μισό tile έξω
    από τα tiles του — κάτι που στο παιχνίδι δεν γίνεται."""
    rec = G.m.read_ram(sym["BLD_ITEMS"] + 8 * item, 4)
    return tuple(a + ((a ^ n) & 1) for a, n in zip(at, rec[2:4]))


def place(G, sym, g, item, at, room=None):
    if not B.build(G.m, sym, item, g + 6, at=at, room=room, fit=False):
        return None
    node = G.m.peek(sym["BD_NODE"])
    G.settle()
    return node


def apply(G, sym, patch):
    for where, at, v in patch:
        if where is None:
            G.m.poke(at, v)
        else:
            G.bank(where)[at - 0x4000] = v


def finish(G, node, frames=30000):
    """Ως να γίνει DS_ACTIVE, και η λίστα να αδειάσει."""
    for _ in range(frames // 10):
        if RI.rec(G, node)[4] == DS_ACTIVE:
            break
        G.run(200_000)
    G.settle()
    return RI.rec(G, node)[4] == DS_ACTIVE


# --------------------------------------------------------------------------
# ΘΟΛΟΙ — S ως το τέλος, L για το σχήμα και το κόστος
# --------------------------------------------------------------------------
def domes(sym, g, patch=(), quiet=False, cost=False):
    say_ = (lambda s: None) if quiet else (lambda s: print("    " + s))
    out = {}
    G = R.Game(sym, g)
    apply(G, sym, patch)
    F = TF.Fit(G, sym, g)
    F.set_stocks(0, 0)
    spots = B.clear_spots(8, 2, dome=True)
    tx, ty = spots[1]
    G.camera(tx - 6, ty - 1)
    big = place(G, sym, g, I_DOME_L, (2 * tx + 8, 2 * ty + 8), R.R_FACTORY)
    if big is None:
        return f"ΘΟΛΟΣ L: δεν μπήκε στο {spots[1]}"
    got = tape(G, sym, big, f"ΘΟΛΟΣ L {big}, εργοτάξιο χωρίς φορτία")
    if isinstance(got, str):
        return got
    say_(f"ΚΟΡΔΕΛΑ: θόλος L {big}, {got[1]} θέσεις, όλες κίτρινες εκτός από {got[2]}")
    why = bands(G, sym, big)
    if why:
        return why
    say_("ΚΟΜΜΑΤΙΑ: ο L με το clip σε λωρίδες των 9, 6, 13, 32 και 28 γραμμών, "
         "στοιχισμένες και όχι, ακριβώς οι θέσεις της πρόζας")
    if cost:
        out["L"] = full_us(G, sym)
    tx, ty = spots[0]
    G.camera(tx - 8, ty - 2)
    node = place(G, sym, g, I_DOME_S, (2 * tx + 4, 2 * ty + 4), R.R_FACTORY)
    if node is None:
        return f"ΘΟΛΟΣ S: δεν μπήκε στο {spots[0]}"
    got = tape(G, sym, node, f"ΘΟΛΟΣ S {node}, εργοτάξιο χωρίς φορτία", (big,))
    if isinstance(got, str):
        return got
    say_(f"ΚΟΡΔΕΛΑ: θόλος S {node}, {got[1]} θέσεις, όλες κίτρινες εκτός από {got[2]}")
    F.set_stocks(999, 999)
    n0, loads = RI.left(RI.rec(G, node), node), 0
    for _ in range(4000):
        G.m.run_frames(5)
        k = RI.left(RI.rec(G, node), node)
        if k != n0:
            loads += n0 - k
            n0 = k
            got = tape(G, sym, node, f"ΘΟΛΟΣ S {node}, μετά από {loads} φορτία", (big,))
            if isinstance(got, str):
                return got
            if k == 0:
                break
    G.worst()
    if not finish(G, node):
        return f"ΘΟΛΟΣ S {node}: δεν τελείωσε ({RI.rec(G, node)[4:8]})"
    out["built"] = G.worst()
    why = clean(G, sym, f"ΤΕΛΟΣ: θόλος S {node}", (big,))
    if why:
        return why
    say_(f"ΑΛΗΘΕΙΑ: ο S {node} με κάθε ένα από τα {loads} φορτία· ΤΕΛΟΣ: τελείωσε, χωρίς "
         f"κορδέλα, ο χειρότερος γύρος {out['built']:.0f} ms")
    return out if cost else None


def full_us(G, sym):
    """Η πλήρης σχεδίαση (VIEW_DRAW) σε µs, με και χωρίς κορδέλα."""
    import test_bar as TB
    res = []
    b1, at = G.bank(1), sym["TK_DRAW"] - 0x4000
    keep = b1[at]
    on = G.still()
    for v in (keep, 0xC9):
        b1[at] = v
        G.probe(["OB_CLIP_FULL"])
        res.append(TB.call_us(G.m, sym, sym["VIEW_DRAW"], reps=1))
    b1[at] = keep
    G.full()
    G.go(on)
    return res


# --------------------------------------------------------------------------
# ΔΟΜΕΣ — ηλιακό ως το τέλος και ο μετεωρίτης, ορυχείο, airlock
# --------------------------------------------------------------------------
def structs(sym, g, patch=(), quiet=False):
    say_ = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G = R.Game(sym, g)
    apply(G, sym, patch)
    F = TF.Fit(G, sym, g)
    F.set_stocks(0, 0)
    nodes = {}
    for item, name, near in ((I_MINE, "ορυχείο", (10, 24)), (I_LOCK, "airlock", (-6, 20)),
                             (I_SOLAR, "ηλιακό", (0, 24))):
        at = parity(G, sym, item, B.live_spot(G.m, sym, item, near))
        G.camera((at[0] >> 1) - 10, (at[1] >> 1) - 5)
        node = place(G, sym, g, item, at)
        if node is None:
            return f"{name}: δεν μπήκε στο {at}"
        got = tape(G, sym, node, f"{name} {node}, εργοτάξιο χωρίς φορτία", tuple(nodes.values()))
        if isinstance(got, str):
            return got
        nodes[name] = node
        say_(f"ΚΟΡΔΕΛΑ: {name} {node}, πλαίσιο {frame(G, sym, node)[2:]}, {got[1]} θέσεις, "
             f"όλες κίτρινες εκτός από {got[2]}")
    node = nodes["ηλιακό"]
    F.set_stocks(999, 999)
    if not finish(G, node):
        return f"ηλιακό {node}: δεν τελείωσε ({RI.rec(G, node)[4:8]})"
    rest = (nodes["ορυχείο"], nodes["airlock"])
    why = clean(G, sym, f"ΤΕΛΟΣ: ηλιακό {node}", rest)
    if why:
        return why
    on = G.still()
    r = RI.meteor(G, sym, node)
    G.go(on)
    if r[4] != DS_BUILDING:
        return f"ΜΕΤΕΩΡΙΤΗΣ: το ηλιακό {node} μετά {r[4:8]} — θέλει εργοτάξιο"
    G.settle()
    got = tape(G, sym, node, f"ΜΕΤΕΩΡΙΤΗΣ: ηλιακό {node} πάλι εργοτάξιο", rest)
    if isinstance(got, str):
        return got
    say_(f"ΤΕΛΟΣ: το ηλιακό {node} τελείωσε χωρίς κορδέλα· ΜΕΤΕΩΡΙΤΗΣ: πάλι εργοτάξιο, "
         f"με κορδέλα ({got[1]} θέσεις)")
    return None


# --------------------------------------------------------------------------
# ΑΡΜΟΣ — δύο θόλοι S εργοτάξια, ο διάδρομος του δεύτερου στον πρώτο
# --------------------------------------------------------------------------
def joint(sym, g, patch=(), quiet=False):
    say_ = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G = R.Game(sym, g)
    apply(G, sym, patch)
    F = TF.Fit(G, sym, g)
    F.set_stocks(0, 0)
    spots = B.clear_spots(4, 40, dome=True)
    pair = next(((a, b) for a in spots for b in spots
                 if b[1] == a[1] and 6 <= b[0] - a[0] <= 9), None)
    if pair is None:
        return f"ΑΡΜΟΣ: δεν βρέθηκαν δύο θέσεις στην ίδια σειρά ({len(spots)})"
    (ax, ay), (bx, by) = pair
    G.camera(ax - 2, ay - 3)
    first = place(G, sym, g, I_DOME_S, (2 * ax + 4, 2 * ay + 4), R.R_FACTORY)
    if first is None:
        return f"ΑΡΜΟΣ: ο πρώτος δεν μπήκε στο {(ax, ay)}"
    second = place(G, sym, g, I_DOME_S, (2 * bx + 4, 2 * by + 4), R.R_FACTORY)
    if second is None:
        return f"ΑΡΜΟΣ: ο δεύτερος δεν μπήκε στο {(bx, by)}"
    got = tape(G, sym, first, f"ΑΡΜΟΣ: ο {first} μετά τον διάδρομο του {second}", (second,))
    if isinstance(got, str):
        return got
    say_(f"ΑΡΜΟΣ: ο {first} με τον διάδρομο του {second}: η οθόνη η πλήρης σχεδίαση, η "
         f"κορδέλα στη θέση της ({got[1]} θέσεις, και οι {len(tape_on(*frame(G, sym, second)))} "
         f"του {second})")
    return None


def main():
    sym, g = TG.build()
    out = domes(sym, g, cost=True)
    say(not isinstance(out, str), out if isinstance(out, str) else
        "ΘΟΛΟΙ: η κορδέλα του L και του S, ο S με κάθε φορτίο και όταν τελειώσει")
    for fn, what in ((structs, "ΔΟΜΕΣ: ορυχείο, airlock, ηλιακό ως το τέλος, και ο μετεωρίτης"),
                     (joint, "ΑΡΜΟΣ: ο διάδρομος ενός δεύτερου θόλου στο εργοτάξιο")):
        why = fn(sym, g)
        say(why is None, why or what)

    # --- αρνητικά ---
    G = R.Game(sym, g)
    m0 = lambda a, n: bytes(G.m.read_ram(a, n))
    find = lambda blob, pat: next((k for k in range(len(blob)) if list(blob[k:k + len(pat)]) == pat), None)
    tf = sym["OB_TAPEF"]
    fi = find(m0(sym["OB_FITTINGS"], 80), [0xC3, tf & 255, tf >> 8])            # jp ob_tapef
    om = sym["OS_MARK"]
    sm = find(m0(sym["ST_MARK"], 40), [0xC3, om & 255, om >> 8])                # jp os_mark
    cn = find(m0(sym["DH_CONN"], 40), [0xDC, tf & 255, tf >> 8])                # call c,ob_tapef
    b1 = bytes(G.bank(1)[sym["TK_COL"] - 0x4000 + k] for k in range(sym["TK_ROW"] - sym["TK_COL"]))
    bt = find(b1, [0xCB, 0x59])                                                 # bit 3,c (τετράδες)
    bo = find(b1[bt + 2:], [0xCB, 0x59]) if bt is not None else None            # και γραμμή γραμμή
    bo = None if bo is None else bt + 2 + bo
    st = sym["ST_SITE"]
    if None in (fi, sm, cn, bt, bo):
        say(False, f"τα σημεία των αρνητικών δεν βρέθηκαν: {fi, sm, cn, bt, bo}")
        return 1
    of = sym["OB_FIGURES"]
    mk = sym["OB_MARK"]
    for label, fn, patch in (
            ("ο θόλος χωρίς κορδέλα", domes, [(None, sym["OB_FITTINGS"] + fi + 1, of & 255),
                                              (None, sym["OB_FITTINGS"] + fi + 2, of >> 8)]),
            ("η δομή χωρίς κορδέλα", structs, [(None, sym["ST_MARK"] + sm + 1, mk & 255),
                                               (None, sym["ST_MARK"] + sm + 2, mk >> 8)]),
            ("οι κάθετες παύλες ανά τέσσερις γραμμές", structs,
             [(1, sym["TK_COL"] + bt + 1, 0x51)]),                               # bit 2,c
            ("οι κάθετες παύλες γραμμή γραμμή ανά τέσσερις", domes,
             [(1, sym["TK_COL"] + bo + 1, 0x51)]),
            ("το st_built χωρίς το αποτύπωμα", domes, [(6, st, 0xC9)]),
            ("ο αρμός χωρίς κορδέλα", joint, [(None, sym["DH_CONN"] + cn + k, 0) for k in range(3)])):
        why = fn(sym, g, patch, quiet=True)
        say(why is not None, f"ΑΡΝΗΤΙΚΟ «{label}»: " + (why[:120] if isinstance(why, str) else "ΠΕΡΝΑ"))

    if isinstance(out, dict):
        on, off = out["L"]
        print(f"\nκόστος: πλήρης σχεδίαση με τον θόλο L-εργοτάξιο {on} µs, χωρίς κορδέλα {off} "
              f"(+{on - off})· όταν τελειώνει ο S, ο χειρότερος γύρος {out['built']:.0f} ms")
    print(f"\n{len(FAIL)} ΑΠΟΤΥΧΙΕΣ" if FAIL else "\nΟΛΑ ΚΑΛΑ")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
