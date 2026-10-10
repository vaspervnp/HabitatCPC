; ---------------------------------------------------------------------------
; bend.asm — οι κοντές στροφές (βήμα 97).
;
; Ο παίκτης, στο βήμα 96: «κλείσε και τα λευκά pixels μετά τις στροφές». Ο
; κανόνας του αρμού (src/joint.asm) είναι ότι τα pixels του εξωτερικού
; περιγράμματος του δακτυλίου που ακουμπούν το γκρι ενός διαδρόμου γίνονται
; γκρι. Οι αρμοί του 96 είναι ΣΤΑΘΕΡΑ σχέδια ανά μέγεθος και κατεύθυνση,
; υπολογισμένα για έναν διάδρομο μόνο του. Μετρημένο σε όλες τις διαδρομές ως
; 12 tiles, κάθε μέγεθος και κάθε μισό tile: μία μόνο γεωμετρία ξεφεύγει. Ο
; διάδρομος φτάνει στον θόλο ΟΡΙΖΟΝΤΙΑ με ΕΝΑ tile μετά τη στροφή, και η
; διαγώνιος του ακουμπά το περίγραμμα ένα pixel κάτω ή πάνω από τον αρμό του
; οριζόντιου. Πάντα ένα pixel, πάντα στην ίδια θέση του πλαισίου: στην πρώτη
; ή την τελευταία στήλη, στη γραμμή qh + 4 (η διαγώνιος από κάτω) ή qh - 5
; (από πάνω).
;
; Ποιοι θόλοι το έχουν το λέει το jtb_flags, ένα byte ανά θόλο: bit k = μια
; τέτοια στροφή με τη διαγώνιο στην πλευρά k (1 βα, 3 να, 5 νδ, 7 βδ).
; Γράφεται όπως το dome_conn, στη μέτρηση του ευρετηρίου των διαδρόμων
; (jt_mark -> jtb_mark), και σβήνει μαζί του (jt_clear -> jtb_clr). Τα
; σχέδια των θόλων τα κοιτάζουν μόνο όταν υπάρχει έστω μία (jtd_sw). Ενας νέος
; διάδρομος ΔΕΝ το χρειάζεται στη λίστα αλλαγών: το pixel πέφτει πάντα σε μία
; από τις δύο τελευταίες σειρές της διαγωνίου (DK_CROW, τρία tiles), που
; ξαναζωγραφίζουν ό,τι πέφτει εκεί με το ob_draw_all, και τον θόλο — μετρημένο
; σε όλες τις 2.024 κοντές στροφές ως 12 tiles (tests/test_corridor.py): 506
; στην τελευταία, 1.518 στην προτελευταία. Με τις σειρές ένα tile δεξιά, 411
; μένουν έξω.
;
; ΣΤΗΝ ΤΡΑΠΕΖΑ 5 (b5code, tools/pack.py): στην 0 και στο b6code δεν έμεναν
; ούτε τα 64 bytes των σημαιών. Τρέχει με την 5 στο παράθυρο, μέσα από το
; jt_b5 (src/object.asm), και ζωγραφίζει με το ob_put την πρώτη γραμμή του
; δυτικού ή του ανατολικού αρμού (jt_pxl, jt_pxr), που είναι ακριβώς αυτό το
; pixel. Τίποτα εδώ δεν σελιδοποιεί. Το tests/objtest.asm το έχει επίπεδο, το
; tests/uitest.asm στην τράπεζα 5, όπως το παιχνίδι.
; ---------------------------------------------------------------------------

B5C_MAX     equ 248                     ; = B5C_MAX του tools/pack.py (272 ως το βήμα 99: 24 στα σήματα των μηχανών)

        assert  C_LEN == C_DIR + 1      ; ld hl,(oc_cr + C_DIR) στο jtm_bend (src/object.asm)

jtb_flags:  defs MAX_DOME

; jtb_clr — καμία στροφή (jt_clear, όταν ξαναχτίζεται το ευρετήριο).
jtb_clr:
        ld      hl,jtb_flags
        ld      de,jtb_flags + 1
        ld      bc,MAX_DOME - 1
        ld      (hl),b
        ldir
        ret

; jtb_mark — από το jtm_bend (src/object.asm): ο διάδρομος συνεχίζει ΕΝΑ tile
; οριζόντια ως τον b, θόλο. Η σημαία του b, στην πλευρά της διαγωνίου.
jtb_mark:
        ld      a,(c_rec + C_DIR)       ; η διαγώνιος
        add     a,4
        and     7                       ; k, η πλευρά της
        ld      hl,bit_tab              ; src/entity.asm
        call    ob_addu
        ld      e,(hl)                  ; 1 << k
        ld      a,(c_rec + C_B)
        call    jtb_at
        ld      a,e
        or      (hl)
        ld      (hl),a
        ret

; jtb_at — A = θόλος: HL = η σημαία του.
jtb_at:
        ld      hl,jtb_flags
        jp      ob_addu

; jtb_dome — τα pixels των στροφών του θόλου d_id (από το jtd_end, μετά τους
; αρμούς του, όταν η αποικία έχει έστω μία κοντή στροφή: ο διακόπτης jtd_sw
; του src/object.asm). Απαιτεί το πλαίσιο (ob_getdome, ob_vis).
jtb_dome:
        ld      a,(d_id)
        ld      hl,jtb_flags            ; χωρίς το jtb_at: 10 µs σε κάθε θόλο
        add     a,l                     ; με αρμούς, όσο ο διακόπτης είναι
        ld      l,a                     ; ανοιχτός
        adc     a,h
        sub     l
        ld      h,a
        ld      a,(hl)
        or      a
        ret     z
        ld      c,0                     ; k (μόνο τα μονά)
jtbd_lp:
        srl     a                       ; ΟΧΙ rra: ένα CY της εισόδου γινόταν
        jr      nc,jtbd_nx              ; στροφή στην πλευρά 8 (βήμα 97)
        push    af
        push    bc
        ld      a,c
        call    jtb_px
        pop     bc
        pop     af
jtbd_nx:
        inc     c
        or      a
        jr      nz,jtbd_lp
        ret

; jtb_px — A = k (1, 3, 5, 7): το pixel της στροφής από εκείνη την πλευρά, στο
; πλαίσιο d_fx, d_fy (QW, QH στο d_qw, d_qh). Ανατολικά (1, 3) η τελευταία
; στήλη, το δεξί pixel· δυτικά (5, 7) η πρώτη, το αριστερό. Από κάτω (3, 5)
; η γραμμή qh + 4, από πάνω (1, 7) η qh - 5.
jtb_px:
        ld      c,a
        ld      hl,(d_qw)               ; L = QW, H = QH
        inc     a
        and     4                       ; 4: η διαγώνιος από κάτω
        ld      a,h
        jr      z,jtbp_up
        add     a,9
jtbp_up:
        sub     5
        push    hl
        ld      hl,(d_fy)
        call    ob_addu
        ld      (ob_y),hl
        pop     hl
        ld      de,jt_pxl               ; δυτικά: η στήλη 0
        xor     a
        bit     2,c
        jr      nz,jtbp_x
        ld      de,jt_pxr               ; ανατολικά: η στήλη 2 QW - 1
        ld      a,l
        add     a,a
        dec     a
jtbp_x:
        ld      hl,(d_fx)
        call    ob_addu
        ld      (ob_x),hl
        ld      (ob_src),de
        ld      hl,#0101                ; 1 byte, 1 γραμμή
        xor     a                       ; με μάσκα, χωρίς καθρέφτισμα
        jp      ob_put

; jtb_cc — ο αρμός του b του διαδρόμου που μόλις μπήκε (crr_conns, από το
; cr_redraw), στη λίστα: DK_CONN στην αντίθετη του ΤΕΛΕΥΤΑΙΟΥ τρεξίματος.
; Τίποτα για airlock: δεν έχει δακτύλιο. Εδώ και όχι στο src/ui.asm, όπου ήταν
; ως το 96: η τράπεζα 0 κερδίζει 17 bytes.
jtb_cc:
        ld      a,(cr_to)
        cp      MAX_DOME
        ret     nc
        ld      b,a
        ld      a,(cr_n)
        cp      2
        ld      a,(cr_d0)
        jr      c,jtbc_last
        ld      a,(cr_d1)
jtbc_last:
        add     a,4
        and     7
        ld      c,a
        ld      a,DK_CONN
        jp      dirty_push
