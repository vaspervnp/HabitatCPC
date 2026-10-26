; ---------------------------------------------------------------------------
; tpage.asm — οι σελίδες του tutorial (βήμα 175, DESIGN §9.6). ΣΤΗΝ ΤΡΑΠΕΖΑ 7,
; μετά τα κείμενα και το src/st7.asm, στο ίδιο αρχείο του δίσκου (TEXT.BIN):
; τρέχει με την 7 στο παράθυρο και δεν σελιδοποιεί ποτέ. Ό,τι καλεί στην 0
; και στη 2 δεν σελιδοποιεί κι αυτό: snd_off, is_m1, hw_clear, in_scan και ο
; οδηγός του δίσκου (src/fdc.asm, στο SV_ORG του GH_BUF από το sv_ovl).
;
; Ο ΠΑΙΚΤΗΣ: «Το tutorial δεν έχει οδηγίες. Βάλε να έχει οδηγίες.
; Χρησιμοποίησε και αρχείο στην δισκέττα αν χρειάζεσαι για τα κείμενά του.»
; Διάλεξε μια σελίδα σε κάθε βήμα, σε όλη την οθόνη όπως η βοήθεια του «?»:
; τι χτίζεις, γιατί, ποια πλήκτρα, τι να κοιτάς. Οποιοδήποτε πλήκτρο γυρίζει
; στο παιχνίδι, η γραμμή κάτω από τα κουμπιά μένει, και το «?» την ξαναδείχνει.
;
; ΤΑ ΚΕΙΜΕΝΑ ΕΙΝΑΙ ΣΤΟΝ ΔΙΣΚΟ, στο TUTOR.TXT (tools/tupages.py από το
; src/tupages.txt): ~6 KB, πολύ περισσότερα από όσα χωρούν στη μνήμη. Κάθε
; σελίδα διαβάζεται όταν δείχνεται: ο κατάλογος του δίσκου (track 0) δίνει
; τα blocks του αρχείου, και το tp_idx (build/tupages.asm) πού ξεκινά η
; σελίδα μέσα του. Ενας τομέας τη φορά, στα 512 bytes της κεφαλίδας του
; σωσίματος (SV_HDR, το GH_BUF με τον κέρσορα σβηστό).
;
; Η ΜΟΡΦΗ: «@» αρχή σελίδας, «*» λευκά / πράσινα, CR νέα γραμμή, LF τίποτα,
; #1A τέλος αρχείου. Ο τίτλος είναι η πρώτη γραμμή, λευκός με τους
; αστερίσκους του, και μετά μια κενή.
;
; ΧΩΡΙΣ ΔΙΣΚΟ — βγήκε από τον οδηγό, ή δεν είναι αυτός του παιχνιδιού — η
; σελίδα λέει πού είναι, και το πλήκτρο γυρίζει πίσω όπως πάντα.
; ---------------------------------------------------------------------------

TP_COL      equ 2                       ; οι στήλες 2-77 (tools/tupages.py: TP_W 76)
TP_TROW     equ 1                       ; ο τίτλος· το σώμα από τη σειρά 3
TP_FROW     equ 24                      ; το υποσέλιδο, όπως της βοήθειας
TP_BUF      equ SV_HDR                  ; ένας τομέας
TP_WHITE    equ #FF                     ; pen 3 όπου ο γλύφος έχει pixel
TP_GREEN    equ #0F                     ; pen 2, όπως το hp_green
TP_KQ       equ 3                       ; το «?», το πλήκτρο /: γραμμή 3 του πίνακα,
TP_KQM      equ #40                     ; bit 6 (0 = πατημένο)
        include "../build/tupages.asm"  ; TP_N, tp_idx

; tp_show — A = σελίδα: 0 η εισαγωγή (και μετά η 1), #FF η σελίδα του βήματος
; (tp_cur). Γυρίζει με NZ αν το πλήκτρο που την έκλεισε ήταν το «?», με τις
; διακοπές κλειστές και την οθόνη όλη Mode 1: το ξαναζωγραφίζει ο καλών
; (hp_back, src/help.asm).
tp_show:
        inc     a
        jr      nz,tps_pg
        ld      a,(tp_cur)
        inc     a
tps_pg:
        dec     a
        ld      (tp_pg),a
        call    snd_off
        di
        call    fdc_on
        call    tp_find                 ; Z: βρέθηκε, τα blocks στο tp_blk
        ld      (tp_ok),a
tps_one:
        call    is_m1
        call    hw_clear
        ld      hl,-HUD_TOPB + TP_TROW * 80 + TP_COL
        call    tp_line
        ld      a,(tp_ok)
        or      a
        jr      z,tps_disc
        ld      hl,tp_nodisc
        call    tp_str
        jr      tps_foot
tps_disc:
        ld      a,(tp_pg)
        add     a,a
        ld      e,a
        ld      d,0
        ld      hl,tp_idx
        add     hl,de
        ld      e,(hl)
        inc     hl
        ld      d,(hl)
        ld      (tp_off),de
        ld      a,#FF
        ld      (tp_k),a                ; κανένας τομέας ακόμη
tps_ch:
        call    tp_get                  ; C: ο δίσκος δεν τον έδωσε
        jr      c,tps_foot
        cp      '@'                     ; η επόμενη σελίδα
        jr      z,tps_foot
        cp      #1A                     ; το τέλος του αρχείου
        jr      z,tps_foot
        call    tp_put
        jr      tps_ch
tps_foot:
        ld      hl,-HUD_TOPB + TP_FROW * 80 + TP_COL
        call    tp_line
        ld      hl,tp_foot
        call    tp_str
        call    tp_key                  ; NZ: το «?»
        jr      nz,tps_out
        ld      hl,tp_pg
        ld      a,(hl)
        inc     (hl)                    ; μετά την εισαγωγή το βήμα 1
        or      a
        jr      z,tps_one
        xor     a                       ; Z: όχι το «?»
tps_out:
        push    af
        call    fdc_off
        ld      hl,tp_pg
        ld      (hl),#FF                ; καμία σελίδα: το βλέπουν οι δοκιμές και ο tools/play.py
        pop     af
        ret

; tp_line — HL = θέση (από το cam_p, όπως το hp_go): εκεί η αρχή της γραμμής,
; πράσινα.
tp_line:
        ld      (tp_ls),hl
        ld      (tp_at),hl
        ld      a,TP_GREEN
        ld      (tp_mask),a
        ret

; tp_str — HL = κείμενο εδώ, ως το 0, με τους κανόνες του αρχείου.
tp_str:
        ld      a,(hl)
        or      a
        ret     z
        inc     hl
        push    hl
        call    tp_put
        pop     hl
        jr      tp_str

; tp_put — A = ένας χαρακτήρας του κειμένου: γλύφος, «*», CR ή τίποτα.
tp_put:
        cp      13
        jr      z,tpp_cr
        cp      '*'
        jr      z,tpp_ink
        sub     32
        ret     c                       ; το LF, και ό,τι δεν είναι γράμμα
        ld      l,a
        ld      h,0
        add     hl,hl
        add     hl,hl
        add     hl,hl
        ld      de,G_font_m1
        add     hl,de
        ex      de,hl                   ; DE = ο γλύφος, στην 7 που είναι μέσα
        ld      hl,(tp_at)
        push    hl
        inc     hl
        ld      (tp_at),hl
        pop     hl
        ld      bc,(cam_p)
        add     hl,bc
        ld      a,h
        and     7                       ; το δαχτυλίδι των 2 KB, όπως το hg_p
        or      SCR_BASE / 256
        ld      h,a
        ld      a,(tp_mask)
        ld      c,a
        ld      b,8
tpp_ln:
        ld      a,(de)
        inc     e                       ; ο γλύφος δεν διασχίζει σελίδα (hp_green)
        and     c
        ld      (hl),a
        ld      a,h
        add     a,8
        ld      h,a
        djnz    tpp_ln
        ret
tpp_ink:
        ld      a,(tp_mask)
        xor     TP_WHITE ^ TP_GREEN
        ld      (tp_mask),a
        ret
tpp_cr:
        ld      hl,(tp_ls)
        ld      de,80
        add     hl,de
        jr      tp_line

; tp_get — A = το επόμενο byte του αρχείου, NC. C αν ο τομέας του δεν διαβάστηκε.
tp_get:
        ld      hl,(tp_off)
        ld      a,h
        srl     a                       ; ο τομέας μέσα στο αρχείο: off >> 9
        ld      hl,tp_k
        cp      (hl)
        call    nz,tp_read
        ret     c
        ld      hl,(tp_off)
        ld      a,h
        and     1
        ld      h,a
        ld      de,TP_BUF
        add     hl,de
        ld      a,(hl)
        ld      hl,(tp_off)
        inc     hl
        ld      (tp_off),hl
        or      a                       ; NC
        ret

; tp_read — A = τομέας μέσα στο αρχείο: στο TP_BUF. C αν δεν διαβάστηκε.
; Το block από τον κατάλογο, ο λογικός τομέας του δίσκου 2 x block + μισό, και
; από αυτόν το track (/ 9) και το id (#C1 + υπόλοιπο), όπως ο αναγνώστης του
; φορτωτή (src/boot.asm).
tp_read:
        ld      (tp_k),a
        ld      c,a
        srl     a                       ; το block μέσα στο αρχείο
        cp      16
        ccf
        ret     c                       ; πέρα από την πρώτη έκταση
        ld      e,a
        ld      d,0
        ld      hl,tp_blk
        add     hl,de
        ld      l,(hl)
        ld      h,d
        add     hl,hl
        ld      a,c
        and     1
        or      l
        ld      l,a                     ; HL = ο τομέας του δίσκου
        ld      de,-9
        ld      b,-1
tpr_div:
        inc     b
        add     hl,de                   ; C όσο ήταν τουλάχιστον 9
        jr      c,tpr_div
        ld      a,l                     ; L = υπόλοιπο - 9
        add     a,#C1 + 9
        ld      (fd_sect),a
        ld      a,b
        call    fdc_seek
        ld      hl,TP_BUF
        call    fdc_rsect               ; Z (και NC) αν πέτυχε
        ret     z
        scf
        ret

; tp_find — ο κατάλογος, οι τομείς #C1-#C4 του track 0: η εγγραφή του
; TUTOR.TXT (χρήστης 0, έκταση 0), και τα blocks της στο tp_blk. Z αν βρέθηκε.
tp_find:
        xor     a
        call    fdc_seek
        ld      a,#C1
tpf_sec:
        ld      (fd_sect),a
        ld      hl,TP_BUF
        call    fdc_rsect
        ret     nz                      ; ο δίσκος δεν απάντησε
        ld      hl,TP_BUF
        ld      b,512 / 32
tpf_ent:
        push    bc
        push    hl
        ld      de,tp_name
        ld      b,13                    ; χρήστης, όνομα και τύπος, έκταση
tpf_cmp:
        ld      a,(de)
        cp      (hl)
        jr      nz,tpf_no
        inc     de
        inc     hl
        djnz    tpf_cmp
        ld      de,16 - 13
        add     hl,de                   ; τα blocks, από το byte 16
        ld      de,tp_blk
        ld      bc,16
        ldir
        pop     hl
        pop     bc
        xor     a                       ; Z
        ret
tpf_no:
        pop     hl
        ld      de,32
        add     hl,de
        pop     bc
        djnz    tpf_ent
        ld      a,(fd_sect)
        inc     a
        cp      #C5
        jr      nz,tpf_sec
        or      a                       ; NZ: δεν είναι σε αυτόν τον δίσκο
        ret

; tp_key — περιμένει να αφεθεί ό,τι κρατιέται (το «?» που την άνοιξε, το
; FIRE που έχτισε), ένα πλήκτρο ή το χειριστήριο, και να αφεθεί κι αυτό:
; αλλιώς το ίδιο πάτημα θα έκανε κάτι στο παιχνίδι (όπως το hp_up). NZ αν
; ήταν το «?».
tp_key:
        call    tpk_up
tpk_dn:
        call    tp_any
        jr      z,tpk_dn
        ld      a,(key_now + TP_KQ)
        cpl
        and     TP_KQM
        push    af
        call    tpk_up
        pop     af
        ret
tpk_up:
        call    tp_any
        jr      nz,tpk_up
        ret

; tp_any — μια σάρωση, και NZ αν κάτι είναι πατημένο (όπως το hp_any).
tp_any:
        call    in_scan
        ld      hl,key_now
        ld      b,KEY_LINES
        ld      a,#FF
tpa_lp:
        and     (hl)
        inc     hl
        djnz    tpa_lp
        inc     a
        ret

tp_foot:    db "*ANY KEY*  GO ON             *?*  WHAT EVERY BUTTON DOES",0
tp_nodisc:  db "*THIS PAGE IS ON THE GAME'S DISC*",13,13
            db "PUT THE DISC BACK IN THE DRIVE, AND PRESS *?* TO SEE IT.",0
tp_name:    db 0,"TUTOR   TXT",0
tp_cur:     db 1                        ; η σελίδα του βήματος: την γράφει το tuo_go
tp_pg:      db #FF                      ; η σελίδα που δείχνεται, #FF καμία
tp_ok:      db 0
tp_k:       db 0
tp_mask:    db 0
tp_off:     dw 0
tp_at:      dw 0
tp_ls:      dw 0
tp_blk:     ds 16
