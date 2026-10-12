; span.asm — τα κελύφη των θόλων και των δακτυλίων, ως διαστήματα (βήματα 108
; και 110, DESIGN §8.4).
;
; ΕΝΑ ΖΕΥΓΟΣ (#FF, 0) ΔΕΝ ΑΛΛΑΖΕΙ ΤΙΠΟΤΑ, και το blit του κοστίζει 18 us, 32
; καθρεφτισμένο. Στα τεταρτημόρια των θόλων είναι τα δύο πέμπτα των ζευγών:
; έξω από τον κύκλο, και όλες οι οκτώ πρώτες γραμμές. Στους δακτυλίους τα τρία
; τέταρτα: και το εσωτερικό τους, που ο θόλος καλύπτει. Μετρημένο στην
; αποικία του objtest: από τα 5.888 καθρεφτισμένα bytes μιας πλήρους σχεδίασης
; τα 3.362 ήταν τέτοια, 107 ms από τα 642.
;
; Κάθε γραμμή κάθε τεταρτημορίου έχει ΕΝΑ διάστημα με κάτι, και ό,τι είναι έξω
; του δεν αλλάζει την οθόνη. Ανά ΟΚΤΩ γραμμές πηγής (μία ομάδα) το (a << 4) | n:
; από ποιο ζεύγος, όπως στο nw, και πόσα.
;
; ΑΠΟ ΤΟ ΒΗΜΑ 110 ΤΑ ΚΕΛΥΦΗ ΕΙΝΑΙ ΜΟΝΟ ΑΥΤΟ (tools/pack.py, shell): μια
; κεφαλίδα — τα διαστήματα των ομάδων στο +0, οι διευθύνσεις τους στο +8 — και
; κάθε ομάδα οκτώ γραμμές των 2n bytes. 7.424 bytes -> 3.840 στην τράπεζα 6, που
; τα δίνει στον κώδικα του τροχού. Ως το 109 ο πίνακας ήταν εδώ, στην τράπεζα 0,
; και τα τεταρτημόρια ολόκληρα: η πηγή μετακινούνταν μόνο όσο το διάστημα.
;
; Ο βρόχος του ob_blit (src/object.asm) τρέχει σε ΚΟΜΜΑΤΙΑ: όσες γραμμές έχει η
; ομάδα, ή όσες μένουν. Για κάθε κομμάτι, εδώ: το obl_n (πόσα), το obl_k (ο
; πυρήνας, ή ret όταν η ομάδα δεν έχει τίποτα), το obl_p (η πηγή: η ομάδα, η
; γραμμή της, η στήλη), το obl_s (±2n) και το DE, από το scr_addr. Το ob_bspan
; έρχεται εδώ αμέσως μετά το κόψιμο: τίποτα από όσα στήνει για τα άλλα sprites
; δεν ισχύει για κέλυφος.

        include "../build/span_tables.asm"      ; SPAN_G, SHELL_HDR (tools/pack.py)
        assert  SPAN_G == 8 && SHELL_HDR == 3 * SPAN_G

; ---------------------------------------------------------------------------
; sp_first — HL = το κέλυφος (ob_spt), από το ob_bspan· γυρίζει στο ob_line.
; Η πρώτη γραμμή πηγής είναι το ob_st (από πάνω) ή h - 1 - ob_st (ανάποδα), και
; η ομάδα της έχει όσες γραμμές μένουν ως το όριο των οκτώ προς τα εκεί που πάει.
; ---------------------------------------------------------------------------
sp_first:
        ld      (spg_t+1),hl
        ld      a,(ob_fl)
        rra
        ld      hl,blt_mask_flip        ; ο πυρήνας, και μετά από άδεια ομάδα
        ld      de,spg_fl               ; και ο δρόμος των στηλών: ΜΙΑ φορά ανά
        jr      c,spf_k                 ; blit, όχι δύο ανά ομάδα
        ld      hl,blt_mask_line
        ld      de,spg_nf
spf_k:
        ld      (spg_k+1),hl
        ld      (spg_fx+1),de
        ld      a,(ob_y0)
        ld      hl,ob_nl
        add     a,(hl)
        ld      (spg_y+1),a             ; το y μετά την τελευταία γραμμή
        ld      a,(ob_fl)
        and     2
        ld      a,(ob_st)
        ld      bc,#0100                ; κάτω: +1, κάθε επόμενη ομάδα από τη γραμμή 0
        jr      z,spf_dn
        cpl
        ld      hl,ob_h
        add     a,(hl)                  ; h - 1 - st
        ld      bc,#FF00 + SPAN_G - 1   ; πάνω: -1, από τη γραμμή 7
spf_dn:
        ld      e,a                     ; η πρώτη γραμμή πηγής
        ld      a,b
        ld      (spn_d+1),a
        ld      a,c
        ld      (spn_j+1),a
        ld      a,b
        rla                             ; CY: πάνω
        sbc     a,a
        cpl
        and     spg_pos - spg_sg - 2    ; κάτω: πάνω από το neg· πάνω: 0
        ld      (spg_sg+1),a
        ld      a,e
        and     SPAN_G - 1
        ld      (spg_j+1),a             ; η γραμμή της μέσα στην ομάδα
        inc     b                       ; Z: προς τα πάνω
        jr      z,spf_up
        cpl
        add     a,SPAN_G + 1            ; κάτω: 8 - m
        jr      spf_go
spf_up:
        inc     a                       ; πάνω: m + 1
spf_go:
        ld      b,a
        ld      a,e
        rrca
        rrca
        rrca
        and     31                      ; η ομάδα
        call    sp_grp
        jp      ob_line

; ---------------------------------------------------------------------------
; sp_next — από το ob_line, όταν τελειώνει ένα κομμάτι και μένουν γραμμές.
; sp_grp — A = η ομάδα, B = πόσες γραμμές της μένουν, η πρώτη τους στο spg_j.
; ---------------------------------------------------------------------------
sp_next:
        ld      b,SPAN_G
spn_j:  ld      a,0                     ; 0 κάτω, 7 πάνω
        ld      (spg_j+1),a
spn_g:  ld      a,0
spn_d:  add     a,0                     ; ±1
sp_grp:
        ld      (spn_g+1),a
        ld      hl,ob_nl
        ld      a,b
        cp      (hl)
        jr      c,spg_kk
        ld      a,(hl)                  ; ή όσες μένουν στο blit
spg_kk:
        ld      (obl_c),a
        ld      b,a
        ld      a,(hl)
        ld      c,a
        sub     b
        ld      (hl),a                  ; όσες μένουν μετά το κομμάτι
spg_y:  ld      a,0
        sub     c
        ld      (spg_yy+1),a            ; το y της πρώτης γραμμής του
        ; --- η κεφαλίδα: το διάστημα στο +g, η διεύθυνση στο +8+2g ---
        ld      a,(spn_g+1)
        ld      e,a
spg_t:  ld      hl,0
        add     a,l
        ld      l,a                     ; μία σελίδα (pack.py, page)
        ld      a,(hl)
        ld      c,a
        and     15
        jp      z,spg_none
        ld      b,a                     ; n
        ld      a,l
        add     a,e
        add     a,SPAN_G
        ld      l,a
        ld      a,(hl)
        inc     l
        ld      h,(hl)
        ld      l,a
        ld      (spg_da+1),hl           ; οι οκτώ γραμμές της ομάδας
        ; --- το βήμα, ±2n, και η γραμμή μέσα στην ομάδα ---
        ld      a,b
        add     a,a
        ld      e,a                     ; 2n
spg_sg: jr      spg_pos                 ; το sp_first: 0 όταν πάει πάνω
        neg
        ld      l,a
        ld      h,#FF                   ; -2n
        jr      spg_sd
spg_pos:
        ld      l,a
        ld      h,0
spg_sd:
        ld      (obl_s+1),hl
spg_j:  ld      a,0                     ; η γραμμή
        or      a
        jr      z,spg_r
        cp      SPAN_G - 1
        jr      nz,spg_rm
        ld      a,b                     ; η τελευταία: 14n = 16n - 2n
        add     a,a
        add     a,a
        add     a,a
        add     a,a
        sub     e
        jr      spg_r
spg_rm:
        ld      d,a                     ; κάποια άλλη: μόνο στο πρώτο κομμάτι
        xor     a
spg_ml:
        add     a,e
        dec     d
        jr      nz,spg_ml
spg_r:
        ld      (spg_ro+1),a
        ; --- οι στήλες: [C, B) στην οθόνη, και από πού διαβάζει η πηγή ---
        ld      a,c
        xor     b
        rrca
        rrca
        rrca
        rrca
        ld      c,a                     ; a, η πρώτη στήλη όπως στο nw
spg_fx: jp      spg_nf                  ; ή spg_fl, καθρεφτισμένο (sp_first)

spg_fl:
        ld      a,(ob_w)                ; οι στήλες w-a-n .. w-a,
        sub     c
        dec     a
        ld      d,a                     ; και η πηγή από το w-1-a, ανάποδα
        sub     b
        inc     a
        ld      c,a
        add     a,b
        ld      b,a                     ; [C, B)
        ld      hl,(cl_skip)            ; L = πόσες κόπηκαν, H = πόσες φαίνονται
        ld      a,l
        add     a,h
        cp      b
        jr      nc,spf_hi
        ld      b,a                     ; ως το τέλος του clip
spf_hi:
        ld      a,c
        cp      l
        jr      nc,spf_lo
        ld      a,l                     ; από την αρχή του clip
spf_lo:
        ld      c,a                     ; s: η πρώτη που ζωγραφίζεται
        sub     l
        ld      e,a                     ; πόσες στήλες μετά την αρχή του clip
        ld      a,b
        sub     c
        jr      c,spg_none
        jr      z,spg_none
        ld      (obl_n+1),a
        ld      a,d
        sub     c                       ; w-1-a - s
        jr      spg_pt

spg_nf:
        ld      d,c                     ; η πηγή από το a
        ld      a,c
        add     a,b
        ld      b,a                     ; [C, B)
        ld      hl,(cl_skip)
        ld      a,l
        add     a,h
        cp      b
        jr      nc,spg_hi
        ld      b,a
spg_hi:
        ld      a,c
        cp      l
        jr      nc,spg_lo
        ld      a,l
spg_lo:
        ld      c,a                     ; s
        sub     l
        ld      e,a
        ld      a,b
        sub     c
        jr      c,spg_none
        jr      z,spg_none
        ld      (obl_n+1),a
        ld      a,c
        sub     d                       ; s - a
spg_pt:
        ; --- η πηγή: ομάδα + γραμμή + 2 x τη στήλη ---
spg_cc: add     a,a                     ; δύο bytes το ζεύγος
spg_ro: add     a,0                     ; + η γραμμή
        ld      l,a
        ld      h,0
spg_da: ld      bc,0
        add     hl,bc
        ld      (obl_p+1),hl
spg_k:  ld      hl,0
        ld      (obl_k+1),hl
        ld      a,(cl_start)
        add     a,e
        ld      c,a                     ; το x
spg_yy: ld      a,0
        jp      scr_addr                ; DE: η οθόνη, από την αρχή του διαστήματος
spg_none:
        ld      hl,spg_ret              ; τίποτα: οι γραμμές του κομματιού δεν γράφουν
        ld      (obl_k+1),hl
spg_ret:
        ret
