; inputtest.asm — πληκτρολόγιο και χειριστήριο σε πραγματικό υλικό.
;
; Ενας βρόχος συγχρονισμένος στο VSync που διαβάζει μία φορά ανά frame και
; μετράει ΑΚΜΕΣ ανά ενέργεια. Το harness πατάει πλήκτρα και ελέγχει δύο
; πράγματα: ότι η σωστή ενέργεια ανάβει, και ότι ένα κράτημα δέκα frames
; μετράει ΜΙΑ φορά.

        buildsna
        bankset 0
        org     #0100
        run     start

        include "../src/const.asm"
        include "../src/input.asm"


start:
        di
        ld      sp,#0100
        ld      hl,hit_n
        ld      de,hit_n+1
        ld      bc,A_ACTIONS-1
        ld      (hl),0
        ldir
        xor     a
        ld      (act_now),a
        ld      (act_now+1),a
loop:
        ld      bc,PPI_B
vs_low:
        in      a,(c)
        rra
        jr      c,vs_low
vs_high:
        in      a,(c)
        rra
        jr      nc,vs_high
        call    in_read
        ld      b,A_ACTIONS
        ld      c,0
cnt_lp:
        push    bc
        ld      a,c
        call    in_hit
        or      a
        jr      z,cnt_no
        pop     bc
        push    bc
        ld      l,c
        ld      h,0
        ld      de,hit_n
        add     hl,de
        inc     (hl)
cnt_no:
        pop     bc
        inc     c
        djnz    cnt_lp
        jr      loop

hit_n:      defs A_ACTIONS
