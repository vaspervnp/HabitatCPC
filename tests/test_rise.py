#!/usr/bin/env python3
"""Το εργοτάξιο υψώνεται από κάτω όσο φτάνουν τα φορτία του (βήμα 200, DESIGN §6.9).

Ο παίκτης: «Μέχρι να πάνε όλα να φαίνεται γραμμή παρά γραμμή το κτήριο.» Οι
αποφάσεις του: από κάτω προς τα πάνω, ανάλογα με τα φορτία που έφτασαν, και
από πάνω το έδαφος· οι ρίγες του βήματος 109 μένουν ως να τελειώσει ο
μηχανικός· οι διάδρομοι φαίνονται από την αρχή.

  ΑΚΕΡΑΙΟΤΗΤΑ  όσο χρωστά, η ακεραιότητα p του εργοταξίου είναι το μερίδιο
               που έφτασε: κάθε φορτίο την κάνει p + (255 - p) / (όσα μένουν
               + 1), δηλαδή 255 x k / N μετά από k από τα N· με το τελευταίο
               0, για τον χτίστη, που την ανεβάζει όπως ως τώρα.
  ΓΡΑΜΜΕΣ     ένα εργοτάξιο που χρωστά δείχνει τις κάτω H x p / 256 γραμμές
               του πλαισίου του (H το ύψος του): πάνω από αυτές η οθόνη είναι
               ό,τι θα ήταν με p = 0, από εκεί και κάτω ό,τι θα ήταν ολόκληρο —
               σε όλη την οθόνη, όχι μόνο στο πλαίσιο. Με το τελευταίο φορτίο
               ολόκληρο.
  ΑΛΗΘΕΙΑ      μετά από κάθε φορτίο η οθόνη είναι ίδια με πλήρη σχεδίαση: οι
               σειρές που φάνηκαν ξαναζωγραφίζονται (ένα DK_RSIZE με την πρόοδο
               και ένα DK_RECT με τον κόμβο, που το dh_rise κάνει σειρές).
  ΕΔΑΦΟΣ       μια δομή χωρίς φορτίο είναι το έδαφος και οι ρίγες στο κέντρο,
               και από το βήμα 202 η κορδέλα στο πλαίσιο (tests/test_tape.py):
               η οθόνη χωρίς τη δομή διαφέρει μόνο στο ορθογώνιο των ριγών, σε
               όλο του, και στις θέσεις της κορδέλας. Με το μισό φορτίο οι
               ρίγες ολόκληρες.
  ΜΕΤΕΩΡΙΤΗΣ   ένα εργοτάξιο που χρωστά κρατά το μερίδιό του όταν το χτυπήσει
               (ως το βήμα 199 ήταν 0 εκεί έτσι κι αλλιώς)· ένα που χτίζεται
               χάνει την πρόοδο του χτίστη, όπως ως τώρα.

Στην αποικία δοκιμών: ένας μεσαίος θόλος (εργοστάσιο) χωρίς αποθέματα, και
μετά με αποθέματα ως να φτάσουν όλα· ένα ηλιακό με το ένα από τα δύο φορτία
του. Ο μετεωρίτης είναι το mt_hit του src/meteor.asm, με την εγγραφή.

Αρνητικά, με τον κώδικα πειραγμένο στη μνήμη: ο θόλος ολόκληρος (ob_rise ένα
ret)· η δομή ολόκληρη (το os_site δεν κοιτάζει το χρέος)· καμία πρόοδος (το
sp_dlv χωρίς το ld (hl),a)· καμία σειρά στη λίστα (sdl_view ένα ret)· ο
χειριστής δεν βρίσκει σειρές (dh_rise ένα ret)· ο μετεωρίτης σβήνει το μερίδιο
(mt_site χωρίς το ret nz)· το clip δεν ξαναπέφτει (ob_fall ένα ret)· οι ρίγες
κομμένες (ob_fallm χωρίς το st_mark).
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
import balance as B                                      # noqa: E402
import codeat as CA                                      # noqa: E402
import ovmap as OV                                       # noqa: E402

FAIL = []
DS_BUILDING, DS_ACTIVE = 1, 2
I_SOLAR = 4
DOME_QH = (32, 48, 64)                                   # DOME_S_H.. (build/sprite_consts.asm)
SOLAR_H = 48                                             # struct_dims του ηλιακού l
MARK_W, MARK_H = 2, 6                                    # οι ρίγες (st_mark): κέντρο - 1 byte, - 3 γραμμές
LINES, COLS = 160, 80


def say(ok, msg):
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ: ") + msg)
    if not ok:
        FAIL.append(msg)


def consts():
    c = open(os.path.join(ROOT, "src", "const.asm"), encoding="utf-8").read()
    return {n: int(re.search(rf"^{n}\s+equ\s+#([0-9A-Fa-f]+)", c, re.M).group(1), 16)
            for n in ("GA_PORT", "PAGE_B1", "PAGE_B6")}


def s8(v):
    return v - 256 if v > 127 else v


def rise(p, left):
    """Η πρόζα: η ακεραιότητα μετά από ένα φορτίο, με `left` να μένουν."""
    return 0 if left == 0 else p + (255 - p) // (left + 1)


def off(node):
    return R.DOME_TBL + node * 24 if node < 64 else R.STRUCT_TBL + (node - 64) * 8


def rec(G, node):
    b6, o = G.bank(6), off(node)
    return [b6[o + k] for k in range(8)]


def left(r, node):
    """Τα φορτία που χρωστιούνται: θόλος D_POWER + D_OPS, δομή τα δύο μισά του ST_OWED."""
    return r[6] + r[7] if node < 64 else (r[7] & 15) + (r[7] >> 4)


def frame(G, sym, node):
    """(πάνω γραμμή, ύψος) του πλαισίου στην οθόνη: ob_frame και ob_struct."""
    r = rec(G, node)
    sy = 8 * (s8(r[1]) - 2 * s8(G.m.peek(sym["CAM_TY"])))
    h = 2 * DOME_QH[r[2]] if node < 64 else SOLAR_H
    return sy - h // 2, h


def apply(G, sym, patch):
    """(τράπεζα ή None, διεύθυνση, τιμή): None στη μνήμη που φαίνεται, 6 στο
    παράθυρο της 6, "r1" στο OV_R1."""
    for where, at, v in patch:
        if where is None:
            G.m.poke(at, v)
        elif where == "r1":
            OV.poke(G.m, sym, "rise", at, v)
        else:
            G.bank(where)[at - 0x4000] = v


def looks(G, node):
    """Με σταματημένη προσομοίωση: (η οθόνη, πλήρης σχεδίαση, πλήρης με p = 0,
    πλήρης ολόκληρο, πλήρης χωρίς το εργοτάξιο). Η εγγραφή ξαναγίνεται όπως
    ήταν πριν από την τελευταία."""
    on = G.still()
    pic = G.play()
    b6, o = G.bank(6), off(node)
    keep = [b6[o + k] for k in range(8)]
    out = []
    for edit in ({5: 0}, {6: 0, 7: 0} if node < 64 else {7: 0}, {4: 0}):
        for k, v in edit.items():
            b6[o + k] = v
        G.full()
        out.append(G.play())
        for k in range(8):
            b6[o + k] = keep[k]
    G.full()
    ref = G.play()
    G.go(on)
    return (pic, ref) + tuple(out)


def rows(a, y):
    return a[y * COLS:(y + 1) * COLS]


def lines(ref, empty, whole, top, h, p):
    """Οι γραμμές της οθόνης που δεν είναι ό,τι λέει η πρόζα, και πού κόβει."""
    cut = top + h - (h * p >> 8)
    bad = [y for y in range(LINES)
           if rows(ref, y) != rows(empty if top <= y < cut else whole, y)]
    return bad, cut


def check(G, sym, node, what, p):
    """ΓΡΑΜΜΕΣ και ΑΛΗΘΕΙΑ για την κατάσταση που είναι: None ή η διαφορά. Με p
    None το εργοτάξιο δεν χρωστά πια: μόνο η ΑΛΗΘΕΙΑ (ολόκληρο είναι η πλήρης
    σχεδίαση του ίδιου)."""
    top, h = frame(G, sym, node)
    pic, ref, empty, whole, _ = looks(G, node)
    same = R.shape(pic, ref)
    if p is None:
        return None if same[0] else f"{what}: οθόνη/πλήρης σχεδίαση: {same[1]}"
    bad, cut = lines(ref, empty, whole, top, h, p)
    seen = [y for y in range(max(top, 0), min(top + h, LINES)) if rows(empty, y) != rows(whole, y)]
    if not same[0] or bad or not seen:
        return (f"{what}: p {p}, πλαίσιο {top}+{h}, κόβει στη γραμμή {cut}· οθόνη/πλήρης "
                f"σχεδίαση: {same[1]}· γραμμές που δεν είναι ούτε του p = 0 από πάνω ούτε "
                f"του ολόκληρου από κάτω: {bad[:8]}{'…' if len(bad) > 8 else ''} "
                f"({len(seen)} γραμμές όπου διαφέρουν τα δύο)")
    return None


def meteor(G, sym, node):
    """Το mt_hit (src/meteor.asm) στην εγγραφή του κόμβου, από την κορυφή του
    βρόχου, με την 6 μέσα όπως στον τροχό· η εγγραφή μετά."""
    k, m = consts(), G.m
    for _ in range(40000):
        if G.top <= m.pc < G.top + 13:
            break
        m.run_us(50)
    w = lambda a: [a & 255, a >> 8]
    code = ([0xF3, 0x01] + w(k["GA_PORT"] + k["PAGE_B6"]) + [0xED, 0x49]
            + [0x21] + w(0x4000 + off(node)) + [0x3E, node, 0x16, 0x00]
            + [0xCD] + w(sym["MT_HIT"])
            + [0x01] + w(k["GA_PORT"] + k["PAGE_B1"]) + [0xED, 0x49])
    m.run_code(R.PROBE, bytes(code + [0x18, 0xFE]), frames=20)
    m.set_pc(G.top)
    G.last, G.inw = None, False
    return rec(G, node)


# --------------------------------------------------------------------------
# ΘΟΛΟΣ — ένας μεσαίος, χωρίς αποθέματα, και μετά με αποθέματα
# --------------------------------------------------------------------------
def dome(sym, g, patch=(), quiet=False):
    say_ = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G = R.Game(sym, g)
    apply(G, sym, patch)
    F = TF.Fit(G, sym, g)
    F.set_stocks(0, 0)
    tx, ty = B.clear_spots(8, 1, dome=True)[0]
    G.camera(tx - 6, ty - 1)
    at = (2 * tx + 8, 2 * ty + 8)
    B.build(G.m, sym, TF.I_DOME_M, g + 6, at=at, room=TF.RM_FACTORY, fit=False)
    node = G.m.peek(sym["BD_NODE"])
    G.settle()
    r = rec(G, node)
    n = left(r, node)
    if r[4] != DS_BUILDING or r[5] != 0 or not n:
        return f"ΘΟΛΟΣ: ο {node} στο FIRE {r} — θέλει εργοτάξιο με ακεραιότητα 0 που χρωστά"
    why = check(G, sym, node, f"ΘΟΛΟΣ {node}, κανένα φορτίο από τα {n}", 0)
    if why:
        return why
    total, p, steps = n, 0, []
    F.set_stocks(999, 999)
    for _ in range(6000):
        G.m.run_frames(5)
        r = rec(G, node)
        k = left(r, node)
        if k == n:
            continue
        want = p
        for j in range(n - 1, k - 1, -1):
            want = rise(want, j)
        got = r[5]
        if k == 0:
            ok = r[4] == DS_BUILDING and got % 32 == 0      # ο χτίστης ίσως ξεκίνησε (BUILD_STEP)
        else:
            ok = got == want
        if not ok:
            return (f"ΘΟΛΟΣ {node}: από {n} σε {k} φορτία που μένουν (από {total}) η "
                    f"ακεραιότητα {p} -> {got} — η πρόζα λέει {want}")
        steps.append((total - k, got))
        why = check(G, sym, node, f"ΘΟΛΟΣ {node}, {total - k} φορτία από τα {total}",
                    got if k else None)
        if why:
            return why
        p, n = got, k
        if k == 0:
            break
    else:
        return f"ΘΟΛΟΣ {node}: έμειναν {n} φορτία από τα {total}"
    ideal = [(k, 255 * k // total) for k, _ in steps[:-1]]
    if any(abs(v - 255 * k / total) >= 1.0 for k, v in steps[:-1]):
        return f"ΘΟΛΟΣ {node}: ακεραιότητες {steps}, όχι 255 x k / N {ideal}"
    say_(f"ΘΟΛΟΣ: ο {node} (M, εργοστάσιο), {total} φορτία· (φορτία, ακεραιότητα) {steps}· "
         f"σε κάθε ένα οι γραμμές από κάτω, η οθόνη ίδια με πλήρη σχεδίαση")
    # --- ο μετεωρίτης, όταν χτίζεται: η πρόοδος του χτίστη χάνεται ---
    for _ in range(4000):
        if rec(G, node)[5] >= 64 or rec(G, node)[4] != DS_BUILDING:
            break
        G.m.run_frames(2)
    on = G.still()
    r0 = rec(G, node)
    r1 = meteor(G, sym, node)
    G.go(on)
    if r0[4] != DS_BUILDING or r0[5] < 64 or r1[4] != DS_BUILDING or r1[5] != 0:
        return (f"ΜΕΤΕΩΡΙΤΗΣ: ο θόλος {node} που χτίζεται: {r0[4:8]} -> {r1[4:8]} — "
                f"θέλει ακεραιότητα πάνω από 64, και μετά 0")
    say_(f"ΜΕΤΕΩΡΙΤΗΣ: ο θόλος που χτίζεται ({r0[5]}) χάνει την πρόοδο του χτίστη")
    return None


# --------------------------------------------------------------------------
# ΗΛΙΑΚΟ — έδαφος και ρίγες, το ένα από τα δύο φορτία, ο μετεωρίτης
# --------------------------------------------------------------------------
def solar(sym, g, patch=(), quiet=False):
    say_ = (lambda s: None) if quiet else (lambda s: print("    " + s))
    G = R.Game(sym, g)
    apply(G, sym, patch)
    F = TF.Fit(G, sym, g)
    F.set_stocks(0, 0)
    # Ο ΚΕΡΣΟΡΑΣ ΤΟΥ ΠΑΙΧΝΙΔΙΟΥ (βήμα 202): το B.build γράφει το cur_hx μετά την
    # επιλογή, και το ηλιακό έπεφτε μισό tile έξω από τα tiles του — κάτι που
    # στο παιχνίδι δεν γίνεται (bds_lp). Η τοποθέτηση ξαναζωγραφίζει τα tiles,
    # και η κορδέλα στη μισή στήλη και σειρά από έξω έμενε απ' έξω.
    import test_tape as TT
    at = TT.parity(G, sym, I_SOLAR, B.live_spot(G.m, sym, I_SOLAR, (0, 24)))
    G.camera((at[0] >> 1) - 10, (at[1] >> 1) - 5)
    if not B.build(G.m, sym, I_SOLAR, g + 6, at=at, fit=False):
        return f"ΗΛΙΑΚΟ: δεν μπήκε στο {at}"
    node = G.m.peek(sym["BD_NODE"])
    G.settle()
    r = rec(G, node)
    if r[4] != DS_BUILDING or r[5] != 0 or r[7] != 0x20:
        return f"ΗΛΙΑΚΟ: το {node} στο FIRE {r} — θέλει εργοτάξιο, ακεραιότητα 0, #20"
    # --- ΕΔΑΦΟΣ: χωρίς φορτίο, μόνο οι ρίγες ---
    pic, ref, empty, whole, gone = looks(G, node)
    cx = 2 * (s8(r[0]) - 2 * s8(G.m.peek(sym["CAM_TX"]))) - 1
    cy = 8 * (s8(r[1]) - 2 * s8(G.m.peek(sym["CAM_TY"]))) - 3
    box = {(x, y) for x in range(cx, cx + MARK_W) for y in range(cy, cy + MARK_H)}
    diff = {(i % COLS, i // COLS) for i, (a, b) in enumerate(zip(ref, gone)) if a != b}
    tape = TT.tape_on(*TT.frame(G, sym, node))
    if diff - box - tape or len(diff - tape) < len(box) // 2 or not R.shape(pic, ref)[0]:
        return (f"ΕΔΑΦΟΣ: το ηλιακό {node} χωρίς φορτίο διαφέρει από την οθόνη χωρίς αυτό σε "
                f"{len(diff)} bytes, {len(diff - box - tape)} έξω από τις ρίγες ({cx}, {cy}) 2x6 "
                f"και την κορδέλα· οθόνη/πλήρης σχεδίαση: {R.shape(pic, ref)[1]}")
    say_(f"ΕΔΑΦΟΣ: το ηλιακό {node} χωρίς φορτίο είναι το έδαφος, οι ρίγες και η κορδέλα "
         f"({len(diff - tape)} bytes στο 2x6 του κέντρου, {len(diff & tape)} της κορδέλας)")
    # --- ένα φορτίο από τα δύο ---
    F.set_stocks(12, 0)
    for _ in range(4000):
        G.m.run_frames(5)
        if rec(G, node)[7] != 0x20:
            break
    r = rec(G, node)
    if r[7] != 0x10 or r[5] != rise(0, 1):
        return f"ΗΛΙΑΚΟ: μετά το πρώτο φορτίο {r} — θέλει #10 και ακεραιότητα {rise(0, 1)}"
    why = check(G, sym, node, f"ΗΛΙΑΚΟ {node}, ένα φορτίο από τα δύο", r[5])
    if why:
        return why
    pic, ref, empty, whole, gone = looks(G, node)
    lost = [(x, y) for x, y in box if 0 <= y < LINES and ref[y * COLS + x] != whole[y * COLS + x]]
    if lost:
        return f"ΗΛΙΑΚΟ: οι ρίγες με το μισό φορτίο δεν είναι ολόκληρες: {sorted(lost)[:6]}"
    say_(f"ΗΛΙΑΚΟ: ένα φορτίο από τα δύο, ακεραιότητα {r[5]}: οι κάτω "
         f"{SOLAR_H * r[5] >> 8} γραμμές και οι ρίγες ολόκληρες")
    # --- ΜΕΤΕΩΡΙΤΗΣ: το εργοτάξιο που χρωστά κρατά το μερίδιό του ---
    on = G.still()
    r0 = rec(G, node)
    r1 = meteor(G, sym, node)
    G.go(on)
    if r1 != r0:
        return f"ΜΕΤΕΩΡΙΤΗΣ: το ηλιακό που χρωστά {r0[4:8]} -> {r1[4:8]} — θέλει ίδιο"
    say_(f"ΜΕΤΕΩΡΙΤΗΣ: το ηλιακό που χρωστά κρατά το {r1[5]}")
    return None


def main():
    sym, g = TG.build()
    for fn, what in ((dome, "ΘΟΛΟΣ: γραμμή γραμμή από κάτω, και ο μετεωρίτης στον χτίστη"),
                     (solar, "ΗΛΙΑΚΟ: έδαφος και ρίγες, το μισό, και ο μετεωρίτης στο χρέος")):
        why = fn(sym, g)
        say(why is None, why or what)

    # --- αρνητικά ---
    G = R.Game(sym, g)
    b6 = lambda a, n: bytes(G.bank(6)[a - 0x4000 + k] for k in range(n))
    m0 = lambda a, n: bytes(G.m.read_ram(a, n))
    find = lambda blob, pat: next((k for k in range(len(blob)) if list(blob[k:k + len(pat)]) == pat), None)
    os_ = find(m0(sym["OS_SITE"], 24), [0x23, 0x23, 0x7E, 0xB7, 0xC8])   # inc hl ×2 · ld a,(hl) · or a · ret z
    dl = find(b6(sym["SP_DLV"], 72), [0x77, 0x5F, 0x21, 9, 0])          # ld (hl),a · ld e,a · ld hl,9
    mt = find(b6(sym["MT_SITE"], 16), [0xB6, 0xC0])                     # or (hl) · ret nz
    if None in (os_, dl, mt):
        say(False, f"τα σημεία των αρνητικών δεν βρέθηκαν: {os_, dl, mt}")
        return 1
    fm = sym["OB_FALLM"]
    for label, fn, patch in (
            ("ο θόλος ολόκληρος", dome, [(None, sym["OB_RISE"], 0xC9)]),
            ("η δομή ολόκληρη", solar, [(None, sym["OS_SITE"] + os_ + 4, 0xC9)]),
            ("καμία πρόοδος", dome, [(6, sym["SP_DLV"] + dl, 0x00)]),
            ("καμία σειρά στη λίστα", dome, [(None, sym["SDL_VIEW"], 0xC9)]),
            ("ο χειριστής δεν βρίσκει σειρές", dome, [("r1", sym["DH_RISE"], 0xC9)]),
            ("ο μετεωρίτης σβήνει το μερίδιο", solar, [(6, sym["MT_SITE"] + mt + 1, 0x00)]),
            ("το clip δεν ξαναπέφτει", solar, [(None, sym["OB_FALL"], 0xC9)]),
            ("οι ρίγες κομμένες", solar, [(None, fm + k, 0x00) for k in range(4)])):
        why = fn(sym, g, patch, quiet=True)
        say(why is not None, f"ΑΡΝΗΤΙΚΟ «{label}»: " + (why[:110] if why else "ΠΕΡΝΑ"))
    print(f"\n{len(FAIL)} ΑΠΟΤΥΧΙΕΣ" if FAIL else "\nΟΛΑ ΚΑΛΑ")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
