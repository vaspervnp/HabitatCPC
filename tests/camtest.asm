; camtest.asm — κάμερα με offset του CRTC, και η απόπειρα raster split.
;
; Το §15 του DESIGN το έχει ως τον πιο αβέβαιο ισχυρισμό όλου του εγγράφου, και
; το §8.2 στηρίζεται πάνω του: αν το σκρολάρισμα δεν γίνεται με τους
; καταχωρητές, κάθε βήμα κοστίζει πλήρη επανασχεδίαση 9,3 frames αντί για 0,47.
;
; Τρεις ξεχωριστοί ισχυρισμοί, τρία ξεχωριστά πειράματα, με το (split_mode) να
; διαλέγει:
;
;   0  καθόλου δεύτερη εγγραφή — μετράμε μόνο τη μετατόπιση ανά offset
;   1  δεύτερη εγγραφή στα R12/R13 στη μέση του frame  (η τομή του §8.1)
;   2  δεύτερη εγγραφή στο ΠΕΡΙΓΡΑΜΜΑ στο ίδιο ακριβώς σημείο
;
; Το 2 είναι ο έλεγχος που κρατά το πείραμα τίμιο: αν το περίγραμμα αλλάζει στη
; μέση της οθόνης και η σελίδα όχι, τότε ο χρονισμός είναι σωστός και το
; συμπέρασμα αφορά τον CRTC, όχι τον κώδικά μου.
;
; Η σελίδα παιχνιδιού είναι μαύρη με ΜΙΑ κάθετη γραμμή: η θέση της στην
; αποδοσμένη εικόνα μετράει ακριβώς πόσο μετακινήθηκε η εικόνα.

        buildsna
        bankset 0
        org     #0100
        run     start

        include "../src/const.asm"

CRTC_SEL    equ #BC00
CRTC_VAL    equ #BD00

PLAY_PAGE   equ 3                   ; &C000
HUD_PAGE    equ 2                   ; &8000
LINE_BYTE   equ 20                  ; πού κάθεται η κάθετη γραμμή

start:
        di
        ld      sp,#0100
        call    hw_mode0
        ld      hl,pal_test
        call    pal_set
        xor     a
        call    pal_border

        call    fill_play
        call    fill_hud

loop:
        ; --- συγχρονισμός στην ακμή του VSync ---
        ld      bc,PPI_B
vs_low:
        in      a,(c)
        rra
        jr      c,vs_low
vs_high:
        in      a,(c)
        rra
        jr      nc,vs_high

        ; --- η σελίδα του κάδρου, με το offset της κάμερας ---
        ld      a,(cam_off+1)
        and     #03
        or      PLAY_PAGE*16
        ld      b,a
        ld      a,(cam_off)
        ld      c,a
        call    crtc_set
        ld      a,#54               ; περίγραμμα μαύρο (hw για firmware 0)
        call    border_set

        ; --- περίμενε ως το σημείο τομής ---
        ld      hl,(split_delay)
sd_lp:
        dec     hl
        ld      a,h
        or      l
        jr      nz,sd_lp

        ld      a,(split_mode)
        dec     a
        jr      z,do_page
        dec     a
        jr      z,do_border
        jr      loop
do_page:
        ld      b,HUD_PAGE*16
        ld      c,0
        call    crtc_set
        jr      loop
do_border:
        ld      a,#4C               ; έντονο κόκκινο
        call    border_set
        jr      loop

; crtc_set — B = R12 (σελίδα + ψηλά bits offset), C = R13 (χαμηλά bits)
crtc_set:
        push    bc
        ld      bc,CRTC_SEL + 12
        out     (c),c
        pop     bc
        push    bc
        ld      a,b
        ld      bc,CRTC_VAL
        ld      c,a
        out     (c),c
        ld      bc,CRTC_SEL + 13
        out     (c),c
        pop     bc
        ld      a,c
        ld      bc,CRTC_VAL
        ld      c,a
        out     (c),c
        ret

; border_set — A = τιμή υλικού χρώματος
border_set:
        ld      b,a
        ld      bc,GA_PORT + GA_BORDER
        out     (c),c
        ld      bc,GA_PORT
        ld      c,a
        out     (c),c
        ret

; ---------------------------------------------------------------------------
; fill_play — μαύρο, με μία κάθετη γραμμή σε γνωστή στήλη.
; ---------------------------------------------------------------------------
fill_play:
        ld      hl,#C000
        ld      de,#C001
        ld      bc,#3FFF
        ld      (hl),0
        ldir
        ld      c,0
fp_lp:
        push    bc
        ld      a,c
        ld      c,LINE_BYTE
        call    scr_addr
        ld      a,#FF
        ld      (de),a
        pop     bc
        inc     c
        ld      a,c
        cp      SCR_H
        jr      nz,fp_lp
        ret

; fill_hud — η σελίδα 2, συμπαγής, ώστε να ξεχωρίζει αμέσως αν εμφανιστεί.
fill_hud:
        ld      hl,#8000
        ld      de,#8001
        ld      bc,#3FFF
        ld      (hl),#55
        ldir
        ret

        include "../src/screen.asm"
        include "../src/hw.asm"

pal_test:
        db  0, 1,11,23,13,26,24,15
        db  6,18,10, 5,25, 3,19,16

cam_off:     dw 0                   ; offset σε λέξεις (2 bytes) του CRTC
split_delay: dw 1730                ; ~γραμμή 160, βαθμονομημένο στον εξομοιωτή
split_mode:  db 0
