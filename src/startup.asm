; startup.asm — η εκκίνηση του παιχνιδιού, ό,τι ως το βήμα 157 ήταν η αρχή του
; start (src/main.asm), από την τράπεζα 0.
;
; ΤΡΕΧΕΙ ΜΙΑ ΦΟΡΑ ΑΠΟ ΤΟ ΤΕΛΟΣ ΤΟΥ GH_BUF (βήμα 158): στο BOOT_ORG, με το
; game_new (src/newgame.asm) αμέσως μετά. Ο δίσκος τα φέρνει με το game2.bin,
; που αρχίζει από το BOOT_ORG (src/boot.asm, tools/mkdsk.py). Ως το πρώτο
; φάντασμα κανείς άλλος δεν γράφει εδώ: ο εγκαταστάτης των τρυπών περνά την
; κατεδάφιση από το ovi_buf σε τρία κομμάτια (src/ov_inst.asm), το tutorial
; τρέχει από την αρχή του GH_BUF, και η αποικία δοκιμών κάθεται από κάτω (τα
; assert στο src/main.asm). Μετά, το φάντασμα γράφει πάνω του — όπως πάνω
; στην αποικία από το βήμα 91 — και κανείς δεν τον ξαναζητά: το game_new
; τρέχει μόνο στην εκκίνηση (tests/test_newgame.py τον ξαναγράφει πριν τον
; καλέσει).
;
; Τελειώνει με jp game_new, που τελειώνει με jp ui_init· το ret του ui_init
; γυρίζει στο start, στον main_loop.
; ---------------------------------------------------------------------------
boot_go:
        ; --- η διακοπή των λωρίδων (src/isr.asm): το διάνυσμα, IM 1, το R7, και
        ; τα pens του κάδρου. Οι διακοπές μένουν κλειστές: τις ανοίγει ο βρόχος.
        ; Το «jp isr» γράφεται στο #0038 εδώ και όχι από τη μεταγλώττιση: ο
        ; δίσκος φορτώνει από το #0100, και κάτω από αυτό είναι ό,τι άφησε το
        ; firmware. (Ως το βήμα 102 το is_init, με μόνο αυτόν τον καλούντα.)
        ld      a,#C3                   ; jp
        ld      (IS_VEC),a
        ld      hl,is_vs
        ld      (IS_VEC + 1),hl
        im      1
        ld      bc,CRTC_SEL + 7
        out     (c),c
        ld      bc,CRTC_VAL + IS_R7
        out     (c),c
        ld      hl,G_palette_fw + 1
        ld      de,is_pal + 3
        ld      b,3
isi_lp: ld      a,(hl)
        inc     hl
        push    hl
        ld      hl,fw_to_hw
        add     a,l
        ld      l,a
        adc     a,h
        sub     l
        ld      h,a
        ld      a,(hl)
        or      GA_INK
        ld      (de),a
        inc     de
        pop     hl
        djnz    isi_lp
        call    hw_mode0
        call    hw_clear                ; ό,τι άφησε ο φορτωτής, φεύγει τώρα
        ld      hl,G_palette_fw
        call    pal_set
        ; Ο πλανήτης ζει στα τέσσερα bytes που άφησε η γεννήτρια στην τράπεζα 6
        ; (§5.7): τέσσερα pens εδάφους, τίποτε άλλο.
        call    ob_b6                   ; BC = GA_PORT + PAGE_B6
        ld      a,(G_worldinfo + 2)
        ld      c,PAGE_B1               ; το B είναι ακόμη GA_PORT >> 8
        out     (c),c
        call    pal_planet
        xor     a
        call    pal_border
        ; Ο renderer παρουσιάζεται στην προσομοίωση ΠΡΙΝ από την πρώτη εντολή:
        ; το wh_hook ξεκινά δείχνοντας στο dirty_push (src/wheel.asm, HAS_VIEW).
        ; Ως το βήμα 70 το έγραφαν δύο εντολές εδώ, έξι bytes για μια τιμή που
        ; δεν αλλάζει ποτέ.
        call    snd_init
        call    ov_install              ; ο κώδικας του GH_BUF στις τρύπες (βήμα 101)
        ; ΚΟΣΜΟΣ ΤΟΥ TUTORIAL; Η ΓΡΑΜΜΗ ΤΟΥ ΠΡΩΤΟΥ ΒΗΜΑΤΟΣ (βήμα 149). ΠΡΙΝ από το
        ; game_new: εκείνο τελειώνει δείχνοντας τον κέρσορα (ui_init), που
        ; γράφει το αρχείο του στο GH_BUF, όπου τρέχει το tutorial — μετά, το
        ; πρώτο ui_hide ξανάγραφε σκουπίδια και το UI δεν άκουγε κανένα πλήκτρο.
        ; Το game_new μηδενίζει το EC_TU, και το επόμενο γεγονός το ξαναβρίσκει
        ; από το worldinfo (src/tutor.asm).
        ; ΚΑΙ Η ΣΕΛΙΔΑ ΤΗΣ ΕΙΣΑΓΩΓΗΣ (βήμα 175): το ret του ui_init, στο τέλος
        ; του game_new, πάει στο tu_open, και το δικό του στο main_loop. Οχι
        ; εδώ: το GH_BUF, όπου τρέχει αυτός ο κώδικας, γίνεται ο τομέας της
        ; σελίδας και ο οδηγός του δίσκου.
        ld      hl,tu_open
        push    hl
        call    tu_run
        jp      game_new
