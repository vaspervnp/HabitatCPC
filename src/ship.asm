; ship.asm — πλοία, εμπόριο, ορόσημα (§6.11, §10.2)
;
; Ολα εδώ τρέχουν στη ΘΕΣΗ 15, πάνω στα συμβάντα: η θέση κόστιζε 200 us και ο
; τροχός δεν έχει άλλη ελεύθερη. Τα πλοία κινούνται μία φορά ανά περιστροφή
; και τα ορόσημα κρίνονται μία φορά ανά sol — καμία από τις δύο δεν είναι
; δουλειά που θέλει frame δικό της.
;
; ΤΟ ΜΗΚΟΣ ΤΟΥ SOL ΕΙΝΑΙ ΔΕΔΟΜΕΝΟ, ΟΧΙ ΣΤΑΘΕΡΑ. Ενα sol είναι 12.000 frames·
; μια δοκιμή που θέλει να δει πέντε από αυτά δεν μπορεί να περιμένει 60.000.

SHIP_NONE   equ 0
SHIP_INCOM  equ 1
SHIP_LANDED equ 2
SK_COLONIST equ 0
SK_MERCHANT equ 1
SK_VISITOR  equ 2
SHIP_TRIP   equ 24
SHIP_STAY   equ 8
SHIP_NCREW  equ 4
VIS_FOOD    equ 6
VIS_MORALE  equ 24
POP_PER_CTL equ 48
R_CONTROL   equ 1

M_FOOTHOLD  equ 1
M_INDUSTRY  equ 2
M_INDEPEND  equ 4
M_AUTOMAT   equ 8
M_HABITAT   equ 16

; ---------------------------------------------------------------------------
; ship_call — A = είδος. Επιστρέφει Cy=1 αν ξεκίνησε.
; ---------------------------------------------------------------------------
ship_call:
        ld      b,a
        ld      a,(EC_SHSTATE)
        or      a
        jr      nz,sc_no
        ld      a,(EC_PADNODE)
        cp      255
        jr      z,sc_no                 ; χωρίς πίστα, κανένα πλοίο
        ld      a,b
        ld      (EC_SHKIND),a
        ld      a,SHIP_INCOM
        ld      (EC_SHSTATE),a
        ld      hl,SHIP_TRIP
        ld      (EC_SHETA),hl
        scf
        ret
sc_no:
        or      a
        ret

; ---------------------------------------------------------------------------
; ship_tick — μία περιστροφή.
; ---------------------------------------------------------------------------
ship_tick:
        ld      a,(EC_SHSTATE)
        or      a
        ret     z
        ld      hl,(EC_SHETA)
        ld      a,h
        or      l
        jr      z,st_here
        dec     hl
        ld      (EC_SHETA),hl
        ret
st_here:
        ld      a,(EC_SHSTATE)
        cp      SHIP_INCOM
        jr      z,st_land
        xor     a                       ; έφυγε
        ld      (EC_SHSTATE),a
        ret
st_land:
        ld      a,SHIP_LANDED
        ld      (EC_SHSTATE),a
        ld      hl,SHIP_STAY
        ld      (EC_SHETA),hl
        ld      a,(EC_SHKIND)
        cp      SK_COLONIST
        jp      z,ship_crew
        cp      SK_VISITOR
        ret     nz
        ; --- επισκέπτες: τρώνε και ανεβάζουν το ηθικό ---
        ld      a,S_FOOD
        call    ec_stock_ptr            ; DE = &stock
        ld      a,(de)
        ld      l,a
        inc     de
        ld      a,(de)
        ld      h,a
        dec     de
        ld      bc,VIS_FOOD
        or      a
        sbc     hl,bc
        jr      nc,sv_pay
        ld      hl,0                    ; ό,τι είχαμε
sv_pay:
        ld      a,l
        ld      (de),a
        inc     de
        ld      a,h
        ld      (de),a

        ld      hl,G_agent_fields       ; σελίδα flags
        ld      b,128
        ld      c,0
sv_lp:
        ld      a,(hl)
        and     F_ALIVE
        jr      z,sv_n
        push    hl
        ld      a,l
        ld      h,AG_PG + 6
        ld      l,a
        set     7,l                     ; ηθικό
        ld      a,(hl)
        add     a,VIS_MORALE
        jr      nc,sv_st
        ld      a,255
sv_st:
        ld      (hl),a
        pop     hl
sv_n:
        inc     l
        djnz    sv_lp
        ret

; --- καινούργιοι άποικοι στην πίστα ----------------------------------------
ship_crew:
        ld      a,(EC_PADNODE)
        ld      (sh_node),a
        ld      b,128
        ld      c,0                     ; πόσοι μπήκαν
        ld      hl,G_agent_fields
sk_lp:
        ld      a,c
        cp      SHIP_NCREW
        ret     nc
        ld      a,(EC_ALIVE)
        add     a,c
        ld      e,a
        ld      a,(EC_POPCAP)
        cp      e
        ret     z
        jr      c,sk_full
        ld      a,(hl)
        and     F_ALIVE
        jr      nz,sk_n
        push    hl
        push    bc
        ld      a,l
        call    sh_born
        pop     bc
        pop     hl
        inc     c
sk_n:
        inc     l
        djnz    sk_lp
sk_full:
        ld      a,(EC_ALIVE)
        add     a,c
        ld      (EC_ALIVE),a
        ret

; sh_born — A = ταυτότητα. Γεννιέται στην πίστα, με γεμάτες μπάρες.
sh_born:
        ld      l,a
        ld      h,AG_PG
        ld      (hl),F_ALIVE
        ld      a,l
        and     7
        push    hl
        set     7,l
        ld      (hl),a                  ; ρόλος
        pop     hl
        ld      h,AG_PG + 1
        ld      a,(sh_node)
        ld      (hl),a                  ; κόμβος
        set     7,l
        ld      (hl),255                ; χωρίς θέση δαχτυλιδιού
        res     7,l
        ld      h,AG_PG + 2
        ld      (hl),a                  ; προορισμός = εδώ
        set     7,l
        ld      (hl),255                ; χωρίς ακμή
        res     7,l
        ld      h,AG_PG + 3
        ld      (hl),0                  ; πρόοδος
        set     7,l
        ld      (hl),255                ; χωρίς εργασία
        res     7,l
        ld      h,AG_PG + 4
        ld      (hl),200
        set     7,l
        ld      (hl),200
        res     7,l
        ld      h,AG_PG + 5
        ld      (hl),200
        set     7,l
        ld      (hl),200
        res     7,l
        ld      h,AG_PG + 6
        ld      (hl),200
        set     7,l
        ld      (hl),160
        ret

; ---------------------------------------------------------------------------
; sol_rollover — μία φορά ανά sol: τα σερί, και μετά τα ορόσημα (§10.2).
;
; Ολα τα μετρήματα γίνονται ΕΔΩ και όχι μέσα στα καυτά περάσματα: μία σάρωση
; 128 πρακτόρων ανά 750 περιστροφές δεν φαίνεται πουθενά.
; ---------------------------------------------------------------------------
sol_rollover:
        ; «όλα πράσινα» είναι η ένδειξη της ΑΠΟΙΚΙΑΣ, όχι η μπάρα κάθε ατόμου
        ld      a,(EC_O2OK)
        or      a
        jr      z,sr_notgreen
        ld      a,(EC_POK)
        or      a
        jr      z,sr_notgreen
        ld      hl,(EC_STOCK + 2*S_WATER)
        ld      a,h
        or      l
        jr      z,sr_notgreen
        ld      hl,(EC_STOCK + 2*S_FOOD)
        ld      a,h
        or      l
        jr      z,sr_notgreen
        ld      a,(EC_GREENS)
        inc     a
        jr      nz,sr_gst
        dec     a
sr_gst:
        ld      (EC_GREENS),a
        jr      sr_deaths
sr_notgreen:
        xor     a
        ld      (EC_GREENS),a

sr_deaths:
        ld      a,(EC_DEATHS)
        or      a
        jr      z,sr_nodeath
        xor     a
        ld      (EC_NODEATH),a
        jr      sr_dclr
sr_nodeath:
        ld      a,(EC_NODEATH)
        inc     a
        jr      nz,sr_nst
        dec     a
sr_nst:
        ld      (EC_NODEATH),a
sr_dclr:
        xor     a
        ld      (EC_DEATHS),a

        ld      a,(EC_TRADED)
        or      a
        jr      z,sr_notrade
        xor     a
        ld      (EC_NOTRADE),a
        jr      sr_tclr
sr_notrade:
        ld      a,(EC_NOTRADE)
        inc     a
        jr      nz,sr_tst
        dec     a
sr_tst:
        ld      (EC_NOTRADE),a
sr_tclr:
        xor     a
        ld      (EC_TRADED),a

        ; --- πόσα ρομπότ δουλεύουν ---
        ld      hl,G_agent_fields
        ld      b,128
        ld      c,0
sr_bots:
        ld      a,(hl)
        and     F_ALIVE
        jr      z,sr_bn
        ld      a,(hl)
        and     F_WORKING
        jr      z,sr_bn
        push    hl
        ld      a,l
        ld      h,AG_PG
        ld      l,a
        set     7,l
        ld      a,(hl)                  ; ρόλος
        pop     hl
        cp      5
        jr      c,sr_bn
        inc     c
sr_bn:
        inc     l
        djnz    sr_bots
        ld      a,c
        ld      (sh_bots),a

        ; --- τα ορόσημα, και δεν σβήνουν ποτέ ---
        ; Ο συσσωρευτής ζει στη ΜΝΗΜΗ και όχι στο B: το sh_allmade χρησιμοποιεί
        ; το B ως μετρητή ολίσθησης, και η πρώτη γραφή έχτιζε τις σημαίες πάνω
        ; σε ό,τι είχε αφήσει εκείνο.
        ld      a,(EC_MILE)
        ld      (sh_mile),a

        ld      a,(EC_ALIVE)
        cp      10
        jr      c,sr_m2
        ld      a,(EC_GREENS)
        or      a
        jr      z,sr_m2
        ld      a,M_FOOTHOLD
        call    sh_set
sr_m2:
        ld      hl,ind_stocks           ; μέταλλο, βιοπλαστικό, ανταλλακτικά
        ld      c,3
        call    sh_allmade
        jr      nc,sr_m3
        ld      a,M_INDUSTRY
        call    sh_set
sr_m3:
        ld      hl,dep_stocks           ; και τα δέκα αγαθά
        ld      c,10
        call    sh_allmade
        jr      nc,sr_m4
        ld      a,(EC_NOTRADE)
        cp      5
        jr      c,sr_m4
        ld      a,M_INDEPEND
        call    sh_set
sr_m4:
        ld      a,(sh_bots)
        cp      8
        jr      c,sr_m5
        ld      a,M_AUTOMAT
        call    sh_set
sr_m5:
        ld      a,(sh_mile)
        and     M_INDEPEND
        jr      z,sr_done
        ld      a,(EC_ALIVE)
        cp      80
        jr      c,sr_done
        ld      a,(EC_NODEATH)
        cp      5
        jr      c,sr_done
        ld      a,M_HABITAT
        call    sh_set
sr_done:
        ld      a,(sh_mile)
        ld      (EC_MILE),a
        ret

; sh_set — A = σημαία ορόσημου
sh_set:
        ld      hl,sh_mile
        or      (hl)
        ld      (hl),a
        ret

; sh_allmade — HL = λίστα δεικτών, C = πλήθος. Cy=1 αν όλα φτιάχτηκαν εδώ.
sh_allmade:
        ld      de,(EC_PRODM)
sa_lp:
        ld      a,(hl)
        inc     hl
        push    hl
        push    de
        ld      b,a
        ld      hl,1
        inc     b
sa_sh:
        dec     b
        jr      z,sa_test
        add     hl,hl
        jr      sa_sh
sa_test:
        ld      a,h
        and     d
        ld      b,a
        ld      a,l
        and     e
        or      b
        pop     de
        pop     hl
        jr      z,sa_no
        dec     c
        jr      nz,sa_lp
        scf
        ret
sa_no:
        or      a
        ret

ind_stocks: db 3,4,6                    ; μέταλλο, βιοπλαστικό, ανταλλακτικά
dep_stocks: db 0,1,2,3,4,5,6,7,8,9
sh_node:    db 0
sh_bots:    db 0
sh_mile:    db 0
