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
        cp      255
        jr      z,jr_pop
        ld      e,a
        ld      d,AG_PG                 ; flags
        ld      a,(de)
        and     F_ALIVE
        jr      z,jr_free
        set     7,e                     ; το task είναι στο ΠΑΝΩ μισό
        ld      d,AG_PG + 3
        ld      a,(de)
        ld      e,a
        ld      a,c
        cp      e
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
; ---------------------------------------------------------------------------
jb_arrive:
        ld      hl,G_job_tbl
        ld      b,MAX_JOB
ja_lp:
        push    bc
        push    hl
        ld      a,(hl)
        cp      NO_JOB
        jp      z,ja_next
        inc     hl
        ld      c,(hl)                  ; C = κόμβος
        inc     hl
        ld      a,(hl)                  ; ο πράκτορας
        cp      255
        jp      z,ja_next
        ld      e,a
        ld      (jb_ag),a
        ld      d,AG_PG + 1             ; node
        ld      a,(de)
        cp      c
        jp      nz,ja_next              ; δεν έφτασε ακόμη
        ld      d,AG_PG + 2
        ld      a,e
        add     a,128                   ; edge στο πάνω μισό
        ld      e,a
        ld      a,(de)
        cp      255
        jp      nz,ja_next              ; ακόμη στον σωλήνα

        ; --- κατασκευή; τότε ο πράκτορας δουλεύει και μένει ---
        pop     hl
        push    hl
        ld      a,(hl)
        cp      J_BUILD
        jp      z,ja_build
        ; --- επισκευή; τότε ο μηχανικός φτάνει, αλλάζει το εξάρτημα, φεύγει ---
        cp      J_REPAIR
        jp      nz,ja_operate
        ld      a,c
        ld      (jb_d),a
        call    jb_broken
        cp      255
        jr      z,ja_fail
        ld      (jb_slot),a
        ld      a,S_SPARE               ; χρειάζεται ένα ανταλλακτικό
        ld      c,1
        call    ec_have
        jr      c,ja_fail
        ld      a,(de)
        sub     1
        ld      (de),a
        inc     de
        ld      a,(de)
        sbc     a,0
        ld      (de),a
        ld      a,(jb_d)
        call    jb_dome_ptr
        ld      de,D_HEALTH
        add     hl,de
        ld      a,(jb_slot)
        ld      e,a
        ld      d,0
        add     hl,de
        ld      (hl),200                ; ξαναδουλεύει
        call    ja_cleartask
        pop     hl
        push    hl
        ld      (hl),NO_JOB
        jp      ja_next
ja_fail:
        ; τζάμπα δρόμος: η εργασία μένει ανοιχτή για τον επόμενο
        call    ja_cleartask
        pop     hl
        push    hl
        inc     hl
        inc     hl
        ld      (hl),255
        jp      ja_next
; ---------------------------------------------------------------------------
; ja_build — ο πράκτορας δουλεύει στο εργοτάξιο (§6.9 βήμα 3). C = ο κόμβος.
;
; Η ΠΡΟΟΔΟΣ ΕΙΝΑΙ Η ΑΚΕΡΑΙΟΤΗΤΑ. Το §6.9 λέει «η πρόοδος είναι ένα byte» και η
; εγγραφή έχει ήδη ένα: το bd_commit γράφει ακεραιότητα 0, και η κατασκευή την
; ανεβάζει ως το 255 — οπότε ένα μισοχτισμένο κτίριο είναι το ίδιο πράγμα με
; ένα μισοκατεστραμμένο, που είναι σωστό και γλιτώνει ένα byte ανά κόμβο.
;
; Το D_STATE και το D_INTEG είναι στα ίδια offsets με το ST_STATE και το
; ST_INTEG, οπότε θόλος και δομή περνούν από τον ίδιο κώδικα.
BUILD_STEP  equ 32                  ; οκτώ επισκέψεις = ~2,6 δευτερόλεπτα

ja_build:
        ld      a,c
        cp      MAX_DOME
        jr      c,jab_dome
        sub     MAX_DOME
        ld      l,a
        ld      h,0
        add     hl,hl
        add     hl,hl
        add     hl,hl                   ; *STRUCT_REC
        ld      de,G_struct_tbl
        add     hl,de
        jr      jab_rec
jab_dome:
        call    jb_dome_ptr
jab_rec:
        push    hl
        ld      de,D_INTEG
        add     hl,de
        ld      a,(hl)
        add     a,BUILD_STEP
        jr      nc,jab_st
        ld      a,255
jab_st:
        ld      (hl),a
        pop     hl
        cp      255
        jp      nz,ja_next              ; ακόμη χτίζεται· η εργασία μένει
        ld      de,D_STATE
        add     hl,de
        ld      (hl),DS_ACTIVE
        ld      a,1
        ld      (wh_built),a            ; το κτίριο πρέπει να φανεί
        call    ja_cleartask
        pop     hl
        push    hl
        ld      (hl),NO_JOB
        jp      ja_next

ja_cleartask:
        ld      a,(jb_ag)
        ld      e,a
        set     7,e
        ld      d,AG_PG + 3
        ld      a,NO_TASK
        ld      (de),a
        ret

ja_operate:
        ; --- ο θόλος αποκτά χειριστή ---
        ld      a,c
        cp      MAX_DOME
        jr      nc,ja_flags             ; δομή, όχι θόλος: δεν έχει ops
        ld      h,0
        ld      l,a
        add     hl,hl
        add     hl,hl
        add     hl,hl
        ld      d,h
        ld      e,l
        add     hl,hl
        add     hl,de                   ; *24
        ld      de,G_dome_tbl + D_OPS
        add     hl,de
        inc     (hl)
ja_flags:
        ld      a,(jb_ag)
        ld      e,a
        ld      d,AG_PG
        ld      a,(de)
        or      F_WORKING
        ld      (de),a
        ld      a,(jb_ag)
        ld      e,a
        set     7,e                     ; το task, όχι το progress
        ld      d,AG_PG + 3
        ld      a,NO_TASK
        ld      (de),a
        pop     hl
        push    hl
        ld      (hl),NO_JOB             ; η εργασία τελείωσε
ja_next:
        pop     hl
        ld      de,JOB_REC
        add     hl,de
        pop     bc
        dec     b
        jp      nz,ja_lp
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
        cp      MAX_DOME
        jr      c,jp_st
        xor     a
jp_st:
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
        cp      255
        jr      nz,jp_have
        ld      a,J_OPERATE
        ld      (jb_kind2),a
        call    jb_need
        ld      (jb_want),a
        or      a
        ret     z
        ld      a,(jb_d)
        call    jb_dome_ptr
        ld      de,D_OPS
        add     hl,de
        ld      a,(hl)
        ld      hl,jb_want
        cp      (hl)
        ret     nc                      ; έχει ήδη αρκετούς
jp_have:

        ; ΕΝΑ πέρασμα: βρίσκει και το διπλότυπο και την πρώτη ελεύθερη θέση.
        ; Δύο ξεχωριστές σαρώσεις των 32 ήταν η μισή δουλειά της δημοσίευσης.
        ld      hl,G_job_tbl
        ld      b,MAX_JOB
        ld      a,(jb_d)
        ld      c,a
        ld      de,0
        ld      (jp_slot),de            ; 0 = δεν βρέθηκε ελεύθερη
jp_dup:
        ld      a,(hl)
        cp      NO_JOB
        jr      nz,jp_used
        push    hl
        ld      hl,(jp_slot)
        ld      a,h
        or      l
        pop     hl
        jr      nz,jp_dup_n             ; έχουμε ήδη μία ελεύθερη
        ld      (jp_slot),hl
        jr      jp_dup_n
jp_used:
        push    hl
        ld      hl,jb_kind2
        cp      (hl)
        pop     hl
        jr      nz,jp_dup_n
        inc     hl
        ld      a,(hl)
        dec     hl
        cp      c
        ret     z                       ; υπάρχει ήδη — δεν ξαναδημοσιεύουμε
jp_dup_n:
        ld      de,JOB_REC
        add     hl,de
        djnz    jp_dup

        ld      hl,(jp_slot)
        ld      a,h
        or      l
        ret     z                       ; ο πίνακας γέμισε
jp_write:
        ld      a,(jb_kind2)
        ld      (hl),a
        inc     hl
        ld      a,(jb_d)
        ld      (hl),a
        inc     hl
        ld      (hl),255                ; αδιάθετη
        inc     hl
        ld      a,(jb_kind2)
        push    hl
        ld      hl,job_prio
        add     a,l
        ld      l,a
        ld      a,0
        adc     a,h
        ld      h,a
        ld      a,(hl)
        pop     hl
        ld      (hl),a
        inc     hl
        ld      (hl),0
        ret

; jb_broken — (jb_d) = θόλος. A = η πρώτη σταματημένη υποδοχή, ή 255.
jb_broken:
        ld      a,(jb_d)
        call    jb_dome_ptr
        push    hl
        ld      de,D_STATE
        add     hl,de
        ld      a,(hl)
        pop     hl
        cp      DS_ACTIVE
        jr      nz,jbr_no
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
        ld      b,(hl)
        pop     hl
        ld      de,D_MACH
        add     hl,de
        ld      c,0
jbr_lp:
        ld      a,(hl)
        cp      NO_MACH
        jr      z,jbr_n
        push    hl
        ld      de,D_HEALTH - D_MACH
        add     hl,de
        ld      a,(hl)
        pop     hl
        or      a
        jr      nz,jbr_n
        ld      a,c                     ; βρέθηκε
        ret
jbr_n:
        inc     hl
        inc     c
        djnz    jbr_lp
jbr_no:
        ld      a,255
        ret

; jb_need — A/(jb_d) = θόλος -> A = πόσες μηχανές θέλουν χειριστή
jb_need:
        ld      a,(jb_d)
        call    jb_dome_ptr
        push    hl
        ld      de,D_STATE
        add     hl,de
        ld      a,(hl)
        pop     hl
        cp      DS_ACTIVE
        jr      z,jn_go
        xor     a
        ret
jn_go:
        push    hl                      ; θερμοκήπιο; τότε κάθε φυτό μετράει
        ld      de,D_ROOM
        add     hl,de
        ld      a,(hl)
        pop     hl
        cp      R_GREENHS
        ld      a,0
        jr      nz,jn_ng
        inc     a
jn_ng:
        ld      (jb_green),a
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
        ld      b,(hl)                  ; πλήθος υποδοχών
        pop     hl
        ld      de,D_MACH
        add     hl,de
        ld      c,0                     ; μετρητής
jn_lp:
        ld      a,(hl)
        cp      NO_MACH
        jr      z,jn_next
        push    hl
        ld      de,D_HEALTH - D_MACH
        add     hl,de
        ld      e,(hl)
        pop     hl
        inc     e
        dec     e
        jr      z,jn_next               ; χαλασμένη
        push    hl
        ld      hl,jb_green
        ld      e,(hl)
        ld      hl,G_mach_op
        add     a,l
        ld      l,a
        ld      a,0
        adc     a,h
        ld      h,a
        ld      a,(hl)
        or      e                       ; στο θερμοκήπιο, όλα μετράνε
        pop     hl
        or      a
        jr      z,jn_next
        inc     c
jn_next:
        inc     hl
        djnz    jn_lp
        ld      a,c
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

jb_ag:      db 0
jb_d:       db 0
jb_want:    db 0
jb_kind2:   db 0
jb_green:   db 0
jb_slot:    db 0
job_prio:   db 5,3,2,4,6,8,9

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
        push    hl
        inc     hl
        inc     hl
        ld      a,(hl)
        pop     hl
        cp      255
        jr      z,jba_go                ; βρέθηκε αδιάθετη
jba_an:
        ld      de,JOB_REC
        add     hl,de
        djnz    jba_any
        ld      a,(EC_JAGENT)           ; καμία: ο δείκτης προχωράει, τέλος
        add     a,JOB_LOOK
        and     127
        ld      (EC_JAGENT),a
        ret
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
        ld      a,(de)
        ld      c,a
        and     F_ALIVE
        jr      z,jas_next
        ld      a,c
        and     F_WORKING
        jr      nz,jas_next

        ld      a,(jb_i)
        ld      e,a
        set     7,e
        ld      d,AG_PG + 3             ; task
        ld      a,(de)
        cp      NO_TASK
        jr      nz,jas_next

        ; bit του ρόλου
        ld      a,(jb_i)
        ld      e,a
        set     7,e
        ld      d,AG_PG                 ; role
        ld      a,(de)
        and     7
        ld      b,a
        ld      a,1
        inc     b
jas_rb:
        dec     b
        jr      z,jas_rbd
        add     a,a
        jr      jas_rb
jas_rbd:
        ld      (jb_rolebit),a

        ld      a,(jb_i)
        ld      e,a
        ld      d,AG_PG + 1             ; node
        ld      a,(de)
        ld      (jb_node),a

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
; jb_best — η καλύτερη ανοιχτή εργασία για τον (jb_i). A = δείκτης ή 255.
;
; Η τράπεζα 1 μπαίνει ΜΙΑ φορά για όλη τη σάρωση των 32 εργασιών, όχι μία ανά
; ανάγνωση: ο πίνακας εργασιών είναι στην τράπεζα 2 και φαίνεται πάντα.
; ---------------------------------------------------------------------------
jb_best:
        ld      a,NO_JOB
        ld      (jb_bj),a
        xor     a
        ld      (jb_bp),a
        ld      a,255
        ld      (jb_bd),a
        xor     a
        ld      (jb_j),a

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
        cp      255
        jr      nz,jbb_next             ; ήδη ανατεθειμένη
        inc     hl
        ld      d,(hl)                  ; D = προτεραιότητα

        ld      hl,job_roles
        ld      a,c
        add     a,l
        ld      l,a
        ld      a,0
        adc     a,h
        ld      h,a
        ld      a,(hl)
        ld      hl,jb_rolebit
        and     (hl)
        jr      z,jbb_next              ; λάθος ρόλος

        ; DIST[κόμβος πράκτορα][κόμβος εργασίας]
        ld      a,(jb_node)
        ld      h,a
        ld      l,0
        srl     h
        rr      l
        ld      a,l
        add     a,e
        ld      l,a
        set     6,h
        ld      c,(hl)                  ; C = απόσταση

        ld      hl,jb_bp
        ld      a,d
        cp      (hl)
        jr      c,jbb_next
        jr      nz,jbb_better
        ld      a,c
        ld      hl,jb_bd
        cp      (hl)
        jr      nc,jbb_next
jbb_better:
        ld      a,d
        ld      (jb_bp),a
        ld      a,c
        ld      (jb_bd),a
        ld      a,(jb_j)
        ld      (jb_bj),a
jbb_next:
        pop     hl
        ld      de,JOB_REC
        add     hl,de
        ld      a,(jb_j)
        inc     a
        ld      (jb_j),a
        pop     bc
        djnz    jbb_lp

        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        ld      a,(jb_bj)
        ret

; ---------------------------------------------------------------------------
; jb_take — ο (jb_i) παίρνει την εργασία A.
; ---------------------------------------------------------------------------
jb_take:
        push    af
        ld      h,0
        ld      l,a
        ld      d,h
        ld      e,l
        add     hl,hl
        add     hl,hl                   ; *4
        add     hl,de                   ; *5
        ld      de,G_job_tbl
        add     hl,de
        inc     hl
        ld      c,(hl)                  ; κόμβος της εργασίας
        inc     hl
        ld      a,(jb_i)
        ld      (hl),a                  ; job.agent = i

        ld      e,a
        set     7,e
        ld      d,AG_PG + 3
        pop     af
        ld      (de),a                  ; agent.task = j

        ld      a,(jb_i)
        ld      e,a
        ld      d,AG_PG + 2
        ld      a,c
        ld      (de),a                  ; agent.dest = κόμβος
        ret

job_roles:  db #22,#05,#41,#81,#02,#08,#10
jp_slot:    dw 0
jb_i:       db 0
jb_j:       db 0
jb_done:    db 0
jb_node:    db 0
jb_rolebit: db 0
jb_bj:      db 0
jb_bp:      db 0
jb_bd:      db 0
