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
        cp      MAX_NODE
        jr      nc,mts_nx               ; 96-127: δεν είναι κόμβος
        call    mt_rec
        push    hl
        ld      de,D_STATE
        add     hl,de
        ld      a,(hl)
        pop     hl
        or      a
        jr      nz,mts_got
mts_nx:
        inc     c
        res     7,c
        djnz    mts_lp
        ret                             ; ούτε ένα κτίριο: καμία βροχή
mts_got:
        ld      a,(hl)
        sra     a
        ld      e,a
        inc     hl
        ld      a,(hl)
        sra     a
        ld      d,a
        ld      (EC_MCX),de             ; και το EC_MCY από πίσω
        ld      a,METEOR_N
        ld      (EC_METEOR),a
        ret
        assert  EC_MCY == EC_MCX + 1

; --- μία κρούση --------------------------------------------------------------
mt_impact:
        dec     a
        ld      (EC_METEOR),a
        ld      a,1
        ld      (mt_boom),a             ; ο κύριος βρόχος παίζει τον ήχο
        call    mt_byte                 ; (και το EC_MRND + 1: ποια μηχανή)
        ld      e,a
        ld      hl,(EC_MCX)             ; L = το κέντρο x, H = y
        and     15
        sub     8
        add     a,l
        ld      b,a
        ld      a,e
        rrca
        rrca
        rrca
        rrca
        and     15
        sub     8
        add     a,h
        ld      c,a                     ; (B, C) = το tile της κρούσης
        ; ΕΞΩ ΑΠΟ ΤΟΝ ΚΟΣΜΟ: x + 64 ή y + 64 με το bit 7 (-64..63 -> 0..127)
        add     a,64
        ld      l,a
        ld      a,b
        add     a,64
        or      l
        ret     m
        ; --- ποιο κτίριο, αν κάποιο: οι θόλοι, και οι δομές αμέσως μετά ---
        ld      hl,G_dome_tbl
        ld      de,MAX_DOME * 256 + DOME_REC
        call    mt_scan
        ld      a,MAX_DOME
        jr      c,mt_hit
        ld      de,MAX_STRUCT * 256 + STRUCT_REC
        call    mt_scan                 ; το HL είναι ήδη στο G_struct_tbl
        ld      a,MAX_NODE
        jr      nc,mt_ground
        assert  G_struct_tbl == G_dome_tbl + MAX_DOME * DOME_REC

; --- χτύπησε κτίριο: HL = η εγγραφή, A - D = ο κόμβος ------------------------
mt_hit:
        sub     d
        ld      c,a
        ld      de,D_STATE              ; = ST_STATE
        add     hl,de
        ld      a,(hl)
        inc     hl                      ; D_INTEG = ST_INTEG
        cp      DS_ACTIVE
        jr      z,mth_live
        ld      (hl),0                  ; εργοτάξιο: χάνει την πρόοδο
        ret
mth_live:
        ld      a,c
        cp      MAX_DOME
        jr      nc,mth_struct
        ld      (eb_d),a                ; θόλος: μία μηχανή σταματά
        ld      a,(EC_MRND + 1)         ; το byte πριν από αυτό της κρούσης
        ld      (eb_s),a
        jp      ec_break_d
mth_struct:
        ld      (hl),0                  ; ακεραιότητα 0
        dec     hl
        ld      (hl),DS_BUILDING        ; ξανά εργοτάξιο
        ld      a,1
        ld      (ec_fdiv),a             ; το ισοζύγιο ξαναμετρά (όπως το ja_build)
        ld      a,c
        jp      jb_post_build           ; και κάποιος έρχεται να το ξαναχτίσει

; --- έδαφος: κρατήρας, αν είναι ελεύθερη γη ----------------------------------
mt_ground:
        ; η διεύθυνση του tile_addr (src/tiles.asm), εδώ επειδή το harness της
        ; προσομοίωσης (tests/simtest.asm) δεν έχει renderer:
        ; H = #40 + (y + 64) / 2, L = (y & 1) * 128 + x + 64
        ld      a,c
        add     a,64
        or      #80
        rra                             ; #40 | (y + 64) / 2, carry = y & 1
        ld      h,a
        sbc     a,a
        and     #80
        add     a,b
        add     a,64
        ld      l,a
        push    bc
        ld      bc,GA_PORT + PAGE_B4
        out     (c),c
        ld      a,(hl)
        and     W_OCC_MASK | 7          ; κατοχή και έδαφος
        cp      W_MOUNTAIN
        jr      c,mtg_yes               ; ελεύθερο έδαφος, σκόνη, βράχος
        cp      W_FOUNDATION
        jr      nz,mtg_back             ; διάδρομος, βουνό, νερό, ήδη κρατήρας
mtg_yes:
        ld      a,(hl)
        and     #C0                     ; το decor μένει
        or      W_CRATER
        ld      (hl),a
        xor     a                       ; Z: ο χάρτης άλλαξε
mtg_back:
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        pop     bc
        ret     nz                      ; δεν άλλαξε τίποτα στον χάρτη
        ld      a,DK_TILE               ; το tile και οι γείτονες (autotile)
        jp      wh_push

; ---------------------------------------------------------------------------
; mt_scan — ένας πίνακας κτιρίων. HL = η πρώτη εγγραφή, D = πόσες, E = μέγεθος
; εγγραφής (DOME_REC ή STRUCT_REC: το bit 4 λέει ποιο), (B, C) = το tile. CY αν
; το tile είναι σε κάποιο αποτύπωμα, και τότε HL = η εγγραφή και D = πόσες
; έμεναν μαζί της. NC: HL = μετά την τελευταία. Κρατά BC.
;
; ΠΡΩΤΑ ΤΟ ΚΕΝΤΡΟ, ΜΕΤΑ ΤΟ ΑΠΟΤΥΠΩΜΑ. Το πρώτο γράψιμο ρωτούσε το αποτύπωμα
; κάθε ζωντανού κόμβου: ~165 µs ο ένας, 9,5 ms μια κρούση σε αποικία 54
; κτιρίων, στη θέση του τροχού με προϋπολογισμό 500 µs. Κανένα αποτύπωμα δεν
; φτάνει πάνω από MT_REACH tiles από το κέντρο του, οπότε ένα κέντρο μακρύτερα
; στο x φεύγει με έξι εντολές, και το αποτύπωμα το πληρώνουν μόνο τα κοντινά.
; ---------------------------------------------------------------------------
MT_REACH    equ 4                       ; θόλος L: 8x8, το μισό. Δομές ως 4x4.

mt_scan:
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

; Το αποτύπωμα: θόλος, πλευρά 4 + 2*μέγεθος· δομή, το πλαίσιο του sprite της
; (struct_dims, bytes x γραμμές), που γεμίζει ακριβώς τα tiles της. Η αρχή
; είναι (κέντρο - πλευρά) / 2, όπως στο dh_site. Άδεια εγγραφή: κανένα.
msc_near:
        push    de
        push    hl
        inc     hl
        inc     hl
        ld      a,(hl)                  ; D_SIZE / ST_KIND
        inc     hl
        ld      d,(hl)                  ; ST_SIZE
        inc     hl
        inc     (hl)
        dec     (hl)                    ; D_STATE = ST_STATE: Z = άδεια
        jr      z,msn_no
        bit     4,e
        jr      z,msn_st
        add     a,a
        add     a,4
        ld      d,a
        ld      e,a
        jr      msn_go
msn_st:
        add     a,a
        add     a,a
        add     a,d
        add     a,a                     ; είδος * 8 + 2 * μέγεθος
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
msn_go:
        pop     hl
        push    hl
        ld      a,(hl)                  ; cx
        sub     d
        sra     a
        neg
        add     a,b
        cp      d
        jr      nc,msn_no
        inc     hl
        ld      a,(hl)                  ; cy
        sub     e
        sra     a
        neg
        add     a,c
        cp      e
        jr      nc,msn_no
        pop     hl
        pop     de
        ret                             ; CY
msn_no:
        pop     hl
        pop     de
        jr      msc_nx
        assert  DOME_REC & 16 && !(STRUCT_REC & 16)

; ---------------------------------------------------------------------------
; mt_rec — A = κόμβος (< MAX_NODE) -> HL = η εγγραφή του (θόλος < 64, δομή από
; κει και πάνω). Χαλάει DE. Το καλεί και το ja_build (src/jobs.asm).
mt_rec:
        cp      MAX_DOME
        jp      c,jb_dome_ptr
        ld      l,a
        ld      h,0
        add     hl,hl
        add     hl,hl
        add     hl,hl                   ; *STRUCT_REC
        ld      de,G_struct_tbl - MAX_DOME * STRUCT_REC
        add     hl,de
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

mt_boom:    db 0                        ; έπεσε μετεωρίτης· ο ήχος από το main
