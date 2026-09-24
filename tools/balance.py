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


def clear_spots(size=3, n=4):
    """Θέσεις κέρσορα όπου το bd_ok του src/build.asm λέει ναι, από το ΙΔΙΟ
    επίπεδο κόσμου που θα δει το παιχνίδι (build/world_new.bin).

    Επιστρέφει ΠΛΑΚΙΔΙΑ (το πάνω-αριστερά του αποτυπώματος), όχι κέρσορες: ο
    κέρσορας βγαίνει από το πλακίδιο και το πλάτος του αντικειμένου, και δύο
    αντικείμενα με διαφορετικό πλάτος πρέπει να μπορούν να μοιραστούν την ίδια
    λίστα χωρίς να πέσουν το ένα πάνω στο άλλο. `size` = η μεγαλύτερη πλευρά
    που θα χωρέσει εκεί (4 για ορυχείο και θόλο, 3 για τις ενεργειακές). Το βήμα «περπάτα δεξιά ώσπου να ανάψει πράσινο»
    έψαχνε στα τυφλά και κόλλαγε στον κρατήρα: εδώ ο έλεγχος είναι ο κανόνας
    του παιχνιδιού — έδαφος, σκόνη ή θεμέλιο, και όλα τα tiles. Η αποικία του
    §10.1 κάθεται μέσα στο θεμέλιο -4..4, οπότε οι θέσεις ζητούνται ΕΞΩ από
    αυτό: εκεί δεν υπάρχει τίποτα κατειλημμένο που να μην το ξέρουμε.
    """
    import world as W
    plane = open(os.path.join(ROOT, "build", "world_new.bin"), "rb").read()
    ok = {W.GROUND, W.DUST, W.FOUNDATION}

    def good(tx, ty):
        # ΟΛΟ το αποτύπωμα έξω από την αποικία: το επίπεδο κόσμου δεν ξέρει
        # τίποτα για τα κατειλημμένα πλακίδια που έστρωσε το newgame, και ένα
        # δαχτυλίδι που μετριέται από την ΠΑΝΩ-ΑΡΙΣΤΕΡΗ γωνία φτάνει άνετα
        # πάνω στους θόλους με την κάτω-δεξιά του.
        if any(max(abs(tx + i), abs(ty + j)) < 12
               for i in range(size) for j in range(size)):
            return False
        return all(W.cls_of(plane[W.index(tx + i, ty + j)]) in ok
                   for i in range(size) for j in range(size))

    out = []
    for r in range(12, 30):                  # δαχτυλίδια γύρω από την αποικία
        for ty in range(-r, r + 1):
            for tx in range(-r, r + 1):
                if max(abs(tx), abs(ty)) != r or not good(tx, ty):
                    continue
                if any(abs(tx - x) < size + 1 and abs(ty - y) < size + 1
                       for x, y in out):
                    continue
                out.append((tx, ty))
                if len(out) >= n:
                    return out
    return out


def build(m, sym, item, g_metal, at=None, room=None):
    """Ο,τι κάνει το tests/test_game.py: κατάλογος, θέση, FIRE.

    `item` = σειρά στον κατάλογο του src/build.asm (0-2 θόλοι, 4 = SOLAR,
    7 = EXTRACTOR, 8 = MINE), `room` = σειρά στον κατάλογο δωματίων του
    src/rooms.asm για θόλο (0 = OXYGEN, 3 = GREENHOUSE, 4 = FACTORY).
    `at` = (cur_hx, cur_hy) σε μισά tiles, από το clear_spots().
    """
    from cpc import KEY_SPACE, KEY_RIGHT, KEY_DOWN, JOY_FIRE

    # ΠΕΝΤΕ FRAMES ΠΑΤΗΜΕΝΟ, ΟΧΙ ΤΡΙΑ. Μια αλλαγή δωματίου ξαναγράφει τις δύο
    # σειρές του πίνακα (~15.000 us, τα τρία τέταρτα ενός frame), οπότε το
    # ui_tick της επόμενης εικόνας αργεί και ένα πάτημα τριών frames χάνεται
    # ολόκληρο. Ο άνθρωπος κρατά ένα πλήκτρο εκατό χιλιοστά· το σενάριο πρέπει
    # να κάνει το ίδιο.
    def tap(key, n=1):
        for _ in range(n):
            m.key_down(key)
            m.run_frames(5)
            m.key_up(key)
            m.run_frames(8)

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
    tap(KEY_SPACE)                       # -> MENU
    # Ο κατάλογος ΘΥΜΑΤΑΙ πού έμεινε: μετά τον ηλιακό το ui_sel είναι 4, όχι 0.
    # ΕΝΑ ΠΑΤΗΜΑ ΤΗ ΦΟΡΑ, ΜΕ ΕΠΑΛΗΘΕΥΣΗ: ένα χαμένο δεξιά αφήνει τον κατάλογο
    # σε δομή αντί για θόλο, και τότε το πάνω-κάτω δεν κάνει τίποτα — η
    # αποτυχία φαινόταν σαν «το δωμάτιο δεν κλείδωσε» δώδεκα πατήματα αργότερα.
    for _ in range(14):
        if m.peek(sym["UI_SEL"]) == item:
            break
        tap(KEY_RIGHT)
    assert m.peek(sym["UI_SEL"]) == item, (
        f"το αντικείμενο δεν κλείδωσε: ui_sel={m.peek(sym['UI_SEL'])} "
        f"αντί για {item}")
    if room is not None:
        # ΜΕ ΕΠΑΛΗΘΕΥΣΗ: ένα πάτημα που πέφτει πάνω στην επανασχεδίαση του
        # πίνακα χάνεται, και ένα δωμάτιο λάθος είναι ένας θόλος που φτιάχνει
        # άλλο πράγμα — το σενάριο νόμιζε ότι μετρούσε θερμοκήπιο και μετρούσε
        # εργοστάσιο.
        for _ in range(12):
            d = (room - m.peek(sym["BD_RSEL"])) % 10
            if not d:
                break
            tap(KEY_DOWN)
        assert m.peek(sym["BD_RSEL"]) == room, (
            f"το δωμάτιο δεν κλείδωσε: bd_rsel={m.peek(sym['BD_RSEL'])} "
            f"αντί για {room} (είδος {m.peek(sym['BD_KIND'])}, "
            f"μέγεθος {m.peek(sym['BD_PARAM'])})")
    # Ο ΚΕΡΣΟΡΑΣ ΤΕΛΕΥΤΑΙΟΣ: κάθε αλλαγή αντικειμένου τον κουμπώνει στην
    # ισοτιμία του πλάτους (§3.4), οπότε ένα poke πριν από τον κατάλογο
    # μετακινείται από κάτω του.
    if at:
        m.poke(sym["CUR_HX"], at[0] & 0xFF)
        m.poke(sym["CUR_HY"], at[1] & 0xFF)
    m.key_up("\x01")
    m.set_joystick_type(1)
    for _ in range(4):                   # -> PLACE, όσα FIRE χρειαστούν
        if m.peek(sym["UI_STATE"]) == 2:
            break
        stick(JOY_FIRE)
    metal0 = m.peek(g_metal) | (m.peek(g_metal + 1) << 8)
    stick(JOY_FIRE)                      # -> τοποθέτηση
    m.set_joystick_type(0)
    m.run_frames(30)
    metal1 = m.peek(g_metal) | (m.peek(g_metal + 1) << 8)
    if metal1 == metal0:
        print(f"  ΠΡΟΣΟΧΗ: το κτίσμα {item} ΔΕΝ μπήκε (μέταλλο {metal0}, "
              f"ui_bad={m.peek(sym['UI_BAD'])})", flush=True)
    return metal1 != metal0


def run(name, sym, g, snapshot, sols=8, items=(), speed=4):
    """`items` = λίστα από `item` ή `(item, δωμάτιο)`."""
    m = boot(sym, snapshot)
    # RICH=1: υλικά από το πουθενά, ΜΟΝΟ για να δοκιμαστεί ο μηχανισμός μιας
    # αλυσίδας που το απόθεμα του §10.1 δεν φτάνει ακόμη να αγοράσει.
    # 500, όχι 200: το σενάριο με τα δύο πλοία χτίζει εννιά πράγματα και τα
    # 200 τελείωναν στο όγδοο — το κυλικείο ΔΕΝ ΜΠΑΙΝΕ και η μέτρηση έλεγε
    # «η αλυσίδα της τροφής δεν δουλεύει» ενώ έλειπε ο θόλος που φτιάχνει τα
    # γεύματα. Το ταβάνι αποθέματος είναι 600 (EC_CAP).
    if os.environ.get("RICH"):
        for k in (3, 4):
            m.poke(g + EC["STOCK"] + k * 2, 500 & 255)
            m.poke(g + EC["STOCK"] + k * 2 + 1, 500 >> 8)
    # ΜΙΑ λίστα θέσεων για όλα: αλλιώς ένα 3x3 και ένα 4x4 διαλέγουν το ίδιο
    # σημείο του κόσμου και το δεύτερο βρίσκει κατειλημμένο έδαφος.
    spots = clear_spots(6, 10)           # 6 = ο μεσαίος θόλος, το φαρδύτερο
    k = 0
    for it in items:                      # που χτίζει κανένα σενάριο
        if it == "C":                     # κάλεσε πλοίο αποίκων (§6.11)
            # ΠΡΩΤΑ ΝΑ ΧΤΙΣΤΕΙ Η ΑΙΘΟΥΣΑ ΕΛΕΓΧΟΥ: το ταβάνι πληθυσμού ανεβαίνει
            # όταν ο θόλος γίνει DS_ACTIVE, και ως τότε το πλοίο θα προσγειωνόταν
            # άδειο — το ui_ship δεν το αφήνει καν να φύγει.
            for _ in range(60):
                if m.peek(g + EC["POPCAP"]) > 4:
                    break
                m.run_frames(100)
            # ΚΑΙ ΣΤΗΝ ΗΡΕΜΗ ΚΑΤΑΣΤΑΣΗ: το C το διαβάζει μόνο το LOOK, και μετά
            # από ένα χτίσιμο η διεπαφή μένει στο PLACE.
            m.set_joystick_type(1)
            for _ in range(2):
                m.joystick(0x20)
                m.run_frames(4)
                m.joystick(0)
                m.run_frames(10)
            m.set_joystick_type(0)
            m.key_down("C")
            m.run_frames(6)
            m.key_up("C")
            m.run_frames(1500)            # ταξίδι 24 περιστροφές + προσγείωση
            continue
        item, room = it if isinstance(it, tuple) else (it, None)
        w = (4, 6, 8)[item] if item <= 2 else (4 if item == 8 else 3)
        tx, ty = spots[k]
        k += 1
        at = (2 * tx + w, 2 * ty + w)
        build(m, sym, item, g + EC["STOCK"] + 3 * 2, at=at, room=room)
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
            stock=[w16(g + EC["STOCK"] + i * 2) for i in range(14)],
            pwr=w16(g + EC["PSTORE"]), cap=w16(g + EC["PCAP"]),
            pp=w16(g + EC["PPROD"]), pu=w16(g + EC["PUSE"]),
            o2p=w16(g + EC["O2PROD"]), o2u=w16(g + EC["O2USE"]),
            pok=m.peek(g + EC["POK"]), o2ok=m.peek(g + EC["O2OK"]),
            popcap=m.peek(g + EC["POPCAP"]),
            over=m.peek(g + EC["GAMEOVER"])))
        if alive < 4 and dead_at is None:
            dead_at = frames
        if rows[-1]["over"]:
            break
    return rows, dead_at


def report(name, rows, dead_at):
    print(f"\n=== {name} ===")
    print(f"{'sol':>4s} {'ζωντ':>5s} {'νερό':>6s} {'τροφή':>6s} "
          f"{'ρεύμα π/κ':>10s} {'μπατ':>5s} {'μετ/μέτ':>8s} "
          f"{'O2 π/κ':>8s}  σημειώσεις")
    last = None
    for r in rows:
        note = []
        if not r["pok"]:
            note.append("χωρίς ρεύμα")
        if not r["o2ok"]:
            note.append("χωρίς οξυγόνο")
        if r["over"]:
            note.append("ΤΕΛΟΣ")
        key = (r["sol"], r["alive"], r["stock"][0] // 5,
               r["stock"][3] // 5, tuple(note))
        if key != last:
            print(f"{r['sol']:4d} {r['alive']:5d} {r['stock'][0]:6d} "
                  f"{r['stock'][1]:6d} {r['pp']:4d}/{r['pu']:<5d} "
                  f"{r['pwr']:5d} {r['stock'][2]:3d}/{r['stock'][3]:<4d} "
                  f"{r['o2p']:3d}/{r['o2u']:<4d}  {', '.join(note)}")
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
    scen = [("τίποτα", ()),
            ("ένας ηλιακός", (4,)),
            ("ηλιακός + αντλία", (4, 7)),
            ("ηλιακός + μπαταρία", (4, 6)),
            ("ηλιακός + ανεμογεννήτρια", (4, 5)),
            ("ηλιακός + μπαταρία + αντλία", (4, 6, 7)),
            ("ηλιακός + αντλία + εργοστάσιο", (4, 7, (0, 4))),
            ("και συλλέκτης: ό,τι ακριβώς αγοράζει το §10.1",
             (4, 7, 6, (0, 4))),
            # Η αλυσίδα της τροφής, με RICH=1: τρεις θόλοι που το άνοιγμα δεν
            # αγοράζει ακόμη — θερμοκήπιο για άμυλο και λαχανικά, εργαστήριο
            # για κρέας, κυλικείο για γεύματα.
            ("τροφή: θερμοκήπιο + εργαστήριο + κυλικείο",
             (4, 4, 7, 6, (1, 3), (0, 5), (0, 1))),
            # Και με ΚΟΣΜΟ: η αλυσίδα της τροφής θέλει επτά χειριστές και η
            # αποικία του §10.1 έχει τέσσερις κατοίκους συνολικά.
            # ΚΑΙ ΟΞΥΓΟΝΟ ΓΙΑ ΟΛΟΥΣ: μια γεννήτρια βγάζει 20 και κάθε άποικος
            # αναπνέει 2 (§6.5), άρα δώδεκα κάτοικοι θέλουν δεύτερο θόλο
            # οξυγόνου πριν καν φτάσει το πλοίο.
            ("τροφή με δύο πλοία αποίκων",
             (4, 4, 7, 6, (0, 0), (0, 7), "C", "C",
              (1, 3), (1, 5), (0, 1)))]
    pick = os.environ.get("SCEN")
    if pick:
        scen = [scen[int(i)] for i in pick.split(",")]
    for name, items in scen:
        rows, dead = run(name, sym, g, T.SNA, sols=sols, items=items)
        report(name, rows, dead)
    return 0


if __name__ == "__main__":
    sys.exit(main())
