#!/usr/bin/env python3
"""Τα αποθέματα του src/stock.asm, στο main.sna, απέναντι στον κανόνα.

  ec_stock_ptr  A = απόθεμα -> DE = EC_STOCK + 2A, το HL μένει
  ec_add_stock  stock[A] = min(stock[A] + DE, EC_CAP), τίποτε άλλο δεν αλλάζει
  ec_make       το ίδιο, και πρώτα το bit A του EC_PRODM (§10.2): τα αποθέματα
                0-7 στο κάτω byte, τα 8-13 στο πάνω

Για καθένα από τα 14 αποθέματα: ποσότητες 0, 1, 255, 256, 599, 600, 601 και
τυχαίες, με αποθέματα κάτω, πάνω και πάνω στο ταβάνι και EC_PRODM τυχαίο. Το
άθροισμα μένει κάτω από 65.536, όπως στο παιχνίδι (βλ. την κεφαλίδα του
ec_add_stock).

ΓΙΑΤΙ. Ως το βήμα 69 τα έβλεπε μόνο το test_sim, μέσα από μια ολόκληρη
οικονομία. Το έπιανε κάθε λάθος — αλλά όχι το «χωρίς and 7» του ec_make, που
δίνει το ίδιο bit με οκτώ περιστροφές παραπάνω για τα αποθέματα 8-13. Γι' αυτό
και ο ΧΡΟΝΟΣ: το ec_make κάθε αποθέματος όχι πιο αργό από όσο μετρήθηκε στο
βήμα 69. Με το stock.asm του βήματος 68 αποτυγχάνουν και τα 14.

Αρνητικά, με το snapshot πειραγμένο: η μάσκα από #01 αντί #80 (ένα bit πιο
πάνω), ταβάνι 599, και το ec_stock_ptr χωρίς το x2.
"""
import os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import cpc                                               # noqa: E402

PROBE = 0x3E00
EC_CAP = 600                                             # src/const.asm
# µs ανά ec_make με το probe, απόθεμα 0..13, κάτω από το ταβάνι (βήμα 69)
CEIL = [99, 104, 109, 114, 119, 124, 129, 134, 100, 105, 110, 115, 120, 125]


def check(sym, g, patch=(), timing=True):
    """Η πρώτη διαφορά από τον κανόνα, ή None."""
    m = cpc.CPC()
    m.run_frames(60)
    assert m.quickload(TG.COLONY, start=False), "quickload απέτυχε"
    for at, v in patch:
        m.poke(at, v)
    stock, prodm = g, g + 68                             # EC_STOCK, EC_PRODM (src/const.asm)
    w16 = lambda a: m.peek(a) | m.peek(a + 1) << 8

    def run(code, step=20):
        code = [0xF3, 0x31, 0x00, 0x01] + code + [0xED, 0x53, 0xF0, 0x3F, 0x22, 0xF2, 0x3F, 0x18, 0xFE]
        m.write_ram(PROBE, bytes(code))
        m.set_pc(PROBE)
        end, t = PROBE + len(code) - 2, 0
        while not (end <= m.pc <= end + 2):
            m.run_us(step)
            t += step
            if t > 100_000:
                return None
        return t

    call = lambda n: [0xCD, sym[n] & 255, sym[n] >> 8]
    for a in range(14):
        if run([0x3E, a, 0x21, 0x34, 0x12] + call("EC_STOCK_PTR")) is None:
            return "το ec_stock_ptr δεν γύρισε"
        if (w16(0x3FF0), w16(0x3FF2)) != (stock + 2 * a, 0x1234):
            return f"ec_stock_ptr({a}): DE #{w16(0x3FF0):04X}, HL #{w16(0x3FF2):04X}"

    rnd = random.Random(69)
    for k in range(14 * 2 * 12):
        a, name = k % 14, ("EC_ADD_STOCK", "EC_MAKE")[(k // 14) % 2]
        st = [rnd.choice([0, 1, 300, 599, 600, 601, rnd.randrange(700), rnd.randrange(30000)])
              for _ in range(14)]
        q = [0, 1, 255, 256, 599, 600, 601][k // 28] if k < 28 * 7 else rnd.randrange(65536 - st[a])
        pm = rnd.randrange(65536)
        m.write_ram(stock, b"".join(v.to_bytes(2, "little") for v in st))
        m.write_ram(prodm, pm.to_bytes(2, "little"))
        if run([0x3E, a, 0x11, q & 255, q >> 8] + call(name)) is None:
            return f"{name.lower()}({a}, {q}) δεν γύρισε"
        want = list(st)
        want[a] = min(st[a] + q, EC_CAP)
        wpm = pm | (1 << a) if name == "EC_MAKE" else pm
        got = [w16(stock + 2 * i) for i in range(14)]
        where = f"{name.lower()}(απόθεμα {a}, ποσότητα {q}) με απόθεμα {st[a]}"
        if got != want:
            i = next(i for i in range(14) if got[i] != want[i])
            return f"{where}: stock[{i}] = {got[i]}, ο κανόνας λέει {want[i]}"
        if w16(prodm) != wpm:
            return f"{where}: EC_PRODM #{w16(prodm):04X}, ο κανόνας λέει #{wpm:04X}"
    if not timing:
        return None
    slow = []
    times = []
    for a in range(14):
        m.write_ram(stock, bytes(28))
        t = run([0x3E, a, 0x11, 1, 0] + call("EC_MAKE"), step=1)
        times.append(t)
        if t > CEIL[a]:
            slow.append(f"απόθεμα {a} {t} > {CEIL[a]} us")
    print(f"    ec_make, απόθεμα 0..13: {times} us")
    return "πιο αργό από το βήμα 69: " + ", ".join(slow) if slow else None


def main():
    sym, g = TG.build()
    fails = 0
    why = check(sym, g)
    if why:
        print(f"ΑΠΟΤΥΧΙΑ: {why}")
        fails += 1
    else:
        print("OK ec_stock_ptr, ec_add_stock και ec_make = ο κανόνας, για τα 14 αποθέματα "
              "(336 κλήσεις: ταβάνι, EC_PRODM, τα άλλα αποθέματα ανέγγιχτα)")
        print("OK κανένα ec_make πιο αργό από το βήμα 69")

    # --- αρνητικά ---
    m = cpc.CPC()
    m.run_frames(60)
    assert m.quickload(TG.COLONY, start=False)
    mk, ad, pt = sym["EC_MAKE"], sym["EC_ADD_STOCK"], sym["EC_STOCK_PTR"]
    i80 = m.read_ram(mk, 24).find(bytes([0x3E, 0x80]))
    icap = m.read_ram(ad, 24).find(bytes([0x01, EC_CAP & 255, EC_CAP >> 8]))
    assert i80 > 0 and icap > 0, "δεν βρέθηκαν το ld a,#80 / ld bc,EC_CAP"
    assert m.peek(pt) == 0x87, "το ec_stock_ptr δεν ξεκινά με add a,a"
    for label, patch in (("τη μάσκα από #01", [(mk + i80 + 1, 0x01)]),
                         ("ταβάνι 599", [(ad + icap + 1, (EC_CAP - 1) & 255)]),
                         ("το ec_stock_ptr χωρίς x2", [(pt, 0)])):
        why = check(sym, g, patch, timing=False)
        if why:
            print(f"OK ΑΡΝΗΤΙΚΟ: με {label} αποτυγχάνει ({why[:80]})")
        else:
            print(f"ΑΠΟΤΥΧΙΑ ΑΡΝΗΤΙΚΟΥ: με {label} περνά")
            fails += 1
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
