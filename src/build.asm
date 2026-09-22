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
        ld      (bd_item),a
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
        ; --- ισοτιμία ---
        ld      a,(cur_hx)
        ld      hl,bd_w
        xor     (hl)
        and     1
        jr      z,bds_y
        ld      hl,cur_hx
        inc     (hl)
bds_y:
        ld      a,(cur_hy)
        ld      hl,bd_h
        xor     (hl)
        and     1
        jr      z,bds_done
        ld      hl,cur_hy
        inc     (hl)
bds_done:
        ; Το μέγεθος μιας δομής βγαίνει από το είδος: τα τέσσερα ενεργειακά
        ; υπάρχουν σε τρία μεγέθη και ο κατάλογος δίνει το μεγάλο· ορυχείο,
        ; αεροθάλαμος και πλατφόρμα υπάρχουν μόνο στη θέση 0 του struct_dims.
        ld      a,(bd_param)
        cp      K_MINE
        ld      a,2
        jr      c,bds_sz
        xor     a
bds_sz:
        ld      (bd_size),a
        ret

; ---------------------------------------------------------------------------
; bd_rect — πάνω-αριστερά tile του αποτυπώματος, από το κέντρο του κέρσορα.
;       left_tile = (cur_hx - W) / 2      (ακριβές: ίδια ισοτιμία)
; Out: (bd_tx), (bd_ty) προσημασμένα· CY αν βγαίνει έξω από τον κόσμο.
; ---------------------------------------------------------------------------
bd_rect:
        ld      a,(cur_hx)
        call    ob_sext
        ld      a,(bd_w)
        ld      e,a
        ld      d,0
        or      a
        sbc     hl,de
        sra     h
        rr      l                       ; (cx - W) / 2, ακριβές: ίδια ισοτιμία
        ld      a,l
        ld      (bd_tx),a
        ld      a,(bd_w)
        call    bd_range
        ret     c
        ld      a,(cur_hy)
        call    ob_sext
        ld      a,(bd_h)
        ld      e,a
        ld      d,0
        or      a
        sbc     hl,de
        sra     h
        rr      l
        ld      a,l
        ld      (bd_ty),a
        ld      a,(bd_h)
        jp      bd_range

; bd_range — HL = άκρη σε tiles (προσημασμένο), A = μήκος.
; CY αν το [άκρη, άκρη+μήκος) δεν χωράει στο -64..+63.
bd_range:
        ld      e,a
        ld      d,0
        push    hl
        add     hl,de
        ld      de,64
        or      a
        sbc     hl,de                   ; τέλος - 64
        pop     hl
        jr      z,br_lo
        jp      p,br_bad
br_lo:
        push    hl
        ld      de,#FFC0                ; -64
        or      a
        sbc     hl,de                   ; άκρη + 64
        pop     hl
        jp      m,br_bad
        or      a
        ret
br_bad:
        scf
        ret

; ---------------------------------------------------------------------------
; bd_check — κάθε tile του αποτυπώματος. Απαιτεί ΤΡΑΠΕΖΑ 4.
;
; Το §6.9 λέει: έδαφος, σκόνη ή θεμέλιο, και η κατοχή ελεύθερη. Τα κακά tiles
; σημειώνονται στο bd_bad (ένα byte ανά σειρά, ένα bit ανά στήλη) ώστε το
; φάντασμα να δείξει ΠΟΙΟ φταίει και όχι μόνο ότι κάτι φταίει.
; Out: A = πλήθος κακών tiles (0 = επιτρέπεται).
; ---------------------------------------------------------------------------
bd_check:
        ld      hl,bd_bad
        ld      de,bd_bad+1
        ld      bc,7
        ld      (hl),0
        ldir
        xor     a
        ld      (bd_nbad),a
        call    bd_rect
        jr      nc,bdc_in
        ld      a,255                   ; έξω από τον κόσμο: όλα άκυρα
        ld      (bd_nbad),a
        ret
bdc_in:
        ld      a,(bd_ty)
        ld      (bd_cy),a
        xor     a
        ld      (bd_row),a
bdc_rl:
        ld      a,(bd_tx)
        ld      b,a
        ld      a,(bd_cy)
        ld      c,a
        call    tile_addr
        ld      a,(bd_w)
        ld      b,a
        ld      d,1                     ; η μάσκα της στήλης
        ld      e,0                     ; τα κακά tiles της σειράς
bdc_cl:
        ld      a,(hl)
        push    hl
        push    bc
        push    de
        call    bd_ok
        pop     de
        pop     bc
        pop     hl
        jr      z,bdc_good
        ld      a,e
        or      d
        ld      e,a
        push    hl
        ld      hl,bd_nbad
        inc     (hl)
        pop     hl
bdc_good:
        sla     d
        inc     hl
        djnz    bdc_cl
        ld      a,(bd_row)
        ld      l,a
        ld      h,0
        ld      bc,bd_bad
        add     hl,bc
        ld      (hl),e
        ld      a,(bd_cy)
        inc     a
        ld      (bd_cy),a
        ld      a,(bd_row)
        inc     a
        ld      (bd_row),a
        ld      hl,bd_h
        cp      (hl)
        jr      nz,bdc_rl
        ld      a,(bd_nbad)
        ret

; bd_ok — A = world byte. Z αν το tile επιτρέπεται.
bd_ok:
        push    bc
        ld      c,a
        and     W_OCC_MASK
        jr      nz,bok_no
        ld      a,c
        and     7
        cp      W_FOUNDATION
        jr      z,bok_yes
        cp      W_DUST
        jr      z,bok_yes
        or      a
        jr      z,bok_yes
bok_no:
        pop     bc
        ld      a,1
        or      a
        ret
bok_yes:
        pop     bc
        xor     a
        ret

; ---------------------------------------------------------------------------
; bd_afford — έχει η αποικία τα υλικά; Z αν ναι.
; ---------------------------------------------------------------------------
bd_afford:
        ld      hl,(EC_STOCK + S_METAL*2)
        ld      a,(bd_metal)
        ld      e,a
        ld      d,0
        or      a
        sbc     hl,de
        jr      c,bda_no
        ld      hl,(EC_STOCK + S_BIOPL*2)
        ld      a,(bd_biop)
        ld      e,a
        ld      d,0
        or      a
        sbc     hl,de
        jr      c,bda_no
        xor     a
        ret
bda_no:
        or      a
        ld      a,1
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
        ld      a,(bd_kind)
        cp      BK_STRUCT
        jr      z,bdk_struct
        ; --- θόλος ---
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        ld      b,MAX_DOME
        ld      c,0
bdk_find:
        ld      a,c
        call    ob_dome_live
        jr      z,bdk_got
        inc     c
        djnz    bdk_find
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        ld      a,255
        ret
bdk_got:
        ld      a,c
        ld      (bd_node),a
        call    ob_domeadr
        ld      a,(cur_hx)
        ld      (hl),a
        inc     hl
        ld      a,(cur_hy)
        ld      (hl),a
        inc     hl
        ld      a,(bd_param)
        ld      (hl),a                  ; μέγεθος
        inc     hl
        ld      (hl),0                  ; δωμάτιο: κενό ως την επιλογή
        inc     hl
        ld      (hl),DS_BUILDING
        inc     hl
        ld      (hl),0                  ; ακεραιότητα 0 — δεν χτίστηκε ακόμη
        inc     hl
        ld      (hl),0
        inc     hl
        ld      (hl),0                  ; χειριστές
        inc     hl
        ld      b,8
bdk_m:
        ld      (hl),NO_MACH
        inc     hl
        djnz    bdk_m
        ld      b,8
bdk_h:
        ld      (hl),0
        inc     hl
        djnz    bdk_h
        jr      bdk_done
bdk_struct:
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        ld      hl,G_struct_tbl + ST_STATE
        ld      b,MAX_STRUCT
        ld      c,0
bds_find:
        ld      a,(hl)
        or      a
        jr      z,bds_got
        ld      de,STRUCT_REC
        add     hl,de
        inc     c
        djnz    bds_find
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        ld      a,255
        ret
bds_got:
        ld      a,c
        add     a,MAX_DOME              ; κόμβος = 64 + δομή
        ld      (bd_node),a
        ld      a,c
        ld      l,a
        ld      h,0
        add     hl,hl
        add     hl,hl
        add     hl,hl
        ld      de,G_struct_tbl
        add     hl,de
        ld      a,(cur_hx)
        ld      (hl),a
        inc     hl
        ld      a,(cur_hy)
        ld      (hl),a
        inc     hl
        ld      a,(bd_param)
        ld      (hl),a                  ; είδος
        inc     hl
        ld      a,(bd_size)
        ld      (hl),a
        inc     hl
        ld      (hl),DS_BUILDING
        inc     hl
        ld      (hl),0
        inc     hl
        ld      (hl),0
bdk_done:
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        call    bd_stock_pay            ; πληρώνει ΑΦΟΥ βρεθεί θέση
        call    bd_stamp
        call    bd_postjob
        call    ob_touch
        ld      a,(bd_node)
        ret

; bd_stamp — τα tiles γίνονται θεμέλιο και δεσμευμένα (§6.9 βήμα 2).
bd_stamp:
        ld      bc,GA_PORT + PAGE_B4
        out     (c),c
        ld      a,(bd_ty)
        ld      (bd_cy),a
        ld      a,(bd_h)
        ld      (bd_row),a
bst_rl:
        ld      a,(bd_tx)
        ld      b,a
        ld      a,(bd_cy)
        ld      c,a
        call    tile_addr
        ld      a,(bd_w)
        ld      b,a
bst_cl:
        ld      a,(hl)
        and     #C0                     ; το decor μένει
        or      W_FOUNDATION + W_OCC_STRUCT
        ld      (hl),a
        inc     hl
        djnz    bst_cl
        ld      a,(bd_cy)
        inc     a
        ld      (bd_cy),a
        ld      a,(bd_row)
        dec     a
        ld      (bd_row),a
        jr      nz,bst_rl
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        ret

; bd_stock_pay — αφαιρεί το κόστος.
bd_stock_pay:
        ld      hl,(EC_STOCK + S_METAL*2)
        ld      a,(bd_metal)
        ld      e,a
        ld      d,0
        or      a
        sbc     hl,de
        ld      (EC_STOCK + S_METAL*2),hl
        ld      hl,(EC_STOCK + S_BIOPL*2)
        ld      a,(bd_biop)
        ld      e,a
        ld      d,0
        or      a
        sbc     hl,de
        ld      (EC_STOCK + S_BIOPL*2),hl
        ret

; ---------------------------------------------------------------------------
; bd_postjob — εργασία Build στον νέο κόμβο.
;
; Με αυτό, το ΠΡΩΤΟ είδος εργασίας που δέχονται τα ρομπότ αποκτά πηγή: ως τώρα
; κανείς δεν δημοσίευε Haul, Drill ή Build, και το ορόσημο «αυτοματισμός» του
; §10.2 ήταν απρόσιτο εξ ορισμού.
; ---------------------------------------------------------------------------
bd_postjob:
        ld      hl,G_job_tbl
        ld      b,MAX_JOB
bpj_lp:
        ld      a,(hl)
        cp      NO_JOB
        jr      z,bpj_got
        ld      de,JOB_REC
        add     hl,de
        djnz    bpj_lp
        ret
bpj_got:
        ld      (hl),J_BUILD
        inc     hl
        ld      a,(bd_node)
        ld      (hl),a
        inc     hl
        ld      (hl),255                ; αδιάθετη
        inc     hl
        ld      (hl),5                  ; προτεραιότητα, από το job_prio
        inc     hl
        ld      (hl),0
        ret

; --- ο κατάλογος -----------------------------------------------------------
; είδος, παράμετρος, W tiles, H tiles, μέταλλο, βιοπλαστικό, όνομα
;
; Τα κόστη είναι ΠΡΩΤΕΣ ΕΚΤΙΜΗΣΕΙΣ, όπως κάθε αριθμός του §6.5 πριν παιχτεί.
bld_items:
        db BK_DOME,  0, 4,4, 20,10
        dw t_dome_s
        db BK_DOME,  1, 6,6, 40,20
        dw t_dome_m
        db BK_DOME,  2, 8,8, 70,35
        dw t_dome_l
        db BK_LINK,  0, 1,1,  6, 3
        dw t_corr
        db BK_STRUCT,K_SOLAR,   3,3, 15, 8
        dw t_solar
        db BK_STRUCT,K_TURBINE, 3,3, 18, 6
        dw t_turb
        db BK_STRUCT,K_COLLECT, 3,3, 14,10
        dw t_coll
        db BK_STRUCT,K_EXTRACT, 3,3, 22, 8
        dw t_extr
        db BK_STRUCT,K_MINE,    4,4, 30,12
        dw t_mine
        db BK_STRUCT,K_AIRLOCK, 2,2, 10, 6
        dw t_lock
        db BK_STRUCT,K_PAD,     4,4, 45,20
        dw t_pad

t_dome_s:   db "DOME S   ",0
t_dome_m:   db "DOME M   ",0
t_dome_l:   db "DOME L   ",0
t_corr:     db "CORRIDOR ",0
t_solar:    db "SOLAR    ",0
t_turb:     db "TURBINE  ",0
t_coll:     db "COLLECTOR",0
t_extr:     db "EXTRACTOR",0
t_mine:     db "MINE     ",0
t_lock:     db "AIRLOCK  ",0
t_pad:      db "LANDING  ",0

; --- η τρέχουσα επιλογή, αντιγραμμένη από τον κατάλογο ---------------------
bd_item:    db 0
bd_kind:    db 0
bd_param:   db 0
bd_w:       db 0
bd_h:       db 0
bd_metal:   db 0
bd_biop:    db 0
bd_name:    dw 0
bd_size:    db 2                ; μέγεθος δομής· οι δομές του καταλόγου είναι l
bd_tx:      db 0
bd_ty:      db 0
bd_cy:      db 0
bd_row:     db 0
bd_span:    db 0
bd_nbad:    db 0
bd_node:    db 255
bd_bad:     defs 8
