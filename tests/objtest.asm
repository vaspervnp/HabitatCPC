; objtest.asm — το πέρασμα αντικειμένων σε πραγματικό Z80.
;
; Η αποικία έρχεται ΜΕΣΑ στην εικόνα της τράπεζας 6 (tools/mkcolony.py): η
; περιοχή #C000 που χρησιμοποιούσε το simtest για staging είναι εδώ η οθόνη.
;
; Το harness βάζει την κάμερα ΜΕΤΑ το quickload και ξαναξεκινά από το start,
; ώστε ένα snapshot να δοκιμάζει πολλές θέσεις — και κυρίως θέσεις όπου το
; τύλιγμα του δαχτυλιδιού πέφτει μέσα στην εικόνα.

REPS        equ 1

        buildsna
        bankset 0
        org     #0100
        run     start

        include "../src/const.asm"
        include "../build/sprite_consts.asm"
        include "../build/layout.asm"

FLIPTAB     equ G_flip_mode0

start:
        di
        ld      sp,#0100
        call    hw_mode0
        ld      hl,G_palette_fw
        call    pal_set
        xor     a
        call    pal_border
        call    ob_clip_full
        ld      a,REPS
        ld      (rep_n),a
rep_loop:
        call    view_draw
        ld      a,(rep_n)
        dec     a
        ld      (rep_n),a
        jr      nz,rep_loop
        ld      a,#5A
        ld      (done_flag),a
hang:   jr      hang

; --- δεύτερη είσοδος: μόνο το πέρασμα αντικειμένων, για μέτρηση κόστους ---
obj_only:
        ld      a,(rep_n)
        ld      (oo_n),a
oo_loop:
        call    ob_draw_all
        ld      a,(oo_n)
        dec     a
        ld      (oo_n),a
        jr      nz,oo_loop
        ld      a,#5A
        ld      (done_flag),a
oo_hang: jr     oo_hang

rep_n:      db 0
oo_n:       db 0
done_flag:  db 0

        include "../src/screen.asm"
        include "../src/blit.asm"
        include "../src/tiles.asm"
        include "../src/object.asm"
        include "../src/view.asm"
        include "../src/hw.asm"

        org     #8000
        incbin  "../build/page2.bin"

        bankset 1
        org     #0000                   ; τράπεζα 4 — το επίπεδο κόσμου
        incbin  "../build/world_col.bin"
        org     #8000                   ; τράπεζα 6 — τεταρτημόρια ΚΑΙ πίνακες
        incbin  "../build/bank6_col.bin"
        org     #C000                   ; τράπεζα 7
        incbin  "../build/bank7.bin"
