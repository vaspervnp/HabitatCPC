; ---------------------------------------------------------------------------
; menu.asm — το μενού του πλανήτη πάνω σε κομμάτι κόσμου (βήμα 130, DESIGN
; §13.2). Γίνεται το MENU.BIN (tools/mkdsk.py), που ο φορτωτής το φορτώνει
; στο MW_ORG ΠΡΙΝ από το μενού και το καλεί.
;
; Ο παίκτης: «θέλω το μενού να έχει και γραφικά, ζωγραφισμένο πάνω σε τμήμα
; κόσμου — ένας τυχαίος κόσμος κάθε φορά». Οι κόσμοι είναι έτοιμοι, MW_N
; κομμάτια από τη γεννήτρια αναφοράς (tools/menuworld.py), και ο φορτωτής
; διαλέγει ένα με τον R. Ο ίδιος κόσμος μένει σε όλο το μενού και σε όλη τη
; φόρτωση· μετά την επιλογή το πάνελ γράφει τη φόρτωση και τη μπάρα, που τη
; γεμίζουν ο φορτωτής και η γεννήτρια (src/menugeom.asm).
;
; ΖΕΙ ΣΤΗ ΒΑΣΙΚΗ RAM, στο #4000: ως το μενού δεν έχει φορτωθεί τίποτε άλλο.
; Μετά το πατάνε η PAGE2.BIN και η BANK1.BIN, και το επίμετρο του φορτωτή
; σβήνει ό,τι μένει — γι' αυτό ό,τι γράφεται στην οθόνη κατά τη φόρτωση
; (μπάρα, BUILDING THE WORLD) το κάνουν ο φορτωτής και η γεννήτρια, όχι αυτό.
;
; ΔΕΝ ΔΙΑΒΑΖΕΙ ΠΟΤΕ ΤΗΝ ΟΘΟΝΗ. Το firmware ζει, και στο #C000 ο επεξεργαστής
; ΔΙΑΒΑΖΕΙ την πάνω ROM (οι εγγραφές πάνε στη RAM). Το βουνό με φλέβα βγαίνει
; από το tile και τη φλέβα μαζί, η ανάποδη γραμμή από τον γλύφο με XOR.
; ---------------------------------------------------------------------------

        include "menugeom.asm"

SCR_SET_MODE    equ #BC0E
SCR_SET_INK     equ #BC32
SCR_SET_BORDER  equ #BC38
KM_TEST_KEY     equ #BB1E
MC_WAIT_FLYBACK equ #BD19

MW_CW           equ MW_COLS + 2         ; το παράθυρο των κλάσεων, με περιθώριο
MW_CH           equ MW_ROWS + 2
MOUNTAIN        equ 3                   ; world.py: οι κλάσεις
WATER           equ 4
DEEPWATER       equ 5

        org     MW_ORG

; Οι είσοδοι, σε σταθερές θέσεις: ο φορτωτής καλεί την πρώτη, οι δοκιμές και
; τις άλλες δύο (tests/test_menu.py), που δεν αγγίζουν το firmware.
mw_entry:   jp      mw_run              ; A = κόσμος. Out: A = πλανήτης 0-3, #FF τυχαίος, 4 το tutorial
mw_show_e:  jp      mw_show             ; A = κόσμος, B = η διαλεγμένη 0-5
mw_load_e:  jp      mw_load             ; A = η διαλεγμένη 0-5: το πάνελ της φόρτωσης

; ---------------------------------------------------------------------------
; mw_run — όλο το μενού. MODE 0 και τα χρώματα του πλανήτη του κόσμου, ο
; κόσμος με το μενού, η επιλογή, και στο τέλος το πάνελ της φόρτωσης.
; ---------------------------------------------------------------------------
mw_run:
        ld      (mw_k),a
        xor     a
        call    SCR_SET_MODE            ; MODE 0· σβήνει και την οθόνη
        ; ΟΛΑ ΤΑ ΧΡΩΜΑΤΑ ΜΑΥΡΑ ΟΣΟ ΖΩΓΡΑΦΙΖΕΙ: ~0,5 s, και ο παίκτης θα έβλεπε
        ; τον κόσμο να χτίζεται σειρά σειρά. Η παλέτα μπαίνει όλη μαζί στο τέλος.
        ld      hl,mw_ink
        ld      de,mw_ink + 1
        ld      bc,15
        ld      (hl),b                  ; 0
        ldir
        call    mw_setink
        ld      a,(mw_k)
        ld      b,0                     ; ο τυχαίος διαλεγμένος
        call    mw_show
        ld      a,(mw_k)
        call    mw_inks
        call    mw_pick                 ; A = 0-5
        push    af
        call    mw_load
        pop     af
        dec     a                       ; 0 τυχαίος -> #FF, 1-4 -> 0-3, 5 το tutorial -> 4
        ret

; ---------------------------------------------------------------------------
; mw_inks — A = κόσμος: τα 16 pens, palette_fw με τα τέσσερα του πλανήτη του
; (planet_pens στα pal_terrain, όπως το pal_planet του παιχνιδιού), από το
; SCR SET INK· το περίγραμμα μαύρο.
; ---------------------------------------------------------------------------
mw_inks:
        call    mw_exent                ; HL -> η εγγραφή του κόσμου
        ld      a,(hl)                  ; ο πλανήτης
        add     a,a
        add     a,a
        ld      c,a
        ld      b,0
        ld      hl,mw_pp
        add     hl,bc                   ; τα τέσσερα χρώματά του
        push    hl
        ld      hl,mw_pal
        ld      de,mw_ink
        ld      bc,16
        ldir
        pop     hl
        ld      de,mw_tpen
        ld      b,4
mi_ter:
        push    bc
        ld      a,(de)                  ; το pen
        inc     de
        push    de
        ld      e,a
        ld      d,0
        push    hl
        ld      hl,mw_ink
        add     hl,de
        ex      de,hl
        pop     hl
        ld      a,(hl)                  ; το χρώμα
        inc     hl
        ld      (de),a
        pop     de
        pop     bc
        djnz    mi_ter
; mw_setink — τα 16 του mw_ink στο firmware, και το περίγραμμα μαύρο.
mw_setink:
        xor     a
mi_set:
        push    af
        ld      e,a
        ld      d,0
        ld      hl,mw_ink
        add     hl,de
        ld      b,(hl)
        ld      c,b                     ; χωρίς αναβόσβημα
        call    SCR_SET_INK
        pop     af
        inc     a
        cp      16
        jr      c,mi_set
        ld      bc,0
        jp      SCR_SET_BORDER

; mw_exent — A = κόσμος: HL -> η εγγραφή του στο mw_ex (πλανήτης, δείκτης).
mw_exent:
        ld      l,a
        ld      h,0
        ld      d,h
        ld      e,l
        add     hl,hl
        add     hl,de                   ; x 3
        ld      de,mw_ex
        add     hl,de
        ret

; ---------------------------------------------------------------------------
; mw_show — A = κόσμος, B = η διαλεγμένη γραμμή: ο κόσμος, ο τίτλος, και το
; πάνελ του μενού. Χωρίς firmware (το καλούν και οι δοκιμές).
; ---------------------------------------------------------------------------
mw_show:
        push    af
        ld      a,b
        ld      (mn_sel),a
        pop     af
        call    mw_world
        call    mw_title
        ld      hl,s_sub
        ld      de,SUB_ROW * 256 + SUB_COL
        ld      c,SUB_W
        call    mw_textn
        call    mw_panel
        ld      hl,s_cho
        ld      de,CHO_ROW * 256 + CHO_COL
        call    mw_text
        ld      hl,s_key
        ld      de,KEY_ROW * 256 + KEY_COL
        call    mw_text
        ld      b,OPT_N
ms_opt:
        push    bc
        ld      a,b
        dec     a
        call    mw_opt                  ; ανάποδα μόνο η διαλεγμένη
        pop     bc
        djnz    ms_opt
        jp      mw_desc

; mw_opt — A = γραμμή 0-5: γραμμένη ίσια, ή ανάποδα αν είναι η mn_sel.
mw_opt:
        ld      c,a
        ld      a,(mn_sel)
        cp      c
        ld      a,0                     ; XOR
        jr      nz,mo_flat
        ld      a,INV
mo_flat:
        ld      b,#FF                   ; AND
        call    mw_mode
        ld      a,c
        ld      hl,mw_sopt
        call    mw_ptr
        ld      a,c
        add     a,OPT_ROW
        ld      d,a
        ld      e,OPT_COL
        ld      c,OPT_W
        call    mw_textn
        jp      mw_flat

; mw_desc — η περιγραφή της mn_sel, με κενά ως το DSC_W (σβήνει την παλιά).
mw_desc:
        ld      a,(mn_sel)
        ld      hl,mw_sdsc
        call    mw_ptr
        ld      de,DSC_ROW * 256 + DSC_COL
        ld      c,DSC_W
        jp      mw_textn

; mw_ptr — HL = πίνακας δεικτών, A = θέση: HL = ο δείκτης.
mw_ptr:
        add     a,a
        ld      e,a
        ld      d,0
        add     hl,de
        ld      a,(hl)
        inc     hl
        ld      h,(hl)
        ld      l,a
        ret

; ---------------------------------------------------------------------------
; mw_pick — η επιλογή (από το βήμα 128, src/boot.asm). Out: A = mn_sel.
;
; ΒΕΛΑΚΙΑ Ή ΧΕΙΡΙΣΤΗΡΙΟ, FIRE Ή ENTER. Το KM TEST KEY διαβάζει τον χάρτη του
; firmware, που σαρώνει το πληκτρολόγιο 50 φορές το δευτερόλεπτο, το
; χειριστήριο 0 μέσα (πλήκτρα 72-77). Μετράει μόνο ό,τι ΠΑΤΗΘΗΚΕ ΤΩΡΑ: το
; mn_prev ξεκινά «όλα πατημένα», ώστε ένα RETURN που κρατιέται ακόμη από το
; RUN"HABITAT να μη διαλέξει μόνο του.
; ---------------------------------------------------------------------------
mw_pick:
        call    MC_WAIT_FLYBACK
        call    mn_keys                 ; E = τα πλήκτρα τώρα
        ld      hl,mn_prev
        ld      a,(hl)
        ld      (hl),e
        cpl
        and     e                       ; όσα πατήθηκαν από το προηγούμενο frame
        jr      z,mw_pick
        ld      d,a
        ld      a,(mn_sel)
        rr      d
        jr      c,mp_up
        rr      d
        jr      c,mp_dn
        ret                             ; FIRE
mp_up:
        dec     a
        jp      p,mp_set
        ld      a,OPT_N - 1             ; από την κορυφή στον πάτο
        jr      mp_set
mp_dn:
        inc     a
        cp      OPT_N
        jr      c,mp_set
        xor     a
mp_set:
        ld      hl,mn_sel
        ld      c,(hl)
        ld      (hl),a
        ld      a,c
        call    mw_opt                  ; η παλιά ίσια
        ld      a,(mn_sel)
        call    mw_opt                  ; η καινούργια ανάποδα
        call    mw_desc
        jr      mw_pick

; mn_keys — Out: E = bit 0 πάνω, bit 1 κάτω, bit 2 FIRE. Το KM TEST KEY
; χαλάει A, C, HL και τις σημαίες.
mn_keys:
        ld      hl,mn_ktab
        ld      e,0
mnk_lp:
        ld      a,(hl)
        inc     a
        ret     z                       ; #FF: τέλος
        dec     a
        inc     hl
        ld      d,(hl)
        inc     hl
        push    hl
        push    de
        call    KM_TEST_KEY
        pop     de
        pop     hl
        jr      z,mnk_lp
        ld      a,e
        or      d
        ld      e,a
        jr      mnk_lp

; ---------------------------------------------------------------------------
; mw_load — A = η διαλεγμένη: το πάνελ ξανά, με τον κόσμο που διάλεξε, το
; LOADING, το πλαίσιο της μπάρας άδειο, και το BUILDING THE WORLD σβηστό (το
; ανάβει ο φορτωτής πριν από τη γεννήτρια).
; ---------------------------------------------------------------------------
mw_load:
        push    af
        call    mw_panel
        pop     af
        ld      hl,mw_snam
        call    mw_ptr
        ld      de,NAM_ROW * 256 + NAM_COL
        call    mw_text
        ld      hl,s_lod
        ld      de,LOD_ROW * 256 + LOD_COL
        call    mw_text
        ld      a,BAR_ROW * 8
        ld      bc,(BAR_W + 2) * 256 + BAR_X0 - 1
        ld      de,8 * 256 + 0          ; 8 γραμμές, πλαίσιο στην πρώτη και την τελευταία
        call    mw_frame
        xor     a
        ld      b,DIM
        call    mw_mode
        ld      hl,s_wld
        ld      de,WLD_ROW * 256 + WLD_COL
        ld      c,WLD_W
        call    mw_textn
        jp      mw_flat

; mw_panel — το πάνελ: μαύρο, με πλαίσιο στην πένα 4 μία γραμμή μέσα.
mw_panel:
        ld      a,PNL_ROW * 8
        ld      bc,(PNL_W * 2) * 256 + PNL_COL * 2
        ld      de,(PNL_H * 8) * 256 + 1
        ; πέφτει στο mw_frame

; ---------------------------------------------------------------------------
; mw_frame — A = πρώτη γραμμή, C = πρώτο byte, B = πλάτος σε bytes, D = ύψος
; σε γραμμές, E = εσοχή του πλαισίου (0 ή 1). Ανά γραμμή: οι E πρώτες και
; τελευταίες μηδέν, η επόμενη από μέσα το πλαίσιο (EDGE_L, EDGE..., EDGE_R),
; οι άλλες τα δύο χείλη και μηδέν ανάμεσα (tools/menuworld.py: frame).
; ---------------------------------------------------------------------------
EDGE            equ #30
EDGE_L          equ #10
EDGE_R          equ #20

mw_frame:
        ld      (mf_y),a
        ld      (mf_x),bc               ; C = x, B = πλάτος
        ld      (mf_h),de               ; E = εσοχή, D = ύψος
        ld      a,d
        ld      (mf_n),a
mf_line:
        ; ποια γραμμή: k = y - y0 από το 0, h - 1 - k από το τέλος
        ld      a,(mf_h + 1)
        ld      hl,mf_n
        sub     (hl)                    ; k
        ld      c,a
        ld      a,(hl)
        dec     a                       ; h - 1 - k
        cp      c
        jr      c,mf_min
        ld      a,c
mf_min:                                 ; A = η απόσταση από την κοντινότερη άκρη
        ld      hl,mf_h
        cp      (hl)                    ; < εσοχή: μηδέν
        ld      bc,0 * 256 + 0          ; αριστερό, μέση (το δεξί στο E)
        ld      e,0
        jr      c,mf_put
        ld      bc,EDGE_L * 256 + EDGE
        ld      e,EDGE_R
        jr      z,mf_put                ; = εσοχή: το πλαίσιο
        ld      c,0                     ; αλλιώς: χείλη και μηδέν
mf_put:
        push    bc
        push    de
        ld      a,(mf_y)
        call    mw_line
        ld      a,(mf_x)
        call    mw_addu                 ; HL = η πρώτη θέση
        pop     de
        pop     bc
        ld      (hl),b                  ; αριστερό
        inc     hl
        ld      a,(mf_x + 1)
        sub     2
        ld      b,a
mf_mid:
        ld      (hl),c
        inc     hl
        djnz    mf_mid
        ld      (hl),e                  ; δεξί
        ld      hl,mf_y
        inc     (hl)
        ld      hl,mf_n
        dec     (hl)
        jr      nz,mf_line
        ret

; mw_line — A = γραμμή 0-199: HL = #C000 + (A >> 3) * 80 + (A & 7) * #800.
; Χαλάει τα DE· κρατά τα BC.
mw_line:
        push    bc
        ld      c,a
        and     #F8                     ; (A >> 3) * 8
        ld      l,a
        ld      h,0
        add     hl,hl                   ; x 16
        ld      d,h
        ld      e,l
        add     hl,hl
        add     hl,hl                   ; x 64
        add     hl,de                   ; x 80
        ld      a,c
        and     7
        add     a,a
        add     a,a
        add     a,a                     ; (A & 7) * 8, το πάνω byte του * #800
        add     a,#C0
        add     a,h
        ld      h,a
        pop     bc
        ret

; mw_addu — HL += A.
mw_addu:
        add     a,l
        ld      l,a
        ret     nc
        inc     h
        ret

; mw_next — DE = η επόμενη γραμμή της οθόνης (+#800, και από την 7η στην
; αρχή της επόμενης χαρακτηρο-σειράς).
mw_next:
        ld      a,d
        add     a,8
        ld      d,a
        ret     nc
        ld      a,e
        add     a,#50
        ld      e,a
        ld      a,d
        adc     a,#C0
        ld      d,a
        ret

; ---------------------------------------------------------------------------
; Κείμενα. Τα strings είναι αριθμοί γλύφων (tools/menuworld.py: charset), με
; τον γλύφο 0 το κενό και #FF το τέλος. Ενας γλύφος = 2 bytes x 8 γραμμές.
; mw_mode: A = XOR, B = AND σε κάθε byte (ίσια 0/#FF, ανάποδα INV/#FF, σβηστά
; 0/DIM)· το mw_flat το ξαναφέρνει ίσιο.
; ---------------------------------------------------------------------------
INV             equ #F0
DIM             equ #3F

mw_flat:
        xor     a
        ld      b,#FF
mw_mode:
        ld      (mgm_x + 1),a
        ld      a,b
        ld      (mgm_a + 1),a
        ret

; mw_text — HL = string, D = σειρά, E = στήλη. mw_textn: και C = πλάτος, με
; κενά ως εκεί (0: χωρίς).
mw_text:
        ld      c,0
mw_textn:
        push    hl
        ld      a,d
        add     a,a
        add     a,a
        add     a,a                     ; σειρά x 8
        push    de
        call    mw_line
        pop     de
        ld      a,e
        add     a,a
        call    mw_addu
        ex      de,hl                   ; DE = η οθόνη
        pop     hl
mt_lp:
        ld      a,(hl)
        cp      #FF
        jr      z,mt_pad
        inc     hl
        call    mt_one
        jr      mt_lp
mt_pad:
        ld      a,c
        or      a
        ret     z
        xor     a                       ; το κενό
        call    mt_one
        jr      mt_pad

; mt_one — ένας γλύφος A στο DE, και DE += 2· το C (πλάτος) μετράει ως το 0.
mt_one:
        push    hl
        ld      l,a
        ld      h,0
        add     hl,hl
        add     hl,hl
        add     hl,hl
        add     hl,hl                   ; x 16
        push    de
        ld      de,mw_glyphs
        add     hl,de
        pop     de
        push    de
        ld      b,8
mto_ln:
        ld      a,(hl)
        inc     hl
        call    mg_mode
        ld      (de),a
        inc     de
        ld      a,(hl)
        inc     hl
        call    mg_mode
        ld      (de),a
        dec     de
        ld      a,d
        add     a,8                     ; μέσα στη χαρακτηρο-σειρά: χωρίς τύλιγμα
        ld      d,a
        djnz    mto_ln
        pop     de
        inc     de
        inc     de
        pop     hl
        ld      a,c
        or      a
        ret     z
        dec     c
        ret
mg_mode:
mgm_x:  xor     0
mgm_a:  and     #FF
        ret

; ---------------------------------------------------------------------------
; mw_title — ο τίτλος, κελιά του ενός byte x 2 γραμμών (2 bits το κελί, τέσσερα
; ανά byte, το πρώτο στα bits 0-1): 0 τίποτα, 1 μαύρο, 2 κίτρινο.
; ---------------------------------------------------------------------------
TITLE_INK       equ #3C

mw_title:
        ld      hl,mw_tcell
        ld      c,0                     ; κελιά που μένουν στο byte, ΣΥΝΕΧΙΖΕΙ
        ld      a,TITLE_Y               ; από σειρά σε σειρά (30 δεν είναι x 4)
        ld      (mtt_y),a
        ld      a,MW_TH
        ld      (mtt_n),a
mtt_row:
        ld      a,(mtt_y)
        push    hl
        call    mw_line
        ld      a,TITLE_X
        call    mw_addu
        ex      de,hl                   ; DE = η πρώτη γραμμή του κελιού
        pop     hl
        ld      b,MW_TW
mtt_cell:
        ld      a,c
        or      a
        jr      nz,mtt_have
        ld      a,(hl)
        inc     hl
        ld      (mtt_b),a
        ld      c,4
mtt_have:
        dec     c
        ld      a,(mtt_b)
        push    af
        rrca
        rrca
        ld      (mtt_b),a
        pop     af
        and     3
        jr      z,mtt_skip
        dec     a
        jr      z,mtt_put               ; 1: μαύρο (A = 0)
        ld      a,TITLE_INK
mtt_put:
        ld      (de),a
        push    de
        push    af
        call    mw_next
        pop     af
        ld      (de),a                  ; και η δεύτερη γραμμή
        pop     de
mtt_skip:
        inc     de
        djnz    mtt_cell
        ld      a,(mtt_y)
        add     a,2
        ld      (mtt_y),a
        ld      a,(mtt_n)
        dec     a
        ld      (mtt_n),a
        jr      nz,mtt_row
        ret

; ---------------------------------------------------------------------------
; mw_world — A = κόσμος: το κομμάτι του, 20 x 13 tiles από το πάνω-αριστερά.
;
; Το RLE γεμίζει το mw_cbuf (MW_CW x MW_CH κλάσεις, με περιθώριο ένα tile).
; Μετά, ανά tile: η παραλλαγή — από τους τέσσερις γείτονες για κλάση με 16
; (νερό, βουνό: autotile, bit 0 βόρεια, 1 ανατολικά, 2 νότια, 3 δυτικά, το
; βαθύ νερό ως νερό) ή από τα δύο bits decor για τις άλλες — και για βουνό με
; φλέβα ποια φλέβα, από τα επόμενα δύο bits.
; ---------------------------------------------------------------------------
mw_world:
        call    mw_exent
        inc     hl
        ld      a,(hl)
        inc     hl
        ld      h,(hl)
        ld      l,a                     ; τα δεδομένα του κόσμου
        ld      de,mw_cbuf
        ld      bc,MW_CW * MW_CH
mwd_lp:
        ld      a,(hl)
        inc     hl
        push    hl
        ld      h,a
        and     15
        ld      l,a                     ; η τιμή
        ld      a,h
        rrca
        rrca
        rrca
        rrca
        and     15
        inc     a
        ld      h,a                     ; το μήκος
mwd_put:
        ld      a,l
        ld      (de),a
        inc     de
        dec     bc
        dec     h
        jr      nz,mwd_put
        pop     hl
        ld      a,b
        or      c
        jr      nz,mwd_lp
        ld      (mw_dp),hl              ; τα bits decor
        xor     a
        ld      (mw_dn),a
        ; --- τα tiles ---
        ld      hl,mw_cbuf + MW_CW + 1
        ld      (mwt_p),hl
        ld      hl,#C000
        ld      (mwt_s),hl
        ld      b,MW_ROWS
mwt_row:
        push    bc
        ld      a,16
        dec     b
        jr      nz,mwt_full
        ld      a,8                     ; η τελευταία: μισή
mwt_full:
        ld      (mwt_l),a
        ld      hl,(mwt_s)
        ld      (mwt_a),hl
        ld      b,MW_COLS
mwt_col:
        push    bc
        call    mw_tile
        ld      hl,(mwt_p)
        inc     hl
        ld      (mwt_p),hl
        ld      hl,(mwt_a)
        ld      a,4
        call    mw_addu
        ld      (mwt_a),hl
        pop     bc
        djnz    mwt_col
        ld      hl,(mwt_p)
        inc     hl
        inc     hl                      ; το περιθώριο
        ld      (mwt_p),hl
        ld      hl,(mwt_s)
        ld      de,160                  ; δύο χαρακτηρο-σειρές
        add     hl,de
        ld      (mwt_s),hl
        pop     bc
        djnz    mwt_row
        ret

; mw_tile — το tile του mwt_p στο mwt_a, mwt_l γραμμές.
mw_tile:
        ld      hl,(mwt_p)
        ld      a,(hl)
        and     7
        ld      c,a                     ; η κλάση
        ld      hl,mw_var
        call    mw_addu
        ld      a,(hl)
        cp      16
        jr      z,mtl_auto
        dec     a
        ld      b,a                     ; παραλλαγές - 1
        call    mw_dec
        and     b
        jr      mtl_have
mtl_auto:
        ld      a,c
        call    mw_fam
        ld      e,a                     ; η οικογένεια του tile
        ld      d,0                     ; η μάσκα
        ld      hl,(mwt_p)
        ld      bc,-1                   ; δυτικά: bit 3 (μπαίνει πρώτο)
        call    mtl_nb
        ld      bc,MW_CW                ; νότια: bit 2
        call    mtl_nb
        ld      bc,1                    ; ανατολικά: bit 1
        call    mtl_nb
        ld      bc,-MW_CW               ; βόρεια: bit 0
        call    mtl_nb
        ld      a,d
mtl_have:
        ld      e,a                     ; η παραλλαγή
        ld      hl,(mwt_p)
        ld      a,(hl)
        and     7
        ld      hl,mw_toff
        call    mw_addu
        ld      a,(hl)
        add     a,e                     ; ο αριθμός του tile
        ld      l,a
        ld      h,0
        add     hl,hl
        add     hl,hl
        add     hl,hl
        add     hl,hl
        add     hl,hl                   ; x 32
        ld      de,mw_tiles
        add     hl,de
        ex      de,hl                   ; DE = το tile
        ld      hl,(mwt_p)
        ld      a,(hl)
        cp      MOUNTAIN + 8
        jr      z,mtl_ore
        ex      de,hl
        ld      de,(mwt_a)
        ld      a,(mwt_l)
        srl     a
        ld      b,a                     ; γραμμές της πηγής
        ; --- αδιαφανές, κάθε γραμμή δύο φορές ---
mtl_ln:
        push    bc
        push    hl
        push    de
        ldi
        ldi
        ldi
        ldi
        pop     de
        call    mw_next
        pop     hl
        push    de
        ldi
        ldi
        ldi
        ldi
        pop     de
        call    mw_next
        pop     bc
        djnz    mtl_ln
        ret
mtl_ore:
        ; --- βουνό με φλέβα: (tile AND μάσκα) OR δεδομένα, χωρίς την οθόνη ---
        ld      (mo_t),de
        call    mw_dec
        and     1
        rrca                            ; x 128
        ld      l,a
        ld      h,0
        ld      bc,mw_ore
        add     hl,bc
        ld      (mo_o),hl
        ld      de,(mwt_a)
        ld      a,(mwt_l)
        ld      b,a
mto_ln2:
        push    bc
        push    de
        ld      hl,(mo_o)
        ld      bc,(mo_t)
        ld      a,4
mto_b:
        push    af
        ld      a,(bc)
        inc     bc
        and     (hl)
        inc     hl
        or      (hl)
        inc     hl
        ld      (de),a
        inc     de
        pop     af
        dec     a
        jr      nz,mto_b
        ld      (mo_o),hl
        pop     de
        call    mw_next
        pop     bc
        bit     0,b                     ; ανά δύο γραμμές, η επόμενη του tile
        jr      z,mto_same
        ld      hl,(mo_t)
        ld      a,4
        call    mw_addu
        ld      (mo_t),hl
mto_same:
        djnz    mto_ln2
        ret

; mtl_nb — HL = το tile, BC = ο γείτονας, E = η οικογένεια: D = D << 1 | ίδια.
mtl_nb:
        push    hl
        add     hl,bc
        ld      a,(hl)
        and     7
        call    mw_fam
        pop     hl
        cp      e
        scf
        jr      z,mtn_same
        ccf
mtn_same:
        rl      d
        ret

; mw_fam — A = κλάση: η οικογένεια (το βαθύ νερό είναι νερό).
mw_fam:
        cp      DEEPWATER
        ret     nz
        ld      a,WATER
        ret

; mw_dec — A = τα επόμενα δύο bits decor.
mw_dec:
        push    hl
        ld      a,(mw_dn)
        or      a
        jr      nz,mdc_have
        ld      hl,(mw_dp)
        ld      a,(hl)
        inc     hl
        ld      (mw_dp),hl
        ld      (mw_db),a
        ld      a,4
mdc_have:
        dec     a
        ld      (mw_dn),a
        ld      a,(mw_db)
        ld      l,a
        rrca
        rrca
        ld      (mw_db),a
        ld      a,l
        and     3
        pop     hl
        ret

; --- μεταβλητές --------------------------------------------------------------
mw_k:       db 0                        ; ο κόσμος
mw_ink:     ds 16                       ; τα χρώματα της οθόνης
mn_ktab:    db 0,1, 72,1                ; πάνω: βελάκι, χειριστήριο
            db 2,2, 73,2                ; κάτω
            db 18,4, 6,4, 47,4          ; RETURN, το μικρό ENTER, SPACE
            db 76,4, 77,4               ; τα δύο FIRE του χειριστηρίου
            db #FF
mn_sel:     db 0                        ; 0 τυχαίος, 1-4 οι πλανήτες 0-3
mn_prev:    db #FF
mf_y:       db 0
mf_x:       dw 0                        ; x, πλάτος
mf_h:       dw 0                        ; εσοχή, ύψος
mf_n:       db 0
mtt_y:      db 0
mtt_n:      db 0
mtt_b:      db 0
mwt_p:      dw 0                        ; το κελί στο mw_cbuf
mwt_s:      dw 0                        ; η αρχή της σειράς στην οθόνη
mwt_a:      dw 0                        ; το tile στην οθόνη
mwt_l:      db 0                        ; γραμμές
mw_dp:      dw 0                        ; τα bits decor
mw_dn:      db 0
mw_db:      db 0
mo_t:       dw 0
mo_o:       dw 0

; --- τα δεδομένα (tools/menuworld.py) -------------------------------------------
        include "../build/menu_data.asm"
zz_menu_end:

; Το παράθυρο των κλάσεων ΔΕΝ είναι στο αρχείο: μετά το τέλος του.
mw_cbuf     equ zz_menu_end
        assert  mw_cbuf + MW_CW * MW_CH <= #8000

        save    "../build/menu.bin", MW_ORG, zz_menu_end - MW_ORG
