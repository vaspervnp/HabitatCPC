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
        ld      d,EC_STOCK / 256
        ret

        assert  (EC_STOCK & 255) + 2 * 14 <= 256  ; 14 αποθέματα, μία σελίδα

; ec_make — A = απόθεμα, DE = ποσότητα: φτιάχτηκε ΕΔΩ (EC_PRODM, τα ορόσημα
; του §10.2) και μπαίνει στην αποθήκη. Ως το βήμα 45 ήταν δύο κλήσεις σε
; κάθε σημείο που παράγει, με το A και το DE φορτωμένα δύο φορές.
ec_make:
        ld      hl,EC_PRODM
        ld      b,a
        cp      8
        jr      c,ecm_lo
        inc     hl                      ; τα αποθέματα 8-13 στο πάνω byte
        sub     8
ecm_lo:
        ld      c,1
        inc     a
        jr      ecm_e
ecm_sh:
        sla     c
ecm_e:
        dec     a
        jr      nz,ecm_sh               ; C = 1 << A
        ld      a,c
        or      (hl)
        ld      (hl),a
        ld      a,b
        ; fall through

; ec_add_stock — A = απόθεμα, DE = ποσότητα (16 bit: οι αντλίες ξεπερνούν
; εύκολα το 255). Με ταβάνι EC_CAP. Χαλάει AF, BC, DE, HL.
ec_add_stock:
        ex      de,hl                   ; HL = ποσότητα
        call    ec_stock_ptr
        ex      de,hl                   ; HL = &stock, DE = ποσότητα
        ld      c,(hl)
        inc     hl
        ld      b,(hl)                  ; BC = απόθεμα
        ex      de,hl                   ; DE -> το πάνω byte του
        add     hl,bc
        ld      bc,EC_CAP
        or      a
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
