#!/usr/bin/env python3
"""Ενα κτίριο μπαίνει και τελειώνει ΧΩΡΙΣ να παγώσει η οθόνη (§6.9, §15).

Ως το βήμα 34 δύο στιγμές ξαναζωγράφιζαν ΟΛΟ το κάδρο: η τοποθέτηση (ui.asm,
uip_fire και uil_second) και η ολοκλήρωση (main.asm, ml_built). Το §15 έγραφε
«0,8 s, μία φορά ανά κτίριο». Μετρημένο με συνεχές ρολόι, ήταν 360-920 ms στην
ολοκλήρωση και 440-1.000 ms στην τοποθέτηση, ανάλογα με το τι φαινόταν — για
να αλλάξουν, στην ολοκλήρωση, το πολύ 1.200 bytes: το εικονίδιο του δωματίου
και οι μηχανές. Μια δομή ως το βήμα 109 δεν άλλαζε ΚΑΝΕΝΑ, γιατί
ζωγραφιζόταν ίδια χτισμένη ή όχι· από το 109 το εργοτάξιο έχει στο κέντρο του
το σήμα της αναμονής (st_mark), και η ολοκλήρωση ξαναζωγραφίζει τα 3x3 tiles
γύρω του (st_built). Ο κέρσορας μένει πάνω στη δομή, οπότε εκεί ο έλεγχος
ΑΛΗΘΕΙΑ γίνεται και ΚΑΤΩ από το φάντασμα (under). Τρία αρνητικά γι' αυτό:
χωρίς το st_mark το εργοτάξιο δεν έχει σήμα· χωρίς το DK_TILE του st_built το
σήμα μένει στη χτισμένη δομή· και χωρίς το dt_ghost_rect του dh_tile το αρχείο
του φαντάσματος κρατά το εργοτάξιο. Το ίδιο και για έναν κρατήρα κάτω από το
πλαίσιο του κέρσορα, που ως το βήμα 108 το ui_hide τον έσβηνε.

Τρία πράγματα ελέγχονται για κάθε περίπτωση, και κανένα δεν είναι «φαίνεται
σωστό»:

  ΚΑΝΑΡΙΝΙ  Ενα byte της οθόνης μακριά από το κτίριο αλλάζει με το χέρι πριν
            από το γεγονός. Μια πλήρης επανασχεδίαση το σβήνει· αν επιζήσει,
            ξαναζωγραφίστηκε μόνο ό,τι έπρεπε. Η παλιά συμπεριφορά το σβήνει
            κάθε φορά.
  ΑΛΗΘΕΙΑ   Η προσομοίωση σταματά, η λίστα αλλαγών αδειάζει, και η οθόνη
            συγκρίνεται με ΠΛΗΡΗ σχεδίαση της ίδιας κατάστασης: έξω από το
            κανάρινο, ΚΑΜΙΑ διαφορά. Ως το βήμα 42 επιτρεπόταν το σχήμα της
            άδειας θέσης δακτυλίου (§15)· το dhs_vacate το έκλεισε.
  ΧΡΟΝΟΣ    Ο μεγαλύτερος γύρος του βρόχου γύρω από το γεγονός, με ρολόι που
            δεν σταματά στις ραφές — η πρώτη μέτρηση έχανε ακριβώς τον γύρο
            που πάγωνε, γιατί έπεφτε ανάμεσα σε δύο κλήσεις.

Και ένα αρνητικό δείγμα μέσα στη δοκιμή: το φάντασμα του κέρσορα κάθεται πάνω
στον θόλο όταν τελειώνει. Αν το dt_ghost γίνει `ret`, η αναίρεση του
φαντάσματος γράφει πίσω το άδειο εργοτάξιο πάνω από τις μηχανές — και ο
έλεγχος ΑΛΗΘΕΙΑ πρέπει να το πιάσει.

Από το βήμα 85 ο θόλος L παίρνει μόνος του διάδρομο προς τον κοντινό θόλο
(src/link.asm): οι γύροι της εμφάνισης είναι οι οκτώ σειρές του εργοταξίου ΚΑΙ
όσες σειρές της διαγωνίου φαίνονται (tools/reach.py για τον διάδρομο, το rows()
του test_link για τις σειρές), πάντα μία ανά γύρο. Χωρίς τον διάδρομο ο θόλος
δεν θα είχε ακμή και δεν θα τελείωνε ποτέ. Για τον διάδρομο ανάμεσα στους δύο S,
που ζητιέται με το χέρι σε χωράφι μακριά από την αποικία, ο κανόνας σβήνει
(balance.no_link).
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/vasilhs/cpcemu")

import cpc                                                         # noqa: E402
import balance as B                                                # noqa: E402
import test_game as T                                              # noqa: E402
import world as W                                                  # noqa: E402
from cpc import JOY_FIRE, KEY_SPACE, KEY_RIGHT                     # noqa: E402

FAIL = []
PROBE = 0x3F10                           # η σκαλωσιά των δοκιμών (§4.2)
HOOK, CNT, RING = 0x3EC0, 0x3EE0, 0x3EF0  # ο μετρητής γύρων, κάτω από το PROBE
I_DOME_S, I_DOME_L, I_CORR, I_SOLAR = 0, 2, 3, 4
R_FACTORY = 4
DS_ACTIVE = 2
DOME_TBL, STRUCT_TBL = 0x7500 - 0x4000, 0x7B00 - 0x4000   # μέσα στην τράπεζα 6
# Το χειρότερο φάντασμα: θόλος L κόκκινος σε όλα του τα tiles. Πλαίσιο 32 x 128
# σε τέσσερα ορθογώνια (κεφαλίδα 4 το καθένα, πάνω και κάτω πάχους 2) και 64
# σημάδια 2x4. Από το βήμα 41 το GH_LOG είναι ΑΚΡΙΒΩΣ αυτό (src/const.asm).
RED_L = 2 * (4 + 32 * 2) + 2 * (4 + 128 - 4) + 64 * (4 + 2 * 4)


def check(ok, msg):
    print(("OK " if ok else "ΛΑΘΟΣ ") + msg)
    if not ok:
        FAIL.append(msg)


def site_mark(pic, hx, hy, cam):
    """Είναι στην εικόνα το σήμα «περιμένει» στο κέντρο (hx, hy) μιας δομής,
    σε μισά tiles; Οπως το γράφει το st_mark (src/figure.asm): ένα byte αριστερά
    και τρεις γραμμές πάνω από το κέντρο, με τα bytes του tools/pack.py."""
    import pack
    n = pack.MARK_W * pack.MARK_H
    want = pack.marks()[n:2 * n]
    x0 = 2 * hx - 4 * cam[0] - pack.MARK_W // 2
    y0 = 8 * hy - 16 * cam[1] - pack.MARK_H // 2
    return bytes(pic[(y0 + j) * 80 + x0 + i]
                 for j in range(pack.MARK_H) for i in range(pack.MARK_W)) == want


class Game:
    """Το ΚΑΝΟΝΙΚΟ binary, με τα εργαλεία που χρειάζεται η δοκιμή."""

    def __init__(self, sym, g):
        self.sym, self.g = sym, g
        self.top = sym["MAIN_LOOP"]
        self.m = B.boot(sym, T.COLONY)
        for k in (3, 4):                     # μέταλλο και βιοπλαστικό: 999
            self.m.poke(g + 2 * k, 0xE7)
            self.m.poke(g + 2 * k + 1, 0x03)
        self.iters, self.t, self.inw, self.last = [], 0, False, None
        self.pend = []                       # rv_pend σε κάθε τέλος γύρου
        self.hook()
        for line in open(os.path.join(ROOT, "build", "layout.asm"),
                         encoding="utf-8"):
            if line.startswith("PAGE2_TOP"):
                self.ghbuf = int(line.split("#")[1].split()[0], 16)

    def bank(self, n):
        return cpc._lib.cpcemu_ram_ptr(self.m._h, n)

    def hook(self):
        """Ο ΓΥΡΟΣ ΜΕΤΡΙΕΤΑΙ ΜΕΣΑ ΣΤΟ ΠΑΙΧΝΙΔΙ. Το `jp main_loop` στο τέλος του
        βρόχου πηγαίνει πρώτα εδώ: το rv_pend του γύρου που μόλις τελείωσε στο
        RING[μετρητής & 15], και ΜΕΤΑ ο μετρητής γύρων στο CNT — αλλιώς ένα
        δείγμα ανάμεσα στα δύο διαβάζει θέση που δεν γράφτηκε ακόμη. Ο μετρητής
        είναι ένα byte, για να μη διαβαστεί ποτέ μισογραμμένος· ανάμεσα σε δύο
        δείγματα κλείνουν το πολύ δύο γύροι.

        Ως το βήμα 62 ο γύρος ήταν «το PC μέσα στην αναμονή του vsync», με δείγμα
        κάθε 100 us. Μια αναμονή κάτω από 100 us δεν φαινόταν, και δύο γύροι
        μετρούσαν για έναν: όταν η δρομολόγηση έγινε φθηνότερη, ένας γύρος του
        test_link έκλεινε λίγο πριν από το vsync και η διαγώνιος «έβγαλε δύο
        σειρές σε έναν γύρο» που ήταν στην πραγματικότητα δύο. Ούτε πυκνότερο
        δείγμα το λύνει, η αναμονή μπορεί να είναι όσο μικρή θέλει. 23 bytes
        κώδικα, ~27 µs ανά γύρο."""
        m, top, ut, rv = self.m, self.top, self.sym["UI_TICK"], self.sym["RV_PEND"]
        k = next(k for k in range(256) if list(m.read_ram(top + k, 6)) ==
                 [0xCD, ut & 255, ut >> 8, 0xC3, top & 255, top >> 8])
        assert (RING & 255) + 15 < 256
        m.write_ram(HOOK, bytes([
            0x3A, CNT & 255, CNT >> 8,          # ld a,(CNT)
            0x3C, 0x6F,                         # inc a · ld l,a
            0xE6, 0x0F, 0xC6, RING & 255,       # and 15 · add a,RING
            0x5F, 0x16, RING >> 8,              # ld e,a · ld d,RING >> 8
            0x3A, rv & 255, rv >> 8, 0x12,      # ld a,(rv_pend) · ld (de),a
            0x7D, 0x32, CNT & 255, CNT >> 8,    # ld a,l · ld (CNT),a
            0xC3, top & 255, top >> 8]))        # jp main_loop
        m.poke(CNT, 0)
        m.write_ram(top + k + 4, bytes([HOOK & 255, HOOK >> 8]))
        self.cnt = 0

    def count(self):
        return self.m.peek(CNT)

    # --- το ρολόι ---------------------------------------------------------
    def run(self, us, until=None, step=100):
        """Τρέχει με βήμα `step` και κρατά τη διάρκεια ΚΑΘΕ γύρου του βρόχου.

        Γύρος = από το ένα τέλος του βρόχου ως το επόμενο, όπως τα μετρά το
        hook. Ενα ρολόι για όλη τη δοκιμή, ώστε κανένας γύρος να μη χάνεται
        στις ραφές· όσοι γύροι έτρεξαν ΕΞΩ από το run (run_frames, probe) δεν
        μετρούν, και ο επόμενος δεν έχει διάρκεια.
        """
        m, end, after = self.m, self.t + us, None
        if self.count() != self.cnt:
            self.cnt, self.last = self.count(), None
        while self.t < end:
            m.run_us(step)
            self.t += step
            c = self.count()
            while self.cnt != c:             # και δύο γύροι σε ένα βήμα
                self.cnt = (self.cnt + 1) & 0xFF
                if self.last is not None:
                    self.iters.append(self.t - self.last)
                self.last = self.t
                self.pend.append(m.peek(RING + (self.cnt & 15)))
            if until and until():
                until, after = None, len(self.iters)
            # ΤΡΕΙΣ ΓΥΡΟΙ ΑΚΟΜΗ μετά τη συνθήκη, όχι χρόνος. Η συνθήκη αληθεύει
            # ΜΕΣΑ στον γύρο που μετράμε (ο τροχός γράφει DS_ACTIVE πριν
            # ζωγραφίσει ο βρόχος), και μια ουρά 400 ms έκοβε ακριβώς τον γύρο
            # των 919 ms: ο παλιός κώδικας περνούσε τον έλεγχο με «40 ms».
            if after is not None and len(self.iters) >= after + 3:
                break
        return self

    def settle(self):
        """Ως να κλείσουν τρεις γύροι ακόμη — όσο κι αν κρατά ο τρέχων."""
        return self.run(5_000_000, until=lambda: True)

    def worst(self):
        w = max(self.iters, default=0)
        self.iters = []
        return w / 1000

    # --- κώδικας του παιχνιδιού, από την αναμονή του vsync ----------------
    def probe(self, names, frames=100):
        m = self.m
        for _ in range(40000):
            if self.top <= m.pc < self.top + 13:
                break
            m.run_us(50)
        # di πρώτα (βήμα 83): αλλιώς η διακοπή των λωρίδων τρέχει πάνω στο jr $,
        # και ο έλεγχος του PC την πετυχαίνει μέσα της. Το ei το ξανακάνει ο βρόχος.
        code = [0xF3]
        for n in names:
            code += [0xCD, self.sym[n] & 0xFF, self.sym[n] >> 8]
        m.run_code(PROBE, bytes(code + [0x18, 0xFE]), frames=frames)
        # Το PC του εξομοιωτή δείχνει ένα byte πριν από την εντολή που θα
        # εκτελεστεί (το ίδιο περιθώριο κρατά και το tools/agents.py).
        assert PROBE + len(code) - 1 <= m.pc <= PROBE + len(code) + 1, (
            f"το {names} δεν τελείωσε: pc={m.pc:#06x}")
        m.set_pc(self.top)
        self.last, self.inw = None, False

    def full(self):
        """Πλήρης σχεδίαση, με το φάντασμα όπως θα το έβαζε το ui_show."""
        self.probe(["UI_HIDE", "OB_CLIP_FULL", "VIEW_DRAW", "UI_SHOW"])

    def camera(self, tx, ty):
        self.m.poke(self.sym["CAM_TX"], tx & 0xFF)
        self.m.poke(self.sym["CAM_TY"], ty & 0xFF)
        self.full()                          # το view_draw κάνει και view_cam

    # --- η οθόνη -----------------------------------------------------------
    def addr(self, x, y):
        off = self.m.peek(self.sym["CAM_OFF"]) | (self.m.peek(self.sym["CAM_OFF"] + 1) << 8)
        return (y & 7) * 0x800 + (((y >> 3) * 80 + x + 2 * off) & 0x7FF)

    def play(self):
        scr = self.bank(3)
        return bytes(scr[self.addr(x, y)] for y in range(160) for x in range(80))

    def canary(self, x=0, y=0):
        scr, a = self.bank(3), self.addr(x, y)
        scr[a] ^= 0xA5
        return a, scr[a]

    def alive(self, c):
        return self.bank(3)[c[0]] == c[1]

    # --- η προσομοίωση ---------------------------------------------------
    def still(self):
        """Σταματά την προσομοίωση και αδειάζει τη λίστα. Επιστρέφει τον
        διακόπτη για να ξαναρχίσει."""
        on = [self.m.peek(self.sym["WH_ON"] + k) for k in range(16)]
        for k in range(16):
            self.m.poke(self.sym["WH_ON"] + k, 0)
        for _ in range(200):
            if self.m.peek(self.sym["DIRTY_NUM"]) == 0:
                break
            self.m.run_frames(1)
        self.m.run_frames(2)
        return on

    def go(self, on):
        for k, v in enumerate(on):
            self.m.poke(self.sym["WH_ON"] + k, v)

    def truth(self):
        """(τρέχουσα εικόνα, πλήρης σχεδίαση), με σταματημένη προσομοίωση."""
        on = self.still()
        pic = self.play()
        self.full()
        ref = self.play()
        self.go(on)
        return pic, ref

    def under(self):
        """(με το φάντασμα, κάτω από αυτό, πλήρης σχεδίαση χωρίς αυτό, ξανά με
        αυτό), με σταματημένη προσομοίωση. Το «κάτω» είναι ό,τι γράφει πίσω το
        ui_hide από το αρχείο: ένα αρχείο που δεν ξέρει μια αλλαγή κάτω από το
        φάντασμα το δείχνει εδώ (βήμα 109). Και ό,τι η πλήρης σχεδίαση του
        truth() θα έσβηνε."""
        on = self.still()
        pic = self.play()
        self.probe(["UI_HIDE"])
        bare = self.play()
        self.probe(["OB_CLIP_FULL", "VIEW_DRAW"])
        ref = self.play()
        self.probe(["UI_SHOW"])
        again = self.play()
        self.go(on)
        return pic, bare, ref, again

    def state(self, node):
        b6 = self.bank(6)
        off = DOME_TBL + node * 24 if node < 64 else STRUCT_TBL + (node - 64) * 8
        return b6[off + 4], b6[off + 5]         # κατάσταση, ακεραιότητα

    # --- ο παίκτης -------------------------------------------------------
    def stick(self, mask, frames=4):
        self.m.joystick(mask)
        self.run(frames * 20_000)
        self.m.joystick(0)
        self.run(10 * 20_000)


def interior(x0, y0):
    """Τα bytes του εικονιδίου και των οκτώ μηχανών ενός θόλου L με πλαίσιο
    στο (x0, y0) της οθόνης — ό,τι αλλάζει όταν τελειώνει (dh_built).

    Από τους ΙΔΙΟΥΣ πίνακες που διαβάζει το object.asm: machine_slots (x, y
    μέσα στο πλαίσιο), interior_ofs (το εικονίδιο, από το κέντρο).
    """
    from sprites import load_map, load_bin
    smap, blob = load_map(), load_bin()

    def tab(n):
        t = smap[n]
        return blob[t.off:t.off + t.size]
    slots, ofs = tab("machine_slots")[32:48], tab("interior_ofs")[4:6]
    rects = [(slots[k], slots[k + 1], 6, 22) for k in range(0, 16, 2)]  # MACH_W/H
    sx = lambda v: v - 256 if v > 127 else v
    rects.append((16 + sx(ofs[0]), 64 + sx(ofs[1]), 10, 20))           # ICON_L
    return {(y0 + y + j) * 80 + x0 + x + i
            for x, y, w, h in rects for j in range(h) for i in range(w)}


def shape(pic, ref, skip=()):
    """(ίδια;, περιγραφή της διαφοράς). Ως το βήμα 42 επέτρεπε το «γνωστό σχήμα»
    του §15 — ως τέσσερα tiles με ως 8 bytes σε δύο στήλες, μια θέση δακτυλίου
    που άδειασε. Η αιτία ήταν το έδαφος κάτω από τη θέση (dhs_vacate) και
    διορθώθηκε· μια ανοχή χωρίς αιτία θα έκρυβε το επόμενο σφάλμα."""
    bad = [(i % 80, i // 80) for i, (a, b) in enumerate(zip(pic, ref))
           if a != b and i not in skip]
    tiles = {}
    for x, y in bad:
        tiles.setdefault((x // 4, y // 16), []).append((x, y))
    worst = max((len(v) for v in tiles.values()), default=0)
    span = max((max(x for x, _ in v) - min(x for x, _ in v) + 1
                for v in tiles.values()), default=0)
    ok = not bad
    return ok, f"{len(bad)} bytes σε {len(tiles)} tiles (χειρότερο {worst}, {span} στήλες)"


def finish(G, node):
    """Περιμένει τη στιγμή της ολοκλήρωσης με το ρολόι να τρέχει."""
    for _ in range(8000):
        if G.state(node)[1] >= 192:          # μία επίσκεψη πριν από το 255
            break
        G.m.run_frames(1)
    G.last, G.inw, G.iters = None, False, []
    G.run(20_000_000, until=lambda: G.state(node)[0] == DS_ACTIVE)
    return G.state(node)[0] == DS_ACTIVE


def dome(sym, g, cut_ghost=False, short=False):
    """Θόλος L εργοστάσιο: τοποθέτηση και ολοκλήρωση, με το κόκκινο φάντασμα
    να κάθεται από πάνω του σε όλη τη διάρκεια — εκεί το αφήνει το uip_after.

    Με `short` το όριο του αρχείου στο ghr_put κατεβαίνει ένα byte, και
    επιστρέφεται μόνο πόσο γέμισε: το τελευταίο σημάδι δεν πρέπει να χωρά."""
    G = Game(sym, g)
    if short:
        # ld hl,4 - όριο (βήμα 58: το κρατούμενο είναι η απάντηση) — όριο ένα
        # byte πιο κάτω σημαίνει σταθερά ένα πιο πάνω
        at, want = sym["GHR_PUT"], (0x10000 + 4 - (G.ghbuf + RED_L + 1)) & 0xFFFF
        for k in range(48):
            if (G.m.peek(at + k) == 0x21 and G.m.peek(at + k + 1) == want & 0xFF
                    and G.m.peek(at + k + 2) == want >> 8):
                G.m.poke(at + k + 1, (want + 1) & 0xFF)
                G.m.poke(at + k + 2, (want + 1) >> 8)
                break
        else:
            raise SystemExit(f"το ghr_put δεν ξεκινά από #{want:04X}: το GH_LOG "
                             f"δεν είναι {RED_L}")
    tx, ty = B.clear_spots(8, 1, dome=True)[0]
    G.camera(tx - 6, ty - 1)                 # ο θόλος στις στήλες 6-13
    G.inside = interior(6 * 4, 1 * 16)
    B.build(G.m, sym, I_DOME_L, g + 6, at=(2 * tx + 8, 2 * ty + 8),
            room=R_FACTORY, place=False)
    # Οι σειρές των διαγωνίων του (βήμα 85), όσες φαίνονται από την κάμερα.
    import test_link as TL, reach
    plan = B.live_plan(G.m, sym, I_DOME_L, (2 * tx + 8, 2 * ty + 8))
    crow = sum(len(TL.rows((reach.sb(c[1][0]), reach.sb(c[1][1])), c[1][2], c[3],
                           (tx - 6, ty - 1))[0])
               for c in plan["corridors"])
    if cut_ghost:
        G.m.poke(sym["DT_GHOST"], 0xC9)      # ret: το φάντασμα δεν σηκώνεται

    c = G.canary()
    metal = G.m.peek(g + 6)
    G.run(40_000)
    G.iters, G.pend = [], []
    G.m.set_joystick_type(1)
    G.m.joystick(JOY_FIRE)
    G.run(80_000)
    G.m.joystick(0)
    G.m.set_joystick_type(0)
    # ΩΣ ΝΑ ΞΑΝΑΜΠΕΙ ΤΟ ΦΑΝΤΑΣΜΑ: η εμφάνιση είναι οκτώ γύροι, και ο
    # μακρύτερος είναι ο τελευταίος, όπου το ui_late ξαναζωγραφίζει το
    # κόκκινο φάντασμα.
    G.run(4_000_000, until=lambda: G.m.peek(sym["RV_PEND"]) == 0
          and G.m.peek(sym["UI_OWED"]) == 0)
    node = G.m.peek(sym["BD_NODE"])
    # ΟΙ ΟΚΤΩ ΜΗΧΑΝΕΣ, πάνω στο εργοτάξιο. Ως το βήμα 44 τις έγραφε το
    # bd_commit· από το 45 ο θόλος μπαίνει άδειος και τις διαλέγει ο παίκτης
    # (src/fit.asm, tests/test_fit.py). Γράφονται εδώ όπως θα τις έγραφε ο
    # εξοπλισμός πάνω στο εργοτάξιο — χωρίς DK_MACH — γιατί χωρίς αυτές η
    # ολοκλήρωση ζωγραφίζει μόνο το εικονίδιο, και ο χειρότερος γύρος της και
    # το αρνητικό του φαντάσματος θα μετρούσαν το μισό.
    b6 = G.bank(6)
    for s_, mach in enumerate((1, 2, 3, 5, 7, 1, 2, 3)):
        b6[DOME_TBL + node * 24 + 8 + s_] = mach
        b6[DOME_TBL + node * 24 + 16 + s_] = 200
    bands = sum(1 for a, b in zip(G.pend, G.pend[1:]) if b < a)
    most = max((a - b for a, b in zip(G.pend, G.pend[1:])), default=0)
    placed = G.worst()
    if short:
        return (G.m.peek(sym["GH_PTR"]) | (G.m.peek(sym["GH_PTR"] + 1) << 8)) - G.ghbuf
    if not cut_ghost:
        check(G.m.peek(g + 6) != metal and G.state(node)[0] == 1,
              f"ο θόλος L μπήκε στο {(tx, ty)}: κόμβος {node}, εργοτάξιο")
        check(G.alive(c), "η τοποθέτηση ΔΕΝ ξαναζωγράφισε το κάδρο: το "
                          "κανάρινι ζει")
        # ΜΕΤΡΗΜΕΝΟ: 80 ms το FIRE, 60-80 κάθε σειρά, 140 ο γύρος όπου
        # ξαναμπαίνει το φάντασμα. Ηταν ΕΝΑΣ γύρος 998 ms (βήμα 34: 859 με
        # το ξανασχέδιο μόνο του αποτυπώματος).
        check(placed < 200, f"ο χειρότερος γύρος της τοποθέτησης ήταν "
                            f"{placed:.0f} ms (όριο 200· ήταν 998)")
        check(bands == 8 + crow and most == 1,
              f"ο θόλος εμφανίστηκε σε {bands} γύρους, το πολύ {most} σειρά "
              f"ανά γύρο (§6.9: μία σειρά tiles ανά γύρο, οκτώ για τον L και "
              f"{crow} για τις διαγώνιους των {len(plan['corridors'])} διαδρόμων του)")
        gp = G.m.peek(sym["GH_PTR"]) | (G.m.peek(sym["GH_PTR"] + 1) << 8)
        # ΟΛΟΚΛΗΡΟ: το αρχείο είναι ακριβώς όσο αυτό το φάντασμα (βήμα 41), και
        # ό,τι δεν χωρά απλώς δεν ζωγραφίζεται — ένα σημάδι λιγότερο θα ήταν
        # 12 bytes λιγότερα εδώ, και τίποτε άλλο δεν θα το έλεγε.
        check(gp - G.ghbuf == RED_L and G.m.peek(sym["UI_STATE"]) == 2,
              f"και μετά το φάντασμα ξαναμπήκε κόκκινο ΟΛΟΚΛΗΡΟ: {gp - G.ghbuf} "
              f"bytes στο αρχείο (πλαίσιο + 64 σημάδια = {RED_L}), κατάσταση PLACE")
        pic, ref = G.truth()
        ok, how = shape(pic, ref, skip={0})
        check(ok, f"και η οθόνη είναι η αλήθεια: το αποτύπωμα ζωγραφίστηκε "
                  f"όλο — {how}")

    c = G.canary()
    done = finish(G, node)
    built = G.worst()
    if cut_ghost:
        return G, node
    check(done, f"ο θόλος τελείωσε (κατάσταση {G.state(node)[0]})")
    check(G.alive(c), "η ολοκλήρωση ΔΕΝ ξαναζωγράφισε το κάδρο: το κανάρινι ζει")
    # ΜΕΤΡΗΜΕΝΟ: 120 ms, από τα οποία τα 60 είναι οι δύο ανταλλαγές του
    # φαντάσματος (gh_swap) — το κόκκινο φάντασμα του L είναι 1.160 bytes
    # αρχείου (βήμα 35· στο 34 ήταν κομμένο στα 1.600 και έβγαινε 100). Ηταν
    # 919 ms. Το όριο αφήνει χώρο για ένα HUD που πέφτει στον ίδιο γύρο (46 ms
    # κρύο, §9.2).
    check(built < 200, f"και ο χειρότερος γύρος ήταν {built:.0f} ms "
                       f"(όριο 200· ήταν 919 με την πλήρη σχεδίαση)")
    # Η ΣΥΓΚΡΙΣΗ ΠΕΡΙΜΕΝΕΙ ΤΟ ghost_moves: η πλήρης σχεδίαση ξαναχτίζει και
    # το αρχείο του φαντάσματος, οπότε θα έσβηνε ακριβώς το ίχνος που ψάχνουμε.
    return G, node


def twice(G, sym, node):
    """ΔΥΟ εγγραφές κάτω από το φάντασμα, στο ΙΔΙΟ τικ της λίστας.

    Το dt_ghost σηκώνει το φάντασμα με ανταλλαγή, και η ανταλλαγή είναι η
    αντίστροφη του εαυτού της: αν η δεύτερη εγγραφή την ξανάκανε, το φάντασμα
    θα ξανάπεφτε πριν ζωγραφίσει ο δεύτερος χειριστής και θα έμενε σηκωμένο στο
    τέλος. Το βρήκε το test_save (το πλαίσιο του κέρσορα χανόταν μετά το
    φόρτωμα)· εδώ στήνεται επίτηδες, για να μην εξαρτάται από το πού έτυχε να
    περπατήσει ένας άποικος.
    """
    code = [0xF3]                            # di: βλ. το probe
    for _ in range(2):
        code += [0x3E, 2, 0x06, node, 0x0E, 0,          # DK_ICON, θόλος, 0
                 0xCD, sym["DIRTY_PUSH"] & 0xFF, sym["DIRTY_PUSH"] >> 8]
    for _ in range(40000):
        if G.top <= G.m.pc < G.top + 13:
            break
        G.m.run_us(50)
    G.m.run_code(PROBE, bytes(code + [0x18, 0xFE]), frames=1)
    G.m.set_pc(G.top)
    G.last, G.inw = None, False
    G.m.run_frames(10)


def ghost_moves(G, sym):
    """Το φάντασμα φεύγει από τον θόλο: η αναίρεσή του πρέπει να γράψει πίσω
    το ΤΕΛΕΙΩΜΕΝΟ εσωτερικό, όχι το άδειο εργοτάξιο."""
    G.m.set_joystick_type(1)
    G.stick(0x20)                            # PLACE -> MENU: ui_hide
    G.m.set_joystick_type(0)
    pic, ref = G.truth()
    bad = sum(1 for i in G.inside if pic[i] != ref[i])
    ok, how = shape(pic, ref, skip=G.inside | {0})     # 0: το κανάρινι
    return bad, ok, how


def solar(sym, g, cut=None):
    """Μια δομή: η τοποθέτηση αλλάζει 3x3 tiles, και από το βήμα 109 η
    ολοκλήρωση άλλα 3x3, γύρω από το κέντρο: σβήνει το σήμα του εργοταξίου.

    Ο κέρσορας μένει πάνω στη δομή (uip_after), και το σήμα είναι κάτω από
    το κόκκινο φάντασμά του: οι έλεγχοι κοιτάζουν κάτω από αυτό (Game.under).

    Με `cut` = "mark" το st_mark γίνεται `ret`, με "built" το st_redraw (το
    DK_TILE του st_built), και με "ghost" το dt_ghost_rect του dh_tile τρία
    NOP. Τότε επιστρέφει μόνο (σήμα μετά την τοποθέτηση, σήμα μετά την
    ολοκλήρωση, η οθόνη είναι η αλήθεια μετά την ολοκλήρωση, η διαφορά)."""
    G = Game(sym, g)
    tx, ty = B.clear_spots(3, 1)[0]
    cam, hx, hy = (tx - 8, ty - 3), 2 * tx + 3, 2 * ty + 3
    G.camera(*cam)
    B.build(G.m, sym, I_SOLAR, g + 6, at=(hx, hy), place=False)
    if cut == "ghost":
        at, gr = sym["DH_TILE"], sym["DT_GHOST_RECT"]
        k = next(k for k in range(40) if list(G.m.read_ram(at + k, 3)) ==
                 [0xCD, gr & 255, gr >> 8])
        G.m.write_ram(at + k, bytes(3))
    elif cut:
        G.m.poke(sym["ST_MARK" if cut == "mark" else "ST_REDRAW"], 0xC9)
    c = G.canary()
    G.run(40_000)
    G.iters = []
    G.m.set_joystick_type(1)
    G.stick(JOY_FIRE)
    G.m.set_joystick_type(0)
    G.settle()
    node = G.m.peek(sym["BD_NODE"])
    placed = G.worst()
    alive = G.alive(c)
    pic, bare, ref, again = G.under()
    marked = site_mark(bare, hx, hy, cam)
    if not cut:
        check(node >= 64 and alive,
              f"ο ηλιακός μπήκε (κόμβος {node}) και το κανάρινι ζει "
              f"({placed:.0f} ms ο χειρότερος γύρος)")
        check(marked and G.state(node)[0] == 1 and pic != bare,
              "και είναι εργοτάξιο με το σήμα της αναμονής στο κέντρο του, κάτω "
              "από το κόκκινο φάντασμα του κέρσορα (βήμα 109)")
        ok, how = shape(bare, ref, skip={0})
        ok2, how2 = shape(pic, again, skip={0})
        check(ok and ok2, f"και η οθόνη είναι η αλήθεια: κάτω από το φάντασμα "
                          f"{how}, με αυτό {how2}")

    c = G.canary()
    done = finish(G, node)
    built = G.worst()
    alive = G.alive(c)
    pic, bare, ref, again = G.under()
    gone = not site_mark(bare, hx, hy, cam)
    ok, how = shape(bare, ref, skip={0})
    ok2, how2 = shape(pic, again, skip={0})
    if cut:
        return marked, not gone, ok and ok2, how
    # ΜΕΤΡΗΜΕΝΟ: ως το βήμα 108 40 ms, το HUD — η ολοκλήρωση μιας δομής δεν
    # ζωγράφιζε τίποτα. Ηταν 360 με την πλήρη σχεδίαση. Από το 109 τα 3x3 tiles
    # γύρω από το κέντρο, με τον ηλιακό από πάνω.
    check(done and alive and built < 100,
          f"η ολοκλήρωση του ηλιακού ζωγράφισε μόνο γύρω από το κέντρο του: "
          f"κανάρινι {'ζει' if alive else 'ΝΕΚΡΟ'}, χειρότερος γύρος "
          f"{built:.0f} ms (όριο 100· ήταν 360)")
    check(gone, "και το σήμα του εργοταξίου έσβησε")
    check(ok and ok2, f"και η οθόνη είναι η αλήθεια: κάτω από το φάντασμα "
                      f"{how}, με αυτό {how2}")

    # --- η λίστα ξεχειλίζει: η υπόσχεση του dirty_push -------------------
    # «Μια χαμένη αλλαγή αφήνει ψέμα στην οθόνη για πάντα· μια πλήρης
    # επανασχεδίαση κοστίζει, αλλά λέει αλήθεια.» Η σημαία σηκωνόταν από το
    # βήμα 6a και κανείς δεν τη διάβαζε.
    c = G.canary()
    G.m.poke(sym["DIRTY_OVER"], 1)
    G.run(2_000_000)
    check(G.m.peek(sym["DIRTY_OVER"]) == 0 and not G.alive(c),
          f"το ξεχείλισμα φέρνει πλήρη σχεδίαση: σημαία "
          f"{G.m.peek(sym['DIRTY_OVER'])}, κανάρινι "
          f"{'ζει' if G.alive(c) else 'σβήστηκε'}")


def crater(sym, g, cut=False):
    """ΚΡΑΤΗΡΑΣ ΚΑΤΩ ΑΠΟ ΤΟ ΠΛΑΙΣΙΟ ΤΟΥ ΚΕΡΣΟΡΑ (βήμα 109). Το dh_tile
    ζωγράφιζε χωρίς να σηκώσει το φάντασμα, από το βήμα 38: το αρχείο κρατούσε
    το έδαφος που ήταν πριν, και το ui_hide το έγραφε πίσω πάνω στον κρατήρα. Ο
    κέρσορας ενός ηλιακού σε ελεύθερο έδαφος, και ο κρατήρας στο tile της γωνίας
    του, κάτω από το πλαίσιο. Με `cut` το dt_ghost_rect του dh_tile τρία NOP.
    Επιστρέφει (ίδια;, περιγραφή) κάτω από το φάντασμα."""
    G = Game(sym, g)
    tx, ty = B.clear_spots(3, 1)[0]
    G.camera(tx - 8, ty - 3)
    B.build(G.m, sym, I_SOLAR, g + 6, at=(2 * tx + 3, 2 * ty + 3), place=False)
    if cut:
        at, gr = sym["DH_TILE"], sym["DT_GHOST_RECT"]
        k = next(k for k in range(40) if list(G.m.read_ram(at + k, 3)) ==
                 [0xCD, gr & 255, gr >> 8])
        G.m.write_ram(at + k, bytes(3))
    G.run(400_000)
    on = G.still()
    b4 = G.bank(4)
    v = b4[W.index(tx, ty)]
    b4[W.index(tx, ty)] = (v & 0xC0) | W.CRATER   # όπως το mt_ground
    dp = sym["DIRTY_PUSH"]
    G.m.run_code(PROBE, bytes([0xF3, 0x3E, 4, 0x06, tx & 255, 0x0E, ty & 255,
                               0xCD, dp & 255, dp >> 8, 0x18, 0xFE]), frames=1)
    G.m.set_pc(G.top)
    G.last, G.inw = None, False
    G.go(on)
    G.run(200_000)
    pic, bare, ref, again = G.under()
    return shape(bare, ref)


def corridor(sym, g, dx=8, dy=0):
    """Δύο θόλοι S και ένας διάδρομος ανάμεσά τους: ο B στο (+dx, +dy) tiles.

    Το cr_redraw ξαναζωγραφίζει ΜΟΝΟ το περίγραμμα των tiles που πατά η
    διαδρομή, και οι πόρτες έρχονται από τη λίστα αλλαγών.
    """
    pl = B.plane()
    ok = {W.GROUND, W.DUST, W.FOUNDATION}
    spot = None
    wide, high = dx + 4, dy + 4
    for r in range(12, 30):
        for ty in range(-r, r + 1):
            for tx in range(-r, r + 1):
                if spot or max(abs(tx), abs(ty)) != r:
                    continue
                if any(max(abs(tx + i), abs(ty + j)) < 12
                       for i in range(wide) for j in range(high)):
                    continue
                if all(W.cls_of(pl[W.index(tx + i, ty + j)]) in ok
                       for i in range(-1, wide + 1) for j in range(-1, high + 1)):
                    spot = (tx, ty)
    tx, ty = spot
    G = Game(sym, g)
    B.no_link(G.m, sym)                      # ο διάδρομος ζητιέται με το χέρι
    G.camera(tx + wide // 2 - 10, ty + high // 2 - 5)
    B.build(G.m, sym, I_DOME_S, g + 6, at=(2 * tx + 4, 2 * ty + 4), room=R_FACTORY)
    B.build(G.m, sym, I_DOME_S, g + 6, at=(2 * (tx + dx) + 4, 2 * (ty + dy) + 4),
            room=R_FACTORY)

    def tap(key):
        G.m.key_down(key)
        G.m.run_frames(5)
        G.m.key_up(key)
        G.m.run_frames(8)

    G.m.set_joystick_type(1)
    G.stick(0x20)
    G.stick(0x20)
    G.m.set_joystick_type(0)
    tap(KEY_SPACE)                      # -> ACT (βήμα 80)
    tap(KEY_SPACE)                      # -> MENU: το BUILD είναι πρώτο
    for _ in range(14):
        if G.m.peek(sym["UI_SEL"]) == I_CORR:
            break
        tap(KEY_RIGHT)
    G.m.key_up("\x01")
    G.m.set_joystick_type(1)
    G.stick(JOY_FIRE)                        # -> LINK
    G.m.poke(sym["CUR_HX"], (2 * tx + 4) & 0xFF)
    G.m.poke(sym["CUR_HY"], (2 * ty + 4) & 0xFF)
    G.stick(JOY_FIRE)                        # η αφετηρία
    G.m.poke(sym["CUR_HX"], (2 * (tx + dx) + 4) & 0xFF)
    G.m.poke(sym["CUR_HY"], (2 * (ty + dy) + 4) & 0xFF)
    c = G.canary()
    metal = G.m.peek(g + 6) | (G.m.peek(g + 7) << 8)
    G.run(40_000)
    G.iters = []                             # μόνο το FIRE που χτίζει
    G.stick(JOY_FIRE)                        # ο προορισμός: χτίζει
    G.m.set_joystick_type(0)
    G.settle()
    paid = metal - (G.m.peek(g + 6) | (G.m.peek(g + 7) << 8))
    laid = G.worst()
    kind = "με στροφή" if dy else "ευθύς"
    check(paid > 0 and G.alive(c),
          f"ο διάδρομος {kind} μπήκε (μέταλλο -{paid}) και το κανάρινι ζει "
          f"({laid:.0f} ms ο χειρότερος γύρος)")
    pic, ref = G.truth()
    ok, how = shape(pic, ref, skip={0})
    bad = sum(1 for i, (a, b) in enumerate(zip(pic, ref)) if a != b and i)
    check(bad == 0, f"και η οθόνη είναι η αλήθεια — διάδρομος ΚΑΙ οι δύο "
                    f"πόρτες, byte προς byte: {how}")
    return G


def main():
    sym, g = T.build()
    G, node = dome(sym, g)
    twice(G, sym, node)
    bad, ok, how = ghost_moves(G, sym)
    check(bad == 0, f"το φάντασμα φεύγει από τον τελειωμένο θόλο και το "
                    f"εσωτερικό είναι ακριβώς η πλήρης σχεδίαση: εικονίδιο και "
                    f"μηχανές, {len(G.inside)} bytes, {bad} λάθος")
    check(ok, f"και έξω από αυτό, τίποτα: {how}")
    got = dome(sym, g, short=True)
    check(got == RED_L - 12,
          f"ΑΡΝΗΤΙΚΟ: με αρχείο ένα byte μικρότερο το τελευταίο σημάδι δεν "
          f"μπαίνει — {got} bytes ({RED_L} - 12)")
    G, node = dome(sym, g, cut_ghost=True)
    bad, ok, how = ghost_moves(G, sym)
    check(bad > 0, f"ΑΡΝΗΤΙΚΟ: με το dt_ghost κομμένο, το φάντασμα που φεύγει "
                   f"γράφει το εργοτάξιο πάνω στις μηχανές — {bad} λάθος bytes "
                   f"στο εσωτερικό")
    solar(sym, g)
    marked, stays, ok, _ = solar(sym, g, cut="mark")
    check(not marked and ok,
          "ΑΡΝΗΤΙΚΟ: με το st_mark κομμένο το εργοτάξιο του ηλιακού δεν έχει "
          "σήμα — και η πλήρης σχεδίαση δεν το λέει, γιατί δεν το έχει ούτε αυτή")
    marked, stays, ok, _ = solar(sym, g, cut="built")
    check(marked and stays and not ok,
          f"ΑΡΝΗΤΙΚΟ: χωρίς το DK_TILE του st_built το σήμα μένει στον "
          f"τελειωμένο ηλιακό ({'μένει' if stays else 'έσβησε'}), και ο έλεγχος "
          f"ΑΛΗΘΕΙΑ το πιάνει")
    # Το κόκκινο σημάδι του κέρσορα στο tile του κέντρου πέφτει πάνω σε μέρος
    # του σήματος: αυτό το μέρος γράφει πίσω το ui_hide.
    marked, stays, ok, how = solar(sym, g, cut="ghost")
    check(marked and not ok,
          f"ΑΡΝΗΤΙΚΟ: χωρίς το dt_ghost_rect του dh_tile το αρχείο του "
          f"φαντάσματος κρατά το εργοτάξιο, και το ui_hide το γράφει πίσω — "
          f"κάτω από το φάντασμα {how}")
    ok, how = crater(sym, g)
    check(ok, f"κρατήρας κάτω από το πλαίσιο του κέρσορα: κάτω από το φάντασμα "
              f"η οθόνη είναι η πλήρης σχεδίαση — {how}")
    ok, how = crater(sym, g, cut=True)
    check(not ok, f"ΑΡΝΗΤΙΚΟ: χωρίς το dt_ghost_rect του dh_tile το ui_hide γράφει "
                  f"πίσω το έδαφος πάνω στον κρατήρα (ως το βήμα 108) — {how}")
    # Ο ΕΥΘΥΣ ΕΔΩ. Οι διάδρομοι με διαγώνιο και με στροφή, ανάμεσα σε θόλους
    # που έβαλε ο παίκτης, έχουν δική τους δοκιμή από το βήμα 36
    # (tests/test_link.py): ως τότε δεν χτίζονταν καθόλου.
    corridor(sym, g)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
