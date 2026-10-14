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
;   ΠΕΡΠΑΤΑ έξω           από το μπροστινό σημείο του ενός κόμβου ως του
;                         άλλου (fw_xy), όσο λέει το progress, στη στήλη της
;                         θέσης 0 — και από το βήμα 118 στο Γ του μονοπατιού,
;                         στη στήλη του κέντρου πάνω στα σκέλη του (fw_leg,
;                         src/walk6.asm): ένα βήμα ανά βήμα κίνησης (§6.3)
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
; Οι χρεώσεις, ΜΕΤΡΗΜΕΝΕΣ (test_figure, ΚΟΣΤΟΣ): πέρα από το DK_AGENT (1.200,
; ο υπολογισμός και το cpir σε γεμάτη λίστα), το παλιό κελί σε έδαφος ή δίπλα
; σε κτίσμα (με κτίσμα από κάτω: DHS_VAC_US), το νέο, και ό,τι κοστίζει το
; fg_cell ή το fg_draw: η σάρωση και κάθε φιγούρα. Μόνο του, το σβήσιμο σε
; έδαφος είναι 840-1.000 us (το autotile του βουνού και του νερού είναι το
; πάνω άκρο), δίπλα σε κτίσμα 1.500-1.640, το ζωγράφισμα ~400 χωρίς φιγούρες.
FG_ERASE_US equ 1100                    ; βήμα 106, fge_free (1.200 ως το 105)
FG_ERASE_NEAR equ 1600                  ; με το fg_draw του ob_draw_all
FG_PAINT_US equ 500                     ; βήμα 106, fg_cell (800 ως το 105)
FG_SCAN_US  equ 24                      ; ανά εγγραφή που κοιτά το fg_draw
FG_ONE_US   equ 800                     ; ανά φιγούρα που ζωγραφίζει: ~770
FG_VEIN_US  equ 300                     ; η φλέβα στο fg_tile (βήμα 106): ~280
FGC_SCAN_US equ 8                       ; το fg_cell (βήμα 106): ανά εγγραφή, 5,25
FGC_XM_US   equ 24                      ; ανά εγγραφή με το ίδιο ux: ~25 μαζί
FGC_ONE_US  equ 300                     ; ανά φιγούρα: ~265

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
        ; Η ΣΕΙΡΑ ΑΛΛΑΞΕ (βήμα 134): η τελευταία πήγε πιο μπροστά, και όσες ήταν
        ; ανάμεσα είναι τώρα μετά από αυτήν — από πάνω της στην πλήρη σχεδίαση.
        ; Αν μία πατά το ίδιο κελί, το fg_ord (src/walk6.asm, τράπεζα 6) το
        ; δίνει στο fg_paint μετά το σβήσιμο· αλλιώς η οθόνη κρατούσε την παλιά
        ; από πάνω (test_reach, θόλος S πάνω στο μονοπάτι).
        call    fg_ord
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
        call    fg_in                   ; και ob_x, ob_y· κρατά το HL
        ret     nc                      ; εκτός κάδρου: τίποτα να σβηστεί
        ld      a,h
        call    fge_t
        ld      b,a
        ld      a,l
        call    fge_t
        ld      c,a                     ; B, C: το tile βορειοδυτικά
        push    bc
        call    fg_cclip                ; το clip: το κελί
        ld      bc,GA_PORT + PAGE_B4
        out     (c),c
        pop     bc
        push    bc
        ; ΤΑ 3x3 ΚΑΤΕΥΘΕΙΑΝ ΣΤΟΝ ΚΟΣΜΟ (βήμα 106): μία διεύθυνση, τρία bytes ανά
        ; σειρά, +128 η επόμενη σειρά (tile_addr). Ως το 105 το vr_clip τα
        ; έκοβε στο κάδρο και το dh_occ_a έψαχνε τη διεύθυνση κάθε σειράς:
        ; ~370 us. Ενα tile έξω από το κάδρο μετρά τώρα κι αυτό — το
        ; αντικείμενό του μπορεί να φτάνει ως το κελί — και έξω από τον κόσμο
        ; (στήλη ή σειρά -65 / 64) διαβάζεται ένα άλλο byte: το πολύ ένα
        ; ακριβότερο σβήσιμο, ποτέ λάθος.
        call    tile_addr
        ld      de,128 - 2
        ld      b,3
fge_row:
        ld      a,(hl)
        inc     l
        or      (hl)
        inc     l
        or      (hl)
        and     W_OCC_STRUCT            ; τα μονοπάτια (κατοχή 2) είναι έδαφος
        jr      nz,fge_obj
        add     hl,de
        djnz    fge_row
        pop     bc
        inc     b
        inc     c                       ; B = tx, C = ty: το tile του κελιού
        jr      fge_free
fge_obj:
        pop     bc
        inc     b
        inc     c
        ; ΤΙ ΚΟΣΤΙΖΕΙ ΤΟ ΠΕΡΑΣΜΑ: σχεδόν τίποτα, αν το ίδιο το tile του κελιού
        ; είναι ελεύθερο — ένας γείτονας κατέχει, αλλά το ευρετήριο κόβει το
        ; αντικείμενό του στο tile του κελιού. Αν το κατέχει, μπορεί να είναι
        ; θόλος: όσο ένα άδειασμα θέσης.
        ld      a,W_OCC_STRUCT
        call    tl_occ                  ; src/tiles.asm· γυρίζει την 1
        ld      de,FG_ERASE_NEAR
        jr      z,fge_go
        ld      de,DHS_VAC_US
fge_go:
        ; ΤΟ TILE ΤΟΥ ΚΕΛΙΟΥ ΑΠΟ ΤΟ fg_tile (βήμα 105): το call του ob_put στο
        ; dhv_rect_us γράφεται για όσο σβήνει το κελί, και ξαναγράφεται μετά.
        ; Το άδειασμα θέσης και η μηχανή που βγαίνει δεν πληρώνουν τίποτα.
        ld      hl,fg_tile
        ld      (dhv_put + 1),hl
        call    dhv_rect_c              ; το clip είναι ήδη το κελί
        ld      hl,ob_put
        ld      (dhv_put + 1),hl
        ret

; fge_free — ΕΛΕΥΘΕΡΟ ΕΔΑΦΟΣ (βήμα 106): ό,τι έκανε το dhv_rect_us για ένα
; κελί, χωρίς ό,τι δεν χρειάζεται εδώ — το κελί είναι μέσα σε ένα tile, και
; πάνω του μόνο φιγούρες (fg_cell). B = tx, C = ty, η 4 μέσα, το clip = το
; κελί. Η διεύθυνση οθόνης βρίσκεται μία φορά, για το tile και τις φιγούρες.
fge_free:
        push    bc
        call    dt_ghost_rect           ; δεν σελιδοποιεί
        pop     bc
        call    tile_addr
        ld      (t_wptr),hl
        call    tile_src
        ld      (ob_src),hl
        call    fg_scr                  ; κρατά το C = clip_x0
        call    fgt_de
        call    ob_b6
        ld      hl,(fg_oy)
        ld      de,FG_ERASE_US
        call    fg_cell
        jp      ob_clip_full

fg_paint:
        ld      a,(fg_q)
        or      a
        ret     nz                      ; fg_build: η πλήρης σχεδίαση έρχεται
        ld      hl,(fg_ny)              ; L = uy, H = ux
        call    fg_in                   ; και ob_x, ob_y
        ret     nc
        call    fg_cclip
        call    dt_ghost_rect
        call    ob_b6
        call    fg_scr
        ld      hl,(fg_ny)
        ld      de,FG_PAINT_US
        call    fg_cell
        jp      ob_clip_full

; fg_scr — η διεύθυνση οθόνης του clip, στο DE και στο fgc_de. C = clip_x0.
fg_scr:
        ld      a,(clip_x0)
        ld      c,a
        ld      a,(clip_y0)
        call    scr_addr
        ld      (fgc_de + 1),de
        ret

; fg_cclip — το clip = το κελί στο ob_x, ob_y, που το fg_in βρήκε ΟΛΟ μέσα στο
; κάδρο: χωρίς το ob_clip του dhv_clip, δύο φορές ανά άξονα (~230 us).
fg_cclip:
        ld      a,(ob_x)
        ld      l,a
        add     a,SLOT_W
        ld      h,a
        ld      (clip_x0),hl            ; clip_x0, clip_x1
        ld      a,(ob_y)
        ld      l,a
        add     a,SLOT_H
        ld      h,a
        ld      (clip_y0),hl            ; clip_y0, clip_y1
        ret

; ---------------------------------------------------------------------------
; fg_cell — οι φιγούρες της λίστας ΣΤΟ κελί H = ux, L = uy, που είναι το clip
; και όλο μέσα στο κάδρο (βήμα 106), με τη διεύθυνσή του στο fgc_de (fg_scr).
; Τράπεζα 6.
;
; ΤΟ fg_draw ΓΙΑ ΕΝΑ ΚΕΛΙ. Οι φιγούρες έξω πατούν σε κελιά, άρα όποια τέμνει
; ένα κελί είναι ΣΤΟ κελί: ίδιο ux, ίδιο uy, όλη μέσα του. Δεν χρειάζεται
; ούτε το παράθυρο του fg_draw ούτε το κόψιμο του ob_fig, και η διεύθυνση
; οθόνης είναι μία για όλες: cpir στη στήλη των ux (~5 us η εγγραφή αντί για
; 11), και η φιγούρα κατευθείαν στο obfs_lp. Με τη σειρά της λίστας, όπως
; στην πλήρη σχεδίαση.
;
; ΧΡΕΩΝΕΙ ΟΣΑ ΚΑΝΕΙ, ΜΙΑ ΦΟΡΑ: DE = ό,τι χρεώνει ο καλών, και FGC_SCAN_US ανά
; εγγραφή, FGC_XM_US ανά εγγραφή με το ίδιο ux (ο έλεγχος του uy και η
; επανεκκίνηση του cpir), FGC_ONE_US ανά φιγούρα.
; ---------------------------------------------------------------------------
fg_cell:
        ld      a,h
        ld      (fgc_x + 1),a
        ld      a,l
        ld      (fgc_y + 1),a
        ld      a,(fg_n)
        ld      l,a
        ld      h,0
        add     hl,hl
        add     hl,hl
        add     hl,hl                   ; FGC_SCAN_US x εγγραφές
        add     hl,de                   ; + ό,τι χρεώνει ο καλών
        ld      (fgc_us + 1),hl
        or      a
        ld      de,0                    ; D = φιγούρες, E = εγγραφές με το ίδιο ux
        jr      z,fgc_end
        ld      c,a
        ld      b,d                     ; BC = εγγραφές
        ld      hl,G_fig_list
fgc_x:  ld      a,0
        cpir
        jr      nz,fgc_end
        inc     e
        dec     l
        set     6,l
        ld      a,(hl)                  ; uy
        res     6,l
fgc_y:  cp      0
        jr      nz,fgc_nx
        inc     d
        set     7,l
        ld      a,(hl)                  ; ο κωδικός της φιγούρας
        res     7,l
        push    bc
        push    de
        push    hl
        ld      l,a                     ; το L της, και το bit 0 η σελίδα (βήμα
        and     1                       ; 111, tools/pack.py: fig_code)
        add     a,G_fig_gfx >> 8
        ld      h,a
fgc_de: ld      de,0
        ld      b,SLOT_H
        call    obfs_lp                 ; πάνω σε ό,τι είναι ήδη εκεί
        pop     hl
        pop     de
        pop     bc
fgc_nx:
        inc     l
        ld      a,b
        or      c
        jr      nz,fgc_x
        ; ΜΙΑ ΧΡΕΩΣΗ ΓΙΑ ΟΛΑ: του καλούντος, η σάρωση, όσες με το ίδιο ux, οι
        ; φιγούρες — ένα dhv_charge αντί για τέσσερα ή πέντε (~20 us το καθένα)
fgc_end:
        ld      l,e
        ld      h,0
        add     hl,hl
        add     hl,hl
        add     hl,hl
        ld      b,h
        ld      c,l
        add     hl,hl
        add     hl,bc                   ; FGC_XM_US x όσες με το ίδιο ux
        ld      bc,FGC_ONE_US
        inc     d
        jr      fgc_d
fgc_one:
        add     hl,bc
fgc_d:
        dec     d
        jr      nz,fgc_one
fgc_us: ld      de,0
        add     hl,de
        ex      de,hl
        jp      dhv_charge

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
        add     a,a
        add     a,l                     ; 3 x εγγραφές < 256 (FG_CAP, assert)
        ld      l,a
        ld      h,0
        add     hl,hl
        add     hl,hl
        add     hl,hl                   ; 24 x εγγραφές
        ex      de,hl
        call    dhv_charge
        ld      hl,clip_x0
        ld      a,(cam_tx)
        add     a,a
        add     a,128
        ld      c,a                     ; C = 2 * cam + 128
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
        add     a,a
        add     a,128
        ld      c,a
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
        ld      a,(hl)                  ; ο κωδικός της φιγούρας
        ex      de,hl
        push    af
        call    fg_in                   ; μέσα στο παράθυρο = μέσα στο κάδρο
        pop     af
        ld      l,a                     ; το L της, και το bit 0 η σελίδα
        and     1
        add     a,G_fig_gfx >> 8
        ld      h,a
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
        inc     l                       ; καμία φιγούρα δεν περνά σελίδα (pack.py)
        or      (hl)
        inc     l
        ld      (de),a
        inc     e
        ld      a,(de)
        and     (hl)
        inc     l
        or      (hl)
        inc     l
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
        call    z,gh_wrap               ; src/ghost.asm: το ίδιο, τράπεζα 0
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
;
; ΜΕ ΤΗ ΣΕΙΡΑ ΠΟΥ ΕΙΧΕ Η ΛΙΣΤΑ (βήμα 134). Δύο φιγούρες στο ίδιο κελί: από
; πάνω είναι όποια είναι μετά στη λίστα. Ως το 133 η λίστα ξαναγινόταν με τη
; σειρά των πρακτόρων, 127 -> 0, ενώ στο παιχνίδι έχει τη σειρά που μπήκαν: η
; πλήρης σχεδίαση έδειχνε άλλη από πάνω (test_reach, θόλος S πάνω στο
; μονοπάτι). Πρώτα όσοι ήταν ήδη μέσα, με τη σειρά τους — ο καθένας μπαίνει
; σε θέση ίση ή πιο μπροστά από την παλιά του, που έχει ήδη διαβαστεί — και
; μετά όλοι, όπου όσοι μπήκαν βρίσκονται ίδιοι και μένουν.
;
; ΜΟΝΟ ΟΙ ΠΡΑΚΤΟΡΕΣ 0-99 (βήμα 134). Το dh_agent σβήνει το σημάδι του
; πράκτορα, και τα σημάδια των 100-127, που δεν υπάρχουν, είναι το EC_X
; (src/const.asm): ως το 133 κάθε view_draw (σπίτι, βοήθεια, φόρτωμα)
; μηδένιζε τις ώρες ηρεμίας του βήματος 121, και θα μηδένιζε τα νομίσματα.
; ---------------------------------------------------------------------------
fg_build:
        ld      hl,fg_q
        ld      (hl),1
        call    ob_b6                   ; η λίστα, τα σημάδια, οι πράκτορες
        ld      hl,fg_n
        ld      a,(hl)
        ld      (hl),0
        or      a
        jr      z,fgb_all
        ld      b,a
        ld      hl,G_fig_list + FG_AGENT
fgb_old:
        ld      a,(hl)
        inc     l
        push    hl
        push    bc
        ld      (dt_a),a
        call    dh_agent                ; γυρίζει με την 1
        call    ob_b6
        ld      a,(fg_na)
        or      128
        ld      l,a
        ld      h,OCCPG
        ld      (hl),255                ; πέρασε: το fgb_lp τον προσπερνά
        pop     bc
        pop     hl
        djnz    fgb_old
fgb_all:
        ; ΜΙΑ ΦΟΡΑ Ο ΚΑΘΕΝΑΣ. Οσοι πέρασαν από πάνω έχουν σημάδι 255 (ένα
        ; σημάδι αλλιώς είναι 0 ή 1, fg_mark): μόνο σβήνεται. Ενας νεκρός, ή μια
        ; κενή θέση, δεν είναι στη νέα λίστα — οι παλιές εγγραφές πέρασαν όλες
        ; από πάνω — άρα ούτε dh_agent: μόνο το σημάδι. Χωρίς αυτά, ο καθένας
        ; από τους 94 που δεν υπάρχουν έψαχνε τη λίστα (cpir), και κάθε φιγούρα
        ; περνούσε δύο φορές: 18,1 ms με έξι αποίκους έξω. Τώρα 5,3 (14,5 ως το
        ; βήμα 133, με το dh_agent για όλους τους 128).
        ld      b,AG_FOE0 + AG_NFOE     ; όχι N_AGENT (src/entity.asm): EC_X
        assert  EC_X - G_node_occ - 128 >= AG_FOE0 + AG_NFOE
fgb_lp:
        ld      a,b
        dec     a
        ld      l,a
        set     7,l
        ld      h,OCCPG
        inc     (hl)                    ; 255 -> 0: πέρασε ήδη
        jr      z,fgb_nx
        ld      (hl),0                  ; το σημάδι, όπως στο dh_agent
        res     7,l
        ld      h,AG_PG
        bit     0,(hl)                  ; F_ALIVE
        jr      z,fgb_nx
        ld      (dt_a),a
        push    bc
        call    dh_agent
        call    ob_b6
        pop     bc
fgb_nx:
        djnz    fgb_lp
        xor     a
        ld      (fg_q),a
        jp      ob_touch

; ---------------------------------------------------------------------------
; fg_want — L = πράκτορας (το bit 7 δεν μετρά), τράπεζα 6. Πού φαίνεται έξω:
; A = ο κωδικός της φιγούρας (βήμα 111), D = ux, E = uy (μισά tiles + 128)· ή A = 0, πουθενά.
; ---------------------------------------------------------------------------
fg_want:
        res     7,l
        ld      h,AG_PG
        bit     0,(hl)                  ; F_ALIVE
        jr      z,fw_none
        set     7,l
        ld      a,(hl)                  ; ρόλος
        and     15                      ; 0-8: ο εισβολέας είναι ο 8 (βήμα 111)
        add     a,role_fig & 255        ; μία σελίδα (assert): χωρίς ob_addu
        ld      e,a
        ld      d,role_fig >> 8
        ld      a,(de)
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
        ld      (fw_q),a
        call    fw_xy
        dec     d                       ; η στήλη της θέσης 0 (fw_dx)
        ld      (fw_b),de               ; by, bx
        ld      a,b
        ld      (fw_hb),a               ; το μισό του
        pop     af
        ld      c,a
        call    fw_xy                   ; D = ax, E = ay, B = ha· κρατά το C
        dec     d
        jp      fw_leg                  ; πάνω στο Γ (βήμα 118, src/walk6.asm),
                                        ; και από εκεί στο fw_out

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
        ; ΞΕΔΙΠΛΩΜΕΝΟ (βήμα 106): χωρίς djnz, 25 us λιγότερα ανά άξονα — και
        ; το fg_want το πληρώνει κάθε βήμα κάθε περιπατητή έξω, στο κάδρο ή όχι.
        repeat  8
        srl     l
        jr      nc,$ + 3
        add     a,h
        rra
        rend
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
        cp      MAX_DOME
        jr      nc,fwx_st
        call    ob_domeadr
        inc     l                       ; μια εγγραφή θόλου δεν περνά σελίδα
        inc     l                       ; στα 8 πρώτα της (assert στο τέλος)
        ld      a,(hl)                  ; D_SIZE: πλευρά 4 + 2 x μέγεθος tiles
        add     a,a
        add     a,4
        dec     l
        dec     l
        jr      fwx_go
fwx_st:
        add     a,a
        add     a,a
        add     a,a                     ; (64 + δομή) x 8 = δομή x 8 σε 8 bits
        ld      l,a
        ld      h,G_struct_tbl >> 8     ; μία σελίδα (assert στο τέλος)
        ld      b,l                     ; (βήμα 118: όχι push / pop, 3 us)
        inc     l
        inc     l
        ld      a,(hl)                  ; ST_KIND
        add     a,a
        add     a,a
        inc     l
        add     a,(hl)                  ; + ST_SIZE
        add     a,a
        inc     a                       ; struct_dims[είδος*4 + μέγεθος].h
        add     a,G_struct_dims & 255   ; μία σελίδα (assert)
        ld      l,a
        ld      h,G_struct_dims >> 8
        ld      a,(hl)
        rrca
        rrca
        rrca
        rrca
        and     #0F                     ; γραμμές / 16 = μισό ύψος σε μισά tiles
        ld      l,b
        ld      h,G_struct_tbl >> 8
fwx_go:
        ld      b,a
        ld      d,(hl)                  ; cx
        inc     l
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
; dhv_rect_c — το ίδιο, με το clip ήδη στημένο (fg_erase, βήμα 106).
dhv_rect_c:
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
dhv_put:
        call    ob_put                  ; ΓΡΑΜΜΕΝΟ: fg_tile όσο σβήνει κελί φιγούρας
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
        ; --- και από πάνω ό,τι πατά εκεί: όλα. Ως το βήμα 105 και μόνο οι
        ; φιγούρες, όταν το έλεγε το fg_erase· από το 106 εκείνο έχει δικό
        ; του δρόμο (fge_free) ---
        ld      hl,ob_clip_full         ; η επιστροφή του ob_draw_all: μετά,
        push    hl                      ; το clip ολόκληρο
        jp      ob_draw_all

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

; fg_tile — το tile κάτω από το κελί μιας φιγούρας έξω (το clip), αντί για το
; ob_put του dhv_rect_us (fge_go, βήμα 105). Το (ob_src) είναι το tile.
;
; ΚΑΤΕΥΘΕΙΑΝ. Ως το βήμα 104 περνούσε από το ob_put: όλο το tile κομμένο στο
; 2x8 — κόψιμο σε κάθε πλευρά, δείκτες γραμμής — ~1 ms για 16 bytes, το ένα
; πέμπτο ενός βήματος αποίκου έξω. Εδώ τα 16 bytes, γραμμή γραμμή:
;
; - Το κελί είναι ΟΛΟ μέσα στο κάδρο (fg_in), άρα το clip είναι το κελί: x
;   ζυγό ως 78, y σε σειρά χαρακτήρων ως 152.
; - Κάθε γραμμή του είναι η προηγούμενη + #800, όπως στο ob_fig.
; - Τα δύο bytes μιας γραμμής είναι στην ίδια σελίδα της οθόνης: η διεύθυνση
;   είναι ζυγή (x ζυγό, cam_p πολλαπλάσιο του 4: view_cam), οπότε το πρώτο
;   δεν είναι ποτέ #xxFF.
; - Μέσα στο tile, 4 bytes τη γραμμή, το κελί είναι το μισό του: + 32 το
;   κάτω, + 2 το δεξί.
;
; ΚΑΙ Η ΦΛΕΒΑ από πάνω, με μάσκα, όπως στο tile_one. Ως το βήμα 104 ένα κελί
; που σβηνόταν πάνω σε φλέβα (βουνό με το bit πόρου) την έχανε ως την
; επόμενη πλήρη σχεδίαση.
fg_tile:
        ld      a,(clip_x0)
        ld      c,a
        ld      a,(clip_y0)
        call    scr_addr                ; DE = η οθόνη· κρατά το BC
; fgt_de — το ίδιο με DE = η οθόνη, C = clip_x0 (fge_free).
fgt_de:
        ld      a,(clip_y0)
        and     8
        add     a,a
        add     a,a                     ; 0 ή 32
        ld      b,a
        ld      a,c
        and     2                       ; 0 ή 2
        add     a,b
        ld      (fgv_q + 1),a           ; το τέταρτο, και για τη φλέβα
        ld      c,a
        ld      b,0
        ld      hl,(ob_src)
        add     hl,bc
        ld      b,SLOT_H
fgt_lp:
        ld      a,(hl)
        ld      (de),a
        inc     l                       ; το tile είναι 64 bytes σε όριο 64
        inc     e                       ; (assert): το L δεν ξεχειλίζει
        ld      a,(hl)
        ld      (de),a
        dec     e
        inc     l
        inc     l
        inc     l                       ; η επόμενη γραμμή του tile
        ld      a,d
        add     a,8
        ld      d,a
        djnz    fgt_lp
        ld      a,(t_cur)
        ld      c,a
        and     15
        cp      11                      ; βουνό με το bit πόρου
        ret     nz
        ; ΚΑΙ Η ΦΛΕΒΑ ΚΑΤΕΥΘΕΙΑΝ (βήμα 106), όπως το obfs_lp. Ως το 105 το
        ; ob_put της κόστιζε ~1.700 us, ενώ το σβήσιμο χρέωνε μόνο το tile.
        ; Η φλέβα είναι 4 x 16 σε ζεύγη (μάσκα, data): 8 bytes η γραμμή, και
        ; το τέταρτό της στο διπλάσιο του τετάρτου του tile.
        ld      a,d
        sub     8 * SLOT_H
        ld      d,a                     ; η πρώτη γραμμή του κελιού ξανά
        ld      a,c
        add     a,a                     ; decor & 1 (bit 6) -> bit 7
        and     #80                     ; 2 παραλλαγές, x ORE_OVL_SZ
        ld      l,a
fgv_q:  ld      a,0
        add     a,a
        add     a,l
        ld      l,a
        ld      h,G_ore_overlay >> 8    ; σε όριο 256 (tiles.asm): το L φτάνει
        ld      b,SLOT_H
fgv_lp:
        ld      a,(de)
        and     (hl)
        inc     l
        or      (hl)
        inc     l
        ld      (de),a
        inc     e
        ld      a,(de)
        and     (hl)
        inc     l
        or      (hl)
        ld      (de),a
        dec     e
        ld      a,l
        add     a,5                     ; η επόμενη γραμμή της φλέβας
        ld      l,a
        ld      a,d
        add     a,8
        ld      d,a
        djnz    fgv_lp
        ld      de,FG_VEIN_US
        jp      dhv_charge

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

; ---------------------------------------------------------------------------
; st_mark — η ουρά του ob_struct (src/object.asm), με το s_rec γεμάτο και την
; τράπεζα 6 μέσα: μια δομή που είναι ακόμη ΕΡΓΟΤΑΞΙΟ έχει στο κέντρο της το
; σήμα της αναμονής των μηχανών (βήμα 100), τις κίτρινες και μαύρες ρίγες.
; Ως το βήμα 108 μια δομή φαινόταν ίδια χτισμένη ή όχι (§15). Το σήμα είναι
; αδιαφανές και μέσα στο sprite κάθε δομής: όπου ξαναζωγραφίζεται η δομή,
; ξαναζωγραφίζεται και αυτό. Σβήνει με το DK_TILE του st_built (src/meteor.asm).
; Εδώ, στην τράπεζα 2: είναι 34 bytes, και στην 0 έμεναν 27 ως το όριο των
; δοκιμών.
; ---------------------------------------------------------------------------
st_mark:
        ld      a,(s_rec+ST_STATE)
        cp      DS_ACTIVE
        ret     z
        ld      a,(s_rec+ST_CX)
        call    ob_sx
        dec     hl                      ; το κέντρο μείον ένα byte
        ld      (ob_x),hl
        ld      a,(s_rec+ST_CY)
        call    ob_sy
        dec     hl
        dec     hl
        dec     hl                      ; και τρεις γραμμές
        ld      (ob_y),hl
        ld      hl,G_marks + MARK_W * MARK_H    ; περιμένει
        jp      ob_mark
        assert  MARK_W == 2 && MARK_H == 6

; Η σειρά του slot γύρω από τη δομή: ζευγάρια (νότια, βόρεια) ανά στήλη. Το
; corr_fill γεμίζει 0, 4, 2, 6 πρώτα: -1, 0, -2, +1 — συνεχόμενη σειρά σε
; κάθε πλήθος.
fw_dx:      db -1, -2, 0, 1

fg_n:       db 0                        ; εγγραφές της λίστας
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
        assert  (G_fig_list & 255) == 0 && (G_fig_gfx & 255) == 192   ; FIG_PHASE (tools/pack.py)
        assert  FG_CAP * 4 == 256 && SLOT_W == 2 && SLOT_H == 8
        assert  ((G_node_adj >> 3) & 255) + 128 <= 256
        assert  FG_SCAN_US == 24 && FG_CAP * 3 < 256
        assert  FGC_SCAN_US == 8 && FGC_XM_US == 24    ; οι ολισθήσεις του fg_cell
        assert  (role_fig & 255) + 16 <= 256   ; and 15
        assert  FC_COLONIST & 1 && (FC_INTRUDER & 1) == 0   ; οι δύο σελίδες (tools/pack.py)
        assert  ((G_tile_ground | G_tile_dust | G_tile_rock | G_tile_mountain) & 63) == 0
        assert  ((G_tile_water | G_tile_deepwater | G_tile_crater | G_tile_foundation) & 63) == 0
        assert  (G_struct_dims & 255) + 64 <= 256          ; 64 bytes (build/layout.txt)
        assert  obf_n == obf_k + 1 && (G_slot_empty >> 8) != 0
        assert  (G_struct_tbl & 255) == 0 && MAX_STRUCT * STRUCT_REC == 256 && MAX_DOME == 64
        assert  (G_dome_tbl & 7) == 0 && (DOME_REC & 7) == 0 && D_SIZE < 8  ; τα inc l του fw_xy
