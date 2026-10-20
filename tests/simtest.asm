; simtest.asm — ο τροχός, η κίνηση και η φθορά, πάνω σε αληθινή δρομολόγηση.
;
; Οι πράκτορες ζουν στην τράπεζα 6 και το write_ram του εξομοιωτή φτάνει μόνο
; ως τη βασική μνήμη, οπότε η αρχική κατάσταση περνά από τη σελίδα οθόνης:
; ο host τη γράφει στο &C000 και ο Z80 τη σπρώχνει μέσα.

        buildsna
        bankset 0
        org     #0100
        run     build_routes

        include "../src/const.asm"
        include "../build/layout.asm"

STAGE_AG    equ #C000                   ; 2.048 bytes πεδία πρακτόρων
STAGE_OCC   equ #C800                   ; 256 bytes μάσκες θέσεων
STAGE_DOME  equ #C900                   ; 1.536 bytes πίνακας θόλων
STAGE_STR   equ #CF00                   ; 384 bytes πίνακας δομών (βήμα 154: ως τότε 512,
STR_BYTES   equ 48 * STRUCT_REC         ; που έγραφαν πάνω στο node_occ από το #7C00)
; Το econ_state ζει στην τράπεζα 2, δηλαδή στη βασική μνήμη: ο host το γράφει
; και το διαβάζει κατευθείαν, χωρίς σκάλα.

; --- 1. χτίζει τους πίνακες δρομολόγησης από τον γράφο που ήρθε ---
build_routes:
        di
        ld      sp,#0100
        xor     a
        ld      (done_flag),a
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        call    rt_rebuild
        call    wheel_reset
        ld      a,#5A
        ld      (done_flag),a
b1:     jr      b1

; --- 2. η αρχική κατάσταση μέσα στην τράπεζα 6 ---
load_state:
        di
        ld      sp,#0100
        xor     a
        ld      (done_flag),a
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        ld      hl,STAGE_AG
        ld      de,G_agent_fields
        ld      bc,2048
        ldir
        ld      hl,STAGE_OCC
        ld      de,G_node_occ
        ld      bc,256
        ldir
        ld      hl,STAGE_DOME
        ld      de,G_dome_tbl
        ld      bc,1536
        ldir
        ld      hl,STAGE_STR
        ld      de,G_struct_tbl
        ld      bc,STR_BYTES
        ldir
        ; ΟΙ ΔΙΑΔΡΟΜΟΙ ΑΔΕΙΟΙ (βήμα 154): στην τράπεζα 5, με CT_EMPTY, όπως τους
        ; αφήνει το game_new. Ως τότε άδεια ήταν η κατάσταση 0, και η τράπεζα 6
        ; μηδενική· τώρα 0 θα ήταν διάδρομος από τον θόλο 0 στον θόλο 0, και το
        ; lkd_corr (src/door.asm) θα τον έδενε όταν τελειώσει ο θόλος 0.
        ld      bc,GA_PORT + PAGE_B5
        out     (c),c
        ld      hl,G_corr_tbl
        ld      (hl),CT_EMPTY
        ld      bc,(MAX_CORR + 1) * CORR_REC - 1
        call    ng_dup
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        ld      a,(ec_full)             ; ο κώδικας της γεμάτης αποθήκης, όπως τον
        call    ec_setfull              ; αφήνει το st_check (βήμα 122)
        call    st_recount              ; το όριο σάρωσης από τον πίνακα που ήρθε (157)
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        ld      a,#5A
        ld      (done_flag),a
b2:     jr      b2

; --- 3. (tick_count) frames προσομοίωσης ---
run_ticks:
        di
        ld      sp,#0100
        xor     a
        ld      (done_flag),a
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
rt_lp:
        ld      hl,(tick_count)
        ld      a,h
        or      l
        jr      z,rt_end
        dec     hl
        ld      (tick_count),hl
        ; Καρφώνει τον τροχό σε μία θέση, ώστε να μετρηθεί ΑΥΤΗ και μόνο
        ; αυτή. Η μέτρηση με αφαίρεση («τρέξε χωρίς αυτήν, βγάλε τη διαφορά»)
        ; σταμάτησε να ισχύει μόλις τα περάσματα άρχισαν να εξαρτώνται το ένα
        ; από το άλλο: σβήνοντας την κίνηση, κανείς δεν φτάνει ποτέ πουθενά
        ; και το πέρασμα αναγκών βλέπει εντελώς άλλη αποικία.
        ld      a,(pin_slot)
        cp      255
        jr      z,rt_go
        ld      (wh_slot),a
rt_go:
        call    wheel_tick
        jr      rt_lp
rt_end:
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        ld      a,#5A
        ld      (done_flag),a
b3:     jr      b3

; --- 4. πίσω στη σελίδα οθόνης για να τη διαβάσει ο host ---
save_state:
        di
        ld      sp,#0100
        xor     a
        ld      (done_flag),a
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        ld      hl,G_agent_fields
        ld      de,STAGE_AG
        ld      bc,2048
        ldir
        ld      hl,G_node_occ
        ld      de,STAGE_OCC
        ld      bc,256
        ldir
        ld      hl,G_dome_tbl
        ld      de,STAGE_DOME
        ld      bc,1536
        ldir
        ld      hl,G_struct_tbl
        ld      de,STAGE_STR
        ld      bc,STR_BYTES
        ldir
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        ld      a,#5A
        ld      (done_flag),a
b4:     jr      b4


; rt_rebuild — όλη η ανοικοδόμηση χωρίς κόψιμο. Εδώ και όχι στο graph.asm:
; το παιχνίδι δεν τη χρειάζεται ποτέ (βήμα 62).
rt_rebuild:
        call    rt_begin
rtr_lp:
        ld      b,255
        call    rt_slice
        jr      nc,rtr_lp
        ret

; asc_b5 / asc_b6 — του src/link.asm, που εδώ δεν υπάρχει (το lkd_corr του
; src/door.asm τα καλεί από το βήμα 154). Κρατούν τα πάντα.
asc_b1:                                 ; βήμα 157: το st_recount (src/wheel.asm)
        push    bc
        ld      bc,GA_PORT + PAGE_B1
        jr      asc_out
asc_b5:
        push    bc
        ld      bc,GA_PORT + PAGE_B5
        jr      asc_out
asc_b6:
        push    bc
        ld      bc,GA_PORT + PAGE_B6
asc_out:
        out     (c),c
        pop     bc
        ret
ng_dup:
        ld      d,h
        ld      e,l
        inc     de
        ldir
        ret

        include "../src/graph.asm"
        include "../src/entity.asm"
        include "../src/econ.asm"
        include "../src/flow.asm"           ; βήμα 93: η θέση 12 (στο παιχνίδι στην τράπεζα 6)
        include "../src/repost.asm"         ; βήμα 115: ό,τι χάθηκε από γεμάτο πίνακα
        include "../src/drill.asm"          ; βήμα 94: η γεώτρηση
        include "../src/jobs.asm"
        include "../src/haul.asm"           ; βήμα 95: η μεταφορά
        include "../src/carry.asm"          ; βήμα 98: τα αγαθά του εμπόρου
        include "../src/install.asm"        ; βήμα 99: οι μηχανές κουβαλιούνται
        include "../src/supply.asm"         ; βήμα 88: η τροφοδοσία
        include "../src/suit.asm"           ; βήμα 90: οι στολές
        include "../src/stock.asm"
        include "../src/needs.asm"
        include "../src/ship.asm"
        include "../src/visit.asm"          ; βήμα 136: οι επισκέπτες που περπατούν
        include "../src/visit0.asm"         ; ...και ό,τι στο παιχνίδι είναι στην τράπεζα 0
        include "../src/fight0.asm"         ; βήμα 150: οι φρουροί και οι ανάγκες (τράπεζα 0)
        include "../src/foe.asm"            ; βήμα 111: οι εισβολείς (στο παιχνίδι στην τράπεζα 6)
        include "../src/crew.asm"           ; βήμα 91: οι ειδικότητες
        include "../src/bots.asm"           ; βήμα 92: τα ρομπότ (στο παιχνίδι στην τράπεζα 6)
        include "../src/wheel.asm"
        include "../src/top.asm"            ; βήμα 157: το st_set του st_recount (στο παιχνίδι στο OV_R1)
        include "../src/sound.asm"
        include "../src/meteor.asm"
        include "../src/calm.asm"           ; βήμα 158: η ηρεμία (στο παιχνίδι στη σελίδα 2, ως το 157 στο meteor.asm)
        include "../src/b6out.asm"          ; βήμα 110: ό,τι των needs/meteor θέλει άλλη τράπεζα
        include "../src/door.asm"           ; βήμα 87: το ja_build το καλεί
        include "../src/edges.asm"          ; βήμα 87: οι ακμές

done_flag:   db 0
tick_count:  dw 0
pin_slot:    db 255
bd_node:     db 0                   ; src/build.asm, που εδώ δεν υπάρχει: το st_raise
                                    ; (src/top.asm, βήμα 157) το διαβάζει, κανείς δεν το καλεί
al_brk:      db 0, 255              ; src/hud.asm (βήμα 119): η χαλασμένη μηχανή της γραμμής
                                    ; ειδοποιήσεων· το ec_break_d και το jp_one τη γράφουν

; --- η τράπεζα 2 ΠΡΕΠΕΙ να φορτωθεί ---
; Χωρίς αυτό το incbin, το G_corr_fill διαβάζεται μηδενικό: κάθε θέση του
; δαχτυλιδιού γίνεται η θέση 0, και το ent_claim αποτυγχάνει μόλις πιαστεί η
; πρώτη. Η δοκιμή περνούσε 112 frames πριν το δείξει.
        org     #8000
        incbin  "../build/page2.bin"
