; tiles.asm — το πέρασμα εδάφους (DESIGN.md §8.3)
;
; Το μόνο κομμάτι που ξαναζωγραφίζεται σε σκρολάρισμα. Διαβάζει το επίπεδο
; κόσμου από την τράπεζα 4 και σχεδιάζει 20x10 tiles.
;
; Η τράπεζα 4 είναι σελιδοποιημένη σε ΟΛΟ το πέρασμα και καμία άλλη δεν
; χρειάζεται: τα γραφικά εδάφους, ο tile_ptr, ο tile_variants και το
; ore_overlay ζουν όλα στη σελίδα 2, που είναι πάντα ορατή. Κανένα
; out (c),c μέσα στον βρόχο.

WORLD_BASE  equ #4000          ; η τράπεζα 4 στο παράθυρο
WORLD_W     equ 128
VIEW_TW     equ 20             ; tiles οριζόντια στο κάδρο
VIEW_TH     equ 10             ; tiles κάθετα

; ---------------------------------------------------------------------------
; tile_addr — διεύθυνση στο επίπεδο κόσμου για (tx, ty).
; In :  B = tx, C = ty  (προσημασμένα, -64..+63)
; Out:  HL = WORLD_BASE + ((ty+64)*128) + (tx+64)
;
; Το *128 δεν θέλει πολλαπλασιασμό: v = ty+64 είναι 0..127, οπότε το γινόμενο
; είναι v<<7 — ψηλό byte v>>1, χαμηλό (v&1)<<7.
; ---------------------------------------------------------------------------
tile_addr:
        ld      a,c
        add     a,64
        srl     a                   ; v>>1, το κρατούμενο είναι το v&1
        ld      h,a
        ld      a,0
        rra                         ; κρατούμενο -> bit 7
        ld      l,a
        ld      a,b
        add     a,64                ; 0..127, χωράει στα bits 0-6
        or      l
        ld      l,a
        ld      a,h
        add     a,WORLD_BASE/256
        ld      h,a
        ret

; ---------------------------------------------------------------------------
; tile_draw_all — όλο το κάδρο από (cam_tx, cam_ty), που είναι το ΠΑΝΩ-ΑΡΙΣΤΕΡΑ
; ορατό tile.
;
; tile_draw_rect — μόνο ένα ορθογώνιο από tiles του κάδρου: (td_c0, td_r0) και
; (td_nc, td_nr). Αυτό είναι όλο το σκρολάρισμα — μία στήλη ή μία σειρά.
; ---------------------------------------------------------------------------
tile_draw_all:
        xor     a
        ld      (td_c0),a
        ld      (td_r0),a
        ld      a,VIEW_TW
        ld      (td_nc),a
        ld      a,VIEW_TH
        ld      (td_nr),a

tile_draw_rect:
        ld      a,(td_nr)
        or      a
        ret     z
        ld      (td_left),a
        ld      hl,td_r0
        ld      a,(cam_ty)
        add     a,(hl)
        ld      (td_ty),a
        ld      a,(td_r0)
        ld      (td_row),a

td_next_row:
        ; --- δείκτης κόσμου και διεύθυνση οθόνης για την αρχή της σειράς ---
        ld      hl,td_c0
        ld      a,(cam_tx)
        add     a,(hl)
        ld      b,a
        ld      a,(td_ty)
        ld      c,a
        call    tile_addr
        ld      (t_wptr),hl
        ld      a,(td_c0)
        add     a,a
        add     a,a                 ; col*4 bytes
        ld      c,a
        ld      a,(td_row)
        add     a,a
        add     a,a
        add     a,a
        add     a,a                 ; row*16 γραμμές
        call    scr_addr
        ld      (t_sptr),de

        ld      a,(td_nc)
        ld      (td_col),a
td_next_col:
        call    tile_one
        ld      hl,(t_wptr)
        inc     hl
        ld      (t_wptr),hl
        ld      hl,(t_sptr)
        ld      de,TILE_W
        add     hl,de
        ld      a,h
        and     #C7                 ; το δαχτυλίδι: p mod 2048 (screen.asm)
        ld      h,a
        ld      (t_sptr),hl
        ld      a,(td_col)
        dec     a
        ld      (td_col),a
        jr      nz,td_next_col

        ld      a,(td_ty)
        inc     a
        ld      (td_ty),a
        ld      a,(td_row)
        inc     a
        ld      (td_row),a
        ld      a,(td_left)
        dec     a
        ld      (td_left),a
        jr      nz,td_next_row
        ret

; ---------------------------------------------------------------------------
; tile_one — ένα tile: κλάση, παραλλαγή, blit, και φλέβα αν υπάρχει.
; ---------------------------------------------------------------------------
tile_one:
        ld      hl,(t_wptr)
        ld      a,(hl)
        ld      (t_cur),a
        and     7
        ld      (t_cls),a
        ; πόσες παραλλαγές έχει η κλάση;
        ld      e,a
        ld      d,0
        ld      hl,G_tile_variants
        add     hl,de
        ld      a,(hl)
        cp      16
        jr      z,to_auto
        ; --- μη autotiled: η παραλλαγή είναι τα bits decor, με mask ---
        ; Χωρίς το mask, decor 2-3 σε crater δείχνει στα tiles της ΕΠΟΜΕΝΗΣ
        ; κλάσης — ο crater και το foundation έχουν μόνο 2 (SPRITES.md §3).
        dec     a
        ld      e,a
        ld      a,(t_cur)
        rlca
        rlca                        ; decor στα bits 0-1
        and     3
        and     e
        jr      to_have_var
to_auto:
        call    tile_autotile       ; -> A = μάσκα 0..15
to_have_var:
        ; --- πηγή = tile_ptr[class] + variant*TILE_SZ ---
        ld      l,a
        ld      h,0
        add     hl,hl
        add     hl,hl
        add     hl,hl
        add     hl,hl
        add     hl,hl
        add     hl,hl               ; *64
        ex      de,hl               ; DE = variant*64
        ld      a,(t_cls)
        add     a,a
        ld      l,a
        ld      h,0
        ld      bc,G_tile_ptr
        add     hl,bc
        ld      a,(hl)
        inc     hl
        ld      h,(hl)
        ld      l,a                 ; HL = tile_ptr[class]
        add     hl,de               ; + variant*64
        ld      de,(t_sptr)
        call    blit_tile

        ; --- φλέβα: μόνο σε βουνό με τον πόρο αναμμένο ---
        ld      a,(t_cls)
        cp      3                   ; MOUNTAIN
        ret     nz
        ld      a,(t_cur)
        and     8                   ; bit πόρου
        ret     z
        ld      a,(t_cur)
        rlca
        rlca
        and     1                   ; decor & 1 -> 2 παραλλαγές
        ld      l,a
        ld      h,0
        add     hl,hl               ; *2
        add     hl,hl
        add     hl,hl
        add     hl,hl
        add     hl,hl
        add     hl,hl
        add     hl,hl               ; *128 = ORE_OVL_SZ
        ld      de,G_ore_overlay
        add     hl,de
        ld      de,(t_sptr)
        ld      b,TILE_W
        ld      c,TILE_H
        jp      blit_mask

; ---------------------------------------------------------------------------
; tile_autotile — μάσκα γειτόνων για το tile στο (t_wptr).
; bit0 = N, bit1 = E, bit2 = S, bit3 = W· μπαίνει όταν ο γείτονας είναι ΙΔΙΑΣ
; ΟΙΚΟΓΕΝΕΙΑΣ. Το βαθύ νερό μετράει ως νερό, αλλιώς κάθε λίμνη αποκτά ακτή
; γύρω από το βαθύ της κομμάτι (SPRITES.md §3).
; Out: A = 0..15
; ---------------------------------------------------------------------------
tile_autotile:
        ld      a,(t_cls)
        call    tile_family
        ld      (t_fam),a

        ld      hl,(t_wptr)
        ld      de,0-WORLD_W
        add     hl,de
        call    ta_same             ; N
        rra                         ; κρατούμενο -> bit 7 ...
        ld      b,a                 ; ... το μαζεύουμε ανάποδα και γυρίζουμε

        ld      hl,(t_wptr)
        inc     hl
        call    ta_same             ; E
        ld      a,b
        rra
        ld      b,a

        ld      hl,(t_wptr)
        ld      de,WORLD_W
        add     hl,de
        call    ta_same             ; S
        ld      a,b
        rra
        ld      b,a

        ld      hl,(t_wptr)
        dec     hl
        call    ta_same             ; W
        ld      a,b
        rra
        ; τα τέσσερα bits κάθονται στα 7..4· κατέβασέ τα
        rlca
        rlca
        rlca
        rlca
        and     15
        ret

; ta_same — κρατούμενο = 1 αν το (HL) είναι ίδιας οικογένειας με το t_fam.
;
; Ο γείτονας μπορεί να πέσει ΕΞΩ από το επίπεδο: στη γραμμή -64 ο βορράς είναι
; κάτω από το #4000, στο tile (-64,-64) η δύση είναι το #3FFF — δηλαδή ο ΚΩΔΙΚΑΣ
; της τράπεζας 0, όχι ο κόσμος. Ένας έλεγχος ότι το H είναι μέσα στο παράθυρο
; τα πιάνει όλα μαζί, σε κάθε άκρη και γωνία, χωρίς λογιστική ανά σειρά και
; ανά στήλη. Εκτός κόσμου διαβάζεται ως ο ΕΑΥΤΟΣ του tile, ώστε να μη
; ζωγραφιστεί ακτή στην άκρη του κόσμου.
ta_same:
        ld      a,h
        cp      WORLD_BASE/256
        jr      c,ta_yes            ; κάτω από το παράθυρο
        cp      (WORLD_BASE+#4000)/256
        jr      nc,ta_yes           ; πάνω από το παράθυρο
        ld      a,(hl)
        and     7
        cp      5                   ; tile_family, ξετυλιγμένο: καλείται 4 φορές
        jr      nz,ta_cmp           ; ανά tile, και το call+ret κόστιζε όσο ο
        dec     a                   ; ίδιος ο έλεγχος
ta_cmp:
        ld      hl,t_fam
        cp      (hl)
        jr      z,ta_yes
        or      a                   ; καθάρισε το κρατούμενο
        ret
ta_yes:
        scf
        ret

; tile_family — A = κλάση -> A = οικογένεια.
; Μόνο ΕΝΑ ζευγάρι μοιράζεται οικογένεια: το βαθύ νερό (5) μετράει ως νερό (4),
; αλλιώς κάθε λίμνη αποκτά ακτή γύρω από το βαθύ της κομμάτι (SPRITES.md §3).
; Πίνακας οκτώ θέσεων θα κόστιζε και lookup και έναν δείκτη· τρεις εντολές όχι.
tile_family:
        cp      5
        ret     nz
        dec     a
        ret

; ---------------------------------------------------------------------------
; blit_tile — 4 bytes x 16 γραμμές, αδιαφανές. Ο πιο καυτός βρόχος του παιχνιδιού.
; In: HL = πηγή, DE = οθόνη (πάνω-αριστερά). Το DE διατηρείται ανά γραμμή.
;
; Το y ενός tile είναι πάντα πολλαπλάσιο του 16, άρα και του 8: κάθε tile πέφτει
; ΑΚΡΙΒΩΣ σε δύο σειρές χαρακτήρων των 8 γραμμών. Μέσα στη σειρά η επόμενη
; γραμμή είναι +#800, δηλαδή D += 8 — χωρίς κλήση, χωρίς έλεγχο.
;
; Το BC μπαίνει μία φορά: το ldi απλώς το μειώνει και κανείς δεν το κοιτά.
;
; ΠΡΟΣΟΧΗ — εδώ κρύφτηκε σφάλμα. Το ldi κάνει inc de, άρα όταν τα 4 bytes
; πατάνε σε όριο 256 (E >= #FD) το E γυρίζει και το ΚΡΑΤΟΥΜΕΝΟ ΜΠΑΙΝΕΙ ΣΤΟ D.
; Μια πρώτη εκδοχή κρατούσε μόνο το E σε ixl και το επανέφερε· το D έμενε
; αυξημένο και μετά από 16 γραμμές η διεύθυνση έγραφε μέσα στον κώδικα και
; στη στοίβα. Σώσε ΟΛΟΚΛΗΡΟ το DE — 21 T-states που δεν διαπραγματεύονται.
; ---------------------------------------------------------------------------
blit_tile:
        ld      bc,64               ; μετρητής του ldi· κανείς δεν τον κοιτά
        repeat  8
        push    de                  ; ΟΛΟΚΛΗΡΟ το DE, όχι μόνο το E
        ldi
        ldi
        ldi
        ldi
        pop     de
        ld      a,d
        add     a,8                 ; +#800 = επόμενη γραμμή της ίδιας σειράς
        ld      d,a
        rend
        ; πέρασμα στη δεύτερη σειρά χαρακτήρων: -#4000 +#50
        ld      a,d
        sub     #40
        ld      d,a
        ld      a,e
        add     a,SCR_W
        ld      e,a
        ld      a,d
        adc     a,0
        and     #C7                 ; και εδώ το δαχτυλίδι — μία εντολή ανά tile
        ld      d,a
        repeat  8
        push    de
        ldi
        ldi
        ldi
        ldi
        pop     de
        ld      a,d
        add     a,8
        ld      d,a
        rend
        ret

; --- μεταβλητές ------------------------------------------------------------
cam_tx:     db 0                ; πάνω-αριστερά ορατό tile, προσημασμένο
cam_ty:     db 0
td_ty:      db 0
td_row:     db 0
td_col:     db 0
td_c0:      db 0                ; το ορθογώνιο μέσα στο κάδρο, σε tiles
td_r0:      db 0
td_nc:      db VIEW_TW
td_nr:      db VIEW_TH
td_left:    db 0
t_wptr:     dw 0
t_sptr:     dw 0
t_cur:      db 0                ; το world byte του τρέχοντος tile
t_cls:      db 0
t_fam:      db 0
