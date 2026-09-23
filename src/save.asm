; save.asm — σώσιμο και φόρτωμα, τρία slots στον δίσκο (DESIGN §11)
;
; ΤΙ ΣΩΖΕΤΑΙ, ΚΑΙ ΓΙΑΤΙ ΤΟΣΟ ΛΙΓΟ. Τρία μπλοκ και μια κεφαλίδα:
;
;   κεφαλίδα     1 τομέας    μαγικό, έκδοση, seed, πλανήτης, κάμερα, κέρσορας
;   επίπεδο     32 τομείς    η τράπεζα 4 ολόκληρη — 16 KB, αυτούσια
;   οντότητες    9 τομείς    #6C00-#7DFF της τράπεζας 6: πράκτορες, θόλοι,
;                            δομές, διάδρομοι, κατοχή θέσεων, seed
;   κατάσταση    4 τομείς    #A400-#ABFF της τράπεζας 2: οικονομία, εργασίες,
;                            γράφος κόμβων
;
; Το επίπεδο σώζεται ΟΛΟΚΛΗΡΟ (§5.10): η αναγέννηση από το seed κοστίζει 13,5
; δευτερόλεπτα και τα 16 KB κοστίζουν τρία.
;
; ΔΕΝ σώζεται τίποτε παράγωγο: ούτε το NEXTHOP (ξαναχτίζεται από τον τροχό),
; ούτε το dome_fig (ξαναχτίζεται από τους πράκτορες), ούτε η λίστα βρώμικων,
; ούτε η θέση του τροχού. Το φόρτωμα τα ξαναφτιάχνει ΟΛΑ, με την ίδια σειρά
; που τα φτιάχνει μια νέα παρτίδα — αλλιώς δύο ίδιες καταστάσεις θα έδιναν
; διαφορετική οθόνη.
;
; ΠΟΥ ΣΤΟΝ ΔΙΣΚΟ. Οι τομείς των slots δεν ανήκουν σε αρχείο AMSDOS: ο δίσκος
; είναι δικός μας και το tools/mkdsk.py αφήνει τα tracks 24-41 άδεια. Ενα slot
; είναι 6 tracks (54 τομείς) και χρησιμοποιεί 46.

SV_T0       equ 24                  ; πρώτος track του slot 0
SV_TRACKS   equ 6
SV_SLOTS    equ 3
SV_VER      equ 1
SV_HDR      equ GH_BUF              ; 512 δανεικά bytes από το ημερολόγιο του
                                    ; φαντάσματος: σώζουμε μόνο σε κατάσταση
                                    ; LOOK, όπου δεν υπάρχει φάντασμα

; ---------------------------------------------------------------------------
; sv_save — A = slot. Out: Z και A=0 αν πέτυχε.
; ---------------------------------------------------------------------------
sv_save:
        ld      (sv_slot),a
        ld      a,#45                   ; WRITE DATA
        ld      (sv_cmd),a
        call    sv_hdr_make
        call    sv_begin
        call    sv_hdr_io
        jr      nz,sv_stop
        call    sv_body
sv_stop:
        push    af
        call    fdc_off
        pop     af
        or      a
        ret

; ---------------------------------------------------------------------------
; sv_load — A = slot. Out: Z και A=0 αν πέτυχε· η οθόνη ξαναχτίζεται.
;
; Η ΚΕΦΑΛΙΔΑ ΕΛΕΓΧΕΤΑΙ ΠΡΙΝ γραφτεί οτιδήποτε πάνω στο παιχνίδι. Ενα άδειο
; slot είναι #E5 παντού, που δεν είναι έγκυρη κατάσταση αλλά είναι απολύτως
; έγκυρα bytes: χωρίς το μαγικό, ένα «φόρτωσε» σε άδειο slot θα γέμιζε τον
; κόσμο με σκουπίδια και θα κρεμούσε την προσομοίωση.
; ---------------------------------------------------------------------------
sv_load:
        ld      (sv_slot),a
        ld      a,#46                   ; READ DATA
        ld      (sv_cmd),a
        call    sv_begin
        call    sv_hdr_io
        jr      nz,sv_stop
        call    sv_hdr_ok
        jr      nz,sv_stop
        call    sv_body
        jr      nz,sv_stop
        call    fdc_off
        jp      sv_after

; sv_begin — μοτέρ, και η κεφαλή στον πρώτο track του slot.
sv_begin:
        call    fdc_on
        ld      a,(sv_slot)
        add     a,a                     ; x2
        ld      b,a
        add     a,a                     ; x4
        add     a,b                     ; x6
        add     a,SV_T0
        call    fdc_seek
        ld      a,#C1
        ld      (fd_sect),a
        ret

sv_hdr_io:
        ld      hl,SV_HDR
        ld      b,1
        ld      a,(sv_cmd)
        jp      fdc_stream

; ---------------------------------------------------------------------------
; sv_body — τα τρία μπλοκ, καθένα με τη δική του τράπεζα στο παράθυρο.
; ---------------------------------------------------------------------------
sv_body:
        ld      ix,sv_blocks
svb_lp:
        ld      a,(ix+0)
        cp      255
        jr      z,svb_done
        or      a
        jr      z,svb_nopage
        ld      c,a
        ld      b,GA_PORT/256
        out     (c),c
svb_nopage:
        ld      l,(ix+1)
        ld      h,(ix+2)
        ld      b,(ix+3)
        ld      a,(sv_cmd)
        call    fdc_stream
        push    af
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        pop     af
        or      a
        ret     nz
        ld      de,4
        add     ix,de
        jr      svb_lp
svb_done:
        xor     a
        ret

; τράπεζα · διεύθυνση · τομείς   (0 = χωρίς σελιδοποίηση)
sv_blocks:
        db      PAGE_B4
        dw      #4000
        db      32                      ; το επίπεδο κόσμου, 16 KB
        db      PAGE_B6
        dw      #6C00
        db      9                       ; οντότητες ως και το worldinfo
        db      0
        dw      #A400
        db      4                       ; οικονομία, εργασίες, γράφος
        db      255

; ---------------------------------------------------------------------------
; sv_hdr_make / sv_hdr_ok — η κεφαλίδα.
; ---------------------------------------------------------------------------
sv_hdr_make:
        ld      hl,SV_HDR
        ld      (hl),0
        ld      de,SV_HDR + 1
        ld      bc,511
        ldir
        ld      hl,sv_magic
        ld      de,SV_HDR
        ld      bc,5
        ldir
        ld      bc,GA_PORT + PAGE_B6
        out     (c),c
        ld      hl,(G_worldinfo)
        ld      a,(G_worldinfo + 2)
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        ld      (SV_HDR + 5),hl         ; seed
        ld      (SV_HDR + 7),a          ; πλανήτης
        ld      a,(cam_tx)
        ld      (SV_HDR + 8),a
        ld      a,(cam_ty)
        ld      (SV_HDR + 9),a
        ld      a,(cur_hx)
        ld      (SV_HDR + 10),a
        ld      a,(cur_hy)
        ld      (SV_HDR + 11),a
        ld      a,(sv_slot)
        ld      (SV_HDR + 12),a
        ret

sv_hdr_ok:
        ld      hl,SV_HDR
        ld      de,sv_magic
        ld      b,5
svo_lp:
        ld      a,(de)
        cp      (hl)
        jr      nz,svo_bad
        inc     hl
        inc     de
        djnz    svo_lp
        xor     a
        ret
svo_bad:
        ld      a,#FF
        or      a
        ret

sv_magic:   db "HBT", SV_VER + '0', SV_VER

; ---------------------------------------------------------------------------
; sv_after — ό,τι ΔΕΝ σώθηκε, ξαναφτιαγμένο.
;
; Η σειρά έχει σημασία: το NEXTHOP μηδενίζεται ΠΡΙΝ ξεκινήσει ο τροχός, γιατί
; ένας πράκτορας που διαβάζει παλιό «επόμενο κόμβο» δεν διαβάζει σκουπίδι —
; διαβάζει έγκυρο γείτονα ΑΛΛΟΥ κόσμου, και φεύγει προς τα εκεί.
; ---------------------------------------------------------------------------
sv_after:
        ld      a,(SV_HDR + 7)
        call    pal_planet              ; ο κόσμος που ήρθε μπορεί να είναι άλλος πλανήτης
        ld      a,(SV_HDR + 8)
        ld      (cam_tx),a
        ld      a,(SV_HDR + 9)
        ld      (cam_ty),a
        ld      a,(SV_HDR + 10)
        ld      (cur_hx),a
        ld      a,(SV_HDR + 11)
        ld      (cur_hy),a
        ld      bc,GA_PORT + PAGE_B5
        out     (c),c
        ld      hl,#4000
        ld      (hl),0
        ld      de,#4001
        ld      bc,#3FFF
        ldir
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        call    wheel_reset
        call    rt_mark
        call    dirty_reset
        call    gh_reset
        xor     a
        ld      (ui_state),a
        ld      (ui_sel),a
        call    view_draw               ; κάνει και ob_touch και view_cam
        call    ui_hudall
        call    ui_show
        xor     a
        ret

sv_slot:    db 0
sv_cmd:     db 0
