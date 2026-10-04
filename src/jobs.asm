; jobs.asm — ο πίνακας εργασιών (§6.7), θέση 13 του τροχού
;
; Τέσσερα πράγματα με αυτή τη σειρά, και η σειρά μετράει:
;
;   1. ΜΑΖΕΜΑ      όποιος πέθανε ή άλλαξε γνώμη αφήνει την εργασία ανοιχτή.
;   2. ΟΛΟΚΛΗΡΩΣΗ  όποιος έφτασε πιάνει δουλειά — ο θόλος αποκτά χειριστή και
;                  οι μηχανές του αρχίζουν να γυρίζουν. ΕΔΩ κλείνει ο κύκλος:
;                  χωρίς αυτό ο πίνακας εργασιών δεν κάνει τίποτα ορατό.
;   3. ΔΗΜΟΣΙΕΥΣΗ  JOB_SCAN θόλοι ανά επίσκεψη, περιστροφικά.
;   4. ΑΝΑΘΕΣΗ     ως JOB_ASSIGN, με τη μεγαλύτερη προτεραιότητα και ισοπαλία
;                  στο DIST.
;
; ΤΟ ΠΑΡΑΘΥΡΟ, ΠΑΛΙ. Η ανάθεση διαβάζει το DIST (τράπεζα 1) και τα πεδία των
; πρακτόρων (τράπεζα 6) — δεν φαίνονται μαζί. Ο πίνακας εργασιών ζει στην
; τράπεζα 2 γι' αυτόν ακριβώς τον λόγο, και η σελιδοποίηση γίνεται ΜΙΑ φορά
; γύρω από όλη τη φάση ανάθεσης, όχι μία ανά ανάγνωση.
;
; Η ΣΥΜΒΑΣΗ ΚΟΜΒΩΝ: κόμβος < 64 είναι ο θόλος με το ίδιο id· από κει και πάνω
; είναι η δομή n-64. 64 + 64 = 128, ακριβώς το ταβάνι κόμβων του §6.2.

NO_TASK     equ 255
JOB_SCAN    equ 4
JOB_ASSIGN  equ 4
JOB_LOOK    equ 32                  ; πράκτορες που εξετάζονται ανά επίσκεψη
F_WORKING   equ 32
        assert  F_WORKING == 1 << 5     ; entity.asm: bit/res 5

        assert  D_INTEG == D_STATE + 1 && D_OPS == D_STATE + 3
        assert  D_ROOM == D_MACH - 5 && D_HEALTH == D_MACH + 8
        assert  (MAX_DOME & (MAX_DOME - 1)) == 0    ; and αντί για σύγκριση
        assert  (G_machine_count & 255) <= 256 - 3
        assert  (G_mach_op & 255) <= 256 - 12

jobs_tick:
        call    jb_reap
        call    jb_arrive
        call    jb_post
        jp      jb_assign

; ---------------------------------------------------------------------------
; 1. όποιος πέθανε ή δεν κρατά πια αυτή την εργασία, την αφήνει
; ---------------------------------------------------------------------------
jb_reap:
        ld      hl,G_job_tbl
        ld      b,MAX_JOB
        ld      c,0                     ; C = δείκτης εργασίας
jr_lp:
        ld      a,(hl)
        cp      NO_JOB
        jr      z,jr_next
        push    hl
        inc     hl
        inc     hl
        ld      a,(hl)                  ; ο πράκτορας
        ld      e,a
        inc     a
        jr      z,jr_pop                ; αδιάθετη
        ld      d,AG_PG                 ; flags
        ld      a,(de)
        and     F_ALIVE
        jr      z,jr_free
        set     7,e                     ; το task είναι στο ΠΑΝΩ μισό
        ld      d,AG_PG + 3
        ld      a,(de)
        cp      c
        jr      z,jr_pop
jr_free:
        ld      (hl),255
jr_pop:
        pop     hl
jr_next:
        ld      de,JOB_REC
        add     hl,de
        inc     c
        djnz    jr_lp
        ret

; ---------------------------------------------------------------------------
; 2. όποιος έφτασε, πιάνει δουλειά
;
; Η εγγραφή της εργασίας μένει στη στοίβα όλο τον γύρο. Οι τρεις τρόποι να
; τελειώσει — χειριστής, επισκευή, κατασκευή — καταλήγουν στο ίδιο ja_done·
; ως το βήμα 46 ήταν τρία αντίγραφα του.
; ---------------------------------------------------------------------------
jb_arrive:
        ld      hl,G_job_tbl
        ld      b,MAX_JOB
ja_lp:
        push    bc
        push    hl
        ld      a,(hl)
        cp      NO_JOB
        jr      z,ja_next
        inc     hl
        ld      c,(hl)                  ; C = κόμβος
        inc     hl
        ld      a,(hl)                  ; ο πράκτορας
        ld      e,a
        inc     a
        jr      z,ja_next               ; αδιάθετη
        ld      a,e
        ld      (jb_ag),a
        ld      d,AG_PG + 1             ; node
        ld      a,(de)
        cp      c
        jr      nz,ja_next              ; δεν έφτασε ακόμη
        set     7,e
        inc     d                       ; AG_PG + 2: το edge, στο πάνω μισό
        ld      a,(de)
        inc     a
        jr      nz,ja_next              ; ακόμη στον σωλήνα
        pop     hl
        push    hl
        ld      a,(hl)
        cp      J_BUILD
        jr      z,ja_build              ; ο πράκτορας δουλεύει και μένει
        cp      J_REPAIR
        jr      z,ja_repair             ; φτάνει, αλλάζει το εξάρτημα, φεύγει
        ; --- ο θόλος αποκτά χειριστή ---
        ld      a,c
        cp      MAX_DOME
        jr      nc,ja_flags             ; δομή, όχι θόλος: δεν έχει ops
        call    jb_dome_ptr
        ld      de,D_OPS
        add     hl,de
        inc     (hl)
ja_flags:
        ld      a,(jb_ag)
        ld      e,a
        ld      d,AG_PG
        ld      a,(de)
        or      F_WORKING
        ld      (de),a
ja_done:                                ; η εργασία τελείωσε
        call    ja_cleartask
        pop     hl
        push    hl
        ld      (hl),NO_JOB
ja_next:
        pop     hl
        ld      de,JOB_REC
        add     hl,de
        pop     bc
        djnz    ja_lp
        ret

; --- επισκευή: C = ο θόλος ---
; Το jb_broken αφήνει τον IX πάνω στην υποδοχή που βρήκε, και η υγεία είναι
; οκτώ bytes πιο κάτω· ως το βήμα 46 η υποδοχή περνούσε από μεταβλητή και η
; διεύθυνση ξαναφτιαχνόταν από την αρχή.
ja_repair:
        ld      a,c
        ld      (jb_d),a
        call    jb_broken
        inc     a
        jr      z,ja_fail
        ld      a,S_SPARE               ; χρειάζεται ένα ανταλλακτικό
        ld      c,1
        call    ec_have
        jr      c,ja_fail
        ld      a,c
        call    ec_sub                  ; src/econ.asm
        ld      (ix+D_HEALTH-D_MACH),200 ; ξαναδουλεύει
        jr      ja_done
ja_fail:
        ; τζάμπα δρόμος: η εργασία μένει ανοιχτή για τον επόμενο
        call    ja_cleartask
        pop     hl
        push    hl
        inc     hl
        inc     hl
        ld      (hl),255
        jr      ja_next

; ---------------------------------------------------------------------------
; ja_build — ο πράκτορας δουλεύει στο εργοτάξιο (§6.9 βήμα 3). C = ο κόμβος.
;
; Η ΠΡΟΟΔΟΣ ΕΙΝΑΙ Η ΑΚΕΡΑΙΟΤΗΤΑ. Το §6.9 λέει «η πρόοδος είναι ένα byte» και η
; εγγραφή έχει ήδη ένα: το bd_commit γράφει ακεραιότητα 0, και η κατασκευή την
; ανεβάζει ως το 255 — οπότε ένα μισοχτισμένο κτίριο είναι το ίδιο πράγμα με
; ένα μισοκατεστραμμένο, που είναι σωστό και γλιτώνει ένα byte ανά κόμβο.
;
; Το D_STATE και το D_INTEG είναι στα ίδια offsets με το ST_STATE και το
; ST_INTEG, οπότε θόλος και δομή περνούν από τον ίδιο κώδικα — και από το
; ίδιο mt_rec του μετεωρίτη για την εγγραφή.
BUILD_STEP  equ 32                  ; οκτώ επισκέψεις = ~2,6 δευτερόλεπτα

ja_build:
        ld      a,c
        call    mt_rec                  ; HL = εγγραφή (src/meteor.asm)
        ld      de,D_INTEG
        add     hl,de
        ld      a,(hl)
        add     a,BUILD_STEP
        jr      nc,jab_st
        ld      a,255
jab_st:
        ld      (hl),a
        inc     a
        jr      nz,ja_next              ; ακόμη χτίζεται· η εργασία μένει
        dec     hl                      ; D_STATE
        ld      (hl),DS_ACTIVE
        ; ΤΟ ΚΤΙΡΙΟ ΠΡΕΠΕΙ ΝΑ ΦΑΝΕΙ — και η σκηνή μαθαίνει ΠΟΙΟ. Ως το βήμα 34
        ; ήταν μια σημαία, και ο βρόχος ξαναζωγράφιζε ολόκληρο το κάδρο γιατί
        ; δεν ήξερε τι άλλαξε: 0,36-0,92 s παγωμένη οθόνη ανά κτίριο (§6.9).
        ld      b,c
        ld      a,DK_BUILT
        call    wh_push
        ; ΚΑΙ ΤΟ ΙΣΟΖΥΓΙΟ ΞΑΝΑΜΕΤΡΑΕΙ ΑΜΕΣΩΣ. Ο κύκλος ροής είναι 64
        ; περιστροφές (~20 δευτερόλεπτα): χωρίς αυτό, το πρώτο ηλιακό πάνελ
        ; του παίκτη έβγαζε ρεύμα και το HUD συνέχιζε να γράφει NO POWER ως
        ; να έρθει η σειρά του κύκλου. Οτι αλλάζει την αποικία, ξαναμετριέται.
        ld      a,1
        ld      (ec_fdiv),a
        jr      ja_done

ja_cleartask:
        ld      a,(jb_ag)
        ld      e,a
        set     7,e
        ld      d,AG_PG + 3
        ld      a,NO_TASK
        ld      (de),a
        ret

; ---------------------------------------------------------------------------
; 3. δημοσίευση: JOB_SCAN θόλοι, περιστροφικά
; ---------------------------------------------------------------------------
jb_post:
        ld      b,JOB_SCAN
jp_lp:
        push    bc
        ld      a,(EC_JDOME)
        ld      (jb_d),a
        inc     a
        and     MAX_DOME - 1
        ld      (EC_JDOME),a
        call    jp_one
        pop     bc
        djnz    jp_lp
        ret

jp_one:
        ; Μία εργασία ανά θόλο ανά επίσκεψη, και η επισκευή προηγείται: μια
        ; σταματημένη μηχανή δεν θέλει χειριστή, θέλει μηχανικό.
        ld      a,J_REPAIR
        ld      (jb_kind2),a
        call    jb_broken
        inc     a
        jr      nz,jp_have
        ld      a,J_OPERATE
        ld      (jb_kind2),a
        call    jb_need                 ; HL -> D_STATE του θόλου
        or      a
        ret     z
        dec     a
        inc     hl
        inc     hl
        inc     hl                      ; D_OPS
        cp      (hl)
        ret     c                       ; έχει ήδη αρκετούς: θέλει <= έχει
jp_have:

        ; ΕΝΑ πέρασμα: βρίσκει και το διπλότυπο και την πρώτη ελεύθερη θέση.
        ; Δύο ξεχωριστές σαρώσεις των 32 ήταν η μισή δουλειά της δημοσίευσης.
        ; Η ελεύθερη στο DE, όχι σε μεταβλητή με push / pop σε κάθε εγγραφή.
        ld      a,(jb_d)
        ld      c,a
        ld      hl,G_job_tbl
        ld      b,MAX_JOB
        ld      de,0                    ; 0 = δεν βρέθηκε ελεύθερη
jp_dup:
        ld      a,(hl)
        cp      NO_JOB
        jr      z,jp_free
        ld      a,(jb_kind2)
        cp      (hl)
        jr      nz,jp_dup_n
        inc     hl
        ld      a,(hl)
        dec     hl
        cp      c
        ret     z                       ; υπάρχει ήδη — δεν ξαναδημοσιεύουμε
        jr      jp_dup_n
jp_free:
        ld      a,d
        or      e
        jr      nz,jp_dup_n             ; έχουμε ήδη μία ελεύθερη
        ld      d,h
        ld      e,l
jp_dup_n:
        repeat  JOB_REC
        inc     hl
        rend
        djnz    jp_dup

        ex      de,hl
        ld      a,h
        or      l
        ret     z                       ; ο πίνακας γέμισε
        ld      a,(jb_kind2)
        ld      (hl),a
        inc     hl
        ld      (hl),c                  ; ο θόλος
        inc     hl
        ld      (hl),255                ; αδιάθετη
        inc     hl
        ; Η ΠΡΟΤΕΡΑΙΟΤΗΤΑ ΤΟΥ OPERATE ΒΓΑΙΝΕΙ ΑΠΟ ΤΟ ΔΩΜΑΤΙΟ. Με μία κοινή
        ; τιμή για όλα τα μηχανήματα η ισοπαλία έσπαγε στην ΑΠΟΣΤΑΣΗ, και η
        ; απόσταση δεν αλλάζει: ο κοντινότερος θόλος έπαιρνε κάθε φορά όλο τον
        ; κόσμο και το κυλικείο του παίκτη έμενε αστελέχωτο για πάντα —
        ; μετρημένο, 147 δείγματα στη σειρά με την εργασία του αδιάθετη, ενώ
        ; το θερμοκήπιο δίπλα του στοίβαζε 250 άμυλο που κανείς δεν μαγείρευε.
        ; Το δωμάτιο το κράτησε το jb_need.
        push    hl
        ld      hl,job_prio
        cp      J_OPERATE
        jr      nz,jpw_look
        ld      a,(jb_room)
        ld      hl,room_prio
jpw_look:
        add     a,l
        ld      l,a
        adc     a,h
        sub     l
        ld      h,a
        ld      a,(hl)
        pop     hl
        ld      (hl),a
        inc     hl
        ld      (hl),0
        ret

; jb_slots — (jb_d) = θόλος. Z αν είναι χτισμένος, και τότε HL -> D_STATE,
; IX -> υποδοχή 0, B = πόσες υποδοχές έχει το μέγεθός του, A = το δωμάτιο.
; NZ αν δεν είναι. Χαλάει DE.
;
; Ο ΙΧ ΠΕΡΠΑΤΑΕΙ ΤΙΣ ΥΠΟΔΟΧΕΣ, και η υγεία είναι πάντα στο (ix+8): ως το βήμα
; 46 κάθε υποδοχή ήθελε push / add / pop για να τη φτάσει, και το «χτισμένος;
; πόσες υποδοχές;» ήταν γραμμένο χωριστά στο jb_broken και στο jb_need.
jb_slots:
        ld      a,(jb_d)
        call    jb_dome_ptr
        ld      de,D_STATE
        add     hl,de
        ld      a,(hl)
        cp      DS_ACTIVE
        ret     nz
        push    hl
        pop     ix
        ld      a,(ix+D_SIZE-D_STATE)
        add     a,G_machine_count & 255
        ld      e,a
        ld      d,G_machine_count / 256
        ld      a,(de)
        ld      b,a
        ld      de,D_MACH - D_STATE
        add     ix,de
        ld      a,(ix+D_ROOM-D_MACH)
        cp      a                       ; Z: το add a,n πιο πάνω το είχε χαλάσει
        ret

; jb_broken — (jb_d) = θόλος. A = η πρώτη σταματημένη υποδοχή, και IX ->
; αυτήν· ή A = 255.
jb_broken:
        call    jb_slots
        jr      nz,jbr_no
        ld      c,0
jbr_lp:
        ld      a,(ix+0)
        inc     a
        jr      z,jbr_n                 ; NO_MACH
        ld      a,(ix+D_HEALTH-D_MACH)
        or      a
        ld      a,c
        ret     z                       ; βρέθηκε
jbr_n:
        inc     ix
        inc     c
        djnz    jbr_lp
jbr_no:
        ld      a,255
        ret

; jb_need — (jb_d) = θόλος -> A = πόσες μηχανές του θέλουν χειριστή, και
; (jb_room) = το δωμάτιο, HL -> D_STATE αν είναι χτισμένος.
jb_need:
        call    jb_slots
        jr      nz,jn_zero
        ld      (jb_room),a
        ld      c,0
        cp      R_GREENHS
        jr      z,jn_green
jn_lp:
        ld      a,(ix+0)
        cp      NO_MACH
        jr      z,jn_next
        ld      e,a
        ld      a,(ix+D_HEALTH-D_MACH)
        or      a
        jr      z,jn_next               ; χαλασμένη
        ld      a,e
        add     a,G_mach_op & 255
        ld      e,a
        ld      d,G_mach_op / 256
        ld      a,(de)
        or      a
        jr      z,jn_next
        inc     c
jn_next:
        inc     ix
        djnz    jn_lp
        ld      a,c
        ret

; Το θερμοκήπιο: ΕΝΑΣ χειριστής, αν έχει έστω ένα ζωντανό φυτό. Ζητάει έναν,
; όχι έναν ανά γλάστρα: το ec_run_plant ποτίζει όλο τον θόλο με τον πρώτο.
; Οσο ζητούσε τέσσερις, ο πίνακας εργασιών έστελνε τέσσερις — και το
; κυλικείο περίμενε μαγείρα.
jn_green:
        ld      a,(ix+0)
        inc     a
        jr      z,jng_n
        ld      a,(ix+D_HEALTH-D_MACH)
        or      a
        ld      a,1
        ret     nz
jng_n:
        inc     ix
        djnz    jn_green
jn_zero:
        xor     a
        ret

; jb_dome_ptr — A = θόλος -> HL = εγγραφή
jb_dome_ptr:
        ld      h,0
        ld      l,a
        add     hl,hl
        add     hl,hl
        add     hl,hl
        ld      d,h
        ld      e,l
        add     hl,hl
        add     hl,de                   ; *24
        ld      de,G_dome_tbl
        add     hl,de
        ret

job_prio:   db 5,3,2,4,6,8,9

; Προτεραιότητα OPERATE ανά δωμάτιο (§6.7). Πρώτα ό,τι κρατά ανθρώπους στη
; ζωή, μετά ό,τι το ταΐζει, μετά η βιομηχανία:
;   empty control quarters canteen oxygen greenhouse storage airlock
;   factory lab medbay lounge
room_prio:  db 3,3,3,5,5,4,3,3,3,4,4,3

; ---------------------------------------------------------------------------
; 4. ανάθεση: ως JOB_ASSIGN, κοιτάζοντας ως JOB_LOOK πράκτορες
; ---------------------------------------------------------------------------
jb_assign:
        ; Πρώτα: υπάρχει καθόλου αδιάθετη εργασία; Στη μόνιμη κατάσταση δεν
        ; υπάρχει, και χωρίς αυτόν τον έλεγχο κάθε αδρανής πράκτορας σάρωνε
        ; και τις 32 εγγραφές για να μη βρει τίποτα — 36 ms τη θέση.
        ld      hl,G_job_tbl
        ld      b,MAX_JOB
jba_any:
        ld      a,(hl)
        cp      NO_JOB
        jr      z,jba_an
        inc     hl
        inc     hl
        ld      a,(hl)
        dec     hl
        dec     hl
        inc     a
        jr      z,jba_go                ; βρέθηκε αδιάθετη
jba_an:
        ld      de,JOB_REC
        add     hl,de
        djnz    jba_any
        jr      jas_done                ; καμία: ο δείκτης προχωράει, τέλος
jba_go:
        ld      a,(EC_JAGENT)
        ld      (jb_i),a
        xor     a
        ld      (jb_done),a
        ld      b,JOB_LOOK
jas_lp:
        push    bc
        ld      a,(jb_done)
        cp      JOB_ASSIGN
        jr      nc,jas_stop

        ld      a,(jb_i)
        ld      e,a
        ld      d,AG_PG
        ld      a,(de)                  ; flags
        and     F_ALIVE + F_WORKING
        cp      F_ALIVE
        jr      nz,jas_next             ; νεκρός, ή δουλεύει ήδη
        set     7,e
        ld      d,AG_PG + 3             ; task
        ld      a,(de)
        inc     a                       ; NO_TASK
        jr      nz,jas_next
        ld      d,AG_PG                 ; role, στο πάνω μισό
        ld      a,(de)
        and     7
        ld      b,a
        inc     b
        ld      a,#80
jas_rb:
        rlca
        djnz    jas_rb                  ; A = 1 << ρόλος
        ld      (jb_rolebit),a
        res     7,e
        inc     d                       ; AG_PG + 1: node
        ld      a,(de)
        ; Η ΓΡΑΜΜΗ ΤΟΥ DIST μία φορά ανά πράκτορα: #4000 + 128 * κόμβος. Ως το
        ; βήμα 46 υπολογιζόταν ξανά για καθεμία από τις 32 εργασίες.
        ld      h,a
        ld      l,0
        srl     h
        rr      l
        set     6,h
        ld      (jb_row),hl

        call    jb_best
        cp      NO_JOB
        jr      z,jas_next
        call    jb_take
        ld      hl,jb_done
        inc     (hl)
jas_next:
        ld      a,(jb_i)
        inc     a
        and     127
        ld      (jb_i),a
        pop     bc
        djnz    jas_lp
        jr      jas_done
jas_stop:
        pop     bc
jas_done:
        ld      a,(EC_JAGENT)
        add     a,JOB_LOOK
        and     127
        ld      (EC_JAGENT),a
        ret

; ---------------------------------------------------------------------------
; jb_best — η καλύτερη ανοιχτή εργασία για τον (jb_i). A = δείκτης ή NO_JOB.
;
; Η τράπεζα 1 μπαίνει ΜΙΑ φορά για όλη τη σάρωση των 32 εργασιών, όχι μία ανά
; ανάγνωση: ο πίνακας εργασιών είναι στην τράπεζα 2 και φαίνεται πάντα. Ο
; δείκτης της εργασίας είναι MAX_JOB - B, όχι δική του μεταβλητή.
; ---------------------------------------------------------------------------
jb_best:
        ld      hl,NO_JOB               ; jb_bj = NO_JOB, jb_bp = 0
        ld      (jb_bj),hl
        ld      a,255
        ld      (jb_bd),a

        ld      bc,GA_PORT + PAGE_B1
        out     (c),c

        ld      hl,G_job_tbl
        ld      b,MAX_JOB
jbb_lp:
        push    bc
        push    hl
        ld      a,(hl)
        cp      NO_JOB
        jr      z,jbb_next
        ld      c,a                     ; C = είδος
        inc     hl
        ld      e,(hl)                  ; E = κόμβος εργασίας
        inc     hl
        ld      a,(hl)
        inc     a
        jr      nz,jbb_next             ; ήδη ανατεθειμένη
        inc     hl
        ld      d,(hl)                  ; D = προτεραιότητα

        ld      hl,job_roles
        ld      a,c
        add     a,l
        ld      l,a
        adc     a,h
        sub     l
        ld      h,a
        ld      a,(jb_rolebit)
        and     (hl)
        jr      z,jbb_next              ; λάθος ρόλος

        ld      hl,(jb_row)             ; DIST[κόμβος πράκτορα][κόμβος εργασίας]
        ld      a,l
        add     a,e
        ld      l,a
        ld      c,(hl)                  ; C = απόσταση

        ld      hl,jb_bp
        ld      a,d
        cp      (hl)
        jr      c,jbb_next
        jr      nz,jbb_better
        ld      a,c
        inc     hl                      ; jb_bd
        cp      (hl)
        jr      nc,jbb_next
jbb_better:
        ld      h,c
        ld      l,d
        ld      (jb_bp),hl              ; jb_bp = D, jb_bd = C
        ld      a,MAX_JOB
        sub     b
        ld      (jb_bj),a
jbb_next:
        pop     hl
        ld      de,JOB_REC
        add     hl,de
        pop     bc
        djnz    jbb_lp

        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        ld      a,(jb_bj)
        ret

; ---------------------------------------------------------------------------
; jb_take — ο (jb_i) παίρνει την εργασία A. Χαλάει B.
; ---------------------------------------------------------------------------
jb_take:
        ld      c,a                     ; C = j
        ld      l,a
        add     a,a
        add     a,a
        add     a,l                     ; 5j: ως 155, χωράει σε byte
        ld      l,a
        ld      h,0
        ld      de,G_job_tbl
        add     hl,de
        inc     hl
        ld      b,(hl)                  ; B = κόμβος της εργασίας
        inc     hl
        ld      a,(jb_i)
        ld      (hl),a                  ; job.agent = i
        ld      e,a
        set     7,e
        ld      d,AG_PG + 3
        ld      a,c
        ld      (de),a                  ; agent.task = j
        res     7,e
        dec     d                       ; AG_PG + 2
        ld      a,b
        ld      (de),a                  ; agent.dest = κόμβος
        ret

job_roles:  db #22,#05,#41,#81,#02,#08,#10
jb_ag:      db 0
jb_d:       db 0
jb_kind2:   db 0
jb_room:    db 0                    ; το δωμάτιο του jb_need, για την προτεραιότητα
jb_i:       db 0
jb_done:    db 0
jb_rolebit: db 0
jb_row:     dw 0                    ; η γραμμή του DIST για τον (jb_i)
jb_bj:      db 0                    ; jb_bj, jb_bp, jb_bd διπλανά
jb_bp:      db 0
jb_bd:      db 0
        assert  jb_bp == jb_bj + 1 && jb_bd == jb_bp + 1
        assert  JOB_REC * (MAX_JOB - 1) <= 255  ; jb_take: το 5j χωράει σε byte
