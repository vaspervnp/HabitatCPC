; door.asm — ένα κτίσμα τελειώνει: τι αλλάζει στον γράφο (βήμα 87)
;
; Ως το βήμα 86 ο γράφος έπαιρνε τις ακμές ενός κτίσματος τη στιγμή που
; τοποθετούνταν, και τις κρατούσε. Από το 87 ένα εργοτάξιο δεν έχει αέρα:
; φτάνεις σε αυτό μόνο από έξω, με σύνδεση εδάφους από το κοντινότερο airlock
; ή το σκάφος (lk_ground, src/link.asm). Οι διάδρομοί του γίνονται ακμές όταν
; τελειώσει — εδώ, από το ja_build (src/jobs.asm).
;
; Εδώ και όχι στο link.asm: το πέρασμα των εργασιών τρέχει και στο
; tests/simtest.asm, που δεν έχει ούτε το ui ούτε τον δρομολογητή.

; ---------------------------------------------------------------------------
; lk_done — A = κόμβος που μόλις τελείωσε, (jb_ag) ο χτίστης που στέκεται
; εκεί. Τράπεζα 6 μέσα. Σε θόλο βγαίνουν όλοι όσοι στέκονται εκεί (lk_out).
;
; ΕΝΑΣ ΘΟΛΟΣ ΣΦΡΑΓΙΖΕΤΑΙ. Οι ακμές του ως τώρα ήταν μόνο συνδέσεις εδάφους,
; και φεύγουν όλες: σε θόλο μπαίνεις μόνο από airlock. Ο χτίστης δούλευε απ'
; έξω, οπότε βγαίνει εκεί που τον έφερε η πρώτη τους — αλλιώς ο πρώτος θόλος
; κλείδωνε μέσα του τον μόνο μηχανικό, και το airlock δεν χτιζόταν ποτέ.
;
; Η σύνδεση εδάφους πάει πάντα σε δομή (σκάφος ή airlock). Ενας θόλος που η
; πρώτη του ακμή πάει σε θόλο έχει ήδη τους διαδρόμους του ως ακμές — δεν
; γίνεται στο παιχνίδι, γίνεται στις σκηνές του tests/test_sim.py — και τους
; κρατά.
;
; ΜΕΤΑ, κάθε διάδρομος που τον αγγίζει και του οποίου η άλλη άκρη είναι ήδη
; έτοιμη γίνεται ακμή — αν δεν είναι ήδη: ένα airlock που ξαναχτίζεται μετά
; από μετεωρίτη έχει ακόμη τον διάδρομό του.
; ---------------------------------------------------------------------------
lk_done:
        ld      (lk_n),a
        cp      MAX_DOME
        jr      nc,lkd_st
        ld      l,a
        ld      h,NODEPG
        ld      a,(hl)
        or      a
        jr      z,lkd_corr              ; χωρίς σύνδεση εδάφους (σκηνές χωρίς άγκυρα)
        ld      a,(lk_n)
        call    lk_adj
        ld      a,(hl)                  ; εκεί που βγαίνει ο χτίστης
        cp      MAX_DOME
        jr      c,lkd_corr              ; θόλος: ακμή διαδρόμου, όχι εδάφους
        call    lk_out
        call    lk_cut
        jr      lkd_corr
lkd_st:
        ; Μια δομή: όσοι στέκονται εκεί μένουν. Αν είναι airlock, στέκονται
        ; πια σε μέρος με αέρα — ως τώρα ήταν εργοτάξιο, δηλαδή έξω: ο χτίστης
        ; ΚΑΙ όσοι έφεραν τα υλικά (βήμα 88· ως το 87 μόνο ο χτίστης). Σε κάθε
        ; άλλη δομή ήταν ήδη έξω.
        call    en_in
        jr      nc,lkd_corr
        ld      hl,lks_in
        call    lk_each
lkd_corr:
        ld      hl,G_corr_tbl
        ld      b,MAX_CORR
lkd_lp:
        push    bc
        push    hl
        ld      a,(hl)                  ; C_A
        cp      255
        jr      z,lkd_nx                ; συνέχεια διαδρομής
        ld      c,a
        inc     hl
        ld      b,(hl)                  ; C_B
        inc     hl
        inc     hl
        inc     hl
        ld      a,(hl)                  ; C_CSTATE
        or      a
        jr      z,lkd_nx
        ld      a,(lk_n)
        cp      c
        jr      z,lkd_o
        cp      b
        jr      nz,lkd_nx
        ld      b,c                     ; B = η άλλη άκρη
lkd_o:
        ld      c,a                     ; C = ο νέος
        ld      a,b
        call    gr_live                 ; κρατά BC
        jr      nz,lkd_nx               ; η άλλη άκρη χτίζεται ακόμη
        ld      l,c
        ld      h,NODEPG
        ld      e,(hl)                  ; ο βαθμός του νέου
        ld      a,e
        or      a
        jr      z,lkd_ln
        ld      a,c
        call    lk_adj
        push    bc
        ld      a,b
        ld      c,e
        ld      b,0
        cpir                            ; μόνο ως τον βαθμό: πιο πέρα μένουν παλιά
        pop     bc
        jr      z,lkd_nx                ; είναι ήδη ακμή
lkd_ln:
        call    cr_link_bc
lkd_nx:
        pop     hl
        ld      de,CORR_REC
        add     hl,de
        pop     bc
        djnz    lkd_lp
        ret

; lk_adj — A = κόμβος -> HL = node_adj + 8 * κόμβος. Κρατά A, BC, DE.
lk_adj:
        ld      l,a
        ld      h,0
        add     hl,hl
        add     hl,hl
        add     hl,hl
        push    de
        ld      de,G_node_adj
        add     hl,de
        pop     de
        ret

; lk_cut — σβήνει κάθε ακμή του (lk_n), και από τις δύο μεριές. Από τη λίστα
; του γείτονα φεύγει με το τελευταίο στη θέση του, και η τελευταία θέση μένει
; όπως ήταν: όποιος ταξιδεύει πάνω της φτάνει εκεί που πήγαινε. Μόνο όποιος
; πήγαινε ΣΤΟΝ θόλο που σφραγίστηκε φτάνει στον γείτονα που πήρε τη θέση του,
; κι από εκεί ξαναδρομολογείται.
lk_cut:
        ld      a,(lk_n)
        ld      l,a
        ld      h,NODEPG
        ld      b,(hl)                  ; ο βαθμός του
        ld      (hl),0
        call    lk_adj
lkc_lp:
        push    bc
        push    hl
        ld      a,(hl)                  ; ο γείτονας
        ld      e,a
        ld      d,NODEPG                ; DE -> ο βαθμός του γείτονα
        call    lk_adj
        ld      a,(de)
        or      a
        jr      z,lkc_nx
        ld      c,a
        ld      b,0
        push    hl
        ld      a,(lk_n)
        cpir
        pop     bc                      ; BC = η αρχή της λίστας του
        jr      nz,lkc_nx               ; μισή ακμή: τίποτα να σβήσει
        dec     hl                      ; HL -> η θέση του σφραγισμένου
        ld      a,(de)
        dec     a
        ld      (de),a
        add     a,c                     ; η γραμμή είναι στοιχισμένη στα 8:
        ld      c,a                     ; χωρίς κρατούμενο (assert, graph.asm)
        ld      a,(bc)
        ld      (hl),a                  ; το τελευταίο στη θέση του
lkc_nx:
        pop     hl
        pop     bc
        inc     hl
        djnz    lkc_lp
        jp      rt_mark

; lk_out — A = ο κόμβος έξω: ΟΣΟΙ ΣΤΕΚΟΝΤΑΙ στον θόλο (lk_n) πάνε εκεί,
; ακίνητοι, έξω. Ως το βήμα 87 μόνο ο χτίστης (jb_ag)· από το 88 στέκονται
; εκεί και όσοι έφεραν τα υλικά, και ο θόλος που σφραγιζόταν τους κλείδωνε
; μέσα, χωρίς ακμή: έπαιρναν τις εργασίες του επόμενου εργοταξίου, δεν έβρισκαν
; δρόμο, τις άφηναν και τις ξανάπαιρναν — και οι έξω δεν έπαιρναν ποτέ καμία
; (tests/test_outside.py). Οποιος ταξιδεύει ήδη φεύγοντας φτάνει κανονικά
; (lk_cut).
lk_out:
        ld      (lk_t),a
        ld      hl,lko_one
; lk_each — HL = ρουτίνα: καλείται με A = κάθε ζωντανός που στέκεται στον
; (lk_n), όχι στον δρόμο. Ενα πέρασμα των 128, μία φορά ανά θόλο ή airlock που
; τελειώνει: ο κόμβος μένει στον A και ο πράκτορας είναι ο L, οπότε όποιος
; είναι αλλού κοστίζει cp (hl), jr, inc l, djnz — 36 T, ~1,2 ms οι 128. Η
; κλήση γράφεται στη δική της διεύθυνση, όπως στο ent_needs_slice.
lk_each:
        ld      (lke_call + 1),hl
        ld      hl,(AG_PG + 1) * 256    ; οι κόμβοι· L = ο πράκτορας
        ld      b,N_AGENT
        ld      a,(lk_n)
lke_lp:
        cp      (hl)
        jr      z,lke_hit
lke_nx:
        inc     l
        djnz    lke_lp
        ret
lke_hit:
        push    bc
        push    hl
        set     7,l
        inc     h
        ld      a,(hl)                  ; edge
        inc     a
        jr      nz,lke_pop              ; στον δρόμο
        res     7,l
        ld      h,AG_PG
        bit     0,(hl)                  ; F_ALIVE
        jr      z,lke_pop
        ld      a,l
lke_call:
        call    lko_one
lke_pop:
        pop     hl
        pop     bc
        ld      a,(lk_n)
        jr      lke_nx
; lks_in — A = πράκτορας: μέσα (F_INDOORS).
lks_in:
        ld      l,a
        ld      h,AG_PG
        set     1,(hl)
        ret
; lko_one — A = πράκτορας στον θόλο (lk_n): στο (lk_t), έξω.
lko_one:
        ld      (em_id),a
        ld      a,(lk_n)
        ld      (em_node),a
        call    ent_release             ; η θέση του στον δακτύλιο
        ld      a,(lk_t)
        call    ent_claim               ; A = θέση στον νέο κόμβο
        ld      c,a
        ld      a,(em_id)
        ld      l,a
        ld      h,AG_PG
        res     1,(hl)                  ; F_INDOORS
        inc     h
        ld      a,(lk_t)
        ld      (hl),a                  ; node
        inc     h
        ld      (hl),a                  ; dest: δεν ξαναγυρίζει στον θόλο
        dec     h
        set     7,l
        ld      (hl),c                  ; slot
        jp      fg_mark                 ; φαίνεται στη δομή (βήμα 89)

; ---------------------------------------------------------------------------
; ΜΕΣΑ Ή ΕΞΩ. Εκτός από την κίνηση, το F_INDOORS (bit 1 των σημαιών) το
; γράφουν μόνο το lks_in και το lko_one πιο πάνω — ως το βήμα 87 το en_put. Εδώ και όχι στο entity.asm: η τράπεζα 0 είναι γεμάτη
; ως τη σκαλωσιά των tests (#3C00), η 2 έχει χώρο και είναι πάντα ορατή.
; ---------------------------------------------------------------------------

; en_in — A = κόμβος -> CY αν είναι μέρος με αέρα: έτοιμος θόλος ή έτοιμο
; airlock. Το εργοτάξιο, η δομή και το σκάφος είναι έξω. Χαλάει A, DE, HL·
; κρατά BC. Τράπεζα 6 μέσα.
;
; Χωρίς το gr_live, παρότι ρωτά το ίδιο: η κίνηση το καλεί σε κάθε άφιξη και
; σε κάθε αναχώρηση από μέσα, και το gr_live με τα push του και το δεύτερο
; cp ήταν 60 us — εδώ 40 για θόλο, και η θέση 0 γύρισε κάτω από το βήμα 86.
en_in:
        cp      MAX_DOME
        jr      nc,eni_s
        ld      l,a
        add     a,a
        add     a,l                     ; 3 * θόλος < 192: χωράει σε byte
        ld      l,a
        ld      h,0
        add     hl,hl
        add     hl,hl
        add     hl,hl                   ; 24 * θόλος
        ld      de,G_dome_tbl + D_STATE
eni_st:
        add     hl,de
        ld      a,(hl)
        xor     DS_ACTIVE
        cp      1                       ; CY αν ήταν DS_ACTIVE
        ret
eni_s:
        ld      l,a
        ld      h,0
        add     hl,hl
        add     hl,hl
        add     hl,hl                   ; 8 * κόμβος
        ld      de,G_struct_tbl - MAX_DOME * STRUCT_REC + ST_KIND
        add     hl,de
        ld      a,(hl)
        cp      K_AIRLOCK
        ld      de,ST_STATE - ST_KIND
        jr      z,eni_st
        or      a                       ; δομή ή σκάφος: έξω
        ret

        assert  DOME_REC == 24 && STRUCT_REC == 8
        assert  F_INDOORS == 2 && MAX_DOME == 64 && ST_STATE - ST_KIND == 2

; en_count — C = ζωντανοί, E = ζωντανοί με F_INDOORS (το ef_o2, src/econ.asm).
; Ξετυλιγμένο στα οκτώ: ως το βήμα 86 ο βρόχος μετρούσε μόνο ζωντανούς, 12 us
; τον καθένα με το djnz. Το δεύτερο bit θα έφερνε 15· ξετυλιγμένο, 11,5 —
; κάτω από το 86 και με τα δύο. Και οι 128 θέσεις, πάντα.
en_count:
        ld      hl,G_agent_fields       ; η σελίδα των σημαιών
        ld      bc,(N_AGENT / 8) * 256
        ld      e,c
enc_lp:
        repeat  8
        ld      a,(hl)
        rra                             ; F_ALIVE
        jr      nc,$ + 7                ; -> inc l
        inc     c
        rra                             ; F_INDOORS
        jr      nc,$ + 3                ; -> inc l
        inc     e
        inc     l
        rend
        djnz    enc_lp
        ret

        assert  F_ALIVE == 1 && (G_agent_fields & 255) == 0 && N_AGENT == 128

lk_n:       db 0
lk_t:       db 0
