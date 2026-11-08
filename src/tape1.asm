; ---------------------------------------------------------------------------
; tape1.asm — η κορδέλα του εργοταξίου (βήμα 202, DESIGN §6.9): ΣΤΟ OV_R1, και
; τρέχει εκεί, με τη βασική τράπεζα 1 στο παράθυρο. Οι είσοδοί της στην
; τράπεζα 0 (src/tape0.asm) την ανοίγουν και ξαναβάζουν την 6.
;
; Ο παίκτης: «να φαίνεται περίγραμμα εκεί που θα ζωγραφιστεί αυτό που ζήτησα
; να χτίσω». Οσο ένα κτίριο είναι εργοτάξιο (DS_BUILDING), από την τοποθέτηση
; ως να τελειώσει ο μηχανικός, γύρω από το αποτύπωμά του ένα ΠΛΑΙΣΙΟ όπως το
; πράσινο της τοποθέτησης (src/ghost.asm, gh_box): οριζόντιες πλευρές δύο
; γραμμών, κάθετες ενός byte, μέσα στο πλαίσιο. ΚΙΤΡΙΝΟ, όπως το σήμα του
; εργοταξίου, ΔΙΑΚΕΚΟΜΜΕΝΟ, να διαβάζεται ως σχέδιο, και ΠΑΝΩ στο κτίριο, σαν
; κορδέλα: φαίνεται ολόκληρο και όσο το κτίριο υψώνεται από κάτω (src/rise0.asm).
;
; ΟΙ ΠΑΥΛΕΣ ΚΕΝΤΡΑΡΙΣΜΕΝΕΣ ΣΤΑ ΟΡΙΑ ΤΩΝ TILES. Οριζόντια ανά δύο bytes (4
; pixels), με το byte x του πλαισίου αναμμένο όταν x mod 4 είναι 0 ή 3·
; κάθετα ανά οκτώ γραμμές, με τη γραμμή y αναμμένη όταν (y + 4) mod 16 < 8. Ενα
; πλαίσιο έχει πλάτος πολλαπλάσιο του 4 και ύψος του 16 (ένα tile, 4 x 16), άρα
; και οι τέσσερις γωνίες έχουν μισή παύλα από κάθε πλευρά. Τα x και y είναι από
; την αρχή του πλαισίου, όχι της οθόνης: η κορδέλα μένει ίδια όπου κι αν
; σκρολάρει η κάμερα, και ένα κομμάτι της που ξαναζωγραφίζεται κομμένο (clip)
; βγαίνει ίδιο με το ολόκληρο.
; ---------------------------------------------------------------------------
TK_PEN      equ #3C                     ; το pen 6, κίτρινο, στα δύο pixels του byte
TK_LINES    equ 2                       ; οι γραμμές μιας οριζόντιας πλευράς, όπως το GH_EDGE

; tk_dome — ο θόλος του d_rec: το πλαίσιό του (d_fx, d_fy), 2 QW bytes x 2 QH
; γραμμές, όπως το ob_vis.
tk_dome:
        ld      hl,(d_qw)               ; L = QW, H = QH
        add     hl,hl                   ; 2 QW, 2 QH: QW < 128
        ld      (tk_w),hl               ; tk_w, tk_h
        ld      hl,(d_fy)
        ld      (tk_y),hl
        ld      hl,(d_fx)
        jr      tk_draw

; tk_struct — η δομή του s_rec: το πλαίσιο του σχεδίου της, κέντρο μείον το
; μισό, όπως το ob_struct. ΟΧΙ από τα ob_x, ob_y, ob_w, ob_h που άφησε εκείνο:
; το st_mark βάζει εκεί το σήμα, και όταν το εργοτάξιο υψώνεται τρέχει δύο
; φορές (src/rise0.asm, ob_fallm).
tk_struct:
        ld      a,(s_rec+ST_KIND)
        add     a,a
        add     a,a
        ld      hl,s_rec+ST_SIZE
        add     a,(hl)
        add     a,a
        ld      hl,G_struct_dims
        call    ob_addu
        ld      e,(hl)
        inc     hl
        ld      d,(hl)
        ld      (tk_w),de               ; tk_w, tk_h
        ld      a,(s_rec+ST_CY)
        call    ob_sy
        ld      a,(tk_h)
        srl     a
        call    ob_subu
        ld      (tk_y),hl
        ld      a,(s_rec+ST_CX)
        call    ob_sx
        ld      a,(tk_w)
        srl     a
        call    ob_subu
        ; fall through, HL = x

; tk_draw — HL = x (16 bit, σε bytes), (tk_y), (tk_w), (tk_h): οι τέσσερις
; πλευρές, κομμένες στο clip. Οι κάθετες περνούν και από τις γραμμές των
; οριζόντιων: δεν σώζεται τίποτα από κάτω, όπως στο gh_box.
tk_draw:
        ld      (tk_x),hl
        ld      hl,(tk_y)
        call    tk_row                  ; πάνω
        ld      hl,(tk_y)
        ld      a,(tk_h)
        sub     TK_LINES
        call    ob_addu
        call    tk_row                  ; κάτω
        ld      hl,(tk_x)
        call    tk_col                  ; αριστερά
        ld      hl,(tk_x)
        ld      a,(tk_w)
        dec     a
        call    ob_addu
        ; fall through: δεξιά

; tk_col — η κάθετη πλευρά, ένα byte στο x = HL, όλο το ύψος του πλαισίου.
;
; ΑΝΑ ΤΕΣΣΕΡΙΣ ΓΡΑΜΜΕΣ. Το πλαίσιο αρχίζει πάντα σε γραμμή πολλαπλάσια του 4
; (θόλος σε όριο tile, δομή σε μισό tile), οι παύλες αλλάζουν στο (y + 4) mod 8
; = 0, και μια σειρά χαρακτήρων έχει 8 γραμμές: τέσσερις γραμμές από γραμμή
; πολλαπλάσια του 4 έχουν την ίδια παύλα και είναι στην ίδια σειρά
; χαρακτήρων, με τα bits 3 και 4 του H να τις διαλέγουν. Οταν το clip κόβει
; ανάμεσα (η θέση δακτυλίου που αδειάζει, η δομή που υψώνεται), γραμμή γραμμή.
; 8 us τη γραμμή αντί για 20 στην πλήρη σχεδίαση.
tk_col:
        ld      a,1
        ld      de,(clip_x0)
        call    ob_clip
        ret     z
        ld      a,(cl_start)
        ld      (tk_cx),a
        ld      hl,(tk_y)
        ld      a,(tk_h)
        ld      de,(clip_y0)
        call    ob_clip
        ret     z
        ld      a,(tk_cx)
        ld      c,a
        ld      a,(cl_start)
        call    scr_addr                ; DE· κρατά το BC
        ld      hl,tk_y
        ld      a,(cl_start)
        sub     (hl)                    ; η πρώτη γραμμή από την αρχή του πλαισίου
        add     a,4
        ld      c,a                     ; αναμμένη όσο το bit 3 είναι 0
        ex      de,hl                   ; HL = η οθόνη
        ld      a,(cl_n)
        ld      b,a
        or      c
        and     3
        jr      nz,tkc_one              ; όχι σε τετράδες
        srl     b
        srl     b
tkc_four:
        bit     3,c
        ld      a,h
        jr      nz,tkc_dark
        ld      (hl),TK_PEN             ; οι γραμμές 0-3 ή 4-7 της σειράς
        set     3,h
        ld      (hl),TK_PEN
        set     4,h
        res     3,h
        ld      (hl),TK_PEN
        set     3,h
        ld      (hl),TK_PEN
        ld      a,h
        add     a,8
        jr      tkc_next
tkc_dark:
        add     a,32
tkc_next:
        ld      h,a
        call    c,tk_nlw                ; η επόμενη σειρά χαρακτήρων
        ld      a,c
        add     a,4
        ld      c,a
        djnz    tkc_four
        ret
tkc_one:
        bit     3,c
        jr      nz,tkc_off
        ld      (hl),TK_PEN
tkc_off:
        inc     c
        ld      a,h
        add     a,8
        ld      h,a
        call    c,tk_nlw
        djnz    tkc_one
        ret
; tk_nlw — το scr_nlw (src/screen.asm) για το HL.
tk_nlw:
        ex      de,hl
        call    scr_nlw
        ex      de,hl
        ret

; tk_row — η οριζόντια πλευρά, TK_LINES γραμμές από το y = HL, όλο το πλάτος.
tk_row:
        ld      a,TK_LINES
        ld      de,(clip_y0)
        call    ob_clip
        ret     z
        ld      hl,(cl_n)               ; L = γραμμές, H = η πρώτη
        ld      (tk_rn),hl              ; tk_rn, tk_ry
        ld      hl,(tk_x)
        ld      a,(tk_w)
        ld      de,(clip_x0)
        call    ob_clip
        ret     z
        ; το μοτίβο από το πρώτο byte που φαίνεται: %10011001, ένα bit ανά byte
        ; του πλαισίου, γυρισμένο κατά (x mod 4)
        ld      hl,tk_x
        ld      a,(cl_start)
        sub     (hl)
        and     3
        ld      b,a
        inc     b
        ld      a,%10011001
        jr      tkr_r
tkr_rot:
        rrca
tkr_r:
        djnz    tkr_rot
        ld      (tk_pat),a
tkr_line:
        ld      a,(cl_start)
        ld      c,a
        ld      a,(tk_ry)
        call    scr_addr                ; DE
        ld      a,(tk_pat)
        ld      c,a
        ld      a,(cl_n)
        ld      b,a
tkr_lp:
        rrc     c
        jr      nc,tkr_off
        ld      a,TK_PEN
        ld      (de),a
tkr_off:
        inc     e
        call    z,gh_wrap               ; src/ghost.asm: μέσα στο δαχτυλίδι των 2 KB
        djnz    tkr_lp
        ld      hl,tk_ry
        inc     (hl)
        dec     hl                      ; tk_rn
        dec     (hl)
        jr      nz,tkr_line
        ret

tk_x:       dw 0                        ; το πλαίσιο, σε bytes και γραμμές οθόνης
tk_y:       dw 0
tk_w:       db 0                        ; tk_w, tk_h διπλανά
tk_h:       db 0
tk_cx:      db 0                        ; το x μιας κάθετης πλευράς στην οθόνη
tk_rn:      db 0                        ; tk_rn, tk_ry διπλανά: όσες γραμμές μένουν, η επόμενη
tk_ry:      db 0
tk_pat:     db 0
        assert  tk_h == tk_w + 1 && tk_ry == tk_rn + 1 && d_qh == d_qw + 1
        assert  cl_start == cl_n + 1 && TK_LINES == GH_EDGE
