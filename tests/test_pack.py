#!/usr/bin/env python3
"""Δομικοί έλεγχοι της διάταξης μνήμης (DESIGN.md §4.2).

Ο packer λέει «χώρεσε». Αυτό δεν σημαίνει «σωστά»: δύο κομμάτια μπορεί να
επικαλύπτονται, ή ένα sprite να βρεθεί με τα bytes ενός άλλου.

Οι έλεγχοι για αρένες και για τις γραμμές οθόνης του HUD έφυγαν μαζί με τις
αρένες: το tests/test_camera.py έδειξε ότι η τομή δύο σελίδων δεν γίνεται,
οπότε η τράπεζα 2 δεν είναι πια σελίδα οθόνης αλλά επίπεδα 16 KB.
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
    arena, bank1, bank5, bank6, bank7, ptr, images, free, _ = pack.pack()
    smap, blob = load_map(), load_bin()
    all_runs = arena + bank1 + bank5 + bank6 + bank7
    by_name = {r.name: r for r in all_runs}

    # 1. καμία επικάλυψη μέσα στην ίδια περιοχή
    for label, runs in (("τράπεζα 2", arena), ("τράπεζα 1", bank1), ("τράπεζα 5", bank5),
                        ("τράπεζα 6", bank6), ("τράπεζα 7", bank7)):
        seen = sorted(runs, key=lambda r: r.addr)
        for a, b in zip(seen, seen[1:]):
            check(a.addr + a.size <= b.addr,
                  f"{label}: {a.name} (#{a.addr:04X}+{a.size}) επικαλύπτει "
                  f"{b.name} (#{b.addr:04X})")
        if seen:
            last = seen[-1]
            base = (pack.PAGE2_BASE if label == "τράπεζα 2"
                    else pack.BANK1_BASE if label == "τράπεζα 1"
                    else pack.BANK5_BASE if label == "τράπεζα 5"
                    else pack.WINDOW_BASE)
            # Η τράπεζα 5 κάτω από το B5_BASE είναι NEXTHOP και ευρετήριο
            # (βήμα 85): οι μηχανές μόνο από εκεί ως το τέλος.
            cap = (pack.BANK1_SIZE if label == "τράπεζα 1"
                   else pack.BANK5_SIZE if label == "τράπεζα 5" else pack.BANK_SIZE)
            check(seen[0].addr >= base,
                  f"{label}: το {seen[0].name} αρχίζει πριν από το #{base:04X}")
            check(last.addr + last.size <= base + cap,
                  f"{label}: το {last.name} βγαίνει από την τράπεζα")

    # 4. το flip_mode0 σε όριο σελίδας — όλη η παραγωγή τεταρτημορίων εξαρτάται
    f = by_name["flip_mode0"]
    check(f.addr % 256 == 0, f"το flip_mode0 στο #{f.addr:04X} δεν είναι σε σελίδα")

    # 5. τα bytes στις εικόνες είναι ΟΝΤΩΣ τα bytes του sprites.bin
    #    (αν ο packer έβαζε λάθος κομμάτι, όλα τα παραπάνω θα περνούσαν)
    def image_of(r):
        if r in arena:
            return images["page2"], pack.PAGE2_BASE
        if r in bank1:
            return images["bank1"], pack.BANK1_BASE
        if r in bank5:
            return images["bank5"], pack.BANK5_BASE
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
    # Το None είναι θέση που ΔΕΝ υπάρχει — το struct_ptr κρατά τέσσερις ανά
    # είδος και το ορυχείο έχει ένα μέγεθος. Πρέπει να δείχνει μηδέν, και ο
    # renderer το ελέγχει πριν σχεδιάσει.
    for tab, names in ptr.items():
        r = by_name[tab]
        for i, n in enumerate(names):
            want = 0 if n is None else by_name[n].addr
            got = int.from_bytes(r.data[i * 2:i * 2 + 2], "little")
            check(got == want,
                  f"{tab}[{i}] -> #{got:04X}, περίμενα #{want:04X} ({n})")

    # 7. ό,τι δεικτοδοτείται με πολλαπλασιασμό πρέπει να είναι ΣΥΝΕΧΟΜΕΝΟ
    for grp, stride, count in (("font_m1", 8, 96 + 5), ("connectors", 32, 8),
                               ("slot_empty", 16, 24), ("fig_ring", 32, 8),
                               ("fig_gfx", 32, 8)):
        r = by_name[grp]
        check(r.size == stride * count,
              f"{grp}: {r.size} B, περίμενα {stride*count}")

    # 7α. ΟΙ ΘΕΣΕΙΣ ΤΟΥ ΔΑΚΤΥΛΙΟΥ (βήμα 89): η κενή, και από πάνω η φιγούρα με
    #     μάσκα, είναι η ψημένη παραλλαγή των assets — και για τις 24 x 8, από
    #     τα bytes της ΕΙΚΟΝΑΣ της τράπεζας 6, όχι από ό,τι νομίζει το pack.py.
    #     Και η φιγούρα έξω είναι η ίδια σιλουέτα: όπου η μάσκα του δακτυλίου
    #     λέει «φιγούρα», η έξω λέει το ίδιο pixel (η σκιά είναι μόνο παραπάνω).
    #     Η λίστα, οι φιγούρες και ο δακτύλιος σε σελίδα (ld h,σελίδα).
    img6 = images["bank6"]
    at6 = lambda n: img6[by_name[n].addr - pack.WINDOW_BASE:][:by_name[n].size]
    empty, ring, out = at6("slot_empty"), at6("fig_ring"), at6("fig_gfx")
    bad = []
    for i, (z, t) in enumerate((z, t) for z in "sml" for t in range(8)):
        for f, nm in enumerate(pack.FIG_NAMES):
            want = blob[smap[f"slot_{z}_{t}_{nm}"].off:][:16]
            spr = ring[f * 32:(f + 1) * 32]
            got = bytes((empty[i * 16 + k] & spr[2 * k]) | spr[2 * k + 1] for k in range(16))
            if got != want:
                bad.append(f"slot_{z}_{t}_{nm}")
    check(not bad, f"κενή + φιγούρα δεν είναι η ψημένη θέση: {bad[:4]}")
    same = all((out[k] | ring[k]) == ring[k] if k % 2 == 0 else
               (ring[k] & ~ring[k - 1] & 0xFF) == (out[k] & ~ring[k - 1] & 0xFF)
               for k in range(256))
    check(same, "η φιγούρα έξω δεν είναι η σιλουέτα του δακτυλίου")
    for n in ("fig_list", "fig_gfx", "fig_ring"):
        check(by_name[n].addr % 256 == 0, f"το {n} στο #{by_name[n].addr:04X} δεν είναι σε σελίδα")
    check(by_name["agent_fields"].addr == 0x6C00,
          f"το agent_fields στο #{by_name['agent_fields'].addr:04X}, όχι στο #6C00 του σωσίματος")

    # 7β. Η γραμματοσειρά Mode 1 του HUD (βήμα 83) δεν είναι sprite: τη γράφει
    #     το pack.py από το font_gfx. Εδώ ξαναβγαίνει από τα PIXEL, με τον
    #     αναγνώστη των δοκιμών (tests/hudread.py), και τα πέντε κελιά της
    #     μπάρας από την περιγραφή τους· στοίχιση 8, για το inc e του hc_line.
    sys.path.insert(0, HERE)
    import hudread
    r = by_name["font_m1"]
    img, base = image_of(r)
    want = b"".join(hudread.font_m1()) + b"".join(
        hudread.CELLS[k] for k in ("blank", "low", "full", "white", "empty"))
    check(img[r.addr - base:r.addr - base + r.size] == want and r.addr % 8 == 0,
          f"font_m1 στο #{r.addr:04X}: δεν είναι το font_gfx σε Mode 1 και τα κελιά της μπάρας")

    # 8. κάθε κλάση εδάφους συνεχόμενη, ώστε tile_ptr[class] + variant*64
    for cls, n in (("ground", 4), ("dust", 4), ("rock", 4), ("mountain", 16),
                   ("water", 16), ("deepwater", 4), ("crater", 2), ("foundation", 2)):
        r = by_name[f"tile_{cls}"]
        check(r.size == n * 64, f"tile_{cls}: {r.size} B, περίμενα {n*64}")

    print(f"διάταξη: {len(all_runs)} κομμάτια, {checked} sprites επαληθευμένα byte-προς-byte")
    print(f"  τράπ. 2 {sum(r.size for r in arena):>6}/{pack.BANK_SIZE}"
          f"   ελεύθερα {free[0]} συνεχόμενα")
    print(f"  τράπ. 5 {sum(r.size for r in bank5):>6}/{pack.BANK5_SIZE}")
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
