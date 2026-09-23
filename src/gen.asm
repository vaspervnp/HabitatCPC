; gen.asm — η γεννήτρια κόσμου ως ΞΕΧΩΡΙΣΤΟ ΦΟΡΤΩΜΑ.
;
; Ο κώδικας του παιχνιδιού πιάνει 13,2 KB από τα 16,1 της τράπεζας 0 και η
; γεννήτρια θέλει άλλα 2,9: δεν χωρούν μαζί (DESIGN §4.2). Τρέχει μία φορά, πριν
; υπάρξει τίποτε άλλο, και το παιχνίδι φορτώνεται από πάνω της.
;
; ΕΠΙΣΤΡΕΦΕΙ στον φορτωτή: το AMSDOS πρέπει να είναι ακόμη ζωντανό για να
; φορτωθεί το παιχνίδι μετά. Γι' αυτό δεν αγγίζει το #A700 και πάνω, όπου ο
; χώρος εργασίας του.
;
; ΓΙΑΤΙ ΣΤΟ #8000 ΚΑΙ ΟΧΙ ΣΤΟ #0100. Οσο ζει το firmware, το κάτω ROM είναι
; αναμμένο: ό,τι γραφτεί στο #0000-#3FFF μπαίνει μεν στη RAM, αλλά ο
; επεξεργαστής διαβάζει εκεί ROM. Κώδικας που πρέπει να ΤΡΕΞΕΙ πριν σβήσει το
; firmware ζει πάνω από το #4000. Το #8000-#8BFF είναι ελεύθερο ως την τελευταία
; στιγμή — τα δεδομένα της τράπεζας 2 έρχονται εκεί αφού τελειώσει η γεννήτρια.

        org     #8000

; ΤΟ ΠΡΩΤΟ BYTE ΠΡΕΠΕΙ ΝΑ ΕΙΝΑΙ ΕΝΤΟΛΗ. Ο φορτωτής ξέρει μόνο μία διεύθυνση —
; εκείνη που φόρτωσε — και εκεί πηδά. Χωρίς αυτό το άλμα, το πρώτο byte του
; αρχείου είναι ό,τι έτυχε να βγάλει το πρώτο include: το gen_tables.asm
; εκπέμπει ΠΙΝΑΚΕΣ, και το `call` έτρεχε τον πίνακα. Επέστρεφε κιόλας, αθόρυβα,
; με την τράπεζα 4 άδεια — ο κόσμος έβγαινε ένα ατέλειωτο χωράφι.
        jp      gen_entry

        include "const.asm"
        include "../build/sprite_consts.asm"
        include "../build/layout.asm"
        include "../build/gen_tables.asm"

; ---------------------------------------------------------------------------
; gen_entry — παράγει το επίπεδο στην τράπεζα 4 και γυρίζει.
;
; ΤΟ SEED ΔΕΝ ΕΙΝΑΙ ΜΕΡΟΣ ΤΗΣ ΓΕΝΕΣΗΣ. Το §5.1 απαγορεύει στη ΓΕΝΕΣΗ να κοιτάξει
; τον καταχωρητή R ή τον μετρητή frames — αλλιώς δύο εκκινήσεις με το ίδιο seed
; δεν δίνουν τον ίδιο κόσμο. Το να ΔΙΑΛΕΞΕΙΣ seed από τον R είναι άλλο πράγμα:
; είναι ακριβώς αυτό που κάνει κάθε νέο παιχνίδι διαφορετικό, και το seed
; φυλάγεται ώστε ο κόσμος να ξαναγίνεται (§11).
; ---------------------------------------------------------------------------
gen_entry:
        di
        ld      a,r
        ld      l,a
        ld      a,r
        add     a,a
        add     a,a
        add     a,a
        xor     l
        ld      h,a
        ld      a,h
        or      l
        jr      nz,ge_seed
        ld      hl,#ACE1                ; το μηδέν είναι απορροφητικό στο LFSR
ge_seed:
        ld      (gen_seed),hl
        ; Ο ΠΛΑΝΗΤΗΣ ΒΓΑΙΝΕΙ ΑΠΟ ΤΟ SEED. Οχι από τον R δεύτερη φορά: το §5.1
        ; θέλει τον κόσμο καθαρή συνάρτηση του seed, και ο πλανήτης είναι
        ; είσοδος της γένεσης (§5.7) — αν διαλεγόταν χωριστά, δύο παιχνίδια με
        ; το ίδιο seed θα έδιναν άλλο κόσμο. Ετσι τα δύο bytes του seed είναι
        ; ακόμη ΟΛΟΣ ο κόσμος, πλανήτης μέσα.
        ld      a,h
        xor     l
        and     3
        ld      (gen_planet),a
        ld      c,a
        ; Το seed ΕΠΙΒΙΩΝΕΙ της γεννήτριας. Σε τέσσερα bytes της τράπεζας 6,
        ; που φορτώθηκε πριν από εδώ και δεν ξαναγράφεται: αυτό το αρχείο
        ; σβήνεται σε λίγο από τον κώδικα του παιχνιδιού, και χωρίς αυτά το
        ; παιχνίδι δεν ξέρει ποτέ από ποιο seed βγήκε ο κόσμος του (§11).
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        ld      (G_worldinfo),hl
        ld      a,c
        ld      (G_worldinfo + 2),a
        ld      a,GEN_VERSION
        ld      (G_worldinfo + 3),a
        ld      bc,GA_PORT + PAGE_B4
        out     (c),c
        call    mus_init
        call    worldgen_run
        call    mus_off
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        ei
        ret

; --- η μπάρα προόδου (§5.9) -----------------------------------------------
; Η γένεση κρατά 13,5 δευτερόλεπτα και ως τώρα η οθόνη δεν έλεγε τίποτα: ο
; παίκτης κοίταζε το «Ready» του BASIC και το περίγραμμα να αλλάζει χρώμα.
;
; Η οθόνη εδώ είναι ακόμη του firmware — MODE 1, που την έστησε ο φορτωτής —
; και η μπάρα γράφεται ΚΑΤΕΥΘΕΙΑΝ στη μνήμη της: τα ROM είναι αναμμένα, αλλά οι
; ΕΓΓΡΑΦΕΣ περνούν πάντα στη RAM. Καμία κλήση firmware, κανένα ρίσκο.
;
; 128 σειρές, 64 bytes μπάρα: μία κίνηση ανά δύο σειρές.
WG_PROGRESS equ 1
GEN_BAR     equ SCR_BASE + 16 * 80 + 8      ; χαρακτηρο-σειρά 16, κεντραρισμένη

wg_prog:
        push    af
        push    bc
        push    de
        push    hl
        srl     a
        jr      c,wp_done                   ; μόνο οι ζυγές σειρές
        ld      e,a
        ld      d,0
        ld      hl,GEN_BAR
        add     hl,de
        ld      b,8                         ; οι οκτώ γραμμές του χαρακτήρα
wp_lp:
        ld      (hl),#FF
        ld      a,h
        add     a,8                         ; +#800: επόμενη γραμμή του ίδιου
        ld      h,a                         ; χαρακτήρα
        djnz    wp_lp
wp_done:
        pop     hl
        pop     de
        pop     bc
        pop     af
        ret

; --- η μουσική της αναμονής (§9.5) -----------------------------------------
; Δεκατρεισήμισι δευτερόλεπτα σιωπής είναι πολλά. Ο ήχος του παιχνιδιού ζει στην
; τράπεζα 2, που ΔΕΝ υπάρχει ακόμη όταν τρέχει η γεννήτρια — η PAGE2.BIN κάθεται
; σε πρόχειρο χώρο και αντιγράφεται στο τέλος (§13.1). Οπότε η γεννήτρια έχει
; δικό της, μικρό παίκτη: δύο κανάλια, μία λίστα νότες το καθένα.
;
; ΤΟ ΡΟΛΟΙ ΕΙΝΑΙ Η ΙΔΙΑ Η ΓΕΝΝΗΣΗ. Οι διακοπές είναι κλειστές (το gen_entry
; κάνει di και δεν θα το αλλάξουμε: η σελιδοποίηση της τράπεζας 4 δεν θέλει
; παρέα), άρα δεν υπάρχει frame interrupt να χτυπά τον ρυθμό. Χτυπά ο βρόχος
; των πλακιδίων, ανά 32 πλακίδια — μετρημένα 541 us το πλακίδιο, άρα ~17 ms.
;
; Νότα: διάρκεια σε χτύπους, μετά περίοδος 16-bit (62500/Hz). Περίοδος 0 =
; παύση. Διάρκεια 0 = γύρνα στην αρχή.

; Η ΕΝΤΑΣΗ ΕΙΝΑΙ ΛΟΓΙΣΜΙΚΟ, ΟΧΙ ΦΑΚΕΛΟΣ ΥΛΙΚΟΥ. Ο AY έχει δικό του φάκελο και
; θα κόστιζε δύο εγγραφές τη νότα — αλλά τότε η ΕΝΤΑΣΗ ΔΕΝ ΦΑΙΝΕΤΑΙ ΣΤΟΥΣ
; ΚΑΤΑΧΩΡΗΤΕΣ (ο R8 λέει μόνο «χρησιμοποίησε φάκελο») και ούτε η δοκιμή ούτε ο
; renderer του tools/ayrender.py μπορούν να πουν τι ακούγεται. Εδώ κάθε δεύτερος
; χτύπος κατεβάζει την ένταση κατά ένα: 13 ως το 0 σε 26 χτύπους, μισό
; δευτερόλεπτο, και ό,τι ακούγεται το λένε οι καταχωρητές.

mus_init:
        ld      a,7                     ; μίκτης: τόνος σε A και C, θόρυβος off
        ld      e,#F9
        call    mus_reg
        ld      a,8
        ld      e,0
        call    mus_reg
        ld      a,10
        ld      e,0
        call    mus_reg
        ld      hl,mus_a
        ld      (mus_pa),hl
        ld      hl,mus_c
        ld      (mus_pc),hl
        xor     a
        ld      (mus_ta),a
        ld      (mus_tc),a
        ld      (mus_va),a
        ld      (mus_vc),a
        ret

; mus_off — σιωπή. Μετά από εδώ ο ήχος ανήκει πάλι στο firmware.
mus_off:
        ld      a,7
        ld      e,#FF
        call    mus_reg
        ld      a,8
        ld      e,0
        call    mus_reg
        ld      a,10
        ld      e,0
        jp      mus_reg

; wg_beat — ένας χτύπος, από τον βρόχο των πλακιδίων του worldgen.asm.
wg_beat:
        push    af
        push    bc
        push    de
        push    hl
        ld      hl,mus_half
        ld      a,(hl)
        xor     1
        ld      (hl),a
        ld      hl,mus_ta
        ld      de,mus_pa
        ld      b,0                     ; κανάλι A -> καταχωρητές 0/1, ένταση 8
        call    mus_chan
        ld      hl,mus_tc
        ld      de,mus_pc
        ld      b,4                     ; κανάλι C -> καταχωρητές 4/5, ένταση 10
        call    mus_chan
        pop     hl
        pop     de
        pop     bc
        pop     af
        ret

; mus_chan — HL = μετρητής (+1 = ένταση), DE = δείκτης νότας, B = καταχωρητής
; περιόδου. Χαλάει τα πάντα εκτός από το B.
mus_chan:
        ld      a,(hl)
        or      a
        jr      z,mc_next
        dec     (hl)
        jr      mc_decay
mc_next:
        push    hl
        ex      de,hl
        ld      e,(hl)
        inc     hl
        ld      d,(hl)                  ; DE = η νότα
        push    hl                      ; δείκτης προς τον δείκτη
        ld      a,(de)                  ; διάρκεια
        or      a
        jr      nz,mc_play
        ld      de,mus_a                ; τέλος λίστας: από την αρχή
        ld      a,b
        or      a
        jr      z,mc_rew
        ld      de,mus_c
mc_rew:
        ld      a,(de)
mc_play:
        ld      c,a                     ; C = διάρκεια
        inc     de
        ld      a,(de)
        ld      (mus_lo),a
        inc     de
        ld      a,(de)
        ld      (mus_hi),a
        inc     de
        pop     hl
        ld      (hl),d
        dec     hl
        ld      (hl),e                  ; ο δείκτης στην επόμενη νότα
        pop     hl
        dec     c
        ld      (hl),c                  ; μετρητής ως την επόμενη
        ; --- η περίοδος στον AY ---
        ld      a,(mus_lo)
        ld      e,a
        ld      a,b
        push    bc
        call    mus_reg
        pop     bc
        ld      a,(mus_hi)
        ld      e,a
        ld      a,b
        inc     a
        push    bc
        call    mus_reg
        pop     bc
        ; --- νέα ένταση: 13, ή 0 αν είναι παύση ---
        inc     hl
        ld      a,(mus_lo)
        ld      c,a
        ld      a,(mus_hi)
        or      c
        ld      a,13
        jr      nz,mc_vol
        xor     a
mc_vol:
        ld      (hl),a
        dec     hl
        jr      mc_write
mc_decay:
        ld      a,(mus_half)
        or      a
        ret     nz                      ; σβήνει κάθε δεύτερο χτύπο
        inc     hl
        ld      a,(hl)
        or      a
        ret     z                       ; ήδη σιωπηλό
        dec     a
        ld      (hl),a
        dec     hl
mc_write:
        inc     hl
        ld      e,(hl)
        dec     hl
        ld      a,b
        srl     a
        add     a,8                     ; 0 -> R8, 4 -> R10
        jp      mus_reg

; mus_reg — A = καταχωρητής, E = τιμή. Το ίδιο πρωτόκολλο PPI με το sound.asm.
mus_reg:
        ld      bc,PPI_CTRL + #82
        out     (c),c
        ld      b,PPI_A / 256
        ld      c,a
        out     (c),c
        ld      bc,PPI_C + #C0
        out     (c),c
        ld      bc,PPI_C + #00
        out     (c),c
        ld      b,PPI_A / 256
        ld      c,e
        out     (c),c
        ld      bc,PPI_C + #80
        out     (c),c
        ld      bc,PPI_C + #00
        out     (c),c
        ret

mus_pa:     dw 0
mus_pc:     dw 0
mus_ta:     db 0                        ; μετρητής ως την επόμενη νότα...
mus_va:     db 0                        ; ...και η ένταση, ΑΜΕΣΩΣ μετά (HL+1)
mus_tc:     db 0
mus_vc:     db 0
mus_half:   db 0
mus_lo:     db 0
mus_hi:     db 0

; --- ο σκοπός ---------------------------------------------------------------
; Λα ελάσσονα, αργά. Η μελωδία σε χτύπους των 17 ms: 30 = μισό δευτερόλεπτο.
MU_A3   equ 284
MU_C4   equ 239
MU_D4   equ 213
MU_E4   equ 190
MU_F4   equ 179
MU_G4   equ 159
MU_A4   equ 142
MU_C5   equ 120
MU_D5   equ 106
MU_E5   equ 95
MU_A2   equ 568
MU_E2   equ 758
MU_F2   equ 716
MU_G2   equ 638

mus_a:
        db 30
        dw MU_A4
        db 30
        dw MU_C5
        db 45
        dw MU_E5
        db 15
        dw MU_D5
        db 60
        dw MU_C5
        db 30
        dw MU_A4
        db 30
        dw MU_E4
        db 60
        dw MU_A4
        db 30
        dw 0
        db 30
        dw MU_F4
        db 30
        dw MU_A4
        db 45
        dw MU_C5
        db 15
        dw MU_A4
        db 60
        dw MU_G4
        db 30
        dw MU_E4
        db 90
        dw MU_D4
        db 30
        dw 0
        db 0

mus_c:
        db 60
        dw MU_A2
        db 60
        dw MU_A2
        db 60
        dw MU_E2
        db 60
        dw MU_A2
        db 60
        dw MU_F2
        db 60
        dw MU_F2
        db 60
        dw MU_G2
        db 60
        dw MU_G2
        db 0

        include "worldgen.asm"

gen_end:
        save    "../build/gen.bin", #8000, gen_end - #8000
