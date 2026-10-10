#!/usr/bin/env python3
"""Η κατάσταση μιας μηχανής φαίνεται (βήμα 100, DESIGN §6.10).

Η πρόζα — οι αποφάσεις του παίκτη:

  ΣΗΜΑ       μια μηχανή που δεν δουλεύει παίρνει ένα σήμα πάνω αριστερά στο
             sprite της, 2 bytes x 6 γραμμές, όπως τα εικονίδια του Planetbase.
             Το ζωγραφίζει το tools/pack.py, όχι τα assets.
  ΔΥΟ        ΧΑΛΑΣΜΕΝΗ (υγεία 0): κόκκινο με λευκό θαυμαστικό· θέλει μηχανικό με
             ανταλλακτικό. ΠΕΡΙΜΕΝΕΙ να στηθεί (υγεία 1-127, βήμα 99): κίτρινες
             και μαύρες λωρίδες. Μια μηχανή που δουλεύει (bit 7) κανένα.
  ΦΥΤΑ      ένα μαραμένο φυτό (υγεία 0) παίρνει το σήμα της χαλασμένης.
  ΑΛΛΑΖΕΙ    η υποδοχή ξαναζωγραφίζεται (DK_MACH) όταν μπαίνει στο FIT, όταν
             στήνεται, όταν χαλάει (βλάβη, μετεωρίτης) και όταν επισκευάζεται·
             η οθόνη είναι κάθε φορά ΙΔΙΑ με πλήρη σχεδίαση.

Στο παιχνίδι που τρέχει, στην αποικία δοκιμών, με τα πλήκτρα του παίκτη:

  FIT        ένα μεσαίο εργοστάσιο, τέσσερις μηχανές: τέσσερα σήματα «περιμένει».
  ΣΤΗΣΙΜΟ    οι άποικοι κουβαλούν, ο μηχανικός στήνει: τα σήματα φεύγουν ένα
             ένα, και μένει το sprite της μηχανής.
  ΒΛΑΒΗ      ένα μεσαίο εργοστάσιο με δύο μηχανές στημένες· η πρώτη χαλάει
             (ec_break_d), χωρίς ανταλλακτικά: το σήμα της χαλασμένης. Με
             ανταλλακτικά ο μηχανικός την επισκευάζει και το σήμα φεύγει.
  ΦΥΤΟ      ένα μεσαίο θερμοκήπιο με τέσσερα φυτά, ένα μαραίνεται: το σήμα, και
             το επόμενο φυτό ζωγραφίζεται σωστά (τα φυτά ζουν στην 7, τα σήματα
             στην 5).

Αρνητικά, με τον κώδικα πειραγμένο στη μνήμη: ποτέ σήμα· σήμα και σε όσες
δουλεύουν· τα δύο σήματα ανάποδα· η βλάβη, η επισκευή, το στήσιμο χωρίς
DK_MACH· η επόμενη υποδοχή χωρίς την τράπεζά της.
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import test_reveal as R                                  # noqa: E402
import test_fit as TF                                    # noqa: E402
import test_outside as TO                                # noqa: E402
import balance as B                                      # noqa: E402
import scene as S                                        # noqa: E402
import pack as P                                         # noqa: E402
import econ as EC                                        # noqa: E402

FAIL = []
BROKEN, WAIT = 0, 1
HP = 200
S_SPARE = EC.S_SPARE


def check(ok, msg):
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ ") + msg)
    if not ok:
        FAIL.append(msg)


def consts():
    c = open(os.path.join(ROOT, "src", "const.asm"), encoding="utf-8").read()
    return {n: int(re.search(rf"^{n}\s+equ\s+#([0-9A-Fa-f]+)", c, re.M).group(1), 16)
            for n in ("GA_PORT", "PAGE_B1", "PAGE_B6")}


ASSETS = S.Assets()
MARK = [S.mark_rows(k) for k in (BROKEN, WAIT)]


def corner(G, at):
    """Τα 2 x 6 bytes της οθόνης πάνω αριστερά στην υποδοχή."""
    x, y = at
    scr = G.bank(3)
    return [bytes(scr[G.addr(x + i, y + j)] for i in range(P.MARK_W))
            for j in range(P.MARK_H)]


def sprite_corner(name):
    return [bytes(r[:P.MARK_W]) for r in list(ASSETS.rows(name))[:P.MARK_H]]


def want(rec, s, green):
    """Ο,τι πρέπει να έχει η γωνία της υποδοχής s, κατά την πρόζα."""
    m, hp = rec[8 + s], rec[16 + s]
    if not hp & 0x80:
        return MARK[BROKEN if hp == 0 else WAIT]
    return sprite_corner(f"plant_{S.PLANTS[m]}" if green else f"mach_{S.MACH[m]}")


def slots(G, rec, at, green=False):
    """Οι υποδοχές με μηχανή που δεν έχουν ό,τι λέει η πρόζα: [(υποδοχή, υγεία)].
    Με τον κέρσορα κρυμμένο: το πλαίσιό του κάθεται πάνω στον θόλο του LOOK."""
    G.probe(["UI_HIDE"])
    bad = [(s, rec[16 + s]) for s, a in enumerate(at)
           if rec[8 + s] != 255 and corner(G, a) != want(rec, s, green)]
    G.probe(["UI_SHOW"])
    return bad


def truth(G):
    pic, ref = G.truth()
    return R.shape(pic, ref)


def break_slot(G, sym, dome, slot):
    """Το ec_break_d (src/econ.asm) στον θόλο και στην υποδοχή, από την κορυφή
    του βρόχου, με την 6 μέσα όπως στον τροχό· ο βρόχος συνεχίζει μετά."""
    k, m = consts(), G.m
    for _ in range(40000):
        if G.top <= m.pc < G.top + 13:
            break
        m.run_us(50)
    w = lambda a: [a & 255, a >> 8]
    code = ([0xF3, 0x3E, dome, 0x32] + w(sym["EB_D"]) + [0x3E, slot, 0x32] + w(sym["EB_S"])
            + [0x01] + w(k["GA_PORT"] + k["PAGE_B6"]) + [0xED, 0x49]
            + [0xCD] + w(sym["EC_BREAK_D"])
            + [0x01] + w(k["GA_PORT"] + k["PAGE_B1"]) + [0xED, 0x49])
    m.run_code(R.PROBE, bytes(code + [0x18, 0xFE]), frames=50)
    m.set_pc(G.top)
    G.last, G.inw = None, False


def spares(G, g, n):
    G.m.poke(g + 2 * S_SPARE, n & 255)
    G.m.poke(g + 2 * S_SPARE + 1, n >> 8)


def positions(F, n):
    """Η πάνω αριστερή γωνία κάθε υποδοχής στην οθόνη, από το πλαίσιο του
    fit_show (gh_bx = x - 1, gh_by = y - 2)."""
    sx = lambda v: v - 65536 if v > 32767 else v
    out = []
    for s in range(n):
        F.slot(s)
        out.append((sx(F.peek("GH_BX") | (F.peek("GH_BX", 1) << 8)) + 1,
                    sx(F.peek("GH_BY") | (F.peek("GH_BY", 1) << 8)) + 2))
    return out


def dome_here(sym, g, room, patch=()):
    """Ενας μεσαίος θόλος, τελειωμένος, στην οθόνη: (G, F, κόμβος, at)."""
    G = R.Game(sym, g)
    for at, v in patch:
        G.m.poke(at, v)
    F = TF.Fit(G, sym, g)
    F.set_stocks(TF.STOCK, TF.STOCK)
    tx, ty = B.clear_spots(8, 1, dome=True)[0]
    G.camera(tx - 6, ty - 1)
    at = (2 * tx + 8, 2 * ty + 8)
    B.build(G.m, sym, TF.I_DOME_M, g + 6, at=at, room=room, fit=False)
    node = G.m.peek(sym["BD_NODE"])
    ok = R.finish(G, node)
    G.settle()
    return G, F, node, at, ok


# --------------------------------------------------------------------------
# ΠΙΝΑΚΕΣ
# --------------------------------------------------------------------------
def tables(sym, g):
    G = R.Game(sym, g)
    b5 = G.bank(5)
    L = TO.layout()
    got = bytes(b5[L["G_marks"] - 0x4000 + k] for k in range(2 * P.MARK_W * P.MARK_H))
    pens = {"R": 8, "W": 5, "Y": 6, "K": 0}
    prose = (["RWWR", "RWWR", "RWWR", "RRRR", "RWWR", "RRRR"],
             ["YYKK", "YKKY", "KKYY", "KYYK", "YYKK", "YKKY"])
    data = bytes(P._m0_byte(pens[r[2 * k]], pens[r[2 * k + 1]])
                 for m in prose for r in m for k in range(2))
    if got != data or P.marks() != data:
        return (f"ΠΙΝΑΚΕΣ: τα σήματα στην τράπεζα 5 {got.hex()}, του pack.py "
                f"{P.marks().hex()} — η πρόζα λέει {data.hex()}")
    return None


# --------------------------------------------------------------------------
# FIT και ΣΤΗΣΙΜΟ — τέσσερις μηχανές σε ένα μεσαίο εργοστάσιο
# --------------------------------------------------------------------------
def fit_install(sym, g, patch=(), quiet=False, frames=60_000_000):
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G, F, node, at, ok = dome_here(sym, g, TF.RM_FACTORY, patch)
    if not ok:
        return f"FIT: το εργοστάσιο {node} δεν τελείωσε"
    if not F.enter(at):
        return f"FIT: ο εξοπλισμός δεν άνοιξε (κατάσταση {F.peek('UI_STATE')})"
    for s, i in enumerate([1, 2, 1, 4]):            # μέταλλο, βιοπλαστικό, μέταλλο, ρομπότ
        F.put(s, i)
    pos = positions(F, 4)
    F.look()
    G.settle()
    rec = F.rec(node)
    bad, same = slots(G, rec, pos), truth(G)
    if any(not 0 < h < 128 for h in rec[16:20]) or bad or not same[0]:
        return (f"FIT: υγείες {rec[16:20]}, γωνίες που δεν λένε ό,τι η πρόζα {bad}, "
                f"οθόνη/πλήρης σχεδίαση: {same[1]} — η πρόζα λέει τέσσερα «περιμένει»")
    say(f"FIT: τέσσερις μηχανές στο εργοστάσιο {node}, υγείες {rec[16:20]}, τέσσερα σήματα "
        f"«περιμένει»· η οθόνη ίδια με πλήρη σχεδίαση")
    G.run(frames, until=lambda: all(h == HP for h in F.rec(node)[16:20]))
    G.settle()
    rec = F.rec(node)
    bad, same = slots(G, rec, pos), truth(G)
    if rec[16:20] != [HP] * 4 or bad or not same[0]:
        return (f"ΣΤΗΣΙΜΟ: υγείες {rec[16:20]}, γωνίες {bad}, οθόνη/πλήρης σχεδίαση: "
                f"{same[1]} — η πρόζα λέει στήθηκαν και τα σήματα έφυγαν")
    say(f"ΣΤΗΣΙΜΟ: οι τέσσερις στήθηκαν σε {G.t / 1e6:.1f} s παιχνιδιού· τα σήματα έφυγαν, "
        f"έμειναν τα sprites· η οθόνη ίδια με πλήρη σχεδίαση")
    return None


# --------------------------------------------------------------------------
# ΒΛΑΒΗ και ΕΠΙΣΚΕΥΗ — δύο μηχανές σε ένα μεσαίο εργοστάσιο
# --------------------------------------------------------------------------
def break_repair(sym, g, patch=(), quiet=False, frames=60_000_000):
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G, F, node, at, ok = dome_here(sym, g, TF.RM_FACTORY, patch)
    if not ok:
        return f"ΒΛΑΒΗ: το εργοστάσιο {node} δεν τελείωσε"
    if not F.enter(at):
        return f"ΒΛΑΒΗ: ο εξοπλισμός δεν άνοιξε (κατάσταση {F.peek('UI_STATE')})"
    for s, i in enumerate([1, 1]):
        F.put(s, i)
    pos = positions(F, 4)
    F.look()
    G.run(60_000_000, until=lambda: F.rec(node)[16:18] == [HP, HP])
    G.settle()
    if F.rec(node)[16:18] != [HP, HP]:
        return f"ΒΛΑΒΗ: οι δύο μηχανές δεν στήθηκαν: {F.rec(node)[16:20]}"
    spares(G, g, 0)
    break_slot(G, sym, node, 0)
    G.run(400_000)
    G.settle()
    rec = F.rec(node)
    bad, same = slots(G, rec, pos), truth(G)
    if rec[16] != 0 or bad or not same[0]:
        return (f"ΒΛΑΒΗ: υγείες {rec[16:20]}, γωνίες {bad}, οθόνη/πλήρης σχεδίαση: "
                f"{same[1]} — η πρόζα λέει το σήμα της χαλασμένης στην υποδοχή 0")
    say("ΒΛΑΒΗ: το ec_break_d μηδένισε την υποδοχή 0 και το σήμα της χαλασμένης φάνηκε· "
        "η υποδοχή 1 έμεινε όπως ήταν· η οθόνη ίδια με πλήρη σχεδίαση")
    spares(G, g, 5)
    G.run(frames, until=lambda: F.rec(node)[16] == HP)
    G.settle()
    rec = F.rec(node)
    bad, same = slots(G, rec, pos), truth(G)
    if rec[16] != HP or bad or not same[0]:
        return (f"ΕΠΙΣΚΕΥΗ: υγείες {rec[16:20]}, γωνίες {bad}, οθόνη/πλήρης σχεδίαση: "
                f"{same[1]} — η πρόζα λέει ο μηχανικός την επισκεύασε και το σήμα έφυγε")
    say("ΕΠΙΣΚΕΥΗ: με ανταλλακτικά ο μηχανικός ήρθε, η υγεία 200, το σήμα έφυγε")
    return None


# --------------------------------------------------------------------------
# ΦΥΤΟ — ένα μαραμένο φυτό σε μεσαίο θερμοκήπιο
# --------------------------------------------------------------------------
def plant(sym, g, patch=(), quiet=False):
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G, F, node, at, ok = dome_here(sym, g, TF.RM_GREEN, patch)
    if not ok:
        return f"ΦΥΤΟ: το θερμοκήπιο {node} δεν τελείωσε"
    if not F.enter(at):
        return f"ΦΥΤΟ: ο εξοπλισμός δεν άνοιξε (κατάσταση {F.peek('UI_STATE')})"
    for s, i in enumerate([2, 2, 3, 5]):            # άμυλο, άμυλο, λαχανικά, δέντρο
        F.put(s, i)
    pos = positions(F, 4)
    F.look()
    G.settle()
    break_slot(G, sym, node, 1)
    G.run(400_000)
    G.settle()
    rec = F.rec(node)
    bad, same = slots(G, rec, pos, green=True), truth(G)
    if rec[16:20] != [HP, 0, HP, HP] or bad or not same[0]:
        return (f"ΦΥΤΟ: υγείες {rec[16:20]}, γωνίες {bad}, οθόνη/πλήρης σχεδίαση: "
                f"{same[1]} — η πρόζα λέει το σήμα της χαλασμένης στο φυτό 1, τα άλλα "
                f"όπως είναι")
    say("ΦΥΤΟ: το φυτό 1 μαράθηκε και πήρε το σήμα της χαλασμένης· τα 0, 2, 3 όπως είναι, "
        "και η πλήρης σχεδίαση το ίδιο")
    return None


# --------------------------------------------------------------------------
# ΑΡΝΗΤΙΚΑ
# --------------------------------------------------------------------------
def find(G, sym, name, n, pat):
    data = G.m.read_ram(sym[name], n)
    hits = [sym[name] + k for k in range(n - len(pat) + 1) if list(data[k:k + len(pat)]) == pat]
    return hits[0] if len(hits) == 1 else None


def negatives(sym, g):
    G = R.Game(sym, g)
    w = lambda a: [a & 255, a >> 8]
    mp, om = sym["JB_MPUSH"], sym["OM_PREP"]
    out = []

    def at(label, name, n, pat, edits, test):
        a = find(G, sym, name, n, pat)
        out.append((label, None if a is None else [(a + k, v) for k, v in edits], test))

    at("ποτέ σήμα", "OB_MACH_ONE", 80, [0x87, 0xD8], [(1, 0xC9)], "fit")
    at("σήμα και σε όσες δουλεύουν", "OB_MACH_ONE", 80, [0x87, 0xD8], [(1, 0)], "fit")
    at("τα δύο σήματα ανάποδα", "OB_MACH_ONE", 80, [0x28, 0x02, 0x2E], [(0, 0x20)], "break")
    at("η βλάβη χωρίς DK_MACH", "EC_BREAK_D", 80, [0xC3] + w(mp), [(0, 0xC9), (1, 0), (2, 0)],
       "break")
    at("η επισκευή χωρίς DK_MACH", "JA_REPAIR", 60, [0xCD] + w(mp), [(0, 0), (1, 0), (2, 0)],
       "break")
    at("το στήσιμο χωρίς DK_MACH", "JABI_GO", 40, [0xCD] + w(mp), [(0, 0), (1, 0), (2, 0)],
       "fit")
    at("η επόμενη υποδοχή χωρίς την τράπεζά της", "OB_MACH_ONE", 100, [0xC3] + w(om),
       [(0, 0xC9), (1, 0), (2, 0)], "plant")
    return out


def run_negative(sym, g, patch, test):
    return {"fit": fit_install, "break": break_repair, "plant": plant}[test](
        sym, g, patch, quiet=True)


def main():
    sym, g = TG.build()
    err = tables(sym, g)
    check(err is None, err or "ΠΙΝΑΚΕΣ: τα δύο σήματα στην τράπεζα 5 είναι της πρόζας")
    for fn, what in ((fit_install, "FIT και ΣΤΗΣΙΜΟ: τα σήματα «περιμένει» μπαίνουν και φεύγουν"),
                     (break_repair, "ΒΛΑΒΗ και ΕΠΙΣΚΕΥΗ: το σήμα της χαλασμένης μπαίνει και φεύγει"),
                     (plant, "ΦΥΤΟ: ένα μαραμένο φυτό, και τα άλλα σωστά")):
        err = fn(sym, g)
        check(err is None, err or what)
    for label, patch, test in negatives(sym, g):
        if patch is None:
            check(False, f"ΑΡΝΗΤΙΚΟ «{label}»: το μοτίβο δεν βρέθηκε μία φορά")
            continue
        err = run_negative(sym, g, patch, test)
        check(err is not None, f"ΑΡΝΗΤΙΚΟ «{label}»: {err or 'ΔΕΝ ΠΙΑΣΤΗΚΕ'}")
    if FAIL:
        print(f"\n{len(FAIL)} ΑΠΟΤΥΧΙΕΣ")
        sys.exit(1)
    print("\nΟΛΑ ΚΑΛΑ")


if __name__ == "__main__":
    main()
