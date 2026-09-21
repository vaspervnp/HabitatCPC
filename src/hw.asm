; hw.asm — gate array: mode, ROM, παλέτα
;
; Το `palette_fw` των assets δίνει **firmware** colour numbers (0..26). Ο gate
; array θέλει **hardware** τιμές. Η μετάφραση δεν υπάρχει στα assets — είναι
; δουλειά της μηχανής, και ζει εδώ.

; ---------------------------------------------------------------------------
; hw_mode0 — Mode 0, και τα δύο ROM εκτός. Από εδώ και πέρα η μνήμη είναι δική μας.
; ---------------------------------------------------------------------------
hw_mode0:
        ld      bc,GA_PORT + RMR_MODE0
        out     (c),c
        ret

; ---------------------------------------------------------------------------
; pal_set — στήνει και τα 16 pens από πίνακα firmware αριθμών.
; In:  HL = 16 bytes, pen 0..15
; ---------------------------------------------------------------------------
pal_set:
        ld      e,0                 ; pen
ps_loop:
        ld      a,(hl)
        inc     hl
        push    hl
        ld      hl,fw_to_hw
        ld      d,0
        push    de
        ld      e,a
        add     hl,de
        ld      a,(hl)              ; hardware τιμή
        pop     de
        or      GA_INK
        ld      b,a                 ; κρατάμε το χρώμα
        ld      a,e
        or      GA_PEN
        ld      c,a
        ld      a,b
        ld      b,GA_PORT/256
        out     (c),c               ; επιλογή pen
        ld      c,a
        out     (c),c               ; τιμή χρώματος
        pop     hl
        inc     e
        ld      a,e
        cp      16
        jr      nz,ps_loop
        ret

; ---------------------------------------------------------------------------
; pal_border — χρώμα περιγράμματος από firmware αριθμό στον A.
; ---------------------------------------------------------------------------
pal_border:
        ld      hl,fw_to_hw
        ld      e,a
        ld      d,0
        add     hl,de
        ld      a,(hl)
        or      GA_INK
        ld      b,GA_PORT/256
        ld      c,GA_BORDER
        out     (c),c
        ld      c,a
        out     (c),c
        ret

; firmware colour number -> hardware τιμή (χωρίς το bit #40)
; 27 χρώματα· ό,τι είναι πάνω από 26 δεν υπάρχει.
fw_to_hw:
        db  #14,#04,#15,#1C,#18,#1D,#0C,#05,#0D
        db  #16,#06,#17,#1E,#00,#1F,#0E,#07,#0F
        db  #12,#02,#13,#1A,#19,#1B,#10,#11,#01
