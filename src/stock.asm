; stock.asm — τα αποθέματα: πού κάθεται το καθένα, και η πρόσθεση με ταβάνι.
;
; ΚΟΙΝΑ ΣΕ ΤΡΙΑ BUILDS (βήμα 46). Τα θέλει η οικονομία (src/econ.asm), οι
; ανάγκες και τα πλοία, που ζουν στο main και στο tests/simtest.asm — αλλά και
; ο εξοπλισμός (src/fit.asm), που ζει στο main και στο tests/uitest.asm χωρίς
; οικονομία. Ως το βήμα 45 το fit.asm είχε δικό του αντίγραφο της πρόσθεσης
; (fit_give), επειδή το ec_add_stock ήταν στο econ.asm.

; ec_stock_ptr — A = απόθεμα -> DE = &stock[A]. Το HL μένει, το A χάνεται.
; Ο πίνακας δεν περνά όριο σελίδας, οπότε το D είναι σταθερό: 5 bytes και
; 46 T-states λιγότερα από τη διαδρομή μέσα από το HL, και το ec_have τρέχει
; για κάθε είσοδο κάθε μηχανής.
ec_stock_ptr:
        add     a,a
        add     a,EC_STOCK & 255
        ld      e,a
        ld      d,EC_STOCK >> 8
        ret

        assert  (EC_STOCK & 255) + 2 * 14 <= 256  ; 14 αποθέματα, μία σελίδα

; ec_make — A = απόθεμα, DE = ποσότητα: φτιάχτηκε ΕΔΩ (EC_PRODM, τα ορόσημα
; του §10.2) και μπαίνει στην αποθήκη. Ως το βήμα 45 ήταν δύο κλήσεις σε
; κάθε σημείο που παράγει, με το A και το DE φορτωμένα δύο φορές.
ec_make:
        ld      hl,EC_PRODM
        ld      c,a                     ; το απόθεμα, για το ec_add_stock
        cp      8
        jr      c,ecm_lo
        inc     hl                      ; τα αποθέματα 8-13 στο πάνω byte
ecm_lo:
        and     7
        ld      b,a
        inc     b
        ld      a,#80
ecm_sh:
        rlca
        djnz    ecm_sh                  ; A = 1 << (απόθεμα & 7): το #80 n+1 φορές
        or      (hl)
        ld      (hl),a
        ld      a,c
        ; fall through

; ec_add_stock — A = απόθεμα, DE = ποσότητα (16 bit: οι αντλίες ξεπερνούν
; εύκολα το 255). Με ταβάνι EC_CAP. Χαλάει AF, BC, DE, HL.
; Το άθροισμα δεν περνά ποτέ το 65.535 (το απόθεμα είναι ως το EC_CAP, η
; μεγαλύτερη ποσότητα οι αντλίες και τα ορυχεία ενός κύκλου, εκατοντάδες), άρα
; το add hl,bc αφήνει CY = 0 και το sbc δεν θέλει `or a` πριν (βήμα 69).
ec_add_stock:
        ex      de,hl                   ; HL = ποσότητα
        call    ec_stock_ptr
        ex      de,hl                   ; HL = &stock, DE = ποσότητα
        ld      c,(hl)
        inc     hl
        ld      b,(hl)                  ; BC = απόθεμα
        ex      de,hl                   ; DE -> το πάνω byte του
        add     hl,bc                   ; CY = 0: απόθεμα + ποσότητα < 65.536
        ld      bc,EC_CAP
        sbc     hl,bc
        add     hl,bc                   ; CY αν κάτω από το ταβάνι
        jr      c,eas_st
        ld      h,b
        ld      l,c
eas_st:
        ex      de,hl
        ld      (hl),d
        dec     hl
        ld      (hl),e
        ret

; --- Ο ΕΜΠΟΡΟΣ (βήμα 93, DESIGN §6.11) --------------------------------------
; Ανά απόθεμα: η αξία του, και η μονάδα του βέλους στη γραμμή του εμπόρου, που
; είναι και η μονάδα του φορτίου του (φέρνει 1-4). Οι αξίες είναι του
; Planetbase: meal 5, ore 10, metal 15, bioplastic 10, semiconductors 40,
; spares 15, medical supplies 25, gun 80, starch, vegetables, vitromeat 5,
; medicinal plants 10. Το ρομπότ 120, ανάμεσα στο ρομπότ μεταφοράς (80) και
; κατασκευής (160): εδώ ένα Bot γίνεται εναλλάξ το ένα ή το άλλο. Το νερό 0:
; δεν είναι εμπόρευμα, όπως εκεί. Το tools/econ.py έχει τους ίδιους πίνακες
; (TRADE_VALUE, TRADE_LOT). Εδώ, και όχι στη γραμμή, επειδή το φορτίο το
; φτιάχνει ο τροχός (src/ship.asm, που ζει και στο tests/simtest.asm).
tr_value:   db 0, 5, 10, 15, 10, 40, 15, 25, 80, 120, 5, 5, 10, 5
tr_lot:     db 0, 10, 10, 5, 10, 2, 5, 4, 1, 1, 10, 10, 10, 10
