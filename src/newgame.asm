; newgame.asm — η κατάσταση εκκίνησης του §10.1.
;
; Ως το βήμα 12 αυτό δεν υπήρχε: κάθε δοκιμή έστηνε τον κόσμο της μόνη της, και
; κάθε μία ξεχνούσε κάτι διαφορετικό. Το χειρότερο ήταν ο πίνακας εργασιών —
; το άδειο είναι 255 ενώ το μηδέν σημαίνει «εργασία Build», οπότε ένας πίνακας
; που δεν αρχικοποιήθηκε διαβάζεται ως τριάντα δύο εργασίες Build.
;
; Η ΓΕΝΝΗΤΡΙΑ ΔΕΝ ΕΙΝΑΙ ΕΔΩ. Δεν χωράει: ο κώδικας του παιχνιδιού πιάνει 15,9 KB
; από τα 16,1 της τράπεζας 0 και η γεννήτρια θέλει άλλα 2,9. Είναι ξεχωριστό
; φόρτωμα — τρέχει, γράφει το επίπεδο στην τράπεζα 4, και μετά φορτώνεται το
; παιχνίδι από πάνω της. Δες DESIGN §4.2.

M_OXYGEN    equ 0
M_BEDS      equ 10

NG_SEED     equ #ACE1

; ---------------------------------------------------------------------------
; game_new — από το μηδέν ως το πρώτο frame.
; ---------------------------------------------------------------------------
game_new:
        call    ng_wipe
        call    ng_colony
        call    ng_people
        call    ng_stock
        call    wheel_reset
        call    rt_mark
        jp      ui_init

; ---------------------------------------------------------------------------
; ng_wipe — κάθε πίνακας στην τιμή που σημαίνει «άδειο», και αυτή ΔΕΝ είναι
; πάντα το μηδέν.
; ---------------------------------------------------------------------------
ng_wipe:
        ; --- η οικονομία (τράπεζα 2, πάντα ορατή) ---
        ld      hl,G_econ_state
        ld      de,G_econ_state+1
        ld      bc,85
        ld      (hl),0
        ldir
        ; --- ο πίνακας εργασιών: 255, όχι 0 ---
        ld      hl,G_job_tbl
        ld      b,MAX_JOB
ngw_job:
        ld      (hl),NO_JOB
        push    bc
        ld      bc,JOB_REC
        add     hl,bc
        pop     bc
        djnz    ngw_job
        ; --- ο γράφος ---
        ld      hl,NODE_DEG
        ld      de,NODE_DEG+1
        ld      bc,127
        ld      (hl),0
        ldir
        ; --- οι πίνακες οντοτήτων, στην τράπεζα 6 ---
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        ld      hl,G_node_occ
        ld      de,G_node_occ+1
        ld      bc,255
        ld      (hl),0
        ldir
        ld      hl,G_dome_tbl
        ld      de,G_dome_tbl+1
        ld      bc,MAX_DOME*DOME_REC - 1
        ld      (hl),0
        ldir
        ld      hl,G_struct_tbl
        ld      de,G_struct_tbl+1
        ld      bc,MAX_STRUCT*STRUCT_REC - 1
        ld      (hl),0
        ldir
        ld      hl,G_corr_tbl
        ld      de,G_corr_tbl+1
        ld      bc,MAX_CORR*CORR_REC - 1
        ld      (hl),0
        ldir
        ld      hl,G_agent_fields
        ld      de,G_agent_fields+1
        ld      bc,8*256 - 1
        ld      (hl),0
        ldir
        ; Τρεις στήλες πρακτόρων θέλουν 255, όχι 0: μια ακμή 0 σημαίνει «στον
        ; δρόμο για τον πρώτο γείτονα», μια θέση 0 «στην πρώτη θέση του
        ; δακτυλίου», και μια εργασία 0 «κρατάει την εργασία μηδέν».
        ld      hl,AG_DEST + 128
        call    ng_ff
        ld      hl,AG_NODE + 128
        call    ng_ff
        ld      hl,AG_PROG + 128
        call    ng_ff
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        ret

ng_ff:
        ld      b,128
ngf_lp:
        ld      (hl),255
        inc     hl
        djnz    ngf_lp
        ret

; ---------------------------------------------------------------------------
; ng_colony — τρεις μικροί θόλοι σε Γ, δύο διάδρομοι, και η πλατφόρμα.
;
; ΚΥΛΙΚΕΙΟ, ΟΧΙ ΑΠΟΘΗΚΗ, και αυτό είναι απόκλιση από το §10.1. Το πέρασμα
; αναγκών ψάχνει ΜΟΝΟ ιατρείο, κυλικείο και καταλύματα (§6.6): χωρίς κυλικείο
; κανείς δεν πίνει και δεν τρώει ποτέ, και τα «δύο sols χωρίς να κάνεις τίποτα»
; δεν υπάρχουν — η αποικία πεθαίνει από δίψα με γεμάτες αποθήκες. Το δωμάτιο
; «αποθήκη» δεν το διαβάζει κανένα πέρασμα ακόμη, οπότε ήταν το φθηνότερο να
; θυσιαστεί.
;
; Η απόσταση είναι 16 μισά tiles = 8 tiles: το κενό ανάμεσα σε δύο μικρούς
; θόλους βγαίνει 8 - 2 - 2 = 4 πλακίδια διαδρόμου, ακέραιο, όπως απαιτεί το
; §9.4. Μικρότερη απόσταση δεν αφήνει διάδρομο· μεγαλύτερη σκορπίζει την
; αποικία πριν καν αρχίσει.
; ---------------------------------------------------------------------------
ng_colony:
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        ld      hl,ng_domes
        ld      b,3
        ld      c,0
ngc_lp:
        push    bc
        push    hl
        ld      a,c
        call    ob_domeadr
        ex      de,hl                   ; DE = εγγραφή, HL = πρότυπο
        pop     hl
        push    hl
        ld      bc,4                    ; cx, cy, size, room
        ldir
        ex      de,hl
        ld      (hl),DS_ACTIVE
        inc     hl
        ld      (hl),255                ; ακεραιότητα: χτισμένος
        inc     hl
        ld      (hl),0                  ; ρεύμα
        inc     hl
        ld      (hl),0                  ; χειριστές
        inc     hl
        ld      b,8
ngc_m:
        ld      (hl),NO_MACH
        inc     hl
        djnz    ngc_m
        pop     hl                      ; πίσω στο πρότυπο
        ld      de,5
        add     hl,de                   ; το επόμενο
        pop     bc
        inc     c
        djnz    ngc_lp
        ; --- οι μηχανές, χωριστά: το πρότυπο είναι πέντε bytes και η υποδοχή
        ; είναι μέσα στην εγγραφή, όχι δίπλα της.
        ld      hl,ng_domes+4
        ld      b,3
        ld      c,0
ngc_ml:
        push    bc
        push    hl
        ld      a,(hl)
        cp      NO_MACH
        jr      z,ngc_mn
        ld      e,a
        ld      a,c
        call    ob_domeadr
        ld      bc,D_MACH
        add     hl,bc
        ld      (hl),e                  ; υποδοχή 0
        ld      bc,D_HEALTH - D_MACH
        add     hl,bc
        ld      (hl),200
ngc_mn:
        pop     hl
        ld      de,5
        add     hl,de
        pop     bc
        inc     c
        djnz    ngc_ml
        ; --- η πλατφόρμα προσγείωσης ---
        ld      hl,G_struct_tbl
        ld      (hl),-16                ; cx
        inc     hl
        ld      (hl),16                 ; cy
        inc     hl
        ld      (hl),K_PAD
        inc     hl
        ld      (hl),0                  ; ένα μέγεθος μόνο
        inc     hl
        ld      (hl),DS_ACTIVE
        inc     hl
        ld      (hl),255
        ; --- οι δύο διάδρομοι, γραμμένοι κατευθείαν: στο νέο παιχνίδι δεν
        ; πληρώνονται και δεν χτίζονται.
        ld      hl,G_corr_tbl
        ld      de,ng_corrs
        ex      de,hl
        ld      bc,2*CORR_REC
        ldir
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        ; --- ο κόσμος κάτω από την αποικία ---
        call    ng_stamp
        ; --- ο γράφος: δύο διάδρομοι και μία εξωτερική ακμή ως την πλατφόρμα ---
        ld      b,0
        ld      c,1
        call    cr_edge
        ld      b,1
        ld      c,0
        call    cr_edge
        ld      b,0
        ld      c,2
        call    cr_edge
        ld      b,2
        ld      c,0
        call    cr_edge
        ; Η πλατφόρμα ΔΕΝ συνδέεται με διάδρομο: το §6.2 λέει ότι οι εξωτερικές
        ; δομές έχουν «ακμή εξωτερικού χώρου» και ο κόμβος τους είναι 64+δομή.
        ld      b,2
        ld      c,MAX_DOME
        call    cr_edge
        ld      b,MAX_DOME
        ld      c,2
        jp      cr_edge

; ---------------------------------------------------------------------------
; ng_stamp — θεμέλιο και κατοχή κάτω από κάθε θόλο, την πλατφόρμα και τους
; διαδρόμους. Απαιτεί τράπεζα 1 στην είσοδο.
; ---------------------------------------------------------------------------
ng_stamp:
        ld      hl,ng_rects
        ld      b,4
ngs_lp:
        push    bc
        ld      a,(hl)
        ld      (ngs_x),a
        inc     hl
        ld      a,(hl)
        ld      (ngs_y),a
        inc     hl
        ld      a,(hl)
        ld      (ngs_n),a
        inc     hl
        push    hl
        ld      bc,GA_PORT + PAGE_B4
        out     (c),c
        ld      a,(ngs_n)
        ld      (ngs_r),a
ngs_rl:
        ld      a,(ngs_x)
        ld      b,a
        ld      a,(ngs_y)
        ld      c,a
        call    tile_addr
        ld      a,(ngs_n)
        ld      b,a
ngs_cl:
        ld      a,(hl)
        and     #C0
        or      W_FOUNDATION + W_OCC_STRUCT
        ld      (hl),a
        inc     hl
        djnz    ngs_cl
        ld      a,(ngs_y)
        inc     a
        ld      (ngs_y),a
        ld      a,(ngs_r)
        dec     a
        ld      (ngs_r),a
        jr      nz,ngs_rl
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        pop     hl
        pop     bc
        djnz    ngs_lp
        ; --- και οι δύο διάδρομοι, με τον ίδιο κώδικα που χρησιμοποιεί ο
        ; παίκτης: ο δρομολογητής ξέρει ποια πλακίδια πατά η διαδρομή.
        ld      a,0
        ld      (cr_a),a
        ld      a,1
        ld      (cr_b),a
        call    cr_plan
        or      a
        call    nz,cr_stamp
        ld      a,0
        ld      (cr_a),a
        ld      a,2
        ld      (cr_b),a
        call    cr_plan
        or      a
        ret     z
        jp      cr_stamp

; ---------------------------------------------------------------------------
; ng_people — τέσσερις άποικοι: δύο εργάτες, ένας μηχανικός, μία βιολόγος.
; ---------------------------------------------------------------------------
ng_people:
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        ld      hl,ng_roles
        ld      b,4
        ld      c,0
ngp_lp:
        push    bc
        push    hl
        ld      a,(hl)
        ld      e,a                     ; ρόλος
        inc     hl
        ld      a,(hl)                  ; κόμβος
        ld      d,a
        ld      h,AG_PG
        ld      l,c
        ld      (hl),F_ALIVE + F_INDOORS
        set     7,l
        ld      (hl),e                  ; ρόλος
        ld      h,AG_PG + 1
        ld      l,c
        ld      (hl),d                  ; κόμβος
        ld      h,AG_PG + 2
        ld      l,c
        ld      (hl),d                  ; προορισμός = εκεί που είναι
        ld      a,d
        ld      (em_dst),a
        push    bc
        call    ent_claim
        pop     bc
        ld      h,AG_PG + 1
        ld      l,c
        set     7,l
        ld      (hl),a                  ; η θέση στον δακτύλιο
        ; --- οι ανάγκες γεμάτες: ένας άποικος που ξεκινά στο μηδέν πεθαίνει
        ; πριν προλάβει να περπατήσει ως το ψυγείο.
        ld      h,AG_PG + 4
        call    ng_full
        ld      h,AG_PG + 5
        call    ng_full
        ld      h,AG_PG + 6
        call    ng_full
        pop     hl
        inc     hl
        inc     hl
        pop     bc
        inc     c
        djnz    ngp_lp
        ld      a,4
        ld      (EC_ALIVE),a
        ld      a,8
        ld      (EC_POPCAP),a           ; τρεις μικροί θόλοι
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        ret

; ng_full — και οι δύο στήλες της σελίδας H στο 255, για τον πράκτορα C.
ng_full:
        ld      l,c
        ld      (hl),255
        set     7,l
        ld      (hl),255
        ret

; ---------------------------------------------------------------------------
; ng_stock — τα αποθέματα του §10.1, και το ρολόι.
; ---------------------------------------------------------------------------
ng_stock:
        ld      hl,ng_start_stock
        ld      de,EC_STOCK
        ld      bc,14*2
        ldir
        ld      hl,12000
        ld      (EC_SOLLEN),hl
        ld      hl,7200
        ld      (EC_DAYLEN),hl
        ld      hl,NG_SEED
        ld      (EC_RND),hl
        ld      a,1
        ld      (EC_DAY),a
        ld      (EC_POK),a
        ld      (EC_O2OK),a
        ret

; --- δεδομένα --------------------------------------------------------------
; cx, cy (μισά tiles), μέγεθος, δωμάτιο, μηχανή υποδοχής 0
ng_domes:
        db   0,  0, 0, R_OXYGEN,   M_OXYGEN
        db  16,  0, 0, R_QUARTERS, M_BEDS
        db   0, 16, 0, R_CANTEEN,  NO_MACH

; a, b, dir, len, state — 8 tiles κέντρο σε κέντρο μείον δύο ακτίνες = 4
ng_corrs:
        db 0, 1, 2, 4, DS_ACTIVE        ; ανατολή
        db 0, 2, 4, 4, DS_ACTIVE        ; νότος

; αριστερό tile, πάνω tile, πλευρά — τρεις θόλοι 4x4 και η πλατφόρμα 4x4
ng_rects:
        db  -2, -2, 4
        db   6, -2, 4
        db  -2,  6, 4
        db -10,  6, 4

; ρόλος, κόμβος
ng_roles:
        db 0, 0
        db 0, 1
        db 1, 0
        db 2, 2

ng_start_stock:
        dw 60, 40, 0, 30, 10, 0, 4, 0, 0, 0, 0, 0, 0, 0

ngs_x:      db 0
ngs_y:      db 0
ngs_n:      db 0
ngs_r:      db 0
