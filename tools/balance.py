#!/usr/bin/env python3
"""Η ΚΑΜΠΥΛΗ ΜΙΑΣ ΑΠΟΙΚΙΑΣ — τι γίνεται αν αφήσεις το παιχνίδι να τρέξει.

Το §15 λέει για την ισορροπία: «Certain. Κάθε νούμερο του §6.5 είναι πρώτη
εικασία». Οι δοκιμές ως τώρα ελέγχουν ότι ο μηχανισμός δουλεύει — ότι το νερό
πέφτει, ότι το κτίριο τελειώνει — όχι ότι τα ΝΟΥΜΕΡΑ βγάζουν παιχνίδι. Αυτό
εδώ τα μετράει: τρέχει το ΚΑΝΟΝΙΚΟ binary στον εξομοιωτή, με ταχύτητα x4, και
δειγματίζει την οικονομία κάθε λίγα δευτερόλεπτα.

Δύο σενάρια:

  «τίποτα»  ο παίκτης δεν αγγίζει τίποτα. Η αποικία του §10.1 ξεκινά χωρίς
            ρεύμα, άρα χωρίς οξυγόνο: πόση ώρα έχει ο παίκτης πριν αρχίσουν
            οι θάνατοι, και τι τους σκοτώνει;
  «ηλιακός» ο παίκτης χτίζει ΕΝΑ ηλιακό πάνελ, όπως στο tests/test_game.py.
            Φτάνει ένα για να γυρίσει το οξυγόνο; Και μετά τι τελειώνει;
  «+αντλία» και μια αντλία νερού από πάνω, χτισμένη με τον ίδιο τρόπο.
  «+μπαταρία» / «+ανεμογεννήτρια» οι δύο απαντήσεις του §6.10 στη νύχτα: ο
            ηλιακός σβήνει το 40% του sol και άλλο τόσο στις αμμοθύελλες.

Το απόθεμα του §10.1 αγοράζει ΔΥΟ κτίσματα. Ποια δύο, είναι το παιχνίδι.
Με SCEN=0,3 τρέχουν μόνο τα σενάρια 0 και 3 της λίστας.

Ενα sol είναι 12.000 frames προσομοίωσης (§10.4)· στο x4 αυτό είναι ~3.200
πραγματικά frames, δηλαδή ~64 δευτερόλεπτα εξομοίωσης ανά sol.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, "/home/vasilhs/cpcemu")

EC = dict(STOCK=0, PSTORE=28, PCAP=30, PPROD=32, PUSE=34, O2PROD=38,
          O2USE=40, POK=46, O2OK=47,
          DAY=49, SOL=51, ALIVE=58, GAMEOVER=59, STORM=61, POPCAP=74)
NAMES = ["νερό", "τροφή", "μετάλλ.", "μέταλλο", "βιοπλ.", "επεξ.",
         "ανταλ.", "φάρμακα", "όπλα", "ρομπότ"]


def boot(sym, snapshot):
    from cpc import CPC
    m = CPC()
    m.run_frames(60)
    assert m.quickload(snapshot), "quickload απέτυχε"
    m.run_frames(250)
    return m


def clear_spots(n=4):
    """Θέσεις κέρσορα όπου το bd_ok του src/build.asm λέει ναι, από το ΙΔΙΟ
    επίπεδο κόσμου που θα δει το παιχνίδι (build/world_new.bin).

    Το βήμα «περπάτα δεξιά ώσπου να ανάψει πράσινο» έψαχνε στα τυφλά και
    κόλλαγε στον κρατήρα: εδώ ο έλεγχος είναι ο κανόνας του παιχνιδιού —
    έδαφος, σκόνη ή θεμέλιο, και τα εννιά tiles. Η αποικία του §10.1 κάθεται
    μέσα στο θεμέλιο -4..4, οπότε οι θέσεις ζητούνται ΕΞΩ από αυτό: εκεί δεν
    υπάρχει τίποτα κατειλημμένο που να μην το ξέρουμε.
    """
    import world as W
    plane = open(os.path.join(ROOT, "build", "world_new.bin"), "rb").read()
    ok = {W.GROUND, W.DUST, W.FOUNDATION}

    def good(tx, ty):
        return all(W.cls_of(plane[W.index(tx + i, ty + j)]) in ok
                   for i in range(3) for j in range(3))

    out = []
    for r in range(6, 20):                  # δαχτυλίδια γύρω από την αποικία
        for ty in range(-r, r + 1):
            for tx in range(-r, r + 1):
                if max(abs(tx), abs(ty)) != r or not good(tx, ty):
                    continue
                if any(abs(tx - x) < 4 and abs(ty - y) < 4 for x, y in out):
                    continue
                out.append((tx, ty))
                if len(out) >= n:
                    # κέρσορας = κέντρο: left_tile = (cur_hx - 3) / 2
                    return [(2 * x + 3, 2 * y + 3) for x, y in out]
    return [(2 * x + 3, 2 * y + 3) for x, y in out]


def build(m, sym, item, g_metal, at=None):
    """Ο,τι κάνει το tests/test_game.py: κατάλογος, θέση, FIRE.

    `item` = σειρά στον κατάλογο του src/build.asm (4 = SOLAR, 7 = EXTRACTOR).
    `at` = (cur_hx, cur_hy) σε μισά tiles, από το clear_spots().
    """
    from cpc import KEY_SPACE, KEY_RIGHT, JOY_FIRE

    def tap(key, n=1):
        for _ in range(n):
            m.key_down(key)
            m.run_frames(3)
            m.key_up(key)
            m.run_frames(4)

    def stick(mask, n=1):
        for _ in range(n):
            m.joystick(mask)
            m.run_frames(4)
            m.joystick(0)
            m.run_frames(10)

    # ΠΙΣΩ ΣΤΗΝ ΑΡΧΙΚΗ ΚΑΤΑΣΤΑΣΗ ΠΡΩΤΑ. Μετά από μια τοποθέτηση η διεπαφή
    # ΜΕΝΕΙ στο PLACE (uip_after -> ui_show), οπότε το SPACE του επόμενου
    # κτισίματος ήταν ένα ακόμη FIRE: το σενάριο «ηλιακός + αντλία» έχτιζε δύο
    # ηλιακά και καμία αντλία. Το fire 2 του χειριστηρίου είναι η ακύρωση.
    m.set_joystick_type(1)
    stick(0x20, 2)                       # PLACE -> MENU -> ήρεμη κατάσταση
    m.set_joystick_type(0)
    if at:
        m.poke(sym["CUR_HX"], at[0] & 0xFF)
        m.poke(sym["CUR_HY"], at[1] & 0xFF)
    tap(KEY_SPACE)                       # -> MENU
    # Ο κατάλογος ΘΥΜΑΤΑΙ πού έμεινε: μετά τον ηλιακό το ui_sel είναι 4, όχι 0.
    tap(KEY_RIGHT, (item - m.peek(sym["UI_SEL"])) % 11)
    m.key_up("\x01")
    m.set_joystick_type(1)
    stick(JOY_FIRE)                      # -> PLACE
    metal0 = m.peek(g_metal) | (m.peek(g_metal + 1) << 8)
    stick(JOY_FIRE)                      # -> τοποθέτηση
    m.set_joystick_type(0)
    m.run_frames(30)
    metal1 = m.peek(g_metal) | (m.peek(g_metal + 1) << 8)
    if metal1 == metal0:
        print(f"  ΠΡΟΣΟΧΗ: το κτίσμα {item} ΔΕΝ μπήκε (μέταλλο {metal0}, "
              f"ui_bad={m.peek(sym['UI_BAD'])})")
    return metal1 != metal0


def run(name, sym, g, snapshot, sols=8, items=(), speed=4, spots=()):
    m = boot(sym, snapshot)
    for k, item in enumerate(items):
        build(m, sym, item, g + EC["STOCK"] + 3 * 2, at=spots[k])
    m.poke(sym["UI_SPD"], speed)

    def w16(a):
        return m.peek(a) | (m.peek(a + 1) << 8)

    rows, frames = [], 0
    # x4 = 3,76 φορές το ονομαστικό (§9.1): τόσα πραγματικά frames ανά sol
    per_sol = int(12000 / 3.76)
    step = per_sol // 6
    dead_at = None
    while frames < sols * per_sol:
        m.run_frames(step)
        frames += step
        alive = m.peek(g + EC["ALIVE"])
        rows.append(dict(
            f=frames, sol=m.peek(g + EC["SOL"]), alive=alive,
            stock=[w16(g + EC["STOCK"] + i * 2) for i in range(10)],
            pwr=w16(g + EC["PSTORE"]), cap=w16(g + EC["PCAP"]),
            pp=w16(g + EC["PPROD"]), pu=w16(g + EC["PUSE"]),
            o2p=w16(g + EC["O2PROD"]), o2u=w16(g + EC["O2USE"]),
            pok=m.peek(g + EC["POK"]), o2ok=m.peek(g + EC["O2OK"]),
            over=m.peek(g + EC["GAMEOVER"])))
        if alive < 4 and dead_at is None:
            dead_at = frames
        if rows[-1]["over"]:
            break
    return rows, dead_at


def report(name, rows, dead_at):
    print(f"\n=== {name} ===")
    print(f"{'sol':>4s} {'ζωντ':>5s} {'νερό':>6s} {'τροφή':>6s} "
          f"{'ρεύμα π/κ':>10s} {'μπατ':>5s} {'O2 π/κ':>8s}  σημειώσεις")
    last = None
    for r in rows:
        note = []
        if not r["pok"]:
            note.append("χωρίς ρεύμα")
        if not r["o2ok"]:
            note.append("χωρίς οξυγόνο")
        if r["over"]:
            note.append("ΤΕΛΟΣ")
        key = (r["sol"], r["alive"], r["stock"][0] // 5, tuple(note))
        if key != last:
            print(f"{r['sol']:4d} {r['alive']:5d} {r['stock'][0]:6d} "
                  f"{r['stock'][1]:6d} {r['pp']:4d}/{r['pu']:<5d} "
                  f"{r['pwr']:5d} {r['o2p']:3d}/{r['o2u']:<4d}  {', '.join(note)}")
            last = key
    if dead_at:
        print(f"πρώτος θάνατος στα {dead_at} πραγματικά frames "
              f"= {dead_at / 50:.0f} s παιχνιδιού στο x4")
    else:
        print("κανένας θάνατος")


def main():
    import test_game as T
    sym, g = T.build()
    sols = int(os.environ.get("SOLS", "6"))
    spots = clear_spots()
    print("θέσεις κτισίματος (μισά tiles):", spots)
    scen = [("τίποτα", ()),
            ("ένας ηλιακός", (4,)),
            ("ηλιακός + αντλία", (4, 7)),
            ("ηλιακός + μπαταρία", (4, 6)),
            ("ηλιακός + ανεμογεννήτρια", (4, 5)),
            ("ηλιακός + μπαταρία + αντλία", (4, 6, 7))]
    pick = os.environ.get("SCEN")
    if pick:
        scen = [scen[int(i)] for i in pick.split(",")]
    for name, items in scen:
        rows, dead = run(name, sym, g, T.SNA, sols=sols, items=items,
                         spots=spots)
        report(name, rows, dead)
    return 0


if __name__ == "__main__":
    sys.exit(main())
