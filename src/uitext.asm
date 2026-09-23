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
; 7, τυπώνει, ξαναβάζει την 1.
;
; ΟΙ ΔΥΟ ΔΙΕΥΘΥΝΣΕΙΣ. Μέσα στο bankset 1 του rasm η τράπεζα 7 κάθεται στο
; #C000· σελιδοποιημένη στο παιχνίδι κάθεται στο #4000. Τα bytes γράφονται στην
; πρώτη και οι ετικέτες που βλέπει ο κώδικας δείχνουν στη δεύτερη. (Το `bank 7`
; του rasm θα τα έδινε κατευθείαν σωστά, αλλά δεν συνδυάζεται με το `bankset 1`
; που στήνει τις τράπεζες 4-7 πιο πάνω.)

TEXT_MAX    equ 1024                    ; η δέσμευση του §4.2
TEXT_IMG    equ #C000 + G_text - #4000

        org     TEXT_IMG

x_txt_o2:     db "O2 ",0
x_txt_pwr:    db "PWR",0
x_txt_h2o:    db "H2O",0
x_txt_fod:    db "FOD",0
x_txt_pop:    db "POP ",0
x_txt_sol:    db " SOL",0
x_txt_day:    db "DAY",0
x_txt_night:  db "NGT",0
x_txt_ok:     db "ALL SYSTEMS OK     ",0
x_txt_nopwr:  db "NO POWER           ",0
x_txt_noo2:   db "NO OXYGEN          ",0
x_txt_storm:  db "SANDSTORM          ",0
x_txt_lost:   db "COLONY LOST        ",0
x_t_saving:   db "SAVING TO DISC...   ",0
x_t_saved:    db "SAVED TO SLOT 1     ",0
x_t_loading:  db "LOADING FROM DISC...",0
x_t_loaded:   db "LOADED FROM SLOT 1  ",0
x_t_dskerr:   db "DISC ERROR          ",0
x_t_empty:    db "NOTHING IN SLOT 1   ",0
x_t_slsave:   db "SAVE TO SLOT  ",0
x_t_slload:   db "LOAD FROM SLOT",0
x_t_slkeys:   db "LEFT RIGHT FIRE ESC ",0
x_t_pause:    db "PAUSE",0
x_t_x1:       db "  x1 ",0
x_t_x2:       db "  x2 ",0
x_t_x4:       db "  x4 ",0
x_t_look:     db "LOOK  SPACE=BUILD  ",0
x_t_keys:     db "FIRE=PLACE ESC=BACK ",0
x_t_ok:       db "READY  FIRE TO BUILD",0
x_t_block:    db "BLOCKED             ",0
x_t_poor:     db "NOT ENOUGH MATERIAL ",0
x_t_ln1:      db "PICK THE FIRST DOME ",0
x_t_ln2:      db "NO ROUTE FROM THERE ",0
x_t_fe:       db "FE",0
x_t_bi:       db "BI",0

zz_text_end:

; --- οι σελιδοποιημένες διευθύνσεις, αυτές που βλέπει ο κώδικας ---
txt_o2    equ x_txt_o2 - TEXT_IMG + G_text
txt_pwr   equ x_txt_pwr - TEXT_IMG + G_text
txt_h2o   equ x_txt_h2o - TEXT_IMG + G_text
txt_fod   equ x_txt_fod - TEXT_IMG + G_text
txt_pop   equ x_txt_pop - TEXT_IMG + G_text
txt_sol   equ x_txt_sol - TEXT_IMG + G_text
txt_day   equ x_txt_day - TEXT_IMG + G_text
txt_night equ x_txt_night - TEXT_IMG + G_text
txt_ok    equ x_txt_ok - TEXT_IMG + G_text
txt_nopwr equ x_txt_nopwr - TEXT_IMG + G_text
txt_noo2  equ x_txt_noo2 - TEXT_IMG + G_text
txt_storm equ x_txt_storm - TEXT_IMG + G_text
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
t_block   equ x_t_block - TEXT_IMG + G_text
t_poor    equ x_t_poor - TEXT_IMG + G_text
t_ln1     equ x_t_ln1 - TEXT_IMG + G_text
t_ln2     equ x_t_ln2 - TEXT_IMG + G_text
t_fe      equ x_t_fe - TEXT_IMG + G_text
t_bi      equ x_t_bi - TEXT_IMG + G_text

        ; Το κενό είναι 1.024 bytes και τελειώνει εκεί που αρχίζει το επόμενο
        ; πράγμα της τράπεζας 7. Χωρίς αυτόν τον έλεγχο, ένα κείμενο παραπάνω θα
        ; έγραφε πάνω σε δεδομένα — αθόρυβα, και μόνο στην οθόνη θα φαινόταν.
        assert  zz_text_end - TEXT_IMG <= TEXT_MAX

        ; ΚΑΙ ΣΤΟΝ ΔΙΣΚΟ: η BANK7.BIN φτιάχνεται από το tools/pack.py, που δεν
        ; ξέρει τι λέει το παιχνίδι. Τα κείμενα πάνε ως δικό τους αρχείο και ο
        ; φορτωτής τα ρίχνει πάνω από το δεσμευμένο κενό.
        save    "../build/text.bin", TEXT_IMG, zz_text_end - TEXT_IMG
