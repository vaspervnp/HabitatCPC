; full6.asm — το ec_setfull, στις ουρές των σελίδων πεδίων της τράπεζας 6
; (βήμα 188, DESIGN §4.2).
;
; ΟΙ ΟΥΡΕΣ: τα ids 188-255 των σελίδων AG_PG + 0..B6T_N-1, B6T_LEN bytes η
; καθεμιά (B6T_0, src/const.asm). Κανένας πράκτορας δεν είναι εκεί (N_AGENT
; 188), και η κρυφή μνήμη φιγούρων είναι στις σελίδες 8-15. Τις φέρνει η
; B6TAIL.BIN (src/boot.asm), το game_new τις αφήνει (src/newgame.asm), και κάθε
; φόρτωμα τις κρατά στην άκρη όπως το b6x (src/keep6.asm). Τρέχουν με την 6.
;
; ΤΟ ec_setfull ΣΕ ΔΥΟ ΚΟΜΜΑΤΙΑ, ένα ανά ουρά: το δεύτερο, το esf_keep, ήταν
; η συνέχειά του. Στο τέλος του πρώτου, το mt_site του βήματος 200. Στο tests/simtest.asm το B6T_PIECE δεν κάνει τίποτα, και
; το jp πάει στην επόμενη εντολή.

; ec_setfull — A = 0 ή 1: το ec_full (src/stock.asm) και ο κώδικας που το
; ακούει χωρίς να το διαβάζει (βήμα 122). Ενα «ld a,(ec_full) / or a» σε κάθε
; μηχανή και σε κάθε κήπο κόστιζε ~170 us στην επίσκεψη των θόλων 0-15 της
; αποικίας του tests/test_sim.py (12,5 ms, η βαρύτερη της θέσης 11) για κάτι
; που αλλάζει σπάνια: εδώ αλλάζει η τρίτη κλήση του ec_run_mach (erm_in ή
; erm_inf) και το «or a» του κήπου (ή «xor a», που αφήνει πάντα Z). Από το
; st_need (src/need6.asm) και το wheel_reset, με την 6 μέσα (στην τράπεζα 0
; ως το βήμα 187). Χαλάει AF, C, HL.
ec_setfull:
        ld      (ec_full),a
        or      a
        ld      hl,erm_in
        ld      de,256 * S_WATER + #3E  ; ld a,S_WATER: ο κήπος όπως ήταν
        jr      z,esf_put
        ; ΓΕΜΑΤΗ (βήμα 142): το σπανιότερο υλικό του γεύματος — το ec_need, που
        ; το erm_inf το διαβάζει ως απόθεμα — και στο erp_chk ως κατηγορία φυτού
        ; (άμυλο 0, λαχανικά 1· το κρέας δεν το βγάζει κανένα φυτό, #FF).
        ld      a,(ec_need)
        sub     S_STARCH
        cp      2
        jr      c,esf_cls
        ld      a,#FF
esf_cls:
        ld      (erp_cls + 1),a
        ld      hl,erm_inf
        ld      de,#18 + 256 * (erp_chk - erp_full - 2)   ; jr erp_chk
esf_put:
        ld      (erm_c3 + 1),hl
        ld      (erp_full),de
        jp      esf_keep                ; η επόμενη ουρά
        assert  erp_chk - erp_full - 2 < 128 && NEED_MIN < 256 && S_WATER == 0

; mt_site — ο μετεωρίτης σε εργοτάξιο (mt_hit, src/meteor.asm), στο τέλος της
; ουράς 1 από το βήμα 200: η ουρά 0 γέμισε με το sp_dlv (src/rise6.asm), και στο
; b6code δεν χωρούσε. HL -> D_INTEG = ST_INTEG, C = ο κόμβος. Χάνει την πρόοδο
; του χτίστη. Οσο χρωστά φορτία, η ακεραιότητα είναι το μερίδιο που έφτασε και
; μένει, όπως έμενε ως το βήμα 199 το 0 της εκεί.
mt_site:
        inc     hl
        ld      a,c
        cp      MAX_DOME
        ld      a,(hl)                  ; D_POWER
        inc     hl
        jr      c,mts_d
        xor     a                       ; δομή: μόνο το ST_OWED
mts_d:
        or      (hl)                    ; D_OPS, ή ST_OWED
        ret     nz
        dec     hl
        dec     hl
        ld      (hl),0
        ret
        assert  D_OPS == D_INTEG + 2 && ST_OWED == ST_INTEG + 2

        B6T_PIECE 2

; esf_keep — ΚΑΙ ΤΟ ΑΠΟΘΕΜΑ ΜΕΤΑΛΛΟΥ (βήμα 127) ΚΑΙ ΤΟ ΟΡΙΟ ΤΟΥ ΒΙΟΠΛΑΣΤΙΚΟΥ
; (βήμα 138): τα δύο bits του ec_keep διαλέγουν την πρώτη κλήση εισόδου από
; τις τέσσερις. Οσο υπάρχει μέταλλο και το βιοπλαστικό είναι κάτω από BIO_MAX,
; τίποτα δεν κοστίζει· με το ένα από τα δύο, όσο κόστιζε το απόθεμα μετάλλου
; μόνο του. Πρόσθεση 16 bits, όχι σελίδα: οι δοκιμές βάζουν τον κώδικα αλλού.
; ΚΑΙ ΤΟ ΟΡΙΟ ΤΩΝ ΑΝΤΑΛΛΑΚΤΙΚΩΝ (βήμα 144): το bit 2 διαλέγει τη δεύτερη κλήση,
; erm_in ή erm_inp. Τα δύο κάτω την πρώτη, όπως ως τώρα.
esf_keep:
        ld      a,(ec_keep)
        ld      hl,erm_in
        bit     2,a
        jr      z,esf_c2
        ld      hl,erm_inp
esf_c2:
        ld      (erm_c2 + 1),hl
        and     3
        add     a,a
        ld      hl,esf_tab
        add     a,l
        ld      l,a
        adc     a,h
        sub     l
        ld      h,a
        ld      a,(hl)
        inc     hl
        ld      h,(hl)
        ld      l,a
        ld      (erm_c1 + 1),hl
        ret
esf_tab:
        dw      erm_in, erm_inb, erm_ink, erm_inkb      ; ec_keep 0-3
