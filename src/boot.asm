; boot.asm — ο φορτωτής. Αυτό είναι που τρέχει το RUN"HABITAT".
;
; ΠΟΥ ΖΕΙ, ΚΑΙ ΓΙΑΤΙ ΟΧΙ ΧΑΜΗΛΑ. Δύο εκδοχές πριν από αυτήν δεν έτρεξαν ποτέ
; ΟΥΤΕ ΜΙΑ εντολή, και οι δύο για τον ίδιο λόγο: όσο ζει το firmware, τα ROM
; είναι αναμμένα. Στο #C000-#FFFF διαβάζεται η ΠΑΝΩ ROM (BASIC) και στο
; #0000-#3FFF η ΚΑΤΩ (λειτουργικό). Οι εγγραφές περνούν στη RAM — γι' αυτό το
; αρχείο «φορτώνεται» κανονικά — αλλά ο επεξεργαστής διαβάζει ROM. Ο φορτωτής
; πήδηξε μέσα στο λειτουργικό και το μηχάνημα κατέληξε να ζητά κασέτα.
;
; Μένει η RAM #4000-#A67B (πάνω από το HIMEM ο χώρος εργασίας του AMSDOS). Από
; αυτήν, το #4000-#7FFF είναι το παράθυρο που αλλάζει τράπεζα και το #8000 και
; πάνω το χρειάζεται μόνο η ΤΕΛΕΥΤΑΙΑ πράξη. Ετσι:
;
;   #8000-#8DFF   η γεννήτρια (φορτώνεται, τρέχει, ξεχνιέται)
;   #9000-#97FF   ο φορτωτής (589 bytes στο βήμα 112, 1.228 με τον δικό
;                 του αναγνώστη τομέων από το 113, 1.677 με το μενού του
;                 πλανήτη από το 128· το boot_end ελέγχεται)
;   #9800-#9FFF   ο κατάλογος του δίσκου (βήμα 113)· ο buffer 2 KB του
;                 AMSDOS αν χρειαστεί
;   #A000-#A1FF   ένας τομέας (SECT_BUF, βήμα 113)
;   #A200-#A2FF   η σελίδα εργασίας της γεννήτριας (GEN_WORK)
;   ως το #A67B   το HIMEM του 6128 με δίσκο: από πάνω ο χώρος του AMSDOS
;   #3FC0         το επίμετρο — ΑΦΟΥ σβήσουν τα ROM
;
; Η ΣΕΙΡΑ ΕΙΝΑΙ ΔΕΣΜΕΥΤΙΚΗ. Δύο κομμάτια πατάνε πάνω στο AMSDOS: τα δεδομένα
; της τράπεζας 2 (#8000-#ABFF) και ο κώδικας της τράπεζας 2 (#B440). Και τα δύο
; φορτώνονται πρώτα σε πρόχειρο — τα δεδομένα στη βασική τράπεζα 1, ο κώδικας
; στην τράπεζα 5 (βήμα 86) — και αντιγράφονται από το επίμετρο, που ζει
; στο #3F80 — εκεί φτάνει κανείς μόνο με τα ROM σβηστά, και τότε το AMSDOS δεν
; χρειάζεται πια.

        include "const.asm"
        include "../build/layout.asm"

CAS_IN_OPEN     equ #BC77
CAS_IN_DIRECT   equ #BC83
CAS_IN_CLOSE    equ #BC7A
SCR_SET_MODE    equ #BC0E
TXT_SET_CURSOR  equ #BB75
TXT_OUTPUT      equ #BB5A
KM_TEST_KEY     equ #BB1E
MC_WAIT_FLYBACK equ #BD19
KL_U_ROM_DISABLE equ #B903
KL_ROM_RESTORE  equ #B90C

LF_BUF          equ #9800               ; 2 KB, βασική RAM
GEN_ORG         equ #8000               ; όπου φορτώνεται η γεννήτρια
SCRATCH         equ #4000               ; ΒΑΣΙΚΗ τράπεζα 1: δεδομένα τράπεζας 2
; ΟΧΙ #6C00 (βήμα 38): ο κώδικας της τράπεζας 2 πέρασε τα 5.120 bytes που
; χωρούσαν από εκεί ως το #8000, ενώ τα δεδομένα από κάτω τελείωναν στο #6578
; — 1.672 bytes κενό. Από το #6800 χωρούν 6.144, περισσότερα από όσα
; παίρνει η ίδια η τράπεζα 2 (#ABB8-#BFFF): το όριο είναι ξανά εκείνο.
; ΚΑΙ ΟΧΙ #6800 (βήμα 85): οι μηχανές έφυγαν από τα δεδομένα της τράπεζας 2
; για την τράπεζα 5, και ο κώδικας της τράπεζας 2 μεγάλωσε στη θέση τους πέρα
; από τα 6.144 bytes· στο #6640, με τις μηχανές από κάτω του σε πρόχειρο.
; ΚΑΙ ΟΧΙ ΟΛΑ ΣΤΗΝ ΤΡΑΠΕΖΑ 5 (βήμα 86): δεδομένα 8.056 + μηχανές 1.584 +
; κώδικας 6.835 = 16.475, 91 bytes πάνω από ολόκληρη την τράπεζα. Τα δεδομένα
; περιμένουν τώρα στη ΒΑΣΙΚΗ τράπεζα 1, εκεί που θα σταθεί το DIST (που το
; φτιάχνει η δρομολόγηση, δεν φορτώνεται), ως τα εικονίδια στο ICONS· ο
; κώδικας στην τράπεζα 5 από το #4000, ως τις μηχανές, που φορτώνονται
; κατευθείαν στο B5_BASE. Το tools/mkdsk.py ελέγχει και τα δύο ταβάνια.
SCRATCH_G2      equ #4000               ; τράπεζα 5: κώδικας τράπεζας 2
ICONS           equ #7000               ; βασική τράπεζα 1: τα εικονίδια m και l
; Ο ΚΩΔΙΚΑΣ ΤΩΝ ΤΡΥΠΩΝ ΤΟΥ DIST (βήμα 102), αμέσως κάτω από τα εικονίδια: η
; BANK1.BIN αρχίζει από εδώ, και το ov_install του παιχνιδιού τον μοιράζει στις
; τρύπες στην εκκίνηση (src/demolish.asm). Ως το βήμα 101 ερχόταν στο GH_BUF,
; πίσω από τα δεδομένα της τράπεζας 2, όπου δεν χωρούσε πάνω από την αποικία
; δοκιμών του snapshot. Το OV_LOAD του src/main.asm· το tools/mkdsk.py ελέγχει
; ότι είναι το ίδιο. #6B78 (#7000 - GH_LOG) στο βήμα 102· 2 KB από το 103, με
; το σώσιμο και τον οδηγό του δίσκου μαζί.
OV_LOAD         equ #6800
; ΤΟ ΕΠΙΜΕΤΡΟ ΕΙΝΑΙ 40 BYTES ΚΑΙ ΚΡΑΤΟΥΣΕ 512. Το #3E00 ήταν στρογγυλός
; αριθμός, και το tools/mkdsk.py τον επιβάλλει ως ταβάνι της τράπεζας 0: ό,τι
; έμενε από κει ως το #4000 ήταν χαμένο, γιατί ο φορτωτής αντιγράφει το
; επίμετρο ΑΦΟΥ φορτώσει το παιχνίδι. Το επίμετρο είναι ΣΑΡΑΝΤΑ bytes: στο
; #3F80 του κρατούσαμε 128 και στο #3FC0 του κρατάμε 64 — άλλα 64 για την
; τράπεζα 0, που στο βήμα 29 έμεινε με 82. Πιο ψηλά δεν πάει χωρίς να μετρηθεί
; ξανά το επίμετρο· πιο κάτω δεν χρειάζεται: η στοίβα του παιχνιδιού ξεκινά από
; το #0100 προς τα κάτω και το επίμετρο δεν αγγίζει τίποτα κάτω από το #4000.
;
; ΤΟ ΝΟΥΜΕΡΟ ΤΟ ΔΙΑΒΑΖΕΙ ΤΟ tools/mkdsk.py ΑΠΟ ΕΔΩ, με regex πάνω σε αυτή τη
; γραμμή: ήταν γραμμένο δύο φορές, και δύο αντίγραφα του ίδιου ταβανιού είναι
; ένα ταβάνι που κάποια στιγμή θα διαφωνήσει με τον εαυτό του.
ENDGAME         equ #3FC0               ; το επίμετρο, με τα ROM σβηστά

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
        call    bt_title
        ; --- ο πλανήτης (βήμα 128) ---
        ; ΠΡΙΝ ΑΠΟ ΤΟ ΦΟΡΤΩΜΑ, όπως το ζήτησε ο παίκτης: ο δίσκος δεν έχει
        ; ξεκινήσει ακόμη, και η επιλογή δεν χρειάζεται τίποτα από αυτόν. Τη
        ; διαβάζει η γεννήτρια, στο τέλος, από το A.
        call    mn_pick
        ld      (bt_pl),a
        ld      a,1
        call    SCR_SET_MODE            ; το μενού φεύγει, ο τίτλος ξαναγράφεται
        call    bt_title
        ld      b,11
        ld      c,8
        ld      hl,t_load
        call    pr_at
        ld      a,2
        call    bd_border
        call    fl_init                 ; ο κατάλογος του δίσκου (βήμα 113)
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
        ; Το ίδιο για τον κώδικα του τροχού στην τράπεζα 6 (βήμα 92, src/bots.asm),
        ; πάνω στη δέσμευση b6code: η BANK6.BIN του pack.py την έχει άδεια.
        ld      hl,n_b6code
        ld      b,n_b6code_e - n_b6code
        ld      de,G_b6code
        ld      c,PAGE_B6
        call    ld_bank
        ; Η «τράπεζα 1» είναι η βασική RAM στο παράθυρο, όχι επέκταση: τα
        ; εικονίδια κάθονται πάνω από τον πίνακα DIST, χωρίς σελιδοποίηση.
        ld      a,9
        call    bd_border
        ld      hl,n_bank1
        ld      b,n_bank1_e - n_bank1
        ld      de,OV_LOAD              ; ο κώδικας των τρυπών, και τα εικονίδια
        call    ld_file
        ; --- τα δύο που πατάνε το AMSDOS, σε πρόχειρο χώρο ---
        ld      a,12
        call    bd_border
        ld      hl,n_page2
        ld      b,n_page2_e - n_page2
        ld      de,SCRATCH
        call    ld_file
        ld      hl,(lf_len)
        ld      (bt_n2),hl
        ld      hl,n_bank5
        ld      b,n_bank5_e - n_bank5
        ld      de,B5_BASE
        ld      c,PAGE_B5
        call    ld_bank
        ld      hl,n_game2
        ld      b,n_game2_e - n_game2
        ld      de,SCRATCH_G2
        ld      c,PAGE_B5
        call    ld_bank
        ld      hl,(lf_len)
        ld      (bt_ng2),hl
        ; --- ο κώδικας του παιχνιδιού, κάτω από την κάτω ROM ---
        ; ΠΡΙΝ ΑΠΟ ΤΗ ΓΕΝΝΗΤΡΙΑ από το βήμα 113, ώστε ο δίσκος να τελειώνει μαζί
        ; και το μοτέρ να σβήνει πριν από τα 5 δευτερόλεπτα της γένεσης. Η
        ; γεννήτρια δεν αγγίζει τίποτα κάτω από το #4000, και το firmware μόνο
        ; το #0000-#003F.
        ld      a,26
        call    bd_border
        ld      hl,n_game
        ld      b,n_game_e - n_game
        ld      de,#0100
        call    ld_file
        ; --- η γεννήτρια: φορτώνεται, τρέχει, και ξεχνιέται ---
        ld      a,15
        call    bd_border
        ld      hl,n_gen
        ld      b,n_gen_e - n_gen
        ld      de,GEN_ORG
        call    ld_file
        ld      bc,FDC_MOTOR            ; ο δίσκος τελείωσε
        xor     a
        out     (c),a
        ld      a,3
        call    bd_border
        ; Η γένεση κρατά 5 δευτερόλεπτα (13,5 ως το βήμα 111). Το λέει, και δείχνει και μπάρα: το
        ; gen.asm γράφει κατευθείαν στη χαρακτηρο-σειρά 16.
        ld      b,14
        ld      c,8
        ld      hl,t_world
        call    pr_at
        ld      a,(bt_pl)               ; ο πλανήτης του μενού (βήμα 128)
        call    GEN_ORG
        ld      b,14
        ld      c,8
        ld      hl,t_ready
        call    pr_at
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
        ld      ix,(bt_n2)
        ld      bc,(bt_ng2)
        jp      ENDGAME

; ---------------------------------------------------------------------------
; eg_code — το επίμετρο. Αντιγράφεται στο #3E00 και τρέχει εκεί.
;
; Οι δύο αντιγραφές περνούν πάνω από τον ΙΔΙΟ τον φορτωτή (#9000) και πάνω από
; τη στοίβα του BASIC, γι' αυτό τρέχει από αλλού. Δεν διαβάζει ούτε ένα byte
; από τη μνήμη του φορτωτή: τα δύο μήκη έρχονται έτοιμα σε BC (κώδικας) και
; IX (δεδομένα). Η τράπεζα 5 είναι στο παράθυρο όταν ξεκινά.
;
; Ο ΚΩΔΙΚΑΣ ΠΡΩΤΑ, ΜΕΤΑ ΤΑ ΔΕΔΟΜΕΝΑ (βήμα 86): ο καθένας περιμένει σε άλλη
; τράπεζα, και κάθε τράπεζα αδειάζει και μηδενίζεται πριν αλλάξει η σελίδα.
; ---------------------------------------------------------------------------
eg_code:
        ld      hl,SCRATCH_G2
        ld      de,PAGE2_CODE
        ldir
        ; Η τράπεζα 5 είναι το NEXTHOP (§7.4). Αν μείνουν εκεί τα σκουπίδια του
        ; προχείρου, ένας πράκτορας μπορεί να διαβάσει «επόμενο κόμβο» που δεν
        ; είναι σκουπίδι αλλά ΕΓΚΥΡΟΣ γείτονας, και να κάνει ένα λάθος βήμα πριν
        ; προλάβει η δρομολόγηση. Μηδενίζεται, ώστε ο δίσκος να ξεκινά από την
        ; ίδια ακριβώς κατάσταση με το snapshot.
        ld      hl,#4000
        ld      (hl),0
        ld      de,#4001
        ld      bc,B5_BASE - #4001      ; ως τις μηχανές
        ldir
        ld      bc,GA_PORT + PAGE_B1
        out     (c),c
        push    ix
        pop     bc
        ld      hl,SCRATCH
        ld      de,#8000
        ldir
        ; Και το DIST, για τον ίδιο λόγο: εκεί περίμεναν τα δεδομένα. Ως τον
        ; κώδικα των τρυπών (βήμα 102), που τον μοιράζει το ov_install.
        ld      hl,#4000
        ld      (hl),0
        ld      de,#4001
        ld      bc,OV_LOAD - #4001      ; ως τον κώδικα των τρυπών
        ldir
        jp      #0100
eg_end:

; Το επίμετρο τρέχει στο ENDGAME και δεν έχει πού να ξεχειλίσει: από πάνω του
; είναι το #4000, δηλαδή το παράθυρο σελιδοποίησης. Το ταβάνι της τράπεζας 0 το
; ελέγχει το tools/mkdsk.py· ΑΥΤΟ εδώ ελέγχει το ίδιο το επίμετρο, που το βήμα
; 30 το στρίμωξε από τα 128 bytes στα 64.
        assert  eg_end - eg_code <= #4000 - ENDGAME

; ld_bank — σαν το ld_file, με την τράπεζα C στο παράθυρο.
;
; Το AMSDOS δουλεύει κανονικά με σελιδοποιημένο παράθυρο: ο κώδικάς του είναι
; σε ROM, ο χώρος εργασίας του πάνω από το HIMEM και ο buffer του εδώ στο
; #9800 — τίποτε δικό του δεν περνά από το #4000-#7FFF. Το ίδιο ο αναγνώστης
; τομέων (βήμα 113): κατάλογος, τομέας και μεταβλητές από το #9000 και πάνω.
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
; Το μήκος του αρχείου μένει στο lf_len: οι δύο αντιγραφές του επιμέτρου το
; χρειάζονται, και ο φορτωτής δεν ξέρει τα μεγέθη. Το δίνει η κεφαλίδα AMSDOS
; του αρχείου, είτε τη διαβάσει το fl_raw είτε το CAS IN OPEN.
;
; ΠΡΩΤΑ Ο ΔΙΚΟΣ ΜΑΣ ΑΝΑΓΝΩΣΤΗΣ (βήμα 113). Το AMSDOS ήθελε ~1,8 s ανά αρχείο
; στον εξομοιωτή όποιο κι αν ήταν το μέγεθος: 23,6 από τα 29 s της εκκίνησης
; ήταν τα αρχεία. Αν το fl_raw αποτύχει, το ίδιο αρχείο και όλα τα επόμενα
; πάνε στο AMSDOS, όπως ως το βήμα 112.
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
        ld      a,(fl_off)
        or      a
        jr      nz,lf_amsdos
        push    bc
        push    hl
        call    fl_mkname
        di                              ; ο ελεγκτής δεν περιμένει διακοπές
        call    fl_raw
        ei
        call    c,fl_quit               ; από εδώ και πέρα το AMSDOS
        pop     hl
        pop     bc
        ld      a,(fl_off)
        or      a
        ret     z
lf_amsdos:
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

; ===========================================================================
; Ο ΑΝΑΓΝΩΣΤΗΣ ΤΟΜΕΩΝ (βήμα 113)
;
; Ο δίσκος είναι μορφής DATA: tracks των 9 τομέων με id #C1-#C9, 512 bytes ο
; καθένας, blocks του 1 KB (δύο τομείς), και ο κατάλογος στα blocks 0-1, τους
; τέσσερις πρώτους τομείς του track 0. Ο λογικός τομέας s είναι το track s/9
; και το id #C1 + s mod 9. Μία εγγραφή του καταλόγου κρατά ως 16 blocks (16
; KB, μία «έκταση»)· η BANK6.BIN και η BANK7.BIN, 16 KB συν την κεφαλίδα,
; έχουν δύο.
;
; Ο κατάλογος διαβάζεται ΜΙΑ φορά, στην αρχή. Κάθε αρχείο: οι εγγραφές του με
; το όνομά του, έκταση 0, 1, ... · από αυτές τα blocks του· από αυτά οι
; τομείς. Ο πρώτος τομέας έχει την κεφαλίδα AMSDOS (128 bytes): ελέγχεται το
; άθροισμά της και ο τύπος, και δίνει το μήκος. Οι επόμενοι πάνε κατευθείαν
; στον προορισμό όσο χωρούν ολόκληροι· ο τελευταίος, μισός, από τον SECT_BUF.
;
; ΕΝΑΣ ΤΟΜΕΑΣ ΑΝΑ ΕΝΤΟΛΗ, με αύξοντα id. Στον δίσκο τα id είναι πλεγμένα (C1,
; C6, C2, C7, ...), οπότε δύο στροφές ανά track στο πραγματικό μηχάνημα, όπως
; και στο AMSDOS. Ο ελεγκτής του εξομοιωτή δεν διαβάζει παραπάνω από έναν
; τομέα ανά εντολή, άρα ένα διάβασμα ολόκληρου track δεν θα ελεγχόταν πουθενά.
;
; Τι κερδίζεται, αφού ο ρυθμός του δίσκου είναι ο ίδιος: όσα κάνει το AMSDOS
; ΓΥΡΩ από κάθε αρχείο — ο κατάλογος από την αρχή σε κάθε άνοιγμα, οι
; αναμονές του, και το CAS IN DIRECT που περνά κάθε τομέα από τον buffer του.
; ===========================================================================

SECT_BUF        equ #A000               ; ένας τομέας, κάτω από το HIMEM (#A67B)
FDC_MOTOR       equ #FA7E
FL_TRIES        equ 16                  ; προσπάθειες ανά τομέα πριν το AMSDOS
FL_SETTLE       equ #0900               ; ~15 ms: η κεφαλή μετά το βήμα (AMSDOS: 15)
FL_PAUSE        equ #3C00               ; ~100 ms ανάμεσα σε δύο προσπάθειες

; ---------------------------------------------------------------------------
; fl_init — το μοτέρ, και ο κατάλογος στο LF_BUF.
;
; ΤΟ ΜΟΤΕΡ ΓΥΡΙΖΕΙ ΗΔΗ: το BASIC μόλις φόρτωσε τον φορτωτή, και το AMSDOS το
; σβήνει μόνο του 5 s αργότερα (με το ρολόι των διακοπών, που μένουν κλειστές
; όσο διαβάζουμε). Αν το βρει σβηστό κάποια προσπάθεια, το ανάβει και
; περιμένει: δεκαέξι προσπάθειες των 100 ms καλύπτουν το ξεκίνημα του δίσκου.
; ---------------------------------------------------------------------------
fl_init:
        di
        ld      bc,FDC_MOTOR
        ld      a,1
        out     (c),a
        ld      a,#C1
fli_lp:
        push    af
        sub     #C1
        add     a,a
        add     a,LF_BUF >> 8           ; LF_BUF + 512 x (id - #C1)
        ld      h,a
        ld      l,0
        pop     af
        push    af
        ld      c,0                     ; track 0
        call    fl_rd
        jr      c,fli_bad
        pop     af
        inc     a
        cp      #C5                     ; τέσσερις τομείς: 64 εγγραφές
        jr      nz,fli_lp
        ei
        ret
fli_bad:
        pop     af
        ei
; fl_quit — το AMSDOS παίρνει τον δίσκο. Η κεφαλή ξαναπάει στο track 0, όπου
; το CAS IN OPEN διαβάζει πρώτα τον κατάλογο: αν το AMSDOS πιστεύει ότι είναι
; ήδη εκεί, δεν την κινεί. Το πιστεύει όταν ο φορτωτής χωράει στο track 0 (ως
; το βήμα 127). Από το 128, με το μενού, ο τελευταίος τομέας του LOADER.BIN
; είναι στο track 1 και το AMSDOS κινείται μόνο του· το SEEK μένει, γιατί ένας
; μικρότερος φορτωτής θα το ξαναχρειαζόταν (tests/test_disc.py, §7).
fl_quit:
        ld      a,1
        ld      (fl_off),a
        di
        xor     a
        call    fl_seek
        ei
        ret

; ---------------------------------------------------------------------------
; fl_mkname — HL = όνομα με τελεία, B = μήκος → fl_name, 8 + 3 με κενά, όπως
; στον κατάλογο. Κρατά HL, BC.
; ---------------------------------------------------------------------------
fl_mkname:
        push    bc
        push    hl
        ld      de,fl_name
        ld      a,' '
        ld      c,11
flm_sp:
        ld      (de),a
        inc     de
        dec     c
        jr      nz,flm_sp
        ld      de,fl_name
flm_lp:
        ld      a,(hl)
        inc     hl
        cp      '.'
        jr      nz,flm_ch
        ld      de,fl_name + 8          ; η κατάληξη
        jr      flm_nx
flm_ch:
        ld      (de),a
        inc     de
flm_nx:
        djnz    flm_lp
        pop     hl
        pop     bc
        ret

; ---------------------------------------------------------------------------
; fl_find — A = έκταση. Out: HL = η εγγραφή του fl_name, ή carry.
;
; Χρήστης 0 (το #E5 είναι σβησμένη εγγραφή). Το bit 7 των χαρακτήρων είναι
; σημαία του AMSDOS (μόνο ανάγνωση, σύστημα) και δεν μετρά.
; ---------------------------------------------------------------------------
fl_find:
        ld      c,a
        ld      hl,LF_BUF
        ld      b,64
ffd_lp:
        push    hl
        ld      a,(hl)
        or      a
        jr      nz,ffd_no
        push    bc
        ld      de,fl_name
        ld      b,11
ffd_ch:
        inc     hl
        ld      a,(hl)
        and     #7F
        ex      de,hl
        cp      (hl)
        ex      de,hl
        inc     de
        jr      nz,ffd_nb
        djnz    ffd_ch
        pop     bc
        inc     hl
        ld      a,(hl)                  ; η έκταση
        cp      c
        jr      nz,ffd_no
        pop     hl
        ret                             ; NC: ίσα
ffd_nb:
        pop     bc
ffd_no:
        pop     hl
        ld      de,32
        add     hl,de
        djnz    ffd_lp
        scf
        ret

; ---------------------------------------------------------------------------
; fl_raw — το αρχείο του fl_name στο (lf_dest). NC = φορτώθηκε, carry = όχι.
; Με τις διακοπές κλειστές.
; ---------------------------------------------------------------------------
fl_raw:
        ld      hl,(lf_dest)
        ld      (fl_dst),hl
        xor     a
        ld      (fl_n),a
fr_sec:
        ; --- ο τομέας n: block n >> 1 του αρχείου, μισό n & 1 ---
        ld      a,(fl_n)
        and     #1F
        jr      nz,fr_ent
        ld      a,(fl_n)
        rlca
        rlca
        rlca
        and     7                       ; η έκταση: 32 τομείς η καθεμία
        call    fl_find
        ret     c
        ld      (fl_ent),hl
fr_ent:
        ld      a,(fl_n)
        and     #1F
        rra                             ; A = θέση στην εγγραφή, carry = μισό
        push    af
        add     a,16
        ld      e,a
        ld      d,0
        ld      hl,(fl_ent)
        add     hl,de
        ld      l,(hl)
        ld      h,d
        ld      a,l
        or      a
        jr      z,fr_none               ; τα blocks τελείωσαν πριν από το μήκος
        pop     af
        adc     hl,hl                   ; 2 x block + μισό: ο λογικός τομέας
        ld      c,-1
        ld      de,-9
fr_div:
        inc     c
        add     hl,de
        jr      c,fr_div
        ld      a,l
        add     a,#C1 + 9               ; A = id, C = track
        ; --- πού: η κεφαλίδα και το τέλος στον SECT_BUF, τα άλλα κατευθείαν ---
        ld      hl,SECT_BUF
        ld      b,a
        ld      a,(fl_n)
        or      a
        jr      z,fr_buf
        ld      a,(fl_left + 1)
        cp      2                       ; τουλάχιστον 512 ακόμη;
        jr      c,fr_buf
        ld      hl,(fl_dst)
fr_buf:
        ld      a,b
        push    hl
        call    fl_rd
        pop     de                      ; πού πήγε
        ret     c
        ld      hl,fl_n
        ld      a,(hl)
        inc     (hl)
        or      a
        jr      nz,fr_body
        ; --- η κεφαλίδα AMSDOS ---
        call    fl_hdr
        scf
        ret     nz                      ; δεν είναι κεφαλίδα: AMSDOS
        ld      hl,(SECT_BUF + 24)      ; το μήκος, όπως το δίνει το CAS IN OPEN
        ld      (fl_left),hl
        ld      (lf_len),hl
        ld      hl,SECT_BUF + 128
        ld      bc,384
        jr      fr_copy
fr_none:
        pop     af
        scf
        ret
fr_body:
        ex      de,hl
        ld      bc,512
; fr_copy — HL = από πού, BC = όσα έχει ο τομέας. Μετακινεί min(BC, fl_left)
; στο fl_dst — εκτός αν ο τομέας διαβάστηκε ήδη εκεί (HL = fl_dst).
fr_copy:
        push    hl
        ld      hl,(fl_left)
        or      a
        sbc     hl,bc
        jr      nc,fr_cnt               ; μένουν κι άλλα
        add     hl,bc
        ld      b,h
        ld      c,l                     ; ο τελευταίος: όσα έμειναν
        ld      hl,0
fr_cnt:
        ld      (fl_left),hl
        pop     hl
        ld      de,(fl_dst)
        ld      a,b
        or      c
        jr      z,fr_moved              ; αρχείο 0 bytes: το ldir θα έκανε 64 KB
        or      a
        sbc     hl,de
        add     hl,de
        jr      z,fr_here
        ldir
        jr      fr_moved
fr_here:
        ex      de,hl
        add     hl,bc
        ex      de,hl
fr_moved:
        ld      (fl_dst),de
        ld      hl,(fl_left)
        ld      a,h
        or      l
        jp      nz,fr_sec
        ret                             ; NC από το or

; fl_hdr — Z αν ο SECT_BUF ξεκινά με κεφαλίδα AMSDOS δυαδικού αρχείου: τύπος
; 2, και τα bytes 67-68 το άθροισμα των 0-66. Ο τύπος πιάνει και τον τομέα
; με μηδενικά, που το άθροισμά του είναι σωστό.
fl_hdr:
        ld      a,(SECT_BUF + 18)
        cp      2
        ret     nz
        ld      hl,SECT_BUF
        ld      de,0
        ld      b,67
flh_lp:
        ld      a,(hl)
        add     a,e
        ld      e,a
        jr      nc,flh_nc
        inc     d
flh_nc:
        inc     hl
        djnz    flh_lp
        ld      a,(hl)
        cp      e
        ret     nz
        inc     hl
        ld      a,(hl)
        cp      d
        ret

; ---------------------------------------------------------------------------
; fl_rd — ένας τομέας στο HL. A = id, C = track.
; Out: NC = διαβάστηκε, carry = όχι, μετά από FL_TRIES προσπάθειες.
;
; Κάθε αποτυχία ανάβει ξανά το μοτέρ, περιμένει 100 ms και ξαναβρίσκει το
; track 0 (RECALIBRATE) πριν πάει ξανά: έτσι κάνει και το AMSDOS όταν κάτι δεν
; διαβάζεται.
; ---------------------------------------------------------------------------
fl_rd:
        ld      (fl_ptr),hl
        ld      (fl_rcmd + 4),a         ; R
        ld      (fl_rcmd + 6),a         ; EOT = R: ένας τομέας
        ld      a,c
        ld      (fl_rcmd + 2),a         ; C
        ld      a,FL_TRIES
        ld      (fl_try),a
flr_go:
        ld      a,(fl_rcmd + 2)
        ld      hl,fl_cur
        cp      (hl)
        call    nz,fl_seek
        ld      hl,fl_rcmd
        ld      e,9
flr_cmd:
        ld      a,(hl)
        call    fl_out
        inc     hl
        dec     e
        jr      nz,flr_cmd
        ; Η μεταφορά: ένα byte κάθε 32 us από τον δίσκο, και ο βρόχος θέλει 20.
        ld      hl,(fl_ptr)
        ld      bc,#FB7E
flr_x:
        in      a,(c)
        jp      p,flr_x                 ; RQM
        and     #20                     ; EXM: η εκτέλεση συνεχίζεται
        jr      z,flr_end
        inc     c
        in      a,(c)
        ld      (hl),a
        dec     c
        inc     hl
        jr      flr_x
flr_end:
        ld      hl,fl_st
        ld      e,7
flr_res:
        call    fl_in
        ld      (hl),a
        inc     hl
        dec     e
        jr      nz,flr_res
        call    fl_ok
        ret     z                       ; και NC
        ld      hl,fl_try
        dec     (hl)
        scf
        ret     z
        ld      bc,FDC_MOTOR
        ld      a,1
        out     (c),a
        ld      de,FL_PAUSE
        call    fl_wait
        ld      a,#07                   ; RECALIBRATE
        call    fl_out
        xor     a
        call    fl_out                  ; drive 0
        call    fl_sense
        xor     a
        ld      (fl_cur),a
        jr      flr_go

; ---------------------------------------------------------------------------
; fl_ok — Z αν το διάβασμα πέτυχε, από τα ST0, ST1, ST2 του fl_st.
;
; ΣΤΟ CPC ΚΑΘΕ ΔΙΑΒΑΣΜΑ ΤΕΛΕΙΩΝΕΙ «ΑΝΩΜΑΛΑ». Το σήμα TC του μPD765 δεν είναι
; συνδεδεμένο, οπότε ο ελεγκτής δεν μαθαίνει ποτέ ότι τελειώσαμε: φτάνει στο
; EOT και αναφέρει IC = 01 (ST0 #40) με EN (ST1 bit 7, «τέλος κυλίνδρου»).
; Αυτό είναι το «εντάξει» του πραγματικού μηχανήματος. Ο ελεγκτής του
; εξομοιωτή δίνει IC = 00. Λάθος είναι: IC = 10 ή 11, NR (ST0 bit 3), και
; οποιοδήποτε άλλο bit του ST1 ή του ST2.
; ---------------------------------------------------------------------------
fl_ok:
        ld      a,(fl_st)
        and     #88                     ; IC = 1x, ή NR
        ret     nz
        ld      a,(fl_st + 1)
        and     #7F                     ; όλα εκτός από το EN
        ld      b,a
        ld      a,(fl_st + 2)
        or      b
        ret

; ---------------------------------------------------------------------------
; fl_seek — A = track. fl_sense — περιμένει το τέλος μιας κίνησης.
;
; Το SENSE INTERRUPT STATUS απαντά #80 (ένα byte) όσο η κεφαλή κινείται, και
; ST0 με SE (bit 5) και το track όταν σταματήσει. Ο εξομοιωτής απαντά πάντα
; δύο bytes και η κίνηση είναι στιγμιαία. Μετά, 15 ms για να ησυχάσει η
; κεφαλή, όπως περιμένει και το AMSDOS.
; ---------------------------------------------------------------------------
fl_seek:
        ld      (fl_cur),a
        push    af
        ld      a,#0F                   ; SEEK
        call    fl_out
        xor     a
        call    fl_out                  ; drive 0, head 0
        pop     af
        call    fl_out
        call    fl_sense
        ld      de,FL_SETTLE
fl_wait:
        dec     de
        ld      a,d
        or      e
        jr      nz,fl_wait
        ret

fl_sense:
        ld      a,#08                   ; SENSE INTERRUPT STATUS
        call    fl_out
        call    fl_in
        cp      #80
        jr      z,fl_sense              ; κινείται ακόμη: ένα byte μόνο
        ld      d,a
        call    fl_in                   ; το track
        bit     5,d
        jr      z,fl_sense
        ret

; fl_out — A στον ελεγκτή. fl_in — ένα byte του ελεγκτή στο A. Χαλάνε BC.
fl_out:
        push    af
        ld      bc,#FB7E
flo_w:
        in      a,(c)
        add     a,a
        jr      nc,flo_w                ; RQM
        add     a,a
        jr      c,flo_w                 ; DIO: έχει κάτι να πει
        pop     af
        inc     c
        out     (c),a
        ret

fl_in:
        ld      bc,#FB7E
fli_w:
        in      a,(c)
        add     a,a
        jr      nc,fli_w
        add     a,a
        jr      nc,fli_w
        inc     c
        in      a,(c)
        ret

; ---------------------------------------------------------------------------
; mn_pick — το μενού του πλανήτη (βήμα 128, §13.2). Out: A = 0-3 ο πλανήτης
; (§5.7), #FF τυχαίος.
;
; ΒΕΛΑΚΙΑ Ή ΧΕΙΡΙΣΤΗΡΙΟ, FIRE Ή ENTER. Ο φορτωτής ζει ακόμη μαζί με το firmware,
; που σαρώνει το πληκτρολόγιο 50 φορές το δευτερόλεπτο· το KM TEST KEY
; διαβάζει τον χάρτη του, το χειριστήριο 0 μέσα (πλήκτρα 72-77). Μετράει
; μόνο ό,τι ΠΑΤΗΘΗΚΕ ΤΩΡΑ: το mn_prev ξεκινά «όλα πατημένα», ώστε ένα RETURN
; που κρατιέται ακόμη από το RUN"HABITAT να μη διαλέξει μόνο του.
; ---------------------------------------------------------------------------
mn_pick:
        ld      b,10
        ld      c,14
        ld      hl,t_choose
        call    pr_at
        ld      b,23
        ld      c,7
        ld      hl,t_keys
        call    pr_at
        ld      hl,t_menu
        ld      b,12                    ; οι πέντε γραμμές, ανά δύο σειρές
mnp_row:
        push    bc
        ld      c,2
        call    pr_at                   ; ο HL μένει στο 0 του κειμένου
        inc     hl
        pop     bc
        inc     b
        inc     b
        ld      a,b
        cp      12 + 2 * 5
        jr      c,mnp_row
mnp_flip:
        call    mn_flip                 ; η διαλεγμένη ανάποδα
mnp_wait:
        call    MC_WAIT_FLYBACK
        call    mn_keys                 ; E = τα πλήκτρα τώρα
        ld      hl,mn_prev
        ld      a,(hl)
        ld      (hl),e
        cpl
        and     e                       ; όσα πατήθηκαν από το προηγούμενο frame
        jr      z,mnp_wait
        push    af
        call    mn_flip                 ; η παλιά ξανά ίσια
        pop     de                      ; D = τα καινούργια (το mn_flip χαλάει τα DE)
        ld      a,(mn_sel)
        rr      d
        jr      c,mnp_up
        rr      d
        jr      c,mnp_dn
        dec     a                       ; FIRE: 0 τυχαίος -> #FF, 1-4 -> 0-3
        ret
mnp_up:
        dec     a
        jp      p,mnp_set
        ld      a,4                     ; από την κορυφή στον πάτο
        jr      mnp_set
mnp_dn:
        inc     a
        cp      5
        jr      c,mnp_set
        xor     a
mnp_set:
        ld      (mn_sel),a
        jr      mnp_flip

; mn_keys — Out: E = bit 0 πάνω, bit 1 κάτω, bit 2 FIRE. Το KM TEST KEY
; χαλάει A, C, HL και τις σημαίες.
mn_keys:
        ld      hl,mn_ktab
        ld      e,0
mnk_lp:
        ld      a,(hl)
        inc     a
        ret     z                       ; #FF: τέλος
        dec     a
        inc     hl
        ld      d,(hl)
        inc     hl
        push    hl
        push    de
        call    KM_TEST_KEY
        pop     de
        pop     hl
        jr      z,mnk_lp
        ld      a,e
        or      d
        ld      e,a
        jr      mnk_lp

; mn_flip — αναποδογυρίζει τη γραμμή του mn_sel ΚΑΤΕΥΘΕΙΑΝ στην οθόνη.
;
; ΟΧΙ ΜΕ ΤΟ TXT INVERSE. Το firmware γράφει έναν χαρακτήρα σε ~3 ms: η γραμμή
; των 38 κρατά 6 frames, και ξαναγράφοντας όλο το μενού σε κάθε πάτημα το
; βελάκι άργησε 0,6 s. Στο MODE 1 η πένα 1 (τα γράμματα) είναι το bit 0 του
; pixel, στο πάνω μισό του byte, και το χαρτί 0 μηδέν: XOR #F0 τα αλλάζει
; μεταξύ τους, και το ίδιο XOR τα ξαναγυρίζει. 8 x 76 bytes, ~5 ms.
;
; Η ΠΑΝΩ ROM ΣΒΗΝΕΙ ΓΙΑ ΛΙΓΟ: ο φορτωτής ξεκίνησε με CALL από το BASIC, και
; στο #C000 ο επεξεργαστής ΔΙΑΒΑΖΕΙ το BASIC (οι εγγραφές πάνε στη RAM, γι'
; αυτό η μπάρα της γεννήτριας δεν το χρειάζεται). Η οθόνη είναι στο #C000
; χωρίς μετατόπιση: τη μηδενίζει το SCR SET MODE.
mn_flip:
        ld      a,(mn_sel)
        add     a,a
        add     a,12 - 1                ; η σειρά, από το 0
        ld      l,a
        ld      h,0
        add     hl,hl
        add     hl,hl
        add     hl,hl
        add     hl,hl                   ; x 16
        ld      d,h
        ld      e,l
        add     hl,hl
        add     hl,hl                   ; x 64
        add     hl,de                   ; x 80
        ld      de,#C000 + 2            ; η στήλη 2
        add     hl,de
        call    KL_U_ROM_DISABLE
        push    af
        ld      c,8
mnf_ln:
        push    hl
        ld      b,76
mnf_b:
        ld      a,(hl)
        xor     #F0
        ld      (hl),a
        inc     hl
        djnz    mnf_b
        pop     hl
        ld      a,h
        add     a,8
        ld      h,a
        dec     c
        jr      nz,mnf_ln
        pop     af
        jp      KL_ROM_RESTORE

; bt_title — ο τίτλος και ο υπότιτλος, πάνω από το μενού και πάνω από τη
; φόρτωση.
bt_title:
        ld      b,5
        ld      c,17
        ld      hl,t_title
        call    pr_at
        ld      b,7
        ld      c,9
        ld      hl,t_sub
        jr      pr_at

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
t_choose:   db "CHOOSE A WORLD",0
t_keys:     db "UP/DOWN, THEN FIRE OR ENTER",0
; Πέντε γραμμές των 38 χαρακτήρων: η ανάποδη μπάρα του mn_flip είναι 76 bytes.
; Οι περιγραφές είναι μετρημένες, όχι του πίνακα του §5.7: 24 κόσμοι ανά
; πλανήτη από το tools/worldgen_ref.py, νερό / γη για χτίσιμο (έδαφος και
; σκόνη) / βουνό / φλέβες σε 16.384 πλακίδια — έρημος 3.274 / 7.342 / 3.984 /
; 76, πάγος 6.006 / 4.245 / 4.252 / 76, θύελλα 2.114 / 5.778 / 5.444 / 121,
; φεγγάρι 863 / 7.846 / 4.817 / 126. Το γόνιμο έδαφος δεν το διαβάζει τίποτα
; (§3.5), γι' αυτό δεν το λένε.
t_menu:     db " RANDOM      ANY OF THE FOUR          ",0
t_menu1:    db " DESERT      WATER, LAND, SOME ORE    ",0
            db " ICE         MUCH WATER, LESS LAND    ",0
            db " STORM       MOUNTAINS, ORE, DRY      ",0
            db " BARREN MOON DUST, ORE, LITTLE WATER  ",0
t_menu_e:
        assert  t_menu1 - t_menu == 39
        assert  t_menu_e - t_menu == 5 * 39
mn_ktab:    db 0,1, 72,1                ; πάνω: βελάκι, χειριστήριο
            db 2,2, 73,2                ; κάτω
            db 18,4, 6,4, 47,4          ; RETURN, το μικρό ENTER, SPACE
            db 76,4, 77,4               ; τα δύο FIRE του χειριστηρίου
            db #FF
mn_sel:     db 0                        ; 0 τυχαίος, 1-4 οι πλανήτες 0-3
mn_prev:    db #FF
bt_pl:      db #FF                      ; ό,τι διάλεξε, για τη γεννήτρια

n_bank1:    db "BANK1.BIN"
n_bank1_e:
n_bank6:    db "BANK6.BIN"
n_bank6_e:
n_bank7:    db "BANK7.BIN"
n_bank7_e:
n_text:     db "TEXT.BIN"
n_text_e:
n_b6code:   db "B6CODE.BIN"
n_b6code_e:
n_page2:    db "PAGE2.BIN"
n_page2_e:
n_bank5:    db "BANK5.BIN"
n_bank5_e:
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
; ο αναγνώστης τομέων (βήμα 113)
fl_off:     db 0                        ; 1 = AMSDOS από εδώ και πέρα
fl_cur:     db #FF                      ; το track της κεφαλής· #FF = άγνωστο
fl_name:    ds 11
fl_n:       db 0                        ; ο τομέας μέσα στο αρχείο
fl_ent:     dw 0                        ; η εγγραφή καταλόγου της έκτασης
fl_dst:     dw 0
fl_left:    dw 0
fl_ptr:     dw 0
fl_try:     db 0
fl_st:      ds 7                        ; ST0, ST1, ST2, C, H, R, N
; READ DATA (MFM), drive 0 / head 0, C, H, R, N = 2 (512 bytes), EOT, GPL, DTL
fl_rcmd:    db #46,0,0,0,#C1,2,#C1,#2A,#FF
boot_end:
        assert  boot_end <= LF_BUF      ; ο κατάλογος
        assert  (LF_BUF & #FF) == 0     ; το fl_init τον γράφει ανά 512
        assert  SECT_BUF >= LF_BUF + #800
        assert  GEN_WORK >= SECT_BUF + 512 ; η γεννήτρια τρέχει μετά τον δίσκο
        assert  GEN_WORK + 256 <= #A67C ; το HIMEM: από εκεί και πάνω το AMSDOS

        save    "../build/boot.bin", #9000, boot_end - #9000
