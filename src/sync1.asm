; ---------------------------------------------------------------------------
; sync1.asm — το bar_sync (src/bar.asm), ΣΤΟ OV_R1 ΑΠΟ ΤΟ ΒΗΜΑ 199: στη βασική
; τράπεζα 1, όπου τρέχει και το bar_want που καλεί (src/bar1.asm, b1code).
; Τρέχει ΜΟΝΟ με την 1 στο παράθυρο: το καλεί μόνο το ui_panel, και το
; ui_panel ήδη την ήθελε, για το bar_want. Ο κώδικας είναι ο ίδιος byte προς
; byte· οι μεταβλητές του (bsg_was, bs_gen, bs_id, bw_id) μένουν στην τράπεζα
; 0, και ο πίνακας της υπογραφής (bsg_src) έρχεται μαζί του. Τα 156 bytes της
; 0 είναι για το βήμα 200, το κτίριο γραμμή-γραμμή.
; ---------------------------------------------------------------------------
; bar_sync — η μπάρα όπως πρέπει να είναι. Από το ui_panel, ΠΡΙΝ από το ui_hold:
; ένα μήνυμα κρατά τις σειρές 3-4, όχι τα κουμπιά.
; ---------------------------------------------------------------------------
bar_sync:
        ; ΣΥΓΚΡΙΣΗ ΚΑΘΩΣ ΔΙΑΒΑΖΕΙ: 10 us ανά byte, και στο πρώτο που διαφέρει
        ; γράφονται όλα. Τρέχει σε κάθε ui_panel, δηλαδή σε κάθε βήμα κέρσορα.
        ; Τα τρία του πλοίου ωμά (bar_shipok θα ήθελε κλήση): ένα δεύτερο
        ; Control ξαναζητά τη μπάρα χωρίς να αλλάξει τίποτα, και αυτό είναι όλο.
        ld      hl,bsg_was
        ld      a,(ui_state)
        cp      (hl)
        jr      nz,bsc_go
        inc     hl
        ld      a,(ui_sel)
        cp      (hl)
        jr      nz,bsc_go
        inc     hl
        ld      a,(bd_rsel)
        cp      (hl)
        jr      nz,bsc_go
        inc     hl
        ld      a,(ac_sel)
        cp      (hl)
        jr      nz,bsc_go
        inc     hl
        ld      a,(ac_mode)
        cp      (hl)
        jr      nz,bsc_go
        inc     hl
        ld      a,(ac_fit)
        cp      (hl)
        jr      nz,bsc_go
        inc     hl
        ld      a,(hud_gen)             ; σβησμένες λωρίδες: όλα από την αρχή
        cp      (hl)
        jr      nz,bsc_go
        inc     hl
        ld      a,(G_room_n + R_CONTROL)
        cp      (hl)
        jr      nz,bsc_go
        inc     hl
        ld      a,(EC_PADNODE)
        cp      (hl)
        jr      nz,bsc_go
        inc     hl
        ld      a,(EC_SHSTATE)
        cp      (hl)
        ret     z
bsc_go:
        ; Η ΕΓΓΡΑΦΗ ΑΠΟ ΠΙΝΑΚΑ: τρέχει μόνο όταν κάτι άλλαξε, όχι σε κάθε βήμα
        ; κέρσορα όπως η σύγκριση από πάνω, που μένει ξετυλιγμένη.
        ld      hl,bsg_src
        ld      de,bsg_was
        ld      b,BSG_N
bsc_cp:
        ld      a,(hl)
        inc     hl
        push    hl
        ld      h,(hl)
        ld      l,a
        ld      a,(hl)
        ld      (de),a
        pop     hl
        inc     hl
        inc     de
        djnz    bsc_cp
        ld      a,(hud_gen)
        ld      hl,bs_gen
        cp      (hl)
        jr      z,bsc_want
        ld      (hl),a
        ld      hl,bs_id
        ld      b,BAR_N
bsc_inv:
        ld      (hl),BT_NONE - 1        ; καμία θέση δεν είναι αυτό
        inc     hl
        djnz    bsc_inv
bsc_want:
        call    bar_want
        ; --- άλλαξε κουμπί (όχι μόνο χρώμα); τότε και τα πλήκτρα ---
        ld      hl,bw_id
        ld      de,bs_id
        ld      b,BAR_N
bsk_lp:
        ld      a,(de)
        cp      (hl)
        inc     hl                      ; δεν αγγίζουν τις σημαίες
        inc     de
        jr      nz,bsk_gen
        djnz    bsk_lp
bsk_gen:
        call    nz,bk_gen               ; NZ: κάποιο διέφερε
        jp      bar_more                ; src/button.asm, τράπεζα 2

; ---------------------------------------------------------------------------
; bar_want — τι πρέπει να δείχνει η μπάρα: στην τράπεζα 1 από το βήμα 152
; (src/bar1.asm, στη δέσμευση b1code). Γράφει τα bw_id / bw_st από κάτω.
; ---------------------------------------------------------------------------

; Τα bytes της υπογραφής, με τη σειρά της σύγκρισης του bar_sync.
bsg_src:    dw ui_state, ui_sel, bd_rsel, ac_sel, ac_mode, ac_fit, hud_gen
            dw G_room_n + R_CONTROL, EC_PADNODE, EC_SHSTATE
bsg_end:
        assert  bsg_end - bsg_src == 2 * BSG_N
