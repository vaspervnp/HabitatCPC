; info.asm — «τι έχει από κάτω»: το I στο LOOK (DESIGN §9.1, βήμα 79).
;
; Οι σειρές 3-4 του HUD λένε τι είναι χτισμένο στο tile του κέρσορα και τι
; έδαφος έχει. Είναι μια κατάσταση του ui (UI_INFO) που τρέχει τον κώδικα του
; LOOK: μένει ώσπου να κουνηθεί ο κέρσορας ή να πατηθεί το ESC, και ένα I
; ακόμη την ξαναδιαβάζει. Μόνο στο πλήρες παιχνίδι: το κτίριο το βρίσκει το
; mt_scan του src/meteor.asm, η ίδια ερώτηση που κάνει μια κρούση.
;
; Στην τράπεζα 2, όπως ό,τι τρέχει μόνο όταν το ζητήσει ο παίκτης.
;
;   σειρά 3   DOME S   OXYGEN     ACTIVE HP 100%     (θόλος: μέγεθος, δωμάτιο)
;             SOLAR               SITE   HP  40%     (δομή)
;             CORRIDOR                               (κατοχή, χωρίς κτίριο)
;             NOTHING BUILT
;   σειρά 4   MOUNTAIN   ORE VEIN                    (το έδαφος του tile)

; ---------------------------------------------------------------------------
; in_panel — από το ui_panel, με το HUD στη σειρά 3, στήλη 0. Τελειώνει στο
; uip_spd, την ταχύτητα στις στήλες 35-39 της σειράς 3.
; ---------------------------------------------------------------------------
in_panel:
        ; --- ό,τι χρειάζεται από τις τράπεζες 6 και 4, πριν τυπωθεί τίποτα:
        ; ο γλύφος σελιδοποιεί την 7 ---
        call    ob_b6
        call    ui_curt                 ; L = x, H = y
        ld      b,l
        ld      c,h
        ld      hl,G_dome_tbl
        ld      de,MAX_DOME * 256 + DOME_REC
        call    mt_scan
        ld      a,1                     ; θόλος
        jr      c,inp_rec
        ld      de,MAX_STRUCT * 256 + STRUCT_REC
        call    mt_scan                 ; το HL είναι ήδη στο G_struct_tbl
        ld      a,2                     ; δομή
        jr      c,inp_rec
        xor     a                       ; τίποτα
inp_rec:
        ld      (in_t),a
        push    bc                      ; το tile, για το έδαφος
        inc     hl
        inc     hl                      ; D_SIZE / ST_KIND
        ld      de,in_k
        ld      bc,4                    ; μέγεθος/είδος, δωμάτιο/μέγεθος,
        ldir                            ; κατάσταση, ακεραιότητα
        assert  D_ROOM == D_SIZE + 1 && D_STATE == D_SIZE + 2 && D_INTEG == D_SIZE + 3
        assert  ST_SIZE == ST_KIND + 1 && ST_STATE == ST_KIND + 2 && ST_INTEG == ST_KIND + 3
        assert  D_SIZE == ST_KIND
        ld      bc,GA_PORT + PAGE_B4
        out     (c),c
        pop     bc
        call    tile_addr
        ld      a,(hl)
        ld      (in_w),a
        ; Η τράπεζα 1 ξαναμπαίνει με τον πρώτο γλύφο: το hud_char γυρίζει
        ; στο hud_pg, που το hud_text7 αφήνει πάντα στην 1.
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
        ; --- το δωμάτιο, για θόλο: η θέση του στο rm_list δίνει το όνομα ---
        ld      a,(in_t)
        dec     a
        jr      nz,inp_noroom
        ld      a,(in_r)
        ld      hl,rm_list
        ld      bc,10
        cpir
        jr      nz,inp_noroom           ; άδειο ή αεροθάλαμος: κανένα όνομα
        ld      a,9
        sub     c                       ; η θέση στον κατάλογο
        add     a,a
        ld      hl,rm_names
        call    ob_addu
        ld      a,(hl)
        inc     hl
        ld      h,(hl)
        ld      l,a
        call    hud_text7
        jr      inp_state
inp_noroom:
        ld      b,10
        call    hud_blank
inp_state:
        ld      b,1
        call    hud_blank
        ld      a,(in_st)
        cp      DS_ACTIVE
        ld      hl,t_i_act
        jr      z,inp_st
        ld      hl,t_i_site
inp_st:
        call    hud_text7
        ld      b,1
        call    hud_blank
        ld      hl,t_i_hp
        call    hud_text7
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
        ld      b,35 - 34               ; ένα κενό πριν από την ταχύτητα
        jr      inp_r3
inp_none:
        ; Κατοχή χωρίς θόλο ή δομή από πάνω: διάδρομος. Το cr_stamp σφραγίζει
        ; τα tiles του με το ίδιο bit που βάζει και το χτίσιμο (W_OCC_STRUCT).
        ; Από το βήμα 85 και το μονοπάτι στο έδαφος, με κατοχή 2 (src/link.asm).
        ld      a,(in_w)
        and     W_OCC_MASK
        ld      hl,t_corr               ; τράπεζα 2
        ld      b,35 - 9
        cp      W_OCC_PATH
        jr      nz,inp_cor
        ld      hl,t_pathw
inp_cor:
        or      a
        jr      nz,inp_name
        ld      hl,t_i_none
        call    hud_text7
        ld      b,35 - 13
        jr      inp_r3
inp_name:
        push    bc
        call    hud_text
        pop     bc
inp_r3:
        call    hud_blank
        ; --- σειρά 4: το έδαφος, και η φλέβα αν είναι βουνό με μετάλλευμα ---
        ld      a,4
        call    hud_go
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
        call    hud_text7
        ld      b,40 - 10
        ld      a,(in_w)
        and     #0F
        cp      #08 + W_MOUNTAIN        ; βουνό, με το bit του πόρου
        jr      nz,inp_r4
        ld      hl,t_i_ore
        call    hud_text7
        ld      b,40 - 19
inp_r4:
        call    hud_blank
        jp      uip_spd

in_t:       db 0                ; 0 τίποτα, 1 θόλος, 2 δομή
in_k:       db 0                ; μέγεθος θόλου / είδος δομής
in_r:       db 0                ; δωμάτιο θόλου / μέγεθος δομής
in_st:      db 0                ; κατάσταση
in_hp:      db 0                ; ακεραιότητα
in_w:       db 0                ; το byte του κόσμου
        assert  in_r == in_k + 1 && in_st == in_k + 2 && in_hp == in_k + 3
        assert  rm_names == rm_list + 10
