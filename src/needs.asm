; needs.asm — ανάγκες, υγεία, θάνατος, και πού πρέπει να πάει ο καθένας (§6.6)
;
; Το §6.6 έλεγε «το ακριβό είναι να αποφασίσεις τι θα κάνεις γι' αυτό, και
; αυτό είναι πρόβλημα του πίνακα εργασιών». Δεν είναι: ο πίνακας εργασιών
; μοιράζει δουλειές, δεν στέλνει κόσμο για φαγητό. Η απόφαση ζει εδώ, στο ίδιο
; πέρασμα που έχει ήδη τα νούμερα στα χέρια του.
;
; Οκτώ βήματα ανά άποικο, με αυτή τη σειρά:
;   φθορά · οξυγόνο περιβάλλοντος · ικανοποίηση · υγεία · θάνατος · ηθικό ·
;   αναζήτηση
;
; Το οξυγόνο δεν είναι ταξίδι αλλά ΡΟΗ: όποιος είναι μέσα το αναπνέει. Τα
; υπόλοιπα θέλουν να πας κάπου, και το πού είναι μία ανάγνωση του ευρετηρίου
; δωματίων (θέση 14) συν ως οκτώ αναγνώσεις του DIST.
;
; ΜΙΚΡΟΤΕΡΟ, ΣΤΟ ΒΗΜΑ 53 (963 -> 776 bytes). Οι ενδιάμεσες τιμές ζουν σε
; καταχωρητές αντί για μεταβλητές — η ζημιά, το ελάχιστο του ηθικού, ο κόμβος,
; η καλύτερη απόσταση — και οι θόλοι και οι δομές της θέσης 14 διαβάζονται με
; τον IX αντί για push, add, pop γύρω από κάθε πεδίο.

NEED_LOW    equ 64
NEED_CRIT   equ 16
O2_REFILL   equ 2
; Το ROOM_MAX και τα R_* είναι στο const.asm.

; Το ευρετήριο δωματίων: 12 μετρητές και 12 λίστες των ROOM_MAX, σε ΜΙΑ σελίδα
; (layout του tools/pack.py), οπότε κάθε δείκτης μέσα του είναι «add, ld l».
;
; Η ΣΕΛΙΔΑ ΕΙΝΑΙ «>> 8», ΠΟΤΕ «/ 256». Η RASM λογαριάζει τις εκφράσεις σε
; πραγματικούς αριθμούς και ΣΤΡΟΓΓΥΛΕΥΕΙ: το #9E84 / 256 βγαίνει #9F. Ετσι
; έσπασε η πρώτη γραφή του βήματος 53 — οι άποικοι διάβαζαν τη λίστα των
; δωματίων από την επόμενη σελίδα και πήγαιναν σε άλλους θόλους.
        assert  G_room_list == G_room_n + 12
        assert  (G_room_n & 255) + 12 + 12 * ROOM_MAX <= 256
        assert  (G_machine_count & 255) <= 256 - 3
        assert  (G_plant_class & 255) <= 256 - 12  ; στο θερμοκήπιο μόνο ποικιλίες 0-11

; «ΠΑΩ ΓΙΑ ΦΑΓΗΤΟ» ΕΙΝΑΙ ΚΙ ΑΥΤΟ ΕΡΓΑΣΙΑ, και το §6.7 το έλεγε από την αρχή:
; ο πίνακάς του έχει γραμμή «Rest / Eat / Drink — η ίδια του η ανάγκη — ό,τι
; προτεραιότητα θέλει». Ως το βήμα 28 το nd_search έγραφε NO_TASK, δηλαδή
; «αδρανής», και ο πίνακας εργασιών δίνει δουλειά στους αδρανείς: η ανάγκη
; έστελνε τον άποικο στο κυλικείο, η ανάθεση τον ξανάπαιρνε στον επόμενο
; κόμβο, και ο άποικος πηγαινοερχόταν ανάμεσα στους δύο ΩΣΠΟΥ ΠΕΘΑΙΝΕ — με
; τριάντα εννιά τρόφιμα στην αποθήκη, μετρημένο στο tools/agents.py.
;
; Το 254 δεν είναι ποτέ δείκτης εργασίας (ο πίνακας έχει 32 θέσεις), οπότε:
; το μάζεμα το βλέπει «άλλαξε γνώμη» και ελευθερώνει την εργασία, η ανάθεση
; το βλέπει «απασχολημένος» και δεν τον αγγίζει. Καμία καινούργια στήλη.
; (Το T_NEED = 254 είναι στο const.asm από το βήμα 90: το διαβάζει και το
; src/suit.asm, που το συμπεριλαμβάνουν σκαλωσιές χωρίς αυτό το αρχείο.)

; ---------------------------------------------------------------------------
; ent_needs_slice — C = πρώτος, B = πλήθος.
; ---------------------------------------------------------------------------
ent_needs_slice:
        ; ΤΑ ΡΟΜΠΟΤ ΔΕΝ ΕΧΟΥΝ ΑΝΑΓΚΕΣ (βήμα 92): οι θέσεις 80-95 είναι δικές
        ; τους, και οι φέτες είναι των οκτώ, οπότε μια φέτα είναι ή όλη αποίκων
        ; ή όλη ρομπότ. Στη θέση του ελέγχου για φέτα μηδέν, που δεν έρχεται
        ; ποτέ: το wh_decay_n δεν το γράφει τίποτα (src/wheel.asm).
        ld      a,c
        cp      AG_BOT0
        ret     nc
        ; Η ΡΟΗ ΤΟΥ ΟΞΥΓΟΝΟΥ ΔΙΑΛΕΓΕΤΑΙ ΜΙΑ ΦΟΡΑ ΑΝΑ ΚΟΜΜΑΤΙ (βήμα 87). Το
        ; EC_O2OK το γράφει μόνο η θέση 12· εδώ δεν αλλάζει. Με το F_INDOORS
        ; ο άποικος είχε τρεις δρόμους αντί για δύο, και δύο ελέγχους ο
        ; καθένας — ως το 86 ένας. Τώρα ο ένας έλεγχος γίνεται εδώ, στη
        ; διεύθυνση του call (όπως το hmc_call του hud.asm), και ο άποικος
        ; κάνει μόνο τον άλλο.
        ld      hl,nd_ok
        ld      a,(EC_O2OK)
        or      a
        jr      nz,ens_o2
        ld      hl,nd_def
ens_o2:
        ld      (ens_call + 1),hl
        ; ΟΧΙ exx ΕΔΩ (δοκιμάστηκε στο βήμα 90). Με το id και τον μετρητή στο
        ; σκιώδες BC, όπως στην κίνηση, ένας ζωντανός κοστίζει 5 us λιγότερα
        ; αλλά μια ΝΕΚΡΗ θέση 8 περισσότερα, και η φέτα 9 για το στήσιμο: στην
        ; αρχή του παιχνιδιού οι 92 από τις 96 θέσεις είναι νεκρές.
ens_lp:
        ld      h,AG_PG
        ld      l,c                     ; το L μένει η ταυτότητα στο nd_ok
        ld      a,(hl)
        rra                             ; F_ALIVE
        jr      nc,ens_next
        push    bc
        ld      e,a                     ; bit 0: F_INDOORS
ens_call:
        call    nd_ok                   ; ή nd_def
        pop     bc
ens_next:
        inc     c                       ; mod N_AGENT: 2 us λιγότερα από το
        res     7,c                     ; ld/inc/and/ld (βήμα 89)
        djnz    ens_lp
        ret

        assert  F_ALIVE == 1 && F_INDOORS == 2

; ---------------------------------------------------------------------------
; nd_ok / nd_def — ένας άποικος. C = L = ταυτότητα, E bit 0 = F_INDOORS. Το
; nd_ok όταν το οξυγόνο φτάνει, το nd_def όταν δεν φτάνει· από το nd_d2 και
; κάτω κοινά.
;
; Το L ΚΡΑΤΑΕΙ ΤΗΝ ΤΑΥΤΟΤΗΤΑ ΑΠΟ ΤΗΝ ΑΡΧΗ ΩΣ ΤΟ ΤΕΛΟΣ. Κάθε πεδίο είναι τότε
; «ld h,σελίδα» και τίποτε άλλο — το bit 7 του L διαλέγει ποιο από τα δύο
; πεδία της σελίδας. Η πρώτη γραφή ξαναδιάβαζε την ταυτότητα από τη μνήμη
; δεκαπέντε φορές ανά άποικο, και αυτό ήταν ο μισός χρόνος του περάσματος.
;
; ΤΟ ΟΞΥΓΟΝΟ ΜΟΝΟ ΜΕΣΑ (βήμα 87). Εξω αναπνέει από τη στολή: το nd_out πηδά
; στο su_tick (src/suit.asm, βήμα 90· ως τότε η στολή δεν άδειαζε), που
; κάνει και τη φθορά και γυρίζει με jp στο nd_load, μετά το nd_sat: έξω
; κανένα δωμάτιο δεν δίνει τίποτα. Ή στο nd_die, αμέσως, αν άδειασε: καμία
; ζημιά υγείας στη μέση (η απόφαση του παίκτη). Με call/ret ήταν 9 us
; περισσότερα ανά επίσκεψη έξω· με jp nc κατευθείαν 3 λιγότερα, αλλά 1
; περισσότερο για όποιον είναι μέσα, και αυτοί είναι οι πολλοί.
; Μέσα, φθορά ένα με πάτωμα στο μηδέν και μετά η ροή O2_REFILL ως το 255 — ως
; το 86 δύο βήματα, εδώ μία πρόσθεση: max(o2 - 1, 0) + R είναι o2 + R - 1,
; εκτός από το 0.
; ---------------------------------------------------------------------------
nd_ok:
        ld      a,c
        ld      (nd_i),a
        ld      h,AG_PG + 4
        rr      e                       ; F_INDOORS
        jr      nc,nd_out               ; έξω: η στολή
        ld      a,(hl)                  ; οξυγόνο
        add     a,O2_REFILL - 1
        jr      c,nd_o2max
        cp      O2_REFILL - 1
        jr      nz,nd_o2st
        inc     a                       ; ήταν 0: η φθορά σταματά στο μηδέν
        jr      nd_o2st
nd_o2max:
        ld      a,255
nd_o2st:
        ld      (hl),a
        jr      nd_d2
nd_out:
        jp      su_tick                 ; src/suit.asm

nd_def:
        ld      a,c
        ld      (nd_i),a
        ld      h,AG_PG + 4
        rr      e                       ; F_INDOORS
        jr      nc,nd_out               ; έξω: η στολή
        ld      a,(hl)                  ; οξυγόνο: μόνο φθορά
        or      a
        jr      z,nd_d2
        dec     (hl)
        ; --- 1. φθορά: ένα ανά επίσκεψη, με πάτωμα στο μηδέν ---
nd_d2:  set     7,l
        ld      a,(hl)                  ; νερό
        or      a
        jr      z,nd_d3
        dec     (hl)
nd_d3:  inc     h
        ld      a,(hl)                  ; ύπνος
        or      a
        jr      z,nd_d4
        dec     (hl)
nd_d4:  res     7,l
        ld      a,(hl)                  ; τροφή
        or      a
        jr      z,nd_d5
        dec     (hl)
nd_d5:

        ; --- 3. αν στέκεται σε θόλο, ό,τι έχει να του δώσει του το δίνει ---
        ; Μόνο μέσα: όποιος είναι έξω (και στέκεται ίσως σε εργοτάξιο θόλου)
        ; έρχεται από το su_tick κατευθείαν στο nd_load (βήμα 90).
nd_sat:
        ld      h,AG_PG + 2
        set     7,l
        ld      a,(hl)                  ; ακμή
        res     7,l
        cp      NO_EDGE
        jr      nz,nd_load              ; ταξιδεύει
        dec     h
        ld      a,(hl)                  ; κόμβος
        cp      MAX_DOME
        jr      nc,nd_load              ; δομή, όχι θόλος
        call    nd_satisfy
        ld      a,(nd_i)
        ld      l,a                     ; το nd_satisfy πείραξε το HL

        ; --- B=οξυγόνο C=νερό D=τροφή· ο ύπνος μετά, στο E ---
nd_load:
        ld      h,AG_PG + 4
        ld      b,(hl)
        set     7,l
        ld      c,(hl)
        inc     h
        res     7,l
        ld      d,(hl)

        ; --- 4. υγεία ---
        ; Η ζημιά μαζεύεται στο E με τα carry των συγκρίσεων: 4 για το
        ; οξυγόνο, 2 για το νερό, 1 για την τροφή — ακριβώς τα bits τους.
        ld      e,0
        ld      a,b
        cp      NEED_CRIT
        rl      e
        ld      a,c
        cp      NEED_CRIT
        rl      e
        ld      a,d
        cp      NEED_CRIT
        rl      e
        ; Η αμμοθύελλα χτυπά όποιον είναι έξω. Αυτό ακριβώς κάνει τη θέση
        ; του αεροφράκτη απόφαση (§6.2). Ως το βήμα 86 «έξω» ήταν «σε δομή»·
        ; από το 87 είναι το F_INDOORS, που ξέρει και το έδαφος, το σκάφος,
        ; τα εργοτάξια, και ότι το airlock έχει αέρα.
        ld      a,(EC_STORM)
        or      a
        jr      z,nd_h4
        ld      h,AG_PG
        bit     1,(hl)                  ; F_INDOORS
        jr      nz,nd_h4
        ld      a,e
        add     a,4
        ld      e,a
nd_h4:
        ld      h,AG_PG + 6
        ld      a,e
        or      a
        jr      z,nd_recover
        ld      a,(hl)                  ; υγεία
        sub     e
        jr      nc,nd_hput
        xor     a
nd_hput:
        ld      (hl),a
        jr      nd_death

nd_recover:
        ; γιατρεύεται μόνο αν ΚΑΙ ΤΑ ΤΡΙΑ είναι πάνω από το κατώφλι
        ld      a,b
        cp      NEED_LOW
        jr      c,nd_death
        ld      a,c
        cp      NEED_LOW
        jr      c,nd_death
        ld      a,d
        cp      NEED_LOW
        jr      c,nd_death
        inc     (hl)
        jr      nz,nd_death
        dec     (hl)                    ; ταβάνι το 255

        ; --- 5. θάνατος ---
nd_death:
        ld      a,(hl)                  ; H = AG_PG + 6 από όλους τους δρόμους
        or      a
        jp      z,nd_die
        dec     h
        set     7,l
        ld      e,(hl)                  ; ο ύπνος
        inc     h                       ; AG_PG + 6, bit 7: το ηθικό

        ; --- 6. ηθικό: το ελάχιστο των τεσσάρων ---
        ld      a,b
        cp      c
        jr      c,nd_m1
        ld      a,c
nd_m1:
        cp      d
        jr      c,nd_m2
        ld      a,d
nd_m2:
        cp      e
        jr      c,nd_m3
        ld      a,e
nd_m3:
        cp      NEED_CRIT
        jr      nc,nd_mo_up
        ld      a,(hl)
        sub     2
        jr      nc,nd_mo_st
        xor     a
nd_mo_st:
        ld      (hl),a
        jr      nd_gloom
nd_mo_up:
        cp      NEED_LOW                ; το A είναι ακόμη το ελάχιστο
        jr      c,nd_gloom
        inc     (hl)
        jr      nz,nd_gloom
        dec     (hl)
nd_gloom:
        ld      a,(EC_AMENITY)          ; ένα δέντρο ή ένα σαλόνι παρηγορεί
        or      a
        jr      nz,nd_seek0
        ld      a,(EC_GLOOM)            ; αλλιώς το πένθος βαραίνει όλους
        or      a
        jr      z,nd_seek0
        ld      a,(hl)
        or      a
        jr      z,nd_seek0
        dec     (hl)
nd_seek0:
        res     7,l

        ; --- 7. πού πρέπει να πάει ---
        ; ΜΙΑ ΑΝΑΓΚΗ ΧΩΡΙΣ ΤΟ ΔΩΜΑΤΙΟ ΤΗΣ ΠΕΡΝΑ ΣΤΗΝ ΕΠΟΜΕΝΗ (βήμα 120). Ως
        ; τότε ο άποικος πήγαινε στο nd_want, το ψάξιμο δεν έβρισκε τίποτα, και
        ; έμενε όπως ήταν: χωρίς κοιτώνα, όποιος είχε πάει για νερό με τον ύπνο
        ; κάτω από το κατώφλι κρατούσε το T_NEED για πάντα — ο tools/play.py
        ; βρήκε και τους τέσσερις της αρχής στο κυλικείο από το sol 2, με τα
        ; εργοτάξια άδεια — και χωρίς ιατρείο ένας τραυματίας δεν ξαναπήγαινε
        ; ποτέ για φαγητό. Το G_room_n το λέει χωρίς ψάξιμο, και ο χορτάτος
        ; γλιτώνει 13 T-states: jr nc που πηδά αντί για ld a,n και jr c που όχι.
        ld      a,(hl)                  ; υγεία
        cp      NEED_LOW
        jr      nc,nd_fed
        ld      a,(G_room_n + R_MEDBAY)
        or      a
        ld      a,R_MEDBAY
        jr      nz,nd_want
nd_fed:
        ld      a,d                     ; τροφή
        cp      NEED_LOW
        jr      c,nd_eat
        ld      a,c                     ; νερό
        cp      NEED_LOW
        jr      nc,nd_drunk
nd_eat:
        ld      a,(G_room_n + R_CANTEEN)
        or      a
        ld      a,R_CANTEEN
        jr      nz,nd_want
nd_drunk:
        ld      a,e                     ; ύπνος
        cp      NEED_LOW
        jr      nc,nd_sated
        ld      a,(G_room_n + R_QUARTERS)
        or      a
        ld      a,R_QUARTERS
        jr      nz,nd_want
        ; Χορτάτος: αν κρατούσε το «πάω για φαγητό», το αφήνει και ξαναγίνεται
        ; διαθέσιμος για τον πίνακα εργασιών — ΜΕΣΑ. Εξω το T_NEED τον πηγαίνει
        ; μέσα (βήμα 90: η στολή, su_tick), και αν το έσβηνε εδώ ο πίνακας
        ; εργασιών θα τον ξανάστελνε στη δουλειά του, η στολή πίσω στο airlock,
        ; και οι δύο με τη σειρά ως να αδειάσει — το λάθος του βήματος 28.
nd_sated:
        ld      h,AG_PG + 3
        set     7,l
        ld      a,(hl)
        cp      T_NEED
        ret     nz
        res     7,l
        ld      h,AG_PG
        bit     1,(hl)                  ; F_INDOORS
        ret     z                       ; έξω: πάει ακόμη μέσα
        ld      h,AG_PG + 3
        set     7,l
        ld      (hl),NO_TASK
        ret
nd_want:
        ; ΤΟ ΔΩΜΑΤΙΟ ΣΤΟΝ B, ΟΧΙ ΣΕ ΜΕΤΑΒΛΗΤΗ (βήμα 120): το οξυγόνο του δεν
        ; χρειάζεται πια, και το jb_dome_ptr κρατά το B. 22 T-states λιγότερα
        ; για όποιον πάει ήδη εκεί, 31 για όποιον ψάχνει — όσα πληρώνει
        ; παραπάνω η αλυσίδα από πάνω για τον έλεγχο του G_room_n.
        ld      b,a

        ; Πάει ήδη σε τέτοιο δωμάτιο; Τότε τελειώσαμε.
        ld      h,AG_PG + 2
        ld      a,(hl)                  ; προορισμός
        cp      MAX_DOME
        jr      nc,nd_search
        call    nd_droom
        cp      b
        ret     z
nd_search:
        ld      a,(nd_i)
        ld      l,a
        ld      h,AG_PG + 1
        ld      d,(hl)                  ; D = ο κόμβος του
        ld      a,b
        call    nd_nearest
        ld      c,a
        inc     a
        jr      z,nd_far                ; υπάρχει, αλλά δεν φτάνει εκεί
        ld      a,(nd_i)                ; αφήνει τη δουλειά του (§6.7)
        ld      l,a
        ld      h,AG_PG + 3
        set     7,l
        ld      (hl),T_NEED             ; ΟΧΙ NO_TASK: βλ. παραπάνω
        res     7,l
        dec     h
        ld      (hl),c                  ; dest = ο θόλος
        ret
nd_far:
        ; Ο,ΤΙ Ο ΧΟΡΤΑΤΟΣ (βήμα 120): ένα «πάω για φαγητό» που δεν πάει
        ; πουθενά δεν κρατά κανέναν μακριά από τη δουλειά. Ως τότε έμενε.
        ld      a,(nd_i)
        ld      l,a
        jr      nd_sated

; nd_droom — A = θόλος -> A = το είδος του δωματίου. Χαλάει DE, HL.
nd_droom:
        call    jb_dome_ptr
        ld      de,D_ROOM
        add     hl,de
        ld      a,(hl)
        ret

; ---------------------------------------------------------------------------
; nd_satisfy — A = θόλος, L = ταυτότητα. Ο,τι έχει το δωμάτιο να δώσει.
;
; ΓΕΜΙΖΕΙ ΤΗ ΜΠΑΡΑ, ΔΕΝ ΤΗΝ ΑΝΕΒΑΖΕΙ ΚΑΤΑ 64. Με +64 ο άποικος ξαναπεινούσε σε
; 64 περιστροφές και κατανάλωνε ένα γεύμα και ένα νερό δώδεκα φορές το sol —
; δώδεκα φορές πάνω από το «1 γεύμα, 2 νερά ανά sol» του §6.5, και τα 40
; τρόφιμα της αρχικής αποικίας τέλειωναν σε ΕΝΑ sol (μετρημένο με το
; tools/balance.py). Γεμάτη μπάρα = 191 επισκέψεις αναγκών ως το NEED_LOW, και
; ο καθένας δέχεται επίσκεψη κάθε τέσσερις περιστροφές: ΜΙΑ φορά το sol,
; ακριβώς όσο λέει ο πίνακας του §6.5. Και ο άποικος δουλεύει αντί να τρώει.
; ---------------------------------------------------------------------------
nd_satisfy:
        push    hl
        call    nd_droom
        pop     hl
        cp      R_QUARTERS
        jr      z,nds_sleep
        cp      R_CANTEEN
        jr      z,nds_canteen
        cp      R_MEDBAY
        ret     nz

        ; --- ιατρείο: φάρμακο για υγεία ---
        ld      h,AG_PG + 6
        ld      a,(hl)
        cp      NEED_LOW
        ret     nc
        ld      a,S_MEDI
        ld      c,32
        jr      nds_spend

nds_sleep:
        ld      h,AG_PG + 5
        set     7,l
        ld      (hl),255                ; ΓΕΜΑΤΟ, όχι +64: βλ. παραπάνω
        ret

nds_canteen:
        ld      h,AG_PG + 5
        ld      a,(hl)                  ; τροφή
        cp      NEED_LOW
        jr      nc,nds_water
        ld      a,S_FOOD
        ld      c,255
        call    nds_spend
nds_water:
        ld      h,AG_PG + 4
        set     7,l
        ld      a,(hl)                  ; νερό
        cp      NEED_LOW
        ret     nc
        ld      a,S_WATER
        ld      c,255
        ; πέφτει μέσα

; nds_spend — A = απόθεμα, C = πόσο δίνει, HL = το πεδίο της ανάγκης (μένει).
nds_spend:
        push    hl
        call    ec_stock_ptr            ; DE = &stock[A]
        ex      de,hl
        ld      e,(hl)
        inc     hl
        ld      d,(hl)
        ld      a,d
        or      e
        jr      z,nds_none              ; άδειο
        dec     de
        ld      (hl),d
        dec     hl
        ld      (hl),e
        pop     hl
        ld      a,(hl)
        add     a,c
        jr      nc,nds_st
        ld      a,255
nds_st:
        ld      (hl),a
        ret
nds_none:
        pop     hl
        ret

; ---------------------------------------------------------------------------
; nd_die — θέση, δουλειά, χειριστής, πένθος. L = ταυτότητα.
; ---------------------------------------------------------------------------
nd_die:
        ld      a,SFX_DEATH
        call    snd_ping                ; δεν χαλάει καταχωρητές: §9.5
        ld      h,AG_PG
        ld      a,(hl)
        and     F_WORKING
        jr      z,nd_d_slot
        inc     h
        ld      a,(hl)                  ; κόμβος: θόλος, ή ορυχείο (βήμα 94)
        call    op_ptr
        dec     (hl)
nd_d_slot:
        call    nd_bury
        ld      a,(EC_GLOOM)            ; το πένθος, με ταβάνι
        add     a,16
        jr      nc,nd_gl
        ld      a,255
nd_gl:
        ld      (EC_GLOOM),a
        ld      hl,EC_DEATHS            ; για το σερί «χωρίς θανάτους» (§10.2)
        inc     (hl)
        ret     nz
        dec     (hl)
        ret

; nd_bury — (nd_i) = ταυτότητα: ό,τι κάνει ο θάνατος εκτός από χειριστή και
; πένθος — η θέση, οι σημαίες, η ακμή, η εργασία, η πρόοδος, η φιγούρα. Και ο
; εισβολέας που πέφτει (src/foe.asm, βήμα 111): εκείνος δεν φέρνει πένθος.
nd_bury:
        ld      a,(nd_i)
        ld      (em_id),a
        ld      l,a
        ld      h,AG_PG + 1
        ld      a,(hl)
        ld      (em_node),a
        call    ent_release             ; ελευθερώνει και μηδενίζει το slot
        ld      a,(nd_i)
        ld      l,a
        ld      h,AG_PG
        ld      (hl),0                  ; δεν ζει πια
        ld      h,AG_PG + 2
        set     7,l
        ld      (hl),NO_EDGE
        inc     h
        ld      (hl),NO_TASK
        res     7,l
        ld      (hl),0                  ; progress
        jp      fg_mark                 ; αν φαινόταν έξω, σβήνει (βήμα 89)

; ---------------------------------------------------------------------------
; st_check — ο κύκλος ροής αρχίζει (βήμα 122): πόσα χωράνε — το
; αμπάρι του σκάφους (STORE_BASE) και οι θόλοι Storage του ευρετηρίου, 100 /
; 300 / 600 κατά μέγεθος, ως ROOM_MAX — πόσα υπάρχουν — όλα τα αγαθά εκτός από
; το νερό — και το ec_full: 1 αν δεν χωρά άλλο. Από τον κύκλο ροής (econ_flow,
; src/flow.asm), μία φορά ανά 64 περιστροφές, με την 6 μέσα. ΟΧΙ ΣΤΟ rooms_rebuild, που
; τρέχει κάθε περιστροφή και είναι το χειρότερο frame του τροχού: εκεί ο
; έλεγχος του είδους θα πλήρωνε ~5 us για κάθε θόλο. Χαλάει όλα, και τον HL'.
; ---------------------------------------------------------------------------
st_check:
        ld      ix,STORE_BASE           ; IX = η χωρητικότητα
        ld      a,(G_room_n + R_STORAGE)
        or      a
        jr      z,stc_tot
        ld      b,a
        exx
        ld      hl,G_room_list + R_STORAGE * ROOM_MAX
        exx
        ; 52 us ο θόλος: ο δείκτης της λίστας στον HL' (κανένα exx στο ISR,
        ; src/isr.asm), όχι push/pop γύρω από το jb_dome_ptr — 100 us.
stc_lp:
        exx
        ld      a,(hl)                  ; ο θόλος, 0-63
        inc     hl
        exx
        ld      l,a
        ld      h,0
        add     hl,hl
        add     hl,hl
        add     hl,hl
        ld      d,h
        ld      e,l
        add     hl,hl
        add     hl,de                   ; x24
        ld      de,G_dome_tbl + D_SIZE
        add     hl,de
        ld      a,(hl)                  ; 0-2
        add     a,a
        add     a,stc_caps & 255
        ld      l,a
        ld      h,stc_caps >> 8
        ld      e,(hl)
        inc     hl
        ld      d,(hl)                  ; DE = όσα χωρά αυτός
        add     ix,de
        djnz    stc_lp
stc_tot:
        ; Ξεδιπλωμένο: 9 us το απόθεμα αντί για 16 με βρόχο (60 bytes αντί για
        ; 15, στο b6code). Το άθροισμα δεν ξεχειλίζει: 13 x EC_CAP < 65.536.
        ld      hl,(EC_STOCK + 2)       ; χωρίς το νερό (S_WATER = 0)
stc_k = 1
        repeat  12
stc_k = stc_k + 1
        ld      de,(EC_STOCK + stc_k * 2)
        add     hl,de
        rend
        ex      de,hl                   ; DE = σύνολο
        push    ix
        pop     hl                      ; HL = η χωρητικότητα
        or      a
        sbc     hl,de                   ; CY, ή μηδέν: δεν χωρά άλλο
        ld      a,0
        jr      c,stc_full
        jr      nz,stc_set
stc_full:
        inc     a
stc_set:
        ; ΚΑΙ ΤΟ ΑΠΟΘΕΜΑ ΜΕΤΑΛΛΟΥ (βήμα 127): μέταλλο < KEEP_METAL.
        ; Εδώ, μία φορά ανά κύκλο ροής — όσο τρέχει κάθε μηχανή μία φορά — και
        ; όχι σε κάθε μηχανή της θέσης 11: μέσα σε έναν γύρο το μέταλλο πέφτει
        ; ως όσα τρώνε μαζί οι μηχανές του, λίγο κάτω από τα 30.
        ; ΚΑΙ ΤΟ ΒΙΟΠΛΑΣΤΙΚΟ (βήμα 138): το bit 0, BIO_MAX ή πάνω — η PLASTIC
        ; σταματά. Το μέταλλο πάει στο bit 1.
        ld      c,a
        ld      hl,(EC_STOCK + 2 * S_METAL)
        ld      de,-KEEP_METAL
        add     hl,de                   ; CY αν φτάνει
        sbc     a,a
        inc     a                       ; 0 αν φτάνει, 1 αν όχι
        ld      hl,(EC_STOCK + 2 * S_BIOPL)
        ld      de,-BIO_MAX
        add     hl,de                   ; CY αν έφτασε το BIO_MAX
        rla                             ; bit 1 το μέταλλο, bit 0 το βιοπλαστικό
        ld      (ec_keep),a
        ld      a,c
        jp      st_need                 ; src/econ.asm, τράπεζα 0: και το ec_need (142)
stc_caps:    dw 100, 300, 600
        assert  (stc_caps & 255) <= 256 - 6 && S_WATER == 0 && S_MEAT == 13 && DOME_REC == 24 && EC_CAP * 13 < 65536

; ---------------------------------------------------------------------------
; rooms_rebuild — θέση 14: ποιοι θόλοι είναι τι. 64 εγγραφές ανά περιστροφή.
; ---------------------------------------------------------------------------
rooms_rebuild:
        ld      hl,G_room_n
        ld      b,12
        xor     a
rr_clr:
        ld      (hl),a
        inc     hl
        djnz    rr_clr
        ld      (EC_AMENITY),a          ; μετράει εκεί: το nd_gloom τρέχει σε άλλη θέση του τροχού

        ld      ix,G_dome_tbl
        ld      c,0                     ; C = δείκτης θόλου
rr_lp:
        ld      a,(ix+D_STATE)
        cp      DS_ACTIVE
        jr      nz,rr_next
        ld      a,(ix+D_ROOM)
        cp      12
        jr      nc,rr_next
        push    bc
        call    rr_amenity              ; σαλόνια και δέντρα (§6.6)
        pop     bc
        ld      a,(ix+D_ROOM)
        ld      e,a                     ; E = είδος
        add     a,G_room_n & 255
        ld      l,a
        ld      h,G_room_n >> 8
        ld      a,(hl)
        cp      ROOM_MAX
        jr      nc,rr_next              ; γέμισε αυτό το είδος
        inc     (hl)
        ld      d,a                     ; D = θέση μέσα στη λίστα
        ld      a,e
        add     a,a
        add     a,a
        add     a,a                     ; είδος*8
        add     a,d
        add     a,G_room_list & 255
        ld      l,a                     ; η ίδια σελίδα
        ld      (hl),c
rr_next:
        ld      de,DOME_REC
        add     ix,de
        inc     c
        ld      a,c
        cp      MAX_DOME
        jr      c,rr_lp

        ; Το ταβάνι πληθυσμού είναι δουλειά του Control (§6.8), και η πίστα
        ; είναι ο κόμβος όπου κατεβαίνει ο κόσμος (§6.11). Και τα δύο βγαίνουν
        ; από ένα πέρασμα που γίνεται ούτως ή άλλως.
        ld      a,(G_room_n + R_CONTROL)
        ld      b,a
        ld      a,POP_BASE
        inc     b
        jr      rr_cap_t
rr_cap:
        add     a,POP_PER_CTL
        jr      c,rr_cap_max
rr_cap_t:
        djnz    rr_cap
        cp      AG_BOT0 + 1             ; ως 80 άποικοι (βήμα 92· ως τότε 128,
        jr      c,rr_capok              ; και πάνω από τον 95ο κανείς δεν κινούνταν)
rr_cap_max:
        ld      a,AG_BOT0
rr_capok:
        ld      (EC_POPCAP),a

        ld      a,255
        ld      (EC_PADNODE),a
        ; ΟΙ ΔΟΜΕΣ ΕΙΝΑΙ 32, ΟΧΙ 64 (βήμα 90). Με 64 το πέρασμα συνέχιζε στον
        ; πίνακα διαδρόμων αμέσως μετά: χωρίς πλατφόρμα, ένας διάδρομος 0 με
        ; κατεύθυνση 6 (ST_KIND = C_DIR) και έτοιμος (ST_STATE = C_CSTATE)
        ; γινόταν πίστα στον κόμβο 96 — που δεν υπάρχει — και διπλάσιος δρόμος
        ; σε κάθε περιστροφή χωρίς πλατφόρμα, δηλαδή σε κάθε νέα παρτίδα.
        ld      ix,G_struct_tbl
        ld      bc,MAX_STRUCT * 256 + MAX_DOME  ; B = δομές, C = ο κόμβος της πρώτης
rr_pad:
        ld      a,(ix+ST_STATE)
        cp      DS_ACTIVE
        jr      nz,rr_pad_n
        ld      a,(ix+ST_KIND)
        cp      K_PAD
        jr      nz,rr_pad_n
        ld      a,c
        ld      (EC_PADNODE),a
        ret
rr_pad_n:
        ld      de,STRUCT_REC
        add     ix,de
        inc     c
        djnz    rr_pad
        ret

; rr_amenity — A = είδος δωματίου, IX -> θόλος. Μετράει σαλόνια και δέντρα.
; Το δέντρο είναι φυτό κατηγορίας 3 σε θερμοκήπιο. Χαλάει B, DE, HL.
rr_amenity:
        cp      R_LOUNGE
        jr      z,rr_am_one
        cp      R_GREENHS
        ret     nz
        ld      a,(ix+D_SIZE)           ; πόσες υποδοχές;
        add     a,G_machine_count & 255
        ld      l,a
        ld      h,G_machine_count >> 8
        ld      b,(hl)
        push    ix
        pop     hl
        ld      de,D_MACH
        add     hl,de
rr_am_lp:
        ld      a,(hl)
        cp      NO_MACH
        jr      z,rr_am_n
        add     a,G_plant_class & 255
        ld      e,a
        ld      d,G_plant_class >> 8
        ld      a,(de)
        and     3
        cp      3
        call    z,rr_am_one
rr_am_n:
        inc     hl
        djnz    rr_am_lp
        ret
rr_am_one:
        ld      a,(EC_AMENITY)
        inc     a
        ret     z                       ; ταβάνι το 255
        ld      (EC_AMENITY),a
        ret

nd_i:       db 0
