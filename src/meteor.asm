; meteor.asm — η βροχή μετεωριτών (DESIGN §6.10).
;
; ΜΙΑ ΖΑΡΙΑ ΑΠΟ ΤΙΣ ΤΡΕΙΣ ΠΟΥ ΥΠΑΡΧΟΥΝ ΗΔΗ. Το econ_events τραβά πάντα r1, r2,
; r3, και κάθε συμβάν κοιτά άλλο κομμάτι τους. Η βροχή ζητά τα δώδεκα ψηλά bits
; του r1 ΟΛΑ ΕΝΑ: 1 στις 4.096 περιστροφές, μία βροχή κάθε ~5 sol. Τα άλλα
; συμβάντα ζητούν ΜΗΔΕΝΙΚΑ, και ο Galois ολισθαίνει δεξιά — τα ίδια bits της
; ροής ξαναβγαίνουν μετατοπισμένα στο r2 και στο r3. Με «όλα ένα» η βροχή δεν
; πέφτει ποτέ στον ίδιο γύρο με θύελλα, βλάβη, έκλαμψη ή επισκέπτη· με «όλα
; μηδέν» θα έπεφτε μαζί με τη θύελλα τη μισή φορά.
;
; ΔΙΚΗ ΤΗΣ ΓΕΝΝΗΤΡΙΑ ΓΙΑ ΤΙΣ ΘΕΣΕΙΣ. Μετά από δώδεκα γνωστά bits η κατάσταση
; του Galois είναι σχεδόν γνωστή για τις επόμενες περιστροφές — τρία καινούργια
; bits ανά περιστροφή — και κάθε βροχή θα έπεφτε με το ίδιο σχήμα. Ούτε γίνεται
; να τραβήξει περισσότερα από τη γεννήτρια των συμβάντων: μια ζαριά υπό όρους
; αλλάζει την ακολουθία όλων των επόμενων (§6.10). Η EC_MRND σπέρνεται από το
; r1 και το ρολόι, και προχωρά οκτώ βήματα ανά κρούση: ένα καινούργιο byte.
;
; ΤΙ ΧΤΥΠΑ. Οκτώ κρούσεις, μία ανά περιστροφή (~2,6 s), σε ένα τετράγωνο 16x16
; tiles γύρω από ένα τυχαίο κτίριο. Η απλωμένη βάση χάνει λιγότερα — αυτό είναι
; το αντίδοτο του §6.10.
;   θόλος σε λειτουργία   σταματά μία μηχανή του: μηχανικός και ανταλλακτικό
;   δομή σε λειτουργία    ξαναγίνεται εργοτάξιο, ακεραιότητα 0, και ξαναχτίζεται
;   εργοτάξιο             χάνει την πρόοδό του (ακεραιότητα 0)
;   ελεύθερο έδαφος       κρατήρας στον χάρτη — εκεί δεν χτίζεται πια
;   διάδρομος, νερό, βουνό, κρατήρας   τίποτα
; Το «καταστρέφει τυχαίες δομές» του §6.10 έγινε «τις γυρίζει σε εργοτάξιο»: η
; πρόοδος ΕΙΝΑΙ η ακεραιότητα (src/jobs.asm, ja_build), οπότε μισοχτισμένο και
; μισοκατεστραμμένο είναι ήδη το ίδιο πράγμα, και η επισκευή είναι η κατασκευή.
; Το σβήσιμο μιας δομής θα ήθελε αφαίρεση ακμής από τον γράφο, πράκτορες
; πάνω της και εργασίες προς αυτήν — κώδικας που δεν υπάρχει πουθενά.
;
; Η αναφορά σε Python είναι το tools/econ.py (meteor_tick) και το tests/test_sim.py
; τα συγκρίνει byte προς byte. Τον κρατήρα δεν τον ξέρει η αναφορά — δεν έχει
; κόσμο — και τον ελέγχει το tests/test_meteor.py στο κανονικό binary.

METEOR_N    equ 8                       ; κρούσεις ανά βροχή

; ---------------------------------------------------------------------------
; mt_tick — από το econ_events, μία φορά ανά περιστροφή. Απαιτεί τράπεζα 6.
; ---------------------------------------------------------------------------
mt_tick:
        ld      a,(EC_METEOR)
        or      a
        jr      nz,mt_impact
        ld      hl,(ev_r1)
        ld      a,h
        inc     a
        ret     nz                      ; τα ψηλά οκτώ δεν είναι όλα ένα
        ld      a,l
        or      #0F
        inc     a
        ret     nz                      ; ούτε τα τέσσερα από κάτω
        ; --- αρχίζει: σπόρος από το r1 και το ρολόι, ποτέ μηδέν ---
        ld      de,(EC_FRAME)
        ld      a,l
        xor     e
        ld      l,a
        ld      a,h
        xor     d
        ld      h,a
        or      l
        jr      nz,mts_seed
        inc     l
mts_seed:
        ld      (EC_MRND),hl
        ; --- το κέντρο: το πρώτο ζωντανό κτίριο από ένα τυχαίο σημείο ---
        call    mt_byte
        and     127
        ld      c,a
        ld      b,128
mts_lp:
        ld      a,c
        call    mt_rec
        jr      c,mts_nx                ; 96-127: δεν είναι κόμβος
        call    mt_state
        jr      nz,mts_got
mts_nx:
        inc     c
        res     7,c
        djnz    mts_lp
        ret                             ; ούτε ένα κτίριο: καμία βροχή
mts_got:
        ld      a,(hl)
        sra     a
        ld      (EC_MCX),a
        inc     hl
        ld      a,(hl)
        sra     a
        ld      (EC_MCY),a
        ld      a,METEOR_N
        ld      (EC_METEOR),a
        ret

; --- μία κρούση --------------------------------------------------------------
mt_impact:
        dec     a
        ld      (EC_METEOR),a
        ld      a,1
        ld      (mt_boom),a             ; ο κύριος βρόχος παίζει τον ήχο
        call    mt_byte
        ld      e,a
        ld      a,h
        ld      (mt_s),a                ; ποια μηχανή, αν πέσει σε θόλο
        ld      a,e
        and     15
        sub     8
        ld      hl,EC_MCX
        add     a,(hl)
        ld      b,a
        ld      a,e
        rrca
        rrca
        rrca
        rrca
        and     15
        sub     8
        ld      hl,EC_MCY
        add     a,(hl)
        ld      c,a                     ; (B, C) = το tile της κρούσης
        ld      a,b
        add     a,64
        and     #80
        ret     nz                      ; έξω από τον κόσμο
        ld      a,c
        add     a,64
        and     #80
        ret     nz
        ; --- ποιο κτίριο, αν κάποιο ---
        ld      hl,G_dome_tbl
        ld      de,MAX_DOME * 256 + DOME_REC
        xor     a
        call    mt_scan
        jr      c,mt_hit
        ld      hl,G_struct_tbl
        ld      de,MAX_STRUCT * 256 + STRUCT_REC
        ld      a,MAX_DOME
        call    mt_scan
        jr      c,mt_hit
        ; fall through: κανένα κτίριο

; --- έδαφος: κρατήρας, αν είναι ελεύθερη γη ----------------------------------
mt_ground:
        push    bc
        ld      bc,GA_PORT + PAGE_B4
        out     (c),c
        pop     bc
        ; η διεύθυνση του tile_addr (src/tiles.asm), εδώ επειδή το harness της
        ; προσομοίωσης (tests/simtest.asm) δεν έχει renderer
        ld      a,c
        add     a,64
        srl     a
        ld      h,a
        ld      a,0
        rra
        ld      l,a
        ld      a,b
        add     a,64
        or      l
        ld      l,a
        ld      a,h
        add     a,#40                   ; WORLD_BASE / 256
        ld      h,a
        ld      d,0                     ; «ο χάρτης δεν άλλαξε»
        ld      a,(hl)
        ld      e,a
        and     W_OCC_MASK
        jr      nz,mtg_no               ; διάδρομος
        ld      a,e
        and     7
        cp      W_MOUNTAIN
        jr      c,mtg_yes               ; έδαφος, σκόνη, βράχος
        cp      W_FOUNDATION
        jr      nz,mtg_no               ; βουνό, νερό, ήδη κρατήρας
mtg_yes:
        ld      a,e
        and     #C0                     ; το decor μένει
        or      W_CRATER
        ld      (hl),a
        inc     d
mtg_no:
        push    bc
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        pop     bc
        dec     d
        ret     nz                      ; δεν άλλαξε τίποτα στον χάρτη
        ld      a,DK_TILE               ; το tile και οι γείτονες (autotile)
        jp      wh_push

; --- χτύπησε κτίριο ----------------------------------------------------------
mt_hit:
        ld      a,(mt_n)
        call    mt_rec
        ld      de,D_STATE              ; = ST_STATE
        add     hl,de
        ld      a,(hl)
        inc     hl                      ; D_INTEG = ST_INTEG
        cp      DS_ACTIVE
        jr      z,mth_live
        ld      (hl),0                  ; εργοτάξιο: χάνει την πρόοδο
        ret
mth_live:
        ld      a,(mt_n)
        cp      MAX_DOME
        jr      nc,mth_struct
        ld      (eb_d),a                ; θόλος: μία μηχανή σταματά
        ld      a,(mt_s)
        ld      (eb_s),a
        jp      ec_break_d
mth_struct:
        ld      (hl),0                  ; ακεραιότητα 0
        dec     hl
        ld      (hl),DS_BUILDING        ; ξανά εργοτάξιο
        ld      a,1
        ld      (ec_fdiv),a             ; το ισοζύγιο ξαναμετρά (όπως το ja_build)
        ld      a,(mt_n)
        jp      jb_post_build           ; και κάποιος έρχεται να το ξαναχτίσει

; ---------------------------------------------------------------------------
; mt_scan — ένας πίνακας κτιρίων. HL = η πρώτη εγγραφή, D = πόσες, E = μέγεθος
; εγγραφής, A = ο κόμβος της πρώτης, (B, C) = το tile. CY αν το tile είναι σε
; κάποιο αποτύπωμα, και τότε (mt_n) = ο κόμβος. Κρατά BC.
;
; ΠΡΩΤΑ ΤΟ ΚΕΝΤΡΟ, ΜΕΤΑ ΤΟ ΑΠΟΤΥΠΩΜΑ. Το πρώτο γράψιμο ρωτούσε το mt_foot για
; κάθε ζωντανό κόμβο: ~165 µs ο ένας, 9,5 ms μια κρούση σε αποικία 54 κτιρίων,
; στη θέση του τροχού με προϋπολογισμό 500 µs. Κανένα αποτύπωμα δεν φτάνει
; πάνω από MT_REACH tiles από το κέντρο του, οπότε ένα κέντρο μακρύτερα στο x
; φεύγει με έξι εντολές, και το mt_foot το πληρώνουν μόνο τα κοντινά.
; ---------------------------------------------------------------------------
MT_REACH    equ 4                       ; θόλος L: 8x8, το μισό. Δομές ως 4x4.

mt_scan:
        add     a,d
        ld      (mt_end),a              ; ο κόμβος μετά την τελευταία εγγραφή
msc_lp:
        ld      a,(hl)                  ; cx, μισά tiles
        sra     a
        sub     b
        add     a,MT_REACH
        cp      2 * MT_REACH + 1
        jr      c,msc_near
msc_nx:
        ld      a,l
        add     a,e
        ld      l,a
        jr      nc,msc_c
        inc     h
msc_c:
        dec     d
        jr      nz,msc_lp
        or      a                       ; NC: κανένα
        ret
msc_near:
        push    de
        push    hl
        ld      a,(mt_end)
        sub     d
        ld      (mt_n),a
        call    mt_state                ; άδεια εγγραφή: Z, NC
        call    nz,mt_foot              ; CY αν η κρούση είναι μέσα του
        pop     hl
        pop     de
        ret     c
        jr      msc_nx

; ---------------------------------------------------------------------------
; mt_rec — A = κόμβος -> HL = η εγγραφή του (θόλος < 64, δομή από κει και
; πάνω). CY αν ο κόμβος δεν υπάρχει (>= 96). Χαλάει DE.
mt_rec:
        cp      MAX_NODE
        ccf
        ret     c
        cp      MAX_DOME
        jp      c,jb_dome_ptr           ; γυρίζει χωρίς CY
        sub     MAX_DOME
        ld      l,a
        ld      h,0
        add     hl,hl
        add     hl,hl
        add     hl,hl                   ; *STRUCT_REC
        ld      de,G_struct_tbl
        add     hl,de
        ret

; mt_state — HL = εγγραφή. NZ αν το κτίριο υπάρχει. Κρατά HL, χαλάει A, DE.
mt_state:
        push    hl
        ld      de,D_STATE
        add     hl,de
        ld      a,(hl)
        pop     hl
        or      a
        ret

; mt_foot — HL = εγγραφή του κόμβου (mt_n), (B, C) = tile. CY αν το tile
; είναι στο αποτύπωμα. Θόλος: πλευρά 4 + 2*μέγεθος. Δομή: το πλαίσιο του
; sprite της (struct_dims, bytes x γραμμές), που γεμίζει ακριβώς τα tiles της.
; Η αρχή είναι (κέντρο - πλευρά) / 2, όπως στο dh_site. Χαλάει A, DE, HL.
mt_foot:
        push    hl
        inc     hl
        inc     hl
        ld      a,(mt_n)
        cp      MAX_DOME
        jr      nc,mtf_st
        ld      a,(hl)                  ; D_SIZE
        add     a,a
        add     a,4
        ld      d,a
        ld      e,a
        jr      mtf_go
mtf_st:
        ld      a,(hl)                  ; ST_KIND
        add     a,a
        add     a,a
        add     a,a
        inc     hl
        add     a,(hl)
        add     a,(hl)                  ; + 2*ST_SIZE
        ld      e,a
        ld      d,0
        ld      hl,G_struct_dims
        add     hl,de
        ld      a,(hl)
        rrca
        rrca
        and     #3F                     ; bytes / 4
        ld      d,a
        inc     hl
        ld      a,(hl)
        rrca
        rrca
        rrca
        rrca
        and     #0F                     ; γραμμές / 16
        ld      e,a
mtf_go:
        pop     hl
        ld      a,(hl)                  ; cx
        sub     d
        sra     a
        neg
        add     a,b
        cp      d
        ret     nc
        inc     hl
        ld      a,(hl)                  ; cy
        sub     e
        sra     a
        neg
        add     a,c
        cp      e
        ret

; mt_byte — οκτώ βήματα της EC_MRND: A = L = ένα καινούργιο byte, H το
; προηγούμενο. Χαλάει B.
mt_byte:
        ld      hl,(EC_MRND)
        ld      b,8
mtb_lp:
        call    lfsr_hl
        djnz    mtb_lp
        ld      (EC_MRND),hl
        ld      a,l
        ret

mt_n:       db 0
mt_end:     db 0
mt_s:       db 0
mt_boom:    db 0                        ; έπεσε μετεωρίτης· ο ήχος από το main
