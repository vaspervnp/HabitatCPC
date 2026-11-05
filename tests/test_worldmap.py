#!/usr/bin/env python3
"""Ο χάρτης του κόσμου (βήμα 186, DESIGN §9.3, src/map_ov.asm): το TAB.

Ο παίκτης ρώτησε «υπάρχει minimap;» και ζήτησε «φτιάξε τον χάρτη σε σελίδα με
πλήκτρο». Διάλεξε όλη την οθόνη σε Mode 1, τέσσερα χρώματα, όλο τον κόσμο με
ένα pixel το tile, και: μαύρο ό,τι χτίζεται, καφέ ό,τι όχι, μπλε το νερό,
λευκή η αποικία, οι φλέβες καφέ με λευκές κουκκίδες (σκακιέρα), και το
πλαίσιο της οθόνης με XOR. Τα βέλη το κουνούν, το SPACE πηγαίνει εκεί, το
ESC γυρίζει όπως ήταν.

Στο colony.sna, παύση:

  ΠΛΗΚΤΡΟ   ο κώδικας διαβάζει τη γραμμή 8 με τη μάσκα #10, το TAB του CPC, στο
            bk_more και στο ms_key. Ο εξομοιωτής (chips, cpc.h) δεν έχει TAB:
            η δοκιμή κάνει τις δύο μάσκες #08, το Q, που δεν είναι κουμπί στη
            μπάρα των ομάδων. Σε άλλη μπάρα (ΕΝΕΡΓΕΙΑ) το Q δεν ανοίγει τίποτα.
  ΧΑΡΤΗΣ    τα 128 x 128 pixels της οθόνης απέναντι στο μοντέλο της πρόζας,
            από το επίπεδο του κόσμου (τράπεζα 4), με το πλαίσιο στην κάμερα·
            σε πόσα frames.
  ΒΕΛΗ      ένα πάτημα ένα tile· κρατημένα ως το χείλος, 0 και 108, 0 και 118,
            όσο και η κάμερα· ο χάρτης ξανά απέναντι στο μοντέλο.
  SPACE     η κάμερα στο πλαίσιο, ο κέρσορας στη μέση του, το LOOK, και η
            οθόνη ίδια με μια πλήρη σχεδίαση.
  ESC       η κάμερα και ο κέρσορας όπως ήταν, η οθόνη ίδια με πλήρη σχεδίαση.

Αρνητικά: χωρίς κατοχή, το νερό καφέ, φλέβες χωρίς κουκκίδες, χωρίς
πλαίσιο, χωρίς ταβάνι στο χείλος, το SPACE χωρίς την κάμερα, το TAB όχι στη
μπάρα.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/vasilhs/cpcemu")

import test_game as TG                                  # noqa: E402
import test_reveal as TR                                # noqa: E402
import ovmap as OV                                      # noqa: E402
import cpc                                              # noqa: E402

FAIL = []
VIEW_TW, VIEW_TH = 20, 10
FX_MAX, FY_MAX = 64 - VIEW_TW + 64, 64 - VIEW_TH + 64   # CAM_XMAX/YMAX + 64
OPEN_FRAMES = 25                                        # ταβάνι: 500 ms
# Το pen κάθε κλάσης: έδαφος, σκόνη, βράχος, βουνό, νερό, βαθύ νερό, κρατήρας,
# θεμέλιο (η πρόζα του src/map_ov.asm).
CLS_PEN = [0, 0, 1, 1, 2, 2, 1, 3]


def check(ok, msg):
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ ") + msg, flush=True)
    if not ok:
        FAIL.append(msg)


def model(b4, fx, fy):
    """Τα pens του χάρτη, όπως τα λέει η πρόζα, και το πλαίσιο με XOR 3."""
    out = []
    for y in range(128):
        row = []
        for x in range(128):
            b = b4[y * 128 + x]
            if b & 0x30:
                p = 3
            elif b & 7 == 3 and b & 8:
                p = 3 if (x + y) % 2 == 0 else 1
            else:
                p = CLS_PEN[b & 7]
            row.append(p)
        out.append(row)
    for x in range(fx, fx + VIEW_TW):
        out[fy][x] ^= 3
        out[fy + VIEW_TH - 1][x] ^= 3
    for y in range(fy + 1, fy + VIEW_TH - 1):
        out[y][fx] ^= 3
        out[y][fx + VIEW_TW - 1] ^= 3
    return out


class Map(TR.Game):
    def __init__(self, sym, g, patch=(), tab=True):
        super().__init__(sym, g)
        m = self.m
        b1 = self.bank(1)
        # ΤΟ TAB ΓΙΝΕΤΑΙ Q (ο εξομοιωτής δεν έχει TAB): η μάσκα #10 -> #08
        bm, mk = sym["BK_MORE"], sym["MS_KEY"]
        code = bytes(b1[a - 0x4000] for a in range(bm, bm + 40))
        self.tab_at = code.find(bytes([0x01, 0x10, 0x08]))
        ms = bytes(b1[a - 0x4000] for a in range(mk, mk + 8))
        kn = sym["KEY_NOW"] + 8
        self.ms_ok = ms[:6] == bytes([0x3A, kn & 255, kn >> 8, 0xE6, 0x10, 0xCA]) \
            and ms[6:8] == bytes([sym["MP_OPEN"] & 255, sym["MP_OPEN"] >> 8])
        if self.tab_at >= 0 and self.ms_ok:
            b1[bm - 0x4000 + self.tab_at + 1] = 0x08
            b1[mk - 0x4000 + 4] = 0x08
            if not tab:                  # ΑΡΝΗΤΙΚΟ: το call bkm_one του TAB -> nop
                for k in range(3):
                    b1[bm - 0x4000 + self.tab_at + 3 + k] = 0
        for bank_, a, v in patch:
            self.bank(bank_)[a - 0x4000] = v
        self.b4 = self.bank(4)
        self.tap("1")                    # παύση
        self.tap("d")
        self.tap("d")                    # η μπάρα ξανά: το bk_more με το Q

    def tap(self, key, n=1, hold=3, gap=12):
        for _ in range(n):
            self.m.key_down(key)
            self.m.run_frames(hold)
            self.m.key_up(key)
            self.m.run_frames(gap)

    def cam(self):
        p = lambda n: self.m.peek(self.sym[n])
        sb = lambda v: v - 256 if v > 127 else v
        return sb(p("CAM_TX")), sb(p("CAM_TY")), sb(p("CUR_HX")), sb(p("CUR_HY"))

    def screen(self):
        """Τα 128 x 128 pens του χάρτη στην οθόνη (το mp_addr της πρόζας)."""
        sym, m = self.sym, self.m
        camp = m.peek(sym["CAM_P"]) | m.peek(sym["CAM_P"] + 1) << 8
        scr = self.bank(3)
        out = []
        for y in range(128):
            r, ln = 3 + y // 8, y % 8
            row = []
            for xb in range(32):
                q = (camp - 160 + r * 80 + 24 + xb) & 0x7FF
                byte = scr[ln * 0x800 + q]
                for p in range(4):
                    row.append((byte >> (7 - p)) & 1 | ((byte >> (3 - p)) & 1) << 1)
            out.append(row)
        return out

    def in_map(self):
        gh = self.ghbuf
        return gh <= self.m.pc < gh + 1160

    def open(self, limit=60):
        """Q (το TAB), και τα frames ως να είναι ο χάρτης ίδιος με το μοντέλο
        στην κάμερα. -> (frames ή None, η διαφορά)."""
        cx, cy = self.cam()[:2]
        self.fx, self.fy = cx + 64, cy + 64
        want = model(self.b4, self.fx, self.fy)
        self.m.key_down("q")
        self.m.run_frames(3)
        self.m.key_up("q")
        for k in range(limit):
            self.m.run_frames(1)
            if self.screen() == want:
                return k + 4, 0
        return None, diff(self.screen(), want)

    def same(self):
        got = self.screen()
        return diff(got, model(self.b4, self.fx, self.fy))


def diff(a, b):
    return sum(1 for y in range(128) for x in range(128) if a[y][x] != b[y][x])


def find(sym, label, pat, span=80):
    """(τράπεζα, διεύθυνση) του pat στον κώδικα του χάρτη, από το label."""
    mp = OV.pieces(sym)["map"][3]
    gh = OV.pieces(sym)["map"][2]
    lo = sym[label] - gh
    k = mp.find(bytes(pat), lo, lo + span)
    if k < 0:
        return None
    return OV.at(sym, "map", gh + k)


def run(sym, g, patch=(), tab=True, quiet=False, full=True):
    """Ολόκληρη η σειρά. -> η πρώτη διαφορά, ή None."""
    G = Map(sym, g, patch, tab)
    if G.tab_at < 0 or not G.ms_ok:
        return "ΠΛΗΚΤΡΟ: το bk_more ή το ms_key δεν διαβάζουν τη γραμμή 8, #10 (το TAB)"
    c0 = G.cam()
    n, d = G.open()
    if n is None:
        return f"ΧΑΡΤΗΣ: {d} pixels διαφέρουν από το μοντέλο (ή δεν άνοιξε: PC #{G.m.pc:04X})"
    if not quiet:
        print(f"    ΧΑΡΤΗΣ: ίδιος με το μοντέλο σε {n} frames ({n * 20} ms), το πλαίσιο "
              f"στο ({G.fx}, {G.fy})")
    if n > OPEN_FRAMES:
        return f"ΧΑΡΤΗΣ: {n} frames, ταβάνι {OPEN_FRAMES}"
    # --- ΒΕΛΗ ---
    G.tap(cpc.KEY_RIGHT, 5, 3, 4)
    G.tap(cpc.KEY_DOWN, 2, 3, 4)
    G.fx, G.fy = G.fx + 5, G.fy + 2
    d = G.same()
    if d:
        return f"ΒΕΛΗ: πέντε δεξιά και δύο κάτω, {d} pixels διαφέρουν"
    edges = []
    for key, fx, fy in ((cpc.KEY_LEFT, 0, None), (cpc.KEY_UP, None, 0),
                        (cpc.KEY_RIGHT, FX_MAX, None), (cpc.KEY_DOWN, None, FY_MAX)):
        G.m.key_down(key)
        G.m.run_frames(300)
        G.m.key_up(key)
        G.m.run_frames(4)
        G.fx = G.fx if fx is None else fx
        G.fy = G.fy if fy is None else fy
        got = (G.m.peek(G.sym["MP_FX"]), G.m.peek(G.sym["MP_FY"]))
        edges.append(got)
        if got != (G.fx, G.fy) or G.same():
            return (f"ΧΕΙΛΟΣ: κρατημένο βέλος, το πλαίσιο στο {got} — η πρόζα λέει "
                    f"({G.fx}, {G.fy}), {G.same()} pixels διαφέρουν")
    if not full:
        return None
    # --- SPACE: πήγαινε εκεί ---
    G.tap(cpc.KEY_LEFT, 30, 3, 4)
    G.tap(cpc.KEY_UP, 40, 3, 4)
    G.fx, G.fy = G.fx - 30, G.fy - 40
    G.tap(" ", 1, 3, 120)
    want = (G.fx - 64, G.fy - 64, 2 * (G.fx - 64 + VIEW_TW // 2), 2 * (G.fy - 64 + VIEW_TH // 2))
    got = G.cam()
    st = G.m.peek(sym["UI_STATE"])
    if got != want or st != 0 or G.in_map():
        return (f"SPACE: κάμερα και κέρσορας {got}, κατάσταση {st} — η πρόζα λέει {want}, "
                f"LOOK")
    pic, ref = G.truth()
    bad = sum(1 for a, b in zip(pic, ref) if a != b)
    if bad:
        return f"SPACE: η οθόνη διαφέρει από την πλήρη σχεδίαση σε {bad} bytes"
    if not quiet:
        print(f"    ΒΕΛΗ: ένα πάτημα ένα tile, κρατημένα ως το χείλος {edges}· SPACE: "
              f"κάμερα ({want[0]}, {want[1]}), κέρσορας ({want[2]}, {want[3]}) σε μισά "
              f"tiles, LOOK, η οθόνη ίδια με πλήρη σχεδίαση")
    # --- ESC: όπως ήταν ---
    c1 = G.cam()
    n, d = G.open()
    if n is None:
        return f"ESC: ο χάρτης δεν άνοιξε ξανά ({d} pixels)"
    G.tap(cpc.KEY_RIGHT, 7, 3, 4)
    G.tap(cpc.KEY_ESC, 1, 3, 120)
    pic, ref = G.truth()
    bad = sum(1 for a, b in zip(pic, ref) if a != b)
    if G.cam() != c1 or G.m.peek(sym["UI_STATE"]) != 0 or bad or G.in_map():
        return (f"ESC: κάμερα και κέρσορας {G.cam()} (ήταν {c1}), κατάσταση "
                f"{G.m.peek(sym['UI_STATE'])}, {bad} bytes από την πλήρη σχεδίαση")
    if not quiet:
        print(f"    ESC: ο χάρτης ξανά σε {n} frames, επτά δεξιά, και ESC: κάμερα και "
              f"κέρσορας όπως ήταν {c1}, η οθόνη ίδια με πλήρη σχεδίαση (στην αρχή {c0})")
    return None


def other_bar(sym, g):
    """Σε άλλη μπάρα (ΕΝΕΡΓΕΙΑ: S, T, C) το Q δεν ανοίγει τίποτα."""
    G = Map(sym, g)
    G.tap("p")
    G.m.key_down("q")
    seen = False
    for _ in range(40):
        G.m.run_frames(1)
        seen = seen or G.in_map()
    G.m.key_up("q")
    return seen


def main():
    sym, g = TG.build()
    why = run(sym, g)
    check(why is None, why or "χάρτης: TAB (γραμμή 8, #10), όλος ο κόσμος όπως η πρόζα, "
          "βέλη, χείλος, SPACE και ESC")
    check(not other_bar(sym, g), "στη μπάρα της ΕΝΕΡΓΕΙΑΣ το ίδιο πλήκτρο δεν ανοίγει τον χάρτη")

    negs = []
    p = find(sym, "MPT_LP", [0xE6, 0x30])
    negs.append(("χωρίς κατοχή", p and [(p[0], p[1] + 1, 0)], {}))
    p = OV.at(sym, "map", sym["MP_CLS"] + 4)
    negs.append(("το νερό καφέ", [(p[0], p[1], 0x10)], {}))
    p = find(sym, "MP_VEIN", [0xD0])
    negs.append(("φλέβες χωρίς κουκκίδες", p and [(p[0], p[1], 0xC9)], {}))
    p = OV.at(sym, "map", sym["MP_FRAME"])
    negs.append(("χωρίς πλαίσιο", [(p[0], p[1], 0xC9)], {}))
    p = find(sym, "MPM_CL", [0xFE, FX_MAX + 1])
    negs.append(("χωρίς ταβάνι στο χείλος", p and [(p[0], p[1] + 1, 0xFF)], {"full": False}))
    ct = sym["CAM_TX"]
    p = find(sym, "MPO_GO", [0x22, ct & 255, ct >> 8])
    negs.append(("το SPACE χωρίς την κάμερα", p and [(p[0], p[1] + k, 0) for k in range(3)], {}))
    negs.append(("το TAB όχι στη μπάρα", [], {"tab": False}))
    for name, patch, kw in negs:
        if patch is None:
            check(False, f"ΑΡΝΗΤΙΚΟ «{name}»: το σημείο δεν βρέθηκε")
            continue
        why = run(sym, g, patch, quiet=True, **kw)
        check(why is not None, f"ΑΡΝΗΤΙΚΟ «{name}»: " + (why or "ΔΕΝ το έπιασε τίποτα"))

    print()
    print("ΟΛΑ ΟΚ" if not FAIL else f"{len(FAIL)} ΑΠΟΤΥΧΙΕΣ")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
