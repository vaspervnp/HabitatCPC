; gentest.asm — η γεννήτρια κόσμου σε πραγματικό Z80.
;
; Το read_ram του εξομοιωτή ΔΕΝ ακολουθεί το paging: στο &4000 βλέπει τη βασική
; τράπεζα 1, όχι την 4. Γι' αυτό υπάρχει το dump_bank4 — κατεβάζει το επίπεδο
; στη βασική τράπεζα 1 ανά 256 bytes, εναλλάσσοντας σελιδοποίηση, ώστε το
; harness να το διαβάσει με ένα read_ram(#4000, #4000).

        buildsna
        bankset 0
        org     #0100
        run     start

        include "../src/const.asm"
        include "../build/sprite_consts.asm"
        include "../build/layout.asm"
        include "../build/gen_tables.asm"

start:
        di
        ld      sp,#0100
        ld      bc,GA_PORT + PAGE_B4
        out     (c),c
        call    worldgen_run
        call    dump_bank4
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        ld      a,#5A
        ld      (done_flag),a
hang:   jr      hang

; ---------------------------------------------------------------------------
; dump_bank4 — τράπεζα 4 -> βασική τράπεζα 1, ανά 256 bytes μέσω ενδιάμεσου.
; Καμία σελίδα δεν βλέπει και τις δύο ταυτόχρονα, οπότε πάει με σκάλα.
; ---------------------------------------------------------------------------
dump_bank4:
        ld      hl,0                ; μετατόπιση
db_loop:
        ld      (db_off),hl
        ld      bc,GA_PORT + PAGE_B4
        out     (c),c
        ld      hl,(db_off)
        ld      de,#4000
        add     hl,de
        ld      de,db_buf
        ld      bc,256
        ldir
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        ld      hl,db_buf
        ld      de,(db_off)
        ex      de,hl
        ld      bc,#4000
        add     hl,bc
        ex      de,hl               ; DE = #4000 + off
        ld      bc,256
        ldir
        ld      hl,(db_off)
        ld      bc,256
        add     hl,bc
        ld      a,h
        cp      #40
        jr      nz,db_loop
        ret

db_off:     dw 0
db_buf:     defs 256
done_flag:  db 0

        include "../src/worldgen.asm"
