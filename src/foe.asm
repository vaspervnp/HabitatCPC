; foe.asm — οι εισβολείς (βήμα 111, DESIGN §6.10)
;
; ΟΠΩΣ ΣΤΟ PLANETBASE, με τις αποφάσεις του παίκτη:
;
;   - ΜΕ ΔΙΚΟ ΤΟΥΣ ΠΛΟΙΟ. Μετράνε όλες οι προσγειώσεις (EC_LANDS, src/ship.asm),
;     και όταν συμπληρωθούν FOE_EVERY το επόμενο απρόσκλητο πλοίο είναι των
;     εισβολέων (ev_ship, src/econ.asm) — ποτέ το πλοίο αποίκων που καλείς, και
;     ποτέ με λιγότερους από FOE_POP αποίκους. Δύο με 20-39, τρεις με 40-59,
;     τέσσερις με 60 και πάνω (fo_land).
;   - ΧΤΥΠΟΥΝ ΟΠΟΙΟΝ ΒΡΟΥΝ ΜΠΡΟΣΤΑ ΤΟΥΣ: κάθε εισβολέας που στέκεται σε κόμβο
;     χτυπά, μία φορά ανά περιστροφή, τον πρώτο άποικο που στέκεται εκεί, και
;     μένει. Οταν δεν βρίσκει κανέναν και έφτασε εκεί που πήγαινε, πάει όπου
;     στέκεται ο επόμενος άποικος (fo_pk) — έτσι μπαίνουν από το airlock και
;     γυρίζουν τη βάση.
;   - ΟΙ ΦΡΟΥΡΟΙ ΤΟΥΣ ΑΝΤΙΜΕΤΩΠΙΖΟΥΝ: με τον συναγερμό όλοι αφήνουν ό,τι
;     έκαναν (T_FIGHT· όχι όποιος πάει για ανάγκη), παίρνουν ένα Gun από το
;     απόθεμα αν δεν έχουν και υπάρχει, και το κρατούν για πάντα (F_GUN). Με τα
;     χέρια χτυπούν όποιον στέκεται στον κόμβο τους, με όπλο και όποιον είναι
;     στον κόμβο τους ή σε γειτονικό. Αλλιώς πάνε στον εισβολέα τους, κατά σειρά.
;
; ΟΙ ΘΕΣΕΙΣ 96-99 (AG_FOE0), που δεν είχαν κανέναν: έξω από τις φέτες κίνησης
; και αναγκών (0-95). Κινούνται εδώ, με το ίδιο ent_move_slice, μία φορά ανά
; περιστροφή όπως όλοι. Ανάγκες δεν έχουν· τον πίνακα εργασιών τον κρατά μακριά
; η εργασία T_FIGHT, που δεν είναι δείκτης εργασίας (όπως το T_NEED).
;
; ΖΕΙ ΣΤΗΝ ΤΡΑΠΕΖΑ 6, στο b6code: το καλεί μόνο η θέση 15, που την έχει στο
; παράθυρο. Το fo_n (src/stock.asm) είναι στην τράπεζα 0: το διαβάζει και το HUD.
; Χωρίς εισβολείς η θέση πληρώνει ένα byte και ένα άλμα. Η αναφορά είναι το
; tools/entity.py (foe_tick), και το tests/test_sim.py τα συγκρίνει byte προς
; byte.

FOE_HP      equ 160                     ; η υγεία του όταν κατεβαίνει
FOE_HIT     equ 32                      ; ό,τι παίρνει από έναν άποικο
HAND_HIT    equ 32                      ; ό,τι του παίρνει ένας φρουρός με τα χέρια
GUN_HIT     equ 64                      ; ...και με όπλο: τρεις βολές

        assert  AG_FOE0 + AG_NFOE <= N_AGENT && AG_FOE0 >= AG_BOT0 + AG_NBOT
        assert  F_ALIVE == 1 && F_GUN == 128 && NO_EDGE == 255
        assert  T_FIGHT != T_NEED && T_FIGHT >= MAX_JOB
        assert  (G_agent_fields & 255) == 0

; ΕΝΑΣ ΧΑΡΤΗΣ ΚΟΜΒΩΝ ΤΟΥ ΑΠΟΜΕΝΕΙ ΜΗΔΕΝ. Η πρώτη γραφή ρωτούσε για κάθε άποικο
; τέσσερα cp και για κάθε φρουρό τέσσερις γειτονιές με cpir: 9,4 ms η θέση 15,
; πάνω από τη θέση 14 (4,7). Τώρα ο εισβολέας k γράφει το bit του, μία φορά ανά
; περιστροφή, στο FO_MAP[κόμβος όπου στέκεται] και στο FO_MAP + 128 [κόμβος όπου
; είναι, και κάθε γειτονικός]· ο άποικος ρωτά ένα byte, ο φρουρός δύο. Στο τέλος
; τα ίδια bytes ξαναγίνονται μηδέν. Η σελίδα κάτω από τους πράκτορες, στην κορυφή
; της δέσμευσης b6code (το src/main.asm ελέγχει ότι ο κώδικας δεν φτάνει ως
; εκεί)· στο tests/simtest.asm είναι η ίδια διεύθυνση της τράπεζας 6.
FO_MAP      equ G_agent_fields - 256

; ---------------------------------------------------------------------------
; fo_tick — μία περιστροφή. Το bot_tick πηδά εδώ, και αυτό στο ship_tick.
; ---------------------------------------------------------------------------
fo_tick:
        ld      a,(fo_n)
        or      a
        jp      z,ship_tick             ; κανένας εισβολέας
        call    fo_count
        jp      z,fo_over               ; το #80 μιας φόρτωσης, ή έπεσε ο τελευταίος
        ld      bc,AG_NFOE * 256 + AG_FOE0
        call    ent_move_slice          ; src/entity.asm: όπως κάθε πράκτορας

        ; --- ποιος στέκεται πού (fn), ποιος είναι πού (an), ποιοι ζουν (tg, και
        ; οι μάσκες fo_live, fo_ch: όσοι στέκονται και δεν χτύπησαν ακόμη), και ο
        ; χάρτης ---
        ld      hl,fo_fn
        ld      b,8                     ; fn, an: 255
foz_lp: ld      (hl),255
        inc     hl
        djnz    foz_lp
        xor     a
        ld      (fo_live),a
        ld      (fo_ch),a
        ld      ix,fo_fn
        ld      de,fo_tgb
        ld      bc,1 * 256 + AG_FOE0    ; B = το bit του k, C = ο εισβολέας
foi_lp:
        ld      l,c
        ld      h,AG_PG
        bit     0,(hl)                  ; F_ALIVE
        jr      z,foi_n
        ld      a,b
        ld      (de),a                  ; tgb: το bit του
        ld      a,(fo_live)
        or      b
        ld      (fo_live),a
        inc     h                       ; AG_PG + 1
        ld      a,(hl)                  ; ο κόμβος του
        ld      (ix+4),a                ; an
        inc     e
        inc     e
        inc     e
        inc     e
        ld      (de),a                  ; tgn: ο κόμβος του
        dec     e
        dec     e
        dec     e
        push    bc
        push    de
        push    hl
        call    fo_zone                 ; FO_MAP + 128: εκεί και δίπλα
        pop     hl
        pop     de
        pop     bc
        ld      a,(ix+4)
        inc     h                       ; AG_PG + 2
        set     7,l
        ld      l,(hl)                  ; η ακμή
        inc     l
        jr      nz,foi_n                ; περπατά
        ld      (ix+0),a                ; fn
        ld      l,a
        ld      h,FO_MAP >> 8
        ld      a,(hl)
        or      b
        ld      (hl),a                  ; FO_MAP: στέκεται εδώ
        ld      a,(fo_ch)
        or      b
        ld      (fo_ch),a
foi_n:
        inc     ix
        inc     c
        sla     b
        ld      a,b
        cp      1 << AG_NFOE
        jr      c,foi_lp
        ; ΟΙ ΣΤΟΧΟΙ ΤΩΝ ΦΡΟΥΡΩΝ: ο φρουρός με αριθμό g (με τη σειρά τους σε
        ; αυτή την περιστροφή) πάει στον κόμβο fo_ts[g & 3], δηλαδή στον
        ; (g & 3) mod nt ζωντανό. Τέσσερα bytes εδώ αντί για mod σε κάθε φρουρό.
        ld      a,e
        sub     fo_tgb & 255
        ld      c,a                     ; C = nt, 1-4
        ld      hl,fo_tgn
        ld      de,fo_ts
        ld      b,AG_NFOE
fots_lp:
        ld      a,(hl)
        ld      (de),a
        inc     e
        inc     l
        ld      a,l
        sub     fo_tgn & 255
        cp      c
        jr      c,fots_n
        ld      l,fo_tgn & 255          ; ξανά από τον πρώτο
fots_n:
        djnz    fots_lp
        xor     a
        ld      (fo_gi),a

        ; --- ΠΡΩΤΑ ΧΤΥΠΟΥΝ ΟΙ ΕΙΣΒΟΛΕΙΣ: οι άποικοι 0-79 με τη σειρά, και ένα
        ; byte του χάρτη λέει αν στον κόμβο του καθενός στέκεται εισβολέας που
        ; δεν χτύπησε ακόμη. Οταν χτυπήσουν όλοι, τέλος. ---
        ld      a,(fo_ch)
        or      a
        jr      z,fov_end               ; κανείς δεν στέκεται
        ld      c,a                     ; C = fo_ch
        ld      d,FO_MAP >> 8
        ld      hl,AG_PG * 256          ; L = ο άποικος
        ld      b,AG_BOT0
fov_lp:
        inc     h                       ; AG_PG + 1
        ld      e,(hl)                  ; ο κόμβος του
        dec     h
        ld      a,(hl)                  ; σημαίες
        rra                             ; F_ALIVE
        jr      nc,fov_nx
        ld      a,(de)
        and     c
        jr      nz,fov_v                ; κάποιος εκεί μπορεί να τον χτυπήσει
fov_nx:
        inc     l
        djnz    fov_lp
        jr      fov_end
; --- στον κόμβο του στέκονται εισβολείς που δεν χτύπησαν: αν στέκεται κι
; αυτός, ο πρώτος τον χτυπά ---
fov_v:
        ld      h,AG_PG + 2
        set     7,l
        ld      a,(hl)                  ; η ακμή
        res     7,l
        ld      h,AG_PG
        inc     a
        jr      nz,fov_nx               ; περπατά: κανείς δεν τον χτυπά
        ld      a,(de)
        and     c
fov_h:
        ld      h,a
        neg
        and     h                       ; ο πρώτος: το κάτω bit
        cpl
        and     c
        ld      c,a                     ; δεν χτυπά ξανά
        ld      h,AG_PG + 6
        ld      a,(hl)                  ; η υγεία του
        sub     FOE_HIT
        jr      nc,fovh_st
        xor     a
fovh_st:
        ld      (hl),a
        ld      h,AG_PG
        jr      z,fov_die
        ld      a,(de)                  ; ζει: μήπως στέκεται κι άλλος εκεί
        and     c
        jr      nz,fov_h
fov_more:
        inc     c
        dec     c
        jr      nz,fov_nx               ; χτύπησαν όλοι: τέλος
        jr      fov_end
fov_die:
        ld      a,l
        ld      (nd_i),a
        push    bc
        push    de
        push    hl
        call    nd_die                  ; src/needs.asm: θέση, δουλειά, πένθος
        pop     hl
        pop     de
        pop     bc
        jr      fov_more
fov_end:
        ld      a,c
        ld      (fo_ch),a

        ; --- ΜΕΤΑ ΑΠΑΝΤΟΥΝ ΟΙ ΦΡΟΥΡΟΙ, με τη σειρά τους: cpir στη στήλη των
        ; ρόλων 0-79 ---
        ld      hl,AG_PG * 256 + 128
        ld      bc,AG_BOT0
fog_lp:
        ld      a,RL_GUARD
        cpir
        jr      nz,fo_after             ; κανένας άλλος
        push    bc
        push    hl
        dec     l
        call    fo_guard
        pop     hl
        pop     bc
        ld      a,b
        or      c
        jr      nz,fog_lp

; --- οι εισβολείς: T_FIGHT ξανά (μια απρόσιτη διαδρομή το σβήνει), και όποιος
; στέκεται: αν χτύπησε μένει, αν έφτασε ψάχνει τον επόμενο. Και ο χάρτης
; ξαναγίνεται μηδέν. ---
fo_after:
        ld      ix,fo_fn
        ld      bc,1 * 256 + AG_FOE0    ; B = το bit, C = ο εισβολέας
foa_lp:
        ld      a,(ix+4)                ; an
        cp      255
        jr      z,foa_n                 ; δεν ζούσε
        push    bc
        call    fo_unzone
        pop     bc
        ld      a,(ix+0)                ; fn
        ld      l,a
        ld      h,FO_MAP >> 8
        ld      (hl),0                  ; (ένα 255 πέφτει στο FO_MAP + 255, που μηδενίζεται κι αυτό)
        ld      a,(fo_live)
        and     b
        jr      z,foa_n                 ; έπεσε
        ld      l,c
        ld      h,AG_PG + 3
        set     7,l
        ld      (hl),T_FIGHT
        res     7,l
        ld      a,(ix+0)
        inc     a
        jr      z,foa_n                 ; περπατά
        ld      h,AG_PG + 1
        ld      a,(hl)                  ; ο κόμβος του
        inc     h                       ; AG_PG + 2
        ld      e,a
        ld      a,(fo_ch)
        and     b
        ld      a,e
        jr      nz,foa_look             ; δεν χτύπησε
        ld      (hl),a                  ; χτύπησε: μένει
        jr      foa_n
foa_look:
        cp      (hl)
        jr      nz,foa_n                ; δεν έφτασε ακόμη
        ld      d,a                     ; D = ο κόμβος του
        push    bc
        ld      a,(fo_pk)
        ld      e,a
        ld      b,AG_BOT0
fos_lp:
        inc     e                       ; ο επόμενος άποικος, κυκλικά
        ld      a,e
        cp      AG_BOT0
        jr      c,fos_e
        ld      e,0
fos_e:
        ld      l,e
        ld      h,AG_PG
        bit     0,(hl)                  ; F_ALIVE
        jr      z,fos_nx
        ld      h,AG_PG + 2
        set     7,l
        ld      a,(hl)                  ; η ακμή
        res     7,l
        inc     a
        jr      nz,fos_nx               ; περπατά
        dec     h                       ; AG_PG + 1
        ld      a,(hl)
        cp      d
        jr      nz,fos_go               ; στέκεται αλλού: εκεί πάει
fos_nx:
        djnz    fos_lp
        pop     bc
        jr      foa_n
fos_go:
        ld      l,a
        ld      a,e
        ld      (fo_pk),a
        ld      a,l
        pop     bc
        ld      l,c
        ld      h,AG_PG + 2
        ld      (hl),a                  ; ο προορισμός του
foa_n:
        inc     ix
        inc     c
        sla     b
        ld      a,b
        cp      1 << AG_NFOE
        jr      c,foa_lp
        call    fo_count
        jr      z,fo_over
        ld      (fo_n),a
        jp      ship_tick

; --- κανένας εισβολέας: όποιος φρουρός ήταν στη μάχη γίνεται διαθέσιμος ---
fo_over:
        xor     a
        ld      (fo_n),a
        ld      hl,(AG_PG + 3) * 256 + 128      ; οι εργασίες, 0-79
        ld      b,AG_BOT0
foo_lp:
        ld      a,(hl)
        cp      T_FIGHT
        jr      nz,foo_n
        ld      (hl),NO_TASK
foo_n:
        inc     l
        djnz    foo_lp
        jp      ship_tick

; fo_count — A = πόσοι εισβολείς ζουν, Z αν κανείς. Χαλάει BC, HL.
fo_count:
        ld      hl,G_agent_fields + AG_FOE0
        ld      bc,AG_NFOE * 256
fot_lp:
        ld      a,(hl)
        and     F_ALIVE
        add     a,c
        ld      c,a
        inc     l
        djnz    fot_lp
        or      a
        ret

; fo_zone — A = κόμβος, B = το bit ενός εισβολέα: FO_MAP + 128 στον κόμβο και
; σε κάθε γειτονικό (node_adj, όσοι λέει το deg). fo_unzone — το ίδιο, μηδέν.
; Χαλάει A, C, DE, HL.
fo_zone:
        ld      e,a
        ld      d,FO_MAP >> 8
        set     7,e
        ld      a,(de)
        or      b
        ld      (de),a
        res     7,e
        ld      l,e
        ld      h,NODEPG
        ld      c,(hl)                  ; deg
        inc     c
        dec     c
        ret     z
        ld      a,l
        add     a,(G_node_adj >> 3) & 255
        ld      l,a
        ld      h,G_node_adj >> 11
        add     hl,hl
        add     hl,hl
        add     hl,hl
foz_n:
        ld      e,(hl)                  ; ένας γείτονας
        set     7,e
        ld      a,(de)
        or      b
        ld      (de),a
        inc     l
        dec     c
        jr      nz,foz_n
        ret
fo_unzone:
        ld      e,a
        ld      d,FO_MAP >> 8
        set     7,e
        xor     a
        ld      (de),a
        res     7,e
        ld      l,e
        ld      h,NODEPG
        ld      c,(hl)
        inc     c
        dec     c
        ret     z
        ld      a,l
        add     a,(G_node_adj >> 3) & 255
        ld      l,a
        ld      h,G_node_adj >> 11
        add     hl,hl
        add     hl,hl
        add     hl,hl
fou_n:
        ld      e,(hl)
        set     7,e
        xor     a
        ld      (de),a
        inc     l
        dec     c
        jr      nz,fou_n
        ret

; ---------------------------------------------------------------------------
; fo_guard — L = ο φρουρός (το bit 7 δεν μετρά). Αν ζει και δεν πάει για ανάγκη.
; Χαλάει όλους.
; ---------------------------------------------------------------------------
fo_guard:
        res     7,l
        ld      h,AG_PG
        bit     0,(hl)                  ; F_ALIVE
        ret     z
        ld      h,AG_PG + 3
        set     7,l
        ld      a,(hl)                  ; η εργασία του
        cp      T_NEED
        ret     z                       ; πάει για ανάγκη: εκείνη πρώτα
        ld      (hl),T_FIGHT
        res     7,l
        ; --- ένα όπλο, αν δεν έχει και υπάρχει, για πάντα ---
        ld      h,AG_PG
        bit     7,(hl)                  ; F_GUN
        jr      nz,fog_tgt
        ld      bc,(EC_STOCK + 2 * S_GUN)
        ld      a,b
        or      c
        jr      z,fog_tgt
        dec     bc
        ld      (EC_STOCK + 2 * S_GUN),bc
        set     7,(hl)
fog_tgt:
        ; --- ο στόχος του: fo_ts[gi & 3], και gi + 1 ---
        ld      a,(fo_gi)
        inc     a
        ld      (fo_gi),a
        dec     a
        and     3
        add     a,fo_ts & 255
        ld      e,a
        ld      d,fo_ts >> 8
        ld      a,(de)
        ld      (fo_tt),a               ; ο κόμβος του
        ; --- στέκεται; τότε χτυπά όποιον φτάνει ---
        ld      h,AG_PG + 2
        set     7,l
        ld      a,(hl)                  ; η ακμή
        res     7,l
        inc     a
        jr      nz,fog_go               ; περπατά: προς τον στόχο
        dec     h                       ; AG_PG + 1
        ld      e,(hl)                  ; ο κόμβος του
        ld      d,FO_MAP >> 8
        ld      a,(de)                  ; όσοι στέκονται εδώ: με τα χέρια
        ld      c,a
        ld      h,AG_PG
        bit     7,(hl)                  ; F_GUN
        ld      b,HAND_HIT
        jr      z,fog_r
        set     7,e
        ld      a,(de)                  ; ...και με όπλο, εδώ και δίπλα
        or      c
        ld      c,a
        ld      b,GUN_HIT
fog_r:
        ld      a,(fo_live)
        and     c
        jr      nz,fog_hit
fog_go:
        ld      a,(fo_tt)
        ld      h,AG_PG + 2
        ld      (hl),a                  ; προς τον κόμβο του
        ret

; --- ο φρουρός L χτυπά τον πρώτο της μάσκας A, με B, και μένει ---
fog_hit:
        ld      c,a
        neg
        and     c                       ; το κάτω bit
        ld      c,a                     ; C = το bit του
        ld      e,AG_FOE0 - 1
fogh_k: inc     e
        rra
        jr      nc,fogh_k               ; E = ο εισβολέας
        ld      h,AG_PG + 1
        ld      a,(hl)
        ld      h,AG_PG + 2
        ld      (hl),a                  ; μένει εκεί που είναι
        ld      l,e
        ld      h,AG_PG + 6             ; η υγεία του εισβολέα
        ld      a,(hl)
        sub     b
        jr      nc,fogh_st
        xor     a
fogh_st:
        ld      (hl),a
        ret     nz

; fo_down — L = ο εισβολέας, C = το bit του: πέφτει. Ο θάνατος χωρίς πένθος
; (nd_bury), και το bit του φεύγει από το fo_live και το fo_ch.
fo_down:
        push    bc
        ld      a,l
        ld      (nd_i),a
        ld      a,SFX_DEATH
        call    snd_ping                ; δεν χαλάει καταχωρητές (§9.5)
        call    nd_bury                 ; src/needs.asm
        pop     bc
        ld      a,c
        cpl
        ld      c,a
        ld      a,(fo_live)
        and     c
        ld      (fo_live),a
        ld      a,(fo_ch)
        and     c
        ld      (fo_ch),a
        ret

; ---------------------------------------------------------------------------
; fo_land — το πλοίο των εισβολέων προσγειώθηκε (st_here, src/ship.asm): το
; μέτρημα των προσγειώσεων από την αρχή, και 2-4 εισβολείς στην πίστα, έξω,
; στις πρώτες ελεύθερες από τις θέσεις 96-99. Γεννιούνται όπως ο άποικος
; (sb_rest), με εργασία T_FIGHT και υγεία FOE_HP.
; ---------------------------------------------------------------------------
fo_land:
        xor     a
        ld      (EC_LANDS),a
        ld      a,SFX_ALERT
        call    snd_ping
        ld      a,(EC_ALIVE)
        ld      c,2
        cp      40
        jr      c,fol_40
        inc     c
fol_40:  cp      60
        jr      c,fol_60
        inc     c                       ; C = πόσοι
fol_60:
        ld      hl,G_agent_fields + AG_FOE0
        ld      de,RL_FOE * 256 + T_FIGHT
        ld      b,AG_NFOE
        call    ag_land                 ; src/ship.asm (βήμα 136: κοινό με τους επισκέπτες)
fol_end:
        ld      a,#80                   ; ο τροχός τους μετρά στην επόμενη περιστροφή
        ld      (fo_n),a
        ret

; --- μνήμη: fn, an, tgb, tgn διαδοχικά και σε μία σελίδα (ld e,a). Οι
; σκαλωσιές των δοκιμών τα βάζουν αλλού (tests/simtest.asm): όποια διάταξη κι
; αν βγει, τα 16 πάνε στην επόμενη σελίδα αν δεν χωρούν σε αυτή. ---
        if      ($ & 255) > 256 - 20
        defs    256 - ($ & 255)
        endif
fo_fn:      ds 4                        ; όπου στέκεται στην αρχή της περιστροφής, ή 255
fo_an:      ds 4                        ; όπου είναι (κι αν περπατά), ή 255
fo_tgb:     ds 4                        ; οι ζωντανοί, με τη σειρά: το bit τους
fo_tgn:     ds 4                        ; ...και ο κόμβος τους
fo_ts:      ds 4                        ; ο στόχος του φρουρού g: fo_tgn[(g & 3) mod nt]
fo_live:    db 0                        ; μάσκα: όσοι ζουν ακόμη
fo_ch:      db 0                        ; μάσκα: όσοι στέκονται και δεν χτύπησαν
fo_gi:      db 0                        ; ο επόμενος στόχος φρουρού
fo_pk:      db 0                        ; ο τελευταίος άποικος που έγινε στόχος
fo_tt:      db 0
        assert  fo_an == fo_fn + 4 && fo_tgb == fo_an + 4 && fo_tgn == fo_tgb + 4
        assert  fo_ts == fo_tgn + 4 && (fo_fn >> 8) == ((fo_ts + 3) >> 8)
        assert  (FO_MAP & 255) == 0 && AG_NFOE == 4
