; demolish.asm — η κατεδάφιση (βήμα 101, DESIGN §9.3).
;
; Ο ΠΑΙΚΤΗΣ: M, και το D της ΔΙΑΧΕΙΡΙΣΗΣ ανοίγει τη γραμμή του DEMOLISH για
; ό,τι είναι κάτω από τον κέρσορα· FIRE (ή D ξανά) το γκρεμίζει, ESC όχι. Οι
; αποφάσεις του παίκτη:
;
;   θόλοι και δομές, τελειωμένα ή εργοτάξια· ποτέ το σκάφος. Οι διάδρομοι
;   ενός θόλου φεύγουν μαζί του, όπως ήρθαν μαζί του.
;   τα μισά υλικά πίσω, όπως μια μηχανή που βγαίνει στο FIT: του κτιρίου, των
;   διαδρόμων του και των μηχανών του. Ενα εργοτάξιο δεν έχει ξοδέψει τίποτα
;   ακόμη, και δίνει πίσω όλα όσα πληρώθηκαν.
;   αμέσως, με το FIRE.
;   όσοι είναι μέσα βγαίνουν, και ό,τι δουλειά είχε εκεί σταματά.
;
; Στην τράπεζα 2, όπως ό,τι τρέχει μόνο όταν το ζητήσει ο παίκτης.

; ---------------------------------------------------------------------------
; dm_can — CY αν ό,τι είναι κάτω από τον κέρσορα γκρεμίζεται: A = (dm_n) ο
; κόμβος. Ποτέ το σκάφος. Ούτε η πίστα και οι αποθήκες όσο έρχεται ή κάθεται
; πλοίο (EC_SHSTATE): εκεί κατεβαίνουν οι άποικοι, εκεί κουβαλιούνται τα αγαθά
; του εμπόρου. Γυρίζει με την τράπεζα 1.
; ---------------------------------------------------------------------------
dm_can:
        call    mt_cursor               ; src/info.asm
        jr      nc,dmc_out
        ld      (dm_n),a
        inc     hl
        inc     hl
        ld      c,(hl)                  ; D_SIZE / ST_KIND
        inc     hl
        cp      MAX_DOME
        ld      a,c
        jr      nc,dmc_st
        ld      a,(hl)                  ; D_ROOM
        cp      R_STORAGE
        jr      dmc_ship
dmc_st:
        cp      K_SHIP
        jr      z,dmc_out               ; NC
        cp      K_PAD
dmc_ship:
        scf
        jr      nz,dmc_out              ; CY: γκρεμίζεται
        ld      a,(EC_SHSTATE)
        cp      1                       ; CY αν δεν έρχεται κανένα πλοίο
dmc_out:
        ld      a,(dm_n)
        jp      dt_end                  ; η 1 πίσω· κρατά AF

; ---------------------------------------------------------------------------
; dm_go — FIRE στη γραμμή του DEMOLISH (src/act.asm).
; ---------------------------------------------------------------------------
dm_go:
        call    dm_can                  ; ξανά: ένα πλοίο μπορεί να ήρθε
        jp      nc,uip_deny
        call    ui_hide                 ; το GH_BUF αδειάζει: εκεί τρέχει το dm_do
        call    ov_run
        ld      a,SFX_BUILD
        call    snd_play
        xor     a                       ; UI_LOOK
        jp      ui_goto_h

; ---------------------------------------------------------------------------
; ΚΩΔΙΚΑΣ ΠΟΥ ΔΕΝ ΜΕΝΕΙ ΣΤΗ ΜΝΗΜΗ (βήμα 101). Οι πίνακες της δρομολόγησης έχουν
; γραμμές των 128 bytes για 96 κόμβους (graph.asm): οι στήλες 96-127 κάθε
; γραμμής του DIST, 32 bytes x 96 γραμμές, δεν τις διαβάζει ούτε τις γράφει
; κανείς από το βήμα 101 (το rt_flush γράφει 96). Εκεί ζει, σε κομμάτια των 32,
; κώδικας που τρέχει σπάνια και πάντα με το φάντασμα κρυμμένο — τότε το GH_BUF
; της τράπεζας 2, που φαίνεται πάντα, είναι άδειο. Το ov_run τον φέρνει εκεί
; και τον τρέχει. Στον δίσκο και στο snapshot ο κώδικας έρχεται στο OV_LOAD,
; κάτω από τα εικονίδια της τράπεζας 1 (βήμα 102, src/main.asm· ως το 101 στο
; ίδιο το GH_BUF), και το ov_install τον μοιράζει στις τρύπες στην εκκίνηση.
; Η σειρά 0 τρέχει και εκεί που είναι: δύο χειριστές της λίστας αλλαγών
; (src/dm_ovl.asm), με την 1 μέσα.
; ---------------------------------------------------------------------------
OV_HOLE     equ #4000 + RT_NODES        ; η τρύπα της γραμμής 0, στην τράπεζα 1
OV_ROWS     equ (zz_ovl_end - GH_BUF + 31) >> 5
OV2_ROWS    equ (zz_ov2_end - SV_ORG + 31) >> 5     ; το σώσιμο, μετά (βήμα 103)
OV2_HOLE    equ OV_HOLE + OV_ROWS * 128
OV3_ROWS    equ (zz_ov3_end - GH_BUF + 31) >> 5     ; η βοήθεια (βήμα 108)
OV3_HOLE    equ OV2_HOLE + OV2_ROWS * 128
        assert  OV_ROWS + OV2_ROWS + OV3_ROWS <= RT_NODES && RT_NODES + 32 == 128
        assert  OV1_PAD == OV_ROWS * 32 && OV2_PAD == OV2_ROWS * 32
        ; το ov_install δεν σβήνει ό,τι θα διαβάσει
        assert  #4000 + (OV_ROWS + OV2_ROWS + OV3_ROWS) * 128 <= OV_LOAD

; ov_run — ο κώδικας από τις τρύπες στο GH_BUF, και κλήση του. Το φάντασμα
; κρυμμένο (ui_hide). Χαλάει τα πάντα· γυρίζει με ό,τι αφήσει ο κώδικας.
ov_run:
        ld      hl,OV_HOLE
        ld      de,GH_BUF
        ld      a,OV_ROWS
        call    ov_copy
        jp      dm_do                   ; μετά τη σειρά 0 (src/dm_ovl.asm)

; ---------------------------------------------------------------------------
; sv_save / sv_load — A = slot. ΤΟ ΣΩΣΙΜΟ ΖΕΙ ΣΤΙΣ ΤΡΥΠΕΣ από το βήμα 103,
; μετά την κατεδάφιση (src/main.asm): το src/save.asm και ο οδηγός του δίσκου,
; 633 bytes που ως τότε ήταν στην τράπεζα 2. Τρέχει στο SV_ORG, μετά τα 512
; της κεφαλίδας του (SV_HDR) — ο κέρσορας είναι σβηστός σε κάθε S και L
; (ui_dosave, ui_doload), άρα το GH_BUF είναι άδειο. Οι δύο είσοδοι μένουν
; εδώ, με τα ονόματα που καλεί το src/ui.asm, και φέρνουν τον κώδικα κάθε
; φορά. Το φόρτωμα δείχνει τον κέρσορα ΕΔΩ, αφού γυρίσει: το αρχείο του
; φαντάσματος γράφεται στο GH_BUF, κάτω από τον κώδικα που θα έτρεχε ακόμη.
; ---------------------------------------------------------------------------
sv_save:
        call    sv_ovl
        jp      svo_save
sv_load:
        call    sv_ovl
        call    svo_load
        ret     nz
        call    ui_show
        xor     a
        ret
sv_ovl:
        push    af
        ld      hl,OV2_HOLE
        ld      de,SV_ORG
        ld      a,OV2_ROWS
        call    ov_copy
        pop     af
        ret

; ov_copy — A γραμμές των 32 bytes από τις τρύπες (HL, τράπεζα 1) στο DE.
; Γυρίζει με την 1.
ov_copy:
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
ovr_lp:
        ld      bc,32
        ldir
        ld      bc,128 - 32
        add     hl,bc
        dec     a
        jr      nz,ovr_lp
        ret

; ov_install — στην εκκίνηση: ό,τι έφερε ο φορτωτής στο OV_LOAD, στις τρύπες,
; και τα τρία κομμάτια (η βοήθεια από το βήμα 108). Και τα δύο, εικόνα και
; τρύπες, στην τράπεζα 1, και δεν επικαλύπτονται: το OV_LOAD είναι στις
; γραμμές 80-95 του DIST, οι τρύπες που γεμίζουν στις πρώτες (assert).
ov_install:
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        ld      hl,OV_LOAD
        ld      de,OV_HOLE
        ld      a,OV_ROWS + OV2_ROWS + OV3_ROWS
ovi_lp:
        ld      bc,32
        ldir
        ex      de,hl
        ld      bc,128 - 32
        add     hl,bc
        ex      de,hl
        dec     a
        jr      nz,ovi_lp
        ret

; ---------------------------------------------------------------------------
; ΟΣΑ ΑΦΗΝΕ ΠΙΣΩ ΤΗΣ Η ΚΑΤΕΔΑΦΙΣΗ (βήμα 116, DESIGN §9.3). Εδώ και όχι στο
; overlay (src/dm_ovl.asm), που έχει 25 bytes: από εκεί τρεις κλήσεις.
; ---------------------------------------------------------------------------

; dm_sites — ΕΝΑ ΕΡΓΟΤΑΞΙΟ ΘΟΛΟΥ ΧΩΡΙΣ ΑΚΜΗ. Η μόνη ακμή ενός θόλου που χτίζεται
; είναι η σύνδεση εδάφους του ως το κοντινότερο airlock ή το σκάφος (lk_ground):
; οι διάδρομοί του γίνονται ακμές όταν τελειώσει. Γκρεμίστηκε εκείνο το airlock,
; και κανείς δεν τον έφτανε πια για να τον χτίσει. Παίρνει σύνδεση εδάφους
; ξανά, όπως στην τοποθέτηση, από το κέντρο του (το lk_anchor ψάχνει από τον
; κέρσορα, που μένει όπως ήταν). Τίποτα δεν κρέμεται από εργοτάξιο θόλου, άρα
; κανένας κύκλος. Μετά το dm_relink, με το εργοτάξιο που γκρεμίστηκε ήδη άδειο.
; Γυρίζει με την 1, όπως το dm_relink πριν από αυτό.
dm_sites:
        call    asc_b6
        ld      ix,G_dome_tbl
        ld      c,0                     ; ο θόλος
dms_lp:
        ld      a,(ix+D_STATE)
        dec     a                       ; DS_BUILDING
        jr      nz,dms_nx
        ld      l,c
        ld      h,NODEPG
        or      (hl)                    ; ο βαθμός του
        jr      nz,dms_nx
        push    bc
        push    ix
        ld      hl,(cur_hx)             ; cur_hx, cur_hy διπλανά
        push    hl
        ld      l,(ix+D_CX)
        ld      h,(ix+D_CY)
        ld      (cur_hx),hl
        ld      b,c
        call    lk_ground               ; src/link.asm· γυρίζει με την 1
        pop     hl
        ld      (cur_hx),hl
        call    asc_b6
        pop     ix
        pop     bc
dms_nx:
        ld      de,DOME_REC
        add     ix,de
        inc     c
        bit     6,c                     ; MAX_DOME
        jr      z,dms_lp
        jp      asc_b1

; dm_up — A = ο γονιός του γκρεμισμένου (dm_par, 255 κανένας) -> CY και A = από
; πού κρέμονται τα ορφανά του· NC (A = 255) από πουθενά. Ο ίδιος αν έχει θέση για ακμή·
; αλλιώς ο δικός του γονιός (LK_OWN), και πάει λέγοντας: ένας πρόγονος του
; γκρεμισμένου δεν κρέμεται από ορφανό του, άρα κανένας κύκλος. Χωρίς γονιό (ένα
; σώσιμο πριν από το βήμα 102), το σκάφος, η ρίζα όλων — αν η δομή 0 είναι
; σκάφος· στην αποικία δοκιμών δεν είναι. Ως το 115 και τα δύο έμεναν χωρίς
; σύνδεση. Το πολύ MAX_STRUCT βήματα, κι ας έλεγε ψέματα ένα LK_OWN. Χαλάει
; B, HL. Τράπεζα 1 μέσα και έξω.
dm_up:
        ld      b,MAX_STRUCT
        cp      255
        jr      nz,dmu_lp
        call    asc_b6
        ld      a,(G_struct_tbl + ST_KIND)
        call    asc_b1
        cp      K_SHIP
        ld      a,MAX_DOME              ; το σκάφος, η δομή 0
        jr      z,dmu_lp
        jr      dmu_no
dmu_lp:
        ld      l,a
        ld      h,NODEPG
        ld      a,(hl)                  ; ο βαθμός του
        cp      MAX_DEGREE
        ld      a,l
        ret     c                       ; έχει θέση: CY
        set     5,l                     ; LK_OWN + δομή
        ld      a,(hl)
        and     #FF - #80 - LKO_GROUND  ; ο γονιός του, 0 κανένας
        jr      z,dmu_no
        djnz    dmu_lp
dmu_no:
        ld      a,255
        or      a                       ; NC: το cp K_SHIP μπορεί να το άφησε
        ret

; dm_haul — HL -> J_KIND μιας εργασίας, από το dmj_lp του dm_do. ΜΙΑ HAUL ΜΕ ΤΟ
; ΦΟΡΤΙΟ ΤΗΣ (J_NODE ≠ J_SITE: φορτώθηκε, ή αφέθηκε στη μέση, src/haul.asm) της
; οποίας ο προορισμός ή το ορυχείο γκρεμίζεται, το παραδίδει στα αποθέματα,
; όπως ένα φορτίο που δεν έχει πού να πάει (hla_drop). Ως το 115 χανόταν:
; τα 10 μεταλλεύματα είχαν ήδη φύγει από τον σωρό. Κρατά BC, DE, HL.
dm_haul:
        ld      a,(hl)
        cp      J_HAUL
        ret     nz
        push    hl
        push    de
        push    bc
        inc     hl
        ld      a,(dm_n)
        ld      b,a
        ld      c,(hl)                  ; J_NODE
        inc     hl
        inc     hl
        inc     hl
        ld      a,(hl)                  ; J_SITE
        cp      c
        jr      z,dmh_out               ; στο ορυχείο ακόμη: άδεια χέρια
        cp      b
        jr      z,dmh_go                ; το ορυχείο γκρεμίζεται
        ld      a,c
        cp      b
        jr      nz,dmh_out              ; ούτε ο προορισμός
dmh_go:
        ld      a,S_ORE
        ld      de,HAUL_LOAD
        call    ec_make                 ; src/stock.asm
dmh_out:
        pop     bc
        pop     de
        pop     hl
        ret

        assert  J_NODE == 1 && J_SITE == 4 && DS_BUILDING == 1 && MAX_DOME == 64
        assert  D_CY == D_CX + 1 && ST_KIND == 2

dm_n:       db 0
