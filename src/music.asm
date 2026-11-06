; music.asm — η μουσική (βήμα 195, DESIGN §9.5). Τράπεζα 0, στο MU_ORG.
;
; Ο ΧΡΗΣΤΗΣ ΖΗΤΗΣΕ ατμοσφαιρική μουσική που να παίζει με τη διακοπή και να
; ανοιγοκλείνει από το μενού. Διάλεξε (AskUserQuestion) γεννητική, κουμπί στη
; ΔΙΑΧΕΙΡΙΣΗ με δικό του πλήκτρο, ανοιχτή στην αρχή και σωσμένη, και το εφέ να
; παίρνει μόνο το κανάλι του. Μετά το δείγμα: η ένταση στο 1/4.
;
; ΤΙ ΠΑΙΖΕΙ: το tools/music.py, το μοντέλο αναφοράς, με την ίδια σειρά πράξεων
; ανά frame — καμπάνα στο A, βάθος στο B, ηχώ στο C. Το tests/test_music.py
; συγκρίνει τους καταχωρητές του εξομοιωτή με εκείνο frame προς frame.
;
; ΠΟΥ ΖΕΙ. Η διακοπή δεν σελιδοποιεί (123 σημεία γράφουν τράπεζα, και κανένα
; δεν αφήνει ίχνος), οπότε ο κώδικας είναι στη βασική μνήμη. Εκεί το μόνο
; ελεύθερο είναι το MU_ORG-#3FFF, πάνω από το πάτωμα των δοκιμών
; (src/main.asm): το παιχνίδι από τον δίσκο δεν το αγγίζει ποτέ, αλλά οι
; δοκιμές γράφουν εκεί probes. ΓΙ' ΑΥΤΟ Η ΜΟΥΣΙΚΗ ΕΙΝΑΙ ΚΛΕΙΣΤΗ ΣΤΟ main.sna
; (mu_off = 1, src/isr.asm) και την ανοίγει ο δίσκος (tools/mkdsk.py): ένα
; probe εδώ δεν τρέχει ποτέ ως μουσική. Οποια δοκιμή την ανοίγει, δεν γράφει
; εδώ (tests/codeat.py, music_off).
;
; ΜΟΝΟ Ο,ΤΙ ΑΛΛΑΞΕ (mu_dirty, ένα bit ανά κανάλι). Ενα frame χωρίς αλλαγή
; κοστίζει μόνο τους μετρητές· μια ένταση που άλλαξε γράφεται με την περίοδό
; της. Το βάθος γράφεται κάθε 32 frames ούτως ή άλλως, και αυτό είναι και η
; ανανέωσή του μετά από ένα snd_off (σώσιμο, φόρτωμα, το κουμπί): η καμπάνα και
; η ηχώ αλλάζουν κάθε 4 frames όσο ακούγονται. Η πρώτη εκδοχή είχε ανά κανάλι
; «ό,τι γράφτηκε» και τα κοίταζε όλα σε κάθε frame: 342 µs κατά μέσο όρο, ως
; 1.014 (tests/test_music.py, ΚΟΣΤΟΣ).
;
; ΜΕ ΤΟΝ ΚΥΡΙΟ ΒΡΟΧΟ ΣΤΟΝ ΙΔΙΟ AY. Το in_scan (src/input.asm) περνά από τη
; θύρα Α του PSG για το πληκτρολόγιο, και το snd_reg (src/sound.asm) γράφει
; τα εφέ σε δύο βήματα, επιλογή και τιμή. Μια εγγραφή από εδώ ανάμεσά τους θα
; έστελνε την τιμή σε άλλον καταχωρητή, ή θα άφηνε τη θύρα έξοδο μέσα στη
; σάρωση. Οταν η διακοπή έπεσε στη ΣΕΛΙΔΑ ενός από τα δύο (assert), η μουσική
; δεν γράφει: τα bits μένουν, και γράφει στο επόμενο frame. Η σελίδα και όχι η
; ακριβής περιοχή: δύο συγκρίσεις αντί για δύο αφαιρέσεις 16 bit, και ό,τι
; άλλο είναι εκεί (ο κύριος βρόχος, ένα κομμάτι του oi_build) σπάνια κρατά.
;
; ΤΑ ΕΦΕ ΠΑΙΡΝΟΥΝ ΜΟΝΟ ΤΟ ΚΑΝΑΛΙ ΤΟΥΣ: όσο το wait του sn_st είναι μη μηδέν,
; η μουσική δεν αγγίζει το κανάλι, και το bit του μένει ως να ελευθερωθεί.
; Τον μίκτη δεν τον γράφει ποτέ: οι τόνοι μένουν ανοιχτοί από το snd_off και
; το τέλος κάθε εφέ (#38), και το sn_mix μένει μόνο του snd_tick.

MU_BELL     equ 8                       ; 12 - 4: το 1/4 του δείγματος
MU_ECHO     equ 4                       ; 8 - 4
MU_PC       equ 6                       ; το PC που διακόπηκε: HL, BC, AF από πάνω
; (Τα assert της σελίδας: στο τέλος του src/main.asm.)

; ---------------------------------------------------------------------------
; mu_tick — από το is_i5, με AF και BC στη στοίβα· τελειώνει στο is_out. Μία
; φορά ανά frame, όσο το mu_off είναι 0.
; ---------------------------------------------------------------------------
mu_tick:
        push    hl
        ld      hl,(mu_fr)
        ld      a,l
        and     31
        call    z,mu_deep               ; κάθε 32 frames το βάθος
        inc     hl
        ld      (mu_fr),hl
        ld      hl,mu_bt
        dec     (hl)
        call    z,mu_ring               ; η επόμενη καμπάνα
        ; --- σβήσιμο: η καμπάνα στη φάση 0, η ηχώ στη 2 ---
        ld      hl,mu_dc
        ld      a,(hl)
        inc     a
        and     3
        ld      (hl),a
        jr      nz,mue_fade
        ld      hl,mu_a
        ld      a,(hl)
        or      a
        jr      z,mue_fade
        dec     (hl)
        ld      hl,mu_dirty
        set     0,(hl)
        ; Η ΗΧΩ: η ίδια νότα, όταν η καμπάνα πέφτει από το 6 στο 5 — 11 ticks
        ; μετά τον χτύπο, όσο το «12 frames» του tools/music.py (ECHO_T), χωρίς
        ; δικό της μετρητή. Η επόμενη καμπάνα αργεί τουλάχιστον 32.
        cp      6
        jr      nz,mue_fade
        ld      a,(mu_a + 1)
        ld      (mu_c + 1),a
        ld      a,MU_ECHO
        ld      (mu_c),a
        set     2,(hl)
mue_fade:
        ld      a,(mu_dc)
        cp      2
        jr      nz,muo_go
        ld      hl,mu_c
        ld      a,(hl)
        or      a
        jr      z,muo_go
        dec     (hl)
        ld      hl,mu_dirty
        set     2,(hl)
muo_go:
        ; --- στον AY, μόνο αν κάτι άλλαξε ---
        ld      a,(mu_dirty)
        or      a
        jr      z,muo_done
        ld      hl,MU_PC + 1
        add     hl,sp
        ld      a,(hl)                  ; η σελίδα του PC που διακόπηκε
        cp      in_scan >> 8
        jr      z,muo_done
        cp      snd_reg >> 8
        jr      z,muo_done
        ; ανά κανάλι: με εφέ, το bit μένει ως να τελειώσει
        ld      hl,mu_dirty
        ld      a,(sn_st)
        or      a
        jr      nz,muo_b
        bit     0,(hl)
        jr      z,muo_b
        res     0,(hl)
        ld      hl,mu_a
        xor     a                       ; R0, R1, R8
        call    mu_ch
        ld      hl,mu_dirty
muo_b:
        ld      a,(sn_st + SND_REC)
        or      a
        jr      nz,muo_c
        bit     1,(hl)
        jr      z,muo_c
        res     1,(hl)
        ld      hl,mu_b
        ld      a,2                     ; R2, R3, R9
        call    mu_ch
        ld      hl,mu_dirty
muo_c:
        ld      a,(sn_st + 2 * SND_REC)
        or      a
        jr      nz,muo_done
        bit     2,(hl)
        jr      z,muo_done
        res     2,(hl)
        ld      hl,mu_c
        ld      a,4                     ; R4, R5, R10
        call    mu_ch
muo_done:
        pop     hl
        jp      is_out

; mu_ch — A = ο καταχωρητής της περιόδου του καναλιού (0, 2, 4), HL = η εγγραφή
; του: ένταση, περίοδος. Χαλάει A, BC, HL.
mu_ch:
        push    af
        rrca
        add     a,8
        call    snd_reg                 ; R8 + κανάλι: η ένταση
        pop     af
        call    snd_reg                 ; η περίοδος, χαμηλό
        inc     a
        jp      snd_reg                 ; ...και ψηλό

; mu_deep — κάθε 32 frames, HL = frame (μένει): η ένταση του βάθους, και κάθε
; 512 η συγχορδία.
mu_deep:
        push    de
        ld      a,h
        and     1
        or      l
        jr      nz,mud_vol
        ld      a,h
        and     6                       ; (frame >> 9 & 3) * 2
        add     a,mu_chords & 255
        ld      e,a
        ld      d,mu_chords >> 8
        ld      a,(de)
        ld      (mu_b + 1),a
        inc     e
        ld      a,(de)
        ld      (mu_b + 2),a
mud_vol:
        push    hl
        add     hl,hl
        add     hl,hl
        add     hl,hl
        ld      a,h
        and     15                      ; frame >> 5: ποιο 32άρι της συγχορδίας
        add     a,mu_swell & 255
        ld      l,a
        ld      h,mu_swell >> 8
        ld      a,(hl)
        ld      (mu_b),a
        ld      hl,mu_dirty
        set     1,(hl)
        pop     hl
        pop     de
        ret

; mu_ring — ο χτύπος έφτασε, HL = mu_bt: ο επόμενος σε 32-95 frames, και μία
; στις τέσσερις φορές σιωπή, αλλιώς ένα ή δύο σκαλιά πάνω ή κάτω.
mu_ring:
        push    de
        call    mu_rand
        ld      d,a
        and     63
        add     a,32
        ld      (hl),a
        ld      a,d
        and     #C0
        jr      z,mub_x                 ; 1/4: σιωπή
        call    mu_rand
        rrca
        rrca
        rrca
        and     3
        sub     2
        jr      c,mub_step              ; 0 1 -> -2 -1
        inc     a                       ; 2 3 -> +1 +2
mub_step:
        ld      hl,mu_deg
        add     a,(hl)
        jp      p,mub_lo
        ld      a,1                     ; κάτω από το A4: ένα πάνω του
mub_lo:
        cp      10
        jr      c,mub_hi
        ld      a,8                     ; πάνω από το G6: ένα κάτω του
mub_hi:
        ld      (hl),a
        add     a,mu_scale & 255
        ld      e,a
        ld      d,mu_scale >> 8
        ld      a,(de)
        ld      (mu_a + 1),a            ; το πάνω byte μένει 0: όλες < 256
        ld      a,MU_BELL
        ld      (mu_a),a
        ld      hl,mu_dc
        ld      (hl),0
        inc     hl                      ; mu_dirty
        set     0,(hl)
mub_x:
        pop     de
        ret

; mu_rand — 16-bit Galois LFSR (#B400), όπως το tools/music.py. A = το χαμηλό.
mu_rand:
        push    hl
        ld      hl,(mu_rnd)
        srl     h
        rr      l
        jr      nc,mur_0
        ld      a,h
        xor     #B4
        ld      h,a
mur_0:
        ld      (mu_rnd),hl
        ld      a,l
        pop     hl
        ret

; Οι πίνακες: ένα add στο χαμηλό byte (assert).
mu_scale:   db 142, 120, 106, 95, 80, 71, 60, 53, 47, 40   ; A4 C5 D5 E5 G5 A5 C6 D6 E6 G6
mu_chords:  dw 568, 716, 478, 638                          ; A2 F2 C3 G2
mu_swell:   db 0, 0, 0, 1, 2, 3, 3, 3, 3, 3, 3, 3, 3, 3, 1, 0
mu_tab_end:
        assert  mu_scale >> 8 == (mu_tab_end - 1) >> 8

; Η κατάσταση· οι αρχικές τιμές όπως του tools/music.py.
mu_fr:      dw 0
mu_rnd:     dw #ACE1
mu_deg:     db 4
mu_bt:      db 20
mu_dc:      db 0                        ; τα δύο μαζί (mu_ring)
mu_dirty:   db 0                        ; bit 0-2: το κανάλι θέλει εγγραφή
; ανά κανάλι: ένταση, περίοδος
mu_a:       db 0
            dw 0
mu_b:       db 0
            dw 0
mu_c:       db 0
            dw 0
