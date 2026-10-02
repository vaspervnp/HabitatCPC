; fit.asm — ο εξοπλισμός ενός θόλου, υποδοχή-υποδοχή (DESIGN §6.5, §9.3).
;
; ΟΠΩΣ ΣΤΟ PLANETBASE (βήμα 45). Ο θόλος χτίζεται άδειος· το δωμάτιο λέει τι
; ΧΩΡΑΕΙ μέσα (rm_build), ο παίκτης διαλέγει τι ΜΠΑΙΝΕΙ σε κάθε υποδοχή και το
; πληρώνει χωριστά. Ως το βήμα 44 οι υποδοχές γέμιζαν μόνες τους, κυκλικά, και
; ένα μεγάλο εργοστάσιο έβγαζε από όλα λίγο αντί για αυτό που έλειπε.
;
; Από το LOOK, FIRE πάνω σε θόλο — χτισμένο ή εργοτάξιο:
;
;   αριστερά / δεξιά    ποια υποδοχή
;   πάνω / κάτω         τι μπαίνει: ΑΔΕΙΟ ή ό,τι δέχεται το δωμάτιο
;   FIRE                μπαίνει και πληρώνεται· ό,τι βγήκε δίνει τα μισά πίσω
;   SPACE               το ίδιο σε ΟΛΕΣ τις υποδοχές, όσο φτάνουν τα υλικά
;   ESC                 πίσω στο LOOK
;
; ΤΟ ΘΕΡΜΟΚΗΠΙΟ διαλέγει ΚΑΛΛΙΕΡΓΕΙΑ, όχι ποικιλία — άμυλο, λαχανικά, βότανα,
; δέντρο — και η ποικιλία βγαίνει από την υποδοχή, ώστε ένα χωράφι με άμυλο να
; μην είναι οκτώ φορές το ίδιο sprite. Και ΜΙΚΤΟ: η εναλλαγή του rm_plants, η
; παλιά αυτόματη μίξη, για όποιον θέλει έναν θόλο που τα βγάζει όλα (με SPACE).

UI_FIT      equ 5
FT_CLS      equ 250                     ; 250..253: άμυλο, λαχανικά, βότανα, δέντρο
FT_MIX      equ 254
FT_EMPTY    equ NO_MACH                 ; η άδεια υποδοχή: γράφεται όπως είναι
PLANT_FE    equ 2                       ; ένα φυτό: δύο μέταλλο, καθόλου βιοπλαστικό
FIT_MAX     equ 13                      ; ΑΔΕΙΟ και ως δώδεκα μηχανές (RM_MACH)
MACH_HP     equ 200                     ; καινούργια μηχανή (όπως στο newgame)

        assert  D_ROOM == D_SIZE + 1 && D_STATE == D_SIZE + 2
        assert  DS_BUILDING == 1 && DS_ACTIVE == 2
        assert  A_UP + 1 == A_DOWN && A_LEFT + 1 == A_RIGHT

; ---------------------------------------------------------------------------
; fit_enter — από το LOOK: ο θόλος κάτω από τον κέρσορα, αν δέχεται κάτι.
; ---------------------------------------------------------------------------
fit_enter:
        call    ui_dome
        cp      255
        ret     z                       ; ο κέρσορας δεν είναι πάνω σε θόλο
        ld      (fit_d),a
        ld      a,D_SIZE
        call    fit_fld
        ld      a,(hl)
        ld      (fit_sz),a
        inc     hl
        ld      a,(hl)
        ld      (fit_rm),a
        inc     hl
        ld      a,(hl)                  ; D_STATE
        call    uid_out
        ; ΚΑΙ ΣΤΟ ΕΡΓΟΤΑΞΙΟ, όπως στο Planetbase: οι μηχανές μπαίνουν από τώρα
        ; και φαίνονται όταν τελειώσει ο θόλος (dh_built).
        dec     a                       ; εργοτάξιο 0, χτισμένος 1
        cp      2
        jp      nc,uip_deny
        ld      a,(fit_sz)
        ld      hl,G_machine_count
        call    ob_addu
        ld      a,(hl)
        ld      (fit_n),a
        call    fit_list
        cp      2
        jp      c,uip_deny              ; δωμάτιο χωρίς μηχανές: τίποτα να μπει
        xor     a
        ld      (fit_s),a
        inc     a
        ld      (fit_i),a               ; η κύρια μηχανή του δωματίου (rm_pref)
        call    fit_pick                ; ή ό,τι ήδη υπάρχει στην υποδοχή 0
        call    ui_click
        ld      a,UI_FIT
        jp      ui_goto

; fit_list — fit_lst = ΑΔΕΙΟ και ό,τι δέχεται το δωμάτιο σε αυτό το μέγεθος,
; με την κύρια μηχανή πρώτη (rm_build). Out: A = (fit_c) = πόσα.
fit_list:
        ld      hl,fit_lst
        ld      (hl),FT_EMPTY
        inc     hl
        ex      de,hl                   ; DE -> fit_lst + 1
        ld      a,(fit_rm)
        ld      hl,fl_green
        ld      c,5
        cp      R_GREENHS
        jr      z,fl_copy
        ld      hl,bd_param             ; το rm_build διαβάζει το μέγεθος από
        ld      b,(hl)                  ; εκεί, και ο κατάλογος το θέλει πίσω
        ld      c,a
        ld      a,(fit_sz)
        ld      (hl),a
        ld      a,c
        call    rm_build                ; κρατά τα BC, DE, HL
        ld      (hl),b
        ld      c,a
        ld      hl,rm_buf
fl_copy:
        ld      a,c
        inc     a
        ld      (fit_c),a
        ld      b,0
        inc     c
        dec     c
        ret     z
        ldir
        ret

fl_green:   db FT_MIX, FT_CLS, FT_CLS+1, FT_CLS+2, FT_CLS+3

; ---------------------------------------------------------------------------
; uist_fit — ένα καρέ εισόδου στον εξοπλισμό.
; ---------------------------------------------------------------------------
uist_fit:
        ld      a,A_CANCEL
        call    in_hit
        jr      z,uf_lr
        xor     a                       ; UI_LOOK
        jp      ui_goto
uf_lr:
        ld      hl,fit_s
        ld      a,(fit_n)
        ld      c,a
        call    ui_lr
        jr      z,uf_ud
        call    fit_pick                ; δείξε ό,τι έχει η νέα υποδοχή
        jr      uf_click
uf_ud:
        ld      hl,fit_i
        ld      a,(fit_c)
        ld      c,a
        call    ui_ud
        jr      z,uf_fire
uf_click:
        call    ui_click
uf_redo:
        ; Η ΥΠΟΓΡΑΦΗ ΤΟΥ ΠΙΝΑΚΑ (ui_sig) δεν ξέρει τίποτα από υποδοχές και
        ; επιλογές — μόνο το ui_state, που εδώ δεν αλλάζει.
        call    ui_dirty
        call    ui_hide                 ; το πλαίσιο αλλάζει θέση ή χρώμα
        jp      ui_show
uf_fire:
        ld      a,A_FIRE
        call    in_hit
        jr      z,uf_all
        call    fit_set
        jr      uf_paid
uf_all:
        ld      a,A_MENU
        call    in_hit
        ret     z
        ; ΟΛΕΣ ΟΙ ΥΠΟΔΟΧΕΣ, από την πρώτη. Οσες δεν πληρώνονται μένουν όπως
        ; ήταν, και ο ήχος της άρνησης λέει «όχι όλες».
        ld      a,(fit_s)
        push    af
        ld      a,(fit_n)
        ld      b,a
        ld      c,0                     ; πόσες δεν πληρώθηκαν
ufa_lp:
        push    bc
        ld      a,(fit_n)
        sub     b
        ld      (fit_s),a
        call    fit_set
        pop     bc
        jr      z,ufa_ok
        inc     c
ufa_ok:
        djnz    ufa_lp
        pop     af
        ld      (fit_s),a
        ld      a,c
        or      a
uf_paid:
        ld      a,SFX_BUILD
        jr      z,uf_snd
        ld      a,SFX_DENY              ; δεν φτάνουν τα υλικά
uf_snd:
        call    snd_play
        jr      uf_redo

; ---------------------------------------------------------------------------
; fit_set — η υποδοχή fit_s παίρνει το fit_lst[fit_i].
; Out: Z = μπήκε (ή ήταν ήδη εκεί), NZ = δεν φτάνουν τα υλικά.
;
; ΠΛΗΡΩΝΕΙ ΤΟ ΝΕΟ ΠΡΙΝ ΠΑΡΕΙ ΠΙΣΩ ΤΟ ΠΑΛΙΟ: μια μηχανή που αντικαθιστά άλλη
; θέλει τα υλικά της στην αποθήκη, όπως στο Planetbase, όπου το ξήλωμα είναι
; άλλη πράξη από το χτίσιμο.
; ---------------------------------------------------------------------------
fit_set:
        call    fit_new
        ld      (fit_nw),a
        call    fit_slot
        ld      a,(hl)
        call    uid_out
        ld      (fit_old),a
        ld      hl,fit_nw
        cp      (hl)
        ret     z                       ; ίδιο: τίποτα να γίνει
        ld      a,(hl)
        call    fit_price
        call    bd_afford
        ret     nz
        call    bd_stock_pay
        ld      a,(fit_old)             ; ΤΑ ΜΙΣΑ ΠΙΣΩ για ό,τι βγήκε
        call    fit_price
        ld      hl,(bd_metal)           ; L = μέταλλο, H = βιοπλαστικό
        srl     l
        srl     h
        push    hl
        ld      a,l
        ld      hl,EC_STOCK + S_METAL*2
        call    fit_give
        pop     af                      ; A = H
        ld      hl,EC_STOCK + S_BIOPL*2
        call    fit_give
        ; --- η υποδοχή ---
        call    fit_slot
        ld      a,(fit_nw)
        ld      (hl),a
        ld      de,D_HEALTH - D_MACH
        add     hl,de
        ld      (hl),0                  ; άδεια υποδοχή: καμία υγεία
        inc     a
        jr      z,fs_hp
        ld      (hl),MACH_HP
fs_hp:
        ld      a,D_STATE
        call    fit_fld
        ld      a,(hl)
        call    uid_out
        cp      DS_ACTIVE
        jr      nz,fs_out               ; εργοτάξιο: τις ζωγραφίζει το dh_built
        ld      a,(fit_d)
        ld      b,a
        ld      a,(fit_s)
        ld      c,a
        ld      a,DK_MACH
        call    dirty_push
fs_out:
        xor     a                       ; Z
        ret

; fit_give — (HL) += A, 16 bit, με ταβάνι EC_CAP όπως το ec_add_stock (που
; δεν υπάρχει στο tests/uitest.asm).
fit_give:
        ld      e,(hl)
        inc     hl
        ld      d,(hl)
        ex      de,hl                   ; HL = απόθεμα, DE -> το πάνω byte του
        call    ob_addu
        push    de
        ld      de,EC_CAP
        or      a
        sbc     hl,de
        add     hl,de                   ; CY αν κάτω από το ταβάνι
        pop     de
        jr      c,fg_st
        ld      hl,EC_CAP
fg_st:
        ex      de,hl
        ld      (hl),d
        dec     hl
        ld      (hl),e
        ret

; fit_price — A = περιεχόμενο υποδοχής -> bd_metal, bd_biop: η τιμή του.
; Ετσι το bd_afford, το bd_stock_pay και ο πίνακας (uip_item) δουλεύουν
; όπως για ό,τι άλλο χτίζεται.
fit_price:
        ld      hl,0
        cp      NO_MACH
        jr      z,fpr_st
        ld      c,a
        ld      a,(fit_rm)
        cp      R_GREENHS
        ld      hl,PLANT_FE
        jr      z,fpr_st
        ld      a,c
        add     a,a
        ld      hl,fit_cost
        call    ob_addu
        ld      a,(hl)
        inc     hl
        ld      h,(hl)
        ld      l,a
fpr_st:
        ld      (bd_metal),hl           ; bd_metal, bd_biop διπλανά
        ret

; Μέταλλο, βιοπλαστικό ανά μηχανή, με τη σειρά του MACH_TYPES. Οι τρεις
; ακριβές είναι οι τρεις που βγάζουν προϊόν για εμπόριο ή άμυνα· τα έπιπλα
; του ιατρείου είναι έπιπλα.
fit_cost:
        db  8, 2                        ; οξυγόνο
        db  8, 2                        ; μέταλλο
        db  8, 2                        ; βιοπλαστικό
        db 10, 4                        ; όπλα
        db 10, 4                        ; επεξεργαστές
        db 10, 4                        ; ρομπότ
        db  6, 2                        ; γεύματα
        db  8, 2                        ; ανταλλακτικά
        db  8, 2                        ; φάρμακα
        db  8, 2                        ; κρέας εργαστηρίου
        db  4, 2                        ; κρεβάτια
        db  4, 2                        ; ντουλάπι φαρμάκων

; fit_new — A = ό,τι γράφεται στην υποδοχή fit_s για το fit_lst[fit_i]: η
; μηχανή, η ποικιλία του φυτού, ή NO_MACH.
fit_new:
        ld      a,(fit_i)
        call    fit_code
        cp      FT_CLS
        ret     c                       ; μηχανή: ο ίδιος ο αριθμός της
        cp      FT_EMPTY
        ret     z
        ld      c,a
        ld      a,(fit_s)
        ld      hl,rm_plants            ; ΜΙΚΤΟ: η παλιά μίξη, ανά υποδοχή
        ld      b,a
        call    ob_addu
        ld      a,c
        cp      FT_MIX
        ld      a,(hl)
        ret     z
        ld      a,c
        sub     FT_CLS                  ; 0 άμυλο, 1 λαχανικά, 2 βότανα, 3 δέντρο
        ld      e,a
        ld      hl,fw_base
        call    ob_addu
        ld      a,e
        cp      2
        ld      a,(hl)
        ret     nc                      ; βότανα, δέντρο: μία ποικιλία το καθένα
        ld      c,a                     ; άμυλο, λαχανικά: πέντε, ανά υποδοχή
        ld      a,b
        cp      5
        jr      c,fw_add
        sub     5
fw_add:
        add     a,c
        ret

fw_base:    db 0, 5, 10, 11             ; η πρώτη ποικιλία κάθε κλάσης (plant_class)

; fit_code — A = θέση στη λίστα -> A = ο κωδικός της (fit_lst[A]).
fit_code:
        ld      hl,fit_lst
        call    ob_addu
        ld      a,(hl)
        ret

; fit_pick — fit_i = ό,τι έχει ήδη η υποδοχή fit_s. Σε άδεια υποδοχή μένει η
; τελευταία επιλογή: διάλεξε ΜΕΤΑΛΛΟ, και δεξιά-FIRE γεμίζει τις επόμενες.
fit_pick:
        call    fit_slot
        ld      a,(hl)
        call    uid_out
        cp      NO_MACH
        ret     z
        ld      c,a
        ld      a,(fit_rm)
        cp      R_GREENHS
        ld      a,c
        jr      nz,fp_find
        ld      hl,G_plant_class        ; στο θερμοκήπιο ψάχνεται η ΚΛΑΣΗ
        call    ob_addu
        ld      a,(hl)
        add     a,FT_CLS
fp_find:
        ld      c,a
        ld      b,0
fp_lp:
        ld      a,b
        call    fit_code
        cp      c
        jr      z,fp_hit
        inc     b
        ld      a,(fit_c)
        cp      b
        jr      nz,fp_lp
        ret                             ; δεν είναι στη λίστα (δεν θα έπρεπε)
fp_hit:
        ld      a,b
        ld      (fit_i),a
        ret

; fit_slot — HL -> η υποδοχή fit_s του fit_d, με την τράπεζα 6 μέσα.
; fit_fld — το ίδιο για το πεδίο A της εγγραφής. Χαλάνε τα BC, DE.
fit_slot:
        ld      a,(fit_s)
        add     a,D_MACH
fit_fld:
        ld      c,a
        ld      a,(fit_d)
        call    ob_domeadr
        ld      a,c
        call    ob_addu
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        ret

; ---------------------------------------------------------------------------
; fit_show — το ui_show στον εξοπλισμό: ένα πλαίσιο γύρω από την υποδοχή, ροζ
; αν η επιλογή είναι ήδη μέσα, πράσινο αν πληρώνεται, κόκκινο αν όχι.
; ---------------------------------------------------------------------------
fit_show:
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        ld      a,(fit_d)
        call    ob_getdome              ; d_rec και το πλαίσιο, για την κάμερα
        call    uid_out                 ; που ισχύει ΤΩΡΑ
        ld      a,(fit_s)
        ld      de,G_machine_slots
        call    ob_slot_at
        ld      hl,(ob_x)
        dec     hl
        ld      (gh_bx),hl
        ld      hl,(ob_y)
        dec     hl
        dec     hl
        ld      (gh_by),hl
        ld      hl,(MACH_H + 4)*256 + MACH_W + 2
        ld      (gh_bw),hl              ; gh_bw, gh_bh διπλανά
        call    fit_new
        ld      c,a
        push    bc
        call    fit_price               ; και για τον πίνακα: uip_item, ui_sig
        pop     bc
        ld      a,(fit_s)
        ld      hl,d_rec + D_MACH
        call    ob_addu
        ld      a,(hl)
        cp      c
        ld      a,PEN_CUR
        jr      z,fsh_pen
        call    bd_afford
        ld      a,PEN_OK
        jr      z,fsh_pen
        ld      a,PEN_NO
fsh_pen:
        call    gh_setpen
        call    gh_box
        jp      ui_panel

; fit_name — η σειρά 3 (uip_item): το όνομα της επιλογής στη θέση του ονόματος
; του καταλόγου, πλάτος 12 όπως εκείνο.
fit_name:
        ld      a,(fit_i)
        call    fit_code
        cp      FT_CLS
        jr      c,fn_m
        sub     FT_CLS - FIT_MAX + 1    ; 250.. -> 12.., μετά τις μηχανές
fn_m:
        add     a,a
        add     a,a
        add     a,a                     ; οκτώ bytes το όνομα
        ld      hl,t_f_names
        call    ob_addu
        call    hud_text7
        ld      b,12 - 7
        call    hud_blank
        jp      uipi_arrow

; fit_row4 — «SLOT 2/4  UP/DN=PICK FIRE=FIT SPACE=ALL».
fit_row4:
        ld      hl,t_f_slot
        call    hud_text7
        ld      a,(fit_s)
        add     a,'1'
        call    hud_char
        ld      a,'/'
        call    hud_char
        ld      a,(fit_n)
        add     a,'0'
        call    hud_char
        ld      b,2
        call    hud_blank
        ld      hl,t_f_keys
        call    hud_text7
        ld      b,40 - 39
        call    hud_blank
        jp      uip_spd

fit_d:      db 0                        ; ο θόλος
fit_s:      db 0                        ; η υποδοχή
fit_n:      db 0                        ; πόσες υποδοχές έχει
fit_i:      db 0                        ; η επιλογή, θέση στο fit_lst
fit_c:      db 0                        ; πόσες επιλογές
fit_rm:     db 0
fit_sz:     db 0
fit_nw:     db 0
fit_old:    db 0
fit_lst:    defs FIT_MAX
