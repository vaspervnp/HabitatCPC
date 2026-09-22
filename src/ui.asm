; ui.asm — ο κέρσορας, το μενού και το φάντασμα (DESIGN §9.1, §9.3).
;
; Τρεις καταστάσεις και τίποτε άλλο:
;
;   LOOK   ο κέρσορας περιφέρεται· η κάμερα τον ακολουθεί στο χείλος
;   MENU   ο κατάλογος του §9.3, μια γραμμή· αριστερά/δεξιά αλλάζει είδος
;   PLACE  το φάντασμα ακολουθεί τον κέρσορα, με τα άκυρα tiles σημαδεμένα
;
; Η ΣΕΙΡΑ ΜΕΣΑ ΣΕ ΕΝΑ ΒΗΜΑ ΕΙΝΑΙ ΔΕΣΜΕΥΤΙΚΗ: πρώτα σβήνει το φάντασμα, μετά
; κινείται ο κέρσορας, μετά (αν χρειάζεται) σκρολάρει η κάμερα, και τελευταίο
; ξαναζωγραφίζεται το φάντασμα. Αν το σβήσιμο γίνει μετά το σκρολάρισμα, οι
; διευθύνσεις του αρχείου αναίρεσης δείχνουν σε άλλα pixel — το δαχτυλίδι έχει
; γυρίσει από κάτω τους.

UI_LOOK     equ 0
UI_MENU     equ 1
UI_PLACE    equ 2

UI_MARGIN   equ 1                       ; tiles από το χείλος πριν σκρολάρει
PEN_CUR     equ 15                      ; ροζ — το λευκό χανόταν πάνω στα χείλη
                                    ; των διαδρόμων, που είναι κι αυτά λευκά
PEN_OK      equ 9                       ; έντονο πράσινο — επιτρέπεται
PEN_NO      equ 8                       ; έντονο κόκκινο — δεν επιτρέπεται

; ---------------------------------------------------------------------------
; ui_init — κέρσορας στο κέντρο του κόσμου, κατάσταση LOOK.
; ---------------------------------------------------------------------------
ui_init:
        xor     a
        ld      (cur_hx),a
        ld      (cur_hy),a
        ld      (ui_state),a
        ld      (ui_sel),a
        call    gh_reset
        call    ui_center
        call    view_draw
        call    hud_draw
        call    ui_show
        ret

; ui_center — η κάμερα με τον κέρσορα στη μέση του κάδρου.
ui_center:
        ld      a,(cur_hx)
        sra     a
        sub     VIEW_TW/2
        ld      (cam_tx),a
        ld      a,(cur_hy)
        sra     a
        sub     VIEW_TH/2
        ld      (cam_ty),a
        ret

; ---------------------------------------------------------------------------
; ui_tick — ένα καρέ εισόδου.
; ---------------------------------------------------------------------------
ui_tick:
        call    in_read
        ld      a,A_HOME
        call    in_hit
        jr      z,uit_state
        call    ui_hide
        xor     a
        ld      (cur_hx),a
        ld      (cur_hy),a
        call    ui_center
        call    view_draw
        call    hud_draw
        jp      ui_show
uit_state:
        ld      a,(ui_state)
        cp      UI_MENU
        jp      z,uist_menu
        cp      UI_PLACE
        jp      z,uist_place
        ; fall through — UI_LOOK

; --- LOOK ------------------------------------------------------------------
uist_look:
        call    ui_move                 ; -> NZ αν κουνήθηκε
        ld      a,A_MENU
        call    in_hit
        ret     z
        call    ui_hide
        ld      a,UI_MENU
        ld      (ui_state),a
        ld      a,(ui_sel)
        call    bd_select
        jp      ui_show

; --- MENU ------------------------------------------------------------------
uist_menu:
        ld      a,A_CANCEL
        call    in_hit
        jr      z,uim_fire
        call    ui_hide
        xor     a
        ld      (ui_state),a
        jp      ui_show
uim_fire:
        ld      a,A_FIRE
        call    in_hit
        jr      z,uim_lr
        call    ui_hide
        ld      a,UI_PLACE
        ld      (ui_state),a
        jp      ui_show
uim_lr:
        ld      a,A_RIGHT
        call    in_hit
        jr      z,uim_left
        ld      a,(ui_sel)
        inc     a
        cp      BLD_N
        jr      c,uim_set
        xor     a
        jr      uim_set
uim_left:
        ld      a,A_LEFT
        call    in_hit
        ret     z
        ld      a,(ui_sel)
        or      a
        jr      nz,uim_dec
        ld      a,BLD_N
uim_dec:
        dec     a
uim_set:
        ld      (ui_sel),a
        call    ui_hide
        ld      a,(ui_sel)
        call    bd_select
        jp      ui_show

; --- PLACE -----------------------------------------------------------------
uist_place:
        ld      a,A_CANCEL
        call    in_hit
        jr      z,uip_fire
        call    ui_hide
        ld      a,UI_MENU
        ld      (ui_state),a
        jp      ui_show
uip_fire:
        ld      a,A_FIRE
        call    in_hit
        jr      z,uip_move
        call    ui_validate
        or      a
        ret     nz                      ; άκυρη θέση — το FIRE δεν κάνει τίποτα
        call    bd_afford
        ret     nz
        call    ui_hide
        call    bd_commit
        cp      255
        jr      z,uip_nospace
        call    view_draw               ; το νέο αντικείμενο μπαίνει στη σκηνή
uip_nospace:
        call    hud_draw
        jp      ui_show
uip_move:
        jp      ui_move

; ---------------------------------------------------------------------------
; ui_move — κίνηση κέρσορα ένα tile, με την κάμερα να ακολουθεί.
; Out: NZ αν κουνήθηκε.
; ---------------------------------------------------------------------------
; Η ΚΙΝΗΣΗ ΔΙΑΒΑΖΕΙ ΣΤΑΘΜΗ, ΟΧΙ ΑΚΜΗ — σε αντίθεση με τα κουμπιά.
;
; Ενας κύκλος ui_tick μπορεί να κρατήσει 3 ως 9 frames όταν σκρολάρει η κάμερα
; ([§8.2]). Με ακμή, ένα πάτημα συντομότερο από τον κύκλο ΧΑΝΕΤΑΙ εντελώς — και
; αυτό ακριβώς έδειξε η δοκιμή: δώδεκα πατήματα έδωσαν ένδεκα βήματα. Με στάθμη
; το κρατημένο πλήκτρο επαναλαμβάνει, όπως περιμένει κανείς από κέρσορα, και ο
; ρυθμός επανάληψης είναι ο ρυθμός του κύκλου.
ui_move:
        xor     a
        ld      (ui_dx),a
        ld      (ui_dy),a
        ld      a,A_LEFT
        call    in_held
        jr      z,um_r
        ld      a,-2
        ld      (ui_dx),a
um_r:
        ld      a,A_RIGHT
        call    in_held
        jr      z,um_u
        ld      a,2
        ld      (ui_dx),a
um_u:
        ld      a,A_UP
        call    in_held
        jr      z,um_d
        ld      a,-2
        ld      (ui_dy),a
um_d:
        ld      a,A_DOWN
        call    in_held
        jr      z,um_go
        ld      a,2
        ld      (ui_dy),a
um_go:
        ld      a,(ui_dx)
        ld      hl,ui_dy
        or      (hl)
        ret     z                       ; τίποτα δεν πατήθηκε
        call    ui_hide
        ld      a,(ui_dx)
        ld      hl,cur_hx
        add     a,(hl)
        ld      (hl),a
        ld      a,(ui_dy)
        ld      hl,cur_hy
        add     a,(hl)
        ld      (hl),a
        call    ui_follow
        call    ui_show
        ld      a,1
        or      a
        ret

; ---------------------------------------------------------------------------
; ui_follow — η κάμερα κρατά το αποτύπωμα μέσα στο κάδρο, με ένα tile
; περιθώριο, και σκρολάρει ΜΕ ΛΩΡΙΔΑ — όχι με πλήρη σχεδίαση.
; ---------------------------------------------------------------------------
ui_follow:
        call    ui_rect
uif_x:
        ld      a,(ui_tx)
        ld      hl,cam_tx
        sub     (hl)
        bit     7,a                     ; ο κέρσορας αριστερά της κάμερας
        jr      nz,uif_west
        cp      UI_MARGIN
        jr      nc,uif_x2
uif_west:
        ld      a,3                     ; δύση
        call    view_scroll
        jr      uif_x
uif_x2:
        ld      a,(ui_tx)
        ld      hl,ui_w
        add     a,(hl)
        ld      hl,cam_tx
        sub     (hl)
        cp      VIEW_TW - UI_MARGIN + 1
        jr      c,uif_y
        ld      a,1                     ; ανατολή
        call    view_scroll
        jr      uif_x2
uif_y:
        ld      a,(ui_ty)
        ld      hl,cam_ty
        sub     (hl)
        bit     7,a
        jr      nz,uif_north
        cp      UI_MARGIN
        jr      nc,uif_y2
uif_north:
        ld      a,0                     ; βορράς
        call    view_scroll
        jr      uif_y
uif_y2:
        ld      a,(ui_ty)
        ld      hl,ui_h
        add     a,(hl)
        ld      hl,cam_ty
        sub     (hl)
        cp      VIEW_TH - UI_MARGIN + 1
        ret     c
        ld      a,2                     ; νότος
        call    view_scroll
        jr      uif_y2

; ---------------------------------------------------------------------------
; ui_rect — το ορθογώνιο που δείχνει ο κέρσορας, σε tiles.
; Στο LOOK είναι ένα tile· στο PLACE το αποτύπωμα του αντικειμένου.
; ---------------------------------------------------------------------------
ui_rect:
        ld      a,(ui_state)
        cp      UI_PLACE
        jr      z,uir_foot
        ld      a,(cur_hx)
        sra     a
        ld      (ui_tx),a
        ld      a,(cur_hy)
        sra     a
        ld      (ui_ty),a
        ld      a,1
        ld      (ui_w),a
        ld      (ui_h),a
        ret
uir_foot:
        call    bd_rect
        ld      a,(bd_tx)
        ld      (ui_tx),a
        ld      a,(bd_ty)
        ld      (ui_ty),a
        ld      a,(bd_w)
        ld      (ui_w),a
        ld      a,(bd_h)
        ld      (ui_h),a
        ret

; ---------------------------------------------------------------------------
; ui_validate — Out: A = 0 αν η θέση επιτρέπεται.
; ---------------------------------------------------------------------------
ui_validate:
        ld      a,(ui_state)
        cp      UI_PLACE
        ld      a,0
        ret     nz
        ld      bc,GA_PORT + PAGE_B4
        out     (c),c
        call    bd_check
        push    af
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        pop     af
        ret

; ---------------------------------------------------------------------------
; ui_show / ui_hide — το φάντασμα πάνω στη σκηνή, και πίσω.
; ---------------------------------------------------------------------------
ui_hide:
        jp      gh_undo

ui_show:
        call    ui_rect
        ld      a,(ui_state)
        cp      UI_PLACE
        jr      nz,uis_pen
        call    ui_validate
        ld      (ui_bad),a
uis_pen:
        ld      a,(ui_state)
        cp      UI_PLACE
        ld      a,PEN_CUR
        jr      nz,uis_set
        ld      a,(ui_bad)
        or      a
        ld      a,PEN_OK
        jr      z,uis_set
        ld      a,PEN_NO
uis_set:
        call    gh_setpen
        ; --- το πλαίσιο, σε συντεταγμένες οθόνης ---
        ld      a,(ui_tx)
        call    ui_sxt
        ld      (gh_bx),hl
        ld      a,(ui_ty)
        call    ui_syt
        ld      (gh_by),hl
        ld      a,(ui_w)
        add     a,a
        add     a,a
        ld      (gh_bw),a
        ld      a,(ui_h)
        add     a,a
        add     a,a
        add     a,a
        add     a,a
        ld      (gh_bh),a
        call    gh_box
        ; --- τα άκυρα tiles ---
        ld      a,(ui_state)
        cp      UI_PLACE
        jp      nz,ui_panel
        ld      a,(ui_bad)
        or      a
        jp      z,ui_panel
        ld      a,PEN_NO
        call    gh_setpen
        xor     a
        ld      (uis_row),a
uis_rl:
        ld      a,(uis_row)
        ld      l,a
        ld      h,0
        ld      de,bd_bad
        add     hl,de
        ld      a,(hl)
        or      a
        jr      z,uis_rn
        ld      c,a
        xor     a
        ld      (uis_col),a
uis_cl:
        ld      a,c
        rrca
        ld      c,a
        jr      nc,uis_cn
        push    bc
        ld      a,(ui_tx)
        ld      hl,uis_col
        add     a,(hl)
        call    ui_sxt
        ld      (gh_x),hl
        ld      a,(ui_ty)
        ld      hl,uis_row
        add     a,(hl)
        call    ui_syt
        ld      (gh_y),hl
        call    gh_mark
        pop     bc
uis_cn:
        ld      a,(uis_col)
        inc     a
        ld      (uis_col),a
        ld      hl,ui_w
        cp      (hl)
        jr      nz,uis_cl
uis_rn:
        ld      a,(uis_row)
        inc     a
        ld      (uis_row),a
        ld      hl,ui_h
        cp      (hl)
        jr      nz,uis_rl
        jp      ui_panel

; ui_sxt / ui_syt — tile -> οθόνη, προσημασμένα 16 bit.
ui_sxt:
        call    ob_sext
        add     hl,hl
        add     hl,hl
        push    hl
        ld      a,(cam_tx)
        call    ob_sext
        add     hl,hl
        add     hl,hl
        ex      de,hl
        pop     hl
        or      a
        sbc     hl,de
        ret
ui_syt:
        call    ob_sext
        add     hl,hl
        add     hl,hl
        add     hl,hl
        add     hl,hl
        push    hl
        ld      a,(cam_ty)
        call    ob_sext
        add     hl,hl
        add     hl,hl
        add     hl,hl
        add     hl,hl
        ex      de,hl
        pop     hl
        or      a
        sbc     hl,de
        ret

; ---------------------------------------------------------------------------
; ui_panel — οι σειρές 3-4 του HUD: τι κρατάς και τι σου λέει το έδαφος.
; ---------------------------------------------------------------------------
ui_panel:
        ld      a,3
        call    hud_go
        ld      a,(ui_state)
        or      a
        jr      nz,uip_item
        ld      hl,t_look
        call    hud_text
        ld      b,40-19
        call    hud_blank
        jr      uip_row4
uip_item:
        ld      a,'<'
        call    hud_char
        ld      b,1
        call    hud_blank
        ld      hl,(bd_name)
        call    hud_text
        ld      b,1
        call    hud_blank
        ld      a,'>'
        call    hud_char
        ld      b,2
        call    hud_blank
        ld      hl,t_fe
        call    hud_text
        ld      a,(bd_metal)
        ld      l,a
        ld      h,0
        ld      b,3
        call    hud_num
        ld      b,2
        call    hud_blank
        ld      hl,t_bi
        call    hud_text
        ld      a,(bd_biop)
        ld      l,a
        ld      h,0
        ld      b,3
        call    hud_num
        ld      b,40-31
        call    hud_blank
uip_row4:
        ld      a,4
        call    hud_go
        ld      a,(ui_state)
        cp      UI_PLACE
        jr      z,uip_st
        ld      hl,t_keys
        call    hud_text
        ld      b,40-24
        jp      hud_blank
uip_st:
        ld      a,(ui_bad)
        or      a
        jr      nz,uip_blocked
        call    bd_afford
        jr      nz,uip_poor
        ld      hl,t_ok
        jr      uip_say
uip_blocked:
        ld      hl,t_block
        jr      uip_say
uip_poor:
        ld      hl,t_poor
uip_say:
        call    hud_text
        ld      b,40-20
        jp      hud_blank

t_look:     db "LOOK  SPACE=BUILD  ",0
t_keys:     db "FIRE=PLACE ESC=BACK ",0
t_ok:       db "READY  FIRE TO BUILD",0
t_block:    db "BLOCKED             ",0
t_poor:     db "NOT ENOUGH MATERIAL ",0
t_fe:       db "FE",0
t_bi:       db "BI",0

ui_state:   db 0
ui_sel:     db 0
ui_tx:      db 0
ui_ty:      db 0
ui_w:       db 1
ui_h:       db 1
ui_bad:     db 0
ui_dx:      db 0
ui_dy:      db 0
uis_row:    db 0
uis_col:    db 0
cur_hx:     db 0
cur_hy:     db 0
