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
        assert  FT_MIX == FT_CLS + 4 && FT_EMPTY == FT_MIX + 1
        assert  PEN_NO == PEN_OK ^ 1            ; fit_show: xor με το A του bd_afford

; ---------------------------------------------------------------------------
; fit_enter — από το LOOK: ο θόλος κάτω από τον κέρσορα, αν δέχεται κάτι.
; ---------------------------------------------------------------------------
fit_enter:
        call    fit_can
        jr      c,fe_go
        ret     z                       ; ο κέρσορας δεν είναι πάνω σε θόλο
        jp      uip_deny                ; θόλος, αλλά τίποτα να μπει
fe_go:
        xor     a
        ld      (fit_s),a
        inc     a
        ld      (fit_i),a               ; η κύρια μηχανή του δωματίου (rm_pref)
        call    fit_pick                ; ή ό,τι ήδη υπάρχει στην υποδοχή 0
        call    ui_click
        ld      a,UI_FIT
        jp      ui_goto

; fit_can — ανοίγει εδώ ο εξοπλισμός; Out: CY ναι, με τον κατάλογο έτοιμο·
; NC και Z: δεν είναι θόλος· NC και NZ: θόλος που δεν δέχεται τίποτα. Και για
; το μενού ενεργειών (src/act.asm, βήμα 80), που δείχνει το FIT μόνο όταν
; ανοίγει: γράφει μόνο τις μεταβλητές του εξοπλισμού, που εκτός FIT δεν τις
; διαβάζει κανείς.
fit_can:
        call    ui_dome
        cp      255
        ret     z                       ; NC, Z
        ld      (fit_d),a
        ld      a,D_SIZE
        call    fit_fld
        ld      e,(hl)                  ; E = μέγεθος
        inc     hl
        ld      a,(hl)
        ld      (fit_rm),a
        ld      d,a                     ; D = δωμάτιο
        inc     hl
        ld      a,(hl)                  ; D_STATE
        call    uid_out                 ; κρατά το DE, όπως και το ob_addu
        ; ΚΑΙ ΣΤΟ ΕΡΓΟΤΑΞΙΟ, όπως στο Planetbase: οι μηχανές μπαίνουν από τώρα
        ; και φαίνονται όταν τελειώσει ο θόλος (dh_built).
        dec     a                       ; εργοτάξιο 0, χτισμένος 1
        cp      2
        jr      nc,fc_no
        ld      a,e
        ld      hl,G_machine_count
        call    ob_addu
        ld      a,(hl)
        ld      (fit_n),a
        ; --- fit_lst = ΑΔΕΙΟ και ό,τι δέχεται το δωμάτιο σε αυτό το μέγεθος,
        ; με την κύρια μηχανή πρώτη (rm_build). Το ΑΔΕΙΟ αντιγράφεται μαζί:
        ; είναι το πρώτο byte του fl_green και το byte πριν από το rm_buf.
        ld      a,d
        ld      hl,fl_green
        ld      c,5
        cp      R_GREENHS
        jr      z,fl_copy
        ld      hl,bd_param             ; το rm_build διαβάζει το μέγεθος από
        ld      b,(hl)                  ; εκεί, και ο κατάλογος το θέλει πίσω
        ld      (hl),e
        call    rm_build                ; κρατά τα BC, DE, HL
        ld      (hl),b
        ld      c,a
        ld      hl,rm_buf - 1
fl_copy:
        ld      de,fit_lst
        inc     c
        ld      a,c
        ld      (fit_c),a
        ld      b,0
        ldir
        cp      2                       ; δωμάτιο χωρίς μηχανές: μόνο το ΑΔΕΙΟ
        ccf
        ret     c
fc_no:
        or      1                       ; NC, NZ
        ret

fl_green:   db FT_EMPTY, FT_MIX, FT_CLS, FT_CLS+1, FT_CLS+2, FT_CLS+3

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
        ld      hl,fit_n
        ld      c,(hl)
        inc     hl                      ; fit_s
        call    ui_lr
        jr      z,uf_ud
        call    fit_pick                ; δείξε ό,τι έχει η νέα υποδοχή
        jr      uf_click
uf_ud:
        ld      hl,fit_c
        ld      c,(hl)
        dec     hl                      ; fit_i
        call    ui_ud
        jr      z,uf_fire
uf_click:
        ld      a,SFX_MENU
        jr      uf_snd
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
        ld      hl,(fit_n)              ; L = fit_n, H = fit_s (ο κέρσορας)
        push    hl
        ld      b,l
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
        pop     hl
        ld      (fit_n),hl
        ld      a,c
        or      a
uf_paid:
        ld      a,SFX_BUILD
        jr      z,uf_snd
        dec     a                       ; SFX_DENY: δεν φτάνουν τα υλικά
uf_snd:
        call    snd_play
        ; Η ΥΠΟΓΡΑΦΗ ΤΟΥ ΠΙΝΑΚΑ (ui_sig) δεν ξέρει τίποτα από υποδοχές και
        ; επιλογές — μόνο το ui_state, που εδώ δεν αλλάζει.
        call    ui_dirty
        call    ui_hide                 ; το πλαίσιο αλλάζει θέση ή χρώμα
        jp      ui_show

; ---------------------------------------------------------------------------
; fit_set — η υποδοχή fit_s παίρνει το fit_lst[fit_i].
; Out: Z = μπήκε (ή ήταν ήδη εκεί), NZ = δεν φτάνουν τα υλικά.
;
; ΠΛΗΡΩΝΕΙ ΤΟ ΝΕΟ ΠΡΙΝ ΠΑΡΕΙ ΠΙΣΩ ΤΟ ΠΑΛΙΟ: μια μηχανή που αντικαθιστά άλλη
; θέλει τα υλικά της στην αποθήκη, όπως στο Planetbase, όπου το ξήλωμα είναι
; άλλη πράξη από το χτίσιμο.
; ---------------------------------------------------------------------------
fit_set:
        call    fit_want
        ret     z                       ; ίδιο: τίποτα να γίνει
        call    bd_afford               ; κρατά το BC, όπως και το bd_stock_pay
        ret     nz
        call    bd_stock_pay
        push    bc                      ; B = το παλιό, για τα μισά πίσω
        ; --- η υποδοχή ---
        call    fit_slot
        pop     bc
        push    bc
        ld      (hl),c
        ld      de,D_HEALTH - D_MACH
        add     hl,de
        ld      a,c
        cp      NO_MACH
        sbc     a,a                     ; FF μηχανή, 0 άδεια υποδοχή
        and     MACH_HP
        ld      (hl),a
        ld      a,D_STATE
        call    fit_fld
        ld      a,(hl)
        call    uid_out
        cp      DS_ACTIVE
        jr      nz,fs_give              ; εργοτάξιο: τις ζωγραφίζει το dh_built
        ld      bc,(fit_s)              ; C = υποδοχή, B = θόλος
        ld      a,DK_MACH
        call    dirty_push
fs_give:
        pop     af                      ; ΤΑ ΜΙΣΑ ΠΙΣΩ για ό,τι βγήκε
        call    fit_price
        ld      hl,(bd_metal)           ; L = μέταλλο, H = βιοπλαστικό
        push    hl
        ld      e,l
        ld      a,S_METAL
        call    fs_half
        pop     de
        ld      e,d
        ld      a,S_BIOPL
fs_half:
        srl     e
        ld      d,0
        call    ec_add_stock            ; με ταβάνι (src/stock.asm)
        xor     a                       ; Z
        ret

; fit_want — ό,τι θα έμπαινε στην υποδοχή fit_s (fit_new), και η τιμή του στο
; bd_metal, bd_biop (fit_price), που τη δείχνει και ο πίνακας.
; Out: C = το νέο, B = ό,τι έχει τώρα η υποδοχή, Z = ίδια.
fit_want:
        call    fit_new
        push    af
        call    fit_price
        call    fit_slot
        ld      a,(hl)
        call    uid_out
        pop     bc
        ld      c,b
        ld      b,a
        cp      c
        ret

; fit_price — A = περιεχόμενο υποδοχής -> bd_metal, bd_biop: η τιμή του.
; Ετσι το bd_afford, το bd_stock_pay και ο πίνακας (uip_item) δουλεύουν
; όπως για ό,τι άλλο χτίζεται. Χαλάει C, DE, HL.
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
        ld      hl,fit_cost
        call    ob_addu
        ld      a,(hl)
        and     FC_BI - 1
        ld      e,a                     ; E = μέταλλο
        xor     (hl)
        rlca
        rlca
        rlca
        ld      d,a                     ; D = βιοπλαστικό
        ex      de,hl
fpr_st:
        ld      (bd_metal),hl           ; bd_metal, bd_biop διπλανά
        ret

; Μέταλλο, βιοπλαστικό ανά μηχανή, με τη σειρά του MACH_TYPES. Οι τρεις
; ακριβές είναι οι τρεις που βγάζουν προϊόν για εμπόριο ή άμυνα· τα έπιπλα
; του ιατρείου είναι έπιπλα. ΕΝΑ BYTE η μηχανή, μέταλλο + 32 x βιοπλαστικό:
; το μέταλλο ως 31, το βιοπλαστικό ως 7 (το test_fit ελέγχει τις τιμές).
FC_BI       equ 32
fit_cost:
        db  8 + 2*FC_BI                 ; οξυγόνο
        db  8 + 2*FC_BI                 ; μέταλλο
        db  8 + 2*FC_BI                 ; βιοπλαστικό
        db 10 + 4*FC_BI                 ; όπλα
        db 10 + 4*FC_BI                 ; επεξεργαστές
        db 10 + 4*FC_BI                 ; ρομπότ
        db  6 + 2*FC_BI                 ; γεύματα
        db  8 + 2*FC_BI                 ; ανταλλακτικά
        db  8 + 2*FC_BI                 ; φάρμακα
        db  8 + 2*FC_BI                 ; κρέας εργαστηρίου
        db  4 + 2*FC_BI                 ; κρεβάτια
        db  4 + 2*FC_BI                 ; ντουλάπι φαρμάκων

; fit_new — A = ό,τι γράφεται στην υποδοχή fit_s για το fit_lst[fit_i]: η
; μηχανή, η ποικιλία του φυτού, ή NO_MACH. Χαλάει BC, HL.
;
; Η ΠΟΙΚΙΛΙΑ: η πρώτη της κλάσης, και στο άμυλο και στα λαχανικά, που έχουν
; από πέντε, συν την υποδοχή mod 5 — ώστε ένα χωράφι με άμυλο να μην είναι
; οκτώ φορές το ίδιο sprite. Η πρώτη κάθε κλάσης είναι τα τέσσερα πρώτα του
; rm_plants, που ξεκινά την εναλλαγή του από εκεί. Το ΜΙΚΤΟ: το rm_plants
; στη θέση της υποδοχής, η παλιά αυτόματη μίξη.
fit_new:
        ld      a,(fit_i)
        call    fit_code
        cp      FT_CLS
        ret     c                       ; μηχανή: ο ίδιος ο αριθμός της
        cp      FT_EMPTY
        ret     z
        sub     FT_CLS
        ld      c,a                     ; C = κλάση 0-3, ή 4 το ΜΙΚΤΟ
        ld      a,(fit_s)
        ld      b,a
        bit     2,c
        jr      nz,fn_at                ; ΜΙΚΤΟ: η θέση στο rm_plants = υποδοχή
        ld      a,c
fn_at:
        ld      hl,rm_plants
        call    ob_addu
        ld      a,c
        and     6                       ; βότανα, δέντρο, ΜΙΚΤΟ: συν τίποτα
        ld      a,0
        jr      nz,fn_add
        ld      a,b
        cp      5
        jr      c,fn_add
        sub     5
fn_add:
        add     a,(hl)
        ret

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
        ld      hl,fit_c
        ld      c,(hl)
        ld      b,0
        inc     hl                      ; fit_lst
        cpir
        ret     nz                      ; δεν είναι στη λίστα (δεν θα έπρεπε)
        ld      a,l                     ; το L του fit_lst + θέση + 1, και η
        sub     (fit_lst + 1) & 255     ; διαφορά των L είναι σωστή και αν
        ld      (fit_i),a               ; η λίστα περνά όριο σελίδας
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
        call    fit_want                ; και η τιμή, για τον πίνακα
        ld      a,PEN_CUR
        jr      z,fsh_pen               ; ήδη μέσα
        call    bd_afford               ; A = 0 πληρώνεται, 1 όχι
        xor     PEN_OK
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
        call    hud_space               ; 39 στήλες ως εδώ, η 40ή κενή
        jp      uip_spd

fit_rm:     db 0
fit_n:      db 0                        ; πόσες υποδοχές έχει
fit_s:      db 0                        ; η υποδοχή
fit_d:      db 0                        ; ο θόλος
fit_i:      db 0                        ; η επιλογή, θέση στο fit_lst
fit_c:      db 0                        ; πόσες επιλογές
fit_lst:    defs FIT_MAX
        ; ld hl,(fit_n) / ld bc,(fit_s) / ld hl,fit_n: ld c,(hl): inc hl ·
        ; ld hl,fit_c: ld c,(hl): dec hl για το fit_i, inc hl για το fit_lst
        assert  fit_s == fit_n + 1 && fit_d == fit_s + 1
        assert  fit_c == fit_i + 1 && fit_lst == fit_c + 1
