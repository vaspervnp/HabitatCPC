; ui.asm — ο κέρσορας, το μενού και το φάντασμα (DESIGN §9.1, §9.3).
;
; Τρεις καταστάσεις και τίποτε άλλο:
;
;   LOOK   ο κέρσορας περιφέρεται· η κάμερα τον ακολουθεί στο χείλος
;   MENU   ο κατάλογος του §9.3, μια γραμμή· αριστερά/δεξιά αλλάζει είδος
;   PLACE  το φάντασμα ακολουθεί τον κέρσορα, με τα άκυρα tiles σημαδεμένα
;   LINK   δύο θόλοι, και η διαδρομή του διαδρόμου ανάμεσά τους σαν φάντασμα
;   FIT    ο εξοπλισμός ενός θόλου, υποδοχή-υποδοχή (src/fit.asm)
;   INFO   το LOOK, με τις σειρές 3-4 να λένε τι έχει κάτω ο κέρσορας (info.asm)
;   ACT    το μενού ενεργειών του SPACE: ό,τι γίνεται εδώ (act.asm)
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
UI_INFO     equ 6                       ; τι έχει κάτω ο κέρσορας (βήμα 79· 5 = UI_FIT)
MSG_TICKS   equ 6                       ; τικ HUD που κρατά ένα μήνυμα (§11)

UIP_NSIG    equ 11                      ; bytes υπογραφής των σειρών 3-4
UI_MARGIN   equ 1                       ; tiles από το χείλος πριν σκρολάρει
; Η κάμερα δεν βγαίνει από τον κόσμο (-64..63): πάνω-αριστερά από -64 ως εκεί
; όπου το κάδρο φτάνει στο 63 (βήμα 78).
CAM_MIN     equ #C0                     ; -64
CAM_XMAX    equ 64 - VIEW_TW            ; 44
CAM_YMAX    equ 64 - VIEW_TH            ; 54
PEN_CUR     equ 15                      ; ροζ — το λευκό χανόταν πάνω στα χείλη
                                    ; των διαδρόμων, που είναι κι αυτά λευκά
PEN_OK      equ 9                       ; έντονο πράσινο — επιτρέπεται
PEN_NO      equ 8                       ; έντονο κόκκινο — δεν επιτρέπεται

; ---------------------------------------------------------------------------
; ui_init — κέρσορας στο κέντρο του κόσμου, κατάσταση LOOK.
; ---------------------------------------------------------------------------
ui_init:
        xor     a
        ld      (ui_state),a
        ld      (ui_sel),a
        call    gh_reset
        jr      ui_home

; ui_center — η κάμερα με τον κέρσορα στη μέση του κάδρου.
ui_center:
        call    ui_curt
        ld      a,l
        sub     VIEW_TW/2
        ld      l,a
        ld      a,h
        sub     VIEW_TH/2
        ld      h,a
        ld      (cam_tx),hl             ; cam_tx, cam_ty διπλανά
        ret

; ---------------------------------------------------------------------------
; ui_tick — ένα καρέ εισόδου.
; ---------------------------------------------------------------------------
ui_tick:
        ld      a,(ui_owed)
        or      a
        call    nz,ui_late
        call    in_read
        call    ui_speed
        ld      a,A_HOME
        call    in_hit
        jr      z,uit_state
        call    ui_hide
; ui_home — ο κέρσορας στο κέντρο του κόσμου, η κάμερα μαζί του, όλα από την
; αρχή. Και το ui_init τελειώνει εδώ.
ui_home:
        ld      hl,0
        ld      (cur_hx),hl
        call    ui_center
        call    view_draw
        call    ui_hudall
        jp      ui_show
uit_state:
        ld      a,(ui_state)
        ; ΠΡΩΤΑ ΤΟ LOOK, όπου κάθεται το παιχνίδι: ως το βήμα 80 περνούσε από
        ; πέντε συγκρίσεις για να φτάσει εδώ με πτώση.
        or      a
        jr      z,uist_look
        cp      UI_MENU
        jp      z,uist_menu
        cp      UI_PLACE
        jp      z,uist_place
        cp      UI_LINK
        jp      z,uist_link
        cp      UI_FIT
        jp      z,uist_fit
        ifdef HAS_DISC
        cp      UI_SLOT
        jp      z,uist_slot
        endif
        ifdef HAS_SIM
        cp      UI_ACT
        jp      z,ac_tick               ; src/act.asm, τράπεζα 2
        endif
        ; fall through — UI_INFO

; --- LOOK ------------------------------------------------------------------
uist_look:
        call    ui_move                 ; -> NZ αν κουνήθηκε
        ifdef HAS_SIM
        ; --- INFO (βήμα 79): μια κατάσταση που πέφτει εδώ, όπως το LOOK. Οι
        ; σειρές 3-4 έλεγαν για το tile που ΗΤΑΝ κάτω από τον κέρσορα: μόλις
        ; κουνηθεί, πίσω στο LOOK. ---
        jr      z,usl_still
        ld      hl,ui_state
        ld      a,(hl)
        cp      UI_INFO
        jr      nz,usl_still
        ld      (hl),UI_LOOK
        call    ui_panel
usl_still:
        ; Ενα and για το I και το ESC μαζί, όχι δύο in_hit: στο tick που δεν
        ; πατιέται τίποτα κοστίζει 8 µs αντί για 100.
        ld      a,(act_hit)
        and     1 << A_INFO | 1 << A_CANCEL
        jr      z,usl_go
        add     a,a                     ; το bit 7, το I, στο Cy
        jr      nc,usl_esc
        ld      a,UI_INFO               ; και ένα δεύτερο I τα ξαναδιαβάζει
        jp      ui_ask
        assert  A_INFO == 7 && A_CANCEL < 7
usl_esc:
        ld      a,(ui_state)
        cp      UI_INFO
        jr      nz,usl_go
        xor     a                       ; UI_LOOK
        jp      ui_goto
usl_go:
        endif
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
        ifdef HAS_SIM
        ld      a,A_SHIP
        call    in_hit
        jr      z,ush_none
        jp      ui_ship
ush_none:
        endif
        ld      a,A_FIRE                ; πάνω σε θόλο: ο εξοπλισμός του
        call    in_hit
        jp      nz,fit_enter
        ld      a,A_MENU
        call    in_hit
        ret     z
        ifdef HAS_SIM
        jp      ac_open                 ; το μενού ενεργειών (src/act.asm)
        endif
; ui_build — ο κατάλογος χτισίματος. Από το SPACE στις δοκιμές χωρίς
; προσομοίωση, από το BUILD του μενού ενεργειών στο παιχνίδι.
ui_build:
        call    ui_hide
        ld      a,UI_MENU
        ld      (ui_state),a
        jp      uim_pick

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

ui_owed:    db 0                    ; το φάντασμα δεν ξαναμπήκε μετά την τοποθέτηση
ui_spd_tab: db 0, 1, 2, 4
ui_spd:     db 1                    ; 0 παύση · 1 κανονικά · 2 γρήγορα · 4 πολύ
uis_was:    db 1

        ifdef HAS_SIM
; --- ΤΟ ΠΛΟΙΟ ΤΩΝ ΑΠΟΙΚΩΝ (§6.11) -----------------------------------------
; Το «κουμπί που το καλεί», που το §6.11 άφηνε στο §9. Ενα πλήκτρο και όχι
; μενού: ο κατάλογος πλοίων έχει τρία είδη, από τα οποία ο έμπορος θέλει οθόνη
; ανταλλαγής που δεν υπάρχει και οι επισκέπτες έρχονται μόνοι τους. Μένει ένα
; είδος, και ένα είδος είναι πλήκτρο.
;
; ΧΩΡΙΣ ΑΙΘΟΥΣΑ ΕΛΕΓΧΟΥ ΔΕΝ ΦΕΥΓΕΙ ΠΛΟΙΟ, και αυτό δεν είναι διακόσμηση: το
; ταβάνι πληθυσμού είναι 4 συν 48 ανά Control (§6.11), άρα χωρίς αυτήν οι
; τέσσερις που ήδη ζουν ΕΙΝΑΙ το ταβάνι και το πλοίο θα προσγειωνόταν άδειο.
; ΤΟ ui_hide ΠΡΩΤΑ, ΚΑΙ ΜΟΝΟ ΤΟΥ: πάει στο gh_undo, που χαλάει το HL. Με τη
; σειρά που ήταν γραμμένο (μήνυμα στο HL, μετά ui_hide) το ui_msg τύπωνε από
; σκουπίδια — και επειδή τα σκουπίδια έδειχναν σε μηδενικό, η γραμμή 3 έβγαινε
; ΚΕΝΗ αντί για λάθος. Δοκιμή που κοιτάζει την οθόνη το πιάνει, έλεγχος
; κατάστασης όχι.
ui_ship:
        call    ui_hide
        ld      hl,t_noctl
        ld      a,(G_room_n + R_CONTROL)
        or      a
        jr      z,ush_say
        ld      hl,t_nopad              ; η πίστα είναι όρος του ship_call
        ld      a,(EC_PADNODE)
        cp      255
        jr      z,ush_say
        ld      a,SK_COLONIST
        call    ship_call
        ld      hl,t_ship
        jr      c,ush_say
        ld      hl,t_shipno             ; ένα τη φορά
ush_say:
        jr      ui_say                  ; το ui_msg ζει στο μπλοκ του δίσκου:
        endif                           ; HAS_SIM χωρίς HAS_DISC δεν υπάρχει

        ifdef HAS_DISC
; --- δίσκος ----------------------------------------------------------------
; Μόνο από το LOOK, και με τον κέρσορα σβηστό: το σώσιμο κρατά περίπου δύο
; δευτερόλεπτα με τις διακοπές ανοιχτές και τίποτα δεν σχεδιάζεται στο μεταξύ.
; Το μήνυμα μένει ως το επόμενο ui_panel, δηλαδή ως μία περιστροφή τροχού.
ui_dosave:
        ld      hl,t_saving
        call    uds_go
        call    sv_save
        ld      hl,t_saved
        jr      z,ui_say
        ld      hl,t_dskerr
; ui_say — HL = μήνυμα: στη σειρά 3, ο πίνακας άκυρος, ο κέρσορας πίσω.
ui_say:
        call    ui_msg
        call    ui_dirty
        jp      ui_show

ui_doload:
        ld      hl,t_loading
        call    uds_go
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
        xor     a                       ; UI_LOOK
        ld      (ui_state),a
        ret
usl_fire:
        ld      a,A_FIRE
        call    in_hit
        jr      z,usl_lr
        xor     a                       ; UI_LOOK
        ld      (ui_state),a
        ld      a,(sl_mode)
        or      a
        jr      z,ui_dosave
        jr      ui_doload
usl_lr:
        ld      hl,sl_pick
        ld      c,SV_SLOTS
        call    ui_lr
        ret     z
        ; ΚΑΙ ΤΩΡΑ, όχι στο επόμενο ρολόι του HUD: σε παύση δεν έρχεται ποτέ, και
        ; ως το βήμα 80 η θέση άλλαζε χωρίς να το λέει η σειρά 3.
        call    ui_click
        jp      ui_panel

; ui_askslot — μπαίνει στην επιλογή. A = 0 σώσιμο, 1 φόρτωμα.
; (ΟΧΙ «ui_slot»: ο rasm δεν ξεχωρίζει ετικέτα από alias, και το UI_SLOT
; είναι ήδη σταθερά.)
ui_askslot:
        ld      (sl_mode),a
        call    ui_click
        ld      a,UI_SLOT
        jp      ui_ask                  ; ως το βήμα 80 χωρίς ui_panel: σε παύση
                                        ; η επιλογή δεν φαινόταν καθόλου

; uds_go — η αρχή του σωσίματος και του φορτώματος. HL = το πρώτο μήνυμα.
; Out: A = η θέση. Ο κέρσορας σβηστός, το μήνυμα στη σειρά 3.
;
; Και το νούμερο της θέσης μέσα στα τρία μηνύματα του τέλους, γραμμένο πριν
; φανούν. Οι τρεις μετατοπίσεις είναι μετρημένες στα κείμενα: αν αλλάξει λέξη,
; αλλάζει και ο αριθμός εδώ — γι' αυτό το test_save διαβάζει το ψηφίο από την
; ΟΘΟΝΗ και όχι από τη μνήμη.
uds_go:
        push    hl
        ld      bc,GA_PORT + PAGE_B7    ; τα κείμενα ζουν στην τράπεζα 7
        out     (c),c
        ld      a,(sl_pick)
        add     a,'1'
        ld      (t_saved + 14),a
        ld      (t_loaded + 17),a
        ld      (t_empty + 16),a
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        call    ui_hide
        pop     hl
        call    ui_msg
        ld      a,(sl_pick)
        ret

sl_mode:    db 0
sl_pick:    db 0

; ui_msg — μία γραμμή στη σειρά 3 του HUD, και το υπόλοιπο σβηστό.
ui_msg:
        ; Η τράπεζα 7 ανοίγει ΜΙΑ φορά και για τα δύο: και το τύπωμα και το
        ; μέτρημα του μήκους διαβάζουν από εκεί (§4.2).
        ld      bc,GA_PORT + PAGE_B7
        call    hud_page                ; ο γλύφος (τράπεζα 7) γυρίζει ΕΔΩ
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
        call    hud_page
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
        xor     a                       ; UI_LOOK
        jr      ui_goto
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
        call    ui_click                ; «διάλεξες»: το FIRE στον κατάλογο δεν
        jp      ui_show                 ; αλλάζει τίποτα ορατό εκτός φαντάσματος
uim_lr:
        ; ΔΥΟ ΑΞΟΝΕΣ ΣΤΟ ΙΔΙΟ ΜΕΝΟΥ: δεξιά-αριστερά το αντικείμενο, πάνω-κάτω το
        ; δωμάτιο του θόλου (§6.1). Το πάνω-κάτω δεν έκανε τίποτα ως τώρα.
        ld      a,(bd_kind)
        or      a                       ; BK_DOME
        jr      nz,uim_item
        ld      a,A_UP
        call    in_hit                  ; Z = ΔΕΝ πατήθηκε (βλ. uim_fire πιο πάνω)
        jr      z,uim_dn
        ld      a,255                   ; πάνω = πίσω στη λίστα
        jr      uim_room
uim_dn:
        ld      a,A_DOWN
        call    in_hit
        jr      z,uim_item
        ld      a,1
uim_room:
        call    rm_step
        call    ui_click
        jp      ui_panel                ; το φάντασμα δεν αλλάζει σχήμα, ο
                                        ; πίνακας όμως λέει άλλο δωμάτιο
uim_item:
        ld      hl,ui_sel
        ld      c,BLD_N
        call    ui_lr
        ret     z
        call    ui_hide
; uim_pick — το αντικείμενο του ui_sel στο φάντασμα, με το «κλικ». Και από
; το LOOK, όταν ανοίγει ο κατάλογος.
uim_pick:
        ld      a,(ui_sel)
        call    bd_select
        call    ui_click
        jp      ui_show

; ui_ask — A = μια κατάσταση που ΖΗΤΗΣΕ ο παίκτης και ζει στις σειρές 3-4
; (INFO, ACT, SLOT): το ui_goto, με τον πίνακα άκυρο και χωρίς μήνυμα από
; πάνω. Ενα μήνυμα κρατά τις σειρές έξι κλήσεις του ui_panel, και σε παύση
; δεν το καλεί κανένα ρολόι: το I μετά από ένα μήνυμα δεν έδειχνε ποτέ τίποτα.
; (HAS_DISC: το HAS_SIM δεν υπάρχει χωρίς αυτό.)
        ifdef HAS_DISC
ui_ask:
        ld      hl,uip_sig
        ld      (hl),255                ; ui_dirty, που χαλάει το A
        ld      hl,ui_hold
        ld      (hl),0
        endif
; ui_goto — A = η νέα κατάσταση: σβήνει το φάντασμα, αλλάζει, το ξαναδείχνει.
; ui_goto_h — το ίδιο, με το φάντασμα ήδη σβηστό.
ui_goto:
        push    af
        call    ui_hide
        pop     af
ui_goto_h:
        ld      (ui_state),a
        jp      ui_show

; ui_lr — δεξιά / αριστερά, κυκλικά. HL -> η τιμή, C = πόσες τιμές.
; ui_ud — το ίδιο με κάτω / πάνω (ο εξοπλισμός, src/fit.asm).
; Out: Z = κανένα από τα δύο· αλλιώς NZ, και η τιμή άλλαξε.
; Ως το βήμα 44 γραμμένο δύο φορές, για τη θέση δίσκου και για τον κατάλογο.
ui_ud:
        ld      d,A_DOWN
        jr      uilr_k
ui_lr:
        ld      d,A_RIGHT               ; το «πίσω» είναι πάντα το προηγούμενο
uilr_k:                                 ; πλήκτρο (assert στο fit.asm)
        push    hl
        ld      e,1                     ; το in_hit κρατά τα C, DE
        ld      a,d
        call    in_hit
        jr      nz,uilr_go
        ld      e,c
        dec     e                       ; -1 ≡ πόσες - 1
        ld      a,d
        dec     a
        call    in_hit
uilr_go:
        pop     hl
        ret     z
        ld      a,(hl)
        add     a,e
        cp      c
        jr      c,uilr_set
        sub     c
uilr_set:
        ld      (hl),a
        or      1                       ; NZ, ό,τι κι αν βγήκε
        ret

; ui_click / uip_deny — οι δύο ήχοι που πληρώνονταν με δύο ld σε κάθε σημείο.
ui_click:
        ld      a,SFX_MENU
        jp      snd_play

; --- PLACE -----------------------------------------------------------------
uist_place:
        ld      a,A_CANCEL
        call    in_hit
        jr      z,uip_fire
        ld      a,UI_MENU
        jr      ui_goto
uip_fire:
        ld      a,A_FIRE
        call    in_hit
        jp      z,ui_move
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
        call    bd_redraw               ; το νέο αντικείμενο μπαίνει στη σκηνή
uip_late:
        jr      z,uip_after
        ; ΤΟ ΦΑΝΤΑΣΜΑ ΠΕΡΙΜΕΝΕΙ ΤΟ ΕΡΓΟΤΑΞΙΟ. Θα ξανάπεφτε κόκκινο πάνω στον θόλο
        ; που μόλις μπήκε, και κάθε σειρά που εμφανίζεται από κάτω του θα το
        ; σήκωνε και θα το ξανάριχνε. Το ui_late το δείχνει μόλις βγει η
        ; τελευταία σειρά — ή νωρίτερα, αν ο παίκτης κουνήσει τον κέρσορα. Το
        ; ίδιο και μετά από διαγώνιο διάδρομο, που βγαίνει σειρά-σειρά.
        ld      a,1
        ld      (ui_owed),a
        jp      hud_draw
uip_nospace:
        call    uip_deny
uip_after:
        ; hud_draw, ΟΧΙ ui_hudall: το δεύτερο αναγκάζει και τον πίνακα (σειρές
        ; 3-4) να ξαναγραφτεί, ~20 ms, ενώ ό,τι αλλάζει σε αυτόν με την
        ; τοποθέτηση — εγκυρότητα, κόστος — είναι στην υπογραφή του, και το
        ; ui_show τον ξαναγράφει μόνο αν άλλαξε.
        call    hud_draw
        jp      ui_show
uip_deny:
        ld      a,SFX_DENY
        jp      snd_play

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
        ld      a,UI_MENU
        jp      z,ui_goto_h             ; χωρίς αφετηρία: έξω
        ld      a,255
        ld      (ln_a),a
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
        jr      nz,uip_deny             ; άκυρη διαδρομή — το FIRE δεν κάνει τίποτα
        ld      a,(cr_n)
        or      a
        jr      z,uip_deny
        call    cr_afford
        jr      nz,uip_deny
        call    ui_hide
        call    cr_commit
        or      a
        jr      nz,uip_nospace
        ld      a,255
        ld      (ln_a),a                ; μια διαδρομή τη φορά
        ld      a,SFX_BUILD
        call    snd_play
        call    cr_redraw
        jr      uip_late                ; όπως μετά από θόλο

; ---------------------------------------------------------------------------
; ui_dome — ποιος θόλος είναι κάτω από τον κέρσορα; A = id ή 255.
; ---------------------------------------------------------------------------
ui_dome:
        call    ui_curt
        ld      (uid_tx),hl             ; uid_tx, uid_ty διπλανά
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        ld      c,0
uid_lp:
        ld      a,c
        call    ob_dome_live
        jr      z,uid_next              ; άδεια θέση
        push    bc
        call    ob_domeadr
        ld      e,(hl)                  ; cx, cy σε μισά tiles — ΣΤΗ ΜΝΗΜΗ: το
        inc     hl                      ; cr_look παρακάτω χαλάει το DE
        ld      d,(hl)
        inc     hl
        ld      (uid_cx),de             ; uid_cx, uid_cy διπλανά
        ld      a,(hl)                  ; μέγεθος
        ld      hl,uid_wt
        call    cr_look
        ld      b,a                     ; W σε tiles
        ld      hl,uid_cx
        ld      de,uid_tx
        call    uid_in
        jr      nc,uid_no
        inc     hl
        inc     de
        call    uid_in
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
; uid_out — πίσω η τράπεζα 1, με το AF όπως ήταν. Και για το ui_validate.
uid_out:
        push    af
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        pop     af
        ret

; uid_in — ένας άξονας. (HL) = κέντρο σε μισά tiles, (DE) = το tile του
; κέρσορα, B = W σε tiles. Out: C αν ο κέρσορας είναι μέσα. Το BC του βρόχου
; είναι στη στοίβα· το C εδώ είναι πρόχειρο.
;       left = (κέντρο - W) / 2, ακριβές: κέντρο και W έχουν την ίδια ισοτιμία
uid_in:
        ld      a,(hl)
        sub     b
        sra     a
        ld      c,a
        ld      a,(de)
        sub     c
        cp      b
        ret

uid_wt:     db 4,6,8

; ---------------------------------------------------------------------------
; ln_plan — η διαδρομή από τον (ln_a) στον θόλο κάτω από τον κέρσορα.
; Out: A = (ui_bad): 0 σημαίνει «χτίζεται». (cr_n) = 0 αν δεν υπάρχει καν, και
; τότε το ui_bad λέει γιατί: 1 το σχήμα, 2 η απόσταση (cr_far, βήμα 81).
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
        jr      z,lnp_none
        call    cr_check
        ld      (ui_bad),a
        ret
lnp_none:
        ld      a,(cr_far)
        inc     a
        jr      lnp_bad
lnp_no:                                 ; το cr_n είναι 0 από την αρχή
        ld      a,1
lnp_bad:
        ld      (ui_bad),a
        ret

; ui_mark — B, C = ένα tile του κόσμου: σημάδι φαντάσματος εκεί. Κρατά τα
; BC, DE. Και για τα tiles της διαδρομής (cr_walk), και για τα άκυρα tiles.
ui_mark:
        push    bc
        push    de
        ld      hl,cam_tx
        ld      a,b
        sub     (hl)
        ld      b,a
        inc     hl                      ; cam_ty
        ld      a,c
        sub     (hl)
        ld      c,a
        call    gh_mark
        pop     de
        pop     bc
        ret

; ui_curt — HL = το tile του κέρσορα: L = x, H = y.
ui_curt:
        ld      hl,(cur_hx)
        sra     l
        sra     h
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
        ld      de,0                    ; E = dx, D = dy: το in_held τα κρατά
        ld      a,A_LEFT
        call    in_held
        jr      z,um_r
        ld      e,-2
um_r:
        ld      a,A_RIGHT
        call    in_held
        jr      z,um_u
        ld      e,2
um_u:
        ld      a,A_UP
        call    in_held
        jr      z,um_d
        ld      d,-2
um_d:
        ld      a,A_DOWN
        call    in_held
        jr      z,um_go
        ld      d,2
um_go:
        ld      a,d
        or      e
        ret     z                       ; τίποτα δεν πατήθηκε
        ; ΣΤΟ ΧΕΙΛΟΣ ΤΟΥ ΚΟΣΜΟΥ Ο ΚΕΡΣΟΡΑΣ ΣΤΑΜΑΤΑ. Τα μισά tiles -128..127
        ; είναι ακριβώς τα tiles -64..63, οπότε «βγαίνει από τον κόσμο» είναι
        ; η υπερχείλιση του add. Ως το βήμα 78 τυλιγόταν στην απέναντι άκρη,
        ; και η κάμερα τον ακολουθούσε μέσα από 128 στήλες σκουπίδια.
        ld      hl,(cur_hx)             ; L = hx, H = hy
        ld      a,l
        add     a,e
        jp      po,um_x
        ld      e,0                     ; έξω: αυτός ο άξονας δεν κινείται
        ld      a,l
um_x:
        ld      l,a
        ld      a,h
        add     a,d
        jp      po,um_y
        ld      d,0
        ld      a,h
um_y:
        ld      h,a
        ld      a,d
        or      e
        ret     z                       ; μόνο προς τα έξω: σαν να μην πατήθηκε
        push    hl
        call    ui_hide
        pop     hl
        ld      (cur_hx),hl
        call    ui_follow
        call    ui_show
        ld      a,SFX_MOVE
        call    snd_play
        or      1                       ; NZ: κουνήθηκε
        ret

; ---------------------------------------------------------------------------
; ui_follow — η κάμερα κρατά το αποτύπωμα μέσα στο κάδρο, με ένα tile
; περιθώριο, και σκρολάρει ΜΕ ΛΩΡΙΔΑ — όχι με πλήρη σχεδίαση.
; Η κάμερα σταματά στο χείλος του κόσμου (CAM_MIN..CAM_XMAX/YMAX): εκεί το
; περιθώριο χάνεται και ο κέρσορας φτάνει ως το τελευταίο tile.
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
        ld      a,(hl)                  ; HL = cam_tx
        cp      CAM_MIN
        jr      z,uif_x2                ; το δυτικό χείλος του κόσμου
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
        ld      a,(hl)
        cp      CAM_XMAX
        jr      z,uif_y
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
        ld      a,(hl)                  ; HL = cam_ty
        cp      CAM_MIN
        jr      z,uif_y2
        xor     a                       ; βορράς
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
        ld      a,(hl)
        cp      CAM_YMAX
        ret     z
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
        call    ui_curt
        ld      (ui_tx),hl              ; ui_tx, ui_ty διπλανά
        ld      hl,#0101
        ld      (ui_w),hl               ; ui_w, ui_h διπλανά
        ret
uir_foot:
        call    bd_rect
        ld      hl,(bd_tx)              ; bd_tx, bd_ty διπλανά (build.asm)
        ld      (ui_tx),hl
        ld      hl,(bd_w)               ; bd_w, bd_h διπλανά
        ld      (ui_w),hl
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
        jp      uid_out

; ---------------------------------------------------------------------------
; ui_show / ui_hide — το φάντασμα πάνω στη σκηνή, και πίσω.
; ---------------------------------------------------------------------------
ui_hide:
        jp      gh_undo

; ui_late — το φάντασμα που χρωστά η τοποθέτηση θόλου, ΕΝΑΝ γύρο αφού βγει η
; τελευταία σειρά του (rv_pend = 0). Στον ίδιο γύρο θα πλήρωνε και τη σειρά
; και το φάντασμα: 200 ms, το μακρύτερο καρέ όλης της εμφάνισης.
ui_late:
        ld      a,(rv_pend)
        or      a
        ret     nz
        ld      hl,ui_owed
        ld      a,(hl)
        inc     (hl)                    ; 1 -> 2: ο επόμενος γύρος
        dec     a
        ret     z
        jp      ui_show

ui_show:
        xor     a
        ld      (ui_owed),a             ; κάθε εμφάνιση ξοφλά το χρέος
        call    ui_rect
        ; --- το χρώμα: ροζ κέρσορας, ή πράσινο / κόκκινο για ό,τι χτίζεται ---
        ld      a,(ui_state)
        cp      UI_LINK
        jr      nz,uis_np
        call    ln_plan
        ld      a,(ln_a)
        inc     a
        ld      a,PEN_CUR               ; δεν έχει αφετηρία ακόμη
        jr      z,uis_set
        ld      a,(ui_bad)
        jr      uis_okno
uis_np:
        cp      UI_FIT
        jp      z,fit_show              ; πλαίσιο γύρω από υποδοχή, όχι tile
        cp      UI_PLACE
        ld      a,PEN_CUR
        jr      nz,uis_set
        call    ui_validate
        ld      (ui_bad),a
uis_okno:
        or      a
        ld      a,PEN_OK
        jr      z,uis_set
        ld      a,PEN_NO
uis_set:
        call    gh_setpen
        call    uis_box
        ld      a,(ui_state)
        cp      UI_LINK
        jr      z,uis_route

uis_bad:
        ; --- τα άκυρα tiles ---
        cp      UI_PLACE
        jp      nz,ui_panel
        ld      a,(ui_bad)
        or      a
        jp      z,ui_panel
        ld      a,PEN_NO
        call    gh_setpen
        ld      de,(ui_tx)              ; E = ui_tx, D = ui_ty
        ld      a,(ui_h)
        ld      b,a
        ld      hl,bd_bad               ; ένα byte ανά σειρά, ένα bit ανά στήλη,
uisb_row:                               ; ΜΟΝΟ μέσα στο πλάτος (bd_check)
        push    bc
        push    hl
        ld      a,(hl)
        ld      b,e                     ; στήλη
        ld      c,d                     ; σειρά
uisb_col:
        or      a
        jr      z,uisb_rn               ; τίποτα άλλο σε αυτή τη σειρά
        srl     a
        push    af
        call    c,ui_mark
        pop     af
        inc     b
        jr      uisb_col
uisb_rn:
        pop     hl
        pop     bc
        inc     hl
        inc     d
        djnz    uisb_row
        jp      ui_panel

; --- το φάντασμα της διαδρομής ---------------------------------------------
uis_route:
        ld      a,(cr_n)
        or      a
        jp      z,ui_panel
        ld      hl,ui_mark
        ld      (cr_cb),hl
        call    cr_walk
        jp      ui_panel

; uis_box — το πλαίσιο του (ui_tx, ui_ty, ui_w, ui_h) σε συντεταγμένες οθόνης.
uis_box:
        ld      a,(ui_tx)
        call    ui_sxt
        ld      (gh_bx),hl
        ld      a,(ui_ty)
        call    ui_syt
        ld      (gh_by),hl
        ld      hl,(ui_w)               ; L = w, H = h, σε tiles
        ld      a,l
        add     a,a
        add     a,a
        ld      l,a                     ; x4 bytes
        ld      a,h
        add     a,a
        add     a,a
        add     a,a
        add     a,a
        ld      h,a                     ; x16 γραμμές
        ld      (gh_bw),hl              ; gh_bw, gh_bh διπλανά
        jp      gh_box

; ui_sxt / ui_syt — tile -> οθόνη, προσημασμένα 16 bit:
;       x = 4*(tx - cam_tx) = 2*(2*tx - 2*cam_tx)
;       y = 16*(ty - cam_ty) = 8*(2*ty - 2*cam_ty)
; Το 2*tile - 2*κάμερα είναι το ob_rel με το A διπλασιασμένο σε 16 bit: ένα
; αποτύπωμα στο χείλος του κόσμου αρχίζει πριν από το -64, και το 2*tx δεν
; χωρά σε byte.
ui_sxt:
        ld      de,cam_tx
        call    ui_rel
        add     hl,hl
        ret
ui_syt:
        ld      de,cam_ty
        call    ui_rel
        add     hl,hl
        add     hl,hl
        add     hl,hl
        ret
ui_rel:
        call    ob_sext
        add     hl,hl
        jp      obr_t

; ---------------------------------------------------------------------------
; ui_panel — οι σειρές 3-4 του HUD: τι κρατάς και τι σου λέει το έδαφος.
; ---------------------------------------------------------------------------
; ---------------------------------------------------------------------------
; ΟΙ ΔΥΟ ΣΕΙΡΕΣ ΞΑΝΑΓΡΑΦΟΝΤΑΙ ΜΟΝΟ ΟΤΑΝ ΑΛΛΑΖΟΥΝ. Μετρημένο: ένα βήμα κέρσορα
; κόστιζε 29.952 us και το ui_panel ήταν 14.976 από αυτά — ακριβώς ο μισός
; κέρσορας, για ογδόντα κελιά που συνήθως λένε ακριβώς ό,τι έλεγαν πριν.
; Η υπογραφή είναι ό,τι μπορεί να τις αλλάξει — ΚΑΙ ΤΟ ΔΑΧΤΥΛΙΔΙ: το hud_gen
; του hud_inval είναι το ένατο byte της, γιατί ένα άλμα κάμερας σβήνει τις
; λωρίδες χωρίς να αλλάξει τίποτα από όσα λένε οι σειρές 3-4. (Ως το βήμα 82
; το ίδιο έκανε και κάθε ΒΗΜΑ κάμερας· από το 83 οι λωρίδες μετακινούνται.)
ui_panel:
        ; ΤΟ ΜΗΝΥΜΑ ΚΡΑΤΙΕΤΑΙ. Χωρίς αυτό ζούσε ως το επόμενο ρολόι HUD — δεκαέξι
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
        ld      b,35-33                 ; ως τον δείκτη ταχύτητας (uip_spd)
        call    hud_blank
        jp      uip_row4
uip_notlook:
        ifdef HAS_SIM
        cp      UI_INFO
        jp      z,in_panel              ; src/info.asm, τράπεζα 2
        cp      UI_ACT
        jp      z,ac_panel              ; src/act.asm, τράπεζα 2
        endif
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
        ld      a,(ui_state)
        cp      UI_FIT
        jp      z,fit_name              ; η μηχανή στη θέση του ονόματος
        ; ΓΙΑ ΘΟΛΟ ΤΟ ΟΝΟΜΑ ΕΙΝΑΙ ΤΟ ΔΩΜΑΤΙΟ, και το μέγεθος ένα γράμμα από
        ; πίσω: «OXYGEN     S» λέει και τα δύο σε μία λέξη λιγότερη από
        ; «DOME S». Τα υπόλοιπα του καταλόγου κρατούν το όνομά τους, που ζει
        ; στην τράπεζα 2 μαζί με το build.asm.
        ld      a,(bd_kind)
        or      a
        jr      nz,uipi_nm
        call    rm_name
        call    hud_text7
        ld      b,1
        call    hud_blank
        ld      a,(bd_param)
        ld      hl,uip_szc
        call    ob_addu
        ld      a,(hl)
        call    hud_char
        jr      uipi_arrow
uipi_nm:
        ld      hl,(bd_name)
        call    hud_text   ; τράπεζα 2, όχι 7
        ld      b,3                     ; τα ονόματα καταλόγου είναι 9· τα
        call    hud_blank               ; δωμάτια 10 συν το γράμμα μεγέθους
uipi_arrow:
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
        ld      b,40-34
        call    hud_blank
uip_row4:
        ld      a,4
        call    hud_go
        ld      a,(ui_state)
        cp      UI_LINK
        jr      z,uip_ln
        cp      UI_PLACE
        jr      z,uip_st
        cp      UI_FIT
        jp      z,fit_row4
        ifdef HAS_DISC
        cp      UI_SLOT
        ld      hl,t_slkeys
        jr      z,uip_say
        endif
        ; ΜΕΝΟΥΝ LOOK ΚΑΙ MENU. Στο LOOK η σειρά 4 έλεγε «FIRE=PLACE» ως το
        ; βήμα 44, όταν το FIRE εκεί δεν έκανε τίποτα· από το 45 ανοίγει τον
        ; εξοπλισμό, και το λέει η σειρά 3.
        or      a
        ld      b,40
        jr      z,uip_blk
        ld      hl,t_keys
        ld      b,40-20                 ; το t_keys είναι 20 χαρακτήρες, όχι 24:
                                        ; οι τέσσερις τελευταίες στήλες έμεναν
        ld      a,(bd_kind)
        or      a                       ; σε θόλο, το πάνω-κάτω κάνει κάτι
        jr      nz,uip_ks
        ld      hl,t_keysr
        ld      b,40-22
uip_ks:
        push    bc
        call    hud_text7
        pop     bc
uip_blk:
        call    hud_blank
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
        ; ΓΙΑΤΙ ΟΧΙ, ΟΧΙ ΜΟΝΟ ΟΧΙ. Οταν φταίνε τα tiles, το φάντασμα τα δείχνει
        ; ένα προς ένα με κόκκινο· όταν λείπει το υλικό της δομής (§6.5) δεν
        ; υπάρχει κακό tile να δειχτεί, και ένα σκέτο BLOCKED πάνω σε καθαρό
        ; έδαφος διαβάζεται ως σφάλμα του παιχνιδιού.
        ld      a,(bd_nres)
        ld      hl,t_block
        or      a
        jr      z,uip_say
        dec     a
        ld      hl,t_nowat
        jr      z,uip_say
        ld      hl,t_noore
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
        jr      nz,uip_lnr
        ld      a,(ui_bad)
        dec     a
        ld      hl,t_ln2                ; 1: το σχήμα δεν βγαίνει
        jr      z,uip_say
        ld      hl,t_far                ; 2: >= 64 tiles (βήμα 81)
        jr      uip_say
uip_lnr:
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
        ld      c,35
        call    hud_goc
        ld      a,(ui_spd)
        add     a,a
        ld      hl,t_spd_ptr
        call    ob_addu
        ld      a,(hl)
        inc     hl
        ld      h,(hl)
        ld      l,a
        jp      hud_text7

t_spd_ptr:  dw t_pause, t_x1, t_x2, t_x2, t_x4

; ui_sig — η υπογραφή των σειρών 3-4 στο uip_now.
; ΓΡΑΜΜΕΝΗ ΕΥΘΕΙΑ, ΟΧΙ ΑΠΟ ΠΙΝΑΚΑ. Με πίνακα διευθύνσεων είναι 12 bytes
; μικρότερη (βήμα 44) — και 139 us ακριβότερη σε ΚΑΘΕ βήμα κέρσορα, που
; τρέχει το ui_panel και άρα αυτήν (4.942 -> 5.081 us).
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
        ld      a,(hud_gen)           ; σβήστηκαν οι λωρίδες; τότε οι σειρές 3-4
        ld      (hl),a                ; είναι μαύρες, ό,τι κι αν λέει το υπόλοιπο
        inc     hl
        ifdef HAS_DISC
        ld      a,(sl_pick)
        else
        xor     a
        endif
        ld      (hl),a
        inc     hl
        ld      a,(bd_rsel)             ; το δωμάτιο γράφεται στη σειρά 3
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
uip_szc:    db "SML"
uip_sig:    defs UIP_NSIG, 255
uip_now:    defs UIP_NSIG
cur_hx:     db 0
cur_hy:     db 0

        assert  cam_ty == cam_tx + 1 && cur_hy == cur_hx + 1
        assert  ui_ty == ui_tx + 1 && ui_h == ui_w + 1 && uid_ty == uid_tx + 1
        assert  uid_cy == uid_cx + 1
        assert  gh_bh == gh_bw + 1 && UI_LOOK == 0
