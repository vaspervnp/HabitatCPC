; need6.asm — το τέλος του st_check, στο δεύτερο κομμάτι του κώδικα της
; τράπεζας 6 (βήμα 187, DESIGN §4.2).
;
; ΤΟ b6x: τα 122 bytes ανάμεσα στο worldinfo (με τα EC_PEAK και EC_MSEEN) και
; τους θόλους, #6606-#667F. Ως το βήμα 186 ήταν άδεια μέσα στο μπλοκ που
; σώζεται. Τα φέρνει η B6CODE.BIN, μαζί με τον κώδικα από κάτω (src/main.asm),
; και το φόρτωμα τα κρατά στην άκρη όσο διαβάζει το μπλοκ (src/save.asm): ένα
; σώσιμο, και ένα του βήματος 186 που τα έχει μηδέν, γράφει από πάνω τους.
; Τρέχουν μόνο με την 6 στο παράθυρο, όπως το b6code.
;
; ΤΟ st_need ΕΡΧΕΤΑΙ ΑΠΟ ΤΗΝ ΤΡΑΠΕΖΑ 0, που είχε 7 bytes ως το πάτωμα των
; δοκιμών: το καλεί μόνο το st_check (src/needs.asm), με την 6 μέσα. Το
; ec_setfull, που το συνεχίζει, μένει εκεί: το καλεί και το wheel_reset.

; st_need — το τέλος του st_check (βήμα 142, src/needs.asm), A = 0 ή 1 όπως στο
; ec_setfull: με γεμάτη αποθήκη το ec_need, το σπανιότερο από άμυλο, λαχανικά
; και κρέας αν είναι κάτω από NEED_MIN, αλλιώς NO_STOCK· στην ισοπαλία το πρώτο
; της σειράς. Μία φορά ανά κύκλο ροής, όπως το ec_keep — στην τράπεζα 0 ως το
; βήμα 186, γιατί το b6code του st_check είχε 1 byte. ΜΟΝΟ ΜΕ ΓΕΜΑΤΗ: χωρίς,
; κανείς δεν το διαβάζει, και ο κύκλος ροής πλήρωνε 90 us για τίποτα (4 τώρα).
; Το ec_need δεν είναι μεταβλητή: είναι το immediate του erm_inf, που το
; διαβάζει (4 bytes λιγότερα). Χαλάει όσα και το ec_setfull, και τα B, DE.
st_need:
        ; ΚΑΙ ΤΟ ΟΡΙΟ ΤΩΝ ΑΝΤΑΛΛΑΚΤΙΚΩΝ (βήμα 144): το bit 2 του ec_keep, που το
        ; st_check μόλις έγραψε με τα δύο κάτω. Εδώ για τον ίδιο λόγο με το
        ; ec_need. Κρατά το A.
        ld      hl,(EC_STOCK + 2 * S_SPARE)
        ld      de,-SPARES_MAX
        add     hl,de                   ; CY αν έφτασαν
        jr      nc,stn_sp
        ld      hl,ec_keep
        set     2,(hl)
stn_sp:
        ; ΤΑ ΑΠΟΘΕΜΑΤΙΚΑ ΣΤΗΝ ΑΠΟΘΗΚΗ (βήμα 184, src/reserve.asm): με χώρο, και
        ; αν κάποιο γέμισε από τον προηγούμενο, ένας κύκλος ροής με το ec_dr1
        ; στο erd_call — οι τέσσερις επισκέψεις της θέσης 11 ως τον επόμενο
        ; βλέπουν και τους 64 θόλους. Αλλιώς το ec_run_one, και κανείς δεν
        ; πληρώνει τίποτα. Κρατά το A.
        ld      hl,EC_RSV
        ld      de,ec_run_one
        or      a
        jr      nz,stn_dr               ; γεμάτη: κανένα (NZ)
        cp      (hl)
        jr      z,stn_dr                ; χωρά, κανένα αποθεματικό (Z): 66 T από το 183
        xor     a                       ; Z, και A = 0
        ld      (hl),a
        ld      de,ec_dr1
stn_dr:
        ld      (erd_call + 1),de
        jp      z,ec_setfull            ; χωρά (src/econ.asm, τράπεζα 0)
        ld      bc,256 * NEED_MIN + NO_STOCK    ; B = το όριο, C = κανένα
        ld      hl,EC_STOCK + 2 * S_STARCH
        ld      e,S_STARCH
        call    esn_one
        inc     e                       ; τα λαχανικά, αμέσως μετά
        call    esn_one
        inc     hl                      ; όχι τα βότανα
        inc     hl
        inc     e
        inc     e
        call    esn_one                 ; το κρέας
        ld      a,c
        ld      (ec_need),a
        ld      a,1                     ; γεμάτη
        jp      ec_setfull              ; ως το βήμα 186 έπεφτε μέσα του

; esn_one — HL = &απόθεμα, E = ο δείκτης του: αν είναι κάτω από το B, το B
; γίνεται αυτό και το C ο E. HL μετά το απόθεμα. Για το st_need.
esn_one:
        ld      a,(hl)
        inc     hl
        ld      d,(hl)
        inc     hl
        inc     d
        dec     d
        ret     nz                      ; 256 ή πάνω
        cp      b
        ret     nc
        ld      b,a
        ld      c,e
        ret
        assert  S_VEG == S_STARCH + 1 && S_MEDPLANT == S_STARCH + 2 && S_MEAT == S_STARCH + 3
