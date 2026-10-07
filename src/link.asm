; link.asm — πώς ένα νέο κτίσμα δένεται με την αποικία (DESIGN §9.3, βήμα 85).
;
; Ο ΚΑΝΟΝΑΣ ΕΙΝΑΙ ΤΟΥ ΠΑΙΚΤΗ, όπως τον ζήτησε:
;
;   * Το ΠΡΩΤΟ κτίσμα του κόσμου μπαίνει όπου το επιτρέπει το έδαφος.
;   * Κάθε επόμενο θέλει κάποιο κτίσμα ως AL_RANGE = 12 tiles μακριά, και
;     δένεται μαζί του τη στιγμή που τοποθετείται:
;       - ένας θόλος με ΣΚΕΠΑΣΤΟ διάδρομο προς ΚΑΘΕ θόλο που ο διάδρομος
;         φτάνει με το πολύ 12 πλακίδια — ως AL_MAX = 4, όσα χωρά το αρχείο
;         του φαντάσματος (assert πιο κάτω)·
;       - μια δομή, ή ένας θόλος που δεν βρήκε διάδρομο, με ΜΟΝΟΠΑΤΙ στο
;         έδαφος προς το κοντινότερο κτίσμα, θόλο ή δομή. Χωρίς σκέπαστρο:
;         όποιος το περπατά είναι έξω. Είναι ένα Γ από το κεντρικό tile του
;         ενός στο κεντρικό tile του άλλου, και μετρούν μόνο τα tiles του έξω
;         από τα δύο αποτυπώματα: το πολύ 12, όλα πάνω σε έδαφος που χτίζεται
;         (bd_ok). Δοκιμάζονται και τα δύο Γ — πρώτα κατά x, μετά κατά y — και
;         κρατιέται το κοντύτερο· σε ισοπαλία το πρώτο που βρέθηκε.
;   * Αλλιώς το φάντασμα είναι κόκκινο, και ο πίνακας λέει γιατί: TOO FAR αν
;     κανένα κτίσμα δεν είναι σε απόσταση, PATH BLOCKED αν κάποιο είναι αλλά
;     το έδαφος ή ένα άλλο κτίσμα κόβει τον δρόμο (bd_nres = 3, 4).
;
; Το μονοπάτι γίνεται θεμέλιο με κατοχή 2 (W_OCC_PATH): ο κόσμος το δείχνει
; ως ισοπεδωμένο έδαφος, τίποτα δεν χτίζεται από πάνω του, και το I το λέει
; PATH. Ο διάδρομος κρατά την κατοχή 1 που είχε πάντα (cr_stamp).
;
; ΓΙΑΤΙ Ο ΕΛΕΓΧΟΣ ΓΙΝΕΤΑΙ ΣΕ ΚΑΘΕ ΒΗΜΑ ΚΕΡΣΟΡΑ. Το φάντασμα δείχνει τους
; διαδρόμους και το μονοπάτι ΠΡΙΝ από το FIRE, και το κόστος τους μετρά στο
; «φτάνουν τα υλικά»: ό,τι δείχνει είναι ακριβώς ό,τι θα χτιστεί. Γι' αυτό οι
; διάδρομοι που διαλέγονται σφραγίζονται ΠΡΟΣΩΡΙΝΑ στον κόσμο (bit 5) ώσπου
; να τελειώσει η αναζήτηση: δύο διάδρομοι του ίδιου θόλου δεν διασταυρώνονται,
; και το FIRE ξαναπαίζει την ίδια λίστα χωρίς να ξαναρωτήσει.

AL_RANGE    equ 12
AL_MAX      equ 4
CORR_M      equ 6                   ; ο διάδρομος ανά πλακίδιο: build.asm, bld_items
CORR_B      equ 3
W_OCC_PATH  equ #20

        ; ΤΟ ΧΕΙΡΟΤΕΡΟ ΠΡΑΣΙΝΟ ΦΑΝΤΑΣΜΑ: το πλαίσιο ενός θόλου L και AL_MAX
        ; διάδρομοι, ως AL_RANGE + 1 σημάδια ο καθένας (η διαγώνιος n βημάτων
        ; είναι n + 1 tiles, η στροφή δεν προσθέτει).
        assert  2 * (GH_HDR + GH_SIDE * 4 * GH_EDGE) + 2 * (GH_HDR + GH_SIDE * 16 - 2 * GH_EDGE) + AL_MAX * (AL_RANGE + 1) * (GH_HDR + 8) <= GH_LOG

; ---------------------------------------------------------------------------
; al_plan — In: A = ό,τι είπε το bd_check (0: το αποτύπωμα πατά), τράπεζα 4.
; Out: A = 0 αν χτίζεται εδώ· το πλήθος των κακών tiles, ή 255 έξω από τον
; κόσμο· ή #F0 + bd_nres όταν τα tiles είναι καλά αλλά κάτι άλλο λείπει: F1
; νερό, F2 φλέβα (bd_res), F3 TOO FAR, F4 PATH BLOCKED. Γυρίζει με την
; τράπεζα 1 (uid_out).
;
; ΤΟ #F0 + ΛΟΓΟΣ ΕΙΝΑΙ ΓΙΑ ΤΟΝ ΠΙΝΑΚΑ. Το A γίνεται ui_bad, και το ui_bad είναι
; στην υπογραφή των σειρών 3-4 (ui_sig) ενώ το bd_nres όχι: ως το βήμα 84 μια
; αντλία που περνούσε από ένα κακό tile σε στεγνό έδαφος έβγαζε ui_bad = 1 και
; στα δύο, και ο πίνακας έμενε στο BLOCKED αντί για NEEDS WATER. Με τέσσερις
; λόγους πια, κάθε λόγος έχει δικό του ui_bad — ένα αποτύπωμα έχει ως 64 tiles.
;
; Γράφει ΠΑΝΤΑ το σύνολο του κόστους — κτίσμα και διάδρομοι — στο cr_metal,
; cr_biop (16 bit), όπου το διαβάζουν ο πίνακας (uip_item, και η υπογραφή του)
; και το al_afford.
; ---------------------------------------------------------------------------
al_plan:
        ld      hl,al_n
        ld      (hl),0
        inc     hl                      ; al_len
        ld      (hl),0
        inc     hl                      ; al_pt
        ld      (hl),255
        or      a
        call    z,al_find
        push    af
        ld      a,(al_len)
        ld      c,CORR_M
        call    ob_mul                  ; HL = A * C· το A μένει
        ld      de,(bd_metal)           ; E = μέταλλο, D = βιοπλαστικό
        push    de
        ld      d,0
        add     hl,de
        ld      (cr_metal),hl
        ld      c,CORR_B
        call    ob_mul
        pop     de
        ld      e,d
        ld      d,0
        add     hl,de
        ld      (cr_biop),hl
        pop     af
        ld      hl,bd_nres
        inc     (hl)
        dec     (hl)
        jp      z,uid_out               ; τα tiles, ή 0
        ld      a,(hl)
        or      #F0
        jp      uid_out

; al_afford — Z και A = 0 αν φτάνουν τα υλικά για ΟΛΟ το σύνολο του al_plan.
al_afford:
        ld      hl,(cr_metal)
        jp      cra_tot

; ---------------------------------------------------------------------------
; al_find — οι δεσμοί του κτίσματος κάτω από τον κέρσορα. Out: A = 0 ή 1.
; ---------------------------------------------------------------------------
al_find:
        ld      hl,(bd_tx)              ; το αποτύπωμα: x0, y0, w, h
        ld      (al_nx),hl
        ld      hl,(bd_w)
        ld      (al_nw),hl
        ld      hl,(cur_hx)             ; και το κεντρικό του tile
        sra     l
        sra     h
        ld      b,l
        ld      c,h
        ld      (al_p),bc               ; al_p = y, al_p + 1 = x
        xor     a
        ld      (al_why),a
        ld      (al_any),a
        ld      a,(bd_kind)
        or      a                       ; BK_DOME
        jr      nz,alf_path
        ; --- ένας θόλος: διάδρομος προς κάθε θόλο σε απόσταση ---
        ld      hl,al_cor1
        call    al_scand
        ld      hl,al_cunt              ; οι προσωρινές σφραγίδες φεύγουν
        call    al_each
        ld      a,(al_n)
        or      a
        jr      z,alf_path
        xor     a
        ret
        ; --- αλλιώς μονοπάτι, προς το κοντινότερο κτίσμα ---
alf_path:
        ld      a,AL_RANGE + 1
        ld      (al_best),a
        ld      hl,al_try
        call    al_scan
        ld      a,(al_pt)
        inc     a
        jr      nz,alf_ok
        ld      a,(al_any)
        or      a
        ret     z                       ; τίποτα χτισμένο: το πρώτο, όπου θέλει
        ld      a,(al_why)
        add     a,3                     ; 3 TOO FAR, 4 PATH BLOCKED
        ld      (bd_nres),a
        ld      a,1
        ret
alf_ok:
        xor     a
        ret

; ---------------------------------------------------------------------------
; al_scan — HL = ρουτίνα: κάθε κτίσμα σε απόσταση, θόλοι και δομές. al_scand —
; μόνο οι θόλοι. Η ρουτίνα καλείται με A = κόμβο για κάθε κτίσμα που υπάρχει
; και που το κέντρο του απέχει ως AL_REACH μισά tiles από τον κέρσορα σε κάθε
; άξονα· το al_any σημειώνει ότι κάτι υπάρχει. Γυρίζει με την τράπεζα 1.
;
; ΓΡΗΓΟΡΑ ΠΑΝΩ ΑΠΟ ΤΑ ΑΔΕΙΑ. Στο πρώτο σχέδιο κάθε θέση του πίνακα πλήρωνε
; σελίδα, πολλαπλασιασμό και αποτύπωμα, και κάθε κτίσμα σε απόσταση δύο Γ: ο
; έλεγχος ενός βήματος κέρσορα με ηλιακό στο χέρι κόστιζε 29 ms, με θόλο ως
; 40. Εδώ ο δείκτης περπατά τους δύο πίνακες με την 6 μέσα, έξι εντολές η
; άδεια θέση. Το όριο είναι ακριβές, όχι εκτίμηση: δύο αποτυπώματα απλώνονται
; ως 8 μισά tiles από το κέντρο τους, άρα κέντρα 41 μισά tiles μακριά αφήνουν
; κενό τουλάχιστον 13 tiles — και ένας διάδρομος 12 πλακιδίων φτάνει ως 20
; tiles κέντρο-κέντρο.
; ---------------------------------------------------------------------------
AL_REACH    equ 2 * (AL_RANGE + 8)

al_scan:
        call    al_scand
        ld      hl,G_struct_tbl + ST_STATE
        ld      de,STRUCT_REC
        ld      bc,MAX_STRUCT * 256 + MAX_DOME
        jr      asc_go
al_scand:
        ld      (al_fn),hl
        ld      hl,G_dome_tbl + D_STATE
        ld      de,DOME_REC
        ld      bc,MAX_DOME * 256       ; B = πόσες θέσεις, C = ο κόμβος
asc_go:
        call    asc_b6
asc_lp:
        ld      a,(hl)                  ; D_STATE = ST_STATE
        or      a
        jr      nz,asc_live
asc_nx:
        add     hl,de
        inc     c
        djnz    asc_lp
        push    bc
        ld      bc,GA_PORT + PAGE_B1
        jr      asc_out
asc_live:
        ld      (al_any),a
        push    bc
        push    de
        push    hl
        dec     hl
        dec     hl
        dec     hl                      ; cy
        ld      de,cur_hy
        call    al_far
        dec     hl                      ; cx
        dec     de                      ; cur_hx
        call    nc,al_far
        ld      a,c
        call    nc,al_call
        call    asc_b6
        pop     hl
        pop     de
        pop     bc
        jr      asc_nx
asc_b6:
        push    bc
        ld      bc,GA_PORT + PAGE_B6
asc_out:
        out     (c),c
        pop     bc
        ret
al_call:
        ld      hl,(al_fn)
        jp      (hl)

; al_far — CY αν |(DE) - (HL)| > AL_REACH μισά tiles (ή >= 128). Κρατά HL, DE.
al_far:
        ld      a,(de)
        sub     (hl)
        jp      pe,alf_far
        jp      p,alf_p
        neg
alf_p:
        cp      AL_REACH + 1
        ccf
        ret
alf_far:
        scf
        ret

; al_cor1 — A = θόλος σε απόσταση: στη λίστα, αν ο διάδρομος βγαίνει και χωρά.
al_cor1:
        ld      c,a
        ld      a,(al_n)
        cp      AL_MAX
        ret     nc
        ld      a,c
        push    bc
        call    al_cor
        pop     bc
        ret     nz
        ld      hl,al_n
        ld      a,(hl)
        inc     (hl)
        ld      hl,al_lst
        call    ob_addu
        ld      (hl),c
        call    cr_pcs
        ld      hl,al_len
        add     a,(hl)
        ld      (hl),a
        ret

; al_cor — A = θόλος: διάδρομος ως εκεί; Z αν ναι — και τότε τα tiles του
; σφραγίζονται προσωρινά, ώστε ο επόμενος να μην περάσει από πάνω του.
al_cor:
        call    al_set
        jr      z,alc_no                ; άδεια θέση, ή δεν υπάρχει σχήμα
        call    cr_pcs
        cp      AL_RANGE + 1
        jr      nc,alc_no
        call    cr_check
        or      a
        ret     nz
        ld      hl,al_ctmp
        call    crw_b4
        xor     a
        ret
alc_no:
        or      1
        ret

; al_set — A = θόλος b: η διαδρομή από το κτίσμα του κέρσορα ως τον b.
; NZ αν υπάρχει (A = cr_n). Το άκρο a είναι ο κέρσορας, όχι ο πίνακας: στον
; έλεγχο το κτίσμα δεν υπάρχει ακόμη, και μετά το bd_commit είναι το ίδιο.
al_set:
        ld      (cr_b),a
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        ld      de,cr_tx
        call    cr_read
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        jr      c,als_no
        ld      a,(bd_node)
        ld      (cr_a),a
        ld      hl,(cur_hx)
        ld      (cr_fx),hl              ; και το cr_fy
        ld      a,(bd_param)
        ld      (cr_fs),a
        jp      cr_pair
als_no:
        xor     a
        ret

; al_each — HL = ρουτίνα ανά tile: κάθε διάδρομος της λίστας με την τράπεζα 4.
al_each:
        ld      (al_ecb),hl
        ld      a,(al_n)
        or      a
        ret     z
        ld      b,a
        ld      hl,al_lst
ale_lp:
        push    bc
        push    hl
        ld      a,(hl)
        call    al_set
        ld      hl,(al_ecb)
        call    crw_b4
        pop     hl
        pop     bc
        inc     hl
        djnz    ale_lp
        ret

; al_ctmp / al_cunt — η προσωρινή σφραγίδα: bit 5, η κατοχή 2, ΜΟΝΟ έξω από
; τα δύο αποτυπώματα. Εκεί τα tiles ήταν ελεύθερα (cr_check), άρα το bit 5 ήταν
; 0 και το res το ξαναφέρνει. Μέσα δεν χρειάζεται: ο έλεγχος δεν κοιτά τα tiles
; των δύο άκρων, και ένας άλλος θόλος είναι ήδη κατειλημμένος. (Ως να γραφτεί
; αυτό, η σφραγίδα έπιανε και το αποτύπωμα του b — και το tests/test_reach.py
; βρήκε κόσμο όπου το bit 5 ήταν ήδη αναμμένο εκεί και το res το έσβηνε.)
al_ctmp:
        call    al_out
        ret     c
        set     5,(hl)
        ret
al_cunt:
        call    al_out
        ret     c
        res     5,(hl)
        ret
; al_out — HL = το tile (B, C)· CY αν είναι μέσα στο αποτύπωμα ενός άκρου.
al_out:
        call    tile_addr
        push    hl
        ld      hl,cr_fx
        call    crk_in
        jr      c,alo_in
        ld      hl,cr_tx
        call    crk_in
alo_in:
        pop     hl
        ret

; ---------------------------------------------------------------------------
; al_try — A = κόμβος: ένα μονοπάτι ως εκεί, κοντύτερο από το al_best;
; ---------------------------------------------------------------------------
al_try:
        ld      (al_t),a
        call    al_node
        ret     c                       ; άδεια θέση
        ; --- ΤΟ ΚΑΤΩ ΟΡΙΟ: το Γ πατά ΤΟΥΛΑΧΙΣΤΟΝ το κενό ανάμεσα στα δύο
        ; αποτυπώματα στον x ΚΑΙ στον y. Το οριζόντιο σκέλος του κάθεται σε
        ; σειρά του ενός και το κάθετο σε στήλη του άλλου, άρα κανένα tile του
        ; δεν είναι και στα δύο κενά. Οτι δεν νικά το καλύτερο ως τώρα δεν
        ; περπατιέται — και το «κομμένο» (al_why) μετρά μόνο όταν δεν βρεθεί
        ; τίποτα, οπότε το al_best είναι ακόμη AL_RANGE + 1.
        ld      hl,al_nx
        ld      de,al_rx
        call    al_gap
        ld      b,a
        inc     hl
        inc     de
        call    al_gap
        add     a,b
        ld      hl,al_best
        cp      (hl)
        ret     nc
        ld      (al_lb),a
        xor     a                       ; πρώτα κατά x
        call    al_ltry
        ; ΤΟ ΔΕΥΤΕΡΟ Γ ΔΕΝ ΝΙΚΑ ΤΟ ΚΑΤΩ ΟΡΙΟ: αν το πρώτο το έπιασε — και σε
        ; αποτυπώματα που επικαλύπτονται σε έναν άξονα σχεδόν πάντα — το καλύτερο
        ; είναι δικό του (ό,τι νικιόταν από παλιότερο δεν έφτασε ως εδώ).
        ld      a,(al_best)
        ld      hl,al_lb
        cp      (hl)
        ret     z
        ld      a,1                     ; και μετά κατά y
al_ltry:
        ld      (al_ori),a
        ld      hl,0
        ld      (al_cnt),hl             ; και το al_bad
        ld      hl,al_cbk
        ld      (al_cb),hl
        call    al_w4
        ret     c                       ; μακρύτερο από AL_RANGE
        ld      a,(al_bad)
        or      a
        jr      nz,alt_blk
        ld      a,(al_cnt)
        ld      hl,al_best
        cp      (hl)
        ret     nc
        ld      (hl),a
        ld      a,(al_t)
        ld      (al_pt),a
        ld      a,(al_ori)
        ld      (al_po),a
        ret
alt_blk:
        ld      (al_why),a              ; κάτι σε απόσταση, αλλά κομμένο
        ret

; al_gap — HL -> (x0, ., w) του νέου, DE -> του άλλου, στον ίδιο άξονα: A =
; τα tiles ανάμεσά τους, 0 αν επικαλύπτονται. Μετά το al_scan οι αρχές απέχουν
; ως 24 tiles και η αφαίρεση δεν ξεχειλίζει. Κρατά BC, DE, HL.
al_gap:
        call    alg_one                 ; δεξιά του νέου;
        ret     p
        ex      de,hl
        call    alg_one                 ; αριστερά;
        ex      de,hl
        ret     p
        xor     a
        ret
; alg_one — A = (DE).x0 - (HL).x0 - (HL).w, με το πρόσημο στις σημαίες.
alg_one:
        ld      a,(de)
        sub     (hl)
        inc     hl
        inc     hl
        sub     (hl)
        dec     hl
        dec     hl
        ret

; al_cbk — ένα tile του μονοπατιού στον έλεγχο: μετράει, και θυμάται αν δεν
; πατιέται. CY όταν περάσει τα AL_RANGE. Κρατά BC, DE.
al_cbk:
        call    tile_addr
        ld      a,(hl)
        call    bd_ok
        jr      z,alk_ok
        ld      a,1
        ld      (al_bad),a
alk_ok:
        ld      hl,al_cnt
        inc     (hl)
        ld      a,AL_RANGE
        cp      (hl)
        ret

; al_cbm — το σημάδι του φαντάσματος. al_cbs — η σφραγίδα του FIRE.
al_cbm:
        call    ui_mark
        or      a
        ret
al_cbs:
        call    tile_addr
        ld      a,(hl)
        and     #C0                     ; το decor μένει
        or      W_FOUNDATION + W_OCC_PATH
        ld      (hl),a
        ret
; al_cbb — το πρώτο και το τελευταίο tile ενός σκέλους (al_leg). NC.
al_cbb:
        ld      hl,al_en
        ld      a,(hl)
        inc     (hl)
        or      a                       ; και NC
        jr      nz,alb_l
        ld      (al_ef),bc
alb_l:
        ld      (al_el),bc
        ret

; ---------------------------------------------------------------------------
; al_node — A = κόμβος (θόλος 0-63, 64 + δομή). Το αποτύπωμά του στο al_rx..
; al_rh και το κεντρικό του tile στο al_q. CY αν η θέση είναι άδεια. Γυρίζει
; με την τράπεζα 1.
;
; Θόλος: πλευρά 4 + 2 x μέγεθος. Δομή: το struct_dims, bytes / 4 x γραμμές /
; 16 — το sprite γεμίζει ακριβώς τα tiles της (όπως το msc_near).
; ---------------------------------------------------------------------------
al_node:
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        sub     MAX_DOME
        jr      nc,aln_st
        add     a,MAX_DOME
        call    ob_domeadr              ; HL -> cx
        inc     hl
        inc     hl
        ld      a,(hl)                  ; D_SIZE
        add     a,a
        add     a,4
        ld      d,a
        ld      e,a
        jr      aln_go
aln_st:
        ld      l,a
        ld      h,0
        add     hl,hl
        add     hl,hl
        add     hl,hl
        ld      de,G_struct_tbl + ST_KIND
        add     hl,de
        ld      a,(hl)                  ; ST_KIND
        inc     hl
        add     a,a
        add     a,a
        add     a,(hl)                  ; + ST_SIZE
        dec     hl
        add     a,a                     ; είδος * 8 + μέγεθος * 2
        push    hl
        ld      hl,G_struct_dims
        call    ob_addu
        ld      a,(hl)
        rrca
        rrca
        and     #3F
        ld      e,a                     ; w = bytes / 4
        inc     hl
        ld      a,(hl)
        rrca
        rrca
        rrca
        rrca
        and     #0F
        ld      d,a                     ; h = γραμμές / 16
        pop     hl
aln_go:                                 ; HL -> +2, E = w, D = h
        inc     hl
        inc     hl
        ld      a,(hl)                  ; D_STATE = ST_STATE
        sub     1                       ; CY: άδεια
        jr      c,aln_out
        dec     hl
        dec     hl
        dec     hl
        ld      a,(hl)                  ; cy
        ld      c,a
        sub     d
        sra     a
        ld      (al_ry),a
        dec     hl
        ld      a,(hl)                  ; cx
        ld      b,a
        sub     e
        sra     a
        ld      (al_rx),a
        ld      (al_rw),de              ; και το al_rh
        sra     b
        sra     c
        ld      (al_q),bc               ; al_q = y, al_q + 1 = x
        or      a                       ; NC
aln_out:
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        ret

; ---------------------------------------------------------------------------
; al_walk — το Γ από το P (al_p) στο Q (al_q): (al_ori) 0 = πρώτα κατά x. Για
; κάθε tile έξω από τα δύο αποτυπώματα καλεί την (al_cb) με B = x, C = y·
; αυτή κρατά τα BC, DE, και με CY σταματά τα πάντα. Το P δεν περνιέται: είναι
; μέσα στο νέο αποτύπωμα. Κάθε tile μία φορά — το φάντασμα το θέλει έτσι.
; al_w4 — το ίδιο με την τράπεζα 4 στο παράθυρο.
; ---------------------------------------------------------------------------
; al_lgo — HL = ρουτίνα ανά tile: το μονοπάτι που διαλέχτηκε, με την 4.
al_lgo:
        ld      (al_cb),hl
        ld      a,(al_po)
        ld      (al_ori),a
        ld      a,(al_pt)
        call    al_node
al_w4:
        ld      bc,GA_PORT + PAGE_B4
        out     (c),c
        call    al_walk
        ld      bc,GA_PORT + PAGE_B1    ; οι σημαίες μένουν
        out     (c),c
        ret
al_walk:
        call    al_k
        call    al_seg
        ret     c
        ld      hl,(al_q)
; al_seg — από το (B, C) ως το (H, L), σε έναν άξονα: βήμα, και μετά tile.
al_seg:
        ld      a,h
        sub     b
        call    al_sgn
        ld      d,a
        ld      a,l
        sub     c
        call    al_sgn
        ld      e,a
als_lp:
        ld      a,b
        cp      h
        jr      nz,als_st
        ld      a,c
        cp      l
        ret     z                       ; και NC
als_st:
        ld      a,b
        add     a,d
        ld      b,a
        ld      a,c
        add     a,e
        ld      c,a
        push    hl
        call    al_emit
        pop     hl
        ret     c
        jr      als_lp

; al_sgn — A -> -1, 0 ή 1.
al_sgn:
        or      a
        ret     z
        ld      a,1
        ret     p
        neg
        ret

; al_k — BC = P (B = x, C = y) και HL = η γωνία K του Γ (H = x, L = y).
al_k:
        ld      bc,(al_p)
        ld      hl,(al_q)
        ld      a,(al_ori)
        or      a
        jr      nz,alk_v
        ld      l,c                     ; πρώτα κατά x: K = (qx, py)
        ret
alk_v:
        ld      h,b                     ; πρώτα κατά y: K = (px, qy)
        ret

; al_emit — ένα tile: μέσα σε κάποιο από τα δύο αποτυπώματα δεν μετρά.
al_emit:
        ld      hl,al_nx
        call    al_in
        ccf
        ret     nc
        ld      hl,al_rx
        call    al_in
        ccf
        ret     nc
        ld      hl,(al_cb)
        jp      (hl)

; al_in — HL -> x0, y0, w, h: CY αν το (B, C) είναι μέσα.
al_in:
        ld      a,b
        sub     (hl)
        inc     hl
        inc     hl
        cp      (hl)
        ret     nc
        dec     hl
        ld      a,c
        sub     (hl)
        inc     hl
        inc     hl
        cp      (hl)
        ret

; ---------------------------------------------------------------------------
; al_ghost — οι διάδρομοι ή το μονοπάτι, πράσινα, πάνω στο φάντασμα· και μετά
; ο πίνακας. Από το ui_show, όταν η θέση επιτρέπεται.
; ---------------------------------------------------------------------------
al_ghost:
        ld      a,(al_pt)
        inc     a
        ld      hl,al_cbm
        call    nz,al_lgo
        ld      hl,ui_mark
        call    al_each
        jp      ui_panel


; ---------------------------------------------------------------------------
; al_commit — μετά από ένα bd_commit που πέτυχε: οι διάδρομοι ή το μονοπάτι
; που έδειξε το φάντασμα. Οι διάδρομοι μπαίνουν με το cr_commit (σφραγίδα,
; πληρωμή με την τιμή του καταλόγου ανά πλακίδιο, ακμή) και ζωγραφίζονται με
; το cr_redraw· το μονοπάτι γίνεται θεμέλιο, ακμή, και ζωγραφίζεται εδώ.
; ---------------------------------------------------------------------------
al_commit:
        ld      a,(al_pt)
        inc     a
        jr      z,alc_cor
        ld      hl,al_cbs
        call    al_lgo
        ld      a,(bd_node)
        ld      b,a
        ld      a,(al_pt)
        ld      c,a
        call    cr_link_bc
        ; ΜΟΝΟ ΤΑ TILES ΤΟΥ ΜΟΝΟΠΑΤΙΟΥ, σκέλος-σκέλος. Το ορθογώνιο κέντρο-γωνία-
        ; κέντρο έπιανε και κομμάτια των δύο αποτυπωμάτων, και ο ηλιακός
        ; πλήρωνε 68 ms στο FIRE για να ξαναζωγραφίσει τον θόλο απέναντι. Τα
        ; tiles ενός σκέλους είναι στη σειρά, οπότε το πρώτο και το τελευταίο
        ; τους είναι το ορθογώνιό του. Το autotile των γειτόνων δεν αλλάζει:
        ; το μονοπάτι πατά μόνο έδαφος, σκόνη ή θεμέλιο, που δεν μετρούν.
        ld      hl,al_cbb
        ld      (al_cb),hl
        call    al_k
        push    hl
        call    al_leg                  ; P..K
        pop     bc
        ld      hl,(al_q)               ; K..Q
; al_leg — ένα σκέλος από το (B, C) ως το (H, L): τα tiles του που βγαίνουν
; από το al_emit, ξαναζωγραφισμένα, αν βγήκε κανένα.
al_leg:
        xor     a
        ld      (al_en),a
        call    al_seg
        ld      a,(al_en)
        or      a
        ret     z
        ld      bc,(al_ef)
        ld      hl,(al_el)
; al_vr — το ορθογώνιο από το (B, C) ως το (H, L), ξαναζωγραφισμένο.
al_vr:
        ld      a,h
        sub     b
        jp      p,alv_x
        neg
        ld      b,h
alv_x:
        inc     a
        ld      (vr_w),a
        ld      a,b
        ld      (vr_tx),a
        ld      a,l
        sub     c
        jp      p,alv_y
        neg
        ld      c,l
alv_y:
        inc     a
        ld      (vr_h),a
        ld      a,c
        ld      (vr_ty),a
        jp      view_rect
alc_cor:
        ld      hl,(bd_metal)
        push    hl
        ld      hl,CORR_B * 256 + CORR_M
        ld      (bd_metal),hl
        ld      a,(al_n)
        or      a
        jr      z,alc_out
        ld      b,a
        ld      hl,al_lst
alc_lp:
        push    bc
        push    hl
        ld      a,(hl)
        call    al_set
        call    cr_commit               ; A = 0: μπήκε
        or      a
        call    z,cr_redraw
        pop     hl
        pop     bc
        inc     hl
        djnz    alc_lp
alc_out:
        pop     hl
        ld      (bd_metal),hl
        ret

; --- η κατάσταση -------------------------------------------------------------
al_n:       db 0                ; πόσοι διάδρομοι
al_len:     db 0                ; τα πλακίδιά τους, όλων μαζί
al_pt:      db 255              ; το μονοπάτι: ο κόμβος στην άκρη, 255 = κανένα
al_po:      db 0                ; και το σχήμα του (al_ori)
al_lst:     defs AL_MAX         ; οι θόλοι των διαδρόμων
al_nx:      db 0                ; το νέο: x0, y0, w, h σε tiles
al_ny:      db 0
al_nw:      db 0
al_nh:      db 0
al_rx:      db 0                ; το άλλο άκρο
al_ry:      db 0
al_rw:      db 0
al_rh:      db 0
al_p:       dw 0                ; τα κεντρικά tiles: y, x
al_q:       dw 0
al_ori:     db 0
al_cnt:     db 0
al_bad:     db 0
al_best:    db 0
al_t:       db 0
al_any:     db 0
al_why:     db 0
al_cb:      dw 0
al_en:      db 0                ; al_leg: πόσα tiles, το πρώτο, το τελευταίο
al_ef:      dw 0
al_el:      dw 0
al_ecb:     dw 0
al_fn:      dw 0
al_lb:      db 0

        ; (το cr_fy == cr_fx + 1, το bd_biop == bd_metal + 1 και το cur_hy ==
        ; cur_hx + 1 τα ελέγχουν τα route.asm, build.asm και ui.asm· στο
        ; tests/uitest.asm θα ήταν εδώ μπροστινές ετικέτες)
        assert  al_len == al_n + 1 && al_pt == al_n + 2
        assert  al_bad == al_cnt + 1 && al_nh == al_nw + 1 && al_rh == al_rw + 1
        assert  D_STATE == 4 && ST_STATE == 4 && ST_KIND == 2 && ST_SIZE == 3
        assert  D_SIZE == 2 && D_CX == 0 && D_CY == 1
