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


# Οι χαρακτήρες 32-122 της γραμματοσειράς: τα {|}~ και το DEL δεν τα γράφει κανένα
# κείμενο, και έδωσαν τα 40 bytes τους στην κατεδάφιση (βήμα 101, tools/pack.py).
FONT_N = 0x7B - 32

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
        if r is None or r.data is None or getattr(r, "groups", None) is not None:
            continue
        img, base = image_of(r)
        if getattr(r, "rows", None):
            # ΒΗΜΑ 170: οι δομές της τράπεζας 7 χωρίς μάσκα. Το χρώμα της εικόνας,
            # με τη μάσκα του st_mask όπως τη διαβάζει το src/st7.asm, είναι ΚΑΘΕ
            # κελί του sprites.bin: η μάσκα και το χρώμα του.
            w, h = r.rows
            mk = by_name["st_mask"]
            mtab = img[mk.addr - base:mk.addr - base + 256]
            got = img[r.addr - base:r.addr - base + r.size]
            check(r.size == w * h and
                  [(mtab[d], d) for d in got] ==
                  [(blob[s.off + y * s.stride + 2 * x], blob[s.off + y * s.stride + 2 * x + 1])
                   for y in range(h) for x in range(w)],
                  f"το {name} στο #{r.addr:04X}: τα bytes του με το st_mask δεν δίνουν τα κελιά του sprites.bin")
            checked += 1
            continue
        got = img[r.addr - base:r.addr - base + s.size]
        want = bytearray(blob[s.off:s.off + s.size])
        if name == "struct_dims":       # βήμα 151: τα s και m των ενεργειακών μηδέν
            for k in range(4):
                want[k * 8:k * 8 + 4] = bytes(4)
        check(got == bytes(want),
              f"το {name} στο #{r.addr:04X} δεν είναι τα bytes του sprites.bin")
        checked += 1

    # 5γ. ΒΗΜΑ 151: ό,τι δεν ζωγραφίζει ποτέ το παιχνίδι λείπει, και οι δείκτες
    #     του δείχνουν όπως πρέπει. Τα μεγέθη 0 και 1 των τεσσάρων ενεργειακών:
    #     κανένα sprite, struct_dims 0 — και το 2 εκεί, με τον δείκτη του είδους
    #     στο struct_ptr (μία λέξη ανά είδος από το βήμα 152). Τα τρία
    #     εικονίδια του airlock (δωμάτιο 7): κανένα, και ο δείκτης του δείχνει το
    #     άδειο. Μηχανές, σήματα, εικονίδια s και mach_ptr στην τράπεζα 7.
    def table(name):
        r = by_name[name]
        img, base = image_of(r)
        return img[r.addr - base:r.addr - base + r.size]
    w16 = lambda t, i: t[2 * i] | t[2 * i + 1] << 8
    sp, sd = table("struct_ptr"), table("struct_dims")
    check(len(sp) == 16, f"struct_ptr {len(sp)} bytes, όχι 16 (ένα ανά είδος, βήμα 152)")
    for k, kind in enumerate(("solar", "turbine", "collector", "extractor")):
        for z, size in enumerate("sml"):
            name = f"{kind}_{size}"
            if size == "l":
                check(name in by_name and w16(sp, k) == by_name[name].addr
                      and sd[8 * k + 4] and sd[8 * k + 5],
                      f"το {name}: struct_ptr #{w16(sp, k):04X}, διαστάσεις "
                      f"{sd[8 * k + 4]}x{sd[8 * k + 5]}")
            else:
                check(name not in by_name and sd[8 * k + 2 * z] == sd[8 * k + 2 * z + 1] == 0,
                      f"το {name} δεν έπρεπε να υπάρχει: διαστάσεις "
                      f"{sd[8 * k + 2 * z]}x{sd[8 * k + 2 * z + 1]}")
    # τα τέσσερα του ενός μεγέθους: το 0 έχει διαστάσεις, τα 1-3 μηδέν
    for k, kind in enumerate(("mine", "airlock", "pad", "ship"), 4):
        check(w16(sp, k) == by_name[kind].addr and sd[8 * k] and sd[8 * k + 1]
              and not any(sd[8 * k + 2:8 * k + 8]),
              f"το {kind}: struct_ptr #{w16(sp, k):04X}, διαστάσεις {list(sd[8 * k:8 * k + 8])}")
    for size in "sml":
        t = table(f"icon_{size}_ptr")
        check(f"icon_{size}_airlock" not in by_name
              and w16(t, 7) == by_name[f"icon_{size}_empty"].addr,
              f"icon_{size}_ptr[7] #{w16(t, 7):04X}, όχι το icon_{size}_empty")
    # οι μηχανές και τα εικονίδια s με το όνομα του sprite τους· όχι το mach_op
    # (συνταγές, τράπεζα 2) και το icon_s_ptr (δείκτες, τράπεζα 6)
    moved = [n for n in by_name if n.startswith(("mach_", "icon_s_")) and n in smap] \
        + ["mach_ptr", "marks"]
    check(len(moved) == 12 + 11 + 2 and all(by_name[n] in bank7 for n in moved),
          f"στην τράπεζα 7: {[n for n in moved if by_name[n] not in bank7]} λείπουν "
          f"({len(moved)} από 25)")

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

    # 5γ. ΤΑ ΚΕΛΥΦΗ (βήμα 110): μόνο τα διαστήματά τους. Από την ΕΙΚΟΝΑ της
    #     τράπεζας 6, με την κεφαλίδα και τις διευθύνσεις της, ξαναχτίζεται
    #     ολόκληρο το nw — με (#FF, 0) έξω από τα διαστήματα — και πρέπει να
    #     είναι τα bytes του sprites.bin. Και η κεφαλίδα σε μία σελίδα, και οι
    #     ομάδες η μία μετά την άλλη μέσα στο κομμάτι.
    #     ΚΑΙ ΤΟ ΑΔΙΑΦΑΝΕΣ ΤΕΛΟΣ (βήμα 114): οι k τελευταίες στήλες κάθε ομάδας
    #     είναι μόνο χρώμα, και ξαναχτίζονται με μάσκα 0· αν μία από αυτές δεν
    #     είχε μάσκα 0 σε κάποια γραμμή, το sprite δεν ξαναβγαίνει. Και κάθε
    #     ομάδα που θα μπορούσε να έχει k >= K_MIN το έχει.
    img6 = images["bank6"]
    shells, opaque = 0, 0
    for r in bank6:
        if getattr(r, "groups", None) is None:
            continue
        s = smap[r.name]
        o = r.addr - pack.WINDOW_BASE
        hdr = img6[o:o + pack.SHELL_HDR]
        check((r.addr & 255) + pack.SHELL_HDR <= 256,
              f"{r.name}: η κεφαλίδα στο #{r.addr:04X} περνά σελίδα")
        full = bytearray(b"\xff\x00" * (s.w * s.h))
        at = r.addr + pack.SHELL_HDR
        for g in range(s.h // pack.SPAN_G):
            a, n = hdr[g] >> 4, hdr[g] & 15
            addr = hdr[pack.SPAN_G + 2 * g] | hdr[pack.SPAN_G + 2 * g + 1] << 8
            ko = hdr[3 * pack.SPAN_G + g]
            if n == 0:
                check(addr == 0 and ko == 0,
                      f"{r.name}: η άδεια ομάδα {g} έχει διεύθυνση #{addr:04X}, k {ko}")
                continue
            check(addr == at, f"{r.name}: η ομάδα {g} στο #{addr:04X}, περίμενα #{at:04X}")
            check(ko == 0 or pack.K_MIN <= ko <= n,
                  f"{r.name}: η ομάδα {g} έχει k {ko} (n {n}, K_MIN {pack.K_MIN})")
            check(ko == pack.shell_opaque(s, blob, g, a, n),
                  f"{r.name}: η ομάδα {g} έχει k {ko}, οι στήλες της λένε "
                  f"{pack.shell_opaque(s, blob, g, a, n)}")
            m, ln = n - ko, 2 * n - ko
            for y in range(pack.SPAN_G):
                row = img6[addr - pack.WINDOW_BASE + y * ln:][:ln]
                k = ((g * pack.SPAN_G + y) * s.w + a) * 2
                full[k:k + 2 * m] = row[:2 * m]
                for c in range(ko):
                    full[k + 2 * (m + c):k + 2 * (m + c) + 2] = bytes([0, row[2 * m + c]])
            opaque += pack.SPAN_G * ko
            at += pack.SPAN_G * ln
        check(at == r.addr + r.size, f"{r.name}: οι ομάδες τελειώνουν στο #{at:04X}, "
                                     f"το κομμάτι στο #{r.addr + r.size:04X}")
        check(bytes(full) == blob[s.off:s.off + s.size],
              f"{r.name}: από τα διαστήματα δεν ξαναβγαίνει το sprite του sprites.bin")
        shells += 1
    check(shells == 6, f"{shells} κελύφη ως διαστήματα, περίμενα 6")
    check(opaque > 800, f"το αδιαφανές τέλος των κελυφών: {opaque} στήλες χωρίς μάσκα "
                        f"(βήμα 114), όσα bytes γλίτωσε η τράπεζα 6")

    # ΑΡΝΗΤΙΚΟ (βήμα 114): ένα k μία στήλη μεγαλύτερο σε κάθε ομάδα που έχει.
    # Η στήλη πριν από το αδιαφανές τέλος έχει κάπου μάσκα, και αποθηκευμένη
    # χωρίς αυτήν το sprite δεν ξαναβγαίνει. Η ανασύνθεση εδώ είναι από τα
    # δεδομένα του κομματιού, με τις ομάδες τη μία μετά την άλλη.
    def unshell(s, data):
        full = bytearray(b"\xff\x00" * (s.w * s.h))
        at = pack.SHELL_HDR
        for g in range(s.h // pack.SPAN_G):
            a, n, ko = data[g] >> 4, data[g] & 15, data[3 * pack.SPAN_G + g]
            if n == 0:
                continue
            m, ln = n - ko, 2 * n - ko
            for y in range(pack.SPAN_G):
                row = data[at + y * ln:at + (y + 1) * ln]
                k = ((g * pack.SPAN_G + y) * s.w + a) * 2
                full[k:k + 2 * m] = row[:2 * m]
                for c in range(ko):
                    full[k + 2 * (m + c):k + 2 * (m + c) + 2] = bytes([0, row[2 * m + c]])
            at += pack.SPAN_G * ln
        return bytes(full)
    good = [unshell(smap[n], pack.shell(n, smap, blob).data) == blob[smap[n].off:smap[n].off + smap[n].size]
            for n in ("dome_s_nw", "dome_m_nw", "dome_l_nw")]
    orig = pack.shell_opaque
    pack.shell_opaque = lambda s, b, g, a, n: min(n, orig(s, b, g, a, n) + 1) if orig(s, b, g, a, n) else 0
    try:
        bad = [unshell(smap[n], pack.shell(n, smap, blob).data) == blob[smap[n].off:smap[n].off + smap[n].size]
               for n in ("dome_s_nw", "dome_m_nw", "dome_l_nw")]
    finally:
        pack.shell_opaque = orig
    check(all(good) and not any(bad),
          f"ΑΡΝΗΤΙΚΟ: με k + 1 οι θόλοι δεν ξαναβγαίνουν ({good} σωστά, {bad} με το λάθος)")

    # 6. οι παραγόμενοι πίνακες δείχνουν στα σωστά
    # Το None είναι θέση που ΔΕΝ υπάρχει — ως το βήμα 151 το struct_ptr κρατούσε
    # τέσσερις ανά είδος και το ορυχείο είχε ένα μέγεθος. Πρέπει να δείχνει
    # μηδέν, και ο renderer το ελέγχει πριν σχεδιάσει.
    for tab, names in ptr.items():
        r = by_name[tab]
        for i, n in enumerate(names):
            want = 0 if n is None else by_name[n].addr
            got = int.from_bytes(r.data[i * 2:i * 2 + 2], "little")
            check(got == want,
                  f"{tab}[{i}] -> #{got:04X}, περίμενα #{want:04X} ({n})")

    # 7. ό,τι δεικτοδοτείται με πολλαπλασιασμό πρέπει να είναι ΣΥΝΕΧΟΜΕΝΟ
    # (οι πόρτες, connectors 8 x 32, ως το βήμα 95: δεν ζωγραφίζονται πια· οι
    # αρμοί του 96 τους ελέγχει το test_object, απέναντι στη scene.joint)
    for grp, stride, count in (("font_m1", 8, FONT_N + 5),
                               ("slot_empty", 16, 24)):
        r = by_name[grp]
        check(r.size == stride * count,
              f"{grp}: {r.size} B, περίμενα {stride*count}")
    # ΟΙ ΕΝΝΙΑ ΦΙΓΟΥΡΕΣ (βήμα 111) δεν δεικτοδοτούνται με πολλαπλασιασμό: ο
    # κωδικός της καθεμίας είναι το L της, και το bit 0 η σελίδα πάνω από την
    # πρώτη (src/figure.asm: ld l,a / and 1 / add a,σελίδα / ld h,a). Κάθε
    # φιγούρα όλη σε μία σελίδα (inc l), καμία πάνω σε άλλη, κανένας κωδικός 0.
    for grp in ("fig_gfx", "fig_ring"):
        r = by_name[grp]
        page = r.addr >> 8
        spans = []
        for j, nm in enumerate(pack.FIG_ALL):
            c = pack.fig_code(j)
            at = r.addr + pack.fig_off(j)
            spans.append((at, at + 32))
            check(c != 0 and at == ((page + (c & 1)) << 8) + c
                  and (at >> 8) == ((at + 31) >> 8) and at + 32 <= r.addr + r.size,
                  f"{grp}: η φιγούρα {nm} (κωδικός {c}) στο #{at:04X}")
        spans.sort()
        check(all(a1 <= b0 for (_, a1), (b0, _) in zip(spans, spans[1:])),
              f"{grp}: φιγούρες η μία πάνω στην άλλη")

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
            spr = ring[pack.fig_off(f):pack.fig_off(f) + 32]
            got = bytes((empty[i * 16 + k] & spr[2 * k]) | spr[2 * k + 1] for k in range(16))
            if got != want:
                bad.append(f"slot_{z}_{t}_{nm}")
    check(not bad, f"κενή + φιγούρα δεν είναι η ψημένη θέση: {bad[:4]}")
    figk = [(pack.fig_off(j) + k, k) for j in range(len(pack.FIG_ALL)) for k in range(32)]
    same = all((out[a] | ring[a]) == ring[a] if k % 2 == 0 else
               (ring[a] & ~ring[a - 1] & 0xFF) == (out[a] & ~ring[a - 1] & 0xFF)
               for a, k in figk)
    check(same, "η φιγούρα έξω δεν είναι η σιλουέτα του δακτυλίου")
    check(by_name["fig_list"].addr % 256 == 0,
          f"το fig_list στο #{by_name['fig_list'].addr:04X} δεν είναι σε σελίδα")
    for n in ("fig_gfx", "fig_ring"):
        check(by_name[n].addr % 256 == pack.FIG_PHASE,
              f"το {n} στο #{by_name[n].addr:04X}, όχι στο {pack.FIG_PHASE} μιας σελίδας")

    # 7β'. Ο ΕΙΣΒΟΛΕΑΣ (βήμα 111): στον δακτύλιο, η σιλουέτα του αποίκου pixel
    #     προς pixel, κόκκινη (pen 8) εκτός από τα τέσσερα μαύρα — από τα bytes
    #     της τράπεζας 6. Και έξω η ίδια, με τη σκιά του αποίκου.
    def pens(tab, j):
        o, px = pack.fig_off(j), {}
        for y in range(8):
            for xb in range(2):
                mk, d = tab[o + y * 4 + xb * 2], tab[o + y * 4 + xb * 2 + 1]
                pl, pr = pack._m0_pens(d)
                for k, (bits, pen) in enumerate(((0xAA, pl), (0x55, pr))):
                    if not mk & bits:
                        px[(xb * 2 + k, y)] = pen
        return px
    jc, jf = pack.FIG_ALL.index("colonist"), pack.FIG_ALL.index(pack.FOE_FIG)

    def foe_ok(ring, tab):
        col, foe = pens(tab, jc), pens(tab, jf)
        sil = {p for p, v in pens(ring, jc).items()}
        want = {p: (0 if p in pack.FOE_BLACK else 8) if p in sil else v
                for p, v in col.items()}
        return foe == want and len(pack.FOE_BLACK) == 4 and pack.FOE_BLACK <= sil
    for tab, nm in ((ring, "δακτύλιος"), (out, "έξω")):
        check(foe_ok(ring, tab),
              f"ο εισβολέας ({nm}) δεν είναι ο άποικος σε κόκκινο με τέσσερα μαύρα")
    # ΑΡΝΗΤΙΚΟ: ο εισβολέας ίδιος με τον άποικο (το pack.py τον ξέχασε).
    bad = bytearray(ring)
    bad[pack.fig_off(jf):pack.fig_off(jf) + 32] = ring[pack.fig_off(jc):pack.fig_off(jc) + 32]
    check(not foe_ok(ring, bytes(bad)), "ΑΡΝΗΤΙΚΟ: ένας κίτρινος εισβολέας περνά τον έλεγχο")
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
    want = b"".join(hudread.font_m1()[:FONT_N]) + b"".join(
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
