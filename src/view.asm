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
; view_draw — έδαφος και μετά αντικείμενα, μέσα στο τρέχον clip.
; Το έδαφος θέλει την τράπεζα 4· το πέρασμα αντικειμένων σελιδοποιεί μόνο του.
; ---------------------------------------------------------------------------
view_draw:
        call    view_cam
        ld      bc,GA_PORT + PAGE_B4
        out     (c),c
        call    tile_draw_all
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        jp      ob_draw_all

; --- μεταβλητές ------------------------------------------------------------
cam_off:    dw 0                ; λέξεις offset του CRTC (0..1023)
