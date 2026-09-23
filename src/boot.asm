; boot.asm — ο φορτωτής. Αυτό είναι που τρέχει το RUN"HABITAT".
;
; ΠΟΥ ΖΕΙ, ΚΑΙ ΓΙΑΤΙ ΟΧΙ ΧΑΜΗΛΑ. Δύο εκδοχές πριν από αυτήν δεν έτρεξαν ποτέ
; ΟΥΤΕ ΜΙΑ εντολή, και οι δύο για τον ίδιο λόγο: όσο ζει το firmware, τα ROM
; είναι αναμμένα. Στο #C000-#FFFF διαβάζεται η ΠΑΝΩ ROM (BASIC) και στο
; #0000-#3FFF η ΚΑΤΩ (λειτουργικό). Οι εγγραφές περνούν στη RAM — γι' αυτό το
; αρχείο «φορτώνεται» κανονικά — αλλά ο επεξεργαστής διαβάζει ROM. Ο φορτωτής
; πήδηξε μέσα στο λειτουργικό και το μηχάνημα κατέληξε να ζητά κασέτα.
;
; Μένει η RAM #4000-#A6FF (πάνω από το #A700 ο χώρος εργασίας του AMSDOS). Από
; αυτήν, το #4000-#7FFF είναι το παράθυρο που αλλάζει τράπεζα και το #8000 και
; πάνω το χρειάζεται μόνο η ΤΕΛΕΥΤΑΙΑ πράξη. Ετσι:
;
;   #8000-#8BFF   η γεννήτρια (φορτώνεται, τρέχει, ξεχνιέται)
;   #9000-#91FF   ο φορτωτής
;   #9800-#9FFF   ο buffer 2 KB του AMSDOS
;   #3E00         το επίμετρο — ΑΦΟΥ σβήσουν τα ROM
;
; Η ΣΕΙΡΑ ΕΙΝΑΙ ΔΕΣΜΕΥΤΙΚΗ. Δύο κομμάτια πατάνε πάνω στο AMSDOS: τα δεδομένα
; της τράπεζας 2 (#8000-#ABFF) και ο κώδικας της τράπεζας 2 (#B440). Και τα δύο
; φορτώνονται πρώτα στην τράπεζα 5 και αντιγράφονται από το επίμετρο, που ζει
; στο #3E00 — εκεί φτάνει κανείς μόνο με τα ROM σβηστά, και τότε το AMSDOS δεν
; χρειάζεται πια.

        include "const.asm"
        include "../build/layout.asm"

CAS_IN_OPEN     equ #BC77
CAS_IN_DIRECT   equ #BC83
CAS_IN_CLOSE    equ #BC7A
SCR_SET_MODE    equ #BC0E
TXT_SET_CURSOR  equ #BB75
TXT_OUTPUT      equ #BB5A

LF_BUF          equ #9800               ; 2 KB, βασική RAM
GEN_ORG         equ #8000               ; όπου φορτώνεται η γεννήτρια
SCRATCH         equ #4000               ; τράπεζα 5: δεδομένα τράπεζας 2
SCRATCH_G2      equ #6C00               ; τράπεζα 5: κώδικας τράπεζας 2
ENDGAME         equ #3E00               ; το επίμετρο, με τα ROM σβηστά

        org     #9000

boot:
        ; --- η οθόνη φόρτωσης (§13.2) ---
        ; Πρώτη πράξη, πριν από οτιδήποτε άλλο: το SCR SET MODE ΣΒΗΝΕΙ την
        ; οθόνη, οπότε το «Ready» και το run"habitat φεύγουν αμέσως. Ως εδώ ο
        ; παίκτης κοίταζε μισό λεπτό μια οθόνη BASIC.
        ;
        ; MODE 1 και όχι 0: σαράντα στήλες χωρούν λέξεις, είκοσι όχι. Το
        ; παιχνίδι γυρίζει σε MODE 0 μόνο του, αφού σβήσουν τα ROM.
        ld      a,1
        call    SCR_SET_MODE
        ld      b,5
        ld      c,17
        ld      hl,t_title
        call    pr_at
        ld      b,7
        ld      c,9
        ld      hl,t_sub
        call    pr_at
        ld      b,11
        ld      c,8
        ld      hl,t_load
        call    pr_at
        ld      a,2
        call    bd_border
        ld      hl,n_bank6
        ld      b,n_bank6_e - n_bank6
        ld      de,SCRATCH
        ld      c,PAGE_B6
        call    ld_bank
        ld      a,6
        call    bd_border
        ld      hl,n_bank7
        ld      b,n_bank7_e - n_bank7
        ld      de,SCRATCH
        ld      c,PAGE_B7
        call    ld_bank
        ; Τα κείμενα (§4.2) πάνε ΠΑΝΩ στο δεσμευμένο κενό της τράπεζας 7, άρα
        ; ΜΕΤΑ από αυτήν. Ξεχωριστό αρχείο επειδή το pack.py φτιάχνει την
        ; BANK7.BIN χωρίς να ξέρει τι λέει το παιχνίδι.
        ld      hl,n_text
        ld      b,n_text_e - n_text
        ld      de,G_text
        ld      c,PAGE_B7
        call    ld_bank
        ; Η «τράπεζα 1» είναι η βασική RAM στο παράθυρο, όχι επέκταση: τα
        ; εικονίδια κάθονται πάνω από τον πίνακα DIST, χωρίς σελιδοποίηση.
        ld      a,9
        call    bd_border
        ld      hl,n_bank1
        ld      b,n_bank1_e - n_bank1
        ld      de,#7000
        call    ld_file
        ; --- τα δύο που πατάνε το AMSDOS, σε πρόχειρο χώρο ---
        ld      a,12
        call    bd_border
        ld      hl,n_page2
        ld      b,n_page2_e - n_page2
        ld      de,SCRATCH
        ld      c,PAGE_B5
        call    ld_bank
        ld      hl,(lf_len)
        ld      (bt_n2),hl
        ld      hl,n_game2
        ld      b,n_game2_e - n_game2
        ld      de,SCRATCH_G2
        ld      c,PAGE_B5
        call    ld_bank
        ld      hl,(lf_len)
        ld      (bt_ng2),hl
        ; --- η γεννήτρια: φορτώνεται, τρέχει, και ξεχνιέται ---
        ld      a,15
        call    bd_border
        ld      hl,n_gen
        ld      b,n_gen_e - n_gen
        ld      de,GEN_ORG
        call    ld_file
        ld      a,3
        call    bd_border
        ; Η γένεση κρατά 13,5 δευτερόλεπτα. Το λέει, και δείχνει και μπάρα: το
        ; gen.asm γράφει κατευθείαν στη χαρακτηρο-σειρά 16.
        ld      b,14
        ld      c,8
        ld      hl,t_world
        call    pr_at
        call    GEN_ORG
        ld      b,14
        ld      c,8
        ld      hl,t_ready
        call    pr_at
        ; --- ο κώδικας του παιχνιδιού, κάτω από την κάτω ROM ---
        ld      a,26
        call    bd_border
        ld      hl,n_game
        ld      b,n_game_e - n_game
        ld      de,#0100
        call    ld_file
        ; --- το επίμετρο ---
        ld      hl,eg_code
        ld      de,ENDGAME
        ld      bc,eg_end - eg_code
        ldir
        di
        ld      sp,#0100
        ld      bc,GA_PORT + PAGE_B5
        out     (c),c
        ld      bc,GA_PORT + RMR_MODE0  ; ΤΑ ROM ΣΒΗΝΟΥΝ: η μνήμη είναι δική μας
        out     (c),c
        ld      ix,(bt_ng2)
        ld      bc,(bt_n2)
        jp      ENDGAME

; ---------------------------------------------------------------------------
; eg_code — το επίμετρο. Αντιγράφεται στο #3E00 και τρέχει εκεί.
;
; Οι δύο αντιγραφές περνούν πάνω από τον ΙΔΙΟ τον φορτωτή (#9000) και πάνω από
; τη στοίβα του BASIC, γι' αυτό τρέχει από αλλού. Δεν διαβάζει ούτε ένα byte
; από τη μνήμη του φορτωτή: τα δύο μήκη έρχονται έτοιμα σε BC και IX.
; ---------------------------------------------------------------------------
eg_code:
        ld      hl,SCRATCH
        ld      de,#8000
        ldir                            ; BC = μήκος δεδομένων τράπεζας 2
        push    ix
        pop     bc
        ld      hl,SCRATCH_G2
        ld      de,PAGE2_CODE
        ldir
        ; Η τράπεζα 5 είναι το NEXTHOP (§7.4). Αν μείνουν εκεί τα σκουπίδια του
        ; προχείρου, ένας πράκτορας μπορεί να διαβάσει «επόμενο κόμβο» που δεν
        ; είναι σκουπίδι αλλά ΕΓΚΥΡΟΣ γείτονας, και να κάνει ένα λάθος βήμα πριν
        ; προλάβει η δρομολόγηση. Μηδενίζεται, ώστε ο δίσκος να ξεκινά από την
        ; ίδια ακριβώς κατάσταση με το snapshot.
        ld      hl,SCRATCH
        ld      (hl),0
        ld      de,SCRATCH + 1
        ld      bc,#4000 - 1
        ldir
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        jp      #0100
eg_end:

; ld_bank — σαν το ld_file, με την τράπεζα C στο παράθυρο.
;
; Το AMSDOS δουλεύει κανονικά με σελιδοποιημένο παράθυρο: ο κώδικάς του είναι
; σε ROM, ο χώρος εργασίας του πάνω από το #A700 και ο buffer του εδώ στο
; #9800 — τίποτε δικό του δεν περνά από το #4000-#7FFF.
ld_bank:
        push    bc
        ld      b,GA_PORT/256
        out     (c),c
        pop     bc
        call    ld_file
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        ret

; ---------------------------------------------------------------------------
; ld_file — HL = όνομα, B = μήκος, DE = πού. Κολλάει με κόκκινο αν αποτύχει.
;
; Το CAS IN OPEN γυρίζει στο BC το ΜΗΚΟΣ του αρχείου· φυλάγεται, γιατί οι δύο
; αντιγραφές του επιμέτρου το χρειάζονται και ο φορτωτής δεν ξέρει τα μεγέθη.
; ---------------------------------------------------------------------------
ld_file:
        ld      (lf_dest),de
        push    bc
        push    de
        push    hl
        ld      a,'.'                   ; μία τελεία ανά αρχείο — ο δρομέας
        call    TXT_OUTPUT              ; μένει εκεί που τον άφησε το t_load
        pop     hl
        pop     de
        pop     bc
        ld      de,LF_BUF
        call    CAS_IN_OPEN
        jr      nc,lf_fail
        ld      (lf_len),bc
        ld      hl,(lf_dest)
        call    CAS_IN_DIRECT
        push    af
        call    CAS_IN_CLOSE
        pop     af
        ret     c
lf_fail:
        ld      a,6                     ; κόκκινο: δεν βρέθηκε ή δεν διαβάστηκε
        call    bd_border
lf_hang:
        jr      lf_hang

; ---------------------------------------------------------------------------
; pr_at — B = γραμμή, C = στήλη (1-25 / 1-40), HL = κείμενο με τερματικό 0.
;
; Το TXT OUTPUT χαλάει τα πάντα εκτός από το IX/IY, γι' αυτό ο δείκτης του
; κειμένου πηγαινοέρχεται από τη στοίβα σε κάθε χαρακτήρα.
; ---------------------------------------------------------------------------
pr_at:
        push    hl
        ld      h,c
        ld      l,b
        call    TXT_SET_CURSOR
        pop     hl
pr_str:
        ld      a,(hl)
        or      a
        ret     z
        inc     hl
        push    hl
        call    TXT_OUTPUT
        pop     hl
        jr      pr_str

; bd_border — A = hardware ink του περιγράμματος.
bd_border:
        ld      c,a
        ld      b,GA_PORT/256
        ld      a,GA_BORDER
        out     (c),a
        ld      a,GA_INK
        or      c
        out     (c),a
        ret

t_title:    db "H A B I T A T",0
t_sub:      db "a colony on a dead world",0
t_load:     db "LOADING ",0
t_world:    db "BUILDING THE WORLD",0
t_ready:    db "READY             ",0

n_bank1:    db "BANK1.BIN"
n_bank1_e:
n_bank6:    db "BANK6.BIN"
n_bank6_e:
n_bank7:    db "BANK7.BIN"
n_bank7_e:
n_text:     db "TEXT.BIN"
n_text_e:
n_page2:    db "PAGE2.BIN"
n_page2_e:
n_game2:    db "GAME2.BIN"
n_game2_e:
n_gen:      db "GEN.BIN"
n_gen_e:
n_game:     db "GAME.BIN"
n_game_e:

lf_dest:    dw 0
lf_len:     dw 0
bt_n2:      dw 0
bt_ng2:     dw 0
boot_end:

        save    "../build/boot.bin", #9000, boot_end - #9000
