; input.asm — πληκτρολόγιο και χειριστήριο (DESIGN §9.1).
;
; Το πληκτρολόγιο του CPC δεν διαβάζεται από θύρα: κρέμεται από τη ΘΥΡΑ Α του
; PPI, που την οδηγεί ο ήχος. Η σειρά είναι αυστηρή και αν κάποιο βήμα λείψει
; δεν διαβάζεται τίποτα — ή, χειρότερα, διαβάζεται σκουπίδι:
;
;   1. PPI control #82  θύρα Α ΕΞΟΔΟΣ (πάμε να γράψουμε στον ήχο)
;   2. θύρα Α  = 14     ο καταχωρητής του PSG που βλέπει το πληκτρολόγιο
;   3. θύρα C  = #C0    PSG: «επίλεξε καταχωρητή»
;   4. θύρα C  = #00    PSG: αδρανής
;   5. PPI control #92  θύρα Α ΕΙΣΟΔΟΣ
;   6. θύρα C  = #40|n  PSG: «διάβασε», με τη γραμμή n στα χαμηλά bits
;   7. in a,(#F4xx)     τα bits της γραμμής — ΜΗΔΕΝ σημαίνει πατημένο
;
; Τα bits γυρίζονται εδώ (cpl) ώστε παραπάνω να σημαίνει «πατημένο» παντού.
;
; Η ΓΡΑΜΜΗ 9 ΕΙΝΑΙ ΤΟ ΧΕΙΡΙΣΤΗΡΙΟ. Δεν χρειάζεται τίποτε άλλο: το joystick 0
; κάθεται στην ίδια μήτρα με τα πλήκτρα, οπότε «πληκτρολόγιο ΚΑΙ χειριστήριο,
; και τα δύο πλήρη» είναι ένας πίνακας με δύο στήλες, όχι δεύτερος οδηγός.

KEY_LINES   equ 10
PPI_CTRL    equ #F700
PPI_A       equ #F400
PPI_C       equ #F600

; --- οι ενέργειες, ως bits του act_now / act_hit ---
A_UP        equ 0
A_DOWN      equ 1
A_LEFT      equ 2
A_RIGHT     equ 3
A_FIRE      equ 4
A_CANCEL    equ 5
A_MENU      equ 6
A_NEXT      equ 7
A_HOME      equ 8
A_SPD1      equ 9
A_SPD2      equ 10
A_SPD3      equ 11
A_SPD4      equ 12
A_ACTIONS   equ 13

; ---------------------------------------------------------------------------
; in_scan — και οι δέκα γραμμές στο key_now. 1 = πατημένο.
; ---------------------------------------------------------------------------
in_scan:
        ld      bc,PPI_CTRL + #82
        out     (c),c
        ld      bc,PPI_A + 14
        out     (c),c
        ld      bc,PPI_C + #C0
        out     (c),c
        ld      bc,PPI_C + #00
        out     (c),c
        ld      bc,PPI_CTRL + #92
        out     (c),c
        ld      hl,key_now
        ld      e,0
isc_lp:
        ld      a,e
        or      #40
        ld      c,a
        ld      b,PPI_C/256
        out     (c),c
        ld      b,PPI_A/256
        in      a,(c)
        cpl                             ; 0 = πατημένο -> 1 = πατημένο
        ld      (hl),a
        inc     hl
        inc     e
        ld      a,e
        cp      KEY_LINES
        jr      nz,isc_lp
        ld      bc,PPI_CTRL + #82
        out     (c),c
        ld      bc,PPI_C + #00
        out     (c),c
        ret

; ---------------------------------------------------------------------------
; in_read — σαρώνει και βγάζει act_now (κρατημένα) και act_hit (μόλις πατήθηκαν).
;
; Το act_hit είναι ΑΚΜΗ, όχι στάθμη, και χωρίς αυτό κάθε πάτημα θα έτρεχε
; πενήντα φορές το δευτερόλεπτο: ένα «χτίσε» θα έχτιζε πενήντα θόλους.
; ---------------------------------------------------------------------------
in_read:
        call    in_scan
        ld      hl,1
        ld      (inr_mask),hl
        ld      hl,0
        ld      (inr_acc),hl
        ld      hl,act_src
        ld      b,A_ACTIONS
inr_lp:
        push    bc
        push    hl                      ; η αρχή της εγγραφής των 4 bytes
        ld      a,(hl)
        inc     hl
        ld      b,(hl)
        call    inr_test
        jr      nz,inr_on
        pop     hl
        push    hl
        inc     hl
        inc     hl
        ld      a,(hl)                  ; η εναλλακτική — χειριστήριο
        inc     hl
        ld      b,(hl)
        call    inr_test
        jr      z,inr_next
inr_on:
        ld      hl,(inr_acc)
        ld      de,(inr_mask)
        ld      a,l
        or      e
        ld      l,a
        ld      a,h
        or      d
        ld      h,a
        ld      (inr_acc),hl
inr_next:
        pop     hl
        ld      de,4
        add     hl,de
        ld      de,(inr_mask)
        ex      de,hl
        add     hl,hl
        ld      (inr_mask),hl
        ex      de,hl
        pop     bc
        djnz    inr_lp

        ; --- ακμή: ό,τι είναι πατημένο τώρα και δεν ήταν πριν ---
        ld      hl,(act_now)
        ld      (act_prev),hl
        ld      de,(inr_acc)
        ld      (act_now),de
        ld      a,l
        cpl
        and     e
        ld      l,a
        ld      a,h
        cpl
        and     d
        ld      h,a
        ld      (act_hit),hl
        ret

; inr_test — A = γραμμή (>=10 σημαίνει «δεν υπάρχει»), B = μάσκα.
; Out: Z αν ΔΕΝ είναι πατημένο. Διατηρεί HL και B.
inr_test:
        cp      KEY_LINES
        jr      nc,int_none
        push    hl
        ld      l,a
        ld      h,0
        ld      de,key_now
        add     hl,de
        ld      a,(hl)
        pop     hl
        and     b
        ret
int_none:
        xor     a
        ret

; ---------------------------------------------------------------------------
; in_held / in_hit — A = αριθμός ενέργειας. Out: NZ αν ισχύει.
; ---------------------------------------------------------------------------
in_held:
        ld      hl,act_now
        jr      in_bit
in_hit:
        ld      hl,act_hit
in_bit:
        cp      8
        jr      c,ib_lo
        inc     hl
        sub     8
ib_lo:
        ld      b,a
        ld      a,(hl)
        inc     b
        jr      ib_e
ib_l:   rrca
ib_e:   djnz    ib_l
        and     1
        ret

; --- η μήτρα: ενέργεια -> (γραμμή, μάσκα) πλήκτρου και χειριστηρίου ---
; Γραμμή 9 = joystick 0. Το 255 σημαίνει «δεν υπάρχει εναλλακτική».
act_src:
        db      0,#01,  9,#01           ; πάνω     — κέρσορας πάνω / joy πάνω
        db      0,#04,  9,#02           ; κάτω
        db      1,#01,  9,#04           ; αριστερά
        db      0,#02,  9,#08           ; δεξιά
        db      1,#02,  9,#10           ; FIRE     — COPY / joy fire 1
        db      8,#04,  9,#20           ; ακύρωση  — ESC / joy fire 2
        db      5,#80,255,0             ; μενού    — SPACE
        db      8,#10,255,0             ; επόμενο  — TAB
        db      5,#10,255,0             ; κέντρο   — H
        db      8,#01,255,0             ; 1 παύση
        db      8,#02,255,0             ; 2 κανονικά
        db      7,#02,255,0             ; 3 γρήγορα
        db      7,#01,255,0             ; 4 πολύ γρήγορα

key_now:    defs KEY_LINES
act_now:    dw 0
act_prev:   dw 0
act_hit:    dw 0
inr_acc:    dw 0
inr_mask:   dw 0
