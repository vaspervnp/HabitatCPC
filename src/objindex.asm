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
; In: A = οι κατηγορίες που ξαναχτίζονται, OB_IX_* >> 1 (το ob_index έχει
; ήδη βγάλει το bit των φιγούρων). Απαιτεί τράπεζα 6.
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
; Οι κατηγορίες βγαίνουν από το A με rra, και το A περιμένει στη στοίβα όσο
; τρέχει το πέρασμα.
oi_build:
        ld      hl,(cam_tx)
        push    hl
        ld      hl,0
        ld      (cam_tx),hl
        ld      hl,ob_meas              ; 0 έξω από εδώ
        inc     (hl)
        rra
        push    af
        jr      nc,oib_c
        ld      hl,OI_DOME
        ld      de,ob_shell
        ld      b,MAX_DOME
        call    oi_pass
        ld      (oi_nd),a
oib_c:
        pop     af
        rra
        push    af
        jr      nc,oib_s
        ld      hl,OI_CORR
        ld      de,ob_corr
        ld      b,MAX_CORR
        call    oi_pass
        ld      (oi_nc),a
oib_s:
        pop     af
        rra
        jr      nc,oib_end
        call    ob_struct_sort
        ld      hl,OI_STRUCT
        ld      de,oi_st
        ld      a,(st_n)
        ld      b,a
        or      a
        call    nz,oi_pass              ; καμία δομή: A = 0
        ld      (oi_ns),a
oib_end:
        xor     a
        ld      (ob_meas),a
        pop     hl
        ld      (cam_tx),hl
        ret

; oi_pass — B > 0 εγγραφές, id 0..B-1. HL = η πρώτη εγγραφή του ευρετηρίου,
; DE = η ρουτίνα σε τρόπο μέτρησης (A = id). Out: A = πόσες γράφτηκαν· τον
; μετρητή της κατηγορίας τον γράφει αυτός που καλεί.
oi_pass:
        ld      (oi_ptr),hl
        ld      (oiw_fn),de
        xor     a
        ld      (oi_k),a
        ld      c,a
oip_lp:
        push    bc
        ld      a,c
        ld      (oi_e + 4),a
        ld      hl,#00FF                ; άδειο: x0 = 255, x1 = 0
        ld      (oi_e),hl
        ld      (oi_e + 2),hl
        call    oiw_go
        ld      a,(oi_e + 1)
        or      a
        jr      z,oip_nx                ; τίποτα δεν θα ζωγραφιζόταν
        ld      bc,GA_PORT + PAGE_B5
        out     (c),c
        ld      hl,oi_e
        ld      de,(oi_ptr)
        ld      bc,OI_REC
        ldir
        ld      (hl),e                  ; HL = oi_ptr
        inc     hl
        ld      (hl),d
        inc     hl
        inc     (hl)                    ; oi_k
        call    ob_b6
oip_nx:
        pop     bc
        inc     c
        djnz    oip_lp
        ld      a,(oi_k)
        ret

; oi_st — η ρουτίνα του περάσματος των δομών: A = θέση στο st_ord -> το id,
; και αυτό μπαίνει στην εγγραφή.
oi_st:
        ld      e,a
        ld      d,0
        ld      hl,st_ord
        add     hl,de
        ld      a,(hl)
        ld      (oi_e + 4),a
        jp      ob_struct

; oi_gx8 / oi_gy8 — HL = αρχή, A = μήκος (byte). oi_gx / oi_gy — DE = μήκος.
; Το περίγραμμα (oi_e) μεγαλώνει ως τα tiles που αγγίζει το [αρχή, αρχή+μήκος):
; από το tile της αρχής ως ΕΝΑ ΜΕΤΑ το tile του τελευταίου byte ή γραμμής,
; ⌈e/n⌉ = ⌊(e-1)/n⌋ + 1, με το ίδιο oi_t για τα δύο άκρα.
oi_gx8:
        ld      e,a
        ld      d,0
oi_gx:
        push    hl
        add     hl,de
        dec     hl
        call    oi_t4                   ; το τελευταίο byte
        inc     a                       ; ... και ένα μετά
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
        dec     hl
        call    oi_t16
        inc     a
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

; oi_t16 / oi_t4 — HL προσημασμένο (γραμμές ή bytes) -> A = tile + 128.
; Το tile είναι τα bits 4-11 ή 2-9 του HL: τέσσερα add hl,hl τα φέρνουν στο
; H, δύο rr h / rra στο A. Τα bits που μπαίνουν από πάνω δεν τα φτάνουν.
oi_t16:
        add     hl,hl
        add     hl,hl
        add     hl,hl
        add     hl,hl
        ld      a,h
        jr      oit_b
oi_t4:
        ld      a,l
        rr      h
        rra
        rr      h
        rra
oit_b:
        xor     #80
        ret

; --- τα άγκιστρα του object.asm, σε τρόπο μέτρησης ---
; ov_meas — το πλαίσιο στο περίγραμμα του ευρετηρίου (oi_build), και τίποτα
; στην οθόνη. Ο θόλος δεν έχει τίποτα άλλο να πει: το pop αφήνει την
; επιστροφή στο ob_shell, και το oi_gy8 γυρίζει κατευθείαν στο oi_pass.
ov_meas:
        pop     af
        ld      hl,(d_fx)
        ld      a,(d_qw)
        add     a,a
        call    oi_gx8
        ld      hl,(d_fy)
        ld      a,(d_qh)
        add     a,a
        jp      oi_gy8


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

oi_e:       defs OI_REC         ; η εγγραφή που μετριέται: x0, x1, y0, y1, id
oi_ptr:     dw 0                ; πού πάει η επόμενη (τράπεζα 5)
oi_k:       db 0                ; πόσες γράφτηκαν σε αυτό το πέρασμα
        assert  oi_ptr == oi_e + OI_REC && oi_k == oi_ptr + 2
