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
        ld      (gr_dst),de
        ld      (gr_src),hl
        ld      a,(gr_v)
        and     7
        ld      (gr_fv),a
        ld      a,(gr_v)
        rrca
        rrca
        rrca
        and     #1F                 ; cv = v>>3  (0..15)
        ; top = src + cv*16
        add     a,a
        add     a,a
        add     a,a
        add     a,a
        ld      e,a
        ld      d,0
        ld      hl,(gr_src)
        add     hl,de
        ld      (gr_top),hl
        ; bot = src + ((cv+1)&15)*16
        ld      a,(gr_v)
        rrca
        rrca
        rrca
        and     #1F
        inc     a
        and     15
        add     a,a
        add     a,a
        add     a,a
        add     a,a
        ld      e,a
        ld      d,0
        ld      hl,(gr_src)
        add     hl,de
        ld      (gr_bot),hl
        ; lat[j] = top[j] + (((bot[j]-top[j]) * fv) >> 3)
        ld      b,GEN_COARSE
        ld      ix,gen_lat
gr_lat:
        push    bc
        ld      hl,(gr_top)
        ld      c,(hl)              ; a = top[j]
        inc     hl
        ld      (gr_top),hl
        ld      hl,(gr_bot)
        ld      a,(hl)              ; b = bot[j]
        inc     hl
        ld      (gr_bot),hl
        ; DE = b - a σε ΠΛΗΡΗ 16 bits. Με 8-bit sub και επέκταση προσήμου το
        ; 195 διαβαζόταν ως -61: η διαφορά δύο bytes ζει στο -255..255 και ΔΕΝ
        ; χωράει σε προσημασμένο byte.
        ld      l,a
        ld      h,0
        ld      e,c
        ld      d,0
        or      a
        sbc     hl,de
        ex      de,hl               ; DE = b - a
        ld      hl,0
        ld      a,(gr_fv)
        or      a
        jr      z,gr_nofv
gr_mul:
        add     hl,de
        dec     a
        jr      nz,gr_mul
gr_nofv:
        sra     h
        rr      l
        sra     h
        rr      l
        sra     h
        rr      l                   ; >> 3, αριθμητικά
        ld      a,l
        add     a,c
        ld      (ix+0),a
        inc     ix
        pop     bc
        djnz    gr_lat
        ; ράμπα: 16 κελιά x 8 tiles
        ld      de,(gr_dst)
        ld      ix,gen_lat
        ld      a,GEN_COARSE
        ld      (gr_c),a
gr_cell:
        ld      a,(ix+0)            ; a = lat[c]
        ld      (gr_a),a
        ld      a,(gr_c)
        cp      1
        jr      nz,gr_next_in
        ld      a,(gen_lat)         ; τυλίγει στο lat[0]
        jr      gr_have_b
gr_next_in:
        ld      a,(ix+1)
gr_have_b:
        push    de                  ; ο προορισμός
        ld      l,a                 ; b
        ld      h,0
        ld      a,(gr_a)
        ld      e,a
        ld      d,0
        or      a
        sbc     hl,de               ; HL = b - a, πλήρη 16 bits
        add     hl,hl
        add     hl,hl
        add     hl,hl
        add     hl,hl
        add     hl,hl               ; << 5
        ld      b,h
        ld      c,l                 ; BC = βήμα του συσσωρευτή
        pop     de
        ld      a,(gr_a)
        ld      h,a
        ld      l,0                 ; acc = a << 8
        repeat  8
        ld      a,h
        ld      (de),a
        inc     de
        add     hl,bc
        rend
        inc     ix
        ld      a,(gr_c)
        dec     a
        ld      (gr_c),a
        jr      nz,gr_cell
        ret


; ---------------------------------------------------------------------------
; wg_plane — το κύριο πέρασμα. Μία γραμμή τη φορά: τα δύο πεδία, οι ενεργές
; άγκυρες, μετά 128 tiles.
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

wg_beatn:   db 32

wg_plane:
        xor     a
        ld      (gp_v),a
        ld      hl,GEN_PLANE
        ld      (gp_wptr),hl
gpl_row:
        ld      a,(gp_v)
        call    wg_prog                 ; η μπάρα του §5.9, μία κίνηση ανά σειρά
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
        ld      a,(gp_v)
        sub     64
        ld      (gp_y),a
        ld      a,(gp_v)
        srl     a
        ld      (gp_v1),a
        srl     a
        ld      (gp_v2),a
        call    gp_active
        xor     a
        ld      (gp_u),a
gpl_col:
        ; Ο χτύπος της μουσικής (§9.5): ένα τικ ανά 32 πλακίδια, δηλαδή περίπου
        ; κάθε 17 ms — αρκετά σταθερό για ρυθμό, και ο διαιρέτης είναι εδώ ώστε
        ; ο βρόχος να πληρώνει έναν dec και όχι μια κλήση.
        ld      hl,wg_beatn
        dec     (hl)
        jr      nz,gpl_nb
        ld      (hl),32
        call    wg_beat
gpl_nb:
        ld      a,(gp_u)
        sub     64
        ld      (gp_x),a
        call    gen_tile
        ld      hl,(gp_wptr)
        inc     hl
        ld      (gp_wptr),hl
        ld      a,(gp_u)
        inc     a
        ld      (gp_u),a
        cp      128
        jr      nz,gpl_col
        ld      a,(gp_v)
        inc     a
        ld      (gp_v),a
        cp      128
        jr      nz,gpl_row
        ret

; gp_active — ποιες άγκυρες αγγίζουν αυτή τη γραμμή. Σχεδόν πάντα καμία, οπότε
; ο βρόχος των tiles δεν πληρώνει τίποτα για τις υπόλοιπες.
gp_active:
        ld      ix,anchors
        ld      iy,act_list
        ld      b,GEN_ANCHORS
        xor     a
        ld      (act_n),a
gpa_lp:
        ld      a,(gp_y)
        sub     (ix+1)
        jp      p,gpa_abs
        neg
gpa_abs:
        cp      (ix+3)
        jr      z,gpa_take
        jr      nc,gpa_skip
gpa_take:
        ld      a,(ix+0)
        ld      (iy+0),a
        ld      a,(ix+1)
        ld      (iy+1),a
        ld      a,(ix+2)
        ld      (iy+2),a
        ld      a,(ix+3)
        ld      (iy+3),a
        ld      a,(ix+4)
        ld      (iy+4),a
        ld      de,5
        add     iy,de
        ld      a,(act_n)
        inc     a
        ld      (act_n),a
gpa_skip:
        ld      de,5
        add     ix,de
        djnz    gpa_lp
        ret

; ---------------------------------------------------------------------------
; gen_tile — ένα tile: ύψος, άγκυρες, σχήμα, ταξινόμηση, εγγραφή.
; ---------------------------------------------------------------------------
gen_tile:
        ; --- e = erow[u] + (H(u>>2,v>>2)>>3) + (H(u>>1,v>>1)>>4) ---
        ld      a,(gp_v2)
        ld      c,a
        ld      a,(gp_u)
        srl     a
        srl     a
        call    gen_hash
        srl     a
        srl     a
        srl     a
        ld      (gt_o),a
        ld      a,(gp_v1)
        ld      c,a
        ld      a,(gp_u)
        srl     a
        call    gen_hash
        srl     a
        srl     a
        srl     a
        srl     a
        ld      b,a
        ld      a,(gt_o)
        add     a,b
        ld      b,a                 ; B = οι δύο οκτάβες
        ld      a,(gp_u)
        ld      l,a
        ld      h,erow/256
        ld      a,(hl)
        add     a,b
        ld      l,a
        ld      a,0
        adc     a,0
        ld      h,a                 ; HL = άθροισμα, έως 301
        ld      de,23               ; η μέση τιμή των δύο οκταβών
        or      a
        sbc     hl,de
        bit     7,h
        jr      nz,gt_zero
        ld      a,h
        or      a
        jr      z,gt_ehave
        ld      a,255
        jr      gt_estore
gt_zero:
        xor     a
        jr      gt_estore
gt_ehave:
        ld      a,l
gt_estore:
        ld      (gt_e),a

        ; --- άγκυρες: ΑΝΑΜΕΙΞΗ με βάρος, προτεραιότητα λίμνη > ράχη > λεκάνη ---
        ; Το βάρος πάει στο 255 στο κέντρο (η εγγύηση κρατάει) και σβήνει στο 0
        ; στην άκρη (την άκρη τη γράφει ο θόρυβος). Με σκέτο ταβάνι/πάτωμα οι
        ; λίμνες έβγαιναν κυριολεκτικά τετράγωνες.
        xor     a
        ld      (gt_lakew),a
        ld      (gt_ridgew),a
        ld      (gt_basinw),a
        ld      (gt_ore),a
        ld      a,(act_n)
        or      a
        jp      z,gt_shape
        ld      b,a
        ld      ix,act_list
gt_anch:
        push    bc
        ld      a,(gp_x)
        sub     (ix+0)
        jp      p,gt_dx
        neg
gt_dx:
        ld      c,a                 ; dx
        ld      a,(gp_y)
        sub     (ix+1)
        jp      p,gt_dy
        neg
gt_dy:
        ; οκταγωνική απόσταση: max + min/2. Η Chebyshev έδινε τετράγωνα.
        cp      c
        jr      nc,gt_oct
        ld      b,a                 ; dy είναι το μικρό
        ld      a,c                 ; dx είναι το μεγάλο
        jr      gt_oct2
gt_oct:
        ld      b,c
gt_oct2:
        srl     b
        add     a,b
        ld      (gt_d),a
        cp      (ix+3)
        jp      nc,gt_anext         ; d >= rad -> εκτός
        ; w = min(255, (rad - d) * scale)
        ld      a,(ix+3)
        ld      c,a
        ld      a,(gt_d)
        neg
        add     a,c
        ld      d,a                 ; rad - d
        ld      e,(ix+4)            ; scale
        push    ix
        call    gen_mul
        pop     ix
        ld      a,h
        or      a
        ld      a,l
        jr      z,gt_w_ok
        ld      a,255
gt_w_ok:
        ld      c,a                 ; C = w
        ld      a,(ix+2)
        or      a
        jr      z,gt_lake
        dec     a
        jr      z,gt_ridge
        ld      a,(gt_basinw)
        cp      c
        jp      nc,gt_anext
        ld      a,c
        ld      (gt_basinw),a
        jp      gt_anext
gt_lake:
        ld      a,(gt_lakew)
        cp      c
        jp      nc,gt_anext
        ld      a,c
        ld      (gt_lakew),a
        jp      gt_anext
gt_ridge:
        ld      a,(gt_ridgew)
        cp      c
        jr      nc,gt_r_ore
        ld      a,c
        ld      (gt_ridgew),a
gt_r_ore:
        ld      a,(ix+3)
        srl     a
        ld      c,a
        ld      a,(gt_d)
        cp      c
        jp      nc,gt_anext
        ld      a,1
        ld      (gt_ore),a
gt_anext:
        ld      de,5
        add     ix,de
        pop     bc
        dec     b                   ; ο βρόχος ξεπέρασε το djnz
        jp      nz,gt_anch

        ; --- εφαρμογή με προτεραιότητα ---
        ld      a,(gt_lakew)
        or      a
        jr      z,gt_ap_ridge
        ; στόχος 0:  e -= (e * w) >> 8
        ld      a,(gt_e)
        ld      e,a
        ld      a,(gt_lakew)
        ld      d,a
        call    gen_mul
        ld      a,(gt_e)
        sub     h
        ld      (gt_e),a
        xor     a
        ld      (gt_ore),a
        jp      gt_shape
gt_ap_ridge:
        ld      a,(gt_ridgew)
        or      a
        jr      z,gt_ap_basin
        ; στόχος 255:  e += ((255-e) * w) >> 8
        ld      a,(gt_e)
        cpl                         ; 255 - e
        ld      e,a
        ld      a,(gt_ridgew)
        ld      d,a
        call    gen_mul
        ld      a,(gt_e)
        add     a,h
        ld      (gt_e),a
        jp      gt_shape
gt_ap_basin:
        ld      a,(gt_basinw)
        or      a
        jp      z,gt_shape
        ld      a,(gt_e)
        cp      GEN_MID
        jp      z,gt_shape
        jr      c,gt_bas_up
        ; e > MID. Η Python κάνει (αρνητικό)>>8, που στρογγυλεύει ΚΑΤΩ:
        ; e + ((MID-e)*w >> 8)  ==  e - ((p+255) >> 8)
        sub     GEN_MID
        ld      e,a
        ld      a,(gt_basinw)
        ld      d,a
        call    gen_mul
        ld      de,255
        add     hl,de
        ld      a,(gt_e)
        sub     h
        ld      (gt_e),a
        jp      gt_shape
gt_bas_up:
        ld      a,GEN_MID
        ld      c,a
        ld      a,(gt_e)
        neg
        add     a,c                 ; MID - e
        ld      e,a
        ld      a,(gt_basinw)
        ld      d,a
        call    gen_mul
        ld      a,(gt_e)
        add     a,h
        ld      (gt_e),a

        ; --- πλατό κέντρου και ορεινό χείλος ---
gt_shape:
        ld      a,(gp_x)
        bit     7,a
        jr      z,gt_ax
        neg
gt_ax:
        ld      c,a
        ld      a,(gp_y)
        bit     7,a
        jr      z,gt_ay
        neg
gt_ay:
        cp      c
        jr      nc,gt_rmax
        ld      a,c
gt_rmax:
        ld      (gt_r),a
        cp      R_PLATEAU+1
        jr      nc,gt_blend
        ld      a,GEN_MID
        ld      (gt_e),a
        jr      gt_rim
gt_blend:
        ld      a,(gt_r)
        cp      R_BLEND+1
        jr      nc,gt_rim
        ; e = MID + ((e - MID) * w) >> 8
        sub     R_PLATEAU
        ld      l,a
        ld      h,0
        ld      de,gen_blend
        add     hl,de
        ld      a,(hl)
        ld      (gt_w),a
        ld      a,(gt_e)
        sub     GEN_MID
        ld      l,a
        add     a,a
        sbc     a,a
        ld      h,a                 ; HL = προσημασμένο (e - MID)
        ld      d,h
        ld      e,l
        ld      hl,0
        ld      a,(gt_w)
        or      a
        jr      z,gt_bl_done
gt_bl_mul:
        add     hl,de
        dec     a
        jr      nz,gt_bl_mul
gt_bl_done:
        ld      a,h                 ; >> 8 αριθμητικά = το ψηλό byte
        add     a,GEN_MID
        ld      (gt_e),a
gt_rim:
        ld      a,(gt_r)
        cp      R_RIM
        jr      c,gt_class
        sub     R_RIM
        ld      l,a
        ld      h,0
        ld      de,gen_rim
        add     hl,de
        ld      a,(gt_e)
        add     a,(hl)
        jr      nc,gt_rim_ok
        ld      a,255
gt_rim_ok:
        ld      (gt_e),a

        ; --- ταξινόμηση ---
gt_class:
        ld      a,(gt_e)
        ld      c,a
        ld      a,(thr_W2)
        ld      b,a
        ld      a,c
        cp      b
        jr      c,gt_deep
        ld      a,(thr_W1)
        ld      b,a
        ld      a,c
        cp      b
        jr      c,gt_water
        ld      a,(thr_M2)
        ld      b,a
        ld      a,b
        cp      c
        jr      c,gt_mount          ; e > M2
        ld      a,(thr_M1)
        ld      b,a
        ld      a,b
        cp      c
        jr      c,gt_rock           ; e > M1
        ; υγρασία: ground αν m > F, αλλιώς dust
        ld      a,(gp_u)
        add     a,128               ; το mrow είναι στην ΙΔΙΑ σελίδα με το erow,
        ld      l,a                 ; οπότε δείκτης u σκέτος διάβαζε το ΥΨΟΣ
        ld      h,erow/256
        ld      a,(hl)
        ld      c,a
        ld      a,(thr_F)
        cp      c
        jr      c,gt_ground
        ld      a,1                 ; DUST
        ld      b,0
        jr      gt_write
gt_ground:
        xor     a                   ; GROUND
        ld      b,1                 ; γόνιμο
        jr      gt_write
gt_rock:
        ld      a,2
        ld      b,0
        jr      gt_write
gt_water:
        ld      a,4
        ld      b,0
        jr      gt_write
gt_deep:
        ld      a,5
        ld      b,0
        jr      gt_write
gt_mount:
        ld      b,0
        ld      a,(gt_ore)
        or      a
        jr      z,gt_m_done
        ld      a,(gp_v)
        ld      c,a
        ld      a,(gp_u)
        add     a,GEN_OSALT
        call    gen_hash
        ld      c,a
        ld      a,(thr_OT)
        cp      c
        jr      nc,gt_m_done
        ld      b,1
gt_m_done:
        ld      a,3                 ; MOUNTAIN
gt_write:
        ; A = κλάση, B = πόρος. decor = H(u, v+7) & 3
        ld      c,a
        push    bc
        ld      a,(gp_v)
        add     a,7
        ld      c,a
        ld      a,(gp_u)
        call    gen_hash
        and     3
        rrca
        rrca                        ; στα bits 6-7
        ld      e,a
        pop     bc
        ld      a,b
        add     a,a
        add     a,a
        add     a,a                 ; πόρος στο bit 3
        or      c
        or      e
        ld      hl,(gp_wptr)
        ld      (hl),a
        ret

; ---------------------------------------------------------------------------
; gen_despeckle — ένα πέρασμα: tile που διαφέρει και από τους τέσσερις γείτονες
; παίρνει την κλάση του βόρειου. In-place, σταθερή σειρά σάρωσης — εξαρτάται
; από τη σειρά, αλλά είναι ΝΤΕΤΕΡΜΙΝΙΣΤΙΚΟ, που είναι το μόνο που μετράει.
; ---------------------------------------------------------------------------
gen_despeckle:
        ld      a,1
        ld      (gd_v),a
gd_row:
        ld      a,1
        ld      (gd_u),a
        ld      a,(gd_v)
        ld      h,0
        ld      l,a
        add     hl,hl
        add     hl,hl
        add     hl,hl
        add     hl,hl
        add     hl,hl
        add     hl,hl
        add     hl,hl               ; v*128
        ld      de,GEN_PLANE+1
        add     hl,de
gd_col:
        push    hl
        ld      a,(hl)
        and     7
        ld      c,a                 ; c
        ld      de,-128
        add     hl,de
        ld      a,(hl)
        and     7
        ld      b,a                 ; n
        cp      c
        jr      z,gd_next
        ld      de,256
        add     hl,de               ; -> νότος
        ld      a,(hl)
        and     7
        cp      c
        jr      z,gd_next
        ld      de,-128-1
        add     hl,de               ; -> δύση
        ld      a,(hl)
        and     7
        cp      c
        jr      z,gd_next
        inc     hl
        inc     hl                  ; -> ανατολή
        ld      a,(hl)
        and     7
        cp      c
        jr      z,gd_next
        ; μοναχικό — πάρε την κλάση του βόρειου
        pop     hl
        push    hl
        ld      a,(hl)
        and     #F8
        or      b
        ld      (hl),a
gd_next:
        pop     hl
        inc     hl
        ld      a,(gd_u)
        inc     a
        ld      (gd_u),a
        cp      127
        jr      nz,gd_col
        ld      a,(gd_v)
        inc     a
        ld      (gd_v),a
        cp      127
        jr      nz,gd_row
        ret

; ---------------------------------------------------------------------------
; gen_landing — ό,τι κι αν είπε ο θόρυβος, το κέντρο είναι επίπεδο και χτίσιμο.
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
        ; byte = FOUNDATION | decor((x+y)&1)
        ld      a,b
        add     a,c
        and     1
        rrca
        rrca                        ; στα bits 6-7
        or      7                   ; FOUNDATION
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
gr_fv:      db 0
gr_c:       db 0
gr_a:       db 0
gr_dst:     dw 0
gr_src:     dw 0
gr_top:     dw 0
gr_bot:     dw 0
ga_k:       db 0
gp_u:       db 0
gp_v:       db 0
gp_x:       db 0
gp_y:       db 0
gp_v1:      db 0
gp_v2:      db 0
gp_wptr:    dw 0
act_n:      db 0
act_list:   defs GEN_ANCHORS*5
gt_o:       db 0
gt_e:       db 0
gt_r:       db 0
gt_w:       db 0
gt_ore:     db 0
gt_d:       db 0
gt_lakew:   db 0
gt_ridgew:  db 0
gt_basinw:  db 0
gd_u:       db 0
gd_v:       db 0
anchors:    defs GEN_ANCHORS*5      ; ax, ay, kind, rad, scale
gen_lat:    defs GEN_COARSE
        align 256
gen_P:      defs 256         ; ΠΡΕΠΕΙ σε σελίδα — το gen_hash το θεωρεί
coarse_e:   defs 256
coarse_m:   defs 256
        align 256
erow:       defs 128
mrow:       defs 128
