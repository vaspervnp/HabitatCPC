#!/usr/bin/env python3
"""Οι λωρίδες Mode 1 του HUD και τα σπασίματα της οθόνης, στο main.sna (DESIGN §8.1,
§9.2, βήμα 83).

Η ΠΡΟΖΑ:

  Η εικόνα είναι τρία κομμάτια. Οι γραμμές 0-15 είναι Mode 1 με τα pens της
  λωρίδας (0 μαύρο, 1 κόκκινο, 2 πράσινο, 3 λευκό), οι 16-175 Mode 0 με την
  παλέτα του παιχνιδιού και του πλανήτη, οι 176-199 ξανά Mode 1 με τα pens της
  λωρίδας. Κάθε pixel της εικόνας που βγάζει ο εξομοιωτής είναι η μνήμη της
  οθόνης διαβασμένη έτσι — και όταν ο Z80 τρέχει τις πιο αργές εντολές του,
  που καθυστερούν τη διακοπή ως 6 us.

  Οι γραμμές 15 και 176 μένουν μαύρες στη μνήμη: εκεί γίνονται τα σπασίματα.

  Οι λωρίδες είναι ίδιες στην οθόνη πριν και μετά από κάθε βήμα κάμερας, προς
  κάθε κατεύθυνση και όπου κι αν πέσει το τύλιγμα του δαχτυλιδιού — με ή
  χωρίς παύση (ως το βήμα 82 οι σειρές 0-2 έμεναν σκουπίδια σε παύση).

  Η διακοπή παίρνει το πολύ 1.200 us ανά frame (μετρημένο: 1.177).

ΠΩΣ. Η εικόνα του εξομοιωτή είναι μία σάρωση ανά γραμμή, 16 pixel ανά us· η
γραμμή 0 είναι η σάρωση 13 (R7 = 33) και ο χαρακτήρας 0 το x = 64. Ενα byte
είναι 8 pixel της εικόνας: 2 pixel Mode 0 ή 4 Mode 1.

  1. Μοτίβο: οι λωρίδες και οι γραμμές του κάδρου δίπλα στα σύνορα γεμίζουν
     με bytes που έχουν και τα τέσσερα pens, η παύση σταματά το παιχνίδι, και
     ο Z80 τρέχει βρόχο με ex (sp),hl (6 us) και nop (1 us) — όσο πιο άνισα
     γίνεται. Κάθε δείγμα με άλλο πλήθος nop, ώστε η φάση να αλλάζει.
  2. Το ζωντανό παιχνίδι στο x4: συγκρίνονται οι γραμμές που η μνήμη τους δεν
     άλλαξε μέσα στο frame.
  3. Βήματα κάμερας με probe (view_scroll), και οι 40 γραμμές των λωρίδων
     διαβασμένες ως οθόνη πριν και μετά.
  4. Μετρητής σε βρόχο, 200 frames, με και χωρίς διακοπές.

ΑΡΝΗΤΙΚΑ, με τη διακοπή πειραγμένη στη μνήμη — κάθε ένα πρέπει να χαλάει το 1:
χωρίς τον μηδενισμό του μετρητή του Gate Array· το πάνω σπάσιμο 48 us νωρίτερα
και 20 us αργότερα· το κάτω 20 us νωρίτερα και 48 us αργότερα. Και για το 3:
το hud_move που δεν κάνει τίποτα.
"""
import os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import hudread                                           # noqa: E402
import cpc                                               # noqa: E402
from palette import FW_RGB                               # noqa: E402

FAIL = []
W, X0 = 1024, 64                    # η εικόνα: πλάτος σάρωσης, x του χαρακτήρα 0
Y0 = 13                             # η σάρωση της γραμμής 0 με R7 = 33
PROBE = 0x3E00
TOP, BOT = 16, 176                  # η πρώτη γραμμή του κάδρου, της κάτω λωρίδας
BAND_HW = [0x14, 0x0C, 0x12, 0x0B]  # μαύρο, έντονο κόκκινο, πράσινο, λευκό
BAND_FW = [0, 6, 18, 26]
COST_CEIL = 1200                    # us ανά frame


def check(ok, msg):
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ ") + msg)
    if not ok:
        FAIL.append(msg)


def layout(name):
    for line in open(os.path.join(ROOT, "build", "layout.asm"), encoding="utf-8"):
        p = line.split()
        if p and p[0] == name:
            return int(p[2].lstrip("#"), 16)
    raise SystemExit(f"δεν βρέθηκε το {name}")


def fresh(sym, patch=()):
    m = cpc.CPC()
    m.run_frames(60)
    assert m.quickload(TG.SNA), "quickload απέτυχε"
    m.run_frames(150)
    for at, v in patch:
        m.poke(at, v)
    return m


def to_loop(m, sym):
    top = sym["MAIN_LOOP"]
    for _ in range(40000):
        if top <= m.pc < top + 13:
            return
        m.run_us(50)
    raise SystemExit("ο βρόχος δεν ξαναήρθε")


def play_pens(m, sym):
    """Pen -> hardware χρώμα στο κάδρο: το palette_fw, και ο πλανήτης στα 7, 11, 12, 14,
    μέσα από τον πίνακα του παιχνιδιού (τον ελέγχει το test_palette)."""
    fw = [m.peek(layout("G_palette_fw") + p) for p in range(16)]
    b6 = cpc._lib.cpcemu_ram_ptr(m._h, 6)
    planet = b6[layout("G_worldinfo") + 2 - 0x4000]
    for k, p in enumerate((7, 11, 12, 14)):
        fw[p] = m.peek(layout("G_planet_pens") + 4 * planet + k)
    return [m.peek(sym["FW_TO_HW"] + c) & 0x1F for c in fw]


def expect_line(ram, start, y, play):
    """Τα 640 pixel της γραμμής y όπως τα λέει η μνήμη (hardware χρώματα)."""
    base = (y & 7) * 0x800                      # το ram αρχίζει στο #C000
    off = start + (y >> 3) * 80
    out = []
    band = y < TOP or y >= BOT
    for x in range(80):
        b = ram[base + ((off + x) & 0x7FF)]
        if band:
            for p in hudread.m1_pens(b):
                out += [BAND_HW[p]] * 2
        else:
            for p in hudread.m0_pens(b):
                out += [play[p]] * 4
    return out


def compare(m, ram, play, lines):
    """-> [(γραμμή, πόσα pixel λάθος, το πρώτο x σε us)]"""
    fb = m.framebuffer()
    start = 2 * (m.crtc_screen_addr & 0x3FF)
    bad = []
    for y in lines:
        want = expect_line(ram, start, y, play)
        row = fb[(Y0 + y) * W + X0:(Y0 + y) * W + X0 + 640]
        diff = [x for x in range(640) if row[x] != want[x]]
        if diff:
            bad.append((y, len(diff), diff[0] / 16))
    return bad


# --- 1. μοτίβο, και ο Z80 στις αργές του ---------------------------------
M1_PAT = [0x1B, 0xE4, 0x6C, 0xC9, 0xFF, 0x93]     # Mode 1: όλα τα pens, σε όλες τις θέσεις
M0_PAT = [0xC0, 0x0C, 0xCC, 0x3C, 0xF3, 0x30]     # Mode 0: pens 1, 2, 3 και άλλα


def pattern(m, sym):
    """Γεμίζει λωρίδες (εκτός από 15 και 176) και τις γραμμές 14-17, 174-177 του κάδρου."""
    cp = hudread.cam_p(m, sym)
    start = cp - 160
    for y in list(range(0, 15)) + list(range(177, 200)) + [16, 17, 174, 175]:
        pat = M1_PAT if (y < TOP or y >= BOT) else M0_PAT
        off = start + (y >> 3) * 80
        data = bytes(pat[(x + y) % len(pat)] for x in range(80))
        for x in range(80):
            m.poke(0xC000 + (y & 7) * 0x800 + ((off + x) & 0x7FF), data[x])


def slow_loop(nops):
    """ei · βρόχος: nop x nops · ex (sp),hl · ex (sp),hl · jr"""
    body = [0x00] * nops + [0xE3, 0xE3]
    return bytes([0xFB] + body + [0x18, (-(len(body) + 2)) & 0xFF])


def scenario_pattern(sym, patch=(), samples=24):
    m = fresh(sym)
    m.poke(sym["UI_SPD"], 0)
    m.run_frames(30)
    to_loop(m, sym)
    play = play_pens(m, sym)
    for at, v in patch:
        m.poke(at, v)
    pattern(m, sym)
    ram = m.read_ram(0xC000, 0x4000)
    blank = [y for y in (15, 176)
             if any(expect_line(ram, 2 * (m.crtc_screen_addr & 0x3FF), y, play)[x] != 0x14
                    for x in range(640))]
    bad_all = []
    for k in range(samples):
        m.write_ram(PROBE, slow_loop(k % 7))
        m.set_pc(PROBE)
        m.run_frames(2 + k % 3)
        bad_all += compare(m, ram, play, range(200))
    return blank, bad_all


# --- 1β. μετά από κλειστές διακοπές --------------------------------------
def scenario_resync(sym, on=True, trials=16, patch=()):
    """di για 1-56 ms, μετά is_on (ή σκέτο ei) και ο αργός βρόχος. Με το is_on η
    αλυσίδα περιμένει το πρώτο VSYNC, άρα κάθε frame που αρχίζει 20 ms μετά το
    ei είναι σωστό: συγκρίνονται τα τρία πρώτα τέτοια. -> σε πόσες δοκιμές
    κάποιο είχε λάθος pixel."""
    m = fresh(sym)
    m.poke(sym["UI_SPD"], 0)
    m.run_frames(30)
    to_loop(m, sym)
    play = play_pens(m, sym)
    pattern(m, sym)
    ram = m.read_ram(0xC000, 0x4000)
    io = sym["IS_ON"]
    wrong = 0
    for at, v in patch:
        m.poke(at, v)
    for k in range(trials):
        n = 150 + k * 520                       # x 7 us: 1,0 - 55,7 ms κλειστές
        back = [0xCD, io & 255, io >> 8] if on else [0xFB]
        loop = [0x00, 0xE3, 0xE3]
        code = ([0xF3, 0x01, n & 255, n >> 8, 0x0B, 0x78, 0xB1, 0x20, 0xFB]  # di · αναμονή
                + back + loop + [0x18, (-(len(loop) + 2)) & 0xFF])
        m.write_ram(PROBE, bytes(code))
        m.set_pc(PROBE)
        m.run_us(n * 7 + 40000)                 # ως το τέλος του πρώτου ολόκληρου
        bad = False
        for _ in range(3):
            bad = bad or bool(compare(m, ram, play, range(200)))
            m.run_us(19968)
        wrong += bad
    return wrong


# --- 2. το ζωντανό παιχνίδι ------------------------------------------------
def scenario_live(sym, frames=60):
    m = fresh(sym)
    m.poke(sym["UI_SPD"], 4)
    m.run_frames(100)
    play = play_pens(m, sym)
    seen, bad = 0, []
    for _ in range(frames):
        a = m.read_ram(0xC000, 0x4000)
        crtc = m.crtc_screen_addr
        m.run_frames(1)
        b = m.read_ram(0xC000, 0x4000)
        if m.crtc_screen_addr != crtc:
            continue
        start = 2 * (crtc & 0x3FF)
        same = [y for y in range(200)
                if all(a[(y & 7) * 0x800 + ((start + (y >> 3) * 80 + x) & 0x7FF)]
                       == b[(y & 7) * 0x800 + ((start + (y >> 3) * 80 + x) & 0x7FF)]
                       for x in range(80))]
        seen += len(same)
        bad += compare(m, b, play, same)
    return seen, bad


# --- 3. οι λωρίδες μετά από βήματα κάμερας --------------------------------
def straddles(cp):
    """Μια λωρίδα πατά το τύλιγμα του δαχτυλιδιού (το hud_move την κόβει στα δύο)."""
    return cp < 160 or 2048 - 1840 < cp <= 2048 - 1600

PATH = [2] * 8 + [1, 1, 3, 0, 1, 3, 3, 0, 2, 2, 1, 0, 0, 0]


def scenario_move(sym, patch=(), steps=40, paused=True):
    m = fresh(sym)
    if paused:
        m.poke(sym["UI_SPD"], 0)
    m.run_frames(30)
    for at, v in patch:
        m.poke(at, v)
    rnd = random.Random(8300)
    bad, wraps = [], 0
    for k in range(steps):
        to_loop(m, sym)
        ram = m.read_ram(0xC000, 0x4000)
        cp = hudread.cam_p(m, sym)
        before = hudread.band_lines(ram, cp)
        # Πρώτα οκτώ νότια: το cam_p περνά από το 56, το 216 και το 376, όπου
        # η πάνω και η κάτω λωρίδα πατούν το τύλιγμα. Μετά όλες οι κατευθύνσεις.
        d = PATH[k] if k < len(PATH) else rnd.choice([0, 1, 2, 3])
        tx, ty = m.peek(sym["CAM_TX"]), m.peek(sym["CAM_TY"])
        if (d == 1 and tx == 44) or (d == 3 and tx == 0xC0) \
                or (d == 2 and ty == 54) or (d == 0 and ty == 0xC0):
            d ^= 2                                  # το χείλος του κόσμου
        code = [0xF3, 0x3E, d, 0xCD, sym["VIEW_SCROLL"] & 255, sym["VIEW_SCROLL"] >> 8,
                0x18, 0xFE]
        m.run_code(PROBE, bytes(code), frames=40)
        ram = m.read_ram(0xC000, 0x4000)
        cp2 = hudread.cam_p(m, sym)
        after = hudread.band_lines(ram, cp2)
        wraps += straddles(cp) or straddles(cp2)
        diff = [y for y in before if before[y] != after[y]]
        if diff:
            bad.append((k, "NESW"[d], len(diff), diff[:4]))
        m.set_pc(sym["MAIN_LOOP"])
        m.run_frames(3)
    return bad, wraps


# --- 3β. το hud_move μόνο του, σε κάθε θέση του δαχτυλιδιού ---------------
def move_trial(m, sym, old, new, timed=False):
    """Το δαχτυλίδι γεμάτο γνωστά bytes, hud_move από το old στο new.
    -> (πόσα bytes των λωρίδων λάθος, us ή None)"""
    data = bytes(((o * 7 + ln * 3) & 255) for ln in range(8) for o in range(2048))
    m.write_ram(0xC000, data)
    m.poke(sym["CAM_P"], new & 255)
    m.poke(sym["CAM_P"] + 1, new >> 8)
    code = [0xF3, 0x11, old & 255, old >> 8,
            0xCD, sym["HUD_MOVE"] & 255, sym["HUD_MOVE"] >> 8, 0x18, 0xFE]
    us = None
    if timed:
        m.write_ram(PROBE, bytes(code))
        m.set_pc(PROBE)
        end, us = PROBE + len(code) - 2, 0
        while not (end <= m.pc <= end + 2):
            m.run_us(10)
            us += 10
    else:
        m.run_code(PROBE, bytes(code), frames=2)
    ram = m.read_ram(0xC000, 0x4000)
    bad = 0
    for ln in range(8):
        for off, n in ((hudread.TOP_OFF, hudread.TOP_BYTES), (hudread.BOT_OFF, hudread.BOT_BYTES)):
            for x in range(n):
                src, dst = (old + off + x) & 0x7FF, (new + off + x) & 0x7FF
                bad += ram[ln * 0x800 + dst] != data[ln * 0x800 + src]
    return bad, us


MOVE_CEIL = 18900                   # us, όλες οι θέσεις (μετρημένο: 17.680-18.820)


def scenario_ring(sym):
    """Ολες οι 512 θέσεις x 4 κατευθύνσεις· ο χρόνος σε 128 από αυτές."""
    m = fresh(sym)
    wrong, worst = [], 0
    for cp in range(0, 2048, 4):
        for d in (4, -4, 160, -160):
            timed = cp % 64 == 0 or (straddles(cp) and cp % 16 == 0)
            bad, us = move_trial(m, sym, cp, (cp + d) & 0x7FF, timed)
            if bad:
                wrong.append((cp, d, bad))
            if us:
                worst = max(worst, us)
    return wrong, worst


# --- 4. το κόστος ----------------------------------------------------------
def scenario_cost(sym):
    cnt = 0x3E80
    res = {}
    for ei in (0, 1):
        m = fresh(sym)
        code = [0xFB if ei else 0xF3,
                0x2A, cnt & 255, cnt >> 8, 0x23, 0x22, cnt & 255, cnt >> 8,
                0x7C, 0xB5, 0x20, 0xF5,
                0x2A, (cnt + 2) & 255, cnt >> 8, 0x23, 0x22, (cnt + 2) & 255, cnt >> 8, 0x18, 0xEC]
        m.write_ram(cnt, bytes(4))
        m.write_ram(PROBE, bytes(code))
        m.set_pc(PROBE)
        m.run_frames(200)
        b = m.read_ram(cnt, 4)
        res[ei] = b[0] | b[1] << 8 | b[2] << 16 | b[3] << 24
    return (1 - res[1] / res[0]) * 19968


def main():
    sym, _ = TG.build()

    # Τα pens της λωρίδας είναι τα χρώματα που λέει το §8.1 (έντονο κόκκινο,
    # πράσινο, λευκό): ο ίδιος ο πίνακας του παιχνιδιού, και το RGB του εξομοιωτή.
    m = fresh(sym)
    pal = m.palette()
    near = [min(range(32), key=lambda h: sum((a - b) ** 2 for a, b in zip(pal[h], FW_RGB[f])))
            for f in BAND_FW]
    isp = [m.peek(sym["IS_PAL"] + i) & 0x1F for i in range(9)]
    check(near == BAND_HW and isp[0:3] == BAND_HW[1:] and isp[6:9] == BAND_HW[1:]
          and isp[3:6] == play_pens(m, sym)[1:4],
          f"τα pens 1-3: λωρίδα {[hex(v) for v in isp[0:3]]} / {[hex(v) for v in isp[6:9]]} "
          f"(έντονο κόκκινο, πράσινο, λευκό), κάδρο {[hex(v) for v in isp[3:6]]} = palette_fw")

    blank, bad = scenario_pattern(sym)
    check(not blank and not bad,
          f"μοτίβο, 24 δείγματα με ex (sp),hl και nop: κάθε pixel των 200 γραμμών είναι η "
          f"μνήμη με το mode και τα pens της θέσης του"
          + (f" — μη κενές: {blank}" if blank else "")
          + (f" — {len(bad)} γραμμές λάθος, π.χ. {bad[:4]}" if bad else ""))

    wrong = scenario_resync(sym)
    check(wrong == 0, f"16 φορές κλειστές διακοπές για 1-56 ms και μετά is_on: το πρώτο ολόκληρο "
                      f"frame μετά το VSYNC σωστό σε κάθε pixel ({wrong} με λάθος)")

    seen, bad = scenario_live(sym)
    check(seen > 4000 and not bad,
          f"το παιχνίδι στο x4, 60 frames: {seen} σταθερές γραμμές, όλες όπως η μνήμη"
          + (f" — {len(bad)} λάθος, π.χ. {bad[:4]}" if bad else ""))

    for paused in (True, False):
        bad, wraps = scenario_move(sym, paused=paused)
        check(not bad and wraps > 0,
              f"40 βήματα κάμερας {'σε παύση' if paused else 'με το παιχνίδι να τρέχει'}"
              f" ({wraps} με τύλιγμα μέσα σε λωρίδα): οι 40 γραμμές των λωρίδων ίδιες πριν "
              f"και μετά" + (f" — {bad[:3]}" if bad else ""))

    wrong, worst = scenario_ring(sym)
    check(not wrong and worst <= MOVE_CEIL,
          f"hud_move σε όλες τις 512 θέσεις του δαχτυλιδιού, ±4 και ±160: κάθε byte των "
          f"λωρίδων στη θέση του, το πολύ {worst} us (ταβάνι {MOVE_CEIL}· ως το βήμα 82 "
          f"το ίδιο βήμα κόστιζε ~19.500 us ξαναγράφοντας τις σειρές 3-4)"
          + (f" — λάθος: {wrong[:4]}" if wrong else ""))

    us = scenario_cost(sym)
    check(us <= COST_CEIL, f"η διακοπή παίρνει {us:.0f} us ανά frame (ταβάνι {COST_CEIL})")

    # --- ΑΡΝΗΤΙΚΑ ---------------------------------------------------------
    top, bot = sym["IS_TOP"], sym["IS_BOT"]
    m = fresh(sym)
    code = m.read_ram(top, 16)
    rst = top + code.index(bytes([0x01, 0x9C, 0x7F]))            # ld bc,#7F9C
    assert m.peek(top + 2) == 0x3E and m.peek(bot + 2) == 0x3E, "ld a,N στη θέση 2"
    wt, wb = m.peek(top + 3), m.peek(bot + 3)
    neg = [("χωρίς τον μηδενισμό του μετρητή", [(rst + 1, 0x8C)]),
           ("το πάνω σπάσιμο 48 us νωρίτερα", [(top + 3, wt - 12)]),
           ("το πάνω σπάσιμο 20 us αργότερα", [(top + 3, wt + 5)]),
           ("το κάτω σπάσιμο 20 us νωρίτερα", [(bot + 3, wb - 5)]),
           ("το κάτω σπάσιμο 48 us αργότερα", [(bot + 3, wb + 12)])]
    for label, patch in neg:
        blank, bad = scenario_pattern(sym, patch, samples=8)
        check(bool(bad), f"ΑΡΝΗΤΙΚΟ: {label} — {len(bad)} γραμμές λάθος"
                         + (f", π.χ. {bad[:2]}" if bad else ""))
    wrong = scenario_resync(sym, on=False)
    check(wrong > 0, f"ΑΡΝΗΤΙΚΟ: με σκέτο ei αντί για is_on, {wrong} από 16 φορές με λάθος "
                     f"pixel στο ίδιο frame")
    won = sym["ION_W"] - 1
    assert m.peek(won - 1) == 0x3E, "ld a,IS_WON πριν από το ion_w"
    wrong = scenario_resync(sym, patch=[(won, 60)])
    check(wrong > 0, f"ΑΡΝΗΤΙΚΟ: με το is_on να μηδενίζει μετά τη γραμμή 266 (60 βρόχοι), "
                     f"{wrong} από 16 φορές με λάθος pixel")
    bad, _ = scenario_move(sym, [(sym["HUD_MOVE"], 0xC9)], steps=6)
    check(bool(bad), f"ΑΡΝΗΤΙΚΟ: χωρίς hud_move οι λωρίδες αλλάζουν ({len(bad)} από 6 βήματα)")
    # Το λάθος που βρήκε αυτή η δοκιμή στο βήμα 83: ένα «or a» στο τέλος του
    # hm_chunk έσβηνε το Z της αφαίρεσης, και κάθε λωρίδα σταματούσε στο πρώτο
    # της κομμάτι. Το ίδιο εδώ: το «ret z» μετά από κάθε «call hm_chunk» γίνεται ret.
    m = fresh(sym)
    ch = bytes([0xCD, sym["HM_CHUNK"] & 255, sym["HM_CHUNK"] >> 8, 0xC8])
    for lab in ("HM_FWD", "HM_BACK"):
        at = sym[lab] + m.read_ram(sym[lab], 60).index(ch)
        m.poke(at + 3, 0xC9)
    wrong = sum(move_trial(m, sym, cp, (cp + d) & 0x7FF)[0] > 0
                for cp in (56, 216, 1944, 100) for d in (4, 160, -4, -160))
    check(wrong > 0, f"ΑΡΝΗΤΙΚΟ: μόνο το πρώτο κομμάτι κάθε λωρίδας — {wrong} από 16 βήματα "
                     f"κοντά στο τύλιγμα λάθος")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
