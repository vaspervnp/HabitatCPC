; packtest.asm — η διάταξη μνήμης σε πραγματικό υλικό.
;
; Το tests/test_pack.py αποδεικνύει ότι η διάταξη είναι σωστή ΣΤΟ ΧΑΡΤΙ: τίποτα
; δεν πατάει σε δύο αρένες, τίποτα δεν κάθεται πάνω στις γραμμές του HUD, τα
; bytes είναι τα σωστά. Δεν αποδεικνύει ότι ο Z80 τα ΦΤΑΝΕΙ.
;
; Εδώ σχεδιάζεται μια σκηνή που αγγίζει και τις τρεις περιοχές:
;
;   σελίδα 2 (&8000)  έδαφος μέσω tile_ptr, εικονίδιο μέσω icon_m_ptr
;   τράπεζα 6 (&C6)   δακτύλιος + θόλος + flip_mode0 + φιγούρα σε θέση
;   τράπεζα 7 (&C7)   εξωτερική δομή
;
; Δύο σελιδοποιήσεις μέσα στην ίδια σκηνή, που είναι ακριβώς ό,τι θα κάνει ο
; πραγματικός βρόχος σχεδίασης.

        buildsna

        bankset 0
        org     #0100
        run     start

        include "../src/const.asm"
        include "../build/sprite_consts.asm"
        include "../build/layout.asm"

FLIPTAB     equ G_flip_mode0        ; στην τράπεζα 6, σε όριο σελίδας

DOME_X      equ 24                  ; bytes
DOME_Y      equ 32                  ; γραμμές
STRUCT_X    equ 60
STRUCT_Y    equ 40
ICON_X      equ 4
ICON_Y      equ 8

start:
        di
        ld      sp,#0100
        call    hw_mode0
        ld      hl,G_palette_fw         ; η ΠΡΑΓΜΑΤΙΚΗ παλέτα, από τα assets
        call    pal_set
        xor     a
        call    pal_border

        call    draw_terrain            ; σελίδα 2

        ; --- τράπεζα 6: δακτύλιος, θόλος, φιγούρα ---
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        ld      hl,frametab
        ld      b,2
p6_loop:
        push    bc
        push    hl
        ld      de,qf_src
        ld      bc,6
        ldir
        call    blit_quads
        pop     hl
        ld      bc,6
        add     hl,bc
        pop     bc
        djnz    p6_loop

        ; φιγούρα 1 (άποικος) στη θέση 0 του μικρού θόλου.
        ; corr_slots + size*CORR_SLOTS*2 + slot*2 -> (x σε bytes, y) στο πλαίσιο
        ld      hl,(G_corr_slots)       ; μέγεθος s, θέση 0 -> L = x, H = y
        ld      a,l
        add     a,DOME_X
        ld      c,a
        ld      a,h
        add     a,DOME_Y
        call    scr_addr
        ld      hl,G_corr_slot_gfx + 1*SLOT_SIZE   ; s, θέση 0, fig 1
        ld      b,SLOT_W
        ld      c,SLOT_H
        call    blit_op

        ; --- τράπεζα 7: εξωτερική δομή ---
        ld      bc,GA_PORT + PAGE_B7
        out     (c),c
        ld      c,STRUCT_X
        ld      a,STRUCT_Y
        call    scr_addr
        ld      hl,G_solar_m
        ld      b,8                     ; solar_m: 16x32 px -> 8 bytes δεδομένων
        ld      c,32
        call    blit_mask

        ; --- πίσω στη βασική, και ένα εικονίδιο από τη σελίδα 2 ---
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        ld      hl,(G_icon_m_ptr + 5*2) ; τύπος 5 = greenhouse
        ld      c,ICON_X
        ld      a,ICON_Y
        push    hl
        call    scr_addr
        pop     hl
        ld      b,ICON_M_W
        ld      c,ICON_M_H
        call    blit_op

        ld      a,#5A
        ld      (done_flag),a
hang:   jr      hang

frametab:
        dw      G_ring_s_nw
        db      DOME_X, DOME_Y, DOME_S_W, DOME_S_H
        dw      G_dome_s_nw
        db      DOME_X, DOME_Y, DOME_S_W, DOME_S_H

; ---------------------------------------------------------------------------
; draw_terrain — 20x10 tiles στο κάδρο, από τη σελίδα 2.
;
; Η κλάση και η παραλλαγή βγαίνουν ντετερμινιστικά από τις συντεταγμένες, ώστε
; η Python να φτιάξει ακριβώς την ίδια εικόνα χωρίς να μοιραστεί κώδικα:
;       class   = (tx + ty) mod 8
;       variant = (tx * 3 + ty) AND (tile_variants[class] - 1)
;
; Το AND είναι ο λόγος που υπάρχει ο tile_variants: ο crater και το foundation
; έχουν 2 παραλλαγές, όχι 4, και χωρίς mask το decor 2-3 δείχνει στα tiles της
; ΕΠΟΜΕΝΗΣ κλάσης (SPRITES.md §3).
; ---------------------------------------------------------------------------
draw_terrain:
        ld      c,0                     ; ty
dt_row:
        ld      b,0                     ; tx
dt_col:
        push    bc
        ; class = (tx + ty) & 7
        ld      a,b
        add     a,c
        and     7
        ld      e,a                     ; class
        ; variant = (tx*3 + ty) & (tile_variants[class]-1)
        ld      a,b
        add     a,b
        add     a,b
        add     a,c
        push    af
        ld      hl,G_tile_variants
        ld      d,0
        add     hl,de
        ld      a,(hl)
        dec     a
        ld      l,a                     ; mask
        pop     af
        and     l                       ; variant
        ; πηγή = tile_ptr[class] + variant*TILE_SZ
        ld      h,0
        ld      l,a
        add     hl,hl                   ; *2
        add     hl,hl                   ; *4
        add     hl,hl                   ; *8
        add     hl,hl                   ; *16
        add     hl,hl                   ; *32
        add     hl,hl                   ; *64
        push    hl
        ld      hl,G_tile_ptr
        sla     e
        ld      d,0
        add     hl,de
        ld      a,(hl)
        inc     hl
        ld      h,(hl)
        ld      l,a                     ; HL = tile_ptr[class]
        pop     de
        add     hl,de                   ; + variant*64
        pop     bc                      ; B = tx, C = ty
        push    bc
        push    hl                      ; η πηγή· το scr_addr χαλάει το HL
        ; οθόνη: x = tx*TILE_W, y = ty*TILE_H
        ld      a,c
        add     a,a
        add     a,a
        add     a,a
        add     a,a                     ; ty*16  (<=144)
        ld      d,a                     ; φύλαξε το y πριν χαθεί το C
        ld      a,b
        add     a,a
        add     a,a                     ; tx*4   (<=76)
        ld      c,a
        ld      a,d
        call    scr_addr
        pop     hl
        ld      b,TILE_W
        ld      c,TILE_H
        call    blit_op
        pop     bc
        inc     b
        ld      a,b
        cp      20
        jr      nz,dt_col
        inc     c
        ld      a,c
        cp      10
        jr      nz,dt_row
        ret

        include "../src/screen.asm"
        include "../src/blit.asm"
        include "../src/hw.asm"

done_flag:  db 0

; --- σελίδα 2: αρένες + περιοχή οθόνης HUD ---
        org     #8000
        incbin  "../build/page2.bin"

; --- τράπεζες 4-7 ---
        bankset 1
        org     #8000                   ; τρίτο μπλοκ του bankset 1 = τράπεζα 6
        incbin  "../build/bank6.bin"
        org     #C000                   ; τέταρτο = τράπεζα 7
        incbin  "../build/bank7.bin"
