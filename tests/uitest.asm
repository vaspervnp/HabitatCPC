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

; do_plant — σκαλωσιά: γράφει bytes ΣΕ σελιδοποιημένη τράπεζα. Το αντίστροφο
; του do_snoop, και ο μόνος τρόπος να στηθεί σκηνή που ο έλεγχος θέσης δεν θα
; επέτρεπε — ο renderer πρέπει να δοκιμαστεί και εκεί που το έδαφος λέει όχι.
do_plant:
        ld      a,(snoop_bk)
        ld      c,a
        ld      b,GA_PORT/256
        out     (c),c
        ld      hl,snoop_buf
        ld      de,(snoop_ad)
        ld      a,(snoop_n)
        ld      c,a
        ld      b,0
        ldir
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        ld      a,#5A
        ld      (done_flag),a
dpl_hang: jr    dpl_hang

; do_link — σκαλωσιά: δρομολογεί και ΤΟΠΟΘΕΤΕΙ, χωρίς να περάσει από τον
; έλεγχο εδάφους. Ο έλεγχος δοκιμάζεται χωριστά· εδώ δοκιμάζεται η εγγραφή.
do_link:
        ld      a,3                     ; CORRIDOR — ό,τι κάνει και το μενού:
        call    bd_select               ; από εκεί βγαίνει το κόστος ανά πλακίδιο
        ld      a,(plan_a)
        ld      (cr_a),a
        ld      a,(plan_b)
        ld      (cr_b),a
        call    cr_plan
        or      a
        jr      z,dl_done
        call    cr_commit
dl_done:
        ld      a,#5A
        ld      (done_flag),a
dl_hang: jr     dl_hang

; do_cost — σκαλωσιά μέτρησης: δεκαέξι φορές «σβήσε και ξαναζωγράφισε το
; φάντασμα», ώστε να βγει το κόστος ενός βήματος κέρσορα χωρίς το σκρολάρισμα.
do_cost:
        ld      b,16
dc_lp:
        push    bc
        call    ui_hide
        call    ui_show
        pop     bc
        djnz    dc_lp
        ld      a,#5A
        ld      (done_flag),a
dc_hang: jr     dc_hang

; do_plan — σκαλωσιά: δρομολογεί ανάμεσα σε δύο θόλους και γράφει και τα
; πλακίδια που πατά η διαδρομή, ώστε να συγκριθούν με το tools/route.py.
do_plan:
        ld      a,(plan_a)
        ld      (cr_a),a
        ld      a,(plan_b)
        ld      (cr_b),a
        call    cr_plan
        ld      hl,walk_buf
        ld      (walk_p),hl
        xor     a
        ld      (walk_n),a
        ld      a,(cr_n)
        or      a
        jr      z,dp_none
        ld      hl,dp_cb
        ld      (cr_cb),hl
        call    cr_walk
        call    cr_check
        jr      dp_done
dp_none:
        ld      a,255
dp_done:
        ld      (plan_bad),a
        ld      a,#5A
        ld      (done_flag),a
dp_hang: jr     dp_hang

dp_cb:
        ld      a,(walk_n)
        cp      120
        ret     nc
        ld      hl,walk_n
        inc     (hl)
        ld      hl,(walk_p)
        ld      (hl),b
        inc     hl
        ld      (hl),c
        inc     hl
        ld      (walk_p),hl
        ret

plan_a:     db 0
plan_b:     db 0
plan_bad:   db 0
walk_p:     dw 0
walk_n:     db 0
walk_buf:   defs 240

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
        include "../src/graph.asm"
        include "../src/route.asm"
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
