; mine.asm — Η ΤΙΜΗ ΚΑΙ ΟΙ ΣΗΜΑΙΕΣ ΤΟΥ ΟΡΥΧΕΙΟΥ (βήμα 123, DESIGN §6.5).
;
; ΣΤΗΝ ΤΡΑΠΕΖΑ 0, ΜΟΝΟ ΣΤΟ ΠΑΙΧΝΙΔΙ. Ζούσαν στο src/terrain.asm, και το
; tests/uitest.asm, που το περιέχει, πέρασε το #3F00 όπου γράφουν οι
; ανιχνεύσεις των δοκιμών (assert, βήμα 97). Εκεί τα δύο είναι ένα ret: στο
; uitest το ορυχείο πληρώνει πάντα, όπως ως το βήμα 122· το bd_half του
; bd_res μένει στο terrain.asm.

; ---------------------------------------------------------------------------
; bd_mprice — ΤΟ ΠΡΩΤΟ ΟΡΥΧΕΙΟ ΔΩΡΕΑΝ (βήμα 123, DESIGN §6.5): αν η επιλογή
; είναι ορυχείο και η αποικία δεν έχει άλλο — έτοιμο ή εργοτάξιο — το bd_metal
; γίνεται 0· αλλιώς η τιμή του καταλόγου. Ετσι η αποικία που έχασε το ορυχείο
; της και το μέταλλό της ξαναρχίζει πάντα: ένα ορυχείο και η μηχανή METAL.
; Μηδενίζει και το bd_half (το ξαναβρίσκει το bd_res). Από το bd_select και
; μετά από κάθε τοποθέτηση (bdk_post), με την 1 στο παράθυρο, που την αφήνει.
; Οι εγγραφές ως το ST_TOP (βήμα 157, src/top.asm), 13 us η καθεμία, μόνο
; όταν διαλέγεται ή μπαίνει ορυχείο. Χαλάει AF,
; BC, DE, HL (βήμα 154: και τον DE, που κανείς από τους δύο καλούντες δεν
; κρατά).
; ---------------------------------------------------------------------------
bd_mprice:
        xor     a
        ld      (bd_half),a
        ld      hl,(bd_kind)            ; L = είδος, H = παράμετρος
        dec     l                       ; BK_STRUCT
        ret     nz
        ld      a,h
        cp      K_MINE
        ret     nz
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        ld      hl,G_struct_tbl + ST_KIND
        ld      de,STRUCT_REC
        ld      a,(ST_TOP)              ; ως την ψηλότερη θέση σε χρήση (βήμα 157)
        ld      b,a
bmp_lp:
        ld      a,(hl)
        cp      K_MINE
        jr      z,bmp_mine
bmp_nx:
        add     hl,de                   ; δύο σελίδες (βήμα 154): 1 us λιγότερο
        djnz    bmp_lp                  ; από το ld a,l / add a,8 / ld l,a
        xor     a                       ; κανένα: δωρεάν
        jr      bmp_set
bmp_mine:
        inc     l
        inc     l                       ; ST_STATE
        ld      a,(hl)
        dec     l
        dec     l
        or      a
        jr      z,bmp_nx                ; άδεια εγγραφή που λέει ακόμη «ορυχείο»
        ld      a,(bld_mine + 4)        ; η τιμή του καταλόγου
bmp_set:
        ld      (bd_metal),a
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        ret

; bd_mflags — HL -> το ST_OWED μιας δομής που μόλις γράφτηκε (bds_got, με
; την 6 στο παράθυρο): ένα ορυχείο κρατά στο ST_OPS αν είναι εκτός φλέβας
; (ST_HALF) και αν μπήκε δωρεάν (ST_FREE). Το bdk_rec το έγραψε 0. Κρατά HL.
bd_mflags:
        ld      a,(bd_param)
        cp      K_MINE
        ret     nz
        dec     hl                      ; ST_OPS
        ld      a,(bd_metal)
        or      a
        ld      a,(bd_half)
        jr      nz,bmf_st
        or      1 << ST_FREE
bmf_st:
        ld      (hl),a
        inc     hl
        ret

