#!/usr/bin/env python3
"""Ο διάδρομος και πάνω από βράχο (βήμα 161, DESIGN §9.3).

Η επιλογή του χρήστη μετά το βήμα 160, όπου μια αποικία είχε γεμίσει την
κοιλάδα της: ένας διάδρομος πατά έδαφος, σκόνη, ΒΡΑΧΟ ή θεμέλιο χωρίς κατοχή
(cr_cb_chk, src/route.asm)· ο θόλος, η δομή και το μονοπάτι μιας δομής μένουν
σε ό,τι λέει το bd_ok — έδαφος, σκόνη, θεμέλιο. Ο βράχος μένει βράχος: η
σφραγίδα βάζει μόνο το bit 4 της κατοχής, και η κατεδάφιση το παίρνει πίσω.

Δύο σκηνές στην αποικία δοκιμών: ένας θόλος S δυτικά του θόλου 0, με αξονικό
διάδρομο πέντε tiles (και άλλα πέντε του μισού πλάτους), και ένας
βορειοδυτικά, με διαγώνιο επτά. Τα tiles των διαδρόμων έξω από τα δύο
αποτυπώματα, και οι γείτονές τους, γίνονται βράχος — όσα ήταν έδαφος ή σκόνη.

  ΧΤΙΣΜΑ     Το reach.py τον δέχεται με αυτόν τον έναν διάδρομο, το ui_validate
             λέει το ίδιο (ui_bad 0), και το FIRE τον χτίζει: εργοτάξιο, η
             εγγραφή του διαδρόμου, και ο κόσμος αλλάζει ΜΟΝΟ στο bit 4, όπως
             λέει το μοντέλο του test_demolish (αποτυπώματα, tiles διαδρόμων
             και μισού πλάτους) — ο βράχος κάτω από τον διάδρομο #12.
  ΕΙΚΟΝΑ     Η ίδια σκηνή χωρίς τον βράχο, σε δεύτερο παιχνίδι, με την
             προσομοίωση σταματημένη και στα δύο: μετά το FIRE οι δύο οθόνες
             διαφέρουν ΜΟΝΟ όπου διέφεραν και πριν, εκεί που φαίνεται το
             έδαφος· και πάνω από κάθε tile βράχου του διαδρόμου η οθόνη
             άλλαξε. Ο διάδρομος ζωγραφίζεται ίδιος, και φαίνεται. Και η οθόνη
             = η πλήρης σχεδίαση.
  ΤΕΛΟΣ      Ο θόλος τελειώνει με το ρολόι να τρέχει: η ακμή του διαδρόμου στον
             γράφο και από τις δύο μεριές, ο κόσμος ακόμη μόνο με το bit 4
             αλλαγμένο, η οθόνη = η πλήρης σχεδίαση.
  ΚΑΤΕΔΑΦΙΣΗ M, D, FIRE στον θόλο: ό,τι ελέγχει το test_demolish (common), και ο
             κόσμος byte προς byte όπως πριν από το FIRE — βράχος χωρίς
             κατοχή.
  ΒΟΥΝΟ      Η ίδια σκηνή με βουνό αντί για βράχο: κόκκινο με τον λόγο του
             reach.py, και το FIRE δεν χτίζει τίποτα.

Το μονοπάτι μιας δομής πάνω σε βράχο το ελέγχει το test_reach (ο πίνακας: PATH
BLOCKED), και τον κανόνα σε τυχαίους κόσμους τα test_corridor και test_reach.

Αρνητικά, με τον κώδικα πειραγμένο: ο κανόνας ως το βήμα 160 (cp W_ROCK + 1 ->
cp W_ROCK: ο θόλος κόκκινος), η σφραγίδα που κάνει τον βράχο θεμέλιο (set
4,(hl) -> ld (hl),#17 στο crx_cb του cr_stampx), και η κατεδάφιση που σβήνει και την κλάση (AND #EF ->
AND #E8: ο βράχος γίνεται έδαφος).
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import test_reveal as R                                  # noqa: E402
import test_demolish as TD                               # noqa: E402
import balance as B                                      # noqa: E402
import reach                                             # noqa: E402
import econ as EC                                        # noqa: E402
from test_unlink import shot                              # noqa: E402
from cpc import JOY_FIRE                                 # noqa: E402

FAIL = []
W_ROCK, W_MOUNTAIN = 2, 3                                # src/const.asm
I_DOME_S = 0                                             # bld_items
VIEW_TW, VIEW_TH = 20, 10                                # tiles, 4 bytes x 16 γραμμές
# (όνομα, κέρσορας σε μισά tiles, κάμερα, ο άλλος θόλος, τρεξίματα του reach.py)
SCENES = [("αξονικός, δυτικά του θόλου 0", (-18, 0), (-14, -5), 0, [(2, 5)]),
          ("διαγώνιος, βορειοδυτικά", (-20, -20), (-15, -10), 0, [(3, 7)])]
sb = reach.sb


def check(ok, msg):
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ ") + msg)
    if not ok:
        FAIL.append(msg)


def tables(G):
    b6 = bytes(G.bank(6)[:0x4000])
    domes = [list(b6[R.DOME_TBL + 24 * d:R.DOME_TBL + 24 * d + 4]) for d in range(64)]
    structs = [list(b6[R.STRUCT_TBL + 8 * k:R.STRUCT_TBL + 8 * k + 7])
               for k in range(EC.MAX_STRUCT)]
    return domes, structs


def plan(G, sym, at):
    domes, structs = tables(G)
    dims = G.m.read_ram(TD.L["G_struct_dims"], 64)
    kind, param, w, h = G.m.read_ram(sym["BLD_ITEMS"] + 8 * I_DOME_S, 4)
    return reach.plan(bytes(G.bank(4)[:0x4000]), domes, structs, dims, kind, param, w, h,
                      at[0] & 255, at[1] & 255)


def ridge(G, sym, at, cls):
    """Τα tiles του διαδρόμου του reach.py, του μισού του πλάτους και οι γείτονές
    τους, έξω από τα δύο αποτυπώματα και όσα είναι έδαφος ή σκόνη χωρίς
    κατοχή, γίνονται `cls` (το decor μένει). -> τα tiles του διαδρόμου που
    άλλαξαν, ή None αν ο κανόνας δεν δίνει έναν διάδρομο."""
    res = plan(G, sym, at)
    if not res["ok"] or len(res["corridors"]) != 1:
        return None, res
    _, f, t, runs, tl = res["corridors"][0]
    out = lambda x, y: not (reach.in_dome(*f, x, y) or reach.in_dome(*t, x, y))
    near = set(tl) | set(reach.half_tiles(f, t, runs))
    near |= {(x + i, y + j) for x, y in near for i in (-1, 0, 1) for j in (-1, 0, 1)}
    b4 = G.bank(4)
    for x, y in sorted(near):
        k = reach.widx(x, y)
        if out(x, y) and not b4[k] & 0x30 and b4[k] & 7 in (0, 1):
            b4[k] = b4[k] & 0xC8 | cls
    return [(x, y) for x, y in tl if out(x, y) and b4[reach.widx(x, y)] & 7 == cls], res


def place(G, F, sym, g, at, cam):
    """Η προσομοίωση σταματημένη, η κάμερα, BUILD -> θόλος S στο at. -> (η οθόνη
    πριν, ui_bad στο PLACE, ο διακόπτης της προσομοίωσης)."""
    on = G.still()
    G.camera(*cam)
    before = G.play()
    B.build(G.m, sym, I_DOME_S, g + 6, at=at, place=False)
    G.settle()
    return before, G.m.peek(sym["UI_BAD"]), on


def fire(G, F, sym):
    """FIRE, ως να αδειάσει η λίστα, και ESC δύο φορές: πίσω στην ήρεμη
    κατάσταση, χωρίς φάντασμα. -> ο νέος κόμβος."""
    n0 = G.m.peek(sym["BD_NODE"])
    G.stick(JOY_FIRE)
    G.run(5_000_000, until=lambda: not (G.m.peek(sym["RV_PEND"]) or G.m.peek(sym["UI_OWED"])
                                        or G.m.peek(sym["DIRTY_NUM"])))
    F.esc()
    F.esc()
    G.run(3_000_000, until=lambda: G.m.peek(sym["DIRTY_NUM"]) == 0)
    G.settle()
    return G.m.peek(sym["BD_NODE"]), n0


def bit4_only(a, b):
    """Το πρώτο tile όπου οι δύο κόσμοι διαφέρουν και σε κάτι άλλο εκτός από
    το bit 4, ή None."""
    k = next((k for k in range(0x4000) if (a[k] ^ b[k]) & 0xEF), None)
    if k is None:
        return None
    return f"({k % 128 - 64}, {k // 128 - 64}) #{a[k]:02X} -> #{b[k]:02X}"


def tile_bytes(cam, x, y):
    """Οι θέσεις του G.play() (80 bytes x 160 γραμμές) ενός tile της οθόνης."""
    c, r = x - cam[0], y - cam[1]
    if not (0 <= c < VIEW_TW and 0 <= r < VIEW_TH):
        return []
    return [(16 * r + j) * 80 + 4 * c + i for j in range(16) for i in range(4)]


def scene(sym, g, k, patch=(), quiet=False, cls=W_ROCK, twin=True, png=None):
    """Η σκηνή k: None, ή η πρώτη διαφορά από την πρόζα."""
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    name, at, cam, other, runs = SCENES[k]
    G, F = TD.game(sym, g, patch)
    rock, res0 = ridge(G, sym, at, cls)
    if rock is None:
        return f"{name}: ο κανόνας δεν δίνει έναν διάδρομο ({res0['reason']})"
    if len(rock) < 4:
        return f"{name}: μόνο {len(rock)} tiles του διαδρόμου έγιναν βράχος"
    res = plan(G, sym, at)
    world0 = bytes(G.bank(4)[:0x4000])
    pic0, bad, on = place(G, F, sym, g, at, cam)
    if cls == W_MOUNTAIN:
        # ΒΟΥΝΟ: ο κανόνας λέει όχι, και γιατί· το παιχνίδι το ίδιο
        want = 0xF0 + res["reason"]
        if res["ok"] or bad != want:
            return (f"ΒΟΥΝΟ, {name}: ui_bad #{bad:02X}, ο κανόνας λέει "
                    f"{'ναι' if res['ok'] else f'#{want:02X}'}")
        live = lambda: sum(1 for d in range(64) if TD.dome(G, d)[4])
        d0 = live()
        fire(G, F, sym)
        if live() != d0 or bytes(G.bank(4)[:0x4000]) != world0:
            return f"ΒΟΥΝΟ, {name}: το FIRE έχτισε κάτι ({d0} -> {live()} θόλοι)"
        say(f"ΒΟΥΝΟ, {name}: κόκκινο, ui_bad #{bad:02X} όπως ο κανόνας, και το FIRE δεν έχτισε τίποτα")
        return None
    c = res["corridors"]
    if not res["ok"] or len(c) != 1 or c[0][0] != other or c[0][3] != runs:
        return f"{name}: ο κανόνας λέει {res['reason']}, {[(x[0], x[3]) for x in c]}"
    if bad != 0:
        return f"ΧΤΙΣΜΑ, {name}: ui_bad #{bad:02X} στο PLACE, ο κανόνας λέει 0"
    corr0 = [r[:2] for r in TD.corridors(G) if r[4]]
    n, _ = fire(G, F, sym)
    if (G.m.peek(sym["CAM_TX"]), G.m.peek(sym["CAM_TY"])) != (cam[0] & 255, cam[1] & 255):
        return f"{name}: η κάμερα έφυγε από το {cam}"
    if TD.rec(G, n)[4] != 1:
        return f"ΧΤΙΣΜΑ, {name}: ο κόμβος {n} σε κατάσταση {TD.rec(G, n)[4]}, όχι εργοτάξιο"
    new = [r[:2] for r in TD.corridors(G) if r[4]]
    for r in corr0:
        new.remove(r)
    if sorted(map(sorted, new)) != [sorted([n, other])]:
        return f"ΧΤΙΣΜΑ, {name}: νέες εγγραφές διαδρόμων {new}, η πρόζα λέει {n} - {other}"
    world1 = bytes(G.bank(4)[:0x4000])
    why = bit4_only(world0, world1)
    if why:
        return f"ΧΤΙΣΜΑ, {name}: ο κόσμος άλλαξε και αλλού εκτός από το bit 4: {why}"
    ok, why = TD.world_ok(G)
    if not ok:
        return f"ΧΤΙΣΜΑ, {name}: η κατοχή δεν είναι ό,τι λέει το μοντέλο: {why}"
    under = [world1[reach.widx(x, y)] & 0x37 for x, y in rock]
    if set(under) != {0x10 | W_ROCK}:
        return f"ΧΤΙΣΜΑ, {name}: κάτω από τον διάδρομο {sorted(set(under))}, όχι #12"
    pic1 = G.play()
    same = TD.truth(G)
    if not same[0]:
        return f"ΧΤΙΣΜΑ, {name}: οθόνη/πλήρης σχεδίαση: {same[1]}"
    say(f"ΧΤΙΣΜΑ, {name}: ο θόλος {n} με τον διάδρομο προς τον {other}, "
        f"{len(rock)} tiles του πάνω σε βράχο (#12), ο κόσμος αλλιώς ίδιος")
    if twin:
        # ΕΙΚΟΝΑ: το ίδιο χωρίς τον βράχο
        H, FH = TD.game(sym, g, patch)
        hpic0, hbad, _ = place(H, FH, sym, g, at, cam)
        if hbad != 0:
            return f"ΕΙΚΟΝΑ, {name}: χωρίς βράχο ui_bad #{hbad:02X}"
        fire(H, FH, sym)
        hpic1 = H.play()
        diff = [i for i in range(len(pic1)) if pic1[i] != hpic1[i] and pic0[i] == hpic0[i]]
        if diff:
            i = diff[0]
            return (f"ΕΙΚΟΝΑ, {name}: {len(diff)} bytes διαφέρουν μετά το FIRE χωρίς να "
                    f"διαφέρει το έδαφος, πρώτο στη στήλη {i % 80}, γραμμή {i // 80}")
        seen = [(x, y) for x, y in rock if tile_bytes(cam, x, y)]
        terr = [(x, y) for x, y in seen if any(pic0[i] != hpic0[i] for i in tile_bytes(cam, x, y))]
        drawn = [(x, y) for x, y in seen if any(pic1[i] != pic0[i] for i in tile_bytes(cam, x, y))]
        if len(seen) < 4 or terr != seen or drawn != seen:
            return (f"ΕΙΚΟΝΑ, {name}: {len(seen)} tiles βράχου στην οθόνη, {len(terr)} "
                    f"με άλλο έδαφος, {len(drawn)} με τον διάδρομο από πάνω")
        say(f"ΕΙΚΟΝΑ, {name}: {len(seen)} tiles βράχου στην οθόνη, όλα με τον διάδρομο "
            f"από πάνω· με έδαφος αντί για βράχο η οθόνη διαφέρει μόνο στο έδαφος "
            f"({sum(1 for i in range(len(pic0)) if pic0[i] != hpic0[i])} bytes)")
    # ΤΕΛΟΣ
    G.go(on)
    if not R.finish(G, n):
        return f"ΤΕΛΟΣ, {name}: ο θόλος {n} δεν τελείωσε"
    G.run(3_000_000, until=lambda: G.m.peek(sym["DIRTY_NUM"]) == 0)
    if other not in TD.adj(G, n) or n not in TD.adj(G, other):
        return f"ΤΕΛΟΣ, {name}: λείπει η ακμή {n} <-> {other}: {TD.adj(G, n)} / {TD.adj(G, other)}"
    world2 = bytes(G.bank(4)[:0x4000])
    why = bit4_only(world0, world2)
    if why:
        return f"ΤΕΛΟΣ, {name}: ο κόσμος άλλαξε και αλλού εκτός από το bit 4: {why}"
    ok, why = TD.world_ok(G)
    if not ok:
        return f"ΤΕΛΟΣ, {name}: η κατοχή δεν είναι ό,τι λέει το μοντέλο: {why}"
    same = TD.truth(G)
    if not same[0]:
        return f"ΤΕΛΟΣ, {name}: οθόνη/πλήρης σχεδίαση: {same[1]}"
    if png:
        shot(G, png)                    # με τις λωρίδες της διακοπής (βήμα 83)
    say(f"ΤΕΛΟΣ, {name}: ο θόλος {n} τελείωσε, η ακμή {n} <-> {other} στον γράφο")
    # ΚΑΤΕΔΑΦΙΣΗ
    nbrs = TD.adj(G, n)
    TD.demolish(G, F, at)
    why = TD.common(G, F, n, nbrs)
    if why:
        return f"ΚΑΤΕΔΑΦΙΣΗ, {name}: {why}"
    world3 = bytes(G.bank(4)[:0x4000])
    if world3 != world0:
        k = next(k for k in range(0x4000) if world3[k] != world0[k])
        return (f"ΚΑΤΕΔΑΦΙΣΗ, {name}: ο κόσμος στο ({k % 128 - 64}, {k // 128 - 64}) "
                f"#{world3[k]:02X}, πριν από το FIRE #{world0[k]:02X}")
    say(f"ΚΑΤΕΔΑΦΙΣΗ, {name}: ο κόσμος byte προς byte όπως πριν, ο βράχος #02 χωρίς κατοχή")
    return None


def negatives(sym, g):
    G, _ = TD.game(sym, g)
    ck = sym["CR_CB_CHK"]
    irk = G.m.read_ram(ck, 30).find(bytes([0xE6, 0x37, 0xFE, W_ROCK + 1, 0xD8, 0xFE, 7, 0xC8]))
    st = sym["CRX_EV"]                  # η σφραγίδα του FIRE: cr_stampx, src/ui.asm
    ist = G.m.read_ram(st, 8).find(bytes([0xCB, 0xE6]))           # set 4,(hl)
    dmw = TD.at_ovl(sym, "DM_WORLD", 40, [0x11, 0x00, 0xEF], [(2, 0xE8)])
    neg = [("ο κανόνας ως το βήμα 160", [("ram", ck + irk + 3, W_ROCK)] if irk >= 0 else None),
           ("η σφραγίδα που κάνει τον βράχο θεμέλιο",
            [("ram", st + ist, 0x36), ("ram", st + ist + 1, 0x17)] if ist >= 0 else None),
           ("η κατεδάφιση που σβήνει και την κλάση", dmw)]
    for label, patch in neg:
        if not patch:
            check(False, f"ΑΡΝΗΤΙΚΟ «{label}»: δεν βρέθηκε πού να πειραχτεί")
            continue
        err = scene(sym, g, 0, patch, quiet=True, twin=False)
        check(err is not None, f"ΑΡΝΗΤΙΚΟ «{label}»: " + (err or "ΔΕΝ το έπιασε τίποτα"))


def main():
    sym, g = TG.build()
    for k in range(len(SCENES)):
        err = scene(sym, g, k, png=f"rock_{k}.png")
        check(err is None, err or f"{SCENES[k][0]}: ο διάδρομος πάνω από βράχο χτίζεται, "
                                  f"ζωγραφίζεται, τελειώνει και γκρεμίζεται")
        err = scene(sym, g, k, cls=W_MOUNTAIN, quiet=False)
        check(err is None, err or f"{SCENES[k][0]}: πάνω από βουνό όχι")
    negatives(sym, g)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
