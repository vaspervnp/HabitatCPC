; route.asm — η διαδρομή ενός διαδρόμου ανάμεσα σε δύο θόλους (DESIGN §9.4).
;
; Η τέχνη δίνει τέσσερα sprites — corr_h, corr_v, corr_dr, corr_dl — και ΚΑΜΙΑ
; γωνία 90 μοιρών. Αρα η διαδρομή δεν μπορεί να είναι Γ: η μόνη στροφή που
; υπάρχει στο σετ είναι διαγώνιος -> άξονας.
;
; ΤΟ ΠΛΕΓΜΑ. Το διαγώνιο πλακίδιο είναι 8 bytes x 16 γραμμές, δηλαδή ΔΥΟ tiles
; φαρδύ και ΕΝΑ ψηλό, και το βήμα του είναι (4, 16) — ένα tile διαγώνια. Δύο
; διαδοχικά επικαλύπτονται κατά ένα tile (αυτό είναι τα «8 pixel» του
; SPRITES.md §6) και η γραμμή τους περνά από τα σημεία πλέγματος
; (4j, 16j) γύρω από το κέντρο του θόλου: το πλακίδιο j έχει πάνω-αριστερά το
; σημείο πλέγματος j μείον (4, 8).
;
; Ο οριζόντιος είναι 4x8 — ένα tile φαρδύς, μισό ψηλός — και κάθεται στο ΠΑΝΩ
; μισό της σειράς του. Ο κάθετος είναι 2x16: μισό tile φαρδύς, στο ΑΡΙΣΤΕΡΟ
; μισό της στήλης του. Και οι δύο βγαίνουν από το σημείο σύνδεσης, που κάθεται
; στη μέση της πλευράς — άρα η λωρίδα τους περνά από το ΚΕΝΤΡΟ του θόλου.
;
; ΟΙ ΔΥΟ ΣΤΡΟΦΕΣ, και γιατί δεν είναι συμμετρικές:
;
;   διαγώνιος -> ΟΡΙΖΟΝΤΙΟΣ: η διαγώνιος φτάνει ως το σημείο πλέγματος T (η
;       κατακόρυφη απόσταση σε tiles) και ο οριζόντιος ξεκινά ΕΝΑ tile πριν,
;       πάνω στο ίδιο πλακίδιο. Το διαγώνιο πλακίδιο είναι ένα tile ψηλό, άρα
;       δεν προεξέχει κατακόρυφα και ο οριζόντιος το σκεπάζει.
;
;   διαγώνιος -> ΚΑΘΕΤΟΣ: η διαγώνιος σταματά ΕΝΑ βήμα νωρίτερα, στο S-1. Αν
;       πήγαινε ως το S, το πλακίδιο — δύο tiles φαρδύ — θα προεξείχε μισό
;       tile δεξιά από μια λωρίδα που είναι μισό tile φαρδιά, και η ουρά θα
;       φαινόταν. Και οι δύο επιλογές βγήκαν ΚΟΙΤΑΖΟΝΤΑΣ, όχι από τύπο.
;
; ΟΧΙ ΠΑΝΩ ΑΠΟ 63 TILES (βήμα 81). Δύο θόλοι που απέχουν 64 tiles ή
; περισσότερο σε έναν άξονα δεν παίρνουν διάδρομο, και το cr_far το λέει. Τα
; κέντρα είναι μισά tiles, -128..127, και η διαφορά τους σε 8 bits αναδιπλωνόταν:
; η διαδρομή σχεδιαζόταν ΑΝΑΠΟΔΑ, και όση έμενε στον κόσμο περνούσε τον έλεγχο
; και έδενε τους δύο θόλους στον γράφο με διάδρομο που δεν φτάνει στον b. Ο
; κανόνας είναι συμμετρικός — και το -64, που χωρά σε 8 bits, είναι μακριά —
; ώστε να μην εξαρτάται από το ποιος θόλος διαλέχτηκε πρώτος.
;
; ΠΟΤΕ ΔΕΝ ΥΠΑΡΧΕΙ ΔΙΑΔΡΟΜΗ. Η στροφή τρώει |S-T| tiles στον άξονα που μένει
; και ο θόλος προορισμού τρώει την ακτίνα του· αν δεν μένει ούτε ένα πλακίδιο,
; απορρίπτεται. Δοκιμάζονται ΚΑΙ ΟΙ ΔΥΟ μεριές — η διαγώνιος αγκυρώνεται σε
; όποιον θόλο ξεκινά — αλλά μια ζώνη «σχεδόν διαγώνιο» μένει αδρομολόγητη.
; Είναι όριο της τέχνης: χωρίς sprite γωνίας δεν υπάρχει σχήμα να την καλύψει.
;
; Η αναφορά σε Python είναι το tools/route.py και η δοκιμή τα συγκρίνει.

; ---------------------------------------------------------------------------
; cr_plan — διαδρομή ανάμεσα στους θόλους (cr_a) και (cr_b).
; Out: A = πλήθος τρεξιμάτων (0 = δεν υπάρχει), με Z αν A = 0 (το ln_plan
; το διαβάζει)· (cr_from) ο θόλος αφετηρίας,
; (cr_to) ο προορισμός. Χαλάει τα πάντα. Επιστρέφει με την τράπεζα 1.
;
; ΤΟ cr_from ΕΙΝΑΙ ΤΟ cr_a (βήμα 72). Κάθε άκρο είναι μία εγγραφή τεσσάρων
; bytes — θόλος, cx, cy, μέγεθος — και αν η διαδρομή δεν βγαίνει από τον a, οι
; δύο εγγραφές αλλάζουν θέση και δοκιμάζεται ο b. Ως το βήμα 71 οι θέσεις
; διαβάζονταν σε τρίτο ζεύγος και αντιγράφονταν σε κάθε μεριά.
; ---------------------------------------------------------------------------
cr_plan:
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        ld      a,(cr_a)
        ld      de,cr_fx
        call    cr_read
        jr      c,crp_out
        ld      a,(cr_b)
        inc     de                      ; cr_tx
        call    cr_read
        jr      c,crp_out
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
; cr_pair — το ίδιο, με τα δύο άκρα ήδη στο cr_a, cr_b (src/link.asm: το άκρο
; a είναι ο κέρσορας). Μέσα στο cr_plan, για να βρίσκουν το crs_far και το
; crs_sym την ίδια στοίβα.
cr_pair:
        call    cr_side
        ld      a,(cr_n)
        or      a
        ret     nz
        ; --- και μετά από τον b: η διαγώνιος αγκυρώνεται στον ΘΟΛΟ ΑΦΕΤΗΡΙΑΣ,
        ; οπότε οι δύο κατευθύνσεις δεν είναι η ίδια ερώτηση.
        ld      hl,cr_a
        ld      de,cr_b
        ld      b,4
crp_sw:
        ld      a,(de)
        ld      c,(hl)
        ld      (hl),a
        ld      a,c
        ld      (de),a
        inc     hl
        inc     de
        djnz    crp_sw
        call    cr_side
        ld      a,(cr_n)
        or      a
        ret     nz
        ld      (cr_far),a              ; καμία από τις δύο: το σχήμα
        ret
crp_out:
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        xor     a
        ld      (cr_n),a
        ld      (cr_far),a
        ret

; cr_read — A = κόμβος, DE = πού (cx, cy, size). CY αν η θέση είναι άδεια,
; αλλιώς DE += 3. Απαιτεί τράπεζα 6.
;
; ΚΑΙ ΤΟ AIRLOCK (βήμα 86): κόμβος 64 + δομή, μέγεθος AIRLOCK = 255. Καμία άλλη
; δομή δεν είναι άκρο διαδρόμου, και για αυτές το CY λέει «όχι».
cr_read:
        cp      MAX_DOME
        jr      nc,crd_st
        push    de                      ; το ob_domeadr ΧΑΛΑΕΙ το DE
        call    ob_domeadr
        pop     de
        ; ΠΡΩΤΑ Η ΑΝΤΙΓΡΑΦΗ, ΜΕΤΑ Η ΚΑΤΑΣΤΑΣΗ (βήμα 86): τρία ldi φέρνουν το HL
        ; ένα byte πριν από το D_STATE, και ένα άδειο άκρο το αγνοούν όλοι οι
        ; καλούντες. 56 T λιγότερα ανά ανάγνωση — όσο κόστισαν οι έλεγχοι του
        ; airlock στο cr_side και εδώ, και το cr_plan μένει όσο ήταν.
        ldi
        ldi
        ldi                             ; cx, cy, size
        inc     hl                      ; D_STATE
        ld      a,(hl)
        sub     1                       ; CY μόνο για DS_EMPTY
        ret
        assert  D_CX == 0 && D_CY == 1 && D_SIZE == 2 && D_STATE == 4
crd_st:
        add     a,a
        add     a,a
        add     a,a                     ; (64 + δομή) x 8 = δομή x 8 σε 8 bits
        ld      l,a
        ld      h,G_struct_tbl >> 8     ; μία σελίδα (assert πιο κάτω)
        ld      a,(hl)                  ; ST_CX
        ld      (de),a
        inc     hl
        inc     de
        ld      a,(hl)                  ; ST_CY
        ld      (de),a
        inc     hl
        inc     de
        ld      a,(hl)                  ; ST_KIND
        cp      K_AIRLOCK
        scf
        ret     nz
        inc     hl
        inc     hl                      ; ST_STATE
        ld      a,(hl)
        sub     1                       ; CY μόνο για DS_EMPTY
        ret     c
        ld      a,AIRLOCK
        ld      (de),a
        inc     de
        ret                             ; NC από το sub

        assert  STRUCT_REC == 8 && ST_CX == 0 && ST_CY == 1 && ST_KIND == 2 && ST_STATE == 4
        assert  (G_struct_tbl & 255) == 0 && MAX_STRUCT * STRUCT_REC == 256 && MAX_DOME == 64

; crs_far / crs_sym — οι δύο αποτυχίες που ΔΕΝ εξαρτώνται από το ποιος θόλος
; είναι η αφετηρία: 64 tiles ή περισσότερο σε έναν άξονα (cr_far = 1, για τον
; πίνακα: ln_plan, uip_ln), και διαφορά που δεν πέφτει στο πλέγμα. Η άλλη
; μεριά θα έλεγε το ίδιο, οπότε δεν ρωτιέται: η διεύθυνση επιστροφής στο
; cr_plan πετιέται και η απάντηση πάει κατευθείαν σε όποιον το κάλεσε, με
; A = 0 και cr_n = 0 (το cr_side το μηδενίζει πρώτο). Το cr_far γράφεται μόνο
; όταν δεν υπάρχει διαδρομή, και μόνο τότε λέει κάτι.
crs_far:
        ld      a,1
        jr      crs_out
crs_sym:
        xor     a
crs_out:
        ld      (cr_far),a
        pop     hl                      ; το cr_plan: η άλλη μεριά δεν ρωτιέται
        xor     a
        ret

; ---------------------------------------------------------------------------
; cr_side — διαδρομή που ΞΕΚΙΝΑ από τον (cr_fx, cr_fy, cr_fs).
; Out: (cr_n), και τα (cr_d0, cr_l0, cr_d1, cr_l1).
; ---------------------------------------------------------------------------
cr_side:
        xor     a
        ld      (cr_n),a
        ; --- διαφορές σε tiles. Τα κέντρα είναι σε ΖΥΓΑ μισά tiles (§3.4),
        ; άρα η διαφορά τους είναι ακέραιο πλήθος tiles· αν όχι, δεν πέφτει
        ; στο πλέγμα και δεν υπάρχει διαδρομή: το sra το λέει στο CY.
        ;
        ; Το |Δ| και το πρόσημο γράφονται εδώ, όχι με κλήση, και οι ακτίνες το
        ; ίδιο (βήμα 81): οι δύο κλήσεις του καθενός πλήρωναν τον έλεγχο της
        ; απόστασης, και το cr_side μένει πιο γρήγορο από πριν.
        ld      a,(cr_tx)
        ld      hl,cr_fx
        sub     (hl)
        jp      pe,crs_far              ; |Δ| >= 128 μισά tiles: αναδιπλωνόταν
        sra     a
        jr      c,crs_sym               ; δεν πέφτει στο πλέγμα
        ld      c,0
        or      a
        jr      z,crs_x
        ld      c,1                     ; ld, όχι inc: οι σημαίες είναι του A
        jp      p,crs_x
        ld      c,-1
        neg
crs_x:
        ld      (cr_ds),a
        ld      a,c
        ld      (cr_ux),a
        ld      a,(cr_ty)
        inc     hl                      ; cr_fy
        sub     (hl)
        jp      pe,crs_far
        sra     a
        jr      c,crs_sym
        ld      c,0
        or      a
        jr      z,crs_y
        ld      c,1
        jp      p,crs_y
        ld      c,-1
        neg
crs_y:
        ld      (cr_dt),a
        ld      a,c
        ld      (cr_uy),a
        ; --- ακτίνες σε tiles, size + 2 = 2/3/4, και DIAG_K, το βήμα όπου ο
        ; δακτύλιος ξεφεύγει: 2 για το S, 3 αλλιώς. Ως το βήμα 71 ήταν δύο
        ; πίνακες και τέσσερις αναζητήσεις, ως το 80 μια ρουτίνα με δύο κλήσεις.
        ld      a,(cr_fs)
crs_rk:
        ; ΑΠΟ AIRLOCK ΔΕΝ ΞΕΚΙΝΑ ΤΙΠΟΤΑ (βήμα 86): οι πόρτες του είναι βόρεια
        ; και νότια, και καμία διαγώνιος δεν βγαίνει από εκεί. Ο κάθετος
        ; βρίσκεται από την άλλη μεριά, από τον θόλο, που τον ζωγραφίζει. Εδώ
        ; και όχι στην είσοδο: το add a,2 γίνεται δύο inc, και ο έλεγχος κοστίζει
        ; 6 T αντί για 22 (το tests/test_corridor.py μετρά το cr_plan).
        inc     a                       ; AIRLOCK = 255 -> 0
        ret     z
        inc     a                       ; = size + 2
        ld      (cr_ra),a
        sub     3                       ; CY μόνο για το S
        ld      a,3
        sbc     a,0
        ld      (cr_ka),a
        ld      a,(cr_ts)
        add     a,2
        ld      (cr_rb),a
        sub     3
        ld      a,3
        sbc     a,0
        ld      (cr_kb),a
        ; --- ποια περίπτωση; ---
        ld      hl,cr_dt
        ld      a,(cr_ds)
        ld      b,a                     ; S
        or      (hl)
        ret     z                       ; ο ίδιος θόλος
        ; ΚΑΙ ΤΟ -64, που χωρά σε 8 bits: χωρίς αυτό ο κανόνας θα εξαρτιόταν
        ; από το ποιος θόλος είναι ο a. S, T <= 64, άρα το bit 6 του S | T
        ; ανάβει μόνο όταν ένα από τα δύο είναι 64.
        bit     6,a
        jp      nz,crs_far
        ld      c,a                     ; S | T: το μήκος, όταν το άλλο είναι 0
        ld      a,b
        or      a
        jr      z,crs_axial
        ; ΣΕ AIRLOCK ΜΟΝΟ ΚΑΘΕΤΑ: ο κάθετος αξονικός πέρασε πιο πάνω (S = 0),
        ; και από τα σχήματα με διαγώνιο μόνο η στροφή σε κάθετο (T > S).
        ld      a,(cr_ts)
        inc     a
        jr      nz,crs_case
        ld      a,(hl)                  ; T
        cp      b
        ret     c
        ret     z
        jr      crs_vert
crs_case:
        ld      a,(hl)                  ; T
        or      a
        jr      z,crs_axial
        cp      b
        jr      z,crs_diag
        jr      nc,crs_vert             ; S < T: διαγώνιος, μετά κάθετος
        ; fall through — T < S: διαγώνιος, μετά οριζόντιος

; --- διαγώνιος + οριζόντιος ------------------------------------------------
crs_horz:
        ld      de,(cr_ds)              ; E = S, D = T
        ld      a,(cr_ux)
        ld      c,a                     ; το δεύτερο τρέξιμο: (ux, 0)
        ld      b,0
        ld      a,d
        inc     a                       ; n1 = T - ka + 1
        jr      crs_bend

; --- διαγώνιος + κάθετος ---------------------------------------------------
crs_vert:
        ld      de,(cr_ds)
        ld      a,e
        ld      e,d                     ; E = T
        ld      d,a                     ; D = S
        ld      a,(cr_uy)
        ld      b,a                     ; το δεύτερο τρέξιμο: (0, uy)
        ld      c,0
        ld      a,d                     ; n1 = S - ka
        ; fall through

; crs_bend — οι δύο στροφές είναι ΕΝΑΣ τύπος (βήμα 72), με m = min(S, T):
;
;   n1 = m - ka, +1 όταν η στροφή είναι σε οριζόντιο (ο A στην είσοδο)
;   n2 = max(S, T) - m - rb + 1
;   και το πρώτο πλακίδιο του άξονα δεν γυρίζει μέσα στον a: απέχει από το
;   κέντρο m - 1 tiles αν ο άξονας πηγαίνει προς τα θετικά, m αν όχι, και
;   αυτό πρέπει να είναι τουλάχιστον ra.
;
; D = m, E = max, B/C = uy/ux του δεύτερου τρεξίματος.
crs_bend:
        ld      hl,cr_ka
        sub     (hl)
        ret     m
        ret     z
        ld      (cr_l0),a
        ld      a,e
        sub     d
        dec     hl                      ; cr_rb
        sub     (hl)
        inc     a
        ret     m
        ret     z
        ld      (cr_l1),a
        ld      a,b
        or      c                       ; ο άξονας: +1 ή -1
        dec     a                       ; Z αν προς τα θετικά
        ld      a,d
        jr      nz,crs_bm
        dec     a
crs_bm:
        dec     hl                      ; cr_ra
        cp      (hl)
        ret     c                       ; θα έστριβε μέσα στον a
        ld      a,b
        call    cr_dir
        ld      (cr_d1),a
        ld      a,2
        jr      crs_set

; --- καθαρή διαγώνιος: n = S - ka - kb + 1 ----------------------------------
crs_diag:
        ld      a,b
        ld      hl,cr_ka
        sub     (hl)
        inc     hl                      ; cr_kb
        sub     (hl)
        inc     a
        jr      crs_one

; --- καθαρά αξονικός: n = S|T - ra - rb (ο ένας από τους δύο είναι μηδέν) ----
crs_axial:
        ld      a,c
        ld      hl,cr_ra
        sub     (hl)
        inc     hl                      ; cr_rb
        sub     (hl)
crs_one:
        ret     m
        ret     z
        ld      (cr_l0),a
        ld      a,1
crs_set:
        ld      (cr_n),a
        call    cr_diagdir
        ld      (cr_d0),a
        ret

; cr_diagdir — η κατεύθυνση από τα (cr_ux, cr_uy).
cr_diagdir:
        ld      a,(cr_ux)
        ld      c,a
        ld      a,(cr_uy)
        ; fall through

; cr_dir — A = uy, C = ux (και τα δύο -1, 0 ή 1) -> A = κατεύθυνση 0..7.
; Χαλάει B, HL.
cr_dir:
        ld      b,a
        add     a,a
        add     a,b
        add     a,c                     ; 3uy + ux, -4..4
        add     a,(cr_dtab + 4) & 255
        ld      l,a
        ld      h,cr_dtab >> 8          ; >> και όχι / : ο rasm στρογγυλεύει
        ld      a,(hl)                  ; το / (#23F5 / 256 = #24, στο uitest)
        ret

; ---------------------------------------------------------------------------
; cr_redraw — ο διάδρομος που μόλις μπήκε: τα tiles του, και οι δύο αρμοί.
; Απαιτεί έγκυρη διαδρομή (cr_n): καλείται αμέσως μετά το cr_commit.
; Out: NZ αν έμειναν σειρές στη λίστα αλλαγών (rv_pend) — τότε ο καλών χρωστά
; το φάντασμα, όπως μετά από θόλο (§6.9).
;
; Η ΔΙΑΓΩΝΙΟΣ ΣΕΙΡΑ-ΣΕΙΡΑ (βήμα 37). Το περίγραμμα μιας διαγωνίου n βημάτων
; είναι τετράγωνο n x n, και μια διαγώνιος 7 βημάτων ξαναζωγράφιζε 64 tiles
; σε έναν γύρο — 130 ms, 220 ο γύρος όλος — για να αλλάξει μια γραμμή. Τώρα
; κάθε σειρά της είναι μία DK_CROW: τα τρία tiles που αγγίζουν τα δύο
; πλακίδια της σειράς, μία σειρά ανά γύρο. Ο αξονικός κομμάτι είναι ήδη
; λεπτό ορθογώνιο και ζωγραφίζεται αμέσως, όπως πριν.
;
; ΤΟ ΠΕΡΙΓΡΑΜΜΑ ΤΗΣ ΔΙΑΔΡΟΜΗΣ ΧΩΡΙΣ ΠΕΡΙΘΩΡΙΟ, και οι αρμοί από τη λίστα
; αλλαγών (DK_CONN, crr_conns στο src/ui.asm). Στο βήμα 34 το περίγραμμα
; είχε ένα tile περιθώριο για τις πόρτες, που κάθονταν στους δακτυλίους — και
; αυτό το tile ξαναζωγράφιζε μια ολόκληρη στήλη από κάθε θόλο: 48 από τα 180
; ms. Από το 96 ο διάδρομος σταματά στο εξωτερικό χείλος του δακτυλίου, κάτω
; από το κέλυφος, και μπαίνει ένα pixel μέσα με τον αρμό (src/joint.asm): ως
; το 95 εδώ ήταν οι πόρτες, που άνοιγαν τον δακτύλιο ως τον εσωτερικό κύκλο.
; ---------------------------------------------------------------------------
cr_redraw:
        call    crr_conns
        ld      a,(cr_d0)
        rrca
        jr      c,crr_diag
        ; --- αξονικός: όλη η διαδρομή σε ένα ορθογώνιο ---
        ld      hl,cr_walk
        call    crr_box
        xor     a                       ; Z: τίποτα δεν περιμένει
        ret
crr_diag:
        call    crr_rows
        ld      a,(cr_n)
        cp      2
        jr      c,crr_pend
        ; --- η στροφή: το αξονικό τρέξιμο, μόνο του ---
        call    crw_base
        ld      hl,cr_walk1
        call    crr_box
crr_pend:
        ld      a,(rv_pend)
        or      a
        ret

; crr_rows — μία DK_CROW για κάθε σειρά της διαγωνίου που φαίνεται στο κάδρο.
;
; Τα δύο tiles του πλακιδίου j είναι οι δύο διαγώνιες γωνίες του τετραγώνου
; 2x2 γύρω από το σημείο πλέγματος (ux*j, uy*j). Μια σειρά της διαγωνίου την
; πατούν δύο διαδοχικά πλακίδια, και οι στήλες τους είναι ΤΡΕΙΣ: από τη στήλη
; του πρώτου tile της σειράς στη σειρά tiles του cr_walk μείον ένα. Οι σειρές
; είναι l0 + 1, όσα και τα tiles της διαγωνίου, και προχωρούν μαζί τους. Οι
; αρμοί στους δακτυλίους (βήμα 96) δεν είναι σε αυτές: έρχονται χωριστά, ως
; DK_CONN (crr_conns, src/ui.asm).
crr_rows:
        call    crw_base
        call    crw_dg                  ; B, C = το πρώτο tile, E = uy
        dec     b                       ; τρεις στήλες, από την αριστερή
crrw_bs:                                ; (το tests/test_link.py σβήνει το dec b)
        ld      hl,(cr_btx)
        ld      a,b
        add     a,l
        ld      b,a
        ld      a,c
        add     a,h
        ld      c,a                     ; στον κόσμο
        ld      a,(cr_l0)
        inc     a
        ld      (cr_i),a
crrw_lp:
        ; ΜΟΝΟ Ο,ΤΙ ΦΑΙΝΕΤΑΙ. Μια σειρά έξω από το κάδρο θα την έκοβε ούτως ή
        ; άλλως το vr_clip, και μια μακριά διαγώνιος θα γέμιζε το δαχτυλίδι
        ; των 32. Αν η κάμερα κουνηθεί στο μεταξύ, ό,τι μπαίνει στο κάδρο το
        ; ζωγραφίζει ολόκληρο η λωρίδα του σκρολαρίσματος.
        ld      hl,cam_tx
        ld      a,b
        sub     (hl)
        add     a,2                     ; τρεις στήλες: φαίνεται από το -2
        cp      VIEW_TW + 2
        jr      nc,crrw_nx
        inc     hl                      ; cam_ty
        ld      a,c
        sub     (hl)
        cp      VIEW_TH
        jr      nc,crrw_nx
        ld      a,DK_CROW
        call    dirty_push              ; κρατά B, C, E
        ld      hl,rv_pend
        inc     (hl)
crrw_nx:
        ld      a,(cr_ux)
        add     a,b
        ld      b,a
        ld      a,c
        add     a,e
        ld      c,a
        ld      hl,cr_i
        dec     (hl)
        jr      nz,crrw_lp
        ret

; crr_box — το περίγραμμα των tiles που περπατά η ρουτίνα (HL), χωρίς
; περιθώριο, και view_add πάνω του.
crr_box:
        push    hl
        ld      hl,#00FF                ; min = +127, max = -128 (μετατοπισμένα)
        ld      (crr_x0),hl
        ld      (crr_y0),hl
        ld      hl,cr_cb_bb
        ld      (cr_cb),hl
        pop     hl
        call    crr_go
        ld      hl,(crr_x0)             ; L = min, H = max· η διαφορά τους δεν
        ld      a,l                     ; θέλει πίσω τη μετατόπιση
        xor     #80
        ld      (vr_tx),a
        ld      a,h
        sub     l
        inc     a
        ld      (vr_w),a
        ld      hl,(crr_y0)
        ld      a,l
        xor     #80
        ld      (vr_ty),a
        ld      a,h
        sub     l
        inc     a
        ld      (vr_h),a
; crr_half — ο αξονικός διάδρομος ΣΤΟ ΚΕΝΤΡΟ του θόλου (βήμα 96) πάει μισό
; πλάτος πίσω: 1 byte ο κάθετος, 4 γραμμές ο οριζόντιος. Οταν ο άξονας πέφτει
; σε όριο tile — ζυγό cx ή cy σε μισά tiles, 2*cx bytes ή 8*cy γραμμές — το
; μισό αυτό πατά τη στήλη αριστερά ή τη σειρά πάνω από τα tiles της διαδρομής,
; και μπαίνει στο ορθογώνιο. Ο άξονας είναι του b: ενός αξονικού είναι κοινός
; με τον a, μιας στροφής είναι η συνέχεια που φτάνει στον b.
crr_half:
        ld      a,(cr_n)
        cp      2
        ld      a,(cr_d0)
        jr      c,crh_d
        ld      a,(cr_d1)
crh_d:
        and     2                       ; e, w = 2, 6: οριζόντιος· n, s κάθετος
        rrca                            ; 0 = x, 1 = y
        ld      e,a
        ld      d,0
        ld      hl,cr_tx
        add     hl,de
        bit     0,(hl)
        jp      nz,view_add             ; μονό: όλος μέσα στη στήλη ή στη σειρά
        ld      hl,vr_tx
        add     hl,de
        dec     (hl)                    ; μία στήλη ή σειρά νωρίτερα
        inc     hl
        inc     hl                      ; vr_w ή vr_h
        inc     (hl)
        jp      view_add                ; ο διάδρομος μόνο προσθέτει
crr_go:
        jp      (hl)

; cr_cb_bb — ένα tile της διαδρομής μεγαλώνει το περίγραμμα. B, C μένουν.
cr_cb_bb:
        ld      hl,crr_x0
        ld      a,b
        call    crr_mm
        ld      a,c
        ; fall through, με το HL στο crr_y0
; crr_mm — A = προσημασμένο· (HL) = ελάχιστο, (HL+1) = μέγιστο, μετατοπισμένα
; κατά 128 ώστε η σύγκριση χωρίς πρόσημο να είναι σωστή. HL += 2.
crr_mm:
        xor     #80
        cp      (hl)
        jr      nc,crrm_lo
        ld      (hl),a
crrm_lo:
        inc     hl
        cp      (hl)
        jr      c,crrm_hi
        ld      (hl),a
crrm_hi:
        inc     hl
        ret

crr_x0:     db 0
crr_x1:     db 0
crr_y0:     db 0
crr_y1:     db 0

; ---------------------------------------------------------------------------
; cr_walk — καλεί την (cr_cb) μία φορά για κάθε tile της διαδρομής, με
; B = tile x, C = tile y (προσημασμένα, συντεταγμένες κόσμου).
;
; Το διαγώνιο πλακίδιο πατά ΔΥΟ tiles, όχι τέσσερα: η γραμμή του περνά από τις
; δύο απέναντι γωνίες του τετραγώνου 2x2 που καλύπτει, και τα άλλα δύο μόνο τα
; ακουμπά. Δύο διαδοχικά μοιράζονται το ένα, οπότε μια διαγώνιος n βημάτων
; είναι n + 1 tiles.
;
; ΚΑΘΕ TILE ΜΙΑ ΦΟΡΑ. Ως το βήμα 37 το κοινό tile περνούσε δύο φορές, και το
; φάντασμα ζωγράφιζε το σημάδι του δύο φορές — η αναίρεση, που πάει μπροστά,
; έγραφε τελευταίο το «φόντο» της δεύτερης εγγραφής, δηλαδή το πρώτο σημάδι,
; και ο κέρσορας άφηνε ίχνος.
;
; ΚΑΙ ΕΙΝΑΙ ΜΙΑ ΕΥΘΕΙΑ (βήμα 72). Το «μπροστινό» tile του πλακιδίου j είναι το
; «πίσω» του j + 1, άρα τα n + 1 tiles απέχουν κατά (ux, uy) το καθένα από το
; προηγούμενο: η διαγώνιος περνά από το cr_line, όπως οι άξονες. Ως το βήμα 71
; κάθε βήμα υπολόγιζε τα δύο tiles του πλακιδίου με δύο πολλαπλασιασμούς.
; ---------------------------------------------------------------------------
cr_walk:
        call    crw_base
        ld      a,(cr_d0)
        rrca
        jr      nc,crw_ax0              ; ζυγή κατεύθυνση = αξονικός
        ; --- τρέξιμο 0: διαγώνιος ---
        call    crw_dg
        ld      a,(cr_l0)
        inc     a
        call    cr_line
        ld      a,c                     ; το τελευταίο tile, για τη στροφή:
        sub     e                       ; το cr_line σταματά ένα βήμα μετά
        ld      l,a
        ld      a,b
        sub     d
        ld      h,a
        ld      (crw_ly),hl
        ld      a,(cr_n)
        cp      2
        ret     c
; cr_walk1 — μόνο το τρέξιμο 1, η στροφή. Απαιτεί το crw_base.
cr_walk1:
        ld      a,(cr_d1)
        and     3                       ; e και w είναι 2 και 6· n και s 0 και 4
        cp      2
        jr      nz,crw_v1
; Ο οριζόντιος από τη στήλη ux*T - (ux > 0), στη σειρά uy*T, βήμα (ux, 0).
crw_h1:
        ld      hl,cr_ux
        ld      a,(cr_dt)
        ld      e,a
        dec     a
        ld      c,a
        ld      d,(hl)
        call    crw_oz
        ld      b,a
        inc     hl                      ; cr_uy
        ld      a,e
        call    cr_mulsg
        ld      c,a
        ; ΟΤΑΝ Η ΔΙΑΓΩΝΙΟΣ ΑΝΕΒΑΙΝΕΙ, το ΠΡΩΤΟ tile του οριζόντιου είναι το
        ; «πίσω» του τελευταίου διαγώνιου πλακιδίου — δηλαδή ένα μπροστινό που
        ; έχει ήδη περάσει — και το τελευταίο μπροστινό δεν το αγγίζει (βήμα
        ; 40, μετρημένο σε όλες τις στροφές). Ως τότε το σημάδι του έμπαινε δύο
        ; φορές στο αρχείο του φαντάσματος και η αναίρεση άφηνε το ένα στην
        ; οθόνη: 8 bytes σε κάθε προεπισκόπηση ΒΑ->Α και ΒΔ->Δ.
        bit     7,(hl)
        jr      z,crw_h1s
        ld      (crw_ly),bc             ; C -> crw_ly, B -> crw_lx
crw_h1s:
        ld      e,0
        jr      crw_run1
; Ο κάθετος από τη σειρά uy*(S-1) - (uy < 0), στη στήλη ux*S, βήμα (0, uy).
crw_v1:
        ld      hl,cr_uy
        ld      a,(cr_ds)
        ld      b,a
        dec     a
        ld      c,a
        ld      e,(hl)
        call    crw_oz
        ld      c,a
        dec     hl                      ; cr_ux
        ld      a,b
        call    cr_mulsg
        ld      b,a
        ld      d,0
crw_run1:
        ld      a,(cr_l1)
        jr      cr_line

; --- τρέξιμο 0 αξονικό: από το σημείο σύνδεσης, προς τα έξω ---------------
; Από το ra (νότος, ανατολή) ή το -ra-1 (βορράς, δύση) στον άξονα της κίνησης,
; 0 στον άλλον. Χωρίς το crw_oz: εδώ είναι ο ένας από τους δύο, και οι δύο
; κλήσεις έκαναν τον αξονικό διάδρομο 8 µs πιο αργό από το βήμα 71.
crw_ax0:
        ld      hl,(cr_ux)              ; L = ux, H = uy
        ld      d,l
        ld      e,h
        ld      a,l
        or      h                       ; ο άξονας: +1 ή -1
        ld      a,(cr_ra)
        jp      p,crw_axp
        cpl
crw_axp:
        ld      b,a                     ; οριζόντιος...
        ld      c,0
        inc     l
        dec     l
        jr      nz,crw_axr
        ld      c,b                     ; ...ή κάθετος
        ld      b,0
crw_axr:
        ld      a,(cr_l0)
        jr      cr_line

; crw_dg — το πρώτο tile της διαγωνίου, το «πίσω» του πλακιδίου ka:
; B = ux*(ka-1) - (ux < 0), C = το ίδιο με το uy. D = ux, E = uy.
crw_dg:
        ld      hl,cr_ux
        ld      a,(cr_ka)
        dec     a
        ld      c,a
        ld      d,(hl)
        call    crw_oz
        ld      b,a
        inc     hl                      ; cr_uy
        ld      e,(hl)
        call    crw_oz
        ld      c,a
        ret

; crw_oz — (HL) = u (-1, 0, 1), C = k -> A = 0, k, ή ~k = -k-1.
crw_oz:
        ld      a,(hl)
        or      a
        ret     z
        ld      a,c
        ret     p
        cpl
        ret

; crw_base — η βάση των σχετικών συντεταγμένων: το tile του κέντρου του a.
; Και ξεχνά το τελευταίο tile της διαγωνίου (-128: δεν υπάρχει στον κόσμο).
crw_base:
        ld      hl,#8080
        ld      (crw_ly),hl
        ld      hl,(cr_fx)              ; L = cx, H = cy, σε μισά tiles
        sra     l
        sra     h
        ld      (cr_btx),hl
        ret

; cr_line — A πλακίδια από το (B, C) με βήμα (D, E).
cr_line:
        ld      (cr_i),a
crl_lp:
        push    bc
        push    de
        call    cr_emit
        pop     de
        pop     bc
        ld      a,b
        add     a,d
        ld      b,a
        ld      a,c
        add     a,e
        ld      c,a
        ld      hl,cr_i
        dec     (hl)
        jr      nz,crl_lp
        ret

; cr_emit — ένα tile: προσθέτει τη βάση και καλεί την (cr_cb).
;
; Ο ΟΡΙΖΟΝΤΙΟΣ ΤΗΣ ΣΤΡΟΦΗΣ ξεκινά ένα tile πίσω, πάνω στο τελευταίο διαγώνιο
; πλακίδιο, και όταν η διαγώνιος κατεβαίνει το δεύτερο tile του είναι το
; τελευταίο της διαγωνίου· όταν ανεβαίνει, το πρώτο του (crw_h1). Το ίδιο το
; πρώτο tile του κάθετου όταν η διαγώνιος πάει δυτικά. Δεύτερη φορά δεν
; περνιέται (crw_lx).
cr_emit:
        ld      a,(crw_lx)
        cp      b
        jr      nz,cre_go
        ld      a,(crw_ly)
        cp      c
        ret     z
cre_go:
        ld      hl,(cr_btx)
        ld      a,l
        add     a,b
        ld      b,a
        ld      a,h
        add     a,c
        ld      c,a
        ld      hl,(cr_cb)
        jp      (hl)

; cr_mulsg — A = |k|, (HL) = πρόσημο -> A = πρόσημο * k.
cr_mulsg:
        bit     7,(hl)
        ret     z
        neg
        ret

; (uy+1)*3 + (ux+1) -> κατεύθυνση
cr_dtab:    db 7,0,1
            db 6,255,2
            db 5,4,3

; Τα δύο άκρα, μία εγγραφή τεσσάρων bytes το καθένα: θόλος, cx, cy, μέγεθος.
cr_a:
cr_from:    db 0
cr_fx:      db 0
cr_fy:      db 0
cr_fs:      db 0
cr_b:
cr_to:      db 0
cr_tx:      db 0
cr_ty:      db 0
        assert  cr_ty == cr_tx + 1      ; crr_half
cr_ts:      db 0
cr_n:       db 0
cr_far:     db 0                        ; όταν cr_plan = 0: 1 αν οι θόλοι απέχουν
                                        ; >= 64 tiles σε έναν άξονα (βήμα 81)
cr_d0:      db 0
cr_l0:      db 0
cr_d1:      db 0
cr_l1:      db 0
cr_ds:      db 0                        ; |Δx| σε tiles
cr_dt:      db 0                        ; |Δy| σε tiles
cr_ux:      db 0
cr_uy:      db 0
cr_ra:      db 0
cr_rb:      db 0
cr_ka:      db 0
cr_kb:      db 0
cr_btx:     db 0
cr_bty:     db 0
cr_i:       db 0
cr_cb:      dw 0
crw_ly:     db 0                        ; το τελευταίο tile της διαγωνίου,
crw_lx:     db 0                        ; σχετικό (y, x) — #80 = κανένα

        assert  cr_b == cr_a + 4 && cr_tx == cr_fx + 4 && cr_fy == cr_fx + 1
        assert  cr_fx == cr_a + 1 && cr_ty == cr_tx + 1 && cr_ts == cr_tx + 2
        assert  cr_l0 == cr_d0 + 1 && cr_d1 == cr_d0 + 2 && cr_l1 == cr_d0 + 3
        assert  cr_dt == cr_ds + 1 && cr_uy == cr_ux + 1
        assert  cr_rb == cr_ra + 1 && cr_ka == cr_ra + 2 && cr_kb == cr_ra + 3
        assert  cr_bty == cr_btx + 1 && crw_lx == crw_ly + 1
        assert  (cr_dtab & 255) + 8 < 256       ; cr_dir: ένα byte διεύθυνσης

; ---------------------------------------------------------------------------
; cr_check — περπατά τη διαδρομή και μετρά τα tiles που δεν επιτρέπονται.
; Out: A = πλήθος κακών tiles (0 = επιτρέπεται). Απαιτεί έγκυρη (cr_n).
; ---------------------------------------------------------------------------
cr_check:
        xor     a
        ld      (cr_bad),a
        ld      hl,cr_cb_chk
        call    crw_b4
        ld      a,(cr_bad)
        ret

; cr_cb_chk — ένα tile. Απαιτεί τράπεζα 4.
;
; ΤΟ ΑΠΟΤΥΠΩΜΑ ΤΩΝ ΔΥΟ ΑΚΡΩΝ ΕΙΝΑΙ ΤΟΥ ΔΙΑΔΡΟΜΟΥ. Η διαγώνιος ξεκινά DIAG_K
; βήματα από το κέντρο — εκεί που ξεφεύγει ο ΚΥΚΛΙΚΟΣ δακτύλιος — και τα
; πρώτα της tiles είναι η γωνία του ΤΕΤΡΑΓΩΝΟΥ αποτυπώματος, που το bd_commit
; σφράγισε κατειλημμένη. Ως το βήμα 36 ο έλεγχος τη μετρούσε κακή: κανένας
; διάδρομος με διαγώνιο δεν χτιζόταν ανάμεσα σε θόλους του παίκτη (ένα tile
; για S και M, δύο για L, και άλλα τόσα στον προορισμό μιας καθαρής
; διαγωνίου). Μέσα σε ένα αποτύπωμα δεν πατά τίποτε άλλο εκτός από τον ίδιο
; τον θόλο, οπότε εκεί δεν έχει τι να ελέγξει η κατοχή· το αν το πλακίδιο
; πέφτει πάνω στον δακτύλιο το αποφασίζει η γεωμετρία του cr_side.
;
; Εξω από τον κόσμο είναι ένα από τα δύο (B + 64, C + 64) με το bit 7: το
; πρόσημο του OR τους τα πιάνει μαζί.
cr_cb_chk:
        ld      a,b
        add     a,64
        ld      e,a
        ld      a,c
        add     a,64
        or      e
        jp      m,crk_bad               ; έξω από τον κόσμο
        call    tile_addr               ; κρατά τα BC
        ld      a,(hl)
        call    bd_ok                   ; κι αυτό
        ret     z
        ld      hl,cr_fx
        call    crk_in
        ret     c                       ; η γωνία του θόλου αφετηρίας
        ld      hl,cr_tx
        call    crk_in
        ret     c                       ; ή του θόλου προορισμού
crk_bad:
        ld      hl,cr_bad
        inc     (hl)
        ret

; crk_in — HL -> (cx, cy, size) ενός άκρου, κέντρο σε μισά tiles. CY αν το
; tile (B, C) είναι μέσα στο αποτύπωμά του: B - (cx/2 - r) < 2r, χωρίς
; πρόσημο, και το ίδιο για το C. Η ακτίνα σε tiles είναι size + 2. Χαλάει
; A, DE, HL.
crk_in:
        inc     hl
        inc     hl
        ld      a,(hl)
        add     a,2                     ; r
        dec     hl
        dec     hl
        ld      e,a
        add     a,a
        ld      d,a                     ; 2r
        ld      a,(hl)
        sra     a
        neg
        add     a,b
        add     a,e
        cp      d
        ret     nc
        inc     hl
        ld      a,(hl)
        sra     a
        neg
        add     a,c
        add     a,e
        cp      d
        ret

; ---------------------------------------------------------------------------
; cr_stamp — τα tiles της διαδρομής γίνονται δεσμευμένα.
;
; ΟΧΙ θεμέλιο, σε αντίθεση με τον θόλο (§6.9): ο διάδρομος είναι μια λωρίδα
; μισού tile πάνω στο έδαφος, και το να γίνει σκυρόδεμα ολόκληρη η διαγώνιος
; θα έβαφε τέσσερις φορές περισσότερο απ' όσο πατά. Η κατοχή όμως μπαίνει —
; αλλιώς χτίζεται θόλος πάνω σε διάδρομο.
; ---------------------------------------------------------------------------
cr_stamp:
        ld      hl,cr_cb_stp
; crw_b4 — HL = callback: η διαδρομή με την τράπεζα 4 στο παράθυρο.
crw_b4:
        ld      (cr_cb),hl
        ld      bc,GA_PORT + PAGE_B4
        out     (c),c
        call    cr_walk
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        ret

cr_cb_stp:
        ld      a,b
        add     a,64
        ld      e,a
        ld      a,c
        add     a,64
        or      e
        ret     m                       ; έξω από τον κόσμο
        call    tile_addr
        set     4,(hl)                  ; W_OCC_STRUCT
        ret

        assert  W_OCC_STRUCT == 1 << 4

; ---------------------------------------------------------------------------
; cr_cost — το συνολικό κόστος σε (cr_metal, cr_biop), 16 bit. Out: HL =
; (cr_metal).
; Ο κατάλογος δίνει την τιμή ΑΝΑ ΠΛΑΚΙΔΙΟ: ένας διάδρομος δέκα πλακιδίων
; κοστίζει δέκα φορές όσο ένας του ενός, που είναι και το μόνο που βγάζει
; νόημα όταν το μήκος το διαλέγει η γεωμετρία και όχι ο παίκτης.
; ---------------------------------------------------------------------------
cr_cost:
        ld      hl,cr_l0
        ld      a,(cr_n)
        cp      2
        ld      a,(hl)
        jr      c,crc_one
        inc     hl
        inc     hl                      ; cr_l1
        add     a,(hl)
crc_one:
        ld      hl,(bd_metal)           ; L = μέταλλο, H = βιοπλαστικό
        push    hl
        ld      c,h
        call    ob_mul                  ; HL = A * C· το A μένει (οκτώ rlca)
        ld      (cr_biop),hl
        pop     hl
        ld      c,l
        call    ob_mul
        ld      (cr_metal),hl
        ret

; cr_pcs — A = τα πλακίδια της διαδρομής, και των δύο τρεξιμάτων. Για το
; src/link.asm· το cr_cost έχει το ίδιο μέσα του, γιατί μια κλήση εκεί
; κόστιζε 7 µs σε κάθε afford του LINK (tests/test_corridor.py).
cr_pcs:
        ld      hl,cr_l0
        ld      a,(cr_n)
        cp      2
        ld      a,(hl)
        ret     c
        inc     hl
        inc     hl                      ; cr_l1
        add     a,(hl)
        ret

        assert  bd_biop == bd_metal + 1

; cr_afford — Z και A = 0 αν φτάνουν τα υλικά για ολόκληρη τη διαδρομή, NZ
; και A = 1 αν όχι. Το μέταλλο πρώτα, όπως ως το βήμα 71: το κόστος του είναι
; ήδη στο HL, και ένα «λείπει» βγαίνει χωρίς να κοιτάξει το βιοπλαστικό.
cr_afford:
        call    cr_cost
; cra_tot — HL = μέταλλο, (cr_biop) = βιοπλαστικό: το σύνολο του al_plan.
cra_tot:
        ex      de,hl
        ld      hl,(EC_STOCK + S_METAL*2)
        or      a
        sbc     hl,de
        jr      c,cra_no
        ld      hl,(EC_STOCK + S_BIOPL*2)
        ld      de,(cr_biop)
        sbc     hl,de                   ; NC από πριν
        jr      c,cra_no
        xor     a
        ret
cra_no:
        xor     a
        inc     a                       ; A = 1, NZ, NC (οι σημαίες του or a)
        ret

; ---------------------------------------------------------------------------
; cr_commit — γράφει τη διαδρομή στον πίνακα διαδρόμων.
; Out: A = 0 αν μπήκε, 1 αν δεν βρέθηκε θέση.
;
; ΔΥΟ ΕΓΓΡΑΦΕΣ ΓΙΑ ΜΙΑ ΔΙΑΔΡΟΜΗ. Η εγγραφή του §6.1 κρατά ΕΝΑ τρέξιμο
; (a, b, dir, len, state) και η στροφή θέλει δύο. Η δεύτερη γράφεται με
; C_A = 255 — «συνεχίζει την προηγούμενη» — ώστε:
;   * ο γράφος να την αγνοεί (μία ακμή, όχι δύο),
;   * ο renderer να τη ζωγραφίζει μαζί με την πρώτη, από εκεί που εκείνη
;     σταμάτησε, χωρίς να ξέρει τίποτε για δρομολόγηση.
; Οι δύο εγγραφές πρέπει να είναι ΔΙΠΛΑΝΕΣ, γι' αυτό η αναζήτηση θέλει δύο
; συνεχόμενες άδειες.
;
; ΜΠΑΙΝΕΙ ΩΣ DS_ACTIVE, όχι DS_BUILDING. Ο πίνακας εργασιών του §6.7 δείχνει
; σε ΚΟΜΒΟ, και ο διάδρομος είναι ακμή: δεν υπάρχει κόμβος να δημοσιευτεί η
; εργασία Build. Ενας διάδρομος που χτίζεται θα ήθελε είτε δικό του id κόμβου
; είτε νέο είδος εργασίας — και τα δύο είναι αλλαγή στο §6.7, όχι εδώ.
; ---------------------------------------------------------------------------
cr_commit:
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        ld      hl,G_corr_tbl + C_CSTATE
        ld      de,CORR_REC
        ld      b,MAX_CORR
crm_find:
        ld      a,(hl)
        or      a
        jr      nz,crm_next
        ld      a,(cr_n)
        cp      2
        jr      c,crm_got               ; ένα τρέξιμο: μία θέση αρκεί
        ld      a,b
        dec     a
        jr      z,crm_next              ; τελευταία θέση — δεν χωρά ζευγάρι
        push    hl
        add     hl,de
        ld      a,(hl)
        pop     hl
        or      a
        jr      z,crm_got
crm_next:
        add     hl,de
        djnz    crm_find
        ld      a,1
        jp      dt_end                  ; η 1 (src/dirty.asm)· το A μένει
crm_got:
        ld      de,(cr_d0)              ; E = d0, D = l0
        ld      a,(cr_from)
        ld      c,a
        ld      a,(cr_to)
        ld      b,a
        call    crm_put
        ld      a,(cr_n)
        cp      2
        jr      c,crm_done
        ld      de,CORR_REC + C_CSTATE
        add     hl,de
        ld      de,(cr_d1)              ; E = d1, D = l1
        ld      bc,#FFFF                ; C_A = 255: συνέχεια της προηγούμενης
        call    crm_put
crm_done:
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        call    cr_stampx               ; και το μισό tile στο κέντρο (src/ui.asm)
        call    cr_pay
        ; ΟΧΙ ΑΚΜΗ ΕΔΩ (βήμα 87). Στην τοποθέτηση (al_commit) η μία άκρη είναι
        ; πάντα το νέο εργοτάξιο, χωρίς αέρα: η ακμή γίνεται όταν τελειώσει
        ; (lk_done, src/door.asm). Μόνο το LINK ενώνει δύο θόλους που ίσως
        ; είναι ήδη έτοιμοι, και ρωτά — cr_commit_ln, πιο κάτω.
        ld      a,OB_IX_CORR            ; οι διάδρομοι (ως το 95 και οι πόρτες)
        call    ob_touch_a
        xor     a
        ret

; cr_commit_ln — το cr_commit του LINK (src/ui.asm): και αν οι δύο θόλοι είναι
; ήδη έτοιμοι, ο διάδρομος γίνεται ακμή αμέσως. A = 0 αν μπήκε, και Z μαζί
; (το uil_second το διαβάζει).
cr_commit_ln:
        call    cr_commit
        or      a
        ret     nz
        call    cr_lnk
        xor     a
        ret

; crm_put — HL -> C_CSTATE μιας εγγραφής· C = a, B = b, E = κατεύθυνση,
; D = μήκος. Γράφει από το τέλος προς την αρχή· HL -> η αρχή της.
crm_put:
        ld      (hl),DS_ACTIVE
        dec     hl
        ld      (hl),d
        dec     hl
        ld      (hl),e
        dec     hl
        ld      (hl),b
        dec     hl
        ld      (hl),c
        ret

        assert  C_A == 0 && C_B == 1 && C_DIR == 2 && C_LEN == 3 && C_CSTATE == 4

; cr_pay — αφαιρεί το κόστος ολόκληρης της διαδρομής.
cr_pay:
        call    cr_cost
        ex      de,hl
        ld      hl,(EC_STOCK + S_METAL*2)
        or      a
        sbc     hl,de
        ld      (EC_STOCK + S_METAL*2),hl
        ld      hl,(EC_STOCK + S_BIOPL*2)
        ld      de,(cr_biop)
        or      a
        sbc     hl,de
        ld      (EC_STOCK + S_BIOPL*2),hl
        ret

; cr_lnk — η ακμή, ΜΟΝΟ αν και οι δύο άκρες είναι έτοιμες (βήμα 87). Ενας
; διάδρομος προς εργοτάξιο δεν έχει αέρα στη μία του άκρη· γίνεται ακμή όταν
; τελειώσει το κτίσμα (lk_done, src/door.asm). Ως το cr_commit κόστιζε 133 us
; σε κάθε διάδρομο κάθε τοποθέτησης, για μια ερώτηση με γνωστή απάντηση.
cr_lnk:
        call    ob_b6
        ld      a,(cr_from)
        call    gr_live
        jr      nz,crl_no
        ld      a,(cr_to)
        call    gr_live
crl_no:
        call    dt_end                  ; η 1· οι σημαίες μένουν
        ret     nz
; ---------------------------------------------------------------------------
; cr_link — η ακμή μπαίνει στον γράφο κόμβων και ξαναχτίζεται η δρομολόγηση.
; Ο γράφος ζει στην τράπεζα 2, που είναι πάντα ορατή (§4.3).
; ---------------------------------------------------------------------------
cr_link:
        ld      a,(cr_from)
        ld      b,a
        ld      a,(cr_to)
        ld      c,a
        jp      cr_link_bc              ; src/edges.asm (βήμα 87)

cr_bad:     db 0
cr_metal:   dw 0
cr_biop:    dw 0
