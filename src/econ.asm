; econ.asm — αποθέματα, παραγωγή, ισοζύγιο ροών, συμβάντα (§6.5, §6.10)
;
; Οι θέσεις 11, 12 και 15 του τροχού. Και οι τρεις δουλεύουν πάνω στο
; econ_state, που ζει στην ΤΡΑΠΕΖΑ 2 και όχι στην 6: τα αποθέματα τα διαβάζει
; το HUD σε κάθε frame, και ο,τι διαβάζεται έξω από τη σειρά της προσομοίωσης
; δεν μπορεί να είναι πίσω από σελιδοποίηση.
;
; Η ΠΑΡΑΓΩΓΗ ΔΙΑΒΑΖΕΙ ΤΟ ΙΣΟΖΥΓΙΟ ΤΗΣ ΠΡΟΗΓΟΥΜΕΝΗΣ ΠΕΡΙΣΤΡΟΦΗΣ (το
; power_ok), και το ισοζύγιο διαβάζει την κατανάλωση του προηγούμενου
; ΣΑΡΩΜΑΤΟΣ (το mach_power). Χωρίς αυτό το buffer οι δύο θέσεις θα ήθελαν η
; μία την άλλη μέσα στο ίδιο frame. Το §6.5 λέει ήδη «buffered».

EC_STOCK    equ G_econ_state            ; 14 x 16-bit
EC_PSTORE   equ G_econ_state + 28
EC_PCAP     equ G_econ_state + 30
EC_PPROD    equ G_econ_state + 32
EC_PUSE     equ G_econ_state + 34
EC_MPOWER   equ G_econ_state + 36
EC_O2PROD   equ G_econ_state + 38
EC_O2USE    equ G_econ_state + 40
EC_ACCP     equ G_econ_state + 42
EC_ACCO2    equ G_econ_state + 44
EC_POK      equ G_econ_state + 46
EC_O2OK     equ G_econ_state + 47
EC_PDOME    equ G_econ_state + 48
EC_DAY      equ G_econ_state + 49
EC_WIND     equ G_econ_state + 50
EC_SOL      equ G_econ_state + 51
EC_FRAME    equ G_econ_state + 52
EC_RND      equ G_econ_state + 54
EC_JDOME    equ G_econ_state + 56       ; περιστροφικοί δείκτες του πίνακα
EC_JAGENT   equ G_econ_state + 57       ; εργασιών (§6.7)
EC_ALIVE    equ G_econ_state + 58
EC_GAMEOVER equ G_econ_state + 59       ; §10.3 — η μόνη συνθήκη ήττας
EC_GLOOM    equ G_econ_state + 60       ; πένθος: ανεβαίνει με κάθε θάνατο
EC_STORM    equ G_econ_state + 61       ; περιστροφές αμμοθύελλας (§6.10)
EC_AMENITY  equ G_econ_state + 62       ; δέντρα και σαλόνια (§6.6)
EC_SOLLEN   equ G_econ_state + 64       ; frames ανά sol — ΔΕΔΟΜΕΝΟ (§6.11)
EC_DAYLEN   equ G_econ_state + 66
EC_PRODM    equ G_econ_state + 68       ; ποια αποθέματα φτιάχτηκαν ΕΔΩ
EC_SHETA    equ G_econ_state + 70
EC_SHSTATE  equ G_econ_state + 72
EC_SHKIND   equ G_econ_state + 73
EC_POPCAP   equ G_econ_state + 74
EC_MILE     equ G_econ_state + 75       ; τα πέντε ορόσημα του §10.2
EC_DEATHS   equ G_econ_state + 76
EC_NODEATH  equ G_econ_state + 77
EC_GREENS   equ G_econ_state + 78
EC_NOTRADE  equ G_econ_state + 79
EC_TRADED   equ G_econ_state + 80
EC_PADNODE  equ G_econ_state + 81

EC_CAP      equ 600                     ; ταβάνι αποθέματος
DOME_REC    equ 24
D_SIZE      equ 2
D_ROOM      equ 3
D_STATE     equ 4
D_OPS       equ 7
D_MACH      equ 8
D_HEALTH    equ 16
DS_ACTIVE   equ 2
NO_MACH     equ 255
NO_STOCK    equ 255
MF_OPERATOR equ 1
MF_FLOW     equ 2
PROD_DOMES  equ 16
R_GREENHS   equ 5
R_LOUNGE    equ 11
STORM_LEN   equ 32
S_WATER     equ 0
S_FOOD      equ 1
S_ORE       equ 2
S_STARCH    equ 10
S_VEG       equ 11
S_MEDPLANT  equ 12
MAX_DOME    equ 64
MAX_STRUCT  equ 64
STRUCT_REC  equ 8
ST_KIND     equ 2
ST_SIZE     equ 3
ST_STATE    equ 4
K_SOLAR     equ 0
K_TURBINE   equ 1
K_COLLECT   equ 2
K_EXTRACT   equ 3
K_MINE      equ 4
O2_PER_COL  equ 2
SOL_FRAMES  equ 12000
DAY_FRAMES  equ 7200                    ; 3/5 του sol

; ---------------------------------------------------------------------------
; econ_prod_slice — θέση 11: PROD_DOMES θόλοι, σάρωμα σε τέσσερις περιστροφές.
; ---------------------------------------------------------------------------
econ_prod_slice:
        ld      b,PROD_DOMES
epr_lp:
        push    bc
        call    ec_run_dome
        ld      a,(EC_PDOME)
        inc     a
        cp      MAX_DOME
        jr      c,epr_store
        ; το σάρωμα έκλεισε: ό,τι μαζεύτηκε γίνεται η επίσημη τιμή
        ld      hl,(EC_ACCP)
        ld      (EC_MPOWER),hl
        ld      hl,(EC_ACCO2)
        ld      (EC_O2PROD),hl
        ld      hl,0
        ld      (EC_ACCP),hl
        ld      (EC_ACCO2),hl
        xor     a
epr_store:
        ld      (EC_PDOME),a
        pop     bc
        djnz    epr_lp
        ret

; --- ένας θόλος ------------------------------------------------------------
; Ο δείκτης περπατάει· δεν ξαναϋπολογίζεται. Η πρώτη γραφή ξανάφτιαχνε τη
; διεύθυνση της εγγραφής για κάθε πεδίο και κόστιζε 7.488 us τη θέση.
ec_run_dome:
        ld      a,(EC_PDOME)
        ld      h,0
        ld      l,a
        add     hl,hl
        add     hl,hl
        add     hl,hl                   ; *8
        ld      d,h
        ld      e,l
        add     hl,hl                   ; *16
        add     hl,de                   ; *24
        ld      de,G_dome_tbl
        add     hl,de                   ; HL = εγγραφή θόλου

        ld      de,D_STATE
        add     hl,de
        ld      a,(hl)
        cp      DS_ACTIVE
        ret     nz
        ld      de,D_ROOM - D_STATE
        add     hl,de
        ld      a,(hl)
        cp      R_GREENHS
        ld      a,0
        jr      nz,erd_ng
        inc     a
erd_ng:
        ld      (ed_green),a
        ld      de,D_OPS - D_ROOM
        add     hl,de
        ld      a,(hl)
        ld      (ed_ops),a              ; HL = base + D_OPS
        push    hl
        ld      de,D_SIZE - D_OPS       ; πίσω στο μέγεθος
        add     hl,de
        ld      a,(hl)
        pop     hl
        ld      de,G_machine_count
        push    hl
        ld      l,a
        ld      h,0
        add     hl,de
        ld      b,(hl)                  ; B = πόσες υποδοχές
        pop     hl
        ld      de,D_MACH - D_OPS
        add     hl,de                   ; HL = base + D_MACH

        xor     a
        ld      (ed_slot),a
erd_lp:
        ld      a,(hl)
        cp      NO_MACH
        jr      z,erd_next
        push    bc
        push    hl
        ld      b,a
        ld      a,(ed_green)
        or      a
        ld      a,b
        jr      z,erd_mach
        call    ec_run_plant            ; A = φυτό, HL -> υποδοχή
        jr      erd_back
erd_mach:
        call    ec_run_mach             ; A = μηχανή, HL -> υποδοχή
erd_back:
        pop     hl
        pop     bc
erd_next:
        inc     hl
        ld      a,(ed_slot)
        inc     a
        ld      (ed_slot),a
        djnz    erd_lp
        ret

; --- ένα φυτό --------------------------------------------------------------
; Ιδια υποδοχή, άλλο νόημα: το είδος δωματίου λέει αν εκεί κάθεται μηχανή ή
; φυτό. Νερό και ρεύμα μέσα, χλωρίδα έξω (§6.5).
ec_run_plant:
        ld      (ed_m),a
        push    hl
        ld      de,D_HEALTH - D_MACH
        add     hl,de
        ld      e,(hl)
        pop     hl
        inc     e
        dec     e
        ret     z                       ; μαραμένο

        ld      a,(ed_slot)             ; τα φυτά θέλουν φροντίδα
        ld      hl,ed_ops
        cp      (hl)
        ret     nc
        ld      a,(EC_POK)
        or      a
        ret     z

        ld      a,S_WATER               ; ένα νερό
        ld      c,1
        call    ec_have
        ret     c
        ld      a,(de)
        sub     1
        ld      (de),a
        inc     de
        ld      a,(de)
        sbc     a,0
        ld      (de),a

        ld      de,1                    ; ένα ρεύμα
        ld      hl,EC_ACCP
        call    ec_add16

        ld      a,(ed_m)                ; η κατηγορία του φυτού
        ld      hl,G_plant_class
        add     a,l
        ld      l,a
        ld      a,0
        adc     a,h
        ld      h,a
        ld      a,(hl)
        and     3
        add     a,a                     ; *2 στον πίνακα εξόδου
        ld      hl,plant_out
        add     a,l
        ld      l,a
        ld      a,0
        adc     a,h
        ld      h,a
        ld      a,(hl)                  ; απόθεμα, 255 = τίποτα (δέντρο)
        inc     hl
        ld      e,(hl)
        ld      d,0
        cp      NO_STOCK
        ret     z
        call    ec_mark
        jp      ec_add_stock

plant_out:  db S_STARCH,3, S_VEG,2, S_MEDPLANT,2, NO_STOCK,0

; --- μία μηχανή ------------------------------------------------------------
; A = τύπος μηχανής, HL = δείκτης στην υποδοχή (η υγεία είναι 8 πιο κάτω).
ec_run_mach:
        push    hl
        ld      de,D_HEALTH - D_MACH
        add     hl,de
        ld      e,(hl)                  ; υγεία
        pop     hl
        inc     e
        dec     e
        ret     z                       ; χαλασμένη

        ; IX = συνταγή = G_recipes + m*10
        ld      h,0
        ld      l,a
        ld      d,h
        ld      e,l
        add     hl,hl
        add     hl,hl
        add     hl,hl                   ; *8
        add     hl,de
        add     hl,de                   ; *10
        ld      de,G_recipes
        add     hl,de
        push    hl
        pop     ix

        ld      a,(ix+9)                ; σημαίες
        ld      (ed_flags),a
        and     MF_OPERATOR
        jr      z,erm_power
        ld      a,(ed_slot)
        ld      hl,ed_ops
        cp      (hl)
        ret     nc                      ; αυτή η υποδοχή δεν έχει χειριστή
erm_power:
        ld      a,(EC_POK)
        or      a
        ret     z                       ; μπλακάουτ

        ; --- οι τρεις είσοδοι, ξετυλιγμένες ---
        ; Ο βρόχος με IY και υπολογισμό μετατόπισης κόστιζε 280 T-states ανά
        ; είσοδο. Με σταθερές μετατοπίσεις IX και πρόωρη έξοδο στην πρώτη που
        ; λείπει, η συνηθισμένη περίπτωση — «δεν φτάνει» — βγαίνει αμέσως.
        ld      a,(ix+0)
        cp      NO_STOCK
        jr      z,erm_n1
        ld      c,(ix+1)
        call    ec_have
        ret     c
        ld      (ed_p1),de
        ld      a,c
        ld      (ed_q1),a
        jr      erm_i2
erm_n1:
        ld      hl,0
        ld      (ed_p1),hl
erm_i2:
        ld      a,(ix+2)
        cp      NO_STOCK
        jr      z,erm_n2
        ld      c,(ix+3)
        call    ec_have
        ret     c
        ld      (ed_p2),de
        ld      a,c
        ld      (ed_q2),a
        jr      erm_i3
erm_n2:
        ld      hl,0
        ld      (ed_p2),hl
erm_i3:
        ld      a,(ix+4)
        cp      NO_STOCK
        jr      z,erm_n3
        ld      c,(ix+5)
        call    ec_have
        ret     c
        ld      (ed_p3),de
        ld      a,c
        ld      (ed_q3),a
        jr      erm_run
erm_n3:
        ld      hl,0
        ld      (ed_p3),hl

erm_run:
        ; --- αφαίρεση, με τους δείκτες που ήδη έχουμε ---
        ld      de,(ed_p1)
        ld      a,(ed_q1)
        call    ec_sub
        ld      de,(ed_p2)
        ld      a,(ed_q2)
        call    ec_sub
        ld      de,(ed_p3)
        ld      a,(ed_q3)
        call    ec_sub

        ld      e,(ix+8)                ; ρεύμα
        ld      d,0
        ld      hl,EC_ACCP
        call    ec_add16

        ld      a,(ed_flags)
        and     MF_FLOW
        jr      z,erm_stock
        ld      e,(ix+7)
        ld      d,0
        ld      hl,EC_ACCO2
        jp      ec_add16
erm_stock:
        ld      a,(ix+6)                ; δείκτης αποθέματος
        cp      NO_STOCK
        ret     z
        call    ec_mark                 ; φτιάχτηκε ΕΔΩ (§10.2)
        ld      e,(ix+7)
        ld      d,0
        jp      ec_add_stock

; ec_mark — A = δείκτης αποθέματος. Σημειώνει ότι βγήκε από την αποικία.
ec_mark:
        push    af
        push    bc
        push    de
        push    hl
        ld      b,a
        ld      hl,1
        inc     b
ecm_sh:
        dec     b
        jr      z,ecm_or
        add     hl,hl
        jr      ecm_sh
ecm_or:
        ld      de,(EC_PRODM)
        ld      a,h
        or      d
        ld      h,a
        ld      a,l
        or      e
        ld      l,a
        ld      (EC_PRODM),hl
        pop     hl
        pop     de
        pop     bc
        pop     af
        ret

; ec_have — A = δείκτης αποθέματος, C = ποσότητα.
;           Επιστρέφει DE = &stock[A], Cy=1 αν ΔΕΝ φτάνει.
ec_have:
        push    hl
        ld      l,a
        ld      h,0
        add     hl,hl
        ld      de,EC_STOCK
        add     hl,de
        ex      de,hl
        pop     hl
        ld      a,(de)
        sub     c
        inc     de
        ld      a,(de)
        sbc     a,0                     ; τα inc/dec de δεν πειράζουν το carry
        dec     de
        ret

; ec_sub — DE = &stock (ή 0 = καμία είσοδος), A = ποσότητα.
ec_sub:
        ld      c,a
        ld      a,d
        or      e
        ret     z
        ld      a,(de)
        sub     c
        ld      (de),a
        inc     de
        ld      a,(de)
        sbc     a,0
        ld      (de),a
        ret

; ec_add_stock — A = δείκτης, DE = ποσότητα (16-bit: οι αντλίες ξεπερνούν
; εύκολα το 255). Με ταβάνι EC_CAP.
ec_add_stock:
        push    de
        call    ec_stock_ptr
        ex      de,hl                   ; HL = &stock
        pop     bc                      ; BC = ποσότητα
        ld      e,(hl)
        inc     hl
        ld      d,(hl)
        dec     hl
        ld      a,e
        add     a,c
        ld      e,a
        ld      a,d
        adc     a,b
        ld      d,a
        ; DE > EC_CAP ;
        ld      a,d
        cp      EC_CAP / 256
        jr      c,ec_as_st
        jr      nz,ec_as_cap
        ld      a,e
        cp      EC_CAP & 255
        jr      c,ec_as_st
ec_as_cap:
        ld      de,EC_CAP
ec_as_st:
        ld      (hl),e
        inc     hl
        ld      (hl),d
        ret

; ec_stock_ptr — A = δείκτης -> DE = &stock[A]. Το HL μένει ανέπαφο.
ec_stock_ptr:
        push    hl
        ld      l,a
        ld      h,0
        add     hl,hl
        ld      de,EC_STOCK
        add     hl,de
        ex      de,hl
        pop     hl
        ret

; ec_add16 — (HL) += DE
ec_add16:
        ld      a,(hl)
        add     a,e
        ld      (hl),a
        inc     hl
        ld      a,(hl)
        adc     a,d
        ld      (hl),a
        ret

ed_p1:      dw 0                    ; οι τρεις δείκτες εισόδου, και οι ποσότητες
ed_q1:      db 0
ed_p2:      dw 0
ed_q2:      db 0
ed_p3:      dw 0
ed_q3:      db 0
ed_n:       db 0
ed_ops:     db 0
ed_slot:    db 0
ed_m:       db 0
ed_flags:   db 0
ed_green:   db 0

; ---------------------------------------------------------------------------
; econ_flow — θέση 12: παραγωγή απέναντι σε κατανάλωση, και η μπαταρία.
;
; Σαρώνει τις 64 δομές. Η κατανάλωση των ΜΗΧΑΝΩΝ δεν ξανασαρώνεται εδώ — τη
; μάζεψε η παραγωγή στο τελευταίο της σάρωμα. Αλλιώς αυτή η θέση θα κοίταζε
; 64 θόλους x 8 υποδοχές κάθε περιστροφή, για έναν αριθμό που ήδη υπάρχει.
; ---------------------------------------------------------------------------
econ_flow:
        ld      hl,0
        ld      (ef_prod),hl
        ld      (ef_cap),hl
        ld      (ef_wat),hl
        ld      (ef_ore),hl
        ld      hl,(EC_MPOWER)
        ld      (ef_use),hl

        ld      hl,G_struct_tbl
        ld      (ef_p),hl
        ld      a,MAX_STRUCT
        ld      (ef_cnt),a
ef_lp:
        ld      ix,(ef_p)
        ld      a,(ix+ST_STATE)
        cp      DS_ACTIVE
        jr      nz,ef_next
        ld      c,(ix+ST_SIZE)
        ld      b,0
        ld      a,(ix+ST_KIND)
        cp      K_SOLAR
        jr      z,ef_solar
        cp      K_TURBINE
        jr      z,ef_turb
        cp      K_COLLECT
        jr      z,ef_coll
        cp      K_EXTRACT
        jr      z,ef_extr
        cp      K_MINE
        jp      z,ef_mine
ef_next:
        ld      hl,(ef_p)
        ld      de,STRUCT_REC
        add     hl,de
        ld      (ef_p),hl
        ld      hl,ef_cnt
        dec     (hl)
        jr      nz,ef_lp
        jp      ef_battery

ef_solar:
        ld      a,(EC_STORM)            ; η σκόνη σκεπάζει τα πάνελ (§6.10)
        or      a
        jp      nz,ef_next
        ld      a,(EC_DAY)
        or      a
        jp      z,ef_next
        ld      hl,tab_solar
        add     hl,bc
        ld      e,(hl)
        ld      d,0
        ld      hl,ef_prod
        call    ec_add16
        jp      ef_next

ef_turb:
        ; παραγωγή = βάση * άνεμος / 3, ακέραια — όπως η αναφορά
        ld      hl,tab_turb
        add     hl,bc
        ld      c,(hl)
        ld      a,(EC_WIND)
        or      a                       ; ΟΧΙ `xor a / or b`: το or b γράφει το
        jr      z,ef_next               ; B μέσα στο A, δεν το δοκιμάζει μόνο
        ld      b,a
        xor     a
ef_t_mul:
        add     a,c
        djnz    ef_t_mul
        ld      c,0
ef_t_div:
        cp      3
        jr      c,ef_t_done
        sub     3
        inc     c
        jr      ef_t_div
ef_t_done:
        ld      e,c
        ld      d,0
        ld      hl,ef_prod
        call    ec_add16
        jr      ef_next

ef_coll:
        sla     c                       ; 16-bit πίνακας
        ld      hl,tab_coll
        add     hl,bc
        ld      e,(hl)
        inc     hl
        ld      d,(hl)
        ld      hl,ef_cap
        call    ec_add16
        jr      ef_next

ef_extr:
        push    bc
        ld      hl,tab_extr_pw
        add     hl,bc
        ld      e,(hl)
        ld      d,0
        ld      hl,ef_use
        call    ec_add16
        pop     bc
        ld      hl,tab_extr_out
        add     hl,bc
        ld      e,(hl)
        ld      d,0
        ld      hl,ef_wat
        call    ec_add16
        jp      ef_next

ef_mine:
        ld      de,8                    ; MINE_POWER
        ld      hl,ef_use
        call    ec_add16
        ld      de,20                   ; MINE_OUT
        ld      hl,ef_ore
        call    ec_add16
        jp      ef_next

ef_battery:
        ld      hl,(ef_prod)
        ld      (EC_PPROD),hl
        ld      hl,(ef_cap)
        ld      (EC_PCAP),hl
        ld      hl,(ef_use)
        ld      (EC_PUSE),hl

        ld      hl,(ef_prod)
        ld      de,(ef_use)
        or      a
        sbc     hl,de
        jr      c,ef_deficit
        ; πλεόνασμα: φορτίζει, ως το ταβάνι
        ld      de,(EC_PSTORE)
        add     hl,de
        ld      de,(ef_cap)
        push    hl
        or      a
        sbc     hl,de
        pop     hl
        jr      c,ef_ch_st
        ld      hl,(ef_cap)
ef_ch_st:
        ld      (EC_PSTORE),hl
        ld      a,1
        ld      (EC_POK),a
        jr      ef_pumps

ef_deficit:
        ld      hl,(ef_use)
        ld      de,(ef_prod)
        or      a
        sbc     hl,de                   ; HL = έλλειμμα
        ex      de,hl
        ld      hl,(EC_PSTORE)
        or      a
        sbc     hl,de
        jr      c,ef_blackout
        ld      (EC_PSTORE),hl
        ld      a,1
        ld      (EC_POK),a
        jr      ef_pumps
ef_blackout:
        ld      hl,0
        ld      (EC_PSTORE),hl
        xor     a
        ld      (EC_POK),a
        jr      ef_o2                   ; χωρίς ρεύμα δεν αντλεί κανείς

ef_pumps:
        ; Το νερό και το μετάλλευμα βγαίνουν από ΔΟΜΕΣ, όχι από μηχανές
        ; θόλου — αλλά βγαίνουν εδώ, και το §10.2 τα θέλει.
        ld      hl,(ef_wat)
        ld      a,h
        or      l
        jr      z,ef_pump2
        ld      a,S_WATER
        call    ec_mark
        ld      de,(ef_wat)
        ld      a,S_WATER
        call    ec_add_stock
ef_pump2:
        ld      hl,(ef_ore)
        ld      a,h
        or      l
        jr      z,ef_o2
        ld      a,S_ORE
        call    ec_mark
        ld      de,(ef_ore)
        ld      a,S_ORE
        call    ec_add_stock

ef_o2:
        ld      hl,G_agent_fields       ; η σελίδα των flags
        ld      b,128
        ld      c,0
ef_cnt_lp:
        ld      a,(hl)
        and     F_ALIVE
        jr      z,ef_cnt_n
        inc     c
ef_cnt_n:
        inc     l
        djnz    ef_cnt_lp

        ld      a,c
        ld      (EC_ALIVE),a
        or      a
        jr      nz,ef_alive
        ld      a,1
        ld      (EC_GAMEOVER),a         ; κανείς ζωντανός: τέλος (§10.3)
ef_alive:
        ld      l,c
        ld      h,0
        add     hl,hl                   ; O2_PER_COL = 2
        ld      (EC_O2USE),hl
        ex      de,hl                   ; DE = κατανάλωση
        ld      hl,(EC_O2PROD)
        or      a
        sbc     hl,de
        ld      a,0
        jr      c,ef_o2_st
        inc     a
ef_o2_st:
        ld      (EC_O2OK),a
        ret

; ---------------------------------------------------------------------------
; econ_events — θέση 15: μία ζαριά. Ρολόι, μέρα/νύχτα, άνεμος.
;
; Δική της γεννήτρια, ξεχωριστή από του κόσμου: ο κόσμος πρέπει να μένει
; αναπαράξιμος από το seed του και μόνο, ό,τι κι αν έκανε ο καιρός.
; ---------------------------------------------------------------------------
econ_events:
        ld      hl,(EC_FRAME)
        ld      de,16                   ; μία περιστροφή
        add     hl,de
        ld      de,(EC_SOLLEN)
        or      a
        sbc     hl,de
        jr      nc,ev_newsol
        add     hl,de
        xor     a
        ld      (ev_newday),a
        jr      ev_store
ev_newsol:
        ld      a,(EC_SOL)
        inc     a
        ld      (EC_SOL),a
        ld      a,1
        ld      (ev_newday),a
ev_store:
        ld      (EC_FRAME),hl
        ld      de,(EC_DAYLEN)
        or      a
        sbc     hl,de
        ld      a,0
        jr      nc,ev_night
        inc     a
ev_night:
        ld      (EC_DAY),a

        ld      a,(EC_GLOOM)            ; το πένθος περνάει, αργά
        or      a
        jr      z,ev_roll
        dec     a
        ld      (EC_GLOOM),a

        ; Τρεις ζαριές, ΠΑΝΤΑ. Μια ζαριά υπό όρους θα έκανε την ακολουθία να
        ; εξαρτάται από το αποτέλεσμα της προηγούμενης, και η αναπαραγωγή θα
        ; γινόταν δουλειά.
ev_roll:
        call    ev_rnd
        ld      (ev_r1),hl
        call    ev_rnd
        ld      (ev_r2),hl
        call    ev_rnd
        ld      (ev_r3),hl

        ld      hl,(ev_r1)              ; --- άνεμος ---
        ld      a,l
        and     15
        jr      nz,ev_storm
        ld      a,l
        rrca
        rrca
        rrca
        rrca
        and     3
        ld      (EC_WIND),a

ev_storm:                               ; --- αμμοθύελλα ---
        ld      a,(EC_STORM)
        or      a
        jr      z,ev_st_new
        dec     a
        ld      (EC_STORM),a
        jr      ev_fault
ev_st_new:
        ; Τα ΨΗΛΑ bits του δεύτερου. Ο Galois ολισθαίνει δεξιά, άρα δύο
        ; διαδοχικά τραβήγματα είναι το ίδιο νούμερο μετατοπισμένο: με δύο
        ; δοκιμές στα χαμηλά bits, θύελλα και βλάβη έπεφταν μαζί ή καθόλου.
        ld      hl,(ev_r2)
        ld      a,h
        and     #FE
        jr      nz,ev_fault
        ld      a,STORM_LEN
        ld      (EC_STORM),a

ev_fault:                               ; --- απλή βλάβη: χαμηλά του τρίτου ---
        ld      hl,(ev_r3)
        ld      a,l
        and     #1F
        jr      nz,ev_visit
        ld      hl,(ev_r3)
        ld      b,5
        call    ev_shr
        call    ec_break

ev_visit:                               ; --- απρόσκλητοι επισκέπτες (§6.11) ---
        ld      hl,(ev_r2)
        ld      a,l
        and     #3F
        jr      nz,ev_flare
        ld      a,SK_VISITOR
        call    ship_call

ev_flare:                               ; --- έκλαμψη: ψηλά του ίδιου ---
        ld      hl,(ev_r3)
        ld      a,h
        or      a
        jr      z,ev_fl_go
        jp      ev_after
ev_fl_go:
        ld      hl,(ev_r3)
        ld      de,37
        add     hl,de
        call    ec_break
        ld      hl,(ev_r3)
        ld      b,3
        call    ev_shr
        ld      de,101
        add     hl,de
        call    ec_break
        ld      hl,(ev_r3)
        ld      b,1
        call    ev_shr
        ld      de,173
        add     hl,de
        call    ec_break
        jp      ev_after

; ev_rnd — Galois, ίδιος με τη γεννήτρια κόσμου, ΞΕΧΩΡΙΣΤΗ κατάσταση.
ev_rnd:
        ld      hl,(EC_RND)
        ld      a,l
        srl     h
        rr      l
        and     1
        jr      z,ev_nox
        ld      a,h
        xor     #B4
        ld      h,a
ev_nox:
        ld      (EC_RND),hl
        ret

; ev_shr — HL >>= B
ev_shr:
        inc     b
        dec     b
        ret     z
ev_shr1:
        srl     h
        rr      l
        djnz    ev_shr1
        ret

; ---------------------------------------------------------------------------
; ec_break — HL = τυχαία τιμή. Μία μηχανή σταματά.
;
; Οχι «χαλάει λίγο»: υγεία μηδέν, και μένει εκεί ως να έρθει μηχανικός με ένα
; ανταλλακτικό. Ο πίνακας εργασιών δημοσιεύει την επισκευή μόνος του.
; ---------------------------------------------------------------------------
ec_break:
        ld      a,l
        and     63                      ; MAX_DOME - 1
        ld      (eb_d),a
        ld      b,6
        call    ev_shr
        ld      a,l
        ld      (eb_s),a

        ld      a,(eb_d)
        call    jb_dome_ptr
        push    hl
        ld      de,D_STATE
        add     hl,de
        ld      a,(hl)
        pop     hl
        cp      DS_ACTIVE
        ret     nz

        push    hl
        ld      de,D_SIZE
        add     hl,de
        ld      a,(hl)
        ld      hl,G_machine_count
        add     a,l
        ld      l,a
        ld      a,0
        adc     a,h
        ld      h,a
        ld      a,(hl)
        dec     a                       ; 1/4/8 -> μάσκα
        ld      c,a
        pop     hl
        ld      a,(eb_s)
        and     c
        ld      e,a
        ld      d,0

        push    hl
        ld      bc,D_MACH
        add     hl,bc
        add     hl,de
        ld      a,(hl)
        pop     hl
        cp      NO_MACH
        ret     z

        ld      bc,D_HEALTH
        add     hl,bc
        add     hl,de
        ld      a,(hl)
        or      a
        ret     z                       ; ήδη σταματημένη
        ld      (hl),0
        ret

ev_after:
        ld      a,(ev_newday)
        or      a
        call    nz,sol_rollover
        jp      ship_tick

ev_newday:  db 0
ev_r1:      dw 0
ev_r2:      dw 0
ev_r3:      dw 0
eb_d:       db 0
eb_s:       db 0

tab_solar:      db 2,8,18
tab_turb:       db 3,12,27
tab_coll:       dw 40,160,360
tab_extr_pw:    db 2,6,12
tab_extr_out:   db 6,24,54

ef_p:       dw 0
ef_prod:    dw 0
ef_cap:     dw 0
ef_use:     dw 0
ef_wat:     dw 0
ef_ore:     dw 0
ef_cnt:     db 0
