; ---------------------------------------------------------------------------
; panel7.asm — οι πίνακες των σειρών 3-4 που τυπώνονται με την 7 στο παράθυρο
; (βήμα 180, DESIGN §4.2): του I (in_p7, από το in_panel του src/info.asm), η
; γραμμή του πλοίου (cw_panel) και του εμπόρου (tr_panel, από το ac_panel του
; src/act.asm). ΣΤΗΝ ΤΡΑΠΕΖΑ 7, μετά τις σελίδες του tutorial, στο ίδιο αρχείο
; του δίσκου (TEXT.BIN): τρέχουν με την 7 μέσα και δεν σελιδοποιούν ποτέ. Το
; hud_pg είναι η 7 (hud_page), οπότε ο γλύφος γυρίζει εδώ· ΚΑΝΕΝΑ hud_text7,
; που θα έβαζε την 1 κάτω από τα πόδια τους. Ό,τι καλούν στην 0 δεν
; σελιδοποιεί: hud_char, hud_text, hud_to, hud_go, hud_blank, hud_num, ob_mul,
; ob_addu, ln_row4, και τα tr_sum, tr_ok, tr_load, tr_qn του src/lines.asm.
; Τελειώνουν όλα στο acp_end της 2 (src/act.asm), που βάζει πίσω την 1.
;
; Ως το βήμα 179 ζούσαν εκεί που τα καλούν: 167 bytes στην τράπεζα 2 και 260
; στην 0, που είχαν 1 και 4. Τα θέλει το βήμα 181, η κατεδάφιση του πλοίου.
; ---------------------------------------------------------------------------

; in_p7 — η σειρά 3 και η 4 του I: in_t, in_k.. in_w τα γέμισε το in_panel.
in_p7:
        ; --- σειρά 3: το κτίριο ---
        ld      a,(in_t)
        or      a
        jp      z,inp_none
        ; Το όνομα από τον κατάλογο: δέκα bytes το καθένα, οι θόλοι κατά
        ; μέγεθος από το t_dome_s, οι δομές κατά είδος από το t_solar.
        dec     a
        ld      hl,t_dome_s
        jr      z,inp_nm
        ld      hl,t_solar
inp_nm:
        ld      a,(in_k)
        add     a,a
        ld      c,a
        add     a,a
        add     a,a
        add     a,c                     ; x10
        call    ob_addu
        call    hud_text                ; εννέα στήλες, με τα κενά του
        ld      a,(in_k)
        cp      K_CRATES                ; ένας θόλος έχει εδώ το μέγεθός του, 0-2
        jr      z,inp_box
        ; --- το δωμάτιο, για θόλο: η θέση του στο rm_list δίνει το όνομα ---
        ld      a,(in_t)
        dec     a
        jr      nz,inp_noroom
        ld      a,(in_r)
        ld      hl,rm_list
        ld      bc,10
        cpir
        jr      nz,inp_noroom           ; άδειο ή αεροθάλαμος: κανένα όνομα
        ld      a,18                    ; HL = rm_list + θέση + 1, θέση = 9 - C:
        sub     c                       ; rm_names + 2 x θέση = HL + 18 - C
        call    ob_addu
        ld      a,(hl)
        inc     hl
        ld      h,(hl)
        ld      l,a
        call    hud_text
inp_noroom:
        ld      b,20                    ; 9 + 10 στήλες, και ένα κενό
        call    hud_to
inp_state:
        ld      a,(in_st)
        cp      DS_ACTIVE
        ld      hl,t_i_act
        jr      z,inp_st
        ld      hl,t_i_site
inp_st:
        call    hud_text
        call    hud_space
        ld      hl,t_i_hp
        call    hud_text
        ; Η ακεραιότητα είναι 0-255 (και στο εργοτάξιο η πρόοδος, §6.9): στα
        ; εκατό, 255 x 101 / 256 = 100.
        ld      a,(in_hp)
        ld      c,101
        call    ob_mul                  ; HL = ακεραιότητα x 101
        ld      a,h
        ld      b,3
        call    hud_numa
        ld      a,'%'
        call    hud_char
        jr      inp_r3
; ΤΑ ΚΙΒΩΤΙΑ ΤΟΥ ΣΚΑΦΟΥΣ (βήμα 181, src/crates.asm): ό,τι μένει από το καθένα
; και σε πόσα sol χάνεται, στη θέση της κατάστασης και της ακεραιότητας:
;   CRATES    FE 150 BI 100 10 SOL
; Ο σωρός είναι ένας, πρώτα το μέταλλο ως το CR_BIO και από κάτω το βιοπλαστικό.
inp_box:
        call    hud_space
        ld      hl,t_fe
        call    hud_text
        call    hud_space
        ld      a,(in_ow)
        sub     CR_BIO
        jr      nc,inb_fe
        xor     a                       ; το μέταλλο τελείωσε
inb_fe:
        ld      b,3
        call    hud_numa
        call    hud_space
        ld      hl,t_bi
        call    hud_text
        call    hud_space
        ld      a,(in_ow)
        cp      CR_BIO
        jr      c,inb_bi
        ld      a,CR_BIO
inb_bi:
        ld      b,3
        call    hud_numa
        call    hud_space
        ld      a,(in_ops)              ; το sol της λήξης, & 63 (και το bit της Haul)
        ld      hl,EC_SOL
        sub     (hl)
        and     CR_SMASK
        ld      b,2
        call    hud_numa
        ld      hl,txt_sol
        call    hud_text
        jr      inp_r3
inp_none:
        ; Κατοχή χωρίς θόλο ή δομή από πάνω: διάδρομος. Το cr_stamp σφραγίζει
        ; τα tiles του με το ίδιο bit που βάζει και το χτίσιμο (W_OCC_STRUCT).
        ; Από το βήμα 85 ως το 130 και το μονοπάτι στο έδαφος, με κατοχή 2·
        ; από το 131 είναι θεμέλιο χωρίς κατοχή (src/link.asm), και το I λέει
        ; NOTHING BUILT και στη σειρά 4 το θεμέλιο, όπως για τη σύνδεση εδάφους.
        ld      a,(in_w)
        and     W_OCC_MASK
        ld      hl,t_corr               ; τράπεζα 2
        jr      nz,inp_name
        ld      hl,t_i_none             ; τράπεζα 7: φαίνονται και οι δύο
inp_name:
        call    hud_text
inp_r3:
        ; --- σειρά 4: το έδαφος, και η φλέβα αν είναι βουνό με μετάλλευμα ---
        call    ln_row4                 ; κενά ως τη στήλη 35, και η σειρά 4
        ld      a,(in_w)
        and     7
        ld      c,a
        add     a,a
        add     a,a
        add     a,c
        add     a,a
        add     a,c                     ; x11
        ld      hl,t_i_cls
        call    ob_addu
        call    hud_text
        ld      a,(in_w)
        and     #0F
        cp      #08 + W_MOUNTAIN        ; βουνό, με το bit του πόρου
        ld      hl,t_i_ore
        call    z,hud_text
        ; Ο ΣΩΡΟΣ ΕΝΟΣ ΟΡΥΧΕΙΟΥ ΣΕ ΛΕΙΤΟΥΡΓΙΑ (βήμα 184, η επιλογή του χρήστη),
        ; μετά το έδαφος: «ORE 4/6». Ενας θόλος έχει στο in_k το μέγεθός του, 0-2,
        ; και ένα εργοτάξιο στο ST_OWED τα υλικά που χρωστά. Το «/6» είναι
        ; κείμενο: το src/uitext.asm το έχουν και σκαλωσιές χωρίς το haul.asm.
        assert  MINE_CAP == 6 && K_MINE > 2
        ld      a,(in_k)
        cp      K_MINE
        jr      nz,inp_end
        ld      a,(in_st)
        cp      DS_ACTIVE
        jr      nz,inp_end
        call    hud_space
        ld      hl,t_i_pile
        call    hud_text                ; «ORE»
        ld      a,(in_ow)
        ld      b,2
        call    hud_numa                ; « 4»
        ld      hl,t_i_cap
        call    hud_text                ; «/6»
inp_end:
        jp      acp_end                 ; κενά ως τη στήλη 40, uip_spd

; cw_panel — από το ac_panel, στη σειρά 3, στήλη 0. Οι οδηγίες στη σειρά 3
; και η λίστα στη 4, που έχει 40 στήλες: πέντε φορές «>WRK 20» είναι 35, και
; στη σειρά 3 θα κολλούσαν στην ταχύτητα (35-39) — οι δύο σειρές είναι μία
; γραμμή οθόνης. Τελειώνει όπως εκείνο.
cw_panel:
        ld      hl,t_cw_keys
        call    hud_text
        call    ln_row4
        call    hud_space               ; ένα κενό μετά το PAUSE
        ld      hl,t_cw_names
        xor     a
cwp_lp:
        push    af                      ; i, στη στοίβα ως το τέλος του γύρου
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
        pop     af
        push    hl
        push    af
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
        pop     af
        pop     hl
        inc     a
        cp      CW_N
        jr      c,cwp_lp
        jp      acp_end                 ; src/act.asm

; tr_panel — σειρά 3, στήλη 0. Τελειώνει όπως το cw_panel.
tr_panel:
        call    tr_sum
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
        ld      hl,t_tr_fire
        call    nc,hud_text
        call    ln_row4                 ; --- σειρά 4 ---
        call    tr_load                 ; HL -> net
        push    hl
        call    hud_space               ; ένα κενό μετά το PAUSE, όπως το cw_panel:
        ld      a,'<'                   ; οι σειρές 3 και 4 είναι μία γραμμή
        call    hud_char
        ld      a,(tr_g)
        ld      hl,tr_name
        call    ob_addu
        ld      l,(hl)                  ; ήδη x8 (t_f_names)
        ld      h,0
        ld      de,t_f_names
        add     hl,de
        call    hud_text
        ld      a,'>'
        call    hud_char
        ld      hl,t_tr_ship
        call    hud_text
        ld      a,(tr_cq)               ; ως 40 (tr_lot x 4), ή 150 νομίσματα
        call    tr_qn
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
        call    tr_qn
        jr      trp_hv
trp_0:  ld      a,(tr_g)
        cp      1                       ; CY: τα νομίσματα, ένα ψηφίο ακόμη
        ld      a,8
        adc     a,0
        ld      b,a
        call    hud_blank
trp_hv: ld      hl,t_tr_have
        call    hud_text
        ld      hl,(tr_hv)
        ld      b,3                     ; ως το EC_CAP, 600, ή το COIN_MAX, 999
        call    hud_num
        ld      a,(tr_g)
        or      a
        jp      z,acp_end               ; τα νομίσματα: η αξία τους είναι 1
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
