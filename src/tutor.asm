; ---------------------------------------------------------------------------
; tutor.asm — τα βήματα του tutorial (βήμα 149, DESIGN §9.6). ΚΟΜΜΑΤΙ ΤΩΝ
; ΤΡΥΠΩΝ, στο OV_R1 από το βήμα 155 (src/main.asm): το φέρνει στο GH_BUF
; το tu_run (src/demolish.asm) με το φάντασμα σβηστό, όπως την κατεδάφιση.
;
; Ο ΧΡΗΣΤΗΣ: «πρέπει να υπάρχει και ένα tutorial (σε barren moon) για το πως
; λειτουργεί το παιχνίδι», με βήματα που οδηγούν. Η έκτη γραμμή του μενού,
; TUTORIAL, φτιάχνει πάντα τον ίδιο κόσμο της σελήνης (TU_SEED, src/gen.asm),
; και η γραμμή των πλήκτρων κάτω από τα κουμπιά λέει τι να χτίσει: δεκατέσσερα
; βήματα, από τον ηλιακό ως το πρώτο πλοίο. Δεκατρία ήταν το σχέδιο· ο παίκτης
; του tools/play.py είδε με έναν ηλιακό το ρεύμα κομμένο το 60% του χρόνου ως
; το πλοίο, και ο χρήστης διάλεξε έναν δεύτερο μετά το κυλικείο (DESIGN §9.6).
; Το επόμενο έρχεται μόλις ΜΠΕΙ το κτίσμα του τρέχοντος — το εργοτάξιο
; μετράει — ή η μηχανή που λέει. Μετά
; «THE COLONY IS YOURS», ώς το επόμενο γεγονός, και η γραμμή γίνεται ξανά ό,τι
; ήταν. Ως το τέλος κανένας κίνδυνος: οι καταστροφές θέλουν είκοσι αποίκους
; (DIS_POP), και πλοίο αποίκων έρχεται μόνο με το τελευταίο βήμα· οι βλάβες,
; που είναι φθορά από την αρχή, σβήνουν εδώ (ev_fmask, src/econ.asm).
;
; ΠΟΤΕ ΤΡΕΧΕΙ. Οχι σε κάθε frame: σε ΓΕΓΟΝΟΤΑ, που μόνο αυτά τελειώνουν ένα
; βήμα — η τοποθέτηση (uip_fire), ο εξοπλισμός (ui_redo, μετά από κάθε πλήκτρο
; του FIT), το πλοίο (ui_ship) — και στην εκκίνηση και μετά από κάθε φόρτωμα.
; Τα γεγονότα καλούν το tu_ev, που είναι ret όσο δεν τρέχει tutorial: ένα call
; και ένα ret σε κάθε άλλο παιχνίδι. Κάθε φορά ξαναμετρά ΟΛΟ το βήμα από τους
; πίνακες — δεν ρωτά τι έγινε — άρα και ό,τι χτίστηκε νωρίτερα από τη σειρά του
; περνά μόλις έρθει.
;
; ΤΟ ΒΗΜΑ ΣΩΖΕΤΑΙ: EC_TU, ένα byte στα άδεια του node_occ (src/const.asm), στο
; μπλοκ οντοτήτων του σωσίματος. 0 όσο δεν είναι κόσμος του tutorial, 1-14 τα
; βήματα, 15 το μήνυμα, 16 τέλος. Ο κόσμος το λέει στο bit 7 του τέταρτου
; byte του worldinfo (src/gen.asm), που σώζεται κι αυτό. Στην εκκίνηση το
; tu_run τρέχει ΠΡΙΝ από το game_new (src/main.asm), που το μηδενίζει: ως το
; πρώτο γεγονός το EC_TU είναι 0, και το 0 σε κόσμο του tutorial είναι το βήμα 1.
;
; ΤΟ ΚΕΙΜΕΝΟ. Δεκαέξι γραμμές των 32 bytes ΠΡΙΝ από τον κώδικα, συνεχείς στο
; OV_R1 από το βήμα 155 (TU_TXT· ως τότε μία ανά τρύπα του DIST, μετά τον
; κώδικα): δεν έρχονται στο GH_BUF, φέρνει μία κάθε φορά ένα ldir, και
; πάει στο x_t_look της τράπεζας 7 — εκεί που το διαβάζει η γραμμή του LOOK
; όπως πάντα (ui_panel): ο δρόμος που τη ζωγραφίζει δεν άλλαξε ούτε ένα byte.
; Το x_t_look έχει 33 χαρακτήρες· ο 33ος είναι κενό στα βήματα και το «P» του
; «C=SHIP» στη γραμμή που ήταν (assert στο src/uitext.asm).
; ---------------------------------------------------------------------------

TU_N        equ 14                      ; τα βήματα
TU_YOURS    equ TU_N + 1                ; «THE COLONY IS YOURS», και η γραμμή του ως το LOOK
TU_STRUCT   equ #80                     ; tuo_tab: δομές αυτού του είδους, όσες λέει το δεύτερο byte
TU_SHIP     equ #FF                     ; tuo_tab: πλοίο αποίκων στον δρόμο
TU_ROOM     equ #FF                     ; δεύτερο byte: φτάνει το δωμάτιο
TU_ANY      equ #FE                     ; δεύτερο byte: ό,τι κι αν μπει σε υποδοχή (φυτά)
TU_METAL    equ 1                       ; οι μηχανές, με τη σειρά του MACH του tools/pack.py
TU_MEALS    equ 6
TU_MEAT     equ 9
        assert  SK_COLONIST == 0 && EC_SHKIND == EC_SHSTATE + 1
        assert  ST_STATE == ST_KIND + 2 && DS_EMPTY == 0     ; και M_OXYGEN == 0 (src/newgame.asm)
        assert  (G_struct_tbl & 7) == 0 && STRUCT_REC == 8

; tuo_go — από το tu_run, με την 1 στο παράθυρο. Γυρίζει με την 1.
tuo_go:
        call    ob_b6                   ; θόλοι, δομές, EC_TU, worldinfo
        ld      a,(EC_TU)
        cp      TU_YOURS
        jr      nz,tuo_new
        inc     a                       ; το μήνυμα κράτησε ως αυτό το γεγονός
tuo_new:
        or      a
        jr      nz,tuo_lp
        ld      a,(G_worldinfo + 3)
        add     a,a                     ; bit 7: κόσμος του tutorial
        ld      a,0
        adc     a,a                     ; 1, το πρώτο βήμα· 0, κανένα tutorial
        jr      z,tuo_set
tuo_lp:
        ld      (tuo_s),a
        cp      TU_YOURS
        jr      nc,tuo_set
        call    tuo_done                ; CY: το βήμα A έγινε
        ld      a,(tuo_s)
        jr      nc,tuo_set
        inc     a
        jr      tuo_lp
tuo_set:
        ld      (EC_TU),a
        ld      (tuo_s),a
        ; --- η γραμμή: 0-13 τα βήματα και το μήνυμα, 14 η γραμμή που ήταν ---
        dec     a
        cp      TU_YOURS
        jr      c,tuo_txt
        ld      a,TU_YOURS
tuo_txt:
        ld      (tuo_i),a
        ld      l,a
        ld      h,0
        add     hl,hl
        add     hl,hl
        add     hl,hl
        add     hl,hl
        add     hl,hl                   ; HL = A * 32
        ld      de,TU_TXT
        add     hl,de
        call    ov_b1                   ; src/demolish.asm
        ld      de,tuo_buf
        ld      bc,32
        ldir                            ; από το OV_R1 (βήμα 155)
        ld      bc,GA_PORT + PAGE_B7
        out     (c),c
        ld      hl,tuo_buf
        ld      de,t_look
        ld      bc,32
        ldir
        ld      a,(tuo_i)
        cp      TU_YOURS
        ld      a,' '
        jr      nz,tuo_33
        ld      a,'P'                   ; το τέλος του «C=SHIP»
tuo_33:
        ld      (de),a
        ; --- οι βλάβες σβηστές στα βήματα (or αντί για and στο ev_fault) ---
        ld      a,(tuo_s)
        dec     a
        cp      TU_N
        ld      a,#E6                   ; and n
        jr      nc,tuo_flt
        ld      a,#F6                   ; or n: ποτέ μηδέν, καμία βλάβη
tuo_flt:
        ld      (ev_fmask),a
        ; --- και τα γεγονότα το φέρνουν στα βήματα και στο μήνυμα ---
        ld      a,(tuo_s)
        dec     a
        cp      TU_YOURS
        ld      a,#C9                   ; ret
        jr      nc,tuo_ev
        xor     a                       ; nop
tuo_ev:
        ld      (tu_ev),a
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        ret

; tuo_done — A = βήμα 1-14. CY αν έγινε. Η 6 στο παράθυρο.
tuo_done:
        add     a,a
        ld      e,a
        ld      d,0
        ld      hl,tuo_tab - 2
        add     hl,de
        ld      a,(hl)
        inc     hl
        ld      e,(hl)
        cp      TU_SHIP
        jr      z,tuo_ship
        bit     7,a
        jr      nz,tuo_st
        ; --- θόλος με δωμάτιο A — εργοτάξιο ή χτισμένος — και μηχανή E ---
        ld      c,a
        ld      ix,G_dome_tbl
        ld      b,MAX_DOME
tuo_dlp:
        ld      a,(ix+D_STATE)
        or      a
        jr      z,tuo_dnx
        ld      a,(ix+D_ROOM)
        cp      c
        jr      nz,tuo_dnx
        ld      a,e
        cp      TU_ROOM
        scf
        ret     z
        push    bc
        push    ix
        pop     hl
        ld      bc,D_MACH
        add     hl,bc
        ld      b,8                     ; οι άδειες είναι NO_MACH (bd_commit)
tuo_mlp:
        ld      a,(hl)
        cp      e
        jr      z,tuo_got
        inc     a                       ; NO_MACH
        jr      z,tuo_mnx
        ld      a,e
        cp      TU_ANY
        jr      z,tuo_got
tuo_mnx:
        inc     hl
        djnz    tuo_mlp
        pop     bc
tuo_dnx:
        push    de
        ld      de,DOME_REC
        add     ix,de
        pop     de
        djnz    tuo_dlp
        or      a
        ret
tuo_got:
        pop     bc
        scf
        ret
        ; --- E δομές του είδους A & #7F, εργοτάξια ή χτισμένες ---
tuo_st:
        and     #7F
        ld      c,a
        ld      hl,G_struct_tbl + ST_KIND
        ld      b,MAX_STRUCT
tuo_slp:
        ld      a,(hl)
        cp      c
        jr      nz,tuo_snx
        inc     l
        inc     l
        ld      a,(hl)                  ; ST_STATE
        dec     l
        dec     l
        or      a
        jr      z,tuo_snx
        dec     e
        scf
        ret     z
tuo_snx:
        ld      a,l
        add     a,STRUCT_REC
        ld      l,a
        jr      c,tuo_pg                ; δύο σελίδες (βήμα 154): 2 us ανά εγγραφή
tuo_sc:
        djnz    tuo_slp
        or      a
        ret
tuo_pg:
        inc     h                       ; μία φορά, στο τέλος της πρώτης σελίδας
        jr      tuo_sc
        ; --- πλοίο αποίκων στον δρόμο: το έφερε το C ---
tuo_ship:
        ld      hl,(EC_SHSTATE)         ; L = κατάσταση, H = είδος
        ld      a,l
        or      a
        ret     z
        ld      a,h
        or      a                       ; SK_COLONIST
        ret     nz
        scf
        ret

; Ενα ζευγάρι ανά βήμα: δωμάτιο και μηχανή, TU_STRUCT | είδος και πόσες, ή
; TU_SHIP.
tuo_tab:
        db      TU_STRUCT | K_SOLAR, 1          ;  1 ηλιακός
        db      R_OXYGEN, M_OXYGEN              ;  2 θόλος οξυγόνου, με τη μηχανή του
        db      TU_STRUCT | K_AIRLOCK, 1        ;  3 airlock
        db      TU_STRUCT | K_EXTRACT, 1        ;  4 αντλία
        db      R_CANTEEN, TU_MEALS             ;  5 κυλικείο με MEALS
        db      TU_STRUCT | K_SOLAR, 2          ;  6 δεύτερος ηλιακός
        db      TU_STRUCT | K_COLLECT, 1        ;  7 συλλέκτης
        db      TU_STRUCT | K_MINE, 1           ;  8 ορυχείο
        db      R_FACTORY, TU_METAL             ;  9 εργοστάσιο με METAL
        db      R_GREENHS, TU_ANY               ; 10 θερμοκήπιο με φυτά
        db      R_LAB, TU_MEAT                  ; 11 εργαστήριο με MEAT
        db      R_CONTROL, TU_ROOM              ; 12 έλεγχος
        db      TU_STRUCT | K_PAD, 1            ; 13 πίστα
        db      TU_SHIP, 0                      ; 14 πλοίο
        assert  $ - tuo_tab == 2 * TU_N
tuo_s:      db 0                        ; το βήμα
tuo_i:      db 0                        ; η γραμμή του κειμένου
tuo_buf     equ $                       ; 32 bytes, μετά τον κώδικα: δεν γράφονται
