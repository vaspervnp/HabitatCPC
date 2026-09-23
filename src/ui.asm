; ui.asm — ο κέρσορας, το μενού και το φάντασμα (DESIGN §9.1, §9.3).
;
; Τρεις καταστάσεις και τίποτε άλλο:
;
;   LOOK   ο κέρσορας περιφέρεται· η κάμερα τον ακολουθεί στο χείλος
;   MENU   ο κατάλογος του §9.3, μια γραμμή· αριστερά/δεξιά αλλάζει είδος
;   PLACE  το φάντασμα ακολουθεί τον κέρσορα, με τα άκυρα tiles σημαδεμένα
;   LINK   δύο θόλοι, και η διαδρομή του διαδρόμου ανάμεσά τους σαν φάντασμα
;
; Η ΣΕΙΡΑ ΜΕΣΑ ΣΕ ΕΝΑ ΒΗΜΑ ΕΙΝΑΙ ΔΕΣΜΕΥΤΙΚΗ: πρώτα σβήνει το φάντασμα, μετά
; κινείται ο κέρσορας, μετά (αν χρειάζεται) σκρολάρει η κάμερα, και τελευταίο
; ξαναζωγραφίζεται το φάντασμα. Αν το σβήσιμο γίνει μετά το σκρολάρισμα, οι
; διευθύνσεις του αρχείου αναίρεσης δείχνουν σε άλλα pixel — το δαχτυλίδι έχει
; γυρίσει από κάτω τους.

UI_LOOK     equ 0
UI_MENU     equ 1
UI_PLACE    equ 2
UI_LINK     equ 3                       ; διάλεξε θόλο, διάλεξε θόλο (§9.4)
UI_SLOT     equ 4                       ; ποια από τις τρεις θέσεις δίσκου (§11)
MSG_TICKS   equ 6                       ; τικ HUD που κρατά ένα μήνυμα (§11)

UIP_NSIG    equ 10                      ; bytes υπογραφής των σειρών 3-4
UI_MARGIN   equ 1                       ; tiles από το χείλος πριν σκρολάρει
PEN_CUR     equ 15                      ; ροζ — το λευκό χανόταν πάνω στα χείλη
                                    ; των διαδρόμων, που είναι κι αυτά λευκά
PEN_OK      equ 9                       ; έντονο πράσινο — επιτρέπεται
PEN_NO      equ 8                       ; έντονο κόκκινο — δεν επιτρέπεται

; ---------------------------------------------------------------------------
; ui_init — κέρσορας στο κέντρο του κόσμου, κατάσταση LOOK.
; ---------------------------------------------------------------------------
ui_init:
        xor     a
        ld      (cur_hx),a
        ld      (cur_hy),a
        ld      (ui_state),a
        ld      (ui_sel),a
        call    gh_reset
        call    ui_center
        call    view_draw
        call    ui_hudall
        call    ui_show
        ret

; ui_center — η κάμερα με τον κέρσορα στη μέση του κάδρου.
ui_center:
        ld      a,(cur_hx)
        sra     a
        sub     VIEW_TW/2
        ld      (cam_tx),a
        ld      a,(cur_hy)
        sra     a
        sub     VIEW_TH/2
        ld      (cam_ty),a
        ret

; ---------------------------------------------------------------------------
; ui_tick — ένα καρέ εισόδου.
; ---------------------------------------------------------------------------
ui_tick:
        call    in_read
        call    ui_speed
        ld      a,A_HOME
        call    in_hit
        jr      z,uit_state
        call    ui_hide
        xor     a
        ld      (cur_hx),a
        ld      (cur_hy),a
        call    ui_center
        call    view_draw
        call    ui_hudall
        jp      ui_show
uit_state:
        ld      a,(ui_state)
        cp      UI_MENU
        jp      z,uist_menu
        cp      UI_PLACE
        jp      z,uist_place
        cp      UI_LINK
        jp      z,uist_link
        ifdef HAS_DISC
        cp      UI_SLOT
        jp      z,uist_slot
        endif
        ; fall through — UI_LOOK

; --- LOOK ------------------------------------------------------------------
uist_look:
        call    ui_move                 ; -> NZ αν κουνήθηκε
        ; Ο δίσκος υπάρχει μόνο στο πλήρες παιχνίδι: τα tests/uitest.asm και
        ; tests/objtest.asm δένουν τον renderer χωρίς τροχό και χωρίς οδηγό
        ; δισκέτας, και δεν έχουν πού να σώσουν.
        ifdef HAS_DISC
        ld      a,A_SAVE
        call    in_hit
        jr      z,usv_load
        xor     a                       ; 0 = σώσιμο
        jp      ui_askslot
usv_load:
        ld      a,A_LOAD
        call    in_hit
        jr      z,usv_none
        ld      a,1                     ; 1 = φόρτωμα
        jp      ui_askslot
usv_none:
        endif
        ld      a,A_MENU
        call    in_hit
        ret     z
        call    ui_hide
        ld      a,UI_MENU
        ld      (ui_state),a
        ld      a,(ui_sel)
        call    bd_select
        ld      a,SFX_MENU
        call    snd_play
        jp      ui_show

; ---------------------------------------------------------------------------
; ui_speed — τα πλήκτρα 1-4 (§9.1). Δουλεύουν σε ΚΑΘΕ κατάσταση: η παύση είναι
; χρήσιμη ακριβώς όταν χτίζεις, και το x4 όταν περιμένεις.
;
; ΔΕΝ ΜΠΑΙΝΕΙ ΑΝΑΜΕΣΑ ΣΤΟ uit_state ΚΑΙ ΣΤΟ uist_look. Εκεί το έβαλα την πρώτη
; φορά, και η κατάσταση LOOK φτάνει με ΠΤΩΣΗ μετά τον διαλογέα: το παιχνίδι
; σταμάτησε να απαντά στο SPACE και το ui_spd γέμισε σκουπίδια — που σημαίνει
; 255 θέσεις τροχού ανά frame, δηλαδή μηχάνημα που φαίνεται κολλημένο.
;
; Ο δείκτης ζωγραφίζεται ΜΕΤΑ τον βρόχο και μόνο αν άλλαξε κάτι: το ui_panel
; χαλάει HL και BC, και μέσα στον βρόχο θα διάβαζε ο επόμενος γύρος τον πίνακα
; από λάθος θέση.
; ---------------------------------------------------------------------------
ui_speed:
        ld      a,(ui_spd)
        ld      (uis_was),a
        ld      hl,ui_spd_tab
        ld      c,A_SPD1
        ld      b,4
uis_lp:
        push    bc
        push    hl
        ld      a,c
        call    in_hit
        pop     hl
        pop     bc
        jr      z,uis_next
        ld      a,(hl)
        ld      (ui_spd),a
uis_next:
        inc     hl
        inc     c
        djnz    uis_lp
        ld      a,(ui_spd)
        ld      hl,uis_was
        cp      (hl)
        ret     z
        call    ui_dirty                ; στην παύση ο τροχός δεν ξαναφτάνει
        jp      ui_panel                ; στη θέση 0: δείξ' το τώρα ή ποτέ

ui_spd_tab: db 0, 1, 2, 4
ui_spd:     db 1                    ; 0 παύση · 1 κανονικά · 2 γρήγορα · 4 πολύ
uis_was:    db 1

        ifdef HAS_DISC
; --- δίσκος ----------------------------------------------------------------
; Μόνο από το LOOK, και με τον κέρσορα σβηστό: το σώσιμο κρατά περίπου δύο
; δευτερόλεπτα με τις διακοπές ανοιχτές και τίποτα δεν σχεδιάζεται στο μεταξύ.
; Το μήνυμα μένει ως το επόμενο ui_panel, δηλαδή ως μία περιστροφή τροχού.
ui_dosave:
        call    sl_digit
        call    ui_hide
        ld      hl,t_saving
        call    ui_msg
        ld      a,(sl_pick)
        call    sv_save
        ld      hl,t_saved
        jr      z,uds_end
        ld      hl,t_dskerr
uds_end:
        call    ui_msg
        call    ui_dirty
        jp      ui_show

ui_doload:
        call    sl_digit
        call    ui_hide
        ld      hl,t_loading
        call    ui_msg
        ld      a,(sl_pick)
        call    sv_load                 ; πετυχαίνοντας, ξανασχεδιάζει τα πάντα
        push    af
        ld      hl,t_loaded
        jr      z,udl_end
        ; Αδεια θέση ΔΕΝ είναι βλάβη δίσκου, και το μήνυμα το έλεγε λάθος: το
        ; sv_hdr_ok γυρίζει #FF όταν η υπογραφή δεν ταιριάζει, ο ελεγκτής
        ; οτιδήποτε άλλο.
        cp      #FF
        ld      hl,t_empty
        jr      z,udl_end
        ld      hl,t_dskerr
udl_end:
        call    ui_msg
        call    ui_dirty
        pop     af
        jp      nz,ui_show              ; αποτυχία: ο κέρσορας ήταν κρυμμένος
        ret                             ; επιτυχία: το sv_after τον έδειξε ήδη


; --- SLOT: ποιο από τα τρία -------------------------------------------------
; Ο δίσκος είχε ΠΑΝΤΑ τρεις θέσεις (§11) και το παιχνίδι έγραφε πάντα στην
; πρώτη: το sv_save έπαιρνε slot σε A και το UI έδινε `xor a`. Δύο από τις
; τρεις — 46 KB δίσκου — δεν είχαν γραφτεί ποτέ, ούτε σε δοκιμή.
;
; Η κατάσταση είναι κοινή για σώσιμο και φόρτωμα· το sl_mode ξεχωρίζει.
uist_slot:
        ld      a,A_CANCEL
        call    in_hit
        jr      z,usl_fire
        ld      a,UI_LOOK
        ld      (ui_state),a
        ret
usl_fire:
        ld      a,A_FIRE
        call    in_hit
        jr      z,usl_lr
        ld      a,UI_LOOK
        ld      (ui_state),a
        ld      a,(sl_mode)
        or      a
        ld      a,(sl_pick)
        jp      z,ui_dosave
        jp      ui_doload
usl_lr:
        ld      a,A_RIGHT
        call    in_hit
        jr      z,usl_left
        ld      a,(sl_pick)
        inc     a
        cp      SV_SLOTS
        jr      c,usl_set
        xor     a
        jr      usl_set
usl_left:
        ld      a,A_LEFT
        call    in_hit
        ret     z
        ld      a,(sl_pick)
        or      a
        jr      nz,usl_dec
        ld      a,SV_SLOTS
usl_dec:
        dec     a
usl_set:
        ld      (sl_pick),a
        ld      a,SFX_MENU
        jp      snd_play

; ui_askslot — μπαίνει στην επιλογή. A = 0 σώσιμο, 1 φόρτωμα.
; (ΟΧΙ «ui_slot»: ο rasm δεν ξεχωρίζει ετικέτα από alias, και το UI_SLOT
; είναι ήδη σταθερά.)
ui_askslot:
        ld      (sl_mode),a
        ld      a,UI_SLOT
        ld      (ui_state),a
        ld      a,SFX_MENU
        jp      snd_play

; sl_digit — το νούμερο της θέσης μέσα στα τρία μηνύματα, γραμμένο πριν φανούν.
; Οι τρεις μετατοπίσεις είναι μετρημένες στα κείμενα από κάτω: αν αλλάξει λέξη,
; αλλάζει και ο αριθμός εδώ — γι' αυτό το test_save διαβάζει το ψηφίο από την
; ΟΘΟΝΗ και όχι από τη μνήμη.
sl_digit:
        ld      bc,GA_PORT + PAGE_B7    ; τα κείμενα ζουν στην τράπεζα 7
        out     (c),c
        ld      a,(sl_pick)
        add     a,'1'
        ld      (t_saved + 14),a
        ld      (t_loaded + 17),a
        ld      (t_empty + 16),a
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        ret

sl_mode:    db 0
sl_pick:    db 0

; ui_msg — μία γραμμή στη σειρά 3 του HUD, και το υπόλοιπο σβηστό.
ui_msg:
        ; Η τράπεζα 7 ανοίγει ΜΙΑ φορά και για τα δύο: και το τύπωμα και το
        ; μέτρημα του μήκους διαβάζουν από εκεί (§4.2).
        ld      bc,GA_PORT + PAGE_B7
        out     (c),c
        push    hl
        ld      a,3
        call    hud_go
        pop     hl
        push    hl
        call    hud_text
        pop     hl
        ld      b,40
um_len:
        ld      a,(hl)
        or      a
        jr      z,um_blank
        inc     hl
        dec     b
        jr      um_len
um_blank:
        push    bc
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        pop     bc
        ld      a,MSG_TICKS
        ld      (ui_hold),a
        jp      hud_blank

        endif

; --- MENU ------------------------------------------------------------------
uist_menu:
        ld      a,A_CANCEL
        call    in_hit
        jr      z,uim_fire
        call    ui_hide
        xor     a
        ld      (ui_state),a
        jp      ui_show
uim_fire:
        ld      a,A_FIRE
        call    in_hit
        jr      z,uim_lr
        call    ui_hide
        ld      a,(bd_kind)
        cp      BK_LINK
        ld      a,UI_PLACE
        jr      nz,uim_go
        ld      a,255
        ld      (ln_a),a                ; ακόμη δεν έχει διαλεγεί αφετηρία
        ld      a,UI_LINK
uim_go:
        ld      (ui_state),a
        ld      a,SFX_MENU              ; «διάλεξες»: το FIRE στον κατάλογο δεν
        call    snd_play                ; αλλάζει τίποτα ορατό εκτός φαντάσματος
        jp      ui_show
uim_lr:
        ld      a,A_RIGHT
        call    in_hit
        jr      z,uim_left
        ld      a,(ui_sel)
        inc     a
        cp      BLD_N
        jr      c,uim_set
        xor     a
        jr      uim_set
uim_left:
        ld      a,A_LEFT
        call    in_hit
        ret     z
        ld      a,(ui_sel)
        or      a
        jr      nz,uim_dec
        ld      a,BLD_N
uim_dec:
        dec     a
uim_set:
        ld      (ui_sel),a
        call    ui_hide
        ld      a,(ui_sel)
        call    bd_select
        ld      a,SFX_MENU
        call    snd_play
        jp      ui_show

; --- PLACE -----------------------------------------------------------------
uist_place:
        ld      a,A_CANCEL
        call    in_hit
        jr      z,uip_fire
        call    ui_hide
        ld      a,UI_MENU
        ld      (ui_state),a
        jp      ui_show
uip_fire:
        ld      a,A_FIRE
        call    in_hit
        jr      z,uip_move
        call    ui_validate
        or      a
        jr      nz,uip_deny             ; άκυρη θέση — το FIRE δεν κάνει τίποτα
        call    bd_afford
        jr      nz,uip_deny             ; ούτε τα υλικά φτάνουν
        call    ui_hide
        call    bd_commit
        cp      255
        jr      z,uip_nospace
        ld      a,SFX_BUILD
        call    snd_play
        call    view_draw               ; το νέο αντικείμενο μπαίνει στη σκηνή
        jr      uip_after
uip_nospace:
        ld      a,SFX_DENY
        call    snd_play
uip_after:
        call    ui_hudall
        jp      ui_show
uip_deny:
        ld      a,SFX_DENY
        jp      snd_play
uip_move:
        jp      ui_move

; --- LINK ------------------------------------------------------------------
; Δύο πατήματα: το πρώτο διαλέγει την αφετηρία, το δεύτερο τον προορισμό. Η
; ακύρωση ξηλώνει ένα βήμα τη φορά — αφήνει πρώτα την αφετηρία και μετά βγαίνει
; από την κατάσταση, γιατί το να χάνεις και τα δύο με ένα πάτημα είναι η
; συνηθέστερη αιτία να ξαναδιαλέγεις τα ίδια.
uist_link:
        ld      a,A_CANCEL
        call    in_hit
        jr      z,uil_fire
        call    ui_hide
        ld      a,(ln_a)
        inc     a
        jr      z,uil_out
        ld      a,255
        ld      (ln_a),a
        jp      ui_show
uil_out:
        ld      a,UI_MENU
        ld      (ui_state),a
        jp      ui_show
uil_fire:
        ld      a,A_FIRE
        call    in_hit
        jp      z,ui_move
        call    ui_dome
        cp      255
        ret     z                       ; ο κέρσορας δεν είναι πάνω σε θόλο
        ld      (ln_pick),a             ; ΣΤΗ ΜΝΗΜΗ: το ui_hide ζωγραφίζει
        ld      a,(ln_a)
        inc     a
        jr      nz,uil_second
        call    ui_hide
        ld      a,(ln_pick)
        ld      (ln_a),a
        jp      ui_show
uil_second:
        call    ln_plan
        or      a
        jr      nz,uil_deny             ; άκυρη διαδρομή — το FIRE δεν κάνει τίποτα
        ld      a,(cr_n)
        or      a
        jr      z,uil_deny
        call    cr_afford
        jr      nz,uil_deny
        call    ui_hide
        call    cr_commit
        or      a
        jr      nz,uil_full
        ld      a,255
        ld      (ln_a),a                ; μια διαδρομή τη φορά
        ld      a,SFX_BUILD
        call    snd_play
        call    view_draw
        jr      uil_after
uil_full:
        ld      a,SFX_DENY
        call    snd_play
uil_after:
        call    ui_hudall
        jp      ui_show
uil_deny:
        ld      a,SFX_DENY
        jp      snd_play

; ---------------------------------------------------------------------------
; ui_dome — ποιος θόλος είναι κάτω από τον κέρσορα; A = id ή 255.
; ---------------------------------------------------------------------------
ui_dome:
        ld      a,(cur_hx)
        sra     a
        ld      (uid_tx),a
        ld      a,(cur_hy)
        sra     a
        ld      (uid_ty),a
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        ld      c,0
uid_lp:
        ld      a,c
        call    ob_dome_live
        jr      z,uid_next              ; άδεια θέση
        push    bc
        call    ob_domeadr
        ld      a,(hl)                  ; cx σε μισά tiles — ΣΤΗ ΜΝΗΜΗ: το
        ld      (uid_cx),a              ; cr_look παρακάτω χαλάει το DE
        inc     hl
        ld      a,(hl)                  ; cy
        ld      (uid_cy),a
        inc     hl
        ld      a,(hl)                  ; μέγεθος
        ld      hl,uid_wt
        call    cr_look
        ld      b,a                     ; W σε tiles
        ld      a,(uid_cx)
        call    uid_left                ; A = αριστερό tile
        ld      e,a
        ld      a,(uid_tx)
        sub     e
        cp      b
        jr      nc,uid_no
        ld      a,(uid_cy)
        call    uid_left
        ld      e,a
        ld      a,(uid_ty)
        sub     e
        cp      b
        jr      nc,uid_no
        pop     bc
        ld      a,c
        jr      uid_out
uid_no:
        pop     bc
uid_next:
        inc     c
        ld      a,c
        cp      MAX_DOME
        jr      c,uid_lp
        ld      a,255
uid_out:
        push    af
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        pop     af
        ret

; uid_left — A = κέντρο σε μισά tiles, B = W σε tiles -> A = αριστερό tile.
;       left = (κέντρο - W) / 2, ακριβές: κέντρο και W έχουν την ίδια ισοτιμία
uid_left:
        sub     b
        sra     a
        ret

uid_wt:     db 4,6,8

; ---------------------------------------------------------------------------
; ln_plan — η διαδρομή από τον (ln_a) στον θόλο κάτω από τον κέρσορα.
; Out: A = (ui_bad): 0 σημαίνει «χτίζεται». (cr_n) = 0 αν δεν υπάρχει καν.
; ---------------------------------------------------------------------------
ln_plan:
        xor     a
        ld      (cr_n),a
        ld      (ui_bad),a
        ld      a,(ln_a)
        inc     a
        ret     z                       ; δεν έχει διαλεγεί αφετηρία ακόμη
        call    ui_dome
        cp      255
        jr      z,lnp_no
        ld      hl,ln_a
        cp      (hl)
        jr      z,lnp_no                ; ο ίδιος θόλος με τον εαυτό του
        ld      (cr_b),a
        ld      a,(ln_a)
        ld      (cr_a),a
        call    cr_plan
        or      a
        jr      z,lnp_no
        call    cr_check
        ld      (ui_bad),a
        ret
lnp_no:
        xor     a
        ld      (cr_n),a
        ld      a,1
        ld      (ui_bad),a
        ret

; cr_cb_gh — ένα tile της διαδρομής σαν σημάδι φαντάσματος.
cr_cb_gh:
        push    bc
        ld      a,b
        call    ui_sxt
        ld      (gh_x),hl
        pop     bc
        push    bc
        ld      a,c
        call    ui_syt
        ld      (gh_y),hl
        call    gh_mark
        pop     bc
        ret

; ---------------------------------------------------------------------------
; ui_move — κίνηση κέρσορα ένα tile, με την κάμερα να ακολουθεί.
; Out: NZ αν κουνήθηκε.
; ---------------------------------------------------------------------------
; Η ΚΙΝΗΣΗ ΔΙΑΒΑΖΕΙ ΣΤΑΘΜΗ, ΟΧΙ ΑΚΜΗ — σε αντίθεση με τα κουμπιά.
;
; Ενας κύκλος ui_tick μπορεί να κρατήσει 3 ως 9 frames όταν σκρολάρει η κάμερα
; ([§8.2]). Με ακμή, ένα πάτημα συντομότερο από τον κύκλο ΧΑΝΕΤΑΙ εντελώς — και
; αυτό ακριβώς έδειξε η δοκιμή: δώδεκα πατήματα έδωσαν ένδεκα βήματα. Με στάθμη
; το κρατημένο πλήκτρο επαναλαμβάνει, όπως περιμένει κανείς από κέρσορα, και ο
; ρυθμός επανάληψης είναι ο ρυθμός του κύκλου.
ui_move:
        xor     a
        ld      (ui_dx),a
        ld      (ui_dy),a
        ld      a,A_LEFT
        call    in_held
        jr      z,um_r
        ld      a,-2
        ld      (ui_dx),a
um_r:
        ld      a,A_RIGHT
        call    in_held
        jr      z,um_u
        ld      a,2
        ld      (ui_dx),a
um_u:
        ld      a,A_UP
        call    in_held
        jr      z,um_d
        ld      a,-2
        ld      (ui_dy),a
um_d:
        ld      a,A_DOWN
        call    in_held
        jr      z,um_go
        ld      a,2
        ld      (ui_dy),a
um_go:
        ld      a,(ui_dx)
        ld      hl,ui_dy
        or      (hl)
        ret     z                       ; τίποτα δεν πατήθηκε
        call    ui_hide
        ld      a,(ui_dx)
        ld      hl,cur_hx
        add     a,(hl)
        ld      (hl),a
        ld      a,(ui_dy)
        ld      hl,cur_hy
        add     a,(hl)
        ld      (hl),a
        call    ui_follow
        call    ui_show
        ld      a,SFX_MOVE
        call    snd_play
        ld      a,1
        or      a
        ret

; ---------------------------------------------------------------------------
; ui_follow — η κάμερα κρατά το αποτύπωμα μέσα στο κάδρο, με ένα tile
; περιθώριο, και σκρολάρει ΜΕ ΛΩΡΙΔΑ — όχι με πλήρη σχεδίαση.
; ---------------------------------------------------------------------------
ui_follow:
        call    ui_rect
uif_x:
        ld      a,(ui_tx)
        ld      hl,cam_tx
        sub     (hl)
        bit     7,a                     ; ο κέρσορας αριστερά της κάμερας
        jr      nz,uif_west
        cp      UI_MARGIN
        jr      nc,uif_x2
uif_west:
        ld      a,3                     ; δύση
        call    view_scroll
        jr      uif_x
uif_x2:
        ld      a,(ui_tx)
        ld      hl,ui_w
        add     a,(hl)
        ld      hl,cam_tx
        sub     (hl)
        cp      VIEW_TW - UI_MARGIN + 1
        jr      c,uif_y
        ld      a,1                     ; ανατολή
        call    view_scroll
        jr      uif_x2
uif_y:
        ld      a,(ui_ty)
        ld      hl,cam_ty
        sub     (hl)
        bit     7,a
        jr      nz,uif_north
        cp      UI_MARGIN
        jr      nc,uif_y2
uif_north:
        ld      a,0                     ; βορράς
        call    view_scroll
        jr      uif_y
uif_y2:
        ld      a,(ui_ty)
        ld      hl,ui_h
        add     a,(hl)
        ld      hl,cam_ty
        sub     (hl)
        cp      VIEW_TH - UI_MARGIN + 1
        ret     c
        ld      a,2                     ; νότος
        call    view_scroll
        jr      uif_y2

; ---------------------------------------------------------------------------
; ui_rect — το ορθογώνιο που δείχνει ο κέρσορας, σε tiles.
; Στο LOOK είναι ένα tile· στο PLACE το αποτύπωμα του αντικειμένου.
; ---------------------------------------------------------------------------
ui_rect:
        ld      a,(ui_state)
        cp      UI_PLACE
        jr      z,uir_foot
        ld      a,(cur_hx)
        sra     a
        ld      (ui_tx),a
        ld      a,(cur_hy)
        sra     a
        ld      (ui_ty),a
        ld      a,1
        ld      (ui_w),a
        ld      (ui_h),a
        ret
uir_foot:
        call    bd_rect
        ld      a,(bd_tx)
        ld      (ui_tx),a
        ld      a,(bd_ty)
        ld      (ui_ty),a
        ld      a,(bd_w)
        ld      (ui_w),a
        ld      a,(bd_h)
        ld      (ui_h),a
        ret

; ---------------------------------------------------------------------------
; ui_validate — Out: A = 0 αν η θέση επιτρέπεται.
; ---------------------------------------------------------------------------
ui_validate:
        ld      a,(ui_state)
        cp      UI_PLACE
        ld      a,0
        ret     nz
        ld      bc,GA_PORT + PAGE_B4
        out     (c),c
        call    bd_check
        push    af
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        pop     af
        ret

; ---------------------------------------------------------------------------
; ui_show / ui_hide — το φάντασμα πάνω στη σκηνή, και πίσω.
; ---------------------------------------------------------------------------
ui_hide:
        jp      gh_undo

ui_show:
        call    ui_rect
        ld      a,(ui_state)
        cp      UI_LINK
        jp      z,uis_link
        cp      UI_PLACE
        jr      nz,uis_pen
        call    ui_validate
        ld      (ui_bad),a
uis_pen:
        ld      a,(ui_state)
        cp      UI_PLACE
        ld      a,PEN_CUR
        jr      nz,uis_set
        ld      a,(ui_bad)
        or      a
        ld      a,PEN_OK
        jr      z,uis_set
        ld      a,PEN_NO
uis_set:
        call    gh_setpen
        call    uis_box
        jr      uis_bad

; uis_box — το πλαίσιο του (ui_tx, ui_ty, ui_w, ui_h) σε συντεταγμένες οθόνης.
uis_box:
        ld      a,(ui_tx)
        call    ui_sxt
        ld      (gh_bx),hl
        ld      a,(ui_ty)
        call    ui_syt
        ld      (gh_by),hl
        ld      a,(ui_w)
        add     a,a
        add     a,a
        ld      (gh_bw),a
        ld      a,(ui_h)
        add     a,a
        add     a,a
        add     a,a
        add     a,a
        ld      (gh_bh),a
        jp      gh_box

uis_bad:
        ; --- τα άκυρα tiles ---
        ld      a,(ui_state)
        cp      UI_PLACE
        jp      nz,ui_panel
        ld      a,(ui_bad)
        or      a
        jp      z,ui_panel
        ld      a,PEN_NO
        call    gh_setpen
        xor     a
        ld      (uis_row),a
uis_rl:
        ld      a,(uis_row)
        ld      l,a
        ld      h,0
        ld      de,bd_bad
        add     hl,de
        ld      a,(hl)
        or      a
        jr      z,uis_rn
        ld      c,a
        xor     a
        ld      (uis_col),a
uis_cl:
        ld      a,c
        rrca
        ld      c,a
        jr      nc,uis_cn
        push    bc
        ld      a,(ui_tx)
        ld      hl,uis_col
        add     a,(hl)
        call    ui_sxt
        ld      (gh_x),hl
        ld      a,(ui_ty)
        ld      hl,uis_row
        add     a,(hl)
        call    ui_syt
        ld      (gh_y),hl
        call    gh_mark
        pop     bc
uis_cn:
        ld      a,(uis_col)
        inc     a
        ld      (uis_col),a
        ld      hl,ui_w
        cp      (hl)
        jr      nz,uis_cl
uis_rn:
        ld      a,(uis_row)
        inc     a
        ld      (uis_row),a
        ld      hl,ui_h
        cp      (hl)
        jr      nz,uis_rl
        jp      ui_panel

; --- το φάντασμα της διαδρομής ---------------------------------------------
uis_link:
        call    ln_plan
        ld      a,(ln_a)
        inc     a
        ld      a,PEN_CUR
        jr      z,uisl_pen
        ld      a,(ui_bad)
        or      a
        ld      a,PEN_OK
        jr      z,uisl_pen
        ld      a,PEN_NO
uisl_pen:
        call    gh_setpen
        call    uis_box
        ld      a,(cr_n)
        or      a
        jp      z,ui_panel
        ld      hl,cr_cb_gh
        ld      (cr_cb),hl
        call    cr_walk
        jp      ui_panel

; ui_sxt / ui_syt — tile -> οθόνη, προσημασμένα 16 bit.
ui_sxt:
        call    ob_sext
        add     hl,hl
        add     hl,hl
        push    hl
        ld      a,(cam_tx)
        call    ob_sext
        add     hl,hl
        add     hl,hl
        ex      de,hl
        pop     hl
        or      a
        sbc     hl,de
        ret
ui_syt:
        call    ob_sext
        add     hl,hl
        add     hl,hl
        add     hl,hl
        add     hl,hl
        push    hl
        ld      a,(cam_ty)
        call    ob_sext
        add     hl,hl
        add     hl,hl
        add     hl,hl
        add     hl,hl
        ex      de,hl
        pop     hl
        or      a
        sbc     hl,de
        ret

; ---------------------------------------------------------------------------
; ui_panel — οι σειρές 3-4 του HUD: τι κρατάς και τι σου λέει το έδαφος.
; ---------------------------------------------------------------------------
; ---------------------------------------------------------------------------
; ΟΙ ΔΥΟ ΣΕΙΡΕΣ ΞΑΝΑΓΡΑΦΟΝΤΑΙ ΜΟΝΟ ΟΤΑΝ ΑΛΛΑΖΟΥΝ. Μετρημένο: ένα βήμα κέρσορα
; κόστιζε 29.952 us και το ui_panel ήταν 14.976 από αυτά — ακριβώς ο μισός
; κέρσορας, για ογδόντα κελιά που συνήθως λένε ακριβώς ό,τι έλεγαν πριν.
; Η υπογραφή είναι ό,τι μπορεί να τις αλλάξει — ΚΑΙ ΤΟ ΔΑΧΤΥΛΙΔΙ: το hud_gen
; του hud_inval είναι το ένατο byte της, γιατί ένα βήμα κάμερας αλλάζει τα
; pixel των σειρών 3-4 χωρίς να αλλάξει τίποτα από όσα λένε.
ui_panel:
        ; ΤΟ ΜΗΝΥΜΑ ΚΡΑΤΙΕΤΑΙ. Χωρίς αυτό ζούσε ως το επόμενο ml_hud — δεκαέξι
        ; frames, ένα τρίτο του δευτερολέπτου. Για ένα σώσιμο δύο δευτερολέπτων
        ; δεν φαινόταν (το μήνυμα έμενε όσο κρατούσε ο δίσκος), αλλά ένα «δεν
        ; υπάρχει τίποτα εδώ» απορρίπτεται στην πρώτη πίστα και ο παίκτης έβλεπε
        ; μια αναλαμπή. Εξι τικ HUD = δύο δευτερόλεπτα.
        ld      hl,ui_hold
        ld      a,(hl)
        or      a
        jr      z,uip_start
        dec     (hl)
        ret
uip_start:
        call    ui_sig
        ld      hl,uip_sig
        ld      de,uip_now
        ld      b,UIP_NSIG
uipc_lp:
        ld      a,(de)
        cp      (hl)
        jr      nz,uipc_go
        inc     hl
        inc     de
        djnz    uipc_lp
        ret                             ; τίποτα δεν άλλαξε
uipc_go:
        ld      hl,uip_now
        ld      de,uip_sig
        ld      bc,UIP_NSIG
        ldir
        ld      a,3
        call    hud_go
        ld      a,(ui_state)
        or      a
        jr      nz,uip_notlook
        ld      hl,t_look
        call    hud_text7
        ld      b,40-19
        call    hud_blank
        jp      uip_row4
uip_notlook:
        ifdef HAS_DISC
        cp      UI_SLOT
        jr      nz,uip_item
        ld      hl,t_slsave             ; «SAVE TO SLOT  » / «LOAD FROM SLOT»
        ld      a,(sl_mode)
        or      a
        jr      z,uip_slt
        ld      hl,t_slload
uip_slt:
        call    hud_text7
        ld      b,1
        call    hud_blank
        ld      a,(sl_pick)
        add     a,'1'
        call    hud_char
        ld      b,40-16
        call    hud_blank
        jp      uip_row4
        endif
uip_item:
        ; Το κόστος που δείχνεται είναι ΟΛΗΣ της διαδρομής όταν υπάρχει
        ; διαδρομή: ο κατάλογος γράφει την τιμή ενός πλακιδίου διαδρόμου, και
        ; το μήκος δεν το διαλέγει ο παίκτης αλλά η γεωμετρία (§9.4).
        ld      a,(bd_metal)
        ld      l,a
        ld      h,0
        ld      (uip_fe),hl
        ld      a,(bd_biop)
        ld      l,a
        ld      h,0
        ld      (uip_bi),hl
        ld      a,(ui_state)
        cp      UI_LINK
        jr      nz,uipi_go
        ld      a,(cr_n)
        or      a
        jr      z,uipi_go
        call    cr_cost
        ld      hl,(cr_metal)
        ld      (uip_fe),hl
        ld      hl,(cr_biop)
        ld      (uip_bi),hl
uipi_go:
        ld      a,'<'
        call    hud_char
        ld      b,1
        call    hud_blank
        ld      hl,(bd_name)
        call    hud_text   ; τράπεζα 2, όχι 7
        ld      b,1
        call    hud_blank
        ld      a,'>'
        call    hud_char
        ld      b,2
        call    hud_blank
        ld      hl,t_fe
        call    hud_text7
        ld      hl,(uip_fe)
        ld      b,3
        call    hud_num
        ld      b,2
        call    hud_blank
        ld      hl,t_bi
        call    hud_text7
        ld      hl,(uip_bi)
        ld      b,3
        call    hud_num
        ld      b,40-31
        call    hud_blank
uip_row4:
        ld      a,4
        call    hud_go
        ld      a,(ui_state)
        cp      UI_LINK
        jr      z,uip_ln
        cp      UI_PLACE
        jr      z,uip_st
        ifdef HAS_DISC
        cp      UI_SLOT
        ld      hl,t_slkeys
        jr      z,uip_say
        endif
        ld      hl,t_keys
        call    hud_text7
        ld      b,40-20                 ; το t_keys είναι 20 χαρακτήρες, όχι 24:
        call    hud_blank               ; οι τέσσερις τελευταίες στήλες έμεναν
        jr      uip_spd
uip_st:
        ld      a,(ui_bad)
        or      a
        jr      nz,uip_blocked
        call    bd_afford
        jr      nz,uip_poor
        ld      hl,t_ok
        jr      uip_say
uip_blocked:
        ld      hl,t_block
        jr      uip_say
uip_poor:
        ld      hl,t_poor
        jr      uip_say
uip_ln:
        ld      a,(ln_a)
        inc     a
        ld      hl,t_ln1
        jr      z,uip_say
        ld      a,(cr_n)
        or      a
        ld      hl,t_ln2
        jr      z,uip_say
        ld      a,(ui_bad)
        or      a
        ld      hl,t_block
        jr      nz,uip_say
        call    cr_afford
        ld      hl,t_poor
        jr      nz,uip_say
        ld      hl,t_ok
uip_say:
        call    hud_text7
        ld      b,40-20
        call    hud_blank
        ; fall through

; uip_spd — η ταχύτητα, στις πέντε τελευταίες στήλες της σειράς 3. Είναι το
; μόνο σημείο του HUD που γράφεται από τα δεξιά: οι σειρές 0-2 είναι γεμάτες
; ως το τελευταίο κελί (§9.2) και η σειρά 3 τελειώνει με κενά σε κάθε
; κατάσταση.
uip_spd:
        ld      a,3
        call    hud_go
        ld      b,35
        call    hud_adv
        ld      a,(ui_spd)
        add     a,a
        ld      l,a
        ld      h,0
        ld      de,t_spd_ptr
        add     hl,de
        ld      a,(hl)
        inc     hl
        ld      h,(hl)
        ld      l,a
        jp      hud_text7

t_spd_ptr:  dw t_pause, t_x1, t_x2, t_x2, t_x4

; ui_sig — η υπογραφή των σειρών 3-4 στο uip_now.
ui_sig:
        ld      hl,uip_now
        ld      a,(ui_state)
        ld      (hl),a
        inc     hl
        ld      a,(ui_sel)
        ld      (hl),a
        inc     hl
        ld      a,(ui_bad)
        ld      (hl),a
        inc     hl
        ld      a,(ln_a)
        ld      (hl),a
        inc     hl
        ld      a,(cr_n)
        ld      (hl),a
        inc     hl
        ld      a,(cr_l0)               ; δύο διαδρομές ίδιου σχήματος και
        push    hl                      ; διαφορετικού μήκους κοστίζουν αλλιώς
        ld      hl,cr_l1
        add     a,(hl)
        pop     hl
        ld      (hl),a
        inc     hl
        push    hl
        ld      a,(ui_state)
        cp      UI_LINK
        jr      z,uisg_link
        call    bd_afford
        jr      uisg_st
uisg_link:
        call    cr_afford
uisg_st:
        pop     hl
        ld      (hl),a
        inc     hl
        ld      a,(ui_spd)            ; ο δείκτης ταχύτητας ζει στη σειρά 3
        ld      (hl),a
        inc     hl
        ld      a,(hud_gen)           ; γύρισε το δαχτυλίδι; τότε οι σειρές 3-4
        ld      (hl),a                ; δείχνουν έδαφος, ό,τι κι αν λέει το υπόλοιπο
        inc     hl
        ifdef HAS_DISC
        ld      a,(sl_pick)
        else
        xor     a
        endif
        ld      (hl),a
        ret

; ui_dirty — «οι σειρές 3-4 δεν λένε πια αυτό που νομίζω».
ui_dirty:
        ld      a,255
        ld      (uip_sig),a
        ret

; ui_hudall — πλήρες HUD· σβήνει τις σειρές 3-4, άρα ακυρώνει την υπογραφή.
ui_hudall:
        call    hud_draw
        call    ui_dirty                ; ο πίνακας δεν ξέρει τι έγινε από κάτω
        jp      ui_panel


ui_state:   db 0
ui_sel:     db 0
ui_tx:      db 0
ui_ty:      db 0
ui_w:       db 1
ui_h:       db 1
ui_bad:     db 0
ui_dx:      db 0
ui_dy:      db 0
uis_row:    db 0
uis_col:    db 0
ln_a:       db 255
ln_pick:    db 255
uid_tx:     db 0
uid_ty:     db 0
uid_cx:     db 0
uid_cy:     db 0
uip_fe:     dw 0
uip_bi:     dw 0
; Το ui_hold ζει ΕΞΩ από το ifdef του δίσκου: το ui_panel το διαβάζει πάντα,
; και το tests/uitest.asm χτίζεται χωρίς μηνύματα δίσκου. (Το όνομα δεν είναι
; UI_HOLD γιατί ο rasm δεν ξεχωρίζει ετικέτα από alias.)
ui_hold:    db 0
uip_sig:    defs UIP_NSIG, 255
uip_now:    defs UIP_NSIG
cur_hx:     db 0
cur_hy:     db 0
