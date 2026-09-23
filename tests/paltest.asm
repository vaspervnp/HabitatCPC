; paltest.asm — τα δεκαέξι pens στο χρώμα που ζητά η παλέτα.
;
; Η δοκιμή γεμίζει την οθόνη με μοτίβο όπου το pen n πιάνει n+1 bytes ανά
; περίοδο, διαβάζει το framebuffer και ζυγίζει τα χρώματα: το χρώμα με το
; μεγαλύτερο μερίδιο ΠΡΕΠΕΙ να είναι αυτό που ζητά το pen 15, και ούτω καθεξής.
; Ετσι ελέγχεται η ΜΕΤΑΦΡΑΣΗ firmware -> υλικό, που καμία άλλη δοκιμή δεν
; κοιτά: όλες συγκρίνουν αριθμούς pen, και ο πίνακας fw_to_hw βρίσκεται μετά.
;
; Το περίγραμμα μπαίνει επίτηδες σε χρώμα που ΔΕΝ υπάρχει στην παλέτα, ώστε τα
; pixel του να ξεχωρίζουν από τα μετρούμενα.

        buildsna
        bankset 0
        org     #0100
        run     start

        include "../src/const.asm"
        include "../build/sprite_consts.asm"
        include "../build/layout.asm"

start:
        di
        ld      sp,#0100
        call    hw_mode0
        ld      hl,G_palette_fw
        call    pal_set
        ld      a,(pl_border)
        call    pal_border
        ld      a,(pl_planet)
        cp      4
        jr      nc,pt_done              ; >= 4: χωρίς πλανήτη, σκέτη παλέτα
        call    pal_planet
pt_done:
        ld      a,#5A
        ld      (done_flag),a
hang:   jr      hang

pl_planet:  db #FF
pl_border:  db 6
done_flag:  db 0

        include "../src/hw.asm"

        org     #8000
        incbin  "../build/page2.bin"     ; planet_pens, palette_fw
