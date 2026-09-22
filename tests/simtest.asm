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
STAGE_STR   equ #CF00                   ; 512 bytes πίνακας δομών
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
        ld      bc,512
        ldir
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
        ld      bc,512
        ldir
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        ld      a,#5A
        ld      (done_flag),a
b4:     jr      b4

        include "../src/graph.asm"
        include "../src/entity.asm"
        include "../src/econ.asm"
        include "../src/wheel.asm"

done_flag:   db 0
tick_count:  dw 0

; --- η τράπεζα 2 ΠΡΕΠΕΙ να φορτωθεί ---
; Χωρίς αυτό το incbin, το G_corr_fill διαβάζεται μηδενικό: κάθε θέση του
; δαχτυλιδιού γίνεται η θέση 0, και το ent_claim αποτυγχάνει μόλις πιαστεί η
; πρώτη. Η δοκιμή περνούσε 112 frames πριν το δείξει.
        org     #8000
        incbin  "../build/page2.bin"
