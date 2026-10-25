; st7.asm — οι δομές χωρίς μάσκα (βήμα 170, DESIGN §8.4), στην ΤΡΑΠΕΖΑ 7.
;
; ΤΑ SPRITES ΤΩΝ ΔΟΜΩΝ ΧΩΡΙΣ ΤΗ ΜΑΣΚΑ ΤΟΥΣ (tools/pack.py, struct_data). Το
; πρώτο βήμα του σχεδίου για 160 αποίκους (DESIGN §6.1). Η μάσκα κάθε κελιού
; τους ήταν ακριβώς τα pixel του με pen 0, οπότε μένει μόνο το χρώμα: ένα byte
; ανά κελί, w ανά γραμμή, και τα επτά sprites με μάσκα, 7.680 bytes, έγιναν
; 3.840. Η μάσκα βγαίνει από τον πίνακα st_mask (256 bytes, σε σελίδα), ένα
; ld a,(bc) ανά κελί.
;
; ΕΔΩ, ΚΑΙ ΟΧΙ ΣΤΗΝ ΤΡΑΠΕΖΑ 0. Τα κείμενα της τράπεζας 7 έλεγαν (src/uitext.asm)
; ότι κώδικας δεν ζει εδώ, γιατί θα έσβηνε τον εαυτό του με την πρώτη άλλη
; τράπεζα. Αυτός δεν σελιδοποιεί τίποτα: διαβάζει τα sprites και τον πίνακα της
; 7, γράφει στην οθόνη (τράπεζα 3) και καλεί το ob_clip, το ob_mul και το
; scr_addr της τράπεζας 0, που είναι πάντα εκεί. Ταξιδεύει μέσα στο TEXT.BIN,
; μετά τα κείμενα (src/uitext.asm).
;
; ΤΟ ob_struct (src/object.asm) ΑΝΟΙΓΕΙ ΤΗΝ 7 ΚΑΙ ΕΡΧΕΤΑΙ ΕΔΩ (st7_put), με το
; ob_src, ob_x, ob_y, ob_w, ob_h γραμμένα. Η πλατφόρμα, η μόνη αδιαφανής, πάει
; στο ob_put όπως πριν· οι άλλες κόβονται εδώ με τα δύο ob_clip του ob_bspan.
; Ετσι το ob_struct δεν έχει διακλάδωση για το είδος, και είναι 12 bytes
; μικρότερο.
;
; Ο ΒΡΟΧΟΣ ΕΙΝΑΙ ΤΟΥ ob_line, με σταθερό βήμα w και το clip μία μετατόπιση.
; ΑΠΟ ΤΟ ΒΗΜΑ 171 ζωγραφίζει και τους διαδρόμους (s7_clip, από το oc_run και το
; cn_post) και τις γωνίες τους, καθρεφτισμένες κάθετα βόρεια (s7_clipv).
; Ο πυρήνας είναι ΞΕΤΥΛΙΓΜΕΝΟΣ: δεκαέξι κελιά των 48 T (το blt_mask_line θέλει
; 59 με το djnz του), και μπαίνει κανείς n κελιά πριν από το τέλος του (s7_k).
; Το τύλιγμα των 2 KB το βλέπει ο έλεγχος του (H & 7) = 7 μία φορά ανά γραμμή,
; όπως στους πυρήνες του src/blit.asm, και τότε η γραμμή σπάει στα δύο (s7_wchk).

; ---------------------------------------------------------------------------
; st7_put — μία δομή, με την 7 μέσα. Από το ob_struct. Χαλάει και το IXL.
; ---------------------------------------------------------------------------
st7_put:
        ld      a,(s_rec+ST_KIND)
        cp      K_PAD
        jr      nz,s7_clip
        ld      hl,(ob_w)
        ld      a,4                     ; αδιαφανής, χωρίς μάσκα
        jp      ob_put
s7_clip:
        ; --- τα δύο clip, όπως στο ob_bspan ---
        ld      hl,(ob_y)
        ld      a,(ob_h)
        ld      de,(clip_y0)
        call    ob_clip
        ret     z
        ld      hl,(cl_skip)            ; skip, n -> ob_st, ob_nl
        ld      (ob_st),hl
        ld      a,(cl_start)
        ld      (ob_y0),a
        ld      hl,(ob_x)
        ld      a,(ob_w)
        ld      de,(clip_x0)
        call    ob_clip
        ret     z
        ; --- ο πυρήνας για cl_n κελιά: s7_cend - 8 n ---
        ld      (s7_cn),a
        add     a,a
        add     a,a
        add     a,a
        ld      c,a
        ld      a,s7_cend & 255
        sub     c
        ld      (s7_k + 1),a
        ld      a,s7_cend >> 8
        sbc     a,0
        ld      (s7_k + 2),a
        ; --- η πηγή: ob_src + st * w + skip ---
        ld      a,(ob_w)
        ld      (s7_w + 1),a            ; + w: το πάνω byte του βήματος είναι 0
        ld      c,a
        ld      a,(ob_st)
s7_row0:                                ; A = η πρώτη γραμμή της πηγής, C = w
        call    ob_mul                  ; HL = γραμμή * w
        ld      de,(ob_src)
        add     hl,de
        ld      a,(cl_skip)
        call    ob_addu
        push    hl
        ld      a,(cl_start)
        ld      c,a
        ld      a,(ob_y0)
        call    scr_addr                ; DE = η οθόνη
        pop     hl
        ld      a,(ob_nl)
        ld      ixl,a
        ld      b,G_st_mask >> 8        ; ως το τέλος: κανείς από κάτω δεν το αγγίζει
s7_row:
        push    de
        push    hl
        ex      de,hl                   ; HL = η οθόνη, DE = η πηγή
        ld      a,h
        or      #F8
        inc     a
        jr      z,s7_wchk               ; (H & 7) = 7: ίσως το τύλιγμα μέσα
s7_k:   call    0                       ; n κελιά πριν από το s7_cend
s7_ret:
        pop     hl
s7_w:   ld      de,0                    ; ± w (βήμα 171: 16 bit, 6 T λιγότερα από το add a,w)
        add     hl,de
        pop     de
        ld      a,d
        add     a,8
        ld      d,a
        call    c,scr_nlw               ; μόνο όταν τελειώνει σειρά χαρακτήρων
        dec     ixl
        jr      nz,s7_row
        ret

; s7_wchk — το τελευταίο κελί περνά το #FF; Μόνο τότε η γραμμή σπάει: k1 = 256 - L
; κελιά ως το τύλιγμα, το H πίσω κατά 8 (από το (H+1):00 στο (H-7):00), και τα
; υπόλοιπα. Το L δεν είναι 0 εδώ: 16 κελιά από το 0 δεν τυλίγουν.
s7_wchk:
        ld      a,(s7_cn)
        dec     a
        add     a,l
        jr      nc,s7_k
        inc     a
        ld      (s7_k2),a               ; όσα μένουν μετά το τύλιγμα
        xor     a
        sub     l
        call    s7_part
        ld      a,h
        sub     8
        ld      h,a
        ld      a,(s7_k2)
        call    s7_part
        jr      s7_ret

; s7_part — A κελιά (1-16) από τον πυρήνα. Κρατά τα HL, DE, B.
s7_part:
        add     a,a
        add     a,a
        add     a,a
        ld      c,a
        ld      a,s7_cend & 255
        sub     c
        ld      (s7_pj + 1),a
        ld      a,s7_cend >> 8
        sbc     a,0
        ld      (s7_pj + 2),a
s7_pj:  jp      0

; ο πυρήνας: HL = η οθόνη, DE = η πηγή, B = η σελίδα του st_mask
s7_cells:
        repeat  16
        ld      a,(de)                  ; το χρώμα
        ld      c,a
        ld      a,(bc)                  ; η μάσκα του: τα pixel με pen 0
        and     (hl)
        or      c
        ld      (hl),a
        inc     de
        inc     hl
        rend
s7_cend:
        ret

        assert  s7_cend - s7_cells == 16 * 8
        assert  (G_st_mask & 255) == 0

; ---------------------------------------------------------------------------
; s7_clipv — το ίδιο, ΚΑΘΡΕΦΤΙΣΜΕΝΟ ΚΑΘΕΤΑ, όπως το bit 1 του ob_fl στο ob_blit:
; η πρώτη γραμμή της πηγής είναι η h - 1 - st και το βήμα -w. Οι γωνίες των
; διαδρόμων βόρεια (src/corner.asm, βήμα 171). Τα δύο clip και ο πυρήνας όπως
; στο s7_clip (αντίγραφο: το s7_clip δεν πληρώνει τίποτα γι' αυτό), και στο
; τέλος πίσω το πάνω byte του βήματος, το 0 των άλλων.
; ---------------------------------------------------------------------------
s7_clipv:
        ld      hl,(ob_y)
        ld      a,(ob_h)
        ld      de,(clip_y0)
        call    ob_clip
        ret     z
        ld      hl,(cl_skip)
        ld      (ob_st),hl
        ld      a,(cl_start)
        ld      (ob_y0),a
        ld      hl,(ob_x)
        ld      a,(ob_w)
        ld      de,(clip_x0)
        call    ob_clip
        ret     z
        ld      (s7_cn),a
        add     a,a
        add     a,a
        add     a,a
        ld      c,a
        ld      a,s7_cend & 255
        sub     c
        ld      (s7_k + 1),a
        ld      a,s7_cend >> 8
        sbc     a,0
        ld      (s7_k + 2),a
        ld      a,(ob_w)
        ld      c,a
        neg
        ld      (s7_w + 1),a
        ld      a,#FF
        ld      (s7_w + 2),a            ; -w
        ld      a,(ob_st)
        ld      b,a
        ld      a,(ob_h)
        dec     a
        sub     b                       ; h - 1 - st
        call    s7_row0
        xor     a
        ld      (s7_w + 2),a
        ret

s7_cn:      db 0
s7_k2:      db 0
