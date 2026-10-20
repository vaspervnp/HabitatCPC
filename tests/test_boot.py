#!/usr/bin/env python3
"""Ο κώδικας της εκκίνησης στο τέλος του GH_BUF (βήμα 158, src/startup.asm,
DESIGN §4.2).

Ως το βήμα 157 η αρχή του start ήταν στην τράπεζα 0 (95 bytes) και το game_new
στο τέλος του κώδικα της τράπεζας 2 (342): κώδικας που τρέχει μία φορά, στην
εκκίνηση, σε δύο περιοχές που δεν είχαν πια ούτε ένα byte. Από το 158 είναι
στο BOOT_ORG, κάτω από το PAGE2_CODE, στο τέλος του αρχείου του φαντάσματος, με
την αποικία δοκιμών από κάτω του. Ο δίσκος τον φέρνει με το game2.bin, και το
πρώτο μεγάλο φάντασμα γράφει από πάνω του. Δύο πράγματα πρέπει να ισχύουν:

  ΑΘΙΚΤΟΣ   στο main.sna και στο colony.sna, τη στιγμή που αρχίζει το
            game_new, η αποικία και ο κώδικας της εκκίνησης (ZZ_COLONY ως
            ZZ_BOOT_END) είναι όπως στο snapshot: ό,τι έτρεξε ως εκεί — ο
            εγκαταστάτης των τρυπών με την κατεδάφιση σε τρία κομμάτια στο
            ovi_buf, και το tutorial — έγραψε μόνο από κάτω τους. Τα assert του
            src/main.asm το λένε από τις διευθύνσεις· εδώ το βλέπουμε να
            συμβαίνει, και τυπώνεται το ψηλότερο byte που γράφτηκε.
  ΜΙΑ ΦΟΡΑ  μετά την εκκίνηση κανείς δεν ξαναζητά τίποτα από εκεί: η περιοχή
            γεμίζει με halt, και η αποικία δοκιμών ζει — δύο δευτερόλεπτα
            τροχού χωρίς το PC να μπει ποτέ εκεί (δείγμα ανά 100 µs), ένα
            ηλιακό από τον παίκτη (μεγάλο φάντασμα) και η κατεδάφισή του (η
            επικάλυψη στο GH_BUF), και ο βρόχος γυρίζει όλη την ώρα.

Αρνητικά: ο εγκαταστάτης σε δύο μισά, όπως ως το βήμα 157 (η κατεδάφιση στο
ovi_buf σβήνει την αποικία: ΑΘΙΚΤΟΣ), και ένα call boot_go στη θέση του call
ui_tick του βρόχου (ΜΙΑ ΦΟΡΑ).
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, "/home/vasilhs/cpcemu")
import test_game as TG                                   # noqa: E402
import test_demolish as D                                # noqa: E402
import test_unlink as U                                  # noqa: E402
import test_fit as TF                                    # noqa: E402
import cpc                                               # noqa: E402

FAIL = []
HALT = 0x76


def check(ok, msg):
    print(("OK " if ok else "ΑΠΟΤΥΧΙΑ ") + msg, flush=True)
    if not ok:
        FAIL.append(msg)


def layout():
    L = {}
    for line in open(os.path.join(ROOT, "build", "layout.asm"), encoding="utf-8"):
        p = line.split()
        if len(p) >= 3 and p[1] == "equ" and p[2].startswith("#"):
            L[p[0]] = int(p[2][1:], 16)
    return L


GH_BUF = layout()["PAGE2_TOP"]


def intact(sym, sna, b1=()):
    """ΑΘΙΚΤΟΣ. (None ή η πρώτη διαφορά, το ψηλότερο byte του GH_BUF που
    γράφτηκε ως το game_new). `b1` = (διεύθυνση, τιμή) στη βασική τράπεζα 1,
    όπου είναι η εικόνα των τρυπών με τον εγκαταστάτη."""
    m = cpc.CPC()
    m.run_frames(60)
    assert m.quickload(sna, start=False), "quickload απέτυχε"
    p1 = cpc._lib.cpcemu_ram_ptr(m._h, 1)
    for at, v in b1:
        p1[at - 0x4000] = v
    lo, hi = sym["ZZ_COLONY"], sym["ZZ_BOOT_END"]
    want = m.read_ram(lo, hi - lo)
    under = m.read_ram(GH_BUF, lo - GH_BUF)
    t = 0
    while m.pc != sym["GAME_NEW"]:
        m.run_us(1)
        t += 1
        if t > 3_000_000:
            return f"το game_new δεν άρχισε σε 3 s (PC #{m.pc:04X})", None
    got = m.read_ram(lo, hi - lo)
    below = m.read_ram(GH_BUF, lo - GH_BUF)
    top = max((i for i in range(len(below)) if below[i] != under[i]), default=-1) + GH_BUF
    if got != want:
        i = next(i for i in range(len(got)) if got[i] != want[i])
        what = "η αποικία" if lo + i < sym["ZZ_BOOT"] else "ο κώδικας της εκκίνησης"
        return (f"{os.path.basename(sna)}: στην αρχή του game_new ({t} µs) {what} άλλαξε "
                f"στο #{lo + i:04X} ({want[i]:02X} -> {got[i]:02X})"), top
    return None, top


def two_halves(sym):
    """Ο εγκαταστάτης όπως ως το βήμα 157: δύο μισά. Στην εικόνα (τράπεζα 1,
    zz_ovi): το πρώτο call ovi_half σβηστό, και τα OVI_CH του ovi_half (ld
    bc,OVI_CH * 16 μετά το ld de,ovi_buf· ld a,OVI_CH μετά το ld hl,ovi_buf)
    στο μισό των R3_UNITS."""
    m = cpc.CPC()
    m.run_frames(60)
    assert m.quickload(TG.SNA, start=False)
    p1 = cpc._lib.cpcemu_ram_ptr(m._h, 1)
    a = sym["ZZ_OVI"]
    img = bytes(p1[a - 0x4000:a - 0x4000 + sym["ZZ_OVI_END"] - sym["OVI_GO"]])
    half, buf = sym["OVI_HALF"], sym["OVI_BUF"]
    call = bytes([0xCD, half & 255, half >> 8])
    i1 = img.find(call)
    i2 = img.find(bytes([0x11, buf & 255, buf >> 8, 0x01]))
    i3 = img.find(bytes([0x21, buf & 255, buf >> 8, 0x3E]))
    assert i1 >= 0 and img.find(call, i1 + 3) == i1 + 3 and i2 > 0 and i3 > 0, \
        "δεν βρέθηκαν τα δύο call ovi_half, το ld de,ovi_buf · ld bc και το ld hl,ovi_buf · ld a"
    n = img[i3 + 4]                          # OVI_CH: 22 = 66 / 3
    h = (3 * n + 1) // 2                     # 33, όσο ως το βήμα 157
    return [(a + i1 + k, 0) for k in range(3)] + \
           [(a + i2 + 4, (h * 16) & 255), (a + i2 + 5, (h * 16) >> 8), (a + i3 + 4, h)]


def once(sym, g, patch=()):
    """ΜΙΑ ΦΟΡΑ. None, ή τι πήγε στραβά."""
    G, F = D.game(sym, g, patch)
    lo, hi = sym["ZZ_COLONY"], sym["ZZ_BOOT_END"]
    G.m.write_ram(lo, bytes([HALT]) * (hi - lo))
    n0 = len(G.iters)
    G.run(1_000_000)
    for k in range(10_000):                  # ένα δευτερόλεπτο, δείγμα ανά 100 µs
        G.m.run_us(100)
        if lo <= G.m.pc < hi:
            return f"το PC στο #{G.m.pc:04X}, μέσα στην περιοχή της εκκίνησης, μετά από {k * 100} µs"
    n1 = len(G.iters)
    if n1 - n0 < 40:
        return f"ο βρόχος γύρισε {n1 - n0} φορές σε ένα δευτερόλεπτο μετά το halt"
    centre = U.tile(D.centre(G, 65))
    at, _ = U.find_spot(G, sym, U.SOLAR, lambda r, a: True, centre, rmax=30)
    if not at:
        return f"καμία θέση για ηλιακό γύρω από το {centre}"
    F.set_stocks(TF.STOCK, TF.STOCK)
    try:
        n = U.place(G, sym, g, U.SOLAR, at)
    except Exception as e:                   # noqa: BLE001
        return f"το ηλιακό δεν μπήκε: {type(e).__name__} {str(e)[:60]}"
    if not D.rec(G, n)[4]:
        return f"το ηλιακό στο {at} (κόμβος {n}) δεν είναι στον πίνακα"
    try:
        D.demolish(G, F, at)
    except Exception as e:                   # noqa: BLE001
        return f"η κατεδάφιση δεν έγινε: {type(e).__name__} {str(e)[:60]}"
    if D.rec(G, n)[4]:
        return f"η κατεδάφιση δεν άδειασε τον κόμβο {n}"
    n2 = len(G.iters)
    G.run(1_000_000)
    if len(G.iters) - n2 < 40:
        return f"μετά την κατεδάφιση ο βρόχος γύρισε {len(G.iters) - n2} φορές σε ένα δευτερόλεπτο"
    print(f"    ΜΙΑ ΦΟΡΑ: με halt από το #{lo:04X} ως το #{hi:04X}, {n1 - n0} γύροι σε "
          f"ένα δευτερόλεπτο, το ηλιακό στον κόμβο {n} και η κατεδάφισή του, "
          f"{len(G.iters) - n2} γύροι μετά", flush=True)
    return None


def main():
    sym, g = TG.build()
    lo, boot, hi = sym["ZZ_COLONY"], sym["ZZ_BOOT"], sym["ZZ_BOOT_END"]
    print(f"    η αποικία #{lo:04X}-#{boot - 1:04X}, η εκκίνηση #{boot:04X}-#{hi - 1:04X} "
          f"(game_new #{sym['GAME_NEW']:04X}), το GH_BUF #{GH_BUF:04X}-#9BFF", flush=True)
    for sna in (TG.SNA, TG.COLONY):
        why, top = intact(sym, sna)
        check(not why, why or f"ΑΘΙΚΤΟΣ: {os.path.basename(sna)} — στην αρχή του game_new "
                               f"η αποικία και η εκκίνηση όπως στο snapshot· ό,τι έτρεξε ως "
                               f"εκεί έγραψε ως το #{top:04X}, {lo - top - 1} bytes κάτω τους")
    why = once(sym, g)
    check(not why, why or "ΜΙΑ ΦΟΡΑ: μετά την εκκίνηση κανείς δεν ζητά τίποτα από την περιοχή της")
    # --- αρνητικά ---
    why, _ = intact(sym, TG.SNA, b1=two_halves(sym))
    check(bool(why), f"ΑΡΝΗΤΙΚΟ: ο εγκαταστάτης σε δύο μισά — {why or 'ΠΕΡΝΑ'}")
    top, ut = sym["MAIN_LOOP"], sym["UI_TICK"]
    m = cpc.CPC()
    m.run_frames(60)
    assert m.quickload(TG.COLONY, start=False)
    k = next(k for k in range(256) if list(m.read_ram(top + k, 6)) ==
             [0xCD, ut & 255, ut >> 8, 0xC3, top & 255, top >> 8])
    bg = sym["BOOT_GO"]
    why = once(sym, g, [("ram", top + k + 1, bg & 255), ("ram", top + k + 2, bg >> 8)])
    check(bool(why), f"ΑΡΝΗΤΙΚΟ: call boot_go στη θέση του call ui_tick — {why or 'ΠΕΡΝΑ'}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
