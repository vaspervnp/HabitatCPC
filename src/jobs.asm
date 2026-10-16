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
        inc     a                       ; NO_JOB: 3 T φθηνότερο από το cp (βήμα 88)
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
        ; ΚΑΙ ΠΙΣΩ ΣΤΟΝ ΚΟΜΒΟ ΤΗΣ (βήμα 88): μια Supply που αφέθηκε στο πρώτο
        ; σκέλος δείχνει ακόμη την πηγή. Το J_SITE είναι ο κόμβος της, και σε
        ; κάθε άλλη εργασία ίσος με το J_NODE: η αντιγραφή είναι πάντα σωστή.
        ; ΟΧΙ ΣΤΗ HAUL (βήμα 95, src/haul.asm): εκεί το J_SITE είναι το ορυχείο,
        ; και μια Haul που αφέθηκε φορτωμένη δείχνει τον προορισμό — εκεί πάει
        ; ο επόμενος και παραδίδει το φορτίο που έμεινε στη μέση. ΟΥΤΕ ΣΤΗ
        ; J_TRADE (βήμα 98, src/carry.asm): το J_SITE της είναι το φορτίο.
        dec     hl
        dec     hl
        ld      a,(hl)                  ; J_KIND
        cp      J_HAUL
        jr      z,jr_pop
        cp      J_TRADE
        jr      z,jr_pop
        inc     hl
        inc     hl
        inc     hl
        inc     hl
        ld      a,(hl)                  ; J_SITE
        dec     hl
        dec     hl
        dec     hl
        ld      (hl),a                  ; J_NODE
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
        inc     a                       ; NO_JOB
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
        ; Ο ΧΕΙΡΙΣΤΗΣ ΠΕΡΝΑ ΑΠΟ ΔΥΟ ΕΡΩΤΗΣΕΙΣ, όχι από τρεις (βήμα 88): η
        ; επισκευή και η τροφοδοσία είναι από το J_REPAIR και πάνω.
        ld      a,(hl)
        or      a                       ; J_BUILD
        jr      z,ja_build              ; ο πράκτορας δουλεύει και μένει
        cp      J_HAUL
        jr      z,ja_haul               ; βήμα 95: φορτώνει ή παραδίδει
        cp      J_REPAIR
        jr      nc,ja_more              ; επισκευή ή τροφοδοσία
ja_oper:
        ; --- ο θόλος αποκτά χειριστή, ή το ορυχείο κάποιον που σκάβει (βήμα
        ; 94: ως τότε μια δομή δεν μετρούσε κανέναν, και καμία δεν είχε ανάγκη) ---
        ld      a,c
        call    op_ptr
        inc     (hl)
        res     7,(hl)                  ; το ορυχείο: η Drill του έφυγε (src/drill.asm)
        res     ST_DLOW,(hl)            ; και ό,τι έλεγε για αυτήν (βήμα 126)
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

; --- μεταφορά (βήμα 95): φορτώνει στο ορυχείο, παραδίδει στον προορισμό
; (src/haul.asm). C = ο κόμβος. ---
ja_haul:
        call    hl_arrive
        jr      z,ja_next               ; φόρτωσε: η εργασία μένει δική του
        jr      ja_done

ja_more:
        jr      z,ja_repair             ; φτάνει, αλλάζει το εξάρτημα, φεύγει
        cp      J_SUPPLY
        jr      c,ja_oper               ; Heal, Defend: όπως ως το 87
; --- τροφοδοσία (βήμα 88): φορτώνει στην πηγή, ξεφορτώνει στο εργοτάξιο
; (src/supply.asm). E = ο πράκτορας. Και τα αγαθά του εμπόρου (βήμα 98): το
; sp_arrive στέλνει τη J_TRADE στο tr_arrive (src/carry.asm), με την ίδια
; σύμβαση. ---
ja_supply:
        call    sp_arrive
        jr      z,ja_next               ; φόρτωσε: η εργασία μένει δική του
        jr      c,ja_fail               ; παρέδωσε, χρωστιέται κι άλλο: ξανανοίγει
        jr      ja_done                 ; το τελευταίο φορτίο του υλικού

; --- επισκευή: C = ο θόλος ---
; Το jb_broken αφήνει τον IX πάνω στην υποδοχή που βρήκε, και η υγεία είναι
; οκτώ bytes πιο κάτω· ως το βήμα 46 η υποδοχή περνούσε από μεταβλητή και η
; διεύθυνση ξαναφτιαχνόταν από την αρχή.
ja_repair:
        ld      a,c
        ld      (jb_d),a
        call    jb_broken               ; και C = η υποδοχή
        inc     a
        jr      z,ja_fail
        ld      b,c                     ; το ec_have και το ec_sub κρατούν το B
        ld      a,S_SPARE               ; χρειάζεται ένα ανταλλακτικό
        ld      c,1
        call    ec_have
        jr      c,ja_fail
        ld      a,c
        call    ec_sub                  ; src/econ.asm
        ld      (ix+D_HEALTH-D_MACH),MACH_HP ; ξαναδουλεύει
        ld      c,b                     ; και το σήμα φεύγει (βήμα 100)
        ld      a,(jb_d)
        ld      b,a
        call    jb_mpush
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
        ld      de,D_STATE
        add     hl,de
        bit     1,(hl)                  ; DS_ACTIVE: χτισμένο, οι μηχανές του
        jr      nz,jab_inst
        inc     hl                      ; D_INTEG
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
        ; Ο ΓΡΑΦΟΣ ΑΛΛΑΖΕΙ (βήμα 87): ένας θόλος σφραγίζεται και ο χτίστης
        ; βγαίνει, και οι διάδρομοί του γίνονται ακμές (src/door.asm).
        push    bc
        ld      a,c
        call    lk_done
        pop     bc
        ; ΤΟ ΚΤΙΡΙΟ ΠΡΕΠΕΙ ΝΑ ΦΑΝΕΙ — και η σκηνή μαθαίνει ΠΟΙΟ. Ως το βήμα 34
        ; ήταν μια σημαία, και ο βρόχος ξαναζωγράφιζε ολόκληρο το κάδρο γιατί
        ; δεν ήξερε τι άλλαξε: 0,36-0,92 s παγωμένη οθόνη ανά κτίριο (§6.9).
        push    bc
        ld      a,c
        call    st_built                ; DK_BUILT, και το σήμα μιας δομής σβήνει (βήμα 109)
        pop     bc
        ; ΚΑΙ ΤΟ ΙΣΟΖΥΓΙΟ ΞΑΝΑΜΕΤΡΑΕΙ ΑΜΕΣΩΣ. Ο κύκλος ροής είναι 64
        ; περιστροφές (~20 δευτερόλεπτα): χωρίς αυτό, το πρώτο ηλιακό πάνελ
        ; του παίκτη έβγαζε ρεύμα και το HUD συνέχιζε να γράφει NO POWER ως
        ; να έρθει η σειρά του κύκλου. Οτι αλλάζει την αποικία, ξαναμετριέται.
        ld      a,1
        ld      (ec_fdiv),a
        ; ΚΑΙ ΟΙ ΜΗΧΑΝΕΣ ΤΟΥ (βήμα 99): όσες πήραν τα υλικά τους όσο ήταν
        ; εργοτάξιο τις στήνει ο ίδιος χτίστης, από αυτή κιόλας την επίσκεψη.
; --- η Build σε θόλο σε λειτουργία: στήνει τις μηχανές του (βήμα 99,
; src/install.asm). Η πρώτη υποδοχή που πήρε τα υλικά της και δεν δουλεύει
; ακόμη (4 + 32k) ανεβαίνει BUILD_STEP, και πάνω από το 127 γίνεται MACH_HP.
; Η εργασία μένει όσο βρίσκει μία. ---
jab_inst:
        ld      a,c
        cp      MAX_DOME
        jr      nc,jab_end              ; δομή: δεν έχει μηχανές
        call    mc_rec                  ; IX -> υποδοχή 0, B = υποδοχές
        ld      e,0                     ; η υποδοχή, για τη λίστα (βήμα 100)
jabi_lp:
        ld      a,(ix+D_HEALTH-D_MACH)
        and     #80 | 3                 ; δουλεύει, ή χρωστά υλικά
        jr      nz,jabi_n
        or      (ix+D_HEALTH-D_MACH)
        jr      nz,jabi_go              ; 0: χαλασμένη ή άδεια — θέλει Repair
jabi_n:
        inc     ix
        inc     e
        djnz    jabi_lp
jab_end:
        ld      hl,EC_NBUILD            ; μία Build λιγότερη (βήμα 88)
        dec     (hl)
        jp      ja_done
jabi_go:
        add     a,BUILD_STEP
        ld      (ix+D_HEALTH-D_MACH),a
        ; Ο ΧΤΙΣΤΗΣ ΜΕΝΕΙ ΣΤΟΝ ΘΟΛΟ. Αν το κτίριο μόλις τελείωσε, το lk_done τον
        ; έβγαλε έξω, στο airlock ή στο σκάφος, με την εργασία ακόμη δική του:
        ; ο προορισμός του ξαναγίνεται ο θόλος, αλλιώς περίμενε εκεί για πάντα.
        ld      hl,(jb_ag)
        ld      h,AG_PG + 2             ; dest
        ld      (hl),c
        jp      p,ja_next               ; ακόμη στήνεται
        ld      (ix+D_HEALTH-D_MACH),MACH_HP ; στήθηκε: δουλεύει,
        ld      b,c                     ; και το σήμα φεύγει (βήμα 100)
        ld      c,e
        call    jb_mpush
        jp      ja_next

; jb_mpush — B = θόλος, C = υποδοχή: η υποδοχή ξαναζωγραφίζεται (βήμα 100), με
; το σήμα της ή χωρίς. Από το ja_repair, το jab_inst και το ec_break_d.
jb_mpush:
        ld      a,DK_MACH
        jp      wh_push

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
        ; Ο ΔΕΙΚΤΗΣ ΤΡΕΧΕΙ 0-255 (βήμα 140): ο θόλος είναι τα έξι χαμηλά του bits,
        ; και το bit 6 η ισοτιμία του σαρώματος των 64 — το jp_one τη διαβάζει.
        ; Δύο bytes λιγότερα από το and πριν από την αποθήκευση.
        ld      hl,EC_JDOME
        ld      a,(hl)
        inc     (hl)
        and     MAX_DOME - 1
        ld      (jb_d),a
        call    jp_one
        pop     bc
        djnz    jp_lp
        ret

        ; ΜΙΑ ΧΑΛΑΣΜΕΝΗ ΣΤΗ ΓΡΑΜΜΗ ΕΙΔΟΠΟΙΗΣΕΩΝ (βήμα 119, src/alert6.asm): αν
        ; το HUD δεν κρατά καμία, κρατά αυτή — τη δεύτερη, όταν επισκευάστηκε η
        ; πρώτη, ή μετά από φόρτωση. Πριν από τη δημοσίευση, που μπορεί να μη
        ; γίνει (διπλότυπο, γεμάτος πίνακας). C = η υποδοχή (jb_broken).
jp_rep:
        ld      hl,al_brk + 1
        ld      a,(hl)
        inc     a
        jr      nz,jp_have              ; κρατά ήδη μία
        ld      a,(jb_d)
        ld      (hl),a                  ; ο θόλος
        dec     hl
        ld      (hl),c                  ; η υποδοχή
        jr      jp_have

jp_one:
        ; Μία εργασία ανά θόλο ανά επίσκεψη: μια σταματημένη μηχανή δεν θέλει
        ; χειριστή, θέλει μηχανικό. ΟΙ ΑΛΛΕΣ ΟΜΩΣ ΘΕΛΟΥΝ (βήμα 140, η επιλογή του
        ; χρήστη: σταματά μόνο η χαλασμένη). Ως το 139 ένας θόλος με μία
        ; χαλασμένη ζητούσε μόνο τη Repair, και ένας μεσαίος με τέσσερις MEALS
        ; έμενε χωρίς μάγειρα ως να έρθει ανταλλακτικό (tools/play.py, 1048 3:
        ; τριάντα νεκροί δίπλα σε 184 άμυλο, 157 λαχανικά, 99 κρέας). Τώρα
        ; ΕΝΑΛΛΑΞ: στα ζυγά σαρώματα η Repair, στα μονά η Operate για όσες
        ; δουλεύουν. Οχι και τις δύο στην ίδια επίσκεψη: δεύτερη σάρωση των 32,
        ; 3.414 µs αντί για 1.808 στο χειρότερο (tests/test_brokenop.py).
        ld      a,J_REPAIR
        ld      (jb_kind2),a
        call    jb_broken
        inc     a
        jr      z,jp_oper               ; καμία χαλασμένη
        ld      a,(EC_JDOME)            ; ήδη +1: το bit 6 είναι το σάρωμα
        and     MAX_DOME
        jr      z,jp_rep                ; ζυγό: η Repair, C = η υποδοχή
jp_oper:
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
        ld      (hl),c                  ; J_SITE = ο θόλος (βήμα 88)
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
jbs_any:
        push    hl
        pop     ix
        ld      a,(ix+D_SIZE-D_STATE)
        add     a,G_machine_count & 255
        ld      e,a
        ld      d,G_machine_count >> 8
        ld      a,(de)
        ld      b,a
        ld      de,D_MACH - D_STATE
        add     ix,de
        ld      a,(ix+D_ROOM-D_MACH)
        cp      a                       ; Z: το add a,n πιο πάνω το είχε χαλάσει
        ret

; mc_rec — A = θόλος, χτισμένος ή όχι: IX -> υποδοχή 0, B = υποδοχές, HL ->
; D_STATE. Χαλάει DE. Οι μηχανές που κουβαλιούνται (βήμα 99, src/install.asm)
; έχουν υποδοχές και σε εργοτάξιο.
mc_rec:
        call    jb_dome_ptr
        ld      de,D_STATE
        add     hl,de
        jr      jbs_any

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
        bit     7,(ix+D_HEALTH-D_MACH)
        jr      z,jn_next               ; χαλασμένη, ή δεν στήθηκε ακόμη (βήμα 99)
        ld      a,e
        add     a,G_mach_op & 255
        ld      e,a
        ld      d,G_mach_op >> 8
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

; jb_dome_ptr — A = θόλος -> HL = εγγραφή. Κρατά το A, χαλάει το DE.
; ΣΤΟ ΠΑΙΧΝΙΔΙ ΕΙΝΑΙ ΤΟ ob_domeadr (src/object.asm, που έρχεται πιο πριν): οι
; ίδιες εντολές, 15 bytes (βήμα 103). Δικό του αντίγραφο μόνο όπου εκείνο δεν
; υπάρχει, στο tests/simtest.asm.
        ifdef   ob_domeadr
jb_dome_ptr equ ob_domeadr
        else
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
        endif

; op_ptr — A = κόμβος -> HL -> οι χειριστές του: το D_OPS ενός θόλου, ή το
; ST_OPS μιας δομής — όσοι σκάβουν σε ένα ορυχείο (βήμα 94, src/drill.asm).
; Η άφιξη (ja_oper), η αναχώρηση (src/entity.asm) και ο θάνατος (nd_die)
; περνούν από εδώ: ως το 93 ήταν τρία αντίγραφα του «αν είναι θόλος». Κρατά BC.
op_ptr:
        cp      MAX_DOME
        jr      nc,opp_st
        call    jb_dome_ptr
        ld      de,D_OPS
        add     hl,de
        ret
opp_st:
        add     a,a
        add     a,a
        add     a,a                     ; (κόμβος - 64) * 8: το 512 φεύγει από το byte
        add     a,ST_OPS
        ld      l,a
        ld      h,G_struct_tbl >> 8
        ret
        assert  (G_struct_tbl & 255) == 0 && STRUCT_REC == 8 && MAX_DOME == 64

; Η HAUL ΣΤΟ 5, πάνω από τη Drill (4), από το βήμα 95 (ως τότε 2, και δεν τη
; δημοσίευε τίποτα): οι εργάτες κάνουν και τα δύο, και με λίγους εργάτες μια
; Haul κάτω από τη Drill δεν την έπαιρνε κανείς — ο σωρός γέμιζε (HAUL_CAP)
; και το ορυχείο σταματούσε για πάντα, με όλους να σκάβουν.
; Η DRILL ΕΙΝΑΙ ΜΕΤΑΒΛΗΤΗ από το βήμα 126: το dr_post (src/drill.asm) γράφει
; εδώ DRILL_PRIO ή DRILL_LOW πριν από κάθε δημοσίευσή της.
job_prio:   db 5,3,5,DRILL_PRIO,6,8,9

; Προτεραιότητα OPERATE ανά δωμάτιο (§6.7). Πρώτα ό,τι κρατά ανθρώπους στη
; ζωή, μετά ό,τι το ταΐζει, μετά η βιομηχανία:
;   empty control quarters canteen oxygen greenhouse storage airlock
;   factory lab medbay lounge
room_prio:  db 3,3,3,5,5,4,3,3,3,4,4,3

; ---------------------------------------------------------------------------
; 4. ανάθεση: ως JOB_ASSIGN, κοιτάζοντας ως JOB_LOOK πράκτορες
; ---------------------------------------------------------------------------
jb_assign:
        ; Πρώτα: ποιοι ρόλοι έχουν αδιάθετη εργασία (jb_open, src/drill.asm);
        ; Στη μόνιμη κατάσταση κανείς, και χωρίς αυτόν τον έλεγχο κάθε αδρανής
        ; πράκτορας σάρωνε και τις 32 εγγραφές για να μη βρει τίποτα — 36 ms τη
        ; θέση. Ως το βήμα 93 ο έλεγχος ήταν «καμία», και μία εργασία που δεν
        ; την έπαιρνε κανείς από τους αδρανείς τα πλήρωνε πάλι ολόκληρα: με
        ; τη γεώτρηση, που αφήνει μια Drill ανοιχτή όσο το ορυχείο έχει θέση,
        ; θα τα πλήρωνε σε κάθε περιστροφή.
        call    jb_open
        jr      z,jas_done              ; καμία: ο δείκτης προχωράει, τέλος
        xor     a
        ld      (jb_done),a
        ld      a,(EC_JAGENT)
        ld      c,a                     ; C = ο πράκτορας
        ld      b,JOB_LOOK
        ; Ο ΠΡΑΚΤΟΡΑΣ ΣΤΟΝ C ΚΑΙ Ο ΓΡΗΓΟΡΟΣ ΔΡΟΜΟΣ ΧΩΡΙΣ push (βήμα 94): οι
        ; περισσότεροι από τους 32 είναι νεκροί ή δουλεύουν, και ο καθένας
        ; κόστιζε ~155 T με το jb_i και το jb_done στη μνήμη — ~1,2 ms τη θέση
        ; όποτε υπάρχει αδιάθετη εργασία. Τώρα ~70 T. Αυτό ξεπληρώνει τη
        ; σάρωση του jb_open, που δεν σταματά στην πρώτη αδιάθετη όπως το
        ; «καμία;» που αντικατέστησε. Το jb_done ελέγχεται μετά από ανάθεση.
jas_lp:
        ld      l,c
        ld      h,AG_PG
        ld      a,(hl)                  ; flags
        and     F_ALIVE + F_WORKING
        cp      F_ALIVE
        jr      nz,jas_next             ; νεκρός, ή δουλεύει ήδη
        set     7,l
        ld      h,AG_PG + 3             ; task
        ld      a,(hl)
        inc     a                       ; NO_TASK
        jr      nz,jas_next
        push    bc
        ld      a,c
        ld      (jb_i),a                ; για το jb_best και το jb_take
        ld      h,AG_PG                 ; role, στο πάνω μισό
        ld      a,(hl)
        and     7
        ld      b,a
        inc     b
        ld      a,#80
jas_rb:
        rlca
        djnz    jas_rb                  ; A = 1 << ρόλος
        ld      (jb_rolebit),a
        ld      e,a
        ld      a,(jb_om)
        and     e
        jr      z,jas_nx                ; καμία ανοιχτή για τον ρόλο του
        res     7,l
        inc     h                       ; AG_PG + 1: node
        ld      a,(hl)
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
        jr      z,jas_nx
        call    jb_take
        ld      hl,jb_done
        inc     (hl)
        ld      a,(hl)
        cp      JOB_ASSIGN
        jr      nc,jas_stop
        ; Η ΜΑΣΚΑ ΞΑΝΑ: μπορεί να ήταν η τελευταία του ρόλου της, και τότε οι
        ; επόμενοι του ίδιου ρόλου θα έψαχναν τις 32 για να μη βρουν τίποτα.
        ; Ενα jb_open (~500 us) ανά ανάθεση, ως JOB_ASSIGN, φθηνότερο από ένα
        ; jb_best (~1 ms) που αποτυγχάνει: στη θέση 13 του σεναρίου ταυτότητας
        ; του tests/test_sim.py, 314 ms στα 640 ticks έτσι και 361 με μια μάσκα
        ; που διορθώνεται στην αποτυχία (363 στο 93, 982 με τη γεώτρηση χωρίς
        ; μάσκα). Με μάσκα 0 η ανάθεση σταματά.
        call    jb_open
        jr      z,jas_stop
jas_nx:
        pop     bc
jas_next:
        inc     c
        res     7,c
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
        ld      a,l                     ; 255 (assert)
        assert  NO_JOB == 255
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
; jb_take — ο (jb_i) παίρνει την εργασία A. Χαλάει B, C, DE, HL.
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
        ; Η ερώτηση εδώ, η απάντηση στο τέλος (βήμα 88): το CY
        ; επιζεί, γιατί inc hl, ld, set/res και dec d δεν το αγγίζουν.
        ld      a,(hl)
        cp      J_SUPPLY                ; CY: όχι Supply
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
        ret     c
        jp      sp_take                 ; μια Supply πάει πρώτα στην πηγή (βήμα 88)

; Ποιοι ρόλοι παίρνουν κάθε είδος, ένα bit ανά ρόλο (§6.1): εργάτης,
; μηχανικός, βιολόγος, γιατρός, φρουρός, ρομπότ κατασκευής, μεταφοράς,
; γεώτρησης. Η Supply (βήμα 88) είναι ΟΛΟΙ οι άποικοι και το ρομπότ
; μεταφοράς, για μέταλλο και για βιοπλαστικό· το ίδιο τα αγαθά του εμπόρου
; (βήμα 98).
job_roles:  db #22,#05,#41,#81,#02,#08,#10,#5F,#5F,#5F
        assert  J_TRADE == J_SUPPLY + 2 && $ - job_roles == J_TRADE + 1
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
