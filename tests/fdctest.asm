; fdctest.asm — ο οδηγός δισκέτας σε πραγματικό Z80, με πραγματική δισκέτα.
;
; Τρία πράγματα, με αυτή τη σειρά: διάβασε τομέα που ΞΕΡΟΥΜΕ τι έχει (τον
; κατάλογο), γράψε μοτίβο σε άδειους τομείς, ξαναδιάβασέ τους. Το πρώτο
; αποδεικνύει ότι ο οδηγός μιλά στον δίσκο και όχι στον εαυτό του· τα άλλα δύο
; ότι η εγγραφή φτάνει εκεί που λέει.

        buildsna
        bankset 0
        org     #0100
        run     start

        include "../src/const.asm"
        include "../build/sprite_consts.asm"
        include "../build/layout.asm"

SRC         equ #9000               ; το μοτίβο
BACK       equ #A000                ; και πού ξαναδιαβάζεται
NSECT       equ 3

start:
        di
        ld      sp,#0100
        call    hw_mode0                ; τα ROM σβηστά, όπως στο παιχνίδι
        ; --- το μοτίβο: κάθε byte συνάρτηση της διεύθυνσής του ---
        ld      hl,SRC
        ld      de,NSECT * 512
pat_lp:
        ld      a,h
        xor     l
        add     a,l
        ld      (hl),a
        inc     hl
        dec     de
        ld      a,d
        or      e
        jr      nz,pat_lp

        call    fdc_on
        ; --- 1. ο κατάλογος: track 0, τομέας #C1 ---
        xor     a
        call    fdc_seek
        ld      a,#C1
        ld      (fd_sect),a
        ld      hl,#8000
        call    fdc_rsect
        ld      (r_read),a
        ; --- 2. γράψιμο στο track 24 ---
        ld      a,24
        call    fdc_seek
        ld      a,#C1
        ld      (fd_sect),a
        ld      hl,SRC
        ld      b,NSECT
        ld      a,#45
        call    fdc_stream
        ld      (r_write),a
        ; --- 3. και πίσω ---
        ld      a,24
        call    fdc_seek
        ld      a,#C1
        ld      (fd_sect),a
        ld      hl,BACK
        ld      b,NSECT
        ld      a,#46
        call    fdc_stream
        ld      (r_back),a
        ; --- 4. ΓΕΙΤΟΝΑΣ: ο τομέας #C5 του ίδιου track δεν γράφτηκε ---
        ld      a,24
        call    fdc_seek
        ld      a,#C5
        ld      (fd_sect),a
        ld      hl,#B000
        call    fdc_rsect
        ld      (r_nbr),a
        call    fdc_off
        ld      a,#5A
        ld      (done_flag),a
hang:   jr      hang

r_read:     db #FF
r_write:    db #FF
r_back:     db #FF
r_nbr:      db #FF
done_flag:  db 0

        include "../src/fdc.asm"
        include "../src/hw.asm"
