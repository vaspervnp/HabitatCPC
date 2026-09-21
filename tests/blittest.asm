; blittest.asm — το πρώτο πράγμα που πρέπει να αποδειχθεί.
;
; Ολόκληρη η στρατηγική μνήμης (DESIGN.md §4.4) στηρίζεται στο ότι τα τρία
; τεταρτημόρια ne/sw/se παράγονται σωστά τη στιγμή του blit από το αποθηκευμένο
; nw. Μέχρι τώρα αυτό ήταν επαληθευμένο μόνο μέσα στη γεννήτρια των assets —
; ποτέ σε Z80.
;
; Η σκηνή: φόντο με μοτίβο (ώστε λάθος μάσκα να ΦΑΙΝΕΤΑΙ), και τα τρία μεγέθη
; θόλου με τον δακτύλιό τους. Τα τρία μεγέθη δίνουν W = 8, 12, 16, οπότε ο
; flipbuf δοκιμάζεται και στο μέγιστο πλάτος του (DOME_L_W*2 = 32).
;
; Η tests/test_blit.py χτίζει την ίδια σκηνή σε Python και συγκρίνει byte-byte.

        buildsna
        bankset 0
        org     #0100
        run     start

        include "../src/const.asm"
        include "../build/sprite_consts.asm"

; πού κάθονται τα δεδομένα σε αυτή τη δοκιμή (χωρίς τράπεζες ακόμα)
DOME_S      equ #4000       ;  512
DOME_M      equ #4200       ; 1152
DOME_L      equ #4680       ; 2048
RING_S      equ #4E80       ;  512
RING_M      equ #5080       ; 1152
RING_L      equ #5500       ; 2048 -> τελειώνει #5D00
FLIPTAB     equ #6000       ; ΠΡΕΠΕΙ να είναι σε όριο σελίδας

start:
        di
        ld      sp,#4000
        call    hw_mode0
        ld      hl,pal_test
        call    pal_set
        xor     a
        call    pal_border

        call    fill_pattern

        ; Κάθε εγγραφή είναι ακριβώς το μπλοκ παραμέτρων qf_* (6 bytes), οπότε
        ; αντιγράφεται με ldir αντί να στηθεί πεδίο-πεδίο.
        ld      hl,frametab
        ld      b,FRAMES
fr_loop:
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
        djnz    fr_loop

        ; σημάδι «τελείωσα» για το harness
        ld      a,#5A
        ld      (done_flag),a
hang:   jr      hang

; Ο δακτύλιος πρώτα, ο θόλος μετά. Δεν επικαλύπτονται ποτέ (SPRITES.md §10),
; οπότε η σειρά τους δεν κρίνει τίποτα· τη διατηρούμε για να μοιάζει με το
; πραγματικό μονοπάτι σχεδίασης.
frametab:
        dw      RING_S
        db       2,  8, DOME_S_W, DOME_S_H
        dw      DOME_S
        db       2,  8, DOME_S_W, DOME_S_H
        dw      RING_M
        db      20,  8, DOME_M_W, DOME_M_H
        dw      DOME_M
        db      20,  8, DOME_M_W, DOME_M_H
        dw      RING_L
        db      46,  8, DOME_L_W, DOME_L_H
        dw      DOME_L
        db      46,  8, DOME_L_W, DOME_L_H
FRAMES  equ 6

; ---------------------------------------------------------------------------
; fill_pattern — byte(x,y) = (y*5 + x) & 255
; Αλλάζει και στους δύο άξονες, οπότε μια μάσκα που αφήνει να περάσει λάθος
; pixel δεν μπορεί να κρυφτεί πίσω από ομοιόμορφο φόντο.
; ---------------------------------------------------------------------------
fill_pattern:
        ld      c,0                 ; y
fp_line:
        push    bc
        ld      a,c
        ld      c,0                 ; x = 0
        call    scr_addr            ; -> DE
        pop     bc
        ld      a,c                 ; y
        ld      l,a
        add     a,a
        add     a,a
        add     a,l                 ; y*5
        ld      b,SCR_W
fp_byte:
        ld      (de),a
        inc     de
        inc     a
        djnz    fp_byte
        inc     c
        ld      a,c
        cp      SCR_H
        jr      nz,fp_line
        ret

        include "../src/screen.asm"
        include "../src/blit.asm"
        include "../src/hw.asm"

done_flag:  db 0

; Προσωρινή παλέτα δοκιμής: 16 διακριτοί firmware αριθμοί, ώστε κάθε pen να
; ξεχωρίζει στο PNG. Η πραγματική έρχεται από το palette_fw των assets.
pal_test:
        db  0, 1,11,23,13,26,24,15
        db  6,18,10, 5,25, 3,19,16

; --- δεδομένα ---
; Κομμάτια από το tools/mkslices.py. ΟΧΙ incbin με offset: ο rasm αποτιμά τα
; ορίσματα του incbin πριν υπάρξουν τα equ, και φορτώνει σιωπηλά λάθος bytes.
        org     DOME_S
        incbin  "../build/slices/dome_s_nw.bin"
        org     DOME_M
        incbin  "../build/slices/dome_m_nw.bin"
        org     DOME_L
        incbin  "../build/slices/dome_l_nw.bin"
        org     RING_S
        incbin  "../build/slices/ring_s_nw.bin"
        org     RING_M
        incbin  "../build/slices/ring_m_nw.bin"
        org     RING_L
        incbin  "../build/slices/ring_l_nw.bin"
        org     FLIPTAB
        incbin  "../build/slices/flip_mode0.bin"
