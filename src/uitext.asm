; uitext.asm — ΟΛΑ τα κείμενα του παιχνιδιού, στην ΤΡΑΠΕΖΑ 7.
;
; Η τράπεζα 0 τελείωσε: 37 ελεύθερα bytes στο βήμα 22. Το §4.2 κρατούσε από την
; αρχή 1.024 bytes «text» στην τράπεζα 7 ακριβώς γι' αυτό, και εδώ
; εξαργυρώνονται — 496 bytes κειμένου φεύγουν από την τράπεζα 0.
;
; ΓΙΑΤΙ ΜΟΝΟ ΚΕΙΜΕΝΑ. Η τράπεζα 7 φαίνεται στο παράθυρο #4000-#7FFF, δηλαδή
; μόνο σελιδοποιημένη. Κώδικας δεν μπορεί να ζήσει εκεί: το πρώτο πράγμα που θα
; έκανε — να σελιδοποιήσει την τράπεζα 4 για τον κόσμο ή την 6 για τους
; πράκτορες — θα έσβηνε τον ίδιο του τον εαυτό. Δεδομένα ΜΟΝΟ ΓΙΑ ΑΝΑΓΝΩΣΗ, από
; κώδικα που δεν χρειάζεται άλλη τράπεζα όσο διαβάζει: το hud_text7 ανοίγει την
; 7, τυπώνει, ξαναβάζει την 1. Η ΜΙΑ ΕΞΑΙΡΕΣΗ, από το βήμα 170, είναι κώδικας που
; δεν σελιδοποιεί ποτέ: οι δομές (src/st7.asm), μετά τα κείμενα και στο ίδιο
; αρχείο του δίσκου.
;
; ΟΙ ΔΥΟ ΔΙΕΥΘΥΝΣΕΙΣ. Μέσα στο bankset 1 του rasm η τράπεζα 7 κάθεται στο
; #C000· σελιδοποιημένη στο παιχνίδι κάθεται στο #4000. Τα bytes γράφονται στην
; πρώτη και οι ετικέτες που βλέπει ο κώδικας δείχνουν στη δεύτερη. (Το `bank 7`
; του rasm θα τα έδινε κατευθείαν σωστά, αλλά δεν συνδυάζεται με το `bankset 1`
; που στήνει τις τράπεζες 4-7 πιο πάνω.)

TEXT_MAX    equ 3200                    ; η δέσμευση του §4.2, με τον κώδικα της 7 από το βήμα 170 και τις σελίδες του tutorial από το 175 (2.578 ως το βήμα 175, 2.485 ως το βήμα 170, 2.148 ως το βήμα 169, 2.138 ως το βήμα 110, 2.120 ως το βήμα 100, 2.100 ως το βήμα 89, 2.080 ως το 87, 2.064 ως το 85, 2.048 ως το 84, 1.280 ως το 83,
                                        ; 1.024 ως το 79)
TEXT_IMG    equ #C000 + G_text - #4000

        org     TEXT_IMG

x_txt_o2:     db "O2 ",0
x_txt_pwr:    db "PWR",0
x_txt_h2o:    db "H2O",0
x_txt_fod:    db "FOD",0
x_txt_sol:    db " SOL",0
x_txt_day:    db "DAY",0
x_txt_night:  db "NGT",0
x_txt_ok:     db "ALL SYSTEMS OK",0
x_txt_nopwr:  db "NO POWER",0
x_txt_shed:   db "LOW POWER",0
x_txt_noo2:   db "NO OXYGEN",0
x_txt_storm:  db "SANDSTORM",0
x_txt_meteor: db "METEOR SHOWER",0
x_txt_nofood: db "LOW ON FOOD",0
x_txt_nowater:db "LOW ON WATER",0
x_txt_lost:   db "COLONY LOST",0
x_txt_noeng:  db "NO ENGINEER",0   ; βήμα 88
x_txt_suit:   db "SUIT AIR LOW",0   ; βήμα 90
x_txt_mer:    db "MERCHANT LANDED",0   ; βήμα 93: χωρίς κενά στο τέλος, όπως όλα από το 93 (hd_say)
x_txt_foe:    db "INTRUDERS",0         ; βήμα 111
x_txt_full:   db "STORAGE FULL",0      ; βήμα 122
x_txt_brk:    db "BROKEN",0            ; βήμα 119: και το όνομα της μηχανής (hd_named)
x_t_saving:   db "SAVING TO DISC...",0
        ; Το κείμενο, ένα κενό και επτά γράμματα χωρούν στις 19 στήλες: ένα 20ό
        ; θα έπεφτε στο δεξί μισό της T1, και το hud_to μετά θα έγραφε 254 κενά.
        assert  (x_txt_suit - 1 - x_txt_noeng) + 1 + 7 <= 19
        assert  (x_t_saving - 1 - x_txt_brk) + 1 + 7 <= 19
x_t_saved:    db "SAVED TO SLOT 1",0
x_t_loading:  db "LOADING FROM DISC...",0
x_t_loaded:   db "LOADED FROM SLOT 1",0
x_t_dskerr:   db "DISC ERROR",0
x_t_empty:    db "NOTHING IN SLOT 1",0
x_t_slsave:   db "SAVE TO SLOT  ",0
x_t_slload:   db "LOAD FROM SLOT",0
x_t_slkeys:   db "LEFT RIGHT FIRE ESC",0
x_t_pause:    db "PAUSE",0
x_t_x1:       db "  x1 ",0
x_t_x2:       db "  x2 ",0
x_t_x4:       db "  x4 ",0
x_t_look:     db "SPACE=MENU I=INFO FIRE=FIT C=SHIP",0
x_t_keys:     db "FIRE=PLACE ESC=BACK ",0
        ; Το tutorial γράφει εδώ τις γραμμές του (βήμα 149, src/tutor.asm): 32
        ; χαρακτήρες από τις τρύπες και ο 33ος, κενό ή το «P» αυτού εδώ.
        assert  x_t_keys - x_t_look == 34
x_t_ok:       db "READY  FIRE TO BUILD",0
x_t_block:    db "BLOCKED",0
x_t_poor:     db "NOT ENOUGH MATERIAL",0
x_t_ln1:      db "PICK THE FIRST DOME",0
x_t_ln2:      db "NO ROUTE FROM THERE",0
x_t_far:      db "TOO FAR",0       ; >= 64 tiles (βήμα 81)· ή > 12 (βήμα 85)
x_t_path:     db "PATH BLOCKED",0       ; βήμα 85, src/link.asm
x_t_nofit:    db "NO CORRIDOR FITS",0       ; βήμα 86: η ζώνη «σχεδόν διαγώνιο»
x_t_nowat:    db "NEEDS WATER NEARBY",0
x_t_half:     db "NO VEIN  HALF ORE",0  ; ως το βήμα 122 «NEEDS AN ORE VEIN»
x_t_fe:       db "FE",0
x_t_bi:       db "BI",0

; (Τα δωμάτια του καταλόγου ζούσαν εδώ ως το βήμα 118, δέκα χαρακτήρες το
; καθένα με κενά: το γράμμα μεγέθους μπαίνει μετά. Είναι οι ίδιες λέξεις με τα
; κουμπιά της βοήθειας, πιο κάτω, και δείχνουν πια εκεί· τη στήλη του γράμματος
; τη βρίσκει το hud_to (src/ui.asm). 110 bytes, για το BROKEN και ό,τι έρθει.)
x_t_keysr:    db "FIRE=PLACE  UP/DN=ROOM",0
x_t_ship:     db "COLONIST SHIP CALLED",0
x_t_shipno:   db "A SHIP IS ALREADY DUE",0
x_t_noctl:    db "NEED A CONTROL ROOM",0
x_t_nopad:    db "NEED A LANDING PAD",0

; Η γραμμή του πλοίου (src/crew.asm, βήμα 91): τέσσερα bytes το όνομα, με τη
; σειρά των ρόλων 0-4 — το cw_panel τα διαβάζει στη σειρά.
x_t_cw_names: db "WRK",0, "ENG",0, "BIO",0, "MED",0, "GRD",0
x_t_cw_keys:  db "SHIP UP/DN=10% FIRE=CALL ESC=BACK",0

; Η γραμμή του εμπόρου (src/lines.asm, βήμα 93).
x_t_tr_take:  db " TAKE ",0
x_t_tr_give:  db " GIVE ",0
x_t_tr_fire:  db " FIRE=DEAL",0
x_t_tr_ship:  db " SHIP ",0
x_t_tr_have:  db " HAVE ",0
x_t_deal:     db "TRADE DONE",0

; Ο εξοπλισμός (src/fit.asm). ΟΚΤΩ bytes το όνομα, συνεχόμενα και με τη σειρά
; του MACH_TYPES και μετά των κωδικών 250-255: το fit_name τα βρίσκει με x8.
x_t_f_names:  db "OXYGEN ",0, "METAL  ",0, "PLASTIC",0, "WEAPONS",0
              db "CHIPS  ",0, "ROBOTS ",0, "MEALS  ",0, "SPARES ",0
              db "DRUGS  ",0, "MEAT   ",0, "BEDS   ",0, "CABINET",0
              db "STARCH ",0, "VEGGIES",0, "HERBS  ",0, "TREE   ",0
              db "MIXED  ",0, "EMPTY  ",0
              db "ORE    ",0        ; 18: μόνο για τη γραμμή του εμπόρου (βήμα 93)
              db "COINS  ",0        ; 19: κι αυτά (βήμα 135)
x_t_f_slot:   db "SLOT ",0
x_t_f_keys:   db "UP/DN=PICK FIRE=FIT SPACE=ALL",0

; Τι έχει κάτω ο κέρσορας (src/info.asm, βήμα 79). Τα εδάφη ΕΝΤΕΚΑ bytes το
; καθένα, με τη σειρά του W_*: το in_panel τα βρίσκει με x11.
x_t_i_none:   db "NOTHING BUILT",0
x_t_i_site:   db "SITE  ",0
x_t_i_act:    db "ACTIVE",0
x_t_i_hp:     db "HP ",0
x_t_i_cls:    db "GROUND    ",0, "DUST      ",0, "ROCK      ",0, "MOUNTAIN  ",0
              db "WATER     ",0, "DEEP WATER",0, "CRATER    ",0, "FOUNDATION",0
x_t_i_ore:    db " ORE VEIN",0

; Τα κουμπιά (src/bar.asm, βήμα 84): για ΚΑΘΕ κουμπί, με τη σειρά του αριθμού
; του (tools/buttons.py), το όνομα και μία γραμμή για την οθόνη βοήθειας.
; Ως 12 και 20 χαρακτήρες. Το bt_text τα βρίσκει μετρώντας μηδενικά: δεν
; υπάρχει πίνακας δεικτών, και κάθε κείμενο είναι ΔΥΟ συμβολοσειρές.
; (Ως το βήμα 83 εδώ ζούσαν τα ονόματα του μενού ενεργειών, επτά bytes το
; καθένα· τα λένε πια αυτά.)
x_t_help:     db "DOMES",0, "LIVE AND WORK INSIDE",0
              db "SMALL DOME",0, "4X4, ANY ROOM",0
              db "MEDIUM DOME",0, "6X6, NO OXYGEN",0
              db "LARGE DOME",0, "8X8, NO OXYGEN",0
x_t_r_oxy:    db "OXYGEN",0
              db "AIR FOR THE COLONY",0
x_t_r_can:    db "CANTEEN",0
              db "COOKS MEALS",0
x_t_r_qrt:    db "QUARTERS",0
              db "BEDS TO SLEEP IN",0
x_t_r_grn:    db "GREENHOUSE",0
              db "GROWS PLANTS",0
x_t_r_fac:    db "FACTORY",0
              db "METAL AND PARTS",0
x_t_r_lab:    db "LAB",0
              db "MEAT AND CHIPS",0
x_t_r_med:    db "MEDBAY",0
              db "HEALS THE SICK",0
x_t_r_ctl:    db "CONTROL",0
              db "MORE COLONISTS",0
x_t_r_sto:    db "STORAGE",0
              db "ROOM FOR MORE GOODS",0
x_t_r_lng:    db "LOUNGE",0
              db "KEEPS MORALE UP",0
              db "CORRIDOR",0, "LINKS TWO DOMES",0
              db "POWER",0, "MAKE AND STORE POWER",0
              db "SOLAR PANEL",0, "POWER BY DAY",0
              db "WIND TURBINE",0, "POWER FROM WIND",0
              db "COLLECTOR",0, "STORES POWER",0
              db "RESOURCES",0, "WATER AND ORE",0
              db "EXTRACTOR",0, "WATER FROM GROUND",0
              db "MINE",0, "ORE, BEST ON A VEIN",0     ; βήμα 123: «ORE FROM A VEIN»
              db "TRANSPORT",0, "COMING AND GOING",0
              db "AIRLOCK",0, "WAY IN AND OUT",0
              db "LANDING PAD",0, "SHIPS LAND HERE",0
              db "SHIP",0, "CALL NEW COLONISTS",0
              db "TRADE",0, "UP TAKES, DOWN GIVES",0      ; βήμα 93
              db "MANAGE",0, "INFO, DISC, VIEW",0
              db "INFO",0, "WHAT IS HERE",0
              db "FIT",0, "MACHINES IN A DOME",0
              db "SAVE",0, "SAVE TO DISC",0
              db "LOAD",0, "LOAD FROM DISC",0
              db "CENTRE",0, "BACK TO THE MIDDLE",0
              db "DEMOLISH",0, "MATERIAL BACK",0       ; βήμα 101
              db "HELP",0, "THIS SCREEN",0
x_t_help_end:
x_t_a_keys:   db "FIRE=GO ESC=BACK",0
x_t_hfoot:    db "THE LETTER ON A BUTTON IS ITS KEY.   PRESS ANY KEY TO GO BACK",0

zz_text_end:
        ; ΚΑΙ Ο ΚΩΔΙΚΑΣ ΤΗΣ 7 (βήμα 170, src/st7.asm), αμέσως μετά και στο ίδιο
        ; αρχείο του δίσκου: οι ετικέτες του στο παράθυρο (#4000-#7FFF), τα bytes
        ; του εδώ, όπως του b6code (src/main.asm).
        org     zz_text_end - TEXT_IMG + G_text, zz_text_end
        include "st7.asm"
        ifdef HAS_DISC
        ; ΚΑΙ ΟΙ ΣΕΛΙΔΕΣ ΤΟΥ TUTORIAL (βήμα 175, src/tpage.asm): κώδικας που δεν
        ; σελιδοποιεί, όπως το st7. Μόνο στο παιχνίδι: θέλει τον οδηγό του δίσκου.
        include "tpage.asm"
        endif
zz_st7_end:

; --- οι σελιδοποιημένες διευθύνσεις, αυτές που βλέπει ο κώδικας ---
txt_o2    equ x_txt_o2 - TEXT_IMG + G_text
txt_pwr   equ x_txt_pwr - TEXT_IMG + G_text
txt_h2o   equ x_txt_h2o - TEXT_IMG + G_text
txt_fod   equ x_txt_fod - TEXT_IMG + G_text
txt_sol   equ x_txt_sol - TEXT_IMG + G_text
txt_day   equ x_txt_day - TEXT_IMG + G_text
txt_night equ x_txt_night - TEXT_IMG + G_text
txt_noeng equ x_txt_noeng - TEXT_IMG + G_text
txt_suit  equ x_txt_suit - TEXT_IMG + G_text
txt_ok    equ x_txt_ok - TEXT_IMG + G_text
txt_nopwr equ x_txt_nopwr - TEXT_IMG + G_text
txt_shed  equ x_txt_shed - TEXT_IMG + G_text
txt_noo2  equ x_txt_noo2 - TEXT_IMG + G_text
txt_storm equ x_txt_storm - TEXT_IMG + G_text
txt_full  equ x_txt_full - TEXT_IMG + G_text
txt_meteor equ x_txt_meteor - TEXT_IMG + G_text
txt_lost  equ x_txt_lost - TEXT_IMG + G_text
t_saving  equ x_t_saving - TEXT_IMG + G_text
t_saved   equ x_t_saved - TEXT_IMG + G_text
t_loading equ x_t_loading - TEXT_IMG + G_text
t_loaded  equ x_t_loaded - TEXT_IMG + G_text
t_dskerr  equ x_t_dskerr - TEXT_IMG + G_text
t_empty   equ x_t_empty - TEXT_IMG + G_text
t_slsave  equ x_t_slsave - TEXT_IMG + G_text
t_slload  equ x_t_slload - TEXT_IMG + G_text
t_slkeys  equ x_t_slkeys - TEXT_IMG + G_text
t_pause   equ x_t_pause - TEXT_IMG + G_text
t_x1      equ x_t_x1 - TEXT_IMG + G_text
t_x2      equ x_t_x2 - TEXT_IMG + G_text
t_x4      equ x_t_x4 - TEXT_IMG + G_text
t_look    equ x_t_look - TEXT_IMG + G_text
t_keys    equ x_t_keys - TEXT_IMG + G_text
t_ok      equ x_t_ok - TEXT_IMG + G_text
txt_nofood  equ x_txt_nofood - TEXT_IMG + G_text
txt_nowater equ x_txt_nowater - TEXT_IMG + G_text
t_block   equ x_t_block - TEXT_IMG + G_text
t_poor    equ x_t_poor - TEXT_IMG + G_text
t_ln1     equ x_t_ln1 - TEXT_IMG + G_text
t_ln2     equ x_t_ln2 - TEXT_IMG + G_text
t_far     equ x_t_far - TEXT_IMG + G_text
t_path    equ x_t_path - TEXT_IMG + G_text
t_nofit   equ x_t_nofit - TEXT_IMG + G_text
t_nowat   equ x_t_nowat - TEXT_IMG + G_text
t_half    equ x_t_half - TEXT_IMG + G_text
t_fe      equ x_t_fe - TEXT_IMG + G_text
t_bi      equ x_t_bi - TEXT_IMG + G_text
t_r_oxy   equ x_t_r_oxy - TEXT_IMG + G_text
t_r_can   equ x_t_r_can - TEXT_IMG + G_text
t_r_qrt   equ x_t_r_qrt - TEXT_IMG + G_text
t_r_grn   equ x_t_r_grn - TEXT_IMG + G_text
t_r_fac   equ x_t_r_fac - TEXT_IMG + G_text
t_r_lab   equ x_t_r_lab - TEXT_IMG + G_text
t_r_med   equ x_t_r_med - TEXT_IMG + G_text
t_r_ctl   equ x_t_r_ctl - TEXT_IMG + G_text
t_r_sto   equ x_t_r_sto - TEXT_IMG + G_text
t_r_lng   equ x_t_r_lng - TEXT_IMG + G_text
t_keysr   equ x_t_keysr - TEXT_IMG + G_text
t_ship    equ x_t_ship - TEXT_IMG + G_text
t_cw_names equ x_t_cw_names - TEXT_IMG + G_text
t_cw_keys equ x_t_cw_keys - TEXT_IMG + G_text
t_shipno  equ x_t_shipno - TEXT_IMG + G_text
t_noctl   equ x_t_noctl - TEXT_IMG + G_text
t_nopad   equ x_t_nopad - TEXT_IMG + G_text
t_f_names equ x_t_f_names - TEXT_IMG + G_text
t_f_slot  equ x_t_f_slot - TEXT_IMG + G_text
t_f_keys  equ x_t_f_keys - TEXT_IMG + G_text
t_i_none  equ x_t_i_none - TEXT_IMG + G_text
t_i_site  equ x_t_i_site - TEXT_IMG + G_text
t_i_act   equ x_t_i_act - TEXT_IMG + G_text
t_i_hp    equ x_t_i_hp - TEXT_IMG + G_text
t_i_cls   equ x_t_i_cls - TEXT_IMG + G_text
t_i_ore   equ x_t_i_ore - TEXT_IMG + G_text
t_help    equ x_t_help - TEXT_IMG + G_text
t_a_keys  equ x_t_a_keys - TEXT_IMG + G_text
t_hfoot   equ x_t_hfoot - TEXT_IMG + G_text
txt_mer   equ x_txt_mer - TEXT_IMG + G_text
txt_foe   equ x_txt_foe - TEXT_IMG + G_text
txt_brk   equ x_txt_brk - TEXT_IMG + G_text
t_tr_take equ x_t_tr_take - TEXT_IMG + G_text
t_tr_give equ x_t_tr_give - TEXT_IMG + G_text
t_tr_fire equ x_t_tr_fire - TEXT_IMG + G_text
t_tr_ship equ x_t_tr_ship - TEXT_IMG + G_text
t_tr_have equ x_t_tr_have - TEXT_IMG + G_text
t_deal    equ x_t_deal - TEXT_IMG + G_text

        ; Το κενό είναι 1.280 bytes και τελειώνει εκεί που αρχίζει το επόμενο
        ; πράγμα της τράπεζας 7. Χωρίς αυτόν τον έλεγχο, ένα κείμενο παραπάνω θα
        ; έγραφε πάνω σε δεδομένα — αθόρυβα, και μόνο στην οθόνη θα φαινόταν.
        assert  zz_st7_end - G_text <= TEXT_MAX         ; τα κείμενα και ο κώδικας (βήμα 170)
        ; Και το TEXT_MAX ΣΥΜΦΩΝΕΙ με την τρύπα του tools/pack.py, που βάζει τη
        ; γραμματοσειρά αμέσως μετά: αλλιώς τα κείμενα γράφουν πάνω της.
        assert  G_text + TEXT_MAX <= G_font_m1
        assert  x_t_f_slot - x_t_f_names == 20 * 8   ; fit_name, tr_panel: x8
        assert  x_t_x1 - x_t_pause == 6 && x_t_x2 - x_t_pause == 12 && x_t_x4 - x_t_pause == 18  ; uip_spd: x6
        assert  x_t_i_ore - x_t_i_cls == 8 * 11      ; in_panel: x11

        ; ΚΑΙ ΣΤΟΝ ΔΙΣΚΟ: η BANK7.BIN φτιάχνεται από το tools/pack.py, που δεν
        ; ξέρει τι λέει το παιχνίδι. Τα κείμενα πάνε ως δικό τους αρχείο και ο
        ; φορτωτής τα ρίχνει πάνω από το δεσμευμένο κενό.
        save    "../build/text.bin", TEXT_IMG, zz_st7_end - G_text
