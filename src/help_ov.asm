; help_ov.asm — το σώμα της οθόνης βοήθειας (βήμα 108): τρίτος κώδικας στις
; τρύπες του DIST, μετά την κατεδάφιση και το σώσιμο (src/demolish.asm). Το
; φέρνει στο GH_BUF και το καλεί το hp_show του src/help.asm, με τον κέρσορα
; σβηστό· ό,τι ξαναζωγραφίζει μετά το κάνει εκείνο, αφού γυρίσει: ο κέρσορας
; γράφει το αρχείο του στο GH_BUF, πάνω σε αυτόν τον κώδικα.

hpo_show:
        call    snd_off
        di
        call    is_m1
        call    hw_clear
        ld      bc,GA_PORT + PAGE_B7
        call    hud_page                ; ο γλύφος γυρίζει στην 7: εκεί τα κείμενα
        ld      hl,HP_ROWS * 256
        ld      (hp_id),hl              ; hp_id = 0, hp_row = HP_ROWS
        ld      hl,t_help               ; τα κείμενα στη σειρά, όχι bt_text για
        push    hl                      ; το καθένα: ~90 ms λιγότερα. ΣΤΗ ΣΤΟΙΒΑ
        ld      hl,-HUD_TOPB            ; σειρά οθόνης 0, στήλη 0
        ld      (hp_at),hl
hp_lp:
        ; --- το κουμπί: λευκό αν είναι ομάδα, όπως στη μπάρα ---
        ld      a,(hp_id)
        ld      b,a                     ; το ob_addu κρατά το BC
        add     a,a
        add     a,a
        ld      hl,bt_tab + 3
        call    ob_addu
        ld      a,(hl)
        and     #E0                     ; KB_GROUP << 5 == 0
        ld      c,BS_WHITE
        jr      z,hp_grp
        ld      c,BS_GREEN
hp_grp:
        ld      hl,(hp_at)
        ld      a,b
        call    sl_draw
        ; --- το όνομα λευκό, η γραμμή του πράσινη από κάτω ---
        ld      a,HP_TEXT
        call    hp_goa
        pop     hl                      ; το κείμενο (το push πιο πάνω)
        call    hud_text
        inc     hl
        push    hl
        ld      a,HP_TEXT + 80
        call    hp_goa
        pop     hl
        call    hp_green
        inc     hl
        push    hl                      ; το επόμενο κείμενο
        ; --- το επόμενο: δύο σειρές πιο κάτω, ή η επόμενη στήλη ---
        ld      de,160
        ld      hl,hp_row
        dec     (hl)
        jr      nz,hp_same
        ld      (hl),HP_ROWS
        ld      de,HP_COLW - 160 * (HP_ROWS - 1)
hp_same:
        dec     hl                      ; hp_id
        inc     (hl)
        ld      a,(hl)
        ld      hl,(hp_at)
        add     hl,de
        ld      (hp_at),hl
        cp      BT_N
        jr      c,hp_lp
        pop     hl                      ; το push του τελευταίου
        ; --- η σειρά 24 ---
        ld      hl,-HUD_TOPB + 24 * 80
        call    hp_go
        ld      hl,t_hfoot
        call    hud_text7               ; η 7 είναι ήδη μέσα· γυρίζει στην 1
        ; --- ΕΝΑ ΠΛΗΚΤΡΟ: πρώτα να αφεθεί το ?, μετά ένα οποιοδήποτε, και να
        ; αφεθεί κι αυτό — αλλιώς το ίδιο πάτημα θα έκανε κάτι στο παιχνίδι ---
        call    hp_up
hp_wait:
        call    hp_any
        jr      z,hp_wait
        ; και το hp_up, πίσω στο hp_show, που ξαναζωγραφίζει

hp_up:
        call    hp_any
        jr      nz,hp_up
        ret

; hp_any — μια σάρωση (in_scan), και NZ αν είναι πατημένο οτιδήποτε, και το
; χειριστήριο.
hp_any:
        call    in_scan
        ld      hl,key_now
        ld      b,KEY_LINES
        ld      a,#FF
hpa_lp:
        and     (hl)
        inc     hl
        djnz    hpa_lp
        inc     a                       ; #FF (τίποτα) -> 0
        ret

; hp_go — HL = θέση από το cam_p: εκεί το επόμενο κελί του HUD, χωρίς κρυφή μνήμη.
; hp_goa — το ίδιο, στη θέση hp_at + A.
hp_goa:
        ld      hl,(hp_at)
        call    ob_addu
hp_go:
        ld      de,0
        ld      (hud_sp),de
        jp      hg_p                    ; src/hud.asm: το τέλος του hud_go

; hp_green — HL = κείμενο (τράπεζα 7, μέσα): όπως το hud_text, σε pen 2.
hp_green:
        ld      a,(hl)
        or      a
        ret     z
        inc     hl
        push    hl
        ld      l,a
        ld      h,0
        add     hl,hl
        add     hl,hl
        add     hl,hl
        ld      de,G_font_m1 - 32 * 8
        add     hl,de
        ex      de,hl
        call    hud_scr                 ; src/hud.asm
        ld      b,8
hpg_ln:
        ld      a,(de)
        inc     e                       ; ο γλύφος δεν διασχίζει σελίδα
        and     #0F
        ld      (hl),a
        ld      a,h
        add     a,8
        ld      h,a
        djnz    hpg_ln
        call    hud_next
        pop     hl
        jr      hp_green

hp_at:      dw 0
hp_id:      db 0
hp_row:     db 0
        assert  hp_row == hp_id + 1
