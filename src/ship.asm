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
; το R_CONTROL είναι στο const.asm

; τα πέντε ορόσημα του §10.2: το bit μέσα στο EC_MILE
MB_FOOTHOLD equ 0
MB_INDUSTRY equ 1
MB_INDEPEND equ 2
MB_AUTOMAT  equ 3
MB_HABITAT  equ 4

; ΤΑ ΑΓΑΘΑ ΤΩΝ ΟΡΟΣΗΜΩΝ ως μάσκες του EC_PRODM, που έχει ένα bit ανά απόθεμα
; (ec_make). Βιομηχανία: μέταλλο, βιοπλαστικό, ανταλλακτικά. Ανεξαρτησία: τα
; δέκα αγαθά του §6.5, αποθέματα 0-9 — όλο το κάτω byte και δύο bits του πάνω.
; Ως το βήμα 57 δύο λίστες και ένας βρόχος που έφτιαχνε το bit κάθε φορά.
IND_MASK    equ (1 << S_METAL) | (1 << S_BIOPL) | (1 << S_SPARE)
DEP_MASK    equ (1 << 10) - 1
        assert  IND_MASK < 256 && (DEP_MASK & 255) == 255

        assert  EC_SHKIND == EC_SHSTATE + 1
        assert  EC_NODEATH == EC_DEATHS + 1 && EC_GREENS == EC_NODEATH + 1
        assert  EC_NOTRADE == EC_GREENS + 1 && EC_TRADED == EC_NOTRADE + 1
        assert  SHIP_LANDED == 2 * SHIP_INCOM && ((2 * SHIP_LANDED) & 3) == SHIP_NONE
        assert  SK_COLONIST == 0 && VIS_FOOD < 256
        assert  (G_agent_fields & 255) == 0     ; AG_PG: η σελίδα των σημαιών

; ---------------------------------------------------------------------------
; ship_call — A = είδος. Επιστρέφει Cy=1 αν ξεκίνησε.
; ---------------------------------------------------------------------------
ship_call:
        ld      b,a
        ld      a,(EC_SHSTATE)
        or      a
        jr      nz,sc_no
        ld      a,(EC_PADNODE)
        inc     a
        jr      z,sc_no                 ; 255: χωρίς πίστα, κανένα πλοίο
        ld      h,b
        ld      l,SHIP_INCOM
        ld      (EC_SHSTATE),hl         ; EC_SHSTATE, EC_SHKIND
        ld      hl,SHIP_TRIP
        ld      (EC_SHETA),hl
        scf
        ret
sc_no:
        or      a                       ; και από τους δύο δρόμους: CY = 0
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
        ld      hl,EC_SHSTATE
        ld      a,(hl)
        add     a,a                     ; ΕΡΧΕΤΑΙ -> ΠΡΟΣΓΕΙΩΜΕΝΟ, και
        and     3                       ; ΠΡΟΣΓΕΙΩΜΕΝΟ -> ΤΙΠΟΤΑ: έφυγε
        ld      (hl),a
        ret     z
        ld      a,SFX_SHIP
        call    snd_ping
        ld      hl,SHIP_STAY
        ld      (EC_SHETA),hl
        ld      a,(EC_SHKIND)
        or      a                       ; SK_COLONIST
        jr      z,ship_crew
        cp      SK_VISITOR
        ret     nz
        ; --- επισκέπτες: τρώνε και ανεβάζουν το ηθικό ---
        ld      hl,(EC_STOCK + 2*S_FOOD)
        ld      bc,VIS_FOOD
        or      a
        sbc     hl,bc
        jr      nc,sv_pay
        ld      h,b                     ; ό,τι είχαμε: 0
        ld      l,b
sv_pay:
        ld      (EC_STOCK + 2*S_FOOD),hl
        ld      hl,G_agent_fields       ; σελίδα flags
        ld      b,128
sv_lp:
        ld      a,(hl)
        and     F_ALIVE
        jr      z,sv_n
        push    hl
        ld      h,AG_PG + 6
        set     7,l                     ; ηθικό
        ld      a,(hl)
        add     a,VIS_MORALE
        jr      nc,sv_st
        sbc     a,a                     ; 255
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
        ld      (sb_tab),a              ; κόμβος και προορισμός: η πίστα
        ld      (sb_tab + 2),a
        ld      bc,128*256 + SHIP_NCREW ; B = θέσεις, C = όσοι χωράνε ακόμη
        ld      hl,G_agent_fields
sk_lp:
        ; ΤΟ EC_ALIVE ΜΕΤΡΑΕΙ ΚΑΘΕ ΓΕΝΝΗΣΗ ΑΜΕΣΩΣ, οπότε κάθε έξοδος το βρίσκει
        ; σωστό. Ως το βήμα 38 το πλήρες πλήρωμα και το ταβάνι ακριβώς γεμάτο
        ; έβγαιναν με RET πριν από την πρόσθεση, και οι τέσσερις καινούργιοι
        ; δεν μετρούσαν στο EC_ALIVE ως την επόμενη μέτρηση της θέσης 12. Το
        ; έδειξε ο τροχός καρφωμένος στη θέση 15 (tests/test_sim.py, άκρες).
        ld      a,(EC_POPCAP)
        ld      e,a
        ld      a,(EC_ALIVE)
        cp      e
        ret     nc                      ; το ταβάνι
        ld      a,(hl)
        and     F_ALIVE
        jr      nz,sk_n
        push    hl
        push    bc
        ld      a,l
        call    sh_born
        ld      hl,EC_ALIVE
        inc     (hl)
        pop     bc
        pop     hl
        dec     c
        ret     z                       ; όλο το πλήρωμα
sk_n:
        inc     l
        djnz    sk_lp
        ret

; sh_born — A = ταυτότητα. Γεννιέται στην πίστα, με γεμάτες μπάρες: σημαίες
; και ρόλος στη σελίδα AG_PG, και οι σελίδες +1..+6 από το sb_tab, κάτω μισό
; και πάνω μισό (set 7,l) η καθεμία.
sh_born:
        ld      l,a
        ld      h,AG_PG
        ld      (hl),F_ALIVE
        and     7
        set     7,l
        ld      (hl),a                  ; ρόλος
        ld      de,sb_tab
        ld      b,6
sb_lp:
        inc     h
        res     7,l
        ld      a,(de)
        ld      (hl),a
        inc     de
        set     7,l
        ld      a,(de)
        ld      (hl),a
        inc     de
        djnz    sb_lp
        ret

; κόμβος, θέση δακτυλιδιού · προορισμός, ακμή · πρόοδος, εργασία · οξυγόνο,
; νερό · τροφή, ύπνος · υγεία, ηθικό. Τον κόμβο και τον προορισμό τους γράφει
; το ship_crew.
sb_tab:     db 0, 255, 0, 255, 0, 255, 200, 200, 200, 200, 200, 160

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
        jr      z,sr_grey
        ld      a,(EC_POK)
        cp      P_ALL                   ; P_ESS δεν είναι πράσινο sol: οι
        jr      nz,sr_green             ; μηχανές της αποικίας σταμάτησαν
        ld      hl,(EC_STOCK + 2*S_WATER)
        ld      a,h
        or      l
        jr      z,sr_grey
        ld      hl,(EC_STOCK + 2*S_FOOD)
        ld      a,h
        or      l
        jr      z,sr_grey
        xor     a                       ; Z: πράσινο
        jr      sr_green
sr_grey:
        or      1                       ; NZ: το σερί σπάει
sr_green:
        ld      hl,EC_GREENS
        call    sr_streak
        ; --- θάνατοι και εμπόριο του sol: σπάνε το δικό τους σερί, και
        ; μηδενίζονται για το επόμενο ---
        ld      hl,EC_DEATHS
        ld      a,(hl)
        ld      (hl),0
        or      a
        inc     hl                      ; EC_NODEATH
        call    sr_streak
        ld      hl,EC_TRADED
        ld      a,(hl)
        ld      (hl),0
        or      a
        dec     hl                      ; EC_NOTRADE
        call    sr_streak

        ; --- πόσα ρομπότ δουλεύουν: ζωντανά, στη θέση εργασίας, ρόλος 5+ ---
        ld      hl,G_agent_fields
        ld      bc,128*256 + 0
sr_bots:
        ld      a,(hl)
        and     F_ALIVE + F_WORKING
        cp      F_ALIVE + F_WORKING
        jr      nz,sr_bn
        set     7,l
        ld      a,(hl)                  ; ρόλος
        res     7,l
        cp      5
        jr      c,sr_bn
        inc     c
sr_bn:
        inc     l
        djnz    sr_bots

        ; --- τα ορόσημα, κατευθείαν στο EC_MILE, και δεν σβήνουν ποτέ ---
        ld      hl,EC_MILE
        ld      a,c
        cp      8
        jr      c,sr_m1
        set     MB_AUTOMAT,(hl)
sr_m1:
        ld      a,(EC_ALIVE)
        cp      10
        jr      c,sr_m2
        ld      a,(EC_GREENS)
        or      a
        jr      z,sr_m2
        set     MB_FOOTHOLD,(hl)
sr_m2:
        ld      a,(EC_PRODM)
        and     IND_MASK
        cp      IND_MASK
        jr      nz,sr_m3
        set     MB_INDUSTRY,(hl)
sr_m3:
        ld      de,(EC_PRODM)
        ld      a,d
        or      255 - (DEP_MASK >> 8)   ; τα αγαθά 8, 9 — τα άλλα bits ένα
        and     e                       ; και τα 0-7
        inc     a                       ; όλα ένα: 255 -> 0
        jr      nz,sr_m4
        ld      a,(EC_NOTRADE)
        cp      5
        jr      c,sr_m4
        set     MB_INDEPEND,(hl)
sr_m4:
        bit     MB_INDEPEND,(hl)        ; και αυτού του sol
        ret     z
        ld      a,(EC_ALIVE)
        cp      80
        ret     c
        ld      a,(EC_NODEATH)
        cp      5
        ret     c
        set     MB_HABITAT,(hl)
        ret

; sr_streak — το σερί στο (HL): Z συνεχίζει (+1, ως το 255), NZ σπάει (0).
sr_streak:
        ld      a,0
        jr      nz,srs_st
        ld      a,(hl)
        inc     a
        jr      nz,srs_st
        dec     a
srs_st:
        ld      (hl),a
        ret
