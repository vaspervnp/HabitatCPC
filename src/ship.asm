; ship.asm — πλοία, εμπόριο, ορόσημα (§6.11, §10.2)
;
; Ολα εδώ τρέχουν στη ΘΕΣΗ 15, πάνω στα συμβάντα: η θέση κόστιζε 200 us και ο
; τροχός δεν έχει άλλη ελεύθερη. Τα πλοία κινούνται μία φορά ανά περιστροφή
; και τα ορόσημα κρίνονται μία φορά ανά sol — καμία από τις δύο δεν είναι
; δουλειά που θέλει frame δικό της.
;
; ΤΟ ΜΗΚΟΣ ΤΟΥ SOL ΕΙΝΑΙ ΔΕΔΟΜΕΝΟ, ΟΧΙ ΣΤΑΘΕΡΑ. Ενα sol είναι 12.000 frames·
; μια δοκιμή που θέλει να δει πέντε από αυτά δεν μπορεί να περιμένει 60.000.
;
; ΖΕΙ ΣΤΗΝ ΤΡΑΠΕΖΑ 6 από το βήμα 93, στη δέσμευση b6code μαζί με τα ρομπότ
; (src/bots.asm): ό,τι είναι εδώ το καλεί μόνο η θέση 15, που έχει την 6 στο
; παράθυρο. Η τράπεζα 0 είχε 28 bytes ως το πάτωμα των δοκιμών και το εμπόριο
; ήθελε εκατοντάδες. Το ship_call, που το καλεί και το κουμπί του πλοίου, έμεινε
; στην τράπεζα 0, δίπλα στο econ_events (src/econ.asm).

; οι καταστάσεις και τα είδη των πλοίων είναι στο const.asm (βήμα 93)
SHIP_TRIP   equ 24
SHIP_STAY   equ 8
SHIP_NCREW  equ 4
VIS_MORALE  equ 24
; ΕΠΙΣΚΕΠΤΕΣ ΠΟΥ ΠΛΗΡΩΝΟΥΝ (βήμα 134, tools/econ.py): VIS_BASE + κύρος/64 ανά
; πλοίο· με κυλικείο, τρόφιμο και νερό ο καθένας τρώει, πίνει και δίνει
; COIN_MEAL, και COIN_FUN ακόμη αν η αποικία έχει σαλόνι ή δέντρα. Ως το βήμα
; 133 το πλοίο έτρωγε έξι τρόφιμα (VIS_FOOD) και δεν έδινε τίποτα. Από το 136
; τα ίδια, εκεί όπου περπατούν: src/visit.asm.
VIS_BASE    equ 2
COIN_MEAL   equ 5
COIN_FUN    equ 3
GOOD_UP     equ 3
GOOD_DOWN   equ 6
GOOD_MAX    equ 100
POP_PER_CTL equ 48
POP_BASE    equ 6                       ; το πλήρωμα του σκάφους (βήμα 120· ως τότε 4)
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
        assert  SK_COLONIST == 0 && COIN_MEAL + COIN_FUN < 256 && MER_COIN == 5
        assert  (G_agent_fields & 255) == 0     ; AG_PG: η σελίδα των σημαιών

; ---------------------------------------------------------------------------
; ship_tick — μία περιστροφή.
; ---------------------------------------------------------------------------
ship_tick:
        ld      a,(EC_SHSTATE)
        or      a
        ret     z
        ; ΟΙ ΕΠΙΣΚΕΠΤΕΣ ΠΕΡΠΑΤΟΥΝ (βήμα 136, src/visit.asm) όσο είναι
        ; προσγειωμένο το πλοίο τους: αυτή είναι η πύλη τους. Χωρίς πλοίο η
        ; θέση δεν πληρώνει τίποτα, με πλοίο που έρχεται 19 T, με άλλο
        ; προσγειωμένο 44. (Η πρώτη γραφή, μία σύγκριση 16 bits, ήταν 51 T και
        ; για το πλοίο που έρχεται, το συνηθέστερο: η θέση 15 του
        ; tests/test_sim.py πέρασε τα 500 us.)
        cp      SHIP_LANDED
        jr      nz,st_eta
        ld      a,(EC_SHKIND)
        cp      SK_VISITOR
        call    z,vi_tick
st_eta:
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
        and     3                       ; ΠΡΟΣΓΕΙΩΜΕΝΟ -> ΤΙΠΟΤΑ: έφυγε, και
        ld      (hl),a                  ; όσοι επισκέπτες δεν γύρισαν μαζί του
        jp      z,vi_gone               ; (βήμα 136, src/visit.asm)
        ld      a,SFX_SHIP
        call    snd_ping
        ld      hl,SHIP_STAY
        ld      (EC_SHETA),hl
        ; ΜΕΤΡΑΝΕ ΟΛΕΣ ΟΙ ΠΡΟΣΓΕΙΩΣΕΙΣ (βήμα 111, η απόφαση του παίκτη):
        ; άποικοι, επισκέπτες, έμποροι, ως το 255. Των εισβολέων το μηδενίζει.
        ld      a,(EC_SHKIND)
        cp      SK_FOE
        jp      z,fo_land               ; src/foe.asm
        ld      hl,EC_LANDS
        inc     (hl)
        jr      nz,st_disp
        dec     (hl)
st_disp:
        ld      a,(EC_SHKIND)
        or      a                       ; SK_COLONIST
        jp      z,ship_crew             ; jp από το βήμα 134: τα νομίσματα στη μέση
        cp      SK_VISITOR
        jp      nz,sm_land              ; ο έμπορος (βήμα 93), πιο κάτω
        ; --- ΕΠΙΣΚΕΠΤΕΣ (βήμα 136): κατεβαίνουν στην πίστα και περπατούν ως
        ; το κυλικείο και το σαλόνι (src/visit.asm), και πληρώνουν εκεί. Ως το
        ; 135 έτρωγαν και πλήρωναν εδώ, όλοι μαζί, τη στιγμή της προσγείωσης.
        call    vi_land
        ; --- και ανεβάζουν το ηθικό, όπως πριν ---
        ld      hl,G_agent_fields       ; σελίδα flags
        ld      b,AG_BOT0               ; οι άποικοι: τα ρομπότ δεν έχουν ηθικό
sv_lp:                                  ; (ως το βήμα 93 και οι 128)
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
        jp      sm_stay                 ; και μένει ως μισό sol, όπως ο έμπορος

; vs_coins — HL = τα νομίσματα (βήμα 134). Για το HUD, με το hd_b6.
vs_coins:
        ld      hl,(EC_COINS)
        ret

; --- καινούργιοι άποικοι στην πίστα ----------------------------------------
ship_crew:
        call    cw_count                ; ποιοι ζουν, ανά ειδικότητα (src/crew.asm)
        ld      l,a                     ; ο πρώτος νεκρός: από εκεί, όχι από το 0
        sub     AG_BOT0
        ret     nc                      ; οι 80 θέσεις αποίκων γεμάτες (βήμα 92)
        neg
        ld      b,a                     ; B = θέσεις ως το 79
        ld      c,SHIP_NCREW            ; C = όσοι χωράνε ακόμη
        ld      h,AG_PG
        ld      a,(EC_PADNODE)
        ld      (sb_tab),a              ; κόμβος και προορισμός: η πίστα
        ld      (sb_tab + 2),a
sk_cap:
        ; ΤΟ EC_ALIVE ΜΕΤΡΑΕΙ ΚΑΘΕ ΓΕΝΝΗΣΗ ΑΜΕΣΩΣ, οπότε κάθε έξοδος το βρίσκει
        ; σωστό. Ως το βήμα 38 το πλήρες πλήρωμα και το ταβάνι ακριβώς γεμάτο
        ; έβγαιναν με RET πριν από την πρόσθεση, και οι τέσσερις καινούργιοι
        ; δεν μετρούσαν στο EC_ALIVE ως την επόμενη μέτρηση της θέσης 12. Το
        ; έδειξε ο τροχός καρφωμένος στη θέση 15 (tests/test_sim.py, άκρες).
        ;
        ; ΤΟ ΤΑΒΑΝΙ ΜΟΝΟ ΜΕΤΑ ΑΠΟ ΓΕΝΝΗΣΗ (βήμα 89): μόνο τότε αλλάζει. Ως τότε
        ; το ρωτούσε κάθε ένας από τους 128 πριν από τον πρώτο ελεύθερο, 12 us
        ; ο καθένας — περισσότερα από όσα κοστίζει η θέση που παίρνει τώρα ο
        ; καινούργιος στην πίστα (sh_born).
        ld      a,(EC_POPCAP)
        ld      e,a
        ld      a,(EC_ALIVE)
        cp      e
        ret     nc                      ; το ταβάνι
sk_lp:
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
        inc     l
        djnz    sk_cap
        ret
sk_n:
        inc     l
        djnz    sk_lp
        ret

; sh_born — A = ταυτότητα. Γεννιέται στην πίστα, με γεμάτες μπάρες: σημαίες
; και ρόλος στη σελίδα AG_PG, και οι σελίδες +1..+7 από το sb_tab, κάτω μισό
; και πάνω μισό (set 7,l) η καθεμία — η +7 από το βήμα 90: στολή, φορτίο.
sh_born:
        ld      l,a
        ld      h,AG_PG
        ld      (hl),F_ALIVE
        set     7,l
        call    cw_pick                 ; η ειδικότητα που λείπει (βήμα 91·
        ld      (hl),a                  ; ως τότε id & 7, και ρομπότ)
; sb_rest — H = AG_PG, L = ταυτότητα (το bit 7 δεν μετρά): ό,τι μένει μετά από
; σημαίες και ρόλο. Τα ρομπότ του src/bots.asm γράφουν τα δύο δικά τους και
; μπαίνουν εδώ (βήμα 92) — και ο άποικος περνά από τις ίδιες εντολές με το 91.
sb_rest:
        ld      de,sb_tab
        ld      b,7
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
        ; ΘΕΣΗ ΣΤΗΝ ΠΙΣΤΑ (βήμα 89), όπως σε κάθε άφιξη (em_arrive): ως τότε
        ; γεννιόταν χωρίς, και μια φιγούρα έξω στέκεται στη θέση της.
        res     7,l
        push    hl
        ld      a,(sb_tab)              ; ο κόμβος: η πίστα
        call    ent_claim
        pop     hl
        ld      h,AG_PG + 1
        set     7,l
        ld      (hl),a                  ; η θέση, ή NO_SLOT αν γέμισε
        jp      fg_mark                 ; φαίνεται στην πίστα

; κόμβος, θέση δακτυλιδιού · προορισμός, ακμή · πρόοδος, εργασία · οξυγόνο,
; νερό · τροφή, ύπνος · υγεία, ηθικό · στολή, φορτίο. Τον κόμβο και τον προορισμό τους γράφει
; το ship_crew, ή το bot_tick (βήμα 92)· τη θέση την ξαναγράφει το ent_claim (βήμα 89).
sb_tab:     db 0, 255, 0, 255, 0, 255, 200, 200, 200, 200, 200, 160
            db SUIT_TRIP, 0             ; στολή, φορτίο (βήμα 90): κατεβαίνει έξω

; ag_land — HL = η πρώτη θέση (σημαίες), B = θέσεις, C = πόσοι, D = ρόλος,
; E = εργασία: C καινούργιοι έξω, στην πίστα, στις πρώτες ελεύθερες από τις B,
; γεννημένοι όπως ο άποικος (sb_rest), με την εργασία τους και υγεία FOE_HP.
; Οι εισβολείς (βήμα 111, fo_land), και από το βήμα 136 οι επισκέπτες
; (vi_land), για τους οποίους το FOE_HP είναι η φάση VP_EAT.
ag_land:
        ld      a,(EC_PADNODE)
        ld      (sb_tab),a              ; κόμβος και προορισμός: η πίστα
        ld      (sb_tab + 2),a
agl_lp:
        bit     0,(hl)                  ; F_ALIVE
        jr      nz,agl_nx
        push    bc
        push    de
        push    hl
        ld      (hl),F_ALIVE            ; έξω
        set     7,l
        ld      (hl),d
        call    sb_rest
        pop     hl
        pop     de
        push    de
        push    hl
        ld      h,AG_PG + 3
        set     7,l
        ld      (hl),e                  ; η εργασία
        ld      h,AG_PG + 6
        res     7,l
        ld      (hl),FOE_HP             ; η υγεία
        pop     hl
        pop     de
        pop     bc
        dec     c
        ret     z
agl_nx:
        inc     l
        djnz    agl_lp
        ret

; --- ο έμπορος (βήμα 93): το φορτίο του, και μένει μισό sol ----------------
; ΟΠΩΣ ΣΤΟ PLANETBASE: τρία ή τέσσερα αγαθά, άλλα κάθε φορά, 1-4 μονάδες από
; το καθένα (tr_lot, src/stock.asm), και το κέρδος του, 35-65%. Τρία bytes από
; ΔΙΚΑ τους βήματα του Galois, οκτώ ανά byte, με σπόρο το EC_RND — που δεν
; αλλάζει: η ακολουθία των συμβάντων μένει ίδια, με ή χωρίς έμπορο (όπως η
; βροχή μετεωριτών, src/meteor.asm).
;   1ο   κέρδος: τα 5 κάτω bits, mod 31 · τέσσερα αγαθά αν το bit 5 · και
;        από το βήμα 135 τα νομίσματα που φέρνει: τα bits 6-7, x 50
;   2ο   το πρώτο αγαθό: τα 4 κάτω, mod 13 · το βήμα: τα 4 πάνω, mod 12, + 1
;   3ο   οι μονάδες, δύο bits ανά αγαθό
; Το 13 είναι πρώτος: t, t + d, t + 2d, t + 3d (mod 13) διαφέρουν πάντα.
; tools/econ.py: land_merchant.
sm_land:
        ld      hl,EC_CARGO             ; οι κενές θέσεις μένουν 0
        ld      b,2 * MER_SLOTS
sml_z:  ld      (hl),0
        inc     hl
        djnz    sml_z
        ld      hl,(EC_RND)
        call    sm_byte
        ld      d,a                     ; D = το πρώτο
        call    sm_byte
        ld      e,a                     ; E = το δεύτερο
        call    sm_byte
        ld      c,a                     ; C = οι μονάδες
        ld      a,d
        and     31
        cp      31
        jr      c,sml_m
        xor     a                       ; 31 mod 31
sml_m:  add     a,MARKUP_MIN
        ld      (EC_MARKUP),a
        ld      a,d                     ; ΚΑΙ ΝΟΜΙΣΜΑΤΑ (βήμα 135): τα bits 6-7,
        rlca                            ; 0-3 παρτίδες των 50 — ένας στους
        rlca                            ; τέσσερις δεν φέρνει
        and     3
        ld      b,a
        add     a,a
        add     a,a
        add     a,b                     ; x MER_COIN, σε δεκάδες
        ld      (EC_MCOIN),a
        ld      b,3
        bit     5,d
        jr      z,sml_k
        inc     b                       ; B = πόσα
sml_k:  ld      a,e
        rrca
        rrca
        rrca
        rrca
        and     15
        cp      12
        jr      c,sml_d
        sub     12
sml_d:  inc     a
        ld      d,a                     ; D = το βήμα, 1-12
        ld      a,e
        and     15
        cp      TRADE_N
        jr      c,sml_t
        sub     TRADE_N
sml_t:  ld      e,a                     ; E = t, 0-12
        ld      hl,EC_CARGO
sml_lp:
        ld      a,e
        inc     a                       ; το απόθεμα: 1 + t
        ld      (hl),a
        inc     hl
        push    hl
        ld      hl,tr_lot               ; (το ob_addu δεν υπάρχει στο simtest)
        add     a,l
        ld      l,a
        jr      nc,sml_l
        inc     h
sml_l:  ld      a,(hl)                  ; η μονάδα του
        pop     hl
        push    bc
        ld      b,a
        ld      a,c
        and     3
        ld      c,a                     ; C = 0-3: 1-4 μονάδες
        ld      a,b
sml_q:  dec     c
        jp      m,sml_qd
        add     a,b
        jr      sml_q
sml_qd: pop     bc
        ld      (hl),a                  ; η ποσότητα
        inc     hl
        srl     c
        srl     c
        ld      a,e
        add     a,d                     ; t += d, mod 13
        cp      TRADE_N
        jr      c,sml_n
        sub     TRADE_N
sml_n:  ld      e,a
        djnz    sml_lp
        ; ΜΙΣΟ SOL, ΟΧΙ SHIP_STAY: οκτώ περιστροφές είναι 2,6 δευτερόλεπτα, και
        ; η ανταλλαγή θέλει χρόνο. Από το μήκος του sol, που είναι δεδομένο: 32
        ; = 16 frames ανά περιστροφή x 2. Και του πλοίου επισκεπτών (βήμα
        ; 136), που φεύγει νωρίτερα αν ανέβουν όλοι (vi_tick).
sm_stay:
        ld      hl,(EC_SOLLEN)
        ld      b,5
sml_h:  srl     h
        rr      l
        djnz    sml_h
        ld      (EC_SHETA),hl
        ret

; sm_byte — HL = κατάσταση: οκτώ βήματα του Galois, A = το κάτω byte.
sm_byte:
        ld      b,8
smb_lp: call    lfsr_hl                 ; src/econ.asm, τράπεζα 0: χαλάει το A
        djnz    smb_lp
        ld      a,l
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

        ; --- πόσα ρομπότ ζουν: οι δεκαέξι θέσεις τους (βήμα 92) ---
        ; Ως το 91 «δουλεύουν»: ζωντανά, με F_WORKING και ρόλο 5+. Το F_WORKING
        ; όμως το βάζει μόνο ο χειριστής, ο γιατρός και ο φρουρός (src/jobs.asm),
        ; και καμία από αυτές τις εργασίες δεν την παίρνει ρομπότ: το ορόσημο
        ; δεν πιανόταν ποτέ, ούτε όταν τα έφερναν τα πλοία. Ο παίκτης διάλεξε
        ; «οκτώ ζωντανά ρομπότ».
        ld      hl,G_agent_fields + AG_BOT0
        ld      bc,AG_NBOT * 256 + 0
sr_bots:
        ld      a,(hl)
        and     F_ALIVE
        add     a,c
        ld      c,a
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
        jr      z,sr_pres
        ld      a,(EC_ALIVE)
        cp      80
        jr      c,sr_pres
        ld      a,(EC_NODEATH)
        cp      5
        jr      c,sr_pres
        set     MB_HABITAT,(hl)

        ; --- ΤΟ ΚΥΡΟΣ (βήμα 134, tools/econ.py): 10 ανά ορόσημο, οι μισοί
        ; ζωντανοί, το σερί χωρίς θάνατο ως το 30, 5 ανά σαλόνι ή δέντρο ως τα
        ; έξι, και η εύνοια, που πρώτα σβήνει κατά ένα. Ως 250. ---
sr_pres:
        ld      hl,EC_GOOD
        ld      a,(hl)
        or      a
        jr      z,srp_g
        dec     (hl)
srp_g:  ld      a,(EC_MILE)
        ld      c,0
srp_m:  or      a
        jr      z,srp_al
        srl     a
        jr      nc,srp_m
        ld      d,a
        ld      a,c
        add     a,10
        ld      c,a
        ld      a,d
        jr      srp_m
srp_al: ld      a,(EC_ALIVE)
        srl     a
        add     a,c
        ld      c,a
        ld      a,(EC_NODEATH)
        cp      30
        jr      c,srp_nd
        ld      a,30
srp_nd: add     a,c
        ld      c,a
        ld      a,(EC_AMENITY)
        cp      6
        jr      c,srp_am
        ld      a,6
srp_am: ld      b,a
        add     a,a
        add     a,a
        add     a,b                     ; x5
        add     a,c
        add     a,(hl)                  ; + η εύνοια (HL = EC_GOOD)
        ld      (EC_PREST),a
        ; --- και ο συσσωρευτής: πάνω από 255, πλοίο επισκεπτών — ή εισβολέων,
        ; όπως η ζαριά. Αν δεν έρθει, μένει στο 255 και ξαναδοκιμάζει. ---
        ld      hl,EC_VISACC
        add     a,(hl)
        jr      nc,srp_st
        push    af
        ld      a,SK_VISITOR
        call    ev_kind                 ; src/econ.asm: ή εισβολείς
        call    ship_call               ; CY: ήρθε
        pop     de                      ; D = ό,τι περίσσεψε πάνω από το 256
        ld      a,d
        ld      hl,EC_VISACC
        jr      c,srp_st
        ld      a,255
srp_st: ld      (hl),a
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
