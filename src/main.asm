; main.asm — το παιχνίδι, ολόκληρο, σε ένα binary.
;
; Ως το βήμα 12 τα δύο μισά ζούσαν χωριστά: το tests/uitest.asm έδενε τον
; renderer με το build mode, το tests/simtest.asm την οικονομία με τον τροχό,
; και ΚΑΝΕΝΑ δεν έδενε και τα δύο. Αυτό σημαίνει ότι το συνολικό μέγεθος
; κώδικα κάτω από το &4000 ήταν αμέτρητο και καμία κλήση από το ένα μισό στο
; άλλο δεν είχε ποτέ μεταγλωττιστεί.
;
; Ο ΒΡΟΧΟΣ. Ενα frame είναι: μία θέση τροχού, μία φέτα λίστας βρώμικων, ένα
; ui_tick. Ο τροχός είναι η προσομοίωση (§7.2), η λίστα είναι η οθόνη (§8.5)
; και το ui_tick είναι ο παίκτης (§9.1). Και τα τρία έχουν ταβάνι, οπότε το
; frame δεν μπορεί να ξεφύγει — αυτό είναι όλος ο κανόνας 1 του §7.1.

        buildsna
        bankset 0
        org     #0100
        run     start

        include "const.asm"
        include "../build/sprite_consts.asm"
        include "../build/layout.asm"

FLIPTAB     equ G_flip_mode0
PPI_B       equ #F500

start:
        di
        ld      sp,#0100
        call    hw_mode0
        ld      hl,G_palette_fw
        call    pal_set
        xor     a
        call    pal_border
        call    game_new
        ; fall through

; ---------------------------------------------------------------------------
; main_loop — ένα frame.
; ---------------------------------------------------------------------------
main_loop:
        ld      bc,PPI_B
ml_low:
        in      a,(c)
        rra
        jr      c,ml_low
ml_high:
        in      a,(c)
        rra
        jr      nc,ml_high
        call    wheel_tick
        call    dirty_tick
        call    ui_tick
        jr      main_loop

        include "screen.asm"
        include "blit.asm"
        include "tiles.asm"
        include "object.asm"
        include "dirty.asm"
        include "hud.asm"
        include "view.asm"
        include "ghost.asm"
        include "input.asm"
        include "build.asm"
        include "graph.asm"
        include "route.asm"
        include "ui.asm"
        include "newgame.asm"
        include "entity.asm"
        include "econ.asm"
        include "jobs.asm"
        include "needs.asm"
        include "ship.asm"
        include "wheel.asm"
        include "hw.asm"

        org     #8000
        incbin  "../build/page2.bin"

        bankset 1
        org     #0000
        incbin  "../build/world_new.bin"
        org     #8000
        incbin  "../build/bank6.bin"
        org     #C000
        incbin  "../build/bank7.bin"
