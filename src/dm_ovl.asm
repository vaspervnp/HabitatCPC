; dm_ovl.asm — ο κώδικας της κατεδάφισης που τρέχει από το GH_BUF (βήμα 101).
; Τον φέρνει εκεί το ov_run (src/demolish.asm), από τις τρύπες του DIST, και
; πηδά στο dm_do.

; ---------------------------------------------------------------------------
; Η ΣΕΙΡΑ 0: δύο χειριστές της λίστας αλλαγών (src/dirty.asm) που ΤΡΕΧΟΥΝ ΑΠΟ
; ΤΗΝ ΤΡΥΠΑ ΤΗΣ ΓΡΑΜΜΗΣ 0, στην τράπεζα 1 — εκεί που είναι το παράθυρο όταν
; τρέχει η λίστα, και όπου ξαναγυρίζει κάθε χειριστής. Γράφονται για το GH_BUF
; αλλά τρέχουν στο #4060: ΧΩΡΙΣ αναφορές στον εαυτό τους, μόνο κλήσεις
; έξω. Κάθε ορθογώνιο της κατεδάφισης είναι ένα DK_RSIZE και ένα DK_RECT
; (dm_do), ένα ανά πέρασμα της λίστας: όλα μαζί στο FIRE έκαναν το καρέ ως
; 270 ms.
; ---------------------------------------------------------------------------
dho_rsize:
        ld      hl,(dt_a)
        ld      (vr_w),hl               ; vr_w, vr_h
        ret
dho_rect:
        ld      hl,(dt_a)
        ld      (vr_tx),hl              ; vr_tx, vr_ty
        call    vr_clip                 ; src/view.asm
        ret     z                       ; έξω από το κάδρο
        call    dt_ghost_rect           ; το φάντασμα σηκώνεται, αν είναι εκεί
        call    vr_paint                ; το έδαφος
        jp      vr_objs                 ; ό,τι το πατά, και το clip πίσω
dh_row0_end:
        assert  dh_row0_end - GH_BUF <= 32 && dho_rsize == GH_BUF
        defs    32 - (dh_row0_end - GH_BUF)
DH_RSIZE    equ OV_HOLE + dho_rsize - GH_BUF
DH_RECT     equ OV_HOLE + dho_rect - GH_BUF

; ---------------------------------------------------------------------------
; dm_do — γκρεμίζει τον (dm_n). Γυρίζει με την τράπεζα 1.
; ---------------------------------------------------------------------------
dm_do:
        ld      hl,dmv_r
        ld      (dmv_p),hl
        ld      a,(dm_n)
        call    al_node                 ; το αποτύπωμά του (src/link.asm)
        ld      hl,al_rx                ; al_rx, al_ry, al_rw, al_rh
        call    dmv_put                 ; το πρώτο ορθογώνιο (dm_world)
        call    asc_b6                  ; το al_node γυρίζει με την 1
        ; --- ΤΟ ΚΤΙΡΙΟ: η τιμή του στον κατάλογο (bld_items) ---
        ld      a,(dm_n)
        call    mt_rec
        inc     hl
        inc     hl                      ; D_SIZE / ST_KIND
        push    hl
        ld      a,(dm_n)
        cp      MAX_DOME
        ld      a,(hl)
        jr      c,dmd_it
        add     a,4                     ; δομή: το είδος + 4 στον κατάλογο
dmd_it:
        add     a,a
        add     a,a
        add     a,a
        add     a,4                     ; μέταλλο, και βιοπλαστικό αμέσως μετά
        ld      hl,bld_items
        call    ob_addu
        ld      e,(hl)
        inc     hl
        ld      d,(hl)
        ld      l,e                     ; τα σύνολα αρχίζουν από αυτήν
        ld      h,0
        ld      (dm_m),hl
        ld      l,d
        ld      (dm_b),hl
        pop     hl                      ; -> D_SIZE
        inc     hl
        inc     hl
        ld      a,(hl)                  ; D_STATE = ST_STATE
        ld      (dm_st),a
        dec     hl
        dec     hl
        ; --- ΟΙ ΜΗΧΑΝΕΣ ΕΝΟΣ ΘΟΛΟΥ, με την τιμή του FIT (fit_price) ---
        ld      a,(dm_n)
        cp      MAX_DOME
        jr      nc,dmd_corr
        ld      a,(hl)                  ; D_SIZE
        inc     hl
        ld      c,(hl)                  ; D_ROOM
        ld      de,D_MACH - D_ROOM
        add     hl,de
        push    hl
        ld      hl,G_machine_count
        call    ob_addu
        ld      b,(hl)                  ; 1, 4 ή 8
        ld      a,c
        ld      (fit_rm),a              ; το θερμοκήπιο: τα φυτά
        pop     hl
dmm_lp:
        push    bc
        push    hl
        ld      a,(hl)
        call    fit_price               ; χαλάει C, DE, HL
        ld      de,(bd_metal)           ; E = μέταλλο, D = βιοπλαστικό
        call    dm_add8
        pop     hl
        pop     bc
        inc     hl
        djnz    dmm_lp
dmd_corr:
        ; --- ΟΙ ΔΙΑΔΡΟΜΟΙ ΤΟΥ: στο σύνολο, και φεύγουν. Μια στροφή είναι δύο
        ; εγγραφές, και η δεύτερη (C_A = 255) φεύγει με την πρώτη: αλλιώς ένας
        ; ευθύς διάδρομος που θα έπαιρνε την πρώτη θα την έβρισκε για στροφή
        ; του (oc_cont, src/object.asm). Ενα airlock στην άλλη άκρη μένει
        ; χωρίς διάδρομο, όπως ένα που μπήκε μόνο του (alc_none, src/link.asm).
        ld      hl,G_corr_tbl
        ld      b,MAX_CORR
dmk_lp:
        push    bc
        push    hl
        ld      a,(dm_n)
        ld      e,(hl)                  ; C_A
        inc     hl
        ld      d,(hl)                  ; C_B
        cp      e
        jr      z,dmk_me
        cp      d
        jr      nz,dmk_nx
        ld      d,e                     ; D = η άλλη άκρη
dmk_me:
        inc     hl
        inc     hl                      ; C_LEN
        ld      a,(hl)
        inc     hl                      ; C_CSTATE
        inc     (hl)
        dec     (hl)
        jr      z,dmk_nx                ; ελεύθερη: τα άκρα της είναι παλιά
        ld      (hl),0
        call    dm_tiles
        inc     hl                      ; ο C_A της επόμενης
        ld      a,(hl)
        inc     a
        jr      nz,dmk_air
        inc     hl
        inc     hl
        inc     hl                      ; C_LEN
        ld      a,(hl)
        inc     hl
        ld      (hl),0                  ; C_CSTATE
        call    dm_tiles
dmk_air:
        push    de
        ld      a,d
        call    dm_crect                ; το ορθογώνιό του (dm_world)
        pop     de
        ld      a,d
        sub     MAX_DOME
        jr      c,dmk_nx                ; θόλος
        add     a,a
        add     a,a
        add     a,a
        add     a,ST_JOINED
        ld      l,a
        ld      h,G_struct_tbl >> 8
        ld      (hl),0
        ld      hl,EC_FREELK
        inc     (hl)
dmk_nx:
        pop     hl
        ld      de,CORR_REC
        add     hl,de
        pop     bc
        djnz    dmk_lp
        ; --- ΤΑ ΥΛΙΚΑ ΠΙΣΩ: τα μισά, ή όλα από εργοτάξιο ---
        ld      hl,(dm_m)
        ld      de,(dm_b)
        ld      a,(dm_st)
        cp      DS_ACTIVE
        jr      nz,dmr_all
        srl     h
        rr      l
        srl     d
        rr      e
dmr_all:
        push    de
        ex      de,hl
        ld      a,S_METAL
        call    ec_add_stock            ; με ταβάνι (src/stock.asm)
        pop     de
        ld      a,S_BIOPL
        call    ec_add_stock
        ; --- ΟΙ ΕΡΓΑΣΙΕΣ ΤΟΥ. Οσες είναι του κόμβου (J_SITE) σβήνουν· όσες
        ; έρχονται από αυτόν ή πάνε σε αυτόν από αλλού (μια Supply από την
        ; αποθήκη του, μια Haul προς αυτήν) γυρίζουν στο J_SITE τους. Οποιος
        ; τις δούλευε τις αφήνει. Η J_TRADE δεν έχει κόμβο στο J_SITE: εκεί
        ; κρατά το φορτίο, και πλοίο δεν υπάρχει (dm_can).
        ld      hl,G_job_tbl
        ld      bc,MAX_JOB * 256        ; C = η εργασία
dmj_lp:
        push    hl
        ld      a,(hl)                  ; J_KIND
        cp      J_TRADE
        jr      z,dmj_nx
        inc     a
        jr      z,dmj_nx                ; NO_JOB
        call    dm_haul                 ; το φορτίο μιας Haul (src/demolish.asm)
        inc     hl
        inc     hl                      ; J_AGENT
        ld      e,(hl)
        inc     hl
        inc     hl                      ; J_SITE
        ld      a,(dm_n)
        cp      (hl)
        jr      z,dmj_del
        ld      d,(hl)
        dec     hl
        dec     hl
        dec     hl                      ; J_NODE
        cp      (hl)
        jr      nz,dmj_nx
        ld      (hl),d
        jr      dmj_free
dmj_del:
        pop     hl
        push    hl
        ld      a,(hl)
        ld      (hl),NO_JOB
        or      a                       ; J_BUILD
        jr      nz,dmj_free
        ld      hl,EC_NBUILD
        dec     (hl)
dmj_free:
        ld      a,e
        inc     a
        jr      z,dmj_nx                ; αδιάθετη
        set     7,e
        ld      d,AG_PG + 3             ; το task, στο πάνω μισό
        ld      a,(de)
        cp      c
        jr      nz,dmj_nx
        ld      a,NO_TASK
        ld      (de),a
dmj_nx:
        pop     hl
        ld      de,JOB_REC
        add     hl,de
        inc     c
        djnz    dmj_lp
        ; --- ΟΣΟΙ ΣΤΕΚΟΝΤΑΙ ΕΚΕΙ, στο κοντινότερο airlock ή στο σκάφος
        ; (lk_anchor, από τον κέρσορα), με γεμάτη στολή. Μέσα, αν το airlock
        ; είναι έτοιμο: αλλιώς ένας που θα ζητούσε αέρα θα έβρισκε για
        ; κοντινότερο airlock αυτό όπου ήδη στέκεται, και δεν θα έφτανε ποτέ.
        ld      a,(dm_n)
        ld      (lk_n),a
        ld      b,a
        call    lk_anchor               ; src/link.asm
        inc     a
        jr      nz,dmp_t
        ld      a,MAX_DOME + 1          ; καμία ελεύθερη ακμή: η δομή 0
dmp_t:
        dec     a
        ld      (lk_t),a
        call    en_in                   ; CY: έχει αέρα
        sbc     a,a
        and     F_INDOORS
        ld      (dm_in),a
        ld      hl,dm_out
        call    lk_each                 ; src/door.asm
        call    dm_paths                ; τα μονοπάτια του (βήμα 102)
        ; --- Ο ΓΡΑΦΟΣ: οι ακμές του φεύγουν (lk_cut, που καλεί και το
        ; rt_mark). Η θέση που μένει πίσω στη λίστα κάθε γείτονα κρατά ακόμη
        ; τον κόμβο αν ήταν ο τελευταίος της: όποιος ταξίδευε προς αυτόν θα
        ; έφτανε σε κόμβο χωρίς ακμές, και θα έμενε εκεί. Γίνεται ο ίδιος ο
        ; γείτονας: γυρίζει πίσω, κι από εκεί ξαναδρομολογείται.
        ld      a,(dm_n)
        ld      l,a
        ld      h,NODEPG
        ld      b,(hl)                  ; ο βαθμός του, πριν σβηστεί
        push    bc
        call    lk_cut
        pop     bc
        inc     b
        dec     b
        jr      z,dmg_end
        ld      a,(dm_n)
        call    lk_adj                  ; οι γείτονές του: η γραμμή μένει
dmg_lp:
        ld      e,(hl)
        ld      d,NODEPG
        push    hl
        ld      a,e
        call    lk_adj                  ; κρατά DE
        ld      a,(de)                  ; ο βαθμός του γείτονα, τώρα
        bit     3,a
        jr      nz,dmg_nx               ; οκτώ: δεν τον είχε (μισή ακμή)
        add     a,l
        ld      l,a                     ; η γραμμή είναι στοιχισμένη στα 8
        ld      a,(dm_n)
        cp      (hl)
        jr      nz,dmg_nx
        ld      (hl),e
dmg_nx:
        pop     hl
        inc     hl
        djnz    dmg_lp
dmg_end:
        ; --- Η ΕΓΓΡΑΦΗ: άδεια. Τα υπόλοιπα bytes μένουν — ένας που φεύγει
        ; ακόμη από εκεί ζωγραφίζεται από το κέντρο της (fw_xy). Ενα airlock
        ; χωρίς διάδρομο μετρούσε στα ελεύθερα (EC_FREELK).
        ld      a,(dm_n)
        ld      l,a
        ld      h,OCCPG
        ld      (hl),0                  ; καμία θέση πιασμένη
        call    mt_rec
        ld      de,D_STATE
        add     hl,de
        ld      (hl),DS_EMPTY
        ld      a,(dm_n)
        cp      MAX_DOME
        jr      c,dmw_go
        dec     hl
        dec     hl                      ; ST_KIND
        ld      a,(hl)
        cp      K_AIRLOCK
        jr      nz,dmw_go
        ld      de,ST_JOINED - ST_KIND
        add     hl,de
        ld      a,(hl)
        or      a
        jr      nz,dmw_go
        ld      hl,EC_FREELK
        dec     (hl)
dmw_go:
        call    dm_world
        ; --- ό,τι μετριέται από τα κτίρια ---
        call    asc_b6
        call    rooms_rebuild           ; τα δωμάτια, η πίστα, το ταβάνι
        ld      a,1
        ld      (ec_fdiv),a             ; η ροή ξαναμετρά ρεύμα και ορυχεία
        ; --- Η ΕΙΚΟΝΑ: τα ίδια ορθογώνια (dmv_r), στη λίστα αλλαγών (DK_RSIZE
        ; και DK_RECT, ένα ανά πέρασμα): έδαφος, και ό,τι μένει από πάνω τους,
        ; κομμένα στο κάδρο, με τα ευρετήρια ξαναχτισμένα. ΟΧΙ πλήρης σχεδίαση:
        ; είναι 360-920 ms ανάλογα με ό,τι φαίνεται (§6.9, βήμα 34). Οσα έμειναν
        ; στη λίστα για τον θόλο που έφυγε τα προσπερνά το dt_prep
        ; (ob_dome_live). Μια λίστα που ξεχειλίζει κάνει πλήρη σχεδίαση.
        call    ob_touch
        ld      hl,dmv_r
dmv_lp:
        push    hl
        inc     hl
        inc     hl
        ld      b,(hl)                  ; πλάτος
        inc     hl
        ld      c,(hl)                  ; ύψος
        ld      a,DK_RSIZE
        call    dirty_push              ; κρατά B, C, E
        pop     hl
        ld      b,(hl)                  ; x0
        inc     hl
        ld      c,(hl)                  ; y0
        inc     hl
        inc     hl
        inc     hl
        push    hl
        ld      a,DK_RECT
        call    dirty_push
        pop     hl
        ld      a,(dmv_p)
        cp      l
        jr      nz,dmv_lp
        call    dm_relink               ; όποιος έχασε τη σύνδεσή του (βήμα 102)
        call    dm_sites                ; ένα εργοτάξιο θόλου χωρίς ακμή (src/demolish.asm)
        jp      dt_end

; ---------------------------------------------------------------------------
; dm_paths — ΤΑ ΜΟΝΟΠΑΤΙΑ ΤΟΥ (βήμα 102): το δικό του, και όσα τελείωναν σε
; αυτόν. Το Γ καθενός είναι κρατημένο στο LK_OWN της δομής του (lk_keep,
; src/link.asm), και ξαναπερπατιέται όπως στην τοποθέτηση (al_walk): τα tiles
; του χάνουν το bit 5 και μένουν θεμέλιο, όπως το αποτύπωμα που γκρεμίστηκε.
; Δεν φαίνεται τίποτα να αλλάζει (το bit 5 δεν ζωγραφίζεται), άρα τίποτα δεν
; ξαναζωγραφίζεται, και κανένα άλλο μονοπάτι δεν χρειάζεται να ξαναγραφτεί:
; ένα μονοπάτι πατά μόνο tiles που χτίζονται (bd_ok), άρα ποτέ άλλο μονοπάτι.
; Οποια δομή η σύνδεσή της — μονοπάτι ή εδάφους — τελείωνε εδώ γίνεται
; LKO_LOST, για το dm_relink. Πριν από τον γράφο και την εγγραφή: θέλει τις
; εγγραφές ζωντανές (al_node). Γυρίζει με την 6.
; ---------------------------------------------------------------------------
dm_paths:
        ld      a,255
        ld      (dm_par),a              ; η άκρη της δικής του σύνδεσης: καμία
        ld      c,MAX_DOME
dmp_lp:
        ld      h,NODEPG
        ld      l,c
        set     5,l                     ; LK_OWN + δομή
        ld      a,(hl)
        or      a
        jr      z,dmp_nx                ; τίποτα κρατημένο
        ld      e,a
        and     #FF - #80 - LKO_GROUND
        ld      b,a                     ; B = η άκρη
        ld      a,(dm_n)
        cp      c
        jr      z,dmp_own               ; η δική του: φεύγει μαζί του
        cp      b
        jr      nz,dmp_nx               ; πάει αλλού
        ld      a,LKO_LOST
        jr      dmp_put
dmp_own:
        ld      a,b
        ld      (dm_par),a              ; για όσους κρέμονταν από αυτόν (dm_relink)
        xor     a
dmp_put:
        ld      (hl),a
        bit     5,e                     ; LKO_GROUND: στο έδαφος δεν έχει bit
        jr      nz,dmp_nx
        push    bc
        ld      a,e
        and     #80
        ld      (al_ori),a              ; το σχήμα: το al_k ρωτά μόνο «μηδέν;»
        ld      a,c
        call    dmp_set                 ; η δομή: το «νέο» του al_walk
        pop     bc
        push    bc
        ld      a,b
        call    al_node                 ; η άκρη: al_rx.. και al_q
        ld      hl,dmp_cb
        ld      (al_cb),hl
        call    al_w4                   ; src/link.asm
        pop     bc
dmp_nx:
        inc     c
        ld      a,c
        cp      MAX_NODE
        jr      c,dmp_lp
        jp      asc_b6                  ; η εγγραφή θέλει την 6
; dmp_cb — ένα tile του μονοπατιού, με την 4: όχι πια μονοπάτι. NC.
dmp_cb:
        call    tile_addr               ; κρατά BC, DE
        res     5,(hl)                  ; W_OCC_PATH
        or      a
        ret
; dmp_set — A = κόμβος: το αποτύπωμά του στο al_nx.. και το κέντρο του στο
; al_p, όπως τα αφήνει το al_find για ό,τι τοποθετείται. Γυρίζει με την 1.
dmp_set:
        call    al_node
        ld      hl,al_rx
        ld      de,al_nx
        ld      bc,4
        ldir
        ld      hl,(al_q)
        ld      (al_p),hl
        ret

; ---------------------------------------------------------------------------
; dm_relink — ΟΠΟΙΑ ΔΟΜΗ ΚΡΕΜΟΤΑΝ ΑΠΟ ΑΥΤΟΝ (βήμα 102) — η σύνδεσή της, μονοπάτι
; ή εδάφους, τελείωνε εκεί, LKO_LOST από το dm_paths — κρέμεται πια από εκεί που
; κρεμόταν εκείνος (dm_par), με σύνδεση εδάφους ζωγραφισμένη όπως όλες (lk_keep,
; lk_draw). Αλλιώς έμενε απρόσιτη: ένα εργοτάξιο που δεν τελειώνει ποτέ, ένα
; ορυχείο που δεν φτάνει κανείς, ένα airlock που ήταν ο δρόμος της αποικίας ως
; το σκάφος.
;
; ΟΧΙ ΤΟ ΚΟΝΤΙΝΟΤΕΡΟ AIRLOCK, όπως ό,τι μπαίνει χωρίς μονοπάτι (lk_ground). Το
; κοντινότερο είναι συχνά ένα που κρέμεται από το ίδιο το ορφανό — δύο airlock
; σε σειρά από το γκρεμισμένο — και τότε οι δύο δένονται μεταξύ τους, με δύο
; ακμές, νησί χωρίς δρόμο ως το σκάφος. Το να αποκλειστεί ό,τι κρέμεται από
; ορφανό θέλει να περπατηθεί όλο το δέντρο, και δεν χωρούσε εδώ. Ο γονιός του
; γκρεμισμένου είναι πιο πάνω στο ίδιο δέντρο: κανένας κύκλος, καμία διπλή
; ακμή, και ο ίδιος δρόμος ως το σκάφος που είχαν πριν. Αν ο γκρεμισμένος δεν
; κρεμόταν από πουθενά (η αποικία δοκιμών, ένα σώσιμο πριν από το βήμα 102), ή
; αν ο γονιός του έχει ήδη MAX_DEGREE ακμές, μένουν χωρίς σύνδεση, όπως ως τώρα.
;
; Μετά τον γράφο και την εγγραφή, και μετά το dm_world, ώστε το lk_draw να
; βλέπει την κατοχή όπως έμεινε. Τα σκέλη που άλλαξαν δεν ζωγραφίζονται εδώ: το
; alv_jp του al_vr (src/commit.asm, τράπεζα 1) δείχνει για λίγο στο dmv_leg, και
; πάνε στη λίστα αλλαγών μετά από τα ορθογώνια του dm_do, ένα ανά πέρασμα.
; ---------------------------------------------------------------------------
dm_relink:
        call    asc_b1                  ; το alv_jp είναι στην τράπεζα 1
        ld      hl,dmv_leg
        ld      (alv_jp + 1),hl
        ld      c,MAX_DOME
dml_lp:
        ld      h,NODEPG
        ld      l,c
        set     5,l                     ; LK_OWN + δομή
        ld      a,(hl)
        inc     a                       ; LKO_LOST
        jr      nz,dml_nx
        ld      (hl),a                  ; 0, ώσπου να γράψει το lk_keep
        ld      a,(dm_par)
        call    dm_up                   ; ο γονιός, ή πρόγονος, ή το σκάφος
        jr      nc,dml_nx               ; κανένας
        ld      (al_pt),a               ; η άκρη, για το lk_draw
        push    bc
        ld      b,c
        ld      c,a
        or      LKO_GROUND
        call    lk_keep                 ; κρατιέται, και η ακμή (src/link.asm)
        pop     bc
        push    bc
        ld      a,c
        call    dmp_set                 ; το «νέο» του lk_draw
        call    lk_draw                 ; src/commit.asm· γυρίζει με την 1
        pop     bc
dml_nx:
        inc     c
        ld      a,c
        cp      MAX_NODE
        jr      c,dml_lp
        ld      hl,view_rect            ; με την 1, από την αρχή ή από το lk_draw
        ld      (alv_jp + 1),hl
        ret
; dmv_leg — στη θέση του view_rect, από το al_vr: το ορθογώνιο ενός σκέλους
; (vr_tx, vr_ty, vr_w, vr_h) στη λίστα αλλαγών, ένα DK_RSIZE και ένα DK_RECT
; όπως τα ορθογώνια του dm_do — μετά από αυτά.
dmv_leg:
        ld      hl,(vr_w)               ; L = vr_w, H = vr_h
        ld      b,l
        ld      c,h
        ld      a,DK_RSIZE
        call    dirty_push
        ld      hl,(vr_tx)              ; L = vr_tx, H = vr_ty
        ld      b,l
        ld      c,h
        ld      a,DK_RECT
        jp      dirty_push

; ---------------------------------------------------------------------------
; dm_world — η κατοχή του κόσμου (bit 4) ξαναγράφεται στα ορθογώνια της λίστας
; (dmv_r): σβήνει, και ξαναγράφεται από τα αποτυπώματα όσων μένουν και από όσους
; διαδρόμους περνούν από εκεί, με τη σφραγίδα της τοποθέτησης (cr_stampx). Τα
; μονοπάτια (bit 5) δεν τα αγγίζει: όσα φεύγουν τα σβήνει το dm_paths (βήμα 102).
; ΓΙΑΤΙ ΞΑΝΑΓΡΑΦΕΤΑΙ ΚΑΙ ΔΕΝ ΣΒΗΝΕΤΑΙ ΜΟΝΟ ΟΤΙ ΕΦΥΓΕ. Ενας διάδρομος σφραγίζει
; και τα tiles του μισού πλάτους όσα ήταν ελεύθερα, και το ποια ήταν δεν το
; κρατά κανείς· ένα tile του μπορεί να είναι και ενός άλλου διαδρόμου ή
; αποτυπώματος. Ξαναγραμμένο, το bit είναι ό,τι θα έγραφαν οι τοποθετήσεις όσων
; μένουν.
; ΤΑ ΟΡΘΟΓΩΝΙΑ: το αποτύπωμα του κόμβου, και κάθε διάδρομός του από κέντρο σε
; κέντρο με ένα tile γύρω (dm_crect). Ο,τι πήρε το bit από αυτόν είναι εκεί
; μέσα. Ενα κουτί με όλα αυτά και 5 tiles γύρω έπιανε τα δύο τρίτα του κάδρου·
; ολόκληρος ο κόσμος ήταν 170 ms μόνο το σβήσιμο.
; ---------------------------------------------------------------------------
dm_world:
        ld      hl,dmv_r
dmw_cr:
        ld      b,(hl)                  ; x0
        inc     hl
        ld      c,(hl)                  ; y0
        inc     hl
        ld      a,(hl)
        ld      (bd_w),a
        inc     hl
        ld      e,(hl)                  ; σειρές
        inc     hl
        push    hl
        call    tile_addr               ; κρατά BC, DE
        ld      c,e
        ld      de,#EF00                ; AND #EF: το bit 4 σβήνει
        call    dmw_fill
        pop     hl
        ld      a,(dmv_p)
        cp      l
        jr      nz,dmw_cr
        ld      c,0
dmw_fp:
        push    bc
        ld      a,c
        call    al_node                 ; CY: άδεια· γυρίζει με την 1
        jr      c,dmw_fn
        ld      hl,(al_rx)              ; L = x, H = y
        ld      b,l
        ld      c,h
        call    tile_addr
        ld      a,(al_rw)
        ld      (bd_w),a
        ld      a,(al_rh)
        ld      c,a
        ld      de,#FF00 + W_OCC_STRUCT
        call    dmw_fill
dmw_fn:
        pop     bc
        inc     c
        ld      a,c
        cp      MAX_NODE
        jr      c,dmw_fp
        ld      hl,G_corr_tbl
        ld      b,MAX_CORR
dmw_cl:
        push    bc
        push    hl
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        ; ΠΡΩΤΑ Η ΚΑΤΑΣΤΑΣΗ: οι άδειες εγγραφές είναι οι περισσότερες, και τα
        ; δύο mt_rec πριν από αυτήν ήταν 17 ms στην αποικία δοκιμών.
        ld      bc,C_CSTATE
        add     hl,bc
        ld      a,(hl)
        pop     hl
        push    hl
        or      a
        jr      z,dmw_cn                ; ελεύθερη
        ld      a,(hl)                  ; C_A
        ld      (cr_a),a
        inc     a
        jr      z,dmw_cn                ; η δεύτερη εγγραφή μιας στροφής
        inc     hl
        ld      a,(hl)                  ; C_B
        ld      (cr_b),a
        ld      c,a
        ld      a,(cr_a)
        call    dmr_pair                ; το ορθογώνιό του, στο dmv_t
        call    dmw_meets
        jr      nc,dmw_cn               ; δεν περνά από κανένα
        call    cr_plan                 ; src/route.asm: η ίδια διαδρομή
        call    cr_stampx               ; src/ui.asm
dmw_cn:
        pop     hl
        ld      de,CORR_REC
        add     hl,de
        pop     bc
        djnz    dmw_cl
        ret

; dmw_fill — HL = το πρώτο tile, C = σειρές, (bd_w) = tiles ανά σειρά: κάθε
; byte AND D, OR E, με την τράπεζα 4 μέσα. Ο ίδιος βρόχος με το bd_link
; (src/build.asm), αντίγραφο: κοινός, η τοποθέτηση μιας δομής θα πλήρωνε ένα
; call και ένα ret, 6 µs πάνω από το ταβάνι του test_place.
dmw_fill:
        push    bc
        ld      bc,GA_PORT + PAGE_B4
        out     (c),c
        pop     bc
dmf_rl:
        push    hl
        ld      a,(bd_w)
        ld      b,a
dmf_cl:
        ld      a,(hl)
        and     d
        or      e
        ld      (hl),a
        inc     l                       ; μια σειρά δεν περνά σελίδα (tile_addr)
        djnz    dmf_cl
        pop     hl
        ld      a,l                     ; η επόμενη σειρά: +128
        add     a,128
        ld      l,a
        jr      nc,dmf_nx
        inc     h
dmf_nx:
        dec     c
        jr      nz,dmf_rl
        ret

; dmw_meets — CY αν το dmv_t τέμνει κάποιο ορθογώνιο της λίστας.
dmw_meets:
        ld      hl,dmv_r
dmt_lp:
        push    hl
        ld      de,dmv_t
        call    dmm_axis                ; x
        call    c,dmm_axis              ; και y
        pop     hl
        ret     c
        inc     hl
        inc     hl
        inc     hl
        inc     hl
        ld      a,(dmv_p)
        cp      l
        jr      nz,dmt_lp
        ret                             ; NC: το cp βρήκε ίσα

; dmm_axis — HL, DE -> η αρχή δύο ορθογωνίων σε έναν άξονα (το μήκος δύο bytes
; μετά): CY αν τα [αρχή, αρχή + μήκος) τέμνονται. HL + 1, DE + 1. Οι αρχές
; είναι -65..63 και τα τέλη ως 65: με +128 συγκρίνονται χωρίς πρόσημο.
dmm_axis:
        ld      a,(de)
        add     a,128
        ld      c,a                     ; C = η αρχή του dmv_t
        inc     de
        inc     de
        ld      a,(de)
        dec     de
        add     a,c
        ld      b,a                     ; B = το τέλος του
        ld      a,(hl)
        add     a,128
        inc     hl
        cp      b
        ret     nc                      ; αρχίζει μετά το τέλος του dmv_t
        inc     hl
        add     a,(hl)
        dec     hl
        ld      b,a                     ; B = το τέλος του
        ld      a,c
        cp      b                       ; CY: το dmv_t αρχίζει πριν από αυτό
        ret

; dm_out — A = πράκτορας στον (dm_n), από το lk_each: όχι πια χειριστής,
; καμία εργασία, γεμάτη στολή, στο (lk_t) — μέσα αν εκεί έχει αέρα.
dm_out:
        ld      l,a
        ld      h,AG_PG
        res     5,(hl)                  ; F_WORKING: αλλιώς η επόμενη αναχώρησή
        ld      h,AG_PG + 3             ; του θα μείωνε τους χειριστές άλλου
        set     7,l
        ld      (hl),NO_TASK
        ld      h,AG_PG + 7
        res     7,l
        ld      (hl),SUIT_TRIP
        ld      a,l
        call    lko_one                 ; src/door.asm: έξω, στο (lk_t)
        ld      hl,(em_id)
        ld      h,AG_PG
        ld      a,(dm_in)
        or      (hl)
        ld      (hl),a
        ret

; dm_tiles — A = πλακίδια διαδρόμου: CORR_M μέταλλο και CORR_B βιοπλαστικό το
; καθένα, στο σύνολο. Κρατά DE, HL.
dm_tiles:
        push    hl
        push    de
        ld      c,CORR_B
        call    ob_mul                  ; HL = A x C, το A μένει
        push    hl
        ld      c,CORR_M
        call    ob_mul
        pop     de
        call    dm_add
        pop     de
        pop     hl
        ret

; dm_add8 — E = μέταλλο, D = βιοπλαστικό. dm_add — HL = μέταλλο, DE =
; βιοπλαστικό: στο σύνολο.
dm_add8:
        ld      l,e
        ld      e,d
        xor     a
        ld      h,a
        ld      d,a
dm_add:
        push    de
        ld      de,(dm_m)
        add     hl,de
        ld      (dm_m),hl
        pop     hl
        ld      de,(dm_b)
        add     hl,de
        ld      (dm_b),hl
        ret

; dm_crect — A = η άλλη άκρη ενός διαδρόμου του (dm_n): το ορθογώνιό του στη
; λίστα.
dm_crect:
        ld      c,a
        ld      a,(dm_n)
        call    dmr_pair
        ld      hl,dmv_t
; dmv_put — HL -> ένα ορθογώνιο (x0, y0, w, h σε tiles): στη λίστα.
dmv_put:
        ld      de,(dmv_p)
        ld      bc,4
        ldir
        ld      (dmv_p),de
        ret

; dmr_pair — A, C = οι δύο άκρες ενός διαδρόμου: στο dmv_t το ορθογώνιο από
; κέντρο σε κέντρο, με ένα tile γύρω — το μισό πλάτος, και ο αρμός στον
; δακτύλιο. Ενας διάδρομος δεν βγαίνει από εκεί, ούτε με τη στροφή του.
; Τράπεζα 6.
dmr_pair:
        push    af
        ld      a,c
        call    mt_rec
        ld      c,(hl)                  ; cx
        inc     hl
        ld      b,(hl)                  ; cy
        pop     af
        push    bc
        call    mt_rec
        pop     bc
        ld      de,dmv_t
        ld      a,(hl)
        call    dmc_axis                ; x0 και πλάτος
        inc     hl
        ld      a,(hl)
        ld      c,b                     ; και y0 και ύψος, στο dmc_axis
; dmc_axis — A, C = τα δύο κέντρα σε έναν άξονα (προσημασμένα μισά tiles), DE
; -> x0 (ή y0) ενός ορθογωνίου: (DE) = το μικρότερο tile - 1, (DE + 2) = όσα
; ως το μεγαλύτερο + 1. DE + 1 μετά. Κρατά B, HL.
dmc_axis:
        push    hl
        add     a,128
        ld      l,a
        ld      a,c
        add     a,128
        cp      l
        jr      nc,dmca_s               ; A = το μεγαλύτερο, L = το μικρότερο
        ld      h,a
        ld      a,l
        ld      l,h
dmca_s:
        srl     a                       ; tile + 64
        srl     l
        sub     l
        add     a,3
        inc     de
        inc     de
        ld      (de),a
        dec     de
        dec     de
        ld      a,l
        sub     64 + 1
        ld      (de),a
        inc     de
        pop     hl
        ret

        ; Η εγγραφή ενός κόμβου είναι το mt_rec (src/meteor.asm): A -> HL, με
        ; την 6 μέσα, χαλάει A και DE. Ως το βήμα 102 εδώ υπήρχε αντίγραφό του.
        assert  D_STATE == ST_STATE && D_SIZE == ST_KIND && J_BUILD == 0

; ΟΙ ΜΕΤΑΒΛΗΤΕΣ ΔΕΝ ΓΡΑΦΟΝΤΑΙ στο ovl.bin ούτε στις τρύπες (nocode): ζουν
; στο GH_BUF μετά τον κώδικα, και το dm_do τις γράφει πριν τις διαβάσει.
dm_ovl_code:
        nocode
dm_st:      db 0
dm_par:     db 0                ; ο γονιός του γκρεμισμένου (dm_paths), 255 = κανένας
dm_in:      db 0
dm_m:       dw 0
dm_b:       dw 0
dmv_p:      dw 0                ; η επόμενη θέση της λίστας
dmv_t:      defs 4              ; ένα ορθογώνιο υπό κατασκευή
dmv_r:      defs 4 * (1 + MAX_DEGREE)   ; το αποτύπωμα, και ένα ανά διάδρομο
dm_ovl_vars:
        code    skip            ; το $ πίσω στο dm_ovl_code (rasm)
        assert  dm_ovl_vars <= GH_BUF + GH_LOG
