; blit.asm — οι δύο πυρήνες σχεδίασης, και η παραγωγή τεταρτημορίων
;
; Βλ. assets/SPRITES.md §2 (οι δύο μορφές) και §5 (τα τεταρτημόρια).
;
; ΠΡΟΣΟΧΗ: το `and (de)` του SPRITES.md §2 δεν είναι εντολή του Z80. Η πηγή
; πρέπει να είναι στο HL ώστε να δουλεύουν τα `and (hl)` / `or (hl)`, και η
; οθόνη στο DE:
;
;       ld a,(de) : and (hl) : inc hl : or (hl) : inc hl : ld (de),a : inc de
;
; Αυτό αφήνει το HL δεσμευμένο, γι' αυτό τα καθρεφτισμένα τεταρτημόρια (ne, se)
; γυρίζουν πρώτα τη γραμμή σε buffer (flip_line) και μετά τρέχουν τον ίδιο
; γρήγορο πυρήνα από πάνω του.

; ---------------------------------------------------------------------------
; blit_op — αδιαφανές αντίγραφο W x H.
; In :  HL = πηγή,  DE = οθόνη,  B = W bytes,  C = H γραμμές
; Out:  HL μετά το τελευταίο byte
; ---------------------------------------------------------------------------
blit_op:
        ld      a,b
        ld      (bo_w),a
        ld      a,c
        ld      (bo_h),a
bo_line:
        push    de
        ld      a,(bo_w)
        ld      b,a
        call    blt_op_line
        pop     de
        call    scr_nextline
        ld      a,(bo_h)
        dec     a
        ld      (bo_h),a
        jr      nz,bo_line
        ret

; ---------------------------------------------------------------------------
; blt_op_line / blt_mask_line — ΜΙΑ γραμμή, με το δαχτυλίδι των 2 KB μέσα.
; In :  HL = πηγή, DE = οθόνη, B = πλήθος bytes (1..80)
;
; Η γραμμή σπάει στα δύο μόνο όταν πατάει το σημείο τυλίγματος — μία στις
; χίλιες. Το φθηνό φίλτρο είναι το (d&7)==7: μόνο τότε είναι το p πάνω από το
; #700 και μόνο τότε μπορεί μια γραμμή 80 bytes να περάσει το #800. Τρεις
; εντολές ανά γραμμή, ΟΧΙ ανά byte — ένα `and #C7` σε κάθε `inc de` θα κόστιζε
; 70%. Ο έλεγχος ήταν πρώτα κλήση σε ρουτίνα και φάνηκε αμέσως: η επικάλυψη
; εδάφους (blit_mask, 16 γραμμές ανά tile) πλήρωνε 90 T τη γραμμή για τίποτα.
; ---------------------------------------------------------------------------
blt_op_line:
        ld      c,b
        ld      b,0
        ld      a,d
        and     7
        cp      7
        jr      z,bol_chk
bol_go:
        ldir
        ret
bol_chk:
        ld      a,c
        dec     a
        add     a,e
        jr      nc,bol_go
        ld      a,e
        neg                         ; 256 - e = όσα χωράνε πριν το τύλιγμα
        ld      b,a
        ld      a,c
        sub     b
        ld      c,b
        ld      b,0
        push    af
        ldir
        call    scr_ringtop
        pop     af
        ld      c,a
        ld      b,0
        ldir
        ret

blt_mask_line:
        ld      a,d
        and     7
        cp      7
        jr      z,bml_chk
bml_run:
        ld      a,(de)
        and     (hl)
        inc     hl
        or      (hl)
        inc     hl
        ld      (de),a
        inc     de
        djnz    bml_run
        ret
bml_chk:
        ld      a,b
        dec     a
        add     a,e                 ; το ΤΕΛΕΥΤΑΙΟ byte περνάει το #FF;
        jr      nc,bml_run
        ld      a,e
        neg
        ld      c,a
        ld      a,b
        sub     c
        ld      b,c
        ld      c,a
        call    bml_run             ; ως το τύλιγμα
        ld      b,c
        call    scr_ringtop
        jp      bml_run             ; και το υπόλοιπο, από την αρχή

; ---------------------------------------------------------------------------
; blit_mask — με μάσκα, W x H, χωρίς καθρεφτισμό.
; In :  HL = πηγή (mask,data ανά ζεύγος),  DE = οθόνη,  B = W,  C = H
; ---------------------------------------------------------------------------
blit_mask:
        ld      a,b
        ld      (bq_w),a
        ld      a,c
        ld      (bm_h),a
bm_line:
        push    de
        call    blit_mline
        pop     de
        call    scr_nextline
        ld      a,(bm_h)
        dec     a
        ld      (bm_h),a
        jr      nz,bm_line
        ret

; ---------------------------------------------------------------------------
; blit_mline — μία γραμμή με μάσκα. HL = πηγή, DE = οθόνη, πλάτος από bq_w.
; Χαλάει: A, B, HL, DE
; ---------------------------------------------------------------------------
blit_mline:
        ld      a,(bq_w)
        ld      b,a
        jp      blt_mask_line

; ---------------------------------------------------------------------------
; blit_quad — ΕΝΑ τεταρτημόριο, σε όποιον προσανατολισμό, από το αποθηκευμένο nw.
;
; In :  HL = αρχή του nw
;       DE = οθόνη, πάνω-αριστερά ΑΥΤΟΥ του τεταρτημορίου
;       B  = W (bytes δεδομένων ανά γραμμή),  C = H (γραμμές)
;       A  = Q_NW / Q_NE / Q_SW / Q_SE
;
; bit0 του προσανατολισμού = καθρεφτισμός οριζόντια, bit1 = κάθετα.
; ---------------------------------------------------------------------------
blit_quad:
        ld      (bq_or),a
        ld      a,b
        ld      (bq_w),a
        add     a,a
        ld      (bq_str),a          ; 2W — bytes ανά γραμμή στη μνήμη
        ld      a,c
        ld      (bq_h),a

        ld      a,(bq_or)
        and     2
        jr      z,bq_line           ; nw/ne — η πηγή ξεκινά από πάνω
        ; sw/se — ξεκίνα από την ΤΕΛΕΥΤΑΙΑ γραμμή και προχώρα ανάποδα
        ld      a,(bq_h)
        dec     a
        jr      z,bq_line
        push    de
        ld      b,a                 ; H-1 φορές
        ld      a,(bq_str)
        ld      e,a
        ld      d,0
bq_adv:
        add     hl,de
        djnz    bq_adv
        pop     de

bq_line:
        push    de
        ld      a,(bq_or)
        and     1
        jr      z,bq_plain
        ; ne/se — γύρνα τη γραμμή σε buffer, μετά ίδιος πυρήνας
        call    flip_line
        push    hl
        ld      hl,flipbuf
        call    blit_mline
        pop     hl
        jr      bq_next
bq_plain:
        push    hl
        call    blit_mline
        pop     hl
bq_next:
        pop     de
        call    scr_nextline
        ; πηγή: ±2W
        ld      a,(bq_str)
        ld      c,a
        ld      b,0
        ld      a,(bq_or)
        and     2
        jr      z,bq_down
        ld      a,l                 ; HL -= 2W
        sub     c
        ld      l,a
        ld      a,h
        sbc     a,b
        ld      h,a
        jr      bq_cnt
bq_down:
        add     hl,bc
bq_cnt:
        ld      a,(bq_h)
        dec     a
        ld      (bq_h),a
        jr      nz,bq_line
        ret

; ---------------------------------------------------------------------------
; flip_line — μία γραμμή με ΑΝΑΠΟΔΗ σειρά ΖΕΥΓΩΝ και κάθε byte από το flip_mode0.
;
; Το ζεύγος (mask,data) μένει ενιαίο: αντιστρέφονται τα ζεύγη, όχι τα bytes
; μέσα τους (SPRITES.md §5).
;
; In :  HL = αρχή γραμμής πηγής (δεν αλλάζει), πλάτος από bq_w
; Out:  flipbuf γεμάτο, W ζεύγη
; ---------------------------------------------------------------------------
flip_line:
        push    hl
        push    de                  ; το blit_quad κρατά την οθόνη στο DE
        ld      a,(bq_w)
        dec     a
        add     a,a                 ; (W-1)*2 -> τελευταίο ζεύγος
        ld      e,a
        ld      d,0
        add     hl,de
        ld      a,(bq_w)
        ld      b,a
        call    flip_span
        pop     de
        pop     hl
        ret

; ---------------------------------------------------------------------------
; flip_span — B ζεύγη, ανάποδα, από το HL και κατεβαίνοντας, στο flipbuf.
;
; Ο λόγος που υπάρχει χωριστά από το flip_line: με clip, η γραμμή που τελικά
; γράφεται μπορεί να είναι 4 bytes από τα 16. Το να γυρίζει ολόκληρη η γραμμή
; και να κόβεται μετά κόστιζε στο σκρολάρισμα ΤΕΣΣΕΡΙΣ φορές το σχέδιο.
; ---------------------------------------------------------------------------
flip_span:
        push    hl
        push    de
        ld      de,flipbuf
        ld      ix,FLIPTAB          ; ixh = σελίδα του πίνακα, ixl = δείκτης
fl_pair:
        ld      a,(hl)              ; mask
        ld      ixl,a
        ld      a,(ix+0)
        ld      (de),a
        inc     de
        inc     hl
        ld      a,(hl)              ; data
        ld      ixl,a
        ld      a,(ix+0)
        ld      (de),a
        inc     de
        dec     hl
        dec     hl
        dec     hl                  ; -> mask του προηγούμενου ζεύγους
        djnz    fl_pair
        pop     de
        pop     hl
        ret

; ---------------------------------------------------------------------------
; blit_quads — ολόκληρο πλαίσιο (θόλος ή δακτύλιος) από το ένα αποθηκευμένο nw.
;
;       nw (0,0)        ne (QW,0)
;       sw (0,QH)       se (QW,QH)
;
; Παράμετροι στο μπλοκ qf_* παρακάτω.
; ---------------------------------------------------------------------------
blit_quads:
        xor     a
qf_loop:
        ld      (qf_cur),a
        ; οθόνη: x + (bit0 ? QW : 0),  y + (bit1 ? QH : 0)
        ld      c,a
        and     1
        ld      b,a
        ld      a,(qf_x)
        jr      z,qf_nox
        ld      hl,qf_w
        add     a,(hl)
qf_nox:
        ld      (qf_tx),a
        ld      a,c
        and     2
        ld      a,(qf_y)
        jr      z,qf_noy
        ld      hl,qf_h
        add     a,(hl)
qf_noy:
        ld      c,a                 ; y
        ld      a,(qf_tx)
        ld      b,a                 ; x -> θα το βάλουμε στο C του scr_addr
        ld      a,c
        ld      c,b
        call    scr_addr            ; C = x, A = y  ->  DE
        ld      hl,(qf_src)
        ld      a,(qf_w)
        ld      b,a
        ld      a,(qf_h)
        ld      c,a
        ld      a,(qf_cur)
        call    blit_quad
        ld      a,(qf_cur)
        inc     a
        cp      4
        jr      nz,qf_loop
        ret

; --- μεταβλητές ------------------------------------------------------------
bo_w:       db 0
bo_h:       db 0
bm_h:       db 0
bq_w:       db 0
bq_h:       db 0
bq_str:     db 0
bq_or:      db 0
qf_cur:     db 0
qf_tx:      db 0

; παράμετροι του blit_quads
qf_src:     dw 0            ; αρχή του nw
qf_x:       db 0            ; x σε bytes, πάνω-αριστερά του ΠΛΑΙΣΙΟΥ
qf_y:       db 0            ; y σε γραμμές
qf_w:       db 0            ; W τεταρτημορίου σε bytes δεδομένων
qf_h:       db 0            ; H τεταρτημορίου σε γραμμές

; buffer για μια καθρεφτισμένη γραμμή· η μεγαλύτερη είναι DOME_L_W*2 = 32
; Το flipbuf χωράει ΑΚΡΙΒΩΣ το πλατύτερο τεταρτημόριο: 16 bytes δεδομένων =
; 16 ζεύγη = 32 bytes. Δεν υπάρχει περιθώριο, και όταν το bq_w έγινε 185 από
; λάθος βήμα πίνακα, το flip_line έγραψε 370 bytes μέσα στον κώδικα του
; tiles.asm. Οποιος το μεγαλώσει, ας το μεγαλώσει επίτηδες.
flipbuf:    defs 32
