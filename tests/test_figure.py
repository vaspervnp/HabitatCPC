#!/usr/bin/env python3
"""Οι άποικοι έξω (βήμα 89, DESIGN §8.4, §8.5, §6.3), στο main.sna.

Ως το βήμα 88 ένας άποικος φαινόταν μόνο στις θέσεις του δακτυλίου ενός θόλου·
στο σκάφος, σε δομή και στο έδαφος ήταν αόρατος. Τώρα:

  ΣΤΕΚΕΤΑΙ σε δομή     στη θέση του: οι 0, 4, 2, 6 στη σειρά ακριβώς κάτω από
                       το αποτύπωμα, στις στήλες cx-1, cx, cx-2, cx+1· οι 1,
                       5, 3, 7 στη σειρά ακριβώς από πάνω του
  ΠΕΡΠΑΤΑ έξω          από το μπροστινό σημείο του ενός κόμβου (cx, cy + μισό
                       ύψος) ως του άλλου, a + (b - a) * progress / 256, στη
                       στήλη της θέσης 0
  αλλιώς               πουθενά: σε θόλο (ο δακτύλιος), στον σωλήνα, νεκρός

Το μοντέλο εδώ είναι γραμμένο από αυτή την πρόζα, όχι από τον κώδικα.

  ΑΡΧΗ      η λίστα είναι οι τέσσερις άποικοι, στη σειρά κάτω από το σκάφος,
            με τη φιγούρα του ρόλου τους· και στην οθόνη: κάθε αδιαφανές
            pixel της φιγούρας (fig_gfx) είναι εκεί.
  ΔΡΟΜΟΣ    ένα ηλιακό τέσσερα tiles ανατολικά: οι μεταφορείς πάνε και
            έρχονται. Σε κάθε δείγμα, με τη λίστα αλλαγών άδεια: η λίστα είναι
            το μοντέλο για ΟΛΟΥΣ τους πράκτορες, κάθε φιγούρα φαίνεται, και η
            οθόνη είναι byte προς byte η πλήρης σχεδίαση (ένα ΑΝΤΙΓΡΑΦΟ της
            μηχανής την κάνει, ώστε η λίστα της κανονικής να μην ξαναχτίζεται
            ποτέ: ό,τι μαζεύεται βήμα με βήμα, μένει). Τουλάχιστον τέσσερα
            διαφορετικά κελιά στον δρόμο.
  ΘΟΛΟΣ     ο πρώτος θόλος: στο εργοτάξιο οι φιγούρες φεύγουν από τη λίστα και
            μπαίνουν στον δακτύλιο, στο τέλος όλοι βγαίνουν στο σκάφος (lk_out)
            — με τους ίδιους ελέγχους σε κάθε δείγμα.
  ΜΕΤΕΩΡΙΤΗΣ  ένα tile αλλάζει κάτω από κάποιον που περπατά σε ελεύθερο
            έδαφος: η φιγούρα μένει, και η οθόνη είναι η πλήρης σχεδίαση.
  ΚΟΣΤΟΣ    κάθε dh_agent, για κάθε φιγούρα έξω με την κάμερα πάνω της,
            κοστίζει όσο χρεώνει ή λιγότερο: το DK_AGENT του dirty_cost, συν
            ό,τι πρόσθεσε ο ίδιος στο dt_spent (το παλιό κελί ανά έδαφος, το
            νέο, 24 us ανά εγγραφή που κοιτά το fg_draw, κάθε φιγούρα που
            ζωγραφίζει). Πέντε περιπτώσεις — σβήνει και ζωγραφίζει, μόνο
            σβήνει, μόνο ζωγραφίζει, τίποτα, αλλάζει έξω από το κάδρο — και η
            καθεμία ξανά με τη λίστα σχεδόν γεμάτη: ο περιπατητής τελευταίος
            στο cpir, 60 εγγραφές στη στήλη του, δύο φιγούρες πάνω στο κελί του.

Αρνητικά, με το snapshot πειραγμένο: χωρίς το fg_draw στο ob_draw_all (η ΑΡΧΗ
δεν έχει φιγούρες στην οθόνη), χωρίς το σημάδι του em_trans (η λίστα μένει
πίσω από το μοντέλο), χωρίς το σβήσιμο του παλιού κελιού (ίχνη), χωρίς το
fg_paint (το νέο κελί άδειο), χωρίς το fg_build στο view_draw (η ΑΡΧΗ χωρίς
λίστα), με το dh_tile χωρίς φιγούρες (ο ΜΕΤΕΩΡΙΤΗΣ), και χωρίς τη χρέωση της
σάρωσης στο fg_draw (το ΚΟΣΤΟΣ με γεμάτη λίστα).
"""
import ctypes, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import test_outside as TO                                # noqa: E402
import balance as B                                      # noqa: E402
import cpc                                               # noqa: E402

SHIP = 64
SOLAR_FAR = (1, 15)      # επτάμισι tiles νότια: ο δρόμος περνά από ελεύθερο έδαφος
SOLAR_AT = (9, 1)        # ηλιακό l, 3x3: ΠΕΡΙΤΤΟ κέντρο (§3.4). Το (8, 0) του test_supply
                         # το κουμπώνει μόνο το poke του B.build, και εκεί η σχεδίαση
                         # της τοποθέτησης κόβει μισό tile (ίδιο και στο βήμα 88)
DX = [-1, -2, 0, 1]                                      # θέση >> 1 -> στήλη


def dk_us():
    """Η χρέωση του DK_AGENT στον πίνακα dirty_cost (src/dirty.asm, 9η)."""
    src = open(os.path.join(ROOT, "src", "dirty.asm"), encoding="utf-8").read()
    body = src[src.index("\ndirty_cost:"):].split("\n")[1:]
    vals = [ln.split()[1] for ln in body if ln.split()[:1] == ["dw"]]
    return int(vals[8])                  # οι επόμενες (βήμα 101) λένε και DIRTY_BUD


DK_US = dk_us()
PROBE, FLAG, STACK = 0x3E00, 0x3EFF, 0x3EFC
FAIL = []


def check(ok, msg):
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ ") + msg)
    if not ok:
        FAIL.append(msg)


def sb(v):
    return v - 256 if v > 127 else v


class G:
    """Μια μηχανή με το main.sna, και ό,τι διαβάζει η δοκιμή."""

    def __init__(self, sym, g, patch=(), m=None):
        self.sym, self.g, self.L = sym, g, TO.layout()
        self.m = m or B.boot(sym, TG.SNA)
        for at, v in patch:
            self.m.poke(at, v)

    def bank(self, n):
        p = cpc._lib.cpcemu_ram_ptr(self.m._h, n)
        return (ctypes.c_ubyte * 0x4000).from_address(ctypes.addressof(p.contents))

    def b6(self, addr):
        return self.bank(6)[addr - 0x4000]

    def ag(self, i, off):
        return self.b6(self.L["G_agent_fields"] + off + i)

    # --- το μοντέλο, από την πρόζα ------------------------------------------
    def front(self, node):
        """(cx, cy + μισό ύψος, μισό ύψος) σε μισά tiles."""
        if node < 64:
            r = self.L["G_dome_tbl"] + 24 * node
            half = 4 + 2 * self.b6(r + 2)
        else:
            r = self.L["G_struct_tbl"] + 8 * (node - 64)
            k, z = self.b6(r + 2), self.b6(r + 3)
            half = self.m.peek(self.L["G_struct_dims"] + (k * 4 + z) * 2 + 1) // 16
        cx, cy = sb(self.b6(r)), sb(self.b6(r + 1))
        return cx, cy + half, half

    @staticmethod
    def lerp(a, b, p):
        d = b - a
        s = abs(d) * p >> 8
        return a + (s if d >= 0 else -s)

    def want(self, i):
        f = self.ag(i, 0)
        if not f & 1:
            return None
        fig = self.m.peek(self.sym["ROLE_FIG"] + (self.ag(i, 128) & 7))
        edge, node = self.ag(i, 640), self.ag(i, 256)
        if edge == 255:
            slot = self.ag(i, 384)
            if slot > 7 or node < 64:
                return None
            cx, fy, half = self.front(node)
            y = fy if slot % 2 == 0 else fy - 2 * half - 1
            return (cx + DX[slot >> 1], y, fig)
        if f & 2:
            return None
        to = self.m.peek(self.L["G_node_adj"] + 8 * node + edge)
        p = self.ag(i, 768)
        ax, ay, _ = self.front(node)
        bx, by, _ = self.front(to)
        return (self.lerp(ax, bx, p) - 1, self.lerp(ay, by, p), fig)

    def model(self):
        return {i: w for i in range(128) if (w := self.want(i)) is not None}

    def figs(self):
        """Η λίστα, με τη σειρά της: [(πράκτορας, x, y, φιγούρα)]."""
        n, base = self.m.peek(self.sym["FG_N"]), self.L["G_fig_list"]
        return [(self.b6(base + 192 + k), sb(self.b6(base + k) ^ 128),
                 sb(self.b6(base + 64 + k) ^ 128), self.b6(base + 128 + k)) for k in range(n)]

    # --- η οθόνη ------------------------------------------------------------
    def cam(self):
        m, s = self.m, self.sym
        return 2 * (m.peek(s["CAM_OFF"]) | m.peek(s["CAM_OFF"] + 1) << 8)

    def play(self):
        scr, cam = self.bank(3), self.cam()
        return bytes(scr[(y & 7) * 0x800 + (((y >> 3) * 80 + x + cam) & 0x7FF)]
                     for y in range(160) for x in range(80))

    def shown(self, figs, play):
        """Οι φιγούρες που θα έπρεπε να φαίνονται ολόκληρες και δεν φαίνονται:
        κάθε αδιαφανές bit της (fig_gfx) στην οθόνη. Οχι κάτω από το πλαίσιο
        του κέρσορα, και όχι όπου στο ίδιο κελί ζωγραφίζεται μετά άλλη."""
        m, s = self.m, self.sym
        tx, ty = sb(m.peek(s["CAM_TX"])), sb(m.peek(s["CAM_TY"]))
        gx0, gx1, gy0, gy1 = (m.peek(s["GH_BBX"]), m.peek(s["GH_BBX"] + 1),
                              m.peek(s["GH_BBY"]), m.peek(s["GH_BBY"] + 1))
        gfx = self.L["G_fig_gfx"]
        bad, n = [], 0
        for k, (a, x, y, f) in enumerate(figs):
            if any((x2, y2) == (x, y) for _, x2, y2, _ in figs[k + 1:]):
                continue
            bx, ly = 2 * (x - 2 * tx), 8 * (y - 2 * ty)
            if not (0 <= bx <= 78 and 0 <= ly <= 152):
                continue
            if bx < gx1 and gx0 < bx + 2 and ly < gy1 and gy0 < ly + 8:
                continue
            n += 1
            for r in range(8):
                for c in range(2):
                    mk = self.b6(gfx + (f - 1) * 32 + r * 4 + c * 2)
                    d = self.b6(gfx + (f - 1) * 32 + r * 4 + c * 2 + 1)
                    if play[(ly + r) * 80 + bx + c] & ~mk & 0xFF != d & ~mk & 0xFF:
                        bad.append((a, x, y))
                        break
                else:
                    continue
                break
        return n, bad

    # --- δείγμα ----------------------------------------------------------------
    def drain(self):
        """Παύση, και η λίστα αλλαγών άδεια."""
        m, s = self.m, self.sym
        m.poke(s["UI_SPD"], 0)
        for _ in range(200):
            m.run_frames(1)
            if m.peek(s["DIRTY_NUM"]) == 0:
                break
        m.run_frames(2)

    def clone(self):
        """Μια δεύτερη μηχανή με την ίδια μνήμη: εκεί τρέχουν οι probes."""
        c = cpc.CPC()
        c.run_frames(5)
        assert c.quickload(TG.SNA, start=False)
        for n in range(8):
            dst, src = cpc._lib.cpcemu_ram_ptr(c._h, n), cpc._lib.cpcemu_ram_ptr(self.m._h, n)
            ctypes.memmove(ctypes.addressof(dst.contents), ctypes.addressof(src.contents), 0x4000)
        return G(self.sym, self.g, m=c)

    def probe(self, body):
        """di, δική του στοίβα, Mode 0 χωρίς ROM (hw_mode0 — το αντίγραφο
        ξεκινά από την κεφαλίδα του snapshot), το body, σημαία. -> us από την
        αρχή του body ως τη σημαία."""
        m = self.m
        code = [0xF3, 0x31, STACK & 255, STACK >> 8] + self.call("HW_MODE0") + body + \
               [0x3E, 0x5A, 0x32, FLAG & 255, FLAG >> 8, 0x18, 0xFE]
        m.write_ram(PROBE, bytes(code))
        m.poke(FLAG, 0)
        m.set_pc(PROBE)
        us = 0
        while m.peek(FLAG) != 0x5A:
            m.run_us(2)
            us += 2
            assert us < 5_000_000, "η probe δεν τελείωσε"
        return us

    def call(self, name):
        a = self.sym[name]
        return [0xCD, a & 255, a >> 8]

    def full(self):
        """Η πλήρης σχεδίαση, όπως τη ζητά το dirty_over στον βρόχο."""
        self.probe(self.call("DIRTY_RESET") + self.call("UI_HIDE")
                   + self.call("VIEW_DRAW") + self.call("UI_SHOW"))
        return self.play()

    def sample(self, tag):
        """Η πρώτη διαφορά από την πρόζα, ή None. -> (λάθος, κελιά δρόμου)."""
        self.drain()
        figs, want = self.figs(), self.model()
        got = {a: (x, y, f) for a, x, y, f in figs}
        if len(got) != len(figs):
            return f"{tag}: ο ίδιος πράκτορας δύο φορές στη λίστα: {figs}", set()
        if got != want:
            diff = {a: (got.get(a), want.get(a)) for a in set(got) | set(want)
                    if got.get(a) != want.get(a)}
            return f"{tag}: λίστα != μοντέλο: {diff}", set()
        play = self.play()
        n, bad = self.shown(figs, play)
        if bad:
            return f"{tag}: δεν φαίνονται {bad} (από {n})", set()
        # Η ΠΛΗΡΗΣ ΣΧΕΔΙΑΣΗ ΣΕ ΑΝΤΙΓΡΑΦΟ, και με τη λίστα του άδεια και όλους
        # σημειωμένους: το fg_build πρέπει να τη φτιάξει από την αρχή, ίδια, και
        # να σβήσει τα σημάδια — αλλιώς κανείς δεν θα ξανασπρωχνόταν ποτέ.
        c = self.clone()
        c.m.poke(self.sym["FG_N"], 0)
        mk = self.L["G_node_occ"] + 128 - 0x4000
        for i in range(128):
            c.bank(6)[mk + i] = 1
        other = c.full()
        cl = {a: (x, y, f) for a, x, y, f in c.figs()}
        if cl != want or any(c.bank(6)[mk + i] for i in range(128)):
            return (f"{tag}: η πλήρης σχεδίαση δεν ξαναχτίζει τη λίστα: {sorted(cl.items())}, "
                    f"σημάδια {[i for i in range(128) if c.bank(6)[mk + i]][:8]}"), set()
        if other != play:
            d = [k for k in range(len(play)) if play[k] != other[k]]
            return (f"{tag}: η οθόνη δεν είναι η πλήρης σχεδίαση: {len(d)} bytes, "
                    f"πρώτο ({d[0] % 80}, {d[0] // 80})"), set()
        self.m.poke(self.sym["UI_SPD"], 1)
        road = {(x, y) for a, x, y, f in figs if self.ag(a, 640) != 255}
        return None, road


def look(m):
    """Πίσω στην ήρεμη κατάσταση μετά από μια τοποθέτηση (B.build)."""
    m.set_joystick_type(1)
    for _ in range(2):
        m.joystick(0x20)
        m.run_frames(4)
        m.joystick(0)
        m.run_frames(10)
    m.set_joystick_type(0)


def scenario(sym, g, patch=(), quiet=False):
    """ΑΡΧΗ και ΔΡΟΜΟΣ. Η πρώτη διαφορά από την πρόζα, ή None."""
    w = G(sym, g, patch)
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    # --- ΑΡΧΗ
    figs = w.figs()
    want = {a: (x, y, f) for a, (x, y, f) in w.model().items()}
    roles = [w.ag(i, 128) for i in range(4)]
    exp = {}
    for i in range(4):
        slot = w.ag(i, 384)
        exp[i] = (DX[slot >> 1], 2, w.m.peek(sym["ROLE_FIG"] + roles[i]))
    if {a: (x, y, f) for a, x, y, f in figs} != exp or want != exp:
        return f"ΑΡΧΗ: λίστα {figs}, μοντέλο {want}, η πρόζα λέει {exp}"
    n, bad = w.shown(figs, w.play())
    if n != 4 or bad:
        return f"ΑΡΧΗ: στην οθόνη {n} από 4 ολόκληρες, λείπουν {bad}"
    say(f"ΑΡΧΗ: {sorted((x, f) for a, x, y, f in figs)} στη σειρά y = 2, στην οθόνη")
    # --- ΔΡΟΜΟΣ
    B.build(w.m, sym, 4, g + 6, at=SOLAR_AT, fit=False)
    look(w.m)
    road, t = set(), 0
    for k in range(36):
        w.m.run_frames(9 if k % 3 else 14)
        why, r = w.sample(f"ΔΡΟΜΟΣ, δείγμα {k}")
        if why:
            return why
        road |= r
    if len(road) < 4:
        return f"ΔΡΟΜΟΣ: μόνο {sorted(road)} στον δρόμο — η κίνηση δεν φάνηκε"
    say(f"ΔΡΟΜΟΣ: 36 δείγματα, λίστα = μοντέλο και οθόνη = πλήρης σχεδίαση σε όλα· "
        f"κελιά στον δρόμο {sorted(road)}")
    return None


def dome(sym, g, quiet=False):
    """ΘΟΛΟΣ. Η πρώτη διαφορά από την πρόζα, ή None."""
    w = G(sym, g)
    B.build(w.m, sym, 0, g + 6, at=TO.DOME_AT, room=0, fit=False)
    look(w.m)
    ring = seen_out = 0
    for k in range(60):
        w.m.run_frames(40)
        why, r = w.sample(f"ΘΟΛΟΣ, δείγμα {k}")
        if why:
            return why
        at = [w.ag(i, 256) for i in range(4) if w.ag(i, 640) == 255]
        ring += sum(1 for n in at if n < 64)
        if w.b6(w.L["G_dome_tbl"] + 4) == 2:          # DS_ACTIVE
            seen_out += 1
            if seen_out >= 3:
                break
    if not ring or seen_out < 3:
        return (f"ΘΟΛΟΣ: {ring} φορές κάποιος στον δακτύλιο, ο θόλος "
                f"{'τελείωσε' if seen_out else 'δεν τελείωσε'}")
    if not quiet:
        print(f"    ΘΟΛΟΣ: {k + 1} δείγματα ως το τέλος, {ring} φορές κάποιος στον "
              f"δακτύλιο του εργοταξίου")
    return None


def ground(w, x, y):
    """Τι είναι κάτω από το κελί (x, y): 0 = τα 3x3 tiles γύρω του χωρίς
    κατοχή από αντικείμενο (§3.5: bit 4· το μονοπάτι, κατοχή 2, είναι έδαφος),
    1 = κάποιος γείτονας, 2 = το ίδιο το tile του."""
    tx, ty = x >> 1, y >> 1
    pl = w.bank(4)
    occ = lambda dx, dy: pl[((ty + dy + 64) << 7) | (tx + dx + 64)] & 0x10
    if occ(0, 0):
        return 2
    return int(any(occ(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)))


def free(w, x, y):
    return ground(w, x, y) == 0


def meteor(sym, g, patch=(), quiet=False):
    """ΜΕΤΕΩΡΙΤΗΣ: αλλάζει το tile κάτω από κάποιον που περπατά σε ελεύθερο
    έδαφος (DK_TILE, σε αντίγραφο). Το dh_tile ξαναστρώνει τα 3x3 και, χωρίς
    κατοχή, ως το βήμα 89 δεν ζωγράφιζε τίποτα από πάνω: η φιγούρα χανόταν."""
    w = G(sym, g, patch)
    B.build(w.m, sym, 4, g + 6, at=SOLAR_FAR, fit=False)
    look(w.m)
    for _ in range(150):
        w.m.run_frames(5)
        w.drain()
        hit = [(a, x, y) for a, x, y, f in w.figs()
               if w.ag(a, 640) != 255 and free(w, x, y)]
        if hit:
            break
        w.m.poke(sym["UI_SPD"], 1)
    else:
        return "ΜΕΤΕΩΡΙΤΗΣ: κανείς δεν περπάτησε σε ελεύθερο έδαφος"
    a, x, y = hit[0]
    c = w.clone()
    c.probe([0x3E, 4, 0x01, (y >> 1) & 255, (x >> 1) & 255]       # DK_TILE, C = ty, B = tx
            + c.call("DIRTY_PUSH") + c.call("DIRTY_TICK") + c.call("DIRTY_TICK"))
    if c.m.peek(sym["DIRTY_NUM"]):
        return "ΜΕΤΕΩΡΙΤΗΣ: η λίστα αλλαγών δεν άδειασε"
    play = c.play()
    n, bad = c.shown(c.figs(), play)
    if bad:
        return f"ΜΕΤΕΩΡΙΤΗΣ: μετά το tile ({x >> 1}, {y >> 1}) δεν φαίνονται {bad}"
    if c.clone().full() != play:
        return f"ΜΕΤΕΩΡΙΤΗΣ: μετά το tile ({x >> 1}, {y >> 1}) η οθόνη δεν είναι η πλήρης σχεδίαση"
    if not quiet:
        print(f"    ΜΕΤΕΩΡΙΤΗΣ: το tile ({x >> 1}, {y >> 1}) κάτω από τον {a}, στο ({x}, {y}): "
              f"η φιγούρα μένει, η οθόνη = η πλήρης σχεδίαση")
    return None


FG_PAD = 62
RAW = []                                  # (είδος, γεμάτη, έδαφος, us, χρέωση)


def pad(c, a, x, y):
    """Η λίστα του c σχεδόν γεμάτη: FG_PAD ψεύτικες εγγραφές πρώτες, η του a
    τελευταία — το cpir του dh_agent τις περνά όλες. Οι 60 στη στήλη του, σε
    άλλες σειρές του κάδρου (η ακριβότερη σάρωση: x μέσα, y έξω), και δύο
    ΠΑΝΩ στο κελί του, που ζωγραφίζονται κάθε φορά που ζωγραφίζεται εκείνο."""
    s, fl = c.sym, c.L["G_fig_list"] - 0x4000
    b6, figs = c.bank(6), c.figs()
    k = [e[0] for e in figs].index(a)
    real = [b6[fl + col + k] for col in range(0, 256, 64)]
    ty = sb(c.m.peek(s["CAM_TY"]))
    for j in range(FG_PAD):
        if j < 2:
            yy = y
        else:
            yy = 2 * ty + (y - 2 * ty + 3 + j % 15) % 20
        for col, v in zip(range(0, 256, 64), ((x + 128) & 255, (yy + 128) & 255,
                                             1 + j % 8, 127 - j if 127 - j != a else 0)):
            b6[fl + col + j] = v
    for col, v in zip(range(0, 256, 64), real):
        b6[fl + col + FG_PAD] = v
    c.m.poke(s["FG_N"], FG_PAD + 1)


def cost(sym, g, patch=(), out=None):
    """ΚΟΣΤΟΣ: dh_agent σε αντίγραφο, για κάθε φιγούρα έξω, με την κάμερα
    κεντραρισμένη πάνω της και την πλήρη σχεδίαση (ο δρόμος ως το ηλιακό δεν
    χωρά σε ένα κάδρο). Μόνο με καθαρό ευρετήριο αντικειμένων (ob_idx = 0):
    μετά από μια τοποθέτηση το πρώτο ob_draw_all ξαναχτίζει το ευρετήριο
    (~11 ms), όποιος χειριστής κι αν το καλέσει — το πληρώνει κι ένα άδειασμα
    θέσης (dhs_vacate), δεν είναι κόστος της φιγούρας."""
    check_ = out or check
    w = G(sym, g, patch)
    B.build(w.m, sym, 4, g + 6, at=SOLAR_FAR, fit=False)
    look(w.m)
    kinds = ("σβήνει και ζωγραφίζει", "μόνο σβήνει", "μόνο ζωγραφίζει", "τίποτα",
             "αλλάζει έξω από το κάδρο")
    under = {0: [], 1: [], 2: []}           # μόνο σβήνει, ανά ground()
    meas = {k: [] for k in kinds}
    padded = {k: [] for k in kinds}         # τα ίδια, με τη λίστα σχεδόν γεμάτη
    L, spent, fl = w.L, sym["DT_SPENT"], w.L["G_fig_list"] - 0x4000
    for _ in range(160):
        w.m.run_frames(7)
        w.drain()
        if w.m.peek(sym["OB_IDX"]):
            w.m.poke(sym["UI_SPD"], 1)
            continue
        for a, x, y, f in w.figs():
            walks = w.ag(a, 640) != 255
            if walks and w.ag(a, 768) >= 150:
                continue
            v = w.clone()                   # η κάμερα πάνω του
            v.m.poke(sym["CAM_TX"], min(max((x >> 1) - 10, -64), 44) & 255)
            v.m.poke(sym["CAM_TY"], min(max((y >> 1) - 5, -64), 54) & 255)
            v.full()
            if v.m.peek(sym["OB_IDX"]):
                continue
            for full, kind in [(f, k) for f in (False, True) for k in kinds]:
                if not walks and kind != "μόνο σβήνει":
                    continue
                c = v.clone()
                b6 = c.bank(6)
                if full:
                    pad(c, a, x, y)
                k = [e[0] for e in c.figs()].index(a)
                if kind in ("σβήνει και ζωγραφίζει", "αλλάζει έξω από το κάδρο"):
                    b6[L["G_agent_fields"] + 768 + a - 0x4000] += 100     # progress
                if kind == "μόνο σβήνει" and walks:
                    b6[L["G_agent_fields"] + a - 0x4000] |= 2              # F_INDOORS
                if kind == "μόνο σβήνει" and not walks:
                    b6[L["G_agent_fields"] + 384 + a - 0x4000] |= 8        # NO_SLOT
                if kind == "μόνο ζωγραφίζει":                # «δεν ήταν»: έξω από τη λίστα
                    n = c.m.peek(sym["FG_N"]) - 1
                    for col in range(0, 256, 64):
                        b6[fl + col + k] = b6[fl + col + n]
                    c.m.poke(sym["FG_N"], n)
                if kind == "αλλάζει έξω από το κάδρο":
                    c.m.poke(sym["CAM_TX"], (c.m.peek(sym["CAM_TX"]) + 40) & 255)
                us = c.probe([0x21, 0, 0, 0x22, spent & 255, spent >> 8,
                              0x3E, a, 0x32, sym["DT_A"] & 255, sym["DT_A"] >> 8]
                             + c.call("DH_AGENT")) - 34    # probe, hw_mode0, σημαία
                charged = DK_US + (c.m.peek(spent) | c.m.peek(spent + 1) << 8)
                meas[kind].append((us, charged))
                RAW.append((kind, full, ground(w, x, y), us, charged))
                if full:
                    padded[kind].append((us, charged))
                if kind == "μόνο σβήνει":
                    under[ground(w, x, y)].append((us, charged))
        w.m.poke(sym["UI_SPD"], 1)
        if all(len(v) >= 12 for v in meas.values()) and all(len(under[k]) >= 6 for k in (0, 1)):
            break
    for kind, v in meas.items():
        worst = max(v, key=lambda x: x[0] - x[1]) if v else (None, None)
        check_(len(v) >= 12 and all(x[0] <= x[1] for x in v),
              f"ΚΟΣΤΟΣ, {kind}: {len(v)} μετρήσεις, χειρότερη {worst[0]} us για "
              f"χρέωση {worst[1]} (μέση {sum(x[0] for x in v) // max(1, len(v))} us)")
    worst = max((x for v in padded.values() for x in v), key=lambda x: x[0], default=(0, 0))
    check_(all(len(v) >= 6 for v in padded.values()),
          f"ΚΟΣΤΟΣ με τη λίστα σχεδόν γεμάτη ({FG_PAD + 1} εγγραφές, ο περιπατητής "
          f"τελευταίος, δύο φιγούρες στο κελί του): {sum(map(len, padded.values()))} "
          f"μετρήσεις μέσα στα παραπάνω, ως {worst[0]} us για χρέωση {worst[1]}")
    for k, name in ((0, "σε ελεύθερο έδαφος"), (1, "δίπλα σε κτίσμα"), (2, "πάνω σε κτίσμα")):
        v = under[k]
        check_((len(v) >= 6 or k == 2) and all(x[0] <= x[1] for x in v),
              f"ΚΟΣΤΟΣ, σβήσιμο {name}: {len(v)} μετρήσεις, ως "
              f"{max((x[0] for x in v), default='-')} us για χρέωση "
              f"{sorted(set(x[1] for x in v))}")
    return meas, under, padded


def main():
    sym, g = TG.build()
    why = scenario(sym, g)
    check(why is None, why or "ΑΡΧΗ και ΔΡΟΜΟΣ: όπως λέει η πρόζα")
    why = dome(sym, g)
    check(why is None, why or "ΘΟΛΟΣ: όπως λέει η πρόζα")
    why = meteor(sym, g)
    check(why is None, why or "ΜΕΤΕΩΡΙΤΗΣ: όπως λέει η πρόζα")
    cost(sym, g)

    # --- αρνητικά ---
    m = B.boot(sym, TG.SNA)

    def find(at, pat, n=64):
        return next((at + k for k in range(n)
                     if list(m.read_ram(at + k, len(pat))) == pat), None)

    w = lambda a: [a & 255, a >> 8]
    fd = find(sym["OB_DRAW_ALL"], [0xCD] + w(sym["FG_DRAW"]), 80)
    vd = find(sym["VIEW_DRAW"], [0xCD] + w(sym["FG_BUILD"]), 4)
    er = find(sym["DHA_ERASE"], [0xCD] + w(sym["FG_ERASE"]), 4)
    mk = sym["EMS_MARK"] - 2                                 # jr nz,ems_nx του em_trans
    for label, patch in (
            ("χωρίς το fg_draw στο ob_draw_all", fd and [(fd + k, 0) for k in range(3)]),
            ("χωρίς το σημάδι του em_trans",
             m.peek(mk) == 0x20 and [(mk, 0x18)]),                  # jr nz -> jr
            ("χωρίς το σβήσιμο του παλιού κελιού", er and [(er + k, 0) for k in range(3)]),
            ("χωρίς το fg_paint", [(sym["FG_PAINT"], 0xC9)]),
            ("χωρίς το fg_build στο view_draw",
             vd and [(vd + 1, sym["OB_TOUCH"] & 255), (vd + 2, sym["OB_TOUCH"] >> 8)])):
        if not patch:
            check(False, f"δεν βρέθηκε πού να πειραχτεί για «{label}»")
            continue
        why = scenario(sym, g, patch, quiet=True)
        check(why is not None, f"ΑΡΝΗΤΙΚΟ: με «{label}» αποτυγχάνει ({(why or '')[:110]})")
    # Χωρίς τη χρέωση της σάρωσης στο fg_draw: με τη λίστα γεμάτη, 1,5 ms ανά
    # σάρωση που δεν τα χρεώνει κανείς.
    sc = find(sym["FG_DRAW"], [0xCD] + w(sym["DHV_CHARGE"]), 40)
    bad = []
    if sc:
        cost(sym, g, [(sc + k, 0) for k in range(3)], out=lambda ok, msg: bad.append(not ok))
    check(sc and any(bad), "ΑΡΝΗΤΙΚΟ: χωρίς τη χρέωση της σάρωσης στο fg_draw, το ΚΟΣΤΟΣ "
                           f"αποτυγχάνει ({sum(bad)} από {len(bad)} έλεγχοι)")
    why = meteor(sym, g, [(sym["FG_DRAW1"], 0xC9)], quiet=True)    # ret
    check(why is not None, f"ΑΡΝΗΤΙΚΟ: με το dh_tile χωρίς φιγούρες σε ελεύθερο έδαφος, ο "
                           f"ΜΕΤΕΩΡΙΤΗΣ αποτυγχάνει ({(why or '')[:100]})")

    if FAIL:
        print(f"\nΑΠΟΤΥΧΙΑ — {len(FAIL)}")
        return 1
    print("\nOK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
