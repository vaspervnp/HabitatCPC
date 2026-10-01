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
; ΠΟΤΕ ΔΕΝ ΥΠΑΡΧΕΙ ΔΙΑΔΡΟΜΗ. Η στροφή τρώει |S-T| tiles στον άξονα που μένει
; και ο θόλος προορισμού τρώει την ακτίνα του· αν δεν μένει ούτε ένα πλακίδιο,
; απορρίπτεται. Δοκιμάζονται ΚΑΙ ΟΙ ΔΥΟ μεριές — η διαγώνιος αγκυρώνεται σε
; όποιον θόλο ξεκινά — αλλά μια ζώνη «σχεδόν διαγώνιο» μένει αδρομολόγητη.
; Είναι όριο της τέχνης: χωρίς sprite γωνίας δεν υπάρχει σχήμα να την καλύψει.
;
; Η αναφορά σε Python είναι το tools/route.py και η δοκιμή τα συγκρίνει.

; ---------------------------------------------------------------------------
; cr_plan — διαδρομή ανάμεσα στους θόλους (cr_a) και (cr_b).
; Out: A = πλήθος τρεξιμάτων (0 = δεν υπάρχει)· (cr_from) ο θόλος αφετηρίας.
; Χαλάει τα πάντα. Επιστρέφει με την τράπεζα 1 στο παράθυρο.
; ---------------------------------------------------------------------------
cr_plan:
        xor     a
        ld      (cr_n),a
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        ld      a,(cr_a)
        ld      de,cr_pax
        call    cr_read
        jr      c,crp_out
        ld      a,(cr_b)
        ld      de,cr_pbx
        call    cr_read
        jr      c,crp_out
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        ; --- πρώτα από τον a ---
        ld      hl,cr_pax
        ld      de,cr_fx
        ld      bc,3
        ldir
        ld      hl,cr_pbx
        ld      de,cr_tx
        ld      bc,3
        ldir
        call    cr_side
        ld      a,(cr_n)
        or      a
        jr      z,crp_other
        ld      a,(cr_a)
        ld      (cr_from),a
        ld      a,(cr_b)
        ld      (cr_to),a
        ld      a,(cr_n)
        ret
crp_other:
        ; --- και μετά από τον b: η διαγώνιος αγκυρώνεται στον ΘΟΛΟ ΑΦΕΤΗΡΙΑΣ,
        ; οπότε οι δύο κατευθύνσεις δεν είναι η ίδια ερώτηση.
        ld      hl,cr_pbx
        ld      de,cr_fx
        ld      bc,3
        ldir
        ld      hl,cr_pax
        ld      de,cr_tx
        ld      bc,3
        ldir
        call    cr_side
        ld      a,(cr_n)
        or      a
        ret     z
        ld      a,(cr_b)
        ld      (cr_from),a
        ld      a,(cr_a)
        ld      (cr_to),a
        ld      a,(cr_n)
        ret
crp_out:
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        xor     a
        ret

; cr_read — A = θόλος, DE = πού (cx, cy, size). CY αν η θέση είναι άδεια.
; Απαιτεί τράπεζα 6.
cr_read:
        push    de                      ; το ob_domeadr ΧΑΛΑΕΙ το DE
        call    ob_domeadr
        push    hl
        ld      de,D_STATE
        add     hl,de
        ld      a,(hl)
        pop     hl
        pop     de
        or      a
        jr      z,crr_no
        ld      bc,3
        ldir
        or      a
        ret
crr_no:
        scf
        ret

; ---------------------------------------------------------------------------
; cr_side — διαδρομή που ΞΕΚΙΝΑ από τον (cr_fx, cr_fy, cr_fs).
; Out: A = (cr_n), και τα (cr_d0, cr_l0, cr_d1, cr_l1).
; ---------------------------------------------------------------------------
cr_side:
        xor     a
        ld      (cr_n),a
        ; --- διαφορές σε tiles. Τα κέντρα είναι σε ΖΥΓΑ μισά tiles (§3.4),
        ; άρα η διαφορά τους είναι ακέραιο πλήθος tiles· αν όχι, δεν πέφτει
        ; στο πλέγμα και δεν υπάρχει διαδρομή.
        ld      a,(cr_tx)
        ld      hl,cr_fx
        sub     (hl)
        bit     0,a
        ret     nz
        sra     a
        call    cr_sgn
        ld      (cr_ds),a
        ld      a,c
        ld      (cr_ux),a
        ld      a,(cr_ty)
        ld      hl,cr_fy
        sub     (hl)
        bit     0,a
        ret     nz
        sra     a
        call    cr_sgn
        ld      (cr_dt),a
        ld      a,c
        ld      (cr_uy),a
        ; --- ακτίνες σε tiles και το βήμα εκκίνησης της διαγωνίου ---
        ld      a,(cr_fs)
        ld      hl,cr_radt
        call    cr_look
        ld      (cr_ra),a
        ld      a,(cr_fs)
        ld      hl,cr_kt
        call    cr_look
        ld      (cr_ka),a
        ld      a,(cr_ts)
        ld      hl,cr_radt
        call    cr_look
        ld      (cr_rb),a
        ld      a,(cr_ts)
        ld      hl,cr_kt
        call    cr_look
        ld      (cr_kb),a
        ; --- ποια περίπτωση; ---
        ld      a,(cr_ds)
        ld      hl,cr_dt
        or      (hl)
        ret     z                       ; ο ίδιος θόλος
        ld      a,(cr_ds)
        or      a
        jp      z,crs_axial
        ld      a,(cr_dt)
        or      a
        jp      z,crs_axial
        ld      a,(cr_ds)
        ld      hl,cr_dt
        cp      (hl)
        jp      z,crs_diag
        jr      c,crs_vert              ; S < T: διαγώνιος, μετά κάθετος
        ; fall through — T < S: διαγώνιος, μετά οριζόντιος

; --- διαγώνιος + οριζόντιος ------------------------------------------------
crs_horz:
        ld      a,(cr_dt)               ; n1 = T - ka + 1
        ld      hl,cr_ka
        sub     (hl)
        inc     a
        ret     m
        ret     z
        ld      (cr_l0),a
        ld      a,(cr_ds)               ; n2 = S - T - rb + 1
        ld      hl,cr_dt
        sub     (hl)
        ld      hl,cr_rb
        sub     (hl)
        inc     a
        ret     m
        ret     z
        ld      (cr_l1),a
        call    cr_c0                   ; η στήλη του πρώτου οριζόντιου
        call    cr_sgn
        ld      hl,cr_ra                ; δεν πρέπει να γυρίσει μέσα στον a
        cp      (hl)
        ret     c
        call    cr_diagdir
        ld      (cr_d0),a
        ld      a,(cr_ux)
        ld      c,a
        ld      a,0
        call    cr_dir
        ld      (cr_d1),a
        ld      a,2
        ld      (cr_n),a
        ret

; --- διαγώνιος + κάθετος ---------------------------------------------------
crs_vert:
        ld      a,(cr_ds)               ; n1 = S - ka
        ld      hl,cr_ka
        sub     (hl)
        ret     m
        ret     z
        ld      (cr_l0),a
        ld      a,(cr_dt)               ; n2 = T - S - rb + 1
        ld      hl,cr_ds
        sub     (hl)
        ld      hl,cr_rb
        sub     (hl)
        inc     a
        ret     m
        ret     z
        ld      (cr_l1),a
        call    cr_r0
        call    cr_sgn
        ld      hl,cr_ra
        cp      (hl)
        ret     c
        call    cr_diagdir
        ld      (cr_d0),a
        ld      c,0                     ; ux = 0
        ld      a,(cr_uy)
        call    cr_dir
        ld      (cr_d1),a
        ld      a,2
        ld      (cr_n),a
        ret

; --- καθαρή διαγώνιος ------------------------------------------------------
crs_diag:
        ld      a,(cr_ds)               ; n = S - ka - kb + 1
        ld      hl,cr_ka
        sub     (hl)
        ld      hl,cr_kb
        sub     (hl)
        inc     a
        ret     m
        ret     z
        ld      (cr_l0),a
        call    cr_diagdir
        ld      (cr_d0),a
        ld      a,1
        ld      (cr_n),a
        ret

; --- καθαρά αξονικός -------------------------------------------------------
crs_axial:
        ld      a,(cr_ds)               ; ο ένας από τους δύο είναι μηδέν
        ld      hl,cr_dt
        or      (hl)
        ld      hl,cr_ra
        sub     (hl)
        ld      hl,cr_rb
        sub     (hl)
        ret     m
        ret     z
        ld      (cr_l0),a
        call    cr_diagdir
        ld      (cr_d0),a
        ld      a,1
        ld      (cr_n),a
        ret

; cr_c0 — η στήλη του πρώτου οριζόντιου πλακιδίου: ux*T - (ux > 0).
cr_c0:
        ld      a,(cr_dt)
        ld      hl,cr_ux
        bit     7,(hl)
        jr      nz,crc0_neg
        dec     a
        ret
crc0_neg:
        neg
        ret

; cr_r0 — η σειρά του πρώτου κάθετου πλακιδίου: uy*(S-1) - (uy < 0).
cr_r0:
        ld      a,(cr_ds)
        dec     a
        ld      hl,cr_uy
        bit     7,(hl)
        ret     z
        inc     a
        neg
        ret

; cr_diagdir — η κατεύθυνση από τα (cr_ux, cr_uy).
cr_diagdir:
        ld      a,(cr_ux)
        ld      c,a
        ld      a,(cr_uy)
        ; fall through

; cr_dir — A = uy, C = ux (και τα δύο -1, 0 ή 1) -> A = κατεύθυνση 0..7.
cr_dir:
        inc     a
        ld      b,a
        add     a,a
        add     a,b                     ; (uy+1)*3
        ld      b,a
        ld      a,c
        inc     a
        add     a,b
        ld      l,a
        ld      h,0
        ld      de,cr_dtab
        add     hl,de
        ld      a,(hl)
        ret

; cr_look — A = δείκτης, HL = πίνακας -> A = πίνακας[δείκτης].
cr_look:
        ld      e,a
        ld      d,0
        add     hl,de
        ld      a,(hl)
        ret

; cr_sgn — A -> |A|, C = -1 / 0 / 1.
cr_sgn:
        ld      c,0
        or      a
        ret     z
        jp      p,crg_pos
        ld      c,-1
        neg
        ret
crg_pos:
        ld      c,1
        ret

; ---------------------------------------------------------------------------
; cr_redraw — ο διάδρομος που μόλις μπήκε: τα tiles του, και οι δύο πόρτες.
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
; ΤΟ ΠΕΡΙΓΡΑΜΜΑ ΤΗΣ ΔΙΑΔΡΟΜΗΣ ΧΩΡΙΣ ΠΕΡΙΘΩΡΙΟ, και οι πόρτες από τη λίστα
; αλλαγών (DK_CONN). Στο βήμα 34 το περίγραμμα είχε ένα tile περιθώριο για τις
; πόρτες, που κάθονται στους δακτυλίους των θόλων, μέσα στο αποτύπωμά τους —
; και αυτό το tile ξαναζωγράφιζε μια ολόκληρη στήλη από κάθε θόλο, δακτύλιο και
; θόλο σε όλο τους το ύψος: 48 από τα 180 ms. Μια πόρτα δεν πέφτει πάνω σε
; θέση δακτυλίου, μηχανή ή εικονίδιο σε κανένα μέγεθος (βήμα 35, από τους
; πίνακες conn_points / corr_slots / machine_slots), οπότε γραμμένη μόνη της
; πάνω από το κέλυφος δίνει ό,τι και το πλήρες πέρασμα. Ο κανόνας κατεύθυνσης
; είναι του ob_conn_scan: ο a στην κατεύθυνση του πρώτου τρεξίματος, ο b στην
; αντίθετη του ΤΕΛΕΥΤΑΙΟΥ.
; ---------------------------------------------------------------------------
cr_redraw:
        ld      a,(cr_from)
        ld      b,a
        ld      a,(cr_d0)
        and     7
        ld      c,a
        ld      a,DK_CONN
        call    dirty_push
        ld      a,(cr_n)
        cp      2
        ld      a,(cr_d0)
        jr      c,crr_last
        ld      a,(cr_d1)
crr_last:
        add     a,4
        and     7
        ld      c,a
        ld      a,(cr_to)
        ld      b,a
        ld      a,DK_CONN
        call    dirty_push
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
; Το πλακίδιο j έχει το σημείο πλέγματος (ux*j, uy*j) στη μέση του, πιάνει
; τις στήλες ux*j - 1 και ux*j, και μισό tile πάνω και κάτω από τη γραμμή
; uy*j. Αρα μια σειρά R = uy*v τη μοιράζονται τα πλακίδια v και v + uy, και
; οι στήλες τους είναι ΤΡΕΙΣ: από ux*v - 1 για «\» (ux = uy), από ux*v - 2
; για «/». Οι σειρές είναι l0 + 1, και η πρώτη έχει v = ka - 1 όταν η
; διαγώνιος κατεβαίνει (uy > 0), v = ka όταν ανεβαίνει.
crr_rows:
        call    crw_base
        ld      a,(cr_uy)
        rlca
        and     1
        xor     1                       ; 1 αν uy > 0
        ld      b,a
        ld      a,(cr_ka)
        sub     b
        ld      (cr_j),a                ; v
        ld      a,(cr_l0)
        inc     a
        ld      (cr_i),a
crrw_lp:
        ld      a,(cr_j)
        ld      hl,cr_uy
        call    cr_mulsg
        ld      hl,cr_bty
        add     a,(hl)
        ld      c,a                     ; η σειρά, στον κόσμο
        ld      a,(cr_j)
        ld      hl,cr_ux
        call    cr_mulsg
        dec     a
        ld      hl,cr_btx
        add     a,(hl)
        ld      b,a                     ; η πρώτη στήλη, στον κόσμο
        ld      a,(cr_ux)
        ld      hl,cr_uy
        cp      (hl)
        jr      z,crrw_bs
        dec     b                       ; «/»: ένα tile αριστερότερα
crrw_bs:
        ; ΜΟΝΟ Ο,ΤΙ ΦΑΙΝΕΤΑΙ. Μια σειρά έξω από το κάδρο θα την έκοβε ούτως ή
        ; άλλως το vr_clip, και μια μακριά διαγώνιος θα γέμιζε το δαχτυλίδι
        ; των 32. Αν η κάμερα κουνηθεί στο μεταξύ, ό,τι μπαίνει στο κάδρο το
        ; ζωγραφίζει ολόκληρο η λωρίδα του σκρολαρίσματος.
        ld      a,(cam_ty)
        neg
        add     a,c
        cp      VIEW_TH
        jr      nc,crrw_nx
        ld      a,(cam_tx)
        neg
        add     a,b
        add     a,2                     ; τρεις στήλες: φαίνεται από το -2
        cp      VIEW_TW + 2
        jr      nc,crrw_nx
        ld      a,DK_CROW
        call    dirty_push
        ld      hl,rv_pend
        inc     (hl)
crrw_nx:
        ld      hl,cr_j
        inc     (hl)
        ld      hl,cr_i
        dec     (hl)
        jr      nz,crrw_lp
        ret

; crr_box — το περίγραμμα των tiles που περπατά η ρουτίνα (HL), χωρίς
; περιθώριο, και view_rect πάνω του.
crr_box:
        push    hl
        ld      hl,#00FF                ; min = +127, max = -128 (μετατοπισμένα)
        ld      (crr_x0),hl
        ld      (crr_y0),hl
        ld      hl,cr_cb_bb
        ld      (cr_cb),hl
        pop     hl
        call    crr_go
        ld      a,(crr_x0)
        xor     #80
        ld      (vr_tx),a
        ld      b,a
        ld      a,(crr_x1)
        xor     #80
        inc     a
        sub     b
        ld      (vr_w),a
        ld      a,(crr_y0)
        xor     #80
        ld      (vr_ty),a
        ld      b,a
        ld      a,(crr_y1)
        xor     #80
        inc     a
        sub     b
        ld      (vr_h),a
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
; ακουμπά. Το ποια δύο εξαρτάται από το αν είναι «\» ή «/». Δύο διαδοχικά
; μοιράζονται το ένα, οπότε μια διαγώνιος n βημάτων είναι n + 1 tiles.
; ---------------------------------------------------------------------------
cr_walk:
        call    crw_base
        ld      a,(cr_d0)
        rrca
        jp      nc,crw_ax0              ; ζυγή κατεύθυνση = αξονικός
        ; --- τρέξιμο 0: διαγώνιος ---
        ld      a,(cr_ka)
        ld      (cr_j),a
        ld      a,(cr_l0)
        ld      (cr_i),a
crw_dl:
        ld      a,(cr_j)
        ld      hl,cr_ux
        call    cr_mulsg                ; A = ux * j
        ld      (cr_lx),a
        ld      a,(cr_j)
        ld      hl,cr_uy
        call    cr_mulsg
        ld      (cr_ly),a
        ; Τα δύο tiles: T1 = (lx - 1, y1), T2 = (lx, 2*ly - 1 - y1), με
        ; y1 = ly - 1 για «\» (ux = uy) και ly για «/».
        ld      a,(cr_ux)
        ld      hl,cr_uy
        cp      (hl)
        ld      a,(cr_ly)
        jr      nz,crw_slash
        dec     a
crw_slash:
        ld      c,a                     ; y1
        ld      a,(cr_ly)
        add     a,a
        dec     a
        sub     c
        ld      e,a                     ; y2
        ld      a,(cr_lx)
        ld      d,a                     ; x2
        ld      b,a
        dec     b                       ; x1
        ; ΚΑΘΕ TILE ΜΙΑ ΦΟΡΑ. Δύο διαδοχικά πλακίδια μοιράζονται ένα tile:
        ; το «μπροστινό» του j είναι το «πίσω» του j + 1. Ως το βήμα 37 το
        ; περνούσαμε δύο φορές, και το φάντασμα ζωγράφιζε το σημάδι του δύο
        ; φορές — η αναίρεση, που πάει μπροστά, έγραφε τελευταίο το «φόντο»
        ; της δεύτερης εγγραφής, δηλαδή το πρώτο σημάδι, και ο κέρσορας άφηνε
        ; ίχνος. Μπροστινό είναι το T2 όταν ux > 0, το T1 όταν ux < 0.
        ld      a,(cr_ux)
        or      a
        jp      p,crw_fw
        ld      a,b
        ld      b,d
        ld      d,a
        ld      a,c
        ld      c,e
        ld      e,a
crw_fw:
        ld      (crw_dy),de             ; E = y, D = x
        ld      a,(cr_j)                ; (B, C) πίσω, (D, E) μπροστά
        ld      hl,cr_ka
        cp      (hl)
        jr      nz,crw_front            ; το πίσω το πέρασε το προηγούμενο βήμα
        push    de
        call    cr_emit
        pop     de
crw_front:
        ld      b,d
        ld      c,e
        call    cr_emit
        ld      hl,(crw_dy)             ; το τελευταίο μπροστινό, για τη στροφή
        ld      (crw_ly),hl
crw_dn:
        ld      hl,cr_j
        inc     (hl)
        ld      hl,cr_i
        dec     (hl)
        jr      nz,crw_dl
        ld      a,(cr_n)
        cp      2
        ret     c
; cr_walk1 — μόνο το τρέξιμο 1, η στροφή. Απαιτεί το crw_base.
cr_walk1:
        ld      a,(cr_d1)
        and     3                       ; e και w είναι 2 και 6· n και s 0 και 4
        cp      2
        jr      nz,crw_v1
crw_h1:
        call    cr_c0
        ld      b,a
        ld      a,(cr_dt)
        ld      hl,cr_uy
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
        ld      a,(cr_ux)
        ld      d,a
        ld      e,0
        jr      crw_run1
crw_v1:
        call    cr_r0
        ld      c,a
        ld      a,(cr_ds)
        ld      hl,cr_ux
        call    cr_mulsg
        ld      b,a
        ld      d,0
        ld      a,(cr_uy)
        ld      e,a
crw_run1:
        ld      a,(cr_l1)
        jp      cr_line

; --- τρέξιμο 0 αξονικό: από το σημείο σύνδεσης, προς τα έξω ---------------
crw_ax0:
        ld      a,(cr_d0)
        and     3
        cp      2
        jr      z,crw_axh
        ; κάθετος: r0 = ra (νότος) ή -ra-1 (βορράς)
        ld      a,(cr_ra)
        ld      hl,cr_uy
        bit     7,(hl)
        jr      z,crw_axv1
        inc     a
        neg
crw_axv1:
        ld      c,a
        ld      b,0
        ld      d,0
        ld      a,(cr_uy)
        ld      e,a
        ld      a,(cr_l0)
        jp      cr_line
crw_axh:
        ld      a,(cr_ra)
        ld      hl,cr_ux
        bit     7,(hl)
        jr      z,crw_axh1
        inc     a
        neg
crw_axh1:
        ld      b,a
        ld      c,0
        ld      a,(cr_ux)
        ld      d,a
        ld      e,0
        ld      a,(cr_l0)
        jp      cr_line

; crw_base — η βάση των σχετικών συντεταγμένων: το tile του κέντρου του a.
; Και ξεχνά το τελευταίο tile της διαγωνίου (-128: δεν υπάρχει στον κόσμο).
crw_base:
        ld      hl,#8080
        ld      (crw_ly),hl
        ld      a,(cr_fx)
        sra     a
        ld      (cr_btx),a
        ld      a,(cr_fy)
        sra     a
        ld      (cr_bty),a
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
; τελευταίο της διαγωνίου· όταν ανεβαίνει, το πρώτο του (crw_h1). Δεύτερη
; φορά δεν περνιέται (crw_lx).
cr_emit:
        ld      a,(crw_lx)
        cp      b
        jr      nz,cre_go
        ld      a,(crw_ly)
        cp      c
        ret     z
cre_go:
        ld      a,(cr_btx)
        add     a,b
        ld      b,a
        ld      a,(cr_bty)
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

cr_radt:    db 2,3,4                    ; ακτίνα σε tiles ανά μέγεθος
cr_kt:      db 2,3,3                    ; DIAG_K — το βήμα που ξεφεύγει ο δακτύλιος
; (uy+1)*3 + (ux+1) -> κατεύθυνση
cr_dtab:    db 7,0,1
            db 6,255,2
            db 5,4,3

cr_a:       db 0
cr_b:       db 0
cr_from:    db 0
cr_to:      db 0
cr_n:       db 0
cr_d0:      db 0
cr_l0:      db 0
cr_d1:      db 0
cr_l1:      db 0
cr_pax:     db 0,0,0                    ; cx, cy, size του a
cr_pbx:     db 0,0,0
cr_fx:      db 0
cr_fy:      db 0
cr_fs:      db 0
cr_tx:      db 0
cr_ty:      db 0
cr_ts:      db 0
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
cr_lx:      db 0
cr_ly:      db 0
cr_i:       db 0
cr_j:       db 0
cr_cb:      dw 0
crw_ly:     db 0                        ; το τελευταίο μπροστινό διαγώνιο tile,
crw_lx:     db 0                        ; σχετικό (y, x) — #80 = κανένα
crw_dy:     db 0                        ; το μπροστινό του τρέχοντος βήματος
crw_dx:     db 0

; ---------------------------------------------------------------------------
; cr_check — περπατά τη διαδρομή και μετρά τα tiles που δεν επιτρέπονται.
; Out: A = πλήθος κακών tiles (0 = επιτρέπεται). Απαιτεί έγκυρη (cr_n).
; ---------------------------------------------------------------------------
cr_check:
        xor     a
        ld      (cr_bad),a
        ld      (cr_ntile),a
        ld      hl,cr_cb_chk
        ld      (cr_cb),hl
        ld      bc,GA_PORT + PAGE_B4
        out     (c),c
        call    cr_walk
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
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
cr_cb_chk:
        ld      hl,cr_ntile
        inc     (hl)
        ld      a,b
        add     a,64
        bit     7,a
        jr      nz,crk_bad              ; έξω από τον κόσμο
        ld      a,c
        add     a,64
        bit     7,a
        jr      nz,crk_bad
        push    bc
        call    tile_addr
        ld      a,(hl)
        call    bd_ok
        pop     bc
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
; πρόσημο, και το ίδιο για το C. Χαλάει A, DE, HL.
crk_in:
        push    hl
        inc     hl
        inc     hl
        ld      a,(hl)
        ld      hl,cr_radt
        call    cr_look                 ; A = r σε tiles
        pop     hl
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
        bit     7,a
        ret     nz
        ld      a,c
        add     a,64
        bit     7,a
        ret     nz
        push    bc
        call    tile_addr
        ld      a,(hl)
        or      W_OCC_STRUCT
        ld      (hl),a
        pop     bc
        ret

; ---------------------------------------------------------------------------
; cr_cost — το συνολικό κόστος σε (cr_metal, cr_biop), 16 bit.
; Ο κατάλογος δίνει την τιμή ΑΝΑ ΠΛΑΚΙΔΙΟ: ένας διάδρομος δέκα πλακιδίων
; κοστίζει δέκα φορές όσο ένας του ενός, που είναι και το μόνο που βγάζει
; νόημα όταν το μήκος το διαλέγει η γεωμετρία και όχι ο παίκτης.
; ---------------------------------------------------------------------------
cr_cost:
        ld      a,(cr_l0)
        ld      b,a
        ld      a,(cr_n)
        cp      2
        jr      c,crc_one
        ld      a,(cr_l1)
        add     a,b
        ld      b,a
crc_one:
        ld      a,b
        ld      (cr_ntile),a
        ld      a,(bd_metal)
        ld      c,a
        ld      a,(cr_ntile)
        call    ob_mul
        ld      (cr_metal),hl
        ld      a,(bd_biop)
        ld      c,a
        ld      a,(cr_ntile)
        call    ob_mul
        ld      (cr_biop),hl
        ret

; cr_afford — Z αν φτάνουν τα υλικά για ολόκληρη τη διαδρομή.
cr_afford:
        call    cr_cost
        ld      hl,(EC_STOCK + S_METAL*2)
        ld      de,(cr_metal)
        or      a
        sbc     hl,de
        jr      c,cra_no
        ld      hl,(EC_STOCK + S_BIOPL*2)
        ld      de,(cr_biop)
        or      a
        sbc     hl,de
        jr      c,cra_no
        xor     a
        ret
cra_no:
        or      a
        ld      a,1
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
        ld      b,MAX_CORR
        ld      c,0
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
        ld      de,CORR_REC
        add     hl,de
        ld      a,(hl)
        pop     hl
        or      a
        jr      z,crm_got
crm_next:
        ld      de,CORR_REC
        add     hl,de
        inc     c
        djnz    crm_find
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        ld      a,1
        ret
crm_got:
        ; HL δείχνει στο C_CSTATE της πρώτης άδειας· πίσω στην αρχή της
        ld      de,C_CSTATE
        or      a
        sbc     hl,de
        push    hl
        ld      a,(cr_from)
        ld      (hl),a
        inc     hl
        ld      a,(cr_to)
        ld      (hl),a
        inc     hl
        ld      a,(cr_d0)
        ld      (hl),a
        inc     hl
        ld      a,(cr_l0)
        ld      (hl),a
        inc     hl
        ld      (hl),DS_ACTIVE
        pop     hl
        ld      a,(cr_n)
        cp      2
        jr      c,crm_done
        ld      de,CORR_REC
        add     hl,de
        ld      (hl),255                ; C_A = 255: συνέχεια της προηγούμενης
        inc     hl
        ld      (hl),255
        inc     hl
        ld      a,(cr_d1)
        ld      (hl),a
        inc     hl
        ld      a,(cr_l1)
        ld      (hl),a
        inc     hl
        ld      (hl),DS_ACTIVE
crm_done:
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        call    cr_stamp
        call    cr_pay
        call    cr_link
        ld      a,OB_IX_FIG + OB_IX_CORR    ; οι πόρτες και οι διάδρομοι
        call    ob_touch_a
        xor     a
        ret

; cr_pay — αφαιρεί το κόστος ολόκληρης της διαδρομής.
cr_pay:
        call    cr_cost
        ld      hl,(EC_STOCK + S_METAL*2)
        ld      de,(cr_metal)
        or      a
        sbc     hl,de
        ld      (EC_STOCK + S_METAL*2),hl
        ld      hl,(EC_STOCK + S_BIOPL*2)
        ld      de,(cr_biop)
        or      a
        sbc     hl,de
        ld      (EC_STOCK + S_BIOPL*2),hl
        ret

; ---------------------------------------------------------------------------
; cr_link — η ακμή μπαίνει στον γράφο κόμβων και ξαναχτίζεται η δρομολόγηση.
; Ο γράφος ζει στην τράπεζα 2, που είναι πάντα ορατή (§4.3).
; ---------------------------------------------------------------------------
cr_link:
        ld      a,(cr_from)
        ld      b,a
        ld      a,(cr_to)
        ld      c,a
        call    cr_edge
        ld      a,(cr_to)
        ld      b,a
        ld      a,(cr_from)
        ld      c,a
        call    cr_edge
        ; Οχι rt_begin: αυτό μόνο μηδενίζει τον μετρητή πηγών. Το rt_dirty
        ; είναι που κάνει τον τροχό να ΤΡΕΞΕΙ την ανοικοδόμηση.
        jp      rt_mark

; cr_edge — προσθέτει τον C στους γείτονες του B, αν χωράει.
cr_edge:
        ld      h,NODEPG
        ld      l,b
        ld      a,(hl)
        cp      MAX_DEGREE
        ret     nc
        push    af
        inc     (hl)
        ld      l,b
        ld      h,0
        add     hl,hl
        add     hl,hl
        add     hl,hl
        ld      de,G_node_adj
        add     hl,de
        pop     af
        ld      e,a
        ld      d,0
        add     hl,de
        ld      (hl),c
        ret

cr_bad:     db 0
cr_ntile:   db 0
cr_metal:   dw 0
cr_biop:    dw 0
