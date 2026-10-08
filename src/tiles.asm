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

        assert  WORLD_BASE == #4000             ; tile_addr, ta_same
        assert  TILE_SZ == 64 && ORE_OVL_SZ == 128
        ; ΜΙΑ ΣΕΛΙΔΑ ο καθένας (pack.py): το H είναι σταθερό, και η αναζήτηση
        ; θέλει μόνο το L — ανά tile, 200 φορές το κάδρο.
        assert  (G_tile_variants & 255) + 8 <= 256 && (G_tile_ptr & 255) + 16 <= 256
        assert  (G_ore_overlay & 255) == 0

; ---------------------------------------------------------------------------
; tile_addr — διεύθυνση στο επίπεδο κόσμου για (tx, ty).
; In :  B = tx, C = ty  (προσημασμένα, -64..+63)
; Out:  HL = WORLD_BASE + ((ty+64)*128) + (tx+64). Χαλάει μόνο το AF.
;
; Το *128 δεν θέλει πολλαπλασιασμό: v = ty+64 είναι 0..127, οπότε το γινόμενο
; είναι v<<7 — ψηλό byte v>>1, χαμηλό (v&1)<<7.
;
; ΕΞΩ ΑΠΟ ΤΟΝ ΚΟΣΜΟ (η κάμερα φτάνει μία στήλη πέρα από την άκρη) το tx+64
; έχει το bit 7, και το (v&1)<<7 μπαίνει με OR, όχι με πρόσθεση: το ίδιο
; σκουπίδι με πριν από το βήμα 56, για να βγαίνει η ίδια εικόνα.
; ---------------------------------------------------------------------------
tile_addr:
        ld      a,b
        add     a,64
        ld      l,a                 ; tx+64
        ld      a,c
        add     a,64
        srl     a                   ; v>>1, το κρατούμενο είναι το v&1
        jr      nc,ta_even
        set     7,l
ta_even:
        add     a,WORLD_BASE >> 8
        ld      h,a
        ret

; tl_occ — A = μάσκα, B = tx, C = ty του κόσμου: NZ αν το byte του tile έχει
; κάτι από τη μάσκα. Σελιδοποιεί την 4 και γυρίζει την 1 (βήμα 89: τι είναι
; κάτω από το κελί μιας φιγούρας, src/figure.asm).
tl_occ:
        ld      e,a                     ; το tile_addr κρατά το DE
        push    bc
        ld      bc,GA_PORT + PAGE_B4
        out     (c),c
        pop     bc
        call    tile_addr
        ld      a,(hl)
        and     e
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c                   ; οι σημαίες μένουν
        ret

; ---------------------------------------------------------------------------
; tile_draw_all — όλο το κάδρο από (cam_tx, cam_ty), που είναι το ΠΑΝΩ-ΑΡΙΣΤΕΡΑ
; ορατό tile.
;
; tile_draw_rect — μόνο ένα ορθογώνιο από tiles του κάδρου: (td_c0, td_r0) και
; (td_nc, td_nr). Αυτό είναι όλο το σκρολάρισμα — μία στήλη ή μία σειρά. Τα
; td_* μένουν όπως ήταν: το dh_occupied τα διαβάζει μετά.
; ---------------------------------------------------------------------------
tile_draw_all:
        ld      hl,0*256 + VIEW_TW
        ld      (td_nc),hl              ; td_nc, td_c0
        ld      hl,VIEW_TH*256 + 0
        ld      (td_r0),hl              ; td_r0, td_nr

tile_draw_rect:
        ld      hl,(td_r0)              ; L = td_r0, H = td_nr
        ld      a,h
        or      a
        ret     z
        ld      (td_row),hl             ; td_row, td_left

td_next_row:
        ; --- δείκτης κόσμου και διεύθυνση οθόνης για την αρχή της σειράς ---
        ld      de,(td_c0)              ; E = στήλη, D = σειρά του κάδρου
        ld      hl,(cam_tx)             ; L = cam_tx, H = cam_ty
        ld      a,e
        add     a,l
        ld      b,a
        ld      a,d
        add     a,h
        ld      c,a
        call    tile_addr               ; κρατά τα BC, DE
        ld      (t_wptr),hl
        ld      a,e
        add     a,a
        add     a,a
        ld      c,a                     ; στήλη*4 bytes
        ld      a,d
        add     a,a
        add     a,a
        add     a,a
        add     a,a                     ; σειρά*16 γραμμές
        call    scr_addr
        ld      (t_sptr),de

        ld      a,(td_nc)
        ld      b,a
td_next_col:
        push    bc
        call    tile_one
        ld      hl,(t_wptr)
        inc     hl                      ; 16 bit: μια σειρά που αρχίζει ΕΞΩ από
        ld      (t_wptr),hl             ; τον κόσμο κουβαλά κρατούμενο (σκουπίδι)
        ld      hl,t_sptr
        ld      a,(hl)
        add     a,TILE_W
        ld      (hl),a
        jr      nc,td_same
        inc     hl                      ; το H είναι #C0-#C7 (σειρά tile = γραμμή
        inc     (hl)                    ; 0 της σειράς χαρακτήρων), οπότε το
        res     3,(hl)                  ; δαχτυλίδι p mod 2048 είναι #C8 -> #C0
td_same:
        pop     bc
        djnz    td_next_col

        ld      hl,td_row
        inc     (hl)
        inc     hl                      ; td_left
        dec     (hl)
        jr      nz,td_next_row
        ret

; ---------------------------------------------------------------------------
; tile_one — ένα tile: κλάση, παραλλαγή, blit, και φλέβα αν υπάρχει.
; ---------------------------------------------------------------------------
tile_one:
        call    tile_src
        ld      de,(t_sptr)
        call    blit_tile

        ; --- φλέβα: μόνο σε βουνό με τον πόρο αναμμένο ---
        ld      a,(t_cls)
        cp      3                       ; MOUNTAIN
        ret     nz
        ld      a,(t_cur)
        bit     3,a                     ; bit πόρου
        ret     z
        add     a,a                     ; decor & 1 (bit 6) -> bit 7
        and     #80                     ; 2 παραλλαγές, x ORE_OVL_SZ
        ld      l,a
        ld      h,G_ore_overlay >> 8
        ld      de,(t_sptr)
        ld      bc,TILE_W*256 + TILE_H
        jp      blit_mask

; tile_src — το sprite του tile στο (t_wptr): κλάση, παραλλαγή ή autotile.
; Out: HL = πηγή, (t_cur), (t_cls). Απαιτεί τράπεζα 4. Χωριστά από το blit
; από το βήμα 42, για τη θέση δακτυλίου που αδειάζει (dirty.asm, dhs_vacate):
; εκεί το tile περνά από το ob_blit, κομμένο σε 2x8.
tile_src:
        ld      hl,(t_wptr)
        ld      a,(hl)
        ld      (t_cur),a
        ld      b,a
        and     7
        ld      (t_cls),a
        ; πόσες παραλλαγές έχει η κλάση;
        add     a,G_tile_variants & 255
        ld      l,a
        ld      h,G_tile_variants >> 8
        ld      a,(hl)
        cp      16
        jr      z,to_auto
        ; --- μη autotiled: η παραλλαγή είναι τα bits decor, με mask ---
        ; Χωρίς το mask, decor 2-3 σε crater δείχνει στα tiles της ΕΠΟΜΕΝΗΣ
        ; κλάσης — ο crater και το foundation έχουν μόνο 2 (SPRITES.md §3).
        dec     a
        ld      e,a
        ld      a,b
        rlca
        rlca                            ; decor στα bits 0-1
        and     3
        and     e
        jr      to_have_var
to_auto:
        call    tile_autotile           ; -> A = μάσκα 0..15
to_have_var:
        ; --- πηγή = tile_ptr[class] + variant*TILE_SZ ---
        rrca
        rrca                            ; v1 v0 0 0 0 0 v3 v2
        ld      d,a
        and     #C0
        ld      e,a
        xor     d
        ld      d,a                     ; DE = variant*64
        ld      a,(t_cls)
        add     a,a
        add     a,G_tile_ptr & 255
        ld      l,a
        ld      h,G_tile_ptr >> 8
        ld      a,(hl)
        inc     l
        ld      h,(hl)
        ld      l,a                     ; HL = tile_ptr[class]
        add     hl,de                   ; + variant*64
        ret

; ---------------------------------------------------------------------------
; tile_autotile — μάσκα γειτόνων για το tile στο (t_wptr).
; bit0 = N, bit1 = E, bit2 = S, bit3 = W· μπαίνει όταν ο γείτονας είναι ΙΔΙΑΣ
; ΟΙΚΟΓΕΝΕΙΑΣ. Μόνο ΕΝΑ ζευγάρι μοιράζεται οικογένεια: το βαθύ νερό (5)
; μετράει ως νερό (4), αλλιώς κάθε λίμνη αποκτά ακτή γύρω από το βαθύ της
; κομμάτι (SPRITES.md §3).
; Out: A = 0..15
;
; Οι γείτονες με τη σειρά W, S, E, N: ο δείκτης περπατά από τον έναν στον
; άλλον, και κάθε κρατούμενο μπαίνει από δεξιά στο B — το W καταλήγει bit 3.
; ---------------------------------------------------------------------------
tile_autotile:
        ld      a,(t_cls)
        cp      5
        jr      nz,tat_fam
        dec     a
tat_fam:
        ld      c,a                     ; C = η οικογένεια
        ld      hl,(t_wptr)
        dec     hl
        call    ta_same                 ; W
        rl      b
        ld      de,WORLD_W + 1
        add     hl,de
        call    ta_same                 ; S
        rl      b
        ld      de,1 - WORLD_W
        add     hl,de
        call    ta_same                 ; E
        rl      b
        ld      de,-WORLD_W - 1
        add     hl,de
        call    ta_same                 ; N
        ld      a,b
        rla
        and     15
        ret

; ta_same — κρατούμενο = 1 αν το (HL) είναι ίδιας οικογένειας με το C. Κρατά
; όλους τους καταχωρητές εκτός από το AF.
;
; Ο γείτονας μπορεί να πέσει ΕΞΩ από το επίπεδο: στη γραμμή -64 ο βορράς είναι
; κάτω από το #4000, στο tile (-64,-64) η δύση είναι το #3FFF — δηλαδή ο ΚΩΔΙΚΑΣ
; της τράπεζας 0, όχι ο κόσμος. Ένας έλεγχος ότι το H είναι μέσα στο παράθυρο
; τα πιάνει όλα μαζί, σε κάθε άκρη και γωνία, χωρίς λογιστική ανά σειρά και
; ανά στήλη. Εκτός κόσμου διαβάζεται ως ο ΕΑΥΤΟΣ του tile, ώστε να μη
; ζωγραφιστεί ακτή στην άκρη του κόσμου.
ta_same:
        ld      a,h
        sub     WORLD_BASE >> 8
        cp      #40
        jr      nc,ta_yes               ; έξω από το παράθυρο #4000-#7FFF
        ld      a,(hl)
        and     7
        cp      5                       ; η οικογένεια, ξετυλιγμένη: καλείται
        jr      nz,ta_cmp               ; 4 φορές ανά tile
        dec     a
ta_cmp:
        sub     c
        sub     1                       ; κρατούμενο μόνο από το 0: ίσα
        ret
ta_yes:
        scf
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
;
; Η 8η γραμμή δεν προσθέτει το #800 που θα αφαιρούσε αμέσως το πέρασμα στη
; δεύτερη σειρά, και η 16η ούτε σώζει το DE ούτε προχωρά: κανείς δεν το
; διαβάζει μετά (βήμα 56, 66 T-states ανά tile).
; ---------------------------------------------------------------------------
blit_tile:
        ld      bc,64               ; μετρητής του ldi· κανείς δεν τον κοιτά
        repeat  7
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
        push    de
        ldi
        ldi
        ldi
        ldi
        pop     de                  ; D = D0 + 7*8
        ; πέρασμα στη δεύτερη σειρά χαρακτήρων: +#50, και το D πίσω στο D0
        ld      a,e
        add     a,SCR_W
        ld      e,a
        ld      a,d
        adc     a,-7*8
        and     #C7                 ; και εδώ το δαχτυλίδι — μία εντολή ανά tile
        ld      d,a
        repeat  7
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
        ldi
        ldi
        ldi
        ldi
        ret

; --- μεταβλητές ------------------------------------------------------------
cam_tx:     db 0                ; πάνω-αριστερά ορατό tile, προσημασμένο
cam_ty:     db 0
td_nc:      db VIEW_TW          ; το ορθογώνιο μέσα στο κάδρο, σε tiles
td_c0:      db 0
td_row:     db 0                ; η σειρά που ζωγραφίζεται τώρα
td_left:    db 0                ; και πόσες μένουν
td_r0:      db 0
td_nr:      db VIEW_TH
        assert  cam_ty == cam_tx + 1
        assert  td_c0 == td_nc + 1 && td_row == td_c0 + 1 && td_left == td_row + 1
        assert  td_nr == td_r0 + 1
t_wptr:     dw 0
t_sptr:     dw 0
t_cur:      db 0                ; το world byte του τρέχοντος tile
t_cls:      db 0
