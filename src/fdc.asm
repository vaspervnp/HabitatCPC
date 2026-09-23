; fdc.asm — ο ελεγκτής δισκέτας μPD765, χωρίς AMSDOS (DESIGN §11)
;
; ΓΙΑΤΙ ΟΧΙ ΤΟ AMSDOS. Την ώρα που τρέχει το παιχνίδι, ο χώρος εργασίας του
; (#A700-#BFFF) είναι δεδομένα και κώδικας της τράπεζας 2, τα ROM είναι σβηστά
; και οι διακοπές κλειστές. Δεν υπάρχει AMSDOS για να κληθεί. Ο δίσκος είναι
; δικός μας ούτως ή άλλως: οι τομείς των slots δεν ανήκουν σε αρχείο.
;
; ΤΡΕΙΣ ΘΥΡΕΣ. Το #FA7E ανάβει το μοτέρ (bit 0), το #FB7E είναι ο καταχωρητής
; κατάστασης και το #FB7F τα δεδομένα. Καμία διακοπή: η μεταφορά είναι
; polling — ο ελεγκτής ζητά byte-byte και ο Z80 προλαβαίνει άνετα (15 us ανά
; byte έναντι 27 που δίνει ο ελεγκτής στα 250 kbit/s MFM).
;
; Ο ΚΑΤΑΧΩΡΗΤΗΣ ΚΑΤΑΣΤΑΣΗΣ, bit προς bit:
;   7 RQM  ο ελεγκτής είναι έτοιμος για ένα byte
;   6 DIO  1 = θα δώσει, 0 = θέλει να πάρει
;   5 EXM  1 = είμαστε στη φάση εκτέλεσης (η μεταφορά συνεχίζεται)
;   4 CB   απασχολημένος
; Δύο `add a,a` φέρνουν το RQM και το DIO στο carry και αφήνουν το EXM στο
; πρόσημο — γι' αυτό ο βρόχος μεταφοράς δεν έχει ούτε ένα `and`.

FDC_MOTOR   equ #FA7E
FDC_PORT    equ #FB                 ; υψηλό byte: #FB7E κατάσταση, #FB7F δεδομένα

; ---------------------------------------------------------------------------
; fdc_on / fdc_off — το μοτέρ.
;
; Η καθυστέρηση είναι για πραγματικό υλικό: ο δίσκος θέλει περίπου μισό
; δευτερόλεπτο να φτάσει στις στροφές του και ο εξομοιωτής δεν το απαιτεί.
; ---------------------------------------------------------------------------
fdc_on:
        ld      bc,FDC_MOTOR
        ld      a,1
        out     (c),a
        ld      de,#0C00
fon_lp:
        dec     de
        ld      a,d
        or      e
        jr      nz,fon_lp
        ret

fdc_off:
        ld      bc,FDC_MOTOR
        xor     a
        out     (c),a
        ret

; ---------------------------------------------------------------------------
; fdc_out — στέλνει το A στον ελεγκτή.  fdc_in — παίρνει ένα byte στο A.
; Χαλάνε: BC. Το fdc_out κρατά το A.
; ---------------------------------------------------------------------------
fdc_out:
        ld      e,a
        ld      b,FDC_PORT
fo_wait:
        ld      c,#7E
        in      a,(c)
        add     a,a                     ; carry = RQM
        jr      nc,fo_wait
        add     a,a                     ; carry = DIO
        jr      c,fo_wait               ; θέλει να δώσει — δεν είναι η σειρά μας
        ld      c,#7F
        out     (c),e
        ld      a,e
        ret

fdc_in:
        ld      b,FDC_PORT
fi_wait:
        ld      c,#7E
        in      a,(c)
        add     a,a
        jr      nc,fi_wait
        add     a,a
        jr      nc,fi_wait              ; DIO=0 — δεν έχει τίποτε να δώσει
        ld      c,#7F
        in      a,(c)
        ret

; ---------------------------------------------------------------------------
; fdc_seek — A = track. Κινεί την κεφαλή και περιμένει να σταματήσει.
;
; Το SENSE INTERRUPT STATUS είναι ΔΥΟ bytes όταν υπάρχει εκκρεμής διακοπή και
; ΕΝΑ (#80, «άκυρη εντολή») όταν δεν υπάρχει. Αν διαβάσεις δεύτερο byte που
; δεν υπάρχει, κολλάς για πάντα — γι' αυτό ελέγχεται το #80 πριν.
; ---------------------------------------------------------------------------
fdc_seek:
        ld      (fd_trk),a
        ld      a,#0F                   ; SEEK
        call    fdc_out
        xor     a
        call    fdc_out                 ; drive 0, head 0
        ld      a,(fd_trk)
        call    fdc_out
        ld      b,100
fs_lp:
        push    bc
        ld      a,#08                   ; SENSE INTERRUPT STATUS
        call    fdc_out
        call    fdc_in
        ld      c,a                     ; ST0
        cp      #80
        jr      z,fs_inv
        call    fdc_in                  ; PCN — μόνο αν υπάρχει
fs_inv:
        ld      a,c
        pop     bc
        and     #20                     ; SE: η κίνηση τελείωσε
        ret     nz
        djnz    fs_lp
        ret                             ; δεν κάθεται· το διάβασμα θα το δείξει

; ---------------------------------------------------------------------------
; fdc_cmd — τα εννιά bytes της READ DATA / WRITE DATA. A = ο κωδικός.
;
; Το EOT ισούται με το R: ΕΝΑΣ τομέας ανά εντολή. Ο ελεγκτής μπορεί να
; διαβάσει ολόκληρο track με μία εντολή, αλλά τότε η μεταφορά δεν επιτρέπει
; ούτε μία σελιδοποίηση στη μέση — και εδώ τα δεδομένα αλλάζουν τράπεζα.
; ---------------------------------------------------------------------------
fdc_cmd:
        call    fdc_out                 ; εντολή (MFM)
        xor     a
        call    fdc_out                 ; drive 0, head 0
        ld      a,(fd_trk)
        call    fdc_out                 ; C
        xor     a
        call    fdc_out                 ; H
        ld      a,(fd_sect)
        call    fdc_out                 ; R
        ld      a,2
        call    fdc_out                 ; N: 512 bytes
        ld      a,(fd_sect)
        call    fdc_out                 ; EOT
        ld      a,#2A
        call    fdc_out                 ; GPL
        ld      a,#FF
        call    fdc_out                 ; DTL
        ret

; ---------------------------------------------------------------------------
; fdc_rsect / fdc_wsect — ένας τομέας από/προς το HL.
; In:  (fd_trk), (fd_sect), HL. Out: A = 0 εντάξει, αλλιώς το ST0.
; ---------------------------------------------------------------------------
fdc_rsect:
        ld      a,#46                   ; READ DATA, MFM
        call    fdc_cmd
        ld      b,FDC_PORT
fdr_w:
        ld      c,#7E
        in      a,(c)
        add     a,a
        jr      nc,fdr_w                ; RQM
        add     a,a                     ; carry = DIO, πρόσημο = EXM
        jp      p,fd_end                ; EXM=0: η μεταφορά τελείωσε
        ld      c,#7F
        in      a,(c)
        ld      (hl),a
        inc     hl
        jr      fdr_w

fdc_wsect:
        ld      a,#45                   ; WRITE DATA, MFM
        call    fdc_cmd
        ld      b,FDC_PORT
fdw_w:
        ld      c,#7E
        in      a,(c)
        add     a,a
        jr      nc,fdw_w
        add     a,a
        jp      p,fd_end
        ld      c,#7F
        ld      a,(hl)
        out     (c),a
        inc     hl
        jr      fdw_w

; fd_end — η φάση αποτελέσματος: επτά bytes, και το ST0 κρίνει.
fd_end:
        push    hl
        ld      hl,fd_res
        ld      b,7
fde_lp:
        push    bc
        push    hl
        call    fdc_in
        pop     hl
        ld      (hl),a
        inc     hl
        pop     bc
        djnz    fde_lp
        pop     hl
        ld      a,(fd_res)
        and     #C0                     ; IC: 00 = κανονικός τερματισμός
        ret

; ---------------------------------------------------------------------------
; fdc_stream — B τομείς διαδοχικά, από/προς το HL.
; In:  A = #46 ή #45, (fd_trk) = track (ήδη seeked), (fd_sect) = πρώτο id,
;      B = πλήθος τομέων, HL = μνήμη.
; Out: A = 0 εντάξει. Το HL δείχνει μετά το τελευταίο byte.
;
; Τα id είναι #C1..#C9 και μετά αλλάζει track. Η ΣΕΙΡΑ ΣΤΟΝ ΔΙΣΚΟ είναι
; πλεγμένη (C1, C6, C2, C7, ...) ώστε ο ελεγκτής να προλαβαίνει την περιστροφή·
; εμείς ζητάμε αύξοντα id και ο ελεγκτής βρίσκει τον καθένα.
; ---------------------------------------------------------------------------
fdc_stream:
        ld      (fs_cmd),a
fst_lp:
        push    bc
        ld      a,(fs_cmd)
        cp      #46
        jr      nz,fst_wr
        call    fdc_rsect
        jr      fst_chk
fst_wr:
        call    fdc_wsect
fst_chk:
        or      a
        jr      nz,fst_bad
        ld      a,(fd_sect)
        inc     a
        cp      #CA
        jr      nz,fst_same
        ld      a,(fd_trk)
        inc     a
        call    fdc_seek                ; γράφει το fd_trk
        ld      a,#C1
fst_same:
        ld      (fd_sect),a
        pop     bc
        djnz    fst_lp
        xor     a
        ret
fst_bad:
        pop     bc
        ret

fd_trk:     db 0
fd_sect:    db 0
fs_cmd:     db 0
fd_res:     ds 7
