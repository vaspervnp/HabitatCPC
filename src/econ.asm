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

NO_STOCK    equ 255
MF_OPERATOR equ 1
MF_FLOW     equ 2
PROD_DOMES  equ 16

; ΤΡΕΙΣ ΣΤΑΘΜΕΣ ΡΕΥΜΑΤΟΣ, ΟΧΙ ΔΥΟ. Ο πίνακας του §6.5 γράφει για την αστοχία
; ρεύματος «machines stop, THEN oxygen stops» — και ο κώδικας δεν είχε «then»:
; το EC_POK ήταν μία σημαία για ολόκληρη την αποικία, οπότε το ίδιο μπλακάουτ
; που σταματούσε τις αντλίες σταματούσε και τη γεννήτρια οξυγόνου.
;
; Αυτό δεν ήταν θεωρητικό. Το βήμα 31 μέτρησε ότι η σωστή απάντηση στο νερό —
; δεύτερη αντλία — ανεβάζει τη ζήτηση από 22 σε 28 απέναντι σε 36 παραγωγής,
; και τότε η μέρα αποταμιεύει ~50 ενώ η νύχτα θέλει ~130: μπλακάουτ κάθε νύχτα,
; 13 στα 80 δείγματα, με την παραγωγή οξυγόνου να πέφτει 20 -> 0 και τη μπάρα
; του αποίκου στο 208. Δηλαδή το παιχνίδι τιμωρούσε τη σωστή κίνηση.
;
; Οι ΤΡΕΙΣ ΣΤΑΘΜΕΣ — P_NONE, P_ALL, P_ESS — ζουν στο src/const.asm: τις
; διαβάζουν και το hud.asm, το main.asm και το ship.asm, και δεν συμπεριλαμβάνουν
; όλα τα δοκιμαστικά harness το econ.asm (το objtest δεν το κάνει, και το είπε
; με σφάλμα μεταγλώττισης).

; Η ΡΕΖΕΡΒΑ: πόσους κύκλους ροής κρατά η μπαταρία ΣΤΗΝ ΑΚΡΗ για την
; υποστήριξη ζωής. Η
; νύχτα είναι το 40% του sol και ένας κύκλος το 1/11,7 του sol — 4,7 κύκλοι —
; οπότε το οκτώ καλύπτει τη νύχτα και μια αμμοθύελλα από πάνω.
;
; ΓΡΑΜΜΕΝΟ ΩΣ ΟΛΙΣΘΗΣΕΙΣ, ΚΑΙ ΤΟ `repeat` ΔΕΝ ΕΙΝΑΙ ΚΑΛΛΩΠΙΣΜΟΣ: η πρώτη μορφή
; είχε τρία καρφωμένα `add hl,hl` με ένα σχόλιο «x RESERVE_CYC» από δίπλα. Η
; σταθερά δεν σήμαινε τίποτα — το αρνητικό δείγμα την έβαλε 0, το binary δεν
; άλλαξε ούτε ένα byte, και η δοκιμή «πέρασε» χωρίς ρεζέρβα. Μια σταθερά που
; δεν οδηγεί τον κώδικα είναι χειρότερη από καθόλου σταθερά.
RESERVE_SH  equ 3                       ; ρεζέρβα = ζήτηση ζωής << RESERVE_SH
RESERVE_CYC equ 1 << RESERVE_SH         ; = 8 κύκλοι, όσο λέει η αναφορά

; ΤΟ ΡΟΛΟΙ ΤΗΣ ΟΙΚΟΝΟΜΙΑΣ (§6.5). Οι συνταγές και οι αντλίες έτρεχαν κάθε
; περιστροφή τροχού — 750 φορές το sol — ενώ ο πίνακας του §6.5 τις έγραφε ΑΝΑ
; SOL. Μετρημένο στο tools/balance.py: η μηχανή οξυγόνου έπινε τα 60 νερά της
; αρχικής αποικίας σε είκοσι δευτερόλεπτα και όλοι πέθαναν μέσα σε ενάμιση sol,
; με ή χωρίς ηλιακό. Ο διαιρέτης κρατά ΟΛΕΣ τις αναλογίες (μια μηχανή προς μια
; αντλία) και κατεβάζει μόνο τον ρυθμό: μία παραγωγή ανά 16 περιστροφές.
ECON_DIV    equ 16
; ΚΑΙ Ο ΚΥΚΛΟΣ ΤΗΣ ΡΟΗΣ. Το σάρωμα παραγωγής θέλει ΤΕΣΣΕΡΙΣ επισκέψεις για να
; δει και τους 64 θόλους, άρα μια μηχανή τρέχει μια φορά ανά 4*ECON_DIV = 64
; περιστροφές — 11,7 φορές το sol. Το ισοζύγιο μετράει ΕΝΕΡΓΕΙΑ (η μπαταρία
; γεμίζει και αδειάζει) και οι αντλίες βγάζουν ΥΛΙΚΟ: και τα δύο πρέπει να
; πατάνε στον ίδιο κύκλο με τις μηχανές, αλλιώς η αναλογία του §6.5 σπάει επί
; 64. Με το ισοζύγιο ανά περιστροφή, ένας συλλέκτης των 360 άδειαζε σε 18
; περιστροφές — το 6% μιας νύχτας των 300· τώρα κρατά τριάντα κύκλους.
FLOW_DIV    equ ECON_DIV * 4
STORM_LEN   equ 32
O2_PER_COL  equ 2
SOL_FRAMES  equ 12000
DAY_FRAMES  equ 7200                    ; 3/5 του sol

; ---------------------------------------------------------------------------
; econ_prod_slice — θέση 11: PROD_DOMES θόλοι, σάρωμα σε τέσσερις περιστροφές.
; ---------------------------------------------------------------------------
econ_prod_slice:
        ld      hl,ec_pdiv
        dec     (hl)
        ret     nz
        ld      (hl),ECON_DIV
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
        ld      hl,(EC_ACCE)
        ld      (EC_EPOWER),hl
        ld      hl,(EC_ACCO2)
        ld      (EC_O2PROD),hl
        ld      hl,0
        ld      (EC_ACCP),hl
        ld      (EC_ACCE),hl
        ld      (EC_ACCO2),hl
        xor     a
epr_store:
        ld      (EC_PDOME),a
        pop     bc
        djnz    epr_lp
        ret

; --- ένας θόλος ------------------------------------------------------------
; Τα πεδία από τον IX, οι υποδοχές από το HL που περπατάει. Η πρώτη γραφή
; ξανάφτιαχνε τη διεύθυνση της εγγραφής για κάθε πεδίο και κόστιζε 7.488 us
; τη θέση.
;
; Η ΥΓΕΙΑ ΚΟΙΤΑΖΕΤΑΙ ΕΔΩ, ΜΙΑ ΦΟΡΑ: ως το βήμα 45 την κοίταζαν χωριστά η
; μηχανή και το φυτό, με τα ίδια δέκα bytes.
ec_run_dome:
        ld      a,(EC_PDOME)
        call    jb_dome_ptr             ; HL = εγγραφή (src/jobs.asm)
        ld      de,D_STATE
        add     hl,de
        ld      a,(hl)
        cp      DS_ACTIVE
        ret     nz                      ; ΠΡΙΝ από τον IX: οι περισσότερες
        push    hl                      ; θέσεις είναι άδειες, και το push /
        pop     ix                      ; pop ix είναι 25 T-states η καθεμία
        ld      a,(ix+D_OPS-D_STATE)
        ld      (ed_ops),a
        ld      a,(ix+D_ROOM-D_STATE)
        sub     R_GREENHS
        ld      (ed_green),a            ; 0 = θερμοκήπιο
        ld      a,(ix+D_SIZE-D_STATE)
        add     a,G_machine_count & 255
        ld      e,a
        ld      d,G_machine_count / 256
        ld      a,(de)
        ld      b,a                     ; B = πόσες υποδοχές
        ld      de,D_MACH - D_STATE
        add     hl,de                   ; HL -> υποδοχή 0
        xor     a
        ld      (ed_k),a                ; καμία μηχανή με χειριστή ακόμη
erd_lp:
        ld      a,(hl)
        cp      NO_MACH
        jr      z,erd_next
        push    hl
        push    bc
        ld      de,D_HEALTH - D_MACH
        add     hl,de
        inc     (hl)
        dec     (hl)                    ; υγεία 0: χαλασμένη μηχανή, μαραμένο φυτό
        call    nz,ec_run_one
        pop     bc
        pop     hl
erd_next:
        inc     hl
        djnz    erd_lp
        ret

        assert  (G_machine_count & 255) <= 256 - 3  ; τρία μεγέθη, μία σελίδα
        assert  (G_plant_class & 255) <= 256 - 12   ; δώδεκα φυτά, μία σελίδα
        assert  MF_OPERATOR == 1 && MF_FLOW == 2    ; bit 0 και bit 1

; ec_run_one — A = μηχανή ή φυτό: το δωμάτιο λέει ποιο από τα δύο κάθεται στην
; υποδοχή (§6.5).
ec_run_one:
        ld      c,a
        ld      a,(ed_green)
        or      a
        ld      a,c
        jr      nz,ec_run_mach
        ; fall through

; --- ένα φυτό --------------------------------------------------------------
; Νερό και ρεύμα μέσα, χλωρίδα έξω (§6.5).
ec_run_plant:
        ld      (ed_m),a

        ; ΕΝΑΣ ΒΙΟΛΟΓΟΣ ΠΟΤΙΖΕΙ ΟΛΟ ΤΟ ΘΕΡΜΟΚΗΠΙΟ. Ο κανόνας ήταν ο ίδιος με τις
        ; μηχανές — μία υποδοχή, ένας χειριστής — και σήμαινε ότι ένα μεσαίο
        ; θερμοκήπιο ήθελε ΤΕΣΣΕΡΙΣ ανθρώπους για να δώσει τα τέσσερα φυτά του.
        ; Με έναν έδινε μόνο την υποδοχή 0, δηλαδή άμυλο: μετρημένο, 286 άμυλο
        ; και ΜΗΔΕΝ λαχανικά, και το mach_food θέλει και τα δύο — η αποικία
        ; πέθαινε από πείνα με γεμάτη σιταποθήκη. Ο κήπος είναι ένας κήπος:
        ; όποιος τον φροντίζει, τον φροντίζει όλο.
        ld      a,(ed_ops)
        or      a
        ret     z

        ld      a,S_WATER               ; ένα νερό
        ld      c,1
        call    ec_have                 ; DE = &νερό
        ret     c

        ld      hl,(EC_ACCP)            ; ΖΗΤΑΕΙ το ρεύμα του — και το ζητά
        inc     hl                      ; είτε το πάρει είτε όχι· βλ. ec_run_mach
        ld      (EC_ACCP),hl
        ld      a,(EC_POK)
        cp      P_ALL
        ret     nz                      ; ο κήπος δεν είναι υποστήριξη ζωής
        ld      a,c
        call    ec_sub                  ; το νερό

        ld      a,(ed_m)                ; η κατηγορία του φυτού, 0-3
        add     a,G_plant_class & 255
        ld      l,a
        ld      h,G_plant_class / 256
        ld      a,(hl)
        add     a,a                     ; *2 στον πίνακα εξόδου
        ld      hl,plant_out
        add     a,l
        ld      l,a
        adc     a,h
        sub     l
        ld      h,a
        ld      a,(hl)                  ; απόθεμα, NO_STOCK = τίποτα (δέντρο)
        inc     hl
        ld      e,(hl)
        ld      d,0
        cp      NO_STOCK
        ret     z
        jp      ec_make

plant_out:  db S_STARCH,3, S_VEG,2, S_MEDPLANT,2, NO_STOCK,0

; --- μία μηχανή ------------------------------------------------------------
; A = τύπος μηχανής. IX = η συνταγή, G_recipes + 10*A: το 10*A χωράει σε byte
; (δώδεκα μηχανές), και ο υπολογισμός γίνεται στο A.
ec_run_mach:
        ld      e,a
        add     a,a
        add     a,a
        add     a,e
        add     a,a                     ; *10
        ld      e,a
        ld      d,0
        ld      ix,G_recipes
        add     ix,de
        bit     0,(ix+9)                ; MF_OPERATOR
        jr      z,erm_ins
        ; Η k-ΟΣΤΗ ΜΗΧΑΝΗ ΠΟΥ ΘΕΛΕΙ ΧΕΙΡΙΣΤΗ τρέχει αν ο θόλος έχει k, όποια
        ; υποδοχή κι αν πιάνει. Ως το βήμα 44 μετρούσε η ΥΠΟΔΟΧΗ (slot < ops),
        ; που δούλευε μόνο επειδή το γέμισμα έβαζε τις μηχανές από την 0 και
        ; κάτω: με εξοπλισμό ανά υποδοχή, ένα μεταλλουργείο στην υποδοχή 5 κι
        ; ένας χειριστής δεν θα έτρεχε ποτέ. Το jb_need μετράει ακριβώς αυτές.
        ld      hl,ed_k
        ld      a,(hl)
        inc     (hl)
        ld      hl,ed_ops
        cp      (hl)
        ret     nc                      ; δεν φτάνουν οι χειριστές ως αυτήν
erm_ins:
        ; --- οι τρεις είσοδοι, με πρόωρη έξοδο στην πρώτη που λείπει ---
        ; Ενας βρόχος με IY και υπολογισμό μετατόπισης κόστιζε 280 T-states ανά
        ; είσοδο. Οι σταθερές μετατοπίσεις του IX μένουν· από το βήμα 46 τα
        ; τρία αντίγραφα του ελέγχου είναι ένα (erm_in), για 27 T-states ανά
        ; είσοδο.
        ld      hl,ed_in
        ld      a,(ix+0)
        ld      c,(ix+1)
        call    erm_in
        ret     c
        ld      a,(ix+2)
        ld      c,(ix+3)
        call    erm_in
        ret     c
        ld      a,(ix+4)
        ld      c,(ix+5)
        call    erm_in
        ret     c

        ; ΤΟ ΡΕΥΜΑ ΜΕΤΡΑΕΙ ΩΣ ΖΗΤΗΣΗ, ΟΧΙ ΩΣ ΚΑΤΑΝΑΛΩΣΗ. Οσο το mach_power
        ; ήταν «ό,τι κάηκε», ένα μπλακάουτ μηδένιζε τη ζήτηση του επόμενου
        ; σαρώματος, το ισοζύγιο έβρισκε 0 >= 0 και το ρεύμα ξαναγύριζε: η
        ; αποικία του §10.1, χωρίς ούτε ένα πάνελ, έπαιρνε το μισό της οξυγόνο
        ; ΔΩΡΕΑΝ και ζούσε πέντε sols αντί για δύο (μετρημένο στο
        ; tools/balance.py). Ζήτηση είναι όσα ΘΑ έτρεχαν: χειριστής υπάρχει,
        ; είσοδοι υπάρχουν, μόνο το ρεύμα λείπει.
        ld      e,(ix+8)
        ld      d,0
        ld      hl,EC_ACCP
        call    ec_add16                ; κρατά το DE
        ; Η ΥΠΟΣΤΗΡΙΞΗ ΖΩΗΣ ΜΕΤΡΙΕΤΑΙ ΚΑΙ ΧΩΡΙΣΤΑ: το ισοζύγιο πρέπει να ξέρει
        ; πόσο ρεύμα κρατά την αποικία ζωντανή, για να μπορεί να αφήσει τα
        ; υπόλοιπα να σταματήσουν.
        bit     1,(ix+9)                ; MF_FLOW
        ld      hl,EC_ACCE
        call    nz,ec_add16
        ld      a,(EC_POK)
        cp      P_ALL
        jr      z,erm_take
        or      a
        ret     z                       ; μπλακάουτ: ζήτησε, δεν πήρε
        bit     1,(ix+9)                ; P_ESS: μόνο η υποστήριξη ζωής
        ret     z
erm_take:
        ; --- αφαίρεση, με τους δείκτες που ήδη έχουμε ---
        ld      hl,ed_in
        ld      b,3
erm_tk:
        ld      e,(hl)
        inc     hl
        ld      d,(hl)
        inc     hl
        ld      a,(hl)
        inc     hl
        call    ec_sub                  ; κρατά τα B, HL
        djnz    erm_tk

        ld      e,(ix+7)
        ld      d,0
        bit     1,(ix+9)
        ld      hl,EC_ACCO2
        jp      nz,ec_add16             ; το οξυγόνο είναι ροή, όχι απόθεμα
        ld      a,(ix+6)                ; δείκτης αποθέματος
        cp      NO_STOCK
        ret     z                       ; τα κρεβάτια δεν παράγουν τίποτα
        jp      ec_make                 ; φτιάχτηκε ΕΔΩ (§10.2)

; erm_in — μία είσοδος: A = απόθεμα (NO_STOCK = καμία), C = ποσότητα, HL -> η
; θέση της στο ed_in. CY αν δεν φτάνει· αλλιώς γράφει (δείκτης, ποσότητα) και
; HL += 3. Χωρίς είσοδο ο δείκτης είναι 0, και το ec_sub τον προσπερνά.
erm_in:
        ld      de,0
        cp      NO_STOCK                ; Z και NC αν δεν υπάρχει είσοδος
        call    nz,ec_have              ; DE = &stock, CY αν δεν φτάνει
        ret     c
        ld      (hl),e
        inc     hl
        ld      (hl),d
        inc     hl
        ld      (hl),c
        inc     hl
        ret

; ec_have — A = δείκτης αποθέματος, C = ποσότητα.
;           Επιστρέφει DE = &stock[A], Cy=1 αν ΔΕΝ φτάνει. Το C και το HL μένουν.
ec_have:
        call    ec_stock_ptr            ; src/stock.asm
        ld      a,(de)
        sub     c
        inc     de
        ld      a,(de)
        sbc     a,0                     ; τα inc/dec de δεν πειράζουν το carry
        dec     de
        ret

; ec_sub — DE = &stock (ή 0 = καμία είσοδος), A = ποσότητα. Κρατά B, HL.
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

; ec_add16 — (HL) += DE. Κρατά το DE.
ec_add16:
        ld      a,(hl)
        add     a,e
        ld      (hl),a
        inc     hl
        ld      a,(hl)
        adc     a,d
        ld      (hl),a
        ret

ed_in:      defs 9                  ; τρεις είσοδοι: δείκτης (2), ποσότητα (1)
ed_ops:     db 0
ed_k:       db 0                    ; πόσες με χειριστή πέρασαν σε αυτόν τον θόλο
ed_m:       db 0
ed_green:   db 0                    ; 0 = θερμοκήπιο

; ---------------------------------------------------------------------------
; econ_flow — θέση 12: παραγωγή απέναντι σε κατανάλωση, και η μπαταρία.
;
; Σαρώνει τις 64 δομές. Η κατανάλωση των ΜΗΧΑΝΩΝ δεν ξανασαρώνεται εδώ — τη
; μάζεψε η παραγωγή στο τελευταίο της σάρωμα. Αλλιώς αυτή η θέση θα κοίταζε
; 64 θόλους x 8 υποδοχές κάθε περιστροφή, για έναν αριθμό που ήδη υπάρχει.
;
; Η ΠΑΡΑΓΩΓΗ, ΤΟ ΤΑΒΑΝΙ ΚΑΙ Η ΖΗΤΗΣΗ μαζεύονται ΚΑΤΕΥΘΕΙΑΝ στα EC_PPROD,
; EC_PCAP, EC_PUSE: ο κύκλος τρέχει ολόκληρος σε μία κλήση, και κανείς δεν τα
; διαβάζει στη μέση του. Ως το βήμα 45 μαζεύονταν σε τρία ιδιωτικά αντίγραφα
; και αντιγράφονταν στο τέλος.
; ---------------------------------------------------------------------------
econ_flow:
        ; Η ΜΕΤΡΗΣΗ ΤΩΝ ΖΩΝΤΑΝΩΝ ΓΙΝΕΤΑΙ ΚΑΘΕ ΠΕΡΙΣΤΡΟΦΗ — είναι η συνθήκη
        ; ήττας (§10.3) και δεν περιμένει κύκλο. Το ισοζύγιο από κάτω όχι.
        ld      hl,ec_fdiv
        dec     (hl)
        jp      nz,ef_o2
        ld      (hl),FLOW_DIV

        ld      hl,0
        ld      (EC_PCAP),hl
        ld      (EC_PPROD),hl
        ld      (ef_wat),hl
        ld      (ef_ore),hl
        ld      hl,(EC_MPOWER)
        ld      (EC_PUSE),hl

        ld      ix,G_struct_tbl
        ld      b,MAX_STRUCT
ef_lp:
        push    bc
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
        jr      nz,ef_next
        ld      e,8                     ; MINE_POWER
        ld      c,2                     ; MINE_OUT
        ld      hl,ef_ore
; ef_pump — E = ρεύμα, C = προϊόν, HL -> πού πάει: αντλία και ορυχείο, που
; ως το βήμα 45 ήταν γραμμένα το καθένα μόνο του.
ef_pump:
        push    hl
        ld      d,0
        ld      hl,EC_PUSE
        call    ec_add16
        pop     hl
        ld      e,c
ef_addn:
        call    ec_add16                ; (HL) += DE, και η επόμενη δομή
ef_next:
        pop     bc
        ld      de,STRUCT_REC
        add     ix,de
        djnz    ef_lp
        jr      ef_balance

ef_solar:
        ld      a,(EC_STORM)            ; η σκόνη σκεπάζει τα πάνελ (§6.10)
        or      a
        jr      nz,ef_next
        ld      a,(EC_DAY)
        or      a
        jr      z,ef_next
        ld      hl,tab_solar
        add     hl,bc
        ld      e,(hl)
        ld      d,0
        ld      hl,EC_PPROD
        jr      ef_addn

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
        djnz    ef_t_mul                ; ως 27 * 3 = 81: χωράει σε byte
        ld      de,-1                   ; E = πηλίκο, και το D γίνεται 0
ef_t_div:
        inc     de
        sub     3
        jr      nc,ef_t_div
        ld      hl,EC_PPROD
        jr      ef_addn

ef_coll:
        sla     c                       ; 16-bit πίνακας
        ld      hl,tab_coll
        add     hl,bc
        ld      e,(hl)
        inc     hl
        ld      d,(hl)
        ld      hl,EC_PCAP
        jr      ef_addn

ef_extr:
        ld      hl,tab_extr_out
        add     hl,bc
        ld      a,(hl)                  ; νερό
        ld      hl,tab_extr_pw
        add     hl,bc
        ld      e,(hl)                  ; ρεύμα
        ld      c,a
        ld      hl,ef_wat
        jr      ef_pump

ef_balance:
        ; --- το ισοζύγιο ---
        ld      hl,(EC_PPROD)
        ld      de,(EC_PUSE)
        or      a
        sbc     hl,de
        jr      nc,ef_surplus

; --- η παραγωγή δεν φτάνει: ποιος σταματά πρώτος (§6.5) --------------------
; Η μπαταρία δανείζεται στις μηχανές ΜΟΝΟ όσο μένει πίσω ό,τι θέλει η
; υποστήριξη ζωής για RESERVE_CYC κύκλους. Χωρίς αυτή τη ρεζέρβα η σειρά
; «πρώτα οι μηχανές, μετά το οξυγόνο» δεν σημαίνει τίποτα: οι μηχανές
; αδειάζουν τη μπαταρία στους δύο πρώτους κύκλους της νύχτας και το οξυγόνο
; σβήνει ούτως ή άλλως — που είναι ακριβώς αυτό που μετρήθηκε στο βήμα 31.
;
; ΜΕ ΤΟ ΕΛΛΕΙΜΜΑ ΑΡΝΗΤΙΚΟ, όπως βγήκε: μπαταρία + (παραγωγή - ζήτηση) με
; κρατούμενο σημαίνει «η μπαταρία το σηκώνει», και το υπόλοιπο συγκρίνεται με
; τη ρεζέρβα. Ως το βήμα 45 το έλλειμμα ξαναϋπολογιζόταν θετικό, μπαινόταν σε
; μεταβλητή και αφαιρούνταν δύο φορές.
        ld      de,(EC_PSTORE)
        add     hl,de                   ; HL = μπαταρία - έλλειμμα, CY αν φτάνει
        jr      nc,ef_shed
        push    hl
        ld      hl,(EC_EPOWER)
        repeat  RESERVE_SH
        add     hl,hl                   ; x RESERVE_CYC
        rend
        ex      de,hl                   ; DE = ρεζέρβα
        pop     hl
        or      a
        sbc     hl,de
        add     hl,de                   ; CY αν θα έμενε κάτω από τη ρεζέρβα
        jr      c,ef_shed
        ld      (EC_PSTORE),hl          ; η μπαταρία σηκώνει και τα δύο
        jr      ef_all

; --- ρίχνει φορτίο: αντλίες, ορυχεία, εργοστάσια και κήποι σταματούν -------
ef_shed:
        ld      hl,(EC_PPROD)
        ld      de,(EC_EPOWER)
        or      a
        sbc     hl,de
        jr      c,ef_shed_dr
        call    ef_charge               ; ό,τι περισσεύει, φορτίζει
        jr      ef_ess
ef_shed_dr:
        ld      de,(EC_PSTORE)          ; από τη μπαταρία, αν φτάνει
        add     hl,de
        jr      nc,ef_blackout
        ld      (EC_PSTORE),hl
ef_ess:
        ld      a,P_ESS
        jr      ef_setp                 ; οι αντλίες είναι από τα φορτία που
                                        ; έπεσαν: αντλούν την επόμενη μέρα
ef_blackout:
        xor     a                       ; P_NONE
        ld      h,a
        ld      l,a
        ld      (EC_PSTORE),hl
        jr      ef_setp                 ; χωρίς ρεύμα δεν αντλεί κανείς

ef_surplus:
        call    ef_charge               ; πλεόνασμα: φορτίζει, ως το ταβάνι
ef_all:
        ld      a,P_ALL
ef_setp:
        ld      (EC_POK),a
        cp      P_ALL
        jr      nz,ef_o2

        ; Το νερό και το μετάλλευμα βγαίνουν από ΔΟΜΕΣ, όχι από μηχανές
        ; θόλου — αλλά βγαίνουν εδώ, και το §10.2 τα θέλει.
        ;
        ; Στον ΙΔΙΟ κύκλο με τις μηχανές (βλ. FLOW_DIV): αλλιώς μία αντλία θα
        ; γέμιζε την αποικία νερό εξήντα τέσσερις φορές πιο γρήγορα απ' όσο το
        ; πίνει η μηχανή οξυγόνου.
        ld      de,(ef_wat)
        ld      a,d
        or      e
        ld      a,S_WATER
        call    nz,ec_make
        ld      de,(ef_ore)
        ld      a,d
        or      e
        ld      a,S_ORE
        call    nz,ec_make

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
        inc     a
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
        sbc     a,a                     ; -1 αν δεν φτάνει
        inc     a
        ld      (EC_O2OK),a
        ret

; ef_charge — HL = πλεόνασμα: η μπαταρία το παίρνει, ως το ταβάνι. Ως το βήμα
; 45 γραμμένο δύο φορές, για την αποικία και για το φορτίο που έπεσε.
ef_charge:
        ld      de,(EC_PSTORE)
        add     hl,de
        ld      de,(EC_PCAP)
        or      a
        sbc     hl,de
        add     hl,de                   ; CY αν κάτω από το ταβάνι
        jr      c,efc_st
        ex      de,hl
efc_st:
        ld      (EC_PSTORE),hl
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
        sbc     a,a
        inc     a                       ; 1 = νέο sol
        ld      (ev_newday),a
        jr      nz,ev_newsol
        add     hl,de
        jr      ev_store
ev_newsol:
        ld      a,(EC_SOL)
        inc     a
        ld      (EC_SOL),a
ev_store:
        ld      (EC_FRAME),hl
        ld      de,(EC_DAYLEN)
        or      a
        sbc     hl,de
        sbc     a,a
        and     1                       ; 1 = μέρα
        ld      (EC_DAY),a

        ld      hl,EC_GLOOM             ; το πένθος περνάει, αργά
        ld      a,(hl)
        or      a
        jr      z,ev_roll
        dec     (hl)

        ; Τρεις ζαριές, ΠΑΝΤΑ. Μια ζαριά υπό όρους θα έκανε την ακολουθία να
        ; εξαρτάται από το αποτέλεσμα της προηγούμενης, και η αναπαραγωγή θα
        ; γινόταν δουλειά. Ο άνεμος διαβάζει την πρώτη αμέσως: δεν πειράζει
        ; τη γεννήτρια, άρα ούτε τη σειρά. Τη θέλει και ο μετεωρίτης (mt_tick).
ev_roll:
        call    ev_rnd                  ; --- άνεμος: η πρώτη ---
        ld      (ev_r1),hl
        ld      a,l
        and     15
        jr      nz,ev_r23
        ld      a,l
        rrca
        rrca
        rrca
        rrca
        and     3
        ld      (EC_WIND),a
ev_r23:
        call    ev_rnd
        ld      (ev_r2),hl
        call    ev_rnd
        ld      (ev_r3),hl

        ld      hl,EC_STORM             ; --- αμμοθύελλα ---
        ld      a,(hl)
        or      a
        jr      z,ev_st_new
        dec     (hl)
        jr      ev_fault
ev_st_new:
        ; Τα ΨΗΛΑ bits του δεύτερου. Ο Galois ολισθαίνει δεξιά, άρα δύο
        ; διαδοχικά τραβήγματα είναι το ίδιο νούμερο μετατοπισμένο: με δύο
        ; δοκιμές στα χαμηλά bits, θύελλα και βλάβη έπεφταν μαζί ή καθόλου.
        ; 1/512 ΑΝΑ ΠΕΡΙΣΤΡΟΦΗ, ΟΧΙ 1/128: επί STORM_LEN περιστροφές η παλιά
        ; ζαριά κρατούσε τα πάνελ σκεπασμένα το ΕΝΑ ΤΕΤΑΡΤΟ του sol, πάνω από
        ; τη νύχτα. Τώρα 6%. Μετρημένο στο tools/balance.py.
        ld      a,(ev_r2 + 1)
        or      a
        jr      nz,ev_fault
        ld      a,(ev_r2)
        rla                             ; το bit 7
        jr      c,ev_fault
        ld      (hl),STORM_LEN

ev_fault:                               ; --- απλή βλάβη: χαμηλά του τρίτου ---
        ; 1/128, ΟΧΙ 1/32. Με 1/32 η μοναδική μηχανή οξυγόνου του §10.1
        ; σταματούσε κάθε 1,3 sol: τα τέσσερα ανταλλακτικά τελείωναν σε τρία
        ; sols, και η επόμενη βλάβη ήταν ασφυξία — καμία μηχανή δεν φτιάχνει
        ; ανταλλακτικά στην αρχική αποικία.
        ;
        ; Ο ΔΕΙΚΤΗΣ ΑΠΟ ΤΑ BITS ΠΟΥ ΠΕΡΙΣΣΕΨΑΝ. Με δείκτη το ev_r2 — την
        ; προηγούμενη ρίψη του ίδιου Galois, που το #B400 δεν της αγγίζει το
        ; χαμηλό byte — το r2 % 64 ήταν ΠΑΝΤΑ 0: κάθε βλάβη έπεφτε στον θόλο 0,
        ; τη μοναδική γεννήτρια οξυγόνου.
        ld      hl,(ev_r3)
        ld      a,l
        and     #7F
        jr      nz,ev_visit
        ld      b,7
        call    ev_shr
        call    ec_break

ev_visit:                               ; --- απρόσκλητοι επισκέπτες (§6.11) ---
        ; ΕΝΑΣ ΑΝΑ ΔΥΟ SOL, ΟΧΙ ΔΩΔΕΚΑ ΤΟ SOL. Η ζαριά ήταν 1/64 ανά περιστροφή
        ; — δηλαδή ένα πλοίο κάθε είκοσι δευτερόλεπτα παιχνιδιού, και κάθε
        ; επισκέπτης τρώει έξι τρόφιμα (VIS_FOOD): εβδομήντα τρόφιμα το sol,
        ; όταν η αρχική αποικία έχει σαράντα. Μετρημένο με το tools/balance.py:
        ; τα τρόφιμα τέλειωναν σε ένα sol και τα έτρωγαν ΟΙ ΕΠΙΣΚΕΠΤΕΣ, όχι οι
        ; άποικοι. 1/2048 ανά περιστροφή = ένας κάθε 2,7 sol.
        ld      hl,(ev_r2)
        ld      a,h
        and     #07
        or      l
        jr      nz,ev_flare
        ld      a,SK_VISITOR
        call    ship_call

ev_flare:                               ; --- έκλαμψη: ψηλά του ίδιου ---
        ; 1/2048, όχι 1/256: τρεις εκλάμψεις το sol, με τρεις μηχανές η καθεμία,
        ; δεν είναι συμβάν αλλά καιρός. Μία ανά 2,7 sol.
        ld      hl,(ev_r3)
        ld      a,h
        or      a
        jr      nz,ev_after
        ld      a,l
        and     #C0
        jr      nz,ev_after
        ; Τρεις μηχανές, από τρεις ολισθήσεις του ίδιου αριθμού. Από πίνακα
        ; από το βήμα 46· ως τότε τρία αντίγραφα του ίδιου κώδικα.
        ld      hl,ev_fl_tab
ev_fl_lp:
        ld      b,(hl)                  ; ολίσθηση
        inc     hl
        ld      e,(hl)                  ; και μετατόπιση
        inc     hl
        push    hl
        ld      hl,(ev_r3)
        call    ev_shr
        ld      d,0
        add     hl,de
        call    ec_break
        pop     hl
        ld      a,l
        cp      ev_fl_end & 255         ; έξι bytes: το L μόνο του αρκεί
        jr      nz,ev_fl_lp

ev_after:
        call    mt_tick                 ; η βροχή μετεωριτών (src/meteor.asm)
        ld      a,(ev_newday)
        or      a
        call    nz,sol_rollover
        jp      ship_tick

ev_fl_tab:  db 0,37, 3,101, 1,173
ev_fl_end:

; ev_rnd — Galois, ίδιος με τη γεννήτρια κόσμου, ΞΕΧΩΡΙΣΤΗ κατάσταση.
ev_rnd:
        ld      hl,(EC_RND)
        call    lfsr_hl
        ld      (EC_RND),hl
        ret

; lfsr_hl — ένα βήμα του Galois στο HL. Και για τη βροχή μετεωριτών, που έχει
; δική της κατάσταση (EC_MRND, src/meteor.asm). Χαλάει το A.
lfsr_hl:
        ld      a,l
        srl     h
        rr      l
        and     1
        ret     z
        ld      a,h
        xor     #B4
        ld      h,a
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
; ec_break_d — ο θόλος (eb_d) και η υποδοχή (eb_s) ήδη διαλεγμένοι: τον
; θόλο που χτύπησε ο μετεωρίτης τον ξέρουμε, δεν τον βγάζουμε από ζαριά.
ec_break_d:
        ld      a,(eb_d)
        call    jb_dome_ptr
        push    hl
        pop     ix
        ld      a,(ix+D_STATE)
        cp      DS_ACTIVE
        ret     nz
        ld      a,(ix+D_SIZE)
        add     a,G_machine_count & 255
        ld      l,a
        ld      h,G_machine_count / 256
        ld      a,(hl)
        dec     a                       ; 1/4/8 -> μάσκα
        ld      hl,eb_s
        and     (hl)
        ld      e,a
        ld      d,0
        add     ix,de                   ; IX -> η υποδοχή, μέσα στην εγγραφή
        ld      a,(ix+D_MACH)
        cp      NO_MACH
        ret     z
        ld      (ix+D_HEALTH),0         ; ήδη σταματημένη: το ίδιο μηδέν
        ret

ev_newday:  db 0
ev_r1:      dw 0
ev_r2:      dw 0
ev_r3:      dw 0
eb_d:       db 0
eb_s:       db 0

tab_solar:      db 2,8,18
tab_turb:       db 3,12,27
tab_coll:       dw 40,160,360
; Η ΑΝΤΛΙΑ ΚΟΣΤΙΖΕ ΤΑ ΔΥΟ ΤΡΙΤΑ ΕΝΟΣ ΠΑΝΕΛ (12 έναντι 18) και αυτό έκλεινε το
; άνοιγμα του παιχνιδιού: με τη μεγάλη αντλία αναμμένη το πλεόνασμα της ημέρας
; έπεφτε στη ΜΟΝΑΔΑ, ο συλλέκτης δεν προλάβαινε να φορτίσει, και η νύχτα έσβηνε
; το οξυγόνο ό,τι κι αν έχτιζε ο παίκτης — μετρημένο στο tools/balance.py.
; Το ένα τρίτο αφήνει την ημέρα να φορτίσει τη νύχτα.
tab_extr_pw:    db 1,3,6
tab_extr_out:   db 1,2,5

ef_wat:     dw 0
ef_ore:     dw 0
ec_pdiv:    db 1
ec_fdiv:    db 1
