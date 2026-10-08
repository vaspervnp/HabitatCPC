; figure.asm — οι άποικοι ΕΞΩ (βήμα 89, DESIGN §8.4, §8.5).
;
; Ως το βήμα 88 ένας άποικος φαινόταν μόνο στις οκτώ θέσεις του δακτυλίου ενός
; θόλου. Στο σκάφος, σε μια δομή και στο έδαφος ανάμεσα ήταν παρών και αόρατος
; — και από το βήμα 87 η αρχή είναι τέσσερις άνθρωποι δίπλα στο σκάφος, άρα η
; πρώτη οθόνη του παιχνιδιού έδειχνε το σκάφος και κανέναν. Εδώ φαίνονται:
;
;   ΣΤΕΚΕΤΑΙ σε δομή      στη θέση του (slot) γύρω της: οι 0, 4, 2, 6 σε μια
;                         σειρά ακριβώς κάτω από το αποτύπωμα, οι 1, 5, 3, 7
;                         από πάνω του (fw_dx)
;   ΠΕΡΠΑΤΑ έξω           στην ευθεία από το μπροστινό σημείο του ενός
;                         κόμβου ως του άλλου (fw_xy), όσο λέει το progress:
;                         ένα βήμα ανά βήμα κίνησης (§6.3)
;   οτιδήποτε άλλο        τίποτα — θόλος (ο δακτύλιος), σωλήνας, νεκρός
;
; ΜΙΑ ΛΙΣΤΑ ΜΕ Ο,ΤΙ ΖΩΓΡΑΦΙΣΤΗΚΕ, ΟΧΙ Ο,ΤΙ ΙΣΧΥΕΙ. Η λίστα (τράπεζα 6, ως 64)
; κρατά για κάθε φιγούρα έξω το κελί όπου ΕΙΝΑΙ στην οθόνη. Το πέρασμα
; αντικειμένων τη ζωγραφίζει τελευταία, πάνω από όλα, και το σβήσιμο ξέρει
; πού να σβήσει χωρίς να ξαναϋπολογίσει τίποτα. Μια αλλαγή που δεν
; σημειώθηκε (ένας γείτονας που άλλαξε θέση στη λίστα γειτνίασης κάτω από
; κάποιον που περπατά, lk_cut) αφήνει τη φιγούρα ένα βήμα πίσω — όχι ίχνος.
;
; Η ΠΡΟΣΟΜΟΙΩΣΗ ΣΗΜΕΙΩΝΕΙ, Ο RENDERER ΥΠΟΛΟΓΙΖΕΙ. Οπου αλλάζει κάτι που φαίνεται
; έξω, η κίνηση καλεί το fg_mark (src/entity.asm): ένα byte ανά πράκτορα στο
; πάνω μισό της σελίδας node_occ, και μία εγγραφή DK_AGENT στη λίστα αλλαγών
; αν το byte ήταν 0. Ενας πράκτορας είναι το πολύ μία φορά στη λίστα αλλαγών,
; όσο γρήγορα κι αν κινείται. Το dh_agent εδώ σβήνει το σημάδι, βρίσκει πού
; φαίνεται τώρα (fg_want), και αν δεν είναι εκεί που ζωγραφίστηκε: ξαναστρώνει
; το παλιό κελί (dhv_rect: έδαφος + ό,τι πατά εκεί, ΚΑΙ οι άλλες φιγούρες) και
; ζωγραφίζει τις φιγούρες του νέου (fg_paint).
;
; ΚΕΛΙ = ΜΙΣΟ TILE. Μια φιγούρα είναι 2x8, όσο ακριβώς ένα μισό tile (§3.1):
; η θέση της είναι ένα ζεύγος προσημασμένων bytes, και το κελί της δεν
; ακουμπά ποτέ δεύτερο tile εδάφους.

FG_CAP      equ 64                      ; φιγούρες έξω που ζωγραφίζονται
FG_UY       equ 64                      ; οι στήλες της λίστας, στο L
FG_FIG      equ 128
FG_AGENT    equ 192
; Οι χρεώσεις, ΜΕΤΡΗΜΕΝΕΣ (test_figure, ΚΟΣΤΟΣ): πέρα από το DK_AGENT (1.300,
; ο υπολογισμός και το cpir σε γεμάτη λίστα), το παλιό κελί σε έδαφος ή δίπλα
; σε κτίσμα (με κτίσμα από κάτω: DHS_VAC_US), το νέο, και ό,τι κοστίζει το
; fg_draw όπου κι αν κληθεί: η σάρωση και κάθε φιγούρα.
FG_ERASE_US equ 2200                    ; μετρημένο ως 1.946
FG_ERASE_NEAR equ 2600                  ; ως 2.320
FG_PAINT_US equ 800                     ; ως 284· με το σβήσιμο μαζί ως 2.812 / 3.220
FG_SCAN_US  equ 24                      ; ανά εγγραφή που κοιτά το fg_draw
FG_ONE_US   equ 800                     ; ανά φιγούρα που ζωγραφίζει: 785

; ---------------------------------------------------------------------------
; dh_agent — DK_AGENT, a = πράκτορας: η φιγούρα του έξω, όπως είναι τώρα.
; ---------------------------------------------------------------------------
dh_agent:
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        ld      a,(dt_a)
        ld      (fg_na),a
        ld      l,a
        ld      h,OCCPG
        set     7,l
        ld      (hl),0                  ; το σημάδι: η επόμενη αλλαγή ξανασπρώχνει
        call    fg_want
        ld      (fg_ny),de              ; fg_ny, fg_nx
        ld      (fg_nf),a
        ; --- πού ζωγραφίστηκε; cpir στη στήλη των πρακτόρων ---
        ld      hl,fg_n
        ld      a,(hl)
        or      a
        jr      z,dha_none
        ld      c,a
        ld      b,0
        ld      a,(fg_na)
        ld      hl,G_fig_list + FG_AGENT
        cpir
        jr      nz,dha_none
        dec     l
        ld      a,l
        and     FG_CAP - 1
        ld      l,a                     ; HL -> ux της εγγραφής
        ; --- ίδιο κελί, ίδια φιγούρα: τίποτα ---
        ld      de,fg_nx
        ld      bc,3 * 256 + FG_UY      ; τρεις στήλες
dha_cmp:
        ld      a,(de)
        cp      (hl)
        jr      nz,dha_diff
        dec     de                      ; fg_nx, fg_ny, fg_nf: ανάποδα στη μνήμη
        ld      a,l
        add     a,c
        ld      l,a
        djnz    dha_cmp
        jp      dt_end
dha_diff:
        ld      a,l
        and     FG_CAP - 1
        ld      l,a
        ld      a,(hl)
        ld      (fg_ox),a
        set     6,l
        ld      a,(hl)
        ld      (fg_oy),a
        res     6,l
        ld      a,(fg_nf)
        or      a
        jr      nz,dha_put
        ; Φεύγει από τη λίστα: η τελευταία εγγραφή στη θέση της.
        ld      a,(fg_n)
        dec     a
        ld      (fg_n),a
        ld      e,a
        ld      d,h
        ld      b,4
dha_mv:
        ld      a,(de)
        ld      (hl),a
        ld      a,e
        add     a,FG_UY
        ld      e,a
        ld      a,l
        add     a,FG_UY
        ld      l,a
        djnz    dha_mv
        jr      dha_erase
dha_put:
        call    fg_put
dha_erase:
        call    fg_erase
        ld      a,(fg_nf)
        or      a
        jr      nz,dha_paint
        jp      dt_end
dha_none:
        ld      a,(fg_nf)
        or      a
        jp      z,dt_end                ; ούτε ήταν ούτε είναι
        ld      hl,fg_n
        ld      a,(hl)
        cp      FG_CAP
        jp      nc,dt_end               ; γεμάτη: δεν ζωγραφίζεται (§15)
        inc     (hl)
        ld      l,a
        ld      h,G_fig_list >> 8
        call    fg_put
dha_paint:
        call    fg_paint
        jp      dt_end

; fg_put — HL -> ux μιας εγγραφής: γράφει fg_nx, fg_ny, fg_nf, fg_na.
fg_put:
        ld      de,fg_nx
        ld      b,4
fgp_lp:
        ld      a,(de)
        ld      (hl),a
        dec     de
        ld      a,l
        add     a,FG_UY
        ld      l,a
        djnz    fgp_lp
        ret

; fg_erase — το κελί (fg_ox, fg_oy) από την αρχή: έδαφος και ό,τι το πατά.
; fg_paint — οι φιγούρες του κελιού (fg_nx, fg_ny), πάνω σε ό,τι είναι εκεί.
; Ζωγραφίζονται ΟΛΕΣ όσες το πατούν, με τη σειρά της λίστας, όπως στην πλήρη
; σχεδίαση: αν μπήκε σε κελί όπου στεκόταν άλλος, εκείνος μένει από πάνω αν
; είναι μετά στη λίστα.
;
; ΤΟ ΣΒΗΣΙΜΟ ΡΩΤΑ ΤΗΝ ΚΑΤΟΧΗ, όπως το dh_tile. Αντικείμενα ζωγραφίζονται μόνο σε
; tiles που κατέχει κάτι ή δίπλα τους (ο διαγώνιος διάδρομος αγγίζει δύο που δεν
; κατέχει): αν τα 3x3 γύρω από το tile του κελιού είναι ελεύθερα, το κελί είναι
; έδαφος και φιγούρες (FG_ERASE_US). Αλλιώς ολόκληρο το πέρασμα, κομμένο στο
; κελί: φθηνό όταν το ίδιο το tile είναι ελεύθερο (FG_ERASE_NEAR), όσο ένα
; άδειασμα θέσης όταν όχι (DHS_VAC_US) — από κάτω μπορεί να είναι θόλος, και ο
; θόλος κομμένος σε 2x8 είναι ~25 blit.
fg_erase:
        ld      hl,(fg_oy)              ; L = uy, H = ux
        call    fg_in                   ; και ob_x, ob_y
        ret     nc                      ; εκτός κάδρου: τίποτα να σβηστεί
        ld      hl,(fg_oy)
        ld      a,h
        call    fge_t
        ld      e,a
        ld      a,l
        call    fge_t
        ld      d,a
        ld      (vr_tx),de              ; vr_tx, vr_ty: το tile βορειοδυτικά
        ld      hl,3 * 256 + 3
        ld      (vr_w),hl               ; vr_w, vr_h
        call    vr_clip                 ; td_*: τα 3x3 όσο φαίνονται
        ld      a,W_OCC_STRUCT          ; τα μονοπάτια (κατοχή 2) είναι έδαφος
        call    nz,dh_occ_a
        jr      nz,fge_obj
        ld      a,1
        ld      (dhv_fo),a              ; μόνο οι φιγούρες
        ld      de,FG_ERASE_US
        jr      fge_go
fge_obj:
        ; ΤΙ ΚΟΣΤΙΖΕΙ ΤΟ ΠΕΡΑΣΜΑ: σχεδόν τίποτα, αν το ίδιο το tile του κελιού
        ; είναι ελεύθερο — ένας γείτονας κατέχει, αλλά το ευρετήριο κόβει το
        ; αντικείμενό του στο tile του κελιού. Αν το κατέχει, μπορεί να είναι
        ; θόλος: όσο ένα άδειασμα θέσης.
        ld      bc,(vr_tx)
        inc     c
        inc     b
        ld      a,b
        ld      b,c
        ld      c,a                     ; B = tx, C = ty
        ld      a,W_OCC_STRUCT
        call    tl_occ                  ; src/tiles.asm
        ld      de,FG_ERASE_NEAR
        jr      z,fge_go
        ld      de,DHS_VAC_US
fge_go:
        ld      hl,SLOT_H * 256 + SLOT_W
        jp      dhv_rect_us

fg_paint:
        ld      a,(fg_q)
        or      a
        ret     nz                      ; fg_build: η πλήρης σχεδίαση έρχεται
        ld      hl,(fg_ny)              ; L = uy, H = ux
        call    fg_in                   ; και ob_x, ob_y
        ret     nc
        ld      hl,SLOT_H * 256 + SLOT_W
        call    dhv_clip
        ret     z
        ld      de,FG_PAINT_US
        call    dhv_charge
        call    dt_ghost_rect
        call    ob_b6
        call    fg_draw
        jp      ob_clip_full

; ---------------------------------------------------------------------------
; fg_draw — οι φιγούρες της λίστας που τέμνουν το clip. Από το ob_draw_all,
; τελευταίες, και από το fg_paint. Η λίστα και οι φιγούρες είναι στην τράπεζα
; 6, που είναι ήδη στο παράθυρο: τίποτα να σελιδοποιηθεί.
;
; Το παράθυρο σε μισά tiles +128, ώστε η σύγκριση να είναι ΜΙΑ αφαίρεση και
; ΕΝΑ cp ανά άξονα: ux - wx0 < πλάτος. Το κάθετο μπαίνει μέσα στις εντολές
; (fgd_y0, fgd_h): ο βρόχος δεν έχει καταχωρητές γι' αυτό.
; ---------------------------------------------------------------------------
fg_draw:
        ld      a,(fg_n)
        or      a
        ret     z
        ; ΧΡΕΩΝΕΙ ΤΟ ΙΔΙΟ ΟΣΑ ΚΑΝΕΙ (§8.5): FG_SCAN_US ανά εγγραφή που κοιτά,
        ; FG_ONE_US ανά φιγούρα που ζωγραφίζει (fgd_one) — όποιος κι αν το
        ; κάλεσε: το dh_agent, το dh_tile, ένα άδειασμα θέσης. Με γεμάτη λίστα
        ; η σάρωση είναι 1,5 ms, και ένα σταθερό κόστος δεν θα το ήξερε.
        ld      l,a
        ld      h,0
        add     hl,hl
        add     hl,hl
        add     hl,hl
        ld      d,h
        ld      e,l
        add     hl,hl
        add     hl,de                   ; 24 x εγγραφές
        ex      de,hl
        call    dhv_charge
        ld      hl,clip_x0
        ld      a,(cam_tx)
        call    fgd_base                ; C = 2 * cam + 128
        ld      a,(hl)
        srl     a
        add     a,c
        ld      d,a                     ; wx0 = x0 / 2
        inc     hl
        ld      a,(hl)
        inc     a
        srl     a
        add     a,c
        sub     d
        ld      e,a                     ; πλάτος ως ⌈x1 / 2⌉
        inc     hl
        ld      a,(cam_ty)
        call    fgd_base
        ld      a,(hl)
        rrca
        rrca
        rrca
        and     31
        add     a,c
        ld      (fgd_y0 + 1),a          ; wy0 = y0 / 8
        ld      b,a
        inc     hl
        ld      a,(hl)
        add     a,7
        rrca
        rrca
        rrca
        and     31
        add     a,c
        sub     b
        ld      (fgd_h + 1),a           ; ύψος ως ⌈y1 / 8⌉
        ld      a,(fg_n)
        ld      b,a
        ld      hl,G_fig_list
fgd_lp:
        ld      a,(hl)                  ; ux
        sub     d
        cp      e
        jr      nc,fgd_nx
        set     6,l
        ld      a,(hl)                  ; uy
        res     6,l
fgd_y0: sub     0
fgd_h:  cp      0
        call    c,fgd_one
fgd_nx:
        inc     l
        djnz    fgd_lp
        ret
fgd_base:
        add     a,a
        add     a,128
        ld      c,a
        ret

; fgd_one — η φιγούρα της εγγραφής L. Κρατά BC, DE, HL.
fgd_one:
        push    bc
        push    de
        push    hl
        ld      d,(hl)                  ; ux
        set     6,l
        ld      e,(hl)                  ; uy
        set     7,l
        res     6,l
        ld      a,(hl)                  ; φιγούρα 1-8
        ex      de,hl
        push    af
        call    fg_in                   ; μέσα στο παράθυρο = μέσα στο κάδρο
        pop     af
        dec     a
        rrca
        rrca
        rrca                            ; * 32: μία σελίδα, 8 x 32
        ld      l,a
        ld      h,G_fig_gfx >> 8
        ld      b,0                     ; πάνω σε ό,τι είναι ήδη εκεί
        call    ob_fig
        ld      de,FG_ONE_US
        call    dhv_charge
        pop     hl
        pop     de
        pop     bc
        ret

; ---------------------------------------------------------------------------
; ob_fig — ΜΙΑ φιγούρα 2x8 στο ob_x, ob_y, κομμένη στο clip: (από κάτω AND
; μάσκα) OR data. HL = η φιγούρα (μάσκα, data, μάσκα, data ανά γραμμή). BC = η
; κενή θέση του δακτυλίου (2 bytes τη γραμμή) που μπαίνει από κάτω, αδιαφανής:
; αυτό είναι ακριβώς η ψημένη θέση του βήματος 88 (tools/pack.py, check_ring).
; Ή B = 0: από κάτω είναι ό,τι έχει ήδη η οθόνη — η φιγούρα έξω.
;
; ΤΟ ob_put ΕΙΝΑΙ ΓΕΝΙΚΟ ΚΑΙ ΤΟ ΠΛΗΡΩΝΕΙ. Κόψιμο σε κάθε πλευρά, καθρέφτισμα,
; δείκτες γραμμής στη μνήμη: μετρημένα ~110 us ανά γραμμή για τα δύο bytes μιας
; φιγούρας, 1,2 ms η φιγούρα — και ο δακτύλιος, με την κενή θέση και τη φιγούρα
; χωριστά, θα ήθελε δύο. Εδώ ένα πέρασμα, ~50 us η γραμμή. Οταν το κάδρο κόβει
; ένα από τα δύο bytes (στην άκρη του), το ob_put — δύο φορές για τον δακτύλιο.
; ---------------------------------------------------------------------------
ob_fig:
        ld      (obf_f),hl
        ld      (obf_e),bc
        ld      hl,(ob_y)
        ld      a,SLOT_H
        ld      de,(clip_y0)
        call    ob_clip
        ret     z
        ld      hl,(cl_skip)            ; L = γραμμές κομμένες από πάνω, H = πόσες
        ld      (obf_k),hl              ; obf_k, obf_n
        ld      a,(cl_start)
        ld      (obf_y),a
        ld      hl,(ob_x)
        ld      a,SLOT_W
        ld      de,(clip_x0)
        call    ob_clip
        ret     z
        cp      SLOT_W
        jr      nz,obf_slow
        ld      a,(cl_start)
        ld      c,a
        ld      a,(obf_y)
        call    scr_addr                ; DE = οθόνη· χαλάει το HL
        ld      a,(obf_k)
        add     a,a
        ld      c,a
        ld      b,0                     ; BC = 2 * κομμένες
        ld      hl,(obf_e)
        add     hl,bc
        push    hl
        ld      hl,(obf_f)
        add     hl,bc
        add     hl,bc
        pop     bc
        ld      a,(obf_e + 1)
        or      a
        ld      a,(obf_n)
        jr      nz,obf_ring
        ld      b,a
        ; ΕΞΩ ΤΟ ΚΕΛΙ ΑΡΧΙΖΕΙ ΣΕ ΣΕΙΡΑ ΧΑΡΑΚΤΗΡΩΝ (y = 8 x σειρά, fg_in): οι
        ; γραμμές του είναι +#800 η καθεμία, χωρίς scr_nextline και χωρίς
        ; push/pop — 34 us η γραμμή αντί για 52. Το δεύτερο byte σε άλλη
        ; σελίδα (e = #FF, μία θέση στις 256): το γενικό ob_put.
        ld      a,e
        inc     a
        jr      z,obf_slow
obfs_lp:
        ld      a,(de)
        and     (hl)
        inc     hl
        or      (hl)
        inc     hl
        ld      (de),a
        inc     e
        ld      a,(de)
        and     (hl)
        inc     hl
        or      (hl)
        inc     hl
        ld      (de),a
        dec     e
        ld      a,d
        add     a,8
        ld      d,a
        djnz    obfs_lp
        ret
obf_ring:
        ld      ixl,a
obfr_lp:
        push    de
        ld      a,(bc)
        inc     bc
        and     (hl)
        inc     hl
        or      (hl)
        inc     hl
        ld      (de),a
        inc     e
        call    z,obf_wr
        ld      a,(bc)
        inc     bc
        and     (hl)
        inc     hl
        or      (hl)
        inc     hl
        ld      (de),a
        pop     de
        call    scr_nextline
        dec     ixl
        jr      nz,obfr_lp
        ret
; obf_wr — το δεύτερο byte πέρασε σελίδα: η επόμενη, ή η αρχή του δαχτυλιδιού
; των 2 KB αν ήταν η τελευταία του (§8.2).
obf_wr:
        inc     d
        ld      a,d
        and     7
        ret     nz
        ld      a,d
        sub     8
        ld      d,a
        ret
; obf_slow — μισή φιγούρα, στην άκρη του κάδρου: το γενικό ob_put.
obf_slow:
        ld      hl,(obf_e)
        ld      a,h
        or      a
        jr      z,obfs_f
        ld      (ob_src),hl
        ld      hl,SLOT_H * 256 + SLOT_W
        ld      a,4                     ; αδιαφανές
        call    ob_put
obfs_f:
        ld      hl,(obf_f)
        ld      (ob_src),hl
        ld      hl,SLOT_H * 256 + SLOT_W
        xor     a                       ; με μάσκα
        jp      ob_put

; ---------------------------------------------------------------------------
; fg_build — η λίστα από την αρχή, για την πλήρη σχεδίαση (view_draw): ο
; καθένας όπως θα τον έβαζε το dh_agent, χωρίς να ζωγραφίσει — το ob_draw_all
; που ακολουθεί ζωγραφίζει όλη τη λίστα. Τα σημάδια σβήνουν όλα: ό,τι
; σπρώχτηκε πριν το πετά το dirty_reset της πλήρους σχεδίασης, ή το βρίσκει
; ήδη σωστό. Μετά το ob_touch, που έκανε το view_draw ως εδώ.
; ---------------------------------------------------------------------------
fg_build:
        ld      hl,fg_q
        ld      (hl),1
        xor     a
        ld      (fg_n),a
        ld      b,128                   ; N_AGENT (src/entity.asm)
fgb_lp:
        ld      a,b
        dec     a
        ld      (dt_a),a
        push    bc
        call    dh_agent
        pop     bc
        djnz    fgb_lp
        xor     a
        ld      (fg_q),a
        jp      ob_touch

; ---------------------------------------------------------------------------
; fg_want — L = πράκτορας (το bit 7 δεν μετρά), τράπεζα 6. Πού φαίνεται έξω:
; A = φιγούρα 1-8, D = ux, E = uy (μισά tiles + 128)· ή A = 0, πουθενά.
; ---------------------------------------------------------------------------
fg_want:
        res     7,l
        ld      h,AG_PG
        bit     0,(hl)                  ; F_ALIVE
        jr      z,fw_none
        set     7,l
        ld      a,(hl)                  ; ρόλος
        and     7
        push    hl
        ld      hl,role_fig
        call    ob_addu
        ld      a,(hl)
        pop     hl
        ld      (fw_f),a
        ld      h,AG_PG + 2
        ld      a,(hl)                  ; edge
        res     7,l
        inc     a
        jr      nz,fw_walk
        ; --- ΣΤΕΚΕΤΑΙ: σε δομή, στη θέση του γύρω της ---
        dec     h                       ; AG_PG + 1
        ld      a,(hl)                  ; κόμβος
        set     7,l
        ld      c,(hl)                  ; θέση
        bit     3,c
        jr      nz,fw_none              ; NO_SLOT: δεν χώρεσε, όπως στον θόλο
        cp      MAX_DOME
        jr      c,fw_none               ; θόλος: τον ζωγραφίζει ο δακτύλιος
        call    fw_xy                   ; D = cx, E = cy + μισό, B = μισό
        bit     0,c
        jr      z,fw_south
        ld      a,e                     ; βόρεια: cy - μισό - 1
        sub     b
        sub     b
        dec     a
        ld      e,a
fw_south:
        ld      a,c
        rra
        and     3
        ld      hl,fw_dx
        call    ob_addu
        ld      a,(hl)
        add     a,d
        ld      d,a
fw_out:
        ld      a,d
        xor     128
        ld      d,a
        ld      a,e
        xor     128
        ld      e,a
        ld      a,(fw_f)
        ret
fw_none:
        xor     a
        ret

        ; --- ΠΕΡΠΑΤΑ: A = edge + 1, L = πράκτορας ---
fw_walk:
        ld      c,a
        ld      h,AG_PG
        bit     1,(hl)                  ; F_INDOORS: στον σωλήνα
        jr      nz,fw_none
        ld      h,AG_PG + 3
        ld      a,(hl)
        ld      (fw_p),a                ; progress
        ld      h,AG_PG + 1
        ld      a,(hl)                  ; από πού
        push    af
        ; ο στόχος: node_adj[από*8 + edge], όπως στο em_arrive
        add     a,(G_node_adj >> 3) & 255
        ld      l,a
        ld      h,G_node_adj >> 11
        add     hl,hl
        add     hl,hl
        add     hl,hl
        dec     c
        ld      a,l
        add     a,c
        ld      l,a
        ld      a,(hl)
        call    fw_xy
        ld      (fw_b),de               ; by, bx
        pop     af
        call    fw_xy                   ; D = ax, E = ay
        ld      a,(fw_p)
        ld      c,a
        ld      a,(fw_b)
        call    fw_axis
        push    af
        ld      e,d
        ld      a,(fw_b + 1)
        call    fw_axis
        dec     a                       ; η στήλη της θέσης 0 (fw_dx)
        ld      d,a
        pop     af
        ld      e,a
        jr      fw_out

; fw_axis — A = b, E = a (προσημασμένα), C = p -> A = a + (b - a) * p / 256.
; Η διαφορά είναι ως ±255, εννέα bits: το πρόσημο στο CY, και ο
; πολλαπλασιασμός ανυπόγραφος. Κρατά C, D, E.
fw_axis:
        xor     128
        ld      h,a
        ld      a,e
        xor     128
        ld      l,a
        ld      a,h
        sub     l
        push    af
        jr      nc,fwa_pos
        neg
fwa_pos:
        ld      h,a
        ld      l,c
        xor     a
        ld      b,8
fwa_lp:
        srl     l
        jr      nc,fwa_no
        add     a,h
fwa_no:
        rra
        djnz    fwa_lp
        ld      h,a
        pop     af
        ld      a,h
        jr      nc,fwa_add
        neg
fwa_add:
        add     a,e
        ret

; fw_xy — A = κόμβος -> το ΜΠΡΟΣΤΙΝΟ του σημείο: D = cx, E = cy + μισό ύψος
; του αποτυπώματος, B = το μισό ύψος (μισά tiles). Εκεί στέκεται η θέση 0, και
; από εκεί ως εκεί περπατά όποιος είναι έξω: από κέντρο σε κέντρο, η φιγούρα
; ξεκινούσε πάνω στη σκεπή του σκάφους. Τράπεζα 6. Κρατά C.
fw_xy:
        sub     MAX_DOME
        jr      nc,fwx_st
        add     a,MAX_DOME
        call    ob_domeadr
        inc     hl
        inc     hl
        ld      a,(hl)                  ; D_SIZE: πλευρά 4 + 2 x μέγεθος tiles
        add     a,a
        add     a,4
        dec     hl
        dec     hl
        jr      fwx_go
fwx_st:
        ld      l,a
        ld      h,0
        add     hl,hl
        add     hl,hl
        add     hl,hl
        ld      de,G_struct_tbl
        add     hl,de
        push    hl
        inc     hl
        inc     hl
        ld      a,(hl)                  ; ST_KIND
        add     a,a
        add     a,a
        inc     hl
        add     a,(hl)                  ; + ST_SIZE
        add     a,a
        inc     a                       ; struct_dims[είδος*4 + μέγεθος].h
        ld      hl,G_struct_dims
        call    ob_addu
        ld      a,(hl)
        rrca
        rrca
        rrca
        rrca
        and     #0F                     ; γραμμές / 16 = μισό ύψος σε μισά tiles
        pop     hl
fwx_go:
        ld      b,a
        ld      d,(hl)                  ; cx
        inc     hl
        ld      a,(hl)                  ; cy
        add     a,b
        ld      e,a
        ret

; ---------------------------------------------------------------------------
; dhs_vacate — μια θέση του δακτυλίου άδειασε (dh_slot· ob_x, ob_y = η θέση).
;
; Οταν ΕΡΧΕΤΑΙ άποικος, το αδιαφανές 2x8 του ob_fig_one είναι ό,τι θα έβγαζε
; το πλήρες πέρασμα. Οταν ΦΕΥΓΕΙ, όχι: η «κενή» παραλλαγή είναι ο δακτύλιος
; πάνω σε ΜΑΥΡΟ, και όπου ο δακτύλιος είναι διαφανής το πλήρες πέρασμα δείχνει
; το ΕΔΑΦΟΣ — η αδιαφανής παραλλαγή εκεί βάφει pen 0. Ως το βήμα 42 αυτό άφηνε
; 1-8 bytes λάθος σε 12 από τις 20 θέσεις της αποικίας δοκιμής, και το §15 το
; χρέωνε στο κόψιμο του περάσματος αντικειμένων: ο θόλος ξανασχεδιασμένος
; κομμένος στο 2x8 έβγαζε τα ίδια pixel — γιατί ούτε κι εκείνος ξανάστρωνε
; έδαφος.
;
; Εδώ γίνεται ό,τι κάνει το πλήρες πέρασμα, ΜΟΝΟ στο 2x8: το έδαφος από κάτω
; (το tile, ή τα δύο ως τέσσερα που πιάνει η θέση, μέσα από το ob_blit που
; κόβει), και από πάνω όλα τα αντικείμενα κομμένα στο ίδιο. Μια πρώτη μορφή
; ξανάστρωνε ΟΛΟΚΛΗΡΑ τα tiles (view_rect) και έπρεπε μετά να ξαναζωγραφίσει
; ό,τι πατούσε πάνω τους — εικονίδιο, μηχανές: ως 32,6 ms για 16 bytes.
;
; dhv_rect — το ίδιο για ΟΠΟΙΟΔΗΠΟΤΕ ορθογώνιο στο ob_x, ob_y: L = bytes,
; H = γραμμές. Και για τη μηχανή που βγήκε (dh_mach, βήμα 45): 6x22 αντί 2x8.
; ---------------------------------------------------------------------------
dhs_vacate:
        ld      hl,SLOT_H*256 + SLOT_W
dhv_rect:
        ; --- ΤΟ ΚΟΣΤΟΣ ΤΟ ΞΕΡΕΙ ΜΟΝΟ ΑΥΤΟΣ. Ο πίνακας λέει 1.500 για το
        ; DK_SLOT, όσο κοστίζει ένας άποικος που ΕΡΧΕΤΑΙ. Ενα άδειασμα που
        ; φαίνεται κοστίζει ως 18 ms ακόμη: ο θόλος, κομμένος στο 2x8, περνά
        ; ακόμη από ~25 blit. Το λέει στον dirty_tick, για να μην ακολουθήσει
        ; τίποτε άλλο στο ίδιο καρέ. Το 16 bit ξεχειλίζει ως «πάνω» (dt_lp).
        ; Η φιγούρα έξω (βήμα 89) λέει το δικό της: DE = πόσο, dhv_rect_us.
        ld      de,DHS_VAC_US
dhv_rect_us:
        push    de
        call    dhv_clip
        pop     de
        ret     z
        call    dhv_charge
        ; Το φάντασμα, αν πέφτει εδώ (βήμα 89): ο θόλος του dh_slot και του
        ; dh_mach το σήκωσε ήδη στο dt_prep, το κελί μιας φιγούρας έξω όχι.
        call    dt_ghost_rect
        ; --- το έδαφος: κάθε tile που αγγίζει το clip, κομμένο σε αυτό ---
        ld      bc,GA_PORT + PAGE_B4
        out     (c),c
        ld      a,(clip_y0)
        and     #F0                     ; η γραμμή του πρώτου tile
        ld      d,a
dhv_row:
        ld      a,(clip_x0)
        and     #FC
        ld      e,a
dhv_col:
        push    de                      ; D = γραμμή, E = byte του tile
        ld      a,e
        rrca
        rrca                            ; στήλη tile (το x < 80)
        ld      hl,cam_tx
        add     a,(hl)
        ld      b,a
        ld      a,d
        rrca
        rrca
        rrca
        rrca                            ; σειρά tile (το y < 160)
        ld      hl,cam_ty
        add     a,(hl)
        ld      c,a
        call    tile_addr
        ld      (t_wptr),hl
        call    tile_src
        ld      (ob_src),hl
        pop     de
        push    de
        ld      h,0
        ld      l,e
        ld      (ob_x),hl
        ld      l,d
        ld      (ob_y),hl
        ld      hl,TILE_H*256 + TILE_W
        ld      a,4                     ; αδιαφανές
        call    ob_put
        pop     de
        ld      a,e
        add     a,TILE_W
        ld      e,a
        ld      hl,clip_x1
        cp      (hl)
        jr      c,dhv_col
        ld      a,d
        add     a,TILE_H
        ld      d,a
        ld      hl,clip_y1
        cp      (hl)
        jr      c,dhv_row
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        ; --- και από πάνω ό,τι πατά εκεί: όλα, ή μόνο οι φιγούρες όταν το
        ; λέει το fg_erase (dhv_fo, μία φορά) ---
        ld      hl,dhv_fo
        ld      a,(hl)
        ld      (hl),0
        or      a
        jr      nz,dhv_figs
        call    ob_draw_all
        jp      ob_clip_full
dhv_figs:
        call    fg_draw1
        jp      ob_clip_full

; fg_objs — μετά από έδαφος (dh_tile): NZ, κάτι κατέχει τα tiles -> όλα τα
; αντικείμενα· Z -> μόνο οι φιγούρες έξω. Ως το βήμα 89 το Z δεν ζωγράφιζε
; τίποτα, και ένας μετεωρίτης δίπλα σε κάποιον που στεκόταν στο έδαφος τον
; έσβηνε από την οθόνη.
fg_objs:
        jp      nz,ob_draw_all
; fg_draw1 — το fg_draw από όπου κι αν καλείται: η 6 μέσα, η 1 μετά.
fg_draw1:
        call    ob_b6
        call    fg_draw
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        ret

; dhv_clip — το clip: το ορθογώνιο L x H στο ob_x, ob_y, κομμένο στο κάδρο.
; Z αν δεν φαίνεται, και τότε το clip είναι ολόκληρο το κάδρο.
dhv_clip:
        ld      (dhv_w),hl              ; dhv_w, dhv_h διπλανά
        ld      a,l
        ld      hl,(ob_x)
        ld      de,SCR_W * 256          ; lo = 0, hi = SCR_W
        call    dhv_cut
        ret     z
        ld      (clip_x0),hl            ; clip_x0, clip_x1
        ld      hl,(ob_y)
        ld      a,(dhv_h)
        ld      de,PLAY_LINES * 256
        call    dhv_cut
        ; ΤΟ clip_x ΕΧΕΙ ΗΔΗ ΣΤΕΝΕΨΕΙ. Με `ret z` εδώ, μια θέση που φαίνεται
        ; οριζόντια αλλά πέφτει κάτω ή πάνω από το κάδρο άφηνε το clip μια
        ; στήλη δύο bytes, και ΚΑΘΕ επόμενος χειριστής της λίστας ζωγράφιζε
        ; μέσα σε αυτήν — δηλαδή τίποτα. Από το βήμα 42 ως το 45 δεν φάνηκε,
        ; γιατί κανένας θόλος δεν τελείωνε στο κάδρο μετά από τέτοιο άδειασμα·
        ; το test_link του βήματος 45, που περιμένει τον εξοπλισμό, βρήκε έναν
        ; L χωρίς εικονίδιο και χωρίς καμία από τις οκτώ μηχανές του.
        jp      z,ob_clip_full
        ld      (clip_y0),hl            ; clip_y0, clip_y1
        ret                             ; NZ, από το dhv_cut

; dhv_charge — DE us ακόμη στο dt_spent, με ταβάνι το #FFFF.
dhv_charge:
        ld      hl,(dt_spent)
        add     hl,de
        jr      nc,dhv_spent
        ld      hl,#FFFF
dhv_spent:
        ld      (dt_spent),hl
        ret

; dhv_cut — A = μήκος, HL = θέση, DE = όρια: το ob_clip. Out: Z αν εκτός
; κάδρου, αλλιώς L = αρχή και H = τέλος του κομμένου.
dhv_cut:
        call    ob_clip
        ret     z
        ld      b,a                     ; cl_n
        ld      a,(cl_start)
        ld      l,a
        add     a,b                     ; NZ: το τέλος δεν είναι ποτέ 0
        ld      h,a
        ret

; Η σειρά του slot γύρω από τη δομή: ζευγάρια (νότια, βόρεια) ανά στήλη. Το
; corr_fill γεμίζει 0, 4, 2, 6 πρώτα: -1, 0, -2, +1 — συνεχόμενη σειρά σε
; κάθε πλήθος.
fw_dx:      db -1, -2, 0, 1

fg_n:       db 0                        ; εγγραφές της λίστας
dhv_fo:     db 0                        ; 1 = το dhv_rect ζωγραφίζει μόνο φιγούρες
fg_q:       db 0                        ; 1 = fg_build: χωρίς ζωγραφική
fg_oy:      db 0                        ; fg_oy, fg_ox: το κελί που σβήνει
fg_ox:      db 0
fg_na:      db 0                        ; η νέα εγγραφή, ΑΝΑΠΟΔΑ: το fg_put
fg_nf:      db 0                        ; γράφει από το fg_nx προς τα κάτω
fg_ny:      db 0
fg_nx:      db 0
fw_f:       db 0
fw_p:       db 0
obf_f:      dw 0                        ; η φιγούρα
obf_e:      dw 0                        ; η κενή θέση, ή 0
obf_k:      db 0                        ; obf_k, obf_n διπλανά: ld (obf_k),hl
obf_n:      db 0
obf_y:      db 0
fw_b:       dw 0                        ; by, bx

        assert  fg_ox == fg_oy + 1 && fg_nx == fg_ny + 1
        assert  fg_ny == fg_nf + 1 && fg_nf == fg_na + 1
        assert  (G_fig_list & 255) == 0 && (G_fig_gfx & 255) == 0
        assert  FG_CAP * 4 == 256 && SLOT_W == 2 && SLOT_H == 8
        assert  ((G_node_adj >> 3) & 255) + 128 <= 256
        assert  FG_SCAN_US == 24
        assert  obf_n == obf_k + 1 && (G_slot_empty >> 8) != 0
