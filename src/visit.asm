; visit.asm — οι επισκέπτες που περπατούν (βήμα 136, DESIGN §6.11)
;
; ΟΠΩΣ ΣΤΟ PLANETBASE, με τις αποφάσεις του παίκτη (βήμα 134): κατεβαίνουν από
; το πλοίο στην πίστα και περπατούν όπως οι άποικοι, τρώνε και πίνουν στο
; κυλικείο, πάνε στο σαλόνι, αναπνέουν όσο είναι μέσα, και πληρώνουν ανά
; υπηρεσία. Μετά γυρίζουν στο πλοίο, που φεύγει μόλις ανέβει ο τελευταίος — ή
; στο μισό sol, όπως ο έμπορος, και παίρνει όσους δεν γύρισαν.
;
;   ΚΥΛΙΚΕΙΟ  ένα τρόφιμο και ένα νερό: COIN_MEAL, και η εύνοια +GOOD_UP. Αν
;             λείπει το ένα, ή δεν φτάνει σε κυλικείο: η εύνοια -GOOD_DOWN, και
;             γυρίζει στο πλοίο.
;   ΣΑΛΟΝΙ    COIN_FUN. Χωρίς σαλόνι που φτάνει, τα δέντρα (EC_AMENITY) τον
;             πληρώνουν εκεί που έφαγε, όπως στο βήμα 134.
;
; Και στα δύο κάθεται VIS_STAY περιστροφές αφού πληρώσει.
;
; ΟΙ ΘΕΣΕΙΣ 112-119 (AG_VIS0), μετά το EC_X: έξω από τις φέτες κίνησης και
; αναγκών. Κινούνται εδώ, με το ent_move_slice, μία φορά ανά περιστροφή, όσο
; είναι προσγειωμένο πλοίο επισκεπτών: αυτή είναι η πύλη τους (ship_tick), και
; χωρίς τέτοιο πλοίο τίποτα από εδώ δεν τρέχει. Ανάγκες δεν έχουν· τον πίνακα
; εργασιών τον κρατά μακριά η εργασία T_VISIT, που ξαναγράφεται σε κάθε
; περιστροφή, όπως το T_FIGHT των εισβολέων.
;
; Η ΦΑΣΗ ΤΟΥΣ στο byte της υγείας (AG_HEALTH), που για αυτούς δεν το διαβάζει
; κανείς: VP_EAT πάει να φάει, VP_FUN στο σαλόνι, VP_HOME στο πλοίο. Το VP_EAT
; είναι το FOE_HP: γεννιούνται με το ag_land των εισβολέων (src/ship.asm), που
; γράφει αυτή την υγεία, και η ρουτίνα δεν θέλει άλλη παράμετρο.
;
; ΖΕΙ ΣΤΗΝ ΤΡΑΠΕΖΑ 6, στο b6code, όπως το src/ship.asm που το καλεί — και ό,τι
; δεν θέλει την 6 (το φαγητό, η πληρωμή, η εύνοια, το δωμάτιο) στην τράπεζα 0,
; στο src/visit0.asm: η 6 δεν είχε τόσα. Η αναφορά είναι το tools/entity.py
; (visit_tick), και το tests/test_sim.py τα συγκρίνει byte προς byte.

VP_EAT      equ FOE_HP
VP_FUN      equ VP_EAT + 1
VP_HOME     equ VP_EAT + 2
; ΚΑΘΟΝΤΑΙ: όσες περιστροφές μένουν στο κυλικείο και στο σαλόνι αφού
; πληρώσουν, ~10 δευτερόλεπτα. Χωρίς αυτό η επίσκεψη στην αποικία δοκιμών
; κρατούσε τέσσερα, και δεν προλάβαινες να τους δεις.
VIS_STAY    equ 32

        assert  AG_VIS0 >= AG_FOE0 + AG_NFOE && AG_VIS0 + AG_NVIS <= N_AGENT
        assert  T_VISIT >= MAX_JOB && T_VISIT != T_FIGHT && T_VISIT != T_NEED
        assert  F_ALIVE == 1 && F_INDOORS == 2 && NO_TASK == 255 && NO_EDGE == 255
        assert  SHIP_LANDED == 2 && SK_VISITOR < 256

; ---------------------------------------------------------------------------
; vi_land — το πλοίο προσγειώθηκε (st_disp): VIS_BASE + κύρος/64 επισκέπτες
; στην πίστα, έξω, στις πρώτες ελεύθερες θέσεις 112-119. Γεννιούνται όπως ο
; άποικος (sb_rest), με εργασία T_VISIT και φάση VP_EAT: στην πρώτη τους
; περιστροφή στέκονται εκεί που «πήγαιναν», και το vi_at τους στέλνει.
; ---------------------------------------------------------------------------
vi_land:
        ld      a,(EC_PREST)
        rlca
        rlca
        and     3                       ; κύρος / 64
        add     a,VIS_BASE
        ld      c,a                     ; C = πόσοι
        ld      hl,G_agent_fields + AG_VIS0
        ld      de,RL_VIS * 256 + T_VISIT
        ld      b,AG_NVIS
        jp      ag_land                 ; src/ship.asm: και η φάση, VP_EAT = FOE_HP

; ---------------------------------------------------------------------------
; vi_tick — μία περιστροφή, όσο είναι προσγειωμένο το πλοίο τους. Κινούνται,
; και όποιος στέκεται εκεί που πήγαινε αποφασίζει (vi_at) — και όποιος βρήκε
; τον δρόμο απρόσιτο, γιατί τότε το ent_move_slice κάνει προορισμό τον κόμβο
; του. Η εργασία ξαναγίνεται T_VISIT: τη σβήνει μια απρόσιτη διαδρομή ή μια
; κατεδάφιση (dm_out), και με NO_TASK ο πίνακας εργασιών θα του έδινε δουλειά.
; Μετρά όσους είναι μέσα (EC_VIN, για το οξυγόνο), και αν δεν έμεινε κανείς το
; πλοίο φεύγει.
; ---------------------------------------------------------------------------
vi_tick:
        ld      bc,AG_NVIS * 256 + AG_VIS0
        call    ent_move_slice          ; src/entity.asm: όπως κάθε πράκτορας
        ld      bc,0                    ; B = ζωντανοί, C = μέσα
        ld      l,AG_VIS0
vit_lp:
        ld      h,AG_PG
        ld      a,(hl)
        rra                             ; F_ALIVE
        jr      nc,vit_nx
        inc     b
        rra                             ; F_INDOORS
        jr      nc,vit_out
        inc     c
vit_out:
        ld      h,AG_TASK >> 8
        ld      (hl),T_VISIT            ; κι αν το έσβησε μια διαδρομή ή μια κατεδάφιση
        dec     h                       ; AG_EDGE
        ld      a,(hl)                  ; η ακμή
        res     3,h                     ; AG_PG + 2
        inc     a
        jr      nz,vit_nx               ; περπατά
        ld      a,(hl)                  ; ο προορισμός
        dec     h                       ; AG_PG + 1
        cp      (hl)                    ; ο κόμβος
        jr      nz,vit_nx
        push    bc
        push    hl
        call    vi_at
        pop     hl
        pop     bc
vit_nx:
        inc     l
        ld      a,l
        cp      AG_VIS0 + AG_NVIS
        jr      c,vit_lp
        ld      a,c
        ld      (EC_VIN),a              ; src/flow.asm: αναπνέουν
        ld      a,b
        or      a
        ret     nz
        ld      h,a
        ld      l,a
        ld      (EC_SHETA),hl           ; ανέβηκαν όλοι: το πλοίο φεύγει τώρα
        ret

; ---------------------------------------------------------------------------
; vi_at — L = ο επισκέπτης: στέκεται εκεί που πήγαινε.
; Χαλάει όλους.
; ---------------------------------------------------------------------------
vi_at:
        ld      h,AG_PG + 3
        ld      a,(hl)                  ; όσο κάθεται ακόμη: η πρόοδος, που όσο
        or      a                       ; στέκεται δεν τη διαβάζει κανείς
        jr      z,via_now
        dec     (hl)
        ret
via_now:
        ld      h,AG_PG + 1
        ld      d,(hl)                  ; D = ο κόμβος του
        ld      h,AG_PG + 6
        ld      a,(hl)                  ; η φάση
        sub     VP_EAT
        jr      z,via_eat
        dec     a
        jr      nz,via_home             ; VP_HOME
        ; --- VP_FUN: στο σαλόνι ---
        ld      e,R_LOUNGE
        call    via_go                  ; src/visit0.asm
        jr      c,via_tree              ; κανένα σαλόνι που φτάνει
        ret     nz                      ; πάει εκεί
        ld      a,COIN_FUN
        push    hl
        call    vi_pay
        pop     hl
; --- πλήρωσε: κάθεται VIS_STAY περιστροφές, και μετά η επόμενη φάση ---
via_stay:
        ld      h,AG_PG + 6
        inc     (hl)                    ; VP_EAT -> VP_FUN -> VP_HOME
        ld      h,AG_PG + 3
        ld      (hl),VIS_STAY
        ret
via_tree:
        ld      a,(EC_AMENITY)          ; δέντρα: πληρώνει εδώ, όπως στο βήμα 134
        or      a
        jr      z,via_home
        ld      a,COIN_FUN
        push    hl
        call    vi_pay
        pop     hl
via_home:
        ld      h,AG_PG + 6
        ld      (hl),VP_HOME
        ld      h,AG_PG + 1             ; ο κόμβος ξανά: το vi_pay χαλά το D
        ld      a,(EC_PADNODE)
        cp      (hl)
        jr      z,via_board
        ld      h,AG_PG + 2
        ld      (hl),a                  ; στο πλοίο
        ret
via_board:
        ld      a,l
        ld      (nd_i),a
        jp      nd_bury                 ; src/needs.asm: ανέβηκε, χωρίς πένθος
via_eat:
        ld      e,R_CANTEEN
        call    via_go
        jr      c,via_hungry            ; κανένα κυλικείο που φτάνει
        ret     nz                      ; πάει εκεί
        push    hl
        call    vi_eat                  ; src/visit0.asm
        pop     hl
        jr      nc,via_stay             ; έφαγε
        jr      via_home                ; τίποτα να φάει
via_hungry:
        call    vi_sad                  ; κρατά τον HL
        jr      via_home

; ---------------------------------------------------------------------------
; vi_gone — A = 0: το πλοίο έφυγε (st_here). Οσοι επισκέπτες δεν γύρισαν
; φεύγουν μαζί του, και κανείς δεν αναπνέει πια.
; ---------------------------------------------------------------------------
vi_gone:
        ld      (EC_VIN),a
        ld      l,AG_VIS0
vig_lp:
        ld      h,AG_PG
        bit     0,(hl)                  ; F_ALIVE
        jr      z,vig_nx
        ld      a,l
        ld      (nd_i),a
        push    hl
        call    nd_bury
        pop     hl
vig_nx:
        inc     l
        ld      a,l
        cp      AG_VIS0 + AG_NVIS
        jr      c,vig_lp
        ret
