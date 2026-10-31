; const.asm — σταθερές μηχανής και χάρτη μνήμης
; Βλ. DESIGN.md §2.1, §4.1, §8.1

; --- οθόνη ---
SCR_BASE    equ #C000       ; σελίδα 3 — περιοχή παιχνιδιού
SCR_W       equ 80          ; bytes ανά γραμμή
SCR_H       equ 200         ; γραμμές συνολικά
PLAY_LINES  equ 160         ; §8.1 — οι πρώτες 160 είναι το κάδρο
HUD_LINES   equ 40

; --- PPI 8255: πληκτρολόγιο ΚΑΙ ήχος περνούν από εδώ (§9.1, §9.5) ---
; Η θύρα Α του PPI είναι ο δίαυλος δεδομένων του PSG, και το πληκτρολόγιο
; κρέμεται από τη θύρα Α του PSG. Γι' αυτό οι σταθερές είναι εδώ και όχι στο
; input.asm: τις χρειάζονται και τα δύο, και η σειρά τους είναι κοινή.
PPI_A       equ #F400
PPI_B       equ #F500
PPI_C       equ #F600
PPI_CTRL    equ #F700

; --- gate array ---
GA_PORT     equ #7F00
RMR_MODE0   equ #8C         ; 100 0 11 00 : mode 0, κάτω ROM off, πάνω ROM off
GA_PEN      equ #00         ; 00pppppp επιλογή pen
GA_BORDER   equ #10
GA_INK      equ #40         ; 01cccccc τιμή χρώματος

; --- διαμορφώσεις RAM για το παράθυρο &4000-&7FFF (§4.1) ---
PAGE_B1     equ #C0         ; βασική τράπεζα 1
PAGE_B4     equ #C4         ; επίπεδο κόσμου
PAGE_B5     equ #C5         ; NEXTHOP, και πάνω του το ευρετήριο αντικειμένων
PAGE_B6     equ #C6         ; τεταρτημόρια, φιγούρες, πίνακες οντοτήτων
PAGE_B7     equ #C7         ; εξωτερικές δομές, φυτά, κείμενο, ήχος

; --- η σελίδα εργασίας της γεννήτριας (βήμα 112, src/worldgen.asm) ---
; Οι ενεργές άγκυρες της γραμμής και οι πίνακες βάρους. Στον δίσκο, πάνω από
; τον κατάλογο (#9800) και τον τομέα (#A000) του φορτωτή, κάτω από το HIMEM
; (#A67B): η γέννηση τρέχει αφού φορτωθούν όλα (βήμα 113), και το src/boot.asm
; ελέγχει τα όρια. Ως το βήμα 112 στο #9400, ανάμεσα στον φορτωτή και τον
; buffer του AMSDOS· ο φορτωτής μεγάλωσε. Στο tests/gentest.asm ελεύθερη μνήμη.
GEN_WORK    equ #A200

; --- προσανατολισμοί τεταρτημορίου (§5 του SPRITES.md) ---
Q_NW        equ 0
Q_NE        equ 1           ; ζεύγη ανάποδα + flip_mode0 σε κάθε byte
Q_SW        equ 2           ; γραμμές ανάποδα
Q_SE        equ 3           ; και τα δύο

; --- οι εγγραφές των πινάκων της τράπεζας 6 (§6.1) ---
; Εδώ και όχι στο econ.asm: ο renderer τις διαβάζει χωρίς να θέλει τίποτε άλλο
; από την οικονομία, και ο assembler δεν συγχωρεί δύο ορισμούς.
; ΟΙ ΚΟΜΒΟΙ ΕΙΝΑΙ 96, ΟΧΙ 128, και αυτό είναι απόφαση χάρτη μνήμης (§4.2). Οι
; δύο πίνακες δρομολόγησης είναι κόμβοι x 128 bytes ο καθένας, δηλαδή 12 KB
; αντί για 16 — και τα 4 KB που ελευθερώνονται στην τράπεζα 1 πήραν τα
; εικονίδια δωματίων m και l, που με τη σειρά τους ελευθέρωσαν 3.936 bytes
; ΚΩΔΙΚΑ στην τράπεζα 2. Ο κόμβος ενός θόλου είναι το id του, μιας δομής
; MAX_DOME + id: 64 + 32 = 96.
MAX_DOME    equ 64
MAX_STRUCT  equ 48
MAX_NODE    equ MAX_DOME + MAX_STRUCT
MAX_CORR    equ 128                 ; 96 ως το βήμα 158: γέμιζαν γύρω στους 60 θόλους (DESIGN §4.2)
; Ο ΧΩΡΟΣ ΓΙΑ 112 ΚΟΜΒΟΥΣ (βήμα 155), πριν από το MAX_STRUCT 48 του βήματος
; 156: οι πίνακες έχουν όσες γραμμές και στήλες θα έχει τότε ο γράφος, και ό,τι
; ζει στις τρύπες τους είναι πια πάνω από τη στήλη NODE_CAP.
STRUCT_CAP  equ 48
NODE_CAP    equ MAX_DOME + STRUCT_CAP
; ΤΟ ΟΡΙΟ ΣΑΡΩΣΗΣ (βήμα 157, src/top.asm): ST_TOP = η ψηλότερη θέση δομής σε
; χρήση + 1, στρογγυλεμένη πάνω σε ζυγό (2-48), και κάθε πέρασμα του πίνακα
; των δομών σταματά εκεί. Πέντε bytes στις θέσεις 112-116 του node_deg, που
; δεν είναι κόμβος κανενός: φαίνονται από κάθε τράπεζα, σώζονται με τον γράφο
; (SV_STATE) και το game_new τα μηδενίζει. Οι μορφές είναι για όσους τις
; διαβάζουν: [ST_TEND, ST_THALF] είναι το BC του al_scans, [ST_TZERO, ST_THI] το
; BC του ob_struct_sort. Τα γράφει μόνο το st_set.
ST_TEND     equ G_rt_nodes + MAX_NODE   ; MAX_DOME + ST_TOP: ο πρώτος κόμβος έξω
ST_THALF    equ ST_TEND + 1             ; ST_TOP / 2: τα ζεύγη του al_scans
ST_TOP      equ ST_TEND + 2
ST_TZERO    equ ST_TEND + 3             ; πάντα 0: το C του ob_struct_sort
ST_THI      equ ST_TEND + 4             ; ST_TOP - 16, τουλάχιστον 1: η δεύτερη σελίδα
; ΚΑΙ ΤΟ ΟΡΙΟ ΤΩΝ ΔΙΑΔΡΟΜΩΝ (βήμα 159): CT_TOP = η ψηλότερη εγγραφή σε χρήση + 1
; (και η συνέχεια μιας διαδρομής με στροφή, CT_CONT), τουλάχιστον 1, στη θέση
; 117 του node_deg. Το ανεβάζει το cr_commit (src/route.asm), το ξαναμετρά το
; ct_recount στο τέλος του wheel_reset (src/wheel.asm), και δεν κατεβαίνει μέσα
; σε ένα παιχνίδι: η κατεδάφιση αφήνει κενό από κάτω του. Το διαβάζουν το
; χτίσιμο του ευρετηρίου (oi_build), το lk_done (src/door.asm) και η
; κατεδάφιση (src/dm_ovl.asm)· το cr_commit ψάχνει θέση σε όλο τον πίνακα.
CT_TOP      equ ST_TEND + 5
        assert  MAX_NODE + 6 <= 128 && (MAX_STRUCT & 1) == 0
; ΤΟ DIST ΣΤΗΝ ΤΡΑΠΕΖΑ 1 (βήμα 155, DESIGN §6.4): οι 64 γραμμές των θόλων, 128
; bytes η καθεμία, με τις στήλες 0 ως NODE_CAP - 1· η τρύπα κάθε γραμμής είναι
; οι στήλες NODE_CAP-127. Από το βήμα 153 η γραμμή μιας δομής χρειάζεται μόνο
; τις στήλες των δομών (το DIST με συμμετρία): ΜΠΛΟΚ στο DB_ROW, 64 bytes ανά
; δομή s, και η απόσταση ως τη δομή t στο DB_ROW + 64 s + t. Από κάτω του 1
; KB για τον κώδικα των τρυπών (OV_R1).
DB_ROW      equ #6400
DB_STRIDE   equ 64
OV_R1       equ #6000                   ; τράπεζα 1, συνεχές, 1 KB
OV_R2       equ #4000 + NODE_CAP        ; τράπεζα 1, οι τρύπες των 64 γραμμών θόλων
OV_R3       equ #4000 + NODE_CAP        ; τράπεζα 5, οι τρύπες των NODE_CAP γραμμών του NEXTHOP
OV_UNIT     equ 128 - NODE_CAP          ; 16 bytes ανά τρύπα
DOME_REC    equ 24
D_CX        equ 0
D_CY        equ 1
D_SIZE      equ 2
D_ROOM      equ 3
D_STATE     equ 4
D_INTEG     equ 5
D_POWER     equ 6
D_OPS       equ 7
D_MACH      equ 8
D_HEALTH    equ 16
; Η ΕΓΓΡΑΦΗ ΜΙΑΣ ΔΟΜΗΣ ΑΠΟ ΤΟΝ ΚΟΜΒΟ ΤΗΣ (βήμα 154). Ως το βήμα 153 ο πίνακας
; ήταν μία σελίδα: 8 x κόμβος σε 8 bits, και ld h,σελίδα. Με 48 δομές είναι 384
; bytes, και το 8 x δομή δεν χωρά σε ένα byte. Το 4 x δομή χωρά, και το ×2 το
; κάνει το add hl,hl, που περνά το κρατούμενο στο H:
;
;       add a,a / add a,a       ; 4 x κόμβος = 4 x δομή σε 8 bits (κόμβος 64 + δομή)
;       add a,STB_C + πεδίο/2   ; (μονό πεδίο: + (πεδίο - 1)/2, και inc l μετά)
;       ld l,a / ld h,STB_H
;       add hl,hl               ; G_struct_tbl + 8 x δομή + πεδίο
;
; Με πεδίο, ίδια bytes και 2 us παραπάνω από το παλιό add a,a x 3 / add a,πεδίο /
; ld l,a / ld h,σελίδα (3 για το add hl,hl, 1 λιγότερο add a,a)· χωρίς πεδίο,
; και το add a,STB_C, 2 bytes και 2 us. Ο πίνακας στο #7A80 (tools/pack.py):
; STB_C = 64, και κάθε σελίδα του τελειώνει σε όριο εγγραφής (16 + 32). Μια
; εγγραφή δεν περνά σελίδα: μέσα της αρκεί το inc l.
STB_H       equ G_struct_tbl >> 9
STB_C       equ (G_struct_tbl >> 1) & 255
; Ο ΚΟΜΒΟΣ ΑΠΟ ΤΟΝ ΔΕΙΚΤΗ (st_post, dr_raise): ld a,ixh / rra / ld a,ixl / rra x 3
; δίνει 32 x (σελίδα & 1) + L / 8 — η πρώτη σελίδα του πίνακα είναι ζυγή. (Τα
; assert στο src/newgame.asm: εδώ η διάταξη δεν έχει διαβαστεί ακόμη.)
STRUCT_REC  equ 8
ST_CX       equ 0
ST_CY       equ 1
ST_KIND     equ 2
ST_SIZE     equ 3
ST_STATE    equ 4
ST_INTEG    equ 5
ST_JOINED   equ 6           ; airlock: έχει ήδη τον διάδρομό του (βήμα 87)
ST_OPS      equ 6           ; ορυχείο: όσοι σκάβουν εκεί (βήμα 94, src/drill.asm), η Drill (bit 7), η Haul (bit 6, βήμα 95)
ST_HALF     equ 2           ; το bit του ST_OPS ενός ορυχείου: εκτός φλέβας, μισή απόδοση (βήμα 123)
ST_FREE     equ 3           ; το bit του ST_OPS ενός ορυχείου: μπήκε δωρεάν, δεν επιστρέφει τίποτα (βήμα 123)
ST_DLOW     equ 4           ; το bit του ST_OPS ενός ορυχείου: η Drill του περιμένει χαμηλά (βήμα 126, src/drill.asm)
DRILL_PRIO  equ 4           ; η Drill του πρώτου που σκάβει (job_prio)
KEEP_METAL  equ 30          ; βήμα 127: όσες τρώνε μέταλλο το αφήνουν ως εδώ (src/econ.asm, erm_ink)
BIO_MAX     equ 100         ; βήμα 138: η PLASTIC σταματά από εδώ και πάνω (src/econ.asm, erm_inb)
SPARES_MAX  equ 20          ; βήμα 144: η SPARES σταματά από εδώ και πάνω (src/econ.asm, erm_inp)
DRILL_LOW   equ 2           ; του δεύτερου και του τρίτου: κάτω από κάθε Operate (room_prio >= 3)
ST_OWED     equ 7           ; εργοτάξιο: φορτία που χρωστιούνται, μέταλλο<<4 | βιοπλ. (βήμα 88)· έτοιμο ορυχείο: ο σωρός (βήμα 95, src/haul.asm)
; Ο ΔΙΑΔΡΟΜΟΣ: 4 bytes από το βήμα 154, στην τράπεζα 5 (G_corr_tbl, #7800). Ως
; τότε 5, στην 6, με ένα πέμπτο byte κατάστασης που ήταν πάντα DS_ACTIVE ή 0:
; ένας διάδρομος μπαίνει έτοιμος (cr_commit). Η κατάσταση είναι πια στο C_A:
; ο κόμβος a (0-111), CT_EMPTY η άδεια θέση, CT_CONT η συνέχεια της
; προηγούμενης εγγραφής (το δεύτερο τρέξιμο μιας διαδρομής με στροφή).
CORR_REC    equ 4
C_A         equ 0
C_B         equ 1
C_DIR       equ 2
C_LEN       equ 3
CT_EMPTY    equ 254
CT_CONT     equ 255
; η εγγραφή από το id: add a,a / ld l,a / ld h,CT_H / add hl,hl (ob_corr)
CT_H        equ G_corr_tbl >> 9
DS_EMPTY    equ 0
DS_BUILDING equ 1
DS_ACTIVE   equ 2
NO_MACH     equ 255
FT_CLS      equ 250             ; 250..253 φυτά: άμυλο, λαχανικά, βότανα, δέντρο (src/fit.asm· εδώ από το βήμα 119, για το ec_break_d όπου δεν υπάρχει το fit.asm)
MACH_HP     equ 200             ; υγεία: δουλεύει (bit 7· όπως στο newgame)
MACH_OWED   equ 7               ; καινούργια: χρωστά μέταλλο (bit 0), βιοπλαστικό (bit 1), περιμένει χτίστη (βήμα 99, src/install.asm)
MACH_READY  equ 4               ; τα υλικά ήρθαν: τη στήνει μια Build
; --- οι δώδεκα τύποι δωματίου, με τη σειρά των εικονιδίων του pack.py ---
R_EMPTY     equ 0
R_CONTROL   equ 1
R_QUARTERS  equ 2
R_CANTEEN   equ 3
R_OXYGEN    equ 4
R_GREENHS   equ 5
R_STORAGE   equ 6
R_AIRLOCK   equ 7
R_FACTORY   equ 8
R_LAB       equ 9
R_MEDBAY    equ 10
R_LOUNGE    equ 11
K_SOLAR     equ 0
K_TURBINE   equ 1
K_COLLECT   equ 2
K_EXTRACT   equ 3
K_MINE      equ 4
; Πόσα tiles φτάνει η αντλία/το ορυχείο (§6.5). Ηταν στο build.asm, που στο
; main.asm έρχεται ΜΕΤΑ το terrain.asm: το rasm ΠΕΤΑΕΙ το μείον μπροστά σε equ
; που ορίζεται πιο κάτω (`-X`, `-X * k`, `-X + 1`· οι ετικέτες δεν παθαίνουν
; τίποτα). Το `ld bc,-RES_NEAR * 129` έβγαινε +258 (βήμα 67).
RES_NEAR    equ 2
K_AIRLOCK   equ 5
K_PAD       equ 6
K_SHIP      equ 7
; Το airlock ως άκρο διαδρόμου (src/route.asm, βήμα 86): «μέγεθος» -1, ώστε
; η ακτίνα μέγεθος + 2 να βγαίνει 1 tile, όσο το αποτύπωμά του 2x2.
AIRLOCK     equ 255

; --- η κατάσταση της οικονομίας (§6.5). Εδώ επειδή τη διαβάζει και το HUD,
; σε κάθε frame, χωρίς να θέλει τίποτε άλλο από το econ.asm.
EC_STOCK    equ G_econ_state            ; 14 x 16-bit
EC_PSTORE   equ G_econ_state + 28
EC_PCAP     equ G_econ_state + 30
EC_PPROD    equ G_econ_state + 32
EC_PUSE     equ G_econ_state + 34
EC_MPOWER   equ G_econ_state + 36
EC_O2PROD   equ G_econ_state + 38
EC_O2USE    equ G_econ_state + 40
EC_ACCP     equ G_econ_state + 42
EC_ACCO2    equ G_econ_state + 44
EC_POK      equ G_econ_state + 46
EC_O2OK     equ G_econ_state + 47
EC_PDOME    equ G_econ_state + 48
EC_DAY      equ G_econ_state + 49
EC_WIND     equ G_econ_state + 50
EC_SOL      equ G_econ_state + 51
EC_FRAME    equ G_econ_state + 52
EC_RND      equ G_econ_state + 54
EC_JDOME    equ G_econ_state + 56       ; περιστροφικοί δείκτες του πίνακα
EC_JAGENT   equ G_econ_state + 57       ; εργασιών (§6.7)
EC_ALIVE    equ G_econ_state + 58
EC_GAMEOVER equ G_econ_state + 59       ; §10.3 — η μόνη συνθήκη ήττας
EC_GLOOM    equ G_econ_state + 60       ; πένθος: ανεβαίνει με κάθε θάνατο
EC_STORM    equ G_econ_state + 61       ; περιστροφές αμμοθύελλας (§6.10)
EC_AMENITY  equ G_econ_state + 62       ; δέντρα και σαλόνια (§6.6)
EC_FREELK   equ G_econ_state + 63       ; airlock μόνα τους, χωρίς διάδρομο (βήμα 86)
EC_SOLLEN   equ G_econ_state + 64       ; frames ανά sol — ΔΕΔΟΜΕΝΟ (§6.11)
EC_DAYLEN   equ G_econ_state + 66
EC_PRODM    equ G_econ_state + 68       ; ποια αποθέματα φτιάχτηκαν ΕΔΩ
EC_SHETA    equ G_econ_state + 70
EC_SHSTATE  equ G_econ_state + 72
EC_SHKIND   equ G_econ_state + 73
EC_POPCAP   equ G_econ_state + 74
EC_MILE     equ G_econ_state + 75       ; τα πέντε ορόσημα του §10.2
EC_DEATHS   equ G_econ_state + 76
EC_NODEATH  equ G_econ_state + 77
EC_GREENS   equ G_econ_state + 78
EC_NOTRADE  equ G_econ_state + 79
EC_TRADED   equ G_econ_state + 80
EC_PADNODE  equ G_econ_state + 81

; ΟΙ ΤΡΕΙΣ ΣΤΑΘΜΕΣ ΡΕΥΜΑΤΟΣ (§6.5). Το EC_POK δεν είναι σημαία αλλά στάθμη: το
; §6.5 γράφει «machines stop, THEN oxygen stops» και ως το βήμα 32 δεν υπήρχε
; «then» — το ίδιο μπλακάουτ σταματούσε τις αντλίες και τη γεννήτρια οξυγόνου.
; Εδώ και όχι στο econ.asm, επειδή τις διαβάζουν και το hud.asm, το main.asm και
; το ship.asm, και δεν συμπεριλαμβάνουν όλα τα harness το econ.asm.
P_NONE      equ 0                       ; μπλακάουτ: τίποτα δεν γυρίζει
P_ALL       equ 1                       ; όλα
P_ESS       equ 2                       ; μόνο η υποστήριξη ζωής (MF_FLOW)

; ΤΑ ΔΥΟ ΝΕΑ ΠΕΔΙΑ ΣΤΟ ΤΕΛΟΣ, ΚΑΙ ΕΠΙΤΗΔΕΣ: το EC_POK κάθεται στο +46 και οι
; ζωντανοί στο +58, και αυτές τις μετατοπίσεις τις ξέρουν απ' έξω δέκα δοκιμές
; και τρία εργαλεία — δύο πεδία στη μέση θα τα μετακινούσαν όλα για να
; κερδίσουν τίποτα.
EC_EPOWER   equ G_econ_state + 82       ; ζήτηση ΥΠΟΣΤΗΡΙΞΗΣ ΖΩΗΣ (§6.5)
EC_ACCE     equ G_econ_state + 84       ; ο συσσωρευτής της, ανά σάρωμα
; Η βροχή μετεωριτών (§6.10), βήμα 38 — πάλι στο τέλος, για τον ίδιο λόγο.
EC_METEOR   equ G_econ_state + 86       ; κρούσεις που μένουν (0 = καμία βροχή)
EC_MCX      equ G_econ_state + 87       ; το κέντρο της, σε tiles, προσημασμένα
EC_MCY      equ G_econ_state + 88
EC_MRND     equ G_econ_state + 89       ; η δική της γεννήτρια (16 bit)
; Οι εργασίες Build στον πίνακα (βήμα 88): το NO ENGINEER του HUD ρωτά ένα byte
; αντί να σαρώνει τον πίνακα σε κάθε τικ του. Μπαίνει με το sp_build, βγαίνει
; όταν το κτίσμα τελειώσει (ja_build) — καμία Build δεν φεύγει αλλιώς.
EC_NBUILD   equ G_econ_state + 91
EC_LAND     equ G_econ_state + 92       ; 5 bytes: οι ειδικότητες των πλοίων σε δέκατα (βήμα 91, src/crew.asm)
; Ο ΕΜΠΟΡΟΣ (βήμα 93, src/ship.asm, src/lines.asm): ό,τι φέρνει, όσο είναι
; προσγειωμένος. Το κέρδος του σε %, και τέσσερα [απόθεμα, ποσότητα] — απόθεμα 0
; (το νερό, που δεν είναι εμπόρευμα) είναι κενή θέση.
EC_MARKUP   equ G_econ_state + 97
EC_CARGO    equ G_econ_state + 98       ; 8 bytes
; Τα έτοιμα ορυχεία (βήμα 94, src/drill.asm): τα μετρά ο κύκλος ροής, και τα
; διαβάζει το dr_need όταν ξυπνά ρομπότ — αλλιώς θα σάρωνε 32 δομές (+430 us).
EC_MINES    equ G_econ_state + 106
; Οι προσγειώσεις από τους τελευταίους εισβολείς (βήμα 111, src/ship.asm): όλες
; μετράνε, ως το 255. ΤΟ ΤΕΛΕΥΤΑΙΟ BYTE ΠΟΥ ΧΩΡΑΕΙ: μετά την οικονομία έρχονται
; ο πίνακας εργασιών, τα δωμάτια και το G_crew, που τελειώνει ακριβώς στο
; #9100 όπου θέλει σελίδα ο γράφος (tools/pack.py).
EC_LANDS    equ G_econ_state + 107

; --- ΣΤΑ ΑΔΕΙΑ ΤΟΥ node_occ (βήμα 121) ---------------------------------------
; Η οικονομία δεν έχει άλλο byte. Στην τράπεζα 6, μέσα στο μπλοκ που σώζεται
; (src/save.asm), που τα διαβάζει μόνο ο τροχός — έχει την 6 στο παράθυρο από
; την αρχή ως το τέλος. Ως το βήμα 171 ήταν τα σημάδια των πρακτόρων 100-111 και
; 120-121 στο πάνω μισό του node_occ· από το 172 τα σημάδια έχουν σελίδα (MKPG),
; το πάνω μισό είναι ο χάρτης των εισβολέων για τους κόμβους 0-111 (FO_MAP,
; src/foe.asm), και τα 14 bytes εδώ ακολουθούν, στο 240-253 (το 255 το γράφει το
; fo_after για όποιον περπατά).
EC_X        equ G_node_occ + 240
EC_LDIS     equ EC_X                    ; [sol, frame]: πότε άρχισε η τελευταία καταστροφή
EC_LEV      equ EC_X + 3                ; [sol, frame]: πότε έγινε το τελευταίο γεγονός
; ΚΥΡΟΣ ΚΑΙ ΝΟΜΙΣΜΑΤΑ (βήμα 134), αμέσως μετά: πέντε bytes ακόμη. Οι πράκτορες
; 180-187 είναι οι επισκέπτες που περπατούν (βήμα 136, AG_VIS0· 112-119 ως το 172).
EC_COINS    equ EC_X + 6                ; 16-bit, ως COIN_MAX: όσα πλήρωσαν οι επισκέπτες
EC_PREST    equ EC_X + 8                ; το κύρος του τελευταίου sol, ως 250
EC_GOOD     equ EC_X + 9                ; η εύνοια των επισκεπτών, 0-GOOD_MAX
EC_VISACC   equ EC_X + 10               ; ο συσσωρευτής: πάνω από 255, πλοίο επισκεπτών
; Ο ΕΜΠΟΡΟΣ ΠΟΥΛΑ ΚΑΙ ΝΟΜΙΣΜΑΤΑ (βήμα 135), όπως στο Planetbase: όσα φέρνει, σε
; δεκάδες. Τα γράφει η προσγείωσή του (sm_land), τα διαβάζει η γραμμή του.
EC_MCOIN    equ EC_X + 11
; ΟΣΟΙ ΕΠΙΣΚΕΠΤΕΣ ΕΙΝΑΙ ΜΕΣΑ (βήμα 136): αναπνέουν, και το ef_o2 (src/flow.asm)
; τους προσθέτει στη ζήτηση οξυγόνου. Το μετρά το vi_tick (src/visit.asm), όσο
; είναι εδώ το πλοίο τους. Μετά το EC_MCOIN (ως το βήμα 171 στο byte του
; πράκτορα 120).
EC_VIN      equ EC_X + 12
; ΤΟ ΒΗΜΑ ΤΟΥ TUTORIAL (βήμα 149, src/tutor.asm): 0 κανένα, 1-14 τα βήματα, 15
; το μήνυμα, 16 τέλος. Μέσα στο μπλοκ που σώζεται (ως το βήμα 171 στο byte
; του πράκτορα 121, που δεν άγγιζε κανείς).
EC_TU       equ EC_VIN + 1
; ΤΑ ΟΡΟΣΗΜΑ ΠΟΥ ΕΙΔΕ Ο ΠΑΙΚΤΗΣ ΚΑΙ ΟΙ ΠΕΡΙΣΣΟΤΕΡΟΙ ΑΠΟΙΚΟΙ (βήμα 177): μετά
; το worldinfo, στα 124 άδεια της τράπεζας 6 ως τους θόλους — μέσα στο μπλοκ
; που σώζεται (#6600-#7FFF, src/save.asm), και μηδέν σε κάθε εκκίνηση (ο
; φορτωτής μηδενίζει την 6, βήμα 175). Το EC_MSEEN είναι τα bits του EC_MILE
; που ζήτησαν ήδη σελίδα (ο κύκλος του sol, src/ship.asm)· το EC_PEAK το γράφει
; ο κύκλος ροής (src/flow.asm) και το δείχνει η σελίδα του τέλους.
EC_PEAK     equ G_worldinfo + 4
EC_MSEEN    equ G_worldinfo + 5
; Οι σελίδες του TUTOR.TXT (src/tupages.txt) μετά του tutorial: τα πέντε
; ορόσημα με τη σειρά των bits τους, το G, το τέλος (assert στο src/tpage.asm).
PG_MS0      equ 16
PG_GOALS    equ PG_MS0 + 5
PG_END      equ PG_GOALS + 1
TP_CHOOSE   equ #FE                     ; το tp_show: τη σελίδα τη διαλέγει το ms_go
; ΟΙ ΚΑΤΑΣΤΡΟΦΕΣ ΑΡΑΙΕΣ (βήμα 121, η απόφαση του χρήστη): θύελλα, έκλαμψη και
; βροχή μετεωριτών μόνο με DIS_POP ζωντανούς ή περισσότερους, και ποτέ μέσα σε
; δύο sol από την προηγούμενη. Οι βλάβες είναι φθορά: από την αρχή, με
; FAULT_GAP περιστροφές ανάμεσα — και ανάμεσα σε βλάβη και καταστροφή.
DIS_POP     equ 20
FAULT_GAP   equ 64
; Η ΧΩΡΗΤΙΚΟΤΗΤΑ ΤΩΝ ΑΠΟΘΗΚΩΝ (βήμα 122, η απόφαση του χρήστη): ΣΥΝΟΛΙΚΗ, όπως
; στο Planetbase — όλα τα αγαθά μαζί εκτός από το νερό, κάτω από το αμπάρι του
; σκάφους (STORE_BASE) και τους θόλους Storage (100/300/600, §6.8). Γεμάτη, και
; σταματούν οι μηχανές που βγάζουν απόθεμα, οι κήποι και το σκάψιμο.
STORE_BASE  equ 500

; --- πλοία (§6.11): το src/ship.asm ζει στην τράπεζα 6 από το βήμα 93, και
; αυτά τα διαβάζουν και το HUD, η μπάρα και η γραμμή του εμπόρου ---
SHIP_NONE   equ 0
SHIP_INCOM  equ 1
SHIP_LANDED equ 2
SK_COLONIST equ 0
SK_MERCHANT equ 1
SK_VISITOR  equ 2
SK_DEALT    equ 3                       ; ο έμπορος μετά τη συμφωνία (βήμα 98, src/carry.asm)
SK_FOE      equ 4                       ; οι εισβολείς (βήμα 111, src/foe.asm)
; ΟΙ ΕΙΣΒΟΛΕΙΣ (βήμα 111, §6.10): το επόμενο απρόσκλητο πλοίο αφού μετρηθούν
; FOE_EVERY προσγειώσεις, και ποτέ με λιγότερους από FOE_POP αποίκους (οι
; αποφάσεις του παίκτη). Εδώ γιατί τα διαβάζει και η ζαριά, στην τράπεζα 0.
FOE_POP     equ 20
FOE_EVERY   equ 8
MER_SLOTS   equ 4                       ; αγαθά στο φορτίο, ως
MER_ROLL    equ #5A5                    ; τα 11 κάτω bits του r2 (src/econ.asm)
MARKUP_MIN  equ 35                      ; + 0..30 %
TRADE_N     equ 13                      ; τα αποθέματα 1-13: όλα εκτός από το νερό
TRADE_MAX   equ 99                      ; ως τόσα από ένα αγαθό σε μία προσφορά
COIN_MAX    equ 999                     ; τα νομίσματα (βήμα 134): όσα χωρά το HUD
MER_COIN    equ 5                       ; δεκάδες ανά παρτίδα νομισμάτων του εμπόρου (βήμα 135)

EC_CAP      equ 600                     ; ταβάνι αποθέματος

; --- τα δεκατέσσερα αποθέματα, με τη σειρά του econ.py ---
S_WATER     equ 0
S_FOOD      equ 1
S_ORE       equ 2
S_METAL     equ 3
S_BIOPL     equ 4
S_PROC      equ 5
S_SPARE     equ 6
S_MEDI      equ 7
S_GUN       equ 8
S_BOT       equ 9
S_STARCH    equ 10
S_VEG       equ 11
S_MEDPLANT  equ 12
S_MEAT      equ 13

; --- οι κλάσεις του world byte (§3.5) ---
W_GROUND    equ 0
W_DUST      equ 1
W_ROCK      equ 2
W_MOUNTAIN  equ 3
W_WATER     equ 4
W_DEEPWATER equ 5
W_CRATER    equ 6
W_FOUNDATION equ 7
W_OCC_MASK  equ #30
W_OCC_STRUCT equ #10

; --- ο πίνακας εργασιών (§6.7). Εδώ επειδή τον γράφει και το build mode.
MAX_JOB     equ 32
JOB_REC     equ 5
J_KIND      equ 0
J_NODE      equ 1
J_AGENT     equ 2
J_PRIO      equ 3
; ΤΟ ΠΕΜΠΤΟ BYTE ΕΙΝΑΙ Ο ΚΟΜΒΟΣ ΤΗΣ ΕΡΓΑΣΙΑΣ, και το J_NODE είναι πού πηγαίνει
; ο πράκτορας της (βήμα 88). Για όλες τις εργασίες τα δύο είναι ίδια, εκτός
; από το πρώτο σκέλος μιας Supply: τότε το J_NODE είναι η πηγή (το σκάφος, μια
; αποθήκη) και το J_SITE το εργοτάξιο. Ως το 87 ήταν «ηλικία» και δεν το
; διάβαζε κανείς.
J_SITE      equ 4
NO_JOB      equ 255
J_BUILD     equ 0
J_OPERATE   equ 1
J_HAUL      equ 2
J_DRILL     equ 3
J_REPAIR    equ 4
J_HEAL      equ 5
J_DEFEND    equ 6
J_SUPPLY    equ 7               ; μέταλλο· J_SUPPLY + 1 βιοπλαστικό (βήμα 88, src/supply.asm)
J_TRADE     equ 9               ; τα αγαθά του εμπόρου (βήμα 98, src/carry.asm)
; Μια J_TRADE κρατά το φορτίο της στο J_SITE, όχι στον πράκτορα (βήμα 98): ό,τι
; κουβαλά συνεχίζει με τον επόμενο, αν ο πρώτος πεινάσει ή πεθάνει. 0 άδεια,
; TRADE_GIVE ένα φορτίο για τον έμπορο, ποσότητα << 4 | απόθεμα ένα δικό του.
TRADE_JOBS  equ 2               ; εργασίες ανά συμφωνία: δύο μεταφορείς
TRADE_LOAD  equ 10              ; μονάδες ανά φορτίο, όπως της τροφοδοσίας
TRADE_GIVE  equ #0F
; οι ρόλοι (§6.1) που χτίζουν: μηχανικός και ρομπότ κατασκευής
RL_ENGINEER equ 1
RL_CBOT     equ 5
RL_CARRY    equ 6
RL_DRILL    equ 7           ; βήμα 94: τα ρομπότ γεώτρησης (src/drill.asm)
; ΟΙ ΘΕΣΕΙΣ ΤΩΝ ΡΟΜΠΟΤ (βήμα 92): οι πράκτορες 0-159 είναι άποικοι και οι
; 160-175 ρομπότ (βήμα 173· ως τότε 0-79 και 80-95, τα 80 + 16 του §6.1). Ο
; τροχός κινεί και τους 176· το πέρασμα των αναγκών μόνο τους 160 (src/wheel.asm),
; γιατί τα ρομπότ δεν τρώνε, δεν πίνουν, δεν κοιμούνται και δεν αναπνέουν. Το
; ταβάνι πληθυσμού, οι ζωντανοί του EC_ALIVE και η ζήτηση οξυγόνου μετρούν μόνο
; τους 160. Το AG_BOT0 είναι και το πλήθος των θέσεων αποίκων.
AG_BOT0     equ 160
AG_NBOT     equ 16
; ΟΙ ΕΙΣΒΟΛΕΙΣ (βήμα 111, src/foe.asm) στις θέσεις 176-179 (96-99 ως το βήμα
; 172): έξω από τις φέτες κίνησης και αναγκών (0-175), χωρίς ανάγκες, με τον
; ρόλο 8 και εργασία T_FIGHT — που δεν είναι δείκτης εργασίας, όπως το T_NEED,
; και τον κρατούν και οι φρουροί στη μάχη. Ο φρουρός με όπλο έχει το F_GUN.
AG_FOE0     equ 176
AG_NFOE     equ 4
RL_GUARD    equ 4
RL_FOE      equ 8
T_FIGHT     equ 253
F_GUN       equ 128
; ΟΙ ΕΠΙΣΚΕΠΤΕΣ ΠΟΥ ΠΕΡΠΑΤΟΥΝ (βήμα 136, src/visit.asm) στις θέσεις 180-187
; (112-119 ως το βήμα 172), αμέσως μετά τους εισβολείς: όπως εκείνοι έξω από τις
; φέτες κίνησης και αναγκών, με τον ρόλο 9 (η λευκή φιγούρα, role_fig) και
; εργασία T_VISIT, που δεν είναι δείκτης εργασίας.
AG_VIS0     equ 180
AG_NVIS     equ 8
; ΟΙ IDS ΣΕ ΧΡΗΣΗ, 0-187 (βήμα 173· 128 ως τότε, στο src/entity.asm): εδώ γιατί
; τα περάσματα του renderer (ob_fig_scan) και του νέου παιχνιδιού τους
; περπατούν και σε σκαλωσιές χωρίς το entity.asm.
N_AGENT     equ AG_VIS0 + AG_NVIS
RL_VIS      equ 9
T_VISIT     equ 252
; Το ευρετήριο δωματίων (src/needs.asm): ως τόσοι θόλοι ανά είδος. Εδώ από το
; βήμα 88, γιατί το διαβάζει και το src/supply.asm, που δεν έχει το needs.asm
; σε κάθε harness.
ROOM_MAX    equ 8

; --- ο γράφος κόμβων (§6.2). Εδώ επειδή τον γράφει και το build mode.
MAX_DEGREE  equ 8

; --- τα πεδία των πρακτόρων (§6.1), ΕΝΑ ΣΕ ΚΑΘΕ ΣΕΛΙΔΑ από το βήμα 172.
; Εδώ και όχι στο entity.asm: τα διαβάζει και ο renderer, και ο assembler δεν
; συγχωρεί δύο ορισμούς — αυτό ήταν το πρώτο που έσπασε όταν τα δύο μισά του
; παιχνιδιού μπήκαν για πρώτη φορά στο ίδιο binary.
; Ως το βήμα 171 δύο πεδία των 128 μοιράζονταν μια σελίδα, το δεύτερο στο +128
; (set 7,l). Τώρα το πρώτο μένει στη σελίδα AG_PG + k και το δεύτερο είναι στην
; AG_PG + 8 + k: από το ένα στο άλλο `set 3,h`, αφού το AG_PG είναι πολλαπλάσιο
; του 16 (assert), και το `inc h` από πεδίο σε πεδίο του ίδιου μισού μένει.
AG_PG       equ G_agent_fields >> 8
AG_HI       equ 8                            ; οι σελίδες των δεύτερων πεδίων
AG_FLAGS    equ G_agent_fields               ; flags     (role     στο + AG_HI σελίδες)
AG_NODE     equ G_agent_fields + 256         ; node      (slot)
AG_DEST     equ G_agent_fields + 512         ; dest      (edge)
AG_PROG     equ G_agent_fields + 768         ; progress  (task)
AG_O2       equ G_agent_fields + 1024        ; o2        (water)
AG_FOOD     equ G_agent_fields + 1280        ; food      (sleep)
AG_HEALTH   equ G_agent_fields + 1536        ; health    (morale)
AG_SUIT     equ G_agent_fields + 1792        ; suit      (spare· βήμα 90: ως τότε skill, που δεν το διάβασε ποτέ κανείς)
AG_ROLE     equ AG_FLAGS + AG_HI * 256
AG_SLOT     equ AG_NODE + AG_HI * 256
AG_EDGE     equ AG_DEST + AG_HI * 256
AG_TASK     equ AG_PROG + AG_HI * 256
AG_WATER    equ AG_O2 + AG_HI * 256
AG_SLEEP    equ AG_FOOD + AG_HI * 256
AG_MORALE   equ AG_HEALTH + AG_HI * 256
AG_SPARE    equ AG_SUIT + AG_HI * 256
; ΤΑ ΣΗΜΑΔΙΑ ΤΩΝ ΦΙΓΟΥΡΩΝ (fg_mark, src/entity.asm), ένα ανά πράκτορα, σε δική
; τους σελίδα από το βήμα 172· ως τότε το πάνω μισό του node_occ.
MKPG        equ G_agent_marks >> 8
; «Πάω για ανάγκη» στο πεδίο της εργασίας: όχι δείκτης εργασίας (src/needs.asm).
T_NEED      equ 254
OCCPG       equ G_node_occ >> 8

; --- η ελεύθερη τράπεζα 2, μοιρασμένη (§4.3).
; Πρώτα οι δύο μεγάλοι buffers και μετά κώδικας. Η τράπεζα 2 φαίνεται πάντα,
; οπότε και τα δύο δουλεύουν χωρίς σελιδοποίηση· αυτό που κερδίζεται είναι
; χώρος στην τράπεζα 0, που είναι η μόνη σπάνια.
GH_BUF      equ PAGE2_TOP
; ΤΟ ΑΡΧΕΙΟ ΕΙΝΑΙ ΟΣΟ ΤΟ ΧΕΙΡΟΤΕΡΟ ΦΑΝΤΑΣΜΑ, ΥΠΟΛΟΓΙΣΜΕΝΟ — όχι ένα στρογγυλό
; 1.600 (βήμα 41). Το χειρότερο είναι ένας θόλος L κόκκινος σε όλα του τα
; tiles: το πλαίσιο, τέσσερα ορθογώνια (src/ghost.asm, gh_box), και ένα σημάδι
; 2x4 σε καθένα από τα 64 tiles. Μετρημένο στο παιχνίδι: 1.160 bytes
; (tests/test_reveal.py). Η προεπισκόπηση διαδρόμου φτάνει τα 308 (βήμα 40,
; εξαντλητικά), η μεγαλύτερη δομή τα 392. Ενα μεγαλύτερο αποτύπωμα αλλάζει
; το GH_SIDE, και το αρχείο ακολουθεί.
GH_HDR      equ 4                   ; κεφαλίδα ορθογωνίου: διεύθυνση, πλάτος, ύψος
GH_EDGE     equ 2                   ; πάχος της οριζόντιας πλευράς του πλαισίου
GH_SIDE     equ 8                   ; το μεγαλύτερο αποτύπωμα σε tiles: θόλος L
GH_LOG      equ 2 * (GH_HDR + GH_SIDE * 4 * GH_EDGE) + 2 * (GH_HDR + GH_SIDE * 16 - 2 * GH_EDGE) + GH_SIDE * GH_SIDE * (GH_HDR + 2 * 4)
PAGE2_CODE  equ GH_BUF + GH_LOG     ; από εδώ και πάνω, κώδικας
; Ο ΚΩΔΙΚΑΣ ΤΗΣ ΕΚΚΙΝΗΣΗΣ ΣΤΟ ΤΕΛΟΣ ΤΟΥ GH_BUF (βήμα 158, src/startup.asm): ό,τι
; τρέχει μία φορά, πριν από το πρώτο φάντασμα — η αρχή του start και όλο το
; game_new. Ο δίσκος τον φέρνει με το game2.bin, που αρχίζει πια από εδώ (ο
; φορτωτής αντιγράφει στο BOOT_ORG, src/boot.asm), και από κάτω του η αποικία
; δοκιμών (μόνο στο snapshot). Το πρώτο μεγάλο φάντασμα τον σβήνει.
BOOT_MAX    equ 448
BOOT_ORG    equ PAGE2_CODE - BOOT_MAX
; Η κρυφή μνήμη φιγούρων ήταν εδώ και πήρε 512 bytes τράπεζας 2· από το βήμα 30
; ζει στην τράπεζα 6 (G_dome_fig), όπου το πέρασμα αντικειμένων την έχει ήδη
; σελιδοποιημένη. Τα 512 έγιναν κώδικας που έφυγε από την τράπεζα 0.
; ΑΠΟ ΤΟ ΒΗΜΑ 172 ΣΤΙΣ ΟΥΡΕΣ ΤΩΝ ΠΕΔΙΩΝ: η θέση s του θόλου d στο byte 192 + d
; της σελίδας DF_PG + s, οι σελίδες των δεύτερων πεδίων (ids ως 187 στο 173).
DF_PG       equ AG_PG + AG_HI
DF_L        equ 192

; --- τα είδη της λίστας βρώμικων (§8.5). Εδώ επειδή τα σπρώχνει η
; προσομοίωση, που δεν συνδέει renderer στο tests/simtest.asm.
DK_SLOT     equ 0                   ; a = θόλος, b = θέση δακτυλίου
DK_MACH     equ 1                   ; a = θόλος, b = υποδοχή
DK_ICON     equ 2                   ; a = θόλος
DK_CONN     equ 3                   ; a = θόλος, b = κατεύθυνση: ο αρμός (ως το 95 η πόρτα)
DK_TILE     equ 4                   ; a = tx, b = ty (προσημασμένα)
DK_BUILT    equ 5                   ; a = κόμβος που μόλις τελείωσε (§6.9)
DK_SITE     equ 6                   ; a = θόλος, b = σειρά tiles του εργοταξίου
DK_CROW     equ 7                   ; a = tx, b = ty: τρία tiles μιας διαγωνίου
DK_AGENT    equ 8                   ; a = πράκτορας: η φιγούρα του έξω (βήμα 89)
DK_RSIZE    equ 9                   ; a = πλάτος, b = ύψος του DK_RECT που ακολουθεί
DK_RECT     equ 10                  ; a = tx, b = ty: ορθογώνιο tiles, έδαφος και ό,τι
                                    ; το πατά (βήμα 101, η κατεδάφιση)
DK_KINDS    equ 11

; --- ευρετήριο αντικειμένων (src/object.asm, βήμα 39) ---
; Στην τράπεζα 5. Ως το βήμα 154 πάνω από το NEXTHOP[MAX_NODE][128], που
; τελείωνε στο #6FFF· από το 155, όπου έχει 112 γραμμές ως το #77FF, πάνω από
; τους διαδρόμους (G_obj_index, tools/pack.py). Ανά εγγραφή x0, x1, y0, y1 σε
; tiles του κόσμου +128, και το id· θόλοι, διάδρομοι, δομές, με τη σειρά
; σχεδίασης.
OI_REC      equ 5
OB_IX_FIG   equ 1           ; ob_idx: οι φιγούρες (ob_fig_scan· ως το 95 και οι πόρτες)
OB_IX_DOME  equ 2           ;         τα κελύφη των θόλων
OB_IX_CORR  equ 4           ;         οι διάδρομοι
OB_IX_STRUCT equ 8          ;         οι δομές
OB_IX_ALL   equ 15
OI_DOME     equ G_obj_index
OI_CORR     equ OI_DOME + MAX_DOME * OI_REC
OI_STRUCT   equ OI_CORR + MAX_CORR * OI_REC
OI_END      equ OI_STRUCT + MAX_STRUCT * OI_REC
