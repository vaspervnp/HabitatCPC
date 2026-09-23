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

NEED_LOW    equ 64
NEED_CRIT   equ 16
O2_REFILL   equ 2
ROOM_MAX    equ 8       ; τα R_* είναι στο const.asm

; ---------------------------------------------------------------------------
; ent_needs_slice — C = πρώτος, B = πλήθος.
; ---------------------------------------------------------------------------
ent_needs_slice:
        inc     b
        dec     b
        ret     z
ens_lp:
        ld      a,c
        ld      h,AG_PG
        ld      l,a
        ld      a,(hl)
        and     F_ALIVE
        jr      z,ens_next
        push    bc
        call    nd_one
        pop     bc
ens_next:
        ld      a,c
        inc     a
        and     N_AGENT - 1
        ld      c,a
        djnz    ens_lp
        ret

; ---------------------------------------------------------------------------
; nd_one — ένας άποικος. C = ταυτότητα.
;
; Το L ΚΡΑΤΑΕΙ ΤΗΝ ΤΑΥΤΟΤΗΤΑ ΑΠΟ ΤΗΝ ΑΡΧΗ ΩΣ ΤΟ ΤΕΛΟΣ. Κάθε πεδίο είναι τότε
; «ld h,σελίδα» και τίποτε άλλο — το bit 7 του L διαλέγει ποιο από τα δύο
; πεδία της σελίδας. Η πρώτη γραφή ξαναδιάβαζε την ταυτότητα από τη μνήμη
; δεκαπέντε φορές ανά άποικο, και αυτό ήταν ο μισός χρόνος του περάσματος.
; ---------------------------------------------------------------------------
nd_one:
        ld      a,c
        ld      (nd_i),a
        ld      l,a

        ; --- 1. φθορά: ένα ανά επίσκεψη, με πάτωμα στο μηδέν ---
        ld      h,AG_PG + 4
        ld      a,(hl)                  ; οξυγόνο
        or      a
        jr      z,nd_d2
        dec     a
        ld      (hl),a
nd_d2:  set     7,l
        ld      a,(hl)                  ; νερό
        or      a
        jr      z,nd_d3
        dec     a
        ld      (hl),a
nd_d3:  ld      h,AG_PG + 5
        res     7,l
        ld      a,(hl)                  ; τροφή
        or      a
        jr      z,nd_d4
        dec     a
        ld      (hl),a
nd_d4:  set     7,l
        ld      a,(hl)                  ; ύπνος
        or      a
        jr      z,nd_d5
        dec     a
        ld      (hl),a
nd_d5:  res     7,l

        ; --- 2. οξυγόνο: ροή, όχι ταξίδι ---
        ld      a,(EC_O2OK)
        or      a
        jr      z,nd_sat
        ld      h,AG_PG + 4
        ld      a,(hl)
        add     a,O2_REFILL
        jr      nc,nd_o2st
        ld      a,255
nd_o2st:
        ld      (hl),a

        ; --- 3. αν στέκεται σε θόλο, ό,τι έχει να του δώσει του το δίνει ---
nd_sat:
        ld      h,AG_PG + 2
        set     7,l
        ld      a,(hl)                  ; ακμή
        res     7,l
        cp      NO_EDGE
        jr      nz,nd_load              ; ταξιδεύει
        ld      h,AG_PG + 1
        ld      a,(hl)                  ; κόμβος
        cp      MAX_DOME
        jr      nc,nd_load              ; δομή, όχι θόλος
        call    nd_satisfy
        ld      a,(nd_i)
        ld      l,a                     ; το nd_satisfy πείραξε το HL

        ; --- B=οξυγόνο C=νερό D=τροφή E=ύπνος ---
nd_load:
        ld      h,AG_PG + 4
        ld      b,(hl)
        set     7,l
        ld      c,(hl)
        ld      h,AG_PG + 5
        res     7,l
        ld      d,(hl)
        set     7,l
        ld      e,(hl)
        res     7,l

        ; --- 4. υγεία ---
        ld      a,b
        cp      NEED_CRIT
        ld      a,0
        jr      nc,nd_h1
        ld      a,4
nd_h1:
        ld      (nd_dmg),a
        ld      a,c
        cp      NEED_CRIT
        jr      nc,nd_h2
        ld      a,(nd_dmg)
        add     a,2
        ld      (nd_dmg),a
nd_h2:
        ld      a,d
        cp      NEED_CRIT
        jr      nc,nd_h3
        ld      a,(nd_dmg)
        inc     a
        ld      (nd_dmg),a
nd_h3:
        ; Η αμμοθύελλα χτυπά όποιον είναι έξω — και έξω σημαίνει «σε εξωτερική
        ; δομή». Αυτό ακριβώς κάνει τη θέση του αεροφράκτη απόφαση (§6.2).
        ld      a,(EC_STORM)
        or      a
        jr      z,nd_h4
        ld      h,AG_PG + 1
        ld      a,(hl)
        cp      MAX_DOME
        jr      c,nd_h4
        ld      a,(nd_dmg)
        add     a,4
        ld      (nd_dmg),a
nd_h4:
        ld      h,AG_PG + 6
        ld      a,(nd_dmg)
        or      a
        jr      z,nd_recover
        ld      a,(hl)                  ; υγεία
        push    hl
        ld      hl,nd_dmg
        sub     (hl)
        pop     hl
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
        ld      a,(hl)
        cp      255
        jr      z,nd_death
        inc     a
        ld      (hl),a

        ; --- 5. θάνατος ---
nd_death:
        ld      h,AG_PG + 6
        ld      a,(hl)
        or      a
        jp      z,nd_die

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
        ld      (nd_min),a
        set     7,l                     ; ηθικό
        cp      NEED_CRIT
        jr      nc,nd_mo_up
        ld      a,(hl)
        sub     2
        jr      nc,nd_mo_st
        xor     a
        jr      nd_mo_st
nd_mo_up:
        ld      a,(nd_min)
        cp      NEED_LOW
        jr      c,nd_gloom
        ld      a,(hl)
        cp      255
        jr      z,nd_gloom
        inc     a
nd_mo_st:
        ld      (hl),a
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
        dec     a
        ld      (hl),a
nd_seek0:
        res     7,l

        ; --- 7. πού πρέπει να πάει ---
nd_seek:
        ld      h,AG_PG + 6
        ld      a,(hl)                  ; υγεία
        cp      NEED_LOW
        ld      a,R_MEDBAY
        jr      c,nd_want
        ld      a,d                     ; τροφή
        cp      NEED_LOW
        ld      a,R_CANTEEN
        jr      c,nd_want
        ld      a,c                     ; νερό
        cp      NEED_LOW
        ld      a,R_CANTEEN
        jr      c,nd_want
        ld      a,e                     ; ύπνος
        cp      NEED_LOW
        ret     nc                      ; δεν του λείπει τίποτα
        ld      a,R_QUARTERS
nd_want:
        ld      (nd_room),a

        ; Πάει ήδη σε τέτοιο δωμάτιο; Τότε τελειώσαμε.
        ld      h,AG_PG + 2
        ld      a,(hl)                  ; προορισμός
        cp      MAX_DOME
        jr      nc,nd_search
        call    jb_dome_ptr
        ld      de,D_ROOM
        add     hl,de
        ld      a,(hl)
        ld      hl,nd_room
        cp      (hl)
        ret     z
nd_search:
        ld      a,(nd_i)
        ld      l,a
        ld      h,AG_PG + 1
        ld      a,(hl)
        ld      (nd_node),a
        ld      a,(nd_room)
        call    nd_nearest
        cp      255
        ret     z                       ; δεν υπάρχει τέτοιο δωμάτιο
        ld      c,a
        ld      a,(nd_i)                ; αφήνει τη δουλειά του (§6.7)
        ld      l,a
        ld      h,AG_PG + 3
        set     7,l
        ld      (hl),NO_TASK
        res     7,l
        ld      h,AG_PG + 2
        ld      (hl),c                  ; dest = ο θόλος
        ret

; ---------------------------------------------------------------------------
; nd_satisfy — A = θόλος. Ο,τι έχει το δωμάτιο να δώσει.
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
        call    jb_dome_ptr
        ld      de,D_ROOM
        add     hl,de
        ld      a,(hl)
        cp      R_QUARTERS
        jr      z,nds_sleep
        cp      R_CANTEEN
        jr      z,nds_canteen
        cp      R_MEDBAY
        ret     nz

        ; --- ιατρείο: φάρμακο για υγεία ---
        ld      a,(nd_i)
        ld      h,AG_PG + 6
        ld      l,a
        ld      a,(hl)
        cp      NEED_LOW
        ret     nc
        ld      a,7                     ; S_MEDI
        ld      c,32
        jp      nds_spend

nds_sleep:
        ld      a,(nd_i)
        ld      h,AG_PG + 5
        ld      l,a
        set     7,l
        ld      (hl),255                ; ΓΕΜΑΤΟ, όχι +64: βλ. παρακάτω
        ret

nds_canteen:
        ; τροφή
        ld      a,(nd_i)
        ld      h,AG_PG + 5
        ld      l,a
        ld      a,(hl)
        cp      NEED_LOW
        jr      nc,nds_water
        ld      a,1                     ; S_FOOD
        ld      c,255
        call    nds_spend
nds_water:
        ld      a,(nd_i)
        ld      h,AG_PG + 4
        ld      l,a
        set     7,l
        ld      a,(hl)
        cp      NEED_LOW
        ret     nc
        ld      a,0                     ; S_WATER
        ld      c,255
        ; πέφτει μέσα

; nds_spend — A = απόθεμα, C = πόσο δίνει, HL = το πεδίο της ανάγκης.
nds_spend:
        push    hl
        call    ec_stock_ptr            ; DE = &stock[A]
        ld      a,(de)
        ld      l,a
        inc     de
        ld      a,(de)
        or      l
        jr      z,nds_none              ; άδειο
        dec     de
        ld      a,(de)
        sub     1
        ld      (de),a
        inc     de
        ld      a,(de)
        sbc     a,0
        ld      (de),a
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
; nd_die — θέση, δουλειά, χειριστής, πένθος.
; ---------------------------------------------------------------------------
nd_die:
        ld      a,SFX_DEATH
        call    snd_ping                ; δεν χαλάει καταχωρητές: §9.5
        ld      a,(nd_i)
        ld      h,AG_PG
        ld      l,a
        ld      a,(hl)
        and     F_WORKING
        jr      z,nd_d_slot
        ld      a,(nd_i)
        ld      h,AG_PG + 1
        ld      l,a
        ld      a,(hl)
        cp      MAX_DOME
        jr      nc,nd_d_slot
        call    jb_dome_ptr
        ld      de,D_OPS
        add     hl,de
        dec     (hl)
nd_d_slot:
        ld      a,(nd_i)
        ld      (em_id),a
        ld      h,AG_PG + 1
        ld      l,a
        ld      a,(hl)
        ld      (em_node),a
        call    ent_release             ; ελευθερώνει και μηδενίζει το slot

        ld      a,(nd_i)
        ld      h,AG_PG
        ld      l,a
        ld      (hl),0                  ; δεν ζει πια
        ld      h,AG_PG + 2
        set     7,l
        ld      (hl),NO_EDGE
        ld      h,AG_PG + 3
        ld      (hl),NO_TASK
        res     7,l
        ld      (hl),0                  ; progress

        ld      a,(EC_GLOOM)            ; το πένθος, με ταβάνι
        add     a,16
        jr      nc,nd_gl
        ld      a,255
nd_gl:
        ld      (EC_GLOOM),a
        ld      a,(EC_DEATHS)           ; για το σερί «χωρίς θανάτους» (§10.2)
        inc     a
        jr      z,nd_dths
        ld      (EC_DEATHS),a
nd_dths:
        ret

; ---------------------------------------------------------------------------
; nd_nearest — A = είδος δωματίου, (nd_node) = κόμβος. A = θόλος ή 255.
;
; Η τράπεζα 1 μπαίνει μία φορά για ως οκτώ υποψηφίους, όχι μία ανά υποψήφιο.
; ---------------------------------------------------------------------------
nd_nearest:
        ld      hl,G_room_n
        add     a,l
        ld      l,a
        ld      a,0
        adc     a,h
        ld      h,a
        ld      b,(hl)
        inc     b
        dec     b
        ld      a,255
        ret     z                       ; δεν υπάρχει κανένα τέτοιο δωμάτιο

        ; DE = η λίστα υποψηφίων
        ld      a,(nd_room)
        ld      h,0
        ld      l,a
        add     hl,hl
        add     hl,hl
        add     hl,hl                   ; *8
        ld      de,G_room_list
        add     hl,de
        ex      de,hl

        ; Η ΓΡΑΜΜΗ ΤΟΥ DIST ΥΠΟΛΟΓΙΖΕΤΑΙ ΜΙΑ ΦΟΡΑ. Ηταν μέσα στον βρόχο, και
        ; ο πολλαπλασιασμός x128 ανά υποψήφιο ήταν το μισό κόστος της
        ; αναζήτησης — που τρέχει για κάθε άποικο που του λείπει κάτι.
        ld      a,(nd_node)
        ld      h,a
        ld      l,0
        srl     h
        rr      l
        set     6,h                     ; το DIST κάθεται στο &4000
        ld      (nd_row),hl

        ld      a,255
        ld      (nd_bestd),a
        ld      (nd_best),a

        ld      hl,GA_PORT + PAGE_B1
        push    bc
        ld      b,h
        ld      c,l
        out     (c),c
        pop     bc
ndn_lp:
        ld      a,(de)                  ; υποψήφιος θόλος
        inc     de
        ld      (nd_cand),a
        ld      hl,(nd_row)
        add     a,l                     ; ο θόλος είναι < 64: δεν κρατάει
        ld      l,a
        ld      a,(hl)                  ; απόσταση
        ld      hl,nd_bestd
        cp      (hl)
        jr      nc,ndn_n
        ld      (hl),a
        ld      a,(nd_cand)
        ld      (nd_best),a
ndn_n:
        djnz    ndn_lp

        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        ld      a,(nd_best)
        ret

; ---------------------------------------------------------------------------
; rooms_rebuild — θέση 14: ποιοι θόλοι είναι τι. 64 εγγραφές ανά περιστροφή.
; ---------------------------------------------------------------------------
rooms_rebuild:
        ld      hl,G_room_n
        ld      b,12
rr_clr:
        ld      (hl),0
        inc     hl
        djnz    rr_clr
        xor     a
        ld      (rr_amen),a

        ld      hl,G_dome_tbl
        ld      c,0                     ; C = δείκτης θόλου
rr_lp:
        push    hl
        ld      de,D_STATE
        add     hl,de
        ld      a,(hl)
        cp      DS_ACTIVE
        jr      nz,rr_next
        pop     hl
        push    hl
        ld      de,D_ROOM
        add     hl,de
        ld      a,(hl)
        cp      12
        jr      nc,rr_next
        ld      e,a                     ; E = είδος
        push    de
        push    bc
        call    rr_amenity              ; σαλόνια και δέντρα (§6.6)
        pop     bc
        pop     de
        ld      a,e
        ld      hl,G_room_n
        add     a,l
        ld      l,a
        ld      a,0
        adc     a,h
        ld      h,a
        ld      a,(hl)
        cp      ROOM_MAX
        jr      nc,rr_next              ; γέμισε αυτό το είδος
        ld      d,a                     ; D = θέση μέσα στη λίστα
        inc     (hl)
        ld      a,e
        ld      h,0
        ld      l,a
        add     hl,hl
        add     hl,hl
        add     hl,hl                   ; είδος*8
        ld      a,d
        add     a,l
        ld      l,a
        ld      a,0
        adc     a,h
        ld      h,a
        ld      de,G_room_list
        add     hl,de
        ld      (hl),c
rr_next:
        pop     hl
        ld      de,DOME_REC
        add     hl,de
        inc     c
        ld      a,c
        cp      MAX_DOME
        jr      c,rr_lp
        ld      a,(rr_amen)
        ld      (EC_AMENITY),a

        ; Το ταβάνι πληθυσμού είναι δουλειά του Control (§6.8), και η πίστα
        ; είναι ο κόμβος όπου κατεβαίνει ο κόσμος (§6.11). Και τα δύο βγαίνουν
        ; από ένα πέρασμα που γίνεται ούτως ή άλλως.
        ld      hl,G_room_n + R_CONTROL
        ld      a,(hl)
        ld      b,a
        ld      a,4
        inc     b
rr_cap:
        dec     b
        jr      z,rr_capst
        add     a,POP_PER_CTL
        jr      nc,rr_cap
        ld      a,128
        jr      rr_capst
rr_capst:
        cp      129
        jr      c,rr_capok
        ld      a,128
rr_capok:
        ld      (EC_POPCAP),a

        ld      a,255
        ld      (EC_PADNODE),a
        ld      hl,G_struct_tbl
        ld      b,64
        ld      c,0
rr_pad:
        push    hl
        ld      de,ST_STATE
        add     hl,de
        ld      a,(hl)
        pop     hl
        cp      DS_ACTIVE
        jr      nz,rr_pad_n
        push    hl
        ld      de,ST_KIND
        add     hl,de
        ld      a,(hl)
        pop     hl
        cp      K_PAD
        jr      nz,rr_pad_n
        ld      a,c
        add     a,MAX_DOME
        ld      (EC_PADNODE),a
        ret
rr_pad_n:
        ld      de,STRUCT_REC
        add     hl,de
        inc     c
        djnz    rr_pad
        ret

; rr_amenity — A/E = είδος δωματίου, (HL στο D_ROOM του θόλου). Μετράει
; σαλόνια και δέντρα. Το δέντρο είναι φυτό κατηγορίας 3 σε θερμοκήπιο.
rr_amenity:
        cp      R_LOUNGE
        jr      z,rr_am_one
        cp      R_GREENHS
        ret     nz
        ; πόσες υποδοχές;
        ld      de,D_SIZE - D_ROOM
        add     hl,de
        ld      a,(hl)
        ld      de,D_ROOM - D_SIZE
        add     hl,de
        push    hl
        ld      hl,G_machine_count
        add     a,l
        ld      l,a
        ld      a,0
        adc     a,h
        ld      h,a
        ld      b,(hl)
        pop     hl
        ld      de,D_MACH - D_ROOM
        add     hl,de
rr_am_lp:
        ld      a,(hl)
        cp      NO_MACH
        jr      z,rr_am_n
        push    hl
        ld      hl,G_plant_class
        add     a,l
        ld      l,a
        ld      a,0
        adc     a,h
        ld      h,a
        ld      a,(hl)
        pop     hl
        and     3
        cp      3
        jr      nz,rr_am_n
        push    hl
        call    rr_am_one
        pop     hl
rr_am_n:
        inc     hl
        djnz    rr_am_lp
        ret
rr_am_one:
        ld      a,(rr_amen)
        cp      255
        ret     z
        inc     a
        ld      (rr_amen),a
        ret

nd_i:       db 0
nd_dmg:     db 0
nd_min:     db 0
nd_room:    db 0
nd_node:    db 0
nd_best:    db 0
nd_bestd:   db 0
nd_cand:    db 0
nd_row:     dw 0
rr_amen:    db 0
