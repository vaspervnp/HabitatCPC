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
        ; Οχι με λιγότερους από DIS_POP ζωντανούς, ούτε μέσα στην ησυχία μετά
        ; από καταστροφή ή βλάβη (βήμα 121, ev_may στο src/econ.asm). Μετά τη
        ; ζαριά: σε 4.095 περιστροφές από τις 4.096 δεν κοστίζει τίποτα.
        call    ev_may
        ret     c
        ld      hl,(ev_r1)
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
        jp      ev_mark                 ; και η ησυχία των δύο sol (βήμα 121)
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
        sub     8 + MT_REACH
        add     a,l
        ld      b,a                     ; B = x - MT_REACH (mt_scan, βήμα 87)
        ld      a,e
        rrca
        rrca
        rrca
        rrca
        and     15
        sub     8
        add     a,h
        ld      c,a                     ; (B + MT_REACH, C) = το tile της κρούσης
        ; ΕΞΩ ΑΠΟ ΤΟΝ ΚΟΣΜΟ: x + 64 ή y + 64 με το bit 7 (-64..63 -> 0..127)
        add     a,64
        ld      l,a
        ld      a,b
        add     a,64 + MT_REACH
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
        dec     hl
        dec     hl
        dec     hl                      ; ST_KIND
        ld      a,(hl)
        cp      K_SHIP
        ret     z                       ; το σκάφος δεν είναι κτίριο (βήμα 87)
        ld      e,a                     ; το είδος, για το airlock πιο κάτω
        inc     hl
        inc     hl
        ld      (hl),DS_BUILDING        ; ξανά εργοτάξιο
        inc     hl
        ld      (hl),0                  ; ακεραιότητα 0
        ; ΚΑΙ ΧΩΡΙΣ ΣΩΡΟ (βήμα 115): το ST_OWED ενός ορυχείου σε λειτουργία είναι
        ; ο σωρός του (src/haul.asm), ενός εργοταξίου τα φορτία που χρωστά. Αν
        ; έμενε, το σάρωμα του src/repost.asm θα τον διάβαζε για χρέος και θα
        ; ζητούσε υλικά για κάτι πληρωμένο. Ο σωρός σκορπίζει· κάθε άλλη δομή σε
        ; λειτουργία έχει ήδη 0 εκεί.
        inc     hl
        inc     hl
        ld      (hl),0                  ; ST_OWED
        assert  ST_OWED == ST_INTEG + 2
        ld      a,1
        ld      (ec_fdiv),a             ; το ισοζύγιο ξαναμετρά (όπως το ja_build)
        ; Ενα airlock χωρίς αέρα: όσοι στέκονταν μέσα του είναι πια έξω, με
        ; στολή (βήμα 90· το §6.2 το άφηνε για όταν θα έρθουν οι στολές).
        ld      a,e                     ; ST_KIND
        cp      K_AIRLOCK
        ld      a,c
        call    z,lk_air_out            ; src/door.asm· κρατά το C
        ; ΚΑΙ ΦΑΙΝΕΤΑΙ (βήμα 109): ως τότε μια δομή που χτύπησε έμενε ίδια ως να
        ; ξαναχτιστεί (§15). Τώρα έχει το σήμα του εργοταξίου.
        push    bc
        ld      a,c
        call    st_redraw
        pop     bc
        ld      a,c
        jp      sp_build                ; και κάποιος έρχεται να το ξαναχτίσει (src/supply.asm)

; ---------------------------------------------------------------------------
; st_built — A = ο κόμβος που μόλις τελείωσε (ja_build): το DK_BUILT, και για
; δομή και το DK_TILE του κέντρου της, που σβήνει το σήμα του εργοταξίου
; (βήμα 109, st_mark του src/figure.asm). Ως τότε μια δομή δεν ξαναζωγραφιζόταν
; όταν τελείωνε: φαινόταν ίδια χτισμένη ή όχι.
; st_redraw — μόνο το DK_TILE: και για τη δομή που ένας μετεωρίτης έκανε πάλι
; εργοτάξιο, ώστε να φανεί το σήμα. Το dh_tile ξαναζωγραφίζει τα 3x3 tiles
; γύρω από το tile του κέντρου, και το σήμα, 2 bytes x 6 γραμμές στο κέντρο,
; πέφτει πάντα μέσα τους: σε ένα tile ή στα δύο από τα δύο όρια. Τράπεζα 6 μέσα.
; ---------------------------------------------------------------------------
st_built:
        ld      b,a
        push    af
        ld      a,DK_BUILT
        call    wh_push
        pop     af
st_redraw:
        cp      MAX_DOME
        ret     c
        call    mt_rec                  ; HL -> ST_CX
        ld      a,(hl)
        sra     a
        ld      b,a                     ; το tile του κέντρου: x
        inc     hl
        ld      a,(hl)
        sra     a
        ld      c,a                     ; και y
        ld      a,DK_TILE
        jp      wh_push
        assert  ST_CX == 0 && ST_CY == 1

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
        add     a,64 + MT_REACH         ; το B είναι x - MT_REACH
        ld      l,a
        call    mt_crater               ; src/b6out.asm: η 4 δεν διαβάζεται από εδώ
mtg_back:
        ret     nz                      ; δεν άλλαξε τίποτα στον χάρτη
        ld      a,b
        add     a,MT_REACH
        ld      b,a                     ; ξανά το x του tile
        ld      a,DK_TILE               ; το tile και οι γείτονες (autotile)
        jp      wh_push

; ---------------------------------------------------------------------------
; mt_scan — ένας πίνακας κτιρίων. HL = η πρώτη εγγραφή, D = πόσες, E = μέγεθος
; εγγραφής (DOME_REC ή STRUCT_REC: το bit 4 λέει ποιο), (B + MT_REACH, C) = το
; tile. CY αν το tile είναι σε κάποιο αποτύπωμα, και τότε HL = η εγγραφή και
; D = πόσες έμεναν μαζί της. NC: HL = μετά την τελευταία. Κρατά BC.
;
; ΤΟ B ΕΙΝΑΙ x - MT_REACH (βήμα 87): το «κοντά» ήταν cx/2 - x + MT_REACH, ένα
; add σε κάθε εγγραφή — 2 us επί 96 σε κάθε κρούση. Ο καλών το αφαιρεί μία
; φορά (μηδενικό κόστος στο mt_impact, όπου το x βγαίνει από μια αφαίρεση
; ούτως ή άλλως) και πλήρωσε με αυτό τον έλεγχο του σκάφους στο mth_struct.
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
        sub     b                       ; - (x - MT_REACH)
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
        add     a,MT_REACH              ; το B είναι x - MT_REACH
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
; κει και πάνω). Χαλάει A και DE. Το καλεί και το ja_build (src/jobs.asm).
mt_rec:
        cp      MAX_DOME
        jp      c,jb_dome_ptr
        add     a,a
        add     a,a
        add     a,a                     ; *STRUCT_REC: (64 + δομή) x 8 = δομή x 8
        ld      l,a
        ld      h,G_struct_tbl >> 8     ; μία σελίδα (assert)
        ret
        assert  (G_struct_tbl & 255) == 0 && MAX_STRUCT * STRUCT_REC == 256 && MAX_DOME == 64

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

; ev_may — μπορεί να αρχίσει καταστροφή τώρα (βήμα 121); CY = όχι: λιγότεροι
; από DIS_POP ζωντανοί, ή λιγότερο από FAULT_GAP περιστροφές από το τελευταίο
; γεγονός, ή λιγότερο από δύο sol από την τελευταία καταστροφή. Από τη θύελλα,
; την έκλαμψη (src/econ.asm) και το mt_tick, μόνο αφού έπεσε η ζαριά τους.
; ΕΔΩ, ΣΤΟ b6code, ΟΧΙ ΣΤΟ econ.asm: τα EC_LDIS και EC_LEV είναι στην τράπεζα
; 6, που έχει μέσα όλη η θέση 15, και οι τρεις ρουτίνες θα έβαζαν 96 bytes στην
; τράπεζα 0, τη στενότερη (§4.2).
; Χαλάει A, BC, DE, HL.
ev_may:
        ld      a,(EC_ALIVE)
        cp      DIS_POP
        ret     c
        ld      de,EC_LEV
        call    ev_since
        ld      bc,FAULT_GAP * 16
        or      a
        sbc     hl,bc
        ret     c
        ld      de,EC_LDIS
        call    ev_since
        ld      bc,(EC_SOLLEN)
        or      a
        sbc     hl,bc
        ret     c
        sbc     hl,bc                   ; δύο sol: το CY είναι ήδη 0
        ret

; ev_since — DE -> [sol, frame] ενός γεγονότος: HL = frames από τότε. #FFFF από
; τρία sol και πάνω (το sol είναι ένα byte: μετά από 256 sol ξαναμοιάζει
; πρόσφατο, για το πολύ δύο sol), και για το [0, 0] — «ποτέ»: ένα γεγονός στο
; sol 0 έχει frame 16 τουλάχιστον, γιατί η ζαριά βλέπει το ρολόι αφού
; προχωρήσει. Χαλάει A, BC, DE, HL.
ev_since:
        ex      de,hl
        ld      e,(hl)                  ; το sol τότε
        inc     hl
        ld      c,(hl)
        inc     hl
        ld      b,(hl)                  ; BC = το frame τότε
        ld      a,e
        or      c
        or      b
        jr      z,evs_far
        ld      a,(EC_SOL)
        sub     e
        cp      3
        jr      nc,evs_far
        ld      d,a                     ; 0-2 sol πριν
        ld      hl,(EC_FRAME)
        or      a
        sbc     hl,bc
        ld      bc,(EC_SOLLEN)
        inc     d
evs_lp:
        dec     d
        ret     z
        add     hl,bc
        jr      evs_lp
evs_far:
        ld      hl,#FFFF
        ret

; ev_mark — μια καταστροφή άρχισε τώρα: η χρονοσφραγίδα της, και του τελευταίου
; γεγονότος. ev_mark1 — μόνο του τελευταίου γεγονότος (η βλάβη). Χαλάει A, DE, HL.
ev_mark:
        ld      hl,EC_LDIS
        call    evm_put
ev_mark1:
        ld      hl,EC_LEV
evm_put:
        ld      a,(EC_SOL)
        ld      (hl),a
        inc     hl
        ld      de,(EC_FRAME)
        ld      (hl),e
        inc     hl
        ld      (hl),d
        ret
        assert  EC_X + 6 <= G_node_occ + 256   ; στα άδεια των πρακτόρων 100-127
