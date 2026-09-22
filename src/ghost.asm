; ghost.asm — ό,τι ζωγραφίζεται ΠΑΝΩ από τη σκηνή και πρέπει να φύγει καθαρά.
;
; Ο κέρσορας και το φάντασμα του §9.3 κινούνται με κάθε πάτημα. Το να
; ξαναζωγραφίζεται η περιοχή από κάτω κοστίζει 3 ως 9 frames ([§8.2]) — δηλαδή
; ο κέρσορας θα κουνιόταν πέντε φορές το δευτερόλεπτο. Αντ' αυτού κρατάμε
; ΑΡΧΕΙΟ ΑΝΑΙΡΕΣΗΣ: κάθε λωρίδα που γράφεται σώζει πρώτα ό,τι έσβησε.
;
; Οι λωρίδες δεν επικαλύπτονται ποτέ μεταξύ τους — γι' αυτό οι κάθετες πλευρές
; του πλαισίου ξεκινούν κάτω από την πάνω και σταματούν πάνω από την κάτω. Αν
; επικαλύπτονταν, η δεύτερη θα έσωζε ό,τι είχε ήδη γράψει η πρώτη και η
; αναίρεση θα άφηνε το φάντασμα καρφωμένο στην οθόνη.

; το GH_LOG και το GH_BUF είναι στο const.asm

; ---------------------------------------------------------------------------
; gh_reset — άδειο αρχείο.
; ---------------------------------------------------------------------------
gh_reset:
        ld      hl,GH_BUF
        ld      (gh_ptr),hl
        ret

; ---------------------------------------------------------------------------
; gh_step — DE στο επόμενο byte, ΜΕΣΑ στο δαχτυλίδι των 2 KB.
;
; Το τύλιγμα φαίνεται μόνο όταν το χαμηλό byte γυρίσει: τότε το ph αυξήθηκε,
; και αν έγινε 0 σημαίνει ότι ήταν 7 και μπήκε στο πεδίο της γραμμής.
; ---------------------------------------------------------------------------
gh_step:
        inc     de
        ld      a,e
        or      a
        ret     nz
        ld      a,d
        and     7
        ret     nz
        ld      a,d
        sub     8
        ld      d,a
        ret

; ---------------------------------------------------------------------------
; gh_run — DE = οθόνη, B = bytes, C = τιμή. Σώζει και γράφει.
; ---------------------------------------------------------------------------
gh_run:
        ld      a,b
        or      a
        ret     z
        push    bc
        ld      hl,(gh_ptr)
        ld      a,b
        add     a,3                     ; κεφαλίδα: διεύθυνση και μήκος
        ld      c,a
        ld      b,0
        add     hl,bc
        ld      bc,GH_BUF + GH_LOG
        or      a
        sbc     hl,bc
        pop     bc
        ret     nc                      ; γεμάτο αρχείο: μη γράφεις ό,τι δεν
        ld      hl,(gh_ptr)             ; μπορείς να πάρεις πίσω
        ld      (hl),e
        inc     hl
        ld      (hl),d
        inc     hl
        ld      (hl),b
        inc     hl
gr_lp:
        ld      a,(de)
        ld      (hl),a
        inc     hl
        ld      a,c
        ld      (de),a
        push    bc
        call    gh_step
        pop     bc
        djnz    gr_lp
        ld      (gh_ptr),hl
        ret

; ---------------------------------------------------------------------------
; gh_undo — όλα πίσω, με τη σειρά που γράφτηκαν (δεν επικαλύπτονται).
; ---------------------------------------------------------------------------
gh_undo:
        ld      hl,GH_BUF
gu_lp:
        ld      de,(gh_ptr)
        ld      a,l
        cp      e
        jr      nz,gu_go
        ld      a,h
        cp      d
        jp      z,gh_reset
gu_go:
        ld      e,(hl)
        inc     hl
        ld      d,(hl)
        inc     hl
        ld      b,(hl)
        inc     hl
gu_b:
        ld      a,(hl)
        ld      (de),a
        inc     hl
        push    bc
        call    gh_step
        pop     bc
        djnz    gu_b
        jr      gu_lp

; ---------------------------------------------------------------------------
; gh_hline — οριζόντια λωρίδα, κομμένη στο κάδρο.
; In: (gh_x) 16-bit προσημασμένο, (gh_y) 16-bit, (gh_n) μήκος, (gh_pen)
; ---------------------------------------------------------------------------
gh_hline:
        ld      hl,(gh_y)
        ld      (cl_pos),hl
        ld      a,1
        ld      (cl_len),a
        ld      hl,(clip_y0)
        ld      (cl_lo),hl
        call    ob_clip
        or      a
        ret     z
        ld      a,(cl_start)
        ld      (gh_ys),a
        ld      hl,(gh_x)
        ld      (cl_pos),hl
        ld      a,(gh_n)
        ld      (cl_len),a
        ld      hl,(clip_x0)
        ld      (cl_lo),hl
        call    ob_clip
        or      a
        ret     z
        ld      a,(cl_start)
        ld      c,a
        ld      a,(gh_ys)
        call    scr_addr
        ld      a,(cl_n)
        ld      b,a
        ld      a,(gh_pen)
        ld      c,a
        jp      gh_run

; ---------------------------------------------------------------------------
; gh_vline — κάθετη λωρίδα ενός byte, (gh_nv) γραμμές.
; ---------------------------------------------------------------------------
gh_vline:
        ld      a,(gh_nv)
        or      a
        ret     z
        ld      b,a
gv_lp:
        push    bc
        ld      a,1
        ld      (gh_n),a
        call    gh_hline
        ld      hl,(gh_y)
        inc     hl
        ld      (gh_y),hl
        pop     bc
        djnz    gv_lp
        ret

; ---------------------------------------------------------------------------
; gh_box — πλαίσιο γύρω από ορθογώνιο.
; In: (gh_bx) 16-bit x σε bytes, (gh_by) 16-bit y, (gh_bw) bytes, (gh_bh) γραμμές
; ---------------------------------------------------------------------------
GH_EDGE     equ 2                       ; πάχος της οριζόντιας πλευράς

gh_box:
        ; --- πάνω ---
        ld      hl,(gh_bx)
        ld      (gh_x),hl
        ld      hl,(gh_by)
        ld      (gh_y),hl
        ld      a,(gh_bw)
        ld      (gh_n),a
        call    gh_hline
        ld      hl,(gh_y)
        inc     hl
        ld      (gh_y),hl
        ld      a,(gh_bw)
        ld      (gh_n),a
        call    gh_hline
        ; --- κάτω ---
        ld      hl,(gh_by)
        ld      a,(gh_bh)
        dec     a
        call    ob_addsx
        ld      (gh_y),hl
        ld      a,(gh_bw)
        ld      (gh_n),a
        call    gh_hline
        ld      hl,(gh_y)
        dec     hl
        ld      (gh_y),hl
        ld      a,(gh_bw)
        ld      (gh_n),a
        call    gh_hline
        ; --- αριστερά, ΧΩΡΙΣ τις γραμμές που έγραψαν οι οριζόντιες ---
        ld      a,(gh_bh)
        sub     GH_EDGE*2
        ret     c
        ret     z
        ld      (gh_nv),a
        ld      hl,(gh_bx)
        ld      (gh_x),hl
        ld      hl,(gh_by)
        ld      de,GH_EDGE
        add     hl,de
        ld      (gh_y),hl
        call    gh_vline
        ; --- δεξιά ---
        ld      hl,(gh_bx)
        ld      a,(gh_bw)
        dec     a
        call    ob_addsx
        ld      (gh_x),hl
        ld      hl,(gh_by)
        ld      de,GH_EDGE
        add     hl,de
        ld      (gh_y),hl
        jp      gh_vline

; ---------------------------------------------------------------------------
; gh_mark — γέμισμα 2 bytes x 4 γραμμές στο κέντρο ενός tile. Ενα σημάδι για
; κάθε tile που ΔΕΝ επιτρέπεται, ώστε ο παίκτης να ξέρει ΠΟΙΟ φταίει.
; In: (gh_x), (gh_y) = πάνω-αριστερά του tile
; ---------------------------------------------------------------------------
gh_mark:
        ld      hl,(gh_x)
        inc     hl
        ld      (gh_x),hl
        ld      hl,(gh_y)
        ld      de,6
        add     hl,de
        ld      (gh_y),hl
        ld      b,4
ghm_lp:
        push    bc
        ld      a,2
        ld      (gh_n),a
        call    gh_hline
        ld      hl,(gh_y)
        inc     hl
        ld      (gh_y),hl
        pop     bc
        djnz    ghm_lp
        ret

; gh_setpen — A = pen -> το byte γεμίσματος στο gh_pen.
gh_setpen:
        ld      l,a
        ld      h,0
        ld      de,hud_solid
        add     hl,de
        ld      a,(hl)
        ld      (gh_pen),a
        ret

gh_ptr:     dw 0
gh_x:       dw 0
gh_y:       dw 0
gh_n:       db 0
gh_nv:      db 0
gh_ys:      db 0
gh_pen:     db 0
gh_bx:      dw 0
gh_by:      dw 0
gh_bw:      db 0
gh_bh:      db 0
