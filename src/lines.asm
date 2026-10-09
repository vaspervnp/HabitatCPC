; lines.asm — οι γραμμές του μενού ενεργειών (DESIGN §6.11, §9.1).
;
; Μία γραμμή είναι υπο-κατάσταση του UI_ACT (το ac_mode του src/act.asm): οι
; σειρές 3-4 του HUD, τα βέλη, FIRE και ESC. Η γραμμή του πλοίου είναι του
; βήματος 91 και ως το 93 ζούσε στο src/crew.asm· το μέτρημα και η επιλογή του
; νεοφερμένου, που τα καλεί μόνο ο τροχός, πήγαν στην τράπεζα 6 (b6code), και
; η γραμμή έμεινε εδώ, στην τράπεζα 0, γιατί τη ζωγραφίζει το HUD με την 7 στο
; παράθυρο.

; ---------------------------------------------------------------------------
; Η ΓΡΑΜΜΗ ΤΟΥ ΠΛΟΙΟΥ: μία υπο-κατάσταση του μενού ενεργειών (UI_ACT, το
; ac_mode του src/act.asm), όπως η διαχείριση. Το κουμπί του πλοίου και το C
; την ανοίγουν.
;
;   σειρά 3   SHIP UP/DN=10% FIRE=CALL ESC=BACK  PAUSE
;   σειρά 4    >WRK 20 ENG 20 BIO 20 MED 20 GRD 20
;
; ΑΡΙΣΤΕΡΑ/ΔΕΞΙΑ διαλέγουν ειδικότητα. ΠΑΝΩ: +10% σε αυτήν, -10% από τη
; μεγαλύτερη από τις άλλες. ΚΑΤΩ: -10% σε αυτήν, +10% στη μικρότερη από τις
; άλλες. Σε ισοπαλία η πρώτη. Ετσι το άθροισμα μένει 100 και το κόστος μιας
; αλλαγής πέφτει εκεί που υπάρχει περισσότερο. FIRE καλεί το πλοίο, ESC κλείνει.
; ---------------------------------------------------------------------------
CW_MODE     equ 2                       ; ac_mode: 0 ομάδες, 1 διαχείριση

; cw_ud — από το cw_tick (src/act.asm): A = 1 πάνω, 2 κάτω (3: κάτω).
cw_ud:
        ld      b,a                     ; 1 πάνω, 2 κάτω (3: κάτω)
        ld      a,(cw_sel)
        ld      e,a
        ld      d,0
        ld      hl,EC_LAND
        add     hl,de                   ; HL -> t_s
        ld      c,d                     ; C = 0: η μεγαλύτερη
        ld      a,(hl)
        djnz    cwu_dn
        cp      10
        ret     nc
        inc     (hl)
        call    cw_ext
        dec     (hl)
        jp      cw_draw                 ; src/act.asm
cwu_dn:
        or      a
        ret     z
        dec     (hl)
        dec     c                       ; #FF: η μικρότερη
        call    cw_ext
        inc     (hl)
        jp      cw_draw

; cw_ext — E = s, C = 0 ή #FF: HL -> το t της μεγαλύτερης (ή, με το xor, της
; μικρότερης) από τις άλλες τέσσερις. Από το τέλος προς την αρχή, και το ίσο
; κερδίζει: σε ισοπαλία μένει η πρώτη.
cw_ext:
        ld      hl,EC_LAND + CW_N - 1
        ld      b,CW_N
        ld      d,0
        inc     e                       ; E = s + 1, όπως το B
cwe_lp:
        ld      a,b
        cp      e
        jr      z,cwe_n                 ; όχι η ίδια
        ld      a,(hl)
        xor     c
        cp      d
        jr      c,cwe_n
        ld      d,a
        ld      (cw_ptr),hl
cwe_n:
        dec     hl
        djnz    cwe_lp
        ld      hl,(cw_ptr)
        ret

; cw_panel — από το ac_panel, στη σειρά 3, στήλη 0. Οι οδηγίες στη σειρά 3
; και η λίστα στη 4, που έχει 40 στήλες: πέντε φορές «>WRK 20» είναι 35, και
; στη σειρά 3 θα κολλούσαν στην ταχύτητα (35-39) — οι δύο σειρές είναι μία
; γραμμή οθόνης. Τελειώνει όπως εκείνο.
cw_panel:
        ld      bc,GA_PORT + PAGE_B7
        call    hud_page                ; τα κείμενα στην 7
        ld      hl,t_cw_keys
        call    hud_text
        ld      b,35
        call    hud_to
        ld      a,4
        call    hud_go
        call    hud_space               ; ένα κενό μετά το PAUSE
        ld      hl,t_cw_names
        xor     a
cwp_lp:
        ld      (cw_i),a
        push    hl
        ld      hl,cw_sel
        cp      (hl)
        ld      a,'>'
        jr      z,cwp_m
        ld      a,' '
cwp_m:
        call    hud_char
        pop     hl
        call    hud_text                ; «WRK»
        inc     hl
        push    hl
        ld      a,(cw_i)
        add     a,EC_LAND & 255
        ld      l,a
        ld      h,EC_LAND >> 8
        ld      a,(hl)
        add     a,a
        ld      b,a
        add     a,a
        add     a,a
        add     a,b                     ; % = 10 t
        ld      b,3
        call    hud_numa                ; «  0», « 20», «100»
        pop     hl
        ld      a,(cw_i)
        inc     a
        cp      CW_N
        jr      c,cwp_lp
        jp      acp_end                 ; src/act.asm

cw_sel:     db 0
cw_i:       db 0
cw_ptr:     dw 0

        assert  A_UP == 0 && A_DOWN == 1        ; το djnz του cw_ud

; ---------------------------------------------------------------------------
; Η ΓΡΑΜΜΗ ΤΟΥ ΕΜΠΟΡΟΥ (βήμα 93, DESIGN §6.11): το παράθυρο ανταλλαγής του
; Planetbase σε μία γραμμή. Το κουμπί του εμπόρου στη ΜΕΤΑΦΟΡΑ την ανοίγει,
; όσο εκείνος είναι προσγειωμένος.
;
;   σειρά 3   +40% TAKE  210 GIVE  250 FIRE=DEAL
;   σειρά 4    <METAL  > SHIP 20  TAKE 10 HAVE 75 @ 15
;
; Η σειρά 3 είναι το ζύγι: όσα παίρνεις, στις τιμές του (η αξία συν το κέρδος
; του), και όσα δίνεις, στην αξία τους. FIRE=DEAL φαίνεται μόνο όταν παίρνεις
; κάτι και δίνεις τουλάχιστον όσο παίρνεις — όπως το κουμπί του Planetbase.
; Η σειρά 4 είναι ένα αγαθό με τις τέσσερις στήλες εκείνου του παραθύρου: όσα
; φέρνει, όσα παίρνεις ή δίνεις, όσα έχεις, και η αξία του.
;
; ΑΡΙΣΤΕΡΑ/ΔΕΞΙΑ περνούν από τα δεκατρία αγαθά, πρώτα τα δικά του. ΠΑΝΩ: μία
; μονάδα ακόμη από αυτόν (ή μία λιγότερη προς αυτόν), ως όσα φέρνει και ως το
; ταβάνι της αποθήκης. ΚΑΤΩ: μία ακόμη προς αυτόν (ή μία λιγότερη από αυτόν),
; ως όσα έχεις και ως 99. Η μονάδα είναι του tr_lot (src/stock.asm). FIRE ή
; SPACE: η ανταλλαγή, και φεύγει. ESC κλείνει, και η προσφορά ξεχνιέται.
;
; Η ΠΡΟΣΦΟΡΑ ΖΕΙ ΣΤΗ ΜΝΗΜΗ ΕΡΓΑΣΙΑΣ ΤΟΥ src/crew.asm: εκείνη τη θέλει μόνο η
; προσγείωση αποίκων, και όσο ο έμπορος είναι εδώ άλλο πλοίο δεν έρχεται.
; ---------------------------------------------------------------------------
TR_MODE     equ 3                       ; ac_mode
TR_NET      equ G_crew                  ; 14, ανά απόθεμα: + παίρνεις, - δίνεις
TR_ORD      equ G_crew + 14             ; 13: η σειρά των βελών
        assert  TR_ORD + TRADE_N <= G_crew + 33
        assert  (EC_CARGO >> 8) == ((EC_CARGO + 2 * MER_SLOTS - 1) >> 8)
        assert  TR_MODE == CW_MODE + 1 && BT_TRADE == BT_SHIP + 1  ; το bww_act

; ln_tick, ln_panel — από το ac_tick και το ac_panel, για ac_mode >= CW_MODE.
ln_tick:
        ld      c,a
        ld      a,(ac_mode)
        cp      TR_MODE
        ld      a,c
        jp      nz,cw_tick              ; src/act.asm
tr_tick:
        ld      c,a
        call    mer_here                ; σε κάθε frame: αν έφυγε, κλείνει
        jr      z,trt_here
        xor     a                       ; UI_LOOK
        jp      ui_goto
trt_here:
        ld      a,c
        and     1 << A_FIRE | 1 << A_MENU
        jp      nz,tr_deal
        ld      a,c
        and     1 << A_UP | 1 << A_DOWN
        jp      nz,tr_ud
        ld      hl,tr_sel
        ld      c,TRADE_N
        call    ui_lr
        ret     z
        jp      cw_draw                 ; ήχος, ui_dirty, ui_panel (src/act.asm)

ln_panel:
        ld      a,(ac_mode)
        cp      TR_MODE
        jp      nz,cw_panel
        ; fall through

; tr_panel — σειρά 3, στήλη 0. Τελειώνει όπως το cw_panel.
tr_panel:
        call    tr_sum
        ld      bc,GA_PORT + PAGE_B7
        call    hud_page                ; τα κείμενα στην 7
        ld      a,'+'
        call    hud_char
        ld      a,(EC_MARKUP)
        ld      b,2
        call    hud_numa
        ld      a,'%'
        call    hud_char
        ld      hl,t_tr_take
        call    hud_text
        ld      hl,(tr_take)
        ld      b,4
        call    hud_num
        ld      hl,t_tr_give
        call    hud_text
        ld      hl,(tr_give)
        ld      b,4
        call    hud_num
        call    tr_ok
        jr      c,trp_r3
        ld      hl,t_tr_fire
        call    hud_text
trp_r3: ld      b,35
        call    hud_to
        ; --- σειρά 4 ---
        ld      a,4
        call    hud_go
        call    tr_load                 ; HL -> net
        push    hl
        call    hud_space               ; ένα κενό μετά το PAUSE, όπως το cw_panel:
        ld      a,'<'                   ; οι σειρές 3 και 4 είναι μία γραμμή
        call    hud_char
        ld      a,(tr_g)
        ld      hl,tr_name
        call    ob_addu
        ld      l,(hl)
        ld      h,0
        add     hl,hl
        add     hl,hl
        add     hl,hl                   ; x8 (t_f_names)
        ld      de,t_f_names
        add     hl,de
        call    hud_text
        ld      a,'>'
        call    hud_char
        ld      hl,t_tr_ship
        call    hud_text
        ld      a,(tr_cq)
        ld      b,2                     ; ως 40 (tr_lot x 4)
        call    hud_numa
        pop     hl
        ld      a,(hl)                  ; net
        or      a
        jr      z,trp_0
        ld      hl,t_tr_take
        jp      p,trp_n
        neg
        ld      hl,t_tr_give
trp_n:  push    af
        call    hud_text
        pop     af
        ld      b,2
        call    hud_numa
        jr      trp_hv
trp_0:  ld      b,8
        call    hud_blank
trp_hv: ld      hl,t_tr_have
        call    hud_text
        ld      hl,(tr_hv)
        ld      b,3                     ; ως το EC_CAP, 600
        call    hud_num
        call    hud_space
        ld      a,'@'
        call    hud_char
        ld      a,(tr_g)
        ld      hl,tr_value
        call    ob_addu
        ld      a,(hl)
        ld      b,3
        call    hud_numa
        jp      acp_end                 ; src/act.asm

; ---------------------------------------------------------------------------
; tr_open — το κουμπί του εμπόρου (btk_ajp, src/act.asm), από το LOOK.
; ---------------------------------------------------------------------------
tr_open:
        call    mer_here
        jp      nz,uip_deny             ; κόκκινο: όπως ένα δωμάτιο που δεν χωρά
        ; η προσφορά από την αρχή
        ld      hl,TR_NET
        ld      b,14
tro_z:  ld      (hl),0
        inc     l
        djnz    tro_z
        ; HL = TR_ORD: πρώτα τα δικά του, με τη σειρά του φορτίου
        ld      de,EC_CARGO
        ld      b,MER_SLOTS
tro_c:  ld      a,(de)
        or      a
        jr      z,tro_cn
        ld      (hl),a
        inc     l
tro_cn: inc     de
        inc     de
        djnz    tro_c
        ; ...και μετά τα υπόλοιπα, με τη σειρά των αποθεμάτων
        ld      c,1
tro_r:  call    tr_find
        jr      z,tro_rn
        ld      (hl),c
        inc     l
tro_rn: inc     c
        ld      a,c
        cp      TRADE_N + 1
        jr      c,tro_r
        xor     a
        ld      (tr_sel),a
        ld      a,TR_MODE
        ld      (ac_mode),a
        call    ui_click
        ld      a,UI_ACT
        jp      ui_ask

; tr_find — C = απόθεμα. Z, και A = πόσα φέρνει, αν το φέρνει· αλλιώς NZ και
; A = 0. Χαλάει B, DE.
tr_find:
        ld      de,EC_CARGO
        ld      b,MER_SLOTS
trf_lp: ld      a,(de)
        inc     de
        cp      c
        ld      a,(de)
        inc     de
        ret     z
        djnz    trf_lp
        ld      a,0                     ; NZ από το τελευταίο cp
        ret

; tr_price — A = απόθεμα: η τιμή του, αξία + (αξία x κέρδος + 50) / 100 —
; στρογγυλεμένη ανά μονάδα: το βιοπλαστικό με 40% κάνει 14, όπως στο
; παράδειγμα του Planetbase. Χαλάει όλους.
tr_price:
        ld      hl,tr_value
        call    ob_addu
        ld      a,(hl)
        push    af
        ld      e,a
        ld      a,(EC_MARKUP)
        call    tr_mul                  ; HL = αξία x κέρδος (ως 120 x 65)
        ld      de,50
        add     hl,de
        ld      de,-100
        ld      a,-1
trp_d:  inc     a
        add     hl,de
        jr      c,trp_d
        pop     bc                      ; B = η αξία
        add     a,b
        ret

; tr_mul — HL = A x E. Χαλάει A, B, D.
tr_mul:
        ld      hl,0
        ld      d,h
        ld      b,8
trm_lp: add     hl,hl
        rla
        jr      nc,trm_n
        add     hl,de
trm_n:  djnz    trm_lp
        ret

; tr_load — το διαλεγμένο: tr_g, tr_cq (όσα φέρνει), tr_hv (όσα έχεις). Out:
; HL -> net του. Χαλάει όλους.
tr_load:
        ld      a,(tr_sel)
        add     a,TR_ORD & 255
        ld      l,a
        ld      h,TR_ORD >> 8
        ld      c,(hl)
        ld      a,c
        ld      (tr_g),a
        call    tr_find
        ld      (tr_cq),a
        ld      a,c
        call    ec_stock_ptr            ; DE -> το απόθεμα (src/stock.asm)
        ex      de,hl
        ld      e,(hl)
        inc     hl
        ld      d,(hl)
        ld      (tr_hv),de
        ld      a,c
        add     a,TR_NET & 255
        ld      l,a
        ld      h,TR_NET >> 8
        ret

; tr_ud — από το tr_tick: A = 1 πάνω, 2 κάτω (3: πάνω).
tr_ud:
        rra                             ; CY = πάνω
        push    af
        call    tr_load                 ; HL -> net
        ld      a,(tr_g)
        push    hl
        ld      hl,tr_lot
        call    ob_addu
        ld      c,(hl)                  ; C = η μονάδα
        pop     hl
        pop     af
        ld      a,(hl)                  ; A = net
        jr      nc,tru_dn
        ; --- ΠΑΝΩ: λιγότερα προς αυτόν, ή περισσότερα από αυτόν ---
        or      a
        jp      p,tru_tk
        add     a,c
        jp      m,tru_st
        xor     a                       ; ως το μηδέν, όχι πέρα
        jr      tru_st
tru_tk: add     a,c
        ld      b,a                     ; B = net + μονάδα
        push    hl
        ld      hl,EC_CAP               ; όσα χωράνε στην αποθήκη...
        ld      de,(tr_hv)
        or      a
        sbc     hl,de
        ld      a,(tr_cq)               ; ...και όσα φέρνει: το μικρότερο
        inc     h
        dec     h
        jr      nz,tru_rm               ; πάνω από 255 χωράνε
        cp      l
        jr      c,tru_rm
        ld      a,l
tru_rm: pop     hl
        cp      b
        jr      c,tru_st                ; το όριο
        ld      a,b
        jr      tru_st
        ; --- ΚΑΤΩ: λιγότερα από αυτόν, ή περισσότερα προς αυτόν ---
tru_dn: or      a
        jr      z,tru_gv
        jp      m,tru_gv
        sub     c
        jr      nc,tru_st
        xor     a
        jr      tru_st
tru_gv: neg                             ; όσα δίνεις, θετικά
        add     a,c
        ld      b,a
        ld      a,(tr_hv + 1)
        or      a
        ld      a,TRADE_MAX
        jr      nz,tru_mx               ; πάνω από 255 έχεις
        ld      a,(tr_hv)
        cp      TRADE_MAX
        jr      c,tru_mx
        ld      a,TRADE_MAX
tru_mx: cp      b                       ; A = όσα μπορείς: το μικρότερο
        jr      c,tru_ng
        ld      a,b
tru_ng: neg
tru_st: ld      (hl),a
        jp      cw_draw

; tr_sum — tr_take: όσα παίρνεις, στις τιμές του (tr_price).
; tr_give: όσα δίνεις, στην αξία τους. Χαλάει όλους.
tr_sum:
        ld      hl,0
        ld      (tr_take),hl
        ld      (tr_give),hl
        ld      c,0                     ; C = θέση φορτίου
trs_c:  ld      a,c
        add     a,a
        add     a,EC_CARGO & 255
        ld      l,a
        ld      h,EC_CARGO >> 8
        ld      a,(hl)                  ; το απόθεμα (0: κενή θέση, net 0)
        add     a,TR_NET & 255
        ld      l,a
        ld      h,TR_NET >> 8
        ld      a,(hl)
        dec     a
        jp      m,trs_cn                ; <= 0: δεν το παίρνεις
        inc     a
        push    bc
        push    af
        ld      a,l
        sub     TR_NET & 255            ; το απόθεμα
        call    tr_price                ; ~0,5 ms: μόνο όταν πατηθεί πλήκτρο
        ld      e,a                     ; η τιμή του
        pop     af
        pop     bc
        ld      hl,tr_take
        call    trs_add
trs_cn: inc     c
        ld      a,c
        cp      MER_SLOTS
        jr      c,trs_c
        ld      c,1                     ; C = απόθεμα
trs_g:  ld      a,c
        add     a,TR_NET & 255
        ld      l,a
        ld      h,TR_NET >> 8
        ld      a,(hl)
        or      a
        jp      p,trs_gn                ; >= 0: δεν το δίνεις
        neg
        push    af
        ld      a,c
        ld      hl,tr_value
        call    ob_addu
        ld      e,(hl)                  ; η αξία του
        pop     af
        ld      hl,tr_give
        call    trs_add
trs_gn: inc     c
        ld      a,c
        cp      TRADE_N + 1
        jr      c,trs_g
        ret

; trs_add — (HL) += A x E, 16 bit. Κρατά το C.
trs_add:
        push    bc
        push    hl
        call    tr_mul
        ex      de,hl
        pop     hl
        ld      a,(hl)
        add     a,e
        ld      (hl),a
        inc     hl
        ld      a,(hl)
        adc     a,d
        ld      (hl),a
        pop     bc
        ret

; tr_ok — μετά το tr_sum. NC: γίνεται (παίρνεις κάτι, και δίνεις τουλάχιστον
; όσο παίρνεις). CY: όχι.
tr_ok:
        ld      de,(tr_take)
        ld      a,d
        or      e
        scf
        ret     z
        ld      hl,(tr_give)
        or      a
        sbc     hl,de
        ret

; ---------------------------------------------------------------------------
; tr_deal — FIRE ή SPACE. Αν δεν φτάνει, ο ήχος του «όχι» και η γραμμή μένει.
; Αλλιώς από όσα έχεις ΤΩΡΑ — κάτι μπορεί να το έφαγαν από τη στιγμή της
; προσφοράς — και τότε η ανταλλαγή: τα δικά του με ταβάνι (ec_add_stock), τα
; δικά σου αφαιρούνται, το σερί της ανεξαρτησίας σπάει, και ο έμπορος φεύγει.
; Στο Planetbase φεύγει όταν του παραδοθούν όλα· εδώ η παράδοση είναι
; στιγμιαία. tools/econ.py: trade.
; ---------------------------------------------------------------------------
tr_deal:
        call    tr_sum
        call    tr_ok
        jp      c,uip_deny
        ld      c,1
trd_ck: ld      a,c
        add     a,TR_NET & 255
        ld      l,a
        ld      h,TR_NET >> 8
        ld      a,(hl)
        or      a
        jp      p,trd_kn
        neg
        ld      b,a                     ; B = όσα δίνεις
        ld      a,c
        call    ec_stock_ptr
        ex      de,hl
        ld      a,(hl)
        inc     hl
        ld      h,(hl)                  ; H: πάνω από 255 έχεις, φτάνουν
        inc     h
        dec     h
        jr      nz,trd_kn
        cp      b
        ld      hl,t_poor               ; «NOT ENOUGH MATERIAL»
        jp      c,ui_say
trd_kn: inc     c
        ld      a,c
        cp      TRADE_N + 1
        jr      c,trd_ck
        ld      c,1
trd_lp: ld      a,c
        add     a,TR_NET & 255
        ld      l,a
        ld      h,TR_NET >> 8
        ld      a,(hl)
        or      a
        jr      z,trd_n
        push    bc
        jp      m,trd_gv
        ld      e,a
        ld      d,0
        ld      a,c
        call    ec_add_stock            ; με ταβάνι
        jr      trd_nx
trd_gv: neg
        ld      b,a
        ld      a,c
        call    ec_stock_ptr
        ex      de,hl
        ld      a,(hl)
        sub     b
        ld      (hl),a
        jr      nc,trd_nx
        inc     hl
        dec     (hl)
trd_nx: pop     bc
trd_n:  inc     c
        ld      a,c
        cp      TRADE_N + 1
        jr      c,trd_lp
        ld      a,1
        ld      (EC_TRADED),a           ; το σερί της ανεξαρτησίας σπάει
        xor     a
        ld      (EC_SHSTATE),a          ; SHIP_NONE: φεύγει
        ld      (ui_state),a            ; UI_LOOK
        ld      a,4                     ; το μήνυμα γράφει μόνο τη σειρά 3
        call    hud_go
        ld      b,40
        call    hud_blank
        ld      hl,t_deal
        jp      ui_say

; Το όνομα κάθε αποθέματος στο t_f_names (x8): μεταλλεύματα 18, το δικό τους.
tr_name:    db 0, 6, 18, 1, 2, 4, 7, 8, 3, 5, 12, 13, 14, 9
tr_sel:     db 0
tr_g:       db 0
tr_cq:      db 0
tr_hv:      dw 0
tr_take:    dw 0
tr_give:    dw 0
