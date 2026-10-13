#!/usr/bin/env python3
"""Οι άποικοι έξω (βήμα 89, DESIGN §8.4, §8.5, §6.3), στο main.sna.

Ως το βήμα 88 ένας άποικος φαινόταν μόνο στις θέσεις του δακτυλίου ενός θόλου·
στο σκάφος, σε δομή και στο έδαφος ήταν αόρατος. Τώρα:

  ΣΤΕΚΕΤΑΙ σε δομή     στη θέση του: οι 0, 4, 2, 6 στη σειρά ακριβώς κάτω από
                       το αποτύπωμα, στις στήλες cx-1, cx, cx-2, cx+1· οι 1,
                       5, 3, 7 στη σειρά ακριβώς από πάνω του
  ΠΕΡΠΑΤΑ έξω          από το μπροστινό σημείο του ενός κόμβου (cx, cy + μισό
                       ύψος) ως του άλλου, στη στήλη x - 1 (της θέσης 0) —
                       πάνω στα σκέλη του μονοπατιού, παρακάτω, στη στήλη x
                       (βήμα 118). Με τα δύο σημεία στην ίδια
                       στήλη ή σειρά, η ευθεία a + (b - a) * progress / 256,
                       όπως ως το βήμα 117. Αλλιώς ένα Γ (βήμα 118), πρώτα
                       κατά x — εκτός αν και οι δύο είναι δομές και η μία
                       κρέμεται από την άλλη (το LK_OWN της χωρίς τα bits 7
                       και 5 είναι η άλλη): τότε το Γ που κράτησε εκείνη, με
                       το bit 7 «πρώτα κατά y», περπατημένο από τη δική της
                       άκρη, ή ανάποδα από την άλλη. Στο πρώτο μισό του
                       progress το πρώτο σκέλος, a + (b - a) * 2p / 256, στο
                       δεύτερο το δεύτερο, με 2p - 256. ΠΟΙΟ Γ: δύο δομές,
                       και η γωνία του μονοπατιού — η στήλη του ενός κέντρου
                       και η σειρά του κέντρου του άλλου (πρώτα κατά x, του
                       από πού, cy = μπροστινό - μισό ύψος) — έξω και από τα
                       δύο αποτυπώματα (στήλες cx - w ως cx + w - 1, σειρές
                       cy - h ως cy + h - 1, w το μισό πλάτος, h το μισό
                       ύψος): με progress 0 στο μπροστινό σημείο, και μετά
                       το κομμάτι του Γ έξω από τα αποτυπώματα, από το
                       πρώτο κελί δίπλα στο αποτύπωμα από όπου φεύγει (ή,
                       πρώτα κατά y με τη γωνία πάνω του, το κελί από
                       πάνω του) ως τη γωνία, και από τη γωνία ως το κελί
                       δίπλα στο αποτύπωμα όπου φτάνει (ή, πρώτα κατά x, το
                       μπροστινό του σημείο αν φτάνει από κάτω, το κελί
                       πάνω του αν από πάνω). Με τη γωνία στη σειρά ενός
                       από τα δύο αποτυπώματα (πρώτα κατά x του πού, πρώτα
                       κατά y του από πού), μόνο το x, a + (b - a) *
                       progress / 256, στη σειρά ay· αλλιώς με τη γωνία στη
                       στήλη του άλλου, μόνο το y, στη στήλη ax. Με έναν
                       θόλο στη μία άκρη, ένα Γ πρώτα κατά x με γωνία τη
                       στήλη bx και τη σειρά ay
  αλλιώς               πουθενά: σε θόλο (ο δακτύλιος), στον σωλήνα, νεκρός

Το μοντέλο εδώ είναι γραμμένο από αυτή την πρόζα, όχι από τον κώδικα.

  ΑΡΧΗ      η λίστα είναι οι έξι άποικοι (τέσσερις ως το βήμα 120), στις
            θέσεις τους γύρω από το σκάφος — οι ζυγές στη σειρά από κάτω, οι
            μονές από πάνω — με τη φιγούρα του ρόλου τους· και στην οθόνη:
            κάθε αδιαφανές pixel της φιγούρας (fig_gfx) είναι εκεί.
  ΔΡΟΜΟΣ    ένα ηλιακό τέσσερα tiles ανατολικά: οι μεταφορείς πάνε και
            έρχονται. Σε κάθε δείγμα, με τη λίστα αλλαγών άδεια: η λίστα είναι
            το μοντέλο για ΟΛΟΥΣ τους πράκτορες, κάθε φιγούρα φαίνεται, και η
            οθόνη είναι byte προς byte η πλήρης σχεδίαση (ένα ΑΝΤΙΓΡΑΦΟ της
            μηχανής την κάνει, ώστε η λίστα της κανονικής να μην ξαναχτίζεται
            ποτέ: ό,τι μαζεύεται βήμα με βήμα, μένει). Τουλάχιστον τέσσερα
            διαφορετικά κελιά στον δρόμο.
  ΓΩΝΙΑ     (βήμα 118) σε αντίγραφο με το ηλιακό του ΔΡΟΜΟΥ χτισμένο: ένας
            πράκτορας που δεν υπάρχει (ο 127) σε μια ακμή, και το fg_want για
            ΚΑΘΕ progress 0-255 = το μοντέλο. Σκάφος προς ηλιακό και ανάποδα,
            με το Γ όπως χτίστηκε, κρατημένο πρώτα κατά x, πρώτα κατά y, ως
            σύνδεση εδάφους, από την άλλη πλευρά (το σκάφος κρέμεται από το
            ηλιακό), από έναν τρίτο, από κανέναν· σκάφος και θόλος (ένας θόλος
            0 μόνο στον πίνακα, όσο τον διαβάζει το fw_xy), με το LK_OWN του
            σκάφους «0, πρώτα κατά y». Ολα σε πέντε θέσεις του ηλιακού — εκεί
            που χτίστηκε, βορειοδυτικά (αρνητικές διαφορές), μία και δύο
            στήλες δίπλα στο σκάφος νότια, μία σειρά κάτω από το κέντρο του —
            και η ευθεία, με το ηλιακό και τον θόλο στη στήλη και στη σειρά
            του σκάφους: 102 ακμές. Και οι δομές είναι τετράγωνες (το fw_leg
            διαβάζει το μισό ύψος ως μισό πλάτος).
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
            Από το βήμα 105 το σβήσιμο χρεώνεται 1.200 σε ελεύθερο έδαφος και
            1.600 δίπλα σε κτίσμα (2.200 και 2.600 ως τότε): το tile του κελιού
            γράφεται κατευθείαν (fg_tile), όχι με το ob_put. Από το 106 το
            σβήσιμο σε ελεύθερο έδαφος είναι 1.100 και το ζωγράφισμα 500, και
            το fg_cell χρεώνει 8 ανά εγγραφή, 24 ανά εγγραφή με το ίδιο ux και
            300 ανά φιγούρα. ΤΑΒΑΝΙΑ: η μέση τιμή με κανονική λίστα — ένα βήμα
            ως 2.400 us σε ελεύθερο έδαφος (3.810 ως το 105) και ως 3.150 δίπλα
            σε κτίσμα (4.174), «τίποτα» ως 620 (682), «αλλάζει έξω από το
            κάδρο» ως 780 (840).
  ΚΕΛΙ      (βήμα 105) σε οκτώ κάμερες — πάνω στο ηλιακό, σε φλέβες, σε
            έδαφος κάθε κλάσης — σκουπίδια σε ένα κελί και το fg_erase του: η
            οθόνη είναι ξανά η πλήρης σχεδίαση, σε ελεύθερο έδαφος, δίπλα σε
            κτίσμα, πάνω σε κτίσμα και σε φλέβα. Και σε κάθε κάμερα, μετά, ένα
            άδειασμα θέσης (dhs_vacate) σε 2x8 που δεν αρχίζει σε σειρά
            χαρακτήρων: το call του dhv_rect_us ξαναγράφτηκε.
  ΣΤΟΙΒΕΣ   (βήμα 106) μια λίστα της δοκιμής (το fg_build γίνεται jp ob_touch,
            ώστε η πλήρης σχεδίαση να ζωγραφίσει αυτήν): κελιά σε οκτώ στήλες
            και τρεις σειρές, το ένα στα τρία με δύο φιγούρες, και κελιά γύρω
            από το ηλιακό. Σε καθένα, σκουπίδια και fg_erase, και μετά το
            κελί χωρίς φιγούρες και fg_paint: κάθε φορά η πλήρης σχεδίαση, με
            τις φιγούρες στη σειρά της λίστας — σε ελεύθερο έδαφος, δίπλα και
            πάνω σε κτίσμα, σε φλέβα.
  ΜΕΡΗ      (βήμα 106) το fg_erase και το fg_paint μόνα τους σε ΚΑΘΕ κελί δύο
            καμερών (πάνω στο ηλιακό, πάνω σε φλέβα), εκτός από το φάντασμα:
            χρεώνουν όσο κοστίζουν ή περισσότερο, ανά έδαφος. Ως το βήμα 105
            το σβήσιμο κόστιζε 1.564-1.900 us σε ελεύθερο έδαφος για χρέωση
            1.296, ως 3.360 σε φλέβα, και δίπλα σε κτίσμα ως 2.208 για 1.696:
            το κάλυπτε μόνο το περιθώριο του DK_AGENT.

Αρνητικά, με το snapshot πειραγμένο: χωρίς το fg_draw στο ob_draw_all (η ΑΡΧΗ
δεν έχει φιγούρες στην οθόνη), χωρίς το σημάδι του em_trans (η λίστα μένει
πίσω από το μοντέλο), χωρίς το σβήσιμο του παλιού κελιού (ίχνη), χωρίς το
fg_paint (το νέο κελί άδειο), χωρίς το fg_build στο view_draw (η ΑΡΧΗ χωρίς
λίστα), με το dh_tile χωρίς φιγούρες (ο ΜΕΤΕΩΡΙΤΗΣ), και χωρίς τη χρέωση της
σάρωσης στο fg_draw (το ΚΟΣΤΟΣ με γεμάτη λίστα). Από το βήμα 105: πάντα το πάνω
αριστερό τέταρτο του tile και χωρίς τη φλέβα (το ΚΕΛΙ), το call που δεν
ξαναγράφεται (το άδειασμα θέσης του ΚΕΛΙΟΥ), και χωρίς το fg_tile (το ΚΟΣΤΟΣ).
Από το βήμα 106: χωρίς τον έλεγχο του uy στο fg_cell, μόνο η πρώτη εγγραφή με το
ίδιο ux, χωρίς το fg_scr στο fg_paint (οι ΣΤΟΙΒΕΣ)· μία σειρά από τα 3x3 και η
φλέβα σε λάθος τέταρτο (το ΚΕΛΙ)· το τελευταίο βήμα του πολλαπλασιασμού του fg_want
χωρίς rra (ο ΔΡΟΜΟΣ)· η φλέβα που δεν χρεώνεται (τα ΜΕΡΗ)· χωρίς τη χρέωση όσων
έχουν το ίδιο ux, και πάντα το γενικό πέρασμα σε ελεύθερο έδαφος (το ΚΟΣΤΟΣ και
τα ταβάνια του). Από το βήμα 118, η ΓΩΝΙΑ: χωρίς το cpl (το Γ από την άλλη
άκρη), πάντα πρώτα κατά x, και με θόλο στη μία άκρη, το bit του εδάφους να
μετρά, χωρίς την ευθεία σε ίδια στήλη, χωρίς την ευθεία σε ίδια σειρά, και το
δεύτερο μισό του «πρώτα κατά x» χωρίς τη στήλη bx· η γωνία στη σειρά του
μπροστινού σημείου, χωρίς τον έλεγχο της στήλης, χωρίς τον έλεγχο της σειράς,
το πρώτο σκέλος από το κέντρο, με progress 0 ήδη στο μονοπάτι, πρώτα κατά y
πάνω από το P χωρίς το cpl, πρώτα κατά y ως τη στήλη του κέντρου του Q, το
σκέλος στη στήλη της θέσης 0, και η σειρά μέσα στο Q που κινεί μόνο το y.
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
        for at, v, *bk in patch:
            if bk:                       # (at, v, 6): ο κώδικας του τροχού (b6code)
                self.bank(bk[0])[at - 0x4000] = v
            else:
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
        fig = self.m.peek(self.sym["ROLE_FIG"] + (self.ag(i, 128) & 15))   # 8: ο εισβολέας
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
        x, y = self.walk(node, to, self.ag(i, 768))
        return (x, y, fig)                       # η στήλη: το walk

    def dims(self, n):
        """(μισό πλάτος, μισό ύψος) σε μισά tiles."""
        if n < 64:
            h = 4 + 2 * self.b6(self.L["G_dome_tbl"] + 24 * n + 2)
            return h, h
        r = self.L["G_struct_tbl"] + 8 * (n - 64)
        at = self.L["G_struct_dims"] + (self.b6(r + 2) * 4 + self.b6(r + 3)) * 2
        return self.m.peek(at) // 4, self.m.peek(at + 1) // 16

    def inside(self, n, x, y):
        (cx, fy, h), (w, _) = self.front(n), self.dims(n)
        return cx - w <= x < cx + w and fy - 2 * h <= y < fy

    def own(self, n):
        """LK_OWN + δομή (βήμα 102): η άκρη της σύνδεσής της, το bit 5 αν είναι
        σύνδεση εδάφους, το bit 7 «πρώτα κατά y»."""
        return self.m.peek(self.L["G_rt_nodes"] + 32 + n)

    def yfirst(self, a, b):
        if a >= 64 and b >= 64:
            if (self.own(b) & 0x5F) == a:
                return not (self.own(b) & 0x80)
            if (self.own(a) & 0x5F) == b:
                return bool(self.own(a) & 0x80)
        return False

    def walk(self, a, b, p):
        """Το κελί όποιου περπατά από το a στο b με αυτό το progress: στη στήλη
        της θέσης 0 (x - 1), εκτός από τα σκέλη του μονοπατιού."""
        x, y, on_path = self.walk_c(a, b, p)
        return (x if on_path else x - 1), y

    def walk_c(self, a, b, p):
        """Το σημείο (x, y), και αν είναι πάνω σε σκέλος του μονοπατιού."""
        ax, ay, ha = self.front(a)
        bx, by, hb = self.front(b)
        if ax == bx or ay == by:
            return self.lerp(ax, bx, p), self.lerp(ay, by, p), False
        q, lerp = 2 * p, self.lerp
        both = a >= 64 and b >= 64
        yf = both and self.yfirst(a, b)
        kx, ky = (ax, by - hb) if yf else (bx, ay - ha)        # η γωνία του μονοπατιού
        if both:
            # η γωνία στη σειρά ενός αποτυπώματος (ελέγχεται πρώτα: του πού
            # πρώτα κατά x, του από πού πρώτα κατά y): μόνο το x· στη στήλη του:
            # μόνο το y
            row, col = (a, b) if yf else (b, a)
            if self.inside(row, kx, ky):
                return lerp(ax, bx, p), ay, False
            if self.inside(col, kx, ky):
                return ax, lerp(ay, by, p), False
            if p == 0:
                return ax, ay, False
            wa, wb = self.dims(a)[0], self.dims(b)[0]
            if not yf:
                x0 = ax + wa if bx > ax else ax - wa - 1
                end = by if ky >= by else by - 2 * hb - 1
                return ((lerp(x0, bx, q), ky) if q < 256 else (bx, lerp(ky, end, q - 256))) + (True,)
            y0 = ay if ky >= ay else ay - 2 * ha - 1
            x1 = bx - wb - 1 if bx > ax else bx + wb
            return ((ax, lerp(y0, ky, q)) if q < 256 else (lerp(ax, x1, q - 256), ky)) + (True,)
        return ((lerp(ax, bx, q), ay) if q < 256 else (bx, lerp(ay, by, q - 256))) + (False,)

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
                    at = (gfx & 0xFF00) + 256 * (f & 1) + f   # ο κωδικός (βήμα 111)
                    mk = self.b6(at + r * 4 + c * 2)
                    d = self.b6(at + r * 4 + c * 2 + 1)
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

    def probe(self, body, step=2):
        """di, δική του στοίβα, Mode 0 χωρίς ROM (hw_mode0 — το αντίγραφο
        ξεκινά από την κεφαλίδα του snapshot), το body, σημαία. -> us από την
        αρχή του body ως τη σημαία, σε βήματα των `step` us."""
        m = self.m
        code = [0xF3, 0x31, STACK & 255, STACK >> 8] + self.call("HW_MODE0") + body + \
               [0x3E, 0x5A, 0x32, FLAG & 255, FLAG >> 8, 0x18, 0xFE]
        m.write_ram(PROBE, bytes(code))
        m.poke(FLAG, 0)
        m.set_pc(PROBE)
        us = 0
        while m.peek(FLAG) != 0x5A:
            m.run_us(step)
            us += step
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
    roles = [w.ag(i, 128) for i in range(6)]
    exp = {}
    for i in range(6):
        slot = w.ag(i, 384)
        exp[i] = (DX[slot >> 1], 2 if slot % 2 == 0 else -3,
                  w.m.peek(sym["ROLE_FIG"] + roles[i]))
    if {a: (x, y, f) for a, x, y, f in figs} != exp or want != exp:
        return f"ΑΡΧΗ: λίστα {figs}, μοντέλο {want}, η πρόζα λέει {exp}"
    n, bad = w.shown(figs, w.play())
    if n != 6 or bad:
        return f"ΑΡΧΗ: στην οθόνη {n} από 6 ολόκληρες, λείπουν {bad}"
    say(f"ΑΡΧΗ: {sorted((x, y, f) for a, x, y, f in figs)} κάτω (y = 2) και πάνω "
        f"(y = -3) από το σκάφος, στην οθόνη")
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


AG = 127                                                 # κανείς δεν είναι ο 127
K_SHIP = 7                                               # src/const.asm: το τελευταίο είδος δομής


def corner(w, patch=(), quiet=False):
    """ΓΩΝΙΑ, σε αντίγραφο του w (το ηλιακό του ΔΡΟΜΟΥ χτισμένο), με το patch
    στην τράπεζα 6. Η πρώτη διαφορά από την πρόζα, ή None."""
    c = w.clone()
    b6, L, m = c.bank(6), c.L, c.m
    for at, v in patch:
        b6[at - 0x4000] = v
    st = lambda n, k: L["G_struct_tbl"] + 8 * (n - 64) + k - 0x4000
    home = (b6[st(65, 0)], b6[st(65, 1)])
    sx, sy = sb(b6[st(64, 0)]), sb(b6[st(64, 1)])
    d0 = L["G_dome_tbl"] - 0x4000                        # ο θόλος 0: cx, cy, μέγεθος
    b6[d0], b6[d0 + 1], b6[d0 + 2] = (sx + 9) & 255, (sy + 13) & 255, 1
    f = L["G_agent_fields"] - 0x4000
    b6[f + AG], b6[f + 128 + AG], b6[f + 640 + AG] = 1, 0, 7   # ζωντανός, έξω, ακμή 7
    adj, own = L["G_node_adj"], lambda n: L["G_rt_nodes"] + 32 + n
    built = (m.peek(own(64)), m.peek(own(65)))
    if (built[1] & 0x5F) != 64:
        return f"ΓΩΝΙΑ: το ηλιακό δεν κρέμεται από το σκάφος (LK_OWN {built[1]:#x})"
    # ΟΙ ΔΟΜΕΣ ΕΙΝΑΙ ΤΕΤΡΑΓΩΝΕΣ: το fw_leg διαβάζει το μισό ύψος ως μισό πλάτος
    d = L["G_struct_dims"]
    odd = [(k, z) for k in range(K_SHIP + 1) for z in range(4)
           if m.peek(d + (k * 4 + z) * 2) // 4 != m.peek(d + (k * 4 + z) * 2 + 1) // 16]
    if odd:
        return f"ΓΩΝΙΑ: δομές που δεν είναι τετράγωνες (είδος, μέγεθος): {odd}"
    pw = c.sym["FG_WANT"]
    pg = L["G_agent_fields"] + 768 + AG
    # p = 0..255, και για καθένα A, D, E του fg_want στην οθόνη (#C000, τράπεζα 3)
    body = [0x01, 0xC6, 0x7F, 0xED, 0x49,                   # ld bc,#7FC6 / out (c),c
            0x21, 0x00, 0xC0, 0x22, 0xF0, 0x3E, 0xAF,       # ld hl,#C000 / ld (#3EF0),hl / xor a
            0x32, pg & 255, pg >> 8, 0x2E, AG,              # lp: ld (progress),a / ld l,AG
            0xCD, pw & 255, pw >> 8,                        # call fg_want
            0x2A, 0xF0, 0x3E, 0x77, 0x23, 0x72, 0x23, 0x73, 0x23,  # ld hl,(#3EF0) / A, D, E
            0x22, 0xF0, 0x3E, 0x3A, pg & 255, pg >> 8, 0x3C, 0x20, 0x100 - 26]
    assert body[-1] == 0x100 - (len(body) - 12)
    n = 0

    def case(label, a, b, o64, o65):
        nonlocal n
        m.poke(own(64), o64)
        m.poke(own(65), o65)
        m.poke(adj + 8 * a + 7, b)
        b6[f + 256 + AG] = a
        c.probe(body, step=500)
        scr = c.bank(3)
        for p in range(256):
            b6[f + 768 + AG] = p
            want = c.want(AG)
            got = (sb(scr[3 * p + 1] ^ 128), sb(scr[3 * p + 2] ^ 128), scr[3 * p])
            if got != want:
                return f"ΓΩΝΙΑ: {label}, {a} -> {b}, p = {p}: fg_want {got}, η πρόζα {want}"
        n += 1
        return None

    def both(label, o64, o65):
        return case(label, 64, 65, o64, o65) or case(label, 65, 64, o64, o65)

    places = (("όπου χτίστηκε", home), ("βορειοδυτικά", ((sx - 11) & 255, (sy - 9) & 255)),
              ("μία στήλη δίπλα, νότια", ((sx + 1) & 255, (sy + 9) & 255)),
              ("δύο στήλες δίπλα, νότια", ((sx + 2) & 255, (sy + 9) & 255)),
              ("σχεδόν στη σειρά", (home[0], (sy + 1) & 255)))
    for where, (x, y) in places:
        b6[st(65, 0)], b6[st(65, 1)] = x, y
        a, b = c.front(64), c.front(65)
        if a[0] == b[0] or a[1] == b[1]:
            return f"ΓΩΝΙΑ: {where}, το ηλιακό στη στήλη ή στη σειρά του σκάφους — κανένα Γ"
        why = (both(f"{where}, όπως χτίστηκε", *built)
               or both(f"{where}, πρώτα κατά x", 0, 64)
               or both(f"{where}, πρώτα κατά y", 0, 64 | 0x80)
               or both(f"{where}, σύνδεση εδάφους", 0, 64 | 0x20)
               or both(f"{where}, εδάφους πρώτα κατά y", 0, 64 | 0xA0)
               or both(f"{where}, το σκάφος από το ηλιακό", 65 | 0x80, 0)
               or both(f"{where}, από έναν τρίτο", 0, 66 | 0x80)
               or both(f"{where}, από κανέναν", 0, 0)
               or case(f"{where}, θόλος", 64, 0, 0x80, 0)
               or case(f"{where}, θόλος", 0, 64, 0x80, 0))
        if why:
            return why
    b6[st(65, 0)], b6[st(65, 1)] = home
    hy = sb(home[1]) + c.front(64)[1] - c.front(65)[1]       # το cy όπου τα μπροστινά συμπίπτουν
    # ο θόλος κι αυτός στη στήλη ή στη σειρά του σκάφους: ανάμεσα σε δύο δομές η
    # ευθεία είναι και αυτό που δίνει η γωνία μέσα σε αποτύπωμα, στον θόλο όχι
    hd = 4 + 2 * b6[d0 + 2]                               # το μισό του θόλου 0
    for where, (x, y), (dx, dy) in (
            ("στη στήλη του σκάφους", (sx & 255, home[1]), (sx, sy + 13)),
            ("στη σειρά του σκάφους", (home[0], hy & 255), (sx + 9, sy + 2 - hd))):
        b6[st(65, 0)], b6[st(65, 1)] = x, y
        b6[d0], b6[d0 + 1] = dx & 255, dy & 255
        a, b, d = c.front(64), c.front(65), c.front(0)
        if (a[0] == b[0]) == (a[1] == b[1]) or (a[0] == d[0]) == (a[1] == d[1]):
            return f"ΓΩΝΙΑ: {where}: τα μπροστινά σημεία {a[:2]}, {b[:2]}, {d[:2]}"
        why = (both(f"{where}, η ευθεία", 0, 64) or both(f"{where}, η ευθεία", 0, 64 | 0x80)
               or case(f"{where}, θόλος", 64, 0, 0, 0) or case(f"{where}, θόλος", 0, 64, 0, 0))
        if why:
            return why
    if not quiet:
        print(f"    ΓΩΝΙΑ: {n} ακμές x 256 τιμές του progress, fg_want = μοντέλο σε όλες "
              f"(το Γ όπως χτίστηκε: LK_OWN {built[1]:#04x})")
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


def cells(sym, g, patch=(), quiet=False):
    """ΚΕΛΙ (βήμα 105). Η πρώτη διαφορά από την πλήρη σχεδίαση, ή None."""
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    w = G(sym, g, patch)
    B.build(w.m, sym, 4, g + 6, at=SOLAR_FAR, fit=False)
    look(w.m)
    w.drain()
    pl = bytes(w.bank(4))
    at = lambda tx, ty: pl[((ty + 64) << 7) | (tx + 64)]
    s_ = w.sym
    # Οι κάμερες: πάνω στο ηλιακό (κελιά δίπλα και πάνω του), πάνω σε φλέβες,
    # και σε έδαφος κάθε κλάσης· το tx αλλάζει και το cam_p.
    veins = [(tx, ty) for ty in range(-60, 60) for tx in range(-60, 60)
             if at(tx, ty) & 15 == 11 and not at(tx, ty) & 0x10]
    cams = [((SOLAR_FAR[0] >> 1) - 10, (SOLAR_FAR[1] >> 1) - 5)]
    cams += [(tx - 10, ty - 5) for tx, ty in veins[::max(1, len(veins) // 3)][:3]]
    cams += [(-30 + 7 * k, -25 + 9 * k) for k in range(4)]
    seen = {"ελεύθερο": 0, "δίπλα σε κτίσμα": 0, "πάνω σε κτίσμα": 0, "φλέβα": 0}
    for j, (cx, cy) in enumerate(cams):
        cx, cy = min(max(cx, -64), 44), min(max(cy, -64), 54)
        c = w.clone()
        c.m.poke(s_["CAM_TX"], cx & 255)
        c.m.poke(s_["CAM_TY"], cy & 255)
        ref = c.full()
        cam, scr = c.cam(), c.bank(3)
        gx0, gx1, gy0, gy1 = (c.m.peek(s_["GH_BBX"]), c.m.peek(s_["GH_BBX"] + 1),
                              c.m.peek(s_["GH_BBY"]), c.m.peek(s_["GH_BBY"] + 1))
        at_ = [(2 * ((k * 7) % 40), 8 * ((k * 11) % 20)) for k in range(48)]
        if j == 0:                          # γύρω από το ηλιακό, στο κέντρο του κάδρου
            at_ += [(bx, ly) for bx in range(30, 52, 2) for ly in range(56, 112, 8)]
        for bx, ly in at_:
            if bx < gx1 and gx0 < bx + 2 and ly < gy1 and gy0 < ly + 8:
                continue                    # κάτω από τον κέρσορα
            x, y = 2 * cx + bx // 2, 2 * cy + ly // 8      # μισά tiles
            for r in range(8):
                for b in range(2):
                    yy, xx = ly + r, bx + b
                    scr[(yy & 7) * 0x800 + (((yy >> 3) * 80 + xx + cam) & 0x7FF)] = 0x55
            c.m.poke(s_["FG_OX"], (x + 128) & 255)
            c.m.poke(s_["FG_OY"], (y + 128) & 255)
            c.probe(c.call("FG_ERASE"))
            got = c.play()
            kind = ("φλέβα" if at(x >> 1, y >> 1) & 15 == 11 else
                    ("ελεύθερο", "δίπλα σε κτίσμα", "πάνω σε κτίσμα")[ground(c, x, y)])
            if got != ref:
                n = sum(1 for a, b in zip(got, ref) if a != b)
                return (f"ΚΕΛΙ ({x}, {y}), {kind}, κάμερα ({cx}, {cy}): {n} bytes "
                        f"διαφέρουν από την πλήρη σχεδίαση")
            seen[kind] += 1
        # ΤΟ call ΞΑΝΑΓΡΑΦΤΗΚΕ: ένα άδειασμα θέσης (dhs_vacate) σε 2x8 που ΔΕΝ
        # αρχίζει σε σειρά χαρακτήρων, μετά από τα σβησίματα — με το fg_tile
        # θα έγραφε σε λάθος γραμμές.
        ox, oy = 2 * ((cx * 3) % 30) + 7, 8 * ((cy * 5) % 15) + 4
        for r in range(8):
            for b in range(2):
                yy, xx = oy + r, ox + b
                scr[(yy & 7) * 0x800 + (((yy >> 3) * 80 + xx + cam) & 0x7FF)] = 0x55
        for name, v in (("OB_X", ox), ("OB_Y", oy)):
            c.m.poke(s_[name], v)
            c.m.poke(s_[name] + 1, 0)
        try:
            c.probe(c.call("DHS_VACATE"))
        except AssertionError:
            # Με το fg_tile αντί για το ob_put το άδειασμα γράφει σε λάθος
            # γραμμές — και από το βήμα 111 (άλλη διάταξη στην τράπεζα 6)
            # γράφει και πάνω στον κώδικα και δεν γυρίζει. Και τα δύο είναι
            # «δεν είναι η πλήρης σχεδίαση».
            return f"ΚΕΛΙ: ένα άδειασμα θέσης στο ({ox}, {oy}) δεν τελείωσε"
        if c.play() != ref:
            return (f"ΚΕΛΙ: ένα άδειασμα θέσης στο ({ox}, {oy}) μετά από τα σβησίματα δεν "
                    f"είναι η πλήρης σχεδίαση")
    if any(v < 6 for v in seen.values()):
        return f"ΚΕΛΙ: οι σκηνές δεν έχουν όλα τα είδη κελιού: {seen}"
    say(f"ΚΕΛΙ: σβησμένα με σκουπίδια πριν και = η πλήρης σχεδίαση: {seen}, σε "
        f"{len(cams)} κάμερες, και ένα άδειασμα θέσης μετά σε καθεμία")
    return None


def stacks(sym, g, patch=(), quiet=False):
    """ΣΤΟΙΒΕΣ (βήμα 106). Η πρώτη διαφορά από την πλήρη σχεδίαση, ή None."""
    say = (lambda s: None) if quiet else (lambda s: print("    " + s))
    w = G(sym, g, patch)
    B.build(w.m, sym, 4, g + 6, at=SOLAR_FAR, fit=False)
    look(w.m)
    w.drain()
    pl = bytes(w.bank(4))
    at = lambda tx, ty: pl[((ty + 64) << 7) | (tx + 64)]
    s_, fl = w.sym, w.L["G_fig_list"] - 0x4000
    veins = [(tx, ty) for ty in range(-60, 60) for tx in range(-60, 60)
             if at(tx, ty) & 15 == 11 and not at(tx, ty) & 0x10]
    cams = [((SOLAR_FAR[0] >> 1) - 10, (SOLAR_FAR[1] >> 1) - 5)]
    cams += [(tx - 10, ty - 5) for tx, ty in veins[:1]]
    seen = {"ελεύθερο": 0, "δίπλα σε κτίσμα": 0, "πάνω σε κτίσμα": 0, "φλέβα": 0}
    stacked = 0
    for j, (cx, cy) in enumerate(cams):
        cx, cy = min(max(cx, -64), 44), min(max(cy, -64), 54)
        c = w.clone()
        c.m.poke(s_["CAM_TX"], cx & 255)
        c.m.poke(s_["CAM_TY"], cy & 255)
        # Η ΛΙΣΤΑ ΤΗΣ ΔΟΚΙΜΗΣ: το fg_build γίνεται jp ob_touch, ώστε η πλήρης
        # σχεδίαση να ζωγραφίσει αυτήν, με τη σειρά της, και όχι τους πράκτορες.
        fb, ot = s_["FG_BUILD"], s_["OB_TOUCH"]
        for k, v in enumerate((0xC3, ot & 255, ot >> 8)):
            c.m.poke(fb + k, v)
        c.full()                            # το φάντασμα, στη νέα κάμερα
        gx0, gx1, gy0, gy1 = (c.m.peek(s_["GH_BBX"]), c.m.peek(s_["GH_BBX"] + 1),
                              c.m.peek(s_["GH_BBY"]), c.m.peek(s_["GH_BBY"] + 1))
        # οκτώ στήλες x τρεις σειρές: κάθε στήλη έχει τρία κελιά, άρα το cpir
        # βρίσκει και εγγραφές με το ίδιο ux σε άλλη σειρά· στην πρώτη κάμερα
        # και κελιά γύρω από το ηλιακό, σε κάθε είδος εδάφους
        at_ = [(bx, ly) for bx in range(2, 80, 10) for ly in range(8, 160, 56)]
        if j == 0:
            at_ += [(bx, ly) for bx in range(32, 52, 4) for ly in range(64, 112, 16)]
        at_ = [(bx, ly) for bx, ly in at_
               if not (bx < gx1 and gx0 < bx + 2 and ly < gy1 and gy0 < ly + 8)]
        b6, ents = c.bank(6), []
        for i, (bx, ly) in enumerate(at_):
            x, y = 2 * cx + bx // 2, 2 * cy + ly // 8
            for f in ((1 + 3 * i % 8, 1 + (3 * i + 5) % 8) if i % 3 == 0 else (1 + 3 * i % 8,)):
                ents.append(((x + 128) & 255, (y + 128) & 255, f))
        ents = ents[:64]                    # FG_CAP
        for k, e in enumerate(ents):
            for col, v in zip(range(0, 256, 64), e + (127 - k,)):
                b6[fl + col + k] = v
        n = len(ents)
        c.m.poke(s_["FG_N"], n)
        ref = c.full()
        cam, scr = c.cam(), c.bank(3)
        for bx, ly in at_:
            x, y = 2 * cx + bx // 2, 2 * cy + ly // 8
            kind = ("φλέβα" if at(x >> 1, y >> 1) & 15 == 11 else
                    ("ελεύθερο", "δίπλα σε κτίσμα", "πάνω σε κτίσμα")[ground(c, x, y)])
            here = [e for e in ents if e[:2] == ((x + 128) & 255, (y + 128) & 255)]
            # σκουπίδια και σβήσιμο: το έδαφος ΚΑΙ οι φιγούρες του κελιού
            for r in range(8):
                for b in range(2):
                    yy, xx = ly + r, bx + b
                    scr[(yy & 7) * 0x800 + (((yy >> 3) * 80 + xx + cam) & 0x7FF)] = 0x55
            c.m.poke(s_["FG_OX"], (x + 128) & 255)
            c.m.poke(s_["FG_OY"], (y + 128) & 255)
            c.probe(c.call("FG_ERASE"))
            got = c.play()
            if got != ref:
                return (f"ΣΤΟΙΒΕΣ: σβήσιμο του ({x}, {y}), {kind}, {len(here)} φιγούρες: "
                        f"{sum(a != b for a, b in zip(got, ref))} bytes διαφέρουν")
            # το κελί χωρίς φιγούρες (λίστα άδεια για το σβήσιμο), και μετά το
            # ζωγράφισμα: οι φιγούρες του, με τη σειρά της λίστας
            c.m.poke(s_["FG_N"], 0)
            c.probe(c.call("FG_ERASE"))
            c.m.poke(s_["FG_N"], n)
            c.m.poke(s_["FG_NX"], (x + 128) & 255)
            c.m.poke(s_["FG_NY"], (y + 128) & 255)
            c.probe(c.call("FG_PAINT"))
            got = c.play()
            if got != ref:
                return (f"ΣΤΟΙΒΕΣ: ζωγράφισμα του ({x}, {y}), {kind}, {len(here)} φιγούρες: "
                        f"{sum(a != b for a, b in zip(got, ref))} bytes διαφέρουν")
            seen[kind] += 1
            stacked += len(here) > 1
    if min(seen.values()) < 2 or stacked < 6:
        return f"ΣΤΟΙΒΕΣ: οι σκηνές δεν έχουν όλα τα είδη κελιού: {seen}, {stacked} με δύο φιγούρες"
    say(f"ΣΤΟΙΒΕΣ: σβήσιμο και ζωγράφισμα = η πλήρης σχεδίαση με τη λίστα της δοκιμής: "
        f"{seen}, {stacked} κελιά με δύο φιγούρες")
    return None


def parts(sym, g, patch=(), out=None):
    """ΜΕΡΗ (βήμα 106): το fg_erase και το fg_paint μόνα τους, σε κάθε κελί
    δύο καμερών, χρεώνουν όσο κοστίζουν ή περισσότερο."""
    check_ = out or check
    w = G(sym, g, patch)
    B.build(w.m, sym, 4, g + 6, at=SOLAR_FAR, fit=False)
    look(w.m)
    w.drain()
    pl = bytes(w.bank(4))
    at = lambda tx, ty: pl[((ty + 64) << 7) | (tx + 64)]
    s_, spent = w.sym, sym["DT_SPENT"]
    veins = [(tx, ty) for ty in range(-60, 60) for tx in range(-60, 60)
             if at(tx, ty) & 15 == 11 and not at(tx, ty) & 0x10]
    cams = [((SOLAR_FAR[0] >> 1) - 10, (SOLAR_FAR[1] >> 1) - 5)]
    cams += [(tx - 10, ty - 5) for tx, ty in veins[:1]]
    meas = {}
    for cx, cy in cams:
        cx, cy = min(max(cx, -64), 44), min(max(cy, -64), 54)
        c = w.clone()
        c.m.poke(s_["CAM_TX"], cx & 255)
        c.m.poke(s_["CAM_TY"], cy & 255)
        c.full()
        gx0, gx1, gy0, gy1 = (c.m.peek(s_["GH_BBX"]), c.m.peek(s_["GH_BBX"] + 1),
                              c.m.peek(s_["GH_BBY"]), c.m.peek(s_["GH_BBY"] + 1))
        for bx in range(0, 80, 2):
            for ly in range(0, 160, 8):
                if bx < gx1 and gx0 < bx + 2 and ly < gy1 and gy0 < ly + 8:
                    continue                # το φάντασμα σηκώνεται μία φορά ανά τικ
                x, y = 2 * cx + bx // 2, 2 * cy + ly // 8
                kind = ("φλέβα" if at(x >> 1, y >> 1) & 15 == 11 else
                        ("ελεύθερο", "δίπλα σε κτίσμα", "πάνω σε κτίσμα")[ground(c, x, y)])
                for name, lx, ly_ in (("FG_ERASE", "FG_OX", "FG_OY"), ("FG_PAINT", "FG_NX", "FG_NY")):
                    c.m.poke(s_[lx], (x + 128) & 255)
                    c.m.poke(s_[ly_], (y + 128) & 255)
                    us = c.probe([0x21, 0, 0, 0x22, spent & 255, spent >> 8]
                                 + c.call(name)) - 34
                    ch = c.m.peek(spent) | c.m.peek(spent + 1) << 8
                    meas.setdefault((name, kind if name == "FG_ERASE" else "όπου κι αν"), []).append((us, ch))
    for (name, kind), v in sorted(meas.items()):
        worst = max(v, key=lambda x: x[0] - x[1])
        check_(len(v) >= 8 and all(u <= ch for u, ch in v),
               f"ΜΕΡΗ, {name.lower()} {kind}: {len(v)} κελιά, {min(u for u, _ in v)}-"
               f"{max(u for u, _ in v)} us, χειρότερο {worst[0]} για χρέωση {worst[1]}")
    return meas


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
    raw = []
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
                raw.append((kind, full, ground(w, x, y), us))
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
    # ΤΑΒΑΝΙΑ (βήμα 106): η μέση τιμή με κανονική λίστα, ανά έδαφος — όχι
    # μόνο «όσο χρεώνει», γιατί η χρέωση μπορεί να ανέβει μαζί με το κόστος.
    for kind, gr, cap, was in (("σβήνει και ζωγραφίζει", 0, 2400, 3810),
                               ("σβήνει και ζωγραφίζει", 1, 3150, 4174),
                               ("τίποτα", 0, 620, 682),
                               ("αλλάζει έξω από το κάδρο", 0, 780, 840)):
        v = [us for k, full, g_, us in raw if k == kind and not full and g_ == gr]
        avg = sum(v) // max(1, len(v))
        check_(v and avg <= cap,
               f"ΚΟΣΤΟΣ, ΤΑΒΑΝΙ: {kind}, {('σε ελεύθερο έδαφος', 'δίπλα σε κτίσμα')[gr]}: "
               f"μέση {avg} us σε {len(v)} μετρήσεις, ως {cap} ({was} ως το βήμα 105)")
    return meas, under, padded


def main():
    sym, g = TG.build()
    why = scenario(sym, g)
    check(why is None, why or "ΑΡΧΗ και ΔΡΟΜΟΣ: όπως λέει η πρόζα")
    base = G(sym, g)
    B.build(base.m, sym, 4, g + 6, at=SOLAR_AT, fit=False)
    look(base.m)
    why = corner(base)
    check(why is None, why or "ΓΩΝΙΑ: όπως λέει η πρόζα")
    why = dome(sym, g)
    check(why is None, why or "ΘΟΛΟΣ: όπως λέει η πρόζα")
    why = meteor(sym, g)
    check(why is None, why or "ΜΕΤΕΩΡΙΤΗΣ: όπως λέει η πρόζα")
    why = cells(sym, g)
    check(why is None, why or "ΚΕΛΙ: το σβήσιμο = η πλήρης σχεδίαση, και η φλέβα μένει")
    why = stacks(sym, g)
    check(why is None, why or "ΣΤΟΙΒΕΣ: σβήσιμο και ζωγράφισμα = η πλήρης σχεδίαση")
    parts(sym, g)
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
    # βήμα 105: το fg_tile
    ft = sym["FG_TILE"]
    q8, q2 = find(ft, [0xE6, 8], 40), find(ft, [0xE6, 2], 40)
    vn = find(ft, [0xE6, 15, 0xFE, 11], 80)
    gl = find(sym["FGE_GO"], [0x21] + w(ft), 4)                   # ld hl,fg_tile
    gr = find(sym["FGE_GO"], [0x21] + w(sym["OB_PUT"]), 24)       # ld hl,ob_put
    for label, patch in (
            ("πάντα το πάνω αριστερό τέταρτο του tile",
             q8 and q2 and [(q8 + 1, 0), (q2 + 1, 0)]),
            ("χωρίς τη φλέβα", vn and [(vn + 3, 255)]),
            ("το call δεν ξαναγράφεται", gr and [(gr + 1, ft & 255), (gr + 2, ft >> 8)])):
        if not patch:
            check(False, f"δεν βρέθηκε πού να πειραχτεί για «{label}»")
            continue
        why = cells(sym, g, patch, quiet=True)
        check(why is not None, f"ΑΡΝΗΤΙΚΟ: με «{label}» το ΚΕΛΙ αποτυγχάνει ({(why or '')[:100]})")
    bad = []
    if gl:
        op = sym["OB_PUT"]
        cost(sym, g, [(gl + 1, op & 255), (gl + 2, op >> 8)], out=lambda ok, msg: bad.append(not ok))
    check(gl and any(bad), "ΑΡΝΗΤΙΚΟ: χωρίς το fg_tile (το ob_put όπως ως το βήμα 104) το "
                           f"ΚΟΣΤΟΣ αποτυγχάνει ({sum(bad)} από {len(bad)} έλεγχοι)")
    why = meteor(sym, g, [(sym["FG_DRAW1"], 0xC9)], quiet=True)    # ret
    check(why is not None, f"ΑΡΝΗΤΙΚΟ: με το dh_tile χωρίς φιγούρες σε ελεύθερο έδαφος, ο "
                           f"ΜΕΤΕΩΡΙΤΗΣ αποτυγχάνει ({(why or '')[:100]})")
    # βήμα 106: ο δρόμος του κελιού
    fc, fe, fp = sym["FG_CELL"], sym["FG_ERASE"], sym["FG_PAINT"]
    yc = find(sym["FGC_Y"], [0xFE, 0, 0x20], 4)                   # cp 0 / jr nz,fgc_nx
    lp = find(sym["FGC_NX"], [0x2C, 0x78, 0xB1, 0x20], 4)         # inc l / ... / jr nz,fgc_x
    ie = find(fc, [0x1C, 0x2D, 0xCB], 40)                         # inc e / dec l / set
    rw = find(fe, [0x06, 3], 60)                                  # ld b,3 των 3x3
    sp = find(fp, [0xCD] + w(sym["FG_SCR"]), 40)
    fq = find(sym["FGV_Q"], [0x3E, 0, 0x87], 4)                   # ld a,0 / add a,a
    fv = find(sym["FGV_LP"], [0x11] + w(300), 40)                 # ld de,FG_VEIN_US
    jf = find(sym["FGE_ROW"], [0xE6, 0x10, 0x20], 12)              # and W_OCC_STRUCT / jr nz
    wa = find(sym["FWA_POS"], [0xCB, 0x3D, 0x30, 1, 0x84, 0x1F], 8)  # το πρώτο βήμα
    for label, patch, fn in (
            ("χωρίς τον έλεγχο του uy στο fg_cell", yc and [(yc + 2, 0), (yc + 3, 0)], stacks),
            ("μόνο η πρώτη εγγραφή με το ίδιο ux", lp and [(lp + 3, 0), (lp + 4, 0)], stacks),
            ("χωρίς το fg_scr στο fg_paint", sp and [(sp + k, 0) for k in range(3)], stacks),
            ("μία σειρά από τα 3x3", rw and [(rw + 1, 1)], cells),
            ("η φλέβα σε λάθος τέταρτο", fq and [(fq + 2, 0)], cells),
            ("το τελευταίο βήμα του πολλαπλασιασμού χωρίς rra", wa and [(wa + 5 + 7 * 6, 0)], scenario)):
        if not patch:
            check(False, f"δεν βρέθηκε πού να πειραχτεί για «{label}»")
            continue
        why = fn(sym, g, patch, quiet=True)
        check(why is not None, f"ΑΡΝΗΤΙΚΟ: με «{label}» το {fn.__name__} αποτυγχάνει "
                               f"({(why or '')[:100]})")
    for label, patch, fn in (
            ("η φλέβα δεν χρεώνεται", fv and [(fv + 1, 0), (fv + 2, 0)], parts),
            ("χωρίς τη χρέωση όσων έχουν το ίδιο ux", ie and [(ie, 0)], cost),
            ("πάντα το γενικό πέρασμα, και σε ελεύθερο έδαφος",
             jf and [(jf + 2, 0x18)], cost)):                        # jr nz -> jr
        bad = []
        if patch:
            fn(sym, g, patch, out=lambda ok, msg: bad.append(not ok))
        check(patch and any(bad), f"ΑΡΝΗΤΙΚΟ: με «{label}» το {'ΜΕΡΗ' if fn is parts else 'ΚΟΣΤΟΣ'} "
                                  f"αποτυγχάνει ({sum(bad)} από {len(bad)} έλεγχοι)")

    # βήμα 118: το Γ (src/walk6.asm, b6code)
    b6 = base.bank(6)
    fl = sym["FW_LEG"]

    def find6(at, pat, n=96):
        return next((at + k for k in range(n)
                     if list(b6[at + k - 0x4000:at + k - 0x4000 + len(pat)]) == pat), None)

    cl = sym["FWL_OWN"] - 1
    a64 = find6(fl, [0xE6, 0x40, 0x28])                           # and 64 / jr z,fwl_x
    g1 = find6(fl, [0xE6, 0x5F])
    g2 = g1 and find6(g1 + 2, [0xE6, 0x5F])
    ly = find6(fl, [0x7A, 0xBC, 0x28])                            # ld a,d / cp h / jr z,fwl_ly
    lx = find6(fl, [0x7B, 0xBD, 0x28])                            # ld a,e / cp l / jr z,fwl_lx
    dh = find6(sym["FWL_X"], [0x30], 8)                           # jr nc,fwl_mx / ld d,h
    pr = find6(sym["FWL_PX"], [0x7B, 0x90, 0x4F], 4)              # ld a,e / sub b / ld c,a
    pc = find6(sym["FPX_C"], [0x7C, 0x90, 0xFA], 16)              # ld a,h / sub b / jp m,fwl_xr
    ps = find6(sym["FWL_PX"], [0x6F, 0x91, 0xFA], 24)             # ld l,a / sub c / jp m,fwl_xr
    po, pg = sym["FPX_C"], sym["FPX_GO"]                          # ... add a,b; ... jp z,fw_out
    yc = find6(sym["FWL_PY"], [0x78, 0x87, 0x2F, 0x83], 24)       # ld a,b / add a,a / cpl / add a,e
    yx = find6(sym["FPY_E"], [0x91, 0x3D], 4)                     # sub c / dec a
    fa = sym["FW_AXIS"]
    ia = find6(sym["FPX_GO"], [0xCD, fa & 255, fa >> 8, 0x3C], 24)  # call fw_axis / inc a
    for label, patch in (
            ("χωρίς το cpl", b6[cl - 0x4000] == 0x2F and [(cl, 0)]),
            ("πάντα πρώτα κατά x", b6[cl + 1 - 0x4000] == 0x17 and [(cl + 1, 0xB7)]),   # rla -> or a
            ("και με θόλο στη μία άκρη", a64 and [(a64 + 2, 0), (a64 + 3, 0)]),
            ("το bit του εδάφους μετρά", g2 and [(g1 + 1, 0x7F), (g2 + 1, 0x7F)]),
            ("χωρίς την ευθεία σε ίδια στήλη", ly and [(ly + 2, 0), (ly + 3, 0)]),
            ("χωρίς την ευθεία σε ίδια σειρά", lx and [(lx + 2, 0), (lx + 3, 0)]),
            ("το δεύτερο μισό του «πρώτα κατά x» χωρίς τη στήλη bx",
             dh and b6[dh + 2 - 0x4000] == 0x54 and [(dh + 2, 0)]),
            ("η γωνία στη σειρά του μπροστινού σημείου", pr and [(pr + 1, 0)]),
            ("χωρίς τον έλεγχο της στήλης", pc and [(pc + 2, 0), (pc + 3, 0), (pc + 4, 0)]),
            ("χωρίς τον έλεγχο της σειράς", ps and [(ps + 2, 0), (ps + 3, 0), (ps + 4, 0)]),
            ("το πρώτο σκέλος από το κέντρο", b6[po + 6 - 0x4000] == 0x80 and [(po + 6, 0)]),
            ("με progress 0 ήδη στο μονοπάτι",
             b6[pg + 6 - 0x4000] == 0xCA and [(pg + 6, 0), (pg + 7, 0), (pg + 8, 0)]),
            ("πρώτα κατά y, πάνω από το P χωρίς το cpl", yc and [(yc + 2, 0)]),
            ("πρώτα κατά y, ως τη στήλη του κέντρου του Q", yx and [(yx, 0), (yx + 1, 0)]),
            ("το σκέλος στη στήλη της θέσης 0", ia and [(ia + 3, 0)]),
            ("η σειρά μέσα στο Q, μόνο το y", ps and [(ps + 3, sym["FWL_LYR"] & 255),
                                                       (ps + 4, sym["FWL_LYR"] >> 8)])):
        if not patch:
            check(False, f"δεν βρέθηκε πού να πειραχτεί για «{label}»")
            continue
        why = corner(base, patch, quiet=True)
        check(why is not None, f"ΑΡΝΗΤΙΚΟ: με «{label}» η ΓΩΝΙΑ αποτυγχάνει ({(why or '')[:110]})")

    if FAIL:
        print(f"\nΑΠΟΤΥΧΙΑ — {len(FAIL)}")
        return 1
    print("\nOK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
