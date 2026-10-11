; span.asm — τα διαστήματα των θόλων και των δακτυλίων (βήμα 108, DESIGN §8.4).
;
; ΕΝΑ ΖΕΥΓΟΣ (#FF, 0) ΔΕΝ ΑΛΛΑΖΕΙ ΤΙΠΟΤΑ, και το blit του κοστίζει 18 us, 32
; καθρεφτισμένο. Στα τεταρτημόρια των θόλων είναι τα δύο πέμπτα των ζευγών:
; έξω από τον κύκλο, και όλες οι οκτώ πρώτες γραμμές. Στους δακτυλίους τα τρία
; τέταρτα: και το εσωτερικό τους, που ο θόλος καλύπτει. Μετρημένο στην
; αποικία του objtest: από τα 5.888 καθρεφτισμένα bytes μιας πλήρους σχεδίασης
; τα 3.362 ήταν τέτοια, 107 ms από τα 642.
;
; Κάθε γραμμή κάθε τεταρτημορίου έχει ΕΝΑ διάστημα με κάτι, και ό,τι είναι έξω
; του δεν αλλάζει την οθόνη. Ο πίνακας (build/span_tables.asm, από το
; tools/pack.py, που τρέχει σε κάθε build) δίνει για κάθε ΟΚΤΩ γραμμές πηγής
; το (a << 4) | n: από ποιο ζεύγος, όπως στο nw, και πόσα. Ανά οκτώ και όχι
; ανά γραμμή: 36 bytes αντί για 288, και στο μοντέλο του βήματος 108 οι
; ομάδες των τεσσάρων γλίτωναν 10 ms σε μια πλήρη σχεδίαση και πλήρωναν άλλα
; τόσα σε ομάδες.
;
; Ο βρόχος του ob_blit (src/object.asm) τρέχει σε ΚΟΜΜΑΤΙΑ: όσες γραμμές
; έχει η ομάδα, ή όσες μένουν. Ανάμεσά τους, εδώ: το obl_n (πόσα), το obl_k (ο
; πυρήνας, ή ret όταν η ομάδα δεν έχει τίποτα), το obl_p (η πηγή, μετακινημένη
; όσο μετακινήθηκε το διάστημα) και το DE, από το scr_addr.

; ---------------------------------------------------------------------------
; sp_first — HL = ο πίνακας, από το ob_bspan· γυρίζει στο ob_line.
; Η πρώτη γραμμή πηγής είναι το ob_st (από πάνω) ή h - 1 - ob_st (ανάποδα), και
; η ομάδα της έχει όσες γραμμές μένουν ως το όριο των οκτώ προς τα εκεί που πάει.
; ---------------------------------------------------------------------------
sp_first:
        ld      (spg_t+1),hl
        ld      hl,(obl_k+1)
        ld      (spg_k+1),hl            ; ο πυρήνας, για μετά από άδεια ομάδα
        ld      hl,0
        ld      (spg_off),hl            ; το obl_p δεν έχει μετακινηθεί ακόμη
        ld      a,(ob_y0)
        ld      hl,ob_nl
        add     a,(hl)
        ld      (spg_y+1),a             ; το y μετά την τελευταία γραμμή
        ld      a,(ob_fl)
        and     2
        ld      a,(ob_st)
        ld      b,1                     ; προς τα κάτω
        jr      z,spf_dn
        cpl
        ld      hl,ob_h
        add     a,(hl)                  ; h - 1 - st
        ld      b,-1
spf_dn:
        ld      c,a                     ; η πρώτη γραμμή πηγής
        ld      a,b
        ld      (spn_d+1),a
        ld      a,c
        and     SPAN_G - 1
        inc     b                       ; Z: προς τα πάνω
        jr      z,spf_up
        cpl
        add     a,SPAN_G + 1            ; κάτω: 8 - m
        jr      spf_k
spf_up:
        inc     a                       ; πάνω: m + 1
spf_k:
        ld      b,a
        ld      a,c
        rrca
        rrca
        rrca
        and     31                      ; η ομάδα
        call    sp_grp
        jp      ob_line

; ---------------------------------------------------------------------------
; sp_next — από το ob_line, όταν τελειώνει ένα κομμάτι και μένουν γραμμές.
; sp_grp — A = η ομάδα, B = πόσες γραμμές της μένουν.
; ---------------------------------------------------------------------------
sp_next:
        ld      b,SPAN_G
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
        ld      a,(spn_g+1)
spg_t:  ld      hl,0
        add     a,l
        ld      l,a                     ; ο πίνακας δεν περνά όριο σελίδας
        ld      a,(hl)
        ld      c,a
        and     15
        jr      z,spg_none
        ld      b,a                     ; n
        xor     c
        rrca
        rrca
        rrca
        rrca
        ld      c,a                     ; a, η πρώτη στήλη όπως στο nw
        ld      a,(ob_fl)
        rra
        jr      nc,spg_nf
        ld      a,(ob_w)                ; καθρεφτισμένο: οι στήλες w-a-n .. w-a
        sub     c
        sub     b
        ld      c,a
spg_nf:
        ld      a,c
        add     a,b
        ld      b,a                     ; [C, B): οι στήλες με κάτι
        ld      hl,(cl_skip)            ; L = πόσες κόπηκαν, H = πόσες φαίνονται
        ld      a,l
        add     a,h
        cp      b
        jr      nc,spg_hi
        ld      b,a                     ; ως το τέλος του clip
spg_hi:
        ld      a,c
        cp      l
        jr      nc,spg_lo
        ld      a,l                     ; από την αρχή του clip
spg_lo:
        ld      c,a
        sub     l
        ld      e,a                     ; πόσες στήλες μετά την αρχή του clip
        ld      a,b
        sub     c
        jr      c,spg_none
        jr      z,spg_none
        ld      (obl_n+1),a
spg_k:  ld      hl,0
        ld      (obl_k+1),hl
        ld      l,e
        ld      h,0
        add     hl,hl                   ; δύο bytes το ζεύγος
        ld      a,(ob_fl)
        rra
        jr      nc,spg_o
        xor     a                       ; καθρεφτισμένο: η πηγή πάει ανάποδα
        sub     l
        ld      l,a
        sbc     a,a
        ld      h,a
spg_o:
        ld      a,(cl_start)
        add     a,e
        ld      c,a                     ; το x
        ld      de,(spg_off)
        ld      (spg_off),hl
        or      a
        sbc     hl,de                   ; πόσο μετακινήθηκε το διάστημα
        ld      de,(obl_p+1)
        add     hl,de
        ld      (obl_p+1),hl
spg_yy: ld      a,0
        jp      scr_addr                ; DE: η οθόνη, από την αρχή του διαστήματος
spg_none:
        ld      hl,spg_ret              ; τίποτα: οι γραμμές του κομματιού δεν γράφουν
        ld      (obl_k+1),hl
spg_ret:
        ret

spg_off:    dw 0                ; πόσο απέχει το obl_p από την αρχή του clip

; ---------------------------------------------------------------------------
; Οι πίνακες: ανά μέγεθος ο δακτύλιος και αμέσως μετά ο θόλος. Το ob_shell
; βρίσκει τον δακτύλιο από το sp_ring και τον θόλο QH / 8 bytes μετά.
; ---------------------------------------------------------------------------
sp_ring:
        db      spt_s & 255, spt_m & 255, spt_l & 255
        include "../build/span_tables.asm"
sp_end:
        assert  sp_ring >> 8 == (sp_end - 1) >> 8
