; uitest.asm — το build mode σε πραγματικό υλικό.
;
; Ο βρόχος είναι ο κανονικός: ένα ui_tick ανά frame, συγχρονισμένο στο VSync.
; Το harness πατάει πλήκτρα και κοιτάζει και τη μνήμη και την οθόνη.

        buildsna
        bankset 0
        org     #0100
        run     start

        include "../src/const.asm"
        include "../build/sprite_consts.asm"
        include "../build/layout.asm"

FLIPTAB     equ G_flip_mode0
PPI_B       equ #F500

start:
        di
        ld      sp,#0100
        call    hw_mode0
        ld      hl,G_palette_fw
        call    pal_set
        xor     a
        call    pal_border
        call    ob_clip_full
        ; Ο πίνακας εργασιών ξεκινά ΑΔΕΙΟΣ, και το άδειο είναι 255 — το μηδέν
        ; σημαίνει «εργασία Build». Δεν υπάρχει ακόμη ρουτίνα «νέο παιχνίδι»
        ; στον Z80 (§10.1), οπότε το κάνει το harness.
        ld      hl,G_job_tbl
        ld      b,MAX_JOB
jt_lp:
        ld      (hl),NO_JOB
        push    bc
        ld      bc,JOB_REC
        add     hl,bc
        pop     bc
        djnz    jt_lp
        call    ui_init
        ld      a,#5A
        ld      (ready_flag),a
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
        call    ui_tick
        ld      hl,tick_n
        inc     (hl)
        jr      loop

; --- είσοδοι που οδηγεί το harness ---
do_hide:
        call    ui_hide
        ld      a,#5A
        ld      (done_flag),a
dh_hang: jr     dh_hang

do_redraw:
        call    gh_reset
        call    ob_clip_full
        call    view_draw
        call    hud_draw
        ld      a,#5A
        ld      (done_flag),a
dr_hang: jr     dr_hang

; do_goto — σκαλωσιά δοκιμής: πηγαίνει τον κέρσορα κάπου χωρίς εκατό πατήματα.
do_goto:
        call    ui_hide
        ld      a,(goto_x)
        ld      (cur_hx),a
        ld      a,(goto_y)
        ld      (cur_hy),a
        ld      a,(goto_st)
        ld      (ui_state),a
        call    ui_center
        call    view_draw
        call    hud_draw
        call    ui_show
        ld      a,#5A
        ld      (done_flag),a
dg_hang: jr     dg_hang

; do_snoop — σκαλωσιά: αντιγράφει bytes από σελιδοποιημένη τράπεζα σε RAM που
; βλέπει το harness. Το read_ram του εξομοιωτή φτάνει μόνο ως τα βασικά 64K.
do_snoop:
        ld      a,(snoop_bk)
        ld      c,a
        ld      b,GA_PORT/256
        out     (c),c
        ld      hl,(snoop_ad)
        ld      de,snoop_buf
        ld      a,(snoop_n)
        ld      c,a
        ld      b,0
        ldir
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        ld      a,#5A
        ld      (done_flag),a
ds_hang: jr     ds_hang

ready_flag: db 0
done_flag:  db 0
snoop_bk:   db PAGE_B6
snoop_ad:   dw 0
snoop_n:    db 0
snoop_buf:  defs 96
tick_n:     db 0
goto_x:     db 0
goto_y:     db 0
goto_st:    db 0

        include "../src/screen.asm"
        include "../src/blit.asm"
        include "../src/tiles.asm"
        include "../src/object.asm"
        include "../src/dirty.asm"
        include "../src/hud.asm"
        include "../src/view.asm"
        include "../src/ghost.asm"
        include "../src/input.asm"
        include "../src/build.asm"
        include "../src/ui.asm"
        include "../src/hw.asm"

        org     #8000
        incbin  "../build/page2.bin"

        bankset 1
        org     #0000
        incbin  "../build/world_col.bin"
        org     #8000
        incbin  "../build/bank6_col.bin"
        org     #C000
        incbin  "../build/bank7.bin"
