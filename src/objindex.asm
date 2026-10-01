; objindex.asm — το ΧΤΙΣΙΜΟ του ευρετηρίου αντικειμένων (DESIGN §8.4).
;
; ΣΤΗΝ ΤΡΑΠΕΖΑ 2, ΟΧΙ ΣΤΗΝ 0 (βήμα 41). Τρέχει μόνο όταν αλλάζει η αποικία —
; μια τοποθέτηση, μια φόρτωση, μια πλήρης σχεδίαση — ποτέ σε καρέ που
; σκρολάρει, και είναι ο μεγαλύτερος ψυχρός κώδικας του περάσματος
; αντικειμένων. Το πέρασμα (oi_walk), το παράθυρο και τα άγκιστρα μένουν
; στο object.asm, στην τράπεζα 0· τα άγκιστρα κάνουν JP εδώ όταν το ob_meas
; λέει «μέτρα». Ο χώρος ήρθε από το αρχείο του φαντάσματος, που ως το βήμα 40
; είχε 440 bytes που δεν χρησιμοποίησε ποτέ τίποτα (src/const.asm, GH_LOG).
;
; Η τράπεζα 2 φαίνεται πάντα (#8000-#BFFF), οπότε ο κώδικας εδώ σελιδοποιεί
; ελεύθερα το παράθυρο #4000 — την 5 για να γράψει το ευρετήριο, την 6 για
; τους πίνακες — όπως και πριν.

; ---------------------------------------------------------------------------
; oi_build — το ευρετήριο αντικειμένων στην τράπεζα 5, πάνω από το NEXTHOP.
;
; ΜΕ ΤΗΝ ΚΑΜΕΡΑ ΣΤΟ (0, 0), όπου η οθόνη ΕΙΝΑΙ ο κόσμος: οι ίδιες ρουτίνες
; που ζωγραφίζουν δίνουν τις θέσεις, και το ob_meas τις κάνει να τις ΜΕΤΡΑΝΕ
; αντί να ζωγραφίζουν. Ενας θόλος είναι το πλαίσιό του (ob_vis) — σε αυτό
; κόβονται κέλυφος και εξαρτήματα μαζί. Ενας διάδρομος είναι η ένωση των
; τρεξιμάτων του (oc_run), μια δομή το sprite της (ob_struct). Οι δομές
; μπαίνουν ταξινομημένες κατά cy, όπως τις ζωγράφιζε το ob_struct_all σε
; κάθε κλήση· η ταξινόμηση γίνεται τώρα μία φορά ανά αλλαγή.
; ---------------------------------------------------------------------------
;
; ΜΟΝΟ Η ΚΑΤΗΓΟΡΙΑ ΠΟΥ ΑΛΛΑΞΕ. Ως να μπει αυτό, κάθε τοποθέτηση ξανάχτιζε
; ολόκληρο το ευρετήριο, και η πρώτη σειρά ενός εργοταξίου — που δεν περνά
; καν από το ob_draw_all — πλήρωνε 56 ms για διαδρόμους που δεν άλλαξαν.
oi_build:
        ld      hl,(cam_tx)
        push    hl
        ld      hl,0
        ld      (cam_tx),hl
        inc     l
        ld      a,l
        ld      (ob_meas),a
        ld      hl,oi_mask
        srl     (hl)                    ; ήδη: το bit των φιγούρων
        srl     (hl)
        jr      nc,oib_c
        ld      hl,OI_DOME
        ld      (oi_ptr),hl
        ld      hl,oi_nd
        ld      de,ob_shell
        ld      b,MAX_DOME
        call    oi_pass
oib_c:
        ld      hl,oi_mask
        srl     (hl)
        jr      nc,oib_s
        ld      hl,OI_CORR
        ld      (oi_ptr),hl
        ld      hl,oi_nc
        ld      de,ob_corr
        ld      b,MAX_CORR
        call    oi_pass
oib_s:
        ld      hl,oi_mask
        srl     (hl)
        jr      nc,oib_end
        ld      hl,OI_STRUCT
        ld      (oi_ptr),hl
        call    ob_struct_sort
        ld      hl,oi_ns
        ld      de,ob_struct
        ld      a,(st_n)
        ld      b,a
        ld      a,1                     ; τα id από το st_ord
        call    oi_pass_a
oib_end:
        xor     a
        ld      (ob_meas),a
        pop     hl
        ld      (cam_tx),hl
        ret

; oi_pass — B εγγραφές, id 0..B-1· oi_pass_a με A = 1: τα id από το st_ord.
; HL = ο μετρητής (oi_nd/nc/ns), DE = η ρουτίνα σε τρόπο μέτρησης.
oi_pass:
        xor     a
oi_pass_a:
        ld      (oi_tab),a
        ld      (hl),0
        ld      (oi_cnt),hl
        ld      (oiw_fn),de
        ld      a,b
        or      a
        ret     z
        ld      c,0
oip_lp:
        push    bc
        ld      a,(oi_tab)
        or      a
        ld      a,c
        jr      z,oip_id
        ld      hl,st_ord
        ld      b,0
        add     hl,bc
        ld      a,(hl)
oip_id:
        ld      (oi_e + 4),a
        ld      hl,#00FF                ; άδειο: x0 = 255, x1 = 0
        ld      (oi_e),hl
        ld      (oi_e + 2),hl
        call    oiw_go
        ld      a,(oi_e + 1)
        or      a
        jr      z,oip_nx                ; τίποτα δεν θα ζωγραφιζόταν
        ld      hl,(oi_cnt)
        inc     (hl)
        ld      bc,GA_PORT + PAGE_B5
        out     (c),c
        ld      hl,oi_e
        ld      de,(oi_ptr)
        ld      bc,OI_REC
        ldir
        ld      (oi_ptr),de
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
oip_nx:
        pop     bc
        inc     c
        djnz    oip_lp
        ret

; oi_gx8 / oi_gy8 — HL = αρχή, A = μήκος (byte). oi_gx / oi_gy — DE = μήκος.
; Το περίγραμμα (oi_e) μεγαλώνει ως τα tiles που αγγίζει το [αρχή, αρχή+μήκος).
oi_gx8:
        ld      e,a
        ld      d,0
oi_gx:
        push    hl
        add     hl,de
        inc     hl
        inc     hl
        inc     hl
        call    oi_t4                   ; το τέλος, προς τα πάνω
        ld      c,a
        pop     hl
        call    oi_t4
        ld      hl,oi_e
        jr      oi_grow
oi_gy8:
        ld      e,a
        ld      d,0
oi_gy:
        push    hl
        add     hl,de
        ld      bc,15
        add     hl,bc
        call    oi_t16
        ld      c,a
        pop     hl
        call    oi_t16
        ld      hl,oi_e + 2
oi_grow:                                ; A = αρχή, C = τέλος, HL -> (lo, hi)
        cp      (hl)
        jr      nc,oig_hi
        ld      (hl),a
oig_hi:
        inc     hl
        ld      a,(hl)
        cp      c
        ret     nc
        ld      (hl),c
        ret

; oi_t16 / oi_t4 — HL προσημασμένο (bytes ή γραμμές) -> A = tile + 128.
oi_t16:
        sra     h
        rr      l
        sra     h
        rr      l
oi_t4:
        sra     h
        rr      l
        sra     h
        rr      l
        ld      a,l
        xor     #80
        ret

; --- τα άγκιστρα του object.asm, σε τρόπο μέτρησης ---
; ov_meas — το πλαίσιο στο περίγραμμα του ευρετηρίου (oi_build), και «δεν
; φαίνεται»: τίποτα δεν ζωγραφίζεται.
ov_meas:
        ld      hl,(d_fx)
        ld      a,(d_qw)
        add     a,a
        call    oi_gx8
        ld      hl,(d_fy)
        ld      a,(d_qh)
        add     a,a
        call    oi_gy8
        xor     a
        ret


; oc_meas — το oc_run όταν χτίζεται το ευρετήριο: το κουτί του τρεξίματος
; στο περίγραμμα, τίποτα στην οθόνη.
oc_meas:
        ld      a,(oc_dx)
        ld      c,a
        ld      hl,(ob_x)
        ld      a,(ob_w)
        call    ob_box
        call    oi_gx
        ld      a,(oc_dy)
        ld      c,a
        ld      hl,(ob_y)
        ld      a,(ob_h)
        call    ob_box
        jp      oi_gy


os_meas:
        ld      hl,(ob_x)
        ld      a,(ob_w)
        call    oi_gx8
        ld      hl,(ob_y)
        ld      a,(ob_h)
        jp      oi_gy8

oi_ptr:     dw 0
oi_cnt:     dw 0
oi_tab:     db 0
oi_e:       defs OI_REC         ; η εγγραφή που μετριέται: x0, x1, y0, y1, id
