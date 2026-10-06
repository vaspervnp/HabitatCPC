; act.asm — το μενού ενεργειών: το SPACE στο LOOK (DESIGN §9.1, βήμα 80).
;
; Μία γραμμή με ό,τι μπορεί να γίνει εκεί που είναι ο κέρσορας, και μόνο αυτό.
; Αριστερά/δεξιά διαλέγει (ο κέρσορας δεν κουνιέται), FIRE ή SPACE το κάνει,
; ESC γυρίζει στο LOOK. Το πρώτο είναι πάντα το BUILD και το μενού ανοίγει
; πάντα εκεί: SPACE SPACE είναι ο κατάλογος του §9.3, όπως ως το βήμα 80 ήταν
; σκέτο SPACE.
;
;   σειρά 3   < SHIP   >  FIRE=GO ESC=BACK
;   σειρά 4    BUILD FIT INFO[SHIP]SAVE LOAD CENTRE
;
;   BUILD, INFO, SAVE, LOAD, CENTRE   πάντα
;   FIT     όταν το FIRE στο LOOK θα άνοιγε τον εξοπλισμό: θόλος κάτω από τον
;           κέρσορα, με δωμάτιο που δέχεται μηχανές (fit_can)
;   SHIP    όταν το C θα έστελνε πλοίο: αίθουσα ελέγχου, πίστα, κανένα άλλο
;           πλοίο στον δρόμο (ui_ship, ship_call)
;
; Τα πλήκτρα μένουν όλα: το μενού είναι ο δρόμος για όποιον δεν τα ξέρει.
;
; Στην τράπεζα 2, όπως ό,τι τρέχει μόνο όταν το ζητήσει ο παίκτης.

UI_ACT      equ 7
AI_BUILD    equ 0
AI_FIT      equ 1
AI_INFO     equ 2
AI_SHIP     equ 3
AI_SAVE     equ 4
AI_LOAD     equ 5
AI_HOME     equ 6
AI_N        equ 7
AI_NAME     equ 7                       ; bytes ανά όνομα, με το 0 του

        assert  A_FIRE < 8 && A_CANCEL < 8 && A_MENU < 8

; ---------------------------------------------------------------------------
; ac_open — από το LOOK, με το SPACE: ο κατάλογος του τι γίνεται εδώ.
; ---------------------------------------------------------------------------
ac_open:
        call    fit_can                 ; CY = ο εξοπλισμός ανοίγει
        ld      c,(1 << AI_N) - 1 - (1 << AI_FIT) - (1 << AI_SHIP)
        jr      nc,aco_ship
        set     AI_FIT,c
aco_ship:
        ld      a,(G_room_n + R_CONTROL)
        or      a
        jr      z,aco_list
        ld      a,(EC_PADNODE)
        inc     a
        jr      z,aco_list
        ld      a,(EC_SHSTATE)
        or      a
        jr      nz,aco_list
        set     AI_SHIP,c
aco_list:
        ; Τα bits του C γίνονται κατάλογος: ac_list = τα δυνατά, με τη σειρά.
        ; Το αριστερά/δεξιά είναι τότε το ui_lr του καταλόγου χτισίματος.
        ld      hl,ac_list
        xor     a
aco_lp:
        srl     c
        jr      nc,aco_no
        ld      (hl),a
        inc     hl
aco_no:
        inc     a
        cp      AI_N
        jr      c,aco_lp
        ld      a,l
        sub     ac_list & 255
        ld      (ac_n),a
        xor     a
        ld      (ac_sel),a              ; BUILD
        call    ui_click                ; όπως ο κατάλογος χτισίματος
        ld      a,UI_ACT
        jp      ui_ask

; ---------------------------------------------------------------------------
; ac_tick — ένα καρέ εισόδου στο μενού.
; ---------------------------------------------------------------------------
ac_tick:
        ld      a,(act_hit)
        bit     A_CANCEL,a
        jr      z,act_fire
        xor     a                       ; UI_LOOK
        jp      ui_goto
act_fire:
        and     1 << A_FIRE | 1 << A_MENU
        jr      nz,ac_do
        ld      hl,ac_sel
        ld      a,(ac_n)
        ld      c,a
        call    ui_lr
        ret     z
        call    ui_click
        call    ui_dirty                ; το ac_sel δεν είναι στην υπογραφή
        jp      ui_panel

; ac_do — η ενέργεια. Ξεκινά από το LOOK, σαν να πατήθηκε το πλήκτρο της: ο
; κέρσορας είναι ίδιος στις δύο καταστάσεις, οπότε τίποτα δεν ξαναζωγραφίζεται.
ac_do:
        ld      a,(ac_sel)
        ld      hl,ac_list
        call    ob_addu
        ld      a,(hl)
        add     a,a
        ld      hl,ac_jp
        call    ob_addu
        ld      a,(hl)
        inc     hl
        ld      h,(hl)
        ld      l,a
        xor     a
        ld      (ui_state),a            ; UI_LOOK
        jp      (hl)

ac_jp:      dw ui_build, fit_enter, ac_info, ac_ship, ac_save, ac_load, ac_home

ac_info:
        ld      a,UI_INFO
        jp      ui_ask
ac_ship:
        ; Το μήνυμα του πλοίου γράφει μόνο τη σειρά 3 (ui_msg), και η 4 θα
        ; έμενε με τον κατάλογο ως το τέλος του μηνύματος — σε παύση, για πάντα.
        ld      a,4
        call    hud_go
        ld      b,40
        call    hud_blank
        jp      ui_ship
ac_save:
        xor     a                       ; 0 = σώσιμο
        jp      ui_askslot
ac_load:
        ld      a,1                     ; 1 = φόρτωμα
        jp      ui_askslot
ac_home:
        call    ui_hide
        jp      ui_home

; ---------------------------------------------------------------------------
; ac_panel — από το ui_panel, με το HUD στη σειρά 3, στήλη 0. Τελειώνει στο
; uip_spd, όπως το in_panel.
; ---------------------------------------------------------------------------
ac_panel:
        ld      a,'<'
        call    hud_char
        call    hud_space
        ld      a,(ac_sel)
        call    ac_name
        call    hud_text7
        ld      b,9                     ; το πιο μακρύ όνομα είναι έξι
        call    ac_to
        ld      a,'>'
        call    hud_char
        ld      b,2
        call    hud_blank
        ld      hl,t_a_keys
        call    hud_text7
        ld      b,35                    ; ως τον δείκτη ταχύτητας
        call    ac_to
        ; --- σειρά 4: όλος ο κατάλογος, το διαλεγμένο σε αγκύλες. Πριν από
        ; κάθε όνομα ένα διαχωριστικό, και ένα ακόμη στο τέλος: «[» πριν από
        ; το διαλεγμένο, «]» μετά, αλλιώς κενό ---
        ld      a,4
        call    hud_go
        ld      c,0
ac4_lp:
        push    bc
        ld      a,(ac_sel)
        sub     c                       ; 0: πριν από αυτό, -1: μετά από αυτό
        ld      b,'['
        jr      z,ac4_sep
        inc     a
        ld      b,']'
        jr      z,ac4_sep
        ld      b,' '
ac4_sep:
        ld      a,b
        call    hud_char
        pop     bc
        ld      a,(ac_n)
        cp      c
        jr      z,ac4_end
        push    bc
        ld      a,c
        call    ac_name
        call    hud_text7
        pop     bc
        inc     c
        jr      ac4_lp
ac4_end:
        ld      b,40
        call    ac_to
        jp      uip_spd

; ac_to — κενά ως τη στήλη B. Στις σειρές 3-4 το hud_sp είναι η στήλη: το
; hud_go το ξεκινά από το 0 και κάθε κελί το ανεβάζει κατά ένα.
ac_to:
        ld      a,(hud_sp)
        cpl
        inc     a                       ; -στήλη
        add     a,b
        ld      b,a
        jp      hud_blank

; ac_name — A = θέση στο ac_list -> HL = το όνομα.
ac_name:
        ld      hl,ac_list
        call    ob_addu
        ld      a,(hl)
        ld      c,a
        add     a,a
        add     a,a
        add     a,a
        sub     c                       ; x7
        ld      hl,t_a_names
        jp      ob_addu

ac_list:    defs AI_N
ac_n:       db 0
ac_sel:     db 0
        assert  (ac_list >> 8) == ((ac_list + AI_N) >> 8)      ; aco_list: L - ac_list
