; supply.asm — πρώτα τα υλικά, μετά ο μηχανικός (DESIGN §6.9, βήμα 88).
;
; Ενα εργοτάξιο περνά από τέσσερις καταστάσεις:
;
;   1. ΤΟΠΟΘΕΤΗΘΗΚΕ  το κόστος έφυγε από τα αποθέματα (όπως ως το 87, επιλογή
;                    του παίκτη), και το εργοτάξιο ΧΡΩΣΤΙΕΤΑΙ ό,τι πλήρωσε, σε
;                    φορτία των δέκα (bd_commit, sp_jobs).
;   2. ΤΡΟΦΟΔΟΤΕΙΤΑΙ μία εργασία Supply ανά υλικό που χρωστιέται, το πολύ δύο.
;                    Την παίρνει ΟΠΟΙΟΣΔΗΠΟΤΕ — κάθε άποικος και το ρομπότ
;                    μεταφοράς. Δύο σκέλη: ως την πηγή (sp_take), και από εκεί
;                    στο εργοτάξιο με ένα φορτίο (sp_arrive).
;   3. ΧΤΙΖΕΤΑΙ      μόνο όταν φτάσει και το τελευταίο φορτίο δημοσιεύεται η
;                    εργασία Build, και την παίρνει ΜΟΝΟ μηχανικός ή ρομπότ
;                    κατασκευής (job_roles, src/jobs.asm). Αν δεν ζει κανένας,
;                    το HUD λέει NO ENGINEER (sp_noeng).
;   4. ΤΕΛΕΙΩΣΕ      όπως ως το 87 (ja_build, lk_done).
;
; ΠΟΥ ΚΑΘΟΝΤΑΙ ΤΑ ΧΡΕΗ, ΧΩΡΙΣ ΝΕΟ ΠΙΝΑΚΑ. Ενας θόλος που χτίζεται δεν έχει
; ούτε ρεύμα ούτε χειριστές: το μέταλλο στο D_POWER, το βιοπλαστικό στο D_OPS,
; ως 255 φορτία το καθένα (ο χειρότερος θόλος L με τέσσερις διαδρόμους θέλει
; ~36). Μια δομή έχει ΕΝΑ ελεύθερο byte, το όγδοο (ST_OWED): μέταλλο στα
; πάνω τέσσερα bits, βιοπλαστικό στα κάτω — το έβδομο είναι το ST_JOINED του
; airlock, και η χειρότερη δομή, ένα airlock με διάδρομο 12 πλακιδίων, θέλει
; 9 και 5 (assert στο src/link.asm). Ο πράκτορας κρατά το φορτίο του στο spare (AG_PG + 7, πάνω μισό):
; το απόθεμα που κουβαλά, ή 0.
;
; ΤΑ ΦΟΡΤΙΑ ΣΤΡΟΓΓΥΛΕΥΟΝΤΑΙ ΠΡΟΣ ΤΑ ΠΑΝΩ: ένα ηλιακό των 15 είναι 10 και 5,
; δύο ταξίδια. Το «ακύρωση ή καταστροφή επιστρέφει ό,τι δεν παραδόθηκε» του
; §6.9 δεν έχει πού να συμβεί: τίποτα στο παιχνίδι δεν ακυρώνει ή δεν γκρεμίζει
; εργοτάξιο — ο μετεωρίτης παίρνει μόνο την πρόοδο (src/meteor.asm). Οταν
; έρθει το γκρέμισμα, θα χρειαστεί και το υπόλοιπο της δεκάδας, που εδώ δεν
; κρατιέται.
;
; ΑΥΤΟΤΕΛΕΣ: μόνο το const.asm και το layout. Το περιλαμβάνουν το παιχνίδι
; (τράπεζα 2), το harness της προσομοίωσης, της διεπαφής και των αντικειμένων
; — καθένα θέλει άλλο κομμάτι του, και κανένα δεν έχει όλα τα άλλα αρχεία.

SP_PRIO     equ 4                   ; κάτω από το Build (5): ο μηχανικός χτίζει πρώτα

        assert  D_POWER == 6 && D_OPS == 7 && ST_OWED == 7
        assert  G_struct_tbl == G_dome_tbl + MAX_DOME * DOME_REC
        assert  NO_JOB == 255 && J_BUILD == 0 && JOB_REC < 256
        assert  J_PRIO == 3 && J_SITE == 4

; ---------------------------------------------------------------------------
; jb_post_build — A = κόμβος. Μία εργασία Build στην πρώτη ελεύθερη θέση· αν
; δεν υπάρχει, καμία. Κρατά το A. Out: B = 0 αν ο πίνακας ήταν γεμάτος, αλλιώς
; HL -> το J_SITE της νέας.
;
; Από το src/jobpost.asm (βήματα 38-87), ίδιο byte προς byte εκτός από το
; τελευταίο, που είναι πια ο κόμβος (J_SITE) και όχι 0. Εδώ, στην τράπεζα 2,
; επειδή το καλούν πια μόνο δύο ρουτίνες της: το sp_build (ο μετεωρίτης, ένα
; εργοτάξιο που τροφοδοτήθηκε) και το sp_post.
;
; ΤΟ inc (hl) ΕΙΝΑΙ ΚΑΙ ΕΡΩΤΗΣΗ ΚΑΙ ΑΠΑΝΤΗΣΗ (βήμα 70, DESIGN §6.7): μια ελεύθερη
; θέση είναι NO_JOB = 255, και το 255 + 1 είναι 0 = J_BUILD, ήδη γραμμένο. Μια
; πιασμένη το ξαναπαίρνει πίσω με dec (hl) — οι διακοπές δεν γράφουν εδώ.
; ---------------------------------------------------------------------------
jb_post_build:
        ld      hl,G_job_tbl
        ld      de,JOB_REC
        ld      b,MAX_JOB
jpb_lp:
        inc     (hl)                    ; NO_JOB + 1 = J_BUILD: Z = ελεύθερη
        jr      z,jpb_got
        dec     (hl)                    ; πιασμένη: όπως ήταν
        add     hl,de
        djnz    jpb_lp
        ret
jpb_got:
        inc     hl                      ; το είδος είναι ήδη J_BUILD
        ld      (hl),a                  ; ο κόμβος
        inc     hl
        ld      (hl),255                ; αδιάθετη
        inc     hl
        ld      (hl),5                  ; προτεραιότητα, από το job_prio
        inc     hl
        ld      (hl),a                  ; J_SITE: ο ίδιος κόμβος
        ret

; sp_build — A = κόμβος: μια Build, και το EC_NBUILD μετρά όσες μπήκαν. Κρατά
; το A. Το jb_post_build μένει όπως το μέτρησε το βήμα 70 (tests/test_jobpost.py).
sp_build:
        call    jb_post_build
        inc     b
        dec     b
        ret     z                       ; ο πίνακας γέμισε: καμία
        ld      hl,EC_NBUILD
        inc     (hl)
        ret

; sp_post — A = κόμβος, C = είδος (Supply): όπως το jb_post_build, με άλλο είδος
; και προτεραιότητα. Κρατά τα A, C. Το Build μένει όπως μετρήθηκε στο βήμα 70
; (tests/test_jobpost.py) και η Supply γράφεται από πάνω του.
sp_post:
        call    jb_post_build
        inc     b
        dec     b
        ret     z                       ; ο πίνακας γέμισε
        dec     hl
        ld      (hl),SP_PRIO
        dec     hl
        dec     hl
        dec     hl
        ld      (hl),c                  ; το είδος
        ret

; ---------------------------------------------------------------------------
; sp_jobs — A = ο κόμβος του νέου εργοταξίου, (sp_m), (sp_b) = τα φορτία που
; χρωστά — τα έγραψε στην εγγραφή του το bd_commit (src/build.asm). Μία Supply
; ανά υλικό που χρωστιέται — ή η Build, αν δεν χρωστά τίποτα. Κρατά το A.
; ---------------------------------------------------------------------------
sp_jobs:
        ld      hl,(sp_m)               ; L = μέταλλο, H = βιοπλαστικό
        ld      b,a
        ld      a,h
        or      l
        ld      a,b
        jp      z,sp_build              ; δεν χρωστά τίποτα: κατευθείαν ο χτίστης
        push    hl
        ld      c,J_SUPPLY
        inc     l
        dec     l
        call    nz,sp_post
        pop     hl
        inc     h
        dec     h
        ret     z
        inc     c                       ; J_SUPPLY + 1: βιοπλαστικό
        jr      sp_post

; sp_loads — HL = μονάδες -> A = φορτία των δέκα, στρογγυλεμένα προς τα πάνω:
; (μονάδες + 9) / 10, με αφαιρέσεις. Το add hl,-10 δίνει CY όσο έμεναν δέκα.
sp_loads:
        ld      de,9
        add     hl,de
        ld      de,-10
        ld      a,-1
spl_lp:
        inc     a
        add     hl,de
        jr      c,spl_lp
        ret

; sp_owed — A = κόμβος, (sp_mat) = 0 μέταλλο, 1 βιοπλαστικό. HL -> το byte
; αυτού του υλικού, DE -> του άλλου (σε δομή το ίδιο), B = ένα φορτίο, C = η
; μάσκα του. Απαιτεί την τράπεζα 6. Θόλος: x24 από το G_dome_tbl· δομή: x8
; από το G_struct_tbl, που αρχίζει αμέσως μετά τους θόλους.
sp_owed:
        ld      l,a
        ld      h,0
        add     hl,hl
        add     hl,hl
        add     hl,hl                   ; x8
        ld      de,G_struct_tbl - MAX_DOME * STRUCT_REC + ST_OWED
        cp      MAX_DOME
        jr      nc,spo_add
        ld      d,h
        ld      e,l
        add     hl,hl
        add     hl,de                   ; x24
        ld      de,G_dome_tbl + D_OPS
spo_add:
        add     hl,de                   ; D_OPS, ή ST_OWED
        cp      MAX_DOME
        ld      d,h
        ld      e,l
        ld      a,(sp_mat)
        jr      nc,spo_st
        dec     de                      ; D_POWER
        or      a
        jr      nz,spo_one              ; βιοπλαστικό: HL -> D_OPS, DE -> D_POWER
        ex      de,hl                   ; μέταλλο: HL -> D_POWER, DE -> D_OPS
spo_one:
        ld      bc,#01FF
        ret
spo_st:
        or      a
        ld      bc,#10F0                ; μέταλλο: τα πάνω τέσσερα bits
        ret     z
        ld      bc,#010F
        ret

; ---------------------------------------------------------------------------
; sp_take — από το jb_take (src/jobs.asm), όταν ο πράκτορας μόλις πήρε μια
; Supply: HL -> J_AGENT της, E = id, D = AG_PG + 2 (ο προορισμός του, που
; είναι ήδη το εργοτάξιο). Τράπεζα 6. Διαλέγει ΠΗΓΗ και τον στέλνει εκεί
; πρώτα.
;
; Η ΠΗΓΗ είναι η κοντινότερη ΣΕ ΑΥΤΟΝ από το σκάφος (η δομή 0, αν είναι
; σκάφος — στην αποικία δοκιμών δεν είναι) και τις αποθήκες σε λειτουργία
; (το ευρετήριο δωματίων, ως ROOM_MAX). Στην ισοπαλία το σκάφος. Μια πηγή
; που δεν φτάνει (DIST = 255) δεν μετρά· χωρίς καμία, πηγαίνει κατευθείαν
; στο εργοτάξιο και το φορτίο λογαριάζεται ότι το έχει ήδη.
; ---------------------------------------------------------------------------
sp_take:
        dec     hl                      ; J_NODE
        set     7,e
        ld      d,AG_PG + 7
        xor     a
        ld      (de),a                  ; spare = 0: δεν κουβαλά ακόμη
        res     7,e
        ld      d,AG_PG + 1
        ld      a,(G_struct_tbl + ST_KIND)
        sub     K_SHIP
        ld      (sp_mat),a              ; εδώ: 0 = υπάρχει σκάφος
        ld      a,(de)                  ; ο κόμβος του
        push    de
        push    hl
        ld      h,a
        ld      l,0
        srl     h
        rr      l
        set     6,h                     ; η γραμμή του στο DIST: #4000 + 128 x κόμβος
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        ld      bc,#FFFF                ; B = η πηγή, C = η απόστασή της
        ld      a,(sp_mat)
        or      a
        jr      nz,spt_st
        ld      a,MAX_DOME              ; το σκάφος, κόμβος 64
        call    spt_one
spt_st:
        ld      de,G_room_list + R_STORAGE * ROOM_MAX
        ld      a,(G_room_n + R_STORAGE)
spt_lp:
        or      a
        jr      z,spt_got
        push    af
        ld      a,(de)
        inc     de
        call    spt_one
        pop     af
        dec     a
        jr      spt_lp
spt_got:
        ld      a,b
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        pop     hl
        pop     de
        inc     a
        ret     z                       ; καμία πηγή: το εργοτάξιο, όπως είναι
        dec     a
        ld      (hl),a                  ; J_NODE = η πηγή
        inc     d
        ld      (de),a                  ; dest = η πηγή
        ret
; spt_one — A = κόμβος-πηγή, HL = η γραμμή του DIST (L = 0 ή 128): αν είναι
; πιο κοντά από τον C, B = αυτός και C = η απόστασή του. Κρατά DE, HL.
spt_one:
        push    hl
        push    af
        add     a,l
        ld      l,a
        ld      a,(hl)                  ; η απόστασή του
        cp      c
        pop     hl                      ; H = ο κόμβος
        jr      nc,spto_n
        ld      c,a
        ld      b,h
spto_n:
        pop     hl
        ret

; ---------------------------------------------------------------------------
; sp_arrive — από το jb_arrive (src/jobs.asm): ο πράκτορας μιας Supply στέκεται
; στο J_NODE της, C. HL -> η εργασία, E = id (το bit 7 αδιάφορο). Τράπεζα 6.
; Μια J_TRADE πάει στο tr_arrive (βήμα 98), με την ίδια σύμβαση.
; Out: Z       πήρε φορτίο από την πηγή και πάει στο εργοτάξιο: η εργασία
;              μένει δική του
;      NZ, CY  παρέδωσε, και αυτό το υλικό χρωστιέται ακόμη: ξανανοίγει
;      NZ, NC  παρέδωσε το τελευταίο φορτίο του υλικού: τελειώνει — και αν
;              το εργοτάξιο δεν χρωστά πια τίποτα, δημοσιεύεται η Build
; ---------------------------------------------------------------------------
sp_arrive:
        ld      a,(hl)
        cp      J_TRADE
        jp      z,tr_arrive             ; τα αγαθά του εμπόρου (βήμα 98, src/carry.asm)
        sub     J_SUPPLY
        ld      (sp_mat),a              ; 0 μέταλλο, 1 βιοπλαστικό
        inc     hl
        ld      c,(hl)                  ; J_NODE: εκεί που στέκεται
        inc     hl
        inc     hl
        inc     hl
        ld      a,(hl)                  ; J_SITE: το εργοτάξιο
        set     7,e
        ld      d,AG_PG + 7             ; spare
        cp      c
        jr      z,spa_site
        ; --- στην πηγή: ένα φορτίο, και το δεύτερο σκέλος ---
        dec     hl
        dec     hl
        dec     hl
        ld      (hl),a                  ; J_NODE = το εργοτάξιο
        ld      b,a
        ld      a,(sp_mat)
        add     a,S_METAL
        ld      (de),a                  ; spare = το απόθεμα που κουβαλά
        res     7,e
        ld      d,AG_PG + 2
        ld      a,b
        ld      (de),a                  ; dest = το εργοτάξιο
        xor     a                       ; Z
        ret
spa_site:
        ; --- στο εργοτάξιο: το φορτίο παραδίδεται ---
        ld      b,a
        xor     a
        ld      (de),a                  ; spare = 0
        ld      a,b
        ; ΚΑΙ ΣΤΙΣ ΜΗΧΑΝΕΣ (βήμα 99, src/install.asm): ένας θόλος σε λειτουργία
        ; δεν χρωστά ο ίδιος — το D_POWER και το D_OPS του είναι ρεύμα και
        ; χειριστές — και ένα εργοτάξιο που δεν το χρωστά το δίνει σε αυτές.
        call    mc_live
        jp      nz,mc_arrive
        push    af
        call    sp_owed                 ; HL, DE, B = φορτίο, C = μάσκα
        ld      a,(hl)
        and     c
        jr      z,spa_mach              ; δεν το χρωστά: μια μηχανή του
        ld      a,(hl)
        sub     b
        ld      (hl),a
        and     c
        jr      z,spa_paid
        pop     af
        xor     a
        inc     a                       ; NZ
        scf                             ; CY: κι άλλο ταξίδι
        ret
spa_paid:
        ld      a,(de)
        or      (hl)                    ; και το άλλο υλικό;
        pop     bc                      ; B = το εργοτάξιο
        ld      a,b
        call    z,sp_build              ; όλα έφτασαν: σειρά του χτίστη
        jp      mc_tail                 ; NZ: τελειώνει, ή CY αν μια μηχανή το χρωστά
spa_mach:
        pop     af
        jp      mc_arrive

; ---------------------------------------------------------------------------
; mc_live — A = ο κόμβος μιας Supply. NZ αν είναι θόλος σε λειτουργία: τότε
; τα χρωστάνε μόνο οι μηχανές του. Κρατά A, BC. Τράπεζα 6. Από το sp_arrive.
; Εδώ, στην τράπεζα 2, από το βήμα 100: ο χώρος της 0 πήγε στα σήματα.
; ---------------------------------------------------------------------------
mc_live:
        cp      MAX_DOME
        jr      nc,mcl_st
        call    jb_dome_ptr             ; κρατά το A (src/jobs.asm)
        ld      de,D_STATE
        add     hl,de
        bit     1,(hl)                  ; DS_ACTIVE
        ret
mcl_st:
        cp      a                       ; δομή: Z
        ret

; ---------------------------------------------------------------------------
; mc_order — A = θόλος, από το fit_set (src/fit.asm): μία Supply ανά υλικό
; για τη μηχανή που μόλις μπήκε, αν δεν υπάρχει ήδη μία για αυτόν τον θόλο —
; του εργοταξίου του ή άλλης μηχανής του (βήμα 99, src/install.asm). Κρατά
; το A και το HL.
; ---------------------------------------------------------------------------
mc_order:
        push    hl
        ld      c,J_SUPPLY
        call    mco_one
        inc     c                       ; J_SUPPLY + 1: βιοπλαστικό
        call    mco_one
        pop     hl
        ret
mco_one:
        call    sp_find
        ret     z
        jp      sp_post                 ; κρατά τα A, C

; sp_find — A = κόμβος, C = είδος: Z αν υπάρχει εργασία αυτού του είδους με
; J_SITE αυτόν τον κόμβο. Κρατά τα A, C· χαλάει B, DE, L, IX. Μια ελεύθερη
; θέση είναι NO_JOB, που δεν είναι κανένα είδος.
sp_find:
        ld      ix,G_job_tbl
        ld      de,JOB_REC
        ld      b,MAX_JOB
spf_lp:
        cp      (ix+J_SITE)
        jr      nz,spf_n
        ld      l,a
        ld      a,c
        cp      (ix+J_KIND)
        ld      a,l
        ret     z
spf_n:
        add     ix,de                   ; το add ix δεν αγγίζει το Z: NZ στο τέλος
        djnz    spf_lp
        ret

; ---------------------------------------------------------------------------
; sp_noeng — CY αν μια εργασία Build περιμένει και δεν ζει κανείς που χτίζει:
; ούτε μηχανικός ούτε ρομπότ κατασκευής. Από το hud_alert, με την τράπεζα 1·
; σελιδοποιεί την 6 μόνο αν υπάρχει Build, και γυρίζει στην 1.
;
; ΣΤΟ HUD ΚΑΙ ΟΧΙ ΣΤΟΝ ΤΡΟΧΟ, και πρώτα ένα byte: το EC_NBUILD. Χωρίς Build στον
; πίνακα — σχεδόν πάντα — κοστίζει 26 T ανά τικ HUD· μια σάρωση των 32
; εργασιών θα ήταν ~380 us. Με Build, οι πράκτορες ως τον πρώτο που χτίζει.
; Αν δεν ζει κανείς, καμία Build δεν μπορεί να είναι πιασμένη (το μάζεμα).
; ---------------------------------------------------------------------------
sp_noeng:
        ld      a,(EC_NBUILD)
        or      a
        ret     z                       ; NC: καμία Build
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        ld      hl,G_agent_fields       ; οι σημαίες· ο ρόλος στο +128
        ld      b,128
spn_ag:
        bit     0,(hl)                  ; F_ALIVE
        jr      z,spn_an
        set     7,l
        ld      a,(hl)
        res     7,l
        and     7
        cp      RL_ENGINEER
        jr      z,spn_yes               ; NC
        cp      RL_CBOT
        jr      z,spn_yes
spn_an:
        inc     l
        djnz    spn_ag
        scf                             ; κανείς
spn_yes:
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        ret

sp_mat:     db 0                    ; 0 μέταλλο, 1 βιοπλαστικό
sp_m:       db 0                    ; φορτία μετάλλου, και δίπλα του
sp_b:       db 0                    ; βιοπλαστικού (bd_commit, sp_jobs)
        assert  sp_b == sp_m + 1
        assert  (G_agent_fields & 255) == 0
