#!/usr/bin/env python3
"""ΕΠΙΣΚΕΠΤΕΣ ΠΟΥ ΠΛΗΡΩΝΟΥΝ, ΚΑΙ ΤΟ ΚΥΡΟΣ (βήμα 134, DESIGN §6.11).

Η αναφορά (tools/econ.py: visit, sol_rollover) και ο Z80 στις άκρες τους είναι
στο tests/test_sim.py: κυλικείο, σαλόνι, τρόφιμο, νερό, δύο ως πέντε
επισκέπτες, το ταβάνι των νομισμάτων, η εύνοια, ο συσσωρευτής. Εδώ το
παιχνίδι, στο colony.sna:

  ΠΛΗΡΩΜΗ   ένα πλοίο επισκεπτών, στο παιχνίδι που τρέχει: δύο επισκέπτες στο
            κυλικείο της αποικίας, πέντε νομίσματα ο καθένας (σαλόνι ή δέντρο
            δεν έχει), η εύνοια +6, και η σειρά 1 του HUD γράφει «$ 10».
  ΣΑΛΟΝΙ    με δέντρα ή σαλόνι (EC_AMENITY) οκτώ ο καθένας.
  ΚΥΡΟΣ     στο τέλος του sol, στο παιχνίδι που τρέχει: το κύρος είναι ο τύπος
            της πρόζας από τα bytes του ίδιου του παιχνιδιού, και με τον
            συσσωρευτή στο 250 έρχεται πλοίο επισκεπτών — που προσγειώνεται
            και πληρώνει.
  ΣΒΗΣΙΜΟ   το HUD γράφει τα νομίσματα μόνο όταν άλλαξαν (hud_cw)· όταν οι
            λωρίδες σβήνουν (hud_inval: άλμα κάμερας, βοήθεια, δίσκος) τα
            ξαναγράφει, ίδια κι ας είναι: το hud_inval κάνει το hud_cw -1.
  ΑΛΜΑ      τα νομίσματα, το κύρος, η εύνοια, ο συσσωρευτής και οι ώρες
            ηρεμίας του βήματος 121 (τα 28 bytes του EC_X) μένουν ίδια σε ένα
            view_draw — άλμα κάμερας, βοήθεια, φόρτωμα. Ως το βήμα 133 το
            fg_build τα μηδένιζε (σημάδια των πρακτόρων 100-127).
  ΚΟΣΤΟΣ    η προσγείωση πέντε επισκεπτών, το τέλος του sol με το κύρος και το
            πλοίο του, και το HUD: με τα ίδια νομίσματα (το συνηθισμένο) και με
            νέα.

Αρνητικά: η πληρωμή που δεν γράφεται, το HUD που διαβάζει μηδέν, ο
συσσωρευτής που δεν φέρνει πλοίο, το HUD που δεν βλέπει το σβήσιμο, το
fg_build σε όλους τους 128 πράκτορες (το ΑΛΜΑ).
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/vasilhs/cpcemu")

import test_game as TG                                     # noqa: E402
import test_trade as TT                                    # noqa: E402
import test_outside as TO                                  # noqa: E402
import hudread                                             # noqa: E402
import econ as EC                                          # noqa: E402

FAIL = []
SK_VISITOR, SK_COLONIST = 2, 0
# Μετρημένα στο βήμα 134, και λίγο πάνω· στο βήμα 133 με τους ίδιους ανιχνευτές
# η προσγείωση επισκεπτών ήταν 1.224 us (έξι τρόφιμα και το ηθικό των 80), το
# τέλος του sol 326 και το HUD 8.794 (DESIGN §6.11). Το HUD με τα ίδια
# νομίσματα 8.810: χωρίς το hud_cw ήταν 9.318, γραμμένα κάθε φορά.
COST = {"προσγείωση, πέντε": 1750, "τέλος του sol, με πλοίο": 500,
        "HUD, τα ίδια $998": 8900, "HUD, 998 -> $999": 9600}


def check(ok, msg):
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ ") + msg)
    if not ok:
        FAIL.append(msg)


def addrs():
    """Οι διευθύνσεις του src/const.asm που θέλει η δοκιμή: της οικονομίας στην
    τράπεζα 2, και του EC_X στην 6."""
    L = TO.layout()
    g, occ = L["G_econ_state"], L["G_node_occ"]
    const = open(os.path.join(ROOT, "src", "const.asm"), encoding="utf-8").read()
    out = {}
    for n in ("EC_STOCK", "EC_SHETA", "EC_SHSTATE", "EC_SHKIND", "EC_AMENITY", "EC_ALIVE",
              "EC_MILE", "EC_NODEATH", "EC_FRAME", "EC_SOLLEN", "EC_SOL", "EC_LANDS"):
        mm = re.search(rf"^{n}\s+equ G_econ_state(?: \+ (\d+))?", const, re.M)
        out[n] = g + int(mm.group(1) or 0)
    x = occ + 128 + EC.AG_FOE0 + EC.AG_NFOE                  # EC_X
    for n, k in (("EC_COINS", 6), ("EC_PREST", 8), ("EC_GOOD", 9), ("EC_VISACC", 10)):
        mm = re.search(rf"^{n}\s+equ EC_X \+ (\d+)", const, re.M)
        assert mm and int(mm.group(1)) == k, f"{n}: το src/const.asm άλλαξε"
        out[n] = x + k
    return out


A = addrs()


class Game(TT.Game):
    def b6v(self, at, n=1):
        v = self.b6[at - 0x4000:at - 0x4000 + n]
        return v[0] if n == 1 else v[0] | v[1] << 8

    def b6s(self, at, v, n=1):
        self.b6[at - 0x4000] = v & 255
        if n == 2:
            self.b6[at - 0x4000 + 1] = v >> 8

    def visitors(self, eta):
        self.m.poke(A["EC_SHSTATE"], 1)
        self.m.poke(A["EC_SHKIND"], SK_VISITOR)
        self.s16(A["EC_SHETA"], eta)


def payment(sym, patch6=(), quiet=False):
    """ΠΛΗΡΩΜΗ, στο παιχνίδι που τρέχει. Η πρώτη διαφορά, ή None."""
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G = Game(sym, patch6=patch6)
    m = G.m
    good0 = G.b6v(A["EC_GOOD"])
    G.visitors(3)
    m.poke(sym["UI_SPD"], 1)
    for f in range(16 * 8):
        m.run_frames(1)
        if m.peek(A["EC_SHSTATE"]) == 2:
            break
    m.run_frames(40)        # το HUD ξαναγράφεται ανά 16 frames, και όχι στην παύση
    m.poke(sym["UI_SPD"], 0)
    coins, good = G.b6v(A["EC_COINS"], 2), G.b6v(A["EC_GOOD"])
    hud = hudread.text(m, sym, 1)
    if m.peek(A["EC_SHSTATE"]) != 2:
        return "ΠΛΗΡΩΜΗ: το πλοίο δεν προσγειώθηκε"
    if (coins, good - good0) != (10, 6):
        return f"ΠΛΗΡΩΜΗ: νομίσματα {coins}, εύνοια +{good - good0} — η πρόζα λέει 10 και +6"
    if hud[36:40].replace("O", "0") != "$ 10":    # το 0 του font διαβάζεται O (hudread)
        return f"ΠΛΗΡΩΜΗ: η σειρά 1 του HUD λέει |{hud}|, όχι «$ 10» στο τέλος"
    if not quiet:
        G.m.screenshot(os.path.join(ROOT, "build", "visit_hud.png"), aspect=True)
    say(f"ΠΛΗΡΩΜΗ: δύο επισκέπτες στο κυλικείο, 10 νομίσματα, εύνοια {good0} -> {good}, "
        f"και το HUD: |{hud.rstrip()}|")
    return None


def lounge(sym):
    """ΣΑΛΟΝΙ: η προσγείωση μόνη της (ship_tick), με EC_AMENITY 2."""
    G = Game(sym)
    m = G.m
    G.visitors(0)
    m.poke(A["EC_AMENITY"], 2)
    G.call("SHIP_TICK")
    coins = G.b6v(A["EC_COINS"], 2)
    return None if coins == 16 else f"ΣΑΛΟΝΙ: νομίσματα {coins} — η πρόζα λέει 16"


def prestige(sym, patch6=(), quiet=False):
    """ΚΥΡΟΣ, στο παιχνίδι που τρέχει: το τέλος του sol. Η πρώτη διαφορά, ή None."""
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G = Game(sym, patch6=patch6)
    m = G.m
    m.poke(A["EC_SHSTATE"], 0)
    G.b6s(A["EC_VISACC"], 250)
    G.b6s(A["EC_GOOD"], 40)
    G.s16(A["EC_FRAME"], G.w16(A["EC_SOLLEN"]) - 40)
    sol0 = m.peek(A["EC_SOL"])
    m.poke(sym["UI_SPD"], 1)
    for _ in range(200):
        m.run_frames(1)
        if m.peek(A["EC_SOL"]) != sol0:
            break
    m.poke(sym["UI_SPD"], 0)
    if m.peek(A["EC_SOL"]) == sol0:
        return "ΚΥΡΟΣ: το sol δεν άλλαξε"
    mile, alive = m.peek(A["EC_MILE"]), m.peek(A["EC_ALIVE"])
    nodeath, amen, good = m.peek(A["EC_NODEATH"]), m.peek(A["EC_AMENITY"]), G.b6v(A["EC_GOOD"])
    want = 10 * bin(mile).count("1") + (alive >> 1) + min(nodeath, 30) + 5 * min(amen, 6) + good
    got, acc = G.b6v(A["EC_PREST"]), G.b6v(A["EC_VISACC"])
    ship = (m.peek(A["EC_SHSTATE"]), m.peek(A["EC_SHKIND"]))
    if good != 39 or got != want:
        return (f"ΚΥΡΟΣ: {got}, ο τύπος {want} (ορόσημα {mile:05b}, ζωντανοί {alive}, σερί "
                f"{nodeath}, σαλόνια {amen}, εύνοια 40 -> {good})")
    if ship != (1, SK_VISITOR) or acc != 250 + want - 256:
        return f"ΚΥΡΟΣ: πλοίο {ship}, συσσωρευτής {acc} — η πρόζα λέει (1, 2) και {250 + want - 256}"
    # και προσγειώνεται, και πληρώνει
    c0 = G.b6v(A["EC_COINS"], 2)
    m.poke(sym["UI_SPD"], 1)
    for _ in range(16 * 30):
        m.run_frames(1)
        if m.peek(A["EC_SHSTATE"]) == 2:
            break
    m.poke(sym["UI_SPD"], 0)
    c1 = G.b6v(A["EC_COINS"], 2)
    if c1 <= c0:
        return f"ΚΥΡΟΣ: το πλοίο του κύρους δεν πλήρωσε ({c0} -> {c1})"
    say(f"ΚΥΡΟΣ: στο τέλος του sol {want} = 10 x {bin(mile).count('1')} + {alive >> 1} + "
        f"{min(nodeath, 30)} + 5 x {min(amen, 6)} + {good}; ο συσσωρευτής 250 -> {acc} με "
        f"πλοίο επισκεπτών, που προσγειώθηκε και έδωσε {c1 - c0}")
    return None


def cold(sym, patch0=()):
    """ΣΒΗΣΙΜΟ: $999 στο HUD, οι λωρίδες σβήνουν, και το HUD τα ξαναγράφει."""
    G = Game(sym)
    m = G.m
    G.b6s(A["EC_COINS"], 999, 2)
    G.call("HUD_DRAW", False, 0xC0)
    first = hudread.text(m, sym, 1)
    for at, v in patch0:
        m.poke(at, v)
    G.call("HUD_INVAL", False, 0xC0)
    G.call("HUD_DRAW", False, 0xC0)
    hud = hudread.text(m, sym, 1)
    if first[36:40] != "$999" or hud[36:40] != "$999":
        return f"ΣΒΗΣΙΜΟ: πριν |{first[36:40]}|, μετά |{hud[36:40]}| — όχι «$999» και τα δύο"
    return None


def jump(sym, patch0=()):
    """ΑΛΜΑ: το EC_X μένει σε ένα view_draw. Η πρώτη διαφορά, ή None."""
    G = Game(sym)
    m = G.m
    for at, v in patch0:
        m.poke(at, v)
    x = A["EC_COINS"] - 6                                      # EC_X
    want = bytes([3, 0x12, 0x34, 2, 0x56, 0x78, 123, 0, 77, 50, 200] + list(range(0x40, 0x51)))
    for k, v in enumerate(want):
        G.b6s(x + k, v)
    G.call("VIEW_DRAW", False, 0xC0)
    got = bytes(G.b6v(x + k) for k in range(28))
    if got != want:
        return f"ΑΛΜΑ: το EC_X μετά το view_draw {got.hex()}, ήταν {want.hex()}"
    return None


def cost(sym):
    G = Game(sym)
    m = G.m
    base = G.probe([], True)
    out = {}
    # πέντε επισκέπτες (κύρος 250), με σαλόνι: ο μακρύτερος δρόμος
    G.visitors(0)
    G.b6s(A["EC_PREST"], 250)
    m.poke(A["EC_AMENITY"], 2)
    G.set_stock({EC.S_FOOD: 300, EC.S_WATER: 300})
    out["προσγείωση, πέντε"] = G.call("SHIP_TICK", True) - base
    # το τέλος του sol με το πλοίο του κύρους
    m.poke(A["EC_SHSTATE"], 0)
    G.b6s(A["EC_VISACC"], 255)
    out["τέλος του sol, με πλοίο"] = G.call("SOL_ROLLOVER", True) - base
    G.b6s(A["EC_COINS"], 998, 2)
    G.call("HUD_DRAW", True, 0xC0)
    out["HUD, τα ίδια $998"] = G.call("HUD_DRAW", True, 0xC0) - base
    G.b6s(A["EC_COINS"], 999, 2)
    out["HUD, 998 -> $999"] = G.call("HUD_DRAW", True, 0xC0) - base
    return out


def main():
    sym, g = TG.build()
    why = payment(sym)
    check(why is None, why or "πληρωμή: δύο επισκέπτες, δέκα νομίσματα, και το HUD τα δείχνει")
    why = lounge(sym)
    check(why is None, why or "σαλόνι: οκτώ ο καθένας")
    why = prestige(sym)
    check(why is None, why or "κύρος: ο τύπος της πρόζας, και το πλοίο του συσσωρευτή")
    got = cost(sym)
    why = jump(sym)
    check(why is None, why or "άλμα: νομίσματα, κύρος και ώρες ηρεμίας μένουν σε ένα view_draw")
    why = cold(sym)
    check(why is None, why or "σβήσιμο: τα νομίσματα ξαναγράφονται, ίδια κι ας είναι")
    check(all(got[k] <= COST[k] for k in COST),
          "κόστος: " + ", ".join(f"{k} {got[k]} us (ταβάνι {COST[k]})" for k in COST))

    # --- ΑΡΝΗΤΙΚΑ, στην τράπεζα 6 ---
    G = Game(sym)
    b6 = lambda name, n: bytes(G.b6[sym[name] - 0x4000:sym[name] - 0x4000 + n])
    find = lambda name, n, pat: [sym[name] + k for k in range(n - len(pat) + 1)
                                 if list(b6(name, n)[k:k + len(pat)]) == pat]
    c = A["EC_COINS"]
    sc = sym["SHIP_CALL"]
    negs = (
        ("η πληρωμή δεν γράφεται", find("SV_PAY", 16, [0x22, c & 255, c >> 8]), 3, payment),
        ("το HUD διαβάζει μηδέν", find("VS_COINS", 3, [0x2A, c & 255, c >> 8]), None, payment),
        ("ο συσσωρευτής δεν φέρνει πλοίο", find("SR_PRES", 120, [0xCD, sc & 255, sc >> 8]), 3,
         prestige),
    )
    # --- ΑΡΝΗΤΙΚΟ, στην τράπεζα 0: το hud_inval δεν ξεχνά τα νομίσματα ---
    cw = sym["HUD_CW"]
    pat = [0x21, 0xFF, 0xFF, 0x22, cw & 255, cw >> 8]
    ram = G.m.read_ram(0, 0x4000)
    at = [k for k in range(0x4000 - len(pat)) if list(ram[k:k + len(pat)]) == pat]
    if len(at) != 1 or at[0] != sym["HUD_INVAL"]:
        check(False, f"ΑΡΝΗΤΙΚΟ «το HUD δεν βλέπει το σβήσιμο»: δεν βρέθηκε ({len(at)} θέσεις)")
    else:
        why = cold(sym, [(at[0] + k, 0) for k in (3, 4, 5)])      # ld (hud_cw),hl -> nop
        check(why is not None, f"ΑΡΝΗΤΙΚΟ «το HUD δεν βλέπει το σβήσιμο»: {why or 'ΔΕΝ ΠΙΑΣΤΗΚΕ'}")
    fn = [sym["FGB_ALL"]] if list(G.m.read_ram(sym["FGB_ALL"], 2)) == [0x06, 100] else []
    why = jump(sym, [(fn[0] + 1, 128)]) if fn else "δεν βρέθηκε"
    check(bool(fn) and why is not None,
          f"ΑΡΝΗΤΙΚΟ «το fg_build σε όλους τους 128 πράκτορες»: {why or 'ΔΕΝ ΠΙΑΣΤΗΚΕ'}")
    for label, at, nops, test in negs:
        if len(at) != 1:
            check(False, f"ΑΡΝΗΤΙΚΟ «{label}»: δεν βρέθηκε ο κώδικας ({len(at)} θέσεις)")
            continue
        p = ([(at[0] + k, 0) for k in range(nops)] if nops else
             [(at[0], 0x21), (at[0] + 1, 0), (at[0] + 2, 0)])          # ld hl,0
        why = test(sym, patch6=p, quiet=True)
        check(why is not None, f"ΑΡΝΗΤΙΚΟ «{label}»: {why or 'ΔΕΝ ΠΙΑΣΤΗΚΕ'}")
    print("ΟΛΑ ΟΚ" if not FAIL else f"{len(FAIL)} ΑΠΟΤΥΧΙΕΣ")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
