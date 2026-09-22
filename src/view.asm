; view.asm — η κάμερα και η πλήρης σχεδίαση του κάδρου (DESIGN §8.1, §8.2).
;
; Η κάμερα ΕΙΝΑΙ το offset του CRTC. Το (cam_tx, cam_ty) είναι το πάνω-αριστερά
; ορατό tile, και από αυτό βγαίνουν δύο αριθμοί:
;
;   cam_off  λέξεις offset για τα R12/R13 — το tile (-64,-64) είναι το 0
;   cam_p    το ίδιο σε bytes, που μπαίνει σε κάθε υπολογισμό διεύθυνσης
;
;       cam_off = ((tx+64)*2 + (ty+64)*80) & #3FF
;
; Το 2 και το 80 δεν είναι αυθαίρετα: μία λέξη offset είναι 2 bytes = 4 pixel
; του Mode 0 (μισό tile), και μία σειρά χαρακτήρων είναι R1 = 40 λέξεις, άρα
; ένα tile ύψους 16 γραμμών είναι 80. Και τα δύο ΖΥΓΑ — γι' αυτό το cam_p είναι
; πάντα πολλαπλάσιο του 4 και ΚΑΝΕΝΑ tile δεν πατάει το τύλιγμα του δαχτυλιδιού
; στη μέση του (§8.2 του screen.asm).

CRTC_SEL    equ #BC00
CRTC_VAL    equ #BD00
PLAY_PAGE   equ 3

; ---------------------------------------------------------------------------
; view_cam — ξαναϋπολογίζει cam_off / cam_p από το (cam_tx, cam_ty) και
; γράφει τα R12/R13. Καμία επανασχεδίαση: αυτό είναι όλο το σκρολάρισμα.
; ---------------------------------------------------------------------------
view_cam:
        ld      a,(cam_tx)
        add     a,64
        ld      l,a
        ld      h,0
        add     hl,hl                   ; (tx+64)*2
        ex      de,hl
        ld      a,(cam_ty)
        add     a,64
        ld      l,a
        ld      h,0
        add     hl,hl
        add     hl,hl
        add     hl,hl
        add     hl,hl                   ; *16
        ld      b,h
        ld      c,l
        add     hl,hl                   ; *32
        add     hl,hl                   ; *64
        add     hl,bc                   ; *80
        add     hl,de
        ld      a,h
        and     3
        ld      h,a                     ; & #3FF
        ld      (cam_off),hl
        add     hl,hl                   ; σε bytes
        ld      (cam_p),hl
        ; --- R12 / R13 ---
        ld      hl,(cam_off)
        ld      a,h
        or      PLAY_PAGE*16
        ld      b,a
        ld      c,l
        push    bc
        ld      bc,CRTC_SEL + 12
        out     (c),c
        pop     bc
        push    bc
        ld      a,b
        ld      bc,CRTC_VAL
        ld      c,a
        out     (c),c
        ld      bc,CRTC_SEL + 13
        out     (c),c
        pop     bc
        ld      a,c
        ld      bc,CRTC_VAL
        ld      c,a
        out     (c),c
        ret

; ---------------------------------------------------------------------------
; view_scroll — ΕΝΑ tile προς μία κατεύθυνση (0 βορράς, 1 ανατολή, 2 νότος,
; 3 δύση). Ολο το σκρολάρισμα είναι δύο εγγραφές στον CRTC· ό,τι ακολουθεί
; αφορά μόνο τη ΛΩΡΙΔΑ που μόλις μπήκε στο κάδρο.
;
; Η προηγούμενη εικόνα ΔΕΝ μετακινείται στη μνήμη. Το περιεχόμενο στη θέση p
; εμφανίζεται στο (p - cam_p), οπότε μια αύξηση 4 bytes στο cam_p το δείχνει
; τέσσερα bytes αριστερότερα — και η αριστερή στήλη κάθε σειράς γίνεται η δεξιά
; στήλη της από πάνω. Αυτή ακριβώς είναι η λωρίδα που ξαναγράφεται.
; ---------------------------------------------------------------------------
view_scroll:
        and     3
        ld      l,a
        ld      h,0
        ld      d,h
        ld      e,l
        add     hl,hl
        add     hl,de
        add     hl,hl                   ; dir*6
        ld      de,vs_tab
        add     hl,de
        ld      a,(cam_tx)
        add     a,(hl)
        ld      (cam_tx),a
        inc     hl
        ld      a,(cam_ty)
        add     a,(hl)
        ld      (cam_ty),a
        inc     hl
        ld      a,(hl)
        ld      (td_c0),a
        inc     hl
        ld      a,(hl)
        ld      (td_r0),a
        inc     hl
        ld      a,(hl)
        ld      (td_nc),a
        inc     hl
        ld      a,(hl)
        ld      (td_nr),a
        call    view_cliprect
        call    view_cam
        ld      bc,GA_PORT + PAGE_B4
        out     (c),c
        call    tile_draw_rect
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        call    ob_draw_all
        jp      ob_clip_full

; view_cliprect — το παράθυρο σχεδίασης από το ορθογώνιο tiles (td_c0..td_nr).
view_cliprect:
        ld      a,(td_c0)
        add     a,a
        add     a,a
        ld      (clip_x0),a
        ld      c,a
        ld      a,(td_nc)
        add     a,a
        add     a,a
        add     a,c
        ld      (clip_x1),a
        ld      a,(td_r0)
        add     a,a
        add     a,a
        add     a,a
        add     a,a
        ld      (clip_y0),a
        ld      c,a
        ld      a,(td_nr)
        add     a,a
        add     a,a
        add     a,a
        add     a,a
        add     a,c
        ld      (clip_y1),a
        ret

; dtx, dty, c0, r0, nc, nr — ανά κατεύθυνση
vs_tab:
        db      0,-1,  0,0,          VIEW_TW,1         ; βορράς
        db      1, 0,  VIEW_TW-1,0,  1,VIEW_TH         ; ανατολή
        db      0, 1,  0,VIEW_TH-1,  VIEW_TW,1         ; νότος
        db     -1, 0,  0,0,          1,VIEW_TH         ; δύση

; ---------------------------------------------------------------------------
; view_draw — έδαφος και μετά αντικείμενα, μέσα στο τρέχον clip.
; Το έδαφος θέλει την τράπεζα 4· το πέρασμα αντικειμένων σελιδοποιεί μόνο του.
; ---------------------------------------------------------------------------
view_draw:
        call    ob_touch
        call    view_cam
        ld      bc,GA_PORT + PAGE_B4
        out     (c),c
        call    tile_draw_all
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        jp      ob_draw_all

; --- μεταβλητές ------------------------------------------------------------
cam_off:    dw 0                ; λέξεις offset του CRTC (0..1023)
