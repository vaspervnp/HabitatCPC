; sndtest.asm — ο ήχος σε πραγματικό Z80, με τον AY να απαντά.
;
; Η δοκιμή δεν κοιτά τη μνήμη του παιχνιδιού αλλά τους ΚΑΤΑΧΩΡΗΤΕΣ ΤΟΥ AY, που
; ο εξομοιωτής τους δίνει από το cpcemu_psg_reg. Ετσι ελέγχεται η αλυσίδα
; ολόκληρη: πίνακας εφέ -> snd_tick -> PPI -> PSG. Αν σπάσει το πρωτόκολλο του
; PPI — που είναι το ίδιο με του πληκτρολογίου και εξίσου ανελέητο — δεν φτάνει
; τίποτα στον ήχο και η δοκιμή το βλέπει.
;
; Κάθε είσοδος τελειώνει με done_flag = #5A, οπότε η Python πλευρά ελέγχει
; ΑΚΡΙΒΩΣ πόσα tick έγιναν: κανένας ήχος δεν εξαρτάται από το πότε προλαβαίνει
; το frame.

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
        call    snd_init
        ld      a,#5A
        ld      (done_flag),a
hang:   jr      hang

; --- do_play: παίξε το εφέ (req) ---
do_play:
        ld      a,(req)
        call    snd_play
        ld      a,#5A
        ld      (done_flag),a
dp_hang: jr     dp_hang

; --- do_tick: (req) φορές snd_tick, για βήμα-βήμα και για μέτρηση κόστους ---
do_tick:
        ld      a,(req)
        ld      (dt_n),a
dt_lp:
        call    snd_tick
        ld      a,(dt_n)
        dec     a
        ld      (dt_n),a
        jr      nz,dt_lp
        ld      a,#5A
        ld      (done_flag),a
dt_hang: jr     dt_hang

; --- do_bulk: (req2) x 250 snd_tick σε ΜΙΑ είσοδο ---
; Το entry() μετράει ολόκληρα frames, οπότε κάθε κλήση χρεώνεται ως ένα frame
; παραπάνω· με 4.000 tick σε μία κλήση το σφάλμα πέφτει κάτω από 6%.
do_bulk:
        ld      a,(req2)
        ld      (db_n),a
dbk_out:
        ld      b,250
dbk_in:
        push    bc
        call    snd_tick
        pop     bc
        djnz    dbk_in
        ld      a,(db_n)
        dec     a
        ld      (db_n),a
        jr      nz,dbk_out
        ld      a,#5A
        ld      (done_flag),a
dbk_hang: jr    dbk_hang

; --- do_busy: (req) φορές «παίξε το (req2) και τρέξ' το ως το τέλος» ---
; Για μέτρηση: ένα εφέ 24 tick δεν φτάνει για να μετρηθεί σε frames των 20 ms.
do_busy:
        ld      a,(req)
        ld      (db_n),a
db_lp:
        ld      a,(req2)
        call    snd_play
        ld      b,32
db_tk:
        push    bc
        call    snd_tick
        pop     bc
        djnz    db_tk
        ld      a,(db_n)
        dec     a
        ld      (db_n),a
        jr      nz,db_lp
        ld      a,#5A
        ld      (done_flag),a
db_hang: jr     db_hang

; --- do_off: σιωπή ---
do_off:
        call    snd_off
        ld      a,#5A
        ld      (done_flag),a
do_hang: jr     do_hang

; --- do_keys: σάρωση πληκτρολογίου ΜΕΤΑ από ήχο — μοιράζονται το PPI ---
do_keys:
        ld      a,(req)
        ld      (dk_n),a
dk_lp:
        call    in_scan
        call    snd_tick
        ld      a,(dk_n)
        dec     a
        ld      (dk_n),a
        jr      nz,dk_lp
        ld      a,#5A
        ld      (done_flag),a
dk_hang: jr     dk_hang

req:        db 0
req2:       db 0
db_n:       db 0
dt_n:       db 0
dk_n:       db 0
done_flag:  db 0

        include "../src/input.asm"
        include "../src/sound.asm"
