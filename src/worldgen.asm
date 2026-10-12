; worldgen.asm — η γεννήτρια κόσμου (DESIGN.md §5)
;
; Η ΠΡΟΔΙΑΓΡΑΦΗ είναι το tools/worldgen_ref.py. Ό,τι εδώ οφείλει να βγάλει
; byte-προς-byte το ίδιο 16 KB επίπεδο για το ίδιο seed — το
; tests/test_worldgen.py το επιβάλλει, και μια διαφορά σε ΕΝΑ tile το ρίχνει.
;
; Η σύμβαση του §5.1: κάθε βήμα καθαρή συνάρτηση του seed. Καμία χρήση του
; καταχωρητή R, του μετρητή frames, ή αδιευκρίνιστης μνήμης.
;
; Η τράπεζα 4 πρέπει να είναι σελιδοποιημένη σε όλη τη διάρκεια.

GEN_PLANE   equ #4000               ; η τράπεζα 4 στο παράθυρο

; ---------------------------------------------------------------------------
; worldgen_run — In: (gen_seed), (gen_planet). Τράπεζα 4 σελιδοποιημένη.
; ---------------------------------------------------------------------------
worldgen_run:
        ld      hl,(gen_seed)
        ld      a,h
        or      l
        jr      nz,wr_seed_ok
        ld      hl,#ACE1            ; το μηδέν είναι απορροφητικό στο LFSR
wr_seed_ok:
        ld      (gen_rng),hl
        ; αντίγραψε τα κατώφλια του πλανήτη σε σταθερές θέσεις
        ld      a,(gen_planet)
        and     3
        ; ΕΞΙ bytes ανά πλανήτη, όχι τέσσερα. Η προηγούμενη εκδοχή έβγαζε
        ; planet*4 ενώ ο σχολιασμός της έλεγε *6, και κανείς δεν το έβλεπε:
        ; ο πλανήτης ήταν πάντα 0, όπου τα δύο συμπίπτουν. Με πλανήτη 1 τα
        ; κατώφλια διαβάζονταν δύο bytes μέσα στη σειρά — γονιμότητα ως βάθος
        ; νερού.
        ld      l,a
        ld      h,0
        add     hl,hl               ; p*2
        ld      d,h
        ld      e,l
        add     hl,hl               ; p*4
        add     hl,de               ; HL = planet*6
        ld      de,gen_planets
        add     hl,de
        ld      de,thr_W2
        ld      bc,6
        ldir
        call    gen_perm
        call    wg_anchors
        call    wg_coarse
        call    wg_plane
        call    gen_despeckle
        jp      gen_landing

; ---------------------------------------------------------------------------
; gen_rnd — LFSR 16-bit Galois, οκτώ βήματα, επιστρέφει το χαμηλό byte.
; Out: A.  Χαλάει: A, B, F, HL
; ---------------------------------------------------------------------------
gen_rnd:
        ld      hl,(gen_rng)
        ld      b,8
gr_step:
        srl     h
        rr      l                   ; κρατούμενο = το bit που βγήκε
        jr      nc,gr_no
        ld      a,h
        xor     #B4
        ld      h,a
gr_no:
        djnz    gr_step
        ld      (gen_rng),hl
        ld      a,l
        ret

; ---------------------------------------------------------------------------
; gen_hash — H(gx,gy) = P[(P[gx] + gy) & 255].  Το P είναι σε σελίδα, οπότε
; δύο αναζητήσεις είναι δύο `ld a,(hl)`.
; In: A = gx, C = gy.  Out: A.  Χαλάει: A, F, HL
; ---------------------------------------------------------------------------
gen_hash:
        ld      h,gen_P/256
        ld      l,a
        ld      a,(hl)
        add     a,c
        ld      l,a
        ld      a,(hl)
        ret

; ---------------------------------------------------------------------------
; gen_perm — P[i] = i, μετά for i = 255 downto 1: swap P[i], P[rnd()]
; ---------------------------------------------------------------------------
gen_perm:
        ld      hl,gen_P
        xor     a
gp_init:
        ld      (hl),a
        inc     l
        inc     a
        jr      nz,gp_init
        ld      c,255               ; i
gp_loop:
        push    bc
        call    gen_rnd             ; A = j
        pop     bc
        ld      h,gen_P/256
        ld      l,a                 ; HL -> P[j]
        ld      d,h
        ld      e,c                 ; DE -> P[i]
        ld      a,(de)              ; παλιό P[i]
        ld      b,(hl)              ; παλιό P[j]
        ld      (hl),a
        ld      a,b
        ld      (de),a
        dec     c
        jr      nz,gp_loop
        ret

; ---------------------------------------------------------------------------
; gen_mul — HL = D * E, θετικά, 8x8 -> 16.  Χαλάει: A, B, DE, HL
; ---------------------------------------------------------------------------
gen_mul:
        ld      hl,0
        ld      b,8
        ld      a,d
        ld      d,0
gm_lp:
        srl     a
        jr      nc,gm_no
        add     hl,de
gm_no:
        sla     e
        rl      d
        djnz    gm_lp
        ret

; ---------------------------------------------------------------------------
; wg_anchors — έξι άγκυρες, μία ανά τομέα 60°, είδη καρφωτά.
;
;   d   = (k*4 + rnd&3)          — πάντα < 24, οπότε το modulo του §5.6 φεύγει
;   rad = lo + (rnd & mask)
;   ax  = (rad * dirx) >> 6      αριθμητική ολίσθηση: το >> της Python στρογγυλεύει
;   ay  = (rad * diry) >> 6      προς τα κάτω και στα αρνητικά
; ---------------------------------------------------------------------------
wg_anchors:
        xor     a
        ld      (ga_k),a
        ld      ix,gen_spec
        ld      iy,anchors
ga_loop:
        call    gen_rnd
        and     3
        ld      b,a
        ld      a,(ga_k)
        add     a,a
        add     a,a
        add     a,b                 ; d = k*4 + (rnd&3), πάντα < 24
        ld      (ga_dir),a
        call    gen_rnd
        and     (ix+2)              ; mask
        add     a,(ix+1)            ; lo
        ld      (ga_rad),a
        ld      (iy+3),a
        ld      a,(ix+0)            ; είδος
        cp      3
        jr      nz,ga_kind          ; όχι wild — το A είναι ήδη το είδος
        call    gen_rnd
        and     1
        xor     1                   ; 1 -> λίμνη(0), 0 -> ράχη(1)
ga_kind:
        ld      (iy+2),a
        ld      a,(ga_dir)
        add     a,a                 ; ζεύγη
        ld      l,a
        ld      h,0
        ld      de,gen_dir
        add     hl,de
        ld      a,(hl)              ; dx
        inc     hl
        ld      b,(hl)              ; dy
        push    bc
        call    ga_scale
        ld      (iy+0),a
        pop     bc
        ld      a,b
        call    ga_scale
        ld      (iy+1),a
        ; scale = 256 / rad, μία διαίρεση ανά άγκυρα
        ld      a,(ga_rad)
        call    gen_recip
        ld      (iy+4),a
        ld      de,3
        add     ix,de
        ld      de,5
        add     iy,de
        ld      a,(ga_k)
        inc     a
        ld      (ga_k),a
        cp      GEN_ANCHORS
        jr      nz,ga_loop
        ret

; ga_scale — A = προσημασμένο dx· επιστρέφει (rad*dx)>>6, αριθμητικά.
ga_scale:
        ld      c,a
        and     #80
        ld      (ga_neg),a
        ld      a,c
        jr      z,ga_pos
        neg
ga_pos:
        ld      d,a
        ld      a,(ga_rad)
        ld      e,a
        push    iy
        push    ix
        call    gen_mul             ; HL = |dx| * rad
        pop     ix
        pop     iy
        ld      a,(ga_neg)
        or      a
        jr      z,ga_nonneg
        ; HL = -HL
        xor     a
        sub     l
        ld      l,a
        sbc     a,a
        sub     h
        ld      h,a
ga_nonneg:
        ; αριθμητική ολίσθηση >> 6
        ld      b,6
ga_sh:
        sra     h
        rr      l
        djnz    ga_sh
        ld      a,l
        ret

; gen_recip — A = rad -> A = 256/rad. Διαίρεση με αφαιρέσεις· τρέχει έξι φορές
; συνολικά, οπότε η ταχύτητα δεν μετράει.
gen_recip:
        ld      hl,256
        ld      d,0
        ld      e,a
        ld      b,0
gre_lp:
        or      a
        sbc     hl,de
        jr      c,gre_done
        inc     b
        jr      gre_lp
gre_done:
        ld      a,b
        ret

; ---------------------------------------------------------------------------
; wg_coarse — τα δύο χονδρά πλέγματα 16x16.
;   coarse_e[i*16+j] = H(j, i)
;   coarse_m[i*16+j] = H(j, i + GEN_MSALT)
; ---------------------------------------------------------------------------
wg_coarse:
        ld      de,coarse_e
        ld      c,0                 ; i (gy)
gc_row:
        ld      b,0                 ; j (gx)
gc_col:
        push    bc
        push    de
        ld      a,b
        call    gen_hash
        pop     de
        ld      (de),a
        inc     de
        pop     bc
        inc     b
        ld      a,b
        cp      GEN_COARSE
        jr      nz,gc_col
        inc     c
        ld      a,c
        cp      GEN_COARSE
        jr      nz,gc_row
        ; ίδιο, με αλάτι υγρασίας
        ld      de,coarse_m
        ld      c,GEN_MSALT
gc_row2:
        ld      b,0
gc_col2:
        push    bc
        push    de
        ld      a,b
        call    gen_hash
        pop     de
        ld      (de),a
        inc     de
        pop     bc
        inc     b
        ld      a,b
        cp      GEN_COARSE
        jr      nz,gc_col2
        inc     c
        ld      a,c
        cp      GEN_MSALT+GEN_COARSE
        jr      nz,gc_row2
        ret

; ---------------------------------------------------------------------------
; gen_row — μία γραμμή 128 τιμών από χονδρό πλέγμα.
; In: HL = coarse, DE = προορισμός, (gr_v) = v
;
; Κάθετα: παρεμβολή ανάμεσα σε δύο γραμμές πλέγματος.
; Οριζόντια: ράμπα με συσσωρευτή 8.8 — το acc>>8 ισούται ΑΚΡΙΒΩΣ με
; a + ((b-a)*f >> 3), χωρίς πολλαπλασιασμό ανά tile.
; ---------------------------------------------------------------------------
gen_row:
        ; ΒΗΜΑ 112: με καταχωρητές. Το top και το bot είναι στην ίδια σελίδα του
        ; πλέγματος (16 x 16, ευθυγραμμισμένο), οπότε το bot είναι το L + 16 και
        ; το τύλιγμα της σειράς 15 στη 0 είναι το τύλιγμα του L. Ως τότε 11 ms
        ; η κλήση, με τους δείκτες στη μνήμη.
        push    de
        ld      a,(gr_v)
        and     7
        ld      (grr_fv+1),a            ; fv
        ld      a,(gr_v)
        and     #F8
        add     a,a                     ; (v >> 3) * 16
        ld      l,a
        ld      de,gen_lat
        ld      b,GEN_COARSE
grr_lat:
        ld      a,l
        add     a,16
        ld      l,a
        ld      c,(hl)                  ; b = bot[j]
        ld      a,l
        sub     16
        ld      l,a
        ld      a,c
        sub     (hl)                    ; b - a, και το δάνειο είναι το πρόσημο
        jr      z,grr_same
        push    hl
        push    bc
        ld      c,a
        sbc     a,a
        ld      b,a                     ; BC = b - a, ΠΛΗΡΗ 16 bits (ως ±255)
        ld      hl,0
grr_fv: ld      a,0                     ; fv
        or      a
        jr      z,grr_z
grr_m:  add     hl,bc
        dec     a
        jr      nz,grr_m
grr_z:  sra     h
        rr      l
        sra     h
        rr      l
        sra     h
        rr      l                       ; >> 3, αριθμητικά
        ld      a,l
        pop     bc
        pop     hl
        add     a,(hl)                  ; + a
        jr      grr_st
grr_same:
        ld      a,(hl)
grr_st: ld      (de),a
        inc     de
        inc     l
        djnz    grr_lat
        ld      a,(gen_lat)
        ld      (de),a                  ; lat[16] = lat[0]: το τύλιγμα της ράμπας
        ; ράμπα: 16 κελιά x 8 tiles, συσσωρευτής 8.8
        pop     de
        ld      ix,gen_lat
        ld      iyl,GEN_COARSE          ; ΟΧΙ το AF': το firmware θέλει τα δικά του
grr_cell:
        ld      a,(ix+1)                ; b
        sub     (ix+0)                  ; - a
        ld      l,a
        sbc     a,a
        ld      h,a                     ; HL = b - a
        add     hl,hl
        add     hl,hl
        add     hl,hl
        add     hl,hl
        add     hl,hl                   ; << 5
        ld      b,h
        ld      c,l
        ld      h,(ix+0)
        ld      l,0                     ; acc = a << 8
        repeat  8
        ld      a,h
        ld      (de),a
        inc     e                       ; erow, mrow: μισή σελίδα, χωρίς πέρασμα
        add     hl,bc
        rend
        inc     ix
        dec     iyl
        jr      nz,grr_cell
        ret

; ---------------------------------------------------------------------------
; wg_plane — το κύριο πέρασμα. Μία γραμμή τη φορά: τα δύο πεδία, οι ενεργές
; άγκυρες, το ύψος, μετά 128 tiles.
;
; ΤΟ ΒΗΜΑ 112: ΤΟ ΙΔΙΟ ΕΠΙΠΕΔΟ ΣΕ ΚΛΑΣΜΑ ΤΟΥ ΧΡΟΝΟΥ. Ως τότε κάθε tile κόστιζε
; ~540 us: δύο hash, τριάντα αναγνώσεις μνήμης, μια κλήση gen_mul με βρόχο οκτώ
; βημάτων για κάθε άγκυρα, και στη ζώνη ανάμειξης ένα άθροισμα επαναλαμβανόμενο
; ως 255 φορές. Τώρα:
;
;   - ΤΟ ΥΨΟΣ ΑΝΑ ΓΡΑΜΜΗ (gp_epass): οι δύο οκτάβες αλλάζουν ανά 4 και ανά 2
;     tiles, οπότε υπολογίζονται μία φορά για τη γραμμή, πάνω στο ίδιο το erow.
;   - ΤΑ ΚΑΤΩΦΛΙΑ ΤΟΥ ΠΛΑΝΗΤΗ ΜΕΣΑ ΣΤΙΣ ΕΝΤΟΛΕΣ (gt_planet): `cp n` αντί για
;     τρεις αναγνώσεις μνήμης ανά σύγκριση. Το ίδιο για το |y|, το v και το v+7
;     ανά γραμμή.
;   - ΤΜΗΜΑΤΑ ΑΝΤΙ ΓΙΑ ΕΛΕΓΧΟ ΑΝΑ TILE: το r = max(|x|,|y|) ενδιαφέρει μόνο στο
;     χείλος (r >= 57) και στο κέντρο (r <= 10). Η γραμμή χωρίζεται σε κομμάτια
;     γνωστά από το |y|, και μόνο τα δικά τους tiles (gtG) υπολογίζουν r· τα
;     υπόλοιπα (gtN) πάνε κατευθείαν στην ταξινόμηση.
;   - ΟΙ ΑΓΚΥΡΕΣ ΜΕ ΠΙΝΑΚΑ ΚΑΙ ΜΕ ΠΛΑΤΟΣ (gp_active, gt_anc): για κάθε ενεργή
;     άγκυρα η γραμμή ξέρει από πριν ποια u είναι μέσα (η απόσταση είναι
;     μονότονη στο dx), και το βάρος min(255, (rad - d) * scale) είναι πίνακας
;     ανά άγκυρα, φτιαγμένος μία φορά (wg_wtab). Ο πολλαπλασιασμός της
;     εφαρμογής ξετυλιγμένος (mul8).
;
; Ο ΧΤΥΠΟΣ ΤΗΣ ΜΟΥΣΙΚΗΣ (§9.5) ΔΥΟ ΦΟΡΕΣ ΑΝΑ ΓΡΑΜΜΗ, στο u = 0 και στο u = 64:
; ως τότε ανά 32 tiles, ~17 ms· μία γραμμή κρατά τώρα ~40 ms, οπότε ~20.
; ---------------------------------------------------------------------------
; wg_prog — A = σειρά 0..127. Η οθόνη προόδου ανήκει στη ΓΕΝΝΗΤΡΙΑ, που ξέρει
; πού ζει η οθόνη και σε ποια λειτουργία· το tests/gentest.asm δεν έχει οθόνη
; και δεν θέλει μπάρα, οπότε η προεπιλογή εδώ είναι «τίποτα». Το gen.asm ορίζει
; WG_PROGRESS και δίνει το δικό του.
        ifndef WG_PROGRESS
wg_prog:
        ret
        endif

; wg_beat — ο χτύπος. Το gen.asm δίνει τον δικό του (μουσική)· οι δοκιμές που
; τρέχουν τη γέννηση χωρίς ήχο παίρνουν αυτόν.
        ifndef WG_PROGRESS
wg_beat:
        ret
        endif

; gt_planet — τα κατώφλια του πλανήτη (thr_*) μέσα στις συγκρίσεις.
gt_planet:
        ld      a,(thr_W2)
        ld      (gcw2+1),a
        ld      a,(thr_W1)
        ld      (gcw1+1),a
        ld      a,(thr_M2)
        ld      (gcm2+1),a
        ld      a,(thr_M1)
        ld      (gcm1+1),a
        ld      a,(thr_F)
        ld      (gcf+1),a
        ld      a,(thr_OT)
        ld      (gcot+1),a
        ret

wg_plane:
        call    gt_planet
        call    wg_wtab
        xor     a
        ld      (gp_v),a
        ld      hl,GEN_PLANE
        ld      (gp_wptr),hl
gpl_row:
        ld      a,(gp_v)
        call    wg_prog                 ; η μπάρα του §5.9, μία κίνηση ανά σειρά
        call    wg_beat                 ; και ο χτύπος της μουσικής
        ld      a,(gp_v)
        ld      (gr_v),a
        ld      hl,coarse_e
        ld      de,erow
        call    gen_row
        ld      a,(gp_v)
        ld      (gr_v),a
        ld      hl,coarse_m
        ld      de,mrow
        call    gen_row
        ; --- τα ανά γραμμή: y, |y|, v, v+7 ---
        ld      a,(gp_v)
        ld      (gcov+1),a              ; H(u + ORE_SALT, v)
        add     a,7
        ld      (gtv7+1),a              ; H(u, v + 7)
        ld      a,(gp_v)
        sub     64
        ld      (gp_y),a
        jp      p,gpl_ya
        neg
gpl_ya: ld      (ggy+1),a
        ld      (ggy2+1),a
        ld      (gp_ay),a
        call    gp_epass
        call    gp_active
        ; --- τα tiles, κομμάτι-κομμάτι, και ένας δεύτερος χτύπος στο u = 64 ---
        ld      de,(gp_wptr)
        ld      c,0
        ld      a,(gp_ay)
        cp      R_RIM
        jr      c,gpl_mid
        ld      a,64                    ; όλη η γραμμή στο χείλος
        ld      hl,gtG
        call    gt_seg
        call    wg_beat
        ld      a,128
        ld      hl,gtG
        call    gt_seg
        jr      gpl_end
gpl_mid:
        ld      a,R_RIM - 57 + 8        ; u 0..7: x <= -57
        ld      hl,gtG
        call    gt_seg
        ld      a,(gp_ay)
        cp      R_BLEND + 1
        jr      nc,gpl_plain
        ld      a,64 - R_BLEND          ; u 8..53: 10 < |x| < 57
        ld      hl,gtN
        call    gt_seg
        ld      a,64                    ; u 54..63: το κέντρο, ως τη μέση
        ld      hl,gtG
        call    gt_seg
        call    wg_beat
        ld      a,64 + R_BLEND + 1      ; u 64..74
        ld      hl,gtG
        call    gt_seg
        jr      gpl_right
gpl_plain:
        ld      a,64                    ; u 8..63
        ld      hl,gtN
        call    gt_seg
        call    wg_beat
gpl_right:
        ld      a,64 + R_RIM            ; ως το u 120
        ld      hl,gtN
        call    gt_seg
        ld      a,128                   ; u 121..127: x >= 57
        ld      hl,gtG
        call    gt_seg
gpl_end:
        ld      (gp_wptr),de
        ld      a,(gp_v)
        inc     a
        ld      (gp_v),a
        cp      128
        jp      nz,gpl_row
        ret

        assert  R_RIM - 57 == 0         ; τα όρια των κομματιών είναι γραμμένα για το 57

; gt_seg — τα tiles C..A-1 με το σώμα HL. Γυρίζει από το gtjp.
gt_seg:
        ld      (gtend+1),a
        ld      (gtjp+1),hl
        jp      (hl)

; ---------------------------------------------------------------------------
; ΤΟ TILE. B = e, C = u, DE = η θέση του στο επίπεδο.
; ---------------------------------------------------------------------------
; gtG — με το r: πλατό, ανάμειξη, χείλος.
gtG:
        ld      h,erow >> 8
        ld      l,c
        ld      b,(hl)
gtGa:   nop                             ; call gt_anc, όταν η γραμμή έχει άγκυρες
        nop
        nop
        ld      a,c
        sub     64
        jr      nc,gg_px
        neg
gg_px:
ggy:    cp      0                       ; |y|
        jr      nc,gg_r
ggy2:   ld      a,0                     ; |y|
gg_r:   cp      R_PLATEAU + 1
        jr      c,gg_plat
        cp      R_BLEND + 1
        jr      c,gg_blend
        cp      R_RIM
        jr      c,gt_cls
        ; χείλος: e = min(255, e + (r - R_RIM + 1) * 40)
        sub     R_RIM
        add     a,gen_rim & 255
        ld      l,a
        adc     a,gen_rim >> 8
        sub     l
        ld      h,a
        ld      a,b
        add     a,(hl)
        jr      nc,gg_rok
        ld      a,255
gg_rok: ld      b,a
        jr      gt_cls
gg_plat:
        ld      b,GEN_MID
        jr      gt_cls
gg_blend:
        ; e = MID + (((e - MID) * w) >> 8), προσημασμένο: αρνητικό στρογγυλεύει
        ; ΚΑΤΩ, δηλαδή MID - ceil((MID - e) * w / 256)
        sub     R_PLATEAU
        add     a,gen_blend & 255
        ld      l,a
        adc     a,gen_blend >> 8
        sub     l
        ld      h,a
        push    de
        ld      e,(hl)                  ; w
        ld      a,b
        sub     GEN_MID
        jr      c,gg_bneg
        call    mul8
        ld      a,h
        add     a,GEN_MID
        jr      gg_bdone
gg_bneg:
        neg
        call    mul8
        ld      de,255
        add     hl,de
        ld      a,GEN_MID
        sub     h
gg_bdone:
        ld      b,a
        pop     de
        jr      gt_cls

; gtN — χωρίς r: 10 < r < 57.
gtN:
        ld      h,erow >> 8
        ld      l,c
        ld      b,(hl)
gtNa:   nop                             ; call gt_anc, όταν η γραμμή έχει άγκυρες
        nop
        nop
; --- ταξινόμηση: B = e -> B = κλάση | πόρος << 3 ---
gt_cls:
        ld      a,b
gcw2:   cp      0                       ; e < W2: βαθύ νερό
        jr      c,gc_deep
gcw1:   cp      0                       ; e < W1: νερό
        jr      c,gc_water
gcm2:   ld      a,0                     ; e > M2: βουνό
        cp      b
        jr      c,gc_mount
gcm1:   ld      a,0                     ; e > M1: βράχος
        cp      b
        jr      c,gc_rock
        ld      h,erow >> 8             ; m > F: έδαφος, γόνιμο· αλλιώς σκόνη
        ld      a,c
        or      #80                     ; το mrow είναι το δεύτερο μισό της σελίδας
        ld      l,a
        ld      b,(hl)
gcf:    ld      a,0
        cp      b
        ld      b,1                     ; DUST (το ld δεν αγγίζει σημαίες)
        jr      nc,gt_wr
        ld      b,8                     ; GROUND, με πόρο
        jr      gt_wr
gc_deep:
        ld      b,5
        jr      gt_wr
gc_water:
        ld      b,4
        jr      gt_wr
gc_rock:
        ld      b,2
        jr      gt_wr
gc_mount:
        ld      b,3
        ld      a,(gt_ore)
        or      a
        jr      z,gt_wr
        ld      h,gen_P >> 8            ; φλέβα αν H(u + ORE_SALT, v) > OT
        ld      a,c
        add     a,GEN_OSALT
        ld      l,a
        ld      a,(hl)
gcov:   add     a,0                     ; v
        ld      l,a
        ld      a,(hl)
        ld      l,a
gcot:   ld      a,0                     ; OT
        cp      l
        jr      nc,gt_wr
        ld      b,3 + 8
; --- εγγραφή: decor = H(u, v+7) & 3 στα bits 6-7 ---
gt_wr:
        ld      h,gen_P >> 8
        ld      l,c
        ld      a,(hl)
gtv7:   add     a,0                     ; v + 7
        ld      l,a
        ld      a,(hl)
        rrca
        rrca
        and     #C0
        or      b
        ld      (de),a
        inc     de
        inc     c
        ld      a,c
gtend:  cp      0                       ; το τέλος του κομματιού
gtjp:   jp      c,0                     ; gtG ή gtN
        ret                             ; στο gt_seg του wg_plane

; ---------------------------------------------------------------------------
; gp_epass — e = min(255, max(0, erow[u] + (H(u>>2, v>>2)>>3) + (H(u>>1, v>>1)>>4)
; - 23)), πάνω στο erow, για όλη τη γραμμή. Το πρώτο hash αλλάζει ανά 4 u, το
; δεύτερο ανά 2.
; ---------------------------------------------------------------------------
gp_epass:
        ld      a,(gp_v)
        srl     a
        ld      (gpe_v1+1),a
        srl     a
        ld      (gpe_v2+1),a
        ld      de,erow
gpe_lp:
        ld      h,gen_P >> 8
        ld      a,e
        and     3
        jr      nz,gpe_h2
        ld      a,e
        rrca
        rrca
        and     #3F                     ; u >> 2
        ld      l,a
        ld      a,(hl)
gpe_v2: add     a,0                     ; v >> 2
        ld      l,a
        ld      a,(hl)
        rrca
        rrca
        rrca
        and     #1F                     ; >> 3
        ld      (gpe_h1+1),a
gpe_h2:
        ld      a,e
        rrca
        and     #7F                     ; u >> 1
        ld      l,a
        ld      a,(hl)
gpe_v1: add     a,0                     ; v >> 1
        ld      l,a
        ld      a,(hl)
        rrca
        rrca
        rrca
        rrca
        and     #0F                     ; >> 4
gpe_h1: add     a,0                     ; + το πρώτο
        ld      c,a                     ; s, ως 46
        repeat  2
        ld      a,(de)
        add     a,c
        jr      c,@big
        sub     23
        jr      nc,@ok
        xor     a                       ; κάτω από το μηδέν
        jr      @ok
@big:   sub     23                      ; t >= 256: t - 23 >= 233
        jr      c,@ok                   ; ...και < 256: το δάνειο δίνει ακριβώς αυτό
        ld      a,255
@ok:    ld      (de),a
        inc     e
        rend
        bit     7,e
        jr      z,gpe_lp
        ret


; ---------------------------------------------------------------------------
; gp_active — οι άγκυρες που αγγίζουν αυτή τη γραμμή, με ό,τι χρειάζεται ανά
; tile ήδη έτοιμο. Μια άγκυρα είναι ενεργή αν dy = |y - ay| < rad. Μέσα της
; είναι τα |dx| <= t, γιατί η απόσταση d = max + min/2 είναι μονότονη στο dx:
;   - αν κάποιο dx > dy είναι μέσα (A2 = rad - (dy>>1) - 1 > dy), t = A2·
;   - αλλιώς t = min(dy, 2(rad - dy) - 1).
; (Ελεγμένο απέναντι στον ορισμό για κάθε rad < 40 και dy < rad.)
;
; ΤΡΕΙΣ ΛΙΣΤΕΣ, ΜΙΑ ΑΝΑ ΕΙΔΟΣ (λίμνες, ράχες, λεκάνη): το gt_anc κρατά το
; μέγιστο βάρος κάθε είδους σε καταχωρητή χωρίς να ρωτά το είδος. Εγγραφή,
; 8 bytes: ulo, πλάτος, ax + 64, dy, rad >> 1 (μόνο οι ράχες), wofs. Το ax
; είναι ως ±35, οπότε το ax + 64 πέφτει πάντα μέσα στον χάρτη και το πλάτος
; είναι τουλάχιστον 1. Και η ΕΝΩΣΗ των πλατών (gan_u0, gan_uw): ό,τι tile
; είναι έξω από όλες βγαίνει από το gt_anc με τρεις εντολές.
; Αν δεν μένει καμία, τα gtGa / gtNa γίνονται nop και το gt_ore μηδέν.
; ---------------------------------------------------------------------------
gp_active:
        ld      a,act_lake & 255
        ld      (gpa_pw),a
        ld      a,act_ridge & 255
        ld      (gpa_pw+1),a
        ld      a,act_basin & 255
        ld      (gpa_pw+2),a
        ld      a,128
        ld      (gpa_u0),a              ; η ένωση: από...
        xor     a
        ld      (gpa_u1),a              ; ...ως πριν από
        ld      ix,anchors
        ld      b,GEN_ANCHORS
gpa_lp:
        ld      a,(gp_y)
        sub     (ix+1)                  ; y - ay
        jp      p,gpa_abs
        neg
gpa_abs:
        cp      (ix+3)                  ; dy < rad;
        jp      nc,gpa_skip
        ld      d,a                     ; D = dy
        srl     a
        cpl
        add     a,(ix+3)                ; A2 = rad - (dy>>1) - 1
        cp      d
        jr      z,gpa_t1
        jr      nc,gpa_t                ; A2 > dy: t = A2
gpa_t1: ld      a,(ix+3)                ; t = min(dy, 2(rad - dy) - 1)
        sub     d
        add     a,a
        dec     a
        cp      d
        jr      c,gpa_t
        ld      a,d
gpa_t:  ld      e,a                     ; E = t
        push    bc
        ld      a,(ix+0)
        add     a,64
        ld      c,a                     ; C = ax + 64
        sub     e
        jr      nc,gpa_lo
        xor     a
gpa_lo: ld      b,a                     ; B = ulo = max(0, ax + 64 - t)
        ld      a,c
        add     a,e
        cp      128
        jr      c,gpa_hi
        ld      a,127                   ; uhi = min(127, ax + 64 + t)
gpa_hi: inc     a                       ; uhi + 1
        ld      e,a
        ld      a,(gpa_u1)              ; η ένωση
        cp      e
        jr      nc,gpa_u1k
        ld      a,e
        ld      (gpa_u1),a
gpa_u1k:
        ld      a,(gpa_u0)
        cp      b
        jr      c,gpa_u0k
        ld      a,b
        ld      (gpa_u0),a
gpa_u0k:
        ld      a,e
        sub     b                       ; πλάτος
        ld      e,a
        ; η λίστα του είδους: gpa_pw + είδος -> το επόμενο ελεύθερο
        ld      a,(ix+2)
        add     a,gpa_pw & 255
        ld      l,a
        ld      h,gpa_pw >> 8
        push    hl
        ld      l,(hl)
        ld      h,act_list >> 8
        ld      (hl),b                  ; +0 ulo
        inc     l
        ld      (hl),e                  ; +1 πλάτος
        inc     l
        ld      (hl),c                  ; +2 ax + 64
        inc     l
        ld      (hl),d                  ; +3 dy
        inc     l
        ld      a,(ix+3)
        srl     a
        ld      (hl),a                  ; +4 rad >> 1
        inc     l
        ld      a,(ix+4)                ; το wofs (wg_wtab, στη θέση του scale)
        ld      (hl),a                  ; +5
        inc     l
        inc     l
        inc     l
        ld      a,l
        pop     hl
        ld      (hl),a
        pop     bc
gpa_skip:
        ld      de,5
        add     ix,de
        dec     b
        jp      nz,gpa_lp
        ; τα τέλη των τριών λιστών, μέσα στις συγκρίσεις του gt_anc
        ld      hl,(gpa_pw)
        ld      a,l
        ld      (gle+1),a
        ld      a,h
        ld      (gke+1),a
        ld      a,(gpa_pw+2)
        ld      (gbe+1),a
        ; η ένωση: u0 και πλάτος. Αν είναι άδεια (u0 = 128), καμία άγκυρα.
        ld      a,(gpa_u0)
        ld      (gan_u0+1),a
        ld      b,a
        ld      a,(gpa_u1)
        sub     b
        ld      (gan_uw+1),a
        ; τα σώματα των tiles: call gt_anc, ή τρία nop και καμία φλέβα
        ld      hl,gt_anc
        ld      c,#CD                   ; call
        ld      a,b
        cp      128
        jr      c,gpa_set
        xor     a
        ld      (gt_ore),a
        ld      h,a
        ld      l,a
        ld      c,a
gpa_set:
        ld      a,c
        ld      (gtGa),a
        ld      (gtNa),a
        ld      (gtGa+1),hl
        ld      (gtNa+1),hl
        ret

; ---------------------------------------------------------------------------
; wg_wtab — για κάθε άγκυρα, w[d] = min(255, (rad - d) * scale) για d < rad,
; διαδοχικά στο wtab, και το wofs (το χαμηλό byte της αρχής) στη θέση του
; scale, που δεν το χρειάζεται τίποτε άλλο. Μία φορά ανά κόσμο, με το gen_mul.
; Τα rad είναι ως 27, 27, 29, 29, 15 και 35 (gen_spec: lo + mask): 162 bytes,
; και το tests/test_worldgen.py ελέγχει ότι χωρούν δίπλα στο act_list.
; ---------------------------------------------------------------------------
wg_wtab:
        ld      ix,anchors
        ld      hl,wtab
        ld      b,GEN_ANCHORS
gw_lp:
        ld      c,(ix+4)                ; scale
        ld      (ix+4),l                ; wofs
        ld      d,(ix+3)                ; k = rad - d, από το rad ως το 1
gw_d:
        push    bc
        push    de
        push    hl
        ld      e,c
        call    gen_mul                 ; HL = k * scale
        ld      a,h
        or      a
        ld      a,l
        jr      z,gw_ok
        ld      a,255
gw_ok:  pop     hl
        pop     de
        pop     bc
        ld      (hl),a
        inc     l
        dec     d
        jr      nz,gw_d
        ld      de,5
        add     ix,de
        djnz    gw_lp
        ret

; ---------------------------------------------------------------------------
; gt_anc — οι άγκυρες ενός tile. In: B = e, C = u. Out: B = e μετά την άγκυρα
; που κερδίζει (λίμνη > ράχη > λεκάνη), (gt_ore). Κρατά C, DE.
; Τα μέγιστα βάρη στους καταχωρητές: D λίμνη, E ράχη, IYH λεκάνη, IYL η φλέβα.
; Ο πίνακας βάρους διαβάζεται με (ix+0): IXH = η σελίδα του, IXL = wofs + d.
; ---------------------------------------------------------------------------
gt_anc:
        ld      a,c
gan_u0: sub     0                       ; έξω από την ένωση: τίποτα
gan_uw: cp      0
        jp      nc,gan_none
        push    de
        ld      de,0
        ld      iy,0
        ld      ixh,wtab >> 8
        ld      hl,act_lake
; --- οι λίμνες: μέγιστο στο D ---
gl_top: ld      a,l
gle:    cp      0                       ; το τέλος της λίστας (gp_active)
        jr      z,gl_done
        ld      a,c
        sub     (hl)                    ; u - ulo
        inc     l
        cp      (hl)                    ; < πλάτος;
        jr      nc,gl_nx
        inc     l
        ld      a,c
        sub     (hl)                    ; u - (ax + 64)
        jr      nc,gl_px
        neg
gl_px:  inc     l                       ; -> dy
        cp      (hl)
        jr      c,gl_le
        jr      z,gl_le
        ld      ixl,a                   ; dx > dy: d = dx + (dy >> 1)
        ld      a,(hl)
        srl     a
        add     a,ixl
        jr      gl_d
gl_le:  srl     a                       ; αλλιώς: d = dy + (dx >> 1)
        add     a,(hl)
gl_d:   inc     l
        inc     l                       ; -> wofs
        add     a,(hl)
        ld      ixl,a
        ld      a,(ix+0)                ; w
        cp      d
        jr      c,gl_nx
        ld      d,a
gl_nx:  ld      a,l
        and     #F8
        add     a,8
        ld      l,a
        jr      gl_top
gl_done:
; --- οι ράχες: μέγιστο στο E, και η φλέβα στο IYL ---
        ld      l,act_ridge & 255
gk_top: ld      a,l
gke:    cp      0
        jr      z,gk_done
        ld      a,c
        sub     (hl)
        inc     l
        cp      (hl)
        jr      nc,gk_nx
        inc     l
        ld      a,c
        sub     (hl)
        jr      nc,gk_px
        neg
gk_px:  inc     l
        cp      (hl)
        jr      c,gk_le
        jr      z,gk_le
        ld      ixl,a
        ld      a,(hl)
        srl     a
        add     a,ixl
        jr      gk_d
gk_le:  srl     a
        add     a,(hl)
gk_d:   inc     l                       ; -> rad >> 1
        cp      (hl)
        jr      nc,gk_w
        ld      iyl,1                   ; d < rad/2: φλέβα
gk_w:   inc     l                       ; -> wofs
        add     a,(hl)
        ld      ixl,a
        ld      a,(ix+0)
        cp      e
        jr      c,gk_nx
        ld      e,a
gk_nx:  ld      a,l
        and     #F8
        add     a,8
        ld      l,a
        jr      gk_top
gk_done:
; --- η λεκάνη: μέγιστο στο IYH ---
        ld      l,act_basin & 255
gb_top: ld      a,l
gbe:    cp      0
        jr      z,gb_done
        ld      a,c
        sub     (hl)
        inc     l
        cp      (hl)
        jr      nc,gb_nx
        inc     l
        ld      a,c
        sub     (hl)
        jr      nc,gb_px
        neg
gb_px:  inc     l
        cp      (hl)
        jr      c,gb_le
        jr      z,gb_le
        ld      ixl,a
        ld      a,(hl)
        srl     a
        add     a,ixl
        jr      gb_d
gb_le:  srl     a
        add     a,(hl)
gb_d:   inc     l
        inc     l
        add     a,(hl)
        ld      ixl,a
        ld      a,(ix+0)
        cp      iyh
        jr      c,gb_nx
        ld      iyh,a
gb_nx:  ld      a,l
        and     #F8
        add     a,8
        ld      l,a
        jr      gb_top
gb_done:
; --- η εφαρμογή ---
        ld      a,d
        or      a
        jr      nz,gap_lake
        ld      a,e
        or      a
        jr      nz,gap_ridge
        ld      a,iyh
        or      a
        jr      z,gap_done
        ld      e,a                     ; λεκάνη: στόχος MID, προσημασμένο
        ld      a,b
        sub     GEN_MID
        jr      z,gap_done
        jr      c,gap_bup
        call    mul8                    ; e > MID: e - ceil((e - MID) * w / 256)
        ld      de,255
        add     hl,de
        ld      a,b
        sub     h
        ld      b,a
        jr      gap_done
gap_bup:
        neg                             ; e < MID: e + ((MID - e) * w >> 8)
        call    mul8
        ld      a,b
        add     a,h
        ld      b,a
        jr      gap_done
gap_lake:
        ld      e,a                     ; στόχος 0: e - (e * w >> 8)
        ld      a,b
        call    mul8
        ld      a,b
        sub     h
        ld      b,a
        ld      iyl,0                   ; η λίμνη σβήνει τη φλέβα
        jr      gap_done
gap_ridge:
        ld      e,a                     ; στόχος 255: e + ((255 - e) * w >> 8)
        ld      a,b
        cpl
        call    mul8
        ld      a,b
        add     a,h
        ld      b,a
gap_done:
        ld      a,iyl
        ld      (gt_ore),a
        pop     de
        ret
gan_none:
        xor     a
        ld      (gt_ore),a
        ret

; mul8 — HL = A * E, ξετυλιγμένο (ως 56 us· το gen_mul με βρόχο ~115). Χαλάει D.
mul8:
        ld      h,a
        ld      l,0
        ld      d,l
        repeat  8
        add     hl,hl
        jr      nc,@n
        add     hl,de
@n:
        rend
        ret

; ---------------------------------------------------------------------------
; gen_despeckle — ένα πέρασμα: tile που διαφέρει και από τους τέσσερις γείτονες
; παίρνει την κλάση του βόρειου. In-place, σταθερή σειρά σάρωσης — εξαρτάται
; από τη σειρά, αλλά είναι ΝΤΕΤΕΡΜΙΝΙΣΤΙΚΟ, που είναι το μόνο που μετράει.
; ---------------------------------------------------------------------------
gen_despeckle:
        ; ΒΗΜΑ 112: τρεις δείκτες που προχωρούν μαζί — βορράς (DE), το tile
        ; (HL), νότος (BC) — και η σύγκριση κλάσης με `xor (hl) / and 7`, χωρίς
        ; την κλάση σε καταχωρητή. Τα περισσότερα tiles έχουν την κλάση του
        ; βόρειου και τελειώνουν στον πρώτο έλεγχο. Ως τότε 40 us το tile.
        ld      hl,GEN_PLANE + 128 + 1  ; (1, 1)
        ld      de,GEN_PLANE + 1        ; ο βόρειος
        ld      bc,GEN_PLANE + 256 + 1  ; ο νότιος
        ld      a,126
gd_row:
        ld      (gd_v),a
        ld      a,126
        ld      ixl,a
gd_col:
        ld      a,(de)
        xor     (hl)
        and     7
        jr      z,gd_next               ; ίδια με τον βόρειο
        ld      a,(bc)
        xor     (hl)
        and     7
        jr      z,gd_next
        dec     l                       ; u 1..126: το L δεν περνά σελίδα
        ld      a,(hl)
        inc     l
        xor     (hl)
        and     7
        jr      z,gd_next
        inc     l
        ld      a,(hl)
        dec     l
        xor     (hl)
        and     7
        jr      z,gd_next
        ld      a,(de)                  ; μοναχικό: η κλάση του βόρειου
        xor     (hl)
        and     7
        xor     (hl)
        ld      (hl),a
gd_next:
        inc     hl
        inc     de
        inc     bc
        dec     ixl
        jr      nz,gd_col
        inc     hl                      ; το u 127 και το u 0 της επόμενης
        inc     hl
        inc     de
        inc     de
        inc     bc
        inc     bc
        ld      a,(gd_v)
        dec     a
        jr      nz,gd_row
        ret

; ---------------------------------------------------------------------------
; gen_landing — ό,τι κι αν είπε ο θόρυβος, το κέντρο είναι επίπεδο και χτίσιμο.
;
; ΕΔΑΦΟΣ, ΟΧΙ ΘΕΜΕΛΙΟ (βήμα 94). Ως τότε ήταν θεμέλιο, και οι πρώτοι θόλοι, που
; χτίζονται δίπλα στο σκάφος, κάθονταν σε μια γκρίζα πλάκα 9x9 — ο παίκτης:
; «δεν χρειάζεται να σχεδιάζεις βάσεις για τους θόλους». Το έδαφος χτίζεται
; όπως το θεμέλιο (bd_ok), και το decor του θορύβου μένει, για τις τέσσερις
; παραλλαγές του αντί για το σκάκι των δύο του θεμελίου.
; ---------------------------------------------------------------------------
gen_landing:
        ld      c,-4                ; y
gl_row:
        ld      b,-4                ; x
gl_col:
        push    bc
        ; δείκτης = GEN_PLANE + (y+64)*128 + (x+64)
        ld      a,c
        add     a,64
        srl     a
        ld      h,a
        ld      a,0
        rra
        ld      l,a
        ld      a,b
        add     a,64
        or      l
        ld      l,a
        ld      a,h
        add     a,GEN_PLANE/256
        ld      h,a
        ; byte = GROUND, με το decor που είχε
        ld      a,(hl)
        and     #C0
        ld      (hl),a
        pop     bc
        inc     b
        ld      a,b
        cp      5
        jr      nz,gl_col
        inc     c
        ld      a,c
        cp      5
        jr      nz,gl_row
        ret

; --- μεταβλητές ------------------------------------------------------------
gen_seed:   dw 0
gen_planet: db 0
gen_rng:    dw 0
thr_W2:     db 0
thr_W1:     db 0
thr_M1:     db 0
thr_M2:     db 0
thr_F:      db 0
thr_OT:     db 0
ga_dir:     db 0
ga_rad:     db 0
ga_neg:     db 0
gr_v:       db 0
ga_k:       db 0
gp_v:       db 0
gp_y:       db 0
gp_wptr:    dw 0
gp_ay:      db 0                ; |y| της γραμμής
gt_ore:     db 0                ; η φλέβα του tile (gt_anc)
gpa_pw:     ds 3                ; gp_active: η επόμενη θέση σε κάθε λίστα
gpa_u0:     db 0                ; και η ένωση των πλατών
gpa_u1:     db 0
gd_v:       db 0
anchors:    defs GEN_ANCHORS*5      ; ax, ay, kind, rad, scale
gen_lat:    defs GEN_COARSE + 1  ; και το lat[0] στο τέλος (gen_row)
        align 256
gen_P:      defs 256         ; ΠΡΕΠΕΙ σε σελίδα — το gen_hash το θεωρεί
coarse_e:   defs 256
coarse_m:   defs 256
        align 256
erow:       defs 128
mrow:       defs 128
; Η ΣΕΛΙΔΑ ΕΡΓΑΣΙΑΣ (βήμα 112): οι ενεργές άγκυρες της γραμμής και οι πίνακες
; βάρους, στο GEN_WORK (src/const.asm), έξω από το αρχείο: δεν φορτώνεται
; τίποτα εκεί, τη γράφει το wg_plane.
act_list    equ GEN_WORK
act_lake    equ act_list            ; ως τρεις: δύο λίμνες και η «άγρια»
act_ridge   equ act_list + 24       ; ως τρεις
act_basin   equ act_list + 48       ; μία
wtab        equ act_list + 56
        assert  (GEN_WORK & 255) == 0
        assert  (erow & 255) == 0 && mrow == erow + 128        ; gp_epass, gt_cls
        assert  (act_list & 255) == 0 && (gpa_pw >> 8) == ((gpa_pw + 2) >> 8)   ; gl_nx, gp_active
