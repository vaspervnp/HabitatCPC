; flow.asm — η θέση 12 του τροχού: το ισοζύγιο ροών (DESIGN §6.5, §7.2).
;
; ΣΤΗΝ ΤΡΑΠΕΖΑ 6 από το βήμα 93, στη δέσμευση b6code, μαζί με τα ρομπότ και
; τα πλοία: ως τότε ήταν το μισό του src/econ.asm στην τράπεζα 0. Το καλεί
; μόνο ο τροχός, με την 6 στο παράθυρο, και ό,τι καλεί (ec_add16, ec_make,
; en_count) δεν σελιδοποιεί. Οι μεταβλητές του (ec_fdiv, ef_wat, ef_ore)
; έμειναν εκεί που ήταν: τις γράφουν και οι εργασίες και οι μετεωρίτες.
; Το εμπόριο ήθελε 840 bytes στην τράπεζα 0, που είχε 584.

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
        ; ΑΝΑΠΝΕΟΥΝ ΜΟΝΟ ΟΣΟΙ ΕΙΝΑΙ ΜΕΣΑ (βήμα 87): ο E μετρά τους ζωντανούς με
        ; F_INDOORS, και η ζήτηση οξυγόνου είναι αυτοί. Οι άλλοι είναι στη στολή.
        call    en_count                ; src/door.asm: C ζωντανοί, E μέσα
        ld      a,c
        ld      (EC_ALIVE),a
        or      a
        jr      nz,ef_alive
        inc     a
        ld      (EC_GAMEOVER),a         ; κανείς ζωντανός: τέλος (§10.3)
ef_alive:
        ld      l,e
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
