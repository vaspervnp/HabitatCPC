; button.asm — ένα κουμπί στην οθόνη (DESIGN §9.3, βήμα 84). Τράπεζα 2: τρέχει
; μόνο όταν αλλάζει η μπάρα (src/bar.asm) ή στην οθόνη βοήθειας (src/help.asm).
;
; ΤΟ ΚΟΥΜΠΙ, 20 x 15 pixel Mode 1 (5 bytes, 15 γραμμές):
;
;   ...####....##### . .     οκτάγωνο 18 x 15 στις στήλες 1-18: πάνω και κάτω
;   ..#..............#..     πλευρά 12 pixel, λοξές γωνίες τριών, και δύο
;   .#....σύμβολο.....#.     στήλες κενό ως το επόμενο
;   #.....12 x 11......#     το σύμβολο (tools/buttons.py) στις στήλες 4-15 =
;   ...                      bytes 1-3, γραμμές 2-12
;   D#..................     το γράμμα του πλήκτρου: το σώμα 3x5 του γλύφου
;   ...                      του HUD (γραμμές 1-5) στο byte 0, γραμμές 10-14,
;                            πάνω από την κάτω αριστερή γωνία
;
; Ενα bit το pixel στο σύμβολο, και το χρώμα το διαλέγει η κατάσταση: το byte
; Mode 1 ενός μισού byte n είναι (n | n << 4) AND μάσκα, με μάσκα #0F για το
; pen 2 (πράσινο), #F0 για το 1 (κόκκινο), #FF για το 3 (λευκό).


; ---------------------------------------------------------------------------
; sl_draw — HL = η στήλη 0 της ΣΕΙΡΑΣ οθόνης του κουμπιού, από το cam_p (το
; κουμπί πιάνει τις γραμμές 1-7 της και 0-7 της επόμενης), A = κουμπί ή
; BT_NONE για άδεια θέση, C = BS_*. Γυρίζει με την τράπεζα του (hud_pg).
; ---------------------------------------------------------------------------
sl_draw:
        ld      (sl_at),hl
        ld      (sl_id),a
        ld      a,c
        add     a,a
        add     a,a                     ; x 4
        ld      hl,sl_pens
        call    ob_addu
        ld      de,sl_po
        ld      bc,4
        ldir                            ; sl_po, sl_pi, sl_ctl
        ld      a,(sl_id)
        cp      BT_NONE
        jr      nz,sld_btn
        ld      hl,sl_buf               ; άδεια θέση: όλα μαύρα, χωρίς σύνθεση
        ld      de,sl_buf + 1
        ld      bc,15 * BAR_W - 1
        ld      (hl),b                  ; B = 0
        ldir
        jp      sld_blit
sld_btn:
        ld      l,a
        ld      h,0
        ld      d,h
        ld      e,l
        add     hl,hl
        add     hl,hl
        add     hl,hl
        add     hl,hl
        add     hl,de                   ; x 17
        ld      de,G_btn_gfx
        add     hl,de
        push    hl
        add     a,a                     ; το A είναι ακόμη το sl_id (sld_btn)
        add     a,a
        ld      hl,bt_tab
        call    ob_addu
        ld      a,(hl)                  ; το γράμμα
        pop     hl
sld_ptr:
        ld      (sl_pic),hl
        ld      de,11
        add     hl,de
        ld      (sl_piq),hl             ; τα pixel 8-11, δύο γραμμές το byte
        ld      l,a
        ld      h,0
        add     hl,hl
        add     hl,hl
        add     hl,hl
        ld      de,G_font_m1 - 32 * 8 + 1       ; η γραμμή 1 του γλύφου
        add     hl,de
        ld      (sl_gly),hl
        ; --- ΤΡΑΠΕΖΑ 7: τα σύμβολα και ο γλύφος ---
        ld      bc,GA_PORT + PAGE_B7
        out     (c),c
        ; ΤΟ ΧΡΩΜΑ ΤΟΥ ΣΥΜΒΟΛΟΥ ΑΠΟ ΠΙΝΑΚΑ: n x #11 AND μάσκα, ένα ld ανά μισό
        ; byte, από έναν από τρεις σταθερούς πίνακες (το or του sld_ct δείχνει
        ; τον σωστό). Η πρώτη γραφή το υπολόγιζε κάθε φορά, με πέντε ob_addu
        ; ανά γραμμή, και ένα κουμπί κόστιζε 5,3 ms.
        ld      hl,(sl_ctl)
        ld      a,l
        ld      (sld_ct + 3),a
        ld      a,h
        ld      (sld_ct + 6),a
        ; --- ΤΟ ΟΚΤΑΓΩΝΟ ΕΙΝΑΙ ΣΤΑΘΕΡΕΣ: C = η μάσκα του, και κάθε γραμμή του
        ; είναι γνωστή (οι γραμμές 0, 1, 13, 14 χωρίς σύμβολο) ---
        ld      a,(sl_po)
        ld      c,a
        ld      de,sl_buf
        xor     a                       ; γραμμή 0: η πάνω πλευρά
        ld      (de),a
        inc     de
        call    sld_po3
        xor     a
        ld      (de),a
        inc     de
        ld      a,#11                   ; γραμμή 1
        and     c
        ld      (de),a
        inc     de
        call    sld_zero3
        ld      a,#88
        and     c
        ld      (de),a
        inc     de
        ld      b,2
sld_pl:                                 ; γραμμές 2-12: το σύμβολο
        ld      a,b
        cp      10
        jr      c,sld_ol
        call    sld_gl                  ; 10-12: το γράμμα
        jr      sld_b0
sld_ol:
        cp      3
        ld      a,#22
        jr      c,sld_o0
        ld      a,#44
sld_o0:
        and     c
sld_b0:
        ld      (de),a
        inc     de
        call    sld_pic
        ld      a,b
        cp      3
        jr      c,sld_44
        cp      12
        ld      a,#22
        jr      c,sld_o4
sld_44:
        ld      a,#44
sld_o4:
        and     c
        ld      (de),a
        inc     de
        inc     b
        ld      a,b
        cp      13
        jr      c,sld_pl
        call    sld_gl                  ; γραμμή 13
        ld      (de),a
        inc     de
        call    sld_zero3
        ld      a,#88
        and     c
        ld      (de),a
        inc     de
        call    sld_gl                  ; γραμμή 14: η κάτω πλευρά
        ld      (de),a
        inc     de
        call    sld_po3
        xor     a
        ld      (de),a
        ; --- στην οθόνη ---
sld_blit:
        ld      hl,(sl_at)
        ld      de,(cam_p)
        add     hl,de
        ld      (sl_at),hl
        ; ΓΡΑΜΜΗ-ΓΡΑΜΜΗ ΜΕ ldi, εκτός αν μία από τις δύο σειρές πέφτει πάνω στο
        ; τύλιγμα του δαχτυλιδιού (#7FF -> 0) μέσα στα πέντε της bytes: τότε
        ; στήλη-στήλη, η κάθε μία με δική της θέση. Μία θέση στις ~400.
        ld      a,h
        and     7
        cp      7
        jr      nz,sld_w2
        ld      a,l
        cp      #100 - BAR_W + 1
        jr      nc,sld_slow
sld_w2:
        ld      de,80
        add     hl,de
        ld      a,h
        and     7
        cp      7
        jr      nz,sld_fast
        ld      a,l
        cp      #100 - BAR_W + 1
        jr      nc,sld_slow
sld_fast:
        push    hl                      ; (sl_at) + 80, από το sld_w2
        ld      hl,sl_buf
        ld      (sl_src),hl
        ld      hl,(sl_at)
        ld      bc,#0701                ; 7 γραμμές από τη γραμμή 1
        call    sld_row
        pop     hl
        ld      bc,#0800                ; 8 από τη 0, στην επόμενη σειρά
        call    sld_row
        jr      sld_out
sld_slow:
        ld      c,0
sld_col:
        ld      hl,sl_buf
        ld      a,c
        call    ob_addu
        ex      de,hl                   ; DE = sl_buf + στήλη
        ld      hl,(sl_at)
        ld      a,c
        call    ob_addu
        push    hl
        call    sld_adr
        ld      a,h
        add     a,8                     ; γραμμή 1 της σειράς
        ld      h,a
        ld      b,7
        call    sld_down
        pop     hl
        ld      a,80                    ; η επόμενη σειρά, γραμμές 0-7
        call    ob_addu
        call    sld_adr
        ld      b,8
        call    sld_down
        inc     c
        ld      a,c
        cp      BAR_W
        jr      c,sld_col
sld_out:
        ld      bc,(hud_pg)
        out     (c),c
        ret

; sld_row — HL = θέση στο δαχτυλίδι (χωρίς μάσκα), C = πρώτη γραμμή, B = πόσες:
; πέντε bytes ανά γραμμή από το (sl_src).
sld_row:
        ld      a,c
        rlca
        rlca
        rlca                            ; γραμμή x 8
        ld      c,a
        ld      a,h
        and     7
        or      c
        or      SCR_BASE / 256
        ld      d,a
        ld      e,l
        ld      hl,(sl_src)
sldr_lp:
        push    bc
        push    de
        ldi
        ldi
        ldi
        ldi
        ldi
        pop     de
        pop     bc
        ld      a,d
        add     a,8
        ld      d,a
        djnz    sldr_lp
        ld      (sl_src),hl
        ret

; sld_pic — τα bytes 1-3 μιας γραμμής του συμβόλου (B = γραμμή κουμπιού).
; Κρατά BC.
sld_pic:
        ld      hl,(sl_pic)
        ld      a,(hl)                  ; pixel 0-7
        inc     hl
        ld      (sl_pic),hl
        push    af
        rrca
        rrca
        rrca
        rrca
        call    sld_ct
        pop     af
        call    sld_ct
        ld      hl,(sl_piq)             ; pixel 8-11: δύο γραμμές το byte
        ld      a,(hl)
        bit     0,b                     ; ζυγή γραμμή κουμπιού = ζυγή συμβόλου
        jr      nz,sldp_odd
        rrca
        rrca
        rrca
        rrca
        jr      sld_ct
sldp_odd:
        inc     hl
        ld      (sl_piq),hl
        ; fall through
; sld_ct — A = μισό byte στο κάτω μισό: το χρώμα του από τον πίνακα της
; κατάστασης, στο (DE).
sld_ct:
        and     #0F
        or      sl_ctg & 255            ; ΜΠΑΛΩΜΕΝΑ: ο πίνακας της κατάστασης,
        ld      l,a                     ; κάτω και πάνω byte (sl_draw)
        ld      h,sl_ctg >> 8
        ld      a,(hl)
        ld      (de),a
        inc     de
        ret

; sld_gl — A = η επόμενη γραμμή του γλύφου.
sld_gl:
        ld      hl,(sl_gly)
        ld      a,(hl)
        inc     hl
        ld      (sl_gly),hl
        ret

; sld_po3 / sld_zero3 — τρία bytes: η πλευρά (C), ή μαύρα.
sld_po3:
        ld      a,c
        jr      sld_3b
sld_zero3:
        xor     a
sld_3b:
        ld      (de),a
        inc     de
        ld      (de),a
        inc     de
        ld      (de),a
        inc     de
        ret

sld_adr:
        ld      a,h
        and     7
        or      SCR_BASE / 256
        ld      h,a
        ret

; sld_down — B γραμμές: από το (DE) ανά BAR_W, στο (HL) ανά #800.
sld_down:
        ld      a,(de)
        ld      (hl),a
        ld      a,e
        add     a,BAR_W
        ld      e,a
        jr      nc,sdd_nc
        inc     d
sdd_nc:
        ld      a,h
        add     a,8
        ld      h,a
        djnz    sld_down
        ret

; (Τα δεδομένα του sl_draw ζουν στην τράπεζα 0, στο τέλος του src/bar.asm: εδώ
; δεν χωρούσαν.)

; ΑΠΟ ΤΟ src/bar.asm: κρύος κώδικας της μπάρας, εδώ γιατί η τράπεζα 0 έφτασε στη
; σκαλωσιά του tests/test_loop.py.

; ---------------------------------------------------------------------------
; bk_gen — ο κώδικας του bk_scan για τη μπάρα του bw_id.
; ---------------------------------------------------------------------------
bk_gen:
        ld      hl,bk_code
        ld      de,bk_ids
        ld      c,0                     ; θέση
bkg_lp:
        push    hl
        ld      hl,bw_id
        ld      a,c
        call    ob_addu
        ld      a,(hl)
        pop     hl
        cp      BT_NONE
        jr      z,bkg_next
        ld      (de),a                  ; bk_ids[k] = κουμπί
        inc     de
        push    de
        push    hl
        add     a,a
        add     a,a
        inc     a                       ; 4 x κουμπί + 1: η γραμμή
        ld      hl,bt_tab
        call    ob_addu
        ld      a,(hl)
        inc     hl
        ld      e,(hl)                  ; μάσκα
        pop     hl
        ld      (hl),#3A                ; ld a,(nn)
        inc     hl
        add     a,key_now & 255
        ld      (hl),a
        inc     hl
        inc     hl                      ; το πάνω byte δεν αλλάζει (assert κάτω)
        inc     hl                      ; and
        ld      (hl),e
        ld      de,4                    ; jr z, inc c: ίδια πάντα· το DE
        add     hl,de                   ; ξαναγυρίζει αμέσως
        pop     de
bkg_next:
        inc     c
        ld      a,c
        cp      BAR_N
        jr      c,bkg_lp
        ; --- το τέλος: jr bk_none στη θέση της επόμενης — εκτός αν η μπάρα
        ; γέμισε και τα δεκαπέντε, όπου η επόμενη θέση ΕΙΝΑΙ το bk_none ---
        ld      a,l
        cp      bk_none & 255
        ret     z
        ld      (hl),#18
        inc     hl
        ld      a,(bk_none - 1) & 255
        sub     l
        ld      (hl),a
        ret

; ---------------------------------------------------------------------------
; bar_more — οι θέσεις που διαφέρουν από ό,τι πρέπει, ΤΟ ΠΟΛΥ BAR_PER τη φορά.
; Από το bar_sync, και από το ui_tick όσο μένουν (bs_pend).
;
; ΛΙΓΑ ΑΝΑ FRAME, ΓΙΑ ΝΑ ΜΗ ΧΑΝΕΤΑΙ ΠΑΤΗΜΑ. Ενα κουμπί είναι ~3 ms, και όλη η
; μπάρα μαζί 50 ms: τόσο κρατούσε ένα frame όταν ένα βελάκι στο MENU περνούσε
; σε άλλη ομάδα, και το επόμενο βελάκι, πατημένο τρία frames, έπεφτε ολόκληρο
; μέσα του (το test_game το έχασε). Δύο ανά frame: μια ομάδα ανοίγει σε οκτώ
; frames, από αριστερά προς τα δεξιά.
; ---------------------------------------------------------------------------
bar_more:
        ld      ix,bw_id
        ld      bc,BAR_PER * 256        ; B = όσα μένουν, C = θέση
bsd_lp:
        ld      d,(ix + 0)              ; κουμπί
        ld      e,(ix + BAR_N)          ; κατάσταση
        ld      a,d
        cp      (ix + 2 * BAR_N)
        jr      nz,bsd_draw
        ld      a,e
        cp      (ix + 3 * BAR_N)
        jr      z,bsd_next
bsd_draw:
        ld      a,b
        or      a
        jr      z,bsd_pend              ; ξόδεψε το frame: τα υπόλοιπα μετά
        dec     b
        ld      (ix + 2 * BAR_N),d
        ld      (ix + 3 * BAR_N),e
        push    bc
        push    ix
        ld      a,c
        add     a,a
        add     a,a
        add     a,c                     ; x BAR_W
        ld      hl,BAR_OFF
        call    ob_addu
        ld      a,d
        ld      c,e
        call    sl_draw                 ; src/button.asm, τράπεζα 2
        pop     ix
        pop     bc
bsd_next:
        inc     ix
        inc     c
        ld      a,c
        cp      BAR_N
        jr      c,bsd_lp
        xor     a
        ld      (bs_pend),a
        ret
bsd_pend:
        inc     a                       ; A = B = 0 (bsd_draw) -> 1
        ld      (bs_pend),a
        ret

; ---------------------------------------------------------------------------
; bt_text — A = κουμπί -> HL = το όνομά του στο t_help· η γραμμή της βοήθειας
; αμέσως μετά το 0 του. Η τράπεζα 7 πρέπει να είναι μέσα.
; ---------------------------------------------------------------------------
bt_text:
        ld      hl,t_help
        add     a,a
        ld      b,a
        inc     b
        jr      btt_t
btt_lp:
        ld      a,(hl)
        inc     hl
        or      a
        jr      nz,btt_lp
btt_t:
        djnz    btt_lp
        ret

