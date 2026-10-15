; object.asm — το πέρασμα αντικειμένων (DESIGN §8.4, SPRITES.md §10).
;
; Η σειρά είναι του SPRITES.md §10 με τις διορθώσεις του §8.4. Ως το βήμα 95
; οι διάδρομοι έμπαιναν ΑΝΑΜΕΣΑ στα κελύφη και στις πόρτες, γιατί η πόρτα
; άνοιγε τον δακτύλιο από πάνω. Από το 96 μπαίνουν ΠΡΩΤΟΙ, κάτω από τα κελύφη,
; και σταματούν στο εξωτερικό χείλος· ο αρμός (src/joint.asm) τους ενώνει.
;
;       1  διάδρομοι                  μάσκα
;       2  δακτύλιοι + θόλοι          μάσκα, από το ένα αποθηκευμένο nw
;       3  αρμοί, εικονίδιο, μηχανές ή φυτά, φιγούρες
;       4  εξωτερικές δομές, ταξινομημένες κατά cy
;
; ΤΟ CLIP ΕΙΝΑΙ Ο ΜΗΧΑΝΙΣΜΟΣ ΤΟΥ ΣΚΡΟΛΑΡΙΣΜΑΤΟΣ. Κάθε blit κόβεται σε ένα
; ορθογώνιο. Με ολόκληρο το κάδρο είναι η πρώτη σχεδίαση· με μία στήλη είναι η
; στήλη που μόλις μπήκε στο κάδρο, και ένας μεγάλος θόλος κοστίζει το ένα
; όγδοο του εαυτού του αντί για ολόκληρο. Ενας μηχανισμός, δύο δουλειές.
;
; ΣΕΛΙΔΟΠΟΙΗΣΗ. Οι πίνακες (dome_tbl, struct_tbl, corr_tbl, agent_fields) είναι
; στην ΤΡΑΠΕΖΑ 6 μαζί με τα τεταρτημόρια και τις φιγούρες· τα εικονίδια, οι
; μηχανές και οι διάδρομοι στην 2 (πάντα ορατή), οι αρμοί στην 5· τα ΦΥΤΑ και οι
; ΕΞΩΤΕΡΙΚΕΣ ΔΟΜΕΣ στην 7. Οπου χρειάζεται και πίνακας και τράπεζα 7, η εγγραφή
; ΑΝΤΙΓΡΑΦΕΤΑΙ πρώτη σε RAM της τράπεζας 0 — το ίδιο μάθημα με τον πάγκο της
; BFS, τρίτη φορά.

OB_ALIVE    equ 1                       ; F_ALIVE του entity.asm
                                        ; (τα AG_* είναι στο const.asm)

; ---------------------------------------------------------------------------
; ob_blit — ΕΝΑ sprite, κομμένο στο παράθυρο clip, με προαιρετικό καθρέφτισμα.
;
; Παράμετροι στο μπλοκ ob_* παρακάτω. Το ob_fl κουβαλά τον προσανατολισμό στα
; bits 0-1 (ίδια κωδικοποίηση με το blit_quad) και το «αδιαφανές» στο bit 2.
;
; Το καθρεφτισμένο sprite διαβάζεται ΑΝΑΠΟΔΑ από το τέλος της γραμμής (blt_mask_flip):
; κόβεται μέσα στο buffer: το clip από αριστερά αντιστοιχεί σε ζεύγη από το
; ΤΕΛΟΣ της πηγής, και κανένας δείκτης δεν το εκφράζει αυτό πιο απλά.
;
; ob_put — το ίδιο, με L = w, H = h, A = σημαίες: οι τρεις αναθέσεις που
; έκανε με το χέρι κάθε καλών.
; ---------------------------------------------------------------------------
ob_put:
        ld      (ob_w),hl               ; ob_w, ob_h διπλανά
        ld      (ob_fl),a
ob_blit:
        ; ΧΩΡΙΣ ΔΙΑΣΤΗΜΑΤΑ. Μόνο το ob_quads μπαίνει πιο κάτω, στο ob_bspan, με
        ; το ob_spt στον πίνακα του τεταρτημορίου (src/span.asm, βήμα 108).
        xor     a
        ld      (ob_spt+1),a
ob_bspan:
        ; --- κάθετο clip ---
        ld      hl,(ob_y)
        ld      a,(ob_h)
        ld      de,(clip_y0)            ; y0 χαμηλό, y1 ψηλό — ένα ld
        call    ob_clip
        ret     z
        ld      hl,(cl_skip)            ; skip, n -> ob_st, ob_nl
        ld      (ob_st),hl
        ld      a,(cl_start)
        ld      (ob_y0),a
        ; --- οριζόντιο clip. Τα cl_skip / cl_n / cl_start του μένουν όπως
        ; βγήκαν ως το τέλος: τίποτα από κάτω δεν ξανακόβει. ---
        ld      hl,(ob_x)
        ld      a,(ob_w)
        ld      de,(clip_x0)
        call    ob_clip
        ret     z
        ; ΤΑ ΚΕΛΥΦΗ ΦΕΥΓΟΥΝ ΕΔΩ (βήμα 110). Από το 110 είναι αποθηκευμένα μόνο ως
        ; διαστήματα (tools/pack.py, shell), και πηγή, βήμα, πυρήνα και οθόνη
        ; τα στήνει το sp_grp ανά ομάδα· ό,τι υπολογίζεται πιο κάτω θα πεταγόταν.
        ld      hl,(ob_spt)
        inc     h
        dec     h
        jp      nz,sp_first             ; src/span.asm· γυρίζει στο ob_line

        ; --- βήμα πηγής ανά γραμμή: W αδιαφανές, 2W με μάσκα ---
        ld      a,(ob_fl)
        and     4
        ld      a,(ob_w)
        jr      nz,ob_stride
        add     a,a
ob_stride:
        ld      c,a

        ; --- πρώτη γραμμή πηγής: από πάνω, ή από κάτω αν καθρεφτίζεται ---
        ld      a,(ob_fl)
        and     2
        ld      a,(ob_st)
        jr      z,ob_fromtop
        ld      b,a
        ld      a,(ob_h)
        dec     a
        sub     b
ob_fromtop:
        call    ob_mul                  ; HL = γραμμή * βήμα· το C μένει
        ld      de,(ob_src)
        add     hl,de

        ; --- και η μετατόπιση μέσα στη γραμμή, για το clip από αριστερά,
        ; ΜΙΑ φορά εδώ και όχι σε κάθε γραμμή. Στο καθρεφτισμένο δείχνει στο
        ; ΠΡΩΤΟ ζεύγος που θα χρειαστεί — στο (w-1-skip) μετρώντας από την
        ; αρχή — και το blt_mask_flip διαβάζει μόνο όσα ζεύγη γράφονται.
        ld      a,(ob_fl)
        rra
        ld      a,(cl_skip)
        jr      nc,ob_noflip
        cpl                             ; -skip-1
        ld      b,a
        ld      a,(ob_w)
        add     a,b
        add     a,a
        jr      ob_skdone
ob_noflip:
        ld      b,a
        ld      a,(ob_fl)
        and     4
        ld      a,b
        jr      nz,ob_skdone
        add     a,a
ob_skdone:
        call    ob_addu
        ld      (obl_p+1),hl

        ; --- ΟΣΑ ΜΕΝΟΥΝ ΙΔΙΑ ΑΠΟ ΓΡΑΜΜΗ ΣΕ ΓΡΑΜΜΗ γράφονται μέσα στον βρόχο
        ; (βήμα 108): η πηγή, ο πυρήνας, πόσα bytes, το βήμα με το πρόσημό
        ; του. Ως τότε ο βρόχος ξαναδιάβαζε σε κάθε γραμμή το ob_fl δύο
        ; φορές, το cl_n, το ob_str και το ob_ln, και καλούσε το scr_nextline:
        ; 83 us η γραμμή έξω από τον πυρήνα, όταν μια στήλη 4 bytes ενός
        ; θόλου είναι 128. Τώρα 51. Το C είναι ακόμη το βήμα (ob_mul,
        ; ob_addu). ---
        ld      a,(ob_fl)
        ld      hl,blt_mask_flip        ; μόνο τα ζεύγη που γράφονται, κατευθείαν
        rra
        jr      c,ob_kern
        ld      hl,blt_op_line
        bit     1,a                     ; το «αδιαφανές», μετά το rra
        jr      nz,ob_kern
        ld      hl,blt_mask_line
ob_kern:
        ld      (obl_k+1),hl
        ld      b,0
        rra                             ; CY: ανάποδα, από κάτω προς τα πάνω
        jr      nc,ob_sdn
        xor     a
        sub     c
        ld      c,a
        sbc     a,a
        ld      b,a                     ; BC = -βήμα
ob_sdn:
        ld      (obl_s+1),bc
        ld      a,(cl_n)
        ld      (obl_n+1),a
        ld      a,(cl_start)
        ld      c,a
        ld      a,(ob_y0)
        call    scr_addr
        ; ΤΑ ΚΟΜΜΑΤΙΑ. Ο βρόχος μετρά γραμμές ως το τέλος του κομματιού
        ; (obl_c), και το ob_nl όσες μένουν μετά από αυτό. Χωρίς διαστήματα
        ; ένα κομμάτι, όλες οι γραμμές· τα κελύφη, ένα ανά οκτώ γραμμές πηγής,
        ; έφυγαν πιο πάνω (src/span.asm).
        ld      hl,ob_nl
        ld      a,(hl)
        ld      (hl),0
        ld      (obl_c),a

ob_line:
        push    de
obl_p:  ld      hl,0                    ; η πηγή αυτής της γραμμής
        push    hl
obl_n:  ld      b,0                     ; πόσα bytes
obl_k:  call    0                       ; blt_mask_flip, blt_mask_line, blt_op_line
        pop     hl
obl_s:  ld      bc,0                    ; ±βήμα
        add     hl,bc
        ld      (obl_p+1),hl
        pop     de
        ld      a,d
        add     a,8
        ld      d,a
        call    c,scr_nlw               ; μόνο όταν τελειώνει σειρά χαρακτήρων
        ld      hl,obl_c
        dec     (hl)
        jr      nz,ob_line
        ld      a,(ob_nl)
        or      a
        ret     z
        call    sp_next                 ; το επόμενο κομμάτι
        jr      ob_line

; ---------------------------------------------------------------------------
; ob_clip — ένας άξονας. Δίνει πόσο κόβεται από την αρχή, πόσο μένει, και πού
; αρχίζει στην οθόνη.
; In :  HL = θέση, 16-bit προσημασμένη· A = μήκος· E = lo, D = hi — ένα
;       ld de,(clip_x0) ή ld de,(clip_y0) τα φέρνει μαζί
; Out:  Z -> εκτός· αλλιώς A = (cl_n), και (cl_skip), (cl_start)
;
; Ως το βήμα 43 έπαιρνε τα πάντα από τη μνήμη, και καθένας από τους οκτώ
; καλούντες τα έγραφε εκεί με τέσσερα ld: 9 bytes ο καθένας.
; ---------------------------------------------------------------------------
ob_clip:
        ld      (cl_len),a
        ld      (cl_lo),de              ; cl_lo, cl_hi
        ld      d,0
        ex      de,hl                   ; HL = lo, DE = pos
        or      a
        sbc     hl,de                   ; lo - pos
        jp      m,oc_after
        ld      a,h
        or      a
        jr      nz,oc_cull              ; κόβεται πάνω από 255 -> έξω
        ld      a,l
        ld      (cl_skip),a
        ld      b,a
        ld      a,(cl_len)
        sub     b
        jr      c,oc_cull
        jr      z,oc_cull
        ld      c,a
        ld      a,(cl_lo)
        ld      (cl_start),a
        jr      oc_tail
oc_after:
        xor     a
        ld      (cl_skip),a
        ld      a,d
        or      a
        jr      nz,oc_cull              ; δεξιά/κάτω από την οθόνη
        ld      a,e
        ld      (cl_start),a
        ld      a,(cl_len)
        ld      c,a
oc_tail:
        ld      a,(cl_start)
        ld      b,a
        ld      a,(cl_hi)
        sub     b
        jr      c,oc_cull
        jr      z,oc_cull
        cp      c
        jr      c,oc_have
        ld      a,c
oc_have:
        ld      (cl_n),a
        or      a                       ; NZ: το n είναι τουλάχιστον 1
        ret
oc_cull:
        xor     a
        ret

; ---------------------------------------------------------------------------
; ob_mul — HL = A * C, χωρίς πίνακα. Καλείται μία φορά ανά sprite.
; ---------------------------------------------------------------------------
ob_mul:
        ld      hl,0
        ld      d,h
        ld      e,c
        ld      b,8
obm_lp:
        add     hl,hl
        rlca
        jr      nc,obm_no
        add     hl,de
obm_no:
        djnz    obm_lp
        ret

; ---------------------------------------------------------------------------
; ob_sext — A (προσημασμένο byte) -> HL.
; ---------------------------------------------------------------------------
ob_sext:
        ld      l,a
        rla
        sbc     a,a
        ld      h,a
        ret

; ob_addu — HL += A, ανυπόγραφο. Δεν αγγίζει τα BC, DE: γι' αυτό αντικαθιστά
; και το ld l,a / ld h,0 / ld de,πίνακας / add hl,de, που τα χαλούσε.
;
; ΟΧΙ ΓΙΑ ΣΤΑΘΕΡΟ ΠΙΝΑΚΑ ΣΤΟ ΠΕΡΑΣΜΑ ΤΟΥ ΕΥΡΕΤΗΡΙΟΥ (βήμα 89). Ο χρόνος του
; εξαρτάται από το αν ο πίνακας περνά όριο σελίδας: στο βήμα 89 ο κώδικας από
; πάνω μεγάλωσε, το corr_dir και το dome_conn έπεσαν πάνω σε όριο, και το
; ob_index βγήκε ως 134 us πιο αργό χωρίς να αλλάξει εντολή. Εκεί (dome_geo,
; corr_dir, diag_k, struct_dims, struct_ptr, και ως το 95 το dome_conn) γράφεται μέσα: add a,
; ld l, adc a, sub l, ld h — 7 us όπου κι αν πέσει, αντί για 13-16.
ob_addu:
        add     a,l
        ld      l,a
        ret     nc
        inc     h
        ret

; ob_subu — HL -= A, ανυπόγραφο.
ob_subu:
        ld      e,a
        ld      d,0
        or      a
        sbc     hl,de
        ret

; ob_sx / ob_sy — κέντρο αντικειμένου σε μισά tiles -> οθόνη (§3.4).
;       x = 2*hx - 4*cam_tx = 2*(hx - 2*cam_tx)
;       y = 8*hy - 16*cam_ty = 8*(hy - 2*cam_ty)
ob_sx:
        ld      de,cam_tx
        call    ob_rel
        add     hl,hl
        ret
ob_sy:
        ld      de,cam_ty
        call    ob_rel
        add     hl,hl
        add     hl,hl
        add     hl,hl
        ret

; Οι συντεταγμένες ενός κελιού φιγούρας έξω (src/figure.asm, βήμα 89): εδώ,
; δίπλα στα ob_sx / ob_sy, γιατί η τράπεζα 2 γέμισε.
; fg_in — H = ux, L = uy -> CY αν το κελί είναι στο κάδρο, και τότε ob_x, ob_y
; = το κελί στην οθόνη. Είναι ΟΛΟ μέσα ή ΟΛΟ έξω: το κάδρο είναι 40 x 20 μισά
; tiles ακριβώς, άρα μέσα η θέση είναι ένα byte (x < 80, y < 160) και δεν
; χρειάζεται το ob_sx / ob_sy των 16 bits — ~45 us αντί για ~150. Χαλάει A, B.
fg_in:
        ld      a,(cam_tx)
        add     a,a
        add     a,128
        ld      b,a
        ld      a,h
        sub     b
        cp      2 * VIEW_TW
        ret     nc
        add     a,a
        ld      (ob_x),a
        ld      a,(cam_ty)
        add     a,a
        add     a,128
        ld      b,a
        ld      a,l
        sub     b
        cp      2 * VIEW_TH
        ret     nc
        add     a,a
        add     a,a
        add     a,a
        ld      (ob_y),a
        xor     a
        ld      (ob_x + 1),a
        ld      (ob_y + 1),a
        scf
        ret
        assert  2 * VIEW_TW * 2 <= 256 && 2 * VIEW_TH * 8 <= 256

; fge_t — A = μισά tiles + 128 -> το tile, μείον ένα.
fge_t:
        xor     128
        sra     a
        dec     a
        ret

; ob_rel — HL = A - 2*(DE), και τα δύο προσημασμένα. obr_t — HL - 2*(DE),
; για όποιον έχει ήδη το HL (ui_rel).
ob_rel:
        call    ob_sext
obr_t:
        ld      a,(de)
        push    hl
        call    ob_sext
        add     hl,hl
        ex      de,hl
        pop     hl
        or      a
        sbc     hl,de
        ret

; ---------------------------------------------------------------------------
; ob_getdome — A = id θόλου· αντιγράφει τα 24 bytes στη RAM της τράπεζας 0 και
; υπολογίζει το πλαίσιο. Η αντιγραφή δεν είναι σπατάλη: χωρίς αυτήν δεν
; μπορούμε να σελιδοποιήσουμε την 7 για τα φυτά.
; Απαιτεί: τράπεζα 6.
; ---------------------------------------------------------------------------
; ob_domeadr — A = id -> HL = η εγγραφή μέσα στην τράπεζα 6.
ob_domeadr:
        ld      l,a
        ld      h,0
        add     hl,hl
        add     hl,hl
        add     hl,hl
        ld      d,h
        ld      e,l                     ; 8*id
        add     hl,hl                   ; 16*id
        add     hl,de                   ; 24*id
        ld      de,G_dome_tbl
        add     hl,de
        ret

; ob_dome_live — A = id· Ζ αν η θέση είναι άδεια. Το A μένει.
;
; Υπάρχει επειδή το ob_getdome αντιγράφει 24 bytes ΠΡΙΝ δει την κατάσταση, και
; 52 από τις 64 θέσεις είναι άδειες: σε κάθε βήμα σκρολαρίσματος πληρώναμε
; 2.500 ldi για εγγραφές που δεν υπάρχουν.
ob_dome_live:
        ld      c,a
        call    ob_domeadr
        ld      de,D_STATE
        add     hl,de
        ld      a,(hl)
        or      a
        ld      a,c
        ret

ob_getdome:
        ld      (d_id),a
        call    ob_domeadr
        ld      de,d_rec
        ld      bc,DOME_REC
        ldir
        ; fall through

; ob_frame — πλαίσιο του θόλου από το d_rec: (d_fx, d_fy) και ο πίνακας d_geo.
ob_frame:
        ld      a,(d_rec+D_SIZE)
        add     a,a
        ld      c,a
        add     a,a
        add     a,a
        add     a,c                     ; 10*size — η εγγραφή είναι ΔΕΚΑ bytes
        add     a,dome_geo & 255        ; σταθερός χρόνος, όπου κι αν πέσει ο πίνακας
        ld      l,a
        adc     a,dome_geo >> 8
        sub     l
        ld      h,a
        ld      (d_geo),hl
        ld      e,(hl)                  ; QW
        inc     hl
        ld      d,(hl)                  ; QH
        ld      (d_qw),de               ; d_qw, d_qh διπλανά
        ld      a,(d_rec+D_CX)
        call    ob_sx
        ld      a,(d_qw)
        call    ob_subu
        ld      (d_fx),hl
        ld      a,(d_rec+D_CY)
        call    ob_sy
        ld      a,(d_qh)
        call    ob_subu
        ld      (d_fy),hl
        ret

; ob_center — ob_x, ob_y = το κέντρο του θόλου: το πλαίσιο συν ένα τεταρτημόριο.
ob_center:
        ld      hl,(d_fx)
        ld      a,(d_qw)
        call    ob_addu
        ld      (ob_x),hl
        ld      hl,(d_fy)
        ld      a,(d_qh)
        call    ob_addu
        ld      (ob_y),hl
        ret

; ob_slot_at — A = θέση (πόρτα, υποδοχή, θέση δακτυλίου), DE = ο πίνακας της
; (px, py) ανά μέγεθος θόλου, 16 bytes το μέγεθος. ob_x, ob_y = το πλαίσιο
; συν το (px, py). Out: C = px — το 255 λέει «αυτή η θέση δεν υπάρχει».
;
; Τέσσερις ρουτίνες το έγραφαν η καθεμιά μόνη της, ως το βήμα 43.
ob_slot_at:
        add     a,a
        ld      c,a
        ld      a,(d_rec+D_SIZE)
        add     a,a
        add     a,a
        add     a,a
        add     a,a
        add     a,c                     ; size*16 + θέση*2
        ex      de,hl
        call    ob_addu
        ld      c,(hl)                  ; px
        inc     hl
        ld      a,(hl)                  ; py
        ld      hl,(d_fy)
        call    ob_addu
        ld      (ob_y),hl
        ld      a,c
        ld      hl,(d_fx)
        call    ob_addu
        ld      (ob_x),hl
        ret

; ob_move — HL -> (dx, dy), προσημασμένα: ob_x += dx, ob_y += dy.
; ob_movek — το ίδιο, B φορές (και καμία, με B = 0).
ob_movek:
        inc     b
        jr      obm_e
obm_k:
        push    bc
        push    hl
        call    ob_move
        pop     hl
        pop     bc
obm_e:
        djnz    obm_k
        ret
ob_move:
        ld      a,(hl)
        inc     hl
        push    hl
        ld      hl,(ob_x)
        call    ob_addsx
        ld      (ob_x),hl
        pop     hl
        ld      a,(hl)
        ld      hl,(ob_y)
        call    ob_addsx
        ld      (ob_y),hl
        ret

; ---------------------------------------------------------------------------
; ob_vis — τέμνει το πλαίσιο του θόλου το παράθυρο clip; A = 0 και Z: όχι.
;
; ΕΝΑΣ έλεγχος ορθογωνίου ανά θόλο, πριν από οτιδήποτε άλλο. Χωρίς αυτόν κάθε
; θόλος πλήρωνε οκτώ πόρτες, οκτώ υποδοχές μηχανών και οκτώ θέσεις αποίκων —
; σαράντα κλήσεις ob_blit που κόβονταν μία-μία. Στο σκρολάρισμα, όπου το
; παράθυρο είναι μία στήλη 4 bytes, αυτό ήταν όλο το κόστος.
; ---------------------------------------------------------------------------
ob_vis:
        ld      a,(ob_meas)
        or      a
        jp      nz,ov_meas              ; src/objindex.asm, τράπεζα 2
        ld      hl,(d_fx)
        ld      a,(d_qw)
        add     a,a
        ld      de,(clip_x0)
        call    ob_clip
        ret     z
        ld      hl,(d_fy)
        ld      a,(d_qh)
        add     a,a
        ld      de,(clip_y0)
        jp      ob_clip
; ---------------------------------------------------------------------------
; ob_ovl — τέμνεται το [HL, HL+DE) με το [cl_lo, cl_hi); 16 bit, για τους
; διαδρόμους που μπορεί να είναι 95 πλακίδια μακριοί.
; Out: A = 0 όχι.
; ---------------------------------------------------------------------------
ob_ovl:
        push    hl
        add     hl,de
        ld      a,(cl_lo)
        ld      e,a
        ld      d,0
        or      a
        sbc     hl,de
        pop     hl
        jp      m,oov_no
        jr      z,oov_no
        push    hl
        ex      de,hl
        ld      a,(cl_hi)
        ld      l,a
        ld      h,0
        or      a
        sbc     hl,de
        pop     hl
        jp      m,oov_no
        jr      z,oov_no
        ld      a,1
        ret
oov_no:
        xor     a
        ret

; ---------------------------------------------------------------------------
; ob_shell — βήματα 1-2: δακτύλιος και θόλος, τέσσερα τεταρτημόρια το καθένα.
; In: A = id θόλου. Απαιτεί τράπεζα 6.
; ---------------------------------------------------------------------------
ob_shell:
        call    ob_dome_live
        ret     z
        call    ob_getdome
        call    ob_vis
        ret     z
        ; ΠΟΥ ΕΧΕΙ ΚΑΤΙ ΚΑΘΕ ΟΚΤΩ ΓΡΑΜΜΕΣ (βήμα 108, src/span.asm): από το
        ; βήμα 110 στην κεφαλίδα του ίδιου του κελύφους, στην τράπεζα 6.
        ld      hl,(d_geo)
        inc     hl
        inc     hl                      ; -> dome_nw
        ld      e,(hl)
        inc     hl
        ld      d,(hl)
        inc     hl
        push    de                      ; ο θόλος περιμένει
        ld      e,(hl)
        inc     hl
        ld      d,(hl)
        call    ob_quads                ; πρώτα ο δακτύλιος
        pop     de
        ; fall through — μετά ο θόλος, στο ίδιο πλαίσιο

; ob_quads — DE = το κέλυφος (η κεφαλίδα του, tools/pack.py)· τέσσερα
; τεταρτημόρια στο πλαίσιο (d_fx,d_fy).
ob_quads:
        ld      (ob_src),de
        ld      (ob_spt),de             ; και τα διαστήματα: ΠΑΝΤΑ (βήμα 110)
        ld      hl,(d_qw)               ; QW, QH -> ob_w, ob_h: το ob_blit
        ld      (ob_w),hl               ; δεν τα πειράζει
        xor     a
oq_loop:
        ld      (oq_cur),a
        ld      (ob_fl),a               ; bits 0-1 = προσανατολισμός, bit2 = 0
        ld      hl,(d_fx)
        rra
        jr      nc,oq_nox
        ld      a,(d_qw)
        call    ob_addu
oq_nox:
        ld      (ob_x),hl
        ld      hl,(d_fy)
        ld      a,(oq_cur)
        and     2
        jr      z,oq_noy
        ld      a,(d_qh)
        call    ob_addu
oq_noy:
        ld      (ob_y),hl
        call    ob_bspan                ; με τα διαστήματα του ob_spt
        ld      a,(oq_cur)
        inc     a
        cp      4
        jr      nz,oq_loop
        ret

; ---------------------------------------------------------------------------
; ob_fittings — βήματα 3-6 ενός θόλου: αρμοί (ως το 95 πόρτες), εικονίδιο,
; μηχανές ή φυτά, φιγούρες. In: A = id θόλου. Απαιτεί τράπεζα 6 στην είσοδο, την αφήνει ως έχει.
; ---------------------------------------------------------------------------
ob_fittings:
        call    ob_dome_live
        ret     z
        call    ob_getdome
        call    ob_vis
        ret     z
        call    jt_dome                 ; βήμα 3: οι αρμοί (src/joint.asm, βήμα 96)
        ; ΤΟ ΕΡΓΟΤΑΞΙΟ ΕΙΝΑΙ ΑΔΕΙΟ. Ο εξοπλισμός (src/fit.asm) γράφει μηχανές
        ; και πάνω σε εργοτάξιο, όπως στο Planetbase — αλλά αν φαίνονταν από
        ; τότε, ο μισοχτισμένος θόλος θα έδειχνε τελειωμένος. Τις ζωγραφίζει
        ; το dh_built στο τέλος. Το κενό εικονίδιο είναι το 0.
        ld      a,(d_rec+D_STATE)
        cp      DS_ACTIVE
        jr      z,obf_full
        xor     a
        ld      (d_rec+D_ROOM),a
        call    ob_icon
        jp      ob_figures
obf_full:
        call    ob_icon
        call    ob_machines
        jp      ob_figures

; --- εικονίδιο δωματίου, στο interior_ofs από το ΚΕΝΤΡΟ --------------------
ob_icon:
        call    ob_center
        ld      a,(d_rec+D_SIZE)
        add     a,a
        ld      hl,G_interior_ofs
        call    ob_addu
        call    ob_move                 ; (dx, dy) προσημασμένα
        ; πηγή: icon_{size}_ptr[room]
        ld      hl,(d_geo)
        ld      de,6
        add     hl,de                   ; -> icon_ptr, icon_w, icon_h
        ld      e,(hl)
        inc     hl
        ld      d,(hl)
        inc     hl
        ld      a,(hl)
        inc     hl
        ld      h,(hl)
        ld      l,a
        push    hl                      ; w, h
        ld      a,(d_rec+D_ROOM)
        add     a,a
        ex      de,hl
        call    ob_addu
        ld      a,(hl)
        inc     hl
        ld      h,(hl)
        ld      l,a
        ld      (ob_src),hl
        pop     hl
        ; Τα εικονίδια m και l μετακόμισαν στην ΤΡΑΠΕΖΑ 1, πάνω από τον πίνακα
        ; DIST (§4.2): με 96 κόμβους ο πίνακας αφήνει 4 KB, και αυτά τα 4 KB
        ; έγιναν χώρος ΚΩΔΙΚΑ στην τράπεζα 2. Τα s ακολούθησαν τις μηχανές
        ; στην ΤΡΑΠΕΖΑ 5 στο βήμα 87, για τον ίδιο λόγο.
        ld      a,(d_rec+D_SIZE)
        or      a
        ld      a,4                     ; αδιαφανές
        ld      c,PAGE_B1
        jr      nz,ob_put_in
        ld      c,PAGE_B5
; ob_put_in — ob_put με την τράπεζα C στο παράθυρο, και μετά πίσω η 6.
ob_put_in:
        ld      b,GA_PORT / 256
        out     (c),c
        call    ob_put
ob_b6:
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        ret

; --- μηχανές ή φυτά στις υποδοχές ------------------------------------------
; Το θερμοκήπιο γεμίζει τις ΙΔΙΕΣ υποδοχές με φυτά, και τα φυτά ζουν στην
; τράπεζα 7. Γι' αυτό η εγγραφή αντιγράφηκε: εδώ φεύγει η 6.
ob_machines:
        ld      a,(d_rec+D_SIZE)
        ld      hl,G_machine_count
        call    ob_addu
        ld      a,(hl)
        ld      (om_n),a
        call    om_prep
        xor     a
om_lp:
        call    ob_mach_one
        ld      a,(om_slot)
        inc     a
        ld      hl,om_n
        cp      (hl)
        jr      nz,om_lp
        jp      ob_b6

; om_prep — ο πίνακας των sprites και η τράπεζα όπου ζουν: μηχανές στην 5
; (βήμα 85, πάνω από το ευρετήριο), ή φυτά στην 7 όταν ο θόλος είναι
; θερμοκήπιο. Για το ob_machines και για τη λίστα (dh_mach).
om_prep:
        ld      hl,G_mach_ptr
        ld      bc,GA_PORT + PAGE_B5
        ld      a,(d_rec+D_ROOM)
        cp      R_GREENHS
        jr      nz,omp_set
        ld      hl,G_plant_ptr
        ld      c,PAGE_B7
omp_set:
        out     (c),c
        ld      (om_tab),hl
        ret

        assert  OI_END <= B5_BASE && B5_BASE + B5_LEN <= #8000

; ---------------------------------------------------------------------------
; ob_mach_one — ΜΙΑ υποδοχή. In: A = υποδοχή· το om_prep έχει τρέξει. Η
; λίστα αλλαγών (§8.5) ξαναζωγραφίζει μία υποδοχή όταν μια μηχανή χαλάσει ή
; ένα φυτό μεγαλώσει, και δεν έχει λόγο να δει τις άλλες επτά.
; ---------------------------------------------------------------------------
ob_mach_one:
        ld      (om_slot),a
        ld      hl,d_rec+D_MACH
        call    ob_addu
        ld      a,(hl)
        cp      NO_MACH
        ret     z
        add     a,a
        ld      hl,(om_tab)
        call    ob_addu
        ld      a,(hl)
        inc     hl
        ld      h,(hl)
        ld      l,a
        ld      (ob_src),hl
        ld      a,(om_slot)
        ld      de,G_machine_slots
        call    ob_slot_at
        inc     c
        ret     z                       ; px = 255: αυτή η υποδοχή δεν υπάρχει
        ld      hl,MACH_H*256 + MACH_W
        ld      a,4
        call    ob_put
        ; ΤΟ ΣΗΜΑ (βήμα 100): μια μηχανή που δεν δουλεύει παίρνει ένα σήμα πάνω
        ; αριστερά — χαλασμένη (υγεία 0, και μαραμένο φυτό) ή καινούργια που
        ; περιμένει να στηθεί (1-127, βήμα 99). Είναι μέσα στο αδιαφανές sprite
        ; της, οπότε όταν ξαναδουλέψει η υποδοχή ξαναζωγραφίζεται και σβήνει.
        ; Τα σήματα ζουν στην 5 (tools/pack.py): για τα φυτά, που ζουν στην 7,
        ; και για την επόμενη υποδοχή, το om_prep ξαναβάζει την τράπεζά τους.
        ld      a,(om_slot)
        ld      hl,d_rec+D_HEALTH
        call    ob_addu
        ld      a,(hl)
        add     a,a                     ; bit 7 -> CY: δουλεύει, κανένα σήμα
        ret     c
        ld      hl,G_marks              ; 0: χαλασμένη
        jr      z,omk_put
        ld      l,(G_marks + MARK_W * MARK_H) & 255     ; περιμένει
omk_put:
        call    ob_mark
        jp      om_prep

; ob_mark — HL = ένα σήμα (τράπεζα 5), αδιαφανές στο (ob_x, ob_y): για τις
; μηχανές, και από το βήμα 109 για τα εργοτάξια των δομών (st_mark).
; Γυρίζει με την 6.
ob_mark:
        ld      (ob_src),hl
        ld      hl,MARK_H*256 + MARK_W
        ld      a,4
        ld      c,PAGE_B5
        jp      ob_put_in

MARK_W      equ 2                       ; = MARK_W, MARK_H του tools/pack.py
MARK_H      equ 6
        assert  (G_marks & 255) + MARK_W * MARK_H <= 255     ; οι δύο αρχές, μία σελίδα (ld l)

; --- φιγούρες στις θέσεις του δακτυλίου ------------------------------------
; Το DOME_FIG γέμισε με ΕΝΑ πέρασμα πάνω στους 128 πράκτορες (ob_fig_scan).
; Χωρίς αυτό κάθε θόλος θα σάρωνε και τους 128, δηλαδή 8.192 αναγνώσεις.
;
; Η ΚΕΝΗ ΠΑΡΑΛΛΑΓΗ ΠΑΡΑΛΕΙΠΕΤΑΙ ΕΔΩ. Στην πλήρη σχεδίαση ο δακτύλιος — και το
; έδαφος κάτω από τα διαφανή του pixel — μόλις ζωγραφίστηκαν. Οταν ΦΕΥΓΕΙ
; ένας άποικος, η λίστα αλλαγών ξαναστρώνει έδαφος και αντικείμενα κάτω από
; τη θέση (dh_slot, βήμα 42): η κενή παραλλαγή είναι ο δακτύλιος πάνω σε
; μαύρο, και μόνη της άφηνε pen 0 εκεί που φαίνεται το έδαφος.
ob_figures:
        xor     a
of_lp:
        ld      (of_slot),a
        call    of_at
        or      a
        call    nz,obfo_have            ; A = η φιγούρα, (of_slot) = η θέση
        ld      a,(of_slot)
        inc     a
        cp      CORR_SLOTS
        jr      nz,of_lp
        ret

; of_at — A = θέση του θόλου d_id -> A = η φιγούρα της (0 = κενή).
of_at:
        ld      c,a
        ld      a,(d_id)
        ld      l,a
        ld      h,0
        add     hl,hl
        add     hl,hl
        add     hl,hl                   ; id*8 — ως 512, θέλει 16 bit
        ld      a,c
        or      l                       ; + θέση: τα τρία κάτω bits είναι 0
        ld      l,a
        ld      de,DOME_FIG
        add     hl,de
        ld      a,(hl)
        ret

; ---------------------------------------------------------------------------
; ob_fig_one — ΜΙΑ θέση δακτυλίου του θόλου d_id. In: A = θέση.
; Out: (of_fig) = η φιγούρα, ob_x / ob_y = η θέση.
;
; Η κενή θέση και η φιγούρα με μάσκα από πάνω της, σε ΕΝΑ πέρασμα (ob_fig),
; αδιαφανές — και αυτό αρκεί για να ΕΜΦΑΝΙΣΤΕΙ. Για να σβηστεί δεν αρκεί: η
; κενή θέση είναι ο δακτύλιος πάνω σε μαύρο, όχι πάνω στο έδαφος που δείχνουν
; τα διαφανή του pixel (dh_slot).
;
; ΑΠΟ ΤΟ ΒΗΜΑ 89 Η ΘΕΣΗ ΔΕΝ ΕΙΝΑΙ ΨΗΜΕΝΗ. Ως τότε ήταν ένα αδιαφανές blit από το
; corr_slot_gfx: κάθε φιγούρα ψημένη σε κάθε θέση, 3.456 bytes της τράπεζας 6.
; Η κενή με τη φιγούρα από πάνω είναι η ίδια εικόνα byte προς byte
; (tools/pack.py, check_ring), οι 3.072 bytes που έμειναν πήραν τις φιγούρες
; έξω, τον διάδρομο και τις πόρτες, και το ob_fig την κάνει πιο γρήγορα από
; ό,τι το ob_put το ένα blit.
; ---------------------------------------------------------------------------
ob_fig_one:
        ld      (of_slot),a
        call    of_at
obfo_have:                              ; από το ob_figures: το of_at έτρεξε ήδη
        ld      (of_fig),a
        ld      a,(of_slot)
        ld      de,G_corr_slots
        call    ob_slot_at
        ; η κενή: slot_empty + 16 * (size*8 + slot)
        ld      a,(d_rec+D_SIZE)
        add     a,a
        add     a,a
        add     a,a
        ld      hl,of_slot
        add     a,(hl)
        ld      l,a
        ld      h,0
        add     hl,hl
        add     hl,hl
        add     hl,hl
        add     hl,hl
        ld      de,G_slot_empty
        add     hl,de
        ld      b,h
        ld      c,l
        ; η φιγούρα: ο κωδικός της είναι το L της, και το bit 0 η σελίδα (βήμα
        ; 111, tools/pack.py: fig_code). Η κενή (0) μόνη της δεν ζωγραφίζεται:
        ; στην πλήρη σχεδίαση ο δακτύλιος είναι ήδη εκεί, και όταν αδειάζει η
        ; θέση το dh_slot ξαναστρώνει όλο το 2x8 (dhs_vacate).
        ld      a,(of_fig)
        or      a
        ret     z
        ld      l,a
        and     1
        add     a,G_fig_ring >> 8
        ld      h,a
        jp      ob_fig                  ; src/figure.asm
        assert  SLOT_SIZE == 16 && SLOT_FIGS <= 9 && (G_fig_ring & 255) == 160

; ---------------------------------------------------------------------------
; ob_corr — ένας διάδρομος. In: A = id διαδρόμου. Απαιτεί τράπεζα 6.
;
; Ο διάδρομος ζωγραφίζεται ΠΑΝΤΑ από την πλευρά του a: το `dir` είναι η
; κατεύθυνση a -> b, και τα οκτώ sprites είναι τέσσερα, το καθένα με δύο φορές.
; ---------------------------------------------------------------------------
ob_corr:
        ld      (oc_id),a
        ld      l,a
        ld      h,0
        ld      d,h
        ld      e,l
        add     hl,hl
        add     hl,hl                   ; 4*id
        add     hl,de                   ; 5*id
        ld      de,G_corr_tbl
        add     hl,de
        ; Η εγγραφή ΚΑΙ η επόμενη, σε c_rec και oc_cr, με ένα ldir: το αν
        ; ακολουθεί συνέχεια ρωτιέται ΕΔΩ, όσο η τράπεζα 6 είναι ακόμη στο
        ; παράθυρο — μετά το ob_getdome ο πίνακας διαδρόμων δεν φαίνεται πια.
        ; Η τελευταία εγγραφή διαβάζει 5 bytes έξω από τον πίνακα· η σύγκριση
        ; με το MAX_CORR πιο κάτω δεν τα κοιτάζει.
        ld      de,c_rec
        ld      bc,2 * CORR_REC
        ldir
        ld      a,(c_rec+C_CSTATE)
        or      a
        ret     z                       ; άδεια θέση
        ld      a,(c_rec+C_A)
        inc     a
        ret     z                       ; C_A = 255: ΣΥΝΕΧΕΙΑ διαδρομής — τη
                                        ; ζωγραφίζει η εγγραφή που την ξεκίνησε
        ld      b,0                     ; oc_cont
        ld      a,(oc_id)
        inc     a
        cp      MAX_CORR
        jr      nc,occ_nocont           ; τελευταία εγγραφή — δεν έχει επόμενη
        ld      a,(oc_cr+C_A)
        inc     a
        jr      nz,occ_nocont
        ld      a,(oc_cr+C_CSTATE)
        or      a
        jr      z,occ_nocont
        inc     b
occ_nocont:
        ld      a,b
        ld      (oc_cont),a
        ld      a,(ob_meas)
        or      a
        call    nz,jt_mark              ; οι αρμοί του a και του b (src/joint.asm)
        ; Οι διάδρομοι έρχονται σε σειρά και μοιράζονται αφετηρία: μισοί από
        ; αυτούς ξεκινούν από τον ίδιο θόλο με τον προηγούμενο. Δύο εντολές
        ; γλιτώνουν την αντιγραφή 24 bytes και τον υπολογισμό του πλαισίου.
        ld      a,(c_rec+C_A)
        ld      hl,d_id
        cp      (hl)
        call    nz,ob_getdome
        call    oc_setdir
        ld      a,(oc_diag)
        or      a
        jr      nz,ob_corr_d
        ; --- αξονικός: από το σημείο σύνδεσης, προς τα έξω ---
        ld      a,(c_rec+C_DIR)
        ld      de,G_conn_points
        call    ob_slot_at
        ld      hl,oc_ox
        call    ob_move
        jr      ob_corr_run

; oc_setdir — sprite, διαστάσεις, βήμα, μετατόπιση και «διαγώνιος;» από τον
; πίνακα corr_dir: εννέα bytes, που πέφτουν με τη σειρά τους στα ob_src, ob_w,
; ob_h, oc_dx, oc_dy, oc_ox, oc_oy, oc_diag (βλ. τις μεταβλητές).
oc_setdir:
        ld      a,(c_rec+C_DIR)
        and     7
        ld      c,a
        add     a,a
        add     a,a
        add     a,a
        add     a,c                     ; dir*9
        add     a,corr_dir & 255
        ld      l,a
        adc     a,corr_dir >> 8
        sub     l
        ld      h,a
        ld      de,ob_src
        ld      bc,9
        ldir
        ret

ob_corr_d:
        ; --- διαγώνιος: πλέγμα DIAG_K από το ΚΕΝΤΡΟ του θόλου ---
        ld      a,(d_rec+D_SIZE)
        add     a,diag_k & 255
        ld      l,a
        adc     a,diag_k >> 8
        sub     l
        ld      h,a
        ld      b,(hl)
        push    bc
        call    ob_center
        ld      hl,diag_ofs
        call    ob_move
        pop     bc
        ld      hl,oc_dx
        call    ob_movek
ob_corr_run:
        ld      a,(c_rec+C_LEN)
        or      a
        ret     z
        ld      (oc_n),a
        ; Πού ΑΡΧΙΖΕΙ αυτό το τρέξιμο, για τη στροφή: από εκεί το oc_bend
        ; βρίσκει το τελευταίο του πλακίδιο — υπολογισμένο, όχι μετρημένο από
        ; τον βρόχο: το κουτί μπορεί να είναι όλο εκτός κάδρου και ο βρόχος να
        ; μην τρέξει καθόλου, ενώ η συνέχεια μπορεί κάλλιστα να φαίνεται.
        ld      hl,(ob_x)
        ld      (oc_lx),hl
        ld      hl,(ob_y)
        ld      (oc_ly),hl
        ld      a,(oc_cont)
        or      a
        jr      z,oc_run                ; ίσιος: ένα τρέξιμο, που γυρίζει στον καλούντα
        call    cn_pre                  ; η γωνία (βήμα 129, src/corner.asm)
        call    oc_run
        call    oc_bend
        jp      cn_post                 ; η γωνία, το αξονικό, το μπάλωμα

; ---------------------------------------------------------------------------
; oc_bend — η στροφή διαγώνιος -> άξονας (§9.4, και tools/route.py).
;
; Το διαγώνιο πλακίδιο είναι δύο tiles φαρδύ και ένα ψηλό, με το σημείο
; πλέγματός του στο πάνω-αριστερά + (4, 8). Η οριζόντια λωρίδα πιάνει το ΠΑΝΩ
; μισό της σειράς της, η κάθετη το ΑΡΙΣΤΕΡΟ μισό της στήλης της — γι' αυτό οι
; δύο στροφές δεν έχουν τον ίδιο τύπο.
; ---------------------------------------------------------------------------
oc_bend:
        ; --- το τελευταίο διαγώνιο: το πρώτο, συν (n-1) βήματα ---
        ld      hl,(oc_lx)
        ld      (ob_x),hl
        ld      hl,(oc_ly)
        ld      (ob_y),hl
        ld      a,(c_rec+C_LEN)
        dec     a
        ld      b,a
        ld      hl,oc_dx
        call    ob_movek
        ; --- και η συνέχεια ---
        ld      hl,(oc_dx)              ; το βήμα της διαγωνίου, πριν φύγει
        push    hl
        ld      hl,oc_cr
        ld      de,c_rec
        ld      bc,CORR_REC
        ldir
        call    oc_setdir
        pop     hl                      ; L = dx, H = dy της διαγωνίου
        ld      a,(oc_dx)
        or      a
        jr      z,ocb_v
        ; --- οριζόντια: το πρώτο πλακίδιο κάθεται ΠΑΝΩ στο τελευταίο διαγώνιο,
        ; στο μισό του που βλέπει προς τον θόλο αφετηρίας: (dx < 0 ? 4 : 0, 8).
        ld      a,l
        rla
        sbc     a,a
        and     4
        ld      l,a
        ld      h,4
        jr      ocb_go
ocb_v:
        ; --- κάθετη: η λωρίδα περνά από το ΚΕΝΤΡΟ του θόλου προορισμού, που
        ; είναι ένα σημείο πλέγματος πιο πέρα από το τελευταίο διαγώνιο:
        ; (dx + 4, dy / 2).
        ld      a,l
        add     a,3
        ld      l,a
        sra     h
ocb_go:
        ld      (oc_lx),hl              ; ως ζεύγος για το ob_move
        ld      hl,oc_lx
        call    ob_move
        ld      a,(c_rec+C_LEN)
        ld      (oc_n),a
        ret

oc_run:
        ld      a,(oc_n)
        or      a
        ret     z
        ld      a,(ob_meas)
        or      a
        jp      nz,oc_meas              ; src/objindex.asm
        ; --- κουτί οριοθέτησης ολόκληρης της διαδρομής ---
        ; Το cl_lo/cl_hi μπαίνει ΠΡΙΝ το ob_box: το ob_box γυρίζει HL και DE,
        ; και ένα ld hl,(clip_x0) μετά θα τα έτρωγε.
        ld      hl,(clip_x0)
        ld      (cl_lo),hl
        ld      a,(oc_dx)
        ld      c,a
        ld      hl,(ob_x)
        ld      a,(ob_w)
        call    ob_box
        call    ob_ovl
        or      a
        ret     z
        ld      hl,(clip_y0)
        ld      (cl_lo),hl
        ld      a,(oc_dy)
        ld      c,a
        ld      hl,(ob_y)
        ld      a,(ob_h)
        call    ob_box
        call    ob_ovl
        or      a
        ret     z
        xor     a
        ld      (ob_fl),a               ; το ob_blit δεν το πειράζει
occ_lp:
        call    ob_blit
        ld      hl,oc_dx
        call    ob_move
        ld      hl,oc_n
        dec     (hl)
        jr      nz,occ_lp
        ret

; ---------------------------------------------------------------------------
; ob_box — το εύρος μιας διαδρομής σε έναν άξονα.
; In :  HL = θέση πρώτου πλακιδίου, C = βήμα (προσημασμένο), A = πλάτος sprite,
;       (oc_n) = πλήθος πλακιδίων
; Out:  HL = αρχή, DE = μήκος
; ---------------------------------------------------------------------------
ob_box:
        ld      (obx_w),a
        ld      a,c
        or      a
        jr      nz,obx_move
        ld      a,(obx_w)               ; ακίνητος άξονας: μόνο το sprite
        ld      e,a
        ld      d,0
        ret
obx_move:
        ld      (obx_sgn),a             ; το πρόσημο, πριν το neg
        or      a
        jp      p,obx_pos
        neg
obx_pos:
        ld      c,a                     ; |βήμα|: 4 ή 16 (corr_dir)
        ld      a,(oc_n)
        dec     a                       ; k = n-1
        push    hl
        ; ΜΕ ΟΛΙΣΘΗΣΕΙΣ, ΟΧΙ ΜΕ ΤΟ ob_mul (βήμα 96): το βήμα ενός διαδρόμου
        ; είναι 4 bytes ή 16 γραμμές, και ο γενικός πολλαπλασιασμός έκανε οκτώ
        ; γύρους, ~100 us σε κάθε άξονα κάθε τρεξίματος — στη μέτρηση του
        ; ευρετηρίου και σε κάθε σχεδίαση. Αυτό πλήρωσε το jt_mark του 96.
        ld      l,a
        ld      h,0
        add     hl,hl
        add     hl,hl                   ; k x 4
        bit     4,c
        jr      z,obx_4
        add     hl,hl
        add     hl,hl                   ; k x 16
obx_4:
        ld      d,h
        ld      e,l                     ; DE = απόσταση
        pop     hl
        push    de
        ld      a,(obx_w)
        ld      c,a
        ld      b,0
        ex      de,hl
        add     hl,bc
        ex      de,hl                   ; DE = απόσταση + πλάτος
        pop     bc                      ; BC = απόσταση
        ld      a,(obx_sgn)
        or      a                       ; και CY = 0, για το sbc
        ret     p
        sbc     hl,bc                   ; αρνητικό βήμα: αρχή = τελευταίο πλακίδιο
        ret

; ob_addsx — HL += A προσημασμένο.
ob_addsx:
        ld      e,a
        rla
        sbc     a,a
        ld      d,a                     ; DE = sext(A)
        add     hl,de
        ret

; ---------------------------------------------------------------------------
; ob_struct — μία εξωτερική δομή. In: A = id. Απαιτεί τράπεζα 6 στην είσοδο·
; γυρίζει με την 6 μέσα.
; ---------------------------------------------------------------------------
ob_struct:
        add     a,a
        add     a,a
        add     a,a                     ; 8*id: μία σελίδα (assert)
        ld      l,a
        ld      h,G_struct_tbl >> 8
        ld      de,s_rec                ; πρώτα η αντιγραφή, μετά η ερώτηση:
        ld      bc,STRUCT_REC           ; το s_rec είναι πρόχειρο
        ldir
        ld      a,(s_rec+ST_STATE)
        or      a
        ret     z
        ; (kind*4 + size)*2: ο ίδιος δείκτης για το struct_dims (δύο bytes
        ; ανά μέγεθος) και για το struct_ptr (μία λέξη ανά μέγεθος).
        ld      a,(s_rec+ST_KIND)
        add     a,a
        add     a,a
        ld      hl,s_rec+ST_SIZE
        add     a,(hl)
        add     a,a
        ld      c,a
        add     a,G_struct_dims & 255
        ld      l,a
        adc     a,G_struct_dims >> 8
        sub     l
        ld      h,a
        ld      a,(hl)
        or      a
        ret     z                       ; 0,0 = αυτό το μέγεθος δεν υπάρχει
        ld      e,a
        inc     hl
        ld      d,(hl)
        ld      (ob_w),de
        ; θέση: κέντρο μείον το μισό πλαίσιο — το C περνά από κάτω ανέγγιχτο
        ld      a,(s_rec+ST_CX)
        call    ob_sx
        ld      a,(ob_w)
        srl     a
        call    ob_subu
        ld      (ob_x),hl
        ld      a,(s_rec+ST_CY)
        call    ob_sy
        ld      a,(ob_h)
        srl     a
        call    ob_subu
        ld      (ob_y),hl
        ld      a,c
        ; πηγή από το struct_ptr, και η πλατφόρμα είναι η μόνη ΑΔΙΑΦΑΝΗ
        add     a,G_struct_ptr & 255
        ld      l,a
        adc     a,G_struct_ptr >> 8
        sub     l
        ld      h,a
        ld      a,(hl)
        inc     hl
        ld      h,(hl)
        ld      l,a
        or      h
        ret     z
        ld      (ob_src),hl
        ld      a,(s_rec+ST_KIND)
        cp      K_PAD
        ld      a,4
        jr      z,os_opaque
        xor     a
os_opaque:
        ld      (ob_fl),a
        ld      e,a
        ld      a,(ob_meas)
        or      a
        jp      nz,os_meas              ; src/objindex.asm
        ld      hl,(ob_w)
        ld      a,e                     ; (ob_fl)
        ld      c,PAGE_B7
        call    ob_put_in
        jp      st_mark                 ; src/figure.asm: το εργοτάξιο (βήμα 109)

; ---------------------------------------------------------------------------
; ob_fig_scan — DOME_FIG[64][8]: ποια φιγούρα σε ποια θέση ποιου θόλου.
; Ενα πέρασμα στους 128 πράκτορες. 0 = κενή, και η κενή ΔΕΝ σχεδιάζεται στην
; πλήρη σχεδίαση — ο δακτύλιος μόλις ζωγραφίστηκε.
; ---------------------------------------------------------------------------
ob_fig_scan:
        ld      hl,DOME_FIG
        ld      de,DOME_FIG+1
        ld      bc,64*8-1
        ld      (hl),0
        ldir
        ld      b,128
        ld      c,0
ofs_lp:
        push    bc
        ld      l,c
        ld      h,AG_FLAGS >> 8
        ld      a,(hl)
        and     OB_ALIVE
        jr      z,ofs_next
        ld      h,AG_NODE >> 8
        set     7,l
        ld      a,(hl)                  ; slot
        cp      255
        jr      z,ofs_next
        ld      b,a                     ; B = slot: το pop bc τα ξαναφέρνει
        res     7,l
        ld      a,(hl)                  ; node
        cp      MAX_DOME
        jr      nc,ofs_next             ; δομή, όχι θόλος
        ld      c,a                     ; C = node
        ld      h,AG_FLAGS >> 8
        set     7,l
        ld      a,(hl)                  ; role
        and     15                      ; 0-9: ο εισβολέας ο 8 (βήμα 111), ο επισκέπτης ο 9 (136)
        ld      l,a
        ld      h,0
        ld      de,role_fig
        add     hl,de
        ld      e,(hl)                  ; E = η φιγούρα
        ld      l,c
        ld      h,0
        add     hl,hl
        add     hl,hl
        add     hl,hl                   ; node*8
        ld      a,b
        and     7
        or      l                       ; + slot: τα τρία κάτω bits είναι 0
        ld      l,a
        ld      bc,DOME_FIG
        add     hl,bc
        ld      (hl),e
ofs_next:
        pop     bc
        inc     c
        djnz    ofs_lp
        ret

; ---------------------------------------------------------------------------
; ob_draw_all — όλη η σκηνή, μέσα στο τρέχον clip.
;
; ΑΠΟ ΤΟ ΕΥΡΕΤΗΡΙΟ, ΟΧΙ ΑΠΟ ΤΟΥΣ ΠΙΝΑΚΕΣ (βήμα 39). Ως τότε κάθε κλήση ρωτούσε
; 64 θόλους δύο φορές, 96 διαδρόμους και όλες τις δομές, και για να πει «όχι»
; κάθε ζωντανό αντικείμενο αντέγραφε την εγγραφή του, υπολογίζε πλαίσιο και
; τρεξίματα: 49 ms για μια αποικία 12 θόλων όπου ΤΙΠΟΤΑ δεν φαινόταν. Το
; ευρετήριο κρατά για κάθε ζωντανό αντικείμενο το περίγραμμά του σε tiles του
; κόσμου, με τη σειρά σχεδίασης, και το «όχι» είναι τέσσερις συγκρίσεις.
; Ό,τι περνά πηγαίνει στις ίδιες ρουτίνες με πριν, που κόβουν ακριβώς.
; ---------------------------------------------------------------------------
ob_draw_all:
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        call    ob_index
        call    oi_window
        ; ΚΑΝΕΝΑΣ ΘΟΛΟΣ ΣΤΗ ΜΝΗΜΗ ΤΟΥ ob_corr. Το ob_corr δεν ξαναδιαβάζει τον
        ; θόλο αφετηρίας αν είναι ο d_id· ως τώρα το πέρασμα κελυφών τον
        ; διάβαζε πάντα με την τρέχουσα κάμερα. Τώρα διαβάζει μόνο όσους
        ; φαίνονται, και ο d_id μπορεί να είναι από άλλη κάμερα — ή από το
        ; (0, 0) του oi_build.
        ld      a,255
        ld      (d_id),a
        ld      hl,OI_CORR
        ld      a,(oi_nc)
        ld      de,ob_corr
        call    oi_walk
        ld      hl,OI_DOME
        ld      a,(oi_nd)
        ld      de,ob_shell
        call    oi_walk
        ld      hl,OI_DOME
        ld      a,(oi_nd)
        ld      de,ob_fittings
        call    oi_walk
        ld      hl,OI_STRUCT
        ld      a,(oi_ns)
        ld      de,ob_struct
        call    oi_walk
        call    fg_draw                 ; οι άποικοι έξω, πάνω από όλα (βήμα 89)
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        ret

; oi_walk — HL = η πρώτη εγγραφή (τράπεζα 5), A = πόσες, DE = η ρουτίνα που
; ζωγραφίζει (A = id, τράπεζα 6). Για όσες τέμνουν το παράθυρο (oi_window).
oi_walk:
        or      a
        ret     z
        ld      (oiw_fn),de
        ld      b,a
        ld      de,(oi_wx0)             ; E = wx0, D = wx1
        ld      a,b
        ld      bc,GA_PORT + PAGE_B5
        out     (c),c
        ld      b,a
oiw_lp:
        push    hl
        ld      a,(hl)                  ; x0 < wx1;
        cp      d
        jr      nc,oiw_no
        inc     hl
        ld      a,e                     ; wx0 < x1;
        cp      (hl)
        jr      nc,oiw_no
        inc     hl
        ld      a,(oi_wy1)              ; y0 < wy1;
        cp      (hl)
        jr      c,oiw_no
        jr      z,oiw_no
        inc     hl
        ld      a,(oi_wy0)              ; wy0 < y1;
        cp      (hl)
        jr      nc,oiw_no
        inc     hl
        ld      a,(hl)                  ; το id
        push    bc
        push    de
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        call    oiw_go
        ld      bc,GA_PORT + PAGE_B5
        out     (c),c
        pop     de
        pop     bc
oiw_no:
        pop     hl
        ld      a,l
        add     a,OI_REC
        ld      l,a
        jr      nc,oiw_nx
        inc     h
oiw_nx:
        djnz    oiw_lp
        jp      ob_b6
oiw_go:
        ld      hl,(oiw_fn)
        jp      (hl)

; oi_window — το clip σε tiles του κόσμου, +128 ώστε οι συγκρίσεις να είναι
; ανυπόγραφες: [wx0, wx1) x [wy0, wy1), στρογγυλεμένο προς τα έξω.
; Τα clip_x0..clip_y1 και oi_wx0..oi_wy1 είναι με την ίδια σειρά.
oi_window:
        ld      hl,clip_x0
        ld      de,oi_wx0
        ld      a,(cam_tx)
        ld      b,%11111100             ; tiles των 4 bytes
        call    oiw_axis
        ld      a,(cam_ty)
        ld      b,%11110000             ; tiles των 16 γραμμών
; oiw_axis — HL -> (lo, hi) του clip, DE -> (w0, w1), A = κάμερα, B = μάσκα.
oiw_axis:
        add     a,128
        ld      c,a
        ld      a,(hl)                  ; lo, προς τα κάτω
        call    oiw_cv
        ld      a,b
        cpl                             ; tile - 1
        add     a,(hl)                  ; hi, προς τα πάνω
; oiw_cv — A στρογγυλεμένο από τη μάσκα, / tile, + κάμερα -> (DE); HL++, DE++.
oiw_cv:
        and     b
        push    bc
oiw_sh:
        rrc     b                       ; τα μηδενικά της μάσκας μετρούν τις
        jr      c,oiw_d                 ; ολισθήσεις: 2 για x, 4 για y
        rrca
        jr      oiw_sh
oiw_d:
        pop     bc
        add     a,c
        ld      (de),a
        inc     hl
        inc     de
        ret

; ob_index — τα ευρετήρια (οι φιγούρες, και τα αντικείμενα ανά κατηγορία· με
; των διαδρόμων και οι αρμοί, βήμα 96) που ακύρωσε το ob_touch. Απαιτεί τράπεζα 6. Και για όποιον
; ζωγραφίζει ΕΝΑΝ θόλο χωρίς το ob_draw_all.
ob_index:
        ld      hl,ob_idx
        ld      a,(hl)
        or      a
        ret     z
        ld      (hl),0
        rra                             ; το or μηδένισε το carry
        jp      nc,oi_build             ; src/objindex.asm, τράπεζα 2
        push    af                      ; οι κατηγορίες, για το oi_build
        call    ob_fig_scan
        pop     af
        jp      oi_build

; jt_clear — ΟΙ ΑΡΜΟΙ (βήμα 96): το dome_conn το γράφει η μέτρηση των
; διαδρόμων (jt_mark, src/joint.asm), άρα σβήνεται όταν ξαναχτίζονται αυτοί —
; από το oi_build, ώστε οι άλλες κατηγορίες να μην πληρώνουν τίποτα.
jt_clear:
        ld      hl,dome_conn
        ld      de,dome_conn+1
        ld      bc,MAX_DOME-1
        ld      (hl),b                  ; B = 0
        ldir
        ld      a,#C9                   ; ret: καμία κοντή στροφή ακόμη (jtd_sw)
        ld      (jtd_sw),a
        ld      hl,jtb_clr              ; και οι σημαίες τους (βήμα 97)
        jr      jt_b6

; jtd_end — το τέλος του jt_dome (b6code): τα pixels των κοντών στροφών του
; θόλου (jtb_dome, src/bend.asm). ΕΝΑΣ ΔΙΑΚΟΠΤΗΣ: το πρώτο byte είναι ret
; (#C9) όσο η αποικία δεν έχει καμία κοντή στροφή — το γράφει το jt_clear,
; πριν από τη μέτρηση των διαδρόμων — και jp jtb_dome (#C3) από τη στιγμή
; που το jtm_bend βρει μία (ως το βήμα 128 ld hl,jtb_dome και το jt_b5 από
; κάτω: το jtb_dome ήταν στην 5). Ετσι ένας θόλος με αρμούς πληρώνει ένα jp, 3 µs,
; και όχι τον έλεγχο της σημαίας: ως το βήμα 128, με το jt_b5, ~65 µs ο θόλος
; με αρμό ανατολικά ή δυτικά, +696 µs στις πέντε κάμερες του tests/
; test_object.py, όπου δεν υπάρχει καμία κοντή στροφή. Με κοντές στροφές στην
; αποικία, κάθε θόλος με αρμούς περνά από το jtb_dome, χωρίς αλλαγή τράπεζας.
jtd_end:
jtd_sw:
        ret
        dw      jtb_dome
        assert  $ == jtd_sw + 3         ; #C3 = jp jtb_dome
; jt_b6 — HL = ρουτίνα του src/bend.asm: την τρέχει με την τράπεζα 6 στο
; παράθυρο και γυρίζει με την 6 — ή, από το jt_b6c, με ό,τι ανοίγει η ρουτίνα
; στο DE (το dt_end ανοίγει την 1). Το A περνά όπως είναι· BC και DE χαλάνε.
; Για όσους δεν ξέρουν ποια τράπεζα έχουν: το jt_clear και το crr_conns. Ως το
; βήμα 128 jt_b5, με την 5: εκεί ζούσε το bend.asm.
jt_b6:
        ld      de,ob_b6
jt_b6c:
        push    de
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        jp      (hl)

; ---------------------------------------------------------------------------
; ob_struct_sort — st_ord[st_n]: οι ζωντανές δομές κατά cy, ώστε οι νότιες να
; σκεπάζουν τις βόρειες (§8.4). Ταξινόμηση με παρεμβολή, ο πίνακας είναι ήδη
; σχεδόν ταξινομημένος. Από το βήμα 39 τρέχει μόνο όταν χτίζεται το
; ευρετήριο, όχι σε κάθε σχεδίαση· μένει εδώ, στην τράπεζα 0, γιατί το
; objindex.asm δεν χωρούσε ολόκληρο στην τράπεζα 2 (βήμα 41).
; ---------------------------------------------------------------------------
ob_struct_sort:
        ld      hl,G_struct_tbl + ST_STATE
        ld      de,st_ord
        ld      bc,MAX_STRUCT * 256     ; B = πόσες, C = id
osa_gather:
        ld      a,(hl)
        or      a
        jr      z,osa_gskip
        ld      a,c
        ld      (de),a
        inc     de
osa_gskip:
        ld      a,l
        add     a,STRUCT_REC            ; μία σελίδα (assert)
        ld      l,a
        inc     c
        djnz    osa_gather
        ld      a,e
        sub     st_ord & #FF            ; πόσες μπήκαν: < 256, άρα αρκεί το
        ld      (st_n),a                ; κάτω byte, όπου κι αν πέφτει το st_ord
        cp      2
        ret     c
        ; --- ταξινόμηση με παρεμβολή πάνω στο cy ---
        ; HL -> st_ord[j], D = το id που μπαίνει, E = το κλειδί του.
        dec     a
        ld      b,a
        ld      hl,st_ord+1
osa_out:
        push    bc
        push    hl
        ld      d,(hl)
        ld      a,d
        call    osa_key
        ld      e,a
osa_in:
        ld      a,l
        cp      st_ord & #FF            ; j = 0; τα 32 κάτω bytes είναι μοναδικά
        jr      z,osa_place
        dec     hl
        ld      a,(hl)
        call    osa_key                 ; το κλειδί του st_ord[j-1]
        cp      e
        jr      c,osa_put
        jr      z,osa_put               ; ίσο: μένει μπροστά — σταθερή
        ld      a,(hl)                  ; st_ord[j] = st_ord[j-1]
        inc     hl
        ld      (hl),a
        dec     hl
        jr      osa_in
osa_put:
        inc     hl
osa_place:
        ld      (hl),d
        pop     hl
        inc     hl
        pop     bc
        djnz    osa_out
        ret

; osa_key — A = id -> A = cy+128. Κρατά τα BC, DE, HL.
osa_key:
        push    hl
        add     a,a
        add     a,a
        add     a,a
        add     a,ST_CY
        ld      l,a
        ld      h,G_struct_tbl >> 8
        ld      a,(hl)
        add     a,128
        pop     hl
        ret
; ob_struct, osa_gskip, osa_key: id*8 + ST_* σε μία σελίδα (βήμα 100)
        assert  (G_struct_tbl & 255) == 0 && MAX_STRUCT * STRUCT_REC == 256

; ---------------------------------------------------------------------------
; ob_touch — τα ευρετήρια είναι παλιά· ξαναχτίσου στην επόμενη σχεδίαση.
; ob_touch_a — μόνο όσα λέει το A (OB_IX_*). ob_touch_n — A = ο κόμβος που
; μόλις μπήκε: οι φιγούρες (ως το 95 και οι πόρτες) και η κατηγορία του. Κρατά το A.
;
; Χωρίς αυτό, οι δύο σαρώσεις (96 διάδρομοι + 128 πράκτορες) έτρεχαν σε ΚΑΘΕ
; βήμα σκρολαρίσματος — 0,8 frames για δεδομένα που δεν είχαν αλλάξει.
; ---------------------------------------------------------------------------
ob_touch_n:
        push    af
        cp      MAX_DOME
        ld      a,OB_IX_FIG + OB_IX_DOME
        jr      c,obt_n
        ld      a,OB_IX_FIG + OB_IX_STRUCT
obt_n:
        call    ob_touch_a
        pop     af
        ret
ob_touch:
        ld      a,OB_IX_ALL
ob_touch_a:
        ld      hl,ob_idx
        or      (hl)
        ld      (hl),a
        ret

; ---------------------------------------------------------------------------
; ob_clip_full / ob_clip_set — το παράθυρο σχεδίασης.
; ---------------------------------------------------------------------------
ob_clip_full:
        ld      hl,SCR_W * 256
        ld      (clip_x0),hl
        ld      hl,PLAY_LINES * 256
        ld      (clip_y0),hl
        ret

; --- πίνακες ---------------------------------------------------------------
; Ανά μέγεθος θόλου: QW, QH, dome_nw, ring_nw, icon_ptr, icon_w, icon_h
dome_geo:
        db      DOME_S_W, DOME_S_H
        dw      G_dome_s_nw, G_ring_s_nw, G_icon_s_ptr
        db      ICON_S_W, ICON_S_H
        db      DOME_M_W, DOME_M_H
        dw      G_dome_m_nw, G_ring_m_nw, G_icon_m_ptr
        db      ICON_M_W, ICON_M_H
        db      DOME_L_W, DOME_L_H
        dw      G_dome_l_nw, G_ring_l_nw, G_icon_l_ptr
        db      ICON_L_W, ICON_L_H

; Ρόλος της προσομοίωσης -> φιγούρα της τέχνης (SPRITES.md §7).
; Δεν είναι ταυτοτικό: η τέχνη έχει τέσσερα ρομπότ και η προσομοίωση τρία, με
; τον ΜΗΧΑΝΙΚΟ ΑΝΘΡΩΠΟ. Ο μηχανικός παίρνει τη φιγούρα 7 (κυανό) γιατί σε 6x6
; pixel το χρώμα είναι η ταυτότητα. Από το βήμα 111 ο ΚΩΔΙΚΑΣ της φιγούρας,
; όχι ο αριθμός της (build/layout.asm, FC_*), και ο ένατος ρόλος: ο εισβολέας.
; Από το βήμα 136 και ο δέκατος, ο επισκέπτης (RL_VIS).
; Σε μία σελίδα (το assert του src/figure.asm, που διαβάζει με and 15). Τα
; τρία builds που έχουν το object.asm (το παιχνίδι, tests/objtest.asm,
; uitest.asm) το βάζουν σε άλλη διεύθυνση το καθένα, και στο βήμα 129 έπεσε
; πρώτα στο τέλος σελίδας στο ένα και μετά στο άλλο. Ο φύλακας συμπληρώνει ως
; την επόμενη σελίδα μόνο όταν χρειάζεται — στο βήμα 129 σε κανένα από τα τρία.
        if      ($ & 255) > 256 - 16
        defs    256 - ($ & 255)
        endif
role_fig:
        db      FC_COLONIST, FC_ENGINEER, FC_BIOLOGIST, FC_MEDIC, FC_GUARD
        db      FC_CONSTRUCTOR, FC_CARRIER, FC_DRILLER, FC_INTRUDER, FC_VISITOR
        assert  RL_FOE == 8 && RL_VIS == 9

; Ανά κατεύθυνση: sprite, w, h, βήμα x, βήμα y, μετατόπιση αρχής x, y, διαγώνιος;
; (Τα βήματα 0, ±4, ±16: το ob_box τα πολλαπλασιάζει με ολισθήσεις.)
corr_dir:
        dw G_corr_v  : db CORR_V_W, CORR_V_H,  0,-16, -1,-16, 0   ; n
        dw G_corr_dl : db CORR_D_W, CORR_D_H,  4,-16,  0,  0, 1   ; ne
        dw G_corr_h  : db CORR_H_W, CORR_H_H,  4,  0,  2, -4, 0   ; e
        dw G_corr_dr : db CORR_D_W, CORR_D_H,  4, 16,  0,  0, 1   ; se
        dw G_corr_v  : db CORR_V_W, CORR_V_H,  0, 16, -1,  8, 0   ; s
        dw G_corr_dl : db CORR_D_W, CORR_D_H, -4, 16,  0,  0, 1   ; sw
        dw G_corr_h  : db CORR_H_W, CORR_H_H, -4,  0, -4, -4, 0   ; w
        dw G_corr_dr : db CORR_D_W, CORR_D_H, -4,-16,  0,  0, 1   ; nw

; Από ποιο βήμα του πλέγματος ξεκινά ο διαγώνιος, ανά μέγεθος θόλου, και
; από πού μετριέται: το κέντρο μείον (4, 8).
diag_k:
        db      2, 3, 3
diag_ofs:
        db      -4, -8

; --- μεταβλητές ------------------------------------------------------------
ob_idx:     db OB_IX_ALL        ; ποια ευρετήρια θέλουν ξαναχτίσιμο (OB_IX_*)
d_id:       db 0                ; ο θόλος στο d_rec (ob_getdome)· 255 = κανένας
ob_meas:    db 0                ; 1 = μέτρα, μη ζωγραφίζεις (oi_build)
oi_nd:      db 0                ; εγγραφές ευρετηρίου: θόλοι,
oi_nc:      db 0                ; διάδρομοι,
oi_ns:      db 0                ; δομές
oi_wx0:     db 0                ; το clip σε tiles +128 — wx0, wx1 ΜΑΖΙ (oi_walk)
oi_wx1:     db 0
oi_wy0:     db 0
oi_wy1:     db 0
oiw_fn:     dw 0
clip_x0:    db 0
clip_x1:    db SCR_W
clip_y0:    db 0
clip_y1:    db PLAY_LINES

ob_x:       dw 0
ob_y:       dw 0
; Τα εννέα bytes μιας γραμμής του corr_dir πέφτουν εδώ με ΕΝΑ ldir (oc_setdir),
; και τα ob_w, ob_h γράφονται μαζί (ob_put): η σειρά είναι συμβόλαιο.
ob_src:     dw 0
ob_w:       db 0
ob_h:       db 0
oc_dx:      db 0
oc_dy:      db 0
oc_ox:      db 0
oc_oy:      db 0
oc_diag:    db 0
ob_fl:      db 0
ob_st:      db 0                ; πόσες γραμμές κόπηκαν από πάνω
ob_nl:      db 0                ; πόσες μένουν
ob_y0:      db 0
ob_spt:     dw 0                ; ο πίνακας διαστημάτων (src/span.asm)· H = 0: κανένας
obl_c:      db 0                ; γραμμές ως το τέλος του κομματιού

; Ο οριζόντιος άξονας του ob_blit ΔΕΝ αντιγράφεται: διαβάζει κατευθείαν τα
; cl_skip, cl_n, cl_start του δεύτερου ob_clip.
cl_len:     db 0
cl_lo:      db 0
cl_hi:      db 0
cl_skip:    db 0
cl_n:       db 0
cl_start:   db 0

d_rec:      defs DOME_REC
d_geo:      dw 0
d_fx:       dw 0
d_fy:       dw 0
d_qw:       db 0
d_qh:       db 0

s_rec:      defs STRUCT_REC
c_rec:      defs CORR_REC
oc_cr:      defs CORR_REC       ; η ΕΠΟΜΕΝΗ εγγραφή, με το ίδιο ldir (ob_corr)

oq_cur:     db 0
oc_n:       db 0
oc_id:      db 0
oc_cont:    db 0
oc_lx:      dw 0                ; το πρώτο πλακίδιο του τρεξίματος· στο
oc_ly:      dw 0                ; oc_bend και ζεύγος (dx, dy) για το ob_move

om_n:       db 0
om_slot:    db 0
om_tab:     dw 0                ; G_mach_ptr ή G_plant_ptr (om_prep)

of_slot:    db 0
of_fig:     db 0


st_n:       db 0
obx_w:      db 0
obx_sgn:    db 0

; Δύο ευρετήρια που χτίζονται με ΕΝΑ πέρασμα και γλιτώνουν δύο βρόχους:
;   dome_conn[64]     ποιοι αρμοί κάθε θόλου (ως το 95 οι πόρτες): τα bits τα
;                     ανάβει η μέτρηση των διαδρόμων (jt_mark, src/joint.asm)
;   DOME_FIG[64][8]   ποια φιγούρα σε κάθε θέση      (αλλιώς 64 x 128)
st_ord:     defs MAX_STRUCT
dome_conn:  defs MAX_DOME

        assert  ob_w == ob_src + 2 && ob_h == ob_w + 1 && oc_diag == ob_src + 8
        assert  ob_nl == ob_st + 1 && cl_n == cl_skip + 1 && cl_hi == cl_lo + 1
        assert  d_qh == d_qw + 1 && oc_cr == c_rec + CORR_REC
        assert  clip_y1 == clip_x0 + 3 && oi_wy1 == oi_wx0 + 3
