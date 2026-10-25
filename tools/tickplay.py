#!/usr/bin/env python3
"""Ενα play με τον χρόνο του ΤΡΟΧΟΥ, όχι των frames (βήμα 172).

    python3 tools/tickplay.py --seed 0x5A5A --planet 2 --sols 120 --json out.json

Το snapshot του κόσμου το φτιάχνει το `tools/play.py --make`, όπως και για το
play.py. Ο παίκτης και τα σχέδιά του είναι του play.py («big»).

ΓΙΑΤΙ. Το play.py τρέχει frames, και ο βρόχος γυρίζει τον τροχό μία φορά ανά
γύρο του (src/main.asm): ένας γύρος με πολλή σχεδίαση κρατά δύο frames και ο
τροχός κάνει μία θέση αντί για δύο. Μια αλλαγή που κάνει τη σχεδίαση
φθηνότερη ή ακριβότερη, χωρίς να αγγίξει τη λογική, βγάζει άλλο play: στο
βήμα 172 τα plays του play.py χώρισαν από το δεύτερο γεγονός (sol 0,19 αντί
για 0,20). Εδώ η σχεδίαση δεν μετρά:

- ο βρόχος τρέχει πάντα σε παύση (ui_spd 0): σχεδιάζει και διαβάζει τα
  πλήκτρα, αλλά δεν γυρίζει τον τροχό·
- τον χρόνο τον προχωρά ένα πρόγραμμα στο #3E80 (το δάπεδο των δοκιμών),
  `call wheel_tick` N φορές, όταν ο βρόχος περιμένει το VSYNC — στο G.run,
  4 ticks για κάθε frame που θα έτρεχε το play.py στο x4·
- πριν από κάθε πάτημα ο βρόχος ησυχάζει: στο VSYNC, χωρίς λίστα, χωρίς
  αναδόμηση, χωρίς φάντασμα που περιμένει. Αλλιώς ένα πάτημα 5 frames έπεφτε
  μέσα σε έναν μακρύ γύρο σχεδίασης («το αντικείμενο δεν κλείδωσε»)·
- η αρχή στο ίδιο tick: η εκκίνηση (250 frames) γυρίζει τον τροχό ανά γύρο,
  και στο 5A5A 2 η μία έκδοση ξεκινούσε μία θέση μπροστά. Ο τροχός μόνος του
  ως το tick 1.024 και τη θέση 0·
- το speed_probe (frames στο x1 και x4) δεν τρέχει.

Ετσι δύο εκδόσεις με την ίδια λογική δίνουν το ίδιο play, γεγονός προς
γεγονός, και σε κάθε δείγμα το ίδιο hash της κατάστασης (`hashes` στο JSON):
πεδία, θόλοι, δομές, θέσεις, ο χάρτης των εισβολέων, EC_X, η οικονομία και ο
πίνακας εργασιών, οι διάδρομοι, το worldinfo, η θέση του τροχού. Σε κανονική
μορφή, για να συγκρίνονται εκδόσεις με άλλη διάταξη μνήμης: όποιο βήμα την
αλλάζει, αλλάζει και το canon() εδώ.
"""
import argparse, hashlib, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [HERE, os.path.join(ROOT, "tests"), "/home/vasilhs/cpcemu"]
import play as P                                          # noqa: E402
import entity as E                                        # noqa: E402

DRV = 0x3E80                    # το δάπεδο των δοκιμών (src/main.asm)
START = 1024                    # το tick όπου αρχίζει ο παίκτης


class Ticks:
    def __init__(self, seed, planet):
        self.sym, g = P.syms()
        self.G = P.Game(self.sym, g, P.sna_path(seed, planet, False))
        self.m, sym = self.G.m, self.sym
        self.lo, self.hi, self.top = sym["ML_LOW"], sym["ML_HIGH"] + 5, sym["MAIN_LOOP"]
        self.quiet = [sym["RV_PEND"], sym["UI_OWED"], sym["DIRTY_NUM"]]
        wt = sym["WHEEL_TICK"]
        # di · ld b,N · push bc · call wheel_tick · pop bc · djnz · jr $
        self.m.write_ram(DRV, bytes([0xF3, 0x06, 0, 0xC5, 0xCD, wt & 255, wt >> 8, 0xC1,
                                     0x10, 0xF9, 0x18, 0xFE]))
        self.ticks, self.loud, self.hashes = 0, 0, []
        self.ly = P.layout()
        kd, js = self.m.key_down, self.m.joystick

        def key_down(key):
            self.settle()
            return kd(key)

        def joystick(mask):
            if mask:
                self.settle()
            return js(mask)
        self.m.key_down, self.m.joystick = key_down, joystick

    def idle(self):
        return self.lo <= self.m.pc < self.hi

    def settle(self):
        for _ in range(4000):
            if self.idle() and not any(self.m.peek(a) for a in self.quiet):
                return
            self.m.run_us(500)
        self.loud += 1

    def advance(self, n):
        """n θέσεις του τροχού, με τον βρόχο στο VSYNC και σε παύση."""
        m = self.m
        m.poke(self.sym["UI_SPD"], 0)
        while n:
            for _ in range(20000):
                if self.idle():
                    break
                m.run_us(64)
            else:
                raise RuntimeError(f"ο βρόχος δεν έφτασε στο VSYNC, PC=#{m.pc:04X}")
            b = min(n, 255)
            m.poke(DRV + 2, b)
            m.set_pc(DRV)
            for _ in range(4000):
                if m.pc == DRV + 10:
                    break
                m.run_us(20000)
            else:
                raise RuntimeError(f"ο τροχός κόλλησε, PC=#{m.pc:04X}")
            m.set_pc(self.top)
            n -= b
            self.ticks += b

    def start(self):
        m, G = self.m, self.G
        m.poke(self.sym["UI_SPD"], 0)
        self.settle()
        t0 = G.ticks()
        assert t0 < START, t0
        self.advance(START - t0)
        while m.peek(self.sym["WH_SLOT"]):      # το EC_FRAME μετρά ανά περιστροφή
            self.advance(1)
        self.settle()
        return t0

    def canon(self):
        """Η κατάσταση της προσομοίωσης, ανεξάρτητη από τη διάταξη (βήμα 172)."""
        G, ly = self.G, self.ly
        b6 = bytes(G.bank(6)[:0x4000])
        w = lambda a, n: b6[a - 0x4000:a - 0x4000 + n]
        occ = ly["G_node_occ"]
        a = E.Agents().from_bytes(w(ly["G_agent_fields"], E.NPAGE * 256))
        b2 = bytes(self.m.read_ram(ly["G_econ_state"], ly["G_job_tbl"] - ly["G_econ_state"] + 160))
        return {"ag": {f: list(getattr(a, f))[:128] for f in E.FIELDS},
                "dome": w(ly["G_dome_tbl"], 64 * 24).hex(), "str": w(ly["G_struct_tbl"], 48 * 8).hex(),
                "occ": w(occ, 128).hex(),
                "foe": [(b & 15, b >> 4) for b in w(occ + 128, 112)],     # FO_MAP (src/foe.asm)
                "x": w(occ + 240, 14).hex(),                              # EC_X, EC_VIN, EC_TU
                "b2": b2.hex(), "corr": bytes(G.bank(5)[0x3800:0x3800 + 4 * 129]).hex(),
                "wi": w(ly["G_worldinfo"], 4).hex(), "wslot": self.m.peek(self.sym["WH_SLOT"])}

    def note(self):
        self.hashes.append({k: hashlib.md5(json.dumps(v).encode()).hexdigest()[:10]
                            for k, v in self.canon().items()})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--planet", type=int, default=0)
    ap.add_argument("--seed", type=lambda s: int(s, 0), default=0xACE1)
    ap.add_argument("--sols", type=float, default=20)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    T = Ticks(a.seed, a.planet)
    G = T.G

    def run(self, frames):
        while frames > 0:
            n = min(P.STEP, frames)
            T.advance(4 * n)
            self.frames += n
            frames -= n
            T.note()
            self.sample()
    P.Game.run = run
    P.Game.speed_probe = lambda self, n1=800, n4=400: (1.0, 4.0)
    G.trader = G.grow = G.zones = True
    G.tut = False
    t0 = T.start()
    print(f"πλανήτης {a.planet}, seed #{a.seed:04X}, «big», {a.sols} sols, με τον χρόνο του τροχού· "
          f"αρχή στο tick {t0} -> {G.ticks()}", flush=True)
    P.play(G, P.PLANS["big"](), a.sols)
    deaths = [e for e in G.events if "ΘΑΝΑΤΟΣ" in e]
    r = G.rows[-1]
    print(f"\nΣΥΝΟΨΗ πλανήτης {a.planet} seed #{a.seed:04X}: sol {G.sol():.2f}, ticks {T.ticks}, "
          f"ζωντανοί {r['alive']}/{r['popcap']}, θάνατοι {len(deaths)}, γεγονότα {len(G.events)}, "
          f"χωρίς ησυχία {T.loud}", flush=True)
    if a.json:
        json.dump(dict(seed=a.seed, planet=a.planet, ticks=T.ticks, loud=T.loud, hashes=T.hashes,
                       events=G.events, rows=[dict(sol=r["sol"], alive=r["alive"], stock=r["stock"])
                                              for r in G.rows]), open(a.json, "w"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
