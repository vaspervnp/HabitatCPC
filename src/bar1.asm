; bar1.asm — τι πρέπει να δείχνει η μπάρα (βήμα 84· στην τράπεζα 1 από το 152)
;
; ΖΕΙ ΣΤΗ ΔΕΣΜΕΥΣΗ b1code, μετά το src/commit.asm. Το καλεί μόνο το bar_sync
; (src/bar.asm, τράπεζα 0), από την αρχή του ui_panel, και το UI τρέχει με την
; τράπεζα 1 στο παράθυρο (src/commit.asm). Κανένας βοηθός του δεν σελιδοποιεί:
; το ob_addu, το rm_fits (rm_at, rm_build, και οι πίνακες των δωματίων στη 2),
; το mer_here, το ac_cur. Και ό,τι γράφει (bw_id, bw_st, bw_fitp, bw_fitm) είναι
; μεταβλητές του src/bar.asm στην τράπεζα 0.
;
; Ως το βήμα 151 ήταν στην τράπεζα 0, που είχε 18 bytes. Τα 48 κτίσματα θέλουν
; εκεί κώδικα για τις αποστάσεις: το bar_want δεν κοστίζει τίποτα στην 1, γιατί
; η κλήση είναι ίδια (call, 17 T) και τρέχει μόνο όταν η υπογραφή της μπάρας
; αλλάξει.

bar_want:
        ld      hl,bw_id
        ld      de,bw_st
        ld      b,BAR_N
        xor     a                       ; BS_GREEN
bww_c1: ld      (hl),BT_NONE
        inc     hl
        ld      (de),a
        inc     de
        djnz    bww_c1
        assert  BS_GREEN == 0
        dec     hl                      ; HL = bw_st = bw_id + BAR_N -> bw_id + BAR_HELP
        ld      (hl),BT_HELP
        assert  BAR_HELP == BAR_N - 1
        ld      a,(ui_state)
        cp      UI_ACT
        jr      z,bww_act
        cp      UI_LINK
        jr      z,bww_corr
        dec     a                       ; MENU 0, PLACE 1
        cp      2
        jr      nc,bww_groups
        ; --- MENU, PLACE: η ομάδα του αντικειμένου ---
        ld      a,(ui_sel)
        ld      hl,bld_grp
        call    ob_addu
        ld      a,(hl)
        cp      G_CORR
        jr      z,bww_corr
        push    af                      ; CY = G_DOMES, η μόνη ομάδα κάτω από το G_CORR
        ld      de,BLD_N                ; bld_btn = bld_grp + BLD_N (src/act.asm)
        add     hl,de
        ld      e,(hl)                  ; το κουμπί του, στο E: το bww_group
        call    bww_group               ; δεν αγγίζει το DE
        ld      a,e
        call    bww_lit
        pop     af
        jp      c,bww_domes
        assert  G_DOMES == 0 && G_CORR == 1
        cp      G_TRANS
        ret     nz
bww_trans:
        call    bar_shipok
        jr      nz,bwt_mer
        ld      a,BT_SHIP
        call    bww_red
bwt_mer:
        ; ΤΟ ΕΜΠΟΡΙΟ ΜΟΝΟ ΟΣΟ ΕΙΝΑΙ ΕΔΩ (βήμα 93). Αλλάζει με το EC_SHSTATE,
        ; που είναι ήδη στην υπογραφή· το είδος αλλάζει μόνο μαζί του, ή στη
        ; συμφωνία (SK_DEALT, βήμα 98), που αλλάζει και το ui_state.
        call    mer_here
        ret     z
        ld      a,BT_TRADE
        jr      bww_red
bww_act:
        ld      a,(ac_mode)
        or      a
        jr      z,bww_agrp
        ; ΟΙ ΓΡΑΜΜΕΣ (src/lines.asm) ΔΕΙΧΝΟΥΝ ΤΗ ΜΕΤΑΦΟΡΑ, με το κουμπί τους
        ; λευκό: του πλοίου (91) και του εμπόρου (93). Ως το 93 η γραμμή του
        ; πλοίου έδειχνε τη ΔΙΑΧΕΙΡΙΣΗ — και τα γράμματά της δούλευαν από εκεί.
        cp      CW_MODE
        jr      c,bww_man
        add     a,BT_SHIP - CW_MODE
        push    af
        ld      a,G_TRANS
        call    bww_group
        call    bww_trans               ; τα κόκκινα, και μετά το λευκό από πάνω
        pop     af
        jr      bww_lit
bww_man:
        ld      a,G_MANAGE
        call    bww_group
        ld      a,(ac_fit)              ; AF_FIT, AF_DEMO (src/act.asm)
        rra
        push    af
        ld      a,BT_FIT
        call    nc,bww_red
        pop     af
        rra
        ld      a,BT_DEMO
        call    nc,bww_red
        jr      bww_asel
bww_agrp:
        call    bww_groups
bww_asel:
        call    ac_cur                  ; A = το διαλεγμένο κουμπί (src/act.asm)
        jr      bww_lit
bww_corr:
        call    bww_groups
        ld      a,BT_CORR
        jr      bww_lit
bww_groups:
        ld      hl,ac_l_grp
        ld      de,bw_id
        ld      bc,6
        ldir
        ret
; bww_group — A = ομάδα: τα κουμπιά της από τη θέση 0, η ίδια λευκή.
bww_group:
        ld      hl,ac_l_grp
        call    ob_addu
        ld      c,(hl)                  ; το πρώτο κουμπί
        inc     hl
        ld      a,(hl)                  ; το πρώτο της επόμενης (ή το ?)
        sub     c
        ld      b,a                     ; πόσα
        ld      a,c
        ld      hl,bw_id
bwg_lp:
        ld      (hl),a
        inc     a
        inc     hl
        djnz    bwg_lp
        ld      a,BS_WHITE
        ld      (bw_st),a
        ret

; bww_lit — A = κουμπί: λευκό, αν είναι στη μπάρα. bww_red — κόκκινο.
; bww_st — με C = κατάσταση. Κρατούν το DE.
bww_lit:
        ld      c,BS_WHITE
        db      #21                     ; ld hl,nn: προσπερνά το ld c,BS_RED· το HL το γράφει το bww_st
bww_red:
        ld      c,BS_RED
bww_st:
        ld      hl,bw_id
        ld      b,BAR_N
bwl_lp:
        cp      (hl)
        jr      z,bwl_hit
        inc     hl
        djnz    bwl_lp
        ret
bwl_hit:
        ld      a,BAR_N
        call    ob_addu
        ld      (hl),c
        ret

; bar_shipok — φεύγει πλοίο αν το ζητήσεις; A = 1 και NZ ναι, A = 0 και Z όχι.
; Οι τρεις όροι του ui_ship (src/ui.asm): αίθουσα ελέγχου, πίστα, κανένα άλλο.
bar_shipok:
        ld      a,(G_room_n + R_CONTROL)
        or      a
        ret     z
        ld      a,(EC_PADNODE)
        inc     a
        ret     z
        ld      a,(EC_SHSTATE)
        or      a
        jr      nz,bso_no
        inc     a
        ret
bso_no:
        xor     a
        ret

; (bww_domes: στο τέλος, ώστε ο διαλογέας του bar_want να φτάνει με jr)
bww_domes:
        ld      a,(bd_rsel)
        add     a,BT_ROOM0
        call    bww_lit
        ; ΤΑ ΚΟΚΚΙΝΑ ΑΝΑ ΜΕΓΕΘΟΣ, ΜΙΑ ΦΟΡΑ: δέκα rm_fits είναι 3,3 ms, και ό,τι
        ; λένε εξαρτάται μόνο από το μέγεθος (assets: room_machines,
        ; machine_rules). Το bw_fitm έχει bit 1 για όποιο δεν χωρά.
        ld      a,(bd_param)
        ld      hl,bw_fitp
        cp      (hl)
        jr      z,bwd_have
        ld      (hl),a
        ld      c,RM_N - 1              ; (το DE μπαίνει από δεξιά: μετρούν μόνο τα
bwd_lp:                                 ; κάτω RM_N bits του bw_fitm)
        ld      a,c
        call    rm_fits                 ; κρατά BC, DE
        add     a,a                     ; CY = δεν χωρά
        rl      e
        rl      d
        dec     c
        jp      p,bwd_lp
        ld      (bw_fitm),de
bwd_have:
        ld      de,(bw_fitm)
        ld      a,BT_ROOM0              ; το κουμπί του δωματίου 0
bwd_mk:
        srl     d
        rr      e
        jr      nc,bwd_ok
        push    af
        call    bww_red                 ; κρατά το DE
        pop     af
bwd_ok:
        inc     a
        cp      BT_ROOM0 + RM_N
        jr      c,bwd_mk
        ret
