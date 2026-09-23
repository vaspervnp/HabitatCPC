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
        ld      a,(hud_on)
        or      a
        call    nz,hud_draw
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

; --- τρίτη είσοδος: σκρολάρισμα, για ισοδυναμία και για κόστος ---
do_scroll:
        ld      a,(sc_n)
        ld      (sc_left),a
ds_lp:
        ld      a,(sc_dir)
        call    view_scroll
        ld      a,(hud_on)
        or      a
        call    nz,hud_draw
        ld      a,(sc_left)
        dec     a
        ld      (sc_left),a
        jr      nz,ds_lp
        ld      a,#5A
        ld      (done_flag),a
ds_hang: jr     ds_hang

; --- τέταρτη είσοδος: μόνο το HUD, για μέτρηση ---
; Το hu_cold ακυρώνει την κρυφή μνήμη πριν από κάθε πέρασμα: έτσι μετριούνται
; χωριστά η ΚΡΥΑ επανασχεδίαση (μετά από βήμα κάμερας, όπου τίποτα δεν ισχύει)
; και η ΖΕΣΤΗ (κάθε τικ HUD, όπου αλλάζουν τρία κελιά).
do_hud:
        ld      a,(rep_n)
        ld      (hu_n),a
hu_loop:
        ld      a,(hu_cold)
        or      a
        call    nz,hud_inval
        call    hud_draw
        ld      a,(hu_n)
        dec     a
        ld      (hu_n),a
        jr      nz,hu_loop
        ld      a,#5A
        ld      (done_flag),a
hu_hang: jr     hu_hang

; --- πέμπτη είσοδος: η λίστα αλλαγών ---
; Η ΙΔΙΑ μετάλλαξη, δύο δρόμοι: μια φορά μέσω της λίστας και μια με πλήρη
; επανασχεδίαση. Αν διαφέρουν, η «ελάχιστη επανασχεδίαση» του §8.5 δεν είναι
; ελάχιστη — είναι ελλιπής.
do_dirty:
        call    mutate
        call    dirty_reset
        call    push_all
dd_lp:
        call    dirty_tick
        ld      hl,dd_ticks
        inc     (hl)
        or      a
        jr      nz,dd_lp
        ld      a,#5A
        ld      (done_flag),a
dd_hang: jr     dd_hang

do_full:
        call    mutate
        call    redraw_now
        ld      a,#5A
        ld      (done_flag),a
df_hang: jr     df_hang

; redraw_now — πλήρης σχεδίαση ΧΩΡΙΣ ob_touch: το dome_fig είναι μέρος της
; μετάλλαξης και δεν πρέπει να ξαναχτιστεί από τους πράκτορες.
redraw_now:
        call    ob_clip_full
        call    view_cam
        ld      bc,GA_PORT + PAGE_B4
        out     (c),c
        call    tile_draw_all
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        jp      ob_draw_all

mutate:
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        ld      a,8                     ; ο θόλος 0 γίνεται εργοστάσιο
        ld      (G_dome_tbl + D_ROOM),a
        ld      a,5                     ; υποδοχή 2: ρομπότ
        ld      (G_dome_tbl + D_MACH + 2),a
        ld      a,200
        ld      (G_dome_tbl + D_HEALTH + 2),a
        ld      a,3                     ; θόλος 1, υποδοχή 0: όπλα
        ld      (G_dome_tbl + DOME_REC + D_MACH),a
        ld      a,200
        ld      (G_dome_tbl + DOME_REC + D_HEALTH),a
        ld      bc,GA_PORT + PAGE_B4
        out     (c),c
        ld      b,-16                   ; ένα tile γίνεται βουνό με φλέβα
        ld      c,-9
        call    tile_addr
        ld      (hl),3 + 8
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        ; Ο ΠΡΑΚΤΟΡΑΣ, ΟΧΙ Ο ΠΙΝΑΚΑΣ ΦΙΓΟΥΡΩΝ. Πριν, η μετάλλαξη έγραφε
        ; κατευθείαν στο dome_fig — που είναι κρυφή μνήμη του renderer, όχι
        ; κατάσταση του παιχνιδιού. Από το βήμα 14 το dirty_tick την ξαναχτίζει
        ; από τους πράκτορες σε κάθε πέρασμα, οπότε μια μετάλλαξη στην κρυφή
        ; μνήμη σβήνεται. Ο πράκτορας 2 είναι στον θόλο 1, θέση 0.
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        xor     a
        ld      (AG_NODE + 2),a         ; -> θόλος 0
        ld      a,1
        ld      (AG_NODE + 128 + 2),a   ; θέση 1
        ld      a,4
        ld      (AG_FLAGS + 128 + 2),a  ; φρουρός
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        jp      ob_touch

push_all:
        ld      a,DK_ICON
        ld      b,0
        ld      c,0
        call    dirty_push
        ld      a,DK_MACH
        ld      b,0
        ld      c,2
        call    dirty_push
        ld      a,DK_MACH
        ld      b,1
        ld      c,0
        call    dirty_push
        ld      a,DK_SLOT
        ld      b,0
        ld      c,1
        call    dirty_push
        ld      a,DK_SLOT
        ld      b,1
        ld      c,0
        call    dirty_push
        ld      a,DK_CONN
        ld      b,0
        ld      c,4
        call    dirty_push
        ld      a,DK_TILE
        ld      b,-16
        ld      c,-9
        jp      dirty_push

; --- έκτη είσοδος: ΕΝΑ είδος της λίστας, REPS φορές, για να μετρηθεί ---
do_one:
        call    mutate
        ld      a,(oo_kind)
        ld      (dt_kind),a
        ld      a,(oo_a)
        ld      (dt_a),a
        ld      a,(oo_b)
        ld      (dt_b),a
        ld      a,(rep_n)
        ld      (o1_n),a
o1_lp:
        call    dt_dispatch
        ld      a,(o1_n)
        dec     a
        ld      (o1_n),a
        jr      nz,o1_lp
        ld      a,#5A
        ld      (done_flag),a
o1_hang: jr     o1_hang

oo_kind:    db 0
oo_a:       db 0
oo_b:       db 0
o1_n:       db 0
dd_ticks:   db 0
hu_n:       db 0
hu_cold:    db 0
rep_n:      db 0
oo_n:       db 0
sc_dir:     db 0
sc_n:       db 1
sc_left:    db 0
hud_on:     db 1
done_flag:  db 0

        include "../src/screen.asm"
        include "../src/blit.asm"
        include "../src/tiles.asm"
        include "../src/object.asm"
        include "../src/dirty.asm"
        include "../src/hud.asm"
        include "../src/view.asm"
        include "../src/hw.asm"

        org     #8000
        incbin  "../build/page2.bin"
        org     #7000
        incbin  "../build/bank1.bin"     ; εικονίδια m και l (§4.2)

        bankset 1
        org     #0000                   ; τράπεζα 4 — το επίπεδο κόσμου
        incbin  "../build/world_col.bin"
        org     #8000                   ; τράπεζα 6 — τεταρτημόρια ΚΑΙ πίνακες
        incbin  "../build/bank6_col.bin"
        org     #C000                   ; τράπεζα 7
        incbin  "../build/bank7.bin", 0, G_text - #4000
        include "../src/uitext.asm"
        org     #C000 + G_text + TEXT_MAX - #4000
        incbin  "../build/bank7.bin", G_text + TEXT_MAX - #4000
