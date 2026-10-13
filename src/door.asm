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
        ld      a,l                     ; ο κόμβος, όπως στο ld l,a
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
; Το #9300 είναι (#12 << 11) + #300: το #12 μπαίνει στο H πριν από τα τρία
; add, και το #300 με δύο inc h — #200 πριν από το τρίτο add, #100 μετά.
lk_adj:
        ld      l,a
        ld      h,G_node_adj >> 11
        add     hl,hl
        add     hl,hl
        inc     h                       ; x2 από το επόμενο add: #200
        add     hl,hl
        inc     h                       ; #100
        ret
        assert  (G_node_adj & #7FF) == #300  ; αλλιώς άλλα inc h (και στο cr_edge)

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
; τελειώνει. Η κλήση γράφεται στη δική της διεύθυνση, όπως στο
; ent_needs_slice.
;
; ΜΕ ΤΟ cpir (βήμα 104): όποιος είναι αλλού κοστίζει 21 T. Ως τότε cp (hl),
; jr, inc l, djnz — 31 T, ~1 ms οι 128. Και ένας νεκρός, ή μια άδεια θέση,
; κοιτάζεται χωρίς push και pop: οι άδειες θέσεις έχουν κόμβο 0 (game_new),
; οπότε για τον θόλο 0 ο βρόχος σταματούσε 124 φορές, 6 ms. Πληρώνει το
; δεύτερο πέρασμα του lk_air_out, για τον σωλήνα.
lk_each:
        ld      (lke_call + 1),hl
        ld      hl,(AG_PG + 1) * 256    ; οι κόμβοι· L - 1 = ο πράκτορας
        ld      bc,N_AGENT
lke_a:
        ld      a,(lk_n)
        cpir
        ret     nz                      ; κανείς άλλος
        dec     l                       ; L = ο πράκτορας
        dec     h                       ; AG_PG: οι σημαίες
        bit     0,(hl)                  ; F_ALIVE
        jr      z,lke_no                ; νεκρός, ή άδεια θέση: κόμβος 0
        inc     h
        inc     h
        set     7,l
        ld      a,(hl)                  ; edge
        res     7,l
        dec     h                       ; ξανά στους κόμβους
        inc     a
        jr      nz,lke_nx               ; στον δρόμο
        push    bc
        push    hl
        ld      a,l
lke_call:
        call    lko_one
        pop     hl
        pop     bc
        jr      lke_nx
lke_no:
        inc     h
lke_nx:
        inc     l
        ld      a,b
        or      c
        jr      nz,lke_a
        ret
; lks_in — A = πράκτορας: μέσα (F_INDOORS).
lks_in:
        ld      l,a
        ld      h,AG_PG
        set     1,(hl)
        ret
; lk_air_out — A = ένα airlock που ξανάγινε εργοτάξιο (src/meteor.asm): όσοι
; στέκονταν μέσα του, έξω, με γεμάτη στολή (βήμα 90). Κρατά το BC.
;
; ΚΑΙ ΟΣΟΙ ΕΡΧΟΝΤΑΙ ΣΤΟΝ ΣΩΛΗΝΑ (βήμα 104). Οποιος ταξιδεύει μέσα φτάνει
; μέσα: η αναχώρηση ρώτησε τον στόχο, και τότε το airlock είχε αέρα. Οποιος
; ερχόταν σε αυτό από θόλο τη στιγμή της κρούσης θα έφτανε σε εργοτάξιο με το
; F_INDOORS, και θα ανέπνεε τον αέρα της αποικίας ως την επόμενη αναχώρησή
; του. Βγαίνει τώρα, όπως αν είχε ξεκινήσει μετά την κρούση: έξω, με γεμάτη
; στολή, στο έδαφος. «Ερχόταν» είναι ό,τι ρωτά η άφιξη (em_arrive): ο κόμβος
; στην άλλη άκρη της ακμής του, node_adj[node * 8 + edge].
;
; Ενα πέρασμα των 128 στη στήλη των edge: όσοι δεν ταξιδεύουν κοστίζουν 35 T,
; ~1,1 ms. Μόνο σε κρούση σε έτοιμο airlock.
lk_air_out:
        ld      (lk_n),a
        push    bc
        ld      hl,lks_out
        call    lk_each
        ld      a,(lk_n)
        ld      e,a                     ; E = το airlock
        ld      hl,(AG_PG + 2) * 256 + 128      ; τα edge· L - 128 = ο πράκτορας
        ld      b,N_AGENT
lkt_lp:
        ld      a,(hl)
        inc     a
        jr      nz,lkt_tr               ; ταξιδεύει
lkt_nx:
        inc     l
        djnz    lkt_lp
        pop     bc
        ret
lkt_tr:
        push    bc
        push    hl
        dec     a
        ld      c,a                     ; C = edge
        res     7,l
        dec     h                       ; AG_PG + 1: ο κόμβος
        ld      a,(hl)
        push    hl
        call    lk_adj                  ; κρατά A, BC, DE
        ld      a,l
        add     a,c                     ; η γραμμή των 8 δεν περνά σελίδα
        ld      l,a
        ld      a,(hl)                  ; εκεί που φτάνει
        pop     hl
        cp      e
        jr      nz,lkt_pop
        dec     h                       ; AG_PG: οι σημαίες
        ld      a,(hl)
        and     F_ALIVE + F_INDOORS
        cp      F_ALIVE + F_INDOORS
        jr      nz,lkt_pop              ; νεκρός, ή ήδη έξω με τη στολή του
        ld      a,l
        push    de
        call    lks_out
        pop     de
lkt_pop:
        pop     hl
        pop     bc
        jr      lkt_nx
lks_out:
        ld      l,a
        ld      h,AG_PG
        res     1,(hl)                  ; F_INDOORS
        ld      h,AG_PG + 7
        ld      (hl),SUIT_TRIP
        jp      fg_mark                 ; φαίνεται, στο εργοτάξιο
; lko_one — A = πράκτορας στον θόλο (lk_n): στο (lk_t), έξω — ή μέσα, αν το
; (lk_t) είναι έτοιμο airlock (βήμα 120).
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
        ; ΣΕ ΕΤΟΙΜΟ AIRLOCK, ΜΕΣΑ (βήμα 120). Ως τότε στέκονταν έξω, στον κόμβο
        ; του airlock και με προορισμό εκεί: η στολή τους, όταν έπεφτε, τους
        ; έστελνε στο κοντινότερο airlock — αυτό που ήδη πατούσαν — και καμία
        ; άφιξη δεν τους έβαζε ποτέ μέσα. Ο παίκτης του tools/play.py έχασε
        ; έτσι τον μηχανικό του, και μετά όλους, όταν χάλασε το OXYGEN.
        push    hl
        ld      a,(lk_t)
        call    en_in                   ; κρατά BC (C = η θέση στον δακτύλιο)
        pop     hl
        jr      nc,lko_out
        set     1,(hl)
lko_out:
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
; γράφουν μόνο το lks_in, το lko_one και το lks_out πιο πάνω — ως το βήμα 87 το en_put. Εδώ και όχι στο entity.asm: η τράπεζα 0 είναι γεμάτη
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
        add     a,a
        add     a,a
        add     a,a                     ; 8 * κόμβος σε 8 bits: = 8 * δομή
        add     a,ST_KIND
        ld      l,a
        ld      h,G_struct_tbl >> 8     ; μία σελίδα (assert πιο κάτω)
        ld      a,(hl)
        cp      K_AIRLOCK
        ld      de,ST_STATE - ST_KIND
        jr      z,eni_st
        or      a                       ; δομή ή σκάφος: έξω
        ret

        assert  DOME_REC == 24 && STRUCT_REC == 8
        assert  F_INDOORS == 2 && MAX_DOME == 64 && ST_STATE - ST_KIND == 2
        assert  (G_struct_tbl & 255) == 0 && MAX_STRUCT * STRUCT_REC == 256

; en_count — C = ζωντανοί, E = ζωντανοί με F_INDOORS (το ef_o2, src/econ.asm).
; ΜΟΝΟ ΟΙ ΑΠΟΙΚΟΙ, 0-79 (βήμα 92): τα ρομπότ δεν πιάνουν θέση στο ταβάνι και δεν
; αναπνέουν. Ως τότε και οι 128, και 48 θέσεις λιγότερες είναι ~250 us κάτω.
; Ξετυλιγμένο στα οκτώ: ως το βήμα 86 ο βρόχος μετρούσε μόνο ζωντανούς, 12 us
; τον καθένα με το djnz. Το δεύτερο bit θα έφερνε 15· ξετυλιγμένο, 11,5 —
; κάτω από το 86 και με τα δύο. Και οι 80 θέσεις, πάντα.
en_count:
        ld      hl,G_agent_fields       ; η σελίδα των σημαιών
        ld      bc,(AG_BOT0 / 8) * 256  ; οι 80 των αποίκων (βήμα 92)
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

        assert  F_ALIVE == 1 && (G_agent_fields & 255) == 0 && (AG_BOT0 & 7) == 0

lk_n:       db 0
lk_t:       db 0
