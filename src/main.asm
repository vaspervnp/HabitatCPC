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
HAS_DISC    equ 1                        ; το ui.asm δίνει S/L μόνο εδώ (§11)

start:
        di
        ld      sp,#0100
        call    hw_mode0
        ld      hl,G_palette_fw
        call    pal_set
        ; Ο πλανήτης ζει στα τέσσερα bytes που άφησε η γεννήτρια στην τράπεζα 6
        ; (§5.7): τέσσερα pens εδάφους, τίποτε άλλο.
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        ld      a,(G_worldinfo + 2)
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        call    pal_planet
        xor     a
        call    pal_border
        ; Ο renderer παρουσιάζεται στην προσομοίωση: από εδώ και πέρα κάθε
        ; αλλαγή που φαίνεται σπρώχνεται στη λίστα βρώμικων (§8.5).
        ld      hl,dirty_push
        ld      (wh_hook),hl
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
        ld      a,(wh_built)
        or      a
        call    nz,ml_built
        ld      a,(wh_slot)
        or      a
        call    z,ml_hud
        call    dirty_tick
        call    ui_tick
        jp      main_loop

; ml_built — ένα κτίριο τελείωσε. Πλήρης σχεδίαση, 41 frames.
;
; Το §6.9 ζητά αποκάλυψη σε οκτώ κομμάτια, ένα τεταρτημόριο ανά frame. Αυτό
; είναι μια στιγμιαία παύση 0,8 δευτερολέπτου αντί για αυτό — σπάνια (μία φορά
; ανά κτίριο) και ειλικρινής· η λίστα βρώμικων ΔΕΝ είναι φθηνότερη εδώ, γιατί
; ένα tile κάτω από θόλο κοστίζει 99.840 us και ο θόλος έχει δεκαέξι.
ml_built:
        xor     a
        ld      (wh_built),a
        call    ui_hide
        call    view_draw
        jp      ui_show

; ml_hud — το HUD μία φορά ανά περιστροφή τροχού, δηλαδή ανά 320 ms.
;
; Ως τώρα ξαναγραφόταν μόνο σε ενέργεια του παίκτη: το νερό έπεφτε 60 -> 0 και
; η μπάρα δεν κουνιόταν.
;
; ΤΟ ΦΑΝΤΑΣΜΑ ΔΕΝ ΑΓΓΙΖΕΤΑΙ. Το HUD ζει στις γραμμές 160-199 και το φάντασμα
; στο κάδρο, άρα δεν πατά ο ένας τον άλλον· ένα ui_hide/ui_show εδώ έσβηνε τον
; κέρσορα για τρία frames κάθε 320 ms, που φαίνεται σαν να τρεμοπαίζει.
; Χρειάζεται μόνο το ui_dirty, γιατί το hud_draw αφήνει τις σειρές 3-4 κενές.
ml_hud:
        call    hud_draw
        call    ui_dirty
        jp      ui_panel

        include "screen.asm"
        include "blit.asm"
        include "tiles.asm"
        include "object.asm"
        include "dirty.asm"
        include "hud.asm"
        include "view.asm"
        include "ghost.asm"
        include "input.asm"
        include "graph.asm"
        include "ui.asm"
        include "entity.asm"
        include "econ.asm"
        include "jobs.asm"
        include "needs.asm"
        include "ship.asm"
        include "wheel.asm"
        include "fdc.asm"
        include "save.asm"
        include "hw.asm"
        include "newgame.asm"
zz_bank0_end:

; --- ό,τι τρέχει από την ΤΡΑΠΕΖΑ 2 -----------------------------------------
; Η τράπεζα 2 φαίνεται πάντα στο &8000, άρα ο κώδικας εκεί είναι απλώς κώδικας.
; Διαλέχτηκαν τρία αρθρώματα που δεν είναι στον καυτό δρόμο και που δεν καλούν
; το ένα το άλλο με jr: οι κλήσεις ανάμεσα στις δύο περιοχές είναι απόλυτες.
        org     PAGE2_CODE
        include "build.asm"
        include "route.asm"
zz_page2_end:

; --- τα δύο κομμάτια του παιχνιδιού, για τον δίσκο ------------------------
; Το AMSDOS δίνει ΜΙΑ διεύθυνση φόρτωσης ανά αρχείο, και το παιχνίδι ζει σε δύο
; ασυνεχείς περιοχές: τον κώδικα της τράπεζας 0 και τον κώδικα της τράπεζας 2.
        save    "../build/game.bin",  #0100, zz_bank0_end - #0100
        save    "../build/game2.bin", PAGE2_CODE, zz_page2_end - PAGE2_CODE

        org     #8000
        incbin  "../build/page2.bin"
        org     #7000
        incbin  "../build/bank1.bin"     ; εικονίδια m και l, πάνω από το DIST

        bankset 1
        org     #0000
        incbin  "../build/world_new.bin"
        org     #8000
        incbin  "../build/bank6.bin"
        org     #C000
        incbin  "../build/bank7.bin"
