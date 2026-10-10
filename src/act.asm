; act.asm — ό,τι κάνουν τα κουμπιά, και το μενού τους χωρίς γράμματα
; (DESIGN §9.1, §9.3· βήμα 80, κουμπιά από το βήμα 84).
;
; ΤΟ SPACE ΣΤΟ LOOK ΕΣΤΙΑΖΕΙ ΣΤΗ ΜΠΑΡΑ. Αριστερά/δεξιά περνά από τις έξι ομάδες
; και το ? (το διαλεγμένο λευκό), FIRE ή SPACE το πατά, ESC γυρίζει στο LOOK.
; Ανοίγει στην ομάδα του αντικειμένου που χτίστηκε τελευταίο, οπότε το SPACE
; SPACE ξαναβρίσκει τον κατάλογο εκεί που έμεινε, όπως ως το βήμα 83.
; Το M ανοίγει με τον ίδιο τρόπο τη ΔΙΑΧΕΙΡΙΣΗ: πληροφορίες, εξοπλισμός, σώσιμο,
; φόρτωμα, κέντρο. Ο,τι δεν γίνεται εδώ (ο εξοπλισμός έξω από θόλο) δείχνεται
; κόκκινο αντί να κρύβεται, όπως έκανε ως το βήμα 83 ο κατάλογος κειμένου.
;
;   σειρά 3   < DOMES        >  FIRE=GO ESC=BACK
;   σειρά 4   LIVE AND WORK INSIDE
;
; Τα γράμματα των κουμπιών, που διαβάζει το bk_scan (src/bar.asm), έρχονται
; ΚΑΙ ΑΥΤΑ στο bt_key: ένα κουμπί κάνει το ίδιο είτε το πατήσεις είτε το
; διαλέξεις εδώ.
;
; Στην τράπεζα 2, όπως ό,τι τρέχει μόνο όταν το ζητήσει ο παίκτης.

UI_ACT      equ 7

        assert  A_FIRE < 8 && A_CANCEL < 8 && A_MENU < 8
        ; Εδώ και όχι στο bar.asm: ο rasm ελέγχει το assert εκεί που το βρίσκει,
        ; και το BLD_N ορίζεται στο build.asm, στην τράπεζα 2.
        assert  bld_end - bld_btn == BLD_N && bld_btn - bld_grp == BLD_N

; ---------------------------------------------------------------------------
; ac_open — από το LOOK, με το SPACE: οι ομάδες.
; ac_manage — το M: η ΔΙΑΧΕΙΡΙΣΗ.
; ---------------------------------------------------------------------------
ac_open:
        ld      a,(ui_sel)
        ld      hl,bld_grp
        call    ob_addu
        ld      a,(hl)                  ; η ομάδα του τελευταίου
        ld      hl,ac_l_grp
        ld      bc,0 * 256 + 7          ; B = ομάδες, C = πόσα
        jr      aco_set
ac_manage:
        call    fit_can                 ; CY = ο εξοπλισμός ανοίγει εδώ
        sbc     a,a
        ld      (ac_fit),a
        ld      hl,ac_l_man
        ld      bc,1 * 256 + 6
        xor     a
aco_set:
        ld      (ac_lst),hl
        ld      l,c
        ld      h,a
        ld      (ac_n),hl               ; ac_n = C, ac_sel = A
        ld      a,b
aco_mode:                               ; A = ac_mode (cw_open, tr_open)
        ld      (ac_mode),a
        call    ui_click
        ld      a,UI_ACT
        jp      ui_ask

; ---------------------------------------------------------------------------
; ac_tick — ένα καρέ εισόδου στο μενού.
; ---------------------------------------------------------------------------
ac_tick:
        ld      a,(act_hit)
        bit     A_CANCEL,a
        jr      nz,ac_look
act_fire:
        ld      c,a
        ld      a,(ac_mode)
        cp      CW_MODE
        ld      a,c
        jp      z,cw_tick               ; οι γραμμές: του πλοίου
        jp      nc,tr_tick              ; και του εμπόρου (src/lines.asm, βήμα 93)
        and     1 << A_FIRE | 1 << A_MENU
        jr      nz,ac_do
        ld      hl,ac_sel
        ld      a,(ac_n)
        ld      c,a
        jp      cw_lr                   ; το ac_sel δεν είναι στην υπογραφή
ac_do:
        call    ac_cur
        ; fall through

; ---------------------------------------------------------------------------
; bt_key — A = κουμπί: ό,τι κάνει. Από το ac_do και από το bk_scan.
; ---------------------------------------------------------------------------
bt_key:
        add     a,a
        add     a,a
        ld      hl,bt_tab + 3
        call    ob_addu
        ld      a,(hl)                  ; είδος << 5 | παράμετρος
        ld      b,a
        rlca
        rlca
        rlca
        and     7
        add     a,a
        ld      hl,btk_jp
        call    ob_addu
        ld      e,(hl)
        inc     hl
        ld      d,(hl)
        ex      de,hl
        ld      a,b
        and     #1F                     ; η παράμετρος
        jp      (hl)

btk_jp:     dw btk_group, btk_size, btk_room, btk_item, btk_act
        assert  KB_GROUP == 0 && KB_SIZE == 1 && KB_ROOM == 2 && KB_ITEM == 3 && KB_ACT == 4

; --- ομάδα: ανοίγει στο MENU με το αντικείμενό της· ανοιχτή (MENU, PLACE,
; LINK), κλείνει ---
btk_group:
        cp      G_MANAGE
        jr      z,btk_man
        ld      c,a
        ld      a,(ui_sel)
        ld      hl,bld_grp
        call    ob_addu
        ld      a,(hl)
        cp      c
        jr      nz,btg_new
        ld      a,(ui_state)
        dec     a                       ; MENU 0, PLACE 1, LINK 2
        cp      3
        jr      nc,btg_bld              ; κλειστή: ανοίγει, ίδιο αντικείμενο
ac_look:
        xor     a                       ; UI_LOOK
        jp      ui_goto
btg_new:
        ld      a,c
        ld      hl,grp_bld
        call    ob_addu
        ld      a,(hl)
        ld      (ui_sel),a
btg_bld:
        jp      ui_build                ; ui_hide, MENU, το φάντασμα του ui_sel
btk_man:
        ld      a,(ui_state)
        cp      UI_ACT
        jr      nz,btm_open
        ld      a,(ac_mode)
        or      a
        jr      nz,ac_look              ; ανοιχτή: κλείνει
btm_open:
        jp      ac_manage

; --- μέγεθος θόλου: η κατάσταση μένει (MENU ή PLACE) ---
btk_size:
        ld      (ui_sel),a
        call    ui_hide
        jp      uim_pick

; --- δωμάτιο: αν χωρά στο μέγεθος, και κατευθείαν στο PLACE ---
btk_room:
        ld      c,a
        call    rm_fits                 ; κρατά BC
        jp      nz,uip_deny
        ld      a,c
        ld      (bd_rsel),a
        call    ui_hide
        jr      btk_place

; --- αντικείμενο του καταλόγου: κατευθείαν στο PLACE ---
btk_item:
        ld      (ui_sel),a
        call    ui_hide
        ld      a,(ui_sel)
        call    bd_select
btk_place:
        call    ui_click
        ld      a,UI_PLACE
        jp      ui_goto_h               ; ld (ui_state),a, ui_show

; --- ενέργεια: από το LOOK, σαν να πατήθηκε το πλήκτρο της ---
btk_act:
        cp      AB_HELP
        jp      z,hp_show               ; src/help.asm: η κατάσταση μένει
        add     a,a
        ld      hl,btk_ajp
        call    ob_addu
        ld      e,(hl)
        inc     hl
        ld      d,(hl)
        ex      de,hl
        xor     a
        ld      (ui_state),a            ; UI_LOOK
        jp      (hl)

btk_ajp:    dw ac_info, fit_enter, ac_save, ac_load, ac_home, cw_open, tr_open
        assert  AB_INFO == 0 && AB_FIT == 1 && AB_SAVE == 2 && AB_LOAD == 3
        assert  AB_HOME == 4 && AB_SHIP == 5 && AB_TRADE == 6   ; το tr_open: src/lines.asm

ac_info:
        ld      a,UI_INFO
        jp      ui_ask
; --- Η ΓΡΑΜΜΗ ΤΟΥ ΠΛΟΙΟΥ (βήμα 91): η κατάσταση εδώ, οι ειδικότητες και
; η εικόνα της στο src/crew.asm ---------------------------------------------
; cw_open — το κουμπί του πλοίου και το C: η γραμμή, στο UI_ACT.
cw_open:
        ld      a,CW_MODE
        jp      aco_mode

; cw_tick — από το ac_tick, όταν δεν πατήθηκε ESC. A = C = act_hit.
cw_tick:
        and     1 << A_FIRE | 1 << A_MENU   ; και το SPACE, όπως στο μενού
        jr      nz,cw_call
        ld      a,c
        and     1 << A_UP | 1 << A_DOWN
        jp      nz,cw_ud                ; src/crew.asm, τράπεζα 0
        ld      hl,cw_sel
        ld      c,CW_N
; cw_lr — HL -> τιμή, C = πόσες: το ui_lr, και αν άλλαξε το cw_draw. Και για
; το ac_sel και το tr_sel.
cw_lr:
        call    ui_lr
        ret     z
cw_draw:
        call    ui_click
        call    ui_dirty                ; ούτε το cw_sel ούτε το EC_LAND είναι
        jp      ui_panel                ; στην υπογραφή
cw_call:
        xor     a                       ; UI_LOOK, όπως το btk_act
        ld      (ui_state),a
        ; fall through
; ac_ship — το FIRE της γραμμής του πλοίου (src/crew.asm, βήμα 91· ως τότε
; το ίδιο το κουμπί). Το μήνυμα του πλοίου γράφει μόνο τη σειρά 3 (ui_msg), και
; η 4 θα έμενε με την περιγραφή ως το τέλος του μηνύματος — σε παύση, για πάντα.
ac_ship:
        call    ac_clr4
        jp      ui_ship
; ac_clr4 — η σειρά 4 σβήνει, για ένα μήνυμα στη σειρά 3· και η συμφωνία με
; τον έμπορο (tr_deal, src/lines.asm).
ac_clr4:
        ld      a,4
        call    hud_go
        ld      b,40
        jp      hud_blank
ac_save:
        xor     a                       ; 0 = σώσιμο
        jr      ac_slot
ac_load:
        ld      a,1                     ; 1 = φόρτωμα
ac_slot:
        jp      ui_askslot
ac_home:
        call    ui_hide
        jp      ui_home

; ac_cur — A = το διαλεγμένο κουμπί.
ac_cur:
        ld      hl,(ac_lst)
        ld      a,(ac_sel)
        call    ob_addu
        ld      a,(hl)
        ret

; ---------------------------------------------------------------------------
; ac_panel — από το ui_panel, με το HUD στη σειρά 3, στήλη 0. Τελειώνει στο
; uip_spd, όπως το in_panel. Το όνομα και η γραμμή είναι της οθόνης βοήθειας.
; ---------------------------------------------------------------------------
ac_panel:
        ld      bc,GA_PORT + PAGE_B7
        call    hud_page                ; τα κείμενα στην 7, και για τις γραμμές
        ld      a,(ac_mode)
        cp      CW_MODE
        jp      z,cw_panel              ; οι γραμμές (src/lines.asm, βήμα 93)
        jp      nc,tr_panel
        ld      a,'<'
        call    hud_char
        call    hud_space
        call    ac_cur
        call    bt_text
        call    hud_text
        inc     hl
        push    hl                      ; η γραμμή του
        ld      b,15                    ; ως 12 γράμματα το όνομα
        call    hud_to
        ld      a,'>'
        call    hud_char
        ld      b,2
        call    hud_blank
        ld      hl,t_a_keys
        call    hud_text
        call    ln_row4                 ; ως τον δείκτη ταχύτητας, και η σειρά 4
        pop     hl
        call    hud_text
acp_end:                                ; οι γραμμές (src/lines.asm)
        ld      b,40
        call    hud_to
        call    hud_page1
        jp      uip_spd


ac_lst:     dw ac_l_grp
ac_n:       db 7
ac_sel:     db 0
ac_mode:    db 0                        ; 0 οι ομάδες, 1 η ΔΙΑΧΕΙΡΙΣΗ
ac_fit:     db 0                        ; #FF: ο εξοπλισμός ανοίγει εκεί που ήταν το M
        assert  ac_sel == ac_n + 1      ; aco_set
