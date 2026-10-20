; link.asm — πώς ένα νέο κτίσμα δένεται με την αποικία (DESIGN §9.3, βήμα 85).
;
; Ο ΚΑΝΟΝΑΣ ΕΙΝΑΙ ΤΟΥ ΠΑΙΚΤΗ, όπως τον ζήτησε:
;
;   * Το ΠΡΩΤΟ κτίσμα του κόσμου μπαίνει όπου το επιτρέπει το έδαφος.
;   * Κάθε επόμενο θέλει κάποιο κτίσμα ως AL_RANGE = 12 tiles μακριά, και
;     δένεται μαζί του τη στιγμή που τοποθετείται:
;       - ένας θόλος με ΣΚΕΠΑΣΤΟ διάδρομο προς ΚΑΘΕ θόλο που ο διάδρομος
;         φτάνει με το πολύ 12 πλακίδια — ως AL_MAX = 4, όσα χωρά το αρχείο
;         του φαντάσματος (assert πιο κάτω)·
;       - μια δομή, ή ένας θόλος που δεν βρήκε διάδρομο, με ΜΟΝΟΠΑΤΙ στο
;         έδαφος προς το κοντινότερο κτίσμα, θόλο ή δομή. Χωρίς σκέπαστρο:
;         όποιος το περπατά είναι έξω. Είναι ένα Γ από το κεντρικό tile του
;         ενός στο κεντρικό tile του άλλου, και μετρούν μόνο τα tiles του έξω
;         από τα δύο αποτυπώματα: το πολύ 12, όλα πάνω σε έδαφος που χτίζεται
;         (bd_ok). Δοκιμάζονται και τα δύο Γ — πρώτα κατά x, μετά κατά y — και
;         κρατιέται το κοντύτερο· σε ισοπαλία το πρώτο που βρέθηκε.
;   * Αλλιώς το φάντασμα είναι κόκκινο, και ο πίνακας λέει γιατί: TOO FAR αν
;     κανένα κτίσμα δεν είναι σε απόσταση, PATH BLOCKED αν κάποιο είναι αλλά
;     το έδαφος ή ένα άλλο κτίσμα κόβει τον δρόμο (bd_nres = 3, 4).
;
; Το μονοπάτι γίνεται θεμέλιο ΧΩΡΙΣ κατοχή (βήμα 131), όπως η σύνδεση εδάφους
; του βήματος 94: ο κόσμος το δείχνει ως ισοπεδωμένο έδαφος, και θόλοι και
; διάδρομοι χτίζονται από πάνω του. Ως το βήμα 130 είχε κατοχή 2 (W_OCC_PATH)
; και ήταν φράχτης: στον κόσμο #ACE1·0 του tools/play.py, δέκα tiles ενός
; μονοπατιού από το airlock στο ορυχείο έκλειναν και τις 141 θέσεις θόλου σε
; είκοσι tiles· χωρίς την κατοχή άνοιγαν 52. Η σύνδεση με τον γράφο μένει
; (LK_OWN): οι άποικοι περπατούν το Γ ακόμη κι αν ένας θόλος το σκεπάσει. Ο
; διάδρομος κρατά την κατοχή 1 που είχε πάντα (cr_stamp).
;
; ΓΙΑΤΙ Ο ΕΛΕΓΧΟΣ ΓΙΝΕΤΑΙ ΣΕ ΚΑΘΕ ΒΗΜΑ ΚΕΡΣΟΡΑ. Το φάντασμα δείχνει τους
; διαδρόμους και το μονοπάτι ΠΡΙΝ από το FIRE, και το κόστος τους μετρά στο
; «φτάνουν τα υλικά»: ό,τι δείχνει είναι ακριβώς ό,τι θα χτιστεί. Γι' αυτό οι
; διάδρομοι που διαλέγονται σφραγίζονται ΠΡΟΣΩΡΙΝΑ στον κόσμο (bit 5) ώσπου
; να τελειώσει η αναζήτηση: δύο διάδρομοι του ίδιου θόλου δεν διασταυρώνονται,
; και το FIRE ξαναπαίζει την ίδια λίστα χωρίς να ξαναρωτήσει.

AL_RANGE    equ 12
AL_MAX      equ 4
CORR_M      equ 6                   ; ο διάδρομος ανά πλακίδιο: build.asm, bld_items
CORR_B      equ 3
; ΠΟΥ ΠΗΓΕ Η ΣΥΝΔΕΣΗ ΚΑΘΕ ΔΟΜΗΣ (lk_keep, πιο κάτω). Από το βήμα 154 στην
; τελευταία σελίδα του node_adj, στις οκτάδες των κόμβων 120-125, που δεν
; υπάρχουν: H = LKOPG, L = κόμβος | 128 — όσο κόστιζε το set 5 στις θέσεις
; 96-127 του node_deg ως τότε, που με 48 δομές είναι κόμβοι.
LKOPG       equ (G_node_adj >> 8) + 3
LK_OWN      equ LKOPG * 256 + 128 + MAX_DOME
LKO_MASK    equ #3F                     ; η δομή: το xor με τον κόμβο της δίνει 0
LKO_NONE    equ #3F                     ; τίποτα κρατημένο (game_new)
LKO_LOST    equ #FF                     ; η άκρη της γκρεμίστηκε (src/dm_ovl.asm)
        assert  (G_node_adj & 1023) == 768 && MAX_NODE <= 120   ; οι 120-125 δεν υπάρχουν
        assert  MAX_DOME == 64 && MAX_STRUCT < LKO_NONE         ; το LKO_NONE δεν είναι δομή

        ; ΤΑ ΧΡΕΗ ΜΙΑΣ ΔΟΜΗΣ ΧΩΡΑΝΕ ΣΕ ΤΕΣΣΕΡΑ BITS ΤΟ ΚΑΘΕΝΑ (src/supply.asm,
        ; ST_OWED, βήμα 88): η ακριβότερη δομή είναι η πλατφόρμα (45, χωρίς
        ; διάδρομο) ή ένα airlock με τον ΕΝΑΝ διάδρομό του, ως AL_RANGE
        ; πλακίδια (al_lck) — ως 15 φορτία των δέκα.
        assert  45 <= 150 && 10 + AL_RANGE * CORR_M <= 150 && 6 + AL_RANGE * CORR_B <= 150

        ; ΤΟ ΧΕΙΡΟΤΕΡΟ ΠΡΑΣΙΝΟ ΦΑΝΤΑΣΜΑ: το πλαίσιο ενός θόλου L και AL_MAX
        ; διάδρομοι, ως AL_RANGE + 1 σημάδια ο καθένας (η διαγώνιος n βημάτων
        ; είναι n + 1 tiles, η στροφή δεν προσθέτει).
        assert  2 * (GH_HDR + GH_SIDE * 4 * GH_EDGE) + 2 * (GH_HDR + GH_SIDE * 16 - 2 * GH_EDGE) + AL_MAX * (AL_RANGE + 1) * (GH_HDR + 8) <= GH_LOG

; ---------------------------------------------------------------------------
; al_plan — In: A = ό,τι είπε το bd_check (0: το αποτύπωμα πατά), τράπεζα 4.
; Out: A = 0 αν χτίζεται εδώ· το πλήθος των κακών tiles, ή 255 έξω από τον
; κόσμο· ή #F0 + bd_nres όταν τα tiles είναι καλά αλλά κάτι άλλο λείπει: F1
; νερό, F2 φλέβα (bd_res), F3 TOO FAR, F4 PATH BLOCKED. Γυρίζει με την
; τράπεζα 1 (uid_out).
;
; ΤΟ #F0 + ΛΟΓΟΣ ΕΙΝΑΙ ΓΙΑ ΤΟΝ ΠΙΝΑΚΑ. Το A γίνεται ui_bad, και το ui_bad είναι
; στην υπογραφή των σειρών 3-4 (ui_sig) ενώ το bd_nres όχι: ως το βήμα 84 μια
; αντλία που περνούσε από ένα κακό tile σε στεγνό έδαφος έβγαζε ui_bad = 1 και
; στα δύο, και ο πίνακας έμενε στο BLOCKED αντί για NEEDS WATER. Με τέσσερις
; λόγους πια, κάθε λόγος έχει δικό του ui_bad — ένα αποτύπωμα έχει ως 64 tiles.
;
; Γράφει ΠΑΝΤΑ το σύνολο του κόστους — κτίσμα και διάδρομοι — στο cr_metal,
; cr_biop (16 bit), όπου το διαβάζουν ο πίνακας (uip_item, και η υπογραφή του)
; και το al_afford.
; ---------------------------------------------------------------------------
al_plan:
        ld      hl,al_n
        ld      (hl),0
        inc     hl                      ; al_len
        ld      (hl),0
        inc     hl                      ; al_pt
        ld      (hl),255
        or      a
        call    z,al_find
        push    af
        ld      a,(al_len)
        ld      c,CORR_M
        call    ob_mul                  ; HL = A * C· το A μένει
        ld      de,(bd_metal)           ; E = μέταλλο, D = βιοπλαστικό
        push    de
        ld      d,0
        add     hl,de
        ld      (cr_metal),hl
        ld      c,CORR_B
        call    ob_mul
        pop     de
        ld      e,d
        ld      d,0
        add     hl,de
        ld      (cr_biop),hl
        pop     af
        ld      hl,bd_nres
        inc     (hl)
        dec     (hl)
        jp      z,uid_out               ; τα tiles, ή 0
        ld      a,(hl)
        or      #F0
        jp      uid_out

; al_afford — Z και A = 0 αν φτάνουν τα υλικά για ΟΛΟ το σύνολο του al_plan.
al_afford:
        ld      hl,(cr_metal)
        jp      cra_tot

; ---------------------------------------------------------------------------
; al_find — οι δεσμοί του κτίσματος κάτω από τον κέρσορα. Out: A = 0 ή 1.
; ---------------------------------------------------------------------------
al_find:
        ld      hl,(bd_tx)              ; το αποτύπωμα: x0, y0, w, h
        ld      (al_nx),hl
        ld      hl,(bd_w)
        ld      (al_nw),hl
        ld      hl,(cur_hx)             ; και το κεντρικό του tile
        sra     l
        sra     h
        ld      b,l
        ld      c,h
        ld      (al_p),bc               ; al_p = y, al_p + 1 = x
        xor     a
        ld      (al_why),a
        ld      (al_any),a
        ld      a,AL_RANGE + 1
        ld      (al_best),a
        ld      a,(bd_kind)
        or      a                       ; BK_DOME
        jr      nz,alf_st
        ; --- ένας θόλος: διάδρομος προς κάθε θόλο σε απόσταση, και προς κάθε
        ; airlock που δεν έχει ακόμη τον δικό του (το πρώτο κτίσμα του κόσμου,
        ; βήμα 86). «Κάτι υπάρχει» είναι μόνο οι θόλοι: ένας θόλος χωρίς άλλο
        ; θόλο στον κόσμο μπαίνει μόνος του, όσα ηλιακά κι αν στέκονται.
        ld      hl,al_cor1
        call    al_scand
        ; ΜΟΝΟ ΑΝ ΥΠΑΡΧΕΙ τέτοιο airlock (EC_FREELK, al_commit): μπαίνει μόνο του
        ; μόνο όταν δεν υπάρχει θόλος, άρα σχεδόν ποτέ — και το πέρασμα των 32
        ; δομών κόστιζε 740 µs σε κάθε βήμα κέρσορα με θόλο στο χέρι.
        ld      a,(EC_FREELK)
        or      a
        jr      z,alf_d
        ld      a,(al_any)
        push    af
        ld      hl,al_cor1a
        call    al_scans
        pop     af
        ld      (al_any),a
alf_d:
        ld      hl,al_cunt              ; οι προσωρινές σφραγίδες φεύγουν
        call    al_each
        jr      alf_n
alf_st:
        ld      a,(bd_param)
        cp      K_AIRLOCK
        jr      nz,alf_path
        ; --- ένα airlock: ΕΝΑΣ διάδρομος, προς τον κοντινότερο θόλο ---
        ld      hl,al_lck
        call    al_scand
alf_n:
        ld      a,(al_n)
        or      a
        jr      z,alf_no
alf_ok:
        xor     a
        ret
        ; --- μια δομή: μονοπάτι προς το κοντινότερο airlock ή δομή, ΠΟΤΕ σε
        ; θόλο — όποιος βγαίνει, βγαίνει από airlock (βήμα 86).
alf_path:
        ld      hl,al_try
        call    al_scans
        ld      a,(al_pt)
        inc     a
        jr      nz,alf_ok
alf_no:
        ld      a,(al_any)
        or      a
        ret     z                       ; τίποτα του είδους του: όπου θέλει
        ; Ο λόγος: κομμένο (bit 0) πριν από «δεν χωρά» (bit 1), αλλιώς μακριά.
        ld      a,(al_why)
        ld      b,4                     ; PATH BLOCKED
        rra
        jr      c,alf_r
        inc     b                       ; 5: NO CORRIDOR FITS
        rra
        jr      c,alf_r
        ld      b,3                     ; TOO FAR
alf_r:
        ld      a,b
        ld      (bd_nres),a
        ld      a,1
        ret

; ---------------------------------------------------------------------------
; al_scan — HL = ρουτίνα: κάθε κτίσμα σε απόσταση, θόλοι και δομές. al_scand —
; μόνο οι θόλοι. Η ρουτίνα καλείται με A = κόμβο για κάθε κτίσμα που υπάρχει
; και που το κέντρο του απέχει ως AL_REACH μισά tiles από τον κέρσορα σε κάθε
; άξονα· το al_any σημειώνει ότι κάτι υπάρχει. Γυρίζει με την τράπεζα 1.
;
; ΓΡΗΓΟΡΑ ΠΑΝΩ ΑΠΟ ΤΑ ΑΔΕΙΑ. Στο πρώτο σχέδιο κάθε θέση του πίνακα πλήρωνε
; σελίδα, πολλαπλασιασμό και αποτύπωμα, και κάθε κτίσμα σε απόσταση δύο Γ: ο
; έλεγχος ενός βήματος κέρσορα με ηλιακό στο χέρι κόστιζε 29 ms, με θόλο ως
; 40. Εδώ ο δείκτης περπατά τους δύο πίνακες με την 6 μέσα, έξι εντολές η
; άδεια θέση. Το όριο είναι ακριβές, όχι εκτίμηση: δύο αποτυπώματα απλώνονται
; ως 8 μισά tiles από το κέντρο τους, άρα κέντρα 41 μισά tiles μακριά αφήνουν
; κενό τουλάχιστον 13 tiles — και ένας διάδρομος 12 πλακιδίων φτάνει ως 20
; tiles κέντρο-κέντρο.
; ---------------------------------------------------------------------------
AL_REACH    equ 2 * (AL_RANGE + 8)

al_scans:
        ld      (al_fn),hl
        call    asc_b6
        ld      hl,G_struct_tbl + ST_STATE
        ld      de,STRUCT_REC
        ld      bc,(ST_TEND)            ; B = ST_THALF ζεύγη, C = MAX_DOME + ST_TOP
        assert  ST_THALF == ST_TEND + 1    ; (βήμα 157, src/top.asm: ως τότε 24 και 112)
        ; ΤΟ ΣΚΑΦΟΣ ΔΕΝ ΕΙΝΑΙ ΚΤΙΡΙΟ (βήμα 87): δεν είναι «κοντά», ούτε κάνει
        ; τον ηλιακό να μην είναι ο πρώτος. Στέκεται πάντα στη θέση 0 — το
        ; game_new το βάζει εκεί, και κτίριο δεν γκρεμίζεται — οπότε το πέρασμα
        ; αρχίζει από την 1 όταν τη βρει σκάφος: από τη μέση του πρώτου
        ; ζεύγους, με A = 0. Ενας έλεγχος, όχι ένας ανά δομή.
        ld      a,(G_struct_tbl + ST_KIND)
        sub     K_SHIP
        jr      z,asc_r0
        jr      asc_go
al_scand:
        ld      (al_fn),hl
        ld      hl,G_dome_tbl + D_STATE
        ld      de,DOME_REC
        ld      bc,(MAX_DOME >> 1) * 256 + MAX_DOME     ; B ζεύγη, C μετά το τέλος
        call    asc_b6
asc_go:
        xor     a                       ; A = 0 σε όλο το πέρασμα: cp (hl)
        ; ΔΥΟ ΘΕΣΕΙΣ ΑΝΑ ΓΥΡΟ, ΚΑΙ Ο ΚΟΜΒΟΣ ΜΟΝΟ ΟΤΑΝ ΧΡΕΙΑΖΕΤΑΙ (βήμα 156). Ως
        ; το 155 η άδεια θέση κόστιζε 13 us (ld a,(hl) / or a / jr / add hl,de /
        ; inc c / djnz), και οι 16 νέες δομές θα έδιναν +208 us σε κάθε βήμα
        ; κέρσορα με δομή στο χέρι. Εδώ 9: cp (hl) / jr / add hl,de και μισό
        ; djnz. Ο κόμβος βγαίνει από το B, και η θέση μέσα στο ζεύγος από το bit
        ; 3 του L (asc_live).
asc_lp:
        cp      (hl)                    ; D_STATE = ST_STATE: NZ αν ζει
        jr      nz,asc_live
asc_r0:
        add     hl,de
        cp      (hl)
        jr      nz,asc_live
asc_r1:
        add     hl,de
        djnz    asc_lp
; asc_b1 / asc_b6 — η τράπεζα 1 ή 6 στο παράθυρο, και τίποτε άλλο: κρατούν
; όλους τους καταχωρητές και τις σημαίες.
asc_b1:
        push    bc
        ld      bc,GA_PORT + PAGE_B1
        jr      asc_out
; asc_b5 — η τράπεζα 5 (βήμα 154: οι διάδρομοι, src/door.asm). Κρατά τα πάντα.
asc_b5:
        push    bc
        ld      bc,GA_PORT + PAGE_B5
        jr      asc_out
asc_b6:
        push    bc
        ld      bc,GA_PORT + PAGE_B6
asc_out:
        out     (c),c
        pop     bc
        ret
; asc_live — HL -> η κατάσταση ενός ζωντανού. Η ΘΕΣΗ ΜΕΣΑ ΣΤΟ ΖΕΥΓΟΣ είναι το
; bit 3 του L: οι εγγραφές είναι 8 ή 24 bytes από μια κατάσταση με L & 15 = 4,
; άρα το bit 3 είναι η ισοτιμία της θέσης, και στη δεύτερη σελίδα των δομών. Ο
; κόμβος C - 2B + αυτό, και μόνο για ό,τι είναι σε απόσταση: τα άλλα δεν
; πληρώνουν ούτε τον κόμβο ούτε το asc_b6 (ως το 155 και τα δύο, 23 us).
asc_live:
        ld      (al_any - 1),hl         ; το H (>= #40) στο al_any: κάτι υπάρχει
        push    bc
        push    de
        push    hl
        dec     hl
        dec     hl
        dec     hl                      ; cy
        ld      de,cur_hy
        call    al_far
        dec     hl                      ; cx: το L - 4 κρατά το bit 3
        dec     de                      ; cur_hx
        call    nc,al_far
        jr      c,asl_far
        ld      a,c
        sub     b
        sub     b
        bit     3,l
        jr      z,asl_k0
        inc     a
asl_k0:
        call    al_call                 ; A = ο κόμβος
        call    asc_b6
asl_far:
        pop     hl
        pop     de
        pop     bc
        xor     a
        bit     3,l
        jr      z,asc_r0
        jr      asc_r1
        assert  ((G_dome_tbl + D_STATE) & 15) == 4
        assert  ((G_struct_tbl + ST_STATE) & 15) == 4
        assert  DOME_REC == 24 && STRUCT_REC == 8 && D_STATE == ST_STATE
        assert  (MAX_DOME & 1) == 0 && (MAX_STRUCT & 1) == 0
al_call:
        ld      hl,(al_fn)
        jp      (hl)

; al_far — CY αν |(DE) - (HL)| > AL_REACH μισά tiles (ή >= 128). Κρατά HL, DE.
al_far:
        ld      a,(de)
        sub     (hl)
        jp      pe,alf_far
        jp      p,alf_p
        neg
alf_p:
        cp      AL_REACH + 1
        ccf
        ret
alf_far:
        scf
        ret

; al_cor1 — A = θόλος σε απόσταση: στη λίστα, αν ο διάδρομος βγαίνει και χωρά.
al_cor1:
        ld      c,a
        ld      a,(al_n)
        cp      AL_MAX
        ret     nc
        ld      a,c
        push    bc
        call    al_cor
        pop     bc
        ret     nz
        ld      hl,al_n
        ld      a,(hl)
        inc     (hl)
        ld      hl,al_lst
        call    ob_addu
        ld      (hl),c
        call    cr_pcs
        ld      hl,al_len
        add     a,(hl)
        ld      (hl),a
        ret

; al_cor1a — A = δομή σε απόσταση: στη λίστα του θόλου μόνο αν είναι airlock
; ΧΩΡΙΣ ακμή — ένα airlock ενώνεται με ΕΝΑ κτίριο (βήμα 86). Η τράπεζα 6 είναι
; ακόμη μέσα (al_scans).
al_cor1a:
        ld      c,a
        add     a,a
        add     a,a                     ; (64 + δομή) x 4 = δομή x 4 σε 8 bits
        add     a,STB_C + ST_KIND / 2
        ld      l,a
        ld      h,STB_H
        add     hl,hl                   ; -> ST_KIND (src/const.asm, βήμα 154)
        ld      a,(hl)
        cp      K_AIRLOCK
        ret     nz
        ; ΜΟΝΟ ΑΝ ΔΕΝ ΕΧΕΙ ΗΔΗ ΔΙΑΔΡΟΜΟ. Ως το βήμα 86 αυτό ήταν «βαθμός 0»· από
        ; το 87 το airlock έχει από την αρχή τη σύνδεση εδάφους του, και ο
        ; διάδρομός του γίνεται ακμή μόνο όταν τελειώσει — οπότε το λέει ένα
        ; byte της εγγραφής του (al_commit).
        set     2,l                     ; ST_JOINED = ST_KIND + 4: L = 8k + 2 -> 8k + 6
        ld      a,(hl)
        or      a
        ret     nz
        ld      a,c
        jr      al_cor1

; al_lck — A = θόλος σε απόσταση, για ένα NEO airlock: κρατά τον θόλο με τον
; κοντύτερο διάδρομο· σε ισοπαλία τον πρώτο. Χωρίς προσωρινή σφραγίδα: ο
; διάδρομος είναι ένας.
al_lck:
        ld      c,a
        push    bc
        call    al_cor0
        pop     bc
        ret     nz
        call    cr_pcs
        ld      hl,al_best
        cp      (hl)
        ret     nc
        ld      (hl),a
        ld      (al_len),a
        ld      a,c
        ld      (al_lst),a
        ld      a,1
        ld      (al_n),a
        ret

; al_cor — A = κόμβος: διάδρομος ως εκεί; Z αν ναι — και τότε τα tiles του
; σφραγίζονται προσωρινά, ώστε ο επόμενος να μην περάσει από πάνω του.
al_cor:
        call    al_cor0
        ret     nz
        ld      hl,al_ctmp
        call    crw_b4
als_no:                                 ; και του al_set
        xor     a
        ret
; al_cor0 — το ίδιο, χωρίς τη σφραγίδα. Θυμάται στο al_why ΓΙΑΤΙ όχι: bit 0
; όταν ο διάδρομος πατά κάτι, bit 1 όταν δεν υπάρχει σχήμα αν και ένας
; αξονικός ως εκεί θα χωρούσε στα AL_RANGE (η ζώνη «σχεδόν διαγώνιο» του
; §9.4) — ο πίνακας λέει τότε NO CORRIDOR FITS, όχι TOO FAR.
al_cor0:
        call    al_set
        jr      z,alc_shape
        call    cr_pcs
        cp      AL_RANGE + 1
        jr      nc,alc_no
        call    cr_check
        or      a
        ret     z
        ld      hl,al_why
        set     0,(hl)
        ret                             ; NZ από το or
alc_shape:
        ld      hl,cr_ds
        ld      a,(hl)                  ; S
        inc     hl
        cp      (hl)                    ; T
        jr      nc,alc_m
        ld      a,(hl)
alc_m:
        ld      hl,cr_ra
        sub     (hl)
        inc     hl                      ; cr_rb
        sub     (hl)
        jp      m,alc_fit               ; πιο κοντά κι από έναν αξονικό
        cp      AL_RANGE + 1
        jr      nc,alc_no
alc_fit:
        ld      hl,al_why
        set     1,(hl)
alc_no:
        or      1
        ret

; al_set — A = κόμβος b: η διαδρομή από το κτίσμα του κέρσορα ως τον b.
; NZ αν υπάρχει (A = cr_n). Το άκρο a είναι ο κέρσορας, όχι ο πίνακας: στον
; έλεγχο το κτίσμα δεν υπάρχει ακόμη, και μετά το bd_commit είναι το ίδιο. Ενα
; νέο airlock είναι άκρο μεγέθους AIRLOCK: το cr_pair δεν βρίσκει τίποτα από
; αυτό και αλλάζει τα άκρα, οπότε ο διάδρομος βγαίνει από τον θόλο.
al_set:
        ld      (cr_b),a
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        ld      de,cr_tx
        call    cr_read
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        jr      c,als_no
        ld      a,(bd_node)
        ld      (cr_a),a
        ld      hl,(cur_hx)
        ld      (cr_fx),hl              ; και το cr_fy
        ld      a,(bd_kind)
        or      a                       ; BK_DOME: το μέγεθος
        ld      a,(bd_param)
        jr      z,als_sz
        ld      a,AIRLOCK               ; η μόνη δομή που φτάνει εδώ
als_sz:
        ld      (cr_fs),a
        jp      cr_pair

; al_each — HL = ρουτίνα ανά tile: κάθε διάδρομος της λίστας με την τράπεζα 4.
al_each:
        ld      (al_ecb),hl
        ld      a,(al_n)
        or      a
        ret     z
        ld      b,a
        ld      hl,al_lst
ale_lp:
        push    bc
        push    hl
        ld      a,(hl)
        call    al_set
        ld      hl,(al_ecb)
        call    crw_b4
        pop     hl
        pop     bc
        inc     hl
        djnz    ale_lp
        ret

; al_ctmp / al_cunt — η προσωρινή σφραγίδα: bit 5, η κατοχή 2, ΜΟΝΟ έξω από
; τα δύο αποτυπώματα. Εκεί τα tiles ήταν ελεύθερα (cr_check), άρα το bit 5 ήταν
; 0 και το res το ξαναφέρνει. Μέσα δεν χρειάζεται: ο έλεγχος δεν κοιτά τα tiles
; των δύο άκρων, και ένας άλλος θόλος είναι ήδη κατειλημμένος. (Ως να γραφτεί
; αυτό, η σφραγίδα έπιανε και το αποτύπωμα του b — και το tests/test_reach.py
; βρήκε κόσμο όπου το bit 5 ήταν ήδη αναμμένο εκεί και το res το έσβηνε.)
al_ctmp:
        call    al_out
        ret     c
        set     5,(hl)
        ret
al_cunt:
        call    al_out
        ret     c
        res     5,(hl)
        ret
; al_out — HL = το tile (B, C)· CY αν είναι μέσα στο αποτύπωμα ενός άκρου.
al_out:
        call    tile_addr
        push    hl
        ld      hl,cr_fx
        call    crk_in
        jr      c,alo_in
        ld      hl,cr_tx
        call    crk_in
alo_in:
        pop     hl
        ret

; ---------------------------------------------------------------------------
; al_try — A = κόμβος: ένα μονοπάτι ως εκεί, κοντύτερο από το al_best;
; ---------------------------------------------------------------------------
al_try:
        ld      (al_t),a
        call    al_node
        ret     c                       ; άδεια θέση
        ; --- ΤΟ ΚΑΤΩ ΟΡΙΟ: το Γ πατά ΤΟΥΛΑΧΙΣΤΟΝ το κενό ανάμεσα στα δύο
        ; αποτυπώματα στον x ΚΑΙ στον y. Το οριζόντιο σκέλος του κάθεται σε
        ; σειρά του ενός και το κάθετο σε στήλη του άλλου, άρα κανένα tile του
        ; δεν είναι και στα δύο κενά. Οτι δεν νικά το καλύτερο ως τώρα δεν
        ; περπατιέται — και το «κομμένο» (al_why) μετρά μόνο όταν δεν βρεθεί
        ; τίποτα, οπότε το al_best είναι ακόμη AL_RANGE + 1.
        ld      hl,al_nx
        ld      de,al_rx
        call    al_gap
        ld      b,a
        inc     hl
        inc     de
        call    al_gap
        add     a,b
        ld      hl,al_best
        cp      (hl)
        ret     nc
        ld      (al_lb),a
        xor     a                       ; πρώτα κατά x
        call    al_ltry
        ; ΤΟ ΔΕΥΤΕΡΟ Γ ΔΕΝ ΝΙΚΑ ΤΟ ΚΑΤΩ ΟΡΙΟ: αν το πρώτο το έπιασε — και σε
        ; αποτυπώματα που επικαλύπτονται σε έναν άξονα σχεδόν πάντα — το καλύτερο
        ; είναι δικό του (ό,τι νικιόταν από παλιότερο δεν έφτασε ως εδώ).
        ld      a,(al_best)
        ld      hl,al_lb
        cp      (hl)
        ret     z
        ld      a,1                     ; και μετά κατά y
al_ltry:
        ld      (al_ori),a
        ld      hl,0
        ld      (al_cnt),hl             ; και το al_bad
        ld      hl,al_cbk
        ld      (al_cb),hl
        call    al_w4
        ret     c                       ; μακρύτερο από AL_RANGE
        ld      a,(al_bad)
        or      a
        jr      nz,alt_blk
        ld      a,(al_cnt)
        ld      hl,al_best
        cp      (hl)
        ret     nc
        ld      (hl),a
        ld      a,(al_t)
        ld      (al_pt),a
        ld      a,(al_ori)
        ld      (al_po),a
        ret
alt_blk:
        ld      (al_why),a              ; κάτι σε απόσταση, αλλά κομμένο
        ret

; al_gap — HL -> (x0, ., w) του νέου, DE -> του άλλου, στον ίδιο άξονα: A =
; τα tiles ανάμεσά τους, 0 αν επικαλύπτονται. Μετά το al_scan οι αρχές απέχουν
; ως 24 tiles και η αφαίρεση δεν ξεχειλίζει. Κρατά BC, DE, HL.
al_gap:
        call    alg_one                 ; δεξιά του νέου;
        ret     p
        ex      de,hl
        call    alg_one                 ; αριστερά;
        ex      de,hl
        ret     p
        xor     a
        ret
; alg_one — A = (DE).x0 - (HL).x0 - (HL).w, με το πρόσημο στις σημαίες.
alg_one:
        ld      a,(de)
        sub     (hl)
        inc     hl
        inc     hl
        sub     (hl)
        dec     hl
        dec     hl
        ret

; al_cbk — ένα tile του μονοπατιού στον έλεγχο: μετράει, και θυμάται αν δεν
; πατιέται. CY όταν περάσει τα AL_RANGE. Κρατά BC, DE.
;
; ΤΟ tile_addr ΚΑΙ ΤΟ bd_ok ΜΕΣΑ (βήμα 107): το al_cbk είναι ο έλεγχος κάθε
; βήματος κέρσορα, ~40 tiles δίπλα στην αποικία, και οι δύο κλήσεις ήταν το
; ένα τρίτο του.
al_cbk:
        ld      a,b
        add     a,64
        ld      l,a                     ; tx + 64
        ld      a,c
        add     a,64
        srl     a                       ; το κρατούμενο είναι το ty & 1
        jr      nc,alk_ev
        set     7,l
alk_ev:
        add     a,WORLD_BASE >> 8
        ld      h,a
        ld      a,(hl)
        and     W_OCC_MASK + 7          ; το bd_ok: έδαφος, σκόνη, θεμέλιο
        jr      z,alk_ok
        dec     a
        jr      z,alk_ok
        cp      W_FOUNDATION - 1
        jr      z,alk_ok
        ld      a,1
        ld      (al_bad),a
alk_ok:
        ld      hl,al_cnt
        inc     (hl)
        ld      a,AL_RANGE
        cp      (hl)
        ret

; al_cbm — το σημάδι του φαντάσματος. al_cbs — η σφραγίδα του FIRE: θεμέλιο
; χωρίς κατοχή (βήμα 131· ως το 130 με κατοχή 2, φράχτης).
al_cbm:
        call    ui_mark
        or      a
        ret
al_cbs:
        call    tile_addr
        ld      a,(hl)
        and     #C0                     ; το decor μένει
        or      W_FOUNDATION
        ld      (hl),a
        ret
; al_cbr — ένα tile της σύνδεσης εδάφους (βήμα 94, lk_draw), με την 4 μέσα:
; θεμέλιο, αν είναι ελεύθερο έδαφος που χτίζεται (bd_ok), και τότε το κρατά
; το al_cbb για να ξαναζωγραφιστεί. ΧΩΡΙΣ κατοχή: μια σύνδεση εδάφους δεν έχει
; όριο μήκους, και ένα μονοπάτι από το σκάφος ως το μακρινό airlock δεν πρέπει
; να κόβει στη μέση τον τόπο όπου θα χτίσεις. Ο,τι άλλο, μένει. Πάντα NC: το
; Γ δεν σταματά. Κρατά BC, DE.
al_cbr:
        call    tile_addr
        ld      a,(hl)
        call    bd_ok
        ld      a,(hl)
        jr      nz,acr_no
        and     #C0                     ; το decor μένει
        or      W_FOUNDATION
        ld      (hl),a
        jr      al_cbb
acr_no:
        or      a
        ret
; al_cbb — το πρώτο και το τελευταίο tile ενός σκέλους (al_leg). NC.
al_cbb:
        ld      hl,al_en
        ld      a,(hl)
        inc     (hl)
        or      a                       ; και NC
        jr      nz,alb_l
        ld      (al_ef),bc
alb_l:
        ld      (al_el),bc
        ret

; ---------------------------------------------------------------------------
; al_node — A = κόμβος (θόλος 0-63, 64 + δομή). Το αποτύπωμά του στο al_rx..
; al_rh και το κεντρικό του tile στο al_q. CY αν η θέση είναι άδεια. Γυρίζει
; με την τράπεζα 1.
;
; Θόλος: πλευρά 4 + 2 x μέγεθος. Δομή: το struct_dims, bytes / 4 x γραμμές /
; 16 — το sprite γεμίζει ακριβώς τα tiles της (όπως το msc_near).
; ---------------------------------------------------------------------------
al_node:
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        cp      MAX_DOME
        jr      nc,aln_st
        call    ob_domeadr              ; HL -> cx
        inc     hl
        inc     hl
        ld      a,(hl)                  ; D_SIZE
        add     a,a
        add     a,4
        ld      d,a
        ld      e,a
        jr      aln_go
aln_st:
        add     a,a
        add     a,a                     ; (64 + δομή) x 4 = δομή x 4 σε 8 bits
        add     a,STB_C + ST_KIND / 2
        ld      l,a
        ld      h,STB_H
        add     hl,hl                   ; -> ST_KIND (src/const.asm, βήμα 154)
        ld      a,(hl)                  ; ST_KIND
        inc     hl
        add     a,a
        add     a,a
        add     a,(hl)                  ; + ST_SIZE
        dec     hl
        add     a,a                     ; είδος * 8 + μέγεθος * 2
        push    hl
        ld      hl,G_struct_dims
        call    ob_addu
        ld      a,(hl)
        rrca
        rrca
        and     #3F
        ld      e,a                     ; w = bytes / 4
        inc     hl
        ld      a,(hl)
        rrca
        rrca
        rrca
        rrca
        and     #0F
        ld      d,a                     ; h = γραμμές / 16
        pop     hl
aln_go:                                 ; HL -> +2, E = w, D = h
        inc     hl
        inc     hl
        ld      a,(hl)                  ; D_STATE = ST_STATE
        sub     1                       ; CY: άδεια
        jr      c,aln_out
        dec     hl
        dec     hl
        dec     hl
        ld      a,(hl)                  ; cy
        ld      c,a
        sub     d
        sra     a
        ld      (al_ry),a
        dec     hl
        ld      a,(hl)                  ; cx
        ld      b,a
        sub     e
        sra     a
        ld      (al_rx),a
        ld      (al_rw),de              ; και το al_rh
        sra     b
        sra     c
        ld      (al_q),bc               ; al_q = y, al_q + 1 = x
        or      a                       ; NC
aln_out:
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        ret

; ---------------------------------------------------------------------------
; al_walk — το Γ από το P (al_p) στο Q (al_q): (al_ori) 0 = πρώτα κατά x. Για
; κάθε tile έξω από τα δύο αποτυπώματα καλεί την (al_cb) με B = x, C = y·
; αυτή κρατά τα BC, DE, και με CY σταματά τα πάντα. Το P δεν περνιέται: είναι
; μέσα στο νέο αποτύπωμα. Κάθε tile μία φορά — το φάντασμα το θέλει έτσι.
; al_w4 — το ίδιο με την τράπεζα 4 στο παράθυρο.
; ---------------------------------------------------------------------------
; (Το al_lgo, το μονοπάτι που διαλέχτηκε με την 4, ζει στην τράπεζα 1 από το
; βήμα 94: src/commit.asm.)
; al_s4 — το al_seg από το (B, C) ως το (H, L) με την τράπεζα 4 μέσα: ένα
; σκέλος του Γ για το al_leg (src/commit.asm, βήμα 94), που ζει στην 1.
al_s4:
        call    al_rsync                ; κρατά BC, HL
        push    bc
        ld      bc,GA_PORT + PAGE_B4
        out     (c),c
        pop     bc
        call    al_seg
        jr      alw_b1
al_w4:
        call    al_rsync
        ld      bc,GA_PORT + PAGE_B4
        out     (c),c
        call    al_walk
alw_b1:
        ld      bc,GA_PORT + PAGE_B1    ; οι σημαίες μένουν
        out     (c),c
        ret
al_walk:
        call    al_k
        call    al_seg
        ret     c
        ld      hl,(al_q)
; al_seg — από το (B, C) ως το (H, L), σε έναν άξονα: βήμα, και μετά tile.
al_seg:
        ld      a,h
        sub     b
        call    al_sgn
        ld      d,a
        ld      a,l
        sub     c
        call    al_sgn
        ld      e,a
als_lp:
        ld      a,b
        cp      h
        jr      nz,als_st
        ld      a,c
        cp      l
        ret     z                       ; και NC
als_st:
        ld      a,b
        add     a,d
        ld      b,a
        ld      a,c
        add     a,e
        ld      c,a
        push    hl
        call    al_emit
        pop     hl
        ret     c
        jr      als_lp

; al_sgn — A -> -1, 0 ή 1.
al_sgn:
        or      a
        ret     z
        ld      a,1
        ret     p
        neg
        ret

; al_k — BC = P (B = x, C = y) και HL = η γωνία K του Γ (H = x, L = y).
al_k:
        ld      bc,(al_p)
        ld      hl,(al_q)
        ld      a,(al_ori)
        or      a
        jr      nz,alk_v
        ld      l,c                     ; πρώτα κατά x: K = (qx, py)
        ret
alk_v:
        ld      h,b                     ; πρώτα κατά y: K = (px, qy)
        ret

; al_emit — ένα tile: μέσα σε κάποιο από τα δύο αποτυπώματα δεν μετρά (NC),
; αλλιώς η (al_cb).
;
; ΤΑ ΔΥΟ ΑΠΟΤΥΠΩΜΑΤΑ ΜΕΣΑ ΣΤΙΣ ΕΝΤΟΛΕΣ (βήμα 107). Ως τότε δύο κλήσεις al_in
; ανά tile, με τον δείκτη στο al_nx και στο al_rx: ~54 us για ένα tile έξω
; και από τα δύο, που είναι σχεδόν όλα. Τώρα το al_rsync γράφει τα x0, y0,
; w, h των δύο στα sub / cp από κάτω στην αρχή κάθε Γ (al_w4, al_s4), και
; ένα tile έξω είναι ~22 us. Οποιος αλλάζει το al_nx.. ή το al_rx.. ανάμεσα
; στα al_w4 / al_s4 δεν φαίνεται εδώ — και κανείς δεν το κάνει: το al_node,
; το al_find και το dmp_set του src/dm_ovl.asm τα γράφουν πριν.
al_emit:
        ld      a,b
ale_nx: sub     0                       ; x - x0 < w: μέσα στον άξονα x
ale_nw: cp      0
        jr      nc,ale_r
        ld      a,c
ale_ny: sub     0
ale_nh: cp      0
        jr      c,ale_in
ale_r:
        ld      a,b
ale_rx: sub     0
ale_rw: cp      0
        jr      nc,ale_cb
        ld      a,c
ale_ry: sub     0
ale_rh: cp      0
        jr      nc,ale_cb
ale_in:
        or      a                       ; NC: δεν μετρά, συνέχισε
        ret
ale_cb:
        ld      hl,(al_cb)
        jp      (hl)

; al_rsync — τα al_nx.. και al_rx.. μέσα στο al_emit. Κρατά BC, HL.
al_rsync:
        ld      de,(al_nx)              ; E = x0, D = y0
        ld      a,e
        ld      (ale_nx + 1),a
        ld      a,d
        ld      (ale_ny + 1),a
        ld      de,(al_nw)              ; E = w, D = h
        ld      a,e
        ld      (ale_nw + 1),a
        ld      a,d
        ld      (ale_nh + 1),a
        ld      de,(al_rx)
        ld      a,e
        ld      (ale_rx + 1),a
        ld      a,d
        ld      (ale_ry + 1),a
        ld      de,(al_rw)
        ld      a,e
        ld      (ale_rw + 1),a
        ld      a,d
        ld      (ale_rh + 1),a
        ret

; ---------------------------------------------------------------------------
; al_ghost — οι διάδρομοι ή το μονοπάτι, πράσινα, πάνω στο φάντασμα· και μετά
; ο πίνακας. Από το ui_show, όταν η θέση επιτρέπεται.
; ---------------------------------------------------------------------------
al_ghost:
        ld      a,(al_pt)
        inc     a
        ld      hl,al_cbm
        call    nz,al_lgo
        ld      hl,ui_mark
        call    al_each
        jp      ui_panel


; ---------------------------------------------------------------------------
; Το al_commit, το μονοπάτι και η σύνδεση εδάφους που ζωγραφίζεται: στην
; τράπεζα 1 από το βήμα 94 (src/commit.asm). Από εδώ και κάτω η συνέχειά του,
; οι διάδρομοι — το alc_cor καλεί το cr_commit, που σελιδοποιεί την 6.
; ---------------------------------------------------------------------------
alc_cor:
        ld      hl,(bd_metal)
        push    hl
        ld      hl,CORR_B * 256 + CORR_M
        ld      (bd_metal),hl
        ld      a,(al_n)
        or      a
        jr      z,alc_none
        ld      b,a
        ld      hl,al_lst
alc_lp:
        push    bc
        push    hl
        ld      a,(hl)
        cp      MAX_DOME
        jr      c,alc_d
        ld      de,EC_FREELK            ; ένα airlock που ήταν μόνο του
        ex      de,hl
        dec     (hl)
        ex      de,hl
        call    alc_join                ; έχει πια τον διάδρομό του
alc_d:
        call    al_set
        call    cr_commit               ; A = 0: μπήκε
        or      a
        call    z,cr_redraw
        pop     hl
        pop     bc
        inc     hl
        djnz    alc_lp
        ; Ενα νέο airlock με τον διάδρομό του: κι αυτό δεν είναι πια μόνο.
        ld      a,(bd_param)
        cp      K_AIRLOCK
        ld      a,(bd_node)
        call    z,alc_join
alc_out:
        pop     hl
        ld      (bd_metal),hl
        ret
; alc_join — A = κόμβος airlock: ST_JOINED = 1. Κρατά AF, BC, HL.
alc_join:
        push    af
        push    hl
        call    asc_b6                  ; το BC το κρατούν το asc_b6, το
        call    gr_live                 ; gr_live και το asc_b1· HL -> ST_STATE
        inc     hl
        inc     hl                      ; ST_JOINED
        ld      (hl),1
        pop     hl
        pop     af
        jp      asc_b1
alc_none:
        ; Χωρίς διάδρομο: ένα airlock που μπήκε μόνο του περιμένει τον θόλο του.
        ld      a,(bd_kind)
        or      a                       ; BK_DOME
        jr      z,alc_out
        ld      a,(bd_param)
        cp      K_AIRLOCK
        jr      nz,alc_out
        ld      hl,EC_FREELK
        inc     (hl)
        jr      alc_out

; ---------------------------------------------------------------------------
; lk_ground — B = κόμβος: η σύνδεση εδάφους ως το κοντινότερο airlock ή το
; σκάφος που έχει ελεύθερη ακμή, αν υπάρχει. Αν όχι, το εργοτάξιο μένει
; απρόσιτο — με το σκάφος να υπάρχει πάντα, χρειάζεται οκτώ ακμές σε κάθε
; πόρτα πρώτα. Η άλλη άκρη, ή 255, μένει στο al_pt: τη ζωγραφίζει το lk_draw
; (src/commit.asm, βήμα 94). Μιας δομής την κρατά και στο LK_OWN (βήμα 102).
; ---------------------------------------------------------------------------
lk_ground:
        call    asc_b6
        call    lk_anchor
        call    asc_b1
        ld      (al_pt),a
        ld      c,a
        inc     a
        ret     z
        bit     6,b
        jp      z,cr_link_bc            ; θόλος: τη χάνει όταν τελειώσει (lk_done)
        ld      a,c
        and     LKO_MASK                ; σύνδεση εδάφους: χωρίς το bit 6
        jr      lk_keep

; ---------------------------------------------------------------------------
; ΠΟΥ ΠΗΓΕ Η ΣΥΝΔΕΣΗ ΜΙΑΣ ΔΟΜΗΣ (βήμα 102). Ενα byte ανά δομή, στο LK_OWN +
; δομή. Ενα μονοπάτι κρατιέται ως ο κόμβος στην άλλη άκρη (64 + δομή), με το
; bit 7 για το σχήμα του, 1 = πρώτα κατά y (al_po). Μια σύνδεση εδάφους
; κρατιέται ως η δομή στην άλλη άκρη, χωρίς το bit 6 του κόμβου, και δεν έχει
; bit 7: ζωγραφίζεται πρώτα κατά x (lk_draw). LKO_NONE (#3F) = καμία, αυτή που
; δεν κράτησε κανείς: η ακμή της αποικίας δοκιμών. Ως το βήμα 153 η σύνδεση
; εδάφους είχε το bit 5 του κόμβου, και το «καμία» ήταν 0· με 48 δομές το bit
; 5 είναι μέρος του κόμβου (96-111), και το 0 είναι η σύνδεση εδάφους ως το
; σκάφος. Ως το βήμα 102 το Γ ενός μονοπατιού δεν το θυμόταν τίποτα, και η
; κατεδάφιση το άφηνε να κόβει το έδαφος για πάντα· με αυτό ξαναδένει όποιον
; έχασε τη σύνδεσή του (src/dm_ovl.asm), και ως το βήμα 130 έσβηνε και τα
; tiles του. Το Γ το περπατούν οι άποικοι (src/walk6.asm, βήμα 118).
;
; Η ΔΟΜΗ ΣΤΗΝ ΑΚΡΗ, και από τα δύο σχήματα, είναι τα έξι κάτω bits
; (LKO_MASK): ο κόμβος C ταιριάζει αν (C xor byte) and LKO_MASK = 0. Ο κόμβος
; της είναι αυτά or 64· το LKO_NONE και το LKO_LOST δίνουν 127, πάνω από το
; MAX_NODE (dm_up).
;
; ΣΤΗΝ ΤΕΛΕΥΤΑΙΑ ΣΕΛΙΔΑ ΤΟΥ node_adj από το βήμα 154 (στις θέσεις 96-127 του
; node_deg ως τότε): το game_new τη γεμίζει με LKO_NONE, και σώζεται με τον
; γράφο (src/save.asm, SV_STATE).
; ---------------------------------------------------------------------------
; lk_keepp — B = η νέα δομή, C = η άκρη του μονοπατιού της (al_po το σχήμα):
; κρατιέται, και μετά η ακμή.
lk_keepp:
        ld      a,(al_po)               ; 0 ή 1 (al_ltry)
        rrca
        or      c
; lk_keep — A = ό,τι κρατιέται, B = η δομή, C = η άλλη άκρη: και η ακμή.
lk_keep:
        ld      h,LKOPG
        ld      l,b
        set     7,l                     ; LK_OWN + δομή
        ld      (hl),a
        jp      cr_link_bc

; lk_anchor — B = ο νέος κόμβος, στον κέρσορα· τράπεζα 6 μέσα. A = το
; κοντινότερο (max |dx|, |dy| σε μισά tiles) σκάφος ή airlock, έτοιμο ή
; εργοτάξιο, όχι ο ίδιος, με βαθμό κάτω από MAX_DEGREE· 255 αν κανένα. Σε
; ισοπαλία το πρώτο. Κρατά B.
lk_anchor:
        push    ix
        ld      de,(cur_hx)             ; E = cx, D = cy: το νέο είναι στον κέρσορα
        ld      ix,G_struct_tbl
        ld      hl,#FFFF                ; L = η καλύτερη απόσταση, H = ο κόμβος
        ld      c,MAX_DOME
lka_lp:
        ld      a,(ix+ST_STATE)
        or      a
        jr      z,lka_nx
        ld      a,(ix+ST_KIND)
        cp      K_SHIP
        jr      z,lka_k
        cp      K_AIRLOCK
        jr      nz,lka_nx
lka_k:
        ld      a,c
        cp      b
        jr      z,lka_nx                ; όχι ο ίδιος
        push    hl
        ld      h,NODEPG
        ld      l,a
        ld      a,(hl)
        pop     hl
        cp      MAX_DEGREE
        jr      nc,lka_nx               ; οι ακμές του γέμισαν
        ld      a,(ix+ST_CX)
        sub     e
        call    lk_abs
        ld      (lk_dt),a
        ld      a,(ix+ST_CY)
        sub     d
        call    lk_abs
        push    hl
        ld      hl,lk_dt
        cp      (hl)
        jr      nc,lka_m
        ld      a,(hl)                  ; το μεγαλύτερο από τα δύο
lka_m:
        pop     hl
        cp      l
        jr      nc,lka_nx
        ld      l,a
        ld      h,c
lka_nx:
        push    de
        ld      de,STRUCT_REC
        add     ix,de
        pop     de
        inc     c
        ld      a,c
        cp      MAX_NODE
        jr      c,lka_lp
        ld      a,h
        pop     ix
        ret

; lk_abs — A = η διαφορά με τις σημαίες του sub -> |A|, 254 αν ξεχείλισε.
lk_abs:
        jp      pe,lka_far
        ret     p
        neg
        ret
lka_far:
        ld      a,254
        ret

; --- η κατάσταση -------------------------------------------------------------
lk_dt:      db 0
al_n:       db 0                ; πόσοι διάδρομοι
al_len:     db 0                ; τα πλακίδιά τους, όλων μαζί
al_pt:      db 255              ; το μονοπάτι: ο κόμβος στην άκρη, 255 = κανένα
al_po:      db 0                ; και το σχήμα του (al_ori)
al_lst:     defs AL_MAX         ; οι θόλοι των διαδρόμων
al_nx:      db 0                ; το νέο: x0, y0, w, h σε tiles
al_ny:      db 0
al_nw:      db 0
al_nh:      db 0
al_rx:      db 0                ; το άλλο άκρο
al_ry:      db 0
al_rw:      db 0
al_rh:      db 0
al_p:       dw 0                ; τα κεντρικά tiles: y, x
al_q:       dw 0
al_ori:     db 0
al_cnt:     db 0
al_bad:     db 0
al_best:    db 0
al_t:       db 0
            db 0                ; το L του asc_live (βήμα 156)
al_any:     db 0
al_why:     db 0
al_cb:      dw 0
al_en:      db 0                ; al_leg: πόσα tiles, το πρώτο, το τελευταίο
al_ef:      dw 0
al_el:      dw 0
al_ecb:     dw 0
al_fn:      dw 0
al_lb:      db 0

        ; (το cr_fy == cr_fx + 1, το bd_biop == bd_metal + 1 και το cur_hy ==
        ; cur_hx + 1 τα ελέγχουν τα route.asm, build.asm και ui.asm· στο
        ; tests/uitest.asm θα ήταν εδώ μπροστινές ετικέτες)
        assert  al_len == al_n + 1 && al_pt == al_n + 2
        assert  al_bad == al_cnt + 1 && al_nh == al_nw + 1 && al_rh == al_rw + 1
        assert  al_ny == al_nx + 1 && al_ry == al_rx + 1      ; al_rsync
        assert  W_DUST == 1                     ; το bd_ok μέσα στο al_cbk
        assert  D_STATE == 4 && ST_STATE == 4 && ST_KIND == 2 && ST_SIZE == 3
        assert  D_SIZE == 2 && D_CX == 0 && D_CY == 1
        assert  MAX_DOME == 64 && (ST_KIND & 1) == 0
        assert  STRUCT_REC == 8 && ST_JOINED == ST_KIND + 4   ; al_cor1a, al_node
