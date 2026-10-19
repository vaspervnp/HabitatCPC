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
        ; Η λίστα αλλαγών τρέχει όπως στο main.asm: από το βήμα 35 ένας θόλος
        ; που τοποθετείται εμφανίζεται μέσα από αυτήν, σειρά προς σειρά.
        call    dirty_tick
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
        call    cr_commit_ln            ; ό,τι και το LINK (βήμα 87)
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

ready_flag: db 0
done_flag:  db 0
snoop_bk:   db PAGE_B6
snoop_ad:   dw 0
snoop_n:    db 0
tick_n:     db 0
goto_x:     db 0
goto_y:     db 0
goto_st:    db 0

        include "../src/screen.asm"
        include "../src/blit.asm"
        include "../src/tiles.asm"
        include "../src/object.asm"
        include "../src/joint.asm"          ; βήμα 96: στο παιχνίδι στο b6code
        ; Το src/entity.asm δεν είναι εδώ· το jtm_set και το jtb_mark θέλουν το
        ; bit_tab του ΚΑΤΩ από το #4000, που τα βλέπει με την 5 ή την 6 μέσα.
bit_tab: db 1,2,4,8,16,32,64,128
; τα DK_RSIZE και DK_RECT της κατεδάφισης (βήμα 101) ζουν στο OV_R1 της
; τράπεζας 1 (src/dm_hand.asm, βήμα 155), που εδώ δεν υπάρχει· κανείς δεν τα
; σπρώχνει. Ούτε το blk_row του src/jobs.asm, που το su_lock καλεί μόνο από
; δομή, και εδώ κανείς δεν το καλεί (βήμα 155).
DH_RSIZE    equ 0
DH_RECT     equ 0
blk_row     equ 0
        include "../src/dirty.asm"
        include "../src/figure.asm"         ; βήμα 89: οι άποικοι έξω
        include "../src/hud.asm"
        include "../src/view.asm"
        include "../src/ghost.asm"
        include "../src/input.asm"
        include "../src/build.asm"
        include "../src/supply.asm"         ; βήμα 88: το bd_link και το HUD το καλούν
        include "../src/suit.asm"           ; βήμα 90: το su_hud του HUD
tr_arrive:                              ; το sp_arrive, για μια J_TRADE (src/carry.asm),
mc_arrive:                              ; και για τις μηχανές (βήμα 99, src/install.asm),
mc_tail:
jb_dome_ptr:                            ; το mc_live του src/supply.asm (βήμα 100) — εδώ δεν το καλεί κανείς,
nd_load:                                ; το su_tick γυρίζει εκεί (src/needs.asm),
nd_die: ret                             ; και εδώ δεν το καλεί κανείς
        include "../src/stock.asm"
        include "../src/terrain.asm"
bd_mprice:                              ; βήμα 123: src/mine.asm, μόνο στο παιχνίδι —
bd_mflags:  ret                         ; εδώ το ορυχείο πληρώνει, όπως ως το 122
        include "../src/graph.asm"
        include "../src/route.asm"
        include "../src/link.asm"           ; βήμα 85: το ui.asm το καλεί
        include "../src/commit.asm"         ; βήμα 94: το al_commit, στην τράπεζα 1 του παιχνιδιού
        include "../src/ui.asm"
        include "../src/fit.asm"
        include "../src/rooms.asm"
        ; ΟΙ ΑΝΙΧΝΕΥΣΕΙΣ ΤΩΝ ΔΟΚΙΜΩΝ γράφουν στο #3F00-#3FFF (test_build,
        ; test_terrain, test_view, test_game). Ως το βήμα 96 ο κώδικας έφτανε ως
        ; το #3FFD και του έσβηναν την ουρά του ήχου· στο 97 το src/bend.asm θα
        ; τον έφερνε ως το #4108, πάνω στο rm_build. Γι' αυτό τα δύο αρχεία των
        ; ανιχνεύσεων και ο ήχος πήγαν στην τράπεζα 2, και το bend.asm στην 5,
        ; όπως στο παιχνίδι.
        assert  $ <= #3F00

        org     #8000
        incbin  "../build/page2.bin"
        ; Πάνω από το αρχείο του φαντάσματος, όπου το παιχνίδι έχει τον κώδικα
        ; της τράπεζας 2 και εδώ δεν υπάρχει τίποτα: πάντα στο παράθυρο.
        org     PAGE2_CODE
walk_buf:   defs 240
snoop_buf:  defs 96
        include "../src/sound.asm"
        ; ΚΑΙ ΤΟ hw.asm (βήμα 134), όπως στο παιχνίδι (src/main.asm): η επίπεδη
        ; περιοχή περνούσε το #3F00 κατά 28 bytes, με τα νομίσματα του HUD, την
        ; κρυφή τους μνήμη και το fg_build που κρατά τη σειρά της λίστας.
        include "../src/hw.asm"
        ; ΚΑΙ ΤΑ ΔΙΑΣΤΗΜΑΤΑ ΤΩΝ ΘΟΛΩΝ (βήμα 108): στην τράπεζα 0 του παιχνιδιού,
        ; αλλά εδώ η επίπεδη περιοχή θα περνούσε το #3F00 κατά 302 bytes· και με
        ; αυτά εδώ, κατά 38, από το ob_blit που μεγάλωσε. Γι' αυτό ήρθε και το
        ; χτίσιμο του ευρετηρίου, που στο παιχνίδι ζει στην τράπεζα 2.
        include "../src/span.asm"
        include "../src/span6.asm"          ; βήμα 114: στο παιχνίδι στο b6code
        include "../src/walk6.asm"          ; βήμα 118: στο παιχνίδι στο b6code
        include "../src/alert6.asm"         ; βήμα 119: στο παιχνίδι στο b6code
vs_coins:                               ; βήμα 134: src/ship.asm, που εδώ δεν υπάρχει·
        ld      hl,(EC_COINS)           ; το hd_b6 έχει βάλει την 6 στο παράθυρο
        ret
        include "../src/bend.asm"           ; βήμα 97: στο παιχνίδι στο b6code (129)
        include "../src/corner.asm"         ; βήμα 129: στο παιχνίδι στο b6code
        include "../src/objindex.asm"
        ; ΚΑΙ ΟΙ ΑΚΜΕΣ (βήμα 154), όπως στο παιχνίδι: η επίπεδη περιοχή περνούσε
        ; το #3F00 κατά 14 bytes, με τον πίνακα των δομών σε δύο σελίδες.
        include "../src/edges.asm"          ; βήμα 87: οι ακμές
        assert  $ <= #C000
        org     #7000
        incbin  "../build/bank1.bin"     ; εικονίδια m και l (§4.2)

        bankset 1
        org     #0000
        incbin  "../build/world_col.bin"
        org     B5_BASE                 ; οι μηχανές στην τράπεζα 5 (βήμα 85)
        incbin  "../build/bank5_col.bin", 0, G_b5code - B5_BASE   ; και οι διάδρομοι (βήμα 154)
        ; οι κοντές στροφές ήταν εδώ ως το βήμα 128 (src/bend.asm): πήγαν στο
        ; b6code, εδώ στο #8000 με τα υπόλοιπα· και εδώ τα σχέδια των γωνιών
        org     G_b5code
        include "../build/corner_spr.asm"
        org     #8000
        incbin  "../build/bank6_col.bin"
        org     #C000
        incbin  "../build/bank7.bin", 0, G_text - #4000
        include "../src/uitext.asm"
        org     #C000 + G_text + TEXT_MAX - #4000
        incbin  "../build/bank7.bin", G_text + TEXT_MAX - #4000
