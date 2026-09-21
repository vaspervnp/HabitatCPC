; screen.asm — αριθμητική διευθύνσεων οθόνης
;
; Διάταξη CPC:  addr = SCR_BASE + (y&7)*#800 + (y>>3)*SCR_W + x
; Το +#800 ανά γραμμή σημαίνει H += 8, που είναι φθηνό· μόνο το πέρασμα σε νέα
; σειρά χαρακτήρων κοστίζει.

; ---------------------------------------------------------------------------
; scr_nextline — DE στην επόμενη γραμμή οθόνης.
; Χαλάει: A, F.  Διατηρεί: BC, HL, IX, IY.
;
; d += 8· αν ξεχειλίσει, ήμασταν στη γραμμή 7 της σειράς, οπότε η επόμενη
; γραμμή είναι -#3800 +#50 από εδώ. Το κρατάμε σε δύο βήματα ώστε το κρατούμενο
; του e να μπει στο d.
; ---------------------------------------------------------------------------
scr_nextline:
        ld      a,d
        add     a,8
        ld      d,a
        ret     nc                  ; ίδια σειρά χαρακτήρων — τελειώσαμε
        ld      a,e
        add     a,SCR_W
        ld      e,a
        ld      a,d                 ; το ld δεν πειράζει τα flags
        adc     a,#C0
        ld      d,a
        ret

; ---------------------------------------------------------------------------
; scr_addr — διεύθυνση οθόνης για (x, y).
; In :  C = x σε bytes (0..79),  A = y σε γραμμές (0..199)
; Out:  DE = διεύθυνση
; Χαλάει: A, F, HL
; ---------------------------------------------------------------------------
scr_addr:
        push    bc
        push    af
        rrca
        rrca
        rrca
        and     #1F                 ; r = y >> 3   (0..24)
        ld      l,a
        ld      h,0
        add     hl,hl               ; *2, πίνακας λέξεων
        ld      de,scr_rowtab
        add     hl,de
        ld      e,(hl)
        inc     hl
        ld      d,(hl)              ; DE = r * SCR_W
        ld      a,c
        add     a,e
        ld      e,a
        ld      a,0
        adc     a,d
        ld      d,a                 ; DE = r*SCR_W + x   (<= #07CF)
        pop     af
        and     7
        add     a,a
        add     a,a
        add     a,a                 ; (y&7) * 8  -> ψηλό byte
        add     a,d
        add     a,#C0
        ld      d,a
        pop     bc
        ret

; r * SCR_W για r = 0..24
scr_rowtab:
        dw      0*SCR_W, 1*SCR_W, 2*SCR_W, 3*SCR_W, 4*SCR_W
        dw      5*SCR_W, 6*SCR_W, 7*SCR_W, 8*SCR_W, 9*SCR_W
        dw     10*SCR_W,11*SCR_W,12*SCR_W,13*SCR_W,14*SCR_W
        dw     15*SCR_W,16*SCR_W,17*SCR_W,18*SCR_W,19*SCR_W
        dw     20*SCR_W,21*SCR_W,22*SCR_W,23*SCR_W,24*SCR_W
