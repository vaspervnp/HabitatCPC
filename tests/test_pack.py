#!/usr/bin/env python3
"""Δομικοί έλεγχοι της διάταξης μνήμης (DESIGN.md §4.2, §4.3).

Ο packer λέει «χώρεσε». Αυτό δεν σημαίνει «σωστά»: ένα κομμάτι μπορεί να
πατάει σε δύο αρένες, δύο κομμάτια να επικαλύπτονται, ή —το χειρότερο— ένα
γραφικό να κάτσει πάνω στα bytes ΟΘΟΝΗΣ του HUD, οπότε θα εμφανιζόταν ως
σκουπίδια στο HUD και θα καταστρεφόταν την πρώτη φορά που το HUD σχεδιάζεται.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))

from sprites import load_map, load_bin                                  # noqa: E402
import pack                                                             # noqa: E402

fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)


def main():
    arena, bank6, bank7, ptr, images, free, _ = pack.pack()
    smap, blob = load_map(), load_bin()
    all_runs = arena + bank6 + bank7
    by_name = {r.name: r for r in all_runs}

    # 1. τίποτα δεν πατάει σε δύο αρένες
    for r in arena:
        lo, hi = pack.ARENAS[r.bin][0], pack.ARENAS[r.bin][0] + pack.ARENA_SIZE
        check(lo <= r.addr and r.addr + r.size <= hi,
              f"το {r.name} (#{r.addr:04X}+{r.size}) βγαίνει από την αρένα {r.bin} "
              f"(#{lo:04X}-#{hi:04X})")

    # 2. καμία επικάλυψη μέσα στην ίδια περιοχή
    for label, runs in (("σελίδα 2", arena), ("τράπεζα 6", bank6), ("τράπεζα 7", bank7)):
        seen = sorted(runs, key=lambda r: r.addr)
        for a, b in zip(seen, seen[1:]):
            check(a.addr + a.size <= b.addr,
                  f"{label}: {a.name} (#{a.addr:04X}+{a.size}) επικαλύπτει "
                  f"{b.name} (#{b.addr:04X})")

    # 3. ΤΙΠΟΤΑ στα bytes οθόνης του HUD
    # Το HUD πιάνει τα &000-&18F κάθε υποσελίδας των &800.
    for i in range(pack.ARENA_N):
        lo = pack.PAGE2_BASE + i * pack.SUBPAGE
        hi = lo + pack.HUD_USED
        for r in arena:
            check(r.addr >= hi or r.addr + r.size <= lo,
                  f"το {r.name} (#{r.addr:04X}+{r.size}) πέφτει στις γραμμές HUD "
                  f"της υποσελίδας {i} (#{lo:04X}-#{hi:04X})")
        check(images["page2"][lo - pack.PAGE2_BASE:hi - pack.PAGE2_BASE] ==
              bytes(pack.HUD_USED),
              f"η περιοχή HUD της υποσελίδας {i} δεν είναι καθαρή στο page2.bin")

    # 4. το flip_mode0 σε όριο σελίδας — όλη η παραγωγή τεταρτημορίων εξαρτάται
    f = by_name["flip_mode0"]
    check(f.addr % 256 == 0, f"το flip_mode0 στο #{f.addr:04X} δεν είναι σε σελίδα")

    # 5. τα bytes στις εικόνες είναι ΟΝΤΩΣ τα bytes του sprites.bin
    #    (αν ο packer έβαζε λάθος κομμάτι, όλα τα παραπάνω θα περνούσαν)
    def image_of(r):
        if r in arena:
            return images["page2"], pack.PAGE2_BASE
        return (images["bank6"], pack.WINDOW_BASE) if r in bank6 else \
               (images["bank7"], pack.WINDOW_BASE)

    checked = 0
    for name, s in smap.items():
        r = by_name.get(name)
        if r is None or r.data is None:
            continue
        img, base = image_of(r)
        got = img[r.addr - base:r.addr - base + s.size]
        check(got == blob[s.off:s.off + s.size],
              f"το {name} στο #{r.addr:04X} δεν είναι τα bytes του sprites.bin")
        checked += 1

    # 5β. και τα μέλη των ομάδων, στη ΣΕΙΡΑ τους — μια ομάδα μπορεί να έχει
    #     σωστά bytes συνολικά και λάθος σειρά μέσα της
    for r in all_runs:
        if not r.members:
            continue
        img, base = image_of(r)
        for name, off in r.members:
            s = smap[name]
            a = r.addr + off
            got = img[a - base:a - base + s.size]
            check(got == blob[s.off:s.off + s.size],
                  f"{r.name}: το μέλος {name} στη μετατόπιση {off} (#{a:04X}) "
                  f"δεν ταιριάζει")
            checked += 1

    # 6. οι παραγόμενοι πίνακες δείχνουν στα σωστά
    for tab, names in ptr.items():
        r = by_name[tab]
        for i, n in enumerate(names):
            want = by_name[n].addr
            got = int.from_bytes(r.data[i * 2:i * 2 + 2], "little")
            check(got == want,
                  f"{tab}[{i}] -> #{got:04X}, περίμενα #{want:04X} ({n})")

    # 7. ό,τι δεικτοδοτείται με πολλαπλασιασμό πρέπει να είναι ΣΥΝΕΧΟΜΕΝΟ
    for grp, stride, count in (("font_gfx", 16, 96), ("connectors", 32, 8),
                               ("corr_slot_gfx", 16, 216)):
        r = by_name[grp]
        check(r.size == stride * count,
              f"{grp}: {r.size} B, περίμενα {stride*count}")

    # 8. κάθε κλάση εδάφους συνεχόμενη, ώστε tile_ptr[class] + variant*64
    for cls, n in (("ground", 4), ("dust", 4), ("rock", 4), ("mountain", 16),
                   ("water", 16), ("deepwater", 4), ("crater", 2), ("foundation", 2)):
        r = by_name[f"tile_{cls}"]
        check(r.size == n * 64, f"tile_{cls}: {r.size} B, περίμενα {n*64}")

    print(f"διάταξη: {len(all_runs)} κομμάτια, {checked} sprites επαληθευμένα byte-προς-byte")
    print(f"  αρένες  {sum(r.size for r in arena):>6}/{pack.ARENA_SIZE*pack.ARENA_N}"
          f"   ελεύθερα ανά αρένα: {free}")
    print(f"  τράπ. 6 {sum(r.size for r in bank6):>6}/{pack.BANK_SIZE}")
    print(f"  τράπ. 7 {sum(r.size for r in bank7):>6}/{pack.BANK_SIZE}")

    if fails:
        print(f"\nΑΠΟΤΥΧΙΑ — {len(fails)} προβλήματα:")
        for m in fails[:20]:
            print("  " + m)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
