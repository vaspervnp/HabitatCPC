; tiletest.asm — το πέρασμα εδάφους σε πραγματικό υλικό.
;
; Το κάδρο 20x10 από το επίπεδο κόσμου της τράπεζας 4, με autotiling που
; υπολογίζεται τη στιγμή της σχεδίασης από τους τέσσερις γείτονες.
;
; Η κάμερα διαβάζεται από τη RAM (cam_tx / cam_ty), ώστε το harness να τη
; βάζει ΜΕΤΑ το quickload και να δοκιμάζει πολλές θέσεις με ένα snapshot —
; και κυρίως τη γωνία του κόσμου, όπου οι γείτονες βγαίνουν εκτός.
;
; REPS: το πέρασμα τρέχει τόσες φορές ώστε η μέτρηση σε frames να έχει
; ανάλυση. Η εικόνα βγαίνει ίδια όσες φορές κι αν τρέξει.

REPS        equ 10

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

        ; Η τράπεζα 4 μένει σελιδοποιημένη σε όλο το πέρασμα. Τα γραφικά
        ; εδάφους και οι πίνακες είναι στη σελίδα 2, που δεν φεύγει ποτέ.
        ld      bc,GA_PORT + PAGE_B4
        out     (c),c

        ld      a,REPS
        ld      (rep_n),a
rep_loop:
        call    tile_draw_all
        ld      a,(rep_n)
        dec     a
        ld      (rep_n),a
        jr      nz,rep_loop

        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        ld      a,#5A
        ld      (done_flag),a
hang:   jr      hang

rep_n:      db 0
done_flag:  db 0

        include "../src/screen.asm"
        include "../src/blit.asm"
        include "../src/tiles.asm"
        include "../src/hw.asm"

; --- σελίδα 2: αρένες (γραφικά εδάφους, tile_ptr, tile_variants, ore) ---
        org     #8000
        incbin  "../build/page2.bin"

; --- τράπεζες 4-7 ---
        bankset 1
        org     #0000                   ; πρώτο μπλοκ του bankset 1 = τράπεζα 4
        incbin  "../build/world_test.bin"
        org     #8000                   ; τράπεζα 6 — flip_mode0 και τεταρτημόρια
        incbin  "../build/bank6.bin"
        org     #C000                   ; τράπεζα 7
        incbin  "../build/bank7.bin"
