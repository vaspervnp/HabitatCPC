; repost.asm — ό,τι χάθηκε από γεμάτο πίνακα ξαναδημοσιεύεται (βήμα 115,
; DESIGN §6.7).
;
; Οι εργασίες ενός εργοταξίου δημοσιεύονται σε στιγμές, όχι σε κάθε επίσκεψη:
; στην τοποθέτηση (sp_jobs), στο τελευταίο φορτίο (sp_build), στον εξοπλισμό
; (mc_order), όταν μια μηχανή πάρει τα υλικά της (mca_got), όταν ο μετεωρίτης
; ρίξει μια δομή. Ως το βήμα 114, αν ο πίνακας ήταν γεμάτος εκείνη τη στιγμή,
; η εργασία δεν έμπαινε ποτέ: ένα ηλιακό τοποθετημένο με τον πίνακα γεμάτο
; έμενε εργοτάξιο 30.000 frames αφού άδειασε, με τα 15 μέταλλα πληρωμένα.
;
; Το jb_post_build παίρνει πια τη θέση μιας Operate ή Repair που δεν την πήρε
; κανείς. Οταν δεν υπάρχει ούτε αυτή, σηκώνει το jb_lost, και ο επόμενος
; κύκλος ροής (θέση 12, κάθε 64 περιστροφές) καλεί το sp_sweep: για κάθε
; κόμβο, οι εργασίες που ζητά η ΚΑΤΑΣΤΑΣΗ του, και όποια λείπει από τον πίνακα
; μπαίνει. Στο πρώτο που δεν χωρά σταματά — και το jb_lost ξανασηκώνεται.
;
; ΤΙ ΖΗΤΑ ΜΙΑ ΚΑΤΑΣΤΑΣΗ (sp_want), οι κανόνες των sp_arrive και mc_arrive
; γραμμένοι ανάποδα:
;   - δομή που χτίζεται: Supply μετάλλου αν το πάνω μισό του ST_OWED δεν είναι
;     0, βιοπλαστικού αν το κάτω, Build αν δεν χρωστά τίποτα·
;   - θόλος που χτίζεται: το ίδιο από το D_POWER και το D_OPS, και Supply για
;     όποιο υλικό χρωστά κάποια μηχανή του (bits 0-1 της υγείας). Οι έτοιμες
;     μηχανές του τις στήνει ο χτίστης του θόλου (ja_build): όχι Build γι' αυτές·
;   - θόλος σε λειτουργία: Supply για τα χρέη των μηχανών του, και Build αν
;     μία είναι 4 + 32k (τα υλικά ήρθαν, δεν στήθηκε)·
;   - τίποτε άλλο. Μια μηχανή σταματημένη (0) θέλει Repair, και τη Repair και
;     την Operate τις ξαναβρίσκει το jp_one μόνο του.
; Μια δομή σε λειτουργία δεν χρωστά: το ST_OWED ενός ορυχείου είναι ο σωρός
; του (βήμα 95). Γι' αυτό ο μετεωρίτης που το ρίχνει τον σκορπίζει (mth_struct,
; src/meteor.asm) — αλλιώς ο σωρός θα διαβαζόταν σαν χρέος.
;
; ΤΙ ΚΟΣΤΙΖΕΙ (tests/test_repost.py): 16,6 ms μια αποικία 48 θόλων με οκτώ
; μηχανές και 24 δομών, χωρίς τίποτα χαμένο — ένα frame της θέσης 12, μετά από
; κάθε φόρτωση (wheel_load) ή κάθε χαμένη εργασία. Οσο ο πίνακας μένει γεμάτος
; χωρίς τίποτα να δώσει, το ίδιο σε κάθε κύκλο ως το πρώτο που δεν χωρά. Με
; τη σημαία κάτω, 8 us τον κύκλο.
;
; ΣΤΟ b6code: διαβάζει θόλους και δομές από το #4000 με την 6 μέσα, όπως ο
; κύκλος ροής που το καλεί. Ο,τι καλεί (mc_rec, sp_find, sp_post, sp_build)
; δεν σελιδοποιεί.

; ---------------------------------------------------------------------------
; sp_sweep — όλοι οι κόμβοι, 0 ως 95. Χαλάει τα πάντα.
; ---------------------------------------------------------------------------
sp_sweep:
        xor     a
        ld      (jb_lost),a             ; ένα μπλοκάρισμα στη μέση το ξανασηκώνει
srp_lp:
        call    sp_want                 ; E = bit 0 μέταλλο, 1 βιοπλαστικό, 2 Build
        inc     e
        dec     e
        jr      z,srp_n                 ; οι περισσότεροι: ~3 us αντί για ~30
        ld      c,J_SUPPLY
        call    srp_kind
        ret     c                       ; ο πίνακας γέμισε: τον επόμενο κύκλο
        inc     c                       ; J_SUPPLY + 1
        call    srp_kind
        ret     c
        ld      c,J_BUILD
        call    srp_kind
        ret     c
srp_n:
        inc     a
        cp      MAX_DOME + MAX_STRUCT
        jr      c,srp_lp
        ret

; srp_kind — A = κόμβος, C = είδος, bit 0 του E = τη θέλει: αν δεν είναι ήδη
; στον πίνακα, μπαίνει. E >>= 1. CY αν δεν χώρεσε. Κρατά A, C, E.
srp_kind:
        srl     e
        ret     nc                      ; δεν τη θέλει
        push    de
        call    sp_find                 ; Z: υπάρχει· κρατά A, C
        jr      z,srk_have
        ld      b,a
        ld      a,c
        or      a                       ; J_BUILD
        ld      a,b
        jr      nz,srk_sup
        call    sp_build                ; και το EC_NBUILD
        jr      srk_b
srk_sup:
        call    sp_post
srk_b:
        pop     de
        ld      l,a
        ld      a,b
        cp      1                       ; B = 0: δεν χώρεσε, CY
        ld      a,l
        ret
srk_have:
        pop     de
        or      a                       ; NC
        ret

; ---------------------------------------------------------------------------
; sp_want — A = κόμβος -> E = οι εργασίες που ζητά η κατάστασή του (πάνω).
; Κρατά το A· χαλάει B, D, HL, IX.
; ---------------------------------------------------------------------------
sp_want:
        push    af
        cp      MAX_DOME
        jr      nc,swa_st
        call    mc_rec                  ; IX -> υποδοχή 0, B = υποδοχές, HL -> D_STATE
        ld      e,0
        ld      a,(hl)
        or      a
        jr      z,swa_out               ; DS_EMPTY
swa_mlp:
        ld      a,(ix+D_HEALTH-D_MACH)
        or      a
        jr      z,swa_mn                ; σταματημένη ή άδεια: Repair, όχι εδώ
        jp      m,swa_mn                ; δουλεύει
        and     3
        jr      nz,swa_owe
        set     2,e                     ; 4 + 32k: τη στήνει μια Build
        jr      swa_mn
swa_owe:
        or      e
        ld      e,a                     ; τα υλικά που χρωστά
swa_mn:
        inc     ix
        djnz    swa_mlp
        ld      a,(hl)
        cp      DS_BUILDING
        jr      nz,swa_out              ; σε λειτουργία: μόνο οι μηχανές
        res     2,e                     ; εργοτάξιο: τις στήνει ο χτίστης του
        inc     hl
        inc     hl                      ; D_POWER: φορτία μετάλλου
        ld      a,(hl)
        or      a
        jr      z,swa_b
        set     0,e
swa_b:
        inc     hl                      ; D_OPS: βιοπλαστικού
        or      (hl)
        jr      z,swa_bld               ; δεν χρωστά τίποτα ο ίδιος
        ld      a,(hl)
        or      a
        jr      z,swa_out
        set     1,e
        jr      swa_out
swa_st:
        add     a,a
        add     a,a                     ; 4 x κόμβος = 4 x δομή σε 8 bits
        add     a,STB_C + ST_STATE / 2
        ld      l,a
        ld      h,STB_H
        add     hl,hl                   ; -> ST_STATE (src/const.asm, βήμα 154)
        ld      e,0
        ld      a,(hl)
        cp      DS_BUILDING
        jr      nz,swa_out
        inc     hl
        inc     hl
        inc     hl                      ; ST_OWED: μέταλλο<<4 | βιοπλαστικό
        ld      a,(hl)
        or      a
        jr      z,swa_bld
        cp      #10
        jr      c,swa_sb                ; όχι μέταλλο
        set     0,e
swa_sb:
        and     #0F
        jr      z,swa_out
        set     1,e
        jr      swa_out
swa_bld:
        set     2,e
swa_out:
        pop     af
        ret

        assert  DS_EMPTY == 0 && DS_BUILDING == 1 && J_BUILD == 0
        assert  D_POWER == D_STATE + 2 && D_OPS == D_STATE + 3 && ST_OWED == ST_STATE + 3
        assert  MAX_DOME == 64 && (ST_STATE & 1) == 0
        assert  MACH_HP & 128 && MACH_OWED == 7
