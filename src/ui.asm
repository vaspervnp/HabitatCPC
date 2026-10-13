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
;   ACT    η μπάρα με εστίαση (SPACE), ή η ΔΙΑΧΕΙΡΙΣΗ (M) (act.asm)
;
; ΚΑΙ Η ΜΠΑΡΑ ΤΩΝ ΚΟΥΜΠΙΩΝ (βήμα 84, src/bar.asm): τα γράμματά της διαβάζονται
; πριν από τον διαλογέα, σε όλες εκτός από SLOT και FIT.
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
        assert  PEN_NO >= 8 && PEN_OK >= 8 && PEN_CUR >= 8 && PEN_CUR < 16  ; hud_solid

; ---------------------------------------------------------------------------
; ui_init — κέρσορας στο κέντρο του κόσμου, κατάσταση LOOK.
; ---------------------------------------------------------------------------
ui_init:
        ld      hl,0
        ld      (ui_state),hl           ; ui_state, ui_sel διπλανά
        call    gh_reset
        jr      ui_home

        ifndef HAS_SIM
; ui_center — η κάμερα με τον κέρσορα στη μέση του κάδρου. Μόνο για το
; do_goto του tests/uitest.asm: το ui_home ξέρει τον κέρσορα (0, 0).
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
        endif

; ---------------------------------------------------------------------------
; ui_tick — ένα καρέ εισόδου.
; ---------------------------------------------------------------------------
ui_tick:
        ld      a,(ui_owed)
        or      a
        call    nz,ui_late
        ifdef HAS_SIM
        ld      a,(bs_pend)             ; κουμπιά που δεν πρόλαβαν (src/bar.asm)
        or      a
        call    nz,bar_more
        endif
        call    in_read
        call    ui_speed
        ; Το H με ένα rra, όχι in_hit (βήμα 84): ~50 us σε κάθε frame.
        ld      a,(act_hit + 1)
        rra                             ; A_HOME: το bit 8
        jr      nc,uit_state
        call    ui_hide
; ui_home — ο κέρσορας στο κέντρο του κόσμου, η κάμερα μαζί του, όλα από την
; αρχή. Και το ui_init τελειώνει εδώ.
ui_home:
        ld      hl,0
        ld      (cur_hx),hl
        ; η κάμερα με τον κέρσορα (tile 0, 0) στη μέση του κάδρου
        ld      hl,(256 - VIEW_TH/2) * 256 + 256 - VIEW_TW/2
        ld      (cam_tx),hl             ; cam_tx, cam_ty διπλανά
        call    view_draw
uh_show:                                ; και το τέλος της βοήθειας (src/help.asm)
        call    ui_hudall
        jp      ui_show
uit_state:
        ifdef HAS_SIM
        ; ΤΑ ΓΡΑΜΜΑΤΑ ΤΗΣ ΜΠΑΡΑΣ (src/bar.asm, βήμα 84), σε κάθε κατάσταση που
        ; δείχνει κουμπιά για πάτημα: όχι στη θέση δίσκου και στον εξοπλισμό,
        ; που έχουν δικά τους πλήκτρα και η μπάρα εκεί είναι μόνο εικόνα.
        ld      a,(ui_state)
        sub     UI_SLOT                 ; SLOT 0, FIT 1 (assert στο fit.asm)
        cp      2
        jr      c,uit_nobar
        call    bk_scan
        jp      c,bt_key                ; src/act.asm, τράπεζα 2
uit_nobar:
        endif
        ld      a,(ui_state)
        ; ΠΡΩΤΑ ΤΟ LOOK, όπου κάθεται το παιχνίδι: ως το βήμα 80 περνούσε από
        ; πέντε συγκρίσεις για να φτάσει εδώ με πτώση.
        ; Οι υπόλοιπες με dec a, με τη σειρά των τιμών (assert στο fit.asm).
        or      a
        jr      z,uist_look
        dec     a
        jp      z,uist_menu             ; 1
        dec     a
        jp      z,uist_place            ; 2
        dec     a
        jp      z,uist_link             ; 3
        dec     a
        ifdef HAS_DISC
        jp      z,uist_slot             ; 4
        endif
        dec     a
        jp      z,uist_fit              ; 5
        ifdef HAS_SIM
        cp      UI_ACT - UI_FIT
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
        jp      z,ui_golook
usl_go:
        endif
        ; ΤΑ ΥΠΟΛΟΙΠΑ ΠΛΗΚΤΡΑ ΤΟΥ LOOK ΜΕ ΔΥΟ and (βήμα 84). Ως τότε πέντε
        ; in_hit σε ΚΑΘΕ frame — S, L, C, FIRE, SPACE — 50-68 us το καθένα,
        ; σχεδόν 300 us για να μάθει ότι δεν πατήθηκε τίποτα. Τα γράμματα της
        ; μπάρας που μπήκαν στη θέση τους κοστίζουν 9 us το καθένα (bk_scan).
        ; Η σειρά προτεραιότητας μένει: δίσκος, πλοίο, FIRE, SPACE.
        ld      a,(act_hit + 1)
        and     1 << (A_SAVE - 8) | 1 << (A_LOAD - 8) | 1 << (A_SHIP - 8)
        jr      nz,usl_rare
        ld      a,(act_hit)
        and     1 << A_FIRE | 1 << A_MENU
        ret     z
        and     1 << A_FIRE             ; πάνω σε θόλο: ο εξοπλισμός του
        jp      nz,fit_enter
        ifdef HAS_SIM
        jp      ac_open                 ; η μπάρα (src/act.asm)
        else
        jp      ui_build
        endif
usl_rare:
        ; Ο δίσκος υπάρχει μόνο στο πλήρες παιχνίδι: τα tests/uitest.asm και
        ; tests/objtest.asm δένουν τον renderer χωρίς τροχό και χωρίς οδηγό
        ; δισκέτας, και δεν έχουν πού να σώσουν.
        ifdef HAS_DISC
        ; Το A είναι ακόμη το act_hit + 1 με τη μάσκα: τα bits του, όχι in_hit.
        ; Δύο add τα βγάζουν στις σημαίες: S = A_SAVE, CY = A_LOAD (βήμα 103).
        add     a,a
        add     a,a
        ld      a,0                     ; 0 = σώσιμο
        jp      m,ui_askslot
        inc     a                       ; 1 = φόρτωμα· το inc κρατά το CY
        jp      c,ui_askslot
        assert  A_SAVE - 8 == 5 && A_LOAD - 8 == 6
usv_none:
        endif
        ifdef HAS_SIM
        jp      cw_open                 ; ό,τι μένει είναι το C (src/crew.asm)
        else
        ret
        endif
        assert  A_SAVE >= 8 && A_LOAD >= 8 && A_SHIP >= 8 && A_FIRE < 8 && A_MENU < 8

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
        ; ΤΙΠΟΤΑ ΑΠΟ ΤΑ ΤΕΣΣΕΡΑ, ΤΙΠΟΤΑ ΝΑ ΓΙΝΕΙ (βήμα 84): τέσσερα in_hit ήταν
        ; ~230 us σε κάθε frame κάθε κατάστασης, για ένα πλήκτρο που πατιέται
        ; σπάνια. Ενα and τα ρωτά όλα μαζί· ό,τι κέρδισε εδώ πληρώνει τα
        ; γράμματα της μπάρας (bk_scan).
        ld      a,(act_hit + 1)
        and     1 << (A_SPD1 - 8) | 1 << (A_SPD2 - 8) | 1 << (A_SPD3 - 8) | 1 << (A_SPD4 - 8)
        ret     z
        ; Τα bits 1-4 ένα-ένα από τα δεξιά, όχι in_hit: το τελευταίο πατημένο
        ; κερδίζει, όπως ως τώρα. Το bit 0 (A_HOME) είναι σβηστό από το and,
        ; άρα το ui_spd_tab - 1 δεν γράφεται ποτέ.
        ld      hl,ui_spd
        ld      c,(hl)                  ; C = η ταχύτητα πριν
        ld      b,a
        ld      de,ui_spd_tab - 1
uis_lp:
        srl     b
        jr      nc,uis_next
        ld      a,(de)
        ld      (hl),a
uis_next:
        inc     de                      ; δεν αγγίζει τις σημαίες του srl
        jr      nz,uis_lp
        ld      a,(hl)
        cp      c
        ret     z
        jp      ui_dpan                 ; ui_dirty, ui_panel: στην παύση ο τροχός
                                        ; δεν ξαναφτάνει στη θέση 0, άρα τώρα ή ποτέ

ui_owed:    db 0                    ; το φάντασμα δεν ξαναμπήκε μετά την τοποθέτηση
ui_spd_tab: db 0, 1, 2, 4
ui_spd:     db 1                    ; 0 παύση · 1 κανονικά · 2 γρήγορα · 4 πολύ
        assert  A_SPD1 == A_HOME + 1 && A_SPD2 == A_SPD1 + 1 && A_SPD3 == A_SPD2 + 1 && A_SPD4 == A_SPD3 + 1

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
        inc     a                       ; 255: καμία πίστα
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
uds_err:
        ld      hl,t_dskerr
; ui_say — HL = μήνυμα: στη σειρά 3, ο πίνακας άκυρος, ο κέρσορας πίσω.
ui_say:
        call    udl_ok                  ; ui_msg, ui_dirty
        jp      ui_show

; --- SLOT: ποιο από τα τρία -------------------------------------------------
; Ο δίσκος είχε ΠΑΝΤΑ τρεις θέσεις (§11) και το παιχνίδι έγραφε πάντα στην
; πρώτη: το sv_save έπαιρνε slot σε A και το UI έδινε `xor a`. Δύο από τις
; τρεις — 46 KB δίσκου — δεν είχαν γραφτεί ποτέ, ούτε σε δοκιμή.
;
; Η κατάσταση είναι κοινή για σώσιμο και φόρτωμα· το sl_mode ξεχωρίζει.
; (Το usl_lr πρώτο, ώστε το uist_slot να πέφτει στο ui_doload.)
usl_lr:
        ld      hl,sl_pick
        ld      c,SV_SLOTS
        call    ui_lr
        ret     z
        ; ΚΑΙ ΤΩΡΑ, όχι στο επόμενο ρολόι του HUD: σε παύση δεν έρχεται ποτέ, και
        ; ως το βήμα 80 η θέση άλλαζε χωρίς να το λέει η σειρά 3.
        jp      uim_cp                  ; ui_click, ui_panel
uist_slot:
        ld      a,(act_hit)             ; ESC ή FIRE: πίσω στο LOOK
        and     1 << A_CANCEL | 1 << A_FIRE
        jr      z,usl_lr
        ld      hl,ui_state
        ld      (hl),UI_LOOK
        and     1 << A_CANCEL           ; το ESC πρώτο, όπως ως τώρα
        ret     nz
        ld      a,(sl_mode)
        or      a
        jr      z,ui_dosave
        ; fall through

ui_doload:
        ld      hl,t_loading
        call    uds_go
        call    sv_load                 ; πετυχαίνοντας, ξανασχεδιάζει τα πάντα
        ld      hl,t_loaded
        jr      z,udl_ok
        ; Αδεια θέση ΔΕΝ είναι βλάβη δίσκου, και το μήνυμα το έλεγε λάθος: το
        ; sv_hdr_ok γυρίζει #FF όταν η υπογραφή δεν ταιριάζει, ο ελεγκτής
        ; οτιδήποτε άλλο. Αποτυχία: ui_say, ο κέρσορας ήταν κρυμμένος.
        inc     a                       ; #FF
        ld      hl,t_empty
        jr      z,ui_say
        jr      uds_err
udl_ok:
        call    ui_msg                  ; επιτυχία: το sv_after τον έδειξε ήδη
        jp      ui_dirty

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
        call    dho_out                 ; πίσω η 1 (src/dirty.asm)
        call    ui_hide
        pop     hl
        call    ui_msg
        ld      a,(sl_pick)
        ret

sl_mode:    db 0
sl_pick:    db 0

; ui_msg — μία γραμμή στη σειρά 3 του HUD, και το υπόλοιπο σβηστό.
ui_msg:
        ; Κενά ως τη στήλη 40 με το hud_to, όπως το uip_say: ξέρει τη στήλη
        ; (hud_tb), και δεν χρειάζεται δεύτερο πέρασμα για το μήκος.
        push    hl
        ld      a,3
        call    hud_go                  ; δεν διαβάζει τράπεζα
        pop     hl
        call    hud_text7
        ld      a,MSG_TICKS
        ld      (ui_hold),a
        ld      b,40
        jp      hud_to

        endif

; --- MENU ------------------------------------------------------------------
uist_menu:
        ; ΚΑΘΕ πλήκτρο του MENU είναι ακμή (ESC, FIRE, τα βελάκια): χωρίς καμία,
        ; τίποτα να ελεγχθεί (βήμα 84 — ως τότε πέντε in_hit ανά frame).
        ; Και τα bits τους από το L, όχι in_hit: όλα είναι στο act_hit, και το
        ; L μένει ως το uim_dn (assert πιο κάτω).
        ld      hl,(act_hit)
        ld      a,h
        or      l
        ret     z
        bit     A_CANCEL,l
        jr      z,uim_fire
; ui_golook — πίσω στο LOOK (το ui_goto με A = UI_LOOK).
ui_golook:
        xor     a                       ; UI_LOOK
        jr      ui_goto
uim_fire:
        bit     A_FIRE,l
        jr      z,uim_lr
        call    ui_hide
        ld      a,(bd_kind)
        cp      BK_LINK
        ld      a,UI_PLACE
        jr      nz,uim_go
        ld      hl,ln_a
        ld      (hl),255                ; ακόμη δεν έχει διαλεγεί αφετηρία
        inc     a                       ; UI_LINK (assert στο fit.asm)
uim_go:
        ld      (ui_state),a            ; «διάλεξες»: το FIRE στον κατάλογο δεν
        jr      uim_cs                  ; αλλάζει τίποτα ορατό εκτός φαντάσματος
uim_lr:
        ; ΔΥΟ ΑΞΟΝΕΣ ΣΤΟ ΙΔΙΟ ΜΕΝΟΥ: δεξιά-αριστερά το αντικείμενο, πάνω-κάτω το
        ; δωμάτιο του θόλου (§6.1). Το πάνω-κάτω δεν έκανε τίποτα ως τώρα.
        ld      a,(bd_kind)
        or      a                       ; BK_DOME
        jr      nz,uim_item
        bit     A_UP,l                  ; Z = ΔΕΝ πατήθηκε
        jr      z,uim_dn
        dec     a                       ; 255: πάνω = πίσω στη λίστα (A = 0 εδώ)
        jr      uim_room
uim_dn:
        bit     A_DOWN,l
        jr      z,uim_item
        inc     a                       ; 1 (A = 0 εδώ)
uim_room:
        call    rm_step
uim_cp:                                 ; και το usl_lr
        call    ui_click
        jp      ui_panel                ; το φάντασμα δεν αλλάζει σχήμα, ο
                                        ; πίνακας όμως λέει άλλο δωμάτιο
uim_item:
        ld      hl,ui_sel
        ld      c,BLD_N
        call    ui_lr
        ret     z
        ; fall through: η κατάσταση είναι ήδη MENU, και το ui_build την ξαναγράφει
; ui_build — ο κατάλογος χτισίματος. Από το SPACE στις δοκιμές χωρίς
; προσομοίωση, από το κουμπί μιας ομάδας στο παιχνίδι (src/act.asm, btk_group).
ui_build:
        call    ui_hide
        ld      a,UI_MENU
        ld      (ui_state),a
; uim_pick — το αντικείμενο του ui_sel στο φάντασμα, με το «κλικ». Και από
; το LOOK, όταν ανοίγει ο κατάλογος.
uim_pick:
        ld      a,(ui_sel)
        call    bd_select
uim_cs:
        call    ui_click
        jp      ui_show
        assert  A_CANCEL < 8 && A_FIRE < 8 && A_UP < 8 && A_DOWN < 8   ; uist_menu: το L

; ui_ask — A = μια κατάσταση που ΖΗΤΗΣΕ ο παίκτης και ζει στις σειρές 3-4
; (INFO, ACT, SLOT): το ui_goto, με τον πίνακα άκυρο και χωρίς μήνυμα από
; πάνω. Ενα μήνυμα κρατά τις σειρές έξι κλήσεις του ui_panel, και σε παύση
; δεν το καλεί κανένα ρολόι: το I μετά από ένα μήνυμα δεν έδειχνε ποτέ τίποτα.
; (HAS_DISC: το HAS_SIM δεν υπάρχει χωρίς αυτό.)
        ifdef HAS_DISC
ui_ask:
        ld      hl,ui_hold
        ld      (hl),0
        inc     hl                      ; uip_sig
        ld      (hl),255                ; ui_dirty, που χαλάει το A
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
; Τα bits του act_hit κατευθείαν, όχι in_hit (βήμα 103): D = η μάσκα του
; «μπρος», και το «πίσω» είναι το προηγούμενο bit (assert στο fit.asm).
; Χαλάει B, D.
ui_ud:
        ld      d,1 << A_DOWN
        jr      uilr_k
ui_lr:
        ld      d,1 << A_RIGHT
uilr_k:
        ld      e,1
        ld      a,(act_hit)
        ld      b,a
        and     d
        jr      nz,uilr_go
        ld      e,c
        dec     e                       ; -1 ≡ πόσες - 1
        ld      a,d
        rrca                            ; αριστερά / πάνω
        and     b
uilr_go:
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

; --- PLACE -----------------------------------------------------------------
uist_place:
        ; Ενα and για το ESC και το FIRE (βήμα 84): δύο in_hit ήταν ~105 us σε
        ; κάθε frame του PLACE, και τα γράμματα της μπάρας κοστίζουν τώρα εκεί.
        ld      a,(act_hit)
        and     1 << A_CANCEL | 1 << A_FIRE
        jp      z,ui_move
        and     1 << A_CANCEL
        jr      z,uip_fire
uip_menu:                               ; και η ακύρωση του LINK χωρίς αφετηρία
        ld      a,UI_MENU
        jr      ui_goto
uip_fire:
        call    ui_validate
        or      a
        jr      nz,uip_deny             ; άκυρη θέση — το FIRE δεν κάνει τίποτα
        call    al_afford               ; και οι διάδρομοι μαζί (βήμα 85)
        jr      nz,uip_deny             ; ούτε τα υλικά φτάνουν
        call    ui_hide
        call    bd_commit
        inc     a                       ; 255: δεν χωρά
        jr      z,uip_nospace
        ld      a,SFX_BUILD
        call    snd_play
        call    bd_redraw               ; το νέο αντικείμενο μπαίνει στη σκηνή
        ; ΟΙ ΔΙΑΔΡΟΜΟΙ ΜΕΤΑ ΑΠΟ ΤΟ ΕΡΓΟΤΑΞΙΟ. Η διαγώνιος ξεκινά από τη γωνία
        ; του αποτυπώματος, και η σειρά του εργοταξίου (dh_site) ζωγραφίζει
        ; μόνο τον θόλο πάνω στο έδαφος: αν οι σειρές της διαγωνίου έμπαιναν
        ; πρώτες στη λίστα, η γωνία θα έσβηνε (test_fit, βήμα 85).
        push    af
        call    al_commit               ; οι διάδρομοι, ή το μονοπάτι (src/link.asm)
        pop     af
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
; uip_deny / ui_click — οι δύο ήχοι που πληρώνονταν με δύο ld σε κάθε σημείο.
uip_deny:
        ld      a,SFX_DENY
        db      #11                     ; ld de,nn: προσπερνά το ld a,SFX_MENU· το
ui_click:                               ; snd_play γράφει το DE πριν το διαβάσει
        ld      a,SFX_MENU
        jp      snd_play

; --- LINK ------------------------------------------------------------------
; Δύο πατήματα: το πρώτο διαλέγει την αφετηρία, το δεύτερο τον προορισμό. Η
; ακύρωση ξηλώνει ένα βήμα τη φορά — αφήνει πρώτα την αφετηρία και μετά βγαίνει
; από την κατάσταση, γιατί το να χάνεις και τα δύο με ένα πάτημα είναι η
; συνηθέστερη αιτία να ξαναδιαλέγεις τα ίδια.
uist_link:
        ld      a,(act_hit)             ; όπως το PLACE (βήμα 84)
        and     1 << A_CANCEL | 1 << A_FIRE
        jp      z,ui_move
        and     1 << A_CANCEL
        jr      z,uil_fire
        ld      a,(ln_a)
        inc     a
        jr      z,uip_menu              ; χωρίς αφετηρία: έξω (ui_goto)
        ld      a,255
        jr      uil_set
uil_fire:
        call    ui_dome                 ; Z: κανένας
        ret     z                       ; ο κέρσορας δεν είναι πάνω σε θόλο
        ld      e,a
        ld      a,(ln_a)
        inc     a
        jr      nz,uil_second
        ld      a,e
uil_set:
        ld      (ln_a),a                ; το ui_hide (gh_undo) δεν το διαβάζει
; ui_redo — το φάντασμα από την αρχή. Και για τον εξοπλισμό (src/fit.asm).
ui_redo:
        call    ui_hide
        jp      ui_show
uil_second:
        call    ln_plan                 ; A = 0 μόνο με διαδρομή (cr_n >= 1)
        or      a
        jr      nz,uip_deny             ; άκυρη διαδρομή — το FIRE δεν κάνει τίποτα
        call    cr_afford
        jr      nz,uip_deny
        call    ui_hide
        call    cr_commit_ln            ; και η ακμή, αν είναι έτοιμοι (βήμα 87)
        jr      nz,uip_nospace          ; Z αν A = 0 (src/route.asm)
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
        call    ob_b6
        ld      c,0
uid_lp:
        ld      a,c
        call    ob_dome_live            ; HL -> D_STATE του θόλου
        jr      z,uid_next              ; άδεια θέση
        push    bc
        dec     hl
        dec     hl                      ; D_SIZE
        ld      a,(hl)
        add     a,2
        add     a,a
        ld      b,a                     ; W σε tiles: 4, 6, 8
        dec     hl
        ld      d,(hl)                  ; cy σε μισά tiles
        dec     hl
        ld      a,(hl)                  ; cx
        ld      hl,(uid_tx)             ; L = tx, H = ty
        call    uid_in
        jr      nc,uid_no
        ld      a,d
        ld      l,h
        call    uid_in
        jr      nc,uid_no
        pop     bc
        ld      a,c
        jr      uid_out                 ; NZ από το cp b του uid_in: βρέθηκε
uid_no:
        pop     bc
uid_next:
        inc     c
        ld      a,c
        cp      MAX_DOME
        jr      c,uid_lp
        ld      a,255                   ; Z από το cp: κανένας θόλος (οι καλούντες)
; uid_out — πίσω η τράπεζα 1, με το AF όπως ήταν. Και για το ui_validate.
uid_out:
        push    af
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        pop     af
        ret

; uid_in — ένας άξονας. A = κέντρο σε μισά tiles, L = το tile του κέρσορα,
; B = W σε tiles. Out: C αν ο κέρσορας είναι μέσα. Το BC του βρόχου είναι στη
; στοίβα· το C εδώ είναι πρόχειρο.
;       left = (κέντρο - W) / 2, ακριβές: κέντρο και W έχουν την ίδια ισοτιμία
uid_in:
        sub     b
        sra     a
        ld      c,a
        ld      a,l
        sub     c
        cp      b
        ret
        assert  D_CY == D_CX + 1 && D_SIZE == D_CY + 1 && D_STATE == D_SIZE + 2

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
        call    ui_dome                 ; Z: κανένας
        jr      z,lnp_no
        ld      hl,ln_a
        cp      (hl)
        jr      z,lnp_no                ; ο ίδιος θόλος με τον εαυτό του
        ld      (cr_b),a
        ld      a,(hl)                  ; HL = ln_a
        ld      (cr_a),a
        call    cr_plan                 ; Z αν A = 0, σε κάθε έξοδο
        jr      z,lnp_none
        call    cr_check
        jr      lnp_bad
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
        ; Τα τέσσερα bits του act_now με bit, όχι τέσσερα in_held.
        ld      de,0                    ; E = dx, D = dy
        ld      a,(act_now)
        bit     A_LEFT,a
        jr      z,um_r
        ld      e,-2
um_r:
        bit     A_RIGHT,a
        jr      z,um_u
        ld      e,2
um_u:
        bit     A_UP,a
        jr      z,um_d
        ld      d,-2
um_d:
        bit     A_DOWN,a
        jr      z,um_go
        ld      d,2
um_go:
        assert  A_LEFT < 8 && A_RIGHT < 8 && A_UP < 8 && A_DOWN < 8
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
        ld      (cur_hx),hl             ; το ui_hide (gh_undo) δεν το διαβάζει
        call    ui_hide
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
        sub     (hl)                    ; 0, ή αρνητικό: ο κέρσορας αριστερά
        jr      z,uif_west              ; (UI_MARGIN = 1)
        jp      p,uif_x2
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
        jr      z,uif_north
        jp      p,uif_y2
        assert  UI_MARGIN == 1
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
        ld      de,#0101
        jr      uir_set
uir_foot:
        call    bd_rect
        ld      hl,(bd_w)               ; bd_w, bd_h διπλανά (build.asm)
        ex      de,hl
        ld      hl,(bd_tx)              ; bd_tx, bd_ty διπλανά
uir_set:
        ld      (ui_tx),hl              ; ui_tx, ui_ty διπλανά
        ld      (ui_w),de               ; ui_w, ui_h διπλανά
        ret

; ---------------------------------------------------------------------------
; ui_validate — Out: A = 0 αν η θέση επιτρέπεται: το έδαφος (bd_check), και
; από το βήμα 85 ένα κτίσμα σε απόσταση για να δεθεί (al_plan). ΜΟΝΟ ΣΤΟ PLACE:
; οι δύο καλούντες (uip_fire, uis_np) είναι ήδη εκεί (βήμα 103: ως τότε το
; ξαναρωτούσε, και έξω από αυτό γύριζε 0).
; ---------------------------------------------------------------------------
ui_validate:
        xor     a
        ; ΤΟ bd_nres ΑΠΟ ΤΟ ΜΗΔΕΝ (βήμα 85). Το γράφουν μόνο το bd_res και το
        ; al_plan, όταν τα tiles είναι καλά· μετά από θέση με κακά tiles έμενε
        ; ό,τι είπε η προηγούμενη, και το ui_bad (al_plan) το διαβάζει.
        ld      (bd_nres),a
        ld      bc,GA_PORT + PAGE_B4
        out     (c),c
        call    bd_check
        jp      al_plan                 ; τελειώνει στο uid_out

; ui_rel — tile -> οθόνη, προσημασμένα 16 bit (το πλαίσιο του ui_show):
;       x = 4*(tx - cam_tx) = 2*(2*tx - 2*cam_tx)
;       y = 16*(ty - cam_ty) = 8*(2*ty - 2*cam_ty)
; Το 2*tile - 2*κάμερα είναι το ob_rel με το A διπλασιασμένο σε 16 bit: ένα
; αποτύπωμα στο χείλος του κόσμου αρχίζει πριν από το -64, και το 2*tx δεν
; χωρά σε byte.
ui_rel:
        call    ob_sext
        add     hl,hl
        jp      obr_t

; ---------------------------------------------------------------------------
; ui_show / ui_hide — το φάντασμα πάνω στη σκηνή, και πίσω.
; ---------------------------------------------------------------------------
; (το ui_hide είναι ετικέτα πάνω στο gh_undo, src/ghost.asm: βήμα 100)

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
        ; fall through

ui_show:
        xor     a
        ld      (ui_owed),a             ; κάθε εμφάνιση ξοφλά το χρέος
        call    ui_rect
        ; --- το χρώμα: ροζ κέρσορας, ή πράσινο / κόκκινο για ό,τι χτίζεται ---
        ld      a,(ui_state)
        cp      UI_LINK
        jr      nz,uis_np
        call    ln_plan                 ; A = (ui_bad), σε κάθε δρόμο
        ld      b,a
        ld      a,(ln_a)
        inc     a
        ld      a,PEN_CUR               ; δεν έχει αφετηρία ακόμη
        jr      z,uis_set
        ld      a,b
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
        dec     a                       ; PEN_NO
        assert  PEN_NO == PEN_OK - 1
uis_set:
        call    gh_setpen
        ; --- το πλαίσιο του (ui_tx, ui_ty, ui_w, ui_h) σε συντεταγμένες οθόνης
        ; (ως το βήμα 102 το uis_box, με μόνο αυτόν τον καλούντα) ---
        ld      a,(ui_tx)
        ld      de,cam_tx
        call    ui_rel
        add     hl,hl                   ; x = 4*(tx - cam_tx)
        ld      (gh_bx),hl
        ld      a,(ui_ty)
        ld      de,cam_ty
        call    ui_rel
        add     hl,hl
        add     hl,hl
        add     hl,hl                   ; y = 16*(ty - cam_ty)
        ld      (gh_by),hl
        ld      hl,(ui_w)               ; L = w, H = h, σε tiles: w <= GH_SIDE
        add     hl,hl
        add     hl,hl                   ; L = 4w χωρίς κρατούμενο, H = 4h
        ld      a,h
        add     a,a
        add     a,a
        ld      h,a                     ; x16 γραμμές
        ld      (gh_bw),hl              ; gh_bw, gh_bh διπλανά
        assert  GH_SIDE * 4 < 256
        call    gh_box
        ld      a,(ui_state)
        cp      UI_LINK
        jr      z,uis_route

uis_bad:
        ; --- τα άκυρα tiles ---
        cp      UI_PLACE
        jr      nz,ui_panel
        ld      a,(ui_bad)
        or      a
        jp      z,al_ghost              ; οι δεσμοί, πράσινοι (βήμα 85)
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
        jr      ui_panel

; --- το φάντασμα της διαδρομής ---------------------------------------------
uis_route:
        ld      a,(cr_n)
        or      a
        jr      z,ui_panel
        ld      hl,ui_mark
        ld      (cr_cb),hl
        call    cr_walk
        ; fall through

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
        ifdef HAS_SIM
        ; Η ΜΠΑΡΑ ΠΡΩΤΑ, έξω από το ui_hold: ένα μήνυμα κρατά τις σειρές 3-4,
        ; όχι τα κουμπιά (src/bar.asm, βήμα 84).
        call    bar_sync
        endif
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
        ; ΣΥΓΚΡΙΣΗ ΚΑΘΩΣ ΔΙΑΒΑΖΕΙ (βήμα 84), όπως το bar_sync: ως τότε το ui_sig
        ; έγραφε τα έντεκα bytes και ένας βρόχος τα σύγκρινε, ~150 us μόνο ο
        ; βρόχος. Το ui_sig γράφει πια μόνο όταν κάτι διαφέρει.
        inc     hl                      ; uip_sig: το HL είναι ακόμη ui_hold
        ld      a,(ui_state)
        cp      (hl)
        jr      nz,uipc_go
        inc     hl
        ld      a,(ui_sel)
        cp      (hl)
        jr      nz,uipc_go
        inc     hl
        ld      a,(ui_bad)
        cp      (hl)
        jr      nz,uipc_go
        inc     hl
        ld      a,(ln_a)
        cp      (hl)
        jr      nz,uipc_go
        inc     hl
        ld      a,(cr_n)
        cp      (hl)
        jr      nz,uipc_go
        inc     hl
        push    hl
        call    uis_aff
        pop     hl
        cp      (hl)
        jr      nz,uipc_go
        inc     hl
        ld      a,(cr_metal)            ; ΜΕΤΑ το uis_aff, που το ξαναμετρά
        cp      (hl)
        jr      nz,uipc_go
        inc     hl
        ld      a,(ui_spd)
        cp      (hl)
        jr      nz,uipc_go
        inc     hl
        ld      a,(hud_gen)
        cp      (hl)
        jr      nz,uipc_go
        inc     hl
        ifdef HAS_DISC
        ld      a,(sl_pick)
        else
        xor     a
        endif
        cp      (hl)
        jr      nz,uipc_go
        inc     hl
        ld      a,(bd_rsel)
        cp      (hl)
        ret     z                       ; τίποτα δεν άλλαξε
uipc_go:
        ; ΤΟ ui_sig, ΕΔΩ: η υπογραφή των σειρών 3-4 γράφεται κατευθείαν στο
        ; uip_sig (ως το βήμα 97 στο uip_now, και ένα ldir την αντέγραφε).
        ; ΓΡΑΜΜΕΝΗ ΕΥΘΕΙΑ, ΟΧΙ ΑΠΟ ΠΙΝΑΚΑ. Με πίνακα διευθύνσεων είναι 12 bytes
        ; μικρότερη (βήμα 44) — και 139 us ακριβότερη σε ΚΑΘΕ βήμα κέρσορα, που
        ; τρέχει το ui_panel και άρα αυτήν (4.942 -> 5.081 us).
        ld      hl,uip_sig
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
        push    hl
        call    uis_aff
        pop     hl
        ld      (hl),a
        inc     hl
        ; ΤΟ ΚΟΣΤΟΣ, όχι το μήκος (βήμα 85): δύο διαδρομές ίδιου σχήματος και
        ; διαφορετικού μήκους κοστίζουν αλλιώς, και στο PLACE το σύνολο του
        ; al_plan αλλάζει με τους διαδρόμους του θόλου. Το χαμηλό byte φτάνει:
        ; δύο σύνολα του ίδιου αντικειμένου διαφέρουν κατά 6k, k <= 48, και
        ; το 256 δεν διαιρείται με το 6. Μετά το uis_aff, που το ξαναμετρά.
        ld      a,(cr_metal)
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
        ld      a,3
        call    hud_go
        ld      a,(ui_state)
        or      a
        jr      nz,uip_notlook
        ld      hl,t_look
        call    hud_text7
        ld      b,35-33                 ; ως τον δείκτη ταχύτητας (uip_spd)
uip_bl4:                                ; B κενά, και η σειρά 4 (και το SLOT)
        jp      uip_blr4
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
        call    hud_space
        ld      a,(sl_pick)
        add     a,'1'
        call    hud_char
        ld      b,40-16
        jr      uip_bl4
        endif
uip_item:
        ; Το κόστος που δείχνεται είναι ΟΛΗΣ της διαδρομής όταν υπάρχει
        ; διαδρομή: ο κατάλογος γράφει την τιμή ενός πλακιδίου διαδρόμου, και
        ; το μήκος δεν το διαλέγει ο παίκτης αλλά η γεωμετρία (§9.4).
        ; ΤΑ ΔΥΟ ΚΟΣΤΗ ΣΤΗ ΣΤΟΙΒΑ ως τη σειρά τους, πιο κάτω (βήμα 103: ως τότε
        ; δύο μεταβλητές): πρώτα το βιοπλαστικό, από πάνω το μέταλλο.
        ld      a,(ui_state)
        cp      UI_PLACE
        jr      z,uipi_tot              ; το σύνολο του al_plan (βήμα 85)
        cp      UI_LINK
        jr      nz,uipi_bd
        ld      a,(cr_n)
        or      a
        jr      z,uipi_bd
        call    cr_cost
uipi_tot:
        ld      hl,(cr_biop)
        push    hl
        ld      hl,(cr_metal)
        jr      uipi_go
uipi_bd:
        ld      hl,(bd_metal)           ; L = μέταλλο, H = βιοπλαστικό
        ld      e,h
        ld      d,0
        push    de
        ld      h,d
uipi_go:
        push    hl
        ld      a,'<'
        call    hud_char
        call    hud_space
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
        ld      b,13                    ; «< » και δέκα στήλες: το γράμμα στη 13η
        call    hud_to                  ; (βήμα 119: τα ονόματα χωρίς κενά)
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
uipi_bl:                                ; δωμάτια 10 συν το γράμμα μεγέθους
        call    hud_blank               ; (και το fit_name, με B = 5)
uipi_arrow:
        call    hud_space
        ld      a,'>'
        call    hud_char
        ld      b,2
        call    hud_blank
        ld      hl,t_fe
        call    hud_text7
        pop     hl                      ; το μέταλλο (uipi_go)
        ld      b,3
        call    hud_num
        ld      b,2
        call    hud_blank
        ld      hl,t_bi
        call    hud_text7
        pop     hl                      ; το βιοπλαστικό
        ld      b,3
        call    hud_num
        ld      b,40-34
uip_blr4:                               ; B κενά, και η σειρά 4 (LOOK, SLOT)
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
        ; Το MENU με το uip_say, που σβήνει ως τη στήλη 40 ό,τι μήκος κι αν
        ; έχει το κείμενο (t_keys 20 χαρακτήρες, t_keysr 22).
        ld      hl,t_keys
        ld      a,(bd_kind)
        or      a                       ; σε θόλο, το πάνω-κάτω κάνει κάτι
        jr      nz,uip_say
        ld      hl,t_keysr
        jr      uip_say
uip_blk:
        call    hud_blank
        jr      uip_spd
uip_st:
        ld      a,(ui_bad)
        or      a
        jr      nz,uip_blocked
        call    al_afford
        jr      uip_aff
uip_blocked:
        ; ΓΙΑΤΙ ΟΧΙ, ΟΧΙ ΜΟΝΟ ΟΧΙ. Οταν φταίνε τα tiles, το φάντασμα τα δείχνει
        ; ένα προς ένα με κόκκινο· όταν λείπει το υλικό της δομής (§6.5) δεν
        ; υπάρχει κακό tile να δειχτεί, και ένα σκέτο BLOCKED πάνω σε καθαρό
        ; έδαφος διαβάζεται ως σφάλμα του παιχνιδιού. Το κείμενο από το
        ; uip_nres, με δείκτη το bd_nres (0-5).
        ld      a,(bd_nres)
        add     a,a
        ld      hl,uip_nres
        call    rm_word                 ; src/rooms.asm
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
uip_aff:                                ; NZ: δεν φτάνουν (και το uip_st)
        ld      hl,t_poor
        jr      nz,uip_say
        ld      hl,t_ok
        ld      a,(bd_half)             ; ορυχείο εκτός φλέβας (βήμα 123)
        or      a
        jr      z,uip_say
        ld      hl,t_half
uip_say:
        call    hud_text7
        ld      b,40                    ; ως το τέλος, όσο κι αν είναι: από το
        call    hud_to                  ; βήμα 91 τα κείμενα δεν έχουν κενά στο
        ; fall through                  ; τέλος (ως τότε 20 στήλες ακριβώς)

; uip_spd — η ταχύτητα, στις πέντε τελευταίες στήλες της σειράς 3. Είναι το
; μόνο σημείο του HUD που γράφεται από τα δεξιά: οι σειρές 0-2 είναι γεμάτες
; ως το τελευταίο κελί (§9.2) και η σειρά 3 τελειώνει με κενά σε κάθε
; κατάσταση.
uip_spd:
        ld      a,3
        ld      c,35
        call    hud_goc
        ld      a,(ui_spd)              ; 0, 1, 2, 4 -> 0, 1, 2, 3: μόνο το 4
        cp      4                       ; βγαίνει χωρίς CY, και το adc #FF του
        adc     a,#FF                   ; αφαιρεί ένα
        ld      c,a
        add     a,a
        add     a,c
        add     a,a                     ; x6: τα τέσσερα κείμενα στη σειρά, έξι
        ld      hl,t_pause              ; bytes το καθένα (src/uitext.asm)
        call    ob_addu
        jp      hud_text7

; uip_blocked — ανά bd_nres: 0 τα tiles, 1 νερό, (2 φλέβα ως το βήμα 123), 3 κανένα κτίσμα σε
; απόσταση (βήμα 85), 4 ο δρόμος κομμένος, 5 κανένα σχήμα διαδρόμου (βήμα 86).
uip_nres:   dw t_block, t_nowat, t_block, t_far, t_path, t_nofit  ; το 2 δεν βγαίνει από το βήμα 123

; uis_aff — A = φτάνουν τα υλικά; του διαδρόμου στο LINK, του καταλόγου αλλού.
uis_aff:
        ld      a,(ui_state)
        cp      UI_PLACE
        jp      z,al_afford
        cp      UI_LINK
        jp      nz,bd_afford
        jp      cr_afford

; ui_dirty — «οι σειρές 3-4 δεν λένε πια αυτό που νομίζω».
ui_dirty:
        ld      a,255
        ld      (uip_sig),a
        ret

; ui_hudall — πλήρες HUD· σβήνει τις σειρές 3-4, άρα ακυρώνει την υπογραφή.
ui_hudall:
        call    hud_draw
ui_dpan:                                ; και το ui_speed
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
uid_tx:     db 0
uid_ty:     db 0
; Το ui_hold ζει ΕΞΩ από το ifdef του δίσκου: το ui_panel το διαβάζει πάντα,
; και το tests/uitest.asm χτίζεται χωρίς μηνύματα δίσκου. (Το όνομα δεν είναι
; UI_HOLD γιατί ο rasm δεν ξεχωρίζει ετικέτα από alias.)
uip_szc:    db "SML"
ui_hold:    db 0
uip_sig:    defs UIP_NSIG, 255
        assert  uip_sig == ui_hold + 1  ; ui_ask, uip_start: inc hl
cur_hx:     db 0
cur_hy:     db 0

        assert  cam_ty == cam_tx + 1 && cur_hy == cur_hx + 1
        assert  ui_ty == ui_tx + 1 && ui_h == ui_w + 1 && uid_ty == uid_tx + 1
        assert  ui_sel == ui_state + 1
        assert  gh_bh == gh_bw + 1 && UI_LOOK == 0
        assert  A_HOME == 8 && A_SPD1 >= 8 && A_SPD4 < 16

; crr_conns — οι δύο αρμοί του διαδρόμου που μόλις μπήκε, στη λίστα (DK_CONN),
; για το cr_redraw: πέφτουν στους δακτυλίους, έξω από το ορθογώνιο και τις
; σειρές του διαδρόμου. Ο a στην κατεύθυνση του πρώτου τρεξίματος, ο b στην
; αντίθετη του ΤΕΛΕΥΤΑΙΟΥ, όπως το jt_mark. Ενας αρμός δεν πέφτει πάνω σε θέση
; δακτυλίου, μηχανή ή εικονίδιο (tests/test_object.py), οπότε γραμμένος μόνος
; του πάνω από το κέλυφος δίνει ό,τι και το πλήρες πέρασμα. Εδώ και όχι στο
; route.asm: η τράπεζα 2 είχε 10 bytes.
crr_conns:
        ld      a,(cr_from)
        ld      b,a
        ld      a,(cr_d0)
        ld      c,a
        ld      a,DK_CONN
        call    dirty_push
        ld      hl,jtb_cc               ; ο b (src/bend.asm, βήμα 97)
        ld      de,dt_end               ; πίσω με την 1
        jp      jt_b5c

; cr_stampx — το cr_stamp, και τα tiles του ΜΙΣΟΥ ΠΛΑΤΟΥΣ (βήμα 96). Ο αξονικός
; διάδρομος στο κέντρο του θόλου πάει μισό πλάτος πίσω: 1 byte στη στήλη
; αριστερά από τα tiles του ο κάθετος, 4 γραμμές στη σειρά πάνω ο οριζόντιος,
; όταν ο άξονας πέφτει σε όριο tile (ζυγό cx ή cy σε μισά tiles, ο κανόνας του
; crr_half). Και αυτά σφραγίζονται, όσα είναι ελεύθερα: ό,τι ξαναζωγραφίζει
; μόνο έδαφος όπου η κατοχή λέει «άδειο» (dh_tile, οι φιγούρες έξω) έσβηνε
; αλλιώς τη λωρίδα του διαδρόμου (tests/test_meteor.py, 32 bytes). Τα πιασμένα
; μένουν όπως είναι: σε θόλο, δομή ή διάδρομο το πέρασμα αντικειμένων γίνεται
; ήδη, και ένα μονοπάτι (κατοχή 2) μένει μονοπάτι. Ο έλεγχος της διαδρομής
; (cr_check) δεν τα κοιτάζει.
;
; ΣΤΟ ΙΔΙΟ ΠΕΡΑΣΜΑ με τη σφραγίδα, και φθηνότερα από το cr_cb_stp: το crx_cb
; βρίσκει τη διεύθυνση του tile μόνο του, με τα x + 64 και y + 64 που μόλις
; έλεγξε για τα όρια, και ο γείτονας είναι το HL - 1 ή το HL - 128. Ενα
; δεύτερο πέρασμα της διαδρομής έκανε το cr_commit ως 1,9 ms πιο αργό από το
; βήμα 72 (tests/test_corridor.py). Σε στροφή το τρέξιμο 0 περνά μόνο με τη
; σφραγίδα (cr_n = 1 για λίγο: το cr_walk σταματά εκεί), και το 1 με τον
; γείτονα, από ένα crw_base — το ίδιο tile της στροφής ξαναπερνά, και η
; σφραγίδα του δεύτερη φορά δεν αλλάζει τίποτα.
cr_stampx:
        ld      a,(cr_n)
        cp      2
        jr      nc,crx_bend
        ld      a,(cr_d0)
        call    crx_sel
        jp      crw_b4                  ; src/route.asm: η διαδρομή με την 4 μέσα
crx_bend:
        ld      hl,cr_n
        dec     (hl)
        ld      a,1                     ; διαγώνιος: μόνο η σφραγίδα
        call    crx_sel
        call    crw_b4                  ; το τρέξιμο 0
        ld      hl,cr_n
        inc     (hl)
        ld      a,(cr_d1)
        call    crx_sel
        ld      bc,GA_PORT + PAGE_B4
        out     (c),c
        call    crw_base
        call    cr_walk1                ; το τρέξιμο 1, η στροφή
        jp      uid_out                 ; πίσω η 1
; crx_sel — A = η κατεύθυνση του τρεξίματος. Στήνει το crx_cb: ret στο
; crx_mode (μόνο η σφραγίδα), ή το ld de του γείτονα (-1 ή -128). HL = crx_cb,
; και (cr_cb) το ίδιο.
crx_sel:
        ld      b,#C9                   ; ret
        rra
        jr      c,crx_set               ; διαγώνιος (bit 0)
        ld      hl,cr_tx                ; ο άξονας του b, όπως στο crr_half
        ld      de,-1                   ; αριστερά
        and     1                       ; το bit 1: e, w = 2, 6 οριζόντιος· n, s κάθετος
        jr      z,crx_x                 ; κάθετος: το x
        inc     hl                      ; cr_ty
        ld      de,-128                 ; πάνω: μία σειρά του κόσμου
crx_x:
        ld      a,(hl)
        sra     a                       ; το tile του άξονα, και το bit 0 στο CY
        jr      c,crx_set               ; μονό: όλος μέσα στα tiles του
        cp      -64
        jr      z,crx_set               ; ο γείτονας θα ήταν έξω από τον κόσμο
        ld      b,#11                   ; ld de,nn
        ld      (crx_mode + 1),de
crx_set:
        ld      a,b
        ld      (crx_mode),a
        ld      hl,crx_cb
        ld      (cr_cb),hl
        ret
; crx_cb — B = x, C = y ενός tile της διαδρομής: κατοχή 1, και (crx_sel) στον
; γείτονα του μισού πλάτους, αν είναι ελεύθερος.
crx_cb:
        ld      a,c
        add     a,64
        ld      e,a                     ; y + 64
        ld      a,b
        add     a,64
        ld      l,a                     ; x + 64
        or      e
        ret     m                       ; έξω από τον κόσμο
        ld      a,e                     ; το tile_addr, με τα ίδια· το or
        rra                             ; μηδένισε το carry
        jr      nc,crx_ev
        set     7,l
crx_ev:
        add     a,WORLD_BASE >> 8
        ld      h,a
        set     4,(hl)                  ; W_OCC_STRUCT
crx_mode:
        ld      de,-1                   ; ή ret: μόνο η σφραγίδα (crx_sel)
        add     hl,de
        ld      a,(hl)
        and     W_OCC_MASK
        ret     nz                      ; πιασμένο: μένει όπως είναι
        set     4,(hl)
        ret
