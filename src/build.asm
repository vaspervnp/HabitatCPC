; build.asm — τι χτίζεται, πού επιτρέπεται, και τι γίνεται όταν μπει
; (DESIGN §6.9, §9.3).
;
; Ο κατάλογος είναι ΕΠΙΠΕΔΟΣ: ένδεκα αντικείμενα σε μια σειρά, όχι το δέντρο
; «κατηγορία -> είδος -> μέγεθος» του §9.3. Με ένδεκα επιλογές το δέντρο
; κοστίζει τρία πατήματα εκεί που χρειάζεται ένα, και ο κατάλογος χωράει σε μία
; γραμμή του HUD. Αν φτάσουν τα τριάντα, ξαναγίνεται δέντρο.
;
; Η ΙΣΟΤΙΜΙΑ ΔΕΝ ΕΙΝΑΙ ΕΠΙΛΟΓΗ ΤΟΥ ΠΑΙΚΤΗ (§3.4): αντικείμενο W tiles πλατύ
; έχει το κέντρο του W μισά tiles από την αριστερή του άκρη, άρα το κέντρο και
; το W έχουν την ΙΔΙΑ ισοτιμία. Ο κέρσορας κουμπώνει μόνος του όταν αλλάζει
; αντικείμενο· ο παίκτης δεν το βλέπει ποτέ.

BLD_REC     equ 8
; RES_NEAR: στο const.asm από το βήμα 67 — το src/terrain.asm το χρειάζεται
; πριν από εδώ (βλ. εκεί).
BK_DOME     equ 0
BK_STRUCT   equ 1
BK_LINK     equ 2
BLD_N       equ 11

; ---------------------------------------------------------------------------
; bd_select — A = αντικείμενο· γεμίζει bd_kind/bd_param/bd_w/bd_h/bd_cost και
; κουμπώνει τον κέρσορα στη σωστή ισοτιμία.
; ---------------------------------------------------------------------------
bd_select:
        cp      BLD_N
        ret     nc
        add     a,a
        add     a,a
        add     a,a                     ; *BLD_REC
        ld      l,a
        ld      h,0
        ld      de,bld_items
        add     hl,de
        ld      de,bd_kind
        ld      bc,BLD_REC
        ldir
        ; --- ισοτιμία: μισό tile πιο πέρα, αν το κέντρο δεν ταιριάζει ---
        ; Στο 127 το «πιο πέρα» θα ήταν το -128, η απέναντι άκρη του κόσμου:
        ; εκεί πάει μισό tile πίσω (βήμα 78).
        ld      hl,cur_hx
        ld      a,(bd_w)
        xor     (hl)
        rra                             ; CY: άλλη ισοτιμία
        jr      nc,bds_y
        inc     (hl)
        jp      po,bds_y
        ld      (hl),126
bds_y:
        inc     hl                      ; cur_hy
        ld      a,(bd_h)
        xor     (hl)
        rra
        jr      nc,bds_sz
        inc     (hl)
        jp      po,bds_sz
        ld      (hl),126
bds_sz:
        ; Το μέγεθος μιας δομής βγαίνει από το είδος: τα τέσσερα ενεργειακά
        ; υπάρχουν σε τρία μεγέθη και ο κατάλογος δίνει το μεγάλο· ορυχείο,
        ; αεροθάλαμος και πλατφόρμα υπάρχουν μόνο στη θέση 0 του struct_dims.
        ld      a,(bd_param)
        cp      K_MINE
        sbc     a,a                     ; -1 πριν από το ορυχείο, 0 από εκεί
        and     2
        ld      (bd_size),a
        ; Το δωμάτιο οξυγόνου χωράει μόνο σε μικρό θόλο: αλλάζοντας μέγεθος, η
        ; επιλογή μπορεί να έγινε άκυρη μόνη της (§6.5).
        jp      rm_fix                  ; cur_hx, cur_hy διπλανά: assert στο ui.asm

; ---------------------------------------------------------------------------
; bd_redraw — το αποτύπωμα του κτίσματος που μόλις μπήκε, και τίποτε άλλο.
; Το θεμέλιο και το εργοτάξιο είναι ΟΛΗ η αλλαγή (view_rect). Εδώ και όχι στο
; ui.asm: τρέχει μία φορά ανά τοποθέτηση, άρα είναι κρύος κώδικας και ζει
; στην τράπεζα 2 όπως το bd_commit που τον προκαλεί (§4.3).
;
; Out: Z = ζωγραφίστηκε τώρα· NZ = θα εμφανιστεί σε λωρίδες (ένας θόλος).
;
; Ο ΘΟΛΟΣ ΕΜΦΑΝΙΖΕΤΑΙ ΜΙΑ ΣΕΙΡΑ TILES ΤΗ ΦΟΡΑ, όπως το ζητά το §6.9 βήμα 4.
; Ως το βήμα 35 ζωγραφιζόταν εδώ ολόκληρος: 450 ms για έναν L, γιατί τα δύο
; κελύφη του είναι οκτώ τεταρτημόρια 16x64 με μάσκα, τα έξι καθρεφτισμένα —
; σχεδόν όσο ολόκληρο το κάδρο (405). Κάθε σειρά μπαίνει στη λίστα αλλαγών
; (DK_SITE) και βγαίνει μία ανά frame, οπότε ο θόλος «υλοποιείται» από πάνω
; προς τα κάτω και η προσομοίωση, ο ήχος και ο κέρσορας δεν σταματούν. Μια δομή
; είναι το πολύ 4x4 tiles ενός sprite και ζωγραφίζεται αμέσως.
; ---------------------------------------------------------------------------
bd_redraw:
        call    bd_rect
        ld      a,(bd_kind)
        or      a                       ; BK_DOME
        jr      z,bdr_bands
        ld      hl,(bd_tx)              ; και το bd_ty
        ld      (vr_tx),hl              ; και το vr_ty
        ld      hl,(bd_w)               ; και το bd_h
        ld      (vr_w),hl               ; και το vr_h
        ; ΜΟΝΟ Η ΔΟΜΗ πάνω στο έδαφος, όχι το ob_draw_all: το αποτύπωμα είναι
        ; δικό της. Το πλήρες πέρασμα θα ρωτούσε 64 θόλους, 96 διαδρόμους και
        ; όλες τις δομές, και θα ξανάχτιζε τα δύο ευρετήρια που μόλις ακύρωσε
        ; το bd_commit — 35 ms από τα 160 ενός ηλιακού (βήμα 35).
        call    vr_tiles
        jr      z,bdr_out
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        ld      a,(bd_node)
        sub     MAX_DOME
        call    ob_struct
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        call    ob_clip_full
bdr_out:
        xor     a
        ret
bdr_bands:
        ld      a,(bd_h)
        ld      e,a                     ; σειρές
        ld      a,(bd_node)
        ld      b,a
        ld      c,0
bdr_lp:
        ld      a,DK_SITE
        call    dirty_push              ; κρατά BC, E
        ld      hl,rv_pend
        inc     (hl)
        inc     c
        dec     e
        jr      nz,bdr_lp
        inc     e                       ; NZ
        ret

        assert  BK_DOME == 0            ; vr_* ανά δύο: assert στο view.asm

; ---------------------------------------------------------------------------
; bd_rect — πάνω-αριστερά tile του αποτυπώματος, από το κέντρο του κέρσορα.
;       left_tile = (cur_hx - W) / 2      (ακριβές: ίδια ισοτιμία)
; Out: (bd_tx), (bd_ty) προσημασμένα· CY αν βγαίνει έξω από τον κόσμο — και
; τότε, αν φταίει το x, το bd_ty μένει όπως ήταν.
;
; ΣΕ 8 BIT (βήμα 73). Το κέντρο + 128 είναι ανυπόγραφο, και η διαφορά του από
; το W έχει ένατο bit το δανεικό: το rra τα κάνει όλα μαζί το μισό, και το
; αποτέλεσμα είναι το πρώτο tile + 64, που μέσα στον κόσμο πάει 0..128-W. Ως
; το βήμα 72 ήταν 16 bit με το ob_sext και ένα bd_range με δύο αφαιρέσεις.
; ---------------------------------------------------------------------------
bd_rect:
        ld      hl,bd_w
        ld      de,bd_tx
        ld      a,(cur_hx)
        call    bdr_one
        ret     c                       ; το bd_ty μένει όπως ήταν
        inc     hl                      ; bd_h
        inc     de                      ; bd_ty
        ld      a,(cur_hy)
; bdr_one — A = κέντρο σε μισά tiles, (HL) = μήκος σε tiles -> (DE) = το
; πρώτο tile, προσημασμένο. CY αν [πρώτο, πρώτο+μήκος) βγαίνει από το -64..63.
bdr_one:
        xor     #80
        sub     (hl)
        rra                             ; πρώτο + 64
        ld      c,a
        sub     64
        ld      (de),a
        ld      a,128
        sub     (hl)
        cp      c                       ; CY: πρώτο + 64 > 128 - μήκος
        ret

; ---------------------------------------------------------------------------
; bd_check — κάθε tile του αποτυπώματος. Απαιτεί ΤΡΑΠΕΖΑ 4.
;
; Το §6.9 λέει: έδαφος, σκόνη ή θεμέλιο, και η κατοχή ελεύθερη. Τα κακά tiles
; σημειώνονται στο bd_bad (ένα byte ανά σειρά, ένα bit ανά στήλη) ώστε το
; φάντασμα να δείξει ΠΟΙΟ φταίει και όχι μόνο ότι κάτι φταίει.
; Out: A = πλήθος κακών tiles (0 = επιτρέπεται), 255 έξω από τον κόσμο — ή 1
;      από το bd_res παρακάτω, όταν τα tiles είναι μια χαρά αλλά λείπει το
;      υλικό της δομής. Το ποιο λείπει το λέει το (bd_nres), και ο πίνακας το
;      διαβάζει για να το πει.
;
; Τρέχει σε κάθε βήμα του κέρσορα (ui_validate). Το bd_ok κρατά τα πάντα εκτός
; από το A, άρα τα tiles μετριούνται σε καταχωρητή και κάθε σειρά είναι η
; προηγούμενη + 128 (tile_addr) — ως το βήμα 72 κάθε tile πλήρωνε τρία push
; και τρία pop, και κάθε σειρά ένα tile_addr.
; ---------------------------------------------------------------------------
bd_check:
        ld      hl,bd_bad
        ld      b,8
        xor     a
bdc_z:
        ld      (hl),a
        inc     hl
        djnz    bdc_z
        call    bd_rect
        ld      a,255                   ; έξω από τον κόσμο: όλα άκυρα
        ret     c
        ld      hl,(bd_tx)              ; L = x, H = y
        ld      b,l
        ld      c,h
        call    tile_addr
        ld      de,bd_bad
        ld      c,0                     ; τα κακά tiles
        ld      a,(bd_h)
bdc_rl:
        push    af                      ; οι σειρές που μένουν
        push    hl
        push    de
        ld      a,(bd_w)
        ld      b,a
        ld      de,#0100                ; D = το bit της στήλης, E = τα κακά της σειράς
bdc_cl:
        ld      a,(hl)
        call    bd_ok
        jr      z,bdc_good
        ld      a,e
        or      d
        ld      e,a
        inc     c
bdc_good:
        sla     d
        inc     hl
        djnz    bdc_cl
        ld      a,e
        pop     de
        ld      (de),a
        inc     de
        pop     hl
        ld      a,l                     ; η επόμενη σειρά: +128
        add     a,128
        ld      l,a
        jr      nc,bdc_nx
        inc     h
bdc_nx:
        pop     af
        dec     a
        jr      nz,bdc_rl
        or      c                       ; A = 0: το πλήθος
        ret     nz
        ; Το αποτύπωμα πατάει· φτάνει και στο υλικό; Ο έλεγχος ζει στην ΤΡΑΠΕΖΑ
        ; 0 (src/terrain.asm) επειδή εδώ πάνω δεν χωρούσε — δες το src/main.asm.
        jp      bd_res

; bd_ok — A = world byte. Z αν το tile επιτρέπεται: χωρίς κατοχή, και έδαφος
; (0), σκόνη (1) ή θεμέλιο (7). Χαλάει ΜΟΝΟ το A.
bd_ok:
        and     W_OCC_MASK + 7          ; το decor (6, 7) και το bit 3 δεν μετράνε
        ret     z
        dec     a
        ret     z
        cp      W_FOUNDATION - 1
        ret

        assert  W_DUST == 1 && W_OCC_MASK == #30

; ---------------------------------------------------------------------------
; bd_afford — έχει η αποικία τα υλικά; Z και A = 0 αν ναι, NZ και A = 1 αν
; όχι (το fit_show φτιάχνει το χρώμα από το A). Κρατά το BC.
; ---------------------------------------------------------------------------
bd_afford:
        ld      de,(bd_metal)           ; E = μέταλλο, D = βιοπλαστικό
        ld      hl,(EC_STOCK + S_METAL*2)
        ld      a,l
        sub     e
        ld      a,h
        sbc     a,0
        jr      c,bda_no
        ld      hl,(EC_STOCK + S_BIOPL*2)
        ld      a,l
        sub     d
        ld      a,h
        sbc     a,0
bda_no:
        sbc     a,a                     ; -1 αν δεν φτάνει
        neg                             ; 1 και NZ, ή 0 και Z
        ret

; ---------------------------------------------------------------------------
; bd_commit — βάζει το αντικείμενο. Απαιτεί έγκυρο αποτύπωμα και υλικά.
; Out: A = ο κόμβος που δημιουργήθηκε, ή 255.
;
; Το §6.9 λέει «το κόστος ΔΕΣΜΕΥΕΤΑΙ, δεν ξοδεύεται ακόμη». Εδώ ξοδεύεται
; αμέσως: δεν υπάρχει δεξαμενή δέσμευσης στην οικονομία και μια ψεύτικη θα
; ήταν χειρότερη από μια ειλικρινή απλοποίηση. Η ΚΑΤΑΣΚΕΥΗ όμως μένει: ο θόλος
; μπαίνει ως DS_BUILDING με ακεραιότητα 0 και δημοσιεύεται εργασία Build.
; ---------------------------------------------------------------------------
bd_commit:
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        ld      a,(bd_kind)
        cp      BK_STRUCT
        jr      z,bdk_struct
        ; --- θόλος ---
        ld      bc,MAX_DOME * 256       ; B = πόσοι μένουν, C = ο θόλος
bdk_find:
        ld      a,c
        call    ob_dome_live            ; HL -> D_STATE
        jr      z,bdk_got
        inc     c
        djnz    bdk_find
bdk_full:
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        ld      a,255
        ret
bdk_got:
        ld      (bd_node),a
        push    hl
        call    rm_room                 ; ό,τι διάλεξε ο παίκτης με πάνω-κάτω
        pop     hl
        call    bdk_rec                 ; δωμάτιο, DS_BUILDING, ακεραιότητα 0
        ld      (hl),a                  ; χειριστές
        inc     hl
        ld      bc,8 * 256 + NO_MACH
bdk_m:
        ld      (hl),c
        inc     hl
        djnz    bdk_m
        ld      b,8
bdk_h:
        ld      (hl),a
        inc     hl
        djnz    bdk_h
        ; Ο ΘΟΛΟΣ ΜΠΑΙΝΕΙ ΑΔΕΙΟΣ (βήμα 45, όπως στο Planetbase). Τις μηχανές
        ; τις διαλέγει ο παίκτης μία-μία και τις πληρώνει χωριστά, και μπορεί
        ; από τώρα, πάνω στο εργοτάξιο: φαίνονται όταν χτιστεί (src/fit.asm).
        jr      bd_link
bdk_struct:
        ld      hl,G_struct_tbl + ST_STATE
        ld      de,STRUCT_REC
        ld      bc,MAX_STRUCT * 256 + MAX_DOME  ; C = ο κόμβος: 64 + δομή
bds_find:
        ld      a,(hl)
        or      a
        jr      z,bds_got
        add     hl,de
        inc     c
        djnz    bds_find
        jr      bdk_full
bds_got:
        ld      a,c
        ld      (bd_node),a
        ld      a,(bd_size)
        call    bdk_rec                 ; μέγεθος, DS_BUILDING, 0, 0

; ---------------------------------------------------------------------------
; bd_link — το θεμέλιο, η πληρωμή, η εργασία Build.
;
; ΧΩΡΙΣ ΑΚΜΗ ΑΠΟ ΤΟ ΒΗΜΑ 85. Ως τότε εδώ το εργοτάξιο έπαιρνε μια «ακμή
; εξωτερικού χώρου» προς τον κοντινότερο ζωντανό θόλο, όσο μακριά κι αν ήταν,
; και χωρίς τίποτα να τη ζωγραφίσει. Τώρα το κτίσμα μπαίνει μόνο κοντά σε άλλο,
; και τους δεσμούς — διαδρόμους ή μονοπάτι, όπως τους έδειξε το φάντασμα —
; τους βάζει το al_commit (src/link.asm) αμέσως μετά από εδώ. Το πρώτο κτίσμα
; του κόσμου μένει χωρίς ακμή, όπως πάντα.
; Με την τράπεζα 6 ακόμη στο παράθυρο από την εγγραφή.
; ---------------------------------------------------------------------------
bd_link:
; --- τα tiles γίνονται θεμέλιο και δεσμευμένα (§6.9 βήμα 2) ---------------
        ld      bc,GA_PORT + PAGE_B4
        out     (c),c
        ld      hl,(bd_tx)              ; L = x, H = y
        ld      b,l
        ld      c,h
        call    tile_addr
        ld      a,(bd_h)
        ld      c,a
bst_rl:
        push    hl
        ld      a,(bd_w)
        ld      b,a
bst_cl:
        ld      a,(hl)
        and     #C0                     ; το decor μένει
        or      W_FOUNDATION + W_OCC_STRUCT
        ld      (hl),a
        inc     hl
        djnz    bst_cl
        pop     hl
        ld      de,128
        add     hl,de                   ; η επόμενη σειρά (tile_addr)
        dec     c
        jr      nz,bst_rl
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        call    bd_stock_pay            ; πληρώνει ΑΦΟΥ βρεθεί θέση
bdk_post:
        ; Με την εργασία Build, το ΠΡΩΤΟ είδος εργασίας που δέχονται τα ρομπότ
        ; απέκτησε πηγή: ως τότε κανείς δεν δημοσίευε Haul, Drill ή Build, και
        ; το ορόσημο «αυτοματισμός» του §10.2 ήταν απρόσιτο εξ ορισμού.
        ld      a,(bd_node)
        call    jb_post_build           ; src/jobs.asm — και για τον μετεωρίτη· κρατά το A
        jp      ob_touch_n              ; μόνο η κατηγορία του· κρατά το A

; bdk_rec — HL -> D_STATE / ST_STATE μιας εγγραφής, A = το τέταρτο byte
; (δωμάτιο ή μέγεθος): γράφει cx, cy, bd_param, A, DS_BUILDING, 0, 0.
; Out: HL -> το όγδοο byte, A = 0.
bdk_rec:
        dec     hl
        dec     hl
        dec     hl
        dec     hl                      ; η αρχή της εγγραφής
        ld      de,(cur_hx)             ; E = cx, D = cy
        ld      (hl),e
        inc     hl
        ld      (hl),d
        inc     hl
        ld      e,a
        ld      a,(bd_param)            ; μέγεθος θόλου, ή είδος δομής
        ld      (hl),a
        inc     hl
        ld      (hl),e
        inc     hl
        ld      (hl),DS_BUILDING
        inc     hl
        xor     a
        ld      (hl),a
        inc     hl
        ld      (hl),a
        inc     hl
        ret

        assert  D_STATE == 4 && ST_STATE == 4

; bd_stock_pay — αφαιρεί το κόστος. Κρατά το BC (fit_set).
bd_stock_pay:
        ld      de,(bd_metal)           ; E = μέταλλο, D = βιοπλαστικό
        ld      hl,(EC_STOCK + S_METAL*2)
        ld      a,l
        sub     e
        ld      l,a
        jr      nc,bsp_m
        dec     h
bsp_m:
        ld      (EC_STOCK + S_METAL*2),hl
        ld      hl,(EC_STOCK + S_BIOPL*2)
        ld      a,l
        sub     d
        ld      l,a
        jr      nc,bsp_b
        dec     h
bsp_b:
        ld      (EC_STOCK + S_BIOPL*2),hl
        ret

; --- ο κατάλογος -----------------------------------------------------------
; είδος, παράμετρος, W tiles, H tiles, μέταλλο, βιοπλαστικό, όνομα
;
; Τα κόστη είναι ΠΡΩΤΕΣ ΕΚΤΙΜΗΣΕΙΣ, όπως κάθε αριθμός του §6.5 πριν παιχτεί.
; ΤΟ ΒΙΟΠΛΑΣΤΙΚΟ ΣΦΡΑΓΙΖΕΙ, ΔΕΝ ΣΤΗΡΙΖΕΙ. Οι εξωτερικές δομές — πάνελ,
; ανεμογεννήτρια, συλλέκτης, αντλία, ορυχείο, πίστα — είναι σκελετοί στον αέρα
; και κοστίζουν ΜΕΤΑΛΛΟ μόνο· βιοπλαστικό θέλει ό,τι κρατά ατμόσφαιρα: θόλοι,
; διάδρομοι, αεροθάλαμος. Ως το βήμα 27 τα πάντα ήθελαν και τα δύο, και το
; βιοπλαστικό ήταν το πραγματικό ταβάνι: η αποικία ξόδευε τα τριάντα της στα
; τέσσερα πρώτα κτίσματα και μετά δεν μπορούσε να χτίσει ΤΙΠΟΤΑ, επειδή η
; μόνη πηγή βιοπλαστικού (mach_bioplastic) θέλει θερμοκήπιο και μεσαίο
; εργοστάσιο — δηλαδή δύο θόλους που κοστίζουν βιοπλαστικό.
; ΤΟ ΚΕΛΥΦΟΣ ΜΟΝΟ (βήμα 45): οι μηχανές πληρώνονται χωριστά (fit_cost,
; src/fit.asm). Ενας μικρός θόλος με τη μηχανή του κοστίζει όσο πριν, 20/10,
; ώστε το άνοιγμα του §10.1 να μένει το ίδιο· οι μεγάλοι κοστίζουν όσο
; γεμίσουν.
bld_items:
        db BK_DOME,  0, 4,4, 12, 8
        dw t_dome_s
        db BK_DOME,  1, 6,6, 24,14
        dw t_dome_m
        db BK_DOME,  2, 8,8, 40,24
        dw t_dome_l
        db BK_LINK,  0, 1,1, CORR_M, CORR_B     ; και ο αυτόματος (src/link.asm)
        dw t_corr
        db BK_STRUCT,K_SOLAR,   3,3, 15, 0
        dw t_solar
        db BK_STRUCT,K_TURBINE, 3,3, 18, 0
        dw t_turb
        db BK_STRUCT,K_COLLECT, 3,3, 14, 0
        dw t_coll
        db BK_STRUCT,K_EXTRACT, 3,3, 22, 0
        dw t_extr
        db BK_STRUCT,K_MINE,    4,4, 30, 0
        dw t_mine
        db BK_STRUCT,K_AIRLOCK, 2,2, 10, 6
        dw t_lock
        db BK_STRUCT,K_PAD,     4,4, 45, 0
        dw t_pad

t_dome_s:   db "DOME S   ",0
t_dome_m:   db "DOME M   ",0
t_dome_l:   db "DOME L   ",0
t_corr:     db "CORRIDOR ",0
t_pathw:    db "PATH     ",0          ; το I πάνω στο μονοπάτι (src/info.asm, βήμα 85)
t_solar:    db "SOLAR    ",0
t_turb:     db "TURBINE  ",0
t_coll:     db "COLLECTOR",0
t_extr:     db "EXTRACTOR",0
t_mine:     db "MINE     ",0
t_lock:     db "AIRLOCK  ",0
t_pad:      db "LANDING  ",0

; --- η τρέχουσα επιλογή, αντιγραμμένη από τον κατάλογο ---------------------
bd_kind:    db 0
bd_param:   db 0
bd_w:       db 0
bd_h:       db 0
bd_metal:   db 0
bd_biop:    db 0
bd_name:    dw 0
bd_size:    db 2                ; μέγεθος δομής· οι δομές του καταλόγου είναι l
bd_rsel:    db 0                ; θέση στον κατάλογο δωματίων (src/rooms.asm)
bd_tx:      db 0
bd_ty:      db 0
bd_node:    db 255
bd_bad:     defs 8
; ΠΟΙΟ ΥΛΙΚΟ ΛΕΙΠΕΙ, ή ΓΙΑΤΙ ΔΕΝ ΔΕΝΕΤΑΙ: 0 κανένα, 1 νερό, 2 φλέβα (bd_res,
; src/terrain.asm), 3 τίποτα σε απόσταση, 4 ο δρόμος κομμένος (al_plan,
; src/link.asm). Ως το βήμα 84 ζούσε στο terrain.asm και έμενε από την
; προηγούμενη θέση όταν το αποτύπωμα είχε κακά tiles· τώρα το μηδενίζει το
; ui_validate πριν από κάθε έλεγχο.
bd_nres:    db 0
        assert  bd_ty == bd_tx + 1 && bd_h == bd_w + 1  ; το ui_rect τα διαβάζει ανά δύο
        assert  bd_biop == bd_metal + 1         ; το fit_price τα γράφει μαζί
        assert  bd_param == bd_kind + 1 && BK_STRUCT == 1       ; το bd_res (src/terrain.asm)
