; blit.asm — οι πυρήνες σχεδίασης
;
; Βλ. assets/SPRITES.md §2 (οι δύο μορφές) και §5 (τα τεταρτημόρια).
;
; ΠΡΟΣΟΧΗ: το `and (de)` του SPRITES.md §2 δεν είναι εντολή του Z80. Η πηγή
; πρέπει να είναι στο HL ώστε να δουλεύουν τα `and (hl)` / `or (hl)`, και η
; οθόνη στο DE:
;
;       ld a,(de) : and (hl) : inc hl : or (hl) : inc hl : ld (de),a : inc de
;
; Τα καθρεφτισμένα τεταρτημόρια (ne, se) δεν περνούν από buffer από το βήμα 35:
; το blt_mask_flip έχει την πηγή στο IX και τον πίνακα στο HL.

; ---------------------------------------------------------------------------
; blt_op_line / blt_mask_line / blt_mask_flip — ΜΙΑ γραμμή, με το δαχτυλίδι
; των 2 KB μέσα.
; In :  HL = πηγή, DE = οθόνη, B = πλήθος bytes (1..80)
;
; Η γραμμή σπάει στα δύο μόνο όταν πατάει το σημείο τυλίγματος — μία στις
; χίλιες. Το φθηνό φίλτρο είναι το (d&7)==7: μόνο τότε είναι το p πάνω από το
; #700 και μόνο τότε μπορεί μια γραμμή 80 bytes να περάσει το #800. Τρεις
; εντολές ανά γραμμή, ΟΧΙ ανά byte — ένα `and #C7` σε κάθε `inc de` θα κόστιζε
; 70%. Ο έλεγχος ήταν πρώτα κλήση σε ρουτίνα και φάνηκε αμέσως: η επικάλυψη
; εδάφους (blit_mask, 16 γραμμές ανά tile) πλήρωνε 90 T τη γραμμή για τίποτα.
; Το σπάσιμο το κάνει ΕΝΑ bl_wrap για τους τρεις, με τον πυρήνα στο IY (το
; παιχνίδι δεν χρησιμοποιεί αλλού το IY· η γεννήτρια τρέχει πριν).
; ---------------------------------------------------------------------------
blt_op_line:
        ld      a,d
        or      #F8
        inc     a                   ; Z: (d & 7) == 7
        jr      z,bol_chk
bol_run:
        ld      c,b
        ld      b,0
        ldir
        ret
bol_chk:
        ld      a,b
        dec     a
        add     a,e                 ; το ΤΕΛΕΥΤΑΙΟ byte περνάει το #FF;
        jr      nc,bol_run
        ld      iy,bol_run
        jr      bl_wrap

blt_mask_line:
        ld      a,d
        or      #F8
        inc     a
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
        add     a,e
        jr      nc,bml_run
        ld      iy,bml_run
        ; και συνεχίζει στο bl_wrap

; ---------------------------------------------------------------------------
; bl_wrap — η γραμμή περνά το #7FF: ο πυρήνας του IY ως το τύλιγμα, το DE πίσω
; στην αρχή του δαχτυλιδιού, και ο ίδιος πυρήνας για τα υπόλοιπα.
; In :  A = πλήθος - 1 + E - 256 (ό,τι άφησε ο έλεγχος) = υπόλοιπο - 1.
;       Το E δεν είναι 0 εδώ: μια γραμμή ως 80 bytes από το 0 δεν τυλίγει.
; Ο πυρήνας κρατά τα HL/IX και το DE συνεχίζει από εκεί που σταμάτησε: μετά
; το πρώτο κομμάτι είναι (d+1):00, οπότε φτάνει το d - 8. Το υπόλοιπο
; περιμένει στο AF' — το παιχνίδι δεν το αγγίζει πουθενά αλλού, και οι
; διακοπές είναι πάντα κλειστές. Το C δεν γίνεται: το θέλουν δύο πυρήνες.
; ---------------------------------------------------------------------------
bl_wrap:
        inc     a
        ex      af,af'              ; το υπόλοιπο
        xor     a
        sub     e                   ; 256 - E: όσα χωράνε ως το τύλιγμα
        ld      b,a
        call    blw_k
        ld      a,d
        sub     8
        ld      d,a
        ex      af,af'
        ld      b,a
blw_k:  jp      (iy)

; ---------------------------------------------------------------------------
; blt_mask_flip — μία γραμμή με μάσκα, ΚΑΘΡΕΦΤΙΣΜΕΝΗ, σε ένα πέρασμα.
; In :  HL = το πρώτο ζεύγος (mask, data) που γράφεται· η πηγή διαβάζεται
;       ΠΡΟΣ ΤΑ ΠΙΣΩ, ένα ζεύγος ανά byte οθόνης.  DE = οθόνη,  B = bytes.
; Χαλάει: A, BC, HL, IX (και IY, AF' στο τύλιγμα).  Απαιτεί: τράπεζα 6 (FLIPTAB).
;
; ΤΟ ΑΚΡΙΒΟ ΚΟΜΜΑΤΙ ΚΑΘΕ ΘΟΛΟΥ. Τα τρία από τα τέσσερα τεταρτημόρια είναι
; καθρεφτισμένα από το ένα nw (§4.4), και τα δύο από αυτά γυρίζουν οριζόντια —
; δηλαδή τα μισά bytes κάθε θόλου περνούσαν από το flip_span (40 us το byte:
; ο πίνακας με ixl και (ix+0)) σε buffer, και ύστερα από το blt_mask_line
; (18 us) στην οθόνη. Εδώ ο πίνακας είναι στο HL, όπου η αναζήτηση είναι
; `ld l,(ix+n) / ld a,(hl)`, και η πηγή στο IX: 32 us το byte, χωρίς buffer.
; Μετρημένο στο βήμα 35: μία σειρά ενός θόλου L πλήρωνε 19 ms μόνο στο
; flip_span.
; ---------------------------------------------------------------------------
blt_mask_flip:
        push    hl
        pop     ix
        ld      h,FLIPTAB / 256     ; ο πίνακας είναι σε όριο σελίδας
        ld      a,d
        or      #F8
        inc     a
        jr      z,bmf_chk
bmf_run:
        ld      l,(ix+0)            ; μάσκα
        ld      a,(de)
        and     (hl)
        ld      c,a
        ld      l,(ix+1)            ; χρώμα
        ld      a,(hl)
        or      c
        ld      (de),a
        inc     de
        dec     ix
        dec     ix                  ; το προηγούμενο ζεύγος
        djnz    bmf_run
        ret
bmf_chk:
        ld      a,b
        dec     a
        add     a,e
        jr      nc,bmf_run
        ld      iy,bmf_run
        jr      bl_wrap

; ---------------------------------------------------------------------------
; blit_mask — με μάσκα, W x H, χωρίς καθρεφτισμό. Το περίγραμμα του
; μεταλλεύματος (tiles.asm).
; In :  HL = πηγή (mask,data ανά ζεύγος),  DE = οθόνη,  B = W,  C = H
; ---------------------------------------------------------------------------
blit_mask:
        push    bc
        push    de
        call    blt_mask_line
        pop     de
        call    scr_nextline
        pop     bc
        dec     c
        jr      nz,blit_mask
        ret

; ---------------------------------------------------------------------------
; ΟΙ ΠΥΡΗΝΕΣ ΤΟΥ ΟΡΟΣΗΜΟΥ 2, ΜΟΝΟ ΓΙΑ ΤΙΣ ΔΟΚΙΜΕΣ ΤΟΥΣ. Το blit_quad(s) ήταν η
; πρώτη απόδειξη του κόστους του §2.2 και το παιχνίδι ζωγραφίζει θόλους με το
; ob_blit του object.asm· από το βήμα 35 και το flip_span έμεινε χωρίς
; καλούντα στο παιχνίδι (το blt_mask_flip καθρεφτίζει χωρίς buffer), και από
; το βήμα 66 το blit_op (τα tiles έχουν το δικό τους blit_tile). Τα
; tests/blittest.asm και tests/packtest.asm τα θέλουν ακόμη, και ορίζουν
; HAS_QUADS· το παιχνίδι γλιτώνει 290 bytes της τράπεζας 0.
; ---------------------------------------------------------------------------
        ifdef HAS_QUADS
; ---------------------------------------------------------------------------
; blit_op — αδιαφανές αντίγραφο W x H.
; In :  HL = πηγή,  DE = οθόνη,  B = W bytes,  C = H γραμμές
; Out:  HL μετά το τελευταίο byte
; ---------------------------------------------------------------------------
blit_op:
        push    bc
        push    de
        call    blt_op_line
        pop     de
        call    scr_nextline
        pop     bc
        dec     c
        jr      nz,blit_op
        ret

; blit_mline — μία γραμμή με μάσκα. HL = πηγή, DE = οθόνη, πλάτος από bq_w.
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

        endif

; --- μεταβλητές ------------------------------------------------------------
        ifdef HAS_QUADS
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
        endif
