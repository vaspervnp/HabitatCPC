; map_ov.asm — ο χάρτης του κόσμου (βήμα 186, DESIGN §9.3): το TAB από την
; κύρια οθόνη. ΣΤΙΣ ΤΡΥΠΕΣ, στο OV_R3 μετά την κατεδάφιση (src/main.asm): το
; φέρνει στο GH_BUF και το καλεί το mp_open (src/map.asm), με τον κέρσορα
; σβηστό, και ξαναζωγραφίζει την οθόνη αφού γυρίσει.
;
; Ο ΠΑΙΚΤΗΣ ρώτησε «υπάρχει minimap;» και ζήτησε «φτιάξε τον χάρτη σε σελίδα
; με πλήκτρο». Διάλεξε (AskUserQuestion, 2026-11-05): όλη η οθόνη σε Mode 1,
; τέσσερα χρώματα, όλος ο κόσμος, ένα pixel το tile (128 x 128· το pixel του
; Mode 1 είναι τετράγωνο απέναντι στο tile του παιχνιδιού, 8 x 16 του Mode 0).
;   μαύρο   το έδαφος που χτίζεται: έδαφος, σκόνη
;   καφέ    ό,τι δεν χτίζεται: βράχος, βουνό, κρατήρας (ο κρατήρας ως λάθος
;           «μαύρο» στην ερώτηση, όπως το είπε το DESIGN)
;   μπλε    το νερό και το βαθύ νερό
;   λευκό   η αποικία: ό,τι έχει κατοχή, και το θεμέλιο (τα μονοπάτια)
;   οι φλέβες (βουνό με το bit του πόρου): καφέ με λευκές κουκκίδες,
;           σκακιέρα, για να ξεχωρίζουν από τη λευκή αποικία
;   το πλαίσιο της οθόνης (20 x 10) με XOR: αναποδογυρίζει ό,τι πατά.
; Τα βέλη κουνούν το πλαίσιο (ένα tile, και κρατημένα κάθε δεύτερο frame μετά
; από MP_DELAY), το SPACE ή το COPY πηγαίνει την κάμερα και τον κέρσορα εκεί,
; το ESC ή ένα δεύτερο TAB γυρίζει όπως ήταν.
;
; ΤΑ PENS ΤΟΥ MODE 1, ΔΥΟ BITS ΑΝΑ PIXEL: το pixel 0 στα bits 7 και 3, το 3
; στα 4 και 0. Ο πίνακας δίνει το pen ενός byte του κόσμου στη θέση του pixel
; 3 (bits 4, 0), και ο βρόχος σπρώχνει αριστερά: μετά από τέσσερα tiles το
; πρώτο είναι στο pixel 0. Μια φλέβα είναι MP_VMARK στον πίνακα, και το mp_vein
; διαλέγει λευκό ή καφέ από την ισοτιμία του x + y: η σκακιέρα. Με δύο
; πίνακες, έναν ανά ισοτιμία, ο κώδικας δεν χωρούσε κάτω τους (692 bytes).
; ---------------------------------------------------------------------------

MP_ROW0     equ 3                       ; η πρώτη σειρά οθόνης του χάρτη, ως τη 18
MP_COL      equ 24                      ; η στήλη του, σε bytes: (80 - 32) / 2
MP_BASE     equ MP_ROW0 * 80 + MP_COL - HUD_TOPB    ; από το cam_p (hp_go)
MP_TA       equ #9B00                   ; ο πίνακας: byte του κόσμου -> pen
MP_VMARK    equ #80                     ; στον πίνακα: φλέβα (το bit 7)
MP_DELAY    equ 12                      ; frames ως την επανάληψη ενός βέλους
MP_KEYS     equ 1 << A_UP | 1 << A_DOWN | 1 << A_LEFT | 1 << A_RIGHT
        assert  (MP_TA & 255) == 0
        assert  A_UP == 0 && A_DOWN == 1 && A_LEFT == 2 && A_RIGHT == 3
        assert  W_MOUNTAIN == 3 && W_OCC_MASK == #30

mpo_show:
        call    snd_off
        di
        ld      bc,GA_PORT + RMR_MODE1
        ld      hl,mp_pal
        call    isf_go                  ; src/isr.asm: Mode 1 και τα τρία pens
        call    hw_clear
        ; --- ο πίνακας ---
        ld      hl,MP_TA
mpt_lp:
        ld      a,l
        ld      c,#11                   ; λευκό: κατειλημμένο
        and     W_OCC_MASK
        jr      nz,mpt_put
        ld      a,l
        and     7
        ld      e,a
        ld      d,0
        push    hl
        ld      hl,mp_cls
        add     hl,de
        ld      c,(hl)
        pop     hl
        cp      W_MOUNTAIN
        jr      nz,mpt_put
        bit     3,l                     ; ο πόρος: φλέβα
        jr      z,mpt_put
        ld      c,MP_VMARK
mpt_put:
        ld      (hl),c
        inc     l
        jr      nz,mpt_lp
        ; --- ο κόσμος, σειρά-σειρά ---
        ld      bc,GA_PORT + PAGE_B4
        out     (c),c
        xor     a
mpw_row:
        ld      (mp_y),a
        ld      b,a
        ld      c,0
        call    mp_addr                 ; HL = η οθόνη στο (0, y)
        push    hl
        exx
        pop     hl                      ; HL' = η οθόνη
        exx
        ld      a,(mp_y)
        ld      l,0
        srl     a
        rr      l
        add     a,#40
        ld      h,a                     ; HL = #4000 + 128 y: η σειρά του κόσμου
        ld      d,MP_TA >> 8
mpw_t:
        ; ΤΕΣΣΕΡΑ TILES, ΞΕΔΙΠΛΩΜΕΝΑ: με βρόχο και «ld a,l · and 3» ανά tile ο
        ; χάρτης ήθελε 27 frames (540 ms)· το πρώτο μπαίνει κατευθείαν στο B.
        ld      e,(hl)
        inc     l
        ld      a,(de)
        or      a
        call    m,mp_vein
        ld      b,a
        repeat  3
        ld      e,(hl)
        inc     l
        ld      a,(de)
        or      a
        call    m,mp_vein
        sla     b
        or      b
        ld      b,a
        rend
        exx
        ld      (hl),a
        inc     l
        call    z,mp_wrap
        exx
        ld      a,l
        and     #7F
        jr      nz,mpw_t                ; ως το τέλος της σειράς (L στο #00 ή #80)
        ld      a,(mp_y)
        inc     a
        jp      p,mpw_row               ; ως το 127
        ; --- τα κείμενα, λευκά, και τα δείγματα των χρωμάτων ---
        ld      bc,GA_PORT + PAGE_B7
        call    hud_page                ; ο γλύφος στην 7
        ld      hl,mp_txt
mps_tx:
        ld      e,(hl)
        inc     hl
        ld      d,(hl)
        inc     hl
        ld      a,d
        or      e
        jr      z,mps_sw
        push    hl
        ex      de,hl
        call    mp_go
        pop     hl
        call    hud_text                ; κρατά το HL στο 0 του τέλους
        inc     hl
        jr      mps_tx
mps_sw:
        ld      hl,mp_swat
mps_sl:
        ld      e,(hl)
        inc     hl
        ld      d,(hl)
        inc     hl
        ld      a,d
        or      e
        jr      z,mps_fr
        push    hl
        ex      de,hl
        call    mp_go
        call    hud_scr                 ; HL = η οθόνη του κελιού
        pop     de
        ld      a,(de)                  ; ζυγές γραμμές
        inc     de
        ld      c,a
        ld      a,(de)                  ; μονές
        inc     de
        push    de
        ld      b,4
mps_ln:
        ld      (hl),c
        call    mp_down
        ld      (hl),a
        call    mp_down
        djnz    mps_ln
        pop     hl
        jr      mps_sl
mps_fr:
        call    ov_b1
        ; --- το πλαίσιο εκεί που είναι η κάμερα ---
        ld      hl,(cam_tx)             ; cam_tx, cam_ty διπλανά
        ld      a,l
        add     a,64
        ld      l,a
        ld      a,h
        add     a,64
        ld      h,a
        ld      (mp_fx),hl
        call    mp_frame
        call    mp_up                   ; το TAB να αφεθεί
mpo_lp:
        call    mp_vs
        call    in_read                 ; act_now, act_hit
        ld      a,(key_now + 8)         ; ESC #04, TAB #10: πίσω όπως ήταν
        and     #04 | #10
        cp      #04 | #10
        jr      nz,mpo_out
        ld      a,(act_hit)
        and     1 << A_FIRE | 1 << A_MENU | 1 << A_CANCEL
        jr      nz,mpo_go
        ld      hl,mp_rep
        ld      a,(act_hit)
        and     MP_KEYS
        jr      z,mpo_held
        ld      (hl),MP_DELAY
        jr      mpo_move
mpo_held:
        ld      a,(act_now)
        and     MP_KEYS
        jr      z,mpo_lp
        dec     (hl)
        jr      nz,mpo_lp
        ld      (hl),2                  ; κρατημένο: κάθε δεύτερο frame
mpo_move:
        push    af
        call    mp_frame                ; σβήνει (XOR)
        pop     af
        ld      hl,(mp_fx)
        rra
        jr      nc,mpm_dn
        dec     h                       ; πάνω
mpm_dn:
        rra
        jr      nc,mpm_lf
        inc     h
mpm_lf:
        rra
        jr      nc,mpm_rt
        dec     l
mpm_rt:
        rra
        jr      nc,mpm_cl
        inc     l
mpm_cl:
        ; ΣΤΟ ΧΕΙΛΟΣ: 0..CAM_XMAX + 64 και 0..CAM_YMAX + 64, όσο και η κάμερα.
        ; Ενα -1 είναι 255, πάνω από το όριο: γυρίζει στο 0.
        ld      a,l
        cp      CAM_XMAX + 64 + 1
        jr      c,mpc_y
        ld      l,0
        cp      #80
        jr      nc,mpc_y
        ld      l,CAM_XMAX + 64
mpc_y:
        ld      a,h
        cp      CAM_YMAX + 64 + 1
        jr      c,mpc_ok
        ld      h,0
        cp      #80
        jr      nc,mpc_ok
        ld      h,CAM_YMAX + 64
mpc_ok:
        ld      (mp_fx),hl
        call    mp_frame                ; ξανά, στη νέα θέση
        jr      mpo_lp
mpo_go:
        and     1 << A_CANCEL           ; το fire 2 του χειριστηρίου: πίσω
        jr      nz,mpo_out
        ; --- η κάμερα στο πλαίσιο, ο κέρσορας στη μέση του ---
        ld      hl,(mp_fx)
        ld      a,l
        sub     64
        ld      l,a
        ld      a,h
        sub     64
        ld      h,a
        ld      (cam_tx),hl
        ld      a,l
        add     a,VIEW_TW / 2
        add     a,a
        ld      l,a
        ld      a,h
        add     a,VIEW_TH / 2
        add     a,a
        ld      h,a
        ld      (cur_hx),hl             ; cur_hx, cur_hy διπλανά, σε μισά tiles
mpo_out:
        call    mp_up                   ; να αφεθεί, αλλιώς θα έκανε κάτι στο παιχνίδι
        jp      ov_b1                   ; και πίσω στο mp_open με την 1

; mp_up — ώσπου να μην είναι πατημένο τίποτα, ούτε το χειριστήριο.
mp_up:
        call    in_scan
        ld      hl,key_now
        ld      b,KEY_LINES
        ld      a,#FF
mpu_lp:
        and     (hl)
        inc     hl
        djnz    mpu_lp
        inc     a
        jr      nz,mp_up
        ret

; mp_vs — η αρχή του επόμενου frame, με τις διακοπές κλειστές: το VSYNC στο
; bit 0 της θύρας B του PPI.
mp_vs:
        ld      b,#F5
mpv_in:
        in      a,(c)
        rra
        jr      c,mpv_in
mpv_out:
        in      a,(c)
        rra
        jr      nc,mpv_out
        ret

; mp_go — HL = θέση από το cam_p: εκεί το επόμενο κελί του HUD, χωρίς κρυφή
; μνήμη (το hp_go της βοήθειας, που είναι σε άλλη τρύπα).
mp_go:
        ld      de,0
        ld      (hud_sp),de
        jp      hg_p                    ; src/hud.asm

; mp_down — HL μία γραμμή πιο κάτω μέσα στο κελί (+#800).
mp_down:
        push    af
        ld      a,h
        add     a,8
        ld      h,a
        pop     af
        ret

; mp_vein — μια φλέβα: λευκό αν το x + y είναι ζυγό, αλλιώς καφέ. Το x είναι
; L - 1 (το inc l έγινε), άρα ζυγό x + y είναι μονό L + y.
mp_vein:
        ld      a,(mp_y)
        add     a,l
        rra
        ld      a,#10                   ; καφέ
        ret     nc
        ld      a,#11                   ; η λευκή κουκκίδα
        ret

; mp_wrap — το δαχτυλίδι των 2 KB της γραμμής, από το inc l που έδωσε 0
; (στο HL' του βρόχου).
mp_wrap:
        inc     h
        ld      a,h
        and     7
        ret     nz
        ld      a,h
        sub     8
        ld      h,a
        ret

; mp_frame — το πλαίσιο της οθόνης, VIEW_TW x VIEW_TH, στο (mp_fx, mp_fy) με
; XOR: δύο φορές το σβήνουν.
mp_frame:
        ld      a,(mp_fy)
        call    mp_hline
        ld      a,(mp_fy)
        add     a,VIEW_TH - 1
        call    mp_hline
        ld      a,(mp_fy)
        ld      e,VIEW_TH - 2
mpf_v:
        inc     a
        push    af
        push    de
        ld      b,a
        ld      a,(mp_fx)
        ld      c,a
        push    bc
        call    mp_px
        pop     bc
        ld      a,c
        add     a,VIEW_TW - 1
        ld      c,a
        call    mp_px
        pop     de
        pop     af
        dec     e
        jr      nz,mpf_v
        ret
; mp_hline — A = y: VIEW_TW pixels από το mp_fx.
mp_hline:
        ld      b,a
        ld      a,(mp_fx)
        ld      c,a
        ld      e,VIEW_TW
mph_lp:
        push    bc
        push    de
        call    mp_px
        pop     de
        pop     bc
        inc     c
        dec     e
        jr      nz,mph_lp
        ret
; mp_px — B = y, C = x: το pixel με XOR στο pen 3.
mp_px:
        call    mp_addr
        xor     (hl)
        ld      (hl),a
        ret

; mp_addr — B = y, C = x (0-127): HL = το byte του pixel στην οθόνη, A = η
; μάσκα του (pen 3). Η σειρά οθόνης MP_ROW0 + y / 8, η γραμμή y mod 8, η στήλη
; MP_COL + x / 4, στο δαχτυλίδι από το cam_p. Χαλάει B, DE.
mp_addr:
        ld      a,b
        and     #F8
        ld      l,a
        ld      h,0
        add     hl,hl                   ; (y / 8) * 16
        ld      d,h
        ld      e,l
        add     hl,hl
        add     hl,hl
        add     hl,de                   ; (y / 8) * 80
        ld      a,c
        rrca
        rrca
        and     #3F
        ld      e,a
        ld      d,0
        add     hl,de
        ld      de,(cam_p)
        add     hl,de
        ld      de,MP_BASE
        add     hl,de
        ld      a,h
        and     7
        ld      h,a
        ld      a,b
        and     7
        add     a,a
        add     a,a
        add     a,a
        or      h
        or      SCR_BASE / 256
        ld      h,a
        ld      a,c
        and     3
        ld      b,a
        ld      a,#88
        inc     b
mpa_m:
        dec     b
        ret     z
        rrca
        jr      mpa_m

; Τα τρία pens (το 0 είναι μαύρο): Red, Bright blue, Bright white.
mp_pal:     db GA_INK + #1C, GA_INK + #15, GA_INK + #0B
; Το pen κάθε κλάσης στη θέση του pixel 3: έδαφος, σκόνη, βράχος, βουνό, νερό,
; βαθύ νερό, κρατήρας, θεμέλιο.
mp_cls:     db #00, #00, #10, #10, #01, #01, #10, #11
        assert  W_GROUND == 0 && W_DUST == 1 && W_ROCK == 2 && W_WATER == 4
        assert  W_DEEPWATER == 5 && W_CRATER == 6 && W_FOUNDATION == 7
; Τα κείμενα: θέση από το cam_p (σειρά x 80 + στήλη· ένα γράμμα είναι ένα byte,
; 4 pixels), και το κείμενο ως το 0. Ενα 0 τελειώνει.
MP_LEG      equ 20                      ; η σειρά του υπομνήματος
mp_txt:     dw 1 * 80 + 36 - HUD_TOPB
            db "WORLD MAP",0
            dw MP_LEG * 80 + 22 - HUD_TOPB
            db "ROCK",0
            dw MP_LEG * 80 + 31 - HUD_TOPB
            db "WATER",0
            dw MP_LEG * 80 + 41 - HUD_TOPB
            db "COLONY",0
            dw MP_LEG * 80 + 52 - HUD_TOPB
            db "ORE",0
            dw 23 * 80 + 24 - HUD_TOPB
            db "ARROWS MOVE  SPACE=GO  ESC=BACK",0
            dw 0
; Τα δείγματα, ένα byte (4 pixels) πριν από κάθε λέξη: θέση, και τα bytes των
; ζυγών και των μονών γραμμών. Καφέ #F0, μπλε #0F, λευκό #FF, οι φλέβες
; σκακιέρα καφέ και λευκού (#FA, #F5).
mp_swat:    dw MP_LEG * 80 + 20 - HUD_TOPB
            db #F0, #F0
            dw MP_LEG * 80 + 29 - HUD_TOPB
            db #0F, #0F
            dw MP_LEG * 80 + 39 - HUD_TOPB
            db #FF, #FF
            dw MP_LEG * 80 + 50 - HUD_TOPB
            db #FA, #F5
            dw 0
mp_y:       db 0
mp_rep:     db 0
mp_fx:      db 0
mp_fy:      db 0
        assert  mp_fy == mp_fx + 1
